# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Coherence-scanning interferometry and chromatic confocal ranging (numpy + scipy only).

The *other* way to turn light into a height. :mod:`fringe` already implements
**phase-shifting** profilometry: the height is read from the fringe *phase*, which
is exquisitely precise and fundamentally ambiguous — a phase is only known modulo
2 pi, so a step taller than a quarter wavelength comes back as a different,
entirely plausible number. This module implements the family that does not have
that ambiguity: the height is read from the position of the **coherence
envelope** along a vertical scan, and an envelope has no periodicity to wrap.

The trade is stated once, in numbers measured by ``tests/test_interferometry.py``
on the same synthetic step (lambda = 0.60 um, so lambda/4 = 0.15 um):

    step height      phase-shifting (fringe)     coherence scanning (here)
    0.150 um         +0.0000 um  (correct)       +0.0000 um  (correct)
    0.200 um         -0.3000 um  (WRONG, silent) -0.0000 um  (correct)
    0.500 um         -0.6000 um  (WRONG, silent) -0.0000 um  (correct)
    1.000 um         -0.9000 um  (WRONG, silent) +0.0000 um  (correct)

The phase-shifting errors are exact multiples of lambda/2 = 0.30 um — one fringe
order — and nothing in its output says so. That is the reason this module exists,
and it is why the comparison is a *test*, not a claim.

Six families of operator:

  * **simulate** — :func:`csi_signal_simulate` / :func:`csi_stack_simulate` /
    :func:`chromatic_confocal_simulate`: the forward model, which is where the
    ground truth comes from. A z-scan interferogram is
    ``a + b*V(z-z0)*cos(4*pi*(z-z0)/lambda)`` with a Gaussian coherence envelope
    ``V``; the factor 4 (not 2) is the double pass down to the surface and back.
  * **envelope** — :func:`csi_envelope`: the analytic-signal (Hilbert) envelope of
    a scan, after the DC pedestal is removed. Removing the pedestal is not
    cosmetic: on the reference signal the envelope error is **1.8e-07** with the
    bias removed and **0.5** (i.e. the whole pedestal) without it — and
    ``dsp.envelope`` applied to the raw interferogram gives that same 0.5, which
    is why this operator exists at all.
  * **locate** — :func:`csi_peak_position`: where along the scan that envelope
    peaks, by four estimators whose biases differ by five orders of magnitude and
    which *swap places* once noise is present (see the table below).
  * **surface** — :func:`csi_height_map` / :func:`csi_contrast_map`: the same
    inversion over a ``(Z, H, W)`` scan stack, giving a height map and the fringe
    modulation (which doubles as the validity / reflectance map).
  * **chromatic** — :func:`chromatic_confocal_height`: the spectral cousin. A
    chromatic lens focuses each wavelength at a different height, so the
    wavelength that comes back through the confocal pinhole *is* the height:
    ``z = z_ref + (lambda - lambda_ref) * dispersion``. No scan, one spectrum.
  * **design** — :func:`csi_design`: the limits, before any hardware exists, in
    the spirit of :mod:`visiondesign` — coherence length from the source
    bandwidth, fringe period, the Nyquist ceiling on the scan step, the capture
    range, and the size of the stack you are about to allocate.

Estimator bias, measured (``tests/test_interferometry.py::test_estimator_bias_table``).
Noiseless, envelope sigma 1.2 um, step 0.05 um, true peak placed at four
sub-step offsets; and the same with 1 % additive noise, 200 trials:

    estimator    noiseless max |error|      noisy RMS error (sigma_n = 0.01)
    peak         2.50e-02 um  (= step/2)    0.1395 um
    centroid     4.55e-07 um                0.0219 um
    parabolic    4.21e-06 um                0.1403 um
    gaussian     1.43e-07 um                0.1403 um

Read that table twice. Noiseless, ``"gaussian"`` is 30x better than
``"parabolic"`` (the logarithm of a sampled Gaussian is *exactly* a parabola, so
the three-point log fit is exact — on the analytic envelope it is exact to 3e-14,
and the 1.43e-07 floor above is the Hilbert envelope's own error, not the fit's).
With noise, ``"centroid"`` wins by 6.4x, because the three local estimators only
look at three samples around an ``argmax`` that noise moves around a broad, flat
envelope, whereas the centroid averages all 241 planes. The default is
``"gaussian"`` because it is the one that is exact when the data is good;
**there is no single best estimator here and the module does not pretend
otherwise.** The centroid's own failure mode is disclosed in
:func:`csi_peak_position`: it is biased by where the peak sits in the scan window
(+0.189 um noiseless, +0.873 um with a 2 % noise floor, when the surface is 2 um
from a 12 um window's edge).

A third number matters more than either: **accuracy here is a property of the
scan layout, not of the estimator.** With the surface centred in the scan the
``"gaussian"`` estimator is exact to 3e-14 um; move it to 2 um from the end of a
12 um scan and the same estimator gives 2.7e-02 um, because part of the coherence
envelope is now outside the scan and the analytic signal is a global transform.
Push further — a surface at 0.500 um — and it returns **0.119 um** without any
first-or-last-plane check firing. That is a silent, plausible, 76 %-wrong answer,
and it is what ``max_edge_envelope`` exists to refuse. Zero-padding and
reflect-padding were both measured as fixes and both made it worse.

Provenance — textbook and cited public literature only, nothing derived from any
commercial instrument (see ``docs/PROVENANCE.md``):

  * P. de Groot, "Principles of interference microscopy for the measurement of
    surface topography", *Advances in Optics and Photonics* 7(1):1-65, 2015 —
    the coherence-scanning signal model and the envelope/phase duality.
  * P. Caber, "Interferometric profiler for rough surfaces", *Applied Optics*
    32(19):3438-3441, 1993 — envelope detection as the rough-surface answer to
    the fringe-order ambiguity.
  * K. G. Larkin, "Efficient nonlinear algorithm for envelope detection in white
    light interferometry", *JOSA A* 13(4):832-843, 1996 — the five-sample
    envelope algorithms this module's Hilbert route is the general case of.
  * M. Born & E. Wolf, *Principles of Optics*, 7th ed., Section 7.5.8 — the
    coherence length of a Gaussian source, ``l_c = (4 ln2 / pi) * lambda^2 /
    delta_lambda`` in **optical path difference** (so half that along the scan
    axis, since the double pass makes OPD = 2z), verified numerically in
    :func:`csi_design`'s test.
  * ISO 25178-604 and ISO 25178-602 — the standard vocabulary for
    coherence-scanning interferometry and for chromatic confocal probes.
  * H. J. Tiziani & H.-M. Uhde, "Three-dimensional image sensing by chromatic
    confocal microscopy", *Applied Optics* 33(10):1838-1843, 1994 — the
    wavelength-to-height mapping.

Units are in every parameter name — ``_um``, ``_nm``, ``_per_nm`` — because a
nanometre/micrometre swap here is a factor of 1000 in a height, which is a
plausible-wrong answer rather than a crash. ``float("0.55")`` succeeds in Python,
so strings, bools and complex numbers are rejected explicitly rather than
coerced.

Deliberately **not** here (owned elsewhere — imported and composed, never
re-implemented):

  * **Phase-shifting interferometry / fringe projection** is :mod:`fringe`
    (``wrapped_phase`` / ``unwrap_phase_2d`` / ``phase_to_height`` /
    ``decode_fringe`` / ``synthesize_fringes``). Nothing here computes a wrapped
    phase, and nothing there detects an envelope. They meet in exactly one place,
    ``tests/test_interferometry.py::test_phase_shifting_breaks_coherence_holds``,
    which drives both from the *same* synthetic surface.
  * **Spatial phase unwrapping** is ``complexops.phase_unwrap`` and
    ``fringe.unwrap_phase_2d``. This module never unwraps, because not needing to
    is the whole point.
  * **Generic 1-D envelopes** are ``dsp.envelope`` (whole-signal Hilbert
    magnitude) and the registered 2-D ``xsp_hilbert_env``. :func:`csi_envelope`
    *calls* ``dsp.envelope`` and adds the one thing an interferogram needs and a
    generic signal does not: removal of the intensity pedestal. Handing a raw
    interferogram straight to ``dsp.envelope`` returns the pedestal, not the
    envelope — measured above, and pinned in the tests.
  * **Filtering, spectra, resampling** of a scan are :mod:`dsp` and
    :mod:`funct1d`; a scan signal is a plain 1-D float64 array and those ops
    apply to it directly, so they are not re-wrapped.
  * **Optical design** (focal length, depth of field, diffraction, MTF) is
    :mod:`optics` and :mod:`visiondesign`. :func:`csi_design` is the *axial*
    counterpart and does not duplicate any of it.

Honest disclosure — what these operators cannot do, measured rather than assumed:

  * **One surface per pixel.** The envelope peak is *a* peak, and a scan that
    crosses two reflectors returns one number that is neither of them: two equal
    surfaces 1.5 um apart come back as 5.75 um when they are at 5.00 and 6.50.
    The same is true of the chromatic path, which picks one of two spectral peaks
    (-5.0 um out of a -5.0/+5.0 pair) and cannot report that there were two.
    Transparent films and multi-layer stacks are exactly this case, and nothing
    here detects it.
  * **Accuracy is set by the scan layout, not by the estimator.** Centre the
    surface in the scan and ``"gaussian"`` is exact to 3e-14 um; leave 2 um of
    margin instead of 6 and the same estimator gives 2.7e-02 um. Both numbers are
    from the same code on the same surface.
  * **Low reflectance costs the local fits 20x.** On a field with a 50x
    reflectance step and 1 % noise the ``"gaussian"`` height error is 0.146 um RMS
    on the bright half and 3.03 um RMS on the dark half (``"centroid"``: 0.022 ->
    0.157 um, so 7x rather than 20x). :func:`csi_contrast_map` is what separates
    the two populations.
  * **One unit error remains undetectable, and it is named here rather than
    hidden.** ``chromatic_confocal_height``'s *dispersion_um_per_nm* is a property
    of the objective, not of the data, so nothing in the spectrum can contradict
    it: pass it per micrometre instead of per nanometre and the height comes back
    1000x too large (3000.0 um for a true 3.0 um) with no way for the operator to
    know. The wavelength/step confusion *is* catchable, because the interferogram
    carries its own carrier frequency, and it is caught (see
    ``carrier_tolerance``). The dispersion is not.
  * **No dispersion compensation, no phase-gap resolution.** Real coherence
    scanning combines the envelope (unambiguous, coarse) with the fringe phase
    (ambiguous, fine) to get both; that combination needs a calibrated
    phase-envelope offset and is not implemented. What is here is the envelope
    half, which is the half :mod:`fringe` does not have.

Fail-closed, like every Fullseye module. A scan step past the carrier Nyquist
limit, a coherence peak sitting on the first or last plane of the scan, a signal
with no coherence peak at all, a zero step, a zero coherence length, a spectral
peak outside the calibrated band, a NaN, a stack over the element cap — all raise
an explicit ``ValueError`` naming the problem. The undersampling refusal in
particular is not pedantry: past Nyquist the answer is *intermittently* wrong
(measured: exactly right at a 0.20 um step, wrong by 0.107 um at a 0.16 um step,
with nothing in the output distinguishing the two), so being lucky is
indistinguishable from being right and the input is refused instead.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "csi_signal_simulate", "csi_stack_simulate", "chromatic_confocal_simulate",
    "csi_envelope", "csi_peak_position",
    "csi_height_map", "csi_contrast_map",
    "chromatic_confocal_height",
    "csi_design",
    "INTERFEROMETRY", "ESTIMATORS", "FWHM_PER_SIGMA",
    "MAX_SCAN_POINTS", "MAX_STACK_ELEMENTS",
]

#: The public operators, by name (introspection / facade wiring).
INTERFEROMETRY = [
    "csi_signal_simulate", "csi_stack_simulate", "chromatic_confocal_simulate",
    "csi_envelope", "csi_peak_position",
    "csi_height_map", "csi_contrast_map",
    "chromatic_confocal_height",
    "csi_design",
]

#: Envelope-peak estimators accepted by :func:`csi_peak_position`,
#: :func:`csi_height_map` and :func:`chromatic_confocal_height`.
#: Their measured biases are tabulated in the module docstring — they differ by
#: five orders of magnitude and the ranking *inverts* once noise is present.
ESTIMATORS = ("peak", "centroid", "parabolic", "gaussian")

#: ``FWHM = FWHM_PER_SIGMA * sigma`` for a Gaussian (``2*sqrt(2*ln 2)``).
#: Same constant, same name, as :data:`photoncount.FWHM_PER_SIGMA`; the coherence
#: envelope and a TCSPC instrument response are both Gaussians and there is no
#: reason for the two modules to disagree about the conversion.
FWHM_PER_SIGMA = 2.0 * np.sqrt(2.0 * np.log(2.0))

#: Largest number of planes in one z scan (2^20 = 8 MB float64 for one pixel).
#: A real scan is 100-10000 planes; the cap only stops a mistyped exponent.
MAX_SCAN_POINTS = 1 << 20

#: Largest element count for a ``(Z, H, W)`` scan stack. The envelope route needs
#: several complex ``(Z, H, W)``-sized temporaries (the analytic signal is
#: complex128 = 16 bytes/element), so 2^23 elements is already ~0.13 GB per
#: complex temporary. Same cap and same reason as
#: :data:`photoncount.MAX_CUBE_ELEMENTS`.
MAX_STACK_ELEMENTS = 1 << 23


# --------------------------------------------------------------------------- #
# fail-closed input helpers (same discipline as photoncount / optics)          #
# --------------------------------------------------------------------------- #
def _finite_scalar(v, name: str) -> float:
    """A real, finite Python float — or ``ValueError`` naming the problem."""
    if np.ma.is_masked(v):
        raise ValueError("%s is a masked value — fill or drop it explicitly"
                         % (name,))
    if isinstance(v, (complex, np.complexfloating)):
        raise ValueError("%s is complex — a length / wavelength / step is a real "
                         "quantity; coercion would silently drop the imaginary "
                         "part" % (name,))
    if isinstance(v, (bool, np.bool_)):
        raise ValueError("%s is a bool — refusing the silent True==1 promotion "
                         "(True um is not a scan step)" % (name,))
    if isinstance(v, (str, bytes, np.str_, np.bytes_)):
        raise ValueError("%s is a string (%r) — a length must be a number; "
                         "float('0.55') would silently succeed and hide an "
                         "unparsed configuration value" % (name, v))
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real scalar, got %r"
                         % (name, type(v).__name__)) from None
    if not np.isfinite(f):
        raise ValueError("%s must be finite, got %r (NaN/Inf would propagate "
                         "through every result)" % (name, v))
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
        raise ValueError("%s must be an int, got %r (a fractional number of scan "
                         "planes is an input mistake, not something to round)"
                         % (name, type(v).__name__))
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
                         "contract in this module — there is no seed=None), "
                         "got %r" % (name, type(v).__name__))
    n = int(v)
    if n < 0:
        raise ValueError("%s must be >= 0, got %d" % (name, n))
    return n


def _bool(v, name: str) -> bool:
    if not isinstance(v, (bool, np.bool_)):
        raise ValueError("%s must be a bool, got %r (a truthy string or a 0/1 "
                         "int would hide a mis-wired flag)"
                         % (name, type(v).__name__))
    return bool(v)


def _size_of(a) -> int:
    """Element count of *a* **without** promoting it to float64 first.

    The order matters and is the whole point of this helper. Checking a size cap
    after ``np.ascontiguousarray(a, dtype=np.float64)`` does not prevent the
    allocation it exists to prevent — the promotion of a 2^25-element uint8 array
    has already claimed 256 MB by the time the cap is consulted. So the cap is
    read off the *shape* and the caller applies it before any coercion.
    """
    shp = getattr(a, "shape", None)
    if shp is None:
        shp = np.shape(a)                      # lists / tuples / scalars
    n = 1
    for d in shp:
        n *= int(d)
    return n if shp else 1


def _as_float_array(a, name: str, cap: int, op: str) -> np.ndarray:
    """Coerce to float64 — after the size cap, and refusing the silent-truncation
    traps (masked arrays, complex, non-finite)."""
    if np.ma.is_masked(a):
        raise ValueError("%s: %s is a masked array with masked (invalid) entries "
                         "— coercion would strip the mask and use the raw values "
                         "underneath; fill or drop them explicitly" % (op, name))
    if isinstance(a, (str, bytes)):
        raise ValueError("%s: %s is a string — an interferogram is an array of "
                         "numbers" % (op, name))
    n = _size_of(a)
    if n > cap:
        raise ValueError(
            "%s: %s has %d elements (shape %r), over the %d cap — refusing "
            "**before** the float64 promotion, because promoting first would "
            "already have allocated ~%d MB to discover the same thing"
            % (op, name, n, tuple(np.shape(a)), cap, n * 8 // (1 << 20)))
    if np.iscomplexobj(a):
        raise ValueError("%s: %s is complex — coercion to float64 would silently "
                         "discard the imaginary part; an interferogram is a "
                         "measured intensity, take .real explicitly if that is "
                         "what you mean" % (op, name))
    kind = getattr(getattr(a, "dtype", None), "kind", None)
    if kind is None and not isinstance(a, (int, float, np.number)):
        # a list / tuple: look at what numpy would make of it, without promoting
        kind = np.asarray(a).dtype.kind if not isinstance(a, np.ndarray) else None
    if kind in ("U", "S", "O", "V", "b"):
        raise ValueError(
            "%s: %s has dtype '%s' — numpy would happily parse it into float64 "
            "(np.asarray(['1.0'], dtype=float) succeeds, and so does an object "
            "array of Decimals or a bool array of True/False), which is exactly "
            "how an unparsed configuration value or a mis-wired mask becomes a "
            "measurement. Convert it yourself and state what you meant."
            % (op, name, np.dtype(kind if kind != "b" else "bool").name
               if kind != "V" else "void"))
    arr = np.ascontiguousarray(a, dtype=np.float64)
    if not np.isfinite(arr).all():
        bad = int((~np.isfinite(arr)).sum())
        raise ValueError("%s: %s has %d non-finite value(s) (NaN/Inf) — refusing"
                         % (op, name, bad))
    return arr


def _unit_interval(v, name: str, op: str) -> float:
    f = _finite_scalar(v, name)
    if not (0.0 <= f <= 1.0):
        raise ValueError("%s: %s must be in [0, 1], got %g" % (op, name, f))
    return f


def _estimator(mode, op: str) -> str:
    if not isinstance(mode, str):
        raise ValueError("%s: mode must be one of %r, got %r"
                         % (op, list(ESTIMATORS), type(mode).__name__))
    if mode not in ESTIMATORS:
        raise ValueError("%s: mode must be one of %r, got %r"
                         % (op, list(ESTIMATORS), mode))
    return mode


def _check_scan_step(z_step_um: float, wavelength_um: float, op: str) -> None:
    """Refuse a scan step that undersamples the interference carrier.

    The interferogram's carrier is ``cos(4*pi*z/lambda)`` — the double pass makes
    the fringe period ``lambda/2``, so Nyquist puts the ceiling on the scan step
    at ``lambda/4``. Past it the aliased carrier corrupts the analytic signal and
    therefore the envelope, and the corruption is **intermittent**: measured on
    the reference scan (lambda = 0.60 um, so the ceiling is 0.15 um), a 0.16 um
    step misplaces the peak by 0.107 um while a 0.20 um step is exactly right.
    Nothing in the output distinguishes the two cases, so the step is refused
    rather than folded — the same call
    :func:`photoncount.dtof_cube_simulate` makes when a distance falls outside
    the unambiguous range.
    """
    limit = 0.25 * wavelength_um
    if z_step_um >= limit:
        raise ValueError(
            "%s: z_step_um = %g um is at or past the Nyquist ceiling %g um "
            "(= wavelength_um/4; the double pass makes the fringe period "
            "lambda/2 = %g um). Past it the carrier aliases and the envelope "
            "peak moves by an amount that depends on where the surface happens "
            "to sit — measured 0.107 um of error at a 0.16 um step and none at "
            "0.20 um for lambda = 0.60 um — so a folded answer is refused "
            "instead of returned. Scan finer (lambda/8 = %g um is the usual "
            "choice) or state a longer wavelength_um."
            % (op, z_step_um, limit, 0.5 * wavelength_um, 0.125 * wavelength_um))


# --------------------------------------------------------------------------- #
# internal envelope machinery (vectorised over the trailing axis)              #
# --------------------------------------------------------------------------- #
def _analytic_envelope(arr: np.ndarray, remove_bias: bool) -> np.ndarray:
    """|analytic signal| along the **last** axis, after optional bias removal.

    ``dsp.envelope`` is the 1-D case of exactly this and is reused verbatim for
    1-D input, so the two can never drift apart; the N-D path calls
    ``scipy.signal.hilbert`` with ``axis=-1`` because ``dsp.envelope`` is 1-D by
    contract.
    """
    work = arr - arr.mean(axis=-1, keepdims=True) if remove_bias else arr
    if work.ndim == 1:
        import dsp                              # noqa: PLC0415 (see module docs)
        return dsp.envelope(work)
    from scipy.signal import hilbert            # noqa: PLC0415
    return np.abs(hilbert(work, axis=-1))


def _visibility(env: np.ndarray) -> np.ndarray:
    """Fringe-peak prominence in ``[0, 1]``, along the last axis.

    ``(max - median) / max``. A coherence envelope is a localised bump on a floor
    near zero, so this is close to 1. A signal with no coherence peak — a pure
    carrier, a constant, a plane of the scan that never came into focus — has a
    flat envelope whose median *is* its maximum, so this is close to 0. Measured
    on the chain fuzzer's ``signal`` pool (a sinusoid plus 10 % noise) it is
    0.241; on a real interferogram, 0.958; on a constant, 0.000.
    """
    top = env.max(axis=-1)
    mid = np.median(env, axis=-1)
    with np.errstate(divide="ignore", invalid="ignore"):
        vis = np.where(top > 0.0, (top - mid) / np.where(top > 0.0, top, 1.0), 0.0)
    return np.asarray(vis, dtype=np.float64)


def _peak_index(env: np.ndarray) -> np.ndarray:
    return np.argmax(env, axis=-1)


def _edge_level(env: np.ndarray) -> np.ndarray:
    """How much of the coherence envelope is still outside the scan, in ``[0, 1]``.

    ``(max(env[0], env[-1]) - median(env)) / (max(env) - median(env))``, along the
    last axis. The median baseline is not decoration: without it the measure reads
    the *noise floor* as if it were a truncated envelope. On a perfectly centred
    scan with 1 % additive noise the raw ratio ``max(ends)/max`` is 0.0586 — above
    any threshold that would catch real truncation — while the baseline-referenced
    form is 0.0069, because the noise floor lifts the ends and the median by the
    same amount and it cancels.

    This is the diagnostic that catches the module's nastiest silent failure, and
    the threshold on it is measured rather than chosen. With a 2.83 um envelope
    FWHM on a 12 um scan, the ``"gaussian"`` estimator's error against the true
    surface height goes:

        edge level  0.0000 -> 3e-14 um     (surface centred at 6.0 um)
        edge level  0.0000 -> 1.9e-06 um   (surface at 4.32 um)
        edge level  0.0107 -> 7.8e-03 um   (surface at 2.77 um)
        edge level  0.1746 -> 2.7e-02 um   (surface at 2.00 um)
        edge level  0.6364 -> **-0.38 um**, on a true height of 0.50 um

    That last row is the point. The envelope peak is at plane 2 of 241 — an
    *interior* plane, so a first-or-last-plane check does not fire — and the
    operator returns 0.1189 um for a surface at 0.5000 um: finite, plausible, and
    76 % wrong. The cause is physical, not an FFT artefact: the analytic signal is
    a global transform and a truncated envelope is genuinely a different signal.
    Zero-padding and reflect-padding were both measured and both made it *worse*
    (-3.3e-02 and -3.7e-02 against -2.7e-02 plain, on the 2.00 um row), so there
    is nothing to fix and the input is refused instead.
    """
    base = np.median(env, axis=-1)
    top = env.max(axis=-1) - base
    ends = np.maximum(env[..., 0], env[..., -1]) - base
    with np.errstate(divide="ignore", invalid="ignore"):
        lvl = np.where(top > 0.0, ends / np.where(top > 0.0, top, 1.0), 1.0)
    return np.asarray(np.clip(lvl, 0.0, 1.0), dtype=np.float64)


def _refine(env: np.ndarray, idx: np.ndarray, mode: str) -> np.ndarray:
    """Sub-step offset (in samples) of the envelope peak, along the last axis.

    ``peak`` -> 0. ``centroid`` -> the whole-scan intensity centroid relative to
    ``idx``. ``parabolic`` / ``gaussian`` -> the three-point fit around ``idx``,
    falling back to 0 where the three samples are degenerate (flat, or
    non-positive for the log fit). The boundary case never reaches here: callers
    reject or mask a peak sitting on the first or last plane first.
    """
    n = env.shape[-1]
    if mode == "peak":
        return np.zeros(env.shape[:-1], dtype=np.float64)
    if mode == "centroid":
        k = np.arange(n, dtype=np.float64)
        tot = env.sum(axis=-1)
        with np.errstate(divide="ignore", invalid="ignore"):
            cen = np.where(tot > 0.0, (env * k).sum(axis=-1) / np.where(tot > 0.0, tot, 1.0),
                           idx.astype(np.float64))
        return np.asarray(cen - idx, dtype=np.float64)

    lo = np.take_along_axis(env, (idx - 1)[..., None], axis=-1)[..., 0]
    mid = np.take_along_axis(env, idx[..., None], axis=-1)[..., 0]
    hi = np.take_along_axis(env, (idx + 1)[..., None], axis=-1)[..., 0]
    if mode == "gaussian":
        ok = (lo > 0.0) & (mid > 0.0) & (hi > 0.0)
        safe = np.where(ok, 1.0, np.nan)
        with np.errstate(divide="ignore", invalid="ignore"):
            lo, mid, hi = np.log(lo * safe), np.log(mid * safe), np.log(hi * safe)
    den = lo - 2.0 * mid + hi
    with np.errstate(divide="ignore", invalid="ignore"):
        off = 0.5 * (lo - hi) / den
    off = np.where(np.isfinite(off) & (np.abs(off) <= 1.0), off, 0.0)
    return np.asarray(off, dtype=np.float64)


def _carrier_cycles_per_unit(power: np.ndarray, step: float) -> float:
    """Dominant fringe frequency of a DC-removed scan, in cycles per scan unit.

    *power* is a rFFT magnitude (or magnitude summed over pixels — the carrier
    peak survives that sum, because a per-pixel height shift moves the phase and
    not the magnitude). Bin 0 is dropped: the residual DC is not a fringe.
    """
    if power.size < 2:
        return float("nan")
    k = int(np.argmax(power[1:])) + 1
    return float(np.fft.rfftfreq(2 * (power.size - 1), d=step)[k])


def _check_carrier(power: np.ndarray, n: int, step: float, wavelength: float,
                   tol: float, op: str) -> None:
    """Cross-check the *stated* wavelength against the fringe frequency actually
    present in the data. The unit guard that a name cannot provide.

    ``wavelength_um`` is otherwise used only for the Nyquist ceiling, so passing
    it in nanometres (600 instead of 0.6) silently *disables* that ceiling and
    nothing in the answer changes — measured, ``csi_peak_position`` returns the
    same 6.025 um either way. Here the interferogram is asked what wavelength it
    actually has: the carrier sits at ``2/lambda`` cycles per micrometre (the
    double pass again), and a 1000x error in the stated wavelength is a 1000x
    mismatch that no plausible data can produce.

    The tolerance is deliberately loose — a factor of *tol* either way, default
    2 — because the point is to catch unit confusion, not to re-derive the
    wavelength. Measured on the reference scan the ratio is 0.996, and it stays
    0.996 with 1 % noise, with 10 % noise, with a truncated envelope, and with a
    0.3 um envelope; only a scan of fewer than 16 planes moves it (0.667 at 9
    planes), which is why short scans skip the check rather than fail it.
    """
    if n < 16 or tol <= 1.0:
        return
    f = _carrier_cycles_per_unit(power, step)
    if not np.isfinite(f) or f <= 0.0:
        return
    want = 2.0 / wavelength
    ratio = f / want
    if ratio > tol or ratio < 1.0 / tol:
        raise ValueError(
            "%s: the data has its fringe carrier at %.4g cycles per scan unit, "
            "but wavelength_um=%g says it should be at 2/lambda = %.4g — a "
            "factor of %.4g. Either wavelength_um and z_step_um are in different "
            "units (600 nm written as 600 rather than 0.6 is the classic one, "
            "and it silently disables the Nyquist ceiling because nothing else "
            "in the answer uses the wavelength), or this array is not an "
            "interferogram. Pass carrier_tolerance=0 to skip this check."
            % (op, f, wavelength, want, max(ratio, 1.0 / ratio)))


def _gauss_envelope(z: np.ndarray, z0, sigma: float) -> np.ndarray:
    return np.exp(-0.5 * ((z - z0) / sigma) ** 2)


def _sigma_from(envelope_fwhm_um, envelope_sigma_um, op: str) -> float:
    """The envelope width along **z**, given either as a FWHM or as a sigma.

    Exactly one of the two must be supplied. Accepting both and silently
    preferring one is how a 2.35x error in an envelope width gets into a result
    without anybody noticing.

    Note the parameter is ``envelope_fwhm_um`` and **not** ``coherence_length_um``,
    and the difference is a factor of two that a shared name would have hidden.
    The source coherence length is a property of the *optical path difference*,
    and in this geometry the light goes down to the surface and back, so
    ``OPD = 2z`` and the envelope seen along the scan axis is **half** the
    coherence length. :func:`csi_design` returns both, from the same source
    spectrum, and the tests verify the coherence length against a numerical
    Fourier transform of that spectrum.
    """
    have_fw = envelope_fwhm_um is not None
    have_sg = envelope_sigma_um is not None
    if have_fw and have_sg:
        raise ValueError("%s: give either envelope_fwhm_um or envelope_sigma_um, "
                         "not both — they differ by a factor %.4f and silently "
                         "preferring one would be a 2.35x error in the envelope "
                         "width" % (op, FWHM_PER_SIGMA))
    if not (have_fw or have_sg):
        raise ValueError("%s: give either envelope_fwhm_um (the envelope width "
                         "along the scan axis, = csi_design's "
                         "'envelope_fwhm_um', which is HALF the source coherence "
                         "length because the double pass makes OPD = 2z) or "
                         "envelope_sigma_um" % (op,))
    if have_fw:
        return _positive(envelope_fwhm_um, "envelope_fwhm_um") / FWHM_PER_SIGMA
    return _positive(envelope_sigma_um, "envelope_sigma_um")


# --------------------------------------------------------------------------- #
# 1. forward model — where the ground truth comes from                         #
# --------------------------------------------------------------------------- #
def csi_signal_simulate(surface_um=6.0, z_start_um=0.0, z_step_um=0.05,
                        n_planes=241, wavelength_um=0.6,
                        envelope_fwhm_um=2.8, envelope_sigma_um=None,
                        bias=0.5, amplitude=0.4, reflectivity=1.0,
                        noise=0.0, seed=0):
    """Synthesise the z-scan interferogram of one pixel over a known surface height.

    The coherence-scanning forward model, and the reason every other operator here
    has an exact answer to be checked against::

        I(z) = bias + amplitude*reflectivity * exp(-(z-z0)^2 / 2 sigma^2)
                                             * cos(4*pi*(z-z0)/wavelength)

    with ``z0 = surface_um``. The **4** is the double pass — light goes down to the
    surface and back, so one fringe is ``wavelength/2`` of *height*, not a whole
    wavelength. Getting that factor wrong is a clean 2x in every height this
    module produces, which is why it is written out here rather than hidden in a
    constant.

    surface_um:           the true surface height ``z0``, in the scan's own
                          coordinate. Need not land on a scan plane — the
                          sub-step case is the interesting one and the tests use
                          it deliberately.
    z_start_um/z_step_um/n_planes: the scan grid,
                          ``z_k = z_start_um + k*z_step_um``.
    wavelength_um:        mean wavelength of the source.
    envelope_fwhm_um:     the FWHM of the envelope **along the scan axis**. Give
                          this *or* ``envelope_sigma_um``, never both. It is
                          **half** the source coherence length, because the
                          double pass makes OPD = 2z;
                          :func:`csi_design` returns both under separate names
                          for exactly that reason.
    bias/amplitude:       the intensity pedestal ``a`` and fringe amplitude ``b``.
    reflectivity:         per-pixel scale on the fringe amplitude (>= 0). It
                          scales the envelope and therefore
                          :func:`csi_contrast_map`, and — this is the honest part
                          — it does **not** move the envelope peak, so it does not
                          bias :func:`csi_peak_position`. A *spatially varying*
                          reflectivity biases nothing either; what does bias the
                          centroid is where the peak sits in the window, and that
                          is documented on :func:`csi_peak_position`.
    noise:                additive Gaussian sigma (0 = the exact model).
    seed:                 integer seed for that noise (no ``None``).

    Returns a 1-D float64 array of ``n_planes`` intensities.

    Ground truth: with ``noise=0`` and the surface centred in the scan, the
    ``"gaussian"`` estimator of :func:`csi_peak_position` returns *surface_um* to
    1.43e-07 um over sub-step offsets, and to 2.9e-14 um when the envelope is
    given analytically instead of through the Hilbert transform (both pinned in
    the tests).

    **Raises** ``ValueError``: a non-real / non-finite / string / bool parameter,
    a non-positive ``z_step_um`` / ``wavelength_um`` / envelope width, a negative
    ``bias`` / ``amplitude`` / ``reflectivity`` / ``noise``, ``n_planes`` outside
    ``[3, MAX_SCAN_POINTS]``, a ``z_step_um`` at or past the ``wavelength_um/4``
    Nyquist ceiling, and a *surface_um* outside the scan range (which is the case
    a real instrument reports as "no surface found", not as a height).
    """
    z0 = _finite_scalar(surface_um, "surface_um")
    z_start = _finite_scalar(z_start_um, "z_start_um")
    dz = _positive(z_step_um, "z_step_um")
    n = _count(n_planes, "n_planes", 3, MAX_SCAN_POINTS)
    lam = _positive(wavelength_um, "wavelength_um")
    sigma = _sigma_from(envelope_fwhm_um, envelope_sigma_um,
                        "csi_signal_simulate")
    a = _nonneg(bias, "bias")
    b = _nonneg(amplitude, "amplitude")
    refl = _nonneg(reflectivity, "reflectivity")
    sig_n = _nonneg(noise, "noise")
    s = _seed(seed)
    _check_scan_step(dz, lam, "csi_signal_simulate")

    z = z_start + dz * np.arange(n, dtype=np.float64)
    if not (z[0] <= z0 <= z[-1]):
        raise ValueError(
            "csi_signal_simulate: surface_um = %g um is outside the scan range "
            "[%g, %g] um (z_start_um + n_planes*z_step_um). A scan that does not "
            "cross the surface has no coherence peak to find, and returning one "
            "anyway is what this module refuses to do." % (z0, z[0], z[-1]))
    out = a + b * refl * _gauss_envelope(z, z0, sigma) * np.cos(
        4.0 * np.pi * (z - z0) / lam)
    if sig_n:
        out = out + np.random.default_rng(s).normal(0.0, sig_n, out.shape)
    return np.ascontiguousarray(out)


def csi_stack_simulate(height_um, z_start_um=0.0, z_step_um=0.05, n_planes=241,
                       wavelength_um=0.6, envelope_fwhm_um=2.8,
                       envelope_sigma_um=None, bias=0.5, amplitude=0.4,
                       reflectivity=None, noise=0.0, seed=0):
    """Synthesise the ``(Z, H, W)`` scan stack an interference microscope records.

    The per-pixel version of :func:`csi_signal_simulate`: every pixel of the
    *height_um* map gets its own coherence envelope centred on its own height, on
    a shared scan grid. **The scan axis is FIRST** — a stack is what a camera
    streams while the objective moves, one frame per plane — which is the same
    layout as a ``video`` ``(T, H, W)`` and *not* the ``(H, W, T)`` of a
    :func:`photoncount.dtof_cube_simulate` histogram cube.

    That resemblance to ``video`` is not cosmetic and it is measured, not assumed:
    handing a translating-grating clip to :func:`csi_height_map` does **not**
    raise, it returns a height map (see the type note in :mod:`opsinterferometry`
    for the numbers). The registry therefore declares a separate ``zscan`` type.

    height_um:     2-D ``(H, W)`` map of true surface heights, in the scan's own
                   coordinate. Every height must lie inside the scan range.
    reflectivity:  optional ``(H, W)`` map of per-pixel fringe-amplitude scale
                   (>= 0). ``None`` = uniform 1. A pixel with reflectivity 0 has
                   no fringes at all and :func:`csi_height_map` will refuse it
                   rather than report the first plane.
    (the remaining parameters are :func:`csi_signal_simulate`'s, applied to every
    pixel; ``noise`` is sampled once for the whole stack from *seed*.)

    Returns a float64 ``(n_planes, H, W)`` stack.

    Ground truth: with ``noise=0``, ``csi_height_map(stack, ..., mode="gaussian")``
    returns *height_um* with an RMS error of **2.08e-06 um** over a tilted plane
    spanning 5.0-7.0 um of a 0-12 um scan, and the per-pixel result is bit-for-bit
    identical to running :func:`csi_peak_position` on each column separately
    (both pinned in the tests). Widening the same plane to 2.0-10.0 um degrades
    that to 7.06e-03 um — envelope truncation at the scan ends, not the
    estimator.

    **Raises** ``ValueError``: everything :func:`csi_signal_simulate` raises, plus
    a non-2-D / empty *height_um*, a *reflectivity* that is negative or a
    different shape, any height outside the scan range, and a stack over
    :data:`MAX_STACK_ELEMENTS` (``n_planes*H*W`` grows fast — 241 planes of
    256x256 is 1.9x the cap). The element cap is applied **before** the float64
    promotion of *height_um*, not after.
    """
    op = "csi_stack_simulate"
    h = _as_float_array(height_um, "height_um", MAX_STACK_ELEMENTS, op)
    if h.ndim != 2:
        raise ValueError("%s: height_um must be a 2-D (H, W) map in um, got a "
                         "%d-D array of shape %r" % (op, h.ndim, h.shape))
    if h.size == 0:
        raise ValueError("%s: height_um is empty (shape %r)" % (op, h.shape))
    z_start = _finite_scalar(z_start_um, "z_start_um")
    dz = _positive(z_step_um, "z_step_um")
    n = _count(n_planes, "n_planes", 3, MAX_SCAN_POINTS)
    lam = _positive(wavelength_um, "wavelength_um")
    sigma = _sigma_from(envelope_fwhm_um, envelope_sigma_um, op)
    a = _nonneg(bias, "bias")
    b = _nonneg(amplitude, "amplitude")
    sig_n = _nonneg(noise, "noise")
    s = _seed(seed)
    _check_scan_step(dz, lam, op)

    total = int(h.size) * n
    if total > MAX_STACK_ELEMENTS:
        raise ValueError(
            "%s: the stack would be %dx%dx%d = %d elements, over the %d cap "
            "(interferometry.MAX_STACK_ELEMENTS, ~%d MB per float64 temporary "
            "and the envelope route needs complex ones at 16 bytes). Crop the "
            "height map or scan fewer planes."
            % (op, n, h.shape[0], h.shape[1], total, MAX_STACK_ELEMENTS,
               MAX_STACK_ELEMENTS * 8 // (1 << 20)))

    if reflectivity is None:
        refl = np.ones_like(h)
    else:
        refl = _as_float_array(reflectivity, "reflectivity",
                               MAX_STACK_ELEMENTS, op)
        if refl.shape != h.shape:
            raise ValueError("%s: reflectivity has shape %r but height_um has "
                             "shape %r — they must match pixel for pixel"
                             % (op, refl.shape, h.shape))
        if (refl < 0.0).any():
            raise ValueError("%s: reflectivity has %d negative value(s) (min %g)"
                             % (op, int((refl < 0.0).sum()), float(refl.min())))

    z = (z_start + dz * np.arange(n, dtype=np.float64))[:, None, None]
    lo, hi = float(z[0, 0, 0]), float(z[-1, 0, 0])
    if float(h.min()) < lo or float(h.max()) > hi:
        bad = int(((h < lo) | (h > hi)).sum())
        raise ValueError(
            "%s: %d of %d height(s) fall outside the scan range [%g, %g] um "
            "(observed [%g, %g]). Those pixels would have their coherence peak "
            "on the first or last plane, which is indistinguishable from 'the "
            "surface is somewhere further out' — refusing rather than clamping."
            % (op, bad, h.size, lo, hi, float(h.min()), float(h.max())))

    env = np.exp(-0.5 * ((z - h[None, :, :]) / sigma) ** 2)
    out = a + b * refl[None, :, :] * env * np.cos(
        4.0 * np.pi * (z - h[None, :, :]) / lam)
    if sig_n:
        out = out + np.random.default_rng(s).normal(0.0, sig_n, out.shape)
    return np.ascontiguousarray(out)


def chromatic_confocal_simulate(surface_um=0.0, wavelength_start_nm=500.0,
                                wavelength_step_nm=0.5, n_bins=401,
                                dispersion_um_per_nm=0.20,
                                reference_wavelength_nm=600.0,
                                peak_fwhm_nm=4.0, peak_counts=1000.0,
                                background=10.0, noise=0.0, seed=0):
    """Synthesise the confocal return spectrum of a surface at a known height.

    A chromatic objective is built to have axial colour on purpose: each
    wavelength focuses at a different height, so only the wavelength focused *on
    the surface* passes the confocal pinhole. The spectrometer therefore sees a
    peak whose **wavelength is the height**::

        lambda_peak = reference_wavelength_nm
                    + (surface_um - 0) / dispersion_um_per_nm

    i.e. ``surface_um = (lambda_peak - reference_wavelength_nm) *
    dispersion_um_per_nm``, which is what :func:`chromatic_confocal_height`
    inverts. The peak is modelled as a Gaussian of FWHM *peak_fwhm_nm* on a flat
    *background* pedestal.

    surface_um:                 true height (0 = the reference wavelength focuses
                                exactly on it). May be negative — unlike a
                                time-of-flight distance, a height is signed.
    wavelength_start_nm / wavelength_step_nm / n_bins: the spectrometer axis.
    dispersion_um_per_nm:       the axial chromatic dispersion, height per
                                nanometre. This is the calibration constant and
                                the units are in the name for a reason: a
                                per-micrometre reading of it is a 1000x error in
                                the height.
    peak_fwhm_nm:               spectral width of the confocal response.
    peak_counts / background:   peak height above, and level of, the pedestal.
    noise / seed:               additive Gaussian sigma and its integer seed.

    Returns a 1-D float64 spectrum of ``n_bins`` non-negative intensities
    (clipped at 0, because a spectrometer cannot read negative light — and the
    clip is stated here rather than left as a surprise).

    Ground truth: with ``noise=0`` the ``"gaussian"`` estimator recovers
    *surface_um* **exactly** (measured 0.0e+00 to 3.6e-15 um over heights from
    -15 to +18 um), at any peak width and even with the peak two bins from the
    band edge, because the logarithm of a sampled Gaussian is exactly a parabola
    and the three-point fit is *local* — there is no Hilbert transform here, so
    the truncation failure that limits the coherence-scanning side does not exist
    on this one (pinned in the tests).

    **Raises** ``ValueError``: non-real / non-finite / string / bool parameters, a
    non-positive step / width / dispersion, negative *peak_counts* /
    *background* / *noise*, *n_bins* outside ``[3, MAX_SCAN_POINTS]``, and a
    *surface_um* whose wavelength falls outside the spectrometer band (the
    out-of-range case a real probe reports as "no surface").
    """
    op = "chromatic_confocal_simulate"
    z0 = _finite_scalar(surface_um, "surface_um")
    l0 = _positive(wavelength_start_nm, "wavelength_start_nm")
    dl = _positive(wavelength_step_nm, "wavelength_step_nm")
    n = _count(n_bins, "n_bins", 3, MAX_SCAN_POINTS)
    disp = _positive(dispersion_um_per_nm, "dispersion_um_per_nm")
    lref = _positive(reference_wavelength_nm, "reference_wavelength_nm")
    fwhm = _positive(peak_fwhm_nm, "peak_fwhm_nm")
    peak = _nonneg(peak_counts, "peak_counts")
    bg = _nonneg(background, "background")
    sig_n = _nonneg(noise, "noise")
    s = _seed(seed)

    lam = l0 + dl * np.arange(n, dtype=np.float64)
    lam_peak = lref + z0 / disp
    if not (lam[0] <= lam_peak <= lam[-1]):
        raise ValueError(
            "%s: surface_um = %g um maps to %g nm, outside the spectrometer band "
            "[%g, %g] nm. The calibrated measuring range of this configuration is "
            "%+g..%+g um (band width %g nm x dispersion %g um/nm); a height "
            "outside it has no peak in the spectrum and will not be invented."
            % (op, z0, lam_peak, lam[0], lam[-1], (lam[0] - lref) * disp,
               (lam[-1] - lref) * disp, lam[-1] - lam[0], disp))
    sigma = fwhm / FWHM_PER_SIGMA
    out = bg + peak * _gauss_envelope(lam, lam_peak, sigma)
    if sig_n:
        out = out + np.random.default_rng(s).normal(0.0, sig_n, out.shape)
    return np.ascontiguousarray(np.maximum(out, 0.0))


# --------------------------------------------------------------------------- #
# 2. envelope + peak location                                                  #
# --------------------------------------------------------------------------- #
def csi_envelope(signal, remove_bias=True):
    """Coherence envelope of a z-scan interferogram (analytic-signal magnitude).

    ``dsp.envelope`` computes ``|hilbert(x)|`` for any 1-D signal and is called
    here verbatim, so the two can never drift apart. The one thing added is the
    one thing an interferogram needs and a generic signal does not: **removal of
    the intensity pedestal**. An interferogram is ``a + b*V(z)*cos(...)`` with
    ``a > 0``, and the analytic-signal magnitude of that is not ``b*V`` — the DC
    term passes through the Hilbert transform untouched and dominates.

    Measured on the module's reference scan (``a = 0.5``, ``b = 0.4``, envelope
    sigma 1.2 um, surface centred): with the bias removed the envelope matches the
    analytic ``b*V(z)`` to **1.83e-07**; without it, the error is **0.5** — the
    entire pedestal — and the recovered "envelope" never goes near zero.
    ``dsp.envelope`` called directly on the same raw interferogram gives that
    identical 0.5, which is the honest statement of what this operator adds. That
    is why ``remove_bias`` defaults to ``True``; ``False`` is available for a scan
    whose pedestal you have already removed some other way, and it is your
    statement that you did.

    signal:      1-D scan intensities (``(n,)``, n >= 3).
    remove_bias: subtract the scan mean before the transform.

    Returns a 1-D float64 envelope of the same length.

    **Raises** ``ValueError``: a non-1-D, empty, too-short (< 3), non-finite,
    complex or masked *signal*, a *signal* over :data:`MAX_SCAN_POINTS` elements
    (checked before the float64 promotion), or a non-bool *remove_bias*.
    """
    op = "csi_envelope"
    x = _as_float_array(signal, "signal", MAX_SCAN_POINTS, op)
    if x.ndim != 1:
        raise ValueError("%s: signal must be a 1-D z scan, got a %d-D array of "
                         "shape %r — a stack goes to csi_height_map, which knows "
                         "the scan axis is first" % (op, x.ndim, x.shape))
    if x.size < 3:
        raise ValueError("%s: signal has %d sample(s); an envelope peak needs at "
                         "least 3 planes to have an interior" % (op, x.size))
    return np.ascontiguousarray(_analytic_envelope(x, _bool(remove_bias, "remove_bias")))


def csi_peak_position(signal, z_step_um=0.05, z_start_um=0.0, wavelength_um=0.6,
                      mode="gaussian", remove_bias=True, min_visibility=0.30,
                      max_edge_envelope=0.05, carrier_tolerance=2.0):
    """Surface height from one z-scan: the position of the coherence envelope peak.

    This is the operator the whole module is for. Unlike a phase, an envelope has
    no period, so there is no fringe order to get wrong and no unwrapping to do —
    the height is simply where the fringe contrast is greatest, and it is correct
    for a surface step of any size that stays inside the scan.

    *mode* picks the estimator. Measured on the reference scan (0.60 um
    wavelength, 2.83 um envelope FWHM, 0.05 um step, surface centred, four
    sub-step offsets), and then again with 1 % additive noise over 200 trials:

      * ``"peak"``      — the scan plane with the largest envelope. Noiseless
                          2.50e-02 um, which is exactly the step quantisation
                          ``z_step_um/2``. Noisy RMS 0.1395 um.
      * ``"centroid"``  — the centroid of the whole envelope. Noiseless
                          4.55e-07 um, and the **best estimator under noise**
                          (RMS 0.0219 um, 6.4x better than the local fits, because
                          it averages 241 planes instead of looking at 3 samples
                          around an argmax that noise moves). Its own failure is
                          *window bias*: it is pulled toward the centre of the
                          scan. Measured on a 12 um scan, a surface at 2 um reads
                          **+0.189 um** high with no noise at all and **+0.873 um**
                          high with a 2 % noise floor; at 10 um the same bias runs
                          the other way (-0.189 / -0.851). Centre the scan on the
                          surface, or use a local estimator.
      * ``"parabolic"`` — three-point parabola on the envelope. 4.21e-06 um
                          noiseless, 0.1403 um noisy.
      * ``"gaussian"``  — three-point parabola on the **log** of the envelope,
                          which is algebraically exact for a Gaussian envelope:
                          1.43e-07 um noiseless — and the floor there is the
                          Hilbert envelope's own 1.8e-07 error, not the fit, since
                          the same fit on the analytic envelope is exact to 3e-14
                          — and 0.1403 um noisy. The default.

    There is no single best estimator here and this module does not pretend
    otherwise: ``"gaussian"`` is 30x better than ``"parabolic"`` on clean data and
    indistinguishable from it on noisy data, where ``"centroid"`` beats both by
    6.4x — and ``"centroid"`` is the only one of the four whose bias grows with
    how far the surface sits from the middle of the scan.

    signal:            1-D scan intensities.
    z_step_um:         spacing of the scan planes. Must be below the
                       ``wavelength_um/4`` Nyquist ceiling — see
                       :func:`csi_design`.
    z_start_um:        height of plane 0.
    wavelength_um:     mean wavelength, used only for the Nyquist check.
    mode:              one of :data:`ESTIMATORS`.
    remove_bias:       passed to :func:`csi_envelope`.
    min_visibility:    refuse a scan whose envelope prominence
                       ``(max - median)/max`` is below this. A real interferogram
                       scores 0.958; the chain fuzzer's generic ``signal`` (a
                       sinusoid plus 10 % noise, no coherence envelope at all)
                       scores 0.241 and is refused; a constant scores 0.000. The
                       argmax of a flat envelope is a plane noise chose, not a
                       surface.
    max_edge_envelope: refuse a scan whose envelope has not decayed by the ends,
                       ``max(env[0], env[-1]) / max(env) > this``. See
                       :func:`_edge_level` for the measured table this default of
                       0.05 comes from, and for the silent failure it exists to
                       catch — a surface at 0.500 um read as 0.119 um, from an
                       envelope peaking on an *interior* plane so that no
                       first-or-last-plane check fires. Pass 1.0 to disable the
                       check and accept that reading.
    carrier_tolerance: refuse a scan whose fringe carrier is more than this
                       factor away from the ``2/wavelength_um`` the stated
                       wavelength implies. This is the **unit guard**, and it is
                       the only thing standing between a nanometre/micrometre
                       swap and a wrong answer: *wavelength_um* is otherwise used
                       only for the Nyquist ceiling, so writing 600 instead of
                       0.6 silently disables that ceiling while changing nothing
                       in the returned height (measured: the same 6.025 um either
                       way). The default factor of 2 is deliberately loose — the
                       measured ratio on real scans is 0.996 and stays there
                       under 10 % noise, a truncated envelope and a 0.3 um
                       envelope — because it exists to catch a factor of 1000,
                       not to re-derive the wavelength. Scans shorter than 16
                       planes skip it (the FFT cannot resolve the carrier: the
                       ratio is 0.667 at 9 planes). Pass 0 to disable.

    Returns the height as a float, in the same units as *z_start_um* /
    *z_step_um*.

    **Raises** ``ValueError``: everything :func:`csi_envelope` raises, plus an
    unknown *mode*, a non-positive *z_step_um* / *wavelength_um*, a *z_step_um* at
    or past the Nyquist ceiling, an envelope prominence below *min_visibility*, an
    envelope edge level above *max_edge_envelope*, and an envelope peaking on the
    **first or last plane** (the surface is at or beyond the end of the scan).
    Those last three are the same trap in three shapes: each would otherwise
    return a height that is finite, plausible, and wrong.

    Honest scope of the boundary check: it is a **backstop, not the workhorse**.
    The analytic-signal magnitude of a finite record is suppressed at its own
    endpoints, so a surface at ``z = 0.0`` — or at ``-3.0 um``, entirely outside
    the scan — comes back with its envelope maximum on plane **1**, one plane
    inside the boundary, and the first-or-last-plane test does not fire. It fires
    for a genuinely monotone input (a ramp, an impulse on the first sample) and
    for a dead pixel. Everything else is caught by *max_edge_envelope*, and the
    tests pin both halves of that statement.
    """
    op = "csi_peak_position"
    dz = _positive(z_step_um, "z_step_um")
    z0 = _finite_scalar(z_start_um, "z_start_um")
    lam = _positive(wavelength_um, "wavelength_um")
    m = _estimator(mode, op)
    vis_min = _unit_interval(min_visibility, "min_visibility", op)
    edge_max = _unit_interval(max_edge_envelope, "max_edge_envelope", op)
    tol = _nonneg(carrier_tolerance, "carrier_tolerance")
    _check_scan_step(dz, lam, op)

    x = _as_float_array(signal, "signal", MAX_SCAN_POINTS, op)
    if x.ndim == 1 and x.size >= 16:
        _check_carrier(np.abs(np.fft.rfft(x - x.mean())), x.size, dz, lam, tol, op)
    env = csi_envelope(signal, remove_bias=remove_bias)
    vis = float(_visibility(env))
    if vis < vis_min:
        raise ValueError(
            "%s: the envelope prominence (max-median)/max is %.4f, below "
            "min_visibility=%.4f — this scan has no coherence peak. A flat "
            "envelope means the interferometer never crossed the surface (or the "
            "input is not an interferogram at all), and the argmax of a flat "
            "envelope is a plane noise chose. Refusing to report it as a height."
            % (op, vis, vis_min))
    k = int(np.argmax(env))
    if k == 0 or k == env.size - 1:
        raise ValueError(
            "%s: the coherence peak is on plane %d of %d — the first or last "
            "plane of the scan. The surface is at or beyond the end of the scan "
            "range [%g, %g] um, so its position is unknown; returning the "
            "boundary plane would be a plausible, finite, wrong height."
            % (op, k, env.size, z0, z0 + dz * (env.size - 1)))
    lvl = float(_edge_level(env))
    if lvl > edge_max:
        raise ValueError(
            "%s: the envelope is still at %.4f of its peak at the ends of the "
            "scan, above max_edge_envelope=%.4f — a large part of the coherence "
            "peak is outside the scan range [%g, %g] um. Measured, this is where "
            "the answer stops being merely imprecise and starts being wrong: at "
            "an edge level of 0.639 a surface at 0.500 um reads 0.119 um. Extend "
            "the scan (csi_design's capture_range_um says by how much), or pass "
            "max_edge_envelope=1.0 to accept the reading."
            % (op, lvl, edge_max, z0, z0 + dz * (env.size - 1)))
    off = float(_refine(env, np.asarray(k), m))
    return float(z0 + dz * (k + off))


# --------------------------------------------------------------------------- #
# 3. surface — the same inversion over a whole stack                           #
# --------------------------------------------------------------------------- #
def _stack_envelope(stack, op, remove_bias):
    """(Z,H,W) -> envelope as (H,W,Z), with the shared validation."""
    arr = _as_float_array(stack, "stack", MAX_STACK_ELEMENTS, op)
    if arr.ndim != 3:
        raise ValueError(
            "%s: stack must be a 3-D (Z, H, W) scan stack with the **scan axis "
            "first**, got a %d-D array of shape %r. A (H, W, T) photon histogram "
            "cube passed in here would be read as W scan planes and return a "
            "plausible-wrong height map, so the axis order is not guessed."
            % (op, arr.ndim, arr.shape))
    if arr.shape[0] < 3:
        raise ValueError("%s: the stack has %d plane(s); an envelope peak needs "
                         "at least 3 to have an interior. If this array is "
                         "(H, W, Z) with the scan axis last, transpose it — it "
                         "will not be detected for you" % (op, arr.shape[0]))
    if arr.shape[1] == 0 or arr.shape[2] == 0:
        raise ValueError("%s: the stack has an empty spatial extent (shape %r)"
                         % (op, arr.shape))
    moved = np.ascontiguousarray(np.moveaxis(arr, 0, -1))
    return moved, _analytic_envelope(moved, _bool(remove_bias, "remove_bias"))


def csi_height_map(stack, z_step_um=0.05, z_start_um=0.0, wavelength_um=0.6,
                   mode="gaussian", remove_bias=True, min_visibility=0.30,
                   max_edge_envelope=0.05, carrier_tolerance=2.0,
                   on_invalid="raise", fill_value=float("nan")):
    """Height map from a ``(Z, H, W)`` coherence-scanning stack — the CSI inversion.

    The per-pixel :func:`csi_peak_position`, vectorised. **The scan axis is
    first**; see :func:`csi_stack_simulate` for why that is checked rather than
    inferred.

    A pixel is *invalid* when any of three things is true, and all three are the
    same trap in different shapes — each would otherwise yield a finite, plausible,
    wrong height:

      1. its envelope prominence is below *min_visibility* — no fringes ever
         formed there (a hole, a dark or specular-dropout pixel, a facet tilted
         out of the aperture);
      2. its envelope peaks on the first or last plane — the surface is at or past
         the end of the scan;
      3. its envelope is still above *max_edge_envelope* of its peak at the ends
         of the scan — most of the coherence peak is outside the scan even though
         the argmax is on an interior plane. This is the one that has no natural
         alarm: measured, a surface at 0.500 um with an edge level of 0.639 reads
         **0.119 um** and nothing else about the result looks wrong. See
         :func:`_edge_level`.

    What happens then is a decision, not a default:

      * ``on_invalid="raise"`` (**the default**) — raise, naming how many pixels
        failed which of the three checks. Fail-closed: a height map with silently
        wrong pixels in it is worse than no height map.
      * ``on_invalid="fill"`` — write *fill_value* (default NaN) at those pixels
        and return. Opt in to this when you intend to mask afterwards; a NaN
        height poisons every downstream reduction, which is precisely why it is
        not the default.

    There is deliberately no third option that quietly reports the boundary plane.

    Returns a float64 ``(H, W)`` height map, in the units of *z_start_um* /
    *z_step_um*.

    Ground truth (measured, 32x32 pixels, 241 planes x 0.05 um, 0.60 um
    wavelength, 2.83 um envelope FWHM). On a tilted plane spanning **5.0-7.0 um**,
    i.e. comfortably inside a 0-12 um scan, the RMS height error is 1.42e-02 um
    for ``"peak"``, 3.81e-05 um for ``"centroid"``, 4.02e-06 um for
    ``"parabolic"`` and 2.08e-06 um for ``"gaussian"``. Widen the same plane to
    **2.0-10.0 um** — pixels now within 2 um of the ends of the scan — and the
    errors become 1.91e-02 / 5.98e-02 / 7.06e-03 / 7.06e-03 um: the local fits
    lose three decades and the centroid loses four, entirely to envelope
    truncation at the scan ends. Accuracy here is a property of the *scan layout*,
    not of the estimator, and this is the number to look at when a real
    measurement disappoints.

    On that same surface, phase-shifting interferometry via :mod:`fringe` is exact
    below a lambda/4 = 0.15 um step and wrong by exact multiples of
    lambda/2 = 0.30 um above it.

    **Raises** ``ValueError``: a non-3-D stack, fewer than 3 planes, an empty
    spatial extent, a stack over :data:`MAX_STACK_ELEMENTS` (checked before the
    float64 promotion), a non-finite / complex / masked stack, an unknown *mode*
    or *on_invalid*, a *min_visibility* / *max_edge_envelope* outside ``[0, 1]``,
    a *z_step_um* at or past the ``wavelength_um/4`` Nyquist ceiling, a
    non-numeric *fill_value*, and — under the default ``on_invalid="raise"`` —
    any invalid pixel.
    """
    op = "csi_height_map"
    dz = _positive(z_step_um, "z_step_um")
    z0 = _finite_scalar(z_start_um, "z_start_um")
    lam = _positive(wavelength_um, "wavelength_um")
    m = _estimator(mode, op)
    if on_invalid not in ("raise", "fill"):
        raise ValueError("%s: on_invalid must be 'raise' or 'fill', got %r — "
                         "there is no option that reports the boundary plane as "
                         "a height" % (op, on_invalid))
    vis_min = _unit_interval(min_visibility, "min_visibility", op)
    edge_max = _unit_interval(max_edge_envelope, "max_edge_envelope", op)
    if isinstance(fill_value, (str, bytes, bool, np.bool_, complex,
                               np.complexfloating)):
        raise ValueError("%s: fill_value must be a real number or NaN, got %r"
                         % (op, type(fill_value).__name__))
    fill = float(fill_value)
    if np.isinf(fill):
        raise ValueError(
            "%s: fill_value is %s. NaN is the supported marker for 'no height "
            "here' — it propagates as invalid through every reduction, which is "
            "the point. An infinity instead propagates as a *number*: "
            "mean/min/max/percentile of the map all come back infinite or "
            "clipped, and a height map that reads +inf at a dropout is a worse "
            "lie than one that reads NaN." % (op, fill))
    tol = _nonneg(carrier_tolerance, "carrier_tolerance")
    _check_scan_step(dz, lam, op)

    moved, env = _stack_envelope(stack, op, remove_bias)
    n = env.shape[-1]
    if n >= 16:
        # the carrier magnitude survives a sum over pixels: a per-pixel height
        # shifts the phase, not the magnitude
        spec = np.abs(np.fft.rfft(moved - moved.mean(axis=-1, keepdims=True),
                                  axis=-1))
        _check_carrier(spec.reshape(-1, spec.shape[-1]).sum(axis=0), n, dz, lam,
                       tol, op)
    idx = _peak_index(env)
    bad_vis = _visibility(env) < vis_min
    bad_edge = (idx == 0) | (idx == n - 1)
    bad_trunc = _edge_level(env) > edge_max
    bad = bad_vis | bad_edge | bad_trunc
    if bad.any() and on_invalid == "raise":
        raise ValueError(
            "%s: %d of %d pixel(s) have no usable coherence peak — %d with "
            "envelope prominence below min_visibility=%.3f (no fringes ever "
            "formed there), %d peaking on the first or last plane (the surface is "
            "at or past the end of the scan range [%g, %g] um), and %d whose "
            "envelope is still above max_edge_envelope=%.3f at the scan ends (the "
            "coherence peak is mostly outside the scan; measured, that is where "
            "a 0.500 um surface reads 0.119 um). Refusing to return a map with "
            "plausible-wrong pixels in it; pass on_invalid='fill' if you intend "
            "to mask them, or extend the scan."
            % (op, int(bad.sum()), int(bad.size), int(bad_vis.sum()), vis_min,
               int(bad_edge.sum()), z0, z0 + dz * (n - 1), int(bad_trunc.sum()),
               edge_max))

    safe = np.clip(idx, 1, n - 2)
    off = _refine(env, safe, m)
    out = z0 + dz * (safe.astype(np.float64) + off)
    if bad.any():
        out = np.where(bad, fill, out)
    return np.ascontiguousarray(out, dtype=np.float64)


def csi_contrast_map(stack, remove_bias=True):
    """Peak fringe modulation per pixel — the contrast (and validity) map.

    The maximum of each pixel's coherence envelope. Three uses, in order of how
    often they matter:

      1. **Validity.** A pixel that never produced fringes — a hole, a steeply
         tilted facet that threw the light out of the aperture, a saturated or
         dark pixel — has near-zero modulation. This is the map you threshold to
         decide which heights from :func:`csi_height_map` to trust.
      2. **Reflectance.** In the forward model the envelope peak is exactly
         ``amplitude * reflectivity``, so with a known *amplitude* this map *is*
         the reflectivity. Verified in the tests: a known reflectivity map over a
         5.0-7.0 um surface is recovered with a maximum error of 7.32e-05 (the
         residual is envelope truncation again — the same surface spread over
         2.0-10.0 um gives 4.03e-04). It is a contrast map, not a photometric
         measurement, and it is accurate to about four decimal places, not to
         machine precision.
      3. **Focus.** It is the interferometric analogue of a focus measure, and it
         peaks where :func:`csi_height_map` says the surface is.

    Why use 1 rather than trust the height map everywhere: measured on a flat
    surface at 6.0 um with a **50x reflectance step** across the field (0.02 on
    one half, 1.0 on the other) and 1 % noise, the ``"gaussian"`` height error is
    0.146 um RMS on the bright half and **3.03 um RMS** on the dark half, and 30 %
    of the dark pixels are refused outright. The bias barely moves (+0.14 um);
    what explodes is the scatter, because the three-point fit is reading three
    samples out of a noise floor. ``"centroid"`` degrades far more gracefully on
    the same data (0.022 -> 0.157 um, 7x rather than 20x), which is the second
    place in this module where the estimator ranking depends on the data rather
    than on the algebra. This map is what separates the two populations: it reads
    0.035 +- 0.004 on the dark half and 0.412 +- 0.007 on the bright one.

    It is deliberately **not** normalised by the pedestal. The classical fringe
    *visibility* is ``b/a``, and computing it would need the pedestal, which
    ``remove_bias`` has just thrown away; returning ``b`` and saying so is honest,
    whereas returning ``b`` and calling it visibility would not be. Divide by
    :func:`numpy.mean` of the stack along axis 0 if you want the ratio.

    Returns a float64 ``(H, W)`` map. Same shape and validation as
    :func:`csi_height_map`.

    **Raises** ``ValueError``: a non-3-D stack, fewer than 3 planes, an empty
    spatial extent, a stack over :data:`MAX_STACK_ELEMENTS`, a non-finite /
    complex / masked stack, or a non-bool *remove_bias*.
    """
    _, env = _stack_envelope(stack, "csi_contrast_map", remove_bias)
    return np.ascontiguousarray(env.max(axis=-1), dtype=np.float64)


# --------------------------------------------------------------------------- #
# 4. chromatic confocal                                                        #
# --------------------------------------------------------------------------- #
def chromatic_confocal_height(spectrum, wavelength_start_nm=500.0,
                              wavelength_step_nm=0.5,
                              dispersion_um_per_nm=0.20,
                              reference_wavelength_nm=600.0, mode="gaussian",
                              subtract_background=True, min_visibility=0.30,
                              min_peak_bins=2.0, max_carrier_fraction=0.10):
    """Surface height from one confocal return spectrum — the wavelength *is* the height.

    The inverse of :func:`chromatic_confocal_simulate`. Find the peak wavelength
    of the spectrum, then::

        height = (lambda_peak - reference_wavelength_nm) * dispersion_um_per_nm

    No scan, no moving parts, one spectrum per point — which is why this family
    reaches sampling rates a z scan cannot, and why it is limited to the axial
    range the objective's chromatic spread covers.

    The four *mode* estimators are :data:`ESTIMATORS`, identical to
    :func:`csi_peak_position`'s and sharing its implementation. ``"gaussian"`` is
    exact for a Gaussian confocal response (measured 0.0e+00 to 3.6e-15 um),
    *including when the peak is narrower than one bin and when it sits two bins
    from the band edge* — the logarithm of a sampled Gaussian is a parabola
    whatever its width, and the fit is local. That exactness is a property of
    noiseless data only, which is what *min_peak_bins* is about.

    spectrum:             1-D non-negative intensities across the spectrometer.
    wavelength_start_nm / wavelength_step_nm: the spectrometer axis.
    dispersion_um_per_nm: the axial chromatic calibration constant.
    reference_wavelength_nm: the wavelength that focuses at height 0.
    subtract_background:  subtract the spectrum's median before locating the peak.
                          On by default because a pedestal drags the ``centroid``
                          estimator toward the middle of the band exactly as it
                          drags the CSI centroid toward the middle of the scan.
    min_visibility:       refuse a spectrum whose peak prominence
                          ``(max-median)/max`` is below this — a flat spectrum has
                          no focused wavelength and its argmax is noise.
    min_peak_bins:        refuse a peak whose full width at half maximum spans
                          fewer than this many bins. Undersampling does not break
                          the noiseless algebra, but it destroys its noise
                          rejection. Measured at 1 % noise (1000 peak counts,
                          sigma_n = 10, 100 trials), RMS error in locating the
                          peak against the number of bins across its FWHM:

                              0.5 bins -> 0.256 nm
                              1.0 bins -> 0.137 nm
                              2.0 bins -> 0.010 nm
                              4.0 bins -> 0.030 nm
                              8.0 bins -> 0.118 nm

                          Two bins is the optimum and a half-bin peak is **25x**
                          worse, from a spectrum that looks perfectly healthy —
                          hence the default of 2. Note the curve turns around
                          again: a very *broad* peak is also bad, because the
                          three-point fit then sits where the curvature is tiny
                          and noise dominates it. "More samples is better" is
                          false here and this operator does not claim it. Set to
                          0 to disable the check if you know your data is
                          clean.
    max_carrier_fraction: refuse a spectrum whose dominant alternating component
                          sits above this fraction of the Nyquist frequency. A
                          confocal response is one smooth peak and all of its AC
                          content is at low frequency (measured: dominant bin at
                          0.010 of Nyquist for a 4 nm peak, 0.010 for a 1 nm peak,
                          0.015 with 5 % noise). A **z-scan interferogram** put in
                          here instead sits at 0.333 — its fringe carrier — and
                          without this check its carrier's argmax would come back
                          as a focused wavelength and therefore as a plausible,
                          finite, wrong height. This is the guard that lets the
                          two 1-D families share one type pool safely. Pass 0 to
                          disable.

    Returns the height as a float, in micrometres. It may be negative — a height
    is signed, unlike a time-of-flight distance.

    **Raises** ``ValueError``: a non-1-D / empty / too-short (< 3) / non-finite /
    complex / masked *spectrum*, a *spectrum* over :data:`MAX_SCAN_POINTS`
    elements (checked before the float64 promotion), any **negative** intensity
    (a spectrometer cannot read negative light; clip explicitly if this is a
    pre-subtracted spectrum), a non-positive step / dispersion / reference
    wavelength, an unknown *mode*, a peak prominence below *min_visibility*, a
    peak narrower than *min_peak_bins*, and a peak on the **first or last bin**
    (the surface is outside the calibrated axial range, which is
    ``+-(band_nm/2) * dispersion_um_per_nm`` about the reference).
    """
    op = "chromatic_confocal_height"
    x = _as_float_array(spectrum, "spectrum", MAX_SCAN_POINTS, op)
    if x.ndim != 1:
        raise ValueError("%s: spectrum must be 1-D, got a %d-D array of shape %r"
                         % (op, x.ndim, x.shape))
    if x.size < 3:
        raise ValueError("%s: spectrum has %d bin(s); a peak needs at least 3 to "
                         "have an interior" % (op, x.size))
    neg = int((x < 0.0).sum())
    if neg:
        raise ValueError("%s: spectrum has %d negative value(s) (min %g) — a "
                         "spectrometer cannot read negative light; if this is a "
                         "background-subtracted spectrum, clip it at 0 "
                         "explicitly" % (op, neg, float(x.min())))
    l0 = _positive(wavelength_start_nm, "wavelength_start_nm")
    dl = _positive(wavelength_step_nm, "wavelength_step_nm")
    disp = _positive(dispersion_um_per_nm, "dispersion_um_per_nm")
    lref = _positive(reference_wavelength_nm, "reference_wavelength_nm")
    m = _estimator(mode, op)
    sub = _bool(subtract_background, "subtract_background")
    vis_min = _finite_scalar(min_visibility, "min_visibility")
    if not (0.0 <= vis_min <= 1.0):
        raise ValueError("%s: min_visibility must be in [0, 1], got %g"
                         % (op, vis_min))
    bins_min = _nonneg(min_peak_bins, "min_peak_bins")
    carr_max = _unit_interval(max_carrier_fraction, "max_carrier_fraction", op)

    if carr_max > 0.0 and x.size >= 16:
        ac = np.abs(np.fft.rfft((x - x.mean()) * np.hanning(x.size))) ** 2
        ac[0] = 0.0
        where = float(np.argmax(ac)) / float(ac.size - 1)
        if where > carr_max:
            raise ValueError(
                "%s: the dominant oscillation in this spectrum sits at %.3f of "
                "the Nyquist frequency, above max_carrier_fraction=%.3f. A "
                "confocal response is a single smooth peak, whose alternating "
                "content is all at low frequency (measured 0.010 for a 4 nm peak, "
                "0.010 for a 1 nm peak, 0.015 with 5 %% noise). A value up here "
                "means this is an *interferogram* — a fringe carrier at 0.333 is "
                "what a z scan looks like — and reading its carrier's argmax as a "
                "focused wavelength would return a plausible, finite, wrong "
                "height. Pass max_carrier_fraction=0 to skip this check."
                % (op, where, carr_max))

    vis = float(_visibility(x))
    if vis < vis_min:
        raise ValueError(
            "%s: the spectral peak prominence (max-median)/max is %.4f, below "
            "min_visibility=%.4f — this spectrum has no focused wavelength, so "
            "its argmax is a bin noise chose rather than a surface."
            % (op, vis, vis_min))
    work = np.maximum(x - np.median(x), 0.0) if sub else x
    k = int(np.argmax(work))
    if k == 0 or k == work.size - 1:
        raise ValueError(
            "%s: the spectral peak is on bin %d of %d — the first or last bin. "
            "The surface is outside the calibrated axial range (%+g..%+g um "
            "about the reference wavelength %g nm), so its height is unknown; "
            "returning the band edge would be a plausible, finite, wrong height."
            % (op, k, work.size, (l0 - lref) * disp,
               (l0 + (work.size - 1) * dl - lref) * disp, lref))
    tied = int((x == x.max()).sum())
    if tied >= 3:
        # Two bins can tie legitimately: a symmetric peak landing exactly between
        # them. Three or more is a plateau, which a smooth confocal response
        # cannot produce and a clipped detector always does.
        raise ValueError(
            "%s: %d bins share the maximum value %g — a flat top, which a "
            "smooth confocal response cannot produce. The spectrometer is "
            "saturated (or the spectrum has been clipped), so the peak itself is "
            "missing and the three-point fit is being handed a plateau. "
            "Measured, a peak clipped at 30 %% of its height reads 2.5500 um "
            "where the truth is 3.0000 um, with nothing else in the spectrum to "
            "show for it. Reduce the exposure, or pass the unclipped data."
            % (op, tied, float(x.max())))
    if bins_min > 0.0:
        top = float(work[k])
        above = int((work >= 0.5 * top).sum())
        if above < bins_min:
            raise ValueError(
                "%s: the spectral peak spans %d bin(s) above half maximum, below "
                "min_peak_bins=%g — the peak is undersampled by the "
                "spectrometer. The noiseless algebra still inverts it exactly, "
                "which is the trap: measured with 1 %% noise a half-bin peak is "
                "located 25x worse than a two-bin one (0.256 nm vs 0.010 nm) with "
                "nothing in the spectrum to show for it. Use a finer "
                "wavelength_step_nm, or pass min_peak_bins=0 if the data is "
                "known to be clean." % (op, above, bins_min))
    off = float(_refine(work, np.asarray(k), m))
    lam_peak = l0 + dl * (k + off)
    return float((lam_peak - lref) * disp)


# --------------------------------------------------------------------------- #
# 5. design — the limits, before any hardware exists                           #
# --------------------------------------------------------------------------- #
def csi_design(wavelength_um=0.6, bandwidth_um=0.1, z_range_um=12.0,
               width_px=640, height_px=480, min_visibility=0.30,
               step_divisor=8.0):
    """The axial limits of a coherence-scanning setup, from the source spectrum.

    The counterpart of :mod:`visiondesign` for the *vertical* axis: closed-form
    answers to the questions asked before any hardware is bought — how localised
    is the coherence peak, how finely must the scan step, how many planes is that,
    and how much memory does the stack need.

    Returned dict:

      * ``coherence_length_um`` — ``(4 ln2 / pi) * lambda^2 / delta_lambda``, the
        FWHM of ``|gamma(OPD)|`` for a Gaussian source (Born & Wolf 7.5.8). This
        is a property of the **optical path difference**. Verified in the tests
        against a direct numerical Fourier transform of the Gaussian source
        spectrum, at three (lambda, delta_lambda) settings, agreeing to 6
        significant figures.
      * ``envelope_fwhm_um`` — **half** of that: the width of the envelope along
        the **scan axis**, because the double pass makes ``OPD = 2z``. This is the
        one to hand to :func:`csi_signal_simulate` /
        :func:`csi_stack_simulate`, and the two are reported separately precisely
        because collapsing them into one name called "coherence length" is a clean
        factor-of-two error in every height the module produces. (It was one
        during development, and the numerical check above is what caught it.)
      * ``envelope_sigma_um`` — ``envelope_fwhm_um`` as a Gaussian sigma.
      * ``fringe_period_um`` — ``lambda/2``. The double pass halves it, and this
        is the number that makes phase-shifting ambiguous above ``lambda/4``.
      * ``max_z_step_um`` — ``lambda/4``. The Nyquist ceiling on the scan step;
        :func:`csi_peak_position` and :func:`csi_height_map` refuse at or above
        it.
      * ``recommended_z_step_um`` — ``lambda/step_divisor`` (default lambda/8, the
        usual 90-degree-per-plane choice), reported only if it is below the
        ceiling.
      * ``capture_range_um`` — the height interval over which the fringe contrast
        stays above *min_visibility* of its peak,
        ``2*sigma*sqrt(2 ln(1/min_visibility))``. Outside it a surface produces
        fringes too faint to locate, whatever the scan range is.
      * ``planes_per_envelope`` — how many scan planes fall inside
        ``envelope_fwhm_um`` at the recommended step. Below ~4 the three-point
        estimators have nothing to fit.
      * ``n_planes`` / ``stack_elements`` / ``stack_megabytes`` — the scan you are
        about to run and the float64 stack it produces, plus
        ``stack_within_cap`` against :data:`MAX_STACK_ELEMENTS`. This is the
        number people discover after waiting for the scan.
      * ``phase_unambiguous_step_um`` — ``lambda/4``, the largest surface step
        phase-shifting interferometry can measure without a fringe-order error.
        It is here so the two families can be compared in one place: coherence
        scanning has **no** such limit inside the scan range, and that is the
        entire reason to pay for the scan.

    What this deliberately does **not** return is a vertical *repeatability* — a
    "resolution" in nanometres. That number depends on the signal-to-noise ratio
    and on which of :data:`ESTIMATORS` you use, the estimators do not even rank
    the same way with and without noise, and an attempt to verify the textbook
    "two surfaces closer than the coherence length are unresolved" criterion
    against this module's own forward model **failed**: two reflectors 0.4
    coherence lengths apart still produce two envelope maxima, because the two
    interferograms interfere with each other and the envelope of a sum is not the
    sum of the envelopes. Rather than assert a formula that its own tests
    contradict, this operator returns only quantities it can verify, and the
    measured estimator table lives in the module docstring.

    **Raises** ``ValueError``: non-real / non-finite / string / bool parameters, a
    non-positive wavelength / bandwidth / range, a *bandwidth_um* at or above
    *wavelength_um* (a source whose spectrum reaches zero frequency is not a
    quasi-monochromatic source and the coherence-length formula does not apply to
    it), a *min_visibility* outside ``(0, 1)``, a *step_divisor* below 4 (which
    would recommend a step at or past its own Nyquist ceiling), and pixel counts
    outside ``[1, 65536]``.
    """
    op = "csi_design"
    lam = _positive(wavelength_um, "wavelength_um")
    dlam = _positive(bandwidth_um, "bandwidth_um")
    if dlam >= lam:
        raise ValueError(
            "%s: bandwidth_um = %g um is not below wavelength_um = %g um. The "
            "coherence length l_c = (4 ln2/pi) lambda^2/delta_lambda is a "
            "quasi-monochromatic result; a source whose spectrum is as wide as "
            "its centre reaches zero frequency and the formula does not describe "
            "it." % (op, dlam, lam))
    zr = _positive(z_range_um, "z_range_um")
    w = _count(width_px, "width_px", 1, 65536)
    h = _count(height_px, "height_px", 1, 65536)
    vis = _finite_scalar(min_visibility, "min_visibility")
    if not (0.0 < vis < 1.0):
        raise ValueError("%s: min_visibility must be in (0, 1), got %g — 0 makes "
                         "the capture range infinite and 1 makes it zero"
                         % (op, vis))
    div = _finite_scalar(step_divisor, "step_divisor")
    if div < 4.0:
        raise ValueError("%s: step_divisor must be >= 4 (lambda/4 is the Nyquist "
                         "ceiling itself); got %g" % (op, div))

    lc = (4.0 * np.log(2.0) / np.pi) * lam * lam / dlam   # FWHM in OPD
    env_fwhm = 0.5 * lc                                   # ... and along z
    sigma = env_fwhm / FWHM_PER_SIGMA
    period = 0.5 * lam
    max_step = 0.25 * lam
    rec_step = lam / div
    capture = 2.0 * sigma * np.sqrt(2.0 * np.log(1.0 / vis))
    n_planes = int(np.ceil(zr / rec_step)) + 1
    elems = n_planes * w * h
    if elems > (1 << 62):                                  # pragma: no cover
        raise ValueError("%s: the requested scan is absurd (%d elements)"
                         % (op, elems))
    return {
        "wavelength_um": lam,
        "bandwidth_um": dlam,
        "coherence_length_um": float(lc),
        "envelope_fwhm_um": float(env_fwhm),
        "envelope_sigma_um": float(sigma),
        "fringe_period_um": float(period),
        "max_z_step_um": float(max_step),
        "recommended_z_step_um": float(rec_step),
        "capture_range_um": float(capture),
        "planes_per_envelope": float(env_fwhm / rec_step),
        "z_range_um": zr,
        "n_planes": n_planes,
        "stack_elements": int(elems),
        "stack_megabytes": float(elems * 8 / (1 << 20)),
        "stack_within_cap": bool(elems <= MAX_STACK_ELEMENTS),
        "phase_unambiguous_step_um": float(max_step),
    }


if __name__ == "__main__":                                # pragma: no cover
    d = csi_design()
    print("interferometry: %d ops" % len(INTERFEROMETRY))
    for k, v in d.items():
        print("  %-26s %s" % (k, v))
