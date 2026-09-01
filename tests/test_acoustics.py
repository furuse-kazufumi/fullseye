# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Contract and closed-form tests for :mod:`acoustics`.

Every assertion below is anchored on a quantity that is known *before* the
measurement, not on a previously recorded output:

* an invertible transform must invert (machine precision),
* a known amplitude modulation must come back as its own modulation depth at
  its own rate,
* a known shaft order must stay put through a speed ramp while a known fixed
  resonance smears,
* a band definition must satisfy the geometric identities that define it,
* a weighting curve must be 0 dB at 1 kHz by construction and approach its
  analytic slope,
* an echo of known delay must produce a rahmonic at that delay,
* a known gain and a known delay must come back out of a two-channel estimator.

The adversarial section at the bottom does not test that exceptions happen. It
tests the cases where a *plausible wrong number* was found to come back, and
pins the behaviour that was put in to make it visible.
"""
from __future__ import annotations

import numpy as np
import pytest

import acoustics as A
import dsp
import opsacoustics


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _noise(n=4096, seed=0):
    return np.random.default_rng(seed).standard_normal(n)


def _tone(freq, rate, n, amp=1.0):
    return amp * np.sin(2.0 * np.pi * freq * np.arange(n) / rate)


# --------------------------------------------------------------------------- #
# 1. STFT / ISTFT — the round trip is the closed form                          #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("window,win,hop,nfft", [
    ("hann", 256, 128, None),
    ("hann", 256, 64, None),
    ("hamming", 256, 128, None),
    ("blackman", 512, 128, None),
    ("flattop", 256, 64, None),
    ("boxcar", 256, 128, None),
    ("hann", 256, 128, 512),
    ("hann", 64, 17, None),                 # non-dividing hop
])
def test_stft_roundtrip_is_exact(window, win, hop, nfft):
    x = _noise(4096, seed=1)
    tr = A.stft(x, 16000.0, win=win, hop=hop, window=window, nfft=nfft)
    back = A.istft(tr)
    assert back.shape == x.shape
    assert np.abs(back - x).max() < 1e-12


def test_stft_roundtrip_survives_barely_overlapping_hop():
    """hop = win - 1 satisfies NOLA but is badly conditioned; both facts hold."""
    x = _noise(4096, seed=2)
    tr = A.stft(x, 16000.0, win=256, hop=255)
    assert 0.0 < tr["nola_min"] < 1e-6            # the conditioning warning
    assert np.abs(A.istft(tr) - x).max() < 1e-9   # still inverts, 1000x worse


@pytest.mark.parametrize("scaling", ["none", "amplitude", "density"])
def test_stft_roundtrip_is_exact_under_every_scaling(scaling):
    x = _noise(2048, seed=3)
    tr = A.stft(x, 16000.0, win=256, hop=128, scaling=scaling)
    assert np.abs(A.istft(tr) - x).max() < 1e-12


def test_amplitude_scaling_reads_the_tone_amplitude():
    fs, n, amp = 16000.0, 4096, 0.7
    tr = A.stft(_tone(1000.0, fs, n, amp), fs, win=256, hop=128,
                scaling="amplitude")
    k = int(round(1000.0 / (fs / 256)))            # exactly on a bin centre
    v = np.abs(tr["spectra"][k, tr["interior"]])
    assert np.allclose(v, amp, atol=1e-12)


def test_density_scaling_integrates_to_the_variance():
    fs, x = 16000.0, _noise(16384, seed=4)
    tr = A.stft(x, fs, win=1024, hop=512, scaling="density")
    psd = (np.abs(tr["spectra"][:, tr["interior"]]) ** 2).mean(axis=1)
    df = tr["freqs"][1] - tr["freqs"][0]
    assert abs(psd.sum() * df - x.var()) < 0.02 * x.var()


def test_interior_mask_matters_for_frame_averages():
    """Regression: pad frames bias any frame-averaged statistic low."""
    fs, x = 16000.0, _noise(16384, seed=4)
    tr = A.stft(x, fs, win=1024, hop=512, scaling="density")
    df = tr["freqs"][1] - tr["freqs"][0]
    allf = (np.abs(tr["spectra"]) ** 2).mean(axis=1).sum() * df
    inner = (np.abs(tr["spectra"][:, tr["interior"]]) ** 2).mean(axis=1).sum() * df
    assert allf < 0.95 * inner                     # the bias is real and large
    assert abs(inner - x.var()) < 0.02 * x.var()


def test_cola_is_exact_for_the_pairs_that_have_it():
    for window, win, hop, want in [("hann", 256, 128, True),
                                   ("hann", 256, 64, True),
                                   ("hamming", 256, 128, True),
                                   ("boxcar", 256, 128, True),
                                   ("blackman", 256, 64, True),
                                   ("blackman", 256, 128, False),
                                   ("hann", 256, 85, False)]:
        r = A.stft_cola_check(window, win, hop)
        assert r["cola"] is want, (window, win, hop, r["relative_deviation"])
        assert r["nola"] is True
    assert abs(A.stft_cola_check("hann", 256, 128)["constant"] - 1.0) < 1e-12
    assert abs(A.stft_cola_check("boxcar", 256, 128)["constant"] - 2.0) < 1e-12


# --------------------------------------------------------------------------- #
# 2. Bearings: a known modulation comes back as itself                         #
# --------------------------------------------------------------------------- #
def test_envelope_spectrum_recovers_the_modulation_exactly():
    fs, fd, m = 25600.0, 107.0, 0.5
    x = A.synthesize_bearing_signal(fs, 1.0, 3000.0, fd, modulation=m, mode="am")
    r = A.envelope_spectrum(x, fs, 2000.0, 4000.0)
    assert abs(r["peak_freq"] - fd) < 1e-9         # bin-exact: 1 s -> 1 Hz bins
    assert abs(r["peak_amplitude"] - m) < 5e-4     # the modulation depth itself
    assert r["peak_prominence"] > 1e3


def test_the_defect_rate_is_absent_from_the_raw_spectrum():
    """The reason the operator exists: the raw spectrum does not show it."""
    fs, fd = 25600.0, 107.0
    x = A.synthesize_bearing_signal(fs, 1.0, 3000.0, fd, modulation=0.5, mode="am")
    freqs, mag = dsp.spectrum(x, fs)
    amp = mag * 2.0 / x.size
    at_defect = amp[int(round(fd / (fs / x.size)))]
    at_carrier = amp[int(round(3000.0 / (fs / x.size)))]
    assert at_defect < 1e-12                       # nothing at all
    assert abs(at_carrier - 1.0) < 1e-6
    for side in (3000.0 - fd, 3000.0 + fd):        # energy is in the sidebands
        assert abs(amp[int(round(side / (fs / x.size)))] - 0.25) < 1e-6


def test_envelope_spectrum_finds_the_harmonics_in_impulse_mode():
    fs, fd = 25600.0, 107.0
    x = A.synthesize_bearing_signal(fs, 1.0, 3000.0, fd, mode="impulse",
                                    damping=0.05)
    r = A.envelope_spectrum(x, fs, 2000.0, 4000.0, n_peaks=8)
    assert abs(r["peak_freq"] - fd) < 1e-9
    res = r["resolution_hz"]
    for k in (2, 3):
        assert r["magnitude"][int(round(k * fd / res))] > 0.4 * r["peak_amplitude"]


def test_bearing_kinematic_identities_are_exact():
    b = A.bearing_defect_frequencies(1800.0, 9, 8.0, 40.0)
    assert b["shaft_hz"] == 30.0
    assert abs(b["bpfo_hz"] + b["bpfi_hz"] - 9 * b["shaft_hz"]) < 1e-12
    assert abs(b["bpfo_hz"] - 9 * b["ftf_hz"]) < 1e-12
    assert 0.0 < b["ftf_hz"] < 0.5 * b["shaft_hz"]
    assert b["bsf_hz_2x"] == 2.0 * b["bsf_hz"]


@pytest.mark.parametrize("rpm,n,d,dp", [(1800.0, 9, 8.0, 40.0),
                                        (600.0, 16, 3.0, 55.0),
                                        (3550.0, 7, 12.7, 61.0)])
def test_bearing_identities_hold_for_any_geometry(rpm, n, d, dp):
    b = A.bearing_defect_frequencies(rpm, n, d, dp, contact_angle_deg=15.0)
    assert abs(b["bpfo_hz"] + b["bpfi_hz"] - n * b["shaft_hz"]) < 1e-9
    assert abs(b["bpfo_hz"] - n * b["ftf_hz"]) < 1e-9


def test_spectral_kurtosis_reference_cases():
    fs = 16000.0
    sk_noise = A.spectral_kurtosis(_noise(8192, seed=5), fs)
    keep = np.ones(sk_noise["kurtosis"].size, bool)
    for b in sk_noise["real_bins"]:
        keep[b] = False
    assert abs(sk_noise["kurtosis"][keep].mean()) < sk_noise["noise_sigma"]
    sk_tone = A.spectral_kurtosis(_tone(2000.0, fs, 8192), fs)
    j = int(np.argmin(np.abs(sk_tone["freqs"] - 2000.0)))
    assert abs(sk_tone["kurtosis"][j] + 1.0) < 1e-3        # a tone reads -1


def test_spectral_kurtosis_selects_a_band_that_demodulates():
    """End-to-end: the band it picks by itself recovers the true defect rate."""
    fs, fd = 25600.0, 107.0
    x = A.synthesize_bearing_signal(fs, 1.0, 3000.0, fd, mode="impulse",
                                    damping=0.05, noise_sigma=0.05, seed=3)
    sk = A.spectral_kurtosis(x, fs)
    assert sk["max_kurtosis"] > 1.0
    lo, hi = sk["band_lo"], sk["band_hi"]
    # this bin is interior on both sides, so the band is the plain +- one bin
    assert (lo, hi) == (sk["max_freq"] - sk["bin_hz"], sk["max_freq"] + sk["bin_hz"])
    assert abs(A.envelope_spectrum(x, fs, lo, hi)["peak_freq"] - fd) < 1e-9


def test_spectral_kurtosis_band_survives_the_top_bin_handoff():
    """The sibling-op handoff bug: `max_freq +- bin_hz` assembled by the caller
    lands *on* Nyquist whenever the winning bin is the topmost interior one, and
    `envelope_spectrum` fail-closes on it. Measured on the family's own minimal
    example (AM, 25600 Hz, 3 kHz carrier, 107 Hz defect, m = 0.5), whose kurtosis
    maximum is 12400 Hz with bin_hz 400 against a Nyquist of 12800.

    Both operators are individually right; the contract between them was not.
    `envelope_spectrum` keeps refusing (there really is no band at Nyquist) and
    `spectral_kurtosis` now hands over a band that is legal by construction."""
    fs = 25600.0
    x = A.synthesize_bearing_signal(fs, 1.0, 3000.0, 107.0, modulation=0.5,
                                    mode="am")
    sk = A.spectral_kurtosis(x, fs)
    # the precondition of the original bug, pinned so the test cannot go vacuous
    assert sk["max_freq"] == 12400.0 and sk["bin_hz"] == 400.0
    assert sk["freqs"][-1] == 0.5 * fs                 # freqs include Nyquist
    assert sk["max_freq"] + sk["bin_hz"] == 0.5 * fs   # the hand-built edge

    with pytest.raises(ValueError, match="at or above Nyquist"):
        A.envelope_spectrum(x, fs, sk["max_freq"] - sk["bin_hz"],
                            sk["max_freq"] + sk["bin_hz"])

    assert (sk["band_lo"], sk["band_hi"]) == (12000.0, 12600.0)
    env = A.envelope_spectrum(x, fs, sk["band_lo"], sk["band_hi"])
    # returning is not the same as finding: SK itself says there is nothing here
    assert sk["max_kurtosis"] < sk["noise_sigma"]
    assert env["band_fraction"] < 1e-3
    # ...whereas the known resonance band on the same signal is the real thing
    assert abs(A.envelope_spectrum(x, fs, 2000.0, 4000.0)["peak_freq"] - 107.0) < 1e-9


@pytest.mark.parametrize("fs,n,win", [
    (25600.0, 25600, None), (25600.0, 25600, 16), (25600.0, 25600, 64),
    (16000.0, 8192, 32), (48000.0, 16384, 64), (1000.0, 4096, 16),
    (25600.0, 4096, 128),
])
def test_spectral_kurtosis_band_is_always_a_legal_envelope_spectrum_call(fs, n, win):
    """Whatever bin wins, the band handed over is inside the open interval the
    consumer accepts — checked against the consumer itself, not against a
    re-implementation of its rule."""
    x = A.synthesize_bearing_signal(fs, n / fs, 0.12 * fs, 107.0,
                                    mode="impulse", damping=0.05,
                                    noise_sigma=0.05, seed=11)
    sk = A.spectral_kurtosis(x, fs, win=win)
    assert 0.0 < sk["band_lo"] < sk["band_hi"] < 0.5 * fs
    env = A.envelope_spectrum(x, fs, sk["band_lo"], sk["band_hi"])
    assert env["band"] == (sk["band_lo"], sk["band_hi"])


def test_acoustics_guide_python_snippets_actually_run():
    """The documented recipe is executed, not just spell-checked. This guide's
    minimal example *was* the failing handoff above: it was committed, read, and
    copied into an article while raising ValueError on its own inputs."""
    import os
    import re
    guide = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "docs", "ops", "acoustics", "guides",
                         "acoustic_condition_monitoring.md")
    with open(guide, encoding="utf-8") as f:
        blocks = re.findall(r"```python\n(.*?)```", f.read(), re.S)
    # Self-contained blocks only. The guide also quotes the *broken* handoff as a
    # one-liner fragment, deliberately, and that one must keep raising.
    runnable = [b for b in blocks if "import acoustics" in b]
    assert runnable, "the acoustics guide lost its runnable snippet"
    for src in runnable:
        exec(compile(src, guide, "exec"), {"__name__": "__guide__"})


def test_spectral_kurtosis_window_must_be_shorter_than_the_repetition():
    """The documented failure mode, pinned so it cannot regress silently."""
    fs, fd = 25600.0, 107.0
    x = A.synthesize_bearing_signal(fs, 1.0, 3000.0, fd, mode="impulse",
                                    damping=0.05)
    short = A.spectral_kurtosis(x, fs, win=64)
    long_ = A.spectral_kurtosis(x, fs, win=256)
    assert short["window_seconds"] < 1.0 / fd < long_["window_seconds"]
    assert short["max_kurtosis"] > 1.0
    assert long_["max_kurtosis"] < 0.0             # reports *no* impulsiveness


def test_cepstrum_finds_a_known_echo_delay_exactly():
    fs, n, delay = 8000.0, 8192, 200
    x = _noise(n, seed=6)
    y = x.copy()
    y[delay:] += 0.6 * x[:-delay]
    r = A.cepstrum(y, fs)
    assert int(round(r["peak_quefrency"] * fs)) == delay
    assert abs(r["peak_quefrency"] - delay / fs) < 1e-12
    assert r["floored_bins"] == 0


def test_cepstrum_finds_a_known_line_spacing():
    fs, n, spacing = 8000.0, 16384, 50.0
    rng = np.random.default_rng(7)
    train = np.zeros(n)
    train[::int(fs / spacing)] = 1.0
    y = np.convolve(train, rng.standard_normal(64))[:n] + 0.01 * rng.standard_normal(n)
    r = A.cepstrum(y, fs, min_quefrency=0.002)
    assert abs(r["peak_rate_hz"] - spacing) < 1e-9


def test_cepstrum_power_mode_is_exactly_twice_real_mode():
    x = _noise(2048, seed=8)
    a = A.cepstrum(x, 8000.0, mode="real")["cepstrum"]
    b = A.cepstrum(x, 8000.0, mode="power")["cepstrum"]
    assert np.abs(b - 2.0 * a).max() == 0.0


# --------------------------------------------------------------------------- #
# 3. Order tracking: the order stays, the resonance smears                     #
# --------------------------------------------------------------------------- #
def test_order_spectrum_holds_a_known_order_through_a_speed_ramp():
    r = A.synthesize_speed_ramp(5000.0, 4.0, 600.0, 1800.0, orders=(1.0, 3.5),
                                resonance_hz=400.0)
    o = A.order_spectrum(r["signal"], r["rate"], r["rpm"], samples_per_rev=64,
                         revolutions=78)
    for order in (1.0, 3.5):
        j = int(round(order / o["resolution_order"]))
        assert abs(o["orders"][j] - order) < 1e-12
        assert abs(o["magnitude"][j] - 1.0) < 5e-3     # amplitude recovered


def test_the_ordinary_spectrum_is_the_one_that_breaks():
    """Without angular resampling the same component is smeared and small."""
    r = A.synthesize_speed_ramp(5000.0, 4.0, 600.0, 1800.0, orders=(1.0, 3.5),
                                resonance_hz=400.0)
    freqs, mag = dsp.spectrum(r["signal"] - r["signal"].mean(), r["rate"])
    amp = mag * 2.0 / r["signal"].size
    sel = (freqs >= 32.0) & (freqs <= 110.0)           # order 3.5 sweeps 35-105
    assert amp[sel].max() < 0.15                       # ~7 % of the true 1.0
    wide = freqs[sel][amp[sel] >= amp[sel].max() / np.sqrt(2.0)]
    assert wide.max() - wide.min() > 50.0              # tens of Hz wide
    o = A.order_spectrum(r["signal"], r["rate"], r["rpm"], 64, revolutions=78)
    j = int(round(3.5 / o["resolution_order"]))
    narrow = o["orders"][o["magnitude"] >= o["magnitude"][j] / np.sqrt(2.0)]
    narrow = narrow[(narrow > 3.0) & (narrow < 4.0)]
    assert narrow.max() - narrow.min() < 0.05          # one bin


def test_a_fixed_resonance_smears_under_angular_resampling():
    """The reversal is the diagnostic, so it is asserted in both directions."""
    r = A.synthesize_speed_ramp(5000.0, 4.0, 600.0, 1800.0, orders=(1.0,),
                                resonance_hz=400.0)
    freqs, mag = dsp.spectrum(r["signal"] - r["signal"].mean(), r["rate"])
    amp = mag * 2.0 / r["signal"].size
    assert abs(amp[int(np.argmin(np.abs(freqs - 400.0)))] - 1.0) < 0.05
    o = A.order_spectrum(r["signal"], r["rate"], r["rpm"], 64, revolutions=78)
    lo, hi = 400.0 / (1800.0 / 60.0), 400.0 / (600.0 / 60.0)
    sel = (o["orders"] >= lo) & (o["orders"] <= hi)
    assert o["magnitude"][sel].max() < 0.15            # smeared away


def test_half_integer_orders_need_an_even_revolution_count():
    """Regression for a measured 36 % scallop loss that raised nothing."""
    r = A.synthesize_speed_ramp(5000.0, 4.0, 600.0, 1800.0, orders=(3.5,))
    odd = A.order_spectrum(r["signal"], r["rate"], r["rpm"], 64, revolutions=79)
    even = A.order_spectrum(r["signal"], r["rate"], r["rpm"], 64, revolutions=78)
    assert odd["peak_amplitude"] < 0.7                 # measured 0.637
    assert abs(even["peak_amplitude"] - 1.0) < 5e-3


def test_angular_resample_at_constant_speed_is_a_pure_rescale():
    fs, rpm = 4000.0, 120.0                            # 2 rev/s
    x = _tone(20.0, fs, 8000)                          # order 10
    ang = A.angular_resample(x, fs, rpm, samples_per_rev=64)
    # 8000 samples span 7999 intervals, so the record is 4 - 1/2000 revolutions
    assert abs(ang["revolutions"] - (8000 - 1) / fs * (rpm / 60.0)) < 1e-9
    assert ang["mean_rpm"] == rpm
    assert ang["max_order"] == 32.0
    assert ang["whole_revolutions"] == 3
    o = A.order_spectrum(x, fs, rpm, samples_per_rev=64, revolutions=3)
    assert abs(o["peak_order"] - 10.0) < 1e-12


# --------------------------------------------------------------------------- #
# 4. Acoustic quantities: identities that define the constructions             #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("fraction", [1, 2, 3, 6, 12, 24])
@pytest.mark.parametrize("base", [2, 10])
def test_octave_band_geometric_identities(fraction, base):
    b = A.octave_bands(fraction=fraction, f_min=22.0, f_max=20000.0, base=base)
    g = 2.0 if base == 2 else 10.0 ** 0.3
    step = g ** (1.0 / fraction)
    assert np.allclose(b["upper"] / b["lower"], step, rtol=1e-12)
    assert np.allclose(b["centers"], np.sqrt(b["lower"] * b["upper"]), rtol=1e-12)
    assert np.allclose(b["centers"][1:] / b["centers"][:-1], step, rtol=1e-12)
    assert b["ratio"] == pytest.approx(step)


@pytest.mark.parametrize("fraction", [1, 2, 3, 6, 12, 24])
def test_where_1_khz_sits_depends_on_the_parity_of_the_fraction(fraction):
    """Odd b centres a band on 1 kHz; even b puts a band *edge* there and has
    no 1 kHz band at all. That is the construction, and it is surprising enough
    to be worth pinning."""
    b = A.octave_bands(fraction=fraction, f_min=22.0, f_max=20000.0)
    if fraction % 2 == 1:
        assert np.isclose(b["centers"], 1000.0, rtol=1e-12).any()
        assert not np.isclose(b["lower"], 1000.0, rtol=1e-12).any()
    else:
        assert not np.isclose(b["centers"], 1000.0, rtol=1e-12).any()
        assert np.isclose(b["lower"], 1000.0, rtol=1e-12).any()
        assert np.isclose(b["upper"], 1000.0, rtol=1e-12).any()


def test_base_two_octave_centers_are_the_exact_powers():
    b = A.octave_bands(fraction=1, f_min=22.0, f_max=20000.0, base=2)
    assert np.allclose(np.sort(b["centers"]),
                       [31.25, 62.5, 125.0, 250.0, 500.0, 1000.0, 2000.0,
                        4000.0, 8000.0, 16000.0], rtol=1e-12)


def test_octave_spectrum_level_matches_the_closed_form():
    fs, amp = 16000.0, 0.7
    x = _tone(1000.0, fs, 16000, amp)                  # exactly 1000 periods
    o = A.octave_spectrum(x, fs, fraction=3, ref=1.0)
    j = int(np.argmin(np.abs(o["centers"] - 1000.0)))
    assert abs(o["levels"][j] - 10.0 * np.log10(amp ** 2 / 2.0)) < 1e-9
    assert o["clamped"].sum() == o["clamped"].size - 1  # only that band has any


def test_octave_spectrum_obeys_parseval():
    fs, x = 16000.0, _noise(16384, seed=9)
    o = A.octave_spectrum(x, fs, fraction=3, f_min=22.0, f_max=8000.0)
    assert abs(o["total_power"] - np.mean(x * x)) < 1e-12 * np.mean(x * x)
    assert 0.99 < o["powers"].sum() / np.mean(x * x) <= 1.0


@pytest.mark.parametrize("kind", ["A", "C"])
def test_weighting_is_exactly_zero_db_at_1_khz(kind):
    assert A.weighting_response(np.array([1000.0]), kind)[0] == 0.0


def test_weighting_z_is_flat():
    f = np.array([10.0, 100.0, 1000.0, 10000.0])
    assert np.all(A.weighting_response(f, "Z") == 0.0)


@pytest.mark.parametrize("kind,slope", [("A", 80.0), ("C", 40.0)])
def test_weighting_low_frequency_asymptote(kind, slope):
    """The analytic slope, measured with the report floor moved out of the way."""
    w = A.weighting_response(np.array([0.001, 0.01]), kind, floor_db=-1e6)
    assert abs((w[1] - w[0]) - slope) < 1e-4


def test_weighting_is_even_in_frequency():
    a = A.weighting_response(np.array([-100.0, -1000.0]), "A")
    b = A.weighting_response(np.array([100.0, 1000.0]), "A")
    assert np.array_equal(a, b)


def test_weighting_floors_dc_instead_of_returning_minus_inf():
    v = A.weighting_response(np.array([0.0]), "A")
    assert np.isfinite(v).all() and v[0] == A.FLOOR_DB


@pytest.mark.parametrize("kind", ["A", "C"])
def test_apply_weighting_leaves_1_khz_untouched(kind):
    fs = 16000.0
    x = _tone(1000.0, fs, 16000)
    assert np.abs(A.apply_weighting(x, fs, kind) - x).max() < 1e-11


def test_apply_weighting_matches_the_curve_at_100_hz():
    fs = 16000.0
    x = _tone(100.0, fs, 16000)
    y = A.apply_weighting(x, fs, "A")
    want = 10.0 ** (A.weighting_response(np.array([100.0]), "A")[0] / 20.0)
    assert abs(np.abs(y).max() - want) < 1e-6


def test_equivalent_level_matches_the_closed_form():
    fs = 16000.0
    x = _tone(1000.0, fs, 16000, 1.0)
    assert abs(A.equivalent_level(x, fs, "Z") - 10.0 * np.log10(0.5)) < 1e-9
    # A is 0 dB at 1 kHz, so it must not move the level of a 1 kHz tone
    assert abs(A.equivalent_level(x, fs, "A")
               - A.equivalent_level(x, fs, "Z")) < 1e-9
    # doubling the amplitude is exactly +20*log10(2) dB
    assert abs(A.equivalent_level(2 * x, fs, "Z") - A.equivalent_level(x, fs, "Z")
               - 20.0 * np.log10(2.0)) < 1e-9


def _a_weight_error_db(f0, fs=48000.0, duration=0.5):
    """How far the measured A-weighted level of a pure tone sits from A(f0)."""
    x = _tone(f0, fs, int(duration * fs), 1.0)
    got = A.equivalent_level(x, fs, "A") - A.equivalent_level(x, fs, "Z")
    return got - float(A.weighting_response(np.array([f0]), "A")[0])


@pytest.mark.parametrize("f0", [22.0, 100.0, 1000.0, 250.0])
def test_a_weighting_is_exact_when_the_tone_closes_on_itself(f0):
    """Whole number of periods in the record -> no leakage -> exactly A(f0)."""
    assert (f0 * 0.5) == int(f0 * 0.5), "the probe must be bin-centred"
    assert abs(_a_weight_error_db(f0)) < 1e-9


def test_a_weighting_reads_a_non_bin_centred_tone_too_loud():
    """A found bug that is *not* repaired, pinned so the docstring cannot drift
    away from it and so nobody reads a low-frequency A-level as trustworthy.

    The weighting multiplies the record's own DFT, which treats it as periodic;
    a tone that does not close on itself leaks into every bin, and A weighting
    spans ~40 dB across the band, so leakage landing near 1 kHz outweighs the
    attenuated fundamental. Measured, 0.5 s at 48 kHz:
        31.5 Hz (15.75 periods, a nominal 1/3-octave centre)  +7.7986 dB
        20.5 Hz (10.25 periods, worst over a 20-200 Hz sweep) +17.2116 dB
    The error is always positive — leakage only adds power where the curve is
    generous. Nothing raises and nothing is NaN.
    """
    assert _a_weight_error_db(31.5) == pytest.approx(7.7986, abs=1e-3)
    assert _a_weight_error_db(20.5) == pytest.approx(17.2116, abs=1e-3)
    worst = max(_a_weight_error_db(f) for f in np.linspace(20.0, 200.0, 361))
    assert worst > 5.0, worst                      # the failure is not marginal


def test_a_weighting_leakage_is_dynamic_range_not_arithmetic():
    """Two controls that identify the cause, both pinned.

    (1) C weighting has the same machinery but a far gentler tilt, so the same
        31.5 Hz tone is off by only +0.0493 dB instead of +7.7986.
    (2) Lengthening the record until the tone *does* close on itself removes it:
        0.25 s +7.7524, 0.5 s +7.7986, 1 s +0.4615, 2 s -0.0000, 4 s -0.0000.
    """
    fs, f0 = 48000.0, 31.5
    x = _tone(f0, fs, int(0.5 * fs), 1.0)
    c_err = (A.equivalent_level(x, fs, "C") - A.equivalent_level(x, fs, "Z")
             - float(A.weighting_response(np.array([f0]), "C")[0]))
    assert abs(c_err) < 0.1, c_err                 # measured +0.0493
    assert abs(_a_weight_error_db(f0, fs, 1.0)) == pytest.approx(0.4615, abs=1e-3)
    for dur in (2.0, 4.0):                         # 63 and 126 whole periods
        assert abs(_a_weight_error_db(f0, fs, dur)) < 1e-9


def test_a_weighting_leakage_is_not_cured_by_windowing_or_padding():
    """The negative result, pinned so the "obvious fix" is not attempted again.

    Measured at 31.5 Hz / 0.5 s / 48 kHz: as implemented +7.7986 dB, zero-padded
    x4 (linear convolution) +8.6055 — *worse*, because padding puts a broadband
    edge into the record — and Hann-windowed with its power gain divided out
    +3.0879, which also breaks the bin-centred cases that are exact today
    (22 Hz goes from +0.0000 to +5.5586 dB). A real cure is a time-domain
    biquad cascade, which would give up the exact 0 dB at 1 kHz this module is
    built on.
    """
    fs, f0, n = 48000.0, 31.5, int(0.5 * 48000.0)

    def gain(m):
        f = np.fft.rfftfreq(m, d=1.0 / fs)
        r = A._weighting_ratio(f, "A")
        return r / float(A._weighting_ratio(np.array([A.F_REF_HZ]), "A")[0])

    def leq_padded(x, pad=4):
        m = pad * x.size
        y = np.fft.irfft(np.fft.rfft(x, n=m) * gain(m), n=m)[:x.size]
        return 10.0 * np.log10(np.mean(y * y))

    def leq_hann(x):
        w = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(x.size) / x.size)
        y = np.fft.irfft(np.fft.rfft(x * w) * gain(x.size), n=x.size)
        return 10.0 * np.log10(np.mean(y * y) / np.mean(w * w))

    def z_padded(x, pad=4):
        return 10.0 * np.log10(np.mean(x * x))

    x = _tone(f0, fs, n, 1.0)
    exact = float(A.weighting_response(np.array([f0]), "A")[0])
    assert (leq_padded(x) - z_padded(x) - exact) == pytest.approx(8.6055, abs=2e-2)
    hann_err = leq_hann(x) - 10.0 * np.log10(np.mean(x * x)) - exact
    assert hann_err == pytest.approx(3.0879, abs=2e-2)
    assert hann_err > 1.0, "Hann must not be mistaken for a cure"
    # ...and it breaks a case that is exact today
    x22 = _tone(22.0, fs, n, 1.0)
    e22 = float(A.weighting_response(np.array([22.0]), "A")[0])
    assert abs(_a_weight_error_db(22.0)) < 1e-9                 # exact now
    assert (leq_hann(x22) - 10.0 * np.log10(np.mean(x22 * x22))
            - e22) == pytest.approx(5.5586, abs=2e-2)           # broken by Hann


def test_equivalent_level_reference_scales_the_answer():
    fs = 16000.0
    x = _tone(1000.0, fs, 16000, 1.0)
    a = A.equivalent_level(x, fs, "Z", ref=1.0)
    b = A.equivalent_level(x, fs, "Z", ref=0.1)
    assert abs((b - a) - 20.0) < 1e-9              # ref/10 is +20 dB


def test_percentile_levels_of_a_two_level_signal_are_the_two_levels():
    fs, n = 16000.0, 16000
    half = n // 2
    x = np.concatenate([_tone(1000.0, fs, half, 1.0),
                        _tone(1000.0, fs, half, 0.1)])
    p = A.percentile_level(x, fs, (10.0, 90.0), weighting="Z", window_s=0.125)
    assert abs(p["L10"] - 10.0 * np.log10(0.5)) < 1e-6
    assert abs(p["L90"] - 10.0 * np.log10(0.005)) < 1e-6
    assert abs((p["L10"] - p["L90"]) - 20.0) < 1e-6


def test_percentile_levels_of_a_constant_signal_all_agree():
    fs = 16000.0
    x = _tone(1000.0, fs, 16000, 1.0)
    p = A.percentile_level(x, fs, (10.0, 50.0, 90.0), weighting="Z",
                           window_s=0.125)
    assert max(abs(p["L10"] - p["L90"]), abs(p["L50"] - p["leq"])) < 1e-9


# --------------------------------------------------------------------------- #
# 5. Two-channel: a known system comes back out                                #
# --------------------------------------------------------------------------- #
def test_transfer_function_recovers_a_pure_gain_exactly():
    fs, x = 16000.0, _noise(16384, seed=10)
    h = A.transfer_function(x, 2.5 * x, fs, win=1024)
    assert np.abs(h["magnitude"] - 2.5).max() < 1e-12
    assert np.abs(h["phase_rad"]).max() < 1e-12
    assert np.abs(h["coherence"] - 1.0).max() < 1e-12


def test_transfer_function_recovers_a_known_delay():
    fs, n, delay, gain = 16000.0, 16384, 37, 0.8
    x = _noise(n, seed=11)
    y = np.zeros(n)
    y[delay:] = gain * x[:-delay]
    h = A.transfer_function(x, y, fs, win=1024)
    sel = (h["freqs"] > 200.0) & (h["freqs"] < 7000.0)
    slope = np.polyfit(h["freqs"][sel], np.unwrap(h["phase_rad"])[sel], 1)[0]
    assert abs(-slope / (2.0 * np.pi) * fs - delay) < 1e-3
    assert abs(h["magnitude"][sel].mean() - gain) < 0.02


def test_h1_beats_h2_under_output_noise_and_their_ratio_is_the_coherence():
    fs, n, gain = 16000.0, 16384, 2.5
    rng = np.random.default_rng(12)
    x = rng.standard_normal(n)
    y = gain * x + gain * rng.standard_normal(n)         # 0 dB output SNR
    h1 = A.transfer_function(x, y, fs, win=1024, estimator="h1")
    h2 = A.transfer_function(x, y, fs, win=1024, estimator="h2")
    assert abs(h1["magnitude"].mean() - gain) < 0.05 * gain     # H1 is right
    assert h2["magnitude"].mean() > 1.8 * gain                  # H2 is not
    ratio = np.abs(h1["response"] / h2["response"])
    assert np.abs(ratio - h1["coherence"]).max() < 1e-12        # exact identity


def test_coherence_of_a_noiseless_scaling_is_exactly_one():
    fs, x = 16000.0, _noise(16384, seed=13)
    c = A.coherence(x, -3.0 * x, fs, win=1024)
    assert np.abs(c["coherence"] - 1.0).max() < 1e-12


def test_coherence_follows_the_snr_closed_form():
    fs, n = 16000.0, 16384
    rng = np.random.default_rng(14)
    x = rng.standard_normal(n)
    for snr in (1.0, 4.0, 16.0):
        y = x + rng.standard_normal(n) / np.sqrt(snr)
        c = A.coherence(x, y, fs, win=1024)
        assert abs(c["mean_coherence"] - snr / (1.0 + snr)) < 0.05


def test_coherence_of_independent_records_is_near_its_bias_not_zero():
    fs, n = 16000.0, 16384
    rng = np.random.default_rng(15)
    c = A.coherence(rng.standard_normal(n), rng.standard_normal(n), fs, win=1024)
    assert abs(c["mean_coherence"] - c["bias"]) < 3.0 * c["bias"]
    assert c["bias"] == pytest.approx(1.0 / c["n_frames"])


# --------------------------------------------------------------------------- #
# 6. Composition with what already exists                                      #
# --------------------------------------------------------------------------- #
def test_dsp_is_reused_not_reimplemented():
    """envelope_spectrum must be dsp.bandpass + dsp.envelope, provably."""
    fs = 25600.0
    x = A.synthesize_bearing_signal(fs, 0.5, 3000.0, 107.0, modulation=0.5)
    r = A.envelope_spectrum(x, fs, 2000.0, 4000.0)
    env = dsp.envelope(dsp.bandpass(x, fs, 2000.0, 4000.0, order=4))
    e = env - env.mean()
    mag = np.abs(np.fft.rfft(e)) * (2.0 / e.size)
    assert np.abs(mag - r["magnitude"]).max() < 1e-12


def test_a_motionmag_displacement_waveform_is_an_ordinary_acoustic_signal():
    """The camera-side and microphone-side paths measure the same quantity."""
    motionmag = pytest.importorskip("motionmag")
    fps, freq = 64.0, 8.0
    clip = motionmag.synthesize_translation((32, 32), 64, amplitude_px=0.3,
                                            frequency_hz=freq, fps=fps,
                                            direction_deg=0.0, seed=0)
    d = motionmag.displacement_series(clip, 5.0, 11.0, fps)
    dx = np.ascontiguousarray(np.asarray(d, np.float64)[:, 0])
    freqs, mag = dsp.spectrum(dx - dx.mean(), fps)
    assert abs(freqs[int(np.argmax(mag))] - freq) < 1.0
    # and it goes straight through this module's machinery unchanged
    assert np.abs(A.istft(A.stft(dx, fps, win=16, hop=8)) - dx).max() < 1e-12
    assert np.isfinite(A.equivalent_level(dx, fps, "Z"))


# --------------------------------------------------------------------------- #
# 7. Ledger                                                                    #
# --------------------------------------------------------------------------- #
def test_ledger_is_complete_and_declares_real_types():
    assert opsacoustics.missing() == []
    assert len(opsacoustics.OPSACOUSTICS) == 19
    for name in opsacoustics.list_ops():
        m = opsacoustics.info(name)
        assert m["out"] in ("signal", "table", "measurement")
        # only existing sorts are used — no new type vocabulary was introduced
        assert all(i in ("signal", "table") for i in m["in"])
        assert m["doc"], name
    # istft is the one op that consumes a table: an invertible transform cannot
    # be a bare array, and complex_steerable_reconstruct sets the precedent
    assert opsacoustics.info("istft")["in"] == ["table"]
    assert opsacoustics.RESULT_ADAPTERS == {}


def test_ledger_declared_output_types_are_the_actual_types():
    fs = 25600.0
    x = A.synthesize_bearing_signal(fs, 0.5, 3000.0, 107.0)
    ramp = A.synthesize_speed_ramp(2000.0, 2.0, 600.0, 900.0, orders=(2.0,))
    produced = {
        "stft": A.stft(x, fs),
        "istft": A.istft(A.stft(x, fs)),
        "stft_cola_check": A.stft_cola_check(),
        "synthesize_bearing_signal": x,
        "synthesize_speed_ramp": ramp,
        "envelope_spectrum": A.envelope_spectrum(x, fs, 2000.0, 4000.0),
        "bearing_defect_frequencies": A.bearing_defect_frequencies(),
        "spectral_kurtosis": A.spectral_kurtosis(x, fs),
        "cepstrum": A.cepstrum(x, fs),
        "angular_resample": A.angular_resample(ramp["signal"], ramp["rate"],
                                               ramp["rpm"], 16),
        "order_spectrum": A.order_spectrum(ramp["signal"], ramp["rate"],
                                           ramp["rpm"], 16),
        "octave_bands": A.octave_bands(),
        "octave_spectrum": A.octave_spectrum(x, fs),
        "weighting_response": A.weighting_response(np.linspace(1.0, 8000.0, 64)),
        "apply_weighting": A.apply_weighting(x, fs),
        "equivalent_level": A.equivalent_level(x, fs),
        "percentile_level": A.percentile_level(x, fs, window_s=0.05),
        "coherence": A.coherence(x, x, fs),
        "transfer_function": A.transfer_function(x, x, fs),
    }
    checks = {
        "signal": lambda v: isinstance(v, np.ndarray) and v.ndim == 1,
        "table": lambda v: isinstance(v, (list, dict)),
        "measurement": lambda v: isinstance(v, (int, float, np.floating,
                                                np.integer)),
    }
    for name, value in produced.items():
        out = opsacoustics.info(name)["out"]
        assert checks[out](value), (name, out, type(value).__name__)


def test_every_op_survives_the_generic_signal_pool():
    """The type-vocabulary decision, asserted: an ordinary `signal` is valid
    acoustic input to every operator that takes one. Nothing is refused for
    being 'not acoustic enough' — which is why no new sort was added."""
    rng = np.random.default_rng(16)
    sig = np.sin(np.linspace(0, 8 * np.pi, 256)) + 0.1 * rng.standard_normal(256)
    rate = 100.0
    outputs = [
        A.stft(sig, rate), A.stft_cola_check(),
        A.envelope_spectrum(sig, rate, 0.05, 0.2),
        A.spectral_kurtosis(sig, rate), A.cepstrum(sig, rate),
        A.angular_resample(sig, rate, 60.0),
        A.order_spectrum(sig, rate, 60.0),
        A.octave_spectrum(sig, rate), A.weighting_response(sig),
        A.apply_weighting(sig, rate), A.percentile_level(sig, rate,
                                                         window_s=0.5),
        A.coherence(sig, sig, rate), A.transfer_function(sig, sig, rate),
    ]
    for o in outputs:
        arrays = ([o] if isinstance(o, np.ndarray)
                  else [v for v in o.values() if isinstance(v, np.ndarray)])
        for a in arrays:
            assert a.size == 0 or np.isfinite(a).all()
    assert np.isfinite(A.equivalent_level(sig, rate))


# --------------------------------------------------------------------------- #
# 8. Adversarial: the cases that returned a plausible *wrong* number           #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad", ["16000", True, np.True_, 16000 + 0j,
                                 np.str_("16000"), np.complex128(16000)])
def test_a_rate_that_is_not_a_number_is_refused(bad):
    """float('16000') succeeds, so without this an unparsed config value
    silently becomes a sample rate and every frequency below is wrong."""
    x = _noise(512, seed=17)
    for call in (lambda: A.stft(x, bad),
                 lambda: A.equivalent_level(x, bad),
                 lambda: A.cepstrum(x, bad),
                 lambda: A.octave_spectrum(x, bad),
                 lambda: A.apply_weighting(x, bad),
                 lambda: A.coherence(x, x, bad)):
        with pytest.raises(ValueError):
            call()


@pytest.mark.parametrize("call", [
    lambda: A.synthesize_bearing_signal(8000.0, 0.5, 5000.0, 100.0),
    lambda: A.synthesize_bearing_signal(8000.0, 0.5, 3990.0, 100.0),
    lambda: A.synthesize_speed_ramp(1000.0, 2.0, 600.0, 6000.0, orders=(5.0,)),
    lambda: A.envelope_spectrum(_noise(512), 100.0, 10.0, 60.0),
    lambda: A.octave_spectrum(_noise(512), 100.0, f_max=200.0),
    lambda: A.angular_resample(_noise(4096), 100.0, 1800.0, 64),
    lambda: A.order_spectrum(_noise(4096), 1000.0, 60.0, 64, max_order=99.0),
])
def test_above_nyquist_is_refused_never_folded(call):
    with pytest.raises(ValueError):
        call()


def test_the_upper_modulation_sideband_is_checked_not_just_the_carrier():
    A.synthesize_bearing_signal(8000.0, 0.2, 3800.0, 100.0)     # 3900 < 4000
    with pytest.raises(ValueError, match="sideband"):
        A.synthesize_bearing_signal(8000.0, 0.2, 3950.0, 100.0)  # 4050 > 4000


@pytest.mark.parametrize("call", [
    lambda: A.stft(np.array([1.0, np.nan, 2.0, 3.0]), 100.0),
    lambda: A.stft(np.array([1.0, np.inf, 2.0, 3.0]), 100.0),
    lambda: A.stft(np.array([1 + 1j, 2 + 0j, 3 + 0j, 4 + 0j]), 100.0),
    lambda: A.stft(np.ma.masked_invalid(np.array([1.0, np.nan, 2.0, 3.0])), 100.0),
    lambda: A.stft(np.ones((4, 4)), 100.0),
    lambda: A.equivalent_level(_noise(512), 100.0, ref=0.0),
    lambda: A.equivalent_level(_noise(512), 100.0, ref=-1.0),
    lambda: A.bearing_defect_frequencies(1800.0, 9, 40.0, 8.0),
    lambda: A.bearing_defect_frequencies(1800.0, 9, 8.0, 40.0,
                                         contact_angle_deg=90.0),
    lambda: A.synthesize_bearing_signal(16000.0, 0.2, 2000.0, 50.0,
                                        modulation=1.5),
    lambda: A.stft(_noise(512), 100.0, win=64, hop=128),
    lambda: A.angular_resample(_noise(4096), 1000.0, 0.0),
    lambda: A.cepstrum(np.zeros(512), 100.0),
    lambda: A.octave_bands(3, 1000.0, 100.0),
    lambda: A.percentile_level(_noise(256), 100.0, window_s=100.0),
])
def test_fail_closed_refusals(call):
    with pytest.raises(ValueError):
        call()


def test_a_speed_profile_that_touches_zero_is_refused():
    """Shaft angle is the integral of speed, so a zero rate makes the angle
    axis non-monotonic and the interpolation would walk backwards through it."""
    rpm = np.concatenate([np.full(2048, 60.0), np.zeros(2048)])
    with pytest.raises(ValueError, match="non-monotonic"):
        A.angular_resample(_noise(4096), 1000.0, rpm)


def test_a_single_frame_coherence_is_refused_not_returned_as_one():
    """Cauchy-Schwarz makes an unaveraged coherence identically 1.0 — a perfect
    score carrying no information whatsoever."""
    with pytest.raises(ValueError, match="identically"):
        A.coherence(_noise(256), _noise(256, seed=1), 16000.0, win=256)


def test_two_channels_of_different_length_are_refused():
    with pytest.raises(ValueError):
        A.coherence(_noise(4096), _noise(2048), 16000.0)


def test_a_magnitude_spectrogram_cannot_be_inverted():
    tr = A.stft(_noise(1024), 16000.0)
    tr["spectra"] = np.abs(tr["spectra"])
    with pytest.raises(ValueError, match="not complex"):
        A.istft(tr)


def test_a_tampered_transform_dict_is_refused():
    tr = A.stft(_noise(1024), 16000.0)
    broken = dict(tr)
    broken["nfft"] = 512
    with pytest.raises(ValueError):
        A.istft(broken)
    del broken["window_values"]
    with pytest.raises(ValueError, match="missing"):
        A.istft(broken)


@pytest.mark.parametrize("call", [
    lambda: A.stft(_noise(1000), 16000.0, win=1 << 20, hop=1),
    lambda: A.stft(_noise(100000), 16000.0, win=65536, hop=1),
    lambda: A.stft(np.zeros((1 << 24) + 1, np.int8), 16000.0),
    lambda: A.stft(_noise(1000), 16000.0, win=256, nfft=1 << 20),
    lambda: A.coherence(_noise(100000), _noise(100000, 1), 16000.0,
                        win=65536, hop=1),
    lambda: A.octave_bands(24, 1e-300, 1e300),
])
def test_a_small_input_cannot_ask_for_a_huge_allocation(call):
    with pytest.raises(ValueError):
        call()


def test_the_size_cap_fires_before_the_float64_promotion():
    """An over-cap int8 record must be refused without being copied to float64
    first (8x). Checked by the message, which names the promotion."""
    big = np.zeros((1 << 24) + 1, np.int8)
    with pytest.raises(ValueError, match="before the float64 promotion"):
        A.stft(big, 16000.0)


def test_nfft_zero_padding_is_capped_but_ordinary_padding_still_works():
    A.stft(_noise(1000), 16000.0, win=256, nfft=2048)          # 8x is fine
    with pytest.raises(ValueError, match="MAX_NFFT_RATIO"):
        A.stft(_noise(1000), 16000.0, win=256, nfft=1 << 20)


def test_a_degenerate_input_still_yields_a_peak_frequency():
    """Regression for a *silently wrong number*, not for an exception.

    A constant signal band-passed over 100-2000 Hz has an envelope made of
    rounding error, and envelope_spectrum reported peak_freq = 8.0 Hz — a
    perfectly plausible number. It still does, because there is nothing invalid
    to refuse; what changed is that the returned band_fraction shows it."""
    r = A.envelope_spectrum(np.ones(2000), 16000.0, 100.0, 2000.0)
    assert r["peak_amplitude"] < 1e-9
    assert r["band_fraction"] < 1e-9               # the tell
    real = A.envelope_spectrum(
        A.synthesize_bearing_signal(25600.0, 1.0, 3000.0, 107.0), 25600.0,
        2000.0, 4000.0)
    assert real["band_fraction"] > 0.5             # nine orders of magnitude up


def test_nothing_leaks_a_non_finite_number():
    fs = 16000.0
    silent = np.zeros(4096)
    results = [
        A.octave_spectrum(silent, fs), A.percentile_level(silent, fs,
                                                          window_s=0.05),
        A.coherence(silent, silent, fs), A.transfer_function(silent, silent, fs),
        A.spectral_kurtosis(silent, fs),
        A.envelope_spectrum(np.ones(4096), fs, 100.0, 2000.0),
    ]
    for r in results:
        for v in r.values():
            if isinstance(v, np.ndarray) and v.dtype.kind in "fc":
                assert np.isfinite(v).all()
            elif isinstance(v, float):
                assert np.isfinite(v)
    assert np.isfinite(A.equivalent_level(silent, fs))
    assert np.isfinite(A.istft(A.stft(silent, fs))).all()


def test_silence_reports_the_floor_not_minus_infinity():
    assert A.equivalent_level(np.zeros(1000), 16000.0) == A.FLOOR_DB
    o = A.octave_spectrum(np.zeros(1000), 16000.0)
    assert o["clamped"].all() and np.all(o["levels"] == A.FLOOR_DB)


def test_a_single_sample_still_round_trips():
    x = np.array([3.25])
    assert A.istft(A.stft(x, 16000.0)) == pytest.approx(x)
