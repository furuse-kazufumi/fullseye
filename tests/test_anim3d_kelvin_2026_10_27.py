"""Numerical and publication gates for the Kelvin-wake lesson."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BUILDER = "build_kelvin_anim3d"
PAGE = ROOT / "docs" / "view2026" / "anim3d" / "kelvin_wake_anim3d.html"


def _load(name, folder="tools"):
    spec = importlib.util.spec_from_file_location(name + "_kelvin_test", ROOT / folder / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


B = _load(BUILDER)


def test_height_image_cusp_matches_kelvin_angle_at_three_speeds():
    rows = B.compute()
    assert len(rows) == 3
    gate = B.gates(rows)
    assert gate["max_angle_error_deg"] < gate["angle_limit_deg"]
    assert gate["angle_spread_deg"] < gate["angle_limit_deg"]
    assert gate["angle_spread_deg"] > 0.1
    assert all(r["z"].shape == (201, 281) for r in rows)
    assert all(np.array_equal(rows[0]["x"], r["x"]) and np.array_equal(rows[0]["y"], r["y"])
               for r in rows[1:])
    # Fixed physical grids and envelopes mean the cases are not scaled copies.
    assert not np.allclose(rows[0]["z"], rows[1]["z"])
    assert not np.allclose(rows[1]["z"], rows[2]["z"])


def test_centreline_spectrum_measures_transverse_wavelength():
    rows = B.compute()
    assert len(rows) == 3
    for row in rows:
        error = abs(row["wavelength"] - row["wavelength_truth"])
        assert error < row["wavelength_limit"]
    ratios = np.array([r["wavelength"] for r in rows]) / np.square(B.SPEEDS)
    assert np.ptp(ratios) < 0.02 * ratios.mean()
    gate = B.gates(rows)
    assert gate["wavelength_ratio_error"] < gate["wavelength_ratio_limit"]


def test_checks_are_computed_and_limit_is_explicit():
    rows = B.compute(); gate = B.gates(rows); spec = B.build_spec(rows)
    assert len(spec["tabs"]) == 4
    checks = spec["tabs"][0]["checks"]
    assert len(checks) == 4 and all(c["ok"] for c in checks)
    assert "%.2f deg" % gate["max_angle_error_deg"] == checks[0]["result"]
    limited = [c for t in spec["tabs"] for c in t["checks"] if not c["ok"]]
    assert len(limited) == 1
    assert limited[0]["result"]["en"] == "not computed"


def test_i18n_table_and_committed_page_are_current(tmp_path):
    I18N = _load("anim3d_i18n")
    table = I18N.load_table(BUILDER)
    spec = B.build_spec()
    problems, unused = I18N.audit(spec, table)
    assert problems == [] and unused == []
    want = I18N.pv._build_html(I18N.translate(spec, table), list(I18N.LANGS), detect_lang=True)
    html = PAGE.read_text(encoding="utf-8")
    I18N.check_same_page(html, want, PAGE, BUILDER)
