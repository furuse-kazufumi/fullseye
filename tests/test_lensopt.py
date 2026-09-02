# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""lensopt — the optimiser is checked against closed forms, not against itself.

* Bending a thin singlet for minimum spherical aberration: the optimiser,
  started from an equiconvex lens with the EFL held at 100 mm, must land on the
  Coddington shape factor ``q = 2(n²−1)/(n+2)`` (0.74 for n = 1.5168) within
  the thick-lens correction (a brute-force scan of q gives 0.730 for t = 2 mm),
  and the EFL must not move.
* A plano-convex singlet with the flat toward a distant object becomes
  stigmatic when the exit surface is a hyperboloid with ``k = −n²`` (Descartes).
  Varying only ``k1`` the optimiser must find that value to 1e-3 and the RMS
  spot must fall from 0.57 mm to below 1e-9 mm — which also proves the
  aspheric intersection / normal code, since a wrong normal cannot give a
  15-digit stigmatic point.
* The same lens with a spherical base and even polynomial coefficients: A4
  must converge to the conic's fourth-order term ``k c³/8`` (2.08e-6 mm⁻³) to
  1 %, and adding A6 / A8 must reduce the spot monotonically.
* Merit history is monotone non-increasing; the EFL constraint holds to 1e-4;
  an impossible variable (image distance, conic of a flat, unknown kind, index
  out of range) is a ``ValueError``; ``merit_function`` on the optimised system
  reproduces ``merit_final``.
"""
import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import lensopt as LO  # noqa: E402
import raytrace as RT  # noqa: E402

INF = float("inf")
N_BK7 = 1.5168


def _plano_convex_flat_first():
    n = RT.refractive_index("N-BK7")
    return RT.lens_system([{"R": INF, "t": 5.0, "n": "N-BK7", "ap": 12.5},
                           {"R": -(n - 1.0) * 100.0, "t": None, "n": 1.0}], stop=0)


# --------------------------------------------------------------------------- #
# closed forms                                                                 #
# --------------------------------------------------------------------------- #
def test_bend_singlet_default_is_the_coddington_shape_factor():
    b = LO.bend_singlet(100.0, N_BK7, 2.0, 5.0)
    q_cod = 2.0 * (N_BK7 ** 2 - 1.0) / (N_BK7 + 2.0)
    assert b["shape_factor"] == pytest.approx(q_cod)
    assert b["R1"] == pytest.approx(2.0 * 100.0 * (N_BK7 - 1.0) / (q_cod + 1.0))
    assert b["R2"] == pytest.approx(-2.0 * 100.0 * (N_BK7 - 1.0) / (1.0 - q_cod))
    # thin-lens formula: EFL within the thickness correction
    assert abs(b["efl"] - 100.0) < 1.0


def test_optimiser_finds_the_minimum_spherical_bending_from_equiconvex():
    eq = LO.bend_singlet(100.0, N_BK7, 2.0, 5.0, shape_factor=0.0)
    r = LO.optimize_lens(eq["system"], variables=["R0", "R1"], efl_target=100.0, iterations=40)
    R1, R2 = r["variables"][0]["final"], r["variables"][1]["final"]
    q = (R2 + R1) / (R2 - R1)
    # thick-lens optimum (brute-force scan of q) is 0.730; thin-lens Coddington 0.740
    assert abs(q - 0.730) < 0.02, q
    assert r["rms_final"] < r["rms_initial"] * 0.7
    assert abs(r["efl_final"] - 100.0) < 1e-3
    assert r["converged"]
    # the scan optimum is the true minimum: the optimiser cannot beat it by more than sampling noise
    best = min(LO.bend_singlet(100.0, N_BK7, 2.0, 5.0, shape_factor=qq)["rms_spot"]
               for qq in np.linspace(0.6, 0.85, 26))
    assert r["rms_final"] >= best * 0.98


def test_optimiser_recovers_the_descartes_hyperboloid():
    n = RT.refractive_index("N-BK7")
    s = _plano_convex_flat_first()
    r = LO.optimize_lens(s, variables=["k1"], efl_target=100.0, iterations=40)
    assert r["variables"][0]["name"] == "k1"
    assert abs(r["variables"][0]["final"] - (-n * n)) < 1e-3
    assert r["rms_initial"] > 0.5
    assert r["rms_final"] < 1e-9
    assert abs(r["efl_final"] - 100.0) < 1e-6


def test_polynomial_asphere_converges_to_the_conic_fourth_order_term():
    n = RT.refractive_index("N-BK7")
    s = _plano_convex_flat_first()
    c = 1.0 / (-(n - 1.0) * 100.0)
    a4_conic = (-n * n) * c ** 3 / 8.0
    prev = None
    for vs in (["A4_1"], ["A4_1", "A6_1"], ["A4_1", "A6_1", "A8_1"]):
        r = LO.optimize_lens(s, variables=vs, efl_target=100.0, iterations=60)
        a4 = [v for v in r["variables"] if v["name"] == "A4_1"][0]["final"]
        assert abs(a4 - a4_conic) / abs(a4_conic) < 0.01
        if prev is not None:
            assert r["rms_final"] < prev
        prev = r["rms_final"]
    assert prev < 1e-6


# --------------------------------------------------------------------------- #
# behaviour                                                                    #
# --------------------------------------------------------------------------- #
def test_history_is_monotone_and_merit_function_agrees():
    d = RT.example_system("catalog_doublet")
    d["field"] = 3.0
    r = LO.optimize_lens(d, variables=["R0", "R1", "R2"], wavelengths=[RT.WL_F, RT.WL_D, RT.WL_C], iterations=20)
    h = r["history"]
    assert all(b <= a for a, b in zip(h, h[1:]))
    assert r["merit_final"] == pytest.approx(h[-1])
    assert r["rms_final"] < r["rms_initial"]
    # EFL held at the starting value by default
    assert abs(r["efl_final"] - r["efl_initial"]) / r["efl_initial"] < 1e-4
    m = LO.merit_function(r["system"], fields=[0.0, 2.1, 3.0], wavelengths=[RT.WL_F, RT.WL_D, RT.WL_C],
                          efl_target=r["efl_target"], efl_weight=None)
    assert m["merit"] == pytest.approx(r["merit_final"], rel=1e-9)
    assert set(m["rms_by_field"]) == {0.0, 2.1, 3.0}


def test_optimised_system_is_a_valid_prescription():
    d = RT.example_system("doublet")
    r = LO.optimize_lens(d, iterations=5)
    RT._check_system(r["system"])
    RT.paraxial_trace(r["system"])
    RT.spot_stats(r["system"])
    assert len(r["variables"]) == 3 and all(v["name"].startswith("R") for v in r["variables"])


def test_thickness_bounds_are_respected():
    d = RT.example_system("doublet")
    r = LO.optimize_lens(d, variables=["t0", "t1", "R0"], min_thickness=1.0, max_thickness=8.0, iterations=15)
    for s in r["system"]["surfaces"][:2]:
        assert 1.0 - 1e-12 <= s["t"] <= 8.0 + 1e-12


@pytest.mark.parametrize("bad", [
    lambda d: LO.optimize_lens({"x": 1}),
    lambda d: LO.optimize_lens(d, variables=["t2"]),        # image distance
    lambda d: LO.optimize_lens(d, variables=["q1"]),        # unknown kind
    lambda d: LO.optimize_lens(d, variables=["R9"]),        # out of range
    lambda d: LO.optimize_lens(d, variables=["A3_0"]),      # odd order
    lambda d: LO.optimize_lens(d, variables=["R0", "R0"]),  # duplicate
    lambda d: LO.optimize_lens(d, variables=[]),
    lambda d: LO.optimize_lens(d, iterations=0),
    lambda d: LO.optimize_lens(d, damping=float("nan")),
    lambda d: LO.optimize_lens(d, fields=[]),
    lambda d: LO.optimize_lens(d, field_weights=[1.0, 2.0]),
    lambda d: LO.merit_function(d, rings=0),
    lambda d: LO.merit_function(d, pupil_fill=1.5),
    lambda d: LO.bend_singlet(0.0),
    lambda d: LO.bend_singlet(100.0, index=0.5),
])
def test_invalid_inputs_are_value_errors(bad):
    d = RT.example_system("doublet")
    with pytest.raises(ValueError):
        bad(d)


OPT_OPS = ["optimize_lens", "merit_function", "bend_singlet"]


def test_optimization_category_is_registered_and_returns_declared_types():
    import opsoptics
    import api
    import fullseye
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import chain_fuzz
    assert opsoptics.list_ops("optimization") == OPT_OPS
    sg = RT.lens_system()
    args = {"optimize_lens": (sg, None, None, None, 2, None, None, None, 2), "merit_function": (sg,), "bend_singlet": ()}
    for name in OPT_OPS:
        meta = opsoptics.info(name)
        assert meta["module"] == "lensopt" and meta["func"] is getattr(LO, name) and meta["doc"]
        val = opsoptics.call(name, *args[name])
        assert chain_fuzz.TYPE_CHECKS[meta["out"]](val), (name, meta["out"], type(val).__name__)
        assert name in api.__all__ and name in fullseye.__all__
    names = {o[0] for o in chain_fuzz.catalog() if o[1] == "optics"}
    assert set(OPT_OPS) <= names
    rng = np.random.default_rng(0)
    assert chain_fuzz.OP_PARAM_HINTS[("optimize_lens", "iterations")](rng) <= 3


@pytest.mark.parametrize("name", ["optimize_lens", "merit_function"])
def test_table_consuming_optimisation_ops_refuse_a_random_table(name):
    rng = np.random.default_rng(1)
    for bad in ([1, 2, 3], {"x": 1.0}, {"surfaces": []}, rng.random(4).tolist()):
        with pytest.raises(ValueError):
            getattr(LO, name)(bad)


def test_conic_of_a_flat_is_rejected():
    s = _plano_convex_flat_first()
    with pytest.raises(ValueError):
        LO.optimize_lens(s, variables=["k0"])


def test_dict_variable_form_and_efl_free():
    s = LO.bend_singlet(100.0, N_BK7, 2.0, 5.0, shape_factor=0.0)["system"]
    r = LO.optimize_lens(s, variables=[{"surface": 0, "param": "R"}, {"surface": 1, "param": "R"}],
                         efl_target=False, iterations=10)
    assert r["efl_target"] is None
    assert r["rms_final"] <= r["rms_initial"]
