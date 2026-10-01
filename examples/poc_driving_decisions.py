# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC ㉚(自動運転 第 9 回): 判断の場面 —— ミラーと死角、確認の順序、歩行者信号から黄を予測してジレンマゾーンを避ける、
救急車に音と光で気づいて交差点の手前で左に寄る、発進の合図をしたバスを待つ、を閉形式と独立な経路で採点する。

著者の発案: 「信号は歩行者信号の動きを見て予測も必要」「ミラーの確認もいる」「救急車が来た時もちゃんとしないといけない」
「(バス停車中は)出来れば発車まで待つほうが良い」。第 8 回までで「見える / 止まれる」は測れるようになった。ここでは運転者が
**決める** 場面 —— どこを見て、いつ合図し、黄で止まるか抜けるか、サイレンがどちらから来るか、誰に道を譲るか —— を扱う
(部品は :mod:`drivedecide`、バスに付いていく IDM は :mod:`drivetraffic`)。

門(真値の出どころ):
  1. **鏡像の画素位置**: ルームミラー(平面)を drivedecide.mirror_virtual_camera の仮想カメラ F·P·S で描いて左右を反転した絵の
     目印の重心 = 鏡面上の点を Fermat の最短経路(Newton)で解いて実カメラで写した画素(12 点、≤ 1 px)、折り返しの式 P·S(Q) =
     Fermat(≤ 1e-6 px)。左右反転を外すと中央値 228 px ずれる(門が自明でない)。
  2. **死角の多角形**: 左ドアミラー(凸面)の死角(mirror_blind_zone)= 柱を格子(295 点)に立て、両端の反射光線の交点に置いた
     後ろ向きの仮想カメラで描いて「写る ⇔ 多角形の外」(縁 ±0.15 m の 27 点は除外)。
  3. **左折の巻き込み**: 左ドアミラーで左後方を確かめて自転車を追う自車は 400 試行で巻き込まない(最小 1.08 m)。直接の視界だけ
     (ミラーを見ない)だと 68 試行で巻き込む。
  4. **確認の順序**: 自車の左折(ミラー → 30 m 手前で合図 → 左折 → 合図をやめる)と車線変更(ミラー → 約 3 s 前に合図)は
     check_sequence_score の減点 0。順序・時期・継続を崩した 6 版は、警察庁 丁運発第44号の点数(安全不確認 10 / 合図不履行等 5)
     だけ減点される。
  5. **信号の読み取り**: 並行する歩行者信号の灯火の点灯を車載カメラの画素(灯火のまわり 48 × 48 を同じ焦点距離で描く)から読んだ値 =
     描いた時刻の真値(690 コマ全部)、点滅の周波数 = 1.000 Hz。
  6. **黄の予測**: 画像から読んだ観測で predict_amber_onset の区間が全コマ(585 回)で真値を含み、半幅 ≤ (点灯の長さ + 1 コマ)/2。
  7. **ジレンマゾーン**: 予測して早めに止まる / 抜けると決めた自車は 600 試行で黄の瞬間にジレンマゾーンに入らない(GHM と停止線の
     両方の読み)。予測しないと GHM の読みで 48 試行(停止線の読みで 10)入る。
  8. **気づくまでの遅れ**: 赤色灯の点滅はミラーに点いて写ってから 0.233 s(≤ 半周期 + 1 コマ)、サイレンの「近づく」は 0.3 s。
  9. **ドップラー**: doppler_track の近づく / 遠ざかる = 幾何の距離の変化率の符号(99.89 %、減速して左に寄るマイクのまま)。
  10. **TDOA の方位** = 幾何(前後は折り返す)±0.5°(29 窓、最大 0.11°)。
  11. **点滅の周波数** = 式: ミラーの赤い画素の数の時系列で 2.5 Hz、3.75 fps に間引くと折り返して 1.25 Hz(aliased_frequency)。
  12. **40 条**: 交差点の附近で気づいた自車は交差点の手前で左に寄って一時停止(1 項)、附近でない所では左に寄って譲る(2 項)——
      yield_maneuver_check で違反なし。左に寄らずに止まる版は「左に寄っていない」、進みながら近づいてから止まる版は
      「交差点の中で止まった」(門が自明でない)。
  13. **31 条の 2**: 既定(バスの後ろで発車まで待つ)と 40 m 手前から譲る版は違反なし、要る減速 a_req = 刻み 0.1 ms のブレーキ +
      二分法(rel 2e-3)。合図の時に追い越す版・そのまま抜ける版は違反、13 m 手前(急に減速しないと譲れない)は義務なし。

正直に書くこと:
* **仮定の値**: 判断の遅れ 1.0 s、交差点の「附近」30 m・「左に寄る」1.0 m・「急に」3.0 m/s²(法に数値なし)、ドアミラー(凸面
  R 1.4 m・幅 0.18 m・目と同じ高さ)、歩行者信号の点滅 1 Hz(点いている側から始まる)、赤色灯 2.5 Hz(法令に回数の規定なし)、
  Δ = 2 s・黄 3 s・全赤 2 s・青点滅 F = 横断長 / 1.0 m/s、マイクの雑音、救急車 60 km/h。出典と状態は drivedecide.SOURCES。
* **凸面のドアミラーは針穴で近似**: 写る範囲(水平)は両端の反射光線の挟む楔と **厳密に同じ** だが、楔の中の写り方(凸面の歪み)は
  中心射影の近似。縦の視野も近似。鏡の本体・車体・窓枠・ピラーは描かない(ミラーに自車の車体は写らない)。
* **死角は 2D**(目と鏡の高さを揃え法線を水平にした)。直接の視界は方位 100° の線 1 本で、首を回す目視は持たない。左折の試行の
  見える / 見えないは 2D の判定(門 2 で 3D の絵と一致を確かめたもの)で、試行ごとには描いていない。
* **歩行者信号は運転者の方を向いて置いた**(並行する横断歩道の向こう端の灯火は実際にも −x を向く)。点滅の周期は知っている前提
  (点滅の始まりの不確かさを T_ON + 1 コマにする)。押しボタン・感応式は扱わない。灯火は発光(陰影なし)で描く。
* **救急車は初めから 100 m 後ろで見え、聞こえている**。遅れの門は検出器の遅れ(点滅の半周期・判定の窓)で、どこまで遠くで
  気づけるか(検出距離)ではない。サイレンの合成は風・反射・車内の遮音を持たない。視線速度の誤差は遠くで雑音が効いて 99 % 点
  5.87 m/s(判定の符号は 99.89 % 合う)。
* render3d は近い面の切り落としが無い(頂点が 1 つでもカメラの後ろの三角形を描かない)ので、カメラの真横の格子の抜けは地面の色で
  埋めた(物体のラベルは付けない)。鏡の向こう側の面は先に落としてから描く。

教則の場面: S002, S026, S027, S029, S054, S066, S067, S070, S091(docs/drive/kyosoku_scenarios.json、交通の方法に関する教則の再現台帳)

Run: py -3.11 examples/poc_driving_decisions.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く。
FULLSEYE_POC_BUDGET=reduced(CI の既定)で試行数・読み取りの fps・動画の大きさを減らす)
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
import drivedecide as DD  # noqa: E402
import drivetraffic as TR  # noqa: E402
import driveworld as DW  # noqa: E402
import driveterrain as DT  # noqa: E402
import annotate as AN  # noqa: E402

#: 予算: reduced(CI の既定)は試行数を減らし、読み取りを 15 fps・動画を 320 × 180 に。展示の数字は full の実測。
REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
N_BIKE = 120 if REDUCED else 400              # 左折と自転車の試行
N_SIG = 150 if REDUCED else 600               # 信号の予測の試行
CAM_FPS = 15.0 if REDUCED else 30.0           # 車載カメラのコマ(読み取り・門はこの速さ)
VID_EVERY = 2 if REDUCED else 3               # 動画は VID_EVERY コマに 1 枚(7.5 / 10 fps。描画の時間を抑える)
VID_WH = (320, 180) if REDUCED else (640, 360)
T0 = time.time()
OK = []

# ── カメラ(読み取りは予算に依らず同じ焦点距離。reduced は動画を縮めるだけ) ──
CAM_W, CAM_H, CAM_HFOV = 768, 432, 50.0
CAM_VFOV = math.degrees(2 * math.atan(math.tan(math.radians(CAM_HFOV / 2)) * CAM_H / CAM_W))

# ── 道と車(座標: x = 道に沿って前、y = 左。左側通行で自車線は y ∈ [0, 3.25]、路側帯 3.25〜4.5、縁石 4.5) ──
ROAD = 4.5            # 縁石(車道の端)
EDGE = 3.25           # 車道外側線
Y_LANE = 1.625        # 自車線の中心
Y_BIKE = 3.9          # 自転車(路側帯)
EGO_L, EGO_W = 4.5, 1.8
EYE_FWD = 0.45        # 車の中心から目まで(前へ)
EYE_RIGHT = 0.37      # 車の中心から目まで(右へ = 右ハンドル)
EYE_Z = 1.15          # 目の高さ = ドアミラーの高さ(鏡の法線を水平にして 2D の死角と 3D の絵を厳密に揃える)
XC = 230.0            # 交差点の中心(交差道路 x ∈ [225, 235])
X_CROSS = (225.0, 235.0)
S_LINE = 220.0        # 停止線
X_FAR = 240.0         # 交差点の向こう側(向こうの横断歩道の先)。GHM の w = X_FAR − S_LINE = 20 m
R_TURN = 5.0          # 左折の半径(車の中心)
X_T = XC - 1.625 - R_TURN   # 左折を始める車の中心の x
V_CRUISE = 30.0 / 3.6
V_TURN = 3.0

# ── 仮定の値(出典は drivedecide.SOURCES。一次で確かめた値は SOURCES の status を見る) ──
REACT = 1.0           # 運転者・自動運転の判断の遅れ(緊急車両・バス)[s](仮定)
NEAR_MARGIN = 30.0    # 交差点の「附近」(仮定、法に数値なし)
LEFT_TOL = 1.0        # 「左に寄る」= 左端から 1.0 m 以内(仮定)
PED_FLASH_HZ = 1.0    # 歩行者信号の青点滅(0.5 s 点く・0.5 s 消える)(仮定)
BEACON_HZ = 2.5       # 救急車の赤色灯の点滅(法令に回数の規定なし = 仮定)
SIG = dict(crossing_length=X_CROSS[1] - X_CROSS[0], ped_green=20.0, ped_red_to_amber=2.0, amber=3.0, all_red=2.0,
           cross_green=20.0)       # 並行する横断歩道 10 m → F = 10 s(歩行速度 1.0 m/s、SOURCES)、Δ 2 s・黄 3 s・全赤 2 s は例
GHM = dict(reaction=1.0, decel=3.0, amber=3.0, intersection_width=X_FAR - S_LINE, car_length=EGO_L)
STOPLINE = dict(GHM, intersection_width=0.0, car_length=0.0)      # 教則 付表1 の読み(停止線を越えればよい)
A_GENTLE = 2.0        # 予測して早めに止まるときの減速 [m/s²](仮定)
V_SIG = 50.0 / 3.6    # 信号の場面の速さ
FS_AUDIO = 16000.0    # マイクの標本化 [Hz]
MIC_D = 0.15          # マイクの間隔 [m](< c/(2 f) ≈ 0.17 m で方位が一意)
V_AMB = 60.0 / 3.6    # 救急車の速さ
Y_AMB = -0.4          # 救急車の通る線(中央線をまたぐ)

JP = {"cruise": "巡航", "mirror": "ミラーで確認", "signal": "左の合図", "slow": "減速(左折の準備)",
      "wait_bike": "自転車を先に通す", "turn": "左折", "after": "左折の後", "hear": "サイレンを聞いた",
      "pull_stop": "交差点の手前で左に寄って一時停止", "pull_yield": "左に寄って進路を譲る", "stopped": "一時停止(通過を待つ)",
      "resume": "通過した → 発進", "go": "そのまま進む(黄の前に抜けられる)", "prep_stop": "止まる準備(早めに減速)",
      "brake": "停止線で止まる", "red": "赤で停止中", "no_pred": "予測なし"}


def gate(name, cond, detail=""):
    OK.append(bool(cond))
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


# ───────────────────────────── 世界(3D) ─────────────────────────────
def _box_mesh(L, W, H, z0=0.0):
    V = np.array([[x, y, z] for z in (z0, z0 + H) for y in (-W / 2, W / 2) for x in (-L / 2, L / 2)])
    F = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4],
                  [1, 5, 7], [1, 7, 3]])
    return V, F


def _quad(x0, x1, y0, y1, z=0.006):
    return np.array([[x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z]]), np.array([[0, 1, 2], [0, 2, 3]])


def _mesh(parts):
    """[(V, F, color)] → {"V", "F", "color"}(原点 = 底面中心)。"""
    V = np.zeros((0, 3))
    F = np.zeros((0, 3), np.int64)
    C = []
    for v, f, c in parts:
        F = np.vstack([F, f + len(V)])
        V = np.vstack([V, v])
        C.append(np.tile(np.asarray(c, float), (len(f), 1)))
    return {"V": V, "F": F, "color": np.vstack(C)}


def bicycle_mesh():
    """自転車 + 乗る人(箱で組む。長さ 1.8 m、高さ 1.75 m)。"""
    parts = []
    for dx in (-0.55, 0.55):                                             # 車輪(薄い箱)
        v, f = _box_mesh(0.66, 0.06, 0.66)
        parts.append((v + [dx, 0, 0], f, (0.10, 0.10, 0.12)))
    v, f = _box_mesh(1.1, 0.06, 0.08, 0.55)
    parts.append((v, f, (0.15, 0.45, 0.85)))                             # 枠
    v, f = _box_mesh(0.30, 0.36, 0.62, 0.85)
    parts.append((v + [-0.05, 0, 0], f, (0.95, 0.85, 0.20)))             # 胴(黄の上着)
    v, f = _box_mesh(0.22, 0.22, 0.24, 1.48)
    parts.append((v + [0.02, 0, 0], f, (0.92, 0.92, 0.95)))              # ヘルメット
    m = _mesh(parts)
    m.update(label=14, dims=(1.8, 0.6, 1.75))
    return m


def ambulance_mesh():
    """救急車(白い箱型、屋根の前に赤色灯の横長の灯具)。長さ 5.6 m・幅 1.9 m・高さ 2.5 m。赤色灯は別の物体で足す。"""
    parts = []
    v, f = _box_mesh(4.0, 1.9, 2.15, 0.35)
    parts.append((v + [-0.8, 0, 0], f, (0.96, 0.96, 0.96)))             # 箱
    v, f = _box_mesh(1.6, 1.9, 1.35, 0.35)
    parts.append((v + [2.0, 0, 0], f, (0.93, 0.93, 0.93)))              # 運転席
    v, f = _box_mesh(0.05, 1.7, 0.55, 1.0)
    parts.append((v + [2.8, 0, 0], f, (0.15, 0.20, 0.28)))              # 前の窓
    v, f = _box_mesh(4.0, 1.92, 0.12, 1.2)
    parts.append((v + [-0.8, 0, 0], f, (0.55, 0.12, 0.12)))             # 帯(暗い赤。赤色灯の検出のしきい値より暗い)
    for dx in (-2.0, 1.9):
        v, f = _box_mesh(0.7, 2.0, 0.7)
        parts.append((v + [dx, 0, 0], f, (0.08, 0.08, 0.08)))
    m = _mesh(parts)
    m.update(label=2, dims=(5.6, 1.9, 2.5))
    return m


def bus_mesh():
    parts = []
    v, f = _box_mesh(10.5, 2.5, 2.7, 0.35)
    parts.append((v, f, (0.20, 0.55, 0.40)))
    v, f = _box_mesh(10.3, 2.52, 0.8, 1.6)
    parts.append((v, f, (0.15, 0.20, 0.28)))
    m = _mesh(parts)
    m.update(label=2, dims=(10.5, 2.5, 3.05))
    return m


def add_obj(w, mesh, x, y, yaw, name):
    return DT.add_mesh_object(w, mesh, x, y, yaw, name=name)


def add_flat(w, V, F, label, color, name):
    return DW.world_add(w, V, F, label, color, name=name)


def build_world():
    """片側 1 車線 + 路側帯の道、交差点(x ∈ [225, 235])、停止線、横断歩道、車両の信号、並行する歩行者の信号、建物。

    返り値: (world, 物体の索引の dict)。動く物体(自転車・救急車・バス・目印)は初めは遠くに置く。"""
    w = DW._empty_world()
    for (x0, x1) in ((-120.0, X_CROSS[0]), (X_CROSS[1], 480.0)):
        V, F = DW._grid_plane(x0, x1, -ROAD, ROAD, step=2.5)
        add_flat(w, V, F, 0, DW._ROAD_COLOR, "road")
        for side in (1.0, -1.0):
            V, F = DW._grid_plane(x0, x1, 0.0, 12.0, step=2.5, z=0.15)
            V[:, 1] = side * (ROAD + V[:, 1])
            add_flat(w, V, F if side > 0 else F[:, ::-1], 1, (0.70, 0.70, 0.66), "sidewalk")
            parts = []                                                       # 10 m ごとに切る(頂点が 1 つでも
            for xa in np.arange(x0, x1, 10.0):                               # カメラの後ろにある三角形は描かれない)
                V, F = _box_mesh(min(10.0, x1 - xa), 0.15, 0.15)
                parts.append((V + [xa + 0.5 * min(10.0, x1 - xa), side * ROAD, 0.0], F, DW._KERB_COLOR))
            m = _mesh(parts)
            add_flat(w, m["V"], m["F"], 1, m["color"], "kerb")
        for xd in np.arange(x0, x1 - 5.0, 8.0):                             # 中央線(白の破線 5 m・間 3 m)
            V, F = _quad(xd, xd + 5.0, -0.075, 0.075)
            add_flat(w, V, F, 9, DW._LINE_COLOR, "center")
        for ye in (EDGE, -EDGE):                                            # 車道外側線(10 m ごと)
            m = _mesh([(*_quad(xa, min(xa + 10.0, x1), ye - 0.075, ye + 0.075), DW._LINE_COLOR)
                       for xa in np.arange(x0, x1, 10.0)])
            add_flat(w, m["V"], m["F"], 9, m["color"], "edge")
    V, F = DW._grid_plane(X_CROSS[0], X_CROSS[1], -120.0, 120.0, step=2.5)  # 交差道路
    add_flat(w, V, F, 0, DW._ROAD_COLOR, "road")
    for xs in (X_CROSS[0] - 4.2, X_CROSS[1] + 0.2):                         # 横断歩道(主道路を渡る)
        for yy in np.arange(-ROAD + 0.2, ROAD - 0.2, 0.9):
            V, F = _quad(xs, xs + 4.0, yy, yy + 0.45)
            add_flat(w, V, F, 12, (0.93, 0.93, 0.90), "crosswalk")
    for yy in np.arange(ROAD + 0.4, ROAD + 3.0, 0.9):                       # 並行する横断歩道(交差道路を渡る)
        V, F = _quad(X_CROSS[0] + 0.2, X_CROSS[1] - 0.2, yy, yy + 0.45)
        add_flat(w, V, F, 12, (0.93, 0.93, 0.90), "crosswalk_par")
    V, F = _quad(S_LINE - 0.45, S_LINE, 0.05, EDGE)                         # 停止線
    add_flat(w, V, F, 9, DW._LINE_COLOR, "stop_line")
    rng = np.random.default_rng(9)
    for side in (1.0, -1.0):                                                # 建物(手がかりの立体)
        for x in np.arange(-100.0, 470.0, 14.0):
            if X_CROSS[0] - 9 < x < X_CROSS[1] + 9:
                continue
            h = rng.uniform(4.0, 12.0)
            V, F = _box_mesh(10.0, 6.0, h)
            col = tuple(rng.uniform(0.45, 0.80) * np.array([1.0, rng.uniform(0.85, 1.0), rng.uniform(0.75, 0.95)]))
            add_flat(w, V + [x, side * (ROAD + 7.0 + 3.0), 0.0], F, 6, col, "building")
    for sx in (-1.0, 1.0):                                                  # 交差道路の歩道と建物
        xa = X_CROSS[0] - 12.0 if sx < 0 else X_CROSS[1]
        for sy in (-1.0, 1.0):
            V, F = DW._grid_plane(xa, xa + 12.0, ROAD + 12.0, 120.0, step=5.0, z=0.15)
            if sy < 0:
                V[:, 1] *= -1
                F = F[:, ::-1]
            add_flat(w, V, F, 1, (0.70, 0.70, 0.66), "sidewalk")
            for yb in np.arange(ROAD + 18.0, 118.0, 13.0):
                h = rng.uniform(5.0, 14.0)
                V, F = _box_mesh(7.0, 10.0, h)
                col = tuple(rng.uniform(0.45, 0.80) * np.array([1.0, rng.uniform(0.85, 1.0), rng.uniform(0.75, 0.95)]))
                add_flat(w, V + [XC + sx * (5.0 + 3.0 + 3.5), sy * yb, 0.0], F, 6, col, "building")
    ids = {}
    ids["veh_sig"] = DW.add_signal(w, X_FAR + 1.0, ROAD + 0.6, math.pi, state="green")
    # 並行する歩行者の信号(向こうの角、−x を向く): 箱 + 灯火 2 つ(上 = 赤、下 = 青)。灯火は自前の発光(陰影を付けない)
    V, F = _box_mesh(0.12, 0.12, 2.0)
    add_flat(w, V + [X_CROSS[1] + 0.6, ROAD + 1.6, 0.0], F, 6, (0.35, 0.35, 0.35), "ped_pole")
    V, F = _box_mesh(0.30, 0.55, 1.15, 2.0)
    add_flat(w, V + [X_CROSS[1] + 0.6, ROAD + 1.6, 0.0], F, 3, (0.20, 0.20, 0.20), "ped_head")
    xf = X_CROSS[1] + 0.6 - 0.16
    for k, (z0, z1) in (("red", (2.62, 3.08)), ("green", (2.07, 2.53))):
        V = np.array([[xf, ROAD + 1.6 - 0.23, z0], [xf, ROAD + 1.6 + 0.23, z0], [xf, ROAD + 1.6 + 0.23, z1],
                      [xf, ROAD + 1.6 - 0.23, z1]])
        ids["ped_" + k] = add_flat(w, V, np.array([[0, 1, 2], [0, 2, 3]]), 3, (0.1, 0.1, 0.1), "ped_lamp_" + k)
    ids["ped_lamp_xyz"] = {"red": np.array([xf, ROAD + 1.6, 2.85]), "green": np.array([xf, ROAD + 1.6, 2.30])}
    ids["bike"] = add_obj(w, bicycle_mesh(), -900.0, 0.0, 0.0, "bike")
    ids["amb"] = add_obj(w, ambulance_mesh(), -900.0, 20.0, 0.0, "ambulance")
    V, F = _box_mesh(0.30, 1.30, 0.22, 2.5)                                 # 赤色灯(横長の灯具)
    ids["beacon"] = add_obj(w, {"V": V, "F": F, "color": np.tile([0.30, 0.05, 0.05], (len(F), 1)), "label": 16,
                                "dims": (0.3, 1.3, 0.22)}, -900.0, 20.0, 0.0, "beacon")
    ids["bus"] = add_obj(w, bus_mesh(), -900.0, 40.0, 0.0, "bus")
    V, F = _box_mesh(0.10, 0.10, 1.5, 0.3)                                  # 死角の門の柱
    ids["pole"] = add_obj(w, {"V": V, "F": F, "color": np.tile([1.0, 0.4, 0.0], (len(F), 1)), "label": 15,
                              "dims": (0.1, 0.1, 1.8)}, -900.0, 60.0, 0.0, "pole")
    V, F = _box_mesh(0.14, 0.14, 0.14, -0.07)                               # 画素位置の門の目印(中心が原点)
    ids["marker"] = add_obj(w, {"V": V, "F": F, "color": np.tile([1.0, 0.0, 1.0], (len(F), 1)), "label": 17,
                                "dims": (0.14, 0.14, 0.14)}, -900.0, 80.0, 0.0, "marker")
    return w, ids


def move(w, i, x, y, yaw=0.0, z=0.0):
    DW.world_move(w, i, x, y, yaw, z)


def set_color(w, i, col):
    f0, f1 = w["objects"][i]["faces"]
    w["face_color"][f0:f1] = col


GROUND_FAR = np.array([0.60, 0.60, 0.56])


def render(w, pose, K, W, H):
    """world_camera + 地平線より下の空の画素を地面の色で埋める。

    render3d は頂点が 1 つでもカメラの後ろにある三角形を描かない(近い面の切り落としが無い)ので、カメラの真横の
    格子の 1 目が抜けて空が見える。抜けた所(と世界の端の外)は、画素の光線が下を向いていれば地面の色にする
    (物体のラベルは付けない = 門の数え方に影響しない)。"""
    v = DW.world_camera(w, pose, K, W, H)
    bg = v["label"] < 0
    if bg.any():
        rr, cc = np.nonzero(bg)
        d = np.stack([(cc - K[0, 2]) / K[0, 0], -(rr - K[1, 2]) / K[1, 1], -np.ones(len(rr))], 1) @ np.asarray(pose)[:3, :3]
        down = d[:, 2] < 0
        v["color"][rr[down], cc[down]] = GROUND_FAR
    return v


def emissive(w, view, obj_ids, keep=None):
    """発光する物体(灯火・赤色灯)の画素を陰影なしの色に戻す(world_camera は Lambert で暗くするため)。"""
    face = view["face"]
    hit = face >= 0
    fi = np.where(hit, face, 0)
    if keep is not None:
        fi = keep[fi]
    col = view["color"]
    for i in obj_ids:
        f0, f1 = w["objects"][i]["faces"]
        m = hit & (fi >= f0) & (fi < f1)
        col[m] = w["face_color"][fi[m]]
    return col


# ───────────────────────────── 車の姿勢と目・鏡 ─────────────────────────────
def car_frame(cx, cy, hd):
    c, s = math.cos(hd), math.sin(hd)
    return np.array([[c, -s], [s, c]]), np.array([cx, cy])


def to_world(cx, cy, hd, p):
    R, t = car_frame(cx, cy, hd)
    return R @ np.asarray(p, float) + t


def to_car(cx, cy, hd, p):
    R, t = car_frame(cx, cy, hd)
    return (np.asarray(p, float) - t) @ R


EYE_C = np.array([EYE_FWD, -EYE_RIGHT])                  # 車の中心から目(車の座標)


def mirror_specs():
    """車の座標(原点 = 車の中心、x = 前、y = 左)での鏡 3 枚。法線は水平(目と鏡の高さを揃える)。

    ドアミラー(左右): 幅 0.18 m・高さ 0.12 m・凸面 R 1.4 m(drivedecide のテストと同じ例、仮定)。中心の反射光線を
    後ろへ、外へ 4°(左)/ 3°(右)開く。ルームミラー: 幅 0.26 m・高さ 0.07 m の平面鏡、目の前 0.55 m・車の中央。"""
    out = {}
    for side, sy, out_deg in (("left", 1.0, 4.0), ("right", -1.0, 3.0)):
        M = np.array([EYE_FWD + 0.70, sy * (EGO_W / 2 + 0.12)])
        look = np.array([-math.cos(math.radians(out_deg)), sy * math.sin(math.radians(out_deg))])
        n = DD.mirror_aim_normal(EYE_C, M, look)
        out[side] = {"center": M, "normal": n, "width": 0.18, "height": 0.12, "radius": 1.4, "look": look}
    M = np.array([EYE_FWD + 0.55, 0.0])
    look = np.array([-1.0, 0.0])
    out["room"] = {"center": M, "normal": DD.mirror_aim_normal(EYE_C, M, look), "width": 0.26, "height": 0.07,
                   "radius": math.inf, "look": look}
    return out


MIRRORS = mirror_specs()


def door_mirror_geometry(side):
    """drivedecide.mirror_blind_zone の両端の反射光線から、ドアミラー(凸面)の「後ろ向きの仮想カメラ」を作る。

    凸面鏡の両端の反射光線は広がるので、逆へ延ばすと鏡の奥の 1 点 O で交わる。O に置いた針穴カメラの水平の視野を
    両端の光線の挟む角にすると、写る範囲(水平)は鏡で見える範囲(2 本の光線の間 ∩ 鏡の前)と **厳密に同じ**。
    中の写り方(凸面の歪み)は針穴の中心射影で近似する(正直に書くこと)。左ドアミラーは死角の多角形も返す。"""
    m = MIRRORS[side]
    sy = 1.0 if side == "left" else -1.0
    eye = EYE_C
    if side == "left":
        bz = DD.mirror_blind_zone(eye, m["center"], m["normal"], m["width"], mirror_radius=m["radius"],
                                  direct_limit_deg=100.0, roi=(-15.0, 0.9, 1.2, 4.6))
    else:  # 右は y を反転して同じ op で(op は左側の死角の形)
        e2 = eye * [1, -1]
        bz = DD.mirror_blind_zone(e2, m["center"] * [1, -1], m["normal"] * [1, -1], m["width"],
                                  mirror_radius=m["radius"], direct_limit_deg=100.0, roi=(-15.0, 0.9, 1.2, 4.6))
        bz = dict(bz, mirror_edges=bz["mirror_edges"] * [1, -1], mirror_rays=bz["mirror_rays"] * [1, -1],
                  pieces=[p * [1, -1] for p in bz["pieces"]])
    P, r = bz["mirror_edges"], bz["mirror_rays"]
    # P0 + s r0 = P1 + u r1 を解く(s, u < 0 が鏡の奥)
    A = np.column_stack([r[0], -r[1]])
    s, u = np.linalg.solve(A, P[1] - P[0])
    O = P[0] + s * r[0]
    ang = math.acos(float(np.clip(r[0] @ r[1], -1, 1)))
    bis = (r[0] + r[1]) / np.linalg.norm(r[0] + r[1])
    chord = P[1] - P[0]
    cn = np.array([-chord[1], chord[0]])
    if float(cn @ (eye - P[0])) < 0:
        cn = -cn                                                       # 弦の法線を眼の側へ
    return {"bz": bz, "O": O, "hfov": ang, "dir": bis, "edges": P, "rays": r, "chord_n": cn, "chord_p": P[0],
            "behind": (s < 0 and u < 0), "side": sy}


DOOR = {"left": door_mirror_geometry("left"), "right": door_mirror_geometry("right")}


def in_convex(poly, p, eps=0.0):
    """点 p が凸多角形 poly(反時計回りでも時計回りでも)の内側か(境界から eps 内側)。"""
    n = len(poly)
    sgn = 0.0
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        c = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L < 1e-12:
            continue
        c /= L
        if sgn == 0.0 and abs(c) > 1e-12:
            sgn = math.copysign(1.0, c)
        if sgn != 0.0 and c * sgn < eps:
            return False
    return True


def door_sees(side, p_car, margin=0.0):
    """2D: 車の座標の点が凸面ドアミラーで見えるか(両端の反射光線の間 ∩ 弦の眼の側)。margin > 0 なら境界から内側だけ。"""
    g = DOOR[side]
    P, r = g["edges"], g["rays"]
    q = np.asarray(p_car, float)
    T_in = P.mean(axis=0) + r[0] + r[1]
    for k in range(2):
        gk = np.array([-r[k, 1], r[k, 0]])
        sd = 1.0 if gk @ (T_in - P[k]) >= 0 else -1.0
        if sd * (gk @ (q - P[k])) < margin:
            return False
    return float(g["chord_n"] @ (q - g["chord_p"])) / float(np.linalg.norm(g["chord_n"])) >= margin


def direct_sees(p_car, limit_deg=100.0):
    """2D: 首を回さずに直接見えるか(目から見た方位 ≤ 上限。左右対称)。"""
    d = np.asarray(p_car, float) - EYE_C
    return abs(math.degrees(math.atan2(d[1], d[0]))) <= limit_deg


def _cull_faces(w, keep_fn):
    """鏡の向こう側(仮想カメラと鏡の間)の面を落とした世界の浅い写し。返り値: (world, keep の索引)。"""
    F = w["F"]
    cen = w["V"][F].mean(axis=1)
    keep = np.flatnonzero(keep_fn(cen))
    return {"V": w["V"], "F": F[keep], "face_color": w["face_color"][keep], "face_label": w["face_label"][keep]}, keep


def mirror_view(w, ego, side, W, H, emissive_ids=()):
    """鏡に映る像(運転者が見る向き = 左右は鏡のとおり)を描く。ego = (cx, cy, heading)。

    room(平面): 実カメラ(目 → 鏡の中心)の姿勢 P と鏡の平面から drivedecide.mirror_virtual_camera の仮想カメラ F·P·S で
    撮って左右を反転(u' = 2c_x − u)。door(凸面): door_mirror_geometry の点 O の後ろ向きの針穴で撮って左右を反転。
    どちらも鏡の向こう側の面を先に落とす(z-buffer に近い平面の切り落としが無いため)。"""
    cx, cy, hd = ego
    eye3 = np.r_[to_world(cx, cy, hd, EYE_C), EYE_Z]
    if side == "room":
        m = MIRRORS["room"]
        Mw = np.r_[to_world(cx, cy, hd, m["center"]), EYE_Z]          # 目と同じ高さ(法線が水平 = 地平線が傾かない)
        nw = DD.mirror_aim_normal(eye3, Mw, np.r_[car_frame(cx, cy, hd)[0] @ m["look"], 0.0])
        plane = np.r_[nw, nw @ Mw]
        P = DW.camera_pose(eye3, Mw)
        hf = 2 * math.atan(m["width"] / 2 / np.linalg.norm(Mw - eye3))
        K = DW.camera_intrinsics(math.degrees(2 * math.atan(math.tan(hf / 2) * H / W)), W, H)
        vc = DD.mirror_virtual_camera(P, plane)
        wc, keep = _cull_faces(w, lambda c: c @ nw > plane[3] + 1e-6)
        view = render(wc, vc["pose"], K, W, H)
        info = {"P": P, "K": K, "plane": plane, "vc": vc, "eye": eye3}
    else:
        g = DOOR[side]
        R, t = car_frame(cx, cy, hd)
        O = np.r_[R @ g["O"] + t, EYE_Z]
        dirw = np.r_[R @ g["dir"], 0.0]
        P = DW.camera_pose(O, O + dirw)
        vf = math.degrees(2 * math.atan(math.tan(g["hfov"] / 2) * H / W))
        K = DW.camera_intrinsics(vf, W, H)
        cn = R @ g["chord_n"]
        cp = R @ g["chord_p"] + t
        wc, keep = _cull_faces(w, lambda c: (c[:, :2] - cp) @ cn > 1e-6)
        view = render(wc, P, K, W, H)
        info = {"P": P, "K": K, "O": O}
    if emissive_ids:
        emissive(w, view, emissive_ids, keep)
    for k in ("color", "label", "depth", "face"):
        view[k] = view[k][:, ::-1].copy()                   # 鏡像に(左右反転)
    view["face"] = np.where(view["face"] >= 0, keep[np.maximum(view["face"], 0)], -1)
    view["info"] = info
    return view


def dash_pose(ego, pitch=-0.03):
    cx, cy, hd = ego
    e = np.r_[to_world(cx, cy, hd, EYE_C), 1.25]
    return DW.camera_pose(e, e + np.array([math.cos(hd), math.sin(hd), pitch]))


DASH_K = DW.camera_intrinsics(CAM_VFOV, CAM_W, CAM_H)


# ───────────────────────────── 1. ミラー ─────────────────────────────
def fermat_mirror_point(C, Q, plane, M0):
    """平面鏡で C から Q が見える鏡面上の点 M を、道のり |CM| + |MQ| の最小(Fermat)として Newton で解く。

    折り返しの式 S(Q) を使わない独立な経路(drivedecide の閉形式の門の相手)。"""
    n = plane[:3] / np.linalg.norm(plane[:3])
    d0 = plane[3] / np.linalg.norm(plane[:3])
    e1 = np.cross(n, [0.0, 0.0, 1.0])
    if np.linalg.norm(e1) < 1e-9:
        e1 = np.cross(n, [1.0, 0.0, 0.0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(n, e1)
    M0 = M0 - (n @ M0 - d0) * n

    def grad(a):
        M = M0 + a[0] * e1 + a[1] * e2
        g = (M - C) / np.linalg.norm(M - C) + (M - Q) / np.linalg.norm(M - Q)
        return np.array([g @ e1, g @ e2])
    a = np.zeros(2)
    for _ in range(60):
        g = grad(a)
        h = 1e-6
        Hm = np.column_stack([(grad(a + h * np.eye(2)[k]) - grad(a - h * np.eye(2)[k])) / (2 * h) for k in range(2)])
        step = np.linalg.solve(Hm, g)
        a = a - step
        if np.linalg.norm(step) < 1e-14:
            break
    return M0 + a[0] * e1 + a[1] * e2


def scene_mirrors(w, ids):
    print("== 1. ミラー: ルームミラー(平面)とドアミラー(凸面)を仮想カメラで描き、鏡像の位置と死角を確かめる")
    m = MIRRORS["room"]
    dl = float(np.linalg.norm(MIRRORS["left"]["center"] - EYE_C))
    fov_c = DD.convex_mirror_fov(1.4, 0.18, dl)
    print("  ルームミラー 幅 %.2f m(平面)・ドアミラー 幅 %.2f m・凸面 R %.1f m(仮定)。左ドアミラーの水平の視野 %.1f°"
          "(同じ幅の平面鏡 %.1f°、軸上の目の閉形式。斜めに見る実際の置き方では両端の光線の角 %.1f°)" % (
              m["width"], MIRRORS["left"]["width"], MIRRORS["left"]["radius"], fov_c["fov_deg"],
              math.degrees(fov_c["flat_fov_rad"]), math.degrees(DOOR["left"]["hfov"])))
    # (a) 鏡像の画素位置: 描いた絵の目印の重心 = Fermat の光線追跡の画素
    Wm, Hm = 520, 140
    errs, errs_cf, errs_noflip = [], [], []
    for ego in ((150.0, Y_LANE, 0.0), (90.0, 2.4, 0.25)):
        cx, cy, hd = ego
        for dx, dy, z in ((-8.0, 0.5, 1.1), (-12.0, -1.2, 1.3), (-15.0, 2.2, 0.9), (-22.0, -2.0, 1.6), (-30.0, 0.0, 1.2),
                          (-10.0, 1.5, 1.4)):
            Q = np.r_[to_world(cx, cy, hd, np.array([dx, dy])), z]
            move(w, ids["marker"], Q[0], Q[1], 0.0, Q[2])
            v = mirror_view(w, ego, "room", Wm, Hm)
            msk = v["label"] == 17
            if msk.sum() < 4:
                continue
            rr, cc = np.nonzero(msk)
            info = v["info"]
            M = fermat_mirror_point(info["eye"], Q, info["plane"], np.r_[to_world(cx, cy, hd, m["center"]), EYE_Z])
            col, row, _ = DW.world_project_points(M[None, :], info["P"], info["K"])
            S = info["vc"]["reflection"]
            col2, row2, _ = DW.world_project_points((S[:3, :3] @ Q + S[:3, 3])[None, :], info["P"], info["K"])
            errs.append(math.hypot(cc.mean() - col[0], rr.mean() - row[0]))
            errs_cf.append(math.hypot(col2[0] - col[0], row2[0] - row[0]))
            errs_noflip.append(math.hypot((Wm - 1 - cc.mean()) - col[0], rr.mean() - row[0]))
    move(w, ids["marker"], -900.0, 80.0)
    print("  目印 %d 点(後方 8〜30 m、自車の向き 0 と 0.25 rad): 描いた鏡像の重心 − Fermat の光線追跡の画素 最大 %.2f px"
          "(%d × %d)/ 折り返しの式 P·S(Q) − Fermat 最大 %.1e px" % (len(errs), max(errs), Wm, Hm, max(errs_cf)))
    gate("鏡像の画素位置: 仮想カメラ F·P·S で描いて左右反転した目印の重心 = 鏡面上の Fermat の点の画素(≤ 1 px。"
         "重心と中心の射影の差・画素の量子化を含む)、折り返しの式 P·S(Q) = Fermat(≤ 1e-6 px)",
         len(errs) >= 10 and max(errs) <= 1.0 and max(errs_cf) <= 1e-6, "%d 点、最大 %.2f px" % (len(errs), max(errs)))
    gate("門が自明でない: 左右反転(u' = 2c_x − u)を外すと鏡像の位置がずれる(中央の列から離れた目印ほど 2|u − c_x|)",
         float(np.median(errs_noflip)) > 20.0, "中央値 %.0f px、最大 %.0f px" % (np.median(errs_noflip), max(errs_noflip)))

    # (b) 死角: 左ドアミラーの死角の多角形 = 柱を格子に立てて描いた絵(鏡に写るか)
    g = DOOR["left"]
    bz = g["bz"]
    ego = (150.0, Y_LANE, 0.0)
    xs = np.arange(-14.5, 0.75, 0.5)
    ys = np.arange(1.45, 4.5, 0.3)
    n_chk = n_skip = n_dir = 0
    bad = []
    grid = []
    for gx in xs:
        for gy in ys:
            p = np.array([gx, gy])
            if direct_sees(p):
                n_dir += 1
                grid.append((gx, gy, "direct"))
                continue
            inside = any(in_convex(pc, p) for pc in bz["pieces"])
            near = (not door_sees("left", p, margin=0.15)) and door_sees("left", p, margin=-0.15)
            if near:
                n_skip += 1
                grid.append((gx, gy, "edge"))
                continue
            Pw = to_world(*ego, p)
            move(w, ids["pole"], Pw[0], Pw[1])
            v = mirror_view(w, ego, "left", 200, 100)
            seen = bool((v["label"] == 15).sum() >= 1)
            n_chk += 1
            grid.append((gx, gy, "mirror" if seen else "blind"))
            if seen == inside or door_sees("left", p) == inside:
                bad.append((gx, gy, seen, inside))
    move(w, ids["pole"], -900.0, 60.0)
    flat = DD.mirror_blind_zone(EYE_C, MIRRORS["left"]["center"], MIRRORS["left"]["normal"], 0.18, mirror_radius=math.inf,
                                direct_limit_deg=100.0, roi=(-15.0, 0.9, 1.2, 4.6))
    print("  左後方 %.1f m²(車の中心から左 1.2〜4.6 m・前後 −15〜+0.9 m): 死角 %.1f m²(凸面)/ %.1f m²(同じ幅の平面鏡)。"
          "格子 %d 点を描いて確かめ、%d 点は鏡の視野の縁 ±0.15 m で除外、%d 点は直接見える" % (
              bz["roi_area"], bz["area"], flat["area"], n_chk, n_skip, n_dir))
    gate("死角の多角形(mirror_blind_zone)= 柱を格子に立てて凸面ドアミラーの仮想カメラで描いた絵(写る ⇔ 多角形の外)",
         not bad and n_chk >= 100, "%d 点で不一致 %d" % (n_chk, len(bad)) + (" 例 %r" % (bad[:3],) if bad else ""))
    return {"errs": errs, "grid": grid, "bz": bz, "flat": flat, "n_chk": n_chk}


# ───────────────────────────── 1c. 左折の巻き込み(試行) ─────────────────────────────
def obb(cx, cy, hd, L, Wd):
    c, s = math.cos(hd), math.sin(hd)
    R = np.array([[c, -s], [s, c]])
    return (R @ np.array([[L / 2, Wd / 2], [-L / 2, Wd / 2], [-L / 2, -Wd / 2], [L / 2, -Wd / 2]]).T).T + [cx, cy]


def _seg_dist(p, a, b):
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-12), 0.0, 1.0)
    return np.linalg.norm(p - (a + t[..., None] * ab), axis=-1)


def poly_dist(A, B):
    """凸多角形どうしの距離(重なれば 0)。分離軸で重なりを判定し、離れていれば角と辺の距離の最小。"""
    sep = False
    for P_, Q_ in ((A, B), (B, A)):
        for i in range(len(P_)):
            e = P_[(i + 1) % len(P_)] - P_[i]
            nrm = np.array([e[1], -e[0]])
            a = P_ @ nrm
            b = Q_ @ nrm
            if a.max() < b.min() or b.max() < a.min():
                sep = True
                break
        if sep:
            break
    if not sep:
        return 0.0
    d1 = min(_seg_dist(B, A[i], A[(i + 1) % len(A)]).min() for i in range(len(A)))
    d2 = min(_seg_dist(A, B[i], B[(i + 1) % len(B)]).min() for i in range(len(B)))
    return float(min(d1, d2))


def ego_turn_pose(s_arc):
    """左折の弧の上の車の中心の姿勢(弧の長さ s_arc ≥ 0)。弧の中心 (X_T, Y_LANE + R)。曲がり終えたら +y へまっすぐ。"""
    phi = min(s_arc / R_TURN, math.pi / 2)
    x = X_T + R_TURN * math.sin(phi)
    y = Y_LANE + R_TURN * (1 - math.cos(phi))
    if s_arc > R_TURN * math.pi / 2:
        y += s_arc - R_TURN * math.pi / 2
    return x, y, phi


def left_turn_run(bike_x0, bike_v, use_mirror, dt=0.02, record=False):
    """左折の 1 試行(2D)。

    自車: 中心 X_T − 45 m から 30 km/h、前端が左折の地点の 30 m 手前で合図(その 1 s 前にミラー)、25 m 手前から
    減速して左折の地点で 3 m/s、半径 5 m の弧を回る。use_mirror = True: 左ドアミラー + 直接の視界で 0.25 s ごとに
    左後方を確かめて自転車を追う / False: 直接の視界だけ(左後方を見落とす設定)。左折の地点の 6 m 手前で、追っている
    自転車が交差の帯に入るなら手前で止まり、自転車が帯を出てから曲がる。"""
    s_turn = X_T + EGO_L / 2                       # 左折の地点(前端)
    x, v, t = X_T - 45.0, V_CRUISE, 0.0
    s_arc = None
    mode = "cruise"
    ev = []
    track = []
    wait = waited = False
    decided = False
    dmin = math.inf
    rec = []
    t_mirror = t_sig = t_start = t_end = None
    s_sig = None
    a_dec = (V_CRUISE ** 2 - V_TURN ** 2) / (2 * 25.0)
    next_chk = 0.0
    while t < 40.0:
        bx = bike_x0 + bike_v * t
        if s_arc is None:
            cx, cy, hd = x, Y_LANE, 0.0
        else:
            cx, cy, hd = ego_turn_pose(s_arc)
        front = cx + EGO_L / 2
        if t_mirror is None and front >= s_turn - 30.0 - V_CRUISE * 1.0:
            t_mirror, mode = t, "mirror"
            ev.append({"t": t, "kind": "mirror"})
        if t_sig is None and s_arc is None and front >= s_turn - 30.0:
            t_sig, s_sig, mode = t, front, "signal"
            ev.append({"t": t, "kind": "signal_on", "s": front})
        if t_mirror is not None and s_arc is None and t >= next_chk - 1e-9:
            next_chk = t + 0.25
            pb = to_car(cx, cy, hd, (bx, Y_BIKE))
            if direct_sees(pb) or (use_mirror and door_sees("left", pb)):
                track.append((t, bx))
        if not decided and s_arc is None and cx >= X_T - 6.0:
            decided = True
            if track:
                tk, xk = track[-1]
                vb = (track[-1][1] - track[-2][1]) / (track[-1][0] - track[-2][0]) if len(track) >= 2 else 7.0
                xb_now = xk + vb * (t - tk)
                t_cross = 6.0 / V_TURN + 3.0                       # 自車が交差の帯を抜けるまでの見積り + 余裕
                wait = xb_now - 0.9 < X_T + 7.0 and xb_now + 0.9 + vb * t_cross > X_T - 3.0
        if wait and bx - 0.9 > X_T + 7.0:
            wait = False                                           # 自転車の後端が交差の帯を出た
        if s_arc is None:
            if wait:
                waited = True
                mode = "wait_bike"
                if v > 0:
                    a = v * v / (2 * max(X_T - 0.3 - x, 0.05))
                    v = max(0.0, v - a * dt)
                x = min(x + v * dt, X_T - 0.3)
            else:
                if front >= s_turn - 25.0:
                    v = max(V_TURN, v - a_dec * dt) if v > V_TURN else min(V_TURN, v + 1.5 * dt)
                    if mode in ("signal", "mirror", "cruise"):
                        mode = "slow"
                    if mode == "wait_bike":
                        mode = "slow"
                x += v * dt
                if x >= X_T:
                    s_arc = x - X_T
                    t_start, mode = t, "turn"
                    ev.append({"t": t, "kind": "start", "s": s_turn})
        else:
            v = min(V_TURN, v + 1.5 * dt)
            s_arc += v * dt
            if t_end is None and s_arc >= R_TURN * math.pi / 2:
                t_end, mode = t, "after"
                ev.append({"t": t, "kind": "end"})
                ev.append({"t": t + 0.5, "kind": "signal_off"})
        if abs(bx - cx) < 12:
            dmin = min(dmin, poly_dist(obb(cx, cy, hd, EGO_L, EGO_W), obb(bx, Y_BIKE, 0.0, 1.8, 0.6)))
        if record:
            pb = to_car(cx, cy, hd, (bx, Y_BIKE))
            rec.append({"t": t, "ego": (cx, cy, hd), "v": v, "bx": bx, "mode": mode,
                        "in_mirror": bool(door_sees("left", pb)), "direct": bool(direct_sees(pb))})
        t += dt
        if t_end is not None and t > t_end + 1.5:
            break
    return {"dmin": dmin, "waited": waited, "events": ev, "rec": rec, "t_sig": t_sig, "s_sig": s_sig, "t_start": t_start,
            "t_end": t_end, "seen": bool(track)}


def scene_left_turn():
    print("== 1c. 左折の前に左後方の自転車をミラーで見つける(巻き込み)")
    rng = np.random.default_rng(30)
    x0 = rng.uniform(X_T - 75.0, X_T - 48.0, N_BIKE)
    vb = rng.uniform(4.0, 7.0, N_BIKE)
    res, wt = {}, {}
    for use in (True, False):
        rr = [left_turn_run(a, b, use) for a, b in zip(x0, vb)]
        res[use] = np.array([r["dmin"] for r in rr])
        wt[use] = int(sum(r["waited"] for r in rr))
    hit_m, hit_n = int(np.sum(res[True] < 0.3)), int(np.sum(res[False] < 0.3))
    print("  %d 試行(自転車: 自車の中心の 3〜30 m 後ろから 4〜7 m/s、路側帯 y = %.1f m): 最小距離 < 0.3 m(巻き込み)"
          " ミラーで確かめる %d 試行(待った %d)/ 直接の視界だけ %d 試行(待った %d)。全試行の最小距離 %.2f m / %.2f m" % (
              N_BIKE, Y_BIKE, hit_m, wt[True], hit_n, wt[False], res[True].min(), res[False].min()))
    gate("左折: 左ドアミラーで左後方を確かめて自転車を追うと、全試行で巻き込まない(自転車との距離 ≥ 0.3 m)", hit_m == 0,
         "最小 %.2f m" % res[True].min())
    gate("門が自明でない: ミラーを見ない(直接の視界だけ)と巻き込む試行が出る", hit_n > 0, "%d / %d 試行" % (hit_n, N_BIKE))
    demo = left_turn_run(X_T - 51.0, 6.0, True, dt=1.0 / CAM_FPS, record=True)
    demo_n = left_turn_run(X_T - 51.0, 6.0, False, dt=1.0 / CAM_FPS, record=True)
    print("  展示の 1 本: ミラーあり → 自転車を待つ %s、最小距離 %.2f m / なし → 最小距離 %.2f m" % (
        demo["waited"], demo["dmin"], demo_n["dmin"]))
    return {"d": res, "demo": demo, "demo_n": demo_n, "hit_n": hit_n, "hit_m": hit_m, "wait": wt}


# ───────────────────────────── 2. 確認の順序 ─────────────────────────────
EXPECT_DED = {"safety": 10, "signal": 5}           # 丁運発第44号: 安全不確認 10 点、合図不履行等 5 点(PoC 側に書き写した値)


def lane_change_events(t0=0.0, mirror_before=0.6, lead=3.3, dur=3.0, cancel=0.4):
    return [{"t": t0, "kind": "mirror"}, {"t": t0 + mirror_before, "kind": "signal_on"},
            {"t": t0 + mirror_before + lead, "kind": "start"}, {"t": t0 + mirror_before + lead + dur, "kind": "end"},
            {"t": t0 + mirror_before + lead + dur + cancel, "kind": "signal_off"}]


def scene_sequence(LT):
    print("== 2. 確認の順序: ミラー → 合図(約 3 s 前 / 30 m 手前)→ 進路変更 → 合図をやめる(丁運発第44号の減点)")
    ev = LT["demo"]["events"]
    r_turn = DD.check_sequence_score(ev, maneuver="left_turn")
    r_lane = DD.check_sequence_score(lane_change_events(), maneuver="lane_change")
    print("  自車の左折(展示の 1 本): ミラー t = %.2f s → 合図 t = %.2f s(前端が左折の地点の %.1f m 手前)→ 左折 t = %.2f〜%.2f s → "
          "0.5 s 後に合図をやめる → 減点 %d(%d 点)" % (ev[0]["t"], LT["demo"]["t_sig"], r_turn["distance"], LT["demo"]["t_start"],
                                              LT["demo"]["t_end"], r_turn["deduction"], r_turn["score"]))
    print("  自車の車線変更: ミラー → 0.6 s → 合図 → %.1f s → 進路変更 3 s → 0.4 s で合図をやめる → 減点 %d" % (
        r_lane["lead"], r_lane["deduction"]))
    gate("確認の順序: 自車の左折と車線変更は check_sequence_score の減点 0(100 点)", r_turn["deduction"] == 0 and r_lane["deduction"] == 0,
         "%d / %d 点" % (r_turn["score"], r_lane["score"]))
    t_st = LT["demo"]["t_start"]
    bad = {
        "合図の後にミラー(車線変更)": ([dict(e, t=e["t"] + (1.0 if e["kind"] == "mirror" else 0.0)) for e in lane_change_events()],
                              "lane_change", EXPECT_DED["safety"]),
        "ミラーを見ない(車線変更)": ([e for e in lane_change_events() if e["kind"] != "mirror"], "lane_change", EXPECT_DED["safety"]),
        "合図が 1.5 s 前(車線変更)": (lane_change_events(lead=1.5), "lane_change", EXPECT_DED["signal"]),
        "合図が 15 m 手前(左折)": ([dict(e, s=e["s"] + 15.0) if e["kind"] == "signal_on" else e for e in ev], "left_turn",
                             EXPECT_DED["signal"]),
        "左折の途中で合図をやめる": ([dict(e, t=t_st + 0.5) if e["kind"] == "signal_off" else e for e in ev], "left_turn",
                           EXPECT_DED["signal"]),
        "左折の後も合図を出したまま": ([e for e in ev if e["kind"] != "signal_off"], "left_turn", EXPECT_DED["signal"]),
    }
    rows = []
    okb = True
    for k, (evs, man, want) in bad.items():
        r = DD.check_sequence_score(evs, maneuver=man)
        det = "、".join(v["detail"] for v in r["violations"])
        rows.append((k, r["deduction"], want, det))
        okb &= r["deduction"] == want
        print("    %s: 減点 %d(期待 %d) — %s" % (k, r["deduction"], want, det))
    gate("門が自明でない: 順序・時期・継続を崩した 6 版は、それぞれ丁運発第44号の点数(安全不確認 10 / 合図不履行等 5)だけ減点される",
         okb, "%d 版" % len(bad))
    return {"turn": r_turn, "lane": r_lane, "rows": rows}


# ───────────────────────────── 3. 信号の予測とジレンマゾーン ─────────────────────────────
PLAN = DD.signal_phase_plan(**SIG)
T_ON = 0.5 / PED_FLASH_HZ           # 青点滅の「点いている」長さ(仮定: 1 Hz・デューティ 50 %、点いている側から始まる)


def ped_lamps(t):
    """時刻 t(時間割の時刻)の歩行者信号の灯火 (青が点いているか, 赤が点いているか)。真値。"""
    st = DD.signal_state(PLAN, "ped_A", np.atleast_1d(t))
    tt = np.mod(np.atleast_1d(t), PLAN["cycle"])
    ph = np.mod(tt - PLAN["ped_flash_start"], 1.0 / PED_FLASH_HZ)
    g = (st == "green") | ((st == "flash") & (ph < T_ON))
    return g, st == "red"


class PedReader:
    """歩行者信号の灯火の点灯の時系列から、状態の観測を作り車両の黄までを予測する(古典的: 明るさの時系列だけ)。

    青が点いたままの間は「青」、初めて消えた時刻 t₁ に「青点滅」と分かる。点滅は点いている側から始まりうるので、
    消える直前の T_ON + 1 コマの青の観測は点滅だったかもしれない —— 確かな最後の青は t₁ − T_ON − dt とする(仮定:
    点滅の周期は知っている)。赤が点けば点滅 → 赤の切り替わり。観測は drivedecide.predict_amber_onset に渡す。"""

    def __init__(self, dt):
        self.dt = dt
        self.obs = []
        self.state = "green"
        self.t_first_off = None
        self.pred = None

    def step(self, t, g_on, r_on):
        n_trans = self._transitions()
        if r_on:
            if self.state != "red":
                self.state = "red"
            self.obs.append((t, "red"))
        elif g_on and self.state == "green":
            self.obs.append((t, "green"))
        else:                                       # 消えている(点滅の消えた側)か、点滅の点いた側
            if self.state == "green":
                self.state = "flash"
                self.t_first_off = t
                cut = t - T_ON - self.dt
                self.obs = [o for o in self.obs if o[0] <= cut + 1e-9]
                if not self.obs or self.obs[-1][0] < cut - 1e-9:
                    self.obs.append((cut, "green"))
            self.obs.append((t, "flash"))
        if self.state in ("flash", "red") and (self.pred is None or self._transitions() != n_trans):
            # 予測は切り替わりの観測でしか変わらない(区間の積)ので、切り替わりの時だけ解き直す
            self.pred = DD.predict_amber_onset(self.obs, crossing_length=SIG["crossing_length"],
                                               ped_red_to_amber=SIG["ped_red_to_amber"], t_now=t)
        elif self.pred is not None:
            self.pred = dict(self.pred, remaining=self.pred["amber_onset"] - t)
        return self.pred

    def _transitions(self):
        return (self.state, self.t_first_off)


def dilemma_now(v, braking, reading):
    """その車の今の速さ v とブレーキの状態でのジレンマゾーン (lo, hi) か None。減速中は反応 0(もう踏んでいる)。"""
    return DD.dilemma_zone(v, **dict(reading, reaction=0.0 if braking else reading["reaction"]))["dilemma"]


def in_dilemma(d, v, braking, reading):
    """黄の始まりの瞬間に「止まれず抜けられない」か。d = 停止線までの距離、braking = もう減速している(反応 0)。"""
    z = dilemma_now(v, braking, reading)
    return z is not None and z[0] < d < z[1]


def signal_run(d_flash, use_pred, fps, phase=0.0, frames=None):
    """信号の場面の 1 本: 歩行者の青点滅の始まりに自車が停止線の d_flash 手前にいる(50 km/h)。

    use_pred = True: 歩行者信号を読み、黄の最も早い時刻 lo に一定速度で GHM の「抜けられる」(x ≤ x_0)に入らないなら
    停止線で止まる計画(2 m/s² で、x ≤ v²/(2·2) から減速)/ False: 黄を見るまで一定速度(黄を見たら GHM で判断)。
    frames = (g, r) の点灯の列(画像から読んだもの)を渡せば、その値で読む(無ければ真値の点灯)。"""
    dt = 1.0 / fps
    tg = PLAN["ped_flash_start"]
    t = tg - 3.0 + phase * dt
    d = d_flash + V_SIG * 3.0 - V_SIG * phase * dt
    v = V_SIG
    rd = PedReader(dt)
    plan = None
    braking = False
    ta = PLAN["amber_onset"]
    at_amber = None
    rec = []
    k = 0
    while t < ta + (8.0 if frames is None else 1e9):
        if frames is not None:
            g_on, r_on = frames[k]
        else:
            g, r = ped_lamps(t)
            g_on, r_on = bool(g[0]), bool(r[0])
        pred = rd.step(t, g_on, r_on) if use_pred else None
        if use_pred and pred is not None and plan is None:
            x0 = DD.dilemma_zone(v, **GHM)["x_clear_max"]
            d_lo = d - v * (pred["lo"] - t)
            plan = "go" if d_lo <= x0 else "stop"
        if plan == "stop" and not braking and d <= v * v / (2 * A_GENTLE) + 0.05:
            braking = True
        if at_amber is None and t >= ta:
            at_amber = (d, v, braking)
            if not use_pred:                                        # 黄を見て GHM で判断(反応 1 s 後に 3 m/s²)
                z = DD.dilemma_zone(v, **GHM)
                plan = "stop" if d >= z["x_stop_min"] else "go"
        if braking and v > 0:
            a = min(3.0, v * v / (2 * max(d, 0.05)))
            v = max(0.0, v - a * dt)
        elif plan == "stop" and not use_pred and at_amber is not None and t >= ta + GHM["reaction"] and v > 0:
            v = max(0.0, v - 3.0 * dt)
        d -= v * dt
        rec.append((t, d, v, plan, braking, pred))
        t += dt
        k += 1
        if frames is not None and k >= len(frames):
            break
    return {"at_amber": at_amber, "rec": rec, "reader": rd}


def ped_crop_camera(eye_pose, lamp_xyz, half=24):
    """車載カメラ(DASH_K)の、灯火のまわり (2·half)² 画素だけを描く針穴(主点をずらす = 全体の絵の切り抜きと同じ)。"""
    col, row, dep = DW.world_project_points(lamp_xyz[None, :], eye_pose, DASH_K)
    c0, r0 = int(round(col[0])) - half, int(round(row[0])) - half
    K = DASH_K.copy()
    K[0, 2] -= c0
    K[1, 2] -= r0
    return K, (c0, r0), (col[0] - c0, row[0] - r0), dep[0]


def scene_signal(w, ids, want_frames):
    print("== 3. 信号の予測: 並行する歩行者信号の青点滅を車載カメラの画素から読み、車両の黄までの残りを推定する")
    F = PLAN["ped_flash_duration"]
    print("  時間割: 歩行者の青 %.0f s → 青点滅 F = 横断 %.0f m / 歩行速度 %.1f m/s = %.0f s → 赤、Δ = %.0f s 後に車両の黄 %.0f s(真値 t = %.0f s)"
          % (PLAN["ped_flash_start"], SIG["crossing_length"], DD.WALK_SPEED_SIGNAL, F, PLAN["ped_red_to_amber"], PLAN["amber"],
             PLAN["amber_onset"]))
    dt = 1.0 / CAM_FPS
    D_DEMO = 200.0
    # (a) 画像から読む 1 本(停止線の 200 m 手前で青点滅が始まる)。予測ありの自車の動きで撮る
    base = signal_run(D_DEMO, True, CAM_FPS)
    lamp = ids["ped_lamp_xyz"]
    crops, series_g, series_r, read, rois = [], [], [], [], []
    truth_g, truth_r = [], []
    for (t, d, v, plan, braking, pred) in base["rec"]:
        g, r = ped_lamps(t)
        truth_g.append(bool(g[0]))
        truth_r.append(bool(r[0]))
        set_color(w, ids["ped_green"], (0.10, 0.95, 0.55) if g[0] else (0.08, 0.12, 0.10))
        set_color(w, ids["ped_red"], (1.0, 0.15, 0.10) if r[0] else (0.12, 0.08, 0.08))
        x_ego = S_LINE - d - EGO_L / 2
        Pd = dash_pose((x_ego, Y_LANE, 0.0))
        mid = 0.5 * (lamp["red"] + lamp["green"])
        K, (c0, r0), _, _ = ped_crop_camera(Pd, mid)
        v_ = render(w, Pd, K, 48, 48)
        emissive(w, v_, (ids["ped_green"], ids["ped_red"]))
        img = v_["color"]
        vals = []
        rois.append([])
        for kk in ("green", "red"):
            col, row, _ = DW.world_project_points(lamp[kk][None, :], Pd, K)
            rc, cc = int(round(row[0])), int(round(col[0]))
            rois[-1].append((rc, cc))
            roi = img[max(0, rc - 2):rc + 3, max(0, cc - 2):cc + 3]
            vals.append(float((roi[..., 1] - roi[..., 0]).max()) if kk == "green" else float((roi[..., 0] - roi[..., 1]).max()))
        series_g.append(vals[0])
        series_r.append(vals[1])
        read.append((vals[0] > 0.4, vals[1] > 0.4))
        if want_frames:
            crops.append(img.copy())
    read = np.array(read)
    acc = float(np.mean((read[:, 0] == np.array(truth_g)) & (read[:, 1] == np.array(truth_r))))
    img_run = signal_run(D_DEMO, True, CAM_FPS, frames=[tuple(x) for x in read])
    preds = [(r[0], r[5]) for r in img_run["rec"] if r[5] is not None]
    ta = PLAN["amber_onset"]
    inside = all(p["lo"] - 1e-9 <= ta <= p["hi"] + 1e-9 for _, p in preds)
    hw_flash = max(p["half_width"] for _, p in preds if p["basis"] == ["green->flash"])
    hw_red = [p["half_width"] for _, p in preds if "flash->red" in p["basis"]]
    t1 = img_run["reader"].t_first_off
    first = preds[0][1]
    gs = np.array(series_g)
    tt = np.array([r[0] for r in base["rec"]])
    fl = (tt >= PLAN["ped_flash_start"] + 0.0) & (tt < PLAN["ped_red_onset"])
    ff = DD.flash_frequency(gs[fl], CAM_FPS)
    lamp_px = 0.46 * DASH_K[0, 0] / (D_DEMO + (lamp["green"][0] - S_LINE))
    print("  画像(車載 %d × %d、%.0f fps、灯火のまわり 48 × 48 を同じ焦点距離で描く): 灯火 0.46 m が停止線の %.0f m 手前で %.1f px。"
          "点灯の読み取りの一致 %.1f %%(%d コマ)" % (CAM_W, CAM_H, CAM_FPS, D_DEMO, lamp_px, 100 * acc, len(read)))
    print("  青が初めて消えたコマ t = %.3f s(点滅の始まりの真値 %.1f s)→ 黄の予測 %.3f s(区間 %.3f〜%.3f、半幅 %.3f s)、真値 %.1f s。"
          "赤を見た後の半幅 %.3f s。点滅の周波数(画素の時系列)%.3f Hz(真値 %.1f Hz)" % (
              t1, PLAN["ped_flash_start"], first["amber_onset"], first["lo"], first["hi"], first["half_width"], ta,
              min(hw_red) if hw_red else float("nan"), ff["frequency"], PED_FLASH_HZ))
    gate("信号の読み取り: 灯火の点灯を画素から読んだ値 = 描いた時刻の真値(全コマ)、点滅の周波数 = %.1f Hz(±0.02 Hz)" % PED_FLASH_HZ,
         acc == 1.0 and abs(ff["frequency"] - PED_FLASH_HZ) <= 0.02, "一致 %.1f %%、%.3f Hz" % (100 * acc, ff["frequency"]))
    gate("黄の予測: 画像から読んだ観測の予測区間は全コマで真値を含み、半幅 ≤ (点灯の長さ + 1 コマ)/2(点滅中)・≤ 1 コマ/2(赤の後)",
         inside and hw_flash <= (T_ON + dt) / 2 + 1e-9 and (not hw_red or max(hw_red) <= dt / 2 + 1e-9),
         "%d 回の予測、半幅 %.3f / %.3f s" % (len(preds), hw_flash, max(hw_red) if hw_red else float("nan")))
    # (b) 試行: 青点滅の始まりの位置を乱数に、予測あり / なしで黄の瞬間にジレンマゾーンにいるか
    rng = np.random.default_rng(31)
    dfl = rng.uniform(40.0, 330.0, N_SIG)
    ph = rng.uniform(0.0, 1.0, N_SIG)
    cnt = {(u, rdg): 0 for u in (True, False) for rdg in ("ghm", "line")}
    stops = 0
    for df, p in zip(dfl, ph):
        for u in (True, False):
            r = signal_run(df, u, CAM_FPS, phase=p)
            d, v, br = r["at_amber"]
            cnt[(u, "ghm")] += in_dilemma(d, v, br, GHM)
            cnt[(u, "line")] += in_dilemma(d, v, br, STOPLINE)
            stops += (u and r["rec"][-1][3] == "stop")
    zg = DD.dilemma_zone(V_SIG, **GHM)
    zl = DD.dilemma_zone(V_SIG, **STOPLINE)
    print("  ジレンマゾーン(50 km/h): GHM(交差点 w = %.0f m を黄のうちに抜ける)%.1f〜%.1f m / 停止線の読み(教則 付表1)%.1f〜%.1f m" % (
        GHM["intersection_width"], zg["dilemma"][0], zg["dilemma"][1], zl["dilemma"][0], zl["dilemma"][1]))
    print("  %d 試行(点滅の始まりに停止線の 40〜330 m 手前): 黄の瞬間にジレンマゾーン — 予測あり GHM %d・停止線 %d / 予測なし GHM %d・停止線 %d"
          "(予測ありで止まると決めた %d 試行)" % (N_SIG, cnt[(True, "ghm")], cnt[(True, "line")], cnt[(False, "ghm")], cnt[(False, "line")], stops))
    gate("予測あり: 歩行者信号から黄を予測して早めに止まる / 抜けると決めた自車は、黄の瞬間にジレンマゾーンに入らない(GHM・停止線の両方の読み)",
         cnt[(True, "ghm")] == 0 and cnt[(True, "line")] == 0, "%d 試行" % N_SIG)
    gate("門が自明でない: 予測しない自車は黄の瞬間にジレンマゾーンに入る試行が出る(GHM の読み)", cnt[(False, "ghm")] > 0,
         "%d / %d 試行(停止線の読みでは %d)" % (cnt[(False, "ghm")], N_SIG, cnt[(False, "line")]))
    nopred = signal_run(D_DEMO, False, CAM_FPS)
    return {"base": base, "img_run": img_run, "crops": crops, "series_g": series_g, "read": read, "acc": acc, "ff": ff,
            "first": first, "t1": t1, "cnt": cnt, "zg": zg, "zl": zl, "D_DEMO": D_DEMO, "nopred": nopred, "hw_red": hw_red,
            "lamp_px": lamp_px, "roi": rois}


# ───────────────────────────── 4. 救急車(音と光) ─────────────────────────────
AMB_X0 = 85.0                       # 救急車の前端(t = 0)
EGO_X0 = 190.0                      # 自車の中心(t = 0)
Y_PULL = ROAD - 0.5 - EGO_W / 2     # 左に寄った自車の中心(左端から 0.5 m)
T_AMB = 13.0                        # 場面の長さ [s]
NOISE_AUDIO = 0.03                  # マイクの雑音 σ(100 m 先のサイレンの振幅 = 1 に対して。仮定)


def amb_front(t):
    return AMB_X0 + V_AMB * t


def ego_plan_amb(t_aware, naive=None, x_int=(S_LINE, X_FAR)):
    """救急車に気づいた時刻 t_aware から反応 REACT の後の自車の動き(中心の x, y, 速さ, 向き)の関数を作る。

    near_policy: 気づいた時の自車の前端が交差点の「附近」なら交差点の手前(停止線の 1 m 手前に前端)で左に寄って一時停止、
    そうでなければ左に寄って 10 km/h に落として譲る。救急車が前端を 5 m 過ぎて 1 s 後に、元の車線へ戻って加速。
    naive = "stop_in_lane"(左に寄らずその場で止まる)/ "late_stop"(寄りながら進み、救急車が 70 m に来てから 3 m/s² で止まる)。"""
    t_m = t_aware + REACT
    x_m = EGO_X0 + V_CRUISE * t_m
    front_aware = EGO_X0 + V_CRUISE * t_aware + EGO_L / 2
    near = x_int[0] - NEAR_MARGIN <= front_aware <= x_int[1] + NEAR_MARGIN
    x_stop = x_int[0] - 1.0 - EGO_L / 2
    dtl = 3.0                                                   # 左に寄る時間
    if naive == "late_stop":
        # 救急車の前端が自車の後端の 70 m 後ろに来る時刻(一定速度のまま)
        t_b = (EGO_X0 - EGO_L / 2 - 70.0 - AMB_X0) / (V_AMB - V_CRUISE)
        t_b = max(t_b, t_m)
        a_l = 3.0
    if near and naive != "late_stop":
        a_l = V_CRUISE ** 2 / (2 * max(x_stop - x_m, 1.0))
    t_pass = None

    def state(t):
        nonlocal t_pass
        if t <= t_m:
            return EGO_X0 + V_CRUISE * t, Y_LANE, V_CRUISE, 0.0
        tau = t - t_m
        if naive == "stop_in_lane":
            a = 3.0
            ts = V_CRUISE / a
            tt = min(tau, ts)
            return x_m + V_CRUISE * tt - 0.5 * a * tt * tt, Y_LANE, max(0.0, V_CRUISE - a * tau), 0.0
        lat = min(tau / dtl, 1.0)
        y = Y_LANE + (Y_PULL - Y_LANE) * 0.5 * (1 - math.cos(math.pi * lat))
        vy = (Y_PULL - Y_LANE) * 0.5 * math.pi / dtl * math.sin(math.pi * lat) if tau < dtl else 0.0
        if naive == "late_stop":
            if t <= t_b:
                return EGO_X0 + V_CRUISE * t, y, V_CRUISE, math.atan2(vy, V_CRUISE)
            tb = t - t_b
            ts = V_CRUISE / a_l
            tt = min(tb, ts)
            x = EGO_X0 + V_CRUISE * t_b + V_CRUISE * tt - 0.5 * a_l * tt * tt
            v = max(0.0, V_CRUISE - a_l * tb)
            return x, y, v, math.atan2(vy, max(v, 0.3))
        if near:
            ts = V_CRUISE / a_l
            tt = min(tau, ts)
            x = x_m + V_CRUISE * tt - 0.5 * a_l * tt * tt
            v = max(0.0, V_CRUISE - a_l * tau)
        else:
            v_y = 10.0 / 3.6
            a = 1.5
            ts = (V_CRUISE - v_y) / a
            tt = min(tau, ts)
            x = x_m + V_CRUISE * tt - 0.5 * a * tt * tt + v_y * max(0.0, tau - ts)
            v = max(v_y, V_CRUISE - a * tau)
        return x, y, v, math.atan2(vy, max(v, 0.3))
    return state, near, t_m


def resume_after(state, t_passed, t_res=1.0):
    """救急車が通り過ぎた t_passed の t_res 後に元の車線へ戻って 1.5 m/s² で加速する(採点の窓の外)。"""
    cache = {}

    def st(t):
        if t <= t_passed + t_res:
            return state(t)
        if "x0" not in cache:
            cache.update(zip(("x0", "y0", "v0", "h0"), state(t_passed + t_res)))
        tau = t - t_passed - t_res
        v = min(V_CRUISE, cache["v0"] + 1.5 * tau)
        ta = (V_CRUISE - cache["v0"]) / 1.5
        x = cache["x0"] + (cache["v0"] * min(tau, ta) + 0.75 * min(tau, ta) ** 2) + V_CRUISE * max(0.0, tau - ta)
        lat = min(tau / 3.0, 1.0)
        y = cache["y0"] + (Y_LANE - cache["y0"]) * 0.5 * (1 - math.cos(math.pi * lat))
        return x, y, v, 0.0
    return st


def mic_track(state, n, fs):
    t = np.arange(n) / fs
    S = np.array([state(tt) for tt in t])
    x, y, v, h = S.T
    pos, vel = [], []
    for side in (1.0, -1.0):                                       # 左 = +y、右 = −y(車に固定)
        off = side * MIC_D / 2
        pos.append(np.stack([x - off * np.sin(h), y + off * np.cos(h)], 1))
        vel.append(np.stack([v * np.cos(h), np.gradient(y, t)], 1))
    return np.array(pos), np.array(vel), S


def siren_audio(state, T, seed=40):
    n = int(round(T * FS_AUDIO))
    pos, vel, S = mic_track(state, n, FS_AUDIO)
    s = DD.siren_signal(T, FS_AUDIO, source_start=(AMB_X0, Y_AMB), source_velocity=(V_AMB, 0.0), mic_track=(pos, vel))
    amp0 = float(np.linalg.norm(np.array([AMB_X0, Y_AMB]) - pos[0, 0])) / 100.0     # 100 m で振幅 1
    rng = np.random.default_rng(seed)
    sig = s["signals"] * amp0 + rng.normal(0.0, NOISE_AUDIO, s["signals"].shape)
    return s, sig, S


def beacon_on(t):
    return (t * BEACON_HZ) % 1.0 < 0.5


def red_count(img):
    return int(np.sum((img[..., 0] > 0.75) & (img[..., 1] < 0.35) & (img[..., 2] < 0.35)))


def place_amb(w, ids, t):
    xa = amb_front(t) - 2.8
    move(w, ids["amb"], xa, Y_AMB)
    move(w, ids["beacon"], xa + 2.2, Y_AMB)
    set_color(w, ids["beacon"], (1.0, 0.08, 0.05) if beacon_on(t) else (0.30, 0.05, 0.05))


def scene_ambulance(w, ids, want_frames):
    print("== 4. 救急車: サイレン(2 本のマイク)と赤色灯の点滅(ミラーの画素)で気づき、交差点の手前で左に寄って一時停止する")
    dt = 1.0 / CAM_FPS
    # (a) 気づくまで: 一定速度の仮の道で音を作り、0.1 s ごとに doppler_track で「近づく」を、ミラーの赤い画素で点滅を探す
    st0, _, _ = ego_plan_amb(1e9)
    s0, sig0, _ = siren_audio(st0, 4.0)
    t_sound = None
    for tc in np.arange(0.3, 4.0, 0.1):
        k = int(tc * FS_AUDIO)
        r = DD.doppler_track(sig0[0, :k], FS_AUDIO)
        if r["verdict"] == "approaching":
            t_sound = float(tc)
            break
    t_light = t_truth = None
    cnt_hist = []
    t = 0.0
    while t < 4.0 and t_light is None:
        place_amb(w, ids, t)
        ego = st0(t)
        c = 0
        vis = False
        for side, (Wm, Hm) in (("room", (260, 70)), ("right", (150, 110))):
            v_ = mirror_view(w, (ego[0], ego[1], ego[3]), side, Wm, Hm, emissive_ids=(ids["beacon"],))
            c += red_count(v_["color"])
            vis |= bool(np.any(v_["label"] == 16))
        if t_truth is None and vis and beacon_on(t):
            t_truth = t
        cnt_hist.append((t, c))
        on = [cc for tt, cc in cnt_hist if tt > t - 0.5 and cc >= 2]
        off = [cc for tt, cc in cnt_hist if tt > t - 0.5 and cc == 0]
        if on and off:
            t_light = t
        t += dt
    t_aware = max(t_sound, t_light)
    print("  サイレン: doppler_track が「近づく」と判定 t = %.1f s(0.1 s ごと)/ 赤色灯: ミラーに初めて点いて写る t = %.3f s、"
          "点滅(点いたコマと消えたコマ)を見つけた t = %.3f s → 気づいた t = %.2f s(救急車まで %.0f m)" % (
              t_sound, t_truth, t_light, t_aware, EGO_X0 - EGO_L / 2 + V_CRUISE * t_aware - amb_front(t_aware)))
    gate("気づくまでの遅れ: 赤色灯の点滅はミラーに点いて写ってから ≤ %.2f s(点滅の半周期 + 1 コマ)、サイレンの「近づく」は ≤ 1 s" % (
        0.5 / BEACON_HZ + dt), t_light - t_truth <= 0.5 / BEACON_HZ + dt + 1e-9 and t_sound <= 1.0,
        "光 %.3f s / 音 %.1f s" % (t_light - t_truth, t_sound))
    # (b) 本当の道(気づいた後に左に寄って止まる)で音を作り直す(気づくまでは同じ道 = 同じ音)
    st_p, near, t_m = ego_plan_amb(t_aware)
    # 救急車が自車の前端を 5 m 過ぎる時刻
    tt = np.arange(0.0, T_AMB, 0.01)
    fr = np.array([st_p(x)[0] + EGO_L / 2 for x in tt])
    t_passed = float(tt[np.argmax(amb_front(tt) - 5.6 > fr + 5.0)])
    st = resume_after(st_p, t_passed)
    s, sig, S = siren_audio(st, T_AMB)
    tr = DD.doppler_track(sig[0], FS_AUDIO)
    vt = np.interp(tr["t"], s["t"], s["v_radial"][0])
    rt = np.interp(tr["t"], s["t"], s["range_rate"][0])
    ok = tr["valid"] & (np.abs(vt) > 1.5)
    agree = float(np.mean((tr["state"][ok] == "approaching") == (rt[ok] < 0)))
    err_v = np.abs(tr["v_radial"][tr["valid"]] - vt[tr["valid"]])
    # 方位: 0.2 s の窓ごとに TDOA、真値は窓の中央の発音点の方向(自車の向きに対して、前後は折り返す)
    bears = []
    for tc in np.arange(0.5, T_AMB - 0.5, 0.25):
        k0, k1 = int((tc - 0.1) * FS_AUDIO), int((tc + 0.1) * FS_AUDIO)
        b = DD.tdoa_bearing(sig[0, k0:k1], sig[1, k0:k1], FS_AUDIO, MIC_D)
        tru = []
        for kc in (k0, int(tc * FS_AUDIO), k1 - 1):
            p = np.array([AMB_X0 + V_AMB * s["tau"][0, kc], Y_AMB])
            ang = math.atan2(p[1] - S[kc, 1], p[0] - S[kc, 0]) - S[kc, 3]
            tru.append((math.degrees(math.asin(math.sin(ang))), ang))
        truth, ang = tru[1]
        if abs(math.sin(ang)) < 0.95 and abs(tru[2][0] - tru[0][0]) <= 1.0:
            bears.append((tc, b["bearing_deg"], truth, math.degrees(ang), b["ambiguous"]))
    be = np.array([abs(a - b) for _, a, b, _, _ in bears])
    if os.environ.get("POC_DEBUG"):
        for x in bears:
            print("     ", ["%.2f" % y if isinstance(y, float) else y for y in x])
    print("  サイレン(16 kHz、2 本のマイク 間隔 %.2f m、雑音 σ %.2f): 近づく / 遠ざかるの判定は距離の変化率の符号と %.2f %% 一致"
          "(|視線速度| > 1.5 m/s の %d 標本)、視線速度の誤差 99 %% 点 %.2f m/s" % (
              MIC_D, NOISE_AUDIO, 100 * agree, int(ok.sum()), np.percentile(err_v, 99)))
    print("  方位(TDOA、0.2 s の窓 %d 個。真横 ±18° と、窓の中で方位が 1° 以上動く窓は除く): 幾何との差 最大 %.2f°・中央値 %.2f°。"
          "曖昧と返した窓 %d" % (
        len(bears), be.max(), np.median(be), sum(x[4] for x in bears)))
    gate("ドップラー: 近づく / 遠ざかるの判定 = 幾何の距離の変化率の符号(≥ 99 %、減速して左に寄るマイクのまま)", agree >= 0.99,
         "%.2f %%" % (100 * agree))
    gate("TDOA の方位 = 幾何(前後は折り返す)±0.5°", be.max() <= 0.5 and not any(x[4] for x in bears), "最大 %.2f°" % be.max())
    # (c) 赤色灯の点滅の周波数: ミラーの赤い画素の数の時系列(場面の全体、カメラの fps と、間引いた 3.75 fps)
    ser, frames = [], []
    t_list = np.arange(0.0, T_AMB, dt)
    step_vid = VID_EVERY
    for i, t in enumerate(t_list):
        place_amb(w, ids, t)
        x, y, v, h = st(t)
        ego = (x, y, h)
        views = {}
        c = 0
        for side, (Wm, Hm) in (("room", (260, 70)), ("right", (150, 110))):
            views[side] = mirror_view(w, ego, side, Wm, Hm, emissive_ids=(ids["beacon"],))
            c += red_count(views[side]["color"])
        ser.append(c)
        if want_frames and i % step_vid == 0:
            vd = render(w, dash_pose(ego), DW.camera_intrinsics(CAM_VFOV, *VID_WH), *VID_WH)
            emissive(w, vd, (ids["beacon"],))
            frames.append({"t": t, "dash": vd["color"], "room": views["room"]["color"], "door": views["right"]["color"],
                           "x": x, "y": y, "v": v, "amb": amb_front(t)})
    move(w, ids["amb"], -900.0, 20.0)
    move(w, ids["beacon"], -900.0, 20.0)
    ser = np.array(ser, float)
    vis = ser > 0
    k0, k1 = np.argmax(vis), len(vis) - np.argmax(vis[::-1])
    seg = ser[k0:k1]
    ff = DD.flash_frequency(seg, CAM_FPS)
    sub = int(round(CAM_FPS / 3.75))
    ff2 = DD.flash_frequency(seg[::sub], CAM_FPS / sub)
    fa = DD.aliased_frequency(BEACON_HZ, CAM_FPS)
    fa2 = DD.aliased_frequency(BEACON_HZ, CAM_FPS / sub)
    print("  赤色灯 %.1f Hz(仮定): ミラーの赤い画素の時系列 %.1f s → %.3f Hz(式 %.3f)/ %.2f fps に間引くと %.3f Hz(折り返しの式 |f − fps·round(f/fps)| = %.3f)" % (
        BEACON_HZ, len(seg) * dt, ff["frequency"], fa, CAM_FPS / sub, ff2["frequency"], fa2))
    gate("点滅の周波数 = 式(カメラの fps で %.2f Hz、%.2f fps に間引くと折り返して %.2f Hz)±0.05 Hz" % (fa, CAM_FPS / sub, fa2),
         abs(ff["frequency"] - fa) <= 0.05 and abs(ff2["frequency"] - fa2) <= 0.05, "%.3f / %.3f Hz" % (ff["frequency"], ff2["frequency"]))
    # (d) 40 条の採点: この自車(交差点の附近)、附近でない版、素朴な 2 版
    tg = np.arange(0.0, T_AMB, 0.02)

    def traj(stf):
        A = np.array([stf(x) for x in tg])
        return {"t": tg, "x": A[:, 0] + EGO_L / 2, "y": ROAD - (A[:, 1] + EGO_W / 2), "v": A[:, 2]}
    kw = dict(t_approach=t_aware, t_passed=t_passed, intersections=[(S_LINE, X_FAR)], near_margin=NEAR_MARGIN, left_tol=LEFT_TOL,
              car_length=EGO_L)
    res = {"この自車": DD.yield_maneuver_check(traj(st_p), **kw)}
    res["左に寄らずその場で止まる"] = DD.yield_maneuver_check(traj(ego_plan_amb(t_aware, naive="stop_in_lane")[0]), **kw)
    res["寄りながら進み、救急車が 70 m に来てから止まる"] = DD.yield_maneuver_check(traj(ego_plan_amb(t_aware, naive="late_stop")[0]), **kw)
    # 交差点の附近でない場所(交差点を 120 m 先へ)
    kw2 = dict(kw, intersections=[(S_LINE + 120.0, X_FAR + 120.0)])
    st_far = ego_plan_amb(t_aware, x_int=(S_LINE + 120.0, X_FAR + 120.0))[0]
    res["附近でない(この自車の規則)"] = DD.yield_maneuver_check(traj(st_far), **kw2)
    for k, r in res.items():
        print("    %s: %s 項、%s%s(左端まで最小 %.2f m、止まった %s、交差点の中で止まった %s)" % (
            k, r["case"], "違反なし" if r["ok"] else "違反 ", "、".join(v["detail"] for v in r["violations"]), r["min_y"], r["stopped"],
            r["stopped_in_intersection"]))
    print("  この自車: 気づいて %.1f s 後に寄り始め、前端 %.1f m(停止線 %.0f m の %.1f m 手前)で一時停止、救急車が過ぎた t = %.2f s の 1 s 後に発進" % (
        REACT, float(st_p(t_passed)[0] + EGO_L / 2), S_LINE, S_LINE - float(st_p(t_passed)[0] + EGO_L / 2), t_passed))
    rr = list(res.values())
    gate("40 条: この自車は交差点の附近(1 項)で交差点の手前に左に寄って一時停止、附近でない所(2 項)では左に寄って譲る —— 違反なし、"
         "交差点の中で止まらない", rr[0]["ok"] and rr[0]["case"] == "40-1" and not rr[0]["stopped_in_intersection"] and rr[3]["ok"]
         and rr[3]["case"] == "40-2", "")
    gate("門が自明でない: 左に寄らずに止まる版は「左に寄っていない」、進みながら救急車が近づいてから止まる版は「交差点の中で止まった」",
         any(v["rule"] == "not_left" for v in rr[1]["violations"]) and rr[2]["stopped_in_intersection"], "")
    return {"t_sound": t_sound, "t_light": t_light, "t_truth": t_truth, "t_aware": t_aware, "t_passed": t_passed, "s": s, "sig": sig,
            "S": S, "tr": tr, "bears": bears, "agree": agree, "ff": ff, "ff2": ff2, "fa": fa, "fa2": fa2, "sub": sub, "frames": frames,
            "res": res, "near": near, "st": st, "seg_len": len(seg) * dt}


# ───────────────────────────── 5. バスの発進 ─────────────────────────────
BUS_REAR = 300.0
BUS_L = 10.5
IDM_EGO = dict(v0=V_CRUISE, T=1.5, a=1.2, b=2.0, s0=3.0)    # 発車したバスに付いていく自車(IDM、仮定)


def bus_x(t, t_s, merge=4.0, acc=1.0):
    """バスの後端の位置: 合図 t_s から merge 秒は止まったまま(右へ出る準備)、その後 1.0 m/s² で発進(仮定)。"""
    tau = max(0.0, t - t_s - merge)
    return BUS_REAR + 0.5 * acc * tau * tau, acc * tau


def bus_run(kind, t_s=12.0, T=26.0, dt=0.01):
    """自車の軌跡(前端 x、速さ v)。

    wait: 30 km/h で近づき、バスの後端の 3 m 手前で止まって発車まで待ち、発車したら IDM(drivetraffic.idm_accel)で付いていく。
    pass_on_signal: 待っていたが、バスが合図をした時に右から追い越しを始める(2 m/s² で加速)。
    near_fast: 合図の時に 40 km/h でバスの後端の 13 m 手前(急に減速しないと止まれない)、そのまま右から抜ける。
    far_keep / far_yield: 合図の時に 40 km/h で 40 m 手前。そのまま抜ける / 譲って(減速して)後ろで待つ。"""
    t = np.arange(0.0, T, dt)
    x = np.zeros_like(t)
    v = np.zeros_like(t)
    if kind in ("wait", "pass_on_signal"):
        xs, vs = BUS_REAR - 3.0 - 60.0, V_CRUISE
    else:
        v40 = 40.0 / 3.6
        gap = 13.0 if kind == "near_fast" else 40.0
        xs, vs = BUS_REAR - gap - v40 * t_s, v40
    xc, vc = xs, vs
    for i, tt in enumerate(t):
        bx, bv = bus_x(tt, t_s)
        if kind == "wait":
            gap = bx - xc
            a = max(float(TR.idm_accel(vc, gap, vc - bv, **IDM_EGO)), -6.0)
            if bv == 0.0 and gap <= IDM_EGO["s0"] + 1.0 and vc < 0.5:   # 止まったバスの後ろでは止まって待つ(IDM の這い寄りを切る)
                a, vc = 0.0, 0.0
        elif kind == "pass_on_signal":
            gap = bx - xc
            a = 2.0 if tt >= t_s else max(float(TR.idm_accel(vc, gap, vc - bv, **IDM_EGO)), -6.0)
        elif kind in ("near_fast", "far_keep"):
            a = 0.0
        else:                                                    # far_yield: 反応 1 s の後に後端の 3 m 手前で止まる減速
            if tt >= t_s + 1.0:
                free = bx - 3.0 - xc
                a = -min(6.0, vc * vc / (2 * max(free, 0.05))) if vc > 0 and bv == 0 else \
                    max(float(TR.idm_accel(vc, bx - xc, vc - bv, **IDM_EGO)), -6.0)
            else:
                a = 0.0
        x[i], v[i] = xc, vc
        vc = max(0.0, vc + a * dt)
        xc += vc * dt
    return {"t": t, "x": x, "v": v}


def brake_sim_required(v, D, rho, dt=1e-4):
    """反応 ρ の後に一定減速 a で止まって D 以内に収まる最小の a を、刻みを進めるブレーキ + 二分法で(閉形式と別の経路)。"""
    def stops(a):
        x, vv, t = 0.0, v, 0.0
        while vv > 0:
            if t >= rho:
                vv = max(0.0, vv - a * dt)
            x += vv * dt
            t += dt
            if x > D:
                return False
        return True
    lo, hi = 0.01, 30.0
    if not stops(hi):
        return math.inf
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        lo, hi = (lo, mid) if stops(mid) else (mid, hi)
    return hi


def scene_bus():
    print("== 5. バスの発進: 発進の合図をしたバスの進路を妨げない(道交法 31 条の 2)、既定は発車まで待つ")
    t_s = 12.0
    kinds = {"wait": "既定: 後ろで止まって発車まで待つ", "pass_on_signal": "待っていたが合図の時に右から追い越す",
             "near_fast": "合図の時に 40 km/h で 13 m 手前(急に減速しないと譲れない)→ そのまま抜ける",
             "far_keep": "合図の時に 40 km/h で 40 m 手前 → そのまま抜ける", "far_yield": "同じ位置から譲る(減速して後ろで待つ)"}
    res = {}
    for k in kinds:
        tr = bus_run(k, t_s)
        r = DD.bus_departure_yield_check(tr, t_signal=t_s, bus_rear_x=BUS_REAR, merge_time=4.0, reaction=REACT, sudden_decel=3.0,
                                         standoff=2.0)
        res[k] = (r, tr)
        print("    %s: 譲るのに要る減速 %s m/s²、譲る義務 %s、妨げた %s → %s" % (
            kinds[k], "%.2f" % r["a_required"] if math.isfinite(r["a_required"]) else "∞", "あり" if r["must_yield"] else "なし",
            r["obstructed"], "違反" if r["violation"] else "違反なし"))
    # 譲るのに要る減速 = 刻みのブレーキ + 二分法(far の場面)
    r_far = res["far_keep"][0]
    D = BUS_REAR - 2.0 - r_far["x_at_signal"]
    a_sim = brake_sim_required(r_far["v_at_signal"], D, REACT)
    print("  40 m 手前の a_req: 閉形式 v²/(2(D − vρ)) = %.4f m/s² / 刻み 0.1 ms のブレーキ + 二分法 %.4f m/s²" % (r_far["a_required"], a_sim))
    w_tr = res["wait"][1]
    gaps = np.array([bus_x(tt, t_s)[0] - xx for tt, xx in zip(w_tr["t"], w_tr["x"])])
    k_go = int(np.argmax((w_tr["t"] > t_s) & (w_tr["v"] > 0.1)))
    v_at = float(np.interp(t_s, w_tr["t"], w_tr["v"]))
    print("  既定(待つ): 合図の時の速さ %.2f m/s(止まって待っている)、バスの後端との最小の間隔 %.2f m、合図から自車が動き出すまで %.1f s"
          "(バスは合図の 4 s 後に 1 m/s² で発進、自車は drivetraffic.idm_accel で付いていく)" % (v_at, gaps.min(), w_tr["t"][k_go] - t_s))
    gate("バス: 既定(発車まで待つ)と、40 m 手前から譲る版は違反なし、待つ自車はバスに %.0f m より近づかない" % 2.0,
         not res["wait"][0]["violation"] and not res["far_yield"][0]["violation"] and gaps.min() >= 2.0 and
         abs(a_sim - r_far["a_required"]) <= 2e-3 * r_far["a_required"], "最小の間隔 %.2f m" % gaps.min())
    gate("門が自明でない: 合図の時に追い越す版・40 m 手前からそのまま抜ける版は違反、13 m 手前(急に減速しないと譲れない)は義務なし",
         res["pass_on_signal"][0]["violation"] and res["far_keep"][0]["violation"] and not res["near_fast"][0]["must_yield"]
         and not res["near_fast"][0]["violation"], "")
    return {"res": res, "kinds": kinds, "a_sim": a_sim, "gaps": gaps, "t_s": t_s}


# ───────────────────────────── 図 ─────────────────────────────
def _txt(img, s, xy, anchor="lt", fs=12):
    return np.asarray(AN.text_box(img, s, xy, anchor=anchor, font_size=max(9, fs)), dtype=np.float64)


def _resize(img, W, H):
    from PIL import Image
    a = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    return np.asarray(Image.fromarray(a).resize((int(W), int(H)), Image.LANCZOS), dtype=np.float64) / 255.0


def _inset(f, img, x0, y0, W, H, label, fsz):
    sub = _resize(img, W, H)
    f[y0 - 2:y0 + H + 2, x0 - 2:x0 + W + 2] = 0.08
    f[y0:y0 + H, x0:x0 + W] = sub
    return _txt(f, label, (x0 + W // 2, y0 + H + 3), anchor="ct", fs=fsz)


def fig_main_video(LT, AM, w, ids):
    """主図: 車載カメラ + 右上にミラーの小窓。場面 1 = 左折の前の左ドアミラー(自転車)、場面 2 = 救急車(ルームミラー + 右ドアミラー)。"""
    Wv, Hv = VID_WH
    small = Wv < 500
    fsz = 9 if small else 12
    lab = 8 if small else 11
    K = DW.camera_intrinsics(CAM_VFOV, Wv, Hv)
    sc = Wv / 640.0
    rw, rh = int(210 * sc), int(57 * sc)                 # ルームミラーの小窓
    dw, dh = int(120 * sc), int(88 * sc)                 # ドアミラーの小窓
    frames = []
    demo = LT["demo"]
    t0, t1 = demo["t_sig"] - 1.5, demo["t_end"] + 1.0
    for i, r in enumerate(demo["rec"]):
        if r["t"] < t0 or r["t"] > t1 or i % VID_EVERY:
            continue
        move(w, ids["bike"], r["bx"], Y_BIKE)
        ego = r["ego"]
        vd = render(w, dash_pose(ego), K, Wv, Hv)
        room = mirror_view(w, ego, "room", 260, 70)
        door = mirror_view(w, ego, "left", 150, 110)
        f = vd["color"].copy()
        f = _inset(f, door["color"], Wv - dw - 8, 8, dw, dh, "左ドアミラー", lab)
        f = _inset(f, room["color"], Wv - dw - rw - 18, 8, rw, rh, "ルームミラー", lab)
        sig_on = demo["t_sig"] <= r["t"] < demo["t_end"] + 0.5
        lines = ["場面 1: 左折の前に左後方を確かめる", "t = %4.1f s   %4.1f km/h" % (r["t"], 3.6 * r["v"]),
                 "判断: %s" % JP[r["mode"]]]
        if sig_on:
            lines.append("左の合図(30 m 手前から)")
        if r["in_mirror"]:
            lines.append("左ドアミラーに自転車" if not small else "ミラーに自転車")
        elif r["direct"]:
            lines.append("自転車が直接見える")
        f = _txt(f, "\n".join(lines), (6, 6), fs=fsz)
        frames.append(np.clip(f, 0, 1))
    move(w, ids["bike"], -900.0, 0.0)
    n1 = len(frames)
    tr = AM["tr"]
    for fr in AM["frames"]:
        t = fr["t"]
        f = fr["dash"].copy()
        f = _inset(f, fr["door"], Wv - dw - 8, 8, dw, dh, "右ドアミラー", lab)
        f = _inset(f, fr["room"], Wv - dw - rw - 18, 8, rw, rh, "ルームミラー", lab)
        m = (tr["t"] > t - 0.3) & (tr["t"] <= t) & tr["valid"]
        stt = tr["state"][m]
        snd = "—" if not m.any() else {"approaching": "近づいている", "receding": "遠ざかっている", "abeam": "真横",
                                        "unknown": "—"}[max(set(stt), key=list(stt).count)]
        k1 = int(t * FS_AUDIO)
        brg = ""
        if k1 > int(0.2 * FS_AUDIO):
            b = DD.tdoa_bearing(AM["sig"][0, k1 - int(0.2 * FS_AUDIO):k1], AM["sig"][1, k1 - int(0.2 * FS_AUDIO):k1], FS_AUDIO, MIC_D)
            side = "右" if b["bearing_deg"] < 0 else "左"
            behind0 = fr["amb"] < fr["x"] + EGO_L / 2
            brg = ("音の方位: %s %.0f°(前後は赤色灯で → %s)" % (side, abs(b["bearing_deg"]), "後ろ" if behind0 else "前")
                   if not small else
                   "方位 %s %.0f°" % (side, abs(b["bearing_deg"])))
        behind = fr["amb"] < fr["x"] + EGO_L / 2
        if t < AM["t_aware"]:
            mode = "cruise"
        elif t < AM["t_aware"] + REACT:
            mode = "hear"
        elif t < AM["t_passed"]:
            mode = "pull_stop" if fr["v"] > 0.05 else "stopped"
        else:
            mode = "stopped" if t < AM["t_passed"] + 1.0 else "resume"
        lines = ["場面 2: 後ろから救急車", "t = %4.1f s   %4.1f km/h" % (t, 3.6 * fr["v"]),
                 "サイレン: %s" % snd, brg, "赤色灯: %s" % ("ミラーに写る → 後ろ" if behind else "前に見える"),
                 "判断: %s" % JP[mode]]
        f = _txt(f, "\n".join(x for x in lines if x), (6, 6), fs=fsz)
        frames.append(np.clip(f, 0, 1))
    fps = CAM_FPS / VID_EVERY
    figs.save_video("decisions_mirrors_ambulance", frames, fps=fps, gif_every=2, gif_width=480,
                    caption="主図(車載カメラ %d × %d・%.0f fps、右上にミラーの小窓。ミラーは鏡の向こうの仮想カメラで描き左右を反転)。"
                            "場面 1(%d コマ): 左折の 30 m 手前で合図、その前に左ドアミラーで左後方を確かめ、路側帯を来る自転車(黄の上着)を見つけて"
                            "左折の手前で待ち、自転車が交差点を抜けてから曲がる(最小距離 %.2f m。ミラーを見ない版は巻き込む)。"
                            "場面 2: 後ろから救急車(60 km/h)。サイレンの「近づく」(ドップラー)を t = %.1f s、ミラーの赤色灯の点滅を t = %.2f s に見つけ、"
                            "%.0f s の反応の後に左へ寄り、交差点の手前(停止線の 1 m 手前)で一時停止、救急車が過ぎた t = %.1f s の 1 s 後に発進"
                            "(道交法 40 条 1 項)。音の方位は 2 本のマイクの到着時間差(前後は区別できないので、ミラーに写る = 後ろ)。" % (
                                Wv, Hv, fps, n1, LT["demo"]["dmin"], AM["t_sound"], AM["t_light"], REACT, AM["t_passed"]))


def fig_signal_video(SG, w, ids):
    """動画 2: 歩行者信号の青点滅 → 車両の黄までの残りのカウントダウン、下に俯瞰の帯(ジレンマゾーン)。"""
    import fullseye as fs
    Wv, Hv = VID_WH
    small = Wv < 500
    fsz = 10 if small else 13
    K = DW.camera_intrinsics(CAM_VFOV, Wv, Hv)
    Hs = int(150 * Wv / 640)
    base, nop = SG["img_run"], SG["nopred"]
    lamp_read = SG["read"]
    frames = []
    ta = PLAN["amber_onset"]
    zg = DD.dilemma_zone(V_SIG, **GHM)["dilemma"]
    zl = DD.dilemma_zone(V_SIG, **STOPLINE)["dilemma"]
    xl = (-230.0, 30.0)                                        # 停止線からの位置(負 = 手前)
    strip_bg = None
    for i, r in enumerate(base["rec"]):
        t, d, v, plan, braking, pred = r
        if i % VID_EVERY or t < PLAN["ped_flash_start"] - 1.5:
            continue
        if t > ta + 3.5:
            break
        g, rr = ped_lamps(t)
        set_color(w, ids["ped_green"], (0.10, 0.95, 0.55) if g[0] else (0.08, 0.12, 0.10))
        set_color(w, ids["ped_red"], (1.0, 0.15, 0.10) if rr[0] else (0.12, 0.08, 0.08))
        vs = str(DD.signal_state(PLAN, "veh_A", [t])[0])
        DW.set_signal_state(w, ids["veh_sig"], {"green": "green", "amber": "yellow", "red": "red"}[vs])
        Pd = dash_pose((S_LINE - d - EGO_L / 2, Y_LANE, 0.0))
        vd = render(w, Pd, K, Wv, Hv)
        emissive(w, vd, (ids["ped_green"], ids["ped_red"]))
        f = vd["color"]
        z = int(4 * Wv / 640) if not small else 2
        crop = SG["crops"][i] if SG["crops"] else None
        if crop is not None:
            cw = 48 * z
            f[6:10 + cw, Wv - cw - 10:Wv - 6] = 0.08
            big = np.repeat(np.repeat(crop, z, 0), z, 1)
            for (rc, cc) in SG["roi"][i]:                       # 読み取りの窓(5 × 5 画素)を水色の枠で
                r0, r1, c0, c1 = (rc - 2) * z, (rc + 3) * z - 1, (cc - 2) * z, (cc + 3) * z - 1
                if 0 <= r0 and r1 < cw and 0 <= c0 and c1 < cw:
                    big[r0, c0:c1 + 1] = (0.2, 0.9, 1.0)
                    big[r1, c0:c1 + 1] = (0.2, 0.9, 1.0)
                    big[r0:r1 + 1, c0] = (0.2, 0.9, 1.0)
                    big[r0:r1 + 1, c1] = (0.2, 0.9, 1.0)
            f[8:8 + cw, Wv - cw - 8:Wv - 8] = big
            f = _txt(f, "歩行者信号(拡大 %d 倍)" % z, (Wv - cw // 2 - 8, 12 + cw), anchor="ct", fs=8 if small else 11)
        st_ped = {"green": "青", "flash": "青点滅", "red": "赤"}[str(DD.signal_state(PLAN, "ped_A", [t])[0])]
        lines = ["t = %4.1f s   %4.1f km/h   停止線まで %5.1f m" % (t, 3.6 * v, d), "歩行者信号(読み取り): %s" % (
            {(True, False): "青が点いている", (False, False): "消えている", (False, True): "赤"}[tuple(bool(x) for x in lamp_read[i])])]
        if pred is not None:
            if t < ta:
                lines.append("車両の黄まで あと %.1f s(±%.2f)" % (max(pred["amber_onset"] - t, 0.0), pred["half_width"]))
            lines.append("判断: %s" % (JP["go"] if plan == "go" else (JP["brake"] if braking else
                                                                     "止まると決めた(%.0f m 手前から減速)" % (v * v / (2 * A_GENTLE)))))
        else:
            lines.append("判断: %s" % JP["cruise"])
        lines.append("車両の信号: %s" % {"green": "青", "amber": "黄", "red": "赤"}[vs])
        f = _txt(f, "\n".join(lines), (6, 6), fs=fsz)
        # 俯瞰の帯
        L0 = 64 if not small else 54

        def X(xx):
            return L0 + (xx - xl[0]) / (xl[1] - xl[0]) * (Wv - L0 - 10)
        rows_ = {"pred": (0.14, 0.36), "nop": (0.42, 0.64)}
        if strip_bg is None:                                     # 文字と目盛り(コマごとに変わらない)
            strip_bg = np.full((Hs, Wv, 3), 0.95)
            for key, (y0r, y1r) in rows_.items():
                strip_bg = _txt(strip_bg, "予測あり" if key == "pred" else "予測なし", (L0 - 3, (int(Hs * y0r) + int(Hs * y1r)) // 2),
                                anchor="rm", fs=8 if small else 10)
            for xt in (-200, -150, -100, -50, 0):
                strip_bg[int(Hs * 0.64):int(Hs * 0.68), int(X(xt))] = 0.2
                if not small:
                    strip_bg = _txt(strip_bg, "%d m" % xt if xt else "停止線", (int(X(xt)), int(Hs * 0.68)), anchor="ct", fs=9)
            strip_bg = _txt(strip_bg, "青 = 予測あり  黒 = 予測なし  帯 = その車の今の速さ・ブレーキでのジレンマ(上 GHM 橙 / 下 停止線 赤)"
                            "  四角 = 車両の信号" if not small else "青 = 予測あり 黒 = なし 帯 = 今の速さでのジレンマ", (6, Hs - 3),
                            anchor="lb", fs=8 if small else 10)
        strip = strip_bg.copy()
        for key, (y0r, y1r) in rows_.items():
            a0, a1 = int(Hs * y0r), int(Hs * y1r)
            am = (a0 + a1) // 2
            strip[a0:a1, L0:] = 0.45
            # 帯 = この行の車の今の (v, braking) でのジレンマゾーン(門の in_dilemma と同じ式。減速中は反応 0)
            if key == "pred":
                dd, vv, bb = d, v, braking
            else:
                nr = nop["rec"][min(i, len(nop["rec"]) - 1)]
                dd, vv, bb = nr[1], nr[2], nr[4]
            for (h0, h1), rd, col in (((a0, am), GHM, (1.0, 0.65, 0.2)), ((am, a1), STOPLINE, (0.9, 0.15, 0.1))):
                z_ = dilemma_now(vv, bb, rd)
                if z_ is not None:
                    strip[h0:h1, int(max(L0, X(-z_[1]))):max(int(max(L0, X(-z_[1]))), int(X(-z_[0])))] = col
            strip[a0:a1, int(X(0)) - 1:int(X(0)) + 2] = 1.0
            strip[a0:a1, int(X(GHM["intersection_width"]))] = 0.2
            c0 = int(X(-dd))
            strip[a0 + 3:a1 - 3, max(L0, c0 - 9):max(L0, c0)] = (0.15, 0.4, 0.95) if key == "pred" else (0.15, 0.15, 0.15)
        vc = {"green": (0.1, 0.8, 0.4), "amber": (1.0, 0.8, 0.1), "red": (0.9, 0.1, 0.1)}[vs]
        strip[int(Hs * 0.02):int(Hs * 0.12), int(X(0)) - 6:int(X(0)) + 6] = vc
        frames.append(np.clip(np.vstack([f, strip]), 0, 1))
    set_color(w, ids["ped_green"], (0.08, 0.12, 0.10))
    DW.set_signal_state(w, ids["veh_sig"], "green")
    fps = CAM_FPS / VID_EVERY
    fr0 = SG["first"]
    figs.save_video("signal_prediction", frames, fps=fps, gif_every=1, gif_width=480,
                    caption="信号の予測(車載 %d × %d・%.0f fps + 俯瞰の帯)。並行する歩行者信号(右上に灯火のまわりを同じ焦点距離で描いた拡大)の"
                            "青が t = %.2f s に初めて消えたコマで「青点滅」と分かり、青点滅の長さ F = %.0f s と Δ = %.0f s から車両の黄を %.2f s"
                            "(±%.2f、真値 %.0f s)と予測。50 km/h の自車(青)はそのままだと黄の瞬間に GHM のジレンマゾーン(50 km/h で橙、%.1f〜%.1f m)"
                            "に入ると分かるので、早めに 2 m/s² で減速して停止線で止まる。予測しない自車(黒)は黄の瞬間に停止線の %.1f m 手前 = ジレンマ"
                            "ゾーンの中。下の帯は行ごとに「その車の今の速さとブレーキの状態」でのジレンマゾーン(門の in_dilemma と同じ式、減速中は反応 0。"
                            "上 = GHM 橙、下 = 停止線の読み 赤、50 km/h では %.1f〜%.1f m)—— 減速している青の車の帯は縮み、車は帯の外にいる。" % (
                                Wv, Hv, fps, SG["t1"], PLAN["ped_flash_duration"], PLAN["ped_red_to_amber"], fr0["amber_onset"],
                                fr0["half_width"], ta, zg[0], zg[1], nop["at_amber"][0], zl[0], zl[1]))


def _axes_img(W, H, xl, yl):
    import fullseye as fs
    img = np.full((H, W, 3), 1.0)
    rect = (70, 46, W - 100, H - 112)
    ax = fs.axes_transform(rect, xl, yl)
    xt, yt = fs.nice_ticks(*xl, 7), fs.nice_ticks(*yl, 6)
    return img, ax, rect, xt, yt


def _finish_axes(img, ax, xt, yt, title, foot, W, H):
    import fullseye as fs
    img = np.asarray(fs.grid_lines(img, ax, xticks=xt, yticks=yt, alpha=0.25))
    img = np.asarray(fs.axes_frame(img, ax, width=1))
    img = np.asarray(fs.ticks(img, ax, xticks=xt, yticks=yt, tick_len=5, font_size=11))
    img = _txt(img, title, (10, 8), fs=14)
    return _txt(img, foot, (10, H - 10), anchor="lb", fs=11)


def fig_dilemma(SG):
    import fullseye as fs
    W, H = 760, 480
    xl, yl = (0.0, 20.0), (0.0, 80.0)
    img, ax, rect, xt, yt = _axes_img(W, H, xl, yl)
    x0, y0, rw, rh = rect
    vv = xl[0] + (np.arange(rw) + 0.5) / rw * (xl[1] - xl[0])
    dd = yl[1] - (np.arange(rh) + 0.5) / rh * (yl[1] - yl[0])
    V, Dm = np.meshgrid(vv, dd)
    xc = V * GHM["reaction"] + V * V / (2 * GHM["decel"])
    x0g = V * GHM["amber"] - (GHM["intersection_width"] + GHM["car_length"])
    x0l = V * GHM["amber"]
    reg = np.full(V.shape + (3,), 1.0)
    opt = (Dm >= xc) & (Dm <= x0l)
    reg[opt] = (0.80, 0.93, 0.80)
    dg = (Dm < xc) & (Dm > np.maximum(x0g, 0))
    reg[dg] = (1.0, 0.80, 0.55)
    dl = (Dm < xc) & (Dm > np.maximum(x0l, 0))
    reg[dl] = (0.95, 0.45, 0.40)
    img[y0:y0 + rh, x0:x0 + rw] = reg
    v = np.linspace(0.01, 20, 200)
    for yv, col in ((v * GHM["reaction"] + v * v / (2 * GHM["decel"]), (0.1, 0.1, 0.1)),
                    (np.maximum(v * GHM["amber"] - (GHM["intersection_width"] + GHM["car_length"]), -5), (0.85, 0.45, 0.0)),
                    (v * GHM["amber"], (0.75, 0.1, 0.1))):
        m = (yv >= yl[0]) & (yv <= yl[1])
        img = np.asarray(fs.plot_series(img, ax, v[m], yv[m], kind="line", color=col, width=2))
    img = np.asarray(fs.plot_series(img, ax, [V_SIG, V_SIG], [0, 80], kind="line", color=(0.2, 0.3, 0.9), width=1))
    img = np.asarray(fs.legend_box(img, [((0.1, 0.1, 0.1), "止まれる境 x_c = vδ + v²/(2a)"),
                                         ((0.85, 0.45, 0.0), "抜けられる境 x_0 = vτ − (w + L)(GHM)"),
                                         ((0.75, 0.1, 0.1), "停止線を越えられる境 vτ(教則の読み)"),
                                         ((1.0, 0.80, 0.55), "ジレンマ(GHM の読みだけ)"),
                                         ((0.95, 0.45, 0.40), "ジレンマ(両方の読み)"), ((0.80, 0.93, 0.80), "どちらもできる(停止線の読み)"),
                                         ((0.2, 0.3, 0.9), "50 km/h")], (x0 + 10, y0 + 8), anchor="lt", font_size=11))
    img = _finish_axes(img, ax, xt, yt, "ジレンマゾーン(黄 %.0f s・反応 %.0f s・減速 %.0f m/s²・w %.0f m・車長 %.1f m)" % (
        GHM["amber"], GHM["reaction"], GHM["decel"], GHM["intersection_width"], GHM["car_length"]),
        "横 = 速さ [m/s]   縦 = 黄が点いた時の停止線までの距離 [m]", W, H)
    figs.save("dilemma_zone", img, caption="黄が点いた瞬間の (速さ, 停止線までの距離) の平面。止まれる = 黒の線より上、GHM で交差点を抜けられる = 橙の線より下、"
              "停止線を越えられる = 赤の線より下。橙 = GHM の読みでだけ「止まれず抜けられない」、赤 = 停止線の読みでも。停止線の読みでは "
              "v ≤ 2a(τ − δ) = %.0f m/s(%.0f km/h)でジレンマが無く、GHM の読み(w = %.0f m)ではどの速さにもある。50 km/h(青の縦線)で GHM %.1f〜%.1f m、"
              "停止線 %.1f〜%.1f m。試行: 予測なしの自車は %d / %d 試行で GHM のジレンマに入り、予測ありは 0。" % (
                  2 * GHM["decel"] * (GHM["amber"] - GHM["reaction"]), 3.6 * 2 * GHM["decel"] * (GHM["amber"] - GHM["reaction"]),
                  GHM["intersection_width"], SG["zg"]["dilemma"][0], SG["zg"]["dilemma"][1], SG["zl"]["dilemma"][0], SG["zl"]["dilemma"][1],
                  SG["cnt"][(False, "ghm")], N_SIG))


def fig_spectrogram(AM):
    import fullseye as fs
    x = AM["sig"][0]
    n, hop = 2048, 400
    win = np.hanning(n)
    frames = np.lib.stride_tricks.sliding_window_view(x, n)[::hop] * win
    S = np.abs(np.fft.rfft(frames, axis=1, n=4 * n)) + 1e-9
    f = np.fft.rfftfreq(4 * n, 1.0 / FS_AUDIO)
    tc = (np.arange(S.shape[0]) * hop + n / 2) / FS_AUDIO
    fl = (650.0, 1150.0)
    sel = (f >= fl[0]) & (f <= fl[1])
    Sd = 20 * np.log10(S[:, sel] / S[:, sel].max())
    Sd = np.clip((Sd + 60) / 60, 0, 1)
    W, H = 820, 460
    xl, yl = (0.0, T_AMB), fl
    img, ax, rect, xt, yt = _axes_img(W, H, xl, yl)
    x0, y0, rw, rh = rect
    ti = np.clip(((np.arange(rw) + 0.5) / rw * T_AMB - tc[0]) / (tc[1] - tc[0]), 0, len(tc) - 1).astype(int)
    fi = np.clip(((yl[1] - (np.arange(rh) + 0.5) / rh * (yl[1] - yl[0])) - f[sel][0]) / (f[1] - f[0]), 0, sel.sum() - 1).astype(int)
    val = Sd[ti][:, fi].T
    cmap = np.stack([0.05 + 0.95 * val ** 1.2, 0.05 + 0.8 * val ** 2.0, 0.25 + 0.5 * val - 0.4 * val ** 3], -1)
    img[y0:y0 + rh, x0:x0 + rw] = np.clip(cmap, 0, 1)
    s = AM["s"]
    k = np.arange(0, len(s["t"]), 160)
    img = np.asarray(fs.plot_series(img, ax, s["t"][k], s["f_true"][0][k], kind="scatter", color=(1.0, 1.0, 1.0), marker_size=1))
    for tv, col in ((AM["t_aware"], (0.3, 0.9, 1.0)), (AM["t_passed"], (0.6, 1.0, 0.4))):
        img = np.asarray(fs.plot_series(img, ax, [tv, tv], list(fl), kind="line", color=col, width=1))
    img = np.asarray(fs.legend_box(img, [((1.0, 1.0, 1.0), "真の周波数 f_e·dτ/dt(幾何)"), ((0.3, 0.9, 1.0), "気づいた"),
                                         ((0.6, 1.0, 0.4), "救急車が前端を 5 m 過ぎた")], (x0 + rw - 8, y0 + 8), anchor="rt", font_size=11))
    img = _finish_axes(img, ax, xt, yt, "サイレンのスペクトログラム(左のマイク、自車は減速して左に寄り一時停止)",
                       "横 = 時刻 [s]   縦 = 周波数 [Hz]   明るさ = 強さ(dB、60 dB の幅)", W, H)
    vr = s["v_radial"][0]
    figs.save("siren_spectrogram", img, caption="合成したサイレン(960 / 770 Hz を 0.65 s ずつ、発音時刻の 2 次方程式だけで作る)を左のマイクで聞いた"
              "スペクトログラム。白の点 = 幾何から出した真の周波数(ドップラーの式を使わない)。近づく間は高く(視線速度 最大 %.1f m/s → +%.0f Hz)、"
              "前端を過ぎると低くなる。自車が止まった後は救急車の速さだけの偏移。doppler_track の「近づく / 遠ざかる」は距離の変化率の符号と %.2f %% 一致。" % (
                  vr.max(), 960.0 * (DD.doppler_shift(1.0, vr.max()) - 1.0), 100 * AM["agree"]))


def fig_blind_zone(MIR):
    import fullseye as fs
    panels, caps = [], []
    W, H = 520, 430
    xl, yl = (-15.5, 2.5), (-1.5, 5.0)
    for name, bz in (("convex", MIR["bz"]), ("flat", MIR["flat"])):
        img = np.full((H, W, 3), 1.0)
        rect = (50, 20, W - 70, H - 70)
        ax = fs.axes_transform(rect, xl, yl)

        def P(p):
            x0, y0, rw, rh = rect
            return np.array([x0 + (p[0] - xl[0]) / (xl[1] - xl[0]) * (rw - 1), y0 + (yl[1] - p[1]) / (yl[1] - yl[0]) * (rh - 1)])
        x0r, x1r, y0r, y1r = -15.0, 0.9, 1.2, 4.6
        img = np.asarray(fs.filled_polygon(img, np.array([P(q) for q in ((x0r, y0r), (x1r, y0r), (x1r, y1r), (x0r, y1r))]),
                                           color=(0.88, 0.94, 0.88)))
        for pc in bz["pieces"]:
            img = np.asarray(fs.filled_polygon(img, np.array([P(q) for q in pc]), color=(0.95, 0.45, 0.40), alpha=0.85))
        img = np.asarray(fs.filled_polygon(img, np.array([P(q) for q in obb(0, 0, 0, EGO_L, EGO_W)]), color=(0.3, 0.45, 0.85)))
        Pm, r = bz["mirror_edges"], bz["mirror_rays"]
        for k in range(2):
            img = np.asarray(fs.draw_line(img, P(Pm[k]), P(Pm[k] + 18 * r[k]), color=(0.1, 0.1, 0.1), width=1))
            img = np.asarray(fs.draw_line(img, P(EYE_C), P(Pm[k]), color=(0.5, 0.5, 0.5), width=1))
        u = np.array([math.cos(math.radians(100)), math.sin(math.radians(100))])
        img = np.asarray(fs.draw_line(img, P(EYE_C), P(EYE_C + 5.5 * u), color=(0.2, 0.3, 0.9), width=1))
        if name == "convex":
            colmap = {"mirror": (0.1, 0.6, 0.2), "blind": (0.7, 0.0, 0.0), "direct": (0.2, 0.3, 0.9), "edge": (0.6, 0.6, 0.6)}
            for gx, gy, kk in MIR["grid"]:
                c, rr_ = P((gx, gy))
                img[int(rr_) - 1:int(rr_) + 2, int(c) - 1:int(c) + 2] = colmap[kk]
        img = np.asarray(fs.axes_frame(img, ax, width=1))
        img = np.asarray(fs.ticks(img, ax, xticks=fs.nice_ticks(*xl, 7), yticks=fs.nice_ticks(*yl, 6), tick_len=4, font_size=10))
        img = _txt(img, "横 = 前後 [m](車の中心から)  縦 = 左 [m]", (50, H - 6), anchor="lb", fs=10)
        panels.append(img)
        caps.append("%s: 死角 %.1f m²(赤)" % ("凸面鏡 R 1.4 m" if name == "convex" else "同じ幅の平面鏡", bz["area"]))
    figs.save_grid("mirror_blind_zone", panels, captions=caps, ncols=2, title="左ドアミラーの死角(上から見た図、青 = 自車、薄緑 = 調べた範囲)",
                   caption="左後方(車の中心から左 1.2〜4.6 m・目の後ろ 15 m まで)のうち、左ドアミラーにも直接の視界(方位 100° まで、青の線)にも入らない所(赤)。"
                           "黒の線 = 鏡の両端で反射した光線、灰 = 目から鏡の両端。凸面(R 1.4 m)は同じ幅の平面鏡の %.1f m² を %.1f m² に減らす。"
                           "左の図の点 = 柱を立てて凸面ドアミラーの仮想カメラで描いた結果(緑 = 鏡に写った、濃い赤 = 写らない、青 = 直接見える、"
                           "灰 = 鏡の視野の縁 ±0.15 m で除外)。%d 点で多角形と食い違いなし。" % (MIR["flat"]["area"], MIR["bz"]["area"], MIR["n_chk"]))


def fig_sequence(SQ):
    rows = [["自車の左折(展示の 1 本)", "%d" % SQ["turn"]["deduction"], "0", "—"],
            ["自車の車線変更", "%d" % SQ["lane"]["deduction"], "0", "—"]]
    rows += [[k, "%d" % d, "%d" % e, det] for k, d, e, det in SQ["rows"]]
    figs.save_table("check_sequence", ["版", "減点", "期待(丁運発第44号)", "理由(check_sequence_score)"], rows,
                    title="確認の順序の採点(ミラー → 合図 → 進路変更 → 合図をやめる)",
                    caption="技能試験の採点基準(警察庁 丁運発第44号: 安全不確認 10 点・合図不履行等 5 点)を check_sequence_score で。"
                            "自車の計画は減点 0、順序・時期・継続を崩した 6 版はそれぞれの点数だけ減点。「約 3 秒」の許容 ±0.5 s・30 m の許容 −3 m・"
                            "合図をやめる 2 s 以内は仮定。")


def figures(MIR, LT, SQ, SG, AM, BUS, w, ids):
    print("== 6. 図")
    t = time.time()
    fig_main_video(LT, AM, w, ids)
    print("  主図の動画(%.1f s)" % (time.time() - t))
    t = time.time()
    fig_signal_video(SG, w, ids)
    print("  信号の予測の動画(%.1f s)" % (time.time() - t))
    fig_dilemma(SG)
    fig_spectrogram(AM)
    fig_blind_zone(MIR)
    fig_sequence(SQ)
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
        OK.append(False)


def main() -> int:
    """PoC の本体。"""
    print("BUDGET: %s(FULLSEYE_POC_BUDGET、CI では reduced が既定。展示の数字は full)" % ("reduced" if REDUCED else "full"))
    print("仮定: 判断の遅れ %.1f s、交差点の「附近」%.0f m、「左に寄る」%.1f m 以内、歩行者信号の点滅 %.1f Hz、赤色灯 %.1f Hz、"
          "ドアミラー 凸面 R 1.4 m・幅 0.18 m(目と同じ高さ)" % (REACT, NEAR_MARGIN, LEFT_TOL, PED_FLASH_HZ, BEACON_HZ))
    want = figs.enabled()
    tm = {}
    t = time.time()
    w, ids = build_world()
    MIR = scene_mirrors(w, ids)
    tm["mirror"] = time.time() - t
    t = time.time()
    LT = scene_left_turn()
    tm["turn"] = time.time() - t
    t = time.time()
    SQ = scene_sequence(LT)
    tm["seq"] = time.time() - t
    t = time.time()
    SG = scene_signal(w, ids, want)
    tm["signal"] = time.time() - t
    t = time.time()
    AM = scene_ambulance(w, ids, want)
    tm["amb"] = time.time() - t
    t = time.time()
    BUS = scene_bus()
    tm["bus"] = time.time() - t
    print("  区間ごとの所要 [s]: " + ", ".join("%s %.1f" % kv for kv in tm.items()))
    if want:
        figures(MIR, LT, SQ, SG, AM, BUS, w, ids)
    print("== 結果: %d / %d 門, %.1f s" % (sum(OK), len(OK), time.time() - T0))
    print("PASS" if all(OK) else "FAIL")
    return 0 if all(OK) else 1


if __name__ == "__main__":
    sys.exit(main())
