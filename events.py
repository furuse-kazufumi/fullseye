"""events.py — neuromorphic / event-camera vision from conventional frames.

Event (DVS / DAVIS) cameras report asynchronous per-pixel brightness-change
*events* with microsecond latency instead of synchronous frames — the sensing
modality behind low-latency robotics, high-speed manipulation and high-dynamic-
range perception, and one of the clearest "next decade" Physical-AI trends. This
module derives the same representations from a pair (or a short stack) of ordinary
frames, so a Fullseye consumer that only has RGB / rendered frames (onocollo /
evis / hillco physics clips) can still prototype an event-based pipeline. It is a
frame->event model (v2e-style) implemented in plain numpy — no learned simulator.

Model: an event fires at a pixel when the change in LOG intensity since the last
frame crosses a contrast threshold C; the event polarity is the sign of the change
(ON = brighter, OFF = darker). From that we build:

  simulate_events        signed polarity map (ON/OFF/none) between two frames
  event_count            signed multi-event count (how many C-crossings, w/ sign)
  event_image            accumulated event image (IWE) for display / downstream
  event_rate             global activity fraction (scalar) + event_rate_map
  time_surface           Surface of Active Events (SAE) over a (T,H,W) stack
  contrast_maximization  global-motion estimate that SHARPENS the event image by
                         warping events along the true optic flow (Gallego 2018)
  warp_frame             integer/sub-pixel frame shift (compensation primitive)

All functions take 2-D float64 frames in [0,1] (or a (T,H,W) stack), return finite
and deterministic outputs, and are fail-soft on degenerate input. Honest limit:
from only 2 frames the "time surface" and contrast-maximisation see a single
interval, so they approximate what a true async event stream resolves in time.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

_EPS = 1e-3


def _img(v):
    """Coerce to a finite 2-D float64 image in [0,1]."""
    x = np.asarray(v, np.float64)
    if x.ndim == 3:
        x = x.mean(axis=-1)
    elif x.ndim != 2:
        x = np.atleast_2d(x).astype(np.float64)
    x = np.nan_to_num(x, nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(x, 0.0, 1.0)


def _log(x, eps):
    return np.log(np.clip(x, 0.0, 1.0) + eps)


def _delta_log(prev, nxt, eps):
    """Log-intensity change (the DVS event driver), on matched HxW frames."""
    p, n = _img(prev), _img(nxt)
    if p.shape != n.shape:
        n = _resize(n, p.shape[0], p.shape[1])
    return _log(n, eps) - _log(p, eps), p.shape


def _resize(x, H, W):
    x = np.asarray(x, np.float64)
    h, w = x.shape[:2]
    if (h, w) == (H, W):
        return x.copy()
    if h < 1 or w < 1:
        return np.zeros((H, W), np.float64)
    rr = np.linspace(0.0, h - 1, H)
    cc = np.linspace(0.0, w - 1, W)
    R, C = np.meshgrid(rr, cc, indexing="ij")
    return ndimage.map_coordinates(x, np.vstack([R.ravel(), C.ravel()]),
                                   order=1, mode="nearest").reshape(H, W)


def _thr(c):
    """Map a knob-style threshold to a sane contrast threshold in log-units."""
    return float(max(1e-3, c))


# --------------------------------------------------------------------------- #
# core event representations                                                  #
# --------------------------------------------------------------------------- #
def simulate_events(prev, nxt, thr=0.1, eps=_EPS):
    """Signed event-polarity map between two frames.

    Fires ON (+1) where log-intensity rose by >= ``thr``, OFF (-1) where it fell
    by >= ``thr``, 0 otherwise — the pixel-level DVS model. Returns a float64 HxW
    array with values in {-1, 0, +1}.
    """
    d, _ = _delta_log(prev, nxt, eps)
    thr = _thr(thr)
    return np.where(d >= thr, 1.0, np.where(d <= -thr, -1.0, 0.0))


def event_count(prev, nxt, thr=0.1, eps=_EPS):
    """Signed number of contrast crossings per pixel: ``sign(d) * floor(|d|/thr)``.

    A DVS pixel emits one event per ``thr`` of log-change, so a large jump yields
    several same-polarity events. Returns a float64 HxW array (…,-2,-1,0,1,2,…).
    """
    d, _ = _delta_log(prev, nxt, eps)
    thr = _thr(thr)
    return np.sign(d) * np.floor(np.abs(d) / thr)


def event_image(prev, nxt, thr=0.1, eps=_EPS, polarity="both", normalize=True):
    """Accumulated event image (the classic 'image of warped events', IWE).

    ``polarity``: ``"on"`` (ON count), ``"off"`` (OFF count), ``"signed"`` (ON-OFF),
    or ``"both"`` (|ON|+|OFF| activity, default). With ``normalize`` the output is
    min-max scaled to [0,1] for display / as a Fullseye image; otherwise raw counts.
    """
    c = event_count(prev, nxt, thr, eps)
    if polarity == "on":
        out = np.clip(c, 0, None)
    elif polarity == "off":
        out = np.clip(-c, 0, None)
    elif polarity == "signed":
        out = c
    else:
        out = np.abs(c)
    if not normalize:
        return out.astype(np.float64)
    lo, hi = float(out.min()), float(out.max())
    if hi - lo <= 1e-12:
        return np.zeros_like(out, np.float64)
    return ((out - lo) / (hi - lo)).astype(np.float64)


def event_rate(prev, nxt, thr=0.1, eps=_EPS):
    """Global event activity = fraction of pixels that fired at least one event
    (a scalar in [0,1]). High rate = fast / textured motion."""
    e = simulate_events(prev, nxt, thr, eps)
    return float(np.mean(e != 0.0))


def event_rate_map(prev, nxt, thr=0.1, eps=_EPS, sigma=2.0):
    """Local event-density map: the fired-pixel mask smoothed to a [0,1] activity
    field (where in the frame the motion/texture is)."""
    e = (simulate_events(prev, nxt, thr, eps) != 0.0).astype(np.float64)
    if sigma > 1e-6:
        e = ndimage.gaussian_filter(e, sigma=float(sigma), mode="nearest")
    return np.clip(e, 0.0, 1.0)


def time_surface(frames, tau=2.0, thr=0.1, eps=_EPS):
    """Surface of Active Events (SAE) over a (T,H,W) stack.

    For each pixel, the time-since-last-event decays exponentially: a pixel that
    fired in the most recent frame is ~1, one that fired long ago is ~0, one that
    never fired is 0. ``tau`` is the decay constant in frames. Returns an HxW map
    in [0,1] — the standard low-latency event representation for corner/flow front
    ends. With only two frames this reduces to the last interval's event mask.
    """
    f = np.asarray(frames, np.float64)
    if f.ndim != 3 or f.shape[0] < 2:
        raise ValueError("time_surface needs a (T,H,W) stack with T>=2")
    T, H, W = f.shape
    last = np.full((H, W), -np.inf, np.float64)   # last event time per pixel
    for t in range(1, T):
        fired = simulate_events(f[t - 1], f[t], thr, eps) != 0.0
        last[fired] = float(t)
    age = float(T - 1) - last                       # frames since last event
    sae = np.where(np.isfinite(last), np.exp(-age / max(tau, 1e-6)), 0.0)
    return np.clip(sae, 0.0, 1.0)


# --------------------------------------------------------------------------- #
# contrast maximisation (event-based global motion)                           #
# --------------------------------------------------------------------------- #
def warp_frame(frame, dy, dx):
    """Shift a frame by (dy,dx) pixels (bilinear, reflect) — the compensation
    primitive. Positive dy/dx move content down/right."""
    x = _img(frame)
    return np.clip(ndimage.shift(x, (float(dy), float(dx)), order=1, mode="reflect"), 0.0, 1.0)


def contrast_maximization(frames, max_v=4, thr=0.1, eps=_EPS):
    """Estimate the global optic flow by CONTRAST MAXIMISATION (Gallego et al. 2018).

    The event-vision principle: the true motion is the one that, when used to warp
    every event back to a common reference time, piles the events from a moving edge
    onto ONE sharp curve — maximising the CONTRAST (variance) of the accumulated
    "image of warped events" (IWE). Here the motion is a constant global translation
    ``(vy, vx)`` pixels/frame, searched over integers in ``[-max_v, max_v]^2`` over a
    ``(T, H, W)`` stack: each interval's events (fired at end-time ``t``) are warped
    back to ``t = 0`` by ``-(t·vy, t·vx)`` and summed; the sharpest sum wins.

    Returns ``{"vy", "vx", "contrast", "iwe"}`` — the recovered per-frame velocity,
    the winning IWE variance, and the sharpened event image in [0,1]. Ground truth:
    for ``frames[t] = shift(base, t·vy0, t·vx0)`` it recovers ``(vy0, vx0)``.

    Honest limit: a constant global translation (no rotation / per-region flow) on an
    integer velocity grid; T>=3 disambiguates the blur (T=2 sees a single interval,
    so any velocity of the right displacement scores alike — pass a real short clip).
    """
    f = np.asarray(frames, np.float64)
    if f.ndim != 3 or f.shape[0] < 2:
        raise ValueError("contrast_maximization needs a (T,H,W) stack with T>=2")
    T, H, W = f.shape
    ev = [(t, event_count(f[t - 1], f[t], thr, eps)) for t in range(1, T)]
    mv = int(max(0, min(max_v, (min(H, W) - 1) // max(T - 1, 1))))

    def _iwe(vy, vx):
        acc = np.zeros((H, W), np.float64)
        for t, e in ev:
            acc += ndimage.shift(e, (-t * vy, -t * vx), order=1, mode="constant", cval=0.0)
        return acc

    best = {"vy": 0.0, "vx": 0.0, "contrast": -1.0}
    for vy in range(-mv, mv + 1):
        for vx in range(-mv, mv + 1):
            score = float(np.var(_iwe(vy, vx)))
            if score > best["contrast"]:
                best = {"vy": float(vy), "vx": float(vx), "contrast": score}
    raw = np.abs(_iwe(best["vy"], best["vx"]))
    lo, hi = float(raw.min()), float(raw.max())
    best["iwe"] = ((raw - lo) / (hi - lo)) if hi - lo > 1e-12 else np.zeros((H, W), np.float64)
    return best
