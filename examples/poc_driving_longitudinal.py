# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC ㉒(自動運転 第 5 回): 車に慣性と坂を —— 空走 + 制動で停止線の直前に止まり、坂道で止まって逆行せずに発進する。

これまでの教習所(PoC ⑯)は 2.5 m おきの姿勢の列で、停止線で **瞬時に** 止まっていた(時間も速度も無い)。ここでは車に
質量と慣性を持たせ(drivelong: 道なりの 1 次元の運動方程式、坂・転がり抵抗・空気抵抗・ブレーキの静止摩擦)、**時計つきで**
走らせる: 信号を車載カメラの画像処理で読み(第 2 回の閉ループ)、黄か赤を読んだ瞬間から反応時間(空走)を置いて 2 段に分けて
ブレーキを踏み、停止線の手前に止まる。青を読んだら発進。交差点を渡って坂道コース(道路交通法施行規則 別表第三: 緩 8 %・急 11 %)
へ入り、上り坂の指定の場所で一時停止し、逆行せずに発進し、急な下りは速さを抑えて下る。採点は警察庁の技能試験の減点細目
(丙運発第 12 号 令和 4 年)。

門(真値の出どころ):
  1. **停止距離の閉形式** d = vρ + (1/(2k)) ln(1 + k v²/A)、A = b + g sin θ + c_rr g cos θ(平地・上り・下り、転がり・空気抵抗つき)
     と積分器(RK4、事象で刻みを切る)が 1e-9 で一致。
  2. **第 2 実装**: 平地・c_rr = k = 0 で rsssafety.rss_stopping_distance(v, ρ, 0, b) と一致(閉形式 1e-12・積分器 1e-9)。
  3. **坂の保持と坂道発進**: 止まっていられる最小の制動 max(0, |a_creep − g sin θ| − c_rr g cos θ) の両側で「動かない / 動く」。
     踏み替えの間 τ のずり下がり ½a₁τ² + (a₁τ)²/(2a₂) と積分器が 1e-9。
  4. **エネルギー収支**: ½v² + g z + W_rr + W_drag + W_brake − W_drive が一定(走行の全区間)。転がりの仕事は c_rr g Σ cos θ Δl。
  5. **公表値 = 技能試験の減点**: 停止位置(停止線の手前 0〜2 m = 減点 0)、逆行 < 0.3 m(減点 0)、ブレーキ 2 段(制動操作不良 0)。
  6. **つまみ**: 反応時間・路面の摩擦 μ・坂の勾配を動かすと、閉形式のしきい値の向こう側で減点が出る(しきい値は
     stopping_distance_grade / hill_start_rollback から、走らせた結果とは別に計算)。
  7. **閉ループ**: 赤の間は 1 mm も動かず、青を読んでから発進。ゼロ点 = 灯火を消すと 'unknown' で止まったまま(fail-closed)。

正直に書くこと: 停止線の計画は前向き(知覚した瞬間の速さと距離から閉形式で段の時刻を決める)で、モデルと世界が同じなので
ぴったり止まる。車載カメラ(60°、640 × 400)が信号を読めるのは停止線の手前およそ 20 m 以内(それより遠いと灯火の円盤が
1 画素を切る)—— この距離より速く止まれない速さでは入れない。

教則の場面: S003, S014, S100, S126(docs/drive/kyosoku_scenarios.json、交通の方法に関する教則の再現台帳)

Run: py -3.11 examples/poc_driving_longitudinal.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く。
FULLSEYE_POC_BUDGET=reduced(CI の既定)でカメラの周期と GIF のコマを減らす)
"""
from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import drivecourse as DC  # noqa: E402
import driveworld as DW  # noqa: E402
import drivelong as DL  # noqa: E402
import rsssafety as RSS  # noqa: E402
import balltrack as BT  # noqa: E402
import annotate as AN  # noqa: E402

#: 予算: reduced(CI の既定)はカメラの周期 0.2 s・GIF 3 fps・小さい画、full は 0.1 s・5 fps。展示の数字は full の実測。
REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
TICK = 0.2 if REDUCED else 0.1                  # 車載カメラで読む周期 [s](= 判断の周期)
GIF_FPS = 2.0 if REDUCED else 5.0
GIF_WH = (400, 250) if REDUCED else (480, 300)
DT = 0.02                                       # 積分の刻み [s]
T0 = time.time()
OK = []
FRONT = 2.25                                    # 車の中心から前端 [m](4.5 m の車)
LANE_Y = 1.75                                   # 東行きの車線の中心(左側通行)
V_APPROACH = 20.0 / 3.6                         # 場内の速さ(仮定)
V_HILL = 15.0 / 3.6
YELLOW = 3.0                                    # 黄の時間 [s](仮定)
RED_TIME = 8.0
R_READ = 20.0                                   # カメラの読みを信じる距離 [m](この PoC の実測: 下の probe)
CAM_RANGE = 30.0                                # 車載カメラを回す距離 [m](30 m で既に色の一部しか読めない = probe。予算のため)


def gate(name, cond, detail=""):
    OK.append(bool(cond))
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


def main() -> int:
    """PoC の本体。"""
    print("BUDGET: %s(FULLSEYE_POC_BUDGET、CI では reduced が既定)" % ("reduced" if REDUCED else "full"))
    P = DL.long_params()
    g, crr, k = P["g"], P["c_rr"], P["k"]
    print("仮定: 質量 %.0f kg, c_rr %.3f, C_dA %.2f m², 反応 %.2f s, 制動の上限 %.1f m/s², μ %.2f, クリープ %.2f m/s²" % (
        P["mass"], crr, P["cda"], P["reaction"], P["a_brake_max"], P["mu"], P["a_creep"]))

    # ─────────────────────────── 1. 閉形式の門(世界なし) ───────────────────────────
    print("== 1. 停止距離・坂の保持・坂道発進の閉形式と積分器")
    th8, th11 = math.atan(0.08), math.atan(0.11)

    def stop_run(v, rho, b, th, p, dt=0.01):
        def cmd(t, s, vv):
            if t < rho:
                need = p["g"] * math.sin(th) + p["c_rr"] * p["g"] * math.cos(th) + p["k"] * vv * abs(vv)
                return (need, 0.0) if need >= 0 else (0.0, -need)
            return (0.0, b) if vv > 0 else (0.0, p["a_brake_max"])
        r = DL.long_simulate(0.0, v, cmd, road=th, t_end=rho + 30.0, dt=dt, params=p, t_breaks=[rho])
        return r, [e for e in r["events"] if e[0] == "stop"][0][2]

    errs, rows = [], []
    for th, name in ((0.0, "平地"), (th8, "上り 8 %"), (th11, "上り 11 %"), (-th8, "下り 8 %"), (-th11, "下り 11 %")):
        for v_kmh in (20.0, 40.0, 60.0):
            v = v_kmh / 3.6
            _, s = stop_run(v, P["reaction"], 4.0, th, P)
            d = DL.stopping_distance_grade(v, P["reaction"], 4.0, th, crr, k)
            errs.append(abs(s - d))
            rows.append((name, v_kmh, d, s))
    for name, vk, d, s in rows[1::3]:
        print("  %-8s %3.0f km/h: 閉形式 %.6f m / 積分器 %.6f m" % (name, vk, d, s))
    gate("停止距離(制動 4 m/s²、転がり・空気抵抗つき): 平地・上り・下り × 20/40/60 km/h の 15 組で閉形式と積分器が 1e-9",
         max(errs) < 1e-9, "max %.1e" % max(errs))
    p0 = DL.long_params(c_rr=0.0, cda=0.0, a_brake_max=10.0, mu=1.2)
    e_cf, e_sim = [], []
    for v in (2.0, 8.0, 16.7, 25.0):
        for rho in (0.0, 0.75, 1.5):
            ref = RSS.rss_stopping_distance(v, rho, 0.0, 6.0)
            e_cf.append(abs(DL.stopping_distance_grade(v, rho, 6.0) - ref))
            e_sim.append(abs(stop_run(v, rho, 6.0, 0.0, p0)[1] - ref))
    gate("第 2 実装: 平地・c_rr = k = 0 で rsssafety.rss_stopping_distance と一致(12 組)", max(e_cf) < 1e-12 and max(e_sim) < 1e-9,
         "閉形式 %.1e / 積分器 %.1e" % (max(e_cf), max(e_sim)))
    hold_ok, hold_rows = True, []
    for grade in (0.065, 0.08, 0.11, 0.125):
        th = math.atan(grade)
        bmin = DL.hill_hold_brake_min(th, crr, P["a_creep"])
        pz = DL.long_params(cda=0.0)
        moved = []
        for b in (bmin + 1e-9, bmin - 1e-4):
            r = DL.long_simulate(0.0, 0.0, lambda t, s, v, b=b: (pz["a_creep"], b), road=th, t_end=5.0, dt=0.01, params=pz)
            moved.append(abs(r["s"][-1]))
        hold_ok &= moved[0] == 0.0 and moved[1] > 0.0
        hold_rows.append("%.1f %%: %.4f m/s²(1e-4 足りないと 5 s で %.1e m ずり下がる)" % (100 * grade, bmin, moved[1]))
    gate("坂の保持: 最小の制動 max(0, |a_creep − g sin θ| − c_rr g cos θ) の上では動かず、1e-4 下では動く(4 勾配)", hold_ok,
         "; ".join(hold_rows))
    rb_err, rb_rows = [], []
    pz = DL.long_params(cda=0.0)
    for grade in (0.065, 0.08, 0.11, 0.125):
        for tau in (0.5, 1.0):
            th = math.atan(grade)
            cmd = DL.hill_start_command(1.0, tau, 2.0, 3.0, a_creep=pz["a_creep"], technique="gap")
            r = DL.long_simulate(0.0, 0.0, cmd, road=th, t_end=6.0, dt=0.01, params=pz, t_breaks=cmd.t_breaks)
            rb = -min(0.0, float(r["s"].min()))
            cf = DL.hill_start_rollback(th, tau, 2.0, crr, pz["a_creep"])["rollback"]
            rb_err.append(abs(rb - cf))
            rb_rows.append((grade, tau, cf))
    gate("坂道発進のずり下がり(ブレーキを離して τ 後に駆動 2 m/s²): ½a₁τ² + (a₁τ)²/(2a₂) と積分器が 1e-9(4 勾配 × τ 0.5/1.0)",
         max(rb_err) < 1e-9, "max %.1e; 11 %%・τ 1.0 s で %.3f m" % (max(rb_err), [c for g_, t_, c in rb_rows if g_ == 0.11 and t_ == 1.0][0]))

    # ─────────────────────────── 2. 世界(交差点 → 坂道コース) ───────────────────────────
    print("== 2. 世界: 幹線の交差点(信号・停止線)→ 連絡路 → 坂道コース(緩 8 %・頂上 4 m・急 11 %、高さ 1.5 m)")
    I = DC.course_intersection()
    SL = DC.course_slope()
    L_sl = SL["params"]["length"]
    X_RAMP = 33.4
    ELS = [I, DC.course_road(55.0, 7.0), DC.course_road(10.0, 7.0), SL, DC.course_road(16.0, 7.0)]
    PLACE = [(0.0, 0.0, 0.0), (-23.45, 0.0, math.pi), (23.45, 0.0, 0.0), (X_RAMP, 0.0, 0.0), (X_RAMP + L_sl - 0.05, 0.0, 0.0)]
    LAY = DC.course_layout(ELS, PLACE)
    WORLD = DW.world_build(LAY, props=[("sedan", 5.0, -1.75, math.pi, None, "white"), ("cone", 30.0, 3.3, 0.0)])
    # 停止線の手前の縁(車が越えてはいけない縁)を世界のメッシュから読む: world_build は線を流入側へ 0.45 m 幅で塗る
    stop_objs = [o for o in WORLD["objects"] if o["name"] == "stop_line"]
    near_edges = []
    for o in stop_objs:
        f0, f1 = o["faces"] if "faces" in o else (None, None)
        if f0 is None:
            continue
        Vv = WORLD["V"][WORLD["F"][f0:f1]].reshape(-1, 3)
        if Vv[:, 0].max() < 0 and Vv[:, 1].min() > -0.1 and Vv[:, 1].max() < 3.6 and np.ptp(Vv[:, 0]) < 1.0:
            near_edges.append(float(Vv[:, 0].min()))
    X_LINE_TABLE = float(I["stop_lines"][0][0][0])
    X_LINE = min(near_edges) if near_edges else X_LINE_TABLE - 0.45
    print("  東行きの停止線: stop_lines の x = %.2f、塗った線の手前の縁 = %.2f(%s)。PoC ⑯ は x = %.2f を基準に 0.3 m 手前で止めて"
          "いたので、前端は塗った線の上にあった —— ここでは手前の縁を基準にする" % (
              X_LINE_TABLE, X_LINE, "メッシュから" if near_edges else "メッシュの面索引が無いので幅 0.45 m から", X_LINE_TABLE))
    # 坂道の途中の一時停止の線(緩い上りの途中、水平 14 m)を斜面の上に塗る
    X_HILL = X_RAMP + 14.0
    z_h = float(DC.slope_height(SL, 14.0))
    z_h2 = float(DC.slope_height(SL, 14.45))
    Vh = np.array([[X_HILL, 0.0, z_h + 0.01], [X_HILL, 3.5, z_h + 0.01], [X_HILL + 0.45, 3.5, z_h2 + 0.01], [X_HILL + 0.45, 0.0, z_h2 + 0.01]])
    DW.world_add(WORLD, Vh, np.array([[0, 1, 2], [0, 2, 3]]), 9, DW._LINE_COLOR, name="hill_stop_line")
    # driveworld は坂道要素の縁石と白線を z = 0 に引く(斜面は面だけ)ので、横から見ると坂が地面に紛れる。この PoC では
    # 斜面の両側に擁壁(地面から縦断まで)と、斜面の上の白線を足す(driveworld で縁石を縦断に沿わせるのは次の課題)。
    prof = [(X_RAMP + float(xp), float(zp)) for xp, zp in SL["profile"]]
    for side in (-1.0, 1.0):
        yw = side * (SL["params"]["width"] / 2 + 0.3)
        Vw, Fw = [], []
        for (xa, za), (xb, zb) in zip(prof[:-1], prof[1:]):
            n0 = len(Vw)
            Vw += [[xa, yw, 0.0], [xb, yw, 0.0], [xb, yw, zb + 0.15], [xa, yw, za + 0.15]]
            Fw += [[n0, n0 + 1, n0 + 2], [n0, n0 + 2, n0 + 3]]
        DW.world_add(WORLD, np.array(Vw), np.array(Fw), 1, (0.78, 0.74, 0.66), name="ramp_wall")
        yl = side * (SL["params"]["width"] / 2 - 0.2)
        Vl, Fl = [], []
        for (xa, za), (xb, zb) in zip(prof[:-1], prof[1:]):
            n0 = len(Vl)
            Vl += [[xa, yl - 0.06, za + 0.01], [xb, yl - 0.06, zb + 0.01], [xb, yl + 0.06, zb + 0.01], [xa, yl + 0.06, za + 0.01]]
            Fl += [[n0, n0 + 1, n0 + 2], [n0, n0 + 2, n0 + 3]]
        DW.world_add(WORLD, np.array(Vl), np.array(Fl), 9, DW._LINE_COLOR, name="ramp_line")
    X0 = X_LINE - 60.0 - FRONT                                  # 出発: 前端が停止線の 60 m 手前
    X_END = X_RAMP + L_sl + 15.0
    ROAD = DL.road_profile([[X0, 0.0], [X_RAMP, 0.0]] + [[X_RAMP + x, z] for x, z in SL["profile"][1:]] + [[X_END, 0.0]])
    l_of_x = lambda x: float(np.interp(x, ROAD["x"], ROAD["l"]))
    x_of_l = lambda l: float(np.interp(l, ROAD["l"], ROAD["x"]))
    L_LINE, L_HILL, L_RAMP = l_of_x(X_LINE), l_of_x(X_HILL), l_of_x(X_RAMP)
    L_END_LINE = l_of_x(X_END - 3.0)
    print("  縦断: 弧長 %.2f m(水平 %.2f m)、折れ点 %s" % (ROAD["l"][-1], X_END - X0, ", ".join("%.2f" % v for v in ROAD["l"])))

    # 信号(東行きの対面、交差点の向こう側)と、車載カメラで読む画像処理(PoC ⑯ の read_signal に黄を足したもの)
    SIG = [i for i, o in enumerate(WORLD["objects"]) if o["name"] == "traffic_light"
           and abs(o["pose"][0] - I["signal_poses"][0][0]) < 0.1 and abs(o["pose"][1] - I["signal_poses"][0][1]) < 0.1][0]
    LAMPS = np.array([WORLD["V"][WORLD["F"][f0:f1]].reshape(-1, 3).mean(axis=0)
                      for _kind, (f0, f1) in WORLD["objects"][SIG]["lamp_faces"].items()])
    K = DW.camera_intrinsics(60.0, 640, 400)
    COLORS = {c: np.array(DW._LAMP[c]) for c in ("red", "yellow", "green")}

    def cam_pose(l):
        x = x_of_l(l)
        return DW.camera_pose((x + 0.5, LANE_Y, 1.35), (x + 20.0, LANE_Y, 0.9))

    def read_signal(img, Pc, roi=24):
        """地図の灯火の位置を投影した ROI で、色度の検出 op(balltrack.ball_detect)が点いた円盤を探す。1 色だけ → その色、
        それ以外 → 'unknown'(fail-closed)。真値(面 ID)は使わない。"""
        col, row, dep = DW.world_project_points(LAMPS, Pc, K)
        if not np.all(dep > 0):
            return "unknown"
        c0, c1 = max(0, int(col.min()) - roi), min(img.shape[1], int(col.max()) + roi + 1)
        r0, r1 = max(0, int(row.min()) - roi), min(img.shape[0], int(row.max()) + roi + 1)
        if c1 - c0 < 4 or r1 - r0 < 4:
            return "unknown"
        crop = img[r0:r1, c0:c1]
        lit = []
        for name, colr in COLORS.items():
            dets = BT.ball_detect(crop, mode="chroma", color=tuple(float(v) for v in colr), color_tol=0.15, radius_range=(1.0, 14.0))
            if any(crop[min(crop.shape[0] - 1, int(round(d["row"]))), min(crop.shape[1] - 1, int(round(d["col"])))].max() > 0.5
                   for d in dets):
                lit.append(name)
        return lit[0] if len(lit) == 1 else "unknown"

    t = time.time()
    probe = {}
    for dline in ((40.0, 30.0, 25.0, 20.0, 10.0, 2.0) if not REDUCED else (30.0, 20.0, 10.0, 2.0)):
        res = []
        for st in ("red", "yellow", "green"):
            DW.set_signal_state(WORLD, SIG, st)
            Pc = cam_pose(L_LINE - FRONT - dline)
            res.append(read_signal(DW.world_camera(WORLD, Pc, K, 640, 400)["color"], Pc) == st)
        probe[dline] = res
    reach = max([d for d, r in probe.items() if all(r) and all(all(probe[d2]) for d2 in probe if d2 < d)], default=0.0)
    print("  カメラの読みの届く距離(停止線から): %s → 全色を読めるのは %.0f m 以内(%.1f s)" % (
        ", ".join("%.0f m %s" % (d, "".join("o" if x else "x" for x in r)) for d, r in probe.items()), reach, time.time() - t))
    gate("車載カメラが赤・黄・緑を読める距離 ≥ 読みを信じる距離 R_READ = %.0f m(これより遠い 'unknown' は判断に使わない)" % R_READ,
         reach >= R_READ, "%.0f m" % reach)

    # ─────────────────────────── 3. 時計つきで走る ───────────────────────────
    print("== 3. 時計つきで走る(カメラと判断は %.1f s ごと、積分は %.2f s、事象で刻みを切る)" % (TICK, DT))
    T_Y = (60.0 - 17.0) / V_APPROACH                           # 世界の時計: 前端が停止線の約 17 m 手前に来る頃に黄
    T_R, T_G = T_Y + YELLOW, T_Y + YELLOW + RED_TIME

    def world_signal(tt, lamps_on=True):
        if not lamps_on:
            return "off"
        return "green" if tt < T_Y else ("yellow" if tt < T_R else ("red" if tt < T_G else "green"))

    def speed_cmd(v_set):
        """速さを保つ(前送り = 坂 + 転がり + 空気抵抗)+ 比例(加速 1.5・減速 2.0 m/s² で頭打ち)。"""
        def c(tt, s, v):
            _, sn, cs = DL.road_eval(ROAD, s)
            u = g * sn + crr * g * cs + k * v * abs(v) + min(1.5, max(-2.0, 1.0 * (v_set - v)))
            return (u, 0.0) if u >= 0 else (0.0, -u)
        return c

    def drive(lamps_on=True, reaction=None, mu=None, record_ticks=True, t_max=90.0, only_intersection=False):
        """閉ループの走行。返り値 = dict(軌跡・事象・読み・採点の材料)。"""
        p = DL.long_params(reaction=P["reaction"] if reaction is None else reaction, mu=P["mu"] if mu is None else mu)
        st = {"t": 0.0, "s": l_of_x(X0), "v": V_APPROACH}
        chunks, reads, log = [], [], []
        cmd = [speed_cmd(V_APPROACH)]
        brk = [[]]

        def advance(t_to):
            if t_to <= st["t"] + 1e-12:
                return
            r = DL.long_simulate(st["s"], st["v"], cmd[0], road=ROAD, t_end=t_to, dt=DT, params=p, t_breaks=brk[0], t0=st["t"])
            chunks.append(r)
            st["t"], st["s"], st["v"] = float(r["t"][-1]), float(r["s"][-1]), float(r["v"][-1])
            for e in r["events"]:
                log.append(e)

        mode, plan, t_green_read, t_move = "approach", None, None, None
        stop_at_line = None
        hill = {}
        ended = False
        while st["t"] < t_max and not ended:
            tt = st["t"]
            dist = L_LINE - (st["s"] + FRONT)
            if mode in ("approach", "stopping", "waiting"):
                DW.set_signal_state(WORLD, SIG, world_signal(tt, lamps_on))
                read = "unknown"
                if -1.0 < dist <= CAM_RANGE:                            # これより遠いと灯火は読めない(probe)→ 撮らない
                    Pc = cam_pose(st["s"])
                    read = read_signal(DW.world_camera(WORLD, Pc, K, 640, 400)["color"], Pc)
                reads.append((tt, dist, world_signal(tt, lamps_on), read, st["v"]))
                if mode == "approach":
                    act = read in ("yellow", "red") or (read == "unknown" and dist <= R_READ)
                    if act:
                        pl = DL.stop_line_plan(st["v"], dist, 0.0, p, t0=tt)
                        if read == "yellow" and (pl["saturated"] or pl["predicted_gap"] < 0):
                            log.append(("yellow_go", tt, st["s"], 0.0))     # 黄: 安全に止まれない → 進む(道路交通法施行令 第 2 条)
                        else:
                            plan = pl
                            plan["read"] = read
                            plan["dist"] = dist
                            cmd[0] = DL.plan_command(pl, road=ROAD, params=p, before=speed_cmd(V_APPROACH))
                            brk[0] = pl["t_breaks"]
                            mode = "stopping"
                elif mode == "stopping" and st["v"] == 0.0:
                    mode = "waiting"
                    stop_at_line = {"t": tt, "s": st["s"], "gap": dist}
                elif mode == "waiting":
                    if read == "green" and t_green_read is None:
                        t_green_read = tt
                        t_go = tt + p["reaction"]                          # 読んでから足を踏み替える(反応時間)
                        hold = cmd[0]
                        go = speed_cmd(V_HILL)
                        cmd[0] = (lambda h, gcmd, tg: (lambda t_, s_, v_: h(t_, s_, v_) if t_ < tg else gcmd(t_, s_, v_)))(hold, go, t_go)
                        brk[0] = [t_go]
                        mode = "crossing"
                        t_move = t_go
                if only_intersection and mode == "crossing":
                    advance(min(tt + 3.0, t_max))
                    break
                advance(tt + TICK)
                continue
            if mode == "crossing":
                if st["s"] >= L_RAMP + 0.5:                                  # 車の中心が上りに入った → 指定の場所で止まる計画
                    _, sn, _ = DL.road_eval(ROAD, st["s"] + 1e-9)
                    d_h = L_HILL - (st["s"] + FRONT)
                    pl = DL.stop_line_plan(st["v"], d_h, math.asin(sn), p, t0=tt)
                    hill["plan"] = pl
                    hill["dist"] = d_h
                    cmd[0] = DL.plan_command(pl, road=ROAD, params=p)
                    brk[0] = pl["t_breaks"]
                    mode = "hill_stopping"
                advance(tt + TICK)
                continue
            if mode == "hill_stopping":
                if st["v"] == 0.0:
                    hill["stop"] = {"t": tt, "s": st["s"], "gap": L_HILL - (st["s"] + FRONT)}
                    t_rel = tt + 2.0                                          # 一時停止 2 s(仮定)
                    tau = 0.5
                    _, hb = DL._caps(p, 1.0)
                    hs = DL.hill_start_command(t_rel, tau, 1.5, hb, a_creep=p["a_creep"], technique="overlap")
                    up = speed_cmd(V_HILL)
                    cmd[0] = (lambda h, u, tu: (lambda t_, s_, v_: h(t_, s_, v_) if t_ < tu else u(t_, s_, v_)))(hs, up, t_rel + tau)
                    brk[0] = [t_rel, t_rel + tau]
                    hill["t_release"] = t_rel
                    mode = "hill_start"
                advance(tt + TICK)
                continue
            if mode == "hill_start":
                if st["s"] >= L_HILL + 2.0:
                    mode = "descent"
                advance(tt + TICK)
                continue
            if mode == "descent":
                if st["s"] >= l_of_x(X_RAMP + L_sl) + 1.0 and "end" not in hill:
                    d_e = L_END_LINE - (st["s"] + FRONT)
                    pl = DL.stop_line_plan(st["v"], d_e, 0.0, p, t0=tt)
                    hill["end"] = pl
                    cmd[0] = DL.plan_command(pl, road=ROAD, params=p)
                    brk[0] = pl["t_breaks"]
                    mode = "ending"
                advance(tt + TICK)
                continue
            if mode == "ending":
                if st["v"] == 0.0:
                    hill["end_stop"] = {"t": tt, "gap": L_END_LINE - (st["s"] + FRONT)}
                    advance(tt + 1.0)
                    ended = True
                    continue
                advance(tt + TICK)
                continue
        tr = {key: np.concatenate([c[key] for c in chunks]) for key in ("t", "s", "v", "a", "drive", "brake", "z", "stopped")}
        eres = max(float(np.abs(DL.long_energy_residual(c)).max()) for c in chunks)
        return {"tr": tr, "chunks": chunks, "reads": reads, "log": log, "plan": plan, "stop": stop_at_line,
                "t_green_read": t_green_read, "t_move": t_move, "hill": hill, "energy": eres, "p": p}

    t = time.time()
    RUN = drive()
    t_drive = time.time() - t
    tr = RUN["tr"]
    pl, stp, hill = RUN["plan"], RUN["stop"], RUN["hill"]
    print("  走行 %.1f s(シミュレーションの時計)、計算 %.1f s、カメラ %d 回" % (tr["t"][-1], t_drive, len(RUN["reads"])))
    print("  交差点: t = %.2f s に '%s' を読んだ(前端から停止線 %.2f m、%.1f km/h)→ 空走 %.2f m + 待ち %.2f m + 制動 %.2f m(%d 段)"
          " → t = %.2f s に停止、停止線の手前 %.3f m" % (
              pl["t0"], pl["read"], pl["dist"], 3.6 * pl["v"], pl["d_react"], pl["d_cruise"], pl["d_brake"], pl["stages"],
              stp["t"], stp["gap"]))
    t_green_world = T_G
    moved = tr["s"][(tr["t"] > stp["t"]) & (tr["t"] < RUN["t_move"] - 1e-9)]
    still = float(np.ptp(moved)) if len(moved) else 0.0
    delay = None
    mv = [e for e in RUN["log"] if e[0] == "move" and e[1] > stp["t"]]
    if mv:
        delay = mv[0][1] - t_green_world
    print("  信号: 世界の青は t = %.2f s、カメラが 'green' を読んだのは t = %.2f s、動き出し t = %.2f s(遅れ %.2f s = 周期 + 反応)。"
          "赤の間の動き %.1e m" % (t_green_world, RUN["t_green_read"], mv[0][1] if mv else float("nan"), delay if delay else float("nan"), still))
    gate("停止線: 前端が停止線の手前 0〜2 m に止まる(減点 0)。予測と積分器が 1e-9", 0.0 <= stp["gap"] <= 2.0 and abs(stp["gap"] - pl["predicted_gap"]) < 1e-9,
         "手前 %.6f m(予測 %.6f m)" % (stp["gap"], pl["predicted_gap"]))
    reads_in = [r for r in RUN["reads"] if 0.0 <= r[1] <= R_READ]
    match = sum(r[2] == r[3] for r in reads_in)
    gate("閉ループ: 赤の間 1 mm も動かず、'green' を読んでから発進。読みを信じる距離の中の読みは世界の状態と全部一致",
         still == 0.0 and RUN["t_green_read"] is not None and RUN["t_green_read"] >= T_G and match == len(reads_in) and len(reads_in) > 5,
         "%d / %d 一致" % (match, len(reads_in)))
    hs, hst = hill["plan"], hill["stop"]
    after = tr["t"] >= hill["t_release"]
    s_after = tr["s"][after]
    rollback = max(0.0, hst["s"] - float(s_after.min()))
    print("  坂道: 上り %.1f %% で前端から線 %.2f m の所で計画 → 空走 %.2f + 待ち %.2f + 制動 %.2f m → 停止、線の手前 %.3f m。"
          "2 s 保持してからアクセルを踏み(1.5 m/s²)0.5 s 後にブレーキを離す → 逆行 %.2e m" % (
              100 * math.tan(hs["theta"]), hill["dist"], hs["d_react"], hs["d_cruise"], hs["d_brake"], hst["gap"], rollback))
    desc = (tr["s"] > l_of_x(X_RAMP + 22.75)) & (tr["s"] < l_of_x(X_RAMP + L_sl))
    v_desc = float(tr["v"][desc].max()) * 3.6 if desc.any() else float("nan")
    print("  下り 11 %%: 最高 %.2f km/h(速さの管理 = 前送り + 比例、制動の平均 %.2f m/s²)。終点の停止 手前 %.3f m" % (
        v_desc, float(tr["brake"][desc].mean()) if desc.any() else float("nan"), hill["end_stop"]["gap"]))
    events = [{"kind": "stop", "gap": stp["gap"], "signal": "red"}, {"kind": "brake", "stages": pl["stages"]},
              {"kind": "start", "rollback": 0.0, "delay": delay},
              {"kind": "hold", "creep": still},
              {"kind": "stop", "gap": hst["gap"]}, {"kind": "brake", "stages": hs["stages"]},
              {"kind": "start", "rollback": rollback}]
    SC = DL.skill_test_score(events, venue="場内")
    print("  採点(場内): 減点 %d、得点 %s、%s" % (SC["total"], SC["score"], "合格" if SC["passed"] else "不合格"))
    gate("坂道: 指定の線の手前 0〜2 m に止まり、逆行 < 0.3 m(減点 0)", 0.0 <= hst["gap"] <= 2.0 and rollback < 0.3,
         "手前 %.4f m、逆行 %.2e m" % (hst["gap"], rollback))
    gate("技能試験の採点(警察庁 丙運発第 12 号): 減点 0 で 100 点", SC["total"] == 0 and SC["score"] == 100,
         "; ".join("%s %s" % (d[0], d[1]) for d in SC["deductions"]) or "減点なし")
    # 速さの管理(前送り + 比例)は速さに連続に依存する指令なので、その区間の RK4 は厳密でない(dt⁴ の打ち切り誤差)→ 閾値 1e-8。
    # 指令が区分的に一定の区間だけなら 1e-12 の桁(1. の門の走行)
    gate("エネルギー収支: ½v² + g z + W_rr + W_drag + W_brake − W_drive が全区間で一定(%d 区間、比例制御の区間を含む)" % len(RUN["chunks"]),
         RUN["energy"] < 1e-8, "max %.1e J/kg(W_rr %.1f・W_drag %.1f・W_brake %.1f・W_drive %.1f J/kg)" % (
             RUN["energy"], sum(c["W_rr"][-1] for c in RUN["chunks"]), sum(c["W_drag"][-1] for c in RUN["chunks"]),
             sum(c["W_brake"][-1] for c in RUN["chunks"]), sum(c["W_drive"][-1] for c in RUN["chunks"])))

    # ─────────────────────────── 4. つまみ ───────────────────────────
    print("== 4. つまみ: 反応時間・路面の μ・坂の勾配を動かすと減点が出る(しきい値は閉形式で別に計算)")
    v_d, d_d = pl["v"], pl["dist"]
    _, bcap = DL._caps(P, 1.0)
    rho_star = (d_d - DL.stopping_distance_grade(v_d, 0.0, bcap, 0.0, crr, k)) / v_d
    knob_rho = []
    for rho in (0.5, 0.75, 1.0, 1.5, 2.0, rho_star - 0.05, rho_star + 0.05, 3.0):
        q = DL.long_params(reaction=rho)
        plq = DL.stop_line_plan(v_d, d_d, 0.0, q)
        r = DL.long_simulate(0.0, v_d, DL.plan_command(plq, params=q), t_end=40.0, dt=DT, params=q, t_breaks=plq["t_breaks"])
        gap = d_d - [e for e in r["events"] if e[0] == "stop"][0][2]
        sc = DL.skill_test_score([{"kind": "stop", "gap": gap, "signal": "red"}, {"kind": "brake", "stages": plq["stages"]}])
        knob_rho.append((rho, gap, plq["stages"], sc))
    for rho, gap, stg, sc in knob_rho:
        print("  反応 %.2f s: 手前 %+.3f m、%d 段 → %s" % (rho, gap, stg, "; ".join("%s %s" % (d[0], "中止" if d[1] is None else d[1])
                                                                   for d in sc["deductions"]) or "減点 0"))
    below = [x for x in knob_rho if x[0] < rho_star]
    above = [x for x in knob_rho if x[0] > rho_star]
    gate("つまみ(反応時間): 閉形式のしきい値 ρ* = (d − 上限制動の停止距離)/v = %.3f s の手前は線を越えず、越えると線を越えて減点" % rho_star,
         all(x[1] >= 0 for x in below) and all(x[1] < 0 and x[3]["total"] + x[3]["test_stopped"] > 0 for x in above)
         and knob_rho[1][3]["total"] == 0, "反応 %.2f s → 手前 %+.3f m / %.2f s → %+.3f m" % (
             rho_star - 0.05, [x[1] for x in knob_rho if x[0] == rho_star - 0.05][0], rho_star + 0.05,
             [x[1] for x in knob_rho if x[0] == rho_star + 0.05][0]))
    # μ: 反応 0.75 s・同じ検出距離で、止まれる μ の下限を閉形式(stopping_distance_grade の二分法)で
    lo, hi = 0.05, 1.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if DL.stopping_distance_grade(v_d, P["reaction"], min(P["a_brake_max"], mid * g), 0.0, crr, k) <= d_d:
            hi = mid
        else:
            lo = mid
    mu_star = hi
    knob_mu = []
    for mu in (0.8, 0.6, 0.4, mu_star + 0.01, mu_star - 0.01, 0.1):
        q = DL.long_params(mu=mu)
        plq = DL.stop_line_plan(v_d, d_d, 0.0, q)
        r = DL.long_simulate(0.0, v_d, DL.plan_command(plq, params=q), t_end=60.0, dt=DT, params=q, t_breaks=plq["t_breaks"])
        gap = d_d - [e for e in r["events"] if e[0] == "stop"][0][2]
        knob_mu.append((mu, gap, plq["stages"], DL.skill_test_score([{"kind": "stop", "gap": gap, "signal": "red"},
                                                                    {"kind": "brake", "stages": plq["stages"]}])))
    for mu, gap, stg, sc in knob_mu:
        print("  μ %.3f: 手前 %+.3f m、%d 段 → %s" % (mu, gap, stg, "; ".join("%s %s" % (d[0], "中止" if d[1] is None else d[1])
                                                            for d in sc["deductions"]) or "減点 0"))
    gate("つまみ(路面の μ、制動の上限 μ g): 閉形式の下限 μ* = %.4f の上は線の手前、下は越える(雨の路面は次の巡でここに入る)" % mu_star,
         all((x[1] >= -1e-9) == (x[0] >= mu_star) for x in knob_mu), "μ* ± 0.01 → %+.3f / %+.3f m" % (knob_mu[3][1], knob_mu[4][1]))
    # 勾配: 踏み替え(gap)τ = 1.0 s の下手な坂道発進で、逆行の減点が勾配につれて重くなる。しきい値の勾配は閉形式から
    knob_gr = []
    pz = DL.long_params(cda=0.0)
    # 駆動 1.5 m/s² が坂に負ける勾配(a₂ ≤ 0、約 15.5 % 超)は閉形式が inf(登れない)なので入れない
    for grade in (0.065, 0.08, 0.09, 0.10, 0.11, 0.125, 0.14):
        th = math.atan(grade)
        c = DL.hill_start_command(1.0, 1.0, 1.5, 3.0, a_creep=pz["a_creep"], technique="gap")
        cfd = DL.hill_start_rollback(th, 1.0, 1.5, crr, pz["a_creep"])
        cf = cfd["rollback"]
        # 逆行が止まる時刻(閉形式)より十分長く積分する(最初の版は 8 s で打ち切り、15 % で 0.015 m 足りなかった)
        t_rec = 2.0 + (cfd["v_back"] / cfd["a2"] if cfd["a2"] > 0 else 0.0) + 3.0
        r = DL.long_simulate(0.0, 0.0, c, road=th, t_end=t_rec, dt=DT, params=pz, t_breaks=c.t_breaks)
        rb = -min(0.0, float(r["s"].min()))
        sc = DL.skill_test_score([{"kind": "start", "rollback": rb}])
        knob_gr.append((grade, rb, cf, sc))
        print("  勾配 %5.1f %%: 逆行 %.3f m(閉形式 %.3f)→ %s" % (100 * grade, rb, cf, "; ".join(
            "%s %s" % (d[0], "中止" if d[1] is None else d[1]) for d in sc["deductions"]) or "減点 0"))
    levels = [0 if not x[3]["deductions"] else (99 if x[3]["test_stopped"] else x[3]["total"]) for x in knob_gr]
    gate("つまみ(勾配、踏み替え τ 1.0 s): 逆行は閉形式と 1e-9、減点は勾配につれて単調に重くなり、規格の範囲の中で減点 0 から出る",
         max(abs(x[1] - x[2]) for x in knob_gr) < 1e-9 and all(np.diff(levels) >= 0) and levels[0] == 0 and max(levels) > 0,
         "減点 %s" % levels)
    # ゼロ点: 灯火を消すと 'unknown' → 読みを信じる距離で止まり、青が来ない(読めない)ので発進しない
    t = time.time()
    OFF = drive(lamps_on=False, t_max=T_R + 4.0, only_intersection=True)
    off_reads = {r[3] for r in OFF["reads"] if r[1] <= R_READ}
    gate("ゼロ点: 灯火を消すと 'unknown' が続き、読みを信じる距離で止まって発進しない(fail-closed)",
         OFF["stop"] is not None and OFF["t_green_read"] is None and off_reads == {"unknown"} and 0.0 <= OFF["stop"]["gap"] <= 2.0,
         "停止 手前 %.3f m、止まってから %.1f s 待っても発進せず、読み %s(%.1f s)" % (
             OFF["stop"]["gap"] if OFF["stop"] else float("nan"), (T_R + 4.0 - OFF["stop"]["t"]) if OFF["stop"] else float("nan"),
             sorted(off_reads), time.time() - t))

    # ─────────────────────────── 5. 図 ───────────────────────────
    if figs.enabled():
        print("== 5. 図")
        t = time.time()
        EGO = DW.load_asset("sedan", paint="blue")
        Wg, Hg = GIF_WH
        Kc = DW.camera_intrinsics(55.0, Wg, Hg)
        frames = []
        t_frames = np.arange(0.0, tr["t"][-1], 1.0 / GIF_FPS)

        def ego_V(l):
            x = x_of_l(l)
            z, sn, cs = DL.road_eval(ROAD, l)
            V = EGO["V"].copy()
            c_, s_ = cs, sn                                               # 車体を勾配だけ前上がりに回す
            vx, vz = V[:, 0].copy(), V[:, 2].copy()
            V[:, 0] = x + c_ * vx - s_ * vz
            V[:, 2] = z + s_ * vx + c_ * vz
            V[:, 1] = V[:, 1] + LANE_Y
            return V

        def dial(img, v_kmh, cx, cy, R=34, vmax=40.0):
            """速度計: 半円の目盛りと針。"""
            out = img.copy()
            H_, W_ = out.shape[:2]
            yy, xx = np.mgrid[0:H_, 0:W_]
            rr = np.hypot(xx - cx, yy - cy)
            ang = np.arctan2(cy - yy, xx - cx)
            face = (rr <= R + 4) & (yy <= cy + 6)
            out[face] = out[face] * 0.25 + 0.75 * np.array([0.08, 0.08, 0.1])
            ring = (np.abs(rr - R) < 1.2) & (ang >= 0) & (ang <= math.pi)
            out[ring] = 0.9
            for kk in range(0, int(vmax) + 1, 10):
                a = math.pi * (1 - kk / vmax)
                for q in np.linspace(R - 7, R, 8):
                    px, py = int(round(cx + q * math.cos(a))), int(round(cy - q * math.sin(a)))
                    if 0 <= px < W_ and 0 <= py < H_:
                        out[py, px] = 0.95
            a = math.pi * (1 - min(v_kmh, vmax) / vmax)
            for q in np.linspace(0, R - 3, 60):
                px, py = int(round(cx + q * math.cos(a))), int(round(cy - q * math.sin(a)))
                out[max(0, py - 1):py + 1, max(0, px - 1):px + 1] = (1.0, 0.35, 0.2)
            return out

        for tf in t_frames:
            l = float(np.interp(tf, tr["t"], tr["s"]))
            v = float(np.interp(tf, tr["t"], tr["v"]))
            x = x_of_l(l)
            z = DL.road_eval(ROAD, l)[0]
            DW.set_signal_state(WORLD, SIG, world_signal(tf))
            # 斜め後ろ・横から(坂の傾きが見える向き)
            Pc = DW.camera_pose((x - 8.0, LANE_Y - 8.0, z + 3.2), (x + 3.0, LANE_Y, z + 0.6))
            img = DW.world_camera(WORLD, Pc, Kc, Wg, Hg, ego=(ego_V(l), EGO["F"], EGO["color"]))["color"]
            if l + FRONT < L_LINE + 1.0:
                what, dd = "停止線", L_LINE - (l + FRONT)
            elif l + FRONT < L_HILL + 1.0:
                what, dd = "坂の停止線", L_HILL - (l + FRONT)
            else:
                what, dd = "終点", L_END_LINE - (l + FRONT)
            rd = [r_ for r_ in RUN["reads"] if r_[0] <= tf + 1e-9]
            ph = "走行"
            for plan_, t_end_ in ((pl, stp["t"]), (hs, hst["t"]), (hill["end"], hill["end_stop"]["t"])):
                for (t_s, kind, _dr, _br) in plan_["phases"]:
                    if plan_["t0"] <= tf < t_end_ and t_s <= tf:
                        ph = {"react": "反応(空走)", "cruise": "待ち", "brake1": "制動 1 段目", "brake2": "制動 2 段目"}[kind]
            if stp["t"] <= tf < RUN["t_move"]:
                ph = "停止(赤)" if world_signal(tf) != "green" else "青を読んだ → 反応"
            if hst["t"] <= tf < hill["t_release"]:
                ph = "坂で一時停止(保持)"
            elif hill["t_release"] <= tf < hill["t_release"] + 0.5:
                ph = "アクセル → ブレーキを離す"
            if tf >= hill["end_stop"]["t"]:
                ph = "終点で停止"
            txt = "t = %5.1f s   %4.1f km/h\n%s まで %5.2f m   %s\n信号(世界)%s / カメラ %s" % (
                tf, 3.6 * v, what, dd, ph, world_signal(tf), rd[-1][3] if rd and tf < RUN["t_move"] + 1 else "-")
            img = np.asarray(AN.text_box(img, txt, (6, 6), anchor="lt", font_size=11), dtype=float).copy()
            # 左下: 道の縦断(高さを 6 倍)と車の位置、停止線の印
            iw, ih, ox, oy = 170, 44, 6, Hg - 50
            img[oy:oy + ih, ox:ox + iw] = img[oy:oy + ih, ox:ox + iw] * 0.3 + 0.7 * np.array([0.1, 0.1, 0.12])
            xs_ = np.linspace(ROAD["x"][0], ROAD["x"][-1], iw)
            zs_ = np.interp(xs_, ROAD["x"], ROAD["z"])
            for i_, zz in enumerate(zs_):
                img[oy + ih - 6 - int(round(zz / 1.5 * 24)), ox + i_] = (0.85, 0.85, 0.85)
            for xm, colr in ((X_LINE, (1, 1, 1)), (X_HILL, (1, 1, 1)), (X_END - 3.0, (1, 1, 1))):
                i_ = int(round((xm - xs_[0]) / (xs_[-1] - xs_[0]) * (iw - 1)))
                img[oy + 4:oy + ih - 4, ox + i_] = colr
            i_ = int(round((x - xs_[0]) / (xs_[-1] - xs_[0]) * (iw - 1)))
            zc = oy + ih - 6 - int(round(z / 1.5 * 24))
            img[max(oy, zc - 3):zc + 1, max(ox, ox + i_ - 2):ox + i_ + 3] = (1.0, 0.35, 0.2)
            frames.append(dial(img, 3.6 * v, Wg - 44, Hg - 12))
        print("  GIF %d コマ(%.0f fps、%d × %d)%.1f s" % (len(frames), GIF_FPS, Wg, Hg, time.time() - t))
        figs.save_gif("drive_with_time", frames, fps=GIF_FPS,
                      caption="時計つきで走る: 車載カメラ(画像処理)が黄を読んだ瞬間から反応 %.2f s(空走)→ 2 段のブレーキで停止線の手前 "
                              "%.2f m に止まり、青を読んで発進。坂道コース(緩 8 %%)の途中の線の手前 %.2f m で一時停止し、アクセルを踏んでから"
                              "ブレーキを離して逆行 %.1e m、急 11 %% の下りは %.1f km/h 以下で下る。左上 = 時計・速さ・線までの距離・段、"
                              "右下 = 速度計。" % (P["reaction"], stp["gap"], hst["gap"], rollback, v_desc))
        figs.save_plot("speed_distance", [("速さ [km/h]", tr["t"], 3.6 * tr["v"]),
                                         ("高さ z × 10 [m]", tr["t"], 10 * tr["z"]),
                                         ("制動 × 5 [m/s²]", tr["t"], 5 * tr["brake"])],
                       xlabel="時刻 [s]", ylabel="",
                       caption="速さ・路面の高さ・ブレーキの時系列。交差点では反応(空走)の間は速さを保ち、2 段で止まる(制動の 2 つの段)。"
                               "赤の間は 0、青を読んで発進。坂で一時停止して発進し、急な下りでは制動で速さを保つ。")
        vv = np.linspace(1, 60, 60) / 3.6
        curves = [("%s(閉形式)" % nm, vv * 3.6, [DL.stopping_distance_grade(x, P["reaction"], 4.0, th, crr, k) for x in vv])
                  for th, nm in ((th11, "上り 11 %"), (0.0, "平地"), (-th11, "下り 11 %"))]
        curves.append(("積分器(15 組)", [r_[1] for r_ in rows], [r_[3] for r_ in rows]))
        curves.append(("rsssafety(平地・抵抗なし)", vv * 3.6, [RSS.rss_stopping_distance(x, P["reaction"], 0.0, 4.0) for x in vv]))
        figs.save_plot("stopping_distance", curves, kinds=["line", "line", "line", "scatter", "line"],
                       xlabel="速さ [km/h]", ylabel="停止距離 [m]",
                       caption="停止距離 = 空走 vρ + 制動距離(制動 4 m/s²、反応 %.2f s)。上りは短く下りは長い。点は積分器(閉形式と 1e-9)、"
                               "平地で抵抗なしの rsssafety はわずかに長い(転がり・空気抵抗が助ける分)。" % P["reaction"])
        figs.save_plot("knob_reaction", [("止まった位置(停止線の手前 +)", [x[0] for x in knob_rho], [x[1] for x in knob_rho]),
                                        ("ρ*", [rho_star, rho_star], [-3.0, 1.0]), ("線", [0.3, 3.2], [0.0, 0.0])],
                       kinds=["scatter", "line", "line"], xlabel="反応時間 [s]", ylabel="停止線の手前 [m]",
                       caption="つまみ = 反応時間: 同じ場所で黄を読んでも、反応が遅いと空走が延び、閉形式のしきい値 ρ* = %.2f s を越えると"
                               "上限のブレーキでも停止線を越える(停止位置不適 / 信号無視)。手前でも 1 段になると制動操作不良。" % rho_star)
        figs.save_plot("knob_grade", [("積分器", [100 * x[0] for x in knob_gr], [x[1] for x in knob_gr]),
                                     ("閉形式", [100 * x[0] for x in knob_gr], [x[2] for x in knob_gr]),
                                     ("逆行小 0.3 m", [6, 14.5], [0.3, 0.3]), ("逆行中 0.5 m", [6, 14.5], [0.5, 0.5]),
                                     ("逆行大 1 m", [6, 14.5], [1.0, 1.0])],
                       kinds=["scatter", "line", "line", "line", "line"], xlabel="勾配 [%]", ylabel="逆行 [m]",
                       caption="つまみ = 勾配: ブレーキを離してからアクセルまで 1.0 s かかる下手な坂道発進のずり下がり。½a₁τ² + (a₁τ)²/(2a₂)"
                               "(点 = 積分器、1e-9)。規格の急な坂(10〜12.5 %)で逆行小〜中、12.5 % 以上で逆行大(試験中止)。"
                               "距離の閾値は二次情報(要確認)。")
        print("  図 %.1f s" % (time.time() - t))
        if figs.errors():
            print("図の書き出しで失敗:", "; ".join(figs.errors()))

    print("== 結果: %d / %d 門, %.1f s" % (sum(OK), len(OK), time.time() - T0))
    print("PASS" if all(OK) else "FAIL")
    return 0 if all(OK) else 1


if __name__ == "__main__":
    sys.exit(main())
