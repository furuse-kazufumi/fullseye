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
    """Single-sided magnitude spectrum -> ``(freqs, magnitude)`` (real FFT)."""
    x = _require_finite(x)
    mag = np.abs(np.fft.rfft(x))
    freqs = np.fft.rfftfreq(len(x), d=1.0 / float(rate))
    return freqs, mag


def spectrogram(x, rate=1.0, win=256, hop=None):
    """STFT magnitude spectrogram -> ``(freqs, times, S)`` with ``S`` shape
    ``(n_freqs, n_frames)``. Hann-windowed; *hop* defaults to ``win//2``."""
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
    nyq = 0.5 * float(rate)
    wn = np.atleast_1d(np.asarray(cutoff, np.float64) / nyq)
    wn = np.clip(wn, 1e-6, 0.999999)
    b, a = butter(order, wn if wn.size > 1 else wn[0], btype=btype)
    x = np.asarray(x, np.float64)
    pad = 3 * (max(len(a), len(b)) - 1)
    if len(x) <= pad:                                # filtfilt needs enough samples
        return x
    return filtfilt(b, a, x)


def lowpass(x, rate, cutoff, order=4):
    """Butterworth low-pass (scipy, zero-phase filtfilt)."""
    return _butter(x, rate, cutoff, "low", order)


def highpass(x, rate, cutoff, order=4):
    """Butterworth high-pass."""
    return _butter(x, rate, cutoff, "high", order)


def bandpass(x, rate, low, high, order=4):
    """Butterworth band-pass between *low* and *high* Hz."""
    return _butter(x, rate, [low, high], "band", order)


# --------------------------------------------------------------------------- #
# analysis
# --------------------------------------------------------------------------- #
def envelope(x):
    """Amplitude envelope via the analytic (Hilbert) signal — the shape of a
    knock / impact / acoustic-emission burst."""
    from scipy.signal import hilbert
    return np.abs(hilbert(np.asarray(x, np.float64)))


def rms(x, frame=None, hop=None):
    """RMS level. Scalar for the whole signal, or a framewise array when *frame*
    is given (a vibration/energy envelope over time)."""
    x = np.asarray(x, np.float64)
    if frame is None:
        return float(np.sqrt(np.mean(x * x))) if x.size else 0.0
    frame = int(frame)
    hop = frame // 2 if hop is None else int(hop)
    return np.array([np.sqrt(np.mean(x[s:s + frame] ** 2))
                     for s in range(0, max(1, len(x) - frame + 1), hop)])


def zero_crossing_rate(x):
    """Fraction of adjacent samples that change sign — a cheap pitch/noisiness cue."""
    x = np.asarray(x, np.float64)
    if x.size < 2:
        return 0.0
    return float(np.mean(np.abs(np.diff(np.sign(x))) > 0))


def find_peaks(x, height=None, distance=None):
    """Peak indices (scipy.signal.find_peaks) — impacts / defect echoes."""
    from scipy.signal import find_peaks as _fp
    idx, _ = _fp(np.asarray(x, np.float64), height=height, distance=distance)
    return idx


def resample(x, rate, new_rate):
    """Resample a signal to *new_rate* (Fourier method)."""
    from scipy.signal import resample as _rs
    x = np.asarray(x, np.float64)
    n = int(round(len(x) * float(new_rate) / float(rate)))
    return _rs(x, max(1, n)), new_rate


def signal_features(x, rate=1.0):
    """A compact acoustic/vibration feature vector for anomaly detection:
    ``rms``, ``peak``, ``crest_factor``, ``zcr``, ``spectral_centroid`` (Hz),
    ``peak_freq`` (Hz), ``bandwidth`` (Hz). All finite; empty signal -> zeros."""
    x = np.asarray(x, np.float64)
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
