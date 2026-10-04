# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""puck の門(エアホッケーのパック追跡・予測・打ち返しを学習なしで: 閉形式と第 2 実装を真値に)。

 1. 閉形式: 停止距離 = ballistics.slide_stop_distance、壁の反発(e²・成分)、鏡映法 = 区間予測、自己整合 + Euler、粘性模型
 2. 5 節リンク: FK∘IK 恒等、届かない → None、作業域の境界、守備線の届く区間
 3. 検出・追跡: 重心 vs 真値、しきい値の偏り(実測)、速いパックで対応が切れる、kalman_ca の新息
 4. 推定: 速度の最小二乗(真値 / 検出)、雑音ありの交点、μ、e・kₜ
 5. 計画: 間に合う / too_late / unreachable / no_crossing、関節軌道の角速度
 6. 合成: モーションブラーの重心 = v·τ/2、針穴カメラの往復、MJCF 文字列、綴り壊し
 7. MuJoCo(mujoco があるとき; 配布物の MJCF は FULLSEYE_AIRHOCKEY_DATA があるとき): 粘性減衰の確認、自前 Coulomb MJCF の減速、描画 → 検出
"""
from __future__ import annotations

import os

import numpy as np
import pytest

import ballistics as B
import balltrack as BT
import puck as PK

X_DEF = -0.75
FPS = 120.0


@pytest.fixture(scope="module")
def tb():
    return PK.puck_table(mu=0.02, e=0.8, kt=0.9)


@pytest.fixture(scope="module")
def cam(tb):
    return PK.puck_camera(tb, px_per_m=200.0)


@pytest.fixture(scope="module")
def link():
    return PK.fivebar_link()


# ── 1. 閉形式 ──────────────────────────────────────────────────────────────

def test_stop_distance_matches_ballistics_and_the_segment_predictor():
    big = PK.puck_table(mu=0.02, x_half=100.0, y_half=100.0)
    pr = PK.puck_slide_predict((0, 0), (1.3, 0.4), big, 1e3)
    v0 = float(np.hypot(1.3, 0.4))
    d_cf = PK.puck_stop_distance(v0, big)
    assert abs(float(np.linalg.norm(pr["p_end"])) - d_cf) / d_cf < 1e-9
    assert abs(d_cf - B.slide_stop_distance(v0, 0.02)) / d_cf < 1e-12
    assert pr["events"] == ["stop"]


def test_wall_bounce_energy_ratio_and_components():
    b1 = PK.puck_wall_bounce((0.0, -1.3), (0, 1), 0.8, 0.9)
    assert abs(b1["energy_ratio"] - 0.64) < 1e-12
    b2 = PK.puck_wall_bounce((0.7, -1.3), (0, 1), 0.8, 0.9)
    assert abs(b2["vn_out"] - 0.8 * 1.3) < 1e-12 and abs(b2["vt_out"] - 0.9 * 0.7) < 1e-12
    assert abs(b2["v"][1] - 0.8 * 1.3) < 1e-12 and abs(b2["v"][0] - 0.9 * 0.7) < 1e-12
    b3 = PK.puck_wall_bounce((0.7, 1.3), (0, 1), 0.8, 0.9)             # 離れていく → 何もしない
    assert np.allclose(b3["v"], (0.7, 1.3)) and b3["energy_ratio"] == 1.0


def test_mirror_method_equals_the_segment_predictor():
    tb1 = PK.puck_table(mu=0.0, e=1.0, kt=1.0)
    rng = np.random.default_rng(3)
    worst, nb = 0.0, 0
    cases = [(rng.uniform([-0.9, -0.45], [0.9, 0.45]), rng.uniform([-3, -3], [3, 3]), rng.uniform(0.2, 4.0)) for _ in range(100)]
    assert len(cases) == 100
    for p0, v, T in cases:
        pr = PK.puck_slide_predict(p0, v, tb1, T, model="none", goals=False)
        worst = max(worst, float(np.abs(pr["p_end"] - PK.puck_mirror_path(p0, v, tb1, T)).max()))
        nb = max(nb, pr["n_bounces"])
    assert worst < 1e-9 and nb >= 5


def test_closed_form_is_self_consistent_and_matches_euler(tb):
    pr = PK.puck_slide_predict((0.3, 0.1), (-1.6, 0.9), tb, 3.0)
    c = PK.puck_crossing_point(pr, X_DEF)
    assert c is not None and abs(PK.puck_state_at(pr, c["t"])["p"][0, 0] - X_DEF) < 1e-12
    h = 1e-6
    tt = np.array([0.1, 0.3, 0.6, 0.9])
    vnum = (PK.puck_state_at(pr, tt + h)["p"] - PK.puck_state_at(pr, tt - h)["p"]) / (2 * h)
    assert float(np.abs(vnum - PK.puck_state_at(pr, tt)["v"]).max()) < 1e-6
    dt = 2e-5
    p, v = np.array([0.3, 0.1]), np.array([-1.6, 0.9])
    r = tb["puck_radius"]
    xb, yb = tb["x_half"] - r, tb["y_half"] - r
    t = 0.0
    while t < 1.0 - 1e-12:
        s = np.linalg.norm(v)
        if s > 0:
            v = v - min(tb["mu"] * tb["g"] * dt, s) * v / s
        p = p + v * dt
        for ax, bd in ((0, xb), (1, yb)):
            if abs(p[ax]) > bd:
                p[ax] = np.sign(p[ax]) * (2 * bd - abs(p[ax]))
                n = np.zeros(2)
                n[ax] = -np.sign(p[ax])
                v = PK.puck_wall_bounce(v, n, tb["e"], tb["kt"])["v"]
        t += dt
    assert float(np.linalg.norm(p - PK.puck_state_at(pr, 1.0)["p"][0])) < 4e-4
    st = PK.puck_state_at(pr, [5.0, 9.0])                                   # 終端より後は終端の状態のまま
    assert np.allclose(st["p"][0], st["p"][1]) and np.allclose(st["p"][0], pr["p_end"]) and np.allclose(st["v"][0], pr["v_end"])


def test_viscous_model_decays_exponentially_and_matches_euler():
    tb = PK.puck_table(mu=0.0, damping=0.005, mass=0.01, x_half=100.0, y_half=100.0)
    pr = PK.puck_slide_predict((0, 0), (1.0, 0.0), tb, 2.0, model="viscous")
    st = PK.puck_state_at(pr, [0.5, 1.0, 2.0])
    k = 0.5
    assert np.allclose(st["v"][:, 0], np.exp(-k * np.array([0.5, 1.0, 2.0])), atol=1e-12)
    assert np.allclose(st["p"][:, 0], (1 - np.exp(-k * np.array([0.5, 1.0, 2.0]))) / k, atol=1e-12)
    dt, p, v = 1e-4, 0.0, 1.0
    for _ in range(int(round(2.0 / dt))):
        v = v - k * v * dt
        p = p + v * dt
    assert abs(p - st["p"][2, 0]) < 2e-4


# ── 2. 5 節リンク ─────────────────────────────────────────────────────────

def test_fivebar_fk_ik_identity_on_the_workspace(link):
    ws = PK.fivebar_workspace(link, n=41)
    pts = np.argwhere(ws["mask"])
    assert len(pts) >= 100
    rng = np.random.default_rng(1)
    worst = 0.0
    for iy, ix in pts[rng.choice(len(pts), 100, replace=False)]:
        E = np.array([ws["xs"][ix], ws["ys"][iy]])
        worst = max(worst, float(np.linalg.norm(PK.fivebar_fk(PK.fivebar_ik(E, link), link)["E"] - E)))
    assert worst < 1e-9
    assert ws["area"] > 0.05 and ws["x_max"] > link["base"][0]


def test_fivebar_ik_is_none_outside_reach_and_the_boundary_is_sharp(link):
    reach = link["l1"] + link["l2"]
    far = link["A1"] + np.array([reach + 1e-3, 0.0])
    assert PK.fivebar_ik(far, link) is None
    angs = np.linspace(0.35, 0.9, 7)
    assert len(angs) == 7
    for ang in angs:
        u = np.array([np.cos(ang), np.sin(ang)])
        assert PK.fivebar_ik(link["A1"] + (reach - 1e-6) * u, link) is not None
        assert PK.fivebar_ik(link["A1"] + (reach + 1e-6) * u, link) is None
    with pytest.raises(ValueError):
        PK.fivebar_ik((-0.75, 0.0), link, branch="outt")
    with pytest.raises(ValueError):
        PK.fivebar_fk((0.3, 2.0), link, branch="forwad")


def test_reach_interval_on_the_defence_line_leaves_the_corners(link, tb):
    ri = PK.fivebar_reach_interval(link, X_DEF)
    yb = tb["y_half"] - tb["puck_radius"]
    assert ri["ok"] and 0.3 < ri["y_hi"] < yb and abs(ri["y_lo"] + ri["y_hi"]) < 1e-9          # 対称、隅は届かない(正直)


# ── 3. 検出・追跡 ─────────────────────────────────────────────────────────

def test_detection_centroid_matches_the_truth(tb, cam):
    rng = np.random.default_rng(2)
    errs = []
    for _ in range(20):
        p0 = rng.uniform([-0.9, -0.45], [0.9, 0.45])
        d = PK.puck_detect(PK.puck_render_frame(cam, p0), cam)
        tp = PK.puck_world_to_pixel(cam, [p0])[0]
        errs.append((d["col"] - tp[0], d["row"] - tp[1]))
    errs = np.array(errs)
    assert errs.shape == (20, 2) and float(np.abs(errs).max()) < 0.05
    assert PK.puck_detect(PK.puck_render_frame(cam, (0.3, 0.1)), cam, radius_tol=0.01) is None       # 半径の門で落ちる → None


def test_detection_threshold_bias_is_as_measured(tb, cam):
    """しきい値が台の値から遠いほど縁の画素が切れて偏る(docstring の実測): 0.5 の偏りは 0.85 の偏りより大きい。"""
    rng = np.random.default_rng(5)
    worst = {0.5: 0.0, 0.85: 0.0}
    pos = [rng.uniform([-0.9, -0.45], [0.9, 0.45]) for _ in range(12)]
    assert len(pos) == 12
    for p0 in pos:
        fr = PK.puck_render_frame(cam, p0)
        tp = PK.puck_world_to_pixel(cam, [p0])[0]
        for th in worst:
            d = PK.puck_detect(fr, cam, thresh=th)
            worst[th] = max(worst[th], float(np.hypot(d["col"] - tp[0], d["row"] - tp[1])))
    assert worst[0.85] < 0.02 and worst[0.5] > 2 * worst[0.85]


def test_fast_puck_breaks_the_tracking_above_max_jump(tb, cam):
    found = {}
    for step_px in (20.0, 45.0):
        sp = step_px / cam["px_per_m"] * FPS
        syn = PK.puck_synth_frames(tb, cam, (0.8, 0.0), (-sp, 0.0), fps=FPS, n_frames=8)
        found[step_px] = int(PK.puck_track(syn["frames"], cam, max_jump_px=40.0)["found"].sum())
    assert found[20.0] == 8 and found[45.0] < 8


def test_kalman_ca_innovation_vanishes_on_the_exact_coulomb_path(tb, cam):
    syn = PK.puck_synth_frames(tb, cam, (0.5, 0.0), (-1.2, 0.3), fps=FPS, n_frames=30)
    kf = BT.kalman_ca(syn["truth_xy"], 1.0 / FPS, q=1e-3, r=1e-12)
    assert float(np.abs(kf["innovation"][10:]).max()) < 1e-6


# ── 4. 推定 ───────────────────────────────────────────────────────────────

def test_velocity_estimate_exact_and_from_noisy_detections(tb, cam):
    rng = np.random.default_rng(4)
    syn = PK.puck_synth_frames(tb, cam, (0.4, 0.15), (-1.4, 0.55), fps=FPS, n_frames=24, noise=0.01, rng=rng)
    ve = PK.puck_velocity_estimate(syn["t"], syn["truth_xy"], tb)
    assert float(np.linalg.norm(ve["v_ref"] - syn["truth_v"][-1])) < 1e-9
    tr = PK.puck_track(syn["frames"], cam)
    assert tr["frame"].size == 24
    ve12 = PK.puck_velocity_estimate(syn["t"][:12], tr["xy"][:12], tb)
    err = float(np.linalg.norm(ve12["v_ref"] - syn["truth_v"][11]))
    assert err < 3 * np.sqrt(2) * ve12["sigma_v"] + 1e-4 and err / float(np.hypot(1.4, 0.55)) < 0.01
    with pytest.raises(ValueError):
        PK.puck_velocity_estimate([0, 1], [[0, 0], [1, 1]], tb)


def test_crossing_point_from_noisy_detections(tb, cam):
    rng = np.random.default_rng(6)
    errs = []
    for _ in range(6):
        p0 = rng.uniform([0.3, -0.3], [0.8, 0.3])
        ang = rng.uniform(-0.5, 0.5)
        v0 = rng.uniform(1.0, 2.0) * np.array([-np.cos(ang), np.sin(ang)])
        truth_c = PK.puck_crossing_point(PK.puck_slide_predict(p0, v0, tb, 6.0), X_DEF)
        assert truth_c is not None
        syn = PK.puck_synth_frames(tb, cam, p0, v0, fps=FPS, n_frames=12, noise=0.01, rng=rng)
        tr = PK.puck_track(syn["frames"], cam)
        ve = PK.puck_velocity_estimate(syn["t"][tr["frame"]], tr["xy"], tb)
        c = PK.puck_crossing_point(PK.puck_slide_predict(ve["p_ref"], ve["v_ref"], tb, 6.0, t0=ve["t_ref"]), X_DEF)
        assert c is not None
        errs.append(abs(c["p"][1] - truth_c["p"][1]))
    assert len(errs) == 6 and max(errs) < 0.01


def test_mu_from_deceleration(tb, cam):
    syn = PK.puck_synth_frames(tb, cam, (0.5, 0.0), (-1.2, 0.2), fps=FPS, n_frames=36)
    assert abs(PK.puck_mu_from_decel(syn["t"], syn["truth_xy"], tb["g"])["mu"] - tb["mu"]) < 1e-9
    tr = PK.puck_track(syn["frames"], cam)
    assert abs(PK.puck_mu_from_decel(syn["t"], tr["xy"], tb["g"])["mu"] - tb["mu"]) / tb["mu"] < 0.10
    with pytest.raises(ValueError):
        PK.puck_mu_from_decel([0, 1, 2], [[0, 0], [1, 0], [2, 0]])


def test_restitution_from_a_wall_bounce(tb, cam):
    syn = PK.puck_synth_frames(tb, cam, (0.3, 0.30), (-1.0, 1.2), fps=FPS, n_frames=30)
    ex = PK.puck_restitution_from_wall(syn["t"], syn["truth_xy"], tb)
    assert abs(ex["e"] - tb["e"]) < 1e-6 and abs(ex["kt"] - tb["kt"]) < 1e-6 and ex["wall"] == "y+"
    tr = PK.puck_track(syn["frames"], cam)
    rw = PK.puck_restitution_from_wall(syn["t"][tr["frame"]], tr["xy"], tb)
    assert abs(rw["e"] - tb["e"]) / tb["e"] < 0.02 and abs(rw["kt"] - tb["kt"]) / tb["kt"] < 0.03
    with pytest.raises(ValueError):
        PK.puck_restitution_from_wall(syn["t"][:5], syn["truth_xy"][:5], tb)


# ── 5. 計画 ───────────────────────────────────────────────────────────────

def test_striker_plan_reaches_in_time_or_declines_honestly(tb, link):
    q0 = PK.fivebar_ik((X_DEF, 0.0), link)
    c = PK.puck_crossing_point(PK.puck_slide_predict((0.5, 0.1), (-1.5, 0.3), tb, 4.0), X_DEF)
    plan = PK.striker_plan(c, q0, link, omega_max=6.0)
    assert plan["feasible"] and plan["reason"] == "ok" and plan["t_arrive"] <= c["t"]
    assert float(np.linalg.norm(PK.fivebar_fk(plan["q_target"], link)["E"] - c["p"])) < 1e-9
    tq = np.linspace(0, plan["t_cross"], 200)
    Q = PK.fivebar_trajectory(q0, plan, tq)
    assert Q.shape == (200, 2) and float(np.abs(np.diff(Q, axis=0) / np.diff(tq)[:, None]).max()) <= 6.0 * (1 + 1e-9)
    assert np.allclose(Q[-1], plan["q_target"])
    fast = PK.striker_plan(PK.puck_crossing_point(PK.puck_slide_predict((-0.3, 0.3), (-8.0, -1.0), tb, 4.0), X_DEF), q0, link)
    assert fast["reason"] == "too_late"
    corner = PK.striker_plan({"t": 5.0, "p": np.array([X_DEF, 0.47]), "v": np.zeros(2)}, q0, link)
    assert corner["reason"] == "unreachable"
    assert PK.striker_plan(None, q0, link)["reason"] == "no_crossing"
    assert np.allclose(PK.fivebar_trajectory(q0, PK.striker_plan(None, q0, link), [0.0, 1.0]), q0)


# ── 6. 合成・針穴・MJCF・綴り ─────────────────────────────────────────────

def test_motion_blur_moves_the_centroid_by_half_the_blur(tb, cam):
    v = np.array([-1.6, 0.0])
    blurs = (0.0, 2.0, 5.0, 10.0, 20.0)
    assert len(blurs) == 5
    for blur_px in blurs:
        tau = blur_px / (np.linalg.norm(v) * cam["px_per_m"])
        p0 = np.array([0.2, 0.05])
        d = PK.puck_detect(PK.puck_render_frame(cam, p0, v=v, exposure=tau), cam, radius_tol=1.5)
        tp = PK.puck_world_to_pixel(cam, [p0])[0]
        assert abs((d["col"] - tp[0]) - (-blur_px / 2.0)) < 0.1
    with pytest.raises(ValueError):
        PK.puck_render_frame(cam, (0.2, 0.05), exposure=0.01)


def test_pinhole_camera_round_trip_and_centre(tb):
    cm = PK.puck_pinhole_camera(tb, 1.5, 50.0, (480, 800))
    assert np.allclose(PK.puck_world_to_pixel(cm, [[0.0, 0.0]])[0], (400.0, 240.0))
    pts = np.array([[0.3, 0.2], [-0.9, -0.4], [0.0, 0.5]])
    assert np.allclose(PK.puck_pixel_to_world(cm, PK.puck_world_to_pixel(cm, pts)), pts, atol=1e-12)
    assert abs(cm["px_per_m"] - (240.0 / np.tan(np.deg2rad(25.0))) / 1.5) < 1e-12
    with pytest.raises(ValueError):
        PK.puck_pinhole_camera(tb, 0.0, 50.0, (480, 800))


def test_synth_frames_carry_consistent_truth(tb, cam):
    syn = PK.puck_synth_frames(tb, cam, (0.4, 0.15), (-1.4, 0.55), fps=FPS, n_frames=5)
    assert len(syn["frames"]) == 5 and syn["frames"][0].shape == cam["shape"]
    assert np.allclose(syn["truth_px"], PK.puck_world_to_pixel(cam, syn["truth_xy"]))
    assert np.allclose(PK.puck_state_at(syn["pred"], syn["t"])["p"], syn["truth_xy"])


def test_scene_mjcf_string_has_the_parts(tb):
    xml = PK.puck_scene_mjcf(tb)
    assert xml.count("<geom name=") == 6 and 'camera name="top"' in xml and 'friction="%g' % tb["mu"] in xml
    with pytest.raises(ValueError):
        PK.puck_scene_mjcf(tb, fovy=0.0)


def test_spelling_breaks_fail_closed(tb, cam, link):
    with pytest.raises(ValueError):
        PK.puck_slide_predict((0, 0), (1, 0), tb, 1.0, model="Coulumb")
    with pytest.raises(ValueError):
        PK.puck_detect(PK.puck_render_frame(cam, (0, 0)), cam, mode="drak")
    with pytest.raises(ValueError):
        PK.puck_table(e=1.2)
    with pytest.raises(ValueError):
        PK.puck_slide_predict((2.0, 0.0), (1, 0), tb, 1.0)
    with pytest.raises(ValueError):
        PK.puck_wall_bounce((1, 0), (0, 0), 0.8)
    with pytest.raises(ValueError):
        PK.puck_stop_distance(1.0, PK.puck_table(mu=0.0))
    with pytest.raises(ValueError):
        PK.striker_plan(None, (0, 0), link, omega_max=0.0)
    assert PK.puck_crossing_point(PK.puck_slide_predict((0, 0), (0.3, 0.0), tb, 5.0), X_DEF) is None


# ── 7. MuJoCo ─────────────────────────────────────────────────────────────

def test_own_coulomb_mjcf_decelerates_at_mu_g():
    pytest.importorskip("mujoco")
    tb_c = PK.puck_table(mu=0.05, e=0.8, kt=0.9)
    run = PK.puck_mujoco_run(PK.puck_scene_mjcf(tb_c), None, (-0.5, 0.0), (1.0, 0.0), fps=1000.0, duration=1.0, render=False, puck_joint="puck_free")
    s = np.hypot(run["v"][:, 0], run["v"][:, 1])
    m = (run["t"] > 0.05) & (s > 0.2)
    assert m.sum() > 100
    a_fit = -np.polyfit(run["t"][m], s[m], 1)[0]
    assert abs(a_fit - tb_c["mu"] * tb_c["g"]) / (tb_c["mu"] * tb_c["g"]) < 0.05        # 軟接触の摩擦は厳密な Coulomb でない(実測 3.3 %)
    with pytest.raises(ValueError):
        PK.puck_mujoco_run(PK.puck_scene_mjcf(tb_c), None, (0, 0), (1, 0), fps=1000.0, duration=0.1, render=False, puck_joint="puck_fre")


@pytest.mark.skipif(not os.environ.get("FULLSEYE_AIRHOCKEY_DATA"), reason="FULLSEYE_AIRHOCKEY_DATA が未設定(Challenge の table.xml は repo の外)")
def test_challenge_table_is_viscous_not_coulomb():
    pytest.importorskip("mujoco")
    xml, assets = PK.puck_challenge_mjcf()
    run = PK.puck_mujoco_run(xml, assets, (0.0, 0.0), (0.3, 1.0), fps=1000.0, duration=1.0, render=False)
    s = np.hypot(run["v"][:, 0], run["v"][:, 1])
    i_b = int(np.argmax(np.abs(np.diff(run["v"][:, 1])) > 0.05))
    assert i_b > 100
    slope = np.polyfit(run["t"][: i_b - 2], np.log(s[: i_b - 2]), 1)[0]
    assert abs(slope + 0.5) / 0.5 < 0.01                                   # c/m = 0.005 / 0.01
    tb_v = PK.puck_table(damping=0.005, mass=0.01)
    st = PK.puck_state_at(PK.puck_slide_predict((0.0, 0.0), (0.3, 1.0), tb_v, 1.0, model="viscous"), run["t"][: i_b - 2])
    assert float(np.linalg.norm(st["p"] - run["xy"][: i_b - 2], axis=1).max()) < 1e-3


@pytest.mark.skipif(not os.environ.get("FULLSEYE_AIRHOCKEY_DATA"), reason="FULLSEYE_AIRHOCKEY_DATA が未設定(Challenge の table.xml は repo の外)")
def test_mujoco_render_detect_pinhole_against_truth():
    pytest.importorskip("mujoco")
    xml, assets = PK.puck_challenge_mjcf()
    tb_v = PK.puck_table(damping=0.005, mass=0.01)
    cm = PK.puck_pinhole_camera(tb_v, 1.5, 50.0, (480, 800))
    run = PK.puck_mujoco_run(xml, assets, (0.3, 0.2), (-1.2, 0.4), fps=50.0, duration=0.2, render=True, shape=(480, 800))
    det = [PK.puck_detect(f.astype(np.float64) / 255.0, cm, mode="color", color=(1.0, 0.32, 0.32), color_tol=0.45, radius_tol=0.6) for f in run["frames"]]
    assert len(det) == 10 and all(d is not None for d in det)
    dxy = np.array([[d["x"], d["y"]] for d in det]) - run["xy"]
    bias = dxy.mean(0)
    assert float(np.linalg.norm(bias)) < 5e-3 and float(np.sqrt(np.mean((dxy - bias) ** 2))) < 1.5e-3
