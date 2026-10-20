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
