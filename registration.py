"""Rigid point-cloud registration (numpy + scipy).

Aligns one 3-D point set to another and recovers the rigid transform (rotation +
translation). With correspondences it is the closed-form Kabsch/Procrustes
solution; without them it is Iterative Closest Point. Paired with :mod:`stereo`
(depth -> point cloud), this is the object-pose step toward matching an observed
cloud to a CAD/reference model for grasping.

References (public): Kabsch, *A solution for the best rotation to relate two sets
of vectors*, Acta Cryst. 1976; Besl & McKay, *A Method for Registration of 3-D
Shapes*, IEEE TPAMI 1992.
"""
from __future__ import annotations

import numpy as np

__all__ = ["kabsch", "apply_transform", "icp", "point_to_plane_icp",
           "pca_align", "register"]


def kabsch(src, dst):
    """Optimal rigid transform mapping corresponded points *src* -> *dst*.

    *src*, *dst* are (N, 3) with row i of one corresponding to row i of the other.
    Returns ``(R, t)`` (3×3 rotation, 3-vector translation) minimizing
    ``|| (R·src + t) - dst ||`` — a proper rotation (det = +1, reflection-free).
    """
    P = np.asarray(src, np.float64)
    Q = np.asarray(dst, np.float64)
    cp, cq = P.mean(0), Q.mean(0)
    H = (P - cp).T @ (Q - cq)
    U, _, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ np.diag([1.0, 1.0, d]) @ U.T
    t = cq - R @ cp
    return R, t


def apply_transform(points, R, t):
    """Apply ``R·p + t`` to every point (N, 3)."""
    return (np.asarray(points, np.float64) @ np.asarray(R, np.float64).T) + np.asarray(t, np.float64)


def icp(src, dst, max_iter: int = 50, tol: float = 1e-8,
        init=None, trim: float | None = None):
    """Iterative Closest Point: align *src* to *dst* without known correspondences.

    Each iteration matches every source point to its nearest destination point and
    solves Kabsch on those pairs. Returns ``(R, t, aligned, rmse)`` where ``R, t``
    is the accumulated transform, ``aligned`` = R·src + t, and ``rmse`` is the final
    nearest-neighbour RMS distance.

    *init* ``(R0, t0)`` seeds the alignment (use :func:`pca_align` for large
    initial rotations that plain ICP-from-identity cannot escape). *trim*, if set
    to a fraction in ``[0, 1)``, keeps only the best ``1 - trim`` matches by
    distance each iteration (Trimmed ICP) — this rejects outliers and non-overlap,
    the usual case when an observed cloud only partially matches a CAD model; the
    reported ``rmse`` is then over the kept inliers.
    """
    from scipy.spatial import cKDTree

    P0 = np.asarray(src, np.float64)
    Q = np.asarray(dst, np.float64)
    tree = cKDTree(Q)
    if init is None:
        R_tot = np.eye(3)
        t_tot = np.zeros(3)
        cur = P0.copy()
    else:
        R_tot = np.asarray(init[0], np.float64).copy()
        t_tot = np.asarray(init[1], np.float64).copy()
        cur = apply_transform(P0, R_tot, t_tot)
    keep_n = P0.shape[0]
    if trim is not None:
        keep_n = max(3, int(round((1.0 - float(trim)) * P0.shape[0])))
    prev = np.inf
    rmse = np.inf
    for _ in range(max_iter):
        dist, idx = tree.query(cur)
        if keep_n < P0.shape[0]:
            sel = np.argpartition(dist, keep_n - 1)[:keep_n]
        else:
            sel = slice(None)
        rmse = float(np.sqrt(np.mean(dist[sel] ** 2)))
        R, t = kabsch(cur[sel], Q[idx[sel]])
        cur = apply_transform(cur, R, t)
        R_tot = R @ R_tot
        t_tot = R @ t_tot + t
        if abs(prev - rmse) < tol:
            break
        prev = rmse
    return R_tot, t_tot, cur, rmse


def point_to_plane_icp(src, dst, dst_normals=None, k_normals: int = 16,
                       max_iter: int = 50, tol: float = 1e-8,
                       init=None, trim: float | None = None):
    """Point-to-plane ICP: align *src* to *dst* minimizing the distance along the
    destination **surface normal**, not straight-line point distance.

    On a surface this converges faster and tighter than plain :func:`icp` because
    a source point is free to slide within the tangent plane and is only penalised
    for leaving it (Low, 2004). *dst_normals* are estimated with
    :func:`pointcloud.estimate_normals` if not supplied. *init* and *trim* behave
    as in :func:`icp`. Returns ``(R, t, aligned, rmse)`` where ``rmse`` is the
    point-to-plane residual."""
    from scipy.spatial import cKDTree
    from scipy.spatial.transform import Rotation
    import pointcloud

    P0 = np.asarray(src, np.float64)
    Q = np.asarray(dst, np.float64)
    N = (np.asarray(dst_normals, np.float64) if dst_normals is not None
         else pointcloud.estimate_normals(Q, k=k_normals))
    tree = cKDTree(Q)
    if init is None:
        R_tot = np.eye(3)
        t_tot = np.zeros(3)
        cur = P0.copy()
    else:
        R_tot = np.asarray(init[0], np.float64).copy()
        t_tot = np.asarray(init[1], np.float64).copy()
        cur = apply_transform(P0, R_tot, t_tot)
    keep_n = P0.shape[0] if trim is None else max(3, int(round((1.0 - float(trim)) * P0.shape[0])))
    prev = np.inf
    rmse = np.inf
    for _ in range(max_iter):
        dist, idx = tree.query(cur)
        if keep_n < P0.shape[0]:
            sel = np.argpartition(dist, keep_n - 1)[:keep_n]
        else:
            sel = np.arange(P0.shape[0])
        p, q, n = cur[sel], Q[idx[sel]], N[idx[sel]]
        # linearised (small-angle) point-to-plane: [cross(p,n) | n] · [r | t] = -(p-q)·n
        A = np.concatenate([np.cross(p, n), n], axis=1)
        b = -np.einsum("ij,ij->i", p - q, n)
        x, *_ = np.linalg.lstsq(A, b, rcond=None)
        R_inc = Rotation.from_rotvec(x[:3]).as_matrix()
        t_inc = x[3:]
        cur = cur @ R_inc.T + t_inc
        R_tot = R_inc @ R_tot
        t_tot = R_inc @ t_tot + t_inc
        rmse = float(np.sqrt(np.mean(np.einsum("ij,ij->i", cur[sel] - q, n) ** 2)))
        if abs(prev - rmse) < tol:
            break
        prev = rmse
    return R_tot, t_tot, cur, rmse


def pca_align(src, dst):
    """Coarse rigid alignment from principal axes (a one-shot ICP initialiser).

    Centres both clouds and rotates *src*'s principal axes onto *dst*'s. Principal
    axes are defined only up to sign, so all sign combinations that give a proper
    rotation are tried and the lowest nearest-neighbour RMSE wins — this recovers
    large rotations that ICP-from-identity would get stuck on. Returns ``(R, t)``.
    Works best when the cloud is anisotropic (distinct principal extents); a
    near-spherical cloud has ambiguous axes."""
    from scipy.spatial import cKDTree

    P = np.asarray(src, np.float64)
    Q = np.asarray(dst, np.float64)
    cp, cq = P.mean(0), Q.mean(0)
    _, _, VtP = np.linalg.svd(P - cp, full_matrices=False)
    _, _, VtQ = np.linalg.svd(Q - cq, full_matrices=False)
    tree = cKDTree(Q)
    best = None
    for sx in (1.0, -1.0):
        for sy in (1.0, -1.0):
            for sz in (1.0, -1.0):
                R = VtQ.T @ np.diag([sx, sy, sz]) @ VtP
                if np.linalg.det(R) < 0:                 # keep proper rotations only
                    continue
                t = cq - R @ cp
                dist, _ = tree.query(P @ R.T + t)
                rmse = float(np.sqrt(np.mean(dist ** 2)))
                if best is None or rmse < best[0]:
                    best = (rmse, R, t)
    return best[1], best[2]


def register(src, dst, max_iter: int = 60, trim: float | None = 0.2,
             tol: float = 1e-8):
    """Robust one-call registration: :func:`pca_align` for a large-rotation start,
    then Trimmed :func:`icp` for outlier/partial-overlap robustness. Returns the
    same ``(R, t, aligned, rmse)`` tuple as :func:`icp`."""
    R0, t0 = pca_align(src, dst)
    return icp(src, dst, max_iter=max_iter, tol=tol, init=(R0, t0), trim=trim)
