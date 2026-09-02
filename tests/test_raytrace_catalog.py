# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""raytrace additions of 2026-09-03: Sellmeier glass catalogue, aspheres, chromatic shift.

* Every catalogue entry reproduces the manufacturer's d-line index and Abbe
  number (the Sellmeier constants were checked digit by digit against the
  refractiveindex.info database mirror; an nd error above 1e-4 means a typo).
* A plano-convex N-BK7 singlet with the flat toward a distant object and a
  hyperboloidal exit surface (``k = −n²``, Descartes) is stigmatic — RMS spot
  below 1e-9 mm — while the spherical version blurs to 0.5 mm. A wrong
  aspheric normal or intersection cannot pass that.
* An even polynomial with ``A4 = k c³/8`` on a spherical base has the same
  Seidel S_I as the conic and traces to within 5e-4 mm of it at f/16.
* The aspheric normal equals a central finite difference of the sag.
* The real-glass doublet's axial colour is at least 4x below the singlet's and
  its lateral colour is zero on axis, non-zero off axis.
"""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import raytrace as RT  # noqa: E402

INF = float("inf")

# d-line index and Abbe number from the Schott data sheets / Malitson papers
CATALOG_ND_VD = {
    "N-BK7": (1.51680, 64.17), "N-K5": (1.52249, 59.48), "N-BAK4": (1.56883, 55.98),
    "N-SK16": (1.62041, 60.32), "N-SSK5": (1.65844, 50.88), "N-BAF10": (1.67003, 47.11),
    "N-LAK22": (1.65113, 55.89), "N-LAK9": (1.69100, 54.71), "N-LASF9": (1.85025, 32.17),
    "N-FK51A": (1.48656, 84.47), "N-F2": (1.62005, 36.43), "N-SF2": (1.64769, 33.82),
    "N-SF5": (1.67271, 32.25), "N-SF10": (1.72828, 28.53), "N-SF11": (1.78472, 25.68),
    "N-SF6": (1.80518, 25.36), "N-SF57": (1.84666, 23.78),
    "SILICA": (1.45846, 67.8), "CAF2": (1.43385, 95.0), "SAPPHIRE": (1.76817, 72.3),
}


@pytest.mark.parametrize("name", sorted(CATALOG_ND_VD))
def test_catalog_glass_reproduces_the_data_sheet_nd_and_vd(name):
    g = RT.glass_catalog(name)
    nd, vd = CATALOG_ND_VD[name]
    assert abs(g["nd"] - nd) < 1e-4, (name, g["nd"], nd)
    assert abs(g["vd"] - vd) < 0.3, (name, g["vd"], vd)
    assert RT.refractive_index(name) == pytest.approx(g["nd"])
    assert RT.refractive_index(g, RT.WL_F) > RT.refractive_index(g, RT.WL_C)


def test_catalog_listing_aliases_and_errors():
    names = RT.glass_catalog()
    assert set(CATALOG_ND_VD) == set(names)
    assert RT.glass_catalog("bk7")["name"] == "N-BK7"
    assert RT.glass_catalog("fused silica")["name"] == "SILICA"
    with pytest.raises(ValueError):
        RT.glass_catalog("UNOBTAINIUM")
    with pytest.raises(ValueError):
        RT.refractive_index("N-BK7", 5.0)            # outside the fit range
    with pytest.raises(ValueError):
        RT.sellmeier(1.0, 0.0, 0.0, 10.0, 0.0, 0.0)  # pole above the visible -> n < 1
    with pytest.raises(ValueError):
        RT.sellmeier(float("nan"), 0, 0, 0, 0, 0)


def test_cauchy_model_is_close_to_the_real_curve_for_bk7():
    cauchy = RT.glass(1.5168, 64.17)
    for wl in (RT.WL_F, 0.55, RT.WL_D, RT.WL_C):
        assert abs(RT.refractive_index(cauchy, wl) - RT.refractive_index("N-BK7", wl)) < 2e-4


def test_catalog_glass_flows_through_a_prescription_and_tolerances():
    s = RT.example_system("catalog_doublet")
    p = RT.paraxial_trace(s)
    assert abs(p["efl"] - 96.6) < 0.2
    t = RT.tolerance_analysis(s, trials=4, tolerances={"index": 0.001})
    assert t["failed"] == 0
    assert any(r["parameter"] == "n" for r in t["sensitivity"])
    g = RT._index_offset("N-BK7", 1e-3)
    assert RT.refractive_index(g) == pytest.approx(RT.refractive_index("N-BK7") + 1e-3)


def test_plano_hyperbolic_singlet_is_stigmatic_and_its_sphere_is_not():
    a = RT.example_system("asphere")
    st = RT.spot_stats(a)
    assert st["n_vignetted"] == 0
    assert st["rms_radius"] < 1e-9
    assert np.nanmax(np.abs(RT.opd_map(a))) < 1e-6
    n = RT.refractive_index("N-BK7")
    sphere = RT.lens_system([{"R": INF, "t": 5.0, "n": "N-BK7", "ap": 12.5},
                             {"R": -(n - 1.0) * 100.0, "t": None, "n": 1.0}], stop=0)
    assert RT.spot_stats(sphere)["rms_radius"] > 0.3


def test_polynomial_asphere_equals_the_conic_to_fourth_order():
    n = RT.refractive_index("N-BK7")
    R = -(n - 1.0) * 100.0
    c = 1.0 / R
    k = -n * n
    conic = RT.lens_system([{"R": INF, "t": 5.0, "n": n, "ap": 3.0},
                            {"R": R, "t": None, "n": 1.0, "k": k}], stop=0)
    poly = RT.lens_system([{"R": INF, "t": 5.0, "n": n, "ap": 3.0},
                           {"R": R, "t": None, "n": 1.0, "asph": (k * c ** 3 / 8.0,)}], stop=0)
    assert RT.seidel_coefficients(poly)["total"]["S_I"] == pytest.approx(
        RT.seidel_coefficients(conic)["total"]["S_I"], abs=1e-12)
    assert RT.spot_stats(conic)["rms_radius"] < 1e-9
    assert RT.spot_stats(poly)["rms_radius"] < 5e-4
    assert RT.lens_system([{"R": 50, "t": 3, "n": 1.5, "ap": 5, "asph": (1e-6, 0.0, 0.0)},
                           {"R": INF, "t": None, "n": 1.0}])["surfaces"][0]["asph"] == (1e-6,)
    with pytest.raises(ValueError):
        RT.lens_system([{"R": 50, "t": 3, "n": 1.5, "ap": 5, "asph": 1e-6}, {"R": INF, "t": None, "n": 1.0}])
    with pytest.raises(ValueError):
        RT.lens_system([{"R": INF, "t": 3, "n": 1.5, "ap": 5, "asph": (1e-6,), "k": -1},
                        {"R": INF, "t": None, "n": 1.0}])


def test_aspheric_normal_matches_a_finite_difference_of_the_sag():
    c, k, asph = 1.0 / 40.0, -0.5, (2e-6, -3e-9)
    Q = np.array([[3.0, -4.0, 0.0], [0.5, 0.2, 0.0], [-7.0, 1.0, 0.0]])
    r2 = Q[:, 0] ** 2 + Q[:, 1] ** 2
    Q[:, 2] = RT._sag(r2, c, k, asph)
    nrm = RT._surface_normal(Q, c, k, asph)
    h = 1e-6
    for i in range(len(Q)):
        x, y = Q[i, 0], Q[i, 1]
        dzdx = (RT._sag((x + h) ** 2 + y * y, c, k, asph) - RT._sag((x - h) ** 2 + y * y, c, k, asph)) / (2 * h)
        dzdy = (RT._sag(x * x + (y + h) ** 2, c, k, asph) - RT._sag(x * x + (y - h) ** 2, c, k, asph)) / (2 * h)
        g = np.array([-dzdx, -dzdy, 1.0])
        g /= np.linalg.norm(g)
        assert np.allclose(nrm[i], g, atol=1e-7)


def test_aspheric_ray_lands_on_the_surface():
    # the Newton intersection must put the point *on* the asphere (sag residual ~0)
    s = RT.lens_system([{"R": 40.0, "t": 6.0, "n": "N-BK7", "ap": 10.0, "k": -0.6, "asph": (1e-6, -2e-9)},
                        {"R": -60.0, "t": None, "n": 1.0}], stop=0)
    b = RT.ray_bundle(s, rings=5)
    P = b["points"][b["valid"], 1, :]                    # on surface 0
    r2 = P[:, 0] ** 2 + P[:, 1] ** 2
    assert np.max(np.abs(P[:, 2] - RT._sag(r2, 1.0 / 40.0, -0.6, (1e-6, -2e-9)))) < 1e-9


def test_chromatic_shift_doublet_beats_singlet_and_reports_lateral_colour():
    single = RT.chromatic_shift(RT.lens_system())
    doub = RT.chromatic_shift(RT.example_system("catalog_doublet"))
    assert abs(single["axial_color"]) > 1.0                      # ~1.5 mm F-C shift for a BK7 f/4 f=100
    assert abs(doub["axial_color"]) < abs(single["axial_color"]) / 4
    assert doub["rms_polychromatic"] < single["rms_polychromatic"]
    assert [r["wavelength_um"] for r in doub["per_wavelength"]] == [RT.WL_F, RT.WL_D, RT.WL_C]
    assert doub["lateral_color"] == 0.0                          # on axis
    off = RT.chromatic_shift(RT.example_system("catalog_doublet"), field=3.0)
    assert off["lateral_color"] != 0.0 and abs(off["lateral_color"]) < 0.05
    with pytest.raises(ValueError):
        RT.chromatic_shift(RT.lens_system(), wavelengths=[RT.WL_D])
    with pytest.raises(ValueError):
        RT.chromatic_shift({"surfaces": []})


# --------------------------------------------------------------------------- #
# Codex review (2026-09-03): verified findings pinned                          #
# --------------------------------------------------------------------------- #
def test_real_chief_ray_passes_through_the_stop_centre_behind_a_strong_surface():
    s = RT.lens_system([{"R": 15.0, "t": 6.0, "n": 1.8, "ap": 8.0},
                        {"R": -20.0, "t": 4.0, "n": 1.0, "ap": 2.0},        # the stop, behind a strong surface
                        {"R": -40.0, "t": None, "n": 1.0}], stop=1, field=10.0)
    for wl in (RT.WL_F, RT.WL_D):
        c = RT.chief_ray(s, wavelength_um=wl)
        q = c["points"][2]                                       # points[0] launch, [1] surface 0, [2] surface 1
        assert c["valid"] and np.hypot(q[0], q[1]) < 1e-8, q
    # the paraxial aim alone misses by a visible amount (this is what the Newton aiming fixes)
    para = RT.paraxial_trace(s)
    P, D, _ = RT._launch(s, np.array([0.0]), np.array([0.0]), 10.0, para)
    q0 = RT.trace_rays(s, P, D)["points"][0, 2, :2]
    assert np.hypot(q0[0], q0[1]) > 1e-3
    # the bundle is centred on that aimed ray
    b = RT.ray_bundle(s, field=10.0, rings=3)
    assert np.allclose(b["points"][b["chief_index"], 2, :2], 0.0, atol=1e-8)


def test_validators_reject_bool_str_and_fractional_stop():
    with pytest.raises(ValueError):
        RT.lens_system(stop=0.9)
    with pytest.raises(ValueError):
        RT.lens_system([{"R": 50, "t": 3, "n": 1.5, "ap": 5, "mirror": "false"}, {"R": INF, "t": None, "n": 1.0}])
    with pytest.raises(ValueError):
        RT.lens_system([{"R": "50", "t": 3, "n": 1.5, "ap": 5}, {"R": INF, "t": None, "n": 1.0}])
    with pytest.raises(ValueError):
        RT.lens_system([{"R": 50, "t": True, "n": 1.5, "ap": 5}, {"R": INF, "t": None, "n": 1.0}])
    with pytest.raises(ValueError):
        RT.trace_rays(RT.lens_system(), [[0, 0, -1]], [[0, 0, 0]])
    with pytest.raises(ValueError):
        RT._index_offset(1.0, -0.01)
    g = RT.glass_catalog("N-BK7")
    g["offset"] = float("nan")
    with pytest.raises(ValueError):
        RT.refractive_index(g)
    with pytest.raises(ValueError):
        RT.refractive_index({"sellmeier": (1.0, 0.0, 0.0, RT.WL_D ** 2, 0.0, 0.0), "offset": 0.0}, RT.WL_D)
    with pytest.raises(ValueError):
        RT.refractive_index({"sellmeier": (1.0, 0.0, 0.0), "offset": 0.0})


def test_index_tolerance_never_touches_air_gaps():
    s = RT.example_system("doublet")
    t = RT.tolerance_analysis(s, trials=3, tolerances={"index": 0.5, "radius_pct": 0, "thickness_mm": 0,
                                                       "decenter_mm": 0, "tilt_deg": 0})
    assert t["failed"] == 0                                      # a 0.5 index step on air would raise (n < 1)
    assert all(r["surface"] != 2 for r in t["sensitivity"] if r["parameter"] == "n")


def test_with_wavelength_keeps_everything_but_the_index():
    s = RT.example_system("catalog_doublet")
    w = RT.with_wavelength(s, RT.WL_F)
    assert w["wavelength_um"] == RT.WL_F
    assert w["surfaces"][0]["n_value"] > s["surfaces"][0]["n_value"]
    assert [q["R"] for q in w["surfaces"]] == [q["R"] for q in s["surfaces"]]
