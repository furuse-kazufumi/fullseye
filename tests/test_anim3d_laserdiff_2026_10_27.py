"""Numerical gates for the laser-diffraction particle-size lesson."""
from __future__ import annotations

import importlib.util
import pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]


def _load():
    s=importlib.util.spec_from_file_location("laserdiff_builder_t",ROOT/"tools"/"build_laserdiff_anim3d.py")
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


B=_load()


def test_first_dark_ring_is_measured_from_the_same_pixels_as_the_pane():
    r=B.compute()
    assert (r["dark_image"] == B._patterns()[0]).all()
    assert r["dark"] == B.measure_first_dark(B._patterns()[0])
    assert r["dark"] != r["dark_closed"]
    assert r["dark_error"] < 5e-4


def test_nnls_recovers_two_distributions_without_truth_input():
    r=B.compute(); g=B.gates(r)
    assert len(r["cases"]) >= 2
    assert g["single_d50_error"] < g["d50_bound"]
    assert g["bimodal_d50_error"] < g["d50_bound"]
    for case in r["cases"].values():
        assert len(case["fine_diameters"]) == 6*len(B.DIAMETERS)
        assert case["observation_kernel"].shape[1] == len(case["fine_diameters"])
        assert not any(case["fine_diameters"] == B.DIAMETERS[0])
        assert (case["estimate"] >= 0).all()
        assert abs(case["estimate"].sum()-1) < 1e-12


def test_noise_trials_keep_fixed_kernel_and_stable_d50():
    r=B.compute()
    assert len(r["noise_d50"]) == 12
    assert len(set(r["noise_d50"])) > 1
    assert r["noise_cv"] < .08
    expected=(B.math.sqrt(B.DIAMETERS[1]/B.DIAMETERS[0])-1)*100+3*r["noise_cv"]*100
    assert abs(B.gates(r)["d50_bound"]-expected) < 1e-12


def test_limit_row_is_explicit_and_unique():
    tabs=B.build_spec()["tabs"]
    assert len(tabs) == 4
    failed=[c for t in tabs for c in t["checks"] if not c["ok"]]
    assert len(failed) == 1
    assert "not computed" in failed[0]["result"]["en"]
