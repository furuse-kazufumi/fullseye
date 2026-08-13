"""Optical flow — dense two-frame motion (numpy + scipy only).

This adds the *temporal* axis to the perception stack. Where stereo turns two
*spatial* views into depth, optical flow turns two *time* frames into per-pixel
motion — the signal for validating physics in rendered video (onocollo), reading
limb motion for a body-language model (evis / hillco), and cueing events such as
contact, slip, or impact.

Two classical dense estimators are provided so a result can be cross-checked:

* **Lucas-Kanade** (local): windowed least-squares on the brightness-constancy
  gradient constraint, run coarse-to-fine over a Gaussian pyramid so motions
  larger than a pixel are recovered.
* **Horn-Schunck** (global): brightness constancy plus a global smoothness prior,
  solved by Jacobi iteration.

Convention: ``prev`` and ``nxt`` are equal-shape grayscale images in ``[0, 1]``.
The flow ``(u, v)`` is defined so that a feature at ``(x, y)`` in ``prev`` moves
to ``(x + u, y + v)`` in ``nxt`` — equivalently ``nxt[y, x] ≈ prev[y - v, x - u]``.
``u`` is the horizontal (column) motion, ``v`` the vertical (row) motion.

Reference: Lucas & Kanade 1981; Horn & Schunck, "Determining Optical Flow",
Artificial Intelligence 1981; Bouguet, "Pyramidal Implementation of the
Lucas-Kanade Feature Tracker", 2001 (public literature — reimplemented, not
derived from any product).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

__all__ = [
    "optical_flow_lk", "optical_flow_hs", "warp_by_flow",
    "flow_magnitude", "flow_angle",
]


def _box(a: np.ndarray, k: int) -> np.ndarray:
    return ndimage.uniform_filter(a, int(k), mode="nearest")


def _remap(img: np.ndarray, mapx: np.ndarray, mapy: np.ndarray) -> np.ndarray:
    """Bilinear sample: ``out[y, x] = img[mapy[y, x], mapx[y, x]]`` (edge-clamped)."""
    return ndimage.map_coordinates(img, [mapy, mapx], order=1, mode="nearest")


def _pyr_down(a: np.ndarray) -> np.ndarray:
    """Anti-aliased half-resolution copy."""
    return ndimage.gaussian_filter(a, 1.0, mode="nearest")[::2, ::2]


def optical_flow_lk(prev, nxt, window: int = 15, levels: int = 3,
                    iters: int = 4, reg: float = 1e-3):
    """Dense pyramidal Lucas-Kanade flow.

    Parameters
    ----------
    prev, nxt : (H, W) float arrays in [0, 1], equal shape.
    window    : side of the least-squares aggregation window (odd).
    levels    : Gaussian-pyramid levels (coarse-to-fine); >1 recovers multi-pixel
                motion. Auto-capped when the image gets too small.
    iters     : refinement iterations per level.
    reg       : Tikhonov term added to the structure-tensor diagonal so flat,
                aperture-ambiguous regions resolve to zero flow instead of blowing up.

    Returns ``(u, v)`` float arrays of shape (H, W): ``u`` = horizontal motion,
    ``v`` = vertical motion, in pixels of the full-resolution frame.
    """
    P = np.asarray(prev, np.float64)
    N = np.asarray(nxt, np.float64)
    if P.shape != N.shape or P.ndim != 2:
        raise ValueError("prev/nxt must be equal-shape 2-D arrays")
    k = max(3, int(window))

    pyrP = [P]
    pyrN = [N]
    for _ in range(max(1, int(levels)) - 1):
        if min(pyrP[-1].shape) < 16:          # stop before the window outgrows the level
            break
        pyrP.append(_pyr_down(pyrP[-1]))
        pyrN.append(_pyr_down(pyrN[-1]))

    u = np.zeros_like(pyrP[-1])
    v = np.zeros_like(pyrP[-1])
    for lvl in range(len(pyrP) - 1, -1, -1):
        p = pyrP[lvl]
        n = pyrN[lvl]
        H, W = p.shape
        if u.shape != p.shape:                # prolong the flow into this finer level
            # _pyr_down decimates by 2, so a coarse pixel of displacement is 2 fine
            # pixels: rescale the field to the finer grid and double its magnitude.
            u = ndimage.zoom(u, (H / u.shape[0], W / u.shape[1]), order=1) * 2.0
            v = ndimage.zoom(v, (H / v.shape[0], W / v.shape[1]), order=1) * 2.0
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
        Iy, Ix = np.gradient(p)               # template (prev) gradients — constant per level
        Ixx0 = _box(Ix * Ix, k)
        Iyy0 = _box(Iy * Iy, k)
        Ixy = _box(Ix * Iy, k)
        # Tikhonov term as a fraction of the level's mean gradient energy, so the
        # solve is invariant to a common intensity scale of the two frames (a
        # constant `reg` would over-damp low-contrast pairs — the [0,1] range).
        lam = reg * float(Ixx0.mean() + Iyy0.mean()) + 1e-20
        Ixx = Ixx0 + lam
        Iyy = Iyy0 + lam
        det = Ixx * Iyy - Ixy * Ixy
        for _ in range(max(1, int(iters))):
            warped = _remap(n, xx + u, yy + v)   # align nxt onto prev with current flow
            It = warped - p
            Ixt = _box(Ix * It, k)
            Iyt = _box(Iy * It, k)
            # solve [[Ixx,Ixy],[Ixy,Iyy]] [du,dv]^T = [-Ixt,-Iyt]
            du = (-Iyy * Ixt + Ixy * Iyt) / det
            dv = (Ixy * Ixt - Ixx * Iyt) / det
            # freeze pixels whose sample already left the frame: there the warp is
            # edge-clamped so dIt/dflow = 0 and the solve would push them out forever.
            inb = (xx + u >= 0) & (xx + u <= W - 1) & (yy + v >= 0) & (yy + v <= H - 1)
            du = np.where(inb, du, 0.0)
            dv = np.where(inb, dv, 0.0)
            # clamp the step so the fixed-template Gauss-Newton stays contractive
            # (its box-averaged Hessian can have gain > 1 at high-gradient pixels).
            np.clip(du, -1.0, 1.0, out=du)
            np.clip(dv, -1.0, 1.0, out=dv)
            u = u + du
            v = v + dv
            if max(float(np.abs(du).max()), float(np.abs(dv).max())) < 1e-3:
                break
    return u, v


def optical_flow_hs(prev, nxt, alpha: float = 1.0, iters: int = 100):
    """Dense Horn-Schunck flow (global smoothness, Jacobi iteration).

    *alpha* weights the smoothness prior (larger = smoother/blurrier flow). Best
    for small motions; pair with :func:`optical_flow_lk` (which handles large
    displacement) when cross-checking. Returns ``(u, v)`` like :func:`optical_flow_lk`.
    """
    P = np.asarray(prev, np.float64)
    N = np.asarray(nxt, np.float64)
    if P.shape != N.shape or P.ndim != 2:
        raise ValueError("prev/nxt must be equal-shape 2-D arrays")
    Iy, Ix = np.gradient((P + N) * 0.5)
    It = N - P
    u = np.zeros_like(P)
    v = np.zeros_like(P)
    avg = np.array([[1 / 12, 1 / 6, 1 / 12],
                    [1 / 6, 0.0, 1 / 6],
                    [1 / 12, 1 / 6, 1 / 12]])
    a2 = float(alpha) ** 2
    den = a2 + Ix * Ix + Iy * Iy
    for _ in range(max(1, int(iters))):
        ub = ndimage.convolve(u, avg, mode="nearest")
        vb = ndimage.convolve(v, avg, mode="nearest")
        t = (Ix * ub + Iy * vb + It) / den
        u = ub - Ix * t
        v = vb - Iy * t
    return u, v


def warp_by_flow(img, u, v):
    """Warp *img* forward by the flow: ``out[y, x] = img[y - v, x - u]``.

    Warping ``prev`` by its flow to ``nxt`` reconstructs ``nxt`` — the standard
    way to *check* a flow estimate (residual vs. ``nxt`` should shrink)."""
    a = np.asarray(img, np.float64)
    H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    U = np.asarray(u, np.float64)
    V = np.asarray(v, np.float64)
    if a.ndim == 3:
        return np.stack([_remap(a[..., c], xx - U, yy - V) for c in range(a.shape[2])], axis=-1)
    return _remap(a, xx - U, yy - V)


def flow_magnitude(u, v) -> np.ndarray:
    """Per-pixel speed ``sqrt(u^2 + v^2)``."""
    return np.hypot(np.asarray(u, np.float64), np.asarray(v, np.float64))


def flow_angle(u, v) -> np.ndarray:
    """Per-pixel motion direction ``atan2(v, u)`` in radians, range (-pi, pi]."""
    return np.arctan2(np.asarray(v, np.float64), np.asarray(u, np.float64))
