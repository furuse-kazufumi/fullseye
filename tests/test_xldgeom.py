"""Ground-truth tests for the xldgeom contour-geometry tier.

Exercises backends_xldgeom.build() WITHOUT importing ops.py:
  1. a tiny _Op stub captures (name, halcon, in_sort, out_sort, fn),
  2. a FUNCTIONAL GATE runs every op on canonical contours across (a,b) pairs,
  3. per-op GROUND-TRUTH tests prove each claimed geometric behaviour on a
     constructed input (square area, 30deg orientation, DP -> 2 points, ...).
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import backends_xldgeom as X

# Helpers required by the build() contract.
norm = lambda x: (x / m if (m := float(np.max(np.abs(x)))) > 1e-8 else x)
binm = lambda v: np.asarray(v) > 0.5

IMAGE, REGION, FEATURE, CONTOUR = "image", "region", "feature", "contour"
AB_PAIRS = [(0.3, 0.4), (0.6, 0.7), (0.15, 0.85)]


class _Op:
    def __init__(self, *a):
        self.name = a[0]
        self.category = a[1]
        self.halcon = a[2]
        self.in_sort = a[3]
        self.out_sort = a[4]
        self.fn = a[5]


def _build():
    return X.build(_Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm)


# --------------------------------------------------------------------------- #
# canonical fixtures
# --------------------------------------------------------------------------- #
def _square(scale=1.0, origin=(0.0, 0.0)):
    r0, c0 = origin
    return np.array(
        [[r0, c0], [r0, c0 + scale], [r0 + scale, c0 + scale], [r0 + scale, c0]],
        np.float64,
    )


def _canonical():
    """A contour dict with a square, a diagonal line and a coarse circle."""
    t = np.linspace(0.0, 30.0, 40)
    line = np.stack([t, t], axis=1)  # 45deg diagonal
    th = np.linspace(0.0, 2.0 * math.pi, 24, endpoint=False)
    circle = np.stack([20.0 + 10.0 * np.sin(th), 20.0 + 10.0 * np.cos(th)], axis=1)
    return {"shape": (100, 100), "cs": [_square(10.0), line, circle]}


# --------------------------------------------------------------------------- #
# structural expectations
# --------------------------------------------------------------------------- #
def test_registry_shape():
    ops = _build()
    assert len(ops) == 10
    names = [op.name for op in ops]
    assert len(set(names)) == len(names), "op names must be unique"
    for op in ops:
        assert op.name.startswith("xg_")
        assert op.in_sort == CONTOUR
        assert op.out_sort in (FEATURE, CONTOUR)
        # faithful ops keep a real _xld HALCON name; the three reinterpreted ops
        # (clip/crop/regress) carry "" — genuine algorithm, no false coverage claim.
        assert op.halcon == "" or op.halcon.endswith("_xld")
    assert {op.name for op in ops if not op.halcon} == {
        "xg_clip_contours", "xg_crop_contours", "xg_regress_contours"}


# --------------------------------------------------------------------------- #
# FUNCTIONAL GATE
# --------------------------------------------------------------------------- #
def _assert_contour(out):
    assert isinstance(out, dict)
    assert "shape" in out and "cs" in out
    assert isinstance(out["cs"], list)
    for c in out["cs"]:
        arr = np.asarray(c)
        assert arr.ndim == 2 and arr.shape[1] == 2
        assert arr.dtype == np.float64
        assert np.all(np.isfinite(arr))


def test_functional_gate():
    ops = _build()
    cv = _canonical()
    for op in ops:
        for (a, b) in AB_PAIRS:
            out = op.fn(cv, a, b)
            if op.out_sort == FEATURE:
                val = float(np.asarray(out).reshape(-1)[0])
                assert math.isfinite(val), f"{op.name} non-finite at {(a, b)}"
                assert isinstance(out, (float, np.floating)), f"{op.name} not scalar float"
            else:
                _assert_contour(out)


def test_fail_soft_on_degenerate_inputs():
    ops = _build()
    degenerate = [
        {"shape": (0, 0), "cs": []},                       # empty
        {"shape": (10, 10), "cs": [np.zeros((1, 2))]},     # single point
        {"shape": (10, 10), "cs": [np.ones((5, 2))]},      # all-identical points
        {},                                                # missing keys
        None,                                              # not even a dict
    ]
    for op in ops:
        for cv in degenerate:
            out = op.fn(cv, 0.5, 0.5)  # must not raise
            if op.out_sort == FEATURE:
                assert math.isfinite(float(np.asarray(out).reshape(-1)[0]))
            else:
                _assert_contour(out)


def test_determinism():
    ops = _build()
    cv = _canonical()
    for op in ops:
        o1 = op.fn(cv, 0.4, 0.6)
        o2 = op.fn(cv, 0.4, 0.6)
        if op.out_sort == FEATURE:
            assert float(np.asarray(o1)) == float(np.asarray(o2))
        else:
            assert len(o1["cs"]) == len(o2["cs"])
            for c1, c2 in zip(o1["cs"], o2["cs"]):
                assert np.array_equal(c1, c2)


# --------------------------------------------------------------------------- #
# GROUND-TRUTH: contour -> feature
# --------------------------------------------------------------------------- #
def test_area_unit_square():
    cv = {"shape": (10, 10), "cs": [_square(1.0)]}
    assert abs(X.xg_area_center(cv, 0.5, 0.5) - 1.0) < 1e-9


def test_area_scaled_square():
    cv = {"shape": (100, 100), "cs": [_square(5.0)]}  # 5x5 square -> area 25
    assert abs(X.xg_area_center(cv, 0.5, 0.5) - 25.0) < 1e-9


def test_moments_unit_square_corners():
    # 4 corners of a unit square: centroid (0.5,0.5); mu20=mu02=0.25 -> sum 0.5
    cv = {"shape": (10, 10), "cs": [_square(1.0)]}
    assert abs(X.xg_moments(cv, 0.5, 0.5) - 0.5) < 1e-12


def test_orientation_30deg_line():
    t = np.linspace(0.0, 10.0, 60)
    ang = math.radians(30.0)
    line = np.stack([t * math.sin(ang), t * math.cos(ang)], axis=1)  # (row=y, col=x)
    cv = {"shape": (100, 100), "cs": [line]}
    deg = float(X.xg_orientation(cv, 0.5, 0.5)) * 180.0
    assert abs(deg - 30.0) < 1e-6


def test_orientation_scaled_to_unit_interval():
    t = np.linspace(0.0, 10.0, 60)
    ang = math.radians(120.0)
    line = np.stack([t * math.sin(ang), t * math.cos(ang)], axis=1)
    cv = {"shape": (100, 100), "cs": [line]}
    scaled = float(X.xg_orientation(cv, 0.5, 0.5))
    assert 0.0 <= scaled < 1.0
    assert abs(scaled * 180.0 - 120.0) < 1e-6


def _ellipse(a_ax, b_ax, n=240):
    th = np.linspace(0.0, 2.0 * math.pi, n, endpoint=False)
    return np.stack([b_ax * np.sin(th), a_ax * np.cos(th)], axis=1)  # (row,col)=(y,x)


def test_elliptic_axis_ratio():
    # ellipse a=3 (along x/col), b=1 (along y/row): Var(x)=4.5, Var(y)=0.5
    cv = {"shape": (100, 100), "cs": [_ellipse(3.0, 1.0)]}
    ratio = float(X.xg_elliptic_axis(cv, 0.5, 0.5))
    assert abs(ratio - 3.0) < 1e-6


def test_eccentricity_matches_ellipse_formula():
    cv = {"shape": (100, 100), "cs": [_ellipse(3.0, 1.0)]}
    ecc = float(X.xg_eccentricity(cv, 0.5, 0.5))
    assert abs(ecc - math.sqrt(1.0 - 1.0 / 9.0)) < 1e-6


def test_eccentricity_line_vs_circle():
    t = np.linspace(0.0, 10.0, 50)
    line = np.stack([t, 0.5 * t], axis=1)
    circle = _ellipse(5.0, 5.0)
    assert float(X.xg_eccentricity({"shape": (50, 50), "cs": [line]}, 0.5, 0.5)) > 0.999
    assert float(X.xg_eccentricity({"shape": (50, 50), "cs": [circle]}, 0.5, 0.5)) < 1e-3


def test_height_width_ratio():
    # bbox rows [0,2], cols [0,1] -> ratio 2
    pts = np.array([[0.0, 0.0], [2.0, 0.0], [2.0, 1.0], [0.0, 1.0]], np.float64)
    cv = {"shape": (10, 10), "cs": [pts]}
    assert abs(float(X.xg_height_width_ratio(cv, 0.5, 0.5)) - 2.0) < 1e-9


def test_regress_collinear_zero_residual():
    x = np.linspace(0.0, 20.0, 30)
    line = np.stack([2.0 * x, x], axis=1)  # y = 2x exactly
    cv = {"shape": (100, 100), "cs": [line]}
    assert float(X.xg_regress_contours(cv, 0.5, 0.5)) < 1e-9


def test_regress_recovers_perpendicular_rms():
    rng = np.random.default_rng(0)
    n = 4000
    sigma = 0.5
    x = np.linspace(0.0, 100.0, n)         # long axis -> line is the x-axis
    y = rng.normal(0.0, sigma, n)          # perpendicular scatter
    cv = {"shape": (200, 200), "cs": [np.stack([y, x], axis=1)]}
    rms = float(X.xg_regress_contours(cv, 0.5, 0.5))
    assert abs(rms - sigma) < 0.05


# --------------------------------------------------------------------------- #
# GROUND-TRUTH: contour -> contour
# --------------------------------------------------------------------------- #
def test_gen_polygons_noisy_line_to_endpoints():
    rng = np.random.default_rng(0)
    n = 40
    rows = np.linspace(0.0, 100.0, n)
    cols = rng.uniform(-0.3, 0.3, n)       # tiny perpendicular noise
    cv = {"shape": (110, 10), "cs": [np.stack([rows, cols], axis=1)]}
    out = X.xg_gen_polygons(cv, 0.15, 0.5)  # eps ~= 0.15 * 100 >> noise
    assert len(out["cs"]) == 1
    assert out["cs"][0].shape[0] == 2       # collapses to the two endpoints


def test_gen_polygons_preserves_corners():
    # an L-shape: two long legs meeting at a right angle -> DP keeps 3 vertices
    leg = np.linspace(0.0, 50.0, 30)
    horiz = np.stack([np.zeros_like(leg), leg], axis=1)
    vert = np.stack([leg, np.full_like(leg, 50.0)], axis=1)
    poly = np.concatenate([horiz, vert[1:]], axis=0)
    cv = {"shape": (60, 60), "cs": [poly]}
    out = X.xg_gen_polygons(cv, 0.05, 0.5)
    assert out["cs"][0].shape[0] == 3       # start, corner, end


def test_clip_contours_drops_short():
    short = _square(1.0)          # open polyline length 3
    big = _square(100.0)          # open polyline length 300
    cv = {"shape": (200, 200), "cs": [short, big]}
    out = X.xg_clip_contours(cv, 0.5, 0.5)  # threshold 150
    assert len(out["cs"]) == 1
    assert _len(out["cs"][0]) > 100


def test_clip_contours_keeps_all_when_a_zero():
    cv = {"shape": (200, 200), "cs": [_square(1.0), _square(100.0)]}
    out = X.xg_clip_contours(cv, 0.0, 0.5)
    assert len(out["cs"]) == 2


def _len(c):
    d = np.diff(c, axis=0)
    return float(np.sum(np.hypot(d[:, 0], d[:, 1])))


def test_crop_contours_central_window():
    # points on the main diagonal at 0,10,...,90 in a 100x100 image
    idx = np.arange(0, 100, 10, dtype=np.float64)
    pts = np.stack([idx, idx], axis=1)
    cv = {"shape": (100, 100), "cs": [pts]}
    out = X.xg_crop_contours(cv, 0.5, 0.5)  # window rows/cols [25,75]
    kept = out["cs"][0]
    assert kept.shape[0] == 5               # 30,40,50,60,70
    assert kept[:, 0].min() >= 25.0 and kept[:, 0].max() <= 75.0


def test_crop_contours_full_window_keeps_everything():
    idx = np.arange(0, 100, 10, dtype=np.float64)
    pts = np.stack([idx, idx], axis=1)
    cv = {"shape": (100, 100), "cs": [pts]}
    out = X.xg_crop_contours(cv, 1.0, 0.5)
    assert out["cs"][0].shape[0] == pts.shape[0]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
