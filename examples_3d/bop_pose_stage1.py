"""Synthetic, redistributable example for BOP stage-1 pose plumbing.

No ITODD image, depth, point cloud, CAD rendering or derived visualization is
created.  The assertions use an analytic point set with known signed rotation and
translation, then exercise ``ppf_pose_hypotheses`` → ``pose_nms_symmetry`` and
the BOP CSV round trip.

BOP 第1段の合成例。ITODD の画像・深度・点群・CAD 描画・派生可視化は作らず、
解析的な点集合の符号付き真値を assert する。
"""
from __future__ import annotations

import math
from pathlib import Path
import tempfile

import numpy as np

import fullseye as fs


def _rotation(axis, degrees):
    """Build a signed axis-angle rotation. / 符号付き軸角回転を作る。"""
    axis = np.asarray(axis, np.float64)
    axis /= np.linalg.norm(axis)
    angle = math.radians(degrees)
    skew = np.array([[0.0, -axis[2], axis[1]], [axis[2], 0.0, -axis[0]],
                     [-axis[1], axis[0], 0.0]])
    return np.eye(3) + math.sin(angle) * skew + (1.0 - math.cos(angle)) * skew @ skew


def main():
    """Run the self-checking synthetic example. / 自己検査する合成例を実行する。"""
    grid = np.linspace(0.0, 1.0, 6)
    model_points = np.array([(3.0*x, 2.0*y, 0.2*x*y + 0.1*x*x)
                             for x in grid for y in grid])
    model_normals = model_points - model_points.mean(axis=0)
    model_normals /= np.linalg.norm(model_normals, axis=1)[:, None]
    rotation_true = _rotation((0.4, -0.2, 1.0), -38.0)
    translation_true = np.array([-0.35, 0.6, 1.4])
    scene_points = model_points @ rotation_true.T + translation_true
    scene_normals = model_normals @ rotation_true.T

    descriptor = fs.ppf_model(model_points, model_normals, angle_bins=30)
    candidates = fs.ppf_pose_hypotheses(
        descriptor, scene_points, scene_normals, top_n=5,
        ref_fraction=0.6, seed=7)
    diverse = fs.pose_nms_symmetry(
        candidates, model_points, symmetries=(), distance_threshold=1e-5)
    best = diverse[0]
    rotation_error_deg = math.degrees(math.acos(np.clip(
        (np.trace(best.R.T @ rotation_true) - 1.0) / 2.0, -1.0, 1.0)))
    translation_error = float(np.linalg.norm(best.t - translation_true))
    assert rotation_error_deg < 0.2
    assert translation_error < 1e-5
    assert best.votes > 0 and best.inlier_fraction > 0.99

    row = fs.BOPPoseEstimate(
        scene_id=1, im_id=0, obj_id=1, score=best.score,
        R=best.R, t=100.0 * best.t, time=0.01)  # explicit synthetic mm conversion
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "synthetic_itodd-val.csv"
        fs.write_bop_results_csv(path, [row])
        assert fs.read_bop_results_csv(path) == [row]

    print("PASS synthetic pose: rotation_error_deg=%.9f "
          "translation_error=%.9f candidates=%d"
          % (rotation_error_deg, translation_error, len(candidates)))


if __name__ == "__main__":
    main()
