"""dsp.py — 1-D signal / acoustic / vibration processing (beyond images).

HALCON is 2-D/3-D imaging only; Fullseye also handles **1-D signals** — audio,
acoustic emission, vibration — for NDT, predictive maintenance and audio anomaly
detection. A genuine differentiator: acquire a waveform, run the same
design→measure→decide→signal-the-line loop the image side uses.

Core is numpy + scipy (already required). WAV I/O uses the stdlib ``wave`` module
(native, no deps); other audio formats come through the optional ``soundfile``
extra. Signals are float64 in ``[-1, 1]`` and must be **finite** — a NaN / Inf
sample is refused with ``ValueError`` (fail-closed, as in volops / complexops /
specops) instead of quietly turning every downstream feature into NaN.

    import fullseye
    x, rate = fullseye.read_wav("knock.wav")
    f, mag = fullseye.spectrum(x, rate)          # where is the energy?
    feats = fullseye.signal_features(x, rate)    # rms / zcr / centroid / peak_freq …
    ok = feats["peak_freq"] < 4000               # a simple acoustic verdict
"""
from __future__ import annotations

import wave

import numpy as np

__all__ = [
    "read_wav", "write_wav", "read_audio",
    "spectrum", "spectrogram", "bandpass", "lowpass", "highpass",
    "envelope", "rms", "zero_crossing_rate", "find_peaks", "resample",
    "signal_features",
]


def _require_finite(x, name: str = "signal") -> np.ndarray:
    """Coerce to a float64 array and reject any NaN / Inf.

    One poisoned sample spreads across the whole spectrum through the FFT, so the
    1-D layer refuses it up front rather than emitting NaN/Inf features that look
    like measurements. Empty signals are allowed (they are the documented
    zero-feature case)."""
    a = np.asarray(x, np.float64)
    if a.size and not np.isfinite(a).all():
        n = int((~np.isfinite(a)).sum())
        raise ValueError("%s has %d non-finite sample(s) (NaN/Inf) — refusing" % (name, n))
    return a


# --------------------------------------------------------------------------- #
# I/O
# --------------------------------------------------------------------------- #
def read_wav(path):
    """Read a WAV file (stdlib) -> ``(x float64 [-1,1], rate)``. Multi-channel is
    averaged to mono. Handles 8/16/32-bit PCM."""
    with wave.open(str(path), "rb") as w:
        rate = w.getframerate()
        n = w.getnframes()
        ch = w.getnchannels()
        width = w.getsampwidth()
        raw = w.readframes(n)
    if width == 1:                                   # 8-bit PCM is unsigned
        a = (np.frombuffer(raw, np.uint8).astype(np.float64) - 128.0) / 128.0
    elif width == 2:
        a = np.frombuffer(raw, np.int16).astype(np.float64) / 32768.0
    elif width == 4:
        a = np.frombuffer(raw, np.int32).astype(np.float64) / 2147483648.0
    else:
        raise ValueError("unsupported WAV sample width %d bytes" % width)
    if ch > 1:
        a = a.reshape(-1, ch).mean(axis=1)
    return a, rate


def write_wav(path, x, rate=44100):
    """Write a float ``[-1,1]`` mono signal to a 16-bit PCM WAV (stdlib).
    Non-finite samples raise (they would become garbage PCM)."""
    a = np.clip(_require_finite(x), -1.0, 1.0)
    pcm = np.round(a * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(rate))
        w.writeframes(pcm.tobytes())


def read_audio(path):
    """Read any audio format -> ``(x, rate)``. Uses ``soundfile`` if available
    (mp3/flac/ogg/…), else falls back to the stdlib WAV reader."""
    try:
        import soundfile as sf
        x, rate = sf.read(str(path), always_2d=False)
        x = np.asarray(x, np.float64)
        if x.ndim > 1:
            x = x.mean(axis=1)
        return x, rate
    except Exception:
        return read_wav(path)


# --------------------------------------------------------------------------- #
# spectral
# --------------------------------------------------------------------------- #
def spectrum(x, rate=1.0):
    """Raw one-sided magnitude spectrum -> ``(freqs, magnitude)`` (``np.fft.rfft``).

    **Scaling convention — read this before comparing any number.** *One-sided*
    describes the frequency axis, not the amplitude axis. ``rfft`` keeps only the
    non-negative frequencies, so ``freqs`` runs from 0 to ``rate/2`` in
    ``len(x)//2 + 1`` bins — but ``magnitude`` is the **unnormalised**
    ``|rfft(x)|``. It is *not* an amplitude and it grows with ``len(x)``: the same
    tone recorded twice as long comes back twice as tall. Nothing here divides by
    ``N``; the caller does, and the exact factor depends on the bin::

        freqs, mag = spectrum(x, rate)
        amp = mag * (2.0 / len(x))       # one-sided amplitude, bins 1 .. N/2-1
        amp[0] /= 2.0                    # DC has no mirror twin -> no factor 2
        if len(x) % 2 == 0:
            amp[-1] /= 2.0               # nor does the Nyquist bin of an even N

    The factor is ``2/N`` and not ``1/N`` because a real sinusoid of amplitude
    ``A`` splits its energy over a positive and a negative frequency; ``rfft``
    discards the negative half, so the surviving bin holds ``A*N/2``. DC and (for
    even ``N``) Nyquist are their own mirror image and are *not* doubled —
    applying ``2/N`` to them reports twice the true level.

    Measured, so the convention can be checked rather than assumed. A unit sine
    at a bin centre (``rate = 25600`` Hz, ``N = 25600``, 3000 Hz, amplitude
    exactly 1.0): the returned ``mag`` at 3000 Hz is ``12799.999999999998``
    (= ``N/2``), and ``mag * 2/N`` is ``0.9999999999999999``. A constant signal
    of value 1.0 with ``N = 1024``: ``mag[0] = 1024.0``, so ``mag[0] * 1/N`` is
    exactly ``1.0`` while ``mag[0] * 2/N`` would claim ``2.0``. Likewise
    ``cos(pi n)`` (amplitude 1.0 at Nyquist, ``N = 1024``): ``mag[-1] = 1024.0``,
    ``* 1/N`` = ``1.0``, ``* 2/N`` = ``2.0``.

    Everything scale-*invariant* — where the peak is, the spectral centroid, the
    bandwidth, a ratio between two bins — is unaffected by the convention, which
    is why :func:`signal_features` can build on this directly. Everything
    absolute (an amplitude in the signal's own units, a dB level) needs the
    division above. :func:`acoustics.envelope_spectrum` and
    :func:`acoustics.order_spectrum` already return calibrated one-sided
    amplitudes (they apply their own ``2/N`` internally) — do **not** apply the
    factor twice when comparing their output with this one.
    """
    x = _require_finite(x)
    mag = np.abs(np.fft.rfft(x))
    freqs = np.fft.rfftfreq(len(x), d=1.0 / float(rate))
    return freqs, mag


def spectrogram(x, rate=1.0, win=256, hop=None):
    """STFT magnitude spectrogram -> ``(freqs, times, S)`` with ``S`` shape
    ``(n_freqs, n_frames)``. Hann-windowed; *hop* defaults to ``win//2``.

    **Same raw convention as :func:`spectrum`, but a different divisor.** Each
    column is the unnormalised ``|rfft(frame * hann(win))|``, so it is not an
    amplitude either — and dividing by ``2/win`` is *wrong* here, because the
    Hann window has already thrown away part of the signal. The correct one-sided
    amplitude conversion divides by the window's coherent gain::

        w = np.hanning(win)
        amp = S * (2.0 / w.sum())        # bins 1 .. win/2-1; DC / Nyquist: 1/w.sum()

    Measured on a unit sine at a bin centre (``rate = 16000`` Hz, 1000 Hz,
    amplitude exactly 1.0, ``win = 256``): the raw column peak is
    ``63.7497786196906``; ``* 2/win`` gives ``0.49804514546633283`` (too small by
    exactly the Hann coherent gain ``sum(w)/win = 0.498046875``), while
    ``* 2/sum(w)`` gives ``0.9999965273676957``. Only the second one is the
    amplitude that was actually in the signal.

    Peak *positions*, frame-to-frame ratios and any dB *difference* are unaffected
    by either factor. This function returns magnitudes only — the phase is
    discarded, so it cannot be inverted; use ``acoustics.stft`` / ``acoustics.istft``
    for a round-trip."""
    x = _require_finite(x)
    win = int(win)
    hop = win // 2 if hop is None else int(hop)
    if len(x) < win:
        x = np.pad(x, (0, win - len(x)))
    window = np.hanning(win)
    starts = range(0, len(x) - win + 1, hop)
    cols = [np.abs(np.fft.rfft(x[s:s + win] * window)) for s in starts]
    S = np.stack(cols, axis=1) if cols else np.zeros((win // 2 + 1, 0))
    freqs = np.fft.rfftfreq(win, d=1.0 / float(rate))
    times = np.array([s / float(rate) for s in starts])
    return freqs, times, S


# --------------------------------------------------------------------------- #
# filters
# --------------------------------------------------------------------------- #
def _butter(x, rate, cutoff, btype, order=4):
    from scipy.signal import butter, filtfilt
    rate = float(rate)
    if not np.isfinite(rate) or rate <= 0.0:
        raise ValueError("rate must be a positive finite sample rate, got %r" % (rate,))
    nyq = 0.5 * rate
    cut = np.atleast_1d(np.asarray(cutoff, np.float64))
    if not np.isfinite(cut).all() or np.any(cut <= 0.0) or np.any(cut >= nyq):
        raise ValueError(                            # never clip to a near-allpass
            "cutoff %s Hz must lie inside (0, %g) Hz — the Nyquist limit for "
            "rate=%g Hz; an out-of-band cutoff cannot be filtered, it would only "
            "return the signal essentially unchanged" % (cut.tolist(), nyq, rate))
    wn = cut / nyq
    b, a = butter(order, wn if wn.size > 1 else wn[0], btype=btype)
    x = _require_finite(x)
    pad = 3 * max(len(a), len(b))                    # scipy filtfilt's default padlen
    if len(x) <= pad:                                # filtfilt needs enough samples
        raise ValueError(
            "signal has %d sample(s); zero-phase filtfilt needs more than %d for an "
            "order-%d filter — use a longer signal or a lower order"
            % (len(x), pad, int(order)))
    return filtfilt(b, a, x)


def lowpass(x, rate, cutoff, order=4):
    """Butterworth low-pass (scipy, zero-phase filtfilt). *cutoff* must be inside
    ``(0, rate/2)``; an out-of-Nyquist cutoff raises instead of passing the signal
    through. A signal too short for zero-phase filtfilt also raises (the message
    names the exact minimum) instead of silently coming back unfiltered."""
    return _butter(x, rate, cutoff, "low", order)


def highpass(x, rate, cutoff, order=4):
    """Butterworth high-pass. Same Nyquist / length contract as :func:`lowpass`."""
    return _butter(x, rate, cutoff, "high", order)


def bandpass(x, rate, low, high, order=4):
    """Butterworth band-pass between *low* and *high* Hz. Both edges must be inside
    ``(0, rate/2)``; same length contract as :func:`lowpass`."""
    return _butter(x, rate, [low, high], "band", order)


# --------------------------------------------------------------------------- #
# analysis
# --------------------------------------------------------------------------- #
def envelope(x):
    """Amplitude envelope via the analytic (Hilbert) signal — the shape of a
    knock / impact / acoustic-emission burst."""
    from scipy.signal import hilbert
    return np.abs(hilbert(_require_finite(x)))


def rms(x, frame=None, hop=None):
    """RMS level. Scalar for the whole signal, or a framewise array when *frame*
    is given (a vibration/energy envelope over time)."""
    x = _require_finite(x)
    if frame is None:
        return float(np.sqrt(np.mean(x * x))) if x.size else 0.0
    frame = int(frame)
    hop = frame // 2 if hop is None else int(hop)
    return np.array([np.sqrt(np.mean(x[s:s + frame] ** 2))
                     for s in range(0, max(1, len(x) - frame + 1), hop)])


def zero_crossing_rate(x):
    """Fraction of adjacent samples that change sign — a cheap pitch/noisiness cue."""
    x = _require_finite(x)
    if x.size < 2:
        return 0.0
    return float(np.mean(np.abs(np.diff(np.sign(x))) > 0))


def find_peaks(x, height=None, distance=None):
    """Peak indices (scipy.signal.find_peaks) — impacts / defect echoes."""
    from scipy.signal import find_peaks as _fp
    idx, _ = _fp(_require_finite(x), height=height, distance=distance)
    return idx


def resample(x, rate, new_rate):
    """Resample a signal to *new_rate* (Fourier method)."""
    from scipy.signal import resample as _rs
    x = _require_finite(x)
    n = int(round(len(x) * float(new_rate) / float(rate)))
    return _rs(x, max(1, n)), new_rate


def signal_features(x, rate=1.0):
    """A compact acoustic/vibration feature vector for anomaly detection:
    ``rms``, ``peak``, ``crest_factor``, ``zcr``, ``spectral_centroid`` (Hz),
    ``peak_freq`` (Hz), ``bandwidth`` (Hz). All finite — a NaN / Inf sample raises
    ``ValueError`` rather than producing NaN features; empty signal -> zeros."""
    x = _require_finite(x)
    if x.size == 0:
        return {k: 0.0 for k in ("rms", "peak", "crest_factor", "zcr",
                                 "spectral_centroid", "peak_freq", "bandwidth")}
    r = rms(x)
    peak = float(np.max(np.abs(x)))
    freqs, mag = spectrum(x, rate)
    msum = float(mag.sum()) + 1e-12
    centroid = float((freqs * mag).sum() / msum)
    peak_freq = float(freqs[int(np.argmax(mag))])
    bandwidth = float(np.sqrt(((freqs - centroid) ** 2 * mag).sum() / msum))
    return {
        "rms": round(r, 6),
        "peak": round(peak, 6),
        "crest_factor": round(peak / (r + 1e-12), 4),
        "zcr": round(zero_crossing_rate(x), 6),
        "spectral_centroid": round(centroid, 3),
        "peak_freq": round(peak_freq, 3),
        "bandwidth": round(bandwidth, 3),
    }
