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

__all__ = ["kabsch", "apply_transform", "icp"]


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


def icp(src, dst, max_iter: int = 50, tol: float = 1e-8):
    """Iterative Closest Point: align *src* to *dst* without known correspondences.

    Each iteration matches every source point to its nearest destination point and
    solves Kabsch on those pairs. Returns ``(R, t, aligned, rmse)`` where ``R, t``
    is the accumulated transform, ``aligned`` = R·src + t, and ``rmse`` is the final
    nearest-neighbour RMS distance.
    """
    from scipy.spatial import cKDTree

    P0 = np.asarray(src, np.float64)
    Q = np.asarray(dst, np.float64)
    tree = cKDTree(Q)
    R_tot = np.eye(3)
    t_tot = np.zeros(3)
    cur = P0.copy()
    prev = np.inf
    rmse = np.inf
    for _ in range(max_iter):
        dist, idx = tree.query(cur)
        rmse = float(np.sqrt(np.mean(dist ** 2)))
        R, t = kabsch(cur, Q[idx])
        cur = apply_transform(cur, R, t)
        R_tot = R @ R_tot
        t_tot = R @ t_tot + t
        if abs(prev - rmse) < tol:
            break
        prev = rmse
    return R_tot, t_tot, cur, rmse
