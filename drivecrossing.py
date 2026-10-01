# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""踏切と交差点の優先: 踏切の警報・遮断の時刻、警報灯の交互点滅、渡り切る時間と向こう側の余地、一時停止と左右確認の採点、
線路の見通し、優先道路・明らかに広い道路の判定、進行妨害の閉形式、横断歩道の手前の追越し・停止車両の側方、駐停車禁止の距離。

## 何を作るか

自動運転 PoC 第 11 回「踏切と交差点の優先」の部品を numpy だけで持つ。第 9 回(判断)・第 10 回(横の運動)に続き、
ここでは **入ってよいか・譲るべきか** を条文と公表値の判定にする。部品は **学習を使わない** 閉形式・幾何・公表値・
条文の判定・古典的な数値計算で、どれも独立な経路の検算(門)が立つものだけを置いた:

1. 踏切の時刻(``crossing_timing_check`` / ``crossing_gate_state``)—— 解釈基準の 15・20 秒(遮断機、最小 10・15 秒)と
   30 秒(警報機、最小 20 秒)。
2. 警報灯(``crossing_lamp_signal`` / ``lamp_pair_phase``)—— 2 灯の交互点滅、カメラの露光で積分した明るさ、位相差 π。
3. 渡り切る(``crossing_clear_time`` / ``exit_room_check`` / ``crossing_stop_check``)—— 道交法 33 条 1・2 項、50 条 2 項。
4. 線路の見通し(``track_sight_distance`` / ``sight_triangle_distance``)—— 列車がこの距離より遠ければ渡り切れる、
   角の建物で見える距離。
5. 交差点の優先(``priority_rule`` / ``conflict_zone_intervals`` / ``obstruction_decel``)—— 36 条 1〜3 項、2 条 22 号
   (進行妨害)。
6. 横断歩道(``crosswalk_overtake_check`` / ``crosswalk_stopped_vehicle_check``)—— 38 条 2・3 項。
7. 駐停車禁止(``no_stopping_zones`` / ``legal_stop_intervals`` / ``parking_position_check``)—— 44 条 1 項。

## 真値にする閉形式(門)

* 加速して上限で巡航する走行の時間(``_travel_time``): 距離 d、初速 v₀、加速度 a、上限 v_max。
  d_a = (v_max² − v₀²)/(2a)。d ≤ d_a なら t = (√(v₀² + 2ad) − v₀)/a、そうでなければ t = (v_max − v₀)/a + (d − d_a)/v_max。
* 踏切を渡り切る距離 = 停止線から線路の手前の端 + 踏切の長さ + 車長 + 向こう側の余裕。向こう側の余地 = 前の車の後端 − 踏切の
  向こうの端 ≥ 車長 + 車間 + 余裕(50 条 2 項「その部分で停止することとなるおそれ」を幾何で)。
* 警報灯: 1 灯の周期 P = 60 / (毎分の点滅回数)、点灯の割合 D。点灯時間の原始関数 g(s) = ⌊s/P⌋·DP + min(s mod P, DP)
  (負の s でも成り立つ)。露光 [t, t + e] の平均の明るさ = (g(t + e − φ) − g(t − φ))/e。2 灯は φ = 0 と P/2(交互)。
* 交互の 2 灯の位相差: 相互スペクトル A_k B̄_k の偏角(山の周波数で)。交互なら π(遅れ P/2)。
* 線路の見通し(角の建物): 線路を x 軸(y = 0)、目 (x_e, −d_e)、建物の角 (x_c, −d_c)(建物は x ≥ x_c, y ≤ −d_c)。
  d_c < d_e なら目から角を通る直線が線路と交わる x_v = x_e + (x_c − x_e)·d_e/(d_e − d_c)。d_c ≥ d_e なら遮らない(∞)。
* 必要な見通し: 列車の速さ v_T で、渡り切る時間 T_c(+余裕)の間に列車が進む距離 v_T·(T_c + m)。見える距離が
  これ以上なら「見えない列車」は渡り切る前に着かない。
* 交差道路の車が衝突の領域に入るのを t_free まで遅らせるのに要る一定の減速度(進行妨害の量):
  距離 d、速さ v。T = t_free。v T ≤ d なら 0。T ≤ 2d/v なら a = 2(vT − d)/T²(止まらずに T ちょうどで着く)、
  T > 2d/v なら a = v²/(2d)(領域の手前で止まる)。a が「急な」減速度(仮定)を超えると進行妨害(2 条 22 号)。

## 条文の判定(一次: 道路交通法、e-Gov 法令 API の Wayback 保存版 2025-06-01 施行)

* 33 条 1 項: 踏切の直前(停止線の直前)で停止し、安全を確認した後でなければ進行しない(信号機に従うときは除く)。
* 33 条 2 項: 遮断機が閉じようとし、若しくは閉じている間、又は警報機が警報している間は踏切に入らない。
* 50 条 2 項: 前方の車両等の状況により踏切・横断歩道等で停止することとなるおそれがあるときは入らない。
* 36 条 1 項: 交通整理の行われていない交差点では、左方から来る車両の進行妨害をしない(2 項が適用される場合を除く)。
* 36 条 2 項: 自分の道が優先道路である場合を除き、交差道路が優先道路、又は交差道路の幅員が明らかに広いときは、交差道路の
  車両等の進行妨害をしない。優先道路 = 標識等で指定された道路、及び交差点の中まで中央線・車両通行帯が続く道路。
* 36 条 3 項: (優先道路を通る車両等を除き)同じ場合に交差点に入ろうとするときは徐行する。
* 38 条 2 項: 横断歩道等又はその手前の直前で停止している車両等の側方を通過して前方に出ようとするときは、前方に出る前に
  一時停止。38 条 3 項: 横断歩道等とその手前の側端から前に 30 m 以内では、前方を進行している他の車両等(特定小型原動機付
  自転車等 = 特定小型原付・軽車両(18 条 1 項)を除く)の側方を通過して前方に出てはならない。
* 44 条 1 項: 交差点・横断歩道・自転車横断帯・踏切・軌道敷内・坂の頂上付近・勾配の急な坂・トンネル(1 号)、交差点の側端・
  曲がり角から 5 m(2 号)、横断歩道・自転車横断帯の前後の側端から 5 m(3 号)、安全地帯の左側とその前後 10 m(4 号)、
  停留所の標示柱・標示板から 10 m(5 号、運行時間中)、踏切の前後の側端から 10 m(6 号)で駐停車しない。

## 出典(書誌)と確認の状態

``SOURCES`` に 1 つずつ。primary = 一次の本文を文字で確認、secondary = 二次資料だけ、**assumed(仮定)** = 法令・規格に
数値が無い。

## 単位と座標

m, s, m/s, m/s², rad。道に沿った 1 次元の位置 x(進行方向に増える、車の位置は **前端**)。時刻 t [s]。

## 限界(self_reported)

* 「明らかに広い」に数値の規定は無い(判例は「一見して見分けられる程度」)。幅の比の閾値は **仮定**(既定 1.5)。
* 「直前」「急に」も数値の規定が無い(停止線から 2 m、減速度 2.0 m/s² は **仮定**)。
* 遮断かんが上がり切るまで(上昇中)も「入らない」に含める(33 条 2 項の「閉じている間」を保守側に読んだ解釈)。
* 36 条 1 項と 2 項の関係は通説(優先道路・明らかに広い道路の側は左方優先の適用を受けない)に従う。
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

__all__ = [
    "SOURCES", "CROSSING_TIMING", "LAMP_FLASH_PER_MIN", "LAMP_SIGHT_DISTANCE", "BOOM_HEIGHT", "NO_STOP_DISTANCE",
    "CROSSWALK_NO_PASSING", "EXEMPT_KINDS", "GATE_STATES",
    "crossing_timing_check", "crossing_gate_state", "crossing_lamp_signal", "lamp_pair_phase",
    "crossing_clear_time", "exit_room_check", "crossing_stop_check",
    "track_sight_distance", "sight_triangle_distance",
    "priority_rule", "conflict_zone_intervals", "obstruction_decel",
    "crosswalk_overtake_check", "crosswalk_stopped_vehicle_check",
    "no_stopping_zones", "legal_stop_intervals", "parking_position_check",
]

#: 解釈基準 Ⅶ-9 第62条(踏切保安設備)関係: 標準値と最小値 [s]。warn_to_closed・closed_to_arrival = 4(3)(5)(踏切遮断機)、
#: warn_to_arrival = 5(3)(**踏切警報機**、遮断機の無い踏切)。遮断機のある踏切の警報→到達は 4 の 2 つの和(標準 35、最小 25)
CROSSING_TIMING: Dict[str, float] = {
    "warn_to_closed_std": 15.0, "warn_to_closed_min": 10.0,
    "closed_to_arrival_std": 20.0, "closed_to_arrival_min": 15.0,
    "warn_to_arrival_std": 30.0, "warn_to_arrival_min": 20.0,
}
#: 赤色せん光灯の点滅回数 [回/分](1 灯あたり)。JIS E 3701 の値とされる 50 ± 5(二次資料のみ・未確認)
LAMP_FLASH_PER_MIN = 50.0
#: 赤色せん光の見通し距離 [m](解釈基準 Ⅶ-9 2(5)): 一般 45 m、35 km/h を超えて近づけない踏切道 22 m
LAMP_SIGHT_DISTANCE: Dict[str, float] = {"general": 45.0, "slow_approach": 22.0}
#: 遮断かんの遮断時の高さ [m](解釈基準 Ⅶ-9 3(3)①、標準)
BOOM_HEIGHT = 0.8
#: 44 条 1 項の距離 [m](前後それぞれ)。(距離, 号)
NO_STOP_DISTANCE: Dict[str, Tuple[float, str]] = {
    "intersection": (5.0, "44条1項1号・2号"), "corner": (5.0, "44条1項2号"),
    "crosswalk": (5.0, "44条1項1号・3号"), "bicycle_crossing": (5.0, "44条1項1号・3号"),
    "railway_crossing": (10.0, "44条1項1号・6号"), "safety_zone": (10.0, "44条1項4号"),
    "bus_stop": (10.0, "44条1項5号"), "tunnel": (0.0, "44条1項1号"), "no_stopping_sign": (0.0, "44条1項(標識)"),
}
#: 38 条 3 項: 横断歩道等とその手前の側端から前に 30 m
CROSSWALK_NO_PASSING = 30.0
#: 38 条 3 項・30 条で除かれる「特定小型原動機付自転車等」(18 条 1 項: 特定小型原付と軽車両)
EXEMPT_KINDS = ("specified_small_moped", "light_vehicle", "bicycle")

SOURCES: Dict[str, Dict[str, str]] = {
    "road_traffic_act": {
        "status": "primary", "value": "道路交通法 2条・18条1項・30条・33条・36条・38条・44条・50条",
        "source": "道路交通法(昭和35年法律第105号)。e-Gov 法令 API v2 の Wayback Machine 保存版(2026-02-04 捕捉、"
                  "2025-06-01 施行版)を本文で確認。e-Gov 本体は 2026-10-01 保守中"},
    "crossing_timing": {
        "status": "primary", "value": "遮断機: 警報開始→遮断終了 15 秒標準(10 秒以上)、遮断終了→到達 20 秒標準(15 秒以上)。"
                                      "警報機: 警報開始→到達 30 秒標準(20 秒以上)。どちらも速度で大きく異ならない",
        "source": "国土交通省 鉄道局「鉄道に関する技術上の基準を定める省令等の解釈基準」(国鉄技第157号 平成14年3月8日、"
                  "改正を含む)Ⅶ-9 第62条関係 4(3)(5)(6)・5(3)(4)。mlit.go.jp/common/001968198.pdf の 76–77 頁(PDF 78–79 枚目)"},
    "crossing_lamp": {
        "status": "primary", "value": "赤色せん光灯 2 個以上・動作中交互に点滅・見通し 45 m(22 m)、遮断かん 0.8 m",
        "source": "同上 Ⅶ-9 2(3)(4)(5)・3(3)①"},
    "lamp_flash_rate": {
        "status": "secondary", "value": "毎分 50 ± 5 回",
        "source": "JIS E 3701 に拠るとする二次資料(Web 検索の要約・Wikipedia 系)。規格本文は未確認 = 仮定扱い"},
    "kyosoku": {
        "status": "primary", "value": "6-1-1(1)–(5)(踏切)、5-7-3(1)(2)(交差点)、5-3-2(3)(4)(横断歩道)、5-8-2(2)(駐停車)",
        "source": "交通の方法に関する教則(令和6年9月4日 告示第37号まで)npa.go.jp/bureau/traffic/20241113kyousoku.pdf、"
                  "踏切 64–65 頁、交差点 57 頁、横断歩道 47 頁、駐停車 58 頁"},
    "clearly_wider_ratio": {
        "status": "assumed", "value": "交差道路の幅 ≥ 1.5 × 自分の道の幅 を「明らかに広い」",
        "source": "法に数値なし。判例(最高裁 昭和45年11月10日)の「一見して見分けられる程度」は文言のみ(本文は未確認)"},
    "just_before": {
        "status": "assumed", "value": "「直前」= 停止線(踏切の端)から 2 m 以内、横断歩道の「直前」の停止車両 = 3 m 以内",
        "source": "法に数値なし"},
    "sudden_decel": {
        "status": "assumed", "value": "進行妨害の「急に」= 交差道路の車に要る減速度 > 2.0 m/s²",
        "source": "法に数値なし(2 条 22 号は文言のみ)"},
    "beyond_margin": {
        "status": "assumed", "value": "向こう側の余裕 0.5 m、前の車との車間 1.0 m",
        "source": "法に数値なし"},
}


# ───────────────────────────── 入力の検査 ─────────────────────────────
def _finite(v, name: str, op: str) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a number (got %r)" % (op, name, v)) from None
    if not math.isfinite(x):
        raise ValueError("%s: %s must be finite (got %r)" % (op, name, v))
    return x


def _positive(v, name: str, op: str) -> float:
    x = _finite(v, name, op)
    if x <= 0:
        raise ValueError("%s: %s must be > 0 (got %r)" % (op, name, v))
    return x


def _nonneg(v, name: str, op: str) -> float:
    x = _finite(v, name, op)
    if x < 0:
        raise ValueError("%s: %s must be >= 0 (got %r)" % (op, name, v))
    return x


def _array(v, name: str, op: str, allow_inf: bool = False) -> np.ndarray:
    try:
        a = np.asarray(v, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be numeric" % (op, name)) from None
    bad = np.isnan(a) if allow_inf else ~np.isfinite(a)
    if np.any(bad):
        raise ValueError("%s: %s must be finite" % (op, name))
    return a


def _out(a: np.ndarray):
    return float(a) if np.ndim(a) == 0 else a


def _traj(traj, op: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """{"t", "x"[, "v"]} → (t, x, v)。t は狭義増加、v が無ければ x の差分から。"""
    if not isinstance(traj, dict) or "t" not in traj or "x" not in traj:
        raise ValueError("%s: trajectory must be a dict with 't' and 'x'" % op)
    t = _array(traj["t"], "t", op)
    x = _array(traj["x"], "x", op)
    if t.ndim != 1 or t.shape != x.shape or t.size < 2:
        raise ValueError("%s: t and x must be 1-D of the same length >= 2" % op)
    if np.any(np.diff(t) <= 0):
        raise ValueError("%s: t must be strictly increasing" % op)
    if "v" in traj and traj["v"] is not None:
        v = _array(traj["v"], "v", op)
        if v.shape != t.shape:
            raise ValueError("%s: v must have the same length as t" % op)
    else:
        v = np.gradient(x, t)
    return t, x, v


def _first_crossing(t: np.ndarray, x: np.ndarray, level: float) -> Optional[float]:
    """x(t) が level に初めて届く時刻(線形補間)。届かなければ None。"""
    k = np.flatnonzero(x >= level)
    if k.size == 0:
        return None
    i = int(k[0])
    if i == 0:
        return float(t[0])
    x0, x1 = x[i - 1], x[i]
    return float(t[i - 1] + (level - x0) / (x1 - x0) * (t[i] - t[i - 1]))


def _travel_time(d, v0, a, vmax):
    """距離 d を初速 v0・加速度 a(上限 vmax まで)で進む時間(閉形式、配列可)。"""
    d = np.asarray(d, np.float64)
    if a == 0.0:
        return d / v0
    da = (vmax * vmax - v0 * v0) / (2.0 * a)
    t_acc = (np.sqrt(v0 * v0 + 2.0 * a * np.minimum(d, da)) - v0) / a
    return np.where(d <= da, t_acc, (vmax - v0) / a + (d - da) / vmax)


def _kin_args(v0, accel, v_max, op):
    v0 = _nonneg(v0, "v0", op)
    a = _nonneg(accel, "accel", op)
    vmax = _positive(v_max, "v_max", op) if v_max is not None else math.inf
    if v0 > vmax:
        raise ValueError("%s: v0 must not exceed v_max" % op)
    if a == 0.0 and v0 == 0.0:
        raise ValueError("%s: accel and v0 cannot both be zero (never arrives)" % op)
    if a > 0 and not math.isfinite(vmax):
        vmax = 1e12
    if a == 0.0:
        vmax = max(v0, 1e-300)
    return v0, a, vmax


# ───────────────────────────── 1. 踏切の時刻 ─────────────────────────────
def crossing_timing_check(t_warning, t_closed, t_arrival, *, timing: Optional[dict] = None) -> Dict[str, object]:
    """踏切の 3 つの時刻(警報開始・遮断動作の終了・列車の到達)を解釈基準の標準と最小に照らす(配列 = 列車ごと)。

    警報→到達の 30 / 20 秒は解釈基準 5(3) の**踏切警報機**(遮断機なし)の値。遮断機のある踏切では 4(3)(5) の 2 つ
    (15 + 20 = 35 秒が標準)が効き、30 / 20 秒の側は自動的に満たされる。

    返り値: ``warn_to_closed`` / ``closed_to_arrival`` / ``warn_to_arrival``(各 [s])、``meets_minimum``(3 つとも最小以上)、
    ``deviation``(標準からのずれ、3 つ)、``spread``(列車ごとの警報開始→到達の最大 − 最小。解釈基準 5(4)「速度等により
    大きく異なるものでない」の量)。時刻の順が逆(遮断終了が警報より前など)は ValueError。"""
    op = "crossing_timing_check"
    tw = _array(t_warning, "t_warning", op)
    tc = _array(t_closed, "t_closed", op)
    ta = _array(t_arrival, "t_arrival", op)
    try:
        tw, tc, ta = np.broadcast_arrays(tw, tc, ta)
    except ValueError:
        raise ValueError("%s: t_warning, t_closed, t_arrival must broadcast" % op) from None
    if np.any(tc < tw) or np.any(ta < tc):
        raise ValueError("%s: need t_warning <= t_closed <= t_arrival" % op)
    T = dict(CROSSING_TIMING)
    if timing:
        T.update(timing)
    a, b, c = tc - tw, ta - tc, ta - tw
    ok = (a >= T["warn_to_closed_min"]) & (b >= T["closed_to_arrival_min"]) & (c >= T["warn_to_arrival_min"])
    return {"warn_to_closed": _out(a), "closed_to_arrival": _out(b), "warn_to_arrival": _out(c),
            "meets_minimum": bool(np.all(ok)) if ok.ndim == 0 else ok,
            "deviation": {"warn_to_closed": _out(a - T["warn_to_closed_std"]),
                          "closed_to_arrival": _out(b - T["closed_to_arrival_std"]),
                          "warn_to_arrival": _out(c - T["warn_to_arrival_std"])},
            "spread": float(np.ptp(c)) if c.size else 0.0}


#: crossing_gate_state の状態の番号
GATE_STATES = ("idle", "warning", "lowering", "closed", "raising")


def crossing_gate_state(t, *, t_warning: float, t_lower_start: float, lower_duration: float, t_clear: float,
                        raise_duration: float) -> Dict[str, np.ndarray]:
    """踏切の状態機械(警報機 + 遮断機)を時刻 t(配列)で評価する。

    状態: 0 idle(警報なし・かん上)、1 warning(警報中・かん上)、2 lowering(降下中)、3 closed(遮断中)、
    4 raising(列車が過ぎて警報が止まり、かんが上昇中)。警報灯は 1〜3 で点く(解釈基準 5(5)「通過後に警報を停止」)。
    かんの角 [rad]: 上 π/2 → 下 0。降下・上昇は余弦の滑らかな形(**仮定**: 実機の降下曲線は資料なし)。
    ``entry_forbidden`` = 1〜4(33 条 2 項。上昇中も含めるのは保守側の解釈)。

    返り値: ``state``(int)、``boom_angle``、``lamps_on``(bool)、``entry_forbidden``(bool)、``t_closed``(降下の終わり)。"""
    op = "crossing_gate_state"
    tt = _array(t, "t", op)
    tw = _finite(t_warning, "t_warning", op)
    tl = _finite(t_lower_start, "t_lower_start", op)
    ld = _positive(lower_duration, "lower_duration", op)
    tcl = _finite(t_clear, "t_clear", op)
    rd = _positive(raise_duration, "raise_duration", op)
    if not (tw <= tl and tl + ld <= tcl):
        raise ValueError("%s: need t_warning <= t_lower_start and t_lower_start + lower_duration <= t_clear" % op)
    tc = tl + ld
    st = np.zeros(tt.shape, np.int64)
    st[(tt >= tw) & (tt < tl)] = 1
    st[(tt >= tl) & (tt < tc)] = 2
    st[(tt >= tc) & (tt < tcl)] = 3
    st[(tt >= tcl) & (tt < tcl + rd)] = 4
    ang = np.full(tt.shape, 0.5 * math.pi)
    u = np.clip((tt - tl) / ld, 0.0, 1.0)
    ang = np.where(st == 2, 0.25 * math.pi * (1.0 + np.cos(math.pi * u)), ang)
    ang = np.where(st == 3, 0.0, ang)
    u = np.clip((tt - tcl) / rd, 0.0, 1.0)
    ang = np.where(st == 4, 0.25 * math.pi * (1.0 - np.cos(math.pi * u)), ang)
    return {"state": st, "boom_angle": ang, "lamps_on": (st >= 1) & (st <= 3), "entry_forbidden": st >= 1,
            "t_closed": tc}


# ───────────────────────────── 2. 警報灯 ─────────────────────────────
def _ontime(s, P, D):
    """位相 0 の矩形波(周期 P、点灯 D·P)の点灯時間の原始関数 g(s)。"""
    return np.floor(s / P) * D * P + np.minimum(np.mod(s, P), D * P)


def crossing_lamp_signal(t, *, t_on: float, t_off: float, flash_per_min: float = LAMP_FLASH_PER_MIN, duty: float = 0.5,
                         exposure: float = 0.0) -> np.ndarray:
    """2 灯の赤色せん光灯の明るさ(0..1)を時刻 t(配列)で返す: 形 (n, 2)、列 0 = 左、列 1 = 右。

    1 灯の周期 P = 60 / flash_per_min、点灯 duty·P。右の灯は P/2 遅れ(解釈基準「交互に点滅」)。点くのは
    [t_on, t_off)。``exposure`` > 0 ならカメラの露光 [t, t + exposure] の平均(点灯時間の原始関数で閉形式)。"""
    op = "crossing_lamp_signal"
    tt = _array(t, "t", op)
    t0 = _finite(t_on, "t_on", op)
    t1 = _finite(t_off, "t_off", op)
    if t1 < t0:
        raise ValueError("%s: t_off must be >= t_on" % op)
    fpm = _positive(flash_per_min, "flash_per_min", op)
    D = _finite(duty, "duty", op)
    if not (0.0 < D < 1.0):
        raise ValueError("%s: duty must be in (0, 1)" % op)
    e = _nonneg(exposure, "exposure", op)
    P = 60.0 / fpm
    out = np.zeros(tt.shape + (2,))
    u = np.mod((tt - t0) / P, 1.0)                       # 位相を 1 回だけ計算(2 灯の境で丸めが食い違わない)
    for k, phi in enumerate((0.0, 0.5 * P)):
        if e == 0.0:
            on = (np.mod(u - phi / P, 1.0) < D) & (tt >= t0) & (tt < t1)
            out[..., k] = on.astype(np.float64)
        else:
            a = np.clip(tt, t0, t1)
            b = np.clip(tt + e, t0, t1)
            out[..., k] = (_ontime(b - t0 - phi, P, D) - _ontime(a - t0 - phi, P, D)) / e
    return out


def lamp_pair_phase(a, b, fps: float, *, f_min: float = 0.0, pad: int = 8, tol: float = 0.25) -> Dict[str, object]:
    """2 つの明るさの時系列(2 灯の画素)から、共通の点滅の周波数と位相差を相互スペクトルで推定する。

    平均を引き Hann 窓、``pad`` 倍に 0 を詰めた rFFT。|A| + |B| の山(``f_min`` 以上、0 Hz の裾を除く)で
    φ = arg(A_k B̄_k) を [0, π] に畳む。``delay`` = φ / (2π f)。``alternating`` = |φ − π| < tol(交互点滅)。
    周波数は **見かけ** の値(fps/2 を超える点滅は折り返る)。どちらかが一定なら ValueError。"""
    op = "lamp_pair_phase"
    x = _array(a, "a", op)
    y = _array(b, "b", op)
    if x.ndim != 1 or x.shape != y.shape or x.size < 8:
        raise ValueError("%s: a and b must be 1-D of the same length >= 8" % op)
    fs = _positive(fps, "fps", op)
    f_min = _nonneg(f_min, "f_min", op)
    if int(pad) < 1:
        raise ValueError("%s: pad must be >= 1" % op)
    x = x - x.mean()
    y = y - y.mean()
    for z, nm in ((x, "a"), (y, "b")):
        if float(np.ptp(z)) <= 1e-12:
            raise ValueError("%s: %s is constant (no flashing)" % (op, nm))
    n = x.size
    nfft = 1 << int(math.ceil(math.log2(n * int(pad))))
    w = np.hanning(n)
    A = np.fft.rfft(x * w, nfft)
    B = np.fft.rfft(y * w, nfft)
    f = np.fft.rfftfreq(nfft, 1.0 / fs)
    ok = np.flatnonzero(f >= max(f_min, fs / n))
    if ok.size == 0:
        raise ValueError("%s: f_min is above the Nyquist frequency" % op)
    M = np.abs(A) + np.abs(B)
    k = int(ok[np.argmax(M[ok])])
    fk = float(f[k])
    if 0 < k < len(M) - 1 and min(M[k - 1], M[k], M[k + 1]) > 0:
        p, q, r = np.log(M[k - 1]), np.log(M[k]), np.log(M[k + 1])
        den = p - 2 * q + r
        if den < 0:
            fk = float(f[k] + 0.5 * (p - r) / den * (f[1] - f[0]))
    phi = abs(float(np.angle(A[k] * np.conj(B[k]))))
    return {"frequency": fk, "phase": phi, "delay": phi / (2.0 * math.pi * fk) if fk > 0 else math.inf,
            "alternating": abs(phi - math.pi) < float(tol), "nyquist": fs / 2.0}


# ───────────────────────────── 3. 渡り切る ─────────────────────────────
def crossing_clear_time(stop_to_edge: float, crossing_length: float, car_length: float, *, beyond: float = 0.5,
                        accel: float, v_max: Optional[float] = None, v0: float = 0.0) -> Dict[str, float]:
    """停止線から発進して、車の後端が踏切の向こうの端 + ``beyond`` を越えるまでの時間(閉形式)。

    距離 D = stop_to_edge + crossing_length + car_length + beyond(車の位置は前端)。一定の加速度 ``accel`` で
    ``v_max`` まで加速して巡航(教則 6-1-1(5)「変速しないで一気に」= 途中で止まらない)。
    返り値: ``distance``、``time``、``t_on_track``(前端が線路の手前の端に着く時刻)、``v_exit``。"""
    op = "crossing_clear_time"
    e = _nonneg(stop_to_edge, "stop_to_edge", op)
    Lc = _positive(crossing_length, "crossing_length", op)
    Lv = _positive(car_length, "car_length", op)
    bm = _nonneg(beyond, "beyond", op)
    v0, a, vmax = _kin_args(v0, accel, v_max, op)
    D = e + Lc + Lv + bm
    t = float(_travel_time(D, v0, a, vmax))
    t_on = float(_travel_time(e, v0, a, vmax))
    v_exit = min(math.sqrt(v0 * v0 + 2.0 * a * D), vmax) if a > 0 else v0
    return {"distance": D, "time": t, "t_on_track": t_on, "v_exit": float(v_exit)}


def exit_room_check(queue_rear, far_edge: float, car_length: float, *, gap: float = 1.0, beyond: float = 0.5):
    """踏切(横断歩道・交差点も同じ)の向こう側に、自分が止まれる余地があるか(50 条 2 項)。配列可。

    前の車の後端 ``queue_rear`` の後ろ ``gap`` で止まると、自分の後端 = queue_rear − gap − car_length。これが
    far_edge + beyond 以上なら入ってよい。返り値: ``room`` = queue_rear − far_edge、``need`` = car_length + gap + beyond、
    ``ok``、``rear_if_stopped``。前の車が無い場合は queue_rear = +∞。"""
    op = "exit_room_check"
    q = _array(queue_rear, "queue_rear", op, allow_inf=True)
    fe = _finite(far_edge, "far_edge", op)
    Lv = _positive(car_length, "car_length", op)
    g = _nonneg(gap, "gap", op)
    bm = _nonneg(beyond, "beyond", op)
    if np.any(q == -np.inf):
        raise ValueError("%s: queue_rear must not be -inf" % op)
    room = q - fe
    need = Lv + g + bm
    ok = room >= need
    return {"room": _out(room), "need": need, "ok": bool(ok) if ok.ndim == 0 else ok, "rear_if_stopped": _out(q - g - Lv)}


def crossing_stop_check(trajectory, *, stop_line: float, crossing_start: float, crossing_end: float, car_length: float,
                        look_events: Sequence[Tuple[float, str]] = (), forbidden_intervals: Sequence[Tuple[float, float]] = (),
                        queue_rear: Optional[float] = None, signal_controlled: bool = False, near: float = 2.0,
                        v_stop: float = 0.05, gap: float = 1.0, beyond: float = 0.5,
                        brake_max: Optional[float] = None) -> Dict[str, object]:
    """踏切の通り方を採点する(33 条 1・2 項、50 条 2 項、教則 6-1-1(1)(3)(4)(5))。

    ``trajectory`` = {"t", "x"[, "v"]}(x = 車の前端)。判定(違反の名前):
    * ``no_stop``(33 条 1 項): 前端が踏切に入る前に、停止線の直前([stop_line − near, stop_line])で止まっていない
      (``signal_controlled`` なら免除)。
    * ``no_look``(33 条 1 項・教則 6-1-1(1)(2)): **最後の停止**の間(止まってから動き出すまで)に左右の両方を見ていない。
    * ``entered_while_forbidden``(33 条 2 項): 前端が踏切の手前の端を越えた時刻が ``forbidden_intervals`` の中。
      ``brake_max`` [m/s²] を渡すと、その区間の始まりの時点で brake_max の減速では踏切の手前に止まれなかった進入
      (v² / (2 brake_max) > 踏切までの距離)は違反に数えず ``unavoidable`` に記録する(黄信号で止まれない距離と同じ
      考え方。法に明文の例外は無い = **解釈・仮定**)。None なら例外なし。
    * ``no_exit_room``(50 条 2 項): 入った時刻に向こう側の余地が無い(``exit_room_check``)。
    * ``stopped_inside``(教則 6-1-1(5)): 車体が踏切にかかっている間に止まった。
    踏切に入らなかった軌跡は ``entered`` = False(違反は停止・確認以外を数えない)。"""
    op = "crossing_stop_check"
    t, x, v = _traj(trajectory, op)
    sl = _finite(stop_line, "stop_line", op)
    cs = _finite(crossing_start, "crossing_start", op)
    ce = _finite(crossing_end, "crossing_end", op)
    Lv = _positive(car_length, "car_length", op)
    near = _nonneg(near, "near", op)
    vs = _nonneg(v_stop, "v_stop", op)
    if not (sl <= cs < ce):
        raise ValueError("%s: need stop_line <= crossing_start < crossing_end" % op)
    looks = []
    for ev in look_events:
        if len(ev) != 2 or ev[1] not in ("left", "right"):
            raise ValueError("%s: look_events must be (t, 'left'|'right')" % op)
        looks.append((_finite(ev[0], "look time", op), ev[1]))
    fints = []
    for iv in forbidden_intervals:
        a, b = _finite(iv[0], "interval start", op), _finite(iv[1], "interval end", op)
        if b < a:
            raise ValueError("%s: forbidden interval end < start" % op)
        fints.append((a, b))
    t_entry = _first_crossing(t, x, cs)
    entered = t_entry is not None
    lim = t_entry if entered else t[-1] + 1.0
    stopped = (v <= vs) & (t <= lim)
    zone = stopped & (x >= sl - near) & (x <= sl + 1e-9)
    viol: List[str] = []
    stop_iv = None
    if zone.any():
        idx = np.flatnonzero(zone)
        # 最後のひと続きの停止(直前の範囲で)
        j1 = int(idx[-1])
        j0 = j1
        while j0 - 1 >= 0 and zone[j0 - 1]:
            j0 -= 1
        stop_iv = (float(t[j0]), float(t[min(j1 + 1, len(t) - 1)]))
    if not signal_controlled and entered and stop_iv is None:
        viol.append("no_stop")
    seen = sorted({s for (tl, s) in looks if stop_iv is not None and stop_iv[0] - 1e-9 <= tl <= stop_iv[1] + 1e-9})
    if not signal_controlled and entered and stop_iv is not None and len(seen) < 2:
        viol.append("no_look")
    unavoidable = False
    if entered and any(a <= t_entry <= b for a, b in fints):
        a0 = max(a for a, b in fints if a <= t_entry <= b)
        if brake_max is not None and a0 >= t[0]:
            bm_ = _positive(brake_max, "brake_max", op)
            x0 = float(np.interp(a0, t, x))
            v0 = float(np.interp(a0, t, v))
            unavoidable = x0 < cs and v0 * v0 / (2.0 * bm_) > cs - x0
        if not unavoidable:
            viol.append("entered_while_forbidden")
    if entered and queue_rear is not None and not exit_room_check(queue_rear, ce, Lv, gap=gap, beyond=beyond)["ok"]:
        viol.append("no_exit_room")
    on = (x > cs) & (x - Lv < ce)
    if np.any(on & (v <= vs)):
        viol.append("stopped_inside")
    return {"ok": not viol, "violations": viol, "entered": entered, "t_entry": t_entry, "stop_interval": stop_iv,
            "looked": seen, "unavoidable": unavoidable}


# ───────────────────────────── 4. 線路の見通し ─────────────────────────────
def track_sight_distance(v_train, clear_time, *, margin: float = 0.0):
    """渡り切る前に列車が着かないために、線路の上で見えていなければならない距離 = v_train · (clear_time + margin)。

    見える距離がこれ以上なら、見えていない列車は渡り切る前に踏切に着かない(到達時刻 = 距離 / 速さ > 渡り切る時間)。配列可。"""
    op = "track_sight_distance"
    vt = _array(v_train, "v_train", op)
    tc = _array(clear_time, "clear_time", op)
    m = _nonneg(margin, "margin", op)
    if np.any(vt < 0) or np.any(tc < 0):
        raise ValueError("%s: v_train and clear_time must be >= 0" % op)
    return _out(vt * (tc + m))


def sight_triangle_distance(eye_offset: float, eye_distance: float, corner_offset: float, corner_distance: float) -> float:
    """角の建物があるとき、線路の上でどこまで見えるか(見通しの三角形)。

    線路 = x 軸(y = 0)、道路の中心 = x = 0。目 = (eye_offset, −eye_distance)、建物の角 = (corner_offset, −corner_distance)、
    建物は x ≥ corner_offset かつ y ≤ −corner_distance を占める(角の向こうの側、corner_offset > eye_offset)。
    返り値 = 見える線路の上の最も遠い点の x(道路の中心から)。corner_distance ≥ eye_distance(建物が目より線路寄りに
    出ていない)なら遮らず ∞。左側は x を反転して同じ式を使う。"""
    op = "sight_triangle_distance"
    xe = _finite(eye_offset, "eye_offset", op)
    de = _positive(eye_distance, "eye_distance", op)
    xc = _finite(corner_offset, "corner_offset", op)
    dc = _nonneg(corner_distance, "corner_distance", op)
    if xc <= xe:
        raise ValueError("%s: corner_offset must be > eye_offset (the building is beside the road, not in front)" % op)
    if dc >= de:
        return math.inf
    return xe + (xc - xe) * de / (de - dc)


# ───────────────────────────── 5. 交差点の優先 ─────────────────────────────
def _road(r, nm, op):
    if not isinstance(r, dict) or "width" not in r:
        raise ValueError("%s: %s must be a dict with 'width'" % (op, nm))
    w = _positive(r["width"], nm + ".width", op)
    return w, bool(r.get("priority_sign", False)) or bool(r.get("centre_line", False))


def priority_rule(own, cross, *, signalised: bool = False, wide_ratio: float = 1.5) -> Dict[str, object]:
    """交通整理の行われていない交差点で、自分(own)が交差道路(cross)の車に譲るか(36 条 1〜3 項)。

    own, cross = {"width": 幅員 [m], "priority_sign": 優先道路の標識, "centre_line": 交差点の中まで中央線・車両通行帯}。
    優先道路 = 標識 or 中央線(36 条 2 項のかっこ書き)。明らかに広い = 幅の比 ≥ ``wide_ratio``(**仮定**)。

    返り値: ``yield_to`` ∈ {"cross"(交差道路の車すべてに譲る、36 条 2 項)、"left"(左方から来る車に譲る、36 条 1 項)、
    "none"(相手が譲る)}、``must_slow``(36 条 3 項の徐行)、``own_priority`` / ``cross_priority`` / ``cross_clearly_wider`` /
    ``own_clearly_wider``、``article``。交通整理あり(信号)は ValueError(信号に従う)。"""
    op = "priority_rule"
    if signalised:
        raise ValueError("%s: signalised intersection — follow the signal (36 条は交通整理の行われていない交差点)" % op)
    k = _positive(wide_ratio, "wide_ratio", op)
    if k <= 1.0:
        raise ValueError("%s: wide_ratio must be > 1" % op)
    wo, po = _road(own, "own", op)
    wc, pc = _road(cross, "cross", op)
    cw = wc >= k * wo
    ow = wo >= k * wc
    if po and not pc:
        res = ("none", False, "36条2項(自分が優先道路)")
    elif pc and not po:
        res = ("cross", True, "36条2項・3項(交差道路が優先道路)")
    elif po and pc:
        res = ("left", False, "36条1項(双方が優先道路 → 左方優先)")
    elif cw:
        res = ("cross", True, "36条2項・3項(交差道路が明らかに広い)")
    elif ow:
        res = ("none", False, "36条2項(自分の道が明らかに広い)")
    else:
        res = ("left", False, "36条1項(同程度の幅 → 左方優先)")
    return {"yield_to": res[0], "must_slow": res[1], "article": res[2], "own_priority": po, "cross_priority": pc,
            "cross_clearly_wider": cw, "own_clearly_wider": ow}


def conflict_zone_intervals(dist_to_zone, zone_length: float, car_length: float, *, v0: float, accel: float = 0.0,
                            v_max: Optional[float] = None) -> Dict[str, object]:
    """衝突の領域(交差点の中で 2 つの進路が重なる所)を車が占める時刻 [t_in, t_out](閉形式、配列可)。

    前端が dist_to_zone 進むと入り、前端が dist_to_zone + zone_length + car_length 進むと後端が出る。初速 v0 から
    ``accel`` で ``v_max`` まで加速(accel = 0 なら一定の速さ)。既に領域に入っている(dist_to_zone < 0)場合は t_in = 0。"""
    op = "conflict_zone_intervals"
    d = _array(dist_to_zone, "dist_to_zone", op)
    zl = _positive(zone_length, "zone_length", op)
    Lv = _positive(car_length, "car_length", op)
    v0, a, vmax = _kin_args(v0, accel, v_max, op)
    if np.any(d + zl + Lv <= 0):
        raise ValueError("%s: the car has already left the zone" % op)
    t_in = np.where(d > 0, _travel_time(np.maximum(d, 0.0), v0, a, vmax), 0.0)
    t_out = _travel_time(d + zl + Lv, v0, a, vmax)
    return {"t_in": _out(t_in), "t_out": _out(t_out)}


def obstruction_decel(dist, speed, t_free, *, sudden: float = 2.0) -> Dict[str, object]:
    """交差道路の車(領域まで dist、速さ speed)が、領域に t_free より前に入らないために要る一定の減速度(閉形式、配列可)。

    T = t_free。speed·T ≤ dist なら 0(減速しなくても間に合う)。T ≤ 2 dist / speed なら 2(speed·T − dist)/T²、
    それより後なら speed² / (2 dist)(領域の手前で止まる)。``obstructs`` = 減速度 > ``sudden``(**仮定** 2.0 m/s²、
    2 条 22 号「速度又は方向を急に変更しなければならない」)。dist ≤ 0(もう領域にいる)で T > 0 は ∞。"""
    op = "obstruction_decel"
    d = _array(dist, "dist", op)
    v = _array(speed, "speed", op)
    T = _array(t_free, "t_free", op)
    sd = _positive(sudden, "sudden", op)
    if np.any(v < 0):
        raise ValueError("%s: speed must be >= 0" % op)
    d, v, T = np.broadcast_arrays(d, v, T)
    with np.errstate(divide="ignore", invalid="ignore"):
        a1 = 2.0 * (v * T - d) / np.where(T > 0, T * T, 1.0)
        a2 = v * v / (2.0 * np.where(d > 0, d, 1.0))
        tstop = np.where(v > 0, 2.0 * d / np.where(v > 0, v, 1.0), np.inf)
    a = np.where(T <= tstop, a1, a2)
    a = np.where((v * T <= d) | (T <= 0), 0.0, a)
    a = np.where((d <= 0) & (T > 0) & (v * T > d), np.inf, a)
    a = np.where((v == 0) & (d > 0), 0.0, a)
    return {"decel": _out(a), "obstructs": bool(a > sd) if a.ndim == 0 else a > sd}


# ───────────────────────────── 6. 横断歩道 ─────────────────────────────
def _interp_on(t_ref, traj, op):
    t, x, v = _traj(traj, op)
    if t_ref[0] < t[0] - 1e-9 or t_ref[-1] > t[-1] + 1e-9:
        raise ValueError("%s: other trajectories must cover the ego time span" % op)
    return np.interp(t_ref, t, x), np.interp(t_ref, t, v)


def crosswalk_overtake_check(ego, others, *, crosswalk_start: float, crosswalk_end: float,
                             zone: float = CROSSWALK_NO_PASSING, v_moving: float = 0.5) -> Dict[str, object]:
    """横断歩道等とその手前 ``zone`` m の中で、前方を進行している車の前に出たか(38 条 3 項)。

    ego, others[i] = {"t", "x"[, "v"], "kind"}(x = 前端)。他の車の前端を自分の前端が後ろから越えた瞬間(線形補間)を
    「前方に出た」とし、そのときの自分の前端の位置が [crosswalk_start − zone, crosswalk_end] で、相手が進行中(速さ >
    ``v_moving``、**仮定**)かつ特定小型原動機付自転車等(``EXEMPT_KINDS``)でなければ違反。
    返り値: ``ok``、``events`` = [{"other", "t", "x", "in_zone", "exempt", "moving", "violation"}]。"""
    op = "crosswalk_overtake_check"
    t, xe, _ = _traj(ego, op)
    a = _finite(crosswalk_start, "crosswalk_start", op)
    b = _finite(crosswalk_end, "crosswalk_end", op)
    zn = _nonneg(zone, "zone", op)
    vm = _nonneg(v_moving, "v_moving", op)
    if b < a:
        raise ValueError("%s: crosswalk_end must be >= crosswalk_start" % op)
    events = []
    for i, o in enumerate(others):
        xo, vo = _interp_on(t, o, op)
        kind = str(o.get("kind", "car"))
        d = xe - xo
        for k in np.flatnonzero((d[:-1] < 0) & (d[1:] >= 0)):
            s = -d[k] / (d[k + 1] - d[k])
            te = float(t[k] + s * (t[k + 1] - t[k]))
            xp = float(xe[k] + s * (xe[k + 1] - xe[k]))
            vv = float(vo[k] + s * (vo[k + 1] - vo[k]))
            inz = a - zn <= xp <= b
            ex = kind in EXEMPT_KINDS
            mv = vv > vm
            events.append({"other": i, "t": te, "x": xp, "in_zone": inz, "exempt": ex, "moving": mv,
                           "violation": bool(inz and mv and not ex)})
    return {"ok": not any(e["violation"] for e in events), "events": events}


def crosswalk_stopped_vehicle_check(ego, stopped, *, crosswalk_start: float, crosswalk_end: float, near: float = 3.0,
                                    approach: float = 10.0, v_stop: float = 0.05) -> Dict[str, object]:
    """横断歩道等(又はその手前の直前)で止まっている車の側方を通って前に出る前に一時停止したか(38 条 2 項)。

    stopped[i] = {"x": 止まっている車の前端, "t0", "t1": 止まっている時間}。前端が [crosswalk_start − near, crosswalk_end]
    にある車だけが対象(near = 「直前」、**仮定** 3 m)。自分の前端がその前端を越える時刻 t_e が [t0, t1] の中なら、
    t_e より前に、前端が [x − approach, x] にある間に速さ ≤ v_stop になっていなければ違反(approach は **仮定** 10 m)。"""
    op = "crosswalk_stopped_vehicle_check"
    t, xe, v = _traj(ego, op)
    a = _finite(crosswalk_start, "crosswalk_start", op)
    b = _finite(crosswalk_end, "crosswalk_end", op)
    nr = _nonneg(near, "near", op)
    ap = _positive(approach, "approach", op)
    vs = _nonneg(v_stop, "v_stop", op)
    if b < a:
        raise ValueError("%s: crosswalk_end must be >= crosswalk_start" % op)
    events = []
    for i, s in enumerate(stopped):
        xs = _finite(s["x"], "stopped.x", op)
        t0 = _finite(s["t0"], "stopped.t0", op)
        t1 = _finite(s["t1"], "stopped.t1", op)
        if t1 < t0:
            raise ValueError("%s: stopped.t1 must be >= t0" % op)
        if not (a - nr <= xs <= b):
            continue
        te = _first_crossing(t, xe, xs + 1e-9)
        if te is None or not (t0 <= te <= t1):
            continue
        before = (t < te) & (xe >= xs - ap) & (xe <= xs) & (v <= vs)
        events.append({"stopped": i, "t_pass": te, "stopped_before": bool(before.any()), "violation": not bool(before.any())})
    return {"ok": not any(e["violation"] for e in events), "events": events}


# ───────────────────────────── 7. 駐停車禁止 ─────────────────────────────
def no_stopping_zones(features: Iterable[dict], *, in_service: bool = True) -> Dict[str, object]:
    """道に沿った施設から、44 条 1 項の駐停車禁止の区間を作る。

    features[i] = {"kind", "start", "end"}(バス停は "at" = 標示板の位置でもよい)。kind ∈ ``NO_STOP_DISTANCE``。
    区間 = [start − d, end + d](d = その号の距離)。バス停は運行時間中(``in_service``)だけ。
    返り値: ``zones`` = [(a, b, kind, 号)](元の順)、``merged`` = 重なりを併せた (k, 2) の配列(昇順・互いに素)。"""
    op = "no_stopping_zones"
    zones = []
    for f in features:
        if not isinstance(f, dict) or "kind" not in f:
            raise ValueError("%s: each feature must be a dict with 'kind'" % op)
        kind = f["kind"]
        if kind not in NO_STOP_DISTANCE:
            raise ValueError("%s: unknown kind %r (known: %s)" % (op, kind, sorted(NO_STOP_DISTANCE)))
        if "at" in f:
            s = e = _finite(f["at"], "at", op)
        else:
            s = _finite(f.get("start"), "start", op)
            e = _finite(f.get("end"), "end", op)
        if e < s:
            raise ValueError("%s: end must be >= start" % op)
        if kind == "bus_stop" and not in_service:
            continue
        d, art = NO_STOP_DISTANCE[kind]
        zones.append((s - d, e + d, kind, art))
    iv = sorted((z[0], z[1]) for z in zones)
    merged: List[List[float]] = []
    for a, b in iv:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return {"zones": zones, "merged": np.array(merged, np.float64).reshape(-1, 2)}


def legal_stop_intervals(merged, road_start: float, road_end: float, car_length: float) -> np.ndarray:
    """駐停車禁止の区間(併せた (k, 2))を避けて、車体 [rear, rear + car_length] が丸ごと入る **後端の位置** の区間 (m, 2)。

    区間の端ちょうど(距離がちょうど 5 m など)は禁止の側に含める(「以内」)ので、車体が端に触れるだけなら許す
    (閉区間の補集合の閉包)。"""
    op = "legal_stop_intervals"
    M = _array(merged, "merged", op).reshape(-1, 2)
    r0 = _finite(road_start, "road_start", op)
    r1 = _finite(road_end, "road_end", op)
    Lv = _positive(car_length, "car_length", op)
    if r1 <= r0:
        raise ValueError("%s: road_end must be > road_start" % op)
    if np.any(M[:, 1] < M[:, 0]) or np.any(np.diff(M[:, 0]) < 0):
        raise ValueError("%s: merged must be sorted intervals with b >= a" % op)
    out = []
    cur = r0
    for a, b in M:
        if a > cur and min(a, r1) - cur >= Lv:
            out.append((cur, min(a, r1) - Lv))
        cur = max(cur, b)
        if cur >= r1:
            break
    if r1 - cur >= Lv:
        out.append((cur, r1 - Lv))
    return np.array(out, np.float64).reshape(-1, 2)


def parking_position_check(rear: float, front: float, zones_result: dict) -> Dict[str, object]:
    """車体 [rear, front] が駐停車禁止の区間に重なるか。``zones_result`` = ``no_stopping_zones`` の返り値。

    返り値: ``ok``、``overlap`` = 重なりの長さの最大 [m]、``reasons`` = 重なった区間の (kind, 号)。端に触れるだけは重ならない。"""
    op = "parking_position_check"
    r = _finite(rear, "rear", op)
    f = _finite(front, "front", op)
    if f <= r:
        raise ValueError("%s: front must be > rear" % op)
    if not isinstance(zones_result, dict) or "zones" not in zones_result:
        raise ValueError("%s: zones_result must come from no_stopping_zones" % op)
    reasons = []
    ov = 0.0
    for a, b, kind, art in zones_result["zones"]:
        o = min(f, b) - max(r, a)
        if o > 0:
            reasons.append((kind, art))
            ov = max(ov, o)
    return {"ok": not reasons, "overlap": ov, "reasons": reasons}
