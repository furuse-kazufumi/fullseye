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


# ---- S3: gum_expanded の Welch-Satterthwaite と相関 -----------------------

def _tb2(u=(1.0, 1.0), nu=(4.0, 4.0)):
    return {"u": np.array(u), "sensitivity": np.array([1.0, 1.0]), "dof": np.array(nu)}


def test_s3_gum_correlated_dof_never_exceeds_the_budget():
    """r=+1 の等しい 2 成分(各 nu=4)は Wishart の厳密解 nu_eff=4(旧実装 32 > 総和 8)。"""
    import spc
    rs = (0.25, 0.5, 1.0, -0.5, -0.95)
    assert len(rs) == 5
    for r in rs:
        o = spc.gum_expanded(_tb2(), correlation=np.array([[1.0, r], [r, 1.0]]))
        nu_eff = float(o["dof_effective"][0])
        assert nu_eff <= 8.0 + 1e-9, (r, nu_eff)
        assert nu_eff == pytest.approx(4.0, rel=1e-12), (r, nu_eff)
        assert float(o["dof_used"][0]) == 4.0


def test_s3_gum_uncorrelated_value_is_unchanged():
    """相関なし・単位行列の相関は従来の Welch-Satterthwaite と同じ値(閉形式 8)。"""
    import spc
    a = spc.gum_expanded(_tb2())
    b = spc.gum_expanded(_tb2(), correlation=np.eye(2))
    assert float(a["dof_effective"][0]) == pytest.approx(8.0, rel=1e-12)
    assert float(b["dof_effective"][0]) == pytest.approx(8.0, rel=1e-12)


def test_s3_gum_correlated_interval_covers_at_the_nominal_level():
    """独立の検算(Monte Carlo): 同じ 5 回の測定から推定した相関する 2 成分の和について、
    U = k u_c の区間が真値を 95 % 以上で覆う。旧実装(nu_eff を水増し)は r=+1 で約 89 %。"""
    import spc
    rng = np.random.default_rng(3)
    n, reps = 5, 4000
    for r in (1.0, 0.5):
        R = np.array([[1.0, r], [r, 1.0]])
        L = np.linalg.cholesky(np.array([[1.0, r], [r, 1.0 + 1e-12]]))
        X = rng.normal(size=(reps, n, 2)) @ L.T
        m = X.mean(axis=1)
        s = X.std(axis=1, ddof=1) / np.sqrt(n)
        hits = 0
        for i in range(reps):
            g = spc.gum_expanded({"u": s[i], "sensitivity": np.ones(2),
                                  "dof": np.full(2, n - 1.0)}, correlation=R)
            hits += bool(abs(m[i].sum()) <= g["expanded"][0])
        assert hits / reps >= 0.94, (r, hits / reps)


# ---- S4: gum_validate の数値許容差(JCGM 101 8.1.3) -----------------------

def _delta_decimal(u, ndig):
    """独立実装: u を ndig 有効桁に丸めて(半分は切り上げ)c x 10^l、delta = 0.5 x 10^l。"""
    from decimal import Decimal, ROUND_HALF_UP
    d = Decimal(repr(float(u)))
    e = d.adjusted() - (ndig - 1)
    q = d.quantize(Decimal(1).scaleb(e), rounding=ROUND_HALF_UP)
    if q.adjusted() - (ndig - 1) != e:            # 丸めで桁が繰り上がった
        e += 1
    return 0.5 * 10.0 ** e


def test_s4_gum_validate_delta_rounds_u_to_ndig_digits_first():
    """u=0.0996, ndig=2 -> 0.10 = 10 x 10^-2 -> delta 0.005(旧実装 0.0005)。"""
    import spc
    us = (0.0996, 0.0999, 0.1000, 0.0949, 0.0951, 0.996, 0.00994, 0.00996, 1.234, 9.96, 99.4)
    assert len(us) == 11
    for ndig in (1, 2, 3):
        for u in us:
            g = spc.gum_expanded({"u": np.array([u]), "sensitivity": np.array([1.0]),
                                  "dof": np.array([np.inf])}, estimate=1.0)
            v = spc.gum_validate(g, {"low": g["low"], "high": g["high"]}, ndig=ndig)
            assert float(v["delta"][0]) == pytest.approx(_delta_decimal(u, ndig), rel=1e-12), (u, ndig)
    g = spc.gum_expanded({"u": np.array([0.0996]), "sensitivity": np.array([1.0]),
                          "dof": np.array([np.inf])}, estimate=1.0)
    v = spc.gum_validate(g, {"low": g["low"] + 0.003, "high": g["high"] + 0.003}, ndig=2)
    assert float(v["delta"][0]) == pytest.approx(0.005) and bool(v["agree"][0])
