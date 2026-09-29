# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC ⑯: 教習所が開校する —— 規格寸法の周回コースの中に課題を置き、車と信号を置き、LiDAR とカメラで見て、定理と恒等式で採点する。

自動運転のデモは動くので、誰も正しさを測らない。測るには **真値を持った世界** が要る。この PoC はその世界を
開校する: 道路交通法施行規則 別表第三(普通免許)の寸法どおりの周回コース(長円形、直線 80 m・幅 8 m)の内側に
幹線(幅 7 m の十字、信号 4 基)を通し、課題(クランク・S 字・坂道・縦列駐車・方向変換・踏切)を置いて、出口を
連絡路で周回へ戻す —— 教習所と同じく **ぐるぐる回れる** 作り。2-D の多角形(drivecourse)を 3-D の世界にして
CC0 の車・信号機・標識を置き(driveworld)、回転式 LiDAR をメッシュに撃ち(lidarsim)、車載カメラで撮る。
真値は全部世界の側にある —— どの点がどの面から来たか、どの画素がどの物体か、信号が何色か、車が道の中にいるか。

門(真値の出どころ):
  1. **面積の閉形式**: 要素の多角形の靴紐面積が、規格の寸法から導いた閉形式(クランク = 幅 × 中心線長 + 2r²(1 − π/4)、
     周回の半円 = π R w …)と一致する。弧の点数を増やすと単調に収束する。
  2. **平面へのレイの閉形式**: 平らな路面(z = 0)に当たった LiDAR の range が h / (−sin e)(h = センサ高、e = 仰角)と 1e-9 で一致。
  3. **2 センサ 1 世界の恒等式**: LiDAR の点をカメラに投影した画素の深度と点の深度が一致し(中央値 < 1 %)、ラベルも一致
     (画素 1 つの許容で > 97 %; 厳密な画素一致の数字も出す)。
  4. **車の点は車の箱の中**: ラベル「車」の LiDAR 点は、置いた車の箱(姿勢 + 実寸)の内側にある(100 %)。
  5. **縁石の点は道の外**: ラベル「縁石」の点から作った占有格子は、コースの真の占有(多角形の外)を 1 セル(8 近傍)膨らませた集合の部分集合。
  6. **脱輪**: Hybrid A*(13 巡目の op)が出した道の全姿勢で、車体の 4 隅の縁石線からのはみ出しが半セル以内(計画器の分解能)。
     厳密な多角形で越えた姿勢の数と最大の越え幅も出す。ゼロ点 = 縁石を無視して入口から出口へ直線で進むと脱輪する。
  7. **カメラが信号を読む**: 灯火の画素の色で赤/緑を判定し、世界の状態と一致。ゼロ点 = 灯火を全部消すと判定できない。

正直に書くこと: 規格の幅 3.5 m は 4.5 × 1.8 m の車にはぎりぎりで、最大舵角と直進だけの運動基本形(Dolgov 2010 の型)では
クランクも S 字も **前進のみでは到達不能**(格子 0.125 m・θ 144 でも)。後退(切り返し)を許すと通る。実際の検定でも
切り返しは許される(回数で減点)ので、そのまま数を出す。中間の舵角を持つ運動基本形は次の課題。

Run: py -3.11 examples/poc_driving_school.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く)
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import drivecourse as DC  # noqa: E402
import driveworld as DW  # noqa: E402
import lidarsim as LS  # noqa: E402
import carpath as CP  # noqa: E402
from occupancy import occupancy_grid_2d, inflate_obstacles  # noqa: E402
import studio  # noqa: E402

T0 = time.time()
CAR = (4.5, 1.8, 1.0)                 # 車体 (長さ, 幅, 後軸から後端) —— 普通車
RHO = 5.0                             # 最小回転半径 [m]
CELL = 0.25
LIDAR_H = 1.64                        # センサ高 [m](Argoverse 2 の up_lidar と同じ)
LIDAR_FWD = 1.35                      # 後軸からセンサまで [m]
LOOP_R, LOOP_S, LOOP_W = 30.0, 80.0, 8.0
PAL = np.array([[0.62, 0.62, 0.66], [0.95, 0.92, 0.30], [0.95, 0.30, 0.20], [0.20, 0.95, 0.40], [0.30, 0.55, 1.0],
                [1.0, 0.60, 0.10], [0.70, 0.40, 0.90], [1.0, 0.4, 0.7], [0.55, 0.35, 0.25], [1.0, 1.0, 1.0]])
OK = []


def gate(name, cond, detail=""):
    OK.append(bool(cond))
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


def tf(p, pose):
    """要素座標の姿勢 p を配置 pose で世界へ。"""
    x, y, yaw = pose
    c, s = math.cos(yaw), math.sin(yaw)
    return (x + c * p[0] - s * p[1], y + s * p[0] + c * p[1], yaw + p[2])


def ahead(pose, d):
    x, y, yaw = pose
    return (x + d * math.cos(yaw), y + d * math.sin(yaw), yaw)


def sensor_T(pose):
    x, y, yaw = pose
    c, s = math.cos(yaw), math.sin(yaw)
    T = np.eye(4)
    T[:3, :3] = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
    T[:3, 3] = [x + LIDAR_FWD * c, y + LIDAR_FWD * s, LIDAR_H]
    return T


def footprint_corners(pose):
    x, y, yaw = pose
    L, W, rear = CAR
    c, s = math.cos(yaw), math.sin(yaw)
    return np.asarray([(x + c * dx - s * dy, y + s * dx + c * dy)
                       for dx, dy in ((-rear, -W / 2), (L - rear, -W / 2), (L - rear, W / 2), (-rear, W / 2))])


def ego_mesh(asset, pose):
    """自車のメッシュを姿勢に(資産の原点は箱の底面中心 = 後軸から前へ L/2 − rear)。"""
    return DW.place_mesh(asset["V"], *ahead(pose, CAR[0] / 2 - CAR[2]))


def resample(points, ds):
    """姿勢列を弧長 ds ごとに間引く(始点と終点は残す)。"""
    P = np.asarray(points, float)
    d = np.r_[0.0, np.cumsum(np.hypot(np.diff(P[:, 0]), np.diff(P[:, 1])))]
    keep, nxt = [0], ds
    for i in range(1, len(P)):
        if d[i] >= nxt:
            keep.append(i)
            nxt += ds
    if keep[-1] != len(P) - 1:
        keep.append(len(P) - 1)
    return P[keep]


def main() -> int:
    """PoC の本体(examples の門: 実行は __main__ の守りの下で)。"""
    # ─────────────────────────────── 1. コース(規格寸法)と世界 ─────────────────────────────
    print("== 1. 規格寸法のコース(道路交通法施行規則 別表第三、普通免許): 周回の中に幹線と課題、出口は周回へ戻る")
    LOOP = DC.course_loop(LOOP_S, LOOP_R, LOOP_W)                    # 周回: 直線 80 m・幅 8 m、半円 R 30(中心線)
    loop_els, loop_pl = LOOP["elements"], LOOP["placements"]
    I = DC.course_intersection()                                     # 幹線の十字(幅 7 m、腕 20 m、信号 4 基)
    C = DC.course_crank()
    S = DC.course_s_curve()
    SL = DC.course_slope()
    PP = DC.course_parallel_parking()
    TA = DC.course_turnaround()
    X = DC.course_crossing()
    IN = LOOP_R - LOOP_W / 2                                         # 周回の内側の縁(直線部)= 26 m


    def loop_edge_x(y):
        """東の半円の内側の縁の x(y での)。西は符号を反転。"""
        return LOOP_S / 2 + math.sqrt(IN ** 2 - y ** 2)


    ELS = list(loop_els) + [I]
    PLACE = list(loop_pl) + [(0.0, 0.0, 0.0)]
    # 幹線を周回まで延ばす(0.5 m 食い込ませて継ぎ目にする)
    ELS += [DC.course_road(IN + 0.5 - 23.45, 7.0), DC.course_road(IN + 0.5 - 23.45, 7.0)]
    PLACE += [(0.0, 23.45, math.pi / 2), (0.0, -23.45, -math.pi / 2)]
    ELS += [DC.course_road(16.6, 7.0), X, DC.course_road(loop_edge_x(0.0) + 0.5 - 54.55, 7.0)]      # 東: 連絡路 → 踏切 → 連絡路
    PLACE += [(23.45, 0.0, 0.0), (40.0, 0.0, 0.0), (54.55, 0.0, 0.0)]
    ELS += [DC.course_road(loop_edge_x(0.0) + 0.5 - 23.45, 7.0)]                                     # 西: 連絡路
    PLACE += [(-23.45, 0.0, math.pi)]
    pC = (24.0, 3.45, math.pi / 2)                                   # 北東: クランク(北へ入り、左 = 西へ折れ、北へ抜ける)
    cex = tf(C["exit"], pC)
    ELS += [C, DC.course_road(IN + 0.5 - cex[1] + 0.05, 3.5)]
    PLACE += [pC, ahead(cex, -0.05)]
    pS = (-30.0, -3.45, -math.pi / 2)                                # 南西: S 字(南へ入り、東へ膨らみながら南へ抜ける)
    sex = tf(S["exit"], pS)
    ELS += [S, DC.course_road(IN + 0.5 + sex[1] + 0.05, 3.5)]
    PLACE += [pS, ahead(sex, -0.05)]
    pSL = (3.45, -13.0, 0.0)                                         # 南東: 坂道(東へ)→ 連絡路で東の半円へ
    slex = tf(SL["exit"], pSL)
    ELS += [SL, DC.course_road(loop_edge_x(-13.0) + 0.5 - slex[0] + 0.05, 7.0)]
    PLACE += [pSL, ahead(slex, -0.05)]
    pPP = (-3.45, 13.0, math.pi)                                     # 北西: 縦列駐車 → 方向変換 → 連絡路で西の半円へ
    ppex = tf(PP["exit"], pPP)
    pTA = ahead(ppex, -0.05)
    ta_far = ahead(pTA, 13.5)                                        # 方向変換の道の奥端(局所 x = 13.5)
    ELS += [PP, TA, DC.course_road(loop_edge_x(13.0) + 0.5 - abs(ta_far[0]) + 0.05, 3.5)]
    PLACE += [pPP, pTA, ahead(ta_far, -0.05)]
    LAYOUT = DC.course_layout(ELS, PLACE)
    kinds = {}
    for e in LAYOUT["elements"]:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    print("  要素 %d: %s" % (len(ELS), ", ".join("%s × %d" % kv for kv in kinds.items())))
    for el in (loop_els[1], I, C, S, SL, PP, TA, X):
        print("  %-18s 面積 %8.3f m² (閉形式 %8.3f)  規格 %s" % (
            el["kind"], DC.polygon_area(el["polygon"]), el["area_closed_form"],
            ", ".join("%s=%s" % (k, v) for k, v in list(el["params"]["regulation"].items())[:4])))
    # 弧を折線にした分だけ面積は閉形式より小さい。弧の点数を増やすと単調に収束する(門): 16 → 64 → 256 → 1024
    ARC = {"loop_bend": lambda n: DC.course_loop_bend(LOOP_R, LOOP_W, arc_pts=n),
           "crank": lambda n: DC.course_crank(arc_pts=n), "s_curve": lambda n: DC.course_s_curve(arc_pts=n),
           "turnaround": lambda n: DC.course_turnaround(arc_pts=n),
           "intersection": lambda n: DC.course_intersection(arc_pts=n)}
    CONV = {}
    for kind, fn in ARC.items():
        errs = []
        for n in (16, 64, 256, 1024):
            e = fn(n)
            errs.append(abs(DC.polygon_area(e["polygon"]) - e["area_closed_form"]) / e["area_closed_form"])
        CONV[kind] = errs
        print("  %-14s 弧の点数 16/64/256/1024 → 相対差 %.1e / %.1e / %.1e / %.1e" % (kind, *errs))
    mono = all(all(np.diff(v) < 0) for v in CONV.values())
    fine = max(v[-1] for v in CONV.values())
    exact = max(abs(DC.polygon_area(e["polygon"]) - e["area_closed_form"]) / e["area_closed_form"]
                for e in (SL, PP, X, loop_els[0]))
    gate("面積: 弧のある 5 要素は点数を増やすと閉形式へ単調収束(1024 点で < 1e-5)", mono and fine < 1e-5, "max %.1e" % fine)
    gate("面積: 弧の無い 4 要素(坂道・縦列駐車・踏切・直線)は閉形式と厳密一致", exact < 1e-12, "max %.1e" % exact)

    # 左側通行: 東行きは y > 0 の車線、西行きは y < 0。周回は反時計回り(南の直線が東行き)。
    PROPS = [("sedan", -9.0, -1.75, math.pi), ("taxi", 6.0, -1.75, math.pi), ("police", 15.0, -1.75, math.pi),
             ("truck", 48.0, -1.75, math.pi), ("suv", -1.75, 16.0, math.pi / 2), ("sedan", 20.0, 28.0, math.pi),
             ("taxi", -25.0, -28.0, 0.0), ("suv", -20.0, 10.0, math.pi), ("cone", 19.0, 3.0, 0.0), ("cone", 21.0, 3.0, 0.0),
             ("street_light", -4.0, 4.6, 0.0), ("street_light", 30.0, 22.5, 0.0), ("sign_stop", -20.0, 4.3, 0.0)]
    WORLD = DW.world_build(LAYOUT, props=PROPS)
    CARS = [o for o in WORLD["objects"] if o["label"] == 2]
    print("  世界: 三角形 %d, 物体 %d(車 %d・信号機 %d), 広さ %.0f × %.0f m" % (
        len(WORLD["F"]), len(WORLD["objects"]), len(CARS), sum(o["name"] == "traffic_light" for o in WORLD["objects"]),
        LAYOUT["bounds"][1] - LAYOUT["bounds"][0], LAYOUT["bounds"][3] - LAYOUT["bounds"][2]))
    OCC, EXT = DC.course_occupancy(LAYOUT, cell=CELL, margin=3.0)
    print("  真の占有格子 %d × %d (cell %.2f m), 走れる %.1f %%" % (OCC.shape[0], OCC.shape[1], CELL, 100 * (~OCC).mean()))

    # ─────────────────────────────── 2. 走る(信号 → クランク → 周回へ合流) ──────────────────────
    print("== 2. 走る: 幹線で信号を待ち、クランクを抜け、連絡路から周回コースへ合流(Hybrid A*、13 巡目の op)")
    X0, Y0 = EXT[0], EXT[2]


    def plan(start, goal, reverse):
        poses = np.array([[start[0] - X0, start[1] - Y0, start[2]], [goal[0] - X0, goal[1] - Y0, goal[2]]])
        r = CP.car_hybrid_astar(OCC, poses, radius=RHO, cell=CELL, n_theta=72, allow_reverse=reverse, footprint=CAR,
                                switch_penalty=2.0, reverse_penalty=1.0, max_expansions=800000)
        pts = r["points"].copy()
        pts[:, 0] += X0
        pts[:, 1] += Y0
        return r, pts


    APPROACH0 = (-44.0, 1.75, 0.0)                                  # 西の連絡路、東行き車線
    STOP = (-7.5 - (CAR[0] - CAR[2]) - 0.3, 1.75, 0.0)              # 停止線の 0.3 m 手前に前端
    LOOK = ahead(STOP, -10.0)                                        # 停止線の 10 m 手前(灯火が視野に入り、円盤が数画素になる)
    CRANK_IN = tf((0.0, 0.0, 0.0), ahead(pC, 2.0))                   # クランクの入口の直線の中(後端まで入っている)
    CRANK_OUT = ahead(cex, IN + 0.5 - cex[1] - 3.0)                  # 連絡路の先端の手前(前端が周回に入る)
    MERGE = (2.0, LOOP_R - 2.0, math.pi)                             # 周回の北の直線、西行き(左側 = 内側の車線)
    S_IN = tf((0.0, 0.0, 0.0), ahead(pS, 2.0))
    S_OUT = ahead(sex, -(CAR[0] - CAR[2]) - 0.5)                     # 車体が S 字の中に収まる姿勢
    t = time.time()
    path_approach = np.linspace(APPROACH0, STOP, 60)
    r_x, path_cross = plan(STOP, CRANK_IN, True)                     # 交差点を渡り、東の連絡路からクランクへ左折
    try:
        plan(CRANK_IN, CRANK_OUT, False)
        crank_forward_only = True
    except ValueError as e:
        crank_forward_only = False
        print("  クランク 前進のみ: 到達不能(%s)" % str(e).split(":")[-1].strip()[:60])
    r_c, path_crank = plan(CRANK_IN, CRANK_OUT, True)
    d_merge = CP.car_dubins_path(np.array([CRANK_OUT, MERGE]), radius=RHO, step=0.1)
    path_merge = d_merge["points"]
    path_loop = np.linspace(MERGE, (-30.0, LOOP_R - 2.0, math.pi), 40)
    r_s, path_s = plan(S_IN, S_OUT, True)
    n_rev_c = sum(1 for sg in r_c["segments"] if sg[1] < 0)
    n_rev_s = sum(1 for sg in r_s["segments"] if sg[1] < 0)
    print("  交差点→クランク入口: 費用 %.1f m(後退 %d)/ クランク: 費用 %.2f m, 区間 %d(後退 %d), 展開 %d / "
          "合流(Dubins %s %.1f m)/ S 字: 費用 %.2f m(後退 %d), 計画 %.1f s" % (
              r_x["cost"], sum(1 for sg in r_x["segments"] if sg[1] < 0), r_c["cost"], len(r_c["segments"]), n_rev_c,
              r_c["n_expanded"], d_merge["word"], d_merge["length"], r_s["cost"], n_rev_s, time.time() - t))
    gate("クランクは前進のみでは到達不能(規格 3.5 m 幅 × 4.5 m 車 × 最大舵角の基本形)—— 正直に記録", not crank_forward_only)
    gate("切り返しを許すとクランクも S 字も通り、連絡路から周回へ合流できる", len(path_crank) > 2 and len(path_s) > 2)

    PATH = np.vstack([path_approach, path_cross, path_crank, path_merge, path_loop])
    _EDGES = [(np.asarray(el["polygon"], float), np.roll(np.asarray(el["polygon"], float), -1, axis=0))
              for el in LAYOUT["elements"]]


    def outside_distance(xy):
        """多角形の外に出た点が、いちばん近い縁からどれだけ外か(内側なら 0)。"""
        if DC.course_contains(LAYOUT, np.asarray([xy])).all():
            return 0.0
        best = np.inf
        for A, B in _EDGES:
            AB = B - A
            tt = np.clip(((xy - A) * AB).sum(1) / np.maximum((AB * AB).sum(1), 1e-12), 0, 1)
            best = min(best, np.hypot(*(A + tt[:, None] * AB - xy).T).min())
        return float(best)


    drive_poses = np.vstack([path_cross, path_crank, path_merge, path_s])
    excursion = np.array([max(outside_distance(c) for c in footprint_corners(p)) for p in drive_poses])
    n_derail = int((excursion > 0).sum())
    print("  厳密な多角形で測ると %d / %d 姿勢で隅が縁石線を越える(最大 %.3f m)。計画器の衝突判定はセル(%.2f m)単位なので、"
          "半セルまでは越えうる —— 門は「半セル以内」、越え方は正直に数える" % (n_derail, len(drive_poses), excursion.max(), CELL))
    gate("脱輪: 全姿勢で隅の越え幅 ≤ 半セル(%.3f m)、越えた姿勢 %d / %d" % (CELL / 2, n_derail, len(drive_poses)),
         excursion.max() <= CELL / 2, "max %.3f m" % excursion.max())
    straight = np.linspace(CRANK_IN, ahead(cex, 1.0), 60)
    n_derail_straight = int(sum(not DC.course_contains(LAYOUT, footprint_corners(p)).all() for p in straight))
    gate("ゼロ点: クランクの入口→出口を直線で進むと脱輪する", n_derail_straight > 0, "外れ %d / 60" % n_derail_straight)

    # ─────────────────────────────── 3. センサ: LiDAR とカメラ ──────────────────────────────
    print("== 3. LiDAR(32 ビーム −25…+15°, 0.5°)とカメラ(60°, 640 × 400)で同じ世界を見る")
    SPEC = LS.lidar_spec(n_beams=32, v_fov_deg=(-25.0, 15.0), azimuth_res_deg=0.5, range_max=60.0)
    SPEC_GIF = LS.lidar_spec(n_beams=16, v_fov_deg=(-25.0, 15.0), azimuth_res_deg=0.5, range_max=60.0)
    K = DW.camera_intrinsics(60.0, 640, 400)
    SIG = [k for k, o in enumerate(WORLD["objects"]) if o["name"] == "traffic_light"
           and abs(o["pose"][0] + 7.5) < 0.1 and abs(o["pose"][1] - 4.0) < 0.1][0]     # 東行きの信号
    EGO = DW.load_asset("sedan")


    def cam_pose_incar(pose):
        x, y, yaw = pose
        c, s = math.cos(yaw), math.sin(yaw)
        return DW.camera_pose((x + 1.0 * c, y + 1.0 * s, 1.35), (x + 20.0 * c, y + 20.0 * s, 0.9))


    def sense(pose, spec=SPEC, with_camera=True):
        T = sensor_T(pose)
        out = {"scan": LS.lidar_scan(WORLD["V"], WORLD["F"], spec, T, labels=WORLD["face_label"]), "T": T}
        if with_camera:
            out["P"] = cam_pose_incar(pose)
            out["cam"] = DW.world_camera(WORLD, out["P"], K, 640, 400)
        return out


    # 3a. 平面へのレイの閉形式(停止線の 10 m 手前、平らな路面)
    snap = sense(LOOK)
    sc = snap["scan"]
    hit = sc["ranges"] > 0
    ground = hit & (sc["labels"] == 0)
    pts_r = sc["ranges"][ground]
    elev = np.broadcast_to(SPEC["elevations"][:, None], sc["ranges"].shape)[ground]
    z_hit = sc["points"][:, 2][(sc["labels"][hit] == 0)]
    flat = np.abs(z_hit) < 1e-9                                        # 坂道(z > 0)の面は除く
    pred = LIDAR_H / (-np.sin(elev[flat]))
    err = np.abs(pts_r[flat] - pred) / pred
    gate("路面の range = h/(−sin e)(%d 点、平らな面)、相対差 < 1e-9" % flat.sum(), flat.sum() > 1000 and err.max() < 1e-9,
         "max %.1e" % err.max())

    # 3b. 2 センサ 1 世界: LiDAR の点をカメラに投影 → その画素の深度・ラベルと一致
    cam = snap["cam"]
    col, row, dep = DW.world_project_points(sc["points"], snap["P"], K)
    inside = np.isfinite(col) & (dep > 0) & (col >= 0) & (col <= 639.49) & (row >= 0) & (row <= 399.49)
    cc = np.rint(col[inside]).astype(int)
    rr = np.rint(row[inside]).astype(int)
    dcam = cam["depth"][rr, cc]
    vis = np.isfinite(dcam) & (dep[inside] <= dcam * 1.02 + 0.02)     # 別の面に隠れた点は除く
    rel = np.abs(dep[inside][vis] - dcam[vis]) / dcam[vis]
    lab_pt = sc["labels"][hit][inside][vis]
    lab_px = cam["label"][rr, cc][vis]
    merge = np.vectorize(lambda v: 0 if v == 9 else v)                 # 白線は路面の塗り分け(同じ面)
    lab_strict = float(np.mean(merge(lab_px) == merge(lab_pt)))
    # 縁石(高さ 0.15 m)は 20 m 先で 2 画素の細い帯で、点の投影は 1 画素ずれると路面に落ちる —— 3 × 3 の窓に同じラベルが在るか
    L_img = cam["label"]
    H_, W_ = L_img.shape
    win = np.zeros(vis.sum(), bool)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            yy = np.clip(rr[vis] + dy, 0, H_ - 1)
            xx = np.clip(cc[vis] + dx, 0, W_ - 1)
            win |= merge(L_img[yy, xx]) == merge(lab_pt)
    lab_1px = float(win.mean())
    gate("2 センサ 1 世界: 深度の相対差 中央値 < 1 %% (%d 点)" % vis.sum(), np.median(rel) < 0.01,
         "median %.2e p95 %.2e" % (np.median(rel), np.percentile(rel, 95)))
    gate("2 センサ 1 世界: ラベル一致 > 97 %(1 画素の許容)", lab_1px > 0.97,
         "%.2f %%(画素をぴったり合わせると %.2f %%: 細い縁石は 1 画素ずれると路面に落ちる)" % (100 * lab_1px, 100 * lab_strict))

    # 3c. 車の点は車の箱の中 / 縁石の点は道の外 —— 交差点・クランク・周回の 3 姿勢で
    CHECK_POSES = [LOOK, path_crank[len(path_crank) // 2], path_loop[len(path_loop) // 2]]
    in_box_all, n_car_pts, prec_all, n_kerb = [], 0, [], 0
    for pose in CHECK_POSES:
        s2 = sense(pose, with_camera=False)["scan"]
        h2 = s2["ranges"] > 0
        lab = s2["labels"][h2]
        P2 = s2["points"]
        carp = P2[lab == 2]
        n_car_pts += len(carp)
        if len(carp):
            inside_any = np.zeros(len(carp), bool)
            for o in CARS:
                x, y, yaw = o["pose"]
                L, W, Hh = o["dims"]
                c, s = math.cos(yaw), math.sin(yaw)
                u = (carp[:, 0] - x) * c + (carp[:, 1] - y) * s
                v = -(carp[:, 0] - x) * s + (carp[:, 1] - y) * c
                inside_any |= (np.abs(u) <= L / 2 + 0.02) & (np.abs(v) <= W / 2 + 0.02) & (carp[:, 2] >= -0.02) & (carp[:, 2] <= Hh + 0.02)
            in_box_all.append(inside_any)
        kerb = P2[lab == 1]
        n_kerb += len(kerb)
        if len(kerb):
            occ_l, _ = occupancy_grid_2d(kerb, cell=CELL, bounds=EXT, min_points=1)
            prec_all.append(inflate_obstacles(OCC, 1.5)[occ_l])
    in_box = np.concatenate(in_box_all)
    prec = float(np.concatenate(prec_all).mean())
    gate("車の LiDAR 点は置いた車の箱の中(%d 点)" % n_car_pts, in_box.all(), "%.2f %%" % (100 * in_box.mean()))
    gate("縁石の点から作った占有格子 ⊆ 真の占有(1 セル膨張、8 近傍)(%d 点)" % n_kerb, prec == 1.0, "precision %.4f" % prec)


    # 3d. カメラが信号を読む
    def read_signal(cam_img, lamp_pixels):
        """灯火の画素のうち点いているもの(最大チャネル > 0.5)の平均色で赤/緑を決める。点いた画素が無ければ unknown。"""
        px = cam_img[lamp_pixels]
        lit = px[px.max(axis=1) > 0.5]
        if len(lit) < 2:
            return "unknown"
        c = lit.mean(axis=0)
        return "red" if c[0] > c[1] else "green"


    face = snap["cam"]["face"]
    lamp_px = np.zeros(face.shape, bool)
    for kind, (f0, f1) in WORLD["objects"][SIG]["lamp_faces"].items():
        lamp_px |= (face >= f0) & (face < f1)
    read_red = read_signal(snap["cam"]["color"], lamp_px)
    DW.set_signal_state(WORLD, SIG, "green")
    read_green = read_signal(sense(LOOK)["cam"]["color"], lamp_px)
    DW.set_signal_state(WORLD, SIG, "off")
    read_off = read_signal(sense(LOOK)["cam"]["color"], lamp_px)
    DW.set_signal_state(WORLD, SIG, "red")
    gate("カメラが信号を読む: 赤 → 'red', 緑 → 'green'(灯火 %d 画素)" % lamp_px.sum(),
         read_red == "red" and read_green == "green", "%s / %s" % (read_red, read_green))
    gate("ゼロ点: 灯火を消すと読めない", read_off == "unknown", read_off)

    # ─────────────────────────────── 4. 走らせて全コマで測る ────────────────────────────────
    PATH_LEN = float(np.sum(np.hypot(np.diff(PATH[:, 0]), np.diff(PATH[:, 1]))))
    print("== 4. 走らせる(%.0f m: 幹線 → 信号 → 交差点 → クランク → 連絡路 → 周回)—— 全コマで LiDAR を撃ち、縁石の precision を数える" % PATH_LEN)
    frames_pose = resample(PATH, 2.5)
    hold = 6                                                              # 停止線で赤信号を待つコマ
    i_stop = int(np.argmin(np.hypot(frames_pose[:, 0] - STOP[0], frames_pose[:, 1] - STOP[1])))
    seq = [(p, "red") for p in frames_pose[:i_stop + 1]] + [(frames_pose[i_stop], "red")] * hold + \
          [(p, "green") for p in frames_pose[i_stop + 1:]]
    t = time.time()
    gif, n_pts, prec_frames = [], [], []
    for k, (pose, state) in enumerate(seq):
        DW.set_signal_state(WORLD, SIG, state)
        sc2 = LS.lidar_scan(WORLD["V"], WORLD["F"], SPEC_GIF, sensor_T(pose), labels=WORLD["face_label"])
        h2 = sc2["ranges"] > 0
        n_pts.append(int(sc2["n_hits"]))
        kerb = sc2["points"][sc2["labels"][h2] == 1]
        if len(kerb):
            occ_l, _ = occupancy_grid_2d(kerb, cell=CELL, bounds=EXT)
            prec_frames.append(float(inflate_obstacles(OCC, 1.5)[occ_l].mean()))
        if figs.enabled():
            x, y, yaw = pose
            c, s = math.cos(yaw), math.sin(yaw)
            Pc = DW.camera_pose((x - 9.0 * c, y - 9.0 * s, 4.5), (x + 6.0 * c, y + 6.0 * s, 0.6))
            Kc = DW.camera_intrinsics(55.0, 480, 300)
            img = DW.world_camera(WORLD, Pc, Kc, 480, 300, ego=(ego_mesh(EGO, pose), EGO["F"], EGO["color"]))
            gif.append(DW.overlay_points(img["color"], sc2["points"], Pc, Kc, PAL[sc2["labels"][h2]], depth_test=img["depth"]))
    DW.set_signal_state(WORLD, SIG, "red")
    print("  %d コマ, LiDAR 点 %d〜%d / コマ, 縁石 precision 最小 %.4f, %.1f s" % (
        len(seq), min(n_pts), max(n_pts), min(prec_frames), time.time() - t))
    gate("全コマで縁石の占有格子 ⊆ 真の占有", min(prec_frames) == 1.0)

    # ─────────────────────────────── 5. 図 ─────────────────────────────────────────────
    if figs.enabled():
        print("== 5. 図")
        Kb = DW.camera_intrinsics(50.0, 960, 720)
        top = DW.world_camera(WORLD, DW.camera_pose((0.0, 0.0, 165.0), (0.0, 0.01, 0.0), up=(0.0, 1.0, 0.0)), Kb, 960, 720)
        figs.save("course_plan", top["color"],
                  "教習所の平面(真上から): 周回コース(長円形、直線 80 m・幅 8 m・半円 R 30)の中に幹線の十字(幅 7 m・すみ切り 3 m・"
                  "信号 4 基)。北東にクランク(幅 3.5・曲角間 12・すみ切り 1)、南西に S 字(幅 3.5・外側半径 7.5・弧 3/8 周)、"
                  "南東に坂道(緩 8 %・急 11 %・頂上 4 m)、北西に縦列駐車と方向変換(幅 3.5・奥行 5)、東の幹線に踏切(軌間 1.1 m)。"
                  "課題の出口は連絡路で周回へ戻る。寸法は道路交通法施行規則 別表第三(普通免許)。")
        obl = DW.world_camera(WORLD, DW.camera_pose((-40.0, -120.0, 70.0), (0.0, 0.0, 0.0)), Kb, 960, 720)
        figs.save("world_oblique", obl["color"],
                  "同じ世界を斜めから: CC0 の車・信号機・標識・コーン(Kenney)を実寸に合わせて置き、縁石(高さ 0.15 m)と白線を"
                  "多角形の縁に沿って生成(継ぎ目には置かない)。面ごとにラベルと色を持つので、センサの真値は世界の側にある。")
        pc = studio.render_points_frame(sc["points"], PAL[sc["labels"][hit]], yaw=-35.0, pitch=32.0, size=900, point_px=2,
                                        center=(LOOK[0] + 14.0, 0.0, 0.0), radius=28.0)
        figs.save("lidar_sweep", pc,
                  "停止線の 10 m 手前での LiDAR 一掃(32 ビーム・0.5°、%d 点)を面のラベルで塗る: 灰 = 路面、黄 = 縁石、赤 = 車、"
                  "緑 = 信号機、青 = 標識、橙 = コーン、白 = 白線。平らな路面の range は h/(−sin e) と 1e-9 で一致(門 2)。" % sc["n_hits"])
        over = DW.overlay_points(snap["cam"]["color"], sc["points"], snap["P"], K, PAL[sc["labels"][hit]], depth_test=snap["cam"]["depth"])
        figs.save("camera_with_lidar", over,
                  "同じ瞬間の車載カメラ(60°)に LiDAR の点を投影して重ねる: 点の深度と画素の深度の相対差は中央値 %.2e、"
                  "ラベル一致 %.1f %%(1 画素の許容; 門 3、2 センサ 1 世界の恒等式)。信号は赤。" % (np.median(rel), 100 * lab_1px))
        figs.save_gif("drive_gif", gif, fps=6,
                      caption="幹線で赤信号を待ち、青で発進して交差点を渡り、クランクを抜けて連絡路から周回コースへ合流する(%d コマ)。"
                              "追走カメラの画像に LiDAR(16 ビーム)の点を重ねる。クランクは前進のみでは到達不能で、切り返し %d 回"
                              "(後退の区間数)。全姿勢で隅の越え幅は半セル以内。" % (len(seq), n_rev_c))
        els8 = (loop_els[1], I, C, S, SL, PP, TA, X)
        tv = [e["area_closed_form"] for e in els8] + list(pred[:200])
        mv = [DC.polygon_area(e["polygon"]) for e in els8] + list(pts_r[flat][:200])
        figs.save_plot("truths", [("測った値(面積 m², range m)", tv, mv), ("y = x", tv, tv)], kinds=["scatter", "line"],
                       xlabel="閉形式", ylabel="測った値",
                       caption="真値の散布: 8 種の要素の面積(靴紐 vs 閉形式)と路面の range 200 点(実測 vs h/(−sin e))。全部 y = x の上。")
        if figs.errors():
            print("図の書き出しで失敗:", "; ".join(figs.errors()))

    print("== 結果: %d / %d 門, %.1f s" % (sum(OK), len(OK), time.time() - T0))
    print("PASS" if all(OK) else "FAIL")
    return 0 if all(OK) else 1


if __name__ == "__main__":
    sys.exit(main())
