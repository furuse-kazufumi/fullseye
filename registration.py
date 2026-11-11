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
           "icp_gated", "point_to_plane_icp_gated",
           "pca_align", "register", "feature_register"]


def kabsch(src, dst, reproducible: bool = False):
    """Optimal rigid transform mapping corresponded points *src* -> *dst*.

    *src*, *dst* are (N, 3) with row i of one corresponding to row i of the other.
    Returns ``(R, t)`` (3×3 rotation, 3-vector translation) minimizing
    ``|| (R·src + t) - dst ||`` — a proper rotation (det = +1, reflection-free).

    ``reproducible=True`` computes the means with ``math.fsum`` and the cross-covariance
    with :func:`ozakimm.cross_covariance_reproducible`, so ``(R, t)`` are bitwise the same
    for any point order and any BLAS thread count (on the same LAPACK). It needs N >= 3 and
    costs far more for large N (about 0.7 ms -> 170 ms at 200,000 points); the default
    path is unchanged.
    """
    P = np.asarray(src, np.float64)
    Q = np.asarray(dst, np.float64)
    if P.shape != Q.shape or P.ndim != 2 or P.shape[0] < 1:
        raise ValueError("kabsch needs matching, non-empty (N, 3) point sets")
    if reproducible:
        import ozakimm
        return ozakimm._kabsch_rt(P, Q)
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


def _cloud_size(Q: np.ndarray) -> float:
    """Bounding-box diagonal of *Q* (independent of point order) — the length unit that makes
    the ICP tolerances dimensionless. ★2026-11-05 敵対的検証 N4: ``tol`` は座標単位の絶対量だった
    ので、尺度 1e-6 の点群では初回の RMSE 変化が 1e-8 を割って止まり、4.25° ずれた姿勢を返した。"""
    if Q.size == 0:
        return 0.0
    L = float(np.linalg.norm(Q.max(axis=0) - Q.min(axis=0)))
    return L if np.isfinite(L) else 0.0


def _checked_trim(trim, n_src, *, strict_count=False, who="icp"):
    """Validate *trim* (fraction of the worst matches to drop, ``0 <= trim < 1``).

    ★2026-11-09 独立レビュー: ``trim=1.5`` / ``1.0`` は 3 点だけで見かけ上よい rmse を、
    ``trim=-0.5`` は黙って無視されていた。範囲外は ``ValueError``。``strict_count`` のとき
    (``*_gated``)は、残す点が 3 未満になる trim も ``ValueError``(従来の ``icp`` は 3 点へ
    切り上げる挙動を互換のため残す)。
    """
    if trim is None:
        return n_src
    try:
        tr = float(trim)
    except (TypeError, ValueError):
        raise ValueError("%s: trim must be a number in [0, 1), got %r" % (who, trim)) from None
    if not (np.isfinite(tr) and 0.0 <= tr < 1.0):
        raise ValueError("%s: trim must be in [0, 1) (fraction of matches to drop), got %r" % (who, trim))
    keep = int(round((1.0 - tr) * n_src))
    if strict_count and keep < 3:
        raise ValueError("%s: trim=%r keeps %d of %d source points; at least 3 are needed"
                         % (who, trim, keep, n_src))
    return max(3, keep)


def icp(src, dst, max_iter: int = 50, tol: float = 1e-8,
        init=None, trim: float | None = None, reproducible: bool = False):
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

    ★There is **no correspondence-distance limit** (Open3D's
    ``max_correspondence_distance`` = infinity) and no robust loss: every source
    point pulls on the pose. With background / edge points in the source, use
    *trim* or :func:`icp_gated`. Measured 2026-11-09 (bracket 500 pts + 100
    uniform outliers, start 20 deg off, 20 trials): this function median 3.4 deg
    (4.15 deg in the audit probe; identical to Open3D without a limit),
    :func:`icp_gated` with a limit of 5 % of the diameter 1.36 deg.

    *tol* is **relative to the size of dst** (its bounding-box diagonal ``L``): iteration
    stops once the RMSE changes by less than ``tol·L``, so the same call converges the same
    way on a cloud in metres or in micrometres (until 2026-11-05 it was an absolute length).

    ``reproducible=True`` makes every reduction independent of the order of the source
    points (Kabsch through :mod:`ozakimm`, the transform applied element by element, the
    RMS with ``math.fsum``), so the returned ``R, t`` and ``rmse`` are bitwise the same for
    any order of *src* and any BLAS thread count (``aligned`` follows the order of *src*).
    Exact distance ties at the *trim* cut-off may still pick different points. The default
    path is unchanged; the reproducible one is far slower per iteration for large clouds.
    """
    from scipy.spatial import cKDTree

    P0 = np.asarray(src, np.float64)
    Q = np.asarray(dst, np.float64)
    if reproducible:
        import ozakimm
        move = ozakimm._apply_rigid
        rms = ozakimm._rms
    else:
        move = apply_transform

        def rms(d):
            return float(np.sqrt(np.mean(d ** 2)))
    tree = cKDTree(Q)
    tol_abs = float(tol) * _cloud_size(Q)
    if init is None:
        R_tot = np.eye(3)
        t_tot = np.zeros(3)
        cur = P0.copy()
    else:
        R_tot = np.asarray(init[0], np.float64).copy()
        t_tot = np.asarray(init[1], np.float64).copy()
        cur = move(P0, R_tot, t_tot)
    keep_n = _checked_trim(trim, P0.shape[0], who="icp")
    prev = np.inf
    rmse = np.inf
    for _ in range(max_iter):
        dist, idx = tree.query(cur)
        if keep_n < P0.shape[0]:
            sel = np.argpartition(dist, keep_n - 1)[:keep_n]
        else:
            sel = slice(None)
        rmse = rms(dist[sel])
        R, t = kabsch(cur[sel], Q[idx[sel]], reproducible=reproducible)
        cur = move(cur, R, t)
        R_tot = R @ R_tot
        t_tot = R @ t_tot + t
        if abs(prev - rmse) < tol_abs:
            break
        prev = rmse
    # report rmse for the RETURNED pose: the loop's value was computed before its
    # final Kabsch step, so re-query so `rmse` and `aligned` describe one alignment.
    dist, _ = tree.query(cur)
    if keep_n < P0.shape[0]:
        dist = np.partition(dist, keep_n - 1)[:keep_n]
    rmse = rms(dist)
    return R_tot, t_tot, cur, rmse


def point_to_plane_icp(src, dst, dst_normals=None, k_normals: int = 16,
                       max_iter: int = 50, tol: float = 1e-8,
                       init=None, trim: float | None = None, reproducible: bool = False):
    """Point-to-plane ICP: align *src* to *dst* minimizing the distance along the
    destination **surface normal**, not straight-line point distance. *tol* is relative to
    the bounding-box diagonal of dst, as in :func:`icp`.

    On a surface this converges faster and tighter than plain :func:`icp` because
    a source point is free to slide within the tangent plane and is only penalised
    for leaving it (Low, 2004). *dst_normals* are estimated with
    :func:`pointcloud.estimate_normals` if not supplied. *init* and *trim* behave
    as in :func:`icp`. Returns ``(R, t, aligned, rmse)`` where ``rmse`` is the
    point-to-plane residual.

    ★No correspondence-distance limit and no robust loss (as :func:`icp`). Measured
    2026-11-09: bracket 500 pts + 100 uniform outliers, start 20 deg off — median
    27.7 deg, 0/20 within 3 deg (Open3D without a limit fails the same way);
    :func:`point_to_plane_icp_gated` with a limit of 5 % of the diameter 0.4 deg.
    On real T-LESS part 22 frames (started at the truth) 6.6 deg vs 2.3 deg with
    ``trim=0.2``. Pass *trim* or use the gated variant whenever the source holds
    points that are not on the destination surface.

    ``reproducible=True`` replaces the least-squares solve by the 6x6 normal equations
    ``(JᵀJ) x = Jᵀb`` with both products from :mod:`ozakimm` (independent of point order
    and BLAS threads), applies the transform element by element and sums the RMS with
    ``math.fsum``. The default path (``lstsq``) is unchanged."""
    from scipy.spatial import cKDTree
    from scipy.spatial.transform import Rotation
    import pointcloud

    P0 = np.asarray(src, np.float64)
    Q = np.asarray(dst, np.float64)
    N = (np.asarray(dst_normals, np.float64) if dst_normals is not None
         else pointcloud.estimate_normals(Q, k=k_normals))
    tree = cKDTree(Q)
    L = _cloud_size(Q)
    tol_abs = float(tol) * L
    # 正規方程式の正則化は回転の列(長さの次元)を L で割った無次元の系に掛ける(以前の
    # 1e-12·I は尺度 1e-7 の点群で回転ブロック ~1e-14 を潰した。N4 の兄弟)。
    col = np.array([1.0 / L] * 3 + [1.0] * 3) if L > 0 else np.ones(6)
    if reproducible:
        import ozakimm
        move, rowdot, rms = ozakimm._apply_rigid, ozakimm._rowdot, ozakimm._rms
    else:
        move = apply_transform

        def rowdot(a, b):
            return np.einsum("ij,ij->i", a, b)

        def rms(d):
            return float(np.sqrt(np.mean(d ** 2)))
    if init is None:
        R_tot = np.eye(3)
        t_tot = np.zeros(3)
        cur = P0.copy()
    else:
        R_tot = np.asarray(init[0], np.float64).copy()
        t_tot = np.asarray(init[1], np.float64).copy()
        cur = move(P0, R_tot, t_tot)
    keep_n = _checked_trim(trim, P0.shape[0], who="point_to_plane_icp")
    prev = np.inf
    rmse = np.inf
    for _ in range(max_iter):
        dist, idx = tree.query(cur)
        if keep_n < P0.shape[0]:
            sel = np.argpartition(dist, keep_n - 1)[:keep_n]
        else:
            sel = slice(None)
        p, q, n = cur[sel], Q[idx[sel]], N[idx[sel]]
        # linearised (small-angle) point-to-plane: [cross(p,n) | n] · [r | t] = -(p-q)·n
        if reproducible:
            A = np.concatenate([np.cross(p, n), n], axis=1)
            b = -rowdot(p - q, n)
            AtA = ozakimm._matmul_repro_any(A.T, A) * np.outer(col, col)
            Atb = ozakimm._matmul_repro_any(A.T, b[:, None])[:, 0] * col
            x = col * np.linalg.solve(AtA + 1e-12 * np.eye(6), Atb)
        else:
            A = np.concatenate([np.cross(p, n), n], axis=1)
            b = -rowdot(p - q, n)
            x, *_ = np.linalg.lstsq(A, b, rcond=None)
        R_inc = Rotation.from_rotvec(x[:3]).as_matrix()
        t_inc = x[3:]
        cur = move(cur, R_inc, t_inc) if reproducible else cur @ R_inc.T + t_inc
        R_tot = R_inc @ R_tot
        t_tot = R_inc @ t_tot + t_inc
        rmse = rms(rowdot(cur[sel] - q, n))
        if abs(prev - rmse) < tol_abs:
            break
        prev = rmse
    # final point-to-plane residual for the RETURNED pose (also gives a real value
    # when max_iter=0, where the loop never runs, instead of leaving rmse = inf).
    dist, idx = tree.query(cur)
    sel = (np.argpartition(dist, keep_n - 1)[:keep_n]
           if keep_n < P0.shape[0] else slice(None))
    rmse = rms(rowdot(cur[sel] - Q[idx[sel]], N[idx[sel]]))
    return R_tot, t_tot, cur, rmse


def _gate_value(max_corr_dist) -> float:
    try:
        g = float(max_corr_dist)
    except (TypeError, ValueError) as exc:
        raise ValueError("max_corr_dist must be a positive number") from exc
    if not (g > 0.0) or np.isnan(g):
        raise ValueError("max_corr_dist must be > 0 (a length in the cloud's units), got %r"
                         % (max_corr_dist,))
    return g


def _gated_selection(dist, gate, keep_n):
    """Indices of the pairs used this iteration: within *gate*, then the best *keep_n*."""
    cand = np.flatnonzero(dist <= gate)
    if cand.size > keep_n:
        cand = cand[np.argpartition(dist[cand], keep_n - 1)[:keep_n]]
    if cand.size < 3:
        raise ValueError(
            "icp_gated: only %d correspondence(s) within max_corr_dist=%g (need >= 3); "
            "raise max_corr_dist or give a better init" % (cand.size, gate))
    return cand


def icp_gated(src, dst, max_corr_dist, max_iter: int = 50, tol: float = 1e-8,
              init=None, trim: float | None = None, reproducible: bool = False):
    """Point-to-point ICP that ignores pairs farther apart than *max_corr_dist*.

    Same algorithm and arguments as :func:`icp` plus a hard correspondence gate:
    each iteration a source point whose nearest destination point lies farther than
    *max_corr_dist* (in the cloud's units) is left out of the Kabsch solve — the
    meaning of Open3D's ``max_correspondence_distance``. *trim* then keeps the best
    ``1 - trim`` fraction of the **source** count among the gated pairs. With
    ``max_corr_dist`` larger than every distance the result equals :func:`icp`
    (rotation difference < 1e-6 deg in the regression test).

    Measured 2026-11-09 (bracket 500 pts + 100 uniform outliers, start 20 deg off,
    20 trials, ``tests/test_opfix_geom3d_2026_11_09.py``): :func:`icp` median
    3.4 deg; this function with a gate of 5 % of the diameter 1.36 deg, 20/20
    within 3 deg (Open3D, same gate, 0.93 deg in the audit probe).

    Choose the gate from the expected residual after a coarse alignment (a few
    point spacings to a few % of the object size). Too small a gate starves the
    solve when the start is far off — use a coarse initialiser first
    (:func:`pca_align`, :func:`feature_register`, PPF).

    Returns ``(R, t, aligned, rmse, fitness)``: the first four as in :func:`icp`
    (``rmse`` over the gated, kept pairs of the returned pose) and ``fitness`` =
    fraction of source points with a destination point within the gate at the
    returned pose (Open3D's fitness).

    Raises:
        ValueError: ``max_corr_dist`` not a positive number, or fewer than 3
            pairs within the gate at any iteration (fail-closed; no pose is
            invented from too few pairs).
    """
    from scipy.spatial import cKDTree

    gate = _gate_value(max_corr_dist)
    P0 = np.asarray(src, np.float64)
    Q = np.asarray(dst, np.float64)
    if reproducible:
        import ozakimm
        move = ozakimm._apply_rigid
        rms = ozakimm._rms
    else:
        move = apply_transform

        def rms(d):
            return float(np.sqrt(np.mean(d ** 2)))
    tree = cKDTree(Q)
    tol_abs = float(tol) * _cloud_size(Q)
    if init is None:
        R_tot = np.eye(3)
        t_tot = np.zeros(3)
        cur = P0.copy()
    else:
        R_tot = np.asarray(init[0], np.float64).copy()
        t_tot = np.asarray(init[1], np.float64).copy()
        cur = move(P0, R_tot, t_tot)
    keep_n = _checked_trim(trim, P0.shape[0], strict_count=True, who="icp_gated")
    prev = np.inf
    for _ in range(max_iter):
        dist, idx = tree.query(cur)
        sel = _gated_selection(dist, gate, keep_n)
        rmse = rms(dist[sel])
        R, t = kabsch(cur[sel], Q[idx[sel]], reproducible=reproducible)
        cur = move(cur, R, t)
        R_tot = R @ R_tot
        t_tot = R @ t_tot + t
        if abs(prev - rmse) < tol_abs:
            break
        prev = rmse
    dist, _ = tree.query(cur)
    sel = _gated_selection(dist, gate, keep_n)
    rmse = rms(dist[sel])
    fitness = float(np.mean(dist <= gate)) if dist.size else 0.0
    return R_tot, t_tot, cur, rmse, fitness


def point_to_plane_icp_gated(src, dst, max_corr_dist, dst_normals=None,
                             k_normals: int = 16, max_iter: int = 50, tol: float = 1e-8,
                             init=None, trim: float | None = None,
                             reproducible: bool = False):
    """Point-to-plane ICP that ignores pairs farther apart than *max_corr_dist*.

    Same algorithm and arguments as :func:`point_to_plane_icp` plus the hard
    correspondence gate of :func:`icp_gated` (Open3D's
    ``max_correspondence_distance``; the gate is on the point-to-point distance of
    the nearest-neighbour pair, the residual minimised is point-to-plane). With a
    gate larger than every distance the result equals :func:`point_to_plane_icp`.

    Measured 2026-11-09 (bracket 500 pts + 100 uniform outliers, start 20 deg off,
    20 trials): :func:`point_to_plane_icp` median 27.2 deg (0/20 within 3 deg);
    this function with a gate of 5 % of the diameter 0.37 deg, 20/20 within
    3 deg, fitness 0.80 (= the 500 of 600 source points that are not outliers;
    Open3D, same gate, 0.40 deg in the audit probe).

    Returns ``(R, t, aligned, rmse, fitness)`` — ``rmse`` is the point-to-plane
    residual over the gated, kept pairs of the returned pose, ``fitness`` the
    fraction of source points within the gate.

    Raises:
        ValueError: ``max_corr_dist`` not a positive number, or fewer than 3
            pairs within the gate at any iteration.
    """
    from scipy.spatial import cKDTree
    from scipy.spatial.transform import Rotation
    import pointcloud

    gate = _gate_value(max_corr_dist)
    P0 = np.asarray(src, np.float64)
    Q = np.asarray(dst, np.float64)
    N = (np.asarray(dst_normals, np.float64) if dst_normals is not None
         else pointcloud.estimate_normals(Q, k=k_normals))
    tree = cKDTree(Q)
    L = _cloud_size(Q)
    tol_abs = float(tol) * L
    col = np.array([1.0 / L] * 3 + [1.0] * 3) if L > 0 else np.ones(6)
    if reproducible:
        import ozakimm
        move, rowdot, rms = ozakimm._apply_rigid, ozakimm._rowdot, ozakimm._rms
    else:
        move = apply_transform

        def rowdot(a, b):
            return np.einsum("ij,ij->i", a, b)

        def rms(d):
            return float(np.sqrt(np.mean(d ** 2)))
    if init is None:
        R_tot = np.eye(3)
        t_tot = np.zeros(3)
        cur = P0.copy()
    else:
        R_tot = np.asarray(init[0], np.float64).copy()
        t_tot = np.asarray(init[1], np.float64).copy()
        cur = move(P0, R_tot, t_tot)
    keep_n = _checked_trim(trim, P0.shape[0], strict_count=True, who="point_to_plane_icp_gated")
    prev = np.inf
    for _ in range(max_iter):
        dist, idx = tree.query(cur)
        sel = _gated_selection(dist, gate, keep_n)
        p, q, n = cur[sel], Q[idx[sel]], N[idx[sel]]
        A = np.concatenate([np.cross(p, n), n], axis=1)
        b = -rowdot(p - q, n)
        if reproducible:
            AtA = ozakimm._matmul_repro_any(A.T, A) * np.outer(col, col)
            Atb = ozakimm._matmul_repro_any(A.T, b[:, None])[:, 0] * col
            x = col * np.linalg.solve(AtA + 1e-12 * np.eye(6), Atb)
        else:
            x, *_ = np.linalg.lstsq(A, b, rcond=None)
        R_inc = Rotation.from_rotvec(x[:3]).as_matrix()
        t_inc = x[3:]
        cur = move(cur, R_inc, t_inc) if reproducible else cur @ R_inc.T + t_inc
        R_tot = R_inc @ R_tot
        t_tot = R_inc @ t_tot + t_inc
        rmse = rms(rowdot(cur[sel] - q, n))
        if abs(prev - rmse) < tol_abs:
            break
        prev = rmse
    dist, idx = tree.query(cur)
    sel = _gated_selection(dist, gate, keep_n)
    rmse = rms(rowdot(cur[sel] - Q[idx[sel]], N[idx[sel]]))
    fitness = float(np.mean(dist <= gate)) if dist.size else 0.0
    return R_tot, t_tot, cur, rmse, fitness


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
    if P.shape[0] < 3 or Q.shape[0] < 3:
        # fewer than 3 points -> principal axes are undefined; fall back to a
        # centroid-only alignment (identity rotation), consistent with icp
        # accepting the same input instead of raising an opaque shape error.
        return np.eye(3), cq - cp
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
             tol: float = 1e-8, init: str = "auto"):
    """Robust one-call registration: a large-rotation start, then Trimmed
    :func:`icp` for outlier/partial-overlap robustness. Returns the same
    ``(R, t, aligned, rmse)`` tuple as :func:`icp`.

    *init* selects the coarse initialiser:

    * ``"pca"`` — :func:`pca_align` (principal axes). Fast, but the axes of a
      *partial* view differ from those of the full cloud, so below ~80 %
      overlap it starts ICP in the wrong basin (measured 2026-09-02: 116-171
      deg rotation error at 50-74 % source overlap).
    * ``"feature"`` — :func:`feature_register` (FPFH + RANSAC), which matches
      local geometry and so survives partial overlap.
    * ``"auto"`` (default) — run ICP from **both** starts (feature only when the
      clouds are big enough for FPFH neighbourhoods) and keep the one with the
      lower trimmed ``rmse``; the returned ``rmse`` is that of the kept pose.
    """
    if init not in ("auto", "pca", "feature"):
        raise ValueError("init must be 'auto', 'pca' or 'feature'")
    P = np.asarray(src, np.float64)
    Q = np.asarray(dst, np.float64)
    starts = []
    if init in ("auto", "pca"):
        starts.append(pca_align(P, Q))
    if init in ("auto", "feature"):
        # FPFH needs k-neighbourhoods on both clouds; on tiny inputs fall back to
        # PCA silently in auto mode, but fail loudly if the caller asked for it.
        big_enough = min(P.shape[0], Q.shape[0]) >= 32
        if big_enough:
            try:
                R0, t0, _, _ = feature_register(P, Q, refine=False)
                starts.append((R0, t0))
            except (ValueError, IndexError) as e:
                if init == "feature":
                    raise ValueError(f"feature initialiser failed: {e}") from e
        elif init == "feature":
            raise ValueError("feature initialiser needs >= 32 points in both clouds")
    if not starts:                      # auto on a tiny cloud -> PCA/centroid start
        starts.append(pca_align(P, Q))
    best = None
    for R0, t0 in starts:
        out = icp(P, Q, max_iter=max_iter, tol=tol, init=(R0, t0), trim=trim)
        if best is None or out[3] < best[3]:
            best = out
    return best


def feature_register(src, dst, k: int = 16, bins: int = 11, ransac_iter: int = 4000,
                     inlier_thresh: float | None = None, seed: int = 0,
                     refine: bool = True):
    """Correspondence-based registration via FPFH features + RANSAC (+ ICP refine).

    Unlike :func:`pca_align` (which needs distinct global principal axes), this
    matches local-geometry descriptors (:func:`pointcloud.fpfh`), so it aligns
    shapes whose global axes are ambiguous but whose local geometry is
    distinctive. Each source point is matched to its nearest-descriptor
    destination point; RANSAC samples 3 correspondences at a time, keeps the
    transform with the most inliers (within *inlier_thresh*, default 3x the median
    destination point spacing), refits on the inliers, then (``refine``) polishes
    with Trimmed :func:`icp`. Returns ``(R, t, aligned, rmse)`` like :func:`icp`."""
    from scipy.spatial import cKDTree
    import pointcloud

    P = np.asarray(src, np.float64)
    Q = np.asarray(dst, np.float64)
    fp = pointcloud.fpfh(P, k=k, bins=bins)
    fq = pointcloud.fpfh(Q, k=k, bins=bins)
    match = cKDTree(fq).query(fp)[1]              # src i -> nearest-descriptor dst index
    Qm = Q[match]
    if inlier_thresh is None:
        nn = cKDTree(Q).query(Q, k=2)[0][:, 1]
        inlier_thresh = 3.0 * float(np.median(nn))
    rng = np.random.default_rng(seed)
    n = P.shape[0]
    best = None
    for _ in range(max(1, int(ransac_iter))):
        s = rng.choice(n, 3, replace=False)
        try:
            R, t = kabsch(P[s], Qm[s])
        except ValueError:
            continue
        err = np.linalg.norm(apply_transform(P, R, t) - Qm, axis=1)
        inl = err < inlier_thresh
        c = int(inl.sum())
        if best is None or c > best[0]:
            best = (c, inl)
    inl = best[1] if best is not None else np.zeros(n, bool)
    if int(inl.sum()) >= 3:
        R, t = kabsch(P[inl], Qm[inl])
    else:                                          # no consensus -> centroid start
        R, t = np.eye(3), Q.mean(0) - P.mean(0)
    if refine:
        return icp(P, Q, init=(R, t), trim=0.2)
    aligned = apply_transform(P, R, t)
    rmse = float(np.sqrt(np.mean(cKDTree(Q).query(aligned)[0] ** 2)))
    return R, t, aligned, rmse
