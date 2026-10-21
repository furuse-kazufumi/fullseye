"""Device-realism gates for exhibits 2026.022, 2026.033 and 2026.120."""
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


def test_csi_surface_stack_and_resemblance_probe():
    p = _load("poc_interferometry_step")
    result = p.surface_csi_measurement(size=96, n_planes=48, seed=4)
    assert result["stack"].shape == (48, 96, 96)
    assert result["truth_um"].shape == result["height_um"].shape == (96, 96)
    assert result["quality"].shape == (96, 96)
    assert np.count_nonzero(result["quality"] < result["quality_threshold"]) > 20
    gate = p.csi_resemblance_gate(size=72)
    assert gate["envelope_relative_error"] < 0.02
    assert gate["fringe_period_relative_error"] < 1e-3
    assert gate["step_repeatability_nm"] <= 10.0
    assert abs(gate["half_bandwidth_width_ratio"] - 2.0) < 0.02


def test_dof_mosaic_stokes_and_extinction_probe():
    p = _load("poc_polarization_specular")
    result = p.dofp_inspection_scene(size=128, seed=5)
    assert result["raw_mosaic"].shape == (128, 128)
    assert result["analyzers"].shape == (4, 64, 64)
    assert result["stokes"].shape == (3, 64, 64)
    assert result["dolp"].shape == result["aolp_deg"].shape == (64, 64)
    assert np.count_nonzero(result["raw_mosaic"] >= 1.0) > 0
    gate = p.polarization_resemblance_gate(size=160, seed=8)
    assert gate["highlight_dolp"] > 0.97
    assert gate["highlight_aolp_error_deg"] < 1.0
    assert abs(gate["aolp_noise_ratio"] - 1.0) < 0.20
    assert gate["no_polarizer_max_dolp"] < 0.02


def test_aoi_ct_modalities_and_physical_probes():
    p = _load("poc_aoi_ct_traceability")
    result = p.device_scene(size=128, seed=9)
    assert result["aoi_rgb"].shape == (128, 128, 3)
    assert result["ct_slices"].shape == (3, 128, 128)
    assert result["vertical_slice"].shape == (128, 128)
    assert result["sinogram"].ndim == 2
    assert np.count_nonzero(result["defect_mask"]) > 30
    gate = p.aoi_ct_resemblance_gate(size=96, seed=10)
    assert gate["water_streak_snr"] < 3.0
    assert gate["metal_streak_snr"] > 4.0
    assert gate["highlight_angle_error_deg"] < 2.0
    assert gate["attenuation_relative_error"] < 0.05
