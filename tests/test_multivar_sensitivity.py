# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""感度解析・同定性(sensitivity.py、opsmultivar の sensitivity / identifiability)の門 —— 真値は解析値と閉形式。

* Sobol': Ishigami 関数(a=7, b=0.1、Ishigami & Homma 1990)の解析値 S1 = (0.3139, 0.4424, 0)、
  ST = (0.5576, 0.4424, 0.2437)。分散の式から計算し直し、推定値の信頼区間が解析値を含むことを確かめる。
* Morris: 線形モデルでは EE が厳密に係数(μ* = |係数| x 範囲、σ = 0)、Δ = p/(2(p−1))。
* 共線性指数(Brun ら 2001): 同じ列 2 本で γ = ∞、直交な列で γ = 1、n と d が積でしか効かないとき
  決まる組み合わせは n^1 * d^1、決まらないのは n^1 * d^-1。
* 残差 PCA: 純雑音で 0 成分、ランク 1 の構造で 1 成分(既知雑音 = Marchenko-Pastur の端 / 未知 = 置換)。
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import doe  # noqa: E402
import sensitivity as se  # noqa: E402

PI_RANGE = [("x1", -math.pi, math.pi), ("x2", -math.pi, math.pi), ("x3", -math.pi, math.pi)]


def ishigami(x, a=7.0, b=0.1):
    return np.sin(x[:, 0]) + a * np.sin(x[:, 1]) ** 2 + b * x[:, 2] ** 4 * np.sin(x[:, 0])


def ishigami_analytic(a=7.0, b=0.1):
    """Ishigami & Homma 1990 の分散分解(式は UQTestFuns / SFU Virtual Library の転載と照合)。"""
    V = a ** 2 / 8 + b * math.pi ** 4 / 5 + b ** 2 * math.pi ** 8 / 18 + 0.5
    V1 = 0.5 * (1 + b * math.pi ** 4 / 5) ** 2
    V2 = a ** 2 / 8
    V13 = b ** 2 * math.pi ** 8 * (1 / 18 - 1 / 50)
    return np.array([V1, V2, 0.0]) / V, np.array([V1 + V13, V2, V13]) / V


def test_ishigami_analytic_values_match_the_published_ones():
    s1, st = ishigami_analytic()
    assert np.allclose(np.round(s1, 4), [0.3139, 0.4424, 0.0])
    assert np.allclose(np.round(st, 4), [0.5576, 0.4424, 0.2437])
    # V = V1 + V2 + V13(分解が閉じる)
    V = 49 / 8 + 0.1 * math.pi ** 4 / 5 + 0.01 * math.pi ** 8 / 18 + 0.5
    assert s1.sum() * V + st[2] * V == pytest.approx(V)


def test_sobol_indices_of_ishigami_bracket_the_analytic_values():
    d = se.doe_saltelli(2 ** 13, PI_RANGE, seed=1)
    r = se.sens_sobol(d, ishigami(d["natural"]), n_boot=300, seed=0)
    s1, st = ishigami_analytic()
    assert np.all(np.abs(r["S1"] - s1) < 0.02), r["S1"]
    assert np.all(np.abs(r["ST"] - st) < 0.02), r["ST"]
    assert np.all((r["S1_ci"][:, 0] <= s1) & (s1 <= r["S1_ci"][:, 1])), (r["S1_ci"], s1)
    assert np.all((r["ST_ci"][:, 0] <= st) & (st <= r["ST_ci"][:, 1])), (r["ST_ci"], st)
    assert r["ranking"][0] == "x1" and r["n_evaluations"] == 2 ** 13 * 5


def test_saltelli_layout_and_power_of_two():
    d = se.doe_saltelli(64, 3, seed=None)
    A, B = d["coded"][:64], d["coded"][64:128]
    for i in range(3):
        ab = d["coded"][(2 + i) * 64:(3 + i) * 64]
        assert np.array_equal(np.delete(ab, i, axis=1), np.delete(A, i, axis=1))
        assert np.array_equal(ab[:, i], B[:, i])
    with pytest.raises(ValueError, match="power of two"):
        se.doe_saltelli(1000, 3)
    with pytest.raises(ValueError):
        se.sens_sobol(d, np.ones(64 * 5))                     # 出力が動かない
    with pytest.raises(ValueError):
        se.sens_sobol(doe.doe_lhs(10, 3), np.zeros(10))       # Saltelli の計画でない


def test_additive_model_has_s1_equal_st_and_known_shares():
    d = se.doe_saltelli(2 ** 12, [("a", 0, 1), ("b", 0, 1), ("c", 0, 1)], seed=2)
    x = d["natural"]
    r = se.sens_sobol(d, 1.0 * x[:, 0] + 2.0 * x[:, 1], n_boot=0)
    assert np.allclose(r["S1"], [0.2, 0.8, 0.0], atol=0.01)       # 分散 1:4
    assert np.allclose(r["ST"], r["S1"], atol=0.01) and r["S1_ci"] is None


def test_morris_elementary_effects_of_a_linear_model_are_exact():
    m = se.doe_morris(12, [("a", 0, 1), ("b", 0, 2), ("c", 10, 20)], levels=4, seed=3)
    assert m["meta"]["delta"] == pytest.approx(4 / 6)
    x = m["natural"]
    r = se.sens_morris(m, 2 * x[:, 0] + 3 * x[:, 1] + 0 * x[:, 2])
    assert np.allclose(r["mu_star"], [2 * 1, 3 * 2, 0])          # 単位立方体(範囲全体 = 1)あたりの変化
    assert np.allclose(r["mu_star_natural"], [2, 3, 0]) and np.allclose(r["sigma"], 0, atol=1e-12)
    assert r["class"] == ["linear/additive", "linear/additive", "negligible"]
    # 各軌道は各因子をちょうど 1 回動かす
    for t in range(12):
        assert sorted(m["meta"]["changed"][t]) == [0, 1, 2]


def test_morris_flags_interactions_and_ranks_ishigami():
    m = se.doe_morris(40, PI_RANGE, levels=6, seed=4, n_candidates=200)
    r = se.sens_morris(m, ishigami(m["natural"]))
    assert r["class"][2] == "non-linear or interacting"           # x3 は x1 との積でしか効かない
    assert r["mu"][2] == pytest.approx(0.0, abs=0.5 * r["mu_star"][2])   # 符号が打ち消し合う
    assert "Campolongo" in m["meta"]["selection"]
    with pytest.raises(ValueError):
        se.doe_morris(10, 3, levels=5)                            # 奇数の水準
    with pytest.raises(ValueError):
        se.sens_morris(m, np.zeros(5))


def test_confounding_index_closed_forms_and_the_n_times_d_case():
    rng = np.random.default_rng(5)
    g = rng.normal(size=(200, 3))
    Q, _ = np.linalg.qr(g)
    assert se.mv_confounding(Q, ["a", "b", "c"])["gamma_full"] == pytest.approx(1.0)
    S = np.column_stack([g[:, 0], 2 * g[:, 0], g[:, 1], g[:, 2]])   # n と d は積 n*d でしか効かない(対数の感度が比例)
    r = se.mv_confounding(S, ["n", "d", "gain", "offset"], log_params=True)
    assert math.isinf(r["gamma_full"]) and not r["identifiable"]
    assert r["confounded_pairs"][0][0] == ("n", "d")
    grp = r["confounded_groups"][0]
    assert grp["parameters"] == ["n", "d"]
    assert grp["determined"] == ["n^1 * d^1"] and grp["undetermined"] == ["n^1 * d^-1"]
    assert r["determined_individually"] == ["gain", "offset"]
    assert ("gain", "offset") in [tuple(s) for s in r["largest_identifiable"]] or \
        any({"gain", "offset"} <= set(s) for s in r["largest_identifiable"])
    # 2 本の列の角度 θ → γ = 1/sqrt(1 − cos θ)(2x2 のグラム行列の最小固有値)
    th = math.radians(10)
    S2 = np.column_stack([Q[:, 0], math.cos(th) * Q[:, 0] + math.sin(th) * Q[:, 1]])
    assert se.mv_confounding(S2)["gamma_full"] == pytest.approx(1 / math.sqrt(1 - math.cos(th)))


def test_confounding_reports_a_three_way_dependency_and_dead_columns():
    rng = np.random.default_rng(6)
    g = rng.normal(size=(100, 3))
    S = np.column_stack([g[:, 0], g[:, 1], g[:, 0] + g[:, 1], g[:, 2], np.zeros(100)])
    r = se.mv_confounding(S, ["a", "b", "c", "e", "dead"])
    assert r["confounded_pairs"] == []                             # 2 本ずつでは見えない
    assert r["confounded_groups"][0]["parameters"] == ["a", "b", "c"]
    assert r["no_influence"] == ["dead"] and not r["identifiable"]
    with pytest.raises(ValueError):
        se.mv_confounding(np.ones((3, 1)))


def test_residual_pca_noise_floor_and_structure():
    rng = np.random.default_rng(7)
    N = 0.1 * rng.normal(size=(30, 120))
    assert se.mv_residual_pca(N)["n_structural"] == 0
    assert se.mv_residual_pca(N, noise_sigma=0.1)["n_structural"] == 0
    shape = np.sin(np.linspace(0, 6, 120))
    R = N + np.outer(rng.normal(size=30), shape) * 0.3
    for kw in ({}, {"noise_sigma": 0.1}):
        r = se.mv_residual_pca(R, **kw)
        assert r["n_structural"] == 1 and r["structure_detected"]
        assert abs(np.corrcoef(r["loadings"][:, 0], shape)[0, 1]) > 0.95     # どこが違うかの形を返す
    with pytest.raises(ValueError):
        se.mv_residual_pca(R, noise_sigma=-1)


def test_ledger_public_tier_fuzzer_and_summaries():
    import fullseye as fs
    import opsmultivar as om
    import typed_catalog as tc
    sys.path.insert(0, str(ROOT / "tools"))
    import chain_fuzz as cf
    import opdocs
    assert set(om.list_ops("sensitivity")) | set(om.list_ops("identifiability")) == set(se.__all__)
    assert om.missing() == []
    rows = {r[0]: r for r in tc.catalog() if r[0] in se.__all__}
    assert set(rows) == set(se.__all__)
    d = json.loads((ROOT / "docs" / "i18n" / "op_summary.json").read_text(encoding="utf-8"))
    for name in se.__all__:
        assert hasattr(fs.ledger, name), name
        b = cf.OP_ARG_BUILDERS.get(name)                    # 計画の op(入力なし)は既定値で呼ぶ
        args, kw = b(None, np.random.default_rng(0)) if b else ((), {})
        assert cf.TYPE_CHECKS[rows[name][3]](getattr(se, name)(*args, **kw)), name
        line = getattr(se, name).__doc__.strip().splitlines()[0]
        e = d["summaries"]["multivar/" + name]
        assert e["fp"] == opdocs.fingerprint(line), name
        for lang in ("ja", "zh", "tw", "ko", "de", "hi"):
            assert e[lang].strip(), (name, lang)
