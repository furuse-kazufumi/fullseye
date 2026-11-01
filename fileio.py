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
import gzip
import hashlib
import io
import math
import os
import re
import struct
import tempfile
import threading
import types
import uuid
import xml.etree.ElementTree as _ET
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
    "em_mrc_write", "em_mrc_read",
    "nrrd_write", "nrrd_read",
    "nifti_write", "nifti_read",
    "ome_tiff_write", "ome_tiff_read",
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
_MRC_MODE_DTYPES = {0: np.dtype("i1"), 1: np.dtype("i2"),
                    2: np.dtype("f4"), 6: np.dtype("u2")}
_NRRD_DTYPES = {
    "int8": np.dtype("i1"), "uint8": np.dtype("u1"),
    "int16": np.dtype("i2"), "uint16": np.dtype("u2"),
    "int32": np.dtype("i4"), "uint32": np.dtype("u4"),
    "int64": np.dtype("i8"), "uint64": np.dtype("u8"),
    "float": np.dtype("f4"), "double": np.dtype("f8"),
}
_NRRD_TYPE_ALIASES = {
    "signed char": "int8", "int8_t": "int8", "uchar": "uint8",
    "unsigned char": "uint8", "uint8_t": "uint8", "short": "int16",
    "short int": "int16", "signed short": "int16", "signed short int": "int16",
    "int16_t": "int16", "ushort": "uint16", "unsigned short": "uint16",
    "unsigned short int": "uint16", "uint16_t": "uint16", "int": "int32",
    "signed int": "int32", "int32_t": "int32", "uint": "uint32",
    "unsigned int": "uint32", "uint32_t": "uint32", "longlong": "int64",
    "long long": "int64", "long long int": "int64", "int64_t": "int64",
    "ulonglong": "uint64", "unsigned long long": "uint64",
    "unsigned long long int": "uint64", "uint64_t": "uint64",
}
_NIFTI_DTYPES = {
    2: np.dtype("u1"), 4: np.dtype("i2"), 8: np.dtype("i4"),
    16: np.dtype("f4"), 64: np.dtype("f8"), 256: np.dtype("i1"),
    512: np.dtype("u2"), 768: np.dtype("u4"), 1024: np.dtype("i8"),
    1280: np.dtype("u8"),
}
_NIFTI_SPATIAL_UNITS = {1: "m", 2: "mm", 3: "um"}
_NIFTI_TIME_UNITS = {8: "s", 16: "ms", 24: "us"}
_NIFTI_EXTENSIONS = (".nii", ".nii.gz")
_OME_AXIS_ORDER = "TCZYX"
_OME_EXTENSIONS = (".ome.tif", ".ome.tiff")


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


def _mrc_vector(meta, key: str, unit_key: str, op: str, *, positive=False):
    if key not in meta or unit_key not in meta:
        raise ValueError(f"{op}: meta must contain {key!r} and explicit {unit_key!r}='angstrom'")
    unit = str(meta[unit_key]).strip().lower()
    if unit not in ("angstrom", "ångström", "å"):
        raise ValueError(f"{op}: {unit_key} must be 'angstrom' (MRC2014 length unit), got {meta[unit_key]!r}")
    values = np.asarray(meta[key], dtype=np.float64)
    if values.shape != (3,) or not np.all(np.isfinite(values)):
        raise ValueError(f"{op}: meta[{key!r}] must be three finite x/y/z values in angstrom")
    if positive and np.any(values <= 0):
        raise ValueError(f"{op}: meta[{key!r}] voxel sizes must all be positive")
    return values


def em_mrc_write(volume, *, meta):
    """2-D/3-D 電顕データを MRC2014/CCP4 の ``bytes`` にする。

    mode 0/1/2/6(``int8/int16/float32/uint16``)を扱う。``meta`` は
    ``voxel_size`` / ``origin`` の x,y,z と、それぞれの単位キー
    ``voxel_unit='angstrom'`` / ``origin_unit='angstrom'`` を必須とする。
    呼び出し例: ``em_mrc_write(vol, meta={"voxel_size": [1,1,2],
    "voxel_unit": "angstrom", "origin": [0,0,0], "origin_unit": "angstrom"})``。
    """
    op = "em_mrc_write"
    array = np.asarray(volume)
    if array.ndim not in (2, 3) or array.size == 0:
        raise ValueError(f"{op}: data must be a non-empty 2-D image or 3-D volume, got {array.shape!r}")
    if array.ndim == 3 and array.shape[0] == 1:
        raise ValueError(f"{op}: a depth-1 3-D array is ambiguous in MRC; pass its 2-D slice explicitly")
    mode_by_dtype = {dtype: mode for mode, dtype in _MRC_MODE_DTYPES.items()}
    native_dtype = array.dtype.newbyteorder("=")
    if native_dtype not in mode_by_dtype:
        raise ValueError(f"{op}: unsupported dtype {array.dtype}; mode 0/1/2/6 require int8/int16/float32/uint16")
    if not isinstance(meta, Mapping):
        raise ValueError(f"{op}: meta must be a mapping")
    unknown = set(meta) - {"voxel_size", "voxel_unit", "origin", "origin_unit"}
    if unknown:
        raise ValueError(f"{op}: unsupported metadata key(s): {', '.join(sorted(map(str, unknown)))}")
    voxel = _mrc_vector(meta, "voxel_size", "voxel_unit", op, positive=True)
    origin = _mrc_vector(meta, "origin", "origin_unit", op)
    mode = mode_by_dtype[native_dtype]
    nz, ny, nx = ((1,) + array.shape) if array.ndim == 2 else array.shape
    mx, my, mz = nx, ny, nz
    header = bytearray(1024)
    struct.pack_into("<10i", header, 0, nx, ny, nz, mode, 0, 0, 0, mx, my, mz)
    struct.pack_into("<6f", header, 40, *(voxel * [mx, my, mz]), 90.0, 90.0, 90.0)
    struct.pack_into("<3i", header, 64, 1, 2, 3)
    finite = array[np.isfinite(array)] if np.issubdtype(array.dtype, np.floating) else array.reshape(-1)
    if finite.size:
        dmin, dmax, dmean = float(finite.min()), float(finite.max()), float(finite.mean())
        rms = float(np.sqrt(np.mean((finite.astype(np.float64) - dmean) ** 2)))
    else:
        dmin = dmax = dmean = rms = float("nan")
    struct.pack_into("<3f", header, 76, dmin, dmax, dmean)
    struct.pack_into("<2i", header, 88, 0, 0)
    struct.pack_into("<3f", header, 196, *origin)
    header[208:212] = b"MAP "
    header[212:216] = bytes((0x44, 0x41, 0, 0))
    struct.pack_into("<f", header, 216, rms)
    struct.pack_into("<i", header, 220, 1)
    label = b"Fullseye in-memory MRC2014 writer"
    header[224:224 + len(label)] = label
    stored = np.asarray(array, dtype=native_dtype.newbyteorder("<"))
    return bytes(header) + stored.tobytes(order="C")


def em_mrc_read(data):
    """MRC2014/CCP4 の mode 0/1/2/6 を ``(image_or_volume, meta)`` として読む。

    ``meta`` は Å 単位を明示した ``voxel_size`` / ``origin`` を返す。非標準軸順、
    extended header、切れたデータ、shape と mode の不一致は名指しで拒否する。
    呼び出し例: ``volume, meta = em_mrc_read(payload)``。
    """
    op = "em_mrc_read"
    raw = _file_bytes(data, op)
    if len(raw) < 1024:
        raise ValueError(f"{op}: MRC header is truncated ({len(raw)} bytes; need 1024)")
    if raw[208:212] != b"MAP ":
        raise ValueError(f"{op}: header MAP signature is missing")
    stamp = raw[212:216]
    if stamp[:2] in (b"DA", b"DD"):
        endian = "<"
    elif stamp[:2] == b"\x11\x11":
        endian = ">"
    else:
        raise ValueError(f"{op}: unsupported machine stamp {stamp.hex()}")
    nx, ny, nz, mode = struct.unpack_from(endian + "4i", raw, 0)
    if any(v <= 0 for v in (nx, ny, nz)):
        raise ValueError(f"{op}: nx/ny/nz must be positive, got {(nx, ny, nz)!r}")
    if mode not in _MRC_MODE_DTYPES:
        raise ValueError(f"{op}: unsupported MRC mode {mode}; expected 0/1/2/6")
    mx, my, mz = struct.unpack_from(endian + "3i", raw, 28)
    if any(v <= 0 for v in (mx, my, mz)):
        raise ValueError(f"{op}: mx/my/mz sampling counts must be positive, got {(mx, my, mz)!r}")
    mapc, mapr, maps = struct.unpack_from(endian + "3i", raw, 64)
    if (mapc, mapr, maps) != (1, 2, 3):
        raise ValueError(f"{op}: unsupported axis mapping MAPC/MAPR/MAPS={(mapc, mapr, maps)!r}; expected (1, 2, 3)")
    nsymbt = struct.unpack_from(endian + "i", raw, 92)[0]
    if nsymbt != 0:
        raise ValueError(f"{op}: extended header NSYMBT={nsymbt} is unsupported")
    dtype = _MRC_MODE_DTYPES[mode].newbyteorder(endian)
    count = nx * ny * nz
    expected = 1024 + count * dtype.itemsize
    if len(raw) != expected:
        relation = "truncated" if len(raw) < expected else "has trailing bytes"
        raise ValueError(f"{op}: mode {mode} data declares {count} voxels ({expected} total bytes) but input {relation}: {len(raw)} bytes")
    array = np.frombuffer(raw, dtype=dtype, count=count, offset=1024).reshape((nz, ny, nx)).copy()
    if array.dtype.itemsize > 1:
        array = array.astype(array.dtype.newbyteorder("="), copy=False)
    cella = np.asarray(struct.unpack_from(endian + "3f", raw, 40), dtype=np.float64)
    voxel = cella / np.asarray([mx, my, mz], dtype=np.float64)
    if not np.all(np.isfinite(voxel)) or np.any(voxel <= 0):
        raise ValueError(f"{op}: cell dimensions imply invalid voxel size {voxel.tolist()!r} angstrom")
    origin = np.asarray(struct.unpack_from(endian + "3f", raw, 196), dtype=np.float64)
    if not np.all(np.isfinite(origin)):
        raise ValueError(f"{op}: origin contains NaN/Inf")
    result = array[0] if nz == 1 else array
    return result, {"format": "MRC2014", "mode": int(mode),
                    "voxel_size": voxel, "voxel_unit": "angstrom",
                    "origin": origin, "origin_unit": "angstrom"}


def _nrrd_unit(value, op: str):
    aliases = {"mm": "mm", "millimeter": "mm", "millimeters": "mm",
               "um": "um", "µm": "um", "micrometer": "um", "micrometers": "um",
               "angstrom": "angstrom", "ångström": "angstrom", "å": "angstrom"}
    unit = aliases.get(str(value).strip().lower())
    if unit is None:
        raise ValueError(f"{op}: space_unit must be one of mm/um/angstrom, got {value!r}")
    return unit


def _nrrd_geometry(meta, ndim: int, op: str):
    if not isinstance(meta, Mapping):
        raise ValueError(f"{op}: meta must be a mapping")
    allowed = {"space_directions", "space_unit", "space_origin", "kinds"}
    unknown = set(meta) - allowed
    if unknown:
        raise ValueError(f"{op}: unsupported metadata key(s): {', '.join(sorted(map(str, unknown)))}")
    if "space_directions" not in meta or "space_unit" not in meta:
        raise ValueError(f"{op}: meta requires space_directions and explicit space_unit")
    raw_directions = list(meta["space_directions"])
    if len(raw_directions) != ndim:
        raise ValueError(f"{op}: space_directions has {len(raw_directions)} axes; array has {ndim}")
    vectors, space_dim = [], None
    for axis, value in enumerate(raw_directions):
        if value is None:
            vectors.append(None)
            continue
        vector = np.asarray(value, dtype=np.float64)
        if vector.ndim != 1 or vector.size == 0 or not np.all(np.isfinite(vector)):
            raise ValueError(f"{op}: space_directions axis {axis} must be a finite vector or None")
        if not np.any(vector):
            raise ValueError(f"{op}: space_directions axis {axis} must not be a zero vector")
        if space_dim is None:
            space_dim = len(vector)
        elif len(vector) != space_dim:
            raise ValueError(f"{op}: all space direction vectors must have the same length")
        vectors.append(vector)
    if space_dim is None:
        raise ValueError(f"{op}: space_directions must contain at least one spatial vector")
    unit = _nrrd_unit(meta["space_unit"], op)
    origin = np.asarray(meta.get("space_origin", np.zeros(space_dim)), dtype=np.float64)
    if origin.shape != (space_dim,) or not np.all(np.isfinite(origin)):
        raise ValueError(f"{op}: space_origin must be {space_dim} finite values")
    kinds = list(meta.get("kinds", ["domain" if value is not None else "list" for value in vectors]))
    if len(kinds) != ndim or any(not isinstance(v, str) or not v or any(c.isspace() for c in v) for v in kinds):
        raise ValueError(f"{op}: kinds must contain one whitespace-free name per array axis")
    return vectors, unit, origin, kinds


def _nrrd_vector_text(vector) -> str:
    if vector is None:
        return "none"
    return "(" + ",".join("%.17g" % float(value) for value in vector) + ")"


def nrrd_write(array, *, meta, encoding):
    """多次元配列と ``space directions`` を raw/gzip NRRD の ``bytes`` にする。

    ``meta`` は各配列軸の方向ベクトル(非空間軸は ``None``)、``space_origin``、
    ``space_unit``(``mm`` / ``um`` / ``angstrom``)を持つ。``encoding`` は ``raw`` または
    ``gzip`` を明示する。呼び出し例: ``nrrd_write(vol, meta=geometry, encoding="gzip")``。
    """
    op = "nrrd_write"
    values = np.asarray(array)
    if values.ndim < 1 or values.size == 0:
        raise ValueError(f"{op}: array must be non-empty and at least 1-D, got {values.shape!r}")
    native_dtype = values.dtype.newbyteorder("=")
    type_by_dtype = {dtype: name for name, dtype in _NRRD_DTYPES.items()}
    if native_dtype not in type_by_dtype:
        raise ValueError(f"{op}: unsupported dtype {values.dtype}; use fixed-width integers or float32/float64")
    encoding = str(encoding).lower()
    if encoding not in ("raw", "gzip"):
        raise ValueError(f"{op}: encoding must be 'raw' or 'gzip', got {encoding!r}")
    vectors, unit, origin, kinds = _nrrd_geometry(meta, values.ndim, op)
    space_dim = len(origin)
    header = ["NRRD0005", "# Created by Fullseye", f"type: {type_by_dtype[native_dtype]}",
              f"dimension: {values.ndim}", "sizes: " + " ".join(map(str, values.shape)),
              f"space dimension: {space_dim}",
              "space directions: " + " ".join(_nrrd_vector_text(v) for v in vectors),
              "kinds: " + " ".join(kinds),
              "space units: " + " ".join(f'"{unit}"' for _ in range(space_dim)),
              "space origin: " + _nrrd_vector_text(origin),
              f"encoding: {encoding}"]
    if native_dtype.itemsize > 1:
        header.append("endian: little")
    stored = np.asarray(values, dtype=native_dtype.newbyteorder("<")).tobytes(order="F")
    if encoding == "gzip":
        stored = gzip.compress(stored, compresslevel=9, mtime=0)
    return ("\n".join(header) + "\n\n").encode("ascii") + stored


def _nrrd_fields(raw: bytes, op: str):
    marker = raw.find(b"\n\n")
    marker_size = 2
    if marker < 0:
        marker = raw.find(b"\r\n\r\n")
        marker_size = 4
    if marker < 0:
        raise ValueError(f"{op}: NRRD header has no blank-line terminator")
    try:
        text = raw[:marker].decode("ascii").replace("\r\n", "\n")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{op}: NRRD header must be ASCII") from exc
    lines = text.splitlines()
    if not lines or not lines[0].startswith("NRRD000") or lines[0][-1:] not in "12345":
        raise ValueError(f"{op}: unsupported or missing NRRD magic/version")
    fields = {}
    for number, line in enumerate(lines[1:], 2):
        if not line or line.startswith("#"):
            continue
        if ":=" in line:
            raise ValueError(f"{op}: custom key/value field on header line {number} is unsupported")
        if ":" not in line:
            raise ValueError(f"{op}: malformed header line {number}: {line!r}")
        key, value = (part.strip() for part in line.split(":", 1))
        key = key.lower()
        if key in fields:
            raise ValueError(f"{op}: duplicate header field {key!r}")
        fields[key] = value
    return fields, raw[marker + marker_size:]


def _nrrd_directions(text: str, dimension: int, op: str):
    tokens = []
    current, depth = [], 0
    for char in text.strip():
        if char == "(" :
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                raise ValueError(f"{op}: malformed space directions")
        if char.isspace() and depth == 0:
            if current:
                tokens.append("".join(current)); current = []
        else:
            current.append(char)
    if current:
        tokens.append("".join(current))
    if depth != 0 or len(tokens) != dimension:
        raise ValueError(f"{op}: space directions must have {dimension} axis entries")
    vectors, size = [], None
    for axis, token in enumerate(tokens):
        if token.lower() == "none":
            vectors.append(None)
            continue
        if not (token.startswith("(") and token.endswith(")")):
            raise ValueError(f"{op}: malformed space direction for axis {axis}: {token!r}")
        try:
            vector = np.asarray([float(v) for v in token[1:-1].split(",")], dtype=np.float64)
        except ValueError as exc:
            raise ValueError(f"{op}: non-numeric space direction for axis {axis}") from exc
        if vector.size == 0 or not np.all(np.isfinite(vector)) or not np.any(vector):
            raise ValueError(f"{op}: invalid space direction for axis {axis}")
        if size is None:
            size = len(vector)
        elif len(vector) != size:
            raise ValueError(f"{op}: space direction vector lengths disagree")
        vectors.append(vector)
    return vectors, size


def nrrd_read(data):
    """raw/gzip NRRD を ``(array, meta)`` として読み、空間単位を明示して返す。

    ``meta`` は ``space_directions``、方向ベクトルの長さから得た ``voxel_spacing``、
    ``space_unit``、``space_origin``、``kinds`` を持つ。detached data、未知の encoding、
    shape/dtype/byte 数の不一致は拒否する。呼び出し例: ``array, meta = nrrd_read(payload)``。
    """
    op = "nrrd_read"
    raw = _file_bytes(data, op)
    fields, payload = _nrrd_fields(raw, op)
    required = ("type", "dimension", "sizes", "encoding")
    missing = [key for key in required if key not in fields]
    if missing:
        raise ValueError(f"{op}: missing required header field(s): {', '.join(missing)}")
    if any(key in fields for key in ("data file", "datafile", "line skip", "byte skip")):
        raise ValueError(f"{op}: detached data and line/byte skip headers are unsupported")
    type_name = fields["type"].lower()
    type_name = _NRRD_TYPE_ALIASES.get(type_name, type_name)
    if type_name not in _NRRD_DTYPES:
        raise ValueError(f"{op}: unsupported NRRD type {fields['type']!r}")
    try:
        dimension = int(fields["dimension"])
        sizes = tuple(int(v) for v in fields["sizes"].split())
    except ValueError as exc:
        raise ValueError(f"{op}: dimension and sizes must be integers") from exc
    if dimension < 1 or len(sizes) != dimension or any(v <= 0 for v in sizes):
        raise ValueError(f"{op}: dimension {dimension} and sizes {sizes!r} are inconsistent")
    encoding = fields["encoding"].lower()
    if encoding in ("gz", "gzip"):
        try:
            payload = gzip.decompress(payload)
        except (OSError, EOFError) as exc:
            raise ValueError(f"{op}: corrupt or truncated gzip payload: {exc}") from exc
    elif encoding != "raw":
        raise ValueError(f"{op}: unsupported encoding {encoding!r}; expected raw/gzip")
    dtype = _NRRD_DTYPES[type_name]
    if dtype.itemsize > 1:
        endian = fields.get("endian", "").lower()
        if endian not in ("little", "big"):
            raise ValueError(f"{op}: multi-byte type requires endian: little or big")
        dtype = dtype.newbyteorder("<" if endian == "little" else ">")
    expected = math.prod(sizes) * dtype.itemsize
    if len(payload) != expected:
        raise ValueError(f"{op}: sizes/type declare {expected} data bytes, got {len(payload)}")
    array = np.frombuffer(payload, dtype=dtype).reshape(sizes, order="F").copy()
    if array.dtype.itemsize > 1:
        array = array.astype(array.dtype.newbyteorder("="), copy=False)
    vectors, space_dim = (None, None)
    if "space directions" in fields:
        vectors, space_dim = _nrrd_directions(fields["space directions"], dimension, op)
        declared = fields.get("space dimension")
        if declared is not None and int(declared) != space_dim:
            raise ValueError(f"{op}: space dimension {declared} disagrees with direction vectors of length {space_dim}")
    unit = None
    if "space units" in fields:
        units = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', fields["space units"])
        if space_dim is None or len(units) != space_dim:
            raise ValueError(f"{op}: space units count must match space dimension")
        canonical = [_nrrd_unit(value, op) for value in units]
        if len(set(canonical)) != 1:
            raise ValueError(f"{op}: mixed spatial units are unsupported; convert them before reading")
        unit = canonical[0]
    if vectors is not None and unit is None:
        raise ValueError(f"{op}: space directions require explicit space units")
    origin = None
    if "space origin" in fields:
        token = fields["space origin"]
        if not (token.startswith("(") and token.endswith(")")):
            raise ValueError(f"{op}: malformed space origin")
        try:
            origin = np.asarray([float(v) for v in token[1:-1].split(",")], dtype=np.float64)
        except ValueError as exc:
            raise ValueError(f"{op}: non-numeric space origin") from exc
        if space_dim is None or origin.shape != (space_dim,) or not np.all(np.isfinite(origin)):
            raise ValueError(f"{op}: space origin length must match space dimension")
    kinds = fields.get("kinds", "").split() or None
    if kinds is not None and len(kinds) != dimension:
        raise ValueError(f"{op}: kinds count must match dimension")
    spacing = None if vectors is None else [None if v is None else float(np.linalg.norm(v)) for v in vectors]
    return array, {"format": "NRRD", "encoding": encoding, "space_directions": vectors,
                   "voxel_spacing": spacing, "space_unit": unit,
                   "space_origin": origin, "kinds": kinds}


def _nifti_units(spatial, temporal, op: str):
    spatial_aliases = {"m": 1, "meter": 1, "mm": 2, "millimeter": 2,
                       "um": 3, "µm": 3, "micrometer": 3}
    time_aliases = {None: 0, "": 0, "s": 8, "sec": 8, "second": 8,
                    "ms": 16, "msec": 16, "millisecond": 16,
                    "us": 24, "usec": 24, "microsecond": 24}
    s_code = spatial_aliases.get(str(spatial).strip().lower())
    t_key = None if temporal is None else str(temporal).strip().lower()
    t_code = time_aliases.get(t_key)
    if s_code is None:
        raise ValueError(f"{op}: spatial_unit must be m/mm/um, got {spatial!r}")
    if t_code is None:
        raise ValueError(f"{op}: time_unit must be s/ms/us, got {temporal!r}")
    return s_code, t_code


def _rotation_quaternion(matrix, op: str):
    rotation = np.asarray(matrix, dtype=np.float64)
    if not np.allclose(rotation.T @ rotation, np.eye(3), rtol=0, atol=1e-5) or not np.isclose(np.linalg.det(rotation), 1.0, atol=1e-5):
        raise ValueError(f"{op}: affine contains shear or a non-orthogonal rotation; NIfTI qform cannot represent it")
    trace = float(np.trace(rotation))
    if trace > 0:
        s = math.sqrt(trace + 1.0) * 2
        a, b, c, d = 0.25 * s, (rotation[2, 1] - rotation[1, 2]) / s, (rotation[0, 2] - rotation[2, 0]) / s, (rotation[1, 0] - rotation[0, 1]) / s
    else:
        axis = int(np.argmax(np.diag(rotation)))
        if axis == 0:
            s = math.sqrt(1.0 + rotation[0, 0] - rotation[1, 1] - rotation[2, 2]) * 2
            a, b, c, d = (rotation[2, 1] - rotation[1, 2]) / s, 0.25 * s, (rotation[0, 1] + rotation[1, 0]) / s, (rotation[0, 2] + rotation[2, 0]) / s
        elif axis == 1:
            s = math.sqrt(1.0 + rotation[1, 1] - rotation[0, 0] - rotation[2, 2]) * 2
            a, b, c, d = (rotation[0, 2] - rotation[2, 0]) / s, (rotation[0, 1] + rotation[1, 0]) / s, 0.25 * s, (rotation[1, 2] + rotation[2, 1]) / s
        else:
            s = math.sqrt(1.0 + rotation[2, 2] - rotation[0, 0] - rotation[1, 1]) * 2
            a, b, c, d = (rotation[1, 0] - rotation[0, 1]) / s, (rotation[0, 2] + rotation[2, 0]) / s, (rotation[1, 2] + rotation[2, 1]) / s, 0.25 * s
    quat = np.asarray([a, b, c, d], dtype=np.float64)
    quat /= np.linalg.norm(quat)
    if quat[0] < 0:
        quat *= -1
    return quat


def _nifti_affine_parts(meta, ndim: int, op: str):
    if not isinstance(meta, Mapping):
        raise ValueError(f"{op}: meta must be a mapping")
    allowed = {"affine", "spatial_unit", "time_step", "time_unit"}
    unknown = set(meta) - allowed
    if unknown:
        raise ValueError(f"{op}: unsupported metadata key(s): {', '.join(sorted(map(str, unknown)))}")
    if "affine" not in meta or "spatial_unit" not in meta:
        raise ValueError(f"{op}: meta requires affine and explicit spatial_unit")
    affine = np.asarray(meta["affine"], dtype=np.float64)
    if affine.shape != (4, 4) or not np.all(np.isfinite(affine)) or not np.allclose(affine[3], [0, 0, 0, 1], rtol=0, atol=1e-12):
        raise ValueError(f"{op}: affine must be a finite 4x4 homogeneous matrix")
    zooms = np.linalg.norm(affine[:3, :3], axis=0)
    if np.any(zooms <= 0):
        raise ValueError(f"{op}: affine spatial axes must have nonzero scale")
    rotation = affine[:3, :3] / zooms
    qfac = 1.0
    if np.linalg.det(rotation) < 0:
        qfac = -1.0
        rotation[:, 2] *= -1
    quat = _rotation_quaternion(rotation, op)
    if ndim == 4:
        if "time_step" not in meta or "time_unit" not in meta:
            raise ValueError(f"{op}: 4-D data requires time_step and explicit time_unit")
        time_step = float(meta["time_step"])
        if not math.isfinite(time_step) or time_step <= 0:
            raise ValueError(f"{op}: time_step must be positive and finite")
        temporal = meta["time_unit"]
    else:
        if "time_step" in meta or "time_unit" in meta:
            raise ValueError(f"{op}: time_step/time_unit apply only to 4-D data")
        time_step, temporal = 0.0, None
    unit_codes = _nifti_units(meta["spatial_unit"], temporal, op)
    return affine, zooms, qfac, quat, time_step, unit_codes


def nifti_write(volume, *, meta, compressed):
    """3-D/4-D 配列と affine/pixdim を単一ファイル NIfTI-1 の ``bytes`` にする。

    ``meta`` は ``affine`` と ``spatial_unit``(``m/mm/um``)を必須とし、4-D では
    ``time_step`` と ``time_unit`` も必須。qform と sform の両方へ同じ affine を書く。
    ``compressed`` で ``.nii`` / ``.nii.gz`` 相当を選ぶ。呼び出し例:
    ``nifti_write(vol, meta={"affine": affine, "spatial_unit": "mm"}, compressed=True)``。
    """
    op = "nifti_write"
    array = np.asarray(volume)
    if array.ndim not in (3, 4) or array.size == 0:
        raise ValueError(f"{op}: data must be a non-empty 3-D or 4-D array, got {array.shape!r}")
    native_dtype = array.dtype.newbyteorder("=")
    datatype_by_dtype = {dtype: code for code, dtype in _NIFTI_DTYPES.items()}
    if native_dtype not in datatype_by_dtype:
        raise ValueError(f"{op}: unsupported dtype {array.dtype}; use fixed-width integers or float32/float64")
    if not isinstance(compressed, (bool, np.bool_)):
        raise ValueError(f"{op}: compressed must be bool (False for {_NIFTI_EXTENSIONS[0]}, True for {_NIFTI_EXTENSIONS[1]})")
    affine, zooms, qfac, quat, time_step, unit_codes = _nifti_affine_parts(meta, array.ndim, op)
    datatype = datatype_by_dtype[native_dtype]
    header = bytearray(352)
    struct.pack_into("<i", header, 0, 348)
    dims = [array.ndim, *array.shape, *([1] * (7 - array.ndim))]
    struct.pack_into("<8h", header, 40, *dims)
    struct.pack_into("<2h", header, 70, datatype, native_dtype.itemsize * 8)
    pixdim = [qfac, *zooms, time_step, 1.0, 1.0, 1.0]
    struct.pack_into("<8f", header, 76, *pixdim)
    struct.pack_into("<3f", header, 108, 352.0, 1.0, 0.0)
    header[123] = unit_codes[0] | unit_codes[1]
    description = b"Fullseye in-memory NIfTI-1 writer"
    header[148:148 + len(description)] = description
    struct.pack_into("<2h", header, 252, 1, 1)
    struct.pack_into("<3f", header, 256, *quat[1:])
    struct.pack_into("<3f", header, 268, *affine[:3, 3])
    struct.pack_into("<4f", header, 280, *affine[0])
    struct.pack_into("<4f", header, 296, *affine[1])
    struct.pack_into("<4f", header, 312, *affine[2])
    header[344:348] = b"n+1\0"
    stored = np.asarray(array, dtype=native_dtype.newbyteorder("<")).tobytes(order="F")
    payload = bytes(header) + stored
    return gzip.compress(payload, compresslevel=9, mtime=0) if compressed else payload


def _nifti_qform(raw: bytes, endian: str, pixdim):
    b, c, d = struct.unpack_from(endian + "3f", raw, 256)
    norm = b * b + c * c + d * d
    a = math.sqrt(max(0.0, 1.0 - norm)) if norm <= 1.00001 else 0.0
    if norm > 1.00001:
        scale = math.sqrt(norm)
        b, c, d = b / scale, c / scale, d / scale
    rotation = np.asarray([
        [a*a+b*b-c*c-d*d, 2*b*c-2*a*d, 2*b*d+2*a*c],
        [2*b*c+2*a*d, a*a+c*c-b*b-d*d, 2*c*d-2*a*b],
        [2*b*d-2*a*c, 2*c*d+2*a*b, a*a+d*d-c*c-b*b],
    ], dtype=np.float64)
    qfac = -1.0 if pixdim[0] < 0 else 1.0
    affine = np.eye(4, dtype=np.float64)
    affine[:3, :3] = rotation @ np.diag([pixdim[1], pixdim[2], pixdim[3] * qfac])
    affine[:3, 3] = struct.unpack_from(endian + "3f", raw, 268)
    return affine


def nifti_read(data):
    """単一ファイル NIfTI-1(``.nii`` / ``.nii.gz``)を ``(array, meta)`` として読む。

    3-D/4-D、qform/sform、pixdim と空間・時間単位を返す。pair 形式、拡張、未知 datatype、
    header/shape/byte 数の不一致は拒否する。呼び出し例: ``volume, meta = nifti_read(payload)``。
    """
    op = "nifti_read"
    encoded = _file_bytes(data, op)
    compressed = encoded.startswith(b"\x1f\x8b")
    if compressed:
        try:
            raw = gzip.decompress(encoded)
        except (OSError, EOFError) as exc:
            raise ValueError(f"{op}: corrupt or truncated .nii.gz payload: {exc}") from exc
    else:
        raw = encoded
    if len(raw) < 352:
        raise ValueError(f"{op}: NIfTI-1 header is truncated ({len(raw)} bytes; need at least 352)")
    little, big = struct.unpack_from("<i", raw, 0)[0], struct.unpack_from(">i", raw, 0)[0]
    if little == 348:
        endian = "<"
    elif big == 348:
        endian = ">"
    else:
        raise ValueError(f"{op}: sizeof_hdr is not 348 in either byte order")
    magic = raw[344:348]
    if magic != b"n+1\0":
        if magic == b"ni1\0":
            raise ValueError(f"{op}: two-file .hdr/.img NIfTI is unsupported; pass a single .nii")
        raise ValueError(f"{op}: invalid NIfTI-1 magic {magic!r} for {_NIFTI_EXTENSIONS}")
    dims = struct.unpack_from(endian + "8h", raw, 40)
    ndim = dims[0]
    if ndim not in (3, 4):
        raise ValueError(f"{op}: dim[0] must be 3 or 4, got {ndim}")
    shape = tuple(int(v) for v in dims[1:ndim + 1])
    if any(v <= 0 for v in shape):
        raise ValueError(f"{op}: dimensions must be positive, got {shape!r}")
    datatype, bitpix = struct.unpack_from(endian + "2h", raw, 70)
    if datatype not in _NIFTI_DTYPES:
        raise ValueError(f"{op}: unsupported NIfTI datatype code {datatype}")
    dtype = _NIFTI_DTYPES[datatype]
    if bitpix != dtype.itemsize * 8:
        raise ValueError(f"{op}: datatype {datatype} requires bitpix {dtype.itemsize * 8}, got {bitpix}")
    vox_offset, slope, intercept = struct.unpack_from(endian + "3f", raw, 108)
    if vox_offset != 352.0 or raw[348:352] != b"\0\0\0\0":
        raise ValueError(f"{op}: NIfTI extensions or vox_offset {vox_offset:g} are unsupported")
    count = math.prod(shape)
    expected = 352 + count * dtype.itemsize
    if len(raw) != expected:
        raise ValueError(f"{op}: dimensions/datatype declare {expected} total bytes, got {len(raw)}")
    dtype = dtype.newbyteorder(endian)
    array = np.frombuffer(raw, dtype=dtype, count=count, offset=352).reshape(shape, order="F").copy()
    if array.dtype.itemsize > 1:
        array = array.astype(array.dtype.newbyteorder("="), copy=False)
    if slope != 0 and (slope != 1 or intercept != 0):
        if not math.isfinite(slope) or not math.isfinite(intercept):
            raise ValueError(f"{op}: scl_slope/scl_inter must be finite")
        array = array.astype(np.float64) * slope + intercept
    pixdim = np.asarray(struct.unpack_from(endian + "8f", raw, 76), dtype=np.float64)
    if np.any(~np.isfinite(pixdim[1:ndim + 1])) or np.any(pixdim[1:ndim + 1] <= 0):
        raise ValueError(f"{op}: pixdim must be positive and finite for every data axis")
    qform_code, sform_code = struct.unpack_from(endian + "2h", raw, 252)
    qform = _nifti_qform(raw, endian, pixdim) if qform_code > 0 else None
    if sform_code > 0:
        sform = np.eye(4, dtype=np.float64)
        sform[:3] = np.asarray([struct.unpack_from(endian + "4f", raw, offset)
                                for offset in (280, 296, 312)], dtype=np.float64)
        if not np.all(np.isfinite(sform)):
            raise ValueError(f"{op}: sform contains NaN/Inf")
    else:
        sform = None
    fallback = np.diag([pixdim[1], pixdim[2], pixdim[3], 1.0])
    affine = sform if sform is not None else qform if qform is not None else fallback
    units = raw[123]
    spatial_code, temporal_code = units & 0x07, units & 0x38
    if spatial_code not in _NIFTI_SPATIAL_UNITS:
        raise ValueError(f"{op}: spatial xyzt_units code {spatial_code} is unknown; unit must be explicit")
    if ndim == 4 and temporal_code not in _NIFTI_TIME_UNITS:
        raise ValueError(f"{op}: temporal xyzt_units code {temporal_code} is unknown for 4-D data")
    return array, {"format": "NIfTI-1", "compressed": compressed,
                   "affine": affine, "qform_affine": qform, "sform_affine": sform,
                   "qform_code": int(qform_code), "sform_code": int(sform_code),
                   "pixdim": pixdim[1:ndim + 1], "spatial_unit": _NIFTI_SPATIAL_UNITS[spatial_code],
                   "time_unit": _NIFTI_TIME_UNITS.get(temporal_code)}


def _require_tifffile():
    try:
        import tifffile
    except ImportError as exc:
        raise ImportError("OME-TIFF operators require tifffile; install it with `pip install tifffile`") from exc
    return tifffile


def _ome_unit(value, op: str, key: str):
    aliases = {"m": "m", "meter": "m", "mm": "mm", "millimeter": "mm",
               "um": "µm", "µm": "µm", "micrometer": "µm", "nm": "nm",
               "nanometer": "nm", "angstrom": "Å", "ångström": "Å", "å": "Å"}
    unit = aliases.get(str(value).strip().lower())
    if unit is None:
        raise ValueError(f"{op}: {key} must be one of m/mm/um/nm/angstrom, got {value!r}")
    return unit


def _ome_axes_meta(array, meta, op: str):
    if not isinstance(meta, Mapping):
        raise ValueError(f"{op}: meta must be a mapping")
    allowed = {"axes", "physical_size_x", "physical_size_x_unit",
               "physical_size_y", "physical_size_y_unit", "physical_size_z",
               "physical_size_z_unit", "channel_names"}
    unknown = set(meta) - allowed
    if unknown:
        raise ValueError(f"{op}: unsupported metadata key(s): {', '.join(sorted(map(str, unknown)))}")
    axes = str(meta.get("axes", "")).upper()
    if len(axes) != array.ndim or len(set(axes)) != len(axes) or any(axis not in _OME_AXIS_ORDER for axis in axes):
        raise ValueError(f"{op}: axes must contain one unique TCZYX letter per array dimension")
    if "".join(axis for axis in _OME_AXIS_ORDER if axis in axes) != axes or not axes.endswith("YX"):
        raise ValueError(f"{op}: axes must follow canonical TCZYX order and end in YX, got {axes!r}")
    physical = {}
    for axis in "XY" + ("Z" if "Z" in axes else ""):
        key, unit_key = f"physical_size_{axis.lower()}", f"physical_size_{axis.lower()}_unit"
        if key not in meta or unit_key not in meta:
            raise ValueError(f"{op}: meta requires {key} and explicit {unit_key}")
        value = float(meta[key])
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{op}: {key} must be positive and finite")
        physical[axis] = (value, _ome_unit(meta[unit_key], op, unit_key))
    if "Z" not in axes and ("physical_size_z" in meta or "physical_size_z_unit" in meta):
        raise ValueError(f"{op}: physical_size_z applies only when axes contains Z")
    if "C" in axes:
        if "channel_names" not in meta:
            raise ValueError(f"{op}: axes contains C, so channel_names is required")
        names = list(meta["channel_names"])
        channel_count = array.shape[axes.index("C")]
        if len(names) != channel_count or any(not isinstance(name, str) or not name.strip() for name in names):
            raise ValueError(f"{op}: channel_names must contain {channel_count} non-empty strings")
    else:
        names = list(meta.get("channel_names", []))
        if names:
            raise ValueError(f"{op}: channel_names requires a C axis")
    return axes, physical, names


def ome_tiff_write(stack, *, meta):
    """TCZYX 多次元配列と物理サイズ・チャネル名を OME-TIFF の ``bytes`` にする。

    ``meta['axes']`` は TCZYX の部分列で YX 終端。X/Y(および Z 軸があれば Z)の
    ``physical_size_*`` と ``*_unit``、C 軸があれば ``channel_names`` を必須とする。
    呼び出し例: ``ome_tiff_write(stack, meta={"axes": "CZYX", ...})``。
    """
    op = "ome_tiff_write"
    array = np.asarray(stack)
    if array.ndim < 2 or array.size == 0:
        raise ValueError(f"{op}: stack for {_OME_EXTENSIONS} must be a non-empty array with at least YX axes")
    if array.dtype.kind not in "uibf" or array.dtype.itemsize not in (1, 2, 4, 8):
        raise ValueError(f"{op}: unsupported TIFF dtype {array.dtype}")
    axes, physical, channel_names = _ome_axes_meta(array, meta, op)
    metadata = {"axes": axes}
    for axis, (value, unit) in physical.items():
        metadata[f"PhysicalSize{axis}"] = value
        metadata[f"PhysicalSize{axis}Unit"] = unit
    if channel_names:
        metadata["Channel"] = {"Name": channel_names}
    digest = hashlib.sha256()
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(array.shape).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    for key in sorted(metadata):
        digest.update(key.encode("ascii"))
        digest.update(repr(metadata[key]).encode("utf-8"))
    metadata["UUID"] = str(uuid.UUID(hex=digest.hexdigest()[:32]))
    tifffile = _require_tifffile()
    stream = io.BytesIO()
    try:
        tifffile.imwrite(stream, array, ome=True, metadata=metadata,
                         photometric="minisblack", compression=None)
    except Exception as exc:
        raise ValueError(f"{op}: tifffile could not encode the TCZYX stack: {exc}") from exc
    return stream.getvalue()


def _ome_xml_meta(xml: str, shape, axes: str, dtype, op: str):
    try:
        root = _ET.fromstring(xml)
    except _ET.ParseError as exc:
        raise ValueError(f"{op}: malformed OME-XML: {exc}") from exc
    images = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "Image"]
    if len(images) != 1:
        raise ValueError(f"{op}: expected exactly one OME Image, found {len(images)}")
    pixels_nodes = [node for node in images[0] if node.tag.rsplit("}", 1)[-1] == "Pixels"]
    if len(pixels_nodes) != 1:
        raise ValueError(f"{op}: OME Image must contain exactly one Pixels element")
    pixels = pixels_nodes[0]
    dimension_order = pixels.attrib.get("DimensionOrder")
    if dimension_order not in ("XYZCT", "XYZTC", "XYCZT", "XYCTZ", "XYTCZ", "XYTZC"):
        raise ValueError(f"{op}: unsupported OME DimensionOrder {dimension_order!r}")
    size_map = {axis: shape[axes.index(axis)] if axis in axes else 1 for axis in _OME_AXIS_ORDER}
    for axis in _OME_AXIS_ORDER:
        key = f"Size{axis}"
        try:
            declared = int(pixels.attrib[key])
        except (KeyError, ValueError) as exc:
            raise ValueError(f"{op}: OME-XML has invalid or missing {key}") from exc
        if declared != size_map[axis]:
            raise ValueError(f"{op}: OME-XML {key}={declared} disagrees with {axes} array shape {shape!r}")
    physical, units = {}, {}
    for axis in "XY" + ("Z" if "Z" in axes else ""):
        value_key, unit_key = f"PhysicalSize{axis}", f"PhysicalSize{axis}Unit"
        if value_key not in pixels.attrib or unit_key not in pixels.attrib:
            raise ValueError(f"{op}: OME-XML requires {value_key} and explicit {unit_key}")
        try:
            value = float(pixels.attrib[value_key])
        except ValueError as exc:
            raise ValueError(f"{op}: invalid {value_key}") from exc
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{op}: {value_key} must be positive and finite")
        physical[axis], units[axis] = value, _ome_unit(pixels.attrib[unit_key], op, unit_key)
    channels = [node for node in pixels if node.tag.rsplit("}", 1)[-1] == "Channel"]
    names = [node.attrib.get("Name", "") for node in channels]
    if "C" in axes:
        if len(channels) != size_map["C"] or any(not name for name in names):
            raise ValueError(f"{op}: OME-XML must name all {size_map['C']} channels")
    elif len(channels) != 1:
        raise ValueError(f"{op}: OME-XML without C axis must have one implicit channel")
    return {"dimension_order": dimension_order,
            "physical_size_x": physical["X"], "physical_size_x_unit": units["X"],
            "physical_size_y": physical["Y"], "physical_size_y_unit": units["Y"],
            **({"physical_size_z": physical["Z"], "physical_size_z_unit": units["Z"]} if "Z" in axes else {}),
            "channel_names": names if "C" in axes else []}


def ome_tiff_read(data):
    """OME-TIFF を ``(stack, meta)`` として読み、OME-XML と配列を相互検証する。

    ``meta`` は TCZYX 部分列の ``axes``、物理サイズと単位、チャネル名を持つ。
    通常 TIFF、複数 Image、XML の Size/dtype と TIFF の不一致、無名チャネルは拒否する。
    呼び出し例: ``stack, meta = ome_tiff_read(payload)``。
    """
    op = "ome_tiff_read"
    raw = _file_bytes(data, op)
    tifffile = _require_tifffile()
    try:
        with tifffile.TiffFile(io.BytesIO(raw)) as tif:
            if not tif.is_ome or not tif.ome_metadata:
                raise ValueError(f"{op}: input is TIFF but has no OME-XML metadata required by {_OME_EXTENSIONS}")
            if len(tif.series) != 1:
                raise ValueError(f"{op}: expected exactly one TIFF series, found {len(tif.series)}")
            series = tif.series[0]
            axes = series.axes
            array = series.asarray()
            xml = tif.ome_metadata
    except Exception as exc:
        if isinstance(exc, ValueError) and str(exc).startswith(op + ":"):
            raise
        raise ValueError(f"{op}: corrupt or truncated TIFF: {exc}") from exc
    if len(axes) != array.ndim or "".join(axis for axis in _OME_AXIS_ORDER if axis in axes) != axes or not axes.endswith("YX"):
        raise ValueError(f"{op}: TIFF axes {axes!r} are not a canonical TCZYX subset ending in YX")
    parsed = _ome_xml_meta(xml, array.shape, axes, array.dtype, op)
    return array, {"format": "OME-TIFF", "axes": axes, **parsed}
