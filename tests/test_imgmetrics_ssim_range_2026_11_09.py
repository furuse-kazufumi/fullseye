"""Regression tests for the float data_range guess of imgmetrics.ssim
(2026-11-09 op audit g2_calib_ct).

A float image with values 0..0.05 (CT attenuation in 1/mm, say) was taken to
have data_range 1.0; SSIM's constants scale with data_range, so the score was
inflated from 0.515 to 0.993 without an exception."""
import numpy as np
import pytest

import imgmetrics
from metriccontract import MetricContractError


def _pair(scale=0.05, noise=0.05, seed=0):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:128, 0:128] / 127.0
    base = 0.5 + 0.3 * np.sin(9 * x) * np.cos(7 * y) + 0.15 * (x > 0.5)
    a = np.clip(base, 0, 1)
    b = np.clip(a + rng.normal(0, noise, a.shape), 0, 1)
    return a * scale, b * scale


def test_narrow_float_range_needs_explicit_data_range():
    a, b = _pair()
    with pytest.raises(MetricContractError, match="data_range"):
        imgmetrics.ssim(a, b)
    with pytest.raises(MetricContractError, match="data_range"):
        imgmetrics.ssim_map(a, b)


def test_explicit_data_range_matches_skimage():
    sk = pytest.importorskip("skimage.metrics")
    a, b = _pair()
    ours = imgmetrics.ssim(a, b, data_range=0.05)
    ref = sk.structural_similarity(a, b, data_range=0.05, gaussian_weights=True, sigma=1.5,
                                   use_sample_covariance=False)
    assert abs(ours - ref) < 1e-12


def test_inflation_is_what_the_guess_would_have_given():
    a, b = _pair()
    right = imgmetrics.ssim(a, b, data_range=0.05)
    wrong = imgmetrics.ssim(a, b, data_range=1.0)
    assert wrong > right + 0.3                      # the size of the silent error


def test_full_range_float_still_guesses_one():
    a, b = _pair(scale=1.0)
    assert imgmetrics.ssim(a, b) == imgmetrics.ssim(a, b, data_range=1.0)


def test_integer_dtypes_unchanged():
    a, b = _pair(scale=1.0)
    a8, b8 = (a * 255).astype(np.uint8), (b * 255).astype(np.uint8)
    assert imgmetrics.ssim(a8, b8) == imgmetrics.ssim(a8, b8, data_range=255.0)


def test_ms_ssim_has_the_same_guard():
    rng = np.random.default_rng(3)
    a = rng.random((192, 192)) * 0.1
    with pytest.raises(MetricContractError, match="data_range"):
        imgmetrics.ms_ssim(a, a)
