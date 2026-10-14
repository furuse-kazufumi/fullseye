# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""多変量解析(multivar.py、opsmultivar の analysis / features)の門 —— 真値は第 2 実装と閉形式。

* PCA = SVD: 固有値が相関行列(標準化)/ 共分散行列の eigvalsh と一致、得点 = 中心化した表 x 負荷。
* PLS: NIPALS(Wold ら 2001)と SIMPLS(de Jong 1993)の 2 実装が 1 変数 y で 1e-10 まで一致、
  成分数 = 変数の数なら最小二乗と一致、VIP の 2 乗和 = 変数の数(重みが単位長だから)。
* 応答曲面: 雑音なしの二次式を中心複合計画で厳密に回収、停留点 = 解析解、2 水準の計画に二次を当てると
  交絡する項を名指しで拒否、純誤差のある計画では当てはまりの悪さの F 検定が立つ。
* 主効果: 加法モデルの水準平均 = 閉形式、望大 SN は spc.spc_mt_sn_ratio と同じ式(再利用)。
* 特徴量: data_range が要る特徴は data_range 無しで拒否、範囲外の画素も拒否。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import doe  # noqa: E402
import multivar as mv  # noqa: E402


# --------------------------------------------------------------------------- #
# 1. PCA                                                                       #
# --------------------------------------------------------------------------- #
def test_pca_equals_the_eigendecomposition_of_the_correlation_and_covariance():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(50, 6)) @ rng.normal(size=(6, 6))
    r = mv.mv_pca(X, n_components=6)
    assert np.allclose(r["eigenvalues"], np.sort(np.linalg.eigvalsh(np.corrcoef(X.T)))[::-1], atol=1e-12)
    Z = (X - X.mean(0)) / X.std(0, ddof=1)
    assert np.allclose(r["scores"], Z @ r["loadings"], atol=1e-10)
    r2 = mv.mv_pca(X, standardize=False, n_components=6)
    assert np.allclose(r2["eigenvalues"], np.sort(np.linalg.eigvalsh(np.cov(X.T)))[::-1], atol=1e-9)
    assert r["cumulative"][-1] == pytest.approx(1.0)


def test_pca_component_counts_find_a_planted_rank():
    rng = np.random.default_rng(1)
    T = rng.normal(size=(200, 2)) @ rng.normal(size=(2, 8)) + 0.2 * rng.normal(size=(200, 8))
    r = mv.mv_pca(T)
    assert r["n_components"]["parallel"] == 2 and r["n_returned"] == 2
    assert r["n_components"]["mdl"] is None                     # 標準化した表では MDL を出さない
    assert mv.mv_pca(T, standardize=False)["n_components"]["mdl"] == 2
    noise = rng.normal(size=(60, 6))
    assert mv.mv_pca(noise)["n_components"]["parallel"] == 0     # 構造の無い表に成分を作らない


def test_pca_refuses_a_constant_column_and_accepts_a_feature_table():
    X = np.column_stack([np.arange(10.0), np.ones(10), np.arange(10.0) ** 2])
    with pytest.raises(ValueError, match="no variation"):
        mv.mv_pca(X)
    tab = {"matrix": np.random.default_rng(2).normal(size=(20, 3)), "names": ["a", "b", "c"], "units": ["DN"] * 3}
    assert mv.mv_pca(tab)["names"] == ["a", "b", "c"]


# --------------------------------------------------------------------------- #
# 2. PLS                                                                       #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("A", [1, 2, 3, 5])
def test_nipals_and_simpls_agree_for_one_response(A):
    rng = np.random.default_rng(3)
    X = rng.normal(size=(40, 6)) @ rng.normal(size=(6, 6))
    y = X @ rng.normal(size=6) + 0.3 * rng.normal(size=40)
    a = mv.mv_pls(X, y, n_components=A)
    b = mv.mv_pls(X, y, n_components=A, method="simpls")
    assert np.allclose(a["coef"], b["coef"], atol=1e-10 * np.abs(a["coef"]).max())
    assert np.allclose(a["intercept"], b["intercept"], atol=1e-9)
    assert a["q2"] == pytest.approx(b["q2"], abs=1e-9)
    assert np.allclose(a["vip"], b["vip"], atol=1e-9)


def test_pls_with_all_components_is_least_squares_and_vip_sums_to_p():
    rng = np.random.default_rng(4)
    X = rng.normal(size=(30, 4))
    y = X @ np.array([2.0, -1.0, 0.0, 0.5]) + 3.0 + 0.1 * rng.normal(size=30)
    r = mv.mv_pls(X, y, n_components=4)
    M = np.column_stack([np.ones(30), X])
    beta = np.linalg.lstsq(M, y, rcond=None)[0]
    assert np.allclose(r["coef"][:, 0], beta[1:], atol=1e-9) and r["intercept"][0] == pytest.approx(beta[0])
    assert (r["vip"] ** 2).sum() == pytest.approx(4.0)
    assert r["vip"][2] < 1.0 < r["vip"][0]                     # 効かない変数は VIP < 1


def test_pls_q2_rule_picks_the_planted_number_and_flags_noise():
    rng = np.random.default_rng(5)
    t = rng.normal(size=(60, 2))
    X = t @ rng.normal(size=(2, 10)) + 0.05 * rng.normal(size=(60, 10))
    y = t @ np.array([1.0, -1.0]) + 0.05 * rng.normal(size=60)
    r = mv.mv_pls(X, y)
    # Q^2 の規則は目安: 2 成分の構造に 3 本目が X の雑音を補正して Q^2_3 > 0.0975 を取ることがある
    assert r["significant"] and 2 <= r["n_components"] <= 3 and r["q2"] > 0.9
    assert r["q2_per_component"][1] > 0.5 and r["q2_per_component"][3] < 0.0975
    noise = mv.mv_pls(rng.normal(size=(40, 5)), rng.normal(size=40))
    assert not noise["significant"] and noise["q2"] < 0.0975


def test_pls_two_responses_and_refusals():
    rng = np.random.default_rng(6)
    X = rng.normal(size=(40, 5))
    Y = np.column_stack([X[:, 0] + X[:, 1], X[:, 2] - X[:, 0]]) + 0.05 * rng.normal(size=(40, 2))
    r = mv.mv_pls(X, Y)
    assert r["coef"].shape == (5, 2) and r["q2"] > 0.9
    with pytest.raises(ValueError):
        mv.mv_pls(X, Y[:30])
    with pytest.raises(ValueError):
        mv.mv_pls(X, Y, method="kernel")


# --------------------------------------------------------------------------- #
# 3. 応答曲面                                                                  #
# --------------------------------------------------------------------------- #
def test_rsm_recovers_an_exact_quadratic_and_its_stationary_point():
    d = doe.doe_central_composite([("T", 150, 200, "C"), ("t", 10, 30, "s")], center=5)
    c = d["coded"]
    y = 50 - 3 * c[:, 0] ** 2 - 2 * c[:, 1] ** 2 + 1.0 * c[:, 0] * c[:, 1] + 2.4 * c[:, 0] - 1.0 * c[:, 1]
    r = mv.rsm_fit(d, y)
    assert r["terms"] == ["1", "T", "t", "T*t", "T^2", "t^2"]
    assert np.allclose(r["coef"], [50, 2.4, -1.0, 1.0, -3, -2], atol=1e-10)
    B = np.array([[-3, 0.5], [0.5, -2]])
    xs = -0.5 * np.linalg.solve(B, [2.4, -1.0])
    assert np.allclose(r["stationary"]["coded"], xs, atol=1e-10)
    assert np.allclose(r["stationary"]["natural"], doe.doe_decode(d, xs)[0])
    assert r["canonical"]["kind"].startswith("maximum") and r["stationary"]["inside_region"]
    assert r["r2"] == pytest.approx(1.0)


def test_rsm_canonical_analysis_tells_saddle_and_minimum():
    d = doe.doe_central_composite(2, center=3)
    c = d["coded"]
    assert mv.rsm_fit(d, c[:, 0] ** 2 - c[:, 1] ** 2 + 0.1 * c[:, 0])["canonical"]["kind"] == "saddle"
    assert mv.rsm_fit(d, c[:, 0] ** 2 + 2 * c[:, 1] ** 2)["canonical"]["kind"].startswith("minimum")


def test_rsm_refuses_models_the_plan_cannot_support_and_names_the_aliases():
    rng = np.random.default_rng(7)
    with pytest.raises(ValueError, match=r"x1\^2 = 1"):
        mv.rsm_fit(doe.doe_fractional_factorial(4, 1), rng.normal(size=8))
    with pytest.raises(ValueError, match=r"x1\*x2 = x4"):
        mv.rsm_fit(doe.doe_fractional_factorial(5, 2), rng.normal(size=8), model="interaction")
    with pytest.raises(ValueError, match="no residual"):
        mv.rsm_fit(doe.doe_fractional_factorial(2, 0), rng.normal(size=4), model="interaction")
    lin = mv.rsm_fit(doe.doe_fractional_factorial(4, 1, center=3), rng.normal(size=11), model="linear")
    assert lin["terms"] == ["1", "x1", "x2", "x3", "x4"] and "stationary" not in lin


def test_rsm_lack_of_fit_detects_curvature_a_linear_model_misses():
    d = doe.doe_central_composite(2, center=5)
    c = d["coded"]
    rng = np.random.default_rng(8)
    y = 1 + c[:, 0] + 4 * c[:, 0] ** 2 + 0.05 * rng.normal(size=len(c))
    lin = mv.rsm_fit(d, y, model="linear")
    quad = mv.rsm_fit(d, y, model="quadratic")
    assert lin["lack_of_fit"]["testable"] and lin["lack_of_fit"]["p"] < 1e-6
    assert quad["lack_of_fit"]["p"] > 0.01
    assert quad["lack_of_fit"]["df_pe"] == 4


# --------------------------------------------------------------------------- #
# 4. 主効果と SN                                                               #
# --------------------------------------------------------------------------- #
def test_main_effects_of_an_additive_model_on_l9_are_exact():
    d = doe.doe_orthogonal_array("L9", 4)
    c = d["coded"]
    y = 10 + 2 * c[:, 0] - 1 * c[:, 1] + 0.5 * c[:, 2] ** 2
    r = mv.doe_main_effects(d, y)
    assert np.allclose(r["table"]["x1"]["mean"], [10 + 1 / 3 - 2, 10 + 1 / 3, 10 + 1 / 3 + 2])
    assert np.allclose(r["table"]["x4"]["mean"], 10 + 1 / 3)            # 効かない列は平ら
    assert r["best_levels"]["x1"] == 1.0 and r["best_levels"]["x2"] == -1.0
    assert r["table"]["x4"]["share"] == pytest.approx(0.0, abs=1e-12)


def test_larger_the_better_sn_reuses_spc_and_is_not_the_decision():
    import spc
    d = doe.doe_orthogonal_array("L9", 2)
    rng = np.random.default_rng(9)
    Y = 5 + d["coded"][:, :1] + 0.3 * rng.normal(size=(9, 4))
    r = mv.doe_main_effects(d, Y, goal="larger")
    assert np.allclose(r["sn_per_run"], [spc.spc_mt_sn_ratio(row)["sn_ratio_db"] for row in Y])
    assert np.allclose(r["sn_per_run"], -10 * np.log10(np.mean(1 / Y ** 2, axis=1)))
    assert "Box 1988" in r["decision_basis"]
    # 望目: 平均 0 の付近でばらつきの小さい水準(SN は平均を大きくする水準を選びうる)
    Y2 = np.stack([np.where(d["coded"][:, 0] > 0, 1.0, 10.0) + s * np.where(d["coded"][:, 1] > 0, 0.1, 1.0)
                   for s in (-1, 0, 1)], axis=1)
    r2 = mv.doe_main_effects(d, Y2, goal="nominal")
    assert r2["best_levels"]["x2"] == 1.0
    with pytest.raises(ValueError):
        mv.doe_main_effects(d, Y2[:, 0], goal="nominal")                  # 繰り返しが無い


# --------------------------------------------------------------------------- #
# 5. 特徴量                                                                    #
# --------------------------------------------------------------------------- #
def test_image_features_have_names_units_and_never_guess_the_range():
    g = np.linspace(0.0, 1.0, 32)
    imgs = [np.outer(g, g) * s for s in (100.0, 2000.0, 4095.0)]
    t = mv.feat_image_vector(imgs, ["mean", "saturated_fraction", "entropy_bits", "grad_energy"],
                             data_range=(0, 4095), unit="DN")
    assert t["names"] == ["mean", "saturated_fraction", "entropy_bits", "grad_energy"]
    assert t["units"] == ["DN", "1", "bit", "DN^2/px^2"]
    assert t["matrix"][0, 0] == pytest.approx(np.outer(g, g).mean() * 100)
    assert t["matrix"][2, 1] == pytest.approx(1 / 1024)                 # 1 画素だけ 4095
    with pytest.raises(ValueError, match="data_range"):
        mv.feat_image_vector(imgs, ["saturated_fraction"])
    with pytest.raises(ValueError, match="outside data_range"):
        mv.feat_image_vector(imgs, ["dark_fraction"], data_range=(0, 1000))
    with pytest.raises(ValueError):
        mv.feat_image_vector(imgs, ["sharpness"])
    with pytest.raises(ValueError):
        mv.feat_image_vector([np.zeros((2, 2))])


# --------------------------------------------------------------------------- #
# 6. 台帳と公開経路                                                             #
# --------------------------------------------------------------------------- #
def test_ledger_and_public_tier_and_fuzzer():
    import fullseye as fs
    import opsmultivar as om
    import typed_catalog as tc
    sys.path.insert(0, str(ROOT / "tools"))
    import chain_fuzz as cf
    assert set(om.list_ops("analysis")) | set(om.list_ops("features")) == set(mv.__all__)
    assert om.missing() == []
    for name in mv.__all__:
        assert hasattr(fs.ledger, name), name
    rows = {r[0]: r for r in tc.catalog() if r[0] in mv.__all__}
    assert set(rows) == set(mv.__all__)
    for name in mv.__all__:
        args, kw = cf.OP_ARG_BUILDERS[name](None, np.random.default_rng(0))
        assert cf.TYPE_CHECKS[rows[name][3]](getattr(mv, name)(*args, **kw)), name


def test_op_summaries_have_matching_fingerprints():
    sys.path.insert(0, str(ROOT / "tools"))
    import opdocs
    d = json.loads((ROOT / "docs" / "i18n" / "op_summary.json").read_text(encoding="utf-8"))
    for name in mv.__all__:
        line = getattr(mv, name).__doc__.strip().splitlines()[0]
        e = d["summaries"]["multivar/" + name]
        assert e["fp"] == opdocs.fingerprint(line), name
        for lang in ("ja", "zh", "tw", "ko", "de", "hi"):
            assert e[lang].strip(), (name, lang)
