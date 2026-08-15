"""Memory cost of the current object model vs the proposed ObjectSet.

`connection` in fscript.py returns ``[(lbl == i) for i in range(1, k+1)]`` — one
full-frame boolean mask per blob.  Every per-object feature (`area`,
`area_center`, `select_shape`) then scans a full frame again.  Both the memory
and the time therefore grow as O(blobs x H x W) instead of O(H x W).

This is a *data-model* cost, not a Python cost: a native rewrite of the same
model would pay the same asymptotics.  That distinction decides whether "go
native" or "fix the object model" is the right answer, so it is measured.

Run:  py -3.11 tools/bench_objectset_memory.py
"""
from __future__ import annotations

import sys
import time
import tracemalloc
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bench_realtime import make_scene, MIN_AREA  # noqa: E402


def current_model(reg):
    """The pre-I2 object model: one full-frame boolean mask per connected
    component, then a full-frame scan per feature.  fscript no longer does this
    (it uses ObjectSet since I-2), but this is the model the comparison motivated,
    so it is kept inline as the baseline rather than removed."""
    lbl, k = ndi.label(reg)
    masks = [(lbl == i) for i in range(1, k + 1)]            # k full-frame masks
    kept = [m for m in masks if m.sum() >= MIN_AREA]         # k full-frame scans
    cents = [(float(ys.mean()), float(xs.mean()))
             for m in kept for ys, xs in [np.nonzero(m)]]
    return len(kept), cents


def objectset_model(reg):
    """Label image + id list; features vectorised over the label image."""
    lbl, k = ndi.label(reg)
    if k == 0:
        return 0, []
    idx = np.arange(1, k + 1)
    areas = ndi.sum_labels(reg, lbl, index=idx)
    keep = idx[areas >= MIN_AREA]
    cents = ndi.center_of_mass(reg, lbl, keep) if keep.size else []
    return int(keep.size), list(cents)


def run(h, w, blobs):
    img = make_scene(h, w, blobs)
    sm = ndi.gaussian_filter(img, 1.5)
    reg = (sm >= 0.5) & (sm <= 1.0)
    frame_mb = h * w / 1024 / 1024          # bool = 1 byte/px

    out = []
    for name, fn in (("current (mask per blob)", current_model),
                     ("ObjectSet (label image)", objectset_model)):
        fn(reg)                              # warm
        tracemalloc.start()
        t0 = time.perf_counter()
        n, _ = fn(reg)
        dt = (time.perf_counter() - t0) * 1000.0
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        out.append((name, dt, peak / 1024 / 1024, n))

    print("--- %dx%d, %d blobs (1 frame mask = %.1f MB) ---" % (h, w, blobs, frame_mb))
    for name, dt, peak_mb, n in out:
        print("  %-26s %8.1f ms   peak %8.1f MB   kept=%d" % (name, dt, peak_mb, n))
    speed = out[0][1] / max(1e-9, out[1][1])
    mem = out[0][2] / max(1e-9, out[1][2])
    print("  -> ObjectSet is %.1fx faster, %.1fx less peak memory\n" % (speed, mem))
    return out


def main():
    for cfg in [(512, 512, 25), (1024, 1024, 50), (2048, 2048, 50), (2048, 2048, 200)]:
        run(*cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
