"""Run the stage-1 PPF plumbing on selected public ITODD validation frames.

The script writes only a BOP result CSV and a validation target JSON.  It never
writes an image, point cloud, mesh, rendering or derived visualization.  Target
object IDs and instance counts come from validation ground truth, matching the
information supplied in a BOP localization target list; poses are not used by
the inference path.  Test split input is not accepted.

選んだ公開 ITODD val フレームで第1段の端から端までを流す。出力は数値 CSV と
val target JSON だけで、画像・点群・CAD・派生可視化は書かない。正解姿勢は推論に
使わず、BOP target 相当の物体 ID と個数だけを val 正解から作る。test は受けない。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import numpy as np

import fullseye as fs


SCENE_ID = 1
SCENE_VOXEL_MM = 4.0
MAX_SCENE_POINTS = 2500
SCENE_REFERENCE_COUNT = 36
MIN_TOP_N = 3
HYPOTHESES_PER_INSTANCE = 3
NMS_DIAMETER_FRACTION = 0.05
PPF_ANGLE_BINS = 24
RANDOM_SEED = 20261123


def _scene_sample(points, normals):
    """Deterministic first-per-voxel sample. / 決定的な各 voxel 先頭サンプル。"""
    points = np.asarray(points, np.float64)
    normals = np.asarray(normals, np.float64)
    cells = np.floor(points / SCENE_VOXEL_MM).astype(np.int64)
    _unique, first = np.unique(cells, axis=0, return_index=True)
    first.sort()
    if first.size > MAX_SCENE_POINTS:
        rng = np.random.default_rng(RANDOM_SEED)
        first = np.sort(rng.choice(first, MAX_SCENE_POINTS, replace=False))
    return points[first], normals[first]


def run(dataset_root: Path, image_ids, output_csv: Path, targets_filename: str):
    target_path = fs.write_bop_val_targets(
        dataset_root, {SCENE_ID: image_ids}, filename=targets_filename)
    targets = json.loads(target_path.read_text(encoding="utf-8"))
    targets_by_image = {}
    for target in targets:
        targets_by_image.setdefault(target["im_id"], []).append(target)
    model_info = fs.read_bop_models_info(dataset_root)
    estimates = []
    timings = {}

    for im_id in image_ids:
        start = time.perf_counter()
        frame = fs.read_bop_scene_image(dataset_root, "val", SCENE_ID, im_id)
        scene_points, scene_normals = _scene_sample(frame["points_mm"], frame["normals"])
        pending = []
        for target in targets_by_image[im_id]:
            obj_id = target["obj_id"]
            instance_count = target["inst_count"]
            model_points, _faces = fs.read_bop_model(dataset_root, obj_id)
            descriptor = fs.ppf_model(model_points, angle_bins=PPF_ANGLE_BINS)
            top_n = max(MIN_TOP_N, HYPOTHESES_PER_INSTANCE * instance_count)
            ref_fraction = min(1.0, SCENE_REFERENCE_COUNT / len(scene_points))
            try:
                hypotheses = fs.ppf_pose_hypotheses(
                    descriptor, scene_points, scene_normals,
                    top_n=top_n, ref_fraction=ref_fraction,
                    seed=RANDOM_SEED + im_id + obj_id)
            except ValueError as exc:
                if "no votes" not in str(exc):
                    raise
                continue
            diameter = float(model_info[obj_id]["diameter"])
            symmetries = fs.bop_symmetry_transforms(
                model_info[obj_id], max_step=0.01 * diameter)
            diverse = fs.pose_nms_symmetry(
                hypotheses, model_points, symmetries,
                distance_threshold=NMS_DIAMETER_FRACTION * diameter,
                top_n=instance_count)
            pending.extend((obj_id, pose) for pose in diverse)
        elapsed = time.perf_counter() - start
        timings[im_id] = elapsed
        estimates.extend(fs.BOPPoseEstimate(
            scene_id=SCENE_ID, im_id=im_id, obj_id=obj_id,
            score=pose.score, R=pose.R, t=pose.t, time=elapsed)
            for obj_id, pose in pending)
        print("val scene=%d image=%d points=%d estimates=%d seconds=%.6f"
              % (SCENE_ID, im_id, len(scene_points), len(pending), elapsed))

    fs.write_bop_results_csv(output_csv, estimates)
    print("wrote %d rows to %s; total_seconds=%.6f" %
          (len(estimates), output_csv, sum(timings.values())))
    return estimates, timings, target_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dataset_root", type=Path,
                        help="local extracted ITODD root containing val/ and models/")
    parser.add_argument("output_csv", type=Path,
                        help="numeric-only result path, e.g. fullseye_itodd-val.csv")
    parser.add_argument("--image-ids", default="0,15",
                        help="comma-separated public validation image IDs")
    parser.add_argument("--targets-filename", default="val_targets_stage1.json")
    args = parser.parse_args(argv)
    image_ids = [int(value) for value in args.image_ids.split(",") if value.strip()]
    if not image_ids:
        parser.error("--image-ids must contain at least one ID")
    run(args.dataset_root.resolve(), image_ids, args.output_csv.resolve(),
        args.targets_filename)


if __name__ == "__main__":
    main()
