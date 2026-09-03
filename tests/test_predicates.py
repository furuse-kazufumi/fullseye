"""Exact geometric predicates (predicates.py): the SIGN is always the true sign,
even when float64 gets it wrong.

The point of these predicates is robustness: a naive float determinant picks the
wrong side of a near-degenerate configuration ~19% of the time on the collinear
sweep below, which corrupts hull/Delaunay/inside-outside topology. The adaptive
predicate must agree with the exact rational answer on every input.
"""
from __future__ import annotations

import numpy as np
import pytest

import predicates as P


# --- basic, hand-checkable signs -------------------------------------------- #
def test_orient2d_basic_signs():
    assert P.orient2d((0, 0), (1, 0), (0, 1)) == 1       # c left of a->b  (CCW)
    assert P.orient2d((0, 0), (0, 1), (1, 0)) == -1      # c right of a->b (CW)
    assert P.orient2d((0, 0), (1, 1), (2, 2)) == 0       # exactly collinear


def test_orient2d_is_antisymmetric():
    a, b, c = (0.3, 0.7), (2.1, -0.4), (1.0, 5.0)
    assert P.orient2d(a, b, c) == -P.orient2d(a, c, b)
    assert P.orient2d(a, b, c) == P.orient2d(b, c, a)    # cyclic


def test_orient3d_basic_signs():
    a, b, c = (0, 0, 0), (1, 0, 0), (0, 1, 0)
    assert P.orient3d(a, b, c, (0.2, 0.2, -1.0)) == 1
    assert P.orient3d(a, b, c, (0.2, 0.2, 1.0)) == -1
    assert P.orient3d(a, b, c, (0.3, 0.3, 0.0)) == 0     # coplanar


def test_incircle_basic():
    t = [(0, 0), (1, 0), (0, 1)]                          # CCW
    assert P.incircle(*t, (0.3, 0.3)) == 1               # inside circumcircle
    assert P.incircle(*t, (2.0, 2.0)) == -1              # outside
    assert P.incircle(*t, (1.0, 1.0)) == 0               # exactly on it


def test_insphere_basic():
    tet = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)]
    if P.orient3d(*tet) < 0:                              # make it positively oriented
        tet = [tet[0], tet[2], tet[1], tet[3]]
    assert P.insphere(*tet, (0.2, 0.2, 0.2)) == -1 or P.insphere(*tet, (0.2, 0.2, 0.2)) == 1
    inside = P.insphere(*tet, (0.2, 0.2, 0.2))
    outside = P.insphere(*tet, (9.0, 9.0, 9.0))
    assert inside == -outside                             # one strictly in, one strictly out


# --- the whole reason this module exists ------------------------------------ #
def _naive_orient2d(o, a, b):
    v = (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    return (v > 0) - (v < 0)


def test_adaptive_equals_exact_and_beats_naive_on_degenerate_sweep():
    """On points interpolated onto the line a->b (collinear in the reals, rounded
    in float), the adaptive predicate matches exact arithmetic on every case,
    while the naive float determinant returns the wrong sign on a large fraction.
    """
    rng = np.random.default_rng(1)
    n = 40000
    naive_wrong = 0
    for _ in range(n):
        a = (rng.random(), rng.random())
        b = (rng.random(), rng.random())
        f = rng.random()
        c = (a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]))
        exact = P.orient2d_exact(a, b, c)
        assert P.orient2d(a, b, c) == exact              # adaptive is always exact
        if _naive_orient2d(a, b, c) != exact:
            naive_wrong += 1
    # naive float is wrong on a large fraction — this is the bug the module fixes
    assert naive_wrong > 0.05 * n, naive_wrong


def test_adaptive_matches_exact_random_orient3d():
    rng = np.random.default_rng(7)
    for _ in range(3000):
        pts = [tuple(rng.random(3)) for _ in range(3)]
        d0 = pts[0]
        t = rng.random()
        # d on the plane of pts (coplanar in reals, rounded in float) sometimes,
        # random otherwise — exercises both the filter and the exact fallback
        d = tuple(rng.random(3)) if rng.random() < 0.5 else tuple(
            np.asarray(pts[0]) + t * (np.asarray(pts[1]) - np.asarray(pts[0])))
        assert P.orient3d(pts[0], pts[1], pts[2], d) == P.orient3d_exact(pts[0], pts[1], pts[2], d)


def test_adaptive_matches_exact_random_incircle():
    rng = np.random.default_rng(11)
    for _ in range(3000):
        a, b, c, d = ((rng.random(), rng.random()) for _ in range(4))
        assert P.incircle(a, b, c, d) == P.incircle_exact(a, b, c, d)


def test_adaptive_matches_exact_random_insphere():
    rng = np.random.default_rng(13)
    for _ in range(1500):
        a, b, c, d, e = (tuple(rng.random(3)) for _ in range(5))
        assert P.insphere(a, b, c, d, e) == P.insphere_exact(a, b, c, d, e)


# --- downstream: the convex hull built on the robust predicate is always convex #
def test_convex_hull_output_is_exactly_convex():
    """backends_regions2._convex_hull_xy uses predicates.orient2d for its turn test.
    Its output must be exactly convex (every consecutive triple a non-right turn)
    on random and near-collinear point sets — verified with exact arithmetic.
    """
    from backends_regions2 import _convex_hull_xy
    rng = np.random.default_rng(3)

    def is_convex(h):
        n = len(h)
        if n < 3:
            return True
        return all(P.orient2d_exact(h[i], h[(i + 1) % n], h[(i + 2) % n]) >= 0
                   for i in range(n))

    for _ in range(500):
        m = int(rng.integers(4, 25))
        if rng.random() < 0.5:
            pts = rng.random((m, 2))                      # generic
        else:                                            # near-collinear + float-scale noise
            t = np.sort(rng.random(m))
            pts = np.c_[t, t * 0.999999999] + 1e-12 * rng.standard_normal((m, 2))
        hull = _convex_hull_xy(pts)
        assert is_convex(hull), f"non-convex hull on {m} points"
