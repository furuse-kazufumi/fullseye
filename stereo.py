"""Stereo depth building blocks (numpy + scipy only).

Dense two-frame stereo by fronto-parallel block matching — the first piece of a
perception stack that turns two views into depth, and depth into a terrain
heightmap / point cloud for locomotion and grasping. It builds on the same
windowed normalized-correlation idea as the (now-correct) NCC template operator,
and on the geometric-transform ops used for rectification.

Convention: `left` and `right` are **rectified** grayscale images of equal shape
with horizontal epipolar lines, and a scene feature at left column ``c`` appears
in the right image at column ``c - d`` for disparity ``d >= 0`` (nearer surfaces
-> larger ``d``). Depth follows ``Z = focal * baseline / d``.

Reference: Scharstein & Szeliski, "A Taxonomy and Evaluation of Dense Two-Frame
Stereo Correspondence Algorithms", IJCV 2002 (public literature — reimplemented,
not derived from any product).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

__all__ = ["disparity_map", "disparity_subpixel", "lr_consistency",
           "depth_from_disparity", "reproject_to_points"]


def _shift_right_cols(R: np.ndarray, d: int) -> np.ndarray:
    """Return ``Rd`` with ``Rd[y, x] = R[y, x - d]`` (edge-replicated on the left)."""
    if d == 0:
        return R
    Rd = np.empty_like(R)
    Rd[:, d:] = R[:, :-d]
    Rd[:, :d] = R[:, :1]
    return Rd


def _cost_volume(L: np.ndarray, R: np.ndarray, max_disp: int, block: int,
                 method: str) -> np.ndarray:
    """Per-disparity matching cost volume ``vol[d, y, x]`` (lower = better).

    The same windowed SAD/SSD/(1-NCC) cost the winner-take-all matcher argmin's
    over — sharing it lets the sub-pixel refiner read the cost curvature."""
    H, W = L.shape
    k = int(block)

    def box(a):
        return ndimage.uniform_filter(a, k, mode="nearest")

    D = int(max_disp)
    vol = np.empty((D + 1, H, W), np.float64)
    if method == "ncc":
        lz = L - box(L)
        el = box(lz * lz)
    for d in range(0, D + 1):
        Rd = _shift_right_cols(R, d)
        if method == "sad":
            vol[d] = box(np.abs(L - Rd))
        elif method == "ssd":
            vol[d] = box((L - Rd) ** 2)
        elif method == "ncc":
            rz = Rd - box(Rd)
            den = np.sqrt(np.maximum(el * box(rz * rz), 1e-12))
            vol[d] = 1.0 - box(lz * rz) / den          # 1 - NCC: 0 = perfect match
        else:
            raise ValueError("method must be sad|ssd|ncc, got %r" % method)
    return vol


def disparity_map(left, right, max_disp: int = 16, block: int = 7,
                  method: str = "sad", reference: str = "left") -> np.ndarray:
    """Dense disparity by winner-take-all block matching.

    Parameters
    ----------
    left, right : (H, W) float arrays in [0, 1], rectified, same shape.
    max_disp    : largest disparity searched (0..max_disp inclusive).
    block       : matching window side (odd).
    method      : 'sad' (default), 'ssd', or 'ncc' (zero-mean normalized).
    reference   : 'left' (default) indexes the map by left-image columns; 'right'
                  indexes it by right-image columns (the map needed for a
                  left-right consistency check — see :func:`lr_consistency`).

    Returns the per-pixel disparity (float, 0..max_disp). Border columns that
    never have full overlap are left at their best in-range match.
    """
    L = np.asarray(left, np.float64)
    R = np.asarray(right, np.float64)
    if L.shape != R.shape or L.ndim != 2:
        raise ValueError("left/right must be equal-shape 2-D arrays")
    if reference == "right":
        # right-referenced disparity via the standard mirror identity:
        # flip both, swap roles, run the left matcher, flip the result back.
        d = disparity_map(R[:, ::-1], L[:, ::-1], max_disp, block, method, "left")
        return d[:, ::-1]
    if reference != "left":
        raise ValueError("reference must be 'left' or 'right', got %r" % reference)
    return _cost_volume(L, R, max_disp, block, method).argmin(0).astype(np.float64)


def disparity_subpixel(left, right, max_disp: int = 16, block: int = 7,
                       method: str = "ssd") -> np.ndarray:
    """Disparity refined to sub-pixel precision by a parabola fit.

    Fits ``a·x² + b·x + c`` through the winning cost and its two neighbours and
    takes the parabola's vertex, so a surface whose true disparity is 5.4 reads
    ~5.4 instead of snapping to the integer 5. 'ssd'/'ncc' give a smoother cost
    curve than 'sad' and refine more accurately. Pixels whose winner sits at the
    search-range border keep their integer disparity."""
    L = np.asarray(left, np.float64)
    R = np.asarray(right, np.float64)
    if L.shape != R.shape or L.ndim != 2:
        raise ValueError("left/right must be equal-shape 2-D arrays")
    vol = _cost_volume(L, R, max_disp, block, method)
    D = vol.shape[0]
    d = vol.argmin(0)
    dm = np.clip(d - 1, 0, D - 1)[None]
    dp = np.clip(d + 1, 0, D - 1)[None]
    c0 = np.take_along_axis(vol, d[None], 0)[0]
    cm = np.take_along_axis(vol, dm, 0)[0]
    cp = np.take_along_axis(vol, dp, 0)[0]
    denom = cm - 2.0 * c0 + cp                      # >0 at a convex minimum
    offset = np.where(denom > 1e-12, 0.5 * (cm - cp) / denom, 0.0)
    offset = np.clip(offset, -0.5, 0.5)
    interior = (d > 0) & (d < D - 1)
    return d.astype(np.float64) + np.where(interior, offset, 0.0)


def lr_consistency(disp_left, disp_right, max_diff: float = 1.0):
    """Left-right consistency mask (True = disparity is trustworthy).

    A correct left disparity ``dL`` at column ``x`` should be echoed by the
    right-referenced map at the matched column ``x - dL``. Where the two disagree
    by more than *max_diff* the pixel is an occlusion or a mismatch and should be
    dropped. Pass the ``reference='left'`` and ``reference='right'`` disparity
    maps of the same pair."""
    dL = np.asarray(disp_left, np.float64)
    dR = np.asarray(disp_right, np.float64)
    if dL.shape != dR.shape or dL.ndim != 2:
        raise ValueError("disparity maps must be equal-shape 2-D arrays")
    W = dL.shape[1]
    xx = np.arange(W)[None, :]
    xr_raw = np.round(xx - dL).astype(int)
    # a matched column outside [0, W) has no correspondence to check -> not
    # trustworthy (clamping it to column 0 would fabricate an agreement on the
    # left overlap-free margin, which is exactly what this check must reject).
    valid = (xr_raw >= 0) & (xr_raw < W)
    xr = np.clip(xr_raw, 0, W - 1)
    dR_at = np.take_along_axis(dR, xr, axis=1)
    return valid & (np.abs(dL - dR_at) <= float(max_diff))


def depth_from_disparity(disp, focal: float = 1.0, baseline: float = 1.0,
                         min_disp: float = 1e-6) -> np.ndarray:
    """Metric depth ``Z = focal * baseline / disparity``.

    Pixels with ``disparity <= min_disp`` (no measurable parallax -> infinitely
    far / unmatched) are returned as ``inf``.
    """
    d = np.asarray(disp, np.float64)
    z = np.full_like(d, np.inf)
    m = d > min_disp
    z[m] = float(focal) * float(baseline) / d[m]
    return z


def reproject_to_points(depth, fx: float = 1.0, fy: float = 1.0,
                        cx: float | None = None, cy: float | None = None):
    """Back-project a depth map to a camera-frame point cloud (N, 3) of finite
    points. Pinhole model: X = (u-cx)*Z/fx, Y = (v-cy)*Z/fy, Z = depth."""
    Z = np.asarray(depth, np.float64)
    H, W = Z.shape
    cx = (W - 1) / 2.0 if cx is None else cx
    cy = (H - 1) / 2.0 if cy is None else cy
    v, u = np.mgrid[0:H, 0:W]
    finite = np.isfinite(Z)
    zz = Z[finite]
    xx = (u[finite] - cx) * zz / float(fx)
    yy = (v[finite] - cy) * zz / float(fy)
    return np.stack([xx, yy, zz], axis=1)
