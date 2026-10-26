# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""衛星 GSD と回折の動く 3-D の物理門・ページ門。"""
from __future__ import annotations
import importlib.util
import json
import math
import os
import re
import sys
import numpy as np
import pytest

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILDER="build_satgsd_anim3d"
PAGE=os.path.join(ROOT,"docs","view2026","anim3d","satellite_gsd_anim3d.html")

def _load(name, folder="tools"):
    p=os.path.join(ROOT,folder,name+".py"); s=importlib.util.spec_from_file_location(name+"_satgsd_t",p)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

@pytest.fixture(scope="module")
def built():
    if ROOT not in sys.path: sys.path.insert(0,ROOT)
    B=_load(BUILDER); r=B.compute(); g=B.gates(r); return B,r,g,B.build_spec(r,g)

def test_gsd_matches_closed_form_and_one_pixel_projection(built):
    B,r,g,_=built
    assert len(r["heights"])==49
    for h,got in zip(r["heights"],r["gsd"]):
        assert abs(got-B.PIXEL_UM*1e-6*h*1e3/B.FOCAL_M)<1e-12
    assert g["gsd_formula_vs_pixel_m"]<1e-12
    assert abs(r["gsd"][0]-.25)<1e-12 and abs(r["gsd"][-1]-22.5)<1e-12

def test_airy_radius_op_matches_rayleigh_closed_form(built):
    B,r,g,_=built
    assert len(r["apertures"])==49
    assert g["rayleigh_max_err_m"]<1e-9
    for d,op_um in zip(r["apertures"],r["op_r"]):
        assert abs(op_um-1.22*(B.LAM_NM*1e-3)*(B.FOCAL_M/d))<1e-12
        assert abs(op_um*1e-6*400e3/B.FOCAL_M-B.rayleigh_ground_m(400,d))<1e-12

def test_mtf50_improves_monotonically_with_aperture(built):
    _B,r,g,_=built
    assert len(r["mtf50"])>=40
    assert np.all(np.diff(r["mtf50"])<0)
    assert g["mtf50_monotonic_residual_m"]<1e-12

def test_diffraction_blur_is_op_output_and_contrast_recovers(built):
    _B,r,g,_=built
    assert r["blur"].shape==(49,96,320)
    assert g["contrast_start"]<.1 and g["contrast_end"]>.9

def test_learning_flow_checks_and_limit_are_structural(built):
    _B,_r,g,spec=built
    tabs=spec["tabs"]
    assert [t["id"] for t in tabs]==["height","aperture","cross","sign"]
    assert tabs[0]["badge"]=="passed" and tabs[-1]["badge"]=="limit"
    for t in tabs:
        assert set(t["lesson"])=={"question","choices","answer","explain","formula","limit"}
        assert len(t["checks"])>=3 and len(t["t"])>=40
        assert t["axis"]["values"].shape==(len(t["t"]),)
    failed={t["id"]:[c for c in t["checks"] if not c["ok"]] for t in tabs}
    assert failed["height"]==failed["aperture"]==failed["cross"]==[]
    assert len(failed["sign"])==1 and "atmosphere" in failed["sign"][0]["what"]["en"]
    assert abs(g["seeing_floor_m"]-2)<1e-12

def test_page_is_small_synthetic_and_has_no_public_urls_or_names(built):
    B,_r,_g,spec=built
    html=B.pv._build_html(spec,["ja","en"])
    assert len(html.encode())<3.3e6
    assert "lessonTop" in html and "checksHTML" in html and "diffraction_blur" in html
    assert "Entirely synthetic" in html and "specific vehicle" in html
    assert "http://" not in html and "https://" not in html and "**" not in html

I18N=_load("anim3d_i18n")

@pytest.fixture(scope="module")
def spec_table():
    s=I18N.pick_spec(I18N.capture_specs(I18N.example_script(BUILDER)),None)
    return s,I18N.load_table(BUILDER)

def test_i18n_table_has_no_missing_or_unused_entries(spec_table):
    s,t=spec_table
    assert len({d["en"] for _,d in I18N.iter_texts(s)})>50
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
