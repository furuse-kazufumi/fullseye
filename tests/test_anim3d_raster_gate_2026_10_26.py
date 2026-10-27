# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""anim3d のページ一致門が OS フォント由来の pane 画素だけを除外する。"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pocviewer as pv  # noqa: E402
from tools import anim3d_i18n as gate  # noqa: E402


def _tx(s: str) -> dict:
    return {"ja": s, "en": s}


def _page(frames=None, xyz_value=0.0, check_result="1.0", second_pane=False) -> str:
    frames = np.arange(2 * 3 * 4, dtype=np.uint8).reshape(2, 3, 4) if frames is None else frames
    panes = [{"label": _tx("figure"), "frames": frames, "dedupe": False}]
    if second_pane:
        panes.append({"label": _tx("figure 2"), "frames": frames, "dedupe": False})
    tab = pv.viewer_anim3d_tab(
        "a", _tx("animation"), "passed", _tx("text"),
        t=[0.0, 1.0],
        bodies=[{"name": "triangle", "pos": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
                 "faces": [[0, 1, 2]], "rgb": [1, 2, 3]}],
        xyz=np.array([[[xyz_value, 0.0, 0.0]], [[1.0, 0.0, 0.0]]]),
        quat=np.array([[[1.0, 0.0, 0.0, 0.0]], [[1.0, 0.0, 0.0, 0.0]]]),
        panes=panes,
        checks=[{"what": _tx("value"), "criterion": "< 2", "result": check_result, "ok": True}],
    )
    spec = pv.viewer_spec("raster-gate", _tx("title"), _tx("subtitle"), _tx("hint"), [tab])
    return pv._build_html(spec, ["ja", "en"])


def test_one_changed_pixel_is_only_accepted_off_the_reference_font(monkeypatch):
    committed = _page()
    changed = np.arange(2 * 3 * 4, dtype=np.uint8).reshape(2, 3, 4)
    changed[1, 1, 1] ^= 1
    rebuilt = _page(changed)
    assert committed != rebuilt

    monkeypatch.setattr(gate, "_raster_font_name", lambda: gate.RASTER_REFERENCE_FONT)
    with pytest.raises(AssertionError):
        gate.check_same_page(committed, rebuilt, "page.html", "example")
    monkeypatch.setattr(gate, "_raster_font_name", lambda: "DejaVuSans.ttf")
    assert gate.check_same_page(committed, rebuilt, "page.html", "example") == "portable"


@pytest.mark.parametrize("font", [gate.RASTER_REFERENCE_FONT, "NotoSansCJK-Regular.ttc"])
@pytest.mark.parametrize("other", [lambda: _page(xyz_value=0.25), lambda: _page(check_result="1.1")])
def test_non_raster_numbers_stay_exact_on_every_font(monkeypatch, font, other):
    monkeypatch.setattr(gate, "_raster_font_name", lambda: font)
    with pytest.raises(AssertionError):
        gate.check_same_page(_page(), other(), "page.html", "example")


@pytest.mark.parametrize(
    "other",
    [lambda: _page(np.zeros((2, 4, 4), dtype=np.uint8)), lambda: _page(second_pane=True)],
)
def test_raster_shape_or_count_mismatch_still_fails_off_reference(monkeypatch, other):
    monkeypatch.setattr(gate, "_raster_font_name", lambda: "DejaVuSans.ttf")
    with pytest.raises(AssertionError):
        gate.check_same_page(_page(), other(), "page.html", "example")


def test_normal_form_has_a_nonempty_raster_target_and_keeps_shape():
    data, _, _ = gate._embedded_data(gate.normalize_rasters(_page()))
    panes = data["tabs"][0]["panes"]
    assert len(panes) >= 1
    records = [data["arrays"][pane["frames"]] for pane in panes]
    assert len(records) >= 1
    assert records[0]["shape"] == [2, 3, 4]
    assert records[0]["png"] == ["<RASTER>", "<RASTER>"]


def test_tiny_vertex_drift_is_portable_but_reference_font_stays_exact(monkeypatch):
    committed, rebuilt = _page(), _page(xyz_value=1e-10)
    assert committed != rebuilt
    monkeypatch.setattr(gate, "_raster_font_name", lambda: "DejaVuSans.ttf")
    assert gate.check_same_page(committed, rebuilt, "page.html", "example") == "portable"
    monkeypatch.setattr(gate, "_raster_font_name", lambda: gate.RASTER_REFERENCE_FONT)
    with pytest.raises(AssertionError):
        gate.check_same_page(committed, rebuilt, "page.html", "example")


def test_material_vertex_drift_reports_original_key_and_json_location(monkeypatch):
    committed, rebuilt = _page(), _page(xyz_value=1e-3)
    data, _, _ = gate._embedded_data(committed)
    original_key = data["tabs"][0]["xyz"]
    monkeypatch.setattr(gate, "_raster_font_name", lambda: "DejaVuSans.ttf")
    with pytest.raises(AssertionError) as caught:
        gate.check_same_page(committed, rebuilt, "page.html", "example")
    message = str(caught.value)
    assert original_key in message
    assert "$.tabs[0].xyz" in message
    assert "delta" in message


def test_portable_comparison_rejects_string_and_array_count_changes():
    base = _page()
    assert gate.compare_pages_portable(base, _page(check_result="1.X"))
    data, start, end = gate._embedded_data(base)
    key = data["tabs"][0]["quat"]
    del data["arrays"][key]
    import json
    fewer = base[:start] + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + base[end:]
    differences = gate.compare_pages_portable(base, fewer)
    assert differences
    assert any("count" in item or "quat" in item for item in differences)
