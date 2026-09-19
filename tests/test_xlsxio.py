# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fullseye.xlsxio — 型付き結果を Excel(.xlsx)レポートに書き出す。書いて開き直して検査する。"""
import os

import numpy as np
import pytest

openpyxl = pytest.importorskip("openpyxl")   # optional 依存。無ければこのファイルは skip

import fullseye  # noqa: E402
from fullseye import xlsxio  # noqa: E402


def _cells(ws):
    return [c.value for row in ws.iter_rows() for c in row if c.value is not None]


def test_report_writes_tables_scalars_and_embeds_an_image(tmp_path):
    blobs = [{"id": 1, "area": 12.5, "label": "A"}, {"id": 2, "area": 3.0, "label": "B"}]
    pts = np.array([[1.5, 2.0], [3.25, 4.0]])
    img = np.zeros((128, 128))
    img[32:96, 32:96] = 1.0
    p = str(tmp_path / "report.xlsx")
    out = xlsxio.save_xlsx_report(
        [("Blobs", blobs, "table"), ("Points", pts, "points"),
         ("Area frac", 0.42, "feature"), ("Preview", img, "image")],
        p, title="検査レポート")
    assert out == p and os.path.exists(p)
    wb = openpyxl.load_workbook(p)
    ws = wb["Report"]
    vals = _cells(ws)
    assert ws["A1"].value == "検査レポート"
    assert 12.5 in vals and "label" in vals            # table header + data
    assert 0.42 in vals                                # feature scalar
    assert 1.5 in vals and 3.25 in vals                # points
    assert len(ws._images) == 1                        # image embedded


def test_facade_exposes_save_xlsx_report(tmp_path):
    assert hasattr(fullseye, "save_xlsx_report")
    p = str(tmp_path / "f.xlsx")
    fullseye.save_xlsx_report([("M", np.eye(3), "matrix")], p)
    wb = openpyxl.load_workbook(p)
    vals = _cells(wb["Report"])
    assert 1.0 in vals and 0.0 in vals                 # identity matrix cells


def test_unknown_sort_is_rejected(tmp_path):
    with pytest.raises(ValueError, match=r"unknown sort"):
        xlsxio.save_xlsx_report([("bad", object(), "no_such_sort")], str(tmp_path / "x.xlsx"))


def test_bad_section_shape_is_rejected(tmp_path):
    with pytest.raises(ValueError, match=r"heading, value, sort"):
        xlsxio.save_xlsx_report([("only", "two")], str(tmp_path / "x.xlsx"))


def test_image_falls_back_to_a_summary_without_thumbnails(tmp_path):
    img = np.zeros((64, 64))
    img[8:56, 8:56] = 0.7
    p = str(tmp_path / "nothumb.xlsx")
    xlsxio.save_xlsx_report([("Preview", img, "image")], p, thumbnails=False)
    wb = openpyxl.load_workbook(p)
    assert len(wb["Report"]._images) == 0              # no embed
    joined = " ".join(str(v) for v in _cells(wb["Report"]))
    assert "image" in joined and "(64, 64)" in joined  # summary cell instead
