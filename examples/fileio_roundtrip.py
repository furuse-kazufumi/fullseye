"""In-memory CSV round trip with units and provenance."""
from __future__ import annotations

import io

import numpy as np

import fullseye as fs


def main():
    table = {"x": np.array([0.0, 1.25, 2.5]), "force": np.array([1.0, 1.5, 2.0])}
    units = {"x": "mm", "force": "N"}
    meta = {"source": "synthetic calibration table",
            "generated_at": "2026-10-31T12:00:00+09:00",
            "coordinate_meaning": "x increases along the fixture axis"}
    text = fs.table_write_csv(table, units=units, meta=meta)
    back = fs.table_read_csv(text)
    assert back["units"] == units
    assert back["meta"] == meta
    for name in table:
        np.testing.assert_array_equal(back["columns"][name], table[name])

    import pandas as pd
    frame = pd.read_csv(io.StringIO(text), comment="#")
    np.testing.assert_array_equal(frame["x"].to_numpy(), table["x"])

    vertices = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
    faces = np.array([[0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3]])
    for write, read, kwargs in (
            (fs.mesh_write_stl, fs.mesh_read_stl, {"binary": True}),
            (fs.mesh_write_obj, fs.mesh_read_obj, {}),
            (fs.mesh_write_off, fs.mesh_read_off, {})):
        v2, f2 = read(write((vertices, faces), **kwargs))
        assert len(v2) == 4 and len(f2) == 4
    ply = fs.mesh_write_ply({"vertices": vertices, "faces": faces,
                             "attributes": {"temperature": np.arange(4.)}}, binary=False)
    assert "temperature" in fs.mesh_read_ply(ply)["attributes"]
    np.testing.assert_array_equal(fs.points_read_xyz(fs.points_write_xyz(vertices)), vertices)
    e57_table = {"points": vertices, "colors": np.tile([128, 64, 255], (4, 1)),
                 "pose": {"rotation": [1, 0, 0, 0], "translation": [1, 2, 3]}}
    e57_back = fs.e57_read(fs.e57_write(e57_table))
    np.testing.assert_allclose(e57_back["points"], vertices, atol=1e-6)
    np.testing.assert_array_equal(e57_back["colors"], e57_table["colors"])
    print("PASS: CSV, PLY, STL, OBJ, OFF, XYZ, and E57 round-trip in memory")


if __name__ == "__main__":
    main()
