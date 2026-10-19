# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""lockin — per-pixel quadrature demodulation (lock-in / time-correlation imaging) of an image sequence.

A time-correlation image sensor, a lock-in camera and a lock-in thermography rig do the same thing:
the scene is lit (or heated) with a known modulation, every pixel is correlated with a reference
signal, and what comes out is not the picture but three numbers per pixel: the amplitude and the
phase of the part that follows the reference, and the mean (DC). Whatever does not follow the
reference (ambient light, slow drift, a different modulation) is rejected. Here the same operation is
a plain function of an image sequence ``(T, H, W)`` taken at ``fps`` frames per second::

    x_k = DC + A cos(2 pi f_ref k / fps + phi)   ->   lockin_demodulate(video, f_ref, fps)

with ``z = (2 / sum w) sum_k w_k x_k exp(-j 2 pi f_ref k / fps)``, ``A = |z|``, ``phi = arg z`` and
``DC = sum w x / sum w``. The window ``w`` is declared, never implied: ``rect`` is exact only for a
whole number of reference periods in the sequence (otherwise the op refuses and says how many
periods there are); ``hann`` accepts a fractional number of periods and reports the leakage it
leaves (``leak_image``, ``leak_dc``).

The ops::

    lockin_demodulate(video, f_ref, fps, window)      -> amplitude, phase, DC, in-phase, quadrature, leakage
    lockin_amplitude / lockin_phase                   -> the two maps as 2-D images
    lockin_noise_floor(n_frames, sigma, A, window)    -> the closed-form noise of A and phi from the SNR
    lockin_walsh_codes(n_frames, n_codes)             -> orthogonal zero-mean +-1 on/off codes
    lockin_separate(video, codes)                     -> one image per coded light + the uncoded rest
    lockin_ring_synthesize(height, ...)               -> a ring of sources with a multipole phase pattern
    lockin_ring_normals(demod, zenith_deg)            -> surface normals from the first-harmonic response
    lockin_thermal_wave(depth, ...)                   -> steady-state surface temperature of a heated plate

The amplitude and phase of a pixel are a measurement with a known noise: for white noise of standard
deviation ``sigma`` and ``N`` frames the real and imaginary parts of ``z`` each have a standard
deviation of ``sigma sqrt(2/N)`` (``rect``), so the phase standard deviation is
``sigma sqrt(2/N) / A`` at high SNR and the exact Rice-phase value in general
(:func:`lockin_noise_floor`).
"""
from __future__ import annotations

import math

import numpy as np


__all__ = ["lockin_demodulate", "lockin_amplitude", "lockin_phase", "lockin_noise_floor",
           "lockin_walsh_codes", "lockin_separate", "lockin_ring_synthesize", "lockin_ring_normals",
           "lockin_thermal_wave"]

#: the largest image sequence (frames x pixels) the ops take; larger is refused rather than run out of memory
MAX_VIDEO_ELEMENTS = 1 << 24
#: the most frames in one sequence
MAX_FRAMES = 4096
WINDOWS = ("rect", "hann")
#: a whole number of periods is accepted when it is within this many periods of an integer
PERIOD_TOL = 1e-6
#: the codes of :func:`lockin_separate` must be better conditioned than this
MAX_CONDITION = 1e8
#: largest SNR at which the exact Rice-phase integral is evaluated (above it the small-noise value is returned)
_MAX_EXACT_R = 100.0


def _require_video(video, name, op, max_elements):
    """Coerce to a validated ``(T, H, W)`` float64 sequence (a list of equal 2-D frames is accepted); refuse the rest."""
    if isinstance(video, (list, tuple)):
        if not video:
            raise ValueError("%s: %s is an empty frame list" % (op, name))
        frames = [np.asarray(f) for f in video]
        if any(f.ndim != 2 for f in frames) or len({f.shape for f in frames}) != 1:
            raise ValueError("%s: %s frames must be 2-D and of one shape" % (op, name))
        arr = np.stack(frames, axis=0)
    else:
        arr = np.asarray(video)
    if np.ma.is_masked(video):
        raise ValueError("%s: %s is a masked array; fill or drop the masked entries explicitly" % (op, name))
    if np.iscomplexobj(arr):
        raise ValueError("%s: %s is complex; coercion to float64 would silently discard the imaginary part" % (op, name))
    if arr.dtype.kind not in "biuf":
        raise ValueError("%s: %s must be numeric, got dtype %s" % (op, name, arr.dtype))
    vid = np.ascontiguousarray(arr, dtype=np.float64)
    if vid.ndim != 3:
        raise ValueError("%s: %s must be a (T, H, W) clip, got a %d-D array of shape %r; nothing is reshaped silently"
                         % (op, name, vid.ndim, tuple(vid.shape)))
    if vid.shape[0] < 3:
        raise ValueError("%s: %s has %d frames; at least 3 are needed to define a temporal frequency" % (op, name, vid.shape[0]))
    if vid.shape[0] > MAX_FRAMES:
        raise ValueError("%s: %s has %d frames, over the %d cap" % (op, name, vid.shape[0], MAX_FRAMES))
    if vid.shape[1] < 1 or vid.shape[2] < 1:
        raise ValueError("%s: %s frames are empty" % (op, name))
    if vid.size > max_elements:
        raise ValueError("%s: %s has %d elements (shape %r), over the %d cap" % (op, name, vid.size, tuple(vid.shape), max_elements))
    if not np.isfinite(vid).all():
        raise ValueError("%s: %s has %d non-finite sample(s) (NaN or Inf); refusing" % (op, name, int((~np.isfinite(vid)).sum())))
    return vid


def _int(value, name, op, lo, hi=None):
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        if isinstance(value, (float, np.floating)) and float(value).is_integer():
            value = int(value)
        else:
            raise ValueError("%s: %s must be an integer, got %r" % (op, name, value))
    value = int(value)
    if value < lo or (hi is not None and value > hi):
        raise ValueError("%s: %s must be in [%d, %s], got %d" % (op, name, lo, "inf" if hi is None else hi, value))
    return value


def _pos(value, name, op, allow_zero=False):
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a number, got %r" % (op, name, value)) from None
    if not math.isfinite(v) or v < 0.0 or (v == 0.0 and not allow_zero):
        raise ValueError("%s: %s must be finite and %s, got %r" % (op, name, ">= 0" if allow_zero else "> 0", value))
    return v


def _window(n, name, op):
    if name == "rect":
        return np.ones(n)
    if name == "hann":
        return 0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(n) / n)       # periodic Hann
    raise ValueError("%s: window must be one of %s, got %r" % (op, WINDOWS, name))


def _reference(f_ref, fps, n, window, op):
    """Validate (f_ref, fps, n, window) -> (f_ref, fps, periods, w). Refuse what would be silently wrong."""
    f = _pos(f_ref, "f_ref", op)
    fs = _pos(fps, "fps", op)
    if not f < 0.5 * fs:
        raise ValueError("%s: f_ref = %g Hz is not below the Nyquist frequency fps/2 = %g Hz" % (op, f, 0.5 * fs))
    w = _window(n, window, op)
    periods = f * n / fs
    if periods < 1.0:
        raise ValueError("%s: the sequence holds %.4g periods of the reference; at least 1 is needed" % (op, periods))
    if window == "rect" and abs(periods - round(periods)) > PERIOD_TOL:
        raise ValueError(
            "%s: window 'rect' needs a whole number of reference periods but the %d frames at %g fps hold %.6g "
            "periods of %g Hz; use about %.1f or %.1f frames, or declare window='hann' (which leaves a reported leakage)"
            % (op, n, fs, periods, f, math.floor(periods) * fs / f, math.ceil(periods) * fs / f))
    return f, fs, periods, w


def _leak(w, f, fs):
    """Window leakage of the reference: (image, dc) = |W(2f)| / W(0), |W(f)| / W(0)."""
    k = np.arange(len(w))
    w0 = float(w.sum())
    wf = abs(complex(np.sum(w * np.exp(-2j * np.pi * f * k / fs))))
    w2 = abs(complex(np.sum(w * np.exp(-4j * np.pi * f * k / fs))))
    return w2 / w0, wf / w0


def lockin_demodulate(video, f_ref, fps, window="rect") -> dict:
    """Per-pixel quadrature demodulation of an image sequence against a sinusoidal reference -> dict of maps.

    For every pixel the sequence is correlated with ``cos`` and ``sin`` of the reference frequency:
    ``x_k = DC + A cos(2 pi f_ref k / fps + phi)``. The table holds ``amplitude`` (A), ``phase`` (phi in
    radians, (-pi, pi]; 0 where A is 0), ``dc``, ``in_phase`` (A cos phi), ``quadrature`` (A sin phi) and the
    scalars ``periods`` (reference periods in the sequence), ``window``, ``leak_image`` and ``leak_dc``.

    The window is declared. ``rect`` is exact (a sinusoid of amplitude 2.5 and phase 0.7 rad is returned to
    1e-15) but only for a whole number of periods; any other length is refused with the nearest frame counts
    named. ``hann`` takes any length of at least one period and states what it leaks:
    ``leak_image`` (the conjugate image of the reference, relative to its amplitude) and ``leak_dc``
    (a DC offset enters the quadrature sum by 2 ``leak_dc`` times its size)."""
    op = "lockin_demodulate"
    vid = _require_video(video, "video", op, MAX_VIDEO_ELEMENTS)
    n = vid.shape[0]
    f, fs, periods, w = _reference(f_ref, fps, n, window, op)
    ph = 2.0 * np.pi * f * np.arange(n) / fs
    flat = vid.reshape(n, -1)
    sw = float(w.sum())
    shape = vid.shape[1:]
    in_phase = ((2.0 / sw) * ((w * np.cos(ph)) @ flat)).reshape(shape)          # A cos(phi)
    quad = (-(2.0 / sw) * ((w * np.sin(ph)) @ flat)).reshape(shape)             # A sin(phi)
    dc = ((w @ flat) / sw).reshape(shape)
    leak_image, leak_dc = _leak(w, f, fs)
    return {"amplitude": np.hypot(in_phase, quad), "phase": np.arctan2(quad, in_phase), "dc": dc,
            "in_phase": in_phase, "quadrature": quad, "periods": float(periods), "window": window,
            "n_frames": int(n), "f_ref": f, "fps": fs, "leak_image": float(leak_image), "leak_dc": float(leak_dc)}


def lockin_amplitude(video, f_ref, fps, window="rect") -> np.ndarray:
    """Amplitude map A of the part of every pixel that follows the reference -> (H, W) image.

    The same number as ``lockin_demodulate(...)["amplitude"]``; a steady background, drift outside the
    reference frequency and other modulation frequencies do not contribute (a whole number of periods
    rejects them exactly, to rounding)."""
    return lockin_demodulate(video, f_ref, fps, window)["amplitude"]


def lockin_phase(video, f_ref, fps, window="rect") -> np.ndarray:
    """Phase map phi (radians, (-pi, pi]) of the part of every pixel that follows the reference -> (H, W) image.

    The phase is unaffected by a multiplicative change of the whole pixel signal (reflectance, emissivity,
    a non-uniform heating or illumination level): it reads where the response is late, not how strong it is.
    A pixel with zero amplitude has no phase and reads 0."""
    return lockin_demodulate(video, f_ref, fps, window)["phase"]


def _phase_std_exact(r: float) -> float:
    """Standard deviation of the phase of (A + n) / A, with n complex Gaussian of component std s, r = A / s."""
    m = 200001
    dth = 2.0 * np.pi / m
    th = (np.arange(m) + 0.5) * dth - np.pi
    c = r * np.cos(th)
    erf = np.vectorize(math.erf)(c / math.sqrt(2.0))
    pdf = (math.exp(-0.5 * r * r) / (2.0 * np.pi)
           + (c / (2.0 * math.sqrt(2.0 * np.pi))) * np.exp(-0.5 * r * r * np.sin(th) ** 2) * (1.0 + erf))
    pdf = pdf / (pdf.sum() * dth)
    return float(math.sqrt(np.sum(th ** 2 * pdf) * dth))


def lockin_noise_floor(n_frames, noise_sigma, amplitude, window="rect") -> dict:
    """Closed-form noise of the lock-in amplitude and phase for white noise -> dict.

    With white noise of standard deviation ``noise_sigma`` per frame, ``n_frames`` frames and a reference
    of amplitude ``amplitude``, the in-phase and quadrature estimates are independent with the same standard
    deviation ``component_std = noise_sigma sqrt(2 sum w^2) / sum w`` (``noise_sigma sqrt(2/N)`` for ``rect``,
    ``noise_sigma sqrt(3/N)`` for ``hann``). The table gives ``amplitude_std`` (= ``component_std`` at high
    SNR), ``phase_std_small_noise`` (= ``component_std / amplitude`` radians) and ``phase_std_exact``, the standard
    deviation of the Rice phase distribution at the SNR ``snr_component = amplitude / component_std``: at SNR 1 it is
    already 0.75 rad and tends to pi / sqrt(3) when there is no signal. The exact value is evaluated by
    numerical integration of the density and is given for ``snr_component`` up to 100 (above that the
    two agree to better than 1e-4 and the small-noise value is returned)."""
    op = "lockin_noise_floor"
    n = _int(n_frames, "n_frames", op, 3)
    s = _pos(noise_sigma, "noise_sigma", op, allow_zero=True)
    a = _pos(amplitude, "amplitude", op)
    w = _window(n, window, op)
    comp = s * math.sqrt(2.0 * float(np.sum(w * w))) / float(w.sum())
    r = a / comp if comp > 0 else float("inf")
    small = comp / a
    exact = small if (not math.isfinite(r) or r > _MAX_EXACT_R) else _phase_std_exact(r)
    return {"component_std": comp, "amplitude_std": comp, "phase_std_small_noise": small,
            "phase_std_exact": exact, "snr_component": r if math.isfinite(r) else 1e300,
            "window": window, "n_frames": n}


def lockin_walsh_codes(n_frames, n_codes) -> np.ndarray:
    """Orthogonal zero-mean on/off codes for coded intermittent lighting -> (n_codes, n_frames) matrix of +-1.

    Rows 1..n_codes of the Sylvester-Hadamard matrix (the constant row 0 is left out): every row has mean 0,
    any two rows have zero inner product, so lights switched by different rows can be told apart (and from a
    steady background) by correlation (:func:`lockin_separate`). A light that is ON where the code is +1 and OFF
    where it is -1 has the on/off pattern ``(1 + code) / 2``. ``n_frames`` must be a power of two."""
    op = "lockin_walsh_codes"
    n = _int(n_frames, "n_frames", op, 2, 1 << 14)
    if n & (n - 1):
        raise ValueError("%s: n_frames must be a power of two for a Walsh code, got %d" % (op, n))
    m = _int(n_codes, "n_codes", op, 1, n - 1)
    j = np.arange(n)
    rows = []
    for kk in range(1, m + 1):
        bits = np.bitwise_and(kk, j)
        par = np.zeros(n, np.int64)
        while bits.any():
            par ^= (bits & 1)
            bits = bits >> 1
        rows.append(1.0 - 2.0 * par)
    return np.asarray(rows, np.float64)


def lockin_separate(video, codes) -> dict:
    """Separate coded lights and the uncoded rest by least squares against zero-mean codes -> dict of maps.

    Models every pixel as ``x_k = dc + sum_l a_l code_l[k]`` and solves for ``dc`` and the coefficients ``a_l`` by
    least squares (so the codes need not be orthogonal, only independent of each other and of a constant). A
    light switched on where ``code`` is +1 and off where it is -1 with on-state image ``L`` has ``a = L / 2``
    (``on_image = 2 a``). The table holds ``coefficients`` (n_codes, H, W), ``on_image`` (the same times 2),
    ``dc`` (uncoded mean level: ambient plus half of every coded light), ``residual_rms`` (what the model does not
    explain: a flicker or drift the codes do not carry) and ``condition`` (of the design matrix). Codes that are
    constant, of the wrong length, or so dependent that ``condition`` exceeds 1e8 are refused."""
    op = "lockin_separate"
    vid = _require_video(video, "video", op, MAX_VIDEO_ELEMENTS)
    n = vid.shape[0]
    c = np.asarray(codes, np.float64)
    if c.ndim == 1:
        c = c[None, :]
    if c.ndim != 2 or c.shape[1] != n or c.shape[0] < 1:
        raise ValueError("%s: codes must be (n_codes, T) or (T,) with T = %d frames, got shape %r" % (op, n, np.shape(codes)))
    if not np.isfinite(c).all():
        raise ValueError("%s: codes contain non-finite values" % op)
    if n <= c.shape[0] + 1:
        raise ValueError("%s: %d codes need more than %d frames" % (op, c.shape[0], c.shape[0] + 1))
    if np.any(np.ptp(c, axis=1) == 0.0):
        raise ValueError("%s: a code is constant; it cannot be told from the background" % op)
    x = np.concatenate([np.ones((n, 1)), c.T], axis=1)
    cond = float(np.linalg.cond(x))
    if not cond < MAX_CONDITION:
        raise ValueError("%s: the codes are linearly dependent with each other or with a constant (condition %.3g)" % (op, cond))
    flat = vid.reshape(n, -1)
    beta, *_ = np.linalg.lstsq(x, flat, rcond=None)
    res = flat - x @ beta
    shape = vid.shape[1:]
    coef = beta[1:].reshape((c.shape[0],) + shape)
    return {"coefficients": coef, "on_image": 2.0 * coef, "dc": beta[0].reshape(shape),
            "residual_rms": np.sqrt(np.mean(res * res, axis=0)).reshape(shape), "condition": cond,
            "n_codes": int(c.shape[0])}


def lockin_ring_synthesize(height, zenith_deg, n_sources, multipole, frames_per_period, n_periods,
                           albedo=None, noise_sigma=None, seed=None) -> np.ndarray:
    """A Lambertian relief lit by a ring of modulated sources -> image sequence (T, H, W).

    ``height`` is a height map in pixel units (normal = (-h_x, -h_y, 1) / norm). ``n_sources`` point sources sit at
    zenith angle ``zenith_deg`` from the camera axis and equally spaced azimuths theta_s; source ``s`` emits
    ``(1 + cos(2 pi k / frames_per_period - multipole theta_s)) / n_sources`` in frame ``k``, i.e. the modulation phase
    runs around the ring ``multipole`` times (multipole 1 = a dipole pattern, 0 = all in phase). Pixels follow
    ``albedo * max(0, n . l_s)`` summed over sources, shadows included. The sequence has ``frames_per_period *
    n_periods`` frames and is demodulated with ``lockin_demodulate(video, 1.0, frames_per_period)``. White noise
    of standard deviation ``noise_sigma`` needs an explicit ``seed`` (no hidden random state)."""
    op = "lockin_ring_synthesize"
    h = np.asarray(height, np.float64)
    if h.ndim != 2 or h.shape[0] < 4 or h.shape[1] < 4 or not np.isfinite(h).all():
        raise ValueError("%s: height must be a finite 2-D map of at least 4x4, got shape %r" % (op, np.shape(height)))
    z = _pos(zenith_deg, "zenith_deg", op)
    if z >= 90.0:
        raise ValueError("%s: zenith_deg must be below 90, got %g" % (op, z))
    s = _int(n_sources, "n_sources", op, 3, 64)
    m = _int(multipole, "multipole", op, 0, s - 1)
    fpp = _int(frames_per_period, "frames_per_period", op, 3, 256)
    npd = _int(n_periods, "n_periods", op, 1, 64)
    if fpp * npd * h.size > MAX_VIDEO_ELEMENTS:
        raise ValueError("%s: %d frames of %r exceed the %d element cap" % (op, fpp * npd, h.shape, MAX_VIDEO_ELEMENTS))
    rho = 1.0 if albedo is None else np.asarray(albedo, np.float64)
    if albedo is not None and (rho.shape != h.shape or not np.isfinite(rho).all() or (rho < 0).any()):
        raise ValueError("%s: albedo must be a finite non-negative map of the height's shape %r" % (op, h.shape))
    gy, gx = np.gradient(h)
    nrm = np.sqrt(gx * gx + gy * gy + 1.0)
    nx, ny, nz = -gx / nrm, -gy / nrm, 1.0 / nrm
    zr = math.radians(z)
    th = 2.0 * np.pi * np.arange(s) / s
    lx, ly, lz = math.sin(zr) * np.cos(th), math.sin(zr) * np.sin(th), math.cos(zr)
    shade = np.maximum(0.0, nx[None] * lx[:, None, None] + ny[None] * ly[:, None, None] + nz[None] * lz) * rho
    k = np.arange(fpp * npd)
    mod = (1.0 + np.cos(2.0 * np.pi * k[:, None] / fpp - m * th[None, :])) / s
    out = np.einsum("ts,shw->thw", mod, shade)
    if noise_sigma is not None:
        sg = _pos(noise_sigma, "noise_sigma", op, allow_zero=True)
        if seed is None:
            raise ValueError("%s: noise needs an explicit integer seed" % op)
        out = out + np.random.default_rng(_int(seed, "seed", op, 0)).normal(0.0, sg, out.shape)
    return out


def lockin_ring_normals(demod, zenith_deg) -> dict:
    """Surface normals from the first-harmonic response of a dipole-modulated ring -> dict of maps.

    For a Lambertian pixel with unit normal ``n = (n_x, n_y, n_z)`` under a ring of sources at zenith angle
    ``zeta`` modulated with multipole 1, the response at the modulation frequency is
    ``z = A exp(j phi) = (rho / 2) sin(zeta) (n_x - j n_y)`` and the DC is ``rho cos(zeta) n_z`` (per unit ring
    power). The albedo ``rho`` cancels: ``(n_x - j n_y) / n_z = 2 z / (DC tan zeta)``. ``demod`` is the table of
    :func:`lockin_demodulate`. The result has ``height_gradient_x`` / ``height_gradient_y`` (-n_x / n_z, -n_y / n_z),
    ``normal`` (H, W, 3), ``tilt_deg``, ``azimuth_deg`` (direction of the height gradient) and ``valid``.
    A pixel is valid only if no source of the ring is in shadow, which is ``A / DC < 1/2`` (tilt below 90 - zenith_deg);
    the other pixels, and pixels with DC <= 0, are NaN in every map and False in ``valid``: the model does not apply there."""
    op = "lockin_ring_normals"
    if not isinstance(demod, dict) or not {"amplitude", "phase", "dc"} <= set(demod):
        raise ValueError("%s: demod must be the table of lockin_demodulate (amplitude, phase, dc)" % op)
    z = _pos(zenith_deg, "zenith_deg", op)
    if z >= 90.0:
        raise ValueError("%s: zenith_deg must be below 90, got %g" % (op, z))
    amp = np.asarray(demod["amplitude"], np.float64)
    ph = np.asarray(demod["phase"], np.float64)
    dc = np.asarray(demod["dc"], np.float64)
    if amp.ndim != 2 or amp.shape != ph.shape or amp.shape != dc.shape:
        raise ValueError("%s: amplitude, phase and dc must be 2-D maps of one shape" % op)
    if not (np.isfinite(amp).all() and np.isfinite(ph).all() and np.isfinite(dc).all()):
        raise ValueError("%s: the demodulation table has non-finite values" % op)
    valid = (dc > 0.0) & (amp < 0.5 * np.where(dc > 0.0, dc, 1.0))
    safe = np.where(valid, dc, 1.0)
    w = 2.0 * amp * np.exp(1j * ph) / (safe * math.tan(math.radians(z)))     # (n_x - j n_y) / n_z
    nxz, nyz = w.real, -w.imag
    nz = 1.0 / np.sqrt(nxz * nxz + nyz * nyz + 1.0)
    normal = np.stack([nxz * nz, nyz * nz, nz], axis=-1)
    gx, gy = -nxz, -nyz
    tilt = np.degrees(np.arctan2(np.hypot(nxz, nyz), 1.0))
    az = np.degrees(np.arctan2(gy, gx))
    nan = np.where(valid, 0.0, np.nan)
    return {"height_gradient_x": gx + nan, "height_gradient_y": gy + nan, "normal": normal + nan[..., None],
            "tilt_deg": tilt + nan, "azimuth_deg": az + nan, "valid": valid}


def lockin_thermal_wave(depth, thermal_diffusivity, f_heat, frames_per_period, n_periods, nonuniformity=None) -> np.ndarray:
    """Steady-state surface temperature of a plate heated by a sinusoidal flux, per pixel -> image sequence (T, H, W).

    A layer of thickness ``depth`` (m; a pixel over a flat-bottom void has the void depth, a sound pixel the plate
    thickness) with an insulated back face is heated by a flux ``q cos(2 pi f_heat t)``. The one-dimensional heat
    equation gives the complex surface temperature ``T = q coth(sigma L) / (e sqrt(omega) sqrt(j))`` with
    ``sigma = (1 + j) / mu``, ``mu = sqrt(2 alpha / omega)`` (thermal diffusion length), ``omega = 2 pi f_heat`` and
    effusivity ``e``. The output is in units of ``q / (e sqrt(omega))`` and frame ``k`` is ``Re(T exp(j 2 pi k /
    frames_per_period))``: the phase of a deep (``L >> mu``) pixel is -45 degrees, a shallow void is later (towards -90) and
    brighter. ``nonuniformity`` is an optional positive map that multiplies the whole signal (uneven heating or emissivity:
    it changes the amplitude map and leaves the phase map alone). The transient of the first periods is not modelled."""
    op = "lockin_thermal_wave"
    d = np.asarray(depth, np.float64)
    if d.ndim != 2 or d.shape[0] < 4 or d.shape[1] < 4 or not np.isfinite(d).all() or (d <= 0.0).any():
        raise ValueError("%s: depth must be a finite positive 2-D map (m) of at least 4x4, got shape %r" % (op, np.shape(depth)))
    al = _pos(thermal_diffusivity, "thermal_diffusivity", op)
    f = _pos(f_heat, "f_heat", op)
    fpp = _int(frames_per_period, "frames_per_period", op, 3, 256)
    npd = _int(n_periods, "n_periods", op, 1, 64)
    if fpp * npd * d.size > MAX_VIDEO_ELEMENTS:
        raise ValueError("%s: the sequence exceeds the %d element cap" % (op, MAX_VIDEO_ELEMENTS))
    om = 2.0 * np.pi * f
    mu = math.sqrt(2.0 * al / om)
    sig_l = (1.0 + 1.0j) * d / mu
    big = np.abs(sig_l.real) > 300.0
    t = np.where(big, 1.0 + 0.0j, 1.0 / np.tanh(np.where(big, 1.0 + 0.0j, sig_l)))   # coth; exactly 1 for a very deep layer
    zt = t * np.exp(-0.25j * np.pi)
    rot = np.exp(2j * np.pi * np.arange(fpp * npd) / fpp)
    out = (zt[None] * rot[:, None, None]).real
    if nonuniformity is not None:
        nu = np.asarray(nonuniformity, np.float64)
        if nu.shape != d.shape or not np.isfinite(nu).all() or (nu <= 0.0).any():
            raise ValueError("%s: nonuniformity must be a finite positive map of the depth's shape %r" % (op, d.shape))
        out = out * nu[None]
    return out
