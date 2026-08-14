"""Event-camera (neuromorphic) vision from ordinary frames — events.py facade.

Event / DVS cameras report asynchronous per-pixel brightness-change events with
microsecond latency — the sensing modality behind low-latency robotics and
high-speed manipulation. This demo turns a pair (and a short clip) of ordinary
frames into the standard event representations, and recovers global motion by
contrast maximisation. A Fullseye consumer (onocollo / evis / hillco physics
clips) with only rendered frames can prototype an event pipeline this way.

Run:  py -3.11 examples/event_camera.py
Smoke test: it prints an honest one-line summary per representation. Exit 0 means
every step produced a finite, shaped result and contrast maximisation recovered
the injected motion.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fullseye  # noqa: E402


def _textured_scene(n: int = 80) -> np.ndarray:
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    img = np.full((n, n), 0.3)
    img[(yy - 0.4 * n) ** 2 + (xx - 0.4 * n) ** 2 < (0.18 * n) ** 2] = 0.85   # disk
    img += 0.12 * np.sin(xx / 3.0) * np.cos(yy / 4.0)                          # texture
    return np.clip(img, 0.0, 1.0)


def main() -> int:
    base = _textured_scene()
    # the scene moves down-right by (vy, vx) = (1, 2) px per frame
    vy0, vx0 = 1, 2
    clip = np.stack([ndimage.shift(base, (t * vy0, t * vx0), order=1, mode="reflect")
                     for t in range(5)])
    prev, nxt = clip[0], clip[1]

    print("== per-pixel events between two frames ==")
    ev = fullseye.simulate_events(prev, nxt, thr=0.1)
    on = int((ev > 0).sum()); off = int((ev < 0).sum())
    print(f"  simulate_events   ON(+1)={on}  OFF(-1)={off}  (ON where brighter, OFF where darker)")
    iwe = fullseye.event_image(prev, nxt, thr=0.1)
    print(f"  event_image (IWE) shape={iwe.shape}  range=[{iwe.min():.2f},{iwe.max():.2f}]")
    print(f"  event_rate        {fullseye.event_rate(prev, nxt, thr=0.1):.3f}  (fraction of pixels firing)")

    print("== time surface (Surface of Active Events) over the 5-frame clip ==")
    sae = fullseye.time_surface(clip, tau=2.0, thr=0.1)
    print(f"  time_surface      shape={sae.shape}  mean(active)={sae[sae > 0].mean():.3f}  (recent=high, old=low)")

    print("== contrast maximisation: recover the global optic flow ==")
    cm = fullseye.contrast_maximization(clip, max_v=4, thr=0.08)
    ok = (cm["vy"], cm["vx"]) == (float(vy0), float(vx0))
    print(f"  injected velocity (vy,vx) = ({vy0},{vx0})  per frame")
    print(f"  recovered         (vy,vx) = ({cm['vy']:.0f},{cm['vx']:.0f})  contrast={cm['contrast']:.3f}  "
          f"{'OK' if ok else 'MISMATCH'}")
    print(f"  sharpened IWE     shape={cm['iwe'].shape}  range=[{cm['iwe'].min():.2f},{cm['iwe'].max():.2f}]")

    assert ok, "contrast maximisation did not recover the injected motion"
    print("\nevents facade OK. Feed a real clip via fullseye.read_frames(<mp4/gif>).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
