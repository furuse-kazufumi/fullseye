# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pybind11 C ABI bridge / pybind11 C ABI ブリッジ。

The public C boundary accepts only the five scoped v1 operator IDs.  This module
keeps JSON validation and the Python calls in one place; the C++ side owns all
pointer, shape, stride, overflow, and lifetime checks.

公開 C 境界では、層を明記した v1 の 5 演算子だけを受け付ける。JSON の厳格な検証と
Python 呼び出しをこのモジュールに集め、ポインタ・形・ストライド・あふれ・寿命は
C++ 側で検査する。
"""
from __future__ import annotations

import json
import math
import traceback

import numpy as np

from json_safety import _loads_limited

FS_OK = 0
FS_E_INVALID_ARG = 1
FS_E_TYPE = 2
FS_E_NO_BACKEND = 5
FS_E_UNSUPPORTED = 6
FS_E_OUT_OF_MEMORY = 7
FS_E_UNKNOWN_OP = 11
FS_E_BAD_PARAMS = 12
FS_E_PY_EXCEPTION = 13

_OPS = {
    "contract:threshold": ("contract", "threshold"),
    "contract:connection": ("contract", "connection"),
    "contract:measure_all": ("contract", "measure_all"),
    "registry:threshold": ("registry", "threshold"),
    "registry:blob_count": ("registry", "blob_count"),
}

_PARAMS = {
    "contract:threshold": {"lo", "hi"},
    "contract:connection": set(),
    "contract:measure_all": set(),
    "registry:threshold": {"a", "b"},
    "registry:blob_count": {"a", "b"},
}


class _Refuse(Exception):
    """Carry one stable ABI status / 安定 ABI の状態コードを運ぶ例外。"""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def _reject_constant(name: str):
    raise ValueError("%s is not a finite RFC 8259 number" % name)


def _params(op_id: str, text: str | None) -> dict:
    try:
        value = _loads_limited(text or "{}", label="params_json", parse_constant=_reject_constant)
    except (ValueError, RecursionError) as exc:
        raise _Refuse(FS_E_BAD_PARAMS, "params_json is not valid RFC 8259 JSON: %s" % exc) from exc
    if not isinstance(value, dict):
        raise _Refuse(FS_E_BAD_PARAMS, "params_json must be a JSON object")
    extra = set(value) - _PARAMS[op_id]
    if extra:
        raise _Refuse(FS_E_BAD_PARAMS, "unknown parameter(s): %s" % ", ".join(sorted(extra)))
    required = {"lo", "hi"} if op_id == "contract:threshold" else set()
    missing = required - set(value)
    if missing:
        raise _Refuse(FS_E_BAD_PARAMS, "missing parameter(s): %s" % ", ".join(sorted(missing)))
    defaults = {"a": 0.5, "b": 0.5} if op_id.startswith("registry:") else {}
    out = {**defaults, **value}
    for key, number in out.items():
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            raise _Refuse(FS_E_BAD_PARAMS, "parameter %s must be a JSON number" % key)
        number = float(number)
        if not math.isfinite(number) or not 0.0 <= number <= 1.0:
            raise _Refuse(FS_E_BAD_PARAMS, "parameter %s must be finite and in [0, 1]" % key)
        out[key] = number
    if op_id == "contract:threshold" and out["lo"] > out["hi"]:
        raise _Refuse(FS_E_INVALID_ARG, "lo must not exceed hi")
    return out


def _runs_to_mask(height: int, width: int, raw: bytes) -> np.ndarray:
    runs = np.frombuffer(raw, dtype=np.int32).reshape(-1, 3)
    mask = np.zeros((height, width), dtype=bool)
    for row, begin, end in runs:
        mask[int(row), int(begin):int(end)] = True
    return mask


def _input(value: dict):
    """Convert a native-owned input description / ネイティブ所有の入力記述を型付き値へ変換。"""
    import fslib

    kind = value["kind"]
    if kind == "image":
        # np.asarray is a view for F64 input.  Other acquisition formats are
        # explicitly promoted and normalized; they never rely on API coercion.
        array = np.asarray(value["array"])
        lo, hi = float(value["lo"]), float(value["hi"])
        if array.dtype == np.float64:
            return fslib.FImage(array, value_range=(lo, hi))
        return fslib.FImage((array.astype(np.float64) - lo) / (hi - lo), value_range=(0.0, 1.0))
    if kind == "region":
        return fslib.Region(_runs_to_mask(value["h"], value["w"], value["runs"]))
    if kind == "objectset":
        labels = np.zeros((value["h"], value["w"]), dtype=np.int32)
        for label, raw in enumerate(value["objects"], 1):
            labels[_runs_to_mask(value["h"], value["w"], raw)] = label
        return fslib.ObjectSet(labels, np.arange(1, len(value["objects"]) + 1, dtype=np.int32))
    raise _Refuse(FS_E_TYPE, "unsupported input kind: %r" % kind)


def _output(value, op_id: str) -> dict:
    """Copy a Python result into an ABI-neutral description / Python 結果を ABI 中立表現へ複製。"""
    import fslib

    if isinstance(value, fslib.Region):
        runs = np.ascontiguousarray(value.runs(), dtype=np.int32)
        return {"kind": "region", "h": int(value.shape[0]), "w": int(value.shape[1]),
                "runs": runs.tobytes()}
    if isinstance(value, fslib.ObjectSet):
        return {"kind": "objectset", "h": int(value.labels.shape[0]), "w": int(value.labels.shape[1]),
                "objects": [np.ascontiguousarray(value.region(i).runs(), dtype=np.int32).tobytes()
                            for i in range(len(value))]}
    if isinstance(value, fslib.Seq):
        values = np.ascontiguousarray(value.values(), dtype=np.float64)
        return {"kind": "tuple", "values": values.tobytes(), "count": int(values.size)}
    if isinstance(value, np.ndarray) and op_id == "contract:measure_all":
        values = np.ascontiguousarray(value, dtype=np.float64).reshape(-1)
        if not np.isfinite(values).all():
            raise _Refuse(FS_E_INVALID_ARG, "operator output contains NaN or infinity")
        return {"kind": "tuple", "values": values.tobytes(), "count": int(values.size)}
    if isinstance(value, np.ndarray) and op_id == "registry:threshold":
        return _output(fslib.Region(np.asarray(value) > 0.5), op_id)
    if isinstance(value, np.ndarray):
        if value.ndim != 2:
            raise _Refuse(FS_E_UNSUPPORTED, "only 2-D array outputs are supported")
        array = np.ascontiguousarray(value, dtype=np.float64)
        if not np.isfinite(array).all():
            raise _Refuse(FS_E_INVALID_ARG, "operator output contains NaN or infinity")
        return {"kind": "image", "h": int(array.shape[0]), "w": int(array.shape[1]),
                "lo": 0.0, "hi": 1.0, "pixels": array.tobytes()}
    if isinstance(value, (int, float, np.integer, np.floating)):
        real = float(value)
        if not math.isfinite(real):
            raise _Refuse(FS_E_INVALID_ARG, "operator output is NaN or infinity")
        return {"kind": "real", "value": real}
    raise _Refuse(FS_E_UNSUPPORTED, "unsupported output type: %s" % type(value).__name__)


def _code(exc: Exception) -> int:
    import fslib

    if isinstance(exc, fslib.FsBackendError | ImportError):
        return FS_E_NO_BACKEND
    if isinstance(exc, fslib.FsTypeError | TypeError):
        return FS_E_TYPE
    if isinstance(exc, (fslib.FsValueError, ValueError)):
        return FS_E_INVALID_ARG
    if isinstance(exc, MemoryError):
        return FS_E_OUT_OF_MEMORY
    return FS_E_PY_EXCEPTION


def _contract(name: str, values: list[dict], params: dict):
    import fslib

    if len(values) != 1:
        raise _Refuse(FS_E_INVALID_ARG, "%s requires exactly one input" % name)
    return getattr(fslib, name)(_input(values[0]), **params)


def _registry(name: str, values: list[dict], params: dict):
    import fullseye

    if len(values) != 1:
        raise _Refuse(FS_E_INVALID_ARG, "%s requires exactly one input" % name)
    value = values[0]
    if value["kind"] == "image":
        array = np.asarray(value["array"])
        lo, hi = float(value["lo"]), float(value["hi"])
        # Registry semantics are float64 [0, 1].  F64 unit-range input remains a
        # zero-copy view; other declared acquisition formats are normalized.
        if array.dtype == np.float64 and (lo, hi) == (0.0, 1.0):
            normalized = array
        else:
            normalized = (array.astype(np.float64) - lo) / (hi - lo)
    elif value["kind"] == "region":
        normalized = _runs_to_mask(value["h"], value["w"], value["runs"]).astype(np.float64)
    else:
        raise _Refuse(FS_E_TYPE, "registry operators require an image or region input")
    return fullseye.apply(normalized, name, params["a"], params["b"], coerce=False,
                          device="cpu", on_error="raise", allow_nonfinite=False)


def call(op_id: str, inputs: list[dict], params_json: str | None) -> dict:
    """Run one scoped operator and never let an exception cross pybind11.

    層付き演算子を 1 つ実行し、例外を pybind11 の外へ漏らさない。
    """
    try:
        if op_id not in _OPS:
            if ":" not in op_id:
                raise _Refuse(FS_E_UNKNOWN_OP, "operator IDs must include a contract: or registry: scope")
            raise _Refuse(FS_E_UNKNOWN_OP, "unknown operator ID: %s" % op_id)
        tier, name = _OPS[op_id]
        params = _params(op_id, params_json)
        value = _contract(name, inputs, params) if tier == "contract" else _registry(name, inputs, params)
        outputs = list(value) if isinstance(value, tuple) else [value]
        return {"status": FS_OK, "message": "", "outputs": [_output(v, op_id) for v in outputs]}
    except _Refuse as exc:
        return {"status": exc.status, "message": str(exc), "outputs": []}
    except Exception as exc:  # noqa: BLE001 -- C ABI must classify every Python exception
        return {"status": _code(exc),
                "message": "%s: %s\n%s" % (type(exc).__name__, str(exc)[:400], traceback.format_exc()[-800:]),
                "outputs": []}


def find_ops(query_json: str | None) -> str:
    """Return the fixed v1 catalogue filtered by a strict query object.

    厳格な問い合わせオブジェクトで固定 v1 カタログを絞り込む。
    """
    try:
        value = _loads_limited(query_json or "{}", label="query_json", parse_constant=_reject_constant)
    except (TypeError, ValueError) as exc:
        raise ValueError("query_json is not valid RFC 8259 JSON: %s" % exc) from exc
    if not isinstance(value, dict) or set(value) - {"query", "limit"}:
        raise ValueError("query_json must be an object containing only query and limit")
    query = value.get("query", "")
    limit = value.get("limit", len(_OPS))
    if not isinstance(query, str) or isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("query must be a string and limit an integer in [1, 100]")
    rows = [{"id": op_id, "tier": tier, "name": name}
            for op_id, (tier, name) in _OPS.items() if query.lower() in op_id.lower()][:limit]
    return json.dumps({"schema_version": 1, "ops": rows}, ensure_ascii=False, separators=(",", ":"))
