"""Numerical gates for the synthetic tablet-inspection lesson."""
from __future__ import annotations

import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load():
    s = importlib.util.spec_from_file_location("tablet_builder_t", ROOT / "tools" / "build_tablet_anim3d.py")
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


B = _load()


def test_otsu_area_center_finds_planted_particle_within_one_pixel():
    r = B.compute()
    assert r["location_truth"] == (25.37, 27.62)
    assert 0 < r["location_error"]
    assert r["location_error"] <= 1.0


def test_detection_floor_matches_noise_closed_form():
    r = B.compute()
    assert r["trials"] == 800
    assert len(r["areas"]) == len(r["detection_rates"]) == 15
    assert r["formula_area"] == 3
    assert abs(r["measured_area"] - r["formula_area"]) <= 1
    assert r["detection_rates"][r["measured_area"] - 1] >= .90
    assert all(r["detection_rates"][:r["measured_area"] - 1] < .90)
    assert r["false_rates"].max() <= .011
    assert abs(r["min_area_mm2"] - 0.0192) < 1e-12


def test_ciede2000_op_matches_independent_direct_formula():
    r = B.compute()
    assert abs(r["de_op"] - 2.0424596801565738) < 1e-12
    assert r["de_error"] < 1e-9


def test_blob_count_is_nonempty_and_determined():
    r = B.compute(); got = r["blob_result"]
    assert got["count"] == 5
    assert got["determined"] is True


def test_one_computed_limit_row_is_visible():
    spec = B.build_spec(); tabs = spec["tabs"]
    assert len(tabs) == 4
    limited = [c for t in tabs for c in t["checks"] if not c["ok"]]
    assert len(limited) == 1
    assert tabs[-1]["id"] == "light"
    assert "multi-directional lighting" in tabs[-1]["lesson"]["limit"]["en"]
