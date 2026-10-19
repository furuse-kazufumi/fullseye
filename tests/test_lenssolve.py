"""Sequential optical design, 7th slice: solves, pickups, afocal systems, a curved image surface, odd aspheres (lenssolve).

Ground truth, none of it taken from the code under test:

* **Paraxial closed forms** (Smith, *Modern Optical Engineering*; Kingslake & Johnson, *Lens Design Fundamentals*): the
  refraction equation ``n' u' = n u - y c (n' - n)`` and the transfer ``y' = y + t u'`` are written out below for the small
  prescriptions, and every solved quantity is compared with the hand solution of the one linear equation it comes from
  (thickness for a ray height, curvature for a ray angle, curvature for an image-space F/#, with its two roots).
* **The aplanatic points of a refracting sphere** (Weierstrass; Born & Wolf): an object at ``l = R (n + n') / n`` from the
  vertex is imaged *exactly* (every real ray, not only the paraxial one) at ``l' = R (n + n') / n'``; the rays of a surface
  solved for that object have a zero spot at the virtual image, and an ordinary radius does not.
* **A monocentric ball**: a ray aimed at the common centre of two concentric surfaces meets both at normal incidence and
  leaves undeviated (the ``concentric`` solve).
* **Ideal-lens telescopes**: with the thin-lens law ``tan(theta') = tan(theta) - h/f`` a Keplerian telescope (f1, f2 > 0,
  separation f1 + f2) has the angular magnification ``-f1/f2`` for *every* ray and every field, a Galilean one
  (f2 < 0) ``+f1/|f2|``.
* **The Petzval surface of a thin lens**: with the stop on the lens the astigmatism is zero, so the sagittal and tangential
  surfaces are the Petzval surface, of radius ``-N f`` in air.
* **The sag** of a conic plus a power series, written out here, and the surface equation ``z - sag(r) = 0`` for the points
  a ray is traced to.
* **Real files**: the pickup lines the ``.zmx`` format carries (``CURV c 4 source scale offset``, ``PZUP``, ``PPAR``).
"""
import copy
import glob
import json
import math
import os

import numpy as np
import pytest

import lensfile as LF
import lensmerit as LM
import lenssolve as LS
import opsoptics
import raytrace as RT

INF = float("inf")
N1, V1 = 1.5168, 64.17
N2, V2 = 1.6200, 36.37
DATA = os.path.join(os.path.dirname(__file__), "data", "lensfile")
OPS = ["afocal_system", "lens_afocal_report", "lens_apply_solves", "lens_image_surface", "lens_petzval_radius",
       "lens_solve_clear", "lens_solve_set", "lens_solves_list", "lens_zmx_solves_roundtrip"]


def abcd(system, y0, u0):
    """Independent paraxial trace (constant indices, no mirrors): heights at each surface and the slope after it."""
    n = float(system["index_object"])
    y, u = y0, u0
    ys, us = [], []
    for s in system["surfaces"]:
        c = 0.0 if s["R"] == INF else 1.0 / s["R"]
        n2 = float(s["n_value"])
        nu = n * u - y * c * (n2 - n)
        u = nu / n2
        n = n2
        ys.append(y)
        us.append(u)
        y = y + (0.0 if s["t"] is None else s["t"]) * u
    return ys, us


def solved(system, i):
    return LS.lens_apply_solves(system)["surfaces"][i]


# --------------------------------------------------------------------------- #
# 0. registration
# --------------------------------------------------------------------------- #
def test_ops_are_registered_in_the_lenssolve_category():
    assert sorted(opsoptics.list_ops("lenssolve")) == OPS
    assert all(opsoptics.OPSOPTICS[o]["module"] == "lenssolve" for o in OPS)


# --------------------------------------------------------------------------- #
# 1. thickness solves
# --------------------------------------------------------------------------- #
def singlet(**first):
    s0 = {"R": 50.0, "t": None if "solve" in first else 4.0, "n": 1.5, "ap": 5.0}
    s0.update(first)
    return RT.lens_system([s0, {"R": INF, "t": 20.0, "n": 1.0}], stop=0)


@pytest.mark.parametrize("h", [0.0, 1.5, -2.0, 3.25])
def test_marginal_ray_height_solve_matches_the_hand_solution(h):
    y0, c, n = 5.0, 1.0 / 50.0, 1.5
    u1 = -y0 * c * (n - 1.0) / n                       # n' u' = - y c (n' - n) after the first surface
    want = (h - y0) / u1
    if want < 0:
        with pytest.raises(ValueError, match="negative thickness"):
            singlet(solve={"kind": "marginal_ray_height", "h": h})
        return
    s = singlet(solve={"kind": "marginal_ray_height", "h": h})
    assert s["surfaces"][0]["t"] == pytest.approx(want, rel=1e-12, abs=1e-12)
    row = LS.lens_solves_list(s)["solves"][0]
    assert abs(row["error"]) < 1e-12 and row["kind"] == "marginal_ray_height"


def test_chief_ray_height_solve_matches_the_hand_solution():
    t0, c0, n, field = 6.0, 1.0 / 50.0, 1.5, 5.0
    u0 = math.tan(math.radians(field))
    # independent: y1 = y0 + t0 u0' = 0 with u0' = (u0 - y0 c0 (n - 1)) / n  ->  y0 (1 - t0 c0 (n-1)/n) = - t0 u0 / n
    y0 = -t0 * u0 / n / (1.0 - t0 * c0 * (n - 1.0) / n)
    u1 = (u0 - y0 * c0 * (n - 1.0)) / n
    h = 1.2
    want = h / (n * u1)                                # flat second surface: u2 = n u1
    s = RT.lens_system([{"R": 50.0, "t": t0, "n": n, "ap": 5.0},
                        {"R": INF, "t": 3.0, "n": 1.0, "ap": 5.0, "solve": {"kind": "chief_ray_height", "h": h}},
                        {"R": INF, "t": 1.0, "n": 1.0}], stop=1, field=field)
    assert s["surfaces"][1]["t"] == pytest.approx(want, rel=1e-12)
    # and the chief ray is the one through the stop centre: the traced real chief ray crosses the stop at 0
    assert abs(RT.chief_ray(s)["points"][2][1]) < 1e-9


def test_paraxial_image_solve_is_what_a_missing_last_thickness_was():
    p = LF.lens_file_read(None)["system"]
    surf = [dict(x) for x in p["surfaces"]]
    surf[-1]["t"] = None
    old = RT.lens_system(surf, stop=p["stop"], object_mm=p["object_mm"], wavelength_um=p["wavelength_um"],
                         index_object=p["index_object"])
    new = LS.lens_solve_set(old, len(surf) - 1, "paraxial_image")
    assert new["surfaces"][-1]["t"] == pytest.approx(RT.paraxial_trace(old)["bfl"], rel=1e-13)
    for f in (0.0, 10.0, 20.0):
        a, b = RT.spot_stats(new, field=f), RT.spot_stats(old, field=f)
        assert a["rms_radius"] == pytest.approx(b["rms_radius"], rel=1e-9, abs=1e-12)
        assert a["chief_y"] == pytest.approx(b["chief_y"], abs=1e-11)


def test_paraxial_image_solve_with_a_finite_object():
    s = RT.lens_system([{"R": 40.0, "t": 4.0, "n": 1.5, "ap": 4.0}, {"R": -40.0, "t": None, "n": 1.0}], stop=0,
                       object_mm=200.0)
    sv = LS.lens_solve_set(s, 1, "paraxial_image")
    assert sv["surfaces"][1]["t"] == pytest.approx(RT.paraxial_trace(s)["image_mm"], rel=1e-13)


# --------------------------------------------------------------------------- #
# 2. curvature solves
# --------------------------------------------------------------------------- #
def test_marginal_ray_angle_solve_matches_the_hand_solution():
    ang = -2.0
    c = -1.5 * math.tan(math.radians(ang)) / (5.0 * (1.5 - 1.0))     # n u - n' u' = y c (n' - n), u = 0
    s = RT.lens_system([{"R": 80.0, "t": 4.0, "n": 1.5, "ap": 5.0, "solve": {"kind": "marginal_ray_angle",
                                                                            "angle_deg": ang}},
                        {"R": INF, "t": 30.0, "n": 1.0}], stop=0)
    assert 1.0 / s["surfaces"][0]["R"] == pytest.approx(c, rel=1e-12)
    ys, us = abcd(s, 5.0, 0.0)
    assert us[0] == pytest.approx(math.tan(math.radians(ang)), rel=1e-12)


def test_chief_ray_angle_solve_matches_the_hand_solution():
    field, t0, ang = 5.0, 6.0, 4.0
    u0 = math.tan(math.radians(field))
    y1 = t0 * u0 / 1.5                                 # flat stop surface, glass behind it; the chief ray is at y = 0 there
    c = (math.tan(math.radians(ang)) - u0) / (0.5 * y1)
    s = RT.lens_system([{"R": INF, "t": t0, "n": 1.5, "ap": 4.0},
                        {"R": 90.0, "t": 25.0, "n": 1.0, "ap": 5.0, "solve": {"kind": "chief_ray_angle",
                                                                                "angle_deg": ang}}],
                       stop=0, field=field)
    assert 1.0 / s["surfaces"][1]["R"] == pytest.approx(c, rel=1e-12)


def test_f_number_solve_has_two_roots_and_takes_the_one_nearest_the_start():
    n, c1, t, y0, F = 1.5, 1.0 / 60.0, 3.0, 5.0, 4.0
    nu1 = -y0 * c1 * (n - 1.0)
    y1 = y0 + t * nu1 / n
    # n' u' = nu1 - y1 c2 (1 - n) = nu1 + 0.5 y1 c2 = +-1/(2F)  ->  c2 = (+-1/(2F) - nu1) / (0.5 y1)
    roots = sorted((sgn / (2.0 * F) - nu1) / (0.5 * y1) for sgn in (1.0, -1.0))
    lens = RT.lens_system([{"R": 60.0, "t": t, "n": n, "ap": y0}, {"R": -60.0, "t": 40.0, "n": 1.0}], stop=0)
    for start_sign in (+1.0, -1.0):
        c0 = roots[1] if start_sign > 0 else roots[0]
        surf = [dict(s) for s in lens["surfaces"]]
        surf[1]["R"] = 1.0 / (c0 * 1.1)
        base = RT.lens_system(surf, stop=0)
        sv = LS.lens_solve_set(base, 1, "f_number", fno=F)
        row = LS.lens_solves_list(sv)["solves"][0]
        assert row["n_roots"] == 2
        assert row["roots"] == pytest.approx(roots, rel=1e-9, abs=1e-12)
        assert 1.0 / sv["surfaces"][1]["R"] == pytest.approx(c0, rel=1e-9)         # the nearer root is the chosen one
        assert RT.paraxial_trace(sv)["fno"] == pytest.approx(F, rel=1e-9)
        assert row["achieved"] == pytest.approx(F, rel=1e-9)


def test_f_number_solve_that_cannot_be_met_is_refused_with_the_range():
    lens = RT.lens_system([{"R": 60.0, "t": 3.0, "n": 1.5, "ap": 5.0}, {"R": -60.0, "t": 40.0, "n": 1.0}], stop=0)
    with pytest.raises(ValueError, match="no curvature giving F/# 0.1"):
        LS.lens_solve_set(lens, 1, "f_number", fno=0.1, span=0.01)


def test_concentric_ball_lens_passes_a_ray_aimed_at_the_centre_undeviated():
    ball = RT.lens_system([{"R": 20.0, "t": 10.0, "n": 1.7, "ap": 9.0},
                           {"R": -5.0, "t": 30.0, "n": 1.0, "ap": 9.0, "solve": {"kind": "concentric"}}], stop=0)
    assert ball["surfaces"][1]["R"] == pytest.approx(10.0, rel=1e-13)           # R1 - t: the centre is at z = 20
    P = np.array([[0.0, 5.0, -30.0], [0.0, -3.0, -10.0], [4.0, 0.0, -25.0]])
    C = np.array([0.0, 0.0, 20.0])
    D = C - P
    D = D / np.linalg.norm(D, axis=1, keepdims=True)
    tr = RT.trace_rays(ball, P, D)
    assert tr["valid"].all()
    assert np.max(np.abs(tr["dirs"][:, -1, :] - D)) < 1e-12
    vert = LS.lens_solve_set(ball, 1, "concentric", with_surface=0, mode="vertex")
    assert vert["surfaces"][1]["R"] == pytest.approx(-10.0, rel=1e-13)           # centre at the vertex of surface 0


def test_aplanatic_surface_images_its_object_point_without_aberration():
    s_obj, n2 = 10.0, 1.5
    R = -s_obj / (1.0 + n2) * 1.0                      # l = R (n + n') / n = - s  ->  R = - s n / (n + n')
    lens = RT.lens_system([{"R": -3.0, "t": 0.0, "n": n2, "ap": 3.0, "solve": {"kind": "aplanatic"}},
                           {"R": INF, "t": 5.0, "n": n2}], stop=0, object_mm=s_obj)
    assert lens["surfaces"][0]["R"] == pytest.approx(R, rel=1e-12)
    lp = R * (1.0 + n2) / n2                           # l' = R (n + n') / n'
    st = RT.spot_stats(lens, field=0.0, rings=8, image_mm=lp)
    assert st["rms_radius"] < 1e-9 and st["n_vignetted"] == 0
    bad = RT.lens_system([{"R": -3.0, "t": 0.0, "n": n2, "ap": 3.0}, {"R": INF, "t": 5.0, "n": n2}], stop=0, object_mm=s_obj)
    assert RT.spot_stats(bad, field=0.0, rings=8, image_mm=lp)["rms_radius"] > 1e-3


# --------------------------------------------------------------------------- #
# 3. pickups
# --------------------------------------------------------------------------- #
def test_pickups_copy_scale_and_offset_in_any_order():
    s = RT.lens_system([{"R": 50.0, "t": 4.0, "n": 1.5, "ap": 6.0},
                        {"R": -30.0, "t": 3.0, "n": 1.0, "solve": {"kind": "pickup", "source": 0, "scale": -1.0,
                                                                   "offset": 0.002}},
                        {"R": 70.0, "t": 9.0, "n": 1.6, "solve": {"kind": "pickup", "source": 3, "quantity": "c"}},
                        {"R": -80.0, "t": 2.0, "n": 1.0, "solve": {"kind": "pickup", "source": 0, "quantity": "t",
                                                                   "scale": 0.5, "offset": 1.0}},
                        {"R": INF, "t": 10.0, "n": 1.0}], stop=0)
    sf = s["surfaces"]
    assert 1.0 / sf[1]["R"] == pytest.approx(-1.0 / 50.0 + 0.002, rel=1e-12)       # -c plus an offset
    assert sf[3]["t"] == pytest.approx(0.5 * 4.0 + 1.0, rel=1e-13)                  # t = 0.5 t0 + 1
    assert sf[2]["R"] == pytest.approx(sf[3]["R"], rel=1e-12)                       # a forward reference settles


def test_circular_and_self_pickups_are_refused():
    with pytest.raises(ValueError, match="circular pickup"):
        RT.lens_system([{"R": 50.0, "t": 4.0, "n": 1.5, "ap": 6.0, "solve": {"kind": "pickup", "source": 1}},
                        {"R": -30.0, "t": 3.0, "n": 1.0, "solve": {"kind": "pickup", "source": 0}},
                        {"R": INF, "t": 10.0, "n": 1.0}], stop=0)
    with pytest.raises(ValueError, match="itself"):
        RT.lens_system([{"R": 50.0, "t": 4.0, "n": 1.5, "ap": 6.0, "solve": {"kind": "pickup", "source": 0}},
                        {"R": INF, "t": 10.0, "n": 1.0}], stop=0)


def test_an_aspheric_coefficient_can_be_picked_up():
    s = RT.lens_system([{"R": 50.0, "t": 4.0, "n": 1.5, "ap": 6.0, "asph": (1e-6, 2e-9), "a2": 3e-4},
                        {"R": -50.0, "t": 4.0, "n": 1.0, "asph": (0.0, 0.0),
                         "solve": {"kind": "pickup", "source": 0, "quantity": "A4", "scale": -1.0}},
                        {"R": INF, "t": 10.0, "n": 1.0}], stop=0)
    assert s["surfaces"][1]["asph"] == (-1e-6,)
    s2 = RT.lens_system([{"R": 50.0, "t": 4.0, "n": 1.5, "ap": 6.0, "a2": 3e-4},
                         {"R": -50.0, "t": 4.0, "n": 1.0,
                          "solve": {"kind": "pickup", "source": 0, "quantity": "A2", "scale": 2.0}},
                         {"R": INF, "t": 10.0, "n": 1.0}], stop=0)
    assert s2["surfaces"][1]["a2"] == 6e-4


# --------------------------------------------------------------------------- #
# 4. fail-closed
# --------------------------------------------------------------------------- #
def test_unknown_kind_lists_the_kinds_and_bad_arguments_are_refused():
    with pytest.raises(ValueError) as e:
        RT.lens_system([{"R": 50.0, "t": 4.0, "n": 1.5, "ap": 6.0, "solve": {"kind": "cleverness"}},
                        {"R": INF, "t": 10.0, "n": 1.0}], stop=0)
    for k in LS.SOLVE_KINDS:
        assert k in str(e.value)
    lens = singlet()
    with pytest.raises(ValueError, match="does not take"):
        LS.lens_solve_set(lens, 0, "paraxial_image", h=1.0)
    with pytest.raises(ValueError, match="needs the argument 'fno'"):
        LS.lens_solve_set(lens, 0, "f_number")
    with pytest.raises(ValueError, match="needs the argument 'source'"):
        LS.lens_solve_set(lens, 0, "pickup")
    with pytest.raises(ValueError, match="quantity"):
        LS.lens_solve_set(lens, 0, "pickup", source=1, quantity="B3")
    with pytest.raises(ValueError, match="surface must be"):
        LS.lens_solve_set(lens, 7, "paraxial_image")
    with pytest.raises(ValueError, match="takes"):
        RT.lens_system([{"R": 50.0, "t": 4.0, "n": 1.5, "ap": 6.0, "solve": {"kind": "paraxial_image", "zz": 1}},
                        {"R": INF, "t": 10.0, "n": 1.0}], stop=0)


def test_geometry_that_makes_a_solve_meaningless_is_refused():
    lens = RT.lens_system([{"R": 50.0, "t": 4.0, "n": 1.5, "ap": 5.0}, {"R": INF, "t": 5.0, "n": 1.0, "ap": 5.0},
                           {"R": INF, "t": 10.0, "n": 1.0}], stop=1)
    with pytest.raises(ValueError, match="would move the stop"):
        LS.lens_solve_set(lens, 0, "marginal_ray_height", h=1.0)
    with pytest.raises(ValueError, match="needs a field != 0"):
        LS.lens_solve_set(lens, 1, "chief_ray_height", h=1.0)
    ideal = RT.lens_system([{"f": 50.0, "t": 10.0, "ap": 5.0}, {"f": 50.0, "t": 10.0}], stop=0)
    with pytest.raises(ValueError, match="ideal lens"):
        LS.lens_solve_set(ideal, 0, "marginal_ray_angle")
    flat_first = RT.lens_system([{"R": INF, "t": 4.0, "n": 1.0, "ap": 5.0}, {"R": 50.0, "t": 10.0, "n": 1.5},
                                 {"R": INF, "t": 1.0, "n": 1.0}], stop=0)
    with pytest.raises(ValueError, match="no refraction here"):
        LS.lens_solve_set(flat_first, 0, "marginal_ray_angle", angle_deg=1.0)
    # a collimated marginal ray is on the axis nowhere, but the stop's own surface with a chief ray is
    with pytest.raises(ValueError, match="negative thickness"):
        LS.lens_solve_set(singlet(), 0, "marginal_ray_height", h=9.0)
    with pytest.raises(ValueError, match="ideal .paraxial. lens has no line"):
        LF.lens_file_write(LF._prescription_from_system(ideal), system=ideal)


# --------------------------------------------------------------------------- #
# 5. the rules live in the dict, are resolved on every trace, and are pure
# --------------------------------------------------------------------------- #
def triplet_with_solves():
    p = LF.lens_file_read(None)["system"]
    s = LS.lens_solve_set(p, 5, "paraxial_image")
    return LS.lens_solve_set(s, 4, "f_number", fno=6.0)


def test_apply_is_pure_idempotent_and_keeps_the_rules():
    s = triplet_with_solves()
    before = copy.deepcopy(s["surfaces"])
    a = LS.lens_apply_solves(s)
    assert s["surfaces"] == before                                   # the argument is untouched
    assert a is not s and a["surfaces"] is not s["surfaces"]
    assert a["surfaces"][4]["solve"]["kind"] == "f_number" and a["surfaces"][5]["solve"]["kind"] == "paraxial_image"
    b = LS.lens_apply_solves(a)
    assert len(a["surfaces"]) == len(b["surfaces"]) == 6
    for x, y in zip(a["surfaces"], b["surfaces"]):
        assert x["R"] == y["R"] and x["t"] == y["t"]
    plain = LS.lens_apply_solves(RT.lens_system())
    assert "solve_report" not in plain


def test_changing_the_stop_radius_lets_the_solves_settle_again():
    s = triplet_with_solves()
    stop = s["stop"]
    for ap in (2.0, 3.5, 6.0):
        surf = [dict(x) for x in s["surfaces"]]
        surf[stop]["ap"] = ap
        r = RT.lens_system(surf, stop=stop, object_mm=s["object_mm"], wavelength_um=s["wavelength_um"],
                           index_object=s["index_object"])
        pt = RT.paraxial_trace(r)
        assert pt["fno"] == pytest.approx(6.0, rel=1e-9)
        assert r["surfaces"][5]["t"] == pytest.approx(pt["bfl"], rel=1e-12)
    # the F/# is held although the stop shrank, so the curvature moved
    assert solved(s, 4)["R"] != RT.lens_system(surf, stop=stop, object_mm=s["object_mm"])["surfaces"][4]["R"]


def test_a_hand_edited_dict_is_resolved_before_every_trace():
    s = triplet_with_solves()
    tampered = copy.deepcopy(s)
    tampered["surfaces"][5]["t"] = 1.0                                   # stale: not what the rule gives
    tampered["surfaces"][4]["R"] = 123.0
    good = RT.spot_stats(s, field=10.0)
    again = RT.spot_stats(tampered, field=10.0)
    assert again["rms_radius"] == pytest.approx(good["rms_radius"], rel=1e-12)
    assert RT.paraxial_trace(tampered)["fno"] == pytest.approx(6.0, rel=1e-9)
    assert RT.paraxial_trace(tampered)["bfl"] == pytest.approx(s["surfaces"][5]["t"], rel=1e-12)


def test_clear_keeps_the_solved_numbers_and_drops_the_rules():
    s = triplet_with_solves()
    c = LS.lens_solve_clear(s, 4)
    assert "solve" not in c["surfaces"][4] and c["surfaces"][5]["solve"]["kind"] == "paraxial_image"
    assert c["surfaces"][4]["R"] == s["surfaces"][4]["R"]
    all_gone = LS.lens_solve_clear(s)
    assert len(all_gone["surfaces"]) == 6
    assert not any("solve" in x for x in all_gone["surfaces"])
    assert RT.spot_stats(all_gone, field=10.0)["rms_radius"] == pytest.approx(RT.spot_stats(s, field=10.0)["rms_radius"],
                                                                              rel=1e-12)
    with pytest.raises(ValueError, match="no solve to clear"):
        LS.lens_solve_clear(all_gone)
    with pytest.raises(ValueError, match="no solve to clear"):
        LS.lens_solve_clear(c, 0)


def test_a_solve_in_front_of_the_stop_settles_and_reports_its_error():
    lens = RT.lens_system([{"R": 60.0, "t": 4.0, "n": 1.5, "ap": 8.0, "solve": {"kind": "marginal_ray_angle",
                                                                                "angle_deg": -3.0}},
                           {"R": -60.0, "t": 5.0, "n": 1.0, "ap": 8.0}, {"R": INF, "t": 6.0, "n": 1.0, "ap": 4.0},
                           {"R": 100.0, "t": 40.0, "n": 1.5, "ap": 8.0}], stop=2)
    row = LS.lens_solves_list(lens)["solves"][0]
    assert abs(row["error"]) < 1e-11
    assert LS.lens_solves_list(lens)["n_solves"] == 1


def test_variables_on_a_solved_quantity_are_refused_by_the_optimiser():
    import lensopt as LO
    s = triplet_with_solves()
    with pytest.raises(ValueError, match="is set by a 'f_number' solve"):
        LO.optimize_lens(s, variables=["c4"], iterations=1)


# --------------------------------------------------------------------------- #
# 6. afocal systems
# --------------------------------------------------------------------------- #
def test_ideal_keplerian_and_galilean_telescopes_have_the_closed_form_magnification():
    for f1, f2, M in ((100.0, 25.0, -4.0), (100.0, -25.0, 4.0), (60.0, 15.0, -4.0)):
        tele = LS.afocal_system(f1=f1, f2=f2)
        pt = RT.paraxial_trace(tele)
        assert pt["angular_magnification"] == pytest.approx(M, rel=0, abs=1e-12)
        assert pt["efl"] == INF and pt["bfl"] == INF and math.isfinite(pt["xp_radius"])
        r = LS.lens_afocal_report(tele, fields=[0.0, 1.0, 2.5])
        assert max(f["rms_arcmin"] for f in r["fields"]) < 1e-9                 # zero angular aberration
        assert r["beam_compression"] == pytest.approx(abs(M), rel=1e-12)
        assert len(r["fields"]) == 3
        for f in r["fields"][1:]:                                              # tan(theta') = M tan(theta) exactly
            th = math.tan(math.radians(f["field"]))
            assert math.tan(math.radians(f["chief_arcmin"][1] / 60.0)) == pytest.approx(M * th, rel=1e-12)


def test_afocal_opd_is_measured_against_a_plane_wave():
    # a plane-parallel plate is afocal and keeps a plane wave plane: the OPD is zero at every field (closed form)
    plate = RT.lens_system([{"R": INF, "t": 10.0, "n": (N1, V1), "ap": 5.0}, {"R": INF, "t": 5.0, "n": 1.0}], stop=0,
                           afocal=True)
    for f in (0.0, 8.0):
        px, py, w, ok = RT.opd_samples(plate, field=f, size=9)
        assert ok.sum() > 40 and np.max(np.abs(w[ok])) < 1e-7
    # a lens that is not a plate breaks the plane wave: a real telescope has a wavefront error
    px, py, w, ok = RT.opd_samples(two_doublet_telescope(), field=0.0, size=9)
    assert ok.sum() > 40 and np.max(np.abs(w[ok])) > 1e-3
    assert np.isfinite(LS.lens_afocal_report(two_doublet_telescope(), fields=[0.0])["fields"][0]["wavefront_rms_waves"])


def two_doublet_telescope(ap=10.0):
    """A real afocal telescope: two cemented doublets (model glasses), the last curvature set by a 0-degree solve."""
    g1, g2 = (N1, V1), (N2, V2)
    return RT.lens_system([
        {"R": 62.0, "t": 4.0, "n": g1, "ap": ap}, {"R": -45.0, "t": 2.0, "n": g2}, {"R": -170.0, "t": 123.0, "n": 1.0},
        {"R": 24.0, "t": 5.0, "n": g1, "ap": ap / 4.0 * 1.4}, {"R": -17.0, "t": 2.0, "n": g2},
        {"R": -50.0, "t": 6.0, "n": 1.0, "solve": {"kind": "marginal_ray_angle", "angle_deg": 0.0}}],
        stop=0, afocal=True)


def test_a_real_two_doublet_telescope_reports_its_angular_spot_in_arcminutes():
    tele = two_doublet_telescope()
    pt = RT.paraxial_trace(tele)
    assert pt["efl"] == INF and pt["angular_magnification"] < -3.0
    r = LS.lens_afocal_report(tele, fields=[0.0, 0.5, 1.0])
    rms = [f["rms_arcmin"] for f in r["fields"]]
    assert all(0.0 < x < 60.0 for x in rms) and rms[2] > rms[0]                # real glass: a real, field-growing blur
    assert r["unit"] == "arcmin"
    # the same rays measured in millimetres on a plane 100 mm behind: angles times distance, the long way round
    b = RT.ray_bundle(tele, field=1.0, rings=4)
    assert b["image_xy"].shape[1] == 2 and np.isfinite(b["chief_xy"]).all()


def test_afocal_flag_is_checked_and_needs_an_object_at_infinity():
    focusing = RT.lens_system([{"R": 50.0, "t": 30.0, "n": 1.5, "ap": 5.0}, {"R": INF, "t": 10.0, "n": 1.0}], stop=0,
                              afocal=True)
    with pytest.raises(ValueError, match="flagged afocal"):
        RT.paraxial_trace(focusing)
    with pytest.raises(ValueError, match="object at infinity"):
        RT.lens_system([{"R": 50.0, "t": 30.0, "n": 1.5, "ap": 5.0}, {"R": INF, "t": 10.0, "n": 1.0}], stop=0,
                       afocal=True, object_mm=100.0)
    with pytest.raises(ValueError, match="flagged afocal"):
        LS.afocal_system(RT.lens_system([{"R": 50.0, "t": 30.0, "n": 1.5, "ap": 5.0}, {"R": INF, "t": 10.0, "n": 1.0}],
                                         stop=0))
    with pytest.raises(ValueError, match="not afocal"):
        LS.lens_afocal_report(RT.lens_system())
    flagged = LS.afocal_system(RT.lens_system([{"f": 80.0, "t": 100.0, "ap": 4.0}, {"f": 20.0, "t": 5.0}], stop=0))
    assert RT.paraxial_trace(flagged)["angular_magnification"] == pytest.approx(-4.0, abs=1e-12)


def test_afocal_operands_in_the_merit_function():
    tele = LS.afocal_system(f1=100.0, f2=25.0)
    t = LM.merit_evaluate(tele, [{"op": "ANGM", "target": -4.0}, {"op": "RSAN", "target": 0.0, "field": 0}],
                          fields=[0.0, 1.0])["table"]
    assert t[0]["value"] == pytest.approx(-4.0, abs=1e-12) and t[1]["value"] < 1e-9
    with pytest.raises(ValueError, match="needs an afocal system"):
        LM.merit_evaluate(RT.lens_system(), [{"op": "ANGM", "target": -4.0}])
    names = LM.merit_operands_list()["names"]
    assert "ANGM" in names and "RSAN" in names


# --------------------------------------------------------------------------- #
# 7. curved image surface
# --------------------------------------------------------------------------- #
def landscape_lens(ap=0.5):
    """A thin positive meniscus (concave to the object, f = 99.8 mm) with the stop 16.04 mm in front, placed where the
    Seidel astigmatism S_III is zero (found here by bisection): the only field aberration left is the Petzval curvature."""
    R1, R2, t = -100.0, -34.071729957805914, 0.3

    def build(d, a_):
        return RT.lens_system([{"R": INF, "t": d, "n": 1.0, "ap": a_}, {"R": R1, "t": t, "n": (N1, V1), "ap": 14.0},
                               {"R": R2, "t": None, "n": 1.0, "ap": 14.0}], stop=0, field=10.0)
    lo, hi = 10.0, 20.0

    def f(d):
        return RT.seidel_coefficients(build(d, 1.0), field=10.0)["total"]["S_III"]
    assert f(lo) * f(hi) < 0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if f(lo) * f(mid) > 0 else (lo, mid)
    return build(0.5 * (lo + hi), ap)


def test_petzval_radius_of_a_thin_lens_and_the_curved_image_removes_the_field_curvature():
    thin = RT.lens_system([{"R": 100.0, "t": 0.0, "n": 1.5, "ap": 2.0}, {"R": -100.0, "t": None, "n": 1.0}], stop=0)
    f = 1.0 / (0.5 * (2.0 / 100.0))
    assert LS.lens_petzval_radius(thin)["radius"] == pytest.approx(-1.5 * f, rel=1e-12)    # -N f
    lens = landscape_lens()
    assert abs(RT.seidel_coefficients(lens, field=10.0)["total"]["S_III"]) < 1e-9
    # the Seidel module's own Petzval radius is the same number
    assert LS.lens_petzval_radius(lens)["radius"] == pytest.approx(RT.seidel_coefficients(lens, field=10.0)["petzval_radius"],
                                                                   rel=1e-12)
    flat = lens
    curved = LS.lens_image_surface(lens, R="petzval")
    assert curved["image_R"] == pytest.approx(LS.lens_petzval_radius(lens)["radius"], rel=1e-14)
    # the paraxial image does not depend on the image surface
    a, b = RT.paraxial_trace(flat), RT.paraxial_trace(curved)
    for k in ("efl", "bfl", "image_mm", "ep_radius", "xp_position", "lagrange"):
        assert a[k] == pytest.approx(b[k], rel=1e-9, abs=1e-9)
    # field curvature term: the part of the RMS that a refocus along the chief ray would remove; the floor is the best plane
    bfl = a["bfl"]
    f7 = 7.0
    flat_rms = RT.spot_stats(flat, field=f7, rings=8)["rms_radius"]
    cur_rms = RT.spot_stats(curved, field=f7, rings=8)["rms_radius"]
    floor = min(RT.spot_stats(flat, field=f7, rings=8, image_mm=bfl + d)["rms_radius"] for d in np.linspace(-4.0, 1.0, 101))
    term_flat = math.sqrt(max(flat_rms ** 2 - floor ** 2, 0.0))
    term_cur = math.sqrt(max(cur_rms ** 2 - floor ** 2, 0.0))
    assert flat_rms > 5.0 * floor and term_flat > 1e-3                        # on the flat plane the curvature dominates
    assert cur_rms < 0.2 * flat_rms and term_cur < 0.1 * term_flat           # the curved image takes most of it away
    # on axis the two agree (the surface is tangent to the plane at the vertex)
    assert RT.spot_stats(curved, field=0.0)["rms_radius"] == pytest.approx(RT.spot_stats(flat, field=0.0)["rms_radius"],
                                                                           rel=1e-3)


def test_rays_land_on_the_image_surface_equation_and_a_flat_one_is_unchanged():
    lens = landscape_lens(ap=2.0)
    for R, k in ((-120.0, 0.0), (80.0, -0.5), (-60.0, 0.7)):
        cur = LS.lens_image_surface(lens, R=R, k=k)
        b = RT.ray_bundle(cur, field=8.0, rings=5)
        pts = b["points"][b["valid"]][:, -1, :]
        zi = b["z_image_global"]
        r2 = pts[:, 0] ** 2 + pts[:, 1] ** 2
        c = 1.0 / R
        sag = c * r2 / (1.0 + np.sqrt(1.0 - (1.0 + k) * c * c * r2))
        assert np.max(np.abs((pts[:, 2] - zi) - sag)) < 1e-11
    flat = LS.lens_image_surface(LS.lens_image_surface(lens, R=-90.0), R=INF)
    assert "image_R" not in flat
    a, b = RT.trace_rays(lens, np.array([[0.0, 1.0, -5.0]]), np.array([[0.0, 0.1, 1.0]])), \
        RT.trace_rays(flat, np.array([[0.0, 1.0, -5.0]]), np.array([[0.0, 0.1, 1.0]]))
    assert np.array_equal(a["points"], b["points"])
    with pytest.raises(ValueError, match="conic constant is meaningless"):
        LS.lens_image_surface(lens, R=INF, k=-1.0)
    with pytest.raises(ValueError, match="radius or 'petzval'"):
        LS.lens_image_surface(lens, R="flat")


def test_other_modules_keep_the_image_surface_and_the_non_coaxial_tracer_refuses_it():
    lens = LS.lens_image_surface(landscape_lens(), R=-100.0)
    assert RT.with_wavelength(lens, RT.WL_F)["image_R"] == -100.0
    import raytrace3d as R3
    with pytest.raises(ValueError, match="curved image surface"):
        R3.noncoaxial_system(lens)


# --------------------------------------------------------------------------- #
# 8. odd asphere and the r^2 term
# --------------------------------------------------------------------------- #
def conic_sag(r, c, k):
    return c * r * r / (1.0 + np.sqrt(1.0 - (1.0 + k) * c * c * r * r))


def test_odd_asphere_sag_is_the_polynomial_at_ten_heights():
    c, k = 1.0 / 40.0, -0.3
    a2, odd, asph = 2e-4, (1e-4, -3e-5, 2e-6, 0.0, -1e-9), (4e-7, -2e-10)
    h = np.linspace(0.5, 9.5, 10)
    want = conic_sag(h, c, k) + a2 * h ** 2 + sum(b * h ** (i + 1) for i, b in enumerate(odd)) \
        + sum(a * h ** (2 * i + 4) for i, a in enumerate(asph))
    got = RT._sag(h * h, c, k, asph, (a2, odd))
    assert np.max(np.abs(got - want)) < 1e-12
    # the slope used for the normal: d z / d (r^2) by a central difference
    eps = 1e-6
    num = (RT._sag((h + eps) ** 2, c, k, asph, (a2, odd)) - RT._sag((h - eps) ** 2, c, k, asph, (a2, odd))) \
        / ((h + eps) ** 2 - (h - eps) ** 2)
    assert np.max(np.abs(RT._dsag_dr2(h * h, c, k, asph, (a2, odd)) - num)) < 1e-8


def test_odd_asphere_ray_intersection_satisfies_the_surface_equation():
    c, k, a2, odd = 1.0 / 40.0, -0.3, 2e-4, (1e-4, -3e-5, 2e-6)
    rng = np.random.default_rng(5)
    P = np.column_stack([rng.uniform(-6, 6, 40), rng.uniform(-6, 6, 40), np.full(40, -3.0)])
    D = np.column_stack([rng.uniform(-0.1, 0.1, 40), rng.uniform(-0.1, 0.1, 40), np.ones(40)])
    D /= np.linalg.norm(D, axis=1, keepdims=True)
    t = RT._intersect_surface(P, D, c, k, (), (a2, odd))
    Q = P + t[:, None] * D
    r = np.hypot(Q[:, 0], Q[:, 1])
    resid = Q[:, 2] - (conic_sag(r, c, k) + a2 * r ** 2 + sum(b * r ** (i + 1) for i, b in enumerate(odd)))
    assert np.isfinite(t).all() and np.max(np.abs(resid)) < 1e-10


def test_zero_odd_coefficients_are_bit_identical_to_the_even_asphere():
    base = [{"R": 40.0, "t": 4.0, "n": 1.5, "ap": 8.0, "k": -0.3, "asph": (1e-7, -2e-10)},
            {"R": -90.0, "t": None, "n": 1.0}]
    zero = [dict(base[0], odd=(0.0, 0.0), a2=0.0), base[1]]
    a, b = RT.lens_system(base, stop=0), RT.lens_system(zero, stop=0)
    assert "odd" not in b["surfaces"][0] and "a2" not in b["surfaces"][0]
    ta = RT.ray_bundle(a, field=3.0, rings=6)
    tb = RT.ray_bundle(b, field=3.0, rings=6)
    assert np.array_equal(ta["points"], tb["points"], equal_nan=True) and np.array_equal(ta["opl"], tb["opl"], equal_nan=True)


def test_an_odd_term_changes_the_trace_and_a2_matches_a_curvature_change():
    s0 = RT.lens_system([{"R": 40.0, "t": 4.0, "n": 1.5, "ap": 6.0}, {"R": INF, "t": 50.0, "n": 1.0}], stop=0)
    s1 = RT.lens_system([{"R": 40.0, "t": 4.0, "n": 1.5, "ap": 6.0, "odd": (3e-5,)}, {"R": INF, "t": 50.0, "n": 1.0}],
                        stop=0)
    assert RT.spot_stats(s1, field=0.0)["rms_radius"] != RT.spot_stats(s0, field=0.0)["rms_radius"]
    # a2 = delta_c / 2 is the same sag as a curvature change to first order: compare the paraxial power
    dc = 1e-4
    sa = RT.lens_system([{"R": 40.0, "t": 4.0, "n": 1.5, "ap": 6.0, "a2": dc / 2.0}, {"R": INF, "t": 50.0, "n": 1.0}], stop=0)
    sc = RT.lens_system([{"R": 1.0 / (1.0 / 40.0 + dc), "t": 4.0, "n": 1.5, "ap": 6.0}, {"R": INF, "t": 50.0, "n": 1.0}],
                        stop=0)
    pa = RT.spot_stats(sa, field=0.0, image_mm=50.0)
    pc = RT.spot_stats(sc, field=0.0, image_mm=50.0)
    assert pa["rms_radius"] == pytest.approx(pc["rms_radius"], rel=2e-2)


def test_the_r2_terms_are_paraxial_power_and_solves_see_them():
    base = [{"R": 40.0, "t": 4.0, "n": 1.5, "ap": 6.0}, {"R": INF, "t": 50.0, "n": 1.0}]
    a2 = 3e-4
    with_a2 = RT.lens_system([dict(base[0], a2=a2), base[1]], stop=0)
    as_c = RT.lens_system([dict(base[0], R=1.0 / (1.0 / 40.0 + 2.0 * a2)), base[1]], stop=0)
    for key in ("efl", "bfl", "ep_radius", "image_mm"):
        assert RT.paraxial_trace(with_a2)[key] == pytest.approx(RT.paraxial_trace(as_c)[key], rel=1e-13)
    b2 = RT.lens_system([dict(base[0], odd=(5e-4, a2)), base[1]], stop=0)          # B1 is a cone (no power), B2 = a2
    assert RT.paraxial_trace(b2)["efl"] == pytest.approx(RT.paraxial_trace(as_c)["efl"], rel=1e-13)
    with pytest.raises(ValueError, match="third-order sums"):
        RT.seidel_coefficients(with_a2)
    # a curvature solve sets the base curvature so that the *paraxial* quantity is met
    s = RT.lens_system([{"R": 80.0, "t": 4.0, "n": 1.5, "ap": 5.0, "a2": 2e-4,
                         "solve": {"kind": "marginal_ray_angle", "angle_deg": -2.0}}, {"R": INF, "t": 30.0, "n": 1.0}], stop=0)
    c_par = -1.5 * math.tan(math.radians(-2.0)) / (5.0 * 0.5)
    assert 1.0 / s["surfaces"][0]["R"] + 2.0 * 2e-4 == pytest.approx(c_par, rel=1e-12)
    assert abs(LS.lens_solves_list(s)["solves"][0]["error"]) < 1e-12
    f = RT.lens_system([{"R": 60.0, "t": 3.0, "n": 1.5, "ap": 5.0, "a2": 1e-4}, {"R": -60.0, "t": 40.0, "n": 1.0}], stop=0)
    sv = LS.lens_solve_set(f, 1, "f_number", fno=4.0)
    assert RT.paraxial_trace(sv)["fno"] == pytest.approx(4.0, rel=1e-9)


# --------------------------------------------------------------------------- #
# 9. the .zmx files
# --------------------------------------------------------------------------- #
def _tables():
    out = {}
    for f in sorted(glob.glob(os.path.join(DATA, "*.zmx"))):
        name = os.path.basename(f)
        p = LF.lens_file_read(f, allow_partial=True)
        s = p["system"]
        if p.get("noncoaxial"):
            el = [{k: (repr(v) if not isinstance(v, (int, float, str, bool, type(None), list, tuple)) else v)
                   for k, v in e.items()} for e in s["elements"]]
            out[name] = {"noncoaxial": True, "elements": json.loads(json.dumps(el, default=repr))}
        else:
            rows = [{k: x[k] for k in ("R", "t", "k", "ap", "mirror", "asph", "decenter", "tilt")} | {"n_value": x["n_value"]}
                    for x in s["surfaces"]]
            out[name] = {"noncoaxial": False, "rows": json.loads(json.dumps(rows, default=repr)), "stop": s["stop"],
                         "object_mm": repr(s["object_mm"]), "wavelength_um": s["wavelength_um"],
                         "fields": [f_["field"] for f_ in p["fields"]], "n_solves": len(p["solves"])}
    ex = LF.lens_file_read(None)
    out["ZMX_EXAMPLE"] = {"rows": [{k: x[k] for k in ("R", "t", "k", "ap", "mirror", "asph")} for x in ex["system"]["surfaces"]]}
    return json.loads(json.dumps(out, sort_keys=True))


def test_every_test_file_reads_to_the_same_surface_table_as_before_this_slice():
    before = json.load(open(os.path.join(DATA, "surface_tables_before_slice7.json"), encoding="utf-8"))
    now = _tables()
    assert len(before) == 10
    assert sorted(before) == sorted(now)
    for k in before:
        assert now[k] == before[k], k


def rich_system():
    """Three kinds of solve that have a line in the format (curvature pickup with scale -1, thickness pickup,
    aspheric-parameter pickup) plus three that have none (paraxial image, F/#, a ray-angle solve)."""
    return RT.lens_system([
        {"R": 62.0, "t": 4.0, "n": (N1, V1), "ap": 9.0, "asph": (1e-7, -2e-11), "a2": 2e-4},
        {"R": -45.0, "t": 2.0, "n": (N2, V2)},
        {"R": -130.0, "t": 6.0, "n": 1.0, "solve": {"kind": "marginal_ray_angle", "angle_deg": -3.0}},
        {"R": 99.0, "t": 3.0, "n": (N1, V1), "asph": (0.0,), "solve": {"kind": "pickup", "source": 0, "quantity": "A4",
                                                                       "scale": -1.0}},
        {"R": 99.0, "t": 9.0, "n": 1.0, "solve": {"kind": "pickup", "source": 2, "quantity": "c", "scale": -1.0}},
        {"R": 70.0, "t": 5.0, "n": (N2, V2), "solve": {"kind": "pickup", "source": 3, "quantity": "t",
                                                       "scale": 2.0, "offset": 0.25}},
        {"R": -80.0, "t": 1.0, "n": 1.0, "solve": {"kind": "f_number", "fno": 7.5, "c0": -0.0125}},
        {"R": INF, "t": 1.0, "n": 1.0, "solve": {"kind": "paraxial_image"}}], stop=0)


def test_zmx_round_trip_of_three_kinds_of_pickup_and_the_rest_is_a_fixed_point():
    s = rich_system()
    r = LS.lens_zmx_solves_roundtrip(s)
    assert r["fixed_point"] is True and r["max_diff"] < 1e-12 and r["rules_equal"] is True
    assert r["dropped_solves"] == []                                           # nothing is frozen any more
    assert r["native"] == [3, 4, 5] and r["as_note"] == [2, 6, 7]
    text = r["text"]
    assert "CURV -0.0" in text and " 4 3 -1 0" in text                         # CURV c 4 source scale offset (file numbers)
    assert "PZUP 4 2 0.25 0" in text and "PPAR 2 1 -1 0 0" in text            # thickness pickup, A4 = PARM 2 pickup
    assert text.count("NOTE 0 FULLSEYE-SOLVE") == 3
    # the geometry of the twice-read system is the resolved one
    p = LF.lens_file_read(text)
    assert len(p["system"]["surfaces"]) == 8
    for a, b in zip(LS.lens_apply_solves(s)["surfaces"], p["system"]["surfaces"]):
        assert b["R"] == pytest.approx(a["R"], rel=1e-12) and b["t"] == pytest.approx(a["t"], rel=1e-12, abs=1e-12)
        assert b.get("solve") == a.get("solve")
    # and an edit of the source moves what was picked up, on the system read back
    surf = [dict(x) for x in p["system"]["surfaces"]]
    surf[0]["asph"] = (3e-7, -2e-11)
    edited = RT.lens_system(surf, stop=p["system"]["stop"], object_mm=p["system"]["object_mm"],
                            wavelength_um=p["system"]["wavelength_um"], index_object=p["system"]["index_object"])
    assert edited["surfaces"][3]["asph"] == (-3e-7,)


def test_zmx_default_round_trip_and_stale_or_foreign_notes_are_refused():
    r = LS.lens_zmx_solves_roundtrip()
    assert r["fixed_point"] and r["rules_equal"] and r["max_diff"] < 1e-12
    text = r["text"]
    # a stored number that disagrees with its note: the image surface's DISZ is 0, the last lens surface's comes before it
    lines = text.splitlines()
    k = [i for i, ln in enumerate(lines) if ln.startswith("  DISZ")][-2]
    lines[k] = "  DISZ 999"
    with pytest.raises(ValueError, match="stale or corrupted"):
        LF.lens_file_read("\n".join(lines) + "\n")
    with pytest.raises(ValueError, match="unknown Fullseye marker"):
        LF.lens_file_read(text.replace("NOTE 0 FULLSEYE-SOLVE", "NOTE 0 FULLSEYE-WHATEVER", 1))
    with pytest.raises(ValueError, match="not valid"):
        LF.lens_file_read(text.replace('"kind":"paraxial_image"', '"kind":', 1))


def test_curved_image_odd_asphere_r2_and_afocal_marker_round_trip_through_zmx():
    s = RT.lens_system([{"R": 40.0, "t": 4.0, "n": (N1, V1), "ap": 6.0, "odd": (1e-4, 0.0, -2e-6), "a2": 3e-4,
                         "asph": (1e-7,)},
                        {"R": INF, "t": 60.0, "n": 1.0}], stop=0, image_R=-80.0, image_k=-0.5, field=3.0)
    w = LF.lens_file_write(LF._prescription_from_system(s), system=s)["text"]
    assert "TYPE ODDASPH" in w and "PARM 1 0.0001" in w and "PARM 2 0.0003" in w and "PARM 4 1e-07" in w
    assert "CONI -0.5" in w
    p = LF.lens_file_read(w)
    q = p["system"]
    assert q["image_R"] == pytest.approx(-80.0, rel=1e-12) and q["image_k"] == -0.5
    b = q["surfaces"][0]
    # the even terms are folded into the odd asphere's own parameters on writing: the sag is the same
    h = np.linspace(0.5, 5.5, 6)
    want = RT._sag(h * h, 1.0 / 40.0, 0.0, (1e-7,), (3e-4, (1e-4, 0.0, -2e-6)))
    got = RT._sag(h * h, 1.0 / b["R"], b["k"], b.get("asph", ()), RT._xtra(b))
    assert np.max(np.abs(want - got)) < 1e-12
    assert LF.lens_file_write(p)["text"].count("TYPE ODDASPH") == 1
    # even asphere with an r^2 term
    e = RT.lens_system([{"R": 40.0, "t": 4.0, "n": (N1, V1), "ap": 6.0, "a2": 3e-4, "asph": (1e-7,)},
                        {"R": INF, "t": 60.0, "n": 1.0}], stop=0)
    we = LF.lens_file_write(LF._prescription_from_system(e), system=e)["text"]
    assert "TYPE EVENASPH" in we and "PARM 1 0.0003" in we
    assert LF.lens_file_read(we)["system"]["surfaces"][0]["a2"] == 3e-4
    # the afocal marker
    tele = two_doublet_telescope()
    wt = LF.lens_file_write(LF._prescription_from_system(tele), system=tele)["text"]
    assert "NOTE 0 FULLSEYE-AFOCAL 1" in wt and "FULLSEYE-SOLVE" in wt           # the last curvature is a 0-degree solve
    pt = LF.lens_file_read(wt)
    assert pt["system"].get("afocal") is True and "FULLSEYE" not in " ".join(pt["notes"])
    assert RT.paraxial_trace(pt["system"])["angular_magnification"] == pytest.approx(
        RT.paraxial_trace(tele)["angular_magnification"], rel=1e-12)
    assert LF.lens_file_write(pt)["text"].count("FULLSEYE-AFOCAL") == 1
    wo = wt.replace("NOTE 0 FULLSEYE-AFOCAL 1", "NOTE 0 FULLSEYE-AFOCAL 0")
    with pytest.raises(ValueError, match="afocal marker"):
        LF.lens_file_read(wo)


def test_unevidenced_solve_forms_stay_frozen_and_are_listed():
    t = LF.ZMX_EXAMPLE.replace("  CURV 0.012549633801685667 0 0 0 0 \"\"\n  DISZ 2.95208",
                               "  CURV 0.012549633801685667 2 0.5 0 0 \"\"\n  DISZ 2.95208")
    p = LF.lens_file_read(t)
    assert [x for x in p["solves"] if x["surface"] == 5][0]["kind"] == "solve type 2"
    assert "solve" not in p["system"]["surfaces"][4]
    assert LF.lens_file_write(p)["dropped_solves"] == []
    assert "CURV 0.012549633801685667 2 0.5 0 0" in LF.lens_file_write(p)["text"]


def test_a_curvature_pickup_with_a_mirror_or_coordinate_break_is_kept_as_verified_values_only():
    t = LF.ZMX_EXAMPLE.replace("  CURV 0.012549633801685667 0 0 0 0 \"\"\n  DISZ 2.95208",
                               "  CURV 0.045426484276303865 4 1 1 0 \"\"\n  DISZ 2.95208")
    p = LF.lens_file_read(t)
    assert p["system"]["surfaces"][4]["solve"]["kind"] == "pickup"
    cb = LF.lens_file_read(os.path.join(DATA, "cb_tilted_plate.zmx"))
    assert cb["noncoaxial"] is True
