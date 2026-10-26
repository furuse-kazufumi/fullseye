# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""レール光切断 3-D 教材の物理門とページ門。"""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
import re
import sys
import numpy as np
import pytest

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILDER="build_rail_anim3d"
PAGE=os.path.join(ROOT,"docs","view2026","anim3d","rail_light_section_anim3d.html")

def _load(name, folder="tools"):
    p=os.path.join(ROOT,folder,name+".py"); s=importlib.util.spec_from_file_location(name+"_rail_t",p)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

@pytest.fixture(scope="module")
def built():
    if ROOT not in sys.path: sys.path.insert(0,ROOT)
    B=_load(BUILDER); r=B.compute(); g=B.gates(r); return B,r,g,B.build_spec(r,g)

def test_noisy_subpixel_line_recovers_section_with_pixel_derived_gate(built):
    B,r,g,_=built
    assert r["detected"].shape==(49,321)
    assert np.count_nonzero(np.abs(r["detected"]-np.rint(r["detected"]))>.01)>1000
    assert g["profile_limit_mm"]==pytest.approx(1000**2/(B.FX*B.BASELINE_MM)*.05)
    assert g["profile_rms_mm"]<g["profile_limit_mm"]

def test_wear_gauge_and_two_independent_triangulation_paths(built):
    B,r,g,_=built
    assert len(r["wear"])==49 and len(r["gauge_est"])==49
    assert g["wear_error_mm"]<.10
    assert g["wear_fit_delta_mm"]>0
    assert g["gauge_error_mm"]<g["gauge_limit_mm"]
    assert g["two_path_error_mm"]<1e-12
    assert np.max(r["wear"])==pytest.approx(B.WEAR_TRUE_MM)
    # Gauge comes from two reconstructed profile points, calibrated only by the
    # first scan; it is not truth plus random noise.
    assert np.allclose(r["gauge_est"]-B.GAUGE_TRUE_MM,r["raw_gauge"]-r["raw_gauge"][0])
    assert np.allclose(r["gauge_truth"],B.GAUGE_TRUE_MM+r["widen"])
    assert not np.allclose(r["gauge_est"],r["gauge_truth"])
    assert np.max(np.abs(r["recovered_wear_free"]-r["recovered_wear_fit"]))>.05

def test_learning_flow_and_limit_row_are_structural(built):
    _B,_r,_g,spec=built
    tabs=spec["tabs"]
    assert [t["id"] for t in tabs]==["line","triangulation","wear","limit"]
    assert all(len(t["t"])==49 and len(t["checks"])>=4 for t in tabs)
    assert all(all(c["ok"] for c in t["checks"]) for t in tabs[:3])
    failed=[c for c in tabs[-1]["checks"] if not c["ok"]]
    assert len(failed)==1 and "glare" in failed[0]["what"]["en"]

def test_page_is_small_synthetic_and_has_no_public_urls_or_names(built):
    B,_r,_g,spec=built
    html=B.pv._build_html(spec,["ja","en"])
    assert len(html.encode())<3.3e6
    assert "triangulate_column" in html and "Entirely synthetic" in html
    assert "http://" not in html and "https://" not in html and "**" not in html

I18N=_load("anim3d_i18n")

@pytest.fixture(scope="module")
def spec_table():
    s=I18N.pick_spec(I18N.capture_specs(I18N.example_script(BUILDER)),None)
    return s,I18N.load_table(BUILDER)

def test_i18n_table_has_no_missing_or_unused_entries(spec_table):
    s,t=spec_table
    assert len({d["en"] for _,d in I18N.iter_texts(s)})>=50
    problems,unused=I18N.audit(s,t)
    assert problems==[] and unused==[]

def test_committed_page_is_rebuilt_twice_as_same_eight_language_page(spec_table):
    s,t=spec_table
    with open(PAGE,encoding="utf-8") as f: html=f.read()
    data=json.loads(re.search(r"const D = (\{.*?\});\nconst \$ = ",html,re.S).group(1))
    assert data["langs"]==list(I18N.LANGS)
    want1=I18N.pv._build_html(I18N.translate(s,t),list(I18N.LANGS),detect_lang=True)
    want2=I18N.pv._build_html(I18N.translate(s,t),list(I18N.LANGS),detect_lang=True)
    I18N.check_same_page(html,want1,PAGE,BUILDER)
    assert hashlib.sha256(want1.encode()).hexdigest()==hashlib.sha256(want2.encode()).hexdigest()
