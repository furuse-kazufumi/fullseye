# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実在の日本の町を自前の世界に建てて走る —— 道は OpenStreetMap、建物は PLATEAU、道具立てと規則は日本のもの(2026-10-04)。

著者の発案「出来れば日本のマップでやりたい」。外部の高写実シミュレータの同梱マップは欧米の町(右側通行)で、日本の町を入れるには
エディタのビルドと日本の資産が要る。代わりに **自前の世界に日本を作る**:
  * 道路網 = OpenStreetMap の抜粋(ODbL)。等距円筒で平面に落とし、幅は OSM のタグか道路構造令の車線幅の既定。
  * 道路の形 = 辺を幅つきの線分としてラスタに描いた **和集合** を、Fullseye の輪郭追跡(contours_xld._trace_mask_boundaries、面積は画素数に
    厳密に一致)で境界ループにし、穴 = 街区を歩道と縁石にする(多角形の和集合を解析的に解かず、画像として解く)。
  * 建物 = 国土交通省 Project PLATEAU の CityGML(CC BY 4.0 互換)。LOD1 の足元と高さから押し出し柱(driveplateau)。
  * 道具立て = 一時停止の標識(330-A、一辺 80 cm)、停止線(203、幅 45 cm)、路面文字「止まれ」(交通規制基準 第 46 図例(1): 1 字 240 × 80 cm、
    画 15 cm、字間 1 m、縦表示)、日本式の横断歩道(進行方向に平行な 45 cm の縞)、踏切警標(JIS E 3701 の黄地に黒)、電柱、カーブミラー。
  * 規則 = drivetown の法規パック JP(左側通行、一時停止は止まって確認)。経路は最短路(一方通行を守る)を左の車線中心に寄せ、
    信号・一時停止・踏切を停止線にして town_run(IDM)で通して走る。

門(どれも定理か第 2 実装か公表寸法):
  * 等距円筒: 緯度 0.001° = R π/180 × 0.001 m(1e-9)。driveplateau の第 2 実装と一致(1e-9)。
  * 直線 1 本の和集合の面積 = L w + π (w/2)²(1 %、step 0.25 m)。境界ループの面積(外側 − 穴)= 画素数 × step²(1e-6)。
  * 3 × 3 の格子: 穴 = 4、外側 = 1、辺 = 14、総延長 = 960 m、交差点 = 5。
  * 最短路: 長さ = 160 m(閉形式)、停止線 = 交差点の縁(交差する道の半幅 2.75 m)の 1 m 手前 = 76.25 / 156.25 m(1e-4)、左の車線中心 = 幅/4、
    右側通行の経路は中心線について鏡像、逆向きの一方通行を避けて 320 m を回る。
  * 通し走行: 停止 2 回(信号 → 一時停止)、停止線の 0〜1 m 手前、town_checks ok、第 2 実装(long_simulate)は drivetown の門に委ねる。
  * 道具立て: 一時停止の白い縁の板は一辺 0.8 m・上辺の高さ 2.5 m・高さ 0.8·√3/2、「止まれ」の列は 9.2 m(= 3 × 2.4 + 2 × 1.0)、幅 ≤ 0.8 m。
  * 世界: 面ラベルに 路面 0・縁石 1・信号 3・標識 4・レール 8・印 9・横断歩道 12・歩道 15・電柱 16(建物 14 は PLATEAU か合成)、
    一時停止の手前のコマに標識(ラベル 4)と路面の字(9)が映り、コマは定数でない。
  * 実データ(FULLSEYE_OSM_DATA / FULLSEYE_PLATEAU_DATA があるとき): 銀座 0.7 × 0.6 km の面積の門(1e-4)、街区 > 20、建物 > 100、
    信号のある交差点への経路が引けて通し走行が town_checks ok。

正直に: 等距円筒は 1 km 四方で 1e-5 の歪み。幅は OSM にタグが無い辺(銀座で 6 割)は種別の既定で、実測ではない。車線の割り付け
(turn:lanes)・信号の現示・他車・歩行者は無い。「止まれ」の字形は折線の略字形(寸法は公式、曲線は近似)。踏切警標の板の寸法は
JIS に数値が無いので仮定。街区のうち 4 m² 未満の細片(並走する一方通行の間)は置かず、画素の角で自分に触れる街区は行の束で埋める。
PLATEAU の高さは measuredHeight をそのまま使い、地盤の起伏は無視(全部 z = 0 に置く)。図の出典: 道路 © OpenStreetMap contributors
(ODbL、https://www.openstreetmap.org/copyright)、建物 出典: 国土交通省 Project PLATEAU。データそのものは repo に入れない。
Run: py -3.11 examples/poc_driving_japan_town.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く)
"""
from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import drivejapan as DJ  # noqa: E402
import driveplateau as PL  # noqa: E402
import drivetown as TW  # noqa: E402
import driveworld as DW  # noqa: E402
import examplefig as figs  # noqa: E402

_GATES = []
PITCH = 80.0
CAM_W, CAM_H, CAM_FOV = 640, 400, 60.0
EYE_H = 1.35
N_FRAMES = 14
ATTR = "道路: © OpenStreetMap contributors (ODbL) / 建物: 出典 国土交通省 Project PLATEAU"


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


def node_at(g, i, j, n=3):
    x, y = (i - (n - 1) / 2) * PITCH, (j - (n - 1) / 2) * PITCH
    return min(g["nodes"], key=lambda k: (g["nodes"][k]["xy"][0] - x) ** 2 + (g["nodes"][k]["xy"][1] - y) ** 2)


def to_u8(img):
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)


def frame_at(world, P, c, s, ahead=20.0, w=CAM_W, h=CAM_H):
    k = min(max(int(np.searchsorted(c, s)), 1), len(P) - 2)
    d = P[k + 1] - P[k]
    d = d / max(1e-9, float(np.hypot(*d)))
    K = DW.camera_intrinsics(CAM_FOV, w, h)
    pose = DW.camera_pose((P[k][0], P[k][1], EYE_H), (P[k][0] + ahead * d[0], P[k][1] + ahead * d[1], 1.0))
    # 描画器はカメラの背後に頂点を持つ三角形を落とすので、路面格子のカメラ直下の升が空に抜ける → 自車の足元に小さな路面の板を添える
    x0, y0 = P[k]
    Vg = np.array([[x0 - 4, y0 - 4, 0.001], [x0 + 4, y0 - 4, 0.001], [x0 + 4, y0 + 4, 0.001], [x0 - 4, y0 + 4, 0.001]] +
                  [[x0 + 4 * math.cos(a), y0 + 4 * math.sin(a), 0.001] for a in np.linspace(0, 2 * np.pi, 16, endpoint=False)] + [[x0, y0, 0.001]])
    Fg = np.array([[20, 4 + i, 4 + (i + 1) % 16] for i in range(16)])
    return DW.world_camera(world, pose, K, w, h, ego=(Vg, Fg, np.tile(np.asarray(DW._ROAD_COLOR, np.float64), (len(Fg), 1))))


def topdown(world, w=900, h=700, z=None):
    xmin, xmax, ymin, ymax = world["bounds"]
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    if z is None:
        z = 0.9 * max(xmax - xmin, (ymax - ymin) * w / h) / (2 * math.tan(math.radians(CAM_FOV / 2)))
    K = DW.camera_intrinsics(CAM_FOV, w, h)
    img = DW.world_camera(world, DW.camera_pose((cx, cy + 1e-3, z), (cx, cy, 0.0)), K, w, h)
    return img


def run_route(world, g, r, *, rules=None):
    """経路を走り、信号は発進時に青にして車載のコマを撮る。"""
    run = TW.town_run(r, dt=0.05, v_max=8.0, rules=rules)
    ck = TW.town_checks(run, r)
    return run, ck


def frames_along(world, g, r, run, n=N_FRAMES):
    P, c = r["polyline"], r["cum"]
    S = run["s"]
    picks = np.linspace(0, len(S) - 1, n).astype(int)
    # 停止の瞬間と発進直後のコマを必ず入れる
    for s_stop, kind, t_arr, t_leave in run["stops"]:
        picks = np.append(picks, [int(np.searchsorted(run["t"], t_arr)), min(len(S) - 1, int(np.searchsorted(run["t"], t_leave)) + 10)])
    picks = np.unique(np.clip(picks, 0, len(S) - 1))
    out = []
    greened = set()
    for i in picks:
        # 発進済みの信号を青に
        for s_stop, kind, t_arr, t_leave in run["stops"]:
            if kind == "intersection" and run["t"][i] >= t_leave:
                line = [d for d in r["stop_lines"] if d["kind"] == "intersection" and abs(d["s"] - s_stop) < 1.5]
                for d in line:
                    for sg in world["signals"]:
                        if sg["node"] == d["node"] and sg["edge"] == r["edges"][d["element"] - 1] and sg["object"] not in greened:
                            DW.set_signal_state(world, sg["object"], "green")
                            greened.add(sg["object"])
        img = frame_at(world, P, c, float(S[i]))
        out.append((to_u8(img["color"]), "t = %.1f s, s = %.1f m, v = %.1f m/s (%s)" % (run["t"][i], S[i], run["v"][i], run["mode"][i]), img))
    for o in greened:
        DW.set_signal_state(world, o, "red")
    return out


def main() -> int:
    t_all = time.time()
    print("== 1. 座標と道路網(合成の 3 × 3 格子)")
    x, y = DJ.latlon_to_local(35.001, 139.0, (35.0, 139.0))
    gate("緯度 0.001° = R π/180 × 0.001 m", abs(float(y) - DJ.R_EARTH_M * math.pi / 180 * 0.001) < 1e-9 and abs(float(x)) < 1e-12, "y = %.4f m" % float(y))
    x2, y2 = PL.latlon_to_local(35.670, 139.765, (35.6715, 139.766))
    x1, y1 = DJ.latlon_to_local(35.670, 139.765, (35.6715, 139.766))
    gate("第 2 実装(driveplateau)と一致", abs(float(x1) - float(x2)) < 1e-9 and abs(float(y1) - float(y2)) < 1e-9)
    osm = DJ.osm_parse(DJ.osm_synthetic("grid", n=3, pitch=PITCH))
    g = DJ.osm_road_graph(osm)
    st = DJ.japan_stats(g)
    gate("格子: 辺 14・総延長 960 m・交差点 5", g["n_edges"] == 14 and abs(g["total_length"] - 960) < 1e-4 and st["junctions"] == 5,
         "edges %d, %.3f m" % (g["n_edges"], g["total_length"]))
    osm1 = DJ.osm_parse(DJ.osm_synthetic("line", n=2, pitch=100.0))
    g1 = DJ.osm_road_graph(osm1)
    e1 = g1["edges"][0]
    rm1 = DJ.osm_road_mask(g1, step=0.25)
    exact = e1["length"] * e1["width"] + math.pi * (e1["width"] / 2) ** 2
    gate("直線路の和集合の面積 = L w + π (w/2)²(1 %)", abs(rm1["area_m2"] - exact) / exact < 0.01, "%.2f vs %.2f m²" % (rm1["area_m2"], exact))
    rm = DJ.osm_road_mask(g, step=0.5)
    lp = DJ.osm_road_loops(rm)
    gate("境界ループの面積 = 画素数 × step²(1e-6)", lp["area_check"]["abs_err"] < 1e-6, "%.3e m²" % lp["area_check"]["abs_err"])
    gate("格子の穴 = 4・外側 = 1", len(lp["holes"]) == 4 and len(lp["outer"]) == 1)

    print("== 2. 経路と停止線")
    src, dst = node_at(g, 0, 1), node_at(g, 2, 1)
    r = DJ.osm_route(g, src, dst)
    r_x = 5.5 / 2
    gate("最短路 160 m(1e-4)", abs(r["length"] - 160) < 1e-4 and abs(r["graph_length"] - 160) < 1e-4, "%.5f m" % r["length"])
    gate("停止線 = 交差する道の半幅 + 1 m 手前(76.25 / 156.25)",
         [d["kind"] for d in r["stop_lines"]] == ["intersection", "stop_sign"] and abs(r["stop_lines"][0]["s"] - (PITCH - r_x - 1)) < 1e-4
         and abs(r["stop_lines"][1]["s"] - (2 * PITCH - r_x - 1)) < 1e-4, "%s" % [round(d["s"], 3) for d in r["stop_lines"]])
    gate("左の車線中心 = 幅/4", abs(r["polyline"][0, 1] - 6.5 / 4) < 1e-9)
    rr = DJ.osm_route(g, src, dst, side="right")
    gate("右側通行の経路は中心線の鏡像", np.allclose((r["polyline"] + rr["polyline"])[:, 1] / 2, 0.0, atol=1e-9))
    xml = DJ.osm_synthetic("grid", n=3, pitch=PITCH).replace('<tag k="name" v="EW 1"/>', '<tag k="name" v="EW 1"/>\n    <tag k="oneway" v="-1"/>')
    g_ow = DJ.osm_road_graph(DJ.osm_parse(xml))
    r_ow = DJ.osm_route(g_ow, node_at(g_ow, 0, 1), node_at(g_ow, 2, 1))
    gate("逆向きの一方通行を避けて 320 m", abs(r_ow["graph_length"] - 320) < 1e-4, "%.3f m" % r_ow["graph_length"])

    print("== 3. 通し走行(JP)")
    world = DJ.japan_world(g)
    run, ck = run_route(world, g, r)
    gate("停止 2 回: 信号 → 一時停止", len(run["stops"]) == 2 and [s[1] for s in run["stops"]] == ["intersection", "stop_sign"])
    ok_pos = all(0.0 <= [d for d in r["stop_lines"] if d["kind"] == k][0]["s"] - s <= 1.0 for s, k, _, _ in run["stops"])
    gate("停止は停止線の 0〜1 m 手前", ok_pos, "%s" % [(round(s, 3), k) for s, k, _, _ in run["stops"]])
    gate("town_checks ok(運動学・制動距離・回数)", ck["ok"] and ck["count_ok"])
    stt = world["stats"]
    gate("世界: 街区 4・信号 4・一時停止 3(T 字路の 3 進入)・踏切 1・横断歩道 1",
         stt["blocks"] == 4 and stt["signals"] == 4 and stt["stop_signs"] == 3 and stt["crossings"] == 1 and stt["crosswalks"] == 1, str(stt))
    labels = set(np.unique(world["face_label"]).tolist())
    gate("面ラベル 0,1,3,4,8,9,12,15,16 がある", {0, 1, 3, 4, 8, 9, 12, 15, 16} <= labels, str(sorted(labels)))

    print("== 4. 道具立ての寸法")
    V, F, C = DJ.jp_sign_stop_mesh()
    plate = V[np.unique(F[np.all(np.isclose(C, DJ._C_WHITE), axis=1)])]
    gate("一時停止: 一辺 0.8 m・上辺 2.5 m・高さ 0.8·√3/2",
         abs(np.ptp(plate[:, 1]) - 0.8) < 1e-9 and abs(plate[:, 2].max() - 2.5) < 1e-9 and abs(np.ptp(plate[:, 2]) - 0.8 * math.sqrt(3) / 2) < 1e-9)
    Vm, Fm, Cm = DJ.jp_stop_marking_mesh()
    gate("「止まれ」の列 = 9.2 m、幅 ≤ 0.8 m", abs(np.ptp(Vm[:, 0]) - 9.2) < 1e-9 and np.ptp(Vm[:, 1]) <= 0.8 + 1e-9, "%.3f × %.3f m" % (np.ptp(Vm[:, 0]), np.ptp(Vm[:, 1])))
    img = frame_at(world, r["polyline"], r["cum"], r["stop_lines"][1]["s"] - 14.0)
    lab = img["label"]
    gate("一時停止の手前のコマに標識(4)と路面の字(9)、定数でない", (lab == 4).sum() > 10 and (lab == 9).sum() > 50 and np.ptp(img["color"]) > 0.3,
         "sign %d px, marks %d px" % ((lab == 4).sum(), (lab == 9).sum()))

    print("== 5. 建物(合成 CityGML)")
    cg = PL.plateau_parse(PL.citygml_synthetic(n=3, origin=osm["origin"], spacing=30.0, size=10.0, heights=[10.0, 20.0, 30.0]), origin=osm["origin"])
    wb = DJ.japan_world(g, buildings=cg["buildings"])
    Vb = wb["V"][wb["F"][wb["face_label"] == 14].ravel()]
    gate("合成の建物 3 棟が柱になり最高 30 m", wb["stats"]["buildings"] == 3 and abs(Vb[:, 2].max() - 30.0) < 1e-9)

    # ── 実データ(あれば)
    real = None
    osm_dir, pl_dir = os.environ.get("FULLSEYE_OSM_DATA", ""), os.environ.get("FULLSEYE_PLATEAU_DATA", "")
    if osm_dir and (Path(osm_dir) / "ginza.osm").is_file():
        print("== 6. 実データ: 銀座(OSM%s)" % (" + PLATEAU" if pl_dir else ""))
        t0 = time.time()
        osm_r = DJ.osm_parse(Path(osm_dir) / "ginza.osm")
        bx, by = DJ.latlon_to_local(np.array([35.6690, 35.6740]), np.array([139.7620, 139.7700]), osm_r["origin"])
        bbox = (float(bx[0]), float(bx[1]), float(by[0]), float(by[1]))
        g_r = DJ.osm_road_graph(osm_r, bbox=bbox)
        st_r = DJ.japan_stats(g_r)
        B = []
        if pl_dir:
            for p in sorted(Path(pl_dir).glob("*_bldg_*.gml")):
                B += PL.plateau_parse(p, origin=osm_r["origin"])["buildings"]
        w_r = DJ.japan_world(g_r, buildings=B)
        lp_r = w_r["loops"]
        gate("銀座: 境界ループの面積 = 画素数 × step²(1e-4)", lp_r["area_check"]["abs_err"] < 1e-4, "%.2e m²" % lp_r["area_check"]["abs_err"])
        gate("銀座: 街区 > 20・辺 > 100", len(lp_r["holes"]) > 20 and g_r["n_edges"] > 100, "holes %d, edges %d" % (len(lp_r["holes"]), g_r["n_edges"]))
        if pl_dir:
            gate("銀座: 建物 > 100 棟", w_r["stats"]["buildings"] > 100, "%d" % w_r["stats"]["buildings"])
        sig = [i for i, n in g_r["nodes"].items() if "traffic_signals" in n["features"] and n["degree"] >= 3]
        best = None
        for i in list(g_r["nodes"])[::5]:
            try:
                rr_ = DJ.osm_route(g_r, i, sig[0])
            except ValueError:
                continue
            if 300 < rr_["length"] < 700 and (best is None or len(rr_["stop_lines"]) > len(best["stop_lines"])):
                best = rr_
        r_r = best
        run_r, ck_r = run_route(w_r, g_r, r_r)
        gate("銀座: 信号のある交差点への経路を通して走り town_checks ok", ck_r["ok"] and len(run_r["stops"]) >= 1,
             "%.0f m, %d stops, %.1f s" % (r_r["length"], len(run_r["stops"]), run_r["t"][-1]))
        print("  (%.1f s)" % (time.time() - t0))
        real = {"osm": osm_r, "graph": g_r, "world": w_r, "route": r_r, "run": run_r, "stats": st_r, "buildings": len(B)}

    if figs.enabled():
        print("== 図")
        src_world = real["world"] if real else world
        img = topdown(src_world, 900, 700)
        figs.save("japan_town_topdown", to_u8(img["color"]),
                  caption=("銀座 0.7 × 0.6 km の俯瞰: OSM の道路網を幅つきでラスタ化した和集合の穴 = 街区(歩道 + 縁石)、信号・横断歩道・電柱。" if real else
                           "合成 3 × 3 格子の俯瞰(信号・一時停止・踏切・横断歩道)。") + " " + ATTR)
        if real:
            xmin, xmax, ymin, ymax = src_world["bounds"]
            cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
            K = DW.camera_intrinsics(CAM_FOV, 1280, 800)
            bird = DW.world_camera(src_world, DW.camera_pose((cx - 300, cy - 500, 350.0), (cx, cy, 0.0)), K, 1280, 800)
            figs.save("japan_town_bird", to_u8(bird["color"]),
                      caption="PLATEAU(国交省 3D 都市モデル、LOD1 の足元と高さ)の建物 %d 棟を押し出し柱で立てた銀座。%s" % (src_world["stats"]["buildings"], ATTR))
        rt, rn = (real["route"], real["run"]) if real else (r, run)
        fr = frames_along(src_world, real["graph"] if real else g, rt, rn)
        figs.save_gif("japan_town_drive", [f[0] for f in fr], fps=2.0,
                      caption="左の車線中心を通して走る車載カメラ(JP 法規パック): 赤で停止 → 2 秒で青 → 発進、一時停止では止まって確認。" + ATTR)
        figs.save_grid("japan_town_frames", [f[0] for f in fr[:8]], captions=[f[1] for f in fr[:8]], ncols=4,
                       caption="同じ走行のコマ(時刻・弧長・速度・状態)。" + ATTR)
        # 道具立ての見本: 合成格子の一時停止の手前
        img_s = frame_at(world, r["polyline"], r["cum"], r["stop_lines"][1]["s"] - 12.0, ahead=14.0)
        lab_s = img_s["label"]
        pal = np.array([[0.4, 0.41, 0.43], [0.78, 0.78, 0.74], [0.2, 0.4, 0.9], [0.9, 0.5, 0.1], [0.9, 0.1, 0.1], [1, 0.6, 0], [0.5, 0.3, 0.7],
                        [1, 0.8, 0.8], [0.35, 0.33, 0.3], [0.95, 0.95, 0.9], [0.3, 0.6, 0.2], [0.2, 0.5, 0.8], [1, 1, 1], [0.1, 0.6, 0.1],
                        [0.6, 0.6, 0.65], [0.62, 0.6, 0.56], [0.66, 0.65, 0.62]])
        seg = np.zeros(lab_s.shape + (3,))
        m = lab_s >= 0
        seg[m] = pal[np.clip(lab_s[m], 0, len(pal) - 1)]
        seg[~m] = (0.62, 0.75, 0.92)
        figs.save_grid("japan_furniture", [to_u8(img_s["color"]), to_u8(seg)], captions=["一時停止の手前: 標識 330-A・停止線・「止まれ」(縦表示 9.2 m)", "面ラベル(標識 4・印 9・歩道 15・電柱 16)"],
                       ncols=2, caption="日本の道具立て(寸法は道路標識令 別表第二 / 交通規制基準 第 46 図例(1))。字形は略字形。")
        stt_src = real["stats"] if real else st
        rows = [[rw["highway"], rw["edges"], rw["length_m"], rw["mean_width_m"]] for rw in stt_src["table"]]
        figs.save_table("japan_road_table", ["種別 (OSM highway)", "辺", "延長 [m]", "平均幅 [m]"], rows,
                        title="道路網の内訳" + ("(銀座)" if real else "(合成格子)"),
                        caption="幅の由来: %s(width タグ / lanes × 車線幅 / 種別の既定)。節点の特徴: %s。%s" % (stt_src["width_from"], stt_src["features"], ATTR))
        figs.save_plot("japan_speed", [("v [m/s]", rn["s"], rn["v"])], xlabel="s [m]", ylabel="v [m/s]",
                       title="通し走行の速度(停止線で 0)", caption="停止線: %s" % [(round(d["s"], 1), d["kind"]) for d in rt["stop_lines"]])
        print("  figures:", figs.errors() if hasattr(figs, "errors") else "")

    n_ng = sum(1 for _, ok in _GATES if not ok)
    print("gates: %d / %d ok  (%.1f s)" % (len(_GATES) - n_ng, len(_GATES), time.time() - t_all))
    if n_ng:
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
