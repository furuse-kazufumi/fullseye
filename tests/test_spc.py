# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""spc — 統計的工程管理 op の閉じた式の恒等式と fail-closed を検査する。

各 op は学習でなく標準・教科書の閉じた式なので、突き合わせる厳密な恒等式がある
(モジュール docstring の表)。乱数は「対称性の破れ」を隠すので(feedback:
random_test_data_hides_structural_defects)、恒等式は**構造を作った系列**で確かめる:
一定・ステップ・中心を仕様中点に置いた分布・平均行そのもの。
"""
from __future__ import annotations

import numpy as np
import pytest

import spc


# ---- Xbar-R 管理図 --------------------------------------------------------
def test_xbar_r_constants_are_iso8258():
    sg = np.random.default_rng(0).normal(10.0, 1.0, size=(20, 5))
    r = spc.spc_xbar_r(sg)
    assert (r["a2"], r["d3"], r["d4"]) == (0.577, 0.000, 2.115)


def test_xbar_r_in_control_on_stationary_data():
    sg = np.random.default_rng(1).normal(50.0, 2.0, size=(30, 4))
    r = spc.spc_xbar_r(sg)
    # 定常データは限界内に収まる(誤警報率は低いが 0 とは限らないので、大半が管理下)。
    assert len(r["out_of_control"]) <= 1


def test_xbar_r_catches_a_large_shift():
    rng = np.random.default_rng(2)
    sg = rng.normal(10.0, 1.0, size=(25, 5))
    sg[-2:] += 5.0
    r = spc.spc_xbar_r(sg)
    assert not r["in_control"]
    assert set(r["out_of_control"]) >= {23, 24}


def test_xbar_r_limits_are_symmetric_about_grand_mean():
    sg = np.random.default_rng(3).normal(0.0, 1.0, size=(40, 6))
    r = spc.spc_xbar_r(sg)
    assert r["xbar_ucl"] - r["xbar_cl"] == pytest.approx(r["xbar_cl"] - r["xbar_lcl"])
    assert r["r_lcl"] == 0.0            # n=6 は D3=0


@pytest.mark.parametrize("bad", [np.zeros(5), np.zeros((3, 1)), np.zeros((3, 11))])
def test_xbar_r_rejects_bad_shapes(bad):
    with pytest.raises(ValueError):
        spc.spc_xbar_r(bad)


# ---- CUSUM ----------------------------------------------------------------
def test_cusum_constant_at_target_stays_zero():
    r = spc.spc_cusum(np.full(50, 7.0), target=7.0, k=0.5, h=5.0)
    assert float(np.max(r["c_plus"])) == 0.0
    assert float(np.max(r["c_minus"])) == 0.0
    assert r["in_control"]


def test_cusum_step_accumulates_at_rate_d_minus_k():
    x = np.concatenate([np.zeros(5), np.full(20, 2.0)])
    r = spc.spc_cusum(x, target=0.0, k=0.5, h=1e9)     # h 無限大で警報させない
    slope = np.diff(r["c_plus"][6:])                    # ステップ後の傾き
    assert np.allclose(slope, 1.5)                      # d - k = 2 - 0.5


def test_cusum_symmetry_positive_and_negative_shift():
    up = np.concatenate([np.zeros(10), np.full(20, 1.5)])
    dn = np.concatenate([np.zeros(10), np.full(20, -1.5)])
    ru = spc.spc_cusum(up, target=0.0, k=0.5, h=5.0)
    rd = spc.spc_cusum(dn, target=0.0, k=0.5, h=5.0)
    assert np.allclose(ru["c_plus"], rd["c_minus"])
    assert ru["first_alarm"] == rd["first_alarm"]


@pytest.mark.parametrize("kw", [{"k": -1.0}, {"h": 0.0}, {"target": np.inf}])
def test_cusum_rejects_bad_params(kw):
    base = {"target": 0.0, "k": 0.5, "h": 5.0}
    base.update(kw)
    with pytest.raises(ValueError):
        spc.spc_cusum(np.arange(10.0), **base)


# ---- EWMA -----------------------------------------------------------------
def test_ewma_constant_at_target_stays_flat():
    r = spc.spc_ewma(np.full(30, 7.0), target=7.0, sigma=1.0)
    assert np.allclose(r["z"], 7.0)
    assert r["in_control"] and r["first_alarm"] == -1


def test_ewma_matches_the_recursion_exactly():
    rng = np.random.default_rng(3)
    x = rng.normal(0.0, 1.0, 40)
    lam = 0.25
    r = spc.spc_ewma(x, target=0.0, lam=lam, sigma=1.0)
    z = np.empty_like(x)
    prev = 0.0
    for i in range(x.size):
        prev = lam * x[i] + (1.0 - lam) * prev
        z[i] = prev
    assert np.allclose(r["z"], z)


def test_ewma_limits_widen_toward_the_asymptote():
    r = spc.spc_ewma(np.zeros(60), target=0.0, lam=0.2, L=3.0, sigma=1.0)
    assert np.all(np.diff(r["ucl"]) >= -1e-12)          # monotone non-decreasing
    assert r["ucl"][-1] == pytest.approx(r["ucl_inf"], abs=1e-3)
    assert r["ucl"][0] == pytest.approx(3.0 * np.sqrt((0.2 / 1.8) * (1 - 0.8 ** 2)), rel=1e-9)  # i=1 closed form


def test_ewma_lambda_one_reduces_to_shewhart_individuals():
    x = np.array([5.0, 8.0, 3.0, 6.0, 5.0])
    r = spc.spc_ewma(x, target=5.0, lam=1.0, L=3.0, sigma=1.0)
    assert np.allclose(r["z"], x)                       # no smoothing
    assert np.allclose(r["ucl"], 8.0) and np.allclose(r["lcl"], 2.0)  # constant target±L*sigma


def test_ewma_catches_small_sustained_shift_that_shewhart_misses():
    rng = np.random.default_rng(0)
    base = rng.normal(0.0, 1.0, 60)
    base[20:] += 0.8                                     # +0.8 sigma sustained drift
    r = spc.spc_ewma(base, target=0.0, lam=0.2, L=3.0, sigma=1.0)
    assert r["first_alarm"] != -1                        # EWMA alarms
    assert not np.any(np.abs(base) > 3.0)                # a 3-sigma Shewhart chart would not


@pytest.mark.parametrize("kw", [{"lam": 0.0}, {"lam": 1.5}, {"L": 0.0},
                                {"sigma": -1.0}, {"target": np.inf}])
def test_ewma_rejects_bad_params(kw):
    base = {"target": 0.0, "lam": 0.2, "L": 3.0, "sigma": 1.0}
    base.update(kw)
    with pytest.raises(ValueError):
        spc.spc_ewma(np.arange(10.0), **base)


def test_ewma_registered_in_opsspc_change_category():
    import opsspc
    assert "spc_ewma" in opsspc.list_ops("change")
    assert opsspc.get("spc_ewma") is spc.spc_ewma


# ---- 工程能力 -------------------------------------------------------------
def test_capability_centred_gives_cpk_equals_cp():
    x = np.array([9.0, 10.0, 11.0, 10.0, 9.0, 11.0, 10.0] * 6)
    x = x - x.mean() + 10.0                             # 中心 = 中点 10
    r = spc.spc_capability(x, 6.0, 14.0)
    assert r["cpk"] == pytest.approx(r["cp"])


def test_capability_off_centre_reduces_cpk_below_cp():
    x = np.random.default_rng(4).normal(10.0, 1.0, size=300)
    x = x - x.mean() + 12.0                             # 中心を上限寄りに
    r = spc.spc_capability(x, 6.0, 14.0)
    assert r["cpk"] < r["cp"]


def test_capability_cpk_never_exceeds_cp():
    rng = np.random.default_rng(5)
    for _ in range(20):
        x = rng.normal(rng.uniform(6, 14), rng.uniform(0.3, 2.0), size=100)
        r = spc.spc_capability(x, 6.0, 14.0)
        assert r["cpk"] <= r["cp"] + 1e-12


def test_capability_rejects_constant_series():
    with pytest.raises(ValueError):
        spc.spc_capability(np.full(20, 10.0), 6.0, 14.0)


def test_capability_rejects_inverted_limits():
    with pytest.raises(ValueError):
        spc.spc_capability(np.arange(10.0), 14.0, 6.0)


# ---- Hotelling T² ---------------------------------------------------------
def test_hotelling_mean_row_is_zero():
    data = np.random.default_rng(6).normal(0.0, 1.0, size=(50, 3))
    mu = data.mean(axis=0)
    t2 = spc.spc_hotelling_t2(np.vstack([data, mu]))["t2"][-1]
    assert abs(float(t2)) < 1e-9


def test_hotelling_ucl_matches_f_distribution():
    from scipy.stats import f as fdist
    data = np.random.default_rng(7).normal(0.0, 1.0, size=(40, 2))
    r = spc.spc_hotelling_t2(data, alpha=0.0027)
    m, p = 40, 2
    ucl = p * (m + 1.0) * (m - 1.0) / (m * (m - p)) * fdist.ppf(1 - 0.0027, p, m - p)
    assert r["ucl"] == pytest.approx(ucl)


def test_hotelling_catches_joint_outlier():
    rng = np.random.default_rng(8)
    data = rng.normal(0.0, 1.0, size=(60, 3))
    data[-1] += 8.0                                     # 全特徴を同時に飛ばす
    r = spc.spc_hotelling_t2(data)
    assert not r["in_control"]
    assert 59 in r["out_of_control"]


def test_hotelling_rejects_singular_covariance():
    a = np.random.default_rng(9).normal(0.0, 1.0, size=(30, 1))
    data = np.hstack([a, a])                            # 2 列が完全共線
    with pytest.raises(ValueError):
        spc.spc_hotelling_t2(data)


def test_hotelling_rejects_too_few_observations():
    with pytest.raises(ValueError):
        spc.spc_hotelling_t2(np.random.default_rng(10).normal(0, 1, size=(3, 4)))


# ---- 共通の fail-closed ---------------------------------------------------
@pytest.mark.parametrize("op,args", [
    ("spc_cusum", (np.array([np.nan, 1.0, 2.0]),)),
    ("spc_capability", (np.array([np.inf, 1.0]),)),
])
def test_non_finite_is_rejected(op, args):
    fn = getattr(spc, op)
    with pytest.raises(ValueError):
        if op == "spc_cusum":
            fn(*args, target=0.0)
        else:
            fn(*args, 0.0, 10.0)


def test_registry_lists_all_four():
    assert set(spc.SPC) == {"spc_xbar_r", "spc_cusum", "spc_capability",
                            "spc_hotelling_t2"}
