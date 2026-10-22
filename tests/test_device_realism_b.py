"""Device-realism contracts for accessions 2026.023, 2026.043 and 2026.078."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    path = ROOT / "examples" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_lightfield_resemblance_contract():
    poc = _load("poc_lightfield_depth")
    evidence = poc.realism_evidence()
    # Count before iterating: an empty evidence vector must never pass vacuously.
    assert len(evidence["slope_errors_px_per_view"]) == 3
    assert max(evidence["slope_errors_px_per_view"]) <= 0.05
    assert evidence["mixing_error_fraction"] <= 0.05
    assert evidence["breaking_probe_error_px_per_view"] > 0.05


def test_thermography_resemblance_contract():
    poc = _load("poc_thermography_ndt")
    evidence = poc.realism_evidence()
    assert -0.53 <= evidence["sound_log_slope"] <= -0.47
    assert 1.8 <= evidence["peak_time_depth_exponent"] <= 2.2
    assert abs(evidence["diffusivity_time_ratio"] - 0.5) <= 0.05
    frames = evidence["display_frames"]
    assert len(frames) == 4
    assert all(np.asarray(frame).dtype == np.uint8 for frame in frames)
    assert min(np.asarray(frame).shape[0] for frame in frames) >= 512


def test_pv_camera_resemblance_contract():
    poc = _load("poc_pv_thermal_survey")
    evidence = poc.realism_evidence()
    assert 3.0 <= evidence["hotspot_delta_k"] <= 20.0
    assert 0.2 <= evidence["module_spread_k"] <= 5.0
    assert evidence["fresnel_gradient_error"] <= 0.02
    assert evidence["fpn_rms_k"] >= 0.02
    assert evidence["no_nuc_fpn_rms_k"] < 0.01
    assert np.asarray(evidence["raw_frame"]).shape[:2] == (512, 640)
