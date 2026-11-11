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


# ---- S5/S6 と兄弟: 「変動なし」「範囲外」の床に絶対の 1 を混ぜない --------
#
# 不変量: 列(画像)ごとの単位の付け替え(x -> s x)で結果が変わらないこと。

_UNIT_SCALES = (1.0, 1e-12, 1e-15, 1e6)


def test_s5_mt_distance_is_invariant_to_feature_units():
    """MT 法の MD は z = (x - m)/s で無次元。pF と F で同じ値(旧実装は F で全特徴が flat)。"""
    import spc
    rng = np.random.default_rng(0)
    good = np.column_stack([rng.normal(1.0, 0.01, 200), rng.normal(4.7, 0.02, 200),
                            rng.normal(2.2, 0.015, 200)])
    bad = np.array([[1.08, 4.7, 2.2]])
    ref = None
    assert len(_UNIT_SCALES) == 4
    for s in _UNIT_SCALES:
        u = spc.spc_mt_unit_space(good * s)
        d = spc.spc_mt_distance(bad * s, mean=u["mean"], std=u["std"], inv_corr=u["inv_corr"])
        assert u["flat_features"] == 0, s
        if ref is None:
            ref = float(d["md"][0])
            assert ref > 3.0
        assert float(d["md"][0]) == pytest.approx(ref, rel=1e-9), s
        assert d["flagged"].tolist() == [0]


def test_s5_mt_truly_flat_feature_is_still_detected_at_any_scale():
    """床を相対にしても、同じ値の繰り返し(丸め屑の std)は単位に依らず flat と判定する。"""
    import spc
    rng = np.random.default_rng(1)
    for s in _UNIT_SCALES:
        X = np.column_stack([rng.normal(0.0, 1.0, 200), np.full(200, 4.2), rng.normal(5.0, 1.0, 200)]) * s
        assert spc.spc_mt_unit_space(X)["flat_features"] == 1, s
        X0 = np.column_stack([rng.normal(0.0, 1.0, 200), np.zeros(200)]) * s
        assert spc.spc_mt_unit_space(X0)["flat_features"] == 1, s


def test_s6_standardised_pca_is_invariant_to_column_units():
    """標準化 PCA の固有値は列の単位に依らない(旧実装は F で全列「変動なし」の ValueError)。"""
    import multivar
    rng = np.random.default_rng(0)
    t = rng.normal(size=(50, 1))
    X = np.column_stack([1.0 + 0.0005 * t[:, 0] + 0.0002 * rng.normal(size=50),
                         4.7 + 0.02 * t[:, 0] + 0.01 * rng.normal(size=50),
                         2.2 + 0.01 * rng.normal(size=50)])
    ref = np.asarray(multivar.mv_pca(X, n_parallel=0)["eigenvalues"])
    # 独立の検算: 標準化 PCA の固有値 = 相関行列の固有値
    want = np.sort(np.linalg.eigvalsh(np.corrcoef(X, rowvar=False)))[::-1]
    assert np.allclose(ref, want, rtol=1e-9, atol=1e-12)
    for s in _UNIT_SCALES:
        got = np.asarray(multivar.mv_pca(X * s, n_parallel=0)["eigenvalues"])
        assert np.allclose(got, ref, rtol=1e-9, atol=1e-12), s


def test_s6_constant_column_is_still_refused_at_any_scale():
    import multivar
    rng = np.random.default_rng(2)
    for s in _UNIT_SCALES:
        X = np.column_stack([rng.normal(size=30), np.full(30, 4.2), rng.normal(size=30)]) * s
        with pytest.raises(ValueError, match="no variation"):
            multivar.mv_pca(X, n_parallel=0)


def test_sibling_feat_image_vector_range_tolerance_is_relative():
    """data_range=(0, 1e-12) の画像に 1.5e-12 が入っていたら拒否(旧: 許容 1e-12 で通過)。"""
    import multivar
    img = np.full((8, 8), 0.5e-12)
    img[0, 0] = 1.5e-12
    with pytest.raises(ValueError, match="outside data_range"):
        multivar.feat_image_vector([img], features=["entropy_bits"], data_range=(0.0, 1e-12))
    img1 = img * 1e12
    with pytest.raises(ValueError, match="outside data_range"):
        multivar.feat_image_vector([img1], features=["entropy_bits"], data_range=(0.0, 1.0))


def _symmetric_scene():
    yy, xx = np.mgrid[0:41, 0:41].astype(float)
    return (np.exp(-((xx - 20.0) ** 2 + (yy - 14.0) ** 2) / 30.0)
            + 0.5 * np.exp(-((xx - 20.0) ** 2) / 8.0 - ((yy - 30.0) ** 2) / 20.0))


def test_sibling_symmetry2d_is_invariant_to_intensity_units():
    """放射輝度を W(1e-14 フルスケール)で渡しても対称軸は同じ(旧: 「一様な画像」で拒否)。"""
    import symmetry2d as S
    img = _symmetric_scene()
    ref = S.reflection_axis(img)
    for s in (1e-14, 1e-15, 1e8):
        got = S.reflection_axis(img * s)
        assert got["angle_deg"] == pytest.approx(ref["angle_deg"], abs=1e-9), s
        assert got["offset_px"] == pytest.approx(ref["offset_px"], abs=1e-9), s
    with pytest.raises(ValueError):
        S.reflection_axis(np.zeros((41, 41)))


def test_sibling_polar_fit_negative_minimum_is_judged_relative_to_the_pixel():
    """変調振幅が平均を上回る(物理的にあり得ない)掃引は、強度の単位に依らず拒否される。

    角度 0/60/120 では各コマは正のまま、当てはめの I_min だけが負(-1e-6 相対)。
    旧実装は絶対許容 1e-12 なので、1e-14 フルスケールの単位では見逃していた。
    """
    import specularity as SP
    ang = np.array([0.0, 60.0, 120.0])
    S0, eps = 1.0, 1e-6
    t = np.deg2rad(ang)
    frames = 0.5 * (S0 + S0 * (1 + eps) * np.cos(2 * t))
    assert np.all(frames > 0)
    stack = np.broadcast_to(frames[:, None, None], (3, 4, 4)).copy()
    for s in (1.0, 1e-14, 1e6):
        with pytest.raises(ValueError, match="negative minimum"):
            SP.polarization_separate(stack * s, angles_deg=ang)
    ok = 0.5 * (S0 + 0.5 * S0 * np.cos(2 * t))
    okstack = np.broadcast_to(ok[:, None, None], (3, 4, 4)).copy()
    d0, _ = SP.polarization_separate(okstack, angles_deg=ang)
    d1, _ = SP.polarization_separate(okstack * 1e-14, angles_deg=ang)
    assert np.allclose(d1, d0 * 1e-14, rtol=1e-9, atol=0)


def test_s4_gum_validate_delta_matches_the_published_examples():
    """JCGM 101 7.9.2 の例題: u=0.00035 g / ndig=2 -> delta 0.000005、ndig=1 -> 0.00005;
    9.2.2.7: u=2.0 / ndig=2 -> 0.05;u=1.0e1 / ndig=2 -> 0.5。"""
    import spc
    cases = [(0.00035, 2, 0.5e-5), (0.00035, 1, 0.5e-4), (2.0, 2, 0.05), (10.0, 2, 0.5), (10.0, 1, 5.0)]
    assert len(cases) == 5
    for u, ndig, want in cases:
        g = spc.gum_expanded({"u": np.array([u]), "sensitivity": np.array([1.0]),
                              "dof": np.array([np.inf])}, estimate=0.0)
        v = spc.gum_validate(g, {"low": g["low"], "high": g["high"]}, ndig=ndig)
        assert float(v["delta"][0]) == pytest.approx(want, rel=1e-12), (u, ndig)


# ---- 疑い(確認済み): _shortest_interval の q(JCGM 101 7.7.2) ---------------

def _shortest_reference(y, p):
    """独立実装: 7.7.2 のとおり q = pM(整数なら)/ int(pM + 1/2)、r = 1..M-q の最短。"""
    s = sorted(float(v) for v in y)
    M = len(s)
    pm = p * M
    q = int(round(pm)) if abs(pm - round(pm)) < 1e-9 else int(pm + 0.5)
    best = min(range(1, M - q + 1), key=lambda r: (s[r + q - 1] - s[r - 1], r))
    return s[best - 1], s[best + q - 1]


def test_shortest_interval_q_follows_jcgm101_7_7_2():
    """pM の端数が 1/2 以上なら q は切り上げ(旧実装は切り捨てで順序統計量 1 つ分狭い)。"""
    import spc
    rng = np.random.default_rng(5)
    cases = [(30, 0.95), (50, 0.95), (11, 0.95), (200, 0.95), (199, 0.9), (1000, 0.6827)]
    assert len(cases) == 6
    for M, p in cases:
        y = rng.gamma(2.0, size=M)
        assert spc._shortest_interval(y, p) == _shortest_reference(y, p), (M, p)
