"""3-D metrology primitives (numpy + scipy) — the (depth, row, col) analogue of
``measure.py``.

Fit a line / plane / sphere / circle to a set of 3-D points, and bound a point
set with an axis-aligned box (``smallest_box3_axis`` — the 3-D
``smallest_rectangle1``), a **near-minimum-volume oriented box**
(``smallest_box3`` — the 3-D ``smallest_rectangle2``), or a **minimum enclosing
sphere** (``smallest_sphere3`` — the 3-D ``smallest_circle``). Each returns a
plain dict of geometric parameters plus an honest RMS residual where one is
meaningful, and fails closed (``ValueError``) on malformed or degenerate input.

Points are ``(depth, row, col)`` — z-first, matching numpy volume indexing
``vol[depth, row, col]`` and the ``(z, y, x)`` axis order ``regionprops3d``
already reports. Centres are returned both as a 3-vector ``center`` and as scalar
``cd`` (depth), ``cr`` (row), ``cc`` (col); directions and normals carry the same
component order.

Honest provenance — what is genuinely new here vs. a consistency wrapper:
  * ``smallest_box3`` (near-minimum-VOLUME oriented box) is the genuine gap this
    module fills. ``pcseg.obb`` only fits a **PCA-aligned** box, which is not minimal
    on an asymmetric object; ``smallest_box3`` seeds from the hull-face orientations
    and PCA and refines by local search, reaching the true minimum on box-like AND
    case-b shapes (e.g. a tetrahedron, where a PCA box is ~2x too large). It is not a
    *proof* of global minimality for every convex shape — see its docstring for the
    honest limit.
  * ``smallest_sphere3`` computes the minimum enclosing sphere by **exact Welzl**;
    ``hull3d.min_enclosing_sphere`` already offers an *approximate* (iterative
    refinement) one, so this is an exactness upgrade rather than a brand-new
    capability.
  * The remaining functions re-present capability that also exists elsewhere, under
    one fail-closed ``(depth, row, col)`` dict convention: ``smallest_box3_axis``
    ~ ``pcseg.aabb``; ``fit_box3`` ~ ``pcseg.obb`` (PCA); the line/plane/sphere/
    circle fits mirror ``match3d.fit_*_3d`` (which return bare tuples for the GPU
    pipeline). They are re-implemented numpy-only so this module stays lightweight
    (no torch), and to give the metrology surface a single, uniform, validated API.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "fit_line3", "fit_plane3", "fit_sphere3", "fit_circle3",
    "smallest_box3_axis", "fit_box3", "smallest_box3", "smallest_sphere3",
]


# --------------------------------------------------------------------------- #
# input validation — fail closed                                              #
# --------------------------------------------------------------------------- #
def _as_points3(points, min_n: int, name: str = "points") -> np.ndarray:
    p = np.asarray(points, np.float64)
    if p.ndim != 2 or p.shape[1] != 3:
        raise ValueError(
            f"{name} must be an (N, 3) array of (depth, row, col); got shape {p.shape}")
    if not np.all(np.isfinite(p)):
        raise ValueError(f"{name} contains non-finite values")
    if len(p) < min_n:
        raise ValueError(f"{name} needs >= {min_n} points to fit; got {len(p)}")
    return p


def _center_keys(c: np.ndarray) -> dict:
    """center 3-vector -> {center, cd, cr, cc} in (depth, row, col) order."""
    return {"center": c, "cd": float(c[0]), "cr": float(c[1]), "cc": float(c[2])}


# --------------------------------------------------------------------------- #
# line / plane / sphere / circle fits — orthogonal least squares              #
# --------------------------------------------------------------------------- #
def fit_line3(points) -> dict:
    """Total-least-squares 3-D line fit to ``(depth, row, col)`` points — the
    largest principal axis through the centroid (orthogonal regression, isotropic
    in all three axes). Returns the centroid ``center`` (with ``cd/cr/cc``), a unit
    ``direction`` (depth, row, col), and the RMS orthogonal residual. Raises
    ``ValueError`` on < 2 points or a coincident cluster with no defined
    direction."""
    p = _as_points3(points, 2, "points")
    c = p.mean(0)
    u, s, vt = np.linalg.svd(p - c, full_matrices=False)
    if s[0] <= 1e-12:
        raise ValueError("points are coincident; no line direction is defined")
    d = vt[0]
    d = d / np.linalg.norm(d)
    diff = p - c
    perp = diff - np.outer(diff @ d, d)              # stable: no large-value cancellation
    rms = float(np.sqrt(np.mean((perp ** 2).sum(1))))
    return {**_center_keys(c), "direction": d, "rms": rms}


def fit_plane3(points) -> dict:
    """Least-squares 3-D plane fit to ``(depth, row, col)`` points — the plane
    through the centroid whose normal is the smallest principal axis (minimises the
    sum of squared point-to-plane distances). Returns ``center`` (``cd/cr/cc``), a
    unit ``normal`` (depth, row, col), and the RMS point-to-plane residual. Raises
    ``ValueError`` on < 3 points or a collinear set (the normal is undefined)."""
    p = _as_points3(points, 3, "points")
    c = p.mean(0)
    # SVD of the centred points (not eigh of the covariance — forming P^T P squares
    # the condition number and floors the residual at ~1e-8; SVD keeps it ~1e-14).
    _, s, vt = np.linalg.svd(p - c, full_matrices=False)
    if s[1] <= 1e-9 * s[0]:                           # only one spread axis -> collinear
        raise ValueError("points are collinear; no plane normal is defined")
    n = vt[-1]                                        # smallest singular direction
    n = n / np.linalg.norm(n)
    rms = float(s[-1] / np.sqrt(len(p)))
    return {**_center_keys(c), "normal": n, "rms": rms}


def fit_sphere3(points) -> dict:
    """Algebraic (Kåsa) least-squares sphere fit to ``(depth, row, col)`` points:
    solve ``|P|^2 = 2 P·c + (r^2 - |c|^2)`` in the least-squares sense — exact for
    points on a sphere, a standard robust estimator under moderate noise. Returns
    ``center`` (``cd/cr/cc``), radius ``r``, and the RMS radial residual. Raises
    ``ValueError`` on < 4 points or a coplanar set (no finite sphere)."""
    p = _as_points3(points, 4, "points")
    A = np.hstack([2.0 * p, np.ones((len(p), 1))])
    b = (p ** 2).sum(1)
    # coplanar / degenerate <=> A is rank-deficient in its point columns.
    sv = np.linalg.svd(p - p.mean(0), compute_uv=False)
    if sv[-1] <= 1e-9 * sv[0]:
        raise ValueError("points are coplanar or degenerate; no finite sphere fits")
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]
    r = float(np.sqrt(max(sol[3] + c @ c, 0.0)))
    rms = float(np.sqrt(np.mean((np.linalg.norm(p - c, axis=1) - r) ** 2)))
    return {**_center_keys(c), "r": r, "rms": rms}


def fit_circle3(points) -> dict:
    """3-D circle fit to ``(depth, row, col)`` points: fit the supporting plane,
    then fit a 2-D circle in that plane (algebraic least squares). Returns
    ``center`` (``cd/cr/cc``), radius ``r``, a unit plane ``normal`` (depth, row,
    col), and the RMS residual (in-plane radial + out-of-plane, combined). Raises
    ``ValueError`` on < 3 points or a collinear set."""
    p = _as_points3(points, 3, "points")
    pl = fit_plane3(p)
    c0, n = pl["center"], pl["normal"]
    # in-plane orthonormal basis (e1, e2)
    ref = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = np.cross(n, ref); e1 = e1 / np.linalg.norm(e1)
    e2 = np.cross(n, e1)
    xy = np.column_stack([(p - c0) @ e1, (p - c0) @ e2])
    # 2-D Kåsa circle fit
    Amat = np.hstack([2.0 * xy, np.ones((len(xy), 1))])
    bb = (xy ** 2).sum(1)
    sol, *_ = np.linalg.lstsq(Amat, bb, rcond=None)
    cc2 = sol[:2]
    r = float(np.sqrt(max(sol[2] + cc2 @ cc2, 0.0)))
    center = c0 + cc2[0] * e1 + cc2[1] * e2
    in_plane = np.linalg.norm(xy - cc2, axis=1) - r
    out_plane = (p - c0) @ n
    rms = float(np.sqrt(np.mean(in_plane ** 2 + out_plane ** 2)))
    return {**_center_keys(center), "r": r, "normal": n, "rms": rms}


# --------------------------------------------------------------------------- #
# bounding boxes                                                              #
# --------------------------------------------------------------------------- #
def _box_corners(center: np.ndarray, axes: np.ndarray, half: np.ndarray) -> np.ndarray:
    """8 corners (8, 3) of the box centred at ``center`` with unit ROW axes and
    the given half-extents."""
    signs = np.array(np.meshgrid([-1, 1], [-1, 1], [-1, 1])).T.reshape(-1, 3)
    return center + (signs * half) @ axes


def smallest_box3_axis(points) -> dict:
    """Axis-aligned bounding box (the 3-D ``smallest_rectangle1``). Returns the
    ``min`` / ``max`` corners and ``center`` in ``(depth, row, col)``, the full
    ``size`` (depth, row, col edge lengths), and the enclosed ``volume``. This is
    the honest null baseline that ``smallest_box3`` beats on any rotated object.
    Raises ``ValueError`` on empty input."""
    p = _as_points3(points, 1, "points")
    mn, mx = p.min(0), p.max(0)
    center = 0.5 * (mn + mx)
    size = mx - mn
    return {"min": mn, "max": mx, **_center_keys(center),
            "size": size, "volume": float(np.prod(size))}


def fit_box3(points) -> dict:
    """Oriented box fit by PCA (fast, noise-tolerant; the same construction as
    ``pcseg.obb`` but with the ``measure``-style dict). Axes are the principal
    directions of the point spread; extents come from the projected span. Returns
    ``center`` (``cd/cr/cc``), ``axes`` (3, 3 — unit ROW vectors, depth/row/col
    components), sorted half-extents ``l1 >= l2 >= l3``, full ``size``, ``volume``,
    ``corners`` (8, 3), and the RMS point-to-box-surface distance. For the true
    minimum-volume box use ``smallest_box3``. Raises ``ValueError`` on < 4 points
    or a degenerate (flat) set."""
    p = _as_points3(points, 4, "points")
    c0 = p.mean(0)
    _, s, vt = np.linalg.svd(p - c0, full_matrices=False)
    if s[-1] <= 1e-9 * s[0]:
        raise ValueError("points are coplanar or degenerate; no 3-D box orientation")
    axes = vt                                        # rows = unit principal axes
    local = (p - c0) @ axes.T
    lo, hi = local.min(0), local.max(0)
    half = 0.5 * (hi - lo)
    center = c0 + 0.5 * (hi + lo) @ axes
    order = np.argsort(-half)                        # l1 >= l2 >= l3
    half, axes = half[order], axes[order]
    rms = _box_surface_rms(p, center, axes, half)
    return {**_center_keys(center), "axes": axes,
            "l1": float(half[0]), "l2": float(half[1]), "l3": float(half[2]),
            "size": 2.0 * half, "volume": float(np.prod(2.0 * half)),
            "corners": _box_corners(center, axes, half), "rms": rms}


def _box_surface_rms(p, center, axes, half) -> float:
    """RMS signed distance of points to the box surface (SDF of a box)."""
    local = np.abs((p - center) @ axes.T) - half
    outside = np.linalg.norm(np.maximum(local, 0.0), axis=1)
    inside = np.minimum(np.max(local, axis=1), 0.0)
    d = outside + inside
    return float(np.sqrt(np.mean(d ** 2)))


def _rot_about(axis, ang):
    """Rotation matrix by angle ``ang`` about a unit ``axis`` (Rodrigues)."""
    a = axis / (np.linalg.norm(axis) + 1e-300)
    c, sn = np.cos(ang), np.sin(ang)
    x, y, z = a
    return np.array([[c + x * x * (1 - c), x * y * (1 - c) - z * sn, x * z * (1 - c) + y * sn],
                     [y * x * (1 - c) + z * sn, c + y * y * (1 - c), y * z * (1 - c) - x * sn],
                     [z * x * (1 - c) - y * sn, z * y * (1 - c) + x * sn, c + z * z * (1 - c)]])


def _box_axes_volume(P, axes):
    """Volume of the box bounding ``P`` when aligned to the orthonormal ROW frame
    ``axes``; also returns the per-axis extents (lo, hi)."""
    loc = P @ axes.T
    lo, hi = loc.min(0), loc.max(0)
    return float(np.prod(hi - lo)), lo, hi


def _refine_box_axes(P, axes, iters=64, step0=0.35):
    """Coordinate-descent polish of a box orientation: rotate the frame about each
    of its own axes and accept any rotation that shrinks the bounding volume,
    halving the step when a sweep makes no progress. Local search — it drives a seed
    into the O'Rourke case-b regime a hull-face-only search misses."""
    best_ax = axes.copy()
    best_v, _, _ = _box_axes_volume(P, best_ax)
    step = step0
    for _ in range(iters):
        improved = False
        for k in range(3):
            for sgn in (1.0, -1.0):
                cand = best_ax @ _rot_about(best_ax[k], sgn * step).T
                v, _, _ = _box_axes_volume(P, cand)
                if v < best_v - 1e-15:
                    best_v, best_ax, improved = v, cand, True
        if not improved:
            step *= 0.5
            if step < 1e-10:
                break
    return best_v, best_ax


def smallest_box3(points) -> dict:
    """Near-minimum-volume oriented bounding box (the 3-D ``smallest_rectangle2``).

    Found by multi-start local refinement: seed the orientation from every convex-
    hull face normal (the O'Rourke *case a* candidates — a box face flush with a
    hull face), from the PCA axes, and from a fixed set of deterministic random
    frames, then polish each by coordinate descent and keep the least-volume result.
    This is **exact for box-like objects** (a rotated cuboid is recovered to machine
    precision) and, unlike a PCA box (``fit_box3`` / ``pcseg.obb``), reaches the true
    minimum on shapes whose optimum has no face flush with a hull face — e.g. a
    regular tetrahedron, where the PCA / hull-face box is ~2x too large.

    Honest limit: this is not a *proof* of global minimality for every convex shape.
    The exact guarantee needs O'Rourke's full *case b* (two box faces each flush with
    a hull **edge**), which is not enumerated here; local refinement drives seeds into
    that regime instead. Empirically the result is at or below a dense brute-force
    rotation search, but a pathological shape could leave a small gap.

    Returns ``center`` (``cd/cr/cc``), ``axes`` (3, 3 — unit ROW vectors), sorted
    half-extents ``l1 >= l2 >= l3``, full ``size``, ``volume``, and ``corners``
    (8, 3). Deterministic (fixed random seeds). Raises ``ValueError`` on < 4 points
    or a coplanar/degenerate set (no 3-D hull)."""
    from scipy.spatial import ConvexHull
    p = _as_points3(points, 4, "points")
    try:
        hull = ConvexHull(p)
    except Exception:
        raise ValueError("points are coplanar or degenerate; no 3-D bounding box") from None
    hv = p[np.unique(hull.simplices)]                # the box is set by hull vertices
    seeds = []
    # case-a seeds: an orthonormal frame with one axis along each hull-face normal
    seen = []
    for w in hull.equations[:, :3]:
        w = w / (np.linalg.norm(w) + 1e-300)
        if any(abs(w @ sv) > 1.0 - 1e-9 for sv in seen):
            continue
        seen.append(w)
        ref = np.array([1.0, 0.0, 0.0]) if abs(w[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        e1 = np.cross(w, ref); e1 = e1 / np.linalg.norm(e1)
        seeds.append(np.array([e1, np.cross(w, e1), w]))
    # PCA + identity + deterministic random frames (case-b coverage)
    _, _, vt = np.linalg.svd(hv - hv.mean(0), full_matrices=False)
    seeds.append(vt)
    seeds.append(np.eye(3))
    rng = np.random.default_rng(0)
    for _ in range(12):
        q, _ = np.linalg.qr(rng.standard_normal((3, 3)))
        seeds.append(q)
    best_v, best_ax = np.inf, np.eye(3)
    for sd in seeds:
        v, ax = _refine_box_axes(hv, sd)
        if v < best_v:
            best_v, best_ax = v, ax
    # re-orthonormalise (guard against drift) and read off the box
    uu, _, vv = np.linalg.svd(best_ax)
    axes = uu @ vv
    loc = hv @ axes.T
    lo, hi = loc.min(0), loc.max(0)
    half = 0.5 * (hi - lo)
    center = (0.5 * (hi + lo)) @ axes
    order = np.argsort(-half)
    half, axes = half[order], axes[order]
    return {**_center_keys(center), "axes": axes,
            "l1": float(half[0]), "l2": float(half[1]), "l3": float(half[2]),
            "size": 2.0 * half, "volume": float(np.prod(2.0 * half)),
            "corners": _box_corners(center, axes, half)}


# --------------------------------------------------------------------------- #
# minimum enclosing sphere — Welzl (exact)                                     #
# --------------------------------------------------------------------------- #
def _sphere_through(R):
    """Smallest sphere with all points of ``R`` (len 0..4, affinely independent)
    on its boundary. Returns (center(3,), r) or None if degenerate."""
    if len(R) == 0:
        return np.zeros(3), 0.0
    if len(R) == 1:
        return np.asarray(R[0], float), 0.0
    if len(R) == 2:
        a, b = np.asarray(R[0], float), np.asarray(R[1], float)
        return 0.5 * (a + b), 0.5 * float(np.linalg.norm(a - b))
    if len(R) == 3:
        a, b, c = (np.asarray(x, float) for x in R)
        # circumcentre of the triangle, in its own plane
        ab, ac = b - a, c - a
        n = np.cross(ab, ac)
        nn = float(n @ n)
        if nn < 1e-24:
            return None
        cc = a + (np.cross(ab @ ab * ac - ac @ ac * ab, n)) / (2.0 * nn)
        return cc, float(np.linalg.norm(cc - a))
    a, b, c, d = (np.asarray(x, float) for x in R)
    M = 2.0 * np.array([b - a, c - a, d - a])
    rhs = np.array([b @ b - a @ a, c @ c - a @ a, d @ d - a @ a])
    try:
        center = np.linalg.solve(M, rhs)
    except np.linalg.LinAlgError:
        return None
    return center, float(np.linalg.norm(center - a))


def _in_sphere(sph, p, eps=1e-9):
    c, r = sph
    return float(np.linalg.norm(p - c)) <= r * (1.0 + eps) + eps


def _welzl3(P, R):
    if not P or len(R) == 4:
        s = _sphere_through(R)
        return s if s is not None else (np.zeros(3), 0.0)
    p = P[-1]
    d = _welzl3(P[:-1], R)
    if _in_sphere(d, p):
        return d
    s = _welzl3(P[:-1], R + [p])
    return s if s is not None else d


def smallest_sphere3(points) -> dict:
    """Minimum enclosing sphere of ``(depth, row, col)`` points (Welzl's exact
    algorithm on the convex hull). Returns ``center`` (``cd/cr/cc``) and radius
    ``r`` — the smallest sphere that contains every point. This is the 3-D
    ``smallest_circle``; its radius is strictly below the AABB-diagonal sphere on
    any non-spherical set, and equals the true radius for points on a sphere.
    Raises ``ValueError`` on empty input."""
    import sys
    from scipy.spatial import ConvexHull
    p = _as_points3(points, 1, "points")
    if len(p) <= 2:
        c, r = _sphere_through([row for row in p])
        return {**_center_keys(np.asarray(c, float)), "r": float(r)}
    try:
        pts = p[np.unique(ConvexHull(p).simplices)]   # min sphere is set by hull pts
    except Exception:
        pts = p                                       # coplanar/collinear: use all
    rng = np.random.default_rng(0)
    idx = rng.permutation(len(pts))
    P = [pts[i] for i in idx]
    old = sys.getrecursionlimit()
    try:
        sys.setrecursionlimit(max(old, len(P) + 100))
        c, r = _welzl3(P, [])
    finally:
        sys.setrecursionlimit(old)
    return {**_center_keys(np.asarray(c, float)), "r": float(r)}
