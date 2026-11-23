"""PSD regression tests: independent truth, fail-closed upstream records, and intervals."""
from __future__ import annotations

import copy
import hashlib

import numpy as np
import pytest

import pharmaparticle as psd


def _calibration(**changes):
    value = {"scale": {"value": 0.001, "unit": "mm/px", "standard_uncertainty": 0.00001},
             "calibrator_id": "SM-2026-017", "calibrated_at": "2026-10-01", "valid_until": "2027-09-30"}
    value.update(changes)
    return value


def _particles(diameter=(10.0, 20.0, 40.0), repeats=12, **changes):
    d = np.repeat(np.asarray(diameter, float), repeats)
    n = len(d)
    value = {"object_id": ["p%03d" % i for i in range(n)], "diameter_px": d,
             "area_px2": np.pi * np.square(d / 2.0), "diameter_unit": "px", "area_unit": "px2",
             "touches_border": [False] * n, "split_status": ["isolated"] * n,
             "component_id": ["c%03d" % i for i in range(n)],
              "split_evidence": ["blob_split + blob_count_interval:determined"] * n,
              "upstream_provenance_hash": [hashlib.sha256(("component-%03d" % i).encode()).hexdigest() for i in range(n)],
             "count_interval_lo": [1] * n, "count_interval_hi": [1] * n,
             "count_determined": [True] * n}
    value.update(changes)
    return value


def _run(particles=None, calibration=None, **kwargs):
    return psd.particle_size_distribution(
        _particles() if particles is None else particles, _calibration() if calibration is None else calibration,
        measurement_date="2026-11-23", bootstrap_samples=200, **kwargs)


def _border_columns(n, *, probability=.5, uncertainty=.02, diameter_uncertainty=.5, area_uncertainty=2.0):
    """Known correction inputs with uncertainty / 既知補正入力と不確かさ。"""
    return {"border_inclusion_probability": [probability] + [1.] * (n - 1),
            "border_inclusion_probability_uncertainty": [uncertainty] + [0.] * (n - 1),
            "border_corrected_diameter_px": [24.] + [10., 20., 40.] * ((n - 1) // 3) + [10., 20., 40.][:((n - 1) % 3)],
            "border_corrected_diameter_uncertainty_px": [diameter_uncertainty] + [0.] * (n - 1),
            "border_corrected_area_px2": [np.pi * 12.0 ** 2] + [np.pi * x ** 2 / 4 for x in ([10., 20., 40.] * ((n - 1) // 3) + [10., 20., 40.][:((n - 1) % 3)])],
            "border_corrected_area_uncertainty_px2": [area_uncertainty] + [0.] * (n - 1),
            "border_correction_provenance": {"view_shape": [100, 100],
                                               "inclusion_probability_method": "uniform-centre-window geometry",
                                               "correction_method": "experimental Horvitz-Thompson"}}


def test_weighted_empirical_midpoint_quantiles_match_independent_duplicate_weight_truth():
    # Independent paper calculation after pooling duplicate diameters: weights (2, 1, 3)
    # have midpoint probabilities 1/6, 5/12, 3/4.  Linear interpolation gives D10=10,
    # D50=25, D90=40.  This is deliberately not the implementation's cumulative formula.
    p = _particles(diameter=(10.0, 10.0, 20.0, 40.0, 40.0, 40.0), repeats=6)
    report = _run(p)
    q = report["quantiles"]["number"]
    assert q["D10"]["value"] == pytest.approx(0.010)
    assert q["D50"]["value"] == pytest.approx(0.025)
    assert q["D90"]["value"] == pytest.approx(0.040)
    assert report["policy"]["quantile_convention"] == "weighted_empirical_midpoint"


def test_single_particle_and_small_main_sample_report_insufficient_sample_instead_of_zero_width_ci():
    for n in (1, 6, psd.MIN_EFFECTIVE_PARTICLES - 1):
        p = _particles(diameter=(20.0,), repeats=n)
        result = _run(p)
        for basis in ("number", "area", "volume"):
            point = result["quantiles"][basis]["D50"]
            assert point["status"] == "insufficient_sample"
            assert point["value"] is None and point["ci_lower"] is None and point["ci_upper"] is None


def test_kish_effective_particles_are_computed_and_gated_per_weighting_basis():
    # 29 one-pixel particles plus one 10^6-pixel particle: count n_eff is 30,
    # while area and volume mass are concentrated in the single large particle.
    p = _particles(diameter=tuple([1.0] * 29 + [1.0e6]), repeats=1)
    r = _run(p)
    assert r["quantiles"]["number"]["D50"]["status"] == "estimated"
    assert r["quantiles"]["area"]["D50"]["status"] == "insufficient_sample"
    assert r["quantiles"]["volume"]["D50"]["status"] == "insufficient_sample"
    assert r["policy"]["effective_particles"]["number"] == pytest.approx(30.0)
    assert r["policy"]["effective_particles"]["volume"] < 1.01


def test_upstream_count_interval_is_required_and_an_undetermined_component_is_fail_closed_ambiguous():
    p = _particles(repeats=10)
    p["count_determined"][0] = False
    p["count_interval_hi"][0] = None
    p["split_status"][0] = "ambiguous"
    r = _run(p)
    assert r["particle_rows"][0]["accepted"] is False
    bad = copy.deepcopy(p)
    bad["split_status"][0] = "isolated"
    with pytest.raises(ValueError, match="undetermined"):
        _run(bad)


def test_component_record_must_be_coherent_and_determined_count_must_equal_reported_rows():
    p = _particles(diameter=(10.0,), repeats=30)
    p["component_id"] = ["c0"] * 30
    p["upstream_provenance_hash"] = ["a" * 64] * 30
    with pytest.raises(ValueError, match="exactly its declared count"):
        _run(p)
    p = _particles(diameter=(10.0,), repeats=30)
    del p["upstream_provenance_hash"]
    with pytest.raises(ValueError, match="upstream_provenance_hash"):
        _run(p)


def test_unit_empty_and_missing_columns_each_fail_closed():
    with pytest.raises(ValueError, match="must be 'px'"):
        _run(_particles(diameter_unit="um"))
    with pytest.raises(ValueError, match="particles is empty"):
        _run(_particles(diameter=(), repeats=1))
    p = _particles()
    del p["component_id"]
    with pytest.raises(ValueError, match="component_id"):
        _run(p)
    with pytest.raises(ValueError, match="mm/px"):
        _run(calibration=_calibration(scale={"value": 1.0, "unit": "um/px", "standard_uncertainty": .1}))


def test_border_correction_requires_probability_derivation_method_and_uncertainty_provenance():
    p = _particles(repeats=10, touches_border=[True] + [False] * 29, **_border_columns(30))
    r = _run(p, border_policy="correct")
    assert r["counts"]["accepted_corrected"] == pytest.approx(31.0)
    assert r["policy"]["border_correction"]["correction_method"] == "experimental Horvitz-Thompson"
    del p["border_correction_provenance"]
    with pytest.raises(ValueError, match="border correction requires"):
        _run(p, border_policy="correct")


def test_border_correction_uncertainty_changes_quantile_interval_and_particle_uncertainty():
    uncertain = _particles(repeats=12, touches_border=[True] + [False] * 35,
                           **_border_columns(36, uncertainty=.02, diameter_uncertainty=.5, area_uncertainty=2.0))
    fixed = copy.deepcopy(uncertain)
    uncertain["border_corrected_diameter_px"][0] = 100.
    uncertain["border_corrected_area_px2"][0] = np.pi * 50.0 ** 2
    fixed["border_corrected_diameter_px"][0] = 100.
    fixed["border_corrected_area_px2"][0] = np.pi * 50.0 ** 2
    fixed.update(_border_columns(36, uncertainty=0., diameter_uncertainty=0., area_uncertainty=0.))
    fixed["border_corrected_diameter_px"][0] = 100.
    fixed["border_corrected_area_px2"][0] = np.pi * 50.0 ** 2
    a, b = _run(uncertain, border_policy="correct", seed=72), _run(fixed, border_policy="correct", seed=72)
    qa, qb = a["quantiles"]["number"]["D90"], b["quantiles"]["number"]["D90"]
    assert (qa["ci_lower"], qa["ci_upper"]) != pytest.approx((qb["ci_lower"], qb["ci_upper"]))
    assert a["particle_rows"][0]["diameter_uncertainty"] > b["particle_rows"][0]["diameter_uncertainty"]
    assert a["policy"]["border_uncertainty_propagation"] == "truncated-normal sensitivity resampling"


def test_known_random_field_multiple_windows_call_op_and_reduce_border_cdf_bias_with_geometric_correction():
    # Centres are uniformly generated on a larger known field.  For a square window,
    # p=(W-d)^2/W^2 is the declared inclusion probability for a fully visible disc.
    rng = np.random.default_rng(91)
    truth = rng.uniform(8.0, 32.0, size=900)
    windows = []
    for origin in (0.0, 30.0, 60.0):
        inclusion = np.clip((100.0 - truth) / 100.0, 0.01, 1.0)
        observed = rng.random(truth.size) < inclusion
        p = np.clip((100.0 - truth) / 100.0, 0.01, 1.0)
        raw = truth[observed]
        corrected_d, corrected_w = truth[observed], 1.0 / p[observed]
        rows = _particles(diameter=tuple(raw), repeats=1, touches_border=[True] * raw.size,
                          border_inclusion_probability=p[observed].tolist(),
                          border_inclusion_probability_uncertainty=[0.] * raw.size,
                          border_corrected_diameter_px=corrected_d.tolist(),
                          border_corrected_diameter_uncertainty_px=[0.] * raw.size,
                          border_corrected_area_px2=(np.pi * np.square(corrected_d) / 4).tolist(),
                          border_corrected_area_uncertainty_px2=[0.] * raw.size,
                          border_correction_provenance={"view_shape": [100, 100],
                                                        "inclusion_probability_method": "uniform-centre-window geometry",
                                                        "correction_method": "experimental Horvitz-Thompson"})
        report = _run(rows, border_policy="correct", seed=int(origin) + 8)
        corrected_median = report["quantiles"]["number"]["D50"]["value"] / .001
        windows.append((abs(np.median(raw) - np.median(truth)), abs(corrected_median - np.median(truth))))
    raw_bias, corrected_bias = np.mean(windows, axis=0)
    assert corrected_bias < raw_bias


def _wilson_lower(successes, trials, confidence=.95):
    """Wilson lower endpoint without a statistics-library dependency / 下側 Wilson 端点。"""
    z = 1.959963984540054 if confidence == .95 else pytest.fail("test only fixes 95%")
    p = successes / trials
    return (p + z * z / (2 * trials) - z * np.sqrt(p * (1 - p) / trials + z * z / (4 * trials ** 2))) / (1 + z * z / trials)


def test_predeclared_400_trial_conditional_coverage_varies_scale_split_detection_and_border_judgement():
    # Predeclared before running: 400 trials make a 0.90 lower Wilson bound
    # distinguishable from nominal 0.95 (about +/-2.1 percentage points).  The
    # target is explicitly the distribution conditional on accepted particles.
    rng = np.random.default_rng(42)
    population = rng.lognormal(np.log(20.0), .08, 100_000)
    acceptance_probability = .92 * .90 * (.78 + .20 / (1.0 + np.exp(-(population - 16.0) / 3.0)))
    truth = {}
    for basis, weight in (("number", acceptance_probability),
                          ("area", acceptance_probability * population ** 2),
                          ("volume", acceptance_probability * population ** 3)):
        order = np.argsort(population)
        x, w = population[order], weight[order]
        position = (np.cumsum(w) - .5 * w) / w.sum()
        truth[basis] = {"D%d" % q: float(np.interp(q / 100.0, position, x)) * .001 for q in (10, 50, 90)}
    covered = {(basis, "D%d" % q): 0 for basis in truth for q in (10, 50, 90)}
    trials = 400
    for seed in range(trials):
        source = rng.choice(population, 96)
        detected = rng.random(source.size) < (.78 + .20 / (1.0 + np.exp(-(source - 16.0) / 3.0)))
        source = source[detected]
        determined = rng.random(source.size) < .92
        border = rng.random(source.size) < .10
        true_scale = .001 + rng.normal(0.0, .000004)
        observed_px = source * .001 / true_scale + rng.normal(0.0, .18, source.size)
        p = _particles(diameter=tuple(observed_px), repeats=1,
                       area_px2=(np.pi * np.square(observed_px) / 4).tolist(),
                       touches_border=border.tolist(),
                       split_status=["isolated" if item else "ambiguous" for item in determined],
                       count_interval_lo=[1] * source.size,
                       count_interval_hi=[1 if item else None for item in determined],
                       count_determined=determined.tolist())
        calibration = _calibration(scale={"value": true_scale + rng.normal(0.0, .000004),
                                          "unit": "mm/px", "standard_uncertainty": .000004})
        report = _run(p, calibration=calibration, border_policy="exclude", seed=seed)
        for basis in truth:
            for name, target in truth[basis].items():
                interval = report["quantiles"][basis][name]
                if interval["status"] == "estimated":
                    covered[basis, name] += interval["ci_lower"] <= target <= interval["ci_upper"]
                else:
                    pytest.fail("coverage trial fell below the predeclared effective-n gate")
    lower = {key: _wilson_lower(value, trials) for key, value in covered.items()}
    assert all(value >= .90 for value in lower.values()), "\n".join("%s: %.4f" % (key, value) for key, value in lower.items())
