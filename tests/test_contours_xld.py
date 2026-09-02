"""contours_xld: closed-contour boolean ops rebuild the result by tracing the mask
boundary (one closed loop per outer boundary and per hole), plus point-statistics
and point-in-contour fixes.

Regression for the 2026-09-02 finding: results were rebuilt by an angular sort of
border pixels about the centroid, which garbled non-star-shaped regions (annulus
interleaved, crescent self-intersecting) and under-reported areas by 6-13 %.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import contours_xld as cx  # noqa: E402
import contours_xld2 as cx2  # noqa: E402
import backends_xldgeom as xg  # noqa: E402

SHAPE = (128, 128)


def _area(a):
    y, x = a[:, 0], a[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y)))


def _self_intersections(poly):
    def cr(a, b):
        return a[0] * b[1] - a[1] * b[0]

    def hit(p, q, r, s):
        d1, d2 = q - p, s - r
        den = cr(d1, d2)
        if abs(den) < 1e-12:
            return False
        t = cr(r - p, d2) / den
        u = cr(r - p, d1) / den
        return 1e-9 < t < 1 - 1e-9 and 1e-9 < u < 1 - 1e-9
    n = len(poly) - 1
    cnt = 0
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            if hit(poly[i], poly[i + 1], poly[j], poly[j + 1]):
                cnt += 1
    return cnt


def test_annulus_is_two_loops_with_correct_areas():
    big = cx.gen_circle_contour_xld(60, 60, 30, n=200, shape=SHAPE)
    small = cx.gen_circle_contour_xld(60, 60, 12, n=200, shape=SHAPE)
    ann = cx.difference_closed_contours_xld(big, small)
    assert len(ann["cs"]) == 2
    outer, inner = ann["cs"]
    assert abs(_area(outer) - np.pi * 30 ** 2) / (np.pi * 30 ** 2) < 0.02
    # r=12 is small: even the exact Gauss-circle lattice count (441) is 2.5 % under
    # pi*144 = 452.4, so the raster (438 px) is compared at 4 %; the tracer itself
    # is exact against the mask (checked below).
    assert abs(_area(inner) - np.pi * 12 ** 2) / (np.pi * 12 ** 2) < 0.04
    for loop in (outer, inner):
        assert np.allclose(loop[0], loop[-1])
        rad = np.hypot(loop[:, 0] - 60, loop[:, 1] - 60)
        assert np.ptp(rad) < 2.0                        # one ring each, no interleave
    # polygon area == mask pixel count exactly (crack-following tracer)
    mask = cx._rasterize(big["cs"][0], SHAPE) & ~cx._rasterize(small["cs"][0], SHAPE)
    assert abs((_area(outer) - _area(inner)) - mask.sum()) < 1e-6


def test_union_of_identical_circles_is_the_circle():
    c = cx.gen_circle_contour_xld(50, 50, 20, n=200, shape=SHAPE)
    u = cx.union2_closed_contours_xld(c, c)
    assert len(u["cs"]) == 1
    assert abs(_area(u["cs"][0]) - np.pi * 400) / (np.pi * 400) < 0.02
    assert abs(float(xg.xg_area_center(u, 0, 0)) - np.pi * 400) / (np.pi * 400) < 0.02


def test_crescent_has_no_self_intersection_and_matches_mask():
    c1 = cx.gen_circle_contour_xld(50, 50, 20, n=200, shape=SHAPE)
    c2 = cx.gen_circle_contour_xld(50, 70, 20, n=200, shape=SHAPE)
    d = cx.difference_closed_contours_xld(c1, c2)
    assert len(d["cs"]) == 1
    poly = d["cs"][0]
    assert _self_intersections(poly) == 0
    mask = cx._rasterize(c1["cs"][0], SHAPE) & ~cx._rasterize(c2["cs"][0], SHAPE)
    back = cx._rasterize(poly, SHAPE)
    iou = (back & mask).sum() / (back | mask).sum()
    assert iou > 0.97
    assert abs(_area(poly) - mask.sum()) < 1e-6


def test_disjoint_intersection_is_empty_and_symm_difference_gives_two_lunes():
    c1 = cx.gen_circle_contour_xld(30, 30, 10, n=100, shape=SHAPE)
    c2 = cx.gen_circle_contour_xld(90, 90, 10, n=100, shape=SHAPE)
    assert cx.intersection_closed_contours_xld(c1, c2)["cs"] == []
    c3 = cx.gen_circle_contour_xld(50, 50, 20, n=200, shape=SHAPE)
    c4 = cx.gen_circle_contour_xld(50, 70, 20, n=200, shape=SHAPE)
    sd = cx.symm_difference_closed_contours_xld(c3, c4)
    assert len(sd["cs"]) == 2
    inter = cx.intersection_closed_contours_xld(c3, c4)
    assert len(inter["cs"]) == 1
    lens = 2 * 400 * np.arccos(0.5) - 0.5 * 20 * np.sqrt(4 * 400 - 400)
    assert abs(_area(inter["cs"][0]) - lens) / lens < 0.03
    u = cx.union2_closed_contours_xld(c3, c4)
    assert abs(_area(u["cs"][0]) - (2 * np.pi * 400 - lens)) / (2 * np.pi * 400 - lens) < 0.03


def test_diagonal_touch_gives_separate_loops():
    m = np.zeros((8, 8), bool)
    m[2, 2] = True
    m[3, 3] = True
    loops = cx._trace_mask_boundaries(m)
    assert len(loops) == 2 and all(abs(_area(l) - 1.0) < 1e-9 for l in loops)


def test_polygon_boolean_wrappers_and_region_intersection_still_work():
    c1 = cx.gen_circle_contour_xld(50, 50, 20, n=200, shape=SHAPE)
    c2 = cx.gen_circle_contour_xld(50, 70, 20, n=200, shape=SHAPE)
    u = cx2.union2_closed_polygons_xld(c1, c2)
    assert len(u["cs"]) == 1
    region = np.zeros(SHAPE, bool)
    region[:, :50] = True
    r = cx2.intersection_region_contour_xld(region, c1)
    assert r.dtype == bool and 0 < r.sum() < region.sum()


# --- point statistics / point-in-contour -------------------------------------- #
def test_moments_ignore_duplicated_closing_point():
    circ = cx.gen_circle_contour_xld(50.0, 70.0, 20, n=101)          # closed: 101 pts
    m = cx.moments_any_points_xld(circ)
    assert m["n"] == 100
    assert np.abs(m["centroid"] - [50.0, 70.0]).max() < 1e-9
    assert abs(m["m20"] - m["m02"]) < 1e-9 and abs(m["m11"]) < 1e-9
    assert abs(float(xg.xg_eccentricity(circ, 0, 0))) < 1e-6
    assert abs(float(xg.xg_moments(circ, 0, 0)) - 400) < 1e-6
    with pytest.raises(ValueError):
        cx.moments_any_points_xld({"shape": SHAPE, "cs": []})


def test_open_contour_is_never_inside():
    half = cx.gen_circle_contour_xld(50, 50, 20, n=50, start=0, end=np.pi)
    assert cx.test_xld_point(half, 50, 50) == [False]
    full = cx.gen_circle_contour_xld(50, 50, 20, n=100)
    assert cx.test_xld_point(full, 50, 50) == [True]
    assert cx.test_xld_point(full, 50, 75) == [False]


def test_regress_params_rejects_single_point():
    one = cx._contour(SHAPE, [np.array([[5.0, 5.0]])])
    with pytest.raises(ValueError):
        cx.get_regress_params_xld(one)
    pts = np.column_stack([10 + 0.5 * np.arange(50), 20 + 1.0 * np.arange(50)])
    rp = cx.get_regress_params_xld(cx._contour(SHAPE, [pts]))[0]
    assert np.abs(rp["nr"] * pts[:, 0] + rp["nc"] * pts[:, 1] - rp["dist"]).max() < 1e-9
