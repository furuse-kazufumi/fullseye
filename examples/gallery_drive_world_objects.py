# -*- coding: utf-8 -*-
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gallery_drive_world_objects — 世界に置いた物体を動かす op(けん玉・糸・歩く人)を、剛体の不変量と閉形式の投影で確かめる

    py -3.11 examples/gallery_drive_world_objects.py

【平たく言うと】
運転の世界(driveworld の三角形の束)には、毎コマ姿勢を変える物体がいる: けん玉のけんと糸(kendamaworld)、
横断歩道を歩く人(drivehumanoid)。これらの op は「頂点だけ書き換える」約束で動く —— 面の数・色・ラベルは
変えず、ほかの物体には触らない。ここではその約束と、姿勢の式(頂点 = 局所 @ Rᵀ + p)、カメラに写る真値の
位置(ピンホールの閉形式)を 1 本ずつ確かめる。

【何を期待し、何と比べるか】
  * string_mesh        : 糸 = 8 頂点 12 面の閉じた角柱(境界辺 0)、体積 = (2r)²·L、両端の重心 = 2 つの糸穴。
  * add_ken            : 頂点 = ken_mesh の局所頂点 @ Rᵀ + p(R = y 軸まわり 30°)、面ラベル 27/28/30/31 がそのまま写る。
  * ken_set_pose       : 姿勢を変えても頂点数・面数は不変、ほかの物体(玉)の頂点はビット一致のまま。
  * ken_truth          : 大皿の縁の中心 = p + R·(0, 0, 35 mm)、像の (col, row) = 自前のピンホール投影、
                         皿の半径 [px] = f·21 mm / 深度。背を向けたカメラでは visible = False。けんでない物体は拒む。
  * add_string         : ラベル 29・12 面・糸の色。
  * string_set         : 両端の重心が新しい糸穴に移り、長さが更新される。糸でない物体は拒む。
  * world_pose_humanoid: 歩いた距離 d の姿勢を (x, y, yaw) に置く: 頂点 = R(yaw)·局所 + (x, y)(自前の回転で検算)、
                         剛体なので頂点間の距離はクリップのその距離の形と一致、1 周期ぶん先(d + 周期長)は同じ形、
                         ほかの物体は不変。頂点数の違うクリップは拒む。

正直に: 歩く人のクリップは関節のある本物の歩行(MJCF から作る humanoid_walk_clip)ではなく、driveterrain の
歩行者メッシュの歩幅を周期的に変えた箱の人形で、ここで確かめるのは「置き直しの約束」まで。支持脚が滑らないことは
examples/poc_driving_humanoids.py と tests/test_drivehumanoid.py が本物の体で確かめる。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import drivecourse  # noqa: E402
import drivehumanoid as DH  # noqa: E402
import driveterrain as DT  # noqa: E402
import driveworld as DW  # noqa: E402
import kendama as KD  # noqa: E402
import kendamaworld as KW  # noqa: E402

_ROWS = []


def check(op, what, expected, got, ok):
    """1 行 = 何を期待し、何が出て、合ったか。"""
    _ROWS.append((op, bool(ok)))
    print("  %-19s %-50s 期待 %-24s 実測 %-24s %s" % (op, what, expected, got, "ok" if ok else "NG"))


def _boundary_edges(F):
    E = np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1)
    _, cnt = np.unique(E, axis=0, return_counts=True)
    return int((cnt != 2).sum())


def _signed_volume(V, F):
    return float(np.einsum("ij,ij->i", V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum() / 6.0)


def _pairwise(V, idx):
    P = V[idx]
    return np.linalg.norm(P[:, None, :] - P[None, :, :], axis=2)


def _ry(deg):
    a = math.radians(deg)
    return np.array([[math.cos(a), 0.0, math.sin(a)], [0.0, 1.0, 0.0], [-math.sin(a), 0.0, math.cos(a)]])


def part_string_mesh():
    print("== 1. 糸のメッシュ")
    r = 0.0015
    for a, b in (([0.0, 0.0, 0.6], [0.0, 0.0, 1.0]), ([0.1, -0.2, 0.7], [0.0, 0.05, 1.02])):
        V, F = KW.string_mesh(a, b, radius=r)
        L = float(np.linalg.norm(np.subtract(b, a)))
        vol = _signed_volume(V, F)
        check("string_mesh", "L = %.4f m: 8 頂点 12 面・境界辺 0" % L, "8・12・0",
              "%d・%d・%d" % (len(V), len(F), _boundary_edges(F)), len(V) == 8 and len(F) == 12 and _boundary_edges(F) == 0)
        check("string_mesh", "L = %.4f m: 体積 = (2r)²·L(外向き)" % L, "%.4e m³" % ((2 * r) ** 2 * L), "%.4e m³" % vol,
              abs(vol - (2 * r) ** 2 * L) < 1e-15)
        check("string_mesh", "L = %.4f m: 両端の重心 = 糸穴" % L, "差 0", "%.1e" % max(
            np.abs(V[:4].mean(axis=0) - a).max(), np.abs(V[4:].mean(axis=0) - b).max()),
            np.allclose(V[:4].mean(axis=0), a, atol=1e-12) and np.allclose(V[4:].mean(axis=0), b, atol=1e-12))
    same = False
    try:
        KW.string_mesh([0, 0, 1], [0, 0, 1])
    except ValueError:
        same = True
    check("string_mesh", "両端が一致したら拒む", "ValueError", "ValueError" if same else "通った", same)


def part_ken():
    print("== 2. けん(置く・動かす・カメラの真値)")
    kp = KD.kendama_params()
    world = KW.kendama_world(kp)                          # 床 + けん + 玉 + 糸
    m = KW.ken_mesh(kp)
    p, R = np.array([0.5, 0.3, 0.8]), _ry(30.0)
    i = KW.add_ken(world, m, p, R, name="ken2")
    obj = world["objects"][i]
    v0, v1 = obj["verts"]
    err = float(np.abs(world["V"][v0:v1] - (m["V"] @ R.T + p)).max())
    check("add_ken", "頂点 = 局所 @ Rᵀ + p(y 軸まわり 30°)", "差 < 1e-12", "%.1e" % err, err < 1e-12)
    labs = sorted(set(world["face_label"][slice(*obj["faces"])].tolist()))
    check("add_ken", "面ラベルがそのまま写る", "[27, 28, 30, 31]", str(labs),
          labs == [27, 28, 30, 31] and obj["kind"] == "ken" and obj["label"] == 27)

    ball = world["objects"][world["kendama"]["ball"]]
    ball_V = world["V"][slice(*ball["verts"])].copy()
    nV, nF = len(world["V"]), len(world["F"])
    p2 = np.array([0.0, 0.0, 1.0])
    KW.ken_set_pose(world, i, p2, np.eye(3))
    err2 = float(np.abs(world["V"][v0:v1] - (m["V"] + p2)).max())
    check("ken_set_pose", "姿勢 (p2, I): 頂点 = 局所 + p2", "差 < 1e-12", "%.1e" % err2, err2 < 1e-12)
    check("ken_set_pose", "頂点数・面数は不変、玉の頂点はビット一致", "%d・%d・一致" % (nV, nF),
          "%d・%d・%s" % (len(world["V"]), len(world["F"]),
                         "一致" if np.array_equal(world["V"][slice(*ball["verts"])], ball_V) else "変化"),
          len(world["V"]) == nV and len(world["F"]) == nF and np.array_equal(world["V"][slice(*ball["verts"])], ball_V))
    not_ken = False
    try:
        KW.ken_set_pose(world, world["kendama"]["ball"], p2, np.eye(3))
    except ValueError:
        not_ken = True
    check("ken_set_pose", "けんでない物体(玉)は拒む", "ValueError", "ValueError" if not_ken else "通った", not_ken)

    cam = KW.kendama_rig(kp)[0]
    tr = KW.ken_truth(world, i, cam)
    rim = p2 + np.array([0.0, 0.0, 0.035])                # 大皿の縁の中心(局所 (0, 0, 35 mm))
    T, K = np.asarray(cam["pose"]), np.asarray(cam["K"])
    pc = T[:3, :3] @ rim + T[:3, 3]                       # render3d: カメラは −z を見る、+x 右、+y 上
    depth = -pc[2]
    uv = (K[0, 2] + K[0, 0] * pc[0] / depth, K[1, 2] - K[1, 1] * pc[1] / depth)
    check("ken_truth", "大皿の縁の中心 = p + R·(0, 0, 35 mm)", str(np.round(rim, 4).tolist()), str(np.round(tr["p"], 4).tolist()),
          np.allclose(tr["p"], rim, atol=1e-12))
    check("ken_truth", "像の (col, row) = 自前のピンホール投影", "(%.3f, %.3f)" % uv, "(%.3f, %.3f)" % tuple(tr["uv"]),
          np.allclose(tr["uv"], uv, atol=1e-9) and abs(tr["depth"] - depth) < 1e-12)
    rpx = K[0, 0] * 0.021 / depth
    check("ken_truth", "皿の半径 = f·21 mm / 深度", "%.4f px" % rpx, "%.4f px" % tr["radius_px"],
          abs(tr["radius_px"] - rpx) < 1e-9 and tr["visible"])
    away = {"pose": DW.camera_pose((0.0, -2.0, 1.0), (0.0, -4.0, 1.0)), "K": K, "width": cam["width"],
            "height": cam["height"]}
    check("ken_truth", "背を向けたカメラ", "visible False", str(KW.ken_truth(world, i, away)["visible"]),
          KW.ken_truth(world, i, away)["visible"] is False)
    rej = False
    try:
        KW.ken_truth(world, world["kendama"]["ball"], cam)
    except ValueError:
        rej = True
    check("ken_truth", "けんでない物体(玉)は拒む", "ValueError", "ValueError" if rej else "通った", rej)

    print("== 3. 糸を足す・張り直す")
    pb, pc_ = np.array([0.3, 0.0, 0.6]), np.array([0.3, 0.0, 1.0])
    j = KW.add_string(world, pb, pc_)
    so = world["objects"][j]
    f0, f1 = so["faces"]
    check("add_string", "ラベル 29・12 面・糸の色", "29・12・%s" % (KW.STRING_COLOR,),
          "%d・%d・%s" % (so["label"], f1 - f0, tuple(np.round(world["face_color"][f0], 3).tolist())),
          so["label"] == 29 and f1 - f0 == 12 and np.allclose(world["face_color"][f0:f1], KW.STRING_COLOR)
          and bool(np.all(world["face_label"][f0:f1] == 29)))
    nb, nc = np.array([0.42, 0.1, 0.72]), np.array([0.3, 0.0, 1.0])
    KW.string_set(world, j, nb, nc)
    Vs = world["V"][slice(*so["verts"])]
    L2 = float(np.linalg.norm(nb - nc))
    got_L = float(np.linalg.norm(Vs[4:].mean(axis=0) - Vs[:4].mean(axis=0)))
    check("string_set", "両端の重心が新しい糸穴に・長さ更新", "%.6f m" % L2, "%.6f m" % got_L,
          np.allclose(Vs[:4].mean(axis=0), nb, atol=1e-12) and np.allclose(Vs[4:].mean(axis=0), nc, atol=1e-12)
          and abs(got_L - L2) < 1e-12)
    rej2 = False
    try:
        KW.string_set(world, i, nb, nc)
    except ValueError:
        rej2 = True
    check("string_set", "糸でない物体(けん)は拒む", "ValueError", "ValueError" if rej2 else "通った", rej2)


def _box_clip(T=8):
    """歩幅を周期的に変えた箱の人形のクリップ(mujoco 不要)。"""
    ms = [DT.pedestrian_mesh(1.7, stride=0.4 * np.sin(2 * np.pi * k / T)) for k in range(T)]
    return {"V": np.stack([m["V"] for m in ms]), "F": ms[0]["F"], "color": ms[0]["color"], "label": 7,
            "dims": ms[0]["dims"], "advance": np.linspace(0, 1.2, T, endpoint=False), "cycle_length": 1.2}


def part_humanoid():
    print("== 4. 歩く人を置き直す")
    clip = _box_clip()
    world = DW.world_build(drivecourse.course_road(length=60.0, width=7.0))
    i = DT.add_mesh_object(world, DH.humanoid_clip_mesh(clip, 0.0), 2.0, 1.0, 0.0, name="walker")
    obj = world["objects"][i]
    v0, v1 = obj["verts"]
    road_V = world["V"][:v0].copy()
    nF = len(world["F"])
    d, x, y, yaw = 0.45, 3.0, -1.0, 1.2
    DH.world_pose_humanoid(world, i, clip, d, x, y, yaw)
    Vw = world["V"][v0:v1]
    local = DH.humanoid_clip_mesh(clip, d)["V"]
    c, s = math.cos(yaw), math.sin(yaw)
    want = np.column_stack([c * local[:, 0] - s * local[:, 1] + x, s * local[:, 0] + c * local[:, 1] + y, local[:, 2]])
    err = float(np.abs(Vw - want).max())
    check("world_pose_humanoid", "頂点 = R(yaw)·局所 + (x, y)(自前の回転)", "差 < 1e-12", "%.1e" % err, err < 1e-12)
    idx = np.linspace(0, len(local) - 1, 40).astype(int)
    rig = float(np.abs(_pairwise(Vw, idx) - _pairwise(local, idx)).max())
    check("world_pose_humanoid", "剛体: 頂点間の距離 = 距離 d の形のまま", "差 < 1e-12", "%.1e" % rig, rig < 1e-12)
    same = Vw.copy()
    DH.world_pose_humanoid(world, i, clip, d + clip["cycle_length"], x, y, yaw)
    per = float(np.abs(world["V"][v0:v1] - same).max())
    check("world_pose_humanoid", "1 周期先(d + 1.2 m)は同じ形", "差 < 1e-9", "%.1e" % per, per < 1e-9)
    check("world_pose_humanoid", "道の頂点・面の数・pose の記録", "不変・不変・(3, −1, 1.2)",
          "%s・%s・%s" % ("不変" if np.array_equal(world["V"][:v0], road_V) else "変化",
                         "不変" if len(world["F"]) == nF else "変化", obj["pose"]),
          np.array_equal(world["V"][:v0], road_V) and len(world["F"]) == nF and obj["pose"] == (x, y, yaw))
    bad = False
    try:
        DH.world_pose_humanoid(world, i, dict(clip, V=clip["V"][:, :-1]), 0.1, 0.0, 0.0, 0.0)
    except ValueError:
        bad = True
    check("world_pose_humanoid", "頂点数の違うクリップは拒む", "ValueError", "ValueError" if bad else "通った", bad)


def run():
    t0 = time.perf_counter()
    part_string_mesh()
    part_ken()
    part_humanoid()
    return time.perf_counter() - t0


if __name__ == "__main__":
    sec = run()
    ng = [op for op, ok in _ROWS if not ok]
    print("world objects: %d op / %d 検査 / NG %d / %.2f s" % (len({op for op, _ in _ROWS}), len(_ROWS), len(ng), sec))
    if ng:
        print("FAILED:", sorted(set(ng)))
        raise SystemExit(1)
    print("PASS")
