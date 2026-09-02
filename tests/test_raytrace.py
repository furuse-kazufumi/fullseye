# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""raytrace — closed-form ground truth for the real-ray lens-design module.

Like ``tests/test_optics.py``, every assertion here is an identity with a known
answer rather than a golden file: the thick-lens lensmaker equation agrees with
the surface-by-surface paraxial trace to 1e-9; a single refracting surface
obeys ``n'/s' = (n'-n)/R - n/s``; an on-axis paraboloid mirror is stigmatic
(RMS spot < 1e-9 mm, OPD < 1e-6 waves) while the same-radius sphere is not;
the third-order Seidel sums reproduce a least-squares fit of the *exact*
ray-traced OPD at small aperture (W040 within 2 %, W131 / W222 / W220 within
1-3 %) and the fit's excess over Seidel *grows* with field, as higher orders
must; the tangential ray fan is antisymmetric; and the Monte-Carlo tolerance
run is deterministic for a seed. The doublet numbers are pinned to what was
measured (EFL 96.63 mm, axial colour 4.8x below the singlet's), not to a
round target.

The ledger half checks the ``design`` category of ``opsoptics``: every op is
reachable from the chain fuzzer, returns its declared type, and refuses a
random ``table`` with ``ValueError`` (never a TypeError/KeyError).
"""
import json
import math
import os
import re
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import raytrace as RT  # noqa: E402
import opsoptics  # noqa: E402

INF = float("inf")
DESIGN_OPS = ["lens_system", "thick_lens", "glass", "example_system",
              "paraxial_trace", "seidel_coefficients", "spot_stats",
              "tolerance_analysis", "wavefront_from_opd", "spot_diagram",
              "ray_fan", "opd_map"]


def _singlet():
    return RT.lens_system()


def _small_singlet():
    """The default singlet stopped down to a 3 mm semi-aperture: third order dominates."""
    return RT.lens_system([{"R": 51.68, "t": 5, "n": 1.5168, "ap": 3},
                           {"R": INF, "t": None, "n": 1.0}], stop=0)


# --------------------------------------------------------------------------- #
# paraxial: closed forms                                                       #
# --------------------------------------------------------------------------- #
def test_thick_lens_closed_form_equals_the_surface_by_surface_trace():
    tl = RT.thick_lens(50.0, -50.0, 5.0, 1.5168)
    pt = RT.paraxial_trace(RT.lens_system([{"R": 50, "t": 5, "n": 1.5168, "ap": 10},
                                           {"R": -50, "t": None, "n": 1.0}]))
    for k in ("efl", "bfl", "ffl", "pp_front", "pp_rear"):
        assert tl[k] == pytest.approx(pt[k], abs=1e-9), k
    assert tl["efl"] == pytest.approx(49.212999, abs=1e-6)
    assert tl["bfl"] == pytest.approx(47.536227, abs=1e-6)


def test_thick_lens_thin_limit_is_the_lensmaker_equation():
    n, R1, R2 = 1.5, 50.0, -50.0
    thin = 1.0 / ((n - 1.0) * (1.0 / R1 - 1.0 / R2))
    assert RT.thick_lens(R1, R2, 1e-9, n)["efl"] == pytest.approx(thin, rel=1e-9)
    assert RT.thick_lens(R1, R2, 0.0, n)["efl"] == pytest.approx(thin, rel=1e-12)


def test_single_refracting_surface_conjugate_and_magnification():
    """n'/s' = (n'-n)/R - n/s with n=1, n'=1.5, R=50, s=-200 -> s' = 300, m = -1."""
    s = RT.lens_system([{"R": 50, "t": None, "n": 1.5, "ap": 5}], object_mm=200.0)
    p = RT.paraxial_trace(s)
    assert p["image_mm"] == pytest.approx(300.0, abs=1e-9)
    assert p["magnification"] == pytest.approx(-1.0, abs=1e-9)


def test_default_singlet_first_order_numbers():
    p = RT.paraxial_trace(_singlet())
    assert p["efl"] == pytest.approx(100.0, abs=1e-6)
    assert p["bfl"] == pytest.approx(96.7036, abs=1e-3)
    assert p["fno"] == pytest.approx(4.0, abs=1e-9)
    assert p["ep_radius"] == pytest.approx(12.5, abs=1e-12)
    assert p["ep_position"] == pytest.approx(0.0, abs=1e-12)
    assert p["n_surfaces"] == 2


def test_concave_mirrors_have_f_equal_minus_R_over_2():
    for name in ("paraboloid", "sphere_mirror"):
        p = RT.paraxial_trace(RT.example_system(name))
        assert p["efl"] == pytest.approx(100.0, abs=1e-9), name
        assert p["bfl"] == pytest.approx(100.0, abs=1e-9), name


# --------------------------------------------------------------------------- #
# real rays: stigmatic paraboloid, spherical mirror, fans                     #
# --------------------------------------------------------------------------- #
def test_paraboloid_is_stigmatic_on_axis_and_comatic_off_axis():
    pb = RT.example_system("paraboloid")
    assert RT.spot_stats(pb)["rms_radius"] < 1e-9
    w = RT.opd_map(pb, fill=np.nan)
    assert np.isfinite(w).sum() > 100
    assert np.nanmax(np.abs(w)) < 1e-6
    rms1 = RT.spot_stats(pb, field=1.0)["rms_radius"]
    assert rms1 == pytest.approx(0.0227, abs=1e-3)
    assert rms1 > 0.01                      # coma: the paraboloid is only stigmatic on axis


def test_spherical_mirror_of_the_same_radius_has_spherical_aberration():
    rms = RT.spot_stats(RT.example_system("sphere_mirror"))["rms_radius"]
    assert rms == pytest.approx(0.1189, abs=2e-3)
    assert rms > 0.05


def test_tangential_ray_fan_is_antisymmetric_on_axis():
    fan = RT.ray_fan(_singlet(), n=5)
    assert fan.shape == (5, 2)
    np.testing.assert_allclose(fan[:, 0], [-1.0, -0.5, 0.0, 0.5, 1.0])
    np.testing.assert_allclose(fan[:, 1], [0.2222, 0.0268, 0.0, -0.0268, -0.2222], atol=1e-3)
    np.testing.assert_allclose(fan[:, 1], -fan[::-1, 1], atol=1e-12)


def test_spot_diagram_is_centred_on_the_chief_ray():
    xy = RT.spot_diagram(_singlet(), rings=4)
    assert xy.ndim == 2 and xy.shape[1] == 2
    assert np.isfinite(xy).all()
    assert np.all(xy[0] == 0.0)             # the chief ray is the first pupil sample


# --------------------------------------------------------------------------- #
# OPD vs Seidel                                                               #
# --------------------------------------------------------------------------- #
def _fit_wavefront(system, field):
    """Least squares of the exact OPD on [rho^4, rho^2, rho^2*py, py^2, py, 1] (waves)."""
    px, py, w, v = RT.opd_samples(system, field=field, size=129)
    r2 = px * px + py * py
    A = np.stack([r2 * r2, r2, r2 * py, py * py, py, np.ones_like(px)], 1)
    c, *_ = np.linalg.lstsq(A[v], w[v], rcond=None)
    return {"W040": c[0], "W020": c[1], "W131": c[2], "W222": c[3]}


def test_seidel_spherical_matches_exact_opd_at_small_aperture():
    sm = _small_singlet()
    fit = _fit_wavefront(sm, 0.0)
    w040 = RT.seidel_coefficients(sm)["waves"]["S_I"] / 8.0
    assert fit["W040"] == pytest.approx(0.0376, abs=5e-4)
    assert w040 == pytest.approx(0.0375, abs=5e-4)
    assert fit["W040"] == pytest.approx(w040, rel=0.02)


def test_seidel_coma_astigmatism_curvature_match_exact_opd_at_1_degree():
    sm = _small_singlet()
    fit = _fit_wavefront(sm, 1.0)
    se = RT.seidel_coefficients(sm, field=1.0)["waves"]
    assert fit["W131"] / (se["S_II"] / 2.0) == pytest.approx(1.013, abs=0.03)
    assert fit["W222"] == pytest.approx(se["S_III"] / 2.0, rel=0.01)
    assert fit["W020"] == pytest.approx((se["S_III"] + se["S_IV"]) / 4.0, rel=0.01)


def test_higher_orders_grow_with_field_in_a_real_trace():
    """At 5 deg the exact coma exceeds third order by ~10 %, at 1 deg by ~1 %."""
    sm = _small_singlet()
    ratio = {}
    for f in (1.0, 5.0):
        fit = _fit_wavefront(sm, f)
        se = RT.seidel_coefficients(sm, field=f)["waves"]
        ratio[f] = fit["W131"] / (se["S_II"] / 2.0)
    assert ratio[5.0] == pytest.approx(1.098, abs=0.02)
    assert ratio[5.0] > ratio[1.0]


def test_opd_sign_is_welford_undercorrected_positive():
    sg = _singlet()
    w = RT.opd_map(sg)
    assert w.shape == (64, 64)
    assert w.min() >= 0.0
    assert w.max() == pytest.approx(11.56, abs=0.02)
    assert RT.seidel_coefficients(sg)["waves"]["S_I"] / 8.0 == pytest.approx(11.29, abs=0.02)


def test_seidel_per_surface_rows_sum_to_the_total():
    se = RT.seidel_coefficients(RT.example_system("doublet"), field=3.0)
    for k in ("S_I", "S_II", "S_III", "S_IV", "S_V", "C_L", "C_T"):
        assert sum(r[k] for r in se["per_surface"]) == pytest.approx(se["total"][k], abs=1e-12)
    assert len(se["per_surface"]) == 3


def test_wavefront_from_opd_chains_zernike_fit_and_stats():
    w = RT.wavefront_from_opd(_singlet())
    assert (4, 0) in w["zernike"]
    assert w["zernike"][(4, 0)] > 0.0
    assert w["rms_opd_direct"] == pytest.approx(3.43, rel=0.05)
    assert "strehl" in w and "rms_waves" in w and "pv_opd_direct" in w
    assert w["pv_opd_direct"] > w["rms_opd_direct"]


# --------------------------------------------------------------------------- #
# doublet (pinned to the measured numbers)                                    #
# --------------------------------------------------------------------------- #
def test_doublet_efl_and_axial_colour_versus_the_singlet():
    d = RT.example_system("doublet")
    sg = _singlet()
    assert RT.paraxial_trace(d)["efl"] == pytest.approx(96.63, abs=0.5)
    cl_d = abs(RT.seidel_coefficients(d)["total"]["C_L"])
    cl_s = abs(RT.seidel_coefficients(sg)["total"]["C_L"])
    assert cl_s / cl_d == pytest.approx(4.78, abs=0.1)     # measured 2026-09-03
    assert cl_s / cl_d > 4.5
    assert RT.spot_stats(d)["rms_radius"] < RT.spot_stats(sg)["rms_radius"]
    assert RT.spot_stats(d, field=5.0)["rms_radius"] < RT.spot_stats(sg, field=5.0)["rms_radius"]


# --------------------------------------------------------------------------- #
# tolerances                                                                  #
# --------------------------------------------------------------------------- #
def test_tolerance_analysis_is_deterministic_and_centred_on_nominal():
    sg = _singlet()
    t1 = RT.tolerance_analysis(sg, trials=40, seed=1)
    t2 = RT.tolerance_analysis(sg, trials=40, seed=1)
    # NaN != NaN, so compare the serialised form (the air-side index sensitivity
    # is NaN by design: 1.0 - 0.001 < 1 is refused, reported not hidden)
    assert json.dumps(t1, sort_keys=True) == json.dumps(t2, sort_keys=True)
    assert t1["failed"] == 0 and t1["trials"] == 40
    assert t1["rms_spot"]["mean"] == pytest.approx(t1["nominal"]["rms_spot"], abs=2e-3)
    assert t1["nominal"]["rms_spot"] == pytest.approx(0.1325, abs=2e-3)
    assert 4e-4 < t1["rms_spot"]["std"] < 1.6e-3
    assert t1["rms_spot"]["p5"] <= t1["rms_spot"]["mean"] <= t1["rms_spot"]["p95"] <= t1["rms_spot"]["worst"]
    top = t1["sensitivity"][0]
    assert top["parameter"] == "R" and top["surface"] == 0
    assert top["d_efl"] == pytest.approx(0.5, abs=1e-6)     # 0.5 % of R on a f=100 lens
    with pytest.raises(ValueError, match="unknown tolerance"):
        RT.tolerance_analysis(sg, {"colour": 1.0}, trials=1)


# --------------------------------------------------------------------------- #
# glass                                                                       #
# --------------------------------------------------------------------------- #
def test_glass_cauchy_model_hits_the_d_line_and_the_fc_dispersion():
    g = RT.glass(1.5168, 64.17)
    assert RT.refractive_index(g, RT.WL_D) == pytest.approx(1.5168, abs=1e-12)
    dn = RT.refractive_index(g, RT.WL_F) - RT.refractive_index(g, RT.WL_C)
    assert dn == pytest.approx((1.5168 - 1.0) / 64.17, abs=1e-12)
    assert RT.refractive_index((1.5168, 64.17), RT.WL_D) == pytest.approx(1.5168, abs=1e-12)
    assert RT.refractive_index(1.7) == 1.7
    with pytest.raises(ValueError):
        RT.refractive_index(0.9)
    with pytest.raises(ValueError):
        RT.glass(0.9, 60.0)


# --------------------------------------------------------------------------- #
# fail-closed                                                                 #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad", [
    lambda: RT.lens_system([{"R": 0.0, "t": 1, "n": 1.5, "ap": 1}]),          # zero radius
    lambda: RT.lens_system([{"R": 10, "t": -1, "n": 1.5, "ap": 1}]),           # negative thickness
    lambda: RT.lens_system([{"R": 10, "t": None, "n": 1.5}]),                  # no stop aperture
    lambda: RT.lens_system([{"R": 10, "t": None, "n": 1.5, "ap": 1}], stop=3),  # stop out of range
    lambda: RT.lens_system([{"R": float("nan"), "t": 1, "n": 1.5, "ap": 1}]),  # NaN
    lambda: RT.lens_system([{"R": 10, "t": 1, "n": 0.5, "ap": 1}]),            # index < 1
    lambda: RT.lens_system([]),
    lambda: RT.paraxial_trace([1, 2, 3]),
    lambda: RT.spot_stats({"a": 1}),
    lambda: RT.spot_stats(RT.lens_system(), field=float("nan")),
    lambda: RT.trace_rays(RT.lens_system(), np.zeros((3, 2)), np.zeros((3, 2))),
    lambda: RT.ray_fan(RT.lens_system(), axis="z"),
    lambda: RT.thick_lens(0.0, -50.0, 5.0, 1.5),
    lambda: RT.example_system("triplet"),
])
def test_bad_inputs_raise_value_error(bad):
    with pytest.raises(ValueError):
        bad()


def test_vignetting_and_tir_report_nan_instead_of_clipping_or_crashing():
    v = RT.lens_system([{"R": 51.68, "t": 5, "n": 1.5168, "ap": 12.5},
                        {"R": INF, "t": None, "n": 1.0, "ap": 5.0}], stop=0)
    b = RT.ray_bundle(v)
    assert 0 < b["valid"].sum() < len(b["valid"])
    assert np.isnan(b["image_xy"][~b["valid"]]).all()
    assert RT.spot_stats(v)["n_vignetted"] == int((~b["valid"]).sum())
    # glass -> air at grazing incidence on a steep exit surface: TIR, not a crash
    t = RT.lens_system([{"R": INF, "t": 5, "n": 1.5168, "ap": 20},
                        {"R": 5.0, "t": None, "n": 1.0}], stop=0)
    tr = RT.trace_rays(t, np.array([[0.0, 4.9, -5.0]]), np.array([[0.0, 0.0, 1.0]]))
    assert tr["valid"].tolist() == [False]
    assert np.isnan(tr["points"][0, -1]).all()


# --------------------------------------------------------------------------- #
# ledger / fuzzer / facade                                                    #
# --------------------------------------------------------------------------- #
def test_design_category_is_registered_with_the_declared_types():
    assert opsoptics.list_ops("design") == DESIGN_OPS
    for name in DESIGN_OPS:
        meta = opsoptics.info(name)
        assert meta["module"] == "raytrace" and meta["func"] is getattr(RT, name)
        assert meta["doc"], name
    assert opsoptics.info("opd_map")["out"] == "image2d"
    assert opsoptics.info("ray_fan")["out"] == opsoptics.info("spot_diagram")["out"] == "pairs"
    assert all(opsoptics.info(n)["in"] == [] for n in DESIGN_OPS[:4])
    assert all(opsoptics.info(n)["in"] == ["table"] for n in DESIGN_OPS[4:])


def test_design_ops_return_their_declared_type_and_reach_the_fuzzer():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import chain_fuzz
    sg = RT.lens_system()
    args = {"lens_system": (), "thick_lens": (), "glass": (1.5168, 64.17),
            "example_system": (), "paraxial_trace": (sg,), "seidel_coefficients": (sg,),
            "spot_stats": (sg,), "tolerance_analysis": (sg, None, 2),
            "wavefront_from_opd": (sg,), "spot_diagram": (sg,), "ray_fan": (sg,),
            "opd_map": (sg,)}
    for name in DESIGN_OPS:
        out_t = opsoptics.info(name)["out"]
        val = opsoptics.call(name, *args[name])
        assert chain_fuzz.TYPE_CHECKS[out_t](val), (name, out_t, type(val).__name__)
    names = {o[0] for o in chain_fuzz.catalog() if o[1] == "optics"}
    assert set(DESIGN_OPS) <= names
    # glass has two required arguments with no defaults: without op-level hints the
    # fuzzer would skip it forever ("zero findings" = never executed)
    rng = np.random.default_rng(0)
    for p in ("nd", "vd"):
        assert chain_fuzz.OP_PARAM_HINTS[("glass", p)](rng) > 1.0


@pytest.mark.parametrize("name", DESIGN_OPS[4:])
def test_table_consuming_ops_refuse_a_random_table_with_value_error(name):
    rng = np.random.default_rng(7)
    fn = opsoptics.get(name)
    for bad in ([1, 2, 3], {"x": 1.0, "y": [1, 2]}, {"stop": 0}, {"surfaces": []},
                rng.random(5).tolist(), {"efl": 100.0, "bfl": 96.7}):
        with pytest.raises(ValueError):
            fn(bad)


def test_facade_exports_every_raytrace_op():
    import api
    import fullseye
    for name in DESIGN_OPS + ["refractive_index", "trace_rays", "ray_bundle", "opd_samples"]:
        assert name in api.__all__, f"{name} missing from api.__all__"
        assert name in fullseye.__all__, f"{name} missing from fullseye.__all__"
        assert getattr(fullseye, name) is getattr(RT, name)
    assert fullseye.raytrace is RT and api.raytrace is RT


def test_design_guide_snippets_run():
    guide = os.path.join(ROOT, "docs", "ops", "optics", "guides", "optics_imaging.md")
    with open(guide, encoding="utf-8") as f:
        md = f.read()
    assert "## 設計(design)" in md
    blocks = re.findall(r"```python\n(.*?)```", md, re.S)
    runnable = [b for b in blocks if "import raytrace" in b]
    assert len(runnable) >= 3, "the optics guide lost its design snippets"
    for src in runnable:
        exec(compile(src, guide, "exec"), {"__name__": "__guide__"})
