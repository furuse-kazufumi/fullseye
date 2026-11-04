# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""敵対的検証 2026-11-05(担当 stats)の回帰テスト。

各テストは報告の再現を「真値・不変量・独立実装」と比べる形にしてある。
"""
from __future__ import annotations

import math

import numpy as np
import pytest

# ---- S7: fullseye.judge の非有限な限界値 ----------------------------------

_NONFINITE_SPECS = [
    {"width_mm": {"min": 3.0, "max": float("nan")}},
    {"width_mm": {"nominal": 3.0, "tol": float("nan")}},
    {"width_mm": {"nominal": float("nan"), "tol": 0.1}},
    {"area": {"min": float("nan"), "max": float("nan")}},
    {"width_mm": {"max": float("inf")}},
    {"width_mm": {"min": -math.inf}},
    {"width_mm": {"nominal": 3.0, "tol": math.inf}},
    {"width_mm": {"eq": float("nan")}},
    {"width_mm": {"in": [1.0, float("nan")]}},
]


@pytest.mark.parametrize("spec", _NONFINITE_SPECS)
def test_s7_judge_refuses_nonfinite_rule_limits(spec):
    """NaN/inf の限界値は比較が全部 False になり「常に ok」になる → ValueError。"""
    from fullseye.judge import judge
    meas = {"width_mm": 99.0, "area": -5.0}
    with pytest.raises(ValueError, match="finite"):
        judge(meas, spec)


def test_s7_judge_finite_limits_still_judge():
    """有限な規則は従来どおり: 99 mm は max 3.5 を破って ng。"""
    from fullseye.judge import judge
    v = judge({"width_mm": 99.0}, {"width_mm": {"min": 3.0, "max": 3.5}})
    assert v.status == "ng"
    v = judge({"width_mm": 3.2}, {"width_mm": {"min": 3.0, "max": 3.5}})
    assert v.status == "ok"


# ---- S1/S2: spc_hotelling_t2 の管理限界 -----------------------------------

def test_s1_hotelling_known_parameters_use_chi_square_limit():
    """母数既知なら UCL = chi2_p(1-alpha)。行数 m に依らない(m <= p で inf にしない)。"""
    import scipy.stats as st
    import spc
    alpha = 0.0027
    mu, cov = np.zeros(2), np.eye(2)
    want = st.chi2.ppf(1 - alpha, 2)
    cases = [np.array([[50.0, 50.0]]),
             np.array([[50.0, 50.0], [0.0, 0.0]]),
             np.array([[5.0, 5.0], [0.0, 0.0], [0.0, 0.0]])]
    assert len(cases) == 3
    for X in cases:
        r = spc.spc_hotelling_t2(X, alpha=alpha, mean=mu, cov=cov)
        assert r["ucl"] == pytest.approx(want, rel=1e-12)
        assert r["phase"] == "known"
        assert r["out_of_control"] == [0] and not r["in_control"]


def test_s1_hotelling_known_parameters_false_alarm_rate_is_alpha():
    """独立の検算: 母数既知・管理状態の正規データで、行ごとの警報率が alpha に一致する。"""
    import spc
    rng = np.random.default_rng(11)
    alpha, p, n = 0.05, 3, 40000
    X = rng.normal(size=(n, p))
    r = spc.spc_hotelling_t2(X, alpha=alpha, mean=np.zeros(p), cov=np.eye(p))
    rate = len(r["out_of_control"]) / n
    se = math.sqrt(alpha * (1 - alpha) / n)
    assert abs(rate - alpha) < 5 * se


def test_s2_hotelling_phase_one_limit_is_below_the_identity_bound_and_alarms():
    """phase I では T2_i <= (m-1)^2/m が恒等的に成り立つ。UCL はその下にあり、粗大外れ値で警報する。"""
    import spc
    rng = np.random.default_rng(0)
    ms = (10, 20, 30, 50)
    assert len(ms) == 4
    for m in ms:
        X = rng.normal(0, 1, (m, 2))
        X[0] = [1e6, -1e6]
        r = spc.spc_hotelling_t2(X)
        bound = (m - 1) ** 2 / m
        assert r["phase"] == "phase_I"
        assert float(r["t2"].max()) <= bound * (1 + 1e-9)
        assert r["ucl"] < bound
        assert 0 in r["out_of_control"]


def test_s2_hotelling_phase_one_false_alarm_rate_is_alpha():
    """独立の検算(Monte Carlo): phase I の行ごとの警報率が alpha に一致する(Beta 限界が正しい)。

    phase-II の F 式を当てていた旧実装では m=12, p=2, alpha=0.05 の警報率は 0 に近い。
    """
    import spc
    rng = np.random.default_rng(12)
    alpha, m, p, reps = 0.05, 12, 2, 4000
    hits = 0
    for _ in range(reps):
        r = spc.spc_hotelling_t2(rng.normal(size=(m, p)), alpha=alpha)
        hits += len(r["out_of_control"])
    rate = hits / (reps * m)
    assert reps * m == 48000
    # 行どうしは弱く相関する(同じ mean/cov を共有)ので許容は二項より広めに取る。
    assert abs(rate - alpha) < 0.006


def test_s2_hotelling_refuses_half_known_parameters_and_too_few_rows():
    import spc
    X = np.random.default_rng(1).normal(size=(30, 2))
    with pytest.raises(ValueError):
        spc.spc_hotelling_t2(X, mean=np.zeros(2))
    with pytest.raises(ValueError):
        spc.spc_hotelling_t2(X, cov=np.eye(2))
    with pytest.raises(ValueError):
        spc.spc_hotelling_t2(X[:3])            # m = p+1: phase I の Beta が定義されない
