# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""運転の世界を歩くヒューマノイド(drivehumanoid、2026-10-03)の門。

* 間引き: 頂点のずれ ≤ √3·格子幅(格子にまとめた代表は同じ升の中 = 定理)、三角形 ≤ 予算。
* 歩行: 関節の役割は**名前でなく体の形**から(わざと意味の無い名前の体で確かめる)。毎コマ接地(最低点 = 0)、
  前に進む、**支持脚が地面で滑らない**(同じ頂点の世界の x がほぼ動かない)。膝の曲がる向きが逆の体は向きを反転して前へ。
* 事前描画(インポスタ): 方位と位相が段にちょうど乗るとき、直接メッシュで描いたマスクとの一致度 ≥ 0.85。手前の壁に隠れる。
"""
import math

import numpy as np
import pytest

import drivehumanoid as H
import driveterrain as DT
import driveworld as DW


def _box_clip(T=8):
    ms = [DT.pedestrian_mesh(1.7, stride=0.4 * np.sin(2 * np.pi * k / T)) for k in range(T)]
    return {"V": np.stack([m["V"] for m in ms]), "F": ms[0]["F"], "color": ms[0]["color"], "label": 7,
            "dims": ms[0]["dims"], "advance": np.linspace(0, 1.2, T, endpoint=False), "cycle_length": 1.2}


def _ground_world():
    w = DW._empty_world()
    V, F = DW._grid_plane(-30, 30, -30, 30, step=4.0)
    DW.world_add(w, V, F, 0, np.tile([.4, .4, .4], (len(F), 1)), name="ground")
    return w


# ── 再生(mujoco 不要) ─────────────────────────────────────────────────────────────── #
def test_clip_mesh_is_periodic_and_continuous():
    c = _box_clip()
    a = H.humanoid_clip_mesh(c, 0.3)["V"]
    b = H.humanoid_clip_mesh(c, 0.3 + c["cycle_length"])["V"]
    assert np.allclose(a, b)
    e1 = H.humanoid_clip_mesh(c, 0.5)["V"]
    e2 = H.humanoid_clip_mesh(c, 0.5 + 1e-6)["V"]
    assert np.abs(e1 - e2).max() < 1e-4                                  # 補間なので跳ばない
    with pytest.raises(ValueError):
        H.humanoid_clip_mesh(dict(c, cycle_length=0.0), 0.1)


def test_world_pose_humanoid_rewrites_only_that_object():
    c = _box_clip()
    w = _ground_world()
    i = DT.add_mesh_object(w, H.humanoid_clip_mesh(c, 0.0), 2.0, 1.0, 0.0, name="h")
    ground = w["V"][:w["objects"][0]["verts"][1]].copy()
    H.world_pose_humanoid(w, i, c, 0.45, 3.0, -1.0, 1.2)
    v0, v1 = w["objects"][i]["verts"]
    want = DW.place_mesh(H.humanoid_clip_mesh(c, 0.45)["V"], 3.0, -1.0, 1.2)
    assert np.allclose(w["V"][v0:v1], want)
    assert np.array_equal(w["V"][:len(ground)], ground)
    other = DT.pedestrian_mesh(1.7)
    j = DT.add_mesh_object(w, other, 0, 0, 0)
    with pytest.raises(ValueError, match="頂点数"):
        H.world_pose_humanoid(w, j, dict(c, V=c["V"][:, :-1]), 0.1, 0, 0, 0)


# ── 事前描画(インポスタ) ────────────────────────────────────────────────────────── #
@pytest.mark.parametrize("yaw_bin,dist", [(0, 6.0), (3, 9.0), (10, 7.0)])
def test_impostor_matches_the_direct_render_on_the_bins(yaw_bin, dist):
    c = _box_clip()
    imp = H.humanoid_impostors(c, n_yaw=16, n_phase=8, res=160)
    K = DW.camera_intrinsics(60, 640, 400)
    eye = np.array([-dist, 0.0, imp["eye_h"]])
    pose = DW.camera_pose(eye, (0.0, 0.0, imp["eye_h"]))
    yaw = math.pi - 2 * math.pi * yaw_bin / 16                          # 体から見たカメラの方位 = 段 yaw_bin
    s = imp["phase_s"][3]
    w = _ground_world()
    DT.add_mesh_object(w, H.humanoid_clip_mesh(c, s), 0.0, 0.0, yaw)
    a = DW.world_camera(w, pose, K, 640, 400)["label"] == 7
    b = H.world_camera_impostors(_ground_world(), pose, K, 640, 400,
                                 [{"imp": imp, "x": 0.0, "y": 0.0, "yaw": yaw, "distance": s}])["label"] == 7
    assert a.sum() > 600
    iou = (a & b).sum() / (a | b).sum()
    assert iou >= 0.85, iou


def test_impostor_is_hidden_behind_a_nearer_wall():
    c = _box_clip()
    imp = H.humanoid_impostors(c, n_yaw=8, n_phase=4, res=96)
    K = DW.camera_intrinsics(60, 480, 320)
    pose = DW.camera_pose((-10.0, 0.0, 1.0), (0.0, 0.0, 1.0))
    act = [{"imp": imp, "x": 0.0, "y": 0.0, "yaw": 0.0, "distance": 0.0}]
    seen = H.world_camera_impostors(_ground_world(), pose, K, 480, 320, act)
    assert seen["impostor_pixels"] > 200
    w = _ground_world()
    DW.world_add(w, *_wall(-4.0), 3, (0.7, 0.7, 0.7), name="wall")
    hid = H.world_camera_impostors(w, pose, K, 480, 320, act)
    assert hid["impostor_pixels"] == 0
    behind = H.world_camera_impostors(_ground_world(), DW.camera_pose((10.0, 0.0, 1.0), (20.0, 0.0, 1.0)), K, 480,
                                      320, act)
    assert behind["impostor_pixels"] == 0                                  # カメラの後ろは貼らない


def _wall(x):
    V = np.array([[x, -3, 0], [x, 3, 0], [x, 3, 3], [x, -3, 3]], np.float64)
    return V, np.array([[0, 1, 2], [0, 2, 3]])


# ── MJCF からの歩行(mujoco が要る) ──────────────────────────────────────────────── #
def _robot_xml(knee_range="0 2.4"):
    """意味の無い名前(j1 …)の小さな人型。基本形状だけ(メッシュ不要)。"""
    leg = '''
      <body name="t{s}" pos="0 {y} -0.05">
        <joint name="a{s}" type="hinge" axis="1 0 0" range="-0.5 0.5"/>
        <joint name="b{s}" type="hinge" axis="0 1 0" range="-1.5 1.5"/>
        <geom type="capsule" fromto="0 0 0 0 0 -0.4" size="0.05"/>
        <body name="s{s}" pos="0 0 -0.4">
          <joint name="c{s}" type="hinge" axis="0 1 0" range="{kr}"/>
          <geom type="capsule" fromto="0 0 0 0 0 -0.4" size="0.04"/>
          <body name="f{s}" pos="0 0 -0.4">
            <joint name="d{s}" type="hinge" axis="0 1 0" range="-1 1"/>
            <geom type="box" pos="0.05 0 -0.03" size="0.1 0.04 0.03"/>
          </body>
        </body>
      </body>'''
    arm = '''
      <body name="u{s}" pos="0 {y} 0.45">
        <joint name="e{s}" type="hinge" axis="0 1 0" range="-2 2"/>
        <geom type="capsule" fromto="0 0 0 0 0 -0.3" size="0.035"/>
        <body name="l{s}" pos="0 0 -0.3">
          <joint name="g{s}" type="hinge" axis="0 1 0" range="-2.5 0"/>
          <geom type="capsule" fromto="0 0 0 0 0 -0.25" size="0.03"/>
        </body>
      </body>'''
    legs = leg.format(s="1", y=0.1, kr=knee_range) + leg.format(s="2", y=-0.1, kr=knee_range)
    arms = arm.format(s="3", y=0.22) + arm.format(s="4", y=-0.22)
    return '''<mujoco><compiler angle="radian"/><worldbody><light pos="0 0 3"/>
    <body name="pelvis" pos="0 0 0.95"><freejoint/>
      <geom type="box" pos="0 0 0.25" size="0.1 0.15 0.25"/>
      <geom type="sphere" pos="0 0 0.62" size="0.1"/>%s%s
    </body></worldbody></mujoco>''' % (legs, arms)


@pytest.mark.parametrize("knee_range,facing", [("0 2.4", 1.0), ("-2.4 0", -1.0)])
def test_walk_clip_finds_joints_by_shape_and_does_not_slip(tmp_path, knee_range, facing):
    pytest.importorskip("mujoco")
    p = tmp_path / "bot.xml"
    p.write_text(_robot_xml(knee_range), encoding="utf-8")
    c = H.humanoid_walk_clip(str(p), n_frames=24, tri_budget=400)
    assert c["facing"] == facing
    assert {"left_hip", "left_knee", "left_ankle", "right_hip", "right_knee", "right_ankle",
            "left_shoulder", "left_elbow", "right_shoulder", "right_elbow"} <= set(c["joints"])
    V = c["V"]
    assert np.allclose(V[:, :, 2].min(axis=1), 0.0)                       # 毎コマ接地
    assert c["cycle_length"] > 0.3                                        # 前へ進む(腿の振り 0.35 rad × 脚 0.8 m)
    # 支持脚: 2 コマ続けて地面にある頂点の世界の x はほぼ動かない(進んだ量の 15 % 以下)
    slips, steps = [], []
    for k in range(len(V) - 1):
        s0, s1 = c["advance"][k], c["advance"][k + 1]
        a = H.humanoid_clip_mesh(c, s0)["V"] + [s0, 0, 0]
        b = H.humanoid_clip_mesh(c, s1 - 1e-9)["V"] + [s1, 0, 0]
        on = (a[:, 2] < 0.01) & (b[:, 2] < 0.01)
        if on.any() and s1 > s0:
            slips.append(np.median(np.abs(b[on, 0] - a[on, 0])))
            steps.append(s1 - s0)
    assert len(slips) > 8
    assert np.median(slips) <= 0.15 * np.median(steps) + 1e-3, (np.median(slips), np.median(steps))


def test_decimation_shift_is_bounded_by_the_cell_diagonal(tmp_path):
    pytest.importorskip("mujoco")
    p = tmp_path / "bot.xml"
    p.write_text(_robot_xml(), encoding="utf-8")
    full = H.humanoid_walk_clip(str(p), n_frames=4, tri_budget=10 ** 6)
    small = H.humanoid_walk_clip(str(p), n_frames=4, tri_budget=300)
    d = small["decimation"]
    assert full["decimation"]["tris_after"] == full["decimation"]["tris_before"] > 300
    assert 0 < d["tris_after"] <= 300 < d["tris_before"]
    assert d["geoms_dropped"] == 0                                        # 予算に収めるために部品を丸ごと消していない
    assert 0 < d["max_vertex_shift"] <= math.sqrt(3) * d["cell"] + 1e-12


def test_walk_clip_refuses_a_body_without_a_floating_base(tmp_path):
    pytest.importorskip("mujoco")
    p = tmp_path / "arm.xml"
    p.write_text('<mujoco><worldbody><body><joint type="hinge"/><geom type="sphere" size="0.1"/></body>'
                 '</worldbody></mujoco>', encoding="utf-8")
    with pytest.raises(ValueError, match="自由関節"):
        H.humanoid_walk_clip(str(p))
