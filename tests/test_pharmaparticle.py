"""Pharmaceutical microscopy PSD: ground truth, decisions, uncertainty, and refusals."""
from __future__ import annotations

import copy
import math

import numpy as np
import pytest

import blob2d
import opsdrive
import pharmaparticle as psd
from fullseye.evaluation.manifest import build_manifest, compare_manifests
from fullseye.evaluation.result import GateResult
from fullseye.evaluation.truth import TruthBundle


def _calibration(**changes):
    value = {"scale_per_px": 0.5, "unit": "um/px", "uncertainty_per_px": 0.005,
             "calibrator_id": "SM-2026-017", "calibrated_at": "2026-10-01",
             "valid_until": "2027-09-30"}
    value.update(changes)
    return value


def _particles(**changes):
    value = {"object_id": ["p1", "p2", "p3"], "diameter_px": [10.0, 20.0, 40.0],
             "area_px2": np.pi * np.square([5.0, 10.0, 20.0]),
             "touches_border": [False, False, False],
             "split_status": ["isolated", "isolated", "split"]}
    value.update(changes)
    return value


def _run(particles=None, calibration=None, **kwargs):
    return psd.particle_size_distribution(
        _particles() if particles is None else particles,
        _calibration() if calibration is None else calibration,
        measurement_date="2026-11-23", bootstrap_samples=200, **kwargs)


def test_pixelised_circle_and_ellipse_equivalent_diameters_are_within_half_a_pixel():
    yy, xx = np.mgrid[0:160, 0:220]
    circle = (yy - 50.0) ** 2 + (xx - 55.0) ** 2 <= 18.0 ** 2
    ellipse = ((yy - 102.0) / 12.0) ** 2 + ((xx - 150.0) / 28.0) ** 2 <= 1.0
    features = blob2d.blob_features(blob2d.blob_label(circle | ellipse))
    measured = np.sort(features["equiv_diameter"])
    truth = np.sort([36.0, 2.0 * math.sqrt(12.0 * 28.0)])
    error_px = measured - truth
    table = {"object_id": ["circle", "ellipse"], "diameter_px": measured,
             "area_px2": features["area"], "touches_border": [False, False],
             "split_status": ["isolated", "isolated"]}
    report = _run(table)
    assert np.max(np.abs(error_px)) < 0.5
    assert np.allclose([row["diameter"] for row in report["particle_rows"]], measured * 0.5)


def test_number_area_and_volume_weighted_quantiles_match_manual_cumulative_interpolation():
    report = _run()
    diameter = np.array([10.0, 20.0, 40.0])
    manual_weights = {"number": np.ones(3), "area": diameter ** 2, "volume": diameter ** 3}
    for basis, weight in manual_weights.items():
        cumulative = np.cumsum(weight) / np.sum(weight)
        for q in (10, 50, 90):
            expected_um = float(np.interp(q / 100.0, cumulative, diameter)) * 0.5
            assert report["quantiles"][basis][f"D{q}"]["value"] == pytest.approx(expected_um)
    assert report["quantiles"]["number"]["D50"]["value"] < report["quantiles"]["volume"]["D50"]["value"]
    for basis in ("number", "area", "volume"):
        assert np.sum(report["bins"][basis]) == pytest.approx(1.0)


def test_three_border_policies_include_exclude_and_correct_the_known_particle():
    p = _particles(touches_border=[False, True, False],
                   border_inclusion_probability=[1.0, 0.5, 1.0],
                   border_corrected_diameter_px=[10.0, 24.0, 40.0],
                   border_corrected_area_px2=np.pi * np.square([5.0, 12.0, 20.0]))
    included = _run(p, border_policy="include")
    excluded = _run(p, border_policy="exclude")
    corrected = _run(p, border_policy="correct")
    assert included["counts"]["accepted_observed"] == 3
    assert included["particle_rows"][1]["diameter"] == pytest.approx(10.0)
    assert excluded["counts"]["accepted_observed"] == 2
    assert excluded["particle_rows"][1]["reason"] == "border_excluded"
    assert corrected["counts"]["accepted_corrected"] == pytest.approx(4.0)
    assert corrected["particle_rows"][1]["diameter"] == pytest.approx(12.0)


def test_overlap_state_is_recorded_and_unresolved_objects_are_not_counted_as_one():
    p = _particles(object_id=["isolated", "split-a", "unsplit", "ambiguous"],
                   diameter_px=[10.0, 12.0, 22.0, 25.0], area_px2=[80.0, 110.0, 380.0, 490.0],
                   touches_border=[False] * 4,
                   split_status=["isolated", "split", "unsplit", "ambiguous"])
    report = _run(p)
    assert report["counts"]["accepted_observed"] == 2
    assert report["counts"]["overlap_split_accepted"] == 1
    assert report["counts"]["overlap_unsplit_excluded"] == 1
    assert report["counts"]["overlap_ambiguous_excluded"] == 1
    assert [row["accepted"] for row in report["particle_rows"]] == [True, True, False, False]


def test_scale_uncertainty_reaches_each_diameter_and_every_quantile_interval():
    report = _run(calibration=_calibration(uncertainty_per_px=0.01))
    row = report["particle_rows"][0]
    z95 = 1.959963984540054
    assert row["diameter_uncertainty"] == pytest.approx(0.1)
    assert row["diameter_ci_lower"] == pytest.approx(10.0 * (0.5 - z95 * 0.01))
    for basis in ("number", "area", "volume"):
        for name in ("D10", "D50", "D90"):
            q = report["quantiles"][basis][name]
            assert q["ci_lower"] < q["value"] < q["ci_upper"]


def _manifest(report):
    values = np.array([[report["quantiles"][basis][name]["value"]
                        for name in ("D10", "D50", "D90")]
                       for basis in ("number", "area", "volume")])
    truth = TruthBundle(fields={"quantiles": values}, units={"quantiles": "um"},
                        frames={"quantiles": "index"}, masks={},
                        provenance={"processing_stage": "synthetic", "generator": "unit-test"}, seed=776)
    return build_manifest("pharma-psd", metrics={"calibration_sha256": report["calibration_provenance"]["sha256"]},
                          arrays={"quantiles": values}, truth=truth,
                          gates=[GateResult("finite", bool(np.all(np.isfinite(values))),
                                            float(np.max(values)), "finite", 0.0, "is finite", "")],
                          figures=[], videos={}, seed=776)


def test_same_seed_environment_manifest_and_array_hashes_are_exactly_reproducible():
    first, second = _run(), _run()
    manifest_a, manifest_b = _manifest(first), _manifest(second)
    assert compare_manifests(manifest_a, manifest_b) == []
    assert manifest_a["arrays"]["quantiles"]["sha256"] == manifest_b["arrays"]["quantiles"]["sha256"]
    assert first["calibration_provenance"]["particles_sha256"] == second["calibration_provenance"]["particles_sha256"]


@pytest.mark.parametrize("mutation, message", [
    (lambda p, c, k: p.update(diameter_px=[10.0, np.inf, 40.0]), "NaN or Inf"),
    (lambda p, c, k: c.update(scale_per_px=-0.5), "must be > 0"),
    (lambda p, c, k: c.update(uncertainty_per_px=-0.1), "must be >= 0"),
    (lambda p, c, k: c.update(valid_until="2026-11-22"), "not valid"),
    (lambda p, c, k: p.update(split_status=["isolated", "merged", "split"]), "unknown split_status"),
    (lambda p, c, k: k.update(border_policy="correct", particles={**p, "touches_border": [True, False, False]}),
     "border correction requires"),
    (lambda p, c, k: p.update(touches_border=[False] * 3,
                              split_status=["unsplit", "ambiguous", "unsplit"]), "no particle remains"),
])
def test_invalid_inputs_fail_closed(mutation, message):
    particles, calibration, kwargs = copy.deepcopy(_particles()), copy.deepcopy(_calibration()), {}
    mutation(particles, calibration, kwargs)
    particles = kwargs.pop("particles", particles)
    with pytest.raises(ValueError, match=message):
        _run(particles, calibration, **kwargs)


def test_ledger_contract_and_worked_docstring_example_are_reachable():
    meta = opsdrive.info("particle_size_distribution")
    assert meta["in"] == ["table", "table"] and meta["out"] == "table"
    assert "Parameters" in psd.particle_size_distribution.__doc__
    assert "laser-diffraction" in psd.particle_size_distribution.__doc__
