"""Ground-truth tests for 3-D mesh / point-cloud import (mesh.py).

One known object — the unit cube (8 vertices, 12 triangles) — is hand-written as
a literal fixture in every supported format and read back. The comparison is on
*geometry*: the set of triangles as coordinate triples, so a reader is free to
order vertices differently or wind a face the other way and still be correct.
"""
import numpy as np
import pytest

import mesh

# --------------------------------------------------------------------------- #
# The reference object: the unit cube [0,1]^3 as 8 vertices + 12 triangles.    #
# --------------------------------------------------------------------------- #
CUBE_V = np.array([
    [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0],
])
CUBE_F = np.array([
    [0, 2, 1], [0, 3, 2],        # z = 0
    [4, 5, 6], [4, 6, 7],        # z = 1
    [0, 1, 5], [0, 5, 4],        # y = 0
    [1, 2, 6], [1, 6, 5],        # x = 1
    [2, 3, 7], [2, 7, 6],        # y = 1
    [3, 0, 4], [3, 4, 7],        # x = 0
])
CUBE_QUADS = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4],
              [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]


def tri_set(V, F):
    """Triangles as an order/winding-independent set of coordinate triples."""
    return {tuple(sorted(tuple(np.round(V[i], 9) + 0.0) for i in f)) for f in F}


REF = tri_set(CUBE_V, CUBE_F)


def assert_is_cube(V, F, nv=8):
    assert V.dtype == np.float64 and V.ndim == 2 and V.shape[1] == 3
    assert F.dtype == np.int64 and F.ndim == 2 and F.shape[1] == 3
    assert F.shape[0] == 12, "expected 12 triangles, got %d" % F.shape[0]
    assert tri_set(V, F) == REF
    used = np.unique(F)
    assert used.size == nv                       # every vertex referenced exactly once


# --------------------------------------------------------------------------- #
# Literal fixtures, one per format.                                           #
# --------------------------------------------------------------------------- #
OBJ_CUBE = """# unit cube, hand written
o cube
v 0 0 0
v 1 0 0
v 1 1 0
v 0 1 0
v 0 0 1
v 1 0 1
v 1 1 1
v 0 1 1
f 1 3 2
f 1 4 3
f 5 6 7
f 5 7 8
f 1 2 6
f 1 6 5
f 2 3 7
f 2 7 6
f 3 4 8
f 3 8 7
f 4 1 5
f 4 5 8
"""

# same cube as 6 quads (+ v/vt/vn index syntax) — exercises fan triangulation
OBJ_CUBE_QUADS = """v 0 0 0
v 1 0 0
v 1 1 0
v 0 1 0
v 0 0 1
v 1 0 1
v 1 1 1
v 0 1 1
vt 0 0
vn 0 0 1
f 1/1/1 4/1/1 3/1/1 2/1/1
f 5/1/1 6/1/1 7/1/1 8/1/1
f 1/1/1 2/1/1 6/1/1 5/1/1
f 2/1/1 3/1/1 7/1/1 6/1/1
f 3/1/1 4/1/1 8/1/1 7/1/1
f 4/1/1 1/1/1 5/1/1 8/1/1
"""

OFF_CUBE = """OFF
# unit cube
8 12 0
0 0 0
1 0 0
1 1 0
0 1 0
0 0 1
1 0 1
1 1 1
0 1 1
3 0 2 1
3 0 3 2
3 4 5 6
3 4 6 7
3 0 1 5
3 0 5 4
3 1 2 6
3 1 6 5
3 2 3 7
3 2 7 6
3 3 0 4
3 3 4 7
"""

PLY_ASCII_CUBE = """ply
format ascii 1.0
comment hand written unit cube
element vertex 8
property float x
property float y
property float z
element face 12
property list uchar int vertex_indices
end_header
0 0 0
1 0 0
1 1 0
0 1 0
0 0 1
1 0 1
1 1 1
0 1 1
3 0 2 1
3 0 3 2
3 4 5 6
3 4 6 7
3 0 1 5
3 0 5 4
3 1 2 6
3 1 6 5
3 2 3 7
3 2 7 6
3 3 0 4
3 3 4 7
"""


def _stl_ascii_cube() -> str:
    out = ["solid cube"]
    for f in CUBE_F:
        out.append("  facet normal 0 0 0")
        out.append("    outer loop")
        for i in f:
            out.append("      vertex %g %g %g" % tuple(CUBE_V[i]))
        out.append("    endloop")
        out.append("  endfacet")
    out.append("endsolid cube")
    return "\n".join(out) + "\n"


def _stl_binary_cube(count=None, ntri=None) -> bytes:
    """Binary STL per the 3D Systems spec: 80-byte header, uint32 count, 50 B/tri.
    *count* overrides the declared count (to forge a truncated file)."""
    tris = CUBE_F if ntri is None else CUBE_F[:ntri]
    dt = np.dtype([("normal", "<f4", (3,)), ("v", "<f4", (3, 3)), ("attr", "<u2")])
    rec = np.zeros(len(tris), dt)
    rec["v"] = CUBE_V[tris].astype("<f4")
    head = b"binary STL unit cube (fullseye test)".ljust(80, b"\0")
    n = len(tris) if count is None else count
    return head + np.array([n], "<u4").tobytes() + rec.tobytes()


def _ply_binary_cube(endian="<", nvert=8) -> bytes:
    fmt = "binary_little_endian" if endian == "<" else "binary_big_endian"
    header = ("ply\nformat %s 1.0\ncomment hand written unit cube\n"
              "element vertex %d\nproperty float x\nproperty float y\nproperty float z\n"
              "element face 12\nproperty list uchar int vertex_indices\n"
              "end_header\n" % (fmt, nvert)).encode("ascii")
    body = CUBE_V.astype(endian + "f4").tobytes()
    fdt = np.dtype([("n", "u1"), ("v", endian + "i4", (3,))])
    fa = np.zeros(12, fdt)
    fa["n"] = 3
    fa["v"] = CUBE_F
    return header + body + fa.tobytes()


def _write(tmp_path, name, content):
    p = tmp_path / name
    if isinstance(content, bytes):
        p.write_bytes(content)
    else:
        p.write_text(content, encoding="ascii")
    return str(p)


# --------------------------------------------------------------------------- #
# read_mesh — one test per format                                             #
# --------------------------------------------------------------------------- #
def test_read_obj_cube(tmp_path):
    V, F = mesh.read_mesh(_write(tmp_path, "cube.obj", OBJ_CUBE))
    assert_is_cube(V, F)


def test_read_obj_quads_are_fan_triangulated(tmp_path):
    V, F = mesh.read_mesh(_write(tmp_path, "quads.obj", OBJ_CUBE_QUADS))
    assert F.shape == (12, 3)                    # 6 quads -> 12 triangles
    assert V.shape == (8, 3)
    # a fan of a planar quad covers the same surface: total area must match
    A, B, C = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(B - A, C - A), axis=1).sum()
    assert abs(area - 6.0) < 1e-9                # unit cube surface area


def test_read_off_cube(tmp_path):
    V, F = mesh.read_mesh(_write(tmp_path, "cube.off", OFF_CUBE))
    assert_is_cube(V, F)


def test_read_stl_ascii_cube(tmp_path):
    V, F = mesh.read_mesh(_write(tmp_path, "cube.stl", _stl_ascii_cube()))
    assert_is_cube(V, F)                         # per-corner soup welded back to 8 vertices


def test_read_stl_binary_cube(tmp_path):
    V, F = mesh.read_mesh(_write(tmp_path, "cube_bin.stl", _stl_binary_cube()))
    assert_is_cube(V, F)


def test_read_ply_ascii_cube(tmp_path):
    V, F = mesh.read_mesh(_write(tmp_path, "cube.ply", PLY_ASCII_CUBE))
    assert_is_cube(V, F)


def test_read_ply_binary_little_endian_cube(tmp_path):
    V, F = mesh.read_mesh(_write(tmp_path, "cube_le.ply", _ply_binary_cube("<")))
    assert_is_cube(V, F)


def test_read_ply_binary_big_endian_cube(tmp_path):
    """The header declares the byte order and the reader must honour it — the same
    bytes read little-endian would be astronomically large floats."""
    V, F = mesh.read_mesh(_write(tmp_path, "cube_be.ply", _ply_binary_cube(">")))
    assert_is_cube(V, F)


def test_all_formats_agree(tmp_path):
    files = {"cube.obj": OBJ_CUBE, "cube.off": OFF_CUBE, "cube.ply": PLY_ASCII_CUBE,
             "a.stl": _stl_ascii_cube(), "b.stl": _stl_binary_cube(),
             "le.ply": _ply_binary_cube("<"), "be.ply": _ply_binary_cube(">")}
    sets = [tri_set(*mesh.read_mesh(_write(tmp_path, k, v))) for k, v in files.items()]
    assert all(s == REF for s in sets)


# --------------------------------------------------------------------------- #
# write_mesh round-trip                                                        #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", ["out.obj", "out.ply"])
def test_write_mesh_roundtrip(tmp_path, name):
    p = str(tmp_path / name)
    mesh.write_mesh(p, CUBE_V, CUBE_F)
    V, F = mesh.read_mesh(p)
    assert_is_cube(V, F)
    assert np.array_equal(V, CUBE_V)             # order and float64 value preserved
    assert np.array_equal(F, CUBE_F)


def test_write_mesh_preserves_float64_precision(tmp_path):
    V = CUBE_V + np.pi / 7.0                     # coordinates that float32 cannot hold
    p = str(tmp_path / "prec.ply")
    mesh.write_mesh(p, V, CUBE_F)
    back, _ = mesh.read_mesh(p)
    assert np.array_equal(back, V)


def test_write_mesh_rejects_bad_extension_and_indices(tmp_path):
    with pytest.raises(ValueError):
        mesh.write_mesh(str(tmp_path / "x.stl"), CUBE_V, CUBE_F)
    with pytest.raises(ValueError):
        mesh.write_mesh(str(tmp_path / "x.obj"), CUBE_V, np.array([[0, 1, 99]]))


# --------------------------------------------------------------------------- #
# read_points                                                                  #
# --------------------------------------------------------------------------- #
XYZ_TEXT = """# x y z
0.5 -1.25 3.0
-2.0 0.0 0.125
1.0 2.0 3.0
"""

XYZ_RGB_TEXT = """0.5 -1.25 3.0 255 0 0
-2.0 0.0 0.125 0 128 255
"""

PLY_POINTS = """ply
format ascii 1.0
element vertex 3
property float x
property float y
property float z
property uchar red
property uchar green
property uchar blue
end_header
0.5 -1.25 3 255 0 0
-2 0 0.125 0 128 255
1 2 3 51 102 153
"""

PCD_ASCII = """# .PCD v0.7 - Point Cloud Data file format
VERSION 0.7
FIELDS x y z
SIZE 4 4 4
TYPE F F F
COUNT 1 1 1
WIDTH 3
HEIGHT 1
VIEWPOINT 0 0 0 1 0 0 0
POINTS 3
DATA ascii
0.5 -1.25 3
-2 0 0.125
1 2 3
"""

EXPECT_P = np.array([[0.5, -1.25, 3.0], [-2.0, 0.0, 0.125], [1.0, 2.0, 3.0]])


def test_read_points_xyz_exact(tmp_path):
    P = mesh.read_points(_write(tmp_path, "cloud.xyz", XYZ_TEXT))
    assert P.dtype == np.float64
    assert np.array_equal(P, EXPECT_P)


def test_read_points_xyz_colors_roundtrip(tmp_path):
    P, C = mesh.read_points(_write(tmp_path, "rgb.xyz", XYZ_RGB_TEXT), with_colors=True)
    assert np.array_equal(P, EXPECT_P[:2])
    assert C.shape == (2, 3) and C.min() >= 0.0 and C.max() <= 1.0
    assert np.allclose(C[0], [1.0, 0.0, 0.0])
    assert np.allclose(C[1], [0.0, 128 / 255.0, 1.0])


def test_read_points_ply_exact_with_colors(tmp_path):
    p = _write(tmp_path, "cloud.ply", PLY_POINTS)
    P = mesh.read_points(p)
    assert np.array_equal(P, EXPECT_P)
    P2, C = mesh.read_points(p, with_colors=True)
    assert np.array_equal(P2, EXPECT_P)
    assert np.allclose(C, np.array([[255, 0, 0], [0, 128, 255], [51, 102, 153]]) / 255.0)


def test_read_points_without_colors_returns_none(tmp_path):
    _, C = mesh.read_points(_write(tmp_path, "plain.xyz", XYZ_TEXT), with_colors=True)
    assert C is None


def test_read_points_pcd_ascii(tmp_path):
    P = mesh.read_points(_write(tmp_path, "cloud.pcd", PCD_ASCII))
    assert np.array_equal(P, EXPECT_P)


def test_read_points_pcd_binary_is_refused(tmp_path):
    txt = PCD_ASCII.replace("DATA ascii", "DATA binary")
    with pytest.raises(ValueError, match="ascii"):
        mesh.read_points(_write(tmp_path, "bin.pcd", txt))


def test_read_points_obj_uses_vertices_only(tmp_path):
    P = mesh.read_points(_write(tmp_path, "cube.obj", OBJ_CUBE))
    assert P.shape == (8, 3)
    assert np.array_equal(np.unique(P, axis=0), np.unique(CUBE_V, axis=0))


def test_read_ply_binary_ragged_faces(tmp_path):
    """Mixed face degrees defeat the uniform-stride fast path — the sequential
    fallback must read the same pyramid (1 quad base + 4 triangles -> 6 tris)."""
    V = np.array([[0.0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0.5, 0.5, 1.0]])
    faces = [[0, 1, 2, 3], [0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]]
    head = ("ply\nformat binary_little_endian 1.0\nelement vertex 5\n"
            "property float x\nproperty float y\nproperty float z\n"
            "element face 5\nproperty list uchar int vertex_indices\n"
            "end_header\n").encode("ascii")
    body = V.astype("<f4").tobytes()
    for f in faces:
        body += np.array([len(f)], "u1").tobytes() + np.array(f, "<i4").tobytes()
    Vr, Fr = mesh.read_mesh(_write(tmp_path, "pyramid.ply", head + body))
    assert Vr.shape == (5, 3) and Fr.shape == (6, 3)
    assert np.allclose(Vr, V)
    assert tri_set(Vr, Fr) == tri_set(V, np.array([[0, 1, 2], [0, 2, 3], [0, 1, 4],
                                                   [1, 2, 4], [2, 3, 4], [3, 0, 4]]))


PLY_EXTRA_PROPS = """ply
format ascii 1.0
element vertex 3
property float x
property float y
property float z
property float nx
property uchar red
property uchar green
property uchar blue
property uchar alpha
element face 1
property list uchar int vertex_indices
property uchar flags
element edge 2
property int v1
property int v2
end_header
0 0 0 1 255 0 0 255
1 0 0 1 0 255 0 255
0 1 0 1 0 0 255 255
3 0 1 2 7
0 1
1 2
"""


def test_ply_extra_properties_and_elements_are_skipped(tmp_path):
    """Normals/alpha/per-face flags and a trailing 'edge' element are parsed for
    layout and dropped; geometry and colours still come out exactly."""
    p = _write(tmp_path, "extra.ply", PLY_EXTRA_PROPS)
    V, F = mesh.read_mesh(p)
    assert V.shape == (3, 3) and F.tolist() == [[0, 1, 2]]
    P, C = mesh.read_points(p, with_colors=True)
    assert np.array_equal(P, V)
    assert np.allclose(C, np.eye(3))


def test_read_points_pcd_packed_rgb(tmp_path):
    """PCL packs r,g,b into the bits of one float32 'rgb' field."""
    packed = np.array([255 * 65536 + 128 * 256 + 64], np.uint32).view(np.float32)[0]
    txt = ("VERSION 0.7\nFIELDS x y z rgb\nSIZE 4 4 4 4\nTYPE F F F F\nCOUNT 1 1 1 1\n"
           "WIDTH 1\nHEIGHT 1\nPOINTS 1\nDATA ascii\n0 1 2 %.9g\n" % packed)
    P, C = mesh.read_points(_write(tmp_path, "packed.pcd", txt), with_colors=True)
    assert np.array_equal(P, [[0.0, 1.0, 2.0]])
    assert np.allclose(C, [[1.0, 128 / 255.0, 64 / 255.0]])


def test_read_points_ply_binary(tmp_path):
    P = mesh.read_points(_write(tmp_path, "cube_le.ply", _ply_binary_cube("<")))
    assert np.array_equal(np.unique(P, axis=0), np.unique(CUBE_V, axis=0))


# --------------------------------------------------------------------------- #
# sample_surface / mesh_to_points                                              #
# --------------------------------------------------------------------------- #
def _on_cube_surface(P, tol=1e-9):
    """Distance to the nearest of the six cube planes, per point."""
    return np.minimum(np.abs(P), np.abs(P - 1.0)).min(axis=1) <= tol


def test_sample_surface_points_lie_on_the_surface():
    P = mesh.sample_surface(CUBE_V, CUBE_F, 3000, seed=0)
    assert P.shape == (3000, 3) and P.dtype == np.float64
    assert P.min() >= -1e-12 and P.max() <= 1 + 1e-12          # inside the bbox
    assert _on_cube_surface(P).all()                            # and on a face plane


def test_sample_surface_is_deterministic_per_seed():
    a = mesh.sample_surface(CUBE_V, CUBE_F, 500, seed=7)
    b = mesh.sample_surface(CUBE_V, CUBE_F, 500, seed=7)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, mesh.sample_surface(CUBE_V, CUBE_F, 500, seed=8))


def test_sample_surface_is_area_uniform_across_faces():
    n = 6000
    P = mesh.sample_surface(CUBE_V, CUBE_F, n, seed=1)
    # six equal-area faces -> ~n/6 points each (binomial sigma ~29, so +/-20% is ~7 sigma)
    d = np.stack([P[:, 0], 1 - P[:, 0], P[:, 1], 1 - P[:, 1], P[:, 2], 1 - P[:, 2]], axis=1)
    counts = np.bincount(np.argmin(d, axis=1), minlength=6)
    assert counts.sum() == n
    assert counts.min() > 0.8 * n / 6 and counts.max() < 1.2 * n / 6, counts.tolist()


def test_sample_surface_weights_by_area_not_by_triangle():
    # one big triangle + one tiny one: 99% of the area must draw ~99% of the points
    V = np.array([[0.0, 0, 0], [10.0, 0, 0], [0.0, 10, 0], [0.0, 0, 1], [0.1, 0, 1], [0, 0.1, 1]])
    F = np.array([[0, 1, 2], [3, 4, 5]])
    P = mesh.sample_surface(V, F, 4000, seed=2)
    on_small = P[:, 2] > 0.5
    assert on_small.mean() < 0.01


def test_mesh_to_points_is_sample_surface():
    assert np.array_equal(mesh.mesh_to_points(CUBE_V, CUBE_F, 200, seed=3),
                          mesh.sample_surface(CUBE_V, CUBE_F, 200, seed=3))


def test_sample_surface_edge_cases():
    assert mesh.sample_surface(CUBE_V, CUBE_F, 0).shape == (0, 3)
    with pytest.raises(ValueError):
        mesh.sample_surface(CUBE_V, CUBE_F, -1)
    with pytest.raises(ValueError):                 # degenerate (zero-area) mesh
        mesh.sample_surface(np.zeros((3, 3)), np.array([[0, 1, 2]]), 10)
    with pytest.raises(ValueError):                 # no faces
        mesh.sample_surface(CUBE_V, np.zeros((0, 3), np.int64), 10)


# --------------------------------------------------------------------------- #
# voxelize                                                                     #
# --------------------------------------------------------------------------- #
def test_voxelize_unit_cube_shell_count():
    occ, origin = mesh.voxelize(CUBE_V, CUBE_F, 0.25)
    assert occ.dtype == bool
    assert occ.shape == (5, 5, 5)                  # [0,1] at pitch .25 -> indices 0..4
    assert np.allclose(origin, [0.0, 0.0, 0.0]) and origin.dtype == np.float64
    # surface voxelization: the 5x5x5 box minus its 3x3x3 interior
    assert int(occ.sum()) == 125 - 27
    assert not occ[1:4, 1:4, 1:4].any()            # interior stays empty (hollow shell)
    assert occ[0].all() and occ[-1].all()          # the x=0 / x=1 faces are solid slabs


def test_voxelize_coarser_pitch():
    occ, origin = mesh.voxelize(CUBE_V, CUBE_F, 0.5)
    assert occ.shape == (3, 3, 3)
    assert int(occ.sum()) == 26                    # 27 minus the single interior cell
    assert not occ[1, 1, 1]


def test_voxelize_origin_follows_the_mesh():
    occ, origin = mesh.voxelize(CUBE_V - 3.0, CUBE_F, 0.25)
    assert np.allclose(origin, [-3.0, -3.0, -3.0])
    assert occ.shape == (5, 5, 5) and int(occ.sum()) == 98


def test_voxelize_rejects_bad_pitch_and_oversized_grid():
    for bad in (0.0, -0.1, np.nan):
        with pytest.raises(ValueError):
            mesh.voxelize(CUBE_V, CUBE_F, bad)
    with pytest.raises(ValueError, match="MAX_VOXELS"):
        mesh.voxelize(CUBE_V, CUBE_F, 1e-4)        # 10001^3 cells
    with pytest.raises(ValueError, match="MAX_VOXELS"):
        mesh.voxelize(CUBE_V, CUBE_F, 1e-30)       # cell count overflows int64 if unguarded


# --------------------------------------------------------------------------- #
# helpers                                                                      #
# --------------------------------------------------------------------------- #
def test_bounds_recenter_normalize_scale():
    V = CUBE_V * np.array([2.0, 4.0, 1.0]) + 5.0
    lo, hi = mesh.bounds(V)
    assert np.allclose(lo, [5, 5, 5]) and np.allclose(hi, [7, 9, 6])
    c = mesh.recenter(V)
    assert np.allclose(c.mean(axis=0), 0.0)
    assert np.allclose(mesh.bounds(c)[1] - mesh.bounds(c)[0], [2, 4, 1])   # shape kept
    s = mesh.normalize_scale(c, size=1.0)
    ext = mesh.bounds(s)[1] - mesh.bounds(s)[0]
    assert abs(ext.max() - 1.0) < 1e-12
    assert np.allclose(ext, [0.5, 1.0, 0.25])                              # aspect kept
    assert abs((mesh.bounds(mesh.normalize_scale(c, size=3.0))[1]
                - mesh.bounds(mesh.normalize_scale(c, size=3.0))[0]).max() - 3.0) < 1e-12


def test_helpers_reject_degenerate_input():
    with pytest.raises(ValueError):
        mesh.bounds(np.zeros((0, 3)))
    with pytest.raises(ValueError):
        mesh.normalize_scale(np.ones((4, 3)))          # all vertices coincident
    with pytest.raises(ValueError):
        mesh.normalize_scale(CUBE_V, size=0.0)


# --------------------------------------------------------------------------- #
# fail-closed on untrusted files                                              #
# --------------------------------------------------------------------------- #
def test_truncated_binary_stl_raises(tmp_path):
    """Header claims 12 triangles, the file carries 2 — must refuse, not read junk."""
    raw = _stl_binary_cube(count=12, ntri=2)
    with pytest.raises(ValueError, match="declares 12 triangles"):
        mesh.read_mesh(_write(tmp_path, "trunc.stl", raw))


def test_garbage_binary_file_raises(tmp_path):
    junk = np.random.default_rng(0).integers(0, 256, 300, dtype=np.uint8).tobytes()
    for name in ("junk.ply", "junk.stl", "junk.off", "junk.obj"):
        with pytest.raises(ValueError):
            mesh.read_mesh(_write(tmp_path, name, junk))


def test_oversized_declared_count_raises(tmp_path):
    """A declared element count that cannot fit in the file is refused up front."""
    head = ("ply\nformat binary_little_endian 1.0\nelement vertex 100000\n"
            "property float x\nproperty float y\nproperty float z\n"
            "end_header\n").encode("ascii") + b"\0" * 24
    with pytest.raises(ValueError, match="bytes remain"):
        mesh.read_mesh(_write(tmp_path, "big.ply", head))
    # and one past the hard cap is refused while still parsing the header
    huge = ("ply\nformat ascii 1.0\nelement vertex 999999999\n"
            "property float x\nproperty float y\nproperty float z\nend_header\n0 0 0\n")
    with pytest.raises(ValueError, match="MAX_ELEMENTS"):
        mesh.read_mesh(_write(tmp_path, "huge.ply", huge))
    off = OFF_CUBE.replace("8 12 0", "80 12 0")
    with pytest.raises(ValueError, match="data lines"):
        mesh.read_mesh(_write(tmp_path, "big.off", off))


def test_nan_vertex_raises(tmp_path):
    bad_obj = OBJ_CUBE.replace("v 1 1 0", "v 1 nan 0")
    with pytest.raises(ValueError, match="non-finite"):
        mesh.read_mesh(_write(tmp_path, "nan.obj", bad_obj))
    bad_ply = PLY_ASCII_CUBE.replace("1 1 0\n", "1 inf 0\n", 1)
    with pytest.raises(ValueError, match="non-finite"):
        mesh.read_mesh(_write(tmp_path, "inf.ply", bad_ply))
    with pytest.raises(ValueError, match="non-finite"):
        mesh.write_mesh(str(tmp_path / "nan.obj"), CUBE_V * np.nan, CUBE_F)


def test_out_of_range_face_index_raises(tmp_path):
    with pytest.raises(ValueError, match="out of range"):
        mesh.read_mesh(_write(tmp_path, "bad.off", OFF_CUBE.replace("3 0 2 1", "3 0 2 99")))
    with pytest.raises(ValueError, match="out of range"):
        mesh.read_mesh(_write(tmp_path, "bad.obj", OBJ_CUBE.replace("f 1 3 2", "f 1 3 99")))


def test_malformed_headers_raise(tmp_path):
    cases = {
        "noply.ply": "notply\nformat ascii 1.0\nend_header\n",
        "noend.ply": "ply\nformat ascii 1.0\nelement vertex 1\nproperty float x\n",
        "badfmt.ply": PLY_ASCII_CUBE.replace("format ascii 1.0", "format binary_middle 1.0"),
        "nomagic.off": OFF_CUBE.replace("OFF\n", "NOTOFF\n"),
        "shortface.off": OFF_CUBE.replace("3 0 2 1", "3 0 2"),
        "degenerate.off": OFF_CUBE.replace("3 0 2 1", "2 0 2"),
    }
    for name, txt in cases.items():
        with pytest.raises(ValueError):
            mesh.read_mesh(_write(tmp_path, name, txt))


def test_ascii_stl_with_partial_triangle_raises(tmp_path):
    txt = _stl_ascii_cube().replace("      vertex 0 0 0\n", "", 1)     # 35 vertices left
    with pytest.raises(ValueError, match="multiple of 3"):
        mesh.read_mesh(_write(tmp_path, "odd.stl", txt))


def test_empty_and_missing_files_raise(tmp_path):
    with pytest.raises(ValueError, match="empty"):
        mesh.read_mesh(_write(tmp_path, "empty.obj", ""))
    with pytest.raises(FileNotFoundError):
        mesh.read_mesh(str(tmp_path / "nope.ply"))


def test_unsupported_extension_raises(tmp_path):
    p = _write(tmp_path, "cube.gltf", "{}")
    with pytest.raises(ValueError, match="unsupported mesh format"):
        mesh.read_mesh(p)
    with pytest.raises(ValueError, match="unsupported point format"):
        mesh.read_points(p)


def test_ragged_xyz_and_pcd_rows_raise(tmp_path):
    with pytest.raises(ValueError, match="columns"):
        mesh.read_points(_write(tmp_path, "ragged.xyz", "1 2 3\n4 5\n"))
    with pytest.raises(ValueError, match="values"):
        mesh.read_points(_write(tmp_path, "ragged.pcd", PCD_ASCII.replace("1 2 3\n", "1 2\n")))
    with pytest.raises(ValueError, match="expected numbers"):
        mesh.read_points(_write(tmp_path, "words.xyz", "1 2 3\na b c\n"))


# --------------------------------------------------------------------------- #
# wiring: the facade and the rest of the perception stack                      #
# --------------------------------------------------------------------------- #
def test_mesh_reachable_through_facade(tmp_path):
    import fullseye as fs
    p = _write(tmp_path, "cube.obj", OBJ_CUBE)
    V, F = fs.read_mesh(p)
    assert_is_cube(V, F)
    assert fs.sample_surface(V, F, 64, seed=0).shape == (64, 3)
    assert fs.mesh_to_points(V, F, 8, seed=0).shape == (8, 3)
    occ, origin = fs.voxelize(V, F, 0.5)
    assert occ.shape == (3, 3, 3) and origin.shape == (3,)
    assert np.allclose(fs.bounds(V)[1], [1, 1, 1])
    assert np.allclose(fs.recenter(V).mean(axis=0), 0.0)
    assert abs(fs.normalize_scale(V, 2.0).max() - 2.0) < 1e-12
    q = str(tmp_path / "again.ply")
    fs.write_mesh(q, V, F)
    assert np.array_equal(fs.read_points(q), V)


def test_imported_mesh_feeds_the_pointcloud_stack():
    """The deliverable claim: an imported object becomes a cloud the existing
    perception modules consume (normals for grasp approach, voxel downsampling)."""
    import fullseye as fs
    P = fs.sample_surface(CUBE_V, CUBE_F, 2000, seed=4)
    n = fs.estimate_normals(P, k=12)
    assert n.shape == P.shape and np.allclose(np.linalg.norm(n, axis=1), 1.0)
    # cube normals are axis-aligned: one component ~1, the others ~0
    assert np.median(np.abs(n).max(axis=1)) > 0.95
    assert fs.voxel_downsample(P, voxel=0.25).shape[0] < P.shape[0]


def test_mesh_module_exports_match_all():
    for name in mesh.__all__:
        assert hasattr(mesh, name), name
