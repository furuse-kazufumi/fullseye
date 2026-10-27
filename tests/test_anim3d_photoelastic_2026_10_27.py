"""Numerical and honesty gates for the photoelastic lesson."""
from __future__ import annotations
import importlib.util
import pathlib
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load():
    s=importlib.util.spec_from_file_location("photoelastic_builder_t",ROOT/"tools"/"build_photoelastic_anim3d.py")
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


B=_load()


def test_realistic_noisy_quantized_images_recover_three_loads_without_truth_in_estimator():
    rows=B.measurements()
    assert len(rows) == 3
    assert B.READ_NOISE == .01 and B.FULL_WELL == 10_000 and B.ADC_LEVELS == 256
    assert max(r["load_error_pct"] for r in rows) < 2.0
    assert max(r["fringe_error_pct"] for r in rows) < 3.0
    assert all(r["dark_count"] <= rows[i+1]["dark_count"] for i,r in enumerate(rows[:-1]))


def test_independent_temporal_fringe_count_and_multispectral_phase_agree():
    rows=B.measurements()
    assert len(rows) >= 3
    assert max(r["route_difference_pct"] for r in rows) < 4.0
    assert max(r["order_rmse"] for r in rows) < .10


def test_spatial_route_uses_an_offset_sensor_grid_and_detected_dark_lines():
    o=B.observe(B.LOADS[-1],seed=2)
    assert o["dark_count"] >= 3
    assert len(o["spatial"]["cols"]) > 40
    assert o["spatial"]["centre_order"] > 3
    assert set(np.unique(o["mono"])).issubset(set(np.arange(256)/255.0))


def test_deterministic_mesh_and_explicit_limit():
    v,f=B._disc()
    assert len(v) == 98 and len(f) == 192
    spec=B.build_spec(); assert len(spec["tabs"]) == 4
    failed=[c for t in spec["tabs"] for c in t["checks"] if not c["ok"]]
    assert len(failed) == 1
    assert spec["tabs"][-1]["badge"] == "limit"
