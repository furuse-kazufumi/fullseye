"""End-to-end motion analysis: two frames -> dense optical flow -> global-motion
removal -> independently-moving regions, with a colourised flow export.

A template for reading motion out of a video pair — onocollo physics clips (did
that object actually move, or did the whole scene drift?) or evis / hillco body
language (which limb moved). Runs on synthetic data with no external files.

    py -3.11 examples/motion_analysis.py [--save out_dir]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fullseye as fs


def _blob(shape, cy, cx, sigma=6.0, amp=0.8):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    return amp * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * sigma ** 2))


def synthetic_pair(h=112, w=144, global_motion=(1.5, 0.0),
                   object_motion=(0.0, 5.0), seed=0):
    """A textured background that drifts by *global_motion* between the two frames,
    plus a bright object that additionally moves by *object_motion*."""
    rng = np.random.default_rng(seed)
    base = np.clip(ndimage.gaussian_filter(rng.random((h, w)), 1.3), 0, 1)
    c0 = (h // 2, w // 2)
    gx, gy = global_motion
    ox, oy = object_motion
    prev = np.clip(base + _blob((h, w), c0[0], c0[1]), 0, 1)
    bg1 = ndimage.shift(base, (gy, gx), order=1, mode="nearest")
    nxt = np.clip(bg1 + _blob((h, w), c0[0] + gy + oy, c0[1] + gx + ox), 0, 1)
    return prev, nxt


def run(save_dir=None):
    prev, nxt = synthetic_pair()
    u, v = fs.optical_flow_lk(prev, nxt, window=15, levels=3, iters=5)
    energy = fs.frame_motion_energy(u, v)
    M = fs.dominant_motion(u, v)                       # robust global (camera) motion
    mask, segs = fs.motion_segments(u, v, threshold=2.0, min_area=25)

    result = {
        "motion_energy": round(energy, 4),
        "global_u": round(float(M[0, 0]), 3),
        "global_v": round(float(M[1, 0]), 3),
        "n_moving_segments": len(segs),
        "largest_segment_area": segs[0]["area"] if segs else 0,
    }
    print("[motion] " + "  ".join(f"{k}={v}" for k, v in result.items()))

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        fs.save(os.path.join(save_dir, "flow.png"), fs.colorize_flow(u, v))
        ru, rv = fs.residual_motion(u, v)
        fs.save(os.path.join(save_dir, "residual_flow.png"), fs.colorize_flow(ru, rv))
        fs.save(os.path.join(save_dir, "moving_mask.png"), mask.astype(float))
        print(f"[motion] wrote flow/residual_flow/moving_mask PNGs -> {save_dir}")
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--save", default=None, help="directory to write colourised outputs")
    a = ap.parse_args()
    run(save_dir=a.save)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
