"""Point-cloud segmentation, model fitting and spatial filtering (numpy + scipy).

The analysis layer above :mod:`pointcloud` (normals / downsample) and
:mod:`camera` (which builds the cloud from depth). Where :mod:`registration`
aligns a whole cloud to a known model, this module *carves a raw cloud up*: fit
the dominant plane and drop it (ground removal for locomotion), cluster what
remains into separate objects (the "which blob is a graspable thing" step),
bound each cluster with an oriented box, and fit primitive shapes (plane / sphere
/ cylinder) that stand in for pipes, balls and table-tops. These are the classic
robot-perception front-end operations a manipulator runs before it decides what
to pick up or where to step.

References (public literature — reimplemented, not derived from any product):
- Fischler & Bolles, "Random Sample Consensus", CACM 1981 (RANSAC).
- Rusu, "Semantic 3D Object Maps for Everyday Manipulation", PhD 2009 (Euclidean
  cluster extraction; cylinder model from point+normal samples).
- Rabbani et al., "Segmentation of point clouds using smoothness constraint",
  ISPRS 2006 (normal/curvature region growing).
- Pauly et al., "Efficient Simplification of Point-Sampled Surfaces", VIS 2002
  (surface variation as a curvature estimate).
- Eldar et al., "The farthest point strategy for progressive image sampling",
  ICPR 1994 (farthest-point sampling).
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "fit_plane", "fit_plane_ransac", "fit_sphere_ransac", "fit_cylinder_ransac",
    "plane_distance", "height_above_plane", "remove_ground",
    "euclidean_clusters", "region_growing",
    "aabb", "obb", "crop_box", "crop_sphere", "farthest_point_sampling",
    "curvature", "centroid", "principal_axes",
]


def _pts3(a) -> np.ndarray:
    a = np.asarray(a, np.float64)
    if a.ndim != 2 or a.shape[1] != 3:
        raise ValueError("expected (N, 3) points, got shape %r" % (a.shape,))
    return a


# --- plane / primitive fitting ---------------------------------------------- #
def fit_plane(points) -> np.ndarray:
    """Total-least-squares plane through all points (PCA).

    Returns ``[a, b, c, d]`` with unit normal ``(a, b, c)`` and ``a*x+b*y+c*z+d=0``.
    Sensitive to outliers — use :func:`fit_plane_ransac` on real depth clouds."""
    P = _pts3(points)
    if P.shape[0] < 3:
        raise ValueError("need >= 3 points to fit a plane")
    c = P.mean(0)
    _, _, Vt = np.linalg.svd(P - c)
    n = Vt[-1]
    n = n / max(np.linalg.norm(n), 1e-12)
    return np.append(n, -n @ c)


def fit_plane_ransac(points, thresh: float = 0.01, iters: int = 200, seed: int = 0):
    """Robust dominant-plane fit by RANSAC (Fischler & Bolles 1981).

    Repeatedly fits a plane to 3 random points and counts inliers within
    *thresh* metric distance, then refits (TLS) to the best consensus set. Returns
    ``(plane [a,b,c,d], inliers boolean mask)``. The workhorse for table-top and
    ground-plane extraction."""
    P = _pts3(points)
    n = P.shape[0]
    if n < 3:
        raise ValueError("need >= 3 points")
    rng = np.random.default_rng(seed)
    best_inl, best_cnt = None, -1
    for _ in range(int(iters)):
        i = rng.choice(n, 3, replace=False)
        nrm = np.cross(P[i[1]] - P[i[0]], P[i[2]] - P[i[0]])
        nn = np.linalg.norm(nrm)
        if nn < 1e-12:
            continue
        nrm = nrm / nn
        d = -nrm @ P[i[0]]
        inl = np.abs(P @ nrm + d) <= thresh
        cnt = int(inl.sum())
        if cnt > best_cnt:
            best_cnt, best_inl = cnt, inl
    if best_inl is None or best_cnt < 3:
        return fit_plane(P), np.ones(n, bool)
    plane = fit_plane(P[best_inl])
    inliers = np.abs(P @ plane[:3] + plane[3]) <= thresh
    return plane, inliers


def fit_sphere_ransac(points, thresh: float = 0.01, iters: int = 200, seed: int = 0):
    """Robust sphere fit by RANSAC. Returns ``(center (3,), radius, inliers)``.

    Each hypothesis solves the algebraic sphere through 4 random points (linear in
    ``[2x,2y,2z,1]`` against ``x^2+y^2+z^2``); the best consensus set is refit
    algebraically. Detects balls / spherical fittings for grasping."""
    P = _pts3(points)
    n = P.shape[0]
    if n < 4:
        raise ValueError("need >= 4 points")
    rng = np.random.default_rng(seed)

    def solve(Q):
        A = np.hstack([2 * Q, np.ones((Q.shape[0], 1))])
        b = (Q ** 2).sum(1)
        sol, *_ = np.linalg.lstsq(A, b, rcond=None)
        c = sol[:3]
        r2 = sol[3] + c @ c
        if r2 <= 0:
            return None
        return c, np.sqrt(r2)

    best = None
    for _ in range(int(iters)):
        i = rng.choice(n, 4, replace=False)
        res = solve(P[i])
        if res is None:
            continue
        c, r = res
        inl = np.abs(np.linalg.norm(P - c, axis=1) - r) <= thresh
        cnt = int(inl.sum())
        if best is None or cnt > best[0]:
            best = (cnt, c, r, inl)
    if best is None:
        raise ValueError("sphere RANSAC failed to find any valid model")
    res = solve(P[best[3]])
    if res is not None:
        c, r = res
        inl = np.abs(np.linalg.norm(P - c, axis=1) - r) <= thresh
        return c, float(r), inl
    return best[1], float(best[2]), best[3]


def fit_cylinder_ransac(points, normals=None, thresh: float = 0.01,
                        iters: int = 300, seed: int = 0):
    """Robust cylinder fit by RANSAC from point+normal samples (Rusu 2009).

    Two surface points with their normals fix a candidate: the axis direction is
    ``n0 x n1`` and the radius/axis line follow from intersecting the two normals in
    the plane perpendicular to the axis. Returns
    ``(axis_point (3,), axis_dir (3, unit), radius, inliers)``. Detects pipes, rods
    and (roughly) limbs — cylindrical things a gripper wraps around. If *normals*
    is None they are estimated from the cloud."""
    P = _pts3(points)
    n = P.shape[0]
    if n < 2:
        raise ValueError("need >= 2 points")
    if normals is None:
        from pointcloud import estimate_normals
        N = estimate_normals(P)
    else:
        N = np.asarray(normals, np.float64)
        if N.shape != P.shape:
            raise ValueError("normals must match points shape")
    rng = np.random.default_rng(seed)

    def hypo(i, j):
        w = np.cross(N[i], N[j])
        wn = np.linalg.norm(w)
        if wn < 1e-9:
            return None
        w = w / wn
        # work in the plane perpendicular to the axis: drop the w-component
        def proj(v):
            return v - (v @ w) * w
        p0, p1 = proj(P[i]), proj(P[j])
        d0, d1 = proj(N[i]), proj(N[j])
        n0, n1 = np.linalg.norm(d0), np.linalg.norm(d1)
        if n0 < 1e-9 or n1 < 1e-9:
            return None
        d0, d1 = d0 / n0, d1 / n1
        # intersect lines p0 + s d0 and p1 + t d1 (least squares for skew safety)
        A = np.stack([d0, -d1], 1)
        st, *_ = np.linalg.lstsq(A, p1 - p0, rcond=None)
        c = p0 + st[0] * d0
        r = np.linalg.norm(p0 - c)
        if r <= 1e-9:
            return None
        return c, w, r

    def axis_dist(c, w, r):
        rel = P - c
        perp = rel - (rel @ w)[:, None] * w
        return np.abs(np.linalg.norm(perp, axis=1) - r)

    best = None
    for _ in range(int(iters)):
        i, j = rng.choice(n, 2, replace=False)
        h = hypo(i, j)
        if h is None:
            continue
        c, w, r = h
        inl = axis_dist(c, w, r) <= thresh
        cnt = int(inl.sum())
        if best is None or cnt > best[0]:
            best = (cnt, c, w, r, inl)
    if best is None:
        raise ValueError("cylinder RANSAC failed to find any valid model")
    return best[1], best[2], float(best[3]), best[4]


# --- distances / ground removal --------------------------------------------- #
def plane_distance(points, plane) -> np.ndarray:
    """Signed distance of each point to a plane ``[a,b,c,d]`` (unit normal assumed)."""
    P = _pts3(points)
    pl = np.asarray(plane, np.float64).ravel()
    if pl.size != 4:
        raise ValueError("plane must be [a, b, c, d]")
    return P @ pl[:3] + pl[3]


def height_above_plane(points, plane) -> np.ndarray:
    """Height of each point above a plane = signed distance along the plane's own
    (given) normal. The **caller** controls which way is 'up' by the orientation of
    the plane normal — pass a plane whose normal points up (e.g. ``[0,0,1,d]`` for a
    floor) and clearance comes back positive. (This deliberately does *not* re-orient
    by a majority-of-points heuristic: that silently discarded the caller's chosen
    normal and flipped the sign depending on the sampling.) The cloud analogue of a
    terrain heightmap for foothold / clearance checks."""
    return plane_distance(points, plane)


def remove_ground(points, thresh: float = 0.02, iters: int = 200,
                  max_slope_deg: float = 45.0, seed: int = 0):
    """Split a cloud into ground and non-ground by RANSAC-fitting the dominant
    (near-horizontal) plane and dropping its inliers.

    Only accepts a plane whose normal is within *max_slope_deg* of vertical as
    "ground" (so a large wall is not mistaken for the floor). Returns
    ``(nonground_points, ground_mask)``. The first step of locomotion perception:
    what is walkable floor vs. what is an obstacle/object standing on it."""
    P = _pts3(points)
    plane, inl = fit_plane_ransac(P, thresh=thresh, iters=iters, seed=seed)
    vertical = abs(plane[2]) / max(np.linalg.norm(plane[:3]), 1e-12)
    if vertical < np.cos(np.radians(max_slope_deg)):
        # dominant plane is too steep to be ground -> nothing removed
        return P.copy(), np.zeros(P.shape[0], bool)
    return P[~inl], inl


# --- clustering / region growing -------------------------------------------- #
def euclidean_clusters(points, tol: float = 0.05, min_size: int = 10,
                       max_size: int | None = None):
    """Euclidean cluster extraction (Rusu 2009): group points that are within
    *tol* of each other (transitively) into connected components.

    Returns a list of index arrays (largest first), each a candidate object once
    the ground/table has been removed. Clusters smaller than *min_size* (noise) or
    larger than *max_size* are dropped."""
    from scipy.spatial import cKDTree
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import connected_components

    P = _pts3(points)
    n = P.shape[0]
    if n == 0:
        return []
    tree = cKDTree(P)
    pairs = tree.query_pairs(r=float(tol), output_type="ndarray")
    if pairs.size == 0:
        rows = cols = np.zeros(0, int)
    else:
        rows = np.concatenate([pairs[:, 0], pairs[:, 1]])
        cols = np.concatenate([pairs[:, 1], pairs[:, 0]])
    graph = csr_matrix((np.ones(rows.size), (rows, cols)), shape=(n, n))
    ncomp, labels = connected_components(graph, directed=False)
    out = []
    for c in range(ncomp):
        idx = np.where(labels == c)[0]
        if idx.size < min_size:
            continue
        if max_size is not None and idx.size > max_size:
            continue
        out.append(idx)
    out.sort(key=lambda a: -a.size)
    return out


def region_growing(points, normals=None, angle_deg: float = 15.0,
                   curv_thresh: float = 0.1, k: int = 16):
    """Smoothness-constraint region growing (Rabbani 2006).

    Grows regions from low-curvature seeds, adding a neighbour when its normal is
    within *angle_deg* of the seed region's and its curvature is below
    *curv_thresh*. Segments a cloud into smooth surface patches — e.g. separating
    the several faces of a box, or floor vs. ramp. Returns integer labels (N,),
    ``-1`` for unassigned. If *normals* is None they are estimated."""
    from scipy.spatial import cKDTree

    P = _pts3(points)
    n = P.shape[0]
    if n == 0:
        return np.zeros(0, int)
    if normals is None:
        from pointcloud import estimate_normals
        N = estimate_normals(P, k=k)
    else:
        N = np.asarray(normals, np.float64)
    curv = curvature(P, k=k)
    cos_thr = np.cos(np.radians(angle_deg))
    kk = int(min(k + 1, n))
    _, idx = cKDTree(P).query(P, k=kk)
    if idx.ndim == 1:
        idx = idx.reshape(n, 1)
    labels = np.full(n, -1, int)
    order = np.argsort(curv)                       # grow from flattest points first
    cur = 0
    for seed in order:
        if labels[seed] != -1:
            continue
        labels[seed] = cur
        stack = [seed]
        while stack:
            p = stack.pop()
            for q in idx[p, 1:]:
                if labels[q] != -1:
                    continue
                if abs(N[p] @ N[q]) < cos_thr:
                    continue
                labels[q] = cur
                if curv[q] < curv_thresh:
                    stack.append(q)
        cur += 1
    return labels


# --- bounding volumes / sampling / filtering -------------------------------- #
def aabb(points):
    """Axis-aligned bounding box. Returns ``(min (3,), max (3,))``."""
    P = _pts3(points)
    if P.shape[0] == 0:
        raise ValueError("empty cloud")
    return P.min(0), P.max(0)


def obb(points) -> dict:
    """Oriented bounding box by PCA.

    Returns ``{center, axes (3,3 columns = box axes), extents (3, half-widths),
    corners (8,3)}``. The tight-fitting box a manipulator uses to reason about an
    object's size and grasp width once it has been segmented out."""
    P = _pts3(points)
    if P.shape[0] < 2:
        raise ValueError("need >= 2 points")
    c = P.mean(0)
    _, _, Vt = np.linalg.svd(P - c)
    axes = Vt.T                                    # columns are principal directions
    local = (P - c) @ axes
    lo, hi = local.min(0), local.max(0)
    extents = (hi - lo) / 2.0
    center = c + axes @ ((hi + lo) / 2.0)
    signs = np.array(np.meshgrid([-1, 1], [-1, 1], [-1, 1])).T.reshape(-1, 3)
    corners = center + (signs * extents) @ axes.T
    return {"center": center, "axes": axes, "extents": extents, "corners": corners}


def crop_box(points, lo, hi):
    """Keep points inside the axis-aligned box ``[lo, hi]``. Returns
    ``(kept_points, mask)`` — a "passthrough"/region-of-interest crop of the cloud."""
    P = _pts3(points)
    lo = np.asarray(lo, np.float64).ravel()
    hi = np.asarray(hi, np.float64).ravel()
    if lo.size != 3 or hi.size != 3:
        raise ValueError("lo/hi must be length-3")
    mask = np.all((P >= lo) & (P <= hi), axis=1)
    return P[mask], mask


def crop_sphere(points, center, radius: float):
    """Keep points within *radius* of *center*. Returns ``(kept_points, mask)``."""
    P = _pts3(points)
    c = np.asarray(center, np.float64).ravel()
    if c.size != 3:
        raise ValueError("center must be length-3")
    mask = np.linalg.norm(P - c, axis=1) <= float(radius)
    return P[mask], mask


def farthest_point_sampling(points, k: int, seed: int = 0) -> np.ndarray:
    """Farthest-point sampling (Eldar 1994): pick *k* points that spread out to
    cover the cloud, each maximally far from those already chosen.

    Returns the chosen indices (k,). Gives an even, geometry-aware thinning (unlike
    voxel downsampling it keeps a fixed count and preserves extremes) — the standard
    front-end for point-based recognition."""
    P = _pts3(points)
    n = P.shape[0]
    k = int(k)
    if k <= 0:
        raise ValueError("k must be > 0")
    if k >= n:
        return np.arange(n)
    rng = np.random.default_rng(seed)
    chosen = np.empty(k, int)
    chosen[0] = rng.integers(n)
    d = np.linalg.norm(P - P[chosen[0]], axis=1)
    d = np.nan_to_num(d, nan=-1.0)                 # NaN points are not valid samples
    d[chosen[0]] = -1.0
    for i in range(1, k):
        j = int(np.argmax(d))
        chosen[i] = j
        d = np.minimum(d, np.nan_to_num(np.linalg.norm(P - P[j], axis=1), nan=-1.0))
        d[chosen[:i + 1]] = -1.0                    # never re-pick an already-chosen point
    return chosen


def curvature(points, k: int = 16) -> np.ndarray:
    """Per-point surface variation ``lambda0 / (lambda0+lambda1+lambda2)`` over the
    ``k`` nearest neighbours (Pauly 2002) — a curvature estimate in [0, 1/3].

    ~0 on a flat patch, larger on edges/corners/bumps. Feeds region growing and
    marks graspable rims / terrain steps. Returns (N,)."""
    from scipy.spatial import cKDTree

    P = _pts3(points)
    n = P.shape[0]
    if n == 0:
        return np.zeros(0)
    kk = int(min(max(3, k), n))
    _, idx = cKDTree(P).query(P, k=kk)
    if idx.ndim == 1:
        idx = idx.reshape(n, 1)
    nb = P[idx]
    c = nb - nb.mean(1, keepdims=True)
    cov = np.einsum("nki,nkj->nij", c, c)
    ev = np.linalg.eigvalsh(cov)                   # ascending
    tot = ev.sum(1)
    return np.where(tot > 1e-12, ev[:, 0] / tot, 0.0)


def centroid(points) -> np.ndarray:
    """Mean position of the cloud (3,)."""
    return _pts3(points).mean(0)


def principal_axes(points):
    """PCA of the cloud. Returns ``(eigvals (3, descending), eigvecs (3,3 columns))``
    — the object's principal directions and their spread, e.g. for coarse pose."""
    P = _pts3(points)
    if P.shape[0] < 2:
        raise ValueError("need >= 2 points")
    cov = np.cov((P - P.mean(0)).T)
    w, V = np.linalg.eigh(cov)
    order = np.argsort(w)[::-1]
    return w[order], V[:, order]
