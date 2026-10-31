from __future__ import annotations

import io

import numpy as np
import pytest
import trimesh
from plyfile import PlyData
from stl import mesh as numpy_stl_mesh

import fileio
import imgio


V = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
              [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]], dtype=np.float64)
F = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7],
              [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5],
              [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]], dtype=np.int64)


def _sorted_rows(a):
    a = np.asarray(a)
    return a[np.lexsort(a.T[::-1])]


@pytest.mark.parametrize("binary", [False, True])
def test_ply_roundtrip_properties_and_independent_reader(binary):
    normals = V - 0.5
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    colors = np.tile([0.5, 0.25, 1.0], (len(V), 1))
    confidence = np.linspace(0.0, 1.0, len(V))
    payload = fileio.mesh_write_ply(
        {"vertices": V, "faces": F, "normals": normals, "colors": colors,
         "attributes": {"confidence": confidence}}, binary=binary)
    assert isinstance(payload, bytes if binary else str)
    back = fileio.mesh_read_ply(payload)
    np.testing.assert_array_equal(back["vertices"], V)
    np.testing.assert_array_equal(back["faces"], F)
    np.testing.assert_allclose(back["normals"], normals, rtol=0, atol=0)
    np.testing.assert_array_equal(back["colors"], np.tile([128, 64, 255], (len(V), 1)) / 255.0)
    np.testing.assert_array_equal(back["attributes"]["confidence"], confidence)

    independent = PlyData.read(io.BytesIO(payload if binary else payload.encode("ascii")))
    assert independent["vertex"].count == len(V) and independent["face"].count == len(F)
    assert independent["vertex"]["red"][0] == 128
    np.testing.assert_array_equal(independent["vertex"]["confidence"], confidence)


@pytest.mark.parametrize("binary", [False, True])
def test_stl_roundtrip_trimesh_numpy_stl_volume_and_watertight(binary):
    payload = fileio.mesh_write_stl((V, F), binary=binary)
    raw = payload if isinstance(payload, bytes) else payload.encode("ascii")
    back_v, back_f = fileio.mesh_read_stl(raw)
    expected = V.astype(np.float32).astype(np.float64) if binary else V
    np.testing.assert_array_equal(_sorted_rows(back_v), _sorted_rows(expected))
    assert len(back_f) == 12

    tm = trimesh.load(io.BytesIO(raw), file_type="stl", force="mesh", process=True)
    assert tm.is_watertight and tm.is_winding_consistent
    assert abs(float(tm.volume) - 1.0) < 1e-12
    ns = numpy_stl_mesh.Mesh.from_file("cube.stl", fh=io.BytesIO(raw))
    volume, _cog, _inertia = ns.get_mass_properties()
    assert abs(float(volume) - 1.0) < 1e-12


@pytest.mark.parametrize("fmt,writer,reader", [
    ("obj", fileio.mesh_write_obj, fileio.mesh_read_obj),
    ("off", fileio.mesh_write_off, fileio.mesh_read_off),
])
def test_obj_off_roundtrip_and_trimesh(fmt, writer, reader):
    text = writer((V, F))
    back_v, back_f = reader(text)
    np.testing.assert_array_equal(back_v, V)
    np.testing.assert_array_equal(back_f, F)
    tm = trimesh.load(io.BytesIO(text.encode("ascii")), file_type=fmt, force="mesh", process=True)
    assert tm.is_watertight and abs(float(tm.volume) - 1.0) < 1e-12
    if fmt == "obj":
        assert "\nvn " in text and "//" in text


def test_xyz_roundtrip():
    points = V + np.array([0.125, -0.25, 1.5])
    text = fileio.points_write_xyz(points)
    np.testing.assert_array_equal(fileio.points_read_xyz(text), points)


def test_imgio_save_ply_rounds_half_up(tmp_path):
    path = tmp_path / "half.ply"
    imgio.save_ply(str(path), [[0, 0, 0]], [[0.5, 0.5, 0.5]])
    assert path.read_text(encoding="ascii").splitlines()[-1].endswith("128 128 128")


def test_mesh_formats_reject_corrupt_inputs_by_name():
    binary_stl = fileio.mesh_write_stl((V, F), binary=True)
    with pytest.raises(ValueError, match="declares 12 triangles"):
        fileio.mesh_read_stl(binary_stl[:-7])
    with pytest.raises(ValueError, match=r"face index .* out of range"):
        fileio.mesh_read_off("OFF\n3 1 0\n0 0 0\n1 0 0\n0 1 0\n3 0 1 9\n")
    valid = fileio.mesh_write_ply({"vertices": V, "faces": F}, binary=False)
    unknown = valid.replace("property double z\n", "property double z\nproperty list uchar int neighbours\n")
    with pytest.raises(ValueError, match="unknown vertex list property 'neighbours'"):
        fileio.mesh_read_ply(unknown)
    with pytest.raises(ValueError, match="unknown PLY element 'edge'"):
        fileio.mesh_read_ply(valid.replace("element face", "element edge"))


def test_mesh_writers_reject_degenerate_face():
    with pytest.raises(ValueError, match="degenerate face at index 0"):
        fileio.mesh_write_stl((V, np.array([[0, 0, 1]])), binary=True)
