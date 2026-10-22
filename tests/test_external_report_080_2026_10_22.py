"""Regression gates for externally reported 0.8.0 boundary cases."""

import warnings

import numpy as np
import pytest

import matching


@pytest.mark.parametrize(
    "scale", (1, 1e-180, 1e-100, 1e-8, 1e-6, 1e6, 1e100, 1e155, 1e160, 1e300)
)
def test_ncc_self_match_survives_extreme_finite_scales(scale):
    template = np.arange(25, dtype=float).reshape(5, 5) * scale
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        raw = matching._ncc_map(template, template)
        prepared = matching._ncc_map(matching.create_ncc_model(template), template)
    assert raw[0, 0] == pytest.approx(1.0, abs=1e-12)
    np.testing.assert_array_equal(prepared, raw)


def test_ncc_random_crop_and_mixed_extreme_scales():
    rng = np.random.default_rng(800)
    base = rng.random((64, 64))
    pattern = base[23:39, 17:33].copy()
    for template_scale, image_scale in ((1e-180, 1e-180), (1e300, 1e300),
                                        (1e-150, 1e150)):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = matching.find_ncc_model(
                matching.create_ncc_model(pattern * template_scale),
                base * image_scale,
                min_score=0.9,
            )
        assert (result["row_tl"], result["col_tl"]) == (23, 17)
        assert result["score"] == pytest.approx(1.0, abs=1e-12)


def test_ncc_constant_and_nonfinite_contracts():
    assert np.count_nonzero(matching._ncc_map(np.zeros((3, 3)), np.zeros((5, 5)))) == 0
    with pytest.raises(ValueError, match="NaN or infinity"):
        matching._ncc_map(np.full((3, 3), np.nan), np.zeros((5, 5)))
