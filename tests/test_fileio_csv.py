from __future__ import annotations

import csv
import io

import numpy as np
import pandas as pd
import pytest

import fileio


META = {"source": "laser tracker", "generated_at": "2026-10-31T09:00:00+09:00",
        "coordinate_meaning": "right-handed fixture coordinates"}


def test_csv_roundtrip_and_independent_readers():
    table = {"x": np.array([0.5, 1.25, np.nan]), "label": np.array(["a", "b", "c"])}
    units = {"x": "mm", "label": "1"}
    text = fileio.table_write_csv(table, units=units, meta=META)
    lines = text.splitlines()
    assert next(csv.reader([lines[0]])) == ["x", "label"]
    assert next(csv.reader([lines[1]])) == ["# units:", "mm", "1"]

    frame = pd.read_csv(io.StringIO(text), comment="#")
    np.testing.assert_allclose(frame["x"].to_numpy(), table["x"], equal_nan=True, rtol=0, atol=0)
    np.testing.assert_array_equal(frame["label"].to_numpy(), table["label"])

    back = fileio.table_read_csv(text)
    assert back["units"] == units and back["meta"] == META
    np.testing.assert_allclose(back["columns"]["x"], table["x"], equal_nan=True, rtol=0, atol=0)
    np.testing.assert_array_equal(back["columns"]["label"], table["label"])


@pytest.mark.parametrize("mutate,match", [
    (lambda s: s.replace("# units:,mm,1", "# units:,mm"), "plus 2 units"),
    (lambda s: s.replace("1.25,b", "1.25"), "fields; expected"),
    (lambda s: s.replace("# source:", "# source_without_colon "), "lacks ':'"),
])
def test_csv_rejects_malformed_input(mutate, match):
    text = fileio.table_write_csv({"x": [0.5, 1.25], "label": ["a", "b"]},
                                  units={"x": "mm", "label": "1"}, meta=META)
    with pytest.raises(ValueError, match=match):
        fileio.table_read_csv(mutate(text))


def test_csv_writer_rejects_column_and_metadata_mismatches():
    with pytest.raises(ValueError, match="2 rows; expected 1"):
        fileio.table_write_csv({"x": [1], "y": [1, 2]}, units={"x": "mm", "y": "mm"}, meta=META)
    with pytest.raises(ValueError, match="units keys must exactly match"):
        fileio.table_write_csv({"x": [1]}, units={}, meta=META)
    with pytest.raises(ValueError, match="missing required key"):
        fileio.table_write_csv({"x": [1]}, units={"x": "mm"}, meta={})
