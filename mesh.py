"""3-D mesh / point-cloud file readers and geometry helpers (numpy + scipy only).

The *import* side of the perception stack: this turns a 3-D object file — a CAD
part, a scanned prop, the collision mesh of a MuJoCo asset — into the plain numpy
arrays the rest of the library already speaks, so a physical-AI project can hand
a robot something to look at and to grasp:

    import fullseye as fs
    V, F = fs.read_mesh("part.stl")            # (nv,3) float64, (nf,3) int64
    model = fs.sample_surface(V, F, 4000)      # -> (N,3) cloud
    n     = fs.estimate_normals(model)         # pointcloud.py: grasp approach dirs
    T     = fs.register(scan, model)           # registration.py: object pose
    occ, origin = fs.voxelize(V, F, 0.01)      # -> the `volume` sort (3-D array)

Four formats are read, chosen because each is completely specified by a public,
dependency-free spec — no third-party parser (and no GPL code) is needed:

  ``.obj``  Wavefront OBJ — Wavefront Technologies' *Advanced Visualizer* file
            format (public spec; ``v`` / ``f`` records).
  ``.stl``  binary **and** ASCII — 3D Systems, *StereoLithography Interface
            Specification* (1989). Binary STL is little-endian by spec.
  ``.ply``  ASCII and binary (little- **and** big-endian) — Greg Turk, "The PLY
            Polygon File Format" (Stanford, 1994).
  ``.off``  Object File Format — the Geomview / Princeton Shape Benchmark spec.

Point clouds additionally read ``.xyz`` (plain ``x y z [r g b]`` text) and
ASCII ``.pcd`` (Point Cloud Library file format).

Honest limitations (nothing here claims more than its round-trip test proves):

  * Polygons with more than 3 corners are **fan-triangulated** (correct for
    convex faces, which is what these formats carry in practice; a concave
    n-gon can produce triangles outside the polygon).
  * :func:`voxelize` is **surface** voxelization — it marks the cells a triangle
    passes through, it does not fill the interior.
  * PLY vertex properties beyond ``x/y/z`` and an RGB triple are **ignored**
    (normals, alpha, confidence, custom properties). Element types other than
    ``vertex`` / ``face`` are parsed for structure but dropped.
  * Materials, textures, normals, groups, smoothing and per-face attributes are
    not read from any format — this module returns geometry only.
  * Binary PCD and the heavier formats (glTF/GLB, COLLADA, LAS) are **not**
    supported here; they need more than numpy and belong in an optional extra.
  * STL carries no vertex sharing, so :func:`read_mesh` welds bit-identical
    coordinates into shared vertices; coordinates that differ in the last float
    bit stay separate.

Every reader is **fail-closed** on untrusted input: magic bytes and headers are
validated, declared element counts are checked against the bytes actually
present, counts and file size are capped (``MAX_FILE_BYTES`` / ``MAX_ELEMENTS``),
and NaN/Inf coordinates are rejected. A malformed file raises ``ValueError`` with
a message naming the file and the problem — it never returns partial garbage.
"""
from __future__ import annotations

import os

import numpy as np

__all__ = [
    "read_mesh", "read_points", "write_mesh",
    "sample_surface", "mesh_to_points", "voxelize",
    "bounds", "recenter", "normalize_scale",
    "MESH_FORMATS", "POINT_FORMATS",
]

#: Extensions :func:`read_mesh` accepts.
MESH_FORMATS = (".obj", ".stl", ".ply", ".off")
#: Extensions :func:`read_points` accepts.
POINT_FORMATS = (".ply", ".xyz", ".txt", ".pts", ".asc", ".obj", ".pcd", ".off", ".stl")

#: Refuse files larger than this (untrusted input / accidental DoS guard).
MAX_FILE_BYTES = 1 << 29          # 512 MiB
#: Refuse a declared vertex/face/element count larger than this.
MAX_ELEMENTS = 50_000_000
#: Refuse a voxel grid with more cells than this (a bool array of that size).
MAX_VOXELS = 1 << 27              # ~134 M cells = 134 MB as bool
_MAX_SUBDIV = 4096                # per-triangle rasterisation subdivisions
_MAX_VOXEL_SAMPLES = 50_000_000   # total rasterisation samples across the mesh
_CHUNK = 1 << 20                  # sample points held in memory at once

_PLY_TYPES = {
    "char": "i1", "int8": "i1", "uchar": "u1", "uint8": "u1",
    "short": "i2", "int16": "i2", "ushort": "u2", "uint16": "u2",
    "int": "i4", "int32": "i4", "uint": "u4", "uint32": "u4",
    "float": "f4", "float32": "f4", "double": "f8", "float64": "f8",
}
_OFF_MAGIC = ("OFF", "COFF", "NOFF", "CNOFF", "STOFF", "STCOFF", "4OFF", "NCOFF")


# ---- low-level guards ------------------------------------------------------ #
def _ext(path: str) -> str:
    return os.path.splitext(str(path))[1].lower()


def _read_bytes(path: str) -> bytes:
    """Read a file whole after checking it exists and is within the size cap."""
    p = str(path)
    if not os.path.isfile(p):
        raise FileNotFoundError(p)
    size = os.path.getsize(p)
    if size == 0:
        raise ValueError("%s is empty" % p)
    if size > MAX_FILE_BYTES:
        raise ValueError("%s is %d bytes, over the %d-byte cap (mesh.MAX_FILE_BYTES)"
                         % (p, size, MAX_FILE_BYTES))
    with open(p, "rb") as f:
        return f.read()


def _text(raw: bytes) -> str:
    return raw.decode("utf-8", "replace")


def _check_count(n: int, what: str, src: str) -> int:
    if n < 0:
        raise ValueError("%s: negative %s count (%d)" % (src, what, n))
    if n > MAX_ELEMENTS:
        raise ValueError("%s: declares %d %s, over the %d cap (mesh.MAX_ELEMENTS)"
                         % (src, n, what, MAX_ELEMENTS))
    return n


def _floats(tokens, what: str, src: str) -> np.ndarray:
    """Token list -> float64 array, with a message that names the file."""
    try:
        return np.array(tokens, dtype=np.float64)
    except (ValueError, TypeError):
        raise ValueError("%s: malformed %s — expected numbers, got %r"
                         % (src, what, list(tokens)[:6])) from None


def _ints(tokens, what: str, src: str) -> np.ndarray:
    try:
        return np.array(tokens, dtype=np.int64)
    except (ValueError, TypeError):
        raise ValueError("%s: malformed %s — expected integers, got %r"
                         % (src, what, list(tokens)[:6])) from None


def _one_int(tok, what: str, src: str) -> int:
    try:
        return int(tok)
    except (ValueError, TypeError):
        raise ValueError("%s: malformed %s — expected an integer, got %r"
                         % (src, what, tok)) from None


def _finite_points(P, what: str, src: str) -> np.ndarray:
    """Coerce to (N, 3) float64 and reject NaN/Inf (a poisoned coordinate would
    silently corrupt every downstream registration / grasp computation)."""
    A = np.asarray(P, np.float64)
    if A.size == 0:
        return np.zeros((0, 3), np.float64)
    if A.ndim != 2 or A.shape[1] != 3:
        raise ValueError("%s: %s must be (N, 3), got %r" % (src, what, (A.shape,)))
    bad = ~np.isfinite(A)
    if bad.any():
        row = int(np.flatnonzero(bad.any(axis=1))[0])
        raise ValueError("%s: %s contain %d non-finite value(s) (first at index %d: %r)"
                         % (src, what, int(bad.sum()), row, A[row].tolist()))
    return A


def _fan_triangulate(faces, src: str) -> np.ndarray:
    """Polygon faces -> (nf, 3) int64 triangles by fan triangulation.

    *faces* is a list of index sequences **or** a uniform 2-D index array.
    A ``k``-gon becomes ``k-2`` triangles ``(f0, fi, fi+1)``; face order is kept.
    """
    if isinstance(faces, np.ndarray) and faces.ndim == 2:
        P, k = faces.astype(np.int64), int(faces.shape[1])
        if k < 3:
            raise ValueError("%s: face with %d vertices (need >= 3)" % (src, k))
    else:
        if len(faces) == 0:
            return np.zeros((0, 3), np.int64)
        sizes = np.fromiter((len(f) for f in faces), np.int64, len(faces))
        if int(sizes.min()) < 3:
            raise ValueError("%s: face with %d vertices (need >= 3)" % (src, int(sizes.min())))
        if int(sizes.min()) != int(sizes.max()):
            out = []
            for f in faces:
                f = np.asarray(f, np.int64)
                for i in range(1, len(f) - 1):
                    out.append((f[0], f[i], f[i + 1]))
            return np.asarray(out, np.int64).reshape(-1, 3)
        k = int(sizes[0])
        P = np.asarray([np.asarray(f, np.int64) for f in faces], np.int64).reshape(-1, k)
    if P.shape[0] == 0:
        return np.zeros((0, 3), np.int64)
    tris = np.stack([np.stack([P[:, 0], P[:, i], P[:, i + 1]], axis=1)
                     for i in range(1, k - 1)], axis=1)          # (m, k-2, 3)
    return tris.reshape(-1, 3).astype(np.int64)


def _finish_mesh(V, faces, src: str):
    """Validate vertices, triangulate faces, bounds-check every index."""
    V = _finite_points(V, "vertices", src)
    F = _fan_triangulate(faces, src)
    if F.size:
        lo, hi = int(F.min()), int(F.max())
        if lo < 0 or hi >= V.shape[0]:
            raise ValueError("%s: face index %d out of range for %d vertices"
                             % (src, hi if hi >= V.shape[0] else lo, V.shape[0]))
    return V, F


def _weld(P: np.ndarray):
    """Per-corner triangle soup (3m, 3) -> shared (V, F) by exact coordinate match."""
    V, inv = np.unique(P, axis=0, return_inverse=True)
    return V.astype(np.float64), np.asarray(inv).ravel().reshape(-1, 3).astype(np.int64)


# ---- Wavefront OBJ --------------------------------------------------------- #
def _read_obj_vertices(raw: bytes, src: str):
    """``v`` records -> (V, C). Colours only when a line carries exactly 6 numbers
    (``x y z r g b``, the common vertex-colour extension); ``v x y z w`` keeps w
    out of the colours."""
    rows, widths = [], []
    for ln in _text(raw).splitlines():
        s = ln.strip()
        if not s or s[0] == "#" or not s.startswith("v "):
            continue
        parts = s.split()
        if len(parts) < 4:
            raise ValueError("%s: OBJ 'v' record needs 3 coordinates, got %r" % (src, s[:60]))
        rows.append(parts[1:7])
        widths.append(len(parts) - 1)
    # OBJ declares no counts, so "not one v record" cannot be told from "not an OBJ":
    # fail closed rather than hand back an empty mesh for an arbitrary file.
    if not rows:
        raise ValueError("%s: no 'v' vertex records — not a Wavefront OBJ file?" % src)
    V = _floats([r[:3] for r in rows], "OBJ vertex", src)
    C = None
    if all(w == 6 for w in widths):
        C = np.clip(_floats([r[3:6] for r in rows], "OBJ vertex colour", src), 0.0, 1.0)
    return V, C


def _read_obj(raw: bytes, src: str):
    V, _ = _read_obj_vertices(raw, src)
    nv_seen, seen, faces = 0, 0, []
    for ln in _text(raw).splitlines():
        s = ln.strip()
        if not s or s[0] == "#":
            continue
        if s.startswith("v "):
            seen += 1
            continue
        if not s.startswith("f "):
            continue
        nv_seen = seen
        idx = []
        for tok in s.split()[1:]:
            first = tok.split("/")[0]
            if not first:
                raise ValueError("%s: OBJ face vertex %r has no vertex index" % (src, tok))
            i = _one_int(first, "OBJ face index", src)
            if i == 0:
                raise ValueError("%s: OBJ indices are 1-based, got 0" % src)
            idx.append(i - 1 if i > 0 else nv_seen + i)      # negative = relative, per spec
        if len(idx) < 3:
            raise ValueError("%s: OBJ face with %d vertices (need >= 3)" % (src, len(idx)))
        faces.append(np.asarray(idx, np.int64))
    return _finish_mesh(V, faces, src)


# ---- OFF ------------------------------------------------------------------- #
def _off_lines(raw: bytes) -> list:
    out = []
    for ln in _text(raw).splitlines():
        s = ln.split("#")[0].strip()
        if s:
            out.append(s)
    return out


def _read_off(raw: bytes, src: str):
    lines = _off_lines(raw)
    if not lines:
        raise ValueError("%s: OFF file has no content" % src)
    head = lines[0].split()
    if head[0].upper() not in _OFF_MAGIC:
        raise ValueError("%s: not an OFF file — first line is %r, expected an 'OFF' magic"
                         % (src, lines[0][:40]))
    if len(head) >= 4:                       # counts on the magic line: "OFF 8 12 0"
        counts, li = head[1:4], 1
    else:
        if len(lines) < 2:
            raise ValueError("%s: OFF file ends before its counts line" % src)
        counts, li = lines[1].split(), 2
    if len(counts) < 3:
        raise ValueError("%s: OFF counts line needs 'nvert nface nedge', got %r"
                         % (src, " ".join(counts)))
    nv = _check_count(_one_int(counts[0], "OFF vertex count", src), "vertices", src)
    nf = _check_count(_one_int(counts[1], "OFF face count", src), "faces", src)
    if len(lines) < li + nv + nf:
        raise ValueError("%s: OFF declares %d vertices + %d faces but only %d data lines follow"
                         % (src, nv, nf, len(lines) - li))
    vrows = []
    for i in range(nv):
        t = lines[li + i].split()
        if len(t) < 3:
            raise ValueError("%s: OFF vertex line %d has %d value(s), need 3"
                             % (src, i, len(t)))
        vrows.append(t[:3])
    V = _floats(vrows, "OFF vertex", src) if vrows else np.zeros((0, 3))
    faces = []
    for i in range(nf):
        t = lines[li + nv + i].split()
        k = _one_int(t[0], "OFF face size", src) if t else 0
        if k < 3:
            raise ValueError("%s: OFF face line %d declares %d vertices (need >= 3)"
                             % (src, i, k))
        if len(t) < k + 1:
            raise ValueError("%s: OFF face line %d declares %d indices but carries %d"
                             % (src, i, k, len(t) - 1))
        faces.append(_ints(t[1:k + 1], "OFF face index", src))
    return _finish_mesh(V, faces, src)


# ---- STL (binary + ASCII) --------------------------------------------------- #
_STL_DTYPE = np.dtype([("normal", "<f4", (3,)), ("v", "<f4", (3, 3)), ("attr", "<u2")])


def _read_stl(raw: bytes, src: str):
    head = raw[:5].lower()
    probe = raw[:4096].lower()
    if head == b"solid" and b"facet" in probe:
        return _read_stl_ascii(raw, src)
    if len(raw) < 84:
        raise ValueError("%s: %d bytes is too short for a binary STL (80-byte header "
                         "+ 4-byte count) and it does not start with 'solid'"
                         % (src, len(raw)))
    return _read_stl_binary(raw, src)


def _read_stl_ascii(raw: bytes, src: str):
    toks = _text(raw).split()
    rows, i, n = [], 0, len(toks)
    while i < n:
        if toks[i] == "vertex":
            if i + 3 >= n:
                raise ValueError("%s: ASCII STL ends inside a 'vertex' record" % src)
            rows.append(toks[i + 1:i + 4])
            i += 4
        else:
            i += 1
    if not rows:
        raise ValueError("%s: ASCII STL has no 'vertex' records" % src)
    if len(rows) % 3:
        raise ValueError("%s: ASCII STL has %d vertex records, not a multiple of 3"
                         % (src, len(rows)))
    _check_count(len(rows) // 3, "triangles", src)
    P = _finite_points(_floats(rows, "STL vertex", src), "vertices", src)
    V, F = _weld(P)
    return _finish_mesh(V, F, src)


def _read_stl_binary(raw: bytes, src: str):
    n = int(np.frombuffer(raw, "<u4", count=1, offset=80)[0])       # spec: little-endian
    _check_count(n, "triangles", src)
    need = 84 + _STL_DTYPE.itemsize * n
    if need > len(raw):
        raise ValueError("%s: binary STL header declares %d triangles (%d bytes) but the "
                         "file holds %d bytes" % (src, n, need, len(raw)))
    if n == 0:
        return np.zeros((0, 3), np.float64), np.zeros((0, 3), np.int64)
    tri = np.frombuffer(raw, _STL_DTYPE, count=n, offset=84)
    P = _finite_points(tri["v"].astype(np.float64).reshape(-1, 3), "vertices", src)
    V, F = _weld(P)
    return _finish_mesh(V, F, src)


# ---- PLY ------------------------------------------------------------------- #
def _ply_header(raw: bytes, src: str):
    """-> (format, elements, data_offset). Elements keep their declared property
    list so the body reader knows the exact byte / token layout."""
    if not raw.startswith(b"ply"):
        raise ValueError("%s: not a PLY file — missing the 'ply' magic" % src)
    end = raw.find(b"end_header")
    if end < 0:
        raise ValueError("%s: PLY header has no 'end_header' line" % src)
    nl = raw.find(b"\n", end)
    if nl < 0:
        raise ValueError("%s: PLY 'end_header' line is not terminated" % src)
    fmt, elements = None, []
    for ln in raw[:end].decode("ascii", "replace").splitlines():
        parts = ln.split()
        if not parts:
            continue
        key = parts[0]
        if key == "format":
            if len(parts) < 2:
                raise ValueError("%s: PLY 'format' line is incomplete" % src)
            fmt = parts[1]
        elif key == "element":
            if len(parts) < 3:
                raise ValueError("%s: PLY 'element' line is incomplete" % src)
            cnt = _check_count(_one_int(parts[2], "PLY element count", src),
                               "%r elements" % parts[1], src)
            elements.append({"name": parts[1], "count": cnt, "props": []})
        elif key == "property":
            if not elements:
                raise ValueError("%s: PLY 'property' before any 'element'" % src)
            if len(parts) >= 2 and parts[1] == "list":
                if len(parts) < 5:
                    raise ValueError("%s: PLY list property is incomplete: %r" % (src, ln[:60]))
                if parts[2] not in _PLY_TYPES or parts[3] not in _PLY_TYPES:
                    raise ValueError("%s: unsupported PLY property type in %r" % (src, ln[:60]))
                elements[-1]["props"].append({"kind": "list", "count_type": parts[2],
                                              "type": parts[3], "name": parts[4]})
            else:
                if len(parts) < 3:
                    raise ValueError("%s: PLY property is incomplete: %r" % (src, ln[:60]))
                if parts[1] not in _PLY_TYPES:
                    raise ValueError("%s: unsupported PLY property type %r" % (src, parts[1]))
                elements[-1]["props"].append({"kind": "scalar", "type": parts[1],
                                              "name": parts[2]})
    if fmt not in ("ascii", "binary_little_endian", "binary_big_endian"):
        raise ValueError("%s: unsupported PLY format %r (want ascii / binary_little_endian "
                         "/ binary_big_endian)" % (src, fmt))
    return fmt, elements, nl + 1


def _ply_ascii(elements, text: str, src: str) -> dict:
    toks = text.split()
    pos, out = 0, {}
    for el in elements:
        n, props = el["count"], el["props"]
        sc, li = {}, {}
        if props and all(p["kind"] == "scalar" for p in props):
            k, need = len(props), n * len(props)
            if pos + need > len(toks):
                raise ValueError("%s: PLY element %r declares %d rows (%d values) but only "
                                 "%d values remain" % (src, el["name"], n, need, len(toks) - pos))
            block = _floats(toks[pos:pos + need], "PLY %r data" % el["name"], src).reshape(n, k)
            pos += need
            for j, p in enumerate(props):
                sc[p["name"]] = block[:, j]
        else:
            for p in props:
                (sc if p["kind"] == "scalar" else li)[p["name"]] = (
                    np.zeros(n, np.float64) if p["kind"] == "scalar" else [])
            for i in range(n):
                for p in props:
                    if pos >= len(toks):
                        raise ValueError("%s: PLY element %r ends after %d of %d rows"
                                         % (src, el["name"], i, n))
                    if p["kind"] == "scalar":
                        sc[p["name"]][i] = _floats([toks[pos]], "PLY %r" % p["name"], src)[0]
                        pos += 1
                    else:
                        c = _one_int(toks[pos], "PLY list length", src)
                        pos += 1
                        if c < 0 or pos + c > len(toks):
                            raise ValueError("%s: PLY list of length %d at row %d runs past the "
                                             "end of the file" % (src, c, i))
                        li[p["name"]].append(_ints(toks[pos:pos + c], "PLY list value", src))
                        pos += c
        out[el["name"]] = {"scalars": sc, "lists": li, "count": n,
                           "types": {p["name"]: p["type"] for p in props}}
    return out


def _ply_binary(elements, raw: bytes, offset: int, endian: str, src: str) -> dict:
    out, total = {}, len(raw)
    for el in elements:
        n, props = el["count"], el["props"]
        sc, li = {}, {}
        if props and all(p["kind"] == "scalar" for p in props):
            dt = np.dtype([("f%d" % j, endian + _PLY_TYPES[p["type"]])
                           for j, p in enumerate(props)])
            need = dt.itemsize * n
            if offset + need > total:
                raise ValueError("%s: PLY element %r declares %d rows (%d bytes) but only %d "
                                 "bytes remain" % (src, el["name"], n, need, total - offset))
            arr = np.frombuffer(raw, dt, count=n, offset=offset)
            offset += need
            for j, p in enumerate(props):
                sc[p["name"]] = arr["f%d" % j].astype(np.float64)
        elif len(props) == 1 and props[0]["kind"] == "list" and n > 0:
            p = props[0]
            ct, vt = endian + _PLY_TYPES[p["count_type"]], endian + _PLY_TYPES[p["type"]]
            csz = np.dtype(ct).itemsize
            if offset + csz > total:
                raise ValueError("%s: PLY element %r declares %d rows but the data ends at the "
                                 "first length field" % (src, el["name"], n))
            k = int(np.frombuffer(raw, ct, count=1, offset=offset)[0])
            if k < 0:
                raise ValueError("%s: PLY negative list length (%d)" % (src, k))
            dt = np.dtype([("n", ct), ("v", vt, (k,))])
            uniform = False
            if k >= 1 and offset + dt.itemsize * n <= total:
                arr = np.frombuffer(raw, dt, count=n, offset=offset)
                if bool(np.all(arr["n"] == k)):                    # every row has k entries
                    li[p["name"]] = arr["v"].astype(np.int64)      # (n, k) — fast path
                    offset += dt.itemsize * n
                    uniform = True
            if not uniform:
                offset, li[p["name"]] = _ply_binary_lists(raw, offset, n, ct, vt, el, src)
        else:
            rows = {p["name"]: (np.zeros(n, np.float64) if p["kind"] == "scalar" else [])
                    for p in props}
            for i in range(n):
                for p in props:
                    if p["kind"] == "scalar":
                        dt = np.dtype(endian + _PLY_TYPES[p["type"]])
                        if offset + dt.itemsize > total:
                            raise ValueError("%s: PLY element %r ends after %d of %d rows"
                                             % (src, el["name"], i, n))
                        rows[p["name"]][i] = float(np.frombuffer(raw, dt, count=1,
                                                                 offset=offset)[0])
                        offset += dt.itemsize
                    else:
                        ct = np.dtype(endian + _PLY_TYPES[p["count_type"]])
                        vt = np.dtype(endian + _PLY_TYPES[p["type"]])
                        if offset + ct.itemsize > total:
                            raise ValueError("%s: PLY element %r ends after %d of %d rows"
                                             % (src, el["name"], i, n))
                        c = int(np.frombuffer(raw, ct, count=1, offset=offset)[0])
                        offset += ct.itemsize
                        if c < 0 or offset + c * vt.itemsize > total:
                            raise ValueError("%s: PLY list of length %d at row %d runs past the "
                                             "end of the file" % (src, c, i))
                        rows[p["name"]].append(np.frombuffer(raw, vt, count=c,
                                                             offset=offset).astype(np.int64))
                        offset += c * vt.itemsize
            for p in props:
                (sc if p["kind"] == "scalar" else li)[p["name"]] = rows[p["name"]]
        out[el["name"]] = {"scalars": sc, "lists": li, "count": n,
                           "types": {p["name"]: p["type"] for p in props}}
    return out


def _ply_binary_lists(raw: bytes, offset: int, n: int, ct: str, vt: str, el, src: str):
    """Ragged binary list element (faces of mixed degree) — sequential fallback."""
    cdt, vdt, total, out = np.dtype(ct), np.dtype(vt), len(raw), []
    for i in range(n):
        if offset + cdt.itemsize > total:
            raise ValueError("%s: PLY element %r ends after %d of %d rows"
                             % (src, el["name"], i, n))
        c = int(np.frombuffer(raw, cdt, count=1, offset=offset)[0])
        offset += cdt.itemsize
        if c < 0 or offset + c * vdt.itemsize > total:
            raise ValueError("%s: PLY list of length %d at row %d runs past the end of the file"
                             % (src, c, i))
        out.append(np.frombuffer(raw, vdt, count=c, offset=offset).astype(np.int64))
        offset += c * vdt.itemsize
    return offset, out


def _ply_data(raw: bytes, src: str) -> dict:
    fmt, elements, offset = _ply_header(raw, src)
    if fmt == "ascii":
        return _ply_ascii(elements, raw[offset:].decode("utf-8", "replace"), src)
    endian = "<" if fmt == "binary_little_endian" else ">"
    return _ply_binary(elements, raw, offset, endian, src)


def _ply_xyz(el, src: str) -> np.ndarray:
    sc = el["scalars"]
    missing = [c for c in ("x", "y", "z") if c not in sc]
    if missing:
        raise ValueError("%s: PLY vertex element lacks propert%s %s"
                         % (src, "y" if len(missing) == 1 else "ies", ", ".join(missing)))
    return np.column_stack([sc["x"], sc["y"], sc["z"]]).astype(np.float64)


def _ply_rgb(el):
    """RGB in [0, 1] from whichever colour naming the file uses, else None.
    Integer channels are divided by their dtype maximum; float channels are
    assumed already normalised and clipped."""
    sc, types = el["scalars"], el["types"]
    for trio in (("red", "green", "blue"), ("r", "g", "b"),
                 ("diffuse_red", "diffuse_green", "diffuse_blue")):
        if all(c in sc for c in trio):
            C = np.column_stack([sc[c] for c in trio]).astype(np.float64)
            dt = np.dtype(_PLY_TYPES.get(types.get(trio[0], "uchar"), "u1"))
            if dt.kind in "iu":
                C = C / float(np.iinfo(dt).max)
            return np.clip(C, 0.0, 1.0)
    return None


def _read_ply_mesh(raw: bytes, src: str):
    data = _ply_data(raw, src)
    if "vertex" not in data:
        raise ValueError("%s: PLY has no 'vertex' element" % src)
    V = _ply_xyz(data["vertex"], src)
    faces = np.zeros((0, 3), np.int64)
    face = data.get("face")
    if face is not None and face["count"]:
        for key in ("vertex_indices", "vertex_index", "vertex-indices"):
            if key in face["lists"]:
                faces = face["lists"][key]
                break
        else:
            if face["lists"]:
                faces = next(iter(face["lists"].values()))
            else:
                raise ValueError("%s: PLY 'face' element has no vertex-index list property" % src)
    return _finish_mesh(V, faces, src)


def _read_ply_points(raw: bytes, src: str):
    data = _ply_data(raw, src)
    if "vertex" not in data:
        raise ValueError("%s: PLY has no 'vertex' element" % src)
    return _ply_xyz(data["vertex"], src), _ply_rgb(data["vertex"])


# ---- XYZ / PCD (points only) ------------------------------------------------ #
def _read_xyz(raw: bytes, src: str):
    """Plain text ``x y z [r g b]``, one point per line (``#`` starts a comment)."""
    rows = []
    for ln in _text(raw).splitlines():
        s = ln.split("#")[0].strip()
        if not s:
            continue
        rows.append(s.replace(",", " ").split())
    if not rows:
        raise ValueError("%s: XYZ file has no data lines" % src)
    _check_count(len(rows), "points", src)
    w = len(rows[0])
    if w < 3:
        raise ValueError("%s: XYZ needs at least 3 columns (x y z), first line has %d"
                         % (src, w))
    bad = next((i for i, r in enumerate(rows) if len(r) != w), None)
    if bad is not None:
        raise ValueError("%s: XYZ line %d has %d columns, expected %d — the file is not a "
                         "uniform 'x y z [r g b]' table" % (src, bad, len(rows[bad]), w))
    A = _floats(rows, "XYZ row", src).reshape(len(rows), w)
    C = None
    if w >= 6:
        C = A[:, 3:6]
        if np.isfinite(C).all() and C.max() > 1.0:       # 0..255 convention
            C = C / 255.0
        C = np.clip(C, 0.0, 1.0)
    return A[:, :3], C


def _read_pcd(raw: bytes, src: str):
    """ASCII PCD (Point Cloud Library file format). Binary/binary_compressed PCD
    is refused — it belongs with the optional-extra formats."""
    lines = _text(raw).splitlines()
    fields = types = counts = None
    npts, width, height, data, di = None, None, None, None, None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        key = parts[0].upper()
        if key == "FIELDS":
            fields = parts[1:]
        elif key == "TYPE":
            types = parts[1:]
        elif key == "COUNT":
            counts = parts[1:]
        elif key == "POINTS":
            npts = _one_int(parts[1], "PCD POINTS", src) if len(parts) > 1 else None
        elif key == "WIDTH":
            width = _one_int(parts[1], "PCD WIDTH", src) if len(parts) > 1 else None
        elif key == "HEIGHT":
            height = _one_int(parts[1], "PCD HEIGHT", src) if len(parts) > 1 else None
        elif key == "DATA":
            data = parts[1].lower() if len(parts) > 1 else ""
            di = i + 1
            break
    if data is None:
        raise ValueError("%s: no PCD 'DATA' line — not a PCD file?" % src)
    if data != "ascii":
        raise ValueError("%s: PCD DATA %r is not supported — only 'ascii' (binary PCD needs "
                         "an optional extra)" % (src, data))
    if not fields:
        raise ValueError("%s: PCD header has no 'FIELDS' line" % src)
    if counts is not None and any(c != "1" for c in counts):
        raise ValueError("%s: PCD COUNT != 1 per field is not supported (got %r)"
                         % (src, " ".join(counts)))
    if npts is None:
        npts = (width * height) if (width is not None and height is not None) else None
    rows = []
    for ln in lines[di:]:
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        rows.append(s.split())
    if npts is None:
        npts = len(rows)
    _check_count(npts, "points", src)
    if len(rows) < npts:
        raise ValueError("%s: PCD declares %d points but only %d data rows follow"
                         % (src, npts, len(rows)))
    rows = rows[:npts]
    nf = len(fields)
    bad = next((i for i, r in enumerate(rows) if len(r) != nf), None)
    if bad is not None:
        raise ValueError("%s: PCD row %d has %d values, expected %d (one per FIELD)"
                         % (src, bad, len(rows[bad]), nf))
    low = [f.lower() for f in fields]
    for axis in ("x", "y", "z"):
        if axis not in low:
            raise ValueError("%s: PCD FIELDS %r has no %r field" % (src, " ".join(fields), axis))
    A = _floats(rows, "PCD row", src).reshape(npts, nf) if npts else np.zeros((0, nf))
    P = np.column_stack([A[:, low.index(a)] for a in ("x", "y", "z")])
    C = None
    for trio in (("r", "g", "b"), ("red", "green", "blue")):
        if all(c in low for c in trio):
            C = np.clip(np.column_stack([A[:, low.index(c)] for c in trio]) / 255.0, 0.0, 1.0)
            break
    if C is None and ("rgb" in low or "rgba" in low):
        j = low.index("rgb" if "rgb" in low else "rgba")
        col = A[:, j]
        kind = (types[j].upper() if types is not None and j < len(types) else "F")
        packed = (col.astype(np.float32).view(np.uint32) if kind == "F"
                  else col.astype(np.int64).astype(np.uint32))
        C = np.clip(np.column_stack([(packed >> 16) & 255, (packed >> 8) & 255,
                                     packed & 255]).astype(np.float64) / 255.0, 0.0, 1.0)
    return P, C


# ---- public readers --------------------------------------------------------- #
def read_mesh(path: str):
    """Read a triangle mesh -> ``(V, F)``: vertices (nv, 3) float64 and triangle
    indices (nf, 3) int64.

    The format comes from the extension (``.obj``, ``.stl``, ``.ply``, ``.off``);
    STL and PLY additionally sniff **binary vs ASCII** from the header/content and
    honour the declared endianness. Polygons with more than 3 corners are
    fan-triangulated. STL has no vertex sharing, so its per-triangle corners are
    welded on exact coordinate equality (8 vertices for a cube, not 36).

    Raises ``ValueError`` on a malformed header, a declared count that does not
    fit the file, an out-of-range face index, or a NaN/Inf coordinate — never a
    partially parsed mesh.
    """
    src = str(path)
    ext = _ext(src)
    if ext not in MESH_FORMATS:
        raise ValueError("unsupported mesh format %r for %s — read_mesh handles %s"
                         % (ext, src, ", ".join(MESH_FORMATS)))
    raw = _read_bytes(src)
    if ext == ".obj":
        return _read_obj(raw, src)
    if ext == ".off":
        return _read_off(raw, src)
    if ext == ".stl":
        return _read_stl(raw, src)
    return _read_ply_mesh(raw, src)


def read_points(path: str, with_colors: bool = False):
    """Read a point cloud -> ``P`` (n, 3) float64, or ``(P, C)`` when
    *with_colors* (``C`` is (n, 3) in [0, 1], or ``None`` when the file carries
    no colours).

    Supported: ``.ply`` (the ``vertex`` element, with ``red/green/blue``,
    ``r/g/b`` or ``diffuse_*`` colours), ``.xyz`` / ``.txt`` / ``.pts`` / ``.asc``
    (whitespace ``x y z [r g b]``; a colour column whose maximum exceeds 1 is read
    as 0..255), ``.obj`` (``v`` records only — faces ignored), ASCII ``.pcd``
    (fields ``x y z`` plus ``r g b`` or a packed ``rgb``), and ``.stl`` / ``.off``
    via their mesh vertices.
    """
    src = str(path)
    ext = _ext(src)
    if ext not in POINT_FORMATS:
        raise ValueError("unsupported point format %r for %s — read_points handles %s"
                         % (ext, src, ", ".join(POINT_FORMATS)))
    raw = _read_bytes(src)
    if ext == ".ply":
        P, C = _read_ply_points(raw, src)
    elif ext == ".pcd":
        P, C = _read_pcd(raw, src)
    elif ext == ".obj":
        P, C = _read_obj_vertices(raw, src)
    elif ext == ".stl":
        P, C = _read_stl(raw, src)[0], None
    elif ext == ".off":
        P, C = _read_off(raw, src)[0], None
    else:
        P, C = _read_xyz(raw, src)
    P = _finite_points(P, "points", src)
    if C is not None:
        C = np.asarray(C, np.float64)
        if C.shape != P.shape:
            raise ValueError("%s: %d colours for %d points" % (src, C.shape[0], P.shape[0]))
        if not np.isfinite(C).all():
            raise ValueError("%s: colours contain non-finite values" % src)
    return (P, C) if with_colors else P


# ---- writer ----------------------------------------------------------------- #
def write_mesh(path: str, vertices, faces) -> None:
    """Write a triangle mesh to ``.obj`` or ``.ply`` (ASCII).

    Coordinates are written with 17 significant digits, and the PLY header
    declares ``double`` vertex properties, so ``read_mesh(write_mesh(...))``
    round-trips float64 exactly. Geometry only — no normals, materials or colours.
    """
    src = str(path)
    ext = _ext(src)
    if ext not in (".obj", ".ply"):
        raise ValueError("unsupported write format %r for %s — write_mesh handles .obj, .ply"
                         % (ext, src))
    V = _finite_points(vertices, "vertices", src)
    F = np.asarray(faces, np.int64)
    if F.size == 0:
        F = np.zeros((0, 3), np.int64)
    if F.ndim != 2 or F.shape[1] != 3:
        raise ValueError("%s: faces must be (M, 3) triangles, got %r" % (src, (F.shape,)))
    if F.size and (int(F.min()) < 0 or int(F.max()) >= V.shape[0]):
        raise ValueError("%s: face index out of range for %d vertices" % (src, V.shape[0]))
    if ext == ".obj":
        out = ["# Wavefront OBJ written by fullseye.mesh", "o mesh"]
        out += ["v %.17g %.17g %.17g" % (x, y, z) for x, y, z in V]
        out += ["f %d %d %d" % (i + 1, j + 1, k + 1) for i, j, k in F]     # OBJ is 1-based
    else:
        out = ["ply", "format ascii 1.0", "comment written by fullseye.mesh",
               "element vertex %d" % V.shape[0],
               "property double x", "property double y", "property double z",
               "element face %d" % F.shape[0],
               "property list uchar int vertex_indices", "end_header"]
        out += ["%.17g %.17g %.17g" % (x, y, z) for x, y, z in V]
        out += ["3 %d %d %d" % (i, j, k) for i, j, k in F]
    with open(src, "w", encoding="ascii") as f:
        f.write("\n".join(out) + "\n")


# ---- geometry helpers -------------------------------------------------------- #
def _tri_corners(V, F, src: str = "mesh"):
    """(V, F) -> the three corner arrays A, B, C, each (nf, 3), after validation."""
    V = _finite_points(V, "vertices", src)
    F = np.asarray(F, np.int64)
    if F.size == 0:
        raise ValueError("mesh has no faces")
    if F.ndim != 2 or F.shape[1] != 3:
        raise ValueError("faces must be (M, 3) triangles, got %r" % (F.shape,))
    if int(F.min()) < 0 or int(F.max()) >= V.shape[0]:
        raise ValueError("face index out of range for %d vertices" % V.shape[0])
    return V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]


def sample_surface(V, F, n: int, seed: int = 0) -> np.ndarray:
    """Uniformly sample *n* points over the mesh **surface** -> (n, 3) float64.

    Area-weighted: a triangle is drawn with probability proportional to its area,
    then a point is drawn uniformly inside it with the reflected-barycentric trick
    (``u+v>1 -> (1-u, 1-v)``), so density is uniform per unit area rather than per
    triangle. Deterministic for a given *seed* (``np.random.default_rng(seed)``).

    This is the bridge from an imported CAD/scan mesh to the (N, 3) cloud
    :mod:`pointcloud` and :mod:`registration` work on.
    """
    A, B, C = _tri_corners(V, F)
    n = int(n)
    if n < 0:
        raise ValueError("n must be >= 0, got %r" % (n,))
    if n == 0:
        return np.zeros((0, 3), np.float64)
    area = 0.5 * np.linalg.norm(np.cross(B - A, C - A), axis=1)
    total = float(area.sum())
    if not np.isfinite(total) or total <= 0.0:
        raise ValueError("mesh has zero total surface area — nothing to sample")
    rng = np.random.default_rng(seed)
    cum = np.cumsum(area) / total
    cum[-1] = 1.0
    idx = np.searchsorted(cum, rng.random(n), side="right")
    idx = np.clip(idx, 0, area.shape[0] - 1)
    u, v = rng.random(n), rng.random(n)
    fold = (u + v) > 1.0
    u[fold], v[fold] = 1.0 - u[fold], 1.0 - v[fold]
    a, ab, ac = A[idx], B[idx] - A[idx], C[idx] - A[idx]
    return a + u[:, None] * ab + v[:, None] * ac


def mesh_to_points(V, F, n: int, seed: int = 0) -> np.ndarray:
    """Alias of :func:`sample_surface` — mesh in, point cloud out."""
    return sample_surface(V, F, n, seed=seed)


def voxelize(V, F, pitch: float):
    """Rasterise the mesh onto a regular grid -> ``(occ, origin)``.

    *occ* is a bool (nx, ny, nz) array (the ``volume`` sort, indexed x, y, z) and
    *origin* is the float64 (3,) world coordinate of the **corner** of cell
    ``occ[0, 0, 0]`` — i.e. that cell covers ``[origin, origin + pitch)`` on each
    axis, so a world point maps to ``floor((p - origin) / pitch)``. *origin* is
    the mesh's bounding-box minimum.

    This is **surface** voxelization: every cell a triangle passes through is
    marked and the interior is left empty (a hollow shell). Solid/interior fill
    needs an inside-outside test, which this module does not do — do not read an
    occupied cell as "material here", only as "surface here".

    Triangles are covered by a barycentric lattice with spacing <= ``pitch/2``,
    which marks every cell the triangle meets for the meshes tested; it is a
    dense-sampling rasteriser, not an exact triangle-box intersection test, so a
    sliver triangle crossing a cell corner can in principle be missed.
    """
    A, B, C = _tri_corners(V, F)
    pitch = float(pitch)
    if not np.isfinite(pitch) or pitch <= 0.0:
        raise ValueError("pitch must be > 0, got %r" % (pitch,))
    lo = np.minimum(np.minimum(A.min(0), B.min(0)), C.min(0))
    hi = np.maximum(np.maximum(A.max(0), B.max(0)), C.max(0))
    span = np.maximum(np.floor((hi - lo) / pitch) + 1.0, 1.0)      # float: no int overflow
    cells = float(np.prod(span))
    if not np.isfinite(cells) or cells > MAX_VOXELS:
        raise ValueError("pitch %g gives a %s grid (%.3g cells), over the %d cap "
                         "(mesh.MAX_VOXELS) — use a larger pitch"
                         % (pitch, tuple(span.tolist()), cells, MAX_VOXELS))
    shape = span.astype(np.int64)
    edge = np.maximum(np.maximum(np.linalg.norm(B - A, axis=1),
                                 np.linalg.norm(C - A, axis=1)),
                      np.linalg.norm(C - B, axis=1))
    sub = np.clip(np.ceil(edge / (0.5 * pitch)), 1.0, _MAX_SUBDIV).astype(np.int64)
    est = float(np.sum((sub + 1.0) * (sub + 2.0) / 2.0))
    if est > _MAX_VOXEL_SAMPLES:
        raise ValueError("pitch %g needs ~%d surface samples, over the %d cap — use a larger "
                         "pitch or a coarser mesh" % (pitch, int(est), _MAX_VOXEL_SAMPLES))
    occ = np.zeros(tuple(int(s) for s in shape), bool)
    hi_idx = shape - 1
    for nsub in np.unique(sub):
        sel = np.flatnonzero(sub == nsub)
        gi, gj = np.meshgrid(np.arange(nsub + 1), np.arange(nsub + 1), indexing="ij")
        keep = (gi + gj) <= nsub
        u = (gi[keep] / float(nsub))[None, :, None]
        v = (gj[keep] / float(nsub))[None, :, None]
        k = int(u.shape[1])
        step = max(1, _CHUNK // max(k, 1))
        for s0 in range(0, sel.shape[0], step):
            t = sel[s0:s0 + step]
            a, ab, ac = A[t][:, None, :], (B - A)[t][:, None, :], (C - A)[t][:, None, :]
            pts = (a + u * ab + v * ac).reshape(-1, 3)
            ijk = np.floor((pts - lo) / pitch).astype(np.int64)
            np.clip(ijk, 0, hi_idx, out=ijk)
            occ[ijk[:, 0], ijk[:, 1], ijk[:, 2]] = True
    return occ, lo.astype(np.float64)


def bounds(V):
    """Axis-aligned bounding box -> ``(min, max)``, each float64 (3,)."""
    P = _finite_points(V, "vertices", "bounds")
    if P.shape[0] == 0:
        raise ValueError("bounds needs at least one vertex")
    return P.min(axis=0), P.max(axis=0)


def recenter(V) -> np.ndarray:
    """Translate so the vertex centroid sits at the origin. Returns a new array."""
    P = _finite_points(V, "vertices", "recenter")
    if P.shape[0] == 0:
        return P
    return P - P.mean(axis=0)


def normalize_scale(V, size: float = 1.0) -> np.ndarray:
    """Scale about the origin so the largest bounding-box extent equals *size*.

    Pure scaling — combine with :func:`recenter` for the usual "centred unit
    model" normalisation (``normalize_scale(recenter(V))``). A degenerate mesh
    (all vertices coincident) has no extent to normalise and raises ``ValueError``.
    """
    P = _finite_points(V, "vertices", "normalize_scale")
    size = float(size)
    if size <= 0.0:
        raise ValueError("size must be > 0, got %r" % (size,))
    if P.shape[0] == 0:
        return P
    extent = float((P.max(axis=0) - P.min(axis=0)).max())
    if extent <= 0.0:
        raise ValueError("degenerate mesh: bounding-box extent is 0, nothing to scale")
    return P * (size / extent)
