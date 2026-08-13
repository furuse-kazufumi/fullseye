"""3D Gaussian Splatting (3DGS) output -> fullseye point-cloud processing.

A 3DGS reconstruction produces a set of 3-D Gaussian *centres* (a dense point
cloud, exportable to .ply). Fullseye does not *train* a splat model (that needs a
GPU renderer); it consumes the result — the point cloud — with its geometry stack:
downsample, estimate surface normals (grasp / rendering-normal use), and register
two captures into one frame. This is the bridge from a Physical-AI 3DGS scan to
measurement and manipulation.

Runs on a *synthetic* splat cloud (Gaussian centres sampled on a curved surface),
so it is self-contained. Swap in a real ``points`` array loaded from your 3DGS
.ply export.

    py -3.11 examples/gaussian_splat_cloud.py [--save out_dir]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fullseye as fs


def synthetic_splat_cloud(n=4000, seed=0):
    """Gaussian-splat centres sampled on a bumpy surface (what a 3DGS export of a
    small object looks like as a point cloud), with per-point jitter."""
    rng = np.random.default_rng(seed)
    u = rng.uniform(-1, 1, n)
    v = rng.uniform(-1, 1, n)
    z = 0.3 * np.sin(3 * u) * np.cos(3 * v)               # a curved surface
    pts = np.stack([u, v, z], axis=1)
    pts += 0.01 * rng.standard_normal(pts.shape)          # splat jitter
    return pts


def run(save_dir=None):
    pts = synthetic_splat_cloud()

    # 1) downsample the dense splat cloud (bounds cost, evens density)
    small = fs.voxel_downsample(pts, voxel=0.05)

    # 2) surface normals (per-point orientation — grasp approach / relighting)
    normals = fs.estimate_normals(small, k=12, viewpoint=(0.0, 0.0, 5.0))

    # 3) register a second capture (rotated + translated) back onto the first
    ang = np.deg2rad(20.0)
    R = np.array([[np.cos(ang), -np.sin(ang), 0], [np.sin(ang), np.cos(ang), 0], [0, 0, 1.0]])
    moved = small @ R.T + np.array([0.15, -0.1, 0.05])
    R_est, t_est, aligned, rmse = fs.register(moved, small, trim=0.2)

    result = {
        "n_splats": len(pts),
        "n_downsampled": len(small),
        "normals_unit": round(float(np.abs(np.linalg.norm(normals, axis=1) - 1).max()), 4),
        "register_rmse": round(float(rmse), 5),
    }
    print("[3dgs] " + "  ".join(f"{k}={v}" for k, v in result.items()))

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        fs.save_ply(os.path.join(save_dir, "splat_downsampled.ply"), small)
        fs.save_ply(os.path.join(save_dir, "registered.ply"), aligned)
        print(f"[3dgs] wrote downsampled + registered PLY clouds -> {save_dir}")
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--save", default=None)
    a = ap.parse_args()
    run(save_dir=a.save)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
