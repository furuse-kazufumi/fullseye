# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Exact geometric predicates — robust orientation and in-circle/in-sphere tests.

The sign of a small determinant decides the *topology* of a hull, a Delaunay
triangulation, or a point-in-polytope test. Computed in float64 that sign can be
**wrong** when the points are nearly collinear/coplanar/cocircular: the rounding
error of the determinant exceeds its true (tiny) value, so ``orient2d`` reports
"left" where the truth is "right". A wrong sign is not a small numeric error — it
flips a combinatorial decision and produces a self-intersecting hull, a
non-Delaunay edge, or an inside/outside mistake that no downstream tolerance can
repair.

These four predicates return the **mathematically correct sign** (-1 / 0 / +1)
for any float64 input, using Shewchuk's adaptive strategy in a simple two-level
form:

  1. Evaluate the determinant in float64 and compare its magnitude to a
     provably-safe error bound (the ``*errboundA`` constants below, from
     Shewchuk 1997). If it clears the bound, the float sign is already correct —
     the fast common case, no allocation.
  2. Otherwise recompute the determinant in **exact rational arithmetic**
     (:class:`fractions.Fraction`). A float64 value is a dyadic rational, so its
     conversion to ``Fraction`` is lossless; the exact determinant's sign is
     therefore the true sign with no error at all.

Only the stdlib and numpy are used (``Fraction`` is stdlib) — no bignum or C
extension. The exact path is slower, but it runs only for the near-degenerate
minority, and the whole point is that those are exactly the cases where a fast
float answer is untrustworthy.

Reference: J. R. Shewchuk, "Adaptive Precision Floating-Point Arithmetic and Fast
Robust Geometric Predicates", Discrete & Computational Geometry 18(3), 1997.
"""
from __future__ import annotations

from fractions import Fraction as _Fr

import numpy as np

__all__ = [
    "orient2d", "orient3d", "incircle", "insphere",
    "orient2d_exact", "orient3d_exact", "incircle_exact", "insphere_exact",
]

# machine epsilon for IEEE-754 double (2**-53); Shewchuk's `epsilon`.
_EPS = 1.1102230246251565e-16
# A-level (first filter) error-bound constants, Shewchuk 1997, table in predicates.c.
_ORIENT2D_A = (3.0 + 16.0 * _EPS) * _EPS
_ORIENT3D_A = (7.0 + 56.0 * _EPS) * _EPS
_INCIRCLE_A = (10.0 + 96.0 * _EPS) * _EPS
_INSPHERE_A = (16.0 + 224.0 * _EPS) * _EPS


def _sign(x) -> int:
    return (x > 0) - (x < 0)


def _pt(p, n):
    """Coerce a point to a tuple of *n* python floats (accepts numpy arrays)."""
    a = np.asarray(p, dtype=np.float64).reshape(-1)
    if a.size < n:
        raise ValueError(f"point needs {n} coordinates, got {a.size}")
    return tuple(float(v) for v in a[:n])


# --------------------------------------------------------------------------- #
# 2-D orientation                                                             #
# --------------------------------------------------------------------------- #
def orient2d_exact(a, b, c) -> int:
    """Exact sign of the signed area of triangle (a, b, c). +1 = CCW (c left of
    a->b), -1 = CW, 0 = collinear. Always correct (rational arithmetic)."""
    ax, ay = map(_Fr, _pt(a, 2))
    bx, by = map(_Fr, _pt(b, 2))
    cx, cy = map(_Fr, _pt(c, 2))
    det = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    return _sign(det)


def orient2d(a, b, c) -> int:
    """Robust sign of the signed area of triangle (a, b, c) (see module docstring).

    +1 if c lies to the left of the directed line a->b (CCW), -1 to the right
    (CW), 0 if the three points are exactly collinear.
    """
    ax, ay = _pt(a, 2)
    bx, by = _pt(b, 2)
    cx, cy = _pt(c, 2)
    detleft = (bx - ax) * (cy - ay)
    detright = (by - ay) * (cx - ax)
    det = detleft - detright
    # error bound on |det|; only the same-sign case can be trusted from the sum.
    if (detleft > 0.0 and detright <= 0.0) or (detleft < 0.0 and detright >= 0.0) or detleft == 0.0:
        return _sign(det)
    summ = abs(detleft) + abs(detright)
    errbound = _ORIENT2D_A * summ
    if abs(det) >= errbound:
        return _sign(det)
    return orient2d_exact(a, b, c)


# --------------------------------------------------------------------------- #
# 3-D orientation                                                             #
# --------------------------------------------------------------------------- #
def orient3d_exact(a, b, c, d) -> int:
    """Exact sign of the signed volume of tetrahedron (a, b, c, d). +1 = d below
    the plane a,b,c seen so that a,b,c is CCW from above; -1 above; 0 coplanar."""
    ax, ay, az = map(_Fr, _pt(a, 3))
    bx, by, bz = map(_Fr, _pt(b, 3))
    cx, cy, cz = map(_Fr, _pt(c, 3))
    dx, dy, dz = map(_Fr, _pt(d, 3))
    adx, ady, adz = ax - dx, ay - dy, az - dz
    bdx, bdy, bdz = bx - dx, by - dy, bz - dz
    cdx, cdy, cdz = cx - dx, cy - dy, cz - dz
    det = (adx * (bdy * cdz - bdz * cdy)
           - bdx * (ady * cdz - adz * cdy)
           + cdx * (ady * bdz - adz * bdy))
    return _sign(det)


def orient3d(a, b, c, d) -> int:
    """Robust sign of the signed volume of tetrahedron (a, b, c, d) (see docstring)."""
    ax, ay, az = _pt(a, 3)
    bx, by, bz = _pt(b, 3)
    cx, cy, cz = _pt(c, 3)
    dx, dy, dz = _pt(d, 3)
    adx, ady, adz = ax - dx, ay - dy, az - dz
    bdx, bdy, bdz = bx - dx, by - dy, bz - dz
    cdx, cdy, cdz = cx - dx, cy - dy, cz - dz
    bdxcdy, cdxbdy = bdx * cdy, cdx * bdy
    cdxady, adxcdy = cdx * ady, adx * cdy
    adxbdy, bdxady = adx * bdy, bdx * ady
    det = (adz * (bdxcdy - cdxbdy) + bdz * (cdxady - adxcdy) + cdz * (adxbdy - bdxady))
    # permanent bounds the roundoff: SUM of |terms|, not |difference| — a near-equal
    # pair (the degenerate case) makes |x-y| tiny and would shrink the bound below
    # the true error, so the float sign would be trusted when it is wrong.
    permanent = ((abs(bdxcdy) + abs(cdxbdy)) * abs(adz)
                 + (abs(cdxady) + abs(adxcdy)) * abs(bdz)
                 + (abs(adxbdy) + abs(bdxady)) * abs(cdz))
    errbound = _ORIENT3D_A * permanent
    if abs(det) > errbound:
        return _sign(det)
    return orient3d_exact(a, b, c, d)


# --------------------------------------------------------------------------- #
# in-circle (2-D) and in-sphere (3-D)                                         #
# --------------------------------------------------------------------------- #
def incircle_exact(a, b, c, d) -> int:
    """Exact in-circle test. With (a, b, c) in CCW order: +1 if d is strictly
    INSIDE the circle through a, b, c; -1 outside; 0 cocircular."""
    ax, ay = map(_Fr, _pt(a, 2))
    bx, by = map(_Fr, _pt(b, 2))
    cx, cy = map(_Fr, _pt(c, 2))
    dx, dy = map(_Fr, _pt(d, 2))
    adx, ady = ax - dx, ay - dy
    bdx, bdy = bx - dx, by - dy
    cdx, cdy = cx - dx, cy - dy
    alift = adx * adx + ady * ady
    blift = bdx * bdx + bdy * bdy
    clift = cdx * cdx + cdy * cdy
    det = (alift * (bdx * cdy - cdx * bdy)
           - blift * (adx * cdy - cdx * ady)
           + clift * (adx * bdy - bdx * ady))
    return _sign(det)


def incircle(a, b, c, d) -> int:
    """Robust in-circle test (see :func:`incircle_exact`)."""
    ax, ay = _pt(a, 2)
    bx, by = _pt(b, 2)
    cx, cy = _pt(c, 2)
    dx, dy = _pt(d, 2)
    adx, ady = ax - dx, ay - dy
    bdx, bdy = bx - dx, by - dy
    cdx, cdy = cx - dx, cy - dy
    bdxcdy, cdxbdy = bdx * cdy, cdx * bdy
    cdxady, adxcdy = cdx * ady, adx * cdy
    adxbdy, bdxady = adx * bdy, bdx * ady
    alift = adx * adx + ady * ady
    blift = bdx * bdx + bdy * bdy
    clift = cdx * cdx + cdy * cdy
    det = (alift * (bdxcdy - cdxbdy) + blift * (cdxady - adxcdy) + clift * (adxbdy - bdxady))
    permanent = ((abs(bdxcdy) + abs(cdxbdy)) * alift
                 + (abs(cdxady) + abs(adxcdy)) * blift
                 + (abs(adxbdy) + abs(bdxady)) * clift)
    errbound = _INCIRCLE_A * permanent
    if abs(det) > errbound:
        return _sign(det)
    return incircle_exact(a, b, c, d)


def insphere_exact(a, b, c, d, e) -> int:
    """Exact in-sphere test. With (a, b, c, d) positively oriented
    (``orient3d(a,b,c,d) > 0``): +1 if e is strictly INSIDE the sphere through
    a, b, c, d; -1 outside; 0 cospherical."""
    ax, ay, az = map(_Fr, _pt(a, 3))
    bx, by, bz = map(_Fr, _pt(b, 3))
    cx, cy, cz = map(_Fr, _pt(c, 3))
    dx, dy, dz = map(_Fr, _pt(d, 3))
    ex, ey, ez = map(_Fr, _pt(e, 3))
    aex, aey, aez = ax - ex, ay - ey, az - ez
    bex, bey, bez = bx - ex, by - ey, bz - ez
    cex, cey, cez = cx - ex, cy - ey, cz - ez
    dex, dey, dez = dx - ex, dy - ey, dz - ez

    def det3(r0, r1, r2):
        return (r0[0] * (r1[1] * r2[2] - r1[2] * r2[1])
                - r0[1] * (r1[0] * r2[2] - r1[2] * r2[0])
                + r0[2] * (r1[0] * r2[1] - r1[1] * r2[0]))

    ab = (aex, aey, aez)
    bb = (bex, bey, bez)
    cb = (cex, cey, cez)
    db = (dex, dey, dez)
    alift = aex * aex + aey * aey + aez * aez
    blift = bex * bex + bey * bey + bez * bez
    clift = cex * cex + cey * cey + cez * cez
    dlift = dex * dex + dey * dey + dez * dez
    det = (-dlift * det3(ab, bb, cb) + clift * det3(ab, bb, db)
           - blift * det3(ab, cb, db) + alift * det3(bb, cb, db))
    return _sign(det)


def insphere(a, b, c, d, e) -> int:
    """Robust in-sphere test (see :func:`insphere_exact`).

    An A-level float filter is used, falling back to the exact rational
    determinant when the float value is within its error bound.
    """
    A = [np.asarray(_pt(p, 3)) for p in (a, b, c, d, e)]
    ae, be, ce, de = (A[i] - A[4] for i in range(4))
    rows = [ae, be, ce, de]
    lifts = [float(r @ r) for r in rows]

    def det3f(r0, r1, r2):
        return float(r0[0] * (r1[1] * r2[2] - r1[2] * r2[1])
                     - r0[1] * (r1[0] * r2[2] - r1[2] * r2[0])
                     + r0[2] * (r1[0] * r2[1] - r1[1] * r2[0]))

    d_abc = det3f(ae, be, ce)
    d_abd = det3f(ae, be, de)
    d_acd = det3f(ae, ce, de)
    d_bcd = det3f(be, ce, de)
    det = -lifts[3] * d_abc + lifts[2] * d_abd - lifts[1] * d_acd + lifts[0] * d_bcd
    permanent = (abs(d_abc) * lifts[3] + abs(d_abd) * lifts[2]
                 + abs(d_acd) * lifts[1] + abs(d_bcd) * lifts[0])
    errbound = _INSPHERE_A * permanent
    if abs(det) > errbound:
        return _sign(det)
    return insphere_exact(a, b, c, d, e)
