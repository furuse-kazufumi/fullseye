"""Point-cloud geometry primitives (numpy + scipy).

The 3-D companion to :mod:`stereo` (which builds the cloud) and :mod:`registration`
(which aligns it). Surface normals give a grasp its approach direction and let a
registration use point-to-plane error; voxel downsampling thins a dense depth
cloud to something ICP can chew on. Frame convention: ``points`` is (N, 3) in
metric world/camera units.

Reference (public): Hoppe et al., "Surface Reconstruction from Unorganized
Points", SIGGRAPH 1992 (local-PCA normals); voxel-grid downsampling is standard
point-cloud practice.
"""
from __future__ import annotations

import numpy as np

__all__ = ["estimate_normals", "voxel_downsample",
           "remove_statistical_outliers", "remove_radius_outliers"]


def estimate_normals(points, k: int = 16, viewpoint=None) -> np.ndarray:
    """Per-point surface normal by local PCA over the ``k`` nearest neighbours.

    The normal is the eigenvector of the neighbourhood covariance with the
    smallest eigenvalue (the direction of least spread = perpendicular to the
    local surface). Normals are sign-ambiguous; pass *viewpoint* (e.g. the camera
    position) to orient them consistently toward it. Returns unit normals (N, 3)."""
    from scipy.spatial import cKDTree

    P = np.asarray(points, np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError("points must be (N, 3)")
    n = P.shape[0]
    if n == 0:                              # empty cloud (nothing in view) -> empty normals
        return np.empty((0, 3), np.float64)
    kk = int(min(max(3, k), n))
    _, idx = cKDTree(P).query(P, k=kk)
    if kk == 1:                                   # degenerate: only one point
        idx = idx.reshape(n, 1)
    nb = P[idx]                                   # (N, k, 3)
    c = nb - nb.mean(1, keepdims=True)
    cov = np.einsum("nki,nkj->nij", c, c)         # (N, 3, 3) covariance per point
    _, V = np.linalg.eigh(cov)                    # ascending eigenvalues
    normals = V[:, :, 0]                          # smallest-eigenvalue direction
    if viewpoint is not None:
        d = np.asarray(viewpoint, np.float64) - P
        flip = np.einsum("ni,ni->n", normals, d) < 0
        normals[flip] *= -1.0
    norm = np.linalg.norm(normals, axis=1, keepdims=True)
    return normals / np.maximum(norm, 1e-12)


def voxel_downsample(points, voxel: float = 0.05) -> np.ndarray:
    """Thin a cloud to one point (the cell centroid) per occupied voxel of side
    *voxel*. Order is not preserved. Returns (M, 3) with M <= N — the standard way
    to bound ICP cost and even out non-uniform depth sampling density."""
    P = np.asarray(points, np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError("points must be (N, 3)")
    if float(voxel) <= 0.0:
        raise ValueError("voxel must be > 0, got %r" % (voxel,))
    if P.shape[0] == 0:
        return P.copy()
    keys = np.floor((P - P.min(0)) / float(voxel)).astype(np.int64)
    _, inv = np.unique(keys, axis=0, return_inverse=True)
    inv = inv.ravel()
    m = int(inv.max()) + 1
    out = np.zeros((m, 3))
    counts = np.zeros(m)
    np.add.at(out, inv, P)
    np.add.at(counts, inv, 1.0)
    return out / counts[:, None]


def remove_statistical_outliers(points, k: int = 16, std_ratio: float = 2.0):
    """Drop points whose mean distance to their *k* nearest neighbours is a global
    outlier (greater than ``mean + std_ratio*std`` over all points). Cleans stray
    stereo/depth points before registration or normal estimation. Returns
    ``(filtered, keep)`` — the surviving (M, 3) points and the boolean keep mask."""
    from scipy.spatial import cKDTree

    P = np.asarray(points, np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError("points must be (N, 3)")
    n = P.shape[0]
    if n < 3:
        return P.copy(), np.ones(n, bool)
    kk = int(min(max(1, k), n - 1))
    d, _ = cKDTree(P).query(P, k=kk + 1)          # +1: the first neighbour is self (d=0)
    mean_d = d[:, 1:].mean(axis=1)
    thr = float(mean_d.mean() + float(std_ratio) * mean_d.std())
    keep = mean_d <= thr
    return P[keep], keep


def remove_radius_outliers(points, radius: float, min_neighbors: int = 4):
    """Drop points with fewer than *min_neighbors* other points within *radius*
    (isolated specks). Returns ``(filtered, keep)`` like
    :func:`remove_statistical_outliers`."""
    from scipy.spatial import cKDTree

    P = np.asarray(points, np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError("points must be (N, 3)")
    if float(radius) <= 0.0:
        raise ValueError("radius must be > 0, got %r" % (radius,))
    n = P.shape[0]
    if n == 0:
        return P.copy(), np.ones(0, bool)
    counts = cKDTree(P).query_ball_point(P, r=float(radius), return_length=True)
    keep = (np.asarray(counts) - 1) >= int(min_neighbors)   # -1 excludes the point itself
    return P[keep], keep
