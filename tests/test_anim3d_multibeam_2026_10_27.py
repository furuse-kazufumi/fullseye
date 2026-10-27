"""合成マルチビーム測深教材の物理・観測・表示の門。"""
from __future__ import annotations
import importlib.util, inspect, pathlib
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1]
def load():
    s=importlib.util.spec_from_file_location("multibeam_builder_t",ROOT/"tools"/"build_multibeam_anim3d.py")
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
B=load()
def test_grid_mesh_is_fixed_and_qhull_free():
    v1,f1=B.terrain_mesh(); v2,f2=B.terrain_mesh()
    assert v1.shape==(703,3) and f1.shape==(1296,3)
    assert np.array_equal(v1,v2) and np.array_equal(f1,f2)
    assert "ConvexHull" not in inspect.getsource(B) and "Delaunay" not in inspect.getsource(B)
def test_observations_are_inverted_without_true_bottom():
    src=inspect.getsource(B.compute)
    assert "trace_rk4(actual_angle)" in src
    assert "invert_layers(measured_angle,t2/2,ctd,details=True)" in src
    assert "true_roll" not in inspect.getsource(B.invert_layers)
    r=B.compute(); g=B.gates(r)
    assert len(r["angles"])==41 and len(r["twtt"])==41
    assert np.all(r["twtt"]>0)
    assert np.allclose(r["twtt"]/B.DT,np.rint(r["twtt"]/B.DT))
    assert min(r["twtt"][:3].mean(),r["twtt"][-3:].mean())>r["twtt"][18:23].mean()
    assert g["rms"]<g["allowed"] and g["rms"]>0
    assert len(r["uncertainty"])==4
    assert all(x>0 for x in r["uncertainty"])
    assert not np.array_equal(r["true_roll"],r["measured_roll"])
def test_refraction_and_first_order_gate():
    r=B.compute(); g=B.gates(r)
    assert g["invariant"]<1e-9
    assert g["smile_relative_error"]<.25 and abs(g["smile"])>0.1
    assert g["smile_relative_error"]>0
    assert np.max(np.abs(r["straight"]-r["correct"]))>0.1
    edge=np.abs(r["angles"])>=48
    assert np.count_nonzero(edge)>=8
    assert np.all(np.isfinite(r["bend_approx"][edge]))
    assert np.allclose(r["bend_approx"],r["range_term"]+r["angle_term"])
def test_rk4_ray_does_not_construct_direction_from_invariant():
    src=inspect.getsource(B.trace_rk4)
    assert "q*c" not in src and "clip(q" not in src
    assert "_ray_rhs" in src and "k1" in src and "k4" in src
    assert B.trace_rk4(57)[-1]<1e-10
def test_learning_flow_and_single_limit_row():
    r=B.compute(); g=B.gates(r); spec=B.build_spec(r,g); tabs=spec["tabs"]
    assert [t["id"] for t in tabs]==["time","swath","refraction","limit"]
    assert all(len(t["t"])==41 and len(t["checks"])>=3 and "lesson" in t for t in tabs)
    failed=[[c for c in t["checks"] if not c["ok"]] for t in tabs]
    assert failed[:3]==[[],[],[]] and len(failed[3])==1
def test_page_budget_is_600k():
    r=B.compute(); html=B.pv._build_html(B.build_spec(r,B.gates(r)),list(B.LANGS))
    assert len(html.encode("utf-8"))<=600_000
