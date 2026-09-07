# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""溶接部の X 線透過像から気孔を検出し、寸法と等級を出す —— 等級を 1 段間違える画像の割合で締める。

    py -3.11 examples/poc_weld_radiograph_porosity.py

突合せ溶接の放射線透過試験(RT)で、**気孔(ポロシティ)**を見つけて直径を測り、
JIS Z 3104 / ISO 5817 のような**等級**に落とす仕事です。気孔は透過厚が減るので
透過像では**明るい斑点**になり、余盛は厚いので**暗い帯**になります。現場の数字は
「個数・最大径・合計面積」ではなく最終的に**等級 1 つ**なので、検出率や直径誤差を
別々に測ったうえで、**等級を 1 段間違える画像が何 % あるか**まで畳んで測ります。

【グラウンドトゥルース(閉形式 + 合成)】
板厚 t = 10 mm の母材の上に、断面が円弧(幅 12 mm・高さ 2 mm)の余盛を溶接線
方向(横)に走らせ、球形気孔(直径・位置は既知)を埋める。透過厚 L(x,y) は
母材 + 余盛の弧 − 球の弦長で閉形式、透過像は Beer–Lambert ``I = I0·exp(−μL)``
(μ = 0.08 /mm を既知とする)。そこに散乱(一次線の大窓ぼかし × SPR)、検出器の
不鋭度(σ = 0.6 px)、フィルム粒状雑音(ポアソン + ガウス)を足す。針金 IQI
(ISO 19232-1 の W10〜W16、7 本)は円柱の弦長で同じ式から描く。1 px = 0.1 mm。

EXTEND: 実写に差し替えるなら :func:`render` の代わりに撮影画像(透過率に線形な
DDA 画像、またはフィルム濃度を透過率へ戻したもの)を渡し、``mu`` を段付き試験片で
較正する。等級表(:data:`POINTS_TABLE` / :data:`CLASS_LIMITS`)は**規格本体の
表に置き換える**こと —— ここにある値は考え方を模した本文定数であって、規格の
引用ではない。余盛の形が溶接線方向に変わる実物では、「行方向プロファイル」の
背景は使えない(この PoC でも対照群としてしか使っていない)。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(余盛の帯の中で固定しきい値)は余盛の断面そのものを拾う**。
   気孔 6 個の場面で塊 14 個・合計面積 22.68 mm²(真値 10.50 mm²)、
   最大径は 4.13 mm(真値 2.20 mm)—— 弧の縁(つま先)は弧の中央より
   15 % 明るいので、しきい値 1 本では気孔と区別できない。
2. ★**検出の崖は CNR で先に予測できた**。予測 = 気孔の平均弦長 (2/3)d ×
   μ × √(画素数) / 画素の相対雑音 = 15.29·d² で、CNR = 4 を 50 % 検出の
   目安に置くと d₅₀ = 0.51 mm。実測の 50 % 交点は 0.50 mm(0.4 mm で 20 %、
   0.6 mm で 97 %)。★予想は「CNR=4 で 50 %」だったが、実測の交点は
   CNR 3.8 —— 誤差 5 % で当たった。
3. ★★**背景推定の op には大きさの天井があり、それは崖として現れる**。
   9 px の矩形オープニング(fullseye の窓は 9 px まで)は d ≥ 1.4 mm で
   検出率 100 → 6 % に落ちる(気孔が背景に食われる)。直径オープニング
   (最大 34 px)は 3.0 mm でも 100 %。山削り(再構成)は大きさに依らず
   100 %。**op を選ぶことが測定範囲を選ぶことになっている**。
4. ★**直径は 3 通りで、偏りの向きも大きさも違う**。しきい値の面積径は
   小さい側で縮む(0.6 mm で −20.5 %、予測は弦長モデル
   √(d² − (thr/μ)²) で −13.5 %)。積分コントラスト(体積)径は μ 既知なら
   全域で ±3 % 以内。キャリパ(エッジ対)径は +5〜+8 % で**太る**
   (PSF と平滑化で縁が外へ出る)。
5. ★**散乱かぶりは直径を縮める —— 体積径は (1+SPR)^(−1/3) で、しきい値径は
   もっと速く**。SPR = 1.0 で体積径 −20.8 %(予測 −20.6 %)、しきい値径は
   0.6 mm 気孔で −57 %(予測 −54 %)。**散乱を見込まずに μ を使うと、
   等級の境目(1 mm)をまたぐ**。
6. ★★**余盛のつま先(明暗の段)の近くで壊れるのは大窓平滑だけ**。ガウス
   σ = 3 px の背景はつま先から 0.5 mm 以内で偽陽性 2.0 個/枚を出す
   (段のぼけが明るい側に残る)。オープニング系(山削り・9 px)は段を保存
   するので 0 個。予想は「オープニングも縁で偽陽性」だったが**外れた**
   —— 段差はオープニングでは崩れない(下に凸の角は保存される)。
7. ★★**IQI の視認限界と気孔の検出限界は別の物差し**。針金は長さ 10 mm で
   積分できるので W14(0.16 mm)まで見える(CNR 4.5)のに、気孔の 50 % 限界は
   0.50 mm。同じ CNR で換算すると W14 ≒ 気孔 0.53 mm。「IQI 感度 2 %(0.2 mm)」
   を気孔の検出限界と読むと **3 倍**楽観する。
8. ★★**等級を 1 段間違える画像の割合**(30 枚 × 4 条件、点数法)。
   ゼロ点 100 % / 山削り + しきい値径 20 % / 山削り + 体積径 13 %。
   内訳は「見落とし」が 0 %、「直径の誤分類」がほぼ全部 —— 見落とすのは
   無視径(0.4 mm)以下の気孔だけなので等級には効かず、**効くのは 1 mm の境目を
   またぐ直径誤差**。散乱を止めた対照群では 3 %、余盛を止めても 13 %
   (余盛は等級誤りに効いていない)。

来歴(公開文献のみ): JIS Z 3104 *鋼溶接継手の放射線透過試験方法*(等級分類の
点数法の考え方)/ ISO 5817:2014 *Welding — Quality levels for imperfections* /
ISO 19232-1 *Image quality indicators (wire type)* / Rose, A. (1948) *J. Opt. Soc.
Am.* 38, 196 —— 視認の CNR 基準 / Sternberg (1983) rolling ball。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_dilation, gaussian_filter, zoom

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
H, W = 256, 320          # 行 × 列 [px]
PX = 0.1                 # [mm/px]
T_PLATE = 10.0           # 板厚 [mm]
CAP_W, CAP_H = 12.0, 2.0  # 余盛の幅・高さ [mm](断面は円弧)
CAP_ROW = H / 2.0        # 余盛の中心行
MU = 0.08                # 線減弱係数 [1/mm](鋼、実効 ~250 kV 相当と仮定)
N_PLATE = 2000           # 母材直下の 1 画素あたり光子数(散乱なし)
SIG_G = 0.004            # ガウス雑音(フィルム粒状)[画像単位]
GAIN = 0.6               # 検出器ゲイン(母材の透過率 0.449 → 画像 0.27)
PSF_SIG = 0.6            # 検出器の不鋭度 [px]
SCATTER_SIG = 40.0       # 散乱の広がり [px]
SPR_BASE = 0.5           # 基準条件の散乱/一次線比
SEED = 7

WIRES_MM = (0.40, 0.32, 0.25, 0.20, 0.16, 0.125, 0.10)   # ISO 19232-1 W10〜W16
WIRE_LEN_MM = 24.0
WIRE_PITCH_MM = 4.0

# 等級(点数法)—— JIS Z 3104 の考え方を模した本文定数。規格の引用ではない。
D_IGNORE = 0.4                              # この直径以下は数えない [mm]
POINTS_TABLE = ((1.0, 1), (2.0, 2), (3.0, 3), (4.0, 6), (6.0, 10), (8.0, 15))
POINTS_OVER = 25
CLASS_LIMITS = (3, 6, 12)                   # 1 類 / 2 類 / 3 類 の上限点数(10×10 mm)
FIELD_MM = 10.0

K_SIGMA = 3.0            # 検出しきい値 [σ]
SMOOTH_SIG = 1.0         # 検出前の平滑化 [px]
A_MIN_PX = 3             # 塊の最小画素数

_LAB = fs.ledger


# --------------------------------------------------------------------------- #
# 場面を作る —— 真値は「埋めた球の直径と中心」                                    #
# --------------------------------------------------------------------------- #
def cap_height(rows: np.ndarray) -> np.ndarray:
    """余盛の高さ h(y) [mm]。幅 CAP_W・高さ CAP_H の円弧。"""
    y = (rows - CAP_ROW) * PX
    r_arc = ((CAP_W / 2) ** 2 + CAP_H ** 2) / (2 * CAP_H)
    h = np.sqrt(np.clip(r_arc ** 2 - y ** 2, 0, None)) - (r_arc - CAP_H)
    return np.where(np.abs(y) <= CAP_W / 2, np.clip(h, 0, None), 0.0)


def _sphere_chord(thick: np.ndarray, r0: float, c0: float, d_mm: float, ss: int = 4) -> None:
    """球の弦長 [mm] を ``thick`` から引く(外接箱内を ss×ss 超解像で平均)。"""
    R = d_mm / (2 * PX)
    rr0, rr1 = max(0, int(np.floor(r0 - R - 1))), min(H, int(np.ceil(r0 + R + 2)))
    cc0, cc1 = max(0, int(np.floor(c0 - R - 1))), min(W, int(np.ceil(c0 + R + 2)))
    if rr1 <= rr0 or cc1 <= cc0:
        return
    off = (np.arange(ss) + 0.5) / ss - 0.5
    yy = np.arange(rr0, rr1)[:, None, None, None] + off[None, None, :, None]
    xx = np.arange(cc0, cc1)[None, :, None, None] + off[None, None, None, :]
    rho2 = (yy - r0) ** 2 + (xx - c0) ** 2
    chord = 2 * PX * np.sqrt(np.clip(R * R - rho2, 0, None))
    thick[rr0:rr1, cc0:cc1] -= chord.mean(axis=(2, 3))


def _wire_chord(thick: np.ndarray, col: float, d_mm: float, r_lo: int, r_hi: int, ss: int = 4) -> None:
    """針金(円柱)の弦長 [mm] を ``thick`` に足す(縦に置く)。"""
    rw = d_mm / (2 * PX)
    cc0, cc1 = max(0, int(np.floor(col - rw - 1))), min(W, int(np.ceil(col + rw + 2)))
    off = (np.arange(ss) + 0.5) / ss - 0.5
    xx = np.arange(cc0, cc1)[:, None] + off[None, :]
    chord = 2 * PX * np.sqrt(np.clip(rw * rw - (xx - col) ** 2, 0, None)).mean(axis=1)
    thick[r_lo:r_hi, cc0:cc1] += chord[None, :]


def render(pores, rng, *, cap: bool = True, spr: float = SPR_BASE,
           wires: bool = False, noise: bool = True) -> dict:
    """透過像を作る。``pores`` = [(row, col, d_mm), ...]。

    返り値の ``img`` は [0,1] の float(透過率に線形 = DDA 表示。明るい = 薄い)。
    ``thick`` は透過厚 [mm]、``primary`` は散乱なしの一次線。
    """
    rows = np.arange(H, dtype=np.float64)
    thick = np.full((H, W), T_PLATE)
    if cap:
        thick += cap_height(rows)[:, None]
    if wires:
        r_lo = int(CAP_ROW - WIRE_LEN_MM / (2 * PX))
        r_hi = int(CAP_ROW + WIRE_LEN_MM / (2 * PX))
        for k, dw in enumerate(WIRES_MM):
            _wire_chord(thick, 40 + k * WIRE_PITCH_MM / PX, dw, r_lo, r_hi)
    for r0, c0, d in pores:
        _sphere_chord(thick, r0, c0, d)
    primary = np.exp(-MU * thick)
    primary = np.asarray(fs.apply(primary, "gauss_image", a=(PSF_SIG - 0.3) / 2.7))
    scatter = spr * gaussian_filter(primary, SCATTER_SIG, mode="nearest")
    flux = primary + scatter
    p_plate = np.exp(-MU * T_PLATE)
    if noise:
        counts = rng.poisson(N_PLATE * flux / p_plate).astype(np.float64)
        img = counts / N_PLATE * p_plate * GAIN + SIG_G * rng.standard_normal((H, W))
    else:
        img = flux * GAIN
    return {"img": np.clip(img, 0, 1), "thick": thick, "primary": primary,
            "pores": [tuple(p) for p in pores], "spr": spr, "cap": cap}


def place_pores(rng, n: int, d_lo: float, d_hi: float, *, band: float = 4.5,
                d_fixed: float | None = None, row_fixed: float | None = None):
    """余盛の帯 |y| ≤ band mm に重ならないように気孔を置く。直径は対数一様。"""
    out = []
    for _ in range(400):
        if len(out) >= n:
            break
        d = d_fixed if d_fixed is not None else float(np.exp(rng.uniform(np.log(d_lo), np.log(d_hi))))
        r0 = row_fixed if row_fixed is not None else float(rng.uniform(CAP_ROW - band / PX, CAP_ROW + band / PX))
        c0 = float(rng.uniform(d / PX + 4, W - d / PX - 4))
        if all(np.hypot(r0 - r, c0 - c) * PX > (d + dd) / 2 + 1.0 for r, c, dd in out):
            out.append((r0, c0, d))
    return out


# --------------------------------------------------------------------------- #
# 背景推定(fullseye の op)→ 対数コントラスト → 検出                             #
# --------------------------------------------------------------------------- #
def _coarse_median(img: np.ndarray, f: int) -> np.ndarray:
    """f×f の区画平均で縮小 → fullseye の median_rect(3 × 9)→ 双一次で戻す。

    fullseye の窓は 9 px までなので、**縮小して窓を広げる**。溶接線方向(横)に
    長く、余盛の曲率方向(縦)に短い窓 = 3f × 9f px。中央値は線形フィルタと同じく
    雑音の残差が**片側に偏らない**(オープニング系との違い、2 節で実測)。
    """
    c = img.reshape(H // f, f, W // f, f).mean(axis=(1, 3))
    m = np.asarray(fs.apply(c, "median_rect", a=0.0, b=1.0))
    return zoom(m, f, order=1, grid_mode=True, mode="nearest")


def background(img: np.ndarray, method: str) -> np.ndarray:
    """背景画像を返す。``img - 背景`` が気孔(明るい突起)。"""
    if method == "med72":            # 縮小 ×8 + 中央値 3×9 = 24 × 72 px の窓(主経路)
        return _coarse_median(img, 8)
    if method == "med36":            # 縮小 ×4 + 中央値 3×9 = 12 × 36 px の窓(天井の対照)
        return _coarse_median(img, 4)
    if method == "grind":            # 再構成による山削り(全ての山を鞍点の高さまで削る)
        return np.asarray(fs.apply(img, "xsitk_grayscale_grindpeak"))
    if method == "open9":            # 9 px 矩形オープニング(fullseye の窓の上限)
        return np.asarray(fs.apply(img, "gray_opening_rect", a=1.0))
    if method == "gauss3":           # 大窓平滑(ガウス σ = 3 px、op の上限)
        return np.asarray(fs.apply(img, "gauss_image", a=1.0))
    raise ValueError(method)


def noise_rel(img: np.ndarray) -> float:
    """画素の相対雑音 σ/I(余盛の帯の中で)。σ は fullseye の estimate_noise。"""
    band = img[int(CAP_ROW - 40):int(CAP_ROW + 40)]
    sigma = float(fs.apply(band, "estimate_noise"))
    return sigma / float(np.median(band))


def detect(img: np.ndarray, method: str) -> dict:
    """背景推定 → 対数コントラスト c = ln(I/背景) → 平滑化 → kσ → 連結成分。"""
    bg = np.maximum(background(img, method), 1e-4)
    c = np.log(np.maximum(img, 1e-4) / bg)
    # 平滑化は fullseye の gauss_image(入力 [0,1] の契約なので、ずらして戻す)
    span = max(float(np.abs(c).max()), 1e-6) * 2.0
    cs = (np.asarray(fs.apply(c / span + 0.5, "gauss_image", a=(SMOOTH_SIG - 0.3) / 2.7)) - 0.5) * span
    s_rel = noise_rel(img)
    thr = K_SIGMA * s_rel / (2 * np.sqrt(np.pi) * SMOOTH_SIG)   # ガウス平滑後の σ
    lab = _LAB.blob_label(cs > thr)
    if lab.max() > 0:
        lab = _LAB.blob_select(lab, "area", vmin=A_MIN_PX, vmax=None)
    f = _LAB.blob_features(lab, spacing=PX)
    return {"bg": bg, "c": c, "cs": cs, "thr": thr, "s_rel": s_rel, "labels": lab, "feat": f}


def zero_point(img: np.ndarray) -> dict:
    """ゼロ点: 余盛の帯の中で固定しきい値(帯の中央値 + kσ)。"""
    r0, r1 = int(CAP_ROW - CAP_W / (2 * PX)), int(CAP_ROW + CAP_W / (2 * PX))
    band = img[r0:r1]
    s = float(fs.apply(band, "estimate_noise"))
    thr = float(np.median(band)) + K_SIGMA * s
    mask = np.zeros_like(img, bool)
    mask[r0:r1] = band > thr
    lab = _LAB.blob_label(mask)
    if lab.max() > 0:
        lab = _LAB.blob_select(lab, "area", vmin=A_MIN_PX, vmax=None)
    return {"labels": lab, "feat": _LAB.blob_features(lab, spacing=PX), "thr": thr}


# --------------------------------------------------------------------------- #
# 直径 3 通り: しきい値の面積径 / 積分コントラスト(体積)径 / キャリパ径          #
# --------------------------------------------------------------------------- #
def diameters(det: dict, idx: int, mu: float = MU) -> dict:
    f, lab = det["feat"], det["labels"]
    d_thr = float(f["equiv_diameter"][idx])
    reg = binary_dilation(lab == f["label"][idx], iterations=3)
    vol = float(np.sum(det["c"][reg])) * PX * PX / mu         # = (4/3)π R³ [mm³]
    d_vol = float(np.cbrt(max(vol, 0.0) * 6 / np.pi))
    # キャリパ: 重心を通る横の測定線で、立ち上がり/立ち下がりの対の幅
    row, col = float(f["row"][idx]), float(f["col"][idx])
    half = d_thr / PX / 2 + 8
    span = max(float(np.abs(det["c"]).max()), 1e-6) * 2.0
    cimg = np.clip(det["c"] / span + 0.5, 0, 1)
    mh = _LAB.gen_measure_rectangle2(row, col, 0.0, half, 1, cimg.shape)
    pairs = _LAB.measure_pairs(cimg, mh, sigma=1.0, threshold=det["thr"] / span * 0.5)
    d_cal = np.nan
    bracket = [p for p in pairs if p["first"] <= half <= p["second"]]
    if bracket:
        best = max(bracket, key=lambda p: min(abs(p["first_amplitude"]), abs(p["second_amplitude"])))
        d_cal = float(best["width"]) * PX
    return {"d_thr": d_thr, "d_vol": d_vol, "d_cal": d_cal}


def match(det: dict, pores) -> dict:
    """検出と真値を 1 対 1 で突き合わせる(重心が真の中心から半径 + 1.5 px 以内)。"""
    f = det["feat"]
    n_det = int(f["n"])
    used = np.zeros(n_det, bool)
    pairs = []          # (真値 index, 検出 index)
    for i, (r0, c0, d) in enumerate(pores):
        tol = max(d / (2 * PX), 2.0) + 1.5
        best, bd = -1, tol
        for j in range(n_det):
            if used[j]:
                continue
            dist = float(np.hypot(f["row"][j] - r0, f["col"][j] - c0))
            if dist < bd:
                best, bd = j, dist
        if best >= 0:
            used[best] = True
            pairs.append((i, best))
    fp = [j for j in range(n_det) if not used[j]]
    return {"pairs": pairs, "fp": fp, "miss": [i for i in range(len(pores)) if i not in {p[0] for p in pairs}]}


# --------------------------------------------------------------------------- #
# 等級(点数法)                                                                  #
# --------------------------------------------------------------------------- #
def points_of(d: float) -> int:
    if d <= D_IGNORE:
        return 0
    for lim, pt in POINTS_TABLE:
        if d <= lim:
            return pt
    return POINTS_OVER


def grade(items) -> int:
    """``items`` = [(col_px, d_mm), ...]。溶接線に沿って 10 mm の試験視野を
    ずらし、点数が最大の視野で等級(1〜4)を決める。"""
    if not items:
        return 1
    cols = np.array([c for c, _ in items])
    pts = np.array([points_of(d) for _, d in items])
    field = FIELD_MM / PX
    worst = 0
    for start in np.arange(0, W - field + 1, 5.0):
        worst = max(worst, int(pts[(cols >= start) & (cols < start + field)].sum()))
    for k, lim in enumerate(CLASS_LIMITS):
        if worst <= lim:
            return k + 1
    return 4


def cnr_pred(d_mm: float, s_rel: float, spr: float = 0.0) -> float:
    """気孔 1 個の CNR の閉形式: 平均弦長 (2/3)d × μ/(1+SPR) × √(画素数) / σ_rel。"""
    n_pix = np.pi * (d_mm / (2 * PX)) ** 2
    return (2.0 / 3.0) * d_mm * MU / (1.0 + spr) * np.sqrt(n_pix) / s_rel


# --------------------------------------------------------------------------- #
# 1. 場面とゼロ点                                                                #
# --------------------------------------------------------------------------- #
def section_scene() -> dict:
    print("\n" + "=" * 78)
    print("1) 場面とゼロ点 —— 固定しきい値は余盛の断面を拾う")
    print("=" * 78)
    rng = np.random.default_rng(SEED)
    pores = [(CAP_ROW - 20, 60.0, 0.5), (CAP_ROW + 15, 110.0, 0.8), (CAP_ROW - 5, 160.0, 1.2),
             (CAP_ROW + 25, 205.0, 1.6), (CAP_ROW - 30, 250.0, 2.2), (CAP_ROW + 5, 290.0, 0.35)]
    sc = render(pores, rng, wires=True)
    sc_np = render(pores, np.random.default_rng(SEED), wires=False)
    true_area = sum(np.pi * (d / 2) ** 2 for _, _, d in pores)
    print("  気孔 %d 個、直径 %s mm、合計投影面積 %.2f mm²、最大径 %.2f mm"
          % (len(pores), " / ".join("%.2f" % d for _, _, d in pores), true_area, max(d for _, _, d in pores)))
    print("  余盛中央 / つま先の透過率比 exp(−μ·%.0f mm) = %.3f(つま先は %.0f %% 明るい)"
          % (CAP_H, np.exp(-MU * CAP_H), 100 * (np.exp(MU * CAP_H) - 1)))
    s_rel = noise_rel(sc_np["img"])
    print("  余盛の帯の相対雑音 σ/I = %.4f(estimate_noise)" % s_rel)

    zp = zero_point(sc_np["img"])
    fz = zp["feat"]
    print("\n  ゼロ点(帯の中央値 + %.0fσ の固定しきい値): 塊 %d 個、合計面積 %.2f mm²、最大径 %.2f mm"
          % (K_SIGMA, fz["n"], float(fz["area"].sum()), float(fz["equiv_diameter"].max()) if fz["n"] else 0.0))
    det = detect(sc_np["img"], "grind")
    m = match(det, pores)
    fd = det["feat"]
    print("  fullseye(山削り背景 + 対数コントラスト %.1fσ): 塊 %d 個(一致 %d / 偽陽性 %d / 見落とし %d)、合計面積 %.2f mm²"
          % (K_SIGMA, fd["n"], len(m["pairs"]), len(m["fp"]), len(m["miss"]), float(fd["area"].sum())))
    print("     真値 d [mm]   しきい値径   体積径   キャリパ径")
    for i, j in m["pairs"]:
        dd = diameters(det, j)
        print("        %5.2f        %5.2f      %5.2f     %5.2f" % (pores[i][2], dd["d_thr"], dd["d_vol"], dd["d_cal"]))

    figs.save_grid("scene_radiograph",
                   [sc["img"], sc["thick"], sc_np["img"], det["c"]],
                   ["透過像(IQI 針金 7 本つき、明 = 薄い)", "透過厚 L [mm](余盛 + 気孔の弦長)",
                    "透過像(IQI なし、気孔 6 個)", "対数コントラスト ln(I/背景)(山削り)"],
                   title="溶接部の X 線透過像(1 px = %.1f mm、板厚 %.0f mm)" % (PX, T_PLATE),
                   caption="余盛は暗い帯、気孔は明るい斑点。背景を引いて対数を取ると弦長 × μ に戻る。")
    figs.save_grid("map_detections",
                   [_LAB.blob_overlay(sc_np["img"], zp["labels"]), _LAB.blob_overlay(sc_np["img"], det["labels"])],
                   ["ゼロ点: 固定しきい値(塊 %d 個)" % fz["n"], "fullseye: 山削り + %.0fσ(塊 %d 個)" % (K_SIGMA, fd["n"])],
                   title="固定しきい値は余盛のつま先を拾う")
    return {"zero_n": int(fz["n"]), "zero_area": float(fz["area"].sum()), "true_area": true_area,
            "zero_dmax": float(fz["equiv_diameter"].max()) if fz["n"] else 0.0,
            "fs_n": int(fd["n"]), "fs_fp": len(m["fp"]), "fs_miss": len(m["miss"]), "s_rel": s_rel}


# --------------------------------------------------------------------------- #
# 2. 直径を振る —— 検出の崖と、背景 op の大きさの天井                           #
# --------------------------------------------------------------------------- #
def section_diameter_sweep(s_rel: float) -> dict:
    print("\n" + "=" * 78)
    print("2) 直径 0.3 → 3.0 mm —— 検出率(予測 CNR つき)と直径の偏り")
    print("=" * 78)
    ds = (0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.4, 2.0, 2.5, 3.0)
    methods = ("grind", "open9", "diam34")
    rate = {mth: [] for mth in methods}
    fp = {mth: [] for mth in methods}
    err = {"d_thr": [], "d_vol": [], "d_cal": []}
    pred_thr = []
    print("   d [mm]  CNR予測   検出率: 山削り  9px開  直径開  |  偽陽性/枚  |  直径誤差 %%: しきい値  体積  キャリパ  (しきい値の予測)")
    for d in ds:
        hit = {mth: 0 for mth in methods}
        fpn = {mth: 0 for mth in methods}
        tot = 0
        e = {k: [] for k in err}
        for seed in range(3):
            rng = np.random.default_rng(100 + seed)
            n = 12 if d <= 1.4 else 8
            pores = [(CAP_ROW + (25 if k % 2 else -25), 20 + (k + 0.5) * (W - 40) / n, d) for k in range(n)]
            sc = render(pores, rng, spr=0.0)
            tot += n
            for mth in methods:
                det = detect(sc["img"], mth)
                m = match(det, pores)
                hit[mth] += len(m["pairs"])
                fpn[mth] += len(m["fp"])
                if mth == "grind":
                    for i, j in m["pairs"]:
                        dd = diameters(det, j)
                        for k in e:
                            if np.isfinite(dd[k]):
                                e[k].append(100 * (dd[k] - d) / d)
        for mth in methods:
            rate[mth].append(100.0 * hit[mth] / tot)
            fp[mth].append(fpn[mth] / 3.0)
        for k in err:
            err[k].append(float(np.mean(e[k])) if e[k] else np.nan)
        # しきい値径の予測: 弦長 μ·2√(R²−r²) = thr の等高線 → d_thr = √(d² − (thr/μ)²)
        thr = K_SIGMA * s_rel / (2 * np.sqrt(np.pi) * SMOOTH_SIG)
        pt = 100 * (np.sqrt(max(d * d - (thr / MU) ** 2, 0)) / d - 1)
        pred_thr.append(pt)
        print("   %4.2f   %6.2f     %6.1f  %6.1f  %6.1f   |   %4.2f   |   %+6.1f  %+6.1f  %+6.1f   (%+6.1f)"
              % (d, cnr_pred(d, s_rel), rate["grind"][-1], rate["open9"][-1], rate["diam34"][-1],
                 fp["grind"][-1], err["d_thr"][-1], err["d_vol"][-1], err["d_cal"][-1], pt))

    # 50 % 交点(山削り)を線形補間で
    r = np.array(rate["grind"])
    d50 = float(np.interp(50.0, r[:5], np.array(ds[:5]))) if r[0] < 50 < r[4] else np.nan
    k_pred = 4.0
    d50_pred = float(np.sqrt(k_pred * (3 * PX * s_rel) / (MU * np.sqrt(np.pi))))
    print("\n  ★予測: CNR = %.0f を 50 %% 検出の目安に置くと d₅₀ = %.2f mm(CNR = %.2f·d²)。"
          % (k_pred, d50_pred, cnr_pred(1.0, s_rel)))
    print("     実測の 50 %% 交点 = %.2f mm(そこでの CNR = %.2f)。" % (d50, cnr_pred(d50, s_rel)))
    cliff9 = [d for d, rt in zip(ds, rate["open9"]) if rt < 50]
    print("  ★9 px オープニングの検出率が 50 %% を割る最小径 = %s mm(op の窓の天井 = 0.9 mm)。"
          % ("%.1f" % cliff9[0] if cliff9 else "なし"))
    print("     直径オープニング(34 px)は %.1f mm で %.0f %%、山削りは %.0f %%。"
          % (ds[-1], rate["diam34"][-1], rate["grind"][-1]))

    figs.save_plot("detect_vs_diameter",
                   [("山削り(再構成)", ds, rate["grind"]), ("9 px 矩形オープニング", ds, rate["open9"]),
                    ("直径オープニング 34 px", ds, rate["diam34"])],
                   xlabel="気孔の直径 [mm]", ylabel="検出率 [%]", title="検出の崖(小さい側)と背景 op の天井(大きい側)",
                   caption="小さい側の崖は CNR で予測どおり。大きい側の崖は背景推定 op の構造要素の大きさそのもの。")
    figs.save_plot("cnr_prediction", [("予測 CNR = %.1f·d²" % cnr_pred(1.0, s_rel), ds, [cnr_pred(d, s_rel) for d in ds]),
                                      ("検出率 [%] ÷ 10(山削り)", ds, [x / 10 for x in rate["grind"]])],
                   xlabel="気孔の直径 [mm]", ylabel="CNR / (検出率 ÷ 10)", title="CNR の閉形式と検出率(50 % は CNR≈4)",
                   xlim=(0.25, 1.05), ylim=(0, 12))
    figs.save_plot("diameter_error",
                   [("しきい値の面積径", ds, err["d_thr"]), ("積分コントラスト(体積)径", ds, err["d_vol"]),
                    ("キャリパ(エッジ対)径", ds, err["d_cal"]), ("しきい値径の予測 √(d²−(thr/μ)²)", ds, pred_thr)],
                   xlabel="気孔の直径 [mm]", ylabel="直径の相対誤差 [%]", title="直径 3 通り: 偏りの向きも大きさも違う",
                   caption="面積径は小さい側で縮む(等高線が内側)。体積径は μ 既知なら偏らない。キャリパは縁が外へ出る。")
    return {"ds": ds, "rate": rate, "err": err, "d50": d50, "d50_pred": d50_pred, "cliff9": cliff9[0] if cliff9 else np.nan,
            "rate_diam34_last": rate["diam34"][-1]}


# --------------------------------------------------------------------------- #
# 3. 余盛のつま先からの距離                                                      #
# --------------------------------------------------------------------------- #
def section_toe_distance() -> dict:
    print("\n" + "=" * 78)
    print("3) 余盛のつま先(明暗の段)からの距離 —— 壊れるのは大窓平滑だけ")
    print("=" * 78)
    deltas = (0.0, 0.25, 0.5, 1.0, 1.5, 2.5)
    methods = ("grind", "open9", "gauss3", "row")
    d = 0.8
    toe_row = CAP_ROW - CAP_W / (2 * PX)          # 上のつま先の行
    rate = {m: [] for m in methods}
    fp = {m: [] for m in methods}
    print("   距離 δ [mm]   検出率 %%: 山削り  9px開  ガウス3  行プロファイル  |  偽陽性/枚: 山削り  9px開  ガウス3  行")
    for dl in deltas:
        hit = {m: 0 for m in methods}
        fpn = {m: 0 for m in methods}
        tot = 0
        for seed in range(2):
            rng = np.random.default_rng(300 + seed)
            n = 10
            pores = [(toe_row + dl / PX, 20 + (k + 0.5) * (W - 40) / n, d) for k in range(n)]
            sc = render(pores, rng, spr=0.0)
            tot += n
            for m in methods:
                det = detect(sc["img"], m)
                mm = match(det, pores)
                hit[m] += len(mm["pairs"])
                fpn[m] += len(mm["fp"])
        for m in methods:
            rate[m].append(100.0 * hit[m] / tot)
            fp[m].append(fpn[m] / 2.0)
        print("      %4.2f        %6.1f  %6.1f  %6.1f    %6.1f        |     %5.1f   %5.1f   %5.1f   %5.1f"
              % (dl, *[rate[m][-1] for m in methods], *[fp[m][-1] for m in methods]))
    near = [i for i, dl in enumerate(deltas) if dl <= 0.5]
    fp_g = float(np.mean([fp["gauss3"][i] for i in near]))
    fp_o = float(np.mean([fp["grind"][i] for i in near] + [fp["open9"][i] for i in near]))
    print("\n  ★予想は「オープニング系もつま先で偽陽性を出す」だったが、実測: つま先 0.5 mm 以内の偽陽性は"
          "\n     ガウス σ=3 px %.1f 個/枚、オープニング系(山削り・9 px)%.1f 個/枚。段差はオープニングでは崩れない。"
          % (fp_g, fp_o))

    rng = np.random.default_rng(301)
    sc = render([(toe_row + 0.25 / PX, 20 + (k + 0.5) * 30, d) for k in range(10)], rng, spr=0.0)
    panels = [detect(sc["img"], m)["c"] for m in ("gauss3", "grind")]
    figs.save_grid("map_toe_backgrounds", [sc["img"][60:140]] + [p[60:140] for p in panels],
                   ["透過像(気孔 0.8 mm をつま先の 0.25 mm 内側に 10 個)", "ガウス σ=3 の背景: つま先に明るい帯が残る",
                    "山削りの背景: 段が保存される"], title="つま先(余盛の縁)の近くの背景推定", ncols=1,
                   caption="大窓平滑は段をぼかすので明るい側に残差の帯が出る。オープニング系は下に凸の角を保存する。")
    figs.save_plot("toe_false_positives", [(m_ja, deltas, fp[m]) for m, m_ja in
                                           (("gauss3", "ガウス σ=3"), ("grind", "山削り"), ("open9", "9 px 開"), ("row", "行プロファイル"))],
                   xlabel="つま先からの距離 δ [mm]", ylabel="偽陽性 [個/枚]", title="つま先の近くの偽陽性(気孔 0.8 mm)")
    return {"deltas": deltas, "rate": rate, "fp": fp, "fp_gauss_near": fp_g, "fp_open_near": fp_o}


# --------------------------------------------------------------------------- #
# 4. 散乱かぶり                                                                 #
# --------------------------------------------------------------------------- #
def section_scatter() -> dict:
    print("\n" + "=" * 78)
    print("4) 散乱かぶり(SPR)—— 直径はどれだけ縮むか(予測つき)")
    print("=" * 78)
    sprs = (0.0, 0.25, 0.5, 1.0, 2.0)
    sizes = (0.6, 1.2, 2.4)
    out = {d: {"thr": [], "vol": [], "rate": []} for d in sizes}
    print("   SPR    d [mm]  検出率 %%   しきい値径 誤差 %% (予測)   体積径 誤差 %% (予測 (1+SPR)^(-1/3))")
    panels, caps = [], []
    for spr in sprs:
        rng = np.random.default_rng(500)
        pores = []
        for k, d in enumerate(sizes):
            for q in range(4):
                pores.append((CAP_ROW + (-28, 0, 28)[k], 30 + (q + 0.5) * (W - 60) / 4 + k * 20, d))
        sc = render(pores, rng, spr=spr)
        det = detect(sc["img"], "grind")
        m = match(det, pores)
        if spr in (0.0, 1.0, 2.0):
            panels.append(det["c"])
            caps.append("SPR = %.1f: ln(I/背景)" % spr)
        s_rel = det["s_rel"]
        thr = K_SIGMA * s_rel / (2 * np.sqrt(np.pi) * SMOOTH_SIG)
        for d in sizes:
            e_thr, e_vol, hit = [], [], 0
            for i, j in m["pairs"]:
                if abs(pores[i][2] - d) < 1e-9:
                    dd = diameters(det, j)
                    e_thr.append(100 * (dd["d_thr"] - d) / d)
                    e_vol.append(100 * (dd["d_vol"] - d) / d)
                    hit += 1
            p_thr = 100 * (np.sqrt(max(d * d - ((1 + spr) * thr / MU) ** 2, 0)) / d - 1)
            p_vol = 100 * ((1 + spr) ** (-1 / 3) - 1)
            out[d]["thr"].append(float(np.mean(e_thr)) if e_thr else np.nan)
            out[d]["vol"].append(float(np.mean(e_vol)) if e_vol else np.nan)
            out[d]["rate"].append(100.0 * hit / 4)
            print("   %4.2f   %4.2f    %5.0f      %+7.1f (%+6.1f)          %+7.1f (%+6.1f)"
                  % (spr, d, out[d]["rate"][-1], out[d]["thr"][-1], p_thr, out[d]["vol"][-1], p_vol))
    i1 = sprs.index(1.0)
    print("\n  ★SPR = 1.0: 体積径 %+.1f %%(予測 %+.1f %%)、しきい値径は 0.6 mm 気孔で %+.0f %%。"
          % (float(np.nanmean([out[d]["vol"][i1] for d in sizes])), 100 * (2 ** (-1 / 3) - 1), out[0.6]["thr"][i1]))
    print("     1.2 mm の気孔が SPR = 1.0 でしきい値径 %.2f mm → 等級の境目 1 mm を%s。"
          % (1.2 * (1 + out[1.2]["thr"][i1] / 100), "またぐ" if 1.2 * (1 + out[1.2]["thr"][i1] / 100) <= 1.0 else "またがない"))
    figs.save_grid("frames_scatter", panels, caps, title="散乱かぶりでコントラストが薄まる(対数コントラスト)", ncols=3)
    figs.save_plot("scatter_diameter_bias",
                   [("しきい値径 0.6 mm", sprs, out[0.6]["thr"]), ("しきい値径 1.2 mm", sprs, out[1.2]["thr"]),
                    ("体積径(3 径の平均)", sprs, [float(np.nanmean([out[d]["vol"][i] for d in sizes])) for i in range(len(sprs))]),
                    ("予測 (1+SPR)^(-1/3)", sprs, [100 * ((1 + s) ** (-1 / 3) - 1) for s in sprs])],
                   xlabel="散乱/一次線比 SPR", ylabel="直径の相対誤差 [%]", title="散乱かぶりは直径を縮める",
                   caption="体積径は (1+SPR)^(-1/3) で縮む。しきい値径は小さい気孔ほど速く縮み、消える。")
    return {"sprs": sprs, "out": out}


# --------------------------------------------------------------------------- #
# 5. IQI(針金)の視認限界と気孔の検出限界                                        #
# --------------------------------------------------------------------------- #
def section_iqi(s_rel: float, d50: float) -> dict:
    print("\n" + "=" * 78)
    print("5) IQI 針金の視認限界 vs 気孔の検出限界 —— 別の物差し")
    print("=" * 78)
    rng = np.random.default_rng(900)
    sc = render([], rng, spr=0.0, wires=True)
    img = sc["img"]
    span = 1.0
    rows = []
    vis = []
    print("   針金   d [mm]   コントラスト振幅   CNR(10 mm 平均)  見える?   同じ CNR の気孔径 [mm]")
    k_cnr = cnr_pred(1.0, s_rel)
    for k, dw in enumerate(WIRES_MM):
        col = 40 + k * WIRE_PITCH_MM / PX
        mh = _LAB.gen_measure_rectangle2(CAP_ROW, col, 0.0, 6, 50, img.shape)   # 幅方向に ±50 行 = 10 mm 平均
        pairs = _LAB.measure_pairs(img, mh, sigma=1.0, threshold=0.0005)
        prof_noise = s_rel * float(np.median(img[int(CAP_ROW - 50):int(CAP_ROW + 50), int(col) - 3:int(col) + 4])) / np.sqrt(101)
        amp = 0.0
        if pairs:
            best = min(pairs, key=lambda p: abs(0.5 * (p["first"] + p["second"]) - 6))
            amp = abs(float(best["first_amplitude"]))
        cnr = amp / (prof_noise * 2 * np.sqrt(np.pi) * 1.0 ** 0.5)     # 平滑 σ=1 の後の雑音
        visible = cnr >= 3.0
        vis.append(visible)
        d_eq = float(np.sqrt(cnr / k_cnr))
        rows.append(("W%d" % (10 + k), "%.3f" % dw, "%.4f" % amp, "%.1f" % cnr, "○" if visible else "×", "%.2f" % d_eq))
        print("   W%-3d   %.3f      %.4f          %5.1f         %s        %.2f" % (10 + k, dw, amp, cnr, "○" if visible else "×", d_eq))
    smallest = [dw for dw, v in zip(WIRES_MM, vis) if v]
    d_w = min(smallest) if smallest else np.nan
    idx = WIRES_MM.index(d_w) if smallest else -1
    print("\n  ★見える最細の針金 = %.3f mm(板厚の %.1f %%)。気孔の 50 %% 検出限界は %.2f mm —— %.1f 倍。"
          % (d_w, 100 * d_w / T_PLATE, d50, d50 / d_w))
    print("     針金は 10 mm の長さで積分できるので薄くても見える。同じ CNR に換算すると W%d ≒ 気孔 %s mm。"
          % (10 + idx, rows[idx][5] if idx >= 0 else "?"))
    figs.save_table("iqi_visibility", ["針金", "直径 [mm]", "振幅", "CNR", "見える", "同 CNR の気孔径 [mm]"], rows,
                    title="IQI 針金の視認と、同じ CNR の気孔の直径", caption="視認基準 CNR ≥ 3(Rose)。")
    return {"d_wire": d_w, "ratio": d50 / d_w, "rows": rows}


# --------------------------------------------------------------------------- #
# 6. 等級を 1 段間違える割合(対照群つき)                                         #
# --------------------------------------------------------------------------- #
def section_grading() -> dict:
    print("\n" + "=" * 78)
    print("6) 等級を 1 段間違える画像の割合 —— 原因を「見落とし / 直径 / 偽陽性」で分ける")
    print("=" * 78)
    conds = (("基準(余盛あり・SPR 0.5)", True, SPR_BASE), ("対照: 散乱なし", True, 0.0),
             ("対照: 余盛なし", False, SPR_BASE), ("対照: 両方なし", False, 0.0))
    n_img = 30
    table = []
    res = {}
    print("   条件                   ゼロ点   山削り+しきい値径  山削り+体積径 | 内訳(体積径): 見落とし  直径  偽陽性 | 見落とし率(>%.1f mm)" % D_IGNORE)
    for name, cap, spr in conds:
        wrong = {"zero": 0, "thr": 0, "vol": 0}
        cause = {"miss": 0, "diam": 0, "fp": 0}
        n_true, n_miss = 0, 0
        for k in range(n_img):
            rng = np.random.default_rng(1000 + k)
            pores = place_pores(rng, int(rng.poisson(5)) + 2, 0.3, 3.0)
            sc = render(pores, rng, cap=cap, spr=spr)
            g_true = grade([(c, d) for _, c, d in pores])
            zp = zero_point(sc["img"])
            fz = zp["feat"]
            g_zero = grade([(float(fz["col"][j]), float(fz["equiv_diameter"][j])) for j in range(int(fz["n"]))])
            det = detect(sc["img"], "grind")
            m = match(det, pores)
            f = det["feat"]
            tp_thr, tp_vol, tp_true = [], [], []
            for i, j in m["pairs"]:
                dd = diameters(det, j)
                tp_thr.append((pores[i][1], dd["d_thr"]))
                tp_vol.append((pores[i][1], dd["d_vol"]))
                tp_true.append((pores[i][1], pores[i][2]))
            fp_vol = [(float(f["col"][j]), diameters(det, j)["d_vol"]) for j in m["fp"]]
            fp_thr = [(float(f["col"][j]), diameters(det, j)["d_thr"]) for j in m["fp"]]
            g_thr = grade(tp_thr + fp_thr)
            g_vol = grade(tp_vol + fp_vol)
            wrong["zero"] += g_zero != g_true
            wrong["thr"] += g_thr != g_true
            wrong["vol"] += g_vol != g_true
            cause["miss"] += grade(tp_true) != g_true
            cause["diam"] += grade(tp_vol) != grade(tp_true)
            cause["fp"] += grade(tp_vol + fp_vol) != grade(tp_vol)
            big = [i for i, p in enumerate(pores) if p[2] > D_IGNORE]
            n_true += len(big)
            n_miss += len([i for i in m["miss"] if i in big])
        pc = {k: 100.0 * v / n_img for k, v in wrong.items()}
        cc = {k: 100.0 * v / n_img for k, v in cause.items()}
        miss_rate = 100.0 * n_miss / max(n_true, 1)
        res[name] = {"wrong": pc, "cause": cc, "miss_rate": miss_rate}
        table.append((name, "%.0f %%" % pc["zero"], "%.0f %%" % pc["thr"], "%.0f %%" % pc["vol"],
                      "%.0f %%" % cc["miss"], "%.0f %%" % cc["diam"], "%.0f %%" % cc["fp"], "%.1f %%" % miss_rate))
        print("   %-22s %5.0f %%      %5.0f %%          %5.0f %%     |            %5.0f %%  %5.0f %%  %5.0f %% |   %.1f %%"
              % (name, pc["zero"], pc["thr"], pc["vol"], cc["miss"], cc["diam"], cc["fp"], miss_rate))
    base = res[conds[0][0]]
    print("\n  ★基準条件で等級を 1 段間違える割合: ゼロ点 %.0f %% / しきい値径 %.0f %% / 体積径 %.0f %%。"
          % (base["wrong"]["zero"], base["wrong"]["thr"], base["wrong"]["vol"]))
    print("     内訳(体積径): 見落とし %.0f %%・直径 %.0f %%・偽陽性 %.0f %% —— 無視径 %.1f mm 超の見落とし率は %.1f %% なので"
          "\n     等級を壊すのは 1 mm の境目をまたぐ直径誤差(散乱を止めると %.0f %%)。"
          % (base["cause"]["miss"], base["cause"]["diam"], base["cause"]["fp"], D_IGNORE, base["miss_rate"],
             res[conds[1][0]]["wrong"]["vol"]))
    figs.save_table("grade_errors", ["条件", "ゼロ点", "しきい値径", "体積径", "内訳: 見落とし", "直径", "偽陽性", "見落とし率"],
                    table, title="等級を 1 段間違える画像の割合(30 枚 × 4 条件)",
                    caption="ゼロ点は余盛を拾って全滅。fullseye は見落としでなく直径の誤分類で間違える。")
    return res


# --------------------------------------------------------------------------- #
# 7. 道具の穴                                                                    #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("7) 道具の穴(公開経路に無かった処理)")
    print("=" * 78)
    # (a) sk_rolling_ball は [0,1] 画像では実質 identity(球の半径が輝度単位でも 5〜25)
    yy, xx = np.mgrid[0:64, 0:64]
    dome = 0.45 + 0.05 * np.sqrt(np.clip(1 - ((yy - 32) ** 2 + (xx - 32) ** 2) / 10 ** 2, 0, 1))
    rb = float(np.asarray(fs.apply(dome, "sk_rolling_ball", a=0.5))[32, 32])
    assert rb < 1e-3, rb
    print("  (a) sk_rolling_ball は [0,1] の画像では**何も引かない**(高さ 0.05・幅 20 px の山の残差 %.4f)。"
          "\n      球の半径 5〜25 が輝度単位でもそのまま使われ、針のような球になる(skimage の ellipsoid_kernel 相当が要る)。" % rb)
    # (b) 背景推定の窓が 9 px / σ 3 px で頭打ち
    print("  (b) 矩形オープニング・平均・中央値の窓は 9 px、ガウスは σ 3 px が上限 —— 1 mm 超の気孔は背景に食われる。"
          "\n      直径オープニングは 34 px まで振れるが 0.2 s/枚。行方向の長窓(中央値など)は自前 numpy。")
    # (c) Beer–Lambert の線形化 −ln(I/I0) が無い
    lg = np.asarray(fs.apply(np.full((8, 8), 0.5), "log_image"))
    assert abs(float(lg[0, 0]) - (-np.log(0.5))) > 0.05
    print("  (c) 透過像を μ·L に戻す −ln(I/I0) の op が無い(log_image は表示用の圧縮で値が違う)。対数は自前。")
    # (d) 散乱(大窓ぼかし)を作る/引く op が無い、等級の点数法は自前
    print("  (d) 散乱かぶりの大窓(σ 40 px)ぼかしと、等級の点数法(試験視野の走査)は自前。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("溶接部の X 線透過像から気孔を検出・寸法評価 —— 等級を 1 段間違える画像の割合")
    print("視野 %d × %d px = %.1f × %.1f mm、板厚 %.0f mm、余盛 %.0f × %.0f mm、μ = %.2f /mm" % (
        W, H, W * PX, H * PX, T_PLATE, CAP_W, CAP_H, MU))
    print("=" * 78)

    s1 = section_scene()
    s2 = section_diameter_sweep(s1["s_rel"])
    s3 = section_toe_distance()
    s4 = section_scatter()
    s5 = section_iqi(s1["s_rel"], s2["d50"])
    s6 = section_grading()
    section_tool_gaps()

    # 所見を固定する(壊れたら鳴る)
    assert s1["zero_area"] > 1.5 * s1["true_area"], s1
    assert s1["fs_miss"] <= 1 and s1["fs_fp"] <= 1, s1
    assert 0.35 <= s2["d50"] <= 0.7, s2["d50"]
    assert abs(s2["d50"] - s2["d50_pred"]) / s2["d50_pred"] < 0.3, (s2["d50"], s2["d50_pred"])
    assert s2["rate"]["grind"][-1] >= 90 and s2["rate"]["open9"][-1] <= 30, s2["rate"]
    assert s2["rate_diam34_last"] >= 90
    assert s3["fp_gauss_near"] > s3["fp_open_near"] + 0.5, (s3["fp_gauss_near"], s3["fp_open_near"])
    v1 = s4["out"][1.2]["vol"][s4["sprs"].index(1.0)]
    assert -30 < v1 < -10, v1
    assert s5["ratio"] > 1.5, s5["ratio"]
    base = s6["基準(余盛あり・SPR 0.5)"]
    assert base["wrong"]["zero"] >= 80 and base["wrong"]["vol"] < base["wrong"]["zero"], base

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 検出の崖 d₅₀ = %.2f mm は CNR の閉形式(予測 %.2f mm)で先に出せる。" % (s2["d50"], s2["d50_pred"]))
    print("  * 背景 op の大きさの天井(9 px)は %.1f mm から上の崖になる。" % s2["cliff9"])
    print("  * 散乱 SPR=1 で体積径 %+.0f %%。等級の境目をまたぐ。" % v1)
    print("  * 等級を 1 段間違える割合: ゼロ点 %.0f %% → 体積径 %.0f %%(内訳は直径の誤分類)。"
          % (base["wrong"]["zero"], base["wrong"]["vol"]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
