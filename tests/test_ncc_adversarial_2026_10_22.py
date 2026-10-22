"""Adversarial numeric and performance gates for finite NCC inputs."""
from __future__ import annotations

import os
import time
import warnings

import numpy as np
import pytest
from numpy.lib.stride_tricks import sliding_window_view

import matching


def _oracle(template, image):
    t = np.asarray(template, dtype=np.float64)
    x = np.asarray(image, dtype=np.float64)
    ts = t / np.max(np.abs(t)) if np.any(t) else t
    windows = sliding_window_view(x, t.shape)
    scales = np.max(np.abs(windows), axis=(-2, -1), keepdims=True)
    scaled = np.divide(windows, scales, out=np.zeros_like(windows), where=scales != 0)
    t0 = ts - ts.mean()
    tn = np.linalg.norm(t0)
    centered = scaled - scaled.mean(axis=(-2, -1), keepdims=True)
    norms = np.linalg.norm(centered, axis=(-2, -1))
    numerator = np.einsum("ijkl,kl->ij", centered, t0)
    return np.divide(numerator, norms * tn, out=np.zeros_like(norms),
                     where=(norms != 0) & (tn != 0))


@pytest.mark.parametrize("outlier", [1e10, 1e150, 1e200, 1e300])
def test_global_outlier_does_not_destroy_normal_patch(outlier):
    template = np.array([[0.0, 1.0], [1.0, 0.0]])
    image = np.ones((8, 8))
    image[3:5, 3:5] = template
    image[7, 7] = outlier
    raw = matching._ncc_map(template, image)
    prepared = matching._ncc_map(matching.create_ncc_model(template), image)
    np.testing.assert_array_equal(raw, prepared)
    assert raw[3, 3] == 1.0
    result = matching.find_ncc_model(matching.create_ncc_model(template), image, 0.9)
    assert result["found"] and (result["row_tl"], result["col_tl"]) == (3, 3)


def test_mixed_extreme_self_match_is_one():
    image = np.full((5, 5), 1e-200)
    image[2, 2] = 1e200
    assert matching._ncc_map(image, image)[0, 0] == 1.0


def test_hot_pixel_uniform_windows_are_zero_and_true_patch_wins():
    rng = np.random.default_rng(20261022)
    template = rng.random((5, 5))
    image = np.full((400, 400), 0.3)
    image[200, 200] = 3e11
    image[350:355, 350:355] = template
    actual = matching._ncc_map(template, image)
    expected = _oracle(template, image)
    uniform = sliding_window_view(image, template.shape)
    uniform = np.max(uniform, axis=(-2, -1)) == np.min(uniform, axis=(-2, -1))
    assert np.count_nonzero(actual[uniform]) == 0
    assert actual[350, 350] == pytest.approx(1.0, abs=1e-12)
    assert np.max(np.abs(actual - expected)) < 1e-9
    result = matching.find_ncc_model(matching.create_ncc_model(template), image, 0.9)
    assert (result["row_tl"], result["col_tl"]) == (350, 350)


def test_constant_template_exact_range_sweep():
    rng = np.random.default_rng(20261022)
    values = rng.uniform(-1.0, 1.0, 3000)
    assert values.size == 3000
    for value in values:
        template = np.full((6, 6), value)
        model = matching.create_ncc_model(template)
        assert model["constant"] and model["norm"] == 0.0
        assert np.count_nonzero(matching._ncc_map(model, rng.random((8, 9)))) == 0


def test_subnormal_scale_is_finite_and_warning_free():
    template = np.array([[0.0, 5e-324], [1e-323, 1.5e-323]])
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        model = matching.create_ncc_model(template)
        score = matching._ncc_map(model, template)[0, 0]
    assert np.isfinite(model["template_scale"])
    assert model["template_scale_exp"] == 1023
    assert score == pytest.approx(1.0, abs=1e-12)


def test_scaling_boundary_matches_documented_binary_exponents():
    inside = matching.create_ncc_model(np.array([[0.0, 1.5 * 2.0**500]]))
    outside = matching.create_ncc_model(np.array([[0.0, 2.0**501]]))
    assert inside["template_scale_exp"] == 0
    assert outside["template_scale_exp"] == -501


def test_random_scale_sweep_matches_per_window_oracle():
    rng = np.random.default_rng(20261023)
    exponents = rng.uniform(-300.0, 300.0, 300)
    assert exponents.size == 300
    for exponent in exponents:
        scale = 10.0**exponent
        template = rng.normal(size=(3, 4)) * scale
        image = rng.normal(size=(6, 7)) * scale
        actual = matching._ncc_map(template, image)
        prepared = matching._ncc_map(matching.create_ncc_model(template), image)
        np.testing.assert_array_equal(actual, prepared)
        assert np.max(np.abs(actual - _oracle(template, image))) < 1e-9


@pytest.mark.skipif(bool(os.environ.get("PYTEST_XDIST_WORKER")),
                    reason="timing gate must run alone")
def test_512_square_performance_guards():
    rng = np.random.default_rng(20261022)
    template = rng.random((32, 32))
    normal = rng.random((512, 512))
    constant = np.ones((512, 512))
    for image in (normal, constant):
        matching._ncc_map(template, image)

    def best(image):
        samples = []
        for _ in range(15):
            start = time.perf_counter()
            matching._ncc_map(template, image)
            samples.append(time.perf_counter() - start)
        return min(samples)

    # This branch measured 0.0234464 s before the change on the same host.
    assert best(normal) <= 0.0234464 * 1.3
    assert best(constant) < 0.005
