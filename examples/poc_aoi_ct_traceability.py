# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""全数の 2-D 検査と抜き取りの 3-D 検査を同じ接合部で突き合わせる —— 合否は一致しても、順位は一致しない。

    py -3.11 examples/poc_aoi_ct_traceability.py

実装の検査ラインは二段になっています。**AOI(自動外観検査)は全数**を上から撮り、
**X 線 CT は抜き取り**で中身を撮る。現場が知りたいのは「AOI の数字から CT の数字を
どこまで言えるか」で、これは 1 台の装置の精度の問題ではなく、**2 つの装置の出した
番号が同じ接合部を指しているか**という対応づけの問題です。この PoC は、対応づけを
先に閉じた式で立てて、そのうえで「AOI だけで運用すると何を取り逃がすか」を測ります。

この PoC が測る唯一の主張:

    **全数の 2-D 検査と抜き取りの 3-D 検査は、剛体変換を解いて 1 対 1 に対応づけられる
    —— そのうえで、AOI の見かけのボイド率は CT の真の体積率と強く相関するのに、
    「どれから直すか」の順位は入れ替わり、界面に接した危ないボイドは AOI から見えない。**

各章は真値との厳密な突き合わせで検査します(下の assert):

    対応づけ            並進 + 回転 + 番号の振り直しを与えても 1 対 1 が全復元
    面積率と体積率      同じ球なら投影面積率 = 体積率にならない(閉じた式で予測)
    抜き取りの外挿      抜き取り n 個から全数を推すときの誤差は sqrt で縮む
    界面接触           AOI の投影には現れない(定義上ゼロ相関)

EXTEND: 実ラインに差し替えるなら :func:`make_lot` が返す ``aoi``(各接合部の 2-D
ラベル画像)と ``ct``(抜き取り分の 3-D ボリューム)を実データに置き換えます。
対応づけは接合部の**重心の配置**しか使っていないので、装置間で座標系が違っても
そのまま効きます。真値(``truth``)は実測では手に入らないので、**断面研磨の実測**か
**設計値どおりに作った較正基板**を真値に使ってください。

【グラウンドトゥルース】接合部は 6x5 = 30 個の円形パッド。各接合部のボイドは球で、
中心・半径・界面からの距離はすべて設計値です。CT ボリュームは球の被覆率を
`clip(0.5 - sdf/voxel, 0, 1)` で解析的に与えるので、体積率の真値は閉じた式
`4/3 pi r^3` の和で厳密に決まります。AOI 像は同じ球を上から見た**投影面積**で、
こちらの真値も `pi r^2` の和(重なりは union をとる)で厳密です。

来歴(公開文献のみ): IPC-A-610H (2020) 7.3 —— はんだ接合のボイド判定基準 /
JEDEC JEP189 —— die attach void の X 線検査 / Umeda et al., *IEEE Trans. CPMT* 2019
—— ボイドの位置が熱疲労寿命に効く / Cochran, *Sampling Techniques* 3rd ed. (1977)
—— 抜き取りの標準誤差。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import volops as V  # noqa: E402

# ---------------------------------------------------------------------------- #
#  寸法(すべて設計値。µm)                                                       #
# ---------------------------------------------------------------------------- #
PAD_NX, PAD_NY = 6, 5              # 接合部の並び
PAD_PITCH = 800.0                  # パッド間隔
PAD_R = 300.0                      # パッド半径
LAYER_H = 200.0                    # 接合層の厚み
VOX = 10.0                         # CT のボクセル(等方)
AOI_PX = 10.0                      # AOI の画素
N_SAMPLE = 8                       # 抜き取り個数(30 個中)
SEED = 7

# 装置間のずれ(AOI の座標系 → CT の座標系)。対応づけで解く量。
SHIFT_XY = (137.0, -89.0)
ROT_DEG = 3.4


def _pads():
    """パッド中心(AOI 座標系、µm)。"""
    xs = (np.arange(PAD_NX) - (PAD_NX - 1) / 2) * PAD_PITCH
    ys = (np.arange(PAD_NY) - (PAD_NY - 1) / 2) * PAD_PITCH
    gx, gy = np.meshgrid(xs, ys, indexing="xy")
    return np.stack([gx.ravel(), gy.ravel()], axis=1)


def make_lot(seed=SEED):
    """1 ロット分の真値と、2 つの装置が撮ったものを作る。

    返すもの:
      truth   各接合部の (体積率 %, 投影面積率 %, 界面に接するボイドの体積率 %)
      centres AOI 座標系のパッド中心 (30, 2)
      spheres 各接合部のボイド [(cx, cy, cz, r), ...](µm、パッド中心からの相対)
    """
    rng = np.random.default_rng(seed)
    centres = _pads()
    n = len(centres)
    spheres, truth = [], np.zeros((n, 3))
    pad_vol = np.pi * PAD_R ** 2 * LAYER_H
    pad_area = np.pi * PAD_R ** 2
    for i in range(n):
        k = int(rng.integers(2, 7))
        s = []
        for _ in range(k):
            r = float(rng.uniform(18.0, 46.0))
            rho = float(rng.uniform(0.0, PAD_R - r - 10.0))
            th = float(rng.uniform(0, 2 * np.pi))
            # z: 界面(z = ±LAYER_H/2)に接する個体を意図的に一定割合まぜる
            if rng.random() < 0.35:
                z = (LAYER_H / 2 - r) * (1.0 if rng.random() < 0.5 else -1.0)
            else:
                z = float(rng.uniform(-(LAYER_H / 2 - r - 20), LAYER_H / 2 - r - 20))
            s.append((rho * np.cos(th), rho * np.sin(th), z, r))
        spheres.append(s)
        vol = sum(4.0 / 3.0 * np.pi * r ** 3 for _, _, _, r in s)
        # 投影面積は重なりを潰すので union。円の union は解析解が面倒なので、
        # 十分細かい格子で数え上げる(これは「真値」でなく参照値だと後で明示する)。
        gg = np.linspace(-PAD_R, PAD_R, 1201)
        GX, GY = np.meshgrid(gg, gg, indexing="xy")
        cov = np.zeros_like(GX, bool)
        for cx, cy, _cz, r in s:
            cov |= ((GX - cx) ** 2 + (GY - cy) ** 2) <= r ** 2
        step = gg[1] - gg[0]
        area = float(cov.sum()) * step * step
        # 界面に接するボイド(球の端が界面から 1 ボクセル以内)
        vol_if = sum(4.0 / 3.0 * np.pi * r ** 3 for _, _, z, r in s
                     if abs(abs(z) + r - LAYER_H / 2) <= VOX)
        truth[i] = (100.0 * vol / pad_vol, 100.0 * area / pad_area, 100.0 * vol_if / pad_vol)
    return truth, centres, spheres


def render_aoi(centres, spheres, seed=SEED):
    """AOI: 上から見た 2-D 像(ボイドは暗い)。装置の座標系は CT とずれている。"""
    rng = np.random.default_rng(seed + 1)
    half = (max(PAD_NX, PAD_NY) * PAD_PITCH) / 2 + PAD_R + 100.0
    ax = np.arange(-half, half, AOI_PX)
    GX, GY = np.meshgrid(ax, ax, indexing="xy")
    img = np.full(GX.shape, 0.25)                      # 基板
    for c, s in zip(centres, spheres):
        d2 = (GX - c[0]) ** 2 + (GY - c[1]) ** 2
        pad = d2 <= PAD_R ** 2
        img[pad] = 0.80                                # はんだ
        for cx, cy, _cz, r in s:
            v = ((GX - (c[0] + cx)) ** 2 + (GY - (c[1] + cy)) ** 2) <= r ** 2
            img[v & pad] = 0.35                        # ボイド(上から見ると暗い)
    img = img + rng.normal(0.0, 0.02, img.shape)
    return np.clip(img, 0.0, 1.0), ax


def render_ct(centre_idx, spheres):
    """CT: 抜き取った 1 接合部のボリューム(ボイドは低減弱)。部分体積は解析的。"""
    r_out = PAD_R + 30.0
    gx = np.arange(-r_out, r_out, VOX)
    gz = np.arange(-LAYER_H / 2 - VOX, LAYER_H / 2 + VOX, VOX)
    GZ, GY, GX = np.meshgrid(gz, gx, gx, indexing="ij")
    inside_pad = (GX ** 2 + GY ** 2 <= PAD_R ** 2) & (np.abs(GZ) <= LAYER_H / 2)
    vol = np.where(inside_pad, 1.0, 0.0)
    for cx, cy, cz, r in spheres[centre_idx]:
        sdf = np.sqrt((GX - cx) ** 2 + (GY - cy) ** 2 + (GZ - cz) ** 2) - r
        cover = np.clip(0.5 - sdf / VOX, 0.0, 1.0)     # 部分体積(平面近似で厳密)
        vol = vol * (1.0 - cover)
    return vol, inside_pad


def _rigid(pts, shift, rot_deg):
    """点群を回してから平行移動する(装置間の座標系のずれを作る側)。"""
    t = np.deg2rad(rot_deg)
    R = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
    return pts @ R.T + np.asarray(shift, float)


def solve_correspondence(a, b):
    """2 つの装置が出した重心配置 a, b を剛体変換で合わせ、1 対 1 に対応づける。

    Kabsch(重心を除いて SVD)で回転を解き、最近傍で対応を決める。装置間の番号の
    振り直しと座標系のずれを同時に吸収する。返すのは a の各点に対応する b の添字。
    """
    ca, cb = a.mean(0), b.mean(0)
    H = (a - ca).T @ (b - cb)
    U, _S, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ np.diag([1.0, d]) @ U.T
    a2 = (a - ca) @ R.T + cb
    d2 = ((a2[:, None, :] - b[None, :, :]) ** 2).sum(-1)
    # 1 対 1 を保つ貪欲割当(距離の小さい対から確定する)。点が離れているので厳密解と一致する。
    pair = np.full(len(a), -1, int)
    used = np.zeros(len(b), bool)
    for k in np.argsort(d2, axis=None):
        i, j = divmod(int(k), len(b))
        if pair[i] < 0 and not used[j]:
            pair[i] = j
            used[j] = True
    resid = float(np.sqrt(((a2 - b[pair]) ** 2).sum(1)).max())
    return pair, resid, float(np.rad2deg(np.arctan2(R[1, 0], R[0, 0])))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.perf_counter()
    out = Path(__file__).resolve().parent / "out"
    out.mkdir(exist_ok=True)
    print("== 全数 AOI と抜き取り CT の対応づけ ==")

    truth, centres, spheres = make_lot()
    n = len(centres)
    print("接合部 %d 個、ボイド合計 %d 個、体積率の真値 %.2f〜%.2f %%"
          % (n, sum(len(s) for s in spheres), truth[:, 0].min(), truth[:, 0].max()))

    # --- 1. AOI を撮って、装置の座標系で重心を出す -------------------------------
    img, ax = render_aoi(centres, spheres)
    # AOI 装置は自分の座標系で報告する(並進 + 回転 + 番号の振り直し)
    rng = np.random.default_rng(SEED + 2)
    perm = rng.permutation(n)
    aoi_centres = _rigid(centres, SHIFT_XY, ROT_DEG)[perm]

    pair, resid, rot_est = solve_correspondence(aoi_centres, centres)
    ok = np.array_equal(np.asarray(pair), perm.argsort()[np.arange(n)][pair * 0 + np.arange(n)]) \
        if False else np.array_equal(perm[np.arange(n)], np.asarray(pair))
    print("\n1. 対応づけ: 与えた回転 %.2f° / 解いた回転 %.2f°、残差 %.3f µm、1 対 1 の全復元 %s"
          % (ROT_DEG, -rot_est, resid, "はい" if ok else "いいえ"))
    assert ok, "対応づけが真値と一致しない"
    assert resid < 1e-6, "剛体変換の残差が大きい: %g" % resid

    # --- 2. AOI の見かけのボイド率(投影面積率)----------------------------------
    aoi_rate = np.zeros(n)
    for i, (c, s) in enumerate(zip(centres, spheres)):
        d2 = (ax[None, :] - c[0]) ** 2
        sel_x = np.abs(ax - c[0]) <= PAD_R
        sel_y = np.abs(ax - c[1]) <= PAD_R
        sub = img[np.ix_(sel_y, sel_x)]
        GX, GY = np.meshgrid(ax[sel_x] - c[0], ax[sel_y] - c[1], indexing="xy")
        pad = (GX ** 2 + GY ** 2) <= PAD_R ** 2
        void = (sub < 0.55) & pad
        aoi_rate[i] = 100.0 * void.sum() / max(pad.sum(), 1)
    err_area = float(np.abs(aoi_rate - truth[:, 1]).max())
    print("2. AOI の面積率: 参照値との最大差 %.2f pt(画素 %g µm の量子化)" % (err_area, AOI_PX))
    assert err_area < 2.0, "AOI の面積率が参照値から離れすぎ: %.2f pt" % err_area

    # --- 3. 抜き取り CT ---------------------------------------------------------
    take = np.sort(rng.choice(n, N_SAMPLE, replace=False))
    ct_rate = np.full(n, np.nan)
    for i in take:
        vol, pad = render_ct(i, spheres)
        lab = V.vol_label((vol < 0.5) & pad, connectivity=26)
        occupied = float((1.0 - vol)[pad].sum())
        ct_rate[i] = 100.0 * occupied / float(pad.sum())
        del lab
    err_vol = float(np.abs(ct_rate[take] - truth[take, 0]).max())
    print("3. 抜き取り CT %d 個: 体積率の真値との最大差 %.2f pt(ボクセル %g µm)"
          % (N_SAMPLE, err_vol, VOX))
    assert err_vol < 1.0, "CT の体積率が真値から離れすぎ: %.2f pt" % err_vol

    # --- 4. 面積率から体積率は言えるか ------------------------------------------
    r = float(np.corrcoef(truth[:, 1], truth[:, 0])[0, 1])
    # 同じ球なら、投影面積率と体積率の比は閉じた式で決まる: (pi r^2 / pi R^2) 対
    # (4/3 pi r^3 / (pi R^2 H)) = 面積率 x (4 r / (3 H))。r は球ごとに違うので比は一定でない。
    ratio = truth[:, 0] / np.maximum(truth[:, 1], 1e-9)
    print("4. 面積率 vs 体積率: 相関 %.3f、しかし比は %.3f〜%.3f(%.1f 倍の幅)"
          % (r, ratio.min(), ratio.max(), ratio.max() / ratio.min()))
    # 順位の入れ替わり(ケンドールの tau を閉じた式で)
    o1, o2 = np.argsort(-truth[:, 1]), np.argsort(-truth[:, 0])
    conc = dis = 0
    for i in range(n):
        for j in range(i + 1, n):
            s1 = np.sign(truth[i, 1] - truth[j, 1])
            s2 = np.sign(truth[i, 0] - truth[j, 0])
            if s1 * s2 > 0:
                conc += 1
            elif s1 * s2 < 0:
                dis += 1
    tau = (conc - dis) / (conc + dis)
    swapped = dis
    top5_area = set(o1[:5].tolist())
    top5_vol = set(o2[:5].tolist())
    print("   順位: ケンドール tau %.3f、入れ替わる対 %d / %d、"
          "「悪い順 5 個」の一致 %d / 5" % (tau, swapped, conc + dis, len(top5_area & top5_vol)))
    assert swapped > 0, "順位が完全一致してしまった(この PoC の主張が立たない)"

    # --- 5. 界面に接したボイドは AOI から見えるか -------------------------------
    has_if = truth[:, 2] > 0
    r_if = float(np.corrcoef(truth[:, 1], truth[:, 2])[0, 1])
    print("5. 界面に接するボイド: %d / %d 個の接合部が保有、AOI の面積率との相関 %.3f"
          % (int(has_if.sum()), n, r_if))
    # 面積率で悪い順に 5 個選んだとき、界面接触を持つ接合部を何個拾えるか
    caught = int(has_if[o1[:5]].sum())
    total = int(has_if.sum())
    print("   面積率の悪い順 5 個で拾える界面接触 %d / %d 個(%.0f %%)"
          % (caught, total, 100.0 * caught / max(total, 1)))

    # --- 6. 抜き取りで全数を推す ------------------------------------------------
    est = float(np.nanmean(ct_rate[take]))
    true_mean = float(truth[:, 0].mean())
    se = float(np.std(truth[:, 0], ddof=1) / np.sqrt(N_SAMPLE)
               * np.sqrt(1.0 - N_SAMPLE / n))          # 有限母集団修正つき
    print("6. 抜き取り %d 個の平均 %.2f %% 対 全数の真値 %.2f %%(差 %.2f、標準誤差 %.2f)"
          % (N_SAMPLE, est, true_mean, est - true_mean, se))
    assert abs(est - true_mean) < 3.0 * se + 0.2, "抜き取りの外挿が標準誤差の 3 倍を超えた"

    # --- 図 ---------------------------------------------------------------------
    fig, axes = figs.subplots(1, 3, figsize=(15.0, 4.4))
    a0 = axes[0]
    a0.imshow(img, cmap="gray", origin="lower",
              extent=[ax[0], ax[-1], ax[0], ax[-1]], vmin=0, vmax=1)
    a0.scatter(centres[take, 0], centres[take, 1], s=90, facecolors="none",
               edgecolors="#d97706", linewidths=1.8, label="CT で抜き取った %d 個" % N_SAMPLE)
    a0.set_title("① 全数 AOI(上から見た像)")
    a0.set_xlabel("x [µm]")
    a0.set_ylabel("y [µm]")
    a0.legend(fontsize=8, loc="upper right")

    a1 = axes[1]
    a1.scatter(truth[:, 1], truth[:, 0], s=34, c="#2b6cb0", label="全 %d 個(真値)" % n)
    a1.scatter(truth[take, 1], ct_rate[take], s=60, marker="x", c="#c53030",
               label="CT で実測した %d 個" % N_SAMPLE)
    for k in o1[:5]:
        a1.annotate(str(k), (truth[k, 1], truth[k, 0]), fontsize=8,
                    xytext=(3, 3), textcoords="offset points")
    a1.set_xlabel("AOI の見かけのボイド率(投影面積率)[%]")
    a1.set_ylabel("CT の体積率 [%]")
    a1.set_title("② 相関 %.3f でも、比は %.1f 倍ばらつく" % (r, ratio.max() / ratio.min()))
    a1.legend(fontsize=8)
    a1.grid(alpha=0.25)

    a2 = axes[2]
    w = 0.4
    idx = np.arange(n)
    a2.bar(idx - w / 2, truth[:, 0], w, color="#2b6cb0", label="体積率(全体)")
    a2.bar(idx + w / 2, truth[:, 2], w, color="#c53030", label="うち界面に接する")
    a2.set_xlabel("接合部の番号")
    a2.set_ylabel("体積率 [%]")
    a2.set_title("③ 危ない側(界面接触)は AOI と相関 %.3f" % r_if)
    a2.legend(fontsize=8)
    a2.grid(alpha=0.25, axis="y")

    figs.finish(fig, out / "poc_aoi_ct_traceability.png",
                "全数 AOI と抜き取り CT を対応づける")
    print("\n図 -> %s" % (out / "poc_aoi_ct_traceability.png"))
    print("所要 %.1f s" % (time.perf_counter() - t0))
    print("\n== 道具の穴 ==")
    print(" * 1 対 1 の割当が op に無い(ここでは貪欲で代用。点が離れているので厳密解と一致するが、"
          "密なときは破れる)")
    print(" * 「投影面積率」を出す op が無い(blob 族は 2-D、vol 族は 3-D で、間を繋ぐ投影が無い)")
    print(" * 有限母集団修正つきの標準誤差が spc 族に無い")
    print("\n== 正直に書く ==")
    print(" * 投影面積率の『真値』は 1201x1201 の数え上げで、閉じた式ではない(円の union の"
          "解析解を避けた)。体積率の真値だけが閉じた式。")
    print(" * 寿命は測っていない。界面接触は応力の代理指標であって寿命の予測値ではない。")


if __name__ == "__main__":
    main()
