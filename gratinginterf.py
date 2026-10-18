# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gratinginterf — 格子干渉による位相コントラストと暗視野: タルボ自己像の設計・位相ステップの順モデルと 3 像の分離・暗視野と散乱の関係。

動機(2026-10-15): Fullseye には可視光の位相シフト縞(``fringe``)と、近接ギャップのタルボ効果
(``moirealign.moire_talbot_gap``)はあったが、**格子干渉計**の 3 つの量 —— 平均の透過(吸収)・
縞の位相のずれ(微分位相 = 屈折角)・縞の可視度の低下(暗視野 = 小角散乱)—— を 1 組の位相ステップから
分けて取り出す層が無かった。とくに「可視度の低下」は、Fullseye が初めて扱う物理量である
(試料の中の、画素より小さい構造からの散乱を、画素の明るさではなく縞の振幅で測る)。

内容(8 op):
  設計    `talbot_grating_design`(位相格子・吸収格子の自己像の距離〔分数タルボ距離〕、縞の周期、
          分析格子の周期、円錐ビームでの距離と倍率、線源格子の周期〔Lau の条件〕、角度感度と自己相関長)
  順モデル `grating_stepping_simulate`(透過・微分位相・暗視野の 3 枚の図から、格子を 1 周期ずらしながら撮った
          画像列 (N, H, W) を作る。光子数の Poisson 雑音つき)
  分離    `grating_three_image_retrieve`(試料ありと試料なし〔基準〕の 2 組の画像列 → 透過・微分位相・暗視野。
          1 周期を N 等分した既定の場合は ``fringe.wrapped_phase`` / ``fringe.modulation`` をそのまま呼ぶ。
          1 周期のステップ数が N と違う場合〔端点を含む走査など〕は最小二乗で正弦をあてる)
  散乱    `darkfield_scatter_relation`(暗視野 D と散乱角の広がり σ の換算、線拡散係数、自己相関長)
  絨毯    `talbot_carpet`(2 値の格子の後ろの強度 I(x, z) を回折次数の和で。厳密な角スペクトルか近軸、縞の可視度の z 依存)
  線源    `talbot_source_visibility`(線源の幅・ガウスの焦点・線源格子〔Lau の条件〕で縞の可視度が何倍に落ちるか)
  較正    `grating_step_period_estimate`(1 周期が何ステップかを、正弦をあてた残差の最小で推定。決まらなければ拒否)
  積分    `dpc_integrate`(微分位相 → 波面の位相 → 投影の厚さ。折り返した微分位相は拒否)

式(一次資料で確かめたもの):
  * 位相 π の格子(1 周期の半分が π ずれる)を平面波で照らすと、縞の周期は p1/2、縞の振幅が最大になる距離は
    d_m = (m − 1/2)·p1²/(4λ)、m = 1, 2, …(Weitkamp ら 2005, Opt. Express 13, 6296 の式 2)。
    位相 π/2 の格子では周期 p1、d_m = (m − 1/2)·p1²/λ。吸収格子(線の幅が周期の半分)では周期 p1、
    d_m = m·p1²/λ(m = 1 で半周期ずれた自己像、m = 2 でタルボ長 z_T = 2p1²/λ)。後の 2 つは
    フーリエ級数の厳密な伝搬(``optics.angular_spectrum_propagate``)で門が確かめている。
  * 点光源から距離 L にある格子では、平面波の d_m が d'_m = L·d_m/(L − d_m) に伸びる(同じ文献)。
    縞は M = (L + d')/L 倍に拡大され、分析格子の周期は p2 = M × 縞の周期になる。
  * 縞の位相のずれ φ と波面の位相 Φ: φ = (λ d/p2)·∂Φ/∂x(同じ文献の式 1)。屈折角 α = (λ/2π)·∂Φ/∂x
    なので φ = 2π d α / p2。
  * 線源格子(Lau の条件): 線源格子の 1 本 1 本から出た縞が分析格子の上で 1 周期ずつずれて重なる条件
    p0 = p2·L/d(Pfeiffer ら 2006, Nature Physics 2, 258)。
  * 暗視野: 散乱角の分布 S(θ) が対称なら、縞の可視度は V/V0 = ∫ S(θ) cos(2π d θ/p2) dθ(Strobl 2014,
    Sci. Rep. 4, 7243 の式 5〜7)。S がガウス分布(標準偏差 σ)なら D = V/V0 = exp(−2π² σ² d²/p2²)。
    σ² が厚さ t に比例するとき ε = σ²/t を線拡散係数と呼ぶ(Bech ら 2010, Phys. Med. Biol. 55, 5529)。
    自己相関長は ξ = λ d / p2(Lynch ら 2011, Appl. Opt. 50, 4310)。

規約: 格子の周期は µm、波長は nm(X 線のエネルギーからは λ[nm] = 1.239842/E[keV])、格子間の距離と線源の
距離は mm、角度は µrad、位相は rad。位相ステップは「格子を 1 周期の k/P ずらした画像」を k = 0..N−1 の順に並べ、
各画素の強度を I_k = a·(1 + V·cos(φ − 2πk/P)) と書く(``fringe.wrapped_phase`` と同じ符号)。
正直な限界: 縞の解析は 1 次の正弦だけを見る(高次の調和は暗視野の定義に入れない)。暗視野のガウス近似は
散乱の分布が狭い場合の近似で、粒子の大きさが ξ と同じ程度になると σ では表せない(Strobl 2014)。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "talbot_grating_design", "grating_stepping_simulate", "grating_three_image_retrieve",
    "darkfield_scatter_relation", "talbot_carpet", "talbot_source_visibility", "grating_step_period_estimate",
    "dpc_integrate",
]

#: 第 1 格子の種類(`talbot_grating_design`)。
GRATING_KINDS = ("pi", "pi_half", "absorption")

#: 波長もエネルギーも渡さないときのエネルギー [keV](X 線管の装置で使われる程度)。
DEFAULT_ENERGY_KEV = 28.0

#: hc [keV·nm]。
HC_KEV_NM = 1.2398419843320026

#: 正弦をあてる 3 項の最小二乗の条件数の上限。1 周期の 3 分の 1 ほどしか走査していないと超える
#: (N = 4・P = 16 で 24、N = 5・P = 50 で 150)。超えると雑音が数十倍に増幅されるので拒否する。
_MAX_COND = 30.0

#: 画像の大きさの上限(画素数)。
_MAX_PIXELS = 1 << 24


# --------------------------------------------------------------------------- #
# 入力の検査                                                                    #
# --------------------------------------------------------------------------- #
def _num(v, name, op):
    """optics 族の契約: 文字列と bool は数として通さない。"""
    if isinstance(v, (str, bytes, bool, np.bool_)):
        raise ValueError("%s: %s must be a number, not %s %r" % (op, name, type(v).__name__, v))


def _pos(v, name, op):
    _num(v, name, op)
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a finite number > 0, got %r" % (op, name, v)) from None
    if not (math.isfinite(x) and x > 0.0):
        raise ValueError("%s: %s must be finite and > 0, got %r" % (op, name, v))
    return x


def _finite(v, name, op):
    _num(v, name, op)
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a finite number, got %r" % (op, name, v)) from None
    if not math.isfinite(x):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, v))
    return x


def _int_in(v, name, op, lo, hi):
    _num(v, name, op)
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be an integer, got %r" % (op, name, v)) from None
    if not (math.isfinite(x) and x == int(x) and lo <= int(x) <= hi):
        raise ValueError("%s: %s must be an integer in [%d, %d], got %r" % (op, name, lo, hi, v))
    return int(x)


def _wavelength_nm(wavelength_nm, energy_kev, op):
    if wavelength_nm is not None and energy_kev is not None:
        raise ValueError("%s: give wavelength_nm or energy_kev, not both" % op)
    if wavelength_nm is None and energy_kev is None:
        energy_kev = DEFAULT_ENERGY_KEV
    if wavelength_nm is not None:
        return _pos(wavelength_nm, "wavelength_nm", op)
    return HC_KEV_NM / _pos(energy_kev, "energy_kev", op)


def _map(a, name, op, shape=None):
    """2-D の実数の図(None は呼び手が既定値に置き換える)。"""
    if isinstance(a, (str, bytes)):
        raise ValueError("%s: %s must be a 2-D array, not a string" % (op, name))
    arr = np.asarray(a, dtype=np.float64)
    if arr.ndim == 0 and shape is not None:
        arr = np.full(shape, float(arr))
    if arr.ndim != 2 or min(arr.shape) < 1:
        raise ValueError("%s: %s must be a 2-D array, got shape %s" % (op, name, arr.shape))
    if arr.size > _MAX_PIXELS:
        raise ValueError("%s: %s has %d pixels, more than the cap %d" % (op, name, arr.size, _MAX_PIXELS))
    if not np.all(np.isfinite(arr)):
        raise ValueError("%s: %s contains NaN or Inf" % (op, name))
    if shape is not None and arr.shape != tuple(shape):
        raise ValueError("%s: %s has shape %s but the other maps are %s" % (op, name, arr.shape, tuple(shape)))
    return arr


def _stack(a, name, op):
    if a is None or isinstance(a, (str, bytes)):
        raise ValueError("%s: %s must be a phase-stepping stack (N, H, W)" % (op, name))
    arr = np.asarray(a, dtype=np.float64)
    if arr.ndim != 3:
        raise ValueError("%s: %s must be 3-D (N, H, W), got shape %s" % (op, name, arr.shape))
    if arr.shape[0] < 3:
        raise ValueError("%s: %s has %d steps — at least 3 are needed to separate mean, amplitude and phase"
                         % (op, name, arr.shape[0]))
    if min(arr.shape[1:]) < 1 or arr.size > _MAX_PIXELS * 4:
        raise ValueError("%s: %s has an unusable shape %s" % (op, name, arr.shape))
    if not np.all(np.isfinite(arr)):
        raise ValueError("%s: %s contains NaN or Inf" % (op, name))
    return arr


def _wrap(a):
    """(−π, π] に折り返す。"""
    w = np.mod(np.asarray(a, dtype=np.float64) + np.pi, 2.0 * np.pi) - np.pi
    return np.where(w == -np.pi, np.pi, w)


# --------------------------------------------------------------------------- #
# 1. 設計                                                                       #
# --------------------------------------------------------------------------- #
def talbot_grating_design(period_um=4.0, wavelength_nm=None, energy_kev=None, grating="pi", order=1,
                          source_distance_mm=None):
    """格子干渉計の幾何: 第 1 格子の自己像の距離(分数タルボ距離)、縞と分析格子の周期、線源格子の周期(閉形式)。

    第 1 格子(周期 period_um = p1)を通った波は、ある距離で格子の像(またはその周期の半分の像)を結ぶ。
    その距離に周期の合った吸収格子(分析格子)を置き、どちらかの格子を 1 周期ずらしながら撮ると、各画素で
    縞の正弦が取れる。この op はその距離と周期を返す。

    grating:
      ``"pi"``         位相 π の格子(線の幅が周期の半分)。縞の周期 p1/2、距離 d_m = (m − 1/2)·p1²/(4λ)
                       (Weitkamp ら 2005, Opt. Express 13, 6296 の式 2)。
      ``"pi_half"``    位相 π/2 の格子。縞の周期 p1、d_m = (m − 1/2)·p1²/λ。
      ``"absorption"`` 吸収格子。縞の周期 p1、d_m = m·p1²/λ(m = 2 がタルボ長 z_T = 2p1²/λ)。
    order: m(1 以上の整数)。
    source_distance_mm: 線源から第 1 格子までの距離 L。None は平面波(L = ∞)。有限なら距離は
    d' = L·d/(L − d) に伸び(同じ文献)、縞は M = (L + d')/L 倍に拡大される。L ≤ d では自己像が結ばれない
    (分母が 0 以下)ので拒否する。

    返り値 dict:
      ``wavelength_nm`` / ``talbot_length_mm``(z_T = 2p1²/λ、平面波)/ ``distance_plane_mm``(d_m)/
      ``distance_mm``(d'、円錐ビームで伸びた距離。平面波なら d_m と同じ)/ ``magnification``(M)/
      ``fringe_period_um``(第 1 格子の直後での縞の周期)/ ``analyzer_period_um``(p2 = M × 縞の周期)/
      ``source_grating_period_um``(Lau の条件 p0 = p2·L/d'、Pfeiffer ら 2006。平面波なら None)/
      ``angular_sensitivity``(縞の位相 / 屈折角 = 2π d'/p2 [rad/rad])/
      ``correlation_length_um``(暗視野の自己相関長 ξ = λ d'/p2)/
      ``relative_bandwidth``(縞の振幅が 0 になるまでの波長の幅 Δλ/λ = 1/(2m − 1)。位相 π の格子だけ。
      Weitkamp ら 2005 の式 3。他の格子は None)。

    例(公表値): 14.4 keV、p1 = 4 µm、位相 π、m = 1 → d = 23.2 mm、p2 = 2 µm(平面波。Weitkamp ら 2005 の図 4 の装置)。
    **Raises** ValueError: 正でない周期・波長、wavelength_nm と energy_kev の両方(どちらも無ければ 28 keV)、未知の grating、
    order が 1..1000 の外、L ≤ d。
    """
    op = "talbot_grating_design"
    p1 = _pos(period_um, "period_um", op)
    lam_nm = _wavelength_nm(wavelength_nm, energy_kev, op)
    if grating not in GRATING_KINDS:
        raise ValueError("%s: grating must be one of %s, got %r" % (op, GRATING_KINDS, grating))
    m = _int_in(order, "order", op, 1, 1000)
    lam_um = lam_nm * 1e-3
    p_sq_over_lam_mm = p1 * p1 / lam_um * 1e-3            # p1²/λ [mm]
    if grating == "pi":
        d_plane = (m - 0.5) * p_sq_over_lam_mm / 4.0
        fringe = p1 / 2.0
        bandwidth = 1.0 / (2 * m - 1)
    elif grating == "pi_half":
        d_plane = (m - 0.5) * p_sq_over_lam_mm
        fringe = p1
        bandwidth = None
    else:
        d_plane = m * p_sq_over_lam_mm
        fringe = p1
        bandwidth = None
    if source_distance_mm is None:
        big_l = None
        d = d_plane
        mag = 1.0
        p0 = None
    else:
        big_l = _pos(source_distance_mm, "source_distance_mm", op)
        if big_l <= d_plane * (1.0 + 1e-12):
            raise ValueError("%s: source_distance_mm (%.6g) must exceed the plane-wave distance d_m (%.6g mm) — "
                             "otherwise the spherical wave never forms the self-image (d' = L·d/(L − d) diverges)"
                             % (op, big_l, d_plane))
        d = big_l * d_plane / (big_l - d_plane)
        mag = (big_l + d) / big_l
    p2 = fringe * mag
    if big_l is not None:
        p0 = p2 * big_l / d
    d_um = d * 1e3
    return {"grating": grating, "order": m, "wavelength_nm": lam_nm,
            "talbot_length_mm": 2.0 * p_sq_over_lam_mm,
            "distance_plane_mm": d_plane, "distance_mm": d, "source_distance_mm": big_l,
            "magnification": mag, "fringe_period_um": fringe, "analyzer_period_um": p2,
            "source_grating_period_um": p0,
            "angular_sensitivity": 2.0 * math.pi * d_um / p2,
            "correlation_length_um": lam_um * d_um / p2,
            "relative_bandwidth": bandwidth}


# --------------------------------------------------------------------------- #
# 2. 順モデル                                                                   #
# --------------------------------------------------------------------------- #
def grating_stepping_simulate(transmission=None, dpc_rad=None, darkfield=None, n_steps=8, ref_visibility=0.25,
                              ref_phase_rad=0.0, steps_per_period=None, flux=None, seed=0, shape=(64, 64)):
    """透過・微分位相・暗視野の 3 枚の図から、位相ステップの画像列 (N, H, W) を作る(順モデル)。

    各画素の k 枚目(k = 0..N−1)は I_k = flux·T·(1 + V0·D·cos(φ0 + φ − 2πk/P))。
    T = transmission(吸収)、φ = dpc_rad(縞の位相のずれ = 微分位相。屈折角 α とは φ = 2π d α/p2)、
    D = darkfield(可視度の比、1 = 散乱なし)、V0 = ref_visibility(試料なしの縞の可視度)、
    φ0 = ref_phase_rad(格子のむらによる基準の位相。スカラーか図)、P = steps_per_period
    (1 周期のステップ数。None は N = 1 周期を N 等分)。
    3 枚とも None なら試料なし(基準)の画像列になる: T = 1、φ = 0、D = 1。
    flux: None なら雑音なしの期待値(flux = 1)。数を渡すと、T = 1 の画素の 1 枚あたりの平均光子数として
    Poisson 雑音を足した整数の計数を float で返す(seed で再現)。

    返り値: (N, H, W) float64。``grating_three_image_retrieve`` に試料ありと基準の 2 組を渡すと 3 枚が戻る。
    **Raises** ValueError: 図が 2-D でない / 形がそろわない / NaN・Inf、T < 0、D が [0, 1] の外、
    V0 が (0, 1] の外、n_steps が 3..256 の外、P ≤ 0、flux ≤ 0。
    """
    op = "grating_stepping_simulate"
    n = _int_in(n_steps, "n_steps", op, 3, 256)
    v0 = _finite(ref_visibility, "ref_visibility", op)
    if not 0.0 < v0 <= 1.0:
        raise ValueError("%s: ref_visibility must be in (0, 1], got %r" % (op, ref_visibility))
    period = float(n) if steps_per_period is None else _pos(steps_per_period, "steps_per_period", op)
    shp = None
    for a in (transmission, dpc_rad, darkfield):
        if a is not None:
            shp = _map(a, "map", op).shape
            break
    if shp is None:
        if isinstance(shape, (str, bytes)) or len(tuple(shape)) != 2:
            raise ValueError("%s: shape must be (H, W), got %r" % (op, shape))
        shp = (_int_in(shape[0], "shape[0]", op, 1, 1 << 14), _int_in(shape[1], "shape[1]", op, 1, 1 << 14))
    t = np.ones(shp) if transmission is None else _map(transmission, "transmission", op, shp)
    phi = np.zeros(shp) if dpc_rad is None else _map(dpc_rad, "dpc_rad", op, shp)
    dfm = np.ones(shp) if darkfield is None else _map(darkfield, "darkfield", op, shp)
    phi0 = _map(ref_phase_rad, "ref_phase_rad", op, shp)
    if np.any(t < 0.0):
        raise ValueError("%s: transmission must be >= 0 (it is a ratio of intensities)" % op)
    if np.any(dfm < 0.0) or np.any(dfm > 1.0):
        raise ValueError("%s: darkfield must be in [0, 1] (a ratio of visibilities: scattering only lowers it)" % op)
    delta = 2.0 * np.pi * np.arange(n) / period
    stack = t[None] * (1.0 + v0 * dfm[None] * np.cos(phi0[None] + phi[None] - delta[:, None, None]))
    if flux is None:
        return stack
    lam = _pos(flux, "flux", op)
    rng = np.random.default_rng(_int_in(seed, "seed", op, 0, 2 ** 31 - 1))
    return rng.poisson(lam * stack).astype(np.float64)


# --------------------------------------------------------------------------- #
# 3. 分離                                                                       #
# --------------------------------------------------------------------------- #
def _sine_fit(stack, period, op, name):
    """各画素で I_k = a + b cos(φ − δ_k) をあてる。返り値 (a, b, φ, 残差の RMS / a)。"""
    import fringe                                           # noqa: PLC0415
    n = stack.shape[0]
    delta = 2.0 * np.pi * np.arange(n) / period
    if abs(period - n) <= 1e-9 * n:
        phi = fringe.wrapped_phase(stack)
        mean = stack.mean(axis=0)
        vis = fringe.modulation(stack)
        amp = vis * mean
    else:
        design = np.stack([np.ones(n), np.cos(delta), np.sin(delta)], axis=1)
        cond = np.linalg.cond(design)
        if not math.isfinite(cond) or cond > _MAX_COND:
            raise ValueError("%s: %s — the step phases 2πk/%g for k = 0..%d do not separate mean, cosine and sine "
                             "(condition number %.3g); the stepping covers too little of a period"
                             % (op, name, period, n - 1, cond))
        coef, *_ = np.linalg.lstsq(design, stack.reshape(n, -1), rcond=None)
        mean = coef[0].reshape(stack.shape[1:])
        bc, bs = coef[1].reshape(stack.shape[1:]), coef[2].reshape(stack.shape[1:])
        amp = np.hypot(bc, bs)
        phi = np.arctan2(bs, bc)
    model = mean[None] + amp[None] * np.cos(phi[None] - delta[:, None, None])
    rms = np.sqrt(np.mean((stack - model) ** 2, axis=0))
    with np.errstate(divide="ignore", invalid="ignore"):
        rel = np.where(np.abs(mean) > 0, rms / np.abs(mean), np.inf)
    return mean, amp, phi, rel


def grating_three_image_retrieve(sample_stack, reference_stack=None, steps_per_period_sample=None,
                                 steps_per_period_reference=None, min_visibility=0.02, distance_mm=None,
                                 analyzer_period_um=None, reference_exposure=1.0):
    """位相ステップの 2 組(試料あり・試料なし)から、透過・微分位相・暗視野の 3 枚を分ける。

    各画素で I_k = a·(1 + V·cos(φ − 2πk/P)) をあて(P = 1 周期のステップ数。None は N 等分)、
    透過 T = a_s/a_r、微分位相 φ = wrap(φ_s − φ_r)、暗視野 D = V_s/V_r を返す(Pfeiffer ら 2008,
    Nature Materials 7, 134 の定義)。P = N のときは ``fringe.wrapped_phase`` と ``fringe.modulation``
    (N 段の位相シフトの標準式)をそのまま使い、P ≠ N(1 周期の両端を含む走査など)は 3 項の最小二乗。
    2 組のステップ数は違ってよい(各組を別々にあてる)。

    reference_stack が None なら、試料の画像列だけから a・V・φ を返す(比は取らない)。
    distance_mm と analyzer_period_um を渡すと、屈折角 α = φ·p2/(2π d) [µrad] も返す。
    reference_exposure: 基準を試料の何倍の露光(1 枚あたりの光子数)で撮ったか。透過は a_s/(a_r/reference_exposure)。
    暗視野と微分位相は比と差なので露光に依らない(透過だけが露光の比で化ける)。
    min_visibility: 基準の可視度がこれ未満の画素(格子の欠陥・影)は位相が決まらないので NaN にし、数を返す。
    全画素が NaN になるときは値を返さずに拒否する。

    返り値 dict: ``transmission`` / ``dpc_rad`` / ``darkfield``(いずれも (H, W)、無効画素は NaN)/
    ``visibility_sample`` / ``visibility_reference`` / ``refraction_urad``(幾何があるとき)/
    ``fit_residual_sample`` / ``fit_residual_reference``(正弦をあてた残差の RMS / 平均の中央値。
    1 周期のステップ数を間違えると大きくなる)/ ``n_invalid``。
    **Raises** ValueError: 画像列が 3-D でない・3 枚未満・NaN/Inf、2 組の画素の形が違う、P ≤ 0、
    P が小さすぎて正弦が分けられない、有効な画素が 1 つも無い、幾何の片方だけ、正でない reference_exposure。
    """
    op = "grating_three_image_retrieve"
    s = _stack(sample_stack, "sample_stack", op)
    vmin = _finite(min_visibility, "min_visibility", op)
    if not 0.0 <= vmin < 1.0:
        raise ValueError("%s: min_visibility must be in [0, 1), got %r" % (op, min_visibility))
    ps = float(s.shape[0]) if steps_per_period_sample is None else _pos(steps_per_period_sample,
                                                                        "steps_per_period_sample", op)
    if (distance_mm is None) != (analyzer_period_um is None):
        raise ValueError("%s: give both distance_mm and analyzer_period_um (or neither)" % op)
    a_s, b_s, phi_s, res_s = _sine_fit(s, ps, op, "sample_stack")
    with np.errstate(divide="ignore", invalid="ignore"):
        vis_s = np.where(a_s > 0, b_s / a_s, np.nan)
    out = {"visibility_sample": vis_s, "fit_residual_sample": float(np.nanmedian(res_s))}
    if reference_stack is None:
        out.update({"mean_sample": a_s, "phase_sample_rad": phi_s, "n_invalid": int(np.sum(~np.isfinite(vis_s)))})
        return out
    r = _stack(reference_stack, "reference_stack", op)
    if r.shape[1:] != s.shape[1:]:
        raise ValueError("%s: sample (%s) and reference (%s) images differ in size" % (op, s.shape[1:], r.shape[1:]))
    pr = float(r.shape[0]) if steps_per_period_reference is None else _pos(steps_per_period_reference,
                                                                           "steps_per_period_reference", op)
    a_r, b_r, phi_r, res_r = _sine_fit(r, pr, op, "reference_stack")
    expo = _pos(reference_exposure, "reference_exposure", op)
    with np.errstate(divide="ignore", invalid="ignore"):
        vis_r = np.where(a_r > 0, b_r / a_r, np.nan)
        valid = np.isfinite(vis_r) & (vis_r >= vmin) & (a_r > 0) & np.isfinite(vis_s)
        trans = np.where(valid, a_s * expo / a_r, np.nan)       # 露光の比は平均にだけ効く(可視度は比)
        dfm = np.where(valid, vis_s / vis_r, np.nan)
    dpc = np.where(valid, _wrap(phi_s - phi_r), np.nan)
    if not np.any(valid):
        raise ValueError("%s: no pixel has a reference visibility >= %g — the reference stack shows no fringe "
                         "(wrong stack, or the gratings are not at a self-image distance)" % (op, vmin))
    out.update({"transmission": trans, "dpc_rad": dpc, "darkfield": dfm, "visibility_reference": vis_r,
                "fit_residual_reference": float(np.nanmedian(res_r)), "n_invalid": int(np.sum(~valid))})
    if distance_mm is not None:
        d_um = _pos(distance_mm, "distance_mm", op) * 1e3
        p2 = _pos(analyzer_period_um, "analyzer_period_um", op)
        out["refraction_urad"] = dpc * p2 / (2.0 * math.pi * d_um) * 1e6
    return out


# --------------------------------------------------------------------------- #
# 4. 暗視野と散乱                                                               #
# --------------------------------------------------------------------------- #
def darkfield_scatter_relation(darkfield=None, sigma_urad=None, distance_mm=23.2, analyzer_period_um=2.0,
                               thickness_mm=None, wavelength_nm=None):
    """暗視野 D(可視度の比)と、散乱角の分布の広がり σ の換算(ガウス散乱の公表式)。

    散乱角の分布がガウス(標準偏差 σ、格子の線に直交する向きの成分)なら、縞の可視度は
    D = exp(−2π² σ² d²/p2²)(Strobl 2014, Sci. Rep. 4, 7243 の式 7 をガウスで積分した形 =
    Bech ら 2010, Phys. Med. Biol. 55, 5529 の線拡散係数の式)。d は試料(第 1 格子)から分析格子までの距離、
    p2 は分析格子の周期。逆に σ = (p2/(π d √2))·√(−ln D)。

    darkfield と sigma_urad のどちらか一方を渡す(スカラーか配列)。
    thickness_mm を渡すと線拡散係数 ε = σ²/t [µrad²/mm] を返す(σ² が厚さに比例する、という仮定の下で)。
    wavelength_nm を渡すと自己相関長 ξ = λ d/p2 [µm] を返す(暗視野が感じる構造の大きさの目安)。

    配列の D で (0, 1] の外の画素(雑音で 1 を超えた・0 以下)は σ を NaN にして数を ``n_invalid`` に返す。
    スカラーで (0, 1] の外なら拒否する(黙って 0 や負の σ を返さない)。

    返り値 dict: ``darkfield`` / ``sigma_urad`` / ``diffusion_coeff_urad2_per_mm``(t があるとき)/
    ``correlation_length_um``(λ があるとき)/ ``angular_sensitivity``(2π d/p2)/ ``n_invalid``。
    **Raises** ValueError: darkfield と sigma_urad の両方 / どちらも無い、σ < 0、スカラーの D が (0, 1] の外、
    正でない距離・周期・厚さ・波長、NaN/Inf。
    """
    op = "darkfield_scatter_relation"
    if (darkfield is None) == (sigma_urad is None):
        raise ValueError("%s: give exactly one of darkfield or sigma_urad" % op)
    d_um = _pos(distance_mm, "distance_mm", op) * 1e3
    p2 = _pos(analyzer_period_um, "analyzer_period_um", op)
    k = 2.0 * math.pi * math.pi * d_um * d_um / (p2 * p2)   # −ln D = k σ²(σ in rad)
    scalar = False
    n_invalid = 0
    if darkfield is not None:
        if isinstance(darkfield, (str, bytes, bool, np.bool_)):
            raise ValueError("%s: darkfield must be a number or an array" % op)
        dfm = np.asarray(darkfield, dtype=np.float64)
        scalar = dfm.ndim == 0
        if not np.all(np.isfinite(dfm)):
            raise ValueError("%s: darkfield contains NaN or Inf" % op)
        ok = (dfm > 0.0) & (dfm <= 1.0)
        if scalar and not bool(ok):
            raise ValueError("%s: darkfield must be in (0, 1], got %r — a visibility ratio above 1 or at 0 has no "
                             "Gaussian scattering width" % (op, float(dfm)))
        n_invalid = int(np.sum(~ok))
        with np.errstate(divide="ignore", invalid="ignore"):
            sig = np.where(ok, np.sqrt(np.maximum(-np.log(np.where(ok, dfm, 1.0)), 0.0) / k), np.nan)
        sig_urad = sig * 1e6
    else:
        if isinstance(sigma_urad, (str, bytes, bool, np.bool_)):
            raise ValueError("%s: sigma_urad must be a number or an array" % op)
        sig_urad = np.asarray(sigma_urad, dtype=np.float64)
        scalar = sig_urad.ndim == 0
        if not np.all(np.isfinite(sig_urad)) or np.any(sig_urad < 0):
            raise ValueError("%s: sigma_urad must be finite and >= 0" % op)
        dfm = np.exp(-k * (sig_urad * 1e-6) ** 2)
    out = {"darkfield": float(dfm) if scalar else dfm,
           "sigma_urad": float(sig_urad) if scalar else sig_urad,
           "angular_sensitivity": 2.0 * math.pi * d_um / p2, "n_invalid": n_invalid}
    if thickness_mm is not None:
        t = _pos(thickness_mm, "thickness_mm", op)
        eps = sig_urad ** 2 / t
        out["diffusion_coeff_urad2_per_mm"] = float(eps) if scalar else eps
    if wavelength_nm is not None:
        lam_um = _pos(wavelength_nm, "wavelength_nm", op) * 1e-3
        out["correlation_length_um"] = lam_um * d_um / p2
    return out


# --------------------------------------------------------------------------- #
# 5. タルボ絨毯                                                                 #
# --------------------------------------------------------------------------- #
#: 格子 1 周期の透過の値(線の部分 t_a, 残り t_b)。線の幅の割合は duty。
_GRATING_T = {"pi": (-1.0 + 0j, 1.0 + 0j), "pi_half": (1j, 1.0 + 0j), "absorption": (1.0 + 0j, 0.0 + 0j)}

#: 残差の曲線が「平ら」とみなす最大 / 最小の比(`grating_step_period_estimate`)。P の推定が成り立つかの判定で、
#: 調整するつまみではない(残差が 10 % も変わらない範囲では P は決まらない)。
_MIN_RESIDUAL_CONTRAST = 1.1

#: 折り返しの判定(`dpc_integrate`): 隣り合う画素の差の上限。Itoh の条件そのもの(π を超えた差は、折り返した値からは
#: 2π を足すべきか決まらない)で、数学で決まる値なのでつまみにしない。
_ITOH_LIMIT = math.pi

#: 縞の可視度を出すときに足す回折次数(±N)。
_VIS_HARMONICS = 32768

#: 近軸の式を許す 1 次の回折角の位相誤差の上限 [rad](z_max での 1 次の、厳密な位相との差)。
_MAX_PARAXIAL_ERR = 0.1


def _grating_coeffs(kind, duty, n_harm):
    """2 値の格子 1 周期のフーリエ係数 c_n(n = −N..N、閉形式)。"""
    ta, tb = _GRATING_T[kind]
    n = np.arange(-n_harm, n_harm + 1)
    c = np.empty(n.size, dtype=np.complex128)
    nz = n != 0
    c[nz] = (ta - tb) * (1.0 - np.exp(-2j * np.pi * n[nz] * duty)) / (2j * np.pi * n[nz])
    c[~nz] = ta * duty + tb * (1.0 - duty)
    return n, c


def talbot_carpet(period_um=4.0, wavelength_nm=None, energy_kev=None, grating="pi", duty=0.5, z_max_mm=None,
                  n_z=241, n_x=128, n_periods=2, n_harmonics=63, model="exact"):
    """タルボ絨毯: 2 値の格子(位相 π / 位相 π/2 / 吸収)の後ろの強度 I(x, z) を、回折次数の和で閉形式に出す。

    格子 1 周期の透過 t(x)(線の幅の割合 duty で t_a、残りで t_b)のフーリエ係数 c_n は閉形式
    c_n = (t_a − t_b)(1 − e^{−2πi n·duty})/(2πi n)、c_0 = t_a·duty + t_b(1 − duty)。平面波で照らした場は
    u(x, z) = Σ c_n e^{2πi n x/p} e^{i k_z(n) z}。
    model:
      ``"exact"``     k_z = 2π √(1/λ² − n²/p²)(角スペクトルの厳密な伝搬。1/λ < |n|/p の次数はエバネッセントで減衰)。
      ``"paraxial"``  k_z ≈ 2π/λ − πλ n²/p²(Fresnel)。z_T = 2p²/λ で強度が z = 0 と厳密に同じになる(自己像)。
                      z_max での 1 次の位相誤差 πλ³z/(4p⁴)… が 0.1 rad を超えるときは拒否する(``"exact"`` を使う)。
    縞の可視度 ``visibility``(z ごと)は、縞の周期の次数 h(位相 π の格子は h = 2 = 周期 p/2、他は h = 1)の
    強度の係数 2|I_h|/I_0 で、係数の積から直接出す(x の標本化に依らない)。方形波の縞が完全に結ぶと 4/π。

    z_max_mm: None ならタルボ長 z_T = 2p²/λ の 1 周期分。n_harmonics: 和を打ち切る次数 N(係数は 1/n で減るので、
    角の Gibbs の波打ちは残る —— 図用。距離と可視度は打ち切りにほぼ依らない)。

    返り値 dict: ``intensity``(n_z, n_x)/ ``z_mm`` / ``x_um`` / ``visibility``(n_z)/ ``fringe_harmonic``(h)/
    ``talbot_length_mm`` / ``self_image_mm``(`talbot_grating_design` の分数タルボ距離のうち z_max までのもの)/
    ``wavelength_nm`` / ``model`` / ``paraxial_phase_error_rad``(z_max での 1 次の近軸の位相誤差)。
    **Raises** ValueError: 正でない周期・波長・z_max、wavelength_nm と energy_kev の両方、未知の grating・model、
    duty が (0, 1) の外、n_z・n_x・n_periods・n_harmonics が範囲の外、近軸の誤差が大きすぎる。
    """
    op = "talbot_carpet"
    p = _pos(period_um, "period_um", op)
    lam_nm = _wavelength_nm(wavelength_nm, energy_kev, op)
    if grating not in GRATING_KINDS:
        raise ValueError("%s: grating must be one of %s, got %r" % (op, GRATING_KINDS, grating))
    if model not in ("exact", "paraxial"):
        raise ValueError("%s: model must be 'exact' or 'paraxial', got %r" % (op, model))
    w = _finite(duty, "duty", op)
    if not 0.0 < w < 1.0:
        raise ValueError("%s: duty must be in (0, 1), got %r" % (op, duty))
    nz_ = _int_in(n_z, "n_z", op, 2, 4096)
    nx_ = _int_in(n_x, "n_x", op, 8, 4096)
    nper = _int_in(n_periods, "n_periods", op, 1, 64)
    nh = _int_in(n_harmonics, "n_harmonics", op, 1, 4096)
    if nz_ * nx_ * nper > _MAX_PIXELS:
        raise ValueError("%s: n_z × n_x × n_periods = %d exceeds the cap %d" % (op, nz_ * nx_ * nper, _MAX_PIXELS))
    lam_um = lam_nm * 1e-3
    zt_mm = 2.0 * p * p / lam_um * 1e-3
    zmax = zt_mm if z_max_mm is None else _pos(z_max_mm, "z_max_mm", op)
    # 1 次の近軸の位相誤差: 2π z (√(1/λ² − 1/p²) − (1/λ − λ/(2p²))) ≈ −π λ³ z/(4 p⁴)
    s1 = 1.0 / lam_um ** 2 - 1.0 / p ** 2
    exact1 = math.sqrt(s1) if s1 > 0 else 0.0
    err1 = abs(2.0 * math.pi * zmax * 1e3 * (exact1 - (1.0 / lam_um - lam_um / (2.0 * p * p))))
    if model == "paraxial" and err1 > _MAX_PARAXIAL_ERR:
        raise ValueError("%s: the paraxial model is off by %.3g rad for the first order at z_max = %.6g mm "
                         "(λ/p = %.3g); use model='exact'" % (op, err1, zmax, lam_um / p))
    n, c = _grating_coeffs(grating, w, nh)
    fx = n / p                                                      # 1/µm
    if model == "paraxial":
        kz_rel = -math.pi * lam_um * fx * fx + 0j                   # 共通の位相 2π/λ は落とす
    else:
        kz_rel = 2.0 * math.pi * np.sqrt((1.0 / lam_um ** 2 - fx * fx).astype(np.complex128)) - 2.0 * math.pi / lam_um
    z_mm = np.linspace(0.0, zmax, nz_)
    x_um = (np.arange(nx_ * nper) + 0.5) * (p / nx_)
    prop = np.exp(1j * np.outer(z_mm * 1e3, kz_rel))               # (n_z, 2N+1)
    basis = np.exp(2j * np.pi * np.outer(n, x_um) / p)              # (2N+1, n_x)
    field = (prop * c[None, :]) @ basis
    intensity = np.abs(field) ** 2
    h = 2 if grating == "pi" and abs(w - 0.5) < 1e-12 else 1
    # 可視度は図の打ち切り N と別に、_VIS_HARMONICS 次まで足す(係数の積の尾は 1/N で減る: N = 63 で 1e-2、
    # 32768 で 3e-5 —— 位相格子の z = 0 の「縞なし」がこの桁まで 0 になる)。
    nv, cv = _grating_coeffs(grating, w, max(nh, _VIS_HARMONICS))
    fv = nv / p
    if model == "paraxial":
        kv = -math.pi * lam_um * fv * fv + 0j
    else:
        kv = 2.0 * math.pi * np.sqrt((1.0 / lam_um ** 2 - fv * fv).astype(np.complex128)) - 2.0 * math.pi / lam_um
    vis = np.empty(nz_)
    for i, z in enumerate(z_mm):
        a = cv * np.exp(1j * kv * (z * 1e3))                        # 各次数の振幅
        ih = np.sum(a[h:] * np.conj(a[:-h]))                        # Σ a_n a*_{n−h}
        vis[i] = 2.0 * abs(ih) / float(np.sum(np.abs(a) ** 2))
    if not (np.all(np.isfinite(intensity)) and np.all(np.isfinite(vis))):
        raise ValueError("%s: non-finite intensity (internal overflow)" % op)
    selfs = []
    if abs(w - 0.5) < 1e-12:
        m = 1
        while m <= 1000:
            dm = talbot_grating_design(p, wavelength_nm=lam_nm, grating=grating, order=m)["distance_mm"]
            if dm > zmax * (1.0 + 1e-12):
                break
            selfs.append(dm)
            m += 1
    return {"intensity": intensity, "z_mm": z_mm, "x_um": x_um, "visibility": vis, "fringe_harmonic": h,
            "talbot_length_mm": zt_mm, "self_image_mm": selfs, "wavelength_nm": lam_nm, "model": model,
            "paraxial_phase_error_rad": err1, "grating": grating, "duty": w}


# --------------------------------------------------------------------------- #
# 6. 線源の大きさ・線源格子と縞の可視度                                          #
# --------------------------------------------------------------------------- #
def talbot_source_visibility(source_width_um, source_distance_mm, distance_mm, analyzer_period_um, profile="uniform",
                             source_grating_period_um=None, duty=None, n_slits=None, wavelength_nm=None):
    """線源の大きさと線源格子(Lau の条件)で、縞の可視度が何倍に落ちるか(閉形式、非干渉の和)。

    線源の 1 点が格子の線に直交する向きに s ずれると、分析格子の上の縞は s·d/L だけ逆向きにずれる
    (L = 線源から第 1 格子、d = 第 1 格子から分析格子)。互いに干渉しない点の縞を足すので、可視度の倍率は
    線源の分布のフーリエ変換を周波数 d/(L p2) で読んだ値になる(Pfeiffer ら 2006, Nature Physics 2, 258):
      ``"uniform"`` 幅 w:          |sinc(π w d/(L p2))|(sinc x = sin x / x)
      ``"gaussian"`` 半値全幅 w:   exp(−2π² σ² d²/(L² p2²))、σ = w/(2√(2 ln 2))
    線源格子(周期 p0、開口の割合 duty、開口 n_slits 本)を置くと、各開口は幅 duty·p0 の一様な線源、開口の並びは
    配列の因子 |sin(N β)/(N sin β)|、β = π p0 d/(L p2) を掛ける。β が π の整数倍(Lau の条件 p0 = p2·L/d)で
    すべての開口の縞が重なり、可視度は開口 1 本の |sinc(π duty)|(duty = 0.5 で 2/π)まで戻る。
    n_slits が None なら round(w/p0)(焦点 w に入る開口の数、1 以上)。線源格子はガウスの焦点とは組まない(拒否)。
    duty(開口の割合)は線源格子があるときだけ意味を持つ(None は 0.5)。線源格子なしで duty か n_slits を渡すと、
    黙って無視せずに拒否する(線源格子の周期を渡し忘れた呼び出しを見逃さない)。

    wavelength_nm を渡すと、第 1 格子での横のコヒーレンス長 l_c = λ L/w [µm] も返す。

    返り値 dict: ``visibility_factor`` / ``slit_factor`` / ``array_factor``(線源格子なしは 1)/
    ``lau_period_um``(p2·L/d)/ ``lau_ratio``(p0 / Lau の周期、線源格子なしは None)/ ``n_slits`` /
    ``projected_blur_um``(w·d/L、分析格子の上での線源の影の幅)/ ``coherence_length_um``(λ があるとき)。
    **Raises** ValueError: 正でない幅・距離・周期、未知の profile、ガウスと線源格子の組、duty が (0, 1] の外、
    n_slits が 1..100000 の外、線源格子なしでの duty・n_slits。
    """
    op = "talbot_source_visibility"
    w = _pos(source_width_um, "source_width_um", op)
    big_l = _pos(source_distance_mm, "source_distance_mm", op) * 1e3
    d = _pos(distance_mm, "distance_mm", op) * 1e3
    p2 = _pos(analyzer_period_um, "analyzer_period_um", op)
    if profile not in ("uniform", "gaussian"):
        raise ValueError("%s: profile must be 'uniform' or 'gaussian', got %r" % (op, profile))
    freq = d / (big_l * p2)                                          # 1/µm(線源の座標での縞の周波数)
    lau = p2 * big_l / d
    out = {"lau_period_um": lau, "projected_blur_um": w * d / big_l}
    if source_grating_period_um is None:
        if duty is not None or n_slits is not None:
            raise ValueError("%s: duty and n_slits describe a source grating — pass source_grating_period_um too "
                             "(without a source grating they would be silently ignored)" % op)
        if profile == "uniform":
            x = math.pi * w * freq
            f = 1.0 if x == 0.0 else abs(math.sin(x) / x)
        else:
            sig = w / (2.0 * math.sqrt(2.0 * math.log(2.0)))
            f = math.exp(-2.0 * math.pi ** 2 * sig * sig * freq * freq)
        out.update({"visibility_factor": f, "slit_factor": f, "array_factor": 1.0, "lau_ratio": None, "n_slits": None})
    else:
        if profile != "uniform":
            raise ValueError("%s: a source grating is modelled with a uniformly lit spot only (profile='uniform')" % op)
        p0 = _pos(source_grating_period_um, "source_grating_period_um", op)
        eta = 0.5 if duty is None else _finite(duty, "duty", op)
        if not 0.0 < eta <= 1.0:
            raise ValueError("%s: duty must be in (0, 1], got %r" % (op, duty))
        if n_slits is None:
            ns = max(1, int(round(w / p0)))
        else:
            ns = _int_in(n_slits, "n_slits", op, 1, 100000)
        x = math.pi * eta * p0 * freq
        slit = 1.0 if x == 0.0 else abs(math.sin(x) / x)
        beta = math.pi * p0 * freq
        sb = math.sin(beta)
        if abs(sb) < 1e-12:
            arr = 1.0
        else:
            arr = abs(math.sin(ns * beta) / (ns * sb))
        out.update({"visibility_factor": slit * arr, "slit_factor": slit, "array_factor": arr,
                    "lau_ratio": p0 / lau, "n_slits": ns})
    if wavelength_nm is not None:
        out["coherence_length_um"] = _pos(wavelength_nm, "wavelength_nm", op) * 1e-3 * big_l / w
    return out


# --------------------------------------------------------------------------- #
# 7. 1 周期のステップ数の推定                                                    #
# --------------------------------------------------------------------------- #
def grating_step_period_estimate(stack, p_min=None, p_max=None, p_step=0.05, region=None, min_visibility=0.05):
    """位相ステップの画像列から「1 周期が何ステップか」(P)を、正弦をあてた残差の最小で推定する。

    実際の装置では、格子を動かす量の較正のずれや「1 周期の両端を含む走査」で、1 周期のステップ数 P が
    撮った枚数 N と一致しない。P を間違えると縞の位相・振幅の読みが系統的に狂う(``grating_three_image_retrieve`` の
    ``fit_residual_*`` が大きくなる)。この op は P を p_min..p_max(既定 N − 2 .. N + 2)で p_step 刻みに振り、
    region の画素で I_k = a + b cos(φ − 2πk/P) をあてた残差の RMS / 平均を、画素について二乗平均した値が最小の P を返す。
    残差は 9 桁に丸めて比べ、同点は小さい P を取る(argmin が同点で返す位置が、丸めの屑で OS ごとに変わらないように)。

    region: (y0, y1, x0, x1) の画素の範囲(試料の無い空気・基準の画素を選ぶ)。None は全画素。
    min_visibility: 残差に数える画素の縞の可視度の下限(P = N で一度あてた振幅 / 平均)。格子の欠陥・影・試料の
    縁など、縞の弱い画素は正弦の残差が雑音だけになって P の判定を薄めるので、数に入れない。

    次のときは値を返さずに拒否する(fail-closed):
      * N < 5(未知数 3 + P に対して残差の自由度が足りない)
      * 可視度が min_visibility 以上の画素が 1 つも無い(縞が無い)
      * 最小が探索の範囲の端(本当の最小は外にあるかもしれない)
      * 残差の最大 / 最小が 1.1 未満(曲線が平らで P が決まらない。判定の定数で、つまみではない)

    返り値 dict: ``steps_per_period``(P)/ ``n_steps``(N)/ ``p_grid`` / ``residual``(各 P の残差)/
    ``residual_min`` / ``residual_at_n``(P = N の残差。N が格子に無ければ None)/ ``visibility_median``
    (数に入れた画素の)/ ``n_pixels``(数に入れた画素の数)/ ``resolution``(= p_step)。
    **Raises** ValueError: 上の拒否、画像列が 3-D でない・NaN/Inf、region が画像の外、p_min ≥ p_max、
    p_step ≤ 0、格子が 2000 点を超える。
    """
    op = "grating_step_period_estimate"
    s = _stack(stack, "stack", op)
    n = s.shape[0]
    if n < 5:
        raise ValueError("%s: %d steps — at least 5 are needed to tell the step period from the residual "
                         "(3 unknowns per pixel plus P)" % (op, n))
    if region is not None:
        if isinstance(region, (str, bytes)) or len(tuple(region)) != 4:
            raise ValueError("%s: region must be (y0, y1, x0, x1), got %r" % (op, region))
        y0, y1, x0, x1 = (_int_in(v, "region", op, 0, 1 << 20) for v in region)
        if not (y0 < y1 <= s.shape[1] and x0 < x1 <= s.shape[2]):
            raise ValueError("%s: region %r is empty or outside the %s images" % (op, region, s.shape[1:]))
        s = s[:, y0:y1, x0:x1]
    lo = float(n - 2) if p_min is None else _pos(p_min, "p_min", op)
    hi = float(n + 2) if p_max is None else _pos(p_max, "p_max", op)
    st = _pos(p_step, "p_step", op)
    if not lo < hi:
        raise ValueError("%s: p_min (%g) must be < p_max (%g)" % (op, lo, hi))
    n_grid = int(math.floor((hi - lo) / st + 1e-9)) + 1
    if n_grid < 3 or n_grid > 2000:
        raise ValueError("%s: the search grid has %d points (needs 3..2000)" % (op, n_grid))
    vmin = _finite(min_visibility, "min_visibility", op)
    if not 0.0 <= vmin < 1.0:
        raise ValueError("%s: min_visibility must be in [0, 1), got %r" % (op, min_visibility))
    grid = np.round(lo + st * np.arange(n_grid), 9)
    res = np.full(n_grid, np.inf)
    # 数に入れる画素: P = N(1 周期を N 等分)で一度あてた可視度が vmin 以上。P の候補ごとに選び直さない
    # (候補ごとに画素の組が変わると、残差の比較が別の集合どうしの比較になる)。
    m0, a0, _p0, _r0 = _sine_fit(s, float(n), op, "stack")
    with np.errstate(divide="ignore", invalid="ignore"):
        vis0 = np.where(m0 > 0, a0 / m0, np.nan)
    use = np.isfinite(vis0) & (vis0 >= vmin)
    if not np.any(use):
        raise ValueError("%s: no pixel has a fringe visibility >= %g (median %.3g) — no fringe to fit "
                         "(choose an air/reference region)" % (op, vmin, float(np.nanmedian(vis0))))
    vmed = float(np.median(vis0[use]))
    # 残差は P に依らない画素の素の平均で割る。あてた平均で割ると、P のずれが平均に漏れた分だけ雑音の項が
    # P の一次で傾き、最小が雑音の大きさに比例して偏る(1 枚 3000 光子・V 0.25・22 段で +0.06 段)。
    raw_mean = np.abs(s.mean(axis=0))
    for i, pp in enumerate(grid):
        try:
            mean, amp, _phi, rel = _sine_fit(s, float(pp), op, "stack")
        except ValueError:
            continue                                                # 正弦が分けられない P は候補から外す
        with np.errstate(divide="ignore", invalid="ignore"):
            rel = np.where(raw_mean > 0, rel * np.abs(mean) / raw_mean, np.nan)
        sel = rel[use]
        res[i] = round(float(np.sqrt(np.nanmean(sel * sel))), 9)       # 二乗平均(中央値より雑音に強い)
    if not np.any(np.isfinite(res)):
        raise ValueError("%s: no step period in [%g, %g] separates mean, cosine and sine" % (op, lo, hi))
    k = int(np.argmin(res))                                         # 同点は前(小さい P)
    if k == 0 or k == n_grid - 1:
        raise ValueError("%s: the residual minimum is at the edge of the search range (P = %g in [%g, %g]) — "
                         "the true step period may lie outside; widen p_min/p_max" % (op, grid[k], lo, hi))
    finite = res[np.isfinite(res)]
    if not float(np.max(finite)) >= _MIN_RESIDUAL_CONTRAST * max(float(res[k]), 1e-300):
        raise ValueError("%s: the residual curve is flat (max/min = %.3g < %g) — the step period is not "
                         "determined by these images" % (op, float(np.max(finite)) / max(float(res[k]), 1e-300),
                                                         _MIN_RESIDUAL_CONTRAST))
    at_n = np.nonzero(np.abs(grid - n) < 1e-9)[0]
    return {"steps_per_period": float(grid[k]), "n_steps": n, "p_grid": grid, "residual": res,
            "residual_min": float(res[k]), "residual_at_n": float(res[at_n[0]]) if at_n.size else None,
            "visibility_median": vmed, "n_pixels": int(np.sum(use)), "resolution": st}


# --------------------------------------------------------------------------- #
# 8. 微分位相の積分                                                             #
# --------------------------------------------------------------------------- #
def dpc_integrate(dpc_rad, pixel_um, distance_mm, analyzer_period_um, wavelength_nm=None, energy_kev=None, axis=1,
                  baseline="left", baseline_px=8, delta=None):
    """微分位相(縞の位相のずれ φ)を格子の感度の向きに積分して、波面の位相 Φ [rad] に戻す。

    屈折角 α = φ·p2/(2π d)(Weitkamp ら 2005 の式 1)、∂Φ/∂x = (2π/λ)·α。画素の中で平均した α を
    画素の幅で足すと、画素の境界での Φ が出る(``np.cumsum``)。返すのは隣り合う境界の平均(画素の中心)。
    dpc_rad は 2-D の図か、``grating_three_image_retrieve`` の返り値(表。``dpc_rad`` を取り出す)。
    delta(屈折率の 1 からのずれ δ)を渡すと、投影の厚さ t = −Φ·λ/(2π δ) [µm] も返す。

    積分の定数(と、基準と試料の間の格子のずれによる微分位相の一定のずれ)は baseline で決める:
      ``"left"``  各行の最初の baseline_px 画素(試料の無い縁)で Φ = 0
      ``"both"``  両端の baseline_px 画素で Φ = 0 になるように、行ごとに一次式を引く
                  (微分位相の一定のずれ = 位相の傾きを消す。試料が両端に掛からないことが前提)
      ``"none"``  何も引かない(最初の境界で Φ = 0)

    ★折り返し(fail-closed): 微分位相は (−π, π] に折り返されている。本当の φ が π を超えた画素では
    隣と 2π 近く跳ぶ。積分の向きに隣り合う画素の差が π(Itoh の条件。数学で決まる値なのでつまみにしない)を超える画素が
    1 つでもあれば、どれだけ足すべきか決まらないので値を返さずに拒否する(縞の位相を大きくしない ——
    距離 d を短くするか、細かい画素で撮る)。NaN(``grating_three_image_retrieve`` の無効画素)も拒否する。
    正直な限界: 折り返しは「隣との跳び」でしか見えない。平らな背景の隣にある 1 画素だけが π を超え、折り返した値が
    背景と π 以内に収まる場合(縁の 1 画素など)は、折り返した図だけからは見分けられない(本当の跳びが π を超える
    = 標本化が足りない、という Itoh の条件の外)。

    返り値 dict: ``phase_rad``(H, W)/ ``thickness_um``(δ があるとき)/ ``refraction_urad`` /
    ``max_jump_rad``(実測の隣との差の最大)/ ``baseline``。
    **Raises** ValueError: 2-D でない・NaN/Inf、正でない画素・距離・周期・波長、wavelength_nm と energy_kev の両方 / どちらも無い、
    axis が 0/1 でない、未知の baseline、baseline_px が幅の半分を超える、δ ≤ 0、隣との差が π を超える。
    """
    op = "dpc_integrate"
    if wavelength_nm is None and energy_kev is None:
        raise ValueError("%s: give wavelength_nm or energy_kev — the phase scale 2π/λ has no safe default" % op)
    if isinstance(dpc_rad, dict):                                   # grating_three_image_retrieve の返り値をそのまま
        if "dpc_rad" not in dpc_rad:
            raise ValueError("%s: the table has no 'dpc_rad' (pass the result of grating_three_image_retrieve "
                             "with a reference stack, or the 2-D map itself)" % op)
        dpc_rad = dpc_rad["dpc_rad"]
    if isinstance(dpc_rad, (str, bytes)) or dpc_rad is None:
        raise ValueError("%s: dpc_rad must be a 2-D array" % op)
    phi = np.asarray(dpc_rad, dtype=np.float64)
    if phi.ndim != 2 or min(phi.shape) < 2:
        raise ValueError("%s: dpc_rad must be 2-D with at least 2 pixels per side, got shape %s" % (op, phi.shape))
    if phi.size > _MAX_PIXELS:
        raise ValueError("%s: dpc_rad has %d pixels, more than the cap %d" % (op, phi.size, _MAX_PIXELS))
    n_bad = int(np.sum(~np.isfinite(phi)))
    if n_bad:
        raise ValueError("%s: dpc_rad has %d NaN/Inf pixels (invalid pixels of the retrieval) — the integral "
                         "would carry them along the whole row; mask or fill them first" % (op, n_bad))
    px = _pos(pixel_um, "pixel_um", op)
    d_um = _pos(distance_mm, "distance_mm", op) * 1e3
    p2 = _pos(analyzer_period_um, "analyzer_period_um", op)
    lam_um = _wavelength_nm(wavelength_nm, energy_kev, op) * 1e-3
    ax = _int_in(axis, "axis", op, 0, 1)
    if baseline not in ("left", "both", "none"):
        raise ValueError("%s: baseline must be 'left', 'both' or 'none', got %r" % (op, baseline))
    jmax = _ITOH_LIMIT
    work = phi if ax == 1 else phi.T
    jumps = np.abs(np.diff(work, axis=1))
    worst = float(np.max(jumps))
    if worst > jmax:
        r, c = np.unravel_index(int(np.argmax(jumps)), jumps.shape)
        n_j = int(np.sum(jumps > jmax))
        raise ValueError("%s: %d neighbouring pixel pairs differ by more than %.4g rad (worst %.4g rad at line %d, "
                         "pixel %d) — the differential phase is wrapped (true |φ| > π) or under-sampled, so the "
                         "integral is ambiguous" % (op, n_j, jmax, worst, r, c))
    alpha = work * p2 / (2.0 * math.pi * d_um)                       # rad
    grad = 2.0 * math.pi / lam_um * alpha                            # rad/µm
    edges = np.concatenate([np.zeros((work.shape[0], 1)), np.cumsum(grad * px, axis=1)], axis=1)
    centre = 0.5 * (edges[:, 1:] + edges[:, :-1])
    w = centre.shape[1]
    if baseline != "none":
        bp = _int_in(baseline_px, "baseline_px", op, 1, max(1, w // 2))
        left = centre[:, :bp].mean(axis=1, keepdims=True)
        if baseline == "left":
            centre = centre - left
        else:
            right = centre[:, -bp:].mean(axis=1, keepdims=True)
            xl, xr = (bp - 1) / 2.0, w - 1 - (bp - 1) / 2.0
            xs = np.arange(w)[None, :]
            centre = centre - (left + (right - left) * (xs - xl) / (xr - xl))
    phase = centre if ax == 1 else centre.T
    out = {"phase_rad": phase, "refraction_urad": (alpha if ax == 1 else alpha.T) * 1e6,
           "max_jump_rad": worst, "baseline": baseline}
    if delta is not None:
        dl = _pos(delta, "delta", op)
        out["thickness_um"] = -phase * lam_um / (2.0 * math.pi * dl)
    return out
