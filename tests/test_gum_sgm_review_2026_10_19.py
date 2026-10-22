# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""外部レビュー 6 件(R01-R05, L01)の再現と回帰。各テストは正しい挙動を主張する。

修正前のコードでは R01-R05 がすべて失敗する(= 再現した)ことを確認してから直した。
"""
from __future__ import annotations

import numpy as np
import pytest

import spc
import stereo


def _tbl(u, c, dist=None):
    t = {"u": np.asarray(u, float), "sensitivity": np.asarray(c, float)}
    if dist is not None:
        t["dist"] = np.array(dist, dtype=object)
    return t


def _R3_not_psd():
    # r12 = r13 = 0.9, r23 = -0.9 は半正定値でない(最小固有値 < 0)
    R = np.array([[1, .9, .9], [.9, 1, -.9], [.9, -.9, 1]])
    assert np.linalg.eigvalsh(R).min() < -0.1
    return R


def test_R01_propagate_rejects_non_psd_even_when_variance_positive():
    R = _R3_not_psd()
    c = np.array([1.0, 1.0, 1.0])
    assert c @ R @ c > 0                       # 射影した分散は正 = 従来の検査をすり抜ける
    with pytest.raises(ValueError, match="positive semi-definite"):
        spc.gum_propagate(_tbl([1, 1, 1], c), correlation=R)


@pytest.mark.parametrize("bad", ["asym", "diag", "nan"])
def test_R02_monte_carlo_validates_correlation_matrix(bad):
    R = np.array([[1.0, 0.3], [0.3, 1.0]])
    if bad == "asym":
        R[0, 1] = 0.5
    elif bad == "diag":
        R[0, 0] = 2.0
    else:
        R[0, 1] = R[1, 0] = np.nan
    with pytest.raises(ValueError):
        spc.gum_monte_carlo(_tbl([1, 1], [1, 1], ["normal", "normal"]),
                            distribution="dist", correlation=R, n=2000)


def test_R03_correlated_rectangular_keeps_its_marginal():
    R = np.array([[1.0, 0.8], [0.8, 1.0]])
    t = _tbl([1, 1], [0, 1], ["rectangular", "rectangular"])
    o = spc.gum_monte_carlo(t, distribution="dist", correlation=R, n=400_000, seed=3)
    hw = float(o["half_width"][0])
    assert abs(hw - 0.95 * 3 ** 0.5) < 0.01, hw          # 1.64545 (台形なら 1.88)
    # 周辺分布の KS: 入力 2 を直接取り出し一様のままか
    y = spc._mc_samples(t, R, n=100_000, seed=1)
    from scipy import stats
    for j in range(2):
        ks = stats.kstest(y[:, j] / 3 ** 0.5, stats.uniform(-1, 2).cdf).statistic
        assert ks < 0.01, ks
    assert abs(np.corrcoef(y.T)[0, 1] - 0.8) < 0.03    # 相関は(copula の意味で)残る


def test_R04_exact_cancellation_is_valid_zero():
    R = np.array([[1.0, 1.0], [1.0, 1.0]])
    r = spc.gum_propagate(_tbl([1, 1], [1, -1]), correlation=R)
    assert float(r["u_combined"][0]) == 0.0
    assert bool(r["guf_valid"][0]) is True
    assert list(r["invalid_reasons"]) == []
    assert list(r["note"]) == ["exact_cancellation"]


def test_R04b_real_stationary_point_still_detected():
    r = spc.gum_propagate(_tbl([0.005, 0.005], [0.0, 0.0]))
    assert bool(r["guf_valid"][0]) is False
    assert list(r["invalid_reasons"]) == ["stationary_point"]


@pytest.mark.parametrize("fill", [np.nan, np.inf, -np.inf])
def test_R05_sgm_rejects_entirely_non_finite_image(fill):
    img = np.full((12, 20), fill)
    ok = np.random.default_rng(0).random((12, 20))
    with pytest.raises(ValueError, match="finite"):
        stereo.disparity_sgm(img, ok, max_disp=4)
    with pytest.raises(ValueError, match="finite"):
        stereo.disparity_sgm(ok, img, max_disp=4)


def test_R05b_sgm_marks_non_finite_pixels_as_nan():
    rng = np.random.default_rng(0)
    L = rng.random((16, 24)); Rr = L.copy()
    L[5, 7] = np.nan
    d = stereo.disparity_sgm(L, Rr, max_disp=4)
    assert np.isnan(d[5, 7]) and np.isnan(d).sum() == 1


def test_L01_singular_correlation_is_sampled_as_degenerate_normal():
    R = np.array([[1.0, 1.0], [1.0, 1.0]])
    t = _tbl([1, 1], [1, -1], ["normal", "normal"])
    o = spc.gum_monte_carlo(t, distribution="dist", correlation=R, n=20_000)
    assert float(o["u_monte_carlo"][0]) < 1e-12           # x1 = x2 なので y = 0
    t = _tbl([1, 1], [1, 1], ["normal", "normal"])
    o = spc.gum_monte_carlo(t, distribution="dist", correlation=R, n=200_000)
    assert abs(float(o["u_monte_carlo"][0]) - 2.0) < 0.02
