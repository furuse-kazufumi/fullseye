"""Pinhole camera geometry — the 2-D <-> 3-D backbone of the perception stack.

Everything else in the perception modules hangs off this: :mod:`stereo` needs a
rectified pair and a focal length to turn disparity into metric depth,
:mod:`pointcloud`/:mod:`registration` need a way to lift a depth frame into a
camera-frame cloud, and object 6-DoF pose (grasping) needs to solve where a known
3-D model sits from its 2-D projection. This module supplies those primitives with
no learned model and no product code — just the classical projective geometry.

Frame convention (right-handed, OpenCV-style): the camera sits at the origin
looking down **+Z**, image ``u`` grows right, ``v`` grows down. A world point ``X``
maps to the camera frame by ``X_cam = R @ X_world + t`` and projects to
``u = fx*X/Z + cx``, ``v = fy*Y/Z + cy``. The intrinsic matrix is
``K = [[fx, s, cx], [0, fy, cy], [0, 0, 1]]`` and the 3x4 projection is
``P = K @ [R | t]``.

References (all public literature — reimplemented, not derived from any product):
- Hartley & Zisserman, *Multiple View Geometry in Computer Vision*, 2nd ed. 2004
  (linear triangulation §12.2, DLT camera resection §7.1, normalized 8-point
  fundamental §11.2, essential decomposition §9.6.2, cheirality §9.6.3).
- Hartley, "In Defense of the Eight-Point Algorithm", PAMI 1997 (normalization).
- Brown, "Close-Range Camera Calibration", 1971 (radial-tangential distortion).
- Fusiello, Trucco & Verri, "A compact algorithm for rectification of stereo
  pairs", Machine Vision and Applications 2000 (calibrated stereo rectification).
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "intrinsic_matrix", "decompose_intrinsics", "projection_matrix",
    "project_points", "backproject", "depth_to_points", "normals_from_depth",
    "triangulate", "reprojection_error", "solve_pnp",
    "rodrigues", "rotation_log",
    "fundamental_matrix", "essential_matrix", "essential_from_fundamental",
    "decompose_essential", "recover_pose", "epipolar_lines",
    "distort_points", "undistort_points", "stereo_rectify",
]


# --- small helpers ---------------------------------------------------------- #
def _pts2(a) -> np.ndarray:
    a = np.asarray(a, np.float64)
    if a.ndim != 2 or a.shape[1] != 2:
        raise ValueError("expected (N, 2) pixel coordinates, got shape %r" % (a.shape,))
    return a


def _pts3(a) -> np.ndarray:
    a = np.asarray(a, np.float64)
    if a.ndim != 2 or a.shape[1] != 3:
        raise ValueError("expected (N, 3) points, got shape %r" % (a.shape,))
    return a


def _K3(K) -> np.ndarray:
    K = np.asarray(K, np.float64)
    if K.shape != (3, 3):
        raise ValueError("intrinsic matrix K must be 3x3, got %r" % (K.shape,))
    return K


def rodrigues(rvec) -> np.ndarray:
    """Axis-angle rotation vector (3,) -> rotation matrix (3, 3) (Rodrigues 1840).

    The vector's direction is the rotation axis and its norm the angle in radians.
    Inverse of :func:`rotation_log`. Used to parameterize pose during PnP refinement
    (a minimal 3-DoF representation that stays a valid rotation under +/- updates)."""
    r = np.asarray(rvec, np.float64).ravel()
    if r.size != 3:
        raise ValueError("rotation vector must have 3 elements")
    theta = float(np.linalg.norm(r))
    if theta < 1e-12:
        return np.eye(3)
    k = r / theta
    K = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    return np.eye(3) + np.sin(theta) * K + (1.0 - np.cos(theta)) * (K @ K)


def rotation_log(R) -> np.ndarray:
    """Rotation matrix (3, 3) -> axis-angle vector (3,). Inverse of :func:`rodrigues`."""
    R = np.asarray(R, np.float64)
    if R.shape != (3, 3):
        raise ValueError("R must be 3x3")
    cos = np.clip((np.trace(R) - 1.0) / 2.0, -1.0, 1.0)
    theta = float(np.arccos(cos))
    if theta < 1e-12:
        return np.zeros(3)
    if np.pi - theta < 1e-6:
        # near 180 deg: axis from the largest diagonal of R + I (numerically stable)
        A = (R + np.eye(3)) / 2.0
        k = np.sqrt(np.clip(np.diag(A), 0.0, None))
        i = int(np.argmax(k))
        k = A[:, i] / (k[i] if k[i] > 1e-12 else 1.0)
        k = k / max(np.linalg.norm(k), 1e-12)
        return theta * k
    axis = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    return theta * axis / (2.0 * np.sin(theta))


def _project_camframe(Xc: np.ndarray, K: np.ndarray):
    """Project camera-frame points (N,3) with K -> (uv (N,2), depth (N,))."""
    z = Xc[:, 2]
    zsafe = np.where(np.abs(z) < 1e-12, 1e-12, z)
    xh = Xc @ K.T
    uv = xh[:, :2] / zsafe[:, None]
    return uv, z


# --- intrinsics / projection matrices --------------------------------------- #
def intrinsic_matrix(fx, fy=None, cx=0.0, cy=0.0, skew=0.0) -> np.ndarray:
    """Assemble a pinhole intrinsic matrix K (3, 3).

    ``fy`` defaults to ``fx`` (square pixels). ``skew`` is the axis-skew term
    (0 for almost every real sensor)."""
    fx = float(fx)
    fy = fx if fy is None else float(fy)
    return np.array([[fx, float(skew), float(cx)],
                     [0.0, fy, float(cy)],
                     [0.0, 0.0, 1.0]])


def decompose_intrinsics(K) -> dict:
    """Pull ``fx, fy, cx, cy, skew`` back out of a K (3, 3)."""
    K = _K3(K)
    return {"fx": float(K[0, 0]), "fy": float(K[1, 1]),
            "cx": float(K[0, 2]), "cy": float(K[1, 2]), "skew": float(K[0, 1])}


def projection_matrix(K, R=None, t=None) -> np.ndarray:
    """Build the 3x4 projection ``P = K @ [R | t]``. ``R``/``t`` default to the
    identity pose (camera at the world origin looking down +Z)."""
    K = _K3(K)
    R = np.eye(3) if R is None else np.asarray(R, np.float64)
    t = np.zeros(3) if t is None else np.asarray(t, np.float64).ravel()
    if R.shape != (3, 3) or t.size != 3:
        raise ValueError("R must be 3x3 and t length-3")
    return K @ np.hstack([R, t[:, None]])


# --- projection / back-projection ------------------------------------------- #
def project_points(points, K, R=None, t=None):
    """Project world points (N, 3) to pixels. Returns ``(uv (N,2), depth (N,))``.

    ``depth`` is the camera-frame Z of each point (negative = behind the camera —
    the pixel is still returned but is not physically visible; callers that need
    only visible points should filter on ``depth > 0``)."""
    P = _pts3(points)
    K = _K3(K)
    R = np.eye(3) if R is None else np.asarray(R, np.float64)
    t = np.zeros(3) if t is None else np.asarray(t, np.float64).ravel()
    Xc = P @ R.T + t
    return _project_camframe(Xc, K)


def backproject(pixels, depth, K) -> np.ndarray:
    """Lift pixels (N, 2) at camera-frame ``depth`` (scalar or (N,)) to camera-frame
    points (N, 3). Inverse of :func:`project_points` at the identity pose."""
    uv = _pts2(pixels)
    K = _K3(K)
    z = np.broadcast_to(np.asarray(depth, np.float64), (uv.shape[0],)).astype(np.float64)
    Kinv = np.linalg.inv(K)
    rays = np.hstack([uv, np.ones((uv.shape[0], 1))]) @ Kinv.T   # (N,3), 3rd col ~1
    rays = rays / rays[:, 2:3]
    return rays * z[:, None]


def depth_to_points(depth, K, organized: bool = False):
    """Back-project a full depth map (H, W) to a camera-frame point cloud.

    ``depth`` holds metric Z per pixel; non-finite or ``<= 0`` values are treated
    as "no return". With ``organized=False`` (default) returns the finite points
    (M, 3); with ``organized=True`` returns an (H, W, 3) grid with ``NaN`` where the
    depth is invalid (so it lines up pixel-for-pixel with the image, which
    :func:`normals_from_depth` needs)."""
    Z = np.asarray(depth, np.float64)
    if Z.ndim != 2:
        raise ValueError("depth must be a 2-D (H, W) map")
    K = _K3(K)
    H, W = Z.shape
    fx, fy = K[0, 0], K[1, 1]
    cx, cy, s = K[0, 2], K[1, 2], K[0, 1]
    v, u = np.mgrid[0:H, 0:W].astype(np.float64)
    valid = np.isfinite(Z) & (Z > 0.0)
    # invert the upper-triangular K on the pixel grid (handles skew)
    y = (v - cy) / fy
    x = (u - cx - s * y) / fx
    grid = np.stack([x * Z, y * Z, Z], axis=-1)
    if organized:
        out = grid.copy()
        out[~valid] = np.nan
        return out
    return grid[valid]


def normals_from_depth(depth, K, smooth: int = 0) -> np.ndarray:
    """Per-pixel surface normal (H, W, 3) from an organized depth map.

    Back-projects the depth to a point grid, takes tangent vectors by central
    differences along image rows/columns and normals as their cross product, then
    orients every normal toward the camera (``-Z``). This is the organized-cloud
    shortcut to :func:`pointcloud.estimate_normals` — no neighbour search needed
    because the depth grid already encodes adjacency. Normals are ``NaN`` where the
    depth (or a neighbour it needs) is invalid. ``smooth`` optionally box-blurs the
    depth first to tame stereo noise. Feeds grasp approach directions and terrain
    foothold scoring."""
    Z = np.asarray(depth, np.float64)
    if Z.ndim != 2:
        raise ValueError("depth must be a 2-D (H, W) map")
    if smooth and smooth > 1:
        from scipy import ndimage
        Zf = Z.copy()
        m = np.isfinite(Zf) & (Zf > 0)
        Zf[~m] = np.nan
        Zf = ndimage.uniform_filter(np.nan_to_num(Zf), int(smooth)) / np.maximum(
            ndimage.uniform_filter(m.astype(float), int(smooth)), 1e-9)
        Z = np.where(m, Zf, Z)
    grid = depth_to_points(Z, K, organized=True)              # (H,W,3), NaN invalid
    du = np.full_like(grid, np.nan)
    dv = np.full_like(grid, np.nan)
    du[:, 1:-1] = grid[:, 2:] - grid[:, :-2]                   # d/dx (central)
    dv[1:-1, :] = grid[2:, :] - grid[:-2, :]                   # d/dy (central)
    n = np.cross(du, dv)
    norm = np.linalg.norm(n, axis=-1, keepdims=True)
    n = n / np.where(norm < 1e-12, np.nan, norm)
    # orient toward the camera centre (origin): a visible surface normal must point
    # back toward the viewpoint, i.e. n . X <= 0 (the ray to the point). Testing
    # only the Z sign is wrong once the surface is viewed obliquely enough that the
    # lateral normal components dominate (a steeply-slanted wall past ~55 deg).
    dotp = np.einsum("...i,...i->...", n, grid)
    flip = dotp > 0
    n[flip] *= -1.0
    return n


# --- triangulation ---------------------------------------------------------- #
def triangulate(uv1, uv2, P1, P2) -> np.ndarray:
    """Linear (DLT) triangulation of matched pixels from two views (H&Z §12.2).

    ``uv1``/``uv2`` are (N, 2) corresponding pixels; ``P1``/``P2`` the 3x4
    projection matrices (see :func:`projection_matrix`). Returns the reconstructed
    world points (N, 3)."""
    a = _pts2(uv1)
    b = _pts2(uv2)
    if a.shape != b.shape:
        raise ValueError("uv1 and uv2 must have the same shape")
    P1 = np.asarray(P1, np.float64)
    P2 = np.asarray(P2, np.float64)
    if P1.shape != (3, 4) or P2.shape != (3, 4):
        raise ValueError("P1/P2 must be 3x4 projection matrices")
    N = a.shape[0]
    out = np.empty((N, 3))
    for i in range(N):
        A = np.stack([
            a[i, 0] * P1[2] - P1[0],
            a[i, 1] * P1[2] - P1[1],
            b[i, 0] * P2[2] - P2[0],
            b[i, 1] * P2[2] - P2[1],
        ])
        _, _, Vt = np.linalg.svd(A)
        X = Vt[-1]
        out[i] = X[:3] / (X[3] if abs(X[3]) > 1e-12 else 1e-12)
    return out


def reprojection_error(points3d, uv, K, R=None, t=None) -> np.ndarray:
    """Per-point reprojection error in pixels: ``||project(X; R,t) - uv||`` (N,).

    The honest scalar for how well a solved pose actually explains the
    observations — small means the pose fits, large flags outliers or a wrong
    solution."""
    uv = _pts2(uv)
    proj, _ = project_points(points3d, K, R, t)
    return np.linalg.norm(proj - uv, axis=1)


# --- PnP: object 6-DoF pose from 2-D<->3-D correspondences ------------------ #
def _pnp_dlt(X: np.ndarray, uv: np.ndarray, K: np.ndarray):
    """DLT resection giving an initial (R, t) with known K (H&Z §7.1).

    Solves for [R|t] (up to sign/scale) in normalized image coordinates, then
    projects the 3x3 block back onto SO(3) with an SVD and fixes scale + cheirality.
    """
    Kinv = np.linalg.inv(K)
    m = np.hstack([uv, np.ones((uv.shape[0], 1))]) @ Kinv.T     # normalized rays
    m = m[:, :2] / m[:, 2:3]
    N = X.shape[0]
    A = np.zeros((2 * N, 12))
    Xh = np.hstack([X, np.ones((N, 1))])
    for i in range(N):
        A[2 * i, 0:4] = Xh[i]
        A[2 * i, 8:12] = -m[i, 0] * Xh[i]
        A[2 * i + 1, 4:8] = Xh[i]
        A[2 * i + 1, 8:12] = -m[i, 1] * Xh[i]
    _, _, Vt = np.linalg.svd(A)
    M = Vt[-1].reshape(3, 4)

    def extract(Mm):
        U, S, Vt2 = np.linalg.svd(Mm[:, :3])
        Rr = U @ Vt2
        if np.linalg.det(Rr) < 0:
            Rr = -Rr
        scale = 1.0 / np.mean(S)
        tt = Mm[:, 3] * scale
        return Rr, tt

    best = None
    for sign in (1.0, -1.0):
        R0, t0 = extract(sign * M)
        # the sign of t is tied to the sign of M; pick the (R, t) whose points sit
        # in front of the camera (positive depth) with the lower reprojection error
        depth = (X @ R0.T + t0)[:, 2]
        front = float((depth > 0).mean())
        err = float(np.mean(reprojection_error(X, uv, K, R0, t0)))
        score = (front, -err)
        if best is None or score > best[0]:
            best = (score, R0, t0)
    return best[1], best[2]


def _coplanar(X: np.ndarray, tol: float = 1e-6) -> bool:
    """True if the 3-D points lie (near-)coplanar — where general DLT resection is
    rank-deficient and returns garbage. Ratio of the smallest to largest spread."""
    c = X - X.mean(0)
    s = np.linalg.svd(c, compute_uv=False)
    return bool(s[-1] <= tol * s[0])


def _pnp_planar(X: np.ndarray, uv: np.ndarray, K: np.ndarray):
    """Pose init for a coplanar target via the plane->image homography (H&Z §8.1.1).

    General DLT resection is degenerate for planar points; instead fit a homography
    from the model's own in-plane coordinates to the normalized image points and
    decompose it into (R, t). Returns an initial (R, t) for the LM refinement."""
    c = X.mean(0)
    Xc = X - c
    _, _, Vt = np.linalg.svd(Xc)
    B = Vt.T                                        # columns: 2 in-plane axes + normal
    p2 = Xc @ B[:, :2]                              # (N,2) planar model coords
    Kinv = np.linalg.inv(K)
    m = np.hstack([uv, np.ones((uv.shape[0], 1))]) @ Kinv.T
    m = m[:, :2] / m[:, 2:3]
    # homography DLT: p2 (homogeneous) -> m
    N = X.shape[0]
    A = np.zeros((2 * N, 9))
    for i in range(N):
        x, y = p2[i]
        u, v = m[i]
        A[2 * i] = [-x, -y, -1, 0, 0, 0, u * x, u * y, u]
        A[2 * i + 1] = [0, 0, 0, -x, -y, -1, v * x, v * y, v]
    _, _, Vt2 = np.linalg.svd(A)
    H = Vt2[-1].reshape(3, 3)
    best = None
    for s in (1.0, -1.0):
        lam = s / max(0.5 * (np.linalg.norm(H[:, 0]) + np.linalg.norm(H[:, 1])), 1e-12)
        r1, r2, t_h = lam * H[:, 0], lam * H[:, 1], lam * H[:, 2]
        r3 = np.cross(r1, r2)
        U, _, Vt3 = np.linalg.svd(np.stack([r1, r2, r3], 1))
        Rh = U @ Vt3
        if np.linalg.det(Rh) < 0:
            Rh = -Rh
        R_full = Rh @ B.T                           # plane-frame -> original model frame
        t_full = t_h - R_full @ c
        err = float(np.mean(reprojection_error(X, uv, K, R_full, t_full)))
        front = float(((X @ R_full.T + t_full)[:, 2] > 0).mean())
        score = (front, -err)
        if best is None or score > best[0]:
            best = (score, R_full, t_full)
    return best[1], best[2]


def _pnp_init(X: np.ndarray, uv: np.ndarray, K: np.ndarray):
    """Initial pose for PnP: homography-based for coplanar targets, DLT otherwise."""
    if _coplanar(X):
        return _pnp_planar(X, uv, K)
    return _pnp_dlt(X, uv, K)


def solve_pnp(points3d, uv, K, iters: int = 30, refine: bool = True):
    """Recover object/camera 6-DoF pose ``(R, t)`` from >=6 3-D<->2-D matches.

    Given a known 3-D model (``points3d``, N>=6) and where its points land in the
    image (``uv``) under a calibrated camera (``K``), returns the rotation ``R``
    (3, 3) and translation ``t`` (3,) that map the model into the camera frame
    (``X_cam = R @ X_model + t``). This is the "perspective-n-point" problem — the
    2-D-to-6-DoF step a robot uses to know where a recognised object sits before
    grasping it. DLT initialisation (H&Z §7.1) followed by Gauss-Newton /
    Levenberg-Marquardt refinement of the reprojection error.

    Returns ``(R, t, rms)`` where ``rms`` is the final RMS reprojection error in
    pixels (a small value certifies the fit)."""
    X = _pts3(points3d)
    uv = _pts2(uv)
    K = _K3(K)
    if X.shape[0] != uv.shape[0]:
        raise ValueError("points3d and uv must have the same length")
    if X.shape[0] < 6:
        raise ValueError("PnP needs at least 6 correspondences, got %d" % X.shape[0])
    R0, t0 = _pnp_dlt(X, uv, K)
    if not refine:
        rms = float(np.sqrt(np.mean(reprojection_error(X, uv, K, R0, t0) ** 2)))
        return R0, t0, rms

    xi = np.concatenate([rotation_log(R0), t0])                # (6,)
    lam = 1e-3

    def residual(xi):
        R = rodrigues(xi[:3])
        t = xi[3:]
        proj, _ = project_points(X, K, R, t)
        return (proj - uv).ravel()

    r = residual(xi)
    cost = float(r @ r)
    for _ in range(int(iters)):
        # numeric Jacobian (2N x 6) via forward differences
        J = np.empty((r.size, 6))
        eps = 1e-6
        for j in range(6):
            dxi = xi.copy()
            dxi[j] += eps
            J[:, j] = (residual(dxi) - r) / eps
        H = J.T @ J
        g = J.T @ r
        # Levenberg-Marquardt damped step
        step = np.linalg.solve(H + lam * np.diag(np.diag(H) + 1e-12), -g)
        xi_new = xi + step
        r_new = residual(xi_new)
        cost_new = float(r_new @ r_new)
        if cost_new < cost:
            xi, r, cost, lam = xi_new, r_new, cost_new, max(lam * 0.5, 1e-9)
            if np.linalg.norm(step) < 1e-10:
                break
        else:
            lam = min(lam * 4.0, 1e6)
    R = rodrigues(xi[:3])
    t = xi[3:]
    rms = float(np.sqrt(np.mean(reprojection_error(X, uv, K, R, t) ** 2)))
    return R, t, rms


# --- epipolar geometry ------------------------------------------------------ #
def _normalize_2d(pts: np.ndarray):
    """Hartley isotropic normalization: translate to centroid, scale mean dist to
    sqrt(2). Returns (normalized pts (N,3 homog), transform T (3,3))."""
    c = pts.mean(0)
    d = np.sqrt(((pts - c) ** 2).sum(1)).mean()
    s = np.sqrt(2.0) / d if d > 1e-12 else 1.0
    T = np.array([[s, 0, -s * c[0]], [0, s, -s * c[1]], [0, 0, 1.0]])
    ph = np.hstack([pts, np.ones((pts.shape[0], 1))]) @ T.T
    return ph, T


def fundamental_matrix(uv1, uv2) -> np.ndarray:
    """Fundamental matrix F (3, 3) from >=8 correspondences by the normalized
    eight-point algorithm (Hartley 1997), with the rank-2 constraint enforced.

    F relates matched pixels across two *uncalibrated* views: ``x2^T F x1 = 0``
    for homogeneous pixels ``x1, x2``."""
    a = _pts2(uv1)
    b = _pts2(uv2)
    if a.shape != b.shape or a.shape[0] < 8:
        raise ValueError("need >= 8 equal-count correspondences")
    ah, T1 = _normalize_2d(a)
    bh, T2 = _normalize_2d(b)
    u1, v1 = ah[:, 0], ah[:, 1]
    u2, v2 = bh[:, 0], bh[:, 1]
    A = np.stack([u2 * u1, u2 * v1, u2, v2 * u1, v2 * v1, v2, u1, v1, np.ones_like(u1)], 1)
    _, _, Vt = np.linalg.svd(A)
    F = Vt[-1].reshape(3, 3)
    U, S, Vt2 = np.linalg.svd(F)                # enforce rank 2
    S[2] = 0.0
    F = U @ np.diag(S) @ Vt2
    F = T2.T @ F @ T1                           # denormalize
    return F / (F[2, 2] if abs(F[2, 2]) > 1e-12 else np.linalg.norm(F))


def essential_matrix(uv1, uv2, K, K2=None) -> np.ndarray:
    """Essential matrix E (3, 3) from >=8 correspondences of a *calibrated* pair.

    Normalizes the pixels by ``K`` (and ``K2`` for the second camera, default
    ``K``), runs the eight-point algorithm on the normalized rays, then forces the
    two non-zero singular values equal (the essential-matrix constraint, H&Z §11.7).
    ``x2n^T E x1n = 0`` for normalized rays ``xn = K^-1 x``."""
    a = _pts2(uv1)
    b = _pts2(uv2)
    K = _K3(K)
    K2 = K if K2 is None else _K3(K2)
    Ki1, Ki2 = np.linalg.inv(K), np.linalg.inv(K2)
    an = (np.hstack([a, np.ones((a.shape[0], 1))]) @ Ki1.T)[:, :2]
    bn = (np.hstack([b, np.ones((b.shape[0], 1))]) @ Ki2.T)[:, :2]
    if an.shape[0] < 8:
        raise ValueError("need >= 8 correspondences")
    ah, T1 = _normalize_2d(an)
    bh, T2 = _normalize_2d(bn)
    u1, v1 = ah[:, 0], ah[:, 1]
    u2, v2 = bh[:, 0], bh[:, 1]
    A = np.stack([u2 * u1, u2 * v1, u2, v2 * u1, v2 * v1, v2, u1, v1, np.ones_like(u1)], 1)
    _, _, Vt = np.linalg.svd(A)
    E = Vt[-1].reshape(3, 3)
    E = T2.T @ E @ T1
    U, S, Vt2 = np.linalg.svd(E)
    s = (S[0] + S[1]) / 2.0
    E = U @ np.diag([s, s, 0.0]) @ Vt2
    return E


def essential_from_fundamental(F, K, K2=None) -> np.ndarray:
    """``E = K2^T @ F @ K`` — convert a fundamental matrix to essential given the
    intrinsics of both cameras (``K2`` defaults to ``K``)."""
    F = np.asarray(F, np.float64)
    K = _K3(K)
    K2 = K if K2 is None else _K3(K2)
    return K2.T @ F @ K


def decompose_essential(E):
    """Factor an essential matrix into the four possible relative poses (H&Z §9.6.2).

    Returns ``(R1, R2, t)``: the two rotation candidates and a unit translation
    direction. The physical pose is one of ``(R1, +t), (R1, -t), (R2, +t),
    (R2, -t)`` — :func:`recover_pose` picks it by cheirality."""
    E = np.asarray(E, np.float64)
    U, _, Vt = np.linalg.svd(E)
    if np.linalg.det(U) < 0:
        U = -U
    if np.linalg.det(Vt) < 0:
        Vt = -Vt
    W = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    R1 = U @ W @ Vt
    R2 = U @ W.T @ Vt
    t = U[:, 2]
    return R1, R2, t / max(np.linalg.norm(t), 1e-12)


def recover_pose(E, uv1, uv2, K, K2=None):
    """Select the physically valid relative pose from an essential matrix.

    Tries all four ``decompose_essential`` candidates, triangulates the
    correspondences for each, and returns the ``(R, t, mask)`` under which the most
    points lie in front of both cameras (cheirality, H&Z §9.6.3). ``R, t`` map the
    first camera frame to the second (``X2 = R @ X1 + t``); ``mask`` marks the
    triangulated points that are in front of both."""
    a = _pts2(uv1)
    b = _pts2(uv2)
    K = _K3(K)
    K2 = K if K2 is None else _K3(K2)
    R1, R2, t = decompose_essential(E)
    P1 = projection_matrix(K)                                  # [I | 0]
    best = None
    for R in (R1, R2):
        for sign in (1.0, -1.0):
            tt = sign * t
            P2 = projection_matrix(K2, R, tt)
            X = triangulate(a, b, P1, P2)
            z1 = X[:, 2]
            z2 = (X @ R.T + tt)[:, 2]
            infront = (z1 > 0) & (z2 > 0)
            n = int(infront.sum())
            if best is None or n > best[0]:
                best = (n, R, tt, infront)
    return best[1], best[2], best[3]


def epipolar_lines(F, uv, which: int = 2) -> np.ndarray:
    """Epipolar lines induced by points through a fundamental matrix.

    ``which=2`` (default): lines ``l2 = F @ x1`` in image 2 for points ``uv`` in
    image 1. ``which=1``: lines ``l1 = F^T @ x2`` in image 1 for points in image 2.
    Each returned row ``[a, b, c]`` is the line ``a*u + b*v + c = 0``, normalized so
    ``a^2 + b^2 = 1``."""
    F = np.asarray(F, np.float64)
    p = _pts2(uv)
    xh = np.hstack([p, np.ones((p.shape[0], 1))])
    M = F if which == 2 else F.T
    lines = xh @ M.T
    nrm = np.sqrt(lines[:, 0] ** 2 + lines[:, 1] ** 2)
    return lines / np.where(nrm[:, None] < 1e-12, 1.0, nrm[:, None])


# --- lens distortion (Brown-Conrady) ---------------------------------------- #
def _dist_coeffs(dist):
    """Accept [k1,k2,p1,p2(,k3)] (OpenCV order) -> (k1,k2,k3,p1,p2)."""
    d = np.asarray(dist, np.float64).ravel()
    if d.size == 4:
        k1, k2, p1, p2 = d
        k3 = 0.0
    elif d.size == 5:
        k1, k2, p1, p2, k3 = d
    else:
        raise ValueError("dist must be [k1,k2,p1,p2] or [k1,k2,p1,p2,k3]")
    return k1, k2, k3, p1, p2


def distort_points(uv, K, dist) -> np.ndarray:
    """Apply radial-tangential lens distortion to ideal pixels (Brown 1971).

    Forward model: ideal pinhole pixels ``uv`` -> where they actually land on a
    distorted image. ``dist = [k1, k2, p1, p2(, k3)]`` (OpenCV order). Inverse of
    :func:`undistort_points`."""
    uv = _pts2(uv)
    K = _K3(K)
    k1, k2, k3, p1, p2 = _dist_coeffs(dist)
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
    x = (uv[:, 0] - cx) / fx
    y = (uv[:, 1] - cy) / fy
    r2 = x * x + y * y
    radial = 1.0 + k1 * r2 + k2 * r2 ** 2 + k3 * r2 ** 3
    dx = 2 * p1 * x * y + p2 * (r2 + 2 * x * x)
    dy = p1 * (r2 + 2 * y * y) + 2 * p2 * x * y
    xd = x * radial + dx
    yd = y * radial + dy
    return np.stack([fx * xd + cx, fy * yd + cy], 1)


def undistort_points(uv, K, dist, iters: int = 10) -> np.ndarray:
    """Remove radial-tangential distortion — the inverse of :func:`distort_points`.

    Solves the non-linear forward model by fixed-point iteration in normalized
    coordinates (the standard OpenCV approach). Returns ideal pinhole pixels."""
    uv = _pts2(uv)
    K = _K3(K)
    k1, k2, k3, p1, p2 = _dist_coeffs(dist)
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
    xd = (uv[:, 0] - cx) / fx
    yd = (uv[:, 1] - cy) / fy
    x, y = xd.copy(), yd.copy()
    for _ in range(int(iters)):
        r2 = x * x + y * y
        radial = 1.0 + k1 * r2 + k2 * r2 ** 2 + k3 * r2 ** 3
        dx = 2 * p1 * x * y + p2 * (r2 + 2 * x * x)
        dy = p1 * (r2 + 2 * y * y) + 2 * p2 * x * y
        x = (xd - dx) / radial
        y = (yd - dy) / radial
    return np.stack([fx * x + cx, fy * y + cy], 1)


# --- calibrated stereo rectification (Fusiello et al. 2000) ----------------- #
def stereo_rectify(K1, K2, R, t):
    """Compute rectifying rotations for a calibrated stereo pair (Fusiello 2000).

    Given the two intrinsics and the relative pose of the second camera in the
    first camera's frame (``X2 = R @ X1 + t``), returns
    ``(R_rect1, R_rect2, K_new)`` — the rotations that turn each camera so their
    image planes are coplanar with a common horizontal baseline, plus the shared
    intrinsic matrix. Warp each image by the homography ``H_i = K_new @ R_recti @
    K_i^-1`` and the pair becomes row-aligned, so :func:`stereo.disparity_map` (which
    assumes rectified input) applies. For an already-rectified pair (``R = I``,
    ``t`` along -x) the rotations come back ~identity."""
    K1 = _K3(K1)
    K2 = _K3(K2)
    R = np.asarray(R, np.float64)
    t = np.asarray(t, np.float64).ravel()
    if R.shape != (3, 3) or t.size != 3:
        raise ValueError("R must be 3x3 and t length-3")
    # optical centres in the first camera's frame: c1 = 0, c2 = -R^T t
    c2 = -R.T @ t
    # new x-axis: the baseline direction (from cam1 to cam2)
    v1 = c2
    if np.linalg.norm(v1) < 1e-12:
        raise ValueError("degenerate baseline (cameras coincide)")
    v1 = v1 / np.linalg.norm(v1)
    # new y-axis: orthogonal to new-x and the *old* left optical axis z=[0,0,1]
    oldz = np.array([0.0, 0.0, 1.0])
    v2 = np.cross(oldz, v1)
    if np.linalg.norm(v2) < 1e-12:                 # baseline parallel to optical axis
        v2 = np.cross(np.array([0.0, 1.0, 0.0]), v1)
    v2 = v2 / np.linalg.norm(v2)
    v3 = np.cross(v1, v2)
    Rn = np.stack([v1, v2, v3])                    # world(cam1)-> rectified rows
    # rectifying rotation applied to each camera frame
    R_rect1 = Rn                                   # cam1 old frame is the reference
    R_rect2 = Rn @ R.T                             # map cam2 frame -> rectified
    Knew = (K1 + K2) / 2.0
    Knew[0, 1] = 0.0                               # drop skew in the rectified rig
    return R_rect1, R_rect2, Knew
