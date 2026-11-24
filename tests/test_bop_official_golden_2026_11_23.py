"""Small synthetic golden errors checked against the official BOP toolkit.

Set ``BOP_TOOLKIT_ROOT`` to an explicit local checkout.  The Ubuntu/EGL CI job
clones the toolkit, checks out the recorded commit, verifies the driver digest,
and runs both the direct metric checks and the complete official driver fixture.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

import bop

TOOLKIT_SOURCE_ROOT = os.environ.get("BOP_TOOLKIT_ROOT")
pytestmark = pytest.mark.skipif(
    not TOOLKIT_SOURCE_ROOT, reason="BOP_TOOLKIT_ROOT is not set")


@pytest.fixture(scope="module", autouse=True)
def _disable_toolkit_bytecode():
    """Keep direct toolkit imports clean. / toolkit の直接 import でも bytecode を書かない。"""
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        yield
    finally:
        sys.dont_write_bytecode = previous


@pytest.fixture(scope="module")
def toolkit_root(tmp_path_factory):
    """Clone the pinned revision for the test. / 元を汚さず固定版を一時複製する。"""
    source = Path(TOOLKIT_SOURCE_ROOT).resolve()
    if not (source / ".git").exists():
        pytest.fail(f"BOP_TOOLKIT_ROOT is not a git checkout: {source}")
    root = tmp_path_factory.mktemp("bop_toolkit") / "checkout"
    environment = bop._toolkit_git_environment()
    subprocess.run(
        ["git", "clone", "--no-local", "--no-checkout", str(source), str(root)],
        check=True, env=environment, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(
        ["git", "-C", str(root), "checkout", "--detach", bop._BOP_TOOLKIT_COMMIT],
        check=True, env=environment, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return root


class _SequenceDepthRenderer:
    """Return the synthetic estimate then truth, matching official VSD call order."""

    def __init__(self, estimate, truth):
        self._depths = iter((estimate, truth))

    def render_object(self, _obj_id, _R, _t, _fx, _fy, _cx, _cy):
        return {"depth": next(self._depths)}


def _official_pose_error(toolkit_root):
    root = Path(toolkit_root).resolve()
    if not (root / "LICENSE").is_file():
        pytest.fail(f"BOP_TOOLKIT_ROOT has no LICENSE: {root}")
    sys.path.insert(0, str(root))
    try:
        from bop_toolkit_lib import pose_error
    finally:
        sys.path.pop(0)
    return pose_error


def test_official_vsd_mssd_mspd_match_synthetic_golden_values(toolkit_root):
    pose_error = _official_pose_error(toolkit_root)
    identity = np.eye(3)
    points = np.array([[-2.0, -1.0, 0.0], [3.0, -1.0, 0.0],
                       [0.5, 2.0, 0.0], [0.0, 0.0, 1.0]])
    symmetry_identity = [{"R": identity, "t": np.zeros((3, 1))}]

    # Every point moves by the signed translation (-2,+3,0), so max distance
    # is exactly sqrt(13), not a self-comparison or ratio-only assertion.
    mssd = pose_error.mssd(
        identity, np.array([[-2.0], [3.0], [100.0]]),
        identity, np.array([[0.0], [0.0], [100.0]]),
        points, symmetry_identity)
    assert mssd == pytest.approx(math.sqrt(13.0), abs=1e-12)

    # At Z=100 and fx=100, +2 model units in X is exactly +2 pixels.
    K = np.array([[100.0, 0.0, 2.0], [0.0, 100.0, 2.0], [0.0, 0.0, 1.0]])
    mspd = pose_error.mspd(
        identity, np.array([[2.0], [0.0], [100.0]]),
        identity, np.array([[0.0], [0.0], [100.0]]),
        K, points, symmetry_identity)
    assert mspd == pytest.approx(2.0, abs=1e-12)

    depth_truth = np.zeros((5, 5), np.float64)
    depth_estimate = np.zeros((5, 5), np.float64)
    depth_truth[2, 2] = 100.0
    depth_estimate[2, 2] = 102.0
    vsd = pose_error.vsd(
        identity, np.array([[0.0], [0.0], [102.0]]),
        identity, np.array([[0.0], [0.0], [100.0]]),
        depth_truth, K, delta=5.0, taus=[0.1, 0.3],
        normalized_by_diameter=True, diameter=10.0,
        renderer=_SequenceDepthRenderer(depth_estimate, depth_truth), obj_id=1)
    assert vsd == [1.0, 0.0]


_ITODD_OBJECT_IDS = range(1, 29)
_IDENTITY_R = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
_FIXTURE_IMAGE_SIZE = (1280, 960)
_FIXTURE_FOCAL_LENGTH_PX = 800.0
_FIXTURE_DEPTH_MM = 1000.0


def _write_tetrahedron_ply(path: Path) -> None:
    path.write_text(
        "ply\nformat ascii 1.0\n"
        "element vertex 4\nproperty float x\nproperty float y\nproperty float z\n"
        "element face 4\nproperty list uchar int vertex_indices\nend_header\n"
        "-20 -20 -20\n20 -20 -20\n0 20 -20\n0 0 20\n"
        "3 0 1 2\n3 0 3 1\n3 1 3 2\n3 2 3 0\n", encoding="ascii")


def _write_official_eval_fixture(root: Path) -> tuple[Path, Path]:
    """Create a disposable BOP-shaped fixture; no ITODD asset is copied."""
    from PIL import Image

    dataset = root / "datasets" / "itodd"
    models = dataset / "models_eval"
    scene = dataset / "val" / "000001"
    depth = scene / "depth"
    models.mkdir(parents=True)
    depth.mkdir(parents=True)
    model_info = {}
    for object_id in _ITODD_OBJECT_IDS:
        _write_tetrahedron_ply(models / f"obj_{object_id:06d}.ply")
        model_info[str(object_id)] = {"diameter": 60.0}
    (models / "models_info.json").write_text(json.dumps(model_info), encoding="utf-8")
    Image.fromarray(np.zeros((_FIXTURE_IMAGE_SIZE[1], _FIXTURE_IMAGE_SIZE[0]), np.uint16)).save(
        depth / "000000.tif")
    gt = {"0": [{"obj_id": 1, "cam_R_m2c": _IDENTITY_R,
                  "cam_t_m2c": [0.0, 0.0, _FIXTURE_DEPTH_MM]}]}
    info = {"0": [{"bbox_obj": [600, 440, 80, 80], "bbox_visib": [600, 440, 80, 80],
                   "px_count_all": 6400, "px_count_valid": 6400, "px_count_visib": 6400,
                   "visib_fract": 1.0}]}
    camera = {"0": {"cam_K": [_FIXTURE_FOCAL_LENGTH_PX, 0.0, 640.0,
                                 0.0, _FIXTURE_FOCAL_LENGTH_PX, 480.0,
                                 0.0, 0.0, 1.0], "depth_scale": 1.0}}
    for name, value in (("scene_gt.json", gt), ("scene_gt_info.json", info),
                        ("scene_camera.json", camera), ("val_targets.json", [
                            {"scene_id": 1, "im_id": 0, "obj_id": 1, "inst_count": 1}])):
        ((scene / name) if name.startswith("scene_") else (dataset / name)).write_text(
            json.dumps(value), encoding="utf-8")
    result = root / "method_itodd-val.csv"
    result.write_text(
        "scene_id,im_id,obj_id,score,R,t,time\n"
        "1,0,1,1,1 0 0 0 1 0 0 0 1,0 0 1000,0.25\n", encoding="utf-8")
    return root / "datasets", result


def _assert_toolkit_worktree_is_clean(toolkit_root: Path) -> None:
    completed = subprocess.run(
        ["git", "-C", str(toolkit_root), "status", "--porcelain", "--ignored",
         "--untracked-files=all"],
        check=True, env=bop._toolkit_git_environment(), text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert completed.stdout == ""


def test_pinned_official_bop19_driver_twice_keeps_checkout_clean(tmp_path, toolkit_root):
    """Run the official adapter twice. / 公式 adapter を2回走らせても複製を汚さない。"""
    datasets, result = _write_official_eval_fixture(tmp_path)
    for run_number in (1, 2):
        scores = bop.evaluate_bop19_pose(
            result, datasets, toolkit_root, tmp_path / f"eval-{run_number}",
            renderer_type="vispy", num_workers=1)
        assert scores["AR"] == pytest.approx(1.0, abs=1e-12)
        assert scores["AR_VSD"] == pytest.approx(1.0, abs=1e-12)
        assert scores["AR_MSSD"] == pytest.approx(1.0, abs=1e-12)
        assert scores["AR_MSPD"] == pytest.approx(1.0, abs=1e-12)
        _assert_toolkit_worktree_is_clean(toolkit_root)
