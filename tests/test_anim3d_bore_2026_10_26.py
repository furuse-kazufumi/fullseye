# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ボアスコープの動く 3-D の物理門・翻訳門。"""
from __future__ import annotations
import importlib.util, json, os, re, sys
import numpy as np
import pytest

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILDER="build_bore_anim3d"
PAGE=os.path.join(ROOT,"docs","view2026","anim3d","borescope_anim3d.html")

def _load(name):
    p=os.path.join(ROOT,"tools",name+".py"); s=importlib.util.spec_from_file_location(name+"_bore_t",p)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

@pytest.fixture(scope="module")
def built():
    if ROOT not in sys.path: sys.path.insert(0,ROOT)
    B=_load(BUILDER); r=B.compute(); g=B.gates(r); return B,r,g,B.build_spec(r,g)

def test_abcd_op_and_sequential_trace_agree(built):
    B,r,g,_=built
    assert len(r["stages"])==6 and len(r["matrix_error"])==6
    assert g["image_matrix_error"]<1e-9
    assert np.allclose(np.abs(r["magnification"]),1,atol=1e-12)
    for n,x in zip(r["stages"],r["image_x"]):
        elements=[]
        for _ in range(n): elements += [("free",2*B.F),("lens",B.F),("free",2*B.F),("lens",B.F)]
        assert x==pytest.approx(B._image_crossings(elements)[-1],abs=1e-12)

def test_lagrange_invariant_is_preserved_at_every_surface(built):
    _B,r,g,_=built
    assert len(r["invariant_error"])==6
    assert g["invariant_error"]<1e-9

def test_vignetting_comes_from_fixed_ray_bundle(built):
    _B,r,g,_=built
    assert len(r["transmission"])==6 and np.all((r["transmission"]>0)&(r["transmission"]<1))
    assert g["vignetting_stage_span"]<1e-12
    assert g["vignetting_error"]<.02

def test_fibre_resolution_is_measured_from_synthetic_samples(built):
    B,r,g,_=built
    assert len(r["contrast"])>=12
    assert r["fiber_images"].shape[0]==len(r["periods_um"]) and r["fiber_images"].shape[-1]==3
    assert np.ptp(r["contrast"])>.25
    assert g["fiber_resolution_error_um"]<=B.PITCH_UM
    assert not g["fiber_resolution_um"]==pytest.approx(2*B.PITCH_UM)

def test_sub_nyquist_chart_really_loses_contrast_in_reconstructed_image(built):
    B,r,_g,_=built
    sub=r["periods_um"] < np.sqrt(3)*B.PITCH_UM
    assert np.count_nonzero(sub)>=2
    assert np.max(r["contrast"][sub]) < .5
    assert np.max(r["closed_contrast"][sub]) < .5

def test_lesson_checks_and_limit_are_structural(built):
    _B,_r,_g,spec=built; tabs=spec["tabs"]
    assert [t["id"] for t in tabs]==["inside","relay","invariant","fiber"]
    assert [t["badge"] for t in tabs]==["passed","passed","passed","limit"]
    for t in tabs:
        assert set(t["lesson"])=={"question","choices","answer","explain","formula","limit"}
        assert len(t["checks"])>=4 and len(t["t"])>=6
    failed=[[c for c in t["checks"] if not c["ok"]] for t in tabs]
    assert failed[:3]==[[],[],[]] and len(failed[3])==2

def test_page_is_small_synthetic_and_public_safe(built):
    B,_r,_g,spec=built; html=B.pv._build_html(spec,["ja","en"])
    assert len(html.encode())<600_000 and "lessonTop" in html and "checksHTML" in html
    assert "entirely synthetic" in html.lower()
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
