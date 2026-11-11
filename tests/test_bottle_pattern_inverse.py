# -*- coding: utf-8 -*-
"""Gates for ``bottle_background_map`` and ``bottle_fit_from_pattern`` (a bottle read back from the distortion of a background pattern).

The forward map is a vector-Snell ray trace (``bottle_background_map``); the model inside the fit is a closed form on concentric
circles written with angles and impact parameters (no ray-circle intersections), and the test adds a third derivation (a paraxial
2 x 2 ray matrix) for the centre slope. A truth that two derivations share is not scored against itself: the fit is given maps
made by the tracer. Each guarantee has a probe that breaks the answer on purpose and must be caught.
"""
import numpy as np
import pytest

import watervision as V

R_B, T_B, NG, DC, DB = 30.0, 1.5, 1.52, 500.0, 150.0


def _map(fill, nl, rows=40, t=T_B, ng=NG, R=R_B, pitch_um=50.0, db=DB, dc=DC):
    p = pitch_um / 1000.0
    return V.bottle_background_map(R, t, rows * p, fill, ng, nl, db, dc, pitch_um, size=(rows, int(np.ceil(2.3 * R / p))))


def _fit(m, pitch_um=50.0, **kw):
    return V.bottle_fit_from_pattern(m["u_mm"], m["x_mm"], pitch_um, m["camera_distance_mm"], m["background_distance_mm"], **kw)


def _paraxial_slope(nl, t, ng, R, dc, db):
    """d u / d x at the axis from the 2 x 2 ray matrices (y, n * slope): written here, independent of the module."""
    Ri = R - t

    def T(d, n):
        return np.array([[1.0, d / n], [0.0, 1.0]])

    def S(n1, n2, r):
        return np.array([[1.0, 0.0], [-(n2 - n1) / r, 1.0]])
    M = (T(db - R, 1.0) @ S(ng, 1.0, -R) @ T(t, ng) @ S(nl, ng, -Ri) @ T(2.0 * Ri, nl) @ S(ng, nl, Ri) @ T(t, ng)
         @ S(1.0, ng, R) @ T(dc - R, 1.0))
    return M[0, 1] / dc


# ---------------------------------------------------------------- 1. the map: two derivations and a third
@pytest.mark.parametrize("nc", [1.0, 1.333, 1.47])
@pytest.mark.parametrize("R,t,ng", [(30.0, 1.5, 1.52), (22.0, 3.0, 1.45), (30.0, 0.3, 1.6)])
def test_tracer_and_closed_form_agree_on_every_pixel(nc, R, t, ng):
    row = 0 if nc == 1.0 else -1                                  # the empty rows are the top ones
    m = _map(0.5, max(nc, 1.333), t=t, ng=ng, R=R)
    x = m["x_mm"]
    u_cf, ok_cf = V._section_u(x, R, R - t, ng, nc, DC, DB)
    both = ok_cf & m["valid"][row]
    assert int(both.sum()) > 0.5 * x.size
    assert float(np.abs(u_cf[both] - m["u_mm"][row][both]).max()) < 1e-7                  # the tracer steps 1e-6 mm past each interface
    assert np.array_equal(ok_cf, m["valid"][row])                # the same pixels are dropped (total internal reflection)


@pytest.mark.parametrize("nl", [1.333, 1.47])
def test_centre_slope_matches_the_paraxial_matrix(nl):
    m = _map(0.5, nl)
    c = np.abs(m["x_mm"]) < 0.2
    slope_full = np.polyfit(m["x_mm"][c], m["u_mm"][-1][c], 1)[0]
    slope_empty = np.polyfit(m["x_mm"][c], m["u_mm"][0][c], 1)[0]
    assert abs(slope_full / _paraxial_slope(nl, T_B, NG, R_B, DC, DB) - 1.0) < 1e-4
    assert abs(slope_empty / _paraxial_slope(1.0, T_B, NG, R_B, DC, DB) - 1.0) < 1e-4
    # the lens changes the slope a lot: an unrelated number would not pass
    assert abs(slope_full / (1.0 + DB / DC) - 1.0) > 0.5


def test_outside_the_bottle_the_map_is_the_pinhole_line_and_rows_repeat_bit_for_bit():
    m = _map(0.5, 1.333)
    x = m["x_mm"]
    out = np.abs(x) > R_B * 1.05
    assert int(out.sum()) > 20
    assert float(np.abs(m["u_mm"][0][out] - x[out] * (DC + DB) / DC).max()) < 1e-11
    assert np.array_equal(m["u_mm"][0], m["u_mm"][5], equal_nan=True)
    assert np.array_equal(m["u_mm"][-1], m["u_mm"][-6], equal_nan=True)
    assert m["fill_row_from_top"] == 20 and m["liquid_rows"] == 20 and abs(m["fill_z_mm"] - 1.0) < 1e-12


def test_total_internal_reflection_pixels_are_nan_and_counted_not_guessed():
    m = _map(0.5, 1.333)
    empty = m["valid"][0]
    full = m["valid"][-1]
    assert not empty.all() and full.all()                         # only the air core meets it
    assert m["tir_rays"] == int((~empty).sum()) * 20              # 20 empty rows
    assert bool(np.isnan(m["u_mm"][0][~empty]).all()) and np.isfinite(m["u_mm"][-1]).all()
    assert m["unresolved_rays"] == 0 and m["backward_rays"] == 0
    assert float(m["weight"].min()) >= 0.0 and float(m["weight"].max()) <= 1.0
    assert float(m["weight"][-1][np.abs(m["x_mm"]) < 0.1].max()) < 1.0   # four interfaces lose light at the axis too


# ---------------------------------------------------------------- 2. the fit
@pytest.mark.parametrize("nl", [1.333, 1.47])
@pytest.mark.parametrize("fill", [0.25, 0.75])
def test_noise_free_fit_recovers_every_quantity_and_the_fill_line(nl, fill):
    m = _map(fill, nl)
    r = _fit(m)
    assert r["converged"] and r["fill_state"] == "partial" and r["level_found"]
    assert abs(r["radius_mm"] / R_B - 1.0) < 1e-6 and abs(r["wall_mm"] / T_B - 1.0) < 1e-6
    assert abs(r["n_glass"] / NG - 1.0) < 1e-6 and abs(r["n_liquid"] / nl - 1.0) < 1e-6
    assert abs(r["level_mm"] - m["fill_z_mm"]) <= 0.05 + 1e-9 and r["level_row"] == m["fill_row_from_top"]
    assert r["residual_rms_mm"] < 1e-8
    assert r["separated"] and r["poorly_determined"] == []


def test_empty_and_full_bottles_have_no_fill_line():
    me = _map(0.0, 1.333)
    re = _fit(me)
    assert (not re["level_found"]) and re["level_mm"] is None and re["fill_state"] == "uniform" and re["level_row"] == -1
    assert abs(re["n_liquid"] - 1.0) < 1e-6 and abs(re["wall_mm"] / T_B - 1.0) < 1e-6
    mf = _map(1.0, 1.333)
    rf = _fit(mf)
    assert (not rf["level_found"]) and abs(rf["n_liquid"] / 1.333 - 1.0) < 1e-6


def test_known_values_are_held_and_the_rest_is_still_fitted():
    m = _map(0.5, 1.333)
    r = _fit(m, known={"n_glass": NG})
    assert r["n_glass"] == NG and "n_glass" not in r["free"] and r["sigma"]["n_glass"] is None
    assert abs(r["wall_mm"] / T_B - 1.0) < 1e-6
    r2 = _fit(m, known={"wall_mm": T_B, "n_glass": NG, "radius_mm": R_B})
    assert r2["free"] == ["n_liquid"] and abs(r2["n_liquid"] / 1.333 - 1.0) < 1e-6


def test_the_covariance_says_wall_and_glass_index_trade_off_and_cond_is_reported():
    m = _map(0.5, 1.333)
    r = _fit(m)
    names = r["corr_names"]
    c = np.array(r["corr"])
    assert names == ["radius_mm", "wall_mm", "n_glass", "n_liquid"]
    assert np.allclose(c, c.T) and np.allclose(np.diag(c), 1.0)
    assert c[names.index("wall_mm"), names.index("n_glass")] < -0.8
    assert 2.0 < r["cond"] < 1e4 and len(r["singular_values"]) == 4
    assert abs(sum(v * v for v in r["weak_direction"].values()) - 1.0) < 1e-9


def test_the_background_distance_trades_off_with_the_liquid_index_when_it_is_free():
    m = _map(0.5, 1.333)
    rng = np.random.default_rng(3)
    noisy = m["u_mm"] + rng.normal(0.0, 0.004, m["u_mm"].shape)
    r = V.bottle_fit_from_pattern(noisy, m["x_mm"], 50.0, DC, DB, free_background=True)
    names = r["corr_names"]
    c = np.array(r["corr"])[names.index("n_liquid"), names.index("background_distance_mm")]
    assert c < -0.99                                              # the two are nearly one parameter
    assert abs(r["background_distance_mm"] - DB) < 1.0
    known = V.bottle_fit_from_pattern(noisy, m["x_mm"], 50.0, DC, DB)
    assert r["cond"] > 5 * known["cond"]


def test_a_thin_wall_seen_only_through_the_middle_is_not_called_separated():
    """The edge pixels (steep rays) separate wall from glass index; with only the middle left the fit must say it does not know."""
    m = _map(0.5, 1.333, t=0.1)
    x = m["x_mm"]
    rng = np.random.default_rng(1)
    u = m["u_mm"] + rng.normal(0.0, 0.006, m["u_mm"].shape)
    u = np.where(np.abs(x)[None, :] <= 0.25 * R_B, u, np.nan)
    r = _fit({"u_mm": u, "x_mm": x, "camera_distance_mm": DC, "background_distance_mm": DB}, rows_per_section=1)
    assert (not r["separated"]) and ("wall_mm" in r["poorly_determined"] or "n_glass" in r["poorly_determined"] or not r["converged"])
    assert r["sigma"]["wall_mm"] > 0.25 * abs(r["wall_mm"]) or not r["converged"]
    wide = _fit({"u_mm": m["u_mm"] + rng.normal(0.0, 0.006, m["u_mm"].shape), "x_mm": x, "camera_distance_mm": DC, "background_distance_mm": DB}, rows_per_section=1)
    assert wide["separated"] and abs(wide["wall_mm"] / 0.1 - 1.0) < 0.1


def test_calibration_errors_move_the_indices_far_more_than_noise_does():
    m = _map(0.5, 1.333)
    base = _fit(m)
    wrong_db = V.bottle_fit_from_pattern(m["u_mm"], m["x_mm"], 50.0, DC, DB + 1.0)
    assert abs(wrong_db["n_glass"] - base["n_glass"]) > 5e-3 and wrong_db["residual_rms_mm"] > 1e-4


# ---------------------------------------------------------------- 3. probes that break the answer on purpose
def test_probe_wrong_glass_index_or_radius_or_snell_direction_leaves_a_residual():
    m = _map(0.5, 1.333)
    floor = _fit(m)["residual_rms_mm"]
    assert _fit(m, known={"n_glass": 1.4})["residual_rms_mm"] > 1e-3 > floor
    assert _fit(m, known={"radius_mm": 28.0})["residual_rms_mm"] > 1e-3
    old = V._SNELL_ROTATION
    try:
        V._SNELL_ROTATION = -1.0
        flipped = _fit(m)["residual_rms_mm"]
    finally:
        V._SNELL_ROTATION = old
    assert flipped > 1e-2 > floor
    assert _fit(m)["residual_rms_mm"] == floor                   # restored


def test_a_fringe_measurement_with_noise_recovers_the_bottle():
    rng = np.random.default_rng(11)
    m = _map(0.5, 1.47)
    u = m["u_mm"] + rng.normal(0.0, 0.006, m["u_mm"].shape)
    r = _fit({"u_mm": u, "x_mm": m["x_mm"], "camera_distance_mm": DC, "background_distance_mm": DB})
    assert abs(r["radius_mm"] / R_B - 1.0) < 1e-3 and abs(r["n_liquid"] / 1.47 - 1.0) < 1e-3
    assert abs(r["level_mm"] - 1.0) <= 0.05 + 1e-9
    assert 0.0005 < r["residual_rms_mm"] < 0.006                  # the residual is of the order of the (row-averaged) noise put in


# ---------------------------------------------------------------- 4. refusals
_BAD_MAP = [
    dict(radius_mm=30, wall_mm=31, height_mm=80, fill_fraction=0.5, n_glass=1.52, n_liquid=1.333),
    dict(radius_mm=30, wall_mm=1.5, height_mm=80, fill_fraction=1.2, n_glass=1.52, n_liquid=1.333),
    dict(radius_mm=30, wall_mm=1.5, height_mm=80, fill_fraction=0.5, n_glass=1.0, n_liquid=1.333),
    dict(radius_mm=30, wall_mm=1.5, height_mm=80, fill_fraction=0.5, n_glass=1.52, n_liquid=0.9),
    dict(radius_mm=30, wall_mm=1.5, height_mm=80, fill_fraction=0.5, n_glass=1.52, n_liquid=1.333, background_distance_mm=20.0),
    dict(radius_mm=30, wall_mm=1.5, height_mm=80, fill_fraction=0.5, n_glass=1.52, n_liquid=1.333, camera_distance_mm=50.0),
    dict(radius_mm=30, wall_mm=1.5, height_mm=80, fill_fraction=0.5, n_glass=1.52, n_liquid=1.333, n_air=1.6),
    dict(radius_mm=30, wall_mm=1.5, height_mm=80, fill_fraction=0.5, n_glass=1.52, n_liquid=1.333, size=(0, 5)),
    dict(radius_mm=30, wall_mm=1.5, height_mm=80, fill_fraction=0.5, n_glass=1.52, n_liquid=1.333, pixel_pitch_um=0.0),
    dict(radius_mm=float("nan"), wall_mm=1.5, height_mm=80, fill_fraction=0.5, n_glass=1.52, n_liquid=1.333),
]


@pytest.mark.parametrize("kw", _BAD_MAP)
def test_map_refuses_what_it_cannot_trace(kw):
    with pytest.raises(ValueError):
        V.bottle_background_map(**kw)


def test_fit_refuses_empty_constant_straight_or_malformed_input():
    m = _map(0.5, 1.333)
    x = m["x_mm"]
    for bad in (np.full((40, x.size), 3.0), np.tile(x * (DC + DB) / DC, (40, 1)), np.full((40, x.size), np.nan), np.zeros((2, 3)), "map", None,
                np.full((40, x.size), np.inf)):
        with pytest.raises(ValueError):
            V.bottle_fit_from_pattern(bad, x, 50.0, DC, DB)
    for kw in (dict(known={"bogus": 1.0}), dict(known={"n_glass": -1.0}), dict(restarts=0), dict(restarts=4), dict(rows_per_section=0),
               dict(known={"radius_mm": 30.0, "wall_mm": 1.5, "n_glass": 1.52, "n_liquid": 1.333})):
        with pytest.raises(ValueError):
            V.bottle_fit_from_pattern(m["u_mm"], x, 50.0, DC, DB, **kw)
    with pytest.raises(ValueError):
        V.bottle_fit_from_pattern(m["u_mm"], x * 1.01, 50.0, DC, DB)       # x not spaced by the stated pitch
    with pytest.raises(ValueError):
        V.bottle_fit_from_pattern(m["u_mm"], x[:5], 50.0, DC, DB)
    with pytest.raises(ValueError):
        V.bottle_fit_from_pattern(m["u_mm"], x, 50.0, -1.0, DB)


def test_the_map_changes_nothing_in_bottle_image():
    """The tracer got an optional tracking output; the brightness op must be bit for bit what it was (rows equal the empty / full section)."""
    im = V.bottle_image(30.0, 1.5, 40.0, 0.5, 1.52, 1.333, pixel_pitch_um=250.0)
    assert im["image"].shape == (160, 276) and im["liquid_rows"] == 80
    assert np.array_equal(im["image"][0], im["image"][10]) and np.array_equal(im["image"][-1], im["image"][-10])
    assert float(im["image"].max()) <= 1.0 and abs(im["central_transmittance_filled"] - (1 - (0.52 / 2.52) ** 2) ** 2 * (1 - (0.187 / 2.853) ** 2) ** 2) < 1e-12


# ---------------------------------------------------------------- 5. the results that the review found missing
_MASTER_REF = {   # checksums of bottle_image on origin/master b1f3607750, taken before _trace_rows got its tracking output
    ("backlight", False): (96496.29299729946, 24126.24282372152),
    ("frontlight", False): (119978.2841083644, 29996.887324635012),
    ("backlight", True): (94804.2118015296, 23699.22027772741),
    ("frontlight", True): (120193.65758313793, 30049.370569378396),
}


@pytest.mark.parametrize("light", ["backlight", "frontlight"])
@pytest.mark.parametrize("extra", [False, True])
def test_bottle_image_is_unchanged_from_origin_master(light, extra):
    kw = {"meniscus_mm": 2.0, "bubbles": [(0, 10, 1.5)]} if extra else {}
    a = V.bottle_image(30, 1.5, 40, 0.5, 1.52, 1.333, pixel_pitch_um=250.0, light=light, **kw)["image"]
    w = np.arange(a.size).reshape(a.shape) % 7 + 1.0
    weighted, plain = _MASTER_REF[(light, extra)]
    assert abs(float((a * w).sum()) / weighted - 1.0) < 1e-9 and abs(float(a.sum()) / plain - 1.0) < 1e-9


def test_a_filled_section_with_no_row_left_gives_none_not_nan():
    """Two liquid rows: the two next to the fill line are left out, so no filled section remains (n_liquid is not fitted)."""
    m = V.bottle_background_map(30.0, 1.5, 80.0, 0.00125, 1.52, 1.333, DB, DC, 50.0)
    r = _fit(m)
    assert r["sections"] == 1 and r["n_liquid"] is None and "n_liquid" not in r["free"]
    flat = [v for v in r.values() if isinstance(v, float)]
    assert all(np.isfinite(flat)) and len(flat) > 5


def test_the_separated_flag_needs_one_percent_sigma_so_a_loose_flag_cannot_come_back():
    """At the old 25 % the flag called a noisy, off-by-0.05 n_glass 'separated'; at 1 % a central-window fit is not."""
    m = _map(0.5, 1.333)
    x = m["x_mm"]
    rng = np.random.default_rng(5)
    u = np.where(np.abs(x)[None, :] <= 0.25 * R_B, m["u_mm"] + rng.normal(0.0, 0.006, m["u_mm"].shape), np.nan)
    r = _fit({"u_mm": u, "x_mm": x, "camera_distance_mm": DC, "background_distance_mm": DB}, rows_per_section=1)
    assert r["sigma"]["n_glass"] > 0.01 * r["n_glass"] and not r["separated"] and "n_glass" in r["poorly_determined"]
    assert V._POOR_REL_SIGMA == 0.01
