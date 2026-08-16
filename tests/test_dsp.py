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


def test_facade_exposes_dsp():
    import fullseye
    assert hasattr(fullseye, "read_wav") and hasattr(fullseye, "signal_features")
