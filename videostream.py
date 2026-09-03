# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""videostream — frame-by-frame (streaming) video processing: ring buffer, stateful temporal ops, pipeline.

Why this module exists (measured, ``docs/design/PERF_MEMORY_VIDEO_SURVEY.md`` §3):
:mod:`videops` works on a whole ``(T, H, W)`` float64 clip at once, so one second
of 1080p costs 475 MB before any op runs, and nothing in the registry can hold
state between frames. A camera, a robot's eye or a long recording never gives you
"all T frames" — it gives you one frame at a time. This module is the structural
answer: a fixed-size **ring buffer** (memory = N frames, not T), **stateful ops**
that consume one frame and emit one result, and a **pipeline** that chains
per-frame facade ops with stateful stages and reports what it did.

Contract
--------
* A *frame* is ``(H, W)`` gray (or ``(H, W, C)`` colour for the ring only). The
  first frame fixes the shape and dtype; a later frame with another shape or
  dtype is **refused** (``ValueError``) — a dropped or resized frame silently
  poisoning a temporal window is exactly the failure a stream must not hide.
* Frames may be float64 ``[0, 1]`` (the library contract) **or** ``uint8`` /
  ``uint16``. Integer frames are kept in the ring as integers (8× less memory
  than float64) and converted honestly at compute time (``/255``, ``/65535``);
  every op's *output* is float64 in the library contract, so downstream ops see
  what they always see.
* Window ops are **causal**: the output at frame ``t`` uses frames
  ``t-N+1 .. t`` only. While the ring is still filling they use the frames seen
  so far (a 1-frame window on the first frame). This differs from the centred,
  whole-clip reductions in :mod:`videops` (``temporal_median`` is the median over
  *all* T frames), which is why the streaming ops carry different names
  (``temporal_median_window`` …) — a same-named op with different numbers would
  be a lie.
* Fail-soft with a clean state: when a stateful stage raises inside
  :class:`VideoPipeline`, the stage is **reset** (its ring emptied) and the
  event recorded in the fallback ledger with ``source="stream"``; under
  ``on_error="raise"`` the exception propagates. A stage never keeps running on
  a half-updated window.

The batch functions at the bottom (``temporal_median_window(video, window)`` …)
are what the op ledger (:mod:`opsvideostream`) registers: they *are* the
streaming classes replayed over a ``(T, H, W)`` array, so the ledger op and the
live stream give bit-identical results — tests pin that.

    import fullseye as fs
    pipe = fs.VideoPipeline([("gauss_filter", 0.3, 0.5), fs.BackgroundSubtractionWindow(5, 0.1)])
    for mask in pipe.run(fs.iter_frames("clip.mp4", dtype="uint8")):
        ...
    print(pipe.stats())
"""
from __future__ import annotations

import time
from typing import Callable, Iterable, Optional

import numpy as np

__all__ = [
    "FrameRing", "StatefulOp",
    "TemporalMedianWindow", "MovingAverageWindow", "BackgroundSubtractionWindow",
    "FrameDifference", "ExponentialBackground", "RunningStats", "OpticalFlowStream",
    "VideoPipeline",
    "temporal_median_window", "moving_average_window", "background_subtraction_window",
    "frame_difference_causal", "exponential_background", "exponential_foreground",
    "running_mean_std", "optical_flow_magnitude_stream", "stream_replay",
]

MAX_WINDOW = 4096


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _int(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s must be an int, got %r" % (name, v))
    v = int(v)
    if v < lo or v > hi:
        raise ValueError("%s must be in [%d, %d], got %d" % (name, lo, hi, v))
    return v


def _float(v, name, lo=None, hi=None):
    if isinstance(v, bool) or not isinstance(v, (int, float, np.integer, np.floating)):
        raise ValueError("%s must be a number, got %r" % (name, v))
    v = float(v)
    if not np.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (name, v))
    if lo is not None and v < lo or hi is not None and v > hi:
        raise ValueError("%s must be in [%s, %s], got %r" % (name, lo, hi, v))
    return v


def _scale_of(dtype) -> float:
    """Divisor that maps an integer frame to ``[0, 1]`` (1.0 for floats)."""
    dt = np.dtype(dtype)
    if dt.kind == "u":
        return float(np.iinfo(dt).max)
    if dt.kind == "i":
        return float(np.iinfo(dt).max)
    if dt.kind == "f":
        return 1.0
    if dt.kind == "b":
        return 1.0
    raise ValueError("unsupported frame dtype %s (need uint8/uint16/float/bool)" % dt)


def _frame(frame) -> np.ndarray:
    """Validate one incoming frame: ndarray, 2-D or 3-D, finite if float."""
    a = np.asarray(frame)
    if a.ndim not in (2, 3):
        raise ValueError("frame must be (H, W) or (H, W, C); got ndim=%d shape=%r" % (a.ndim, a.shape))
    if a.size == 0:
        raise ValueError("frame is empty: shape %r" % (a.shape,))
    _scale_of(a.dtype)
    if a.dtype.kind == "f" and not np.all(np.isfinite(a)):
        raise ValueError("frame contains non-finite samples (NaN/Inf)")
    return a


def _to01(a: np.ndarray) -> np.ndarray:
    """Frame (any accepted dtype) → float64 in the library contract."""
    s = _scale_of(a.dtype)
    if a.dtype.kind == "f":
        return np.clip(a.astype(np.float64, copy=False), 0.0, 1.0)
    return a.astype(np.float64) / s


# --------------------------------------------------------------------------- #
# ring buffer
# --------------------------------------------------------------------------- #
class FrameRing:
    """Fixed-capacity ring of the last *n* frames, pre-allocated on the first push.

    Memory is ``n × frame`` in the **frame's own dtype** (a uint8 1080p ring of
    5 is 10 MB; the equivalent float64 ``(T, H, W)`` clip of one second is 475 MB).
    ``push`` refuses a frame whose shape or dtype differs from the first one.
    ``window()`` returns the stored frames oldest → newest as an array (a copy
    when the ring has wrapped, a view otherwise); ``latest`` is always a view.
    """

    def __init__(self, n: int):
        self.n = _int(n, "n", 1, MAX_WINDOW)
        self._buf: Optional[np.ndarray] = None
        self._head = 0          # index where the next frame goes
        self._count = 0         # frames currently stored (≤ n)
        self.total = 0          # frames ever pushed

    # -- state ------------------------------------------------------------ #
    @property
    def shape(self):
        return None if self._buf is None else self._buf.shape[1:]

    @property
    def dtype(self):
        return None if self._buf is None else self._buf.dtype

    @property
    def full(self) -> bool:
        return self._count == self.n

    def __len__(self) -> int:
        return self._count

    def nbytes(self) -> int:
        return 0 if self._buf is None else int(self._buf.nbytes)

    def reset(self) -> None:
        """Forget every stored frame (the allocation is kept for reuse)."""
        self._head = 0
        self._count = 0

    # -- access ----------------------------------------------------------- #
    def push(self, frame) -> None:
        a = _frame(frame)
        if self._buf is None or (self._count == 0 and (a.shape != self._buf.shape[1:]
                                                       or a.dtype != self._buf.dtype)):
            self._buf = np.empty((self.n,) + a.shape, a.dtype)      # (re)allocate: empty ring = new stream
        elif a.shape != self._buf.shape[1:] or a.dtype != self._buf.dtype:
            raise ValueError("frame %r %s does not match the ring's %r %s (stream refused; call reset())"
                             % (a.shape, a.dtype, self._buf.shape[1:], self._buf.dtype))
        self._buf[self._head] = a
        self._head = (self._head + 1) % self.n
        self._count = min(self._count + 1, self.n)
        self.total += 1

    @property
    def latest(self) -> np.ndarray:
        if self._count == 0:
            raise ValueError("ring is empty")
        return self._buf[(self._head - 1) % self.n]

    def window(self) -> np.ndarray:
        """Stored frames oldest → newest, shape ``(count, H, W[, C])``."""
        if self._count == 0:
            raise ValueError("ring is empty")
        if self._count < self.n:
            return self._buf[:self._count]
        if self._head == 0:
            return self._buf
        return np.concatenate([self._buf[self._head:], self._buf[:self._head]], axis=0)

    def window01(self) -> np.ndarray:
        """``window()`` converted to float64 ``[0, 1]``."""
        return _to01(self.window())


# --------------------------------------------------------------------------- #
# stateful ops
# --------------------------------------------------------------------------- #
class StatefulOp:
    """Base class: ``push(frame) -> result``, ``reset()``, ``state`` (a small dict).

    Subclasses implement ``_update(frame01, raw)`` and may keep a ring. The
    base handles frame validation, shape/dtype locking and the frame counter,
    so every stateful op refuses a mismatched frame the same way.
    """
    name = "stateful"

    def __init__(self):
        self.frames = 0
        self._shape = None
        self._dtype = None

    def reset(self) -> None:
        self.frames = 0
        self._shape = None
        self._dtype = None
        self._reset()

    def _reset(self) -> None:          # pragma: no cover - overridden
        pass

    def push(self, frame):
        a = _frame(frame)
        if self._shape is None:
            self._shape, self._dtype = a.shape, a.dtype
        elif a.shape != self._shape or a.dtype != self._dtype:
            raise ValueError("%s: frame %r %s does not match the stream's %r %s (refused; call reset())"
                             % (self.name, a.shape, a.dtype, self._shape, self._dtype))
        out = self._update(a)
        self.frames += 1
        return out

    def _update(self, raw: np.ndarray):    # pragma: no cover - overridden
        raise NotImplementedError

    @property
    def state(self) -> dict:
        return {"name": self.name, "frames": self.frames, "shape": self._shape,
                "dtype": None if self._dtype is None else str(self._dtype)}

    def __call__(self, frame):
        return self.push(frame)


class _RingOp(StatefulOp):
    """A stateful op backed by a :class:`FrameRing` of *window* frames."""

    def __init__(self, window: int):
        super().__init__()
        self.window = _int(window, "window", 1, MAX_WINDOW)
        self.ring = FrameRing(self.window)

    def _reset(self) -> None:
        self.ring.reset()

    @property
    def state(self) -> dict:
        d = super().state
        d.update({"window": self.window, "stored": len(self.ring), "ring_bytes": self.ring.nbytes()})
        return d


class TemporalMedianWindow(_RingOp):
    """Per-pixel median of the last *window* frames (causal) → ``(H, W)`` float64.

    Integer frames are medianed as integers (exact; the median of a uint8 window
    is a representable value or the mean of two) and scaled once at the end.
    """
    name = "temporal_median_window"

    def _update(self, raw):
        self.ring.push(raw)
        w = self.ring.window()
        if w.dtype.kind in "ui":
            return np.median(w, axis=0) / _scale_of(w.dtype)
        return np.median(_to01(w), axis=0)


class MovingAverageWindow(_RingOp):
    """Per-pixel mean of the last *window* frames (causal) → ``(H, W)`` float64.

    Causal counterpart of :func:`videops.moving_average` (which is centred and
    edge-replicated); the two agree only in the interior of a clip.
    """
    name = "moving_average_window"

    def _update(self, raw):
        self.ring.push(raw)
        w = self.ring.window()
        return w.mean(axis=0, dtype=np.float64) / _scale_of(w.dtype)


class BackgroundSubtractionWindow(_RingOp):
    """Foreground mask ``|frame − median(last window)| > threshold`` → 0/1 float64 ``(H, W)``.

    The background is the causal window median (this frame included, as in
    :func:`videops.background_subtraction` where the median includes every
    frame). *threshold* is in ``[0, 1]`` intensity units.
    """
    name = "background_subtraction_window"

    def __init__(self, window: int = 5, threshold: float = 0.1):
        super().__init__(window)
        self.threshold = _float(threshold, "threshold", 0.0, 1.0)
        self.background = None

    def _update(self, raw):
        self.ring.push(raw)
        w = self.ring.window()
        if w.dtype.kind in "ui":
            bg = np.median(w, axis=0) / _scale_of(w.dtype)
        else:
            bg = np.median(_to01(w), axis=0)
        self.background = bg
        return (np.abs(_to01(raw) - bg) > self.threshold).astype(np.float64)


class FrameDifference(StatefulOp):
    """``|frame − previous frame|`` → ``(H, W)`` float64; zeros for the first frame.

    Keeps exactly one frame of state (in the frame's dtype). Integer frames use
    an exact integer absolute difference.
    """
    name = "frame_difference_causal"

    def __init__(self):
        super().__init__()
        self.prev = None

    def _reset(self):
        self.prev = None

    def _update(self, raw):
        if self.prev is None:
            out = np.zeros(raw.shape, np.float64)
        elif raw.dtype.kind in "ui":
            wide = np.int64 if raw.dtype.itemsize >= 4 else np.int32
            out = np.abs(raw.astype(wide) - self.prev.astype(wide)) / _scale_of(raw.dtype)
        else:
            out = np.abs(_to01(raw) - _to01(self.prev))
        self.prev = raw.copy()
        return out


class ExponentialBackground(StatefulOp):
    """Recursive background ``bg ← (1−α)·bg + α·frame`` → the background ``(H, W)`` float64.

    The classic O(1)-memory background model (one float64 image of state, no
    window). ``foreground()`` gives ``|frame − bg| > threshold`` for the last
    frame pushed. The first frame initialises the background.
    """
    name = "exponential_background"

    def __init__(self, alpha: float = 0.05, threshold: float = 0.1):
        super().__init__()
        self.alpha = _float(alpha, "alpha", 0.0, 1.0)
        self.threshold = _float(threshold, "threshold", 0.0, 1.0)
        self.bg = None
        self._last = None

    def _reset(self):
        self.bg = None
        self._last = None

    def _update(self, raw):
        f = _to01(raw)
        if self.bg is None:
            self.bg = f.copy()
        else:
            self.bg += self.alpha * (f - self.bg)
        self._last = f
        return self.bg.copy()

    def foreground(self) -> np.ndarray:
        if self._last is None:
            raise ValueError("no frame pushed yet")
        return (np.abs(self._last - self.bg) > self.threshold).astype(np.float64)


class RunningStats(StatefulOp):
    """Welford running per-pixel mean / variance over every frame seen → ``{"mean", "std", "n"}``.

    Two float64 images of state regardless of how long the stream is; the
    result after T frames equals ``video.mean(0)`` / ``video.std(0)`` (population
    std) to round-off. ``push`` returns the current dict (arrays are copies).
    """
    name = "running_mean_std"

    def __init__(self):
        super().__init__()
        self.mean = None
        self.m2 = None

    def _reset(self):
        self.mean = None
        self.m2 = None

    def _update(self, raw):
        f = _to01(raw)
        n = self.frames + 1
        if self.mean is None:
            self.mean = f.copy()
            self.m2 = np.zeros_like(f)
        else:
            d = f - self.mean
            self.mean += d / n
            self.m2 += d * (f - self.mean)
        return {"mean": self.mean.copy(), "std": np.sqrt(self.m2 / n), "n": n}


class OpticalFlowStream(StatefulOp):
    """Dense flow between the previous and the current frame → speed ``(H, W)`` float64.

    Uses :func:`flow.optical_flow_lk` (pyramidal Lucas–Kanade; keyword arguments
    are passed through). Zeros for the first frame. ``last_flow`` holds the
    ``(u, v)`` pair of the last step for callers that want direction too.
    """
    name = "optical_flow_magnitude_stream"

    def __init__(self, **flow_kwargs):
        super().__init__()
        self.flow_kwargs = dict(flow_kwargs)
        self.prev = None
        self.last_flow = None

    def _reset(self):
        self.prev = None
        self.last_flow = None

    def _update(self, raw):
        import flow as _flow
        f = _to01(raw)
        if f.ndim != 2:
            raise ValueError("optical flow needs gray (H, W) frames, got %r" % (f.shape,))
        if self.prev is None:
            out = np.zeros(f.shape, np.float64)
        else:
            u, v = _flow.optical_flow_lk(self.prev, f, **self.flow_kwargs)
            self.last_flow = (u, v)
            out = _flow.flow_magnitude(u, v)
            out[~np.isfinite(out)] = 0.0
        self.prev = f
        return out


class MotionHistoryImage(StatefulOp):
    """Motion History Image (Bobick & Davis 2001) → ``(H, W)`` float64 in ``[0, 1]``.

    Where motion happens now the image is set to 1; elsewhere it decays linearly
    by ``1/tau`` per frame, so a bright-to-dark gradient records *where* motion
    was and *how recently* — a compact temporal signature of a gesture. Motion is
    ``|frame − previous| > threshold``. ``energy()`` gives the Motion Energy Image
    (the binary union ``MHI > 0``, i.e. *where* motion happened at all).
    """
    name = "motion_history_image"

    def __init__(self, tau: int = 15, threshold: float = 0.1):
        super().__init__()
        self.tau = _int(tau, "tau", 1, MAX_WINDOW)
        self.threshold = _float(threshold, "threshold", 0.0, 1.0)
        self.hist = None
        self.prev = None

    def _reset(self):
        self.hist = None
        self.prev = None

    def _update(self, raw):
        f = _to01(raw)
        if self.hist is None:
            self.hist = np.zeros(f.shape, np.float64)
        if self.prev is not None:
            motion = np.abs(f - self.prev) > self.threshold
            decayed = np.maximum(0.0, self.hist - 1.0 / self.tau)
            self.hist = np.where(motion, 1.0, decayed)
        self.prev = f
        return self.hist.copy()

    def energy(self) -> np.ndarray:
        if self.hist is None:
            raise ValueError("no frame pushed yet")
        return (self.hist > 0.0).astype(np.float64)


class ThreeFrameDifference(StatefulOp):
    """Three-frame difference motion mask (Collins et al., VSAM 2000) → 0/1 float64 ``(H, W)``.

    ``(|f_t − f_{t−1}| > threshold) AND (|f_{t−1} − f_{t−2}| > threshold)``. The
    logical AND of two consecutive frame differences removes the *ghost* (the
    trailing region a plain two-frame difference marks behind a moving object)
    and fills the object's interior better than one difference alone. Zeros for
    the first two frames (two differences are not available yet).
    """
    name = "three_frame_difference"

    def __init__(self, threshold: float = 0.1):
        super().__init__()
        self.threshold = _float(threshold, "threshold", 0.0, 1.0)
        self.prev1 = None
        self.prev2 = None

    def _reset(self):
        self.prev1 = None
        self.prev2 = None

    def _update(self, raw):
        f = _to01(raw)
        if self.prev1 is None:
            out = np.zeros(f.shape, np.float64)
        elif self.prev2 is None:
            out = np.zeros(f.shape, np.float64)
        else:
            d_now = np.abs(f - self.prev1) > self.threshold
            d_prev = np.abs(self.prev1 - self.prev2) > self.threshold
            out = (d_now & d_prev).astype(np.float64)
        self.prev2 = self.prev1
        self.prev1 = f
        return out


class RunningGaussianForeground(StatefulOp):
    """Adaptive single-Gaussian background (Wren *Pfinder* 1997) → 0/1 foreground ``(H, W)``.

    Each pixel keeps a running mean and variance. A pixel is foreground when it
    is more than ``k`` standard deviations from its mean
    (``(frame − mean)² > k²·var``). Unlike :class:`ExponentialBackground` (a fixed
    absolute threshold on a mean-only model), the threshold is *per pixel* and
    scales with how noisy that pixel is, so a busy texture and a flat wall get
    different sensitivities. With ``selective=True`` (the default) the background
    is updated only where the pixel is *not* foreground, so a slow-moving object
    is not absorbed into the background. ``background()`` returns the mean image.
    """
    name = "running_gaussian_foreground"

    def __init__(self, alpha: float = 0.02, k: float = 2.5,
                 var_init: float = 0.01, var_floor: float = 1e-4, selective: bool = True):
        super().__init__()
        self.alpha = _float(alpha, "alpha", 0.0, 1.0)
        self.k = _float(k, "k", 0.0, 100.0)
        self.var_init = _float(var_init, "var_init", 1e-9, 1.0)
        self.var_floor = _float(var_floor, "var_floor", 1e-12, 1.0)
        self.selective = bool(selective)
        self.mean = None
        self.var = None

    def _reset(self):
        self.mean = None
        self.var = None

    def _update(self, raw):
        f = _to01(raw)
        if self.mean is None:
            self.mean = f.copy()
            self.var = np.full(f.shape, self.var_init, np.float64)
            return np.zeros(f.shape, np.float64)
        diff = f - self.mean
        dist2 = diff * diff
        fg = dist2 > (self.k * self.k) * self.var
        upd = ~fg if self.selective else np.ones(f.shape, bool)
        self.mean = np.where(upd, self.mean + self.alpha * diff, self.mean)
        self.var = np.where(upd, self.var + self.alpha * (dist2 - self.var), self.var)
        np.maximum(self.var, self.var_floor, out=self.var)
        return fg.astype(np.float64)

    def background(self) -> np.ndarray:
        if self.mean is None:
            raise ValueError("no frame pushed yet")
        return self.mean.copy()


class TemporalBilateral(_RingOp):
    """Causal temporal bilateral denoise over the last *window* frames → ``(H, W)`` float64.

    A per-pixel weighted average of the recent frames where the weight of frame
    ``i`` is a Gaussian in *time* (older frames count less, ``sigma_t`` in frames)
    times a Gaussian in *intensity* (frames whose value differs from the current
    one count less, ``sigma_r`` in ``[0, 1]`` units). The intensity term is what
    makes it edge-preserving *in time*: a pixel that just moved gets a small
    weight on the stale frames, so the moving edge is not smeared into a ghost the
    way :class:`MovingAverageWindow` smears it. Falls back to the current frame
    where every weight underflows.
    """
    name = "temporal_bilateral"

    def __init__(self, window: int = 5, sigma_t: float = 2.0, sigma_r: float = 0.1):
        super().__init__(window)
        self.sigma_t = _float(sigma_t, "sigma_t", 1e-3, 1e6)
        self.sigma_r = _float(sigma_r, "sigma_r", 1e-4, 1e6)

    def _update(self, raw):
        self.ring.push(raw)
        w = _to01(self.ring.window())          # (k, H, W), oldest .. newest
        k = w.shape[0]
        cur = w[-1]
        age = np.arange(k - 1, -1, -1.0)        # newest -> 0
        wt = np.exp(-(age * age) / (2.0 * self.sigma_t * self.sigma_t))
        dr = w - cur                            # intensity difference to current
        wr = np.exp(-(dr * dr) / (2.0 * self.sigma_r * self.sigma_r))
        weight = wt[:, None, None] * wr
        denom = weight.sum(axis=0)
        num = (weight * w).sum(axis=0)
        out = np.where(denom > 0, num / np.where(denom > 0, denom, 1.0), cur)
        return out


class Deflicker(StatefulOp):
    """Luminance deflicker: rescale each frame so its mean tracks a running reference → ``(H, W)`` float64.

    Old film, auto-exposure hunting and mains-frequency lighting make a clip's
    overall brightness pump frame to frame. Each frame is multiplied by
    ``reference_mean / frame_mean`` (clipped to ``[0, 1]``), and the reference is
    itself a slow exponential of the frame means (``alpha``), so a genuine, gradual
    lighting change is followed while a one-frame flicker is cancelled. The first
    frame sets the reference and passes through unchanged.
    """
    name = "deflicker"

    def __init__(self, alpha: float = 0.1, max_gain: float = 4.0):
        super().__init__()
        self.alpha = _float(alpha, "alpha", 0.0, 1.0)
        self.max_gain = _float(max_gain, "max_gain", 1.0, 1e6)
        self.ref = None

    def _reset(self):
        self.ref = None

    def _update(self, raw):
        f = _to01(raw)
        m = float(f.mean())
        if self.ref is None:
            self.ref = m
            return f.copy()
        gain = self.ref / m if m > 1e-6 else 1.0
        gain = min(max(gain, 1.0 / self.max_gain), self.max_gain)
        out = np.clip(f * gain, 0.0, 1.0)
        self.ref += self.alpha * (m - self.ref)
        return out


class SceneCutDetection(StatefulOp):
    """Shot-boundary detection by histogram distance → ``{"distance", "cut"}`` per frame (``table``).

    Each frame's intensity histogram (``bins`` bins over ``[0, 1]``, area-normalised)
    is compared to the previous frame's with the chi-square distance
    ``½·Σ (h−p)² / (h+p)``. A hard cut makes the histogram jump, so ``distance``
    spikes and ``cut`` is ``True`` when it exceeds ``threshold``. The first frame
    has ``distance`` 0 and ``cut`` ``False``. Robust to motion (which moves pixels
    but keeps the histogram) in a way a raw frame difference is not.
    """
    name = "scene_cut_detection"

    def __init__(self, bins: int = 64, threshold: float = 0.3):
        super().__init__()
        self.bins = _int(bins, "bins", 2, 4096)
        self.threshold = _float(threshold, "threshold", 0.0, 1.0)
        self.prev_hist = None

    def _reset(self):
        self.prev_hist = None

    def _hist(self, f):
        h, _ = np.histogram(f, bins=self.bins, range=(0.0, 1.0), density=True)
        s = h.sum()
        return h / s if s > 0 else h

    def _update(self, raw):
        f = _to01(raw)
        h = self._hist(f)
        if self.prev_hist is None:
            dist, cut = 0.0, False
        else:
            p = self.prev_hist
            denom = h + p
            chi2 = 0.5 * float(np.sum(np.where(denom > 0, (h - p) ** 2 / np.where(denom > 0, denom, 1.0), 0.0)))
            dist, cut = chi2, chi2 > self.threshold
        self.prev_hist = h
        return {"distance": dist, "cut": bool(cut)}


# --------------------------------------------------------------------------- #
# pipeline
# --------------------------------------------------------------------------- #
class VideoPipeline:
    """Chain per-frame facade ops and stateful stages; feed frames one at a time.

    ``stages`` items may be:

    * ``"op_name"`` or ``("op_name", a, b)`` — a registry op applied per frame
      through :func:`api.apply` (``device`` and ``on_error`` are passed on, so
      the GPU path and the fallback ledger behave exactly as for still images);
    * a :class:`StatefulOp` instance (or any object with ``push`` and ``reset``);
    * a plain callable ``f(frame) -> result`` (treated as stateless).

    ``push(frame)`` returns the last stage's result; ``run(frames)`` is a
    generator over an iterable of frames. Integer frames are converted to the
    float64 contract **before the first facade op** (explicitly, once); a
    stateful stage placed first receives the raw integer frame and keeps its
    ring in that dtype. ``stats()`` reports frames, per-stage time, fallbacks
    recorded during the run and the ring memory held by stateful stages.
    """

    def __init__(self, stages, device: str = "cpu", on_error: Optional[str] = None,
                 a: float = 0.5, b: float = 0.5):
        if not isinstance(stages, (list, tuple)) or not stages:
            raise ValueError("stages must be a non-empty list")
        self.device = str(device)
        self.on_error = on_error
        self._stages = []
        for st in stages:
            self._stages.append(self._parse(st, a, b))
        self.frames = 0
        self._t = np.zeros(len(self._stages))
        self._fallbacks_at_start = None
        self._shape = None

    # -- construction ------------------------------------------------------ #
    @staticmethod
    def _parse(st, a, b):
        if isinstance(st, str):
            return ("op", st, float(a), float(b), None)
        if isinstance(st, (tuple, list)) and st and isinstance(st[0], str):
            parts = list(st) + [a, b]
            return ("op", parts[0], float(parts[1]), float(parts[2]), None)
        if hasattr(st, "push") and hasattr(st, "reset"):
            return ("state", getattr(st, "name", type(st).__name__), None, None, st)
        if callable(st):
            return ("fn", getattr(st, "__name__", "callable"), None, None, st)
        raise ValueError("unsupported stage %r" % (st,))

    @property
    def stage_names(self):
        return [s[1] for s in self._stages]

    def reset(self) -> None:
        """Reset every stateful stage and the counters."""
        for kind, _, _, _, obj in self._stages:
            if kind == "state":
                obj.reset()
        self.frames = 0
        self._t[:] = 0.0
        self._shape = None

    # -- execution --------------------------------------------------------- #
    def _record(self, name, exc):
        try:
            import backend_safe as _bs
            _bs.record(name, exc, None, source="stream")
        except Exception:      # noqa: BLE001 - the ledger must never break the stream
            pass

    def push(self, frame):
        import api as _api
        a = _frame(frame)
        if self._shape is None:
            self._shape = a.shape
        elif a.shape != self._shape:
            raise ValueError("frame %r does not match the stream's %r (refused; call reset())"
                             % (a.shape, self._shape))
        x = a
        raise_ = (self.on_error or _api._policy(None)) == "raise"
        for i, (kind, name, sa, sb, obj) in enumerate(self._stages):
            t0 = time.perf_counter()
            if kind == "op":
                if isinstance(x, np.ndarray) and x.dtype.kind in "uib":
                    x = _to01(x)
                x = _api.apply(x, name, sa, sb, device=self.device, on_error=self.on_error)
            elif kind == "state":
                try:
                    x = obj.push(x)
                except Exception as e:      # noqa: BLE001 - reset, record, re-raise under strict
                    obj.reset()
                    self._record(name, e)
                    if raise_:
                        raise
                    x = None
                    self._t[i] += time.perf_counter() - t0
                    break
            else:
                x = obj(x)
            self._t[i] += time.perf_counter() - t0
        self.frames += 1
        return x

    def run(self, frames: Iterable, max_frames: Optional[int] = None):
        """Generator: ``push`` every frame of *frames* (a generator or ``(T, H, W)`` array)."""
        cap = None if max_frames is None else _int(max_frames, "max_frames", 0, 10 ** 9)
        if cap == 0:
            return
        try:
            import backend_safe as _bs
            self._fallbacks_at_start = _bs.fallback_count() if hasattr(_bs, "fallback_count") else None
        except Exception:      # noqa: BLE001
            self._fallbacks_at_start = None
        n = 0
        for fr in frames:
            yield self.push(fr)
            n += 1
            if cap is not None and n >= cap:
                break

    def stats(self) -> dict:
        ring_bytes = sum(getattr(getattr(o, "ring", None), "nbytes", lambda: 0)()
                         for k, _, _, _, o in self._stages if k == "state")
        per = {n: float(t) for n, t in zip(self.stage_names, self._t)}
        total = float(self._t.sum())
        return {"frames": self.frames, "stages": self.stage_names, "seconds_per_stage": per,
                "seconds_total": total,
                "ms_per_frame": 1000.0 * total / self.frames if self.frames else 0.0,
                "fps": self.frames / total if total > 0 else float("inf") if self.frames else 0.0,
                "ring_bytes": int(ring_bytes), "frame_shape": self._shape}


# --------------------------------------------------------------------------- #
# ledger-facing batch functions (= the streaming classes replayed over a clip)
# --------------------------------------------------------------------------- #
def _video(video) -> np.ndarray:
    if isinstance(video, (list, tuple)):
        frames = [np.asarray(f) for f in video]
        if not frames:
            raise ValueError("video is an empty frame list (need T >= 1)")
        shapes = {(f.shape, f.dtype) for f in frames}
        if len(shapes) != 1 or frames[0].ndim != 2:
            raise ValueError("frames must all be the same (H, W) shape and dtype")
        vid = np.stack(frames, axis=0)
    else:
        vid = np.asarray(video)
    if vid.ndim != 3:
        raise ValueError("video must be (T, H, W); got ndim=%d shape=%r" % (vid.ndim, vid.shape))
    if vid.shape[0] < 1:
        raise ValueError("video needs at least one frame (T >= 1)")
    _scale_of(vid.dtype)
    if vid.dtype.kind == "f" and not np.all(np.isfinite(vid)):
        raise ValueError("video contains non-finite samples (NaN/Inf)")
    return vid


def stream_replay(video, op: StatefulOp) -> np.ndarray:
    """Push every frame of *video* ``(T, H, W)`` through *op* and stack the outputs ``(T, H, W)``.

    The bridge between the ledger (whole clips) and the stream (one frame at a
    time): every batch function below is exactly this call, so a result computed
    live equals the registered op's result frame for frame.
    """
    vid = _video(video)
    if not (hasattr(op, "push") and hasattr(op, "reset")):
        raise ValueError("op must be a StatefulOp (push/reset), got %r" % (op,))
    op.reset()
    out = np.empty(vid.shape, np.float64)
    for t in range(vid.shape[0]):
        r = op.push(vid[t])
        if not isinstance(r, np.ndarray) or r.shape != vid.shape[1:]:
            raise ValueError("%s returned %r for a (H, W) frame; stream_replay needs an image per frame"
                             % (getattr(op, "name", op), type(r)))
        out[t] = r
    return out


def temporal_median_window(video, window: int = 5) -> np.ndarray:
    """Causal per-pixel median over the last *window* frames → ``(T, H, W)`` (``video``).

    Frame ``t`` uses frames ``max(0, t−window+1) .. t``. The streaming
    :class:`TemporalMedianWindow` gives the same frames one at a time with a
    ring of *window* frames instead of the whole clip in memory."""
    return stream_replay(video, TemporalMedianWindow(window))


def moving_average_window(video, window: int = 3) -> np.ndarray:
    """Causal per-pixel mean over the last *window* frames → ``(T, H, W)`` (``video``).

    Not the centred :func:`videops.moving_average`: this one never looks ahead,
    which is what a live stream can do."""
    return stream_replay(video, MovingAverageWindow(window))


def background_subtraction_window(video, window: int = 5, threshold: float = 0.1) -> np.ndarray:
    """Causal window-median background → per-frame 0/1 foreground masks ``(T, H, W)`` (``video``)."""
    return stream_replay(video, BackgroundSubtractionWindow(window, threshold))


def frame_difference_causal(video) -> np.ndarray:
    """``|frame t − frame t−1|`` with a zero first frame → ``(T, H, W)`` (``video``).

    Same length as the input (unlike :func:`videops.frame_difference`, ``T−1``),
    so it composes frame-for-frame with the other stream ops."""
    return stream_replay(video, FrameDifference())


def exponential_background(video, alpha: float = 0.05) -> np.ndarray:
    """Recursive background ``bg ← (1−α)·bg + α·frame`` per frame → ``(T, H, W)`` (``video``)."""
    return stream_replay(video, ExponentialBackground(alpha))


def exponential_foreground(video, alpha: float = 0.05, threshold: float = 0.1) -> np.ndarray:
    """Foreground masks ``|frame − exponential background| > threshold`` → 0/1 ``(T, H, W)`` (``video``)."""
    vid = _video(video)
    op = ExponentialBackground(alpha, threshold)
    out = np.empty(vid.shape, np.float64)
    for t in range(vid.shape[0]):
        op.push(vid[t])
        out[t] = op.foreground()
    return out


def running_mean_std(video) -> dict:
    """Welford per-pixel mean / population std over the clip → ``{"mean", "std", "n"}`` (``table``).

    Equals ``video.mean(0)`` / ``video.std(0)`` but needs two images of state,
    not the clip — the streaming form for a recording that never ends."""
    vid = _video(video)
    op = RunningStats()
    r = None
    for t in range(vid.shape[0]):
        r = op.push(vid[t])
    return r


def optical_flow_magnitude_stream(video, **flow_kwargs) -> np.ndarray:
    """Per-frame dense flow speed against the previous frame → ``(T, H, W)`` (``video``).

    Zero first frame; frames ``1..T−1`` equal :func:`videops.optical_flow_sequence`
    shifted by one, computed with one frame of state."""
    return stream_replay(video, OpticalFlowStream(**flow_kwargs))
