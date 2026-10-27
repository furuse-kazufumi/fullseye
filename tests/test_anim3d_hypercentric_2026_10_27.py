"""ハイパーセントリックレンズ教材の物理門・ページ門。"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import re
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
BUILDER = "build_hypercentric_anim3d"
PAGE = ROOT / "docs" / "view2026" / "anim3d" / "hypercentric_lens_anim3d.html"


def _load(name):
    s = importlib.util.spec_from_file_location(name + "_hyper_t", ROOT / "tools" / (name + ".py"))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
B = _load(BUILDER)
I18N = _load("anim3d_i18n")


def test_pupil_op_matches_independent_abcd_path():
    r = B.compute(); g = B.gates(r)
    assert g["pupil_error_mm"] < 1e-9
    assert abs(r["pupil_op"][0] - 40/3) < 1e-12
    assert np.isneginf(r["pupil_op"][1])
    assert abs(r["pupil_op"][2] + 200) < 1e-12
    assert len(r["chief"]) == 3
    for points in r["chief"]:
        assert points.shape[1] == 3
        assert abs(points[2, 1]) < 1e-9


def test_abcd_gate_fails_when_matrix_path_is_perturbed(monkeypatch):
    original = B.optics.abcd_matrix
    def wrong(elements):
        m = original(elements).copy(); m[0, 1] += 1.0; return m
    monkeypatch.setattr(B.optics, "abcd_matrix", wrong)
    r = B.compute(); g = B.gates(r)
    assert g["pupil_error_mm"] > 1e-3


def test_all_three_chief_rays_use_trace_op(monkeypatch):
    original = B.rt.trace_rays; calls = []
    def recording(*args, **kwargs):
        calls.append(1); return original(*args, **kwargs)
    monkeypatch.setattr(B.rt, "trace_rays", recording)
    B.compute()
    assert len(calls) == 3


def test_image_measurement_and_telecentric_zero_are_pixel_based():
    r = B.compute(); g = B.gates(r)
    assert r["images"].shape == (49, 192, 192, 3)
    assert g["image_band_error_px"] < 0.5
    assert 0 < g["telecentric_band_px"] <= 1.0
    assert len(r["measured_band"]) == 49
    assert np.all(r["measured_band"] > 0)
    assert np.max(np.abs(r["measured_centers"] - np.array([96.37, 95.79]))) < 0.5
    xy, faces = r["render_meshes"][0]
    assert xy.shape == (257, 2) and faces.shape == (384, 3)


def test_renderer_is_independent_of_closed_form_band(monkeypatch):
    baseline = B.compute()
    monkeypatch.setattr(B, "side_band_mm", lambda _p: 1.0)
    perturbed = B.compute(); g = B.gates(perturbed)
    assert np.array_equal(baseline["images"], perturbed["images"])
    assert g["image_band_error_px"] > 1.0


def test_learning_structure_and_limit_row():
    r = B.compute(); g = B.gates(r); spec = B.build_spec(r, g)
    tabs = spec["tabs"]
    assert len(tabs) == 4
    assert [t["id"] for t in tabs] == ["compare", "pupil", "image", "limit"]
    assert [t["badge"] for t in tabs] == ["passed", "passed", "passed", "limit"]
    assert [len(t["t"]) for t in tabs] == [49, 49, 13, 13]
    for tab in tabs:
        assert set(tab["lesson"]) == {"question", "choices", "answer", "explain", "formula", "limit"}
        assert len(tab["checks"]) >= 3
    assert tabs[2]["panes"][0]["frames"].shape == (13, 120, 120, 3)
    assert len(r["images"]) == len(r["measured_band"]) == 49
    failed = [c for c in tabs[-1]["checks"] if not c["ok"]]
    assert len(failed) == 1 and "distortion" in failed[0]["what"]["en"]


def test_eight_language_page_is_small_and_byte_reproducible():
    spec = I18N.pick_spec(I18N.capture_specs(I18N.example_script(BUILDER)), None)
    table = I18N.load_table(BUILDER)
    problems, unused = I18N.audit(spec, table)
    assert problems == [] and unused == [] and len(table["strings"]) >= 50
    html = PAGE.read_text(encoding="utf-8")
    want = I18N.pv._build_html(I18N.translate(spec, table), list(I18N.LANGS), detect_lang=True)
    I18N.check_same_page(html, want, PAGE, BUILDER)
    want2 = I18N.pv._build_html(I18N.translate(spec, table), list(I18N.LANGS), detect_lang=True)
    assert hashlib.sha256(want.encode()).digest() == hashlib.sha256(want2.encode()).digest()
    assert len(html.encode()) <= 600_000
    data = json.loads(re.search(r"const D = (\{.*?\});\nconst \$ = ", html, re.S).group(1))
    assert data["langs"] == list(I18N.LANGS)
    payload = html.split("const D = ", 1)[1].split("\nconst $ = ", 1)[0]
    assert not re.search(r"https?://|www\.|[A-Z]:[/\\]", payload)
