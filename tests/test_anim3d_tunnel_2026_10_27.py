# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""トンネルひび割れの動く 3-D の計測門と 8 言語ページ門。"""
from __future__ import annotations
import importlib.util
import json
import os
import re
import sys
import numpy as np
import pytest

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILDER="build_tunnel_anim3d"
PAGE=os.path.join(ROOT,"docs","view2026","anim3d","tunnel_crack_anim3d.html")

def _load(name,folder="tools"):
    p=os.path.join(ROOT,folder,name+".py"); s=importlib.util.spec_from_file_location(name+"_tunnel_t",p)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

@pytest.fixture(scope="module")
def built():
    if ROOT not in sys.path: sys.path.insert(0,ROOT)
    B=_load(BUILDER); r=B.compute(); g=B.gates(r); return B,r,g,B.build_spec(r,g)

def test_fixed_physical_field_resolution_trials_use_real_ops(built):
    B,r,_g,_=built
    assert len(B.PIXEL_MM)==19 and B.PIXEL_MM[0]==1.0 and B.PIXEL_MM[-1]==.1
    assert np.allclose(np.diff(B.PIXEL_MM),-.05)
    assert len(r["images"])==len(r["response"])==len(r["skeleton"])==19
    assert all(x.shape==(256,256) for x in r["images"])
    assert r["recall"][0]<.7 and r["recall"][-1]>.9

def test_length_false_positive_width_and_90_percent_gates_are_measured(built):
    B,r,g,_=built
    assert r["truth_length"]>20
    assert np.all(r["false_length"]>0)
    assert g["recall_best"]>=.9
    assert 0 < g["width_error_mm"] < g["width_limit_mm"]
    assert abs(r["width"][-1]-B.TRUE_WIDTH_MM)<g["width_limit_mm"]
    assert g["measured_90_mm"]==.25
    assert g["estimated_90_mm"]==B.TRUE_WIDTH_MM/B.DETECT_MIN_FILL==.25
    assert g["threshold_delta_mm"]<g["threshold_limit_mm"]<.05
    assert r["best_width_rows"]>150 and r["best_bg_sigma"]>0

def test_learning_flow_checks_and_limit_are_structural(built):
    _B,_r,_g,spec=built; tabs=spec["tabs"]
    assert [t["id"] for t in tabs]==["unwrap","resolution","width","limit"]
    assert tabs[-1]["badge"]=="limit"
    for t in tabs:
        assert set(t["lesson"])=={"question","choices","answer","explain","formula","limit"}
        assert len(t["checks"])>=3 and len(t["t"])==49
    failed=[[c for c in t["checks"] if not c["ok"]] for t in tabs]
    assert failed[:3]==[[],[],[]]
    assert len(failed[-1])==1 and "stains" in failed[-1][0]["what"]["en"]

def test_page_is_small_synthetic_and_url_free(built):
    B,_r,_g,spec=built; html=B.pv._build_html(spec,["ja","en"])
    assert len(html.encode())<3.3e6
    assert "sk_frangi" in html and "sk_skeleton" in html
    assert "Entirely synthetic" in html
    assert "http://" not in html and "https://" not in html and "**" not in html

I18N=_load("anim3d_i18n")

@pytest.fixture(scope="module")
def spec_table():
    s=I18N.pick_spec(I18N.capture_specs(I18N.example_script(BUILDER)),None)
    return s,I18N.load_table(BUILDER)

def test_i18n_table_has_no_missing_or_unused_entries(spec_table):
    s,t=spec_table
    assert len({d["en"] for _,d in I18N.iter_texts(s)})>40
    problems,unused=I18N.audit(s,t)
    assert problems==[] and unused==[]

def test_committed_page_is_rebuilt_eight_language_page(spec_table):
    s,t=spec_table
    with open(PAGE,encoding="utf-8") as f: html=f.read()
    data=json.loads(re.search(r"const D = (\{.*?\});\nconst \$ = ",html,re.S).group(1))
    assert data["langs"]==list(I18N.LANGS)
    want=I18N.pv._build_html(I18N.translate(s,t),list(I18N.LANGS),detect_lang=True)
    I18N.check_same_page(html,want,PAGE,BUILDER)
    assert os.path.getsize(PAGE)<3.3e6
    assert "http://" not in html and "https://" not in html
