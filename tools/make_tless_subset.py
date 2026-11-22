# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0.
"""BOP T-LESS の CI 用最小 subset を決定的に作る。/ Build the CI subset.

元データは読み取り専用として扱い、scene 2 / image 3 の JSON・画像と、obj 5/6 の
モデルを ``tests/data/tless_subset`` に作る。PLY は PoC の主経路が実際に選ぶ頂点行
だけを元の順序で残し、face 要素を落とす。/ The source dataset is read-only. PLY files
retain exactly the ordered vertex rows selected by the PoC primary path and omit faces.

Usage::

    py -3.11 tools/make_tless_subset.py "<T-LESS root>"
    py -3.11 tools/make_tless_subset.py --record-expected
"""
from __future__ import annotations

import argparse
from collections.abc import Callable
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile

import numpy as np
import scipy


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
if str(EXAMPLES) not in sys.path:
    sys.path.insert(0, str(EXAMPLES))

from poc_real_tless_6dof import (  # noqa: E402
    ADOPTED_CONFIG,
    DATA_ENV,
    DEFAULT_DATA,
    EVAL_POINTS,
    MSSD_FAILURE_FRACTION,
    _cap,
    _evaluation_points,
    _metric_rows,
    average_recall,
    run_real,
)


DEFAULT_OUTPUT = ROOT / "tests" / "data" / "tless_subset"
EXPECTED_OUTPUT = ROOT / "tests" / "data" / "tless_subset_expected.json"

# 2026-11-22 brief指定の切り出し。/ BOP scene/image/object selection from the brief.
SUBSET_SCENE_ID = 2
SUBSET_IMAGE_ID = 3
SUBSET_OBJECT_IDS = (5, 6)
SOURCE_INSTANCE_COUNT = 3

# 期待値は同じprocessでこの回数を測る。/ Named run count required by the 2026-11-22 brief.
EXPECTED_MEASUREMENT_RUN_COUNT = 5
EXPECTED_CONTINUOUS_METRIC_FIELDS = ("mssd", "mspd", "rot_deg", "trans_mm")
EXPECTED_SOURCE_TOOL = "tools/make_tless_subset.py"
EXPECTED_COMMAND = (
    "PYTHONUTF8=1 py -3.11 tools/make_tless_subset.py --record-expected"
)

# 固定ブロックでSHA-256を計算する。/ Bound memory while hashing large inputs.
HASH_BLOCK_BYTES = 1024 * 1024

README_TEXT = f"""# BOP T-LESS CI subset

このディレクトリは、Fullseye の実データ門が毎回読む BOP T-LESS の小さな切り出しです。
場面2・画像3にある3個体のうち、obj 5とobj 6を採点するための入力を収録しています。
`scene_gt.json` と `scene_gt_info.json` の個体リストは、mask添字とクラスタ割当の前提を
保つため、obj 7を含む元の3個体を残しています。obj 7のモデルとmaskは収録しません。

## 出典・ライセンス・引用

- データセット: BOP T-LESS, https://bop.felk.cvut.cz/datasets/
- 配布物: Hugging Face `bop-benchmark/tless` の `tless_models.zip` と
  `tless_test_primesense_bop19.zip`
- 元アーカイブのSHA-256 (`tools/fetch_tless.py` の固定値):
  - `tless_base.zip`: `dd70ca884b7c471a530a952f70c5ab2c212f3d2c2f371be86397442b97d70a7e`
  - `tless_models.zip`: `6a29c59766b8d2af05e62e71739f0ca7243ad81bc3c7f9a24925504a8cb37928`
  - `tless_test_primesense_bop19.zip`: `1a18f6bbfb5ac4ced8529f7a35225adfed88c0f62ef38067933e2b541ef1d00b`
- ライセンス: Creative Commons Attribution 4.0 International (CC BY 4.0),
  https://creativecommons.org/licenses/by/4.0/

元データとともに作られる `TLESS_LICENSE.txt` は、CC BY 4.0であること、一次配布元、
論文への帰属表示、BOP形式・ベンチマークの引用先を示しています。このsubsetにも同じ
条件が適用されます。

引用: Hodaň et al., "T-LESS: An RGB-D Dataset for 6D Pose Estimation of
Texture-less Objects", WACV 2017, https://doi.org/10.1109/WACV.2017.8

BOP形式・ベンチマークの引用: Hodaň, Michel et al., "BOP: Benchmark for 6D
Object Pose Estimation", ECCV 2018, http://bop.felk.cvut.cz

BOP Challengeの引用: Hodaň et al., "BOP Challenge 2020 on 6D Object
Localization", https://doi.org/10.1007/978-3-030-68223-0_12

## 収録内容と変更点

- `test_primesense/000002`: `scene_camera.json`、`scene_gt.json`、
  `scene_gt_info.json` は画像キー `"3"` だけを残しました。RGB、depth、obj 5/6の
  visible maskは元ファイルをバイト単位で複写しています。
- `models_reconst/models_info.json`: obj 5/6のキーだけを残しました。
- `models_reconst/obj_000005.ply` と `obj_000006.ply`: PoCの `_cap` が
  {ADOPTED_CONFIG.model_points}点へ一様抽出するときに選ぶ頂点行だけを元の順で残しました。
- `models_cad/obj_000005.ply` と `obj_000006.ply`: PoCの評価点抽出関数が
  最大{EVAL_POINTS}点へ一様抽出するときに選ぶ頂点行だけを元の順で残しました。
- 間引いたPLYは `element vertex` を残した行数へ更新し、`element face`、face property、
  face行を落としました。頂点行の文字列は元ファイルのままです。

この規則はPoCの主経路が読み込むモデル点と評価点を変えません。一方、診断経路の
理想深度合成 `render_point_depth(model_full, ...)` はreconstの全頂点を使うため、間引きで
値が変わります。CI門は `diagnostics=False` として診断経路を実行しません。

## 作り直し方

元のBOP T-LESSを変更せず、repoルートから次を実行します。

```text
PYTHONUTF8=1 py -3.11 tools/make_tless_subset.py "<T-LESS root>"
```

`<T-LESS root>` を省略した場合は `FULLSEYE_TLESS_DATA`、未設定なら
`~/fullseye_data/tless` を読みます。期待値の記録は次のrepo内の道具で作り直せます。

```text
PYTHONUTF8=1 py -3.11 tools/make_tless_subset.py --record-expected
```

生成器は出力を作り直し、`SHA256SUMS` も決定的に更新します。
"""


def _sha256(path: Path) -> str:
    """ファイルのSHA-256を返す。/ Return the file SHA-256."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(HASH_BLOCK_BYTES), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: object) -> None:
    """JSONをUTF-8/LFで決定的に書く。/ Write deterministic UTF-8/LF JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _read_object(path: Path) -> dict:
    """JSON objectだけを受ける。/ Read a JSON object, failing closed otherwise."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _copy(source: Path, destination: Path) -> None:
    """元バイトをそのまま複写する。/ Copy source bytes unchanged."""
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def _model_vertex_indices(vertex_count: int, requested_count: int) -> np.ndarray:
    """PoCの_capでモデル頂点添字を選ぶ。/ Select model indices through PoC _cap."""
    index_points = np.arange(vertex_count, dtype=np.int64).reshape(-1, 1)
    unused_normals = np.empty_like(index_points)
    selected, _unused = _cap(index_points, unused_normals, requested_count)
    return selected[:, 0]


def _evaluation_vertex_indices(vertex_count: int) -> np.ndarray:
    """PoCの評価点関数でCAD頂点添字を選ぶ。/ Select CAD indices through the PoC."""
    index_points = np.arange(vertex_count, dtype=np.int64).reshape(-1, 1)
    return _evaluation_points(index_points)[:, 0]


def _thin_ply(
        source: Path,
        destination: Path,
        select_indices: Callable[[int], np.ndarray],
) -> None:
    """PoCの一様添字にある頂点だけを残す。/ Keep the PoC's uniform vertex sample."""
    lines = source.read_bytes().splitlines(keepends=True)
    try:
        header_end = next(index for index, line in enumerate(lines) if line.rstrip(b"\r\n") == b"end_header")
    except StopIteration as exc:
        raise ValueError(f"PLY end_header is missing: {source}") from exc
    header = lines[:header_end + 1]
    vertex_rows = [line for line in header if line.startswith(b"element vertex ")]
    face_rows = [line for line in header if line.startswith(b"element face ")]
    if len(vertex_rows) != 1 or len(face_rows) != 1 or b"format ascii 1.0" not in b"".join(header):
        raise ValueError(f"unexpected T-LESS PLY header: {source}")
    vertex_count = int(vertex_rows[0].split()[2])
    if len(lines) < header_end + 1 + vertex_count:
        raise ValueError(f"PLY vertex rows are truncated: {source}")
    indices = select_indices(vertex_count)
    kept_count = len(indices)
    vertices = lines[header_end + 1:header_end + 1 + vertex_count]

    output_header: list[bytes] = []
    in_face = False
    newline = b"\r\n" if vertex_rows[0].endswith(b"\r\n") else b"\n"
    for line in header:
        stripped = line.rstrip(b"\r\n")
        if stripped.startswith(b"element vertex "):
            output_header.append(f"element vertex {kept_count}".encode("ascii") + newline)
            continue
        if stripped.startswith(b"element face "):
            in_face = True
            continue
        if in_face and stripped.startswith(b"property "):
            continue
        if stripped.startswith(b"element "):
            in_face = False
        output_header.append(line)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as handle:
        handle.writelines(output_header)
        handle.writelines(vertices[int(index)] for index in indices)


def _write_checksums(root: Path) -> None:
    """SHA256SUMS自身を除く全収録ファイルを列挙する。/ Hash every payload file."""
    checksum_path = root / "SHA256SUMS"
    files = sorted(path for path in root.rglob("*") if path.is_file() and path != checksum_path)
    rows = [f"{_sha256(path)}  {path.relative_to(root).as_posix()}" for path in files]
    checksum_path.write_text("\n".join(rows) + "\n", encoding="ascii", newline="\n")


def build_subset(source_root: Path, output_root: Path = DEFAULT_OUTPUT) -> Path:
    """subsetを一時場所で組み立てて置換する。/ Build the subset atomically."""
    source_root = source_root.resolve()
    output_root = output_root.resolve()
    if (output_root == source_root
            or output_root.is_relative_to(source_root)
            or source_root.is_relative_to(output_root)):
        raise ValueError("output and read-only source root must not contain each other")
    output_parent = output_root.parent
    output_parent.mkdir(parents=True, exist_ok=True)
    scene_source = source_root / "test_primesense" / f"{SUBSET_SCENE_ID:06d}"
    image_key = str(SUBSET_IMAGE_ID)
    with tempfile.TemporaryDirectory(prefix="tless_subset.", dir=output_parent) as temporary:
        staging = Path(temporary) / output_root.name
        scene_destination = staging / "test_primesense" / f"{SUBSET_SCENE_ID:06d}"
        for name in ("scene_camera.json", "scene_gt.json", "scene_gt_info.json"):
            source_value = _read_object(scene_source / name)
            if image_key not in source_value:
                raise ValueError(f"image {image_key} is missing from {name}")
            selected = source_value[image_key]
            if name in {"scene_gt.json", "scene_gt_info.json"}:
                if not isinstance(selected, list) or len(selected) != SOURCE_INSTANCE_COUNT:
                    raise ValueError(f"{name} image {image_key} must have {SOURCE_INSTANCE_COUNT} instances")
            _write_json(scene_destination / name, {image_key: selected})

        image_name = f"{SUBSET_IMAGE_ID:06d}.png"
        _copy(scene_source / "depth" / image_name, scene_destination / "depth" / image_name)
        _copy(scene_source / "rgb" / image_name, scene_destination / "rgb" / image_name)
        for instance_index, _object_id in enumerate(SUBSET_OBJECT_IDS):
            mask_name = f"{SUBSET_IMAGE_ID:06d}_{instance_index:06d}.png"
            _copy(scene_source / "mask_visib" / mask_name, scene_destination / "mask_visib" / mask_name)

        source_info = _read_object(source_root / "models_reconst" / "models_info.json")
        object_keys = tuple(str(object_id) for object_id in SUBSET_OBJECT_IDS)
        if any(key not in source_info for key in object_keys):
            raise ValueError(f"models_info.json lacks one of {object_keys}")
        _write_json(staging / "models_reconst" / "models_info.json",
                    {key: source_info[key] for key in object_keys})
        for object_id in SUBSET_OBJECT_IDS:
            filename = f"obj_{object_id:06d}.ply"
            _thin_ply(source_root / "models_reconst" / filename,
                      staging / "models_reconst" / filename,
                      lambda vertex_count: _model_vertex_indices(
                          vertex_count, ADOPTED_CONFIG.model_points))
            _thin_ply(source_root / "models_cad" / filename,
                      staging / "models_cad" / filename,
                      _evaluation_vertex_indices)

        (staging / "README.md").write_text(README_TEXT, encoding="utf-8", newline="\n")
        _write_checksums(staging)
        if output_root.exists():
            if output_root.is_symlink() or not output_root.is_dir():
                raise ValueError(f"output exists but is not a replaceable directory: {output_root}")
            shutil.rmtree(output_root)
        staging.replace(output_root)
    return output_root


def _measurement_snapshot() -> dict:
    """主経路1回の期待値候補を返す。/ Measure one primary-chain candidate."""
    _scenes, rows = run_real(
        DEFAULT_OUTPUT,
        ADOPTED_CONFIG,
        diagnostics=False,
        scene_ids=(SUBSET_SCENE_ID,),
        object_ids=SUBSET_OBJECT_IDS,
    )
    objects = {}
    for row in rows:
        metrics = row["metrics"]
        objects[str(row["obj_id"])] = {
            field: float(metrics[field])
            for field in EXPECTED_CONTINUOUS_METRIC_FIELDS
        }
        objects[str(row["obj_id"])]["success_mssd_le_0_2d"] = bool(
            metrics["mssd"] <= MSSD_FAILURE_FRACTION * row["diameter"])
    if set(objects) != {str(object_id) for object_id in SUBSET_OBJECT_IDS}:
        raise RuntimeError(f"measured objects do not match the subset: {sorted(objects)}")
    ar_mssd, ar_mspd = average_recall(_metric_rows(rows, "metrics"))
    return {"ar_mssd": float(ar_mssd), "ar_mspd": float(ar_mspd), "objects": objects}


def _maximum_metric_delta(reference: dict, measured: dict) -> float:
    """初回との連続値の最大差を返す。/ Return the largest continuous delta."""
    return max(
        abs(measured["objects"][object_id][field]
            - reference["objects"][object_id][field])
        for object_id in reference["objects"]
        for field in EXPECTED_CONTINUOUS_METRIC_FIELDS
    )


def record_expected() -> Path:
    """repo内subsetを反復実測して期待値を書く。/ Record repeated gate measurements."""
    snapshots = [
        _measurement_snapshot()
        for _run_index in range(EXPECTED_MEASUREMENT_RUN_COUNT)
    ]
    reference = snapshots[0]
    run_deltas = [
        _maximum_metric_delta(reference, measured)
        for measured in snapshots
    ]
    reference_discrete = {
        "ar_mssd": reference["ar_mssd"],
        "ar_mspd": reference["ar_mspd"],
        "success": {
            object_id: measured["success_mssd_le_0_2d"]
            for object_id, measured in reference["objects"].items()
        },
    }
    for run_index, measured in enumerate(snapshots, start=1):
        measured_discrete = {
            "ar_mssd": measured["ar_mssd"],
            "ar_mspd": measured["ar_mspd"],
            "success": {
                object_id: values["success_mssd_le_0_2d"]
                for object_id, values in measured["objects"].items()
            },
        }
        if measured_discrete != reference_discrete:
            raise RuntimeError(f"discrete gate result changed on run {run_index}")
    value = {
        **reference,
        "command": EXPECTED_COMMAND,
        "conditions": [
            f"same process, run {run_index}"
            for run_index in range(1, EXPECTED_MEASUREMENT_RUN_COUNT + 1)
        ],
        "created_at": date.today().isoformat(),
        "diagnostics": False,
        "max_continuous_metric_delta": max(run_deltas),
        "object_ids": list(SUBSET_OBJECT_IDS),
        "run_max_continuous_metric_deltas": run_deltas,
        "runs": EXPECTED_MEASUREMENT_RUN_COUNT,
        "scene_ids": [SUBSET_SCENE_ID],
        "source_tool": EXPECTED_SOURCE_TOOL,
        "versions": {
            "numpy": np.__version__,
            "python": platform.python_version(),
            "scipy": scipy.__version__,
        },
    }
    _write_json(EXPECTED_OUTPUT, value)
    return EXPECTED_OUTPUT


def main() -> None:
    """CLI入口。/ CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", nargs="?", type=Path,
                        help="read-only extracted BOP T-LESS root")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="subset output directory")
    parser.add_argument("--record-expected", action="store_true",
                        help="measure the repository subset repeatedly and record gate values")
    args = parser.parse_args()
    if args.record_expected:
        if args.source_root is not None:
            parser.error("--record-expected does not accept source_root")
        output = record_expected()
        print(f"recorded {output}: {EXPECTED_MEASUREMENT_RUN_COUNT} runs")
        return
    source_root = args.source_root or Path(os.environ.get(DATA_ENV, DEFAULT_DATA))
    output = build_subset(source_root, args.output)
    total_bytes = sum(path.stat().st_size for path in output.rglob("*") if path.is_file())
    print(f"built {output}: {total_bytes} bytes")


if __name__ == "__main__":
    main()
