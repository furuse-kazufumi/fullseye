# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""drivetown — 教習所の要素(:mod:`drivecourse`)を自動で継いで町を 1 つに組み、1 本の通し走行を採点する(自動運転 PoC 系列の集大成の土台)。

これまでの PoC は要素(交差点・踏切・坂道 …)を 1 つずつ置いて個別に採点してきた。集大成では **同じ要素を 1 本の道に継ぎ、
入口から出口まで通して走り、途中の停止線を全部採点する**。そのために要るのは「継ぐ規約」と「縦だけの運転」と「通しの門」と
「どの国の規則で走るか」で、どれも numpy だけで動く(学習なし、ルールベースだけ)。

継ぐ規約(:func:`town_chain`): 要素 k+1 の ``entry`` 姿勢を要素 k の ``exit`` 姿勢に合わせる剛体配置を閉形式で求める
(配置 p = target ∘ entry⁻¹)。継ぎ目は ``overlap``(既定 0.05 m)だけ食い込ませる —— 3-D 化(:mod:`driveworld`)で継ぎ目に
縁石が立たないための重なりで、examples/poc_driving_school.py の私的な ``tf`` / ``ahead`` を一般化した公開 op。
門 = 配置後の要素 k の exit と要素 k+1 の entry の位置差 = overlap(1e-9)、向きの差 = 0(1e-9)、中心線の総延長 = Σ centerline_length
− overlap × 継ぎ目数(直線だけの町では 1e-9、弧のある要素は折線の近似ぶん)。

中心線(:func:`town_centerline`): 各要素の中心線を継ぎ目で ``overlap`` だけ切り詰めて 1 本の折線にし、弧長 s で標本化した
``(N, 4) = (s, x, y, yaw)``。隣接点の間隔は直線部で厳密に ``step``。

法規パック(:func:`town_rules`): 通行の側(left / right)・踏切で止まる条件(always / when_active)・交差点の停止・保持時間・
左右確認の要否・出典・**一次確認の有無**を 1 つの dict にまとめる。JP は道路交通法 33 条 1 項(踏切の直前で停止し安全を確認)を
本文で確認済(``verified: True``)。US・DE は **条文の一次確認ができていない**(``verified: False``。数字・規則を断定しない。
US は一般車は警報中だけ停止・バスや危険物車両は常時停止とされる(49 CFR 392.10 と州法に拠るとされる二次情報)、DE は StVO §19 で
遮断機や灯火が動作している時は待つとされる二次情報)。停止線の選び方(:func:`town_stop_lines`)は ``side`` で切り替える:
左側通行なら中心線から **進行方向の左へ延びる** 停止線、右側通行なら右へ延びる物(交差点の 4 本のうち鏡像の 1 本が選ばれる)。
踏切の停止線は drivecourse が左車線にしか描かないので、右側通行では **踏切面 − stop_setback の閉形式** で位置を出す(白線は JP のまま)。

踏切の設備(:func:`town_world` が置く): 遮断機つき警報機 2 基(手前の左・向こうの右、柱 + クロスマーク + 赤色せん光灯 2 灯 × 両面)、
遮断かん(柱の高さ :data:`drivecrossing.BOOM_HEIGHT` = 0.8 m で水平に遮断、既定は **上がり**)、踏切の板、列車(4 両、既定は
遠くに待機)。メッシュは examples/poc_driving_crossing.py の私的な物を公開の形に写した。ラベルは既存の規約(柱・灯 = 3、
遮断かん = 4、板 = 0、列車 = 6)。:func:`town_crossing_state` が時刻 t の状態を既存 op :func:`drivecrossing.crossing_gate_state` /
:func:`drivecrossing.crossing_lamp_signal` で評価して書き込む(遮断かんの角・灯の交互点滅・列車の位置)。

運転(:func:`town_run`): 中心線に沿う **縦だけ** の運転。先の停止線を「止まっている先行車」と見なし、既存の
:func:`drivetraffic.idm_accel`(Treiber 2000 の IDM、s0 = 停止線の手前の余白)で減速し、止まったら保持(交差点 ``hold_s`` 秒、
踏切は左右確認 ``look_hold`` 秒 × 2 往復)の後に発進。積分は半陰的 Euler(v を先に更新、s は台形則)なので記録の ``∫v dt`` と ``s`` は
丸めまで一致し、記録の a = Δv/Δt は常に ``[−b_max, a_max]`` に入る。``train=(t_warning[, v_train[, length]])`` を渡すと踏切の
状態機械(警報 → 降下 → 遮断 → 列車 → 上昇。時刻は解釈基準の標準値 15 + 20 s、:func:`drivecrossing.crossing_timing_check` で最小値を
確認)が動き、**着いたとき警報中なら、遮断かんが上がって警報が止む(``entry_forbidden`` が消える)まで待ってから渡る**。
``crossing_stop == "when_active"`` の規則では踏切は警報中だけ目標になり、警報が始まった時に b_max で止まれない距離なら進む
(黄信号のジレンマと同じ扱い、drivecrossing の ``unavoidable``)。

採点(:func:`town_checks`): (a) どの停止線でも止まった位置が停止線の 0〜1.0 m 手前 (b) |a| ≤ max(a_max, b_max)、0 ≤ v ≤ v_max
(c) 台形則の ∫v dt と s の差 ≤ dt·v_max (d) 停止の回数 = 目標になった停止線の数 (e) 制動距離 ≥ v²/(2 b_max)(定理: 減速度が
b_max を超えないなら制動距離はこれ以上)。踏切は既存の :func:`drivecrossing.crossing_stop_check`(33 条 1 項・2 項、教則 6-1-1)を
**実際に呼ぶ**(軌跡 {t, x = 前端, v}・見た事象・警報中の区間を run から作る)。列車があれば、警報中に車体が踏切面にかかっていた
時間 = 0、発進は警報停止 + 上昇の後。第 2 実装の門(PoC・テスト): 同じ IDM 指令を :func:`drivelong.long_simulate`(RK4、事象で刻みを
切る)に渡し、止まった位置が dt·v_max 以内で一致。

台帳(:func:`kyosoku_summary`): docs/drive/kyosoku_scenarios.json(教則 159 場面の再現台帳)の category × status の件数表。
門 = 合計 159、tests/test_kyosoku_ledger.py の下限(reproduced ≥ 38、not_reproducible ≤ 10)と整合。

フレーム規約: :mod:`drivecourse` と同じ(x = 前/東、y = 左/北、m、rad、各要素は entry が原点・進入 +x)。走行の ``s`` は
**車の前端** の弧長(crossing_stop_check の x と同じ約束)。

限界(self_reported):
  * 縦だけの運転(横は中心線に貼り付け)。信号は「hold_s 秒待てば青」の規則で、灯火の色を読んで発進はしない
    (閉ループの読みは poc_driving_school.py の門 8)。他車・歩行者は置かない。
  * IDM の停止は漸近的(v → 0 に指数的に近づく)なので、「止まった」は ``v ≤ v_stop`` で切る。停止位置は余白 ``stop_margin``
    の手前に収まるが厳密に等しくはない —— 門は 0〜1.0 m の範囲で見る。
  * 継ぎ目は幅を揃えた突き合わせだけ(幅の違う要素を継ぐと縁石が道を横切る: driveworld の限界と同じ)。
  * 坂道は中心線の z だけ(:func:`drivecourse.slope_height`)で、縦の運動方程式に勾配は入れない(drivelong には入る)。
  * 踏切の時刻のうち、警報から降下の開始 7 s・降下 8 s・上昇 6 s は **仮定**(解釈基準にあるのは 15 s / 20 s の標準と最小だけ)。
    列車の長さ 80 m(4 両)・速さ 20 m/s も既定の仮定。右側通行でも世界の白線・柱の位置は JP の幾何のまま(鏡像は停止線の位置だけ)。
  * US / DE の規則は一次資料で確認していない(``verified: False``)。採点の数字(保持 2 s 等)は JP の値を流用している。

参考: Treiber, Hennecke, Helbing (2000) Congested traffic states in empirical observations and microscopic simulations, PRE 62.
道路交通法 33 条(踏切の通過)、交通の方法に関する教則 6-1-1。道路交通法施行規則 別表第三(コースの寸法、drivecourse)。
国土交通省 鉄道局「鉄道に関する技術上の基準を定める省令等の解釈基準」Ⅶ-9 第 62 条関係(踏切の時刻、drivecrossing.SOURCES)。
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

import drivecourse as _DC

__all__ = [
    "town_chain", "town_layout", "town_world", "town_crossing_state", "town_centerline", "town_stop_lines",
    "town_rules", "town_run", "town_checks", "kyosoku_summary",
    "TOWN_NAMES", "KYOSOKU_STATUSES", "RULE_PACKS", "TRAIN_DEFAULTS",
]

_TWO_PI = 2.0 * math.pi
TOWN_NAMES = ("default", "short")
KYOSOKU_STATUSES = ("reproduced", "partial", "pending", "not_reproducible")
_STOP_KINDS = ("intersection", "crossing", "stop_sign")      # 停止線を持つ要素の kind(drivecourse)+ 一時停止(drivejapan の経路)
_ON_LINE_TOL = 1e-6                              # 停止線の端点が中心線の上にあると見る距離 [m]
_MODES = ("cruise", "brake", "hold", "look", "wait")

#: 踏切の状態機械の既定(解釈基準の標準値 = 警報 → 遮断終了 15 s、遮断終了 → 到達 20 s。降下の開始 7 s・降下 8 s・上昇 6 s は仮定)
TRAIN_DEFAULTS: Dict[str, float] = {"v_train": 20.0, "length": 80.0, "t_lower_offset": 7.0, "lower_duration": 8.0,
                                    "raise_duration": 6.0, "margin": 1.0}

#: 法規パック。JP だけ条文を本文で確認(verified)。US / DE は二次情報で、数字・規則を断定しない(verified False)。
RULE_PACKS: Dict[str, dict] = {
    "JP": {
        "jurisdiction": "JP", "side": "left", "crossing_stop": "always", "intersection_stop": "signal",
        "hold_s": 2.0, "look_required": True, "look_hold_s": 1.0, "verified": True,
        "sources": ["道路交通法 33 条 1 項(踏切の直前で停止し、安全を確認した後でなければ進行してはならない)— e-Gov 本文で確認",
                    "道路交通法 33 条 2 項(遮断機が閉じようとし・閉じている間、警報機が警報している間は入らない)",
                    "交通の方法に関する教則 6-1-1(1)〜(5)"],
        "notes": "左側通行。信号機のある踏切は停止の免除あり(33 条 1 項ただし書き、本モジュールでは扱わない)。",
    },
    "US": {
        "jurisdiction": "US", "side": "right", "crossing_stop": "when_active", "intersection_stop": "signal",
        "hold_s": 2.0, "look_required": False, "look_hold_s": 1.0, "verified": False,
        "sources": ["一般車は警報・遮断機が動作中だけ停止(州の交通法。一次確認なし)",
                    "バス・危険物車両は常時停止とされる(49 CFR 392.10 と州法に拠る二次情報。本文は未確認)"],
        "notes": "右側通行。規則は二次情報。保持 2 s・確認なしは JP の値の流用 = 仮定。",
    },
    "DE": {
        "jurisdiction": "DE", "side": "right", "crossing_stop": "when_active", "intersection_stop": "signal",
        "hold_s": 2.0, "look_required": False, "look_hold_s": 1.0, "verified": False,
        "sources": ["StVO §19(Bahnübergänge): 遮断機・灯火が動作している時は待つ、とされる二次情報。本文は未確認"],
        "notes": "右側通行。規則は二次情報。保持 2 s は JP の値の流用 = 仮定。",
    },
}

# メッシュの色(examples/poc_driving_crossing.py と同じ)
_YELLOW = (0.95, 0.78, 0.10)
_BLACK = (0.08, 0.08, 0.09)
_DECK = (0.56, 0.55, 0.51)
_LAMP_ON = np.array([1.0, 0.12, 0.06])
_LAMP_OFF = np.array([0.22, 0.05, 0.05])
_BOOM_L = 3.5


# ----------------------------------------------------------------------------------------------------------------------
# 検査(fail-closed)
def _finite(v, name: str, op: str) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a finite number, got %r" % (op, name, v))
    if not math.isfinite(f):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, v))
    return f


def _positive(v, name: str, op: str) -> float:
    f = _finite(v, name, op)
    if f <= 0:
        raise ValueError("%s: %s must be > 0, got %r" % (op, name, v))
    return f


def _nonneg(v, name: str, op: str) -> float:
    f = _finite(v, name, op)
    if f < 0:
        raise ValueError("%s: %s must be >= 0, got %r" % (op, name, v))
    return f


def _pose3(p, name: str, op: str) -> Tuple[float, float, float]:
    a = np.asarray(p, np.float64).reshape(-1)
    if a.size != 3 or not np.all(np.isfinite(a)):
        raise ValueError("%s: %s must be a finite (x, y, yaw), got %r" % (op, name, p))
    return float(a[0]), float(a[1]), float(a[2])


def _check_element(e, k: int, op: str) -> dict:
    if not isinstance(e, dict) or e.get("kind") == "layout" or e.get("polygon") is None:
        raise ValueError("%s: element %d must be a single course dict with a polygon (nested layouts are not supported)" % (op, k))
    for key in ("entry", "exit", "centerline", "centerline_length"):
        if key not in e:
            raise ValueError("%s: element %d (%s) has no %r" % (op, k, e.get("kind"), key))
    C = np.asarray(e["centerline"], np.float64)
    if C.ndim != 2 or C.shape[1] != 2 or C.shape[0] < 2 or not np.all(np.isfinite(C)):
        raise ValueError("%s: element %d (%s) centerline must be a finite (L >= 2, 2) array" % (op, k, e.get("kind")))
    return e


def _is_route(layout) -> bool:
    """drivejapan.osm_route の返り値(折線 ``polyline`` と弧長 ``cum``、停止線 ``stop_lines``)か。"""
    return isinstance(layout, dict) and layout.get("kind") == "route" and all(k in layout for k in ("polyline", "cum", "stop_lines"))


def _check_layout(layout, op: str) -> dict:
    if _is_route(layout):
        P = np.asarray(layout["polyline"], np.float64)
        c = np.asarray(layout["cum"], np.float64)
        if P.ndim != 2 or P.shape[1] != 2 or len(P) < 2 or c.shape != (len(P),) or not np.all(np.diff(c) >= 0) or c[-1] <= 0:
            raise ValueError("%s: route must have a polyline (K>=2, 2) with a non-decreasing arc length cum of positive total" % op)
        return layout
    if not isinstance(layout, dict) or layout.get("kind") != "layout" or "chain" not in layout:
        raise ValueError("%s: layout must come from town_chain (a course_layout dict with a 'chain' record)" % op)
    ch = layout["chain"]
    if len(layout["elements"]) != len(ch["s_start"]):
        raise ValueError("%s: layout 'chain' record does not match its elements" % op)
    return layout


def _check_side(side, op: str) -> str:
    if side not in ("left", "right"):
        raise ValueError("%s: side must be 'left' or 'right', got %r" % (op, side))
    return side


def _check_rules(rules, op: str) -> dict:
    if rules is None:
        return town_rules("JP")
    if not isinstance(rules, dict):
        raise ValueError("%s: rules must be the dict returned by town_rules" % op)
    for key in ("jurisdiction", "side", "crossing_stop", "intersection_stop", "hold_s", "look_required", "look_hold_s", "verified"):
        if key not in rules:
            raise ValueError("%s: rules has no %r (use town_rules)" % (op, key))
    _check_side(rules["side"], op)
    if rules["crossing_stop"] not in ("always", "when_active"):
        raise ValueError("%s: rules['crossing_stop'] must be 'always' or 'when_active'" % op)
    if rules["intersection_stop"] not in ("signal",):
        raise ValueError("%s: rules['intersection_stop'] must be 'signal'" % op)
    _nonneg(rules["hold_s"], "rules['hold_s']", op)
    _positive(rules["look_hold_s"], "rules['look_hold_s']", op)
    return rules


# ----------------------------------------------------------------------------------------------------------------------
# 姿勢と折線の小道具
def _wrap(x: float) -> float:
    y = x - _TWO_PI * math.floor((x + math.pi) / _TWO_PI)
    return y + _TWO_PI if y <= -math.pi else y


def _compose(p, q) -> Tuple[float, float, float]:
    """配置 p(剛体運動)の下での局所姿勢 q の世界姿勢(poc_driving_school の tf)。"""
    x, y, yaw = p
    c, s = math.cos(yaw), math.sin(yaw)
    return (x + c * q[0] - s * q[1], y + s * q[0] + c * q[1], _wrap(yaw + q[2]))


def _ahead(pose, d: float) -> Tuple[float, float, float]:
    x, y, yaw = pose
    return (x + d * math.cos(yaw), y + d * math.sin(yaw), yaw)


def _placement_for(entry, target) -> Tuple[float, float, float]:
    """``_compose(p, entry) == target`` となる配置 p(閉形式: p = target ∘ entry⁻¹)。"""
    yaw = target[2] - entry[2]
    c, s = math.cos(yaw), math.sin(yaw)
    return (target[0] - (c * entry[0] - s * entry[1]), target[1] - (s * entry[0] + c * entry[1]), yaw)


def _to_world3(V, placement) -> np.ndarray:
    """局所の 3-D 点 (N, 3) を要素の配置 (x, y, yaw) で世界へ(z は不変)。"""
    x, y, yaw = placement
    c, s = math.cos(yaw), math.sin(yaw)
    V = np.asarray(V, np.float64)
    out = V.copy()
    out[:, 0] = c * V[:, 0] - s * V[:, 1] + x
    out[:, 1] = s * V[:, 0] + c * V[:, 1] + y
    return out


def _clean_polyline(P: np.ndarray) -> np.ndarray:
    """長さ 0 の辺(重複点)を落とす。"""
    P = np.asarray(P, np.float64)
    if len(P) < 2:
        return P
    keep = [0]
    for i in range(1, len(P)):
        if np.hypot(*(P[i] - P[keep[-1]])) > 1e-12:
            keep.append(i)
    return P[keep]


def _cum(P: np.ndarray) -> np.ndarray:
    return np.r_[0.0, np.cumsum(np.hypot(np.diff(P[:, 0]), np.diff(P[:, 1])))]


def _cut_front(P: np.ndarray, d: float) -> np.ndarray:
    """折線の先頭から弧長 d を切り落とす。"""
    if d <= 0:
        return P
    c = _cum(P)
    if d >= c[-1] - 1e-12:
        raise ValueError("drivetown: overlap %g is not shorter than an element centerline (%g)" % (d, c[-1]))
    i = int(np.searchsorted(c, d, side="right")) - 1
    u = (P[i + 1] - P[i]) / (c[i + 1] - c[i])
    start = P[i] + u * (d - c[i])
    return np.vstack([start[None, :], P[i + 1:]])


def _point_at(P: np.ndarray, c: np.ndarray, s) -> np.ndarray:
    """折線 P(累積弧長 c)の弧長 s の点と向き → (..., 3) = (x, y, yaw)。端の外は端の辺で延長する。"""
    s = np.asarray(s, np.float64)
    i = np.clip(np.searchsorted(c, s, side="right") - 1, 0, len(P) - 2)
    d = P[i + 1] - P[i]
    L = np.hypot(d[..., 0], d[..., 1])
    u = d / L[..., None]
    xy = P[i] + u * (s - c[i])[..., None]
    yaw = np.arctan2(u[..., 1], u[..., 0])
    return np.concatenate([xy, yaw[..., None]], axis=-1)


def _project(P: np.ndarray, c: np.ndarray, pt) -> Tuple[float, float]:
    """点から折線への最短距離と、その最近点の弧長。"""
    q = np.asarray(pt, np.float64)
    A, B = P[:-1], P[1:]
    d = B - A
    L2 = np.sum(d * d, axis=1)
    t = np.clip(np.sum((q - A) * d, axis=1) / L2, 0.0, 1.0)
    foot = A + d * t[:, None]
    dist = np.hypot(*(foot - q).T)
    j = int(np.argmin(dist))
    return float(dist[j]), float(c[j] + t[j] * math.sqrt(L2[j]))


# ----------------------------------------------------------------------------------------------------------------------
# 1. 継ぐ
def town_chain(elements, *, start=(0.0, 0.0, 0.0), overlap: float = 0.05) -> dict:
    """要素を順に継いで配置する: 要素 k+1 の entry を要素 k の exit(の ``overlap`` 手前)に合わせる剛体配置を閉形式で求め、
    :func:`drivecourse.course_layout` に渡す。

    Parameters
    ----------
    elements : drivecourse の要素(dict)の列。順に継ぐ。
    start : 最初の要素の entry を置く世界姿勢 (x, y, yaw)。
    overlap : 継ぎ目の食い込み [m](≥ 0。3-D 化で継ぎ目に縁石が立たないため)。要素の中心線より短いこと。

    Returns
    -------
    dict : course_layout の dict に ``"chain"`` を足したもの。``chain = {"overlap", "s_start" (n,) 各要素の entry の
    弧長, "lengths" (n,) 各要素の centerline_length, "polyline_lengths" (n,) 中心線の折線長, "total_length"
    (= Σ 折線長 − overlap × (n − 1)), "joints": [(exit_k, entry_k+1), ...] 世界姿勢}``。

    **Raises** ``ValueError``: 要素が空・layout の入れ子・entry/exit/centerline が無い、start/overlap が非有限、overlap が負、
    overlap が要素の中心線より長い。"""
    op = "town_chain"
    if not isinstance(elements, (list, tuple)) or len(elements) == 0:
        raise ValueError("%s: elements must be a non-empty list of course dicts" % op)
    ov = _nonneg(overlap, "overlap", op)
    target = _pose3(start, "start", op)
    placements, exits = [], []
    for k, e in enumerate(elements):
        _check_element(e, k, op)
        if k > 0 and ov >= float(e["centerline_length"]):
            raise ValueError("%s: overlap %g must be shorter than element %d centerline (%g)" % (op, ov, k, e["centerline_length"]))
        p = _placement_for(e["entry"], target)
        placements.append(p)
        ex = _compose(p, e["exit"])
        exits.append(ex)
        target = _ahead(ex, -ov)
    layout = _DC.course_layout(list(elements), placements)
    lengths = np.array([float(e["centerline_length"]) for e in elements])
    plen = np.array([_cum(_clean_polyline(e["centerline"]))[-1] for e in layout["elements"]])
    s_start = np.r_[0.0, np.cumsum(plen[:-1] - ov)]
    joints = [(exits[k], tuple(layout["elements"][k + 1]["entry"])) for k in range(len(elements) - 1)]
    layout["chain"] = {"overlap": ov, "s_start": s_start, "lengths": lengths, "polyline_lengths": plen,
                       "total_length": float(plen.sum() - ov * (len(elements) - 1)), "joints": joints,
                       "start": tuple(_pose3(start, "start", op))}
    return layout


def town_layout(name: str = "default", *, overlap: float = 0.05) -> dict:
    """既定の町。``"default"`` = road(30) → intersection → road(20) → crossing(踏切) → road(20) → slope → road(20) →
    parallel_parking → road(30)(全部幅 7 m、停止線は交差点 1 本と踏切 1 本)。``"short"`` = road(20) → crossing → road(20)
    (テストの速い門)。

    **Raises** ``ValueError``: 名前が :data:`TOWN_NAMES` に無い。"""
    op = "town_layout"
    if name == "default":
        els = [_DC.course_road(30.0), _DC.course_intersection(), _DC.course_road(20.0), _DC.course_crossing(),
               _DC.course_road(20.0), _DC.course_slope(), _DC.course_road(20.0), _DC.course_parallel_parking(),
               _DC.course_road(30.0)]
    elif name == "short":
        els = [_DC.course_road(20.0), _DC.course_crossing(), _DC.course_road(20.0)]
    else:
        raise ValueError("%s: name must be one of %s, got %r" % (op, TOWN_NAMES, name))
    out = town_chain(els, overlap=overlap)
    out["name"] = name
    return out


# ----------------------------------------------------------------------------------------------------------------------
# 2. 中心線と停止線
def _chain_polyline(layout: dict) -> Tuple[np.ndarray, np.ndarray]:
    """継いだ中心線 1 本(継ぎ目で overlap を切り詰め)と累積弧長。"""
    op = "town_centerline"
    ov = float(layout["chain"]["overlap"])
    parts = []
    for k, e in enumerate(layout["elements"]):
        C = _clean_polyline(e["centerline"])
        if k > 0:
            C = _cut_front(C, ov)
            prev = parts[-1][-1]
            if np.hypot(*(C[0] - prev)) > 1e-6:
                raise ValueError("%s: element %d centerline does not start at the previous exit (gap %.3g m)"
                                 % (op, k, float(np.hypot(*(C[0] - prev)))))
            C = C[1:]
        parts.append(C)
    P = _clean_polyline(np.vstack(parts))
    return P, _cum(P)


def town_centerline(layout, step: float = 0.5) -> np.ndarray:
    """継いだ中心線を弧長 ``step`` ごとに標本化する → ``(N, 4) = (s, x, y, yaw)``(終点は必ず含む)。

    門: 直線部では隣接点の間隔が厳密に step、始点 = 最初の要素の entry、終点 = 最後の要素の exit。

    **Raises** ``ValueError``: layout が town_chain の物でない、step が正でない。"""
    op = "town_centerline"
    _check_layout(layout, op)
    st = _positive(step, "step", op)
    P, c = _chain_polyline(layout)
    L = float(c[-1])
    n = int(math.floor(L / st + 1e-9))
    s = np.arange(n + 1, dtype=np.float64) * st
    if L - s[-1] > 1e-9:
        s = np.r_[s, L]
    xyz = _point_at(P, c, s)
    return np.column_stack([s, xyz])


def town_stop_lines(layout, *, side: str = "left") -> List[dict]:
    """町の停止線を弧長順に並べる: ``[{"s", "x", "y", "yaw", "kind", "element", "crossing_zone": (s0, s1) | None,
    "drawn": bool}, ...]``。

    交差点: 要素の ``stop_lines``(線分 (2, 2))のうち **中心線に端点が載り、進行方向の ``side`` の側へ延びる物** が走行路の
    停止線(4 本のうち 1 本。左側通行なら左、右側通行なら鏡像の 1 本)。踏切: 停止線の位置は **踏切面 − stop_setback の閉形式**
    (drivecourse は左車線にしか白線を描かないので side に依らない。``drawn`` = その側に白線が描かれているか)。
    ``s`` は中心線上の弧長、``yaw`` はそこでの進行方向。踏切は踏切面の弧長の範囲 ``crossing_zone`` も付ける。

    **Raises** ``ValueError``: layout が town_chain の物でない、side が left/right でない。"""
    op = "town_stop_lines"
    _check_layout(layout, op)
    _check_side(side, op)
    sgn = 1.0 if side == "left" else -1.0
    P, c = _chain_polyline(layout)
    s_start = layout["chain"]["s_start"]
    out = []
    for k, e in enumerate(layout["elements"]):
        kind = str(e.get("kind"))
        if kind == "crossing" and "crossing_zone" in e:
            z0, z1 = (float(v) for v in e["crossing_zone"])
            sb = float(e.get("params", {}).get("stop_setback", 0.0))
            s_line = float(s_start[k] + z0 - sb)
            pose = _point_at(P, c, s_line)
            drawn = False
            for seg in np.asarray(e.get("stop_lines", np.zeros((0, 2, 2))), np.float64).reshape(-1, 2, 2):
                proj = [_project(P, c, pt) for pt in seg]
                hits = [i for i in range(2) if proj[i][0] <= _ON_LINE_TOL and abs(proj[i][1] - s_line) <= 1e-6]
                if hits:
                    other = seg[1 - hits[0]] - pose[:2]
                    drawn = drawn or sgn * (-math.sin(pose[2]) * other[0] + math.cos(pose[2]) * other[1]) > _ON_LINE_TOL
            out.append({"s": s_line, "x": float(pose[0]), "y": float(pose[1]), "yaw": float(pose[2]), "kind": kind,
                        "element": k, "crossing_zone": (float(s_start[k] + z0), float(s_start[k] + z1)), "drawn": drawn})
            continue
        sl = e.get("stop_lines")
        if sl is None:
            continue
        for seg in np.asarray(sl, np.float64).reshape(-1, 2, 2):
            proj = [_project(P, c, pt) for pt in seg]
            hits = [i for i in range(2) if proj[i][0] <= _ON_LINE_TOL]
            if not hits:
                continue
            i_on = hits[0]
            s_line = proj[i_on][1]
            pose = _point_at(P, c, s_line)
            # 走行路の停止線は中心線から **進行方向の side の側** へ延びる(反対側は対向車線の停止線 → 除く)
            other = seg[1 - i_on] - pose[:2]
            if sgn * (-math.sin(pose[2]) * other[0] + math.cos(pose[2]) * other[1]) <= _ON_LINE_TOL:
                continue
            out.append({"s": float(s_line), "x": float(pose[0]), "y": float(pose[1]), "yaw": float(pose[2]),
                        "kind": kind, "element": k, "crossing_zone": None, "drawn": True})
    out.sort(key=lambda d: d["s"])
    return out


# ----------------------------------------------------------------------------------------------------------------------
# 3. 法規パック
def town_rules(jurisdiction: str = "JP") -> dict:
    """法規パック(:data:`RULE_PACKS` の複製)。``{"jurisdiction", "side": "left"|"right", "crossing_stop": "always"|"when_active",
    "intersection_stop": "signal", "hold_s", "look_required", "look_hold_s", "sources": [...], "verified", "notes"}``。

    JP = 左側通行・踏切は常に一時停止 + 安全確認(道路交通法 33 条 1 項、本文で確認済 → verified True)。
    US = 右側通行・一般車は警報中だけ停止(州法。**一次確認なし → verified False**)。DE = 右側通行・StVO §19 で遮断機/灯火が
    動作している時だけ(**一次確認なし → verified False**)。verified が False の規則は PoC・報告で断定しない。

    **Raises** ``ValueError``: 知らない jurisdiction。"""
    op = "town_rules"
    if jurisdiction not in RULE_PACKS:
        raise ValueError("%s: jurisdiction must be one of %s, got %r" % (op, tuple(RULE_PACKS), jurisdiction))
    r = dict(RULE_PACKS[jurisdiction])
    r["sources"] = list(r["sources"])
    return r


# ----------------------------------------------------------------------------------------------------------------------
# 4. 世界(踏切の設備つき)
def _box_mesh(L, W, H, z0=0.0):
    """x 長さ L・y 幅 W・高さ H の箱(底面の中心が原点、z0 から)。"""
    V = np.array([[x, y, z] for z in (z0, z0 + H) for y in (-W / 2, W / 2) for x in (-L / 2, L / 2)], np.float64)
    F = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4],
                  [1, 5, 7], [1, 7, 3]], np.int64)
    return V, F


def _mesh(parts):
    V = np.zeros((0, 3))
    F = np.zeros((0, 3), np.int64)
    C = []
    for v, f, c in parts:
        F = np.vstack([F, f + len(V)])
        V = np.vstack([V, v])
        C.append(np.tile(np.asarray(c, np.float64), (len(f), 1)))
    return V, F, np.vstack(C)


def _quad(xa, xb, ya, yb, z=0.006):
    return np.array([[xa, ya, z], [xb, ya, z], [xb, yb, z], [xa, yb, z]], np.float64), np.array([[0, 1, 2], [0, 2, 3]], np.int64)


def _vquad_x(x, ya, yb, za, zb):
    """x = 一定の縦の面(法線 ±x)。"""
    return np.array([[x, ya, za], [x, yb, za], [x, yb, zb], [x, ya, zb]], np.float64), np.array([[0, 1, 2], [0, 2, 3]], np.int64)


def _rot_x(V, ang, about):
    c, s = math.cos(ang), math.sin(ang)
    R = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    return (V - about) @ R.T + about


def _boom_vertices(pivot, sgn, theta, n_seg=4):
    """遮断かん(4 区間の箱、黄黒)の局所頂点。theta = π/2 で上、0 で水平(道を横切る向き = y 方向に sgn)。"""
    d = np.array([0.0, sgn * math.cos(theta), math.sin(theta)])
    nrm = np.array([0.0, -sgn * math.sin(theta), math.cos(theta)])
    e = np.array([1.0, 0.0, 0.0])
    h = 0.045
    out = []
    for k in range(n_seg):
        a0, a1 = _BOOM_L * k / n_seg, _BOOM_L * (k + 1) / n_seg
        for b in (-h, h):
            for cx in (-h, h):
                for a in (a0, a1):
                    out.append(pivot + a * d + cx * e + b * nrm)
    return np.array(out)


def _train_mesh(n_cars: int = 4):
    """列車(+y に進む、先頭の端が y = 0、車体は y < 0 へ)。"""
    parts = []
    for k in range(n_cars):
        yc = -(k + 0.5) * 20.0
        v, f = _box_mesh(2.9, 19.6, 3.4, 0.45)
        parts.append((v + [0, yc, 0], f, (0.80, 0.82, 0.84)))
        for sx in (-1, 1):
            v, f = _box_mesh(0.04, 18.0, 0.7, 2.1)
            parts.append((v + [sx * 1.47, yc, 0], f, (0.12, 0.14, 0.18)))
            v, f = _box_mesh(0.04, 19.4, 0.25, 1.3)
            parts.append((v + [sx * 1.47, yc, 0], f, (0.10, 0.50, 0.30)))
    v, f = _box_mesh(2.5, 0.05, 1.0, 2.0)
    parts.append((v + [0, 0.01, 0], f, (0.12, 0.14, 0.18)))
    return _mesh(parts)


def _add_crossing_gear(world: dict, el: dict, k: int) -> dict:
    """踏切の要素 1 つに、板・遮断機つき警報機 2 基・遮断かん(上がり)・列車(遠くに待機)を足す。局所 → 世界は要素の配置で。"""
    import driveworld as DW
    import drivecrossing as DX
    pl = el["placement"]
    x0, x1 = (float(v) for v in el["crossing_zone"])
    h = 0.5 * float(el["width"])
    gear = {"element": k, "placement": tuple(pl), "zone": (x0, x1), "half_width": h, "posts": [], "lamps": [], "booms": []}
    V, F = _quad(x0, x1, -h, h, z=0.004)
    gear["deck"] = DW.world_add(world, _to_world3(V, pl), F, 0, _DECK, name="deck")
    # 柱: 手前の左(自分の側、停止線のすぐ先)と向こう側の右(対向車の側)。縁石(0.3 m)の外 = 中心から h + 0.5
    for px, py in ((x0 - 0.3, h + 0.5), (x1 + 0.3, -(h + 0.5))):
        parts = []
        v, f = _box_mesh(0.16, 0.16, 3.3)
        parts.append((v + [px, py, 0], f, _YELLOW))
        for z0 in np.arange(0.2, 1.8, 0.5):
            v, f = _box_mesh(0.17, 0.17, 0.25, z0)
            parts.append((v + [px, py, 0], f, _BLACK))
        v, f = _box_mesh(0.10, 1.10, 0.10, 2.48)
        parts.append((v + [px, py, 0], f, _BLACK))
        for ang in (0.7, -0.7):                              # クロスマーク(黄)
            v, f = _box_mesh(0.05, 1.3, 0.20, -0.10)
            parts.append((_rot_x(v, ang, np.zeros(3)) + [px, py, 3.05], f, _YELLOW))
        Vp, Fp, Cp = _mesh(parts)
        gear["posts"].append(DW.world_add(world, _to_world3(Vp, pl), Fp, 3, Cp, name="crossing_post"))
        for face in (-1.0, 1.0):
            for kk, dy in ((0, 0.35), (1, -0.35)):           # 2 灯(交互点滅: 列 0 / 1)、両面
                V, F = _vquad_x(px + face * 0.09, py + dy - 0.15, py + dy + 0.15, 2.08, 2.38)
                i = DW.world_add(world, _to_world3(V, pl), F, 3, _LAMP_OFF, name="crossing_lamp")
                gear["lamps"].append((world["objects"][i]["faces"], kk))
                V, F = _vquad_x(px + face * 0.085, py + dy - 0.2, py + dy + 0.2, 2.03, 2.43)
                DW.world_add(world, _to_world3(V, pl), F, 3, _BLACK, name="crossing_lamp_back")
        sgn = -1.0 if py > 0 else 1.0
        pivot = np.array([px, py, DX.BOOM_HEIGHT])
        Vb = _boom_vertices(pivot, sgn, 0.5 * math.pi)
        Fb = np.vstack([_box_mesh(1, 1, 1)[1] + 8 * j for j in range(4)])
        Cb = np.vstack([np.tile(_YELLOW if j % 2 == 0 else _BLACK, (12, 1)) for j in range(4)])
        i = DW.world_add(world, _to_world3(Vb, pl), Fb, 4, Cb, name="boom")
        gear["booms"].append((i, pivot, sgn))
    Vt, Ft, Ct = _train_mesh()
    xc = 0.5 * (x0 + x1)
    gear["train_local"] = Vt
    gear["track_x"] = xc
    gear["train"] = DW.world_add(world, _to_world3(Vt + [xc, -400.0, 0.0], pl), Ft, 6, Ct, name="train")
    gear["train_y"] = -400.0
    gear["state"] = 0
    gear["boom_angle"] = 0.5 * math.pi
    return gear


def town_world(layout, *, props=(), **kwargs) -> dict:
    """:func:`driveworld.world_build` の薄い包み(``props`` と残りの引数をそのまま渡す)に、停止線・信号・踏切の位置の表を
    ``world["town"]`` として足し、踏切の要素ごとに **遮断機つき警報機 2 基・遮断かん(上がり)・踏切の板・列車(遠くに待機)** を置く。

    ``world["town"] = {"stop_lines": [(x, y, yaw, kind)], "signals": [(x, y, yaw, kind)], "crossings": [(x0, y0, x1, y1, s0, s1)],
    "gear": [踏切ごとの設備の索引 dict], "total_length"}``(signals は交差点の 4 基全部、yaw = 灯器が向く向き。stop_lines は
    左側通行の物)。設備の状態は :func:`town_crossing_state` で時刻ごとに書き換える。

    **Raises** ``ValueError``: layout が town_chain の物でない(world_build の例外はそのまま)。"""
    op = "town_world"
    _check_layout(layout, op)
    import driveworld as DW
    world = DW.world_build(layout, props=props, **kwargs)
    stops = [(d["x"], d["y"], d["yaw"], d["kind"]) for d in town_stop_lines(layout)]
    signals, crossings, gear = [], [], []
    P, c = _chain_polyline(layout)
    for k, e in enumerate(layout["elements"]):
        for sp in np.asarray(e.get("signal_poses", np.zeros((0, 3))), np.float64).reshape(-1, 3):
            signals.append((float(sp[0]), float(sp[1]), float(sp[2]), str(e.get("kind"))))
        if e.get("kind") == "crossing" and "crossing_zone" in e:
            gear.append(_add_crossing_gear(world, e, k))
    for d in town_stop_lines(layout):
        if d["crossing_zone"] is not None:
            a = _point_at(P, c, d["crossing_zone"][0])
            b = _point_at(P, c, d["crossing_zone"][1])
            crossings.append((float(a[0]), float(a[1]), float(b[0]), float(b[1]), d["crossing_zone"][0], d["crossing_zone"][1]))
    world["town"] = {"stop_lines": stops, "signals": signals, "crossings": crossings, "gear": gear,
                     "total_length": float(layout["chain"]["total_length"])}
    return world


def town_crossing_state(world: dict, t: float, train: Optional[dict], *, exposure: float = 0.0) -> Dict[str, object]:
    """時刻 t の踏切の設備を世界に書き込む(全部の踏切に同じ列車の時刻を使う)。

    ``train`` = :func:`town_run` の ``run["train"]``(None = 待機: かん上・灯消灯・列車は遠く)。状態は既存 op
    :func:`drivecrossing.crossing_gate_state`(警報 → 降下 → 遮断 → 上昇、かんの角)と :func:`drivecrossing.crossing_lamp_signal`
    (2 灯の交互点滅、``exposure`` > 0 でカメラの露光平均)で評価する。列車の先頭は ``t_arrival`` に道路の縁(手前 margin)に着き、
    ``v_train`` で +y(局所)へ進む。返り値 ``{"state", "state_name", "boom_angle", "lamps", "entry_forbidden", "train_y"}``。

    **Raises** ``ValueError``: world が town_world の物でない、t が非有限、train の鍵が足りない。"""
    op = "town_crossing_state"
    if not isinstance(world, dict) or "town" not in world or "gear" not in world["town"]:
        raise ValueError("%s: world must come from town_world" % op)
    tt = _finite(t, "t", op)
    import drivecrossing as DX
    if train is None:
        st, ang, lam, forb, y_head = 0, 0.5 * math.pi, np.zeros(2), False, -400.0
    else:
        for key in ("t_warning", "t_lower_start", "lower_duration", "t_clear", "raise_duration", "t_arrival", "v_train", "margin"):
            if key not in train:
                raise ValueError("%s: train has no %r (use town_run(..., train=...)['train'])" % (op, key))
        g = DX.crossing_gate_state(np.array([tt]), t_warning=train["t_warning"], t_lower_start=train["t_lower_start"],
                                   lower_duration=train["lower_duration"], t_clear=train["t_clear"], raise_duration=train["raise_duration"])
        st, ang, forb = int(g["state"][0]), float(g["boom_angle"][0]), bool(g["entry_forbidden"][0])
        lam = DX.crossing_lamp_signal(np.array([tt]), t_on=train["t_warning"], t_off=train["t_clear"], exposure=exposure)[0]
        y_head = None
    for gear in world["town"]["gear"]:
        pl = gear["placement"]
        for i, pivot, sgn in gear["booms"]:
            v0, v1 = world["objects"][i]["verts"]
            world["V"][v0:v1] = _to_world3(_boom_vertices(pivot, sgn, ang), pl)
        for (f0, f1), kk in gear["lamps"]:
            world["face_color"][f0:f1] = _LAMP_OFF + (_LAMP_ON - _LAMP_OFF) * float(lam[kk])
        if y_head is None:
            yh = -(gear["half_width"] + train["margin"]) + train["v_train"] * (tt - train["t_arrival"])
            yh = float(np.clip(yh, -400.0, 400.0))
        else:
            yh = y_head
        v0, v1 = world["objects"][gear["train"]]["verts"]
        world["V"][v0:v1] = _to_world3(gear["train_local"] + [gear["track_x"], yh, 0.0], pl)
        gear["train_y"], gear["state"], gear["boom_angle"] = yh, st, ang
    return {"state": st, "state_name": DX.GATE_STATES[st], "boom_angle": ang, "lamps": lam, "entry_forbidden": forb,
            "train_y": world["town"]["gear"][0]["train_y"] if world["town"]["gear"] else None}


# ----------------------------------------------------------------------------------------------------------------------
# 5. 走る
def _ground_z(layout: dict, s) -> np.ndarray:
    """弧長 s の路面高(坂道要素の profile だけが z > 0)。"""
    s = np.asarray(s, np.float64)
    z = np.zeros_like(s)
    if _is_route(layout):
        return z
    s_start = layout["chain"]["s_start"]
    for k, e in enumerate(layout["elements"]):
        if e.get("kind") == "slope" and "profile" in e:
            loc = s - s_start[k]
            m = (loc >= 0) & (loc <= float(layout["chain"]["polyline_lengths"][k]))
            if np.any(m):
                z[m] = _DC.slope_height(e, loc[m])
    return z


def _train_timing(train, road_width: float, op: str) -> Optional[dict]:
    """``train`` = 数 | (t_warning[, v_train[, length]]) | dict → 状態機械の時刻の dict(解釈基準の標準値、最小値を既存 op で確認)。"""
    if train is None:
        return None
    import drivecrossing as DX
    d = dict(TRAIN_DEFAULTS)
    if isinstance(train, dict):
        d.update(train)
        if "t_warning" not in d:
            raise ValueError("%s: train dict needs 't_warning'" % op)
    else:
        seq = (train,) if np.isscalar(train) else tuple(train)
        if len(seq) < 1 or len(seq) > 3:
            raise ValueError("%s: train must be t_warning or (t_warning[, v_train[, length]])" % op)
        d["t_warning"] = seq[0]
        if len(seq) > 1:
            d["v_train"] = seq[1]
        if len(seq) > 2:
            d["length"] = seq[2]
    tw = _finite(d["t_warning"], "train t_warning", op)
    vt = _positive(d["v_train"], "train v_train", op)
    ln = _positive(d["length"], "train length", op)
    T = DX.CROSSING_TIMING
    t_lower = tw + _nonneg(d["t_lower_offset"], "t_lower_offset", op)
    ld = _positive(d["lower_duration"], "lower_duration", op)
    t_closed = tw + T["warn_to_closed_std"]
    if abs(t_lower + ld - t_closed) > 1e-9:
        raise ValueError("%s: t_lower_offset + lower_duration must equal warn_to_closed_std (%g s)" % (op, T["warn_to_closed_std"]))
    t_arr = t_closed + T["closed_to_arrival_std"]
    margin = _nonneg(d["margin"], "margin", op)
    t_clear = t_arr + (ln + road_width + 2.0 * margin) / vt
    chk = DX.crossing_timing_check(tw, t_closed, t_arr)
    if not chk["meets_minimum"]:
        raise ValueError("%s: crossing timing does not meet the interpretation-standard minimum" % op)
    return {"t_warning": tw, "t_lower_start": t_lower, "lower_duration": ld, "t_closed": t_closed, "t_arrival": t_arr,
            "t_clear": t_clear, "raise_duration": _positive(d["raise_duration"], "raise_duration", op), "v_train": vt,
            "length": ln, "margin": margin, "road_width": road_width, "timing_check": chk,
            "forbidden_interval": (tw, t_clear + float(d["raise_duration"]))}


def _forbidden(train: Optional[dict], t: float) -> bool:
    if train is None:
        return False
    return train["t_warning"] <= t < train["forbidden_interval"][1]


def town_run(layout, *, dt: float = 0.05, v_max: float = 8.0, a_max: float = 1.5, b_max: float = 3.0,
             stop_at: Optional[Sequence[str]] = None, stop_hold: Optional[float] = None, look_hold: Optional[float] = None,
             stop_margin: float = 0.5, idm_T: float = 1.0, v_stop: Optional[float] = None,
             t_max: Optional[float] = None, rules: Optional[dict] = None, train=None) -> Dict[str, object]:
    """中心線に沿う縦だけの通し走行(ルールベース)。

    各刻みで、まだ止まっていない次の **目標の停止線** を「止まっている先行車」と見なし、
    ``drivetraffic.idm_accel(v, gap = 停止線 − 前端, dv = v, v0 = v_max, T = idm_T, a = a_max, b = b_max, s0 = stop_margin)``
    で加速度を出し ``[−b_max, a_max]`` に切る(目標が無ければ gap = ∞ = 自由走行)。v を先に更新(0 ≤ v ≤ v_max)、s は台形則。
    ``v ≤ v_stop`` かつ前端が停止線の 1.0 m 以内なら停止。

    目標の決まり方(``rules`` = :func:`town_rules`、None = JP): 交差点は常に目標(信号は ``stop_hold`` 秒で青の規則)。踏切は
    ``rules["crossing_stop"]`` が "always" なら常に、"when_active" なら ``train`` の警報中(``entry_forbidden``)だけ目標。
    "when_active" で警報が始まった時に b_max で止まれない(gap < v²/(2 b_max))なら進む(event "commit")。``stop_at`` を渡すと
    規則より優先する(kind の列。回帰用)。停止後: 交差点は ``stop_hold``(既定 rules["hold_s"])秒保持(mode "hold")、踏切は
    ``rules["look_required"]`` なら左・右・左・右を各 ``look_hold``(既定 rules["look_hold_s"])秒見る(mode "look")。``train`` が
    あれば、保持が明けても警報中(かん降下〜上昇中)は待つ(mode "wait")。``train`` = t_warning か (t_warning[, v_train[, length]])
    か dict(時刻は解釈基準の標準値、:data:`TRAIN_DEFAULTS`)。

    Returns
    -------
    dict : ``t, s, x, y, z, v, yaw, a`` (各 (n,))、``mode`` (n,) 文字列("cruise" / "brake" / "hold" / "look" / "wait")、
    ``stops`` = [(s_stop, kind, t_arrive, t_leave), ...]、``events`` = [("stop"|"go"|"look"|"wait_gate"|"commit"|"pass"|"end", t, ...)]、
    ``stop_lines``(目標になり得た停止線)、``targets``(停止線ごとの "static" / "dynamic")、``train``(時刻の dict か None)、
    ``rules``、``params``、``total_length``。

    **Raises** ``ValueError``: layout が town_chain の物でも drivejapan.osm_route の "route" でもない、dt/v_max/a_max/b_max/保持時間が不正、stop_at に知らない kind、
    rules/train が不正、停止線を越えてしまった(IDM の想定外)、t_max までに終点に着かない。"""
    op = "town_run"
    _check_layout(layout, op)
    import drivetraffic as DT
    R = _check_rules(rules, op)
    dt = _positive(dt, "dt", op)
    v_max = _positive(v_max, "v_max", op)
    a_max = _positive(a_max, "a_max", op)
    b_max = _positive(b_max, "b_max", op)
    stop_hold = float(R["hold_s"]) if stop_hold is None else _nonneg(stop_hold, "stop_hold", op)
    look_hold = float(R["look_hold_s"]) if look_hold is None else _positive(look_hold, "look_hold", op)
    margin = _nonneg(stop_margin, "stop_margin", op)
    T = _nonneg(idm_T, "idm_T", op)
    if margin > 1.0:
        raise ValueError("%s: stop_margin must be <= 1.0 m (the stop must be within 1.0 m of the line)" % op)
    if stop_at is None:
        kinds = _STOP_KINDS
        dyn = {"crossing": R["crossing_stop"] == "when_active"}
    else:
        kinds = tuple(stop_at)
        dyn = {}
    for kd in kinds:
        if kd not in _STOP_KINDS:
            raise ValueError("%s: stop_at kinds must be in %s, got %r" % (op, _STOP_KINDS, kd))
    vs = min(0.05, b_max * dt) if v_stop is None else _positive(v_stop, "v_stop", op)
    if vs > b_max * dt + 1e-12:
        raise ValueError("%s: v_stop (%g) must be <= b_max * dt (%g) so the final stop stays within b_max" % (op, vs, b_max * dt))
    if _is_route(layout):
        P, c = np.asarray(layout["polyline"], np.float64), np.asarray(layout["cum"], np.float64)
        lines = [d for d in layout["stop_lines"] if d["kind"] in kinds]
        widths = [float(layout.get("crossing_width", 7.0))]
    else:
        P, c = _chain_polyline(layout)
        lines = [d for d in town_stop_lines(layout, side=R["side"]) if d["kind"] in kinds]
        widths = [float(e.get("width", 7.0)) for e in layout["elements"] if e.get("kind") == "crossing"]
    L = float(c[-1])
    TR = _train_timing(train, widths[0] if widths else 7.0, op)
    targets = ["dynamic" if dyn.get(d["kind"], False) else "static" for d in lines]
    holds = sum(stop_hold if d["kind"] != "crossing" else 4 * look_hold for d in lines)
    extra = (TR["forbidden_interval"][1] - TR["t_warning"]) if TR else 0.0
    t_lim = (4.0 * L / v_max + holds + extra + 60.0) if t_max is None else _positive(t_max, "t_max", op)

    t = s = v = 0.0
    T_, S_, V_, A_, M_ = [0.0], [0.0], [0.0], [0.0], ["cruise"]
    stops, events = [], []
    k_next = 0
    hold_until = None
    waiting = False
    look_plan: List[Tuple[float, str]] = []
    t_arr = None
    committed = set()
    while s < L - 1e-9:
        if hold_until is not None:
            while look_plan and look_plan[0][0] <= t + 1e-9:
                events.append(("look", float(look_plan[0][0]), look_plan[0][1]))
                look_plan.pop(0)
            if t + 1e-9 >= hold_until:
                if lines[k_next]["kind"] == "crossing" and _forbidden(TR, t):
                    if not waiting:
                        events.append(("wait_gate", float(t), float(s)))
                        waiting = True
                    t += dt
                    T_.append(t); S_.append(s); V_.append(0.0); A_.append(0.0); M_.append("wait")
                    continue
                stops.append((float(s), lines[k_next]["kind"], float(t_arr), float(t)))
                events.append(("go", float(t), float(s), lines[k_next]["kind"]))
                hold_until = None
                waiting = False
                k_next += 1
            else:
                mode = "look" if (lines[k_next]["kind"] == "crossing" and look_plan) else "hold"
                t += dt
                T_.append(t); S_.append(s); V_.append(0.0); A_.append(0.0); M_.append(mode)
                continue
        # 次の目標: 越えた停止線(動的で止まらなかった物)は "pass" で送る
        while k_next < len(lines) and s > lines[k_next]["s"] + 1e-9:
            if targets[k_next] == "static":
                raise ValueError("%s: the car overran the %s stop line at s = %.3f" % (op, lines[k_next]["kind"], lines[k_next]["s"]))
            events.append(("pass", float(t), float(s), lines[k_next]["kind"]))
            k_next += 1
        gap = math.inf
        if k_next < len(lines):
            d = lines[k_next]
            active = targets[k_next] == "static" or (_forbidden(TR, t) and k_next not in committed)
            if active and targets[k_next] == "dynamic" and (d["s"] - s) < v * v / (2.0 * b_max):
                committed.add(k_next)                       # 警報が始まった時に b_max で止まれない → 進む(ジレンマ)
                events.append(("commit", float(t), float(s), d["kind"]))
                active = False
            if active:
                gap = d["s"] - s
                if gap <= 0:
                    raise ValueError("%s: the car overran the %s stop line at s = %.3f (gap %.3g)" % (op, d["kind"], d["s"], gap))
        a_cmd = float(DT.idm_accel(v, gap, v, v0=v_max, T=T, a=a_max, b=b_max, s0=margin))
        a_cmd = min(a_max, max(-b_max, a_cmd))
        v_new = min(v_max, max(0.0, v + a_cmd * dt))
        mode = "brake" if a_cmd < -0.05 else "cruise"
        arriving = math.isfinite(gap) and v <= vs and gap <= 1.0
        if arriving:
            v_new = 0.0                      # v ≤ v_stop ≤ b_max·dt なので、この刻みの減速度 v/dt も b_max 以内
            mode = "look" if (lines[k_next]["kind"] == "crossing" and R["look_required"]) else "hold"
        s_new = s + 0.5 * (v + v_new) * dt
        a_rec = (v_new - v) / dt
        step = dt
        if s_new > L:
            # 終点を越える最後の刻みは、等加速度で L に届く時間 τ(½ a τ² + v τ = L − s)だけ進める(台形則と厳密に整合)
            rem = L - s
            step = rem / v if abs(a_rec) < 1e-12 else (-v + math.sqrt(v * v + 2.0 * a_rec * rem)) / a_rec
            v_new = v + a_rec * step
            s_new = L
        t += step
        s, v = s_new, v_new
        T_.append(t); S_.append(s); V_.append(v); A_.append(a_rec); M_.append(mode)
        if arriving:
            t_arr = t
            kind = lines[k_next]["kind"]
            events.append(("stop", float(t), float(s), kind))
            if kind == "crossing" and R["look_required"]:
                look_plan = [(t + i * look_hold, side) for i, side in enumerate(("left", "right", "left", "right"))]
                hold_until = t + 4 * look_hold
            elif kind == "crossing":
                hold_until = t + max(stop_hold, dt)
            else:
                hold_until = t + stop_hold
        if t > t_lim:
            raise ValueError("%s: did not reach the end (%.1f m) within t_max = %.1f s (s = %.2f)" % (op, L, t_lim, s))
    events.append(("end", float(t), float(s)))
    S = np.asarray(S_)
    pose = _point_at(P, c, S)
    return {"t": np.asarray(T_), "s": S, "x": pose[:, 0], "y": pose[:, 1], "z": _ground_z(layout, S), "yaw": pose[:, 2],
            "v": np.asarray(V_), "a": np.asarray(A_), "mode": np.asarray(M_), "stops": stops, "events": events,
            "stop_lines": lines, "targets": targets, "train": TR, "rules": R, "total_length": L,
            "params": {"dt": dt, "v_max": v_max, "a_max": a_max, "b_max": b_max, "stop_at": kinds, "stop_hold": stop_hold,
                       "look_hold": look_hold, "stop_margin": margin, "idm_T": T, "v_stop": vs,
                       "jurisdiction": R["jurisdiction"], "side": R["side"]}}


# ----------------------------------------------------------------------------------------------------------------------
# 6. 採点
def town_checks(run, layout, *, car_length: float = 4.5, tol: float = 1e-9) -> Dict[str, object]:
    """通し走行の採点(閉形式の門 + 既存の踏切の採点 op)。

    ``stops``: 目標になった停止線ごと(弧長順)に ``{"kind", "s_line", "s_stop", "before" = s_line − s_stop, "ok" (0 ≤ before ≤ 1.0),
    "crossing": crossing_stop_check の結果(踏切だけ。``train`` があれば警報中の区間を forbidden_intervals に渡す),
    "skipped": 動的な目標で止まらなかった}``。``count_ok`` = 停止の回数 = 静的な停止線 + 止まった動的な停止線の数。
    ``kinematics``: ``{"a_max_abs", "v_max", "v_min", "integral_gap" = max|台形則 ∫v dt − (s − s0)|, "ok"}``
    (|a| ≤ max(a_max, b_max)、0 ≤ v ≤ v_max、integral_gap ≤ dt·v_max)。``braking``: 停止ごとに減速を始めた速度 v_b と制動距離 d_b、
    定理 d_b ≥ v_b²/(2 b_max) の ok。``train``(列車があれば): ``{"inside_while_forbidden_s"(警報中に車体が踏切面にかかっていた
    時間)、"go_after_clear"(踏切の発進が警報停止 + 上昇の後)、"timing_meets_minimum", "ok"}``。``ok`` = 全部。

    **Raises** ``ValueError``: run が town_run の物でない、layout が town_chain の物でない、car_length が正でない。"""
    op = "town_checks"
    _check_layout(layout, op)
    if not isinstance(run, dict) or not all(k in run for k in ("t", "s", "v", "a", "stops", "events", "params", "mode", "stop_lines", "targets")):
        raise ValueError("%s: run must be the dict returned by town_run" % op)
    Lv = _positive(car_length, "car_length", op)
    import drivecrossing as DX
    p = run["params"]
    TR = run.get("train")
    t, s, v, a = (np.asarray(run[k], np.float64) for k in ("t", "s", "v", "a"))
    lines, targets = run["stop_lines"], run["targets"]
    look_events = [(ev[1], ev[2]) for ev in run["events"] if ev[0] == "look"]
    forb = [TR["forbidden_interval"]] if TR else []
    stops_out, expected = [], 0
    stops_by_kind = {}
    for st in run["stops"]:
        stops_by_kind.setdefault(st[1], []).append(st)
    for d, tg in zip(lines, targets):
        cands = [st for st in stops_by_kind.get(d["kind"], []) if 0.0 - tol <= d["s"] - st[0] <= 1.0 + tol]
        rec = cands[0] if cands else None
        if rec is not None:
            stops_by_kind[d["kind"]].remove(rec)
        skipped = rec is None and tg == "dynamic"
        if not skipped:
            expected += 1
        before = (d["s"] - rec[0]) if rec is not None else math.nan
        entry = {"kind": d["kind"], "s_line": d["s"], "s_stop": rec[0] if rec else None, "before": before, "skipped": skipped,
                 "ok": bool(skipped or (rec is not None and -tol <= before <= 1.0 + tol))}
        if d["kind"] == "crossing" and d["crossing_zone"] is not None:
            res = DX.crossing_stop_check({"t": t, "x": s, "v": v}, stop_line=d["s"], crossing_start=d["crossing_zone"][0],
                                         crossing_end=d["crossing_zone"][1], car_length=Lv, look_events=look_events,
                                         forbidden_intervals=forb, brake_max=p["b_max"],
                                         signal_controlled=(run["rules"]["crossing_stop"] == "when_active"))
            entry["crossing"] = res
            entry["ok"] = entry["ok"] and bool(res["ok"]) and bool(res["entered"])
        stops_out.append(entry)
    count_ok = len(run["stops"]) == expected
    integ = np.r_[0.0, np.cumsum(0.5 * (v[1:] + v[:-1]) * np.diff(t))]
    gap = float(np.max(np.abs(integ - (s - s[0]))))
    lim_a = max(p["a_max"], p["b_max"])
    kin = {"a_max_abs": float(np.max(np.abs(a))), "v_max": float(v.max()), "v_min": float(v.min()), "integral_gap": gap,
           "ok": bool(np.max(np.abs(a)) <= lim_a + tol and v.max() <= p["v_max"] + tol and v.min() >= -tol
                      and gap <= p["dt"] * p["v_max"] + tol)}
    braking = []
    for (s_stop, kind, t_arr, _t_leave) in run["stops"]:
        i_arr = int(np.argmin(np.abs(t - t_arr)))
        j = i_arr
        while j > 0 and a[j - 1] < 0:      # 連続して減速していた区間の始まり
            j -= 1
        v_b, d_b = float(v[j]), float(s_stop - s[j])
        braking.append({"kind": kind, "v_brake": v_b, "distance": d_b, "lower_bound": v_b * v_b / (2.0 * p["b_max"]),
                        "ok": bool(d_b + tol >= v_b * v_b / (2.0 * p["b_max"]))})
    train_out = None
    if TR:
        f = (t >= TR["forbidden_interval"][0]) & (t < TR["forbidden_interval"][1])
        inside = 0.0
        for d in lines:
            if d["crossing_zone"] is None:
                continue
            on = (s > d["crossing_zone"][0]) & (s - Lv < d["crossing_zone"][1])
            m = f & on
            if np.any(m[1:]):
                inside += float(np.sum(np.diff(t)[m[1:]]))
        goes = [ev[1] for ev in run["events"] if ev[0] == "go" and ev[3] == "crossing"]
        go_after = all(g >= TR["forbidden_interval"][1] - tol for g in goes)
        # commit(警報が始まった時に b_max で止まれなかった → 進んだ)は drivecrossing の unavoidable と同じ扱い: 警報中に踏切の中に
        # 居た時間は 0 でなくてよい(その判断は crossing_stop_check の側で unavoidable として記録される)
        committed = any(ev[0] == "commit" for ev in run["events"])
        train_out = {"inside_while_forbidden_s": inside, "go_after_clear": bool(go_after), "n_crossing_go": len(goes),
                     "committed": bool(committed), "timing_meets_minimum": bool(TR["timing_check"]["meets_minimum"]),
                     "ok": bool((inside <= tol or committed) and go_after and TR["timing_check"]["meets_minimum"])}
    ok = count_ok and kin["ok"] and all(e["ok"] for e in stops_out) and all(b["ok"] for b in braking) and (train_out is None or train_out["ok"])
    return {"stops": stops_out, "count_ok": bool(count_ok), "kinematics": kin, "braking": braking, "train": train_out, "ok": bool(ok)}


# ----------------------------------------------------------------------------------------------------------------------
# 7. 教則の台帳
def kyosoku_summary(path=None) -> Dict[str, object]:
    """教則の場面の再現台帳(docs/drive/kyosoku_scenarios.json)を読み、category × status の件数表にする。

    ``path`` = None なら repo の ``docs/drive/kyosoku_scenarios.json``(このモジュールの場所から引く)。
    返り値 ``{"total", "statuses" (順序つき), "by_status": {status: n}, "categories": [...](件数の多い順),
    "by_category": {category: {status: n}}, "table": [[category, n_reproduced, n_partial, n_pending, n_not_reproducible, total], ...]}``。

    **Raises** ``ValueError``: ファイルが無い・JSON でない・``scenarios`` が無い・場面に id/category/status が無い・
    status が :data:`KYOSOKU_STATUSES` に無い・id が重複。"""
    op = "kyosoku_summary"
    p = Path(path) if path is not None else Path(__file__).resolve().parent / "docs" / "drive" / "kyosoku_scenarios.json"
    if not p.is_file():
        raise ValueError("%s: ledger not found: %s" % (op, p.name if path is None else p))
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("%s: cannot read the ledger as JSON (%s)" % (op, exc))
    if not isinstance(data, dict) or not isinstance(data.get("scenarios"), list) or not data["scenarios"]:
        raise ValueError("%s: ledger must be a dict with a non-empty 'scenarios' list" % op)
    ids = []
    by_cat: Dict[str, Counter] = {}
    by_status: Counter = Counter()
    for r in data["scenarios"]:
        if not isinstance(r, dict) or not all(k in r for k in ("id", "category", "status")):
            raise ValueError("%s: every scenario needs id / category / status" % op)
        if r["status"] not in KYOSOKU_STATUSES:
            raise ValueError("%s: %s has unknown status %r" % (op, r["id"], r["status"]))
        ids.append(r["id"])
        by_cat.setdefault(str(r["category"]), Counter())[r["status"]] += 1
        by_status[r["status"]] += 1
    if len(set(ids)) != len(ids):
        raise ValueError("%s: duplicate scenario ids" % op)
    cats = sorted(by_cat, key=lambda k: (-sum(by_cat[k].values()), k))
    table = [[k] + [int(by_cat[k][st]) for st in KYOSOKU_STATUSES] + [int(sum(by_cat[k].values()))] for k in cats]
    return {"total": len(ids), "statuses": list(KYOSOKU_STATUSES), "by_status": {st: int(by_status[st]) for st in KYOSOKU_STATUSES},
            "categories": cats, "by_category": {k: {st: int(by_cat[k][st]) for st in KYOSOKU_STATUSES if by_cat[k][st]} for k in cats},
            "table": table}
