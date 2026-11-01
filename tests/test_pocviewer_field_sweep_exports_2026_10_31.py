"""Regression gates for field sweeps, auto ranges, exports, and published motion."""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

import pocviewer as pv

ROOT = Path(__file__).resolve().parents[1]
T = pv.viewer_text


def _spec(dynamic=True):
    frames, n = 3, 4
    pos0 = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0.0]], float)
    pos = np.repeat(pos0[None], frames, 0) if dynamic else pos0
    if dynamic:
        pos[:, :, 2] = np.arange(frames)[:, None] * 0.1
    val = np.arange(frames * n, dtype=float).reshape(frames, n) if dynamic else np.arange(n, dtype=float)
    xyz = np.zeros((frames, 1, 3)); quat = np.zeros((frames, 1, 4)); quat[..., 0] = 1
    pane = np.zeros((frames, 3, 4), np.uint8); pane[-1] = 17
    tab = pv.viewer_anim3d_tab(
        "field", T("場", "Field"), "passed", T("掃引", "Sweep"), np.arange(frames, dtype=float),
        [{"name": "surface", "pos": pos, "faces": [[0, 1, 2], [0, 2, 3]], "val": val}], xyz, quat,
        cbar={"lo": 0, "hi": 12, "unit": "mm", "cmap": "seq", "label": T("値", "Value")},
        series=[{"label": T("変位", "Displacement"), "values": [0.001, 0.002, 0.003], "unit": "mm",
                 "threshold": 0.0025}],
        panes=[{"label": T("像", "Image"), "frames": pane, "png": True}],
        axis={"values": [0, 1, 2], "segments": [{"k": 0, "label": T("荷重", "Load"), "unit": "N"}]})
    return pv.viewer_spec("field_test", T("試験", "Test"), T("副題", "Sub"), T("操作", "Hint"), [tab],
                          credit=T("合成", "Synthetic"))


def _data(spec):
    return pv._pack_spec(spec, ["ja", "en"])


def test_series_range_is_automatic_and_python_mapping_keeps_mm_values_in_frame():
    d = _data(_spec()); s = d["tabs"][0]["series"][0]
    assert s["lo"] == 0.0 and s["hi"] > 0.003
    assert s["lo"] < s["threshold"] < s["hi"]
    y = [pv._series_y(v, s["lo"], s["hi"], 8, 128) for v in s["values"]]
    assert all(8 <= q <= 128 for q in y)
    assert pv._format_sig(-0.305577491) == "-0.306"
    assert pv._format_sig(6.41712731) == "6.42"


def test_indexed_png_roundtrip_is_exact_and_smaller_for_scientific_panels():
    a = np.zeros((192, 256, 3), np.uint8)
    a[:, :128] = [0, 102, 255]; a[:, 128:] = [255, 255, 255]
    rec = pv._encode_array(a[None], "png")
    assert pv._decode_array(rec).shape == (1, 192, 256, 3)
    assert np.array_equal(pv._decode_array(rec)[0], a)
    import base64
    assert len(base64.b64decode(rec["png"][0])) < a.nbytes // 20


def test_dynamic_and_static_body_fields_pack_with_global_colorbar_and_reject_bad_input():
    d = _data(_spec()); b = d["tabs"][0]["bodies"][0]
    assert b["pos_t"] and b["val_t"]
    assert pv._decode_array(d["arrays"][b["pos"]]).shape == (3, 4, 3)
    assert pv._decode_array(d["arrays"][b["val"]]).shape == (3, 4)
    static = _spec(False); _data(static)
    bad = _spec(); bad["tabs"][0]["bodies"][0]["val"] = np.zeros((2, 4))
    with pytest.raises(ValueError, match="val は"):
        _data(bad)
    bad = _spec(); bad["tabs"][0]["bodies"][0]["pos"][1, 2, 0] = np.nan
    with pytest.raises(ValueError, match="NaN"):
        _data(bad)


def test_python_exports_include_metadata_and_vertex_value():
    ex = pv.viewer_export_strings(_spec(), "field", 2, "ja")
    assert ex["series_csv"].splitlines()[0] == "frame,time [s],変位 [mm]"
    assert "# exhibit,試験" in ex["series_csv"] and "# coordinates," in ex["pane_csv"][0]
    ply = ex["ply"][0]
    assert "property float value" in ply and "element vertex 4" in ply


def test_numeric_pane_field_is_exported_instead_of_rendered_pixels():
    spec = _spec()
    spec["tabs"][0]["panes"][0]["data"] = np.arange(18, dtype=float).reshape(3, 2, 3) / 10
    spec["tabs"][0]["panes"][0]["data_unit"] = "fringe"
    csv = pv.viewer_export_strings(spec, "field", 2, "ja")["pane_csv"][0]
    assert '# coordinates,"pane field: row from top, column from left; unit=fringe"' in csv
    assert csv.splitlines()[-1].startswith("1,1.5,1.6,1.7")


def test_motion_gate_requires_a_specific_static_reason():
    spec = _spec(); assert pv.viewer_motion_gate(spec)[0]["moving"]
    tab = spec["tabs"][0]
    tab["bodies"][0]["pos"] = np.asarray(tab["bodies"][0]["pos"])[0]
    tab["bodies"][0]["val"] = np.asarray(tab["bodies"][0]["val"])[0]
    tab["panes"][0]["frames"][:] = 0
    with pytest.raises(ValueError, match="static_reason"):
        pv.viewer_motion_gate(spec)
    tab["static_reason"] = "このタブは固定した基準像と数値系列だけを比較するため静止する。"
    assert pv.viewer_motion_gate(spec)[0]["moving"] is False


def test_every_published_anim3d_page_passes_the_motion_gate():
    for path in sorted((ROOT / "docs" / "view2026" / "anim3d").glob("*.html")):
        m = re.search(r"const D = (\{.*?\});\nconst \$ = ", path.read_text(encoding="utf-8"), re.S)
        if m:
            pv.viewer_motion_gate_data(json.loads(m.group(1)))


def test_published_quality_gate_has_named_legacy_exemptions_and_no_stale_names():
    exemptions = json.loads((ROOT / "tools" / "viewer_quality_exemptions.json").read_text(encoding="utf-8"))
    seen = set()
    for path in sorted((ROOT / "docs" / "view2026" / "anim3d").glob("*.html")):
        m = re.search(r"const D = (\{.*?\});\nconst \$ = ", path.read_text(encoding="utf-8"), re.S)
        if m:
            data = json.loads(m.group(1)); seen.add(data["id"])
            pv.viewer_quality_gate_data(data, exemptions)
    assert set(exemptions) <= seen


@pytest.mark.skipif(shutil.which("node") is None, reason="node が無い")
def test_export_javascript_is_syntax_valid(tmp_path):
    html = pv._build_html(_spec(), ["ja", "en"])
    js = re.search(r"<script>(.*)</script>", html, re.S).group(1)
    p = tmp_path / "viewer.js"; p.write_text(js, encoding="utf-8")
    import subprocess
    r = subprocess.run(["node", "--check", str(p)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_browser_and_python_exports_match(tmp_path):
    sys.path.insert(0, str(ROOT / "tools"))
    import headless_chrome
    if not headless_chrome.find_chrome():
        pytest.skip("Chrome が無い")
    spec = _spec()
    spec["tabs"][0]["panes"][0]["data"] = np.arange(18, dtype=float).reshape(3, 2, 3) / 10
    spec["tabs"][0]["panes"][0]["data_unit"] = "fringe"
    page = tmp_path / "field.html"; page.write_text(pv._build_html(spec, ["ja", "en"]), encoding="utf-8")
    want = pv.viewer_export_strings(spec, "field", 2, "ja")
    with headless_chrome.HeadlessChrome() as ch:
        ch.open(headless_chrome.file_url(page) + "?tab=field&lang=ja", width=900, height=900)
        ch.wait_for('window.__viewerExports && window.__viewerExports.paneCSV("field",0,2)!==null')
        assert ch.eval('window.__viewerExports.seriesCSV("field",2)') == want["series_csv"]
        assert ch.eval('window.__viewerExports.paneCSV("field",0,2)') == want["pane_csv"][0]
        got = ch.eval('window.__viewerExports.ply("field",0,2)')
    def vertices(text):
        lines=text.splitlines(); start=lines.index("end_header")+1
        n=int(next(x.split()[-1] for x in lines if x.startswith("element vertex ")))
        return np.asarray([[float(v) for v in x.split()] for x in lines[start:start+n]])
    assert np.allclose(vertices(got), vertices(want["ply"][0]), atol=1e-9)
