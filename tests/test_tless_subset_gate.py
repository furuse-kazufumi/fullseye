# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

import numpy as np
import pytest

from tools.make_tless_subset import (
    SUBSET_OBJECT_IDS,
    SUBSET_SCENE_ID,
    _evaluation_vertex_indices,
    _model_vertex_indices,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUBSET_ROOT = ROOT / "tests" / "data" / "tless_subset"
EXPECTED_PATH = ROOT / "tests" / "data" / "tless_subset_expected.json"
DEFAULT_POC_PATH = ROOT / "examples" / "poc_real_tless_6dof.py"

# 切り出し生成器を正本にする。/ The subset builder is the single source of truth.
GATE_SCENE_IDS = (SUBSET_SCENE_ID,)
GATE_OBJECT_IDS = SUBSET_OBJECT_IDS
GATE_SCENE_COUNT = len(GATE_SCENE_IDS)
GATE_OBJECT_COUNT = len(GATE_OBJECT_IDS)

# 5実行の最大差0。/ Five runs had zero delta. 1e-6 allows only cross-platform rounding;
# it is over six orders below the smallest 1.089 mm classification margin. No relative tolerance.
CONTINUOUS_METRIC_ABS_TOLERANCE = 1e-6
CONTINUOUS_METRIC_REL_TOLERANCE = 0.0
CONTINUOUS_METRIC_FIELDS = ("mssd", "mspd", "rot_deg", "trans_mm")

# PoCのRECORDEDと同じ2026-11-01の20場面実行ログにある独立照合値。
# 場面2のMSSD > 0.2d失敗対象はobj 5だけで、obj 6は成功している。
# / Independent classification from the same 20-scene run as PoC RECORDED.
RECORDED_2026_11_01_SCENE_2_MSSD_SUCCESS = {5: False, 6: True}

# briefの目安5 MiBと1分。/ Brief limits; measured 0.92 MB and 3.10--3.44 s on 2026-11-22.
SUBSET_SIZE_LIMIT_BYTES = 5 * 1024 * 1024
GATE_TIMEOUT_SECONDS = 60
HASH_BLOCK_BYTES = 1024 * 1024
SHA256_HEX_LENGTH = 64
SHA256_FIELDS_PER_ROW = 2

# fail-closed用の代表値。/ Representative public-range and absent-subset validation inputs.
OUT_OF_RANGE_SCENE_ID = 21
ABSENT_SUBSET_SCENE_ID = 1
NON_INTEGER_SCENE_ID = "two"
OUT_OF_RANGE_OBJECT_ID = 31
NON_INTEGER_OBJECT_ID = "five"
MISSING_SUBSET_MODEL_OBJECT_ID = 7
INVALID_ENV_TEXT = "2,not-an-integer"

# 生成器とPoCの抽出規則をフルデータ無しで通す合成配列の大きさ。
# / Synthetic sizes that exercise both sampling branches without full data.
SYNTHETIC_MODEL_VERTEX_COUNT = 17
SYNTHETIC_MODEL_POINT_COUNT = 7
SYNTHETIC_EVALUATION_VERTEX_COUNT = 607


def _load_poc():
    """このcheckoutのPoC本体をimportする。/ Import this checkout's PoC under test."""
    path = DEFAULT_POC_PATH.resolve()
    examples = str(ROOT / "examples")
    if examples not in sys.path:
        sys.path.insert(0, examples)
    spec = importlib.util.spec_from_file_location("poc_real_tless_6dof_gate", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import T-LESS PoC: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


POC = _load_poc()


def _sha256(path: Path) -> str:
    """大きな画像も固定メモリでhashする。/ Hash a file with bounded memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(HASH_BLOCK_BYTES), b""):
            digest.update(block)
    return digest.hexdigest()


def _checksum_rows(root: Path) -> dict[str, str]:
    """SHA256SUMSを曖昧な行なしで読む。/ Parse SHA256SUMS fail-closed."""
    rows: dict[str, str] = {}
    for line_number, line in enumerate(
            (root / "SHA256SUMS").read_text(encoding="ascii").splitlines(), start=1):
        fields = line.split(maxsplit=1)
        if (len(fields) != SHA256_FIELDS_PER_ROW
                or len(fields[0]) != SHA256_HEX_LENGTH
                or any(character not in "0123456789abcdef" for character in fields[0])):
            raise AssertionError(f"SHA256SUMS line {line_number} is invalid: {line!r}")
        relative = fields[1]
        if relative in rows or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise AssertionError(f"SHA256SUMS line {line_number} has an unsafe/duplicate path: {relative}")
        rows[relative] = fields[0]
    return rows


def test_tless_subset_bytes_match_the_manifest():
    """欠落・追加・1 byte差を赤にする。/ Reject missing, extra, or changed bytes."""
    root = DEFAULT_SUBSET_ROOT
    expected = _checksum_rows(root)
    actual_files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS"
    }
    assert actual_files == set(expected)
    mismatches = {
        relative: {"expected": digest, "actual": _sha256(root / relative)}
        for relative, digest in expected.items()
        if _sha256(root / relative) != digest
    }
    assert not mismatches, f"T-LESS subset checksum mismatch: {mismatches}"
    total_bytes = sum(path.stat().st_size for path in root.rglob("*") if path.is_file())
    assert total_bytes <= SUBSET_SIZE_LIMIT_BYTES, (
        f"T-LESS subset is {total_bytes} bytes > {SUBSET_SIZE_LIMIT_BYTES} bytes")


@pytest.mark.timeout(GATE_TIMEOUT_SECONDS)
def test_tless_subset_runs_the_real_primary_chain_and_matches_measurement():
    """実データで主経路を測る。/ Measure depth-to-normals-to-plane-to-PPF-to-ICP."""
    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    started = time.perf_counter()
    scenes, rows = POC.run_real(
        DEFAULT_SUBSET_ROOT,
        POC.DEFAULT_CONFIG,
        diagnostics=False,
        scene_ids=GATE_SCENE_IDS,
        object_ids=GATE_OBJECT_IDS,
    )
    elapsed_seconds = time.perf_counter() - started
    assert len(scenes) == GATE_SCENE_COUNT
    assert len(rows) == GATE_OBJECT_COUNT
    assert [scene["scene"] for scene in scenes] == list(GATE_SCENE_IDS)
    assert [row["obj_id"] for row in rows] == list(GATE_OBJECT_IDS)
    assert rows
    assert all("絞り込み" in row["condition"] for row in rows)

    actual_by_object = {str(row["obj_id"]): row for row in rows}
    expected_objects = expected["objects"]
    assert set(expected_objects) == {str(object_id) for object_id in GATE_OBJECT_IDS}
    for object_id, measured in expected_objects.items():
        actual = actual_by_object[object_id]
        for field in CONTINUOUS_METRIC_FIELDS:
            assert actual["metrics"][field] == pytest.approx(
                measured[field], abs=CONTINUOUS_METRIC_ABS_TOLERANCE,
                rel=CONTINUOUS_METRIC_REL_TOLERANCE)
        success = (actual["metrics"]["mssd"]
                   <= POC.MSSD_FAILURE_FRACTION * actual["diameter"])
        assert success is measured["success_mssd_le_0_2d"]
        assert success is RECORDED_2026_11_01_SCENE_2_MSSD_SUCCESS[int(object_id)]

    ar_mssd, ar_mspd = POC.average_recall(POC._metric_rows(rows, "metrics"))
    assert ar_mssd == expected["ar_mssd"]
    assert ar_mspd == expected["ar_mspd"]
    assert elapsed_seconds < GATE_TIMEOUT_SECONDS


@pytest.mark.parametrize("scene_ids, message", [
    ((NON_INTEGER_SCENE_ID,), "整数"),
    ((OUT_OF_RANGE_SCENE_ID,), "範囲外"),
    ((ABSENT_SUBSET_SCENE_ID,), "場面ディレクトリが無い"),
])
def test_tless_scene_filter_fails_closed(scene_ids, message):
    """不正・範囲外・データに無い場面を止める。/ Reject invalid/missing scenes."""
    with pytest.raises(ValueError, match=message):
        POC.first_bop19_scene_specs(DEFAULT_SUBSET_ROOT, scene_ids)


@pytest.mark.parametrize("object_ids, message", [
    ((NON_INTEGER_OBJECT_ID,), "整数"),
    ((OUT_OF_RANGE_OBJECT_ID,), "範囲外"),
    ((MISSING_SUBSET_MODEL_OBJECT_ID,), "モデル情報が無い"),
])
def test_tless_object_filter_fails_closed(object_ids, message):
    """不正・範囲外・モデル無し物体を止める。/ Reject invalid/unavailable objects."""
    with pytest.raises(ValueError, match=message):
        POC.run_real(
            DEFAULT_SUBSET_ROOT,
            POC.DEFAULT_CONFIG,
            diagnostics=False,
            scene_ids=GATE_SCENE_IDS,
            object_ids=object_ids,
        )


def test_tless_environment_filter_fails_closed(monkeypatch):
    """環境変数の非整数を止める。/ Reject a non-integer environment filter."""
    monkeypatch.setenv(POC.SCENES_ENV, INVALID_ENV_TEXT)
    with pytest.raises(ValueError, match="comma区切りの整数"):
        POC._parse_id_env(
            POC.SCENES_ENV,
            minimum=POC.SCENE_ID_MIN,
            maximum=POC.SCENE_ID_MAX,
        )


def test_subset_builder_model_selection_matches_poc_cap():
    """生成器のreconst抽出をPoC正本と照合する。/ Match builder model sampling to PoC."""
    points = np.arange(SYNTHETIC_MODEL_VERTEX_COUNT, dtype=np.int64).reshape(-1, 1)
    normals = np.empty_like(points)
    selected, _unused = POC._cap(points, normals, SYNTHETIC_MODEL_POINT_COUNT)
    generated = _model_vertex_indices(
        SYNTHETIC_MODEL_VERTEX_COUNT, SYNTHETIC_MODEL_POINT_COUNT)
    assert np.array_equal(generated, selected[:, 0])


def test_subset_builder_evaluation_selection_matches_poc():
    """生成器のCAD抽出をPoC正本と照合する。/ Match builder CAD sampling to PoC."""
    points = np.arange(SYNTHETIC_EVALUATION_VERTEX_COUNT, dtype=np.int64).reshape(-1, 1)
    selected = POC._evaluation_points(points)
    generated = _evaluation_vertex_indices(SYNTHETIC_EVALUATION_VERTEX_COUNT)
    assert np.array_equal(generated, selected[:, 0])
