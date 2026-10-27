# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""スタートラッカーの動く 3-D の物理門・ページ門。"""
from __future__ import annotations
import importlib.util
import json
import os
import re
import sys
import numpy as np
import pytest

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILDER="build_startrk_anim3d"
PAGE=os.path.join(ROOT,"docs","view2026","anim3d","star_tracker_anim3d.html")

def _load(name, folder="tools"):
    p=os.path.join(ROOT,folder,name+".py"); s=importlib.util.spec_from_file_location(name+"_startrk_t",p)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

@pytest.fixture(scope="module")
def built():
    if ROOT not in sys.path: sys.path.insert(0,ROOT)
    B=_load(BUILDER); r=B.compute(); g=B.gates(r); return B,r,g,B.build_spec(r,g)

def test_image_detection_is_noisy_subpixel_op_path(built):
    _B,r,g,_=built
    assert r["image"].shape==(128,128) and g["n_stars"]>=8
    assert np.any(np.abs(r["truth_px"]-np.rint(r["truth_px"]))>.05)
    assert 0 < g["centroid_median_px"] < .1
    assert g["n_detections"]==g["n_stars"]+2

def test_matching_searches_shuffled_full_catalogue_and_rejects_hot_pixels(built):
    _B,r,g,_=built
    assert g["match_accuracy"]==1.0 and g["mismatch_count"]==0
    genuine=r["truth_rows"]>=0
    assert g["catalogue_size"]==196
    assert not np.array_equal(r["truth_rows"][genuine],np.arange(g["n_stars"]))
    assert np.array_equal(r["match"][genuine],r["truth_rows"][genuine])
    assert np.all(r["match"][~genuine]==-1)
    assert g["false_rejected"]==g["n_false"]==2 and g["false_kept"]==0

def test_attitude_is_below_pixel_angle_and_kabsch_has_independent_crosscheck(built):
    _B,_r,g,_=built
    assert 0 < g["attitude_error_deg"] < g["angular_pixel_deg"]
    assert g["kabsch_svd_max_difference"] < 1e-12

def test_learning_flow_checks_and_limit_are_structural(built):
    _B,_r,_g,spec=built; tabs=spec["tabs"]
    assert [t["id"] for t in tabs]==["fov","detect","attitude","limits"]
    assert tabs[:3][0]["badge"]=="passed" and tabs[-1]["badge"]=="limit"
    for t in tabs:
        assert set(t["lesson"])=={"question","choices","answer","explain","formula","limit"}
        assert len(t["checks"])>=3 and len(t["t"])>=40
    assert all(c["ok"] for t in tabs[:3] for c in t["checks"])
    failed=[c for c in tabs[-1]["checks"] if not c["ok"]]
    assert len(failed)==1 and "Sun/Moon" in failed[0]["what"]["en"]

def test_page_is_small_synthetic_and_has_no_public_urls_or_names(built):
    B,_r,_g,spec=built; html=B.pv._build_html(spec,["ja","en"])
    assert len(html.encode())<3.3e6
    assert "synth_starfield" in html and "star_detect" in html and "kabsch" in html
    assert "entirely seeded synthetic" in html
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
