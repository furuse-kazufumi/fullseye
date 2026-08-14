"""Ground-truth tests for the optional heavier object formats (meshio_opt.py).

The backends (pygltflib / laspy / pypcd4) are installed, so every fixture is
*built with the backend itself* and read back — a real round-trip, not a literal
string. The comparison is on geometry: for glTF the unit cube recovers as the same
set of triangles (order/winding independent); for LAS/PCD the coordinates recover
to the backend's quantisation tolerance and the declared attributes are present.
"""
import numpy as np
import pytest

import meshio_opt


# --------------------------------------------------------------------------- #
# The reference object: the unit cube [0,1]^3 as 8 vertices + 12 triangles.    #
# --------------------------------------------------------------------------- #
CUBE_V = np.array([
    [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0],
], np.float64)
CUBE_F = np.array([
    [0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7],
    [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5],
    [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7],
], np.int64)


def tri_set(V, F):
    """Triangles as an order/winding-independent set of coordinate triples."""
    return {tuple(sorted(tuple(np.round(V[i], 6) + 0.0) for i in f)) for f in F}


REF = tri_set(CUBE_V, CUBE_F)


# --------------------------------------------------------------------------- #
# glTF fixtures, built with pygltflib.                                        #
# --------------------------------------------------------------------------- #
def _build_cube_gltf(translation=(10.0, 0.0, 0.0)):
    """A fresh single-primitive cube GLTF2 with the geometry in a binary blob."""
    import pygltflib as g

    positions = CUBE_V.astype("<f4").tobytes()          # 8 * 12 = 96 bytes
    indices = CUBE_F.astype("<u2").ravel().tobytes()    # 36 * 2 = 72 bytes, at offset 96
    blob = positions + indices
    gltf = g.GLTF2(
        scene=0,
        scenes=[g.Scene(nodes=[0])],
        nodes=[g.Node(mesh=0, translation=list(translation))],
        meshes=[g.Mesh(primitives=[g.Primitive(
            attributes=g.Attributes(POSITION=0), indices=1, mode=g.TRIANGLES)])],
        accessors=[
            g.Accessor(bufferView=0, componentType=g.FLOAT, count=8, type=g.VEC3,
                       min=CUBE_V.min(0).tolist(), max=CUBE_V.max(0).tolist()),
            g.Accessor(bufferView=1, componentType=g.UNSIGNED_SHORT, count=36, type=g.SCALAR),
        ],
        bufferViews=[
            g.BufferView(buffer=0, byteOffset=0, byteLength=len(positions),
                         target=g.ARRAY_BUFFER),
            g.BufferView(buffer=0, byteOffset=len(positions), byteLength=len(indices),
                         target=g.ELEMENT_ARRAY_BUFFER),
        ],
        buffers=[g.Buffer(byteLength=len(blob))],
    )
    gltf.set_binary_blob(blob)
    return gltf


def _save_glb(tmp_path, name="cube.glb", translation=(10.0, 0.0, 0.0)):
    p = str(tmp_path / name)
    _build_cube_gltf(translation).save(p)               # .glb -> GLB by extension
    return p


def _save_gltf(tmp_path, name="cube.gltf", translation=(10.0, 0.0, 0.0)):
    import pygltflib as g

    p = str(tmp_path / name)
    gltf = _build_cube_gltf(translation)
    gltf.convert_buffers(g.BufferFormat.DATAURI)         # embed the blob as a data URI
    gltf.save(p)
    return p


# --------------------------------------------------------------------------- #
# read_gltf / read_gltf_merged                                                #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("saver", [_save_glb, _save_gltf])
def test_read_gltf_scene_shapes_and_transform(tmp_path, saver):
    scene = meshio_opt.read_gltf(saver(tmp_path))
    assert len(scene) == 1
    m = scene[0]
    assert set(m) == {"name", "V", "F", "transform"}
    assert m["V"].dtype == np.float64 and m["V"].shape == (8, 3)
    assert m["F"].dtype == np.int64 and m["F"].shape == (12, 3)
    assert m["transform"].shape == (4, 4) and m["transform"].dtype == np.float64
    # local geometry is the untranslated cube; the transform carries the +10 x shift
    assert tri_set(m["V"], m["F"]) == REF
    assert np.allclose(m["transform"][:3, 3], [10.0, 0.0, 0.0])
    assert np.allclose(m["transform"][:3, :3], np.eye(3))


@pytest.mark.parametrize("saver", [_save_glb, _save_gltf])
def test_read_gltf_merged_bakes_transform(tmp_path, saver):
    V, F = meshio_opt.read_gltf_merged(saver(tmp_path))
    assert V.dtype == np.float64 and F.dtype == np.int64
    assert V.shape == (8, 3) and F.shape == (12, 3)
    # baked: the cube is shifted by +10 in x
    assert tri_set(V, F) == tri_set(CUBE_V + np.array([10.0, 0.0, 0.0]), CUBE_F)
    # and without applying the transform we recover the local cube
    V2, F2 = meshio_opt.read_gltf_merged(saver(tmp_path), apply_transforms=False)
    assert tri_set(V2, F2) == REF


def test_read_gltf_glb_and_gltf_agree(tmp_path):
    a = meshio_opt.read_gltf_merged(_save_glb(tmp_path, "a.glb"))
    b = meshio_opt.read_gltf_merged(_save_gltf(tmp_path, "b.gltf"))
    assert tri_set(*a) == tri_set(*b)


def test_read_gltf_triangle_strip_is_triangulated(tmp_path):
    """A 4-vertex TRIANGLE_STRIP must become 2 triangles covering the quad."""
    import pygltflib as g

    quad = np.array([[0.0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], np.float32)
    idx = np.array([0, 1, 2, 3], np.uint16)
    blob = quad.astype("<f4").tobytes() + idx.astype("<u2").tobytes()
    gltf = g.GLTF2(
        scene=0, scenes=[g.Scene(nodes=[0])], nodes=[g.Node(mesh=0)],
        meshes=[g.Mesh(primitives=[g.Primitive(
            attributes=g.Attributes(POSITION=0), indices=1, mode=g.TRIANGLE_STRIP)])],
        accessors=[
            g.Accessor(bufferView=0, componentType=g.FLOAT, count=4, type=g.VEC3,
                       min=quad.min(0).tolist(), max=quad.max(0).tolist()),
            g.Accessor(bufferView=1, componentType=g.UNSIGNED_SHORT, count=4, type=g.SCALAR),
        ],
        bufferViews=[
            g.BufferView(buffer=0, byteOffset=0, byteLength=quad.nbytes, target=g.ARRAY_BUFFER),
            g.BufferView(buffer=0, byteOffset=quad.nbytes, byteLength=idx.nbytes,
                         target=g.ELEMENT_ARRAY_BUFFER),
        ],
        buffers=[g.Buffer(byteLength=len(blob))],
    )
    gltf.set_binary_blob(blob)
    p = str(tmp_path / "strip.glb")
    gltf.save(p)
    V, F = meshio_opt.read_gltf_merged(p)
    assert V.shape == (4, 3) and F.shape == (2, 3)      # strip of 4 -> 2 triangles
    area = 0.5 * np.linalg.norm(
        np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1).sum()
    assert abs(area - 1.0) < 1e-6                        # the unit quad's area


# --------------------------------------------------------------------------- #
# read_las                                                                     #
# --------------------------------------------------------------------------- #
LAS_XYZ = np.array([[1.0, 3.0, 5.0], [2.5, 4.0, 6.0], [-2.0, 0.0, 0.125]])
LAS_INT = np.array([10, 20, 30])
LAS_CLS = np.array([2, 6, 1])
LAS_RGB16 = np.array([[65535, 0, 0], [0, 32768, 0], [0, 0, 65535]])   # 16-bit


def _write_las(tmp_path, name="scan.las", offset=(10.0, 0.0, 0.0)):
    import laspy

    p = str(tmp_path / name)
    header = laspy.LasHeader(point_format=3, version="1.2")   # fmt 3 has RGB + gps_time
    header.scales = [0.001, 0.001, 0.001]
    header.offsets = list(offset)
    las = laspy.LasData(header)
    las.x, las.y, las.z = LAS_XYZ[:, 0], LAS_XYZ[:, 1], LAS_XYZ[:, 2]
    las.intensity = LAS_INT
    las.classification = LAS_CLS
    las.return_number = np.array([1, 1, 1])
    las.red, las.green, las.blue = LAS_RGB16[:, 0], LAS_RGB16[:, 1], LAS_RGB16[:, 2]
    las.gps_time = np.array([1.5, 2.5, 3.5])
    las.write(p)
    return p


def test_read_las_coords_and_attrs(tmp_path):
    P, attrs = meshio_opt.read_las(_write_las(tmp_path))
    assert P.dtype == np.float64 and P.shape == (3, 3)
    assert np.allclose(P, LAS_XYZ, atol=1e-3)           # scale/offset quantisation tol
    assert np.array_equal(np.asarray(attrs["intensity"]), LAS_INT)
    assert np.array_equal(np.asarray(attrs["classification"]), LAS_CLS)
    assert "return_number" in attrs
    assert "gps_time" in attrs and np.allclose(attrs["gps_time"], [1.5, 2.5, 3.5])
    rgb = attrs["rgb"]
    assert rgb.shape == (3, 3) and rgb.min() >= 0.0 and rgb.max() <= 1.0
    assert np.allclose(rgb[0], [1.0, 0.0, 0.0])         # 65535 -> 1.0 (16-bit path)
    assert np.allclose(rgb[1], [0.0, 32768 / 65535.0, 0.0])


def test_read_laz_roundtrip(tmp_path):
    """The lazrs backend must read a compressed .laz to the same coordinates."""
    import laspy

    src = _write_las(tmp_path, "scan.las")
    laz = str(tmp_path / "scan.laz")
    laspy.read(src).write(laz)
    P, attrs = meshio_opt.read_las(laz)
    assert np.allclose(P, LAS_XYZ, atol=1e-3)
    assert np.array_equal(np.asarray(attrs["intensity"]), LAS_INT)


# --------------------------------------------------------------------------- #
# read_pcd                                                                     #
# --------------------------------------------------------------------------- #
PCD_XYZ = np.array([[0.5, -1.25, 3.0], [-2.0, 0.0, 0.125], [1.0, 2.0, 3.0]], np.float32)


def _write_pcd(tmp_path, name="cloud.pcd", with_rgb=False, encoding=None):
    from pypcd4 import PointCloud, Encoding

    p = str(tmp_path / name)
    if with_rgb:
        rgb = PointCloud.encode_rgb(np.array([[255, 128, 64], [0, 0, 0], [10, 20, 30]], np.uint8))
        pts = np.hstack([PCD_XYZ, rgb.reshape(-1, 1)]).astype(np.float32)
        pc = PointCloud.from_xyzrgb_points(pts)
    else:
        pc = PointCloud.from_xyz_points(PCD_XYZ)
    pc.save(p, encoding=encoding or Encoding.BINARY_COMPRESSED)
    return p


def test_read_pcd_binary_compressed(tmp_path):
    P, attrs = meshio_opt.read_pcd(_write_pcd(tmp_path))
    assert P.dtype == np.float64 and P.shape == (3, 3)
    assert np.allclose(P, PCD_XYZ)
    assert attrs == {} or "rgb" not in attrs


def test_read_pcd_ascii_and_binary(tmp_path):
    from pypcd4 import Encoding

    for enc, name in [(Encoding.ASCII, "a.pcd"), (Encoding.BINARY, "b.pcd")]:
        P, _ = meshio_opt.read_pcd(_write_pcd(tmp_path, name, encoding=enc))
        assert np.allclose(P, PCD_XYZ)


def test_read_pcd_rgb(tmp_path):
    P, attrs = meshio_opt.read_pcd(_write_pcd(tmp_path, "rgb.pcd", with_rgb=True))
    assert np.allclose(P, PCD_XYZ)
    assert "rgb" in attrs and attrs["rgb"].shape == (3, 3)
    assert attrs["rgb"].min() >= 0.0 and attrs["rgb"].max() <= 1.0
    assert np.allclose(attrs["rgb"][0], [255 / 255.0, 128 / 255.0, 64 / 255.0])


# --------------------------------------------------------------------------- #
# formats_available / OPT_FORMATS                                             #
# --------------------------------------------------------------------------- #
def test_formats_available_reports_installed_backends():
    avail = meshio_opt.formats_available()
    assert avail == {"gltf": True, "las": True, "laz": True, "pcd": True}


def test_opt_formats_maps_extensions_to_readers():
    fmt = meshio_opt.OPT_FORMATS
    assert fmt[".gltf"] is meshio_opt.read_gltf and fmt[".glb"] is meshio_opt.read_gltf
    assert fmt[".las"] is meshio_opt.read_las and fmt[".laz"] is meshio_opt.read_las
    assert fmt[".pcd"] is meshio_opt.read_pcd


def test_module_exports_match_all():
    for name in meshio_opt.__all__:
        assert hasattr(meshio_opt, name), name


# --------------------------------------------------------------------------- #
# fail-closed on untrusted files                                              #
# --------------------------------------------------------------------------- #
def test_missing_file_raises_filenotfound(tmp_path):
    for reader in (meshio_opt.read_gltf, meshio_opt.read_las, meshio_opt.read_pcd):
        with pytest.raises(FileNotFoundError):
            reader(str(tmp_path / "nope.dat"))
    with pytest.raises(FileNotFoundError):
        meshio_opt.read_gltf_merged(str(tmp_path / "nope.glb"))


def test_empty_file_raises(tmp_path):
    p = tmp_path / "empty.glb"
    p.write_bytes(b"")
    with pytest.raises(ValueError, match="empty"):
        meshio_opt.read_gltf(str(p))


def test_garbage_files_raise_valueerror(tmp_path):
    junk = np.random.default_rng(0).integers(0, 256, 400, dtype=np.uint8).tobytes()
    cases = [("junk.glb", meshio_opt.read_gltf), ("junk.las", meshio_opt.read_las),
             ("junk.laz", meshio_opt.read_las), ("junk.pcd", meshio_opt.read_pcd)]
    for name, reader in cases:
        p = tmp_path / name
        p.write_bytes(junk)
        with pytest.raises(ValueError):
            reader(str(p))


def test_truncated_glb_raises(tmp_path):
    """A GLB cut off mid-file must not read partial geometry."""
    full = _save_glb(tmp_path, "full.glb")
    with open(full, "rb") as f:
        raw = f.read()
    p = tmp_path / "trunc.glb"
    p.write_bytes(raw[: len(raw) // 2])
    with pytest.raises(ValueError):
        meshio_opt.read_gltf(str(p))


def test_oversized_declared_vertex_count_is_capped(tmp_path):
    """A hostile glTF whose accessor claims billions of vertices must be refused
    before any array is allocated — not left to exhaust memory."""
    import pygltflib as g

    gltf = _build_cube_gltf()
    gltf.accessors[0].count = 999_999_999                # far over MAX_VERTICES
    p = str(tmp_path / "huge.glb")
    gltf.save(p)
    with pytest.raises(ValueError, match="MAX_VERTICES|cap"):
        meshio_opt.read_gltf(str(p))


def test_oversized_declared_face_count_is_capped(tmp_path):
    """An accessor claiming an enormous index count is capped as faces."""
    import pygltflib as g

    gltf = _build_cube_gltf()
    # a valid vertex accessor but an index accessor claiming a huge count
    gltf.accessors[1].count = 999_999_999
    p = str(tmp_path / "hugef.glb")
    gltf.save(p)
    with pytest.raises(ValueError, match="cap|bytes"):
        meshio_opt.read_gltf(str(p))
