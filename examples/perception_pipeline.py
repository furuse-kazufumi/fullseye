"""End-to-end perception pipeline: a rectified stereo pair -> depth -> point cloud
-> terrain heightmap -> traversability, with a colourised export.

A template another project (robot locomotion / manipulation) can copy: swap the
synthetic pair for real rectified frames and the world transform for your camera
extrinsics. Runs on synthetic data with no external files.

    py -3.11 examples/perception_pipeline.py [--save out_dir]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fullseye as fs


def synthetic_stereo(h=90, w=140, ground_disp=4, box_disp=10, seed=0):
    """A rectified pair: flat ground at `ground_disp`, a nearer box at `box_disp`."""
    from scipy import ndimage
    rng = np.random.default_rng(seed)
    left = np.clip(ndimage.gaussian_filter(rng.random((h, w)), 1.1), 0, 1)

    def shift(img, d):
        r = np.empty_like(img)
        r[:, : w - d] = img[:, d:]
        r[:, w - d :] = img[:, -1:]
        return r

    right = shift(left, ground_disp).copy()
    right[h // 3 : 2 * h // 3, w // 3 : 2 * w // 3] = \
        shift(left, box_disp)[h // 3 : 2 * h // 3, w // 3 : 2 * w // 3]
    return left, right


def run(save_dir=None, focal=100.0, baseline=0.10):
    left, right = synthetic_stereo()

    disp = fs.disparity_map(left, right, max_disp=16, block=9, method="sad")
    depth = fs.depth_from_disparity(disp, focal=focal, baseline=baseline)
    pts = fs.reproject_to_points(depth, fx=focal, fy=focal)

    # camera frame (X right, Y down, Z forward) -> a world frame with z up
    world = np.stack([pts[:, 0], pts[:, 2], -pts[:, 1]], axis=1)
    grid, extent = fs.elevation_map(world, cell=0.5, agg="max")
    walkable = fs.traversability(grid, cell=0.5, max_step=0.3, max_slope=2.0)

    result = {
        "disparity_median": float(np.median(disp)),
        "depth_valid_frac": float(np.isfinite(depth).mean()),
        "n_points": int(len(pts)),
        "grid_shape": tuple(grid.shape),
        "walkable_frac": float(np.mean(walkable)),
    }
    print("[perception] " + "  ".join(f"{k}={v}" for k, v in result.items()))

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        fs.save(os.path.join(save_dir, "disparity.png"), fs.colorize_disparity(disp))
        fs.save(os.path.join(save_dir, "depth.png"), fs.colorize_depth(depth))
        fs.save(os.path.join(save_dir, "heightmap.png"), fs.apply_cmap(grid))
        fs.save(os.path.join(save_dir, "walkable.png"), walkable.astype(float))
        fs.save_ply(os.path.join(save_dir, "cloud.ply"), pts)
        print(f"[perception] wrote disparity/depth/heightmap/walkable PNGs + cloud.ply -> {save_dir}")
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--save", default=None, help="directory to write colourised outputs + PLY")
    a = ap.parse_args()
    run(save_dir=a.save)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
