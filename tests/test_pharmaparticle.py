"""PSD regression tests: independent truth, fail-closed upstream records, and intervals."""
from __future__ import annotations

import copy
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
              "upstream_component_label": list(range(1, n + 1)),
              "upstream_split_label": list(range(1, n + 1)),
              "upstream_provenance_hash": [""] * n,
             "count_interval_lo": [1] * n, "count_interval_hi": [1] * n,
             "count_determined": [True] * n}
    value.update(changes)
    return _seal(value)


def _upstream_records(particles):
    """Synthetic blob_split/blob_count_interval records / 合成した上流構造化記録。"""
    labels = np.asarray(particles["upstream_component_label"], int)
    unique = np.unique(labels)
    lo, hi, status = [], [], []
    for label in unique:
        i = int(np.flatnonzero(labels == label)[0])
        lo.append(particles["count_interval_lo"][i])
        hi.append(-1 if particles["count_interval_hi"][i] is None else particles["count_interval_hi"][i])
        status.append("determined" if particles["count_determined"][i] else "ambiguous")
    split_labels = np.asarray(particles["upstream_split_label"], int)
    pixel_areas = np.rint(np.asarray(particles["area_px2"], float)).astype(int)
    if np.any(pixel_areas < 1):
        raise AssertionError("synthetic particle areas must occupy at least one pixel")
    blob_split = np.repeat(split_labels, pixel_areas).reshape(1, -1)
    return {"blob_split": blob_split,
            "blob_count_interval": {"components": {"label": unique, "lo": np.asarray(lo),
                                                        "hi": np.asarray(hi), "status": np.asarray(status)}}}


def _seal(particles):
    """Attach the op-recomputed digest / op が再計算する digest を記録する。"""
    digest = psd._upstream_provenance_digest(_upstream_records(particles))
    particles["upstream_provenance_hash"] = [digest] * len(particles["object_id"])
    return particles


def _run(particles=None, calibration=None, **kwargs):
    particles = _particles() if particles is None else particles
    return psd.particle_size_distribution(
        particles, _calibration() if calibration is None else calibration,
        measurement_date="2026-11-23", bootstrap_samples=200,
        upstream_records=_upstream_records(particles), **kwargs)


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
                                               "correction_method": "experimental Horvitz-Thompson",
                                               "uncertainty_dependence": "independent"}}


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
    p = _particles(diameter=tuple([1.0] * 29 + [100.0]), repeats=1)
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
    _seal(p)
    r = _run(p)
    assert r["particle_rows"][0]["accepted"] is False
    bad = copy.deepcopy(p)
    bad["split_status"][0] = "isolated"
    with pytest.raises(ValueError, match="undetermined"):
        _run(bad)


def test_component_record_must_be_coherent_and_determined_count_must_equal_reported_rows():
    p = _particles(diameter=(10.0,), repeats=30)
    p["component_id"] = ["c0"] * 30
    p["upstream_component_label"] = [1] * 30
    p["upstream_split_label"] = list(range(1, 31))
    p["split_status"] = ["split"] * 30
    p["count_interval_lo"] = [29] * 30
    p["count_interval_hi"] = [29] * 30
    upstream = _upstream_records(p)
    p["upstream_provenance_hash"] = [psd._upstream_provenance_digest(upstream)] * 30
    with pytest.raises(ValueError, match="exactly its declared count"):
        psd.particle_size_distribution(p, _calibration(), measurement_date="2026-11-23", bootstrap_samples=200,
                                       upstream_records=upstream)
    p = _particles(diameter=(10.0,), repeats=30)
    del p["upstream_provenance_hash"]
    with pytest.raises(ValueError, match="upstream_provenance_hash"):
        _run(p)


def test_rejects_thirty_arbitrary_component_ids_with_a_copied_digest():
    p = _particles(diameter=(10.0,), repeats=30)
    p["component_id"] = ["forged-%02d" % i for i in range(30)]
    p["upstream_component_label"] = list(range(101, 131))
    p["upstream_provenance_hash"] = ["a" * 64] * 30
    with pytest.raises(ValueError, match="does not match recomputed"):
        _run(p)


def test_rejects_thirty_distinct_component_ids_claiming_one_upstream_label():
    p = _particles(diameter=(10.0,), repeats=30)
    p["upstream_component_label"] = [1] * 30
    p["upstream_split_label"] = list(range(1, 31))
    p["component_id"] = ["forged-%02d" % i for i in range(30)]
    upstream = _upstream_records(p)
    p["count_interval_lo"] = [30] * 30
    p["count_interval_hi"] = [30] * 30
    p["upstream_provenance_hash"] = [psd._upstream_provenance_digest(upstream)] * 30
    with pytest.raises(ValueError, match="one-to-one"):
        psd.particle_size_distribution(p, _calibration(), measurement_date="2026-11-23", bootstrap_samples=200,
                                       upstream_records=upstream)


def test_rejects_rows_that_do_not_cover_actual_blob_split_labels():
    p = _particles(diameter=(10.0,), repeats=30)
    upstream = _upstream_records(p)
    p["upstream_split_label"][-1] = 999
    p["upstream_provenance_hash"] = [psd._upstream_provenance_digest(upstream)] * 30
    with pytest.raises(ValueError, match="blob_split labels"):
        psd.particle_size_distribution(p, _calibration(), measurement_date="2026-11-23", bootstrap_samples=200,
                                       upstream_records=upstream)


def test_rejects_thirty_rows_reusing_one_actual_split_label():
    p = _particles(diameter=(10.0,), repeats=30)
    p["component_id"] = ["c0"] * 30
    p["upstream_component_label"] = [1] * 30
    p["upstream_split_label"] = [1] * 30
    p["split_status"] = ["split"] * 30
    p["count_interval_lo"] = [30] * 30
    p["count_interval_hi"] = [30] * 30
    one_area = int(round(float(p["area_px2"][0])))
    upstream = {"blob_split": np.ones((1, one_area), dtype=int),
                "blob_count_interval": {"components": {"label": np.array([1]), "lo": np.array([30]),
                                                           "hi": np.array([30]), "status": np.array(["determined"])}}}
    p["upstream_provenance_hash"] = [psd._upstream_provenance_digest(upstream)] * 30
    with pytest.raises(ValueError, match="upstream_split_label must be unique"):
        psd.particle_size_distribution(p, _calibration(), measurement_date="2026-11-23", bootstrap_samples=200,
                                       upstream_records=upstream)


def test_rejects_particle_dimensions_not_measured_from_its_split_region():
    p = _particles(diameter=(10.0,), repeats=30)
    upstream = _upstream_records(p)
    p["area_px2"][7] += 1.0
    p["upstream_provenance_hash"] = [psd._upstream_provenance_digest(upstream)] * 30
    with pytest.raises(ValueError, match="area_px2 does not match"):
        psd.particle_size_distribution(p, _calibration(), measurement_date="2026-11-23", bootstrap_samples=200,
                                       upstream_records=upstream)
    p = _particles(diameter=(10.0,), repeats=30)
    upstream = _upstream_records(p)
    p["diameter_px"][7] += 1.0
    p["upstream_provenance_hash"] = [psd._upstream_provenance_digest(upstream)] * 30
    with pytest.raises(ValueError, match="diameter_px does not match"):
        psd.particle_size_distribution(p, _calibration(), measurement_date="2026-11-23", bootstrap_samples=200,
                                       upstream_records=upstream)


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
    assert "physical-domain rejection sampling" in a["policy"]["border_uncertainty_propagation"]
    assert "correlations are unsupported" in a["policy"]["border_uncertainty_propagation"]


def test_border_correction_requires_an_explicit_independence_assumption():
    p = _particles(repeats=10, touches_border=[True] + [False] * 29, **_border_columns(30))
    p["border_correction_provenance"]["uncertainty_dependence"] = "correlated"
    with pytest.raises(ValueError, match="correlated inputs"):
        _run(p, border_policy="correct")


def test_border_probability_with_a_physically_invalid_tail_is_rejected_instead_of_clipped():
    p = _particles(repeats=10, touches_border=[True] + [False] * 29,
                   **_border_columns(30, probability=.05, uncertainty=.025))
    with pytest.raises(ValueError, match="six-sigma physical tail"):
        _run(p, border_policy="correct")


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
                                                            "correction_method": "experimental Horvitz-Thompson",
                                                            "uncertainty_dependence": "independent"})
        report = _run(rows, border_policy="correct", seed=int(origin) + 8)
        corrected_median = report["quantiles"]["number"]["D50"]["value"] / .001
        windows.append((abs(np.median(raw) - np.median(truth)), abs(corrected_median - np.median(truth))))
    raw_bias, corrected_bias = np.mean(windows, axis=0)
    assert corrected_bias < raw_bias


def test_post_hoc_400_trial_conditional_coverage_observation_drives_the_figure_values():
    summary = psd._conditional_simultaneous_coverage_validation()
    assert summary["trials"] == 400
    assert summary["successes"] == 376
    assert summary["observed_proportion"] == pytest.approx(.94)
    assert summary["wilson_lower_95"] == pytest.approx(.9123, abs=.0001)
    assert summary["interpretation"] == "post_hoc_exploratory_observation"


def test_effective_n_sweep_records_coverage_and_width_near_provisional_gate():
    """Measure the declared 15/20/30/45/60 effective-n neighbourhood / 閾値近傍を測る。"""
    rng = np.random.default_rng(814)
    population = rng.lognormal(np.log(20.0), .12, 100_000)
    target = psd._weighted_midpoint_dx(population, np.ones_like(population), 50) * .001
    rows = []
    trials = 80
    for effective_n in (15, 20, 30, 45, 60):
        covered, widths = 0, []
        statuses = []
        for trial in range(trials):
            sample = rng.choice(population, effective_n)
            report = _run(_particles(diameter=tuple(sample), repeats=1), seed=10_000 + effective_n * 100 + trial)
            interval = report["quantiles"]["number"]["D50"]
            statuses.append(interval["status"])
            if interval["status"] == "estimated":
                covered += interval["ci_lower"] <= target <= interval["ci_upper"]
                widths.append(interval["ci_upper"] - interval["ci_lower"])
        if effective_n < psd.MIN_EFFECTIVE_PARTICLES:
            assert set(statuses) == {"insufficient_sample"}
            rows.append((effective_n, "suppressed", "not applicable"))
        else:
            assert len(widths) == trials and all(width > 0 for width in widths)
            rows.append((effective_n, "%d/%d = %.1f%%" % (covered, trials, 100 * covered / trials),
                         "%.6f mm" % float(np.mean(widths))))
    print("effective-n sweep (number D50): " + "; ".join("n=%s coverage=%s width=%s" % row for row in rows))
