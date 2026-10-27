"""橋梁 DIC の動く 3-D 教材の測定門と 8 言語ページ門。"""
from __future__ import annotations
import hashlib, importlib.util, json, os, re, sys
import numpy as np
import pytest

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILDER="build_bridge_dic_anim3d"
PAGE=os.path.join(ROOT,"docs","view2026","anim3d","bridge_dic_anim3d.html")

def _load(name):
    p=os.path.join(ROOT,"tools",name+".py"); s=importlib.util.spec_from_file_location(name+"_bridge_t",p)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

@pytest.fixture(scope="module")
def built():
    if ROOT not in sys.path: sys.path.insert(0,ROOT)
    B=_load(BUILDER); r=B.compute(); g=B.gates(r); return B,r,g,B.build_spec(r,g)

def test_dic_measures_rendered_images_not_truth_plus_noise(built):
    B,r,g,_=built
    assert len(r["images"])==B.FRAMES==31
    assert r["images"].shape[1:]==(84,160)
    assert r["reference_frame"].shape==r["reference"].shape
    assert not np.allclose(r["reference_frame"],r["reference"])
    assert np.count_nonzero(np.abs(r["measured_mm"]-r["true_mm"])>.01)>10
    assert g["rmse_mm"]<g["limit_mm"]
    assert g["peak_frame_error"]<=1

def test_noise_grid_is_fixed_and_spread_has_expected_slope(built):
    _B,_r,g,_=built
    assert len(g["noise_sigmas"])==len(g["noise_spread"])==len(g["noise_predicted"])==5
    assert np.all(np.diff(g["noise_sigmas"])>0)
    assert np.all(g["noise_spread"]>0)
    assert np.all(g["noise_predicted"]>0)
    assert abs(g["noise_slope"]-g["theory_slope"])<.3
    assert g["theory_slope"]==pytest.approx(1.0)
    assert g["limit_mm"]==pytest.approx(g["systematic_rms_mm"]+3*g["nominal_spread_mm"])
    assert g["systematic_rms_mm"]>0 and g["nominal_spread_mm"]>0

def test_learning_flow_and_one_honest_limit(built):
    _B,_r,_g,spec=built; tabs=spec["tabs"]
    assert [t["id"] for t in tabs]==["bridge","dic","scale","limit"]
    assert all(len(t["t"])==31 and len(t["checks"])>=3 for t in tabs)
    assert all(all(c["ok"] for c in t["checks"]) for t in tabs[:3])
    failed=[c for c in tabs[-1]["checks"] if not c["ok"]]
    assert len(failed)==1 and "shimmer" in failed[0]["what"]["en"]

def test_two_language_page_is_small_and_public_safe(built):
    B,_r,_g,spec=built; html=B.pv._build_html(spec,["ja","en"])
    assert len(html.encode())<600_000
    assert "find_ncc_model" in html and "Entirely synthetic" in html
    assert "http://" not in html and "https://" not in html and "**" not in html

I18N=_load("anim3d_i18n")

def test_i18n_and_committed_page_are_byte_exact_twice():
    spec=I18N.pick_spec(I18N.capture_specs(I18N.example_script(BUILDER)),None); table=I18N.load_table(BUILDER)
    assert len({d["en"] for _,d in I18N.iter_texts(spec)})>=45
    problems,unused=I18N.audit(spec,table); assert problems==[] and unused==[]
    html=open(PAGE,encoding="utf-8").read()
    data=json.loads(re.search(r"const D = (\{.*?\});\nconst \$ = ",html,re.S).group(1))
    assert data["langs"]==list(I18N.LANGS)
    one=I18N.pv._build_html(I18N.translate(spec,table),list(I18N.LANGS),detect_lang=True)
    two=I18N.pv._build_html(I18N.translate(spec,table),list(I18N.LANGS),detect_lang=True)
    I18N.check_same_page(html,one,PAGE,BUILDER)
    assert hashlib.sha256(one.encode()).digest()==hashlib.sha256(two.encode()).digest()
