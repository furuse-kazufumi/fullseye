"""Numerical gates for the synthetic InSAR lesson."""
from __future__ import annotations
import importlib.util, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location("insar_builder_t",ROOT/"tools"/"build_insar_anim3d.py")
B=importlib.util.module_from_spec(s); s.loader.exec_module(B)
def test_observation_only_unwrap_recovers_subsidence():
    r=B.compute(); g=B.gates(r); assert r["wrapped"].shape==(B.N,B.N)
    assert g["rms_mm"]<g["rms_bound_mm"] and g["centre_mm"]<4 and g["fringe_mm"]<12
    assert r["s1"].shape[-2:]==(4,4) and r["s2"].shape==r["s1"].shape
    assert r["interferogram"].shape==(B.N,B.N)
    assert r["h_2pi"]==B.LAM*r["slant_range"]*__import__("math").sin(__import__("math").radians(B.INCIDENCE_DEG))/(2*B.BPERP_M)
def test_stronger_atmosphere_really_increases_error(): assert B.gates(B.compute())["atmosphere_growth_mm"]>2
def test_single_explicit_limit_row():
    tabs=B.build_spec()["tabs"]; assert len(tabs)==4
    failed=[c for t in tabs for c in t["checks"] if not c["ok"]]
    assert len(failed)==2
    assert any("RMS increases" in c["result"]["en"] for c in failed)
    assert any("of pixels" in c["result"]["en"] for c in failed)
