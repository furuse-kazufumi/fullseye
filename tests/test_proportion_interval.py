"""二項比率区間と全数成功の必要件数。"""
import numpy as np
import pytest
from scipy import stats

import anomeval
import opsspc
import pod


def test_audit_examples_and_29_of_29_boundary():
    lo10 = pod.proportion_interval(10, 10, sides="lower")["lower"]
    hi20 = pod.proportion_interval(0, 20, sides="upper")["upper"]
    assert lo10 == pytest.approx(0.05 ** (1 / 10), abs=1e-14)
    assert hi20 == pytest.approx(1 - 0.05 ** (1 / 20), abs=1e-14)
    assert pod.trials_for_all_success(0.90) == 29
    assert pod.proportion_interval(29, 29, sides="lower")["lower"] >= 0.90
    assert pod.proportion_interval(28, 28, sides="lower")["lower"] < 0.90


@pytest.mark.parametrize("k,n,sides", [(10, 10, "lower"), (0, 20, "upper"),
                                         (45, 46, "two"), (1, 60, "upper")])
def test_clopper_pearson_matches_independent_beta_quantiles(k, n, sides):
    r = pod.proportion_interval(k, n, sides=sides)
    tail = 0.025 if sides == "two" else 0.05
    want_lo = 0.0 if k == 0 or sides == "upper" else stats.beta.ppf(tail, k, n-k+1)
    want_hi = 1.0 if k == n or sides == "lower" else stats.beta.ppf(1-tail, k+1, n-k)
    assert r["lower"] == pytest.approx(want_lo, abs=2e-14)
    assert r["upper"] == pytest.approx(want_hi, abs=2e-14)


def test_mil_hdbk_1823a_table_g_i_values():
    # MIL-HDBK-1823A (2009), Table G-I: published values are rounded to four decimals.
    assert pod.proportion_interval(0, 150, confidence=0.50, sides="upper")["upper"] == pytest.approx(0.0046, abs=5e-5)
    assert pod.proportion_interval(0, 60, confidence=0.95, sides="upper")["upper"] == pytest.approx(0.0487, abs=5e-5)
    assert pod.proportion_interval(1, 60, confidence=0.95, sides="upper")["upper"] == pytest.approx(0.0766, abs=5e-5)


def test_wilson_and_jeffreys_known_values():
    # Brown, Cai & DasGupta (Statistical Science 16, 2001), standard score/Beta formulas.
    assert pod.proportion_interval(10, 10, sides="lower", method="wilson")["lower"] == pytest.approx(0.787058, abs=1e-6)
    assert pod.proportion_interval(10, 10, sides="lower", method="jeffreys")["lower"] == pytest.approx(0.829227, abs=1e-6)


def test_validation_is_fail_closed():
    bad = [(11, 10, 0.95), (0, 0, 0.95), (1, 2, 1.0), (1.0, 2, 0.95)]
    for k, n, confidence in bad:
        with pytest.raises(ValueError):
            pod.proportion_interval(k, n, confidence=confidence)
    for kwargs in ({"sides": "left"}, {"method": "wald"}):
        with pytest.raises(ValueError):
            pod.proportion_interval(1, 2, **kwargs)
    for value in (0, 1, np.nan, True):
        with pytest.raises(ValueError):
            pod.trials_for_all_success(value)


def test_lower_limit_is_monotone_in_success_count():
    lower = [pod.proportion_interval(k, 30, sides="lower")["lower"] for k in range(31)]
    assert np.all(np.diff(lower) >= 0)


def test_cp_exact_coverage_is_conservative_on_probability_grid():
    # Exact enumeration is deterministic and stronger than a noisy Monte Carlo check.
    n = 20
    for p in np.linspace(0.05, 0.95, 19):
        coverage = sum(stats.binom.pmf(k, n, p) for k in range(n + 1)
                       if pod.proportion_interval(k, n, sides="lower")["lower"] <= p)
        assert coverage >= 0.95 - 2e-14


def test_registry_and_existing_internal_paths_delegate_without_drift():
    assert opsspc.get("proportion_interval") is pod.proportion_interval
    assert opsspc.get("trials_for_all_success") is pod.trials_for_all_success
    for k, n in ((0, 20), (7, 10), (10, 10)):
        assert anomeval._cp_lower(k, n, 0.05) == pod.proportion_interval(k, n, sides="lower")["lower"]
        assert anomeval._cp_upper(k, n, 0.05) == pod.proportion_interval(k, n, sides="upper")["upper"]
