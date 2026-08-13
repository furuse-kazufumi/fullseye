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
    seq = [np.asarray(f, np.float64) for f in frames]
    if len(seq) < 2:
        return np.zeros(0)
    import flow
    return np.array([frame_motion_energy(*flow.optical_flow_lk(a, b, **flow_kwargs))
                     for a, b in zip(seq[:-1], seq[1:])])


def detect_events(energy, threshold=None, k: float = 2.0) -> np.ndarray:
    """Indices of motion-energy spikes in a per-frame-pair energy signal.

    Returns the local maxima that exceed *threshold* (default ``mean + k*std`` of
    the signal) — the frame-pair indices at which an event occurred."""
    e = np.asarray(energy, np.float64)
    if e.size == 0:
        return np.zeros(0, dtype=int)
    thr = float(e.mean() + float(k) * e.std()) if threshold is None else float(threshold)
    events = []
    for i in range(e.size):
        if e[i] <= thr:
            continue
        left = e[i - 1] if i > 0 else -np.inf
        right = e[i + 1] if i < e.size - 1 else -np.inf
        if e[i] >= left and e[i] >= right:
            events.append(i)
    return np.array(events, dtype=int)


def frame_motion_energy(u, v) -> float:
    """RMS speed over the field — one scalar per frame pair. Tracking this across
    a clip gives a motion-energy signal whose peaks cue events (impact, contact,
    a sudden move)."""
    u = np.asarray(u, np.float64)
    v = np.asarray(v, np.float64)
    return float(np.sqrt(np.mean(u * u + v * v)))


def dominant_motion(u, v, robust: bool = True, trim: float = 0.25,
                    iters: int = 3) -> np.ndarray:
    """Fit the global affine motion ``[u; v] = M · [1, x, y]`` by least squares.

    This is the camera / whole-scene motion. With *robust* (default) the highest-
    residual pixels — the independently moving foreground — are trimmed and the
    model re-fit, so a moving object does not bias the global estimate. Returns
    ``M`` of shape (2, 3): row 0 = (c, ∂u/∂x, ∂u/∂y), row 1 the same for ``v``."""
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
    cu, *_ = np.linalg.lstsq(Af, buf, rcond=None)   # initial (non-robust) fit
    cv, *_ = np.linalg.lstsq(Af, bvf, rcond=None)
    if robust:
        for _ in range(max(1, int(iters))):         # each pass trims then re-fits
            resid = np.hypot(buf - Af @ cu, bvf - Af @ cv)
            thresh = np.quantile(resid, 1.0 - float(trim))
            keep = resid <= thresh
            if int(keep.sum()) < 3:
                break
            cu, *_ = np.linalg.lstsq(Af[keep], buf[keep], rcond=None)
            cv, *_ = np.linalg.lstsq(Af[keep], bvf[keep], rcond=None)
    return np.stack([cu, cv], axis=0)


def flow_from_model(M, shape) -> tuple[np.ndarray, np.ndarray]:
    """Evaluate an affine motion model *M* (2, 3) into ``(u, v)`` fields of *shape*."""
    M = np.asarray(M, np.float64)
    H, W = shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
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
    for i in range(1, n + 1):
        ys, xs = np.where(lbl == i)
        if xs.size < int(min_area):
            mask[ys, xs] = False
            continue
        segments.append({
            "area": int(xs.size),
            "centroid": (float(ys.mean()), float(xs.mean())),
            "bbox": (int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max())),
            "mean_speed": float(mag[ys, xs].mean()),
        })
    segments.sort(key=lambda r: r["area"], reverse=True)
    return mask, segments
