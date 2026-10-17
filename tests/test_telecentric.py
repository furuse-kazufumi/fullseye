# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""telecentric の門: 主光線は絞りの中心を通る、倍率は L/(L − Δz)、Newton の入射瞳、ぼけの RMS、前玉のケラレ、ピンホールの写し。"""
from __future__ import annotations

import math

import numpy as np
import pytest

import opsoptics
import raytrace as RT
import telecentric as T


@pytest.fixture(scope="module")
def lenses():
    return {k: T.telecentric_lens(k) for k in ("entocentric", "object", "bi")}


def test_generator_keeps_the_design_magnification_and_places_the_stop(lenses):
    for k, s in lenses.items():
        p = RT.paraxial_trace(s)
        assert abs(p["magnification"] + 0.5) < 1e-9, k
        assert s["design"]["kind"] == k and s["surfaces"][s["stop"]]["ap"] > 0
    # 物体側・両側テレセンは近軸の入射瞳が無限遠、通常のレンズはレンズの近く
    assert not math.isfinite(RT.paraxial_trace(lenses["object"])["ep_position"])
    assert not math.isfinite(RT.paraxial_trace(lenses["bi"])["ep_position"])
    assert abs(RT.paraxial_trace(lenses["entocentric"])["ep_position"]) < 10.0
    # 両側テレセンは像側も平行: 射出瞳が無限遠
    assert abs(RT.paraxial_trace(lenses["bi"])["xp_position"]) > 1e6


def test_chief_ray_passes_the_stop_centre_even_with_the_pupil_at_infinity(lenses):
    for s in lenses.values():
        for h in (1.0, 4.0, 8.0):
            c = T.chief_ray_angle(s, h)
            assert c["stop_residual_mm"] < 1e-12 and c["valid"]
    # ★2026-10-15 まで raytrace.chief_ray は入射瞳を狙い、物体側テレセンでは ValueError で止まった。
    #   いまは入射瞳が無限遠なら絞りを狙う —— この層の主光線と同じ像の高さになること。
    for h in (1.0, 4.0, 8.0):
        rc = RT.chief_ray(lenses["object"], h)
        assert rc["valid"] and abs(rc["image_y"] - T.chief_ray_angle(lenses["object"], h)["image_y_mm"]) < 1e-9
    # 近軸の限界(小さい物高)では物体側テレセンの傾きは 0 に近い、通常のレンズは tanθ = h/L
    # (残りは単レンズの瞳の球面収差 ∝ h³: 8 mm で 0.05° → 0.5 mm で 1.3e-5°)
    assert abs(T.chief_ray_angle(lenses["object"], 0.5)["object_angle_deg"]) < 3e-5
    p = RT.paraxial_trace(lenses["entocentric"])
    L = lenses["entocentric"]["object_mm"] + p["ep_position"]
    c = T.chief_ray_angle(lenses["entocentric"], 0.5)
    assert abs(c["object_angle_deg"] / -math.degrees(math.atan(0.5 / L)) - 1) < 1e-4


def test_magnification_vs_depth_follows_the_pupil_distance(lenses):
    s = lenses["entocentric"]
    mv = T.magnification_vs_depth(s, 2.0, -5.0, 5.0, 11)
    assert mv.shape == (11, 2)
    L = T.chief_ray_angle(s, 2.0)["pupil_distance_mm"]
    ratio = mv[:, 1] / mv[5, 1]
    assert np.max(np.abs(ratio / (L / (L - mv[:, 0])) - 1)) < 5e-5
    assert ratio[-1] > 1.015                         # 近い物ほど大きい
    for k in ("object", "bi"):
        mt = T.magnification_vs_depth(lenses[k], 2.0, -5.0, 5.0, 11)
        assert np.max(np.abs(mt[:, 1] / mt[5, 1] - 1)) < 1e-4


def test_stop_shift_moves_the_entrance_pupil_by_newtons_equation(lenses):
    base = lenses["object"]
    f, ffl, obj = base["design"]["lens1"]["efl"], base["design"]["lens1"]["ffl"], base["design"]["object_mm"]
    for d in (-2.0, 1.5):
        s = T.telecentric_lens("object", stop_shift_mm=d)
        L = ffl - f * f / d + obj
        p = RT.paraxial_trace(s)
        assert abs((obj + p["ep_position"]) / L - 1) < 1e-9
        th = T.chief_ray_angle(s, 0.5)["object_angle_deg"] - T.chief_ray_angle(base, 0.5)["object_angle_deg"]
        assert abs(th / -math.degrees(math.atan(0.5 / L)) - 1) < 2e-3
    e = T.telecentricity_error(T.telecentric_lens("object", stop_shift_mm=-2.0), 2.0, 5.0)
    assert abs(e["lateral_shift_um"] / e["closed_form_shift_um"] - 1) < 0.02


def test_defocus_rms_slope_is_m_na_over_root_two(lenses):
    sp = T.defocus_spot_vs_depth(lenses["bi"], 0.0, -4.0, 4.0, 9, samples=41)
    far = np.abs(sp[:, 0]) >= 2.0
    A = np.stack([np.abs(sp[far, 0]), np.ones(far.sum())], 1)
    slope = np.linalg.lstsq(A, sp[far, 1], rcond=None)[0][0]
    assert abs(slope / (0.5 * 0.01 / math.sqrt(2) * 1000) - 1) < 0.03


def test_telecentric_field_is_bounded_by_the_front_lens(lenses):
    vt = T.vignetting_vs_field(lenses["object"], 16.0, 9, 41)
    ve = T.vignetting_vs_field(lenses["entocentric"], 16.0, 9, 41)
    assert vt[0, 1] == pytest.approx(1.0) and vt[-1, 1] == 0.0      # 前玉(12.5 mm)の外は写らない
    assert ve[-1, 1] > 0.95                                           # 通常のレンズは前玉より広く見える


def test_pinhole_projects_with_the_lens_magnification(lenses):
    import render3d
    cam4 = T.lens_equivalent_pinhole(lenses["entocentric"], pixel_pitch_um=10.0, width=401, height=401)
    assert not cam4["orthographic_proxy"]
    # 物体面(z = 0)の点 (2 mm, 0) は |m|·2 mm / 10 µm = 100 画素 → 中心から 100 画素
    V = np.array([[1.9, -0.1, 0.0], [2.1, -0.1, 0.0], [2.0, 0.1, 0.0]])
    r = render3d.render_mesh(V, np.array([[0, 1, 2]]), cam4["pose"], cam4["K"], 401, 401)
    cols = np.nonzero(r["silhouette"].any(0))[0]
    assert abs(0.5 * (cols.min() + cols.max()) - (200 + 100)) <= 1.0
    tele = T.lens_equivalent_pinhole(lenses["bi"])
    assert tele["orthographic_proxy"] and tele["pupil_distance_mm"] == 1.0e7
    with pytest.raises(ValueError, match="hypercentric"):
        T.lens_equivalent_pinhole(T.telecentric_lens("object", stop_shift_mm=30.0))


def test_fail_closed():
    with pytest.raises(ValueError):
        T.telecentric_lens("fisheye")
    with pytest.raises(ValueError):
        T.telecentric_lens(magnification=0.5)                 # 正の倍率は単群の実像にならない
    with pytest.raises(ValueError):
        T.telecentric_lens(na_object=0.0)
    with pytest.raises(ValueError):
        T.telecentric_lens(focal_mm=10.0)                     # 前玉の半口径がレンズの曲率半径を超える
    s = T.telecentric_lens()
    with pytest.raises(ValueError):
        T.chief_ray_angle(s, 0.0)
    with pytest.raises(ValueError):
        T.chief_ray_angle(s, 5.0, object_shift_mm=1e4)       # 物体がレンズを越える
    with pytest.raises(ValueError):
        T.magnification_vs_depth(s, 2.0, 1.0, -1.0)
    with pytest.raises(ValueError):
        T.defocus_spot_vs_depth(s, samples=5)
    with pytest.raises(ValueError):
        T.chief_ray_angle(RT.example_system("singlet"), 2.0)  # 無限遠の物体は拒否
    with pytest.raises(ValueError):
        T.chief_ray_angle({"surfaces": []}, 2.0)


def test_registered_in_opsoptics():
    assert opsoptics.list_ops("telecentric") == list(T.__all__)
    assert opsoptics.missing() == []
    out = opsoptics.call("chief_ray_angle", opsoptics.call("telecentric_lens"), 3.0)
    assert out["valid"]
