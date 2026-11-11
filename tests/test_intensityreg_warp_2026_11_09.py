"""Regression tests for intensityreg.warp_parametric input checks and the affine
fast path (2026-11-09 op audit g2_calib_ct).

One NaN pixel used to spread through the cubic-spline prefilter and come back
as an all-zero image (262144/262144 pixels) without an exception; RGB raised
scipy's RuntimeError and an empty image returned an empty array."""
import numpy as np
import pytest
from scipy import ndimage

import intensityreg as ir


def _img(n=96, seed=0):
    rng = np.random.default_rng(seed)
    return ndimage.gaussian_filter(rng.random((n, n)), 2.0)


def test_nan_pixel_is_refused():
    a = _img()
    a[40, 40] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        ir.warp_parametric(a, np.eye(3))


@pytest.mark.parametrize("bad", [np.zeros((0, 4)), np.zeros((8, 8, 3)), np.zeros(5)])
def test_bad_shapes_are_refused(bad):
    with pytest.raises(ValueError):
        ir.warp_parametric(bad, np.eye(3))


@pytest.mark.parametrize("shape", [(0, 4), (-3, 4), (2.5, 4), (4,)])
def test_bad_out_shape_is_refused(shape):
    with pytest.raises(ValueError, match="out_shape"):
        ir.warp_parametric(_img(), np.eye(3), out_shape=shape)


@pytest.mark.parametrize("order", [-1, 6, 1.5, True])
def test_bad_order_is_refused(order):
    with pytest.raises(ValueError, match="order"):
        ir.warp_parametric(_img(), np.eye(3), order=order)


def test_integer_shift_is_exact_inside():
    a = _img()
    W = np.array([[1, 0, 7], [0, 1, 3], [0, 0, 1.0]])
    out = ir.warp_parametric(a, W)
    assert np.max(np.abs(out[3 + 5:-5, 7 + 5:-5] - a[5:-5 - 3, 5:-5 - 7])) < 1e-12


@pytest.mark.parametrize("order", [1, 3])
def test_affine_fast_path_equals_map_coordinates(order):
    a = _img()
    t = 0.2
    W = np.array([[1.1 * np.cos(t), -np.sin(t), 4.3], [np.sin(t), 0.9 * np.cos(t), -2.2], [0, 0, 1.0]])
    out = ir.warp_parametric(a, W, out_shape=(80, 100), order=order)
    yy, xx = np.mgrid[0:80, 0:100].astype(float)
    Wi = np.linalg.inv(W)
    X = Wi[0, 0] * xx + Wi[0, 1] * yy + Wi[0, 2]
    Y = Wi[1, 0] * xx + Wi[1, 1] * yy + Wi[1, 2]
    ref = ndimage.map_coordinates(a, [Y, X], order=order, mode="constant", cval=0.0)
    assert out.shape == (80, 100)
    assert np.max(np.abs(out - ref)) < 1e-12


def test_homography_path_still_works():
    a = _img()
    W = np.array([[1, 0.02, 1.0], [0.01, 1, -1.0], [1e-4, -2e-4, 1.0]])
    out = ir.warp_parametric(a, W)
    assert np.isfinite(out).all() and out.std() > 0


def test_order1_does_not_overshoot_a_step():
    a = np.zeros((64, 64))
    a[:, 32:] = 1.0
    W = np.array([[1, 0, 0.37], [0, 1, 0.0], [0, 0, 1.0]])
    o1 = ir.warp_parametric(a, W, order=1)
    o3 = ir.warp_parametric(a, W, order=3)
    assert o1.min() >= 0.0 and o1.max() <= 1.0
    assert o3.min() < -0.01 or o3.max() > 1.01        # the documented cubic overshoot
