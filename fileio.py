# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0.
"""Dependency-light, in-memory file-format operators.

Writers in this module return text or bytes and never create a caller-visible
file.  Callers may download the result in Studio, send it over an API, or save it
explicitly.  The optional E57 backend is path-only, so that adapter uses and
removes a private temporary file while still exposing an in-memory contract.
"""
from __future__ import annotations

import csv
import datetime as _datetime
import bz2
import contextlib
import gzip
import hashlib
import io
import lzma
import math
import os
import pathlib
import shutil
import stat
import struct
import subprocess
import tarfile
import tempfile
import threading
import types
import uuid
import zipfile
import zlib
from collections.abc import Mapping

import numpy as np
import mesh as _mesh
import _archive_tarxz

__all__ = [
    "table_write_csv", "table_read_csv",
    "mesh_write_ply", "mesh_read_ply", "mesh_write_stl", "mesh_read_stl",
    "mesh_write_obj", "mesh_read_obj", "mesh_write_off", "mesh_read_off",
    "points_write_xyz", "points_read_xyz",
    "e57_write", "e57_read",
    "archive_probe", "archive_list", "archive_extract", "archive_create",
]

_CSV_META_REQUIRED = ("source", "generated_at", "coordinate_meaning")
_MAX_CSV_CHARS = 256 * 1024 * 1024
_E57_WRITE_LOCK = threading.Lock()
_ARCHIVE_MAX_TOTAL_BYTES = 2 * 1024**3
_ARCHIVE_MAX_MEMBERS = 100_000
_ARCHIVE_MAX_RATIO = 1000


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


# ---------------------------------------------------------------------------
# Meshes and point clouds.  Parsing delegates to mesh.py's validated low-level
# readers; these wrappers add an in-memory public surface and richer PLY fields.
# ---------------------------------------------------------------------------
def _file_bytes(data, op: str, *, ascii_only=False) -> bytes:
    if isinstance(data, str):
        try:
            return data.encode("ascii" if ascii_only else "utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError(f"{op}: text must be ASCII") from exc
    if isinstance(data, (bytes, bytearray, memoryview)):
        raw = bytes(data)
        if ascii_only:
            try:
                raw.decode("ascii")
            except UnicodeDecodeError as exc:
                raise ValueError(f"{op}: input must be ASCII") from exc
        return raw
    raise ValueError(f"{op}: expected text or bytes, got {type(data).__name__}")


def _mesh_arrays(value, op: str):
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValueError(f"{op}: mesh must be a (vertices, faces) pair")
    vertices, faces = _mesh._finish_mesh(value[0], value[1], op)
    if vertices.shape[0] == 0 or faces.shape[0] == 0:
        raise ValueError(f"{op}: mesh must contain vertices and triangular faces")
    tri = vertices[faces]
    area2 = np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    bad = np.flatnonzero(area2 == 0)
    if bad.size:
        raise ValueError(f"{op}: degenerate face at index {int(bad[0])}")
    return vertices, faces


def _face_normals(vertices, faces):
    tri = vertices[faces]
    normals = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    return normals, tri


def _vertex_normals(vertices, faces):
    """Return area-weighted normals sharing the vertex indices used by OBJ."""
    tri = vertices[faces]
    cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    normals = np.zeros_like(vertices)
    for corner in range(3):
        np.add.at(normals, faces[:, corner], cross)
    length = np.linalg.norm(normals, axis=1)
    if np.any(length == 0):
        raise ValueError("mesh_write_obj: vertex normal is undefined")
    return normals / length[:, None]


def _ply_table(value, op: str):
    if not isinstance(value, Mapping) or "vertices" not in value:
        raise ValueError(f"{op}: expected a table containing 'vertices'")
    vertices = _mesh._finite_points(value["vertices"], "vertices", op)
    if vertices.shape[0] == 0:
        raise ValueError(f"{op}: vertices must not be empty")
    faces = np.asarray(value.get("faces", np.zeros((0, 3), np.int64)), dtype=np.int64)
    if faces.size == 0:
        faces = np.zeros((0, 3), np.int64)
    if faces.ndim != 2 or faces.shape[1] != 3:
        raise ValueError(f"{op}: faces must be (M, 3), got {faces.shape!r}")
    if faces.size and (int(faces.min()) < 0 or int(faces.max()) >= len(vertices)):
        raise ValueError(f"{op}: face index out of range for {len(vertices)} vertices")
    fields = []
    normals = value.get("normals")
    if normals is not None:
        normals = _mesh._finite_points(normals, "normals", op)
        if normals.shape != vertices.shape:
            raise ValueError(f"{op}: normals must match vertices, got {normals.shape!r}")
        fields += [("nx", normals[:, 0], "double"), ("ny", normals[:, 1], "double"),
                   ("nz", normals[:, 2], "double")]
    colors = value.get("colors")
    if colors is not None:
        colors = np.asarray(colors)
        if colors.shape != vertices.shape or not np.isfinite(colors).all():
            raise ValueError(f"{op}: colors must be finite (N, 3) matching vertices")
        if colors.dtype.kind in "iu":
            if colors.size and (colors.min() < 0 or colors.max() > 255):
                raise ValueError(f"{op}: integer colors must be in 0..255")
            quantized = colors.astype(np.uint8)
        else:
            if colors.size and (colors.min() < 0.0 or colors.max() > 1.0):
                raise ValueError(f"{op}: floating colors must be in 0..1")
            quantized = np.rint(colors.astype(np.float64) * 255.0).astype(np.uint8)
        fields += [("red", quantized[:, 0], "uchar"), ("green", quantized[:, 1], "uchar"),
                   ("blue", quantized[:, 2], "uchar")]
    attributes = value.get("attributes", {})
    if not isinstance(attributes, Mapping):
        raise ValueError(f"{op}: attributes must be a mapping of scalar arrays")
    reserved = {"x", "y", "z", "nx", "ny", "nz", "red", "green", "blue"}
    for name, values in attributes.items():
        if (not isinstance(name, str) or not name.isidentifier() or not name.isascii()
                or name in reserved):
            raise ValueError(f"{op}: invalid or reserved scalar attribute {name!r}")
        arr = np.asarray(values)
        if arr.ndim != 1 or len(arr) != len(vertices) or arr.dtype.kind not in "iuf" or not np.isfinite(arr).all():
            raise ValueError(f"{op}: attribute {name!r} must be a finite numeric (N,) array")
        fields.append((name, arr.astype(np.float64), "double"))
    return vertices, faces, fields


def mesh_write_ply(table, *, binary):
    """頂点・面・色・法線・任意スカラー属性を ASCII / little-endian PLY に書く(``text`` / ``bytes``)。

    ``table`` は ``vertices`` と任意の ``faces/colors/normals/attributes`` を持つ。``binary=False`` は
    ASCII 文字列、``binary=True`` は binary_little_endian bytes。色は最近傍整数へ丸める。
    呼び出し例: ``mesh_write_ply({"vertices": v, "faces": f}, binary=True)``。
    """
    op = "mesh_write_ply"
    vertices, faces, fields = _ply_table(table, op)
    props = [("x", vertices[:, 0], "double"), ("y", vertices[:, 1], "double"),
             ("z", vertices[:, 2], "double")] + fields
    lines = ["ply", "format %s 1.0" % ("binary_little_endian" if binary else "ascii"),
             "comment written by fullseye.fileio", f"element vertex {len(vertices)}"]
    lines += [f"property {kind} {name}" for name, _values, kind in props]
    lines += [f"element face {len(faces)}", "property list uchar int vertex_indices", "end_header"]
    header = "\n".join(lines) + "\n"
    if not binary:
        body = []
        for i in range(len(vertices)):
            body.append(" ".join(str(int(values[i])) if kind == "uchar" else format(float(values[i]), ".17g")
                                 for _name, values, kind in props))
        body += ["3 %d %d %d" % tuple(face) for face in faces]
        return header + "\n".join(body) + ("\n" if body else "")
    dtype = np.dtype([(name, "u1" if kind == "uchar" else "<f8") for name, _v, kind in props])
    records = np.empty(len(vertices), dtype=dtype)
    for name, values, _kind in props:
        records[name] = values
    face_records = np.empty(len(faces), dtype=np.dtype([("n", "u1"), ("v", "<i4", (3,))]))
    face_records["n"] = 3
    face_records["v"] = faces.astype("<i4")
    return header.encode("ascii") + records.tobytes() + face_records.tobytes()


def mesh_read_ply(data):
    """ASCII / binary PLY を読み、頂点・面・色・法線・スカラー属性の ``table`` を返す。

    未知の頂点スカラーは ``attributes`` に保つ。未知の要素、面の未知プロパティ、未知の list
    property は名前を示して拒否する。呼び出し例: ``table = mesh_read_ply(ply_bytes)``。
    """
    op = "mesh_read_ply"
    raw = _file_bytes(data, op)
    _fmt, elements, _offset = _mesh._ply_header(raw, op)
    unknown_elements = [el["name"] for el in elements if el["name"] not in {"vertex", "face"}]
    if unknown_elements:
        raise ValueError(f"{op}: unknown PLY element {unknown_elements[0]!r}")
    for el in elements:
        for prop in el["props"]:
            if el["name"] == "vertex" and prop["kind"] == "list":
                raise ValueError(f"{op}: unknown vertex list property {prop['name']!r}")
            if el["name"] == "face" and (prop["kind"] != "list" or prop["name"] not in {"vertex_indices", "vertex_index"}):
                raise ValueError(f"{op}: unknown face property {prop['name']!r}")
    parsed = _mesh._ply_data(raw, op)
    if "vertex" not in parsed:
        raise ValueError(f"{op}: PLY has no 'vertex' element")
    vertex = parsed["vertex"]
    vertices = _mesh._ply_xyz(vertex, op)
    scalars = vertex["scalars"]
    result = {"vertices": vertices, "faces": np.zeros((0, 3), np.int64), "attributes": {}}
    normals_present = [name in scalars for name in ("nx", "ny", "nz")]
    if any(normals_present) and not all(normals_present):
        missing = [name for name, present in zip(("nx", "ny", "nz"), normals_present) if not present]
        raise ValueError(f"{op}: incomplete normal properties; missing {', '.join(missing)}")
    if all(normals_present):
        result["normals"] = np.column_stack([scalars["nx"], scalars["ny"], scalars["nz"]])
    colors = _mesh._ply_rgb(vertex)
    if colors is not None:
        result["colors"] = colors
    standard = {"x", "y", "z", "nx", "ny", "nz", "red", "green", "blue",
                "r", "g", "b", "diffuse_red", "diffuse_green", "diffuse_blue"}
    result["attributes"] = {name: np.asarray(values) for name, values in scalars.items() if name not in standard}
    face = parsed.get("face")
    if face is not None and face["count"]:
        lists = face["lists"]
        key = "vertex_indices" if "vertex_indices" in lists else "vertex_index"
        _v, triangulated = _mesh._finish_mesh(vertices, lists[key], op)
        result["faces"] = triangulated
    return result


def mesh_write_stl(mesh, *, binary):
    """三角形 mesh を ASCII または little-endian binary STL に書く(``text`` / ``bytes``)。

    STL は単位を持たない。binary は float32 なので、その精度で往復する。呼び出し例:
    ``mesh_write_stl((vertices, faces), binary=False)``。
    """
    vertices, faces = _mesh_arrays(mesh, "mesh_write_stl")
    normals, triangles = _face_normals(vertices, faces)
    if not binary:
        lines = ["solid fullseye"]
        for normal, tri in zip(normals, triangles):
            lines.append("  facet normal %.17g %.17g %.17g" % tuple(normal))
            lines.append("    outer loop")
            lines += ["      vertex %.17g %.17g %.17g" % tuple(point) for point in tri]
            lines += ["    endloop", "  endfacet"]
        return "\n".join(lines + ["endsolid fullseye", ""])
    rec = np.zeros(len(faces), _mesh._STL_DTYPE)
    rec["normal"], rec["v"] = normals.astype("<f4"), triangles.astype("<f4")
    header = b"Fullseye binary STL".ljust(80, b"\0")
    return header + struct.pack("<I", len(faces)) + rec.tobytes()


def mesh_read_stl(data):
    """ASCII / little-endian binary STL を読み、共有頂点の ``mesh`` `(vertices, faces)` を返す。

    切れたバイナリ、宣言三角形数との不一致、縮退面は拒否する。呼び出し例:
    ``vertices, faces = mesh_read_stl(stl_bytes)``。
    """
    result = _mesh._read_stl(_file_bytes(data, "mesh_read_stl"), "mesh_read_stl")
    return _mesh_arrays(result, "mesh_read_stl")


def mesh_write_obj(mesh):
    """三角形 mesh を ``v`` / ``vn`` / ``f`` を持つ Wavefront OBJ 文字列に書く(``text``)。

    面ごとの法線を ``vn`` として書く。material/texture は書かない。呼び出し例:
    ``text = mesh_write_obj((vertices, faces))``。
    """
    vertices, faces = _mesh_arrays(mesh, "mesh_write_obj")
    normals = _vertex_normals(vertices, faces)
    lines = ["# Wavefront OBJ written by fullseye.fileio", "o mesh"]
    lines += ["v %.17g %.17g %.17g" % tuple(v) for v in vertices]
    lines += ["vn %.17g %.17g %.17g" % tuple(n) for n in normals]
    lines += ["f %d//%d %d//%d %d//%d" %
              (a + 1, a + 1, b + 1, b + 1, c + 1, c + 1)
              for a, b, c in faces]
    return "\n".join(lines) + "\n"


def mesh_read_obj(data):
    """Wavefront OBJ の ``v`` / ``f``(``v//vn`` を含む)を読み、三角形 ``mesh`` を返す。

    ``vn`` は構文として許すが mesh sort は幾何だけなので返さない。``mtllib`` / ``usemtl`` と material は
    読まず、形状に影響させない。呼び出し例: ``mesh = mesh_read_obj(obj_text)``。
    """
    result = _mesh._read_obj(_file_bytes(data, "mesh_read_obj", ascii_only=True), "mesh_read_obj")
    return _mesh_arrays(result, "mesh_read_obj")


def mesh_write_off(mesh):
    """三角形 mesh を Geomview OFF 文字列に書く(``text``)。

    座標は17桁で書き、float64を往復する。呼び出し例: ``text = mesh_write_off((vertices, faces))``。
    """
    vertices, faces = _mesh_arrays(mesh, "mesh_write_off")
    lines = ["OFF", f"{len(vertices)} {len(faces)} 0"]
    lines += ["%.17g %.17g %.17g" % tuple(v) for v in vertices]
    lines += ["3 %d %d %d" % tuple(f) for f in faces]
    return "\n".join(lines) + "\n"


def mesh_read_off(data):
    """Geomview OFF を読み、三角形 ``mesh`` `(vertices, faces)` を返す。

    宣言した頂点・面数とデータ行数、全添字を検査する。呼び出し例: ``mesh = mesh_read_off(off_text)``。
    """
    result = _mesh._read_off(_file_bytes(data, "mesh_read_off", ascii_only=True), "mesh_read_off")
    return _mesh_arrays(result, "mesh_read_off")


def points_write_xyz(points):
    """有限な `(N,3)` 点群を17桁の XYZ テキストに書く(``text``)。

    1行に ``x y z`` を1点ずつ書く。呼び出し例: ``text = points_write_xyz(points)``。
    """
    array = _mesh._finite_points(points, "points", "points_write_xyz")
    if len(array) == 0:
        raise ValueError("points_write_xyz: points must not be empty")
    return "\n".join("%.17g %.17g %.17g" % tuple(row) for row in array) + "\n"


def points_read_xyz(data):
    """空白区切りの XYZ テキストを読み、`(N,3)` の ``points`` を返す。

    色列は受け付けるが points sort では返さない。列数不一致・非有限値は拒否する。呼び出し例:
    ``points = points_read_xyz(xyz_text)``。
    """
    points, _colors = _mesh._read_xyz(_file_bytes(data, "points_read_xyz"), "points_read_xyz")
    points = _mesh._finite_points(points, "points", "points_read_xyz")
    if len(points) == 0:
        raise ValueError("points_read_xyz: input contains no points")
    return points


# ---------------------------------------------------------------------------
# ASTM E57.  pye57/libE57 currently exposes a path-only API; the public
# operators nevertheless consume/return bytes and clean their private temp file.
# ---------------------------------------------------------------------------
def _require_pye57():
    try:
        import pye57
    except ImportError as exc:
        raise ImportError(
            "E57 support requires pye57; install it with `pip install pye57` "
            "or `pip install 'fullseye[e57]'`") from exc
    return pye57


def _e57_scan_table(table, op: str):
    if not isinstance(table, Mapping) or "points" not in table:
        raise ValueError(f"{op}: table must contain 'points'")
    points = _mesh._finite_points(table["points"], "points", op)
    if len(points) == 0:
        raise ValueError(f"{op}: points must not be empty")
    raw = {"cartesianX": points[:, 0], "cartesianY": points[:, 1],
           "cartesianZ": points[:, 2]}
    intensity = table.get("intensity")
    if intensity is not None:
        intensity = np.asarray(intensity, dtype=np.float64)
        if intensity.shape != (len(points),) or not np.isfinite(intensity).all():
            raise ValueError(f"{op}: intensity must be finite and have shape ({len(points)},)")
        raw["intensity"] = intensity
    colors = table.get("colors")
    if colors is not None:
        colors = np.asarray(colors)
        if colors.shape != points.shape or not np.isfinite(colors).all():
            raise ValueError(f"{op}: colors must be finite (N, 3) matching points")
        if colors.dtype.kind in "iu":
            if colors.size and (colors.min() < 0 or colors.max() > 255):
                raise ValueError(f"{op}: integer colors must be in [0, 255]")
            colors8 = colors.astype(np.uint8)
        else:
            colors = colors.astype(np.float64)
            if colors.size and (colors.min() < 0 or colors.max() > 1):
                raise ValueError(f"{op}: floating colors must be in [0, 1]")
            colors8 = np.rint(colors * 255).astype(np.uint8)
        raw.update(colorRed=colors8[:, 0], colorGreen=colors8[:, 1],
                   colorBlue=colors8[:, 2])
    pose = table.get("pose", {})
    if not isinstance(pose, Mapping):
        raise ValueError(f"{op}: pose must be a mapping")
    rotation = np.asarray(pose.get("rotation", [1, 0, 0, 0]), dtype=np.float64)
    translation = np.asarray(pose.get("translation", [0, 0, 0]), dtype=np.float64)
    if rotation.shape != (4,) or not np.isfinite(rotation).all() or np.linalg.norm(rotation) == 0:
        raise ValueError(f"{op}: pose.rotation must be a finite nonzero quaternion [w,x,y,z]")
    if translation.shape != (3,) or not np.isfinite(translation).all():
        raise ValueError(f"{op}: pose.translation must be a finite (3,) vector")
    rotation = rotation / np.linalg.norm(rotation)
    return raw, rotation, translation


def e57_write(table):
    """座標・強度・色・pose を持つ点群 ``table`` を ASTM E57 の ``bytes`` に書く。

    ``pye57`` は optional。未導入なら導入コマンドを含む ``ImportError`` で閉じる。
    呼び出し例: ``payload = e57_write({'points': points, 'pose': pose})``。
    """
    pye57 = _require_pye57()
    raw, rotation, translation = _e57_scan_table(table, "e57_write")
    handle = tempfile.NamedTemporaryFile(suffix=".e57", delete=False)
    path = handle.name
    handle.close()
    e57 = None
    try:
        # pye57 otherwise inserts random root/scan GUIDs.  Derive two UUIDs from
        # the canonical point payload so identical inputs yield identical bytes
        # while distinct scans retain distinct, stable identifiers.
        digest = hashlib.sha256()
        for name in sorted(raw):
            arr = np.ascontiguousarray(raw[name])
            digest.update(name.encode("ascii"))
            digest.update(arr.dtype.str.encode("ascii"))
            digest.update(str(arr.shape).encode("ascii"))
            digest.update(arr.tobytes())
        digest.update(np.ascontiguousarray(rotation).tobytes())
        digest.update(np.ascontiguousarray(translation).tobytes())
        token = digest.hexdigest()
        identifiers = iter((uuid.uuid5(uuid.NAMESPACE_URL, token + ":root"),
                            uuid.uuid5(uuid.NAMESPACE_URL, token + ":scan")))
        backend = __import__(pye57.E57.__module__, fromlist=["E57"])
        with _E57_WRITE_LOCK:
            backend_uuid = backend.uuid
            backend.uuid = types.SimpleNamespace(uuid4=lambda: next(identifiers))
            try:
                e57 = pye57.E57(path, mode="w")
                e57.write_scan_raw(raw, rotation=rotation, translation=translation)
                e57.close()
                e57 = None
            finally:
                backend.uuid = backend_uuid
        with open(path, "rb") as stream:
            return stream.read()
    except Exception as exc:
        raise ValueError(f"e57_write: pye57 failed to encode the scan: {exc}") from exc
    finally:
        if e57 is not None:
            e57.close()
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def e57_read(data):
    """ASTM E57 の ``bytes`` を読み、座標・強度・色・pose の点群 ``table`` を返す。

    この op は 1 scan の E57 を受け付ける。``pye57`` 未導入時は黙って代替せず
    導入コマンドを含む ``ImportError`` を返す。呼び出し例: ``table = e57_read(payload)``。
    """
    pye57 = _require_pye57()
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise ValueError(f"e57_read: expected bytes, got {type(data).__name__}")
    payload = bytes(data)
    if not payload:
        raise ValueError("e57_read: input is empty")
    handle = tempfile.NamedTemporaryFile(suffix=".e57", delete=False)
    path = handle.name
    try:
        handle.write(payload)
    finally:
        handle.close()
    e57 = None
    try:
        e57 = pye57.E57(path, mode="r")
        if e57.scan_count != 1:
            raise ValueError(f"e57_read: expected exactly one scan, found {e57.scan_count}")
        raw = e57.read_scan_raw(0)
        header = e57.get_header(0)
        required = ("cartesianX", "cartesianY", "cartesianZ")
        missing = [name for name in required if name not in raw]
        if missing:
            raise ValueError(f"e57_read: scan is missing {', '.join(missing)}")
        points = np.column_stack([raw[name] for name in required]).astype(np.float64)
        points = _mesh._finite_points(points, "points", "e57_read")
        if len(points) == 0:
            raise ValueError("e57_read: scan contains no points")
        result = {"points": points,
                  "pose": {"rotation": np.asarray(header.rotation, dtype=np.float64),
                           "translation": np.asarray(header.translation, dtype=np.float64)}}
        if "intensity" in raw:
            result["intensity"] = np.asarray(raw["intensity"], dtype=np.float64)
        color_fields = ("colorRed", "colorGreen", "colorBlue")
        if all(name in raw for name in color_fields):
            result["colors"] = np.column_stack([raw[name] for name in color_fields]).astype(np.uint8)
        elif any(name in raw for name in color_fields):
            raise ValueError("e57_read: incomplete RGB color fields")
        return result
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"e57_read: pye57 rejected the input: {exc}") from exc
    finally:
        if e57 is not None:
            e57.close()
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


# ---------------------------------------------------------------------------
# Archives.  The safety model and deterministic tar writer are promoted from
# helpstore.py; the bounded streaming copy comes from sample_data.py.
# 書庫。安全モデルと決定的 tar は helpstore.py、実読込量の門は sample_data.py を基にする。
# ---------------------------------------------------------------------------
_ARCHIVE_FORMATS = {"zip", "tar", "tar.gz", "tar.bz2", "tar.xz", "7z", "rar"}
_WINDOWS_DEVICES = {"CON", "PRN", "AUX", "NUL",
                    *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def _archive_source(data_or_path, op):
    if isinstance(data_or_path, (str, os.PathLike)):
        path = os.path.abspath(os.fspath(data_or_path))
        if not os.path.isfile(path):
            raise ValueError(f"{op}: archive path is not a regular file: {path!r}")
        return path
    if isinstance(data_or_path, (bytes, bytearray, memoryview)):
        raw = bytes(data_or_path)
        if not raw:
            raise ValueError(f"{op}: archive input is empty")
        return raw
    raise ValueError(f"{op}: expected archive bytes or a file path, got {type(data_or_path).__name__}")


@contextlib.contextmanager
def _archive_stream(source):
    if isinstance(source, str):
        with open(source, "rb") as stream:
            yield stream
    else:
        yield io.BytesIO(source)


def _archive_format(source, op):
    with _archive_stream(source) as stream:
        head = stream.read(600)
    if head.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return "zip"
    if head.startswith(b"7z\xbc\xaf\x27\x1c"):
        return "7z"
    if head.startswith((b"Rar!\x1a\x07\x00", b"Rar!\x1a\x07\x01\x00")):
        return "rar"
    compressed = ("tar.gz" if head.startswith(b"\x1f\x8b") else
                  "tar.bz2" if head.startswith(b"BZh") else
                  "tar.xz" if head.startswith(b"\xfd7zXZ\x00") else "tar")
    try:
        with _archive_stream(source) as stream, tarfile.open(fileobj=stream, mode="r:*"):
            return compressed
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise ValueError(f"{op}: unsupported or corrupt archive (magic number was not recognised)") from exc


def archive_probe(data_or_path):
    """書庫のマジックナンバーを検査し、形式名を返す。 / Probe archive magic and return its format name.

    入力は ``bytes`` または既存ファイルの path。返り値は ``zip/tar/tar.gz/tar.bz2/tar.xz/7z/rar``
    のいずれかで、拡張子だけでは判定しない。未知・切断・圧縮tarでないgzip等は明示して拒否する。
    Example: ``fmt = archive_probe(payload)``.
    """
    return _archive_format(_archive_source(data_or_path, "archive_probe"), "archive_probe")


def _sevenzip_executable():
    override = os.environ.get("FULLSEYE_7Z")
    if override is not None:
        if override.strip().lower() in {"", "0", "none", "off", "disabled"}:
            return None
        candidate = os.path.abspath(os.path.expandvars(os.path.expanduser(override)))
        return candidate if os.path.isfile(candidate) else shutil.which(override)
    fixed = r"C:\Program Files\7-Zip\7z.exe"
    return fixed if os.path.isfile(fixed) else shutil.which("7z")


def _require_sevenzip(op):
    executable = _sevenzip_executable()
    if executable is None:
        raise ImportError(f"{op}: 7-Zip is not installed; install 7z.exe or set FULLSEYE_7Z to its path")
    return executable


@contextlib.contextmanager
def _sevenzip_source(source, fmt):
    if isinstance(source, str):
        yield source
        return
    suffix = ".7z" if fmt == "7z" else ".rar"
    handle = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    path = handle.name
    try:
        handle.write(source)
        handle.close()
        yield path
    finally:
        try:
            handle.close()
        except Exception:  # pragma: no cover - already closed on the normal path
            pass
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def _iso_timestamp(value):
    if value is None:
        return None
    if isinstance(value, tuple):
        return "%04d-%02d-%02dT%02d:%02d:%02d" % value[:6]
    try:
        return _datetime.datetime.fromtimestamp(float(value), tz=_datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    except (OverflowError, OSError, ValueError):
        return None


def _sevenzip_list(source, fmt, op):
    exe = _require_sevenzip(op)
    with _sevenzip_source(source, fmt) as path:
        result = subprocess.run([exe, "l", "-slt", "-ba", "-sccUTF-8", path],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding="utf-8", errors="replace", check=False)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise ValueError(f"{op}: 7-Zip rejected the archive: {detail[-1] if detail else 'unknown error'}")
    blocks, current = [], {}
    for line in result.stdout.splitlines() + [""]:
        if not line.strip():
            if current:
                blocks.append(current)
                current = {}
            continue
        key, sep, value = line.partition(" = ")
        if sep:
            current[key.strip()] = value.strip()
    rows = []
    for block in blocks:
        if "Path" not in block:
            continue
        attrs = block.get("Attributes", "")
        size_text, packed_text = block.get("Size", "0"), block.get("Packed Size", "")
        try:
            size = int(size_text or 0)
            packed = int(packed_text) if packed_text else None
        except ValueError as exc:
            raise ValueError(f"{op}: 7-Zip returned non-integer sizes for {block['Path']!r}") from exc
        rows.append({"name": block["Path"].replace("\\", "/"), "size": size,
                     "compressed_size": packed, "modified": block.get("Modified") or None,
                     "is_dir": attrs.startswith("D"), "_link": bool(block.get("Symbolic Link") or block.get("Hard Link")),
                     "_raw": block})
    if not rows:
        raise ValueError(f"{op}: 7-Zip found no archive members")
    return rows


def _standard_list(source, fmt, op):
    rows = []
    if fmt == "zip":
        try:
            with _archive_stream(source) as stream, zipfile.ZipFile(stream) as archive:
                for member in archive.infolist():
                    mode = (member.external_attr >> 16) & 0xFFFF
                    rows.append({"name": member.filename.replace("\\", "/"), "size": member.file_size,
                                 "compressed_size": member.compress_size,
                                 "modified": _iso_timestamp(member.date_time), "is_dir": member.is_dir(),
                                 "_link": stat.S_ISLNK(mode), "_raw": member})
        except (zipfile.BadZipFile, OSError, EOFError) as exc:
            raise ValueError(f"{op}: corrupt ZIP archive: {exc}") from exc
        return rows
    try:
        with _archive_stream(source) as stream, tarfile.open(fileobj=stream, mode="r:*") as archive:
            for member in archive.getmembers():
                rows.append({"name": member.name.replace("\\", "/"), "size": member.size,
                             "compressed_size": member.size if fmt == "tar" else None,
                             "modified": _iso_timestamp(member.mtime), "is_dir": member.isdir(),
                             "_link": member.issym() or member.islnk(), "_raw": member,
                             "_regular": member.isfile() or member.isdir()})
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise ValueError(f"{op}: corrupt TAR archive: {exc}") from exc
    return rows


def _archive_rows(source, fmt, op):
    return _sevenzip_list(source, fmt, op) if fmt in {"7z", "rar"} else _standard_list(source, fmt, op)


def archive_list(data_or_path):
    """書庫を読み、名前・展開後/圧縮後サイズ・更新時刻・directoryフラグの一覧を返す。 / List archive metadata.

    ``bytes`` または path を受け、行は ``name/size/compressed_size/modified/is_dir`` を持つ。
    zip と tar 系は標準ライブラリ、7z/rar は 7-Zip が見つかる場合だけ扱う。7-Zip 不在や
    壊れた書庫では空一覧にせず例外にする。Example: ``rows = archive_list(zip_bytes)``.
    """
    op = "archive_list"
    source = _archive_source(data_or_path, op)
    fmt = _archive_format(source, op)
    rows = _archive_rows(source, fmt, op)
    return [{key: row[key] for key in ("name", "size", "compressed_size", "modified", "is_dir")}
            for row in sorted(rows, key=lambda row: row["name"])]


def _safe_archive_name(name, op):
    if not isinstance(name, str) or not name or "\x00" in name:
        raise ValueError(f"{op}: archive member name must be a non-empty string")
    raw = name.replace("\\", "/")
    if raw.startswith(("/", "//")) or pathlib.PureWindowsPath(raw).drive:
        raise ValueError(f"{op}: unsafe absolute or drive-qualified member path {name!r}")
    parts = [part for part in raw.split("/") if part not in {"", "."}]
    if not parts or ".." in parts:
        raise ValueError(f"{op}: unsafe parent traversal in member path {name!r}")
    for part in parts:
        stem = part.rstrip(" .").split(".", 1)[0].upper()
        if ":" in part or part.endswith((" ", ".")) or stem in _WINDOWS_DEVICES:
            raise ValueError(f"{op}: unsafe Windows member path component {part!r}")
    return "/".join(parts)


def _checked_entries(rows, members, max_total_bytes, max_members, op):
    if isinstance(max_total_bytes, bool) or not isinstance(max_total_bytes, int) or max_total_bytes <= 0:
        raise ValueError(f"{op}: max_total_bytes must be a positive integer")
    if isinstance(max_members, bool) or not isinstance(max_members, int) or max_members <= 0:
        raise ValueError(f"{op}: max_members must be a positive integer")
    by_name, folded = {}, {}
    for row in rows:
        safe = _safe_archive_name(row["name"], op)
        key = safe.casefold()
        if safe in by_name or key in folded:
            raise ValueError(f"{op}: duplicate or case-colliding member path {safe!r}")
        if row.get("_link"):
            raise ValueError(f"{op}: symbolic and hard links are forbidden ({row['name']!r})")
        if row.get("_regular") is False:
            raise ValueError(f"{op}: only regular files and directories are allowed ({row['name']!r})")
        copied = dict(row)
        copied["_safe"] = safe
        by_name[safe] = copied
        folded[key] = safe
    if members is None:
        selected = list(by_name.values())
    else:
        if isinstance(members, (str, bytes)):
            raise ValueError(f"{op}: members must be a sequence of member names or None")
        requested = [_safe_archive_name(name, op) for name in members]
        missing = [name for name in requested if name not in by_name]
        if missing:
            raise ValueError(f"{op}: requested member is absent: {missing[0]!r}")
        selected = [by_name[name] for name in requested]
    if len(selected) > max_members:
        raise ValueError(f"{op}: archive has {len(selected)} selected members; limit is {max_members}")
    total = sum(row["size"] for row in selected if not row["is_dir"])
    if total > max_total_bytes:
        raise ValueError(f"{op}: declared extracted size {total} exceeds {max_total_bytes}-byte limit")
    for row in selected:
        packed = row.get("compressed_size")
        if not row["is_dir"] and packed is not None and row["size"] > _ARCHIVE_MAX_RATIO * packed:
            raise ValueError(f"{op}: member {row['name']!r} exceeds the 1:{_ARCHIVE_MAX_RATIO} compression-ratio limit")
    files = {row["_safe"] for row in selected if not row["is_dir"]}
    for name in files:
        parent = pathlib.PurePosixPath(name).parent
        while str(parent) != ".":
            if str(parent) in files:
                raise ValueError(f"{op}: file member {str(parent)!r} is also a parent directory")
            parent = parent.parent
    return sorted(selected, key=lambda row: (row["_safe"].count("/"), row["_safe"]))


def _ratio_compressor(fmt):
    if fmt == "tar.gz":
        return zlib.compressobj(level=9, wbits=31)
    if fmt == "tar.bz2":
        return bz2.BZ2Compressor(9)
    if fmt == "tar.xz":
        # This compressor only measures whether one expanded member exceeds
        # the 1:1000 gate; preset 0 still rejects highly repetitive bombs while
        # avoiding preset-9-extreme's roughly 700 MiB encoder allocation per
        # member. 展開用の比率検査では圧縮率よりも安全な省メモリ性を優先する。
        return lzma.LZMACompressor(format=lzma.FORMAT_XZ, preset=0)
    return None


def _copy_archive_member(src, target, row, fmt, total, max_total_bytes, op):
    written, packed, compressor = 0, 0, _ratio_compressor(fmt)
    with open(target, "xb") as dst:
        while True:
            chunk = src.read(1 << 20)
            if not chunk:
                break
            written += len(chunk)
            total += len(chunk)
            if written > row["size"] or total > max_total_bytes:
                raise ValueError(f"{op}: extracted data exceeded a declared size or the {max_total_bytes}-byte limit")
            if compressor is not None:
                packed += len(compressor.compress(chunk))
            dst.write(chunk)
    if written != row["size"]:
        raise ValueError(f"{op}: member {row['name']!r} yielded {written} bytes; expected {row['size']}")
    if compressor is not None:
        packed += len(compressor.flush())
        if written > _ARCHIVE_MAX_RATIO * packed:
            raise ValueError(f"{op}: member {row['name']!r} exceeds the 1:{_ARCHIVE_MAX_RATIO} compression-ratio limit")
    return total


def _extract_standard(source, fmt, entries, stage, max_total_bytes, op):
    total = 0
    if fmt == "zip":
        with _archive_stream(source) as stream, zipfile.ZipFile(stream) as archive:
            for row in entries:
                target = os.path.join(stage, *row["_safe"].split("/"))
                if row["is_dir"]:
                    os.makedirs(target, exist_ok=True)
                    continue
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with archive.open(row["_raw"], "r") as src:
                    total = _copy_archive_member(src, target, row, fmt, total, max_total_bytes, op)
        return
    with _archive_stream(source) as stream, tarfile.open(fileobj=stream, mode="r:*") as archive:
        for row in entries:
            target = os.path.join(stage, *row["_safe"].split("/"))
            if row["is_dir"]:
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            src = archive.extractfile(row["_raw"])
            if src is None:
                raise ValueError(f"{op}: cannot read member {row['name']!r}")
            with src:
                total = _copy_archive_member(src, target, row, fmt, total, max_total_bytes, op)


def _extract_sevenzip(source, fmt, entries, stage, max_total_bytes, op):
    exe, total = _require_sevenzip(op), 0
    with _sevenzip_source(source, fmt) as archive_path:
        for row in entries:
            target = os.path.join(stage, *row["_safe"].split("/"))
            if row["is_dir"]:
                os.makedirs(target, exist_ok=True)
                continue
            if row.get("compressed_size") is None:
                raise ValueError(f"{op}: 7-Zip did not report a per-member compressed size for {row['name']!r}")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with tempfile.TemporaryFile() as errors:
                proc = subprocess.Popen([exe, "x", "-so", "-y", "-spd", "-sccUTF-8", archive_path, "--", row["name"]],
                                        stdout=subprocess.PIPE, stderr=errors)
                try:
                    total = _copy_archive_member(proc.stdout, target, row, fmt, total, max_total_bytes, op)
                except Exception:
                    proc.kill()
                    proc.wait()
                    raise
                finally:
                    if proc.stdout is not None:
                        proc.stdout.close()
                code = proc.wait()
                if code:
                    errors.seek(0)
                    detail = errors.read().decode("utf-8", "replace").strip().splitlines()
                    raise ValueError(f"{op}: 7-Zip failed to extract {row['name']!r}: {detail[-1] if detail else 'unknown error'}")


def archive_extract(data_or_path, dest, *, members=None,
                    max_total_bytes=_ARCHIVE_MAX_TOTAL_BYTES, max_members=_ARCHIVE_MAX_MEMBERS):
    """書庫を空の ``dest`` へ安全に展開し、相対path一覧を返す。 / Safely extract into an empty destination.

    zip-slip(絶対path・``..``・drive文字)、link、特殊ファイル、重複名、10万件超、既定2 GiB超、
    1:1000超の圧縮率を拒否する。``dest`` は存在しないか空の実directoryに限り、検証済みの
    一時directoryを最後に置換するため失敗時に半端な出力を残さない。
    Example: ``paths = archive_extract(payload, out_dir, members=["data/a.bin"])``.
    """
    op = "archive_extract"
    source = _archive_source(data_or_path, op)
    fmt = _archive_format(source, op)
    rows = _archive_rows(source, fmt, op)
    entries = _checked_entries(rows, members, max_total_bytes, max_members, op)
    dest_path = pathlib.Path(os.fspath(dest)).absolute()
    if dest_path.is_symlink() or (dest_path.exists() and not dest_path.is_dir()):
        raise ValueError(f"{op}: destination must be a missing or empty real directory: {str(dest_path)!r}")
    if dest_path.exists() and any(dest_path.iterdir()):
        raise ValueError(f"{op}: destination directory is not empty: {str(dest_path)!r}")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    stage = pathlib.Path(tempfile.mkdtemp(prefix=".fullseye-archive-", dir=dest_path.parent))
    try:
        if fmt in {"7z", "rar"}:
            _extract_sevenzip(source, fmt, entries, str(stage), max_total_bytes, op)
        else:
            _extract_standard(source, fmt, entries, str(stage), max_total_bytes, op)
        if dest_path.exists():
            dest_path.rmdir()
        os.replace(stage, dest_path)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return [row["_safe"] for row in entries]


def _archive_items(paths_or_items, root, deterministic, op):
    now = int(_datetime.datetime.now(tz=_datetime.timezone.utc).timestamp())
    if isinstance(paths_or_items, Mapping):
        raw_items = list(paths_or_items.items())
    elif (isinstance(paths_or_items, (list, tuple)) and paths_or_items
          and all(isinstance(item, (list, tuple)) and len(item) == 2 for item in paths_or_items)):
        raw_items = list(paths_or_items)
    else:
        raw_items = None
    entries = []
    if raw_items is not None:
        if not raw_items:
            raise ValueError(f"{op}: paths_or_items must not be empty")
        if root is not None:
            raise ValueError(f"{op}: root is only valid for filesystem paths")
        for name, value in raw_items:
            safe = _safe_archive_name(name, op)
            if not isinstance(value, (bytes, bytearray, memoryview, str)):
                raise ValueError(f"{op}: item {name!r} must contain bytes or UTF-8 text")
            data = value.encode("utf-8") if isinstance(value, str) else bytes(value)
            entries.append({"name": safe, "data": data, "size": len(data), "is_dir": False,
                            "mtime": 0 if deterministic else now})
    else:
        values = [paths_or_items] if isinstance(paths_or_items, (str, os.PathLike)) else list(paths_or_items)
        if not values:
            raise ValueError(f"{op}: paths_or_items must not be empty")
        raw_paths = [pathlib.Path(os.fspath(value)).absolute() for value in values]
        if any(path.is_symlink() for path in raw_paths):
            raise ValueError(f"{op}: symbolic links are forbidden")
        if any(not path.exists() for path in raw_paths):
            missing = next(path for path in raw_paths if not path.exists())
            raise ValueError(f"{op}: input path does not exist: {str(missing)!r}")
        if root is None:
            root_path = pathlib.Path(os.path.commonpath([str(path.parent) for path in raw_paths])).resolve()
        else:
            root_path = pathlib.Path(os.fspath(root)).absolute()
            if root_path.is_symlink() or not root_path.is_dir():
                raise ValueError(f"{op}: root must be an existing real directory")
            root_path = root_path.resolve()
        for raw_path in raw_paths:
            resolved = raw_path.resolve()
            try:
                resolved.relative_to(root_path)
            except ValueError as exc:
                raise ValueError(f"{op}: path {str(raw_path)!r} is outside root {str(root_path)!r}") from exc
            visit = [raw_path]
            while visit:
                path = visit.pop()
                if path.is_symlink():
                    raise ValueError(f"{op}: symbolic links are forbidden: {str(path)!r}")
                safe = _safe_archive_name(path.resolve().relative_to(root_path).as_posix(), op)
                info = path.stat()
                if path.is_dir():
                    entries.append({"name": safe, "size": 0, "is_dir": True,
                                    "mtime": 0 if deterministic else int(info.st_mtime)})
                    visit.extend(sorted(path.iterdir(), key=lambda child: child.name, reverse=True))
                elif path.is_file():
                    entries.append({"name": safe, "path": str(path), "size": info.st_size, "is_dir": False,
                                    "mtime": 0 if deterministic else int(info.st_mtime)})
                else:
                    raise ValueError(f"{op}: only regular files and directories are allowed: {str(path)!r}")
    names = [entry["name"] for entry in entries]
    if len(names) != len(set(names)) or len({name.casefold() for name in names}) != len(names):
        raise ValueError(f"{op}: duplicate or case-colliding archive names")
    total = sum(entry["size"] for entry in entries if not entry["is_dir"])
    if total > _ARCHIVE_MAX_TOTAL_BYTES:
        raise ValueError(f"{op}: input size {total} exceeds {_ARCHIVE_MAX_TOTAL_BYTES}-byte limit")
    return sorted(entries, key=lambda entry: entry["name"])


@contextlib.contextmanager
def _entry_stream(entry):
    if "data" in entry:
        yield io.BytesIO(entry["data"])
    else:
        with open(entry["path"], "rb") as stream:
            yield stream


def _zip_datetime(entry, deterministic):
    if deterministic:
        return (1980, 1, 1, 0, 0, 0)
    dt = _datetime.datetime.fromtimestamp(entry["mtime"])
    year = min(2107, max(1980, dt.year))
    return (year, dt.month, dt.day, dt.hour, dt.minute, dt.second - dt.second % 2)


def _create_zip(entries, level, deterministic):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=level, strict_timestamps=True) as archive:
        for entry in entries:
            name = entry["name"] + ("/" if entry["is_dir"] and not entry["name"].endswith("/") else "")
            info = zipfile.ZipInfo(name, _zip_datetime(entry, deterministic))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = ((0o40755 if entry["is_dir"] else 0o100644) << 16) | (0x10 if entry["is_dir"] else 0)
            if entry["is_dir"]:
                archive.writestr(info, b"")
            else:
                with archive.open(info, "w", force_zip64=True) as dst, _entry_stream(entry) as src:
                    shutil.copyfileobj(src, dst, length=1 << 20)
    return out.getvalue()


def _tar_stream(fmt, out, level, deterministic):
    if fmt == "tar":
        return contextlib.nullcontext(out)
    if fmt == "tar.gz":
        return gzip.GzipFile(filename="", mode="wb", fileobj=out, compresslevel=level,
                             mtime=0 if deterministic else None)
    if fmt == "tar.xz":
        return lzma.LZMAFile(out, "wb", format=lzma.FORMAT_XZ,
                             preset=level | (lzma.PRESET_EXTREME if level == 9 else 0))
    raise ValueError(f"archive_create: creation of {fmt!r} is unsupported")


def _create_tar(entries, fmt, level, deterministic):
    out = io.BytesIO()
    with _tar_stream(fmt, out, level, deterministic) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            for entry in entries:
                info = tarfile.TarInfo(entry["name"] + ("/" if entry["is_dir"] else ""))
                info.size = 0 if entry["is_dir"] else entry["size"]
                info.type = tarfile.DIRTYPE if entry["is_dir"] else tarfile.REGTYPE
                info.mtime = entry["mtime"]
                info.mode = 0o755 if entry["is_dir"] else 0o644
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                if entry["is_dir"]:
                    archive.addfile(info)
                else:
                    with _entry_stream(entry) as src:
                        archive.addfile(info, src)
    return out.getvalue()


def _create_7z(entries, level, deterministic):
    exe = _require_sevenzip("archive_create")
    with tempfile.TemporaryDirectory(prefix="fullseye-7z-input-") as stage, tempfile.TemporaryDirectory(prefix="fullseye-7z-output-") as outdir:
        names = []
        for entry in entries:
            target = os.path.join(stage, *entry["name"].split("/"))
            names.append(entry["name"].replace("/", os.sep))
            if entry["is_dir"]:
                os.makedirs(target, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "xb") as dst, _entry_stream(entry) as src:
                    shutil.copyfileobj(src, dst, length=1 << 20)
            if deterministic:
                os.utime(target, (315532800, 315532800))
        listfile = os.path.join(outdir, "members.txt")
        with open(listfile, "w", encoding="utf-8", newline="\n") as stream:
            stream.write("\n".join(names) + "\n")
        archive_path = os.path.join(outdir, "archive.7z")
        # Non-solid output preserves a measurable compressed size per member;
        # solid archives cannot satisfy the mandatory per-member ratio gate.
        # 非solidなら各memberの圧縮後サイズを測れ、1:1000の門を検査できる。
        command = [exe, "a", "-t7z", f"-mx={level}", "-ms=off", "-mmt=off", "-spd", "-scsUTF-8"]
        if deterministic:
            command += ["-mtc=off", "-mta=off", "-mtm=off"]
        command += [archive_path, "@" + listfile]
        result = subprocess.run(command, cwd=stage, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding="utf-8", errors="replace", check=False)
        if result.returncode:
            detail = (result.stderr or result.stdout).strip().splitlines()
            raise ValueError(f"archive_create: 7-Zip failed: {detail[-1] if detail else 'unknown error'}")
        with open(archive_path, "rb") as stream:
            return stream.read()


def archive_create(paths_or_items, fmt, *, root=None, level=None, deterministic=True):
    """pathまたは名前つき内容から決定的な書庫 ``bytes`` を作る。 / Create deterministic archive bytes.

    ``paths_or_items`` は path(列)または ``{relative_name: bytes_or_text}``。fmt は
    ``zip/tar/tar.gz/tar.xz/7z``、rar作成は非対応として拒否する。同じ入力は名前順・固定時刻・
    固定属性で同じbytesになり、root外path・link・2 GiB超を拒否する。
    Example: ``payload = archive_create({"a.txt": b"A"}, "zip", deterministic=True)``.
    """
    op = "archive_create"
    fmt = str(fmt).lower().replace("tgz", "tar.gz").replace("txz", "tar.xz")
    if fmt == "rar":
        raise ValueError(f"{op}: RAR creation is unsupported because RAR is a proprietary format")
    if fmt not in _ARCHIVE_FORMATS - {"rar", "tar.bz2"}:
        raise ValueError(f"{op}: fmt must be zip, tar, tar.gz, tar.xz, or 7z; got {fmt!r}")
    if not isinstance(deterministic, bool):
        raise ValueError(f"{op}: deterministic must be bool")
    if level is None:
        level = 9
    if isinstance(level, bool) or not isinstance(level, int) or not 0 <= level <= 9:
        raise ValueError(f"{op}: level must be an integer from 0 through 9")
    if fmt == "tar" and level != 9:
        raise ValueError(f"{op}: level has no meaning for uncompressed tar; leave it as None")
    if fmt == "tar.xz":
        return _archive_tarxz.create(paths_or_items, root=root, level=level,
                                     deterministic=deterministic, op=op)
    entries = _archive_items(paths_or_items, root, deterministic, op)
    if fmt == "zip":
        return _create_zip(entries, level, deterministic)
    if fmt == "7z":
        return _create_7z(entries, level, deterministic)
    return _create_tar(entries, fmt, level, deterministic)
