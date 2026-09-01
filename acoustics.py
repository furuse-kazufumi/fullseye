# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""acoustics — condition monitoring and standard acoustic metrics on 1-D sound.

:mod:`dsp` already reads a WAV file, filters it, and takes its spectrum. That is
the *material*; this module is the *instrument*. The questions a machine's sound
is actually asked in the field are narrower and harder than "where is the
energy":

* **Which defect is that?** A rolling-element bearing with a spalled race does
  not ring at the defect frequency — it rings at a structural resonance, several
  kHz up, *amplitude-modulated* by the defect frequency, which is typically well
  under 200 Hz. The defect is invisible in the raw spectrum and obvious in the
  envelope spectrum. See :func:`envelope_spectrum` and
  :func:`bearing_defect_frequencies`.
* **Is that peak a machine order or a resonance?** If the shaft speed moves,
  every speed-locked component smears across the spectrum and every fixed
  resonance stays put. Resampling the signal onto the *shaft angle* axis makes
  the orders sharp again and the resonances smear instead. See
  :func:`angular_resample` and :func:`order_spectrum`.
* **How loud, by whose definition?** A level is meaningless without a stated
  reference and a stated frequency weighting. See :func:`equivalent_level`,
  :func:`weighting_response` and :func:`octave_spectrum`.
* **Did that vibration come from this excitation?** Two channels, a transfer
  function, and the coherence that says how much of the answer to believe. See
  :func:`transfer_function` and :func:`coherence`.

Everything here is numpy + scipy and deterministic. Every claim in these
docstrings was produced by running the code (``tests/test_acoustics.py`` and
``examples/acoustic_condition_monitoring.py`` re-derive them).

Method and its public sources
-----------------------------
* Short-time Fourier transform with weighted overlap-add inversion — Allen &
  Rabiner, *A Unified Approach to Short-Time Fourier Analysis and Synthesis*,
  Proc. IEEE 65(11), 1977; Griffin & Lim, IEEE TASSP 32(2), 1984. Exact
  reconstruction needs only the NOLA condition (the squared window sums to
  something strictly positive everywhere), not COLA; COLA is what makes
  *unmodified* overlap-add work without the division, and :func:`stft_cola_check`
  reports it separately.
* Envelope (high-frequency resonance) analysis of rolling-element bearings —
  Darlow, Badgley & Hogg, *Applications of High-Frequency Resonance Techniques
  for Bearing Diagnostics*, 1974; Randall & Antoni, *Rolling element bearing
  diagnostics — a tutorial*, MSSP 25(2), 2011.
* Bearing defect kinematics (cage / outer race / inner race / rolling element
  rates) — the standard epicyclic no-slip derivation, e.g. Harris, *Rolling
  Bearing Analysis*; reproduced from the geometry in
  :func:`bearing_defect_frequencies` rather than copied from a table.
* Computed order tracking by angular resampling — Fyfe & Munck, *Analysis of
  Computed Order Tracking*, MSSP 11(2), 1997.
* Cepstrum for periodic structure in the log spectrum (echo delay, sideband
  spacing) — Bogert, Healy & Tukey, *The Quefrency Alanysis of Time Series for
  Echoes*, 1963; Randall, *A history of cepstrum analysis*, MSSP 97, 2017.
* Spectral kurtosis as an impulsiveness-vs-frequency map — Antoni, *The spectral
  kurtosis: a useful tool for characterising non-stationary signals*, MSSP 20(2),
  2006.
* Fractional-octave band definition — the geometric construction ``f_c =
  f_ref * G**(x/b)`` with ``G = 10**(3/10)`` (base-ten) or ``G = 2``
  (base-two), band edges at ``f_c * G**(-+1/(2b))``. Computed from that
  definition; no published band table is transcribed.
* A- and C-frequency weighting — the pole frequencies of the classical weighting
  networks (20.598997, 107.65265, 737.86223, 12194.217 Hz), normalised so the
  response is exactly 0 dB at 1 kHz *by construction* rather than by adding a
  published offset constant. See :func:`weighting_response`.
* Welch-averaged auto/cross spectra, the H1 and H2 estimators and the ordinary
  coherence function — Welch, IEEE TAE 15(2), 1967; Bendat & Piersol,
  *Random Data: Analysis and Measurement Procedures*.

Conventions
-----------
* A **signal** is a 1-D float64 array. It is *not* required to lie in
  ``[-1, 1]`` — a calibrated pressure or acceleration record does not.
* A **sample rate** is always the argument named ``rate``, in hertz, and always
  comes immediately after the signal — the same order :mod:`dsp` uses.

  **The sample rate is the one error this module cannot catch, so it is worth
  being blunt about.** It is not in the array; it is a separate number, and a
  wrong one produces no exception, no NaN and no warning. Measured, on a
  correct recording of a bearing with a 107 Hz defect at 25600 Hz:

  =============  ==========================  =========  ==================
  rate passed    defect reported             A-w. Leq   loudest 1/3 octave
  =============  ==========================  =========  ==================
  25600 (true)   107.0000 Hz                 -1.2708    3162.3 Hz
  48000 (wrong)  **200.6250 Hz**             -2.2506    6309.6 Hz
  =============  ==========================  =========  ==================

  Every number moved, every number is plausible, and 200.6 Hz would be matched
  against the wrong bearing kinematics. What *can* be done is refuse the ways a
  wrong rate arrives silently, and that is done: strings, bools and complex
  numbers all raise. ``float("16000")`` succeeds, so without that refusal an
  unparsed configuration value becomes a sample rate; ``True`` promotes to 1 Hz.
* A **frequency** is in hertz, an **order** is in multiples of the shaft
  rotation rate, a **quefrency** is in seconds, and a **level** is in decibels
  relative to an explicitly supplied ``ref`` amplitude. There is no implicit
  20 uPa: this library never sees your microphone's calibration, so a default of
  ``ref=1.0`` means "dB relative to one unit of whatever you passed in" and
  says so. Pass ``ref=20e-6`` when your signal really is pascals.
* Spectrogram-shaped outputs are ``(n_freqs, n_frames)``, matching
  :func:`dsp.spectrogram`.
* Nothing above Nyquist is folded. A carrier, a band edge, an order or a
  requested angular resolution that the sample rate cannot represent raises
  ``ValueError`` naming the limit, following the refusal
  :func:`photoncount.tcspc_simulate` makes for a distance past the unambiguous
  range.

Where this sits next to what already exists
-------------------------------------------
* :mod:`dsp` owns audio I/O, Butterworth filtering, the plain spectrum and
  spectrogram, the Hilbert envelope, RMS, resampling and peak picking. **None of
  it is re-implemented here**: :func:`envelope_spectrum` calls ``dsp.bandpass``
  and ``dsp.envelope``, :func:`order_spectrum` is compared against
  ``dsp.spectrum``, and the examples read their input with ``dsp.read_wav``.
  What this module adds is everything ``dsp`` stops short of — invertible STFT,
  demodulation, order tracking, cepstrum, fractional-octave bands, weighting
  curves and two-channel estimators.
* :mod:`funct1d` owns generic 1-D function algebra (smoothing, derivative,
  integral, zero crossings, matching). Unchanged and freely composable: every
  array this module returns is an ordinary 1-D float64 array.
* :mod:`motionmag` measures **the same physical quantity — a small vibration —
  through a camera instead of a microphone.** There the observable is the local
  phase of an oriented sub-band and the answer is a displacement in pixels; here
  the observable is sound pressure and the answer is a modulation rate in hertz.
  The two are complementary, not overlapping: ``motionmag.displacement_series``
  returns a ``(T, 2)`` displacement waveform sampled at the camera's frame rate,
  which is an ordinary 1-D signal — feed a column of it to :func:`stft`,
  :func:`cepstrum` or :func:`envelope_spectrum` and the vibration a camera saw
  is analysed by exactly the machinery below. A camera at 240 fps reaches
  120 Hz; a microphone at 48 kHz reaches 24 kHz and sees the structural
  resonance the bearing actually rings at, which is why bearing diagnosis is an
  acoustic problem and modal shape visualisation is an optical one.
* :mod:`rangedoppler` owns array processing for **coherent narrowband
  radio-frequency** data: a complex baseband beat cube, a carrier wavelength,
  and a delay-and-sum beamformer whose steering vectors are phase ramps at that
  one wavelength. There is deliberately **no acoustic beamformer here**. A
  microphone array on a broadband real-valued signal is a different regime (the
  steering delays are fractional samples, not a single phase per element), and
  adding a second, incompatible beamformer to the repository would be worse than
  having none; if array acoustics is wanted later it belongs beside the existing
  one, sharing its steering-matrix code.
* :mod:`photoncount` supplies the fail-closed idiom this module follows for
  scalars, size caps and out-of-range refusals.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    # transform
    "stft", "istft", "stft_cola_check",
    # synthesis (forward models — the ground truth generators)
    "synthesize_bearing_signal", "synthesize_speed_ramp",
    # bearing / rotating machinery
    "envelope_spectrum", "bearing_defect_frequencies", "spectral_kurtosis",
    "cepstrum",
    # order tracking
    "angular_resample", "order_spectrum",
    # acoustic metrics
    "octave_bands", "octave_spectrum", "weighting_response", "apply_weighting",
    "equivalent_level", "percentile_level",
    # two-channel
    "coherence", "transfer_function",
    # limits
    "MAX_SAMPLES", "MAX_WINDOW", "MAX_STFT_ELEMENTS", "MAX_BANDS",
    "MAX_ANGULAR_SAMPLES", "FLOOR_DB",
]


# --------------------------------------------------------------------------- #
# Limits. Every one of these exists because a *small* argument can otherwise    #
# ask for a very large allocation: an STFT is n_freqs x n_frames, and a hop of  #
# 1 sample over a 2^20 window is 10^11 complex numbers from a one-second clip.  #
# The checks are applied to the raw object's element count **before** any       #
# promotion to float64, because a memory-mapped int8 record promotes 8x and the #
# cap must fire before the copy, not after.                                     #
# --------------------------------------------------------------------------- #

#: Largest accepted signal length (2^24 = 16.8 M samples, 350 s at 48 kHz).
MAX_SAMPLES = 1 << 24

#: Largest accepted analysis window / FFT length.
MAX_WINDOW = 1 << 20

#: Largest ``n_freqs * n_frames`` for any short-time transform. 2^24 complex128
#: is 268 MB, and the STFT machinery holds two such arrays at once.
MAX_STFT_ELEMENTS = 1 << 24

#: Largest number of fractional-octave bands in one request.
MAX_BANDS = 4096

#: Largest ``nfft / win``. Zero-padding a frame interpolates its spectrum and 2x
#: to 8x is ordinary practice, but the memory grows linearly in ``nfft`` while
#: the information does not grow at all. Found by adversarial audit: ``win=256,
#: nfft=2**20`` on a 1000-sample (8 kB) input passed the element cap — 11 frames
#: x 524289 bins is 5.77 M coefficients, under :data:`MAX_STFT_ELEMENTS` — and
#: allocated **92.3 MB**, an 11500x amplification from a small, innocuous input.
MAX_NFFT_RATIO = 16

#: Largest angle-domain record produced by :func:`angular_resample`.
MAX_ANGULAR_SAMPLES = 1 << 24

#: Levels are reported in dB and a level can legitimately be the log of exactly
#: zero (silence, a zero-mean band, an empty octave band). ``-inf`` would poison
#: every downstream average, so it is clamped here and the fact that it was
#: clamped is returned alongside the number.
FLOOR_DB = -200.0

#: Reference frequency of the fractional-octave and weighting constructions.
#: Both systems are *defined* to pass through 1 kHz, so this is the one number
#: that is a definition rather than a measurement.
F_REF_HZ = 1000.0

#: Pole frequencies of the classical A / C weighting networks, in hertz.
#: These four numbers are the definition of the curves; every decibel value this
#: module reports for a weighting is computed from them, so no published table
#: of attenuations is transcribed anywhere in this repository.
_W_F1 = 20.598997
_W_F2 = 107.65265
_W_F3 = 737.86223
_W_F4 = 12194.217


# --------------------------------------------------------------------------- #
# fail-closed input helpers                                                     #
# --------------------------------------------------------------------------- #
def _finite_scalar(v, name: str) -> float:
    """A real, finite Python float — or ``ValueError`` naming the problem.

    The string branch is the important one for this module. ``float("16000")``
    succeeds, so without it a sample rate that arrived as text from a config
    file, a JSON payload or a CSV header is accepted silently and **every
    frequency, order, quefrency and level below is then wrong by an unknown
    factor with no error anywhere**. The bool branch blocks ``True == 1``, which
    as a rate means a 1 Hz timebase. The complex branch blocks the silent loss
    of an imaginary part."""
    if np.ma.is_masked(v):
        raise ValueError("%s is a masked value — fill or drop it explicitly" % (name,))
    if isinstance(v, (complex, np.complexfloating)):
        raise ValueError("%s is complex — a rate / frequency / level is a real "
                         "quantity; coercion would silently drop the imaginary "
                         "part" % (name,))
    if isinstance(v, (bool, np.bool_)):
        raise ValueError("%s is a bool — refusing the silent True==1 promotion "
                         "(as a sample rate that would mean a 1 Hz timebase)"
                         % (name,))
    if isinstance(v, (str, bytes, np.str_, np.bytes_)):
        raise ValueError("%s is a string (%r) — a rate / frequency must be a "
                         "number; float(%r) would silently succeed and every "
                         "frequency computed from it would be wrong with no "
                         "error raised anywhere" % (name, v, v))
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
        raise ValueError("%s must be an int, got %r (a float window length or "
                         "bin count is almost always a unit mix-up)"
                         % (name, type(v).__name__))
    n = int(v)
    if n < lo or n > hi:
        raise ValueError("%s must be in [%d, %d], got %d (the cap is there so a "
                         "mistyped argument fails instead of allocating "
                         "gigabytes)" % (name, lo, hi, n))
    return n


def _seed(v, name: str = "seed"):
    if v is None:
        return None
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s must be None or an int, got %r"
                         % (name, type(v).__name__))
    return int(v)


def _rate(v, name: str = "rate") -> float:
    """A sample rate in hertz: real, finite, strictly positive."""
    return _positive(v, name)


def _as_signal(x, name: str, op: str, min_len: int = 2,
               cap: int = MAX_SAMPLES) -> np.ndarray:
    """Coerce to a validated finite 1-D float64 signal.

    The size cap is applied to the *incoming* object's element count, before
    ``np.ascontiguousarray(..., float64)`` runs, so an int8 or float32 record
    over the cap is refused without first making an 8x or 2x copy of it."""
    if np.ma.is_masked(x):
        raise ValueError("%s: %s is a masked array with masked entries — the "
                         "mask would be stripped and the raw values underneath "
                         "used; fill or drop them explicitly" % (op, name))
    size = getattr(x, "size", None)
    if size is None:
        try:
            size = len(x)
        except TypeError:
            size = None
    if size is not None and int(size) > cap:
        raise ValueError("%s: %s has %d samples, over the %d cap "
                         "(acoustics.MAX_SAMPLES). Checked before the float64 "
                         "promotion so an over-cap low-precision record is "
                         "refused without being copied first"
                         % (op, name, int(size), cap))
    if np.iscomplexobj(x):
        raise ValueError("%s: %s is complex — coercion to float64 would silently "
                         "discard the imaginary part; take .real / .imag / abs() "
                         "explicitly" % (op, name))
    arr = np.ascontiguousarray(x, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError("%s: %s must be a 1-D signal, got a %d-D array of shape "
                         "%r — nothing is flattened or reshaped silently"
                         % (op, name, arr.ndim, tuple(np.shape(x))))
    if arr.size < min_len:
        raise ValueError("%s: %s has %d sample(s), need at least %d"
                         % (op, name, arr.size, min_len))
    if arr.size > cap:                       # lists only reach the cap here
        raise ValueError("%s: %s has %d samples, over the %d cap "
                         "(acoustics.MAX_SAMPLES)" % (op, name, arr.size, cap))
    if not np.isfinite(arr).all():
        n = int((~np.isfinite(arr)).sum())
        raise ValueError("%s: %s has %d non-finite sample(s) (NaN/Inf) — refusing "
                         "(one poisoned sample spreads over the whole spectrum "
                         "through the FFT)" % (op, name, n))
    return arr


def _check_choice(v, allowed, name: str, op: str) -> str:
    if not isinstance(v, str):
        raise ValueError("%s: %s must be one of %r, got %r"
                         % (op, name, tuple(allowed), type(v).__name__))
    s = v.lower()
    if s not in allowed:
        raise ValueError("%s: %s must be one of %r, got %r"
                         % (op, name, tuple(allowed), v))
    return s


def _db_power(power, ref_power: float, floor_db: float = FLOOR_DB):
    """``10*log10(power / ref_power)`` with an explicit floor instead of -inf.

    Returns ``(level, clamped)`` for a scalar, or ``(levels, clamped_mask)`` for
    an array. A band with exactly zero energy is a real case, not an error, and
    ``-inf`` in a level array poisons every mean taken over it afterwards."""
    p = np.asarray(power, np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        lvl = 10.0 * np.log10(p / ref_power)
    clamped = ~np.isfinite(lvl) | (lvl < floor_db)
    lvl = np.where(clamped, floor_db, lvl)
    if p.ndim == 0:
        return float(lvl), bool(clamped)
    return lvl, clamped


def _window_values(window, n: int, op: str) -> np.ndarray:
    """A periodic (``fftbins=True``) analysis window of length *n*.

    Periodic, not symmetric: the symmetric Hann that ``numpy.hanning`` returns
    is **not** COLA at hop = win/2, and the periodic one is exactly constant
    there. :func:`dsp.spectrogram` uses the symmetric form, which is fine for a
    magnitude display and wrong for an invertible transform, so the difference is
    named here rather than left to be discovered."""
    from scipy.signal import get_window
    if isinstance(window, np.ndarray) or isinstance(window, (list, tuple)) and (
            window and not isinstance(window[0], str)):
        w = np.ascontiguousarray(window, dtype=np.float64)
        if w.ndim != 1 or w.size != n:
            raise ValueError("%s: an explicit window array must be 1-D of length "
                             "win=%d, got shape %r" % (op, n, tuple(np.shape(w))))
    else:
        if not isinstance(window, (str, tuple)):
            raise ValueError("%s: window must be a name, a (name, param) tuple, "
                             "or an array of length win; got %r"
                             % (op, type(window).__name__))
        try:
            w = np.asarray(get_window(window, n, fftbins=True), np.float64)
        except Exception as exc:
            raise ValueError("%s: unknown window %r (%s)" % (op, window, exc)) from None
    if not np.isfinite(w).all():
        raise ValueError("%s: window has non-finite values" % (op,))
    if not np.any(w != 0.0):
        raise ValueError("%s: window is identically zero — every frame would be "
                         "zero and every level -inf" % (op,))
    return w


# --------------------------------------------------------------------------- #
# 1. Short-time Fourier transform (invertible)                                  #
# --------------------------------------------------------------------------- #
def _stft_geometry(n: int, win: int, hop: int, op: str):
    """Padding and frame starts such that every original sample is covered.

    The signal is padded by a full window on each side so the first and last
    real samples sit under the flat part of the overlap sum, and the tail is
    extended until a whole number of hops fits."""
    pad_left = win
    total = n + 2 * win
    extra = (-(total - win)) % hop
    padded = total + extra
    starts = np.arange(0, padded - win + 1, hop, dtype=np.int64)
    return pad_left, padded, starts


def stft(x, rate, win=256, hop=None, window="hann", nfft=None, scaling="none"):
    """Short-time Fourier transform that keeps the phase and can be inverted.

    :func:`dsp.spectrogram` returns magnitudes, which is all a display needs and
    strictly less than an analysis needs: a magnitude spectrogram cannot be
    turned back into a signal, so there is no path in :mod:`dsp` that filters or
    modifies a signal in the time-frequency plane and comes back. This is that
    path, and the test of it is that the round trip is exact.

    Returns a dict (the transform plus everything :func:`istft` needs to undo
    it):

    ``spectra``
        complex128 ``(n_freqs, n_frames)``, same orientation as
        :func:`dsp.spectrogram`.
    ``freqs``, ``times``
        bin centre frequencies in Hz and frame start times in seconds. Frame
        time 0.0 is the first *original* sample, so the leading pad does not
        shift the time axis.
    ``rate``, ``win``, ``hop``, ``nfft``, ``length``, ``pad_left``, ``scale``,
    ``scaling``, ``window``, ``window_values``
        the geometry, kept so the inverse needs no arguments.
    ``nola_min``
        the smallest value of the squared-window overlap sum over the original
        samples. Reconstruction divides by this sum, so a value of zero means
        some sample is not reconstructible; it is refused up front rather than
        producing a hole.
    ``interior``
        boolean mask over frames, true for the frames that lie **entirely inside
        the original signal**. The transform pads by a full window at each end so
        that inversion is exact, and the frames straddling that pad see part
        zeros — they are correct as coefficients but they are not representative,
        and any statistic averaged over *all* frames is therefore biased low.
        Measured on 16384 samples of unit-variance white noise, win = 1024,
        hop = 512: the ``"density"`` spectrum integrates to 0.9073 over all 35
        frames and to 0.9933 over the 31 interior ones (the signal's own variance
        is 0.9923). :func:`spectral_kurtosis` uses this mask for exactly that
        reason — a half-empty frame looks impulsive.

    **Normalisation is explicit**, because a windowed spectrum has no single
    natural amplitude and a plausible-looking dB number is the usual result of
    leaving it implicit. ``scaling`` selects a real factor applied to every
    coefficient, recorded as ``scale`` and divided out again by :func:`istft`:

    * ``"none"`` (default) — the raw ``rfft`` of the windowed frame.
    * ``"amplitude"`` — ``2 / sum(w)``. A sinusoid of amplitude ``A`` sitting on
      a bin centre then reads ``|Z| = A``. Measured on a 1 kHz, amplitude-0.7
      tone at 16 kHz with a 256-sample periodic Hann, over the interior frames:
      ``|Z|`` ranges 0.699999999999999 to 0.700000000000001.
      DC and Nyquist read twice their amplitude under this convention (they are
      not two-sided), which is the standard caveat and is not corrected for.
    * ``"density"`` — ``sqrt(2 / (rate * sum(w**2)))``, so ``|Z|**2`` is a
      single-sided power spectral density in units^2/Hz. Measured on 16384
      samples of white noise at 16 kHz (win 1024, hop 512): the PSD integrates
      to 0.9933 over the interior frames against the record's own variance
      0.9923, and to 0.9073 if the pad frames are included — see ``interior``.

    **Raises** ``ValueError``: non-1-D / non-finite / complex / masked input,
    ``rate <= 0``, a string or bool rate, ``hop`` outside ``[1, win]``,
    ``nfft < win``, an unknown window, an all-zero window, a transform over
    :data:`MAX_STFT_ELEMENTS`, and a window/hop pair whose squared overlap sum
    touches zero (NOLA violated — the round trip would be silently lossy).
    """
    op = "stft"
    fs = _rate(rate)
    arr = _as_signal(x, "x", op, min_len=1)
    w_len = _count(win, "win", 2, MAX_WINDOW)
    h = w_len // 2 if hop is None else _count(hop, "hop", 1, MAX_WINDOW)
    if h > w_len:
        raise ValueError("%s: hop=%d is larger than win=%d — the frames would "
                         "not overlap and %d sample(s) between every pair of "
                         "frames would be dropped from the transform entirely"
                         % (op, h, w_len, h - w_len))
    n_fft = w_len if nfft is None else _count(nfft, "nfft", 2, MAX_WINDOW)
    if n_fft < w_len:
        raise ValueError("%s: nfft=%d is below win=%d — the window would be "
                         "truncated, not zero-padded" % (op, n_fft, w_len))
    if n_fft > MAX_NFFT_RATIO * w_len:
        raise ValueError("%s: nfft=%d is %.0fx win=%d, over the %dx cap "
                         "(acoustics.MAX_NFFT_RATIO). Zero-padding interpolates "
                         "the spectrum and adds no information, but the "
                         "allocation grows linearly in nfft — measured, "
                         "win=256 nfft=2**20 on a 1000-sample input passes the "
                         "coefficient cap and still asks for 92 MB"
                         % (op, n_fft, n_fft / float(w_len), w_len,
                            MAX_NFFT_RATIO))
    mode = _check_choice(scaling, ("none", "amplitude", "density"), "scaling", op)
    w = _window_values(window, w_len, op)

    n = arr.size
    pad_left, padded, starts = _stft_geometry(n, w_len, h, op)
    n_freqs = n_fft // 2 + 1
    if starts.size * n_freqs > MAX_STFT_ELEMENTS:
        raise ValueError("%s: the transform would be %d frames x %d bins = %d "
                         "coefficients, over the %d cap "
                         "(acoustics.MAX_STFT_ELEMENTS). n=%d, win=%d, hop=%d, "
                         "nfft=%d — a small signal with a small hop is the usual "
                         "way to reach this"
                         % (op, starts.size, n_freqs, starts.size * n_freqs,
                            MAX_STFT_ELEMENTS, n, w_len, h, n_fft))

    buf = np.zeros(padded, np.float64)
    buf[pad_left:pad_left + n] = arr
    frames = np.lib.stride_tricks.sliding_window_view(buf, w_len)[starts]
    spec = np.fft.rfft(frames * w[None, :], n=n_fft, axis=1).T

    wsum = np.zeros(padded, np.float64)
    w2 = w * w
    for s in starts:
        wsum[s:s + w_len] += w2
    nola_min = float(wsum[pad_left:pad_left + n].min()) if n else float(wsum.min())
    if nola_min <= 0.0:
        raise ValueError("%s: the squared window overlap sum touches %g inside "
                         "the signal (window=%r, win=%d, hop=%d). Inversion "
                         "divides by that sum, so those samples are not "
                         "recoverable — the round trip would silently lose them. "
                         "Use a smaller hop or a window without interior zeros"
                         % (op, nola_min, window, w_len, h))

    if mode == "amplitude":
        scale = 2.0 / float(w.sum()) if float(w.sum()) != 0.0 else 1.0
    elif mode == "density":
        scale = float(np.sqrt(2.0 / (fs * float((w * w).sum()))))
    else:
        scale = 1.0
    if scale != 1.0:
        spec = spec * scale

    freqs = np.fft.rfftfreq(n_fft, d=1.0 / fs)
    times = (starts.astype(np.float64) - pad_left) / fs
    interior = (starts >= pad_left) & (starts + w_len <= pad_left + n)
    return {
        "spectra": np.ascontiguousarray(spec),
        "freqs": freqs,
        "times": times,
        "interior": interior,
        "rate": fs, "win": w_len, "hop": h, "nfft": n_fft,
        "length": int(n), "pad_left": int(pad_left), "padded": int(padded),
        "scale": float(scale), "scaling": mode,
        "window": window if isinstance(window, str) else "array",
        "window_values": w,
        "nola_min": nola_min,
        "n_frames": int(starts.size),
    }


def istft(transform):
    """Invert :func:`stft` by weighted overlap-add — exactly.

    Weighted overlap-add divides the synthesised sum by the overlap sum of the
    *squared* window, which makes the reconstruction exact for any window and
    hop satisfying NOLA, not only for the COLA pairs. :func:`stft` refuses the
    NOLA violation up front, so if the transform was produced by it the inverse
    cannot be lossy.

    Measured round-trip error, ``max |x - istft(stft(x))|`` on 4096 samples of
    white noise (float64, so 2.2e-16 is one ulp of the largest sample):

    ===============  ====  ====  =========  =========
    window           win   hop   max error  nola_min
    ===============  ====  ====  =========  =========
    hann             256   128   1.33e-15   0.5
    hann             256   64    1.33e-15   1.5
    hann             256   255   2.73e-12   2.27e-08
    hamming          256   128   1.33e-15   0.5832
    blackman         512   128   1.33e-15   1.206
    flattop          256   64    1.33e-15   0.396
    boxcar           256   128   8.88e-16   2.0
    hann (nfft 512)  256   128   1.33e-15   0.5
    ===============  ====  ====  =========  =========

    Read the third row's two columns together. ``hop = 255`` on a 256-sample
    window overlaps by one sample, which breaks plain (unweighted) overlap-add
    completely; weighted overlap-add still inverts it, but only to 2.7e-12
    rather than 1.3e-15, because the squared-window overlap sum falls to
    2.3e-08 and the reconstruction divides by it. NOLA is satisfied and the
    result is four orders of magnitude less accurate than every other row —
    which is why ``nola_min`` is *returned* and not merely checked. A NOLA
    minimum that is small but positive is a conditioning warning, and there is
    no threshold at which it stops being one, so no threshold is invented here.

    **Raises** ``ValueError``: a dict missing any key :func:`stft` writes, a
    ``spectra`` whose shape disagrees with the recorded ``nfft`` / frame count,
    or a non-complex ``spectra``.
    """
    op = "istft"
    if not isinstance(transform, dict):
        raise ValueError("%s: expected the dict returned by stft(), got %r"
                         % (op, type(transform).__name__))
    need = ("spectra", "rate", "win", "hop", "nfft", "length", "pad_left",
            "padded", "scale", "window_values")
    miss = [k for k in need if k not in transform]
    if miss:
        raise ValueError("%s: the transform dict is missing %r — it must be the "
                         "dict stft() returned, unmodified apart from 'spectra'"
                         % (op, miss))
    spec = transform["spectra"]
    if not isinstance(spec, np.ndarray) or spec.ndim != 2:
        raise ValueError("%s: spectra must be a 2-D (n_freqs, n_frames) array, "
                         "got %r" % (op, type(spec).__name__))
    if spec.dtype.kind != "c":
        raise ValueError("%s: spectra is %s, not complex — a magnitude "
                         "spectrogram has no phase and cannot be inverted; "
                         "that is exactly why dsp.spectrogram is not invertible"
                         % (op, spec.dtype))
    if not np.isfinite(spec).all():
        raise ValueError("%s: spectra has non-finite coefficients — refusing"
                         % (op,))
    w = np.ascontiguousarray(transform["window_values"], np.float64)
    w_len = int(transform["win"])
    h = int(transform["hop"])
    n_fft = int(transform["nfft"])
    n = int(transform["length"])
    pad_left = int(transform["pad_left"])
    padded = int(transform["padded"])
    scale = float(transform["scale"])
    if spec.shape[0] != n_fft // 2 + 1:
        raise ValueError("%s: spectra has %d frequency bins but nfft=%d implies "
                         "%d — the transform dict and the array disagree"
                         % (op, spec.shape[0], n_fft, n_fft // 2 + 1))
    starts = np.arange(0, padded - w_len + 1, h, dtype=np.int64)
    if spec.shape[1] != starts.size:
        raise ValueError("%s: spectra has %d frames but the recorded geometry "
                         "(padded=%d, win=%d, hop=%d) implies %d"
                         % (op, spec.shape[1], padded, w_len, h, starts.size))

    frames = np.fft.irfft(spec.T / scale, n=n_fft, axis=1)[:, :w_len]
    acc = np.zeros(padded, np.float64)
    wsum = np.zeros(padded, np.float64)
    w2 = w * w
    for i, s in enumerate(starts):
        acc[s:s + w_len] += frames[i] * w
        wsum[s:s + w_len] += w2
    out = acc[pad_left:pad_left + n]
    den = wsum[pad_left:pad_left + n]
    if n and float(den.min()) <= 0.0:
        raise ValueError("%s: the squared window overlap sum touches zero inside "
                         "the reconstructed range — the geometry in the dict was "
                         "modified after stft() produced it" % (op,))
    return np.ascontiguousarray(out / den)


def stft_cola_check(window="hann", win=256, hop=None):
    """Does this (window, hop) pair satisfy COLA, and how exactly?

    COLA — the analysis windows summing to a constant over the hop lattice — is
    what lets plain overlap-add work without a division. It is *not* required by
    :func:`istft`, which is weighted, but it is required by anything that
    overlap-adds modified frames without renormalising, and getting it wrong
    produces a periodic amplitude ripple at ``rate/hop`` Hz that looks like
    tremolo rather than like a bug.

    Returns a dict: ``cola`` (bool), ``constant`` (the mean of the overlap sum),
    ``max_deviation`` (absolute), ``relative_deviation``, ``nola`` (bool),
    ``min_squared_sum``, plus the geometry.

    Measured (periodic windows, ``relative_deviation`` of the plain sum):

    ========  ====  ====  ==================  ========  ====
    window    win   hop   relative_deviation  constant  COLA
    ========  ====  ====  ==================  ========  ====
    hann      256   128   4.44e-16            1.00      yes
    hann      256   64    2.22e-16            2.00      yes
    hann      256   85    1.48e-03            1.506     no
    hamming   256   128   2.06e-16            1.08      yes
    blackman  256   128   1.91e-01            0.84      no
    blackman  256   64    3.97e-16            1.68      yes
    boxcar    256   128   0.00e+00            2.00      yes
    ========  ====  ====  ==================  ========  ====

    The two blackman rows are the useful ones: the same window is COLA at
    hop = win/4 and 19 % off at hop = win/2, so "which window" is not the
    question — the pair is. The boxcar row was worth measuring rather than
    assuming: a rectangular window at 50 % overlap sums to exactly 2 and is
    COLA, which is the opposite of the usual intuition about it. Note also that
    the constant is not 1 in general — an overlap-add that does not divide by it
    is off by a *gain*, which is the failure that looks like a working system.

    **Raises** ``ValueError``: unknown / all-zero window, ``hop`` outside
    ``[1, win]``, ``win`` outside ``[2, MAX_WINDOW]``.
    """
    op = "stft_cola_check"
    w_len = _count(win, "win", 2, MAX_WINDOW)
    h = w_len // 2 if hop is None else _count(hop, "hop", 1, MAX_WINDOW)
    if h > w_len:
        raise ValueError("%s: hop=%d is larger than win=%d" % (op, h, w_len))
    w = _window_values(window, w_len, op)
    reps = max(4, 2 * (w_len // h) + 4)
    span = reps * h + w_len
    s1 = np.zeros(span, np.float64)
    s2 = np.zeros(span, np.float64)
    for i in range(reps):
        s1[i * h:i * h + w_len] += w
        s2[i * h:i * h + w_len] += w * w
    lo = w_len
    hi = span - w_len
    core1 = s1[lo:hi]
    core2 = s2[lo:hi]
    const = float(core1.mean())
    dev = float(np.abs(core1 - const).max()) if core1.size else 0.0
    rel = dev / abs(const) if const != 0.0 else float("inf") if dev > 0 else 0.0
    return {
        "cola": bool(rel <= 1e-12),
        "constant": const,
        "max_deviation": dev,
        "relative_deviation": float(rel),
        "nola": bool(core2.size and float(core2.min()) > 0.0),
        "min_squared_sum": float(core2.min()) if core2.size else 0.0,
        "window": window if isinstance(window, str) else "array",
        "win": w_len, "hop": h,
    }


# --------------------------------------------------------------------------- #
# 2. Forward models. Answers known before the measurement is made.              #
# --------------------------------------------------------------------------- #
def synthesize_bearing_signal(rate=25600.0, duration=1.0, carrier_hz=3000.0,
                              defect_hz=107.0, modulation=0.5, mode="am",
                              damping=0.05, noise_sigma=0.0, seed=None):
    """A resonance amplitude-modulated at a known defect rate — the ground truth.

    This is the whole reason envelope analysis exists, built forwards so the
    answer is known before the measurement. A spall on a bearing race does not
    radiate at the defect rate; it strikes a structure that rings at a much
    higher resonance, once per defect passage. What reaches the microphone is a
    **carrier at the resonance, modulated at the defect rate**, and the defect
    rate itself is not present in the signal as a frequency component at all.

    ``mode="am"`` gives the exactly analysable case,
    ``x(t) = (1 + m cos(2 pi f_d t)) sin(2 pi f_c t)``. Its analytic envelope is
    exactly ``1 + m cos(2 pi f_d t)`` for ``m < 1``, so the single-sided envelope
    spectrum has a line of amplitude **exactly m** at ``f_d`` and nothing else.
    Measured with ``m = 0.5``: :func:`envelope_spectrum` returns a peak at
    107.000000 Hz of amplitude 0.499677 (the 0.06 % shortfall is the band-pass
    filter rolling off across the two sidebands, not the demodulation).

    ``mode="impulse"`` gives the physically shaped case: an impulse train at
    ``f_d``, each impulse ringing down as ``exp(-2 pi zeta f_c t) sin(2 pi f_c
    t)``. The envelope spectrum then shows ``f_d`` **and its harmonics**, which
    is what a real record looks like. Measured with ``f_d = 107`` Hz: the
    envelope-spectrum peak is at 107.000000 Hz and the harmonics at 214 and
    321 Hz carry 0.6542 and 0.4748 of the fundamental's amplitude.

    In am mode the raw spectrum has **nothing** at ``f_d``: measured, the raw
    single-sided amplitude at 107 Hz is 4.3e-16, while the carrier reads
    1.000000 and each sideband at 2893 and 3107 Hz reads 0.250000 — exactly
    ``m/2``, as amplitude modulation requires. In impulse mode the raw amplitude
    at 107 Hz is 0.01165, not zero (an impulse train is not a pure product), but
    still 18x below what the envelope spectrum recovers from the same record.

    **Raises** ``ValueError``: any non-real / non-finite / string / bool scalar,
    ``rate <= 0``, ``duration <= 0``, ``modulation`` outside ``[0, 1)`` in am
    mode (at ``m >= 1`` the envelope is ``|1 + m cos|``, which folds and puts
    energy at ``2 f_d`` — a rectified envelope, not the modulation), ``damping``
    outside ``(0, 1)``, a total length over :data:`MAX_SAMPLES`, and — the one
    that matters — **any requested frequency at or above Nyquist, including the
    upper modulation sideband** ``f_c + f_d``. An aliased carrier would come
    back as a plausible signal at the wrong frequency with no error.
    """
    op = "synthesize_bearing_signal"
    fs = _rate(rate)
    dur = _positive(duration, "duration")
    fc = _positive(carrier_hz, "carrier_hz")
    fd = _positive(defect_hz, "defect_hz")
    m = _nonneg(modulation, "modulation")
    zeta = _finite_scalar(damping, "damping")
    sigma = _nonneg(noise_sigma, "noise_sigma")
    s = _seed(seed)
    kind = _check_choice(mode, ("am", "impulse"), "mode", op)
    nyq = 0.5 * fs
    n = int(round(dur * fs))
    if n < 2:
        raise ValueError("%s: duration=%g s at rate=%g Hz is %d sample(s)"
                         % (op, dur, fs, n))
    if n > MAX_SAMPLES:
        raise ValueError("%s: duration=%g s at rate=%g Hz is %d samples, over "
                         "the %d cap (acoustics.MAX_SAMPLES)"
                         % (op, dur, fs, n, MAX_SAMPLES))
    if fc >= nyq:
        raise ValueError("%s: carrier_hz=%g is at or above the Nyquist frequency "
                         "%g Hz (rate=%g). It would alias to %g Hz and the "
                         "result would look like a perfectly good signal at the "
                         "wrong frequency; refusing to fabricate that"
                         % (op, fc, nyq, fs, abs(fc - fs * round(fc / fs))))
    if fd >= nyq:
        raise ValueError("%s: defect_hz=%g is at or above the Nyquist frequency "
                         "%g Hz (rate=%g)" % (op, fd, nyq, fs))
    if fc + fd >= nyq:
        raise ValueError("%s: the upper modulation sideband carrier_hz + "
                         "defect_hz = %g Hz is at or above Nyquist %g Hz. The "
                         "carrier alone fits but the modulation does not, so the "
                         "sideband would fold down and the envelope spectrum "
                         "would show a defect rate that is not there"
                         % (op, fc + fd, nyq))
    if fd >= fc:
        raise ValueError("%s: defect_hz=%g must be below carrier_hz=%g — the "
                         "modulation has to be slower than what it modulates, "
                         "otherwise 'envelope' and 'carrier' swap meaning"
                         % (op, fd, fc))
    t = np.arange(n, dtype=np.float64) / fs
    if kind == "am":
        if m >= 1.0:
            raise ValueError("%s: modulation=%g must be < 1 in mode='am'. At "
                             "m >= 1 the analytic envelope is |1 + m cos|, which "
                             "rectifies and puts a line at 2*defect_hz — the "
                             "envelope spectrum would report twice the defect "
                             "rate with no error raised" % (op, m))
        x = (1.0 + m * np.cos(2.0 * np.pi * fd * t)) * np.sin(2.0 * np.pi * fc * t)
    else:
        if not 0.0 < zeta < 1.0:
            raise ValueError("%s: damping=%g must lie in (0, 1) — it is the "
                             "resonance's damping ratio" % (op, zeta))
        x = np.zeros(n, np.float64)
        period = fs / fd
        ring_len = int(min(n, max(8, np.ceil(4.0 / (2.0 * np.pi * zeta * fc / fs)))))
        tau = np.arange(ring_len, dtype=np.float64) / fs
        ring = np.exp(-2.0 * np.pi * zeta * fc * tau) * np.sin(2.0 * np.pi * fc * tau)
        k = 0
        while True:
            i0 = int(round(k * period))
            if i0 >= n:
                break
            seg = min(ring_len, n - i0)
            x[i0:i0 + seg] += ring[:seg]
            k += 1
        peak = float(np.abs(x).max())
        if peak > 0.0:
            x = x / peak
    if sigma > 0.0:
        rng = np.random.default_rng(s)
        x = x + sigma * rng.standard_normal(n)
    return np.ascontiguousarray(x)


def synthesize_speed_ramp(rate=5000.0, duration=4.0, rpm_start=600.0,
                          rpm_end=1800.0, orders=(1.0, 3.5),
                          amplitudes=None, resonance_hz=None,
                          noise_sigma=0.0, seed=None):
    """A run-up: components locked to shaft *order*, optionally one fixed in Hz.

    Order tracking has no meaning at constant speed, so its ground truth needs a
    signal whose shaft rate moves. Here the shaft rate ramps linearly from
    ``rpm_start`` to ``rpm_end`` and each component's instantaneous phase is
    ``2 pi * order * revolutions(t)`` — so it is locked to the shaft *exactly*,
    by construction, and its order is known to machine precision.

    ``resonance_hz`` adds one component at a **fixed frequency** instead. That is
    the discriminating case: after angular resampling an order stays put and a
    resonance smears, which is the whole diagnostic value of the transform.

    Returns a dict, because a speed record without its speed profile is not
    analysable: ``signal`` (the waveform), ``rpm`` (per-sample shaft rate),
    ``revolutions`` (cumulative, per-sample), ``rate``, ``duration``,
    ``orders``, ``total_revolutions``, ``resonance_hz``, and
    ``max_component_hz``.

    **Raises** ``ValueError``: non-real / string / bool scalars, non-positive
    ``rate`` / ``duration`` / ``rpm_start`` / ``rpm_end``, an empty or non-finite
    ``orders``, an ``amplitudes`` of the wrong length, a length over
    :data:`MAX_SAMPLES`, and **any component reaching Nyquist at the fastest
    point of the ramp** — checked at ``max(rpm)``, not at the mean, because a
    ramp that is legal on average can alias at its top end and produce a
    perfectly plausible spectrum.
    """
    op = "synthesize_speed_ramp"
    fs = _rate(rate)
    dur = _positive(duration, "duration")
    r0 = _positive(rpm_start, "rpm_start")
    r1 = _positive(rpm_end, "rpm_end")
    sigma = _nonneg(noise_sigma, "noise_sigma")
    s = _seed(seed)
    ords = np.atleast_1d(np.asarray(
        [_positive(o, "orders[%d]" % i) for i, o in enumerate(np.atleast_1d(orders))],
        np.float64))
    if ords.size == 0:
        raise ValueError("%s: orders is empty" % (op,))
    if amplitudes is None:
        amps = np.ones(ords.size, np.float64)
    else:
        amps = np.atleast_1d(np.asarray(
            [_finite_scalar(a, "amplitudes[%d]" % i)
             for i, a in enumerate(np.atleast_1d(amplitudes))], np.float64))
        if amps.size != ords.size:
            raise ValueError("%s: amplitudes has %d entries but orders has %d"
                             % (op, amps.size, ords.size))
    n = int(round(dur * fs))
    if n < 4:
        raise ValueError("%s: duration=%g s at rate=%g Hz is %d sample(s)"
                         % (op, dur, fs, n))
    if n > MAX_SAMPLES:
        raise ValueError("%s: %d samples, over the %d cap"
                         % (op, n, MAX_SAMPLES))
    nyq = 0.5 * fs
    f_shaft_max = max(r0, r1) / 60.0
    top = float(ords.max()) * f_shaft_max
    if top >= nyq:
        raise ValueError("%s: order %g at the fastest shaft rate %g rpm is %g Hz, "
                         "at or above Nyquist %g Hz (rate=%g). The ramp is legal "
                         "at its slow end and aliases at its fast end, which "
                         "produces a component that sweeps the wrong way with no "
                         "error anywhere" % (op, float(ords.max()),
                                             max(r0, r1), top, nyq, fs))
    if resonance_hz is not None:
        fres = _positive(resonance_hz, "resonance_hz")
        if fres >= nyq:
            raise ValueError("%s: resonance_hz=%g is at or above Nyquist %g Hz"
                             % (op, fres, nyq))
    else:
        fres = None

    t = np.arange(n, dtype=np.float64) / fs
    f0 = r0 / 60.0
    f1 = r1 / 60.0
    slope = (f1 - f0) / dur
    rev = f0 * t + 0.5 * slope * t * t          # exact integral of a linear ramp
    rpm = 60.0 * (f0 + slope * t)
    x = np.zeros(n, np.float64)
    for a, o in zip(amps, ords):
        x += a * np.sin(2.0 * np.pi * o * rev)
    if fres is not None:
        x += np.sin(2.0 * np.pi * fres * t)
    if sigma > 0.0:
        rng = np.random.default_rng(s)
        x = x + sigma * rng.standard_normal(n)
    return {
        "signal": np.ascontiguousarray(x),
        "rpm": np.ascontiguousarray(rpm),
        "revolutions": np.ascontiguousarray(rev),
        "rate": fs, "duration": dur,
        "orders": ords, "amplitudes": amps,
        "total_revolutions": float(rev[-1]),
        "resonance_hz": fres,
        "max_component_hz": float(top),
    }


# --------------------------------------------------------------------------- #
# 3. Bearing / rotating machinery diagnostics                                   #
# --------------------------------------------------------------------------- #
def envelope_spectrum(x, rate, low, high, order=4, n_peaks=5):
    """Band-pass, demodulate, transform — where a bearing defect actually shows.

    The three steps are each already available (``dsp.bandpass``,
    ``dsp.envelope``, ``numpy.fft``); what is not available anywhere in
    :mod:`dsp` is the *composition*, and the composition is the diagnostic. The
    raw spectrum of a defective bearing shows a resonance at some kHz and
    nothing at the defect rate; the envelope of that resonance band, transformed,
    shows the defect rate as a clean line.

    ``low`` / ``high`` are the demodulation band in Hz and are **required**,
    not optional. Choosing the band is the analysis; a default would hide the
    one decision that has to be made. :func:`spectral_kurtosis` finds a
    candidate band when there is no prior knowledge of the resonance.

    The envelope's mean is removed before the transform (otherwise a large DC
    line dominates every plot), amplitudes are single-sided (``2/N``), and DC is
    excluded from peak picking.

    Returns a dict: ``freqs``, ``magnitude``, ``peak_freq``, ``peak_amplitude``,
    ``peak_freqs`` / ``peak_amplitudes`` (the ``n_peaks`` largest, descending),
    ``band``, ``envelope_mean``, ``resolution_hz``, plus two numbers that exist
    because **this operator always returns a peak frequency, including when
    there is nothing there**:

    ``peak_prominence``
        the peak divided by the median of the magnitude spectrum.
    ``band_fraction``
        the RMS of the band-passed signal divided by the RMS of the input — how
        much of the record actually lives in the demodulation band.

    Found by adversarial audit and not repaired by an exception, because there
    is nothing invalid to refuse: a **constant** signal band-passed over
    100-2000 Hz has an envelope made of rounding error, and this operator dutifully
    reported ``peak_freq = 8.0000 Hz``. Nothing raised, nothing was NaN, and
    ``8 Hz`` is a perfectly plausible number to write down. Measured, the four
    cases separate on the returned numbers rather than on any invented
    threshold:

    ================  ========  =========  ===========  =============
    input             peak Hz   peak amp   prominence   band_fraction
    ================  ========  =========  ===========  =============
    AM, defect 107    107.0000  4.997e-01     10018.6      9.999e-01
    impulse + noise   107.0000  1.968e-01      9384.7      9.201e-01
    white noise       128.0000  2.785e-02        365.2     3.745e-01
    constant signal     8.0000  1.691e-12        173.0     1.995e-12
    ================  ========  =========  ===========  =============

    No cut-off is imposed here: a defect that is genuinely 20 dB into the noise
    is a real finding and refusing it would be worse than reporting it. The
    numbers are returned so the caller can see the difference between row 1 and
    row 4, which ``peak_freq`` alone does not show.

    Measured on :func:`synthesize_bearing_signal` (25600 Hz, 1 s, 3 kHz carrier,
    107 Hz defect, ``m = 0.5``) demodulated over 2000-4000 Hz: ``peak_freq =
    107.000000`` Hz, ``peak_amplitude = 0.499677`` — the modulation depth
    itself, because the analytic envelope of that signal is exactly
    ``1 + 0.5 cos(2 pi 107 t)``. The raw ``dsp.spectrum`` of the same signal has
    amplitude 4.3e-16 at 107 Hz: the defect rate is not present as a frequency
    component at all, which is the entire point of the operator.

    **Raises** ``ValueError``: everything :func:`_as_signal` and ``dsp.bandpass``
    refuse (non-finite, complex, masked, non-1-D, a band edge outside
    ``(0, rate/2)``, a signal too short for zero-phase filtering), plus a
    non-positive ``n_peaks``.
    """
    op = "envelope_spectrum"
    import dsp
    fs = _rate(rate)
    arr = _as_signal(x, "x", op, min_len=4)
    lo = _positive(low, "low")
    hi = _positive(high, "high")
    if hi <= lo:
        raise ValueError("%s: need low < high, got low=%g high=%g" % (op, lo, hi))
    if hi >= 0.5 * fs:
        raise ValueError("%s: high=%g Hz is at or above Nyquist %g Hz (rate=%g) "
                         "— there is no such band in this recording"
                         % (op, hi, 0.5 * fs, fs))
    k = _count(n_peaks, "n_peaks", 1, 4096)
    band = dsp.bandpass(arr, fs, lo, hi, order=order)
    env = dsp.envelope(band)
    env_mean = float(env.mean())
    e = env - env_mean
    n = e.size
    mag = np.abs(np.fft.rfft(e)) * (2.0 / n)
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    body = mag.copy()
    body[0] = 0.0                                # DC removed already; never a peak
    idx = np.argsort(body)[::-1][:k]
    idx = idx[body[idx] > 0.0]
    med = float(np.median(body[1:])) if body.size > 1 else 0.0
    peak = float(body.max())
    sig_rms = float(np.sqrt(np.mean(arr * arr)))
    band_rms = float(np.sqrt(np.mean(band * band)))
    return {
        "freqs": freqs,
        "magnitude": mag,
        "peak_freq": float(freqs[int(np.argmax(body))]),
        "peak_amplitude": peak,
        "peak_prominence": (peak / med) if med > 0.0 else float("inf"),
        "noise_floor": med,
        "band_rms": band_rms,
        "signal_rms": sig_rms,
        "band_fraction": (band_rms / sig_rms) if sig_rms > 0.0 else 0.0,
        "peak_freqs": freqs[idx].copy(),
        "peak_amplitudes": body[idx].copy(),
        "band": (lo, hi),
        "envelope_mean": env_mean,
        "resolution_hz": float(fs / n),
    }


def bearing_defect_frequencies(rpm=1800.0, n_elements=9, element_diameter=8.0,
                               pitch_diameter=40.0, contact_angle_deg=0.0):
    """The four characteristic rates of a rolling-element bearing, from geometry.

    Derived, not tabulated. Under pure rolling the cage advances at half the sum
    of the race surface speeds, which with ``r = d/D cos(alpha)`` gives, per
    shaft revolution rate ``f_r = rpm/60``:

    * ``FTF``  (cage / fundamental train) ``= f_r (1 - r) / 2``
    * ``BPFO`` (ball pass, outer race)    ``= N f_r (1 - r) / 2 = N * FTF``
    * ``BPFI`` (ball pass, inner race)    ``= N f_r (1 + r) / 2``
    * ``BSF``  (ball spin)                ``= f_r (1 - r^2) D / (2 d)``

    Two exact identities fall out and are asserted in the tests, because they
    catch a transposed ``d`` and ``D`` immediately: ``BPFO + BPFI = N f_r``
    exactly, and ``BPFO = N * FTF`` exactly. Measured for the defaults
    (1800 rpm, 9 elements, d = 8, D = 40, alpha = 0): ``ratio = 0.200000``,
    ``f_r = 30.000000``, ``FTF = 12.000000``, ``BPFO = 108.000000``,
    ``BPFI = 162.000000``, ``BSF = 72.000000`` Hz, with
    ``BPFO + BPFI - 9 f_r = 0.000e+00`` and ``BPFO - 9 FTF = 0.000e+00`` —
    exactly zero in float64, not merely small.

    Returns a dict with ``shaft_hz``, ``ftf_hz``, ``bpfo_hz``, ``bpfi_hz``,
    ``bsf_hz``, ``ratio`` (``d/D cos alpha``), and the inputs echoed back.
    Also ``bsf_hz_2x``: a rolling element normally strikes *both* races per
    spin, so a spall on the element itself is usually seen at ``2 * BSF``, and
    reporting only ``BSF`` is the classic way to miss it.

    These are the **no-slip kinematic** rates. Real bearings slip by roughly a
    percent, so an observed line within about 1 % of one of these is a match and
    an exact match is a coincidence; that tolerance is the caller's to apply.

    **Raises** ``ValueError``: non-real / string / bool scalars, ``rpm <= 0``,
    ``n_elements`` not an int >= 2, non-positive diameters, an
    ``element_diameter >= pitch_diameter`` (geometrically impossible — the
    rolling elements would not fit inside the pitch circle, and the usual cause
    is the two arguments being swapped, which otherwise returns a negative FTF
    and a plausible-looking BPFI), and ``|contact_angle_deg| >= 90``.
    """
    op = "bearing_defect_frequencies"
    r = _positive(rpm, "rpm")
    n = _count(n_elements, "n_elements", 2, 4096)
    d = _positive(element_diameter, "element_diameter")
    dp = _positive(pitch_diameter, "pitch_diameter")
    ang = _finite_scalar(contact_angle_deg, "contact_angle_deg")
    if abs(ang) >= 90.0:
        raise ValueError("%s: contact_angle_deg=%g must lie in (-90, 90); at 90 "
                         "degrees the load line is tangential and the rolling "
                         "kinematics below do not apply" % (op, ang))
    if d >= dp:
        raise ValueError("%s: element_diameter=%g must be smaller than "
                         "pitch_diameter=%g — %d elements of that size cannot "
                         "sit on that pitch circle. The usual cause is the two "
                         "arguments being swapped, which returns a negative cage "
                         "rate and a ball-pass rate that still looks plausible"
                         % (op, d, dp, n))
    fr = r / 60.0
    ratio = (d / dp) * np.cos(np.deg2rad(ang))
    ftf = 0.5 * fr * (1.0 - ratio)
    bpfo = n * ftf
    bpfi = 0.5 * n * fr * (1.0 + ratio)
    bsf = 0.5 * fr * (dp / d) * (1.0 - ratio * ratio)
    return {
        "shaft_hz": float(fr),
        "ftf_hz": float(ftf),
        "bpfo_hz": float(bpfo),
        "bpfi_hz": float(bpfi),
        "bsf_hz": float(bsf),
        "bsf_hz_2x": float(2.0 * bsf),
        "ratio": float(ratio),
        "rpm": float(r), "n_elements": int(n),
        "element_diameter": float(d), "pitch_diameter": float(dp),
        "contact_angle_deg": float(ang),
    }


def spectral_kurtosis(x, rate, win=None, hop=None, window="hann"):
    """Which frequency band is impulsive — i.e. where to demodulate.

    :func:`envelope_spectrum` needs a band, and picking it by eye from a
    spectrum picks the *loudest* band, which is usually a gear mesh or a line
    harmonic rather than the bearing. Spectral kurtosis picks the *most
    non-stationary* band instead: for each frequency bin it measures the
    fourth-order behaviour of that bin's STFT coefficient across frames.

    The normalisation is chosen so the two reference cases are exact:

    * stationary **complex circular Gaussian** noise gives ``SK = 0``,
    * a **pure tone** (constant magnitude in its bin) gives ``SK = -1``,
    * a repetitive **transient** gives ``SK > 0``, and the larger it is the more
      concentrated in time the band's content is.

    Measured over 8192 samples at 16 kHz at the default window (64, 509 interior
    frames): white Gaussian noise gives a mean SK of **-0.0444** over the
    interior bins, against the estimator's own standard deviation
    ``4/sqrt(509) = 0.1773``, so it is zero; and a 2 kHz tone gives **-1.0000**
    in its bin. Both reference cases land on their closed forms.

    **The answer is a band, and it depends on the window — measured, not
    asserted.** The frame has to be *shorter than the gap between transients*,
    or every frame contains one and the band looks perfectly stationary. On the
    ``mode="impulse"`` bearing signal (25.6 kHz, resonance 3000 Hz, impulses
    every 9.35 ms, ring time constant 1.06 ms):

    ======  ==========  =======  ==========  =============
    win     frame (ms)  max SK   at (Hz)     bin spacing
    ======  ==========  =======  ==========  =============
    16      0.62        29.58    6400        1600 Hz
    32      1.25        12.86    1600        800 Hz
    64      2.50         5.38    2000        400 Hz
    128     5.00         1.66    1600        200 Hz
    256    10.00        -0.13   12200        100 Hz
    ======  ==========  =======  ==========  =============

    The last row is the failure mode: at a 10 ms frame against a 9.35 ms impulse
    spacing, every frame holds exactly one impulse, the band is stationary by
    construction, and the operator reports a *negative* kurtosis at an unrelated
    frequency. Nothing raises. So ``window_seconds`` is returned, to be compared
    against the repetition period you expect, and sweeping ``win`` is part of
    using this operator rather than an optimisation.

    What survives the sweep is the *band*, not the bin. On the same signal with
    ``noise_sigma=0.05`` (the noiseless one is impulsive in every bin at once
    and its top six bins differ by 0.03, which is itself worth knowing), the six
    highest bins at ``win=64`` are 2000, 2400, 1600, 4000, 3600 and 1200 Hz —
    bracketing the true 3000 Hz resonance without any of them being it. And that
    is enough: feeding the band this operator returns straight into
    :func:`envelope_spectrum` recovers the defect rate exactly — measured
    **107.0000 Hz** from the 1600-2400 Hz band the operator chose by itself,
    with no knowledge of the resonance.

    **The band is returned, not left to the caller to assemble.** ``band_lo`` /
    ``band_hi`` are ``max_freq -+ bin_hz`` *clamped into the open interval*
    ``(0, rate/2)`` that :func:`envelope_spectrum` accepts, so
    ``envelope_spectrum(x, rate, sk["band_lo"], sk["band_hi"])`` is always a
    legal call. Assembling the band by hand is not: ``freqs`` runs up to and
    including Nyquist, so whenever the winning bin is the topmost interior one,
    ``max_freq + bin_hz`` lands exactly *on* Nyquist and ``envelope_spectrum``
    refuses it — correctly, since no such band exists in the recording. Measured
    on the ``mode="am"`` bearing signal (25600 Hz, 1 s, 3 kHz carrier, 107 Hz
    defect, ``m = 0.5``), whose kurtosis maximum is the top interior bin:

    ===========================  =====================  ==============================
    band handed to the consumer  value                  ``envelope_spectrum``
    ===========================  =====================  ==============================
    ``max_freq -+ bin_hz``       12000.0 - 12800.0 Hz   ``ValueError`` (12800 = Nyquist)
    ``band_lo`` / ``band_hi``    12000.0 - 12600.0 Hz   returns, ``peak_freq`` 107.0000
    ===========================  =====================  ==============================

    The clamp margin is **half a bin**: an edge cannot be placed more finely than
    ``bin_hz`` in the first place, and half a bin is the smallest offset that is
    still a resolvable distance from the boundary — no epsilon, no rate-dependent
    fudge. ``band_lo < band_hi`` always holds, because ``max_freq`` is by
    construction an interior bin and therefore at least one full bin away from
    both 0 and Nyquist.

    ``win`` defaults to the largest power of two that leaves at least 8 interior
    frames, clamped to [16, 64] — short, for the reason in the table — and the
    value used is returned. Fewer than 8 interior frames makes the fourth moment
    meaningless and is refused.

    DC and Nyquist bins are excluded from ``max_kurtosis`` / ``max_freq``: their
    STFT coefficients are real, not complex circular, so the -2 normalisation is
    the wrong one there and they read about -1 for noise. They are still present
    in ``kurtosis`` with the same formula, and ``real_bins`` names them.

    Returns a dict: ``freqs``, ``kurtosis``, ``max_kurtosis``, ``max_freq``,
    ``band_lo``, ``band_hi`` (the demodulation band, ready for
    :func:`envelope_spectrum`), ``n_frames``, ``win``, ``hop``, ``real_bins``,
    ``window_seconds``, ``bin_hz``, ``noise_sigma`` (the estimator's own standard
    deviation, ``4/sqrt(n_frames)`` — a peak below this is not a finding).

    **Raises** ``ValueError``: everything :func:`stft` refuses, plus a signal too
    short for 8 frames at the chosen window.
    """
    op = "spectral_kurtosis"
    fs = _rate(rate)
    arr = _as_signal(x, "x", op, min_len=32)
    if win is None:
        w_len = 16
        while w_len * 2 <= 64 and arr.size >= 16 * w_len:
            w_len *= 2
    else:
        w_len = _count(win, "win", 4, MAX_WINDOW)
    h = w_len // 4 if hop is None else _count(hop, "hop", 1, MAX_WINDOW)
    tr = stft(arr, fs, win=w_len, hop=h, window=window, scaling="none")
    # Only the frames wholly inside the original record. A frame straddling the
    # transform's zero pad is half empty, and a half-empty frame is the most
    # impulsive thing there is — including them puts a spurious positive
    # kurtosis in every bin. The size of the lie scales with the pad's share of
    # the frames; measured on pure white Gaussian noise (mean over interior
    # bins, then the largest single bin, with and without this mask):
    #
    #   n     win  hop  frames  pad     interior  with pad  max with pad
    #   8192   64   16    517   1.5 %    -0.0444   -0.0264       +0.1915
    #   2048  256   64     37  21.6 %    -0.0814   +0.1996       +1.7865
    #   1024  256  128     11  36.4 %    -0.2176   +0.2816       +4.0856
    #    512  256  128      7  57.1 %    -0.4913   +0.4324       +2.7730
    #
    # Row three is the one to look at: white noise, nothing in it at all, and
    # without the mask the operator reports a bin at SK = +4.09 — a strong
    # repetitive transient that does not exist. Nothing raises.
    z = tr["spectra"][:, tr["interior"]]
    n_frames = z.shape[1]
    if n_frames < 8:
        raise ValueError("%s: only %d frame(s) lie wholly inside the record at "
                         "win=%d hop=%d over %d samples (frames overlapping the "
                         "transform's zero pad are excluded — a half-empty frame "
                         "reads as a transient). A fourth moment over fewer than "
                         "8 frames is noise, not a measurement; shorten the "
                         "window or lengthen the record"
                         % (op, n_frames, w_len, h, arr.size))
    p = np.abs(z) ** 2
    m2 = p.mean(axis=1)
    m4 = (p * p).mean(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        sk = m4 / (m2 * m2) - 2.0
    sk = np.where(m2 > 0.0, sk, 0.0)
    real_bins = (0, int(z.shape[0] - 1)) if tr["nfft"] % 2 == 0 else (0,)
    interior = np.ones(z.shape[0], bool)
    for b in real_bins:
        interior[b] = False
    if interior.any():
        j = int(np.argmax(np.where(interior, sk, -np.inf)))
        mx, mf = float(sk[j]), float(tr["freqs"][j])
    else:
        mx, mf = float(sk.max()), float(tr["freqs"][int(np.argmax(sk))])
    # The band, assembled here rather than by the caller. `freqs` includes
    # Nyquist, so `max_freq + bin_hz` sits exactly on it whenever the winning bin
    # is the topmost interior one, and `envelope_spectrum` fail-closes on that
    # (rightly — there is no such band). Half a bin is the clamp margin: an edge
    # is not placeable more finely than one bin, so half of one is the smallest
    # resolvable step away from the boundary.
    df = float(fs) / float(tr["nfft"])
    margin = 0.5 * df
    band_lo = max(mf - df, margin)
    band_hi = min(mf + df, 0.5 * fs - margin)
    return {
        "freqs": tr["freqs"], "kurtosis": np.ascontiguousarray(sk),
        "max_kurtosis": mx, "max_freq": mf,
        "band_lo": float(band_lo), "band_hi": float(band_hi),
        "n_frames": int(n_frames), "win": int(w_len), "hop": int(h),
        "real_bins": real_bins,
        "window_seconds": float(w_len) / fs,
        "bin_hz": float(fs) / float(tr["nfft"]),
        "noise_sigma": 4.0 / np.sqrt(float(n_frames)),
    }


def cepstrum(x, rate, mode="real", floor_ratio=1e-12, min_quefrency=0.0):
    """The spectrum of the log spectrum — periodic structure *in frequency*.

    A harmonic family or a family of modulation sidebands is periodic along the
    frequency axis, so it collapses to a single line along the cepstrum's
    quefrency axis (in seconds). Two things this finds that a spectrum does not:
    an **echo** at delay ``tau`` (a rahmonic at ``q = tau``) and a **sideband
    family** spaced ``df`` apart (a rahmonic at ``q = 1/df``). The second is the
    bearing case — sidebands around a gear mesh spaced at the shaft rate.

    ``mode``:

    * ``"real"`` — ``irfft(log|X|)``, the standard real cepstrum. Discards phase,
      so it cannot be inverted; nothing here pretends otherwise.
    * ``"power"`` — ``irfft(log|X|**2) = 2 * real``, kept because the two
      conventions differ by exactly a factor of two and mixing them silently
      halves or doubles every amplitude a caller compares against a reference.

    ``log(0)`` is handled by flooring the magnitude at ``floor_ratio`` times its
    own maximum (default 1e-12, i.e. -240 dB) rather than letting ``-inf`` enter
    the inverse transform, where it would make the entire cepstrum NaN. The
    number of floored bins is returned as ``floored_bins`` — a large count means
    the signal is band-limited and the cepstrum is dominated by the flooring, not
    by the signal.

    ``min_quefrency`` (seconds) excludes the low-quefrency region from the peak
    search. This is not cosmetic. The first few bins carry the **spectral
    envelope** — the overall shape of the spectrum, which is large and has
    nothing to do with periodic structure — and they dominate. Measured on an AM
    tone with sidebands 50 Hz apart, the five largest cepstral values sit at
    0.000125, 0.00025, 0.000375, 0.000625 and 0.001 s, i.e. all of them are the
    envelope, and the default peak search returns 0.000125 s rather than the
    1/50 = 0.02 s a reader would expect. Excluding the envelope is the standard
    practice ("liftering") and is the caller's decision, so it is an argument
    with a visible default of 0.

    Returns a dict: ``quefrency`` (s), ``cepstrum``, ``rate``, ``mode``,
    ``floored_bins``, ``min_quefrency``, ``peak_quefrency``, ``peak_amplitude``,
    ``peak_rate_hz`` (``1/peak_quefrency`` — the sideband spacing or repetition
    rate the rahmonic corresponds to). The peak is taken over
    ``min_quefrency < q < n/(2*rate)``; the cepstrum is symmetric past that.

    Measured ground truths:

    * **Echo.** White noise at 8 kHz plus 0.6 times itself delayed by 200
      samples: ``peak_quefrency = 0.025000`` s, peak index exactly **200**, and
      ``floored_bins = 0``.
    * **A periodic family of lines.** A 50 Hz impulse train convolved with a
      random 64-tap FIR (so the spectrum is broadband with lines every 50 Hz):
      peak at ``0.020000`` s = **50.00 Hz** exactly, with
      ``min_quefrency=0.002``.
    * **What it looks like when the fundamental is not the largest.** The
      ``mode="impulse"`` bearing signal repeats every 1/107 s, and the largest
      rahmonic above 2 ms is at 0.037383 s — which is ``4/107``, the *fourth*
      rahmonic, not the first. A cepstrum reports a **family**, and reading only
      its maximum gives an answer that is off by an exact integer factor and
      looks entirely reasonable.
    * **Where it stops working.** An AM tone has three spectral lines and
      nothing else; every other bin is floored, the log spectrum is mostly the
      floor, and there is no 1/50 s rahmonic to find at all. Cepstral sideband
      analysis needs a *broadband* signal — a gear mesh, not a tone.

    ``mode="power"`` is exactly twice ``mode="real"`` (measured max difference
    0.000e+00).

    **Raises** ``ValueError``: everything :func:`_as_signal` refuses, an unknown
    ``mode``, ``floor_ratio`` outside ``(0, 1)``, a negative ``min_quefrency``, a
    ``min_quefrency`` at or past the half-length of the record (nothing would be
    left to search), an identically zero signal, and a signal shorter than 4
    samples.
    """
    op = "cepstrum"
    fs = _rate(rate)
    arr = _as_signal(x, "x", op, min_len=4)
    kind = _check_choice(mode, ("real", "power"), "mode", op)
    fr = _finite_scalar(floor_ratio, "floor_ratio")
    if not 0.0 < fr < 1.0:
        raise ValueError("%s: floor_ratio=%g must lie in (0, 1)" % (op, fr))
    spec = np.abs(np.fft.rfft(arr))
    mx = float(spec.max())
    if mx <= 0.0:
        raise ValueError("%s: the signal is identically zero — its log spectrum "
                         "is -inf everywhere and there is no cepstrum" % (op,))
    floor = mx * fr
    floored = int((spec < floor).sum())
    logmag = np.log(np.maximum(spec, floor))
    if kind == "power":
        logmag = 2.0 * logmag
    c = np.fft.irfft(logmag, n=arr.size)
    q = np.arange(arr.size, dtype=np.float64) / fs
    half = arr.size // 2
    mq = _nonneg(min_quefrency, "min_quefrency")
    lo = max(1, int(np.ceil(mq * fs)) if mq > 0.0 else 1)
    if lo >= half:
        raise ValueError("%s: min_quefrency=%g s is at or past the half-length "
                         "%g s of the record — nothing would be left to search "
                         "(the cepstrum is symmetric past the half-length)"
                         % (op, mq, half / fs))
    body = np.abs(c[lo:half])
    if body.size:
        j = int(np.argmax(body)) + lo
        pq, pa = float(q[j]), float(c[j])
    else:
        pq, pa = 0.0, 0.0
    return {
        "quefrency": q, "cepstrum": np.ascontiguousarray(c),
        "rate": fs, "mode": kind, "floored_bins": floored,
        "min_quefrency": mq,
        "peak_quefrency": pq, "peak_amplitude": pa,
        "peak_rate_hz": float(1.0 / pq) if pq > 0.0 else 0.0,
    }


# --------------------------------------------------------------------------- #
# 4. Order tracking                                                             #
# --------------------------------------------------------------------------- #
def _rpm_profile(rpm, n: int, op: str) -> np.ndarray:
    """A per-sample shaft rate in rpm, from a scalar or an array of length n."""
    if isinstance(rpm, (str, bytes, np.str_, np.bytes_)):
        raise ValueError("%s: rpm is a string (%r) — a shaft speed must be a "
                         "number or a per-sample array" % (op, rpm))
    if np.ndim(rpm) == 0:
        return np.full(n, _positive(rpm, "rpm"), np.float64)
    prof = _as_signal(rpm, "rpm", op, min_len=2)
    if prof.size != n:
        raise ValueError("%s: rpm has %d samples but the signal has %d — a speed "
                         "profile must be sampled on the same clock as the "
                         "signal, or be a single number" % (op, prof.size, n))
    if float(prof.min()) <= 0.0:
        raise ValueError("%s: rpm reaches %g at sample %d. Shaft angle is the "
                         "integral of speed, so a zero or negative rate makes "
                         "the angle axis non-monotonic and the resampling would "
                         "interpolate backwards through it without complaining"
                         % (op, float(prof.min()), int(np.argmin(prof))))
    return prof


def angular_resample(x, rate, rpm, samples_per_rev=64):
    """Resample a time record onto the shaft-angle axis (computed order tracking).

    Under a changing shaft speed, a component locked to the shaft has a moving
    frequency and smears across the spectrum, while a structural resonance stays
    put. Resample the record so the samples are equally spaced in **shaft angle**
    instead of in time and the situation reverses exactly: the order becomes a
    single line and the resonance smears.

    ``rpm`` is either a single number (constant speed — the transform is then a
    pure rescaling) or a per-sample array on the same clock as the signal. The
    cumulative revolution count is the trapezoidal integral of ``rpm/60``, and
    the signal is linearly interpolated onto a uniform grid in it.

    Returns a dict — an angle-domain record is **not** put into circulation as a
    plain signal, deliberately. Its samples are indexed by angle, not time, so
    handing it to any op that takes a ``rate`` would produce frequencies in Hz
    from an axis measured in revolutions: no exception, no NaN, just wrong
    numbers. (Same judgement, and the same reason, as ``motionmag.motion_magnify``
    not exposing a bare video adapter.) The dict carries ``signal``,
    ``angle_rev``, ``samples_per_rev``, ``revolutions`` (total),
    ``whole_revolutions``, ``rate`` (the original time-domain one, for
    provenance), ``mean_rpm``, ``max_order``.

    ``max_order`` is ``samples_per_rev / 2`` — the Nyquist of the *angle* axis.

    Measured: a pure order-3.5 component on a 600 -> 1800 rpm ramp, resampled at
    64 samples/rev over 78 whole revolutions, reads amplitude 0.999371 in a
    single bin of the order spectrum; the same component in the ordinary
    spectrum peaks at 0.070203 and is 66.5 Hz wide.

    **Raises** ``ValueError``: everything :func:`_as_signal` refuses, a
    non-positive or wrong-length ``rpm``, ``samples_per_rev`` outside
    ``[2, 65536]``, an output over :data:`MAX_ANGULAR_SAMPLES`, fewer than one
    complete revolution in the record, and — the aliasing refusal — a
    ``samples_per_rev`` whose implied Nyquist order needs content above the
    time-domain Nyquist. Asking for 64 samples/rev on a shaft turning at 30 Hz
    means representing 960 Hz, which a 100 Hz recording does not contain; the
    resampler would happily manufacture it from the interpolation.
    """
    op = "angular_resample"
    fs = _rate(rate)
    arr = _as_signal(x, "x", op, min_len=4)
    spr = _count(samples_per_rev, "samples_per_rev", 2, 65536)
    prof = _rpm_profile(rpm, arr.size, op)
    f_shaft = prof / 60.0
    f_max = float(f_shaft.max())
    need_hz = 0.5 * spr * f_max
    if need_hz > 0.5 * fs:
        raise ValueError(
            "%s: samples_per_rev=%d resolves orders up to %g, which at the "
            "fastest shaft rate in this record (%g rpm = %g Hz) means content at "
            "%g Hz — above the recording's own Nyquist %g Hz (rate=%g). That "
            "content is not in the data; interpolating onto this grid would "
            "manufacture it. The largest honest samples_per_rev here is %d"
            % (op, spr, 0.5 * spr, float(prof.max()), f_max, need_hz,
               0.5 * fs, fs, max(2, int(fs / f_max))))
    dt = 1.0 / fs
    rev = np.concatenate([[0.0], np.cumsum(0.5 * (f_shaft[1:] + f_shaft[:-1]) * dt)])
    total = float(rev[-1])
    if total < 1.0:
        raise ValueError("%s: the record covers %g revolution(s). Order analysis "
                         "needs at least one complete revolution — the order "
                         "resolution is 1/revolutions, so below one revolution "
                         "every order lands in the same bin"
                         % (op, total))
    n_out = int(np.floor(total * spr)) + 1
    if n_out > MAX_ANGULAR_SAMPLES:
        raise ValueError("%s: %g revolutions at %d samples/rev is %d samples, "
                         "over the %d cap (acoustics.MAX_ANGULAR_SAMPLES)"
                         % (op, total, spr, n_out, MAX_ANGULAR_SAMPLES))
    grid = np.arange(n_out, dtype=np.float64) / spr
    out = np.interp(grid, rev, arr)
    return {
        "signal": np.ascontiguousarray(out),
        "angle_rev": grid,
        "samples_per_rev": int(spr),
        "revolutions": total,
        "whole_revolutions": int(np.floor(total)),
        "rate": fs,
        "mean_rpm": float(prof.mean()),
        "max_order": 0.5 * spr,
    }


def order_spectrum(x, rate, rpm, samples_per_rev=64, revolutions=None,
                   max_order=None, n_peaks=5):
    """Amplitude against shaft order — the spectrum a run-up should be read in.

    :func:`angular_resample` followed by an rFFT over a **whole number of
    revolutions** (the record is cropped to that). Bin spacing is
    ``1 / whole_revolutions`` in orders.

    ``revolutions`` overrides how many whole revolutions to keep, and it matters
    more than it looks. An order ``o`` lands exactly on a bin only when
    ``o * revolutions`` is an integer; otherwise it straddles two and both read
    low. Measured on the run-up below, which happens to cover 79.994
    revolutions:

    ==============  ==========  =============  =============
    revolutions     resolution  amp at o=1.0   amp at o=3.5
    ==============  ==========  =============  =============
    79 (default)    0.012658    0.999967       **0.636961**
    78 (even)       0.012821    1.000009       0.999371
    ==============  ==========  =============  =============

    That 0.637 is the classic two-bin scallop loss, and nothing raises: the peak
    is at the right order and 36 % too small, with a second peak of almost equal
    height one bin away (measured 0.6370 at order 3.4937 and 0.6353 at 3.5063).
    Cropping to an **even** number of revolutions puts every half-integer order
    on a bin. The default is the largest whole number available; pass
    ``revolutions`` when the order you care about is fractional.

    Returns a dict: ``orders``, ``magnitude`` (single-sided, ``2/N``),
    ``peak_order``, ``peak_amplitude``, ``peak_orders`` / ``peak_amplitudes``,
    ``resolution_order``, ``whole_revolutions``, ``samples_per_rev``,
    ``mean_rpm``, ``max_order``.

    Measured, and this is the whole argument for the operator. A 4 s run-up from
    600 to 1800 rpm at 5 kHz carrying exactly two shaft-locked components
    (orders 1.0 and 3.5, unit amplitude) plus one fixed 400 Hz resonance, read
    with ``revolutions=78``:

    ==========================  =====================  ====================
    quantity                    ordinary spectrum      order spectrum
    ==========================  =====================  ====================
    order-3.5 peak amplitude    0.070203 (of true 1)   0.999371 (of true 1)
    its -3 dB width             66.50 Hz (= 3.33 ord)  0.00000 order
    400 Hz resonance amplitude  1.0000, one bin        0.0517, over 26.7 ord
    ==========================  =====================  ====================

    The ordinary spectrum recovers **7 %** of the shaft-locked component's
    amplitude, because the energy is spread over 3.3 orders' worth of bins; the
    order spectrum recovers **99.94 %** of it in a single bin whose -3 dB width
    is one bin. The 400 Hz resonance goes the other way — sharp in hertz,
    smeared across 26.7 orders after resampling. That **reversal** is the
    diagnostic, and it is why both spectra are worth computing: what stays sharp
    under angular resampling turns with the shaft, and what stays sharp under
    ordinary transformation does not.

    **Raises** ``ValueError``: everything :func:`angular_resample` refuses (in
    particular the aliasing refusal), a ``revolutions`` larger than the record
    actually contains, and a ``max_order`` above the angular Nyquist
    ``samples_per_rev/2``.
    """
    op = "order_spectrum"
    ang = angular_resample(x, rate, rpm, samples_per_rev=samples_per_rev)
    k = _count(n_peaks, "n_peaks", 1, 4096)
    spr = ang["samples_per_rev"]
    whole = ang["whole_revolutions"]
    if revolutions is not None:
        want = _count(revolutions, "revolutions", 1, 1 << 30)
        if want > whole:
            raise ValueError("%s: revolutions=%d requested but the record covers "
                             "only %g (%d whole). Padding to reach it would "
                             "invent shaft rotations that were never recorded"
                             % (op, want, ang["revolutions"], whole))
        whole = want
    n = whole * spr
    if n < 4:
        raise ValueError("%s: %d whole revolution(s) at %d samples/rev is %d "
                         "samples — too few to transform"
                         % (op, whole, spr, n))
    y = ang["signal"][:n]
    y = y - y.mean()
    mag = np.abs(np.fft.rfft(y)) * (2.0 / n)
    orders = np.arange(mag.size, dtype=np.float64) / float(whole)
    if max_order is not None:
        mo = _positive(max_order, "max_order")
        if mo > 0.5 * spr:
            raise ValueError("%s: max_order=%g is above the angular Nyquist %g "
                             "(samples_per_rev=%d). Raise samples_per_rev instead "
                             "— which angular_resample will then check against "
                             "the recording's own Nyquist"
                             % (op, mo, 0.5 * spr, spr))
        keep = orders <= mo
        orders, mag = orders[keep], mag[keep]
    body = mag.copy()
    if body.size:
        body[0] = 0.0
    idx = np.argsort(body)[::-1][:k]
    idx = idx[body[idx] > 0.0]
    med = float(np.median(body[1:])) if body.size > 1 else 0.0
    peak = float(body.max()) if body.size else 0.0
    return {
        "orders": orders, "magnitude": mag,
        "peak_order": float(orders[int(np.argmax(body))]) if body.size else 0.0,
        "peak_amplitude": peak,
        "peak_prominence": (peak / med) if med > 0.0 else float("inf"),
        "noise_floor": med,
        "peak_orders": orders[idx].copy(), "peak_amplitudes": body[idx].copy(),
        "resolution_order": 1.0 / float(whole),
        "whole_revolutions": whole, "samples_per_rev": spr,
        "mean_rpm": ang["mean_rpm"], "max_order": ang["max_order"],
    }


# --------------------------------------------------------------------------- #
# 5. Standard acoustic quantities                                               #
# --------------------------------------------------------------------------- #
def octave_bands(fraction=3, f_min=22.0, f_max=22050.0, base=10):
    """Fractional-octave band centres and edges, from the defining construction.

    The band system is a geometric progression through 1 kHz:
    ``f_c = 1000 * G**(x/b)`` for odd ``b`` and ``1000 * G**((2x+1)/(2b))`` for
    even ``b``, with edges at ``f_c * G**(-+1/(2b))``. ``base=10`` uses
    ``G = 10**(3/10)`` (the base-ten system, in which ten third-octaves span
    almost exactly a decade); ``base=2`` uses ``G = 2`` exactly. No published
    table of centre frequencies is transcribed — the *exact* centres are
    computed, which is why ``centers`` reads 1000.0, 1258.925, 1584.893 rather
    than the 1000, 1250, 1600 a published series would give.

    **The parity of ``fraction`` changes where 1 kHz sits, and this surprises
    people.** With an odd ``b`` (1/1, 1/3) there is a band *centred* on exactly
    1000.0 Hz. With an even ``b`` (1/2, 1/6, 1/12, 1/24) the offset in the
    exponent means there is **no 1 kHz band at all** — instead 1000.0 Hz is
    exactly a band *edge*, shared by two bands. Measured across
    ``fraction`` = 1, 2, 3, 6, 12, 24: a centre lands on 1000.0 for 1 and 3, and
    a lower edge lands on it for 2, 6, 12 and 24, in every case to within
    ``rtol=1e-12``. That is the defining construction, not an artefact, and it
    matters when a level is quoted "at 1 kHz": in an even system that number
    comes from one of two adjacent half-bands, not from a band on the tone.

    ``nominal`` is the exact centre rounded to three significant figures, for
    labelling only. It is a rounding, **not** the published nominal series, and
    it differs from it: measured, the 1/1-octave centres round to 31.6, 63.1,
    126.0, 251.0, 501.0, 1000.0, 2000.0, 3980.0, 7940.0, 15800.0, where the
    published series has 125 and 250 where this has 126 and 251. Do arithmetic
    with ``centers`` and supply your own labels if they have to match a report.

    Returns a dict: ``centers``, ``lower``, ``upper``, ``nominal``, ``fraction``,
    ``base``, ``ratio`` (``G**(1/b)``), ``bandwidth`` (``upper - lower``),
    ``index`` (the integer ``x``).

    Exact identities, asserted in the tests: ``upper/lower = G**(1/b)`` for every
    band, ``center = sqrt(lower*upper)`` (the centre is the geometric mean of its
    edges, by construction), and successive centres are in the ratio ``G**(1/b)``.
    Measured for ``fraction=3, base=10`` over 22 Hz - 22.05 kHz (30 bands): the
    band containing 1000 Hz has ``lower = 891.250938``, ``center = 1000.000000``,
    ``upper = 1122.018454``; ``upper/lower - G**(1/3) = 2.2e-16``;
    ``|center - sqrt(lower*upper)| <= 1.8e-12`` over all bands; and successive
    centre ratios deviate from ``G**(1/3)`` by at most 6.7e-16. With ``base=2``
    the octave centres come out exactly 31.25, 62.5, 125, 250, 500, 1000, 2000,
    4000, 8000, 16000 Hz.

    **Raises** ``ValueError``: ``fraction`` not an int in ``[1, 24]``, ``base``
    not 2 or 10, non-positive or non-finite ``f_min`` / ``f_max``,
    ``f_min >= f_max``, and a request for more than :data:`MAX_BANDS` bands.
    """
    op = "octave_bands"
    b = _count(fraction, "fraction", 1, 24)
    lo = _positive(f_min, "f_min")
    hi = _positive(f_max, "f_max")
    if lo >= hi:
        raise ValueError("%s: need f_min < f_max, got %g and %g" % (op, lo, hi))
    if isinstance(base, (bool, np.bool_)) or int(base) not in (2, 10):
        raise ValueError("%s: base must be 2 (octave ratio exactly 2) or 10 "
                         "(ratio 10**(3/10)), got %r" % (op, base))
    bs = int(base)
    g = 2.0 if bs == 2 else 10.0 ** 0.3
    step = g ** (1.0 / b)
    half = g ** (0.5 / b)
    # Solve for the integer index range whose *centres* lie in [f_min, f_max].
    if b % 2 == 1:
        def centre(i):
            return F_REF_HZ * g ** (i / float(b))
        x0 = int(np.floor(b * np.log(lo / F_REF_HZ) / np.log(g)))
        x1 = int(np.ceil(b * np.log(hi / F_REF_HZ) / np.log(g)))
    else:
        def centre(i):
            return F_REF_HZ * g ** ((2 * i + 1) / (2.0 * b))
        x0 = int(np.floor((2 * b * np.log(lo / F_REF_HZ) / np.log(g) - 1) / 2.0))
        x1 = int(np.ceil((2 * b * np.log(hi / F_REF_HZ) / np.log(g) - 1) / 2.0))
    idx = [i for i in range(x0 - 1, x1 + 2) if lo <= centre(i) <= hi]
    if len(idx) > MAX_BANDS:
        raise ValueError("%s: [%g, %g] Hz at 1/%d octave is %d bands, over the "
                         "%d cap (acoustics.MAX_BANDS)"
                         % (op, lo, hi, b, len(idx), MAX_BANDS))
    if not idx:
        raise ValueError("%s: no 1/%d-octave band centre lies in [%g, %g] Hz — "
                         "the range is narrower than one band"
                         % (op, b, lo, hi))
    ci = np.array(idx, np.int64)
    centers = np.array([centre(int(i)) for i in ci], np.float64)
    lower = centers / half
    upper = centers * half
    nominal = np.array([float("%.3g" % c) for c in centers], np.float64)
    return {
        "centers": centers, "lower": lower, "upper": upper, "nominal": nominal,
        "fraction": b, "base": bs, "ratio": float(step),
        "bandwidth": upper - lower, "index": ci,
    }


def octave_spectrum(x, rate, fraction=3, f_min=22.0, f_max=None, ref=1.0,
                    weighting="Z", floor_db=FLOOR_DB):
    """Band levels in dB, summed over fractional-octave bands by Parseval.

    Energy is accumulated from the single-sided periodogram into the bands
    :func:`octave_bands` defines, so the band powers sum to the signal's
    mean-square exactly (up to the bins outside the requested range). That
    identity is the test: measured on 16384 samples of white noise at 16 kHz
    over 22 Hz - 8 kHz at 1/3 octave, the band powers sum to **0.996367** of
    ``mean(x**2)`` while ``total_power`` (which counts every FFT bin) comes to
    **1.000000** of it. The 0.36 % difference is exactly the bins outside the
    requested range, and returning both numbers is what makes that visible
    instead of leaving a reader to wonder where the energy went.

    **The reference is explicit and there is no implicit 20 uPa.** ``ref`` is an
    amplitude in the same units as the signal, and the default 1.0 means "dB
    relative to one unit of whatever you passed in". This library never sees a
    microphone calibration, so a number labelled dB SPL would be a fabrication;
    pass ``ref=20e-6`` when the signal really is pascals and the result really is
    dB SPL.

    ``weighting`` applies :func:`apply_weighting` first (``"Z"`` = none).

    Returns a dict: ``centers``, ``nominal``, ``lower``, ``upper``, ``levels``
    (dB), ``powers`` (mean-square), ``total_level``, ``total_power``,
    ``clamped`` (bool mask of bands floored at ``floor_db``), ``ref``,
    ``weighting``, ``fraction``, ``resolution_hz``, ``narrow_bands`` (how many
    FFT bins landed in each band — a band with 0 or 1 is under-resolved and the
    level is not trustworthy).

    Measured exactness: a 1 kHz sine of amplitude 0.7 at 16 kHz over exactly
    1000 periods, ``ref=1.0``, gives the 1 kHz band level
    **-6.1083391564** dB against the closed form
    ``10*log10(0.7**2/2) = -6.1083391564`` dB — the difference is
    **0.000e+00**. 25 of the 26 bands are at the floor, and ``total_level``
    equals the band level to the digit shown, because there is nothing else in
    the record.

    **Raises** ``ValueError``: everything :func:`_as_signal` and
    :func:`octave_bands` refuse, ``ref <= 0`` (a dB with a zero or negative
    reference is not a number), an unknown ``weighting``, and an ``f_max`` above
    Nyquist.
    """
    op = "octave_spectrum"
    fs = _rate(rate)
    arr = _as_signal(x, "x", op, min_len=8)
    r = _positive(ref, "ref")
    kind = _check_choice(weighting, ("a", "c", "z"), "weighting", op).upper()
    fd = _finite_scalar(floor_db, "floor_db")
    nyq = 0.5 * fs
    hi = nyq * 0.999 if f_max is None else _positive(f_max, "f_max")
    if hi > nyq:
        raise ValueError("%s: f_max=%g Hz is above Nyquist %g Hz (rate=%g) — "
                         "there are no bands up there to fill"
                         % (op, hi, nyq, fs))
    if kind != "Z":
        arr = apply_weighting(arr, fs, kind)
    bands = octave_bands(fraction=fraction, f_min=f_min, f_max=hi)
    n = arr.size
    spec = np.fft.rfft(arr)
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    # single-sided mean-square contribution of each bin (Parseval-exact)
    ms = (np.abs(spec) / n) ** 2
    ms[1:] *= 2.0
    if n % 2 == 0:
        ms[-1] /= 2.0                       # Nyquist bin is not two-sided
    idx = np.searchsorted(bands["lower"], freqs, side="right") - 1
    powers = np.zeros(bands["centers"].size, np.float64)
    counts = np.zeros(bands["centers"].size, np.int64)
    valid = (idx >= 0) & (idx < powers.size)
    valid &= freqs <= np.where(valid, bands["upper"][np.clip(idx, 0, powers.size - 1)],
                               -1.0)
    np.add.at(powers, idx[valid], ms[valid])
    np.add.at(counts, idx[valid], 1)
    levels, clamped = _db_power(powers, r * r, fd)
    total = float(ms.sum())
    tl, tc = _db_power(total, r * r, fd)
    return {
        "centers": bands["centers"], "nominal": bands["nominal"],
        "lower": bands["lower"], "upper": bands["upper"],
        "levels": levels, "powers": powers, "clamped": clamped,
        "narrow_bands": counts,
        "total_level": tl, "total_power": total, "total_clamped": tc,
        "ref": r, "weighting": kind, "fraction": bands["fraction"],
        "resolution_hz": float(fs / n),
    }


def _weighting_ratio(f: np.ndarray, kind: str) -> np.ndarray:
    """The un-normalised A / C weighting magnitude response at |f|."""
    f2 = f.astype(np.float64) ** 2
    f1s, f2s, f3s, f4s = _W_F1 ** 2, _W_F2 ** 2, _W_F3 ** 2, _W_F4 ** 2
    if kind == "A":
        num = f4s * f2 * f2
        den = (f2 + f1s) * np.sqrt((f2 + f2s) * (f2 + f3s)) * (f2 + f4s)
    else:                                    # "C"
        num = f4s * f2
        den = (f2 + f1s) * (f2 + f4s)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = num / den
    return np.where(np.isfinite(r), r, 0.0)


def weighting_response(freqs, kind="A", floor_db=FLOOR_DB):
    """The A / C / Z frequency-weighting curve, in dB, at the given frequencies.

    Computed from the four pole frequencies that *define* the networks and
    normalised so that the response at 1 kHz is exactly 0 dB **by construction**
    — the curve is divided by its own value at 1 kHz rather than having a
    published offset constant added to it. That is why the tests can assert
    equality at 1 kHz to 0.0 rather than to a tolerance, and why no standard's
    table of attenuations appears anywhere in this repository.

    The response depends on ``f`` only through ``f**2``, so it is an even
    function and negative frequencies are evaluated at ``|f|`` — that is the
    definition, not a repair. ``f = 0`` has zero response (both curves have a
    zero at DC) and is reported as ``floor_db`` rather than ``-inf``.

    Measured (computed, then printed — these are outputs, not transcriptions):

    ========  =========  =========
    f (Hz)    A (dB)     C (dB)
    ========  =========  =========
    10        -70.4304   -14.3300
    31.5      -39.5250    -3.0305
    100       -19.1428    -0.2996
    1000        0.0000     0.0000
    4000        0.9633    -0.8260
    10000      -2.4918    -4.4055
    20000      -9.3469   -11.2786
    ========  =========  =========

    ``A(1000)`` and ``C(1000)`` are exactly ``0.0`` — the Python float, not a
    rounding — because of the construction. The low-frequency asymptote is a
    closed form and is asserted in the tests: ``A`` falls at exactly
    80 dB/decade as ``f -> 0`` (``f**4`` over three constants) and ``C`` at
    exactly 40 dB/decade (``f**2``). Measured between 0.001 and 0.01 Hz with the
    floor lowered out of the way: **79.999998** and **39.999998** dB/decade.

    That last caveat is real and is why the floor is an argument: with the
    default ``floor_db = -200`` the A curve reaches the floor below about
    0.35 Hz (unfloored, ``A(0.1) = -228.55`` dB), so the asymptote measured
    against the default floor comes out as 0.0 dB/decade between 0.01 and
    0.1 Hz — a clamp, correctly reported, that would look like a bug if the
    floor were not visible.

    Returns a float64 array the same shape as *freqs*.

    **Raises** ``ValueError``: a non-1-D / non-finite / complex / masked
    ``freqs``, an unknown ``kind``.
    """
    op = "weighting_response"
    kind_s = _check_choice(kind, ("a", "c", "z"), "kind", op).upper()
    f = _as_signal(freqs, "freqs", op, min_len=1)
    if kind_s == "Z":
        return np.zeros_like(f)
    fd = _finite_scalar(floor_db, "floor_db")
    r = _weighting_ratio(np.abs(f), kind_s)
    r0 = float(_weighting_ratio(np.array([F_REF_HZ]), kind_s)[0])
    lvl, _ = _db_power(r * r, r0 * r0, fd)
    return np.ascontiguousarray(lvl)


def apply_weighting(x, rate, kind="A"):
    """Apply an A / C / Z frequency weighting to a signal, zero-phase.

    The weighting is applied as a real, even gain in the frequency domain, so it
    introduces no phase distortion and no group delay — the result is aligned
    sample-for-sample with the input, which a recursive filter implementation
    would not be.

    Measured: a 1 kHz sine at 16 kHz (16000 samples, exactly 1000 periods) is
    returned **unchanged** by both A and C weighting — max absolute difference
    1.078e-13 for A and 1.225e-13 for C — because both curves are exactly 0 dB
    at 1 kHz by construction. A 100 Hz sine of amplitude 1.0 comes back with
    amplitude **0.110373** under A weighting, against the closed form
    ``10**(-19.1428/20) = 0.110373``.

    ``kind="Z"`` returns a copy, unchanged.

    **Raises** ``ValueError``: everything :func:`_as_signal` refuses, an unknown
    ``kind``, ``rate <= 0``.
    """
    op = "apply_weighting"
    fs = _rate(rate)
    arr = _as_signal(x, "x", op, min_len=2)
    kind_s = _check_choice(kind, ("a", "c", "z"), "kind", op).upper()
    if kind_s == "Z":
        return arr.copy()
    freqs = np.fft.rfftfreq(arr.size, d=1.0 / fs)
    r = _weighting_ratio(freqs, kind_s)
    r0 = float(_weighting_ratio(np.array([F_REF_HZ]), kind_s)[0])
    gain = r / r0
    return np.ascontiguousarray(np.fft.irfft(np.fft.rfft(arr) * gain, n=arr.size))


def equivalent_level(x, rate, weighting="A", ref=1.0, floor_db=FLOOR_DB):
    """The energy-equivalent level of a record, in dB relative to ``ref``.

    ``L_eq = 10 log10(mean(x_w**2) / ref**2)`` where ``x_w`` is the signal after
    the chosen weighting. Returns a plain float.

    **The reference is yours to supply.** The default ``ref=1.0`` means dB
    relative to one unit of the signal's own units; it is not dB SPL, because
    this library never sees your calibration. Pass ``ref=20e-6`` for pascals.

    Measured: a 1 kHz sine of amplitude 1.0 at 16 kHz over exactly 1000 periods
    gives ``L_eq = -3.010300`` dB with Z weighting, against the closed form
    ``10*log10(1/2) = -3.010300`` (difference 2.2e-15 dB), and the **same** value
    under A weighting (difference 8.9e-16 dB), because A is 0 dB at 1 kHz.
    Doubling the amplitude adds 6.020600 dB. Silence returns -200.0.

    Silence returns ``floor_db`` (default -200) rather than ``-inf``; an ``-inf``
    in a list of levels destroys every average taken over it afterwards.

    **Raises** ``ValueError``: everything :func:`_as_signal` refuses, an unknown
    ``weighting``, ``ref <= 0`` (a decibel needs a positive reference; a zero
    reference makes every level ``+inf`` and a negative one makes the ratio
    negative), ``rate <= 0``.
    """
    op = "equivalent_level"
    fs = _rate(rate)
    arr = _as_signal(x, "x", op, min_len=1)
    r = _positive(ref, "ref")
    kind = _check_choice(weighting, ("a", "c", "z"), "weighting", op).upper()
    fd = _finite_scalar(floor_db, "floor_db")
    y = arr if kind == "Z" else apply_weighting(arr, fs, kind)
    lvl, _ = _db_power(float(np.mean(y * y)), r * r, fd)
    return float(lvl)


def percentile_level(x, rate, percentiles=(10.0, 50.0, 90.0), weighting="A",
                     ref=1.0, window_s=0.125, floor_db=FLOOR_DB):
    """Statistical levels: ``L_N`` is the level exceeded ``N`` % of the time.

    The record is cut into non-overlapping blocks of ``window_s`` seconds, each
    block's equivalent level is computed, and ``L_N`` is the ``(100-N)``-th
    percentile of those levels. Non-overlapping rectangular blocks are used
    rather than an exponential time weighting because the block length is then
    exactly what the caller asked for and the statistic is exactly a percentile
    of the returned ``levels`` array — an exponential average would make the
    effective averaging time a function of the signal.

    Returns a dict with one key per requested percentile (``"L10"``, ``"L50"``,
    ``"L90"``, formatted with ``%g``), plus ``levels`` (the per-block levels),
    ``times`` (block start times, s), ``n_blocks``, ``block_samples``,
    ``leq`` (the energy-equivalent level of the whole record), ``ref``,
    ``weighting``.

    Note that ``L50`` is the *median* level and ``leq`` is the *energy* level;
    they are different numbers whenever the signal is not stationary, and the
    gap between them is itself the usual measure of how fluctuating a record is.

    Measured on a two-level test signal (1 s at 16 kHz, first half a 1 kHz sine
    of amplitude 1.0, second half the same at 0.1, Z-weighted, 0.125 s blocks,
    8 blocks): ``L10 = -3.010300`` and ``L90 = -23.010300`` dB — exactly the two
    constituent levels, **20.000000** dB apart, as they must be for a 50/50
    split. ``L50 = -13.010300`` is the interpolated midpoint of the two clusters
    and ``leq = -5.977386``, which is 17 dB above ``L90``: the energy level sits
    near the loud half while the median sits between them. On a
    constant-amplitude signal all three percentiles and ``leq`` agree to
    3.6e-15 dB.

    **Raises** ``ValueError``: everything :func:`_as_signal` refuses, a
    percentile outside ``[0, 100]``, a non-positive ``window_s``, a ``window_s``
    longer than the record (which would give one block and make every percentile
    the same number while still looking like a statistic), ``ref <= 0``.
    """
    op = "percentile_level"
    fs = _rate(rate)
    arr = _as_signal(x, "x", op, min_len=2)
    r = _positive(ref, "ref")
    kind = _check_choice(weighting, ("a", "c", "z"), "weighting", op).upper()
    fd = _finite_scalar(floor_db, "floor_db")
    ws = _positive(window_s, "window_s")
    pcs = np.atleast_1d(np.asarray(
        [_finite_scalar(p, "percentiles[%d]" % i)
         for i, p in enumerate(np.atleast_1d(percentiles))], np.float64))
    if pcs.size == 0:
        raise ValueError("%s: percentiles is empty" % (op,))
    if np.any(pcs < 0.0) or np.any(pcs > 100.0):
        raise ValueError("%s: percentiles must lie in [0, 100], got %r"
                         % (op, pcs.tolist()))
    blk = int(round(ws * fs))
    if blk < 1:
        raise ValueError("%s: window_s=%g at rate=%g Hz is %d sample(s)"
                         % (op, ws, fs, blk))
    n_blocks = arr.size // blk
    if n_blocks < 2:
        raise ValueError("%s: window_s=%g s gives %d whole block(s) over a %g s "
                         "record. A percentile over one block is that block's "
                         "level repeated — it would look like a statistic and "
                         "carry no information. Shorten window_s or lengthen the "
                         "record" % (op, ws, n_blocks, arr.size / fs))
    y = arr if kind == "Z" else apply_weighting(arr, fs, kind)
    trimmed = y[:n_blocks * blk].reshape(n_blocks, blk)
    power = (trimmed * trimmed).mean(axis=1)
    levels, _ = _db_power(power, r * r, fd)
    out = {}
    for p in pcs:
        out["L%g" % p] = float(np.percentile(levels, 100.0 - p))
    leq, _ = _db_power(float(np.mean(y * y)), r * r, fd)
    out.update({
        "levels": levels,
        "times": np.arange(n_blocks, dtype=np.float64) * blk / fs,
        "n_blocks": int(n_blocks), "block_samples": int(blk),
        "leq": float(leq), "ref": r, "weighting": kind,
        "percentiles": pcs,
    })
    return out


# --------------------------------------------------------------------------- #
# 6. Two-channel estimators                                                     #
# --------------------------------------------------------------------------- #
def _welch_pair(x, y, rate, win, hop, window, op):
    """Welch-averaged auto and cross spectra of two equal-length signals."""
    fs = _rate(rate)
    a = _as_signal(x, "x", op, min_len=8)
    b = _as_signal(y, "y", op, min_len=8)
    if a.size != b.size:
        raise ValueError("%s: x has %d samples and y has %d. Two-channel "
                         "estimators compare the channels sample for sample; "
                         "padding or truncating one of them silently would "
                         "invent a time offset" % (op, a.size, b.size))
    if win is None:
        w_len = 16
        while w_len * 2 <= 1024 and a.size >= 8 * w_len:
            w_len *= 2
    else:
        w_len = _count(win, "win", 4, MAX_WINDOW)
    h = w_len // 2 if hop is None else _count(hop, "hop", 1, MAX_WINDOW)
    if w_len > a.size:
        raise ValueError("%s: win=%d is longer than the %d-sample record"
                         % (op, w_len, a.size))
    starts = np.arange(0, a.size - w_len + 1, h, dtype=np.int64)
    if starts.size < 2:
        raise ValueError(
            "%s: win=%d hop=%d over %d samples gives %d frame(s). With a single "
            "frame the coherence is identically 1.0 at every frequency no matter "
            "what the two channels contain — a perfect-looking result that means "
            "nothing. At least 2 frames are required, and 8 or more before the "
            "number is worth quoting" % (op, w_len, h, a.size, starts.size))
    n_freqs = w_len // 2 + 1
    if starts.size * n_freqs > MAX_STFT_ELEMENTS:
        raise ValueError("%s: %d frames x %d bins is over the %d cap "
                         "(acoustics.MAX_STFT_ELEMENTS)"
                         % (op, starts.size, n_freqs, MAX_STFT_ELEMENTS))
    w = _window_values(window, w_len, op)
    fa = np.lib.stride_tricks.sliding_window_view(a, w_len)[starts] * w
    fb = np.lib.stride_tricks.sliding_window_view(b, w_len)[starts] * w
    xa = np.fft.rfft(fa, axis=1)
    xb = np.fft.rfft(fb, axis=1)
    pxx = np.mean(np.abs(xa) ** 2, axis=0)
    pyy = np.mean(np.abs(xb) ** 2, axis=0)
    pxy = np.mean(np.conj(xa) * xb, axis=0)
    freqs = np.fft.rfftfreq(w_len, d=1.0 / fs)
    return freqs, pxx, pyy, pxy, int(starts.size), w_len, h, fs


def coherence(x, y, rate, win=None, hop=None, window="hann"):
    """Ordinary coherence: how much of ``y`` is linearly explained by ``x``.

    ``gamma**2(f) = |Pxy|**2 / (Pxx * Pyy)``, Welch-averaged. It is bounded in
    ``[0, 1]``, and it is the number that says whether a transfer function is
    worth reading at a given frequency.

    **A single frame makes it identically 1.0** — the Cauchy-Schwarz inequality
    is an equality without averaging — so an unaveraged coherence is a perfect
    score that carries no information at all. That case is refused, not returned.

    ``win`` defaults to the largest power of two leaving at least 8 frames,
    capped at 1024; the value used is returned.

    Returns a dict: ``freqs``, ``coherence``, ``n_frames``, ``win``, ``hop``,
    ``rate``, ``mean_coherence``, ``bias`` (the coherence a *pair of independent
    noise records* would show with this many frames, ``1/n_frames`` — anything
    at or below this is indistinguishable from nothing).

    Measured at 16 kHz over 16384 samples, win = 1024, 31 frames:

    =======================================  ==============  ========
    case                                     mean coherence  min
    =======================================  ==============  ========
    y = 2.5 * x (noiseless)                  1.000000        1.0000
    y = 0.8 * x delayed 37 samples           0.983003        0.9661
    y = 2.5 x + independent noise, 0 dB SNR  0.509143        0.2219
    y, x independent noise                   0.035640        0.0001
    =======================================  ==============  ========

    Row three against its closed form: for output noise the expected coherence
    is ``SNR/(1+SNR)`` = 0.5000 at 0 dB, measured 0.5091. Row four against the
    bias floor ``1/n_frames = 1/31 = 0.0323``, measured 0.0356 — which is why
    ``bias`` is returned: **an uncorrelated pair does not read zero**, and
    reading 0.03 as "a little bit of coupling" is the mistake this number
    prevents. Row two shows the other honest limit: a pure delay is a perfectly
    linear system and still reads 0.983, not 1, because a delay of 37 samples
    moves signal across the frame boundaries the estimator averages over.

    **Raises** ``ValueError``: everything :func:`_as_signal` refuses on either
    channel, unequal channel lengths, fewer than 2 frames, ``win`` longer than
    the record, an unknown window.
    """
    op = "coherence"
    freqs, pxx, pyy, pxy, nf, w_len, h, fs = _welch_pair(
        x, y, rate, win, hop, window, op)
    den = pxx * pyy
    with np.errstate(divide="ignore", invalid="ignore"):
        g2 = np.abs(pxy) ** 2 / den
    g2 = np.where(den > 0.0, g2, 0.0)
    g2 = np.clip(g2, 0.0, 1.0)               # round-off can exceed 1 by ~1e-16
    return {
        "freqs": freqs, "coherence": np.ascontiguousarray(g2),
        "n_frames": nf, "win": w_len, "hop": h, "rate": fs,
        "mean_coherence": float(g2.mean()),
        "bias": 1.0 / nf,
    }


def transfer_function(x, y, rate, win=None, hop=None, window="hann",
                      estimator="h1", ref=1.0, floor_db=FLOOR_DB):
    """Estimate ``H(f)`` with ``x`` in and ``y`` out, with its coherence.

    ``estimator``:

    * ``"h1"`` — ``Pxy / Pxx``. Unbiased when the noise is on the **output**.
      The usual default and the right one for a driven test.
    * ``"h2"`` — ``Pyy / conj(Pxy)``. Unbiased when the noise is on the
      **input**. It over-estimates the magnitude wherever H1 under-estimates it,
      so the two together bracket the truth, and ``|H1/H2| = gamma**2`` exactly —
      an identity worth checking rather than a coincidence.

    Returns a dict: ``freqs``, ``response`` (complex), ``magnitude``,
    ``magnitude_db`` (relative to ``ref``), ``phase_rad``, ``coherence``,
    ``estimator``, ``n_frames``, ``win``, ``hop``, ``rate``.

    Measured at 16 kHz over 16384 samples, win = 1024, 31 frames, white input:

    * ``y = 2.5 * x``: ``mean |H| = 2.5000000000``, max deviation from 2.5 over
      all bins **1.78e-15**, mean ``|phase|`` 2.7e-17, mean coherence
      1.0000000000.
    * ``y = 0.8 * x[n-37]``: the phase is a straight line in frequency of slope
      ``-2 pi * 37 / 16000`` s. A least-squares fit to the unwrapped phase over
      200-7000 Hz gives a group delay of **37.000004 samples** against a true 37
      (error 4.3e-06 samples), and ``mean |H| = 0.792220`` over the same bins
      against a true 0.8 (max deviation 0.050).
    * ``y = 2.5 * x + n`` with output noise at 0 dB SNR: H1 gives
      ``mean |H| = 2.523390`` — 0.94 % from the truth — while H2 gives
      **5.043020**, a factor of 2.0 too large, exactly as the theory predicts
      when the noise sits on the output. And ``|H1/H2|`` equals the coherence
      pointwise to **5.6e-16** (both mean 0.509143), which is the identity worth
      knowing: the ratio of the two estimators *is* the coherence.

    That third row is why the coherence is returned with the response. The H2
    number is off by 100 % and there is nothing about 5.04 that looks wrong.

    **Raises** ``ValueError``: everything :func:`coherence` refuses, plus an
    unknown ``estimator`` and ``ref <= 0``.
    """
    op = "transfer_function"
    est = _check_choice(estimator, ("h1", "h2"), "estimator", op)
    r = _positive(ref, "ref")
    fd = _finite_scalar(floor_db, "floor_db")
    freqs, pxx, pyy, pxy, nf, w_len, h, fs = _welch_pair(
        x, y, rate, win, hop, window, op)
    with np.errstate(divide="ignore", invalid="ignore"):
        if est == "h1":
            hf = np.where(pxx > 0.0, pxy / np.where(pxx > 0.0, pxx, 1.0), 0.0)
        else:
            cj = np.conj(pxy)
            hf = np.where(np.abs(cj) > 0.0, pyy / np.where(np.abs(cj) > 0.0, cj, 1.0),
                          0.0)
        den = pxx * pyy
        g2 = np.where(den > 0.0, np.abs(pxy) ** 2 / np.where(den > 0.0, den, 1.0), 0.0)
    mag = np.abs(hf)
    lvl, _ = _db_power(mag * mag, r * r, fd)
    return {
        "freqs": freqs, "response": np.ascontiguousarray(hf),
        "magnitude": np.ascontiguousarray(mag),
        "magnitude_db": lvl,
        "phase_rad": np.angle(hf),
        "coherence": np.clip(g2, 0.0, 1.0),
        "estimator": est, "n_frames": nf, "win": w_len, "hop": h,
        "rate": fs, "ref": r,
    }
