"""Visual / RGB-D odometry — frame-to-frame camera motion (numpy + scipy).

The self-localization layer of the perception stack: given two frames (their depth
and the optical flow between them, or matched 3-D points), estimate how the camera
moved, then chain those relative motions into a trajectory. This is what tells a
walking or manipulating robot *where it is now* relative to where it started —
built on :mod:`camera` (back-projection / PnP), :mod:`stereo` (depth) and
:mod:`flow` (correspondences), with no learned model.

Two estimators: 3-D↔3-D (:func:`rgbd_odometry` — back-project both frames, robustly
fit a rigid transform between the matched clouds) and 3-D↔2-D
(:func:`pnp_odometry` — the previous frame's points against the current frame's
pixels via PnP). Plus trajectory utilities: compose relative motions
(:func:`integrate_trajectory`) and evaluate against ground truth with a Umeyama
alignment (:func:`umeyama_align`, :func:`trajectory_error`).

Convention: a returned relative pose ``(R, t)`` is the **scene-point motion**
between frames, ``X1 ≈ R @ X0 + t`` (points expressed in each camera's frame);
the camera's own motion is its inverse. ``integrate_trajectory`` composes these
into absolute 4x4 poses.

References (public literature — reimplemented, not derived from any product):
- Umeyama, "Least-squares estimation of transformation parameters between two
  point patterns", PAMI 1991 (similarity alignment / trajectory ATE).
- Besl & McKay 1992 / Arun et al. 1987 (rigid transform from correspondences).
- Fischler & Bolles 1981 (RANSAC).
"""
from __future__ import annotations

import numpy as np

__all__ = ["rgbd_odometry", "pnp_odometry", "integrate_trajectory",
           "umeyama_align", "trajectory_error"]


def _kabsch(A, B):
    """Rigid transform (R, t) with B ≈ R@A + t for corresponded (N,3) clouds."""
    ca, cb = A.mean(0), B.mean(0)
    H = (A - ca).T @ (B - cb)
    U, _, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ np.diag([1.0, 1.0, d]) @ U.T
    return R, cb - R @ ca


def _ransac_kabsch(A, B, thresh: float, iters: int, seed: int):
    """Robust rigid transform A->B by RANSAC over 3-point samples + refit on inliers."""
    n = A.shape[0]
    rng = np.random.default_rng(seed)
    best_inl, best_cnt = None, -1
    if n < 3:
        R, t = _kabsch(A, B) if n else (np.eye(3), np.zeros(3))
        return R, t, np.ones(n, bool)
    for _ in range(int(iters)):
        i = rng.choice(n, 3, replace=False)
        R, t = _kabsch(A[i], B[i])
        err = np.linalg.norm((A @ R.T + t) - B, axis=1)
        inl = err <= thresh
        cnt = int(inl.sum())
        if cnt > best_cnt:
            best_cnt, best_inl = cnt, inl
    if best_inl is None or best_cnt < 3:
        R, t = _kabsch(A, B)                        # RANSAC found no consensus: full refit,
        inl = np.linalg.norm((A @ R.T + t) - B, axis=1) <= thresh  # but report the REAL
        return R, t, inl                            # inlier mask (not all-True) so a failed
    R, t = _kabsch(A[best_inl], B[best_inl])        # fit is not disguised as confident
    inl = np.linalg.norm((A @ R.T + t) - B, axis=1) <= thresh
    return R, t, inl


def rgbd_odometry(depth0, depth1, u, v, K, thresh: float = 0.02,
                  iters: int = 200, min_depth: float = 1e-6,
                  max_depth: float = np.inf, stride: int = 4, seed: int = 0):
    """Frame-to-frame camera motion from an RGB-D pair + optical flow.

    Back-projects each valid pixel at ``t0`` (``depth0``) and its flow-matched pixel
    at ``t1`` (``depth1`` sampled at ``(x+u, y+v)``) into two 3-D clouds, then fits a
    robust rigid transform between the matched points (RANSAC + Kabsch, Arun 1987).
    ``stride`` subsamples pixels for speed. Returns ``(R, t, inlier_fraction)`` = the
    **camera's motion** between the two frames (the relative camera-to-world pose):
    a point fixed in the world appears to move by the inverse. Feed these directly to
    :func:`integrate_trajectory` to build the camera path. Depth outside
    ``[min_depth, max_depth]`` or whose flow lands off-frame is dropped."""
    from scipy import ndimage
    from camera import backproject

    Z0 = np.asarray(depth0, np.float64)
    Z1 = np.asarray(depth1, np.float64)
    u = np.asarray(u, np.float64)
    v = np.asarray(v, np.float64)
    if not (Z0.shape == Z1.shape == u.shape == v.shape) or Z0.ndim != 2:
        raise ValueError("depth0/depth1/u/v must be equal-shape 2-D arrays")
    H, W = Z0.shape
    s = max(1, int(stride))
    yy, xx = np.mgrid[0:H:s, 0:W:s].astype(np.float64)
    z0 = Z0[::s, ::s]
    uu, vv = u[::s, ::s], v[::s, ::s]
    x1, y1 = xx + uu, yy + vv
    z1 = ndimage.map_coordinates(Z1, [y1, x1], order=1, mode="constant", cval=np.nan)
    ok = (np.isfinite(z0) & (z0 > min_depth) & (z0 < max_depth)
          & np.isfinite(z1) & (z1 > min_depth) & (z1 < max_depth)
          & (x1 >= 0) & (x1 <= W - 1) & (y1 >= 0) & (y1 <= H - 1))
    if int(ok.sum()) < 3:
        return np.eye(3), np.zeros(3), 0.0
    p0 = np.stack([xx[ok], yy[ok]], 1)
    p1 = np.stack([x1[ok], y1[ok]], 1)
    X0 = backproject(p0, z0[ok], K)
    X1 = backproject(p1, z1[ok], K)
    Rs, ts, inl = _ransac_kabsch(X0, X1, thresh, iters, seed)
    # _ransac_kabsch gives the scene-point motion (X1 = Rs X0 + ts); return the CAMERA
    # motion, its inverse, so integrate_trajectory composes a correct camera path.
    return Rs.T, -Rs.T @ ts, float(inl.mean())


def pnp_odometry(points3d_prev, uv_curr, K, **kw):
    """Frame-to-frame camera pose from the previous frame's 3-D points seen in the
    current frame's pixels (3-D↔2-D). Thin wrapper over :func:`camera.solve_pnp`;
    returns ``(R, t, rms)`` mapping the previous points into the current camera
    frame. Use when only the previous frame's depth is available."""
    from camera import solve_pnp

    return solve_pnp(points3d_prev, uv_curr, K, **kw)


def _to_4x4(R, t):
    T = np.eye(4)
    T[:3, :3] = np.asarray(R, np.float64)
    T[:3, 3] = np.asarray(t, np.float64).ravel()
    return T


def integrate_trajectory(rel_poses, T0=None):
    """Compose a sequence of relative motions into absolute 4x4 poses.

    ``rel_poses`` is a list of ``(R, t)`` (or 4x4) relative transforms between
    consecutive frames; returns an ``(N+1, 4, 4)`` stack of absolute poses starting
    at ``T0`` (identity by default). The dead-reckoned trajectory a robot walks."""
    T = np.eye(4) if T0 is None else np.asarray(T0, np.float64)
    out = [T.copy()]
    for p in rel_poses:
        if isinstance(p, (tuple, list)) and len(p) == 2:
            step = _to_4x4(p[0], p[1])               # an (R, t) pair
        else:
            step = np.asarray(p, np.float64)
            if step.shape != (4, 4):
                raise ValueError("each relative pose must be a 4x4 matrix or (R, t)")
        T = T @ step
        out.append(T.copy())
    return np.stack(out)


def umeyama_align(src, dst, with_scale: bool = True):
    """Least-squares similarity aligning ``src`` points onto ``dst`` (Umeyama 1991).

    Returns ``(s, R, t)`` with ``dst ≈ s * R @ src + t``. The standard way to line up
    an estimated trajectory with ground truth (which is only known up to a rigid — or
    for monocular, similarity — transform) before measuring error. ``src``/``dst`` are
    (N,3)."""
    A = np.asarray(src, np.float64)
    B = np.asarray(dst, np.float64)
    if A.shape != B.shape or A.ndim != 2 or A.shape[1] != 3:
        raise ValueError("src and dst must be equal-shape (N, 3)")
    n = A.shape[0]
    ca, cb = A.mean(0), B.mean(0)
    Ac, Bc = A - ca, B - cb
    H = Bc.T @ Ac / n
    U, D, Vt = np.linalg.svd(H)
    S = np.eye(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        S[2, 2] = -1.0
    R = U @ S @ Vt
    var = (Ac ** 2).sum() / n
    s = (np.trace(np.diag(D) @ S) / var) if (with_scale and var > 1e-12) else 1.0
    t = cb - s * R @ ca
    return float(s), R, t


def trajectory_error(est_poses, gt_poses, align: bool = True):
    """Absolute Trajectory Error (ATE) between estimated and ground-truth poses.

    Takes two ``(N,4,4)`` (or (N,3) position) trajectories, optionally Umeyama-aligns
    the estimate to ground truth first (the fair comparison for odometry, which is
    only recoverable up to a global transform), and returns
    ``{rmse, mean, max, aligned_positions}`` of the per-pose position error. The
    honest scalar for how well the odometry tracked."""
    def positions(P):
        P = np.asarray(P, np.float64)
        return P[:, :3, 3] if P.ndim == 3 else P
    E = positions(est_poses)
    G = positions(gt_poses)
    if E.shape != G.shape:
        raise ValueError("est and gt trajectories must have the same length/shape")
    if align:
        s, R, t = umeyama_align(E, G)
        E = (s * (E @ R.T)) + t
    err = np.linalg.norm(E - G, axis=1)
    return {"rmse": float(np.sqrt(np.mean(err ** 2))), "mean": float(err.mean()),
            "max": float(err.max()), "aligned_positions": E}
