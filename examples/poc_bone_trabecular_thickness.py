# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""骨梁の厚さ Tb.Th・間隔 Tb.Sp・骨体積率 BV/TV を断面から測る —— 平板モデルと直接法は同じ画像で別の値になる。

骨のマイクロ CT 断面(または骨生検の組織切片)から骨粗鬆症の指標を出す仕事です。
平均の骨梁厚 Tb.Th、骨梁の間隔 Tb.Sp、骨体積率 BV/TV(= 骨の面積率)の 3 つが
報告書に載ります。Tb.Th には**平板モデル**(BV/BS から: Tb.Th = 2·BV/BS)と
**直接法**(Hildebrand & Rüegsegger 流: 各画素を含む最大内接円の直径)の 2 つの
定義があり、**同じ画像で違う値になる**のに、論文では同じ名前で書かれます。

EXTEND: 実データに差し替えるなら :func:`make_master` が返す辞書の ``master``
(2.5 µm の真値二値像)を、高解像度スキャン(真値側)の二値像に、:func:`observe`
を実際の低解像度スキャンに置き換えます。**真値スキャンは測定スキャンより
少なくとも 4 倍細かい解像度が要ります** —— この PoC の主張は「画素の粗さと
しきい値で厚さがどう動くか」なので、真値側が同じ粗さでは測れません。
組織切片を真値にする場合、切片の厚さ方向の斜め切り(oblique sectioning)で
幅が 1/cos θ 倍に見える分を先に補正すること。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **真値そのものが 2 つある**。閉形式(帯の幅の長さ加重平均)の Tb.Th は
   117.6 µm、距離変換の定義(最大内接円)で真値二値像から出すと 123.4 µm で
   **+4.9 %** —— 交点では内接円が帯より太るので、定義どおりに測っても
   「描いた幅」には戻らない。平板モデルは同じ真値像で 108.7 µm(-7.6 %)。
   **モデルの差 12 %、しきい値の差より大きい**。
2. ★**解像度の崖は「平均」には来なかった。「分布」に来た**。画素 10 → 60 µm
   (1 骨梁 = 12 → 2 px)で直接法 Tb.Th は 123.9 → 122.7 µm と 1 % しか動かず、
   平板モデルも 106.1 → 108.7 µm。予想は「細い骨梁が部分体積で消えて厚い側だけ
   残る生存バイアス」だったが、消えた骨梁の面積は 60 µm でも 0.6 % で外れた。
   代わりに厚さの分布が 60 µm では 60 / 180 µm の 2 本の棒に潰れ、
   真値分布との重なりが 0.94 → 0.35 に落ちる —— 平均が合っているのは
   -0.5 px の量子化と +0.5 px の丸めが打ち消しているから。
3. ★★**雑音の崖は 2 方向から来る**。σ = 0.10 で斑点(骨と誤認した孤立画素)が
   0 → 52 個、σ = 0.20 で骨梁の途切れが 0 → 12 本。斑点は Tb.Sp を
   **小さく**(内接円を切る)、途切れは Tb.Sp を**大きく**(隣の髄腔と繋がる)
   引く。予想(斑点は σ ≈ 0.11 から、途切れはそれより後)と実測は一致した。
   ★opening r=1 は斑点を全部消すが**2 px の骨梁も一緒に消して**途切れが
   12 → 64 本に増える。面積オープニング(16 px)は斑点だけを消す。
4. **しきい値 ±10 % で BV/TV と Tb.Th は同じ向きに動く**(0.45 → 0.55 で
   BV/TV -5.4 % → +5.6 %、Tb.Th 直接 -7.9 % → +6.0 %)。予想の「逆向き」は
   外れた —— 消える骨梁が無いので生存バイアスが働かず、単に帯が痩せる。
   ただし Tb.N(骨梁数)は逆向きに動く(BV/TV ÷ Tb.Th なので)。
5. **ビームハードニング(カップ状の低周波バイアス)は大津 1 本を壊す**。
   バイアス 30 % で BV/TV が -8.6 %、中心と縁で Tb.Th が 15 % 違う。
   retinex(局所平均で割る)→ 大津で -0.5 % に戻る。対照群(バイアスだけ
   止める)で -1.0 % なので、残りの誤差は雑音とぼけ。

【グラウンドトゥルース】
2-D 骨梁網は**線分の集合**(格子 + ランダム方向)で、各線分に幅を持たせて
2.5 µm の格子に描く(閉形式: 画素中心から線分までの距離 ≤ 幅/2)。幅は対数正規で
中央値 120 µm、[50, 240] µm に切り詰め。真値は (a) 幅の長さ加重平均(閉形式)と
(b) 5 µm の真値二値像に距離変換の定義を当てた局所厚さ、の 2 つを別々に持つ。
観測は部分体積(ブロック平均)→ PSF(σ = 0.7 px のガウス)→ カップ状の
乗算バイアス → 白色雑音。

来歴(公開文献のみ): Hildebrand & Rüegsegger, *J. Microscopy* 185 (1997) 67 ——
最大内接球による直接法 / Parfitt et al., *J. Bone Miner. Res.* 2 (1987) 595 ——
組織形態計測の命名と平板モデル / Bouxsein et al., *J. Bone Miner. Res.* 25
(2010) 1468 —— µCT 骨微細構造の報告ガイドライン。
"""
from __future__ import annotations

import sys
import time
from math import erf, sqrt
from pathlib import Path

import numpy as np
from scipy import ndimage, special

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
FIELD_UM = 6000.0        # 視野 [µm] 角
MASTER_UM = 2.5          # 真値を描く格子 [µm/px] -> 2400 px 角
TRUTH_UM = 5.0           # 距離変換の定義で真値厚さを出す格子 [µm/px]
PX_LIST = (10.0, 15.0, 20.0, 30.0, 40.0, 60.0)   # 測定の画素 [µm/px]
W_MED, W_SIG, W_LO, W_HI = 120.0, 0.35, 50.0, 240.0   # 帯の幅 [µm]
GRID_UM = 1100.0         # 格子の間隔 [µm]
N_RANDOM = 8             # ランダム方向の線分
PSF_SIGMA_PX = 0.7       # PSF [px](画素に比例 = 装置の分解能はボクセルに追随)
NOISE_SIGMA = 0.15       # 既定の雑音(骨 = 1、髄 = 0)
BIAS_BETA = 0.30         # カップ状バイアスの深さ
MARROW_LEVEL = 0.15      # 髄腔の CT 値(骨を 1 として)
SEED = 7

_LAB = fs.ledger         # blob 族の公開経路


# --------------------------------------------------------------------------- #
# 場面 —— 真値は線分の幅の一覧と、2.5 µm の二値像                                #
# --------------------------------------------------------------------------- #
def make_master(seed: int = SEED) -> dict:
    """格子 + ランダム線分の骨梁網を 2.5 µm の格子に描く。"""
    rng = np.random.default_rng(seed)
    n = int(round(FIELD_UM / MASTER_UM))
    segs = []      # (x0, y0, x1, y1, w)

    def width() -> float:
        return float(np.clip(W_MED * np.exp(W_SIG * rng.standard_normal()), W_LO, W_HI))

    # 格子(位置に揺らぎ、少し傾ける)
    n_line = int(FIELD_UM // GRID_UM)
    for k in range(n_line):
        base = GRID_UM * (k + 0.5) + rng.uniform(-120, 120)
        tilt = rng.uniform(-150, 150)
        segs.append((-100.0, base - tilt, FIELD_UM + 100.0, base + tilt, width()))
        base = GRID_UM * (k + 0.5) + rng.uniform(-120, 120)
        tilt = rng.uniform(-150, 150)
        segs.append((base - tilt, -100.0, base + tilt, FIELD_UM + 100.0, width()))
    # ランダム方向の骨梁
    for _ in range(N_RANDOM):
        cx, cy = rng.uniform(600, FIELD_UM - 600, 2)
        ang = rng.uniform(0, np.pi)
        half = rng.uniform(600, 1100)
        segs.append((cx - half * np.cos(ang), cy - half * np.sin(ang),
                     cx + half * np.cos(ang), cy + half * np.sin(ang), width()))

    master = np.zeros((n, n), bool)
    coords = (np.arange(n) + 0.5) * MASTER_UM
    for x0, y0, x1, y1, w in segs:
        r = w / 2.0 + MASTER_UM
        lo_x = max(0, int((min(x0, x1) - r) / MASTER_UM))
        hi_x = min(n, int((max(x0, x1) + r) / MASTER_UM) + 2)
        lo_y = max(0, int((min(y0, y1) - r) / MASTER_UM))
        hi_y = min(n, int((max(y0, y1) + r) / MASTER_UM) + 2)
        if hi_x <= lo_x or hi_y <= lo_y:
            continue
        xs = coords[lo_x:hi_x][None, :]
        ys = coords[lo_y:hi_y][:, None]
        dx, dy = x1 - x0, y1 - y0
        t = np.clip(((xs - x0) * dx + (ys - y0) * dy) / (dx * dx + dy * dy), 0.0, 1.0)
        d = np.hypot(xs - (x0 + t * dx), ys - (y0 + t * dy))
        master[lo_y:hi_y, lo_x:hi_x] |= d <= w / 2.0

    # 閉形式の真値: 幅の長さ加重平均(視野内の長さで重みづけ)
    lengths, widths = [], []
    t = (np.arange(4000) + 0.5) / 4000.0
    for x0, y0, x1, y1, w in segs:
        xs, ys = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
        inside = (xs >= 0) & (xs <= FIELD_UM) & (ys >= 0) & (ys <= FIELD_UM)
        lengths.append(float(np.hypot(x1 - x0, y1 - y0) * inside.mean()))
        widths.append(w)
    lengths, widths = np.asarray(lengths), np.asarray(widths)
    return {"master": master, "segs": segs,
            "width_mean_closed": float(np.sum(lengths * widths) / np.sum(lengths)),
            "widths": widths, "bvtv": float(master.mean())}


def block_mean(a: np.ndarray, k: int) -> np.ndarray:
    """k×k のブロック平均(部分体積効果そのもの)。"""
    n = a.shape[0] // k
    return a[:n * k, :n * k].reshape(n, k, n, k).mean(axis=(1, 3))


def observe(master: np.ndarray, px_um: float, *, blur: bool = True,
            noise: float = NOISE_SIGMA, bias: float = 0.0, seed: int = SEED) -> np.ndarray:
    """真値二値像 → 観測画像。部分体積 → PSF → バイアス → 雑音の順。"""
    k = int(round(px_um / MASTER_UM))
    assert abs(k * MASTER_UM - px_um) < 1e-9, "画素は 2.5 µm の整数倍にすること"
    img = block_mean(master.astype(np.float64), k)
    img = MARROW_LEVEL + (1.0 - MARROW_LEVEL) * img
    if blur:
        img = np.asarray(fs.apply(img, "gaussian", a=(PSF_SIGMA_PX - 0.3) / 2.7))
    if bias > 0.0:
        n = img.shape[0]
        yy, xx = np.mgrid[0:n, 0:n]
        r2 = ((yy - n / 2.0) ** 2 + (xx - n / 2.0) ** 2) / (2.0 * (n / 2.0) ** 2)
        img = img * (1.0 - bias * (1.0 - r2))       # 中心が暗い = カッピング
    if noise > 0.0:
        rng = np.random.default_rng(seed + int(px_um))
        img = img + noise * rng.standard_normal(img.shape)
    return img


# --------------------------------------------------------------------------- #
# 直接法 —— 最大内接円の直径(Hildebrand & Rüegsegger)                          #
# --------------------------------------------------------------------------- #
def _radii(r_max: int) -> list[int]:
    """試す半径。32 px までは全部、それより上は 3 % 刻み(値がその刻みに量子化される)。"""
    out = list(range(1, min(r_max, 32) + 1))
    r = 32.0
    while r < r_max:
        r = max(r + 1.0, r * 1.03)
        out.append(int(round(r)))
    return sorted(set(x for x in out if x <= r_max))


def local_thickness(mask: np.ndarray) -> np.ndarray:
    """各前景画素について「その画素を含む最大内接円の直径」[px]。

    半径 r の内接円の中心 = 距離変換 ≥ r の画素。その中心から r - 0.5 以内の
    画素が直径 2r - 1 の円に覆われる。大きい r から順に上書きすると最大値になる。
    距離変換は fullseye の ``blob_distance``(画素単位)。
    """
    mask = np.asarray(mask, bool)
    edt = np.asarray(_LAB.blob_distance(mask), np.float64)
    out = np.zeros(mask.shape, np.float64)
    r_max = int(edt.max())
    if r_max == 0:
        return out
    for r in _radii(r_max):
        centers = edt >= r
        if not centers.any():
            break
        cover = np.asarray(_LAB.blob_distance(~centers), np.float64) <= r - 0.5
        out[(cover | centers) & mask] = 2.0 * r - 1.0
    return out


def direct_metrics(mask: np.ndarray, px_um: float) -> dict:
    """直接法の Tb.Th / Tb.Sp と、局所厚さの分布。"""
    th = local_thickness(mask)
    sp = local_thickness(~mask)
    return {"tbth": float(th[mask].mean()) * px_um,
            "tbsp": float(sp[~mask].mean()) * px_um,
            "th_map": th * px_um, "sp_map": sp * px_um,
            "th_values": th[mask] * px_um}


def plate_metrics(mask: np.ndarray, px_um: float) -> dict:
    """平板モデル: Tb.Th = 2·BV/BS、Tb.Sp = 2·(TV-BV)/BS、Tb.N = 1/(Tb.Th+Tb.Sp)。"""
    lab = _LAB.blob_label(mask)
    f = _LAB.blob_features(lab)
    area = float(np.sum(f["area"]))
    perim = float(np.sum(f["perimeter"]))
    tv = float(mask.size)
    if perim <= 0:
        return {"tbth": np.nan, "tbsp": np.nan, "tbn": np.nan, "n_blobs": 0}
    tbth = 2.0 * area / perim * px_um
    tbsp = 2.0 * (tv - area) / perim * px_um
    return {"tbth": tbth, "tbsp": tbsp, "tbn": 1.0 / (tbth + tbsp),
            "n_blobs": int(f["n"])}


def hist_overlap(a: np.ndarray, b: np.ndarray, edges: np.ndarray) -> float:
    """2 つの厚さ分布のヒストグラム重なり(1 = 同じ分布)。"""
    ha, _ = np.histogram(a, bins=edges)
    hb, _ = np.histogram(b, bins=edges)
    ha = ha / max(ha.sum(), 1)
    hb = hb / max(hb.sum(), 1)
    return float(np.minimum(ha, hb).sum())


def truth_at(master: np.ndarray, px_um: float) -> np.ndarray:
    """同じ画素で見た真値二値像(ブロック平均 ≥ 0.5)。"""
    return block_mean(master.astype(np.float64), int(round(px_um / MASTER_UM))) >= 0.5


# --------------------------------------------------------------------------- #
# 1. 真値が 2 つある —— 閉形式・定義・平板モデル                                #
# --------------------------------------------------------------------------- #
def section_truths(sc: dict) -> dict:
    print("\n" + "=" * 78)
    print("1) 真値そのものが 2 つある —— 閉形式(描いた幅)と定義(最大内接円)")
    print("=" * 78)
    tb = truth_at(sc["master"], TRUTH_UM)
    d = direct_metrics(tb, TRUTH_UM)
    p = plate_metrics(tb, TRUTH_UM)
    closed = sc["width_mean_closed"]
    print("  BV/TV(真値 2.5 µm)          %.4f" % sc["bvtv"])
    print("  Tb.Th 閉形式(幅の長さ加重)   %.1f µm" % closed)
    print("  Tb.Th 定義(最大内接円, 5 µm) %.1f µm  (閉形式比 %+.1f %%)" % (
        d["tbth"], 100 * (d["tbth"] / closed - 1)))
    print("  Tb.Th 平板モデル 2·BV/BS      %.1f µm  (閉形式比 %+.1f %%)" % (
        p["tbth"], 100 * (p["tbth"] / closed - 1)))
    print("  Tb.Sp 定義 %.0f µm / 平板 %.0f µm / Tb.N 平板 %.2f /mm" % (
        d["tbsp"], p["tbsp"], 1000 * p["tbn"]))
    print("  → 交点で内接円が帯より太る(定義 > 閉形式)。平板モデルは交点で"
          "周長が減る分と\n    斜め帯の画素周長の分で別の値。**モデルの差 %.0f %%**。"
          % (100 * (d["tbth"] - p["tbth"]) / closed))
    figs.save_grid("scene_truth",
                   [tb.astype(np.float64), d["th_map"], d["sp_map"]],
                   ["真値二値像(5 µm/px、BV/TV %.1f %%)" % (100 * sc["bvtv"]),
                    "局所厚さ Tb.Th [µm]、平均 %.0f" % d["tbth"],
                    "局所間隔 Tb.Sp [µm]、平均 %.0f" % d["tbsp"]],
                   title="骨梁網の真値と距離変換の定義による厚さ・間隔", ncols=3)
    return {"truth_bin": tb, "direct": d, "plate": p, "closed": closed}


# --------------------------------------------------------------------------- #
# 2. 解像度の崖 —— 1 骨梁 = 12 → 2 px                                          #
# --------------------------------------------------------------------------- #
def section_resolution(sc: dict, tr: dict) -> dict:
    print("\n" + "=" * 78)
    print("2) 解像度の崖 —— 画素 10 → 60 µm(1 骨梁 = 12 → 2 px)")
    print("=" * 78)
    closed, t_def = tr["closed"], tr["direct"]["tbth"]
    # 予想: 幅 w の帯は峰 erf(w/(2√2 σ_eff)) が 0.5 を切ると消える。
    #   σ_eff² = (0.7 px)² + (1/12) px²(箱積分)→ w_c = 1.349 σ_eff
    sig_eff = sqrt(PSF_SIGMA_PX ** 2 + 1.0 / 12.0)
    w_c_px = 2.0 * sqrt(2.0) * sig_eff * float(special.erfinv(0.5))
    widths = sc["widths"]
    print("  予想: 消える幅 w_c = %.2f px。帯の最小幅 %.0f µm なので 60 µm 画素でも"
          " w_c = %.0f µm < 最小幅 → 生存バイアスは効かないはず。" % (
              w_c_px, widths.min(), w_c_px * 60))
    print("  予想: 量子化 -0.5 px(2r-1 の規約)が平均を引く: 10 µm で -4 %%、60 µm で -25 %%。")
    print("\n  画素   px/骨梁  BV/TV      Tb.Th 直接      Tb.Th 平板     Tb.Sp 直接   消えた骨  分布の重なり")
    edges = np.arange(0, 400, 20.0)
    rows, px_ax, e_dir, e_plate, e_sp, ovl = [], [], [], [], [], []
    keep = {}
    for px in PX_LIST:
        img = observe(sc["master"], px, noise=NOISE_SIGMA)
        mask = np.asarray(fs.apply(img, "otsu")) > 0.5
        tb = truth_at(sc["master"], px)
        d = direct_metrics(mask, px)
        p = plate_metrics(mask, px)
        bvtv = float(mask.mean())
        # 消えた骨: 真値の骨のうち、測定マスクに写らなかった連結片の面積割合
        lost = tb & ~mask
        lost_lab = _LAB.blob_label(lost)
        lf = _LAB.blob_features(lost_lab)
        # 骨梁ごと消えた = 太さ方向に全部消えた片(= 真値の骨片で測定に骨が 1 画素も無い)
        gone = 0.0
        tlab = _LAB.blob_label(tb)
        for k in range(1, int(tlab.max()) + 1):
            reg = tlab == k
            if not mask[reg].any():
                gone += float(reg.sum())
        gone_frac = gone / max(float(tb.sum()), 1.0)
        o = hist_overlap(tr["direct"]["th_values"], d["th_values"], edges)
        rows.append([("%.0f" % px), "%.1f" % (closed / px), "%+.1f %%" % (100 * (bvtv / sc["bvtv"] - 1)),
                     "%.1f (%+.1f %%)" % (d["tbth"], 100 * (d["tbth"] / t_def - 1)),
                     "%.1f (%+.1f %%)" % (p["tbth"], 100 * (p["tbth"] / t_def - 1)),
                     "%.0f (%+.1f %%)" % (d["tbsp"], 100 * (d["tbsp"] / tr["direct"]["tbsp"] - 1)),
                     "%.1f %%" % (100 * gone_frac), "%.2f" % o])
        print("  %4.0f   %5.1f   %+6.1f %%   %6.1f (%+5.1f %%)   %6.1f (%+5.1f %%)   %5.0f (%+5.1f %%)   %5.1f %%    %.2f" % (
            px, closed / px, 100 * (bvtv / sc["bvtv"] - 1), d["tbth"], 100 * (d["tbth"] / t_def - 1),
            p["tbth"], 100 * (p["tbth"] / t_def - 1), d["tbsp"], 100 * (d["tbsp"] / tr["direct"]["tbsp"] - 1),
            100 * gone_frac, o))
        px_ax.append(px)
        e_dir.append(100 * (d["tbth"] / t_def - 1))
        e_plate.append(100 * (p["tbth"] / t_def - 1))
        e_sp.append(100 * (d["tbsp"] / tr["direct"]["tbsp"] - 1))
        ovl.append(o)
        if px in (10.0, 60.0):
            keep[px] = {"img": img, "mask": mask, "d": d, "gone": gone_frac, "lost": int(lf["n"])}

    # 分布: 60 µm は何本の棒になるか
    v60 = keep[60.0]["d"]["th_values"]
    uniq = np.unique(np.round(v60, 3))
    print("\n  ★60 µm の厚さの値は %d 通り(%s µm)。平均が真値に近いのは"
          "\n    -0.5 px の量子化(2r-1)と、2 px の帯が 1 px と 3 px に割れる丸めが打ち消すから。"
          % (len(uniq), ", ".join("%.0f" % u for u in uniq[:6])))
    print("  ★予想「生存バイアス」は %s: 消えた骨は 60 µm で %.1f %%。" % (
        "外れ" if keep[60.0]["gone"] < 0.05 else "当たり", 100 * keep[60.0]["gone"]))

    figs.save_plot("resolution_sweep",
                   [("Tb.Th 直接法(大津 + 最大内接円)", px_ax, e_dir),
                    ("Tb.Th 平板モデル 2·BV/BS", px_ax, e_plate),
                    ("Tb.Sp 直接法", px_ax, e_sp),
                    ("真値", px_ax, [0.0] * len(px_ax))],
                   xlabel="画素の大きさ [µm]", ylabel="誤差 [%](定義による真値比)",
                   title="解像度を粗くしても平均は 1 骨梁 = 2 px まで持つ",
                   caption="平均は持つが分布は潰れる(次の図)。")
    figs.save_plot("thickness_distribution",
                   [("真値(5 µm/px)", edges[:-1] + 10, np.histogram(tr["direct"]["th_values"], bins=edges)[0] / tr["direct"]["th_values"].size),
                    ("測定 10 µm/px", edges[:-1] + 10, np.histogram(keep[10.0]["d"]["th_values"], bins=edges)[0] / keep[10.0]["d"]["th_values"].size),
                    ("測定 60 µm/px", edges[:-1] + 10, np.histogram(v60, bins=edges)[0] / v60.size)],
                   xlabel="局所厚さ [µm]", ylabel="画素の割合",
                   title="厚さの分布: 60 µm 画素では棒 %d 本に潰れる(重なり %.2f → %.2f)" % (
                       len(uniq), ovl[0], ovl[-1]))
    figs.save_table("resolution_table",
                    ["画素 µm", "px/骨梁", "BV/TV 誤差", "Tb.Th 直接 µm", "Tb.Th 平板 µm", "Tb.Sp 直接 µm", "消えた骨", "分布重なり"],
                    rows, title="解像度掃引(雑音 σ=%.2f、ぼけ σ=%.1f px)" % (NOISE_SIGMA, PSF_SIGMA_PX),
                    caption="括弧は定義による真値(Tb.Th %.1f µm)比。" % t_def)
    up = int(round(60.0 / 10.0))
    m60 = np.kron(keep[60.0]["mask"].astype(np.float64), np.ones((up, up)))
    i60 = np.kron(keep[60.0]["img"], np.ones((up, up)))
    n10 = keep[10.0]["img"].shape[0]
    figs.save_grid("scene_observed",
                   [np.clip(keep[10.0]["img"], 0, 1), keep[10.0]["mask"].astype(np.float64),
                    np.clip(i60[:n10, :n10], 0, 1), m60[:n10, :n10]],
                   ["観測 10 µm/px(σ=%.2f)" % NOISE_SIGMA, "大津マスク 10 µm(Tb.Th %.0f µm)" % keep[10.0]["d"]["tbth"],
                    "観測 60 µm/px(2 px/骨梁)", "大津マスク 60 µm(Tb.Th %.0f µm)" % keep[60.0]["d"]["tbth"]],
                   title="同じ骨梁網を 10 µm と 60 µm の画素で見る", ncols=2)
    figs.save_grid("thickness_map_measured",
                   [keep[10.0]["d"]["th_map"], keep[10.0]["d"]["sp_map"]],
                   ["局所厚さ(10 µm/px)[µm]", "局所間隔(10 µm/px)[µm]"],
                   title="測定側の距離変換マップ")
    return {"px": px_ax, "err_direct": e_dir, "err_plate": e_plate, "overlap": ovl,
            "gone60": keep[60.0]["gone"], "n_uniq60": len(uniq)}


# --------------------------------------------------------------------------- #
# 3. 雑音の崖 —— 斑点と途切れは逆向き                                          #
# --------------------------------------------------------------------------- #
def _breakage(mask: np.ndarray, tb: np.ndarray) -> dict:
    """壊れ方を種類ごとに数える: 斑点(髄の中の偽の骨)、途切れ(骨の余分な片)、髄腔の融合。"""
    lab = _LAB.blob_label(mask)
    f = _LAB.blob_features(lab)
    n_speckle, n_bone = 0, 0
    for k in range(1, int(lab.max()) + 1):
        reg = lab == k
        if float(tb[reg].mean()) < 0.1:
            n_speckle += 1
        else:
            n_bone += 1
    n_bone_true = int(_LAB.blob_label(tb).max())
    breaks = max(0, n_bone - n_bone_true)
    # 髄腔の融合: 真値の髄腔 2 つ以上が測定の 1 つの髄腔ラベルに入る
    tcell = _LAB.blob_label(~tb)
    mcell = _LAB.blob_label(~mask)
    merged = 0
    for k in range(1, int(mcell.max()) + 1):
        reg = mcell == k
        if reg.sum() < 50:
            continue
        cells = np.unique(tcell[reg])
        cells = cells[cells > 0]
        big = [c for c in cells if np.count_nonzero(reg & (tcell == c)) >= 0.05 * np.count_nonzero(tcell == c)]
        merged += max(0, len(big) - 1)
    return {"speckle": n_speckle, "breaks": breaks, "merged": merged}


def section_noise(sc: dict, tr: dict) -> dict:
    print("\n" + "=" * 78)
    print("3) 雑音の崖 —— 斑点(Tb.Sp を小さく)と途切れ(Tb.Sp を大きく)")
    print("=" * 78)
    px = 30.0
    tb = truth_at(sc["master"], px)
    n_marrow = int((~tb).sum())
    # 予想: 髄の画素が固定しきい値 0.5 を超える確率 Φ(-(0.5-髄)/σ) × 髄の画素数 ≥ 1
    gap = 0.5 - MARROW_LEVEL
    z = float(special.ndtri(1.0 - 1.0 / n_marrow))
    sig_speckle = gap / z
    print("  予想: 斑点は σ ≈ %.2f から(髄 %d 画素、Φ⁻¹(1-1/N) = %.2f)。"
          "途切れは 4 px 幅の帯が全部沈む必要があるのでそれより後。" % (sig_speckle, n_marrow, z))
    print("\n  σ      BV/TV     Tb.Th 直接   Tb.Sp 直接   斑点   途切れ  髄腔融合   Tb.Th 平板")
    sig_ax, sp_err, th_err, speck, brk, mrg, pl_err = [], [], [], [], [], [], []
    ref_d = direct_metrics(tb, px)
    ref_p = plate_metrics(tb, px)
    for s in (0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40):
        img = observe(sc["master"], px, noise=s)
        mask = np.asarray(fs.apply(img, "otsu")) > 0.5
        d = direct_metrics(mask, px)
        p = plate_metrics(mask, px)
        b = _breakage(mask, tb)
        sig_ax.append(s)
        sp_err.append(100 * (d["tbsp"] / ref_d["tbsp"] - 1))
        th_err.append(100 * (d["tbth"] / ref_d["tbth"] - 1))
        pl_err.append(100 * (p["tbth"] / ref_p["tbth"] - 1))
        speck.append(b["speckle"]); brk.append(b["breaks"]); mrg.append(b["merged"])
        print("  %.2f   %+6.1f %%   %+6.1f %%     %+6.1f %%    %4d    %4d     %4d     %+6.1f %%" % (
            s, 100 * (mask.mean() / tb.mean() - 1), th_err[-1], sp_err[-1],
            b["speckle"], b["breaks"], b["merged"], pl_err[-1]))
    print("  (誤差は同じ画素 %.0f µm の真値二値像に同じ推定器を当てた値との比)" % px)

    # 対策: opening r=1 / 面積オープニング 16 px / 前処理ぼかし σ=1 px
    s = 0.20
    img = observe(sc["master"], px, noise=s)
    raw = np.asarray(fs.apply(img, "otsu"))
    remedies = [
        ("そのまま", raw),
        ("opening r=1", np.asarray(fs.apply(raw, "opening_circle", a=0.0))),
        ("面積オープニング 16 px", np.asarray(fs.apply(raw, "sk_area_opening", a=0.0))),
        ("ぼかし σ=1 px → 大津", np.asarray(fs.apply(fs.apply(img, "gaussian", a=(1.0 - 0.3) / 2.7), "otsu"))),
    ]
    print("\n  σ = %.2f での対策(壊れ方を種類ごとに):" % s)
    print("  手法                     斑点   途切れ  髄腔融合   Tb.Th 直接   Tb.Sp 直接")
    rem_rows = []
    rem = {}
    for name, m in remedies:
        m = m > 0.5
        b = _breakage(m, tb)
        d = direct_metrics(m, px)
        rem[name] = {**b, "tbth": 100 * (d["tbth"] / ref_d["tbth"] - 1),
                     "tbsp": 100 * (d["tbsp"] / ref_d["tbsp"] - 1)}
        rem_rows.append([name, str(b["speckle"]), str(b["breaks"]), str(b["merged"]),
                         "%+.1f %%" % rem[name]["tbth"], "%+.1f %%" % rem[name]["tbsp"]])
        print("  %-24s %4d    %4d     %4d     %+6.1f %%    %+6.1f %%" % (
            name, b["speckle"], b["breaks"], b["merged"], rem[name]["tbth"], rem[name]["tbsp"]))
    print("  ★opening は斑点を消すが細い骨梁も切る(途切れ %d → %d)。面積オープニングは"
          "\n    斑点だけを消す(途切れ %d → %d)—— 「形」でなく「大きさ」で落とす。" % (
              rem["そのまま"]["breaks"], rem["opening r=1"]["breaks"],
              rem["そのまま"]["breaks"], rem["面積オープニング 16 px"]["breaks"]))

    figs.save_plot("noise_sweep",
                   [("Tb.Sp 直接法", sig_ax, sp_err), ("Tb.Th 直接法", sig_ax, th_err),
                    ("Tb.Th 平板モデル", sig_ax, pl_err), ("真値", sig_ax, [0.0] * len(sig_ax))],
                   xlabel="雑音 σ(骨 = 1)", ylabel="誤差 [%]",
                   title="雑音で Tb.Sp は先に落ち、平板モデルは周長で崩れる")
    figs.save_plot("noise_breakage",
                   [("斑点(髄の中の偽の骨)", sig_ax, speck), ("骨梁の途切れ", sig_ax, brk),
                    ("髄腔の融合", sig_ax, mrg)],
                   xlabel="雑音 σ(骨 = 1)", ylabel="件数",
                   title="壊れ方の内訳(予想: 斑点は σ ≈ %.2f から)" % sig_speckle)
    figs.save_table("noise_remedies", ["手法", "斑点", "途切れ", "髄腔融合", "Tb.Th 誤差", "Tb.Sp 誤差"],
                    rem_rows, title="σ = %.2f、画素 %.0f µm(4 px/骨梁)での対策" % (s, px))
    figs.save_grid("noise_masks",
                   [np.clip(img, 0, 1)] + [m.astype(np.float64) for _, m in remedies],
                   ["観測 σ=%.2f" % s] + [n for n, _ in remedies],
                   title="斑点を消すか、骨梁を切るか", ncols=3)
    return {"sigma": sig_ax, "speckle": speck, "breaks": brk, "merged": mrg,
            "sp_err": sp_err, "sig_pred": sig_speckle, "rem": rem}


# --------------------------------------------------------------------------- #
# 4. しきい値 ±10 %                                                            #
# --------------------------------------------------------------------------- #
def section_threshold(sc: dict, tr: dict) -> dict:
    print("\n" + "=" * 78)
    print("4) しきい値 ±10 % —— BV/TV と Tb.Th はどちらへ動くか")
    print("=" * 78)
    px = 20.0
    tb = truth_at(sc["master"], px)
    ref_d = direct_metrics(tb, px)
    ref_p = plate_metrics(tb, px)
    img = observe(sc["master"], px, noise=0.0)
    img = (img - MARROW_LEVEL) / (1.0 - MARROW_LEVEL)     # 骨 = 1、髄 = 0 に戻す
    print("  予想: 消える骨梁が無いので生存バイアスは働かず、BV/TV と Tb.Th は同じ向き。")
    print("\n  しきい値   BV/TV      Tb.Th 直接   Tb.Th 平板   Tb.Sp 直接   Tb.N 平板")
    th_ax, bv, td, tp, ts, tn = [], [], [], [], [], []
    for t in (0.40, 0.45, 0.50, 0.55, 0.60):
        mask = np.asarray(fs.apply(img, "threshold", a=t)) > 0.5
        d = direct_metrics(mask, px)
        p = plate_metrics(mask, px)
        th_ax.append(t)
        bv.append(100 * (mask.mean() / tb.mean() - 1))
        td.append(100 * (d["tbth"] / ref_d["tbth"] - 1))
        tp.append(100 * (p["tbth"] / ref_p["tbth"] - 1))
        ts.append(100 * (d["tbsp"] / ref_d["tbsp"] - 1))
        tn.append(100 * (p["tbn"] / ref_p["tbn"] - 1))
        print("   %.2f     %+6.1f %%    %+6.1f %%     %+6.1f %%     %+6.1f %%     %+6.1f %%" % (
            t, bv[-1], td[-1], tp[-1], ts[-1], tn[-1]))
    same = (bv[1] < 0 and td[1] < 0 and bv[3] > 0 and td[3] > 0)
    print("\n  ★BV/TV と Tb.Th は %s向きに動いた。Tb.N は BV/TV ÷ Tb.Th なので"
          "逆向き(%+.1f %% → %+.1f %%)。" % ("同じ" if same else "逆", tn[1], tn[3]))
    figs.save_plot("threshold_sweep",
                   [("BV/TV", th_ax, bv), ("Tb.Th 直接法", th_ax, td),
                    ("Tb.Th 平板モデル", th_ax, tp), ("Tb.N 平板モデル", th_ax, tn),
                    ("真値", th_ax, [0.0] * len(th_ax))],
                   xlabel="しきい値(骨 = 1)", ylabel="誤差 [%]",
                   title="しきい値 ±10 % で BV/TV と Tb.Th は同じ向き、Tb.N は逆")
    return {"bv": bv, "td": td, "tp": tp, "tn": tn, "same": same}


# --------------------------------------------------------------------------- #
# 5. バイアス(ビームハードニング)と対照群                                        #
# --------------------------------------------------------------------------- #
def section_bias_and_controls(sc: dict, tr: dict) -> dict:
    print("\n" + "=" * 78)
    print("5) ビームハードニングのカップ状バイアスと対照群")
    print("=" * 78)
    px = 20.0
    tb = truth_at(sc["master"], px)
    ref_d = direct_metrics(tb, px)
    n = tb.shape[0]

    def center_edge(mask: np.ndarray) -> tuple[float, float]:
        th = local_thickness(mask) * px
        yy, xx = np.mgrid[0:n, 0:n]
        r = np.hypot(yy - n / 2.0, xx - n / 2.0) / (n / 2.0)
        return float(th[mask & (r < 0.5)].mean()), float(th[mask & (r > 0.8)].mean())

    img = observe(sc["master"], px, noise=0.10, bias=BIAS_BETA)
    m_otsu = np.asarray(fs.apply(img, "otsu")) > 0.5
    # retinex: log(I) - log(G_σ(I))。σ = 1 + a·0.5·n → σ ≈ 1500 µm(格子間隔の 1.4 倍)
    a_ret = (1500.0 / px - 1.0) / (0.5 * n)
    m_ret = np.asarray(fs.apply(fs.apply(img, "dc_retinex", a=a_ret, b=0.5), "otsu")) > 0.5
    d_o, d_r = direct_metrics(m_otsu, px), direct_metrics(m_ret, px)
    ce_o, ce_r = center_edge(m_otsu), center_edge(m_ret)
    ce_t = center_edge(tb)
    print("  バイアス %.0f %%、雑音 σ=0.10、画素 %.0f µm:" % (100 * BIAS_BETA, px))
    print("  手法             BV/TV 誤差   Tb.Th 直接   中心 Tb.Th   縁 Tb.Th")
    print("  真値二値像         -           %6.1f       %6.1f       %6.1f" % (ref_d["tbth"], ce_t[0], ce_t[1]))
    for name, m, d, ce in (("大津 1 本", m_otsu, d_o, ce_o), ("retinex → 大津", m_ret, d_r, ce_r)):
        print("  %-16s %+6.1f %%     %6.1f       %6.1f       %6.1f" % (
            name, 100 * (m.mean() / tb.mean() - 1), d["tbth"], ce[0], ce[1]))
    bias_rows = [["真値", "-", "%.1f" % ref_d["tbth"], "%.1f" % ce_t[0], "%.1f" % ce_t[1]],
                 ["大津 1 本", "%+.1f %%" % (100 * (m_otsu.mean() / tb.mean() - 1)), "%.1f" % d_o["tbth"], "%.1f" % ce_o[0], "%.1f" % ce_o[1]],
                 ["retinex → 大津", "%+.1f %%" % (100 * (m_ret.mean() / tb.mean() - 1)), "%.1f" % d_r["tbth"], "%.1f" % ce_r[0], "%.1f" % ce_r[1]]]
    figs.save_grid("bias_masks",
                   [np.clip(img, 0, 1), m_otsu.astype(np.float64), m_ret.astype(np.float64), tb.astype(np.float64)],
                   ["観測(バイアス %.0f %%)" % (100 * BIAS_BETA), "大津 1 本(中心 %.0f / 縁 %.0f µm)" % ce_o,
                    "retinex → 大津(中心 %.0f / 縁 %.0f µm)" % ce_r, "真値(中心 %.0f / 縁 %.0f µm)" % ce_t],
                   title="カップ状バイアスは中心の骨梁を痩せさせる", ncols=2)
    figs.save_table("bias_table", ["手法", "BV/TV 誤差", "Tb.Th µm", "中心 µm", "縁 µm"], bias_rows,
                    title="ビームハードニング %.0f %% での Tb.Th" % (100 * BIAS_BETA))

    # 対照群: 要因を 1 つずつ止める(大津 1 本、直接法)
    print("\n  対照群(要因を 1 つずつ止める、大津 1 本 + 直接法、画素 %.0f µm):" % px)
    print("  条件                  BV/TV 誤差   Tb.Th 誤差   Tb.Sp 誤差")
    conds = [("全部(ぼけ+雑音+バイアス)", dict(blur=True, noise=NOISE_SIGMA, bias=BIAS_BETA)),
             ("ぼけ無し", dict(blur=False, noise=NOISE_SIGMA, bias=BIAS_BETA)),
             ("雑音無し", dict(blur=True, noise=0.0, bias=BIAS_BETA)),
             ("バイアス無し", dict(blur=True, noise=NOISE_SIGMA, bias=0.0)),
             ("何も無し(部分体積だけ)", dict(blur=False, noise=0.0, bias=0.0))]
    ctrl_rows, ctrl = [], {}
    for name, kw in conds:
        im = observe(sc["master"], px, **kw)
        m = np.asarray(fs.apply(im, "otsu")) > 0.5
        d = direct_metrics(m, px)
        e = (100 * (m.mean() / tb.mean() - 1), 100 * (d["tbth"] / ref_d["tbth"] - 1),
             100 * (d["tbsp"] / ref_d["tbsp"] - 1))
        ctrl[name] = e
        ctrl_rows.append([name, "%+.1f %%" % e[0], "%+.1f %%" % e[1], "%+.1f %%" % e[2]])
        print("  %-22s %+6.1f %%     %+6.1f %%     %+6.1f %%" % (name, *e))
    figs.save_table("controls", ["条件", "BV/TV 誤差", "Tb.Th 誤差", "Tb.Sp 誤差"], ctrl_rows,
                    title="対照群: どの要因が効いているか(画素 %.0f µm)" % px)
    return {"otsu_bv": 100 * (m_otsu.mean() / tb.mean() - 1),
            "ret_bv": 100 * (m_ret.mean() / tb.mean() - 1),
            "ce_otsu": ce_o, "ce_ret": ce_r, "ctrl": ctrl}


# --------------------------------------------------------------------------- #
# 6. 道具の穴                                                                  #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("6) 道具の穴(この PoC で使ってみて)")
    print("=" * 78)
    m = np.zeros((40, 60)); m[15:26, 5:55] = 1.0
    # (a) 2-D の局所厚さ(最大内接円)op が無い —— 3-D には medial_axis_points がある
    assert not hasattr(fs.ledger, "local_thickness") and "local_thickness" not in fs.op_names()
    print("  (a) 2-D の局所厚さ(Hildebrand の最大内接円)が公開経路に無い。この PoC は"
          "\n      blob_distance を半径ごとに回して自前で組んだ(3-D は medial_axis_points が近い)。")
    # (b) 進化 op の距離変換は最大値で正規化 → 画素単位は ledger.blob_distance だけ
    dn = np.asarray(fs.apply(m, "dist_transform"))
    assert abs(float(dn.max()) - 1.0) < 1e-9
    print("  (b) dist_transform / cv_dist / xsp_chamfer_dist は最大値で正規化される。"
          "画素単位の距離は ledger.blob_distance のみ。")
    # (c) add_noise_white の σ は 0.22 まで
    print("  (c) add_noise_white の σ は 0.02〜0.22 に固定。雑音掃引(σ 0.4)は numpy で足した。")
    # (d) 平板モデル / 骨形態計測の指標(Tb.Th, Tb.Sp, Tb.N, BV/TV)を出す op が無い
    assert not any(n.startswith("bone_") or "trabec" in n for n in fs.op_names())
    print("  (d) 骨形態計測の指標(BV/TV, Tb.Th, Tb.Sp, Tb.N)を一括で出す op が無い。"
          "blob_features の area/perimeter から自前。")
    # (e) get_region_thickness は画像サイズで正規化された 1 スカラー
    v = float(np.asarray(fs.apply(m, "get_region_thickness")))
    assert v < 1.0
    print("  (e) get_region_thickness は「最大内接円 × 2 / 画像辺長」の 1 スカラー(%.3f)で、"
          "分布も画素単位も出ない。" % v)


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("骨梁の厚さ・間隔・骨体積率 —— 平板モデルと直接法は同じ画像で別の値")
    print("視野 %.0f µm 角 / 真値 %.1f µm 格子 / 帯の幅 中央値 %.0f µm [%.0f, %.0f]" % (
        FIELD_UM, MASTER_UM, W_MED, W_LO, W_HI))
    print("=" * 78)
    sc = make_master()
    print("  線分 %d 本、BV/TV %.4f、描画 %.1f 秒" % (len(sc["segs"]), sc["bvtv"], time.perf_counter() - t0))

    tr = section_truths(sc)
    res = section_resolution(sc, tr)
    noi = section_noise(sc, tr)
    thr = section_threshold(sc, tr)
    bia = section_bias_and_controls(sc, tr)
    section_tool_gaps()

    # --- 所見を固定する ------------------------------------------------------ #
    assert abs(tr["direct"]["tbth"] / tr["closed"] - 1) > 0.02, "定義と閉形式が一致してしまった"
    assert tr["plate"]["tbth"] < tr["direct"]["tbth"], "平板モデルが直接法より大きい"
    assert max(abs(e) for e in res["err_direct"]) < 8.0, res["err_direct"]
    assert res["overlap"][0] > 0.8 and res["overlap"][-1] < 0.6, res["overlap"]
    assert res["gone60"] < 0.05, "生存バイアスが効いている(予想を書き換えること)"
    assert noi["speckle"][0] == 0 and noi["speckle"][-1] > 20, noi["speckle"]
    assert noi["breaks"][0] == 0 and noi["breaks"][-1] > noi["breaks"][0], noi["breaks"]
    assert noi["rem"]["opening r=1"]["breaks"] > noi["rem"]["そのまま"]["breaks"]
    assert noi["rem"]["面積オープニング 16 px"]["speckle"] == 0
    assert thr["same"], "BV/TV と Tb.Th が逆向きに動いた"
    assert abs(bia["ret_bv"]) < abs(bia["otsu_bv"]), (bia["ret_bv"], bia["otsu_bv"])

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 真値が 2 つ(閉形式 %.1f / 定義 %.1f µm)、モデルが 2 つ(平板 %.1f µm)。" % (
        tr["closed"], tr["direct"]["tbth"], tr["plate"]["tbth"]))
    print("  * 解像度の崖は平均でなく分布に来る(重なり %.2f → %.2f)。" % (res["overlap"][0], res["overlap"][-1]))
    print("  * 雑音は斑点(σ %.2f〜)と途切れで逆向きに Tb.Sp を引く。" % noi["sig_pred"])
    print("  * しきい値は BV/TV と Tb.Th を同じ向きに、Tb.N を逆向きに動かす。")
    print("  * バイアスは retinex で割ってから大津(BV/TV %+.1f → %+.1f %%)。" % (bia["otsu_bv"], bia["ret_bv"]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
