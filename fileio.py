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
import hashlib
import io
import math
import os
import struct
import tempfile
import threading
import types
import uuid
from collections.abc import Mapping

import numpy as np
import mesh as _mesh

__all__ = [
    "table_write_csv", "table_read_csv",
    "mesh_write_ply", "mesh_read_ply", "mesh_write_stl", "mesh_read_stl",
    "mesh_write_obj", "mesh_read_obj", "mesh_write_off", "mesh_read_off",
    "points_write_xyz", "points_read_xyz",
    "e57_write", "e57_read",
    "astro_fits_write", "astro_fits_read",
]

_CSV_META_REQUIRED = ("source", "generated_at", "coordinate_meaning")
_MAX_CSV_CHARS = 256 * 1024 * 1024
_E57_WRITE_LOCK = threading.Lock()
_FITS_BLOCK = 2880
_FITS_WCS_KEYS = (
    "WCSAXES", "RADESYS", "EQUINOX", "LONPOLE", "LATPOLE",
    "CTYPE1", "CTYPE2", "CTYPE3", "CUNIT1", "CUNIT2", "CUNIT3",
    "CRPIX1", "CRPIX2", "CRPIX3", "CRVAL1", "CRVAL2", "CRVAL3",
    "CDELT1", "CDELT2", "CDELT3", "CROTA1", "CROTA2", "CROTA3",
    "PC1_1", "PC1_2", "PC1_3", "PC2_1", "PC2_2", "PC2_3",
    "PC3_1", "PC3_2", "PC3_3", "CD1_1", "CD1_2", "CD1_3",
    "CD2_1", "CD2_2", "CD2_3", "CD3_1", "CD3_2", "CD3_3",
)


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
# Scientific images and volumes.  FITS and MRC are encoded here so the core
# stays dependency-light; optional reference readers are used only by tests.
# ---------------------------------------------------------------------------
def _fits_value(text: str, keyword: str):
    value = text.rstrip()
    if value.startswith("'"):
        chars, index = [], 1
        while index < len(value):
            if value[index] == "'":
                if index + 1 < len(value) and value[index + 1] == "'":
                    chars.append("'")
                    index += 2
                    continue
                return "".join(chars).rstrip()
            chars.append(value[index])
            index += 1
        raise ValueError(f"astro_fits_read: unterminated string in header key {keyword}")
    token = value.split("/", 1)[0].strip()
    if token in ("T", "F"):
        return token == "T"
    if not token:
        raise ValueError(f"astro_fits_read: header key {keyword} has no value")
    try:
        return float(token.replace("D", "E")) if any(c in token for c in ".EDed") else int(token)
    except ValueError as exc:
        raise ValueError(f"astro_fits_read: unsupported value {token!r} for header key {keyword}") from exc


def _fits_card(keyword: str, value) -> bytes:
    if not isinstance(keyword, str) or not keyword or len(keyword) > 8 or not keyword.isascii():
        raise ValueError(f"astro_fits_write: FITS keyword must be 1..8 ASCII characters, got {keyword!r}")
    key = keyword.upper()
    if isinstance(value, (bool, np.bool_)):
        field = ("T" if bool(value) else "F").rjust(20)
    elif isinstance(value, (int, np.integer)):
        field = str(int(value)).rjust(20)
    elif isinstance(value, (float, np.floating)):
        if not math.isfinite(float(value)):
            raise ValueError(f"astro_fits_write: header key {key} must be finite")
        field = ("%.15G" % float(value)).rjust(20)
    elif isinstance(value, str):
        if not value.isascii() or any(c in value for c in "\r\n"):
            raise ValueError(f"astro_fits_write: header key {key} must contain one-line ASCII text")
        field = "'" + value.replace("'", "''") + "'"
    else:
        raise ValueError(f"astro_fits_write: unsupported value type for header key {key}: {type(value).__name__}")
    card = f"{key:<8}= {field}"
    if len(card) > 80:
        raise ValueError(f"astro_fits_write: header value for {key} does not fit one FITS card")
    return card.ljust(80).encode("ascii")


def _fits_storage(image):
    array = np.asarray(image)
    if array.ndim not in (2, 3):
        raise ValueError(f"astro_fits_write: primary image must be 2-D or 3-D, got shape {array.shape!r}")
    if array.size == 0:
        raise ValueError("astro_fits_write: primary image must not be empty")
    dtype = array.dtype
    bzero, bscale = 0, 1
    if dtype == np.dtype("uint8"):
        bitpix, stored = 8, array.astype(">u1", copy=False)
    elif dtype == np.dtype("int16"):
        bitpix, stored = 16, array.astype(">i2", copy=False)
    elif dtype == np.dtype("uint16"):
        bitpix, bzero = 16, 1 << 15
        stored = (array.astype(np.int64) - bzero).astype(">i2")
    elif dtype == np.dtype("int32"):
        bitpix, stored = 32, array.astype(">i4", copy=False)
    elif dtype == np.dtype("uint32"):
        bitpix, bzero = 32, 1 << 31
        stored = (array.astype(np.int64) - bzero).astype(">i4")
    elif dtype == np.dtype("int64"):
        bitpix, stored = 64, array.astype(">i8", copy=False)
    elif dtype == np.dtype("float32"):
        bitpix, stored = -32, array.astype(">f4", copy=False)
    elif dtype == np.dtype("float64"):
        bitpix, stored = -64, array.astype(">f8", copy=False)
    else:
        raise ValueError(f"astro_fits_write: unsupported dtype {dtype}; use uint8/uint16/uint32, int16/int32/int64, float32/float64")
    return array, stored, bitpix, bzero, bscale


def astro_fits_write(image, *, header):
    """2-D/3-D 天文画像と基本 WCS を primary-HDU FITS の ``bytes`` にする。

    ``header`` は FITS の基本 WCS キー(``CTYPE*``, ``CRPIX*``, ``CRVAL*``,
    ``CDELT*``, ``PC*_*``, ``CD*_*``, ``CUNIT*`` など)だけを持つ辞書。構造キーは
    配列から作り、uint16/uint32 は標準の BZERO 規約で保存する。呼び出し例:
    ``payload = astro_fits_write(image, header={"CTYPE1": "RA---TAN"})``。
    """
    array, stored, bitpix, bzero, bscale = _fits_storage(image)
    if not isinstance(header, Mapping):
        raise ValueError("astro_fits_write: header must be a mapping of basic WCS keys")
    raw_header = header.get("wcs", header) if set(header) >= {"wcs"} else header
    if not isinstance(raw_header, Mapping):
        raise ValueError("astro_fits_write: header['wcs'] must be a mapping")
    wcs = {}
    for key, value in raw_header.items():
        upper = str(key).upper()
        if upper not in _FITS_WCS_KEYS:
            raise ValueError(f"astro_fits_write: unsupported header key {key!r}; only basic WCS keys are accepted")
        if upper in wcs:
            raise ValueError(f"astro_fits_write: duplicate WCS key {upper}")
        wcs[upper] = value
    cards = [_fits_card("SIMPLE", True), _fits_card("BITPIX", bitpix),
             _fits_card("NAXIS", array.ndim)]
    cards.extend(_fits_card(f"NAXIS{axis}", size)
                 for axis, size in enumerate(reversed(array.shape), 1))
    if bzero:
        cards.extend((_fits_card("BZERO", bzero), _fits_card("BSCALE", bscale)))
    cards.extend(_fits_card(key, wcs[key]) for key in sorted(wcs))
    cards.append(b"END".ljust(80, b" "))
    header_bytes = b"".join(cards)
    header_bytes += b" " * (-len(header_bytes) % _FITS_BLOCK)
    body = stored.tobytes(order="C")
    body += b"\0" * (-len(body) % _FITS_BLOCK)
    return header_bytes + body


def astro_fits_read(data):
    """primary HDU の 2-D/3-D FITS を ``(image_or_volume, meta)`` として読む。

    ``meta`` は ``bitpix``、``bzero``、``bscale`` と基本 WCS の ``wcs`` 辞書を持つ。
    切れたブロック、random groups、BLANK、次元・BITPIX・データ長の不一致は名指しで拒否する。
    呼び出し例: ``image, meta = astro_fits_read(payload)``。
    """
    op = "astro_fits_read"
    raw = _file_bytes(data, op, ascii_only=False)
    if len(raw) < _FITS_BLOCK or len(raw) % _FITS_BLOCK:
        raise ValueError(f"{op}: FITS length {len(raw)} is not a whole 2880-byte block")
    values, end_offset = {}, None
    for offset in range(0, len(raw), 80):
        card = raw[offset:offset + 80]
        try:
            text = card.decode("ascii")
        except UnicodeDecodeError as exc:
            raise ValueError(f"{op}: non-ASCII header card at byte {offset}") from exc
        keyword = text[:8].strip()
        if keyword == "END":
            end_offset = offset + 80
            break
        if not keyword:
            continue
        if text[8:10] != "= ":
            if keyword in ("COMMENT", "HISTORY"):
                continue
            raise ValueError(f"{op}: unsupported non-value header card {keyword}")
        if keyword in values:
            raise ValueError(f"{op}: duplicate header key {keyword}")
        values[keyword] = _fits_value(text[10:], keyword)
    if end_offset is None:
        raise ValueError(f"{op}: primary header has no END card")
    if values.get("SIMPLE") is not True:
        raise ValueError(f"{op}: SIMPLE must be T in a primary FITS HDU")
    bitpix = values.get("BITPIX")
    dtype_by_bitpix = {8: np.dtype(">u1"), 16: np.dtype(">i2"), 32: np.dtype(">i4"),
                       64: np.dtype(">i8"), -32: np.dtype(">f4"), -64: np.dtype(">f8")}
    if bitpix not in dtype_by_bitpix:
        raise ValueError(f"{op}: unsupported BITPIX {bitpix!r}; expected 8/16/32/64/-32/-64")
    naxis = values.get("NAXIS")
    if naxis not in (2, 3):
        raise ValueError(f"{op}: primary image NAXIS must be 2 or 3, got {naxis!r}")
    if values.get("GROUPS", False) or values.get("PCOUNT", 0) != 0 or values.get("GCOUNT", 1) != 1:
        raise ValueError(f"{op}: random-groups FITS is unsupported")
    if "BLANK" in values:
        raise ValueError(f"{op}: integer BLANK pixels are unsupported; convert them to a float image with NaN")
    dims = []
    for axis in range(1, naxis + 1):
        size = values.get(f"NAXIS{axis}")
        if not isinstance(size, int) or size <= 0:
            raise ValueError(f"{op}: NAXIS{axis} must be a positive integer, got {size!r}")
        dims.append(size)
    header_size = (end_offset + _FITS_BLOCK - 1) // _FITS_BLOCK * _FITS_BLOCK
    count = math.prod(dims)
    byte_count = count * dtype_by_bitpix[bitpix].itemsize
    padded_end = header_size + ((byte_count + _FITS_BLOCK - 1) // _FITS_BLOCK * _FITS_BLOCK)
    if len(raw) < padded_end:
        raise ValueError(f"{op}: primary data declares {byte_count} bytes but input is truncated by {padded_end - len(raw)} bytes")
    if len(raw) != padded_end:
        raise ValueError(f"{op}: trailing HDU or {len(raw) - padded_end} unexplained bytes are unsupported")
    array = np.frombuffer(raw, dtype=dtype_by_bitpix[bitpix], count=count,
                          offset=header_size).reshape(tuple(reversed(dims))).copy()
    if array.dtype.itemsize > 1:
        array = array.astype(array.dtype.newbyteorder("="), copy=False)
    bzero, bscale = values.get("BZERO", 0), values.get("BSCALE", 1)
    if not isinstance(bzero, (int, float)) or not isinstance(bscale, (int, float)) or bscale == 0:
        raise ValueError(f"{op}: BZERO/BSCALE must be finite numeric values and BSCALE must be nonzero")
    if not math.isfinite(float(bzero)) or not math.isfinite(float(bscale)):
        raise ValueError(f"{op}: BZERO/BSCALE must be finite")
    if bitpix == 16 and bzero == 1 << 15 and bscale == 1:
        array = (array.astype(np.int32) + (1 << 15)).astype(np.uint16)
    elif bitpix == 32 and bzero == 1 << 31 and bscale == 1:
        array = (array.astype(np.int64) + (1 << 31)).astype(np.uint32)
    elif bzero != 0 or bscale != 1:
        array = array.astype(np.float64) * float(bscale) + float(bzero)
    wcs = {key: values[key] for key in _FITS_WCS_KEYS if key in values}
    return array, {"format": "FITS", "bitpix": int(bitpix), "bzero": bzero,
                   "bscale": bscale, "wcs": wcs}
