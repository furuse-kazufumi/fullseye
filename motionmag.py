# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""motionmag — phase-based motion magnification and sub-pixel displacement measurement.

Some of the motion an industrial or scientific camera records is real but far
below the threshold of sight: a machine frame breathing a tenth of a pixel at its
resonance, a pipe wall pulsing, a bolted joint working loose one micron at a time.
Two things are wanted from such a clip, and they are different questions:

* **Show me the motion.** Re-render the video with the small displacement scaled
  up so a human can see it. That is *magnification*.
* **Tell me how large it is.** Return the displacement, in pixels, per frame.
  That is *measurement*.

Both are answered from the same quantity: the **local phase** of a complex
oriented sub-band. A translation of a band-pass image component by ``d`` shifts
the local phase of that component by ``-k·d``, where ``k`` is the component's
local spatial frequency in radians per pixel. Phase is therefore a linear,
sub-pixel-resolved encoding of displacement — and *scaling the phase scales the
displacement*, exactly and without ever estimating a motion field.

Method and its public sources
-----------------------------
* Complex steerable (oriented quadrature) decomposition — Freeman & Adelson,
  *The Design and Use of Steerable Filters*, IEEE PAMI 13(9), 1991; Simoncelli &
  Freeman, *The Steerable Pyramid: A Flexible Architecture for Multi-Scale
  Derivative Computation*, ICIP 1995; Portilla & Simoncelli, IJCV 40(1), 2000.
* Temporal band-pass of a per-pixel signal to isolate a frequency of interest —
  Wu, Rubinstein, Shih, Guttag, Durand & Freeman, *Eulerian Video Magnification
  for Revealing Subtle Changes in the World*, ACM TOG 31(4), 2012.
* Magnifying the **phase** rather than the amplitude — Wadhwa, Rubinstein,
  Durand & Freeman, *Phase-Based Video Motion Processing*, ACM TOG 32(4), 2013.

Everything here is numpy + scipy and deterministic. No product, vendor or
proprietary method is involved; the construction below is assembled from the
papers above and from the standard Fourier identities.

Conventions
-----------
* A **video** is a float64 ``(T, H, W)`` array — the same frame-sequence sort
  :mod:`videops` uses, and a list of equal-shape 2-D frames is accepted and
  stacked for you exactly as there. Values are *not* required to lie in
  ``[0, 1]``: a magnified frame legitimately leaves that range, and clipping
  would silently destroy the very displacement being reported.
* Displacement follows :mod:`flow`: ``dx`` is horizontal (column) motion, ``dy``
  vertical (row) motion, both in pixels, and a feature at ``(x, y)`` in one frame
  is at ``(x + dx, y + dy)`` in the next.
* ``alpha`` is a **displacement gain**, not the literature's amplification
  factor: the output displacement is ``alpha * d``. So ``alpha = 1`` is the
  identity, ``alpha = 0`` removes the in-band motion, and ``alpha = -1`` reverses
  it. The papers above write the magnified motion as ``(1 + alpha_paper) * d``;
  this module's ``alpha`` equals ``1 + alpha_paper``. The reason for the
  difference is testability — ``alpha`` here is the number the measurement is
  compared against, with nothing to add or subtract first.

Where this sits next to what already exists
-------------------------------------------
* :mod:`flow` (``optical_flow_lk`` / ``optical_flow_hs``) *estimates a motion
  field* by brightness constancy over a spatial window. It is the right tool for
  motion of a pixel or more and for independently moving objects. It is not
  re-implemented here, and this module never calls it: phase gives sub-pixel
  displacement of a *band-limited component*, which is a different (and much
  smaller-signal) regime, and it cannot follow a large or occluding motion.
* :mod:`motion` *interprets* an estimated flow field (global model, residual,
  segmentation). Unchanged and unrelated.
* :mod:`videops` supplies the temporal reductions and spatiotemporal filters over
  the same ``(T, H, W)`` sort. ``temporal_bandpass`` here is the frequency-
  selective member of that family that magnification needs; it is *not* a
  duplicate of ``moving_average`` / ``spatiotemporal_gaussian``, which are
  low-pass.
* :mod:`complexops` owns the general complex-field plumbing (``cx_fft``,
  ``phase_unwrap``, Wiener deconvolution) and :mod:`filters_freq` the FFT
  convolution / correlation family. Neither is re-implemented; the steerable
  bank here is built directly on :mod:`numpy.fft` because it needs its *own*
  filter set to be a tight frame, which is what makes reconstruction exact.
* ``backends_transform2.tf_steerable_filter`` is a single real oriented
  derivative-of-Gaussian *response map* for edge detection. It is not a
  quadrature pair, carries no phase, and is not invertible — so it cannot
  support magnification. Different object, kept as it is.

Honest limitations
------------------
* **Phase wrap sets the largest measurable motion.** A displacement is recovered
  from ``-k·d``; once ``|k·d|`` reaches ``pi`` the answer folds over. For a band
  of wavelength ``L`` pixels that is ``|d| < L/2``. Measured breakdown table:
  see :func:`phase_displacement` and ``tests/test_motionmag.py``.
* **Only the oriented sub-bands are magnified.** The low-pass and high-pass
  residuals are reconstructed untouched, because a residual has no well-defined
  local frequency to divide by. Content that lives entirely in a residual is not
  magnified — which is why the synthetic in the tests is placed on a band centre.
* **No amplitude-weighted spatial phase smoothing.** The 2013 paper adds one to
  suppress phase noise. It is deliberately absent: it would trade a measurable
  exact relation (``alpha * d``) for an unquantified bias, and this module's
  contract is that the relation is exact.
* **Magnification does not improve the motion SNR** and this module refuses to
  imply otherwise — see :func:`band_snr` and the ``snr`` block returned by
  :func:`motion_magnify`.
"""
from __future__ import annotations

from math import comb

import numpy as np

__all__ = [
    "synthesize_translation",
    "complex_steerable_decompose", "complex_steerable_reconstruct",
    "temporal_bandpass", "temporal_band_power", "band_snr",
    "motion_magnify", "phase_displacement", "displacement_series",
]

# --------------------------------------------------------------------------- #
# Caps. Every one of these exists because a small-looking argument otherwise    #
# turns into a large allocation.                                               #
# --------------------------------------------------------------------------- #

#: Largest frame count accepted anywhere.
MAX_FRAMES = 4096

#: Largest pixel count in one frame (2^22 = 4.19 M, i.e. 2048x2048).
MAX_FRAME_PIXELS = 1 << 22

#: Largest ``T * H * W`` for the *cheap* temporal operators
#: (:func:`temporal_bandpass`, :func:`temporal_band_power`, :func:`band_snr`).
#: Those hold at most one complex copy of the video, so 2^24 elements is
#: 16.8 M * 16 B = 268 MB.
MAX_VIDEO_ELEMENTS = 1 << 24

#: Largest ``T * H * W`` for the *pyramid* operators (:func:`motion_magnify`,
#: :func:`phase_displacement`). Those hold, simultaneously, the spatial spectrum
#: of the clip, one complex sub-band, one accumulator and one real phase volume:
#: ``3 * 16 + 8 = 56`` bytes per element before FFT temporaries, so the practical
#: peak is near 96 B/element. 2^22 elements is then about 400 MB — e.g. 64 frames
#: of 256x256, or 16 frames of 512x512. Without this cap a clip that looks
#: harmless (300 frames of 1024x1024) asks for 30 GB.
MAX_PYRAMID_ELEMENTS = 1 << 22

#: Bounds on the decomposition itself. ``scales * orientations`` sub-bands are
#: built, each a full ``(H, W)`` float64 filter.
MAX_SCALES = 8
MAX_ORIENTATIONS = 16

#: Largest ``n_bands * H * W`` for the cached filter bank (2^24 float64 = 134 MB).
MAX_FILTER_ELEMENTS = 1 << 24

#: Largest ``|alpha|``. Past this the phase shift is nowhere near the linear
#: regime and the output is decorative rather than metric; the returned
#: ``linear_regime`` flag reports the real limit for the clip at hand.
MAX_ALPHA = 200.0

#: Reported dB values are clamped to this window. An SNR is a ratio of measured
#: powers and either of them can be exactly zero on a synthetic (a noiseless clip
#: has no out-of-band power; a zero-mean clip has no static power). Returning
#: ``inf``/``-inf``/``nan`` would poison every downstream arithmetic, so the
#: window is applied and the fact that it was applied is returned as
#: ``snr_clamped``.
MIN_SNR_DB = -100.0
MAX_SNR_DB = 100.0

#: Sub-band kinds that carry a well-defined local spatial frequency and are
#: therefore the only ones whose phase may be scaled.
_ORIENTED = "band"

# Filter banks are pure functions of (H, W, scales, orientations) and cost a
# handful of FFT-sized allocations to build, so a small cache pays for itself
# across the frames of one clip.
_FILTER_CACHE: dict = {}
_FILTER_CACHE_MAX = 8


# --------------------------------------------------------------------------- #
# fail-closed input helpers                                                     #
# --------------------------------------------------------------------------- #
def _finite_scalar(v, name: str) -> float:
    """A real, finite Python float — or ``ValueError`` naming the problem.

    The string branch is not decoration: ``float("30")`` succeeds, so without it
    ``fps="30"`` passes silently and a caller never learns their configuration
    value was never parsed. The bool branch blocks the ``True == 1`` promotion,
    which for ``fps`` would mean a one-frame-per-second timebase nobody asked
    for. Both traps were exercised against this module (see the adversarial
    section of ``tests/test_motionmag.py``)."""
    if np.ma.is_masked(v):
        raise ValueError("%s is a masked value — fill or drop it explicitly" % (name,))
    if isinstance(v, (complex, np.complexfloating)):
        raise ValueError("%s is complex — a frequency / rate / gain is a real "
                         "quantity; coercion would silently drop the imaginary "
                         "part" % (name,))
    if isinstance(v, (bool, np.bool_)):
        raise ValueError("%s is a bool — refusing the silent True==1 promotion "
                         "(True as an fps would mean a 1 Hz timebase)" % (name,))
    if isinstance(v, (str, bytes, np.str_, np.bytes_)):
        raise ValueError("%s is a string (%r) — a frequency / rate / gain must be "
                         "a number; float('30') would silently succeed and hide "
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


def _count(v, name: str, lo: int, hi: int) -> int:
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s must be an int, got %r" % (name, type(v).__name__))
    n = int(v)
    if n < lo or n > hi:
        raise ValueError("%s must be in [%d, %d], got %d (the cap is there so a "
                         "mistyped argument fails instead of allocating "
                         "gigabytes)" % (name, lo, hi, n))
    return n


def _require_video(video, name: str, op: str, max_elements: int,
                   min_frames: int = 2) -> np.ndarray:
    """Coerce to a validated ``(T, H, W)`` float64 clip.

    Accepts a 3-D array-like or a list/tuple of equal-shape 2-D frames — the same
    contract :mod:`videops` documents — and adds the size caps and the
    complex/masked refusals this module needs."""
    if isinstance(video, (list, tuple)):
        if not video:
            raise ValueError("%s: %s is an empty frame list" % (op, name))
        frames = []
        for i, f in enumerate(video):
            if np.ma.is_masked(f):
                raise ValueError("%s: %s[%d] is a masked array with masked "
                                 "entries — fill or drop them explicitly"
                                 % (op, name, i))
            if np.iscomplexobj(f):
                raise ValueError("%s: %s[%d] is complex — coercion to float64 "
                                 "would silently discard the imaginary part"
                                 % (op, name, i))
            a = np.asarray(f, np.float64)
            if a.ndim != 2:
                raise ValueError("%s: %s[%d] must be 2-D (H, W), got ndim=%d"
                                 % (op, name, i, a.ndim))
            frames.append(a)
        shapes = {f.shape for f in frames}
        if len(shapes) != 1:
            raise ValueError("%s: %s frames have differing shapes: %r"
                             % (op, name, sorted(shapes)))
        vid = np.stack(frames, axis=0)
    else:
        if np.ma.is_masked(video):
            raise ValueError("%s: %s is a masked array with masked entries — "
                             "fill or drop them explicitly" % (op, name))
        if np.iscomplexobj(video):
            raise ValueError("%s: %s is complex — coercion to float64 would "
                             "silently discard the imaginary part" % (op, name))
        vid = np.ascontiguousarray(video, dtype=np.float64)
    if vid.ndim != 3:
        raise ValueError("%s: %s must be a (T, H, W) clip, got a %d-D array of "
                         "shape %r — nothing is reshaped silently"
                         % (op, name, vid.ndim, tuple(np.shape(video))))
    t, h, w = vid.shape
    if t < min_frames:
        raise ValueError("%s: %s has T=%d frames, need at least %d (a temporal "
                         "frequency is undefined below that)"
                         % (op, name, t, min_frames))
    if t > MAX_FRAMES:
        raise ValueError("%s: %s has T=%d frames, over the %d cap "
                         "(motionmag.MAX_FRAMES)" % (op, name, t, MAX_FRAMES))
    if h < 4 or w < 4:
        raise ValueError("%s: %s frames are %dx%d; at least 4x4 is needed for an "
                         "oriented band to be sampled at all" % (op, name, h, w))
    if h * w > MAX_FRAME_PIXELS:
        raise ValueError("%s: %s frames are %dx%d = %d pixels, over the %d cap "
                         "(motionmag.MAX_FRAME_PIXELS)"
                         % (op, name, h, w, h * w, MAX_FRAME_PIXELS))
    if vid.size > max_elements:
        raise ValueError("%s: %s has T*H*W = %d elements (shape %r), over the %d "
                         "cap — this operator holds several complex copies of the "
                         "clip at once, so the cap is a memory bound, not a "
                         "preference" % (op, name, vid.size, vid.shape, max_elements))
    if not np.isfinite(vid).all():
        n = int((~np.isfinite(vid)).sum())
        raise ValueError("%s: %s has %d non-finite sample(s) (NaN/Inf) — refusing"
                         % (op, name, n))
    return vid


def _require_band(f_lo, f_hi, fps, t: int, op: str):
    """Validate a temporal pass-band against the clip's own sampling.

    Returns ``(f_lo, f_hi, fps, mask, freq)`` where *mask* selects the FFT bins
    inside the band. Four separate refusals, each one a way to get a plausible
    but wrong number:

    * ``fps <= 0`` — a zero frame rate makes every frequency infinite.
    * ``f_lo <= 0`` — a pass-band touching DC would scale the *static* phase,
      i.e. the scene's position rather than its motion.
    * ``f_hi > fps/2`` — above Nyquist there is no such temporal frequency in
      the clip; it would alias onto a lower one. Refused rather than folded.
    * an **empty** band — a band narrower than the clip's frequency resolution
      ``fps/T`` contains no bin, so the filter would silently return zeros.
    """
    fs = _positive(fps, "fps")
    lo = _finite_scalar(f_lo, "f_lo")
    hi = _finite_scalar(f_hi, "f_hi")
    if lo <= 0.0:
        raise ValueError("%s: f_lo must be > 0, got %g — a pass-band that reaches "
                         "DC scales the static phase (where the scene *is*) "
                         "instead of its motion" % (op, lo))
    if hi <= lo:
        raise ValueError("%s: need f_lo < f_hi, got f_lo=%g f_hi=%g" % (op, lo, hi))
    nyq = 0.5 * fs
    if hi > nyq:
        raise ValueError("%s: f_hi=%g Hz is above the Nyquist frequency %g Hz "
                         "(fps=%g). That temporal frequency is not present in the "
                         "clip; it would alias onto %g Hz. Refusing rather than "
                         "folding it silently"
                         % (op, hi, nyq, fs, abs(hi - fs * round(hi / fs))))
    freq = np.fft.fftfreq(t, d=1.0 / fs)
    mask = (np.abs(freq) >= lo) & (np.abs(freq) <= hi)
    mask[0] = False                      # DC is never in the band (f_lo > 0)
    if not mask.any():
        raise ValueError("%s: the pass-band [%g, %g] Hz contains no DFT bin. With "
                         "T=%d frames at fps=%g the bin spacing is %g Hz, so the "
                         "band must be at least that wide and must straddle a "
                         "multiple of it. Widen the band or record more frames"
                         % (op, lo, hi, t, fs, fs / t))
    return lo, hi, fs, mask, freq


def _db(num: float, den: float):
    """``10*log10(num/den)`` clamped into the reported dB window.

    Returns ``(value, clamped)``. Both zero powers are real cases on synthetic
    data, so this never emits ``inf`` / ``nan``."""
    if den <= 0.0:
        return (MAX_SNR_DB, True) if num > 0.0 else (MIN_SNR_DB, True)
    if num <= 0.0:
        return MIN_SNR_DB, True
    v = 10.0 * np.log10(num / den)
    if v > MAX_SNR_DB:
        return MAX_SNR_DB, True
    if v < MIN_SNR_DB:
        return MIN_SNR_DB, True
    return float(v), False


# --------------------------------------------------------------------------- #
# The complex steerable filter bank                                            #
# --------------------------------------------------------------------------- #
def _mirror_index(h: int, w: int):
    """Index arrays realising ``omega -> -omega`` on the DFT grid."""
    return (-np.arange(h)) % h, (-np.arange(w)) % w


def _filter_bank(h: int, w: int, scales: int, orientations: int) -> dict:
    """Build (and cache) the complex steerable analysis bank for one frame size.

    Radial: octave-wide raised cosines in ``log2`` of the radial frequency,
    ``A_s(r) = cos(pi/2 * (log2 r - c_s))`` on ``|log2 r - c_s| <= 1`` with
    ``c_s = -1-s``. Neighbouring bands overlap by exactly one octave and
    ``cos^2 + sin^2 = 1`` makes ``sum_s A_s^2`` a partition of unity between the
    first and last centre; the deficit outside is taken up by a low-pass and a
    high-pass residual, so ``sum_s A_s^2 + L^2 + H^2 == 1`` identically.

    Angular: ``G_k(theta) ∝ max(cos(theta - pi k/K), 0)^(K-1)`` — supported on a
    half plane, which is what makes each sub-band *analytic* and gives it a
    phase. The classical identity ``sum_k cos^(2K-2)(theta - pi k/K) =
    K*C(2K-2, K-1)/2^(2K-2)`` (constant in theta) normalises the bank so that
    ``sum_k [G_k(theta)^2 + G_k(theta+pi)^2] == 1`` for every theta.

    Together those give ``M(omega) + M(-omega) == 1`` in the continuum, where
    ``M = sum_j B_j^2``. On a discrete even-sized grid the four self-conjugate
    points (DC and the Nyquist corners) map to themselves, so the continuum
    identity does not apply there and ``M + M(-omega)`` is computed by actual
    index mirroring instead. One extra symmetric residual absorbs whatever
    deficit remains, after which the reconstruction divisor ``D`` is strictly
    positive everywhere — that is what makes :func:`complex_steerable_reconstruct`
    exact to machine precision rather than approximately right.

    Returns a dict with the stacked filters, per-band metadata and ``D``."""
    key = (h, w, scales, orientations)
    hit = _FILTER_CACHE.get(key)
    if hit is not None:
        return hit

    n_bands = scales * orientations + 3
    if n_bands * h * w > MAX_FILTER_ELEMENTS:
        raise ValueError("complex steerable bank: %d filters x %dx%d = %d float64 "
                         "elements, over the %d cap (motionmag.MAX_FILTER_ELEMENTS). "
                         "Reduce scales/orientations or the frame size"
                         % (n_bands, h, w, n_bands * h * w, MAX_FILTER_ELEMENTS))

    fv = np.fft.fftfreq(h)[:, None]
    fu = np.fft.fftfreq(w)[None, :]
    r = np.sqrt(fu * fu + fv * fv)
    theta = np.arctan2(fv, fu)
    nonzero = r > 0.0
    x = np.log2(np.where(nonzero, r, 1.0))          # value at r == 0 is masked out

    radial, centres = [], []
    total = np.zeros((h, w))
    for s in range(scales):
        c = -1.0 - s
        u = x - c
        a = np.where((np.abs(u) <= 1.0) & nonzero, np.cos(0.5 * np.pi * u), 0.0)
        radial.append(a)
        centres.append(2.0 ** c)
        total += a * a
    resid = np.sqrt(np.maximum(0.0, 1.0 - total))
    hipass = np.where((x > -1.0) & nonzero, resid, 0.0)
    lopass = resid - hipass

    m = orientations - 1
    c_k = orientations * comb(2 * m, m) / (2.0 ** (2 * m))
    angular, thetas = [], []
    for k in range(orientations):
        tk = np.pi * k / orientations
        cs = np.cos(theta - tk)
        pos = cs > 0.0
        g = np.where(pos, np.power(np.where(pos, cs, 1.0), m), 0.0)
        angular.append(g / np.sqrt(c_k))
        thetas.append(tk)

    filters, kinds, meta_centre, meta_theta = [], [], [], []
    for s in range(scales):
        for k in range(orientations):
            filters.append(radial[s] * angular[k])
            kinds.append(_ORIENTED)
            meta_centre.append(centres[s])
            meta_theta.append(thetas[k])
    root2 = np.sqrt(2.0)
    filters.append(lopass / root2)
    kinds.append("lowpass")
    meta_centre.append(None)
    meta_theta.append(None)
    filters.append(hipass / root2)
    kinds.append("highpass")
    meta_centre.append(None)
    meta_theta.append(None)

    mi, mj = _mirror_index(h, w)
    stack = np.stack(filters, axis=0)
    mag = (stack * stack).sum(axis=0)
    d_raw = mag + mag[mi][:, mj]
    extra = np.sqrt(np.maximum(0.0, 0.5 * (1.0 - d_raw)))
    filters.append(extra)
    kinds.append("residual")
    meta_centre.append(None)
    meta_theta.append(None)

    stack = np.stack(filters, axis=0)
    mag = (stack * stack).sum(axis=0)
    divisor = mag + mag[mi][:, mj]
    if not (divisor > 0.0).all():
        raise ValueError("complex steerable bank: the reconstruction divisor "
                         "vanishes at %d frequency bin(s) for shape (%d, %d) with "
                         "scales=%d orientations=%d — those frequencies would be "
                         "silently lost, so the bank is refused"
                         % (int((divisor <= 0.0).sum()), h, w, scales, orientations))

    bank = {"filters": stack, "kinds": kinds, "centre": meta_centre,
            "theta": meta_theta, "divisor": divisor, "shape": (h, w),
            "scales": scales, "orientations": orientations,
            "mirror": (mi, mj), "fu": fu, "fv": fv}
    if len(_FILTER_CACHE) >= _FILTER_CACHE_MAX:
        _FILTER_CACHE.clear()
    _FILTER_CACHE[key] = bank
    return bank


def _synthesise(acc_spec: np.ndarray, bank: dict) -> np.ndarray:
    """Turn an accumulated synthesis spectrum back into real frames.

    ``acc_spec = sum_j B_j * fft(sub_j)`` equals ``M * F`` for the unmodified
    decomposition. Because the frames are real, ``F`` is Hermitian and
    ``fft(2*Re(ifft(M F)))(omega) = [M(omega) + M(-omega)] F(omega)``; dividing
    by that divisor recovers ``F`` exactly, including at the self-conjugate
    grid points where the plain factor-of-two argument does not hold."""
    mi, mj = bank["mirror"]
    if acc_spec.ndim == 3:
        mirrored = np.conj(acc_spec[:, mi][:, :, mj])
        spec = (acc_spec + mirrored) / bank["divisor"][None]
        return np.real(np.fft.ifft2(spec, axes=(1, 2)))
    mirrored = np.conj(acc_spec[mi][:, mj])
    spec = (acc_spec + mirrored) / bank["divisor"]
    return np.real(np.fft.ifft2(spec))


# --------------------------------------------------------------------------- #
# Synthetic clip with a closed-form displacement                                #
# --------------------------------------------------------------------------- #
def synthesize_translation(shape=(64, 64), frames: int = 32, amplitude_px=0.5,
                           frequency_hz=4.0, fps=32.0, direction_deg=0.0,
                           wavelength_px=(8.0, 16.0), contrast=0.4, offset=0.5,
                           noise_sigma=0.0, seed: int = 0) -> np.ndarray:
    """A clip whose displacement is known in closed form -> ``(T, H, W)`` video.

    The scene is a stationary two-axis sinusoidal grating that is translated,
    frame by frame, by

        ``d(t) = amplitude_px * sin(2*pi * frequency_hz * t / fps)``

    along *direction_deg* (0 deg = towards +x / increasing column). The
    translation is applied as a Fourier phase ramp, which for a pattern that is
    periodic on the grid is the *exact* band-limited shift — no interpolation
    kernel, no resampling error, so ``d(t)`` is ground truth to machine
    precision and sub-pixel amplitudes are meaningful.

    ``wavelength_px`` is either one number (both axes) or ``(lambda_x,
    lambda_y)``. **The default deliberately makes the two axes different
    octaves**, and that is not cosmetic: if the horizontal and vertical gratings
    share a radial frequency they land in the *same* sub-band, whose local phase
    is then the phase of a sum of two moving components rather than of one. The
    phase of a sum is not linear in the displacement, so scaling it does not
    scale the motion — measured, a 64x64 clip built with a single wavelength on
    both axes magnified at ``alpha = 2`` came out at ``0.939 * (2 d)`` instead of
    ``2 d``, a 6.1 % error that does *not* shrink as ``d`` shrinks. Separating
    the octaves puts one component in each band and the relation becomes exact.
    This is the standard narrow-band condition of phase-based processing, made
    visible in the synthetic instead of hidden.

    Each wavelength is snapped so that a whole number of cycles fits the frame
    (``cycles = max(1, round(W / wavelength_px))``, effective wavelength
    ``W / cycles``); without that the pattern is not periodic on the grid and the
    Fourier shift would wrap a discontinuity across the border. With the default
    64x64 frame and ``(8, 16)`` the snap is exact (8 and 4 cycles).

    Values are **not clipped** into ``[0, 1]``: clipping is a nonlinearity that
    would break the exact translation this function exists to provide. With the
    defaults the samples lie in ``[offset - contrast, offset + contrast]``.

    *noise_sigma* adds zero-mean Gaussian sensor noise (after translation, drawn
    from ``numpy.random.default_rng(seed)``) — the term that makes an SNR
    measurable at all.

    This is the counterpart of ``photoncount.tcspc_simulate``: a forward model
    good enough to close the loop on the analysis operators in this module."""
    if not isinstance(shape, (tuple, list)) or len(shape) != 2:
        raise ValueError("synthesize_translation: shape must be a 2-tuple (H, W), "
                         "got %r" % (shape,))
    h = _count(shape[0], "shape[0]", 4, 1 << 13)
    w = _count(shape[1], "shape[1]", 4, 1 << 13)
    t = _count(frames, "frames", 2, MAX_FRAMES)
    if h * w > MAX_FRAME_PIXELS:
        raise ValueError("synthesize_translation: %dx%d = %d pixels, over the %d "
                         "cap" % (h, w, h * w, MAX_FRAME_PIXELS))
    if t * h * w > MAX_VIDEO_ELEMENTS:
        raise ValueError("synthesize_translation: T*H*W = %d, over the %d cap"
                         % (t * h * w, MAX_VIDEO_ELEMENTS))
    amp = _finite_scalar(amplitude_px, "amplitude_px")
    freq = _finite_scalar(frequency_hz, "frequency_hz")
    fs = _positive(fps, "fps")
    if abs(freq) > 0.5 * fs:
        raise ValueError("synthesize_translation: frequency_hz=%g is above the "
                         "Nyquist frequency %g Hz for fps=%g — the clip would "
                         "show an aliased motion at a different frequency than "
                         "the one requested" % (freq, 0.5 * fs, fs))
    ang = np.deg2rad(_finite_scalar(direction_deg, "direction_deg"))
    lam = _positive(wavelength_px, "wavelength_px")
    con = _finite_scalar(contrast, "contrast")
    off = _finite_scalar(offset, "offset")
    sigma = _finite_scalar(noise_sigma, "noise_sigma")
    if sigma < 0.0:
        raise ValueError("synthesize_translation: noise_sigma must be >= 0, got %g"
                         % (sigma,))
    seed_i = _count(seed, "seed", 0, (1 << 31) - 1)

    cx = max(1, int(round(w / lam)))
    cy = max(1, int(round(h / lam)))
    if 2 * cx >= w or 2 * cy >= h:
        raise ValueError("synthesize_translation: wavelength_px=%g needs %d x %d "
                         "cycles in a %dx%d frame, which is at or past Nyquist "
                         "(the grating would not be resolved). Use a longer "
                         "wavelength or a larger frame" % (lam, cx, cy, h, w))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    base = off + 0.5 * con * (np.cos(2.0 * np.pi * cx * xx / w)
                              + np.cos(2.0 * np.pi * cy * yy / h))

    fv = np.fft.fftfreq(h)[:, None]
    fu = np.fft.fftfreq(w)[None, :]
    spec = np.fft.fft2(base)
    tt = np.arange(t, dtype=np.float64)
    disp = amp * np.sin(2.0 * np.pi * freq * tt / fs)
    ux, uy = np.cos(ang), np.sin(ang)
    out = np.empty((t, h, w), np.float64)
    for i in range(t):
        dx, dy = disp[i] * ux, disp[i] * uy
        ramp = np.exp(-2j * np.pi * (fu * dx + fv * dy))
        out[i] = np.real(np.fft.ifft2(spec * ramp))
    if sigma > 0.0:
        out += np.random.default_rng(seed_i).normal(0.0, sigma, out.shape)
    return out


# --------------------------------------------------------------------------- #
# Complex steerable decomposition                                              #
# --------------------------------------------------------------------------- #
def complex_steerable_decompose(image, scales: int = 4,
                                orientations: int = 4) -> dict:
    """Complex oriented sub-band decomposition of one frame -> ``dict``.

    Splits the image into ``scales * orientations`` **analytic** sub-bands plus
    three residuals (low-pass, high-pass and a small symmetric completion band).
    Each sub-band is a full-resolution ``(H, W)`` complex array whose modulus is
    the local contrast of that scale/orientation and whose argument is the local
    **phase** — the quantity a translation shifts linearly, which is what the
    rest of this module is built on. There is no spatial decimation: keeping
    every band at full resolution costs memory but makes the frame exactly
    invertible, and exactness is the point.

    Returns ``{"bands": [complex (H, W), ...], "kinds": [...],
    "centre_cycles_per_px": [...], "orientation_rad": [...], "shape": (H, W),
    "scales": s, "orientations": k}``. ``kinds[j]`` is ``"band"`` for an oriented
    sub-band and ``"lowpass"`` / ``"highpass"`` / ``"residual"`` otherwise;
    ``centre_cycles_per_px`` and ``orientation_rad`` are ``None`` for residuals,
    which have no orientation and no single centre frequency.

    Feed the whole dict back to :func:`complex_steerable_reconstruct`. Round trip
    error, measured on a 64x64 random frame with the defaults, is
    ``max|out - in| = 6.7e-16`` — the tight-frame construction is exact, not
    approximate (see the module-level notes on the self-conjugate grid points).

    References: Freeman & Adelson, IEEE PAMI 1991; Simoncelli & Freeman,
    ICIP 1995; Portilla & Simoncelli, IJCV 2000."""
    op = "complex_steerable_decompose"
    if np.ma.is_masked(image):
        raise ValueError("%s: image is a masked array with masked entries — fill "
                         "or drop them explicitly" % (op,))
    if np.iscomplexobj(image):
        raise ValueError("%s: image is complex — this decomposition is defined "
                         "for a real frame (the analytic bands it produces are "
                         "the complex object)" % (op,))
    img = np.ascontiguousarray(image, dtype=np.float64)
    if img.ndim != 2:
        raise ValueError("%s: image must be 2-D (H, W), got a %d-D array of shape "
                         "%r" % (op, img.ndim, tuple(np.shape(image))))
    h, w = img.shape
    if h < 4 or w < 4:
        raise ValueError("%s: image must be at least 4x4, got %dx%d" % (op, h, w))
    if h * w > MAX_FRAME_PIXELS:
        raise ValueError("%s: image is %dx%d = %d pixels, over the %d cap"
                         % (op, h, w, h * w, MAX_FRAME_PIXELS))
    if not np.isfinite(img).all():
        raise ValueError("%s: image has %d non-finite value(s) (NaN/Inf) — refusing"
                         % (op, int((~np.isfinite(img)).sum())))
    ns = _count(scales, "scales", 1, MAX_SCALES)
    no = _count(orientations, "orientations", 1, MAX_ORIENTATIONS)

    bank = _filter_bank(h, w, ns, no)
    spec = np.fft.fft2(img)
    bands = [np.fft.ifft2(spec * b) for b in bank["filters"]]
    return {"bands": bands, "kinds": list(bank["kinds"]),
            "centre_cycles_per_px": list(bank["centre"]),
            "orientation_rad": list(bank["theta"]),
            "shape": (h, w), "scales": ns, "orientations": no}


def complex_steerable_reconstruct(decomposition) -> np.ndarray:
    """Invert :func:`complex_steerable_decompose` -> ``(H, W)`` real image.

    Exact: the analysis bank is a tight frame after the divisor correction, so
    the round trip is the identity up to floating-point rounding (measured
    ``6.7e-16`` maximum absolute error on a 64x64 random frame with the default
    4 scales x 4 orientations). Editing a band before calling this — scaling its
    phase, zeroing it — is how every other operator in this module works.

    Refuses a dict whose bands do not match the declared shape or count, because
    a partially edited decomposition would otherwise reconstruct something
    plausible from the wrong frame size."""
    op = "complex_steerable_reconstruct"
    if not isinstance(decomposition, dict):
        raise ValueError("%s: expected the dict returned by "
                         "complex_steerable_decompose, got %r"
                         % (op, type(decomposition).__name__))
    for k in ("bands", "shape", "scales", "orientations"):
        if k not in decomposition:
            raise ValueError("%s: decomposition is missing the %r key" % (op, k))
    shape = tuple(decomposition["shape"])
    if len(shape) != 2:
        raise ValueError("%s: decomposition['shape'] must be (H, W), got %r"
                         % (op, shape))
    h, w = int(shape[0]), int(shape[1])
    ns = _count(decomposition["scales"], "scales", 1, MAX_SCALES)
    no = _count(decomposition["orientations"], "orientations", 1, MAX_ORIENTATIONS)
    bank = _filter_bank(h, w, ns, no)
    bands = decomposition["bands"]
    if not isinstance(bands, (list, tuple)):
        raise ValueError("%s: decomposition['bands'] must be a list, got %r"
                         % (op, type(bands).__name__))
    expected = len(bank["kinds"])
    if len(bands) != expected:
        raise ValueError("%s: decomposition has %d band(s) but scales=%d "
                         "orientations=%d needs %d — a band was added or dropped"
                         % (op, len(bands), ns, no, expected))
    acc = np.zeros((h, w), np.complex128)
    for j, band in enumerate(bands):
        arr = np.ascontiguousarray(band, dtype=np.complex128)
        if arr.shape != (h, w):
            raise ValueError("%s: band %d has shape %r, expected %r"
                             % (op, j, arr.shape, (h, w)))
        if not np.isfinite(arr).all():
            raise ValueError("%s: band %d has non-finite values (NaN/Inf) — "
                             "refusing" % (op, j))
        acc += bank["filters"][j] * np.fft.fft2(arr)
    return _synthesise(acc, bank)


# --------------------------------------------------------------------------- #
# Temporal band selection                                                       #
# --------------------------------------------------------------------------- #
def temporal_bandpass(video, f_lo, f_hi, fps) -> np.ndarray:
    """Ideal temporal band-pass of every pixel's time series -> ``(T, H, W)``.

    Each pixel is transformed along time, every DFT bin whose frequency lies
    outside ``[f_lo, f_hi]`` (in Hz, magnitude, DC always excluded) is zeroed,
    and the result is transformed back. Frequency-selective where
    ``videops.moving_average`` and ``videops.spatiotemporal_gaussian`` are
    low-pass; this is the filter isolating "what is happening at 4 Hz".

    Exact for a component sitting on a bin: with ``T`` frames at ``fps``, a
    sinusoid at ``k*fps/T`` Hz passes with gain 1 and everything else in the band
    passes untouched. Measured on a bin-centred 4 Hz sinusoid of amplitude 1 in
    a clip that also carries a DC offset and a 12 Hz component, the recovered
    amplitude is ``1.0`` to ``4.4e-16`` and the residual outside is ``0``.

    A brick-wall filter rings in time; that is the price of an exact pass-band
    and it is the same choice the 2012 Eulerian magnification paper makes. The
    output is zero-mean along time by construction."""
    op = "temporal_bandpass"
    vid = _require_video(video, "video", op, MAX_VIDEO_ELEMENTS)
    _lo, _hi, _fs, mask, _freq = _require_band(f_lo, f_hi, fps, vid.shape[0], op)
    spec = np.fft.fft(vid, axis=0)
    spec[~mask] = 0.0
    return np.real(np.fft.ifft(spec, axis=0))


def temporal_band_power(video, f_lo, f_hi, fps) -> np.ndarray:
    """Per-pixel mean-square power inside a temporal band -> ``(H, W)`` map.

    "Where in the frame is something moving at this frequency?" — a resonance
    map. The value at a pixel is the mean over time of the squared band-passed
    signal, so a pure sinusoid of amplitude ``a`` inside the band reads exactly
    ``a^2/2`` (Parseval; measured relative error ``2.2e-16`` for ``a = 0.3``).

    This is an *analysis map*, not a displayable image: it is a power and is not
    bounded by 1. Pixels with no in-band content read 0."""
    op = "temporal_band_power"
    vid = _require_video(video, "video", op, MAX_VIDEO_ELEMENTS)
    t = vid.shape[0]
    _lo, _hi, _fs, mask, _freq = _require_band(f_lo, f_hi, fps, t, op)
    spec = np.fft.fft(vid, axis=0)
    power = (np.abs(spec[mask]) ** 2).sum(axis=0) / float(t) ** 2
    return power


def band_snr(video, f_lo, f_hi, fps) -> dict:
    """Measure what a clip's temporal band contains, and what it costs -> ``dict``.

    Every quantity is a measured mean-square power obtained from the per-pixel
    temporal DFT (Parseval-normalised so that the bins of one pixel sum to that
    pixel's mean square), averaged over pixels:

    * ``static_power`` — the DC bin. The scene that is simply *there*.
    * ``band_power`` — the bins inside ``[f_lo, f_hi]``. Coherent motion **plus**
      whatever noise happens to fall in the band.
    * ``out_of_band_power`` / ``out_of_band_bins`` — everything else except DC.
      With broadband sensor noise this is the noise floor, and
      ``noise_power_per_bin`` is its per-bin density.
    * ``noise_in_band`` = ``noise_power_per_bin * band_bins`` — how much of
      ``band_power`` is expected to be noise.
    * ``motion_power`` = ``max(band_power - noise_in_band, 0)`` and
      ``motion_snr_db`` = ``10*log10(motion_power / noise_in_band)``.
    * ``image_snr_db`` = ``10*log10(static_power / (band_power +
      out_of_band_power))`` — the static scene against everything that flickers.

    **The two SNRs answer different questions and magnification moves only one
    of them.** Scaling the in-band phase by ``alpha`` scales the in-band motion
    *and* the in-band noise by the same factor, so ``motion_snr_db`` is
    invariant: magnification cannot make a measurement more certain than the
    recording was. What it does change is ``image_snr_db``, because the temporal
    fluctuation of the output frames grows like ``alpha^2`` while the static
    scene does not. :func:`motion_magnify` reports this measured on its own
    output, so the cost is visible in the same return value as the benefit.

    ``snr_clamped`` is True when a reported dB hit the ``[-100, +100]`` window
    (a noiseless synthetic has zero out-of-band power, which is a division by
    zero rather than an infinite SNR)."""
    op = "band_snr"
    vid = _require_video(video, "video", op, MAX_VIDEO_ELEMENTS)
    t = vid.shape[0]
    lo, hi, fs, mask, _freq = _require_band(f_lo, f_hi, fps, t, op)
    out_mask = ~mask
    out_mask[0] = False
    n_band = int(mask.sum())
    n_out = int(out_mask.sum())
    if n_out < 1:
        raise ValueError("%s: the pass-band [%g, %g] Hz covers every non-DC bin of "
                         "this %d-frame clip, so there is no out-of-band bin left "
                         "to estimate the noise floor from. Narrow the band or "
                         "record more frames" % (op, lo, hi, t))
    spec = np.fft.fft(vid, axis=0)
    scale = 1.0 / float(t) ** 2
    p_dc = float((np.abs(spec[0]) ** 2).mean()) * scale
    p_band = float((np.abs(spec[mask]) ** 2).sum(axis=0).mean()) * scale
    p_out = float((np.abs(spec[out_mask]) ** 2).sum(axis=0).mean()) * scale
    rho = p_out / n_out
    noise_in_band = rho * n_band
    motion_power = max(p_band - noise_in_band, 0.0)
    motion_db, c1 = _db(motion_power, noise_in_band)
    image_db, c2 = _db(p_dc, p_band + p_out)
    return {
        "fps": fs, "band_hz": (lo, hi), "frames": t,
        "bin_hz": fs / t, "band_bins": n_band, "out_of_band_bins": n_out,
        "static_power": p_dc, "band_power": p_band, "out_of_band_power": p_out,
        "noise_power_per_bin": rho, "noise_in_band": noise_in_band,
        "motion_power": motion_power,
        "motion_snr_db": motion_db, "image_snr_db": image_db,
        "snr_clamped": bool(c1 or c2),
    }


# --------------------------------------------------------------------------- #
# Magnification                                                                 #
# --------------------------------------------------------------------------- #
def motion_magnify(video, alpha, f_lo, f_hi, fps, scales: int = 4,
                   orientations: int = 4) -> dict:
    """Scale the in-band motion of a clip by *alpha* -> ``dict``.

    For every oriented sub-band of every frame the local phase is taken relative
    to that band's temporal mean, unwrapped along time, band-passed to
    ``[f_lo, f_hi]``, multiplied by ``alpha - 1`` and added back. Because a
    translation by ``d`` shifts a band's phase by ``-k·d``, the phase of the
    result is ``-alpha * k·d`` for *any* ``k`` — the output displacement is
    ``alpha * d`` without the local spatial frequency ever being estimated.
    Low-pass, high-pass and completion residuals are reconstructed untouched
    (they have no single ``k`` to be consistent about).

    ``alpha`` is the **displacement gain**: 1 is the identity, 0 removes the
    in-band motion, 2 doubles it, -1 reverses it. (The literature writes the
    magnified motion as ``(1 + alpha_paper) d``; this ``alpha`` is
    ``1 + alpha_paper``.)

    Returns a dict::

        {"video": (T, H, W) magnified frames,
         "alpha": ..., "band_hz": (f_lo, f_hi), "fps": ...,
         "snr_in": {...}, "snr_out": {...},          # band_snr of in / out
         "image_snr_change_db": snr_out - snr_in,    # <= 0 for |alpha| > 1
         "motion_snr_change_db": ...,                # ~0 by construction
         "phase_shift_max_rad": ..., "linear_regime": bool}

    **The SNR block is part of the contract, not decoration.** Amplifying the
    in-band phase amplifies the in-band noise by exactly the same factor, so
    ``motion_snr_change_db`` is ~0 — magnification reveals motion, it never
    measures it better than the recording allowed. What does degrade is
    ``image_snr_change_db``: the output's temporal fluctuation grows like
    ``alpha^2`` against an unchanged static scene. Measured on a 64x64x64 clip
    with 0.5 px of 4 Hz motion and sigma=0.02 sensor noise, alpha = 1, 2, 4, 8,
    16 give image SNR 21.24, 16.10, 10.36, 4.44, -1.53 dB — a 5.94 dB loss per
    doubling once the band dominates, which is the 20*log10(2) the algebra
    predicts.

    ``phase_shift_max_rad`` is the largest phase increment actually applied and
    ``linear_regime`` is ``phase_shift_max_rad < pi``. Past ``pi`` the added
    phase has folded and the output is no longer ``alpha * d`` anywhere near
    those pixels; the flag is returned rather than the operation refused, because
    the fold is often confined to a corner the caller does not care about."""
    op = "motion_magnify"
    vid = _require_video(video, "video", op, MAX_PYRAMID_ELEMENTS)
    t, h, w = vid.shape
    a = _finite_scalar(alpha, "alpha")
    if abs(a) > MAX_ALPHA:
        raise ValueError("%s: |alpha| = %g is over the %g cap "
                         "(motionmag.MAX_ALPHA) — at that gain the phase shift is "
                         "far outside the linear regime and the output is not a "
                         "magnified measurement of anything" % (op, abs(a), MAX_ALPHA))
    lo, hi, fs, mask, _freq = _require_band(f_lo, f_hi, fps, t, op)
    ns = _count(scales, "scales", 1, MAX_SCALES)
    no = _count(orientations, "orientations", 1, MAX_ORIENTATIONS)
    bank = _filter_bank(h, w, ns, no)

    gain = a - 1.0
    spec = np.fft.fft2(vid, axes=(1, 2))
    acc = np.zeros((t, h, w), np.complex128)
    max_shift = 0.0
    for j, filt in enumerate(bank["filters"]):
        sub = np.fft.ifft2(spec * filt[None], axes=(1, 2))
        if bank["kinds"][j] == _ORIENTED and gain != 0.0:
            ref = sub.mean(axis=0)
            dphi = np.angle(sub * np.conj(ref)[None])
            dphi = np.unwrap(dphi, axis=0)
            tspec = np.fft.fft(dphi, axis=0)
            tspec[~mask] = 0.0
            dphi = np.real(np.fft.ifft(tspec, axis=0))
            shift = gain * dphi
            m = float(np.abs(shift).max()) if shift.size else 0.0
            if m > max_shift:
                max_shift = m
            sub = sub * np.exp(1j * shift)
        acc += filt[None] * np.fft.fft2(sub, axes=(1, 2))
    out = _synthesise(acc, bank)
    if not np.isfinite(out).all():
        raise ValueError("%s: the reconstruction produced non-finite samples — "
                         "this is a bug in the filter bank, not in the input "
                         "(the input was validated finite)" % (op,))

    snr_in = band_snr(vid, lo, hi, fs)
    snr_out = band_snr(out, lo, hi, fs)
    return {
        "video": out, "alpha": a, "band_hz": (lo, hi), "fps": fs,
        "scales": ns, "orientations": no,
        "snr_in": snr_in, "snr_out": snr_out,
        "image_snr_change_db": snr_out["image_snr_db"] - snr_in["image_snr_db"],
        "motion_snr_change_db": snr_out["motion_snr_db"] - snr_in["motion_snr_db"],
        "phase_shift_max_rad": max_shift,
        "linear_regime": bool(max_shift < np.pi),
    }


# --------------------------------------------------------------------------- #
# Measurement                                                                   #
# --------------------------------------------------------------------------- #
def phase_displacement(video, f_lo, f_hi, fps, scales: int = 4,
                       orientations: int = 4) -> dict:
    """Sub-pixel displacement field from local phase -> ``dict``.

    The quantitative sibling of :func:`motion_magnify`: nothing is amplified and
    nothing is re-rendered, the displacement itself is returned in pixels.

    For each oriented sub-band, the temporal phase deviation ``dphi(t)`` (taken
    against the band's temporal mean, unwrapped in time, band-passed) obeys
    ``dphi = -(kx*dx + ky*dy)``, where ``(kx, ky)`` is the band's **local**
    spatial frequency in radians per pixel — computed exactly as
    ``Im(conj(z) grad z)/|z|^2`` with a spectral derivative, not from the band's
    nominal centre. Each band contributes one linear constraint on the same
    two unknowns, so the bands are combined per pixel by weighted least squares
    with weights ``|z|^2`` (a band with no contrast gets no vote).

    Returns ``{"dx": (T, H, W), "dy": (T, H, W), "weight": (H, W),
    "valid": (H, W) bool, "fps": ..., "band_hz": ..., "wrap_limit_px": ...}``.
    ``dx``/``dy`` follow :mod:`flow`: ``dx`` is column motion, ``dy`` row motion,
    positive towards increasing index, and both are zero-mean along time because
    the band-pass removed DC. Pixels where the normal equations are singular —
    a flat region, or one where every contributing band happens to share an
    orientation — are ``False`` in ``valid`` and exactly 0 in ``dx``/``dy``
    rather than filled with a plausible guess.

    **Accuracy and where it stops** (measured, 64x64x64 clip, 8 px grating,
    4 Hz bin-centred, noiseless, defaults; error is on the peak displacement):

    ======================  ===================  =================
    true amplitude d (px)   measured (px)        relative error
    ======================  ===================  =================
    0.001                   0.00100000           4.9e-11
    0.010                   0.01000000           4.9e-09
    0.100                   0.10000000           4.9e-07
    0.500                   0.50000615           1.2e-05
    1.000                   1.00009843           9.8e-05
    2.000                   2.00157540           7.9e-04
    3.000                   3.00797837           2.7e-03
    3.900                   3.92223401           5.7e-03
    4.100                   3.90855911           4.7e-02   <- folded
    6.000                   1.29857320           7.8e-01   <- folded
    ======================  ===================  =================

    The breakdown at ``d = 4`` px is not a tuning failure: the grating has an
    8 px wavelength, ``k = 2*pi/8``, and ``|k*d| = pi`` exactly at ``d = 4``.
    Past that the phase has wrapped and no phase-based method can recover the
    displacement from a single band. ``wrap_limit_px`` in the return is that
    bound computed from the measured local frequencies (``pi / max|k|``), so a
    caller can check their motion against it instead of guessing."""
    op = "phase_displacement"
    vid = _require_video(video, "video", op, MAX_PYRAMID_ELEMENTS)
    t, h, w = vid.shape
    lo, hi, fs, mask, _freq = _require_band(f_lo, f_hi, fps, t, op)
    ns = _count(scales, "scales", 1, MAX_SCALES)
    no = _count(orientations, "orientations", 1, MAX_ORIENTATIONS)
    bank = _filter_bank(h, w, ns, no)
    fu, fv = bank["fu"], bank["fv"]

    spec = np.fft.fft2(vid, axes=(1, 2))
    a00 = np.zeros((h, w))
    a01 = np.zeros((h, w))
    a11 = np.zeros((h, w))
    b0 = np.zeros((t, h, w))
    b1 = np.zeros((t, h, w))
    weight = np.zeros((h, w))
    kmax = 0.0
    for j, filt in enumerate(bank["filters"]):
        if bank["kinds"][j] != _ORIENTED:
            continue
        sub = np.fft.ifft2(spec * filt[None], axes=(1, 2))
        ref = sub.mean(axis=0)
        amp2 = np.abs(ref) ** 2
        if not amp2.any():
            continue
        rspec = np.fft.fft2(ref)
        dzdx = np.fft.ifft2(rspec * (2j * np.pi * fu))
        dzdy = np.fft.ifft2(rspec * (2j * np.pi * fv))
        den = np.where(amp2 > 0.0, amp2, 1.0)
        kx = np.imag(np.conj(ref) * dzdx) / den
        ky = np.imag(np.conj(ref) * dzdy) / den
        kx = np.where(amp2 > 0.0, kx, 0.0)
        ky = np.where(amp2 > 0.0, ky, 0.0)
        dphi = np.angle(sub * np.conj(ref)[None])
        dphi = np.unwrap(dphi, axis=0)
        tspec = np.fft.fft(dphi, axis=0)
        tspec[~mask] = 0.0
        dphi = np.real(np.fft.ifft(tspec, axis=0))

        wgt = amp2
        a00 += wgt * kx * kx
        a01 += wgt * kx * ky
        a11 += wgt * ky * ky
        b0 -= (wgt * kx)[None] * dphi
        b1 -= (wgt * ky)[None] * dphi
        weight += wgt
        km = float(np.sqrt(kx * kx + ky * ky).max())
        if km > kmax:
            kmax = km

    det = a00 * a11 - a01 * a01
    trace = a00 + a11
    tol = 1e-12 * np.maximum(trace * trace, np.finfo(float).tiny)
    valid = det > tol
    safe = np.where(valid, det, 1.0)
    dx = np.where(valid[None], (a11[None] * b0 - a01[None] * b1) / safe[None], 0.0)
    dy = np.where(valid[None], (a00[None] * b1 - a01[None] * b0) / safe[None], 0.0)
    if not (np.isfinite(dx).all() and np.isfinite(dy).all()):
        raise ValueError("%s: the least-squares solve produced non-finite "
                         "displacements — this is a bug in the singularity guard, "
                         "not in the input" % (op,))
    return {"dx": dx, "dy": dy, "weight": weight, "valid": valid,
            "fps": fs, "band_hz": (lo, hi), "frames": t,
            "wrap_limit_px": (np.pi / kmax) if kmax > 0.0 else 0.0}


def displacement_series(video, f_lo, f_hi, fps, scales: int = 4,
                        orientations: int = 4) -> np.ndarray:
    """Whole-frame displacement waveform -> ``(T, 2)`` array of ``(dx, dy)``.

    The contrast-weighted spatial mean of :func:`phase_displacement`, i.e. the
    rigid-body motion of the scene in pixels, one row per frame. This is the
    trace to plot, or to feed to ``dsp.spectrum`` to read off the resonant
    frequency — a vibration waveform recovered from a camera.

    Weights are the same ``|z|^2`` contrast the field solve uses, restricted to
    the pixels marked ``valid``, so blank regions do not drag the average
    towards zero. A clip with no valid pixel anywhere (a constant image) returns
    exact zeros rather than a division by zero.

    Sub-pixel accuracy inherits from :func:`phase_displacement`; measured on the
    64x64x64 / 8 px / 4 Hz synthetic, a true 0.5 px amplitude is recovered as
    0.50000615 px (1.2e-05 relative)."""
    field = phase_displacement(video, f_lo, f_hi, fps, scales, orientations)
    wgt = field["weight"] * field["valid"]
    total = float(wgt.sum())
    t = field["dx"].shape[0]
    if total <= 0.0:
        return np.zeros((t, 2), np.float64)
    dx = (field["dx"] * wgt[None]).sum(axis=(1, 2)) / total
    dy = (field["dy"] * wgt[None]).sum(axis=(1, 2)) / total
    return np.stack([dx, dy], axis=1)
