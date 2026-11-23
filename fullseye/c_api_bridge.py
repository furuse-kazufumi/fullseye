# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Typed-ledger C API bridge / 型台帳を正本にする C API ブリッジ。

The callable set is derived from the contract and registry type ledgers.  An
operator is callable exactly when both sides use only image, region, color,
volume, or feature; unsupported sorts are reported with their reason rather
than silently omitted.  Parameter objects remain closed schemas.

呼出可能集合は contract / registry の型台帳から導出する。入出力が image、region、
color、volume、feature だけの op を呼出可能とし、他の sort は黙って落とさず理由を
返す。パラメータ JSON は従来どおり閉じた schema で検査する。
"""
from __future__ import annotations

import inspect
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

#: C SDK で値として運べる型。This is the sole reachability rule / 到達可能性の唯一の規則。
ABI_SORTS = frozenset(("image", "region", "color", "volume", "feature"))
_ANN_SORT = {"FImage": "image", "Region": "region", "ObjectSet": "objectset"}


class _Refuse(Exception):
    """Carry one stable ABI status / 安定 ABI の状態コードを運ぶ。"""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def _reject_constant(name: str):
    raise ValueError("%s is not a finite RFC 8259 number" % name)


def _contract_entries() -> list[dict]:
    """Read contract types from fslib signatures / fslib の注釈から contract 型を読む。"""
    import fslib
    from .abi_bridge import CONTRACT_OPS

    rows = []
    for name in CONTRACT_OPS:
        sig = inspect.signature(getattr(fslib, name), eval_str=True)
        first = next(iter(sig.parameters.values()))
        in_sort = _ANN_SORT.get(getattr(first.annotation, "__name__", str(first.annotation)), "unknown")
        ret = sig.return_annotation
        out_sort = _ANN_SORT.get(getattr(ret, "__name__", str(ret)), "unknown")
        rows.append({"id": "contract:" + name, "tier": "contract", "name": name,
                     "in_sort": in_sort, "out_sort": out_sort})
    return rows


def _entries() -> list[dict]:
    """Return all ledger rows and an explicit callable/rejection decision."""
    import ops

    rows = _contract_entries()
    rows += [{"id": "registry:" + op.name, "tier": "registry", "name": op.name,
              "in_sort": op.in_sort, "out_sort": op.out_sort,
              "category": op.category, "halcon": op.halcon} for op in ops.REGISTRY]
    for row in rows:
        unsupported = sorted({row["in_sort"], row["out_sort"]} - ABI_SORTS)
        row["callable"] = not unsupported
        row["reason"] = "" if not unsupported else (
            "C ABI cannot represent declared sort(s): " + ", ".join(unsupported))
    return rows


def catalog() -> dict:
    """Machine-readable C SDK operator ledger / 機械可読 C SDK op 台帳。"""
    rows = _entries()
    callable_rows = [row for row in rows if row["callable"]]
    return {"schema_version": 2, "abi_sorts": sorted(ABI_SORTS),
            "n_ops": len(rows), "n_callable": len(callable_rows),
            "n_rejected": len(rows) - len(callable_rows), "ops": rows}


def catalog_json() -> str:
    return json.dumps(catalog(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _params(row: dict, text: str | None) -> dict:
    try:
        value = _loads_limited(text or "{}", label="params_json", parse_constant=_reject_constant)
    except (ValueError, RecursionError) as exc:
        raise _Refuse(FS_E_BAD_PARAMS, "params_json is not valid RFC 8259 JSON: %s" % exc) from exc
    if not isinstance(value, dict):
        raise _Refuse(FS_E_BAD_PARAMS, "params_json must be a JSON object")
    if row["tier"] == "registry":
        extra = set(value) - {"a", "b"}
        if extra:
            raise _Refuse(FS_E_BAD_PARAMS, "unknown parameter(s): %s" % ", ".join(sorted(extra)))
        out = {"a": 0.5, "b": 0.5, **value}
        for key, number in out.items():
            if isinstance(number, bool) or not isinstance(number, (int, float)):
                raise _Refuse(FS_E_BAD_PARAMS, "parameter %s must be a JSON number" % key)
            if not math.isfinite(float(number)) or not 0.0 <= float(number) <= 1.0:
                raise _Refuse(FS_E_BAD_PARAMS, "parameter %s must be finite and in [0, 1]" % key)
            out[key] = float(number)
        return out
    from .abi_bridge import _contract_schema
    from .mcp.server import ArgError, _validate
    schema = _contract_schema(row["name"])
    try:
        _validate(schema, value)
    except ArgError as exc:
        raise _Refuse(FS_E_BAD_PARAMS, "op %r: %s" % (row["id"], exc)) from exc
    return {key: value[key] if key in value else spec["default"]
            for key, spec in schema["properties"].items()
            if key in value or "default" in spec}


def _runs_to_mask(height: int, width: int, raw: bytes) -> np.ndarray:
    runs = np.frombuffer(raw, dtype=np.int32).reshape(-1, 3)
    mask = np.zeros((height, width), dtype=bool)
    for row, begin, end in runs:
        mask[int(row), int(begin):int(end)] = True
    return mask


def _input(value: dict):
    """Convert a native-owned value without coercion / 暗黙変換せず native 値を戻す。"""
    import fslib

    kind = value["kind"]
    if kind == "image":
        array = np.asarray(value["array"])
        lo, hi = float(value["lo"]), float(value["hi"])
        if array.dtype == np.float64:
            return fslib.FImage(array, value_range=(lo, hi))
        return fslib.FImage((array.astype(np.float64) - lo) / (hi - lo), value_range=(0.0, 1.0))
    if kind == "region":
        return fslib.Region(_runs_to_mask(value["h"], value["w"], value["runs"]))
    if kind in ("color", "volume"):
        return np.asarray(value["array"], dtype=np.float64)
    if kind == "feature":
        number = float(value["value"])
        if not math.isfinite(number):
            raise _Refuse(FS_E_INVALID_ARG, "feature must be finite")
        return number
    raise _Refuse(FS_E_TYPE, "unsupported input kind: %r" % kind)


def _output(value, row: dict) -> dict:
    """Copy one declared result type / 宣言された出力型だけを複製する。"""
    import fslib

    sort = row["out_sort"]
    if sort == "region":
        array = (value._mask if isinstance(value, fslib.Region)
                 else value.pixels if isinstance(value, fslib.FImage) else np.asarray(value))
        if array.ndim != 2:
            raise _Refuse(FS_E_UNSUPPORTED, "%s returned a non-2-D region" % row["id"])
        runs = np.ascontiguousarray(fslib.Region(array > 0.5).runs(), dtype=np.int32)
        return {"kind": "region", "h": int(array.shape[0]), "w": int(array.shape[1]),
                "runs": runs.tobytes()}
    if sort == "feature":
        array = np.asarray(value, dtype=np.float64).reshape(-1)
        if array.size != 1 or not np.isfinite(array[0]):
            raise _Refuse(FS_E_UNSUPPORTED, "%s returned a non-finite or non-scalar feature" % row["id"])
        return {"kind": "feature", "value": float(array[0])}
    if isinstance(value, fslib.FImage):
        value = value.pixels
    array = np.asarray(value, dtype=np.float64)
    want_dims = {"image": (2,), "color": (3,), "volume": (3, 4)}[sort]
    if array.ndim not in want_dims or (sort == "color" and array.shape[-1] != 3):
        raise _Refuse(FS_E_UNSUPPORTED, "%s returned shape %s, not declared %s" %
                      (row["id"], array.shape, sort))
    if not np.isfinite(array).all():
        raise _Refuse(FS_E_INVALID_ARG, "operator output contains NaN or infinity")
    array = np.ascontiguousarray(array, dtype=np.float64)
    if sort == "image":
        return {"kind": "image", "h": int(array.shape[0]), "w": int(array.shape[1]),
                "lo": 0.0, "hi": 1.0, "pixels": array.tobytes()}
    return {"kind": sort, "shape": list(map(int, array.shape)), "pixels": array.tobytes()}


def _run(row: dict, input_value, params: dict):
    if row["tier"] == "contract":
        import fslib
        return getattr(fslib, row["name"])(input_value, **params)
    import fullseye
    value = input_value
    if row["in_sort"] == "image":
        if not hasattr(input_value, "pixels"):
            raise _Refuse(FS_E_TYPE, "registry image input is not an image")
        value = np.asarray(input_value.pixels, dtype=np.float64)
        lo, hi = input_value.value_range
        value = (value - lo) / (hi - lo) if (lo, hi) != (0.0, 1.0) else value
    elif row["in_sort"] == "region":
        value = np.asarray(input_value._mask, dtype=np.float64)
    return fullseye.apply(value, row["name"], params["a"], params["b"], coerce=False,
                          device="cpu", on_error="raise", allow_nonfinite=False)


def call(op_id: str, inputs: list[dict], params_json: str | None) -> dict:
    """Run one scoped ledger op, fail closed, and never leak Python exceptions."""
    try:
        by_id = {row["id"]: row for row in _entries()}
        row = by_id.get(op_id)
        if row is None:
            if ":" not in op_id:
                raise _Refuse(FS_E_UNKNOWN_OP, "operator IDs must include a contract: or registry: scope")
            raise _Refuse(FS_E_UNKNOWN_OP, "unknown operator ID: %s" % op_id)
        if not row["callable"]:
            raise _Refuse(FS_E_UNSUPPORTED, "%s is not C-callable: %s" % (op_id, row["reason"]))
        if len(inputs) != 1:
            raise _Refuse(FS_E_INVALID_ARG, "%s requires exactly one input" % op_id)
        value = _input(inputs[0])
        actual = inputs[0]["kind"]
        if actual != row["in_sort"]:
            raise _Refuse(FS_E_TYPE, "%s requires %s, not %s" % (op_id, row["in_sort"], actual))
        output = _run(row, value, _params(row, params_json))
        return {"status": FS_OK, "message": "", "outputs": [_output(output, row)]}
    except _Refuse as exc:
        return {"status": exc.status, "message": str(exc), "outputs": []}
    except MemoryError:
        return {"status": FS_E_OUT_OF_MEMORY, "message": "out of memory", "outputs": []}
    except (TypeError, ValueError) as exc:
        return {"status": FS_E_TYPE, "message": "%s: %s" % (type(exc).__name__, str(exc)[:400]), "outputs": []}
    except Exception as exc:  # noqa: BLE001 -- C ABI must classify every Python exception
        return {"status": FS_E_PY_EXCEPTION,
                "message": "%s: %s\n%s" % (type(exc).__name__, str(exc)[:400], traceback.format_exc()[-800:]),
                "outputs": []}


def find_ops(query_json: str | None) -> str:
    """Return generated-ledger callable rows / 生成台帳の呼出可能行を返す。"""
    try:
        value = _loads_limited(query_json or "{}", label="query_json", parse_constant=_reject_constant)
    except (TypeError, ValueError) as exc:
        raise ValueError("query_json is not valid RFC 8259 JSON: %s" % exc) from exc
    if not isinstance(value, dict) or set(value) - {"query", "limit"}:
        raise ValueError("query_json must be an object containing only query and limit")
    query = value.get("query", "")
    if not isinstance(query, str):
        raise ValueError("query must be a string")
    rows = [row for row in _entries() if row["callable"] and query.lower() in row["id"].lower()]
    limit = value.get("limit", len(rows))
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
        raise ValueError("limit must be an integer in [1, 1000]")
    return json.dumps({"schema_version": 2, "n_callable": len(rows), "ops": rows[:limit]},
                      ensure_ascii=False, sort_keys=True, separators=(",", ":"))
