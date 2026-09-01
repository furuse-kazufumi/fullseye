# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""photoncount — closed-form ground truth, sign conventions, and the fail-closed contract.

Photon counting is one of the rare corners of imaging where the *answer* is
known analytically, so this suite is built around exact identities rather than
golden files:

  * a Poisson realisation has ``variance == mean`` (Fano 1) and
    ``SNR = sqrt(N)``;
  * the algebraic Anscombe inverse is the exact inverse of the transform, and
    the variance-stabilisation / bias tables are computed **exactly** from the
    Poisson pmf (no sampling, so they are reproducible by anyone);
  * the non-paralysable dead-time law and its correction are exact inverses;
  * Coates's estimator is the **exact** inverse of the first-photon pile-up
    model, so a synthetic piled-up histogram returns the true rates to machine
    precision;
  * a synthetic dToF return at a known distance ``d`` puts its pulse at
    ``t = 2d/c``, and the centroid recovers ``d`` to float round-off;
  * a noiseless exponential decay has an exactly linear log, so the log-linear
    lifetime fit is exact;
  * a single-exponential phasor sits on the universal semicircle
    ``(g-1/2)^2 + s^2 = 1/4``, and a two-component decay sits strictly inside it.

Every randomised check fixes the seed and states, in a comment, the sample size
and the sampling distribution of the statistic it asserts on — a tolerance
without that derivation is a wish, not a test.

Scale invariance is checked in two independent ways wherever the physics has a
scale (two bin widths, two distances, two dead times, two lifetimes), so a unit
mix-up cannot hide behind a single lucky constant.

The classes at the end pin the bugs the 2026-09-01 adversarial pass found, each
with the minimal reproduction that exposed it.
"""
import os
import sys
import warnings

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import photoncount as PC  # noqa: E402
import opsphoton  # noqa: E402

C = PC.SPEED_OF_LIGHT_M_S


def _poisson_pmf(lam, k):
    """Poisson pmf without scipy.stats, via gammaln (exact enough for a table)."""
    from scipy.special import gammaln
    return np.exp(k * np.log(lam) - lam - gammaln(k + 1.0))


def _decay_hist(tau_ps, n_bins, bin_ps, total_counts):
    """A noiseless decay whose bins are the **exact integral** of exp(-t/tau).

    Bin integration multiplies every bin by the same constant, so the log slope
    is still exactly ``-1/tau`` — that is what makes the lifetime fit exact and
    is worth building explicitly rather than sampling the exponential.
    """
    edges = np.arange(n_bins + 1, dtype=np.float64) * bin_ps
    integ = tau_ps * (np.exp(-edges[:-1] / tau_ps) - np.exp(-edges[1:] / tau_ps))
    return total_counts * integ / integ.sum()


# --------------------------------------------------------------------------- #
# counting: Poisson realisation                                                #
# --------------------------------------------------------------------------- #
def test_photon_sample_variance_equals_mean():
    """The defining property of a Poisson process, on 512x512 = 262144 pixels.

    Sampling distribution of the Fano factor for a flat field:
    ``sd(s^2/mean) ~ sqrt((2 + 1/lambda)/n)`` = sqrt(2.01/262144) = 2.8e-3, so
    0.02 is a 7-sigma band. Measured at seed 0: 1.001089.
    """
    counts = PC.photon_sample(np.ones((512, 512)), 100.0, seed=0)
    st = PC.photon_statistics(counts)
    assert st["mean"] == pytest.approx(100.0, abs=0.1)
    assert st["fano_factor"] == pytest.approx(1.0, abs=0.02)
    assert st["fano_factor"] == pytest.approx(1.001089, abs=1e-5)   # pinned
    # SNR = sqrt(N): the theoretical value and the achieved one must agree.
    assert st["snr_poisson"] == pytest.approx(np.sqrt(st["mean"]), rel=1e-12)
    assert st["snr_measured"] == pytest.approx(st["snr_poisson"], rel=0.01)


@pytest.mark.parametrize("lam", [1.0, 10.0, 1000.0])
def test_photon_sample_snr_grows_as_sqrt_n(lam):
    """Three decades of exposure: SNR must track sqrt(lambda), not lambda."""
    counts = PC.photon_sample(np.ones((256, 256)), lam, seed=7)
    st = PC.photon_statistics(counts)
    # sd(mean) = sqrt(lam/n); with n = 65536 that is 0.4% of sqrt(lam) at worst.
    assert st["snr_measured"] == pytest.approx(np.sqrt(lam), rel=0.03)


def test_photon_sample_is_deterministic_per_seed():
    a = PC.photon_sample(np.ones((16, 16)), 20.0, seed=3)
    b = PC.photon_sample(np.ones((16, 16)), 20.0, seed=3)
    c = PC.photon_sample(np.ones((16, 16)), 20.0, seed=4)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_photon_sample_returns_integers_and_respects_dark_rate():
    counts = PC.photon_sample(np.zeros((128, 128)), 100.0, dark_rate=5.0, seed=1)
    assert np.array_equal(counts, np.round(counts))       # counts, not levels
    # A dark frame still counts: mean must sit at the dark rate.
    # sd(mean) = sqrt(5/16384) = 0.017, so 0.1 is ~6 sigma.
    assert counts.mean() == pytest.approx(5.0, abs=0.1)


def test_photon_statistics_zero_fraction_matches_exp_minus_lambda():
    """For a flat field the fraction of empty pixels is exactly exp(-lambda)."""
    for lam in (0.5, 2.0):
        st = PC.photon_statistics(PC.photon_sample(np.ones((512, 512)), lam,
                                                   seed=11))
        # sd of a proportion p over n = 262144: sqrt(p(1-p)/n) <= 1e-3.
        assert st["zero_fraction"] == pytest.approx(np.exp(-lam), abs=0.005)


def test_photon_statistics_fano_is_meaningless_on_a_structured_scene():
    """The honest limitation, pinned as a test so the docstring cannot drift."""
    flat = PC.photon_statistics(PC.photon_sample(np.ones((512, 512)), 100.0,
                                                 seed=0))
    ramp_img = 0.2 + 1.6 * (np.mgrid[0:512, 0:512][1] / 511.0)
    ramp = PC.photon_statistics(PC.photon_sample(ramp_img, 100.0, seed=1))
    assert flat["fano_factor"] == pytest.approx(1.0, abs=0.02)
    assert ramp["fano_factor"] == pytest.approx(22.4102, rel=1e-4)   # pinned
    assert ramp["fano_factor"] > 20.0        # scene variance, not detector noise


def test_photon_uncertainty_is_sqrt_n_and_its_reciprocal_is_snr():
    counts = np.array([[1.0, 4.0], [9.0, 100.0]])
    assert np.allclose(PC.photon_uncertainty(counts), [[1.0, 2.0], [3.0, 10.0]])
    rel = PC.photon_uncertainty(counts, relative=True)
    assert np.allclose(rel, 1.0 / np.sqrt(counts))
    assert np.allclose(1.0 / rel, np.sqrt(counts))           # SNR = sqrt(N)


def test_photon_uncertainty_zero_floor_is_opt_in():
    z = np.zeros((2, 2))
    assert np.allclose(PC.photon_uncertainty(z), 0.0)            # default: honest 0
    assert np.allclose(PC.photon_uncertainty(z, zero_floor=1.0), 1.0)
    with pytest.raises(ValueError, match="1/sqrt"):
        PC.photon_uncertainty(z, relative=True)                  # no silent inf


# --------------------------------------------------------------------------- #
# transform: Anscombe                                                          #
# --------------------------------------------------------------------------- #
def test_anscombe_classical_form_is_the_textbook_formula():
    x = np.linspace(0.0, 50.0, 36).reshape(6, 6)
    assert np.allclose(PC.anscombe_transform(x), 2.0 * np.sqrt(x + 0.375),
                       rtol=0.0, atol=0.0)                     # bit-identical


def test_anscombe_algebraic_inverse_is_exact():
    x = np.linspace(0.0, 1e4, 100001).reshape(-1, 1)
    back = PC.anscombe_inverse(PC.anscombe_transform(x))
    assert np.abs(back - x).max() < 1e-11                        # measured 2.7e-12
    big = x > 1.0
    assert (np.abs(back - x)[big] / x[big]).max() < 1e-15        # measured 3.7e-16


@pytest.mark.parametrize("gain,sigma,offset", [(2.0, 3.0, 100.0),
                                               (0.5, 1.5, 0.0),
                                               (1.0, 0.0, 0.0)])
def test_generalised_anscombe_round_trips_at_every_calibration(gain, sigma, offset):
    x = np.linspace(offset, offset + 500.0, 64).reshape(8, 8)
    A = PC.anscombe_transform(x, gain, sigma, offset)
    back = PC.anscombe_inverse(A, gain, sigma, offset)
    assert np.allclose(back, x, rtol=1e-12, atol=1e-9)


def test_generalised_anscombe_reduces_to_the_classical_form():
    x = np.arange(64.0).reshape(8, 8)
    assert np.allclose(PC.anscombe_transform(x, 1.0, 0.0, 0.0),
                       PC.anscombe_transform(x), rtol=0.0, atol=0.0)


@pytest.mark.parametrize("lam,expected", [(1.0, 0.717443), (2.0, 0.924297),
                                          (4.0, 0.998754), (10.0, 1.000910),
                                          (100.0, 1.000006)])
def test_anscombe_variance_stabilisation_exact_table(lam, expected):
    """var(A(X)) for X~Poisson(lambda), summed exactly over the pmf.

    No sampling: this is the table in the docstring and anyone can reproduce it.
    It is also the honest low-count story — 0.717 at lambda = 1 is NOT 1.
    """
    k = np.arange(0, int(lam + 40.0 * np.sqrt(lam) + 40.0), dtype=np.float64)
    p = _poisson_pmf(lam, k)
    a = 2.0 * np.sqrt(k + 0.375)
    var = float((p * a * a).sum() - (p * a).sum() ** 2)
    assert var == pytest.approx(expected, abs=1e-6)


def test_anscombe_variance_stabilisation_holds_on_real_samples():
    """The sampled counterpart of the exact table (seed 3, 262144 pixels).

    sd of a sample variance around 1 over n = 262144 is ~sqrt(2/n) = 2.8e-3,
    so abs=0.02 is a 7-sigma band.
    """
    for lam, expected in ((4.0, 0.998754), (100.0, 1.000006)):
        s = PC.photon_sample(np.ones((512, 512)), lam, seed=3)
        assert float(PC.anscombe_transform(s).var()) == pytest.approx(expected,
                                                                      abs=0.02)
    # ...and fails to hold at 1 photon/pixel, which is the documented limit.
    s1 = PC.photon_sample(np.ones((512, 512)), 1.0, seed=3)
    assert float(PC.anscombe_transform(s1).var()) < 0.80


@pytest.mark.parametrize("lam,alg_bias,unb_bias", [(1.0, -0.179361, -0.003668),
                                                   (4.0, -0.249688, +0.003779),
                                                   (10.0, -0.250227, +0.016904),
                                                   (100.0, -0.250002, +0.011960)])
def test_anscombe_unbiased_inverse_beats_the_algebraic_one(lam, alg_bias, unb_bias):
    """Apply each inverse to the ideal denoised value D = E[A(X)], exactly."""
    k = np.arange(0, int(lam + 40.0 * np.sqrt(lam) + 40.0), dtype=np.float64)
    D = float((_poisson_pmf(lam, k) * 2.0 * np.sqrt(k + 0.375)).sum())
    d2 = np.array([[D]])
    got_alg = float(PC.anscombe_inverse(d2, mode="algebraic")[0, 0]) - lam
    got_unb = float(PC.anscombe_inverse(d2, mode="unbiased")[0, 0]) - lam
    assert got_alg == pytest.approx(alg_bias, abs=1e-5)
    assert got_unb == pytest.approx(unb_bias, abs=1e-5)
    assert abs(got_unb) < abs(got_alg)              # the whole point of the mode


def test_anscombe_unbiased_inverse_root_is_exactly_a_of_zero():
    """The closed form's positive root coincides with A(0) = 2*sqrt(3/8).

    That is why the clip at 0 essentially never fires: over the whole valid
    domain the formula is non-negative to round-off (measured min -1.11e-16).
    Below A(0) it IS genuinely negative (-0.0217 at D = 1.20), which is why
    those values are refused instead of clipped.
    """
    a0 = 2.0 * np.sqrt(0.375)
    r32 = np.sqrt(1.5)
    raw = lambda d: (d * d / 4.0 + 0.25 * r32 / d - 1.375 / d ** 2      # noqa: E731
                     + 0.625 * r32 / d ** 3 - 0.125)
    assert raw(a0) == pytest.approx(0.0, abs=1e-15)
    d = np.linspace(a0, 6.0, 20001).reshape(-1, 1)
    assert float(raw(d).min()) > -1e-12          # only round-off is negative
    assert (PC.anscombe_inverse(d, mode="unbiased") >= 0.0).all()
    assert raw(1.20) == pytest.approx(-0.0217, rel=0.01)   # genuinely negative
    with pytest.raises(ValueError, match="did not come from anscombe_transform"):
        PC.anscombe_inverse(np.full((2, 2), -1.0), mode="unbiased")


def test_anscombe_unbiased_refuses_the_generalised_parameters():
    v = np.full((2, 2), 4.0)
    with pytest.raises(ValueError, match="CLASSICAL"):
        PC.anscombe_inverse(v, gain=2.0, mode="unbiased")
    with pytest.raises(ValueError, match="CLASSICAL"):
        PC.anscombe_inverse(v, read_sigma=1.0, mode="unbiased")


def test_anscombe_negative_argument_is_refused_unless_clipped():
    x = np.full((2, 2), -10.0)
    with pytest.raises(ValueError, match="negative argument"):
        PC.anscombe_transform(x)
    assert np.allclose(PC.anscombe_transform(x, clip=True), 0.0)


# --------------------------------------------------------------------------- #
# spad: dead time                                                              #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("tau_ns", [10.0, 50.0, 100.0])
def test_deadtime_apply_and_correct_are_exact_inverses(tau_ns):
    n = np.logspace(3.0, np.log10(0.7 / (tau_ns * 1e-9)), 2000)
    m = PC.spad_deadtime_apply(n, tau_ns)
    assert (np.abs(PC.spad_deadtime_correct(m, tau_ns) - n) / n).max() < 1e-14


def test_deadtime_halves_the_rate_at_one_over_tau():
    """Closed form: m = n/(1+n*tau) gives exactly n/2 when n*tau = 1."""
    for tau_ns in (10.0, 50.0):
        n = np.array([1.0 / (tau_ns * 1e-9)])
        assert PC.spad_deadtime_apply(n, tau_ns)[0] == pytest.approx(n[0] / 2.0,
                                                                     rel=1e-15)


def test_paralyzable_law_peaks_at_one_over_e_tau_and_then_falls():
    """The reason no paralysable inverse exists: the law is not injective."""
    tau_ns = 50.0
    tau = tau_ns * 1e-9
    n = np.array([0.5 / tau, 1.0 / tau, 2.0 / tau, 4.0 / tau])
    m = PC.spad_deadtime_apply(n, tau_ns, paralyzable=True)
    assert m[1] == pytest.approx(1.0 / (np.e * tau), rel=1e-12)   # exact maximum
    assert m[1] > m[0] and m[1] > m[2] > m[3]                     # rises, then falls
    # Two different true rates give (nearly) the same measured rate — the branch
    # ambiguity, demonstrated rather than asserted in prose.
    lo = PC.spad_deadtime_apply(np.array([0.2 / tau]), tau_ns, paralyzable=True)[0]
    hi_grid = np.linspace(1.01, 6.0, 20000) / tau
    hi = PC.spad_deadtime_apply(hi_grid, tau_ns, paralyzable=True)
    assert np.abs(hi - lo).min() / lo < 1e-3


def test_deadtime_correct_refuses_a_saturated_rate():
    tau_ns = 50.0
    with pytest.raises(ValueError, match="saturation rate"):
        PC.spad_deadtime_correct(np.array([1.0 / (tau_ns * 1e-9)]), tau_ns)
    with pytest.raises(ValueError, match="saturation rate"):
        PC.spad_deadtime_correct(np.array([1e9]), tau_ns)


def test_deadtime_is_negligible_at_low_rates():
    n = np.array([1e3, 1e4])
    assert np.allclose(PC.spad_deadtime_apply(n, 50.0), n, rtol=1e-3)


# --------------------------------------------------------------------------- #
# spad: Coates pile-up correction                                              #
# --------------------------------------------------------------------------- #
def _piled_up(lam, cycles):
    """The forward first-photon TCSPC model: N_k = C*exp(-sum_{j<k} lam_j)
    *(1 - exp(-lam_k)). Coates is its exact inverse."""
    prior = np.concatenate(([0.0], np.cumsum(lam)[:-1]))
    return cycles * np.exp(-prior) * (1.0 - np.exp(-lam))


@pytest.mark.parametrize("cycles", [10000, 1000000])
def test_coates_is_the_exact_inverse_of_the_pileup_model(cycles):
    lam = np.linspace(0.30, 0.02, 12)
    measured = _piled_up(lam, cycles)
    recovered = PC.tcspc_coates_correct(measured, cycles)
    truth = cycles * lam
    assert (np.abs(recovered - truth) / truth).max() < 1e-13     # measured 1.6e-15


def test_coates_undoes_a_severe_late_bin_suppression():
    """Pile-up is not a small correction: the last bin here reads 14.8% of truth."""
    lam = np.linspace(0.30, 0.02, 12)
    cycles = 100000
    measured = _piled_up(lam, cycles)
    truth = cycles * lam
    assert measured[-1] / truth[-1] == pytest.approx(0.1481, abs=1e-3)
    assert measured[0] / truth[0] == pytest.approx(0.8639, abs=1e-3)
    rec = PC.tcspc_coates_correct(measured, cycles)
    assert np.allclose(rec, truth, rtol=1e-12)
    # The correction must ADD counts to late bins (sign check).
    assert (rec >= measured - 1e-9).all()


def test_coates_biases_a_depth_short_and_the_correction_fixes_it():
    """The reason this op is in the dToF family, not just the FLIM one."""
    bin_ps, bins, cycles = 100.0, 256, 200000
    d = 2.4371
    lam = PC.tcspc_simulate(d, bins=bins, bin_ps=bin_ps, signal_photons=0.6,
                            ambient_photons=0.2, irf_fwhm_ps=500.0, noise=False)
    measured = _piled_up(lam, cycles)
    biased = PC.dtof_depth(measured, bin_ps, mode="centroid",
                           subtract_background=True)
    fixed = PC.dtof_depth(PC.tcspc_coates_correct(measured, cycles), bin_ps,
                          mode="centroid", subtract_background=True)
    assert biased < d                       # pile-up pulls the return earlier
    assert abs(fixed - d) < abs(biased - d) / 5.0


def test_coates_refuses_impossible_inputs():
    with pytest.raises(ValueError, match="only 100 excitation cycle"):
        PC.tcspc_coates_correct(np.array([80.0, 40.0]), 100)
    with pytest.raises(ValueError, match=r"p = 1"):
        PC.tcspc_coates_correct(np.array([100.0, 0.0, 0.0]), 100)


# --------------------------------------------------------------------------- #
# tcspc: histograms                                                            #
# --------------------------------------------------------------------------- #
def test_tcspc_simulate_puts_the_pulse_at_two_d_over_c():
    d, bin_ps, bins = 2.4371, 100.0, 256
    h = PC.tcspc_simulate(d, bins=bins, bin_ps=bin_ps, signal_photons=1000.0,
                          ambient_photons=0.0, irf_fwhm_ps=500.0, noise=False)
    t0 = 2.0 * d / C * 1e12
    st = PC.tcspc_stats(h, bin_ps)
    assert st["centroid_ps"] == pytest.approx(t0, abs=1e-9)      # measured 1.8e-12
    assert st["peak_bin"] == int(t0 // bin_ps)


def test_tcspc_simulate_expectation_is_the_photon_budget():
    h = PC.tcspc_simulate(1.5, bins=256, bin_ps=100.0, signal_photons=800.0,
                          ambient_photons=200.0, irf_fwhm_ps=300.0, noise=False)
    assert float(h.sum()) == pytest.approx(1000.0, rel=1e-9)


def test_tcspc_simulate_poisson_realisation_matches_its_expectation():
    """Total counts over 20 seeds must scatter as Poisson around the budget."""
    lam_total = 1000.0
    totals = np.array([PC.tcspc_simulate(1.5, bins=256, signal_photons=800.0,
                                         ambient_photons=200.0, seed=s).sum()
                       for s in range(20)])
    # sd(total) = sqrt(1000) = 31.6; sd(mean of 20) = 7.07, so 4 sigma is 28.
    assert totals.mean() == pytest.approx(lam_total, abs=28.0)


@pytest.mark.parametrize("bin_ps,bins", [(100.0, 256), (25.0, 1024)])
def test_tcspc_simulate_is_scale_invariant_in_the_time_axis(bin_ps, bins):
    """Same window, four times finer bins: same distance must come back."""
    d = 2.4371
    h = PC.tcspc_simulate(d, bins=bins, bin_ps=bin_ps, signal_photons=1000.0,
                          ambient_photons=0.0, irf_fwhm_ps=500.0, noise=False)
    assert PC.dtof_depth(h, bin_ps, mode="centroid") == pytest.approx(d, abs=1e-12)


def test_tcspc_simulate_refuses_a_target_outside_the_unambiguous_range():
    with pytest.raises(ValueError, match="unambiguous range"):
        PC.tcspc_simulate(10.0, bins=64, bin_ps=100.0)


def test_irf_convolve_reproduces_the_requested_width_and_does_not_move_the_pulse():
    spike = np.zeros(256)
    spike[128] = 1.0
    out = PC.tcspc_irf_convolve(spike, bin_ps=50.0, irf_fwhm_ps=500.0)
    st = PC.tcspc_stats(out, 50.0)
    assert st["centroid_ps"] == pytest.approx(128.5 * 50.0, abs=1e-9)  # unmoved
    assert float(out.sum()) == pytest.approx(1.0, abs=1e-9)            # counts kept
    # 501.22 not 500: the FWHM *estimator* interpolates linearly between bins and
    # overestimates a Gaussian by 0.24%. Pinned so the docstring cannot drift.
    assert st["fwhm_ps"] == pytest.approx(501.22, abs=0.05)


def test_irf_convolve_widths_add_in_quadrature():
    """Two Gaussian blurs compose: FWHM_total^2 = FWHM_a^2 + FWHM_b^2."""
    spike = np.zeros(512)
    spike[256] = 1.0
    once = PC.tcspc_irf_convolve(PC.tcspc_irf_convolve(spike, 25.0, 300.0),
                                 25.0, 400.0)
    direct = PC.tcspc_irf_convolve(spike, 25.0, np.hypot(300.0, 400.0))
    # Not exact: each kernel is truncated at +-4 sigma and renormalised, so the
    # composition is only Gaussian to that approximation. Measured max absolute
    # difference 2.7e-05 against a peak of 0.0469 = 0.06% of the peak.
    assert np.abs(once - direct).max() < 5e-5
    assert PC.tcspc_stats(once, 25.0)["fwhm_ps"] == pytest.approx(
        PC.tcspc_stats(direct, 25.0)["fwhm_ps"], rel=1e-3)


def test_irf_convolve_refuses_a_sub_bin_kernel_instead_of_doing_nothing():
    with pytest.raises(ValueError, match="silently do nothing"):
        PC.tcspc_irf_convolve(np.ones(16), bin_ps=100.0, irf_fwhm_ps=0.01)


def test_background_subtract_recovers_a_known_pedestal_exactly():
    pulse = PC.tcspc_simulate(2.4371, bins=256, bin_ps=100.0,
                              signal_photons=5000.0, ambient_photons=0.0,
                              irf_fwhm_ps=500.0, noise=False)
    h = pulse + 20.0
    assert PC.tcspc_stats(h, 100.0)["background_per_bin"] == pytest.approx(20.0,
                                                                           abs=1e-9)
    out = PC.tcspc_background_subtract(h, "median")
    assert np.allclose(out, pulse, rtol=0.0, atol=1e-12)     # exactly the pulse
    assert float(out.sum()) == pytest.approx(5000.0, rel=1e-9)


def test_background_subtract_is_a_subtraction_not_an_addition():
    """The sign trap, pinned."""
    h = np.array([5.0, 5.0, 5.0, 50.0, 5.0, 5.0])
    out = PC.tcspc_background_subtract(h, "median")
    assert np.allclose(out, [0.0, 0.0, 0.0, 45.0, 0.0, 0.0])
    assert out.sum() < h.sum()


@pytest.mark.parametrize("method,expected", [("median", 20.0), ("leading", 20.0),
                                             ("quantile", 20.0)])
def test_background_methods_agree_on_a_clean_pedestal(method, expected):
    pulse = PC.tcspc_simulate(3.0, bins=256, bin_ps=100.0, signal_photons=5000.0,
                              ambient_photons=0.0, irf_fwhm_ps=500.0, noise=False)
    out = PC.tcspc_background_subtract(pulse + expected, method)
    assert float(out.sum()) == pytest.approx(5000.0, rel=1e-6)


def test_tcspc_stats_fwhm_is_none_for_a_monotone_decay():
    """A decay peaks at bin 0, so there is no left half-crossing — say None."""
    st = PC.tcspc_stats(_decay_hist(2000.0, 256, 100.0, 10000.0), 100.0)
    assert st["fwhm_ps"] is None
    assert st["peak_bin"] == 0


def test_tcspc_stats_sbr_and_signal_counts_are_consistent():
    pulse = PC.tcspc_simulate(2.0, bins=256, bin_ps=100.0, signal_photons=4000.0,
                              ambient_photons=0.0, irf_fwhm_ps=400.0, noise=False)
    st = PC.tcspc_stats(pulse + 10.0, 100.0)
    assert st["signal_counts"] == pytest.approx(4000.0, rel=1e-6)
    assert st["sbr"] == pytest.approx(4000.0 / (10.0 * 256), rel=1e-6)


def test_tcspc_stats_refuses_an_all_zero_histogram():
    with pytest.raises(ValueError, match="no photons"):
        PC.tcspc_stats(np.zeros(16), 100.0)


# --------------------------------------------------------------------------- #
# dtof: distance                                                               #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("d", [0.5, 2.4371, 3.5])
def test_dtof_depth_recovers_a_known_distance_noiselessly(d):
    h = PC.tcspc_simulate(d, bins=256, bin_ps=100.0, signal_photons=1000.0,
                          ambient_photons=0.0, irf_fwhm_ps=500.0, noise=False)
    assert PC.dtof_depth(h, 100.0, "centroid") == pytest.approx(d, abs=1e-12)
    assert PC.dtof_depth(h, 100.0, "gaussian") == pytest.approx(d, abs=1e-4)
    # "peak" is quantised to the bin grid: half a bin is c*dt/4 = 7.5 mm.
    assert abs(PC.dtof_depth(h, 100.0, "peak") - d) <= C * 100e-12 / 4.0 + 1e-12


def test_dtof_estimator_ranking_noiseless_and_noisy():
    """Pins the docstring table, and the honest reversal it contains."""
    d = 2.4371
    clean = PC.tcspc_simulate(d, bins=256, bin_ps=100.0, signal_photons=1000.0,
                              ambient_photons=0.0, irf_fwhm_ps=500.0, noise=False)
    err = {m: abs(PC.dtof_depth(clean, 100.0, m) - d)
           for m in ("peak", "centroid", "parabolic", "gaussian")}
    assert err["centroid"] < err["gaussian"] < err["parabolic"] < err["peak"]
    assert err["peak"] == pytest.approx(1.286e-3, rel=0.02)
    assert err["gaussian"] < 1e-7

    noisy = PC.tcspc_simulate(d, bins=256, bin_ps=100.0, signal_photons=200.0,
                              ambient_photons=200.0, irf_fwhm_ps=500.0, seed=0)
    nerr = {m: abs(PC.dtof_depth(noisy, 100.0, m,
                                 subtract_background=(m == "centroid")) - d)
            for m in ("peak", "centroid", "parabolic", "gaussian")}
    # Shot noise flattens the ranking to ~1.7x, and the centroid collapses.
    assert nerr["gaussian"] < nerr["peak"] < nerr["centroid"]
    assert nerr["peak"] / nerr["gaussian"] < 3.0


def test_dtof_offset_is_subtracted_not_added():
    """The sign trap: a positive offset must bring the target CLOSER."""
    h = PC.tcspc_simulate(3.0, bins=256, bin_ps=100.0, signal_photons=1000.0,
                          ambient_photons=0.0, irf_fwhm_ps=500.0, noise=False)
    d0 = PC.dtof_depth(h, 100.0, "gaussian")
    d1 = PC.dtof_depth(h, 100.0, "gaussian", offset_ps=1000.0)
    assert d1 < d0
    assert d0 - d1 == pytest.approx(C * 1000e-12 / 2.0, rel=1e-9)
    with pytest.raises(ValueError, match="negative distance"):
        PC.dtof_depth(h, 100.0, offset_ps=1e6)


def test_dtof_bin_width_sets_the_depth_resolution():
    """c*dt/2 per bin: 100 ps = 1.499 cm, 25 ps = 0.375 cm."""
    d = 2.4371
    for bin_ps, bins in ((100.0, 256), (25.0, 1024)):
        h = PC.tcspc_simulate(d, bins=bins, bin_ps=bin_ps,
                              signal_photons=1000.0, ambient_photons=0.0,
                              irf_fwhm_ps=500.0, noise=False)
        assert abs(PC.dtof_depth(h, bin_ps, "peak") - d) <= C * bin_ps * 1e-12 / 4.0


def test_dtof_background_biases_the_centroid_toward_the_window_centre():
    """Why subtract_background exists, demonstrated instead of asserted."""
    d, bins, bin_ps = 1.0, 256, 100.0
    h = PC.tcspc_simulate(d, bins=bins, bin_ps=bin_ps, signal_photons=500.0,
                          ambient_photons=2000.0, irf_fwhm_ps=500.0, noise=False)
    mid = C * (bins * bin_ps * 0.5) * 1e-12 / 2.0
    raw = PC.dtof_depth(h, bin_ps, "centroid")
    fixed = PC.dtof_depth(h, bin_ps, "centroid", subtract_background=True)
    assert d < raw < mid                        # dragged toward the middle
    assert abs(fixed - d) < abs(raw - d) / 10.0


def test_dtof_refuses_a_subbin_mode_at_the_window_edge():
    h = np.zeros(16)
    h[0] = 10.0
    with pytest.raises(ValueError, match="bin on each side"):
        PC.dtof_depth(h, 100.0, "gaussian")
    assert PC.dtof_depth(h, 100.0, "peak") == pytest.approx(C * 50e-12 / 2.0)


# --------------------------------------------------------------------------- #
# dtof: the (H, W, T) cube                                                     #
# --------------------------------------------------------------------------- #
def _tilted_plane(h=16, w=16, near=1.0, far=3.0):
    return near + (far - near) * np.linspace(0.0, 1.0, w)[None, :] * np.ones((h, 1))


def test_cube_simulate_and_depth_round_trip_noiselessly():
    depth = _tilted_plane()
    cube = PC.dtof_cube_simulate(depth, bins=256, bin_ps=100.0,
                                 signal_photons=1000.0, ambient_photons=0.0,
                                 irf_fwhm_ps=500.0, noise=False)
    assert cube.shape == depth.shape + (256,)
    got = PC.dtof_cube_depth(cube, 100.0, "centroid")
    assert float(np.sqrt(((got - depth) ** 2).mean())) < 1e-12   # measured 3.2e-16
    peak = PC.dtof_cube_depth(cube, 100.0, "peak")
    assert (np.abs(peak - depth) <= C * 100e-12 / 4.0 + 1e-12).all()


def test_cube_depth_estimator_ranking_matches_the_single_pixel_one():
    depth = _tilted_plane(32, 32)
    cube = PC.dtof_cube_simulate(depth, bins=256, bin_ps=100.0,
                                 signal_photons=1000.0, ambient_photons=0.0,
                                 irf_fwhm_ps=500.0, noise=False)
    rms = {m: float(np.sqrt(((PC.dtof_cube_depth(cube, 100.0, m) - depth) ** 2).mean()))
           for m in ("peak", "centroid", "parabolic", "gaussian")}
    assert rms["centroid"] < rms["gaussian"] < rms["parabolic"] < rms["peak"]
    assert rms["peak"] == pytest.approx(4.388e-3, rel=0.02)      # pinned


def test_cube_depth_survives_photon_starvation():
    depth = _tilted_plane(32, 32)
    cube = PC.dtof_cube_simulate(depth, bins=256, bin_ps=100.0,
                                 signal_photons=20.0, ambient_photons=5.0,
                                 irf_fwhm_ps=500.0, seed=0)
    got = PC.dtof_cube_depth(cube, 100.0, "gaussian")
    rms = float(np.sqrt(((got - depth) ** 2).mean()))
    assert rms < 0.05                                # measured 19.2 mm
    assert np.isfinite(got).all()


def test_cube_depth_marks_empty_pixels_without_a_silent_nan():
    depth = _tilted_plane(8, 8)
    cube = PC.dtof_cube_simulate(depth, bins=128, bin_ps=200.0,
                                 signal_photons=50.0, ambient_photons=0.0,
                                 irf_fwhm_ps=400.0, noise=False)
    cube[0, 0, :] = 0.0                              # a dead pixel
    got = PC.dtof_cube_depth(cube, 200.0)
    assert got[0, 0] == 0.0                          # default marker, finite
    assert np.isfinite(got).all()
    nanned = PC.dtof_cube_depth(cube, 200.0, empty_value=float("nan"))
    assert np.isnan(nanned[0, 0]) and np.isfinite(nanned[1:, :]).all()


def test_cube_simulate_reflectivity_scales_the_signal_not_the_depth():
    depth = np.full((4, 4), 2.0)
    refl = np.linspace(0.1, 1.0, 16).reshape(4, 4)
    cube = PC.dtof_cube_simulate(depth, bins=128, bin_ps=200.0, reflectivity=refl,
                                 signal_photons=100.0, ambient_photons=0.0,
                                 irf_fwhm_ps=400.0, noise=False)
    assert np.allclose(cube.sum(axis=-1), 100.0 * refl, rtol=1e-9)
    got = PC.dtof_cube_depth(cube, 200.0, "centroid")
    assert np.allclose(got, 2.0, atol=1e-12)         # depth is reflectivity-free


def test_cube_simulate_caps_the_allocation():
    with pytest.raises(ValueError, match="MAX_CUBE_ELEMENTS"):
        PC.dtof_cube_simulate(np.full((512, 512), 2.0), bins=256)


def test_cube_depth_offset_is_subtracted_and_refuses_a_negative_flight_time():
    depth = _tilted_plane(4, 4)
    cube = PC.dtof_cube_simulate(depth, bins=256, bin_ps=100.0,
                                 signal_photons=500.0, ambient_photons=0.0,
                                 irf_fwhm_ps=500.0, noise=False)
    shifted = PC.dtof_cube_depth(cube, 100.0, "centroid", offset_ps=1000.0)
    base = PC.dtof_cube_depth(cube, 100.0, "centroid")
    assert np.allclose(base - shifted, C * 1000e-12 / 2.0, rtol=1e-9)
    with pytest.raises(ValueError, match="negative distance"):
        PC.dtof_cube_depth(cube, 100.0, offset_ps=1e6)


# --------------------------------------------------------------------------- #
# lifetime                                                                     #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("tau", [500.0, 2000.0, 6000.0])
def test_lifetime_fit_is_exact_on_a_noiseless_decay(tau):
    """log of an exponential is exactly linear -> the fit is exact, at any tau."""
    h = _decay_hist(tau, 256, 100.0, 10000.0)
    r = PC.lifetime_fit(h, 100.0, background=0.0, min_counts=0.0)
    assert r["lifetime_ps"] == pytest.approx(tau, rel=1e-9)
    assert r["r_squared"] == pytest.approx(1.0, abs=1e-12)


def test_lifetime_fit_is_unaffected_by_bin_integration_versus_sampling():
    """Bin integration scales every bin by the same constant -> same slope."""
    tau, n, dt = 2000.0, 256, 100.0
    integrated = _decay_hist(tau, n, dt, 10000.0)
    sampled = np.exp(-((np.arange(n) + 0.5) * dt) / tau) * 100.0
    a = PC.lifetime_fit(integrated, dt, background=0.0, min_counts=0.0)
    b = PC.lifetime_fit(sampled, dt, background=0.0, min_counts=0.0)
    assert a["lifetime_ps"] == pytest.approx(b["lifetime_ps"], rel=1e-9)


def test_lifetime_fit_bias_under_poisson_noise_is_documented_not_hidden():
    """Measured: +0.72% mean bias over seeds 0-19, sd 18.2 ps, at 20000 photons.

    This is the log-transform bias E[ln N] < ln E[N] in the sparse tail. It is
    pinned so that neither the docstring nor the estimator can drift silently.
    """
    tau, lam = 2000.0, _decay_hist(2000.0, 256, 100.0, 20000.0)
    got = np.array([PC.lifetime_fit(np.random.default_rng(s).poisson(lam).astype(float),
                                    100.0, background=0.0,
                                    min_counts=10.0)["lifetime_ps"]
                    for s in range(20)])
    assert got.mean() == pytest.approx(2014.3, abs=1.0)
    assert got.std() == pytest.approx(18.2, abs=1.0)
    assert 0.0 < (got.mean() - tau) / tau < 0.02        # small, positive, bounded


def test_lifetime_fit_starts_at_the_peak_by_default():
    """The rising edge is the IRF, not the decay.

    Measured direction (2000 ps decay, 600 ps IRF, 256 bins x 100 ps): including
    the four rising-edge bins FLATTENS the log slope, so the lifetime comes back
    **long** — 2100.7 ps (+5.0%) against 2008.0 ps (+0.40%) from the peak. Pinned
    with the numbers because the intuition ("the edge makes it look faster") is
    the opposite of what actually happens.
    """
    tau, dt = 2000.0, 100.0
    with_edge = PC.tcspc_irf_convolve(_decay_hist(tau, 256, dt, 10000.0), dt, 600.0)
    auto = PC.lifetime_fit(with_edge, dt, background=0.0, min_counts=1.0)
    forced = PC.lifetime_fit(with_edge, dt, background=0.0, min_counts=1.0,
                             start_bin=0)
    assert auto["start_bin"] == 4
    assert auto["lifetime_ps"] == pytest.approx(2008.0, abs=1.0)
    assert forced["lifetime_ps"] == pytest.approx(2100.7, abs=1.0)
    assert forced["lifetime_ps"] > auto["lifetime_ps"]        # biased LONG
    assert abs(auto["lifetime_ps"] - tau) < abs(forced["lifetime_ps"] - tau) / 10.0


def test_lifetime_fit_refuses_a_non_decaying_profile():
    with pytest.raises(ValueError, match="does not decay"):
        PC.lifetime_fit(np.linspace(10.0, 100.0, 32), 100.0, background=0.0,
                        min_counts=0.0, start_bin=0)


@pytest.mark.parametrize("tau", [800.0, 2000.0, 5000.0])
def test_phasor_lands_on_the_universal_semicircle(tau):
    """Closed form: g = 1/(1+(w*tau)^2), s = w*tau/(1+(w*tau)^2)."""
    n, dt = 1024, 25.0
    ph = PC.lifetime_phasor(_decay_hist(tau, n, dt, 10000.0), dt)
    w = ph["omega_per_ps"]
    assert w == pytest.approx(2.0 * np.pi / (n * dt), rel=1e-15)
    assert ph["g"] == pytest.approx(1.0 / (1.0 + (w * tau) ** 2), abs=2e-4)
    assert ph["s"] == pytest.approx(w * tau / (1.0 + (w * tau) ** 2), abs=2e-4)
    assert abs(ph["semicircle_residual"]) < 1e-4
    assert ph["tau_phi_ps"] == pytest.approx(tau, rel=2e-3)
    assert ph["tau_m_ps"] == pytest.approx(tau, rel=2e-3)


def test_phasor_discretisation_error_is_second_order_in_the_bin_width():
    """Quadrupling the bin count divides the residual by exactly 16, not by 4."""
    tau = 2000.0
    coarse = PC.lifetime_phasor(_decay_hist(tau, 256, 100.0, 1e4), 100.0)
    fine = PC.lifetime_phasor(_decay_hist(tau, 1024, 25.0, 1e4), 25.0)
    assert coarse["semicircle_residual"] == pytest.approx(6.07e-5, rel=0.02)
    assert fine["semicircle_residual"] == pytest.approx(3.79e-6, rel=0.02)
    ratio = coarse["semicircle_residual"] / fine["semicircle_residual"]
    assert ratio == pytest.approx(16.0, rel=0.01)


def test_phasor_detects_a_multi_exponential_decay_that_the_fit_cannot():
    """The honest companion to lifetime_fit: two components fall INSIDE."""
    n, dt = 256, 100.0
    single = PC.lifetime_phasor(_decay_hist(2000.0, n, dt, 1e4), dt)
    double = PC.lifetime_phasor(_decay_hist(500.0, n, dt, 5e3)
                                + _decay_hist(4000.0, n, dt, 5e3), dt)
    assert abs(single["semicircle_residual"]) < 1e-4
    assert double["semicircle_residual"] == pytest.approx(-0.0924, rel=0.02)
    assert double["semicircle_residual"] < -0.05                 # strictly inside
    # ...while lifetime_fit hands back one confident number for the same data.
    r = PC.lifetime_fit(_decay_hist(500.0, n, dt, 5e3)
                        + _decay_hist(4000.0, n, dt, 5e3), dt, background=0.0,
                        min_counts=0.0)
    assert 500.0 < r["lifetime_ps"] < 4000.0


def test_phasor_reports_none_rather_than_a_negative_lifetime():
    """All the mass in one late bin: the phase leaves (0, pi/2)."""
    h = np.zeros(8)
    h[2] = 7.0
    ph = PC.lifetime_phasor(h, 100.0)
    assert ph["tau_phi_ps"] is None
    assert ph["modulation"] == pytest.approx(1.0, rel=1e-12)
    assert ph["tau_m_ps"] is None                     # m = 1 -> not < 1


def test_phasor_refuses_a_harmonic_above_nyquist():
    with pytest.raises(ValueError, match="harmonic"):
        PC.lifetime_phasor(np.array([1.0, 2.0, 3.0, 4.0]), 100.0, harmonic=3)


# --------------------------------------------------------------------------- #
# composition with the rest of fullseye                                        #
# --------------------------------------------------------------------------- #
def test_photon_limited_image_composes_with_richardson_lucy():
    """The documented bridge: RL is the ML deblur under exactly this noise model.

    Not a claim about how well RL denoises — only that the Poisson data this
    module produces is valid input to volrestore, i.e. that the two families are
    wired to each other rather than duplicated.
    """
    import volrestore
    truth = np.zeros((16, 24, 24))
    truth[6:10, 8:16, 8:16] = 50.0
    psf = volrestore.vol_gaussian_psf(1.2)
    from scipy.signal import fftconvolve
    # fftconvolve leaves ~-2e-15 round-off negatives; photon_sample refuses them
    # by contract, so the clip is explicit here (that refusal is the point).
    blurred = np.maximum(fftconvolve(truth, psf, mode="same"), 0.0)
    noisy = np.stack([PC.photon_sample(blurred[z], 1.0, seed=z)
                      for z in range(blurred.shape[0])])
    out = volrestore.vol_richardson_lucy(noisy, psf, iterations=8)
    assert out.shape == truth.shape
    assert np.isfinite(out).all() and (out >= 0.0).all()
    # forward consistency is what RL optimises, and it must improve
    before = float(np.abs(fftconvolve(noisy, psf, mode="same") - noisy).mean())
    after = float(np.abs(fftconvolve(out, psf, mode="same") - noisy).mean())
    assert after < before


def test_anscombe_route_helps_a_threshold_not_a_linear_smoother():
    """The honest version of "the transform helps you denoise".

    Measured, seed 5, two-level scene (4 and 64 photons/pixel):

      * a plain **Gaussian** filter does slightly WORSE through the transform
        (2.459 vs 2.387) — averaging is already right for Poisson counts, so
        stabilising the variance first buys nothing;
      * a 5x5 **sigma filter**, whose parameter is an absolute noise scale, does
        much better through it (1.191 at a 3-sigma threshold) than in the raw
        domain using the same 3-sigma rule with a globally estimated sigma
        (2.307), because in the raw domain "3 sigma" is 6 photons in the dark
        region and 24 in the bright one and no single constant is right.

    Both halves are asserted, so the docstring cannot quietly become a boast.
    """
    from scipy.ndimage import gaussian_filter, generic_filter

    def sigma_filter(img, thresh, size=5):
        def f(w):
            c = w[len(w) // 2]
            return w[np.abs(w - c) <= thresh].mean()
        return generic_filter(img, f, size=size, mode="nearest")

    truth = np.full((64, 64), 4.0)
    truth[16:48, 16:48] = 64.0
    counts = PC.photon_sample(truth, 1.0, seed=5)
    rmse = lambda a: float(np.sqrt(((a - truth) ** 2).mean()))   # noqa: E731

    # (a) a linear smoother gains nothing — the honest half
    lin_direct = rmse(gaussian_filter(counts, 1.5))
    lin_via = rmse(PC.anscombe_inverse(
        gaussian_filter(PC.anscombe_transform(counts), 1.5), mode="unbiased"))
    assert lin_via > lin_direct

    # (b) an absolute-scale threshold gains a lot — the useful half
    a = PC.anscombe_transform(counts)
    via = rmse(PC.anscombe_inverse(sigma_filter(a, 3.0), mode="unbiased"))
    raw = rmse(sigma_filter(counts, 3.0 * np.sqrt(counts.mean())))
    assert via == pytest.approx(1.191, abs=0.02)
    assert raw == pytest.approx(2.307, abs=0.02)
    assert via < raw / 1.8
    assert via < rmse(counts)


def test_arrival_histogram_is_a_plain_1d_signal_for_dsp():
    """The histogram type is `signal`, so dsp/funct1d apply without a wrapper."""
    import dsp
    h = PC.tcspc_simulate(2.0, bins=256, bin_ps=100.0, signal_photons=400.0,
                          ambient_photons=200.0, seed=2)
    freq, mag = dsp.spectrum(h, 1.0 / 100e-12)
    assert freq.ndim == mag.ndim == 1 and freq.size == mag.size
    assert np.isfinite(mag).all()


# --------------------------------------------------------------------------- #
# ledger                                                                       #
# --------------------------------------------------------------------------- #
def test_ledger_has_every_op_and_no_ghosts():
    assert opsphoton.missing() == []
    assert set(opsphoton.OPSPHOTON) == set(PC.PHOTONCOUNT)
    assert set(PC.PHOTONCOUNT) == set(PC.__all__) - {
        "PHOTONCOUNT", "SPEED_OF_LIGHT_M_S", "FWHM_PER_SIGMA", "MAX_BINS",
        "MAX_IMAGE_ELEMENTS", "MAX_CUBE_ELEMENTS", "MAX_LAMBDA", "DEPTH_MODES",
        "ANSCOMBE_INVERSE_MODES", "BACKGROUND_METHODS"}
    assert len(opsphoton.OPSPHOTON) == 17
    assert len(opsphoton.categories()) == 6


def test_ledger_out_types_match_the_actual_return_values():
    """The TYPEMISS check: call() must return exactly what the ledger declares."""
    depth = _tilted_plane(8, 8)
    hist = PC.tcspc_simulate(2.0, bins=128, bin_ps=200.0, signal_photons=500.0,
                             ambient_photons=100.0, seed=0)
    decay = _decay_hist(2000.0, 128, 200.0, 5000.0)
    counts = PC.photon_sample(np.ones((8, 8)) * 0.5, 40.0, seed=0)
    rates = np.linspace(1e4, 1e6, 32)
    cube = PC.dtof_cube_simulate(depth, bins=128, bin_ps=200.0, noise=False)
    args = {
        "photon_sample": (counts,), "photon_statistics": (counts,),
        "photon_uncertainty": (counts,),
        "anscombe_transform": (counts,),
        "anscombe_inverse": (PC.anscombe_transform(counts),),
        "spad_deadtime_apply": (rates,), "spad_deadtime_correct": (rates,),
        # (the two above are the only countrate consumers; see the ledger notes)
        "tcspc_coates_correct": (hist, 100000),
        "tcspc_simulate": (), "tcspc_irf_convolve": (hist,),
        "tcspc_background_subtract": (hist,), "tcspc_stats": (hist,),
        "dtof_depth": (hist, 200.0),
        "dtof_cube_simulate": (depth,), "dtof_cube_depth": (cube, 200.0),
        "lifetime_fit": (decay, 200.0), "lifetime_phasor": (decay, 200.0),
    }
    # Exactly the TYPE_CHECKS entries tools/chain_fuzz.py needs for this family.
    # Kept in sync here so a ledger edit cannot drift away from the fuzzer.
    checks = {
        "image2d": lambda v: isinstance(v, np.ndarray) and v.ndim == 2,
        "depth": lambda v: isinstance(v, np.ndarray) and v.ndim == 2,
        "table": lambda v: isinstance(v, (list, dict)),
        "measurement": lambda v: isinstance(v, (int, float, np.floating,
                                                np.integer)),
        "counts": lambda v: isinstance(v, np.ndarray) and v.ndim == 1
        and v.dtype.kind == "f" and v.size >= 2 and (v >= 0.0).all(),
        "countrate": lambda v: isinstance(v, np.ndarray) and v.ndim == 1
        and v.dtype.kind == "f" and v.size >= 1 and (v >= 0.0).all(),
        "histcube": lambda v: isinstance(v, np.ndarray) and v.ndim == 3
        and v.dtype.kind == "f" and v.shape[2] >= 2 and (v >= 0.0).all(),
    }
    assert set(args) == set(opsphoton.OPSPHOTON)
    for name, a in args.items():
        out_t = opsphoton.OPSPHOTON[name]["out"]
        assert out_t in checks, name
        val = opsphoton.call(name, *a)
        assert checks[out_t](val), (name, out_t, type(val))
    assert opsphoton.RESULT_ADAPTERS == {}      # no op needs one, on purpose


def test_ledger_declared_input_types_are_real_words():
    known = {"image2d", "depth", "counts", "countrate", "histcube"}
    for name, meta in opsphoton.OPSPHOTON.items():
        assert set(meta["in"]) <= known, (name, meta["in"])
        assert meta["doc"], name                 # every op has a summary line


def test_no_op_declares_the_generic_signal_type():
    """The 2026-09-01 chain-fuzz finding, pinned so it cannot regress.

    With ``signal`` declared, 7 of the 17 photon ops were never executed in a
    1200-chain run (seed 7001): the fuzzer's signal pool is a sine wave with
    negative values, and every photon op refuses negative counts, so they always
    produced CONTRACT. The fail-closed check was perfect and that is exactly the
    problem — "zero findings" looked like robustness while the ops had never
    run. Separating the type is the same call opsoptics made for jones/stokes.
    """
    for name, meta in opsphoton.OPSPHOTON.items():
        assert "signal" not in meta["in"], (name, meta["in"])
        assert meta["out"] != "signal", (name, meta["out"])
    # ...and the family is still seeded from nothing, so the counts pool fills
    # even on the first step of a chain (the airy_pattern role in optics).
    seed_ops = [n for n, m in opsphoton.OPSPHOTON.items()
                if not m["in"] and m["out"] == "counts"]
    assert seed_ops == ["tcspc_simulate"]
    assert opsphoton.call("tcspc_simulate").ndim == 1


def test_counts_and_countrate_are_genuinely_different_quantities():
    """Why two words and not one: a counts-scale array through a rate op is a
    silent near-identity, so the dead-time physics would never be exercised.

    Measured: a histogram peaking at ~250 counts, read as 250 Hz against the
    default 50 ns dead time, comes back changed by 1.2e-05 relative — the op
    "runs" but its saturation branch, its 1/tau guard and the paralysable
    non-injectivity are all untouched. A real rate array (1e3-1e7 Hz) moves by
    up to 33%.
    """
    hist = PC.tcspc_simulate(2.0, bins=256, bin_ps=100.0, signal_photons=5000.0,
                             ambient_photons=100.0, noise=False)
    as_rate = PC.spad_deadtime_apply(hist)              # counts misread as Hz
    moved = float(np.abs(as_rate - hist).max() / max(hist.max(), 1e-30))
    assert moved < 1e-4                                  # a silent near-identity
    real = np.logspace(3.0, 7.0, 32)
    assert float(np.abs(PC.spad_deadtime_apply(real) - real).max()
                 / real.max()) > 0.3                     # a real rate really moves


def test_every_op_documents_what_it_raises():
    for name, fn in ((n, opsphoton.get(n)) for n in opsphoton.OPSPHOTON):
        assert "Raises" in fn.__doc__, name


# --------------------------------------------------------------------------- #
# fail-closed contract                                                         #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_non_finite_input_is_refused_everywhere(bad):
    img = np.full((4, 4), bad)
    with pytest.raises(ValueError, match="non-finite"):
        PC.photon_statistics(img)
    with pytest.raises(ValueError, match="non-finite"):
        PC.anscombe_transform(img)
    with pytest.raises(ValueError, match="non-finite"):
        PC.tcspc_stats(np.full(8, bad), 100.0)
    with pytest.raises(ValueError, match="non-finite"):
        PC.dtof_cube_depth(np.full((2, 2, 4), bad))


def test_negative_counts_are_refused():
    with pytest.raises(ValueError, match="cannot be negative"):
        PC.photon_statistics(np.full((4, 4), -1.0))
    with pytest.raises(ValueError, match="cannot be negative"):
        PC.tcspc_stats(np.full(8, -1.0), 100.0)
    with pytest.raises(ValueError, match="cannot be negative"):
        PC.spad_deadtime_apply(np.full(4, -1.0), 50.0)


def test_string_scalars_are_refused_not_parsed():
    """float('100') succeeds, so a never-parsed config value would sail through."""
    with pytest.raises(ValueError, match="string"):
        PC.tcspc_simulate("3.0")
    with pytest.raises(ValueError, match="string"):
        PC.photon_sample(np.ones((2, 2)), "100")
    with pytest.raises(ValueError, match="string"):
        PC.dtof_depth(np.array([1.0, 5.0, 1.0]), "100")


def test_non_integer_seeds_and_counts_are_refused():
    with pytest.raises(ValueError, match="non-negative int"):
        PC.photon_sample(np.ones((2, 2)), 10.0, seed=1.5)
    with pytest.raises(ValueError, match="seed must be >= 0"):
        PC.photon_sample(np.ones((2, 2)), 10.0, seed=-1)
    with pytest.raises(ValueError, match="must be an int"):
        PC.tcspc_simulate(1.0, bins=64.0)
    with pytest.raises(ValueError, match="must be an int"):
        PC.tcspc_coates_correct(np.array([1.0, 2.0]), 100.0)


def test_masked_arrays_are_refused():
    m = np.ma.masked_array(np.ones((3, 3)), mask=[[1, 0, 0], [0, 0, 0], [0, 0, 0]])
    with pytest.raises(ValueError, match="masked"):
        PC.photon_statistics(m)


def test_size_caps_fail_closed_before_allocating():
    with pytest.raises(ValueError, match="MAX_LAMBDA"):
        PC.photon_sample(np.ones((2, 2)), 1e13)
    with pytest.raises(ValueError, match=r"bins must be in \[2, %d\]" % PC.MAX_BINS):
        PC.tcspc_simulate(1.0, bins=PC.MAX_BINS + 1)
    with pytest.raises(ValueError, match="MAX_BINS"):
        PC.tcspc_stats(np.ones(PC.MAX_BINS + 1), 100.0)
    with pytest.raises(ValueError, match="MAX_CUBE_ELEMENTS"):
        PC.dtof_cube_simulate(np.full((512, 512), 2.0), bins=256)


def test_unknown_mode_strings_are_refused():
    h = np.array([1.0, 9.0, 1.0])
    with pytest.raises(ValueError, match="mode must be one of"):
        PC.dtof_depth(h, 100.0, "argmax")
    with pytest.raises(ValueError, match="method must be one of"):
        PC.tcspc_background_subtract(h, "mode")
    with pytest.raises(ValueError, match="mode must be one of"):
        PC.anscombe_inverse(np.full((2, 2), 4.0), mode="exact")


def test_no_op_emits_a_runtime_warning_on_its_normal_path():
    """A RuntimeWarning is how a silent NaN announces itself; there must be none."""
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        counts = PC.photon_sample(np.ones((32, 32)) * 0.4, 30.0, seed=0)
        PC.photon_statistics(counts)
        PC.photon_uncertainty(counts, zero_floor=1.0)
        PC.anscombe_inverse(PC.anscombe_transform(counts), mode="unbiased")
        h = PC.tcspc_simulate(2.0, bins=128, bin_ps=200.0, seed=0)
        PC.tcspc_irf_convolve(h, 200.0, 400.0)
        PC.tcspc_stats(PC.tcspc_background_subtract(h), 200.0)
        PC.dtof_depth(h, 200.0, "gaussian")
        PC.lifetime_phasor(_decay_hist(2000.0, 128, 200.0, 5000.0), 200.0)
        cube = PC.dtof_cube_simulate(_tilted_plane(8, 8), bins=128, bin_ps=200.0,
                                     seed=0)
        PC.dtof_cube_depth(cube, 200.0, "gaussian")


def test_no_op_returns_a_silent_nan_or_inf():
    counts = PC.photon_sample(np.ones((16, 16)) * 0.5, 20.0, seed=0)
    hist = PC.tcspc_simulate(2.0, bins=128, bin_ps=200.0, signal_photons=300.0,
                             ambient_photons=80.0, seed=0)
    cube = PC.dtof_cube_simulate(_tilted_plane(8, 8), bins=128, bin_ps=200.0,
                                 seed=0)
    outs = [PC.photon_sample(counts, 1.0, seed=0),
            PC.photon_uncertainty(counts),
            PC.anscombe_transform(counts),
            PC.anscombe_inverse(PC.anscombe_transform(counts)),
            PC.spad_deadtime_apply(np.linspace(1e3, 1e6, 16), 50.0),
            PC.spad_deadtime_correct(np.linspace(1e3, 1e6, 16), 50.0),
            PC.tcspc_coates_correct(hist, 100000),
            hist, PC.tcspc_irf_convolve(hist, 200.0, 400.0),
            PC.tcspc_background_subtract(hist), cube,
            PC.dtof_cube_depth(cube, 200.0)]
    for a in outs:
        assert np.isfinite(a).all()
    for d in (PC.photon_statistics(counts), PC.tcspc_stats(hist, 200.0),
              PC.lifetime_fit(_decay_hist(2000.0, 128, 200.0, 5000.0), 200.0,
                              background=0.0),
              PC.lifetime_phasor(hist, 200.0)):
        for key, v in d.items():
            assert v is None or not isinstance(v, float) or np.isfinite(v), key


# --------------------------------------------------------------------------- #
# regressions from the 2026-09-01 adversarial pass                             #
# --------------------------------------------------------------------------- #
class TestAdversarial20260901:
    """Each test is the minimal reproduction that exposed the bug."""

    def test_denormal_irf_width_no_longer_returns_a_silent_nan(self):
        """BUG: irf_fwhm_ps=5e-324 passes '> 0' but sigma underflows to 0.0, and
        a bin edge landing exactly on the pulse centre made 0/0 = NaN. The op
        returned [nan, nan, 0, 0, 0, 0, 0, 0] with no error."""
        d_edge = C * 100e-12 / 2.0                # t0 exactly on bin edge 1
        with pytest.raises(ValueError, match="underflows"):
            PC.tcspc_simulate(d_edge, bins=8, bin_ps=100.0, irf_fwhm_ps=5e-324,
                              noise=False)
        with pytest.raises(ValueError, match="underflows"):
            PC.dtof_cube_simulate(np.full((2, 2), d_edge), bins=8, bin_ps=100.0,
                                  irf_fwhm_ps=5e-324, noise=False)
        # a representable width still works
        assert np.isfinite(PC.tcspc_simulate(d_edge, bins=8, bin_ps=100.0,
                                             irf_fwhm_ps=1e-300,
                                             noise=False)).all()

    def test_anscombe_no_longer_accepts_a_shape_the_ledger_does_not_declare(self):
        """BUG: anscombe_transform(np.arange(5.0)) returned a 1-D array while the
        ledger declares image2d -> image2d, i.e. a type-level lie."""
        with pytest.raises(ValueError, match="2-D"):
            PC.anscombe_transform(np.arange(5.0))
        with pytest.raises(ValueError, match="2-D"):
            PC.anscombe_transform(np.ones((2, 2, 2)))
        with pytest.raises(ValueError, match="2-D"):
            PC.anscombe_inverse(np.arange(2.0, 5.0))

    def test_empty_value_string_is_no_longer_silently_parsed(self):
        """BUG: dtof_cube_depth(cube, empty_value="3") succeeded, because
        float("3") parses — an unparsed config value became a depth in metres."""
        cube = PC.dtof_cube_simulate(_tilted_plane(2, 2), bins=64, bin_ps=400.0,
                                     noise=False)
        with pytest.raises(ValueError, match="string"):
            PC.dtof_cube_depth(cube, 400.0, empty_value="3")
        with pytest.raises(ValueError, match="bool"):
            PC.dtof_cube_depth(cube, 400.0, empty_value=True)
        with pytest.raises(ValueError, match="finite or NaN"):
            PC.dtof_cube_depth(cube, 400.0, empty_value=float("inf"))

    def test_leading_bins_default_no_longer_breaks_a_short_histogram(self):
        """BUG: the fixed default leading_bins=8 made method='leading' raise on
        every histogram shorter than 8 bins, for a constant nobody chose."""
        h = np.array([1.0, 2.0])
        assert np.allclose(PC.tcspc_background_subtract(h, "leading"),
                           [0.0, 0.5])
        assert np.allclose(PC.tcspc_background_subtract(h, "trailing"),
                           [0.0, 0.5])
        # an explicit over-long request is still refused
        with pytest.raises(ValueError, match="leading_bins"):
            PC.tcspc_background_subtract(h, "leading", leading_bins=8)

    def test_flat_histogram_no_longer_reports_the_first_bin_as_a_depth(self):
        """BUG: a flat histogram (e.g. a uniform (D, H, W) voxel volume passed in
        as a cube) made argmax pick bin 0, and every pixel came back as
        0.0075 m — a plausible-wrong depth map with no error anywhere."""
        with pytest.raises(ValueError, match="flat histogram"):
            PC.dtof_depth(np.ones(9), 100.0)
        got = PC.dtof_cube_depth(np.ones((3, 3, 4)), 100.0)
        assert np.allclose(got, 0.0)             # empty marker, not 0.0075 m
        # the centroid mode is well defined on a flat histogram and still works
        assert PC.dtof_depth(np.ones(9), 100.0, "centroid") == pytest.approx(
            C * (4.5 * 100.0) * 1e-12 / 2.0, rel=1e-12)
