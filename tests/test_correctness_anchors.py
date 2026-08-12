"""Ground-truth correctness anchors for representative operators.

The functional gate only proves an op *returns the declared sort*; these anchors
prove a handful of ops actually *compute the right thing*, so a regression that
silently changes the math is caught.
"""
from __future__ import annotations

import numpy as np
import pytest
from scipy import ndimage

import ops

RT = ops.RT


def _img(n=48):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    return np.clip(xx / (n - 1), 0, 1)


def test_identity_returns_input_unchanged():
    v = _img()
    assert np.array_equal(RT["identity"](v, 0.3, 0.7), v)


def test_invert_is_one_minus():
    v = _img()
    assert np.allclose(RT["invert"](v, 0.5, 0.5), 1.0 - v)


def test_threshold_binarises_above_a():
    v = _img()
    out = RT["threshold"](v, 0.5, 0.0)
    assert set(np.unique(out).tolist()) <= {0.0, 1.0}
    assert np.array_equal(out, (v > 0.5).astype(np.float64))


def test_gaussian_reduces_noise_variance():
    rng = np.random.default_rng(0)
    clean = _img()
    noisy = np.clip(clean + rng.normal(0, 0.15, clean.shape), 0, 1)
    smoothed = RT["gaussian"](noisy, 0.6, 0.0)
    assert np.var(smoothed - clean) < np.var(noisy - clean)


def test_otsu_separates_bimodal_image():
    img = np.zeros((40, 40)); img[:, 20:] = 0.9
    img += np.random.default_rng(1).normal(0, 0.02, img.shape)
    reg = RT["otsu"](np.clip(img, 0, 1), 0.0, 0.0)
    # foreground should be the bright right half
    assert reg[:, 30].mean() > 0.9 and reg[:, 10].mean() < 0.1


def test_sobel_responds_to_a_step_edge():
    img = np.zeros((32, 32)); img[:, 16:] = 1.0
    mag = RT["sobel_mag"](img, 0.0, 0.0)
    assert mag[:, 14:18].mean() > mag[:, :10].mean() + 0.3


def test_region_dilate_grows_erode_shrinks():
    reg = np.zeros((32, 32)); reg[12:20, 12:20] = 1.0
    assert RT["reg_dilate"](reg, 0.3, 0.0).sum() > reg.sum()
    assert RT["reg_erode"](reg, 0.3, 0.0).sum() < reg.sum()


def test_fill_holes_fills_interior():
    reg = np.zeros((32, 32)); reg[8:24, 8:24] = 1.0; reg[13:19, 13:19] = 0.0
    filled = RT["fill_holes"](reg, 0.0, 0.0)
    assert filled[16, 16] == 1.0 and filled.sum() > reg.sum()


def test_blob_count_counts_components():
    reg = np.zeros((40, 40))
    reg[4:10, 4:10] = 1.0; reg[4:10, 20:26] = 1.0; reg[20:26, 4:10] = 1.0
    assert float(RT["blob_count"](reg, 0.0, 0.0)) == 3.0


def test_psnr_is_max_for_identical_and_drops_with_noise():
    v = _img()
    assert ops.psnr(v, v) >= 99.0
    noisy = v + np.random.default_rng(2).normal(0, 0.1, v.shape)
    assert ops.psnr(noisy, v) < ops.psnr(RT["gaussian"](noisy, 0.5, 0.0), v) + 30
    assert ops.psnr(noisy, v) < 99.0
