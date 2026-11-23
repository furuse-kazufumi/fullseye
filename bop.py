"""BOP dataset I/O and official BOP19 pose-evaluation adapter.

This module only reads a dataset directory explicitly supplied by the caller.  It
never downloads data and it deliberately refuses evaluation of a ``test`` split:
the public BOP test ground truth is not available and validation parameters must
not be selected on test images.

BOP uses millimetres for model coordinates and translations.  Depth samples are
multiplied by each frame's ``depth_scale`` and therefore stay in millimetres.

BOP データセットの入出力と公式 BOP19 姿勢採点器へのアダプター。
呼び手が明示したローカルディレクトリだけを読み、データ取得は行わない。公開されない
test 正解を要求したり test で調整したりしないよう、test split の採点は明示的に拒否する。
モデル座標、点群、平行移動の単位は BOP 規約どおり mm である。
"""
from __future__ import annotations

from dataclasses import dataclass
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from typing import Iterable, Mapping, Sequence

import numpy as np


__all__ = [
    "BOPPoseEstimate",
    "read_bop_camera",
    "read_bop_scene_image",
    "read_bop_model",
    "read_bop_models_info",
    "bop_symmetry_transforms",
    "write_bop_results_csv",
    "read_bop_results_csv",
    "write_bop_val_targets",
    "evaluate_bop19_pose",
]


_ROTATION_ATOL = 1e-7
_BOP_SYMMETRY_ATOL = 2e-5  # models_info matrices are published with ~6 decimals.
_CSV_FIELDS = ("scene_id", "im_id", "obj_id", "score", "R", "t", "time")
_BOP19_SCORE_KEYS = (
    "bop19_average_recall",
    "bop19_average_recall_vsd",
    "bop19_average_recall_mssd",
    "bop19_average_recall_mspd",
    "bop19_average_time_per_image",
)
_BOP_TOOLKIT_COMMIT = "cea62d651c7e395b2e1962b9749e4e89693c6ac4"
_BOP19_EVALUATOR_SHA256 = "44a0fa020f53bec65dad351c4a188e2a21e3d8cbe554925e06c98315be3f57f4"


def _positive_id(value, name: str) -> int:
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be a positive integer")
    try:
        out = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if out < 0 or out != value:
        raise ValueError(f"{name} must be a non-negative integer")
    return out


def _proper_rotation(value, name="R") -> np.ndarray:
    R = np.asarray(value, dtype=np.float64)
    if R.shape != (3, 3):
        raise ValueError(f"{name} must have shape (3, 3), got {R.shape!r}")
    if not np.isfinite(R).all():
        raise ValueError(f"{name} contains NaN or infinity")
    gram = R.T @ R
    if not np.allclose(gram, np.eye(3), rtol=0.0, atol=_ROTATION_ATOL):
        raise ValueError(f"{name} is not orthonormal: R.T @ R != I")
    determinant = float(np.linalg.det(R))
    if not math.isclose(determinant, 1.0, rel_tol=0.0, abs_tol=_ROTATION_ATOL):
        raise ValueError(f"{name} is not a proper rotation: det(R)={determinant!r}")
    out = R.copy()
    out.setflags(write=False)
    return out


def _finite_vector(value, name: str, length: int) -> np.ndarray:
    out = np.asarray(value, dtype=np.float64)
    if out.shape != (length,):
        raise ValueError(f"{name} must have shape ({length},), got {out.shape!r}")
    if not np.isfinite(out).all():
        raise ValueError(f"{name} contains NaN or infinity")
    out = out.copy()
    out.setflags(write=False)
    return out


@dataclass(frozen=True, eq=False)
class BOPPoseEstimate:
    """One BOP pose result row; ``t`` is in millimetres. / BOP 姿勢結果の1行。``t`` は mm。

    ``R`` must be a finite proper rotation (``R.T @ R == I`` and ``det(R) == 1``).
    All scalar fields must be finite, IDs are non-negative, and time is seconds.
    Arrays are copied and made read-only, so validation cannot be invalidated later.

    ``R`` は有限な正回転、全スカラーは有限、ID は非負、時間は秒。配列は複製して
    読み取り専用にする。反射、拡大縮小、NaN/Inf は ``ValueError`` で拒否する。
    """

    scene_id: int
    im_id: int
    obj_id: int
    score: float
    R: np.ndarray
    t: np.ndarray
    time: float

    def __post_init__(self):
        object.__setattr__(self, "scene_id", _positive_id(self.scene_id, "scene_id"))
        object.__setattr__(self, "im_id", _positive_id(self.im_id, "im_id"))
        object.__setattr__(self, "obj_id", _positive_id(self.obj_id, "obj_id"))
        for name in ("score", "time"):
            value = float(getattr(self, name))
            if not math.isfinite(value):
                raise ValueError(f"{name} contains NaN or infinity")
            if name == "time" and value < 0.0:
                raise ValueError("time must be non-negative seconds")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "R", _proper_rotation(self.R))
        object.__setattr__(self, "t", _finite_vector(self.t, "t", 3))

    def __eq__(self, other):
        if not isinstance(other, BOPPoseEstimate):
            return NotImplemented
        return (
            self.scene_id == other.scene_id
            and self.im_id == other.im_id
            and self.obj_id == other.obj_id
            and self.score == other.score
            and self.time == other.time
            and np.array_equal(self.R, other.R)
            and np.array_equal(self.t, other.t)
        )


def _existing_dir(path, name: str) -> Path:
    out = Path(path).expanduser().resolve()
    if not out.is_dir():
        raise FileNotFoundError(f"{name} is not a local directory: {out}")
    return out


def _load_json(path: Path):
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed JSON in {path}: {exc}") from exc


def read_bop_camera(dataset_root) -> dict:
    """Read ``camera.json`` from an explicit local BOP root. / 指定ローカル BOP のカメラを読む。"""
    root = _existing_dir(dataset_root, "dataset_root")
    path = root / "camera.json"
    # BOP's itodd_base.zip contains the ``itodd/`` prefix while the model/val
    # archives start at ``models/`` and ``val/``.  Accept both standard unzip
    # layouts without walking outside the caller's explicit root.
    if not path.is_file() and (root / "itodd" / "camera.json").is_file():
        path = root / "itodd" / "camera.json"
    camera = _load_json(path)
    if not isinstance(camera, dict):
        raise ValueError("camera.json must contain an object")
    out = dict(camera)
    if "K" in out:
        K = np.asarray(out["K"], np.float64)
        if K.size != 9 or not np.isfinite(K).all():
            raise ValueError("camera.json K must contain 9 finite values")
        out["K"] = K.reshape(3, 3)
    return out


def read_bop_scene_image(dataset_root, split: str, scene_id: int, im_id: int) -> dict:
    """Read one BOP camera/depth frame and return points and normals in millimetres.

    The returned dict has ``K``, ``depth_mm``, ``valid``, ``points_mm``,
    ``normals`` and, when present, ``ground_truth`` / ``ground_truth_info``.
    Point and normal rows correspond to the same valid pixels.  No image or
    derived visualization is written.  Missing depth, malformed matrices, empty
    point clouds and non-finite scales are rejected.

    BOP の1フレームからカメラ、深度、点群、法線を読む。点群の単位は mm。
    画像や派生可視化は書き出さない。test では正解ファイルを読まず、返りにも含めない。
    """
    from camera import depth_to_points, normals_from_depth_edgeaware
    from raster import read_raster

    root = _existing_dir(dataset_root, "dataset_root")
    split_name = str(split).strip().lower()
    if split_name not in {"train", "val", "test"}:
        raise ValueError("split must be 'train', 'val', or 'test'")
    sid = _positive_id(scene_id, "scene_id")
    iid = _positive_id(im_id, "im_id")
    scene = root / split_name / f"{sid:06d}"
    if not scene.is_dir():
        raise FileNotFoundError(scene)
    cameras = _load_json(scene / "scene_camera.json")
    key = str(iid)
    if key not in cameras:
        raise KeyError(f"image {iid} is absent from {scene / 'scene_camera.json'}")
    record = cameras[key]
    K = np.asarray(record.get("cam_K"), np.float64)
    if K.size != 9 or not np.isfinite(K).all():
        raise ValueError("scene camera cam_K must contain 9 finite values")
    K = K.reshape(3, 3)
    scale = float(record.get("depth_scale", 1.0))
    if not math.isfinite(scale) or scale <= 0.0:
        raise ValueError("scene camera depth_scale must be finite and positive")
    depth_path = scene / "depth" / f"{iid:06d}.tif"
    raw, _meta = read_raster(str(depth_path), keep_dtype=True)
    raw = np.asarray(raw)
    if raw.ndim == 3:
        raw = raw[..., 0]
    if raw.ndim != 2:
        raise ValueError(f"depth must be 2-D, got {raw.shape!r}")
    valid = np.isfinite(raw) & (raw > 0)
    depth_mm = raw.astype(np.float64) * scale
    depth_mm[~valid] = np.nan
    points = depth_to_points(depth_mm, K)
    if points.shape[0] == 0:
        raise ValueError("depth contains no valid points")
    normal_grid = normals_from_depth_edgeaware(depth_mm, K)
    normals = normal_grid[valid]
    finite_normal = np.isfinite(normals).all(axis=1)
    out = {
        "scene_id": sid,
        "im_id": iid,
        "K": K,
        "depth_scale": scale,
        "depth_mm": depth_mm,
        "valid": valid,
        "points_mm": points[finite_normal],
        "normals": normals[finite_normal],
    }
    if split_name != "test":
        gt_path = scene / "scene_gt.json"
        info_path = scene / "scene_gt_info.json"
        if gt_path.is_file():
            out["ground_truth"] = _load_json(gt_path).get(key, [])
        if info_path.is_file():
            out["ground_truth_info"] = _load_json(info_path).get(key, [])
    return out


def read_bop_model(dataset_root, obj_id: int, model_folder="models") -> tuple[np.ndarray, np.ndarray]:
    """Read a BOP PLY mesh as ``(vertices_mm, faces)``. / BOP PLY を頂点 mm と面で読む。"""
    from mesh import read_mesh

    root = _existing_dir(dataset_root, "dataset_root")
    oid = _positive_id(obj_id, "obj_id")
    path = root / str(model_folder) / f"obj_{oid:06d}.ply"
    vertices, faces = read_mesh(str(path))
    if vertices.shape[0] == 0:
        raise ValueError(f"model has no vertices: {path}")
    return vertices, faces


def read_bop_models_info(dataset_root, model_folder="models") -> dict[int, dict]:
    """Read BOP model diameters and symmetry declarations. / 直径と対称性宣言を読む。"""
    root = _existing_dir(dataset_root, "dataset_root")
    data = _load_json(root / str(model_folder) / "models_info.json")
    if not isinstance(data, dict):
        raise ValueError("models_info.json must contain an object")
    return {int(key): dict(value) for key, value in data.items()}


def _transform4(value, name: str) -> np.ndarray:
    transform = np.asarray(value, np.float64)
    if transform.size != 16 or not np.isfinite(transform).all():
        raise ValueError(f"{name} must contain 16 finite values")
    transform = transform.reshape(4, 4)
    rotation = transform[:3, :3]
    if not np.allclose(rotation.T @ rotation, np.eye(3), rtol=0.0,
                       atol=_BOP_SYMMETRY_ATOL):
        raise ValueError(f"{name} rotation is not orthonormal")
    if not math.isclose(float(np.linalg.det(rotation)), 1.0, rel_tol=0.0,
                        abs_tol=_BOP_SYMMETRY_ATOL):
        raise ValueError(f"{name} rotation is not proper")
    if not np.allclose(transform[3], (0.0, 0.0, 0.0, 1.0), atol=_ROTATION_ATOL, rtol=0.0):
        raise ValueError(f"{name} has an invalid homogeneous last row")
    return transform


def bop_symmetry_transforms(model_info: Mapping, max_step: float | None = None) -> list[np.ndarray]:
    """Return discrete 4x4 model symmetries, optionally sampling continuous axes.

    ``max_step`` is the maximum surface displacement in model units used to
    discretise a continuous rotational symmetry.  It requires ``diameter``.
    Identity is always included and duplicate matrices are removed.

    BOP ``models_info.json`` の対称変換を4x4列として返す。連続回転は ``max_step``
    以下の表面移動になる角度で離散化する。恒等変換は必ず含める。
    """
    if not isinstance(model_info, Mapping):
        raise ValueError("model_info must be a mapping")
    discrete = [np.eye(4)]
    for index, value in enumerate(model_info.get("symmetries_discrete", [])):
        discrete.append(_transform4(value, f"symmetries_discrete[{index}]"))
    continuous_transforms = []
    continuous = model_info.get("symmetries_continuous", [])
    if continuous:
        if max_step is None:
            raise ValueError("max_step is required for continuous symmetries")
        step = float(max_step)
        diameter = float(model_info.get("diameter", math.nan))
        if not math.isfinite(step) or step <= 0.0 or not math.isfinite(diameter) or diameter <= 0.0:
            raise ValueError("max_step and model diameter must be finite and positive")
        radius = 0.5 * diameter
        angle_step = 2.0 * math.asin(min(1.0, step / max(2.0 * radius, step)))
        count = max(1, int(math.ceil(2.0 * math.pi / max(angle_step, 1e-12))))
        for sym_index, spec in enumerate(continuous):
            axis = _finite_vector(spec.get("axis"), f"continuous axis {sym_index}", 3)
            offset = _finite_vector(spec.get("offset", (0, 0, 0)), f"continuous offset {sym_index}", 3)
            norm = float(np.linalg.norm(axis))
            if norm <= 0.0:
                raise ValueError("continuous symmetry axis must be non-zero")
            axis = np.asarray(axis) / norm
            skew = np.array([[0.0, -axis[2], axis[1]], [axis[2], 0.0, -axis[0]],
                             [-axis[1], axis[0], 0.0]])
            for sample in range(count):
                angle = 2.0 * math.pi * sample / count
                rotation = np.eye(3) + math.sin(angle) * skew + (1.0 - math.cos(angle)) * skew @ skew
                transform = np.eye(4)
                transform[:3, :3] = rotation
                transform[:3, 3] = offset - rotation @ offset
                continuous_transforms.append(transform)
    # BOP first forms the discrete set and then composes every sampled continuous
    # transform on its left (C @ D in its column-vector convention).  Do not
    # merely append D and C: objects such as ITODD 12 and 28 need their product.
    transforms = ([(continuous_transform @ discrete_transform)
                   for discrete_transform in discrete
                   for continuous_transform in continuous_transforms]
                  if continuous_transforms else discrete)
    unique = []
    for transform in transforms:
        if not any(np.allclose(transform, old, atol=1e-10, rtol=0.0) for old in unique):
            unique.append(np.asarray(transform, np.float64))
    return unique


def _float_text(value: float) -> str:
    return repr(float(value))


def write_bop_results_csv(path, estimates: Iterable[BOPPoseEstimate]) -> None:
    """Write BOP19 CSV and enforce one time per image. / BOP19 CSV を書き、画像内 time 一致を検査。"""
    rows = list(estimates)
    if any(not isinstance(row, BOPPoseEstimate) for row in rows):
        raise ValueError("estimates must contain only BOPPoseEstimate rows")
    times = {}
    for row in rows:
        image_key = (row.scene_id, row.im_id)
        old = times.setdefault(image_key, row.time)
        if old != row.time:
            raise ValueError(f"all estimates for image {image_key} must have the same time")
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=_CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "scene_id": row.scene_id,
                "im_id": row.im_id,
                "obj_id": row.obj_id,
                "score": _float_text(row.score),
                "R": " ".join(_float_text(value) for value in row.R.ravel()),
                "t": " ".join(_float_text(value) for value in row.t),
                "time": _float_text(row.time),
            })


def _parse_float_list(value: str, count: int, name: str) -> np.ndarray:
    try:
        out = np.asarray([float(part) for part in value.split()], np.float64)
    except ValueError as exc:
        raise ValueError(f"{name} must contain numbers") from exc
    if out.size != count:
        raise ValueError(f"{name} must contain {count} numbers, got {out.size}")
    return out


def read_bop_results_csv(path) -> list[BOPPoseEstimate]:
    """Read and validate BOP19 CSV rows. / BOP19 CSV を読み、回転・有限性・time を検査する。"""
    source = Path(path)
    with source.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != _CSV_FIELDS:
            raise ValueError(f"BOP CSV header must be {','.join(_CSV_FIELDS)}")
        rows = []
        for line, row in enumerate(reader, 2):
            try:
                rows.append(BOPPoseEstimate(
                    scene_id=int(row["scene_id"]),
                    im_id=int(row["im_id"]),
                    obj_id=int(row["obj_id"]),
                    score=float(row["score"]),
                    R=_parse_float_list(row["R"], 9, f"line {line} R").reshape(3, 3),
                    t=_parse_float_list(row["t"], 3, f"line {line} t"),
                    time=float(row["time"]),
                ))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid BOP CSV line {line}: {exc}") from exc
    # Reuse the writer's cross-row timing invariant without touching disk.
    times = {}
    for row in rows:
        key = (row.scene_id, row.im_id)
        old = times.setdefault(key, row.time)
        if old != row.time:
            raise ValueError(f"all estimates for image {key} must have the same time")
    return rows


def write_bop_val_targets(dataset_root, image_ids: Mapping[int, Sequence[int]], filename="val_targets.json") -> Path:
    """Build official-evaluator targets from public validation GT only.

    ``image_ids`` maps scene IDs to selected image IDs.  The output is written
    under the explicit dataset root so the official toolkit can resolve it.
    Test roots are refused even if a ``scene_gt.json`` file is accidentally added.

    公開 val 正解から公式採点用 target を作る。scene→image ID の指定分だけを数え、
    test の正解探索には流用できない。
    """
    root = _existing_dir(dataset_root, "dataset_root")
    targets = []
    for scene_id, selected in sorted(image_ids.items()):
        sid = _positive_id(scene_id, "scene_id")
        scene = root / "val" / f"{sid:06d}"
        gt = _load_json(scene / "scene_gt.json")
        for im_id in sorted({_positive_id(value, "im_id") for value in selected}):
            entries = gt.get(str(im_id))
            if entries is None:
                raise KeyError(f"validation image {sid}/{im_id} has no ground truth")
            counts = {}
            for entry in entries:
                obj_id = _positive_id(entry["obj_id"], "obj_id")
                counts[obj_id] = counts.get(obj_id, 0) + 1
            for obj_id, count in sorted(counts.items()):
                targets.append({"scene_id": sid, "im_id": im_id, "obj_id": obj_id,
                                "inst_count": count})
    output = root / str(filename)
    if output.parent != root or output.name != filename:
        raise ValueError("filename must be a plain file name inside dataset_root")
    with output.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(targets, stream, ensure_ascii=False, separators=(",", ":"))
    return output


def evaluate_bop19_pose(result_csv, datasets_path, toolkit_root, eval_path,
                        targets_filename="val_targets.json", renderer_type="vispy",
                        num_workers=1, python_executable=None) -> dict:
    """Run official ``eval_bop19_pose.py`` for validation and return AR scores.

    The result filename must follow ``METHOD_itodd-val.csv``.  Any test split is
    refused before a subprocess starts.  ``toolkit_root`` must be an explicit
    local checkout pinned to the recorded official commit and evaluator digest;
    this adapter never clones or installs it.  The input CSV is fully validated
    before the toolkit subprocess starts. Returned keys are AR, AR_VSD, AR_MSSD,
    AR_MSPD and seconds per image exactly as written by the toolkit.

    公式 ``eval_bop19_pose.py`` を val に対して実行する薄いアダプター。test は
    subprocess 起動前に拒否し、toolkit の取得・導入は行わない。
    """
    result = Path(result_csv).expanduser().resolve()
    if not result.is_file():
        raise FileNotFoundError(result)
    parts = result.stem.split("_")
    if len(parts) < 2 or "-" not in parts[1]:
        raise ValueError("result filename must follow METHOD_itodd-val.csv")
    dataset, split, *_rest = parts[1].split("-")
    if split.lower() == "test":
        raise ValueError("test evaluation is forbidden: test ground truth is private")
    if dataset.lower() != "itodd" or split.lower() != "val":
        raise ValueError("stage 1 evaluation accepts only the itodd-val split")
    read_bop_results_csv(result)
    datasets = _existing_dir(datasets_path, "datasets_path")
    dataset_root = datasets / "itodd"
    if not dataset_root.is_dir():
        raise FileNotFoundError(f"datasets_path must contain an itodd directory: {dataset_root}")
    target = dataset_root / str(targets_filename)
    if not target.is_file():
        raise FileNotFoundError(target)
    toolkit = _existing_dir(toolkit_root, "toolkit_root")
    script = toolkit / "scripts" / "eval_bop19_pose.py"
    _validate_official_bop_toolkit(toolkit, script)
    workers = int(num_workers)
    if workers < 1:
        raise ValueError("num_workers must be >= 1")
    output = Path(eval_path).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["BOP_PATH"] = str(datasets)
    interpreter = Path(python_executable or sys.executable).expanduser().resolve()
    if not interpreter.is_file():
        raise FileNotFoundError(f"python_executable does not exist: {interpreter}")
    # The official driver starts its metric workers with the literal command
    # ``python``.  Prepending the selected interpreter's directory keeps every
    # subprocess inside the same isolated toolkit environment.
    env["PATH"] = str(interpreter.parent) + os.pathsep + env.get("PATH", "")
    purelib_probe = subprocess.run(
        [str(interpreter), "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if purelib_probe.returncode:
        raise RuntimeError(f"could not inspect toolkit Python environment: {purelib_probe.stderr.strip()}")
    purelib = purelib_probe.stdout.strip()
    # On Windows the official driver launches workers with the literal
    # ``python``.  CreateProcess may prefer the base interpreter's directory
    # over PATH even when the driver itself runs from a venv.  Supplying the
    # selected venv's purelib keeps those official workers on the same package
    # set without editing the toolkit checkout.
    python_paths = [purelib, str(toolkit)]
    if env.get("PYTHONPATH"):
        python_paths.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(python_paths)
    command = [
        str(interpreter),
        str(script),
        f"--result_filenames={result.name}",
        f"--results_path={result.parent}",
        f"--eval_path={output}",
        f"--targets_filename={target.name}",
        f"--renderer_type={renderer_type}",
        f"--num_workers={workers}",
    ]
    completed = subprocess.run(command, cwd=toolkit, env=env, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if completed.returncode:
        tail = "\n".join(completed.stdout.splitlines()[-30:])
        raise RuntimeError(f"official BOP evaluation failed ({completed.returncode}):\n{tail}")
    score_path = output / result.stem / "scores_bop19.json"
    scores = _load_json(score_path)
    missing = [key for key in _BOP19_SCORE_KEYS if key not in scores]
    if missing:
        raise ValueError(f"official score file is missing keys: {missing}")
    return {
        "AR": float(scores["bop19_average_recall"]),
        "AR_VSD": float(scores["bop19_average_recall_vsd"]),
        "AR_MSSD": float(scores["bop19_average_recall_mssd"]),
        "AR_MSPD": float(scores["bop19_average_recall_mspd"]),
        "time_per_image": float(scores["bop19_average_time_per_image"]),
        "official_score_path": str(score_path),
    }


def _validate_official_bop_toolkit(toolkit: Path, script: Path) -> None:
    """Refuse a look-alike toolkit checkout. / 偽の toolkit checkout を拒否する。"""
    if not script.is_file() or not (toolkit / "LICENSE").is_file():
        raise FileNotFoundError("toolkit_root must contain scripts/eval_bop19_pose.py and LICENSE")
    try:
        top_level = subprocess.run(
            ["git", "-C", str(toolkit), "rev-parse", "--show-toplevel"], check=True,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()
        commit = subprocess.run(
            ["git", "-C", str(toolkit), "rev-parse", "HEAD"], check=True,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip().lower()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError("toolkit_root must be the pinned official BOP toolkit git checkout") from exc
    if Path(top_level).resolve() != toolkit.resolve() or commit != _BOP_TOOLKIT_COMMIT:
        raise ValueError(f"toolkit_root must be BOP toolkit commit {_BOP_TOOLKIT_COMMIT}")
    script_digest = hashlib.sha256(script.read_bytes()).hexdigest()
    if script_digest != _BOP19_EVALUATOR_SHA256:
        raise ValueError("BOP eval_bop19_pose.py does not match the pinned official digest")
