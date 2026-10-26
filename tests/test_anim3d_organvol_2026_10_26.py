"""Numerical gates for the BodyParts3D organ-volume lesson."""
from __future__ import annotations

import importlib.util
import pathlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load():
    s = importlib.util.spec_from_file_location("organvol_builder_t", ROOT / "tools" / "build_organvol_anim3d.py")
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


B = _load()


def test_two_volume_routes_agree_at_resolution_derived_pitch():
    rows = B.metrics()
    assert len(rows) == 6
    assert max(x["relative_error"] for x in rows.values()) < 1e-2
    assert all(x["pitch"] > 0 for x in rows.values())


def test_drawn_polyhedral_sphere_converges_monotonically_to_one():
    gate = B.sphere_gate()
    assert gate["monotonic"]
    assert gate["drawn"] == gate["levels"][1]
    assert gate["levels"][0] < gate["levels"][1] < gate["levels"][2] < 1


def test_all_committed_surfaces_are_closed_spheres_topologically():
    rows = B.metrics()
    assert len(rows) == 6
    assert all(x["chi"] == 2 and x["boundary_edges"] == 0 and x["nonmanifold_edges"] == 0 for x in rows.values())
    assert sum(x["source_boundary_edges"] for x in rows.values()) == 1604
    assert all(x["welded_boundary_edges"] == 0 and x["repair_method"] == "vertex_weld" for x in rows.values())
    assert all("convex" not in x["repair_method"] for x in rows.values())


def test_limit_is_present_and_diagnostic_warning_is_explicit():
    spec = B.build_spec(); tabs = spec["tabs"]
    assert len(tabs) == 4
    limited = [c for t in tabs for c in t["checks"] if not c["ok"]]
    assert len(limited) == 1
    assert "diagnosis" in tabs[-1]["lesson"]["limit"]["en"]
