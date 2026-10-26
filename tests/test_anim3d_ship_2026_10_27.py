"""合成船型の排水量・復原性教材の数値門。"""
from __future__ import annotations
import importlib.util
import pathlib
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]

def _load():
    s=importlib.util.spec_from_file_location("ship_builder_t",ROOT/"tools"/"build_ship_anim3d.py")
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

B=_load()

def test_box_mesh_displacement_buoyancy_centre_and_gm_match_closed_form():
    r=B.compute(); g=B.gates(r)
    assert g["box_relative_error"] < 1e-9
    assert np.isclose(r["box"]["gm_closed"], 2/2+8**2/(12*2)-1.7)

def test_synthetic_hull_draft_search_matches_weight():
    r=B.compute(); g=B.gates(r)
    assert len(r["angles"]) == 49
    assert len(r["volumes"]) == 49
    assert g["displacement_relative_error"] < 1e-6
    assert np.all(r["volumes"] > 0)

def test_small_angle_gz_slope_matches_mesh_waterplane_gm():
    r=B.compute(); g=B.gates(r)
    assert r["hydro"]["Iwp"] > 0 and r["hydro"]["BM"] > 0
    assert g["small_angle_gm_relative_error"] < .02
    assert r["gz"][1] > 0

def test_learning_flow_and_limit_row_are_structural():
    r=B.compute(); g=B.gates(r); spec=B.build_spec(r,g)
    tabs=spec["tabs"]
    assert len(tabs) == 4
    assert [t["id"] for t in tabs] == ["float","buoyancy","gz","limit"]
    assert all(len(t["t"]) == 49 and len(t["checks"]) >= 3 for t in tabs)
    failed=[[c for c in t["checks"] if not c["ok"]] for t in tabs]
    assert failed[:3] == [[],[],[]]
    assert len(failed[3]) == 1 and "centre of gravity" in failed[3][0]["what"]["en"]
    assert g["high_gm"] < 0
