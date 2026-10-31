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
import struct
from collections.abc import Mapping

import numpy as np
import mesh as _mesh

__all__ = [
    "table_write_csv", "table_read_csv",
    "mesh_write_ply", "mesh_read_ply", "mesh_write_stl", "mesh_read_stl",
    "mesh_write_obj", "mesh_read_obj", "mesh_write_off", "mesh_read_off",
    "points_write_xyz", "points_read_xyz",
]

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
