# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""sensorgeneral — 線形でないカメラ(圧伸・対数・HDR・カメラ内の前処理)を EMVA 1288 Release 4.0 General の手順で測る。

Release 4.0 Linear は「出力が光子数に比例し、時間雑音が画素間で独立」なカメラにしか使えない(Linear 1.2 節)。
General は同じ測定(露光を振って 2 枚ずつ・暗画像・L 枚の積み重ね)を**別の評価**で読む: 特性曲線
μ_y − μ_y.dark = R(μ_p)(式 5)を 3 次 B-スプラインで当て(6.6 節、式 44〜49)、その傾きで出力の雑音を**入力**
(光子)の単位に戻す(式 9・10)。だから量子効率 η とシステムゲイン K は**測れない**と報告する(6.7 節、付録 D.2)
—— 代わりに入力 SNR_p・絶対感度しきい値 μ_p.min・DR・光子単位の暗雑音・DSNU・PRNU を出す。

式の番号は General の本文(Release 4.0 General、2021-06-16)のもの。本文から写した(記憶から書かない)。
B-スプラインは sensorchar の :func:`sensorchar.emva_bspline_regression`(Linear の式 51 と同じ道具)。
暗電流は General 7.1 節のとおり K の代わりに暗い所の傾き R_d(式 25)で割る —— :func:`sensorchar.emva_dark_current`
の K に R_d を渡せば同じ式(式 24、分散の傾きは R_d² で割る)。

★本文の食い違い: 式 (74)(相対量子効率)は μ_p(λ)/μ_p(λ_ref) を**掛ける**と印刷されているが、R⁻¹ が基準波長の
光子数に換算した値なので η(λ)/η(λ_ref) = [R⁻¹(μ_y(λ) − μ_y.dark)/μ_p(λ)] / [R⁻¹(μ_y(λ_ref) − μ_y.dark)/μ_p(λ_ref)]
(割る)でなければ、線形の極限で Linear の式 (82) η(λ) = (μ_y(λ) − μ_y.dark)/(K μ_p(λ)) に戻らない。導き直した方を
使い、印刷どおりの値も ``eq74_as_printed`` として返す(各波長の光子数が等しければ両者は一致する —— 9.1 節は光子数を
揃えるのが望ましいと書く)。

真値(tests/test_sensorgeneral.py): 線形センサでは Linear の数と一致(式 12: SNR_p = SNR_y)、γ のセンサ
μ_y = K^γ(η μ_p)^γ(式 13)では SNR_p = γ SNR_y(式 14)、圧伸したセンサでは圧伸の前の線形センサの SNR・μ_p.min・PRNU を
取り戻す。
"""
from __future__ import annotations

import math

import numpy as np

import sensorchar as _sc

__all__ = ["emva_general_sensitivity", "emva_general_nonuniformity", "emva_general_relative_qe"]

_arr = _sc._arr
_pos = _sc._pos
SIGMA_Q2 = _sc.SIGMA_Q2


def emva_general_sensitivity(mu_p, mu_y, var_y, mu_y_dark, var_y_dark, mu_p_sat, n_intervals=8):
    """特性曲線・入力 SNR・絶対感度しきい値・DR・光子単位の暗雑音(General 2.1〜2.4・6.6〜6.8 節)。

    *mu_p*: 露光段ごとの画素あたりの平均光子数。*mu_y*, *var_y*: 同じ露光の 2 枚から出した平均と時間分散(式 16・18、
    :func:`sensorchar.emva_pair_statistics`)。*mu_y_dark*, *var_y_dark*: 暗画像の同じ量。*mu_p_sat*: 飽和の露光
    (0.1〜0.2 % の画素が最大値になる露光、6.7 節)。0 ≤ μ_p ≤ μ_p.sat の点だけを使う。

    手順:
    1. 特性曲線 μ_y − μ_y.dark = R(μ_p) を [0, μ_p.sat] を P 等分した 3 次 B-スプラインで当て、各点の傾き ∂μ_y/∂μ_p
       と暗い所の傾き R_d = ∂μ_y/∂μ_p|μ_p=0(式 25)を出す(6.6 節)。
    2. 出力 SNR_y = (μ_y − μ_y.dark)/σ_y(式 7)、入力 SNR_p = μ_p |∂μ_y/∂μ_p| / σ_y(式 10)、理想 √μ_p(式 15)。
    3. 逆の関係 μ_p(SNR_p) を同じ区間数の B-スプラインで当て、SNR_p = 1 の露光を μ_p.min とする(6.8 節)。測った
       SNR_p が 1 以下の点を含まなければ拒む(外挿になる。付録 D.1 は SNR ≈ 1 の露光を含めよと書く)。
    3'. 照合用(**規格の手順ではない**): SNR_p が 1 をまたぐ隣の 2 点の間を log-log の直線で補間した ``mu_p_min_local``。
       規格の逆回帰は [0, SNR_max] 全体を P 等分した区間の 3 次で当てるので、SNR ≈ 1 の近くの点の雑音を拾いやすい
       (2 万画素の合成センサで乱数 6 通り: 逆回帰 ±5 %、局所の補間 ±1 %)。
    4. SNR_max = 測った SNR_p の最大(6.8 節。線形でないと飽和の露光で最大とは限らない)、DR = μ_p.sat/μ_p.min(式 21)。
    5. 暗雑音 [光子] σ_d = √(σ²_y.dark − σ²_q)/R_d(General の式 50)。σ²_y.dark < 0.24 DN² なら推定せず上限 0.40/R_d
       (式 51)。

    返り値 ``{"slope", "Rd", "snr_y", "snr_p", "snr_p_ideal", "mu_p_min", "mu_p_min_local", "snr_max", "mu_p_at_snr_max", "DR", "DR_dB",
    "sigma_d_p", "sigma_d_p_upper", "sigma_d_valid", "used", "fit", "n_intervals"}``。
    ★η・K・電子の単位の量は**返さない**(General では測れない、6.7 節)。

    **Raises** ``ValueError``: 長さが違う / μ_p.sat が正でない / 区間に点が足りない(B-スプラインの拒否)/ 傾きが 0 の点 /
    分散が正でない点 / SNR_p ≤ 1 の点が無い / var_y_dark が負。
    """
    fn = "emva_general_sensitivity"
    p = _arr(mu_p, "mu_p", fn, ndim=1, min_size=3)
    m = _arr(mu_y, "mu_y", fn, ndim=1, min_size=3)
    v = _arr(var_y, "var_y", fn, ndim=1, min_size=3)
    if not (p.shape == m.shape == v.shape):
        raise ValueError("%s: mu_p, mu_y and var_y differ in length (%d, %d, %d)" % (fn, p.size, m.size, v.size))
    if (p < 0).any():
        raise ValueError("%s: mu_p must be >= 0" % fn)
    md = float(mu_y_dark)
    if not math.isfinite(md):
        raise ValueError("%s: mu_y_dark must be finite" % fn)
    vd = _pos(var_y_dark, "var_y_dark", fn, allow_zero=True)
    ps = _pos(mu_p_sat, "mu_p_sat", fn)
    use = p <= ps * (1 + 1e-12)
    fit = _sc.emva_bspline_regression(p[use], m[use] - md, n_intervals=n_intervals, x_max=ps, x_eval=[0.0])
    slope = fit["slope"]
    Rd = float(fit["slope_eval"][0])
    pu, mu_u, vu = p[use], m[use] - md, v[use]
    if not (vu > 0).all():
        raise ValueError("%s: a used exposure has temporal variance <= 0 — cannot form an SNR" % fn)
    sy = np.sqrt(vu)
    snr_y = mu_u / sy                                                   # 式 (7)
    snr_p = pu * np.abs(slope) / sy                                     # 式 (10)
    ex = pu > 0
    if not ex.any() or not (snr_p[ex] <= 1.0).any():
        raise ValueError("%s: no exposure reaches SNR_p <= 1 (lowest %.3g) — mu_p.min would be an extrapolation; "
                         "add exposures near SNR = 1 (General appendix D.1)" % (fn, float(snr_p[ex].min()) if ex.any() else float("nan")))
    if (slope[ex] == 0).any():
        raise ValueError("%s: the characteristic curve is flat at an exposed point — the input SNR is undefined" % fn)
    s_ex, p_ex = snr_p[ex], pu[ex]
    inv = _sc.emva_bspline_regression(s_ex, p_ex, n_intervals=n_intervals, x_max=float(s_ex.max()), x_eval=[1.0])
    mpm = float(inv["fit_eval"][0])                                     # 6.8 節: μ_p(SNR_p = 1)
    if not mpm > 0:
        raise ValueError("%s: the inverse SNR regression gives mu_p.min = %g <= 0 — too few exposures near SNR = 1" % (fn, mpm))
    o = np.argsort(p_ex)
    so, po = s_ex[o], p_ex[o]
    above = np.nonzero(so > 1.0)[0]
    j = int(above[0]) if above.size else -1
    if j >= 1 and so[j - 1] > 0:                                        # 照合用: 1 をまたぐ 2 点の log-log 補間
        t = (0.0 - math.log(so[j - 1])) / (math.log(so[j]) - math.log(so[j - 1]))
        mpm_local = math.exp(math.log(po[j - 1]) + t * (math.log(po[j]) - math.log(po[j - 1])))
    else:
        mpm_local = None
    i_max = int(np.argmax(s_ex))
    valid = vd >= _sc._DARK_VAR_FLOOR
    if not Rd > 0:
        raise ValueError("%s: the slope at zero exposure R_d = %g is not positive" % (fn, Rd))
    sdp = math.sqrt(max(vd - SIGMA_Q2, 0.0)) / Rd if valid else None    # General 式 (50)
    dr = ps / mpm                                                       # 式 (21)
    return {"slope": slope, "Rd": Rd, "snr_y": snr_y, "snr_p": snr_p, "snr_p_ideal": np.sqrt(pu), "mu_p_min": mpm,
            "mu_p_min_local": mpm_local, "snr_max": float(s_ex[i_max]), "mu_p_at_snr_max": float(p_ex[i_max]), "DR": dr, "DR_dB": 20.0 * math.log10(dr),
            "sigma_d_p": sdp, "sigma_d_p_upper": None if valid else _sc._DARK_LIMIT_DN / Rd, "sigma_d_valid": bool(valid),
            "used": use, "fit": fit["fit"], "n_intervals": int(n_intervals)}


def emva_general_nonuniformity(dark_stack, bright_stack, slope_50, mu_p_50, Rd, highpass="r4"):
    """DSNU と PRNU を入力(光子)の単位で(General 8 節、式 55・56・58・59)。

    General は不均一を特性曲線の傾きで入力へ戻す(式 55: 不均一は信号の幅より小さいので曲線を局所的に直線とみなす)。
    分散は傾きの二乗で割る(式 56)。暗画像の傾きは R_d(式 25)、明るい画像(飽和の約 50 %)の傾きは *slope_50*。
    DSNU1288 = s_y.dark/R_d [光子] (式 58)、PRNU1288 = √(s²_p.50 − s²_p.dark)/μ_p.50(式 59、比)。
    列・行・画素の成分(式 37〜39)にも同じ式を当てる(8.3 節の最後の段落)。成分の差が雑音で負になるときは 0 とする。
    *highpass*: 既定 ``"r4"``(General 8.1 節も Linear と同じフィルタ)、``"r3.1"``、None。

    返り値 ``{"DSNU1288_p", "DSNU1288_y", "PRNU1288", "dsnu_p": {"col", "row", "pixel"}, "prnu": {...},
    "s2_p_dark", "s2_p_50", "dark", "bright", "highpass"}``。

    **Raises** ``ValueError``: :func:`sensorchar.emva_spatial_nonuniformity` と同じ / slope_50・μ_p.50・R_d が正でない /
    s²_p.50 < s²_p.dark。
    """
    fn = "emva_general_nonuniformity"
    d = _arr(dark_stack, "dark_stack", fn, ndim=3)
    b = _arr(bright_stack, "bright_stack", fn, ndim=3)
    s50 = _pos(slope_50, "slope_50", fn)
    mp50 = _pos(mu_p_50, "mu_p_50", fn)
    rd = _pos(Rd, "Rd", fn)
    if highpass is not None and highpass not in _sc._HP_METHODS:
        raise ValueError("%s: highpass must be None, 'r4' or 'r3.1' (got %r)" % (fn, highpass))
    st = _sc._nonuniformity_variances(d, b, highpass, fn)
    dd, bb = st["dark"], st["bright"]
    s2pd = dd["s2"] / rd ** 2                                           # 式 (56)
    s2pb = bb["s2"] / s50 ** 2
    if s2pb < s2pd:
        raise ValueError("%s: s2_p.50 (%g) < s2_p.dark (%g) — no photo-response nonuniformity to measure" % (fn, s2pb, s2pd))
    comp = ("col", "row", "pixel")
    return {"DSNU1288_p": math.sqrt(max(s2pd, 0.0)), "DSNU1288_y": math.sqrt(max(dd["s2"], 0.0)),
            "PRNU1288": math.sqrt(s2pb - s2pd) / mp50,
            "dsnu_p": {c: math.sqrt(max(dd["s2_" + c], 0.0)) / rd for c in comp},
            "prnu": {c: math.sqrt(max(bb["s2_" + c] / s50 ** 2 - dd["s2_" + c] / rd ** 2, 0.0)) / mp50 for c in comp},
            "s2_p_dark": s2pd, "s2_p_50": s2pb, "dark": dd, "bright": bb, "highpass": st["highpass"]}


def emva_general_relative_qe(mu_p_ref, mu_y_ref, mu_y_dark, mu_y_scan, mu_p_scan, ref_index, n_intervals=8):
    """基準波長に対する相対量子効率 η(λ)/η(λ_ref)(General 9.4 節、式 73・74)。

    基準波長で測った特性曲線の**逆**の関係 μ_p = R⁻¹(μ_y − μ_y.dark)を 3 次 B-スプラインで当て(式 73)、波長を振った
    測定の灰色値 μ_y(λ) を基準波長の光子数に換算する(線形化)。η(λ)/η(λ_ref) =
    [R⁻¹(μ_y(λ) − μ_y.dark)/μ_p(λ)] / [R⁻¹(μ_y(λ_ref) − μ_y.dark)/μ_p(λ_ref)]。
    ★式 (74) は μ_p(λ)/μ_p(λ_ref) を掛けると印刷されている —— 線形の極限で Linear の式 (82) に戻らないので割る形を使う
    (モジュールの説明を参照)。印刷どおりの値は ``eq74_as_printed``。

    *mu_p_ref*, *mu_y_ref*: 基準波長の露光段と灰色値。*mu_y_scan*, *mu_p_scan*: 波長を振った測定の灰色値と光子数。
    *ref_index*: 走査の中で基準波長の位置。

    返り値 ``{"eta_rel", "p_equivalent", "eq74_as_printed", "n_intervals"}``。

    **Raises** ``ValueError``: 長さが違う / μ_p が正でない走査点 / ref_index が範囲外 / 走査の灰色値が基準の特性曲線の
    範囲の外(外挿しない)/ B-スプラインの拒否。
    """
    fn = "emva_general_relative_qe"
    pr = _arr(mu_p_ref, "mu_p_ref", fn, ndim=1, min_size=3)
    yr = _arr(mu_y_ref, "mu_y_ref", fn, ndim=1, min_size=3)
    if pr.shape != yr.shape:
        raise ValueError("%s: mu_p_ref and mu_y_ref differ in length (%d, %d)" % (fn, pr.size, yr.size))
    md = float(mu_y_dark)
    if not math.isfinite(md):
        raise ValueError("%s: mu_y_dark must be finite" % fn)
    ys = np.atleast_1d(_arr(mu_y_scan, "mu_y_scan", fn))
    ps = np.atleast_1d(_arr(mu_p_scan, "mu_p_scan", fn))
    if ys.ndim != 1 or ys.shape != ps.shape:
        raise ValueError("%s: mu_y_scan and mu_p_scan must be 1-D of the same length" % fn)
    if not (ps > 0).all():
        raise ValueError("%s: every scanned exposure mu_p_scan must be > 0" % fn)
    if isinstance(ref_index, bool) or not isinstance(ref_index, (int, np.integer)) or not 0 <= int(ref_index) < ys.size:
        raise ValueError("%s: ref_index must be an integer index into the scan (got %r)" % (fn, ref_index))
    x = yr - md
    keep = x >= 0
    xm = float(x[keep].max())
    xs = ys - md
    if (xs < 0).any() or (xs > xm).any():
        raise ValueError("%s: a scanned gray value lies outside the reference characteristic curve [0, %g] DN — "
                         "the inverse regression is not extrapolated" % (fn, xm))
    inv = _sc.emva_bspline_regression(x[keep], pr[keep], n_intervals=n_intervals, x_max=xm, x_eval=xs)   # 式 (73)
    peq = inv["fit_eval"]
    if not (peq > 0).all():
        raise ValueError("%s: the inverse characteristic curve gives a non-positive photon count for a scanned value" % fn)
    i = int(ref_index)
    rel = (peq / ps) / (peq[i] / ps[i])
    printed = (peq / peq[i]) * (ps / ps[i])
    return {"eta_rel": rel, "p_equivalent": peq, "eq74_as_printed": printed, "n_intervals": int(n_intervals)}
