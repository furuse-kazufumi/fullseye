# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""cutting の門(食材の切断を画像で測る: 閉形式の切断力学と合成の被覆率描画を真値に、--full 相当の MuJoCo は facade で)。

numpy だけの門(常に走る、解像度を落とした 4 px/mm と 10 px/mm):
 1. 閉形式: Atkins 2016 の H = ξV・合力・R と w の 1 次、本文の「H/Rw は ξ = 1 で最大 0.5」と「ξ = tan i」、Williams & Patel 2016 の
    最小 1/(1 − sin β) が θ + β = 90° に在り μ = 0.2 で 1.24(本文)。未読の組合せ(ξ > 0 と摩擦・刃角)は ValueError
 2. slice/push 比の閉形式と綴り壊し、切っている幅の閉形式 = 標本を数えた幅
 3. 描画器: 被覆率の和 = 刃の多角形の面積、場面の縮尺(px_per_mm に比例)と知らないキー
 4. 刃の追跡(角度・隠れた中央の刃先・先端)と切り込み深さ
 5. 切片の厚み(薄い 0.1 mm と厚い 2 mm、傾きつき)、刃が端面を突き抜ける形は 0 や負を返さない
 6. 回帰: gain 0.4 を拒否しない(試作は絶対の閾値で拒否)、照明勾配 0.8 の薄い切片が偏らない、ぼけ 4 px は窓を広げて偏らず 8 px は拒否
 7. 切断面の粗さ: 平らな面の床、長い波長の Ra
 8. 力: 閉形式の切断 1 回分 → 手首のたわみ → R が真値、力 1.25 倍の世界では R も 1.25 倍(模型を共有する門の自己申告)
 9. 測るものが無い・綴り壊し・ライセンス未記入の CSV、CSV の読み込み、MJCF 文字列
mujoco が要る門(無ければ skip):
10. 柔らかい手首の刃: 拘束力は定常値 R·w·g(ξ) を超えず、ばねのたわみの力と減衰 c·v 以内で一致
"""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import numpy as np
import pytest

import cutting as C

SF = C.cutting_scene("face", 4.0)
SE = C.cutting_scene("edge", 10.0)
ZB = (6.0 + SE["blade_hb"] + 0.3, SE["food_top"] - 0.3)


def _raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    return False


def _edge_z(track, x_mm, sc):
    f = track["line"]
    return (sc["board_row"] - (f["cy"] + (x_mm * sc["px_per_mm"] - f["cx"]) * f["dy"] / f["dx"])) / sc["px_per_mm"]


def _thick_err(se, h, lean, **cam):
    img = C.cutting_edge_render(se, 6.0, 6.0 + h, lean, 6.0, seed=5, **cam)
    r = C.slice_thickness_profile(img, se["px_per_mm"], se["board_row"], (6.0 + se["blade_hb"] + 0.3, se["food_top"] - 0.3))
    tru = h + (se["food_top"] - r["z_mm"]) * math.tan(math.radians(lean))
    return r, r["thickness_mm"] - tru


# ── 1〜2. 閉形式 ──────────────────────────────────────────────────────────────
def test_closed_forms_reproduce_the_papers_numbers():
    worst = 0.0
    for R in (50.0, 400.0):
        for w in (10.0, 34.0):
            for xi in (0.0, 0.3, 1.0, 3.0):
                f = C.cut_force_atkins(R, w, xi=xi)
                s = R * w * 1e-3
                worst = max(worst, abs(f["H"] - xi * f["V"]) / s, abs(math.hypot(f["V"], f["H"]) - f["F_res"]) / s,
                            abs(f["V"] - s / (1 + xi * xi)) / s)
    assert worst < 1e-12
    a = C.cut_force_atkins(400, 34, xi=0.7)["V"]
    assert abs(C.cut_force_atkins(800, 34, xi=0.7)["V"] - 2 * a) < 1e-12 and abs(C.cut_force_atkins(400, 68, xi=0.7)["V"] - 2 * a) < 1e-12
    xs = np.linspace(0.0, 4.0, 801)
    hh = np.array([C.cut_force_atkins(1.0, 1000.0, xi=x)["H"] for x in xs])
    assert len(hh) == 801 and abs(xs[int(np.argmax(hh))] - 1.0) < 1e-9 and abs(hh.max() - 0.5) < 1e-12   # 本文: ξ = 1 で 0.5
    for i in (5, 20, 45, 60):                                                                                # 本文: ξ = tan i
        assert abs(C.slice_push_ratio(i, 0.0, 5.0) - math.tan(math.radians(i))) < 1e-12
    # Williams & Patel: 最小は θ + β = 90° で 1/(1 − sin β)、μ = 0.2 で θo ≈ 79°・最小 1.24(本文)
    for mu in (0.2, 0.5):
        beta = math.atan(mu)
        th_o = 90.0 - math.degrees(beta)
        v0 = C.cut_force_atkins(1.0, 1000.0, wedge_deg=th_o, mu=mu)["Fc_over_bGc"]
        assert abs(v0 - 1.0 / (1.0 - math.sin(beta))) < 1e-12
        assert all(C.cut_force_atkins(1.0, 1000.0, wedge_deg=th_o + d, mu=mu)["Fc_over_bGc"] > v0 for d in (-0.5, 0.5))
    assert round(1.0 / (1.0 - math.sin(math.atan(0.2))), 2) == 1.24 and round(90 - math.degrees(math.atan(0.2))) == 79


def test_unread_combinations_and_spelling_fail_closed():
    bad = [lambda: C.cut_force_atkins(400, 34, xi=0.5, mu=0.3), lambda: C.cut_force_atkins(400, 34, xi=0.5, wedge_deg=20),
           lambda: C.cut_force_atkins(400, 34, model="atkins"), lambda: C.cut_force_atkins(400, 34, model="Slice_push"),
           lambda: C.cut_force_atkins(0, 34), lambda: C.cut_force_atkins(400, 34, wedge_deg=95, mu=0.2),
           lambda: C.cut_force_atkins(400, float("nan")), lambda: C.cut_force_atkins(True, 34),
           lambda: C.slice_push_ratio(30, 5 * math.cos(math.radians(30)), -5 * math.sin(math.radians(30))),   # 刃先に沿って動く
           lambda: C.slice_push_ratio(95, 0, 5), lambda: C.slice_push_from_track(3, [0, 1, 2], [5, 5, 5]),
           lambda: C.slice_push_from_track(3, [0, 1], [5, 4]), lambda: C.force_from_wrist_displacement([1, 2], [1, 2], 0.0),
           lambda: C.force_from_wrist_displacement([1, 2], [1, 2, 3], 4.0), lambda: C.force_from_wrist_displacement([1, np.nan], [1, 2], 4.0),
           lambda: C.cut_force_fit([1, 2, 3], [5, 5, 5], 0.0, min_w_mm=10), lambda: C.cut_force_fit([-1, -2, -3], [5, 5, 5], 0.0),
           lambda: C.cutting_scene("side"), lambda: C.cutting_scene("face", food_wdth=30), lambda: C.cutting_scene("face", px_per_mm=0.5),
           lambda: C.cutting_episode_synth(vz=0.0), lambda: C.cutting_wrist_mjcf(SE)]
    assert len(bad) == 22
    assert all(_raises(f) for f in bad), [i for i, f in enumerate(bad) if not _raises(f)]


def test_slice_push_ratio_and_cut_width_closed_forms():
    th = 12.0
    u = np.array([math.cos(math.radians(th)), math.sin(math.radians(th))])
    n = np.array([-math.sin(math.radians(th)), math.cos(math.radians(th))])
    for vx, vz in ((0.0, 5.0), (4.0, 6.0), (-3.0, 2.0)):
        v = np.array([vx, -vz])
        assert abs(C.slice_push_ratio(th, vx, vz) - abs(v @ u) / abs(v @ n)) < 1e-12
    for theta in (-6.0, 0.0, 4.0):
        for ez in (30.0, 24.5, 20.0, 5.0):
            x = np.linspace(-17, 17, 200001)
            sampled = float(((ez + x * math.tan(math.radians(theta))) < 24.0).mean() * 34.0)
            assert abs(C.food_cut_width(theta, ez, 34.0, 24.0) - sampled) < 1e-3


# ── 3. 描画器と場面 ────────────────────────────────────────────────────────────
def test_renderer_preserves_blade_area_and_scene_scales():
    for th in (-7.3, 2.2, 11.0):
        v = C._blade_polygon_xz(SF, 15.0, 12.0, th)
        rr, cc = C._face_xz_to_rc(SF, v[:, 0], v[:, 1])
        cov = C._cov_polygon(SF["H"], SF["W"], np.stack([rr, cc], 1))
        area = 0.5 * abs(np.dot(cc, np.roll(rr, -1)) - np.dot(rr, np.roll(cc, -1)))
        assert abs(cov.sum() - area) / area < 2e-4
    full = C.cutting_scene("face")
    assert (SF["H"], SF["W"], SF["board_row"]) == (full["H"] // 2, full["W"] // 2, full["board_row"] / 2) and SF["food_w"] == full["food_w"]
    img = C.cutting_face_render(SF, 18.0, 12.0, 3.0)
    assert img.shape == (SF["H"], SF["W"], 3) and np.isfinite(img).all()


# ── 4. 刃の追跡と深さ ─────────────────────────────────────────────────────────
def test_blade_track_angle_edge_tip_and_depth():
    for th in (-5.0, 4.5):
        img = C.cutting_face_render(SF, 18.0, 12.0, th, noise=0.01, seed=3)
        tr = C.knife_edge_track(img, SF["board_row"])
        assert abs(tr["angle_deg"] - th) < 0.04
        ez = 12.0 + (SF["food_xc"] - 18.0) * math.tan(math.radians(th))
        assert abs(_edge_z(tr, SF["food_xc"], SF) - ez) < 0.02                   # 隠れた中央は両側からの内挿
        assert tr["tip_rc"] is not None and tr["occluded_cols"] is not None
        v = C._blade_polygon_xz(SF, 18.0, 12.0, th)
        r, c = C._face_xz_to_rc(SF, v[1, 0], v[1, 1])
        assert math.hypot(tr["tip_rc"][0] - r, tr["tip_rc"][1] - c) / SF["px_per_mm"] < 0.4
        d = C.cut_depth_from_side(img, tr, SF["px_per_mm"], SF["board_row"])
        assert abs(d["depth_mm"] - (SF["food_h"] - ez)) < 0.045
    g = C.knife_edge_track(img, SF["board_row"], method="gradient")
    assert abs(g["angle_deg"] - 4.5) < 0.1


# ── 5〜6. 厚み ─────────────────────────────────────────────────────────────────
def test_slice_thickness_thin_and_thick_with_lean():
    for h, lean in ((0.1, 0.0), (2.0, -1.0)):
        r, e = _thick_err(SE, h, lean, noise=0.01)
        assert r["n_rows"] >= 100 and abs(e.mean()) < 0.015 and float(np.sqrt(np.mean(e ** 2))) < 0.04 and abs(r["lean_deg"] - lean) < 0.05
    img = C.cutting_edge_render(SE, 6.0, 6.2, -3.0, 6.0)                         # 刃が端面を突き抜ける
    try:
        r = C.slice_thickness_profile(img, SE["px_per_mm"], SE["board_row"], ZB)
        assert r["n_rows"] < 0.5 * (ZB[1] - ZB[0]) * SE["px_per_mm"] and r["thickness_mm"].min() > 0
    except ValueError:
        pass


def test_thickness_regressions_gain_gradient_and_blur_window():
    _, e = _thick_err(SE, 1.0, 0.0, gain=0.4)                                   # 試作: 刃の灰の絶対の閾値で拒否
    assert abs(e.mean()) < 0.03
    _, e = _thick_err(SE, 0.4, 0.0, gradient=0.8)                               # 薄い切片: 本体の色を照明の勾配で戻す
    assert abs(e.mean()) < 0.03
    se = C.cutting_scene("edge")
    _, e = _thick_err(se, 1.0, 0.0, blur_px=4.0)                                # 試作: 窓 ±3 px 固定で −18 µm
    assert abs(e.mean()) < 0.015
    assert _raises(lambda: _thick_err(se, 1.0, 0.0, blur_px=8.0))                # 刃の帯 32 px < ぼけ → 拒否(試作は −37 µm で通った)


# ── 7. 粗さ ────────────────────────────────────────────────────────────────────
def test_cut_surface_roughness_floor_and_long_wavelength():
    import roughness
    zg = np.linspace(-1, 30, 3101)
    flat = C.cutting_edge_render(SE, {"z_mm": zg, "y_mm": 6.0 + 0.02 * zg}, 0.0, 0.0, 0.0, blade=False)
    floor = C.cut_surface_roughness(flat, SE["px_per_mm"], SE["board_row"], (2.0, 22.0))["params"]["Rq"]
    assert floor < 15.0
    prof = {"z_mm": zg, "y_mm": 6.0 + 0.02 * zg + 0.05 * np.sin(2 * np.pi * zg / 2.0)}
    r = C.cut_surface_roughness(C.cutting_edge_render(SE, prof, 0.0, 0.0, 0.0, blade=False), SE["px_per_mm"], SE["board_row"], (2.0, 22.0))
    tru = np.interp(r["z_mm"], prof["z_mm"], prof["y_mm"])
    pt = roughness.profile_params((tru - np.polyval(np.polyfit(r["z_mm"], tru, 1), r["z_mm"])) * 1000, dx=r["dz_um"])
    assert abs(r["params"]["Ra"] / pt["Ra"] - 1) < 0.10 and r["n_rows"] >= 150


# ── 8. 力 ──────────────────────────────────────────────────────────────────────
def test_force_chain_recovers_R_and_declares_the_shared_model():
    for R, expect in ((400.0, 400.0), (500.0, 500.0)):
        ep = C.cutting_episode_synth(R=R, theta_deg=4.0, vx=4.0, vz=6.0, k_wrist=4.0, dt=0.12, n_frames=36, heel_x0=4.0, scene=SF)
        assert len(ep["t"]) >= 10
        z_cmd_c = ep["heel_z_cmd"] + (SF["food_xc"] - ep["heel_x"]) * math.tan(math.radians(4.0))
        F = C.force_from_wrist_displacement(ep["edge_z_c"], z_cmd_c, 4.0)
        assert np.abs(F - ep["F"]).max() < 1e-9
        assert F.max() <= R * SF["food_w"] * 1e-3 / (1 + ep["xi"] ** 2) + 1e-9      # 定常値 R·w·g(ξ) を超えない
        fit = C.cut_force_fit(F, ep["w_eff"], ep["xi"])
        assert abs(fit["R"] - expect) < 1e-6 * expect and "friction" in fit["model"]
    # 力 1.25 倍の世界(摩擦は模型に無い)を R 400 と読むことはできない: 当てはめは差を靱性に吸い込む
    assert abs(fit["R"] / 400.0 - 1.25) < 1e-6


# ── 9. fail-closed・CSV・MJCF ──────────────────────────────────────────────────
def test_nothing_to_measure_raises():
    flat = np.full((200, 300, 3), 0.5)
    img = C.cutting_face_render(SF, 18.0, 12.0, 0.0)
    nan = img.copy()
    nan[3, 3, 1] = np.nan
    checks = [lambda: C.knife_edge_track(C.cutting_face_render(SF, -200.0, 12.0, 0.0), SF["board_row"]),
              lambda: C.knife_edge_track(flat), lambda: C.knife_edge_track(np.full((10, 10), 0.5)), lambda: C.knife_edge_track(nan),
              lambda: C.knife_edge_track(img, method="Coverage"), lambda: C.slice_thickness_profile(flat, 20, 190),
              lambda: C.slice_thickness_profile(img[..., 0], 20, 190), lambda: C.cut_surface_roughness(flat, 20, 190, (1, 5)),
              lambda: C.cut_surface_roughness(img, 20, 190, None), lambda: C.cut_depth_from_side(img, {"line": {}}, 4, 190),
              lambda: C.cut_depth_from_side(img, [1, 2], 4, 190), lambda: C.cutting_edge_render(SE, {"z": [0, 1]}, 6.0, 0.0, 6.0),
              lambda: C.cutting_edge_render(SE, np.array([[1.0, 6.0], [0.0, 6.0]]), 6.0, 0.0, 6.0)]
    assert len(checks) == 13
    assert all(_raises(f) for f in checks), [i for i, f in enumerate(checks) if not _raises(f)]


def test_force_csv_needs_a_licence_and_parses(tmp_path):
    p = tmp_path / "f.csv"
    rows = ["contact deck,Rcforc Data", "Time,X-force,Time,Y-force,Time,Z-force,"]
    for k in range(5):
        t = 0.01 * k
        rows.append("%g,%g,%g,%g,%g,%g," % (t, 0.0, t, -2.0 * k, t, 0.1))
    p.write_text("\n".join(rows) + "\n", encoding="utf-8")
    d = C.cut_force_csv_load(p, license="CC-BY-NC-4.0")
    assert d["F_xyz"].shape == (5, 3) and d["F_xyz"][4, 1] == -8.0 and d["license"] == "CC-BY-NC-4.0" and "path" not in d
    assert _raises(lambda: C.cut_force_csv_load(p, license=""))
    q = tmp_path / "g.csv"
    q.write_text("a,b\n1,2\n", encoding="utf-8")
    assert _raises(lambda: C.cut_force_csv_load(q, license="x")) and _raises(lambda: C.cut_force_csv_load(tmp_path / "none.csv", license="x"))


def test_mjcf_string_without_mujoco():
    root = ET.fromstring(C.cutting_wrist_mjcf(C.cutting_scene("face"), theta_deg=4.0, k_n_per_mm=4.0))
    j = root.find(".//joint")
    cam = root.find(".//camera")
    assert j.get("type") == "slide" and float(j.get("stiffness")) == 4000.0
    assert cam.get("projection") == "orthographic" and root.find(".//global").get("offwidth") == "800"
    assert "](" not in "".join((getattr(C, n).__doc__ or "") for n in C.__all__) + (C.__doc__ or "")


# ── 10. mujoco ─────────────────────────────────────────────────────────────────
def test_mujoco_soft_wrist_force_matches_spring_within_damper():
    pytest.importorskip("mujoco")
    run = C.cutting_mujoco_wrist(C.cutting_scene("face"), theta_deg=4.0, R=400.0, k_n_per_mm=4.0, damping=25.0, vz=6.0, n_frames=14,
                                 render=False)
    assert len(run["t"]) >= 10 and not run["frames"]
    plateau = run["params"]["plateau_N"]
    F_spring = 4.0 * (run["edge_z_true"] - run["z_cmd_c"])
    F_spring = F_spring - F_spring[0]                                              # 空中の 1 コマ目で風袋
    assert run["F_constraint"].max() <= plateau * (1 + 1e-6) and run["F_constraint"].max() > 0.5 * plateau
    assert np.abs(F_spring - run["F_constraint"]).max() <= 25.0 * 6.0 / 1000 + 1e-6
