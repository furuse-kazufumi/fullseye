# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Robust geometry queries built on the exact predicates in :mod:`predicates`.

The predicates decide the *sign* of an orientation/in-circle/in-sphere determinant
correctly for any float64 input. This module spends those correct signs on the
combinatorial questions that actually break under naive float arithmetic:

* :func:`point_in_polygon` / :func:`point_in_convex_polygon` — inside / on / out,
  via a robust winding number whose edge-crossing decisions use ``orient2d``.
* :func:`is_convex_polygon` — every vertex turns the same way (exact).
* :func:`point_in_tetrahedron` / :func:`point_in_convex_polytope` — 3-D inside /
  on / out from the signs of the face determinants (``orient3d``).
* :func:`is_delaunay_2d` — every triangle's circumcircle is empty (``incircle``);
  returns the offending (triangle, point) pairs so a caller can see *why* not.
* :func:`mesh_orientation_consistent` — adjacent faces traverse their shared edge
  in opposite directions (a topological check; reports the offending edges).

A naive float version of the *same* winding/incircle tests flips its answer on
near-degenerate inputs (points on an edge, cocircular quadruples); these functions
do not, because the sign they branch on is the true sign. Only numpy + stdlib.

Convention: all "inside" queries return a 3-valued int — ``+1`` strictly inside,
``0`` exactly on the boundary, ``-1`` strictly outside — so a caller can treat the
boundary explicitly instead of having it fall arbitrarily to one side.
"""
from __future__ import annotations

import numpy as np

import predicates as _P

__all__ = [
    "point_in_polygon", "point_in_convex_polygon", "is_convex_polygon",
    "point_in_tetrahedron", "point_in_convex_polytope",
    "is_delaunay_2d", "mesh_orientation_consistent",
]


def _pts2(poly) -> np.ndarray:
    a = np.asarray(poly, dtype=np.float64)
    if a.ndim != 2 or a.shape[1] != 2:
        raise ValueError(f"expected an (N,2) array of 2-D points, got {a.shape}")
    return a


def _on_segment(a, b, p) -> bool:
    """True if p lies on the closed segment a--b (a, b, p already collinear)."""
    return (min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and
            min(a[1], b[1]) <= p[1] <= max(a[1], b[1]))


# --------------------------------------------------------------------------- #
# 2-D point-in-polygon                                                        #
# --------------------------------------------------------------------------- #
def point_in_polygon(pt, poly) -> int:
    """Robust point-in-polygon for a simple polygon (any winding, convex or not).

    Returns +1 inside, 0 on the boundary, -1 outside. Uses a winding-number rule
    whose "is the crossing to the left?" test is the exact :func:`predicates.orient2d`
    sign, so a point sitting exactly on an edge or vertex is reported as boundary
    (0) rather than being pushed inside or outside by rounding.
    """
    v = _pts2(poly)
    n = v.shape[0]
    if n < 3:
        raise ValueError("polygon needs at least 3 vertices")
    p = np.asarray(pt, dtype=np.float64).reshape(-1)[:2]
    wn = 0
    for i in range(n):
        a = v[i]
        b = v[(i + 1) % n]
        side = _P.orient2d(a, b, p)
        if side == 0 and _on_segment(a, b, p):
            return 0                                   # exactly on an edge/vertex
        if a[1] <= p[1]:
            if b[1] > p[1] and side > 0:               # upward crossing, p left
                wn += 1
        else:
            if b[1] <= p[1] and side < 0:              # downward crossing, p right
                wn -= 1
    return 1 if wn != 0 else -1


def is_convex_polygon(poly) -> bool:
    """True if the polygon is convex (all vertices turn the same way; collinear
    vertices allowed). Exact — uses :func:`predicates.orient2d_exact`."""
    v = _pts2(poly)
    n = v.shape[0]
    if n < 3:
        return False
    sign = 0
    for i in range(n):
        s = _P.orient2d_exact(v[i], v[(i + 1) % n], v[(i + 2) % n])
        if s == 0:
            continue                                   # collinear triple: allowed
        if sign == 0:
            sign = s
        elif s != sign:
            return False                               # a turn the other way: concave
    return True


def point_in_convex_polygon(pt, poly) -> int:
    """Fast robust query for a *convex* polygon (vertices in either orientation).

    Returns +1 / 0 / -1. Determines the polygon's orientation with an exact signed
    area so the caller need not pass CCW; every edge must keep the query point on
    the interior side (``orient2d`` sign), with a boundary hit giving 0.
    """
    v = _pts2(poly)
    n = v.shape[0]
    if n < 3:
        raise ValueError("polygon needs at least 3 vertices")
    p = np.asarray(pt, dtype=np.float64).reshape(-1)[:2]
    # exact orientation of the polygon (sign of twice its signed area, fan from v0)
    area2 = 0
    for i in range(1, n - 1):
        area2 += _P.orient2d_exact(v[0], v[i], v[i + 1])
    poly_sign = (area2 > 0) - (area2 < 0)
    if poly_sign == 0:
        raise ValueError("degenerate (zero-area) polygon")
    on_boundary = False
    for i in range(n):
        a, b = v[i], v[(i + 1) % n]
        s = _P.orient2d(a, b, p)
        if s == poly_sign:
            continue
        if s == 0:
            if _on_segment(a, b, p):
                on_boundary = True
                continue
            return -1                                  # collinear but off the edge
        return -1                                      # wrong side of an edge
    return 0 if on_boundary else 1


# --------------------------------------------------------------------------- #
# 3-D point-in-tetrahedron / convex polytope                                  #
# --------------------------------------------------------------------------- #
def point_in_tetrahedron(pt, tet) -> int:
    """Robust point-in-tetrahedron. Returns +1 inside, 0 on the boundary
    (face/edge/vertex), -1 outside. Uses the four face determinants (``orient3d``);
    raises on a degenerate (flat) tetrahedron."""
    t = np.asarray(tet, dtype=np.float64)
    if t.shape != (4, 3):
        raise ValueError(f"tetrahedron needs shape (4,3), got {t.shape}")
    a, b, c, d = t
    p = np.asarray(pt, dtype=np.float64).reshape(-1)[:3]
    d0 = _P.orient3d(a, b, c, d)
    if d0 == 0:
        raise ValueError("degenerate (coplanar) tetrahedron")
    # sign, relative to the tet's own orientation, of p against each face
    s = (_P.orient3d(p, b, c, d), _P.orient3d(a, p, c, d),
         _P.orient3d(a, b, p, d), _P.orient3d(a, b, c, p))
    ref = 1 if d0 > 0 else -1
    boundary = False
    for si in s:
        rel = si * ref
        if rel < 0:
            return -1                                  # p on the far side of a face
        if rel == 0:
            boundary = True
    return 0 if boundary else 1


def point_in_convex_polytope(pt, verts, faces) -> int:
    """Robust query for a convex polytope given ``verts`` (N,3) and triangular
    ``faces`` (M,3 indices). Face winding need not be supplied: the interior side
    of each face is fixed by the polytope's centroid. Returns +1 / 0 / -1."""
    V = np.asarray(verts, dtype=np.float64)
    F = np.asarray(faces, dtype=np.int64)
    if V.ndim != 2 or V.shape[1] != 3:
        raise ValueError("verts must be (N,3)")
    if F.ndim != 2 or F.shape[1] != 3:
        raise ValueError("faces must be (M,3) triangle indices")
    p = np.asarray(pt, dtype=np.float64).reshape(-1)[:3]
    centroid = V.mean(axis=0)
    boundary = False
    for (i, j, k) in F:
        a, b, c = V[i], V[j], V[k]
        s_in = _P.orient3d(a, b, c, centroid)          # which side is the interior
        if s_in == 0:
            continue                                   # centroid on face plane: skip
        s_p = _P.orient3d(a, b, c, p)
        rel = s_p * s_in
        if rel < 0:
            return -1                                  # p outside this face's halfspace
        if rel == 0:
            boundary = True
    return 0 if boundary else 1


# --------------------------------------------------------------------------- #
# Delaunay validity (2-D) and mesh orientation                                #
# --------------------------------------------------------------------------- #
def is_delaunay_2d(points, triangles):
    """Check whether a 2-D triangulation is Delaunay: no vertex lies strictly
    inside any triangle's circumcircle. Returns ``(ok, violations)`` where
    ``violations`` is a list of ``(triangle_index, point_index)`` pairs whose point
    is strictly inside that triangle's circumcircle. Uses exact :func:`incircle`,
    so a point exactly *on* a circumcircle (a valid, common degeneracy) is not
    flagged. O(#triangles * #points)."""
    P = _pts2(points)
    T = np.asarray(triangles, dtype=np.int64)
    if T.ndim != 2 or T.shape[1] != 3:
        raise ValueError("triangles must be (M,3) vertex indices")
    n = P.shape[0]
    violations = []
    for ti, (i, j, k) in enumerate(T):
        a, b, c = P[i], P[j], P[k]
        # incircle expects CCW (a,b,c); flip the last two if this triangle is CW so
        # a positive result always means "strictly inside".
        if _P.orient2d(a, b, c) < 0:
            b, c = c, b
            j, k = k, j
        if _P.orient2d(a, b, c) == 0:
            continue                                   # degenerate triangle: skip
        tri_v = {int(i), int(j), int(k)}
        for m in range(n):
            if m in tri_v:
                continue
            if _P.incircle(a, b, c, P[m]) > 0:
                violations.append((ti, m))
    return (len(violations) == 0, violations)


def mesh_orientation_consistent(faces):
    """Check that a triangle mesh is consistently oriented: every interior edge is
    traversed in *opposite* directions by its two incident faces. Returns
    ``(ok, bad_edges)``; ``bad_edges`` lists ``(u, v)`` edges that are either
    traversed the same way by two faces (an orientation flip) or shared by more
    than two faces (non-manifold). Topological — no coordinates needed."""
    F = np.asarray(faces, dtype=np.int64)
    if F.ndim != 2 or F.shape[1] != 3:
        raise ValueError("faces must be (M,3) vertex indices")
    directed = {}                                      # (u,v) -> count
    for (i, j, k) in F:
        for u, v in ((int(i), int(j)), (int(j), int(k)), (int(k), int(i))):
            directed[(u, v)] = directed.get((u, v), 0) + 1
    bad = []
    seen = set()
    for (u, v), cnt in directed.items():
        key = (min(u, v), max(u, v))
        if key in seen:
            continue
        seen.add(key)
        fwd = directed.get((u, v), 0)
        rev = directed.get((v, u), 0)
        if fwd + rev > 2:
            bad.append(key)                            # non-manifold edge
        elif fwd == 2 or rev == 2:
            bad.append(key)                            # both faces traverse it alike
    return (len(bad) == 0, bad)
