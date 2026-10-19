"""Sequential optical design, 5th slice: glass substitution and multi-start (global) search (lensglobal).

Ground truth, none of it taken from the code under test:

* **Thin achromatic doublet** (Smith, *Modern Optical Engineering*, the thin-lens chromatic condition;
  Kingslake & Johnson, *Lens Design Fundamentals*, thin-lens achromat): two thin lenses in contact are
  achromatic for the F and C lines when ``phi1/V1 + phi2/V2 = 0``, with ``phi1 + phi2 = phi``, i.e.
  ``phi1 = phi V1/(V1 - V2)`` and ``phi2 = -phi V2/(V1 - V2)``. For any other glass pair the
  *residual* ``phi1/V1' + phi2/V2'`` is ``phi (V1/V1' - V2/V2') / (V1 - V2)`` -- a number computed here by
  hand from the catalogue V_d and compared with the F-C power difference the ray tracer measures.
* **Minimum spherical aberration bending of a thin singlet, object at infinity** (third order). With the
  shape factor ``q = (R2 + R1)/(R2 - R1)`` the third-order spherical aberration of a thin lens is a
  quadratic in q whose coefficients are ``(n+2)/(n(n-1)^2)`` for q^2 and ``4(n+1)/(n(n-1))`` for q p, p the
  position factor (Welford, *Aberrations of Optical Systems*, thin-lens Seidel coefficients; Kingslake &
  Johnson, Coddington factors). With the object at infinity p = -1, the minimum is
  ``q* = 2(n^2 - 1)/(n + 2)`` (0.7397 for n = 1.5168). The sign is a convention: with q defined as above
  q* is positive (the more strongly curved face towards the distant object). The textbooks are not
  at hand here; the derivation above was redone from the two coefficients and the sign was checked
  numerically: the traced optimum approaches +0.7397 as the aperture shrinks (see the test).
"""
import math

import numpy as np
import pytest

import lensglobal as G
import lensopt as LO
import materials as MAT
import opsoptics
import raytrace as RT

N1, V1 = 1.5168, 64.17          # a crown
N2, V2 = 1.6200, 36.37          # a flint
NAMED = ["N-BK7", "N-SF11", "N-FK51A", "N-F2", "N-SK16", "N-SF6", "N-LAK9", "N-BAK4"]
FCD = [RT.WL_F, RT.WL_D, RT.WL_C]


def _row(name):
    return next(r for r in MAT.glass_map("glass") if r["name"] == name)


def _doublet(c0, c1, c2, t=3.0, ap=8.0, glasses=((N1, V1), (N2, V2))):
    return RT.lens_system([{"R": 1.0 / c0, "t": t, "n": glasses[0], "ap": ap},
                           {"R": 1.0 / c1, "t": 1.5 if t > 1 else t, "n": glasses[1]},
                           {"R": 1.0 / c2, "t": None, "n": 1.0}], stop=0, object_mm=RT.INF)


# --------------------------------------------------------------------------- #
# glass substitution                                                           #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", NAMED)
def test_a_catalogue_glass_is_its_own_nearest_neighbour_at_distance_zero(name):
    row = _row(name)
    assert row["PgF"] is not None
    for metric, pgf in (("nd_vd", None), ("partial_dispersion", row["PgF"])):
        r = G.glass_nearest(row["nd"], row["vd"], k=3, metric=metric, p_gf=pgf)
        nb = r["neighbours"]
        assert nb[0]["name"] == name and nb[0]["distance"] == 0.0
        assert nb[1]["distance"] > 0.0 and nb[1]["distance"] <= nb[2]["distance"]
        assert [n["rank"] for n in nb] == [1, 2, 3]


@pytest.mark.parametrize("name", NAMED)
def test_a_model_glass_made_from_a_catalogue_glass_is_replaced_by_that_glass(name):
    row = _row(name)
    s = RT.lens_system([{"R": 60.0, "t": 4.0, "n": (row["nd"], row["vd"]), "ap": 8.0},
                        {"R": -60.0, "t": None, "n": 1.0}], stop=0)
    out = G.lens_substitute_glasses(s)
    assert out["n_substituted"] == 1 and out["n_kept"] == 1          # the air after the lens is kept
    t = out["table"][0]
    assert t["glass"] == name and t["distance"] == 0.0 and t["d_nd"] == 0.0 and t["d_vd"] == 0.0
    assert out["system"]["surfaces"][0]["n"] == name
    # the input is not modified
    assert s["surfaces"][0]["n"] == (row["nd"], row["vd"])


def test_the_metrics_give_different_answers():
    """The partial-dispersion term moves the nearest glass for a query whose P_g,F is far from the
    catalogue glass that nd_vd picks (so the knob is not decorative)."""
    q = (1.62, 36.4)
    a = G.glass_nearest(*q, metric="nd_vd")["neighbours"][0]
    # ask for the P_g,F of a glass with an anomalous partial dispersion (a fluor crown)
    b = G.glass_nearest(*q, metric="partial_dispersion", p_gf=0.535)["neighbours"][0]
    c = G.glass_nearest(*q, metric="partial_dispersion", p_gf=0.62)["neighbours"][0]
    assert len({a["name"], b["name"], c["name"]}) >= 2
    assert b["name"] != c["name"]
    with pytest.raises(ValueError, match="p_gf"):
        G.glass_nearest(*q, metric="partial_dispersion")
    with pytest.raises(ValueError, match="metric"):
        G.glass_nearest(*q, metric="euclid")


def test_k_selects_the_kth_nearest_and_the_system_changes():
    s = _doublet(0.012, -0.02, -0.004)
    one = G.lens_substitute_glasses(s, k=1)
    two = G.lens_substitute_glasses(s, k=2, tolerance=0.2)
    assert [r["glass"] for r in one["table"]] != [r["glass"] for r in two["table"]]
    assert len(one["table"]) == len(two["table"]) == 2
    assert all(b["distance"] >= a["distance"] for a, b in zip(one["table"], two["table"]))
    assert one["system"]["surfaces"][0]["n"] == one["table"][0]["glass"]


@pytest.mark.parametrize("k", [1, 2, 3])
def test_the_achromatic_residual_changes_by_the_closed_form(k):
    """Doublet with the model glasses' own closed-form powers is achromatic (residual 0); after the swap
    the F-C power difference the tracer measures equals phi (V1/V1' - V2/V2')/(V1 - V2), computed by hand."""
    f = 100.0
    phi = 1.0 / f
    p1 = phi * V1 / (V1 - V2)
    p2 = -phi * V2 / (V1 - V2)
    c0 = 0.012
    c1 = c0 - p1 / (N1 - 1.0)
    c2 = c1 - p2 / (N2 - 1.0)
    s = RT.lens_system([{"R": 1 / c0, "t": 0.0, "n": (N1, V1), "ap": 0.004},
                        {"R": 1 / c1, "t": 0.0, "n": (N2, V2)},
                        {"R": 1 / c2, "t": None, "n": 1.0}], stop=0, object_mm=RT.INF)

    def d_power(sys_):          # Phi_F - Phi_C of the traced system (1/EFL at each line)
        pf = 1.0 / RT.paraxial_trace(RT.with_wavelength(sys_, RT.WL_F))["efl"]
        pc = 1.0 / RT.paraxial_trace(RT.with_wavelength(sys_, RT.WL_C))["efl"]
        return pf - pc

    assert abs(d_power(s)) < 1e-12                                  # achromatic by construction
    out = G.lens_substitute_glasses(s, k=k, tolerance=0.3)
    g1, g2 = (_row(r["glass"]) for r in out["table"])
    v1, v2 = g1["vd"], g2["vd"]
    n1, n2 = g1["nd"], g2["nd"]
    # independent closed form: the curvatures stay, the powers are phi_i' = (n_i' - 1) dc_i, V_i' catalogue
    P1 = (n1 - 1.0) * (c0 - c1)
    P2 = (n2 - 1.0) * (c1 - c2)
    expect = P1 / v1 + P2 / v2
    got = d_power(out["system"])
    assert abs(expect) > 1e-3 * phi / V1                              # the swap really de-achromatises it
    assert got == pytest.approx(expect, rel=1e-6)
    # and the same number for a swap that keeps the model powers exactly (V changed only): phi (V1/V1' - V2/V2')/(V1 - V2)
    only_v = phi * (V1 / v1 - V2 / v2) / (V1 - V2)
    s_v = RT.lens_system([{"R": 1 / c0, "t": 0.0, "n": (N1, v1), "ap": 0.004},
                          {"R": 1 / c1, "t": 0.0, "n": (N2, v2)},
                          {"R": 1 / c2, "t": None, "n": 1.0}], stop=0, object_mm=RT.INF)
    p1m = (N1 - 1.0) * (c0 - c1)
    p2m = (N2 - 1.0) * (c1 - c2)
    assert d_power(s_v) == pytest.approx(p1m / v1 + p2m / v2, rel=1e-6)
    assert abs(p1m / v1 + p2m / v2 - only_v) < 5e-6 * phi               # (n - 1) changed by 1e-4 relative at most


def test_substitution_is_fail_closed():
    s = _doublet(0.012, -0.02, -0.004)
    with pytest.raises(ValueError, match="tolerance"):
        G.lens_substitute_glasses(s, tolerance=1e-6)
    far = RT.lens_system([{"R": 50.0, "t": 3.0, "n": (2.6, 12.0), "ap": 5.0}, {"R": -50.0, "t": None, "n": 1.0}], stop=0)
    with pytest.raises(ValueError, match="surface 0"):
        G.lens_substitute_glasses(far)
    with pytest.raises(ValueError, match="k must"):
        G.lens_substitute_glasses(s, k=0)
    with pytest.raises(ValueError, match="duplicate|twice"):
        G.glass_nearest(1.5, 60.0, catalog=[{"name": "A", "nd": 1.5, "vd": 60.0}, {"name": "A", "nd": 1.6, "vd": 40.0}])
    with pytest.raises(ValueError):
        G.glass_nearest(1.5, 60.0, k=999)
    # a system with no model glass has nothing to swap
    named = RT.lens_system([{"R": 50.0, "t": 3.0, "n": "N-BK7", "ap": 5.0}, {"R": -50.0, "t": None, "n": 1.0}], stop=0)
    assert G.lens_substitute_glasses(named)["n_substituted"] == 0


def test_a_custom_catalogue_is_used():
    cat = [{"name": "N-BK7", "nd": 1.5168, "vd": 64.17}, {"name": "N-SF11", "nd": 1.7847, "vd": 25.68}]
    out = G.lens_substitute_glasses(_doublet(0.012, -0.02, -0.004), catalog=cat, tolerance=0.2)
    assert [r["glass"] for r in out["table"]] == ["N-BK7", "N-SF11"]          # the crown stays a crown, the flint goes dense
    assert len(out["table"]) == 2
    assert all(r["glass"] in ("N-BK7", "N-SF11") for r in out["table"])


# --------------------------------------------------------------------------- #
# global search                                                                #
# --------------------------------------------------------------------------- #
def _singlet(q, ap, n=1.5168, f=100.0, t=None):
    t = 0.012 * ap * ap if t is None else t          # the lens thickness scales with the sag, so its effect scales as ap^2 too
    R1 = 2 * f * (n - 1) / (q + 1)
    R2 = -2 * f * (n - 1) / (1 - q)
    return RT.lens_system([{"R": R1, "t": t, "n": n, "ap": ap}, {"R": R2, "t": None, "n": 1.0}],
                          stop=0, object_mm=RT.INF)


def _q_of(values):
    R1, R2 = 1.0 / values[0], 1.0 / values[1]
    return (R2 + R1) / (R2 - R1)


def test_bending_of_a_singlet_approaches_the_third_order_optimum_as_the_aperture_shrinks():
    n = 1.5168
    q_star = 2 * (n * n - 1) / (n + 2)
    best = {}
    for ap in (5.0, 3.0):
        r = G.lens_global_search(_singlet(0.0, ap), ["c0", "c1"], {"tolerance": 1e-12}, n_starts=6, seed=2,
                                 spread=0.3, iterations=200)
        best[ap] = _q_of(r["best"]["values"])
        # every start lands within 0.01 of the best (one basin), the EFL is held
        assert len(r["optima"]) == 6
        assert all(abs(_q_of(o["values"]) - best[ap]) < 0.01 for o in r["optima"])
        assert all(abs(o["efl"] - r["optima"][0]["efl"]) < 1e-3 for o in r["optima"])
    assert best[5.0] < best[3.0] < q_star                       # from below, towards +0.7397
    # fifth-order aberration shifts q by c ap^2: extrapolate to ap -> 0
    q0 = best[3.0] - (best[5.0] - best[3.0]) * 9.0 / (25.0 - 9.0)
    assert abs(q0 - q_star) < 2e-3, (q0, q_star)
    assert q_star == pytest.approx(0.73969645, abs=1e-7)


def test_the_achromatic_doublet_powers_are_found_to_1e_minus_6():
    f = 100.0
    phi = 1.0 / f
    p1 = phi * V1 / (V1 - V2)
    p2 = -phi * V2 / (V1 - V2)
    c0 = 0.012
    c1t = c0 - p1 / (N1 - 1.0)
    c2t = c1t - p2 / (N2 - 1.0)
    thin = RT.lens_system([{"R": 1 / c0, "t": 1e-5, "n": (N1, V1), "ap": 0.004},
                           {"R": 1 / (1.3 * c1t), "t": 1e-5, "n": (N2, V2)},
                           {"R": 1 / (0.8 * c2t), "t": None, "n": 1.0}], stop=0, object_mm=RT.INF)
    merit = {"wavelengths": FCD, "efl_target": f, "efl_weight": 1.0, "tolerance": 1e-14}
    r = G.lens_global_search(thin, ["c1", "c2"], merit, n_starts=8, seed=5, spread=0.4, iterations=300)
    assert r["n_distinct"] == 1                                  # one optimum; the other seven are duplicates
    assert sum(o["duplicate_of"] is not None for o in r["optima"]) == 7
    assert len(r["optima"]) == 8
    for o in r["optima"]:
        c1, c2 = o["values"]
        P1 = (N1 - 1.0) * (c0 - c1)
        P2 = (N2 - 1.0) * (c1 - c2)
        assert P1 / p1 - 1.0 == pytest.approx(0.0, abs=1e-6)
        assert P2 / p2 - 1.0 == pytest.approx(0.0, abs=1e-6)
        assert o["efl"] == pytest.approx(f, abs=1e-6)


def test_multi_start_finds_the_better_basin_a_single_start_misses():
    merit = {"wavelengths": FCD, "tolerance": 1e-12}
    bad = _doublet(1 / 187.04, 1 / -54.72, 1 / -139.15)
    single = G.lens_global_search(bad, ["c0", "c1", "c2"], merit, n_starts=1, iterations=150)
    multi = G.lens_global_search(bad, ["c0", "c1", "c2"], merit, n_starts=20, seed=1, spread=0.7, iterations=150)
    assert single["n_distinct"] == 1
    assert multi["best"]["merit"] < 0.5 * single["best"]["merit"]            # 5.0e-6 against 1.18e-5
    assert multi["n_distinct"] == 2                                          # both basins were visited
    good, worse = multi["basins"][0], multi["basins"][1]
    assert good["merit"] < worse["merit"]
    # the better basin is the rarer one from this start: 1 of 20 starts reach it, 19 land in the worse basin
    assert (good["n_starts"], worse["n_starts"]) == (1, 19)
    # the single start sits in the worse basin
    assert single["best"]["merit"] == pytest.approx(worse["merit"], rel=1e-3)
    assert multi["optima"][0]["duplicate_of"] is None
    ds = [o for o in multi["optima"] if o["duplicate_of"] is not None]
    assert len(ds) == 20 - 2


def test_same_seed_same_answer_other_seed_other_starts():
    s = _doublet(0.012, -0.02, -0.004)
    kw = dict(variables=["c0", "c1"], merit={"wavelengths": FCD}, n_starts=4, iterations=5, spread=0.3)
    a = G.lens_global_search(s, seed=7, **kw)
    b = G.lens_global_search(s, seed=7, **kw)
    c = G.lens_global_search(s, seed=8, **kw)
    assert [o["values"] for o in a["optima"]] == [o["values"] for o in b["optima"]]
    assert [o["start_merit"] for o in a["optima"]] != [o["start_merit"] for o in c["optima"]]
    assert a["optima"][0]["merit"] <= a["optima"][-1]["merit"]
    assert [o["merit"] for o in a["optima"]] == sorted(o["merit"] for o in a["optima"])
    # the input prescription is untouched
    assert s["surfaces"][0]["R"] == pytest.approx(1 / 0.012)


def test_the_merit_is_the_lensopt_merit_not_a_copy():
    s = _singlet(0.2, 3.0)
    r = G.lens_global_search(s, ["c0", "c1"], {"rings": 2}, n_starts=1, iterations=3)
    ref = LO.optimize_lens(s, ["c0", "c1"], rings=2, iterations=3, efl_target=RT.paraxial_trace(s)["efl"])
    assert r["best"]["merit"] == ref["merit_final"]
    assert r["best"]["values"] == [LO._get(ref["system"], LO._parse_variable(v, 2)) for v in ("c0", "c1")]


def test_global_search_refuses_bad_input():
    s = _singlet(0.2, 3.0)
    for kw in ({"n_starts": 0}, {"n_starts": 1.5}, {"seed": -1}, {"spread": 0.0}, {"duplicate_tolerance": -1.0},
               {"merit": {"nonsense": 1}}, {"merit": [1]}, {"variables": ["c0", "c0"]}, {"variables": ["c9"]}):
        with pytest.raises(ValueError):
            G.lens_global_search(s, **kw)
    with pytest.raises(ValueError):
        G.lens_global_search({"surfaces": []})


def test_the_three_ops_are_registered_with_their_category():
    names = set(opsoptics.list_ops("lensglobal"))
    assert names == {"glass_nearest", "lens_substitute_glasses", "lens_global_search"}
    assert len(names) == 3
    assert all(opsoptics.OPSOPTICS[n]["module"] == "lensglobal" for n in names)
