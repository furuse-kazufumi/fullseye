from __future__ import annotations

import builtins

import numpy as np
import pytest
import pye57

import fileio


POINTS = np.array([[0.125, -1.5, 2.0], [1.25, 0.5, 3.0],
                   [2.5, 1.5, 4.25], [4.0, 2.25, 8.5]], dtype=np.float64)
INTENSITY = np.array([0.125, 0.375, 0.625, 0.875], dtype=np.float64)
COLORS = np.array([[0, 64, 255], [32, 96, 224], [128, 160, 192], [255, 224, 0]],
                  dtype=np.uint8)
ROTATION = np.array([0.9238795325, 0.0, 0.0, 0.3826834324])
ROTATION /= np.linalg.norm(ROTATION)
TRANSLATION = np.array([10.0, -20.0, 30.0])


def _table():
    return {"points": POINTS, "intensity": INTENSITY, "colors": COLORS,
            "pose": {"rotation": ROTATION, "translation": TRANSLATION}}


def test_e57_roundtrip_and_independent_pye57_reader(tmp_path):
    before = set(tmp_path.iterdir())
    payload = fileio.e57_write(_table())
    assert isinstance(payload, bytes) and payload.startswith(b"ASTM-E57")
    assert fileio.e57_write(_table()) == payload
    assert set(tmp_path.iterdir()) == before

    back = fileio.e57_read(payload)
    np.testing.assert_allclose(back["points"], POINTS, rtol=0, atol=1e-6)
    np.testing.assert_allclose(back["intensity"], INTENSITY, rtol=0, atol=1e-6)
    np.testing.assert_array_equal(back["colors"], COLORS)
    np.testing.assert_allclose(back["pose"]["rotation"], ROTATION, rtol=0, atol=1e-10)
    np.testing.assert_array_equal(back["pose"]["translation"], TRANSLATION)

    path = tmp_path / "independent.e57"
    path.write_bytes(payload)
    independent = pye57.E57(str(path), mode="r")
    try:
        assert independent.scan_count == 1
        raw = independent.read_scan_raw(0)
        header = independent.get_header(0)
        np.testing.assert_allclose(raw["cartesianX"], POINTS[:, 0], rtol=0, atol=1e-6)
        np.testing.assert_array_equal(raw["colorRed"], COLORS[:, 0])
        np.testing.assert_allclose(header.rotation, ROTATION, rtol=0, atol=1e-10)
        np.testing.assert_array_equal(header.translation, TRANSLATION)
    finally:
        independent.close()


def test_e57_float_colors_round_half_up():
    table = _table()
    table["colors"] = np.tile([0.5, 0.25, 1.0], (len(POINTS), 1))
    back = fileio.e57_read(fileio.e57_write(table))
    np.testing.assert_array_equal(back["colors"], np.tile([128, 64, 255], (len(POINTS), 1)))


def test_e57_corrupt_input_rejected():
    payload = fileio.e57_write(_table())
    with pytest.raises(ValueError, match="e57_read: pye57 rejected"):
        fileio.e57_read(payload[:128])


def test_e57_missing_dependency_fails_closed_with_install_command(monkeypatch):
    real_import = builtins.__import__

    def missing(name, *args, **kwargs):
        if name == "pye57":
            raise ModuleNotFoundError("pye57 deliberately hidden")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing)
    with pytest.raises(ImportError, match=r"pip install pye57"):
        fileio.e57_write(_table())
    with pytest.raises(ImportError, match=r"pip install pye57"):
        fileio.e57_read(b"not e57")


@pytest.mark.parametrize("bad,match", [
    ({"points": np.empty((0, 3))}, "must not be empty"),
    ({"points": POINTS, "intensity": [1, 2]}, "intensity"),
    ({"points": POINTS, "colors": np.full((4, 3), 256)}, "integer colors"),
    ({"points": POINTS, "pose": {"rotation": [0, 0, 0, 0]}}, "nonzero quaternion"),
])
def test_e57_writer_rejects_invalid_tables(bad, match):
    with pytest.raises(ValueError, match=match):
        fileio.e57_write(bad)
