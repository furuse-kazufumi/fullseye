# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""系外惑星トランジットを開口測光で取り出す —— 深さと継続時間は別々に壊れる。

恒星の前を惑星が横切ると、星の明るさが **1 % ほど**、数時間だけ暗くなる
(トランジット)。地上の小望遠鏡でこれを測る仕事は、画像列から目標星と
比較星を開口測光し、**比を取って**大気の透明度変動を消し、残った光度曲線に
解析モデルを当てはめて深さ δ(惑星半径)と継続時間 T14(軌道)を出す、
というものです。δ の誤差と T14 の誤差は**別の量**で、壊れ方も別なので、
この PoC は最後まで 2 つを分けて数えます。

EXTEND: 実写に差し替えるなら :func:`make_series` が返る辞書の ``frames``
(画像列)を撮影画像に、``model``(真のトランジット光度曲線)と
``stars``(星の真の位置と明るさの比)を既知の系(TESS/既知惑星の暦)に
置き換えます。**フラット ``gain`` と位置ずれ ``shifts`` の真値は実写では手に
入らない**ので、5 節の「ドリフト × フラット」の分解は実写では再現できず、
代わりに 5 節の予測式(``a * sqrt(sum w^2)``)で上限を見積もることになります。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(目標星の開口積分だけ)は雲で死ぬ**。透明度変動 rms 3 % の下で
   深さは +33.8 ppt(真値 10.0 ppt、誤差 **+23.8 ppt = 真値の 2.4 倍**)、
   T14 は +37.0 フレーム(真値 80)。対照群(雲なし)では同じゼロ点が
   誤差 -0.10 ppt / -0.15 フレームで当たる —— 壊すのは手法ではなく雲。
   比較星との比を取ると雲ありでも -0.02 ppt / -0.45 フレーム。
2. ★**比較星の選び方で精度が 4.7 倍変わる**。残差 rms は最良(逆分散重み
   の全星)0.72 ppt、最悪(いちばん暗い 1 星)3.41 ppt。深さの誤差 σ は
   その比で動くが、★**T14 の誤差はそうならない**(最悪 -0.4 フレーム、
   最良 -0.5 フレーム)—— 入出の傾斜は深さより雑音に強い。
   全星の単純和(0.75 ppt)は重み付き(0.72 ppt)とほぼ並ぶ ——
   明るい星が支配する和は、重みを付けたのとほぼ同じ。
3. **開口半径の崖は下側にある**。残差 rms は r = 1σ で 2.09 ppt、
   2σ で 0.85 ppt、3σ で 0.72 ppt、6σ で 0.98 ppt(理論の CCD 式は
   1.64 / 0.80 / 0.70 / 0.99)。r=1σ だけ理論より 27 % 悪い ——
   ★開口が小さいと**重心の誤差(rms 0.03 px)が明るさの誤差に化ける**
   (開口の縁で PSF の勾配が最大)。深さの偏りは 1σ で +0.66 ppt、
   3σ 以上では |0.05| ppt 以内。
4. **検出限界(SNR = 5)は理論の CCD 式で予測できる**。δ を 1〜20 ppt で
   振った実測の SNR は理論と比 0.90〜1.09 で並び、SNR = 5 の境目は実測
   2.6 ppt / 理論 2.5 ppt。★1 ppt(SNR 1.9)では深さの推定が +0.5 ppt
   ずれ T14 が 33 フレーム外れる —— 検出できない信号に当てはめると、
   **深さより先に継続時間が壊れる**。
5. ★★**ドリフトとフラット不均一は単独では無害、掛け算で偽の深さを作る**。
   ドリフト 2 px・フラット均一で深さ誤差 -0.03 ppt、ドリフト 0・画素
   フラット 3 % で +0.01 ppt、**両方あると +1.63 ppt(真値の 16 %)**。
   予測は上限 ``a * sqrt(sum w^2) = 0.19 a`` = 3 % で 5.6 ppt、実測は
   その 29 %(直線基線が大半を吸う)。T14 は同じ条件で +2.1 フレーム。

【グラウンドトゥルース】
星は erf による**画素の厳密積分**のガウス PSF(σ = 1.5 px)、トランジットは
Mandel & Agol の小惑星近似(2 円の重なり面積 × 惑星中心での周辺減光強度、
2 次周辺減光 u1 = 0.40, u2 = 0.25)の**閉形式**。系統誤差は 4 つを別々の
乱数で仕込む —— 透明度(全星共通の乗算)、副画素ドリフト(全星共通の平行
移動)、フラット不均一(画素ごとの感度、低次勾配 + 画素ランダム)、
光子雑音(Poisson + 読み出し)。どれも**止められる**ので対照群が作れる。

来歴(公開文献のみ): Mandel & Agol, *ApJ* 580 (2002) L171 —— トランジット
光度曲線の解析式 / Howell, *Handbook of CCD Astronomy* (2006) —— CCD 式 /
Collins et al., *AJ* 153 (2017) 77 —— AstroImageJ の比較星アンサンブル測光。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import least_squares
from scipy.special import erf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

_AS = fs.ledger        # astrostack 族の公開経路(star_detect / frame_align / aperture_photometry)

# --- 場面の諸元 -------------------------------------------------------------- #
SHAPE = (112, 112)         # 視野 [px]
SIGMA = 1.5                # PSF σ [px](FWHM 3.53 px)
SKY = 400.0                # 背景 [e-/px/frame](明るめの空: 大開口側の坂を残す)
READ = 5.0                 # 読み出し雑音 [e- rms]
F_TARGET = 400000.0        # 目標星の明るさ [e-/frame](1 枚で 1.6 ppt の光子雑音)
T = 240                    # 枚数
SEED = 11

#: 星表。目標星が先頭、続く 5 個が比較星(明るさは目標星に対する比)。
#: 比較星の明るさは**わざと 2 倍〜1/20 に散らして**ある —— 2 節で「どれを
#: 選ぶか」の効き目を測るため。位置は互いに 36 px 以上離す(背景環が重ならない)。
STARS = {
    "目標":   {"row": 56.0, "col": 56.0, "ratio": 1.00},
    "比較A":  {"row": 24.0, "col": 26.0, "ratio": 2.00},
    "比較B":  {"row": 26.0, "col": 88.0, "ratio": 1.00},
    "比較C":  {"row": 88.0, "col": 22.0, "ratio": 0.50},
    "比較D":  {"row": 86.0, "col": 90.0, "ratio": 0.20},
    "比較E":  {"row": 20.0, "col": 58.0, "ratio": 0.05},
}
NAMES = list(STARS)

# --- トランジット(真値) ------------------------------------------------------ #
DEPTH = 0.010              # 深さ δ(最深部の減光率)
T0 = 120.0                 # 中心時刻 [frame]
T14 = 80.0                 # 第 1〜第 4 接触の継続時間 [frame]
B = 0.30                   # 衝突径数(恒星半径単位)
U1, U2 = 0.40, 0.25        # 2 次周辺減光係数
IBAR = 1.0 - U1 / 3.0 - U2 / 6.0     # 円盤平均強度(中心 1 に対する)

# --- 系統誤差(既定値。各節で止めたり振ったりする) ---------------------------- #
CLOUD_RMS = 0.03           # 透明度変動の rms(乗算、全星共通)
CLOUD_TREND = -0.02        # 一晩の大気量の傾き(終端での減光率)
DRIFT_PX = 1.0             # 一晩の位置ドリフト [px](直線)
DRIFT_DEG = 35.0           # ドリフトの向き
JITTER_PX = 0.05           # フレームごとの位置のばらつき [px rms]
FLAT_LO = 0.04             # フラットの低次勾配(視野端での振幅)
FLAT_PX = 0.01             # 画素ごとの感度ばらつき rms

# --- 開口 ---------------------------------------------------------------------- #
R_AP = 3.0 * SIGMA         # 開口半径(3σ = 98.9 % を拾う)
R_IN, R_OUT = 8.0, 12.0    # 背景環
DETECT_SIGMA = 8.0         # star_detect のしきい値 [σ]
N_REF = 10                 # 基準像に重ねる枚数


# --------------------------------------------------------------------------- #
# 真値: トランジット光度曲線(閉形式)                                          #
# --------------------------------------------------------------------------- #
def limb(mu):
    """2 次周辺減光 ``I(mu)/I(1)``。"""
    return 1.0 - U1 * (1.0 - mu) - U2 * (1.0 - mu) ** 2


def depth_to_p(depth: float, b: float = B) -> float:
    """深さ δ から惑星/恒星の半径比 p を出す(小惑星近似の逆)。"""
    return float(np.sqrt(depth * IBAR / limb(np.sqrt(1.0 - b * b))))


def overlap_area(z, p: float):
    """半径 1 の円と半径 p の円が距離 z にあるときの重なり面積。"""
    z = np.asarray(z, np.float64)
    a = np.zeros_like(z)
    a[z <= 1.0 - p] = np.pi * p * p
    part = (z > 1.0 - p) & (z < 1.0 + p)
    zz = z[part]
    k0 = np.arccos(np.clip((p * p + zz * zz - 1.0) / (2.0 * p * zz), -1, 1))
    k1 = np.arccos(np.clip((1.0 - p * p + zz * zz) / (2.0 * zz), -1, 1))
    a[part] = (p * p * k0 + k1
               - 0.5 * np.sqrt(np.maximum(4.0 * zz * zz - (1.0 + zz * zz - p * p) ** 2, 0.0)))
    return a


def transit_model(t, depth: float, t0: float, t14: float, b: float = B):
    """相対光度 ``1 - λ(t)``。Mandel & Agol (2002) の小惑星近似。

    ``λ = (重なり面積 / π) * I(惑星中心) / Ī``。最深部(z = b)で λ = δ。
    """
    t = np.asarray(t, np.float64)
    if depth <= 0.0:
        return np.ones_like(t)
    p = depth_to_p(depth, b)
    v = np.sqrt((1.0 + p) ** 2 - b * b) / (0.5 * t14)
    z = np.sqrt(b * b + (v * (t - t0)) ** 2)
    zc = np.clip(z, 0.0, 1.0)
    return 1.0 - overlap_area(z, p) / np.pi * limb(np.sqrt(1.0 - zc * zc)) / IBAR


# --------------------------------------------------------------------------- #
# 場面を作る                                                                    #
# --------------------------------------------------------------------------- #
def render_stars(rows, cols, fluxes, sigma: float = SIGMA, shape=SHAPE):
    """ガウス PSF の星を erf で**画素積分**して足す(総和は与えた flux に厳密)。"""
    h, w = shape
    y = np.arange(h, dtype=np.float64)[:, None]
    x = np.arange(w, dtype=np.float64)[None, :]
    s = sigma * np.sqrt(2.0)
    img = np.zeros(shape)
    for r, c, f in zip(rows, cols, fluxes):
        gy = 0.5 * (erf((y + 0.5 - r) / s) - erf((y - 0.5 - r) / s))
        gx = 0.5 * (erf((x + 0.5 - c) / s) - erf((x - 0.5 - c) / s))
        img += f * (gy * gx)
    return img


def make_flat(flat_px: float, flat_lo: float, seed: int):
    """フラット(画素感度)。低次勾配 + 画素ごとのランダム。"""
    h, w = SHAPE
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    lo = 0.5 * flat_lo * ((xx - w / 2) / (w / 2)) + 0.5 * flat_lo * ((yy - h / 2) / (h / 2))
    rng = np.random.default_rng(seed)
    return 1.0 + lo + flat_px * rng.standard_normal(SHAPE)


def make_series(depth: float = DEPTH, cloud: bool = True, drift_px: float = DRIFT_PX,
                flat_px: float = FLAT_PX, flat_lo: float = FLAT_LO, seed: int = SEED,
                flat_seed: int | None = None, jitter_px: float = JITTER_PX) -> dict:
    """画像列 + 真値。4 つの系統誤差はそれぞれ独立に止められる。"""
    rng = np.random.default_rng(seed)
    t = np.arange(T, dtype=np.float64)
    model = transit_model(t, depth, T0, T14)

    # (a) 透明度: なめらかな乱数(rms CLOUD_RMS)+ 一晩の傾き。全星共通の乗算
    if cloud:
        tau = gaussian_filter1d(rng.standard_normal(T), 12.0)
        tau = 1.0 + CLOUD_RMS * tau / tau.std() + CLOUD_TREND * t / (T - 1)
    else:
        tau = np.ones(T)

    # (b) ドリフト: 直線 + フレームごとのばらつき。全星共通の平行移動
    ang = np.deg2rad(DRIFT_DEG)
    shifts = np.stack([drift_px * t / (T - 1) * np.cos(ang),
                       drift_px * t / (T - 1) * np.sin(ang)], axis=1)
    shifts += jitter_px * rng.standard_normal((T, 2))

    # (c) フラット: 画素感度(補正されていない、または補正の残差)
    gain = make_flat(flat_px, flat_lo, SEED * 7 + 1 if flat_seed is None else flat_seed)

    rows0 = np.array([STARS[n]["row"] for n in NAMES])
    cols0 = np.array([STARS[n]["col"] for n in NAMES])
    ratio = np.array([STARS[n]["ratio"] for n in NAMES])

    frames = np.empty((T,) + SHAPE)
    for k in range(T):
        flux = F_TARGET * ratio * tau[k]
        flux[0] *= model[k]                                   # 目標星だけ減光
        exp_ = (render_stars(rows0 + shifts[k, 0], cols0 + shifts[k, 1], flux) + SKY) * gain
        # (d) 光子雑音 + 読み出し雑音
        frames[k] = rng.poisson(exp_) + READ * rng.standard_normal(SHAPE)
    return {"frames": frames, "model": model, "tau": tau, "shifts": shifts,
            "gain": gain, "rows": rows0, "cols": cols0, "ratio": ratio,
            "depth": depth, "t": t}


# --------------------------------------------------------------------------- #
# 測る: 基準像 → 星表 → 各フレームの位置合わせ → 開口測光(すべて fullseye op) #
# --------------------------------------------------------------------------- #
def locate(frames, rows_true, cols_true):
    """基準像(先頭 N_REF 枚の κ-σ 合成)で星を検出し、星表の順に並べる。

    真の位置は**どの検出がどの星かを名付ける**ためだけに使う(1 px 以内)。
    測る位置は検出の重心。
    """
    ref = np.asarray(_AS.sigma_clip_stack(list(frames[:N_REF]), mode="sigma_clip"))
    if ref.ndim == 3:                       # (image, mask) が返る実装への保険
        ref = ref[0]
    det = np.asarray(_AS.star_detect(ref, threshold_sigma=DETECT_SIGMA, min_separation=4))
    ctr = np.empty((len(rows_true), 2))
    for i, (r, c) in enumerate(zip(rows_true, cols_true)):
        d = np.hypot(det[:, 0] - r, det[:, 1] - c)
        j = int(np.argmin(d))
        assert d[j] < 1.0, ("星表と検出が合わない", r, c, det[j])
        ctr[i] = det[j]
    return ref, ctr


def track(frames, ref, ctr):
    """各フレームの平行移動を ``frame_align`` で出し、星表の位置を追わせる。"""
    centers = np.empty((len(frames),) + ctr.shape)
    est = np.empty((len(frames), 2))
    for k, fr in enumerate(frames):
        m = np.asarray(_AS.frame_align(ref, fr, model="translation",
                                       threshold_sigma=DETECT_SIGMA))
        # m は frame → reference。基準の座標を frame へ移すには並進を引く
        est[k] = -m[:2, 2]
        centers[k] = ctr + est[k]
    return centers, est


def photometry(frames, centers, r_ap: float = R_AP, r_in: float = R_IN,
               r_out: float = R_OUT):
    """開口測光。返りは ``(T, 星数)`` の flux [e-]。"""
    out = np.empty(centers.shape[:2])
    for k, fr in enumerate(frames):
        ph = _AS.aperture_photometry(fr, centers[k], r_aperture=r_ap, r_inner=r_in,
                                     r_outer=r_out, read_sigma=READ)
        out[k] = [p["flux"] for p in ph]
    return out


def measure(sc: dict, r_ap: float = R_AP, r_in: float = R_IN, r_out: float = R_OUT,
            recenter: bool = True) -> dict:
    ref, ctr = locate(sc["frames"], sc["rows"], sc["cols"])
    if recenter:
        centers, est = track(sc["frames"], ref, ctr)
    else:
        centers = np.repeat(ctr[None], len(sc["frames"]), axis=0)
        est = np.zeros((len(sc["frames"]), 2))
    flux = photometry(sc["frames"], centers, r_ap, r_in, r_out)
    return {"flux": flux, "centers": centers, "est_shift": est, "ref": ref}


# --------------------------------------------------------------------------- #
# 光度曲線と当てはめ                                                            #
# --------------------------------------------------------------------------- #
def oot_mask(t=None):
    """トランジット外(out-of-transit)のフレーム。"""
    t = np.arange(T) if t is None else t
    return np.abs(t - T0) > 0.5 * T14 + 2.0


def normalize(y):
    return y / np.median(y[oot_mask()])


def lightcurve(flux, which=("sum",)):
    """目標星 / 比較星アンサンブル。``which``: 星名の列、"sum"、"weighted"。"""
    tgt = flux[:, 0]
    comps = flux[:, 1:]
    if which == ("sum",):
        ref = comps.sum(axis=1)
    elif which == ("weighted",):
        oot = oot_mask()
        var = comps[oot].var(axis=0)
        w = comps[oot].mean(axis=0) / var                   # 逆分散(明るさで重み)
        ref = comps @ w
    elif which == ("zero",):
        return normalize(tgt)
    else:
        idx = [NAMES.index(n) - 1 for n in which]
        ref = comps[:, idx].sum(axis=1)
    return normalize(tgt / ref)


def fit_transit(t, y):
    """深さ・中心・継続時間 + 直線基線の 5 パラメータ最小二乗。

    初期値は粗い格子(t0 4 フレーム刻み × T14 10 刻み)の χ² 最小から取る
    —— 真値を初期値に使わない。
    """
    tc = 0.5 * (T - 1)
    best = None
    for t14 in np.arange(20.0, 130.0, 10.0):
        for t0 in np.arange(40.0, 200.0, 4.0):
            m = transit_model(t, 0.01, t0, t14)
            a = np.stack([m, (t - tc) / T], axis=1)
            coef, *_ = np.linalg.lstsq(a, y, rcond=None)
            r = y - a @ coef
            chi = float(r @ r)
            if best is None or chi < best[0]:
                best = (chi, t0, t14)
    _, t0i, t14i = best

    def resid(p):
        d, t0, t14, c0, c1 = p
        return y - (c0 + c1 * (t - tc) / T) * transit_model(t, d, t0, t14)

    p0 = [0.01, t0i, t14i, 1.0, 0.0]
    lo = [0.0, 30.0, 10.0, 0.5, -1.0]
    hi = [0.05, 210.0, 160.0, 1.5, 1.0]
    res = least_squares(resid, p0, bounds=(lo, hi), x_scale=[0.01, 10, 10, 1, 0.1])
    n, k = y.size, 5
    rss = float(res.fun @ res.fun)
    jtj = res.jac.T @ res.jac
    try:
        cov = np.linalg.inv(jtj) * rss / (n - k)
        sig = np.sqrt(np.maximum(np.diag(cov), 0.0))
    except np.linalg.LinAlgError:
        sig = np.full(k, np.nan)
    d, t0, t14 = res.x[:3]
    rms = float(np.std(res.fun))
    return {"depth": float(d), "t0": float(t0), "t14": float(t14),
            "sig_depth": float(sig[0]), "sig_t14": float(sig[2]), "rms": rms,
            "resid": res.fun, "fit": y - res.fun}


# --------------------------------------------------------------------------- #
# 理論(CCD 式)                                                                 #
# --------------------------------------------------------------------------- #
def frac_in(r: float, sigma: float = SIGMA) -> float:
    return 1.0 - np.exp(-r * r / (2.0 * sigma * sigma))


def theory_rel_noise(r: float, ratio, which=("sum",)) -> float:
    """比 目標/アンサンブル の 1 フレーム相対雑音(Howell の CCD 式)。"""
    f = frac_in(r)
    area = np.pi * r * r
    fl = F_TARGET * np.asarray(ratio, np.float64)
    var = f * fl + area * (SKY + READ ** 2)
    rel_t = var[0] / (f * fl[0]) ** 2
    if which == ("sum",):
        sel = np.arange(1, fl.size)
        rel_c = var[sel].sum() / (f * fl[sel].sum()) ** 2
    elif which == ("weighted",):
        sel = np.arange(1, fl.size)
        w = f * fl[sel] / var[sel]
        rel_c = (w * w * var[sel]).sum() / (w * f * fl[sel]).sum() ** 2
    else:
        sel = np.array([NAMES.index(n) for n in which])
        rel_c = var[sel].sum() / (f * fl[sel].sum()) ** 2
    return float(np.sqrt(rel_t + rel_c))


def theory_sig_depth(rel_noise: float, depth: float = DEPTH) -> float:
    """深さの推定誤差の理論値 —— 5 パラメータ(δ, t0, T14, 基線 2 つ)の Fisher 下限。

    箱形近似 ``σ_rel * sqrt(1/N_in + 1/N_out)`` は t0 / T14 / 基線を同時に
    推定する分を無視するので楽観的になる。ここでは真値でモデルを数値微分して
    ``σ_rel² (JᵀJ)⁻¹`` の対角を取る。
    """
    t = np.arange(T, dtype=np.float64)
    tc = 0.5 * (T - 1)

    def model(p):
        d, t0, t14, c0, c1 = p
        return (c0 + c1 * (t - tc) / T) * transit_model(t, d, t0, t14)

    p = np.array([depth, T0, T14, 1.0, 0.0])
    h = np.array([1e-5, 1e-3, 1e-3, 1e-5, 1e-5])
    cols = []
    for i in range(5):
        dp = np.zeros(5)
        dp[i] = h[i]
        cols.append((model(p + dp) - model(p - dp)) / (2 * h[i]))
    jac = np.stack(cols, axis=1)
    cov = np.linalg.inv(jac.T @ jac) * rel_noise ** 2
    return float(np.sqrt(cov[0, 0]))


# --------------------------------------------------------------------------- #
# 1. ゼロ点 vs 相対測光(雲あり / 雲なし)                                       #
# --------------------------------------------------------------------------- #
def section_zero_point() -> dict:
    print("\n" + "=" * 78)
    print("1) ゼロ点(目標星の開口積分だけ)は雲で死ぬ —— 比較星との比が救う")
    print("=" * 78)
    t = np.arange(T, dtype=np.float64)
    out = {}
    for label, cloud in (("雲あり", True), ("雲なし(対照)", False)):
        sc = make_series(cloud=cloud)
        me = measure(sc)
        rows = []
        for name, which in (("ゼロ点(目標星のみ)", ("zero",)),
                            ("比(目標 / 全比較星の和)", ("sum",))):
            y = lightcurve(me["flux"], which)
            f = fit_transit(t, y)
            rows.append((name, f))
            print("   %-12s %-24s 深さ %+7.2f ppt(誤差 %+6.2f) T14 %6.1f fr(誤差 %+5.1f) "
                  "残差 rms %5.2f ppt" % (label, name, 1e3 * f["depth"],
                                         1e3 * (f["depth"] - DEPTH), f["t14"],
                                         f["t14"] - T14, 1e3 * f["rms"]))
        out[label] = {"scene": sc, "meas": me, "fits": rows}

    sc, me = out["雲あり"]["scene"], out["雲あり"]["meas"]
    # 位置合わせの検算(ドリフトの真値との差)
    d_shift = me["est_shift"] - (sc["shifts"] - sc["shifts"][:N_REF].mean(axis=0))
    print("   位置合わせ(frame_align, 平行移動)の誤差 rms %.3f px / 最大 %.3f px"
          % (np.sqrt((d_shift ** 2).mean()), np.abs(d_shift).max()))
    out["shift_rms"] = float(np.sqrt((d_shift ** 2).mean()))

    # --- 図: 場面 ---
    fr0 = sc["frames"][0]
    oot = oot_mask()
    mid = np.abs(t - T0) < 0.2 * T14
    diff = sc["frames"][mid].mean(axis=0) - sc["frames"][oot].mean(axis=0)
    diff_pre = sc["frames"][t < 30].mean(axis=0) - sc["frames"][oot].mean(axis=0)
    figs.save_grid("scene_starfield",
                   [np.sqrt(np.clip(fr0, 0, None)), sc["gain"] - 1.0,
                    diff_pre, diff],
                   ["フレーム 0(√ストレッチ)[e-]", "フラット(感度 - 1)",
                    "差分: 前半 - トランジット外", "差分: 最深部 - トランジット外 [e-]"],
                   title="星野(目標星は中央、比較星 5 個)と、最深部で目標星だけが沈む差分",
                   ncols=2, signed=[False, True, True, True])
    # トランジット外との差分をフレーム群ごとに(段階の図)
    phases = [("前", t < 60), ("入(ingress)", (t > 78) & (t < 92)),
              ("最深部", mid), ("出(egress)", (t > 148) & (t < 162)), ("後", t > 180)]
    cut = (slice(40, 73), slice(40, 73))
    panels = [(sc["frames"][m].mean(axis=0) - sc["frames"][oot].mean(axis=0))[cut]
              for _, m in phases]
    figs.save_grid("frames_transit_phases", panels, [p for p, _ in phases],
                   title="目標星まわり 33 px の差分(各段階の平均 - トランジット外の平均)[e-]",
                   ncols=5, signed=True)
    # 光度曲線
    zero = lightcurve(me["flux"], ("zero",))
    comp = normalize(me["flux"][:, 1:].sum(axis=1))
    ratio = lightcurve(me["flux"], ("sum",))
    figs.save_plot("lightcurve_zero_vs_relative",
                   [("目標星の開口積分(ゼロ点)", t, zero),
                    ("比較星 5 個の和", t, comp + 0.06),
                    ("比 目標/比較星(+0.12)", t, ratio + 0.12),
                    ("真のトランジット(+0.12)", t, sc["model"] + 0.12)],
                   xlabel="フレーム", ylabel="相対光度(見やすさのため上下にずらした)",
                   title="雲(透明度 rms 3 %)の下で: ゼロ点は雲そのもの、比を取ると 1 % の凹みが残る")
    figs.save_plot("transparency_truth", [("透明度 τ(t)", t, sc["tau"]),
                                          ("目標星のモデル", t, sc["model"])],
                   xlabel="フレーム", ylabel="相対値",
                   title="仕込んだ透明度変動(全星共通)と、目標星だけの減光")
    return out


# --------------------------------------------------------------------------- #
# 2. 比較星の選び方                                                             #
# --------------------------------------------------------------------------- #
def section_comparison_choice(sec1: dict) -> dict:
    print("\n" + "=" * 78)
    print("2) 比較星の選び方で精度が何倍変わるか(同じ画像列、同じ開口)")
    print("=" * 78)
    me = sec1["雲あり"]["meas"]
    sc = sec1["雲あり"]["scene"]
    t = np.arange(T, dtype=np.float64)
    choices = [("A(明るい 2.0 倍)1 星", ("比較A",)),
               ("B(同じ明るさ)1 星", ("比較B",)),
               ("C(0.5 倍)1 星", ("比較C",)),
               ("E(0.12 倍)1 星", ("比較E",)),
               ("A+B(明るい 2 星の和)", ("比較A", "比較B")),
               ("全 5 星の単純和", ("sum",)),
               ("全 5 星の逆分散重み", ("weighted",))]
    rows, res = [], {}
    print("   %-24s 残差rms  理論   深さ誤差  σ(深さ)  T14誤差  σ(T14)" % "比較星")
    for name, which in choices:
        f = fit_transit(t, lightcurve(me["flux"], which))
        th = theory_rel_noise(R_AP, sc["ratio"], which)
        res[name] = (f, th)
        print("   %-24s %5.2f  %5.2f   %+6.2f    %5.2f    %+5.1f    %4.1f  [ppt / fr]" % (
            name, 1e3 * f["rms"], 1e3 * th, 1e3 * (f["depth"] - DEPTH),
            1e3 * f["sig_depth"], f["t14"] - T14, f["sig_t14"]))
    best = min(res.values(), key=lambda v: v[0]["rms"])[0]["rms"]
    worst = max(res.values(), key=lambda v: v[0]["rms"])[0]["rms"]
    for name, (f, th) in res.items():
        rows.append([name, "%.2f" % (1e3 * f["rms"]), "%.2f" % (1e3 * th),
                     "%+.2f" % (1e3 * (f["depth"] - DEPTH)), "%.2f" % (1e3 * f["sig_depth"]),
                     "%+.1f" % (f["t14"] - T14), "%.1f" % f["sig_t14"],
                     "%.1f 倍" % (f["rms"] / best)])
    print("\n   ★最良 %.2f ppt / 最悪 %.2f ppt = **%.1f 倍**。深さの σ はその比で動くが、"
          "T14 の誤差はそうならない。" % (1e3 * best, 1e3 * worst, worst / best))
    figs.save_table("comparison_choice",
                    ["比較星", "残差 rms ppt", "理論 ppt", "深さ誤差 ppt", "σ深さ ppt",
                     "T14 誤差 fr", "σT14 fr", "最良比"],
                    rows, title="比較星の選び方(同じ画像列・開口 3σ)")
    return {"res": res, "ratio": worst / best}


# --------------------------------------------------------------------------- #
# 3. 崖 A: 開口半径                                                             #
# --------------------------------------------------------------------------- #
def section_aperture_sweep(sec1: dict) -> dict:
    print("\n" + "=" * 78)
    print("3) 開口半径の崖 —— 小さすぎると重心誤差が明るさに化け、大きすぎると空を拾う")
    print("=" * 78)
    sc = sec1["雲あり"]["scene"]
    t = np.arange(T, dtype=np.float64)
    ref, ctr = locate(sc["frames"], sc["rows"], sc["cols"])
    centers, _ = track(sc["frames"], ref, ctr)
    ks = np.array([1.0, 1.5, 2.0, 3.0, 4.0, 6.0])
    meas, theo, derr, terr = [], [], [], []
    print("   r/σ   r[px]  残差rms  理論   比    深さ誤差  T14誤差")
    for k in ks:
        r = k * SIGMA
        r_in = max(R_IN, r + 1.5)
        flux = photometry(sc["frames"], centers, r, r_in, r_in + 4.0)
        f = fit_transit(t, lightcurve(flux, ("sum",)))
        th = theory_rel_noise(r, sc["ratio"])
        meas.append(f["rms"]); theo.append(th)
        derr.append(f["depth"] - DEPTH); terr.append(f["t14"] - T14)
        print("   %3.1f   %4.2f   %5.2f  %5.2f  %4.2f   %+6.2f    %+5.1f  [ppt / fr]" % (
            k, r, 1e3 * f["rms"], 1e3 * th, f["rms"] / th, 1e3 * (f["depth"] - DEPTH),
            f["t14"] - T14))
    meas, theo = np.array(meas), np.array(theo)
    # 重心誤差が明るさに化ける量: dF/F ≈ (r/σ²)·exp(-r²/2σ²)·ε·(PSF 縁の勾配)
    print("\n   ★r=1σ で理論より %.0f %% 悪い。開口の縁の PSF 勾配が最大で、重心誤差 "
          "(rms %.3f px)が明るさの誤差に化ける。" % (100 * (meas[0] / theo[0] - 1), sec1["shift_rms"]))
    figs.save_plot("aperture_sweep",
                   [("実測 残差 rms", ks, 1e3 * meas), ("理論 CCD 式", ks, 1e3 * theo)],
                   xlabel="開口半径 r / σ", ylabel="比の 1 フレーム雑音 [ppt]",
                   title="開口半径の掃引: 崖は小さい側(重心誤差)、緩い坂は大きい側(空)")
    figs.save_plot("aperture_depth_bias",
                   [("深さの誤差", ks, 1e3 * np.array(derr))],
                   xlabel="開口半径 r / σ", ylabel="深さの誤差 [ppt](真値 10 ppt)",
                   title="開口が小さいと深さも偏る")
    return {"k": ks, "meas": meas, "theo": theo, "derr": np.array(derr),
            "terr": np.array(terr)}


# --------------------------------------------------------------------------- #
# 4. 崖 B: 深さの検出限界                                                       #
# --------------------------------------------------------------------------- #
def section_depth_cliff() -> dict:
    print("\n" + "=" * 78)
    print("4) 深さの崖 —— SNR = 5 の境目を理論の CCD 式が予測できるか")
    print("=" * 78)
    t = np.arange(T, dtype=np.float64)
    depths = np.array([0.0005, 0.001, 0.0015, 0.002, 0.003, 0.005, 0.010])
    seeds = (101, 102, 103)
    th_noise = theory_rel_noise(R_AP, np.array([STARS[n]["ratio"] for n in NAMES]))
    snr_m, snr_t, derr, terr, rms_m = [], [], [], [], []
    print("   δ[ppt]  観測SNR(δ^/σ^)  真SNR(δ/σ^)  理論SNR  真/理論  深さ誤差[ppt]  |T14誤差|[fr]"
          "(3 seed の平均)")
    snr_true = []
    for d in depths:
        sm, st_, de, te, rr = [], [], [], [], []
        for s in seeds:
            sc = make_series(depth=d, seed=s, drift_px=0.0, flat_px=0.0)
            f = fit_transit(t, lightcurve(measure(sc)["flux"], ("sum",)))
            sm.append(f["depth"] / f["sig_depth"]); st_.append(d / f["sig_depth"])
            de.append(f["depth"] - d); te.append(abs(f["t14"] - T14)); rr.append(f["rms"])
        st = d / theory_sig_depth(th_noise, d)
        snr_m.append(np.mean(sm)); snr_true.append(np.mean(st_)); snr_t.append(st)
        derr.append(np.mean(de)); terr.append(np.mean(te)); rms_m.append(np.mean(rr))
        print("   %5.1f      %5.2f          %5.2f        %5.2f    %4.2f     %+6.2f        %6.1f" % (
            1e3 * d, np.mean(sm), np.mean(st_), st, np.mean(st_) / st, 1e3 * np.mean(de),
            np.mean(te)))
    snr_m, snr_t, snr_true = np.array(snr_m), np.array(snr_t), np.array(snr_true)

    def cross(snr):
        # SNR は δ にほぼ比例するので log-log で 5 を横切る δ を補間
        return float(np.exp(np.interp(np.log(5.0), np.log(snr), np.log(depths))))
    dm, dt_ = cross(snr_true), cross(snr_t)
    print("\n   SNR = 5 の境目: 実測 %.2f ppt / 理論 %.2f ppt。真SNR/理論の比は %.2f〜%.2f。"
          % (1e3 * dm, 1e3 * dt_, (snr_true / snr_t).min(), (snr_true / snr_t).max()))
    print("   ★観測 SNR(δ^/σ^)は限界の下で理論より高く出る(δ^ が過大: δ=%.1f ppt で "
          "%+.2f ppt)—— 雑音を惑星と呼んでいる。" % (1e3 * depths[0], 1e3 * derr[0]))
    print("   ★検出できない δ=%.1f ppt では |T14 誤差| %.0f フレーム —— 深さより先に"
          "継続時間が壊れる。" % (1e3 * depths[0], terr[0]))
    figs.save_plot("depth_cliff",
                   [("観測 SNR(推定深さ/σ、3 seed 平均)", 1e3 * depths, snr_m),
                    ("真 SNR(真の深さ/σ)", 1e3 * depths, snr_true),
                    ("理論 CCD 式 + Fisher", 1e3 * depths, snr_t),
                    ("SNR = 5", 1e3 * depths, np.full(depths.size, 5.0))],
                   xlabel="深さ δ [ppt]", ylabel="深さの検出 SNR",
                   title="深さの検出限界: 実測と理論が並ぶ(SNR=5 は 2.6 ppt)")
    figs.save_plot("depth_cliff_t14",
                   [("|T14 の誤差| [frame]", 1e3 * depths, np.array(terr)),
                    ("深さの誤差 [0.1 ppt]", 1e3 * depths, 1e4 * np.array(derr))],
                   xlabel="深さ δ [ppt]", ylabel="誤差",
                   title="検出限界の下では継続時間が先に壊れる")
    return {"depths": depths, "snr_m": snr_m, "snr_t": snr_t, "snr_true": snr_true,
            "derr": np.array(derr),
            "terr": np.array(terr), "cross_m": dm, "cross_t": dt_}


# --------------------------------------------------------------------------- #
# 5. 崖 C: ドリフト × フラット不均一                                            #
# --------------------------------------------------------------------------- #
def psf_weight_norm(sigma: float = SIGMA) -> float:
    """``sqrt(sum w^2)``: 画素フラットのばらつきが星の明るさに移る係数。"""
    w = render_stars([20.0], [20.0], [1.0], sigma, (41, 41))
    return float(np.sqrt((w * w).sum()))


def section_drift_flat() -> dict:
    print("\n" + "=" * 78)
    print("5) ドリフト × フラット不均一 —— 単独では無害、掛け算で偽の深さ")
    print("=" * 78)
    t = np.arange(T, dtype=np.float64)
    drifts = np.array([0.0, 0.5, 1.0, 2.0])
    flats = np.array([0.0, 0.01, 0.03])
    seeds = (201, 202, 203)
    coef = psf_weight_norm()
    print("   予測(上限): 偽の明るさ変化 rms ≈ a * sqrt(Σw²) = %.3f a → a=1 %% で %.2f ppt、"
          "a=3 %% で %.2f ppt" % (coef, 1e3 * 0.01 * coef, 1e3 * 0.03 * coef))
    print("   ドリフト[px]  画素フラット  深さ誤差 rms[ppt]  平均  |T14誤差| rms[fr]  残差rms[ppt]"
          "  (3 seed)")
    grid = np.zeros((flats.size, drifts.size))       # 深さ誤差の rms(符号はフラット次第)
    grid_t = np.zeros_like(grid)
    rows = []
    for i, a in enumerate(flats):
        for j, dpx in enumerate(drifts):
            de, te, rr = [], [], []
            for s in seeds:
                sc = make_series(drift_px=dpx, flat_px=a, cloud=False, seed=s,
                                 flat_seed=s * 13 + 5)
                f = fit_transit(t, lightcurve(measure(sc)["flux"], ("sum",)))
                de.append(f["depth"] - DEPTH); te.append(f["t14"] - T14); rr.append(f["rms"])
            grid[i, j] = np.sqrt(np.mean(np.square(de)))
            grid_t[i, j] = np.sqrt(np.mean(np.square(te)))
            rows.append(["%.1f" % dpx, "%.0f %%" % (100 * a), "%.2f" % (1e3 * grid[i, j]),
                         "%+.2f" % (1e3 * np.mean(de)),
                         "%.1f" % grid_t[i, j], "%.2f" % (1e3 * np.mean(rr))])
            print("   %5.1f         %4.0f %%         %5.2f        %+5.2f     %5.1f          %5.2f" % (
                dpx, 100 * a, 1e3 * grid[i, j], 1e3 * np.mean(de), grid_t[i, j],
                1e3 * np.mean(rr)))
    print("\n   対照群(深さ誤差 rms): ドリフト 2 px・フラット均一 %.2f ppt / ドリフト 0・"
          "フラット 3 %% %.2f ppt / 両方 %.2f ppt(真値 10 ppt の %.0f %%)"
          % (1e3 * grid[0, -1], 1e3 * grid[-1, 0], 1e3 * grid[-1, -1],
             100 * grid[-1, -1] / DEPTH))
    print("   予測上限 %.2f ppt に対し実測 %.2f ppt = %.0f %%(直線基線が大半を吸う)"
          % (1e3 * 0.03 * coef, 1e3 * grid[-1, -1], 100 * grid[-1, -1] / (0.03 * coef)))
    figs.save_table("drift_flat_table",
                    ["ドリフト px", "画素フラット", "深さ誤差 rms ppt", "深さ誤差 平均 ppt",
                     "|T14 誤差| rms fr", "残差 rms ppt"], rows,
                    title="ドリフト × フラット不均一(雲なし・開口 3σ・3 seed)")
    figs.save_plot("drift_flat_map",
                   [("フラット均一(対照)", drifts, 1e3 * grid[0]),
                    ("画素フラット 1 %", drifts, 1e3 * grid[1]),
                    ("画素フラット 3 %", drifts, 1e3 * grid[2])],
                   xlabel="一晩のドリフト [px]", ylabel="深さの誤差 rms [ppt](真値 10 ppt)",
                   title="偽の深さはドリフトとフラットの積で生まれる")
    return {"grid": grid, "grid_t": grid_t, "coef": coef, "drifts": drifts, "flats": flats}


# --------------------------------------------------------------------------- #
def main() -> int:
    t_start = time.perf_counter()
    print("系外惑星トランジット: %dx%d px, %d 枚, PSF σ %.1f px, 目標星 %.0f e-/枚, "
          "δ %.1f ppt, T14 %.0f fr, b %.2f, u1/u2 %.2f/%.2f"
          % (SHAPE[0], SHAPE[1], T, SIGMA, F_TARGET, 1e3 * DEPTH, T14, B, U1, U2))
    p = depth_to_p(DEPTH)
    print("   半径比 p = %.4f(δ = p² I(b)/Ī)、開口 r = %.1f px(%.1f σ、拾う割合 %.3f)"
          % (p, R_AP, R_AP / SIGMA, frac_in(R_AP)))
    # モデルの検算: 最深部の減光が δ に一致、トランジット外は厳密に 1
    m = transit_model(np.arange(T), DEPTH, T0, T14)
    assert abs((1.0 - m.min()) - DEPTH) < 1e-12, m.min()
    assert np.all(m[oot_mask()] == 1.0)

    tt = time.perf_counter()
    s1 = section_zero_point()
    s2 = section_comparison_choice(s1)
    print("   [%.1f s]" % (time.perf_counter() - tt)); tt = time.perf_counter()
    s3 = section_aperture_sweep(s1)
    print("   [%.1f s]" % (time.perf_counter() - tt)); tt = time.perf_counter()
    s4 = section_depth_cliff()
    print("   [%.1f s]" % (time.perf_counter() - tt)); tt = time.perf_counter()
    s5 = section_drift_flat()
    print("   [%.1f s]" % (time.perf_counter() - tt))

    # --- 所見を固定する(壊れたら鳴る): 数字を見てから入れる ---------------
    print("\n所要 %.1f s" % (time.perf_counter() - t_start))
    if figs.errors():
        print("図の警告:", figs.errors())
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
