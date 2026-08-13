"""End-to-end object pose for grasping: an observed point cloud (noisy, partial,
displaced) is registered to a known model to recover its 6-DoF pose, and per-point
surface normals give candidate grasp approach directions.

A template for manipulation: swap the synthetic model for your CAD/reference cloud
and the observed cloud for a depth-camera / stereo reconstruction
(:mod:`stereo` -> :func:`reproject_to_points`). Runs on synthetic data, no files.

    py -3.11 examples/grasp_pose.py [--save out_dir]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fullseye as fs


def _rot(ax, ay, az):
    cx, sx = np.cos(ax), np.sin(ax)
    cy, sy = np.cos(ay), np.sin(ay)
    cz, sz = np.cos(az), np.sin(az)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def synthetic_model(n=1200, seed=0):
    """An anisotropic 'part' (ellipsoid surface) standing in for a CAD model."""
    v = np.random.default_rng(seed).standard_normal((n, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    return v * np.array([1.0, 0.6, 0.45])


def run(save_dir=None):
    model = synthetic_model()
    R0 = _rot(0.15, 0.35, -0.2)                        # true object pose
    t0 = np.array([0.4, -0.25, 0.15])
    rng = np.random.default_rng(1)
    observed = fs.registration.apply_transform(model, R0, t0)
    observed = observed[rng.random(len(observed)) > 0.25]      # partial view (~75%)
    observed = observed + rng.normal(0, 0.004, observed.shape)  # sensor noise

    obs_ds = fs.voxel_downsample(observed, voxel=0.03)          # thin before ICP
    normals = fs.estimate_normals(obs_ds, k=16, viewpoint=(0, 0, 0))  # grasp directions
    R, t, aligned, rmse = fs.register(obs_ds, model, trim=0.15)  # observed -> model pose

    rot_err = float(np.degrees(np.arccos(np.clip((np.trace(R @ R0) - 1) / 2, -1, 1))))
    result = {
        "n_model": len(model),
        "n_observed": len(observed),
        "n_downsampled": len(obs_ds),
        "rmse": round(rmse, 4),
        "rot_error_deg": round(rot_err, 3),
    }
    print("[grasp] " + "  ".join(f"{k}={v}" for k, v in result.items()))

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        fs.save_ply(os.path.join(save_dir, "model.ply"), model)
        fs.save_ply(os.path.join(save_dir, "observed.ply"), observed)
        fs.save_ply(os.path.join(save_dir, "aligned.ply"), aligned)
        print(f"[grasp] wrote model/observed/aligned PLY (+{len(normals)} normals) -> {save_dir}")
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--save", default=None, help="directory to write PLY clouds")
    a = ap.parse_args()
    run(save_dir=a.save)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
