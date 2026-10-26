# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""会場の日影 3-D 教材の物理門と構造門。"""
from __future__ import annotations
import importlib.util
import pathlib
import sys
import numpy as np
import pytest

ROOT=pathlib.Path(__file__).resolve().parents[1]

def _load():
    p=ROOT/"tools"/"build_shadow_anim3d.py"
    s=importlib.util.spec_from_file_location("build_shadow_anim3d_test",p)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

@pytest.fixture(scope="module")
def built():
    if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
    B=_load(); r=B.compute(); g=B.gates(r); return B,r,g,B.build_spec(r,g)

def test_solar_closed_form_matches_independent_enu_rotation(built):
    _B,r,g,_=built
    assert len(r["times"])==49
    assert g["solar_altitude_max_err_deg"]<1e-9
    assert g["solar_azimuth_max_err_deg"]<1e-9
    assert np.argmax(r["closed"][:,0])==24

def test_box_shadow_length_and_area_match_closed_forms(built):
    _B,_r,g,_=built
    assert g["box_shadow_length_rel_err"]<1e-9
    assert g["box_shadow_area_rel_err"]<1e-9

def test_real_lod2_noon_projection_obeys_highest_point_bound(built):
    _B,r,g,_=built
    assert r["V"].shape==(3575,3) and r["F"].shape==(7123,3)
    assert g["venue_noon_bound_residual_m"]<=1e-9
    assert 0 < g["max_shadow_hours"] <= 8.0

def test_learning_flow_and_computed_checks(built):
    _B,_r,_g,spec=built
    tabs=spec["tabs"]
    assert [t["id"] for t in tabs]==["day","length","duration","limit"]
    assert tabs[-1]["badge"]=="limit"
    for tab in tabs:
        assert len(tab["t"])==49 and len(tab["checks"])>=4
        assert set(tab["lesson"])=={"question","choices","answer","explain","formula","limit"}
    failed=[[c for c in t["checks"] if not c["ok"]] for t in tabs]
    assert failed[:3]==[[],[],[]]
    assert len(failed[3])==1 and "terrain" in failed[3][0]["what"]["en"]

def test_page_budget_and_allowed_source_url_only(built):
    B,_r,_g,spec=built
    html=B.pv._build_html(spec,["ja","en"])
    assert len(html.encode("utf-8"))<3_300_000
    urls=[x.split('"',1)[0] for x in html.split("https://")[1:]]
    assert len(urls)==2  # one allowed source, repeated for ja/en credit
    assert all("geospatial.jp/ckan/dataset/plateau-14100-yokohama-city-2020" in u for u in urls)
