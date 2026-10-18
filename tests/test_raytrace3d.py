# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""raytrace3d(非共軸の逐次光線追跡)の門。

真値は raytrace3d を通さない閉形式: 平面鏡の折り返し = 展開した系の像の Householder 鏡映、反射の回数と像の
裏返り、傾いた平行平板の横ずれ・非点隔差(Smith / Coddington)、シャインプルーフの tanθ' = m·tanθ、Fresnel と
λ/4 単層膜の反射率、平板の 2 回反射のゴーストの焦点 −2t/n、軸外し放物面の焦点(optiland の公開例と同じ配置)。
共軸の処方は raytrace.trace_rays と 1e-12 で一致すること。壊して確かめる探針(反射の後の座標系の曲げを
取り違える・折り返しの切り替えの順序を取り違える)で門が赤になることも確かめる。乱数は引かない。
"""
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import raytrace as RT  # noqa: E402
import raytrace3d as R3  # noqa: E402

INF = math.inf


def _coaxial_cases():
    cass = RT.lens_system([{"R": -400.0, "t": 150.0, "n": 1.0, "k": -1.0, "ap": 50, "mirror": True},
                           {"R": -120.0, "t": 200.0, "n": 1.0, "k": -3.0, "ap": 15, "mirror": True,
                            "decenter": (0.1, 0.2), "tilt": (0.05, 0.03)}], stop=0, field=0.2)
    tilted = RT.lens_system([{"R": 40, "t": 5, "n": "N-BK7", "ap": 10, "tilt": (0.3, 0.2), "decenter": (0.05, -0.02)},
                             {"R": -60, "t": None, "n": 1.0, "asph": (1e-6, -2e-9)}], object_mm=300, field=3.0)
    return [RT.example_system(n) for n in ("singlet", "doublet", "catalog_doublet", "asphere", "paraboloid",
                                           "sphere_mirror")] + [cass, tilted]


def _grid_rays(s):
    ap = s["surfaces"][s["stop"]]["ap"]
    g = np.linspace(-1.0, 1.0, 9)
    X, Y = np.meshgrid(g, g)
    P = np.stack([X.ravel() * ap * 0.9, Y.ravel() * ap * 0.9, np.full(X.size, -20.0)], 1)
    D = np.tile([0.0, 0.02, 1.0], (X.size, 1))
    return P, D


def test_coaxial_prescriptions_trace_exactly_like_raytrace():
    for s in _coaxial_cases():
        s3 = R3.noncoaxial_system(s)
        P, D = _grid_rays(s)
        a = RT.trace_rays(s, P, D)
        b = R3._trace(s3, P, D)
        assert np.array_equal(a["valid"], b["valid"]) and a["valid"].sum() > 0
        assert np.nanmax(np.abs(a["points"] - b["points"])) <= 1e-12
        assert np.nanmax(np.abs(a["opl"] - b["opl"])) <= 1e-12
        st, st3 = RT.spot_stats(s, rings=6), R3.noncoaxial_spot(s3, rings=6)
        assert abs(st["rms_radius"] - st3["rms_radius"]) <= 1e-12
        assert st["n_rays"] == st3["n_rays"]


def test_probe_wrong_bend_after_a_mirror_breaks_the_coaxial_gate(monkeypatch):
    # 反射の後の座標系を x 軸でなく y 軸まわりに 180° 回すと、鏡の後の偏心した副鏡が逆側に置かれる
    s = _coaxial_cases()[6]
    P, D = _grid_rays(s)
    a = RT.trace_rays(s, P, D)
    monkeypatch.setattr(R3, "_REV", np.diag([-1.0, 1.0, -1.0]))
    b = R3._trace(R3.noncoaxial_system(s), P, D)
    diff = np.nanmax(np.abs(a["points"] - b["points"])) if np.any(b["valid"]) else np.inf
    assert diff > 1e-3


def _householder(p, p0, n):
    return p - 2.0 * ((p - p0) @ n) * n


@pytest.mark.parametrize("tilt", [(45.0, 0.0), (0.0, 30.0), (20.0, 30.0), (-35.0, 10.0)])
def test_fold_mirror_image_is_the_mirror_image_of_the_unfolded_image(tilt):
    L = RT.lens_system()
    bfl = RT.paraxial_trace(L)["bfl"]
    lens = [{"R": 51.68, "t": 5.0, "n": (1.5168, 64.17), "ap": 12.5}, {"R": INF, "t": 40.0, "n": 1.0}]
    folded = R3.noncoaxial_system(lens + [{"type": "fold_mirror", "tilt": tilt, "ap": 40, "t": bfl - 40.0}], stop=0)
    unfolded = R3.noncoaxial_system([lens[0], {"R": INF, "t": bfl, "n": 1.0}], stop=0)
    n = RT._rot(*tilt)[:, 2]                                   # 鏡の法線(大域)
    p0 = np.array([0.0, 0.0, 45.0])                            # 鏡の頂点
    for f in [(0.0, 0.0), (1.5, 0.0), (0.0, 2.0), (1.0, -1.5)]:
        a = R3._chief(folded, f)["points"][0, -1]
        b = R3._chief(unfolded, f)["points"][0, -1]
        assert np.max(np.abs(a - _householder(b, p0, n))) < 1e-12 * 1e3
    o = R3.image_orientation(folded)
    assert o["n_reflections"] == 1 and o["reversed"] and o["parity_closed_form"] == -1


def test_probe_naive_fold_order_misses_the_reflected_axis():
    # 鏡の前後の切り替えを同じ順序(xyz)の同じ角にすると、y 軸まわりの折り返しで軸が鏡映方向に向かない
    tilt = (0.0, 30.0)
    recs = [{"R": 51.68, "t": 5.0, "n": (1.5168, 64.17), "ap": 12.5}, {"R": INF, "t": 40.0, "n": 1.0},
            {"type": "break", "tilt": (0.0, 30.0, 0.0), "t": 0.0}, {"R": INF, "mirror": True, "ap": 40, "t": 0.0},
            {"type": "break", "tilt": (0.0, 30.0, 0.0), "t": 50.0}]
    naive = R3.noncoaxial_system(recs, stop=0)
    good = R3.noncoaxial_system(recs[:2] + [{"type": "fold_mirror", "tilt": tilt, "ap": 40, "t": 50.0}], stop=0)
    na = np.array(R3.noncoaxial_layout(naive)["image"]["normal"])
    ga = np.array(R3.noncoaxial_layout(good)["image"]["normal"])
    n = RT._rot(*tilt)[:, 2]
    refl = _householder(np.array([0.0, 0.0, 1.0]), np.zeros(3), n)
    assert np.max(np.abs(ga - refl)) < 1e-12
    assert np.max(np.abs(na - refl)) > 0.5


def test_periscope_has_an_even_number_of_reflections_and_an_unreversed_image():
    o = R3.image_orientation(R3.noncoaxial_example("periscope"))
    assert o["n_reflections"] == 2 and not o["reversed"] and o["det"] > 0
    o1 = R3.image_orientation(R3.noncoaxial_example("folded_singlet"))
    o0 = R3.image_orientation(R3.noncoaxial_system(RT.lens_system()))
    assert o1["reversed"] and not o0["reversed"]
    # 単レンズの実像は 180° 回転(倒立)、鏡 1 枚で上下だけ反転(det < 0)
    assert abs(abs(o0["rotation_deg"]) - 180.0) < 1e-9


def test_beamsplitter_branches_match_the_closed_forms():
    b = R3.beamsplitter_branches(thickness_mm=3.0, glass="N-BK7", tilt_deg=45.0, reflectance=0.5,
                                 focal_mm=100.0, f_number=10.0, gap_mm=40.0)
    cf = R3.tilted_plate_shift(3.0, "N-BK7", 45.0)
    # 透過: 主光線(軸に平行)の横ずれ = Smith の閉形式
    assert abs(abs(b["transmit"]["image_point"][1]) - cf["lateral_shift_mm"]) < 1e-12
    assert b["transmit"]["axis_direction"] == [0.0, 0.0, 1.0]
    # 反射: 像 = 展開した焦点の鏡映(鏡の頂点 = 平板の前面)
    lens = R3._paraxial_lens_elements(100.0, 5.0, 40.0)
    s0 = R3.noncoaxial_system(lens[:1] + [dict(lens[1], t=None)], stop=0)
    z_plate = 2.0 + 40.0
    p_unf = R3._chief(s0, (0.0, 0.0))["points"][0, -1]
    fp = R3._focus_point(s0, (0.0, 0.0))
    n = RT._rot(45.0, 0.0)[:, 2]
    want = _householder(fp, np.array([0.0, 0.0, z_plate]), n)
    assert np.max(np.abs(np.array(b["reflect"]["image_point"]) - want)) < 1e-6
    assert p_unf[1] == 0.0
    assert b["transmit"]["energy_fraction"] == 0.5 and b["reflect"]["energy_fraction"] == 0.5
    # 反射の枝の軸は 90° 折れる
    assert abs(np.dot(b["reflect"]["axis_direction"], [0.0, 1.0, 0.0]) - 1.0) < 1e-12


@pytest.mark.parametrize("theta", [10.0, 30.0, 45.0, 60.0])
def test_tilted_plate_shift_and_astigmatism_equal_the_closed_forms(theta):
    base = [{"R": 51.68, "t": 5.0, "n": (1.5168, 64.17), "ap": 2.0}, {"R": INF, "t": 40.0, "n": 1.0}]
    sp = R3.noncoaxial_system(base + [{"type": "plate", "thickness": 5.0, "n": "N-BK7", "tilt": (theta, 0.0), "ap": 30,
                              "t": 30.0}], stop=0)
    sn = R3.noncoaxial_system(base[:1] + [{"R": INF, "t": 70.0, "n": 1.0}], stop=0)
    ft, fs = R3._foci(sp, (0.0, 0.0))
    f0t, f0s = R3._foci(sn, (0.0, 0.0))
    d = R3._chief(sp, (0.0, 0.0))["dirs"][0, -1]
    n = RT.refractive_index("N-BK7")
    s, c = math.sin(math.radians(theta)), math.cos(math.radians(theta))
    q = math.sqrt(n * n - s * s)
    lat = 5.0 * s * (1.0 - c / q)                              # Smith
    ast = (5.0 / q) * (1.0 - n * n * c * c / (q * q))          # Coddington(接線像が遠い)
    cf = R3.tilted_plate_shift(5.0, "N-BK7", theta)
    assert abs(cf["lateral_shift_mm"] - lat) < 1e-14 and abs(cf["astigmatism_signed_mm"] - ast) < 1e-12
    assert abs(abs(R3._chief(sp, (0.0, 0.0))["points"][0, -1][1]) - lat) < 1e-12
    # 焦点はほぼ平行な 2 本の最接近点なので丸めの床が環境で 1e-9〜1e-7 mm と変わる(CI py3.10 で 1.0e-7)
    assert abs((ft - fs) @ d - ast) < 1e-6
    assert abs((fs - f0s) @ d - cf["sagittal_shift_mm"]) < 1e-6
    assert abs((ft - f0t) @ d - cf["tangential_shift_mm"]) < 1e-6


def test_untilted_plate_shifts_the_focus_by_t_n_minus_1_over_n():
    cf = R3.tilted_plate_shift(5.0, 1.5, 0.0)
    assert abs(cf["sagittal_shift_mm"] - 5.0 * 0.5 / 1.5) < 1e-14 and cf["astigmatism_mm"] < 1e-14


@pytest.mark.parametrize("theta", [10.0, 30.0, 50.0])
def test_scheimpflug_real_rays_match_tan_theta_prime_equals_m_tan_theta(theta):
    r = R3.scheimpflug_tilt(None, 200.0, theta, heights_mm=[-0.2, -0.1, 0.0, 0.1, 0.2])
    m = r["magnification"]
    assert abs(math.tan(math.radians(r["image_tilt_deg"])) - m * math.tan(math.radians(theta))) < 1e-14
    assert abs(r["image_tilt_traced_deg"] - r["image_tilt_deg"]) < 1e-3
    # ヒンジ: Gauss の結像式で傾いた物面の 2 点を写すと、像の 2 点を結ぶ直線は同じ傾き(閉形式の独立の確かめ)
    f, s = r["efl_mm"], r["s_mm"]
    pts = []
    for y in (-1.0, 1.0):
        sy = s - y * math.tan(math.radians(theta))
        spy = sy * f / (sy - f)
        pts.append((-spy / sy * y, spy))
    slope = (pts[1][1] - pts[0][1]) / (pts[1][0] - pts[0][0])
    assert abs(math.atan(slope) - math.radians(r["image_tilt_deg"])) < 1e-12
    # 物面は前側主面と、像面は後側主面と、同じ高さ y_h = s/tanθ で交わる
    y_h = r["hinge_height_mm"]
    zi = r["rear_principal_mm"] + r["s_prime_mm"]
    assert abs((r["rear_principal_mm"] - zi) / math.tan(math.radians(r["image_tilt_deg"])) - y_h) < 1e-9 * y_h


def test_surface_reflectance_closed_forms():
    n = RT.refractive_index("N-BK7")
    r0 = R3.surface_reflectance(1.0, "N-BK7")
    assert abs(r0["R"] - ((n - 1) / (n + 1)) ** 2) < 1e-12
    r1 = R3.surface_reflectance(1.0, "N-BK7", coating="MGF2")
    import materials as M
    nl = float(M._nk(M._record("MGF2", "t"), RT.WL_D, "t")[0][0])
    assert abs(r1["R"] - ((n - nl * nl) / (n + nl * nl)) ** 2) < 1e-12 and r1["R"] < 0.013
    assert R3.surface_reflectance(coating={"R": 0.5})["R"] == 0.5
    # 内側からの反射も同じ(吸収の無い積層は相反)
    assert abs(R3.surface_reflectance("N-BK7", 1.0)["R"] - r0["R"]) < 1e-15


def test_plate_ghost_focus_is_2t_over_n_in_front_and_the_energy_is_R_squared():
    t, n = 5.0, 1.5
    s = R3.noncoaxial_system([{"R": 51.68, "t": 5.0, "n": (1.5168, 64.17), "ap": 0.3},
                     {"R": INF, "t": 40.0, "n": 1.0},
                     {"R": INF, "t": t, "n": n, "ap": 20, "label": "W1"},
                     {"R": INF, "t": None, "n": 1.0, "ap": 20, "label": "W2"}], stop=0)
    g = R3.ghost_analysis(s, pupil_fill=0.5)
    assert g["n_pairs"] == 4 * 3 // 2 and len(g["ghosts"]) == 6
    w = [r for r in g["ghosts"] if r["label"] == "W1/W2"][0]
    assert w is g["ghosts"][0]                                 # 像面の近くに集まるので最も明るい
    assert abs(w["energy_ratio"] - ((n - 1) / (n + 1)) ** 4) < 1e-15
    assert abs(w["focus_offset_mm"] + 2.0 * t / n) < 2e-4
    # 像面での半径 = (2t/n)·tan u(周辺光線の傾き、小 NA)
    para = RT.paraxial_trace(RT.lens_system([{"R": 51.68, "t": 5.0, "n": (1.5168, 64.17), "ap": 0.3},
                                             {"R": INF, "t": 40.0, "n": 1.0}, {"R": INF, "t": t, "n": n},
                                             {"R": INF, "t": None, "n": 1.0}], stop=0))
    slope = abs(para["marginal"]["u"][-1]) * 0.5
    assert abs(w["max_radius_mm"] - 2.0 * t / n * slope) < 2e-3 * w["max_radius_mm"]


def test_mgf2_coating_lowers_the_plate_ghost_by_the_closed_form_ratio():
    s = R3.noncoaxial_system([{"R": 51.68, "t": 5.0, "n": (1.5168, 64.17), "ap": 1.0},
                     {"R": INF, "t": 40.0, "n": 1.0},
                     {"R": INF, "t": 5.0, "n": "N-BK7", "ap": 20, "label": "W1"},
                     {"R": INF, "t": None, "n": 1.0, "ap": 20, "label": "W2"}], stop=0)
    bare = [r for r in R3.ghost_analysis(s)["ghosts"] if r["label"] == "W1/W2"][0]
    ar = [r for r in R3.ghost_analysis(s, coatings={2: "MGF2", 3: "MGF2"})["ghosts"] if r["label"] == "W1/W2"][0]
    rb = R3.surface_reflectance(1.0, "N-BK7")["R"]
    ra = R3.surface_reflectance(1.0, "N-BK7", coating="MGF2")["R"]
    assert abs(bare["energy_ratio"] / ar["energy_ratio"] - (rb / ra) ** 2) < 1e-9


def test_beamsplitter_plate_ghost_separation_is_2t_tan_theta_prime_cos_theta():
    # 平行光を 45° の平板に当てる: 2 回反射のゴーストは主光線と平行に 2t·tanθ'·cosθ だけずれて出る
    th, t = 45.0, 3.0
    s = R3.noncoaxial_system([{"R": INF, "n": 1.0, "ap": 2.0, "t": 10.0, "label": "pupil"},
                     {"type": "plate", "thickness": t, "n": "N-BK7", "tilt": (th, 0.0), "ap": 30.0,
                      "beamsplitter": 0.5, "t": 20.0, "label": "BS"},
                     {"R": INF, "n": 1.0, "ap": 30.0, "t": None, "label": "end"}], stop=0, image_mm=20.0)
    gp = R3.ghost_path(s, i=2, j=3, rings=1)
    nom = R3._trace(s, gp["points"][:, 0, :], np.tile([0.0, 0.0, 1.0], (len(gp["points"]), 1)))
    pn = nom["points"][0, 3]
    pg = gp["points"][0, 5]
    n = RT.refractive_index("N-BK7")
    tp = math.asin(math.sin(math.radians(th)) / n)
    want = 2.0 * t * math.tan(tp) * math.cos(math.radians(th))
    w = pg - pn
    d = np.array([0.0, 0.0, 1.0])
    assert abs(np.linalg.norm(w - (w @ d) * d) - want) < 1e-12
    e = R3.ghost_analysis(s)["ghosts"][0]
    assert e["label"] == "BS:front/BS:back" and abs(e["R_i"] - 0.5) < 1e-15


def test_off_axis_parabola_focuses_at_the_parent_focus():
    s = R3.noncoaxial_example("off_axis_parabola")
    tr = R3.noncoaxial_trace(s, rings=4)["fields"][0]
    p = tr["points"][tr["valid"], -1, :]
    assert np.max(np.abs(p - np.array([0.0, 0.0, -50.0]))) < 1e-8
    assert R3.noncoaxial_spot(s)["rms_radius"] < 1e-9


def test_coordinate_break_undo_and_return_restore_the_frame():
    s = R3.noncoaxial_system([{"R": INF, "n": 1.0, "ap": 5.0, "t": 10.0},
                     {"type": "break", "decenter": (1.0, -2.0), "tilt": (10.0, -20.0, 30.0), "t": 7.0},
                     {"type": "break", "undo": 1, "t": 0.0},
                     {"R": INF, "n": 1.0, "ap": 5.0, "t": 5.0, "label": "back"}], stop=0, image_mm=5.0)
    lay = R3.noncoaxial_layout(s)
    back = [r for r in lay["surfaces"] if r["label"] == "back"][0]
    R = np.array(back["rotation"])
    # undo は角と偏心を逆順に戻す —— 傾いた z に沿って 7 mm 進んだ分だけが残り、回転は単位行列に戻る
    assert np.max(np.abs(R - np.eye(3))) < 1e-15
    B = R3._break_matrix((10.0, -20.0, 30.0), "xyz")
    want = np.array([0.0, 0.0, 10.0]) + B @ np.array([0.0, 0.0, 7.0])
    assert np.max(np.abs(np.array(back["vertex"]) - want)) < 1e-12


def test_raytrace_tilted_mirror_rays_are_no_longer_counted_as_valid():
    # ★2026-10-15: 傾いた鏡(摂動)の後で像面と平行に進む光線を、以前は rms 3.4e18 mm の有効な点として数えた
    s = RT.lens_system([{"R": 51.68, "t": 5.0, "n": (1.5168, 64.17), "ap": 12.5},
                        {"R": INF, "t": 40.0, "n": 1.0, "ap": 30, "mirror": True, "tilt": (45.0, 0.0)},
                        {"R": INF, "t": None, "n": 1.0}], stop=0)
    with pytest.raises(ValueError):
        RT.spot_stats(s)
    with pytest.raises(ValueError):
        R3.noncoaxial_spot(s)


def test_tolerance_compensator_is_explicit():
    s = RT.lens_system()
    a = RT.tolerance_analysis(s, trials=8, compensator="auto")
    b = RT.tolerance_analysis(s, trials=8, compensator="back_focus")
    c = RT.tolerance_analysis(s, trials=8, compensator="none")
    assert a["compensator"] == "back_focus" and a["rms_spot"] == b["rms_spot"]
    assert c["compensator"] == "none" and c["rms_spot"]["std"] > 5.0 * b["rms_spot"]["std"]
    fixed = RT.lens_system([dict(R=x["R"], t=x["t"], n=x["n"], ap=x["ap"]) for x in s["surfaces"][:-1]] +
                           [dict(R=INF, t=RT.paraxial_trace(s)["bfl"], n=1.0)], stop=0)
    assert RT.tolerance_analysis(fixed, trials=4)["compensator"] == "none"
    with pytest.raises(ValueError):
        RT.tolerance_analysis(s, trials=2, compensator="refocus")


def test_chief_ray_through_a_telecentric_stop():
    import telecentric as TC
    L = TC.telecentric_lens("object")
    c = RT.chief_ray(L, field=8.0)
    assert c["valid"] and abs(c["image_y"] - TC.chief_ray_angle(L, 8.0)["image_y_mm"]) < 1e-9


def test_validation_is_fail_closed():
    with pytest.raises(ValueError):
        R3.noncoaxial_system([{"R": 10.0, "t": 1.0, "n": 1.5, "sag": 1}])
    with pytest.raises(ValueError):
        R3.noncoaxial_system([{"type": "fold_mirror", "tilt": (95.0, 0.0), "t": 1.0}])
    with pytest.raises(ValueError):
        R3.noncoaxial_system([{"R": INF, "t": None, "n": 1.0, "ap": 1}, {"R": INF, "t": 1.0, "n": 1.0}])
    with pytest.raises(ValueError):
        R3.noncoaxial_system([{"type": "break", "undo": 0, "t": 1.0}])
    with pytest.raises(ValueError):
        R3.surface_reflectance(coating={"R": 1.5})
    with pytest.raises(ValueError):
        R3.noncoaxial_trace(R3.noncoaxial_example("folded_singlet"), branch="reflect")
    with pytest.raises(ValueError):
        R3.noncoaxial_system([{"R": INF, "t": 1.0, "n": 1.0, "ap": 1}], stop="nope")


def test_ghost_image_and_examples_run():
    s = R3.noncoaxial_example("epi_beamsplitter")
    img = R3.ghost_image(s, size=32)
    assert img.shape == (32, 32) and np.isfinite(img).all() and img.max() > -1.0 and img.min() == -12.0
    for name in ("folded_singlet", "periscope", "coaxial_doublet", "tilted_plate", "epi_beamsplitter",
                 "scheimpflug", "off_axis_parabola"):
        sp = R3.noncoaxial_spot(R3.noncoaxial_example(name))
        assert sp["n_rays"] > 0 and math.isfinite(sp["rms_radius"])
