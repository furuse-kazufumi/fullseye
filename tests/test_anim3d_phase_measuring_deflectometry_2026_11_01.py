"""Acceptance gates for the PMD field-sweep viewer."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def _load():
    s = importlib.util.spec_from_file_location("pmd_builder_t", ROOT / "tools" / "build_phase_measuring_deflectometry_anim3d.py")
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


B = _load()


def test_fullseye_op_chain_and_caption_numbers():
    spec = B.build_spec(); a = spec["_acceptance"]
    assert set(a["ops"]) >= {"deflectometry_rig", "deflectometry_render", "deflectometry_phase_to_slope",
                              "slope_to_curvature", "sfp_height", "deflectometry_sensitivity"}
    assert abs(a["distance_2pct_error"] + 2.3) < .2
    assert .85 <= a["first_order_jump_kd"] <= .95
    assert a["photo_snr"] < .25


def test_both_sweeps_change_3d_colour_and_depth():
    spec = B.build_spec(); a = spec["_acceptance"]
    for key in ("distance", "diffuse"):
        assert a[key]["colour_ptp"] > 0
        assert a[key]["relief_endpoint_ptp_um"] > 0
        assert np.ptp(a[key]["depth_endpoints"]) > 0
        assert a[key]["exaggeration_x1"] > 100
        assert a[key]["shape_mode"] == "residual"
    assert a["distance"]["zero_error_profile_rms_um"] < 0.3
    assert a["distance_original"]["shape_mode"] == "original"
    checks = [c for tab in spec["tabs"] for c in tab["checks"]]
    assert checks, "検算欄が 0 件では受け入れ検査にならない"
    assert all(c["ok"] for c in checks)


def test_relief_paper_panels_height_exports_and_quality_gate():
    spec = B.build_spec()
    assert [t["id"] for t in spec["tabs"]] == ["distance", "diffuse", "distance_original", "diffuse_original"]
    for tab in spec["tabs"]:
        assert tab["bodies"][0]["relief_default"] == 1.0
        assert np.asarray(tab["bodies"][0]["rgb"]).ndim == 3
        assert np.asarray(tab["bodies"][0]["val"]).shape[1:] == (B.N * B.N,)
        assert len(tab["panes"]) == 4
        assert [p["label"]["en"][:3] for p in tab["panes"]] == ["(a)", "(b)", "(c)", "(d)"]
        assert tab["panes"][3]["data"].shape[1:] == (B.N, B.N)
        assert tab["cbar"]["unit"] == "1/m"
        assert np.isclose(tab["cbar"]["lo"], -1.8) and np.isclose(tab["cbar"]["hi"], 1.8)
    packed = B.pv._pack_spec(spec, ["ja", "en"])
    B.pv.viewer_quality_gate_data(packed); B.pv.viewer_motion_gate_data(packed)
    exports = B.pv.viewer_export_strings(spec, "distance", 0, "ja")
    assert "pane field" in exports["pane_csv"][3]
    assert "property float value" in exports["ply"][0]


def test_ja_en_formal_output():
    assert B.ANIM3D_I18N_LANGS == ("ja", "en")
    html = B.pv._build_html(B.build_spec(), ["ja", "en"], detect_lang=True)
    assert '"langs":["ja","en"]' in html
