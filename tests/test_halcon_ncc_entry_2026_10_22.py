import numpy as np
import pytest
from scipy.ndimage import shift

import matching
import shapematch


def test_prepared_ncc_model_owns_template_and_records_prepared_values():
    template = np.arange(20, dtype=np.float32).reshape(4, 5)
    original = template.copy()
    model = matching.create_ncc_model(template)

    template[:] = -99
    np.testing.assert_array_equal(model["template"], original.astype(np.float64))
    assert model["template"].dtype == np.float64
    assert model["dtype"] == np.dtype(np.float32)
    assert model["shape"] == (4, 5)
    assert model["origin"] == (2, 2)
    assert model["norm"] == np.linalg.norm(original - original.mean())
    np.testing.assert_allclose(np.linalg.norm(model["t0n"]), 1.0)
    assert isinstance(model["version"], str)


def test_prepared_and_raw_ncc_maps_are_bit_identical_after_caller_mutation():
    rng = np.random.default_rng(101022)
    template = rng.normal(size=(8, 7))
    original = template.copy()
    image = rng.normal(size=(35, 37))
    model = matching.create_ncc_model(template)

    raw = matching._ncc_map(original, image)
    template[:] = 1e9
    prepared = matching._ncc_map(model, image)
    np.testing.assert_array_equal(prepared, raw)


def test_find_ncc_model_returns_two_matches_with_iou_suppression():
    rng = np.random.default_rng(7022)
    template = rng.normal(size=(8, 8))
    image = rng.normal(scale=0.01, size=(50, 60))
    image[5:13, 7:15] = template
    image[31:39, 42:50] = template
    result = matching.find_ncc_model(
        matching.create_ncc_model(template), image, 0.9, num_matches=2
    )
    assert {(m["row_tl"], m["col_tl"]) for m in result["matches"]} == {
        (5, 7), (31, 42)
    }
    assert result["matches"][0]["score"] >= result["matches"][1]["score"]
    assert result["score"] == result["matches"][0]["score"]


def test_legacy_ncc_multiple_entry_delegates_to_shared_search_core():
    rng = np.random.default_rng(7007)
    template = rng.normal(size=(7, 9))
    image = rng.normal(scale=0.01, size=(45, 47))
    image[4:11, 5:14] = template
    image[27:34, 31:40] = template
    model = matching.create_ncc_model(template)
    core = matching.find_ncc_model(
        model, image, 0.9, num_matches=2, min_distance=5
    )["matches"]
    legacy = shapematch.find_ncc_models(
        model, image, 0.9, max_matches=2, min_distance=5
    )["matches"]
    assert legacy == core


def test_subpixel_interpolation_recovers_fractional_shift_within_point_one():
    y, x = np.mgrid[-1:1:25j, -1:1:25j]
    template = np.exp(-5 * (x * x + y * y)) * (1 + 0.2 * x - 0.1 * y)
    base = np.zeros((70, 75))
    base[20:45, 24:49] = template
    fractional = (0.35, -0.30)
    image = shift(base, fractional, order=1, mode="constant")
    result = matching.find_ncc_model(
        matching.create_ncc_model(template), image, subpixel="interpolation"
    )
    assert result["row_sub"] == pytest.approx(32 + fractional[0], abs=0.1)
    assert result["col_sub"] == pytest.approx(36 + fractional[1], abs=0.1)


def test_subpixel_border_returns_integer_and_unsupported_knobs_fail():
    template = np.arange(16, dtype=float).reshape(4, 4)
    image = np.zeros((15, 15))
    image[:4, :4] = template
    model = matching.create_ncc_model(template)
    result = matching.find_ncc_model(model, image, subpixel="interpolation")
    assert result["row_sub"] == result["row"]
    assert result["col_sub"] == result["col"]
    for name in ("angle_start", "angle_extent", "num_levels"):
        with pytest.raises(NotImplementedError, match=name):
            matching.find_ncc_model(model, image, **{name: 0})
