"""Sequential optical design, 6th slice: an operand-table merit function and its optimiser (lensmerit).

Ground truth, none of it taken from the code under test:

* **Thin achromatic doublet** (Smith, *Modern Optical Engineering*; Kingslake & Johnson, *Lens Design Fundamentals*):
  two thin lenses in contact are achromatic for F and C when ``phi1/V1 + phi2/V2 = 0``, with ``phi1 + phi2 = phi``, so
  ``phi1 = phi V1/(V1 - V2)`` and ``phi2 = -phi V2/(V1 - V2)``. Optimising ``EFFL`` and ``AXCL = 0`` from a detuned start
  must land on that split.
* **Plano-convex edge thickness**: ``t - (R - sqrt(R^2 - h^2))``; with a conic and even aspheric terms the sag is
  written out by hand below.
* **A refracting sphere** (Snell's law in the meridional plane): the real ray height after a spherical surface, the
  angle of incidence ``asin(h/R)`` and the third-order spherical aberration of one surface
  ``S_I = y^4 c^3 (n' - 1)/n'^2`` (Welford).
* **An ideal thin lens**: working F-number ``f/(2 h)``, magnification ``-f/(s - f)``, zero distortion.
* **A second implementation** (optiland 0.6.3, MIT): EFL, real ray positions at the image, the RMS spot about the
  centroid and the OPD of a hexapolar pupil, on a three-element prescription. The numbers it gave are recorded in
  ``tests/data/lensmerit_optiland_ref.json`` and checked in every run; when optiland is importable the same numbers are
  also regenerated live and compared (skipped, with the reason, when it is not installed).
"""
import json
import math
import os
import warnings

import numpy as np
import pytest

import lensmerit as LM
import lensopt as LO
import opsoptics
import raytrace as RT

INF = float("inf")
N1, V1 = 1.5168, 64.17
N2, V2 = 1.6200, 36.37
REF = json.load(open(os.path.join(os.path.dirname(__file__), "data", "lensmerit_optiland_ref.json"), encoding="utf-8"))

# the three-element prescription of the second-implementation check (radii and spacings of the classic 40-degree
# triplet, published in the MIT-licensed optiland sample set), stop on the front surface, constant indices at the d line
RS = [22.01359, -435.76044, -22.21328, 20.29192, 79.6836, -18.39533]
TS = [3.25896, 6.00755, 0.99997, 4.75041, 2.95208, 42.20778]
NS = [1.62041, 1.0, 1.62004, 1.0, 1.62041, 1.0]
FIELDS3 = [0.0, 14.0, 20.0]
PTS = [(0.0, 0.5), (0.3, -0.4), (-0.6, 0.2)]


def triplet(aim="paraxial"):
    return RT.lens_system([{"R": RS[i], "t": TS[i], "n": NS[i], "ap": 4.0 if i == 0 else None} for i in range(6)],
                          stop=0, wavelength_um=0.58756, aim=aim)


def thin_pair(c0, c1, c2, ap=5.0):
    return RT.lens_system([{"R": 1.0 / c0, "t": 0.0, "n": (N1, V1), "ap": ap}, {"R": 1.0 / c1, "t": 0.0, "n": (N2, V2)},
                           {"R": 1.0 / c2, "t": None, "n": 1.0}], stop=0, object_mm=INF)


def value(system, row, **kw):
    """The value of a single operand row on *system*."""
    return LM.merit_evaluate(system, [dict(row, target=row.get("target", 0.0))], **kw)["table"][0]["value"]


# --------------------------------------------------------------------------- #
# the catalogue
# --------------------------------------------------------------------------- #
REQUIRED = ["EFFL", "TOTR", "TTHI", "CTGT", "CTLT", "ETGT", "ETLT", "MNCG", "MXCG", "MNCA", "MXCA", "REAY", "REAX", "RAID",
            "OPDX", "SPHA", "COMA", "ASTI", "FCUR", "DIST", "AXCL", "LACL", "RSCE", "RSCH", "WFNO", "PMAG", "DIMX", "WFRMS"]


def test_the_catalogue_lists_every_required_operand_with_meaning_unit_and_arguments():
    cat = LM.merit_operands_list()
    names = [o["name"] for o in cat["operands"]]
    assert cat["n_operands"] == len(names) == len(set(names)) and cat["names"] == names
    assert set(REQUIRED) <= set(names) and {"TRAN", "OPDW"} <= set(names)
    for o in cat["operands"]:
        assert o["description"].strip() and isinstance(o["unit"], str) and isinstance(o["required"], list)
        assert o["kind"] in ("scalar", "group") and o["sense"] in ("eq", "ge", "le")
    sense = {o["name"]: o["sense"] for o in cat["operands"]}
    assert [n for n in names if sense[n] == "ge"] == ["CTGT", "ETGT", "MNCG", "MNCA"]
    assert [n for n in names if sense[n] == "le"] == ["CTLT", "ETLT", "MXCG", "MXCA"]
    byname = {o["name"]: o for o in cat["operands"]}
    assert byname["REAY"]["required"] == ["surf"] and byname["TTHI"]["required"] == ["surf1", "surf2"]
    assert byname["EFFL"]["unit"] == "mm" and byname["OPDX"]["unit"] == "waves" and byname["DIMX"]["unit"] == "percent"


def test_the_ops_are_registered_in_their_own_category():
    assert sorted(opsoptics.list_ops("lensmerit")) == sorted(
        ["merit_operands_list", "merit_evaluate", "merit_default", "merit_boundary_operands",
         "optimize_lens_operands", "merit_contributions"])
    assert all(m["module"] == "lensmerit" for m in opsoptics.OPSOPTICS.values() if m["category"] == "lensmerit")


# --------------------------------------------------------------------------- #
# closed forms
# --------------------------------------------------------------------------- #
def test_a_detuned_thin_doublet_lands_on_the_closed_form_achromat_power_split():
    """EFFL = 100 and AXCL = 0 from a detuned start give phi1 = phi V1/(V1 - V2), phi2 = -phi V2/(V1 - V2) (1e-4)."""
    phi = 0.01
    p1, p2 = phi * V1 / (V1 - V2), -phi * V2 / (V1 - V2)
    c0 = 0.012
    c1 = c0 - p1 / (N1 - 1.0)
    c2 = c1 - p2 / (N2 - 1.0)
    start = thin_pair(1.3 * c0, 0.7 * c1, 1.4 * c2)
    assert abs(RT.paraxial_trace(start)["efl"] - 100.0) > 10.0                    # genuinely detuned
    ops = [{"op": "EFFL", "target": 100.0, "weight": 1.0}, {"op": "AXCL", "target": 0.0, "weight": 10.0}]
    r = LM.optimize_lens_operands(start, ops, ["c0", "c1", "c2"], iterations=80, tolerance=1e-14, min_thickness=0.0)
    s = r["system"]
    g1 = (N1 - 1.0) * (1.0 / s["surfaces"][0]["R"] - 1.0 / s["surfaces"][1]["R"])
    g2 = (N2 - 1.0) * (1.0 / s["surfaces"][1]["R"] - 1.0 / s["surfaces"][2]["R"])
    assert abs(g1 / p1 - 1.0) < 1e-4 and abs(g2 / p2 - 1.0) < 1e-4
    assert abs(g1 / V1 + g2 / V2) < 1e-4 * phi / V1                                  # the achromatic condition itself
    assert r["merit_final"] < 1e-8 * r["merit_initial"]
    assert abs(RT.paraxial_trace(s)["efl"] - 100.0) < 1e-3


def test_edge_thickness_of_a_plano_convex_singlet_is_t_minus_the_sag():
    for R, t, h in ((50.0, 4.0, 10.0), (30.0, 6.5, 12.0), (-80.0, 3.0, 20.0), (120.0, 2.0, 5.0)):
        s = RT.lens_system([{"R": R, "t": t, "n": 1.5, "ap": h}, {"R": INF, "t": 30.0, "n": 1.0, "ap": h}], stop=0)
        expect = t - (R - math.copysign(math.sqrt(R * R - h * h), R))
        got = value(s, {"op": "ETGT", "surf": 0})
        assert abs(got - expect) < 1e-12, (R, t, h, got, expect)


def test_edge_thickness_includes_the_conic_and_the_even_aspheric_sag():
    def sag(R, k, a4, a6, h):
        c = 1.0 / R
        return c * h * h / (1.0 + math.sqrt(1.0 - (1.0 + k) * c * c * h * h)) + a4 * h ** 4 + a6 * h ** 6
    R0, k0, R1, k1, a4, a6, t, h0, h1 = 40.0, -0.5, -35.0, 0.3, 1.0e-6, -2.0e-9, 5.0, 9.0, 8.0
    s = RT.lens_system([{"R": R0, "t": t, "n": 1.6, "k": k0, "ap": h0},
                        {"R": R1, "t": 40.0, "n": 1.0, "k": k1, "asph": (a4, a6), "ap": h1}], stop=0)
    expect = t - sag(R0, k0, 0.0, 0.0, h0) + sag(R1, k1, a4, a6, h1)
    assert abs(value(s, {"op": "ETGT", "surf": 0}) - expect) < 1e-12
    assert expect > t - 1.1 * h0 * h0 / R0 and abs(expect - t) > 0.1                 # the sag terms matter


def test_total_track_is_the_sum_of_thicknesses_and_tthi_is_a_partial_sum():
    s = triplet()
    assert abs(value(s, {"op": "TOTR"}) - sum(TS)) < 1e-12
    assert abs(value(s, {"op": "TTHI", "surf1": 1, "surf2": 4}) - sum(TS[1:4])) < 1e-12
    assert abs(value(s, {"op": "TTHI", "surf1": 0, "surf2": 6}) - sum(TS)) < 1e-12                  # surf2 = N: through the image plane
    # last thickness left to the paraxial focus: the track ends at the focus
    f = RT.lens_system([{"R": 50.0, "t": 5.0, "n": 1.5, "ap": 5.0}, {"R": INF, "t": None, "n": 1.0}], stop=0)
    assert abs(value(f, {"op": "TOTR"}) - (5.0 + RT.paraxial_trace(f)["bfl"])) < 1e-12


def test_glass_and_air_thickness_ranges():
    s = triplet()
    glass = [TS[0], TS[2], TS[4]]
    air = [TS[1], TS[3], TS[5]]
    assert value(s, {"op": "MNCG", "surf1": 0, "surf2": 5}) == min(glass) and value(s, {"op": "MXCG", "surf1": 0, "surf2": 5}) == max(glass)
    assert value(s, {"op": "MNCA", "surf1": 0, "surf2": 5}) == min(air) and value(s, {"op": "MXCA", "surf1": 0, "surf2": 5}) == max(air)
    assert value(s, {"op": "MNCG", "surf1": 2, "surf2": 3}) == TS[2]
    with pytest.raises(ValueError, match="no glass thickness"):
        value(s, {"op": "MNCG", "surf1": 1, "surf2": 1})


def test_working_f_number_of_an_ideal_lens_is_efl_over_twice_the_pupil_radius():
    f, h = 1000.0, 0.5
    s = RT.lens_system([{"f": f, "t": None, "ap": h}], stop=0)
    got = value(s, {"op": "WFNO"})
    assert abs(got / (f / (2.0 * h)) - 1.0) < 1e-6
    # the same ideal lens, a hundred times faster: the sin() makes the real-ray number differ from f/2h at order (h/f)^2
    s2 = RT.lens_system([{"f": 50.0, "t": None, "ap": 5.0}], stop=0)
    exact = 1.0 / (2.0 * 5.0 / math.hypot(5.0, 50.0))
    assert abs(value(s2, {"op": "WFNO"}) - exact) < 1e-12 and abs(exact / 5.0 - 1.0) > 4e-3


def test_paraxial_magnification_of_an_ideal_lens():
    s = RT.lens_system([{"f": 50.0, "t": None, "ap": 5.0}], stop=0, object_mm=200.0)
    assert abs(value(s, {"op": "PMAG"}) - (-50.0 / (200.0 - 50.0))) < 1e-12
    assert value(RT.lens_system(), {"op": "PMAG"}) == 0.0                            # object at infinity


def test_real_ray_height_and_angle_of_incidence_after_a_refracting_sphere():
    R, n, d, ap = 50.0, 1.5, 30.0, 5.0
    s = RT.lens_system([{"R": R, "t": d, "n": n, "ap": ap}], stop=0)
    for py in (0.2, 0.6, 0.9):
        h = py * ap
        ti = math.asin(h / R)
        tt = math.asin(math.sin(ti) / n)
        zs = R - math.sqrt(R * R - h * h)
        expect = h - (d - zs) * math.tan(ti - tt)
        got = value(s, {"op": "REAY", "surf": 1, "py": py})
        assert abs(got - expect) < 1e-12, (py, got, expect)
        assert abs(value(s, {"op": "REAY", "surf": 0, "py": py}) - h) < 1e-12
        assert abs(value(s, {"op": "RAID", "surf": 0, "py": py}) - math.degrees(ti)) < 1e-12
    assert abs(value(s, {"op": "REAX", "surf": 1, "px": 0.6, "py": 0.0}) - (3.0 - (d - (R - math.sqrt(R * R - 9.0))) *
                                                                  math.tan(math.asin(3.0 / R) - math.asin(3.0 / R / n)))) < 1e-12


def test_seidel_spherical_aberration_of_one_refracting_surface_is_welfords_closed_form():
    R, n, ap = 50.0, 1.5, 5.0
    s = RT.lens_system([{"R": R, "t": 20.0, "n": n, "ap": ap}], stop=0)
    expect = ap ** 4 * (1.0 / R) ** 3 * (n - 1.0) / (n * n) / (s["wavelength_um"] * 1e-3)
    assert abs(value(s, {"op": "SPHA"}) / expect - 1.0) < 1e-9
    # the five sums are exactly the ones seidel_coefficients reports (in waves)
    t = triplet()
    w = RT.seidel_coefficients(t, 14.0)["waves"]
    for op, key in (("SPHA", "S_I"), ("COMA", "S_II"), ("ASTI", "S_III"), ("FCUR", "S_IV"), ("DIST", "S_V")):
        assert value(t, {"op": op, "field": 1}, fields=FIELDS3) == w[key]


def test_axial_colour_of_a_thin_lens_is_the_difference_of_the_two_focal_lengths():
    nd, vd, c0, c1 = 1.5168, 64.17, 0.02, -0.02
    s = RT.lens_system([{"R": 1 / c0, "t": 0.0, "n": (nd, vd), "ap": 5.0}, {"R": 1 / c1, "t": None, "n": 1.0}], stop=0)
    g = RT.glass(nd, vd)
    nF = g["A"] + g["B"] / RT.WL_F ** 2
    nC = g["A"] + g["B"] / RT.WL_C ** 2
    expect = 1.0 / ((nF - 1.0) * (c0 - c1)) - 1.0 / ((nC - 1.0) * (c0 - c1))
    assert abs(value(s, {"op": "AXCL"}) - expect) < 1e-10 and expect < 0.0
    t = triplet()
    assert abs(value(t, {"op": "AXCL"}) - RT.chromatic_shift(t, (RT.WL_F, RT.WL_C), rings=1)["axial_color"]) < 1e-12


def test_distortion_and_opd_of_an_ideal_lens_vanish():
    s = RT.lens_system([{"f": 50.0, "t": None, "ap": 5.0}], stop=0)
    assert value(s, {"op": "DIMX"}, fields=[0.0, 10.0, 20.0]) < 1e-9
    for fi in (0, 1, 2):
        assert abs(value(s, {"op": "OPDX", "field": fi, "py": 0.8}, fields=[0.0, 10.0, 20.0])) < 1e-6
    assert value(s, {"op": "WFRMS", "size": 9}) < 1e-6


def test_rsch_is_at_least_rsce_and_equal_when_the_centroid_is_the_chief_ray():
    t = triplet()
    for fi in (0, 1, 2):
        e = value(t, {"op": "RSCE", "field": fi, "pupil_fill": 0.8}, fields=FIELDS3)
        h = value(t, {"op": "RSCH", "field": fi, "pupil_fill": 0.8}, fields=FIELDS3)
        assert h >= e - 1e-15 and e > 0.0
        assert h * h - e * e > 0.0 or fi == 0                                          # off axis they genuinely differ
    # an aberration-free ideal lens, defocused on axis: the blur is a symmetric disc, centroid == chief ray
    s = RT.lens_system([{"f": 50.0, "t": None, "ap": 5.0}], stop=0, image_mm=48.0)
    e, h = value(s, {"op": "RSCE", "pupil_fill": 1.0}), value(s, {"op": "RSCH", "pupil_fill": 1.0})
    assert e > 0.05 and abs(e - h) < 1e-12
    # in focus the ideal lens has no blur at all, for either reference
    f = RT.lens_system([{"f": 50.0, "t": None, "ap": 5.0}], stop=0)
    assert value(f, {"op": "RSCE", "pupil_fill": 1.0}) < 1e-9 and value(f, {"op": "RSCH", "pupil_fill": 1.0}) < 1e-9


# --------------------------------------------------------------------------- #
# consistency with lensopt and raytrace
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("kw", [
    {}, {"fields": [0.0, 7.0, 10.0]}, {"fields": [0.0, 14.0], "field_weights": [1.0, 3.0]},
    {"fields": [0.0, 14.0, 20.0], "wavelengths": [RT.WL_F, 0.58756, RT.WL_C], "rings": 3},
])
def test_default_spot_merit_equals_lensopt_merit_function(kw):
    s = triplet()
    kw = dict(kw)
    kw.setdefault("rings", 4)
    efl = RT.paraxial_trace(s)["efl"]
    ref = LO.merit_function(s, efl_target=efl, **kw)
    m = LM.merit_default(s, kind="spot", reference="chief", **kw)
    got = LM.merit_evaluate(s, m)
    assert got["n_residuals"] == ref["n_residuals"]
    assert abs(got["merit"] - ref["merit"]) <= 1e-9 * ref["merit"], (got["merit"], ref["merit"])


def test_default_spot_merit_equals_lensopt_after_an_optimisation_step_too():
    s = triplet()
    r = LO.optimize_lens(s, ["c1", "c2", "c4"], fields=FIELDS3, rings=3, iterations=3)
    efl = RT.paraxial_trace(s)["efl"]
    ref = LO.merit_function(r["system"], fields=FIELDS3, rings=3, efl_target=efl)
    got = LM.merit_evaluate(r["system"], LM.merit_default(s, fields=FIELDS3, rings=3))
    assert abs(got["merit"] - ref["merit"]) <= 1e-9 * ref["merit"]


def test_centroid_reference_never_exceeds_the_chief_reference_and_efl_hold_is_shared():
    s = triplet()
    kw = dict(fields=FIELDS3, rings=3, pupil_fill=0.8)
    a = LM.merit_evaluate(s, LM.merit_default(s, reference="chief", **kw))
    b = LM.merit_evaluate(s, LM.merit_default(s, reference="centroid", **kw))
    assert b["merit"] <= a["merit"] and b["merit"] < 0.99 * a["merit"]
    efl = [r for r in a["table"] if r["op"] == "EFFL"][0]
    assert efl["contribution"] == [r for r in b["table"] if r["op"] == "EFFL"][0]["contribution"]
    assert all(r["rays_lost"] == 0 for r in a["table"] if r["op"] == "TRAN")


@pytest.mark.parametrize("aim", ["paraxial", "stop"])
@pytest.mark.parametrize("fi", [0, 1, 2])
def test_opd_at_points_equals_opd_samples_on_the_grid(aim, fi):
    s = triplet(aim)
    field = FIELDS3[fi]
    px, py, w, valid = RT.opd_samples(s, field=field, size=9)
    inside = px * px + py * py <= 1.0 + 1e-12
    mine, mv = LM._opd_points(s, field, s["wavelength_um"], px[inside], py[inside])
    both = valid[inside] & mv
    assert both.sum() > 20
    assert np.abs(mine[both] - w[inside][both]).max() < 1e-9


def test_wfrms_is_the_piston_removed_rms_of_opd_map():
    s = triplet()
    r = value(s, {"op": "WFRMS", "field": 2, "size": 11}, fields=FIELDS3)
    m = RT.opd_map(s, field=20.0, size=11, fill=np.nan)
    v = m[np.isfinite(m)]
    assert abs(r - float(np.sqrt(np.mean((v - v.mean()) ** 2)))) < 1e-9


def test_every_operand_evaluates_to_a_finite_number_on_a_real_prescription():
    s = triplet()
    rows = [{"op": "EFFL"}, {"op": "TOTR"}, {"op": "TTHI", "surf1": 0, "surf2": 3}, {"op": "CTGT", "surf": 0}, {"op": "CTLT", "surf": 2},
            {"op": "ETGT", "surf": 0}, {"op": "ETLT", "surf": 4}, {"op": "MNCG", "surf1": 0, "surf2": 4},
            {"op": "MXCG", "surf1": 0, "surf2": 4}, {"op": "MNCA", "surf1": 0, "surf2": 4}, {"op": "MXCA", "surf1": 0, "surf2": 4},
            {"op": "REAY", "surf": 6, "field": 1, "py": 0.5}, {"op": "REAX", "surf": 6, "field": 1, "px": 0.4, "py": 0.0},
            {"op": "RAID", "surf": 3, "field": 2, "py": 0.5},
            {"op": "OPDX", "field": 1, "py": 0.5}, {"op": "SPHA"}, {"op": "COMA", "field": 1}, {"op": "ASTI", "field": 1},
            {"op": "FCUR", "field": 1}, {"op": "DIST", "field": 1}, {"op": "AXCL"}, {"op": "LACL", "field": 2}, {"op": "RSCE", "field": 1},
            {"op": "RSCH", "field": 1}, {"op": "WFNO"}, {"op": "PMAG"}, {"op": "DIMX"}, {"op": "WFRMS", "field": 1, "size": 9},
            {"op": "TRAN", "field": 1, "rings": 2}, {"op": "OPDW", "field": 1, "rings": 2}]
    seen = {r["op"] for r in rows}
    assert seen == set(LM.merit_operands_list()["names"])
    for row in rows:
        ev = LM.merit_evaluate(s, [dict(row, target=0.0)], fields=FIELDS3)["table"][0]
        assert math.isfinite(ev["value"]), row


def test_all_fields_and_wavelengths_expand_to_weighted_rows():
    s = triplet()
    ev = LM.merit_evaluate(s, [{"op": "RSCE", "field": "all", "wavelength": "all", "target": 0.0}], fields=FIELDS3,
                           wavelengths=[RT.WL_F, 0.58756, RT.WL_C], field_weights=[1.0, 4.0, 9.0], wavelength_weights=[1.0, 2.0, 3.0])
    assert ev["n_operands"] == 9
    r = ev["table"][4]                                   # field 1, wavelength 1
    assert abs(r["weight"] - math.sqrt(4.0 * 2.0)) < 1e-15
    assert abs(r["contribution"] - r["weight"] ** 2 * r["value"] ** 2) < 1e-18
    assert abs(sum(x["percent"] for x in ev["table"]) - 100.0) < 1e-9


def test_one_sided_rows_contribute_nothing_while_the_bound_holds():
    s = triplet()
    e = value(s, {"op": "ETGT", "surf": 0})
    for target, hit in ((e - 0.5, False), (e + 0.5, True)):
        r = LM.merit_evaluate(s, [{"op": "ETGT", "surf": 0, "target": target, "weight": 3.0}])["table"][0]
        assert (r["contribution"] > 0.0) == hit and r["satisfied"] != hit
        if hit:
            assert abs(r["contribution"] - (3.0 * 0.5) ** 2) < 1e-12 and abs(r["margin"] + 0.5) < 1e-12
        else:
            assert r["margin"] > 0.4
    # the same bound written the other way round with an explicit sense
    r = LM.merit_evaluate(s, [{"op": "TOTR", "target": 70.0, "sense": "le"}, {"op": "TOTR", "target": 70.0, "sense": "ge"}])["table"]
    assert r[0]["contribution"] == 0.0 and r[1]["contribution"] > 0.0


def test_boundary_operands_cover_every_glass_element():
    s = triplet()
    b = LM.merit_boundary_operands(s, min_edge=1.0, min_centre=2.0, max_centre=8.0, min_air=0.5)
    assert b["elements"] == [0, 2, 4]
    ops = [r["op"] for r in b["operands"]]
    assert ops.count("ETGT") == 3 and ops.count("MNCG") == 1 and ops.count("MXCG") == 1 and ops.count("MNCA") == 1
    ev = LM.merit_evaluate(s, b["operands"])
    assert ev["n_operands"] == len(ops)
    assert {r["label"] for r in ev["table"] if not r["satisfied"]} == {"MNCG(surf1=0,surf2=4)"}   # the 1.0 mm middle element
    with pytest.raises(ValueError, match="no glass"):
        LM.merit_boundary_operands(RT.lens_system([{"R": INF, "t": 5.0, "n": 1.0, "ap": 3.0}, {"R": INF, "t": None, "n": 1.0}], stop=0))
    with pytest.raises(ValueError, match="no bound requested"):
        LM.merit_boundary_operands(s, min_edge=None)


# --------------------------------------------------------------------------- #
# the second implementation
# --------------------------------------------------------------------------- #
def _optiland_numbers():
    """The numbers optiland gives for the prescription above (the generator of tests/data/lensmerit_optiland_ref.json)."""
    from optiland.optic import Optic
    from optiland.materials import IdealMaterial
    from optiland.wavefront import OPD
    L = Optic()
    L.surfaces.add(index=0, thickness=np.inf)
    for i in range(6):
        kw = dict(index=i + 1, radius=RS[i], thickness=TS[i], is_stop=(i == 0))
        if NS[i] != 1.0:
            kw["material"] = IdealMaterial(n=NS[i])
        L.surfaces.add(**kw)
    L.surfaces.add(index=7)
    L.set_aperture(aperture_type="EPD", value=8.0)
    L.fields.set_type("angle")
    for y in FIELDS3:
        L.fields.add(y=y)
    L.wavelengths.add(value=0.58756, is_primary=True)
    out = {"efl": float(L.paraxial.f2()), "image_xy": {}, "rsce": {}, "opd": {}}
    for fi, hy in ((1, 0.7), (2, 1.0)):
        for (px, py) in PTS:
            r = L.trace_generic(Hx=0, Hy=hy, Px=px, Py=py, wavelength=0.58756)
            out["image_xy"]["%d,%g,%g" % (fi, px, py)] = [float(r.x[0]), float(r.y[0])]
    pts = [(0.0, 0.0)]
    for ring in range(1, 4):
        for j in range(6 * ring):
            a = 2 * np.pi * j / (6 * ring)
            pts.append((ring / 3.0 * 0.8 * np.cos(a), ring / 3.0 * 0.8 * np.sin(a)))
    for fi, hy in ((0, 0.0), (1, 0.7), (2, 1.0)):
        xs, ys = [], []
        for (px, py) in pts:
            r = L.trace_generic(Hx=0, Hy=hy, Px=px, Py=py, wavelength=0.58756)
            xs.append(float(r.x[0]))
            ys.append(float(r.y[0]))
        xs, ys = np.array(xs), np.array(ys)
        out["rsce"][str(fi)] = float(np.sqrt(np.mean((xs - xs.mean()) ** 2 + (ys - ys.mean()) ** 2)))
    for fi, hy in ((0, 0.0), (1, 0.7), (2, 1.0)):
        o = OPD(L, field=(0, hy), wavelength=0.58756, num_rays=3, distribution="hexapolar", strategy="chief_ray")
        d = o.get_data(o.fields[0], o.wavelengths[0])
        out["opd"][str(fi)] = [float(v) for v in np.asarray(d.opd).ravel()]
    return out


def _ours_against(ref, tol_mm=1e-6, tol_opd0=1e-9, tol_opd=5e-3):
    """Our operands against the second implementation's numbers *ref*. Returns the worst differences found."""
    s = triplet()
    worst = {"efl": abs(value(s, {"op": "EFFL"}) - ref["efl"])}
    xy = 0.0
    for key, (rx, ry) in ref["image_xy"].items():
        fi, px, py = key.split(",")
        for ax, rv in (("REAX", rx), ("REAY", ry)):
            got = value(s, {"op": ax, "surf": 6, "field": int(fi), "px": float(px), "py": float(py)}, fields=FIELDS3)
            xy = max(xy, abs(got - rv))
    worst["image_xy"] = xy
    worst["rsce"] = max(abs(value(s, {"op": "RSCE", "field": int(fi), "rings": 3, "pupil_fill": 0.8}, fields=FIELDS3) - v)
                        for fi, v in ref["rsce"].items())
    px, py = RT._pupil_grid(3)
    opd = {}
    for fi, vals in ref["opd"].items():
        w, valid = LM._opd_points(s, FIELDS3[int(fi)], 0.58756, px, py)
        ok = valid & np.isfinite(np.array(vals))
        assert ok.sum() >= 19
        opd[fi] = float(np.abs(w[ok] - np.array(vals)[ok]).max() / np.abs(np.array(vals)[ok]).max())   # relative to the peak OPD
    worst["opd_on_axis"] = opd["0"]
    worst["opd_off_axis"] = max(opd["1"], opd["2"])
    assert worst["efl"] < tol_mm and worst["image_xy"] < tol_mm and worst["rsce"] < tol_mm, worst
    assert worst["opd_on_axis"] < tol_opd0 and worst["opd_off_axis"] < tol_opd, worst
    return worst


def test_against_the_recorded_numbers_of_a_second_implementation():
    """EFL, real ray positions at the image (3 pupil points, 2 fields), RMS spot about the centroid: 1e-6 mm. OPD on
    axis 1e-9 waves; off axis 0.5 % of the peak OPD. The off-axis difference is a convention: optiland's reference sphere
    has the distance from the chief ray's image point to the on-axis exit pupil centre as its radius (69.13 mm at 20 deg),
    ``raytrace.opd_samples`` the axial distance only (66.71 mm); measured 0.03 % of the peak at 14 deg and 0.25 % at 20 deg."""
    assert REF["version"] == "0.6.3" and "MIT" in REF["source"]
    w = _ours_against(REF)
    assert w["image_xy"] < 1e-9                                                           # in fact far inside the 1e-6 gate


def test_against_the_second_implementation_live_when_it_is_installed():
    ol = pytest.importorskip("optiland", reason="optiland is not installed: the recorded numbers above stand in for it")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        live = _optiland_numbers()
    assert abs(live["efl"] - REF["efl"]) < 1e-9
    for key, v in REF["image_xy"].items():
        assert np.abs(np.array(live["image_xy"][key]) - np.array(v)).max() < 1e-9
    _ours_against(live)


# --------------------------------------------------------------------------- #
# the optimiser
# --------------------------------------------------------------------------- #
def detuned_triplet():
    """The prescription above with every radius moved by 7-10 % and model glasses (n_d, V_d): a bad but valid start."""
    mult = [1.08, 0.9, 0.93, 1.1, 0.92, 1.07]
    surf = [{"R": RS[i] * mult[i], "t": TS[i], "n": (NS[i], 60.3 if i in (0, 4) else 36.4) if NS[i] != 1.0 else 1.0,
             "ap": 4.0 if i == 0 else None} for i in range(6)]
    return RT.lens_system(surf, stop=0, field=20.0)


def test_optimiser_lowers_the_merit_monotonically_and_holds_the_efl():
    s = detuned_triplet()
    m = LM.merit_default(s, rings=3, fields=FIELDS3, pupil_fill=0.8)
    r = LM.optimize_lens_operands(s, m, ["c0", "c1", "c2", "c3", "c4", "c5"], iterations=20)
    h = r["history"]
    assert all(b < a for a, b in zip(h, h[1:])) and len(h) >= 4
    assert r["merit_final"] < 0.01 * r["merit_initial"] and r["merit_final"] == pytest.approx(h[-1], rel=1e-12)
    assert abs(RT.paraxial_trace(r["system"])["efl"] / RT.paraxial_trace(s)["efl"] - 1.0) < 1e-3
    assert r["table_before"]["merit"] == r["merit_initial"] and r["table_after"]["merit"] == r["merit_final"]
    assert r["rejected_steps"] >= 0 and r["iterations"] >= 1 and r["glass"] == []
    # the same pupil, lensopt: the same optimiser class of problem -- the operand merit starts from the same number
    assert abs(r["merit_initial"] - LO.merit_function(s, fields=FIELDS3, rings=3, pupil_fill=0.8,
                                                      efl_target=RT.paraxial_trace(s)["efl"])["merit"]) < 1e-9 * r["merit_initial"]


def test_a_bound_operand_is_enforced_through_the_table():
    # a biconvex lens whose edge is negative: the bound pulls the centre thickness up until the edge is 1 mm
    s = RT.lens_system([{"R": 50.0, "t": 1.0, "n": 1.5, "ap": 10.0}, {"R": -50.0, "t": None, "n": 1.0}], stop=0)
    assert value(s, {"op": "ETGT", "surf": 0}) < 0.0
    ops = [{"op": "EFFL", "target": RT.paraxial_trace(s)["efl"], "weight": 1.0},
           {"op": "ETGT", "surf": 0, "target": 1.0, "weight": 100.0}, {"op": "RSCH", "target": 0.0, "weight": 1.0}]
    r = LM.optimize_lens_operands(s, ops, ["c0", "c1", "t0"], iterations=60)
    row = [x for x in r["table_after"]["table"] if x["op"] == "ETGT"][0]
    assert row["value"] > 1.0 - 1e-3 and r["violated_after"] in ([], ["ETGT(surf=0)"])
    assert r["system"]["surfaces"][0]["t"] > 3.0
    assert [x for x in r["table_before"]["table"] if x["op"] == "ETGT"][0]["value"] < 0.0


# --------------------------------------------------------------------------- #
# glass as a variable
# --------------------------------------------------------------------------- #
def _singlet():
    return RT.lens_system([{"R": 55.0, "t": 4.0, "n": (1.5, 60.0), "ap": 6.0}, {"R": -400.0, "t": None, "n": 1.0}], stop=0)


GRID = [(1.50, 60.0), (1.60, 60.0), (1.70, 60.0), (1.80, 60.0)]


def test_a_single_candidate_equal_to_the_current_glass_is_the_continuous_result():
    s = _singlet()
    m = LM.merit_default(s, rings=3)
    a = LM.optimize_lens_operands(s, m, ["c0", "c1"], iterations=15)
    b = LM.optimize_lens_operands(s, m, ["c0", "c1", "g0"], iterations=15, glass_candidates=[(1.5, 60.0)])
    assert b["merit_final"] == a["merit_final"] and b["history"] == a["history"] and b["iterations"] == a["iterations"]
    assert [x["R"] for x in b["system"]["surfaces"]] == [x["R"] for x in a["system"]["surfaces"]]
    assert b["glass"][0]["tried"] == [] and not b["glass"][0]["changed"]
    # a candidate given as a raytrace.glass dict is the same glass, still skipped
    c = LM.optimize_lens_operands(s, m, ["c0", "c1", "g0"], iterations=15, glass_candidates=[RT.glass(1.5, 60.0)])
    assert c["merit_final"] == a["merit_final"]


def test_the_glass_sweep_picks_the_candidate_a_brute_force_continuous_run_picks():
    s = _singlet()
    m = LM.merit_default(s, rings=3)
    r = LM.optimize_lens_operands(s, m, ["c0", "c1", "g0"], iterations=40, glass_candidates=GRID)
    brute = []
    for cand in GRID:
        sc = RT.lens_system([dict(x, n=cand) if i == 0 else dict(x) for i, x in enumerate(s["surfaces"])], stop=0)
        brute.append(LM.optimize_lens_operands(sc, m, ["c0", "c1"], iterations=40)["merit_final"])
    best = GRID[int(np.argmin(brute))]
    assert best == GRID[-1]                                       # higher index, less spherical aberration at fixed focal length
    g = r["glass"][0]
    assert g["changed"] and LM._medium_key(g["final"]) == LM._medium_key(best)
    assert r["merit_final"] < brute[0] and r["merit_final"] <= 1.05 * min(brute)
    assert {tuple(t["candidate"]) for t in g["tried"]} >= {c for c in GRID if c != (1.5, 60.0)}
    assert all(t["merit"] is not None for t in g["tried"])


def test_a_glass_variable_needs_candidates_and_a_glass_surface():
    s = _singlet()
    m = LM.merit_default(s, rings=2)
    with pytest.raises(ValueError, match="glass_candidates"):
        LM.optimize_lens_operands(s, m, ["c0", "g0"])
    with pytest.raises(ValueError, match="no glass"):
        LM.optimize_lens_operands(s, m, ["c0", "g1"], glass_candidates=GRID)
    with pytest.raises(ValueError, match="not a usable medium"):
        LM.optimize_lens_operands(s, m, ["c0", "g0"], glass_candidates=["NOT-A-GLASS"])
    with pytest.raises(ValueError, match="duplicate"):
        LM.optimize_lens_operands(s, m, ["g0", "g0"], glass_candidates=GRID)


# --------------------------------------------------------------------------- #
# probes: each of these must go red when the safeguard is removed
# --------------------------------------------------------------------------- #
def test_a_bound_that_cannot_be_met_is_reported_as_the_dominant_violated_operand():
    s = RT.lens_system([{"R": 55.0, "t": 4.0, "n": (1.5, 60.0), "ap": 8.0}, {"R": -400.0, "t": None, "n": 1.0}], stop=0)
    ops = [{"op": "EFFL", "target": RT.paraxial_trace(s)["efl"], "weight": 1.0}, {"op": "RSCH", "target": 0.0, "weight": 1.0},
           {"op": "ETGT", "surf": 0, "target": 50.0, "weight": 1.0}]
    r = LM.optimize_lens_operands(s, ops, ["c0", "c1", "t0"], iterations=30, max_thickness=6.0)
    assert r["dominant_after"] == "ETGT(surf=0)" and r["violated_after"] == ["ETGT(surf=0)"]
    row = [x for x in r["table_after"]["table"] if x["op"] == "ETGT"][0]
    assert row["margin"] < -40.0 and not row["satisfied"] and row["percent"] > 99.0
    c = LM.merit_contributions(r["system"], ops)
    assert c["dominant"]["label"] == "ETGT(surf=0)" and c["violated"] == ["ETGT(surf=0)"]
    assert [x["percent"] for x in c["contributions"]] == sorted((x["percent"] for x in c["contributions"]), reverse=True)
    assert abs(c["contributions"][-1]["cumulative"] - 100.0) < 1e-9
    # reachable target: nothing is violated afterwards
    ok = [dict(o, target=1.0) if o["op"] == "ETGT" else o for o in ops]
    r2 = LM.optimize_lens_operands(s, ok, ["c0", "c1", "t0"], iterations=30, max_thickness=6.0)
    assert r2["violated_after"] == []


def test_an_unknown_operand_a_missing_argument_and_an_unknown_argument_are_refused():
    s = triplet()
    with pytest.raises(ValueError, match="unknown operand 'XXXX'.*known operands:.*EFFL.*TRAN"):
        LM.merit_evaluate(s, [{"op": "XXXX", "target": 0}])
    with pytest.raises(ValueError, match="missing required argument 'surf'"):
        LM.merit_evaluate(s, [{"op": "ETGT", "target": 1.0}])
    with pytest.raises(ValueError, match="missing required argument 'target'"):
        LM.merit_evaluate(s, [{"op": "EFFL"}])
    with pytest.raises(ValueError, match="unknown argument.*bogus"):
        LM.merit_evaluate(s, [{"op": "EFFL", "target": 50.0, "bogus": 1}])
    with pytest.raises(ValueError, match="target is 0"):
        LM.merit_evaluate(s, [{"op": "TRAN", "target": 0.1}])
    with pytest.raises(ValueError, match="sense"):
        LM.merit_evaluate(s, [{"op": "EFFL", "target": 50.0, "sense": "gt"}])
    with pytest.raises(ValueError, match="non-empty list"):
        LM.merit_evaluate(s, [])
    for bad in (None, 5, "EFFL"):
        with pytest.raises(ValueError):
            LM.merit_evaluate(s, [bad])


def test_a_wrong_index_is_refused():
    s = triplet()
    with pytest.raises(ValueError, match="field index 3 is out of range 0..2"):
        LM.merit_evaluate(s, [{"op": "RSCE", "field": 3, "target": 0.0}], fields=FIELDS3)
    with pytest.raises(ValueError, match="field index"):
        LM.merit_evaluate(s, [{"op": "RSCE", "field": 1, "target": 0.0}])               # the default fields of this system: [0]
    with pytest.raises(ValueError, match="wavelength index 2 is out of range 0..0"):
        LM.merit_evaluate(s, [{"op": "REAY", "surf": 1, "wavelength": 2, "target": 0.0}])
    with pytest.raises(ValueError, match="surf"):
        LM.merit_evaluate(s, [{"op": "REAY", "surf": 7, "target": 0.0}])                  # 6 is the image plane, 7 does not exist
    with pytest.raises(ValueError, match="surf"):
        LM.merit_evaluate(s, [{"op": "ETGT", "surf": 5, "target": 1.0}])                  # the last surface has no next surface
    with pytest.raises(ValueError, match="integer"):
        LM.merit_evaluate(s, [{"op": "CTGT", "surf": 1.5, "target": 1.0}])
    with pytest.raises(ValueError, match="integer"):
        LM.merit_evaluate(s, [{"op": "CTGT", "surf": True, "target": 1.0}])
    with pytest.raises(ValueError, match="surf1"):
        LM.merit_evaluate(s, [{"op": "MNCG", "surf1": 3, "surf2": 1, "target": 1.0}])


def test_all_weights_zero_is_an_empty_merit_and_is_refused():
    s = triplet()
    zero = [{"op": "EFFL", "target": 50.0, "weight": 0.0}, {"op": "TOTR", "target": 60.0, "weight": 0}]
    with pytest.raises(ValueError, match="weight 0"):
        LM.merit_evaluate(s, zero)
    with pytest.raises(ValueError, match="weight 0"):
        LM.optimize_lens_operands(s, zero, ["c0"])
    with pytest.raises(ValueError, match="weight"):
        LM.merit_evaluate(s, [{"op": "EFFL", "target": 50.0, "weight": -1.0}])
    # one live row is enough, and a zero-weight row is carried but contributes nothing
    ev = LM.merit_evaluate(s, zero + [{"op": "TOTR", "target": 0.0, "weight": 1.0}])
    assert ev["table"][0]["contribution"] == 0.0 and ev["merit"] > 0.0


def test_not_finite_values_and_lost_rays_are_refused_not_returned():
    afocal = RT.lens_system([{"R": INF, "t": 5.0, "n": 1.5, "ap": 5.0}, {"R": INF, "t": None, "n": 1.0}], stop=0)
    with pytest.raises(ValueError, match="not finite"):
        LM.merit_evaluate(afocal, [{"op": "EFFL", "target": 50.0}])
    with pytest.raises(ValueError, match="lost"):
        LM.merit_evaluate(triplet(), [{"op": "REAY", "surf": 6, "field": 2, "py": 1.0, "target": 0.0}], fields=FIELDS3)
    with pytest.raises(ValueError):
        LM.merit_default(triplet(), kind="nope")
    with pytest.raises(ValueError):
        LM.merit_default(triplet(), reference="nope")
    with pytest.raises(ValueError):
        LM.merit_default(triplet(), efl_target=0.0)
    with pytest.raises(ValueError):
        LM.optimize_lens_operands(triplet(), None, ["c0"], iterations=0)
    with pytest.raises(ValueError):
        LM.optimize_lens_operands(triplet(), None, ["c9"])


def test_the_optimiser_is_deterministic():
    s = _singlet()
    m = LM.merit_default(s, rings=3)
    runs = [LM.optimize_lens_operands(s, m, ["c0", "c1", "g0"], iterations=25, glass_candidates=GRID) for _ in range(2)]
    a, b = runs
    assert a["history"] == b["history"] and a["merit_final"] == b["merit_final"] and a["rejected_steps"] == b["rejected_steps"]
    assert [x["R"] for x in a["system"]["surfaces"]] == [x["R"] for x in b["system"]["surfaces"]]
    assert a["glass"] == b["glass"]
    e1, e2 = LM.merit_evaluate(s, m), LM.merit_evaluate(s, m)
    assert e1 == e2


def test_the_input_prescription_is_not_modified():
    s = _singlet()
    before = [dict(x) for x in s["surfaces"]]
    LM.optimize_lens_operands(s, LM.merit_default(s, rings=2), ["c0", "c1", "g0"], iterations=5, glass_candidates=GRID)
    assert s["surfaces"] == before
