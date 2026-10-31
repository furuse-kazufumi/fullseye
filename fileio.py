# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0.
"""Dependency-light, in-memory file-format operators.

Writers in this module return text or bytes.  They never choose a path or touch
the filesystem; callers may download the result in Studio, send it over an API,
or save it explicitly.
"""
from __future__ import annotations

import csv
import datetime as _datetime
import io
import math
from collections.abc import Mapping

import numpy as np

__all__ = ["table_write_csv", "table_read_csv"]

_CSV_META_REQUIRED = ("source", "generated_at", "coordinate_meaning")
_MAX_CSV_CHARS = 256 * 1024 * 1024


def _csv_columns(table, op: str) -> dict[str, np.ndarray]:
    if not isinstance(table, Mapping):
        raise ValueError(f"{op}: table must be a mapping of column name to values")
    raw = table.get("columns") if set(table) >= {"columns", "units", "meta"} else table
    if not isinstance(raw, Mapping) or not raw:
        raise ValueError(f"{op}: table must contain at least one column")
    columns = {}
    length = None
    for name, values in raw.items():
        if not isinstance(name, str) or not name or any(ch in name for ch in "\r\n"):
            raise ValueError(f"{op}: invalid column name {name!r}")
        if name.startswith("#"):
            raise ValueError(f"{op}: column name {name!r} must not start with '#'")
        arr = np.asarray(values)
        if arr.ndim != 1:
            raise ValueError(f"{op}: column {name!r} must be one-dimensional, got {arr.shape!r}")
        if length is None:
            length = len(arr)
        elif len(arr) != length:
            raise ValueError(f"{op}: column {name!r} has {len(arr)} rows; expected {length}")
        columns[name] = arr
    return columns


def _csv_meta(meta, op: str) -> dict[str, str]:
    if not isinstance(meta, Mapping):
        raise ValueError(f"{op}: meta must be a mapping")
    missing = [key for key in _CSV_META_REQUIRED if not str(meta.get(key, "")).strip()]
    if missing:
        raise ValueError(f"{op}: meta is missing required key(s): {', '.join(missing)}")
    out = {}
    for key, value in meta.items():
        if not isinstance(key, str) or not key or ":" in key or any(c in key for c in "\r\n"):
            raise ValueError(f"{op}: invalid metadata key {key!r}")
        text = str(value)
        if any(c in text for c in "\r\n"):
            raise ValueError(f"{op}: metadata {key!r} contains a newline")
        out[key] = text
    try:
        _datetime.datetime.fromisoformat(out["generated_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{op}: meta['generated_at'] must be ISO 8601, got {out['generated_at']!r}") from exc
    return out


def _csv_cell(value, column: str, row: int):
    if isinstance(value, np.generic):
        value = value.item()
    if value is None:
        return ""
    if isinstance(value, (float, np.floating)):
        if math.isnan(float(value)):
            return "NaN"
        if not math.isfinite(float(value)):
            raise ValueError(f"table_write_csv: column {column!r} row {row} is infinite")
        return repr(float(value))
    if isinstance(value, (int, np.integer, bool, np.bool_)):
        return str(value)
    text = str(value)
    if "#" in text:
        raise ValueError(f"table_write_csv: column {column!r} row {row} contains '#'; comment-aware readers would truncate it")
    return text


def table_write_csv(table, *, units, meta):
    """単位と由来を持つ表を、pandas / MATLAB でも読める CSV 文字列にする(``text``)。

    ``table`` は ``{列名: 1-D 配列}``。``units`` は全列の単位を同じキーで持つ辞書、``meta`` は
    ``source``(出所)、``generated_at``(ISO 8601)、``coordinate_meaning``(座標の意味)を必ず持つ。
    1 行目は列名、2 行目は ``# units:``、続く ``# key: value`` 行はメタデータ、その後がデータ。
    ``pandas.read_csv(StringIO(text), comment="#")`` で列名と値を読み、MATLAB ではコメント行を除外して
    ``readtable`` で読める。浮動小数は Python の ``repr`` で丸めず、列長不一致・単位欠落・無限値は拒否する。

    呼び出し例: ``table_write_csv({"x": [1.0]}, units={"x": "mm"},
    meta={"source": "caliper", "generated_at": "2026-10-31T12:00:00+09:00",
    "coordinate_meaning": "x is right-handed"})``。
    """
    op = "table_write_csv"
    columns = _csv_columns(table, op)
    if not isinstance(units, Mapping):
        raise ValueError(f"{op}: units must be a mapping")
    missing = [name for name in columns if name not in units or not str(units[name]).strip()]
    extra = [name for name in units if name not in columns]
    if missing or extra:
        parts = []
        if missing:
            parts.append("missing " + ", ".join(repr(v) for v in missing))
        if extra:
            parts.append("unknown " + ", ".join(repr(v) for v in extra))
        raise ValueError(f"{op}: units keys must exactly match columns ({'; '.join(parts)})")
    metadata = _csv_meta(meta, op)
    names = list(columns)
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(names)
    writer.writerow(["# units:"] + [str(units[name]) for name in names])
    ordered_meta = list(_CSV_META_REQUIRED) + sorted(set(metadata) - set(_CSV_META_REQUIRED))
    for key in ordered_meta:
        buf.write(f"# {key}: {metadata[key]}\n")
    n = len(next(iter(columns.values())))
    for row in range(n):
        writer.writerow([_csv_cell(columns[name][row], name, row) for name in names])
    return buf.getvalue()


def _csv_number_column(values: list[str]):
    out = []
    for value in values:
        if value == "":
            out.append(float("nan"))
            continue
        try:
            out.append(float(value))
        except ValueError:
            return np.asarray(values, dtype=str)
    return np.asarray(out, dtype=np.float64)


def table_read_csv(text):
    """ :func:`table_write_csv` の単位つき CSV を読み、列・単位・メタデータの ``table`` を返す。

    返り値は ``{"columns": {列名: 1-D 配列}, "units": {...}, "meta": {...}}``。列名と単位の
    個数、全データ行の列数、必須メタデータを検査し、途中までの表は返さない。数値列は float64
    (空欄は NaN)、数値以外を含む列は文字列配列になる。入力は UTF-8 の ``str`` または ``bytes``。

    呼び出し例: ``roundtrip = table_read_csv(table_write_csv(table, units=units, meta=meta))``。
    """
    op = "table_read_csv"
    if isinstance(text, bytes):
        try:
            text = text.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"{op}: input is not UTF-8") from exc
    if not isinstance(text, str):
        raise ValueError(f"{op}: expected CSV text, got {type(text).__name__}")
    if len(text) > _MAX_CSV_CHARS:
        raise ValueError(f"{op}: input has {len(text)} characters; limit is {_MAX_CSV_CHARS}")
    lines = text.splitlines()
    if len(lines) < 2:
        raise ValueError(f"{op}: expected a column-name line and a '# units:' line")
    try:
        names = next(csv.reader([lines[0]]))
        unit_row = next(csv.reader([lines[1]]))
    except csv.Error as exc:
        raise ValueError(f"{op}: malformed CSV header: {exc}") from exc
    if not names or any(not name or name.startswith("#") for name in names) or len(set(names)) != len(names):
        raise ValueError(f"{op}: column names must be non-empty, unique, and not comments: {names!r}")
    if not unit_row or unit_row[0].strip() != "# units:" or len(unit_row) != len(names) + 1:
        raise ValueError(f"{op}: line 2 must be '# units:' plus {len(names)} units")
    units = dict(zip(names, unit_row[1:]))
    if any(not value.strip() for value in units.values()):
        raise ValueError(f"{op}: every column must have a non-empty unit")
    meta, index = {}, 2
    while index < len(lines) and lines[index].startswith("#"):
        line = lines[index][1:].strip()
        if ":" not in line:
            raise ValueError(f"{op}: metadata line {index + 1} lacks ':': {lines[index]!r}")
        key, value = (part.strip() for part in line.split(":", 1))
        if not key or key in meta:
            raise ValueError(f"{op}: invalid or duplicate metadata key {key!r}")
        meta[key] = value
        index += 1
    metadata = _csv_meta(meta, op)
    columns = {name: [] for name in names}
    try:
        for row_number, row in enumerate(csv.reader(lines[index:]), index + 1):
            if len(row) != len(names):
                raise ValueError(f"{op}: row {row_number} has {len(row)} fields; expected {len(names)}")
            for name, value in zip(names, row):
                columns[name].append(value)
    except csv.Error as exc:
        raise ValueError(f"{op}: malformed CSV data: {exc}") from exc
    return {"columns": {name: _csv_number_column(values) for name, values in columns.items()},
            "units": units, "meta": metadata}
