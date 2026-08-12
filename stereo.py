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

__all__ = ["disparity_map", "depth_from_disparity", "reproject_to_points"]


def _shift_right_cols(R: np.ndarray, d: int) -> np.ndarray:
    """Return ``Rd`` with ``Rd[y, x] = R[y, x - d]`` (edge-replicated on the left)."""
    if d == 0:
        return R
    Rd = np.empty_like(R)
    Rd[:, d:] = R[:, :-d]
    Rd[:, :d] = R[:, :1]
    return Rd


def disparity_map(left, right, max_disp: int = 16, block: int = 7,
                  method: str = "sad") -> np.ndarray:
    """Dense disparity by winner-take-all block matching.

    Parameters
    ----------
    left, right : (H, W) float arrays in [0, 1], rectified, same shape.
    max_disp    : largest disparity searched (0..max_disp inclusive).
    block       : matching window side (odd).
    method      : 'sad' (default), 'ssd', or 'ncc' (zero-mean normalized).

    Returns the per-pixel disparity (float, 0..max_disp). Left-border columns
    that never have full overlap are left at their best in-range match.
    """
    L = np.asarray(left, np.float64)
    R = np.asarray(right, np.float64)
    if L.shape != R.shape or L.ndim != 2:
        raise ValueError("left/right must be equal-shape 2-D arrays")
    H, W = L.shape
    k = int(block)

    def box(a):
        return ndimage.uniform_filter(a, k, mode="nearest")

    best_cost = np.full((H, W), np.inf)
    best_disp = np.zeros((H, W))
    if method == "ncc":
        mL = box(L)
        lz = L - mL
        el = box(lz * lz)
    for d in range(0, int(max_disp) + 1):
        Rd = _shift_right_cols(R, d)
        if method == "sad":
            cost = box(np.abs(L - Rd))
        elif method == "ssd":
            cost = box((L - Rd) ** 2)
        elif method == "ncc":
            rz = Rd - box(Rd)
            den = np.sqrt(np.maximum(el * box(rz * rz), 1e-12))
            cost = 1.0 - box(lz * rz) / den          # 1 - NCC: 0 = perfect match
        else:
            raise ValueError("method must be sad|ssd|ncc, got %r" % method)
        upd = cost < best_cost
        best_cost[upd] = cost[upd]
        best_disp[upd] = d
    return best_disp


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
