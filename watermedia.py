# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""watermedia — water and other transparent media: waves, refraction, attenuation, scattering, bottles.

Seen from above, water is a moving lens; seen from below it is a colour filter whose strength grows with
distance. This module puts both on closed forms and published tables, and checks every numerical
solver against a second route (a closed form, a brute-force minimisation or a Monte Carlo count).

The ops::

    ocean_spectrum(wind_speed_mps, fetch_m, kind)      -> S(omega), Hs and Tp (Pierson-Moskowitz 1964, JONSWAP)
    ocean_height_field(size, extent_m, wind, ...)      -> a Tessendorf (2001) FFT sea: height, slopes, normals
    fresnel_water_air(theta_deg, wavelength_um, ...)   -> reflectance / transmittance / refracted angle / TIR
    snell_window(depth_m)                              -> the radius of Snell's window and the apparent depth
    refracted_view(points, eye, surface)               -> where an underwater point appears (Fermat's principle)
    water_attenuation(wavelength_um, water_type, z)    -> a, b, c, Kd and the transmittance over depth
    underwater_image(image, depth, distance, ...)      -> direct signal + backscatter (Akkaynak & Treibitz 2018)
    phase_function_hg(cos_theta, g)                    -> the Henyey-Greenstein phase function
    scattering_phase_petzold(theta_deg, kind)          -> the measured volume scattering function (Petzold 1972)
    cylinder_lens_caustic(radius_mm, n_glass, ...)     -> the focus and the real-ray caustic of a bottle

Conventions: z points up, the water surface is z = 0 (or the height field), distances are in metres
unless a name says otherwise, angles are in degrees (``_deg``), wavelengths in micrometres
(``wavelength_um``). A solver that does not converge, or an input outside the table it needs, is refused
(``ValueError``) or returned as NaN with a ``converged`` / ``valid`` flag; a wrong number is never returned
silently.

Where the model stops (stated here, shown in the PoC): the flat-interface apparent depth ``d / n`` holds only
for near-normal viewing (it overstates the depth by 52 % at 60 degrees); a wave spectrum of the Pierson-Moskowitz kind has no
capillary waves, so the slope variance of a resolved sea is a fraction of the Cox & Munk (1954) value; the
diffuse attenuation ``Kd`` is used as the attenuation along a line of sight, which is an approximation
(Akkaynak & Treibitz 2018 show it varies with range).
"""
from __future__ import annotations

import math

import numpy as np

import watermedia_data as _wd

__all__ = ["ocean_spectrum", "ocean_height_field", "fresnel_water_air", "snell_window", "refracted_view",
           "water_attenuation", "underwater_image", "phase_function_hg", "scattering_phase_petzold",
           "cylinder_lens_caustic"]

#: standard gravity (m/s^2)
G = 9.80665
#: Pierson-Moskowitz constants (Pierson & Moskowitz 1964)
PM_ALPHA = 0.0081
PM_BETA = 0.74
#: JONSWAP defaults (Hasselmann et al. 1973)
JONSWAP_GAMMA = 3.3
JONSWAP_SIGMA_A = 0.07
JONSWAP_SIGMA_B = 0.09
WAVE_KINDS = ("pierson_moskowitz", "jonswap")
DIRECTIONALS = ("cos2", "cos2s")
#: the largest FFT sea (points per side)
MAX_OCEAN_SIZE = 1024
MAX_WIND_MPS = 60.0
#: pure-water scattering (Smith & Baker 1981): b_w = 0.00288 (lambda / 500 nm)^-4.32 per metre
SB_B500 = 0.00288
SB_EXPONENT = -4.32
#: the fraction of the water scattering that is backscattering for pure water
PURE_BB_OVER_B = 0.5
WATER_TYPES = ("pure",) + tuple("jerlov_" + t for t in _wd.SOLONENKO_MOBLEY_2015)
#: the wave number (rad/m) where gravity waves give way to capillary waves (wavelength 1.7 cm, the minimum of the phase speed)
K_CAPILLARY = 370.0
#: the most points one call of the point solvers takes
MAX_POINTS = 1 << 20
MAX_IMAGE_ELEMENTS = 1 << 24


# --------------------------------------------------------------------------- validation
def _real(value, name, op, lo=None, hi=None, lo_open=False, hi_open=False):
    """A finite real scalar; strings, bools, complex numbers and masked values are refused."""
    if isinstance(value, (bool, np.bool_, str, bytes)) or value is None:
        raise ValueError("%s: %s must be a real number, got %r" % (op, name, value))
    if np.ma.isMaskedArray(value) or np.iscomplexobj(value):
        raise ValueError("%s: %s must be a real number (no masked or complex values)" % (op, name))
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a real number, got %r" % (op, name, value)) from None
    if not math.isfinite(v):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, value))
    if lo is not None and (v < lo or (lo_open and v == lo)):
        raise ValueError("%s: %s must be %s %g, got %g" % (op, name, ">" if lo_open else ">=", lo, v))
    if hi is not None and (v > hi or (hi_open and v == hi)):
        raise ValueError("%s: %s must be %s %g, got %g" % (op, name, "<" if hi_open else "<=", hi, v))
    return v


def _int(value, name, op, lo, hi):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        if isinstance(value, (float, np.floating)) and float(value).is_integer():
            value = int(value)
        else:
            raise ValueError("%s: %s must be an integer, got %r" % (op, name, value))
    value = int(value)
    if value < lo or value > hi:
        raise ValueError("%s: %s must be in [%d, %d], got %d" % (op, name, lo, hi, value))
    return value


def _array(value, name, op, ndim=None, min_size=1, lo=None, hi=None, allow_scalar=True):
    """A finite real float64 array (a scalar becomes a 0-d array when allowed)."""
    if isinstance(value, (str, bytes)) or value is None:
        raise ValueError("%s: %s must be numeric, got %r" % (op, name, value))
    if np.ma.isMaskedArray(value):
        raise ValueError("%s: %s is a masked array; fill or drop the masked entries explicitly" % (op, name))
    try:
        a = np.asarray(value)
    except Exception:
        raise ValueError("%s: %s is not array-like" % (op, name)) from None
    if np.iscomplexobj(a):
        raise ValueError("%s: %s is complex; the imaginary part would be dropped silently" % (op, name))
    if a.dtype.kind not in "iuf":
        raise ValueError("%s: %s must be numeric, got dtype %s" % (op, name, a.dtype))
    a = a.astype(np.float64)
    if a.ndim == 0 and not allow_scalar:
        raise ValueError("%s: %s must be an array, got a scalar" % (op, name))
    if ndim is not None and a.ndim != ndim:
        raise ValueError("%s: %s must be %d-D, got shape %r" % (op, name, ndim, a.shape))
    if a.size < min_size:
        raise ValueError("%s: %s is empty (needs at least %d element(s))" % (op, name, min_size))
    if not np.isfinite(a).all():
        raise ValueError("%s: %s has %d non-finite value(s) (NaN or Inf)" % (op, name, int((~np.isfinite(a)).sum())))
    if lo is not None and (a < lo).any():
        raise ValueError("%s: %s must be >= %g, minimum is %g" % (op, name, lo, a.min()))
    if hi is not None and (a > hi).any():
        raise ValueError("%s: %s must be <= %g, maximum is %g" % (op, name, hi, a.max()))
    return a


def _choice(value, name, op, allowed):
    if not isinstance(value, str) or value not in allowed:
        raise ValueError("%s: %s must be one of %s, got %r" % (op, name, list(allowed), value))
    return value


def _water_index(n_water, wavelength_um, op):
    """The real part of the refractive index of water: a given number, or the material table at the wavelength."""
    if n_water is not None:
        return _real(n_water, "n_water", op, lo=1.0, lo_open=True, hi=3.0)
    wl = _real(wavelength_um, "wavelength_um", op, lo=0.2, hi=2.5)
    import raytrace
    return float(raytrace.refractive_index("WATER", wl))


# --------------------------------------------------------------------------- 1. the wave spectrum
def _jonswap_params(U, fetch_m):
    """alpha, omega_peak, fully_developed (fully developed: Pierson-Moskowitz; with a fetch: Hasselmann 1973)."""
    if fetch_m is None:
        return PM_ALPHA, (4.0 * PM_BETA / 5.0) ** 0.25 * G / U, True
    alpha = 0.076 * (U * U / (fetch_m * G)) ** 0.22
    wp = 22.0 * (G * G / (U * fetch_m)) ** (1.0 / 3.0)
    return alpha, wp, False


def _s_of_omega(omega, U, kind, fetch_m, gamma):
    """S(omega) (m^2 s) of a unidirectional sea, with alpha and the peak parameter omega_p."""
    alpha, wp, _ = _jonswap_params(U, fetch_m if kind == "jonswap" else None)
    om = np.asarray(omega, dtype=np.float64)
    s = alpha * G * G / om ** 5 * np.exp(-1.25 * (wp / om) ** 4)
    if kind == "jonswap":
        sig = np.where(om <= wp, JONSWAP_SIGMA_A, JONSWAP_SIGMA_B)
        r = np.exp(-(om - wp) ** 2 / (2.0 * sig * sig * wp * wp))
        s = s * gamma ** r
    return s, alpha, wp


def ocean_spectrum(wind_speed_mps, fetch_m=None, kind="pierson_moskowitz", omega=None, gamma=JONSWAP_GAMMA) -> dict:
    """One-dimensional wave spectrum S(omega) of a wind sea, with its significant height and peak period -> dict.

    ``pierson_moskowitz`` (Pierson & Moskowitz 1964, a fully developed sea): ``S = alpha g^2 omega^-5
    exp(-1.25 (omega_p / omega)^4)`` with ``alpha = 0.0081`` and ``omega_p = (4 beta / 5)^(1/4) g / U = 0.877 g / U`` (``U`` is
    the wind speed at 10 m). Its zeroth moment is ``m0 = alpha U^4 / (4 beta g^2)`` so ``Hs = 4 sqrt(m0) = 0.2092 U^2 / g``
    (the rule of thumb is 0.21 U^2 / g); ``hs_closed_form_m`` is that value and ``hs_m`` the numerical integral of the
    returned spectrum. ``jonswap`` (Hasselmann et al. 1973) multiplies the same shape by the peak enhancement
    ``gamma ** exp(-(omega - omega_p)^2 / (2 sigma^2 omega_p^2))`` (``gamma = 3.3``, ``sigma = 0.07`` below the peak and
    ``0.09`` above). With ``fetch_m`` the fetch-limited ``alpha = 0.076 (U^2 / (F g))^0.22`` and ``omega_p = 22 (g^2 / (U F))^(1/3)``
    are used, without it the fully developed Pierson-Moskowitz ``alpha`` and ``omega_p``: JONSWAP with ``gamma = 1`` is then
    exactly Pierson-Moskowitz. ``omega`` is an optional increasing grid (rad/s); the default is 6000 points on a
    logarithmic grid from 0.15 to 25 times ``omega_p``. The table has ``omega``, ``S``, ``hs_m``, ``tp_s`` (2 pi / omega_p),
    ``omega_peak`` (the parameter), ``omega_peak_numeric`` (the maximum of S) and ``m0``. A negative or zero wind or fetch is
    refused; ``fetch_m`` with the fully developed kind is refused too."""
    op = "ocean_spectrum"
    U = _real(wind_speed_mps, "wind_speed_mps", op, lo=0.0, lo_open=True, hi=MAX_WIND_MPS)
    kind = _choice(kind, "kind", op, WAVE_KINDS)
    gm = _real(gamma, "gamma", op, lo=1.0, hi=20.0)
    if fetch_m is not None:
        if kind != "jonswap":
            raise ValueError("%s: fetch_m applies to the jonswap kind only (pierson_moskowitz is fully developed)" % op)
        fetch = _real(fetch_m, "fetch_m", op, lo=0.0, lo_open=True)
    else:
        fetch = None
    _, wp0, _ = _jonswap_params(U, fetch)
    if omega is None:
        om = np.geomspace(0.15 * wp0, 25.0 * wp0, 6000)
    else:
        om = _array(omega, "omega", op, ndim=1, min_size=2, lo=0.0)
        if (om <= 0.0).any() or (np.diff(om) <= 0.0).any():
            raise ValueError("%s: omega must be positive and strictly increasing" % op)
    s, alpha, wp = _s_of_omega(om, U, kind, fetch, gm)
    m0 = float(np.sum(0.5 * (s[1:] + s[:-1]) * np.diff(om)))
    from scipy.optimize import minimize_scalar
    i = int(np.argmax(s))
    lo, hi = om[max(i - 1, 0)], om[min(i + 1, om.size - 1)]
    if hi > lo:
        res = minimize_scalar(lambda w: -float(_s_of_omega(np.array([w]), U, kind, fetch, gm)[0][0]),
                              bounds=(lo, hi), method="bounded", options={"xatol": 1e-12})
        w_peak = float(res.x)
    else:
        w_peak = float(om[i])
    out = {"omega": om, "S": s, "hs_m": 4.0 * math.sqrt(m0), "tp_s": 2.0 * math.pi / wp, "omega_peak": wp,
           "omega_peak_numeric": w_peak, "m0": m0, "kind": kind, "alpha": alpha, "gamma": gm if kind == "jonswap" else 1.0,
           "fully_developed": fetch is None, "hs_rule_of_thumb_m": 0.21 * U * U / G}
    out["hs_closed_form_m"] = (4.0 * math.sqrt(PM_ALPHA / (4.0 * PM_BETA)) * U * U / G
                               if (kind == "pierson_moskowitz" or (fetch is None and gm == 1.0)) else float("nan"))
    return out


# --------------------------------------------------------------------------- 2. the FFT sea
def _spreading(theta, directional, s_exp):
    """The directional spreading D(theta) (1/rad), normalised over the circle; theta is measured from the wind direction."""
    th = (theta + np.pi) % (2.0 * np.pi) - np.pi
    if directional == "cos2":
        return np.where(np.abs(th) < 0.5 * np.pi, 2.0 / np.pi * np.cos(th) ** 2, 0.0)
    c = math.gamma(s_exp + 1.0) / (2.0 * math.sqrt(math.pi) * math.gamma(s_exp + 0.5))
    return c * np.cos(0.5 * th) ** (2.0 * s_exp)


def _dispersion(k, depth_m):
    """omega(k) and d omega / dk for gravity waves (deep water or finite depth h: omega^2 = g k tanh(k h))."""
    if depth_m is None:
        om = np.sqrt(G * k)
        return om, np.where(om > 0, 0.5 * G / np.where(om > 0, om, 1.0), 0.0)
    th = np.tanh(k * depth_m)
    om = np.sqrt(G * k * th)
    dom = np.where(om > 0, 0.5 * G * (th + k * depth_m * (1.0 - th * th)) / np.where(om > 0, om, 1.0), 0.0)
    return om, dom


def ocean_height_field(size, extent_m, wind_speed_mps, wind_dir_deg, t=0.0, seed=0, kind="pierson_moskowitz",
                       directional="cos2", choppiness=0.0, depth_m=None, spreading_s=10.0, fetch_m=None,
                       single_mode=None) -> dict:
    """A Tessendorf (2001) FFT sea surface at time ``t`` -> dict (height, slopes, normal map, displacement).

    The wave-number spectrum is the omnidirectional spectrum of :func:`ocean_spectrum` carried to the plane,
    ``psi(k, theta) = S(omega) D(theta) (d omega / d k) / k``, with the dispersion ``omega^2 = g k`` (deep water) or
    ``omega^2 = g k tanh(k h)`` when ``depth_m`` is given. ``D`` is ``cos2`` (``2/pi cos^2`` within 90 degrees of the wind) or
    ``cos2s`` (``cos^(2s)((theta - theta_w) / 2)``, ``s = spreading_s``), both normalised to 1 over the circle. The
    random amplitudes are ``h0(k) = (xi_r + j xi_i)/sqrt(2) sqrt(psi / 2) dk`` and ``h(k, t) = h0(k) e^(-j omega t) +
    conj(h0(-k)) e^(+j omega t)``, which is Hermitian, so the height is real (``imag_residual`` reports the largest
    imaginary part left by the transform). The mean, the Nyquist row and column are zeroed. ``seed`` fixes the amplitudes:
    the same seed gives the same sea at every ``t``. ``choppiness`` moves each point horizontally by ``choppiness`` times
    the Tessendorf displacement (0 gives exactly zero displacement). ``size`` is the number of points per side (the
    grid is ``size x size`` over ``extent_m`` metres, wrap-around); ``wind_dir_deg`` is the direction the waves travel,
    from +x towards +y. ``single_mode=(mx, my, amplitude_m)`` replaces the random sea with one travelling cosine wave.
    The table has ``height``, ``slope_x``, ``slope_y`` (dh/dx, dh/dy), ``normal`` (H, W, 3), ``displacement_x`` / ``displacement_y``,
    ``x_m`` / ``y_m``, ``extent_m``, ``variance_expected_m2`` and ``slope_variance_expected`` (the sums of the spectrum over
    the modes in use), ``cox_munk_slope_variance`` (0.003 + 0.00512 U, Cox & Munk 1954), ``slope_variance_with_tail`` and ``omega_mode`` (single mode only).
    A sea of this kind has no capillary waves, so its resolved slope variance is far below the Cox & Munk value; ``slope_variance_with_tail`` adds the
    saturation range ``alpha / 2 ln(k_c / k_nyquist)`` of the spectrum up to the gravity-capillary wave number ``k_c = 370 rad/m``. That agrees with Cox & Munk
    at 5 m/s and falls 40 % short at 10 m/s (the constant ``alpha`` of the Pierson-Moskowitz range does not grow with the wind); both are shown in the PoC."""
    op = "ocean_height_field"
    n = _int(size, "size", op, 8, MAX_OCEAN_SIZE)
    L = _real(extent_m, "extent_m", op, lo=0.0, lo_open=True)
    U = _real(wind_speed_mps, "wind_speed_mps", op, lo=0.0, lo_open=True, hi=MAX_WIND_MPS)
    wd = _real(wind_dir_deg, "wind_dir_deg", op)
    tt = _real(t, "t", op)
    sd = _int(seed, "seed", op, 0, 2 ** 63 - 1)
    kind = _choice(kind, "kind", op, WAVE_KINDS)
    directional = _choice(directional, "directional", op, DIRECTIONALS)
    ch = _real(choppiness, "choppiness", op, lo=0.0, hi=10.0)
    s_exp = _real(spreading_s, "spreading_s", op, lo=0.5, hi=200.0)
    depth = None if depth_m is None else _real(depth_m, "depth_m", op, lo=0.0, lo_open=True)
    fetch = None if fetch_m is None else _real(fetch_m, "fetch_m", op, lo=0.0, lo_open=True)
    if fetch is not None and kind != "jonswap":
        raise ValueError("%s: fetch_m applies to the jonswap kind only" % op)
    dk = 2.0 * math.pi / L
    f = np.fft.fftfreq(n, d=1.0 / n)                     # integer wave-number indices
    kx1 = dk * f
    KX, KY = np.meshgrid(kx1, kx1, indexing="xy")        # [iy, ix]
    K = np.hypot(KX, KY)
    theta = np.arctan2(KY, KX) - math.radians(wd)
    om, dom = _dispersion(K, depth)
    use = K > 0.0
    if n % 2 == 0:
        nyq = np.zeros((n, n), dtype=bool)
        nyq[n // 2, :] = True
        nyq[:, n // 2] = True
        use &= ~nyq
    Ksafe = np.where(use, K, 1.0)
    s_om, alpha_sat, _ = _s_of_omega(np.where(use, om, 1.0), U, kind, fetch, JONSWAP_GAMMA)
    psi = np.where(use, s_om * _spreading(theta, directional, s_exp) * dom / Ksafe, 0.0)
    if single_mode is not None:
        if not (isinstance(single_mode, (tuple, list)) and len(single_mode) == 3):
            raise ValueError("%s: single_mode must be (mx, my, amplitude_m)" % op)
        mx = _int(single_mode[0], "single_mode mx", op, -(n // 2) + 1, n // 2 - 1)
        my = _int(single_mode[1], "single_mode my", op, -(n // 2) + 1, n // 2 - 1)
        amp = _real(single_mode[2], "single_mode amplitude_m", op, lo=0.0, lo_open=True)
        if mx == 0 and my == 0:
            raise ValueError("%s: single_mode (0, 0) is the mean level, not a wave" % op)
        h0 = np.zeros((n, n), dtype=np.complex128)
        h0[my % n, mx % n] = 0.5 * amp
        psi_used = np.zeros((n, n))
        psi_used[my % n, mx % n] = 0.25 * amp * amp / (dk * dk)
        psi_used[(-my) % n, (-mx) % n] = psi_used[my % n, mx % n]
        omega_mode = float(om[my % n, mx % n])
    else:
        rng = np.random.default_rng(sd)
        xr = rng.standard_normal((n, n))
        xi = rng.standard_normal((n, n))
        h0 = (xr + 1j * xi) / math.sqrt(2.0) * np.sqrt(psi / 2.0) * dk
        psi_used = psi
        omega_mode = float("nan")
    h0m = np.conj(np.roll(h0[::-1, ::-1], (1, 1), axis=(0, 1)))        # conj(h0(-k))
    ph = np.exp(-1j * om * tt)
    ht = h0 * ph + h0m * np.conj(ph)
    n2 = float(n * n)
    hc = np.fft.ifft2(ht) * n2
    gx = np.fft.ifft2(1j * KX * ht) * n2
    gy = np.fft.ifft2(1j * KY * ht) * n2
    imag = float(max(np.abs(hc.imag).max(), np.abs(gx.imag).max(), np.abs(gy.imag).max()))
    height, sx, sy = hc.real, gx.real, gy.real
    if ch > 0.0:
        dx = ch * np.fft.ifft2(-1j * KX / Ksafe * ht).real * n2
        dy = ch * np.fft.ifft2(-1j * KY / Ksafe * ht).real * n2
    else:
        dx = np.zeros((n, n))
        dy = np.zeros((n, n))
    nrm = np.stack([-sx, -sy, np.ones_like(sx)], axis=-1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    x = np.arange(n) * (L / n)
    return {"height": height, "slope_x": sx, "slope_y": sy, "normal": nrm, "displacement_x": dx, "displacement_y": dy,
            "x_m": x, "y_m": x.copy(), "extent_m": L, "t": tt, "imag_residual": imag,
            "variance_expected_m2": float(np.sum(psi_used) * dk * dk),
            "slope_variance_expected": float(np.sum(psi_used * K * K) * dk * dk),
            "slope_variance_with_tail": float(np.sum(psi_used * K * K) * dk * dk
                                              + 0.5 * alpha_sat * math.log(K_CAPILLARY / (dk * (n // 2)))),
            "cox_munk_slope_variance": 0.003 + 0.00512 * U, "omega_mode": omega_mode,
            "k_nyquist_rad_per_m": dk * (n // 2)}


# --------------------------------------------------------------------------- 3. Fresnel at the water surface
POLARIZATIONS = ("s", "p", "unpolarized")
DIRECTIONS = ("air_to_water", "water_to_air")


def fresnel_water_air(theta_deg, wavelength_um=0.55, polarization="s", direction="air_to_water", n_water=None) -> dict:
    """Fresnel reflectance and transmittance of the air-water interface -> dict.

    ``theta_deg`` is the angle of incidence (0 to 90, an array is accepted) on the side the light comes from;
    ``direction`` is ``air_to_water`` or ``water_to_air``. The index of water is the real part of the material table at
    ``wavelength_um`` (dispersion included: 1.3435 at 0.40 um, 1.3347 at 0.55 um, 1.3305 at 0.70 um) unless ``n_water``
    is given. The amplitude coefficients are ``r_s = (n1 cos i - n2 cos t) / (n1 cos i + n2 cos t)`` and
    ``r_p = (n2 cos i - n1 cos t) / (n2 cos i + n1 cos t)``; the reflectance is ``|r|^2`` and the transmittance is computed
    from the transmitted amplitude, ``T = n2 cos t / (n1 cos i) |t|^2``, so ``R + T = 1`` is a check and not a definition.
    Beyond the critical angle (water to air) the light is totally reflected: ``R = 1``, ``T = 0``, ``tir`` is True and the
    refracted angle is NaN. The table has ``R``, ``T`` (for ``polarization``: ``s``, ``p`` or their mean ``unpolarized``),
    ``R_s``, ``R_p``, ``T_s``, ``T_p``, ``theta_t_deg``, ``tir``, ``n_water``, ``brewster_deg`` (``atan n``) and
    ``critical_deg`` (``asin(1/n)``)."""
    op = "fresnel_water_air"
    th = _array(theta_deg, "theta_deg", op, lo=0.0, hi=90.0)
    pol = _choice(polarization, "polarization", op, POLARIZATIONS)
    dr = _choice(direction, "direction", op, DIRECTIONS)
    n = _water_index(n_water, wavelength_um, op)
    n1, n2 = (1.0, n) if dr == "air_to_water" else (n, 1.0)
    ti = np.radians(th)
    ci = np.cos(ti)
    sin_t = n1 / n2 * np.sin(ti)
    tir = sin_t > 1.0
    ct = np.sqrt(np.maximum(1.0 - sin_t * sin_t, 0.0))
    graze = ci < 1e-14
    cis = np.where(graze, 1.0, ci)
    den_s = n1 * cis + n2 * ct
    den_p = n2 * cis + n1 * ct
    rs = (n1 * cis - n2 * ct) / den_s
    rp = (n2 * cis - n1 * ct) / den_p
    ts = 2.0 * n1 * cis / den_s
    tp = 2.0 * n1 * cis / den_p
    Rs, Rp = rs * rs, rp * rp
    Ts = n2 * ct / (n1 * cis) * ts * ts
    Tp = n2 * ct / (n1 * cis) * tp * tp
    bad = tir | graze
    Rs = np.where(bad, 1.0, Rs)
    Rp = np.where(bad, 1.0, Rp)
    Ts = np.where(bad, 0.0, Ts)
    Tp = np.where(bad, 0.0, Tp)
    if pol == "s":
        R, T = Rs, Ts
    elif pol == "p":
        R, T = Rp, Tp
    else:
        R, T = 0.5 * (Rs + Rp), 0.5 * (Ts + Tp)
    tt = np.where(tir, np.nan, np.degrees(np.arcsin(np.minimum(sin_t, 1.0))))
    return {"R": R, "T": T, "R_s": Rs, "R_p": Rp, "T_s": Ts, "T_p": Tp, "theta_t_deg": tt, "tir": tir,
            "n_water": n, "brewster_deg": math.degrees(math.atan(n)), "critical_deg": math.degrees(math.asin(1.0 / n)),
            "polarization": pol, "direction": dr}


# --------------------------------------------------------------------------- 4. Snell's window
def snell_window(depth_m, n_water=None, wavelength_um=0.55, view_angle_deg=0.0) -> dict:
    """Snell's window seen from a point under the surface, and the apparent depth of a flat interface -> dict.

    From a depth ``d`` below a flat surface the whole sky is squeezed into a cone of half angle ``theta_c = asin(1/n)``
    (48.6 degrees for ``n = 1.333``, a full angle of 97.2 degrees); on the surface it is a disc of radius
    ``d tan(theta_c)``. Looking down into water from the air at ``view_angle_deg`` from the vertical, an object at depth
    ``d`` seems to lie at ``d tan(theta_w) / tan(theta_a)`` with ``sin(theta_a) = n sin(theta_w)``, which is exactly
    ``d cos(theta_a) / (n cos(theta_w))``: ``d / n`` for near-normal viewing (the paraxial value ``apparent_depth_factor_paraxial = 1/n``)
    but smaller as the angle grows (the PoC shows the error). The table has ``critical_deg``, ``window_full_angle_deg``,
    ``window_radius_m``, ``apparent_depth_factor_paraxial``, ``apparent_depth_factor`` (at ``view_angle_deg``),
    ``apparent_depth_m``, ``paraxial_error`` (the relative error of the paraxial value) and ``n_water``."""
    op = "snell_window"
    d = _array(depth_m, "depth_m", op, lo=0.0)
    if (d <= 0.0).any():
        raise ValueError("%s: depth_m must be > 0" % op)
    va = _array(view_angle_deg, "view_angle_deg", op, lo=0.0, hi=90.0)
    if (va >= 90.0).any():
        raise ValueError("%s: view_angle_deg must be < 90 (a grazing ray has no apparent depth)" % op)
    n = _water_index(n_water, wavelength_um, op)
    tc = math.asin(1.0 / n)
    ta = np.radians(va)
    stw = np.sin(ta) / n
    ctw = np.sqrt(1.0 - stw * stw)
    factor = np.cos(ta) / (n * ctw)
    return {"critical_deg": math.degrees(tc), "window_full_angle_deg": 2.0 * math.degrees(tc),
            "window_radius_m": d * math.tan(tc), "apparent_depth_factor_paraxial": 1.0 / n,
            "apparent_depth_factor": factor, "apparent_depth_m": d * factor,
            "paraxial_error": (1.0 / n) / factor - 1.0, "n_water": n, "view_angle_deg": va}


# --------------------------------------------------------------------------- 5. where an underwater point appears
SNELL_TOL = 1e-9


def _flat_refraction(px, py, pz, ex, ey, ez, n):
    """Fermat's path from underwater points (z < 0) to an eye above a flat surface: the crossing x along the horizontal line.

    Solves ``n x / sqrt(x^2 + d^2) = (s - x) / sqrt((s - x)^2 + h^2)`` on (0, s) by bisection (the left side increases and
    the right side decreases with x, so the root is unique)."""
    d = -pz
    h = ez
    vx, vy = ex - px, ey - py
    s = np.hypot(vx, vy)
    lo = np.zeros_like(s)
    hi = s.copy()
    for _ in range(120):
        mid = 0.5 * (lo + hi)
        gl = n * mid / np.sqrt(mid * mid + d * d)
        gr = (s - mid) / np.sqrt((s - mid) ** 2 + h * h)
        left = gl < gr
        lo = np.where(left, mid, lo)
        hi = np.where(left, hi, mid)
    x = 0.5 * (lo + hi)
    return x, s, vx, vy, d, h


class _PeriodicSurface:
    """A periodic bicubic height field on the tile [0, L) x [0, L) (the layout of :func:`ocean_height_field`)."""

    def __init__(self, height, extent_m, op):
        from scipy.interpolate import RectBivariateSpline
        hgt = _array(height, "surface height", op, ndim=2, min_size=16, allow_scalar=False)
        if hgt.shape[0] != hgt.shape[1] or hgt.shape[0] < 8:
            raise ValueError("%s: the height field must be square and at least 8x8, got %r" % (op, hgt.shape))
        self.L = _real(extent_m, "surface extent_m", op, lo=0.0, lo_open=True)
        n = hgt.shape[0]
        self.n = n
        self.dx = self.L / n
        pad = 4
        ext = np.pad(hgt, pad, mode="wrap")
        c = (np.arange(n + 2 * pad) - pad) * self.dx
        self.spl = RectBivariateSpline(c, c, ext, kx=3, ky=3, s=0.0)       # indexed [y, x]
        self.zmax = float(hgt.max())
        self.zmin = float(hgt.min())

    def _w(self, x, y):
        return np.mod(x, self.L), np.mod(y, self.L)

    def h(self, x, y):
        xw, yw = self._w(x, y)
        return self.spl.ev(yw, xw)

    def grad(self, x, y):
        xw, yw = self._w(x, y)
        return self.spl.ev(yw, xw, dx=0, dy=1), self.spl.ev(yw, xw, dx=1, dy=0)      # (hx, hy)


def _unit(v):
    return v / np.linalg.norm(v)


def _wavy_refraction(P, E, surf, n, x0, y0):
    """Stationary point of the optical path n|R - P| + |E - R| over a height field, from a starting guess."""
    from scipy.optimize import root

    def length_grad(xy):
        x, y = xy
        z = float(surf.h(x, y))
        hx, hy = surf.grad(x, y)
        R = np.array([x, y, z])
        a = R - P
        b = E - R
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        tx = np.array([1.0, 0.0, float(hx)])
        ty = np.array([0.0, 1.0, float(hy)])
        return np.array([n * a.dot(tx) / na - b.dot(tx) / nb, n * a.dot(ty) / na - b.dot(ty) / nb])

    sol = root(length_grad, np.array([x0, y0]), method="hybr", tol=1e-14)
    x, y = sol.x
    z = float(surf.h(x, y))
    hx, hy = surf.grad(x, y)
    R = np.array([x, y, z])
    N = _unit(np.array([-float(hx), -float(hy), 1.0]))
    dw = _unit(R - P)
    da = _unit(E - R)
    res = float(np.linalg.norm(n * np.cross(dw, N) - np.cross(da, N)))
    ok = res < SNELL_TOL and bool(np.isfinite(R).all()) and abs(x - x0) < 0.5 * surf.L and abs(y - y0) < 0.5 * surf.L
    return R, res, ok


def refracted_view(points_xyz, eye_xyz, surface="flat", n_water=None, wavelength_um=0.55) -> dict:
    """Where an underwater point appears to a camera above a flat or wavy surface (Fermat's principle) -> dict.

    ``points_xyz`` is ``(M, 3)`` (or one point), z up and the mean water level z = 0; ``eye_xyz`` is the camera, above the surface.
    A point with ``z >= surface height`` is in the air and is returned unchanged (``in_air`` True, no refraction point).
    For an underwater point the path from the point to the eye is the one of stationary optical length
    ``n |R - P| + |E - R|`` over the crossing point ``R`` on the surface; at that point Snell's law ``n sin(theta_w) = sin(theta_a)`` holds.
    Flat surface: the crossing lies in the vertical plane through the point and the eye and is the unique root of the
    Snell condition (found by bisection to machine precision); the apparent position is the point seen along the eye ray
    continued below the surface to the horizontal position of the true point: its depth is ``x h / (s - x)`` and tends to ``d / n`` for a
    camera straight above. Wavy surface: ``surface`` is a table with ``height`` (square, periodic) and ``extent_m``, as returned by
    :func:`ocean_height_field`; the crossing is found by Newton iteration on the gradient of the optical path with
    bicubic heights and normals, started from the flat solution; the vector Snell condition ``n (d_w x N) = d_a x N`` is
    verified at the result and a point that fails it (or does not converge) is returned as NaN with ``converged`` False.
    The table has ``apparent`` (M, 3), ``refraction_point`` (M, 3), ``converged``, ``in_air``, ``snell_residual``
    (flat: ``|n sin(theta_w) - sin(theta_a)|``, wavy: the norm of the vector residual), ``apparent_depth_m`` and ``n_water``.
    A caustic can make several paths possible; the one found is the stationary point nearest the flat solution."""
    op = "refracted_view"
    P = _array(points_xyz, "points_xyz", op)
    if P.ndim == 1:
        P = P[None, :]
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError("%s: points_xyz must be (M, 3), got shape %r" % (op, P.shape))
    if P.shape[0] > MAX_POINTS:
        raise ValueError("%s: %d points exceed the cap of %d" % (op, P.shape[0], MAX_POINTS))
    E = _array(eye_xyz, "eye_xyz", op, ndim=1, allow_scalar=False)
    if E.shape != (3,):
        raise ValueError("%s: eye_xyz must be (3,), got shape %r" % (op, E.shape))
    n = _water_index(n_water, wavelength_um, op)
    m = P.shape[0]
    if isinstance(surface, str):
        if surface != "flat":
            raise ValueError("%s: surface must be 'flat' or a height-field table, got %r" % (op, surface))
        wavy = None
    elif isinstance(surface, dict) and "height" in surface and "extent_m" in surface:
        wavy = _PeriodicSurface(surface["height"], surface["extent_m"], op)
    else:
        raise ValueError("%s: surface must be 'flat' or a table with 'height' and 'extent_m'" % op)
    app = P.copy()
    ref = np.full((m, 3), np.nan)
    conv = np.ones(m, dtype=bool)
    res = np.zeros(m)
    if wavy is None:
        if E[2] <= 0.0:
            raise ValueError("%s: the eye must be above the surface (z > 0), got z = %g" % (op, E[2]))
        under = P[:, 2] < 0.0
        in_air = ~under
        if under.any():
            q = P[under]
            x, s, vx, vy, d, h = _flat_refraction(q[:, 0], q[:, 1], q[:, 2], E[0], E[1], E[2], n)
            vert = s < 1e-12 * max(1.0, float(E[2]))
            sg = np.where(vert, 1.0, s)
            ux, uy = vx / sg, vy / sg
            r = np.stack([q[:, 0] + x * ux, q[:, 1] + x * uy, np.zeros_like(x)], axis=1)
            az = np.where(vert, d / n, x * h / np.where(vert, 1.0, s - x))
            a = np.stack([q[:, 0], q[:, 1], -az], axis=1)
            sw = np.where(vert, 0.0, x / np.sqrt(x * x + d * d))
            sa = np.where(vert, 0.0, (s - x) / np.sqrt((s - x) ** 2 + h * h))
            app[under] = a
            ref[under] = r
            res[under] = np.abs(n * sw - sa)
    else:
        if E[2] <= wavy.zmax:
            raise ValueError("%s: the eye must be above the highest crest (z > %g), got z = %g" % (op, wavy.zmax, E[2]))
        if m > 20000:
            raise ValueError("%s: a wavy surface takes up to 20000 points per call, got %d" % (op, m))
        hp = wavy.h(P[:, 0], P[:, 1])
        under = P[:, 2] < hp
        in_air = ~under
        for i in np.nonzero(under)[0]:
            p = P[i]
            x, s, vx, vy, d, h = _flat_refraction(np.array([p[0]]), np.array([p[1]]), np.array([min(p[2], -1e-9)]),
                                                  E[0], E[1], E[2], n)
            sg = s[0] if s[0] > 1e-12 else 1.0
            x0, y0 = p[0] + x[0] * vx[0] / sg, p[1] + x[0] * vy[0] / sg
            R, rr, ok = _wavy_refraction(p, E, wavy, n, x0, y0)
            res[i] = rr
            if not ok:
                conv[i] = False
                app[i] = np.nan
                continue
            ref[i] = R
            e_h = np.hypot(*(R[:2] - E[:2]))
            p_h = np.hypot(*(p[:2] - R[:2]))
            if e_h < 1e-12:
                app[i] = R + np.array([0.0, 0.0, -np.linalg.norm(p - R) / n])
            else:
                app[i] = R + (p_h / e_h) * (R - E)
    return {"apparent": app, "refraction_point": ref, "converged": conv, "in_air": in_air, "snell_residual": res,
            "apparent_depth_m": -app[:, 2], "n_water": n}


# --------------------------------------------------------------------------- 6. attenuation of water
_PF_NM = np.array([w for w, _ in _wd.POPE_FRY_1997], dtype=np.float64)
_PF_A = np.array([a for _, a in _wd.POPE_FRY_1997], dtype=np.float64)
_SM_NM = np.array(_wd.SM_WAVELENGTHS_NM, dtype=np.float64)


def _interp_table(nm, grid, values, op, what):
    """Linear interpolation in wavelength; outside the table, or where the table has no value (NaN), is refused."""
    if (nm < grid[0]).any() or (nm > grid[-1]).any():
        raise ValueError("%s: %s is tabulated for %g-%g nm; got %g-%g nm (nothing is extrapolated)"
                         % (op, what, grid[0], grid[-1], nm.min(), nm.max()))
    i1 = np.clip(np.searchsorted(grid, nm, side="right"), 1, grid.size - 1)
    i0 = i1 - 1
    t = (nm - grid[i0]) / (grid[i1] - grid[i0])
    v0, v1 = values[i0], values[i1]
    out = np.where(t == 0.0, v0, np.where(t == 1.0, v1, v0 + t * (v1 - v0)))
    if np.isnan(out).any():
        raise ValueError("%s: %s has no published value at %s nm" % (op, what, sorted(set(np.round(nm[np.isnan(out)], 1).tolist()))))
    return out


def water_attenuation(wavelength_um, water_type="pure", depth_m=None) -> dict:
    """Absorption, scattering and diffuse attenuation of water, and the transmittance over depth -> dict.

    ``water_type="pure"``: the absorption ``a`` is the integrating-cavity measurement of Pope & Fry (1997), 380-727.5 nm
    (minimum 0.00442 /m at 417.5 nm, 0.624 /m at 700 nm), interpolated linearly in wavelength; the scattering ``b`` is the
    pure-water law of Smith & Baker (1981), ``b = 0.00288 (lambda / 500 nm)^-4.32`` per metre; the diffuse attenuation is
    approximated as ``Kd = a + b_b`` with ``b_b = b / 2`` (a flat-sky approximation, flagged in ``kd_is_approximation``).
    ``water_type="jerlov_I"`` ... ``"jerlov_9C"`` (``IA``, ``IB``, ``II``, ``III``, ``1C``, ``3C``, ``5C``, ``7C``, ``9C``): the Jerlov (1976)
    optical water types, with ``a``, ``b`` and ``Kd`` as assigned by Solonenko & Mobley (2015) at 400-700 nm in 25 nm steps, interpolated
    linearly; the paper gives no value for 3C above 650 nm and 5C above 575 nm, and asking for one is refused. The
    scattering of types I and IA is flagged by the authors as inconsistent with their own constants (``b_suspect``). An
    unknown type is refused with the list of known ones; so is a wavelength outside the table. ``c = a + b``. ``depth_m`` (a
    scalar or a 1-D array of depths, m) adds ``transmittance = exp(-Kd z)``, the fraction of the downwelling light left at depth ``z``
    (shape ``(nz, nw)``, or ``(nw,)`` for a scalar). The table has ``wavelength_um``, ``a``, ``b``, ``c``, ``kd`` (all per metre),
    ``transmittance``, ``water_type``, ``known_types``, ``b_suspect`` and ``kd_is_approximation``."""
    op = "water_attenuation"
    wl = np.atleast_1d(_array(wavelength_um, "wavelength_um", op, lo=0.0))
    if wl.ndim != 1:
        raise ValueError("%s: wavelength_um must be a scalar or a 1-D array, got shape %r" % (op, wl.shape))
    if not isinstance(water_type, str) or water_type not in _water_type_names():
        raise ValueError("%s: unknown water_type %r; known types: %s" % (op, water_type, ", ".join(_water_type_names())))
    nm = wl * 1000.0
    if water_type == "pure":
        a = _interp_table(nm, _PF_NM, _PF_A, op, "the Pope & Fry absorption")
        b = SB_B500 * (nm / 500.0) ** SB_EXPONENT
        kd = a + PURE_BB_OVER_B * b
        suspect, approx = False, True
    else:
        key = water_type[len("jerlov_"):]
        tab = _wd.SOLONENKO_MOBLEY_2015[key]
        a = _interp_table(nm, _SM_NM, np.array(tab["a"], dtype=np.float64), op, "the Solonenko & Mobley absorption of type " + key)
        b = _interp_table(nm, _SM_NM, np.array(tab["b"], dtype=np.float64), op, "the Solonenko & Mobley scattering of type " + key)
        kd = _interp_table(nm, _SM_NM, np.array(tab["Kd"], dtype=np.float64), op, "the diffuse attenuation of type " + key)
        suspect, approx = key in _wd.SM_B_SUSPECT, False
    out = {"wavelength_um": wl, "a": a, "b": b, "c": a + b, "kd": kd, "water_type": water_type,
           "known_types": list(_water_type_names()), "b_suspect": suspect, "kd_is_approximation": approx,
           "transmittance": None}
    if depth_m is not None:
        z = _array(depth_m, "depth_m", op, lo=0.0)
        if z.ndim > 1:
            raise ValueError("%s: depth_m must be a scalar or a 1-D array" % op)
        out["transmittance"] = np.exp(-kd * z) if z.ndim == 0 else np.exp(-z[:, None] * kd[None, :])
    return out


def _water_type_names():
    return WATER_TYPES


# --------------------------------------------------------------------------- 7. underwater image formation
#: the effective wavelengths (um) of the red, green and blue channels when an RGB image is given
RGB_WAVELENGTHS_UM = (0.61, 0.54, 0.465)


def underwater_image(image, depth_map_m, distance_map_m, water_type="jerlov_I", wavelengths_um=None,
                     illumination="daylight", backscatter=True, apply_ambient=False, beta_b_ratio=1.0,
                     backscatter_ratio=0.02) -> dict:
    """The image of a scene recorded through water (revised Jaffe-McGlamery model) -> dict.

    Following Akkaynak & Treibitz (2018) the recorded image is ``I = J exp(-beta_D r) + B_inf (1 - exp(-beta_B r))``: the
    direct signal ``J`` of the object attenuated along the camera-object distance ``r`` with a wavelength-dependent
    coefficient, plus backscatter, the veiling light ``B_inf`` that builds up along the same path with its own coefficient.
    ``image`` is ``(H, W, K)``, non-negative: the appearance of the object at zero distance, per band (``K = 3`` is RGB with the
    effective wavelengths 0.61 / 0.54 / 0.465 um, other ``K`` need ``wavelengths_um``). ``depth_map_m`` is the depth of the scene below the surface and
    ``distance_map_m`` the distance to the camera, each ``(H, W)`` or a scalar. ``beta_D`` is the diffuse attenuation ``Kd`` of
    :func:`water_attenuation` (used as the attenuation along the line of sight, an approximation that Akkaynak & Treibitz
    show to depend on range) and ``beta_B = beta_b_ratio beta_D``. The veiling light is the single-scattering value
    ``B_inf = E(z) b_b / (2 c)`` with ``b_b = backscatter_ratio b`` and ``E(z) = E_0 exp(-Kd z)`` the daylight left at the depth (an assumption, not a
    measurement). ``illumination`` is ``"daylight"`` (flat relative spectrum 1) or a ``(K,)`` relative spectrum at the surface.
    With ``apply_ambient`` the object is also dimmed by the ambient light at its depth, ``J = image E(z)``; without it ``image`` is
    taken as it already is at the object, so that distance 0 returns it exactly. ``backscatter=False`` leaves pure Beer-Lambert.
    The table has ``image`` (the recording), ``direct``, ``backscatter``, ``transmission`` (``exp(-beta_D r)``),
    ``beta_D``, ``beta_B``, ``veiling_light`` (H, W, K), ``ambient`` (``E(z)/E_0``), ``wavelengths_um`` and, for RGB, ``red_to_blue_kd_ratio``.
    Non-finite or negative inputs are refused."""
    op = "underwater_image"
    im = _array(image, "image", op, ndim=3, lo=0.0, allow_scalar=False)
    h, w, k = im.shape
    if im.size > MAX_IMAGE_ELEMENTS:
        raise ValueError("%s: the image has %d elements, over the %d cap" % (op, im.size, MAX_IMAGE_ELEMENTS))
    dep = _array(depth_map_m, "depth_map_m", op, lo=0.0)
    dist = _array(distance_map_m, "distance_map_m", op, lo=0.0)
    for nm_, arr in (("depth_map_m", dep), ("distance_map_m", dist)):
        if arr.ndim not in (0, 2) or (arr.ndim == 2 and arr.shape != (h, w)):
            raise ValueError("%s: %s must be a scalar or (%d, %d), got shape %r" % (op, nm_, h, w, arr.shape))
    dep = np.broadcast_to(dep, (h, w))
    dist = np.broadcast_to(dist, (h, w))
    if wavelengths_um is None:
        if k != 3:
            raise ValueError("%s: an image with %d bands needs wavelengths_um (only 3 bands are taken as RGB)" % (op, k))
        wl = np.array(RGB_WAVELENGTHS_UM)
    else:
        wl = _array(wavelengths_um, "wavelengths_um", op, ndim=1, lo=0.0, allow_scalar=False)
        if wl.size != k:
            raise ValueError("%s: wavelengths_um has %d entries for %d bands" % (op, wl.size, k))
    if isinstance(illumination, str):
        if illumination != "daylight":
            raise ValueError("%s: illumination must be 'daylight' or a (K,) spectrum, got %r" % (op, illumination))
        e0 = np.ones(k)
    else:
        e0 = _array(illumination, "illumination", op, ndim=1, lo=0.0, allow_scalar=False)
        if e0.size != k:
            raise ValueError("%s: illumination has %d entries for %d bands" % (op, e0.size, k))
    bbr = _real(beta_b_ratio, "beta_b_ratio", op, lo=0.0)
    bsr = _real(backscatter_ratio, "backscatter_ratio", op, lo=0.0, hi=1.0)
    att = water_attenuation(wl, water_type)
    kd = att["kd"]
    ambient = np.exp(-dep[:, :, None] * kd[None, None, :])
    beta_d = kd
    beta_b = bbr * kd
    trans = np.exp(-dist[:, :, None] * beta_d[None, None, :])
    j = im * (e0[None, None, :] * ambient if apply_ambient else 1.0)
    direct = j * trans
    veil = e0[None, None, :] * ambient * (bsr * att["b"] / (2.0 * att["c"]))[None, None, :]
    if backscatter:
        back = veil * (1.0 - np.exp(-dist[:, :, None] * beta_b[None, None, :]))
    else:
        back = np.zeros_like(direct)
    out = {"image": direct + back, "direct": direct, "backscatter": back, "transmission": trans, "beta_D": beta_d,
           "beta_B": beta_b, "veiling_light": veil, "ambient": ambient, "wavelengths_um": wl, "water_type": water_type,
           "red_to_blue_kd_ratio": float(kd[0] / kd[2]) if k == 3 else float("nan")}
    return out


# --------------------------------------------------------------------------- 8. scattering phase functions
def phase_function_hg(cos_theta, g) -> dict:
    """The Henyey-Greenstein phase function, normalised over the sphere -> dict.

    ``p(cos theta) = (1 - g^2) / (4 pi (1 + g^2 - 2 g cos theta)^(3/2))`` per steradian, so that ``2 pi int p d(cos theta) = 1``
    and the mean cosine ``2 pi int p cos theta d(cos theta)`` equals ``g`` (g > 0 forward scattering, g < 0 backward). ``|g| >= 1``
    (the function is not a probability density there) and ``cos_theta`` outside [-1, 1] are refused. The table has
    ``cos_theta``, ``phase_per_sr`` and ``g``."""
    op = "phase_function_hg"
    c = _array(cos_theta, "cos_theta", op, lo=-1.0, hi=1.0)
    gg = _real(g, "g", op, lo=-1.0, hi=1.0, lo_open=True, hi_open=True)
    p = (1.0 - gg * gg) / (4.0 * np.pi * (1.0 + gg * gg - 2.0 * gg * c) ** 1.5)
    return {"cos_theta": c, "phase_per_sr": p, "g": gg}


PETZOLD_KINDS = tuple(_wd.PETZOLD_1972)
_PZ_ANG = np.array(_wd.PETZOLD_ANGLES_DEG, dtype=np.float64)


def scattering_phase_petzold(theta_deg, kind="clear") -> dict:
    """The measured volume scattering function of natural waters (Petzold 1972) as a phase function -> dict.

    Petzold's table gives the volume scattering function ``beta(theta)`` (per metre per steradian, at 530 nm) of three
    stations on 55 angles between 0.1 and 180 degrees: ``clear`` (a clear ocean), ``coastal`` (an offshore coastal channel) and
    ``turbid`` (a harbour). The phase function is ``p = beta / b`` with the station's scattering coefficient ``b``, per steradian. Between the tabulated angles
    the logarithm of ``beta`` is interpolated linearly in the logarithm of the angle (the function falls by 5 orders of magnitude
    over the range). Angles outside 0.1-180 degrees are refused. The tabulated range holds ``integral_fraction`` of ``b`` (the rest is
    below 0.1 degrees, where the function keeps rising). The table has ``theta_deg``, ``beta_per_m_sr``, ``phase_per_sr``, ``b_per_m``,
    ``station``, ``kind`` and ``integral_fraction``."""
    op = "scattering_phase_petzold"
    kind = _choice(kind, "kind", op, PETZOLD_KINDS)
    th = _array(theta_deg, "theta_deg", op, lo=_PZ_ANG[0], hi=180.0)
    rec = _wd.PETZOLD_1972[kind]
    lb = np.log(np.array(rec["beta_per_m_sr"], dtype=np.float64))
    la = np.log(_PZ_ANG)
    beta = np.exp(np.interp(np.log(th), la, lb))
    fine = np.geomspace(_PZ_ANG[0], 180.0, 20001)
    bf = np.exp(np.interp(np.log(fine), la, lb))
    integ = float(np.sum(0.5 * (bf[1:] * np.sin(np.radians(fine[1:])) + bf[:-1] * np.sin(np.radians(fine[:-1])))
                         * np.radians(np.diff(fine))) * 2.0 * np.pi)
    return {"theta_deg": th, "beta_per_m_sr": beta, "phase_per_sr": beta / rec["b_per_m"], "b_per_m": rec["b_per_m"],
            "station": rec["station"], "kind": kind, "integral_fraction": integ / rec["b_per_m"]}


# --------------------------------------------------------------------------- 9. a bottle as a cylindrical lens
def _circle_hit(p, d, r, enter):
    """Intersection of rays p + s d with a circle of radius r about the origin (smaller root entering, larger leaving)."""
    b = np.sum(p * d, axis=-1)
    c = np.sum(p * p, axis=-1) - r * r
    disc = b * b - c
    ok = disc >= 0.0
    sq = np.sqrt(np.where(ok, disc, 0.0))
    s = -b - sq if enter else -b + sq
    return np.where(ok, s, np.nan)


def _refract2(d, n_hat, n1, n2):
    """Vector Snell refraction in the plane; returns (direction, tir mask). n_hat is any unit normal of the surface."""
    cosi0 = -np.sum(d * n_hat, axis=-1)
    flip = cosi0 < 0.0
    nn = np.where(flip[..., None], -n_hat, n_hat)
    cosi = np.abs(cosi0)
    eta = n1 / n2
    k = 1.0 - eta * eta * (1.0 - cosi * cosi)
    tir = k < 0.0
    t = eta * d + ((eta * cosi - np.sqrt(np.where(tir, 0.0, k))))[..., None] * nn
    return t, tir


def cylinder_lens_caustic(radius_mm, n_glass, n_fill=1.0, thickness_wall_mm=0.0, n_rays=41) -> dict:
    """The paraxial focus and the real-ray caustic of a cylinder (a rod or a bottle) in a collimated beam -> dict.

    ``thickness_wall_mm = 0`` is a **solid rod** of index ``n_glass`` and outer radius ``radius_mm``; ``thickness_wall_mm > 0`` is a hollow
    tube of that wall thickness filled with a medium of index ``n_fill`` (1.0 = empty, 1.333 = water). The light travels along +z
    across the axis (at the origin) and is bent in the plane of the section. The paraxial focus comes from the 2x2 ray-transfer
    matrix of the surfaces (``efl = -1/C``, back focal distance ``-A/C``); for a solid rod it is the closed form
    ``f = n R / (2 (n - 1))`` measured from the axis, and for a thin-walled tube filled with ``n_fill`` the two-interface limit
    ``n_fill R / (2 (n_fill - 1))``. The real rays are traced surface by surface with the exact vector form of Snell's law
    at parallel heights from the axis up to 95 % of the clear aperture (the rod, or the fill); ``focus_z_mm`` is where each leaves
    the cylinder and crosses the axis (distance from the axis, NaN if it does not cross), ``caustic_z_mm`` / ``caustic_y_mm`` the
    envelope of neighbouring exit rays. The marginal focus (the highest ray that leaves the cylinder before it crosses the axis) is shorter than the paraxial one (positive spherical aberration).
    The table also has ``paraxial_focus_mm`` (from the axis), ``efl_mm``, ``power_per_mm`` (``C``; an empty thin tube has almost none),
    ``efl_closed_form_mm``, ``marginal_focus_mm``, ``longitudinal_aberration_mm``, ``heights_mm``, ``paths_z_mm`` / ``paths_y_mm`` (the ray
    points from the start to the exit) and ``exit_dir_z`` / ``exit_dir_y``. ``n_glass <= 1``, ``n_fill < 1`` and a wall as thick as the
    radius are refused."""
    op = "cylinder_lens_caustic"
    R = _real(radius_mm, "radius_mm", op, lo=0.0, lo_open=True)
    ng = _real(n_glass, "n_glass", op, lo=1.0, lo_open=True, hi=4.0)
    nf = _real(n_fill, "n_fill", op, lo=1.0, hi=4.0)
    t = _real(thickness_wall_mm, "thickness_wall_mm", op, lo=0.0)
    if t >= R:
        raise ValueError("%s: the wall (%g mm) must be thinner than the radius (%g mm)" % (op, t, R))
    nr = _int(n_rays, "n_rays", op, 5, 2001)
    solid = t == 0.0
    # surfaces from the front: (radius of curvature signed for the paraxial matrix, circle radius, enter flag, n before, n after)
    if solid:
        surf = [(R, R, True, 1.0, ng), (-R, R, False, ng, 1.0)]
        gaps = [2.0 * R / ng]
        aperture = R
    else:
        rc = R - t
        surf = [(R, R, True, 1.0, ng), (rc, rc, True, ng, nf), (-rc, rc, False, nf, ng), (-R, R, False, ng, 1.0)]
        gaps = [t / ng, 2.0 * rc / nf, t / ng]
        aperture = rc
    m = np.eye(2)
    for i, (rs, _, _, n1, n2) in enumerate(surf):
        m = np.array([[1.0, 0.0], [-(n2 - n1) / rs, 1.0]]) @ m
        if i < len(gaps):
            m = np.array([[1.0, gaps[i]], [0.0, 1.0]]) @ m
    A, C = m[0, 0], m[1, 0]
    power = -C
    efl = math.inf if abs(C) < 1e-15 else -1.0 / C
    bfd = math.inf if abs(C) < 1e-15 else -A / C
    para = R + bfd
    if solid:
        closed = ng * R / (2.0 * (ng - 1.0))
    else:
        closed = math.inf if nf <= 1.0 else nf * R / (2.0 * (nf - 1.0))
    heights = 0.95 * aperture * np.arange(1, nr + 1) / nr
    p = np.stack([np.full(nr, -2.0 * R), heights], axis=1)
    d = np.stack([np.ones(nr), np.zeros(nr)], axis=1)
    pz = [p[:, 0].copy()]
    py = [p[:, 1].copy()]
    dead = np.zeros(nr, dtype=bool)
    for _, rr, enter, n1, n2 in surf:
        s = _circle_hit(p, d, rr, enter)
        dead |= ~np.isfinite(s)
        hit = p + np.where(np.isfinite(s), s, 0.0)[:, None] * d
        d, tir = _refract2(d, hit / rr, n1, n2)
        dead |= tir
        p = hit
        pz.append(p[:, 0].copy())
        py.append(p[:, 1].copy())
    cross = (~dead) & (d[:, 1] < -1e-15)
    sfoc = np.where(cross, -p[:, 1] / np.where(cross, d[:, 1], 1.0), np.nan)
    focus = p[:, 0] + sfoc * d[:, 0]
    focus = np.where(cross & (sfoc > 0.0), focus, np.nan)
    # envelope: intersect neighbouring exit rays
    cz = np.full(nr - 1, np.nan)
    cy = np.full(nr - 1, np.nan)
    for i in range(nr - 1):
        if dead[i] or dead[i + 1]:
            continue
        den = d[i, 0] * d[i + 1, 1] - d[i, 1] * d[i + 1, 0]
        if abs(den) < 1e-15:
            continue
        w0 = p[i + 1] - p[i]
        si = (w0[0] * d[i + 1, 1] - w0[1] * d[i + 1, 0]) / den
        if si > 0.0:
            cz[i] = p[i, 0] + si * d[i, 0]
            cy[i] = p[i, 1] + si * d[i, 1]
    good = np.nonzero(np.isfinite(focus))[0]
    marginal = float(focus[good[-1]]) if good.size else float("nan")
    return {"paraxial_focus_mm": para, "efl_mm": efl, "power_per_mm": power, "efl_closed_form_mm": closed,
            "back_focal_distance_mm": bfd, "heights_mm": heights, "focus_z_mm": focus, "marginal_focus_mm": marginal,
            "longitudinal_aberration_mm": para - marginal, "caustic_z_mm": cz, "caustic_y_mm": cy,
            "paths_z_mm": np.stack(pz, axis=1), "paths_y_mm": np.stack(py, axis=1), "exit_dir_z": d[:, 0].copy(),
            "exit_dir_y": d[:, 1].copy(), "solid": solid, "aperture_mm": aperture}
