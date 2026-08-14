"""videops.py — spatiotemporal operators for video / higher-dimensional stacks.

Where the rest of the library reasons about a *single* 2-D frame, this module adds
the *time* axis. A "video" here is a plain float64 array of shape ``(T, H, W)`` in
``[0, 1]`` — a stack of ``T`` grayscale frames from a static-camera sequence (an
onocollo physics clip, an evis / hillco pose capture, a microscope time-lapse, a
security feed). A Python list of equal-shape 2-D frames is also accepted and is
stacked into ``(T, H, W)`` for you.

Everything here is numpy + scipy only and deterministic. Three output shapes occur,
each documented per function:

* **video** ``(T, H, W)`` — a processed sequence (denoise, gradient, smoothing).
* **map**   ``(H, W)``    — a single image collapsing the time axis (activity,
  projection, motion energy). These are *analysis maps*, not display images, so a
  map may legitimately exceed ``[0, 1]`` (e.g. an energy is a sum over time).
* **scalar / mask** — a per-frame foreground mask ``(T, H, W)`` of 0/1.

Malformed input is rejected up front (``ValueError`` for a non-3-D array, a
non-finite sample, or ``T < 1``) — the same fail-closed discipline as
:mod:`mesh` / :mod:`pointcloud`. Outputs are always finite.

    import videops as vp
    vid = ...                              # (T, H, W) in [0, 1]
    bg_removed = vp.background_subtraction(vid, threshold=0.15)   # (T, H, W) mask
    where_it_moved = vp.motion_energy(vid)                        # (H, W) map
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

__all__ = [
    "temporal_mean", "temporal_median", "temporal_std",
    "frame_difference", "background_subtraction", "temporal_gradient",
    "motion_energy", "temporal_max", "temporal_min", "moving_average",
    "spatiotemporal_gaussian", "spatiotemporal_sobel", "per_frame",
    "flicker_reduce", "optical_flow_sequence",
]


def _as_video(video) -> np.ndarray:
    """Coerce *video* to a validated ``(T, H, W)`` float64 array.

    Accepts either a 3-D array-like or a list/tuple of equal-shape 2-D frames.
    Raises ``ValueError`` on a non-3-D result, a ragged frame list, ``T < 1``, or
    any non-finite sample — nothing downstream ever sees a NaN/Inf or a bad rank.
    """
    if isinstance(video, (list, tuple)):
        frames = [np.asarray(f, np.float64) for f in video]
        if not frames:
            raise ValueError("video is an empty frame list (need T >= 1)")
        if any(f.ndim != 2 for f in frames):
            raise ValueError("each frame in a frame list must be 2-D (H, W)")
        shapes = {f.shape for f in frames}
        if len(shapes) != 1:
            raise ValueError(f"frames have differing shapes: {sorted(shapes)!r}")
        vid = np.stack(frames, axis=0)
    else:
        vid = np.asarray(video, np.float64)
    if vid.ndim != 3:
        raise ValueError(f"video must be (T, H, W); got ndim={vid.ndim} "
                         f"shape={getattr(vid, 'shape', None)!r}")
    if vid.shape[0] < 1:
        raise ValueError("video needs at least one frame (T >= 1)")
    if not np.all(np.isfinite(vid)):
        raise ValueError("video contains non-finite samples (NaN/Inf)")
    return vid


# --------------------------------------------------------------------------- #
# Temporal reductions (time axis -> a single (H, W) map)
# --------------------------------------------------------------------------- #
def temporal_mean(video) -> np.ndarray:
    """Per-pixel mean over time -> ``(H, W)``.

    The textbook denoiser for a *static* camera: zero-mean sensor noise averages
    out over ``T`` frames while the stationary scene survives, giving a clean
    background/reference image. Returns a map in ``[0, 1]`` when the input is."""
    vid = _as_video(video)
    return vid.mean(axis=0)


def temporal_median(video) -> np.ndarray:
    """Per-pixel median over time -> ``(H, W)``.

    Like :func:`temporal_mean` but robust: transient objects that occupy any pixel
    for a *minority* of frames are rejected, so a busy scene still yields the clean
    empty-scene background. This is the background model :func:`background_subtraction`
    uses."""
    vid = _as_video(video)
    return np.median(vid, axis=0)


def temporal_std(video) -> np.ndarray:
    """Per-pixel standard deviation over time -> ``(H, W)`` *activity map*.

    Pixels that never change read ~0; pixels a moving object passes through read
    high. A parameter-free "where did anything happen" map. For a perfectly static
    sequence this is ~0 everywhere (up to float rounding)."""
    vid = _as_video(video)
    return vid.std(axis=0)


def temporal_max(video) -> np.ndarray:
    """Maximum-intensity projection over time -> ``(H, W)``.

    Each output pixel is the brightest it ever got. A dot that blinks on somewhere
    is captured at full brightness regardless of how briefly it appeared — the
    standard way to see the union of everything bright across a clip."""
    vid = _as_video(video)
    return vid.max(axis=0)


def temporal_min(video) -> np.ndarray:
    """Minimum-intensity projection over time -> ``(H, W)``.

    Each output pixel is the darkest it ever got — the dual of :func:`temporal_max`
    (isolates persistent dark structure / removes transient bright flashes)."""
    vid = _as_video(video)
    return vid.min(axis=0)


def motion_energy(video) -> np.ndarray:
    """Total motion over time -> ``(H, W)`` map: ``sum_t |d video / dt|``.

    Integrates the absolute :func:`temporal_gradient` over the whole clip, so the
    map lights up exactly where intensity changed — the path a moving object swept
    out. A static sequence gives ~0 everywhere. This is a *magnitude* sum, so
    values can exceed 1 (it is an energy map, not a displayable image)."""
    vid = _as_video(video)
    return np.abs(_temporal_gradient(vid)).sum(axis=0)


# --------------------------------------------------------------------------- #
# Temporal derivatives / differences (-> a volume)
# --------------------------------------------------------------------------- #
def frame_difference(video) -> np.ndarray:
    """Consecutive-frame absolute difference -> ``(T-1, H, W)`` motion volume.

    ``out[t] = |video[t+1] - video[t]|``. The simplest motion cue: nonzero exactly
    where something moved between two frames. A single-frame clip (``T == 1``)
    yields an empty ``(0, H, W)`` volume (there is no pair to difference)."""
    vid = _as_video(video)
    return np.abs(np.diff(vid, axis=0))


def _temporal_gradient(vid: np.ndarray) -> np.ndarray:
    """Central-difference d/dt on a pre-validated video (endpoints one-sided).

    Uses :func:`numpy.gradient` along the time axis (2nd-order central in the
    interior, 1st-order at the ends). For ``T < 2`` there is no temporal
    neighbour, so the gradient is zero everywhere."""
    if vid.shape[0] < 2:
        return np.zeros_like(vid)
    return np.gradient(vid, axis=0)


def temporal_gradient(video) -> np.ndarray:
    """Central-difference temporal derivative ``d video / dt`` -> ``(T, H, W)``.

    Signed rate of change per frame (positive where a pixel is brightening,
    negative where it is darkening). Endpoints use a one-sided difference so the
    output keeps the full ``T`` frames. ``T == 1`` -> all zeros (no time neighbour)."""
    return _temporal_gradient(_as_video(video))


# --------------------------------------------------------------------------- #
# Background modelling
# --------------------------------------------------------------------------- #
def background_subtraction(video, threshold: float = 0.1) -> np.ndarray:
    """Temporal-median background model -> per-frame foreground mask ``(T, H, W)``.

    Builds a background image with :func:`temporal_median` (robust to transient
    objects), then flags each frame's pixels whose absolute deviation from that
    background exceeds *threshold*::

        mask[t] = |video[t] - median_t(video)| > threshold

    *threshold* is in intensity units of the ``[0, 1]`` video (default 0.1). A
    perfectly static sequence yields an all-zero (empty) mask; a moving object
    yields a mask localised on the object. Returns a float64 0/1 mask."""
    vid = _as_video(video)
    thr = float(np.clip(threshold, 0.0, 1.0))
    bg = np.median(vid, axis=0)
    return (np.abs(vid - bg[None]) > thr).astype(np.float64)


# --------------------------------------------------------------------------- #
# Temporal / spatiotemporal smoothing
# --------------------------------------------------------------------------- #
def moving_average(video, window: int = 3) -> np.ndarray:
    """Sliding temporal-window box smoothing -> ``(T, H, W)``.

    Averages each pixel over a centred temporal window of *window* frames
    (edge-replicated at the ends), suppressing per-frame noise while preserving
    spatial detail. *window* is clamped to ``[1, T]``; ``window == 1`` is a no-op.
    Uses :func:`scipy.ndimage.uniform_filter1d` along the time axis."""
    vid = _as_video(video)
    w = int(np.clip(int(window), 1, vid.shape[0]))
    if w <= 1:
        return vid.copy()
    return ndimage.uniform_filter1d(vid, size=w, axis=0, mode="nearest")


def spatiotemporal_gaussian(video, sigma_t: float = 1.0,
                            sigma_s: float = 1.0) -> np.ndarray:
    """Separable 3-D Gaussian blur over ``(t, y, x)`` -> ``(T, H, W)``.

    Smooths jointly in time (*sigma_t*) and space (*sigma_s*) — a genuine
    spatiotemporal low-pass that suppresses both spatial and temporal noise. A
    Gaussian preserves a constant volume exactly (DC gain 1), so a flat clip comes
    back unchanged. Negative sigmas are clamped to 0 (that axis is left untouched)."""
    vid = _as_video(video)
    st = max(0.0, float(sigma_t))
    ss = max(0.0, float(sigma_s))
    return ndimage.gaussian_filter(vid, sigma=(st, ss, ss), mode="nearest")


def spatiotemporal_sobel(video) -> np.ndarray:
    """3-D Sobel gradient magnitude over ``(t, y, x)`` -> ``(T, H, W)``.

    Combines the Sobel derivative along time and the two spatial axes into one
    magnitude, ``sqrt(g_t^2 + g_y^2 + g_x^2)`` — a spatiotemporal edge detector
    that responds to both spatial contours and moving edges. A magnitude map (>= 0,
    not bounded by 1)."""
    vid = _as_video(video)
    gt = ndimage.sobel(vid, axis=0, mode="nearest")
    gy = ndimage.sobel(vid, axis=1, mode="nearest")
    gx = ndimage.sobel(vid, axis=2, mode="nearest")
    return np.sqrt(gt * gt + gy * gy + gx * gx)


# --------------------------------------------------------------------------- #
# Per-frame application / photometric normalisation
# --------------------------------------------------------------------------- #
def per_frame(video, fn) -> np.ndarray:
    """Apply a 2-D operator *fn* to every frame independently -> ``(T, H, W)``.

    ``fn`` maps an ``(H, W)`` frame to an ``(H, W)`` result (any of the library's
    spatial ops, or your own callable). Results are stacked back into a video.
    Raises ``TypeError`` if *fn* is not callable and ``ValueError`` if a frame's
    result is not the original ``(H, W)`` shape (so a mistyped op fails loudly
    rather than producing a ragged stack)."""
    vid = _as_video(video)
    if not callable(fn):
        raise TypeError("fn must be callable (H, W) -> (H, W)")
    out = np.empty_like(vid)
    hw = vid.shape[1:]
    for t in range(vid.shape[0]):
        r = np.asarray(fn(vid[t]), np.float64)
        if r.shape != hw:
            raise ValueError(f"fn changed frame shape {hw!r} -> {r.shape!r}")
        out[t] = r
    if not np.all(np.isfinite(out)):
        raise ValueError("fn produced non-finite output")
    return out


def flicker_reduce(video) -> np.ndarray:
    """Remove global per-frame brightness flicker -> ``(T, H, W)``.

    A static scene under an unstable light source (or with auto-exposure hunting)
    shows every frame shifting in overall brightness. This re-levels each frame so
    its mean equals the whole sequence's mean::

        out[t] = video[t] + (mean(video) - mean(video[t]))

    an additive DC correction (no division, so a black frame is safe). The
    corrected frame means are all equal to the sequence mean before the final
    clip back into ``[0, 1]``."""
    vid = _as_video(video)
    seq_mean = float(vid.mean())
    frame_mean = vid.mean(axis=(1, 2))                 # (T,)
    corrected = vid + (seq_mean - frame_mean)[:, None, None]
    return np.clip(corrected, 0.0, 1.0)


# --------------------------------------------------------------------------- #
# Optical flow over a sequence
# --------------------------------------------------------------------------- #
def optical_flow_sequence(video) -> np.ndarray:
    """Consecutive-frame flow-magnitude volume -> ``(T-1, H, W)``.

    For each adjacent pair ``(video[t], video[t+1])`` computes a dense flow and
    returns its per-pixel speed, stacked into a volume that shows how much each
    pixel moved at each step.

    Backend honesty: if :mod:`flow` is importable this uses the *real* dense
    pyramidal Lucas-Kanade estimator (``flow.optical_flow_lk`` +
    ``flow.flow_magnitude``) — true optical flow. If :mod:`flow` cannot be
    imported it falls back to the absolute consecutive-frame difference
    ``|video[t+1] - video[t]|`` as a coarse *motion proxy* — this is NOT optical
    flow (it carries no direction and confounds intensity change with motion), and
    the fallback is taken only when the flow backend is unavailable. A single-frame
    clip yields an empty ``(0, H, W)`` volume."""
    vid = _as_video(video)
    t = vid.shape[0]
    if t < 2:
        return np.zeros((0,) + vid.shape[1:], np.float64)
    try:
        import flow as _flow
        _use_lk = hasattr(_flow, "optical_flow_lk") and hasattr(_flow, "flow_magnitude")
    except ImportError:
        _flow = None
        _use_lk = False
    out = np.empty((t - 1,) + vid.shape[1:], np.float64)
    for i in range(t - 1):
        if _use_lk:
            u, v = _flow.optical_flow_lk(vid[i], vid[i + 1])
            out[i] = _flow.flow_magnitude(u, v)
        else:
            out[i] = np.abs(vid[i + 1] - vid[i])
    out[~np.isfinite(out)] = 0.0
    return out
