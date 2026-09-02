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
    "flow_magnitude", "flow_angle", "track_points",
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
    if min(P.shape) < 2:
        raise ValueError("prev/nxt must be at least 2x2 (need a spatial gradient)")
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
        prev_res = np.inf
        u_prev, v_prev = u.copy(), v.copy()
        for _ in range(max(1, int(iters))):
            warped = _remap(n, xx + u, yy + v)   # align nxt onto prev with current flow
            It = warped - p
            # monotonic-residual guard: the fixed-template iteration is not
            # globally contractive, so stop (and undo the last step) once the
            # aggregate residual stops falling instead of letting it diverge.
            res = float(np.mean(It * It))
            if res >= prev_res:
                u, v = u_prev, v_prev
                break
            prev_res = res
            u_prev, v_prev = u.copy(), v.copy()
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
            # clamp the per-step magnitude so a single high-gradient pixel cannot
            # overshoot (its box-averaged Hessian can have gain > 1).
            np.clip(du, -1.0, 1.0, out=du)
            np.clip(dv, -1.0, 1.0, out=dv)
            u = u + du
            v = v + dv
    return u, v


_HS_AVG = np.array([[1 / 12, 1 / 6, 1 / 12],
                    [1 / 6, 0.0, 1 / 6],
                    [1 / 12, 1 / 6, 1 / 12]])


def _hs_solve(Ix, Iy, It, u, v, a2: float, iters: int, tol: float):
    """Jacobi iteration of the Horn-Schunck normal equations from the start ``(u, v)``.

    Solves ``Ix*u + Iy*v + It = 0`` under the global smoothness prior ``a2`` until
    the largest per-pixel update falls below *tol* (or *iters* sweeps). Returns
    ``(u, v, sweeps)`` — the count lets a caller see whether it converged."""
    # floor the denominator so a flat region with alpha=0 gives 0 flow, not 0/0=NaN
    den = np.maximum(a2 + Ix * Ix + Iy * Iy, 1e-12)
    n = 0
    for n in range(1, max(1, int(iters)) + 1):
        ub = ndimage.convolve(u, _HS_AVG, mode="nearest")
        vb = ndimage.convolve(v, _HS_AVG, mode="nearest")
        t = (Ix * ub + Iy * vb + It) / den
        un = ub - Ix * t
        vn = vb - Iy * t
        delta = max(float(np.abs(un - u).max()), float(np.abs(vn - v).max()))
        u, v = un, vn
        if delta < tol:
            break
    return u, v, n


def optical_flow_hs(prev, nxt, alpha: float = 1.0, iters: int = 2000,
                    tol: float = 1e-4, levels: int = 3, warps: int = 3):
    """Dense Horn-Schunck flow (global smoothness) — iterated to convergence,
    coarse-to-fine, with re-linearisation (warping) between passes.

    The classical scheme is a single Jacobi sweep budget on one linearisation
    of brightness constancy. That has two failure modes this version removes:

    * **Truncated Jacobi.** Jacobi diffuses the data term across the image one
      pixel per sweep, so a fixed budget of ~100 sweeps returns only ~20 % of a
      1-px translation on a 100-px frame (measured 2026-09-02: 0.27 px at 100
      sweeps, 0.64 at 300, 1.1 at 1000). Each pass now iterates until the
      largest per-pixel update is below *tol* (or *iters* sweeps), and the
      solve starts from a coarse level of a Gaussian pyramid (*levels*) so the
      smooth component converges in few sweeps.
    * **Fixed linearisation.** The gradient constraint is only first-order, so
      even the fully converged one-shot solution over/under-shoots (1.2 px for a
      true 1 px, 2.7 px for 2 px). Each pass (*warps*) re-warps *nxt* by the
      current flow and re-linearises about it, which drives a translation to
      its true value.

    Expected accuracy on band-limited texture: a uniform translation of a few
    pixels is recovered to within ~5 % in the interior (the border band of
    roughly one pyramid-level window stays biased by edge clamping); flows
    larger than ~4 px per level rely on the pyramid, as in
    :func:`optical_flow_lk`. *alpha* weights the smoothness prior (larger =
    smoother/blurrier flow). Returns ``(u, v)`` like :func:`optical_flow_lk`.
    """
    P = np.asarray(prev, np.float64)
    N = np.asarray(nxt, np.float64)
    if P.shape != N.shape or P.ndim != 2:
        raise ValueError("prev/nxt must be equal-shape 2-D arrays")
    if min(P.shape) < 2:
        raise ValueError("prev/nxt must be at least 2x2 (need a spatial gradient)")
    a2 = float(alpha) ** 2
    pyrP = [P]
    pyrN = [N]
    for _ in range(max(1, int(levels)) - 1):
        if min(pyrP[-1].shape) < 16:
            break
        pyrP.append(_pyr_down(pyrP[-1]))
        pyrN.append(_pyr_down(pyrN[-1]))
    u = np.zeros_like(pyrP[-1])
    v = np.zeros_like(pyrP[-1])
    for lvl in range(len(pyrP) - 1, -1, -1):
        p = pyrP[lvl]
        n = pyrN[lvl]
        H, W = p.shape
        if u.shape != p.shape:                # prolong: 2x grid, 2x magnitude
            u = ndimage.zoom(u, (H / u.shape[0], W / u.shape[1]), order=1) * 2.0
            v = ndimage.zoom(v, (H / v.shape[0], W / v.shape[1]), order=1) * 2.0
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
        for _ in range(max(1, int(warps))):
            warped = _remap(n, xx + u, yy + v)   # nxt brought onto prev by the current flow
            Iy, Ix = np.gradient((p + warped) * 0.5)
            # linearise about the current flow (u0, v0): Ix*u + Iy*v + It' = 0 with
            # It' = (warped - prev) - Ix*u0 - Iy*v0, so the solve is for the TOTAL flow
            It = (warped - p) - Ix * u - Iy * v
            u, v, _ = _hs_solve(Ix, Iy, It, u, v, a2, iters, tol)
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


def track_points(prev, nxt, points, **flow_kwargs):
    """Track sparse points from *prev* to *nxt* (a Lucas-Kanade point tracker).

    *points* is (N, 2) as ``(x, y)`` pixel coordinates. Returns ``(tracked, ok)``:
    the (N, 2) positions in *nxt* and a boolean mask that is False where a point
    left the frame. Positions come from bilinearly sampling the dense
    :func:`optical_flow_lk` field, so *flow_kwargs* (``window``/``levels``/``iters``)
    tune the underlying estimate. Use it to follow a marker on a limb (evis/hillco)
    or an object across a video (onocollo)."""
    u, v = optical_flow_lk(prev, nxt, **flow_kwargs)
    pts = np.asarray(points, np.float64).reshape(-1, 2)
    xs, ys = pts[:, 0], pts[:, 1]
    du = ndimage.map_coordinates(u, [ys, xs], order=1, mode="nearest")
    dv = ndimage.map_coordinates(v, [ys, xs], order=1, mode="nearest")
    tracked = pts + np.stack([du, dv], axis=1)
    H, W = np.asarray(prev).shape[:2]
    ok = ((tracked[:, 0] >= 0) & (tracked[:, 0] <= W - 1)
          & (tracked[:, 1] >= 0) & (tracked[:, 1] <= H - 1))
    return tracked, ok
