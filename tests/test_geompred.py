# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Robust geometry queries (geompred.py) built on the exact predicates.

Every "inside" query is 3-valued (+1 in / 0 on / -1 out); the boundary must be
reported as boundary, not pushed to one side by rounding. The whole point of
building these on the exact predicates (rather than raw float determinants) is that
a point sitting on an edge, or a cocircular quadruple, gets the *correct* combinatorial
answer — so the near-degenerate sweeps below compare against exact truth and count how
often a naive float version would disagree.
"""
from __future__ import annotations

import numpy as np
import pytest

import geompred as G
import predicates as P


# --------------------------------------------------------------------------- #
# point in polygon                                                            #
# --------------------------------------------------------------------------- #
SQUARE = [(0, 0), (4, 0), (4, 4), (0, 4)]
LSHAPE = [(0, 0), (4, 0), (4, 2), (2, 2), (2, 4), (0, 4)]   # concave


def test_point_in_polygon_basic():
    assert G.point_in_polygon((2, 2), SQUARE) == 1
    assert G.point_in_polygon((5, 2), SQUARE) == -1
    assert G.point_in_polygon((2, 0), SQUARE) == 0          # on an edge
    assert G.point_in_polygon((0, 0), SQUARE) == 0          # on a vertex
    assert G.point_in_polygon((4, 4), SQUARE) == 0


def test_point_in_polygon_concave():
    assert G.point_in_polygon((1, 1), LSHAPE) == 1
    assert G.point_in_polygon((3, 3), LSHAPE) == -1         # in the notch (outside)
    assert G.point_in_polygon((3, 1), LSHAPE) == 1
    assert G.point_in_polygon((2, 3), LSHAPE) == 0          # on the notch edge


def _naive_pip(pt, poly):
    """Naive float winding number (edge side via a raw cross product). Returns
    +1 inside / -1 outside; no robust boundary handling — the thing geompred fixes."""
    v = np.asarray(poly, float)
    n = len(v)
    p = np.asarray(pt, float)
    wn = 0
    for i in range(n):
        a, b = v[i], v[(i + 1) % n]
        cross = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
        if a[1] <= p[1]:
            if b[1] > p[1] and cross > 0:
                wn += 1
        else:
            if b[1] <= p[1] and cross < 0:
                wn -= 1
    return 1 if wn != 0 else -1


def test_point_in_polygon_boundary_robustness_vs_naive():
    """Points placed exactly on polygon edges (collinear in the reals, rounded in
    float): geompred reports boundary (0); a naive float winding is forced to pick
    a side and disagrees with the robust in/out truth on a real fraction of them."""
    rng = np.random.default_rng(0)
    # a random convex polygon (angular order) with float coordinates
    ang = np.sort(rng.uniform(0, 2 * np.pi, 7))
    poly = np.c_[3 + 2 * np.cos(ang), 3 + 2 * np.sin(ang)]
    on_edge_detected = 0
    naive_disagree = 0
    N = 4000
    for _ in range(N):
        i = rng.integers(0, len(poly))
        a, b = poly[i], poly[(i + 1) % len(poly)]
        f = rng.random()
        p = a + f * (b - a)                                  # exactly on edge i
        if G.point_in_polygon(p, poly) == 0:
            on_edge_detected += 1
        # a robust truth for "not strictly outside" is boundary-or-inside; the naive
        # float call, forced to +1/-1, disagrees with that truth sometimes.
        if _naive_pip(p, poly) == -1:
            naive_disagree += 1
    assert on_edge_detected > 0.9 * N, on_edge_detected      # robust: almost all caught
    assert naive_disagree > 0, naive_disagree                # naive misses some as "outside"


# --------------------------------------------------------------------------- #
# convexity + convex point-in-polygon                                        #
# --------------------------------------------------------------------------- #
def test_is_convex_polygon():
    assert G.is_convex_polygon(SQUARE) is True
    assert G.is_convex_polygon(LSHAPE) is False
    collinear = [(0, 0), (2, 0), (4, 0), (4, 4), (0, 4)]     # a flat edge midpoint
    assert G.is_convex_polygon(collinear) is True            # collinear allowed


def test_convex_pip_agrees_with_general_pip_on_convex():
    rng = np.random.default_rng(1)
    ang = np.sort(rng.uniform(0, 2 * np.pi, 6))
    poly = np.c_[np.cos(ang), np.sin(ang)] * 3.0
    assert G.is_convex_polygon(poly)
    for _ in range(2000):
        p = rng.uniform(-4, 4, 2)
        a = G.point_in_convex_polygon(p, poly)
        b = G.point_in_polygon(p, poly)
        # both are 3-valued and must agree on strictly in/out (boundary is measure-0)
        if a != 0 and b != 0:
            assert a == b, (p, a, b)


def test_convex_pip_orientation_independent():
    ccw = SQUARE
    cw = SQUARE[::-1]
    for poly in (ccw, cw):
        assert G.point_in_convex_polygon((2, 2), poly) == 1
        assert G.point_in_convex_polygon((9, 9), poly) == -1
        assert G.point_in_convex_polygon((0, 2), poly) == 0


# --------------------------------------------------------------------------- #
# 3-D                                                                         #
# --------------------------------------------------------------------------- #
TET = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)]


def test_point_in_tetrahedron():
    assert G.point_in_tetrahedron((0.2, 0.2, 0.2), TET) == 1
    assert G.point_in_tetrahedron((1, 1, 1), TET) == -1
    assert G.point_in_tetrahedron((0.0, 0.2, 0.2), TET) == 0     # on the x=0 face
    assert G.point_in_tetrahedron((0, 0, 0), TET) == 0           # on a vertex
    # orientation-independent (swap two vertices -> flipped tet, same answers)
    flipped = [TET[0], TET[2], TET[1], TET[3]]
    assert G.point_in_tetrahedron((0.2, 0.2, 0.2), flipped) == 1


def test_point_in_tetrahedron_rejects_degenerate():
    flat = [(0, 0, 0), (1, 0, 0), (2, 0, 0), (3, 0, 0)]
    with pytest.raises(ValueError):
        G.point_in_tetrahedron((0, 0, 0), flat)


def _unit_cube():
    V = np.array([(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1)], float)
    # 12 triangles (winding irrelevant — polytope query orients via the centroid)
    F = [(0, 1, 3), (0, 3, 2), (4, 7, 5), (4, 6, 7), (0, 5, 1), (0, 4, 5),
         (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]
    return V, np.array(F)


def test_point_in_convex_polytope_cube():
    V, F = _unit_cube()
    assert G.point_in_convex_polytope((0.5, 0.5, 0.5), V, F) == 1
    assert G.point_in_convex_polytope((2.0, 0.5, 0.5), V, F) == -1
    assert G.point_in_convex_polytope((0.0, 0.5, 0.5), V, F) == 0    # on a face


def test_polytope_agrees_with_tetrahedron():
    V = np.array(TET, float)
    F = np.array([(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)])
    rng = np.random.default_rng(2)
    for _ in range(1500):
        p = rng.uniform(-0.3, 1.0, 3)
        a = G.point_in_convex_polytope(p, V, F)
        b = G.point_in_tetrahedron(p, TET)
        if a != 0 and b != 0:
            assert a == b, (p, a, b)


# --------------------------------------------------------------------------- #
# Delaunay validity                                                           #
# --------------------------------------------------------------------------- #
def test_is_delaunay_flags_the_wrong_diagonal():
    """For a random convex quad that is not cocircular, exactly one of its two
    diagonals gives a Delaunay triangulation; geompred must flag the other."""
    rng = np.random.default_rng(3)
    checked = 0
    while checked < 300:
        pts = rng.uniform(0, 10, (4, 2))
        c = pts.mean(0)
        order = np.argsort(np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0]))
        q = pts[order]                                   # convex order q0,q1,q2,q3
        if P.incircle(q[0], q[1], q[2], q[3]) == 0:
            continue                                     # cocircular: both valid, skip
        checked += 1
        diag_02 = np.array([(0, 1, 2), (0, 2, 3)])
        diag_13 = np.array([(1, 2, 3), (1, 3, 0)])
        ok02 = G.is_delaunay_2d(q, diag_02)[0]
        ok13 = G.is_delaunay_2d(q, diag_13)[0]
        assert ok02 != ok13, (q, ok02, ok13)             # exactly one is Delaunay


def test_is_delaunay_reports_the_violating_point():
    # triangle (0,0),(4,0),(0,4); the interior point (0.5,0.5) is inside its
    # circumcircle, so a triangulation that keeps that big triangle is non-Delaunay.
    pts = np.array([(0, 0), (4, 0), (0, 4), (0.5, 0.5)], float)
    ok, viol = G.is_delaunay_2d(pts, np.array([(0, 1, 2)]))
    assert ok is False
    assert (0, 3) in viol


def test_is_delaunay_true_on_good_triangulation():
    pts = np.array([(0, 0), (4, 0), (0, 4), (0.5, 0.5)], float)
    tris = np.array([(0, 1, 3), (1, 2, 3), (2, 0, 3)])    # fan around interior point
    ok, viol = G.is_delaunay_2d(pts, tris)
    assert ok is True and viol == []


# --------------------------------------------------------------------------- #
# mesh orientation                                                            #
# --------------------------------------------------------------------------- #
def test_mesh_orientation_consistent():
    # two triangles sharing edge (1,2): (0,1,2) and (2,1,3) traverse it oppositely
    ok, bad = G.mesh_orientation_consistent(np.array([(0, 1, 2), (2, 1, 3)]))
    assert ok is True and bad == []


def test_mesh_orientation_flip_detected():
    # (0,1,2) and (1,2,3) both traverse edge (1,2) the same way -> inconsistent
    ok, bad = G.mesh_orientation_consistent(np.array([(0, 1, 2), (1, 2, 3)]))
    assert ok is False
    assert (1, 2) in bad


def test_mesh_orientation_tetrahedron_surface_is_consistent():
    # closed tetra surface, all faces CCW seen from outside
    F = np.array([(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)])
    ok, bad = G.mesh_orientation_consistent(F)
    assert ok is True, bad


# --------------------------------------------------------------------------- #
# public exposure                                                             #
# --------------------------------------------------------------------------- #
def test_exposed_via_api_and_facade():
    import api
    for name in ("point_in_polygon", "point_in_tetrahedron", "is_delaunay_2d"):
        assert name in api.__all__
        assert getattr(api, name) is getattr(G, name)
