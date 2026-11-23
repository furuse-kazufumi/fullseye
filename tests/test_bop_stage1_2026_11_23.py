"""Stage-1 BOP gates use synthetic data only; no ITODD assets enter the repository."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial import cKDTree

import bop
import ppf


def _rotation(axis, degrees):
    axis = np.asarray(axis, np.float64)
    axis /= np.linalg.norm(axis)
    angle = math.radians(degrees)
    skew = np.array([[0.0, -axis[2], axis[1]], [axis[2], 0.0, -axis[0]],
                     [-axis[1], axis[0], 0.0]])
    return np.eye(3) + math.sin(angle) * skew + (1.0 - math.cos(angle)) * skew @ skew


def _part():
    grid = np.linspace(0.0, 1.0, 6)
    base = np.array([(3.0*x, 2.0*y, 0.15*x*y) for x in grid for y in grid])
    wall = np.array([(0.2*x, 2.0*y, 1.3*z) for x in (0.0, 1.0)
                     for y in grid for z in grid[1:]])
    points = np.vstack((base, wall))
    normals = points - points.mean(axis=0)
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    return points, normals


def _hypothesis(rotation, translation, score, votes):
    return ppf.PoseHypothesis(rotation, np.asarray(translation, float), votes, score,
                              score, 0.1)


def test_bop_pose_csv_round_trip_is_exact_and_units_are_mm(tmp_path):
    rotation = _rotation((0.2, -0.4, 1.0), -37.0)
    rows = [
        bop.BOPPoseEstimate(1, 7, 2, 0.75, rotation,
                            np.array([-12.5, 3.25, 701.125]), 0.03125),
        bop.BOPPoseEstimate(1, 7, 2, -0.125, np.eye(3),
                            np.array([9.0, -8.0, 700.0]), 0.03125),
    ]
    path = tmp_path / "synthetic_itodd-val.csv"
    bop.write_bop_results_csv(path, rows)
    assert bop.read_bop_results_csv(path) == rows
    assert "-12.5 3.25 701.125" in path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "rotation",
    [np.diag([1.0, 1.0, -1.0]), np.diag([1.0, 1.0, 2.0]),
     np.array([[1.0, 0.0, np.nan], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])],
)
def test_bop_pose_rejects_reflection_scale_and_nan(rotation):
    with pytest.raises(ValueError, match="rotation|orthonormal|NaN"):
        bop.BOPPoseEstimate(1, 2, 3, 0.4, rotation, np.zeros(3), 0.1)


def test_bop_csv_rejects_different_times_for_one_image(tmp_path):
    rows = [
        bop.BOPPoseEstimate(1, 2, 3, 0.9, np.eye(3), np.zeros(3), 0.1),
        bop.BOPPoseEstimate(1, 2, 4, 0.8, np.eye(3), np.ones(3), 0.2),
    ]
    with pytest.raises(ValueError, match="same time"):
        bop.write_bop_results_csv(tmp_path / "bad.csv", rows)


def test_ppf_pose_hypotheses_recovers_signed_known_pose_and_top_n():
    model_points, model_normals = _part()
    rotation_true = _rotation((0.3, 1.0, -0.2), 43.0)
    translation_true = np.array([-0.45, 0.8, 1.25])
    scene = model_points @ rotation_true.T + translation_true
    scene_normals = model_normals @ rotation_true.T
    descriptor = ppf.ppf_model(model_points, model_normals, angle_bins=30)
    hypotheses = ppf.ppf_pose_hypotheses(
        descriptor, scene, scene_normals, top_n=4, ref_fraction=0.6, seed=11)
    assert 1 <= len(hypotheses) <= 4
    best = hypotheses[0]
    signed_rotation = math.degrees(math.acos(np.clip(
        (np.trace(best.R.T @ rotation_true) - 1.0) / 2.0, -1.0, 1.0)))
    assert signed_rotation < 0.2
    assert np.allclose(best.t, translation_true, atol=1e-5, rtol=0.0)
    assert best.votes > 0 and best.inlier_fraction > 0.99 and best.score > 0.99


def test_ppf_pose_hypotheses_rejects_empty_nonfinite_and_no_votes():
    model_points, model_normals = _part()
    descriptor = ppf.ppf_model(model_points, model_normals, angle_bins=24)
    with pytest.raises(ValueError, match="non-empty"):
        ppf.ppf_pose_hypotheses(descriptor, np.zeros((0, 3)), np.zeros((0, 3)))
    poisoned = model_points.copy()
    poisoned[2, 1] = np.inf
    with pytest.raises(ValueError, match="NaN or infinity"):
        ppf.ppf_pose_hypotheses(descriptor, poisoned, model_normals)
    with pytest.raises(ValueError, match="no votes"):
        ppf.ppf_pose_hypotheses(descriptor, np.array([[50.0, 50.0, 50.0]]),
                                    np.array([[0.0, 0.0, 1.0]]))


def test_pose_nms_merges_only_symmetric_same_instance():
    points = np.array([[1.2, 0.0, 0.0], [-1.2, 0.0, 0.0],
                       [0.0, 0.4, 0.3], [0.0, -0.4, -0.1]])
    half_turn = np.eye(4)
    half_turn[:3, :3] = _rotation((0, 0, 1), 180.0)
    identity = _hypothesis(np.eye(3), (0, 0, 0), 0.95, 20)
    symmetric = _hypothesis(half_turn[:3, :3], (0, 0, 0), 0.90, 18)
    non_symmetric = _hypothesis(_rotation((1, 0, 0), 35.0), (0, 0, 0), 0.85, 16)
    other_instance = _hypothesis(half_turn[:3, :3], (4, -2, 1), 0.80, 15)
    kept = ppf.pose_nms_symmetry(
        [other_instance, non_symmetric, symmetric, identity], points, [half_turn],
        distance_threshold=0.01)
    assert kept == [identity, non_symmetric, other_instance]
    without_symmetry = ppf.pose_nms_symmetry(
        [symmetric, identity], points, distance_threshold=0.01)
    assert without_symmetry == [identity, symmetric]


def test_bop_symmetry_product_merges_noncommuting_discrete_and_continuous_pose():
    # This mirrors the mixed discrete/continuous ITODD objects: neither factor
    # alone maps the second pose onto the first one.
    discrete = np.eye(4)
    discrete[:3, :3] = _rotation((1, 0, 0), 180.0)
    info = {
        "diameter": 4.0,
        "symmetries_discrete": [discrete.ravel().tolist()],
        "symmetries_continuous": [{"axis": [0.0, 0.0, 1.0], "offset": [0.0, 0.0, 0.0]}],
    }
    transforms = bop.bop_symmetry_transforms(info, max_step=2.0)
    continuous_half_turn = np.diag([-1.0, -1.0, 1.0, 1.0])
    combined = continuous_half_turn @ discrete
    assert any(np.allclose(combined, transform, atol=1e-12, rtol=0.0)
               for transform in transforms)
    points = np.array([[1.0, 0.3, 0.2], [-0.5, 1.2, 0.4], [0.7, -0.8, 1.1]])
    first = _hypothesis(np.eye(3), (0, 0, 0), 0.9, 10)
    second = _hypothesis(combined[:3, :3].T,
                         -combined[:3, :3].T @ combined[:3, 3], 0.8, 9)
    assert ppf.pose_nms_symmetry([first, second], points, transforms,
                                 distance_threshold=1e-10) == [first]


def test_ppf_vote_hypotheses_keeps_multiple_ranked_local_peaks(monkeypatch):
    accumulator = np.array([[0, 11, 2, 0, 7, 0], [0, 0, 9, 0, 0, 0]])

    def vote_with_two_peaks(*_args):
        return accumulator

    def pose_for_peak(_point, _normal, _model, model_index, alpha):
        return np.eye(3), np.array([float(model_index), alpha, 0.0])

    monkeypatch.setattr(ppf, "_vote", vote_with_two_peaks)
    monkeypatch.setattr(ppf, "_pose_from", pose_for_peak)
    scene = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    normals = np.tile([0.0, 0.0, 1.0], (2, 1))
    tree = cKDTree(scene)
    hypotheses = ppf._vote_hypotheses(
        scene, normals, np.array([0]), tree, 2.0, {"table": {}}, 0.1, 6, 2,
        2.0 * np.pi, 1.0, peaks_per_accumulator=3)
    # The second peak in row zero is not a global argmax, but it is a valid
    # candidate and retains its rank between the stronger and weaker peaks.
    assert [candidate[0] for candidate in hypotheses] == [11.0, 9.0, 7.0]


def test_pose_nms_rejects_empty_and_nonfinite():
    with pytest.raises(ValueError, match="must not be empty"):
        ppf.pose_nms_symmetry([], np.eye(3))
    with pytest.raises(ValueError, match="NaN or infinity"):
        ppf.pose_nms_symmetry([_hypothesis(np.eye(3), (0, 0, 0), 0.9, 2)],
                              np.array([[0.0, np.nan, 0.0]]))


def test_bop_scene_reader_uses_frame_scale_and_hides_test_ground_truth(tmp_path):
    tifffile = pytest.importorskip("tifffile")
    root = tmp_path / "itodd"
    for split in ("val", "test"):
        scene = root / split / "000001"
        (scene / "depth").mkdir(parents=True)
        K = [100.0, 0.0, 1.0, 0.0, 100.0, 1.0, 0.0, 0.0, 1.0]
        (scene / "scene_camera.json").write_text(
            json.dumps({"0": {"cam_K": K, "depth_scale": 0.5}}), encoding="utf-8")
        (scene / "scene_gt.json").write_text(
            json.dumps({"0": [{"obj_id": 1}]}), encoding="utf-8")
        depth = np.full((5, 5), 1000, np.uint16)
        depth[0, 0] = 0
        tifffile.imwrite(scene / "depth" / "000000.tif", depth)
    val = bop.read_bop_scene_image(root, "val", 1, 0)
    test = bop.read_bop_scene_image(root, "test", 1, 0)
    assert val["depth_scale"] == 0.5
    assert val["depth_mm"][2, 2] == 500.0
    assert np.allclose(val["points_mm"][0], [0.0, -5.0, 500.0])
    assert "ground_truth" in val and "ground_truth" not in test


def test_val_target_writer_counts_instances_and_test_evaluator_fails_before_subprocess(tmp_path):
    root = tmp_path / "datasets" / "itodd"
    scene = root / "val" / "000001"
    scene.mkdir(parents=True)
    (scene / "scene_gt.json").write_text(json.dumps({
        "4": [{"obj_id": 2}, {"obj_id": 2}, {"obj_id": 7}],
    }), encoding="utf-8")
    target = bop.write_bop_val_targets(root, {1: [4]})
    assert json.loads(target.read_text(encoding="utf-8")) == [
        {"scene_id": 1, "im_id": 4, "obj_id": 2, "inst_count": 2},
        {"scene_id": 1, "im_id": 4, "obj_id": 7, "inst_count": 1},
    ]
    result = tmp_path / "method_itodd-test.csv"
    result.write_text("scene_id,im_id,obj_id,score,R,t,time\n", encoding="utf-8")
    with pytest.raises(ValueError, match="test evaluation is forbidden"):
        bop.evaluate_bop19_pose(result, tmp_path / "datasets", tmp_path / "missing-toolkit",
                                tmp_path / "eval")


def test_evaluator_rejects_invalid_csv_before_any_subprocess(tmp_path, monkeypatch):
    datasets = tmp_path / "datasets"
    dataset = datasets / "itodd"
    dataset.mkdir(parents=True)
    (dataset / "val_targets.json").write_text("[]", encoding="utf-8")
    result = tmp_path / "method_itodd-val.csv"
    result.write_text(
        "scene_id,im_id,obj_id,score,R,t,time\n"
        "1,1,1,1,1 0 0 0 1 0 0 0 -1,0 0 1,0\n", encoding="utf-8")

    def subprocess_must_not_run(*_args, **_kwargs):
        raise AssertionError("CSV validation must precede every subprocess")

    monkeypatch.setattr(bop.subprocess, "run", subprocess_must_not_run)
    with pytest.raises(ValueError, match="proper rotation"):
        bop.evaluate_bop19_pose(result, datasets, tmp_path / "toolkit", tmp_path / "eval")


def test_evaluator_rejects_lookalike_toolkit_before_execution(tmp_path):
    datasets = tmp_path / "datasets"
    dataset = datasets / "itodd"
    dataset.mkdir(parents=True)
    (dataset / "val_targets.json").write_text("[]", encoding="utf-8")
    toolkit = tmp_path / "toolkit"
    (toolkit / "scripts").mkdir(parents=True)
    (toolkit / "scripts" / "eval_bop19_pose.py").write_text("# imitation\n", encoding="utf-8")
    (toolkit / "LICENSE").write_text("MIT License\n", encoding="utf-8")
    result = tmp_path / "method_itodd-val.csv"
    result.write_text("scene_id,im_id,obj_id,score,R,t,time\n", encoding="utf-8")
    with pytest.raises(ValueError, match="pinned official BOP toolkit"):
        bop.evaluate_bop19_pose(result, datasets, toolkit, tmp_path / "eval")


def test_official_adapter_parses_the_pinned_evaluator_score_file(tmp_path, monkeypatch):
    datasets = tmp_path / "datasets"
    dataset = datasets / "itodd"
    dataset.mkdir(parents=True)
    (dataset / "val_targets.json").write_text("[]", encoding="utf-8")
    toolkit = tmp_path / "toolkit"
    (toolkit / "scripts").mkdir(parents=True)
    (toolkit / "scripts" / "eval_bop19_pose.py").write_text("# synthetic process stub\n",
                                                               encoding="utf-8")
    (toolkit / "LICENSE").write_text("MIT License\n", encoding="utf-8")
    result = tmp_path / "method_itodd-val.csv"
    result.write_text("scene_id,im_id,obj_id,score,R,t,time\n", encoding="utf-8")
    eval_path = tmp_path / "eval"

    def fake_run(command, **kwargs):
        if len(command) > 1 and command[1] == "-c":
            return type("Completed", (), {"returncode": 0, "stdout": str(tmp_path),
                                           "stderr": ""})()
        score_dir = eval_path / "method_itodd-val"
        score_dir.mkdir(parents=True)
        (score_dir / "scores_bop19.json").write_text(json.dumps({
            "bop19_average_recall": 0.25,
            "bop19_average_recall_vsd": 0.1,
            "bop19_average_recall_mssd": 0.2,
            "bop19_average_recall_mspd": 0.45,
            "bop19_average_time_per_image": 0.75,
        }), encoding="utf-8")
        return type("Completed", (), {"returncode": 0, "stdout": "official fixture"})()

    monkeypatch.setattr(bop, "_validate_official_bop_toolkit", lambda *_args: None)
    monkeypatch.setattr(bop.subprocess, "run", fake_run)
    scores = bop.evaluate_bop19_pose(result, datasets, toolkit, eval_path)
    assert scores["AR"] == 0.25
    assert scores["AR_VSD"] == 0.1
    assert scores["AR_MSSD"] == 0.2
    assert scores["AR_MSPD"] == 0.45
