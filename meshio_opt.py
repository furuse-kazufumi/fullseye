"""Heavier / modern 3-D object formats, imported through *optional* libraries.

The numpy-native readers in :mod:`mesh` (OBJ / STL / PLY / OFF) cover the formats
whose specs are simple enough to parse with nothing but the standard library and
numpy. This module extends "the more importable object formats the better" to the
formats that genuinely need a parser — glTF/GLB, LAS/LAZ and binary PCD — so an
evis / onocollo / hillco scene, a LiDAR scan or a PCL capture can still become the
plain numpy arrays the rest of the perception stack speaks:

    import fullseye as fs
    V, F     = fs.read_gltf_merged("scene.glb")   # (nv,3) float64, (nf,3) int64
    P, attrs = fs.read_las("scan.laz")            # (N,3) metric points + per-point attrs
    P, attrs = fs.read_pcd("capture.pcd")         # ascii / binary / binary_compressed

Unlike :mod:`mesh`, these readers depend on third-party libraries, so they are an
**optional extra**: each backend is *lazy-imported inside the reader*, and a
missing backend raises ``RuntimeError`` naming the exact ``pip install`` line. The
numpy core never imports them — ``import meshio_opt`` costs nothing but numpy.

Backends (all permissively licensed):

  ``.gltf`` / ``.glb``   glTF 2.0 via **pygltflib** (MIT). The Khronos glTF 2.0
                         spec: a scene is a graph of nodes, each with a 4x4 local
                         transform, referencing meshes made of primitives.
  ``.las`` / ``.laz``    LAS / LAZ via **laspy** + the **lazrs** backend (BSD-2 /
                         MIT). ASPRS *LAS Specification*: quantised integer XYZ
                         plus a header scale/offset, one of several point formats.
  ``.pcd``               PCD via **pypcd4** (BSD-3). The PCL *Point Cloud Data*
                         file format, incl. the ``binary_compressed`` layout that
                         :mod:`mesh` cannot read.

Honest limitations — nothing here claims more than its round-trip test proves:

  * **glTF returns geometry only.** POSITION accessors and triangle topology are
    decoded; materials, textures, normals, tangents, vertex colours, animations,
    skins, morph targets and cameras are **not** read. Only the mesh geometry and
    the node world transforms come out.
  * **Primitive modes.** ``TRIANGLES`` (the default) is read directly;
    ``TRIANGLE_STRIP`` and ``TRIANGLE_FAN`` are triangulated. ``POINTS`` /
    ``LINES`` / ``LINE_LOOP`` / ``LINE_STRIP`` primitives carry no faces and are
    **skipped** (they contribute no entry to the returned scene).
  * **LAS returns raw metric points** in the file's own coordinate system: the
    header scale and offset are applied (``coord = X*scale + offset``) but **no CRS
    reprojection** is done — a projected file stays in its projection.
  * **RGB scaling.** LAS colour is 16-bit per the ASPRS spec, but many tools write
    8-bit values into the 16-bit field; the heuristic here is *per channel*: a
    channel whose maximum exceeds 255 is divided by 65535, otherwise by 255. PCD
    ``rgb`` is unpacked by PCL's convention and divided by 255. Both are clipped to
    ``[0, 1]``. A genuinely dark 16-bit LAS whose every channel is <= 255 would be
    mis-scaled — document, don't guess silently.

Fail-closed on untrusted input (a hostile file must not exhaust memory): the file
size is capped (``MAX_FILE_BYTES``) and declared vertex / face / point counts are
checked against ``MAX_VERTICES`` / ``MAX_FACES`` / ``MAX_POINTS`` **before** any
large array is allocated; buffer byte ranges are bounds-checked against the data
actually present; parsed coordinates must be finite and every face index must be
in range. A missing file raises ``FileNotFoundError``; a broken or unsupported
file raises ``ValueError`` naming the path.

Public specs: glTF 2.0 (Khronos Group); LAS (ASPRS LAS Specification); PCD (PCL,
Point Cloud Data file format).
"""
from __future__ import annotations

import os

import numpy as np

__all__ = [
    "read_gltf", "read_gltf_merged", "read_las", "read_pcd",
    "formats_available", "OPT_FORMATS",
    "MAX_FILE_BYTES", "MAX_VERTICES", "MAX_FACES", "MAX_POINTS",
]

#: Refuse files larger than this (untrusted input / accidental DoS guard).
MAX_FILE_BYTES = 1 << 29          # 512 MiB
#: Refuse a declared vertex count (per accessor) larger than this.
MAX_VERTICES = 50_000_000
#: Refuse a declared / produced triangle count larger than this.
MAX_FACES = 100_000_000
#: Refuse a declared point count (LAS/PCD) larger than this.
MAX_POINTS = 200_000_000

# glTF component types (little-endian by spec) -> numpy scalar dtype.
_GLTF_COMPONENT = {
    5120: "<i1", 5121: "<u1", 5122: "<i2", 5123: "<u2",
    5125: "<u4", 5126: "<f4",
}
# glTF accessor element types -> component count.
_GLTF_NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4,
               "MAT2": 4, "MAT3": 9, "MAT4": 16}
# Primitive modes.
_MODE_TRIANGLES, _MODE_TRISTRIP, _MODE_TRIFAN = 4, 5, 6


# ---- shared guards --------------------------------------------------------- #
def _ext(path: str) -> str:
    return os.path.splitext(str(path))[1].lower()


def _stat_or_raise(path: str) -> int:
    """Check the file exists and is within the size cap; return its size."""
    p = str(path)
    if not os.path.isfile(p):
        raise FileNotFoundError(p)
    size = os.path.getsize(p)
    if size == 0:
        raise ValueError("%s is empty" % p)
    if size > MAX_FILE_BYTES:
        raise ValueError("%s is %d bytes, over the %d-byte cap (meshio_opt.MAX_FILE_BYTES)"
                         % (p, size, MAX_FILE_BYTES))
    return size


def _need(module: str, func: str, pip: str):
    """Lazy-import an optional backend or raise a clear install message."""
    try:
        return __import__(module)
    except ImportError as e:
        raise RuntimeError("%s needs %s: pip install %s" % (func, module, pip)) from e


def _can_import(module: str) -> bool:
    try:
        __import__(module)
        return True
    except Exception:
        return False


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


def _check_count(n: int, what: str, cap: int, const: str, src: str) -> int:
    if n < 0:
        raise ValueError("%s: negative %s count (%d)" % (src, what, n))
    if n > cap:
        raise ValueError("%s: declares %d %s, over the %d cap (meshio_opt.%s)"
                         % (src, n, what, cap, const))
    return n


# =========================================================================== #
# glTF 2.0 / GLB                                                              #
# =========================================================================== #
def _quat_to_mat(q) -> np.ndarray:
    """Unit quaternion [x, y, z, w] (glTF order) -> 3x3 rotation matrix."""
    x, y, z, w = (float(v) for v in q)
    n = x * x + y * y + z * z + w * w
    if n <= 0.0:
        return np.eye(3)
    s = 2.0 / n
    xx, yy, zz = x * x * s, y * y * s, z * z * s
    xy, xz, yz = x * y * s, x * z * s, y * z * s
    wx, wy, wz = w * x * s, w * y * s, w * z * s
    return np.array([[1.0 - (yy + zz), xy - wz, xz + wy],
                     [xy + wz, 1.0 - (xx + zz), yz - wx],
                     [xz - wy, yz + wx, 1.0 - (xx + yy)]], np.float64)


def _node_local_matrix(node) -> np.ndarray:
    """A glTF node's local transform -> 4x4 float64 (column vectors on the right).

    glTF stores either an explicit column-major ``matrix`` or a
    translation/rotation/scale triple; when both are absent the transform is
    identity. TRS composes as T @ R @ S per the spec."""
    if getattr(node, "matrix", None):
        return np.asarray(node.matrix, np.float64).reshape(4, 4).T   # column-major -> row-major
    M = np.eye(4)
    if getattr(node, "scale", None):
        M = M @ np.diag(list(node.scale) + [1.0])
    if getattr(node, "rotation", None):
        R = np.eye(4)
        R[:3, :3] = _quat_to_mat(node.rotation)
        M = R @ M
    if getattr(node, "translation", None):
        T = np.eye(4)
        T[:3, 3] = node.translation
        M = T @ M
    return M


def _gltf_buffers(gltf, gltf_dir: str, src: str) -> list:
    """Resolve every glTF buffer to raw bytes (GLB blob / data URI / external)."""
    import base64
    from urllib.parse import unquote

    out = []
    for i, buf in enumerate(getattr(gltf, "buffers", None) or []):
        uri = getattr(buf, "uri", None)
        if not uri:
            data = gltf.binary_blob()
            if data is None:
                raise ValueError("%s: buffer %d has no URI and the file carries no binary "
                                 "blob (GLB chunk)" % (src, i))
            data = bytes(data)
        elif uri.startswith("data:"):
            comma = uri.find(",")
            if comma < 0:
                raise ValueError("%s: buffer %d has a malformed data URI" % (src, i))
            try:
                data = base64.b64decode(uri[comma + 1:])
            except Exception as e:
                raise ValueError("%s: buffer %d data URI is not valid base64: %s" % (src, i, e))
        else:
            ext = os.path.normpath(os.path.join(gltf_dir, unquote(uri)))
            if not os.path.isfile(ext):
                raise ValueError("%s: external buffer %r not found" % (src, uri))
            if os.path.getsize(ext) > MAX_FILE_BYTES:
                raise ValueError("%s: external buffer %r over the %d-byte cap"
                                 % (src, uri, MAX_FILE_BYTES))
            with open(ext, "rb") as f:
                data = f.read()
        out.append(data)
    return out


def _read_accessor(gltf, buffers, ai: int, src: str) -> np.ndarray:
    """Decode accessor *ai* -> (count, ncomp) array (honours interleaving/stride).

    Sparse accessors are not supported (they carry no dense geometry in the meshes
    this reader targets); an accessor without a bufferView is rejected."""
    accessors = getattr(gltf, "accessors", None) or []
    if ai < 0 or ai >= len(accessors):
        raise ValueError("%s: accessor index %d out of range" % (src, ai))
    acc = accessors[ai]
    if getattr(acc, "sparse", None) is not None:
        raise ValueError("%s: sparse accessors are not supported" % src)
    bvi = getattr(acc, "bufferView", None)
    if bvi is None:
        raise ValueError("%s: accessor %d has no bufferView" % (src, ai))
    ctype = getattr(acc, "componentType", None)
    if ctype not in _GLTF_COMPONENT:
        raise ValueError("%s: accessor %d unknown componentType %r" % (src, ai, ctype))
    atype = getattr(acc, "type", None)
    if atype not in _GLTF_NCOMP:
        raise ValueError("%s: accessor %d unknown type %r" % (src, ai, atype))
    comp = np.dtype(_GLTF_COMPONENT[ctype])
    ncomp = _GLTF_NCOMP[atype]
    count = int(getattr(acc, "count", 0) or 0)
    _check_count(count, "accessor elements", MAX_VERTICES, "MAX_VERTICES", src)

    bviews = getattr(gltf, "bufferViews", None) or []
    if bvi < 0 or bvi >= len(bviews):
        raise ValueError("%s: bufferView index %d out of range" % (src, bvi))
    bv = bviews[bvi]
    bi = int(getattr(bv, "buffer", -1))
    if bi < 0 or bi >= len(buffers):
        raise ValueError("%s: bufferView %d references missing buffer %d" % (src, bvi, bi))
    data = buffers[bi]
    elem = comp.itemsize * ncomp
    stride = int(getattr(bv, "byteStride", None) or 0) or elem
    start = int(getattr(bv, "byteOffset", None) or 0) + int(getattr(acc, "byteOffset", None) or 0)
    if count == 0:
        return np.zeros((0, ncomp), comp)
    span = start + stride * (count - 1) + elem
    if start < 0 or span > len(data):
        raise ValueError("%s: accessor %d needs bytes [%d, %d) but its buffer holds %d"
                         % (src, ai, start, span, len(data)))
    raw = np.frombuffer(data, np.uint8, count=stride * (count - 1) + elem, offset=start)
    view = np.lib.stride_tricks.as_strided(raw, shape=(count, elem),
                                           strides=(stride, 1))
    return np.ascontiguousarray(view).view(comp).reshape(count, ncomp)


def _triangulate_indices(idx: np.ndarray, mode, src: str) -> np.ndarray:
    """Index stream + primitive mode -> (nf, 3) int64 triangles.

    ``None``/``TRIANGLES`` groups by threes; strips and fans are triangulated;
    non-triangle modes return an empty face array (the caller skips the primitive).
    """
    idx = np.asarray(idx, np.int64).ravel()
    m = _MODE_TRIANGLES if mode is None else int(mode)
    if m == _MODE_TRIANGLES:
        if idx.size % 3:
            raise ValueError("%s: TRIANGLES primitive has %d indices, not a multiple of 3"
                             % (src, idx.size))
        return idx.reshape(-1, 3)
    if m == _MODE_TRISTRIP:
        if idx.size < 3:
            return np.zeros((0, 3), np.int64)
        a, b, c = idx[:-2], idx[1:-1], idx[2:]
        tris = np.stack([a, b, c], axis=1)
        tris[1::2] = tris[1::2][:, [1, 0, 2]]          # flip winding on odd triangles
        return tris.astype(np.int64)
    if m == _MODE_TRIFAN:
        if idx.size < 3:
            return np.zeros((0, 3), np.int64)
        return np.stack([np.full(idx.size - 2, idx[0]), idx[1:-1], idx[2:]],
                        axis=1).astype(np.int64)
    return np.zeros((0, 3), np.int64)                  # POINTS / LINES* -> no faces


def _iter_mesh_nodes(gltf, src: str):
    """Yield ``(node, mesh_index, world_matrix)`` for every mesh-bearing node,
    composing parent transforms along the scene graph (depth-first)."""
    nodes = getattr(gltf, "nodes", None) or []
    if not nodes:
        return
    scenes = getattr(gltf, "scenes", None) or []
    scene_i = getattr(gltf, "scene", None)
    if scenes and scene_i is not None and 0 <= scene_i < len(scenes):
        roots = list(getattr(scenes[scene_i], "nodes", None) or [])
    elif scenes:
        roots = list(getattr(scenes[0], "nodes", None) or [])
    else:
        child = set()
        for nd in nodes:
            for c in (getattr(nd, "children", None) or []):
                child.add(int(c))
        roots = [i for i in range(len(nodes)) if i not in child]
    stack = [(int(r), np.eye(4)) for r in reversed(roots)]
    visited = set()
    while stack:
        ni, parent = stack.pop()
        if ni < 0 or ni >= len(nodes) or ni in visited:
            continue
        visited.add(ni)                                 # guard against cyclic graphs
        node = nodes[ni]
        world = parent @ _node_local_matrix(node)
        mi = getattr(node, "mesh", None)
        if mi is not None:
            yield node, int(mi), world
        for c in (getattr(node, "children", None) or []):
            stack.append((int(c), world))


def read_gltf(path: str) -> list:
    """Read a glTF 2.0 / GLB file -> a **scene**: a list of mesh-primitive dicts.

    Each entry is ``{"name": str, "V": (nv,3) float64, "F": (nf,3) int64,
    "transform": (4,4) float64}``, one per triangle-bearing primitive. ``V`` and
    ``F`` are the primitive's *local* geometry (POSITION accessor + triangulated
    indices); ``transform`` is the node's **world** matrix (parent transforms
    composed), with column vectors on the right, so a vertex is placed in the
    scene by ``transform @ [x, y, z, 1]``. Bake it with :func:`read_gltf_merged`.

    Geometry only: materials, textures, normals, vertex colours, animations, skins
    and cameras are not read (see the module docstring). ``TRIANGLES`` primitives
    are read directly, ``TRIANGLE_STRIP`` / ``TRIANGLE_FAN`` are triangulated, and
    ``POINTS`` / ``LINES`` primitives (no faces) are skipped.

    Reference: glTF 2.0 specification (Khronos Group).

    Raises ``FileNotFoundError`` if the path is missing, ``RuntimeError`` if
    pygltflib is not installed, and ``ValueError`` (naming the path) on a malformed
    file, a declared count over ``MAX_VERTICES`` / ``MAX_FACES``, a buffer range
    that runs past the data, or a non-finite / out-of-range vertex or index.
    """
    src = str(path)
    _stat_or_raise(src)
    pygltflib = _need("pygltflib", "read_gltf", "pygltflib")
    try:
        gltf = pygltflib.GLTF2().load(src)
    except (ValueError, FileNotFoundError, RuntimeError):
        raise
    except Exception as e:
        raise ValueError("%s: not a valid glTF/GLB file (%s: %s)"
                         % (src, type(e).__name__, e)) from None
    if gltf is None:
        raise ValueError("%s: could not parse as glTF/GLB" % src)

    buffers = _gltf_buffers(gltf, os.path.dirname(os.path.abspath(src)), src)
    meshes = getattr(gltf, "meshes", None) or []
    scene = []
    for node, mi, world in _iter_mesh_nodes(gltf, src):
        if mi < 0 or mi >= len(meshes):
            raise ValueError("%s: node references missing mesh %d" % (src, mi))
        mesh_obj = meshes[mi]
        base = getattr(node, "name", None) or getattr(mesh_obj, "name", None) or ("mesh%d" % mi)
        for pi, prim in enumerate(getattr(mesh_obj, "primitives", None) or []):
            attrs = getattr(prim, "attributes", None)
            pos_ai = getattr(attrs, "POSITION", None) if attrs is not None else None
            if pos_ai is None:
                continue                                # nothing to place (e.g. pure morph target)
            V = _finite_points(_read_accessor(gltf, buffers, int(pos_ai), src)
                               .astype(np.float64), "vertices", src)
            idx_ai = getattr(prim, "indices", None)
            if idx_ai is not None:
                idx = _read_accessor(gltf, buffers, int(idx_ai), src).astype(np.int64).ravel()
            else:
                idx = np.arange(V.shape[0], dtype=np.int64)
            F = _triangulate_indices(idx, getattr(prim, "mode", None), src)
            if F.shape[0] == 0:
                continue                                # points/lines primitive -> skip
            _check_count(F.shape[0], "triangles", MAX_FACES, "MAX_FACES", src)
            lo, hi = int(F.min()), int(F.max())
            if lo < 0 or hi >= V.shape[0]:
                raise ValueError("%s: face index %d out of range for %d vertices"
                                 % (src, hi if hi >= V.shape[0] else lo, V.shape[0]))
            name = base if len(getattr(mesh_obj, "primitives", [])) == 1 else "%s[%d]" % (base, pi)
            scene.append({"name": str(name), "V": V, "F": F,
                          "transform": world.astype(np.float64)})
    return scene


def read_gltf_merged(path: str, apply_transforms: bool = True):
    """Read a glTF/GLB and merge every primitive into one ``(V, F)`` mesh.

    The common case for evis: bake each primitive's world *transform* into its
    vertices (when *apply_transforms*) and concatenate, offsetting face indices, so
    the whole scene becomes a single graspable triangle mesh — ``V`` (nv,3) float64,
    ``F`` (nf,3) int64. With ``apply_transforms=False`` the local vertices are kept
    (transforms ignored). Returns two empty arrays for a scene with no triangles.

    Same backend, limitations and errors as :func:`read_gltf`.
    """
    scene = read_gltf(path)
    Vs, Fs, off = [], [], 0
    for m in scene:
        V, F = m["V"], m["F"]
        if apply_transforms:
            T = m["transform"]
            V = V @ T[:3, :3].T + T[:3, 3]
        Vs.append(V)
        Fs.append(F + off)
        off += V.shape[0]
    if not Vs:
        return np.zeros((0, 3), np.float64), np.zeros((0, 3), np.int64)
    V = _finite_points(np.concatenate(Vs, axis=0), "vertices", str(path))
    F = np.concatenate(Fs, axis=0).astype(np.int64)
    return V, F


# =========================================================================== #
# LAS / LAZ                                                                    #
# =========================================================================== #
def _scale_rgb(channels: list, src: str) -> np.ndarray:
    """Stack r/g/b -> (N,3) float64 in [0,1] with the 16-bit/8-bit heuristic."""
    C = np.column_stack([np.asarray(c, np.float64) for c in channels])
    for j in range(3):
        col = C[:, j]
        if col.size and np.isfinite(col).all():
            C[:, j] = col / (65535.0 if col.max() > 255.0 else 255.0)
    return np.clip(C, 0.0, 1.0)


def read_las(path: str):
    """Read a LAS / LAZ point cloud -> ``(P, attrs)``.

    ``P`` is (N, 3) float64 in the file's metric coordinates: the ASPRS header
    scale and offset are applied (``coord = X*scale + offset``). No CRS
    reprojection is performed — the points stay in whatever system the file uses.
    ``.laz`` is handled by laspy's lazrs backend.

    ``attrs`` is a dict of whichever per-point arrays the point format carries,
    among: ``intensity``, ``classification``, ``return_number`` (integer arrays),
    ``red`` / ``green`` / ``blue`` (returned together as ``rgb``, an (N,3) float64
    array in [0,1] — see the module docstring for the 16-bit/8-bit scaling
    heuristic) and ``gps_time`` (float64).

    Reference: ASPRS LAS Specification.

    Raises ``FileNotFoundError`` if the path is missing, ``RuntimeError`` if laspy
    is not installed, and ``ValueError`` (naming the path) on a broken file or a
    point count over ``MAX_POINTS``.
    """
    src = str(path)
    _stat_or_raise(src)
    laspy = _need("laspy", "read_las", "laspy lazrs")
    try:
        with laspy.open(src) as reader:                 # header first: check count before reading
            n = int(reader.header.point_count)
            _check_count(n, "points", MAX_POINTS, "MAX_POINTS", src)
            las = reader.read()
    except (ValueError, FileNotFoundError, RuntimeError):
        raise
    except Exception as e:
        raise ValueError("%s: not a valid LAS/LAZ file (%s: %s)"
                         % (src, type(e).__name__, e)) from None

    P = _finite_points(np.column_stack([np.asarray(las.x, np.float64),
                                        np.asarray(las.y, np.float64),
                                        np.asarray(las.z, np.float64)]), "points", src)
    dims = set(las.point_format.dimension_names)
    attrs: dict = {}
    if "intensity" in dims:
        attrs["intensity"] = np.asarray(las.intensity)
    if "classification" in dims:
        attrs["classification"] = np.asarray(las.classification)
    if "return_number" in dims:
        attrs["return_number"] = np.asarray(las.return_number)
    if {"red", "green", "blue"} <= dims:
        attrs["rgb"] = _scale_rgb([las.red, las.green, las.blue], src)
    if "gps_time" in dims:
        attrs["gps_time"] = np.asarray(las.gps_time, np.float64)
    return P, attrs


# =========================================================================== #
# PCD (ascii / binary / binary_compressed)                                     #
# =========================================================================== #
def read_pcd(path: str):
    """Read a PCD point cloud -> ``(P, attrs)``.

    Handles all three PCL layouts — ``ascii``, ``binary`` and
    ``binary_compressed`` — the last of which :func:`mesh.read_points` cannot read.
    ``P`` is (N, 3) float64 from the ``x`` / ``y`` / ``z`` fields. ``attrs`` carries
    ``rgb`` (an (N,3) float64 array in [0,1]) when the cloud has either a packed
    ``rgb`` field (PCL's float-packed convention) or separate ``r`` / ``g`` / ``b``
    fields; both are divided by 255 and clipped.

    Reference: PCL Point Cloud Data (PCD) file format.

    Raises ``FileNotFoundError`` if the path is missing, ``RuntimeError`` if pypcd4
    is not installed, and ``ValueError`` (naming the path) on a broken file, a point
    count over ``MAX_POINTS``, or a cloud lacking x/y/z fields.
    """
    src = str(path)
    _stat_or_raise(src)
    _need("pypcd4", "read_pcd", "pypcd4")
    from pypcd4 import PointCloud

    try:
        pc = PointCloud.from_path(src)
    except (ValueError, FileNotFoundError, RuntimeError):
        raise
    except Exception as e:
        raise ValueError("%s: not a valid PCD file (%s: %s)"
                         % (src, type(e).__name__, e)) from None

    fields = tuple(pc.fields)
    low = [f.lower() for f in fields]
    for axis in ("x", "y", "z"):
        if axis not in low:
            raise ValueError("%s: PCD has no %r field (fields: %s)"
                             % (src, axis, ", ".join(fields) or "none"))
    n = int(pc.points)
    _check_count(n, "points", MAX_POINTS, "MAX_POINTS", src)

    def col(name):
        return np.asarray(pc.pc_data[fields[low.index(name)]], np.float64)

    P = _finite_points(np.column_stack([col("x"), col("y"), col("z")]), "points", src)
    attrs: dict = {}
    if "rgb" in low or "rgba" in low:
        packed = np.asarray(pc.pc_data[fields[low.index("rgb" if "rgb" in low else "rgba")]])
        dec = np.asarray(PointCloud.decode_rgb(packed.ravel())).reshape(-1, 3).astype(np.float64)
        attrs["rgb"] = np.clip(dec / 255.0, 0.0, 1.0)
    elif {"r", "g", "b"} <= set(low):
        attrs["rgb"] = np.clip(np.column_stack([col("r"), col("g"), col("b")]) / 255.0, 0.0, 1.0)
    return P, attrs


# =========================================================================== #
# Introspection                                                                #
# =========================================================================== #
#: Extension -> optional reader. glTF/GLB return a scene (list of dicts); LAS/LAZ
#: and PCD return ``(points, attrs)``.
OPT_FORMATS = {
    ".gltf": read_gltf,
    ".glb": read_gltf,
    ".las": read_las,
    ".laz": read_las,
    ".pcd": read_pcd,
}


def formats_available() -> dict:
    """Report which optional backends are importable here -> ``{format: bool}``.

    Keys ``gltf`` (pygltflib), ``las`` (laspy), ``laz`` (laspy + a LAZ backend:
    lazrs or laszip), ``pcd`` (pypcd4). ``True`` means the reader for that format
    will run without raising the ``pip install`` ``RuntimeError``."""
    laspy_ok = _can_import("laspy")
    return {
        "gltf": _can_import("pygltflib"),
        "las": laspy_ok,
        "laz": laspy_ok and (_can_import("lazrs") or _can_import("laszip")),
        "pcd": _can_import("pypcd4"),
    }
