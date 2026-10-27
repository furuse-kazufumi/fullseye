"""コンクリート浮きの赤外線サーモグラフィ教材の物理・測定・8 言語門。"""
from __future__ import annotations
import hashlib, importlib.util, json, os, re, sys
import numpy as np
import pytest

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILDER="build_thermo_anim3d"
PAGE=os.path.join(ROOT,"docs","view2026","anim3d","thermo_delamination_anim3d.html")

def _load(name):
    p=os.path.join(ROOT,"tools",name+".py"); s=importlib.util.spec_from_file_location(name+"_thermo_t",p)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

@pytest.fixture(scope="module")
def built():
    if ROOT not in sys.path: sys.path.insert(0,ROOT)
    B=_load(BUILDER); r=B.compute(); g=B.gates(r); return B,r,g,B.build_spec(r,g)

def test_heat_solution_detection_and_depth_are_computed(built):
    B,r,g,_=built
    assert g["fd_rel"] < .08
    assert r["cube"].shape==(len(B.TIMES),48,48)
    assert r["frames"].shape==(len(B.TIMES),48,48,3)
    assert g["detected"]==3 and not g["deep_detected"]
    assert g["position_mm"]<8 and g["diameter_mm"]<14 and g["depth_mm"]<5
    assert g["linearity"]>.97
    assert np.std(r["cube"]-r["residual"])>0, "局所背景を画像から推定していない"
    assert np.all(np.diff(g["contrast_snr"])<0), g["contrast_snr"]
    assert np.all(g["contrast_snr"][:3]>4) and g["contrast_snr"][3]<4

def test_depth_conversion_uses_a_separate_calibration_simulation(built):
    B,r,_g,_=built
    assert np.array_equal(r["cal_depth"],np.array([10.,18.,30.]))
    assert not np.intersect1d(r["cal_depth"],B.DEPTHS_MM).size
    assert len(r["cal_tmax"])==3 and np.all(np.diff(r["cal_tmax"])>0)
    independent=np.polyfit(r["cal_tmax"],r["cal_depth"]**2,1)
    assert np.allclose(r["fit"],independent)
    evaluation_t=np.array([m["tmax"] for m in r["matches"] if m is not None])
    assert not np.array_equal(evaluation_t,r["cal_tmax"])

def test_learning_flow_and_honest_limit(built):
    _B,_r,_g,spec=built; tabs=spec["tabs"]
    assert [t["id"] for t in tabs]==["why","movie","depth","limit"]
    assert all(len(t["t"])==45 and len(t["checks"])>=5 for t in tabs)
    assert all(all(c["ok"] for c in t["checks"]) for t in tabs[:3])
    failed=[c for c in tabs[-1]["checks"] if not c["ok"]]
    assert len(failed)==1 and "38 mm" in failed[0]["what"]["en"]

def test_two_language_page_is_small_and_public_safe(built):
    B,_r,_g,spec=built; html=B.pv._build_html(spec,["ja","en"])
    assert len(html.encode())<600_000
    assert "48\\u00d748\\u00d761" in html and "5 mK" in html
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
