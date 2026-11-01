"""Acceptance gates for the industrial OCT field-sweep viewer."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def _load():
    s = importlib.util.spec_from_file_location("industrial_oct_builder_t", ROOT / "tools" / "build_industrial_oct_anim3d.py")
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


B = _load()


def test_real_or_named_synthetic_source_and_op_chain():
    spec = B.build_spec(); a = spec["_acceptance"]
    assert a["source"] in ("real", "synthetic")
    if B.REAL_PATH.is_file():
        assert a["source"] == "real"
    assert set(a["ops"]) >= {"oct_from_spectra", "oct_bscan", "oct_bscan_boundaries", "oct_bscan_flatten",
                              "oct_layer_thickness", "oct_design"}
    assert spec["credit"]["ja"].startswith("実測") if a["source"] == "real" else "PMMA/PC/PS" in spec["credit"]["ja"]


def test_sweeps_move_colour_and_keep_thickness_closed_form():
    spec = B.build_spec(); a = spec["_acceptance"]
    assert len(spec["tabs"]) == 2
    for key in ("index", "wavelength"):
        assert a[key]["endpoint_colour_ptp"] > 0
        assert np.ptp(a[key]["thickness_endpoints"], axis=0).min() > 0
    bias = 100 * (a["index"]["thickness_endpoints"][0] / a["index"]["thickness_endpoints"][1] - 1)
    assert np.allclose(bias, [0.9, 1.9], atol=1e-12)
    assert a["index"]["axial_exaggeration"] == 8.0
    assert np.max(np.abs(a["index"]["interface_peak_offsets"])) <= 2
    assert all(c["ok"] for tab in spec["tabs"] for c in tab["checks"])


def test_paper_panels_exports_and_quality_gate():
    spec = B.build_spec()
    for tab in spec["tabs"]:
        assert len(tab["panes"]) == 4
        assert [p["label"]["en"][:3] for p in tab["panes"]] == ["(a)", "(b)", "(c)", "(d)"]
        assert tab["panes"][1]["data"].shape[1:] == (3, 2)
        assert np.asarray(tab["bodies"][0]["val"]).ndim == 2
        assert np.asarray(tab["bodies"][1]["pos"]).ndim == 3
        assert len(tab["bodies"]) == 6
        assert all(s["lo"] > 0 and s["hi"] > s["lo"] for s in tab["series"])
        assert all(len(s["references"]) == 1 for s in tab["series"])
    data = B.pv._pack_spec(spec, ["ja", "en"])
    B.pv.viewer_quality_gate_data(data)
    B.pv.viewer_motion_gate_data(data)
    assert "pane field" in B.pv.viewer_export_strings(spec, "index", 0, "ja")["pane_csv"][1]
    assert "element vertex" in B.pv.viewer_export_strings(spec, "index", 0, "ja")["ply"][1]


def test_formal_i18n_opt_in_is_ja_en_only():
    assert B.ANIM3D_I18N_LANGS == ("ja", "en")
    html = B.pv._build_html(B.build_spec(), ["ja", "en"], detect_lang=True)
    assert '"langs":["ja","en"]' in html
