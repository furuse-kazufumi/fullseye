"""External-truth gates for the manufacturing-tolerance operations."""
import math

import numpy as np
import pytest

import lenstol as LT
import raytrace as RT


def test_table_validation_and_independent_row_streams():
    s = RT.example_system("singlet")
    a = LT.tolerance_table(s, defaults={"radius_pct": 0.1})
    b = LT.tolerance_table(s, defaults={"radius_pct": 0.1, "thickness_mm": 0.02})
    ca = LT.tolerance_criteria(rms_spot={"max": 1.0}, fields=[0.0], rings=2)
    ra = LT.tolerance_monte_carlo(s, a, ca, trials=8, seed=17, _return_draws=True)
    rb = LT.tolerance_monte_carlo(s, b, ca, trials=8, seed=17, _return_draws=True)
    aid = a[0]["id"]
    assert len(ra["draws"][aid]) == 8
    assert np.array_equal(ra["draws"][aid], rb["draws"][aid])
    with pytest.raises(ValueError, match="row .*distribution"):
        LT.tolerance_table(s, overrides=[{"kind": "radius_pct", "surface": 0,
                                          "tolerance": 1, "distribution": "triangle"}])


def test_distribution_variances_are_closed_forms():
    assert LT._distribution_variance("uniform", 3.0, None) == pytest.approx(3.0)
    assert LT._distribution_variance("normal", 3.0, None) == pytest.approx(1.0)
    # N(0,1) truncated at +/-3: 1 - 6 phi(3)/(2 Phi(3)-1)
    expected = 1.0 - 6.0 * math.exp(-4.5) / math.sqrt(2 * math.pi) / math.erf(3 / math.sqrt(2))
    assert LT._distribution_variance("truncated_normal", 3.0, None) == pytest.approx(expected)
    assert expected != pytest.approx(1.0)  # broken-probe twin: ignoring truncation is detectable


def test_group_decenter_is_exact_surface_expansion():
    s = RT.example_system("doublet")
    row = {"kind": "group_decenter_mm", "surfaces": [0, 1], "tolerance": 0.1}
    a = LT._apply_row(s, LT._normalise_row(s, row, 0), 0.037)
    surf = [dict(q) for q in s["surfaces"]]
    for i in (0, 1):
        surf[i]["decenter"] = (surf[i]["decenter"][0], surf[i]["decenter"][1] + 0.037)
    b = RT.lens_system(surf, stop=s["stop"], object_mm=s["object_mm"],
                       wavelength_um=s["wavelength_um"], index_object=s["index_object"],
                       image_mm=s["image_mm"], field=s["field"])
    assert a["surfaces"] == b["surfaces"]
    one = LT._apply_row(s, LT._normalise_row(s, {"kind": "decenter_mm", "surface": 0,
                                                 "tolerance": 0.1}, 0), 0.037)
    assert one["surfaces"] != a["surfaces"]


def test_wilson_interval_contains_binomial_fraction():
    lo, hi = LT._wilson(73, 100)
    assert lo < 0.73 < hi
    assert (hi - lo) > 0.01  # broken-probe twin: a zero-width interval fails


def test_nominal_mtf_is_lensimage_zero_defocus():
    import lensimage as LI
    s = RT.lens_system([{"f": 50.0, "t": 50.0, "n": 1.0, "ap": 3.0}], image_mm=50.0)
    c = LT.tolerance_criteria(mtf={"frequency_cpmm": 20.0, "min": 0.1}, fields=[0.0],
                              wavelengths=[s["wavelength_um"]], psf_size=32)
    got = LT._evaluate(s, c)["mtf"]
    ref = LI.through_focus_mtf(s, frequency_cpmm=[20.0], defocus_mm=[0.0], field=0.0,
                               wavelength_um=s["wavelength_um"], size=32)
    want = float(0.5 * (ref["tangential"][0, 0] + ref["sagittal"][0, 0]))
    assert got == pytest.approx(want, abs=1e-12)
    with pytest.raises(ValueError, match="diffraction"):
        LT._check_mtf_physical(s, 20.0, 1.000001, 0.0, s["wavelength_um"], 32)


def test_histogram_counts_and_seed_determinism():
    s = RT.example_system("singlet")
    tab = LT.tolerance_table(s, overrides=[{"kind": "radius_pct", "surface": 0,
                                            "tolerance": 0.01}])
    crit = LT.tolerance_criteria(efl={"max": 200.0}, fields=[0.0])
    a = LT.tolerance_monte_carlo(s, tab, crit, trials=31, seed=4)
    b = LT.tolerance_monte_carlo(s, tab, crit, trials=31, seed=4)
    assert a["criteria"]["efl"] == b["criteria"]["efl"]
    assert sum(a["criteria"]["efl"]["histogram"]["counts"]) == 31


def test_wedge_thin_prism_closed_form_and_broken_probe():
    # A weak wedge followed by an ideal 50 mm imaging surface: dy=f(n-1)alpha.
    s = RT.lens_system([{"R": math.inf, "t": 2.0, "n": 1.5, "ap": 5.0},
                        {"R": math.inf, "t": 10.0, "n": 1.0, "ap": 5.0},
                        {"f": 50.0, "t": 50.0, "n": 1.0, "ap": 5.0}], image_mm=50.0)
    row = LT._normalise_row(s, {"kind": "wedge_arcmin", "surface": 1,
                                "tolerance": 1.0}, 0)
    p = LT._apply_row(s, row, 1.0)
    actual = abs(RT.chief_ray(p, 0.0)["image_y"])
    closed = 50.0 * (1.5 - 1.0) * math.radians(1.0 / 60.0)
    assert actual == pytest.approx(closed, rel=5e-3)
    assert actual != pytest.approx(50.0 * 1.5 * math.radians(1.0 / 60.0), rel=5e-3)


def test_irregularity_real_ray_opd_matches_zernike_closed_form():
    # Convention: one fringe = lambda/2 sag PV coefficient; RMS(x²-y²)=1/sqrt(6).
    s = RT.lens_system([{"R": math.inf, "t": 3.0, "n": 1.5, "ap": 5.0},
                        {"R": math.inf, "t": 20.0, "n": 1.0, "ap": 5.0},
                        {"f": 50.0, "t": 50.0, "n": 1.0, "ap": 5.0}], image_mm=50.0)
    row = LT._normalise_row(s, {"kind": "irregularity_fringes", "surface": 0,
                                "tolerance": 1.0}, 0)
    p = LT._apply_row(s, row, 1.0)
    a = RT.opd_samples(s, size=129)
    b = RT.opd_samples(p, size=129)
    valid = a[3] & b[3]
    assert int(valid.sum()) > 12000
    actual = float(np.std(b[2][valid] - a[2][valid]))
    closed = (1.5 - 1.0) / (2.0 * math.sqrt(6.0))
    assert actual == pytest.approx(closed, rel=0.02)
    assert actual != pytest.approx((1.5 - 1.0) / 2.0, rel=0.02)


def test_irregularity_fringes_double_the_transmitted_opd():
    s = RT.lens_system([{"R": math.inf, "t": 3.0, "n": 1.5, "ap": 5.0},
                        {"R": math.inf, "t": 20.0, "n": 1.0, "ap": 5.0}], image_mm=20.0)
    row = LT._normalise_row(s, {"kind": "irregularity_fringes", "surface": 0,
                                "tolerance": 2.0}, 0)
    base = RT.opd_samples(s, size=65)
    one = RT.opd_samples(LT._apply_row(s, row, 1.0), size=65)
    two = RT.opd_samples(LT._apply_row(s, row, 2.0), size=65)
    valid = base[3] & one[3] & two[3]
    opd1 = np.std(one[2][valid] - base[2][valid])
    opd2 = np.std(two[2][valid] - base[2][valid])
    assert opd2 == pytest.approx(2.0 * opd1, rel=2e-3)
    assert opd2 != pytest.approx(opd1, rel=0.1)


def test_tilted_parallel_plate_lateral_shift_closed_form():
    t, n, angle = 5.0, 1.5, 0.1
    s = RT.lens_system([{"R": math.inf, "t": t, "n": n, "ap": 20.0},
                        {"R": math.inf, "t": 20.0, "n": 1.0, "ap": 20.0}], image_mm=20.0)
    surfaces = [dict(q) for q in s["surfaces"]]
    for q in surfaces:
        q["tilt"] = (angle, 0.0)
    tilted = RT.lens_system(surfaces, image_mm=20.0)
    actual = abs(RT.chief_ray(tilted, 0.0)["image_y"])
    a = math.radians(angle)
    closed = t * math.sin(a) * (1.0 - math.cos(a) / math.sqrt(n * n - math.sin(a) ** 2))
    assert actual == pytest.approx(closed, abs=1e-6)
    assert actual != pytest.approx(t * (n - 1.0) * a, abs=1e-6)


def test_finite_conjugate_decenter_moves_centroid_but_not_spot():
    delta = 0.01
    s = RT.lens_system([{"f": 50.0, "t": 100.0, "n": 1.0, "ap": 20.0}],
                       object_mm=100.0, image_mm=100.0)
    row = LT._normalise_row(s, {"kind": "decenter_mm", "surface": 0,
                                "tolerance": delta}, 0)
    p = LT._apply_row(s, row, delta)
    b0 = RT.ray_bundle(s, field=0.0, rings=4, pupil_fill=0.8)
    b1 = RT.ray_bundle(p, field=0.0, rings=4, pupil_fill=0.8)
    assert np.all(b0["valid"]) and np.all(b1["valid"])
    m = RT.paraxial_trace(s)["magnification"]
    shift = float(b1["image_xy"][:, 1].mean() - b0["image_xy"][:, 1].mean())
    assert shift == pytest.approx(delta * (1.0 - m), abs=1e-4)
    c0 = b0["image_xy"] - b0["image_xy"].mean(axis=0)
    c1 = b1["image_xy"] - b1["image_xy"].mean(axis=0)
    assert np.sqrt(np.mean(np.sum((c1 - c0) ** 2, axis=1))) < 1e-9
    assert abs(shift) > 1000 * 1e-9


def test_linear_regime_10000_trials_and_distribution_standard_deviations():
    s = RT.example_system("singlet")
    table = LT.tolerance_table(s, defaults={"radius_pct": 0.01,
                                            "thickness_mm": 0.005, "index": 0.001})
    crit = LT.tolerance_criteria(efl={}, back_focus={})
    sensitivity = LT.tolerance_sensitivity(s, table, crit)
    run = LT.tolerance_monte_carlo(s, table, crit, trials=10_000, seed=123)
    assert len(sensitivity["rss_std"]) == 2
    for name, predicted in sensitivity["rss_std"].items():
        assert run["criteria"][name]["std"] == pytest.approx(predicted, rel=0.05)
        assert run["criteria"][name]["std"] > 0.01
    for distribution in ("uniform", "normal", "truncated_normal"):
        row = {"id": distribution, "kind": "radius_pct", "surface": 0,
               "tolerance": 0.01, "distribution": distribution, "sigma": None}
        row = LT._normalise_row(s, row, 0)
        measured = float(LT._draws(row, 10_000, 0).std())
        closed = math.sqrt(LT._distribution_variance(distribution, 0.01, None))
        assert measured == pytest.approx(closed, rel=0.01)
    uniform = LT._normalise_row(s, {"kind": "radius_pct", "surface": 0,
                                    "tolerance": 0.01}, 0)
    assert LT._draws(uniform, 10_000, 0).std() == pytest.approx(0.01 / math.sqrt(3), rel=0.01)


def test_yield_matches_erf_wilson_and_histogram_successes():
    s = RT.example_system("singlet")
    table = LT.tolerance_table(s, defaults={}, overrides=[
        {"kind": "radius_pct", "surface": 0, "tolerance": 0.01, "distribution": "normal"}])
    probe = LT.tolerance_criteria(efl={})
    sensitivity = LT.tolerance_sensitivity(s, table, probe)
    nominal = sensitivity["nominal"]["efl"]
    deriv = abs(sensitivity["rows"][0]["derivative"]["efl"])
    criteria = LT.tolerance_criteria(efl={"max": nominal + deriv * 0.01 / 3.0})
    run = LT.tolerance_monte_carlo(s, table, criteria, trials=10_000, seed=71)
    closed = 0.5 * (1.0 + math.erf(1.0 / math.sqrt(2.0)))
    assert run["yield"] == pytest.approx(closed, abs=0.01)
    assert run["yield_wilson95"][0] <= closed <= run["yield_wilson95"][1]
    assert sum(run["criteria"]["efl"]["histogram"]["counts"]) == 10_000
    assert run["passed"] != 0


def test_pure_gap_compensation_travel_and_second_compensator_not_worse():
    s = RT.lens_system([{"R": 40.0, "t": 4.0, "n": 1.52, "ap": 8.0},
                        {"R": -30.0, "t": 1.5, "n": 1.0, "ap": 8.0},
                        {"R": -45.0, "t": 3.0, "n": 1.62, "ap": 8.0,
                         "decenter": (0.0, 0.02)},
                        {"R": 60.0, "t": 55.0, "n": 1.0, "ap": 8.0}], image_mm=55.0)
    criteria = LT.tolerance_criteria(rms_spot={})
    gap = LT._normalise_row(s, {"kind": "thickness_mm", "surface": 1,
                                "tolerance": 0.01}, 0)
    perturbed = LT._apply_row(s, gap, 0.007)
    nominal = LT._evaluate(s, criteria)
    one = LT.compensators(["t3"], criterion="rms_spot", iterations=12)
    two = LT.compensators(["t3", "t1"], criterion="rms_spot", iterations=12,
                          bounds={"t3": [50.0, 60.0], "t1": [1.4, 1.6]})
    p1, _ = LT._compensate(perturbed, nominal, criteria, one)
    p2, _ = LT._compensate(perturbed, nominal, criteria, two)
    assert LT._evaluate(p2, criteria)["rms_spot"] <= LT._evaluate(p1, criteria)["rms_spot"] + 1e-12
    back = LT.tolerance_criteria(back_focus={})
    pure, travel = LT._compensate(perturbed, LT._evaluate(s, back), back,
                                  LT.compensators(["t1"], criterion="back_focus", iterations=8))
    assert abs(travel["t1"]) == pytest.approx(0.007, abs=1e-6)
    assert abs(LT._evaluate(pure, back)["back_focus"] - LT._evaluate(s, back)["back_focus"]) < 1e-9


def test_uniform_back_focus_rms_matches_legacy_2000_trials():
    s = RT.example_system("singlet")
    tolerances = {"radius_pct": 0.01, "thickness_mm": 0.0, "index": 0.0,
                  "decenter_mm": 0.0, "tilt_deg": 0.0}
    legacy = RT.tolerance_analysis(s, tolerances=tolerances, trials=2_000, seed=19,
                                   compensator="back_focus")
    table = LT.tolerance_table(s, defaults={"radius_pct": 0.01})
    criteria = LT.tolerance_criteria(rms_spot={}, rings=6)
    modern = LT.tolerance_monte_carlo(
        s, table, criteria,
        compensators=LT.compensators("t1", criterion="rms_spot", iterations=8),
        trials=2_000, seed=19)
    got, old = modern["criteria"]["rms_spot"]["std"], legacy["rms_spot"]["std"]
    assert got == pytest.approx(old, rel=0.03)
    assert got > 1e-6 and old > 1e-6
