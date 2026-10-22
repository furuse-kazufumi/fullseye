# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""cavityoptics —— 光共振器(Fabry-Perot)と Michelson 干渉計の「設計の式」を閉形式の真値つきで。

重力波望遠鏡(LIGO / Virgo / KAGRA)は、km 級の Michelson の両腕に Fabry-Perot 共振器を
置いた干渉計で、腕の長さの差 ΔL = hL(h: ひずみ)を出力光量で読む。同じ式が
検査装置の側にもそのまま要る —— エタロン(波長フィルタ)の線幅、レーザー共振器の
モード間隔、干渉計測の散射雑音の限界、共振器の長さを合わせる PDH ロックの誤差信号。
fullseye には ``interferometry``(白色干渉・クロマティック共焦点)と ``coherent``
(スペックル)はあったが、**共振器そのもの**と**量子雑音の予算**は 1 本も無かった
(2026-10-14 時点で repo の全層を引いて 0 件)。

収めた式(どれも教科書・公表論文の閉形式で、``tests/test_cavityoptics.py`` が確かめる):

  1. **Fabry-Perot の応答**(``fabry_perot_response``): 鏡の強度透過率 T₁, T₂ と損失から
     振幅反射率 ``r_i = √(1 − T_i − ℓ_i)``、自由スペクトル間隔 ``FSR = c/2L``、
     フィネス ``F = π√(r₁r₂)/(1 − r₁r₂)``、Airy 透過 ``T(φ) = T_max/(1 + (2F/π)² sin²(φ/2))``。
     半値全幅は厳密に ``Δφ = 4·asin(π/2F)``(F が大きいと 2π/F)、共振器の極は半値半幅
     ``f_p = δν/2``。aLIGO の腕(L 3994.5 m、T_ITM 1.4 %、T_ETM 5 ppm)で F ≈ 445、f_p ≈ 42 Hz。
  2. **腕共振器のひずみ伝達関数**(``cavity_strain_transfer``): 単極 ``1/√(1 + (f/f_p)²)`` に
     往復伝搬の ``sinc(2πfL/c)``(FSR で零)を掛け、利得は単純 Michelson の ``2F/π`` 倍。
  3. **Michelson の DC 読み出し**(``michelson_dc_readout``): 暗縞から φ₀ だけずらした
     反対称ポートの光量 ``P_AS = P_in sin²((φ₀ + 4πhL/λ)/2)``、ひずみ感度 ``dP/dh``、
     散射雑音 ``√(2ħωP_AS)`` を割った散射雑音限界 ``h_shot``。φ₀ → 0 で
     ``h_shot → (1/2L)√(ħcλ/πP_in)``(オフセットに依らない極限、**門**)。
  4. **Pound-Drever-Hall の誤差信号**(``pdh_error_signal``、Black 2001 *Am. J. Phys.* 69, 79):
     ``ε = 2√(P_c P_s)·Im[F(ω)F*(ω+Ω) − F*(ω)F(ω−Ω)]``、``F(ω)`` は共振器の反射係数。
     **反対称**(``ε(−δ) = −ε(δ)``)、共振で零、対称共振器の共振近傍の傾きは
     ``−8√(P_c P_s)/δν``(Black 式 15、Ω ≫ δν)。
  5. **量子雑音の予算**(``quantum_noise_budget``、Kimble ら 2001 *Phys. Rev. D* 65, 022002):
     通常の干渉計で ``h_SQL² = 8ħ/(mΩ²L²)``、``K = 2(I₀/I_SQL)γ⁴/(Ω²(γ²+Ω²))``、
     ``I_SQL = mL²γ⁴/(4ω₀)``、``γ = Tc/4L``、散射 ``S_shot = h_SQL²/2K``、
     輻射圧 ``S_rp = K·h_SQL²/2``。恒等式 **``S_shot·S_rp = h_SQL⁴/4``**(不確定性の積、
     入力光量に依らない)と **``S_total ≥ h_SQL²``、等号は K = 1**(``I₀ = I_SQL`` かつ
     ``Ω = γ``)が門。

型語彙(**新語はゼロ**): 入力は数値の引数だけ、出力は ``table``(dict)と ``pairs``
((N, 2) の曲線)。曲線は ``mtf_diffraction`` / ``relative_illumination`` と同じ ``pairs``。
"""
from __future__ import annotations

import numpy as np

__all__ = ["fabry_perot_response", "cavity_strain_transfer", "michelson_dc_readout",
           "pdh_error_signal", "quantum_noise_budget"]

#: 光速 [m/s] (CODATA 2018、定義値)
C_LIGHT = 299792458.0
#: 換算プランク定数 [J·s] (CODATA 2018、定義値)
HBAR = 1.054571817e-34

#: 曲線を返す op の点数の上限(探針が巨大な配列を要求しても fail-closed)
_MAX_POINTS = 1_000_000


# --------------------------------------------------------------------------- #
# 入口の検査(fail-closed)                                                     #
# --------------------------------------------------------------------------- #
def _positive(v, name: str, op: str) -> float:
    f = float(v)
    if not np.isfinite(f) or f <= 0.0:
        raise ValueError("%s: %s must be a positive finite number, got %r" % (op, name, v))
    return f


def _nonneg(v, name: str, op: str) -> float:
    f = float(v)
    if not np.isfinite(f) or f < 0.0:
        raise ValueError("%s: %s must be a non-negative finite number, got %r" % (op, name, v))
    return f


def _fraction(v, name: str, op: str, *, open_top: bool = False) -> float:
    f = float(v)
    ok = np.isfinite(f) and 0.0 <= f <= 1.0 and not (open_top and f >= 1.0)
    if not ok:
        raise ValueError("%s: %s must be in [0, 1%s, got %r"
                         % (op, name, ")" if open_top else "]", v))
    return f


def _count(v, name: str, op: str, lo: int = 2, hi: int = _MAX_POINTS) -> int:
    try:
        n = int(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be an integer, got %r" % (op, name, v))
    if n != float(v) or n < lo or n > hi:
        raise ValueError("%s: %s must be an integer in [%d, %d], got %r" % (op, name, lo, hi, v))
    return n


def _freq_axis(freqs, name: str, op: str) -> np.ndarray:
    f = np.asarray(freqs, dtype=np.float64).reshape(-1)
    if f.size < 1 or f.size > _MAX_POINTS:
        raise ValueError("%s: %s must have 1..%d entries, got %d" % (op, name, _MAX_POINTS, f.size))
    if not np.isfinite(f).all() or (f <= 0.0).any():
        raise ValueError("%s: %s must be positive finite frequencies [Hz]" % (op, name))
    return f


def _mirrors(t1, t2, loss1, loss2, op: str):
    """強度透過率と損失 → 振幅反射率 (r1, r2)。``T + ℓ < 1`` を要求する。"""
    T1 = _fraction(t1, "itm_transmittance", op, open_top=True)
    T2 = _fraction(t2, "etm_transmittance", op, open_top=True)
    l1 = _fraction(loss1, "itm_loss", op, open_top=True)
    l2 = _fraction(loss2, "etm_loss", op, open_top=True)
    if T1 + l1 >= 1.0 or T2 + l2 >= 1.0:
        raise ValueError("%s: transmittance + loss must be < 1 for each mirror" % op)
    if T1 <= 0.0 and T2 <= 0.0:
        raise ValueError("%s: at least one mirror must transmit (T1 = T2 = 0 is a closed box)" % op)
    return float(np.sqrt(1.0 - T1 - l1)), float(np.sqrt(1.0 - T2 - l2)), T1, T2


# --------------------------------------------------------------------------- #
# 1. Fabry-Perot の応答                                                        #
# --------------------------------------------------------------------------- #
def fabry_perot_response(length_m: float = 3994.5, wavelength_nm: float = 1064.0, *,
                         itm_transmittance: float = 0.014, etm_transmittance: float = 5e-6,
                         itm_loss: float = 0.0, etm_loss: float = 0.0) -> dict:
    """Fabry-Perot 共振器の設計量(FSR・フィネス・線幅・極・増幅率・蓄積時間)を閉形式で返す。

    Parameters
    ----------
    length_m : float
        共振器長 L [m]。既定は aLIGO の腕(3994.5 m)。
    wavelength_nm : float
        レーザー波長 [nm]。既定 1064 nm(Nd:YAG)。
    itm_transmittance, etm_transmittance : float
        入力鏡・終端鏡の**強度**透過率(0 ≤ T < 1)。既定は aLIGO(1.4 % / 5 ppm)。
    itm_loss, etm_loss : float
        各鏡の強度損失(吸収 + 散乱)。``T + ℓ < 1``。

    Returns
    -------
    dict
        ``fsr_hz`` = c/2L、``finesse`` = π√(r₁r₂)/(1 − r₁r₂)、
        ``linewidth_hz``(半値全幅、厳密に ``FSR·(2/π)·asin(π/2F)``)、
        ``linewidth_approx_hz`` = FSR/F、``pole_hz`` = 線幅の半分(共振器の極)、
        ``storage_time_s`` = 1/(2π·pole)、``power_gain`` = 共振での循環光量/入射光量
        = T₁/(1 − r₁r₂)²、``transmission_max`` = T₁T₂/(1 − r₁r₂)²、
        ``reflection_min`` = 共振での反射率 ``((r₁ − r₂(1−ℓ₁... ))/(1 − r₁r₂))²`` の
        損失なし形 ``((r₁ − r₂)/(1 − r₁r₂))²``、``r1`` / ``r2``、``round_trip_phase_per_hz``
        = 4πL/c、``mode_number`` = 2L/λ(共振の次数、参考値)。

    Notes
    -----
    aLIGO の既定値で F ≈ 445、FSR 37.5 kHz、線幅 84 Hz、極 42 Hz、循環光量 ≈ 280 倍
    (入力鏡の透過 1.4 % に対して)。``linewidth_hz`` と ``pole_hz`` は Airy 関数の半値を
    **厳密に**与える(``asin`` 形)ので、``tests`` では透過曲線を細かく標本化して半値の
    交点を独立に探し、この値と突き合わせる。
    """
    op = "fabry_perot_response"
    L = _positive(length_m, "length_m", op)
    lam = _positive(wavelength_nm, "wavelength_nm", op) * 1e-9
    r1, r2, T1, T2 = _mirrors(itm_transmittance, etm_transmittance, itm_loss, etm_loss, op)
    rr = r1 * r2
    fsr = C_LIGHT / (2.0 * L)
    finesse = np.pi * np.sqrt(rr) / (1.0 - rr)
    # Airy: T(φ) = T_max / (1 + (2F/π)² sin²(φ/2)) → 半値は sin(φ/2) = π/2F
    x = np.pi / (2.0 * finesse)
    if x >= 1.0:                       # F < π/2: 半値が FSR の外(ほぼ透明な鏡)
        fwhm_phase = 2.0 * np.pi
    else:
        fwhm_phase = 4.0 * np.arcsin(x)
    linewidth = fsr * fwhm_phase / (2.0 * np.pi)
    pole = 0.5 * linewidth
    return {
        "fsr_hz": float(fsr),
        "finesse": float(finesse),
        "linewidth_hz": float(linewidth),
        "linewidth_approx_hz": float(fsr / finesse),
        "pole_hz": float(pole),
        "storage_time_s": float(1.0 / (2.0 * np.pi * pole)),
        "power_gain": float(T1 / (1.0 - rr) ** 2),
        "transmission_max": float(T1 * T2 / (1.0 - rr) ** 2),
        "reflection_min": float(((r1 - r2) / (1.0 - rr)) ** 2),
        "r1": float(r1),
        "r2": float(r2),
        "round_trip_phase_per_hz": float(4.0 * np.pi * L / C_LIGHT),
        "mode_number": float(2.0 * L / lam),
    }


def _airy_transmission(phase: np.ndarray, finesse: float, t_max: float) -> np.ndarray:
    return t_max / (1.0 + (2.0 * finesse / np.pi) ** 2 * np.sin(0.5 * phase) ** 2)


# --------------------------------------------------------------------------- #
# 2. 腕共振器のひずみ伝達関数                                                  #
# --------------------------------------------------------------------------- #
def cavity_strain_transfer(length_m: float = 3994.5, finesse: float = 445.0,
                           f_min_hz: float = 1.0, f_max_hz: float = 100000.0,
                           n_points: int = 512) -> np.ndarray:
    """腕共振器がひずみ h(f) を出力の位相へ写す伝達関数の大きさ |H(f)| を ``pairs`` で返す。

    Parameters
    ----------
    length_m : float
        腕の長さ L [m]。
    finesse : float
        フィネス F(``fabry_perot_response`` の値を渡す)。
    f_min_hz, f_max_hz : float
        周波数の範囲(対数等間隔)。
    n_points : int
        点数。

    Returns
    -------
    numpy.ndarray
        ``(n_points, 2)``: 列 0 = 周波数 [Hz]、列 1 = ``|H| = (2F/π)·|sinc(2πfL/c)|/√(1 + (f/f_p)²)``、
        ``f_p = c/(4FL)``(共振器の極)。DC で ``2F/π``(単純 Michelson の往復回数倍)。

    Notes
    -----
    ``sinc`` は往復伝搬の間にひずみが振動して打ち消す効果(``f = c/2L`` の FSR で零)。
    門: ``f = f_p`` で DC の ``1/√2``(sinc の寄与は 1e-6 以下)、``f = FSR`` で零。
    """
    op = "cavity_strain_transfer"
    L = _positive(length_m, "length_m", op)
    F = _positive(finesse, "finesse", op)
    lo = _positive(f_min_hz, "f_min_hz", op)
    hi = _positive(f_max_hz, "f_max_hz", op)
    if hi <= lo:
        raise ValueError("%s: f_max_hz must exceed f_min_hz" % op)
    n = _count(n_points, "n_points", op)
    f = np.logspace(np.log10(lo), np.log10(hi), n)
    f_p = C_LIGHT / (4.0 * F * L)
    u = 2.0 * np.pi * f * L / C_LIGHT
    sinc = np.abs(np.sin(u) / u)
    gain = (2.0 * F / np.pi) * sinc / np.sqrt(1.0 + (f / f_p) ** 2)
    return np.stack([f, gain], axis=1)


# --------------------------------------------------------------------------- #
# 3. Michelson の DC 読み出し                                                  #
# --------------------------------------------------------------------------- #
def michelson_dc_readout(power_w: float = 1.0, arm_length_m: float = 1.0,
                         wavelength_nm: float = 1064.0, *, dc_offset_rad: float = 0.1,
                         strain: float = 0.0) -> dict:
    """暗縞から φ₀ だけずらした Michelson の反対称ポート光量・ひずみ感度・散射雑音限界。

    Parameters
    ----------
    power_w : float
        ビームスプリッタに入る光量 P_in [W]。
    arm_length_m : float
        腕の長さ L [m] (単純 Michelson。共振器の利得は ``cavity_strain_transfer`` で別に掛ける)。
    wavelength_nm : float
        波長 [nm]。
    dc_offset_rad : float
        暗縞からのオフセット位相 φ₀ [rad] (0 < φ₀ < π)。
    strain : float
        ひずみ h(腕の差 ΔL = hL)。

    Returns
    -------
    dict
        ``p_out_w`` = ``P_in sin²((φ₀ + 4πhL/λ)/2)``、``slope_w_per_strain`` = dP/dh
        = ``P_in sin(φ₀ + 4πhL/λ)·2πL/λ``、``shot_noise_w_per_rthz`` = ``√(2ħω P_out)``、
        ``h_shot_per_rthz`` = 散射雑音/傾き、``h_shot_limit_per_rthz`` = φ₀ → 0 の極限
        ``(1/2L)√(ħcλ/πP_in)``、``phase_total_rad``。

    Notes
    -----
    散射雑音限界は小さなオフセットで ``h_shot = (1/2L)√(ħcλ/πP_in)/cos(φ_total/2)``、
    φ → 0 で極限値に収束する(オフセットを下げるほど光量は減るが感度の比は変わらない ——
    DC 読み出しが成り立つ理由)。``tests`` は傾きを有限差分で独立に求めて突き合わせる。
    """
    op = "michelson_dc_readout"
    P = _positive(power_w, "power_w", op)
    L = _positive(arm_length_m, "arm_length_m", op)
    lam = _positive(wavelength_nm, "wavelength_nm", op) * 1e-9
    phi0 = float(dc_offset_rad)
    if not np.isfinite(phi0) or phi0 <= 0.0 or phi0 >= np.pi:
        raise ValueError("%s: dc_offset_rad must be in (0, π), got %r" % (op, dc_offset_rad))
    h = float(strain)
    if not np.isfinite(h):
        raise ValueError("%s: strain must be finite, got %r" % (op, strain))
    omega = 2.0 * np.pi * C_LIGHT / lam
    phi = phi0 + 4.0 * np.pi * h * L / lam
    p_out = P * np.sin(0.5 * phi) ** 2
    slope = P * np.sin(phi) * (2.0 * np.pi * L / lam)
    shot = np.sqrt(2.0 * HBAR * omega * p_out)
    h_limit = (1.0 / (2.0 * L)) * np.sqrt(HBAR * C_LIGHT * lam / (np.pi * P))
    return {
        "p_out_w": float(p_out),
        "slope_w_per_strain": float(slope),
        "shot_noise_w_per_rthz": float(shot),
        "h_shot_per_rthz": float(shot / slope) if slope != 0.0 else float("inf"),
        "h_shot_limit_per_rthz": float(h_limit),
        "phase_total_rad": float(phi),
    }


# --------------------------------------------------------------------------- #
# 4. Pound-Drever-Hall の誤差信号                                              #
# --------------------------------------------------------------------------- #
def _reflection_coefficient(delta_hz: np.ndarray, fsr_hz: float, r1: float, r2: float) -> np.ndarray:
    """損失なし共振器の反射係数 F(ω) = (r₁ − r₂e^{iφ})/(1 − r₁r₂e^{iφ})、φ = 2πδ/FSR。"""
    e = np.exp(1j * 2.0 * np.pi * delta_hz / fsr_hz)
    return (r1 - r2 * e) / (1.0 - r1 * r2 * e)


def pdh_error_signal(length_m: float = 1.0, *, itm_transmittance: float = 0.01,
                     etm_transmittance: float = 0.01, mod_freq_hz: float = 2.0e7,
                     mod_depth: float = 1.08, power_w: float = 1.0,
                     span_linewidths: float = 6.0, n_points: int = 1201) -> np.ndarray:
    """Pound-Drever-Hall 誤差信号 ε(δ) を、共振からの離調 δ [Hz] の関数として ``pairs`` で返す。

    Parameters
    ----------
    length_m : float
        共振器長 L [m]。
    itm_transmittance, etm_transmittance : float
        鏡の強度透過率(損失なし)。
    mod_freq_hz : float
        位相変調周波数 Ω/2π [Hz]。線幅より十分大きいと傾きが Black の式 15 に乗る。
    mod_depth : float
        変調指数 β。搬送波 ``P_c = J₀(β)²P``、側帯波 ``P_s = J₁(β)²P``(β = 1.08 で ``P_c·P_s`` 最大)。
    power_w : float
        入射光量 P [W]。
    span_linewidths : float
        表示する離調の範囲(線幅の何倍まで、±)。
    n_points : int
        点数(奇数なら δ = 0 を含む)。

    Returns
    -------
    numpy.ndarray
        ``(n_points, 2)``: 列 0 = 離調 δ [Hz]、列 1 = ε [W]
        ``= 2√(P_c P_s)·Im[F(δ)F*(δ+Ω) − F*(δ)F(δ−Ω)]``。

    Notes
    -----
    門(``tests``): 反対称 ``ε(−δ) = −ε(δ)``(1e-12)、``ε(0) = 0``、対称共振器
    (T₁ = T₂)で Ω ≫ δν のとき共振近傍の傾き ``dε/dδ = −8√(P_c P_s)/δν``(Black 2001 式 15)に
    1 % 以内。側帯波が共振に乗る ``δ = ±Ω`` 付近の小さな山も含めて返す(表示範囲が届けば)。
    """
    from scipy.special import j0, j1

    op = "pdh_error_signal"
    L = _positive(length_m, "length_m", op)
    r1, r2, _T1, _T2 = _mirrors(itm_transmittance, etm_transmittance, 0.0, 0.0, op)
    Om = _positive(mod_freq_hz, "mod_freq_hz", op)
    beta = _positive(mod_depth, "mod_depth", op)
    P = _positive(power_w, "power_w", op)
    span = _positive(span_linewidths, "span_linewidths", op)
    n = _count(n_points, "n_points", op, lo=3)
    resp = fabry_perot_response(L, 1064.0, itm_transmittance=itm_transmittance,
                                etm_transmittance=etm_transmittance)
    fsr, lw = resp["fsr_hz"], resp["linewidth_hz"]
    delta = np.linspace(-span * lw, span * lw, n)
    phase = np.exp(1j * 2.0 * np.pi * delta / fsr)
    side = np.exp(1j * 2.0 * np.pi * Om / fsr)

    def reflection(e):
        return (r1 - r2 * e) / (1.0 - r1 * r2 * e)

    Fw = reflection(phase)
    Fp = reflection(phase * side)
    Fm = reflection(phase / side)
    pc = (j0(beta) ** 2) * P
    ps = (j1(beta) ** 2) * P
    eps = 2.0 * np.sqrt(pc * ps) * np.imag(Fw * np.conj(Fp) - np.conj(Fw) * Fm)
    return np.stack([delta, eps], axis=1)


# --------------------------------------------------------------------------- #
# 5. 量子雑音の予算(Kimble ら 2001 の通常干渉計)                               #
# --------------------------------------------------------------------------- #
def quantum_noise_budget(power_w: float = 5200.0, mirror_mass_kg: float = 40.0,
                         length_m: float = 3994.5, wavelength_nm: float = 1064.0, *,
                         itm_transmittance: float = 0.014, f_min_hz: float = 5.0,
                         f_max_hz: float = 5000.0, n_points: int = 400) -> dict:
    """通常の(信号再利用なし)Fabry-Perot Michelson の量子雑音 —— 散射・輻射圧・標準量子限界。

    Parameters
    ----------
    power_w : float
        ビームスプリッタに入る光量 I₀ [W] (aLIGO 設計: 125 W × 出力再利用 ≈ 5.2 kW)。
    mirror_mass_kg : float
        試験質量 m [kg] (aLIGO 40 kg)。
    length_m : float
        腕の長さ L [m]。
    wavelength_nm : float
        波長 [nm]。
    itm_transmittance : float
        入力鏡の強度透過率 T(腕共振器の半値半幅 ``γ = Tc/4L`` [rad/s] を決める)。
    f_min_hz, f_max_hz : float
        周波数範囲(対数等間隔)。
    n_points : int
        点数。

    Returns
    -------
    dict
        ``f_hz``(配列)、振幅スペクトル密度 [1/√Hz] の配列 ``shot`` / ``radiation_pressure`` /
        ``sql`` / ``total``(``√(S_shot + S_rp)``)、``kappa``(Kimble の K(Ω))、
        スカラ ``gamma_rad_s`` / ``pole_hz`` / ``i_sql_w``(``I_SQL = mL²γ⁴/4ω₀``)/
        ``power_ratio`` = I₀/I_SQL / ``f_sql_touch_hz``(K = 1 で総和が SQL に触れる周波数、
        無ければ ``None``)/ ``arm_power_w``(循環光量 ≈ ``I₀·2/T`` の目安)。

    Notes
    -----
    Kimble, Levin, Matsko, Thorne & Vyatchanin, *Phys. Rev. D* 65, 022002 (2001) 式 (16)–(20):
    ``h_SQL² = 8ħ/(mΩ²L²)``、``K = 2(I₀/I_SQL)γ⁴/(Ω²(γ²+Ω²))``、``S_shot = h_SQL²/2K``、
    ``S_rp = K h_SQL²/2``。門: ``S_shot·S_rp = h_SQL⁴/4``(光量に依らない恒等式)、
    ``S_total ≥ h_SQL²`` で等号は K = 1 だけ。I₀ = I_SQL のとき K(γ) = 1 なので ``f_sql_touch_hz``
    = γ/2π。aLIGO の設計感度は信号再利用と熱雑音を含むのでこの曲線とは形が違う ——
    ``examples/poc_gw_detector_pseudo_simulation.py`` が設計曲線と第二実装(gwinc)に当てる。
    """
    op = "quantum_noise_budget"
    I0 = _positive(power_w, "power_w", op)
    m = _positive(mirror_mass_kg, "mirror_mass_kg", op)
    L = _positive(length_m, "length_m", op)
    lam = _positive(wavelength_nm, "wavelength_nm", op) * 1e-9
    T = _fraction(itm_transmittance, "itm_transmittance", op, open_top=True)
    if T <= 0.0:
        raise ValueError("%s: itm_transmittance must be > 0 (a closed arm has no bandwidth)" % op)
    lo = _positive(f_min_hz, "f_min_hz", op)
    hi = _positive(f_max_hz, "f_max_hz", op)
    if hi <= lo:
        raise ValueError("%s: f_max_hz must exceed f_min_hz" % op)
    n = _count(n_points, "n_points", op)
    f = np.logspace(np.log10(lo), np.log10(hi), n)
    Om = 2.0 * np.pi * f
    omega0 = 2.0 * np.pi * C_LIGHT / lam
    gamma = T * C_LIGHT / (4.0 * L)
    i_sql = m * L * L * gamma ** 4 / (4.0 * omega0)
    kappa = 2.0 * (I0 / i_sql) * gamma ** 4 / (Om * Om * (gamma * gamma + Om * Om))
    h_sql2 = 8.0 * HBAR / (m * Om * Om * L * L)
    s_shot = h_sql2 / (2.0 * kappa)
    s_rp = kappa * h_sql2 / 2.0
    # K(Ω) = 1 の根: K は Ω で単調減少なので、K(lo) ≥ 1 ≥ K(hi) のときだけ 1 本ある
    touch = None
    if kappa[0] >= 1.0 - 1e-9 and kappa[-1] <= 1.0 + 1e-9:
        lk = np.log(kappa)
        touch = float(np.exp(np.interp(0.0, -lk, np.log(f))))
    return {
        "f_hz": f,
        "shot": np.sqrt(s_shot),
        "radiation_pressure": np.sqrt(s_rp),
        "sql": np.sqrt(h_sql2),
        "total": np.sqrt(s_shot + s_rp),
        "kappa": kappa,
        "gamma_rad_s": float(gamma),
        "pole_hz": float(gamma / (2.0 * np.pi)),
        "i_sql_w": float(i_sql),
        "power_ratio": float(I0 / i_sql),
        "f_sql_touch_hz": touch,
        "arm_power_w": float(I0 * 2.0 / T),
    }
