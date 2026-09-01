# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Coherent ranging: FMCW range-Doppler and delay-and-sum beamforming (numpy only).

The **signal-processing layer under a coherent range sensor**. A time-of-flight
sensor answers "how far"; a *coherent* one — frequency-modulated continuous wave
(FMCW) radar, or FMCW/frequency-swept lidar — answers "how far **and how fast**"
from the same acquisition, because it keeps the phase of the returned wave. That
extra quantity is not an extra measurement: it falls out of a second Fourier
transform across the repeated chirps, and both axes are closed-form.

Fullseye already had the *geometry* of ranging (``lidar_scan`` / ``pseudo_lidar``
cast rays and report distance). It had no signal layer at all, so velocity was
not merely inaccurate — it was inexpressible. This module is that layer, in four
families:

  * **design** — :func:`fmcw_design`: bin widths, resolutions and the two
    unambiguous limits, in closed form, before any data exists. Same stance as
    :mod:`visiondesign`: where a full simulation is out of scope, return the
    *limits*, which are usually what decides feasibility.
  * **simulate** — :func:`fmcw_beat_simulate`: the forward model. Known ranges,
    velocities and arrival angles in, the complex beat cube out. This is the
    supplier of ground truth for everything else here.
  * **process** — :func:`fmcw_window_apply`, :func:`range_doppler_map`,
    :func:`range_doppler_peaks`, :func:`fmcw_range_profile`: the 2-D FFT (fast
    time -> range, slow time -> velocity), the window that trades main-lobe width
    for sidelobe level, and the detection step that turns bin indices back into
    metres and metres per second.
  * **beamform** — :func:`beamform_delay_sum`, :func:`beamform_doa`: the angle
    axis from a uniform linear array, by the classical delay-and-sum (Bartlett)
    beamformer applied to one range-Doppler cell.

The physics, stated once, because every test in this family is an identity
derived from these four lines (B. R. Mahafza, *Radar Systems Analysis and Design
Using MATLAB*, CRC; M. A. Richards, *Fundamentals of Radar Signal Processing*,
McGraw-Hill; H. L. Van Trees, *Optimum Array Processing*, Wiley 2002):

  1. A chirp of slope ``S`` [Hz/s] reflected from range ``R`` returns after
     ``tau = 2R/c`` and, after mixing, leaves a **beat frequency**
     ``f_b = 2*S*R/c``. Sampling ``N_s`` points at ``f_s`` and transforming puts
     that target in range bin ``k = f_b*N_s/f_s``.
  2. Between chirps spaced ``T_c`` apart the target moves ``v*T_c``, which is
     ``4*pi*v*T_c/lambda`` of carrier phase — the **Doppler phase advance**. The
     transform across chirps puts the target in velocity bin
     ``m = 2*v*T_c*N_c/lambda``.
  3. A plane wave arriving at ``theta`` off boresight advances by
     ``2*pi*d*sin(theta)/lambda`` per array element of spacing ``d``. Summing the
     elements after removing that phase peaks at the true ``theta``.
  4. Each of those is a Fourier pair, so each has an aliasing limit:
     ``R < c*f_s/(2S)``, ``|v| < lambda/(4*T_c)``, ``|sin theta| < lambda/(2d)``.

Sign and axis conventions — the traps, stated once:

  * **Positive velocity means receding.** ``v = dR/dt``: a target moving *away*
    has ``v > 0`` and lands in a **positive** Doppler bin; an approaching target
    has ``v < 0``. Getting this backwards does not raise and does not change the
    picture — the map looks identical, mirrored — so it is checked explicitly in
    the tests rather than assumed.
  * **Positive angle means the wave reaches the higher-index elements later** in
     range but *earlier* in phase: element ``a`` sits at ``x = a*d`` along the
     array axis and carries phase ``+2*pi*d*a*sin(theta)/lambda``. The mirror
     convention is equally common in the literature and equally invisible in a
     plot, so it too is pinned by test.
  * **Cube axis order is ``(antenna, chirp, sample)``** — slow time in the
     middle, **fast time last**. A transposed cube is still a valid 3-D complex
     array and would produce a plausible-wrong map, so the ops check what they
     can (see :func:`fmcw_window_apply`, which names the axis by role rather
     than by number).
  * **The input must be complex (I/Q).** A real-sampled beat stream has a
     conjugate-symmetric spectrum, so **every target appears twice**: once where
     it is, and once as an equal-amplitude ghost at the fabricated range
     ``(N_s - k)*dR`` carrying the *opposite* velocity. Measured: a target in
     range bin 10 at velocity bin +4 gives peaks at ``(10, +4)`` **and**
     ``(54, -4)``, both of amplitude exactly 0.5, and nothing in the map says
     which is real. (An earlier draft of this module claimed the velocity
     *sign* was lost in a real cube. That is true of a range-only real signal
     and **false** here — the two Fourier axes together do keep the sign. What
     is actually lost is which of the pair is the target, plus half the
     amplitude and half the unambiguous range.) A real cube therefore raises,
     and the message names the fix.
  * **Units are in every parameter name** — ``_m``, ``_ms`` (metres per second),
     ``_s``, ``_hz``, ``_deg``. A wavelength/frequency swap or a km/h/(m/s) swap
     is a plausible-wrong answer, not a crash; see the honest-limits section.

Deliberately **not** here (owned elsewhere, imported or composed, never
re-implemented):

  * **Ray geometry** — where the surfaces are, and which ray hits what, is
    ``lidar_sim`` / ``pseudo_lidar``. Nothing here casts a ray; this module takes
    ranges as *given* and produces the signal a coherent sensor would sample.
  * **Direct time-of-flight** is :mod:`photoncount` (``dtof_*``, ``tcspc_*``).
    Same physical quantity — distance — from the opposite principle: dToF counts
    **photon arrival times** and reads distance off a non-negative *count*
    histogram, ``d = c*t/2``. FMCW measures the **phase** of a returned wave and
    reads distance off a complex beat *frequency*, ``f_b = 2SR/c``. The types
    stay separate for that reason (see :mod:`opsrangedoppler` for the measured
    justification): a photon histogram cube is real and non-negative, a beat cube
    is complex, and neither can be interpreted as the other. dToF has no velocity
    axis at all; FMCW cannot count single photons.
  * **1-D spectra, filtering, peak finding** are :mod:`dsp` and :mod:`funct1d`.
    :func:`fmcw_range_profile` and :func:`beamform_delay_sum` both return a plain
    1-D float64 array, so those ops apply to the result directly and are not
    re-wrapped here.
  * **General 2-D image processing** is the rest of Fullseye. A range-Doppler map
    is a plain 2-D float64 array on purpose: thresholding, morphology, labelling
    and blob measurement are exactly what a CFAR-style detector is built from,
    and they already exist.
  * **Windows** are the four textbook ones (F. J. Harris, "On the use of windows
    for harmonic analysis with the discrete Fourier transform", *Proc. IEEE*
    66(1):51-83, 1978), written out in three lines of numpy each rather than
    pulled from ``scipy.signal.get_window`` — the periodic (DFT-even) form is
    required for the sidelobe figures to hold, and that is one keyword away from
    the symmetric form that does not.

Honest disclosure (what these ops cannot do):

  * **The beat model drops the residual video phase.** The exact dechirped phase
    contains a ``pi*S*tau^2`` term; it is omitted here, as in every textbook
    treatment, because ``S*tau^2`` is ~1e-10 cycles at the ranges this module is
    parameterised for. It is *not* negligible for a very long-range, very
    high-slope configuration, and nothing here warns you about that.
  * **Range-Doppler coupling is not modelled.** The target is taken to sit in one
    range bin for the whole coherent processing interval. A target that migrates
    across range bins during the acquisition smears, and this forward model does
    not produce that smear.
  * **No propagation, no radar equation, no clutter.** *amplitudes* are whatever
    you pass in. There is no ``1/R^4``, no atmospheric loss, no ground return, no
    multipath, and no receiver noise figure — only an optional additive circular
    Gaussian noise term with an explicit sigma.
  * **The beamformer is the classical one.** Delay-and-sum resolution is set by
    the aperture (``~0.886*lambda/(N*d)`` at boresight); it cannot separate two
    targets inside one beamwidth. Super-resolution estimators (MUSIC, ESPRIT) are
    a different contract — they need a covariance estimate and a model order, and
    they fail differently — so they are not smuggled in behind the same name.
  * **A unit swap that stays inside the unambiguous window is undetectable.**
    Passing km/h where m/s is expected is caught *only* when the number exceeds
    the maximum unambiguous velocity, which it usually does (that check is the
    guard, and it is tested). A wavelength given as a carrier frequency is caught
    by :data:`MAX_WAVELENGTH_M`, which is a bound, not a proof.

Fail-closed on untrusted input, like every Fullseye module: a real-valued cube, a
range or velocity or angle outside its unambiguous window, a zero chirp slope, a
single-chirp acquisition (no velocity axis exists), a single-element array (no
aperture exists), an all-zero map (no cell to detect), NaN/Inf anywhere, a string
or bool or complex where a scalar belongs — each raises a ``ValueError`` naming
the problem. Sizes are capped (:data:`MAX_CUBE_ELEMENTS`, :data:`MAX_SAMPLES`,
:data:`MAX_CHIRPS`, :data:`MAX_ANTENNAS`, :data:`MAX_TARGETS`,
:data:`MAX_ANGLES`) and **the cap is applied before the complex128 promotion**,
so a mistyped exponent fails instead of allocating the machine's memory.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "fmcw_design", "fmcw_beat_simulate", "fmcw_window_apply",
    "range_doppler_map", "range_doppler_peaks", "fmcw_range_profile",
    "beamform_delay_sum", "beamform_doa",
    "RANGEDOPPLER", "SPEED_OF_LIGHT_M_S", "WINDOWS", "WINDOW_AXES",
    "COMBINE_MODES", "MAX_CUBE_ELEMENTS", "MAX_SAMPLES", "MAX_CHIRPS",
    "MAX_ANTENNAS", "MAX_TARGETS", "MAX_ANGLES", "MAX_WAVELENGTH_M",
]

#: The public coherent-ranging operators, by name (introspection / facade wiring).
RANGEDOPPLER = [
    "fmcw_design", "fmcw_beat_simulate", "fmcw_window_apply",
    "range_doppler_map", "range_doppler_peaks", "fmcw_range_profile",
    "beamform_delay_sum", "beamform_doa",
]

#: Speed of light in vacuum, m/s (SI exact since 1983). Ranges here are
#: vacuum/air ranges; a medium of refractive index n divides this.
SPEED_OF_LIGHT_M_S = 299792458.0

#: Window names accepted by :func:`fmcw_window_apply`. Periodic (DFT-even) forms,
#: which is what the published sidelobe figures assume (Harris 1978).
WINDOWS = ("rect", "hann", "hamming", "blackman")

#: Axis roles accepted by :func:`fmcw_window_apply`. Named by *role*, never by
#: number, because the whole point of the check is that the caller may have the
#: axes transposed.
WINDOW_AXES = ("range", "doppler", "both")

#: How the antenna axis is collapsed. ``incoherent`` = mean of magnitudes (angle
#: independent); ``coherent`` = magnitude of the mean (a boresight beam, so an
#: off-boresight target is attenuated by design).
COMBINE_MODES = ("incoherent", "coherent")

#: Largest element count of an ``(A, C, S)`` beat cube. complex128 is 16 bytes —
#: twice float64 — and the 2-D FFT needs several full-size temporaries, so this
#: cap is half of :data:`photoncount.MAX_CUBE_ELEMENTS`: 2^22 elements = 67 MB
#: per complex temporary. The check is applied to the *declared shape*, before
#: any promotion to complex128, because promoting first is how a cap stops
#: stopping anything.
MAX_CUBE_ELEMENTS = 1 << 22

#: Largest fast-time sample count per chirp (a real ADC does 128-8192).
MAX_SAMPLES = 1 << 20

#: Largest slow-time chirp count per frame (a real frame is 32-512).
MAX_CHIRPS = 1 << 16

#: Largest array element count (a real automotive array is 4-192 virtual channels).
MAX_ANTENNAS = 1 << 12

#: Largest number of simulated targets.
MAX_TARGETS = 1 << 16

#: Largest angle grid for the beamformer. The steering matrix is
#: ``n_angles x n_antennas`` complex, so this cap and :data:`MAX_ANTENNAS`
#: multiply.
MAX_ANGLES = 1 << 16

#: Upper bound on an accepted wavelength, metres. This is a **heuristic guard**,
#: not a proof: its only job is to catch the ``lambda``/``f_carrier`` swap, where
#: someone passes 7.7e10 (hertz) into a metres parameter. With that value every
#: aliasing check passes trivially and the velocity axis becomes meaningless
#: while still looking like a picture — the plausible-wrong failure this module
#: exists to refuse. 10 km is far beyond any ranging sensor's carrier.
MAX_WAVELENGTH_M = 1.0e4


# --------------------------------------------------------------------------- #
# fail-closed input helpers (same discipline as optics / photoncount)          #
# --------------------------------------------------------------------------- #
def _finite_scalar(v, name: str) -> float:
    """A real, finite Python float — or ``ValueError`` naming the problem."""
    if np.ma.is_masked(v):
        raise ValueError("%s is a masked value — fill or drop it explicitly"
                         % (name,))
    if isinstance(v, (bool, np.bool_)):
        raise ValueError("%s is a bool — refusing the silent True==1 promotion"
                         % (name,))
    if isinstance(v, (complex, np.complexfloating)):
        raise ValueError("%s is complex — a range / velocity / frequency / time "
                         "is a real quantity here; coercion would silently drop "
                         "the imaginary part" % (name,))
    if isinstance(v, (str, bytes, np.str_, np.bytes_)):
        raise ValueError("%s is a string (%r) — it must be a number; float('77') "
                         "would silently succeed and hide an unparsed "
                         "configuration value" % (name, v))
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real scalar, got %r"
                         % (name, type(v).__name__)) from None
    if not np.isfinite(f):
        raise ValueError("%s must be finite, got %r (NaN/Inf would propagate "
                         "through every bin of every result)" % (name, v))
    return f


def _positive(v, name: str) -> float:
    f = _finite_scalar(v, name)
    if f <= 0.0:
        raise ValueError("%s must be > 0, got %g" % (name, f))
    return f


def _nonneg(v, name: str) -> float:
    f = _finite_scalar(v, name)
    if f < 0.0:
        raise ValueError("%s must be >= 0, got %g" % (name, f))
    return f


def _count(v, name: str, lo: int, hi: int) -> int:
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s must be an int, got %r (a fractional sample / chirp "
                         "/ element count is an input mistake, not something to "
                         "round)" % (name, type(v).__name__))
    n = int(v)
    if n < lo or n > hi:
        raise ValueError("%s must be in [%d, %d], got %d (the cap is there so a "
                         "mistyped exponent fails instead of allocating "
                         "gigabytes)" % (name, lo, hi, n))
    return n


def _seed(v, name: str = "seed") -> int:
    """A non-negative integer seed. There is no ``None`` — determinism is a rule
    here (the chain fuzzer rejects non-deterministic ops)."""
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s must be a non-negative int (determinism is a "
                         "contract in this module — there is no seed=None), got "
                         "%r" % (name, type(v).__name__))
    n = int(v)
    if n < 0:
        raise ValueError("%s must be >= 0, got %d" % (name, n))
    return n


def _bool(v, name: str) -> bool:
    if not isinstance(v, (bool, np.bool_)):
        raise ValueError("%s must be a bool, got %r" % (name, type(v).__name__))
    return bool(v)


def _wavelength(v, name: str = "wavelength_m") -> float:
    """A positive, finite wavelength in **metres**, bounded by MAX_WAVELENGTH_M.

    The bound exists for exactly one failure: passing the carrier *frequency*
    (e.g. ``77e9``) into a metres parameter. Every aliasing check then passes,
    the Doppler axis silently becomes meaningless, and the map still looks like
    a map. See :data:`MAX_WAVELENGTH_M`.
    """
    f = _positive(v, name)
    if f > MAX_WAVELENGTH_M:
        raise ValueError(
            "%s = %g m is larger than the %g m bound. A ranging sensor's "
            "wavelength is millimetres (radar) to micrometres (lidar); a value "
            "this large is almost always a carrier *frequency* in hertz passed "
            "into a metres parameter — lambda = c/f, so 77e9 Hz is 3.894e-3 m. "
            "Nothing here converts units behind your back."
            % (name, f, MAX_WAVELENGTH_M))
    return f


def _as_float_1d(v, name: str, op: str, cap: int, min_len: int = 1) -> np.ndarray:
    """A finite 1-D float64 vector, refusing the silent-coercion traps.

    ``np.asarray(["77"], float)`` succeeds, so the dtype of the *raw* input is
    inspected before any cast: strings, objects, bools and complex are refused by
    kind rather than discovered later as a wrong number.
    """
    if np.ma.is_masked(v):
        raise ValueError("%s: %s is a masked array with masked (invalid) entries "
                         "— coercion would strip the mask and use the raw values "
                         "underneath; fill or drop them explicitly" % (op, name))
    raw = np.asarray(v)
    kind = raw.dtype.kind
    if kind in ("U", "S", "O"):
        raise ValueError("%s: %s has dtype %r (strings/objects) — float('77') "
                         "succeeds, so an unparsed configuration value would "
                         "become a silent measurement. Convert it explicitly."
                         % (op, name, raw.dtype.str))
    if kind == "b":
        raise ValueError("%s: %s is a boolean array — refusing the silent "
                         "True==1.0 promotion" % (op, name))
    if kind == "c":
        raise ValueError("%s: %s is complex — coercion to float64 would silently "
                         "discard the imaginary part; take .real explicitly"
                         % (op, name))
    arr = np.atleast_1d(np.asarray(raw, dtype=np.float64))
    if arr.ndim != 1:
        raise ValueError("%s: %s must be a 1-D list of values, got a %d-D array "
                         "of shape %r — nothing is flattened silently"
                         % (op, name, arr.ndim, tuple(arr.shape)))
    if arr.size < min_len:
        raise ValueError("%s: %s must have at least %d value(s), got %d"
                         % (op, name, min_len, arr.size))
    if arr.size > cap:
        raise ValueError("%s: %s has %d entries, over the %d cap"
                         % (op, name, arr.size, cap))
    if not np.isfinite(arr).all():
        n = int((~np.isfinite(arr)).sum())
        raise ValueError("%s: %s has %d non-finite value(s) (NaN/Inf) — refusing"
                         % (op, name, n))
    return arr


def _as_beat_cube(a, name: str, op: str) -> np.ndarray:
    """A finite ``(A, C, S)`` **complex** beat cube, size-capped before promotion.

    Order of the checks is load-bearing:

      1. the *declared* shape is read without touching the data, so the element
         cap bites before ``complex128`` doubles a complex64 input (or widens an
         int8 one by 16x);
      2. only then is the dtype kind inspected — a real cube is refused, because
         a real-sampled beat spectrum is conjugate-symmetric and the sign of the
         Doppler shift is not merely noisy in it, it is *absent*;
      3. only then is the array materialised and checked for NaN/Inf.
    """
    if np.ma.is_masked(a):
        raise ValueError("%s: %s is a masked array with masked (invalid) entries "
                         "— fill or drop them explicitly" % (op, name))
    shape = getattr(a, "shape", None)
    if shape is None:
        shape = np.shape(a)
    shape = tuple(int(s) for s in shape)
    if len(shape) != 3:
        raise ValueError(
            "%s: %s must be a 3-D beat cube (n_antennas, n_chirps, n_samples) — "
            "antenna first, slow time (chirp) in the middle, **fast time last** "
            "— got a %d-D array of shape %r. A single-antenna acquisition is "
            "(1, C, S), not (C, S); nothing is reshaped silently."
            % (op, name, len(shape), shape))
    size = int(np.prod(shape)) if shape else 0
    if size > MAX_CUBE_ELEMENTS:
        raise ValueError(
            "%s: %s is %dx%dx%d = %d elements, over the %d cap "
            "(rangedoppler.MAX_CUBE_ELEMENTS, ~%d MB per complex128 temporary "
            "and the 2-D FFT needs several)"
            % (op, name, shape[0], shape[1], shape[2], size, MAX_CUBE_ELEMENTS,
               MAX_CUBE_ELEMENTS * 16 // (1 << 20)))
    if shape[0] < 1:
        raise ValueError("%s: %s has %d antenna(s); at least 1 is needed"
                         % (op, name, shape[0]))
    if shape[1] < 2:
        raise ValueError(
            "%s: %s has %d chirp(s). At least 2 are needed for a velocity axis "
            "to exist at all — a single-chirp acquisition has one Doppler bin, "
            "and reporting that bin as 'v = 0' would label every target static "
            "no matter how fast it moves." % (op, name, shape[1]))
    if shape[2] < 2:
        raise ValueError(
            "%s: %s has %d fast-time sample(s) per chirp. At least 2 are needed "
            "for a range axis to exist. If your cube is (n_samples, n_chirps, "
            "n_antennas), transpose it — fast time is the LAST axis here."
            % (op, name, shape[2]))
    if not np.iscomplexobj(a):
        raise ValueError(
            "%s: %s is real-valued (dtype %r). A beat cube must be the complex "
            "(I/Q) signal: the spectrum of a real-sampled beat is conjugate-"
            "symmetric, so an approaching and a receding target land in the SAME "
            "Doppler bin and the sign of the velocity is not attenuated — it is "
            "absent. Nothing here invents it: form the analytic signal "
            "explicitly (scipy.signal.hilbert along the fast-time axis) or "
            "sample I and Q."
            % (op, name, np.asarray(a).dtype.str))
    arr = np.ascontiguousarray(a, dtype=np.complex128)
    if not np.isfinite(arr).all():
        n = int((~np.isfinite(arr)).sum())
        raise ValueError("%s: %s has %d non-finite value(s) (NaN/Inf) — refusing"
                         % (op, name, n))
    return arr


def _as_map(a, name: str, op: str) -> np.ndarray:
    """A finite, non-negative, size-capped 2-D magnitude map."""
    if np.ma.is_masked(a):
        raise ValueError("%s: %s is a masked array with masked (invalid) entries "
                         "— fill or drop them explicitly" % (op, name))
    if np.iscomplexobj(a):
        raise ValueError("%s: %s is complex — a range-Doppler *map* is a "
                         "magnitude (or power) image; coercion would silently "
                         "drop the imaginary part. Take abs() explicitly."
                         % (op, name))
    shape = getattr(a, "shape", None)
    if shape is None:
        shape = np.shape(a)
    shape = tuple(int(s) for s in shape)
    if len(shape) != 2:
        raise ValueError("%s: %s must be a 2-D (n_doppler, n_range) map, got a "
                         "%d-D array of shape %r" % (op, name, len(shape), shape))
    size = int(np.prod(shape)) if shape else 0
    if size > MAX_CUBE_ELEMENTS:
        raise ValueError("%s: %s has %d elements (shape %r), over the %d cap"
                         % (op, name, size, shape, MAX_CUBE_ELEMENTS))
    arr = np.ascontiguousarray(a, dtype=np.float64)
    if not np.isfinite(arr).all():
        n = int((~np.isfinite(arr)).sum())
        raise ValueError("%s: %s has %d non-finite value(s) (NaN/Inf) — refusing"
                         % (op, name, n))
    neg = int((arr < 0.0).sum())
    if neg:
        raise ValueError("%s: %s has %d negative value(s) (min %g) — a magnitude "
                         "map cannot be negative. If this is a dB map, it is not "
                         "a magnitude; convert it explicitly."
                         % (op, name, neg, float(arr.min())))
    return arr


def _check_mode(mode, allowed, name: str, op: str) -> str:
    if not isinstance(mode, str):
        raise ValueError("%s: %s must be one of %r, got %r"
                         % (op, name, list(allowed), type(mode).__name__))
    m = mode.strip().lower()
    if m not in allowed:
        raise ValueError("%s: %s must be one of %r, got %r"
                         % (op, name, list(allowed), mode))
    return m


def _window_1d(name: str, n: int) -> np.ndarray:
    """Periodic (DFT-even) window of length *n* — Harris 1978, Table 1.

    Periodic, not symmetric: ``w[k] = f(2*pi*k/n)`` for ``k = 0..n-1``. The
    symmetric form (``n-1`` in the denominator, which is what ``np.hanning``
    returns) is the right window for filter design and the *wrong* one for
    spectral analysis — it leaves a discontinuity of one sample in the periodic
    extension, and the published sidelobe levels do not hold for it.
    """
    k = np.arange(n, dtype=np.float64)
    th = 2.0 * np.pi * k / float(n)
    if name == "rect":
        return np.ones(n, dtype=np.float64)
    if name == "hann":
        return 0.5 - 0.5 * np.cos(th)
    if name == "hamming":
        return 0.54 - 0.46 * np.cos(th)
    if name == "blackman":
        return 0.42 - 0.5 * np.cos(th) + 0.08 * np.cos(2.0 * th)
    raise ValueError("unknown window %r" % (name,))       # unreachable via _check_mode


def _spacing(element_spacing_m, wavelength_m: float, op: str) -> float:
    """Element spacing in metres; ``None`` means the half-wavelength standard."""
    if element_spacing_m is None:
        return 0.5 * wavelength_m
    return _positive(element_spacing_m, "element_spacing_m")


def _beamwidth_rad(n_antennas: int, spacing_m: float, wavelength_m: float) -> float:
    """Boresight 3 dB beamwidth of a uniform linear array (Van Trees 2002, §2.4)."""
    return 0.886 * wavelength_m / (n_antennas * spacing_m)


def _require_aperture(na: int, d: float, lam: float, op: str, first_angle: float):
    """Refuse an array that cannot resolve a direction at all.

    Two separate ways to have no aperture, and both end in the same fabricated
    answer — a spectrum that is flat (or wider than the visible region), whose
    ``argmax`` returns the *first grid point* as a confident direction:

      * one element (no baseline at all);
      * many elements packed into much less than a wavelength. Measured: 8
        elements at 1e-12 m spacing give an angle spectrum whose peak-to-trough
        spread is exactly 0.0, and the reported direction was -90 deg — the
        first grid angle. The nominal beamwidth there is 2.5e10 degrees, a
        number the design op used to return without comment.

    The condition is ``0.886*lambda/(N*d) < pi``, i.e. an aperture longer than
    about 0.28 wavelengths.
    """
    if na < 2:
        raise ValueError(
            "%s: the cube has %d antenna element(s). Direction of arrival needs "
            "an aperture: with one element the steering sum is |x_0| for every "
            "angle, the spectrum is exactly flat, and argmax would report "
            "%g degrees — the first grid point — as a confident direction. "
            "Refusing instead of fabricating one." % (op, na, first_angle))
    bw = _beamwidth_rad(na, d, lam)
    if not bw < np.pi:
        raise ValueError(
            "%s: %d elements at %g m spacing span an aperture of %g wavelengths, "
            "whose boresight beamwidth is %g degrees — wider than the entire "
            "visible hemisphere. The angle spectrum is then flat to within "
            "float noise and argmax would report %g degrees (the first grid "
            "point) as a direction. An array shorter than ~0.28 wavelengths has "
            "no directivity; refusing instead of fabricating one."
            % (op, na, d, na * d / lam, float(np.degrees(bw)), first_angle))


def _fft_checked(a, axis, op: str, what: str) -> np.ndarray:
    """``np.fft.fft`` that refuses to return a silent NaN.

    An FFT of an ``N``-point signal can be ``N`` times its largest sample, so a
    finite cube can transform to Inf and then — through the complex arithmetic —
    to NaN. Measured: ``fmcw_beat_simulate(amplitudes=[1e307])`` produces a cube
    that passes every finiteness check, after which ``range_doppler_map``
    returned a map whose maximum was ``nan``, with nothing but a numpy
    ``RuntimeWarning`` to say so. The warning is suppressed here *only* around
    the transform, and immediately replaced by an explicit refusal that names
    the cause — trading an inscrutable warning plus a poisoned array for a
    ValueError.
    """
    import warnings                                       # noqa: PLC0415
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        out = np.fft.fft(a, axis=axis)
    if not np.isfinite(out).all():
        raise ValueError(
            "%s: the %s transform overflowed to Inf/NaN. An N-point FFT can be N "
            "times the largest sample, and the largest |value| going in was %g "
            "over %d points. Scale the data (the amplitudes are yours to choose "
            "— there is no radar equation here) instead of accepting a map full "
            "of NaN." % (op, what, float(np.abs(a).max()), a.shape[axis]))
    return out


def _angle_grid(angles_deg, op: str) -> np.ndarray:
    """The steering grid, defaulting to 1-degree steps over the full hemisphere."""
    if angles_deg is None:
        return np.arange(-90.0, 90.5, 1.0)
    g = _as_float_1d(angles_deg, "angles_deg", op, MAX_ANGLES, min_len=2)
    if float(np.abs(g).max()) > 90.0:
        raise ValueError("%s: angles_deg must lie in [-90, 90] degrees (measured "
                         "from array boresight), got min %g / max %g"
                         % (op, float(g.min()), float(g.max())))
    # A "local maximum of the spectrum" only means anything on an ordered grid:
    # on a scrambled one, adjacency in the array is not adjacency in angle. No
    # wrong *number* could be produced from an unordered grid in testing (the
    # peaks are ranked by power and the fallback is argmax), but the returned
    # (grid_deg, spectrum) pair would be a scrambled curve, so the contract is
    # stated up front rather than left to luck.
    if not np.all(np.diff(g) > 0.0):
        raise ValueError("%s: angles_deg must be strictly increasing — a local "
                         "maximum of the angle spectrum is only defined on an "
                         "ordered grid. Sort it explicitly." % (op,))
    return g


# --------------------------------------------------------------------------- #
# design: the limits, in closed form, before any data exists                    #
# --------------------------------------------------------------------------- #
def fmcw_design(n_samples=64, n_chirps=32, sample_rate_hz=1.0e7,
                slope_hz_per_s=2.0e13, chirp_period_s=5.0e-5,
                wavelength_m=3.8934e-3, n_antennas=1, element_spacing_m=None):
    """Bin widths, resolutions and aliasing limits of an FMCW configuration.

    The paper answer to "will this waveform see what I care about?", with no data
    and no simulation — the stance :mod:`visiondesign` takes for optics. Every
    number is closed form:

    ==============================  ============================================
    quantity                        formula
    ==============================  ============================================
    swept bandwidth                 ``B = S * N_s / f_s``
    range bin / resolution          ``dR = c / (2B) = c*f_s / (2*S*N_s)``
    max unambiguous range           ``R_max = c*f_s / (2S)`` (``= N_s * dR``)
    beat frequency per metre        ``2S/c``
    velocity bin / resolution       ``dv = lambda / (2*N_c*T_c)``
    max unambiguous velocity        ``v_max = lambda / (4*T_c)`` (``= N_c*dv/2``)
    Doppler phase per (m/s)         ``4*pi*T_c / lambda`` rad per chirp
    coherent processing interval    ``N_c * T_c``
    max unambiguous angle           ``asin(lambda / (2d))``
    angular resolution (boresight)  ``0.886 * lambda / (N_a * d)``
    ==============================  ============================================

    The two "max" figures are **hard aliasing limits**, and they are the same
    numbers :func:`fmcw_beat_simulate` refuses to cross. The angular resolution
    is the 3 dB beamwidth of a uniform linear array at boresight (Van Trees 2002,
    §2.4); it widens as ``1/cos(theta)`` off boresight, which this does not report
    because it is a function, not a number.

    ``cube_elements`` and ``cube_mebibytes`` are included because "small input,
    huge allocation" is the failure mode of this family: the cube grows as
    ``N_a * N_c * N_s`` and complex128 is 16 bytes a sample.

    Returns a ``dict``. Raises ``ValueError`` on a non-positive or non-finite
    parameter, a wavelength over :data:`MAX_WAVELENGTH_M`, or a count outside its
    cap.

    >>> d = fmcw_design()
    >>> round(d["range_bin_m"], 6), round(d["max_unambiguous_velocity_ms"], 6)
    (1.171064, 19.467)
    """
    ns = _count(n_samples, "n_samples", 2, MAX_SAMPLES)
    nc = _count(n_chirps, "n_chirps", 2, MAX_CHIRPS)
    na = _count(n_antennas, "n_antennas", 1, MAX_ANTENNAS)
    fs = _positive(sample_rate_hz, "sample_rate_hz")
    s = _positive(slope_hz_per_s, "slope_hz_per_s")
    tc = _positive(chirp_period_s, "chirp_period_s")
    lam = _wavelength(wavelength_m)
    d = _spacing(element_spacing_m, lam, "fmcw_design")

    c = SPEED_OF_LIGHT_M_S
    sampled_s = ns / fs
    bandwidth = s * sampled_s
    range_bin = c * fs / (2.0 * s * ns)
    r_max = c * fs / (2.0 * s)
    vel_bin = lam / (2.0 * nc * tc)
    v_max = lam / (4.0 * tc)
    sin_max = min(1.0, lam / (2.0 * d))
    elements = na * nc * ns
    return {
        "n_samples": ns, "n_chirps": nc, "n_antennas": na,
        "sample_rate_hz": fs, "slope_hz_per_s": s, "chirp_period_s": tc,
        "wavelength_m": lam, "element_spacing_m": d,
        "carrier_frequency_hz": c / lam,
        # range axis
        "sampled_duration_s": sampled_s,
        "sweep_bandwidth_hz": bandwidth,
        "range_bin_m": range_bin,
        "range_resolution_m": c / (2.0 * bandwidth),
        "max_unambiguous_range_m": r_max,
        "beat_hz_per_metre": 2.0 * s / c,
        # velocity axis
        "coherent_processing_interval_s": nc * tc,
        "velocity_bin_ms": vel_bin,
        "velocity_resolution_ms": vel_bin,
        "max_unambiguous_velocity_ms": v_max,
        "doppler_rad_per_chirp_per_ms": 4.0 * np.pi * tc / lam,
        # angle axis. angular_resolution_deg is **None**, not a number, when the
        # array cannot resolve a direction at all (one element, or an aperture
        # under ~0.28 wavelengths): the formula still evaluates there — it
        # returned 2.5e10 degrees for an 8-element array at 1e-12 m spacing —
        # and a number that large is a plausible-wrong answer, not a limit.
        "max_unambiguous_angle_deg": float(np.degrees(np.arcsin(sin_max))),
        "angular_resolution_deg": (
            None if na < 2 or not _beamwidth_rad(na, d, lam) < np.pi
            else float(np.degrees(_beamwidth_rad(na, d, lam)))),
        "aperture_wavelengths": na * d / lam,
        "grating_lobe_free": bool(d <= 0.5 * lam),
        # memory
        "cube_elements": int(elements),
        "cube_mebibytes": elements * 16.0 / float(1 << 20),
        "within_cube_cap": bool(elements <= MAX_CUBE_ELEMENTS),
    }


# --------------------------------------------------------------------------- #
# simulate: the forward model that supplies the ground truth                    #
# --------------------------------------------------------------------------- #
def fmcw_beat_simulate(ranges_m=(10.0,), velocities_ms=(0.0,), angles_deg=None,
                       amplitudes=None, n_samples=64, n_chirps=32, n_antennas=1,
                       sample_rate_hz=1.0e7, slope_hz_per_s=2.0e13,
                       chirp_period_s=5.0e-5, wavelength_m=3.8934e-3,
                       element_spacing_m=None, phase_deg=0.0, noise_sigma=0.0,
                       seed=0):
    """Synthesise the complex ``(A, C, S)`` beat cube for known targets.

    The forward model. Every target ``t`` contributes

    ``a_t * exp(1j*(2*pi*f_b_t*n/f_s + 2*pi*f_d_t*m*T_c + 2*pi*d*k*sin(th_t)/lam + phi))``

    over fast-time sample ``n``, chirp ``m`` and antenna ``k``, with
    ``f_b = 2*S*R/c`` and ``f_d = 2*v/lambda``. Contributions add linearly, which
    is what makes a multi-target cube a valid ground truth: each target's peak
    stands at its own bin regardless of the others.

    **Sign conventions** (see the module docstring): ``velocities_ms`` is
    ``dR/dt``, so **positive is receding** and lands in a positive Doppler bin;
    ``angles_deg`` is measured from array boresight and a positive angle advances
    the phase of the higher-index elements.

    *amplitudes* defaults to 1.0 for every target — there is no radar equation
    here, no ``1/R^4``, no propagation loss (module docstring, honest limits).
    *noise_sigma* adds circular complex Gaussian noise with that per-component
    standard deviation, drawn from ``numpy.random.default_rng(seed)``; the
    default 0.0 returns the exact noiseless cube, which is what the closed-form
    tests compare against.

    Ground truth: a target placed at an exact bin centre — ``R = j*dR`` and
    ``v = i*dv`` from :func:`fmcw_design` — puts the whole of its energy in bin
    ``(i, j)`` of :func:`range_doppler_map`, whose peak magnitude is then exactly
    ``a * N_s * N_c``. Measured on the default configuration: the peak magnitude
    is bit-exactly 2048.0 (``N_s*N_c``, relative error 0.0), the largest other
    cell in the map is 2.6e-16 of it, and with three targets at different bins
    and different amplitudes the recovered ranges and velocities are exact to
    0.0 metres and 0.0 m/s with amplitudes within 5.6e-17. See
    ``tests/test_rangedoppler.py``.

    **Raises** ``ValueError``: a range at or beyond ``c*f_s/(2S)``, a speed at or
    beyond ``lambda/(4*T_c)``, an angle at or beyond ``asin(lambda/(2d))`` — the
    three aliasing limits, refused rather than folded silently; a non-positive
    range; mismatched target-list lengths; a cube over
    :data:`MAX_CUBE_ELEMENTS` (checked *before* allocation); a negative
    amplitude or noise sigma; a non-integer seed; and the usual
    string/bool/complex/NaN scalar refusals.
    """
    op = "fmcw_beat_simulate"
    ns = _count(n_samples, "n_samples", 2, MAX_SAMPLES)
    nc = _count(n_chirps, "n_chirps", 2, MAX_CHIRPS)
    na = _count(n_antennas, "n_antennas", 1, MAX_ANTENNAS)
    fs = _positive(sample_rate_hz, "sample_rate_hz")
    s = _positive(slope_hz_per_s, "slope_hz_per_s")
    tc = _positive(chirp_period_s, "chirp_period_s")
    lam = _wavelength(wavelength_m)
    d = _spacing(element_spacing_m, lam, op)
    phi0 = np.radians(_finite_scalar(phase_deg, "phase_deg"))
    sigma = _nonneg(noise_sigma, "noise_sigma")
    sd = _seed(seed)

    # The cap is checked on the *requested* geometry, before anything is
    # allocated — a small argument list must not be able to ask for a huge cube.
    total = na * nc * ns
    if total > MAX_CUBE_ELEMENTS:
        raise ValueError(
            "%s: the cube would be %dx%dx%d = %d elements, over the %d cap "
            "(rangedoppler.MAX_CUBE_ELEMENTS, ~%d MB per complex128 temporary). "
            "Reduce n_antennas / n_chirps / n_samples."
            % (op, na, nc, ns, total, MAX_CUBE_ELEMENTS,
               MAX_CUBE_ELEMENTS * 16 // (1 << 20)))

    rr = _as_float_1d(ranges_m, "ranges_m", op, MAX_TARGETS)
    vv = _as_float_1d(velocities_ms, "velocities_ms", op, MAX_TARGETS)
    nt = rr.size
    if vv.size != nt:
        raise ValueError("%s: velocities_ms has %d entries but ranges_m has %d — "
                         "one velocity per target, nothing is broadcast silently"
                         % (op, vv.size, nt))
    if angles_deg is None:
        aa = np.zeros(nt)
    else:
        aa = _as_float_1d(angles_deg, "angles_deg", op, MAX_TARGETS)
        if aa.size != nt:
            raise ValueError("%s: angles_deg has %d entries but ranges_m has %d"
                             % (op, aa.size, nt))
    if amplitudes is None:
        amp = np.ones(nt)
    else:
        amp = _as_float_1d(amplitudes, "amplitudes", op, MAX_TARGETS)
        if amp.size != nt:
            raise ValueError("%s: amplitudes has %d entries but ranges_m has %d"
                             % (op, amp.size, nt))
        if (amp < 0.0).any():
            raise ValueError("%s: amplitudes has %d negative value(s) (min %g) — "
                             "an amplitude is non-negative; put the sign in "
                             "phase_deg if you mean a 180-degree phase flip"
                             % (op, int((amp < 0.0).sum()), float(amp.min())))

    c = SPEED_OF_LIGHT_M_S
    r_max = c * fs / (2.0 * s)
    v_max = lam / (4.0 * tc)
    sin_max = lam / (2.0 * d)

    if (rr <= 0.0).any():
        raise ValueError("%s: ranges_m has %d non-positive value(s) (min %g) — a "
                         "range must be > 0 metres"
                         % (op, int((rr <= 0.0).sum()), float(rr.min())))
    bad = rr >= r_max
    if bad.any():
        raise ValueError(
            "%s: %d target(s) at up to %g m are at or past the maximum "
            "unambiguous range %g m (= c*f_s/(2S) with f_s=%g Hz, S=%g Hz/s). "
            "Their beat frequency exceeds the sample rate and they would fold "
            "back to a SHORT range — a plausible-wrong answer, so this refuses "
            "instead. Raise sample_rate_hz or lower slope_hz_per_s."
            % (op, int(bad.sum()), float(rr[bad].max()), r_max, fs, s))
    badv = np.abs(vv) >= v_max
    if badv.any():
        raise ValueError(
            "%s: %d target(s) at up to |v| = %g m/s are at or past the maximum "
            "unambiguous velocity %g m/s (= lambda/(4*T_c) with lambda=%g m, "
            "T_c=%g s). The Doppler phase advance exceeds pi per chirp, so they "
            "would fold to the WRONG SIGN or the wrong speed. If %g looks like a "
            "speed in km/h, this module wants metres per second."
            % (op, int(badv.sum()), float(np.abs(vv[badv]).max()), v_max, lam, tc,
               float(np.abs(vv[badv]).max())))
    # |theta| <= 90 must be checked BEFORE sin(): sin() folds the rear
    # hemisphere onto the front one, so a target requested at 95 deg would be
    # synthesised bit-identically to one at 85 deg and beamformed back as 85 —
    # a plausible-wrong answer with no diagnostic. (Found by the adversarial
    # pass; minimal reproduction in tests/test_rangedoppler.py.)
    outside = np.abs(aa) > 90.0
    if outside.any():
        raise ValueError(
            "%s: %d angle(s) up to |%g| deg lie outside [-90, 90]. Angles are "
            "measured from array boresight, and a linear array has no rear "
            "hemisphere: sin() would fold 95 deg onto 85 deg and 190 deg onto "
            "-10 deg, producing a cube identical to a different scene's. "
            "Refusing rather than folding silently."
            % (op, int(outside.sum()), float(np.abs(aa[outside]).max())))
    sin_t = np.sin(np.radians(aa))
    bada = np.abs(sin_t) >= sin_max
    if bada.any():
        raise ValueError(
            "%s: %d target(s) at up to |theta| = %g deg exceed the array's "
            "unambiguous field |sin theta| < lambda/(2d) = %g (element spacing "
            "%g m, lambda %g m). Beyond it a grating lobe is indistinguishable "
            "from the main lobe. Reduce element_spacing_m."
            % (op, int(bada.sum()), float(np.abs(aa[bada]).max()),
               min(1.0, sin_max), d, lam))

    n_idx = np.arange(ns, dtype=np.float64)                # fast time
    m_idx = np.arange(nc, dtype=np.float64)                # slow time
    k_idx = np.arange(na, dtype=np.float64)                # array element

    f_b = 2.0 * s * rr / c                                 # Hz
    f_d = 2.0 * vv / lam                                   # Hz
    cube = np.zeros((na, nc, ns), dtype=np.complex128)
    for t in range(nt):
        ph_fast = 2.0 * np.pi * f_b[t] * n_idx / fs        # (S,)
        ph_slow = 2.0 * np.pi * f_d[t] * m_idx * tc        # (C,)
        ph_ant = 2.0 * np.pi * d * sin_t[t] / lam * k_idx  # (A,)
        ph = (ph_ant[:, None, None] + ph_slow[None, :, None]
              + ph_fast[None, None, :] + phi0)
        cube += amp[t] * np.exp(1j * ph)
    if sigma > 0.0:
        rng = np.random.default_rng(sd)
        cube += sigma * (rng.standard_normal(cube.shape)
                         + 1j * rng.standard_normal(cube.shape))
    return cube


# --------------------------------------------------------------------------- #
# process: window, 2-D FFT, detection                                          #
# --------------------------------------------------------------------------- #
def fmcw_window_apply(cube, window="hann", axis="range"):
    """Apply a periodic window along the range and/or Doppler axis of a beat cube.

    The sidelobes of a rectangular (unwindowed) transform are -13.3 dB, so a
    strong target buries a weak one 20 dB down at a completely different range.
    Windowing trades main-lobe width for sidelobe level; the published figures
    (Harris 1978, Table 1) and the levels **measured** in this repository on a
    single bin-centred target are:

    ==========  ==============  ==============  ==================
    window      published PSL   measured PSL    measured -3 dB lobe
    ==========  ==============  ==============  ==================
    rect        -13.3 dB        -13.25 dB       0.885 bin
    hann        -31.5 dB        -31.47 dB       1.438 bin
    hamming     -42.7 dB        -42.45 dB       1.301 bin
    blackman    -58.1 dB        -58.11 dB       1.641 bin
    ==========  ==============  ==============  ==================

    Measured by transforming each window on its own with 2^18-point zero padding
    and taking the highest lobe past the first null — that *is* the definition of
    peak sidelobe level, so these are the module's own numbers, not copied ones.
    Hamming lands 0.25 dB off the published figure because the published one is
    for the optimal 0.53836/0.46164 pair; the 0.54/0.46 coefficients written here
    are the textbook ones and this is what they actually give.

    What it buys, measured end to end: a target 45 dB below a strong one, seven
    range bins away, is **undetectable** unwindowed (its cell sits 24.6 dB down
    in the leakage skirt and is not even a local maximum) and becomes a clean
    local maximum at -43.6 dB with ``hann``. That comparison is step 4 of
    ``examples/fmcw_range_doppler.py``.

    *axis* is named by **role** — ``"range"`` (fast time, the last axis),
    ``"doppler"`` (slow time, the middle axis) or ``"both"`` — never by number,
    because a transposed cube is the mistake this naming is defending against.

    The window is *not* folded into :func:`range_doppler_map`: keeping it a
    separate op is what lets the sidelobe table above be measured as a
    difference, and keeps the transform op a pure 2-D FFT.

    Returns a new complex cube of the same shape. **Raises** ``ValueError`` on a
    real-valued or malformed cube, or an unknown *window* / *axis*.
    """
    op = "fmcw_window_apply"
    arr = _as_beat_cube(cube, "cube", op)
    w = _check_mode(window, WINDOWS, "window", op)
    ax = _check_mode(axis, WINDOW_AXES, "axis", op)
    out = arr.copy()
    if ax in ("range", "both"):
        out = out * _window_1d(w, arr.shape[2])[None, None, :]
    if ax in ("doppler", "both"):
        out = out * _window_1d(w, arr.shape[1])[None, :, None]
    return np.ascontiguousarray(out)


def range_doppler_map(cube, combine="incoherent", antenna=None, normalize=False):
    """The 2-D FFT of a beat cube -> a ``(n_doppler, n_range)`` magnitude map.

    Fast time transforms to **range** (last axis, not shifted: bin ``j`` is
    ``j * c*f_s/(2*S*N_s)`` metres, and a physical range is always positive so
    the whole ``[0, f_s)`` band is used). Slow time transforms to **velocity**
    (middle axis, ``fftshift``ed so the map is centred on zero velocity: bin
    ``i`` is ``(i - N_c//2) * lambda/(2*N_c*T_c)`` metres per second, positive =
    receding).

    The antenna axis is collapsed by *combine*: ``"incoherent"`` (default) is the
    **mean of the magnitudes**, which is angle independent and therefore the
    right default for detection; ``"coherent"`` is the **magnitude of the mean**,
    i.e. a beam pointed at boresight, which attenuates an off-boresight target on
    purpose. ``antenna=k`` uses element ``k`` alone. For a single-element cube
    all three agree exactly.

    ``normalize=True`` divides by ``N_c * N_s``, so a bin-centred target of
    amplitude ``a`` peaks at exactly ``a`` (measured: 1.0 for a unit target,
    absolute error 0.0). The default ``False`` keeps the raw FFT magnitude.

    No window is applied — compose :func:`fmcw_window_apply` first if you want
    one. The output is a plain 2-D float64 array, so every 2-D operator in
    Fullseye (threshold, morphology, labelling, blob measurement — the pieces a
    CFAR detector is made of) applies to it directly.

    **Raises** ``ValueError``: a real-valued cube (the sign of the velocity does
    not exist in a real beat spectrum), fewer than 2 chirps or 2 samples, an
    out-of-range *antenna* index, an unknown *combine*, a cube over the element
    cap, or NaN/Inf.
    """
    op = "range_doppler_map"
    arr = _as_beat_cube(cube, "cube", op)
    mode = _check_mode(combine, COMBINE_MODES, "combine", op)
    norm = _bool(normalize, "normalize")
    na, nc, ns = arr.shape
    if antenna is not None:
        k = _count(antenna, "antenna", 0, na - 1)
        arr = arr[k:k + 1]
        na = 1
    spec = _fft_checked(arr, 2, op, "range (fast time)")
    spec = _fft_checked(spec, 1, op, "Doppler (slow time)")
    spec = np.fft.fftshift(spec, axes=1)               # zero velocity at centre
    if mode == "coherent":
        m = np.abs(spec.mean(axis=0))
    else:
        m = np.abs(spec).mean(axis=0)
    if norm:
        m = m / float(nc * ns)
    return np.ascontiguousarray(m)


def fmcw_range_profile(cube, chirp=None, antenna=None, normalize=False):
    """Range-only profile: the fast-time FFT magnitude, averaged over the rest.

    The 1-D marginal of :func:`range_doppler_map` — what a static scene needs,
    and what a single chirp can give. Magnitudes are averaged (never the complex
    values) over chirps and antennas, so the average is independent of the
    target's velocity and angle: ``|FFT|`` does not rotate with the Doppler
    phase, only the phase does.

    Bin ``j`` is ``j * c*f_s/(2*S*N_s)`` metres. With ``normalize=True`` a
    bin-centred target of amplitude ``a`` peaks at exactly ``a``.

    *chirp* / *antenna* select one slice instead of averaging. Returns a 1-D
    float64 array of length ``n_samples`` — a plain signal, so :mod:`dsp` and
    :mod:`funct1d` (``find_peaks``, ``smooth_funct_1d_gauss``, ``spectrum``)
    apply to it directly.

    **Raises** ``ValueError``: as :func:`range_doppler_map`, plus an
    out-of-bounds *chirp* index.
    """
    op = "fmcw_range_profile"
    arr = _as_beat_cube(cube, "cube", op)
    norm = _bool(normalize, "normalize")
    na, nc, ns = arr.shape
    if antenna is not None:
        arr = arr[_count(antenna, "antenna", 0, na - 1)][None, :, :]
    if chirp is not None:
        arr = arr[:, _count(chirp, "chirp", 0, nc - 1), :][:, None, :]
    prof = np.abs(_fft_checked(arr, 2, op, "range (fast time)")).mean(axis=(0, 1))
    if norm:
        prof = prof / float(ns)
    return np.ascontiguousarray(prof)


def range_doppler_peaks(rdmap, range_bin_m=1.0, velocity_bin_ms=1.0, n_peaks=1,
                        min_fraction=0.1, doppler_shifted=True):
    """Detections from a range-Doppler map: bin indices back to metres and m/s.

    Finds strict local maxima of the 2-D magnitude map — greater than all eight
    neighbours, **cyclically** along the Doppler axis (velocity really is
    periodic in the FFT: the fastest receding bin is adjacent to the fastest
    approaching one) and **openly** along the range axis (a cell in the first or
    last range bin competes only against the neighbours that exist, so a target
    in the last bin is a detection, not a discard) — keeps those at least
    *min_fraction* of the global maximum, and returns the strongest *n_peaks*.

    Range bin 0 is reported like any other. In a real receiver it is the
    transmitter-leakage / DC bin rather than a target, but suppressing it here
    would be a silent policy applied to somebody else's data; threshold it
    yourself if you want it gone.

    Index -> physical value, closed form and the exact inverse of
    :func:`fmcw_beat_simulate`:

      * ``range_m = j * range_bin_m``, with ``range_bin_m = c*f_s/(2*S*N_s)``
        from :func:`fmcw_design`;
      * ``velocity_ms = (i - n_doppler//2) * velocity_bin_ms`` when
        *doppler_shifted* (the layout :func:`range_doppler_map` produces), or
        ``i`` wrapped into ``[-N_c/2, N_c/2)`` when the map is unshifted.

    The bin widths are **required parameters with placeholder defaults of 1.0**,
    which means the default output is in bins, not metres. That is deliberate:
    inventing a default waveform here would let a caller read metres off a map
    that was never that waveform's.

    Returns a ``dict`` with ``peaks`` (a list of per-detection dicts holding
    ``range_m``, ``velocity_ms``, ``magnitude``, ``range_bin``, ``doppler_bin``),
    ``n_found``, ``max_magnitude`` and ``noise_floor`` (the median of the map).

    **Raises** ``ValueError``: a non-2-D, complex, negative, or non-finite map; a
    map whose maximum is 0 (an all-zero map has no cell to detect and returning
    cell (0,0) — which is what ``argmax`` does — would be a fabricated
    detection); a non-positive bin width; *n_peaks* < 1; a *min_fraction*
    outside ``[0, 1]``.
    """
    op = "range_doppler_peaks"
    m = _as_map(rdmap, "rdmap", op)
    dr = _positive(range_bin_m, "range_bin_m")
    dv = _positive(velocity_bin_ms, "velocity_bin_ms")
    npk = _count(n_peaks, "n_peaks", 1, 1 << 20)
    frac = _finite_scalar(min_fraction, "min_fraction")
    shifted = _bool(doppler_shifted, "doppler_shifted")
    if not 0.0 <= frac <= 1.0:
        raise ValueError("%s: min_fraction must be in [0, 1], got %g" % (op, frac))
    nd, nr = m.shape
    if nd < 2 or nr < 2:
        raise ValueError("%s: rdmap is %dx%d; a local maximum needs at least 2 "
                         "cells along each axis" % (op, nd, nr))
    peak = float(m.max())
    if peak <= 0.0:
        raise ValueError(
            "%s: the map's maximum is %g — there is nothing to detect. argmax "
            "would return cell (0, 0) and this op would report a target at "
            "range 0 with velocity %g m/s, which is a fabricated detection, not "
            "a measurement." % (op, peak, -(nd // 2) * dv))

    # Strict local maxima: cyclic along Doppler (velocity is periodic in the
    # FFT), open along range (bin 0 and the last bin have no physical neighbour).
    best = np.full(m.shape, -np.inf)
    # The range axis is padded with -inf rather than masked at the border: an
    # earlier version dropped columns 0 and N-1 outright, which silently
    # discarded a target sitting in the LAST range bin — the strongest cell in
    # the map returned zero detections (found by the adversarial pass). A cell
    # at the edge competes only against the neighbours that exist.
    pad = np.pad(m, ((0, 0), (1, 1)), mode="constant", constant_values=-np.inf)
    for di in (-1, 0, 1):
        rolled = np.roll(pad, di, axis=0)              # cyclic in Doppler
        for dj in (0, 1, 2):
            if di == 0 and dj == 1:
                continue                               # the cell itself
            np.maximum(best, rolled[:, dj:dj + nr], out=best)
    mask = (m > best) & (m >= frac * peak)
    idx = np.argwhere(mask)
    order = np.argsort(-m[mask], kind="stable")
    idx = idx[order][:npk]

    zero = nd // 2 if shifted else 0
    peaks = []
    for i, j in idx:
        k = int(i) - zero
        if not shifted and k >= (nd + 1) // 2:
            k -= nd                                    # unshifted layout wraps
        peaks.append({
            "range_bin": int(j), "doppler_bin": int(k),
            "range_m": float(j) * dr, "velocity_ms": float(k) * dv,
            "magnitude": float(m[i, j]),
        })
    return {"peaks": peaks, "n_found": len(peaks), "max_magnitude": peak,
            "noise_floor": float(np.median(m))}


# --------------------------------------------------------------------------- #
# beamform: the angle axis from a uniform linear array                          #
# --------------------------------------------------------------------------- #
def _cell_snapshot(arr, op, range_bin, doppler_bin):
    """The per-antenna complex value at one range-Doppler cell, + the indices.

    *range_bin* and *doppler_bin* are all-or-nothing. Supplying only one used to
    fall through to "pick the strongest cell", so a caller who asked to beamform
    range bin 20 silently got the angle of the target in bin 3 instead, with the
    returned ``range_bin`` field quietly saying 3 (found by the adversarial pass).
    """
    na, nc, ns = arr.shape
    if (range_bin is None) != (doppler_bin is None):
        raise ValueError(
            "%s: range_bin=%r and doppler_bin=%r — give both to select a cell, "
            "or neither to use the strongest one. Half a cell address cannot be "
            "honoured, and defaulting the other half to the strongest cell would "
            "silently beamform a different target than the one you asked for."
            % (op, range_bin, doppler_bin))
    zero = nc // 2
    spec = np.fft.fftshift(
        _fft_checked(_fft_checked(arr, 2, op, "range (fast time)"), 1, op,
                     "Doppler (slow time)"), axes=1)
    if range_bin is None or doppler_bin is None:
        power = np.abs(spec).mean(axis=0)
        if float(power.max()) <= 0.0:
            raise ValueError(
                "%s: the cube's range-Doppler map is identically zero, so there "
                "is no cell to beamform. argmax would pick cell (0, 0) and the "
                "angle spectrum of a zero snapshot is flat — the reported "
                "direction would be an artefact of tie-breaking, not a "
                "measurement." % (op,))
        di, rj = np.unravel_index(int(np.argmax(power)), power.shape)
    else:
        # doppler_bin is the **signed** velocity bin, the same convention
        # range_doppler_peaks reports and beamform_doa returns, so a detection
        # can be handed straight back in. range_bin is a plain 0..N_s-1 index.
        di = _count(doppler_bin, "doppler_bin", -zero, nc - zero - 1) + zero
        rj = _count(range_bin, "range_bin", 0, ns - 1)
    snap = spec[:, int(di), int(rj)]
    if not np.any(np.abs(snap) > 0.0):
        raise ValueError("%s: the snapshot at cell (doppler=%d, range=%d) is "
                         "identically zero; its angle spectrum would be flat"
                         % (op, int(di), int(rj)))
    return snap, int(di), int(rj)


def beamform_delay_sum(cube, wavelength_m=3.8934e-3, element_spacing_m=None,
                       angles_deg=None, range_bin=None, doppler_bin=None,
                       normalize=False):
    """Delay-and-sum (Bartlett) angle spectrum for one range-Doppler cell.

    Takes the per-antenna complex value at a single range-Doppler cell — by
    default the strongest one — and for each steering angle removes the expected
    inter-element phase and sums:

    ``P(theta) = |sum_k conj(exp(1j*2*pi*d*k*sin(theta)/lambda)) * x_k|^2``

    which peaks at the true arrival angle with value ``(N_a * |a|)^2``: the
    aperture gives ``N_a`` in amplitude, ``N_a^2`` in power. That is the exact
    ground truth the tests pin. Measured with 8 elements: the peak power is
    bit-exactly ``(N_a*N_c*N_s)^2 = 268435456`` (relative error 0.0), and
    sweeping the true angle from -80 to +80 degrees in 5-degree steps (33 cases)
    the reported angle matches the truth with a maximum error of 0.0 degrees.

    The steering grid defaults to ``arange(-90, 90.5, 1.0)``. ``normalize=True``
    divides by ``N_a^2 * N_c^2 * N_s^2`` so that a unit-amplitude bin-centred
    target peaks at 1.0.

    Returns a 1-D float64 array of powers, one per grid angle — a plain signal,
    so :mod:`dsp`'s ``find_peaks`` and :mod:`funct1d`'s smoothing apply to it.
    Use :func:`beamform_doa` if you want the angles themselves.

    *range_bin* is a plain ``0..N_s-1`` index; *doppler_bin* is the **signed**
    velocity bin, the same convention :func:`range_doppler_peaks` reports, so a
    detection can be handed straight back in. Both or neither — half a cell
    address raises rather than quietly beamforming the strongest cell instead.

    **Raises** ``ValueError``: **no aperture** — either a single element, or many
    elements packed into under ~0.28 wavelengths. In both cases the spectrum is
    flat to within float noise and ``argmax`` returns the first grid angle, i.e.
    a confident report of -90 degrees that is pure tie-breaking (measured: 8
    elements at 1e-12 m spacing gave a peak-to-trough spread of exactly 0.0 and
    reported -90.0). Also: an all-zero cube or an all-zero selected cell; only
    one of *range_bin* / *doppler_bin*; an out-of-bounds bin index; an angle grid
    outside ``[-90, 90]``; an FFT that overflows to NaN; plus the usual cube and
    scalar refusals.
    """
    op = "beamform_delay_sum"
    arr = _as_beat_cube(cube, "cube", op)
    lam = _wavelength(wavelength_m)
    d = _spacing(element_spacing_m, lam, op)
    grid = _angle_grid(angles_deg, op)
    norm = _bool(normalize, "normalize")
    na, nc, ns = arr.shape
    _require_aperture(na, d, lam, op, float(grid[0]))
    snap, _, _ = _cell_snapshot(arr, op, range_bin, doppler_bin)
    k = np.arange(na, dtype=np.float64)
    steer = np.exp(-1j * 2.0 * np.pi * d / lam
                   * np.sin(np.radians(grid))[:, None] * k[None, :])
    power = np.abs(steer @ snap) ** 2
    if norm:
        power = power / float(na * nc * ns) ** 2
    return np.ascontiguousarray(power)


def beamform_doa(cube, wavelength_m=3.8934e-3, element_spacing_m=None,
                 angles_deg=None, range_bin=None, doppler_bin=None, n_targets=1,
                 min_fraction=0.1, range_bin_m=None, velocity_bin_ms=None):
    """Direction(s) of arrival for one range-Doppler cell, in degrees.

    :func:`beamform_delay_sum` followed by strict local-maximum picking on the
    angle spectrum: the peaks are sorted by power, filtered at *min_fraction* of
    the strongest, and the top *n_targets* returned. Two targets closer than the
    array's beamwidth (``~0.886*lambda/(N_a*d)``, reported here as
    ``angular_resolution_deg``) merge into one lobe — delay-and-sum cannot
    separate them, and this reports one peak rather than pretending otherwise.

    When *range_bin_m* / *velocity_bin_ms* are supplied (from
    :func:`fmcw_design`) the cell's range and velocity are converted too, giving
    the complete ``(range, velocity, angle)`` detection this family exists to
    produce; without them those two fields are ``None`` rather than a number in
    unknown units.

    Returns a ``dict``: ``angles_deg`` and ``powers`` (lists, strongest first),
    ``n_found``, ``grid_deg`` and ``spectrum`` (the full sweep), ``range_bin`` /
    ``doppler_bin`` (the cell used), ``range_m`` / ``velocity_ms``,
    ``angular_resolution_deg`` and ``max_unambiguous_angle_deg``.

    **Raises** ``ValueError``: everything :func:`beamform_delay_sum` raises, plus
    *n_targets* < 1 or a *min_fraction* outside ``[0, 1]``.
    """
    op = "beamform_doa"
    arr = _as_beat_cube(cube, "cube", op)
    lam = _wavelength(wavelength_m)
    d = _spacing(element_spacing_m, lam, op)
    grid = _angle_grid(angles_deg, op)
    nt = _count(n_targets, "n_targets", 1, MAX_ANGLES)
    frac = _finite_scalar(min_fraction, "min_fraction")
    if not 0.0 <= frac <= 1.0:
        raise ValueError("%s: min_fraction must be in [0, 1], got %g" % (op, frac))
    na = arr.shape[0]
    _require_aperture(na, d, lam, op, float(grid[0]))
    zero = arr.shape[1] // 2
    snap, di, rj = _cell_snapshot(arr, op, range_bin, doppler_bin)
    # di comes back as the *shifted* row index; beamform_delay_sum takes the
    # signed velocity bin, so it must be converted, not forwarded raw.
    power = beamform_delay_sum(arr, lam, d, grid, rj, di - zero)

    top = float(power.max())
    inner = power[1:-1]
    loc = np.zeros(power.size, dtype=bool)
    loc[1:-1] = (inner > power[:-2]) & (inner > power[2:]) & (inner >= frac * top)
    # A monotone spectrum has no interior maximum; the boundary is then the
    # honest answer and is reported as such rather than dropped.
    if not loc.any():
        loc[int(np.argmax(power))] = True
    idx = np.flatnonzero(loc)
    idx = idx[np.argsort(-power[idx], kind="stable")][:nt]

    rng_m = None if range_bin_m is None else rj * _positive(range_bin_m,
                                                            "range_bin_m")
    vel = None if velocity_bin_ms is None else (di - zero) * _positive(
        velocity_bin_ms, "velocity_bin_ms")
    sin_max = min(1.0, lam / (2.0 * d))
    return {
        "angles_deg": [float(grid[i]) for i in idx],
        "powers": [float(power[i]) for i in idx],
        "n_found": int(idx.size),
        "grid_deg": np.asarray(grid, dtype=np.float64),
        "spectrum": np.asarray(power, dtype=np.float64),
        "range_bin": int(rj), "doppler_bin": int(di - zero),
        "range_m": rng_m, "velocity_ms": vel,
        "angular_resolution_deg": float(np.degrees(_beamwidth_rad(na, d, lam))),
        "max_unambiguous_angle_deg": float(np.degrees(np.arcsin(sin_max))),
    }
