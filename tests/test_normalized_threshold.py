"""Issue #196: 正規化してから正規化後の単位でしきい値を決める 3 op の真値門。"""
from __future__ import annotations

import math

import numpy as np
import pytest

import normalized_threshold as N
import ops
from fullseye.mcp.catalog import Catalog
from fullseye.mcp.server import call_tool
from fullseye.opsearch import plan, search_ops


def test_ptile_matches_an_analytic_order_statistic_for_both_polarities():
    # 0..99 の一様な既知ヒストグラム。上/下 20 % と残りの境は 79/80、19/20。
    image = np.arange(100, dtype=np.float64).reshape(10, 10)
    bright = N.ptile_threshold(image, 0.20, "bright")
    dark = N.ptile_threshold(image, 0.20, "dark")
    assert bright == 79.5
    assert dark == 19.5
    assert np.count_nonzero(image > bright) == 20
    assert np.count_nonzero(image < dark) == 20


@pytest.mark.parametrize("p", [0.0, 1.0, -0.1, 1.1, np.nan])
def test_ptile_fails_closed_when_the_cdf_has_no_two_sides(p):
    with pytest.raises(ValueError, match=r"0 < p < 1"):
        N.ptile_threshold(np.arange(9).reshape(3, 3), p)


@pytest.mark.parametrize("shape", [(4, 4), (1, 1)])
@pytest.mark.parametrize("polarity", ["bright", "dark"])
def test_ptile_small_images_keep_the_histogram_boundary_in_bounds(shape, polarity):
    image = np.arange(np.prod(shape), dtype=np.float64).reshape(shape)
    threshold = N.ptile_threshold(image, 0.999, polarity)
    assert np.isfinite(threshold)


@pytest.mark.parametrize("value", [0.0, 7.0])
@pytest.mark.parametrize("polarity", ["bright", "dark"])
def test_ptile_constant_images_return_the_only_grey_value(value, polarity):
    image = np.full((4, 4), value)
    assert N.ptile_threshold(image, 0.999, polarity) == value


def test_standardize_zscore_has_zero_mean_and_unit_population_variance():
    image = np.array([[1.0, 2.0, 4.0], [8.0, 16.0, 32.0]])
    z = N.image_standardize_raw(image, "zscore")
    assert z.dtype == np.float64
    assert float(np.mean(z)) == pytest.approx(0.0, abs=2e-16)
    assert float(np.var(z)) == pytest.approx(1.0, abs=5e-16)


def test_only_robust_scale_stays_fixed_when_one_outlier_is_mixed_in():
    clean = np.array([[-2.0, -1.0, 0.0, 1.0, 2.0]])
    contaminated = np.array([[-2.0, -1.0, 0.0, 1.0, 200.0]])
    robust_clean = N.image_standardize_raw(clean, "robust")
    robust_bad = N.image_standardize_raw(contaminated, "robust")
    # 中央の 4 点は中央値 0・MAD 1 のままなので、1 bit も動かない。
    assert np.array_equal(robust_clean[0, :4], robust_bad[0, :4])
    ordinary_clean = N.image_standardize_raw(clean, "zscore")
    ordinary_bad = N.image_standardize_raw(contaminated, "zscore")
    assert np.max(np.abs(ordinary_clean[0, :4] - ordinary_bad[0, :4])) > 1.0


@pytest.mark.parametrize("method", ["zscore", "robust", "percentile"])
def test_standardize_constant_image_has_documented_finite_degenerate_values(method):
    image = np.full((4, 5), 7.0)
    assert np.array_equal(N.image_standardize_raw(image, method), np.zeros_like(image))
    assert np.array_equal(N.image_standardize(image, method), np.full_like(image, 0.5))


@pytest.mark.parametrize("method", ["zscore", "robust", "percentile"])
def test_image_standardize_maps_the_requested_raw_sigma_interval_to_unit_range(method):
    image = np.arange(25, dtype=np.float64).reshape(5, 5)
    out = N.image_standardize(image, method, clip_sigma=2.0)
    assert out.dtype == np.float64
    assert float(out.min()) >= 0.0
    assert float(out.max()) <= 1.0
    raw = N.image_standardize_raw(image, method)
    np.testing.assert_allclose(out, np.clip(0.5 + raw / 4.0, 0.0, 1.0))


@pytest.mark.parametrize("k", [2.0, 2.5, 3.0])
def test_sigma_threshold_false_positive_rate_matches_erfc(k):
    rng = np.random.default_rng(196)
    noise = rng.standard_normal((1000, 1000))
    mask = N.sigma_threshold(noise, k, "both")
    measured = float(np.mean(mask))
    theory = math.erfc(k / math.sqrt(2.0))
    # 二項分布の標準誤差 6 個ぶん。固定 seed だが統計的な意味も残す。
    se = math.sqrt(theory * (1.0 - theory) / noise.size)
    assert measured == pytest.approx(theory, abs=6.0 * se)


def test_sigma_threshold_finds_known_signed_defects_and_ledger_reaches_all_three_ops():
    z = np.zeros((9, 9), dtype=np.float64)
    z[2, 3] = 4.0
    z[6, 7] = -4.0
    assert np.argwhere(N.sigma_threshold(z, 3.0, "bright")).tolist() == [[2, 3]]
    assert np.argwhere(N.sigma_threshold(z, 3.0, "dark")).tolist() == [[6, 7]]
    assert sorted(map(tuple, np.argwhere(N.sigma_threshold(z, 3.0, "both")))) == [(2, 3), (6, 7)]
    for name in ("ptile_threshold", "image_standardize", "sigma_threshold"):
        assert name in ops.RT
        assert callable(ops.RT[name])
    assert "image_standardize_raw" not in ops.RT


@pytest.mark.parametrize(
    "fn", [N.ptile_threshold, N.image_standardize, N.image_standardize_raw, N.sigma_threshold])
def test_public_standardization_and_threshold_functions_refuse_empty_input(fn):
    with pytest.raises(ValueError, match="empty input"):
        fn(np.empty((0, 4)))


def test_all_three_ops_are_reachable_from_search_and_the_apply_facade():
    import fullseye as fs

    queries = {
        "ptile_threshold": "P-tile area fraction threshold",
        "image_standardize": "standardize image",
        "sigma_threshold": "robust sigma threshold binarize image",
    }
    for name, query in queries.items():
        indexed = {row["name"] for row in search_ops(query, k=10)["ops"]}
        assert name in indexed
    assert fs.find_op("ptile_threshold").out_sort == "feature"
    assert fs.find_op("image_standardize").out_sort == "image"
    assert fs.find_op("sigma_threshold").out_sort == "region"
    assert all(callable(getattr(fs.op, name)) for name in
               ("ptile_threshold", "image_standardize", "sigma_threshold"))
    assert callable(N.image_standardize_raw)


def test_find_ops_and_plan_return_sourced_tuning_cards_without_an_llm():
    cat = Catalog.load()
    found = call_tool("fullseye_find_ops", {
        "query": "normalize image then threshold in robust sigma units", "limit": 10,
    }, cat)["structuredContent"]
    assert found["tuning_cards"]
    assert all(card["reference"] and card["ops"] for card in found["tuning_cards"])
    assert "sparse_outliers_robust_sigma" in {card["id"] for card in found["tuning_cards"]}

    planned = call_tool("fullseye_plan", {
        "have": "image", "want": "region", "goal": "global raw threshold",
    }, cat)["structuredContent"]
    alternatives = [p for p in planned["plans"] if p.get("alternative_kind") == "normalized_threshold"]
    assert len(alternatives) == 1
    assert alternatives[0]["ops"] == ["image_standardize", "sigma_threshold"]
    assert alternatives[0]["dag"]["stages"][0]["params"] == {"method": "robust"}
    assert planned["tuning_cards"]


def test_plan_helper_adds_only_one_deterministic_normalized_alternative():
    constraints = {"k": 3, "query": "raw global threshold"}
    first = plan("image", "region", constraints=constraints)
    second = plan("image", "region", constraints=constraints)
    a = [p for p in first["plans"] if p.get("alternative_kind") == "normalized_threshold"]
    b = [p for p in second["plans"] if p.get("alternative_kind") == "normalized_threshold"]
    assert a == b and len(a) == 1
