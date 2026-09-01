# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Photon-counting and time-resolved imaging operators (numpy + scipy only).

The layer *below* the intensity image. A conventional sensor integrates
photons into a grey value; a single-photon detector (SPAD / photon-counting
array) reports **how many** photons arrived and **when** each one arrived, and
that changes the arithmetic completely: the measurement is a Poisson count, its
noise is not a knob but ``sqrt(N)``, the detector is blind for a dead time after
every count, and the arrival-time histogram carries distance (direct
time-of-flight) and fluorescence lifetime. Those are closed-form calculations,
and this module makes them first-class operators in six families:

  * **counting** — ``photon_sample`` / ``photon_statistics`` /
    ``photon_uncertainty``: turn an expected photon rate into a Poisson
    realisation (deterministic per seed), measure whether a frame really is
    Poisson (Fano factor, ``SNR = sqrt(N)``), and attach a per-pixel error bar.
  * **transform** — ``anscombe_transform`` / ``anscombe_inverse``: the
    variance-stabilising transform that lets *any* Gaussian-noise denoiser be
    used on photon-limited data, in both the classical and the generalised
    (gain + read-noise) form, with the algebraic and the exact-unbiased inverse.
  * **spad** — ``spad_deadtime_apply`` / ``spad_deadtime_correct`` /
    ``tcspc_coates_correct``: the non-paralysable and paralysable dead-time
    laws, the exact inverse of the non-paralysable one, and Coates's estimator
    that undoes TCSPC pile-up (the early-photon bias of a first-photon
    histogram) exactly.
  * **tcspc** — ``tcspc_simulate`` / ``tcspc_irf_convolve`` /
    ``tcspc_background_subtract`` / ``tcspc_stats``: a synthetic arrival-time
    histogram with a known answer, the instrument-response (timing jitter)
    convolution, ambient-light floor removal, and the histogram descriptors
    (peak / centroid / FWHM / background / signal-to-background).
  * **dtof** — ``dtof_depth`` / ``dtof_cube_simulate`` / ``dtof_cube_depth``:
    distance from an arrival-time histogram, ``d = c*t/2``, for one pixel and
    for a whole ``(H, W, T)`` histogram cube (which is what a SPAD array
    actually produces).
  * **lifetime** — ``lifetime_fit`` / ``lifetime_phasor``: the mono-exponential
    decay fit and the phasor (frequency-domain) representation whose
    single-exponential locus is the universal semicircle.

Deliberately **not** here (already owned elsewhere — imported and composed,
never re-implemented):

  * **Gaussian read noise** is :func:`backends_aug.aug_read_noise`. The split is
    physical, not cosmetic: read noise is *additive* and signal-independent
    (amplifier + ADC), photon shot noise is *multiplicative-in-variance* and is
    the signal. :func:`anscombe_transform` is the one place they meet — its
    generalised form takes exactly the ``gain`` and ``read_sigma`` that
    ``aug_read_noise`` injects, and stabilises the *sum* of both noises.
  * **Normalised shot-noise augmentation** is
    :func:`backends_aug.aug_shot_noise`, which samples ``Poisson(v*K)/K`` and
    returns a ``[0, 1]`` image for training-data augmentation.
    :func:`photon_sample` returns the **counts themselves** (integers stored as
    float64), because every op downstream here — Fano factor, Coates, Anscombe,
    dToF — needs the count, not a rescaled grey value. Using the augmentation op
    and then multiplying back is *not* equivalent: the rescale-and-clip loses
    the counts above ``K``.
  * **Poisson deconvolution** is :func:`volrestore.vol_richardson_lucy` — RL is
    precisely the maximum-likelihood deblur *under the Poisson model this module
    generates*, so the two compose: ``photon_sample`` (or
    ``dtof_cube_simulate``) makes the photon-limited data, ``vol_gaussian_psf``
    + ``vol_richardson_lucy`` restore it. Nothing here deblurs, and nothing
    there samples.
  * **Optical design** (PSF, MTF, diffraction, depth of field) is :mod:`optics`.
    :func:`tcspc_irf_convolve` is the *temporal* analogue of a PSF blur and says
    so; the spatial one is not duplicated here.
  * **1-D signal processing** (filtering, spectra, resampling) is :mod:`dsp` and
    :mod:`funct1d`. An arrival-time histogram *is* a 1-D ``signal``, so those
    ops apply to it directly and are not re-wrapped here.

Units are encoded in every parameter name — ``_ps``, ``_ns``, ``_hz``, ``_m`` —
because a silent picosecond/nanosecond swap is a plausible-wrong answer (a
factor of 1000 in distance), not a crash. Nothing is normalised behind your back.

Conventions, stated once (the traps):

  * **Bin centres.** Bin ``k`` of a histogram covers ``[k*dt, (k+1)*dt)`` and its
    representative time is the **centre**, ``(k + 0.5)*dt``. Every op here
    (peak, centroid, sub-bin refinement, simulation) uses that same convention,
    so a synthesised pulse at ``t0`` comes back at ``t0``.
  * **The offset sign.** ``offset_ps`` is a *system delay to be removed*:
    ``t_flight = t_measured - offset_ps``. A positive offset therefore makes the
    reported distance **shorter**. A configuration that would give a negative
    flight time raises instead of returning a negative distance.
  * **Rate vs counts.** ``spad_deadtime_*`` work in **counts per second** (Hz)
    with the dead time in **nanoseconds**; everything else works in **counts**
    (photons accumulated over the acquisition). They are never mixed silently.
  * **Poisson determinism.** Every sampling op takes an integer ``seed`` and
    uses ``numpy.random.default_rng(seed)``; there is no global RNG state and no
    ``seed=None`` escape hatch. ``noise=False`` returns the exact expectation
    (no sampling at all), which is what the closed-form tests compare against.

Honest disclosure (what these ops cannot do):

  * **Poisson only.** ``photon_statistics`` reports a Fano factor, but
    ``Fano = 1`` is evidence of Poisson statistics **only on a flat field**. On
    a structured scene the spatial variance of the scene itself dominates and
    the Fano factor is large and meaningless. The op cannot tell the two apart
    and does not try — read the docstring, not the number.
  * **The dead-time inverse is non-paralysable only.** The paralysable law
    ``m = n*exp(-n*tau)`` is not injective (it peaks at ``n = 1/tau`` and then
    *falls*), so no correction op exists for it — a measured rate maps to two
    true rates and picking one silently would be a fabrication.
    :func:`spad_deadtime_apply` will simulate it; nothing here inverts it.
  * **Coates assumes one detection per cycle.** It is the exact inverse of the
    first-photon (classical TCSPC) pile-up model and nothing else. It does not
    model detector after-pulsing, dead time *within* a cycle beyond the
    first-photon rule, or multi-photon-per-cycle electronics.
  * **The mono-exponential fit is mono-exponential.** Real fluorescence is
    frequently multi-exponential; :func:`lifetime_fit` will happily return one
    number for a two-component decay and that number is a weighted blur of both.
    :func:`lifetime_phasor` is the honest companion: a multi-exponential sample
    falls *inside* the universal semicircle, and ``semicircle_residual`` says by
    how much.
  * **Everything here is a single-pixel/single-channel time model.** No
    cross-talk between SPAD pixels, no spatial correlation of ambient light, no
    optical multipath (the second bounce that puts a real dToF return where no
    surface is), and no sensor tiling/binning geometry.

Fail-closed on untrusted input, like every Fullseye module: shapes and units are
exact, NaN/Inf are rejected on the way in, negative photon counts / a zero dead
time / an all-empty histogram / a distance outside the unambiguous range all
raise an explicit ``ValueError`` naming the problem — never a silent NaN, a
silent clamp, or a silent wrap-around. Sizes are capped (:data:`MAX_BINS`,
:data:`MAX_IMAGE_ELEMENTS`, :data:`MAX_CUBE_ELEMENTS`, :data:`MAX_LAMBDA`) so a
mistyped exponent fails instead of allocating the machine's memory.
"""
from __future__ import annotations

import numpy as np
from scipy.special import erf

__all__ = [
    "photon_sample", "photon_statistics", "photon_uncertainty",
    "anscombe_transform", "anscombe_inverse",
    "spad_deadtime_apply", "spad_deadtime_correct", "tcspc_coates_correct",
    "tcspc_simulate", "tcspc_irf_convolve", "tcspc_background_subtract",
    "tcspc_stats",
    "dtof_depth", "dtof_cube_simulate", "dtof_cube_depth",
    "lifetime_fit", "lifetime_phasor",
    "PHOTONCOUNT", "SPEED_OF_LIGHT_M_S", "FWHM_PER_SIGMA",
    "MAX_BINS", "MAX_IMAGE_ELEMENTS", "MAX_CUBE_ELEMENTS", "MAX_LAMBDA",
    "DEPTH_MODES", "ANSCOMBE_INVERSE_MODES", "BACKGROUND_METHODS",
]

#: The public photon-counting operators, by name (introspection / facade wiring).
PHOTONCOUNT = [
    "photon_sample", "photon_statistics", "photon_uncertainty",
    "anscombe_transform", "anscombe_inverse",
    "spad_deadtime_apply", "spad_deadtime_correct", "tcspc_coates_correct",
    "tcspc_simulate", "tcspc_irf_convolve", "tcspc_background_subtract",
    "tcspc_stats",
    "dtof_depth", "dtof_cube_simulate", "dtof_cube_depth",
    "lifetime_fit", "lifetime_phasor",
]

#: Speed of light in vacuum, m/s (SI exact since 1983). Distances here are
#: vacuum/air distances; a medium with refractive index n divides this.
SPEED_OF_LIGHT_M_S = 299792458.0

#: ``FWHM = FWHM_PER_SIGMA * sigma`` for a Gaussian (``2*sqrt(2*ln 2)``).
FWHM_PER_SIGMA = 2.0 * np.sqrt(2.0 * np.log(2.0))

#: Largest number of time bins in one histogram (2^20 bins = 8 MB float64).
#: A real TCSPC card has 1k-64k bins; the cap only stops a mistyped exponent.
MAX_BINS = 1 << 20

#: Largest element count for a supplied 2-D count image (2^24 = 128 MB float64).
MAX_IMAGE_ELEMENTS = 1 << 24

#: Largest element count for a ``(H, W, T)`` histogram cube. The simulator needs
#: several ``(H, W, T)``-sized float64 temporaries (bin edges, erf, lambda,
#: counts), so 2^23 elements = 67 MB each is already ~0.3 GB of working set.
#: A cube grows as ``H*W*T`` — 512x512x256 is 67 M elements, i.e. 8x over this
#: cap — which is exactly the "small input, huge allocation" trap this refuses.
MAX_CUBE_ELEMENTS = 1 << 23

#: Largest Poisson rate ``lambda`` accepted by a sampling op. Beyond this the
#: Poisson distribution is numerically a Gaussian and a value this large is an
#: input mistake (numpy itself raises only above ~9.2e18).
MAX_LAMBDA = 1e12

#: Depth-estimation modes accepted by :func:`dtof_depth` / :func:`dtof_cube_depth`.
DEPTH_MODES = ("peak", "centroid", "parabolic", "gaussian")

#: Inverse modes accepted by :func:`anscombe_inverse`.
ANSCOMBE_INVERSE_MODES = ("algebraic", "unbiased")

#: Background-estimation methods accepted by :func:`tcspc_background_subtract`.
BACKGROUND_METHODS = ("median", "leading", "trailing", "quantile")


# --------------------------------------------------------------------------- #
# fail-closed input helpers (same discipline as optics.py)                     #
# --------------------------------------------------------------------------- #
def _finite_scalar(v, name: str) -> float:
    """A real, finite Python float — or ``ValueError`` naming the problem."""
    if np.ma.is_masked(v):
        raise ValueError("%s is a masked value — fill or drop it explicitly"
                         % (name,))
    if isinstance(v, (complex, np.complexfloating)):
        raise ValueError("%s is complex — a photon count / time / rate is a real "
                         "quantity; coercion would silently drop the imaginary "
                         "part" % (name,))
    if isinstance(v, (bool, np.bool_)):
        raise ValueError("%s is a bool — refusing the silent True==1 promotion"
                         % (name,))
    if isinstance(v, (str, bytes, np.str_, np.bytes_)):
        raise ValueError("%s is a string (%r) — a count/time/rate must be a "
                         "number; float('100') would silently succeed and hide "
                         "an unparsed configuration value" % (name, v))
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
        raise ValueError("%s must be an int, got %r (a float bin/cycle count is "
                         "an input mistake, not something to round)"
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


def _as_float_array(a, name: str) -> np.ndarray:
    """Coerce to float64, refusing the two silent-truncation traps."""
    if np.ma.is_masked(a):
        raise ValueError("%s is a masked array with masked (invalid) entries — "
                         "coercion would strip the mask and use the raw values "
                         "underneath; fill or drop them explicitly" % (name,))
    if np.iscomplexobj(a):
        raise ValueError("%s is complex — coercion to float64 would silently "
                         "discard the imaginary part; take .real/.imag/abs() "
                         "explicitly" % (name,))
    arr = np.ascontiguousarray(a, dtype=np.float64)
    if not np.isfinite(arr).all():
        n = int((~np.isfinite(arr)).sum())
        raise ValueError("%s has %d non-finite value(s) (NaN/Inf) — refusing"
                         % (name, n))
    return arr


def _require_counts(a, name: str, op: str) -> np.ndarray:
    """A finite, non-negative, size-capped 2-D count image."""
    arr = _as_float_array(a, name)
    if arr.ndim != 2:
        raise ValueError("%s: %s must be a 2-D (H, W) image, got a %d-D array of "
                         "shape %r — nothing is reshaped silently"
                         % (op, name, arr.ndim, tuple(np.shape(a))))
    if arr.size == 0:
        raise ValueError("%s: %s is empty (shape %r) — there is nothing to count"
                         % (op, name, arr.shape))
    if arr.size > MAX_IMAGE_ELEMENTS:
        raise ValueError("%s: %s has %d elements (shape %r), over the %d cap "
                         "(photoncount.MAX_IMAGE_ELEMENTS)"
                         % (op, name, arr.size, arr.shape, MAX_IMAGE_ELEMENTS))
    neg = int((arr < 0.0).sum())
    if neg:
        raise ValueError("%s: %s has %d negative value(s) (min %g) — a photon "
                         "count cannot be negative; if this is a background-"
                         "subtracted frame, clip it at 0 explicitly"
                         % (op, name, neg, float(arr.min())))
    return arr


def _require_hist(a, name: str, op: str, min_bins: int = 2) -> np.ndarray:
    """A finite, non-negative, size-capped 1-D arrival-time histogram."""
    arr = _as_float_array(a, name)
    if arr.ndim != 1:
        raise ValueError("%s: %s must be a 1-D histogram (one value per time "
                         "bin), got a %d-D array of shape %r"
                         % (op, name, arr.ndim, tuple(np.shape(a))))
    if arr.size < min_bins:
        raise ValueError("%s: %s must have at least %d bin(s), got %d (a "
                         "single-bin histogram has no resolvable arrival time)"
                         % (op, name, min_bins, arr.size))
    if arr.size > MAX_BINS:
        raise ValueError("%s: %s has %d bins, over the %d cap "
                         "(photoncount.MAX_BINS)" % (op, name, arr.size, MAX_BINS))
    neg = int((arr < 0.0).sum())
    if neg:
        raise ValueError("%s: %s has %d negative bin(s) (min %g) — a photon "
                         "count cannot be negative; clip a background-subtracted "
                         "histogram at 0 explicitly"
                         % (op, name, neg, float(arr.min())))
    return arr


def _require_cube(a, name: str, op: str) -> np.ndarray:
    """A finite, non-negative, size-capped ``(H, W, T)`` histogram cube."""
    arr = _as_float_array(a, name)
    if arr.ndim != 3:
        raise ValueError("%s: %s must be a 3-D (H, W, T) histogram cube — H, W "
                         "spatial and T the *time* axis, LAST — got a %d-D array "
                         "of shape %r" % (op, name, arr.ndim, tuple(np.shape(a))))
    if arr.shape[2] < 2:
        raise ValueError("%s: %s has T=%d time bin(s); at least 2 are needed for "
                         "an arrival time. If your cube is (T, H, W), transpose "
                         "it — the time axis is last here, and a (D, H, W) voxel "
                         "volume passed in unchanged returns a plausible-wrong "
                         "depth map instead of an error"
                         % (op, name, arr.shape[2]))
    if arr.size > MAX_CUBE_ELEMENTS:
        raise ValueError("%s: %s has %d elements (shape %r), over the %d cap "
                         "(photoncount.MAX_CUBE_ELEMENTS)"
                         % (op, name, arr.size, arr.shape, MAX_CUBE_ELEMENTS))
    neg = int((arr < 0.0).sum())
    if neg:
        raise ValueError("%s: %s has %d negative value(s) (min %g) — a photon "
                         "count cannot be negative"
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


def _gauss_bin_probs(edges_ps, t0_ps, sigma_ps):
    """Exact probability mass of a Gaussian pulse in each time bin.

    ``edges_ps`` is ``(..., T+1)`` (broadcastable), ``t0_ps`` the pulse centre.
    Uses the erf difference, so this is the *analytic* bin integral — no
    midpoint approximation, which is what makes the noiseless simulation an
    exact ground truth rather than an approximation of one.
    """
    z = (edges_ps - t0_ps) / (sigma_ps * np.sqrt(2.0))
    cdf = 0.5 * (1.0 + erf(z))
    return np.diff(cdf, axis=-1)


# --------------------------------------------------------------------------- #
# counting: Poisson realisation and Poisson statistics                         #
# --------------------------------------------------------------------------- #
def photon_sample(image, photons_per_unit=100.0, dark_rate=0.0, seed=0):
    """Poisson-sample an expected-photon image into an actual photon count image.

    *image* is a non-negative 2-D map of scene radiance in arbitrary units;
    ``lambda = image * photons_per_unit + dark_rate`` is the expected number of
    photons in each pixel over the exposure, and the result is one Poisson
    realisation of it. *dark_rate* is the dark-count contribution (a SPAD counts
    thermally generated carriers even in the dark) in the same photon units.

    Returns the **counts themselves** as a float64 ``(H, W)`` image (integer
    valued). That is the deliberate difference from
    :func:`backends_aug.aug_shot_noise`, which returns ``Poisson(v*K)/K`` clipped
    to ``[0, 1]`` for training-data augmentation: every operator downstream here
    (Fano factor, Anscombe, Coates, dToF) needs ``N``, and the rescale-and-clip
    is not invertible.

    ``seed`` is a required non-negative integer and the RNG is
    ``numpy.random.default_rng(seed)`` — same seed, same frame, on any machine.

    Ground truth it reproduces (pinned in ``tests/test_photoncount.py``): the
    sample mean and sample variance both converge to ``lambda``. Measured on a
    flat ``lambda = 100`` field of 512x512 pixels at seed 0 — mean 99.9796,
    Fano factor 1.001089, so the photon-limited SNR is ``sqrt(lambda)``: 9.9990
    predicted from the mean, 9.9935 actually achieved.

    **Raises** ``ValueError``: negative or non-finite *image*, negative
    *photons_per_unit* / *dark_rate*, a non-integer or negative *seed*, an image
    over :data:`MAX_IMAGE_ELEMENTS`, and — instead of letting numpy fail deep
    inside the sampler — any ``lambda`` over :data:`MAX_LAMBDA`.
    """
    img = _require_counts(image, "image", "photon_sample")
    k = _nonneg(photons_per_unit, "photons_per_unit")
    dark = _nonneg(dark_rate, "dark_rate")
    s = _seed(seed)
    lam = img * k + dark
    lam_max = float(lam.max())
    if lam_max > MAX_LAMBDA:
        raise ValueError("photon_sample: the largest expected photon count is "
                         "%g, over the %g cap (photoncount.MAX_LAMBDA) — check "
                         "photons_per_unit=%r against the image scale (max %g)"
                         % (lam_max, MAX_LAMBDA, photons_per_unit,
                            float(img.max())))
    rng = np.random.default_rng(s)
    return np.ascontiguousarray(rng.poisson(lam).astype(np.float64))


def photon_statistics(counts):
    """Poisson statistics of a photon-count frame: is it really shot-noise limited?

    Returns a dict: ``mean`` · ``variance`` (population, ``ddof=0``) ·
    ``fano_factor`` ``= variance / mean`` (**1 for a Poisson process**) ·
    ``snr_poisson`` ``= sqrt(mean)`` (the theoretical photon-limited SNR) ·
    ``snr_measured`` ``= mean / std`` (what this frame actually achieved) ·
    ``total_counts`` · ``n_samples`` · ``zero_fraction`` (the fraction of pixels
    that saw no photon at all — the honest measure of "photon starved";
    ``exp(-lambda)`` for a flat field) · ``max_counts``.

    **The Fano factor is evidence of Poisson statistics only on a flat field.**
    On a structured scene the scene's own spatial variance dominates and the
    ratio is large and meaningless — this op computes the number, it cannot tell
    you which situation you are in. Measured on the test scenes: a flat
    ``lambda = 100`` field (512x512, seed 0) gives 1.001089; the same detector
    looking at a linear ramp from 20 to 180 photons gives 22.4102. Both are
    "correct" and only one of them means anything.

    **Raises** ``ValueError``: negative, non-finite or non-2-D *counts*, fewer
    than 2 pixels (no variance), an all-zero frame (``fano_factor`` would be
    ``0/0`` — say "no photons were detected" instead of returning NaN), and a
    frame with exactly zero variance (``snr_measured`` would be ``inf``; for
    ``n >= 2`` a constant frame is not a Poisson realisation but a synthetic
    constant, i.e. an input mistake).
    """
    c = _require_counts(counts, "counts", "photon_statistics")
    if c.size < 2:
        raise ValueError("photon_statistics: need at least 2 pixels to have a "
                         "variance, got %d" % (c.size,))
    mean = float(c.mean())
    if mean == 0.0:
        raise ValueError("photon_statistics: the frame is all zero — no photons "
                         "were detected, so the Fano factor is 0/0 and the SNR "
                         "is undefined (refusing to return NaN). Increase the "
                         "exposure or check that the counts reached this op.")
    var = float(c.var())
    if var == 0.0:
        raise ValueError("photon_statistics: the frame is constant (every pixel "
                         "= %g), so the variance is exactly 0 and snr_measured "
                         "would be inf. A Poisson realisation of %d pixels is "
                         "never constant — this is a synthetic constant image, "
                         "not a photon-count measurement." % (mean, c.size))
    return {"mean": mean,
            "variance": var,
            "fano_factor": var / mean,
            "snr_poisson": float(np.sqrt(mean)),
            "snr_measured": mean / float(np.sqrt(var)),
            "total_counts": float(c.sum()),
            "n_samples": int(c.size),
            "zero_fraction": float((c == 0.0).mean()),
            "max_counts": float(c.max())}


def photon_uncertainty(counts, relative=False, zero_floor=0.0):
    """Per-pixel Poisson error bar of a photon-count frame.

    For a Poisson variable the variance *equals* the mean, so the one-sigma
    uncertainty of a single measurement ``N`` is ``sqrt(N)`` — no calibration, no
    noise model to fit. With ``relative=True`` the returned map is the relative
    uncertainty ``1/sqrt(N)`` instead (its reciprocal is the per-pixel SNR).

    *zero_floor* replaces counts below it before the square root. It exists
    because ``N = 0`` gives ``sqrt(0) = 0``, i.e. "this pixel is exactly zero
    with no uncertainty", which is wrong: the 95% Poisson upper limit for a
    single observed zero is about 3 photons. Set ``zero_floor=1.0`` for the
    common "one-count prior" convention. It is **not** applied silently — the
    default is 0.0 and the absolute map really does return 0 there.

    Returns a float64 ``(H, W)`` image.

    **Raises** ``ValueError``: negative, non-finite or non-2-D *counts*, a
    negative *zero_floor*, and — instead of returning ``inf`` —
    ``relative=True`` with any pixel at 0 after the floor (that is the division
    ``1/sqrt(0)``; pass ``zero_floor > 0`` to say what a zero should mean).
    """
    c = _require_counts(counts, "counts", "photon_uncertainty")
    floor = _nonneg(zero_floor, "zero_floor")
    if not isinstance(relative, (bool, np.bool_)):
        raise ValueError("photon_uncertainty: relative must be a bool, got %r"
                         % (type(relative).__name__,))
    eff = np.maximum(c, floor)
    sd = np.sqrt(eff)
    if not bool(relative):
        return np.ascontiguousarray(sd)
    n_zero = int((eff == 0.0).sum())
    if n_zero:
        raise ValueError("photon_uncertainty: relative=True but %d pixel(s) have "
                         "0 counts — the relative uncertainty 1/sqrt(0) is inf. "
                         "Pass zero_floor > 0 (e.g. 1.0) to state what a zero "
                         "observation is worth, or ask for the absolute map."
                         % (n_zero,))
    return np.ascontiguousarray(sd / eff)


# --------------------------------------------------------------------------- #
# transform: variance stabilisation (the bridge to Gaussian-noise denoisers)   #
# --------------------------------------------------------------------------- #
def anscombe_transform(image, gain=1.0, read_sigma=0.0, offset=0.0, clip=False):
    """Anscombe variance-stabilising transform: Poisson counts -> ~unit-variance.

    Photon-limited data has signal-dependent noise, which every classical
    denoiser (Gaussian, bilateral, NLM, wavelet, BM3D) assumes away. The Anscombe
    transform ``A(x) = 2*sqrt(x + 3/8)`` makes the variance approximately 1
    *independently of the signal*, so the standard route is transform -> denoise
    with a unit-sigma Gaussian denoiser -> :func:`anscombe_inverse`.

    The **generalised** form (Starck/Murtagh/Bijaoui) also absorbs the sensor's
    analogue chain, and takes exactly the parameters
    :func:`backends_aug.aug_read_noise` injects::

        A(x) = (2/g) * sqrt(g*(x - offset) + (3/8)*g^2 + sigma_r^2)

    with *gain* ``g`` in ADU per photon, *read_sigma* the Gaussian read noise in
    ADU and *offset* the black level in ADU. The defaults ``g=1, sigma_r=0,
    offset=0`` reduce it to the classical form exactly.

    Measured stabilisation — ``var(A(X))`` for ``X ~ Poisson(lambda)``, computed
    **exactly** by summing the Poisson pmf (no sampling, so anyone can reproduce
    these; ``tests/test_photoncount.py`` pins them and the sampled versions):

    ========  ========
    lambda    var(A)
    ========  ========
    1         0.717443
    2         0.924297
    4         0.998754
    10        1.000910
    100       1.000006
    ========  ========

    So "variance 1" is true from about 4 photons/pixel upward and **false below
    it** — at 1 photon/pixel the variance is 0.717, a 28% shortfall, which is
    the honest statement of the transform's low-count limit. Below a few photons
    an exact Poisson method (or the exact unbiased inverse, see
    :func:`anscombe_inverse`) is required.

    Returns a float64 array of the same shape as *image*.

    **Raises** ``ValueError``: non-finite *image*, non-positive *gain*, negative
    *read_sigma*, and — unless ``clip=True`` — any pixel whose argument under the
    square root is negative (which can happen for real read-noise data dipping
    below the black level). ``clip=True`` floors the argument at 0 and is the
    documented, opt-in behaviour; the default refuses rather than quietly
    manufacturing a value.
    """
    arr = _as_float_array(image, "image")
    if arr.size == 0:
        raise ValueError("anscombe_transform: image is empty")
    if arr.size > MAX_IMAGE_ELEMENTS:
        raise ValueError("anscombe_transform: image has %d elements, over the %d "
                         "cap (photoncount.MAX_IMAGE_ELEMENTS)"
                         % (arr.size, MAX_IMAGE_ELEMENTS))
    g = _positive(gain, "gain")
    sr = _nonneg(read_sigma, "read_sigma")
    off = _finite_scalar(offset, "offset")
    if not isinstance(clip, (bool, np.bool_)):
        raise ValueError("anscombe_transform: clip must be a bool, got %r"
                         % (type(clip).__name__,))
    arg = g * (arr - off) + 0.375 * g * g + sr * sr
    n_bad = int((arg < 0.0).sum())
    if n_bad:
        if not bool(clip):
            raise ValueError(
                "anscombe_transform: %d value(s) give a negative argument under "
                "the square root (min %g) — with gain=%g, read_sigma=%g, "
                "offset=%g the transform is undefined there. Pass clip=True to "
                "floor the argument at 0 (the documented convention), or fix the "
                "offset/gain calibration." % (n_bad, float(arg.min()), g, sr, off))
        arg = np.maximum(arg, 0.0)
    return np.ascontiguousarray((2.0 / g) * np.sqrt(arg))


def anscombe_inverse(values, gain=1.0, read_sigma=0.0, offset=0.0,
                     mode="algebraic"):
    """Invert :func:`anscombe_transform` — algebraically, or without bias.

    ``mode="algebraic"`` is the exact algebraic inverse of
    :func:`anscombe_transform`::

        x = ((g*A/2)^2 - (3/8)*g^2 - sigma_r^2)/g + offset

    so ``anscombe_inverse(anscombe_transform(x)) == x`` to machine precision
    (measured over 100001 values of ``x`` spanning ``[0, 1e4]``: max absolute
    error 2.7e-12, max relative error 3.7e-16 for ``x > 1``). It is, however,
    **biased**: ``E[A(X)] != A(E[X])``, so applying it to a *denoised* (i.e.
    averaged) Anscombe image underestimates the intensity.

    ``mode="unbiased"`` is the closed-form exact unbiased inverse of Makitalo &
    Foi (IEEE TIP 2011)::

        x = D^2/4 + (1/4)*sqrt(3/2)/D - (11/8)/D^2 + (5/8)*sqrt(3/2)/D^3 - 1/8

    which is defined for the **classical** transform only (``gain=1``,
    ``read_sigma=0``, ``offset=0``) — passing generalised parameters with this
    mode raises rather than returning a formula that does not apply.

    Measured bias — apply the inverse to the *ideal denoised* value
    ``D = E[A(X)]``, ``X ~ Poisson(lambda)``, and compare with ``lambda``. Both
    computed **exactly** from the Poisson pmf (no sampling):

    ========  ==================  ==================
    lambda    algebraic bias      unbiased bias
    ========  ==================  ==================
    1         -0.179361           -0.003668
    2         -0.231074           -0.006374
    4         -0.249688           +0.003779
    10        -0.250227           +0.016904
    30        -0.250019           +0.017041
    100       -0.250002           +0.011960
    ========  ==================  ==================

    The algebraic inverse converges to a **constant -1/4 photon** offset, which
    at 1 photon/pixel is a 18% error; the closed form keeps the worst case to
    0.017 photons (a 49x reduction at ``lambda = 1``, 15x at its own worst point
    near ``lambda = 10-30``). It is a closed-form *approximation* of the exact
    unbiased inverse, so it is not bias-free — those +0.017 are the honest
    residual, not round-off.

    The formula dips slightly below 0 just above its root: measured minimum
    -3.97e-05 over ``D`` in ``[1.2247, 3]``, where ``1.2247 = A(0)`` is the
    smallest value the transform can produce. The result is clipped at 0 —
    stated here rather than done quietly — because a negative photon count is
    not a number this module hands out.

    Returns a float64 array of the same shape as *values*.

    **Raises** ``ValueError``: non-finite *values*, an unknown *mode*, a
    non-positive *gain*, a negative *read_sigma*, ``mode="unbiased"`` combined
    with any non-default generalised parameter, and — instead of dividing by
    zero — ``mode="unbiased"`` with any value ``<= 0`` (the ``1/D^3`` term).
    """
    arr = _as_float_array(values, "values")
    if arr.size == 0:
        raise ValueError("anscombe_inverse: values is empty")
    if arr.size > MAX_IMAGE_ELEMENTS:
        raise ValueError("anscombe_inverse: values has %d elements, over the %d "
                         "cap (photoncount.MAX_IMAGE_ELEMENTS)"
                         % (arr.size, MAX_IMAGE_ELEMENTS))
    m = _check_mode(mode, ANSCOMBE_INVERSE_MODES, "mode", "anscombe_inverse")
    g = _positive(gain, "gain")
    sr = _nonneg(read_sigma, "read_sigma")
    off = _finite_scalar(offset, "offset")
    if m == "algebraic":
        x = ((g * arr / 2.0) ** 2 - 0.375 * g * g - sr * sr) / g + off
        return np.ascontiguousarray(x)
    if g != 1.0 or sr != 0.0 or off != 0.0:
        raise ValueError(
            "anscombe_inverse: mode='unbiased' is the closed form of Makitalo & "
            "Foi for the CLASSICAL Anscombe transform only; it is not valid for "
            "gain=%g, read_sigma=%g, offset=%g. Use mode='algebraic' for the "
            "generalised transform (and accept its bias), or transform in the "
            "classical form." % (g, sr, off))
    n_bad = int((arr <= 0.0).sum())
    if n_bad:
        raise ValueError(
            "anscombe_inverse: mode='unbiased' has 1/D, 1/D^2 and 1/D^3 terms, "
            "but %d value(s) are <= 0 (min %g) — that is a division by zero, not "
            "a small number. A(x) >= 2*sqrt(3/8) = 1.2247 for any x >= 0, so "
            "values this small did not come from anscombe_transform."
            % (n_bad, float(arr.min())))
    r32 = np.sqrt(1.5)
    inv = arr ** -1
    x = (arr * arr / 4.0 + 0.25 * r32 * inv - 1.375 * inv ** 2
         + 0.625 * r32 * inv ** 3 - 0.125)
    return np.ascontiguousarray(np.maximum(x, 0.0))


# --------------------------------------------------------------------------- #
# spad: dead time and pile-up                                                  #
# --------------------------------------------------------------------------- #
def spad_deadtime_apply(rate_hz, dead_time_ns, paralyzable=False):
    """Distort a true photon rate by the detector's dead time (counts lost).

    After every detection a SPAD is blind for a recharge (dead) time ``tau``, so
    the *measured* rate ``m`` is always below the *true* incident rate ``n``.
    Two classical laws, and this op implements both:

      * **non-paralysable** (default) — an arriving photon during the dead time is
        simply lost: ``m = n / (1 + n*tau)``. Monotonic, saturating at ``1/tau``.
      * **paralysable** (``paralyzable=True``) — an arriving photon *restarts* the
        dead time: ``m = n * exp(-n*tau)``. This law **peaks** at ``n = 1/tau``
        (where ``m = 1/(e*tau)``) and then falls, so a bright scene can read
        *darker* than a dim one. That is why no inverse op exists for it (see
        :func:`spad_deadtime_correct`).

    *rate_hz* is a 1-D array of true rates in counts per second; *dead_time_ns*
    is the dead time in nanoseconds (typical SPAD: 10-100 ns). Returns the
    measured rates as a float64 1-D array of the same length.

    Ground truth (pinned in the tests): at ``n = 1/tau`` the non-paralysable law
    gives exactly ``n/2``; the paralysable law's maximum is exactly
    ``1/(e*tau)`` at ``n = 1/tau``; both reduce to ``m = n`` as ``n*tau -> 0``.

    **Raises** ``ValueError``: negative, non-finite or non-1-D *rate_hz*, a
    non-positive *dead_time_ns*, and a non-bool *paralyzable*.
    """
    r = _as_float_array(rate_hz, "rate_hz")
    if r.ndim != 1:
        raise ValueError("spad_deadtime_apply: rate_hz must be a 1-D array of "
                         "rates, got a %d-D array" % (r.ndim,))
    if r.size == 0 or r.size > MAX_BINS:
        raise ValueError("spad_deadtime_apply: rate_hz has %d element(s); it must "
                         "be non-empty and at most %d" % (r.size, MAX_BINS))
    if (r < 0.0).any():
        raise ValueError("spad_deadtime_apply: rate_hz has negative rate(s) "
                         "(min %g) — a count rate cannot be negative"
                         % (float(r.min()),))
    tau = _positive(dead_time_ns, "dead_time_ns") * 1e-9
    if not isinstance(paralyzable, (bool, np.bool_)):
        raise ValueError("spad_deadtime_apply: paralyzable must be a bool, got %r"
                         % (type(paralyzable).__name__,))
    if bool(paralyzable):
        return np.ascontiguousarray(r * np.exp(-r * tau))
    return np.ascontiguousarray(r / (1.0 + r * tau))


def spad_deadtime_correct(measured_hz, dead_time_ns):
    """Recover the true photon rate from a dead-time-distorted measured rate.

    The exact inverse of the **non-paralysable** law of
    :func:`spad_deadtime_apply`::

        n = m / (1 - m*tau)

    A round trip ``apply -> correct`` is exact to machine precision (measured max
    elementwise relative error 6.0e-16 over 2000 rates spanning 1e3 to 5e7 Hz at
    ``tau = 50 ns``, where the measured rate reaches 71.4% of the 20 MHz
    saturation rate).

    **There is deliberately no paralysable inverse.** ``m = n*exp(-n*tau)`` is not
    injective — every measured rate below the maximum ``1/(e*tau)`` corresponds to
    *two* true rates, one below and one above ``1/tau`` — so returning one of them
    would be a fabrication dressed as a correction. Resolve the branch with an
    independent measurement (e.g. an attenuator step) and invert it yourself.

    *measured_hz* is a 1-D array of measured rates in counts per second;
    *dead_time_ns* the dead time in nanoseconds. Returns the corrected true rates
    as a float64 1-D array.

    **Raises** ``ValueError``: negative, non-finite or non-1-D *measured_hz*, a
    non-positive *dead_time_ns*, and — instead of returning ``inf`` or a negative
    rate — any measured rate at or above the saturation rate ``1/tau``, which no
    non-paralysable detector can ever produce.
    """
    m = _as_float_array(measured_hz, "measured_hz")
    if m.ndim != 1:
        raise ValueError("spad_deadtime_correct: measured_hz must be a 1-D array "
                         "of rates, got a %d-D array" % (m.ndim,))
    if m.size == 0 or m.size > MAX_BINS:
        raise ValueError("spad_deadtime_correct: measured_hz has %d element(s); "
                         "it must be non-empty and at most %d"
                         % (m.size, MAX_BINS))
    if (m < 0.0).any():
        raise ValueError("spad_deadtime_correct: measured_hz has negative rate(s) "
                         "(min %g) — a count rate cannot be negative"
                         % (float(m.min()),))
    tau = _positive(dead_time_ns, "dead_time_ns") * 1e-9
    denom = 1.0 - m * tau
    bad = int((denom <= 0.0).sum())
    if bad:
        raise ValueError(
            "spad_deadtime_correct: %d measured rate(s) are at or above the "
            "saturation rate 1/tau = %g Hz (max seen %g Hz). A non-paralysable "
            "detector with dead_time_ns=%r can never measure that, so the input "
            "is a unit error (Hz vs kHz? ns vs us?) — 1/(1 - m*tau) would return "
            "inf or a negative rate."
            % (bad, 1.0 / tau, float(m.max()), dead_time_ns))
    return np.ascontiguousarray(m / denom)


def tcspc_coates_correct(hist, cycles):
    """Undo TCSPC pile-up exactly (Coates's estimator) — the early-photon bias.

    Classical TCSPC records **at most one photon per excitation cycle**: the
    first one. Late bins are therefore starved, because the cycles in which an
    early photon arrived never reach them, and the measured histogram is biased
    toward short arrival times — a dToF depth read straight off a piled-up
    histogram is *too close*, and a fluorescence lifetime is *too short*.

    Coates's estimator inverts that exactly. With ``N_k`` the measured counts in
    bin ``k`` and ``C`` the number of excitation cycles, the number of cycles that
    survived to reach bin ``k`` is ``D_k = C - sum_{j<k} N_j``, the per-cycle
    detection probability in that bin is ``p_k = N_k / D_k`` and the pile-up-free
    per-cycle intensity is ``lambda_k = -ln(1 - p_k)``. This op returns
    ``C * lambda_k`` — the histogram the same scene would have produced if the
    detector could record every photon — so it is directly comparable to the
    measured one.

    This is an **exact** inverse, not a linearisation: build a histogram from a
    known ``lambda`` through the forward model ``N_k = C * exp(-sum_{j<k}
    lambda_j) * (1 - exp(-lambda_k))`` and Coates returns ``lambda`` to machine
    precision (measured max relative error 8.9e-16 in the tests, on a pile-up so
    severe that the last bin was suppressed to 6.8% of its true counts).

    *hist* is the 1-D measured histogram (counts per bin); *cycles* the number of
    excitation cycles (laser pulses) that produced it.

    **Raises** ``ValueError``: negative, non-finite or non-1-D *hist*, a
    non-positive or non-integer *cycles*, a histogram whose total exceeds
    *cycles* (impossible: at most one photon per cycle — a sure sign that
    *cycles* is wrong or the data are not first-photon TCSPC), and any bin that
    consumed every remaining cycle (``p_k = 1``, where ``-ln(0)`` is ``inf``).
    """
    h = _require_hist(hist, "hist", "tcspc_coates_correct")
    c = _count(cycles, "cycles", 1, 1 << 62)
    total = float(h.sum())
    if total > float(c):
        raise ValueError(
            "tcspc_coates_correct: the histogram holds %g counts but only %d "
            "excitation cycle(s) were declared. Classical TCSPC records at most "
            "one photon per cycle, so this cannot be a first-photon histogram — "
            "check the cycles argument (laser rep rate x acquisition time)."
            % (total, c))
    prior = np.concatenate(([0.0], np.cumsum(h)[:-1]))
    denom = float(c) - prior
    bad = (denom <= 0.0) & (h > 0.0)
    if bad.any():
        k = int(np.argmax(bad))
        raise ValueError(
            "tcspc_coates_correct: every cycle was already consumed before bin "
            "%d, yet that bin holds %g count(s) — the histogram is inconsistent "
            "with cycles=%d" % (k, float(h[k]), c))
    with np.errstate(divide="ignore", invalid="ignore"):
        p = np.where(denom > 0.0, h / np.maximum(denom, np.finfo(float).tiny), 0.0)
    sat = int((p >= 1.0).sum())
    if sat:
        k = int(np.argmax(p >= 1.0))
        raise ValueError(
            "tcspc_coates_correct: bin %d consumed all %g remaining cycle(s) "
            "(p = 1), so the Coates estimate -ln(1 - p) is +inf. The detector "
            "saturated completely in that bin; reduce the excitation power or "
            "record more cycles." % (k, denom[k]))
    lam = -np.log1p(-p)
    return np.ascontiguousarray(float(c) * lam)


# --------------------------------------------------------------------------- #
# tcspc: arrival-time histograms                                               #
# --------------------------------------------------------------------------- #
def tcspc_simulate(distance_m=3.0, bins=256, bin_ps=100.0, signal_photons=50.0,
                   ambient_photons=20.0, irf_fwhm_ps=200.0, seed=0, noise=True):
    """Synthesise a single-pixel photon arrival-time histogram with a known answer.

    The generative model of a direct time-of-flight (dToF) / TCSPC measurement::

        lambda_k = signal_photons * P(pulse in bin k) + ambient_photons / bins
        N_k      ~ Poisson(lambda_k)

    where the pulse is a Gaussian of full width at half maximum *irf_fwhm_ps*
    centred at the round-trip time ``t0 = 2*distance_m/c``, and ``P(pulse in bin
    k)`` is its **exact** integral over the bin (an erf difference, not a
    midpoint sample) — so with ``noise=False`` the returned histogram is an
    analytic ground truth, not an approximation of one. *ambient_photons* is the
    total background (sunlight, dark counts) spread uniformly over the window.

    ``noise=False`` returns ``lambda_k`` itself (no sampling); ``noise=True``
    draws one Poisson realisation from ``numpy.random.default_rng(seed)``.

    Returns a float64 1-D histogram of length *bins*. The unambiguous range is
    ``c * bins * bin_ps / 2`` — 3.84 m at the defaults (256 bins x 100 ps), with
    a bin resolution of 1.50 cm.

    The pulse is **not** renormalised to the window: a target near the far edge
    genuinely loses the tail of its pulse, exactly as a real sensor does, and the
    total signal comes back slightly below *signal_photons*. Renormalising would
    have made the truncated pulse asymmetric and biased its centroid.

    **Raises** ``ValueError``: a non-positive *distance_m*, a *bins* outside
    ``[2, MAX_BINS]``, a non-positive *bin_ps* / *irf_fwhm_ps*, negative photon
    budgets, a non-integer or negative *seed*, a non-bool *noise*, and — instead
    of wrapping the pulse silently to a short distance — a *distance_m* whose
    round-trip time falls outside the ``bins * bin_ps`` window.
    """
    d = _positive(distance_m, "distance_m")
    n = _count(bins, "bins", 2, MAX_BINS)
    dt = _positive(bin_ps, "bin_ps")
    sig = _nonneg(signal_photons, "signal_photons")
    amb = _nonneg(ambient_photons, "ambient_photons")
    fwhm = _positive(irf_fwhm_ps, "irf_fwhm_ps")
    s = _seed(seed)
    if not isinstance(noise, (bool, np.bool_)):
        raise ValueError("tcspc_simulate: noise must be a bool, got %r"
                         % (type(noise).__name__,))
    t0 = 2.0 * d / SPEED_OF_LIGHT_M_S * 1e12          # s -> ps
    window = n * dt
    if t0 > window:
        raise ValueError(
            "tcspc_simulate: distance_m=%g gives a round-trip time of %g ps, "
            "past the %g ps window (bins=%d x bin_ps=%g). A real sensor would "
            "alias this into a short distance; refusing to fabricate that. The "
            "unambiguous range here is %g m."
            % (d, t0, window, n, dt,
               SPEED_OF_LIGHT_M_S * window * 1e-12 / 2.0))
    sigma = fwhm / FWHM_PER_SIGMA
    edges = np.arange(n + 1, dtype=np.float64) * dt
    lam = sig * _gauss_bin_probs(edges, t0, sigma) + amb / float(n)
    lam = np.maximum(lam, 0.0)                        # erf round-off can dip <0
    if not bool(noise):
        return np.ascontiguousarray(lam)
    lam_max = float(lam.max())
    if lam_max > MAX_LAMBDA:
        raise ValueError("tcspc_simulate: peak expected count %g is over the %g "
                         "cap (photoncount.MAX_LAMBDA)" % (lam_max, MAX_LAMBDA))
    rng = np.random.default_rng(s)
    return np.ascontiguousarray(rng.poisson(lam).astype(np.float64))


def tcspc_irf_convolve(hist, bin_ps=100.0, irf_fwhm_ps=200.0, truncate=4.0):
    """Blur an arrival-time histogram by the instrument response (timing jitter).

    The temporal analogue of a PSF convolution: a detector's timing uncertainty
    (SPAD jitter + TDC quantisation + laser pulse width) smears every arrival
    time by the instrument response function, here a Gaussian of full width at
    half maximum *irf_fwhm_ps*. The kernel is the **exact bin integral** of that
    Gaussian (erf differences), normalised to sum 1, truncated at
    ``+-truncate*sigma`` and forced to odd length so the convolution is centred.

    Ground truth: convolving a unit spike with ``irf_fwhm_ps = 500`` at
    ``bin_ps = 50`` returns a profile whose measured FWHM (via
    :func:`tcspc_stats`) is 500.0 ps, and whose centroid is unmoved to 1.1e-13 ps.

    Total counts are preserved *except* at the window edges, where
    ``mode='same'`` discards the tail that falls outside — measured 1.4e-10 loss
    for a pulse in the middle of the window, but a genuine loss for a pulse
    within a few sigma of either end.

    Returns a float64 1-D histogram of the same length as *hist*.

    **Raises** ``ValueError``: negative, non-finite or non-1-D *hist*, a
    non-positive *bin_ps* / *irf_fwhm_ps* / *truncate*, an IRF sigma below
    1e-3 bins (the kernel would be a delta and the op a no-op — say so instead
    of pretending to blur), and a kernel that would be longer than the
    :data:`MAX_BINS` cap.
    """
    h = _require_hist(hist, "hist", "tcspc_irf_convolve")
    dt = _positive(bin_ps, "bin_ps")
    fwhm = _positive(irf_fwhm_ps, "irf_fwhm_ps")
    tr = _positive(truncate, "truncate")
    sigma_bins = fwhm / FWHM_PER_SIGMA / dt
    if sigma_bins < 1e-3:
        raise ValueError(
            "tcspc_irf_convolve: irf_fwhm_ps=%g at bin_ps=%g is %g bins of "
            "sigma — far below one bin, so the kernel is a delta and this op "
            "would silently do nothing. The histogram is already at the timing "
            "resolution you asked for." % (fwhm, dt, sigma_bins))
    r = int(np.ceil(tr * sigma_bins))
    if 2 * r + 1 > MAX_BINS:
        raise ValueError("tcspc_irf_convolve: the kernel would be %d bins long, "
                         "over the %d cap (photoncount.MAX_BINS) — check "
                         "irf_fwhm_ps=%r against bin_ps=%r"
                         % (2 * r + 1, MAX_BINS, irf_fwhm_ps, bin_ps))
    idx = np.arange(-r, r + 1, dtype=np.float64)
    edges = np.concatenate((idx - 0.5, [idx[-1] + 0.5]))
    k = _gauss_bin_probs(edges, 0.0, sigma_bins)
    k = np.maximum(k, 0.0)
    ksum = float(k.sum())
    if ksum <= 0.0:                                   # unreachable in practice
        raise ValueError("tcspc_irf_convolve: the IRF kernel underflowed to all "
                         "zeros for irf_fwhm_ps=%r / bin_ps=%r" % (irf_fwhm_ps,
                                                                   bin_ps))
    return np.ascontiguousarray(np.convolve(h, k / ksum, mode="same"))


def tcspc_background_subtract(hist, method="median", leading_bins=8,
                              quantile=0.5, scale=1.0):
    """Remove the ambient-light / dark-count floor from an arrival-time histogram.

    Outdoors, most of what a dToF sensor counts is sunlight: a roughly uniform
    pedestal under the return pulse. It biases the centroid toward the middle of
    the window (a floor of ``b`` per bin pulls the first moment toward
    ``window/2``) and it inflates the apparent signal, so it is removed before
    any depth or lifetime estimate.

    The level is estimated by *method* and then **subtracted** (the sign trap:
    the result is ``hist - level``, clipped at 0, never ``hist + level``):

      * ``"median"`` (default) — the median of every bin. Robust while the pulse
        occupies well under half the window, which is the normal dToF case.
      * ``"leading"`` — the mean of the first *leading_bins* bins, the classical
        choice when the pulse is known to arrive late (a far target).
      * ``"trailing"`` — the mean of the last *leading_bins* bins, for
        fluorescence decays where the tail is background.
      * ``"quantile"`` — the given *quantile* of all bins, for tuning by hand.

    *scale* multiplies the estimated level before subtraction (``scale=1.2`` for
    a deliberately aggressive removal). Clipping at 0 means the result is a valid
    non-negative histogram that the rest of this module will accept.

    Ground truth: on a synthetic histogram with a known flat pedestal of 20
    counts/bin under a pulse covering 3% of the window, the median estimate
    recovers 20.0 exactly and the recovered pulse area is within 0.6% of the
    truth (pinned in the tests).

    Returns a float64 1-D histogram of the same length as *hist*.

    **Raises** ``ValueError``: negative, non-finite or non-1-D *hist*, an unknown
    *method*, a *leading_bins* outside ``[1, len(hist)]``, a *quantile* outside
    ``[0, 1]``, and a negative *scale*.
    """
    h = _require_hist(hist, "hist", "tcspc_background_subtract")
    m = _check_mode(method, BACKGROUND_METHODS, "method",
                    "tcspc_background_subtract")
    sc = _nonneg(scale, "scale")
    if m == "median":
        level = float(np.median(h))
    elif m == "quantile":
        q = _finite_scalar(quantile, "quantile")
        if not 0.0 <= q <= 1.0:
            raise ValueError("tcspc_background_subtract: quantile must be in "
                             "[0, 1], got %g" % (q,))
        level = float(np.quantile(h, q))
    else:
        nb = _count(leading_bins, "leading_bins", 1, h.size)
        level = float(h[:nb].mean() if m == "leading" else h[-nb:].mean())
    return np.ascontiguousarray(np.maximum(h - sc * level, 0.0))


def tcspc_stats(hist, bin_ps=100.0):
    """Descriptors of an arrival-time histogram: peak, centroid, width, background.

    Returns a dict: ``total_counts`` · ``peak_bin`` (int) · ``peak_counts`` ·
    ``peak_time_ps`` (the **centre** of the peak bin, ``(k + 0.5)*bin_ps``) ·
    ``centroid_ps`` (the first moment over the whole histogram, background
    included — run :func:`tcspc_background_subtract` first if that matters) ·
    ``fwhm_ps`` (full width at half maximum *above the background*, by linear
    interpolation of the two half-crossings around the peak) ·
    ``background_per_bin`` (the median bin, the same robust estimate
    :func:`tcspc_background_subtract` uses) · ``signal_counts``
    (``total - background*bins``) · ``sbr`` (signal-to-background ratio, or
    ``None`` when the background estimate is 0) · ``n_bins`` · ``window_ps``.

    ``fwhm_ps`` is ``None`` — never a fabricated number — when the profile does
    not cross the half-maximum on both sides of the peak, which is exactly what a
    monotone fluorescence decay does (its peak is bin 0). A ``None`` here means
    "this histogram has no width in the FWHM sense", not "the measurement
    failed".

    Ground truth: for a noiseless Gaussian pulse of FWHM 500 ps at 100 ps bins
    the measured ``fwhm_ps`` is 500.0 and ``centroid_ps`` matches the analytic
    ``2d/c`` to 3.9e-11 ps (pinned in the tests).

    **Raises** ``ValueError``: negative, non-finite or non-1-D *hist*, a
    non-positive *bin_ps*, and an all-zero histogram (no photon arrived, so
    there is no arrival time; the centroid would be ``0/0``).
    """
    h = _require_hist(hist, "hist", "tcspc_stats")
    dt = _positive(bin_ps, "bin_ps")
    total = float(h.sum())
    if total <= 0.0:
        raise ValueError("tcspc_stats: the histogram is all zero — no photons "
                         "were detected, so there is no arrival time to report "
                         "(the centroid would be 0/0). This is a real outcome "
                         "for a photon-starved acquisition; handle it upstream.")
    n = int(h.size)
    centres = (np.arange(n, dtype=np.float64) + 0.5) * dt
    k = int(np.argmax(h))
    peak = float(h[k])
    bg = float(np.median(h))
    half = bg + 0.5 * (peak - bg)
    fwhm = None
    if peak > bg:
        left = right = None
        for i in range(k, 0, -1):
            if h[i - 1] < half <= h[i]:
                left = (i - 1) + (half - h[i - 1]) / (h[i] - h[i - 1])
                break
        for i in range(k, n - 1):
            if h[i + 1] < half <= h[i]:
                right = i + (h[i] - half) / (h[i] - h[i + 1])
                break
        if left is not None and right is not None:
            fwhm = float((right - left) * dt)
    signal = total - bg * n
    return {"total_counts": total,
            "peak_bin": k,
            "peak_counts": peak,
            "peak_time_ps": float(centres[k]),
            "centroid_ps": float((h * centres).sum() / total),
            "fwhm_ps": fwhm,
            "background_per_bin": bg,
            "signal_counts": float(signal),
            "sbr": float(signal / (bg * n)) if bg > 0.0 else None,
            "n_bins": n,
            "window_ps": float(n * dt)}


# --------------------------------------------------------------------------- #
# dtof: distance from arrival time                                             #
# --------------------------------------------------------------------------- #
def _subbin_delta(prev, peak, nxt, mode, log_domain):
    """Sub-bin offset of a peak from three samples (vectorised, elementwise).

    Parabolic vertex of ``(-1, prev), (0, peak), (1, nxt)``. With
    *log_domain* the parabola is fitted to ``log`` of the samples, which is
    **exact** for a Gaussian pulse. Returns the offset and a validity mask.
    """
    a, b, c = prev, peak, nxt
    if log_domain:
        ok = (a > 0.0) & (b > 0.0) & (c > 0.0)
        with np.errstate(divide="ignore", invalid="ignore"):
            a = np.where(ok, np.log(np.maximum(a, np.finfo(float).tiny)), 0.0)
            b = np.where(ok, np.log(np.maximum(b, np.finfo(float).tiny)), 0.0)
            c = np.where(ok, np.log(np.maximum(c, np.finfo(float).tiny)), 0.0)
    else:
        ok = np.ones(np.shape(b), dtype=bool) if np.ndim(b) else np.array(True)
    denom = a - 2.0 * b + c
    ok = ok & (denom != 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        delta = np.where(ok, 0.5 * (a - c) / np.where(ok, denom, 1.0), 0.0)
    # A vertex further than half a bin from the sampled maximum means the three
    # samples do not describe a peak (noise, or a shoulder); reject it rather
    # than reporting a time in the neighbouring bin.
    ok = ok & (np.abs(delta) <= 0.5)
    return np.where(ok, delta, 0.0), ok


def _fractional_peak(counts, mode, op):
    """Fractional bin index of the return, along the last axis.

    Returns ``(index, valid)``; ``valid`` is False where a sub-bin refinement was
    impossible (peak at an edge bin, flat neighbourhood, non-positive samples).
    """
    k = np.argmax(counts, axis=-1)
    kf = k.astype(np.float64)
    if mode == "peak":
        return kf, np.ones(kf.shape, dtype=bool)
    n = counts.shape[-1]
    if mode == "centroid":
        total = counts.sum(axis=-1)
        idx = np.arange(n, dtype=np.float64)
        with np.errstate(divide="ignore", invalid="ignore"):
            cen = np.where(total > 0.0,
                           (counts * idx).sum(axis=-1) / np.where(total > 0.0,
                                                                  total, 1.0),
                           0.0)
        return cen, total > 0.0
    interior = (k > 0) & (k < n - 1)
    ki = np.clip(k, 1, n - 2)
    prev = np.take_along_axis(counts, ki[..., None] - 1, axis=-1)[..., 0]
    here = np.take_along_axis(counts, ki[..., None], axis=-1)[..., 0]
    nxt = np.take_along_axis(counts, ki[..., None] + 1, axis=-1)[..., 0]
    delta, ok = _subbin_delta(prev, here, nxt, mode, mode == "gaussian")
    ok = ok & interior
    return kf + np.where(ok, delta, 0.0), ok


def dtof_depth(hist, bin_ps=100.0, mode="peak", offset_ps=0.0,
               subtract_background=False):
    """Distance from a photon arrival-time histogram: ``d = c*t/2``.

    Direct time-of-flight. The light travels to the target and back, so the
    one-way distance is **half** the round-trip time times the speed of light.
    *bin_ps* is the width of one time bin (a 100 ps bin is 1.50 cm of depth).

    Four estimators, from crudest to sharpest:

      * ``"peak"`` — the centre of the fullest bin. Quantised to the bin grid;
        the error is uniform in ``+-half`` a bin (``+-0.75 cm`` at 100 ps).
      * ``"centroid"`` — the first moment of the whole histogram. Exact for a
        symmetric pulse *with no background*, and badly biased toward the middle
        of the window with one — pass ``subtract_background=True``.
      * ``"parabolic"`` — a parabola through the peak bin and its two neighbours.
        Sub-bin, cheap, and biased for a Gaussian pulse.
      * ``"gaussian"`` — the same parabola fitted to the **log** of those three
        samples, which is the exact vertex for a Gaussian pulse.

    Measured on a noiseless simulated return at 2.4371 m (256 bins x 100 ps,
    500 ps IRF), absolute error: ``peak`` 4.5 mm, ``centroid`` (background
    subtracted) 1.2e-11 mm, ``parabolic`` 0.86 mm, ``gaussian`` 0.0093 mm. With
    Poisson noise at 200 signal / 200 ambient photons the same four give 4.5 mm,
    2.5 mm, 3.7 mm and 3.2 mm — i.e. **once shot noise dominates, the estimator
    hardly matters**, which is the honest reason not to over-engineer it.

    *offset_ps* is a **system delay to remove**: ``t_flight = t_measured -
    offset_ps``, so a positive offset makes the answer *closer*. Returns the
    distance in metres as a float.

    **Raises** ``ValueError``: negative, non-finite, non-1-D or all-zero *hist*,
    a non-positive *bin_ps*, an unknown *mode*, a non-finite *offset_ps*, a peak
    in the first or last bin with a sub-bin *mode* (there is no neighbour to fit
    to — use ``"peak"``), a degenerate three-sample fit, and — instead of
    returning a negative distance — an *offset_ps* larger than the measured
    arrival time.
    """
    h = _require_hist(hist, "hist", "dtof_depth")
    dt = _positive(bin_ps, "bin_ps")
    m = _check_mode(mode, DEPTH_MODES, "mode", "dtof_depth")
    off = _finite_scalar(offset_ps, "offset_ps")
    if not isinstance(subtract_background, (bool, np.bool_)):
        raise ValueError("dtof_depth: subtract_background must be a bool, got %r"
                         % (type(subtract_background).__name__,))
    if float(h.sum()) <= 0.0:
        raise ValueError("dtof_depth: the histogram is all zero — no photons "
                         "returned, so there is no distance to report. This is a "
                         "real outcome (a dark or distant target); handle it "
                         "upstream rather than reading 0 m as a measurement.")
    work = h
    if bool(subtract_background):
        work = np.maximum(h - float(np.median(h)), 0.0)
        if float(work.sum()) <= 0.0:
            raise ValueError("dtof_depth: subtract_background removed every "
                             "count — more than half the bins are at or above "
                             "the peak, so this histogram is background only "
                             "(no detectable return).")
    idx, ok = _fractional_peak(work, m, "dtof_depth")
    if not bool(ok):
        n = int(work.size)
        k = int(np.argmax(work))
        if m in ("parabolic", "gaussian") and (k == 0 or k == n - 1):
            raise ValueError(
                "dtof_depth: mode=%r needs a bin on each side of the peak, but "
                "the peak is at bin %d of %d (the window edge). Use mode='peak' "
                "or widen the time window." % (m, k, n))
        raise ValueError(
            "dtof_depth: mode=%r could not refine the peak at bin %d — the three "
            "samples (%g, %g, %g) do not describe a peak (flat, or non-positive "
            "for the log fit). Use mode='peak'."
            % (m, k, float(work[max(k - 1, 0)]), float(work[k]),
               float(work[min(k + 1, work.size - 1)])))
    t_ps = (float(idx) + 0.5) * dt - off
    if t_ps < 0.0:
        raise ValueError(
            "dtof_depth: offset_ps=%g exceeds the measured arrival time %g ps, "
            "which would give a negative distance. offset_ps is a system delay "
            "to SUBTRACT (t_flight = t_measured - offset_ps); check its sign and "
            "units." % (off, (float(idx) + 0.5) * dt))
    return float(SPEED_OF_LIGHT_M_S * t_ps * 1e-12 / 2.0)


def dtof_cube_simulate(depth, bins=256, bin_ps=100.0, reflectivity=None,
                       signal_photons=20.0, ambient_photons=5.0,
                       irf_fwhm_ps=200.0, seed=0, noise=True):
    """Synthesise the ``(H, W, T)`` photon histogram cube a SPAD array produces.

    The per-pixel version of :func:`tcspc_simulate`: every pixel of the *depth*
    map (metres, one-way distance) gets a Gaussian return at its own round-trip
    time ``2d/c``, scaled by *signal_photons* times that pixel's *reflectivity*,
    on a uniform ambient pedestal of ``ambient_photons/bins`` per bin, Poisson
    sampled with ``numpy.random.default_rng(seed)``.

    The output is the cube that :func:`dtof_cube_depth` inverts, and the axis
    order is **(H, W, T) with time LAST** — the same layout a SPAD array streams.
    That is not the ``(D, H, W)`` of a :mod:`volops` voxel volume; the two are
    both 3-D float arrays and swapping them silently produces a plausible-wrong
    depth map, which is why :func:`dtof_cube_depth` checks and says so.

    ``noise=False`` returns the exact expectation cube (no sampling).

    Ground truth: with ``noise=False`` the per-pixel centroid of the cube returns
    the input depth map to 8.9e-15 m (pinned in the tests) — the pulse integral
    is analytic, so the only error is float round-off.

    **Raises** ``ValueError``: a non-2-D, non-finite or non-positive *depth*, a
    *reflectivity* that is negative or not the same shape as *depth*, a *bins*
    outside ``[2, MAX_BINS]``, non-positive *bin_ps* / *irf_fwhm_ps*, negative
    photon budgets, a non-integer *seed*, a cube over
    :data:`MAX_CUBE_ELEMENTS` (``H*W*bins`` grows fast — 512x512x256 is 8x the
    cap), and any depth whose round-trip time falls outside the time window
    (which a real sensor would alias into a short distance).
    """
    d = _as_float_array(depth, "depth")
    if d.ndim != 2:
        raise ValueError("dtof_cube_simulate: depth must be a 2-D (H, W) map in "
                         "metres, got a %d-D array" % (d.ndim,))
    if d.size == 0:
        raise ValueError("dtof_cube_simulate: depth is empty")
    if (d <= 0.0).any():
        raise ValueError("dtof_cube_simulate: depth has %d non-positive value(s) "
                         "(min %g) — a distance must be > 0 metres"
                         % (int((d <= 0.0).sum()), float(d.min())))
    n = _count(bins, "bins", 2, MAX_BINS)
    dt = _positive(bin_ps, "bin_ps")
    sig = _nonneg(signal_photons, "signal_photons")
    amb = _nonneg(ambient_photons, "ambient_photons")
    fwhm = _positive(irf_fwhm_ps, "irf_fwhm_ps")
    s = _seed(seed)
    if not isinstance(noise, (bool, np.bool_)):
        raise ValueError("dtof_cube_simulate: noise must be a bool, got %r"
                         % (type(noise).__name__,))
    if reflectivity is None:
        refl = np.ones_like(d)
    else:
        refl = _as_float_array(reflectivity, "reflectivity")
        if refl.shape != d.shape:
            raise ValueError("dtof_cube_simulate: reflectivity has shape %r but "
                             "depth has shape %r — they must match pixel for "
                             "pixel" % (refl.shape, d.shape))
        if (refl < 0.0).any():
            raise ValueError("dtof_cube_simulate: reflectivity has %d negative "
                             "value(s) (min %g)"
                             % (int((refl < 0.0).sum()), float(refl.min())))
    total = int(d.size) * n
    if total > MAX_CUBE_ELEMENTS:
        raise ValueError(
            "dtof_cube_simulate: the cube would be %dx%dx%d = %d elements, over "
            "the %d cap (photoncount.MAX_CUBE_ELEMENTS, ~%d MB per float64 "
            "temporary and this op needs several). Crop the depth map or use "
            "fewer bins." % (d.shape[0], d.shape[1], n, total, MAX_CUBE_ELEMENTS,
                             MAX_CUBE_ELEMENTS * 8 // (1 << 20)))
    t0 = 2.0 * d / SPEED_OF_LIGHT_M_S * 1e12
    window = n * dt
    if float(t0.max()) > window:
        raise ValueError(
            "dtof_cube_simulate: the farthest depth %g m has a round-trip time "
            "of %g ps, past the %g ps window (bins=%d x bin_ps=%g). The "
            "unambiguous range here is %g m; refusing to alias it silently."
            % (float(d.max()), float(t0.max()), window, n, dt,
               SPEED_OF_LIGHT_M_S * window * 1e-12 / 2.0))
    sigma = fwhm / FWHM_PER_SIGMA
    edges = np.arange(n + 1, dtype=np.float64) * dt
    probs = _gauss_bin_probs(edges[None, None, :], t0[:, :, None], sigma)
    lam = sig * refl[:, :, None] * probs + amb / float(n)
    np.maximum(lam, 0.0, out=lam)
    if not bool(noise):
        return np.ascontiguousarray(lam)
    lam_max = float(lam.max())
    if lam_max > MAX_LAMBDA:
        raise ValueError("dtof_cube_simulate: peak expected count %g is over the "
                         "%g cap (photoncount.MAX_LAMBDA)"
                         % (lam_max, MAX_LAMBDA))
    rng = np.random.default_rng(s)
    return np.ascontiguousarray(rng.poisson(lam).astype(np.float64))


def dtof_cube_depth(cube, bin_ps=100.0, mode="peak", offset_ps=0.0,
                    min_counts=1.0, empty_value=0.0, subtract_background=False):
    """Depth map from a ``(H, W, T)`` photon histogram cube — the dToF inversion.

    The array version of :func:`dtof_depth`, with the same four *mode* estimators
    and the same ``t_flight = t_measured - offset_ps`` sign convention. The time
    axis is **last**: a ``(D, H, W)`` voxel volume passed in here would be read as
    ``W`` time bins and return a plausible-wrong depth map, so the shape is
    checked and the error message says exactly that.

    Pixels whose total counts are below *min_counts* are set to *empty_value*
    (default 0.0, a value no real return can have since ``d > 0``). Set
    ``empty_value=float('nan')`` if you would rather propagate a NaN — that is an
    opt-in, never the default, because a NaN depth map silently poisons every
    downstream reduction.

    Where a sub-bin *mode* cannot be applied to a pixel — the peak is in the
    first or last bin, or the three samples are flat / non-positive for the log
    fit — that pixel **falls back to the bin-centre (``"peak"``) estimate**. A
    per-pixel exception would be useless on a megapixel cube; the fallback is
    documented here and pinned in the tests, and it degrades to the coarser
    estimator rather than to a wrong one.

    Ground truth: on a noiseless simulated cube of a tilted plane from 1.0 to
    3.0 m (256 bins x 100 ps) the RMS depth error is 4.3 mm for ``"peak"``,
    8.9e-15 m for ``"centroid"``, 0.79 mm for ``"parabolic"`` and 6.4e-6 m for
    ``"gaussian"``. With Poisson noise (20 signal / 5 ambient photons per pixel)
    the same four give 5.5 mm, 0.24 m, 5.0 mm and 4.7 mm — the centroid
    collapses because the ambient pedestal dominates, which is why
    ``subtract_background=True`` exists.

    Returns a float64 ``(H, W)`` depth map in metres.

    **Raises** ``ValueError``: a cube that is not 3-D / has fewer than 2 time
    bins / holds negative counts / exceeds :data:`MAX_CUBE_ELEMENTS`, a
    non-positive *bin_ps*, an unknown *mode*, a negative *min_counts*, a
    non-finite *empty_value* other than NaN, and — instead of returning negative
    distances — an *offset_ps* that exceeds the measured arrival time of any
    valid pixel (a mis-signed or mis-scaled calibration delay).
    """
    c = _require_cube(cube, "cube", "dtof_cube_depth")
    dt = _positive(bin_ps, "bin_ps")
    m = _check_mode(mode, DEPTH_MODES, "mode", "dtof_cube_depth")
    off = _finite_scalar(offset_ps, "offset_ps")
    mc = _nonneg(min_counts, "min_counts")
    if not isinstance(subtract_background, (bool, np.bool_)):
        raise ValueError("dtof_cube_depth: subtract_background must be a bool, "
                         "got %r" % (type(subtract_background).__name__,))
    ev = float(empty_value)
    if not np.isfinite(ev) and not np.isnan(ev):
        raise ValueError("dtof_cube_depth: empty_value must be finite or NaN, "
                         "got %r (an infinite depth would poison every "
                         "downstream reduction)" % (empty_value,))
    work = c
    if bool(subtract_background):
        work = np.maximum(c - np.median(c, axis=-1, keepdims=True), 0.0)
    valid = c.sum(axis=-1) >= mc
    if bool(subtract_background):
        valid = valid & (work.sum(axis=-1) > 0.0)
    idx, ok = _fractional_peak(work, m, "dtof_cube_depth")
    if m != "peak":
        # documented per-pixel fallback to the bin-centre estimate
        idx = np.where(ok, idx, np.argmax(work, axis=-1).astype(np.float64))
    t_ps = (idx + 0.5) * dt - off
    bad = valid & (t_ps < 0.0)
    if bad.any():
        raise ValueError(
            "dtof_cube_depth: offset_ps=%g exceeds the measured arrival time of "
            "%d valid pixel(s) (earliest %g ps), which would give a negative "
            "distance. offset_ps is a system delay to SUBTRACT (t_flight = "
            "t_measured - offset_ps); check its sign and units."
            % (off, int(bad.sum()), float(((idx + 0.5) * dt)[bad].min())))
    depth = SPEED_OF_LIGHT_M_S * t_ps * 1e-12 / 2.0
    return np.ascontiguousarray(np.where(valid, depth, ev))


# --------------------------------------------------------------------------- #
# lifetime: time-resolved decay analysis                                       #
# --------------------------------------------------------------------------- #
def lifetime_fit(decay, bin_ps=100.0, background=None, min_counts=1.0,
                 start_bin=None):
    """Mono-exponential fluorescence lifetime from a TCSPC decay histogram.

    Fits ``I(t) = A*exp(-t/tau) + b`` by a **Poisson-weighted log-linear least
    squares**: the background is removed, the logarithm of the remaining counts
    is linear in ``t`` with slope ``-1/tau``, and each bin is weighted by its own
    counts because ``var(ln N) ~ 1/N`` — which is exactly the Poisson error bar
    :func:`photon_uncertainty` reports.

    The fit starts at the **peak** bin by default (or at *start_bin* if given):
    the rising edge before the peak is the instrument response convolved with the
    decay, not the decay, and including it biases the lifetime short. Only bins
    with more than *min_counts* counts after background removal take part (the
    logarithm of 0 is ``-inf``, and single-count tail bins carry almost no
    information but huge log-scatter).

    *background* is the flat pedestal per bin; ``None`` (default) estimates it as
    the median of the **last decile** of bins, which for a decay is tail. Pass
    ``0.0`` to state that the data are already background free.

    Returns a dict: ``lifetime_ps`` · ``amplitude`` (the fitted ``A`` at ``t=0``
    of the fit window, in counts per bin) · ``background`` (the level used) ·
    ``start_bin`` · ``n_bins_used`` · ``r_squared`` (of the weighted log fit).

    Ground truth: on a **noiseless** exponential the recovery is exact —
    ``lifetime_ps`` matches the input to a measured 1.1e-12 relative error at
    ``tau = 2000 ps``, and *that stays true when the histogram is built by
    integrating the exponential over each bin* rather than sampling it, because
    bin integration multiplies every bin by the same constant and so cannot
    change the slope. With Poisson noise at 20000 total photons the recovered
    lifetime is 2001.6 ps (0.08% error, seed 0).

    **Raises** ``ValueError``: negative, non-finite or non-1-D *decay*, a
    non-positive *bin_ps*, a negative *background* / *min_counts*, a *start_bin*
    outside the histogram, fewer than 2 usable bins after the background and
    threshold cuts (a straight line needs two points), a degenerate fit (all
    usable bins at the same time), and — instead of returning a negative
    lifetime — a fitted slope that is zero or positive, i.e. a profile that does
    not decay.
    """
    h = _require_hist(decay, "decay", "lifetime_fit")
    dt = _positive(bin_ps, "bin_ps")
    mc = _nonneg(min_counts, "min_counts")
    n = int(h.size)
    if background is None:
        tail = max(1, n // 10)
        bg = float(np.median(h[-tail:]))
    else:
        bg = _nonneg(background, "background")
    if start_bin is None:
        k0 = int(np.argmax(h))
    else:
        k0 = _count(start_bin, "start_bin", 0, n - 1)
    y = h[k0:] - bg
    t = (np.arange(k0, n, dtype=np.float64) + 0.5) * dt
    use = y > mc
    if int(use.sum()) < 2:
        raise ValueError(
            "lifetime_fit: only %d bin(s) survive background=%g and "
            "min_counts=%g from start_bin=%d — a log-linear fit needs at least "
            "2. Either the decay is buried in the background (peak %g, "
            "background %g) or min_counts is too high."
            % (int(use.sum()), bg, mc, k0, float(h.max()), bg))
    tt, yy = t[use], y[use]
    if float(tt.max() - tt.min()) <= 0.0:
        raise ValueError("lifetime_fit: every usable bin is at the same time — "
                         "no slope can be fitted")
    w = yy                                      # var(ln N) ~ 1/N  ->  weight N
    ly = np.log(yy)
    sw = w.sum()
    mt = float((w * tt).sum() / sw)
    ml = float((w * ly).sum() / sw)
    sxx = float((w * (tt - mt) ** 2).sum())
    if sxx <= 0.0:
        raise ValueError("lifetime_fit: the weighted time spread is zero — the "
                         "fit is degenerate")
    slope = float((w * (tt - mt) * (ly - ml)).sum() / sxx)
    if slope >= 0.0:
        raise ValueError(
            "lifetime_fit: the fitted log-slope is %g (>= 0), i.e. the profile "
            "does not decay over the fit window — the lifetime -1/slope would be "
            "infinite or negative. Check start_bin=%d (the fit must start at or "
            "after the peak) and the background (%g)." % (slope, k0, bg))
    intercept = ml - slope * mt
    pred = intercept + slope * tt
    ss_res = float((w * (ly - pred) ** 2).sum())
    ss_tot = float((w * (ly - ml) ** 2).sum())
    return {"lifetime_ps": float(-1.0 / slope),
            "amplitude": float(np.exp(intercept + slope * tt[0])),
            "background": bg,
            "start_bin": k0,
            "n_bins_used": int(use.sum()),
            "r_squared": float(1.0 - ss_res / ss_tot) if ss_tot > 0.0 else 1.0}


def lifetime_phasor(decay, bin_ps=100.0, harmonic=1, background=0.0):
    """Phasor (frequency-domain) representation of a decay — the fit-free view.

    FLIM's standard fit-free tool. With ``omega = 2*pi*harmonic/window`` and bin
    centres ``t_k``::

        g = sum(h_k * cos(omega*t_k)) / sum(h_k)
        s = sum(h_k * sin(omega*t_k)) / sum(h_k)

    For a **single** exponential of lifetime ``tau`` under periodic excitation the
    exact analytic phasor is ``g = 1/(1+(omega*tau)^2)``,
    ``s = omega*tau/(1+(omega*tau)^2)``, which traces the **universal
    semicircle** ``(g - 1/2)^2 + s^2 = 1/4`` as ``tau`` runs from 0 to infinity.
    A multi-exponential decay falls strictly *inside* that circle — which is why
    ``semicircle_residual`` is returned: it is the honest detector of the
    single-exponential assumption that :func:`lifetime_fit` cannot give you.

    Returns a dict: ``g`` · ``s`` · ``modulation`` ``m = sqrt(g^2+s^2)`` ·
    ``phase_rad`` · ``omega_per_ps`` · ``tau_phi_ps`` ``= tan(phase)/omega`` ·
    ``tau_m_ps`` ``= sqrt(1/m^2 - 1)/omega`` · ``semicircle_residual``
    ``= (g-1/2)^2 + s^2 - 1/4`` (0 on the circle, **negative inside**) ·
    ``total_counts``. ``tau_phi_ps`` is ``None`` — not a negative number — when
    the phase is not in ``(0, pi/2)``, and ``tau_m_ps`` is ``None`` when the
    modulation is 0 or >= 1; both mean "this is not a decaying single
    exponential", which is information, not a failure.

    Honest accuracy: the analytic formula is the *continuous* integral over one
    excitation period, while this op sums over bins, so the two differ by the
    midpoint-rule error. Measured on an exactly bin-integrated single exponential
    (``tau = 2000 ps``, 256 bins x 100 ps, i.e. a 25.6 ns period): ``g`` and
    ``s`` match the analytic values to 2.0e-3 and 4.7e-4, ``tau_phi_ps`` comes
    back as 2004.7 ps (0.23% high) and ``semicircle_residual`` is -2.3e-04. At
    1024 bins over the same window the errors fall by 16x (2.9e-5 residual),
    confirming the ``O(bin^2)`` midpoint behaviour rather than a bias.

    **Raises** ``ValueError``: negative, non-finite, non-1-D or all-zero *decay*,
    a non-positive *bin_ps*, a *harmonic* outside ``[1, bins//2]`` (above
    Nyquist the phasor is aliased and meaningless), a negative *background*, and
    a background subtraction that removes every count.
    """
    h = _require_hist(decay, "decay", "lifetime_phasor")
    dt = _positive(bin_ps, "bin_ps")
    n = int(h.size)
    k = _count(harmonic, "harmonic", 1, max(1, n // 2))
    bg = _nonneg(background, "background")
    if float(h.sum()) <= 0.0:
        raise ValueError("lifetime_phasor: the histogram is all zero — no "
                         "photons were detected, so the phasor is 0/0")
    y = np.maximum(h - bg, 0.0)
    total = float(y.sum())
    if total <= 0.0:
        raise ValueError("lifetime_phasor: background=%g removed every count "
                         "(the histogram maximum is %g) — nothing is left to "
                         "transform" % (bg, float(h.max())))
    window = n * dt
    omega = 2.0 * np.pi * k / window
    t = (np.arange(n, dtype=np.float64) + 0.5) * dt
    g = float((y * np.cos(omega * t)).sum() / total)
    s = float((y * np.sin(omega * t)).sum() / total)
    mod = float(np.hypot(g, s))
    phase = float(np.arctan2(s, g))
    tau_phi = None
    if 0.0 < phase < 0.5 * np.pi:
        tau_phi = float(np.tan(phase) / omega)
    tau_m = None
    if 0.0 < mod < 1.0:
        tau_m = float(np.sqrt(1.0 / (mod * mod) - 1.0) / omega)
    return {"g": g, "s": s, "modulation": mod, "phase_rad": phase,
            "omega_per_ps": float(omega),
            "tau_phi_ps": tau_phi, "tau_m_ps": tau_m,
            "semicircle_residual": float((g - 0.5) ** 2 + s * s - 0.25),
            "total_counts": total}
