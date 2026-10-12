# -*- coding: utf-8 -*-
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gallery_drive_carla_bridge — CARLA と自前の世界をつなぐ規約の op を、答えが外から分かる入力で 1 本ずつ確かめる

    py -3.11 examples/gallery_drive_carla_bridge.py

【平たく言うと】
CARLA(UE4)は左手系で、角度は度、主点は画素の角が整数の流儀。Fullseye(render3d / driveworld)は右手系で、
角度はラジアン、主点は画素の中心が整数の流儀。carlabridge はこの食い違いを 1 か所で吸収する橋で、
ここではその橋の op 10 本を「往復すると元に戻るか」「閉形式の値と一致するか」で 1 本ずつ確かめる。

【何を期待し、何と比べるか】
  * carla_intrinsics      : 水平画角 90° なら f = W/2 ちょうど、主点 = (W/2, H/2)。
  * intrinsics_to_carla   : Fullseye の K(主点が 0.5 ずれた K)から CARLA の K へ戻すと元とビット一致。
  * carla_rotation_matrix : 直交(RᵀR = I)・det = +1、yaw だけなら z 軸まわりの回転の閉形式。
  * carla_pose_to_world / world_pose_to_carla : 往復で 6 成分が元に戻る。y と yaw の符号が反転する(右手系へ)。
  * carla_xy_yaw          : 4×4 の並進と向きから読んだ (x, y, yaw) と一致。
  * carla_scene_check     : 正しい記録は要約を返し、鍵の欠けた記録は ValueError で拒む。先行車なしを見分ける。
  * carla_scene_world     : 先行車が「カメラ (20, 0) + 置いた距離 + 半長」に来る。地図の座標で場面ごと平行移動・
                            回転しても同じ世界になる(カメラ基準に正規化する op なので)。
  * carla_scene_render    : 記録を作ったのと同じ世界・同じ K で撮り直すので、深度もラベルも画素単位で一致。
  * lead_from_depth       : 一定深度の箱(閉形式の入力)で深度の中央値と最下行の路面距離 h·f/(v − c) が厳密に出る。
                            撮り直した像では閉形式の真値より 0〜1 m 奥(セダンの後ろ面は曲面)。

正直に: CARLA の本物の撮影記録は使わない(この例は CARLA 無しで走る)。確かめているのは規約の可逆性と閉形式との
一致であって、CARLA の描画そのものの正しさではない(それは examples/poc_carla_bridge.py が FULLSEYE_CARLA_DATA
がある時だけ採点する)。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import carlabridge as CB  # noqa: E402
import driveworld  # noqa: E402

_ROWS = []


def check(op, what, expected, got, ok):
    """1 行 = 何を期待し、何が出て、合ったか。"""
    _ROWS.append((op, bool(ok)))
    print("  %-22s %-44s 期待 %-26s 実測 %-26s %s" % (op, what, expected, got, "ok" if ok else "NG"))


def part_intrinsics():
    print("== 1. 内部パラメータ(水平画角 → K、主点の 0.5 画素)")
    W, H = 320, 180
    K = CB.carla_intrinsics(90.0, W, H)
    check("carla_intrinsics", "fov 90° の焦点距離 f = W/(2 tan45°)", "160", "%.12g" % K[0, 0],
          K[0, 0] == K[1, 1] and abs(K[0, 0] - 160.0) < 1e-9)
    check("carla_intrinsics", "主点 = (W/2, H/2)", "(160, 90)", "(%g, %g)" % (K[0, 2], K[1, 2]),
          K[0, 2] == 160.0 and K[1, 2] == 90.0)
    K60 = CB.carla_intrinsics(60.0, W, H)
    f60 = W / (2.0 * math.tan(math.radians(30.0)))
    check("carla_intrinsics", "fov 60° の f(閉形式)", "%.6f" % f60, "%.6f" % K60[0, 0], abs(K60[0, 0] - f60) < 1e-9)
    Kf = CB.intrinsics_to_fullseye(K)
    back = CB.intrinsics_to_carla(Kf)
    check("intrinsics_to_carla", "Fullseye の主点 (W−1)/2 から戻す", "(160, 90)", "(%g, %g)" % (back[0, 2], back[1, 2]),
          np.array_equal(back, K) and Kf[0, 2] == (W - 1) / 2.0)
    bad = False
    try:
        CB.intrinsics_to_carla(np.zeros((3, 3)))
    except ValueError:
        bad = True
    check("intrinsics_to_carla", "焦点距離 0 の K は拒む", "ValueError", "ValueError" if bad else "通った", bad)


def part_pose():
    print("== 2. 姿勢(左手系の度 ↔ 右手系のラジアン)")
    R = CB.carla_rotation_matrix(10.0, -20.0, 30.0)
    orth = float(np.abs(R.T @ R - np.eye(3)).max())
    check("carla_rotation_matrix", "直交性 max|RᵀR − I|", "< 1e-12", "%.1e" % orth, orth < 1e-12)
    check("carla_rotation_matrix", "det R", "+1", "%.15f" % np.linalg.det(R), abs(np.linalg.det(R) - 1.0) < 1e-12)
    th = math.radians(30.0)
    Rz = np.array([[math.cos(th), -math.sin(th), 0.0], [math.sin(th), math.cos(th), 0.0], [0.0, 0.0, 1.0]])
    Ry = CB.carla_rotation_matrix(0.0, 0.0, 30.0)
    check("carla_rotation_matrix", "yaw だけ = z 軸まわりの回転の閉形式", "Rz(30°)",
          "差 %.1e" % np.abs(Ry - Rz).max(), np.abs(Ry - Rz).max() < 1e-15)

    poses = [[1.0, 2.0, 3.0, 10.0, 20.0, 30.0], [-50.5, 12.25, 0.3, 0.0, 0.0, -135.0],
             [7.0, -3.0, 1.6, -5.0, 45.0, 170.0], [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]
    worst = 0.0
    for p in poses:
        T = CB.carla_pose_to_world(p)
        q = CB.world_pose_to_carla(T)
        d = np.array(q) - np.array(p)
        d[3:] = (d[3:] + 180.0) % 360.0 - 180.0              # 角は 360° の折り返しで比べる
        worst = max(worst, float(np.abs(d).max()))
    check("world_pose_to_carla", "CARLA → world → CARLA の往復(4 姿勢)", "差 < 1e-9", "%.1e" % worst, worst < 1e-9)
    T = CB.carla_pose_to_world([5.0, 2.0, 0.5, 0.0, 0.0, 30.0])
    yaw_f = math.degrees(math.atan2(T[1, 0], T[0, 0]))
    check("carla_pose_to_world", "y の符号反転(右手系へ)", "(5, −2, 0.5)",
          "(%g, %g, %g)" % tuple(T[:3, 3]), np.allclose(T[:3, 3], [5.0, -2.0, 0.5]))
    check("carla_pose_to_world", "yaw の符号反転", "−30°", "%.12g°" % yaw_f, abs(yaw_f + 30.0) < 1e-12)
    Rf = T[:3, :3]
    check("carla_pose_to_world", "回転部も直交・det = +1(鏡映 2 回で右手系の回転)", "+1",
          "%.15f" % np.linalg.det(Rf), abs(np.linalg.det(Rf) - 1.0) < 1e-12 and np.allclose(Rf.T @ Rf, np.eye(3)))
    x, y, yaw = CB.carla_xy_yaw([5.0, 2.0, 0.5, 0.0, 0.0, 30.0])
    check("carla_xy_yaw", "4×4 から読んだ (x, y, yaw[rad]) と一致", "(5, −2, %.6f)" % math.radians(yaw_f),
          "(%g, %g, %.6f)" % (x, y, yaw), abs(x - T[0, 3]) < 1e-12 and abs(y - T[1, 3]) < 1e-12
          and abs(yaw - math.atan2(T[1, 0], T[0, 0])) < 1e-12)


def _moved(scene, theta_deg, dx, dy):
    """場面全体を CARLA の地図の座標で回して平行移動した複製(カメラと先行車の相対配置は不変)。"""
    R = CB.carla_rotation_matrix(0.0, 0.0, theta_deg)
    out = dict(scene)
    for key in ("cam_transform", "ego_transform", "lead_transform"):
        t = np.array(scene[key], np.float64)
        if np.all(np.isfinite(t)):
            t[:3] = R @ t[:3] + np.array([dx, dy, 0.0])
            t[5] += theta_deg
        out[key] = t
    return out


def _lead(world):
    cars = [o for o in world["objects"] if o.get("label") == 2]
    return cars[0]["pose"] if cars else None


def part_scene():
    print("== 3. 場面記録(検査・自前の世界への置き直し・撮り直し)")
    d, lat = 20.0, 1.0
    sc = CB.carla_scene_synthetic(d, width=320, height=180, lateral=lat)
    info = CB.carla_scene_check(sc)
    check("carla_scene_check", "正しい記録の要約", "320×180・先行車あり",
          "%d×%d・%s" % (info["width"], info["height"], "あり" if info["has_lead"] else "なし"),
          info["width"] == 320 and info["height"] == 180 and info["has_lead"])
    empty = CB.carla_scene_synthetic(0.0, width=320, height=180)
    check("carla_scene_check", "先行車なしの記録", "has_lead False", str(CB.carla_scene_check(empty)["has_lead"]),
          CB.carla_scene_check(empty)["has_lead"] is False)
    broken = {k: v for k, v in sc.items() if k != "K"}
    rejected = False
    try:
        CB.carla_scene_check(broken)
    except ValueError:
        rejected = True
    check("carla_scene_check", "鍵 K の欠けた記録は拒む", "ValueError", "ValueError" if rejected else "通った", rejected)

    L = driveworld.ASSETS["sedan"][2][0]
    want = (20.0 + d + 0.5 * L, lat, 0.0)
    w = CB.carla_scene_world(sc)
    got = _lead(w)
    check("carla_scene_world", "先行車 = (20 + d + L/2, 横, 0)", "(%.2f, %.2f, %.1f)" % want,
          "(%.2f, %.2f, %.1f)" % got if got else "無い", got is not None and np.allclose(got, want, atol=1e-9))
    moved = _moved(sc, 37.0, -120.0, 85.5)
    got2 = _lead(CB.carla_scene_world(moved))
    check("carla_scene_world", "地図で 37° 回し (−120, 85.5) 動かしても同じ", "(%.2f, %.2f, %.1f)" % want,
          "(%.2f, %.2f, %.1f)" % got2 if got2 else "無い", got2 is not None and np.allclose(got2, want, atol=1e-9))
    check("carla_scene_world", "先行車なしの記録は車を置かない", "車 0 台",
          "車 %d 台" % sum(o.get("label") == 2 for o in CB.carla_scene_world(empty)["objects"]),
          _lead(CB.carla_scene_world(empty)) is None)

    view = CB.carla_scene_render(sc)
    lab, dep = np.asarray(view["label"]), np.asarray(view["depth"])
    seen = lab >= 0
    n_lab = int((lab != sc["label"]).sum())
    ddep = float(np.abs(dep[seen] - sc["depth"][seen]).max())
    check("carla_scene_render", "撮り直しのラベル = 記録のラベル", "不一致 0 画素", "%d 画素" % n_lab, n_lab == 0)
    check("carla_scene_render", "撮り直しの深度 = 記録の深度", "差 0 m", "%.1e m" % ddep, ddep < 1e-9)
    return sc, view


def part_lead(sc, view):
    print("== 4. 先行車の距離(ルールベースの知覚)")
    H, W, h = 180, 320, 1.6
    K = CB.intrinsics_to_fullseye(CB.carla_intrinsics(90.0, W, H))      # fy = 160、cy = 89.5
    depth = np.full((H, W), 1000.0)
    label = np.zeros((H, W), np.int64)
    bottom = 105                                          # v + 0.5 − cy = 16 行 → h·fy/16 = 16 m
    label[80:bottom + 1, 140:181] = 2
    depth[80:bottom + 1, 140:181] = 16.0
    r = CB.lead_from_depth(depth, label, K, h)
    check("lead_from_depth", "一定深度の箱: 深度の中央値", "16", "%.12g" % r["depth_median"], r["depth_median"] == 16.0)
    check("lead_from_depth", "最下行 105 の路面距離 h·f/(v+½−c)", "%.12g" % (h * 160.0 / 16.0),
          "%.12g" % r["row_distance"], abs(r["row_distance"] - h * 160.0 / 16.0) < 1e-9)
    check("lead_from_depth", "外接箱と画素数", "(80,105,140,180) 1066",
          "%s %d" % (r["bbox"], r["n_pixels"]), r["bbox"] == (80, 105, 140, 180) and r["n_pixels"] == 26 * 41)
    none = CB.lead_from_depth(depth, np.zeros_like(label), K, h)
    check("lead_from_depth", "車の画素が無い", "found False・inf", "%s・%s" % (none["found"], none["depth_median"]),
          none["found"] is False and math.isinf(none["depth_median"]))
    truth = CB.lead_truth_depth(sc)
    rr = CB.lead_from_depth(view["depth"], view["label"], view["K"], h)
    ex = rr["depth_median"] - truth
    check("lead_from_depth", "撮り直し: 中央値 − 閉形式の真値 20 m", "0〜1 m(後ろは曲面)", "%+.3f m" % ex,
          rr["found"] and 0.0 <= ex < 1.0)


def run():
    t0 = time.perf_counter()
    part_intrinsics()
    part_pose()
    sc, view = part_scene()
    part_lead(sc, view)
    return time.perf_counter() - t0


if __name__ == "__main__":
    sec = run()
    ng = [op for op, ok in _ROWS if not ok]
    ops = sorted({op for op, _ in _ROWS})
    print("carlabridge: %d op / %d 検査 / NG %d / %.2f s" % (len(ops), len(_ROWS), len(ng), sec))
    if ng:
        print("FAILED:", sorted(set(ng)))
        raise SystemExit(1)
    print("PASS")
