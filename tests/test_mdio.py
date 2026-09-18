# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fullseye.mdio - typed results <-> Markdown. Readable rendering, and an exact
JSON fence that round-trips back through :mod:`fullseye.jsonio`."""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fullseye import mdio as M  # noqa: E402


def test_table_of_dicts_becomes_a_gfm_table_with_the_union_of_keys():
    tbl = [{"id": 1, "area": 12.5, "label": "A"}, {"id": 2, "area": 3.0, "note": "x"}]
    md = M.to_markdown(tbl, "table")
    assert "| id | area | label | note |" in md            # union, first-seen order
    assert "| --- | --- | --- | --- |" in md
    assert md.count("\n") == 3                              # header + rule + 2 rows


def test_table_dict_and_list_and_pipe_escaping():
    assert "| key | value |" in M.to_markdown({"n": 3, "ok": True}, "table")
    assert "true" in M.to_markdown({"ok": True}, "table")
    assert "| value |" in M.to_markdown([1.0, 2.0, 3.0], "table")
    assert "a\\|b" in M.to_markdown([{"name": "a|b"}], "table")   # pipe never breaks the grid


def test_numeric_sorts_render_as_capped_number_tables():
    pts = np.arange(60.0).reshape(30, 2)
    md = M.to_markdown(pts, "points", max_rows=5)
    assert "| row | c0 | c1 |" in md and "more rows" in md
    wide = np.arange(40.0).reshape(2, 20)
    assert "more columns" in M.to_markdown(wide, "matrix", max_cols=6)


def test_non_text_sorts_become_one_line_summaries():
    img = np.zeros((5, 7)); img[0, 0] = 1.0
    s = M.to_markdown(img, "image")
    assert s.startswith("image 5x7") and "mean" in s
    reg = (np.eye(4) > 0).astype(float)
    r = M.to_markdown(reg, "region")
    assert "coverage" in r and "bbox rows 0-3" in r
    assert "empty region" in M.to_markdown(np.zeros((3, 4)), "region")
    c = {"shape": (10, 12), "cs": [np.zeros((3, 2)), np.zeros((5, 2))]}
    assert "2 contour(s), 8 points total on 10x12" == M.to_markdown(c, "contour")


def test_feature_and_title_and_nonfinite():
    assert M.to_markdown(2.5, "feature") == "`2.5`"
    assert M.to_markdown(2.5, "feature", title="score").startswith("**score**")
    assert "NaN" in M.to_markdown(float("nan"), "feature")


def test_markdown_is_fail_closed_on_unknown_sort():
    with pytest.raises(ValueError, match="no Markdown"):
        M.to_markdown(np.zeros(3), "match")


def test_json_block_round_trips_bit_for_bit_from_inside_prose():
    pts = np.array([[1.5, 2.0], [1.0 / 3.0, np.pi]])
    doc = "# Report\n\ntext\n\n" + M.json_block(pts, "points") + "\n\n```python\nprint(1)\n```\n"
    found = M.extract_json(doc)
    assert len(found) == 1 and found[0][1] == "points"
    assert np.array_equal(found[0][0].view(np.uint8), pts.view(np.uint8))


def test_extract_ignores_foreign_fences_and_fails_closed_on_a_broken_envelope():
    doc = M.json_block(np.zeros((2, 2)), "image") + "\n```json\n{\"hello\": 1}\n```\n"
    assert len(M.extract_json(doc)) == 1                    # the plain json fence is skipped
    assert M.extract_json("no fences here") == []
    bad = '```json\n{"fullseye_sort": "image", "version": 99, "payload": {}}\n```'
    with pytest.raises(ValueError, match="version"):
        M.extract_json(bad)


def test_report_is_both_readable_and_machine_recoverable():
    pts = np.arange(6.0).reshape(3, 2)
    tbl = [{"id": 1, "area": 2.0}]
    rep = M.report([("Blobs", tbl, "table"), ("Score", 0.87, "feature"), ("Points", pts, "points")],
                   title="Inspection", with_json=True)
    assert rep.startswith("# Inspection")
    assert "## Blobs" in rep and "## Score" in rep and "<details>" in rep
    rec = M.extract_json(rep)                               # the folded envelopes come back exactly
    assert len(rec) == 3 and rec[1][0] == 0.87
    assert np.array_equal(rec[2][0].view(np.uint8), pts.view(np.uint8))
    with pytest.raises(ValueError, match="heading"):
        M.report([("only-two", 1.0)])
