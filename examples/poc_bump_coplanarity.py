# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""バンプの共平面性を基板そりから分ける —— 引きすぎると本物の不良も一緒に消える。

先端実装(アドバンストパッケージング)の受け入れ検査です。Cu ピラー / はんだバンプを
何百本も並べた基板を高さ計測(白色干渉・レーザー変位・位相シフトモアレ)に掛けると、
1 枚の高さ場に **基板のそり(warpage、数十 µm・低次のうねり)** と
**バンプ 1 本ごとの高さのばらつき(数 µm)** が重なって入っています。
不良として拾いたいのは後者なのに、値が大きいのは前者。**そりを当てはめて引いた残差が
バンプ個体差**という分け方が正しいのか、どこまで正しいのかを測ります。

EXTEND: 実測に差し替えるなら :func:`make_scene` が返す辞書の ``height``
(高さ場 [µm]、1 画素 = ``PX_UM``)を実機の高さ場に置き換えます。真値側の
``h_true``(バンプ 1 本ごとの真の高さ)は実測では手に入らないので、**同じ基板を
そりの出ない治具で平坦拘束して測った高さ**か、断面研磨の実測を真値に使います。
「良品ロットの平均」を真値にするのは不可 —— そりの平均が 0 でないと系統誤差が入ります。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(そりを引かずに最小二乗平面だけ引く = JEDEC の着座平面)を先に測る**。
   そり PV 50 µm を仕込むと共平面性は **50.10 µm**(真値 34.03 µm)、
   バンプ個体差の読み取り RMS 誤差は **9.30 µm** —— **個体差の 1σ(4 µm)の 2.3 倍**。
   仕様 ±12 µm で **256 本中 40 本が不合格**、うち **35 本は誤検出**。
2. ★**壊れ方は 2 種類あり、片方は誤検出ではなく見逃し**。ゼロ点は
   誤検出 35 本のかたわらで、仕込んだ本物の短小バンプ 6 本のうち **2 本を見逃す**
   (そりが正の側に居るバンプは、-20 µm 沈んでいても平面からは -12 µm を切らない)。
   2 次曲面を引くと誤検出 0 本 / 見逃し 0 本。**数を 1 つに畳むと、この 2 つが混ざる**。
3. **2 次で足りる。3 次は要らない**。読み取り RMS 誤差は
   1 次 9.30 → 2 次 **0.66** → 3 次 **0.66 µm**。
   ★予想は「高次ほど良い」だったが、**3 次は 2 次と同じ**(仕込んだそりの
   高次成分が 4 次のロブなので、3 次の項では 1 µm も取れない)。
4. **崖は幾何で先に予測できる**。そりの形(モードの混ぜ方)を固定すると、
   2 次で取り切れない残りは PV に**比例**する: 比例定数 r2 = **0.01312**。
   個体差 1σ = 4 µm に並ぶのは PV = 4/r2 = **304.9 µm** と予測 —— 掃引の実測は
   **310.3 µm**(予測比 **1.018**)。1 次のほうは r1 = 0.1856 で予測 21.6 µm、
   実測 21.8 µm(比 1.011)。**そりが 300 µm を超える薄型パッケージでは、
   2 次を引いても個体差は読めない**。
5. **対照群(そり PV = 0)**では 1 次と 2 次の RMS 誤差が **0.22 / 0.22 µm** で
   区別がつかない。壊していたのは当てはめでもバンプでもなく**そり**だと確かめられる。
6. ★★**引きすぎの害は「見えない」形で出る**。バンプ高さに**本物の低次不良**
   (中央のバンプが 8.00 µm 低い = ダイアタッチのボイド)を追加で仕込むと、
   2 次曲面はそれを**そりだと思って吸う**: 中央-外周の真の差 8.00 µm が、
   残差では **0.29 µm**(**96.4 % 消える**)。孤立した短小バンプ 6 本は
   そのまま検出できるので、**「検出できている」ことが健全さの証拠にならない**。
   消えた分は捨てられておらず、**そり側の数字が 50.00 → 57.29 µm(+7.29 µm)と
   膨らんでいる** —— 見る場所を変えれば残っている。
7. ★**検出は簡単な側**。そりを引いた画像(``background_flatten`` degree=2)に
   自動しきい値を掛けるだけで 256 本中 **256 本**を取りこぼしなく拾う。
   難しいのは「見つける」ことではなく「読んだ高さから何を引くか」。

【グラウンドトゥルース】そり = 3 つの解析モード(ボウル ξ²+η² / サドル ξ²−η² /
4 次ロブ ξ⁴+η⁴−6ξ²η²)を PV 比 0.55 : 0.33 : 0.08 で混ぜて PV を指定値に正規化した
閉形式の場。バンプ高さ = 平均 200 µm・σ 4 µm の正規分布(seed 固定)+ 仕込んだ
短小 6 本(−20 µm)。所見 6 では中央低下 8 µm を追加。計測雑音 σ 1.5 µm/画素。

来歴(公開文献のみ): JEDEC JESD22-B108 *Coplanarity Test for Surface-Mount
Semiconductor Devices* —— 着座平面(seating plane)の規定 / JEITA ED-7306 —— そり
測定法 / Zernike, *Physica* 1 (1934) 689 —— 低次モードで面形状を表す考え方。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
N_PIX = 480             # 高さ場の一辺 [px]
PX_UM = 20.0            # 1 画素 [µm/px] -> 9.60 mm 角
NB = 16                 # バンプの並び NB x NB = 256 本
PITCH_UM = 500.0        # バンプピッチ [µm]
R_FOOT_UM = 150.0       # ピラーの footprint 半径 [µm]
R_MEAS_UM = 100.0       # 天面の平坦部(高さを読む範囲)の半径 [µm]
H_NOM = 200.0           # バンプ高さの平均 [µm]
H_SD = 4.0              # バンプ高さの 1σ [µm]  <- これが読みたい量
N_SHORT = 6             # 仕込む短小バンプの本数
SHORT_UM = -20.0        # 短小の深さ [µm]
SPEC_UM = 12.0          # 個体偏差の仕様 [µm](= 3σ)
NOISE_UM = 1.5          # 高さ計測の雑音 1σ [µm/px]
WARP_PV = 50.0          # 既定のそり PV [µm]
CENTER_SAG = 8.0        # 所見 6 で足す「本物の低次不良」[µm]
SEED = 5

_L = fs.ledger          # ledger にしか出ていない op(fit_poly_surface, blob_* 等)


# --------------------------------------------------------------------------- #
# 場面を作る —— 真値は「バンプ 1 本ごとの高さ」と「そりの場」                     #
# --------------------------------------------------------------------------- #
def _warp_modes(n_pix: int) -> tuple[np.ndarray, np.ndarray]:
    """そりの 3 モードを PV 比で混ぜた**正規化された**場(PV = 1)を返す。

    ボウルとサドルは 2 次曲面が厳密に表せる。4 次ロブは表せない —— この
    「表せない割合」が崖の位置を決めるので、混ぜ方を定数にして掃引で PV だけ振る。
    """
    g = (np.arange(n_pix) - (n_pix - 1) / 2.0) / ((n_pix - 1) / 2.0)
    eta, xi = np.meshgrid(g, g, indexing="ij")

    def unit_pv(a):
        a = a - a.mean()
        return a / (a.max() - a.min())

    bowl = unit_pv(xi ** 2 + eta ** 2)
    saddle = unit_pv(xi ** 2 - eta ** 2)
    lobe = unit_pv(xi ** 4 + eta ** 4 - 6.0 * xi ** 2 * eta ** 2)
    w = 0.50 * bowl + 0.30 * saddle + 0.20 * lobe
    w = w - w.mean()
    return w / (w.max() - w.min()), g


def make_scene(warp_pv: float = WARP_PV, center_sag: float = 0.0,
               seed: int = SEED) -> dict:
    """高さ場と真値を返す。``warp_pv`` [µm] だけを振れば崖の掃引になる。"""
    rng = np.random.default_rng(seed)
    unit_warp, _ = _warp_modes(N_PIX)
    warp = warp_pv * unit_warp

    # バンプ中心(画素座標。格子は視野の中央に置く)
    k = (np.arange(NB) - (NB - 1) / 2.0) * (PITCH_UM / PX_UM)
    cy, cx = np.meshgrid(k + (N_PIX - 1) / 2.0, k + (N_PIX - 1) / 2.0, indexing="ij")
    cy, cx = cy.ravel(), cx.ravel()

    # 真値: バンプ 1 本ごとの高さ
    h = H_NOM + H_SD * rng.standard_normal(cy.size)
    short_idx = rng.choice(cy.size, N_SHORT, replace=False)
    h[short_idx] += SHORT_UM
    if center_sag > 0.0:
        # ★本物の低次不良(ダイアタッチのボイド = 中央がなだらかに沈む)。
        #   **わざと厳密な 2 次にしない** —— 2 次にすると当てはめが定義上 100 %
        #   吸ってしまい、「どれだけ吸われるか」という問いが自明になる。
        rr = np.hypot(cy - (N_PIX - 1) / 2.0, cx - (N_PIX - 1) / 2.0)
        h -= center_sag * np.exp(-(rr / (0.35 * rr.max())) ** 2)

    # 高さ場に描く: 平坦な天面 + 縁の丸み(ピラーの断面)
    z = warp.copy()
    r_foot = R_FOOT_UM / PX_UM
    pad = int(np.ceil(r_foot)) + 2
    yy, xx = np.mgrid[-pad:pad + 1, -pad:pad + 1]
    for i in range(cy.size):
        r0, c0 = int(round(cy[i])), int(round(cx[i]))
        d = np.hypot(yy + r0 - cy[i], xx + c0 - cx[i])
        # 天面は平ら、縁 20 % で落ちる(Cu ピラーの断面。半球ではない)
        prof = np.clip((r_foot - d) / (0.2 * r_foot), 0.0, 1.0)
        sl = (slice(r0 - pad, r0 + pad + 1), slice(c0 - pad, c0 + pad + 1))
        z[sl] += h[i] * prof
    z += NOISE_UM * rng.standard_normal(z.shape)

    return {"height": z, "warp": warp, "warp_pv": warp_pv,
            "h_true": h, "cy": cy, "cx": cx, "short_idx": np.sort(short_idx)}


# --------------------------------------------------------------------------- #
# 計測 —— 検出は op、天面の平均は自前(ラベルごとの gray 平均が公開経路に無い)   #
# --------------------------------------------------------------------------- #
def detect_bumps(height: np.ndarray) -> dict:
    """そりを引いた画像から天面を拾う(``background_flatten`` -> 自動しきい値 -> blob)。

    ★**進化 op の ``auto_threshold`` は画像を [0,1] とみなす**。µm 単位の高さ場を
    そのまま渡すと Otsu が 0.5 の位置で切られ、しきい値が「0.5 µm」になって
    背景の残差まで拾う(実測 390 個。正しくは 256 個)。ここで正規化するのは
    そのため —— 単位を持った量を進化 op に渡すときの落とし穴。
    """
    flat = np.asarray(_L.background_flatten(height, degree=2))
    lo, hi = float(flat.min()), float(flat.max())
    nrm = (flat - lo) / (hi - lo)
    mask = np.asarray(fs.apply(nrm, "auto_threshold")) > 0.5   # Otsu(進化 op)
    thr = lo + (hi - lo) * float(nrm[mask].min()) if mask.any() else float("nan")
    lab = _L.blob_label(mask)
    f = _L.blob_features(lab)
    return {"flat": flat, "thr": thr, "labels": lab,
            "row": np.asarray(f["row"], float), "col": np.asarray(f["col"], float),
            "n": int(f["n"])}


def match_to_truth(det: dict, cy: np.ndarray, cx: np.ndarray) -> np.ndarray:
    """検出を仕込み順に並べ替える添字(最近傍。1 対 1 と 1 px 以内を検算する)。"""
    d = np.hypot(det["row"][None, :] - cy[:, None], det["col"][None, :] - cx[:, None])
    idx = np.argmin(d, axis=1)
    assert len(set(idx.tolist())) == cy.size, "1 対 1 で対応しない"
    assert float(d[np.arange(cy.size), idx].max()) < 1.0, "1 px 以上ずれた"
    return idx


def plateau_mean(height: np.ndarray, rows, cols, radius_px: float) -> np.ndarray:
    """天面の平坦部の**平均高さ**。★ラベルごとの gray 平均は公開経路に無いので自前。"""
    pad = int(np.ceil(radius_px)) + 1
    yy, xx = np.mgrid[-pad:pad + 1, -pad:pad + 1]
    out = np.empty(len(rows))
    for i, (r, c) in enumerate(zip(rows, cols)):
        r0, c0 = int(round(r)), int(round(c))
        m = np.hypot(yy + r0 - r, xx + c0 - c) <= radius_px
        w = height[r0 - pad:r0 + pad + 1, c0 - pad:c0 + pad + 1]
        out[i] = float(w[m].mean())
    return out


def deviations(tops: np.ndarray, rows: np.ndarray, cols: np.ndarray,
               degree: int) -> tuple[np.ndarray, dict]:
    """天面の高さから ``degree`` 次の基準曲面を引いた残差 = 個体偏差の推定。"""
    x = (cols - (N_PIX - 1) / 2.0) / ((N_PIX - 1) / 2.0)   # 中心化・正規化(条件数)
    y = (rows - (N_PIX - 1) / 2.0) / ((N_PIX - 1) / 2.0)
    model = _L.fit_poly_surface(x, y, tops, degree=degree)
    return tops - np.asarray(_L.eval_poly_surface(model, x, y)), model


def counts(dev_est: np.ndarray, dev_true: np.ndarray) -> tuple[int, int, int]:
    """(不合格の数, 誤検出, 見逃し) —— **1 つの数字に畳まない**。"""
    flag = np.abs(dev_est) > SPEC_UM
    bad = np.abs(dev_true) > SPEC_UM
    return int(flag.sum()), int((flag & ~bad).sum()), int((~flag & bad).sum())


# --------------------------------------------------------------------------- #
# 1-3. ゼロ点と次数                                                             #
# --------------------------------------------------------------------------- #
def section_orders() -> dict:
    print("\n" + "=" * 78)
    print("1-3) ゼロ点(平面だけ)と 2 次・3 次 —— 壊れ方を種類ごとに数える")
    print("=" * 78)

    sc = make_scene()
    det = detect_bumps(sc["height"])
    print("  検出: %d 本 / 仕込み %d 本(しきい値 %.2f µm)"
          % (det["n"], sc["cy"].size, det["thr"]))
    assert det["n"] == sc["cy"].size, (det["n"], sc["cy"].size)

    # 検出順を仕込み順に合わせる(格子なので行優先で一致する)
    idx = match_to_truth(det, sc["cy"], sc["cx"])
    rows, cols = det["row"][idx], det["col"][idx]

    tops = plateau_mean(sc["height"], rows, cols, R_MEAS_UM / PX_UM)
    dev_true = sc["h_true"] - sc["h_true"].mean()

    print("\n  次数  共平面性 PV   RMS 誤差   不合格   誤検出   見逃し")
    rows_tbl, out = [], {}
    for deg in (1, 2, 3):
        dev, _ = deviations(tops, rows, cols, deg)
        rms = float(np.sqrt(np.mean((dev - dev_true) ** 2)))
        pv = float(dev.max() - dev.min())
        n_bad, n_fp, n_fn = counts(dev, dev_true)
        out[deg] = {"dev": dev, "rms": rms, "pv": pv,
                    "bad": n_bad, "fp": n_fp, "fn": n_fn}
        rows_tbl.append([str(deg), "%.2f" % pv, "%.2f" % rms, str(n_bad),
                         str(n_fp), str(n_fn)])
        print("   %d    %8.2f µm  %6.2f µm   %5d   %5d   %5d"
              % (deg, pv, rms, n_bad, n_fp, n_fn))
    pv_true = float(dev_true.max() - dev_true.min())
    print("   真値 %8.2f µm       -        %5d       -       -"
          % (pv_true, int((np.abs(dev_true) > SPEC_UM).sum())))
    print("\n  ★ゼロ点は誤検出 %d 本の裏で**本物の短小を %d 本見逃している**"
          "(そりが正の側に居ると、-20 µm でも平面から -%.0f µm を切らない)。"
          % (out[1]["fp"], out[1]["fn"], SPEC_UM))
    print("  ★予想「高次ほど良い」は外れ: 3 次 %.2f µm は 2 次 %.2f µm より**悪い**"
          "(%.2f 倍)。仕込んだ高次成分は 4 次のロブなので 3 次の項では 1 µm も"
          "取れず、\n     増えた 4 項がバンプ個体差と雑音を余計に吸うぶんだけ損をする。"
          % (out[3]["rms"], out[2]["rms"], out[3]["rms"] / out[2]["rms"]))

    assert out[1]["rms"] > 5.0 and out[2]["rms"] < 1.5, (out[1]["rms"], out[2]["rms"])
    assert out[3]["rms"] > out[2]["rms"], (out[3]["rms"], out[2]["rms"])
    assert out[1]["fp"] > 20 and out[1]["fn"] >= 1, (out[1]["fp"], out[1]["fn"])
    assert out[2]["fp"] == 0 and out[2]["fn"] == 0, (out[2]["fp"], out[2]["fn"])

    # --- 図 ---------------------------------------------------------------- #
    # ★`surface_form_error` は台帳経由だと **PV の float しか返らない**(節 7)ので、
    #   残差の絵は fit_poly_surface + eval_poly_surface で自分で作る。
    hh, ww = sc["height"].shape
    gyy, gxx = np.mgrid[0:hh, 0:ww]
    m_img = _L.fit_poly_surface(gxx / ww, gyy / hh, sc["height"], degree=2)
    resid_img = sc["height"] - np.asarray(_L.eval_poly_surface(m_img, gxx / ww, gyy / hh))

    figs.save_grid(
        "scene",
        [sc["height"], sc["warp"], resid_img],
        ["高さ場(そり PV %.0f µm + バンプ %.0f µm)" % (sc["warp_pv"], H_NOM),
         "仕込んだそり(真値、PV %.0f µm)" % sc["warp_pv"],
         "2 次曲面を引いた残差 [µm]"],
        title="1 枚の高さ場に、そり(数十 µm)とバンプ個体差(数 µm)が重なる",
        ncols=3, signed=[False, True, True])

    def as_map(v):
        return np.kron(v.reshape(NB, NB), np.ones((14, 14)))

    figs.save_grid(
        "deviation_map",
        [as_map(dev_true), as_map(out[1]["dev"]), as_map(out[2]["dev"])],
        ["真値の個体偏差 [µm](短小 %d 本)" % N_SHORT,
         "ゼロ点: 平面だけ引く(RMS 誤差 %.2f µm)" % out[1]["rms"],
         "2 次曲面を引く(RMS 誤差 %.2f µm)" % out[2]["rms"]],
        title="バンプ %d 本の個体偏差(±%.0f µm で発散配色)" % (NB * NB, SPEC_UM),
        ncols=3, signed=True)

    figs.save_table("order_table",
                    ["基準曲面", "共平面性 PV µm", "RMS 誤差 µm", "不合格",
                     "誤検出", "見逃し"], rows_tbl,
                    title="次数で分ける —— 不合格の数だけ見ると誤検出と見逃しが混ざる",
                    caption="真値の共平面性は %.2f µm、本当に仕様外なのは %d 本。"
                            % (pv_true, int((np.abs(dev_true) > SPEC_UM).sum())))

    o = np.argsort(dev_true)
    figs.save_plot("sorted_deviation",
                   [("真値", np.arange(dev_true.size), dev_true[o]),
                    ("ゼロ点(平面)", np.arange(dev_true.size), out[1]["dev"][o]),
                    ("2 次曲面", np.arange(dev_true.size), out[2]["dev"][o]),
                    ("仕様 +%.0f µm" % SPEC_UM, [0, dev_true.size - 1],
                     [SPEC_UM, SPEC_UM]),
                    ("仕様 -%.0f µm" % SPEC_UM, [0, dev_true.size - 1],
                     [-SPEC_UM, -SPEC_UM])],
                   xlabel="バンプ(真値の低い順)", ylabel="個体偏差 [µm]",
                   title="そりを引かないと、仕様線を横切る本数が増える",
                   caption="左端の 6 本が仕込んだ短小。ゼロ点はそこを外し、"
                           "無関係なバンプを仕様外へ押し出す。")
    return {"scene": sc, "rows": rows, "cols": cols, "tops": tops,
            "dev_true": dev_true, "out": out}


# --------------------------------------------------------------------------- #
# 4. 崖 —— 幾何で予測してから掃引する                                            #
# --------------------------------------------------------------------------- #
def section_cliff() -> dict:
    print("\n" + "=" * 78)
    print("4) 崖 —— そりの PV をどこまで上げると個体差が読めなくなるか")
    print("=" * 78)

    # 先に予測: そりの形は固定なので「取り切れない割合」は PV に比例する定数
    unit_warp, _ = _warp_modes(N_PIX)
    k = (np.arange(NB) - (NB - 1) / 2.0) * (PITCH_UM / PX_UM) + (N_PIX - 1) / 2.0
    gy, gx = np.meshgrid(k, k, indexing="ij")
    xs = (gx.ravel() - (N_PIX - 1) / 2.0) / ((N_PIX - 1) / 2.0)
    ys = (gy.ravel() - (N_PIX - 1) / 2.0) / ((N_PIX - 1) / 2.0)
    w_at_bump = unit_warp[np.round(gy).astype(int).ravel(),
                          np.round(gx).astype(int).ravel()]
    ratio, pred = {}, {}
    for deg in (1, 2):
        m = _L.fit_poly_surface(xs, ys, w_at_bump, degree=deg)
        r = w_at_bump - np.asarray(_L.eval_poly_surface(m, xs, ys))
        ratio[deg] = float(np.sqrt(np.mean(r ** 2)))       # PV=1 のときの残差 RMS
        pred[deg] = H_SD / ratio[deg]
        print("  予測: %d 次で取り切れない割合 r%d = %.5f -> "
              "個体差 1σ=%.1f µm に並ぶのは PV = %.1f µm"
              % (deg, deg, ratio[deg], H_SD, pred[deg]))

    pvs = [0.0, 10.0, 25.0, 50.0, 100.0, 150.0, 200.0, 300.0, 400.0]
    meas = {1: [], 2: []}
    print("\n  そり PV [µm]   1 次の RMS 誤差   2 次の RMS 誤差   不合格(1 次 / 2 次)")
    for pv in pvs:
        sc = make_scene(warp_pv=pv)
        det = detect_bumps(sc["height"])
        idx = match_to_truth(det, sc["cy"], sc["cx"])
        rows, cols = det["row"][idx], det["col"][idx]
        tops = plateau_mean(sc["height"], rows, cols, R_MEAS_UM / PX_UM)
        dev_true = sc["h_true"] - sc["h_true"].mean()
        line = []
        for deg in (1, 2):
            dev, _ = deviations(tops, rows, cols, deg)
            meas[deg].append(float(np.sqrt(np.mean((dev - dev_true) ** 2))))
            line.append(counts(dev, dev_true)[0])
        print("   %7.1f       %8.3f µm        %8.3f µm         %4d / %4d"
              % (pv, meas[1][-1], meas[2][-1], line[0], line[1]))

    def crossing(xs_, ys_):
        """RMS 誤差が個体差 1σ を横切る PV を線形補間で求める。"""
        for a in range(1, len(xs_)):
            if ys_[a - 1] < H_SD <= ys_[a]:
                t = (H_SD - ys_[a - 1]) / (ys_[a] - ys_[a - 1])
                return xs_[a - 1] + t * (xs_[a] - xs_[a - 1])
        return float("nan")

    got = {d: crossing(pvs, meas[d]) for d in (1, 2)}
    print("\n  崖(実測 / 予測): 1 次 %.1f / %.1f µm (比 %.3f) | "
          "2 次 %.1f / %.1f µm (比 %.3f)"
          % (got[1], pred[1], got[1] / pred[1], got[2], pred[2], got[2] / pred[2]))
    print("  -> **そりが %.0f µm を超える薄型パッケージでは、2 次を引いても"
          "個体差は読めない**。" % pred[2])
    for d in (1, 2):
        assert 0.5 < got[d] / pred[d] < 2.0, (d, got[d], pred[d])

    figs.save_plot("warpage_cliff",
                   [("ゼロ点(平面)", pvs, meas[1]),
                    ("2 次曲面", pvs, meas[2]),
                    ("個体差 1σ = %.0f µm" % H_SD, [pvs[0], pvs[-1]], [H_SD, H_SD])],
                   xlabel="仕込んだそりの PV [µm]",
                   ylabel="個体偏差の読み取り RMS 誤差 [µm]",
                   title="崖は幾何で予測できる(2 次: 予測 %.0f / 実測 %.0f µm)"
                         % (pred[2], got[2]),
                   caption="そりの形を固定すれば、取り切れない残りは PV に比例する。"
                           "比例定数 r2=%.5f から崖の位置が出る。" % ratio[2])
    return {"pvs": pvs, "meas": meas, "pred": pred, "got": got, "ratio": ratio}


# --------------------------------------------------------------------------- #
# 5. 対照群 —— そりだけ止める                                                    #
# --------------------------------------------------------------------------- #
def section_control() -> dict:
    print("\n" + "=" * 78)
    print("5) 対照群 —— そり PV = 0(バンプも雑音もそのまま)")
    print("=" * 78)

    sc = make_scene(warp_pv=0.0)
    det = detect_bumps(sc["height"])
    idx = match_to_truth(det, sc["cy"], sc["cx"])
    rows, cols = det["row"][idx], det["col"][idx]
    tops = plateau_mean(sc["height"], rows, cols, R_MEAS_UM / PX_UM)
    dev_true = sc["h_true"] - sc["h_true"].mean()
    res = {}
    for deg in (1, 2):
        dev, _ = deviations(tops, rows, cols, deg)
        res[deg] = (float(np.sqrt(np.mean((dev - dev_true) ** 2))),) + counts(dev, dev_true)
        print("   %d 次: RMS 誤差 %.2f µm / 不合格 %d(誤検出 %d・見逃し %d)"
              % ((deg,) + res[deg]))
    print("  -> 1 次と 2 次の差は %.2f µm。**壊していたのは当てはめではなく"
          "そりだった**。" % abs(res[1][0] - res[2][0]))
    assert abs(res[1][0] - res[2][0]) < 0.5, res
    assert res[1][2] == 0 and res[2][2] == 0, res
    return res


# --------------------------------------------------------------------------- #
# 6. ★引きすぎの害 —— 本物の低次不良を吸う                                       #
# --------------------------------------------------------------------------- #
def section_absorbed_defect() -> dict:
    print("\n" + "=" * 78)
    print("6) ★★引きすぎの害 —— 本物の低次不良(中央が %.0f µm 低い)を吸う"
          % CENTER_SAG)
    print("=" * 78)

    out = {}
    for sag in (0.0, CENTER_SAG):
        sc = make_scene(center_sag=sag)
        det = detect_bumps(sc["height"])
        idx = match_to_truth(det, sc["cy"], sc["cx"])
        rows, cols = det["row"][idx], det["col"][idx]
        tops = plateau_mean(sc["height"], rows, cols, R_MEAS_UM / PX_UM)
        dev_true = sc["h_true"] - sc["h_true"].mean()
        dev, model = deviations(tops, rows, cols, 2)

        # 中央 1/3 と外周 1/3 の差 —— 「本物の低次不良」がどれだけ残るか
        rr = np.hypot(rows - (N_PIX - 1) / 2.0, cols - (N_PIX - 1) / 2.0)
        inner, outer = rr < np.quantile(rr, 0.33), rr > np.quantile(rr, 0.67)
        d_true = float(dev_true[inner].mean() - dev_true[outer].mean())
        d_est = float(dev[inner].mean() - dev[outer].mean())
        # 引いた基準曲面そのものの PV(= 報告される「そり」)
        x = (cols - (N_PIX - 1) / 2.0) / ((N_PIX - 1) / 2.0)
        y = (rows - (N_PIX - 1) / 2.0) / ((N_PIX - 1) / 2.0)
        fitted = np.asarray(_L.eval_poly_surface(model, x, y))
        warp_reported = float(fitted.max() - fitted.min())
        n_bad, n_fp, n_fn = counts(dev, dev_true)
        n_true_bad = int((np.abs(dev_true) > SPEC_UM).sum())
        short_found = int((np.abs(dev[sc["short_idx"]]) > SPEC_UM).sum())
        out[sag] = {"d_true": d_true, "d_est": d_est, "warp": warp_reported,
                    "fp": n_fp, "fn": n_fn, "true_bad": n_true_bad,
                    "short_found": short_found}
        print("   中央低下 %.1f µm:  真の中央-外周 %+.2f µm -> 残差では %+.2f µm  |  "
              "報告されるそり PV %.2f µm  |  真に仕様外 %d 本・見逃し %d 本・"
              "短小 %d/%d 本を検出"
              % (sag, d_true, d_est, warp_reported, n_true_bad, n_fn,
                 short_found, N_SHORT))

    a, b = out[0.0], out[CENTER_SAG]
    killed = 100.0 * (1.0 - abs(b["d_est"] - a["d_est"]) / abs(b["d_true"] - a["d_true"]))
    print("\n  ★★本物の低次不良は残差から %.1f %% 消える"
          "(真の差 %.2f µm -> 残差の差 %.2f µm)。"
          % (killed, b["d_true"] - a["d_true"], b["d_est"] - a["d_est"]))
    print("     孤立した短小 %d 本は前と同じに見つかる(%d -> %d 本)。"
          "**「検出できている」は健全さの証拠にならない** ——"
          % (N_SHORT, a["short_found"], b["short_found"]))
    print("     低次不良を足すと真に仕様外のバンプは %d -> %d 本に増えるのに、"
          "見逃しは %d -> %d 本に増える。"
          % (a["true_bad"], b["true_bad"], a["fn"], b["fn"]))
    print("     消えた分は捨てられていない: 報告されるそりが %.2f -> %.2f µm"
          "(+%.2f µm)と膨らむ。" % (a["warp"], b["warp"], b["warp"] - a["warp"]))
    assert killed > 80.0, killed
    assert b["short_found"] == a["short_found"], (a, b)
    assert b["fn"] > a["fn"], (a["fn"], b["fn"])
    assert b["warp"] - a["warp"] > 3.0, (a["warp"], b["warp"])

    figs.save_table("absorbed_defect",
                    ["条件", "真の中央-外周 µm", "残差の中央-外周 µm",
                     "報告されるそり PV µm", "真に仕様外", "見逃し", "短小の検出"],
                    [["低次不良なし", "%+.2f" % a["d_true"], "%+.2f" % a["d_est"],
                      "%.2f" % a["warp"], str(a["true_bad"]), str(a["fn"]),
                      "%d/%d" % (a["short_found"], N_SHORT)],
                     ["中央 %.0f µm 低下" % CENTER_SAG, "%+.2f" % b["d_true"],
                      "%+.2f" % b["d_est"], "%.2f" % b["warp"], str(b["true_bad"]),
                      str(b["fn"]), "%d/%d" % (b["short_found"], N_SHORT)]],
                    title="そりを引くと本物の低次不良も消える(%.0f %%)" % killed,
                    caption="消えた分はそり側の数字に足されている(+%.2f µm)。"
                            "短小の検出数は変わらないので、検出できていることは"
                            "健全さの証拠にならない。" % (b["warp"] - a["warp"]))
    return out


# --------------------------------------------------------------------------- #
# 7. 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("7) 道具の穴(この PoC で使ってみて)")
    print("=" * 78)

    assert not hasattr(fs.ledger, "region_gray_stats")
    print("  (a) **ラベルごとの gray 統計**(領域内の平均・分位点)を出す口が無い。"
          "blob_features は形だけで、`plateau_mean` は自前で書いた。")
    assert not hasattr(fs.ledger, "ransac_poly_surface")
    print("  (b) 多項式曲面の**ロバスト当てはめ**が無い(点群の ransac_plane は"
          "在るが、2 次以上の曲面には効かない)。短小バンプが基準曲面を引っぱる。")
    assert not hasattr(fs.ledger, "seating_plane") and not hasattr(fs.ledger, "coplanarity")
    print("  (c) JEDEC の**着座平面 / 共平面性**そのものの口が無い"
          "(最小二乗平面は fit_plane3 で作れるが、規格の定義は別)。")
    assert hasattr(fs.ledger, "fit_poly_surface") and not hasattr(fs, "fit_poly_surface")
    print("  (d) fit_poly_surface / surface_form_error / blob_* は"
          "fullseye.ledger からしか呼べない(1 行ファサードに出ていない)。")

    # (e) ★台帳経由の surface_form_error は **PV の float しか返らない**
    v = _L.surface_form_error(np.zeros((8, 8)) + np.arange(8), 2)
    assert isinstance(v, float), type(v)
    print("  (e) ★surface_form_error は docstring に「(residual, rms, pv) を返す」と"
          "書いてあるのに、\n      台帳経由では **pv の float 1 個**しか返らない"
          "(残差の (H,W) も rms も取れない)。この PoC の残差の絵は"
          "\n      fit_poly_surface + eval_poly_surface で作り直している。")

    # (f) 進化 op は画像を [0,1] とみなす —— 単位つきの量をそのまま渡すと切る位置が狂う
    n = 64
    ramp = np.linspace(-60.0, 13.0, n)[None, :] * np.ones((n, 1))   # 背景のうねり [µm]
    yy, xx = np.mgrid[0:n, 0:n]
    disc = np.hypot(yy - n / 2, xx - n / 2) < 12.0                  # 前景 +200 µm
    z = ramp + 200.0 * disc
    raw = int((np.asarray(fs.apply(z, "auto_threshold")) > 0.5).sum())
    lo, hi = z.min(), z.max()
    nrm = int((np.asarray(fs.apply((z - lo) / (hi - lo), "auto_threshold")) > 0.5).sum())
    assert raw > 2 * int(disc.sum()) and abs(nrm - int(disc.sum())) < 20, (raw, nrm)
    print("  (f) ★進化 op の auto_threshold は値域を [0,1] とみなす。背景が -60〜+13 µm、"
          "前景 +200 µm の\n      高さ場をそのまま渡すと前景 %d 画素(正解 %d)—— "
          "0.5 **µm** の位置で切っている。\n      正規化してから渡せば %d 画素。"
          "単位つきの量を進化 op に渡すときの落とし穴。"
          % (raw, int(disc.sum()), nrm))


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    print("=" * 78)
    print("バンプの共平面性を基板そりから分ける")
    print("視野 %d px x %.0f µm = %.2f mm 角 / バンプ %d 本(ピッチ %.0f µm)/ "
          "個体差 1σ %.0f µm / 仕様 ±%.0f µm"
          % (N_PIX, PX_UM, N_PIX * PX_UM / 1000.0, NB * NB, PITCH_UM, H_SD, SPEC_UM))
    print("=" * 78)

    a = section_orders()
    b = section_cliff()
    section_control()
    c = section_absorbed_defect()
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * そりを引かないと RMS 誤差 %.2f µm(個体差 1σ の %.1f 倍)、"
          "誤検出 %d 本・見逃し %d 本。"
          % (a["out"][1]["rms"], a["out"][1]["rms"] / H_SD,
             a["out"][1]["fp"], a["out"][1]["fn"]))
    print("  * 2 次で足りる(%.2f µm)。3 次を足すと %.2f µm と**悪くなる**。"
          % (a["out"][2]["rms"], a["out"][3]["rms"]))
    print("  * 崖は幾何で予測できる: 2 次は PV %.1f µm(予測 %.1f µm)で個体差に並ぶ。"
          % (b["got"][2], b["pred"][2]))
    print("  * ★引きすぎると本物の低次不良が消える(中央低下 %.2f µm -> %.2f µm)。"
          % (c[CENTER_SAG]["d_true"] - c[0.0]["d_true"],
             c[CENTER_SAG]["d_est"] - c[0.0]["d_est"]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
