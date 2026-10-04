# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""他人の場面で、自分の運転手を、他人の採点器に出す —— CommonRoad(TUM)の公開シナリオ × 縦 IDM + pure pursuit × drivability-checker(2026-10-04)。

これまでの運転 PoC は自前の町(drivetown / drivejapan)を自前の門で採点してきた。「自分で作った試験に自分で合格する」だけでは
運転手の値は測れないので、**場面も採点器も他人の物** を使う:
  * 場面 = CommonRoad 2020a XML(lanelet の左右境界・動的障害物の軌跡・標識 274・planning problem)。読み書きは :mod:`drivecommonroad`
    が xml.etree で自前に行う(commonroad-io は照合にだけ任意で使う)。
  * 運転手 = 縦は IDM(drivetraffic と同じ式を自前に書いた物: 目標 = ゴール lanelet の 20 % 地点・停止線・経路上の先行障害物)、
    横は pure pursuit、車両は運動学単線(KS)モデル(BMW 320i、参照点 = 後軸、区分一定入力を RK4)。
  * 採点器 = TUM commonroad-drivability-checker の ``valid_solution``(goal 到達 ∧ 初期状態一致 ∧ 障害物・道路境界・自車同士の無衝突 ∧
    運動学の実現可能性 = 位置 2 cm・向き 0.03 rad で入力を復元できる)。Linux(WSL)でしか動かないので、repo 側は **同じ考え方の第 2 実装**
    (:func:`drivecommonroad.cr_feasible` / :func:`drivecommonroad.cr_collision`)を持ち、公式の合否は WSL のスクリプト
    (tools/check_solution_json.py)が書いた JSON を :func:`drivecommonroad.cr_checker_result` で読む。

門(合成 = CI で常に走る / 実データ = FULLSEYE_COMMONROAD_DATA があるときだけ):
  * 読み: 合成 T 字路の lanelet 4・障害物 1・planning problem 1・dt 0.1・標識 274 = 13.89 m/s・stopLine は 100 だけ。2018b は ValueError。
  * 経路: 継いだ中心線の長さ = Σ 中心線長(1e-6)、lanelet の列 = [100, 101, 102]。
  * KS: δ = 0 で x = x₀ + v t(1e-9)。一定 δ で半径 l_wb / tan δ の円(1e-6)、1 周で始点へ(1e-6)。
  * 母数: BMW_320i = commonroad-vehicle-models ``parameters_vehicle2`` の値(l_wb 2.5789128、b 1.4227170936、4.508 × 1.610、δ ±1.066、
    δ̇ ±0.4、v_max 50.8、a_max 11.5、v_switch 7.319)。
  * 運転(合成): ゴール到達、|a| ≤ max(a_max, b_max)、0 ≤ v ≤ 制限、停止線の 0〜1 m 手前で v = 0 → hold → 発進、
    cr_feasible True かつ max_pos_err < 2 cm、cr_collision は障害物・境界とも False。
  * 衝突の門: 経路上に静止障害物を置いた場面で、前を見ない運転手は衝突(first_collision = 前端が後端に届く step ± 1)、IDM は手前で止まる。
  * XML: ksState の数 = step 数、位置 = 後軸 + b (cos ψ, sin ψ)(1e-12)、ElementTree で再読込、benchmark_id = KS2:JB1:<id>:2020a。
  * 実データ(ZAM_Tjunction-1_1_T-1): lanelet 12・障害物 5・制限 14.0。cr_drive_sweep が全門を通す設定を見つける(148 states、終点 50203)。
    既定の運転手は自前判定で t=68 に obs 1 と衝突(負の対照)。公式 JSON(<FULLSEYE_COMMONROAD_DATA>/checker_*.json)があれば:
    正の走行 valid=True、負の対照 obstacle_collision=True ∧ valid=False、自前と公式の判定が 4 項目で一致、n_states 一致。無ければ「JSON 未提出」。

正直に:
  * **ZAM は IDM だけでは解けない。** ゴールの time_step 区間 [146, 147] は、交差点口を t ≈ 70〜110 に通過する対向車(obs 1)より先に
    左折しろ、を暗に要求する。IDM の自由走行項は柔らかく(v → v₀ で a → 0)、曲率で減速すると 1〜2 step の衝突が残る。横の見通しも効く
    (長いと内側を切って対向車線から離れる)。これを **cr_drive_sweep のルールベース gap acceptance**(a_lat 2.5 → 10、見通し 5 / 8、
    k_v 0.6 / 1.0 を穏やかな順に試し、最初に全門を通った走行)で解いた。採用の a_lat 8 m/s² は快適性としては高い(摩擦円 √(1.5² + 8²) = 8.1
    < 11.5 で採点器の制約内)。「対向車に譲って待つ」運転は実装していない —— 待つとこの時間窓は満たせない。
  * 公開 2020a の ZAM / DEU_Speyer / DEU_Moabit には信号・stopLine・一時停止(206)が無く、規則(止まって確認)の採点は合成場面だけ。
  * 公式の合否は WSL の JSON が正。自前の cr_feasible は記録した入力で同じ RK4 を回すので誤差 0 が出る(採点器は入力を SLSQP で復元する
    別の計算。正負の対照とも一致した)。道路境界は多角形の点包含で、採点器の三角形分割とは別の計算(際どい角は結論が割れうる)。
  * 縦だけ(車線変更なし)の運転手は DEU_Speyer / DEU_Moabit では前任の試行で衝突が残った(時間だけのゴール、交差点の他車)。
  * 曲率は 0.5 m 標本の向き差を 10 m 窓で平均した近似(粗い折線の角を均す)。
図の出典: CommonRoad scenarios(Technical University of Munich、BSD-3-Clause、https://commonroad.in.tum.de)。データそのものは repo に入れない。
Run: py -3.11 examples/poc_driving_commonroad.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く)
"""
from __future__ import annotations

import math
import os
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import drivecommonroad as CR  # noqa: E402
import examplefig as figs  # noqa: E402

_GATES = []
ATTR = "出典: CommonRoad scenarios (TUM, BSD-3-Clause)"
ZAM = "ZAM_Tjunction-1_1_T-1"


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


# ----------------------------------------------------------------------------------------------------------------------
# 図の小道具
def _clip_runs(P, xlim, ylim):
    """折線を窓の中の連続区間に分ける(save_plot は範囲外の点で例外を出すので、先に落とす)。"""
    inside = (P[:, 0] >= xlim[0]) & (P[:, 0] <= xlim[1]) & (P[:, 1] >= ylim[0]) & (P[:, 1] <= ylim[1])
    runs, cur = [], []
    for p, ok in zip(P, inside):
        if ok:
            cur.append(p)
        elif cur:
            runs.append(np.asarray(cur))
            cur = []
    if cur:
        runs.append(np.asarray(cur))
    return [r for r in runs if len(r) >= 2]


def scene_window(scene, run):
    """自車の軌跡を中心にした正方形の窓(+20 m、半幅 30〜70 m)。遠くへ去る障害物で窓が広がらないよう自車だけで決める。"""
    xs, ys = run["x"], run["y"]
    cx, cy = 0.5 * (xs.min() + xs.max()), 0.5 * (ys.min() + ys.max())
    half = min(max(0.5 * max(np.ptp(xs), np.ptp(ys)) + 20.0, 30.0), 70.0)
    return (cx - half, cx + half), (cy - half, cy + half)


def _resample01(P, n):
    c = CR._polyline_cum(P)
    u = c / max(c[-1], 1e-12)
    t = np.linspace(0.0, 1.0, n)
    return np.column_stack([np.interp(t, u, P[:, 0]), np.interp(t, u, P[:, 1])])


def scene_series(scene, run, xlim, ylim, goal_lanelets):
    """俯瞰の系列: lanelet 境界(灰)、ゴール lanelet のハッチ、障害物の軌跡(破線)、自車(実線)、停止位置(点)。"""
    series, kinds, styles, colors = [], [], [], []

    def add(label, P, kind="line", style=None, color="neutral"):
        for r in (_clip_runs(P, xlim, ylim) if kind == "line" else [P]):
            series.append((label, r[:, 0], r[:, 1]))
            kinds.append(kind)
            styles.append(style)
            colors.append(color)
            label = ""                                   # 同じ物の 2 本目以降は凡例に出さない

    for lid in goal_lanelets:
        la = scene["lanelets"][lid]
        n = max(int(la["length"] / 1.5), 4)              # 左右境界を 1.5 m ごとに結ぶ短い線分でハッチ(= 塗り)
        Lb, Rb = _resample01(la["left"], n), _resample01(la["right"], n)
        for i in range(n):
            add("ゴール lanelet %d" % lid if i == 0 else "", np.vstack([Lb[i], Rb[i]]), color="right")
    for lid, la in scene["lanelets"].items():
        add("", la["left"])
        add("", la["right"])
    for ob in scene["obstacles"]:
        P = ob["states"][:, 1:3]
        if ob["static"]:
            add("障害物 %d(静止)" % ob["id"], P[:1], kind="scatter", color="wrong")
        else:
            add("障害物 %d" % ob["id"], P, style="dashed", color="wrong")
    add("自車(KS, BMW 320i)", np.column_stack([run["x"], run["y"]]), color="emphasis")
    stops = [k for k, v in enumerate(run["v"]) if v == 0.0]
    if stops:
        k = stops[0]
        add("停止位置", np.array([[run["x"][k], run["y"][k]]]), kind="scatter", color="emphasis")
    return series, kinds, styles, colors


def gap_series(scene, run):
    """自車と各障害物の中心間距離 − 近似半径(半長の和)。"""
    out = []
    L = run["params"]["length"]
    for ob in scene["obstacles"]:
        idx = {int(round(r[0])): r for r in ob["states"]}
        g = []
        for k, t in enumerate(run["time_step"]):
            st = ob["states"][0] if ob["static"] else idx.get(int(t))
            if st is None:
                g.append(np.nan)
                continue
            g.append(math.hypot(run["x"][k] - st[1], run["y"][k] - st[2]) - 0.5 * (L + ob["shape"]["length"]))
        out.append((ob["id"], np.asarray(g)))
    return out


def topdown_frame(scene, run, k, size=(360, 360), window=None, title=""):
    """matplotlib で俯瞰を 1 コマ描き、(H, W, 3) uint8 で返す。"""
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.patches import Polygon as MplPoly
    fig = Figure(figsize=(size[0] / 100, size[1] / 100), dpi=100)
    FigureCanvasAgg(fig)
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    for la in scene["lanelets"].values():
        ax.add_patch(MplPoly(la["polygon"], closed=True, facecolor=(0.82, 0.82, 0.82), edgecolor=(0.55, 0.55, 0.55), lw=0.6))
    goal = scene["planning_problems"][0]["goal"][0]
    for lid in goal["position_lanelets"] or []:
        ax.add_patch(MplPoly(scene["lanelets"][lid]["polygon"], closed=True, facecolor=(0.75, 0.9, 0.75), edgecolor="none"))
    ax.plot(run["route"]["polyline"][:, 0], run["route"]["polyline"][:, 1], color=(0.3, 0.3, 0.9), lw=0.8, ls=":")
    t = int(run["time_step"][k])
    p = run["params"]
    for ob in scene["obstacles"]:
        st = CR._obstacle_state_at(ob, t)
        if st is None:
            continue
        sh = ob["shape"]
        ax.add_patch(MplPoly(CR._rect_corners(st[1], st[2], st[3], sh["length"], sh["width"]), closed=True, facecolor=(0.85, 0.3, 0.3), edgecolor="k", lw=0.5))
        ax.text(st[1], st[2], str(ob["id"]), fontsize=7, ha="center", va="center", color="w")
    ax.plot(run["x"][:k + 1], run["y"][:k + 1], color=(0.1, 0.3, 0.8), lw=1.4)
    ax.add_patch(MplPoly(CR._rect_corners(run["x"][k], run["y"][k], run["psi"][k], p["length"], p["width"]), closed=True, facecolor=(0.15, 0.4, 0.95), edgecolor="k", lw=0.6))
    if window is None:
        window = scene_window(scene, run)
    ax.set_xlim(*window[0])
    ax.set_ylim(*window[1])
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.text(0.02, 0.97, "%s\nt = %.1f s  v = %.1f m/s" % (title, run["t"][k], run["v"][k]), transform=ax.transAxes, fontsize=8, va="top",
            bbox=dict(facecolor="w", alpha=0.8, edgecolor="none"))
    fig.canvas.draw()
    buf = np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()
    return buf


def pick_frames(scene, run):
    """6 コマ: 出発、交差点の手前、曲がり中、対向車とすれ違い(最短距離)、ゴールに入った時、停止。"""
    rt = run["route"]
    s = run["s"]
    n = len(s) - 1
    k_turn_in = int(np.argmax(s >= rt["lanelet_s"][1])) if len(rt["lanelet_s"]) > 1 else n // 3
    k_mid = int(np.argmax(s >= rt["lanelet_s"][1] + 0.5 * rt["lanelet_len"][1])) if len(rt["lanelet_s"]) > 1 else n // 2
    goal = scene["planning_problems"][0]["goal"][0]
    k_goal = next((k for k in range(len(s)) if CR._goal_state_ok(scene, goal, int(run["time_step"][k]), run["x"][k], run["y"][k], run["v"][k], run["psi"][k])
                   or (goal["position_lanelets"] and any(CR._point_in_polygon(scene["lanelets"][l]["polygon"], (run["x"][k], run["y"][k])) for l in goal["position_lanelets"]))), n)
    # 対向車とのすれ違い = 交差点に入ってからゴール lanelet に入るまでの間で、動く障害物との間隔が最小のコマ
    gaps = gap_series(scene, run)
    moving = [g for oid, g in gaps if not [o for o in scene["obstacles"] if o["id"] == oid][0]["static"]]
    if moving:
        gmin = np.nanmin(np.vstack(moving), axis=0)
        lo, hi = max(k_turn_in - 10, 0), max(k_goal, k_turn_in + 1)
        k_pass = lo + int(np.nanargmin(gmin[lo:hi + 1]))
        if k_pass <= lo + 2:                             # 窓の端が最小 = 交差点内にすれ違いが無い(合成は対向車が先に通る)→ 走行全体の最小
            k_pass = int(np.nanargmin(gmin))
    else:
        k_pass = n // 2
    k_stop = next((k for k, v in enumerate(run["v"]) if v == 0.0 and k > k_turn_in), n)
    # コマの中の文字は matplotlib の既定フォント(CJK 無し)なので英語、日本語は save_grid のキャプションに書く
    picks = [(0, "start", "出発"), (max(k_turn_in - 10, 0), "before junction", "交差点の手前"), (k_mid, "turning left", "左折中"),
             (k_pass, "closest to oncoming", "対向車と最接近"), (k_goal, "enters goal lanelet", "ゴール lanelet に入る"), (k_stop, "stopped", "停止")]
    return sorted(((min(k, n), en, ja) for k, en, ja in picks), key=lambda q: q[0])


# ----------------------------------------------------------------------------------------------------------------------
def main() -> int:
    t_all = time.time()
    print("== 1. 読む(合成 T 字路: 直線 → 左 90° → 直線、対向車 1 台、標識 274、stopLine)")
    xml = CR.cr_synthetic("tjunction")
    sc = CR.cr_read(xml)
    gate("lanelet 4・障害物 1・planning problem 1・dt 0.1", len(sc["lanelets"]) == 4 and len(sc["obstacles"]) == 1 and len(sc["planning_problems"]) == 1 and sc["dt"] == 0.1)
    gate("標識 274 → 13.89 m/s、stopLine は lanelet 100 だけ", sc["lanelets"][100]["speed_limit_mps"] == 13.89 and sc["lanelets"][100]["stop_line"].shape == (2, 2)
         and all(sc["lanelets"][l]["stop_line"] is None for l in (101, 102, 200)))
    try:
        CR.cr_read(xml.replace('commonRoadVersion="2020a"', 'commonRoadVersion="2018b"'))
        bad = False
    except ValueError:
        bad = True
    gate("2018b は ValueError(fail-closed)", bad)

    print("== 2. 経路")
    pp = sc["planning_problems"][0]
    route = CR.cr_route(sc, 100, goal=pp["goal"][0])
    expect = sum(sc["lanelets"][l]["length"] for l in route["lanelets"])
    gate("中心線を継いだ長さ = Σ 中心線長(1e-6)、列 = [100, 101, 102]", route["lanelets"] == [100, 101, 102] and abs(route["length"] - expect) <= 1e-6,
         "%.4f m" % route["length"])

    print("== 3. KS モデル(後軸基準、RK4)")
    x = CR.ks_step((0.0, 0.0, 0.0, 7.0, 0.0), (0.0, 0.0), 0.5)
    gate("δ = 0: x = x₀ + v t(1e-9)", abs(x[0] - 3.5) <= 1e-9 and abs(x[1]) <= 1e-12)
    p = CR.BMW_320I
    delta, v = 0.25, 5.0
    R = p["l_wb"] / math.tan(delta)
    T = 2 * math.pi * R / v
    st = np.array([0.0, 0.0, delta, v, 0.0])
    radii = []
    for _ in range(2000):
        st = CR.ks_step(st, (0.0, 0.0), T / 2000)
        radii.append(math.hypot(st[0], st[1] - R))
    gate("一定 δ: 半径 l_wb / tan δ(1e-6)、1 周で始点へ(1e-6)", max(abs(r - R) for r in radii) <= 1e-6 and math.hypot(st[0], st[1]) <= 1e-6,
         "R = %.3f m" % R)
    gate("BMW_320i = parameters_vehicle2 の値(l_wb 2.5789128, b 1.4227170936, 4.508 × 1.610, δ 1.066, δ̇ 0.4, v 50.8, a 11.5, v_switch 7.319)",
         p["l_wb"] == 2.5789128 and p["b"] == 1.4227170936 and p["length"] == 4.508 and p["width"] == 1.61 and p["delta_max"] == 1.066
         and p["ddelta_max"] == 0.4 and p["v_max"] == 50.8 and p["a_max"] == 11.5 and p["v_switch"] == 7.319)

    print("== 4. 運転(合成)")
    run = CR.cr_drive(sc, stop_lines="scene", a_max=1.5, b_max=3.0)
    gate("ゴール到達(time_step 区間内の 1 状態以上)", run["goal_reached"], "index %d" % run["goal_index"])
    gate("|a| ≤ max(a_max, b_max)、0 ≤ v ≤ 制限 13.89", np.all(np.abs(run["u"][:, 1]) <= 3.0 + 1e-9) and np.all(run["v"] >= 0) and np.all(run["v"] <= 13.89 + 1e-9),
         "v_max %.2f" % run["v"].max())
    ok_stop = len(run["stops"]) >= 1 and run["stops"][0][2] == "stop_line" and 0.0 <= run["stops"][0][3] - run["stops"][0][1] <= 1.0 and run["v"][run["stops"][0][0]] == 0.0
    gate("停止線の 0〜1 m 手前で v = 0、hold の後に発進", ok_stop and any("released" in e for e in run["events"]),
         "front %.2f m before" % (run["stops"][0][3] - run["stops"][0][1]) if run["stops"] else "no stop")
    f = CR.cr_feasible(run)
    gate("cr_feasible True、max_pos_err < 2 cm", f["feasible"] and f["max_pos_err"] < 0.02, "%.2e m, %d transitions" % (f["max_pos_err"], f["n_transitions"]))
    c = CR.cr_collision(sc, run)
    gate("cr_collision: 障害物 False・境界 False", not c["obstacle_collision"] and not c["boundary_violation"])

    print("== 5. 衝突の門(経路上に静止障害物)")
    scb = CR.cr_read(CR.cr_synthetic("blocked"))
    blind = CR.cr_drive(scb, follow_obstacles=False)
    cb = CR.cr_collision(scb, blind)
    front = blind["x"] + 0.5 * blind["params"]["length"]
    k_exp = int(np.argmax(front >= 60.0 - 2.25))
    gate("前を見ない運転手は衝突(first_collision = 前端が後端に届く step ± 1)", cb["obstacle_collision"] and cb["first_collision"][1] == 2
         and abs(cb["first_collision"][0] - int(blind["time_step"][k_exp])) <= 1, "%s" % (cb["first_collision"],))
    idm = CR.cr_drive(scb)
    cb2 = CR.cr_collision(scb, idm)
    gate("IDM は手前で止まる(衝突なし、前端 < 障害物の後端)", not cb2["obstacle_collision"] and idm["x"][-1] + 0.5 * idm["params"]["length"] < 60.0 - 2.25 and idm["v"][-1] <= 1e-3)

    print("== 6. solution XML")
    sxml = CR.cr_solution_xml(sc, run)
    root = ET.fromstring(sxml)
    states = root.find("ksTrajectory").findall("ksState")
    xs = np.array([float(s.findtext("x")) for s in states])
    ys = np.array([float(s.findtext("y")) for s in states])
    gate("ksState の数 = step 数、位置 = 後軸 + b (cos ψ, sin ψ)(1e-12)、benchmark_id", len(states) == len(run["time_step"])
         and np.allclose(xs, run["x_rear"] + p["b"] * np.cos(run["psi"]), atol=1e-12) and np.allclose(ys, run["y_rear"] + p["b"] * np.sin(run["psi"]), atol=1e-12)
         and root.get("benchmark_id") == "KS2:JB1:%s:2020a" % sc["id"], "%d states" % len(states))

    # ── 実データ(あれば)
    real = None
    data_dir = os.environ.get("FULLSEYE_COMMONROAD_DATA", "")
    zam = Path(data_dir) / (ZAM + ".xml") if data_dir else None
    if zam is not None and zam.is_file():
        print("== 7. 実データ: %s(CommonRoad, TUM)" % ZAM)
        t0 = time.time()
        scr = CR.cr_read(zam)
        gate("ZAM: lanelet 12・障害物 5・制限 14.0 m/s", len(scr["lanelets"]) == 12 and len(scr["obstacles"]) == 5 and scr["lanelets"][50195]["speed_limit_mps"] == 14.0)
        sw = CR.cr_drive_sweep(scr)
        rr = sw["run"]
        gate("sweep が全門を通す設定を見つける(148 states、終点 50203)", rr is not None and len(rr["time_step"]) == 148 and rr["route"]["lanelets"][-1] == 50203,
             "%d tries, %s" % (sw["n_tries"], sw["settings"]))
        if rr is None:
            print("  sweep failed:", sw["tries"][-1])
            rr = CR.cr_drive(scr)
        fr = CR.cr_feasible(rr)
        crr = CR.cr_collision(scr, rr)
        gate("ZAM: 自前の cr_feasible True・cr_collision False・ゴール到達", fr["feasible"] and not crr["obstacle_collision"] and not crr["boundary_violation"] and rr["goal_reached"],
             "v_max %.2f, lat %.2f m, a_lat %.1f" % (rr["v"].max(), np.abs(rr["lat_err"]).max(), rr["driver"]["a_lat"]))
        neg = CR.cr_drive(scr)
        cneg = CR.cr_collision(scr, neg)
        gate("負の対照: 既定の運転手(a_lat 2.5)は obs 1 と t ≈ 68 で衝突", cneg["obstacle_collision"] and cneg["first_collision"][1] == 1 and abs(cneg["first_collision"][0] - 68) <= 3,
             "%s" % (cneg["first_collision"],))
        own = {"pos": {"goal_reached": rr["goal_reached"], "feasible": fr["feasible"], "obstacle_collision": crr["obstacle_collision"], "boundary_collision": crr["boundary_violation"]},
               "neg": {"goal_reached": neg["goal_reached"], "feasible": CR.cr_feasible(neg)["feasible"], "obstacle_collision": cneg["obstacle_collision"], "boundary_collision": cneg["boundary_violation"]}}
        for d in own.values():
            d["valid"] = d["goal_reached"] and d["feasible"] and not d["obstacle_collision"] and not d["boundary_collision"]
        official = {}
        jpos, jneg = Path(data_dir) / ("checker_%s.json" % ZAM), Path(data_dir) / "checker_negative_control.json"
        if jpos.is_file() and jneg.is_file():
            official = {"pos": CR.cr_checker_result(jpos), "neg": CR.cr_checker_result(jneg)}
            gate("公式(WSL): 正の走行 valid=True、n_states = 自前の step 数", official["pos"]["valid"] and official["pos"].get("n_states") == len(rr["time_step"]),
                 official["pos"]["checker_version"])
            gate("公式(WSL): 負の対照 obstacle_collision=True ∧ valid=False ∧ feasible=True", official["neg"]["obstacle_collision"] and not official["neg"]["valid"] and official["neg"]["feasible"])
            keys = ("goal_reached", "feasible", "obstacle_collision", "boundary_collision", "valid")
            agree = all(own[w][k] == official[w][k] for w in ("pos", "neg") for k in keys)
            gate("自前(第 2 実装)と公式の判定が 5 項目 × 正負で一致", agree, "%s" % {w: [k for k in keys if own[w][k] != official[w][k]] for w in ("pos", "neg")})
        else:
            print("  公式チェッカーの JSON 未提出(%s / %s が無い): WSL で tools/check_solution_json.py を回して置く" % (jpos.name, jneg.name))
        print("  (%.1f s)" % (time.time() - t0))
        real = {"scene": scr, "run": rr, "neg": neg, "sweep": sw, "own": own, "official": official, "feas": fr, "col": crr}

    if figs.enabled():
        print("== 図")
        if real:
            S, RN, NEG = real["scene"], real["run"], real["neg"]
            where = ZAM
        else:
            S, RN, NEG = sc, run, blind
            where = "合成 T 字路"
        goal_l = S["planning_problems"][0]["goal"][0]["position_lanelets"] or []
        xlim, ylim = scene_window(S, RN)
        series, kinds, styles, colors = scene_series(S, RN, xlim, ylim, goal_l)
        figs.save_plot("commonroad_scene", series, xlabel="x [m]", ylabel="y [m]", title="俯瞰: %s" % where, size=(760, 760), xlim=xlim, ylim=ylim,
                       kinds=kinds, styles=styles, colors=colors, aspect="equal",
                       caption="lanelet の左右境界(灰)、動的障害物の軌跡(破線、番号)、自車の軌跡(実線)、ゴール lanelet(ハッチ)、停止位置(点)。"
                               "自車の運転手は縦 IDM + pure pursuit、車両は KS(BMW 320i)。" + ATTR)
        a = np.append(RN["u"][:, 1], np.nan)
        tt = RN["t"]
        figs.save_plot("commonroad_speed", [("v [m/s]", tt, RN["v"]), ("制限 %.1f m/s" % RN["v_limit"], tt, np.full(len(tt), RN["v_limit"])),
                                            ("曲率の許容 v₀", tt, RN["v_allow"]), ("a [m/s²]", tt[:-1], RN["u"][:, 1])],
                       xlabel="t [s]", ylabel="v [m/s], a [m/s²]", title="速度と加速度: %s" % where, styles=[None, "dashed", "dotted", None],
                       colors=["emphasis", "reference", "neutral", "right"],
                       caption="IDM の希望速度 v₀ = min(制限, 曲率の許容 √(a_lat/|κ|))。a は区分一定(RK4 の 1 step ごと)。|a| ≤ max(a_max 1.5, b_max 3.0)。")
        gp, gn = gap_series(S, RN), gap_series(S, NEG)
        gs = []
        for oid, g in gp:
            m = np.isfinite(g)
            gs.append(("障害物 %d" % oid, tt[m], g[m]))
        gmin = np.nanmin(np.vstack([g for _, g in gn]), axis=0)
        m = np.isfinite(gmin)
        gs.append(("負の対照(衝突する走行)の最小", NEG["t"][m], gmin[m]))
        gs.append(("接触の目安 0", tt, np.zeros(len(tt))))
        figs.save_plot("commonroad_gap", gs, xlabel="t [s]", ylabel="中心間距離 − 半長の和 [m]", title="障害物との間隔: %s" % where,
                       styles=[None] * len(gp) + ["dashed", "dotted"], colors=["neutral"] * len(gp) + ["wrong", "reference"],
                       caption="近似(中心間距離 − 両車の半長)。厳密な衝突判定は cr_collision の分離軸判定(SAT)。負の対照は既定の運転手(a_lat 2.5)" + (
                           "で obs 1 と t ≈ 6.8 s に接触。" if real else "の代わりに前を見ない運転手が静止障害物に接触。"))
        picks = pick_frames(S, RN)
        win = scene_window(S, RN)
        frames = [topdown_frame(S, RN, k, window=win, title=en) for k, en, _ in picks]
        figs.save_grid("commonroad_frames", frames, captions=["%s (t = %.1f s)" % (ja, RN["t"][k]) for k, _, ja in picks], ncols=3,
                       caption="俯瞰の 6 コマ(matplotlib で描いた PNG)。灰 = lanelet、緑 = ゴール lanelet、赤 = 障害物(番号)、青 = 自車と軌跡、点線 = 経路。" + ATTR)
        keys = ("goal_reached", "feasible", "obstacle_collision", "boundary_collision", "valid")
        if real:
            own, off = real["own"], real["official"]
            rows = [[k, str(own["pos"][k]), str(off["pos"][k]) if off else "未提出", str(own["neg"][k]), str(off["neg"][k]) if off else "未提出"] for k in keys]
            figs.save_table("commonroad_checks", ["判定", "正の走行: 自前", "正の走行: 公式", "負の対照: 自前", "負の対照: 公式"], rows,
                            title="自前(第 2 実装)と公式チェッカー(WSL JSON)の判定: %s" % ZAM,
                            caption="公式 = %s。自前 = cr_feasible(記録入力で RK4、位置 2 cm・向き 0.03 rad・入力制限・摩擦円)+ cr_collision(SAT・点包含)。"
                                    % (off["pos"]["checker_version"] if off else "未提出"))
            rows = []
            for t_ in real["sweep"]["tries"]:
                s_ = t_["settings"]
                fail = [n for n, bad in (("goal", not t_["goal_reached"]), ("feasible", not t_["feasible"]), ("collision %s" % (t_["first_collision"],), t_["obstacle_collision"]),
                                         ("boundary", t_["boundary_violation"])) if bad]
                rows.append(["%.1f" % s_["a_lat"], "%.0f" % s_["lookahead"], "%.1f" % s_["k_v"], str(s_["v_cruise"] or "制限"), ", ".join(fail) if fail else "通過(採用)"])
            figs.save_table("commonroad_sweep", ["a_lat [m/s²]", "見通し [m]", "k_v", "v_cruise", "落ちた門"], rows, title="ルールベース gap acceptance の試行(穏やかな順)",
                            caption="IDM だけでは対向車 obs 1 より先に左折できず、曲がりの許容横加速度と見通しを順に上げた。採用 = 最初に全門を通った設定。")
        else:
            rows = [[k, str(v), "未提出(合成場面)", "-", "-"] for k, v in (("goal_reached", run["goal_reached"]), ("feasible", f["feasible"]), ("obstacle_collision", c["obstacle_collision"]),
                                                                         ("boundary_collision", c["boundary_violation"]), ("valid", True))]
            figs.save_table("commonroad_checks", ["判定", "合成: 自前", "公式", "-", "-"], rows, title="自前(第 2 実装)の判定: 合成 T 字路",
                            caption="実データ(FULLSEYE_COMMONROAD_DATA)が無いので公式チェッカーの列は未提出。")
            figs.save_table("commonroad_sweep", ["a_lat [m/s²]", "見通し [m]", "k_v", "v_cruise", "落ちた門"], [["2.5", "5", "0.6", "制限", "通過(合成は 1 回)"]],
                            title="sweep(合成)", caption="合成 T 字路は既定の運転手で全門を通る。")
        print("  figures:", figs.errors())

    n_ng = sum(1 for _, ok in _GATES if not ok)
    print("gates: %d / %d ok  (%.1f s)" % (len(_GATES) - n_ng, len(_GATES), time.time() - t_all))
    if n_ng:
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
