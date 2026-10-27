from __future__ import annotations

import importlib.util
import json
import os
import re
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILDER = "build_catenary_anim3d"
PAGE = os.path.join(ROOT, "docs", "view2026", "anim3d", "catenary_wear_anim3d.html")


def load(name):
    spec = importlib.util.spec_from_file_location(name + "_catenary_t", os.path.join(ROOT, "tools", name + ".py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def test_image_measurement_and_geometry_gates():
    B=load(BUILDER); result=B.compute(); r,base=result; g=B.gates(result)
    assert g["rows"] == 36
    assert g["width_max_error_mm"] < g["width_tolerance_mm"]
    assert g["height_max_error_mm"] < g["height_tolerance_mm"]
    assert g["stagger_width_max_diff_mm"] < g["stagger_tolerance_mm"]
    assert np.ptp(r["centre_px"]) > 20
    assert np.ptp(base["centre_px"]) < 0.4
    assert np.allclose(B.remaining_height(r["measured_width"]), r["measured_height"])


def test_renderer_starts_from_section_geometry_and_changes_off_axis():
    B=load(BUILDER); rng=np.random.default_rng(4)
    height=11.82
    row0,width0=B._render_section(height,0.0,rng)
    row1,width1=B._render_section(height,3.0,np.random.default_rng(4))
    want=2*np.sqrt(B.RADIUS_MM**2-(2*B.RADIUS_MM-height-B.RADIUS_MM)**2)
    assert len(row0) == 240 and len(row1) == 240
    assert abs(width0-want) < 1e-12 and abs(width1-want) < 1e-12
    # Recentring does not make the off-axis image identical: finite viewing rays
    # and surface normals change its sampled reflectance, not merely its position.
    shift=int(round((np.argmax(row1)-np.argmax(row0))))
    assert np.sqrt(np.mean((row0-np.roll(row1,-shift))**2)) > 0.1


def test_page_structure_checks_and_size():
    B=load(BUILDER); result=B.compute(); g=B.gates(result); spec=B.build_spec(result,g)
    tabs=spec["tabs"]
    assert len(tabs) == 4
    assert [t["id"] for t in tabs] == ["contact","camera","map","limit"]
    failed={t["id"]:[c for c in t["checks"] if not c["ok"]] for t in tabs}
    assert failed["contact"] == []
    assert failed["camera"] == []
    assert failed["map"] == []
    assert len(failed["limit"]) == 1
    for tab in tabs:
        assert set(tab["lesson"]) == {"question","choices","answer","explain","formula","limit"}
        assert len(tab["checks"]) >= 3
    html=B.pv._build_html(spec,["ja","en"])
    assert len(html.encode("utf-8")) < 600_000
    assert "**" not in html and "http://" not in html and "https://" not in html


def test_i18n_table_and_committed_page_match():
    I=load("anim3d_i18n")
    spec=I.pick_spec(I.capture_specs(I.example_script(BUILDER)),None); table=I.load_table(BUILDER)
    problems,unused=I.audit(spec,table); assert problems == [] and unused == []
    with open(PAGE,encoding="utf-8") as f: html=f.read()
    want=I.pv._build_html(I.translate(spec,table),list(I.LANGS),detect_lang=True)
    I.check_same_page(html,want,PAGE,BUILDER)
    data=json.loads(re.search(r"const D = (\{.*?\});\nconst \$ = ",html,re.S).group(1))
    assert data["langs"] == list(I.LANGS)
    assert len(html.encode("utf-8")) < 600_000
