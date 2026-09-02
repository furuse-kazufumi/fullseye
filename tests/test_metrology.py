"""metrology (2-D metrology model): every object type is measured along its own
normal and re-fitted, so the returned parameters reproduce a synthetic ground truth.

Regression for the 2026-09-02 finding: ellipse / rectangle objects used to be
measured as a circle of radius max(axis) with no refit (a 40x15 ellipse came back
as ra=36 rb=33).  Images are anti-aliased by 4x4 supersampling so the true edge
sits exactly on the analytic boundary (pixel-centre convention).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import metrology as mt  # noqa: E402

H = W = 200


def _aa(inside_fn, ss=4):
    """Anti-aliased binary image of the region ``inside_fn(row, col) -> bool``."""
    off = (np.arange(ss) + 0.5) / ss - 0.5
    acc = np.zeros((H, W))
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    for dy in off:
        for dx in off:
            acc += inside_fn(yy + dy, xx + dx)
    return acc / (ss * ss)


def _ellipse_img(row, col, phi, ra, rb):
    ca, sa = np.cos(phi), np.sin(phi)

    def inside(y, x):
        dx, dy = x - col, y - row
        u = dx * ca + dy * sa
        v = -dx * sa + dy * ca
        return (u / ra) ** 2 + (v / rb) ** 2 <= 1.0
    return _aa(inside)


def _rect_img(row, col, phi, l1, l2):
    ca, sa = np.cos(phi), np.sin(phi)

    def inside(y, x):
        dx, dy = x - col, y - row
        u = dx * ca + dy * sa
        v = -dx * sa + dy * ca
        return (np.abs(u) <= l1) & (np.abs(v) <= l2)
    return _aa(inside)


def test_ellipse_object_recovers_axes_40x15():
    img = _ellipse_img(100, 100, 0.0, 40.0, 15.0)
    m = mt.create_metrology_model()
    mt.add_metrology_object_ellipse_measure(m, 100, 100, 0.0, 40, 15, n=48)
    res = mt.apply_metrology_model(m, img)[0]
    p = res["params"]
    assert p is not None, res.get("error")
    assert abs(p["ra"] - 40.0) < 0.3 and abs(p["rb"] - 15.0) < 0.3
    assert abs(p["row"] - 100) < 0.2 and abs(p["col"] - 100) < 0.2
    assert abs(p["phi"]) < np.radians(1.0)
    assert res["rms"] < 0.3
    assert 0.9 < res["score"] <= 1.01          # unit-contrast edge -> amplitude ~1


def test_ellipse_object_rotated_and_offset_reference():
    """Reference slightly off (2 px, 3 % axes, 3 deg) still converges to the truth."""
    phi = 0.5
    img = _ellipse_img(90.0, 110.0, phi, 40.0, 15.0)
    m = mt.create_metrology_model()
    mt.add_metrology_object_ellipse_measure(m, 92, 108, phi + 0.05, 41, 15.5, n=60)
    p = mt.apply_metrology_model(m, img)[0]["params"]
    assert abs(p["ra"] - 40.0) < 0.3 and abs(p["rb"] - 15.0) < 0.3
    assert abs(p["row"] - 90.0) < 0.2 and abs(p["col"] - 110.0) < 0.2
    assert abs(p["phi"] - phi) < np.radians(1.0)


def test_rectangle_object_recovers_40x12():
    img = _rect_img(100, 100, 0.0, 40.0, 12.0)
    m = mt.create_metrology_model()
    mt.add_metrology_object_rectangle2_measure(m, 100, 100, 0.0, 40, 12, n=48)
    res = mt.apply_metrology_model(m, img)[0]
    p = res["params"]
    assert p is not None, res.get("error")
    assert abs(p["l1"] - 40.0) < 0.3 and abs(p["l2"] - 12.0) < 0.3
    assert abs(p["row"] - 100) < 0.2 and abs(p["col"] - 100) < 0.2
    assert abs(p["phi"]) < np.radians(1.0)
    # edge points lie on the four sides, not on a circle of radius 40
    e = res["edge_points"]
    on_long = np.abs(np.abs(e[:, 0] - 100) - 12) < 0.3
    on_short = np.abs(np.abs(e[:, 1] - 100) - 40) < 0.3
    assert np.all(on_long | on_short)


def test_rectangle_object_rotated():
    phi = 0.3
    img = _rect_img(100, 100, phi, 40.0, 12.0)
    m = mt.create_metrology_model()
    mt.add_metrology_object_rectangle2_measure(m, 101, 99, phi - 0.03, 39, 12.5, n=48)
    p = mt.apply_metrology_model(m, img)[0]["params"]
    assert abs(p["l1"] - 40.0) < 0.3 and abs(p["l2"] - 12.0) < 0.3
    assert abs(p["phi"] - phi) < np.radians(1.0)


def test_circle_object_subpixel_refit():
    yy, xx = np.mgrid[0:H, 0:W]
    img = _aa(lambda y, x: (x - 100.3) ** 2 + (y - 99.6) ** 2 <= 30.0 ** 2)
    m = mt.create_metrology_model()
    mt.add_metrology_object_circle_measure(m, 102, 100, 31, n=36)   # 2 px off
    res = mt.apply_metrology_model(m, img)[0]
    p = res["params"]
    assert abs(p["radius"] - 30.0) < 0.15
    assert abs(p["row"] - 99.6) < 0.15 and abs(p["col"] - 100.3) < 0.15
    assert res["rms"] < 0.2


def test_line_object_refit_and_align():
    img = _aa(lambda y, x: x >= 60.4)
    m = mt.create_metrology_model()
    mt.add_metrology_object_line_measure(m, 50, 61, 150, 61, n=20)
    res = mt.apply_metrology_model(m, img)[0]
    p = res["params"]
    assert abs(p["col1"] - 60.4) < 0.15 and abs(p["col2"] - 60.4) < 0.15
    assert abs(abs(p["angle_deg"]) - 90.0) < 0.5
    # align moves BOTH endpoints of a line object
    a = mt.align_metrology_model(m, drow=3.0, dcol=-2.0)["objects"][0]["p"]
    assert a == (53, 59, 153, 59)


def test_weak_or_missing_edges_are_reported_not_fabricated():
    img = np.zeros((H, W))                                      # no edges at all
    m = mt.create_metrology_model()
    mt.add_metrology_object_circle_measure(m, 100, 100, 30, n=24)
    res = mt.apply_metrology_model(m, img)[0]
    assert len(res["edge_points"]) == 0
    assert res["params"] is None and res["rms"] == float("inf") and "error" in res
    # a 0.3-contrast circle passes a 0.1 threshold but not a 0.5 threshold
    img = 0.3 * _aa(lambda y, x: (x - 100) ** 2 + (y - 100) ** 2 <= 30.0 ** 2)
    ok = mt.apply_metrology_model(m, img, threshold=0.1)[0]
    assert ok["params"] is not None and abs(ok["params"]["radius"] - 30) < 0.15
    assert abs(ok["score"] - 0.3) < 0.03
    assert mt.apply_metrology_model(m, img, threshold=0.5)[0]["params"] is None


def test_non_2d_image_raises():
    m = mt.create_metrology_model()
    mt.add_metrology_object_circle_measure(m, 10, 10, 5)
    with pytest.raises(ValueError):
        mt.apply_metrology_model(m, np.zeros((4, 4, 3)))
