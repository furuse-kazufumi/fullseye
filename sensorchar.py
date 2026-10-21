# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""sensorchar — カメラ(画像センサ)を EMVA 1288 Release 4.0 Linear の手順で測る。

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
★ISO 24942 は発行された本文を読んでいない —— この族は EMVA 1288 Release 4.0(Linear / General、2021-06-16)の
本文だけに基づく。ISO 24942 と中身が同じとは書かない。

2026-10-13 追加(規格の本文から式を写し、式の番号を docstring に書いた):
* 8.1 節の高域フィルタ(7×7 と 11×11 の箱 → 3×3 の二項、元から引く)と付録 C.5 の旧版(5×5 の箱、式 84〜87)
  —— :func:`emva_highpass`。:func:`emva_spatial_nonuniformity` は ``highpass=`` で 8.1 節を通す。
* 8.6 節の水平・垂直スペクトログラム(式 70〜72)—— :func:`emva_spectrogram`。
* 8.5 節の総合 SNR(式 68・69)と SNR の逆関数(式 25)—— :func:`emva_total_snr` / :func:`emva_exposure_for_snr`。
* 2.1 節の光子数(式 3・4)—— :func:`emva_photon_exposure`。
* 6.6 節の photon transfer の直線性の検査(式 51、General の 3 次 B-スプライン 式 44〜49 を使う)——
  :func:`emva_bspline_regression` / :func:`emva_ptc_linearity_check`。
* 1.2 節の前提 3(時間雑音は画素間で独立)を確かめる道具と、線形な画像処理が数をどれだけ動かすかの閉形式 ——
  :func:`emva_noise_whiteness` / :func:`emva_filter_distortion`。★この 2 つの数は**規格が定義した数ではない**
  (規格は前提を書くだけで、確かめ方の数を決めていない)。

本文で見つけた食い違い(実装は導き直した式に従い、どちらも門で確かめる):
* General の式 (49) の 1 ≤ |x| ≤ 2 の枝は +x/(2|x|)(2 − |x|)²。式 (45) を微分すると符号が逆(−)。
* General の式 (48) の傾きは 1/Δμ_p(連鎖律)を欠く —— 正規化した変数での傾きとしてなら正しい。
* Linear 付録 C.5 の式 (86)(87): 白い雑音が 5×5 の箱の高域を通った分散は Parseval で 1 − 1/P² = 0.96(1-D は 1 − 1/P = 0.80)。
  本文の (1 − 1/P²)² = 0.92 と (1 − 1/P)² = 0.64 は二乗が一つ多い(4.0 の 8.1 節のフィルタはこの付録と別物)。
* Linear の式 (51) は「相対偏差の大きさの**平均**」と文で書くが、式は 1/n の無い和。平均で判定し、和も返す。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "emva_pair_statistics", "emva_photon_transfer", "emva_quantum_efficiency", "emva_linearity_error",
    "emva_snr_curve", "emva_sensitivity_threshold", "emva_dynamic_range", "emva_dark_current",
    "emva_spatial_nonuniformity", "emva_defect_pixels",
    "emva_highpass", "emva_spectrogram", "emva_total_snr", "emva_exposure_for_snr", "emva_photon_exposure",
    "emva_bspline_regression", "emva_ptc_linearity_check", "emva_noise_whiteness", "emva_filter_distortion",
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


def _split(avg, var_t, L, gains=(1.0, 1.0, 1.0)):
    """式 (35)(36)(41)(42): 平均画像の空間分散と、列・行・画素への分解。

    *gains* = (画素, 列, 行) の白い雑音の分散の利得。高域フィルタを通した平均画像では、時間雑音の残り σ²/L も
    同じフィルタを通っているので、引く量に利得を掛ける(素の画像では 1)。
    """
    M, N = avg.shape
    g2, g_col, g_row = gains
    mu = float(avg.mean())
    s2 = float(((avg - mu) ** 2).mean()) - g2 * var_t / L               # 式 (35)(36)
    cav = float(((avg.mean(axis=0) - mu) ** 2).mean()) - g_col * var_t / (L * M)
    rav = float(((avg.mean(axis=1) - mu) ** 2).mean()) - g_row * var_t / (L * N)
    A = np.array([[1.0, 0.0, 1.0 / M], [0.0, 1.0, 1.0 / N], [1.0, 1.0, 1.0]])
    col, row, pix = np.linalg.solve(A, np.array([cav, rav, s2]))        # 式 (42)
    return {"mu": mu, "s2": s2, "s2_col": float(col), "s2_row": float(row), "s2_pixel": float(pix)}


def _nonuniformity_variances(d, b, highpass, fn):
    """dark / bright の積み重ねから、平均画像の空間分散(列・行・画素)と時間分散を出す(式 33〜42・65)。

    *highpass* が None でなければ、平均画像に 8.1 節(または付録 C.5)の高域フィルタをかけてから分散を出す。
    平均値 ``mu`` は**フィルタ前**の平均(PRNU の分母、式 67)。
    """
    if d.shape[0] < 2 or b.shape[0] < 2:
        raise ValueError("%s: need at least 2 images per stack (got %d, %d)" % (fn, d.shape[0], b.shape[0]))
    if d.shape[1:] != b.shape[1:]:
        raise ValueError("%s: dark %r and bright %r images differ in shape" % (fn, d.shape[1:], b.shape[1:]))
    out = {}
    hp_info = None
    for nm, st in (("dark", d), ("bright", b)):
        L = st.shape[0]
        var_t = float(st.var(axis=0, ddof=1).mean())                    # 式 (65): 画素ごとの時間分散の平均
        avg = st.mean(axis=0)                                           # 式 (33)
        if highpass is None:
            out[nm] = _split(avg, var_t, L)
        else:
            hp = emva_highpass(avg, method=highpass)
            hp_info = {k: hp[k] for k in ("method", "border", "white_variance_gain", "white_variance_gain_col",
                                          "white_variance_gain_row")}
            out[nm] = _split(hp["image"], var_t, L, (hp["white_variance_gain"], hp["white_variance_gain_col"],
                                                      hp["white_variance_gain_row"]))
            out[nm]["mu"] = float(avg.mean())
        out["var_temporal_" + nm] = var_t
    out["highpass"] = hp_info
    return out


def _nonuniformity_variances_stream(dark_frames, bright_frames, highpass, fn):
    """Streaming counterpart of :func:`_nonuniformity_variances` (``ddof=1``)."""
    def consume(frames, name):
        mean = m2 = None
        count = 0
        for frame in frames:
            x = np.asarray(frame, dtype=np.float64)
            if x.ndim != 2:
                raise ValueError("%s: %s frames must be 2-D" % (fn, name))
            if mean is None:
                mean = x.copy()
                m2 = np.zeros_like(x)
            elif x.shape != mean.shape:
                raise ValueError("%s: %s frames differ in shape" % (fn, name))
            count += 1
            delta = x - mean
            mean += delta / count
            m2 += delta * (x - mean)
        if count < 2:
            raise ValueError("%s: need at least 2 images per stack" % fn)
        return mean, float((m2 / (count - 1)).mean()), count

    out = {}
    hp_info = None
    shapes = []
    counts = []
    for nm, frames in (("dark", dark_frames), ("bright", bright_frames)):
        avg, var_t, count = consume(frames, nm)
        shapes.append(avg.shape); counts.append(count)
        if highpass is None:
            out[nm] = _split(avg, var_t, count)
        else:
            hp = emva_highpass(avg, method=highpass)
            hp_info = {k: hp[k] for k in ("method", "border", "white_variance_gain",
                                          "white_variance_gain_col", "white_variance_gain_row")}
            gains = (hp["white_variance_gain"], hp["white_variance_gain_col"], hp["white_variance_gain_row"])
            out[nm] = _split(hp["image"], var_t, count, gains)
            out[nm]["mu"] = float(avg.mean())
        out["var_temporal_" + nm] = var_t
    if shapes[0] != shapes[1]:
        raise ValueError("%s: dark %r and bright %r images differ in shape" % (fn, *shapes))
    out["highpass"] = hp_info
    out["L"] = tuple(counts)
    return out


def emva_spatial_nonuniformity(dark_stack, bright_stack, K, highpass=None):
    """DSNU と PRNU(式 33〜42・65〜67)。

    *dark_stack*, *bright_stack*: 同じ露光で撮った L 枚(``(L, M, N)``、L ≥ 2)。bright は飽和の約 50 % で撮る。
    平均画像の空間分散から時間雑音の残り σ²_y/L を引き(式 36)、列・行・画素に分け(式 42)、
    DSNU1288 = s_y.dark / K [e⁻] (式 66)、PRNU1288 = √(s²_y.50 − s²_y.dark)/(μ_y.50 − μ_y.dark)(式 67、比)。

    *highpass*: None(既定、渡された画像をそのまま使う —— 互換のため)/ ``"r4"``(8.1 節。規格は式 66・67 を
    **高域フィルタをかけた画像から**求めると書く)/ ``"r3.1"``(付録 C.5 の旧版)。フィルタをかけると端の 9 画素
    (r3.1 は 2 画素)を落とし、時間雑音の残りの引き算にはフィルタの白い雑音の利得を掛ける(導出: 平均画像の時間雑音も
    同じフィルタを通る)。★白い模様の分散そのものも利得 ``highpass["white_variance_gain"]`` 倍になる。4.0 の本文は
    この補正を書いていないので、**補正しない**(付録 C.5 の旧版は 0.96 で割れと書いていた)。

    返り値 ``{"dark": {...}, "bright": {...}, "DSNU1288_e", "PRNU1288", "var_temporal_dark", "var_temporal_bright", "L",
    "highpass"}``(``highpass`` はフィルタの情報か None)。

    **Raises** ``ValueError``: 3-D でない / L < 2 / 形が違う / K が正でない / bright の平均が dark 以下 / s²_y.50 < s²_y.dark /
    highpass の名前が違う / フィルタをかけるには画像が小さい。
    """
    fn = "emva_spatial_nonuniformity"
    d = _arr(dark_stack, "dark_stack", fn, ndim=3)
    b = _arr(bright_stack, "bright_stack", fn, ndim=3)
    k = _pos(K, "K", fn)
    if highpass is not None and highpass not in _HP_METHODS:
        raise ValueError("%s: highpass must be None, 'r4' or 'r3.1' (got %r)" % (fn, highpass))
    out = _nonuniformity_variances(d, b, highpass, fn)
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
    "accum_bin_centers", "accum_counts", "accum_counts_percent", "n_above": 数, "mu"}``。``accum_*`` の 3 つは式 (78)〜(81) の
    升(幅 I/L)の積算ヒストグラム、``accum_x`` / ``accum_percent`` は 257 点の細かい格子の同じ量(図用)。
    ★8.8 節は**高域フィルタをかけた**平均画像で求めると書く(:func:`emva_highpass` を先に通す)。

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
    # 式 (78)〜(81): 積算ヒストグラムを 1/L の整数倍の升で(上の accum_x は 257 点の細かい格子で、規格の升ではない)
    Ia = int(math.floor(Ln * float(dev.max()) / 256.0)) + 1             # 式 (78)
    Qa = int(math.floor(Ln * float(dev.max()) / Ia)) + 1
    qa = np.clip(np.floor(Ln * dev / Ia + 1e-9).astype(np.int64), 0, Qa - 1)   # 式 (79)
    ha = np.bincount(qa, minlength=Qa)
    Ha = np.cumsum(ha[::-1])[::-1]                                      # 式 (81): H[q] = Σ_{q'≥q} h[q']
    ca = (Ia - 1) / (2.0 * Ln) + np.arange(Qa) * Ia / Ln               # 式 (80)
    return {"hist_centers": centers, "hist_counts": counts.astype(np.int64), "accum_x": ax, "accum_percent": accum,
            "accum_bin_centers": ca, "accum_counts": Ha.astype(np.int64), "accum_counts_percent": 100.0 * Ha / dev.size,
            "n_above": int((dev > thr).sum()), "mu": mu}


# ─────────────────────────── 2026-10-13: 規格の残りの式(Linear)と前提の検査 ───────────────────────────

_HP_METHODS = ("r4", "r3.1")
_H_PLANCK = 6.6260755e-34      # 2.1 節に書かれた値 [J s](式 4 の 50.34 はこの値から出る)
_C_LIGHT = 2.99792458e8        # 同 [m/s]


def _box(n):
    return np.full(n, 1.0 / n)


def _hp_smoother_1d(method):
    """高域フィルタの平滑側の 1-D カーネル(分離できるので 2-D は外積)。

    r4(8.1 節): 7 の箱 → 11 の箱 → 3 の二項 [1 2 1]/4 を順にかける = 3 つの畳み込み(19 タップ)。
    r3.1(付録 C.5、式 84): 5 の箱。
    """
    if method == "r4":
        return np.convolve(np.convolve(_box(7), _box(11)), np.array([0.25, 0.5, 0.25]))
    return _box(5)


def _valid_filter_1d(a, k, axis):
    """1-D の相関を 'valid'(端の外を作らない)で。対称なカーネルなので畳み込みと同じ。"""
    w = np.lib.stride_tricks.sliding_window_view(a, k.size, axis=axis)
    return np.tensordot(w, k, axes=([w.ndim - 1], [0]))


def emva_highpass(image, method="r4", line_scan=False):
    """照明のむらを除く高域フィルタ(8.1 節。旧版は付録 C.5 の式 84〜87)。

    8.1 節: 「7 × 7 の箱、11 × 11 の箱、3 × 3 の二項を順にかけて平滑化し、元の画像から引く」。DSNU・PRNU(式 66・67)、
    スペクトログラム(8.6 節)、欠陥画素のヒストグラム(8.8 節)はこの画像から求める(縦横の断面 8.7 節だけはかけない)。
    *method* ``"r4"``(既定、Release 4.0)/ ``"r3.1"``(付録 C.5: 5 × 5 の箱を引く、式 84)。
    *line_scan*: ``"r3.1"`` だけ —— 横 5 × 1 の箱(付録 C.5 の線カメラ)。r4 の線カメラ版は本文に無いので拒む。

    端: 平滑化が完全に定義される内側だけを返す(r4 は各辺 9 画素、r3.1 は 2 画素を落とす)。r3.1 の「上下左右 2 本を
    捨てる」は付録 C.5 の文。r4 の 9 画素は本文に書かれていない —— 3 つのフィルタの半幅の和 3 + 5 + 1 から導いた。

    白い雑音の分散の利得(``white_variance_gain`` = Σh²、h = δ − 平滑化)は**カーネルから厳密に**数える。r3.1 では
    1 − 1/25 = 0.96(本文の式 86 は 0.92、標準偏差を 0.96 で割れと書く —— 二乗が一つ多い。線カメラは
    1 − 1/5 = 0.80 に対し本文の式 87 は 0.64)。列・行の模様(片方向にだけ変わる)は 1-D の利得
    ``white_variance_gain_col`` / ``_row`` で減る。``transfer`` は波数 k̃ = 0..1(ナイキストで 1)の 1-D の伝達関数。

    返り値 ``{"kind": "emva_highpass", "image", "smoothed", "method", "border", "white_variance_gain",
    "white_variance_gain_col", "white_variance_gain_row", "standard_std_divisor", "transfer_k", "transfer"}``
    (``standard_std_divisor`` は付録 C.5 が書く割る数 0.96 / 0.80、r4 は None)。

    **Raises** ``ValueError``: 2-D の実数でない / NaN・inf / method が違う / r4 で line_scan / 画像がカーネルより小さい。
    """
    fn = "emva_highpass"
    if method not in _HP_METHODS:
        raise ValueError("%s: method must be 'r4' (section 8.1) or 'r3.1' (appendix C.5) (got %r)" % (fn, method))
    if line_scan and method == "r4":
        raise ValueError("%s: Release 4.0 section 8.1 defines no line-scan variant of its filter — use method='r3.1'" % fn)
    y = _arr(image, "image", fn, ndim=2)
    k = _hp_smoother_1d(method)
    r = (k.size - 1) // 2
    M, N = y.shape
    if N < k.size + 1 or (not line_scan and M < k.size + 1):
        raise ValueError("%s: image %r is too small for the %d-tap smoothing (need more than %d pixels per filtered axis)"
                         % (fn, y.shape, k.size, k.size))
    sm = _valid_filter_1d(y, k, 1)
    if line_scan:
        core = y[:, r:N - r]
    else:
        sm = _valid_filter_1d(sm, k, 0)
        core = y[r:M - r, r:N - r]
    hp = core - sm
    d1 = -k.copy()
    d1[r] += 1.0
    g1 = float((d1 ** 2).sum())                                         # 1-D: Σ(δ − k)²
    if line_scan:
        g2, gc, gr = g1, g1, 1.0
    else:
        k2 = np.outer(k, k)
        d2 = -k2
        d2[r, r] += 1.0
        g2 = float((d2 ** 2).sum())                                     # 2-D: Σ(δ − k⊗k)²
        gc = gr = g1          # 列の模様 c(n) は縦の平滑で変わらず、横の 1-D で減る(行も同じ)
    kt = np.linspace(0.0, 1.0, 101)
    off = np.arange(k.size) - r
    tr = 1.0 - (k[None, :] * np.cos(np.pi * kt[:, None] * off[None, :])).sum(axis=1)
    std_div = None if method == "r4" else (0.80 if line_scan else 0.96)
    return {"kind": "emva_highpass", "image": hp, "smoothed": sm, "method": method, "border": r,
            "white_variance_gain": g2, "white_variance_gain_col": gc, "white_variance_gain_row": gr,
            "standard_std_divisor": std_div, "transfer_k": kt, "transfer": tr}


def emva_spectrogram(image, axis="horizontal", band=None):
    """水平・垂直のスペクトログラム(8.6 節、式 70〜72)。

    各行(``axis="vertical"`` なら各列)から全体の平均を引き、ŷ[m][v] = (1/√N) Σ_n y[m][n] exp(−2πinv/N)(式 70)、
    P[v] = (1/M) Σ_m ŷ ŷ*(式 71)。白い雑音なら平らで、その高さが空間分散 s²(Parseval: P の全 v の平均 = 画像の分散)。
    *band* = (f_lo, f_hi) [cycles/pixel] を渡すと、その帯の周期模様の振幅 a = 2 ((1/N) Σ_{v=vmin}^{vmax} P[v])^{1/2}
    (式 72、片側の和)を返す。式 72 は帯の中の白い雑音の力も足す —— 照合用(**規格の数ではない**)に、P の中央値を白い床とみて
    帯の点の数 × 床を引いた ``amplitude_above_floor`` も返す。★8.6 節は高域フィルタ(8.1 節)をかけた DSNU 画像 ⟨y_dark⟩ と PRNU 画像
    ⟨y_50⟩ − ⟨y_dark⟩ から求めると書く。

    返り値 ``{"freq": v/N (v = 0..N/2), "power": P[v], "sqrt_power", "mean_power", "variance", "white_floor", "amplitude",
    "amplitude_above_floor", "band", "axis"}``
    (``mean_power`` は全 v の P の平均、``variance`` は平均を引いた画像の分散 —— 両者は等しい)。

    **Raises** ``ValueError``: 2-D の実数でない / NaN・inf / axis が違う / 変換する軸が 4 未満 /
    band が [0, 0.5] の中の lo ≤ hi でない / 帯に周波数の点が無い。
    """
    fn = "emva_spectrogram"
    y = _arr(image, "image", fn, ndim=2)
    if axis not in ("horizontal", "vertical"):
        raise ValueError("%s: axis must be 'horizontal' or 'vertical' (got %r)" % (fn, axis))
    if axis == "vertical":
        y = y.T
    if y.shape[1] < 4:
        raise ValueError("%s: need at least 4 samples along the transformed axis (got %d)" % (fn, y.shape[1]))
    y = y - y.mean()                                                    # 手順 1
    N = y.shape[1]
    yh = np.fft.fft(y, axis=1) / math.sqrt(N)                           # 式 (70)
    P = (yh * np.conj(yh)).real.mean(axis=0)                            # 式 (71)
    v = np.arange(N // 2 + 1)
    out = {"freq": v / N, "power": P[: N // 2 + 1].copy(), "sqrt_power": np.sqrt(P[: N // 2 + 1]),
           "mean_power": float(P.mean()), "variance": float((y ** 2).mean()), "white_floor": float(np.median(P[1:])),
           "amplitude": None, "amplitude_above_floor": None, "band": None, "axis": axis}
    if band is not None:
        try:
            lo, hi = (float(band[0]), float(band[1]))
        except (TypeError, ValueError, IndexError):
            raise ValueError("%s: band must be (f_lo, f_hi) in cycles/pixel (got %r)" % (fn, band)) from None
        if not (math.isfinite(lo) and math.isfinite(hi) and 0.0 <= lo <= hi <= 0.5):
            raise ValueError("%s: band must satisfy 0 <= f_lo <= f_hi <= 0.5 cycles/pixel (got %r)" % (fn, band))
        sel = (out["freq"] >= lo - 1e-12) & (out["freq"] <= hi + 1e-12)
        if not sel.any():
            raise ValueError("%s: no frequency sample of a %d-point transform lies in %r" % (fn, N, band))
        out["amplitude"] = 2.0 * math.sqrt(float(out["power"][sel].sum()) / N)   # 式 (72)
        excess = float(out["power"][sel].sum()) - int(sel.sum()) * out["white_floor"]
        out["amplitude_above_floor"] = 2.0 * math.sqrt(max(excess, 0.0) / N)
        out["band"] = (lo, hi)
    return out


def _snr_inputs(eta, sigma_d, K, sigma_q2, fn):
    e = _pos(eta, "eta", fn)
    if e > 1.0:
        raise ValueError("%s: eta must be in (0, 1] for the linear model (got %r)" % (fn, eta))
    return e, _pos(sigma_d, "sigma_d", fn, allow_zero=True), _pos(K, "K", fn), _pos(sigma_q2, "sigma_q2", fn, allow_zero=True)


def emva_total_snr(mu_p, eta, sigma_d, K, dsnu_e, prnu, sigma_q2=SIGMA_Q2):
    """空間の不均一を含めた総合 SNR(8.5 節、式 68・69)。

    SNR_total = η μ_p / √(σ²_d + DSNU²_1288 + σ²_q/K² + η μ_p + PRNU²_1288 (η μ_p)²)(式 69)。*dsnu_e* [e⁻]、*prnu* は
    **比**(1 % なら 0.01)。DSNU = PRNU = 0 で式 21 に戻り、明るい側では 1/PRNU に頭打ちになる。
    返り値 ``(n, 4)``: 列 = μ_p, SNR(式 21), SNR_total(式 69), SNR_ideal(式 23)。

    **Raises** ``ValueError``: μ_p が負 / η が (0, 1] の外 / σ_d・DSNU・PRNU・σ_q² が負 / K が正でない。
    """
    fn = "emva_total_snr"
    p = _arr(mu_p, "mu_p", fn, ndim=1)
    if (p < 0).any():
        raise ValueError("%s: mu_p must be >= 0" % fn)
    e, sd, k, q2 = _snr_inputs(eta, sigma_d, K, sigma_q2, fn)
    ds = _pos(dsnu_e, "dsnu_e", fn, allow_zero=True)
    pr = _pos(prnu, "prnu", fn, allow_zero=True)
    sig = e * p
    snr = sig / np.sqrt(sd ** 2 + q2 / k ** 2 + sig) if (sd > 0 or q2 > 0) else np.sqrt(sig)
    den = np.sqrt(sd ** 2 + ds ** 2 + q2 / k ** 2 + sig + (pr * sig) ** 2)
    tot = np.divide(sig, den, out=np.zeros_like(sig), where=den > 0)
    return np.ascontiguousarray(np.column_stack([p, snr, tot, np.sqrt(p)]), dtype=np.float64)


def emva_exposure_for_snr(snr, eta, sigma_d, K, sigma_q2=SIGMA_Q2):
    """ある SNR に要る露光 μ_p(SNR)= SNR²/(2η) (1 + √(1 + 4(σ²_d + σ²_q/K²)/SNR²))(式 25、式 21 の逆)。

    SNR = 1 で絶対感度しきい値 μ_p.min(式 26)に一致する。返り値: *snr* と同じ長さの μ_p(signal)。

    **Raises** ``ValueError``: SNR が正でない(式 25 は SNR² で割る)/ η が (0, 1] の外 / σ_d・σ_q² が負 / K が正でない。
    """
    fn = "emva_exposure_for_snr"
    s = _arr(snr, "snr", fn, ndim=None)
    s = np.atleast_1d(s)
    if s.ndim != 1:
        raise ValueError("%s: snr must be a scalar or 1-D" % fn)
    if not (s > 0).all():
        raise ValueError("%s: snr must be > 0 (equation 25 divides by SNR^2)" % fn)
    e, sd, k, q2 = _snr_inputs(eta, sigma_d, K, sigma_q2, fn)
    return s ** 2 / (2.0 * e) * (1.0 + np.sqrt(1.0 + 4.0 * (sd ** 2 + q2 / k ** 2) / s ** 2))


def emva_photon_exposure(irradiance, area_um2, t_exp_ms, wavelength_um):
    """センサ面の放射照度から画素あたりの平均光子数 μ_p = A E t_exp/(hc/λ)(式 3)を、規格の便利な単位で(式 4)。

    μ_p = c₀ · A[µm²] · t_exp[ms] · λ[µm] · E[µW/cm²]、c₀ = 10⁻²³/(h c) = 50.34(式 4。h・c は 2.1 節に書かれた値)。
    *irradiance* [µW/cm²] (スカラか 1-D)。ビニングなら A に縦横のビニング係数を、TDI なら t_exp に段数を掛ける(6.4 節)。
    返り値: μ_p [光子/画素] (signal)。

    **Raises** ``ValueError``: 放射照度が負・非有限 / A・t_exp・λ が正でない。
    """
    fn = "emva_photon_exposure"
    E = np.atleast_1d(_arr(irradiance, "irradiance", fn))
    if E.ndim != 1:
        raise ValueError("%s: irradiance must be a scalar or 1-D" % fn)
    if (E < 0).any():
        raise ValueError("%s: irradiance must be >= 0" % fn)
    A = _pos(area_um2, "area_um2", fn)
    t = _pos(t_exp_ms, "t_exp_ms", fn)
    lam = _pos(wavelength_um, "wavelength_um", fn)
    c0 = 1e-23 / (_H_PLANCK * _C_LIGHT)          # µm²·ms·µm·µW/cm² → m²·s·m·W/m² の桁: 1e-12·1e-3·1e-6·1e-2 = 1e-23
    return c0 * A * t * lam * E


# ── 3 次 B-スプライン(General の式 44〜49。Linear の式 51 はこれを photon transfer に当てる) ──
def _beta3(x):
    """式 (45): β₃(x) = 2/3 − |x|² + |x|³/2(|x| < 1)、(2 − |x|)³/6(1 ≤ |x| ≤ 2)、それ以外 0。"""
    a = np.abs(x)
    return np.where(a < 1.0, 2.0 / 3.0 - a ** 2 + 0.5 * a ** 3, np.where(a <= 2.0, (2.0 - a) ** 3 / 6.0, 0.0))


def _beta3_prime(x):
    """β₃ の導関数。|x| < 1 は式 (49) のとおり −2x(1 − 3|x|/4)。

    ★1 ≤ |x| ≤ 2 の枝は式 (45) を微分すると −sign(x)(2 − |x|)²/2。General の式 (49) は +x/(2|x|)(2 − |x|)² と
    印刷されている(符号が逆)—— 導き直した方を使う(門で有限差分と照合)。
    """
    a = np.abs(x)
    return np.where(a < 1.0, -2.0 * x * (1.0 - 0.75 * a), np.where(a <= 2.0, -np.sign(x) * (2.0 - a) ** 2 / 2.0, 0.0))


def _bspline_basis(x, P, delta, deriv=False):
    t = np.asarray(x, dtype=np.float64)[:, None] / delta - (np.arange(P + 3)[None, :] - 1.0)
    return (_beta3_prime(t) / delta) if deriv else _beta3(t)


def emva_bspline_regression(x, y, n_intervals=8, x_max=None, x_eval=None):
    """3 次 B-スプラインの最小二乗の当てはめと、その傾き(General 6.6 節、式 44〜49)。

    区間 [0, x_max] を P 等分(Δ = x_max/P)、基底 f_p(x) = β₃(x/Δ − (p − 1))(p = 0..P+2 の P + 3 個、式 44・46)。
    係数 a_p は Σ_q (Σ_p a_p f_p(x_q) − y_q)² の最小(式 47、Q > P + 3 点が要る)。傾きは
    Σ_p a_p β₃'(x/Δ − (p − 1)) / Δ(式 48 に連鎖律の 1/Δ を足した —— 本文は正規化した変数での傾き)。
    General は「露光の段数が推奨どおりなら 6〜8 区間」と書く。

    *x_max*: 省略すると max(x)。*x_eval*: 当てはめを評価する追加の点(区間 [0, x_max] の中だけ —— 外挿しない)。
    返り値 ``{"coef", "n_intervals", "x_max", "delta", "fit", "slope", "residual_rms", "x_eval", "fit_eval", "slope_eval"}``。

    **Raises** ``ValueError``: 1-D でない・長さが違う / NaN・inf / P が 1 以上の整数でない / 点が P + 3 以下 /
    x が [0, x_max] の外 / 区間に点が無く係数が決まらない(計画行列の階数が P + 3 未満)/ x_eval が区間の外。
    """
    fn = "emva_bspline_regression"
    xs = _arr(x, "x", fn, ndim=1)
    ys = _arr(y, "y", fn, ndim=1)
    if xs.shape != ys.shape:
        raise ValueError("%s: x and y differ in length (%d, %d)" % (fn, xs.size, ys.size))
    if isinstance(n_intervals, bool) or not isinstance(n_intervals, (int, np.integer)) or int(n_intervals) < 1:
        raise ValueError("%s: n_intervals must be a positive integer (got %r)" % (fn, n_intervals))
    P = int(n_intervals)
    if xs.size <= P + 3:
        raise ValueError("%s: %d points cannot fix %d coefficients — equation 47 needs Q > P + 3" % (fn, xs.size, P + 3))
    xm = float(xs.max()) if x_max is None else _pos(x_max, "x_max", fn)
    if not xm > 0:
        raise ValueError("%s: x_max must be > 0 (got %r)" % (fn, xm))
    if (xs < -1e-12 * xm).any() or (xs > xm * (1 + 1e-12)).any():
        raise ValueError("%s: x must lie in [0, x_max = %g] (got %g .. %g)" % (fn, xm, float(xs.min()), float(xs.max())))
    delta = xm / P
    F = _bspline_basis(xs, P, delta)
    if np.linalg.matrix_rank(F) < P + 3:
        raise ValueError("%s: some of the %d intervals hold too few points to fix the spline — use fewer intervals" % (fn, P))
    coef, *_ = np.linalg.lstsq(F, ys, rcond=None)
    fit = F @ coef
    out = {"coef": coef, "n_intervals": P, "x_max": xm, "delta": delta, "fit": fit,
           "slope": _bspline_basis(xs, P, delta, deriv=True) @ coef,
           "residual_rms": float(np.sqrt(np.mean((ys - fit) ** 2))), "x_eval": None, "fit_eval": None, "slope_eval": None}
    if x_eval is not None:
        xe = np.atleast_1d(_arr(x_eval, "x_eval", fn))
        if xe.ndim != 1:
            raise ValueError("%s: x_eval must be a scalar or 1-D" % fn)
        if (xe < -1e-12 * xm).any() or (xe > xm * (1 + 1e-12)).any():
            raise ValueError("%s: x_eval must lie in [0, x_max = %g] — the regression is not extrapolated" % (fn, xm))
        out["x_eval"] = xe
        out["fit_eval"] = _bspline_basis(xe, P, delta) @ coef
        out["slope_eval"] = _bspline_basis(xe, P, delta, deriv=True) @ coef
    return out


def emva_ptc_linearity_check(mu_y, var_y, mu_y_dark, var_y_dark, mu_y_sat, n_intervals=6, limit=0.03):
    """photon transfer 曲線は直線か(6.6 節、式 51)—— Linear の K を使ってよいかの検査。

    式 (50) の K(0〜70 % の直線当てはめの傾き)と、同じ点に当てた 3 次 B-スプライン(General の式 44〜49)の各点の
    局所の傾き K_i を比べ、相対偏差の大きさ |K_i − K|/K の**平均**が *limit*(3 %)未満なら線形モデルを使ってよい。
    満たさなければ General で評価せよ、と規格は書く。
    ★本文は「相対偏差の大きさの平均」と文で書き、式 (51) は 1/n の無い和で印刷されている。判定は平均、和も返す。
    区間の数は Linear の本文に無い —— 既定 6 は General の「6〜8 区間」の下端(0〜70 % の点だけに当てるので少なめ)。

    返り値 ``{"K", "K_local", "x", "mean_rel_dev", "sum_rel_dev", "limit", "linear_model_ok", "n_points", "n_intervals"}``。

    **Raises** ``ValueError``: :func:`emva_photon_transfer` と :func:`emva_bspline_regression` の拒否 / limit が正でない。
    """
    fn = "emva_ptc_linearity_check"
    lim = _pos(limit, "limit", fn)
    ptc = emva_photon_transfer(mu_y, var_y, mu_y_dark, var_y_dark, mu_y_sat)
    m = _arr(mu_y, "mu_y", fn, ndim=1)
    v = _arr(var_y, "var_y", fn, ndim=1)
    u = ptc["used"]
    x = m[u] - float(mu_y_dark)
    yv = v[u] - float(var_y_dark)
    keep = x >= 0                       # 暗の平均より下の点(雑音で僅かに負)はスプラインの区間 [0, x_max] の外
    sp = emva_bspline_regression(x[keep], yv[keep], n_intervals=n_intervals)
    K = ptc["K"]
    dev = np.abs(sp["slope"] - K) / K
    return {"K": K, "K_local": sp["slope"], "x": x[keep], "mean_rel_dev": float(dev.mean()), "sum_rel_dev": float(dev.sum()),
            "limit": lim, "linear_model_ok": bool(dev.mean() < lim), "n_points": int(keep.sum()), "n_intervals": int(n_intervals)}


def emva_noise_whiteness(y0, y1, y2=None, z_limit=5.0):
    """時間雑音は画素間で独立か(Linear 1.2 節の前提 3)、続けて撮った画像の間で独立か(Linear・General の前提 3)。

    ★規格は前提を書く(「前処理がこの条件を壊すなら Release 4 Linear は使えない。典型は debayer・雑音除去・輪郭強調」)が、
    **確かめ方の数は定義していない**。ここの数はこの族の検査で、規格の数ではない。
    同じ露光の 2 枚の差 d = y0 − y1(固定パターンが消え、時間雑音だけが残る)の隣の画素との相関
    ρ_h = ⟨d[m][n] d[m][n+1]⟩/⟨d²⟩、ρ_v(縦)、斜め ρ_d(2 方向の平均)。白い雑音では 0 で、標準偏差は約 1/√n
    なので z = ρ √n を返す。2 × 2 にまとめた和の分散比 VR = var(和)/(4 var(d)) = 1 + ρ_h + ρ_v + ρ_d は、
    平滑化(雑音除去)で 1 を越え、輪郭強調で 1 を割る。
    *y2*(3 枚目、y1 の次の画像)を渡すと、var(y0 − y2)/var(y0 − y1) − 1 = 1 枚おきの画像の相関 ρ_t を返す
    (1 次の再帰の時間フィルタ y_t = α x_t + (1 − α) y_{t−1} なら ρ_t = 1 − α。独立なら 0、z は √n/√3 で割る近似)。

    返り値 ``{"rho_h", "rho_v", "rho_d", "z_h", "z_v", "z_d", "variance_ratio_2x2", "rho_t", "z_t", "white", "z_limit", "n"}``
    (``white`` は |z| がすべて *z_limit* 未満)。

    **Raises** ``ValueError``: 2-D でない / 形が違う / 4 × 4 未満 / 差がすべて 0(雑音が無い)/ z_limit が正でない。
    """
    fn = "emva_noise_whiteness"
    a = _arr(y0, "y0", fn, ndim=2)
    b = _arr(y1, "y1", fn, ndim=2)
    if a.shape != b.shape:
        raise ValueError("%s: y0 %r and y1 %r differ in shape" % (fn, a.shape, b.shape))
    if a.shape[0] < 4 or a.shape[1] < 4:
        raise ValueError("%s: need at least 4 x 4 pixels (got %r)" % (fn, a.shape))
    zl = _pos(z_limit, "z_limit", fn)
    d = a - b
    d = d - d.mean()
    v = float((d * d).mean())
    if not v > 0:
        raise ValueError("%s: y0 - y1 is constant — there is no temporal noise to test" % fn)
    rh = float((d[:, :-1] * d[:, 1:]).mean()) / v
    rv = float((d[:-1, :] * d[1:, :]).mean()) / v
    rd = 0.5 * (float((d[:-1, :-1] * d[1:, 1:]).mean()) + float((d[:-1, 1:] * d[1:, :-1]).mean())) / v
    n = d.size
    M2, N2 = (d.shape[0] // 2) * 2, (d.shape[1] // 2) * 2
    e = d[:M2, :N2]
    blk = e[0::2, 0::2] + e[1::2, 0::2] + e[0::2, 1::2] + e[1::2, 1::2]
    vr = float(blk.var()) / (4.0 * float(e.var()))
    out = {"rho_h": rh, "rho_v": rv, "rho_d": rd, "z_h": rh * math.sqrt(n), "z_v": rv * math.sqrt(n),
           "z_d": rd * math.sqrt(n), "variance_ratio_2x2": vr, "rho_t": None, "z_t": None, "z_limit": zl, "n": int(n)}
    zs = [out["z_h"], out["z_v"], out["z_d"]]
    if y2 is not None:
        c = _arr(y2, "y2", fn, ndim=2)
        if c.shape != a.shape:
            raise ValueError("%s: y2 %r differs in shape from y0 %r" % (fn, c.shape, a.shape))
        d2 = a - c
        d2 = d2 - d2.mean()
        rt = float((d2 * d2).mean()) / v - 1.0
        out["rho_t"] = rt
        out["z_t"] = rt * math.sqrt(n / 3.0)
        zs.append(out["z_t"])
    out["white"] = bool(all(abs(z) < zl for z in zs))
    return out


def emva_filter_distortion(kernel, temporal_alpha=1.0):
    """カメラの中の線形な前処理が EMVA 1288 Linear の数をどれだけ動かすか —— 閉形式(この族の導出、規格の式ではない)。

    *kernel*: 画像ごとにかかる 2-D の線形フィルタ w(1 × 1 なら数字のゲイン g)。*temporal_alpha*: 続けた画像に
    かかる 1 次の再帰 y_t = α x_t + (1 − α) y_{t−1}(1 = 時間フィルタ無し)。
    平均は G = Σw 倍、白い時間雑音の分散は Σw² 倍になる。2 枚の差の分散(式 18)は再帰で α²/(2 − α) 倍になる。
    S = (Σw²/G²) · α²/(2 − α) とおくと、photon transfer(式 50)の傾き K' = G S K、応答 R' = G R(式 49)、
    η' = R'/K' = η/S(式 52)、σ_d' = σ_d/√S(式 53、量子化を無視)、SNR(μ_p)' = SNR/√S(式 21)。
    固定パターンは空間の w だけを通る: 白い画素の模様の分散は Σw² 倍、列の模様は Σ_n(Σ_m w[m][n])² 倍、行も同様。
    だから DSNU1288' [e⁻] = DSNU · √(gain_x)/S、PRNU1288' = PRNU · √(gain_x)(gain_x = 正規化した各成分の利得)。
    隣の画素の時間雑音の相関の予測 ρ_h・ρ_v・ρ_d と分散比(:func:`emva_noise_whiteness` と同じ定義)も返す。

    前提(破ると閉形式は近似): 量子化と飽和を無視、空間の境界は周期(端の画素を考えない)、雑音と模様は白い。

    返り値 ``{"G", "sum_w2", "S_spatial", "S_temporal", "S", "K_factor", "R_factor", "eta_factor", "sigma_d_factor",
    "snr_factor", "dsnu_e_factor": {"pixel", "col", "row"}, "prnu_factor": {...}, "pattern_gain": {...},
    "rho_h", "rho_v", "rho_d", "variance_ratio_2x2", "rho_t"}``。

    **Raises** ``ValueError``: 2-D の実数でない / NaN・inf / Σw が正でない(平均の符号が反転・消える)/
    temporal_alpha が (0, 1] の外。
    """
    fn = "emva_filter_distortion"
    w = _arr(kernel, "kernel", fn, ndim=2)
    G = float(w.sum())
    if not G > 0:
        raise ValueError("%s: the kernel must sum to a positive gain (got %g) — the mean signal would vanish or flip" % (fn, G))
    a = _pos(temporal_alpha, "temporal_alpha", fn)
    if a > 1.0:
        raise ValueError("%s: temporal_alpha must be in (0, 1] (got %r)" % (fn, temporal_alpha))
    W2 = float((w * w).sum())
    S_sp = W2 / G ** 2
    S_t = a * a / (2.0 - a)
    S = S_sp * S_t
    wc = w.sum(axis=0)                  # 列の模様 c(n) に効く 1-D(行方向に足したもの)
    wr = w.sum(axis=1)
    gain = {"pixel": S_sp, "col": float((wc * wc).sum()) / G ** 2, "row": float((wr * wr).sum()) / G ** 2}

    def ac(dy, dx):                     # 正規化した自己相関 Σ w[m][n] w[m+dy][n+dx] / Σw²
        Mk, Nk = w.shape
        s = 0.0
        for m in range(Mk):
            for n in range(Nk):
                mm, nn = m + dy, n + dx
                if 0 <= mm < Mk and 0 <= nn < Nk:
                    s += w[m, n] * w[mm, nn]
        return s / W2

    rh, rv = ac(0, 1), ac(1, 0)
    rd = 0.5 * (ac(1, 1) + ac(1, -1))
    return {"G": G, "sum_w2": W2, "S_spatial": S_sp, "S_temporal": S_t, "S": S, "K_factor": G * S, "R_factor": G,
            "eta_factor": 1.0 / S, "sigma_d_factor": 1.0 / math.sqrt(S), "snr_factor": 1.0 / math.sqrt(S),
            "dsnu_e_factor": {k: math.sqrt(g) / S for k, g in gain.items()},
            "prnu_factor": {k: math.sqrt(g) for k, g in gain.items()}, "pattern_gain": gain,
            "rho_h": rh, "rho_v": rv, "rho_d": rd, "variance_ratio_2x2": 1.0 + rh + rv + rd, "rho_t": 1.0 - a}
