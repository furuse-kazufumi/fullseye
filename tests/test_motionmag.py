# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Ground-truth tests for motionmag — phase-based motion magnification.

This subject has an unusually strong ground truth, and the tests spend it. A
sinusoidal grating translated by a Fourier phase ramp has an *exactly* known
sub-pixel displacement, and that displacement can be read back out of the result
by an **independent** route — the argument of the DFT bin the grating sits on —
which shares no code with the operators under test. So the central claims are
checked as equalities, not as tolerances chosen to pass:

* the steerable decomposition round-trips to machine precision;
* magnifying by ``alpha`` multiplies the measured displacement by exactly
  ``alpha``, over gains from -4 to +20 and displacements from 0.01 to 0.5 px;
* a motion outside the pass-band is not magnified at all — gain 1.0 to twelve
  decimal places even at ``alpha = 100``;
* the displacement estimator is exact to rounding, and where it stops is a
  closed-form Bessel zero rather than an empirical tolerance;
* raising ``alpha`` costs image SNR, monotonically, and never buys motion SNR.

An adversarial block then attacks the operators the way the repository's
discipline asks: not for exceptions, but for **quiet wrong numbers** — swapped
units, string and bool scalars, aliasing, empty pass-bands, degenerate inputs,
and small arguments that ask for large allocations.
"""
import numpy as np
import pytest
from scipy import special

import motionmag as mm
import opsmotionmag

# --------------------------------------------------------------------------- #
# Constructed inputs with a closed-form answer                                 #
# --------------------------------------------------------------------------- #
H = W = 64
T = 64
FPS = 32.0
FREQ = 4.0                    # bin-centred: FREQ * T / FPS == 8, an integer
BAND = (3.0, 5.0)
CYC_X = 8                     # lambda_x = 64/8 = 8 px  -> r = 0.125 (band centre)
CYC_Y = 4                     # lambda_y = 64/4 = 16 px -> r = 0.0625 (band centre)
K_X = 2.0 * np.pi * CYC_X / W                 # rad/px of the horizontal grating


def truth(amplitude, freq=FREQ, t=T, fps=FPS):
    """The displacement synthesize_translation applies, in closed form."""
    return amplitude * np.sin(2.0 * np.pi * freq * np.arange(t) / fps)


def read_dx(video):
    """Independent displacement readout: the DFT phase of the known grating bin.

    Shares no code with motionmag's own estimator, so agreement between the two
    is evidence rather than tautology."""
    spec = np.fft.fft2(video, axes=(1, 2))
    return -np.unwrap(np.angle(spec[:, 0, CYC_X])) / (2.0 * np.pi * CYC_X / W)


def read_dy(video):
    spec = np.fft.fft2(video, axes=(1, 2))
    return -np.unwrap(np.angle(spec[:, CYC_Y, 0])) / (2.0 * np.pi * CYC_Y / H)


# --------------------------------------------------------------------------- #
# Functional gate: every op runs and returns its declared shape / finiteness    #
# --------------------------------------------------------------------------- #
def test_every_op_runs_and_returns_its_declared_type():
    vid = mm.synthesize_translation((32, 32), 32, 0.2, 4.0, 32.0, noise_sigma=0.01)
    checks = {
        "video": lambda v: isinstance(v, np.ndarray) and v.ndim == 3,
        "image2d": lambda v: isinstance(v, np.ndarray) and v.ndim == 2,
        "table": lambda v: isinstance(v, (list, dict)),
        "pairs": lambda v: isinstance(v, np.ndarray) and v.ndim == 2
        and v.shape[1] == 2,
    }
    args = {
        "synthesize_translation": (),
        "complex_steerable_decompose": (vid[0],),
        "complex_steerable_reconstruct": (mm.complex_steerable_decompose(vid[0]),),
        "temporal_bandpass": (vid, 3.0, 5.0, 32.0),
        "temporal_band_power": (vid, 3.0, 5.0, 32.0),
        "band_snr": (vid, 3.0, 5.0, 32.0),
        "motion_magnify": (vid, 2.0, 3.0, 5.0, 32.0),
        "phase_displacement": (vid, 3.0, 5.0, 32.0),
        "displacement_series": (vid, 3.0, 5.0, 32.0),
    }
    assert not opsmotionmag.missing()
    assert set(args) == set(opsmotionmag.OPSMOTIONMAG)
    for name, meta in opsmotionmag.OPSMOTIONMAG.items():
        out = opsmotionmag.call(name, *args[name])
        assert checks[meta["out"]](out), f"{name} does not match out={meta['out']}"
        if isinstance(out, np.ndarray) and out.dtype.kind in "fc":
            assert np.isfinite(out).all(), f"{name} leaked a non-finite value"
        if isinstance(out, dict):
            for k, v in out.items():
                if isinstance(v, np.ndarray) and v.dtype.kind in "fc":
                    assert np.isfinite(v).all(), f"{name}[{k}] leaked a non-finite"
                elif isinstance(v, float):
                    assert np.isfinite(v), f"{name}[{k}] is non-finite"


def test_ledger_declares_only_types_the_fuzzer_can_check():
    """The ledger must not invent an out type nobody produces or checks."""
    assert set(m["out"] for m in opsmotionmag.OPSMOTIONMAG.values()) == {
        "video", "image2d", "table", "pairs"}
    # `video` is a new vocabulary word, so something in this family must *make*
    # one, or it is a dead sort no chain can ever reach.
    producers = [n for n, m in opsmotionmag.OPSMOTIONMAG.items() if m["out"] == "video"]
    consumers = [n for n, m in opsmotionmag.OPSMOTIONMAG.items() if "video" in m["in"]]
    assert producers and consumers
    entry = [n for n, m in opsmotionmag.OPSMOTIONMAG.items()
             if m["out"] == "video" and not m["in"]]
    assert entry, "no op produces a video from nothing; the pool could never fill"
    # and it must reach back out into the pre-existing sorts
    assert {"image2d", "pairs"} <= {opsmotionmag.OPSMOTIONMAG[n]["out"]
                                    for n in consumers}


# --------------------------------------------------------------------------- #
# 1. The decomposition is an exact tight frame                                 #
# --------------------------------------------------------------------------- #
def test_steerable_round_trip_is_machine_precision():
    img = np.random.default_rng(0).random((64, 64))
    back = mm.complex_steerable_reconstruct(mm.complex_steerable_decompose(img))
    assert back.shape == img.shape
    assert np.abs(back - img).max() < 1e-14


@pytest.mark.parametrize("shape", [(32, 48), (31, 37), (5, 5), (128, 64)])
def test_steerable_round_trip_for_odd_and_non_square_frames(shape):
    """Even-sized grids have self-conjugate DFT points where the usual
    factor-of-two synthesis argument fails; odd ones do not. Both must be exact."""
    img = np.random.default_rng(1).random(shape)
    back = mm.complex_steerable_reconstruct(
        mm.complex_steerable_decompose(img, scales=3, orientations=2))
    assert np.abs(back - img).max() < 1e-14


def test_steerable_round_trip_over_the_whole_parameter_grid():
    rng = np.random.default_rng(2)
    worst = 0.0
    for scales in range(1, mm.MAX_SCALES + 1):
        for orientations in range(1, mm.MAX_ORIENTATIONS + 1):
            img = rng.random((32, 32))
            back = mm.complex_steerable_reconstruct(
                mm.complex_steerable_decompose(img, scales, orientations))
            worst = max(worst, float(np.abs(back - img).max()))
    assert worst < 1e-14, f"worst round-trip error {worst:g}"


def test_zeroing_a_band_removes_energy_and_the_rest_still_reconstructs():
    img = np.random.default_rng(3).random((32, 32))
    dec = mm.complex_steerable_decompose(img, 3, 2)
    kept = dict(dec)
    kept["bands"] = [np.zeros_like(b) if k == "band" else b
                     for b, k in zip(dec["bands"], dec["kinds"])]
    residual_only = mm.complex_steerable_reconstruct(kept)
    # dropping every oriented band must remove real energy but keep the mean
    assert residual_only.var() < img.var()
    assert abs(residual_only.mean() - img.mean()) < 1e-12


# --------------------------------------------------------------------------- #
# 2. The synthetic itself is exact (otherwise nothing below means anything)     #
# --------------------------------------------------------------------------- #
def test_synthetic_translation_matches_its_closed_form():
    vid = mm.synthesize_translation((H, W), T, 0.5, FREQ, FPS)
    assert np.abs(read_dx(vid) - truth(0.5)).max() < 1e-13
    assert np.abs(read_dy(vid)).max() < 1e-13


def test_synthetic_translation_respects_the_direction_argument():
    vid = mm.synthesize_translation((H, W), T, 0.5, FREQ, FPS, direction_deg=90.0)
    assert np.abs(read_dy(vid) - truth(0.5)).max() < 1e-13
    assert np.abs(read_dx(vid)).max() < 1e-13


def test_synthetic_noise_is_seeded_and_reproducible():
    a = mm.synthesize_translation((16, 16), 8, 0.1, 2.0, 16.0, noise_sigma=0.05, seed=4)
    b = mm.synthesize_translation((16, 16), 8, 0.1, 2.0, 16.0, noise_sigma=0.05, seed=4)
    c = mm.synthesize_translation((16, 16), 8, 0.1, 2.0, 16.0, noise_sigma=0.05, seed=5)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


# --------------------------------------------------------------------------- #
# 3. The headline claim: magnified displacement is exactly alpha * d            #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("alpha", [0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 20.0,
                                   -1.0, -2.0, -4.0])
@pytest.mark.parametrize("d", [0.01, 0.05, 0.2, 0.5])
def test_magnified_displacement_is_alpha_times_d(alpha, d):
    if abs(alpha - 1.0) * K_X * d >= np.pi:
        pytest.skip("outside the linear regime by construction (|gain*k*d| >= pi)")
    vid = mm.synthesize_translation((H, W), T, d, FREQ, FPS)
    res = mm.motion_magnify(vid, alpha, BAND[0], BAND[1], FPS)
    err = float(np.abs(read_dx(res["video"]) - alpha * truth(d)).max())
    assert err < 1e-12, f"alpha={alpha} d={d}: max abs error {err:g}"
    if alpha != 0.0:
        assert err / abs(alpha * d) < 1e-11


def test_alpha_one_is_the_identity_even_on_a_noisy_clip():
    vid = mm.synthesize_translation((H, W), T, 0.2, FREQ, FPS,
                                    noise_sigma=0.03, seed=5)
    res = mm.motion_magnify(vid, 1.0, BAND[0], BAND[1], FPS)
    assert np.abs(res["video"] - vid).max() < 1e-14


def test_alpha_zero_removes_the_in_band_motion():
    vid = mm.synthesize_translation((H, W), T, 0.5, FREQ, FPS)
    res = mm.motion_magnify(vid, 0.0, BAND[0], BAND[1], FPS)
    assert np.abs(read_dx(res["video"])).max() < 1e-12


def test_the_sign_of_the_gain_is_not_flipped():
    """A reversed sign would still give |alpha|*d and pass an amplitude test."""
    vid = mm.synthesize_translation((H, W), T, 0.3, FREQ, FPS)
    plus = read_dx(mm.motion_magnify(vid, 3.0, *BAND, FPS)["video"])
    minus = read_dx(mm.motion_magnify(vid, -3.0, *BAND, FPS)["video"])
    assert np.abs(plus + minus).max() < 1e-12          # exact mirror image
    assert np.corrcoef(plus, truth(0.3))[0, 1] > 0.999  # and +alpha is *forward*


def test_the_vertical_channel_is_magnified_independently():
    vid = mm.synthesize_translation((H, W), T, 0.3, FREQ, FPS, direction_deg=90.0)
    res = mm.motion_magnify(vid, 5.0, *BAND, FPS)
    assert np.abs(read_dy(res["video"]) - 5.0 * truth(0.3)).max() < 1e-12
    assert np.abs(read_dx(res["video"])).max() < 1e-12


# --------------------------------------------------------------------------- #
# 4. The control: a motion outside the pass-band is not touched                 #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("alpha", [1.0, 4.0, 16.0, 100.0])
def test_out_of_band_motion_is_not_magnified(alpha):
    """Same clip, same alpha, motion moved from 4 Hz to 12 Hz: gain must be 1."""
    vid = mm.synthesize_translation((H, W), T, 0.5, 12.0, FPS)
    res = mm.motion_magnify(vid, alpha, BAND[0], BAND[1], FPS)
    out = read_dx(res["video"])
    assert np.abs(out - truth(0.5, freq=12.0)).max() < 1e-12
    assert abs(float(np.abs(out).max()) / 0.5 - 1.0) < 1e-11


def test_the_pass_band_actually_selects():
    """Widening the band to include 12 Hz must magnify what the narrow one did not."""
    vid = mm.synthesize_translation((H, W), T, 0.2, 12.0, FPS)
    narrow = mm.motion_magnify(vid, 3.0, 3.0, 5.0, FPS)
    wide = mm.motion_magnify(vid, 3.0, 11.0, 13.0, FPS)
    assert np.abs(read_dx(narrow["video"]) - truth(0.2, freq=12.0)).max() < 1e-12
    assert np.abs(read_dx(wide["video"]) - 3.0 * truth(0.2, freq=12.0)).max() < 1e-12


# --------------------------------------------------------------------------- #
# 5. Temporal filters against Parseval                                         #
# --------------------------------------------------------------------------- #
def test_temporal_bandpass_recovers_one_component_exactly():
    t = np.arange(T)
    wanted = np.sin(2.0 * np.pi * 4.0 * t / FPS)
    mixed = 0.5 + wanted + 0.3 * np.cos(2.0 * np.pi * 12.0 * t / FPS)
    vid = np.tile(mixed[:, None, None], (1, 8, 8))
    got = mm.temporal_bandpass(vid, 3.0, 5.0, FPS)
    assert np.abs(got[:, 0, 0] - wanted).max() < 1e-13
    assert abs(float(got.mean())) < 1e-14        # DC is always removed


def test_temporal_band_power_equals_half_the_squared_amplitude():
    t = np.arange(T)
    for a in (0.05, 0.3, 2.0):
        sig = 1.0 + a * np.sin(2.0 * np.pi * 4.0 * t / FPS)
        vid = np.tile(sig[:, None, None], (1, 8, 8))
        power = mm.temporal_band_power(vid, 3.0, 5.0, FPS)
        assert abs(float(power[0, 0]) - a * a / 2.0) < 1e-15 * max(a * a, 1.0)
        # a component outside the band contributes nothing
        out = mm.temporal_band_power(vid, 11.0, 13.0, FPS)
        assert float(np.abs(out).max()) < 1e-28


# --------------------------------------------------------------------------- #
# 6. Honesty: what magnification costs                                         #
# --------------------------------------------------------------------------- #
def _snr_ladder(noise_sigma, seed=11, alphas=(1.0, 2.0, 4.0, 8.0)):
    vid = mm.synthesize_translation((H, W), T, 0.2, FREQ, FPS,
                                    noise_sigma=noise_sigma, seed=seed)
    return [mm.motion_magnify(vid, a, *BAND, FPS) for a in alphas]


@pytest.mark.parametrize("sigma", [0.002, 0.005, 0.01, 0.02, 0.05])
def test_image_snr_falls_monotonically_as_alpha_rises(sigma):
    """Raising the gain always costs image SNR. Measured, not asserted."""
    ladder = [r["snr_out"]["image_snr_db"] for r in _snr_ladder(sigma)]
    steps = [ladder[i] - ladder[i + 1] for i in range(len(ladder) - 1)]
    assert all(s > 0.0 for s in steps), ladder
    # No step may exceed 20*log10(2) = 6.02 dB, the asymptote the algebra gives
    # once the amplified band dominates the noise budget. The *early* steps fall
    # short of it by design and that is not a defect: when the pass-band starts
    # out below the broadband noise floor (large sigma), doubling the band only
    # doubles a small part of the total fluctuation. Measured first steps:
    # 5.92 dB at sigma=0.002 down to 0.17 dB at sigma=0.05.
    assert all(s < 6.03 for s in steps), steps
    assert steps[-1] > 4.0, steps          # by the last doubling the band leads


def test_magnification_never_improves_the_motion_snr():
    """The claim that would be a lie if it were not enforced."""
    for sigma in (0.005, 0.01, 0.02):
        for res in _snr_ladder(sigma):
            assert res["motion_snr_change_db"] <= 1e-9, (
                sigma, res["alpha"], res["motion_snr_change_db"])


def test_reading_motion_snr_off_the_output_would_have_claimed_an_improvement():
    """Pin the trap that the gain correction exists to close.

    band_snr estimates the in-band noise floor from out-of-band bins, which
    magnification does not touch. Taken at face value on a magnified clip it
    reports a large improvement that did not happen; motion_snr_out_db is the
    corrected figure and must not."""
    res = _snr_ladder(0.01, alphas=(2.0,))[0]
    naive = res["snr_out"]["motion_snr_db"] - res["snr_in"]["motion_snr_db"]
    assert naive > 3.0, "the trap has stopped reproducing; re-check the estimator"
    assert res["motion_snr_change_db"] <= 1e-9


def test_band_power_ratio_reports_departure_from_linearity():
    vid = mm.synthesize_translation((H, W), T, 0.2, FREQ, FPS,
                                    noise_sigma=0.01, seed=7)
    ratios = [mm.motion_magnify(vid, a, *BAND, FPS)["band_power_ratio"]
              for a in (1.0, 2.0, 4.0, 8.0)]
    assert abs(ratios[0] - 1.0) < 1e-9              # alpha=1 is exactly linear
    assert all(ratios[i] > ratios[i + 1] for i in range(len(ratios) - 1))
    assert ratios[-1] < 0.8


def test_phase_shift_rms_is_linear_in_the_gain():
    vid = mm.synthesize_translation((H, W), T, 0.2, FREQ, FPS)
    rms = [mm.motion_magnify(vid, a, *BAND, FPS)["phase_shift_rms_rad"]
           for a in (1.0, 2.0, 4.0, 8.0)]
    assert rms[0] == 0.0
    for gain, r in zip((1.0, 3.0, 7.0), rms[1:]):
        assert abs(r / gain - rms[1]) < 1e-9 * max(rms[1], 1e-9)


def test_linear_regime_flag_turns_off_when_the_phase_folds():
    vid = mm.synthesize_translation((H, W), T, 0.5, FREQ, FPS)
    assert mm.motion_magnify(vid, 2.0, *BAND, FPS)["linear_regime"]
    assert not mm.motion_magnify(vid, 20.0, *BAND, FPS)["linear_regime"]


def test_band_snr_clamps_instead_of_returning_inf_or_nan():
    static = np.tile(np.random.default_rng(0).random((16, 16))[None], (32, 1, 1))
    got = mm.band_snr(static, 3.0, 5.0, FPS)
    assert got["motion_snr_db"] == mm.MIN_SNR_DB
    assert got["image_snr_db"] == mm.MAX_SNR_DB
    assert got["snr_clamped"] is True
    zero = mm.band_snr(np.zeros((32, 16, 16)), 3.0, 5.0, FPS)
    assert zero["motion_snr_db"] == mm.MIN_SNR_DB
    assert zero["image_snr_db"] == mm.MIN_SNR_DB
    for v in (got, zero):
        assert all(np.isfinite(x) for x in v.values()
                   if isinstance(x, float))


# --------------------------------------------------------------------------- #
# 7. Measurement accuracy, and the closed form of where it stops                #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("d", [0.001, 0.01, 0.1, 0.5, 1.0, 2.0, 3.0, 3.05])
def test_displacement_is_exact_below_the_bessel_limit(d):
    """Sub-pixel accuracy is limited by floating point, not by the method —
    right up to the point where the phase reference degenerates."""
    assert K_X * d < 2.4048                      # inside the valid region
    vid = mm.synthesize_translation((H, W), T, d, FREQ, FPS)
    series = mm.displacement_series(vid, *BAND, FPS)
    measured = float(np.abs(series[:, 0]).max())
    assert abs(measured - d) / d < 1e-13, f"d={d}: measured {measured!r}"
    assert float(np.abs(series[:, 1]).max()) < 1e-14 * max(d, 1.0)


@pytest.mark.parametrize("d", [3.1, 4.0, 6.0])
def test_displacement_breaks_past_the_bessel_limit_and_says_so(d):
    """Past the first zero of J0(k*A) the temporal-mean phase reference flips
    sign. The estimate is then wrong — and the returned coherence has already
    fallen far enough to warn about it."""
    assert K_X * d > 2.4048
    vid = mm.synthesize_translation((H, W), T, d, FREQ, FPS)
    series = mm.displacement_series(vid, *BAND, FPS)
    measured = float(np.abs(series[:, 0]).max())
    assert abs(measured - d) / d > 0.2, "the failure has stopped reproducing"
    assert mm.phase_displacement(vid, *BAND, FPS)["reference_coherence"] < 0.7


def test_reference_coherence_tracks_the_bessel_function():
    """The diagnostic is not a fudge factor: it is |J0(k*A)| for this synthetic."""
    coh = []
    for d in (0.001, 0.1, 0.5, 1.0, 2.0, 3.0):
        vid = mm.synthesize_translation((H, W), T, d, FREQ, FPS)
        coh.append(mm.phase_displacement(vid, *BAND, FPS)["reference_coherence"])
        assert coh[-1] <= 1.0 + 1e-12
    assert all(coh[i] > coh[i + 1] for i in range(len(coh) - 1)), coh
    assert coh[0] > 0.999                                    # J0(0.0008) ~ 1
    # the horizontal bands see |J0(k*A)| while the (still) vertical ones see 1,
    # so the blend sits between them and must not exceed either
    assert special.j0(K_X * 3.0) < coh[-1] < 1.0


def test_wrap_limit_is_the_measured_local_frequency_not_a_guess():
    vid = mm.synthesize_translation((H, W), T, 0.1, FREQ, FPS)
    got = mm.phase_displacement(vid, *BAND, FPS)["wrap_limit_px"]
    assert abs(got - np.pi / K_X) < 1e-9          # pi / (2*pi/8) = 4.0 px exactly


def test_displacement_under_noise_degrades_gracefully():
    for sigma, bound in ((0.001, 1e-3), (0.01, 1e-2), (0.05, 5e-2)):
        vid = mm.synthesize_translation((H, W), T, 0.5, FREQ, FPS,
                                        noise_sigma=sigma, seed=3)
        measured = float(np.abs(mm.displacement_series(vid, *BAND, FPS)[:, 0]).max())
        assert abs(measured - 0.5) / 0.5 < bound


def test_aperture_problem_returns_the_observable_component_not_zeros():
    """A purely horizontal grating constrains only horizontal motion. Returning
    zeros would throw away the component that *was* measured; inverting a
    singular system would return a fantasy for the one that was not."""
    x = np.arange(64)
    base = 0.5 + 0.2 * np.cos(2.0 * np.pi * 8 * x / 64)[None, :] * np.ones((64, 1))
    fu = np.fft.fftfreq(64)[None, :]
    spec = np.fft.fft2(base)
    clip = np.stack([np.real(np.fft.ifft2(spec * np.exp(-2j * np.pi * fu * dd)))
                     for dd in truth(0.3)])
    field = mm.phase_displacement(clip, *BAND, FPS)
    assert (field["rank"] == 1).all()
    series = mm.displacement_series(clip, *BAND, FPS)
    assert abs(float(np.abs(series[:, 0]).max()) - 0.3) < 1e-12
    assert float(np.abs(series[:, 1]).max()) == 0.0
    assert np.isfinite(series).all()


def test_measurement_and_magnification_agree_on_a_broadband_texture():
    """Off the synthetic, the narrow-band condition costs accuracy. Pin how much
    so a regression cannot quietly make it worse."""
    from scipy import ndimage
    base = ndimage.gaussian_filter(np.random.default_rng(2).random((64, 64)), 1.5)
    fu = np.fft.fftfreq(64)[None, :]
    spec = np.fft.fft2(base)
    clip = np.stack([np.real(np.fft.ifft2(spec * np.exp(-2j * np.pi * fu * dd)))
                     for dd in truth(0.2)])
    measured = float(np.abs(mm.displacement_series(clip, *BAND, FPS)[:, 0]).max())
    assert abs(measured - 0.2) / 0.2 < 5e-3          # measurement stays good
    res = mm.motion_magnify(clip, 3.0, *BAND, FPS)
    got = float(np.abs(mm.displacement_series(res["video"], *BAND, FPS)[:, 0]).max())
    assert 0.55 < got < 0.60                         # 3*0.2 = 0.6, ~5.5 % short
    assert res["band_power_ratio"] < 1.0


# --------------------------------------------------------------------------- #
# 8. Adversarial: quiet wrong numbers, not exceptions                          #
# --------------------------------------------------------------------------- #
GOOD = mm.synthesize_translation((32, 32), 32, 0.2, 4.0, 32.0,
                                 noise_sigma=0.01, seed=1)


@pytest.mark.parametrize("bad", ["30", b"30", True, np.True_, 3 + 0j,
                                 np.complex128(3), np.str_("30")])
def test_scalar_arguments_refuse_strings_bools_and_complex(bad):
    """float('30') succeeds and True == 1, so without an explicit refusal an
    unparsed config value or a stray flag becomes a plausible frame rate."""
    with pytest.raises(ValueError):
        mm.temporal_bandpass(GOOD, 3.0, 5.0, bad)
    with pytest.raises(ValueError):
        mm.motion_magnify(GOOD, bad, 3.0, 5.0, 32.0)


@pytest.mark.parametrize("bad", [True, 2.0, "2", None])
def test_integer_arguments_refuse_non_integers(bad):
    with pytest.raises(ValueError):
        mm.motion_magnify(GOOD, 2.0, 3.0, 5.0, 32.0, scales=bad)


@pytest.mark.parametrize("bad", [0.0, -1.0, -32.0])
def test_zero_or_negative_frame_rate_is_refused(bad):
    with pytest.raises(ValueError):
        mm.temporal_bandpass(GOOD, 3.0, 5.0, bad)


def test_a_pass_band_touching_dc_is_refused():
    """f_lo = 0 would scale the *static* phase — where the scene is, not how it
    moves — and produce an enormous, entirely fictitious displacement."""
    with pytest.raises(ValueError, match="static phase"):
        mm.motion_magnify(GOOD, 2.0, 0.0, 5.0, 32.0)


def test_an_empty_or_inverted_pass_band_is_refused():
    with pytest.raises(ValueError):
        mm.temporal_bandpass(GOOD, 4.0, 4.0, 32.0)
    with pytest.raises(ValueError):
        mm.temporal_bandpass(GOOD, 5.0, 3.0, 32.0)
    # a band narrower than the clip's frequency resolution holds no DFT bin, so
    # the filter would silently return zeros
    with pytest.raises(ValueError, match="no DFT bin"):
        mm.temporal_bandpass(GOOD, 4.2, 4.4, 32.0)


def test_a_temporal_frequency_above_nyquist_is_refused_not_folded():
    with pytest.raises(ValueError, match="Nyquist"):
        mm.temporal_bandpass(GOOD, 3.0, 20.0, 32.0)
    with pytest.raises(ValueError, match="Nyquist"):
        mm.temporal_bandpass(GOOD, 3.0, 1000.0, 32.0)
    with pytest.raises(ValueError, match="Nyquist"):
        mm.synthesize_translation((32, 32), 32, 0.5, 30.0, 32.0)
    # the classic swap: fps and the band exchanged
    with pytest.raises(ValueError, match="Nyquist"):
        mm.temporal_bandpass(GOOD, 3.0, 5.0, 4.0)


def test_band_snr_refuses_when_no_bin_is_left_to_estimate_noise_from():
    with pytest.raises(ValueError, match="out-of-band bin"):
        mm.band_snr(GOOD, 1e-9, 16.0, 32.0)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_non_finite_scalars_are_refused(bad):
    with pytest.raises(ValueError):
        mm.motion_magnify(GOOD, bad, 3.0, 5.0, 32.0)


def test_non_finite_samples_are_refused_rather_than_propagated():
    for poison in (np.nan, np.inf):
        bad = GOOD.copy()
        bad[3, 4, 5] = poison
        with pytest.raises(ValueError, match="non-finite"):
            mm.temporal_bandpass(bad, 3.0, 5.0, 32.0)


def test_complex_and_masked_clips_are_refused():
    with pytest.raises(ValueError, match="complex"):
        mm.temporal_bandpass(GOOD.astype(complex), 3.0, 5.0, 32.0)
    with pytest.raises(ValueError, match="masked"):
        mm.temporal_bandpass(np.ma.masked_greater(GOOD, 0.6), 3.0, 5.0, 32.0)


@pytest.mark.parametrize("clip,match", [
    (np.zeros((1, 8, 8)), "at least 2"),
    (np.zeros((8, 8)), "T, H, W"),
    (np.zeros((4, 8, 8, 1)), "T, H, W"),
    (np.zeros((8, 2, 2)), "at least 4x4"),
    ([], "empty frame list"),
    ([np.zeros((8, 8)), np.zeros((8, 9))], "differing shapes"),
])
def test_degenerate_clip_shapes_are_refused(clip, match):
    with pytest.raises(ValueError, match=match):
        mm.temporal_bandpass(clip, 3.0, 5.0, 32.0)


def test_a_list_of_frames_is_accepted_like_videops_documents():
    got = mm.temporal_bandpass(list(GOOD), 3.0, 5.0, 32.0)
    assert np.allclose(got, mm.temporal_bandpass(GOOD, 3.0, 5.0, 32.0))


def test_degenerate_content_returns_zeros_not_garbage():
    """A static clip, a constant image and an all-zero clip have no motion to
    magnify and no phase to measure. None of them may produce a number."""
    static = np.tile(GOOD[0][None], (32, 1, 1))
    assert np.abs(mm.motion_magnify(static, 50.0, 3.0, 5.0, 32.0)["video"]
                  - static).max() < 1e-12
    for clip in (np.full((32, 16, 16), 0.5), np.zeros((32, 16, 16))):
        res = mm.motion_magnify(clip, 50.0, 3.0, 5.0, 32.0)
        assert np.isfinite(res["video"]).all()
        assert np.abs(res["video"] - clip).max() < 1e-12
        series = mm.displacement_series(clip, 3.0, 5.0, 32.0)
        assert series.shape == (32, 2)
        assert not series.any()


def test_small_arguments_cannot_ask_for_a_large_allocation():
    """Every one of these is a few characters of input and gigabytes of output."""
    with pytest.raises(ValueError, match="MAX_FRAMES"):
        mm.temporal_bandpass(np.zeros((100000, 4, 4)), 3.0, 5.0, 32.0)
    with pytest.raises(ValueError, match=r"\[1, 8\]"):
        mm.motion_magnify(GOOD, 2.0, 3.0, 5.0, 32.0, scales=64)
    with pytest.raises(ValueError, match=r"\[1, 16\]"):
        mm.motion_magnify(GOOD, 2.0, 3.0, 5.0, 32.0, orientations=1000)
    with pytest.raises(ValueError, match="over the"):
        # 300 MB of virtual clip from a single zero, via a zero-stride view
        mm.motion_magnify(np.lib.stride_tricks.as_strided(
            np.zeros(1), (300, 1024, 1024), (0, 0, 0)), 2.0, 3.0, 5.0, 32.0)
    with pytest.raises(ValueError, match="cap"):
        mm.synthesize_translation((8192, 8192), 4, 0.5, 4.0, 32.0)
    with pytest.raises(ValueError, match=r"\[2, 4096\]"):
        mm.synthesize_translation((8, 8), 10 ** 7, 0.5, 4.0, 32.0)
    with pytest.raises(ValueError, match="MAX_ALPHA"):
        mm.motion_magnify(GOOD, 1e9, 3.0, 5.0, 32.0)


def test_a_tampered_decomposition_is_refused():
    dec = mm.complex_steerable_decompose(np.zeros((16, 16)), 2, 2)
    with pytest.raises(ValueError, match="band was added or dropped"):
        mm.complex_steerable_reconstruct({**dec, "bands": dec["bands"][:-1]})
    with pytest.raises(ValueError, match="expected"):
        mm.complex_steerable_reconstruct(
            {**dec, "bands": [np.zeros((8, 8))] * len(dec["bands"])})
    with pytest.raises(ValueError, match="expected"):
        mm.complex_steerable_reconstruct({**dec, "shape": (8, 8)})
    with pytest.raises(ValueError, match="non-finite"):
        mm.complex_steerable_reconstruct(
            {**dec, "bands": [np.full((16, 16), np.nan)] + list(dec["bands"][1:])})
    with pytest.raises(ValueError, match="missing"):
        mm.complex_steerable_reconstruct({"bands": dec["bands"]})
    with pytest.raises(ValueError, match="expected the dict"):
        mm.complex_steerable_reconstruct([1, 2, 3])
    with pytest.raises(ValueError, match="complex"):
        mm.complex_steerable_decompose(np.zeros((16, 16), complex))


def test_results_do_not_depend_on_the_clip_being_in_zero_to_one():
    """Magnification must be affine-equivariant: offsetting or scaling the whole
    clip may not change the displacement it reports."""
    vid = mm.synthesize_translation((H, W), T, 0.2, FREQ, FPS)
    for transform in (lambda v: v - 5.0, lambda v: v * 1e6, lambda v: v * 1e-6):
        res = mm.motion_magnify(transform(vid), 4.0, *BAND, FPS)
        got = mm.displacement_series(res["video"], *BAND, FPS)
        assert abs(float(np.abs(got[:, 0]).max()) - 0.8) < 1e-9
        assert np.isfinite(res["video"]).all()


def test_the_filter_cache_cannot_grow_without_bound():
    for size in range(8, 8 + mm._FILTER_CACHE_MAX + 4):
        mm.complex_steerable_decompose(np.zeros((size, size)), 2, 2)
    assert len(mm._FILTER_CACHE) <= mm._FILTER_CACHE_MAX


if __name__ == "__main__":       # pragma: no cover
    pytest.main([__file__, "-q"])
