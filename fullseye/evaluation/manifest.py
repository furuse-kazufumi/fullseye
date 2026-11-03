# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Second-stage golden manifests for PoC evaluation.

The base format is ``examplefig``'s ordered ``figures.json`` list.  This module
keeps that list intact and adds the numerical, truth, gate, video-frame, and seed
records required to compare the physics behind the figures.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .result import CaseResult, GateResult
from .truth import TruthBundle


MANIFEST_SCHEMA = 1


def build_manifest(
    case: str,
    *,
    metrics: Mapping[str, Any],
    arrays: Mapping[str, Any],
    truth: TruthBundle,
    gates: Sequence[GateResult],
    figures: Sequence[Mapping[str, Any]],
    videos: Mapping[str, Mapping[str, Any]],
    seed: int | None,
) -> dict[str, Any]:
    """Build a JSON-safe second-stage golden manifest."""
    if not isinstance(case, str) or not case:
        raise ValueError("case must be a non-empty string")
    gate_values = list(gates)
    if not all(isinstance(gate, GateResult) for gate in gate_values):
        raise TypeError("gates must contain GateResult values")
    if seed != truth.seed:
        raise ValueError(f"manifest seed {seed!r} differs from truth seed {truth.seed!r}")
    return {
        "evaluation_manifest_schema": MANIFEST_SCHEMA,
        "case": case,
        "seed": seed,
        "metrics": _json_value(dict(metrics)),
        "arrays": {name: _array_summary(value) for name, value in sorted(arrays.items())},
        "truth": _truth_summary(truth),
        "gates": [_json_value(gate.as_dict()) for gate in gate_values],
        "figures": [_json_value(dict(row)) for row in figures],
        "videos": {name: _video_summary(value) for name, value in sorted(videos.items())},
    }


def manifest_from_case(
    result: CaseResult,
    *,
    arrays: Mapping[str, Any],
    truth: TruthBundle,
    figures: Sequence[Mapping[str, Any]],
    videos: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    return build_manifest(
        result.case,
        metrics=result.metrics,
        arrays=arrays,
        truth=truth,
        gates=result.gates,
        figures=figures,
        videos=videos,
        seed=result.seed,
    )


def write_manifest(path, manifest: Mapping[str, Any]) -> Path:
    """Write deterministic UTF-8 JSON and return its path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(_json_value(dict(manifest)), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    target.write_text(payload, encoding="utf-8")
    return target


def read_manifest(path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("evaluation manifest root must be an object")
    if value.get("evaluation_manifest_schema") != MANIFEST_SCHEMA:
        raise ValueError("unsupported evaluation manifest schema")
    return value


def compare_manifests(
    actual: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    rtol: float = 0.0,
    atol: float = 0.0,
) -> list[str]:
    """Return human-readable differences; an empty list means parity."""
    if rtol < 0 or atol < 0 or not math.isfinite(rtol) or not math.isfinite(atol):
        raise ValueError("rtol and atol must be finite and non-negative")
    differences: list[str] = []
    _compare(_json_value(dict(actual)), _json_value(dict(expected)), "$", rtol, atol, differences)
    return differences


def summarize_video_frames(
    frames: Sequence[Any],
    *,
    capture_fps: float,
    playback_fps: float,
) -> dict[str, Any]:
    """Frame count/fps and first-middle-last hashes before encoding."""
    seq = [np.asarray(frame) for frame in frames]
    if not seq:
        raise ValueError("video frame sequence must not be empty")
    shapes = {frame.shape for frame in seq}
    dtypes = {frame.dtype.str for frame in seq}
    if len(shapes) != 1 or len(dtypes) != 1:
        raise ValueError("video frames must have one shape and dtype")
    if capture_fps <= 0 or playback_fps <= 0:
        raise ValueError("video fps values must be positive")
    mid = len(seq) // 2
    return {
        "frame_count": len(seq),
        "capture_fps": float(capture_fps),
        "playback_fps": float(playback_fps),
        "shape": list(seq[0].shape),
        "dtype": seq[0].dtype.str,
        "frame_hashes": {
            "first": _array_hash(seq[0]),
            "middle": _array_hash(seq[mid]),
            "last": _array_hash(seq[-1]),
        },
    }


def _array_summary(value: Any) -> dict[str, Any]:
    arr = np.asarray(value)
    summary: dict[str, Any] = {
        "shape": list(arr.shape),
        "dtype": arr.dtype.str,
        "sha256": _array_hash(arr),
    }
    if np.issubdtype(arr.dtype, np.number) or arr.dtype == np.bool_:
        finite = np.isfinite(arr) if np.issubdtype(arr.dtype, np.number) else np.ones(arr.shape, bool)
        values = arr[finite]
        summary["finite_count"] = int(values.size)
        summary["nan_count"] = int(np.count_nonzero(np.isnan(arr))) if np.issubdtype(arr.dtype, np.inexact) else 0
        if values.size:
            fv = values.astype(np.float64)
            summary.update(
                {
                    "min": float(fv.min()),
                    "max": float(fv.max()),
                    "mean": float(fv.mean()),
                    "std": float(fv.std()),
                }
            )
    return summary


def _truth_summary(truth: TruthBundle) -> dict[str, Any]:
    return {
        "fields": {name: _array_summary(value) for name, value in sorted(truth.fields.items())},
        "units": dict(sorted(truth.units.items())),
        "frames": dict(sorted(truth.frames.items())),
        "masks": {name: _array_summary(value) for name, value in sorted(truth.masks.items())},
        "provenance": _json_value(dict(truth.provenance)),
        "seed": truth.seed,
    }


def _video_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {"frame_count", "capture_fps", "playback_fps", "frame_hashes"}
    missing = required - set(value)
    if missing:
        raise ValueError(f"video summary lacks {sorted(missing)}")
    hashes = dict(value["frame_hashes"])
    if set(hashes) != {"first", "middle", "last"}:
        raise ValueError("video frame_hashes must contain first/middle/last")
    return _json_value(dict(value))


def _array_hash(arr: np.ndarray) -> str:
    value = np.ascontiguousarray(arr)
    h = hashlib.sha256()
    h.update(value.dtype.str.encode("ascii"))
    h.update(json.dumps(list(value.shape), separators=(",", ":")).encode("ascii"))
    h.update(value.tobytes())
    return h.hexdigest()


def _json_value(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return {"nonfinite": str(value)}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"value of type {type(value).__name__} is not JSON-safe")


def _compare(actual: Any, expected: Any, path: str, rtol: float, atol: float, out: list[str]) -> None:
    if isinstance(actual, dict) and isinstance(expected, dict):
        for key in sorted(set(actual) | set(expected)):
            child = f"{path}.{key}"
            if key not in actual:
                out.append(f"{child}: missing from actual")
            elif key not in expected:
                out.append(f"{child}: extra in actual")
            else:
                _compare(actual[key], expected[key], child, rtol, atol, out)
        return
    if isinstance(actual, list) and isinstance(expected, list):
        if len(actual) != len(expected):
            out.append(f"{path}: length {len(actual)} != {len(expected)}")
        for index, (left, right) in enumerate(zip(actual, expected)):
            _compare(left, right, f"{path}[{index}]", rtol, atol, out)
        return
    numeric = (
        isinstance(actual, (int, float))
        and not isinstance(actual, bool)
        and isinstance(expected, (int, float))
        and not isinstance(expected, bool)
    )
    if numeric:
        if not math.isclose(float(actual), float(expected), rel_tol=rtol, abs_tol=atol):
            out.append(f"{path}: {actual!r} != {expected!r}")
    elif actual != expected:
        out.append(f"{path}: {actual!r} != {expected!r}")
