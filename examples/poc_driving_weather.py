# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC ㉓(自動運転 第 6 回): 太陽と天気 —— 朝日の逆光で信号が読めない時間帯、霧の中で「見えてから止まれる速さ」、雨の路面、夜の前照灯。

これまでの車載カメラは光の向きが固定で、明るさは面の色 × 陰影だけだった。ここでは世界を物理の単位(輝度 cd/m²・照度 lx)で照らし直す
(driveenv): 日時と緯度経度から太陽の高度・方位(NOAA の式)、影(太陽から見た深度画像)、空の明るさ、逆光の光幕(Stiles–Holladay)、
霧(Koschmieder)、濡れた路面に映る灯火、夜の前照灯の照度。車載カメラの画像処理(色度で灯火を読む)がどこで読めなくなるかを、
画素の式から **先に閉形式で出し**、描いた画像の読みがその両側で変わることを確かめる。そして第 5 回の停止距離と組み合わせて、
「見えてから止まれるか」を閉ループで走らせる。

門(真値の出どころ):
  1. **太陽の位置 = 国立天文台 暦計算室の公表値**: 東京(35.6581°N, 139.7414°E)の 2026 年 春分・夏至・秋分・冬至の日の出・南中・日の入りの
     時刻(分)・方位・南中高度(0.1°)。暦計算室の定義(上辺が視地平線・地平大気差 35′8″)で解く。
  2. **影の長さ = 高さ × cot(高度)**: 真上から撮った画像の暗い画素(影)の先端を、4 つの高度で測る。
  3. **逆光**: 灯火の色度が検出の許容(color_tol = 0.25)を割る白の量 W*(veil_chroma_limit)と光幕 10 E/θ² から閾値 θ* を出し、
     描いた画像の読みが θ* の両側で変わる(3 色 × 角度の掃引)。春分の朝、東へ向かう車から信号が読めない時間帯を太陽の式から出し、描いて確かめる。
  4. **霧の濃さを画像から測る**: 路面の縦の輝度の曲線に Koschmieder を当てて β を戻す(視程 30〜200 m)。変曲点の閉形式 β = 2/d_i も並べる。
  5. **霧の中で色が読める距離** d* = ln(1 + W*/L_h)/β(L_h = 画像の空から測った大気光)と、描いた画像で読めた距離。
  6. **見えてから止まれるか**: 読めた距離の中で止まれる速さ v*(sight_stop_speed、停止距離の閉形式を v について解く)の下では停止線の手前に
     止まり、上では越える(閉ループ、カメラの読みで制動を始める)。
  7. **雨**: 国土交通省(道路構造令の解説)の停止距離の式 D = 0.694V + 0.00394V²/f(反応 2.5 s)と第 5 回の閉形式が一致(第 2 実装)。
     湿潤の f で止まるまでの距離が延びる(積分器と閉形式)。路面に映った灯火は地図の ROI の外なので読みを乱さない。
  8. **夜**: 仮定した配光で、すれ違い灯 40 m・走行灯 100 m の障害物(歩行者)を画像で見つけられる(道路運送車両の保安基準 細目告示 第 120 条の
     性能)。見つけた距離から止まれる速さ、その上下で歩行者の手前に止まる / 止まれない(閉ループ)。
  9. **ゼロ点**: 灯火を消すと、どの天気でも 'unknown'(fail-closed)。

正直に書くこと: 空の明るさ・薄明の照度・灯火の輝度・前照灯の配光・HDR カメラの階調は **仮定**(driveenv の docstring)。光幕の式は人の目の散乱の
経験式でカメラのレンズの散乱を代用している。影は太陽のシャドウマップ(解像度で縁が決まる)、前照灯の影は無い。雨筋と路面の鏡像のぼけは見た目だけ。
霧の測定は描画と同じ Koschmieder の世界の上で行うので、実際の霧(一様でない・光源の散乱の光輪)への頑健さは測っていない。

教則の場面: S131, S132, S136, S138(docs/drive/kyosoku_scenarios.json、交通の方法に関する教則の再現台帳)

Run: py -3.11 examples/poc_driving_weather.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く。
FULLSEYE_POC_BUDGET=reduced(CI の既定)で角度・距離の掃引とカメラの周期を粗くし、GIF のコマを減らす)
"""
from __future__ import annotations

import math
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import drivecourse as DC  # noqa: E402
import driveworld as DW  # noqa: E402
import driveterrain as DT  # noqa: E402
import drivelong as DL  # noqa: E402
import driveenv as EV  # noqa: E402
import balltrack as BT  # noqa: E402
import annotate as AN  # noqa: E402

#: 予算: reduced(CI の既定)は掃引を粗く・カメラの周期 0.2 s・GIF は 30 分おき、full は細かく・0.1 s・15 分おき。展示の数字は full の実測。
REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
TICK = 0.2 if REDUCED else 0.1
T0 = time.time()
OK = []
JST = timezone(timedelta(hours=9))
TOKYO = (35.6581, 139.7414)                 # 国立天文台 暦計算室の東京の代表点(標高 0 m)
FRONT = 2.25
LANE_Y = 1.75
CAM_W, CAM_H = 640, 400
K = DW.camera_intrinsics(60.0, CAM_W, CAM_H)
FOCAL = float(K[0, 0])
CAM_Z = 1.35
#: 色度の検出の許容(赤と黄の単位ベクトルの距離 0.54 の半分より小さい = 色を取り違えない。第 5 回は 0.15)
TOL = 0.25
#: 霧の日の明るさ: 朝の霧(太陽の高度 15°、曇天)
FOG_SUN = (15.0, 120.0)

#: 国立天文台 暦計算室「日の出入り」2026 年 東京(https://eco.mtk.nao.ac.jp/koyomi/dni/2026/s1303.html ほか s1306・s1309・s1312)。
#: (月, 日, 日の出, 方位, 南中, 高度, 日の入り, 方位)。時刻は分に、角度は 0.1° に丸めてある。方位は北から東回り。
NAOJ = [(3, 20, "5:45", 89.8, "11:49", 54.2, "17:52", 270.5),
        (6, 21, "4:25", 60.0, "11:43", 77.8, "19:00", 300.0),
        (9, 23, "5:29", 89.3, "11:34", 54.3, "17:37", 270.4),
        (12, 22, "6:47", 118.6, "11:39", 30.9, "16:32", 241.4)]
#: 国土交通省「道路構造令について(3)」の湿潤路面の縦すべり摩擦係数(設計速度 → 走行速度 V [km/h], f)。
MLIT_F = [(120, 102, 0.29), (100, 85, 0.30), (80, 68, 0.31), (60, 54, 0.33), (50, 45, 0.35), (40, 36, 0.38), (30, 30, 0.44), (20, 20, 0.44)]


def gate(name, cond, detail=""):
    OK.append(bool(cond))
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


def hm(dt):
    return dt.hour * 60 + dt.minute + dt.second / 60.0


def main() -> int:
    """PoC の本体。"""
    print("BUDGET: %s(FULLSEYE_POC_BUDGET、CI では reduced が既定)" % ("reduced" if REDUCED else "full"))
    P = DL.long_params()

    # ─────────────────────────── 1. 太陽の位置 = 暦計算室 ───────────────────────────
    print("== 1. 太陽の位置と国立天文台 暦計算室(東京、2026 年)")
    t = time.time()
    dmin, dang, match, rows_sun = [], [], 0, []
    for (m, d, rise, az_r, tr, alt, sett, az_s) in NAOJ:
        ev = EV.sun_events(2026, m, d, *TOKYO, 9.0, h0="naoj")
        for ours, ref in ((ev["sunrise"], rise), (ev["transit"], tr), (ev["sunset"], sett)):
            hh, mm = (int(x) for x in ref.split(":"))
            o = hm(ours)
            dmin.append(abs(o - (hh * 60 + mm)))
            match += int(math.floor(o + 0.5) == hh * 60 + mm)
        for ours, ref in ((ev["sunrise_azimuth"], az_r), (ev["transit_altitude_apparent"], alt), (ev["sunset_azimuth"], az_s)):
            dang.append(abs(ours - ref))
            match += int(math.floor(ours * 10 + 0.5) == round(ref * 10))
        rows_sun.append((m, d, ev))
        print("  %2d/%2d  日の出 %s(暦 %s)方位 %.2f°(%.1f)  南中 %s(%s)高度 %.2f°(%.1f)  日の入り %s(%s)方位 %.2f°(%.1f)" % (
            m, d, ev["sunrise"].strftime("%H:%M:%S"), rise, ev["sunrise_azimuth"], az_r, ev["transit"].strftime("%H:%M:%S"), tr,
            ev["transit_altitude_apparent"], alt, ev["sunset"].strftime("%H:%M:%S"), sett, ev["sunset_azimuth"], az_s))
    gate("太陽の位置: 暦計算室の東京 4 日 × (時刻 3 + 角度 3) = 24 値が丸めで一致、時刻は 1 分以内・角度は 0.1° 以内",
         match == 24 and max(dmin) <= 1.0 and max(dang) <= 0.1,
         "丸めの一致 %d / 24、時刻の差 最大 %.2f 分(丸めの前)、角度の差 最大 %.3f°(%.1f s)" % (match, max(dmin), max(dang), time.time() - t))

    # ─────────────────────────── 2. 影の長さ ───────────────────────────
    print("== 2. 影の長さ = 高さ × cot(高度)(真上から撮った画像の暗い画素の先端)")
    t = time.time()
    WS = DW._empty_world()
    Vg, Fg = DW._grid_plane(-40, 40, -40, 40, step=4.0)
    DW.world_add(WS, Vg, Fg, 0, DW._ROAD_COLOR, name="ground")
    hp, wp = 4.0, 0.3
    bx = np.array([[x, y, z] for z in (0.0, hp) for y in (-wp / 2, wp / 2) for x in (-wp / 2, wp / 2)])
    bf = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4],
                   [1, 5, 7], [1, 7, 3]])
    DW.world_add(WS, bx, bf, 6, (0.8, 0.8, 0.8), name="pole")
    Ktop = DW.camera_intrinsics(50.0, 640, 640)
    Ptop = DW.camera_pose((0.0, 0.0, 70.0), (0.0, 0.0, 0.0), up=(0.0, 1.0, 0.0))
    sh_rows, sh_err = [], []
    for el in (15.0, 25.0, 40.0, 60.0):
        az = 135.0                                                  # 南東の空 → 影は北西へ
        env = EV.env_params(sun=(el, az))
        out = EV.env_render(WS, Ptop, Ktop, 640, 640, env, shadow_res=2048)
        img = out["color"] @ np.array([0.2126, 0.7152, 0.0722])
        ground = img[out["label"] == 0]
        lit, dark = np.median(ground), float(ground.min())               # 影は地面の 1 % 未満なので分位でなく最小値
        mask = img < 0.5 * (lit + dark)                             # 影 = 地面の明るさの中間より暗い(画像だけで決める)
        rr, cc = np.nonzero(mask)
        # 真上のカメラ: 画素 → 地面 (x, y)(高さ 70 m、z = 0 の平面)
        gx = (cc - Ktop[0, 2]) / Ktop[0, 0] * 70.0
        gy = (Ktop[1, 2] - rr) / Ktop[1, 1] * 70.0
        s = EV.sun_vector(el, az)
        u = -s[:2] / np.linalg.norm(s[:2])                          # 影の向き(太陽の反対)
        tip = float(np.max(gx * u[0] + gy * u[1]))
        truth = hp / math.tan(math.radians(el)) + (wp / 2) * (abs(u[0]) + abs(u[1]))
        sh_rows.append((el, truth, tip))
        sh_err.append(abs(tip - truth))
    px = 70.0 / Ktop[0, 0]
    print("  " + "; ".join("高度 %.0f°: 閉形式 %.2f m / 画像 %.2f m" % r for r in sh_rows))
    gate("影の先端: 4 つの高度で 閉形式 h cot(高度) + 柱の角 と画像の差 < 2 画素(%.2f m)" % (2 * px), max(sh_err) < 2 * px,
         "最大 %.3f m(1 画素 %.3f m、%.1f s)" % (max(sh_err), px, time.time() - t))

    # ─────────────────────────── 3. 世界(交差点)と信号の読み ───────────────────────────
    print("== 3. 逆光: 太陽と視線の角 θ が閾値 θ* を割ると、灯火の色度が灰色へ寄って読めない")
    I = DC.course_intersection()
    LAY = DC.course_layout([I, DC.course_road(55.0, 7.0), DC.course_road(10.0, 7.0)], [(0, 0, 0), (-23.45, 0, math.pi), (23.45, 0, 0)])
    WORLD = DW.world_build(LAY, props=[("sedan", 5.0, -1.75, math.pi, None, "white"), ("cone", 30.0, 3.3, 0.0)])
    stop_objs = [o for o in WORLD["objects"] if o["name"] == "stop_line"]
    near = []
    for o in stop_objs:
        f0, f1 = o["faces"]
        Vv = WORLD["V"][WORLD["F"][f0:f1]].reshape(-1, 3)
        if Vv[:, 0].max() < 0 and Vv[:, 1].min() > -0.1 and Vv[:, 1].max() < 3.6 and np.ptp(Vv[:, 0]) < 1.0:
            near.append(float(Vv[:, 0].min()))
    X_LINE = min(near) if near else float(I["stop_lines"][0][0][0]) - 0.45
    SIG = [i for i, o in enumerate(WORLD["objects"]) if o["name"] == "traffic_light"
           and abs(o["pose"][0] - I["signal_poses"][0][0]) < 0.1 and abs(o["pose"][1] - I["signal_poses"][0][1]) < 0.1][0]
    LAMP_C = {kind: WORLD["V"][WORLD["F"][f0:f1]].reshape(-1, 3).mean(axis=0)
              for kind, (f0, f1) in WORLD["objects"][SIG]["lamp_faces"].items()}
    LAMPS = np.array(list(LAMP_C.values()))
    COLORS = {c: np.array(DW._LAMP[c]) for c in ("red", "yellow", "green")}
    for i_, o in enumerate(WORLD["objects"]):                       # 他の信号機は消す(対面の 1 基だけを読む)
        if o["name"] == "traffic_light" and i_ != SIG:
            DW.set_signal_state(WORLD, i_, "off")

    def cam_at(x):
        return DW.camera_pose((x + 0.5, LANE_Y, CAM_Z), (x + 20.0, LANE_Y, 0.9))

    def cam_x_for_gap(gap):
        """前端が停止線の gap m 手前にいる車のカメラの x(車の中心 = 線 − gap − FRONT)。"""
        return X_LINE - gap - FRONT

    def read_signal(img, Pc, roi=24):
        """地図の灯火の位置を投影した ROI で、色度の検出 op(balltrack.ball_detect、chroma、color_tol = TOL)が見つけた色。
        1 色だけ → その色、それ以外 → 'unknown'(fail-closed)。真値(面 ID)は使わない。"""
        col, row, dep = DW.world_project_points(LAMPS, Pc, K)
        if not np.all(dep > 0):
            return "unknown"
        c0, c1 = max(0, int(col.min()) - roi), min(img.shape[1], int(col.max()) + roi + 1)
        r0, r1 = max(0, int(row.min()) - roi), min(img.shape[0], int(row.max()) + roi + 1)
        if c1 - c0 < 4 or r1 - r0 < 4:
            return "unknown"
        crop = img[r0:r1, c0:c1]
        lit = [name for name, colr in COLORS.items()
               if BT.ball_detect(crop, mode="chroma", color=tuple(float(v) for v in colr), color_tol=TOL, radius_range=(1.0, 14.0))]
        return lit[0] if len(lit) == 1 else "unknown"

    L_LAMP = 10000.0
    WSTAR = {c: EV.veil_chroma_limit(COLORS[c], L_LAMP, TOL) for c in COLORS}
    print("  色度が許容 %.2f を割る白の量 W*: " % TOL + ", ".join("%s %.0f cd/m²" % (c, w) for c, w in WSTAR.items()))
    GAP_READ = 15.0                                                 # 停止線の 15 m 手前から読む
    xr = cam_x_for_gap(GAP_READ)
    Pr = cam_at(xr)
    eye_r = np.array([xr + 0.5, LANE_Y, CAM_Z])

    def sun_at_angle(kind, theta):
        """灯火への視線 ℓ を上へ θ 回した向きに太陽を置く → (高度, 方位)。"""
        ell = LAMP_C[kind] - eye_r
        ell /= np.linalg.norm(ell)
        up = np.array([0.0, 0.0, 1.0]) - ell[2] * ell
        up /= np.linalg.norm(up)
        s = math.cos(math.radians(theta)) * ell + math.sin(math.radians(theta)) * up
        return math.degrees(math.asin(s[2])), math.degrees(math.atan2(s[0], s[1])) % 360.0

    def theta_star(kind, el):
        E_dn = EV.sun_illuminance(el)["direct_normal"]
        return math.sqrt(10.0 * E_dn / WSTAR[kind])

    t = time.time()
    back_rows, mism, nearb = [], 0, 0
    thetas = np.arange(4.0, 30.01, 2.0 if REDUCED else 1.0)
    for kind in ("red", "yellow", "green"):
        DW.set_signal_state(WORLD, SIG, kind)
        for th in thetas:
            el, az = sun_at_angle(kind, th)
            ts = theta_star(kind, el)
            img = EV.env_render(WORLD, Pr, K, CAM_W, CAM_H, EV.env_params(sun=(el, az)), shadows=False)["color"]
            rd = read_signal(img, Pr)
            pred = th > ts
            ok = (rd == kind) == pred
            if abs(th - ts) / ts < 0.06:
                nearb += 1                                          # 閾値の ±6 % は灯火の画素の間で θ が変わる帯(判定に入れない)
            elif not ok:
                mism += 1
            back_rows.append((kind, th, el, ts, rd))
    ts_rows = {k: [r for r in back_rows if r[0] == k] for k in COLORS}
    for k, rr_ in ts_rows.items():
        first_ok = min([r[1] for r in rr_ if r[4] == k], default=float("nan"))
        print("  %-6s θ* = %.1f〜%.1f°(高度で変わる)、読めた最小の θ = %.0f°" % (k, min(r[3] for r in rr_), max(r[3] for r in rr_), first_ok))
    gate("逆光: 3 色 × θ %d 点で、読めた / 読めない が閾値 θ* = √(10 E_dn / W*) の予測と一致(閾値の ±6 %% の帯を除く)" % len(thetas),
         mism == 0 and len(back_rows) - nearb >= 3 * len(thetas) - 6,
         "食い違い %d、帯の中 %d(%.1f s)" % (mism, nearb, time.time() - t))

    # 春分の朝、東へ向かう車から: 太陽と赤の灯火への視線の角 θ(t) が θ*(高度) を割る時間帯
    t = time.time()
    DW.set_signal_state(WORLD, SIG, "red")
    ell_r = LAMP_C["red"] - eye_r
    ell_r /= np.linalg.norm(ell_r)
    win, series = [], []
    t_day = datetime(2026, 3, 20, 5, 30, tzinfo=JST)
    for k_ in range(0, 4 * 60 + 1):
        tt = t_day + timedelta(minutes=k_)
        sp = EV.sun_at(tt, *TOKYO)
        if sp["elevation"] <= 0:
            series.append((hm(tt), sp["elevation"], float("nan"), float("nan")))
            continue
        s = EV.sun_vector(sp["elevation"], sp["azimuth"])
        th = math.degrees(math.acos(float(np.clip(s @ ell_r, -1, 1))))
        ts = theta_star("red", sp["elevation"])
        series.append((hm(tt), sp["elevation"], th, ts))
        if th < ts:
            win.append(tt)
    if win:
        w0, w1 = win[0], win[-1]
        print("  春分(3/20)の朝、停止線の 15 m 手前から赤の灯火を見ると、太陽が θ* の内側にあるのは %s〜%s(%d 分)" % (
            w0.strftime("%H:%M"), w1.strftime("%H:%M"), len(win)))
    checks = []
    samples = [t_day + timedelta(minutes=m_) for m_ in range(30, 4 * 60 + 1, 30 if REDUCED else 15)]
    for tt in samples:
        sp = EV.sun_at(tt, *TOKYO)
        img = EV.env_render(WORLD, Pr, K, CAM_W, CAM_H, EV.env_params(tt, *TOKYO), shadows=False)["color"]
        rd = read_signal(img, Pr)
        inside = bool(win) and (win[0] <= tt <= win[-1])
        checks.append((tt, sp["elevation"], rd, inside))
    bad = [c for c in checks if (c[2] == "red") == c[3]]
    gate("春分の朝: 太陽の式が出した「読めない時間帯」の内側では 'unknown'、外側では赤と読む(%d 時刻)" % len(checks),
         bool(win) and not bad and any(c[3] for c in checks),
         "時間帯 %s、%s(%.1f s)" % ("%s〜%s" % (win[0].strftime("%H:%M"), win[-1].strftime("%H:%M")) if win else "なし",
                                   ", ".join("%s %s" % (c[0].strftime("%H:%M"), {"red": "赤", "unknown": "?"}.get(c[2], c[2])) for c in checks),
                                   time.time() - t))

    # ─────────────────────────── 4. 霧 ───────────────────────────
    print("== 4. 霧: 路面の輝度の曲線から β を測り、色が読める距離を閉形式で出す")
    t = time.time()
    WR = DW.world_build(DC.course_layout([DC.course_road(220.0, 7.0)], [(0.0, 0.0, 0.0)]))
    x_cam = 5.0                                                     # course_road は x = 0 から道なりに伸びる
    Pf = cam_at(x_cam)
    pitch = math.atan(0.45 / 19.5)
    v_h = float(K[1, 2] - FOCAL * math.tan(pitch))
    lane_pts = np.array([[x_cam + 0.5 + d, LANE_Y + 0.9, 0.0] for d in np.geomspace(3.0, 200.0, 400)])  # 車線の中の白線でない所
    colp, rowp, _ = DW.world_project_points(lane_pts, Pf, K)
    rng = np.random.default_rng(7)
    fog_rows = []
    for mor in (30.0, 50.0, 100.0, 200.0):
        env = EV.env_params(sun=(30.0, 180.0), cloud=1.0, fog_mor=mor)
        out = EV.env_render(WR, Pf, K, CAM_W, CAM_H, env, shadows=False)
        lum = out["radiance"] @ np.array([0.2126, 0.7152, 0.0722])
        lum = lum * (1.0 + 0.01 * rng.standard_normal(lum.shape))       # センサの雑音 1 %
        rows_ = np.arange(int(math.ceil(v_h + 3)), CAM_H)
        cols_ = np.interp(rows_, rowp[::-1], colp[::-1])
        prof = np.array([np.median(lum[r, max(0, int(c) - 3):int(c) + 4]) for r, c in zip(rows_, cols_)])
        fit = EV.fog_beta_from_profile(rows_, prof, v_h, FOCAL, CAM_Z, pitch)
        b_true = EV.beta_from_mor(mor)
        fog_rows.append((mor, b_true, fit["beta_fit"], fit["beta_inflection"], fit["mor"], rows_, prof, fit))
    for mor, bt, bf, bi, mo, *_ in fog_rows:
        print("  視程 %3.0f m: β 真 %.5f / 当てはめ %.5f(視程 %.1f m)/ 変曲点 %.5f" % (mor, bt, bf, mo, bi))
    e_fit = max(abs(r[2] - r[1]) / r[1] for r in fog_rows)
    gate("霧の濃さを画像から: 路面の縦の輝度(雑音 1 %)に Koschmieder を当てた β が真の値と 2 % 以内(視程 30〜200 m)", e_fit < 0.02,
         "最大 %.2f %%(%.1f s)" % (100 * e_fit, time.time() - t))

    # 霧の中で色が読める距離: 閉形式 d* = ln(1 + W*/L_h)/β(灯火までの視線の長さ)と、描いた画像で読めた距離
    t = time.time()
    reach_rows = []
    gaps = np.arange(1.0, 29.01, 2.0 if REDUCED else 1.0)
    geom = {}
    for kind in ("red", "yellow", "green"):                      # 霧の無いときに読める距離(灯火が小さくなって読めない所)
        DW.set_signal_state(WORLD, SIG, kind)
        gr = 0.0
        for gp in gaps:
            Pc = cam_at(cam_x_for_gap(gp))
            if read_signal(EV.env_render(WORLD, Pc, K, CAM_W, CAM_H, EV.env_params(sun=FOG_SUN, cloud=1.0), shadows=False)["color"], Pc) != kind:
                break
            gr = float(np.linalg.norm(LAMP_C[kind] - np.array([cam_x_for_gap(gp) + 0.5, LANE_Y, CAM_Z])))
        geom[kind] = gr
    print("  霧なしで読める距離(灯火までの視線): " + ", ".join("%s %.1f m" % kv for kv in geom.items()))
    for mor in (150.0, 200.0, 250.0):
        env = EV.env_params(sun=FOG_SUN, cloud=1.0, fog_mor=mor)
        beta = env["beta"]
        res = []
        L_h = None
        for kind in ("red", "yellow", "green"):
            DW.set_signal_state(WORLD, SIG, kind)
            got = []
            for gp in gaps:
                x_ = cam_x_for_gap(gp)
                Pc = cam_at(x_)
                out = EV.env_render(WORLD, Pc, K, CAM_W, CAM_H, env, shadows=False)
                if L_h is None:
                    sky = out["label"] < 0
                    L_h = float(np.median((out["radiance"] @ np.array([0.2126, 0.7152, 0.0722]))[sky]))   # 大気光 = 画像の空
                rng_l = float(np.linalg.norm(LAMP_C[kind] - np.array([x_ + 0.5, LANE_Y, CAM_Z])))
                got.append((gp, rng_l, read_signal(out["color"], Pc) == kind))
            # 読めた距離 = 手前から連続して読めた最も遠い所(灯火までの視線の長さ)
            reach = 0.0
            for gp, rl, okk in got:
                if not okk:
                    break
                reach = rl
            d_star = min(math.log1p(WSTAR[kind] / L_h) / beta, geom[kind])      # 霧か画素の大きさの近い方
            step = max(np.diff([g_[1] for g_ in got]))
            # 探針ごとに「灯火までの視線 ≤ d* なら読める」の予測と照らす(d* の ±3 % は灯火の画素の間で距離が変わる帯)
            # 霧なしで読める距離(画素の大きさの限界)より遠い探針は外す: 灯火が 4 画素ほどで、読めたり読めなかったりする
            cmp_ = [(rl, okk) for _gp, rl, okk in got if rl <= geom[kind] and abs(rl - d_star) > 0.03 * d_star]
            pred_bad = sum(1 for rl, okk in cmp_ if okk != (rl <= d_star))
            res.append((kind, d_star, reach, step, pred_bad, len(cmp_)))
        reach_rows.append((mor, beta, L_h, res))
        print("  視程 %2.0f m(大気光 %.0f cd/m²): " % (mor, L_h) + ", ".join("%s 閉形式 %.1f m / 画像 %.1f m" % (k, ds, rc) for k, ds, rc, *_ in res))
    n_bad = sum(r[4] for _m, _b, _L, res in reach_rows for r in res)
    n_all = sum(r[5] for _m, _b, _L, res in reach_rows for r in res)
    gate("霧の中で色が読める距離: 各探針で「灯火までの視線 ≤ d* = ln(1 + W*/L_h)/β なら読める」の予測と画像の読みが一致(視程 150/200/250 m × 3 色 × "
         "停止線の 1〜29 m 手前。霧なしで読める距離(画素の大きさの限界)より遠い探針と d* の ±3 % の帯は除く)",
         n_bad == 0, "食い違い %d / %d 探針(%.1f s)" % (n_bad, n_all, time.time() - t))

    # ─────────────────────────── 5. 見えてから止まれるか(霧、閉ループ) ───────────────────────────
    print("== 5. 見えてから止まれるか: 霧の中を赤信号へ近づく(カメラで赤を読んだ瞬間から制動を計画)")
    t = time.time()
    MOR_RUN = 200.0
    env_run = EV.env_params(sun=FOG_SUN, cloud=1.0, fog_mor=MOR_RUN)
    DW.set_signal_state(WORLD, SIG, "red")
    red_reach = [r[1] for mor, _b, _L, res in reach_rows if mor == MOR_RUN for r in res if r[0] == "red"][0]   # 閉形式 d*(前の門で確かめた)
    # 読める距離(視線)→ 前端から停止線までの距離: 灯火は停止線の向こう(交差点の奥)にある
    lamp = LAMP_C["red"]

    def gap_from_range(rl):
        # カメラの x について |lamp − eye| = rl を解く(eye = (x + 0.5, LANE_Y, CAM_Z))
        dy, dz = lamp[1] - LANE_Y, lamp[2] - CAM_Z
        dx = math.sqrt(max(rl * rl - dy * dy - dz * dz, 0.0))
        x_ = lamp[0] - dx - 0.5
        return X_LINE - (x_ + FRONT)

    D_read = gap_from_range(red_reach)
    pz = DL.long_params()
    bcap = min(pz["a_brake_max"], pz["mu"] * pz["g"])
    # 読みは TICK ごと: 最悪 v·TICK 遅れる。止まる余裕 0.5 m(stop_line_plan の margin)
    v_star = EV.sight_stop_speed(max(D_read - 0.5, 0.0), pz["reaction"] + TICK, bcap, 0.0, pz["c_rr"], pz["k"])
    print("  視程 %.0f m で赤が読めるのは停止線の %.1f m 手前から → 止まれる速さ v* = %.1f km/h(反応 %.2f s + 読みの周期 %.1f s、制動 %.1f m/s²)" % (
        MOR_RUN, D_read, 3.6 * v_star, pz["reaction"], TICK, bcap))

    def approach(v0, env, lamps_on=True, x_start_gap=40.0):
        """一定の速さ v0 で近づき、カメラが赤(か黄)を読んだ瞬間に stop_line_plan で止まる。返り値 = (停止線の手前 [m], 読んだ所)。"""
        DW.set_signal_state(WORLD, SIG, "red" if lamps_on else "off")
        s, tt = cam_x_for_gap(x_start_gap), 0.0
        while True:
            gap = X_LINE - (s + FRONT)
            if gap < -3.0:
                return gap, None
            Pc = cam_at(s)
            rd = read_signal(EV.env_render(WORLD, Pc, K, CAM_W, CAM_H, env, shadows=False)["color"], Pc)
            if rd in ("red", "yellow"):
                pl = DL.stop_line_plan(v0, gap, 0.0, pz, t0=tt)
                cmd = DL.plan_command(pl, None, pz)
                r = DL.long_simulate(s, v0, cmd, road=0.0, t_end=pl["t_stop"] + 3.0, dt=0.01, params=pz, t_breaks=pl["t_breaks"], t0=tt)
                return X_LINE - (float(r["s"][-1]) + FRONT), gap
            s += v0 * TICK
            tt += TICK

    if v_star < 0.5:
        raise SystemExit("v* = %.3f m/s: 読める距離が停止線より近い(霧の設定を見直す)" % v_star)
    runs = []
    for fac in (0.9, 1.3):
        v0 = fac * v_star
        g_end, g_read = approach(v0, env_run)
        sc = DL.skill_test_score([{"kind": "stop", "gap": g_end}])
        runs.append((fac, v0, g_end, g_read, sc["score"]))
        print("  %.2f v* = %.1f km/h: 赤を読んだのは停止線の %.1f m 手前、止まったのは %+.2f m(手前 +)、採点 %s" % (
            fac, 3.6 * v0, g_read if g_read is not None else float("nan"), g_end, sc["score"]))
    gate("見えてから止まれるか(視程 %.0f m): 0.9 v* では停止線の手前 0〜2 m に止まり、1.3 v* では越える(閉ループ)" % MOR_RUN,
         0.0 <= runs[0][2] <= 2.0 and runs[1][2] < 0.0,
         "0.9 v*: %+.2f m / 1.3 v*: %+.2f m(%.1f s)" % (runs[0][2], runs[1][2], time.time() - t))

    # ─────────────────────────── 6. 雨 ───────────────────────────
    print("== 6. 雨: 国土交通省の停止距離の式と、濡れた路面で止まるまでの距離")
    t = time.time()
    e_ml = []
    for _vd, V, f in MLIT_F:
        D_ml = 0.694 * V + 0.00394 * V * V / f
        D_our = DL.stopping_distance_grade(V / 3.6, 2.5, f * 9.8, g=9.8)
        e_ml.append(abs(D_our - D_ml) / D_ml)
    gate("第 2 実装: 道路構造令の解説の停止距離 D = 0.694V + 0.00394V²/f(反応 2.5 s、湿潤の f、8 速度)と第 5 回の閉形式の差 < 0.2 %"
         "(式の係数の丸め 2.5/3.6 = 0.69444・1/(2·9.8·3.6²) = 0.0039368 の分)", max(e_ml) < 0.002, "最大 %.3f %%" % (100 * max(e_ml)))
    wet = []
    for mu, name in ((0.8, "乾燥(仮定 0.8)"), (0.38, "湿潤(40 km/h の f 0.38)")):
        p_ = DL.long_params(mu=mu)
        v0 = 40.0 / 3.6
        b = min(p_["a_brake_max"], mu * p_["g"])

        def cmd(tt, s, v, _b=b, _p=p_):
            if tt < _p["reaction"]:
                need = _p["c_rr"] * _p["g"] + _p["k"] * v * abs(v)
                return (need, 0.0)
            return (0.0, _b) if v > 0 else (0.0, _b)
        r = DL.long_simulate(0.0, v0, cmd, road=0.0, t_end=p_["reaction"] + 20.0, dt=0.01, params=p_, t_breaks=[p_["reaction"]])
        s_stop = [e for e in r["events"] if e[0] == "stop"][0][2]
        cf = DL.stopping_distance_grade(v0, p_["reaction"], b, 0.0, p_["c_rr"], p_["k"])
        wet.append((name, mu, b, s_stop, cf))
    print("  40 km/h: " + "; ".join("%s 制動 %.2f m/s² → 停止距離 %.2f m(閉形式 %.2f)" % (n, b, s, c) for n, _m, b, s, c in wet))
    gate("濡れた路面: 40 km/h の停止距離が積分器と閉形式で 1e-6 一致し、湿潤 f 0.38 で乾燥より長い",
         max(abs(w[3] - w[4]) for w in wet) < 1e-6 and wet[1][3] > wet[0][3], "%.2f m → %.2f m(+%.2f m)" % (wet[0][3], wet[1][3], wet[1][3] - wet[0][3]))
    DW.set_signal_state(WORLD, SIG, "red")
    env_rain = EV.env_params(sun=(30.0, 180.0), cloud=1.0, rain=1.0)
    rd_rain = []
    for gp in (6.0, 10.0, 14.0):
        Pc = cam_at(cam_x_for_gap(gp))
        rd_rain.append(read_signal(EV.env_render(WORLD, Pc, K, CAM_W, CAM_H, env_rain, shadows=False)["color"], Pc))
    # 路面に映った赤の灯火の位置 = 路面を鏡にした灯火の鏡像の投影(画像の路面の中の赤い塊で測る)
    Pc = cam_at(cam_x_for_gap(12.0))
    out_r = EV.env_render(WORLD, Pc, K, CAM_W, CAM_H, env_rain, shadows=False)
    mir = LAMP_C["red"] * np.array([1.0, 1.0, -1.0])
    mc, mr, _ = DW.world_project_points(mir[None], Pc, K)
    # 路面(灰色)に赤が薄く重なる → 色度でなく「赤の超過」r − (g + b)/2 の最大の画素(路面の中)で測る
    excess = out_r["color"][..., 0] - 0.5 * (out_r["color"][..., 1] + out_r["color"][..., 2])
    excess = np.where(out_r["label"] == 0, excess, -np.inf)
    er, ec = np.unravel_index(int(np.argmax(excess)), excess.shape)
    d_ref = math.hypot(ec - mc[0], er - mr[0])
    gate("雨: 路面に映った赤は鏡像の投影の位置(< 2 画素)にあり、地図の ROI の外なので信号の読みは乱れない(6/10/14 m で赤)",
         d_ref < 2.0 and rd_rain == ["red"] * 3, "鏡像の位置の差 %.2f 画素、読み %s(%.1f s)" % (d_ref, rd_rain, time.time() - t))

    # ─────────────────────────── 7. 夜: 前照灯と歩行者 ───────────────────────────
    print("== 7. 夜: 前照灯で照らした歩行者を画像で見つける距離(保安基準: すれ違い 40 m・走行 100 m)")
    t = time.time()
    ped = DT.pedestrian_mesh(1.7)
    ped_col = np.full((len(ped["F"]), 3), 0.25)                      # 暗い服(反射率 0.25、仮定)

    def world_with_ped(dist):
        Wn = DW.world_build(DC.course_layout([DC.course_road(260.0, 7.0)], [(0.0, 0.0, 0.0)]))
        xp = x_cam + 0.5 + dist
        DW.world_add(Wn, DW.place_mesh(ped["V"], xp, LANE_Y, math.pi), ped["F"], 7, ped_col, name="pedestrian")
        return Wn

    def detect_ped(img, Pc, x_car):
        """車線の ROI で、同じ行の路面より明るい塊の数(行の中央値 = 同じ距離の路面、それより 0.1 かつ 2 倍以上明るい画素)。ROI = 地図の車線の中心 ±1.2 m の台形(路面の行ごとに左右の縁を投影、地平線より上は
        遠方の幅)で、行は地平線の上 40 画素〜下 20 画素(路面なら 37 m より遠い所)。前照灯が照らす手前の路面と白線は ROI の外。"""
        ds = np.geomspace(15.0, 600.0, 200)
        L_ = np.array([[x_car + 0.5 + d, LANE_Y - 1.2, 0.0] for d in ds])
        R_ = np.array([[x_car + 0.5 + d, LANE_Y + 1.2, 0.0] for d in ds])
        cl, rl, _ = DW.world_project_points(L_, Pc, K)
        cr, _rr, _ = DW.world_project_points(R_, Pc, K)
        r0, r1 = int(max(0, v_h - 40)), int(min(CAM_H, v_h + 20))
        rows_ = np.arange(r0, r1)
        ca = np.interp(rows_, rl[::-1], cl[::-1])                      # 地平線より上は最も遠い幅で頭打ち(np.interp の端)
        cb = np.interp(rows_, rl[::-1], cr[::-1])
        lo, hi = np.minimum(ca, cb), np.maximum(ca, cb)                # +y は進行方向の左 = 画像の左(縁の左右は向きで入れ替わる)
        cols_ = np.arange(CAM_W)
        mask = (cols_[None, :] >= lo[:, None]) & (cols_[None, :] <= hi[:, None])
        lum = img[r0:r1] @ np.array([0.2126, 0.7152, 0.0722])
        # 同じ行の路面(= 同じ距離の路面)より明るい所だけ: 行ごとの ROI の中央値を引く(歩行者は車線の幅の 2 割ほどなので中央値は路面)
        med = np.array([np.median(lum[i][mask[i]]) if mask[i].any() else 0.0 for i in range(len(rows_))])
        exc = np.where(mask, lum - med[:, None], 0.0)
        excess = np.where(exc > np.maximum(0.1, 2.0 * med[:, None]), exc, 0.0)
        return BT.ball_detect(excess, mode="bright", thresh=0.1, radius_range=(0.5, 60.0))

    night_rows = {}
    dists = (20.0, 30.0, 40.0, 50.0, 60.0, 80.0, 100.0, 120.0, 150.0) if not REDUCED else (20.0, 40.0, 60.0, 100.0, 150.0)
    for beam in ("low", "high"):
        env_n = EV.env_params(sun=(-25.0, 0.0), headlamps=beam)
        seen = []
        for dd in dists:
            Wn = world_with_ped(dd)
            out = EV.env_render(Wn, Pf, K, CAM_W, CAM_H, env_n, ego_pose=(x_cam - 1.7, LANE_Y, 0.0), shadows=False)
            empty = EV.env_render(WR, Pf, K, CAM_W, CAM_H, env_n, ego_pose=(x_cam - 1.7, LANE_Y, 0.0), shadows=False)
            n_ped, n_emp = len(detect_ped(out["color"], Pf, x_cam)), len(detect_ped(empty["color"], Pf, x_cam))
            seen.append((dd, n_ped > 0 and n_emp == 0, n_ped, n_emp))
        reach = max([dd for dd, okk, *_ in seen if okk], default=0.0)          # 見つけた最も遠い距離
        night_rows[beam] = (reach, seen)
        print("  %s: " % {"low": "すれ違い灯", "high": "走行灯"}[beam] + ", ".join("%.0f m %s" % (dd, "o" if okk else "x") for dd, okk, *_ in seen)
              + " → 見つけられる距離 %.0f m" % reach)
    gate("夜: 仮定した配光で、すれ違い灯は 40 m・走行灯は 100 m の歩行者を画像で見つける(保安基準の性能)。空の車線では何も見つけない",
         dict((dd, okk) for dd, okk, *_ in night_rows["low"][1]).get(40.0, False)
         and dict((dd, okk) for dd, okk, *_ in night_rows["high"][1]).get(100.0, False),
         "すれ違い %.0f m / 走行 %.0f m(%.1f s)" % (night_rows["low"][0], night_rows["high"][0], time.time() - t))
    tbl = []
    for beam in ("low", "high"):
        for rho, b, name in ((pz["reaction"], bcap, "乾燥・反応 0.75 s"), (2.5, 0.38 * 9.8, "湿潤 f 0.38・反応 2.5 s(道路構造令)")):
            tbl.append((beam, name, night_rows[beam][0], 3.6 * EV.sight_stop_speed(night_rows[beam][0], rho, b)))
    print("  見つけてから止まれる速さ: " + "; ".join("%s %s: %.0f m → %.0f km/h" % ({"low": "すれ違い", "high": "走行"}[b], n, d, v)
                                                   for b, n, d, v in tbl))

    # 閉ループ: すれ違い灯で歩行者へ近づき、見つけた瞬間から全制動(反応つき)
    t = time.time()
    DIST_P = 80.0
    Wn = world_with_ped(DIST_P + 40.0)                              # 歩行者は出発点の 120 m 先
    x_ped = x_cam + 0.5 + DIST_P + 40.0
    env_n = EV.env_params(sun=(-25.0, 0.0), headlamps="low")
    Wn_empty = WR

    def night_run(v0):
        s, tt = x_cam, 0.0
        while s + FRONT < x_ped:
            Pc = cam_at(s)
            out = EV.env_render(Wn, Pc, K, CAM_W, CAM_H, env_n, ego_pose=(s, LANE_Y, 0.0), shadows=False)
            if detect_ped(out["color"], Pc, s):
                gap0 = x_ped - (s + FRONT)
                r = DL.long_simulate(s, v0, lambda t_, s_, v_: (0.0, bcap) if t_ >= tt + pz["reaction"] else (pz["c_rr"] * pz["g"] + pz["k"] * v_ * abs(v_), 0.0),
                                     road=0.0, t_end=tt + pz["reaction"] + 30.0, dt=0.01, params=pz, t_breaks=[tt + pz["reaction"]], t0=tt)
                return x_ped - (float(r["s"][-1]) + FRONT), gap0
            s += v0 * TICK
            tt += TICK
        return -1.0, None

    if night_rows["low"][0] <= 0:
        raise SystemExit("すれ違い灯で歩行者を見つけられない: 夜の閉ループは走らせない")
    v_n = EV.sight_stop_speed(max(night_rows["low"][0] - 0.0, 0.0), pz["reaction"] + TICK, bcap, 0.0, pz["c_rr"], pz["k"])
    nrun = []
    for fac in (0.85, 1.3):
        g_end, g_seen = night_run(fac * v_n)
        nrun.append((fac, fac * v_n, g_end, g_seen))
        print("  %.2f v* = %.1f km/h: 見つけたのは歩行者の %.1f m 手前、止まったのは %+.2f m 手前" % (
            fac, 3.6 * fac * v_n, g_seen if g_seen is not None else float("nan"), g_end))
    gate("夜の閉ループ(すれ違い灯): 見つけられる距離から出した v* = %.1f km/h の 0.85 倍では歩行者の手前に止まり、1.3 倍では止まれない" % (3.6 * v_n),
         nrun[0][2] > 0.0 and nrun[1][2] < 0.0, "%+.2f m / %+.2f m(%.1f s)" % (nrun[0][2], nrun[1][2], time.time() - t))

    # ─────────────────────────── 8. ゼロ点 ───────────────────────────
    t = time.time()
    DW.set_signal_state(WORLD, SIG, "off")
    zero = []
    for name, env in (("晴れ", EV.env_params(sun=(40.0, 180.0))), ("霧", EV.env_params(sun=FOG_SUN, cloud=1.0, fog_mor=200.0)),
                      ("雨", env_rain), ("夜", EV.env_params(sun=(-25.0, 0.0), headlamps="low"))):
        Pc = cam_at(cam_x_for_gap(10.0))
        zero.append((name, read_signal(EV.env_render(WORLD, Pc, K, CAM_W, CAM_H, env, shadows=False, ego_pose=(cam_x_for_gap(10.0), LANE_Y, 0.0))["color"], Pc)))
    gate("ゼロ点: 灯火を消すと晴れ・霧・雨・夜のどれでも 'unknown'(fail-closed)", all(r == "unknown" for _, r in zero),
         ", ".join("%s %s" % z for z in zero))

    # ─────────────────────────── 9. 図 ───────────────────────────
    if figs.enabled():
        print("== 9. 図")
        t = time.time()
        make_figures(WORLD, SIG, cam_at, cam_x_for_gap, read_signal, rows_sun, series, win, back_rows, fog_rows, reach_rows, WR, Pf,
                     world_with_ped, night_rows, x_cam, v_h, runs, v_star, D_read, MOR_RUN)
        print("  図 %.1f s" % (time.time() - t))
        if figs.errors():
            print("図の書き出しで失敗:", "; ".join(figs.errors()))

    print("== 結果: %d / %d 門, %.1f s" % (sum(OK), len(OK), time.time() - T0))
    print("PASS" if all(OK) else "FAIL")
    return 0 if all(OK) else 1


def _label(img, txt, size=11):
    return np.asarray(AN.text_box(img, txt, (6, 6), anchor="lt", font_size=size), dtype=float).copy()


def make_figures(WORLD, SIG, cam_at, cam_x_for_gap, read_signal, rows_sun, series, win, back_rows, fog_rows, reach_rows, WR, Pf,
                 world_with_ped, night_rows, x_cam, v_h, runs, v_star, D_read, MOR_RUN):
    """図 7 枚(GIF 1 本を含む)。"""
    # 01: 春分の一日(車載カメラ + 斜め上から)。朝は逆光で赤が読めず、夜は前照灯。
    Wg, Hg = (400, 250) if REDUCED else (480, 300)
    Kg = DW.camera_intrinsics(60.0, Wg, Hg)
    Kb = DW.camera_intrinsics(50.0, Wg, Hg)
    DW.set_signal_state(WORLD, SIG, "red")
    xr = cam_x_for_gap(15.0)
    Pr = cam_at(xr)
    Pb = DW.camera_pose((-48.0, -24.0, 20.0), (-6.0, 2.0, 0.0))            # 近づく車と交差点を斜め上から
    EGO = DW.load_asset("sedan", paint="blue")
    egoV = DW.place_mesh(EGO["V"], xr, LANE_Y, 0.0)
    frames = []
    cache = {}
    step = 30 if REDUCED else 15
    t0_ = datetime(2026, 3, 20, 5, 15, tzinfo=JST)
    for m_ in range(0, 15 * 60 + 1, step):
        tt = t0_ + timedelta(minutes=m_)
        sp = EV.sun_at(tt, *TOKYO)
        hl = "low" if sp["elevation"] < 2.0 else "off"
        env = EV.env_params(tt, *TOKYO, headlamps=hl)
        a = EV.env_render(WORLD, cam_at(xr), Kg, Wg, Hg, env, ego_pose=(xr, LANE_Y, 0.0), shadow_cache=cache, shadows=True)
        rd = read_signal(EV.env_render(WORLD, Pr, K, CAM_W, CAM_H, env, shadows=False, ego_pose=(xr, LANE_Y, 0.0))["color"], Pr)
        b = EV.env_render(WORLD, Pb, Kb, Wg, Hg, env, ego=(egoV, EGO["F"], EGO["color"]), ego_pose=(xr, LANE_Y, 0.0), shadow_cache=cache)
        ia = _label(a["display"], "車載カメラ(停止線の 15 m 手前)\n信号の読み: %s" % {"red": "赤", "unknown": "読めない"}.get(rd, rd))
        ib = _label(b["display"], "2026-03-20 %s 東京\n太陽 高度 %.1f° 方位 %.1f°%s" % (
            tt.strftime("%H:%M"), sp["elevation"], sp["azimuth"], "  前照灯" if hl != "off" else ""))
        frames.append(np.concatenate([ia, ib], axis=1))
    figs.save_gif("sun_day", frames, fps=3.0 if REDUCED else 4.0,
                  caption="春分(2026-03-20)の東京、朝 5:15 から夜 20:15 まで %d 分おき。左 = 東へ向かう車の車載カメラ(停止線の 15 m 手前)と"
                          "信号の読み、右 = 斜め上から(影が太陽と反対へ伸び、短くなってまた伸びる)。朝、太陽が信号の後ろの低い空にある間は"
                          "光幕で赤の色度が灰色へ寄り、画像処理は「読めない」(%s〜%s)。日が沈むと前照灯を点ける。" % (
                              step, win[0].strftime("%H:%M") if win else "-", win[-1].strftime("%H:%M") if win else "-"))
    # 02: 太陽の高度の一日と暦計算室の点
    curves, kinds = [], []
    for m, d, ev in rows_sun:
        ts_ = [datetime(2026, m, d, tzinfo=JST) + timedelta(minutes=k_) for k_ in range(0, 24 * 60, 10)]
        curves.append(("%d/%d" % (m, d), [hm(x) / 60.0 for x in ts_], [EV.sun_at(x, *TOKYO)["elevation"] for x in ts_]))
        kinds.append("line")
    pts_x, pts_y = [], []
    for (m, d, rise, _a, tr, alt, sett, _b) in NAOJ:
        for s_, y_ in ((rise, 0.0), (tr, alt), (sett, 0.0)):
            hh, mm = (int(x) for x in s_.split(":"))
            pts_x.append(hh + mm / 60.0)
            pts_y.append(y_)
    curves.append(("暦計算室(日の出入り・南中)", pts_x, pts_y))
    kinds.append("scatter")
    figs.save_plot("sun_elevation", curves, kinds=kinds, title="東京の太陽の高度と暦計算室", xlabel="時刻(日本標準時)[h]", ylabel="太陽の高度 [°]",
                   caption="東京の太陽の高度(NOAA の式、大気差つき)と国立天文台 暦計算室の公表値(点: 日の出・日の入りは高度 0、南中は高度)。"
                           "24 値が丸めの単位(1 分・0.1°)で一致。")
    # 03: 逆光 —— θ と読み、閾値
    rows3 = []
    for kind in ("red", "yellow", "green"):
        rr_ = [r for r in back_rows if r[0] == kind]
        rows3.append(("%s 読めた" % kind, [r[1] for r in rr_ if r[4] == kind], [r[3] for r in rr_ if r[4] == kind]))
        rows3.append(("%s 読めない" % kind, [r[1] for r in rr_ if r[4] != kind], [r[3] for r in rr_ if r[4] != kind]))
    rows3.append(("θ = θ*", [0, 32], [0, 32]))
    figs.save_plot("backlight_threshold", rows3, title="逆光: 太陽と視線の角と閾値", kinds=["scatter"] * 6 + ["line"], xlabel="太陽と視線の角 θ [°]", ylabel="閾値 θ* [°]",
                   caption="逆光: 横 = 太陽と灯火への視線の角 θ、縦 = 画素の式から先に出した閾値 θ* = √(10 E_dn / W*)(高度で変わる)。"
                           "対角線の右下(θ > θ*)は読め、左上は光幕で色度が灰色に寄って読めない。赤が最も弱い(W* が小さい)。")
    # 04: 霧の画像と 05: 路面の輝度の曲線
    DW.set_signal_state(WORLD, SIG, "red")
    Pc = cam_at(cam_x_for_gap(15.0))
    panels, caps = [], []
    for mor in (None, 400.0, 200.0, 100.0):
        env = EV.env_params(sun=FOG_SUN, cloud=1.0, fog_mor=mor)
        out = EV.env_render(WORLD, Pc, K, CAM_W, CAM_H, env, shadows=False)
        panels.append(out["display"])
        caps.append("霧なし" if mor is None else "視程 %.0f m(β = %.4f)読み: %s" % (mor, env["beta"], read_signal(out["color"], Pc)))
    figs.save_grid("fog_views", panels, captions=caps, ncols=2,
                   caption="霧(Koschmieder、曇天)の車載カメラ、停止線の 15 m 手前。灯火は交差点の向こう(停止線から約 26 m 先)にあり、霧が濃いほど色度が大気光(白)に埋もれる。各図の「読み」は画像処理の結果。")
    series5 = []
    for mor, bt, bf, bi, mo, rows_, prof, fit in fog_rows:
        series5.append(("視程 %.0f m(画像)" % mor, rows_, prof))
    for mor, bt, bf, bi, mo, rows_, prof, fit in fog_rows:
        d = EV.road_row_distance(rows_, v_h, FOCAL, CAM_Z, math.atan(0.45 / 19.5))
        r = np.sqrt(d * d + CAM_Z ** 2)
        series5.append(("当てはめ %.0f m → %.1f m" % (mor, mo), rows_, fit["L_h"] + (fit["L0"] - fit["L_h"]) * np.exp(-fit["beta_fit"] * r)))
    figs.save_plot("fog_profile", series5, title="霧の濃さを路面の輝度から測る", kinds=["scatter"] * len(fog_rows) + ["line"] * len(fog_rows), xlabel="画像の行(下向き +)",
                   ylabel="路面の輝度 [cd/m²]",
                   caption="霧の濃さを画像から測る: 車線の中の路面の輝度を行ごとに並べると(点、雑音 1 %)、遠い行ほど大気光へ近づく。"
                           "行 → 距離(カメラの高さと焦点距離)に Koschmieder を当てた線から視程を戻す(真の値と 2 % 以内)。")
    # 06: 読める距離と止まれる速さ
    mors = np.linspace(80, 400, 60)
    L_h = reach_rows[0][2]
    s6 = []
    for kind in ("red", "yellow", "green"):
        W = EV.veil_chroma_limit(DW._LAMP[kind], 10000.0, TOL)
        s6.append(("%s 閉形式 d*" % kind, mors, [math.log1p(W / L_h) / EV.beta_from_mor(m) for m in mors]))
    for kind in ("red", "yellow", "green"):
        s6.append(("%s 画像" % kind, [mor for mor, *_ in reach_rows], [[r[2] for r in res if r[0] == kind][0] for _m, _b, _L, res in reach_rows]))
    figs.save_plot("fog_reach", s6, title="霧の中で色が読める距離", kinds=["line"] * 3 + ["scatter"] * 3, xlabel="視程(気象光学距離)[m]", ylabel="色が読める距離 [m]",
                   caption="霧の中で灯火の色が読める距離: 閉形式 d* = ln(1 + W*/L_h)/β(線)と、描いた画像で読めた距離(点)。探針ごとの読める / 読めないは予測と一致。"
                           "視程 %.0f m で赤が読めるのは停止線の %.1f m 手前から → 止まれる速さ %.1f km/h。その 0.9 倍では手前 %+.2f m に止まり、"
                           "1.3 倍では %+.2f m(越えた)。" % (MOR_RUN, D_read, 3.6 * v_star, runs[0][2], runs[1][2]))
    # 07: 雨と夜
    panels, caps = [], []
    Pc = cam_at(cam_x_for_gap(12.0))
    out = EV.env_render(WORLD, Pc, K, CAM_W, CAM_H, EV.env_params(sun=(30.0, 180.0), cloud=1.0, rain=1.0), shadows=False)
    panels.append(out["display"])
    caps.append("雨: 濡れた路面に赤が映る(鏡像)。読み %s" % read_signal(out["color"], Pc))
    out = EV.env_render(WORLD, Pc, K, CAM_W, CAM_H, EV.env_params(sun=(-25.0, 0.0), headlamps="low"), shadows=False,
                        ego_pose=(cam_x_for_gap(12.0), LANE_Y, 0.0))
    panels.append(out["display"])
    caps.append("夜: 灯火は自分で光る。読み %s" % read_signal(out["color"], Pc))
    for beam, dd in (("low", 40.0), ("high", 100.0)):
        Wn = world_with_ped(dd)
        out = EV.env_render(Wn, Pf, K, CAM_W, CAM_H, EV.env_params(sun=(-25.0, 0.0), headlamps=beam), shadows=False,
                            ego_pose=(x_cam - 1.7, LANE_Y, 0.0))
        panels.append(out["display"])
        caps.append("%s・歩行者 %.0f m(見つけられる距離 %.0f m)" % ({"low": "すれ違い灯", "high": "走行灯"}[beam], dd, night_rows[beam][0]))
    figs.save_grid("rain_night", panels, captions=caps, ncols=2,
                   caption="雨と夜。上: 濡れた路面に映った赤は路面の中(地図の ROI の外)にあり、読みを乱さない / 夜は灯火が自分で光るので読みやすい。"
                           "下: 前照灯で照らした歩行者(反射率 0.25)。すれ違い灯は上を切るので脚だけが明るく、走行灯は遠くまで届く。")


if __name__ == "__main__":
    sys.exit(main())
