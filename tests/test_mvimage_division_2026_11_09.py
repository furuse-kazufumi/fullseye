"""Regression tests for mvimage.undistort_division beyond its valid radius and the
model note of calib.gen_radial_distortion_map (2026-11-09 op audit g2_calib_ct).

For kappa < 0 the denominator 1 + kappa r^2 reaches 0 at r = 1/sqrt(-kappa):
before the fix undistort_division returned (inf, nan) there and, outside it,
points folded to the opposite side of the principal point (-1928.5 at
r = 848.5 for kappa = -2e-6) without any sign of trouble."""
import numpy as np
import pytest

import calib
import mvimage


def test_beyond_valid_radius_is_nan():
    k = -2e-6
    rmax = 1.0 / np.sqrt(-k)
    x, y = mvimage.undistort_division(np.array([1.2 * rmax, rmax]), np.array([0.0, 0.0]), k)
    assert np.isnan(x).all() and np.isnan(y).all()


def test_inside_valid_radius_round_trips():
    k = -2e-6
    rng = np.random.default_rng(0)
    r = rng.uniform(0, 0.95 / np.sqrt(-k), 2000)
    a = rng.uniform(0, 2 * np.pi, 2000)
    xd, yd = r * np.cos(a), r * np.sin(a)
    xu, yu = mvimage.undistort_division(xd, yd, k)
    assert np.isfinite(xu).all()
    xb, yb = mvimage.distort_division(xu, yu, k)
    assert np.max(np.hypot(xb - xd, yb - yd)) < 1e-9


def test_positive_kappa_has_no_limit():
    x, y = mvimage.undistort_division(np.array([5000.0]), np.array([-3000.0]), 2e-6)
    assert np.isfinite(x).all() and np.isfinite(y).all()


def test_no_runtime_warning_at_the_singular_radius():
    with np.errstate(all="raise"):
        mvimage.undistort_division(np.array([1.0 / np.sqrt(2e-6)]), np.array([0.0]), -2e-6)


def test_change_radial_distortion_image_fills_folded_pixels():
    # output camera with strong negative kappa: the corners are beyond its valid radius
    im = np.random.default_rng(1).random((64, 64))
    cam = {"fx": 50.0, "fy": 50.0, "cx": 31.5, "cy": 31.5, "kappa": 0.0}
    out_cam = dict(cam, kappa=-1.0 / 30.0 ** 2)
    out = mvimage.change_radial_distortion_image(im, cam, out_cam, fill=-1.0)
    assert out[0, 0] == -1.0 and out[32, 32] != -1.0


def test_gen_radial_distortion_map_is_documented_as_first_order():
    # the map is r_in = r_out (1 + kappa r_out^2), not the exact inverse of the
    # division model; the gap is pinned so a silent change of model shows up
    k = -2e-6
    m = calib.gen_radial_distortion_map({"fx": 1.0, "fy": 1.0, "cx": 320.0, "cy": 240.0}, k, (480, 640))
    rr, cc = np.mgrid[0:480, 0:640].astype(float)
    dx, dy = mvimage.distort_division(cc - 320.0, rr - 240.0, k)
    gap = np.nanmax(np.hypot(m["col_map"] - (dx + 320.0), m["row_map"] - (dy + 240.0)))
    assert gap == pytest.approx(46.73, abs=0.01)
    doc = calib.gen_radial_distortion_map.__doc__
    assert "一次" in doc and "distort_division" in doc
