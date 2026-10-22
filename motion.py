"""Motion analysis on top of dense optical flow (numpy + scipy only).

Where :mod:`flow` *estimates* the per-pixel motion between two frames, this module
*interprets* it: measure how much moved (event cueing over a clip), fit and remove
the global/camera motion, and segment the independently-moving regions that remain.
For onocollo physics videos this separates "the whole scene drifted" from "that
object moved"; for evis / hillco it isolates a moving limb from background sway.

Convention matches :mod:`flow`: ``u`` is horizontal, ``v`` vertical motion (pixels).
A global affine motion model is ``[u; v] = M · [1; x; y]`` with ``M`` shape (2, 3).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

__all__ = [
    "frame_motion_energy", "dominant_motion", "flow_from_model",
    "residual_motion", "motion_segments", "motion_energy_series", "detect_events",
]


def motion_energy_series(frames, **flow_kwargs) -> np.ndarray:
    """Per-adjacent-pair motion energy across a frame sequence.

    Returns a 1-D array of length ``len(frames) - 1``; its peaks flag events
    (contact, impact, a sudden move) over a clip. *flow_kwargs* pass through to
    :func:`flow.optical_flow_lk` (e.g. ``levels``, ``window``)."""
    iterator = iter(frames)
    try:
        previous = np.asarray(next(iterator), np.float64)
    except StopIteration:
        return np.zeros(0)
    import flow
    energies = []
    for frame in iterator:
        current = np.asarray(frame, np.float64)
        energies.append(frame_motion_energy(
            *flow.optical_flow_lk(previous, current, **flow_kwargs)))
        previous = current
    return np.asarray(energies)


def detect_events(energy, threshold=None, k: float = 2.0) -> np.ndarray:
    """Indices of motion-energy spikes in a per-frame-pair energy signal.

    Returns the local maxima that exceed *threshold* (default ``mean + k*std`` of
    the signal) — the frame-pair indices at which an event occurred."""
    e = np.asarray(energy, np.float64)
    if e.size == 0:
        return np.zeros(0, dtype=int)
    thr = float(e.mean() + float(k) * e.std()) if threshold is None else float(threshold)
    left = np.empty_like(e)
    right = np.empty_like(e)
    left[0], left[1:] = -np.inf, e[:-1]
    right[-1], right[:-1] = -np.inf, e[1:]
    return np.flatnonzero((e > thr) & (e >= left) & (e >= right))


def frame_motion_energy(u, v) -> float:
    """RMS speed over the field — one scalar per frame pair. Tracking this across
    a clip gives a motion-energy signal whose peaks cue events (impact, contact,
    a sudden move)."""
    u = np.asarray(u, np.float64)
    v = np.asarray(v, np.float64)
    return float(np.sqrt(np.mean(u * u + v * v)))


def dominant_motion(u, v, robust: bool = True, trim: float = 0.25,
                    iters: int = 3, method: str = "exact") -> np.ndarray:
    """Fit the global affine motion ``[u; v] = M · [1, x, y]`` by least squares.

    This is the camera / whole-scene motion. With *robust* (default) the highest-
    residual pixels — the independently moving foreground — are trimmed and the
    model re-fit, so a moving object does not bias the global estimate. Returns
    ``M`` of shape (2, 3): row 0 = (c, ∂u/∂x, ∂u/∂y), row 1 the same for ``v``.
    ``method="exact"`` keeps the established two-solve rounding. ``"fast"``
    solves both right-hand sides together; its measured maximum absolute
    difference is 4.66e-10 on a 1e6-offset, tiny-variance stress field."""
    u = np.asarray(u, np.float64)
    v = np.asarray(v, np.float64)
    H, W = u.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    A = np.stack([np.ones(H * W), xx.ravel(), yy.ravel()], axis=1)
    bu, bv = u.ravel(), v.ravel()
    # fit on finite samples only; a NaN/inf flow pixel (occlusion, unmatched) must
    # not silently collapse the whole model. Too few finite samples -> NaN model
    # (a visible failure) rather than a fake zero-motion answer.
    finite = np.isfinite(bu) & np.isfinite(bv)
    if int(finite.sum()) < 3:
        return np.full((2, 3), np.nan)
    Af, buf, bvf = A[finite], bu[finite], bv[finite]
    if method not in {"exact", "fast"}:
        raise ValueError("method must be 'exact' or 'fast'")

    def solve(a, rhs_u, rhs_v):
        if method == "fast":
            coefficients, *_ = np.linalg.lstsq(
                a, np.column_stack((rhs_u, rhs_v)), rcond=None)
            return coefficients.T
        coefficient_u, *_ = np.linalg.lstsq(a, rhs_u, rcond=None)
        coefficient_v, *_ = np.linalg.lstsq(a, rhs_v, rcond=None)
        return coefficient_u, coefficient_v

    cu, cv = solve(Af, buf, bvf)
    if robust:
        for _ in range(max(1, int(iters))):         # each pass trims then re-fits
            resid = np.hypot(buf - Af @ cu, bvf - Af @ cv)
            thresh = np.quantile(resid, 1.0 - float(trim))
            keep = resid <= thresh
            if int(keep.sum()) < 3:
                break
            cu, cv = solve(Af[keep], buf[keep], bvf[keep])
    return np.stack([cu, cv], axis=0)


def flow_from_model(M, shape) -> tuple[np.ndarray, np.ndarray]:
    """Evaluate an affine motion model *M* (2, 3) into ``(u, v)`` fields of *shape*."""
    M = np.asarray(M, np.float64)
    H, W = shape
    yy, xx = np.ogrid[:H, :W]
    um = M[0, 0] + M[0, 1] * xx + M[0, 2] * yy
    vm = M[1, 0] + M[1, 1] * xx + M[1, 2] * yy
    return um, vm


def residual_motion(u, v, model=None, **fit):
    """Flow with the global/camera motion removed — the independent object motion.

    Fits :func:`dominant_motion` (unless a model *M* is supplied) and subtracts it.
    Returns ``(ru, rv)``, near zero wherever the pixel just followed the global
    motion and large where something moved on its own."""
    u = np.asarray(u, np.float64)
    v = np.asarray(v, np.float64)
    M = dominant_motion(u, v, **fit) if model is None else np.asarray(model, np.float64)
    um, vm = flow_from_model(M, u.shape)
    return u - um, v - vm


def motion_segments(u, v, threshold: float, subtract_dominant: bool = True,
                    min_area: int = 25, smooth: float = 1.0):
    """Segment independently-moving regions from a flow field.

    Removes the global motion (unless *subtract_dominant* is False), then labels
    connected regions whose residual speed exceeds *threshold* (px/frame — size it
    from :func:`frame_motion_energy`). Returns ``(mask, segments)`` with per-region
    dicts (``area`` / ``centroid`` (row, col) / ``bbox`` / ``mean_speed``),
    largest-first. Blobs smaller than *min_area* pixels are dropped. *smooth* is
    the number of binary-closing iterations used to knit noisy interiors together
    *after* thresholding — so ``area`` and ``mean_speed`` are measured on the true
    (un-blurred) speed field, not a smoothed one."""
    if subtract_dominant:
        ru, rv = residual_motion(u, v)
    else:
        ru, rv = np.asarray(u, np.float64), np.asarray(v, np.float64)
    mag = np.hypot(ru, rv)
    mask = mag > float(threshold)
    if smooth and smooth > 0:
        # morphological closing fills holes/gaps without the area-dilation and
        # interior-attenuation a Gaussian blur of the speed field would introduce.
        # Pad by edge-replication first so a moving region touching the frame
        # border is not eroded away by the closing's zero-valued exterior.
        it = int(round(smooth))
        padded = ndimage.binary_closing(np.pad(mask, it, mode="edge"), iterations=it)
        mask = padded[it:-it, it:-it]
    lbl, n = ndimage.label(mask)
    segments = []
    for i, bounds in enumerate(ndimage.find_objects(lbl), start=1):
        if bounds is None:
            continue
        local = lbl[bounds] == i
        local_y, local_x = np.where(local)
        ys = local_y + bounds[0].start
        xs = local_x + bounds[1].start
        if xs.size < int(min_area):
            view = mask[bounds]
            view[local] = False
            continue
        segments.append({
            "area": int(xs.size),
            "centroid": (float(ys.mean()), float(xs.mean())),
            "bbox": (int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max())),
            "mean_speed": float(mag[ys, xs].mean()),
        })
    segments.sort(key=lambda r: r["area"], reverse=True)
    return mask, segments
