# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""photoelastic — 光弾性の族: 応力場の閉形式 → 位相差と主軸 → 偏光像 → 位相差と主軸の推定。

Photoelasticity family. Plane-stress fields with textbook closed forms, the
stress-optic law (isotropic, and cubic crystals cut on a {100} plane), the
fringe intensities of plane and circular polariscopes, the four-direction
polarisation camera / six-intensity polarimeter images, their closed-form
inversion, and multi-wavelength order resolution.

単位は **SI に統一**する(長さ m・応力 Pa・力 N・応力光学係数 Pa⁻¹)。位相差は
**rad** で受け渡し、人が読む量(nm・縞次数)は同じ dict に並べて返す —— 片方だけ
返すと呼び手が単位を取り違えても気づけないため。引数名に単位を付け
(``thickness_m`` / ``wavelength_m``)、桁の外れた値(mm を m に、nm を m に、
×10⁻⁷ MPa⁻¹ の表の数字をそのまま Pa⁻¹ に渡す)は **ValueError で拒否**する。

座標: ``x`` は右、``y`` は**上**(画像の行は下向きなので、格子を作る op は
``y = (中心行 − 行) × 画素``)。角度は x 軸から反時計回り、度で受け渡す。

真値の門(``tests/test_photoelastic_2026_10_23.py``):
  * 円板の直径圧縮(Hondros/Frocht の点荷重解): 外周で表面力 0(荷重点以外)、
    中心で σx = 2P/(πDt)・σy = −6P/(πDt)、水平直径上の σy の積分 = −P/t、
    平衡方程式(差分)。
  * 穴のある無限板の一軸引張(Kirsch): 穴の縁で σrr = τrθ = 0、σθθ(90°) = 3S、
    σθθ(0°) = −S、遠方で一様応力、平衡方程式。
  * 偏光器の閉形式 = Mueller 計算(``optics.mueller_element`` の素子を並べた鎖)。
  * 合成 → 推定で位相差と主軸が 1e-9 で戻る。
  * 立方晶: 4 階テンソルを回す経路 = Stoehr ら(2020)式 (26) の閉形式。
    π44 = π11 − π12 で等方の式に一致。

既存の op との棲み分け: 素子 1 枚の Mueller 行列と Stokes の読みは ``optics``
(``mueller_element`` / ``mueller_apply`` / ``stokes_analyze``)、偏光カメラの
モザイク分解は ``optics.polarization_demosaic``(その返り = 0/45/90/135 度の
``(4, H, W)`` を :func:`photoelastic_phase_estimate` がそのまま食う)、
位相の 2-D アンラップは ``fringe.unwrap_phase_2d``。ここは光弾性に固有の部分だけ。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "brazilian_disc_stress", "kirsch_plate_stress", "principal_stress",
    "retardation_from_birefringence", "photoelastic_retardation", "retardation_convert",
    "cubic_photoelastic_birefringence", "silicon_piezo_optic_coefficients",
    "polariscope_intensity", "photoelastic_polarization_images",
    "photoelastic_phase_estimate", "retardation_unwrap_multiwavelength",
]

# --------------------------------------------------------------------------- #
# 入力の検査(fail-closed)
# --------------------------------------------------------------------------- #


def _scalar(v, name, op, lo=None, hi=None, lo_open=True, hint=""):
    """有限の実数スカラを取り出す。範囲外は理由つきで ValueError。"""
    if isinstance(v, bool) or v is None:
        raise ValueError("%s: %s must be a real number, got %r" % (op, name, v))
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a real number, got %r" % (op, name, v)) from None
    if np.ndim(v) != 0:
        raise ValueError("%s: %s must be a scalar, got shape %r" % (op, name, np.shape(v)))
    if not math.isfinite(x):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, x))
    if lo is not None and (x < lo or (lo_open and x == lo)):
        raise ValueError("%s: %s = %g is out of range (must be %s %g)%s"
                         % (op, name, x, ">" if lo_open else ">=", lo, hint))
    if hi is not None and x > hi:
        raise ValueError("%s: %s = %g is out of range (must be <= %g)%s"
                         % (op, name, x, hi, hint))
    return x


def _field(v, name, op):
    """有限の実数配列(スカラも可)。空・複素・非有限は拒否。"""
    if v is None or isinstance(v, (str, bytes, dict)):
        raise ValueError("%s: %s must be a real number or array, got %r"
                         % (op, name, type(v).__name__))
    try:
        a = np.asarray(v)
    except Exception:                                          # pragma: no cover
        raise ValueError("%s: %s could not be read as an array" % (op, name)) from None
    if a.dtype.kind == "c":
        raise ValueError("%s: %s is complex — pass the real field" % (op, name))
    if a.dtype.kind not in "biuf":
        raise ValueError("%s: %s must be numeric, got dtype %s" % (op, name, a.dtype))
    a = a.astype(np.float64)
    if a.size == 0:
        raise ValueError("%s: %s is empty" % (op, name))
    if not np.isfinite(a).all():
        raise ValueError("%s: %s contains NaN or infinity (%d of %d values)"
                         % (op, name, int((~np.isfinite(a)).sum()), a.size))
    return a


def _broadcast(op, **fields):
    try:
        arrs = np.broadcast_arrays(*fields.values())
    except ValueError:
        raise ValueError("%s: %s do not broadcast (shapes %s)"
                         % (op, " / ".join(fields), [np.shape(v) for v in fields.values()])) from None
    return [np.array(a, dtype=np.float64) for a in arrs]


def _size(n, op, name="size"):
    if isinstance(n, bool) or not isinstance(n, (int, np.integer)):
        raise ValueError("%s: %s must be an integer, got %r" % (op, name, n))
    n = int(n)
    if not 9 <= n <= 4097:
        raise ValueError("%s: %s = %d is out of range [9, 4097]" % (op, name, n))
    return n


# 物理的にあり得る桁(単位の取り違えを拒否するための窓)。
_THICK = (1e-7, 1.0)          # 0.1 µm .. 1 m
_LAMBDA_M = (1e-8, 2e-5)      # 10 nm .. 20 µm
_LAMBDA_NM = (10.0, 2e4)
_C_ABS = (1e-15, 1e-8)        # 応力光学係数 [Pa⁻¹](ガラス ~1e-12、樹脂 ~1e-11)
_PI_ABS = (1e-15, 1e-9)       # 圧電光学係数 [Pa⁻¹]


def _thickness(t, op):
    return _scalar(t, "thickness_m", op, lo=_THICK[0], hi=_THICK[1], lo_open=False,
                   hint=" — thickness is in metres (6 mm = 0.006)")


def _wavelength_m(w, op):
    return _scalar(w, "wavelength_m", op, lo=_LAMBDA_M[0], hi=_LAMBDA_M[1], lo_open=False,
                   hint=" — wavelength is in metres (550 nm = 5.5e-7)")


# --------------------------------------------------------------------------- #
# 1. 応力場の閉形式
# --------------------------------------------------------------------------- #


def _grid(size, half, op):
    n = _size(size, op)
    px = 2.0 * half / (n - 1)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    x = (xx - (n - 1) / 2.0) * px
    y = ((n - 1) / 2.0 - yy) * px
    return x, y, px


def brazilian_disc_stress(radius_m=0.025, thickness_m=0.006, load_n=500.0, size=129, x=None, y=None):
    """直径方向に圧縮された円板(Brazilian disc)の平面応力 σx, σy, τxy の閉形式 → dict。

    Diametrically compressed disc, point loads ``load_n`` [N] at ``(0, ±R)``
    acting along the y axis, plane stress (Hondros / Frocht)::

        r1² = x² + (R−y)²,  r2² = x² + (R+y)²,  k = 2P/(π t)
        σx  = −k [ x²(R−y)/r1⁴ + x²(R+y)/r2⁴ − 1/(2R) ]
        σy  = −k [ (R−y)³/r1⁴ + (R+y)³/r2⁴ − 1/(2R) ]
        τxy =  k [ x(R−y)²/r1⁴ − x(R+y)²/r2⁴ ]

    Stresses are in Pa (tension positive). At the centre σx = 2P/(πDt) and
    σy = −6P/(πDt). The free rim carries no traction except at the two load
    points, where the point-load solution is singular.

    Parameters
    ----------
    radius_m, thickness_m : disc radius and thickness [m].
    load_n : the compressive load P [N] (positive = compression).
    size : grid size (odd puts the centre on a pixel) when ``x``/``y`` are not given.
    x, y : optional evaluation points [m] (arrays that broadcast). Points
        outside the disc or exactly on a load point are refused.

    Returns
    -------
    dict with ``sxx``, ``syy``, ``txy`` [Pa], ``x``, ``y`` [m], ``inside``
    (bool; on the grid, the rim pixel ring and the pixels next to the load
    points are False and their stresses are 0 — the point-load singularity is
    not a measurement), ``pixel_m`` (grid spacing, or 0 for explicit points).

    **Raises** ``ValueError``: non-finite or non-positive radius / thickness /
    load, a thickness that looks like millimetres, only one of ``x``/``y``,
    points outside the disc or on a load point.
    """
    op = "brazilian_disc_stress"
    r = _scalar(radius_m, "radius_m", op, lo=1e-6, hi=10.0, hint=" — radius is in metres")
    t = _thickness(thickness_m, op)
    p = _scalar(load_n, "load_n", op, lo=0.0)
    if (x is None) != (y is None):
        raise ValueError("%s: give both x and y, or neither" % op)
    if x is None:
        xs, ys, px = _grid(size, r, op)
        rho = np.hypot(xs, ys)
        d1 = np.hypot(xs, r - ys)
        d2 = np.hypot(xs, r + ys)
        inside = (rho < r - 0.5 * px) & (d1 > 1.5 * px) & (d2 > 1.5 * px)
    else:
        xs, ys = _broadcast(op, x=_field(x, "x", op), y=_field(y, "y", op))
        rho = np.hypot(xs, ys)
        if (rho > r * (1.0 + 1e-12)).any():
            raise ValueError("%s: %d point(s) lie outside the disc (max radius %.6g m > R = %.6g m)"
                             % (op, int((rho > r * (1 + 1e-12)).sum()), float(rho.max()), r))
        d1 = np.hypot(xs, r - ys)
        d2 = np.hypot(xs, r + ys)
        if (np.minimum(d1, d2) <= 1e-12 * r).any():
            raise ValueError("%s: a point coincides with a load point (0, ±R) — the point-load "
                             "solution is singular there" % op)
        inside = np.ones(xs.shape, dtype=bool)
        px = 0.0
    k = 2.0 * p / (math.pi * t)
    safe = np.where(inside, 1.0, 0.0)
    r1sq = np.where(inside, xs ** 2 + (r - ys) ** 2, 1.0)
    r2sq = np.where(inside, xs ** 2 + (r + ys) ** 2, 1.0)
    sxx = -k * (xs ** 2 * (r - ys) / r1sq ** 2 + xs ** 2 * (r + ys) / r2sq ** 2 - 1.0 / (2.0 * r))
    syy = -k * ((r - ys) ** 3 / r1sq ** 2 + (r + ys) ** 3 / r2sq ** 2 - 1.0 / (2.0 * r))
    txy = k * (xs * (r - ys) ** 2 / r1sq ** 2 - xs * (r + ys) ** 2 / r2sq ** 2)
    return {"sxx": sxx * safe, "syy": syy * safe, "txy": txy * safe, "x": xs, "y": ys,
            "inside": inside, "pixel_m": float(px),
            "centre_sxx": 2.0 * p / (math.pi * 2.0 * r * t),
            "centre_syy": -6.0 * p / (math.pi * 2.0 * r * t)}


def kirsch_plate_stress(hole_radius_m=0.005, remote_stress_pa=1.0e6, load_angle_deg=0.0,
                        half_width_m=0.02, size=129, x=None, y=None):
    """穴のある無限板の一軸引張(Kirsch の解)の σx, σy, τxy と極座標成分の閉形式 → dict。

    Infinite plate with a circular hole of radius ``a`` under a remote uniaxial
    stress ``S`` along the direction ``load_angle_deg`` (Kirsch 1898). With
    ``θ`` measured from the load direction::

        σrr = S/2 (1 − a²/r²) + S/2 (1 − 4a²/r² + 3a⁴/r⁴) cos 2θ
        σθθ = S/2 (1 + a²/r²) − S/2 (1 + 3a⁴/r⁴) cos 2θ
        τrθ = −S/2 (1 + 2a²/r² − 3a⁴/r⁴) sin 2θ

    Hole edge: σrr = τrθ = 0 and σθθ = S(1 − 2 cos 2θ) — 3S at θ = 90°, −S at
    θ = 0°. Far away the field tends to the uniform uniaxial stress.

    Returns a dict with ``sxx``, ``syy``, ``txy``, ``srr``, ``stt``, ``trt`` [Pa]
    (``θ`` of the polar components is measured from the x axis), ``x``, ``y``,
    ``inside`` (False inside the hole on the grid, stresses 0 there),
    ``pixel_m``, and ``stress_concentration`` = 3.0 (max σθθ/S on the edge).

    **Raises** ``ValueError``: non-finite or non-positive radius / half width,
    a non-finite stress or angle, a hole that does not fit the grid, only one of
    ``x``/``y``, or explicit points inside the hole.
    """
    op = "kirsch_plate_stress"
    a = _scalar(hole_radius_m, "hole_radius_m", op, lo=1e-7, hi=10.0, hint=" — radius is in metres")
    s = _scalar(remote_stress_pa, "remote_stress_pa", op)
    ang = math.radians(_scalar(load_angle_deg, "load_angle_deg", op))
    if (x is None) != (y is None):
        raise ValueError("%s: give both x and y, or neither" % op)
    if x is None:
        hw = _scalar(half_width_m, "half_width_m", op, lo=0.0)
        if hw <= 1.5 * a:
            raise ValueError("%s: half_width_m = %g must exceed 1.5 x hole_radius_m = %g"
                             % (op, hw, 1.5 * a))
        xs, ys, px = _grid(size, hw, op)
        inside = np.hypot(xs, ys) >= a
    else:
        xs, ys = _broadcast(op, x=_field(x, "x", op), y=_field(y, "y", op))
        rr = np.hypot(xs, ys)
        if (rr < a * (1.0 - 1e-12)).any():
            raise ValueError("%s: %d point(s) lie inside the hole (r < a = %.6g m)"
                             % (op, int((rr < a * (1 - 1e-12)).sum()), a))
        inside = np.ones(xs.shape, dtype=bool)
        px = 0.0
    r = np.where(inside, np.hypot(xs, ys), a)
    phi = np.arctan2(ys, xs)                 # x 軸からの極角
    th = phi - ang                           # 荷重方向からの角
    q2 = (a / r) ** 2
    q4 = q2 * q2
    c2, s2 = np.cos(2 * th), np.sin(2 * th)
    srr = 0.5 * s * (1 - q2) + 0.5 * s * (1 - 4 * q2 + 3 * q4) * c2
    stt = 0.5 * s * (1 + q2) - 0.5 * s * (1 + 3 * q4) * c2
    trt = -0.5 * s * (1 + 2 * q2 - 3 * q4) * s2
    c, sn = np.cos(phi), np.sin(phi)
    sxx = srr * c * c + stt * sn * sn - 2 * trt * sn * c
    syy = srr * sn * sn + stt * c * c + 2 * trt * sn * c
    txy = (srr - stt) * sn * c + trt * (c * c - sn * sn)
    m = inside.astype(np.float64)
    return {"sxx": sxx * m, "syy": syy * m, "txy": txy * m,
            "srr": srr * m, "stt": stt * m, "trt": trt * m,
            "x": xs, "y": ys, "inside": inside, "pixel_m": float(px),
            "stress_concentration": 3.0}


def principal_stress(sxx, syy, txy):
    """平面応力の主応力 σ1 ≥ σ2、主応力差、σ1 の向き(等傾角)→ dict。

    ``σ1,2 = (σx+σy)/2 ± √(((σx−σy)/2)² + τxy²)``, ``difference = σ1 − σ2 ≥ 0``,
    ``angle_deg = ½·atan2(2τxy, σx−σy)`` in degrees, the direction of σ1 from
    the x axis (counter-clockwise, y up), in (−90, 90]. ``isotropic`` marks
    points where σ1 = σ2 (to 1e-12 of the local stress scale): the direction is
    undefined there and ``angle_deg`` is reported as 0.

    **Raises** ``ValueError``: empty, complex, non-finite or non-broadcasting inputs.
    """
    op = "principal_stress"
    sx, sy, t = _broadcast(op, sxx=_field(sxx, "sxx", op), syy=_field(syy, "syy", op),
                           txy=_field(txy, "txy", op))
    mean = 0.5 * (sx + sy)
    rad = np.hypot(0.5 * (sx - sy), t)
    scale = np.maximum.reduce([np.abs(sx), np.abs(sy), np.abs(t)])
    iso = rad <= 1e-12 * np.where(scale > 0, scale, 1.0)
    ang = np.degrees(0.5 * np.arctan2(2.0 * t, sx - sy))
    ang = np.where(ang <= -90.0, ang + 180.0, ang)
    ang = np.where(iso, 0.0, ang)
    return {"s1": mean + rad, "s2": mean - rad, "difference": 2.0 * rad,
            "max_shear": rad, "angle_deg": ang, "isotropic": iso}


# --------------------------------------------------------------------------- #
# 2. 応力光学則
# --------------------------------------------------------------------------- #


def retardation_from_birefringence(delta_n, thickness_m, wavelength_m):
    """複屈折 Δn から位相差 → dict(rad・nm・縞次数を並べて返す)。

    ``retardation = t·Δn`` [m], ``delta_rad = 2π t Δn / λ``,
    ``fringe_order = t Δn / λ``. All three are returned so that the unit is
    never implicit.

    **Raises** ``ValueError``: a non-finite/empty Δn, |Δn| > 0.1 (no
    stress-induced birefringence is that large — usually a unit slip), a
    thickness outside [1e-7, 1] m (6 mm passed as 6) or a wavelength outside
    [1e-8, 2e-5] m (550 nm passed as 550).
    """
    op = "retardation_from_birefringence"
    dn = _field(delta_n, "delta_n", op)
    if np.abs(dn).max() > 0.1:
        raise ValueError("%s: |delta_n| up to %g — stress birefringence is < 0.1; is this "
                         "a retardation or a stress instead of a refractive-index difference?"
                         % (op, float(np.abs(dn).max())))
    t = _thickness(thickness_m, op)
    lam = _wavelength_m(wavelength_m, op)
    ret = t * dn
    return {"delta_rad": 2.0 * math.pi * ret / lam, "retardation_nm": ret * 1e9,
            "fringe_order": ret / lam, "wavelength_nm": lam * 1e9}


def photoelastic_retardation(stress_difference_pa, thickness_m, stress_optic_coefficient, wavelength_m):
    """等方材料の応力光学則 δ = 2π t C (σ1−σ2)/λ → dict(rad・nm・縞次数・材料縞値)。

    ``stress_optic_coefficient`` C is in Pa⁻¹ (1 brewster = 1e-12 Pa⁻¹); the
    birefringence is ``Δn = C (σ1 − σ2)`` and the material fringe value
    ``f_σ = λ/C`` [N/m per fringe], so ``N = t (σ1 − σ2) / f_σ``.
    Sign: ``Δn = n_σ1 − n_σ2``, so for C > 0 the σ1 direction
    (:func:`principal_stress` ``angle_deg``) is the **slow** axis. The retarder
    angle of ``optics.mueller_element`` and :func:`photoelastic_polarization_images`
    is the **fast** axis (``exp(−iωt)``, the fast axis leads), so pass
    ``axis_deg = angle_deg + 90`` together with this ``delta_rad`` — for either
    sign of C (equivalently ``−delta_rad`` with ``angle_deg``).

    Returns ``delta_rad``, ``retardation_nm``, ``fringe_order``,
    ``birefringence`` and ``fringe_value_n_per_m``.

    **Raises** ``ValueError``: a non-finite/empty stress, |C| outside
    [1e-15, 1e-8] Pa⁻¹ (a value in brewster or in MPa⁻¹ passed as Pa⁻¹), and
    the thickness / wavelength checks of :func:`retardation_from_birefringence`.
    """
    op = "photoelastic_retardation"
    ds = _field(stress_difference_pa, "stress_difference_pa", op)
    c = _scalar(stress_optic_coefficient, "stress_optic_coefficient", op)
    if not _C_ABS[0] <= abs(c) <= _C_ABS[1]:
        raise ValueError("%s: |stress_optic_coefficient| = %g Pa^-1 is outside [%g, %g] — "
                         "C is in Pa^-1 (1 brewster = 1e-12 Pa^-1)" % (op, abs(c), _C_ABS[0], _C_ABS[1]))
    lam = _wavelength_m(wavelength_m, op)
    out = retardation_from_birefringence(c * ds, thickness_m, lam)
    out["birefringence"] = c * ds
    out["fringe_value_n_per_m"] = lam / c
    return out


_RET_UNITS = ("rad", "deg", "nm", "waves")


def retardation_convert(value, from_unit="rad", to_unit="nm", wavelength_nm=550.0):
    """位相差の単位換算(rad / deg / nm / waves = 縞次数)。

    ``2π rad = 360 deg = λ nm = 1 wave``. The wavelength is in **nanometres**
    here (the name says so) and must lie in [10, 20000] nm.

    **Raises** ``ValueError``: an unknown unit, an empty/non-finite value, or a
    wavelength outside [10, 20000] nm (a value in metres is refused).
    """
    op = "retardation_convert"
    for u, nm in ((from_unit, "from_unit"), (to_unit, "to_unit")):
        if u not in _RET_UNITS:
            raise ValueError("%s: %s must be one of %s, got %r" % (op, nm, "/".join(_RET_UNITS), u))
    v = _field(value, "value", op)
    lam = _scalar(wavelength_nm, "wavelength_nm", op, lo=_LAMBDA_NM[0], hi=_LAMBDA_NM[1],
                  lo_open=False, hint=" — wavelength_nm is in nanometres (550, not 5.5e-7)")
    per_wave = {"rad": 2.0 * math.pi, "deg": 360.0, "nm": lam, "waves": 1.0}
    out = v * (per_wave[to_unit] / per_wave[from_unit])
    return out if np.ndim(value) else float(out)


# --------------------------------------------------------------------------- #
# 立方晶 {100} 面(Si など)
# --------------------------------------------------------------------------- #

#: Stoehr, Gerlach, Härtling & Schoenfelder, "Analysis of photoelastic properties
#: of monocrystalline silicon", J. Sens. Sens. Syst. 9, 209–217 (2020),
#: https://doi.org/10.5194/jsss-9-209-2020 (CC BY 4.0) の Table 1。表の単位は
#: ×10⁻⁷ MPa⁻¹ = ×10⁻¹³ Pa⁻¹。``stoehr2020`` は同論文の測定値(近赤外の
#: グレイフィールド偏光計 + Brazilian disc + FEM)。他の 4 行は**同論文の表が引用した値**で、
#: 原論文は照合していない(符号の違いは各論文の定義による、と同論文が述べる)。
_SI_TABLE = {
    "stoehr2020": (14.4e-13, 9.4e-13, "Stoehr et al. 2020, JSSS 9:209, Table 1 (this work)"),
    "he2004": (9.9e-13, 6.5e-13, "He, Zheng & Danyluk 2004, as quoted in Stoehr et al. 2020 Table 1"),
    "liang1992": (-12.2e-13, 6.5e-13, "Liang et al. 1992, as quoted in Stoehr et al. 2020 Table 1"),
    "zheng_danyluk2002": (-12.2e-13, -6.5e-13,
                          "Zheng & Danyluk 2002, as quoted in Stoehr et al. 2020 Table 1"),
    "giardini1958": (-14.4e-13, -5.0e-13, "Giardini 1958, as quoted in Stoehr et al. 2020 Table 1"),
}


def silicon_piezo_optic_coefficients(source="stoehr2020"):
    """単結晶シリコンの圧電光学係数 π11−π12・π44 [Pa⁻¹] を出典つきで返す → dict。

    Values are from Table 1 of Stoehr et al., J. Sens. Sens. Syst. 9, 209 (2020),
    doi:10.5194/jsss-9-209-2020 (``×10⁻⁷ MPa⁻¹`` converted to Pa⁻¹).
    ``source="stoehr2020"`` is that paper's own measurement; ``he2004``,
    ``liang1992``, ``zheng_danyluk2002`` and ``giardini1958`` are the values
    **as that table quotes them** (the original papers were not re-checked).
    ``source="all"`` returns every row. The refractive index is *not* included:
    pass the value for your wavelength to :func:`cubic_photoelastic_birefringence`.

    **Raises** ``ValueError``: an unknown source.
    """
    op = "silicon_piezo_optic_coefficients"
    if source == "all":
        return {k: silicon_piezo_optic_coefficients(k) for k in _SI_TABLE}
    if not isinstance(source, str) or source not in _SI_TABLE:
        raise ValueError("%s: source must be one of %s or 'all', got %r"
                         % (op, "/".join(_SI_TABLE), source))
    d, p44, ref = _SI_TABLE[source]
    return {"pi11_minus_pi12": d, "pi44": p44, "unit": "Pa^-1", "source": ref,
            "doi": "10.5194/jsss-9-209-2020", "anisotropy": p44 / d}


def _cubic_tensor(d, p44):
    """立方晶の π_ijkl(結晶軸)。π11 + π12 は面内の位相差に効かないので π12 = 0, π11 = d と置く。"""
    pi = np.zeros((3, 3, 3, 3))
    for i in range(3):
        pi[i, i, i, i] = d
    for i in range(3):
        for j in range(3):
            if i != j:
                pi[i, j, i, j] = pi[i, j, j, i] = 0.5 * p44
    return pi


def cubic_photoelastic_birefringence(sxx, syy, txy, pi11_minus_pi12, pi44, refractive_index,
                                     crystal_angle_deg=0.0):
    """立方晶 {100} 面(Si ウェハなど)の応力複屈折 Δn と遅相軸 → dict。

    Light travels along the [100] normal of a {100} plate. ``crystal_angle_deg``
    φ is the angle between the [010] direction and the x axis (Stoehr et al.
    2020, Eq. 19). The 4th-order piezo-optic tensor of the cubic crystal is
    rotated, ``π'_ijkl = R_im R_jn R_ko R_lp π_mnop``, the impermeability change
    is ``ΔB_ij = π'_ijkl σ_kl`` and the in-plane birefringence is
    ``Δn = (n³/2)(ΔB_II − ΔB_I)`` — which reproduces Eq. (26) of that paper::

        Δn = (n³/4) √( 2((π11−π12)² + π44²)(4τ² + (σx−σy)²)
                       + 2((π11−π12)² − π44²)[((σx−σy)² − 4τ²) cos 4φ
                                              + 4τ(σx−σy) sin 4φ] )

    With ``π44 = π11 − π12`` the material is photoelastically isotropic and
    ``Δn = (n³/2)|π11 − π12|(σ1 − σ2)``. In the sign of
    :func:`photoelastic_retardation` (``n_σ1 − n_σ2 = C(σ1 − σ2)``; a change of
    impermeability ``ΔB`` changes the index by ``−(n³/2)ΔB``) that is
    ``C = −n³(π11−π12)/2``, returned as ``isotropic_coefficient``: π11 − π12 > 0
    makes σ1 the fast axis, and the value can be passed to
    :func:`photoelastic_retardation` as it is.

    Coefficients are in Pa⁻¹ (:func:`silicon_piezo_optic_coefficients`).
    Returns ``delta_n`` (≥ 0), ``slow_axis_deg`` (direction of the larger
    refractive index, (−90, 90]; 0 where Δn = 0 to 1e-12 of that pixel's own
    stress scale — the fast axis that ``optics.mueller_element`` and
    :func:`photoelastic_polarization_images` take is ``slow_axis_deg + 90``),
    ``effective_coefficient`` (|Δn|/(σ1−σ2) ≥ 0 [Pa⁻¹], 0 where σ1 = σ2),
    ``isotropic_coefficient`` (signed, as above) and ``isotropic`` (σ1 = σ2).

    **Raises** ``ValueError``: non-finite / empty / non-broadcasting stresses,
    |π| outside [1e-15, 1e-9] Pa⁻¹ (a table value in ×10⁻⁷ MPa⁻¹ or in MPa⁻¹
    passed as Pa⁻¹), or a refractive index outside [1, 10].
    """
    op = "cubic_photoelastic_birefringence"
    sx, sy, t = _broadcast(op, sxx=_field(sxx, "sxx", op), syy=_field(syy, "syy", op),
                           txy=_field(txy, "txy", op))
    d = _scalar(pi11_minus_pi12, "pi11_minus_pi12", op)
    p44 = _scalar(pi44, "pi44", op)
    for nm, v in (("pi11_minus_pi12", d), ("pi44", p44)):
        if not _PI_ABS[0] <= abs(v) <= _PI_ABS[1]:
            raise ValueError("%s: |%s| = %g is outside [%g, %g] Pa^-1 — piezo-optic "
                             "coefficients are ~1e-12 Pa^-1 (14.4e-7 MPa^-1 = 1.44e-12 Pa^-1)"
                             % (op, nm, abs(v), _PI_ABS[0], _PI_ABS[1]))
    n0 = _scalar(refractive_index, "refractive_index", op, lo=1.0, hi=10.0, lo_open=False)
    phi = math.radians(_scalar(crystal_angle_deg, "crystal_angle_deg", op))
    c, s = math.cos(phi), math.sin(phi)
    rot = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    pr = np.einsum("im,jn,ko,lp,mnop->ijkl", rot, rot, rot, rot, _cubic_tensor(d, p44))
    sig = {(0, 0): sx, (1, 1): sy, (0, 1): t, (1, 0): t}
    db = {}
    for i, j in ((0, 0), (1, 1), (0, 1)):
        db[(i, j)] = sum(pr[i, j, k, l] * sig[(k, l)] for (k, l) in sig)
    half = 0.5 * (db[(0, 0)] - db[(1, 1)])
    rad = np.hypot(half, db[(0, 1)])
    dn = n0 ** 3 * rad                                   # (n³/2)(ΔB_II − ΔB_I), ΔB_II − ΔB_I = 2·rad
    # 大きい屈折率 = 小さい ΔB の固有ベクトル。最大固有値の向きは ½atan2(2ΔB12, ΔB11−ΔB22)。
    ang_max = 0.5 * np.arctan2(2.0 * db[(0, 1)], db[(0, 0)] - db[(1, 1)])
    slow = np.degrees(ang_max) + 90.0
    slow = np.where(slow > 90.0, slow - 180.0, slow)
    # ゼロの判定は画素ごと: その画素の応力の桁 × 係数の桁が丸めの床の基準
    # (配列全体の最大で割ると、大きな画素の隣の小さいが確かな Δn が 0 に化ける)。
    scale = n0 ** 3 * max(abs(d), abs(p44)) * np.maximum.reduce([np.abs(sx), np.abs(sy), np.abs(t)])
    zero = dn <= 1e-12 * scale
    slow = np.where(zero, 0.0, slow)
    ps = principal_stress(sx, sy, t)
    eff = np.divide(dn, ps["difference"], out=np.zeros_like(dn), where=~ps["isotropic"])
    return {"delta_n": dn, "slow_axis_deg": slow, "effective_coefficient": eff,
            "isotropic": ps["isotropic"], "isotropic_coefficient": -0.5 * n0 ** 3 * d}


# --------------------------------------------------------------------------- #
# 3. 偏光器の縞と偏光像
# --------------------------------------------------------------------------- #

_SETUPS = ("circular_dark", "circular_bright", "plane_dark", "plane_bright")


def _delta(delta_rad, op):
    d = _field(delta_rad, "delta_rad", op)
    if np.abs(d).max() > 2.0 * math.pi * 200.0:
        raise ValueError("%s: |delta_rad| up to %g rad = %.0f fringes — that is not an image a "
                         "polariscope can resolve; is this a retardation in nm? convert with "
                         "retardation_convert(..., 'nm', 'rad', wavelength_nm)"
                         % (op, float(np.abs(d).max()), float(np.abs(d).max()) / (2 * math.pi)))
    return d


def polariscope_intensity(delta_rad, axis_deg=45.0, setup="plane_dark", polarizer_deg=0.0, intensity=1.0):
    """平面・円偏光器の明暗視野の強度(等色線・等傾線)の閉形式。

    ``intensity`` is the intensity of the polarised beam leaving the first
    polariser. With retardance δ and principal (isoclinic) direction θ:

    * ``circular_dark``  ``I sin²(δ/2)``  — isochromatics only (dark at N = 0, 1, 2 …)
    * ``circular_bright`` ``I cos²(δ/2)``  — dark at N = ½, 3/2 …
    * ``plane_dark`` (crossed, polariser at β) ``I sin²(2(θ−β)) sin²(δ/2)`` —
      isochromatics × isoclinics (dark where θ = β or β+90°)
    * ``plane_bright`` (parallel) ``I [1 − sin²(2(θ−β)) sin²(δ/2)]``

    The default is the crossed plane polariscope (the basic setup, where both
    the axis and the polariser angle matter); when only δ is given the
    principal axes are taken at 45 deg to the polariser, where the plane
    polariscope shows the isochromatics at full contrast (at 0 deg the field is
    dark everywhere — that is an isoclinic, not "no stress"). These equal the Mueller chain
    built from ``optics.mueller_element`` (the tests compare them). Returns an
    array of the broadcast shape.

    **Raises** ``ValueError``: an unknown setup, non-finite inputs, a negative
    intensity, or |δ| beyond 200 fringes (a retardation in nm passed as rad).
    """
    op = "polariscope_intensity"
    if setup not in _SETUPS:
        raise ValueError("%s: setup must be one of %s, got %r" % (op, "/".join(_SETUPS), setup))
    d, th = _broadcast(op, delta_rad=_delta(delta_rad, op), axis_deg=_field(axis_deg, "axis_deg", op))
    beta = _scalar(polarizer_deg, "polarizer_deg", op)
    i0 = _scalar(intensity, "intensity", op, lo=0.0, lo_open=False)
    h = np.sin(0.5 * d) ** 2
    if setup == "circular_dark":
        out = h
    elif setup == "circular_bright":
        out = 1.0 - h
    else:
        iso = np.sin(2.0 * np.radians(th - beta)) ** 2
        out = iso * h if setup == "plane_dark" else 1.0 - iso * h
    return i0 * out


def _retarder_field(d, th_rad):
    """画素ごとの位相子 Mueller 行列 (..., 4, 4)(``optics.mueller_element('retarder')`` と同じ規約)。"""
    c2, s2 = np.cos(2 * th_rad), np.sin(2 * th_rad)
    cd, sd = np.cos(d), np.sin(d)
    m = np.zeros(d.shape + (4, 4))
    m[..., 0, 0] = 1.0
    m[..., 1, 1] = c2 * c2 + s2 * s2 * cd
    m[..., 1, 2] = m[..., 2, 1] = c2 * s2 * (1.0 - cd)
    m[..., 1, 3] = -s2 * sd
    m[..., 2, 2] = s2 * s2 + c2 * c2 * cd
    m[..., 2, 3] = c2 * sd
    m[..., 3, 1] = s2 * sd
    m[..., 3, 2] = -c2 * sd
    m[..., 3, 3] = cd
    return m


_ANALYZERS = {"camera4": (0.0, 45.0, 90.0, 135.0),
              "stokes6": (0.0, 45.0, 90.0, 135.0, "right", "left")}


def photoelastic_polarization_images(delta_rad, axis_deg=0.0, analyzers="camera4", intensity=1.0):
    """円偏光照明の試料を偏光カメラ(0/45/90/135 度)または 6 強度の偏光計で撮った像 → (K, H, W)。

    The specimen (retardance δ, **fast** axis θ) is lit with right-circular light
    ``S = I(1, 0, 0, 1)``; the emerging Stokes vector is computed with a
    per-pixel Mueller retarder (same convention as ``optics.mueller_element``,
    whose angle is the fast axis — for a stress field pass ``angle_deg + 90``,
    see :func:`photoelastic_retardation`),
    ``S' = I(1, −sin2θ sinδ, cos2θ sinδ, cosδ)``. Each analyser transmits
    ``½(S0 + S1 cos2α + S2 sin2α)`` (linear at α) or ``½(S0 ± S3)`` (right /
    left circular).

    ``analyzers="camera4"`` returns the 4 frames of a division-of-focal-plane
    camera (0, 45, 90, 135 deg — the order ``optics.polarization_demosaic``
    returns); ``"stokes6"`` adds the right- and left-circular frames.
    The left-circular frame equals :func:`polariscope_intensity` with
    ``setup="circular_dark"``.

    **Raises** ``ValueError``: an unknown analyser set, non-2-D or non-finite
    inputs, a negative intensity, or |δ| beyond 200 fringes.
    """
    op = "photoelastic_polarization_images"
    if analyzers not in _ANALYZERS:
        raise ValueError("%s: analyzers must be one of %s, got %r"
                         % (op, "/".join(_ANALYZERS), analyzers))
    d, th = _broadcast(op, delta_rad=_delta(delta_rad, op), axis_deg=_field(axis_deg, "axis_deg", op))
    if d.ndim != 2:
        raise ValueError("%s: delta_rad / axis_deg must broadcast to a 2-D image, got shape %r"
                         % (op, d.shape))
    i0 = _scalar(intensity, "intensity", op, lo=0.0, lo_open=False)
    s_out = np.einsum("...ij,j->...i", _retarder_field(d, np.radians(th)),
                      np.array([1.0, 0.0, 0.0, 1.0])) * i0
    frames = []
    for a in _ANALYZERS[analyzers]:
        if a == "right":
            frames.append(0.5 * (s_out[..., 0] + s_out[..., 3]))
        elif a == "left":
            frames.append(0.5 * (s_out[..., 0] - s_out[..., 3]))
        else:
            r = math.radians(a)
            frames.append(0.5 * (s_out[..., 0] + s_out[..., 1] * math.cos(2 * r)
                                 + s_out[..., 2] * math.sin(2 * r)))
    return np.clip(np.stack(frames), 0.0, None)


def photoelastic_phase_estimate(images, analyzers="camera4", min_modulation=0.01, sum_tolerance=0.05):
    """偏光像から位相差 δ と主軸 θ を閉形式で逆算 → dict。

    Inverse of :func:`photoelastic_polarization_images` (right-circular
    illumination). With ``S0 = ½(I0 + I90 + I45 + I135)`` (the mean of the two
    pair sums), ``S1 = I0 − I90``, ``S2 = I45 − I135``:

    * ``camera4`` (4 linear analysers): ``sin δ = √(S1² + S2²)/S0`` and
      ``δ = arcsin(·)`` — **unique only for δ ∈ [0, π/2]** (a quarter wave):
      linear analysers alone cannot see the sign of ``cos δ``.
    * ``stokes6`` (+ right/left circular): ``S3 = IR − IL`` and
      ``δ = atan2(√(S1² + S2²), S3)`` ∈ [0, π].

    In both, ``θ = ½ atan2(−S1, S2)`` mod 180 deg, in (−90, 90] — the fast axis
    (for a material with C > 0, σ1 lies at θ + 90°). The pair
    ``(δ, θ)`` and ``(−δ, θ + 90°)`` give identical images; the estimate
    returns the representative with δ ≥ 0. Where the modulation
    ``√(S1²+S2²)/S0`` (= |sin δ|) is at or below ``min_modulation`` (default
    0.01, i.e. δ within ~0.01 rad of 0 or π, where 1 % intensity noise already
    turns the axis by tens of degrees) the axis is undefined: ``axis_valid`` is
    False and ``axis_deg`` is 0 there.

    One exposure obeys ``I0 + I90 = I45 + I135`` (and ``= IR + IL``). Real frames
    do so only to the noise and the demosaic interpolation, so the check is per
    pixel and relative: ``sum_mismatch = |I45 + I135 − (I0 + I90)| / S0`` (for
    stokes6 the larger of that and ``|IR + IL − S0| / S0``).

    Parameters
    ----------
    images : ``(K, H, W)`` array or list of K frames in the order of ``analyzers``.
    analyzers : ``"camera4"`` (0/45/90/135) or ``"stokes6"`` (+ right/left circular).
    min_modulation : modulation at or below which the axis is not reported.
    sum_tolerance : largest ``sum_mismatch`` a pixel may have and stay ``valid``
        (relative to S0, default 0.05). Measured basis: with 1 % independent
        noise per frame the mismatch stays below it (99th percentile 2.9 %,
        maximum 4.6 % over 40 000 pixels), and the bilinear interpolation of
        ``optics.polarization_demosaic`` leaves ≤ 1.5 % on 95 % of a disc with
        nine resolved fringes; pixels above it are aliased fringes, saturated
        or moving pixels, or frames from another exposure. Must lie in [0, 1].

    Returns ``delta_rad``, ``axis_deg``, ``axis_valid``, ``valid`` (``sum_mismatch``
    ≤ ``sum_tolerance``; ``delta_rad`` is still computed where it is False but is
    not a measurement there, and ``axis_valid`` is False), ``sum_mismatch``,
    ``modulation``, ``intensity`` (S0) and ``stokes`` (``(4, H, W)``; S3 = 0 for
    camera4, which is a limitation, not a measurement).

    **Raises** ``ValueError``: wrong number of frames, non-2-D / non-finite /
    negative frames, a dark pixel (S0 = 0), ``sum_tolerance`` outside [0, 1], or
    frames whose pair sums disagree by more than ``sum_tolerance`` on more than
    half of the pixels (not one camera exposure, the wrong frame order, or
    fringes too dense for the sensor).
    """
    op = "photoelastic_phase_estimate"
    if analyzers not in _ANALYZERS:
        raise ValueError("%s: analyzers must be one of %s, got %r"
                         % (op, "/".join(_ANALYZERS), analyzers))
    k = len(_ANALYZERS[analyzers])
    if isinstance(images, (list, tuple)):
        if len(images) == 0:
            raise ValueError("%s: images is empty" % op)
        frames = [_field(f, "images[%d]" % i, op) for i, f in enumerate(images)]
        shapes = {f.shape for f in frames}
        if len(shapes) != 1:
            raise ValueError("%s: frames have different shapes %s" % (op, sorted(shapes)))
        st = np.stack(frames)
    else:
        st = _field(images, "images", op)
    if st.ndim != 3 or st.shape[0] != k:
        raise ValueError("%s: %s needs %d frames of shape (H, W) — got shape %r"
                         % (op, analyzers, k, st.shape))
    if (st < 0).any():
        raise ValueError("%s: %d negative intensities — frames must be radiance"
                         % (op, int((st < 0).sum())))
    mm = _scalar(min_modulation, "min_modulation", op, lo=0.0, hi=1.0, lo_open=False)
    tol = _scalar(sum_tolerance, "sum_tolerance", op, lo=0.0, hi=1.0, lo_open=False)
    i0, i45, i90, i135 = st[0], st[1], st[2], st[3]
    pa, pb = i0 + i90, i45 + i135
    s0 = 0.5 * (pa + pb)
    if (s0 <= 0).any():
        raise ValueError("%s: %d dark pixel(s) (I0 + I90 + I45 + I135 = 0) — no phase can be read there"
                         % (op, int((s0 <= 0).sum())))
    floor = tol + 1e-12                                  # 合成した厳密な像の丸め屑は許す
    mismatch = np.abs(pb - pa) / s0
    if float(np.median(mismatch)) > floor:
        raise ValueError("%s: I0 + I90 != I45 + I135 by more than sum_tolerance = %.3g on more than "
                         "half of the pixels (median %.3g relative) — the frames are not one exposure "
                         "of four linear analysers in the order 0/45/90/135 (or the fringes are too "
                         "dense for the sensor)" % (op, tol, float(np.median(mismatch))))
    s1 = i0 - i90
    s2 = i45 - i135
    lin = np.hypot(s1, s2)
    if analyzers == "camera4":
        mod = np.clip(lin / s0, 0.0, 1.0)
        delta = np.arcsin(mod)
        s3 = np.zeros_like(s0)
    else:
        ir, il = st[4], st[5]
        s3 = ir - il
        circ = np.abs((ir + il) - s0) / s0
        if float(np.median(circ)) > floor:
            raise ValueError("%s: IR + IL != I0 + I90 by more than sum_tolerance = %.3g on more than "
                             "half of the pixels (median %.3g relative) — the circular frames are not "
                             "from the same exposure" % (op, tol, float(np.median(circ))))
        mismatch = np.maximum(mismatch, circ)
        delta = np.arctan2(lin, s3)
        mod = np.clip(lin / s0, 0.0, 1.0)
    ok = mismatch <= floor
    valid = (mod > mm) & ok
    ax = np.degrees(0.5 * np.arctan2(-s1, s2))
    ax = np.where(ax <= -90.0, ax + 180.0, ax)
    ax = np.where(valid, ax, 0.0)
    return {"delta_rad": delta, "axis_deg": ax, "axis_valid": valid, "valid": ok,
            "sum_mismatch": mismatch, "modulation": mod,
            "intensity": s0, "stokes": np.stack([s0, s1, s2, s3])}


def retardation_unwrap_multiwavelength(deltas_rad, wavelengths_nm, max_retardation_nm, folded=True):
    """複数波長の巻いた位相差から絶対位相差(nm)を決める(分散なしの仮定)→ dict。

    The retardation ``R = t·Δn`` [nm] is assumed independent of wavelength
    (no dispersion of C). For each pixel, every candidate from the first
    wavelength, ``R = (k + f)λ1`` (and ``(k + 1 − f)λ1`` when ``folded``,
    ``f = δ1/2π``), up to ``max_retardation_nm``, is scored by how well it
    predicts the measured phase at every other wavelength (residual in nm);
    the best candidate wins.

    ``folded=True`` is for phases in [0, π] that cannot tell δ from 2π − δ
    (:func:`photoelastic_phase_estimate` with ``stokes6``); ``folded=False``
    is for phases wrapped into [0, 2π).

    Returns ``retardation_nm``, ``delta_rad`` (the unwrapped phase at the first
    wavelength), ``residual_nm`` (best score), ``margin_nm`` (second best −
    best, among candidates more than λ_min/4 away from the answer: when it is
    small another order fits almost as well — add a wavelength or reduce
    ``max_retardation_nm``) and ``valid``: False where no candidate up to
    ``max_retardation_nm`` exists for that pixel (its first-wavelength phase
    alone already needs more), and the four numbers are NaN there.

    **Raises** ``ValueError``: fewer than 2 wavelengths, mismatched counts or
    shapes, wavelengths outside [10, 20000] nm or repeated, phases outside
    [0, π] (folded) / [0, 2π) (unfolded), a range over 1000 waves, or a
    ``max_retardation_nm`` below the smallest candidate of every pixel.
    """
    op = "retardation_unwrap_multiwavelength"
    if not isinstance(deltas_rad, (list, tuple)) or len(deltas_rad) < 2:
        raise ValueError("%s: deltas_rad must be a list of >= 2 phase images" % op)
    lams = [_scalar(w, "wavelengths_nm[%d]" % i, op, lo=_LAMBDA_NM[0], hi=_LAMBDA_NM[1],
                    lo_open=False, hint=" — wavelengths are in nanometres")
            for i, w in enumerate(wavelengths_nm)] if isinstance(wavelengths_nm, (list, tuple)) else None
    if lams is None or len(lams) != len(deltas_rad):
        raise ValueError("%s: wavelengths_nm must be a list with one wavelength per phase image" % op)
    if len(set(lams)) != len(lams):
        raise ValueError("%s: wavelengths must be distinct, got %s" % (op, lams))
    ph = _broadcast(op, **{"deltas_rad[%d]" % i: _field(d, "deltas_rad[%d]" % i, op)
                           for i, d in enumerate(deltas_rad)})
    hi = math.pi if folded else 2.0 * math.pi
    for i, p in enumerate(ph):
        bad = (p < -1e-12) | (p > hi + 1e-12) if folded else (p < -1e-12) | (p >= hi)
        if bad.any():
            raise ValueError("%s: deltas_rad[%d] has %d value(s) outside [0, %s] — wrap or fold the "
                             "phase first" % (op, i, int(bad.sum()), "pi" if folded else "2pi)"))
    rmax = _scalar(max_retardation_nm, "max_retardation_nm", op, lo=0.0)
    kmax = int(math.floor(rmax / lams[0])) + 1
    if kmax > 1000:
        raise ValueError("%s: max_retardation_nm = %g spans %d waves — over 1000" % (op, rmax, kmax))
    f = ph[0] / (2.0 * math.pi)
    ks = np.arange(kmax + 1, dtype=np.float64).reshape((-1,) + (1,) * f.ndim)
    cand = (ks + f) * lams[0]
    if folded:
        cand = np.concatenate([cand, (ks + 1.0 - f) * lams[0]])
    cand = np.where(cand <= rmax * (1 + 1e-12) + 1e-9, cand, np.inf)
    has = np.isfinite(cand).any(axis=0)
    if not has.any():
        need = (np.minimum(f, 1.0 - f) if folded else f) * lams[0]
        raise ValueError("%s: no pixel has a candidate retardation up to max_retardation_nm = %g nm — "
                         "the first wavelength's phase alone needs at least %.6g nm; raise "
                         "max_retardation_nm" % (op, rmax, float(need.min())))
    cost = np.zeros(cand.shape)
    for p, lam in zip(ph[1:], lams[1:]):
        pred = np.mod(2.0 * math.pi * np.where(np.isfinite(cand), cand, 0.0) / lam, 2.0 * math.pi)
        if folded:
            pred = np.minimum(pred, 2.0 * math.pi - pred)
            res = np.abs(pred - p)
        else:
            res = np.abs(np.mod(pred - p + math.pi, 2.0 * math.pi) - math.pi)
        cost = cost + (res * lam / (2.0 * math.pi)) ** 2
    cost = np.where(np.isfinite(cand), np.sqrt(cost), np.inf)
    order = np.argsort(cost, axis=0)
    best = np.take_along_axis(cand, order[:1], axis=0)[0]
    c_best = np.take_along_axis(cost, order[:1], axis=0)[0]
    with np.errstate(invalid="ignore"):                         # 候補の無い画素の inf − inf
        if cost.shape[0] > 1:
            # 2 番目は「別の次数」に限る: 最良から λ_min/4 以内の候補は同じ答えの数え直し
            # (折り返し点 f ≈ 0, ½ の近くでは (k+f)λ と (k+1−f)λ がほぼ同じ R になる)。
            cs = np.take_along_axis(cost, order, axis=0)
            rs = np.take_along_axis(cand, order, axis=0)
            same = np.abs(rs - best) <= 0.25 * min(lams)
            cs = np.where(same, np.inf, cs)
            second = cs.min(axis=0)
        else:                                                   # pragma: no cover
            second = np.full(best.shape, np.inf)
        margin = np.where(np.isfinite(second), second - c_best, np.inf)
    best = np.where(has, best, np.nan)
    return {"retardation_nm": best, "delta_rad": 2.0 * math.pi * best / lams[0],
            "residual_nm": np.where(has, c_best, np.nan), "margin_nm": np.where(has, margin, np.nan),
            "valid": has, "wavelength_nm": lams[0]}
