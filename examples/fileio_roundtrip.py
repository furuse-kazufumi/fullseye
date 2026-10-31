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
    print("PASS: CSV units, metadata, and two numeric columns round-trip")


if __name__ == "__main__":
    main()
