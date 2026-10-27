"""Numerical gates for the particle-dissolution lesson."""
from __future__ import annotations

import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load():
    s=importlib.util.spec_from_file_location("dissolution_builder_t",ROOT/"tools"/"build_dissolution_anim3d.py")
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


B=_load()


def test_ode_matches_independent_cube_root_solution():
    r=B.compute(); assert len(r["t"]) == B.N
    assert r["ode_rel"] < 1e-6


def test_image_measurement_stays_inside_pixel_and_noise_bound():
    r=B.compute(); assert max(r["count_eight"]) == 8
    assert r["image_error"] < .05
    assert r["image_error"] < r["pixel_bound"]


def test_eight_way_split_halves_dissolution_time():
    r=B.compute()
    assert r["measured_ratio"] != .5
    assert abs(r["measured_ratio"]-.5) < r["ratio_bound"]


def test_limit_row_is_explicit_and_unique():
    tabs=B.build_spec()["tabs"]; assert len(tabs) == 4
    failed=[c for t in tabs for c in t["checks"] if not c["ok"]]
    assert len(failed) == 1
    assert "not computed" in failed[0]["result"]["en"]
