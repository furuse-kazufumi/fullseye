"""Tests for the 1-D signal / acoustic layer (dsp.py) — the differentiator beyond images.

Synthetic tones have known frequency content, so the spectral + feature results are
checked against the exact answer, and WAV round-trips through the stdlib writer."""
import numpy as np
import pytest

import dsp


def _tone(freq=1000.0, rate=16000, dur=0.25, amp=0.5):
    t = np.arange(int(rate * dur)) / rate
    return amp * np.sin(2 * np.pi * freq * t), rate


def test_spectrum_peak_at_tone_frequency():
    x, rate = _tone(1000.0, rate=16000)
    f, mag = dsp.spectrum(x, rate)
    assert abs(f[int(np.argmax(mag))] - 1000.0) < 20        # peak at ~1 kHz


def test_signal_features_on_tone():
    x, rate = _tone(1000.0, rate=16000, amp=0.5)
    feat = dsp.signal_features(x, rate)
    assert abs(feat["peak_freq"] - 1000.0) < 20
    assert abs(feat["rms"] - 0.5 / np.sqrt(2)) < 0.02       # RMS of a 0.5 sine
    assert feat["crest_factor"] > 1.0
    assert dsp.signal_features(np.array([]))["rms"] == 0.0  # empty -> zeros


def test_bandpass_removes_out_of_band_tone():
    rate = 16000
    lo, _ = _tone(200.0, rate=rate, amp=1.0)
    hi, _ = _tone(4000.0, rate=rate, amp=1.0)
    x = lo + hi
    y = dsp.bandpass(x, rate, 3000, 5000)                   # keep 4 kHz, drop 200 Hz
    # the 4 kHz component survives; overall energy drops (200 Hz removed)
    assert dsp.rms(y) < dsp.rms(x)
    f, mag = dsp.spectrum(y, rate)
    assert abs(f[int(np.argmax(mag))] - 4000.0) < 60


def test_wav_roundtrip(tmp_path):
    x, rate = _tone(440.0, rate=8000, amp=0.6)
    p = str(tmp_path / "t.wav")
    dsp.write_wav(p, x, rate)
    y, r2 = dsp.read_wav(p)
    assert r2 == rate and len(y) == len(x)
    assert np.max(np.abs(y - x)) < 1e-3                     # 16-bit round-trip is close


def test_spectrogram_and_envelope_shapes():
    x, rate = _tone(1000.0, rate=8000, dur=0.1)
    f, t, S = dsp.spectrogram(x, rate, win=128)
    assert S.shape[0] == len(f) and S.shape[1] == len(t)
    env = dsp.envelope(x)
    assert env.shape == x.shape and np.all(env >= 0)


def test_find_peaks_on_impulses():
    x = np.zeros(1000)
    x[[100, 500, 900]] = 1.0
    idx = dsp.find_peaks(x, height=0.5, distance=10)
    assert set(idx.tolist()) == {100, 500, 900}


def test_non_finite_signal_is_refused_not_turned_into_nan_features():
    """A NaN / Inf sample used to come back as rms=inf, crest_factor=nan … while the
    docstring promised finite features; the 1-D layer now fails closed like volops."""
    for bad in ([1.0, np.inf, 2.0], [1.0, np.nan, 2.0]):
        with pytest.raises(ValueError, match="non-finite"):
            dsp.signal_features(bad)
        with pytest.raises(ValueError, match="non-finite"):
            dsp.spectrum(bad, 1000)
        with pytest.raises(ValueError, match="non-finite"):
            dsp.rms(bad)
    x, rate = _tone(1000.0, rate=16000)
    assert all(np.isfinite(v) for v in dsp.signal_features(x, rate).values())
    assert dsp.signal_features(np.array([]))["rms"] == 0.0   # empty stays the zero case


def test_cutoff_above_nyquist_raises_instead_of_near_allpass():
    """cutoff=600 Hz at rate=1000 Hz used to be clipped to wn=0.999999 and returned
    the signal essentially unfiltered; an impossible cutoff is now rejected."""
    x, rate = _tone(300.0, rate=1000, dur=2.0, amp=1.0)
    with pytest.raises(ValueError, match="Nyquist"):
        dsp.lowpass(x, rate, 600)                            # above Nyquist (500 Hz)
    with pytest.raises(ValueError, match="Nyquist"):
        dsp.bandpass(x, rate, 100, 900)
    with pytest.raises(ValueError, match="Nyquist"):
        dsp.highpass(x, rate, 0.0)
    y = dsp.lowpass(x, rate, 100)                            # valid cutoff still filters
    assert dsp.rms(y) < 0.1 * dsp.rms(x)


def test_short_signal_filter_raises_instead_of_silent_no_op():
    """filtfilt needs 3x the filter length; too-short input used to be returned
    unchanged, so the caller could not tell filtered from unfiltered."""
    short = np.arange(10, dtype=np.float64)
    with pytest.raises(ValueError, match="filtfilt"):
        dsp.lowpass(short, 1000, 100)


def test_facade_exposes_dsp():
    import fullseye
    assert hasattr(fullseye, "read_wav") and hasattr(fullseye, "signal_features")
