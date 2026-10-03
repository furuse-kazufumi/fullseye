"""推定と統計の古典の門(2026-10-03、陣 3)。閉じた式・定理・第 2 実装(scipy / 総当たり / 一括最小二乗)で立てる。"""
import math
import warnings

import numpy as np
import pytest
from scipy import stats

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import fullseye as fs
    import mathestimation as E
    import opsmath

LEDGER = ["assign_hungarian", "hist_distance", "stat_ttest_paired", "stat_ttest_welch", "stat_ks_test", "stat_chi2_gof",
          "crlb_gaussian", "kalman_smooth", "mat_expm", "mat_logm", "se3_exp", "se3_log"]


def test_public_and_ledger():
    assert opsmath.missing() == []
    assert sorted(opsmath.list_ops("estimation")) == sorted(LEDGER)
    assert sorted(E.__all__) == sorted(LEDGER)
    for n in LEDGER:
        assert callable(getattr(fs, n)) and n in fs.__all__ and callable(getattr(fs.ledger, n)), n


def test_hungarian_matches_brute_force():
    rng = np.random.default_rng(0)
    for _ in range(30):
        C = rng.random((rng.integers(2, 7), rng.integers(2, 7)))
        assert abs(E.assign_hungarian(C)["total"] - E._assign_bruteforce(C)) < 1e-12
        assert abs(E.assign_hungarian(C, maximize=True)["total"] - E._assign_bruteforce(C, True)) < 1e-12
    with pytest.raises(ValueError):
        E.assign_hungarian([[1.0, np.inf], [2.0, 3.0]])


def test_kl_of_two_gaussians_and_mutual_information_identity():
    x = np.linspace(-15, 15, 30001)
    p = np.exp(-(x - 0.0) ** 2 / 2)
    q = np.exp(-(x - 0.7) ** 2 / (2 * 1.6 ** 2))
    kl = math.log(1.6) + (1 + 0.49) / (2 * 1.6 ** 2) - 0.5
    assert abs(E.hist_distance(p, q) - kl) < 1e-10
    pxy = np.random.default_rng(1).random((6, 5))
    pxy /= pxy.sum()
    prod = np.outer(pxy.sum(1), pxy.sum(0))
    assert abs(E.hist_distance(pxy, prod) - float(np.sum(pxy * np.log(pxy / prod)))) < 1e-12
    assert E.hist_distance(p, p) == 0.0 and E.hist_distance(p, p, "hellinger") == pytest.approx(0, abs=1e-7)
    assert 0 < E.hist_distance(p, q, "js") < math.log(2)
    assert E.hist_distance(p, q, "js") == pytest.approx(E.hist_distance(q, p, "js"), abs=1e-14)   # 対称


def test_hypothesis_tests_match_scipy_and_p_is_uniform_under_the_null():
    rng = np.random.default_rng(2)
    a = rng.normal(size=20)
    b = a + 0.3 + rng.normal(scale=0.5, size=20)
    c = rng.normal(1, 2, 30)
    assert E.stat_ttest_paired(a, b)["p"] == pytest.approx(stats.ttest_rel(a, b).pvalue, rel=1e-12)
    assert E.stat_ttest_welch(a, c)["p"] == pytest.approx(stats.ttest_ind(a, c, equal_var=False).pvalue, rel=1e-12)
    o = np.array([18, 22, 30, 30])
    assert E.stat_chi2_gof(o)["p"] == pytest.approx(stats.chisquare(o).pvalue, rel=1e-12)
    ps = np.array([E.stat_ttest_welch(rng.normal(size=15), rng.normal(size=25))["p"] for _ in range(1500)])
    assert stats.kstest(ps, "uniform").pvalue > 0.01 and 0.03 < np.mean(ps < 0.05) < 0.07
    assert E.stat_ks_test(rng.normal(size=500))["p"] > 0.01 and E.stat_ks_test(rng.uniform(size=500))["p"] < 1e-6


def test_crlb_equals_the_monte_carlo_variance_of_an_efficient_estimator():
    rng = np.random.default_rng(3)
    x = np.linspace(0, 1, 20)
    th, sig = np.array([1.0, 2.0]), 0.1
    cr = E.crlb_gaussian(x, th, sig, model="line")
    est = np.array([np.polyfit(x, th[0] + th[1] * x + sig * rng.normal(size=x.size), 1)[::-1] for _ in range(4000)])
    assert np.allclose(np.std(est, axis=0), cr["std"], rtol=0.05)
    # 定数の平均: σ/√n
    one = E.crlb_gaussian(np.zeros(25), [3.0], 0.2, model="constant")
    assert one["std"][0] == pytest.approx(0.2 / 5, rel=1e-6)


def test_kalman_smoother_equals_the_batch_least_squares():
    rng = np.random.default_rng(4)
    T = 30
    z = np.cumsum(rng.normal(scale=0.2, size=T)) + 0.5 * rng.normal(size=T)
    ks = E.kalman_smooth(z[:, None], [[1.0]], [[1.0]], [[0.04]], [[0.25]], [0.0], [[1.0]])
    A = np.zeros((T, T))
    A[0, 0] += 1.0
    for k in range(1, T):
        A[k, k] += 25
        A[k - 1, k - 1] += 25
        A[k, k - 1] -= 25
        A[k - 1, k] -= 25
    A += np.eye(T) * 4
    xb = np.linalg.solve(A, 4 * z)
    assert np.abs(ks["x_smooth"][:, 0] - xb).max() < 1e-12
    assert np.abs(ks["P_smooth"][:, 0, 0] - np.diag(np.linalg.inv(A))).max() < 1e-12
    assert np.abs(ks["x_filt"][-1, 0] - xb[-1]) < 1e-12                       # 最後の時刻はフィルタ = 平滑化


def test_se3_exp_log_round_trip_and_agrees_with_the_matrix_exponential():
    w, v = np.array([0.3, -0.5, 0.8]), np.array([1.0, 2.0, -0.5])
    xi = np.concatenate([v, w])
    G = np.zeros((4, 4))
    G[:3, :3] = E._hat(w)
    G[:3, 3] = v
    assert np.abs(E.se3_exp(xi) - E.mat_expm(G)).max() < 1e-14
    assert np.abs(E.se3_log(E.se3_exp(xi)) - xi).max() < 1e-12
    assert np.abs(E.se3_log(E.se3_exp(1e-9 * xi)) - 1e-9 * xi).max() < 1e-20
    assert np.abs(E.mat_logm(E.mat_expm(E._hat(w))) - E._hat(w)).max() < 1e-12
    with pytest.raises(ValueError):
        E.mat_logm(np.diag([1.0, -2.0]))


def test_kl_is_never_negative_even_with_tiny_probabilities():
    """床(eps)を q 全体に掛けていた版は、1e-49 の q を 1e-12 に持ち上げて KL(p‖p) = −3e-10 を返した(回帰)。"""
    rng = np.random.default_rng(9)
    for _ in range(50):
        p = rng.random(200) * np.exp(-rng.uniform(0, 120, 200))      # 1e-52 まで落ちる値を混ぜる
        q = p * np.exp(rng.normal(0, 0.01, 200)) if rng.random() < 0.5 else rng.random(200)
        assert E.hist_distance(p, q) >= 0.0 and E.hist_distance(p, p) == 0.0
