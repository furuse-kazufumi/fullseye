# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""sensorchar — カメラ(画像センサ)を EMVA 1288 Release 4.0 Linear(= ISO 24942)の手順で測る。

カメラのデータシートにある「量子効率・システムゲイン K・暗雑音・飽和容量・SNR・ダイナミックレンジ・DSNU・PRNU」は
この規格の手順で出した数である。この族はその手順を op にする: 露光を振った 2 枚ずつの画像から平均と時間分散を出し
(式 16・18)、photon transfer の傾きで K(式 50)、応答の傾きで η(式 49・52)、暗画像から σ_d(式 53)を出す。

式の番号は規格本文(`EMVA1288Linear_4.0Release.pdf`)のもの。本文から写した(記憶から書かない)。

真値(tests/test_sensorchar.py):
* **復元**: 既知の η・K・σ_d・暗電流・DSNU・PRNU で**物理モデル**(光子のポアソン → 電子 → 暗雑音 → K 倍 → 量子化)から
  画像を合成し、**規格の推定手順**(別の式)が元の値を返すか。同じ式を往復させない。
* **恒等式**: SNR(μ_p.min) = 1(式 26 と式 21 は独立に書かれている)/ 理想センサの SNR = √μ_p(式 23)/
  空間分散の列・行・画素の分解(式 42)が既知の模様を返す。
* **規格が書いた適用範囲**: σ²_y.dark < 0.24 DN² では σ_d を推定せず上限 0.40/K を返す(式 54)—— その境界が実際に
  推定が壊れる境界であること。

★σ_d を photon transfer の**切片**から出してはいけない(着手前の見込み確認で 21 % 外した)。規格の推定は式 (53)
σ_d = √(σ²_y.dark − σ²_q)/K で、暗画像から直接測る。切片は K を出すためのもの。
★Linear の規格は 1 光子で 1 電子までの線形なセンサが対象(深紫外などは General の規格)。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "emva_pair_statistics", "emva_photon_transfer", "emva_quantum_efficiency", "emva_linearity_error",
    "emva_snr_curve", "emva_sensitivity_threshold", "emva_dynamic_range", "emva_dark_current",
    "emva_spatial_nonuniformity", "emva_defect_pixels",
]

SIGMA_Q2 = 1.0 / 12.0          # 量子化雑音の分散 [DN²](一様分布の分散、厳密)
_DARK_VAR_FLOOR = 0.24         # 式 (53) の直後: これ未満では σ_d を推定できない
_DARK_LIMIT_DN = 0.40          # 式 (54): σ_d < 0.40 / K


def _arr(x, name, fn, ndim=None, min_size=1):
    a = np.asarray(x)
    if a.dtype == object or np.iscomplexobj(a) or isinstance(x, np.ma.MaskedArray):
        raise ValueError("%s: %s must be a real array (got dtype %s)" % (fn, name, a.dtype))
    a = a.astype(np.float64)
    if ndim is not None and a.ndim != ndim:
        raise ValueError("%s: %s must be %d-D (got shape %r)" % (fn, name, ndim, a.shape))
    if a.size < min_size:
        raise ValueError("%s: %s needs at least %d values (got %d)" % (fn, name, min_size, a.size))
    if not np.isfinite(a).all():
        raise ValueError("%s: %s contains NaN or inf" % (fn, name))
    return a


def _pos(x, name, fn, allow_zero=False):
    try:
        v = float(x)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a number (got %r)" % (fn, name, x)) from None
    if not math.isfinite(v) or v < 0 or (v == 0 and not allow_zero):
        raise ValueError("%s: %s must be %s and finite (got %r)" % (fn, name, ">= 0" if allow_zero else "> 0", x))
    return v


def emva_pair_statistics(y0, y1):
    """同じ露光で撮った 2 枚から、平均・時間分散・空間分散を出す(式 16・18・32)。

    ``mu`` = (μ[0] + μ[1]) / 2(式 16)、``var_temporal`` = Σ(y0 − y1)²/(2NM) − (μ[0] − μ[1])²/2(式 18: 2 枚の平均の差の補正は
    Release 4 の新規)、``var_spatial`` = Σ y0·y1/(NM) − μ[0]μ[1](式 32、負にならないことが示されている)。

    返り値 ``{"mu", "var_temporal", "var_spatial", "mu0", "mu1", "n_pixels"}``。

    **Raises** ``ValueError``: 2-D の実数でない / 形が違う / NaN・inf / 画素が 2 未満。
    """
    fn = "emva_pair_statistics"
    a = _arr(y0, "y0", fn, ndim=2, min_size=2)
    b = _arr(y1, "y1", fn, ndim=2, min_size=2)
    if a.shape != b.shape:
        raise ValueError("%s: y0 %r and y1 %r differ in shape" % (fn, a.shape, b.shape))
    m0, m1 = float(a.mean()), float(b.mean())
    vt = float(((a - b) ** 2).mean()) / 2.0 - (m0 - m1) ** 2 / 2.0
    vs = float((a * b).mean()) - m0 * m1
    return {"mu": 0.5 * (m0 + m1), "var_temporal": vt, "var_spatial": vs, "mu0": m0, "mu1": m1, "n_pixels": int(a.size)}


def _fit_range(mu_y, mu_dark, mu_sat, lo_frac, hi_frac, fn):
    span = mu_sat - mu_dark
    if not span > 0:
        raise ValueError("%s: mu_y_sat (%g) must exceed mu_y_dark (%g)" % (fn, mu_sat, mu_dark))
    s = mu_y - mu_dark
    return (s >= lo_frac * span - 1e-12) & (s <= hi_frac * span + 1e-12)


def emva_photon_transfer(mu_y, var_y, mu_y_dark, var_y_dark, mu_y_sat):
    """photon transfer 曲線からシステムゲイン K と暗雑音 σ_d を出す(式 50・53・54)。

    *mu_y*, *var_y*: 露光段ごとの平均と時間分散(:func:`emva_pair_statistics` の ``mu`` と ``var_temporal``)。
    *mu_y_dark*, *var_y_dark*: 暗画像の同じ量。*mu_y_sat*: 飽和の平均(0.1〜0.2 % の画素が最大値になる露光で測る)。

    K = σ²_y − σ²_y.dark を μ_y − μ_y.dark に当てた直線(**切片あり**)の傾き。使う点は飽和の 0〜70 %(式 50 の直後)。
    σ_d = √(σ²_y.dark − 1/12)/K(式 53)。★σ²_y.dark < 0.24 DN² では量子化雑音が支配的で推定できないので、
    ``sigma_d`` は None、``sigma_d_upper`` = 0.40/K(式 54)を返す。

    返り値 ``{"K", "offset", "sigma_d", "sigma_d_upper", "sigma_d_valid", "n_points", "residual_rms", "used"}``
    (``used`` は当てはめに使った点の真偽)。

    **Raises** ``ValueError``: 長さが違う / 0〜70 % に 3 点未満 / 傾きが正でない / var_y_dark が負。
    """
    fn = "emva_photon_transfer"
    m = _arr(mu_y, "mu_y", fn, ndim=1, min_size=3)
    v = _arr(var_y, "var_y", fn, ndim=1, min_size=3)
    if m.shape != v.shape:
        raise ValueError("%s: mu_y and var_y differ in length (%d, %d)" % (fn, m.size, v.size))
    md = float(mu_y_dark)
    vd = _pos(var_y_dark, "var_y_dark", fn, allow_zero=True)
    use = _fit_range(m, md, float(mu_y_sat), 0.0, 0.70, fn)
    if use.sum() < 3:
        raise ValueError("%s: only %d points lie in 0-70 %% of saturation — need at least 3" % (fn, int(use.sum())))
    x, y = m[use] - md, v[use] - vd
    slope, icpt = np.polyfit(x, y, 1)
    if not slope > 0:
        raise ValueError("%s: the photon transfer slope is %g — the variance does not grow with the signal" % (fn, slope))
    res = y - (icpt + slope * x)
    K = float(slope)
    valid = vd >= _DARK_VAR_FLOOR
    sd = math.sqrt(max(vd - SIGMA_Q2, 0.0)) / K if valid else None
    return {"K": K, "offset": float(icpt), "sigma_d": sd, "sigma_d_upper": None if valid else _DARK_LIMIT_DN / K,
            "sigma_d_valid": bool(valid), "n_points": int(use.sum()), "residual_rms": float(np.sqrt(np.mean(res ** 2))),
            "used": use}


def emva_quantum_efficiency(mu_p, mu_y, mu_y_dark, mu_y_sat, K):
    """応答(特性曲線)の傾きから量子効率 η を出す(式 49・52)。

    *mu_p*: 露光段ごとの画素あたりの平均光子数(照度計と露光時間から: μ_p = A E t_exp λ/(hc))。
    R = μ_y − μ_y.dark を μ_p に当てた直線(**切片 0 に固定**)の傾き、η = R/K。使う点は飽和の 0〜70 %。

    返り値 ``{"eta", "responsivity", "n_points"}``。

    **Raises** ``ValueError``: 長さが違う / 0〜70 % に 2 点未満 / K が正でない / 応答が正でない。
    """
    fn = "emva_quantum_efficiency"
    p = _arr(mu_p, "mu_p", fn, ndim=1, min_size=2)
    m = _arr(mu_y, "mu_y", fn, ndim=1, min_size=2)
    if p.shape != m.shape:
        raise ValueError("%s: mu_p and mu_y differ in length (%d, %d)" % (fn, p.size, m.size))
    k = _pos(K, "K", fn)
    md = float(mu_y_dark)
    use = _fit_range(m, md, float(mu_y_sat), 0.0, 0.70, fn) & (p > 0)
    if use.sum() < 2:
        raise ValueError("%s: only %d exposed points lie in 0-70 %% of saturation" % (fn, int(use.sum())))
    x, y = p[use], m[use] - md
    R = float((x * y).sum() / (x * x).sum())            # 原点を通る最小二乗
    if not R > 0:
        raise ValueError("%s: the responsivity is %g — the signal does not grow with exposure" % (fn, R))
    return {"eta": R / k, "responsivity": R, "n_points": int(use.sum())}


def emva_linearity_error(H, mu_y, mu_y_dark, mu_y_sat):
    """直線性の誤差 LE(式 58〜63)。y = μ_y − μ_y.dark を露光 H に**相対偏差の重み 1/y²**で当て(式 59〜61)、
    飽和の 5〜95 % の点で相対偏差 δy[i] = 100 (y − (a0 + a1 H))/(a0 + a1 H) [%] の絶対値の平均を LE とする。

    返り値 ``{"LE_percent", "a0", "a1", "deviation_percent", "used"}``。

    **Raises** ``ValueError``: 長さが違う / 5〜95 % に 3 点未満 / y が正でない点がある(重み 1/y² が無限)。
    """
    fn = "emva_linearity_error"
    h = _arr(H, "H", fn, ndim=1, min_size=3)
    m = _arr(mu_y, "mu_y", fn, ndim=1, min_size=3)
    if h.shape != m.shape:
        raise ValueError("%s: H and mu_y differ in length (%d, %d)" % (fn, h.size, m.size))
    md = float(mu_y_dark)
    use = _fit_range(m, md, float(mu_y_sat), 0.05, 0.95, fn)
    if use.sum() < 3:
        raise ValueError("%s: only %d points lie in 5-95 %% of saturation — need at least 3" % (fn, int(use.sum())))
    x, y = h[use], m[use] - md
    if not (y > 0).all():
        raise ValueError("%s: a used point has y = mu_y - mu_y_dark <= 0 (weight 1/y^2 undefined)" % fn)
    w = 1.0 / y ** 2
    S_h_y = (x / y).sum()
    S_h_y2 = (x * w).sum()
    S_h2_y2 = (x * x * w).sum()
    S_1_y = (1.0 / y).sum()
    S_1_y2 = w.sum()
    delta = S_h_y2 ** 2 - S_h2_y2 * S_1_y2                              # 式 (61)
    a0 = (S_h_y * S_h_y2 - S_h2_y2 * S_1_y) / delta                     # 式 (59)
    a1 = (S_h_y2 * S_1_y - S_h_y * S_1_y2) / delta                      # 式 (60)
    fit = a0 + a1 * x
    dev = 100.0 * (y - fit) / fit                                       # 式 (62)
    return {"LE_percent": float(np.abs(dev).mean()), "a0": float(a0), "a1": float(a1),     # 式 (63)
            "deviation_percent": dev, "used": use}


def emva_snr_curve(mu_p, eta, sigma_d, K, *, sigma_q2=SIGMA_Q2):
    """線形モデルの SNR(式 21)と理想センサの SNR(式 23)。

    SNR = η μ_p / √(σ²_d + σ²_q/K² + η μ_p)、SNR_ideal = √μ_p。低露光では傾き 1、高露光では傾き 1/2(式 22)。
    返り値 ``(n, 3)``: 列 = μ_p, SNR, SNR_ideal。

    **Raises** ``ValueError``: μ_p が負 / η が (0, 1] の外 / σ_d・σ_q² が負 / K が正でない。
    """
    fn = "emva_snr_curve"
    p = _arr(mu_p, "mu_p", fn, ndim=1)
    if (p < 0).any():
        raise ValueError("%s: mu_p must be >= 0" % fn)
    e = _pos(eta, "eta", fn)
    if e > 1.0:
        raise ValueError("%s: eta must be in (0, 1] for the linear model (got %r)" % (fn, eta))
    sd = _pos(sigma_d, "sigma_d", fn, allow_zero=True)
    k = _pos(K, "K", fn)
    q2 = _pos(sigma_q2, "sigma_q2", fn, allow_zero=True)
    snr = e * p / np.sqrt(sd ** 2 + q2 / k ** 2 + e * p) if (sd > 0 or q2 > 0) else np.sqrt(e * p)
    return np.ascontiguousarray(np.column_stack([p, snr, np.sqrt(p)]), dtype=np.float64)


def emva_sensitivity_threshold(eta, sigma_d, K, *, sigma_q2=SIGMA_Q2):
    """絶対感度しきい値(SNR = 1 になる露光、式 26・27)。

    μ_p.min = (1/η)(√(σ²_d + σ²_q/K² + 1/4) + 1/2)、μ_e.min = η μ_p.min。★量子化雑音が入る限り μ_e.min は σ_d より大きい。
    返り値 ``{"mu_p_min", "mu_e_min"}``。

    **Raises** ``ValueError``: η が (0, 1] の外 / σ_d・σ_q² が負 / K が正でない。
    """
    fn = "emva_sensitivity_threshold"
    e = _pos(eta, "eta", fn)
    if e > 1.0:
        raise ValueError("%s: eta must be in (0, 1] (got %r)" % (fn, eta))
    sd = _pos(sigma_d, "sigma_d", fn, allow_zero=True)
    k = _pos(K, "K", fn)
    q2 = _pos(sigma_q2, "sigma_q2", fn, allow_zero=True)
    mpm = (math.sqrt(sd ** 2 + q2 / k ** 2 + 0.25) + 0.5) / e
    return {"mu_p_min": mpm, "mu_e_min": e * mpm}


def emva_dynamic_range(mu_p_sat, mu_p_min):
    """ダイナミックレンジ DR = μ_p.sat / μ_p.min(式 28)を倍・dB(20 log10)・bit(log2)で。

    **Raises** ``ValueError``: どちらかが正でない / μ_p.sat ≤ μ_p.min。
    """
    fn = "emva_dynamic_range"
    s = _pos(mu_p_sat, "mu_p_sat", fn)
    m = _pos(mu_p_min, "mu_p_min", fn)
    if not s > m:
        raise ValueError("%s: mu_p_sat (%g) must exceed mu_p_min (%g)" % (fn, s, m))
    dr = s / m
    return {"ratio": dr, "dB": 20.0 * math.log10(dr), "bits": math.log2(dr)}


def emva_dark_current(t_exp, mu_y_dark, K, *, var_y_dark=None):
    """暗電流(7.1 節): 暗画像の平均(と分散)を露光時間に直線で当てた傾き。

    μ_I.y [DN/s] = 平均の傾き、μ_I.e [e⁻/s] = μ_I.y / K。*var_y_dark* を渡すと分散の傾き [DN²/s] / K² も出す
    (暗電流の補正があるカメラは分散からしか測れない)。露光時間は **6 点以上**・等間隔を規格が求める。

    返り値 ``{"mu_I_y", "mu_I_e", "offset_y", "var_slope", "mu_I_e_from_var", "n_points"}``。

    **Raises** ``ValueError``: 6 点未満 / 長さが違う / 露光時間がすべて同じ / K が正でない。
    """
    fn = "emva_dark_current"
    t = _arr(t_exp, "t_exp", fn, ndim=1)
    m = _arr(mu_y_dark, "mu_y_dark", fn, ndim=1)
    if t.size < 6:
        raise ValueError("%s: the standard asks for at least six exposure times (got %d)" % (fn, t.size))
    if t.shape != m.shape:
        raise ValueError("%s: t_exp and mu_y_dark differ in length (%d, %d)" % (fn, t.size, m.size))
    if float(np.ptp(t)) == 0.0:
        raise ValueError("%s: all exposure times are equal — no slope" % fn)
    k = _pos(K, "K", fn)
    sl, ic = np.polyfit(t, m, 1)
    out = {"mu_I_y": float(sl), "mu_I_e": float(sl) / k, "offset_y": float(ic), "var_slope": None,
           "mu_I_e_from_var": None, "n_points": int(t.size)}
    if var_y_dark is not None:
        v = _arr(var_y_dark, "var_y_dark", fn, ndim=1)
        if v.shape != t.shape:
            raise ValueError("%s: var_y_dark differs in length from t_exp" % fn)
        vs = float(np.polyfit(t, v, 1)[0])
        out["var_slope"] = vs
        out["mu_I_e_from_var"] = vs / k ** 2
    return out


def _split(avg, var_t, L):
    """式 (35)(36)(41)(42): 平均画像の空間分散と、列・行・画素への分解。"""
    M, N = avg.shape
    mu = float(avg.mean())
    s2 = float(((avg - mu) ** 2).mean()) - var_t / L                    # 式 (35)(36)
    cav = float(((avg.mean(axis=0) - mu) ** 2).mean()) - var_t / (L * M)
    rav = float(((avg.mean(axis=1) - mu) ** 2).mean()) - var_t / (L * N)
    A = np.array([[1.0, 0.0, 1.0 / M], [0.0, 1.0, 1.0 / N], [1.0, 1.0, 1.0]])
    col, row, pix = np.linalg.solve(A, np.array([cav, rav, s2]))        # 式 (42)
    return {"mu": mu, "s2": s2, "s2_col": float(col), "s2_row": float(row), "s2_pixel": float(pix)}


def emva_spatial_nonuniformity(dark_stack, bright_stack, K):
    """DSNU と PRNU(式 33〜42・66・67)。

    *dark_stack*, *bright_stack*: 同じ露光で撮った L 枚(``(L, M, N)``、L ≥ 2)。bright は飽和の約 50 % で撮る。
    平均画像の空間分散から時間雑音の残り σ²_y/L を引き(式 36)、列・行・画素に分け(式 42)、
    DSNU1288 = s_y.dark / K [e⁻](式 66)、PRNU1288 = √(s²_y.50 − s²_y.dark)/(μ_y.50 − μ_y.dark)(式 67、比)。
    ★規格は 8.1 節の高域フィルタ(照明のむら除去)をかけた画像で求める —— この op は渡された画像をそのまま使う
    (照明のむらを除いた画像を渡すこと)。

    返り値 ``{"dark": {...}, "bright": {...}, "DSNU1288_e", "PRNU1288", "var_temporal_dark", "var_temporal_bright", "L"}``。

    **Raises** ``ValueError``: 3-D でない / L < 2 / 形が違う / K が正でない / bright の平均が dark 以下 / s²_y.50 < s²_y.dark。
    """
    fn = "emva_spatial_nonuniformity"
    d = _arr(dark_stack, "dark_stack", fn, ndim=3)
    b = _arr(bright_stack, "bright_stack", fn, ndim=3)
    if d.shape[0] < 2 or b.shape[0] < 2:
        raise ValueError("%s: need at least 2 images per stack (got %d, %d)" % (fn, d.shape[0], b.shape[0]))
    if d.shape[1:] != b.shape[1:]:
        raise ValueError("%s: dark %r and bright %r images differ in shape" % (fn, d.shape[1:], b.shape[1:]))
    k = _pos(K, "K", fn)
    out = {}
    for nm, st in (("dark", d), ("bright", b)):
        L = st.shape[0]
        var_t = float(st.var(axis=0, ddof=1).mean())                    # 画素ごとの時間分散の平均
        out[nm] = _split(st.mean(axis=0), var_t, L)
        out["var_temporal_" + nm] = var_t
    dd, bb = out["dark"], out["bright"]
    if not bb["mu"] > dd["mu"]:
        raise ValueError("%s: the bright mean (%g) must exceed the dark mean (%g)" % (fn, bb["mu"], dd["mu"]))
    diff = bb["s2"] - dd["s2"]
    if diff < 0:
        raise ValueError("%s: s2_y.50 (%g) < s2_y.dark (%g) — no photo-response nonuniformity to measure" % (fn, bb["s2"], dd["s2"]))
    out["DSNU1288_e"] = math.sqrt(max(dd["s2"], 0.0)) / k
    out["PRNU1288"] = math.sqrt(diff) / (bb["mu"] - dd["mu"])
    out["L"] = int(d.shape[0])
    return out


def emva_defect_pixels(avg_image, L, threshold):
    """欠陥画素の特徴づけ(8.8 節): 対数ヒストグラム(式 73〜75)と積算ヒストグラム(式 77)、しきい値を越える画素の数。

    *avg_image*: L 枚の平均画像(時間雑音を平均で消したもの)。*L*: 平均した枚数(ビン幅を 1/L の整数倍にする)。
    *threshold*(必須)[DN]: 平均からの絶対偏差がこれを**越える**画素を数える(用途の「止め帯」)。

    返り値 ``{"hist_centers": 平均からの偏差, "hist_counts", "accum_x": 絶対偏差, "accum_percent": その偏差以上の画素の %,
    "n_above": 数, "mu"}``。

    **Raises** ``ValueError``: 2-D でない / L が正の整数でない / threshold が負 / 画像が一定(ヒストグラムの幅 0)。
    """
    fn = "emva_defect_pixels"
    y = _arr(avg_image, "avg_image", fn, ndim=2, min_size=2)
    if isinstance(L, bool) or not isinstance(L, (int, np.integer)) or int(L) < 1:
        raise ValueError("%s: L must be a positive integer (got %r)" % (fn, L))
    Ln = int(L)
    thr = _pos(threshold, "threshold", fn, allow_zero=True)
    ymin, ymax = float(y.min()), float(y.max())
    if ymax == ymin:
        raise ValueError("%s: the image is constant — no histogram" % fn)
    I = int(math.floor(Ln * (ymax - ymin) / 256.0)) + 1                  # 式 (73)
    Q = int(math.floor(Ln * (ymax - ymin) / I)) + 1
    q = np.floor(Ln * (y - ymin) / I + 1e-9).astype(np.int64).ravel()   # 式 (74)(1/L の整数倍の丸め屑を吸う)
    q = np.clip(q, 0, Q - 1)
    counts = np.bincount(q, minlength=Q)
    mu = float(y.mean())
    centers = ymin + (I - 1) / (2.0 * Ln) + np.arange(Q) * I / Ln - mu  # 式 (75)(平均からの偏差)
    dev = np.abs(y - mu).ravel()                                        # 式 (77)
    ax = np.linspace(0.0, float(dev.max()), 257)
    srt = np.sort(dev)
    accum = 100.0 * (dev.size - np.searchsorted(srt, ax, side="left")) / dev.size
    return {"hist_centers": centers, "hist_counts": counts.astype(np.int64), "accum_x": ax, "accum_percent": accum,
            "n_above": int((dev > thr).sum()), "mu": mu}
