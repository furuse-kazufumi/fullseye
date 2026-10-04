# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""drivecommonroad — 他人の場面(CommonRoad 2020a の公開シナリオ)で自分の運転手(縦 IDM + 経路追従)を走らせ、他人の採点器
(TUM commonroad-drivability-checker)に提出できる solution XML を書く(自動運転 PoC 系列、外部場面への接続の土台)。

これまでの PoC は自前の町(:mod:`drivetown`)で自前の門だけを通してきた。ここでは **場面も採点器も他人の物** を使う:
場面 = CommonRoad 2020a XML(lanelet の左右境界・動的障害物の軌跡・標識・planning problem)、採点器 = TUM の
drivability-checker(``valid_solution`` = goal 到達 ∧ 初期状態一致 ∧ 障害物/道路境界/自車同士の無衝突 ∧ 運動学の実現可能性)。
採点器は Linux(WSL)でしか動かないので、repo 側は (a) 自前の XML 読み書き (b) 軌道生成 (c) 採点器と同じ考え方の運動学・衝突の
**第 2 実装** を持ち、公式の合否は外部 JSON(:func:`cr_checker_result`、tools/check_solution_json.py が WSL で書く)から読む。
numpy と標準ライブラリだけで動く(commonroad-io はテストの照合にだけ任意で使う)。

読む(:func:`cr_read`): xml.etree で 2020a を読む。lanelet の中心線は XML に無いので **左右境界の平均** で作る(左右の頂点数が
同じことを前提にする = commonroad-io と同じ約束)。標識 274(最高速度)の additional_value は m/s の文字列。2020a 以外は
ValueError(fail-closed)。

経路(:func:`cr_route`): successor の BFS(hop 数最小)。ゴールの ``position_lanelets`` があればそれを終点に。中心線を継いで
0.5 m で再標本化し、各 lanelet の始まる弧長 ``lanelet_s`` と多角形(左境界 + 右境界の逆順)も持つ。``length`` = 継いだ中心線の
折線長(門: 合成場面で Σ 中心線長と 1e-6 で一致)。

運動学(:func:`ks_step`): 運動学単線(KS)モデル、参照点 = **後軸中心**。state = (x, y, δ, v, ψ)、u = (δ̇, a)。
ẋ = v cos ψ、ẏ = v sin ψ、δ̇ = u₀、v̇ = u₁、ψ̇ = v / l_wb · tan δ(Althoff & Würsching, commonroad-vehicle-models
``vehicle_dynamics_ks`` と同じ式。入力の状態依存の飽和 ``steering_constraints`` / ``acceleration_constraints`` も右辺に写した)。
**区分一定入力を RK4** で積分する(採点器は同じ ODE を scipy.odeint で積分し、位置 2 cm・向き 0.03 rad の許容で照合する)。
母数 :data:`BMW_320I` は commonroad-vehicle-models 3.0.2 ``parameters_vehicle2`` を実行して写した値(出典コメント参照)。
CommonRoad の state の position は **車両中心** = 後軸 + b·(cos ψ, sin ψ) なので、読み書きで変換する。

運転(:func:`cr_drive`): 縦 = IDM(Treiber 2000、式は :func:`drivetraffic.idm_accel` と同じだがここで自前に書く:
a = a_max (1 − (v/v₀)⁴ − (s*/gap)²)、s* = s₀ + max(0, v T + v Δv / (2√(a_max b_max))))。目標 = (i) 経路の終点(ゴール lanelet の
20 % 地点、止まった先行車と見なす)(ii) ``stop_lines``(弧長の列。止まったら ``hold_s`` 秒で発進)(iii) 経路上の先行障害物
(中心が経路から横 ``follow_width`` 以内で前にある物、Δv つき)。希望速度 v₀ = min(v_cruise, 経路の制限, 曲率の許容速度)。曲率の
許容は √(a_lat / |κ|) を後ろ向きに √(v² + 2 b Δs) で繋いだ速度の上限(先の曲がりに向けて先に減速する)。
横 = pure pursuit(後軸から見通し L_d = max(lookahead, k_v·v) 先の点へ、δ = atan(2 l_wb sin α / L_d)、δ̇ は ±0.4 rad/s で制限)。
各 step で :func:`ks_step`。初期状態は planning problem の initial(位置を後軸へ変換、δ = 0)。停止は IDM では漸近的なので
v ≤ v_stop で a = −v/dt を入れて **ちょうど 0** にし、止まっている間は舵を切らない(ψ̇ = 0 のまま δ だけ変わる状態遷移は採点器の
最適化器が入力を復元しにくい)。ゴール判定 ``goal_reached`` は採点器と同じ(ゴールの time_step 区間内の **1 状態以上** が、
ゴールの多角形の中(車両中心)にあり、速度区間内にある)。到達しなければ ValueError ではなく ``goal_reached: False``。

実現可能性(:func:`cr_feasible`): 採点器の ``solution_feasible`` と同じ考え方の第 2 実装。各遷移で記録した u から :func:`ks_step` を
回し、次の状態と位置 2 cm・向き 0.03 rad 以内か、入力が制限内か、摩擦円 a² + (v ψ̇)² ≤ a_max² か。採点器は u を最適化で復元する
(記録を使わない)ので「同じ結論になるはず」の第 2 実装であって同一の計算ではない。

衝突(:func:`cr_collision`): 自車矩形(4.508 × 1.610、車両中心・ψ)と各障害物の矩形の **分離軸判定(SAT)** を time_step ごとに。
道路境界は車両の 4 角が lanelet 多角形の和集合に入るか(点 in 多角形 OR、既定は場面の全 lanelet = 採点器と同じ範囲、
``lanelets="route"`` で経路だけ)。採点器は三角形分割した境界との衝突で判定するので、角が境界線上に乗る際どい場合は結論が割れうる。

書く(:func:`cr_solution_xml`): 公式 solution XML(``CommonRoadSolution benchmark_id="KS2:JB1:<id>:2020a"``、``ksTrajectory`` の
``ksState{x, y, steeringAngle, velocity, orientation, time}``、位置 = 車両中心)。採点器の読みは commonroad-io
``CommonRoadSolutionReader``。

合成場面(:func:`cr_synthetic`): 実データが無い CI 用の最小 2020a XML(lanelet 3 本の連結 + 対向車 1 台 + 標識 274 + stopLine +
planning problem)。``kind``: ``tjunction``(直線 → 左 90° 円弧 → 直線)/ ``straight``(直線 3 本)/ ``blocked``(straight の
2 本目に静止障害物 = 衝突の門用)。

限界(self_reported):
  * 運転はルールベースの縦 IDM + pure pursuit で、交差点の譲り合い(gap acceptance)は持たない。対向車が経路の帯に入った時だけ
    IDM が減速する。衝突が残る場面では v_cruise を変えて走り直す(PoC 側の規則)。
  * 曲率は 0.5 m 標本の向きの差を 6 m 窓で平均した近似(頂点の粗い折線で角が立つための平滑)。
  * 道路境界の判定は多角形の点包含で、採点器の三角形分割とは別の計算。境界線上の角は結論が割れうる。
  * 2020a の読み取りは PoC に要る要素だけ(lanelet / trafficSign / trafficLight / 動的・静的障害物 / planningProblem)。
    intersection・環境・shapeGroup の障害物・円形の障害物は読まない(円は多角形に近似、矩形以外の障害物は ValueError)。
  * 公式の合否はこのモジュールでは出せない(WSL のチェッカーの JSON を :func:`cr_checker_result` で読むだけ)。

参考: Althoff, Koschi, Manzinger (2017) CommonRoad: Composable benchmarks for motion planning on roads, IV 2017。
CommonRoad XML 2020a specification(commonroad.in.tum.de)。commonroad-vehicle-models 3.0.2(Althoff, Würsching)
``vehicle_dynamics_ks`` / ``parameters_vehicle2``。commonroad-drivability-checker 2025.4.0 ``feasibility_checker``
(e = (2e-2, 2e-2, 3e-2)、丸め 4 桁)。Treiber, Hennecke, Helbing (2000) PRE 62(IDM)。Coulter (1992) pure pursuit, CMU-RI-TR-92-01。
"""
from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

__all__ = [
    "cr_read", "cr_route", "ks_step", "cr_drive", "cr_drive_sweep", "cr_feasible", "cr_collision", "cr_solution_xml",
    "cr_checker_result", "cr_synthetic",
    "BMW_320I", "VEHICLE_TYPE_IDS", "SYNTHETIC_KINDS", "CHECKER_KEYS",
]

_TWO_PI = 2.0 * math.pi
_VERSION = "2020a"

#: BMW 320i(CommonRoad vehicle type 2)。出典: commonroad-vehicle-models 3.0.2 ``parameters_vehicle2()`` を実行して写した値
#: (vehicleParameters/parameters_vehicle2.yaml)。l_wb = a + b。長さ・幅は衝突判定の矩形、a_max は摩擦円と加速の飽和に使う。
BMW_320I: Dict[str, float] = {
    "l_wb": 2.5789128, "a": 1.1561957064, "b": 1.4227170936, "length": 4.508, "width": 1.61,
    "delta_min": -1.066, "delta_max": 1.066, "ddelta_min": -0.4, "ddelta_max": 0.4,
    "v_min": -13.9, "v_max": 50.8, "a_max": 11.5, "v_switch": 7.319,
}
_PARAM_KEYS = tuple(BMW_320I)

#: CommonRoad の vehicle type 番号(benchmark_id の "KS2" の 2)。
VEHICLE_TYPE_IDS: Dict[str, int] = {"FORD_ESCORT": 1, "BMW_320i": 2, "VW_VANAGON": 3}
SYNTHETIC_KINDS = ("tjunction", "straight", "blocked")
#: WSL のチェッカー(tools/check_solution_json.py)が書く JSON の必須キー。
CHECKER_KEYS = ("scenario", "solution", "valid", "goal_reached", "feasible", "obstacle_collision", "boundary_collision",
                "checker_version")
_INPUT_TOL = 1e-9


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


def _params(params, op: str) -> Dict[str, float]:
    if params is None:
        return dict(BMW_320I)
    if not isinstance(params, dict):
        raise ValueError("%s: params must be a dict like BMW_320I" % op)
    out = {}
    for k in _PARAM_KEYS:
        if k not in params:
            raise ValueError("%s: params has no %r" % (op, k))
        out[k] = _finite(params[k], "params[%s]" % k, op)
    if out["l_wb"] <= 0 or out["length"] <= 0 or out["width"] <= 0 or out["a_max"] <= 0:
        raise ValueError("%s: l_wb, length, width, a_max must be > 0" % op)
    return out


def _state5(x, name: str, op: str) -> np.ndarray:
    s = np.asarray(x, dtype=float)
    if s.shape != (5,) or not np.all(np.isfinite(s)):
        raise ValueError("%s: %s must be a finite (x, y, delta, v, psi), got shape %r" % (op, name, s.shape))
    return s


def _check_scene(scene, op: str) -> dict:
    if not isinstance(scene, dict) or scene.get("kind") != "commonroad_scene":
        raise ValueError("%s: scene must be the dict returned by cr_read" % op)
    for key in ("id", "dt", "lanelets", "obstacles", "planning_problems", "traffic_signs", "traffic_lights"):
        if key not in scene:
            raise ValueError("%s: scene has no %r (use cr_read)" % (op, key))
    return scene


def _check_run(run, op: str) -> dict:
    if not isinstance(run, dict) or run.get("kind") != "commonroad_run":
        raise ValueError("%s: run must be the dict returned by cr_drive" % op)
    for key in ("time_step", "x", "y", "x_rear", "y_rear", "delta", "v", "psi", "u", "params", "dt"):
        if key not in run:
            raise ValueError("%s: run has no %r (use cr_drive)" % (op, key))
    n = len(run["time_step"])
    if n < 2 or np.asarray(run["u"]).shape != (n - 1, 2):
        raise ValueError("%s: run must have >= 2 states and u of shape (T-1, 2)" % op)
    return run


# ----------------------------------------------------------------------------------------------------------------------
# 幾何の小道具
def _wrap(x: float) -> float:
    return (x + math.pi) % _TWO_PI - math.pi


def _polyline_cum(P: np.ndarray) -> np.ndarray:
    seg = np.hypot(np.diff(P[:, 0]), np.diff(P[:, 1]))
    return np.concatenate([[0.0], np.cumsum(seg)])


def _point_at(P: np.ndarray, cum: np.ndarray, s: float) -> np.ndarray:
    """弧長 s の点。範囲外は端の線分の向きに外挿(終点を過ぎても舵の目標が壊れないため)。"""
    if s <= 0.0:
        d = P[1] - P[0]
        return P[0] + d / max(float(np.hypot(*d)), 1e-12) * s
    if s >= cum[-1]:
        d = P[-1] - P[-2]
        return P[-1] + d / max(float(np.hypot(*d)), 1e-12) * (s - cum[-1])
    i = int(np.searchsorted(cum, s, side="right")) - 1
    t = (s - cum[i]) / max(cum[i + 1] - cum[i], 1e-12)
    return P[i] + t * (P[i + 1] - P[i])


def _project(P: np.ndarray, cum: np.ndarray, pt) -> Tuple[float, float]:
    """点 pt を折線へ射影した弧長と符号つき横ずれ(左が正)。最近傍線分の上に射影する。"""
    pt = np.asarray(pt, dtype=float)
    A, B = P[:-1], P[1:]
    D = B - A
    L2 = np.maximum(np.einsum("ij,ij->i", D, D), 1e-18)
    t = np.clip(np.einsum("ij,ij->i", pt - A, D) / L2, 0.0, 1.0)
    Q = A + t[:, None] * D
    d2 = np.einsum("ij,ij->i", Q - pt, Q - pt)
    i = int(np.argmin(d2))
    s = float(cum[i] + t[i] * (cum[i + 1] - cum[i]))
    cross = D[i, 0] * (pt[1] - A[i, 1]) - D[i, 1] * (pt[0] - A[i, 0])
    return s, float(math.copysign(math.sqrt(d2[i]), cross))


def _point_in_polygon(poly: np.ndarray, pt, margin: float = 1e-9) -> bool:
    """ray casting + 境界からの距離 ≤ margin も内側(共有境界の上に乗る点を落とさないため)。"""
    x, y = float(pt[0]), float(pt[1])
    n = len(poly)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y):
            xs = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < xs:
                inside = not inside
        j = i
    if inside:
        return True
    A = poly
    B = np.roll(poly, -1, axis=0)
    D = B - A
    L2 = np.maximum(np.einsum("ij,ij->i", D, D), 1e-18)
    t = np.clip(((x - A[:, 0]) * D[:, 0] + (y - A[:, 1]) * D[:, 1]) / L2, 0.0, 1.0)
    Q = A + t[:, None] * D
    return bool(np.min(np.hypot(Q[:, 0] - x, Q[:, 1] - y)) <= margin)


def _rect_corners(cx: float, cy: float, psi: float, length: float, width: float) -> np.ndarray:
    c, s = math.cos(psi), math.sin(psi)
    hl, hw = 0.5 * length, 0.5 * width
    local = np.array([[hl, hw], [hl, -hw], [-hl, -hw], [-hl, hw]])
    R = np.array([[c, -s], [s, c]])
    return local @ R.T + np.array([cx, cy])


def _sat_overlap(A: np.ndarray, B: np.ndarray, margin: float = 0.0) -> bool:
    """2 つの凸多角形(頂点列)の分離軸判定。margin > 0 で膨らませる(その分だけ近づいても衝突と見る)。"""
    for poly in (A, B):
        E = np.roll(poly, -1, axis=0) - poly
        for ex, ey in E:
            n = math.hypot(ex, ey)
            if n < 1e-12:
                continue
            ax, ay = -ey / n, ex / n
            pa = A[:, 0] * ax + A[:, 1] * ay
            pb = B[:, 0] * ax + B[:, 1] * ay
            if pa.max() + margin < pb.min() or pb.max() + margin < pa.min():
                return False
    return True


# ----------------------------------------------------------------------------------------------------------------------
# 読む
def _text_float(el: Optional[ET.Element], name: str, op: str) -> float:
    if el is None or el.text is None:
        raise ValueError("%s: missing <%s>" % (op, name))
    return _finite(el.text.strip(), name, op)


def _points(el: Optional[ET.Element], name: str, op: str) -> np.ndarray:
    if el is None:
        raise ValueError("%s: missing <%s>" % (op, name))
    pts = [(_text_float(p.find("x"), name + "/x", op), _text_float(p.find("y"), name + "/y", op)) for p in el.findall("point")]
    if len(pts) < 2:
        raise ValueError("%s: <%s> needs >= 2 points" % (op, name))
    return np.asarray(pts, dtype=float)


def _interval(el: Optional[ET.Element], name: str, op: str) -> Optional[Tuple[float, float]]:
    if el is None:
        return None
    ex = el.find("exact")
    if ex is not None:
        v = _text_float(ex, name, op)
        return (v, v)
    lo, hi = el.find("intervalStart"), el.find("intervalEnd")
    if lo is None or hi is None:
        raise ValueError("%s: <%s> must have <exact> or <intervalStart>/<intervalEnd>" % (op, name))
    a, b = _text_float(lo, name, op), _text_float(hi, name, op)
    if b < a:
        raise ValueError("%s: <%s> interval end < start" % (op, name))
    return (a, b)


def _exact(el: Optional[ET.Element], name: str, op: str) -> float:
    iv = _interval(el, name, op)
    if iv is None:
        raise ValueError("%s: missing <%s>" % (op, name))
    if iv[0] != iv[1]:
        raise ValueError("%s: <%s> must be exact, got interval %r" % (op, name, iv))
    return iv[0]


def _state_row(el: ET.Element, op: str) -> Tuple[float, float, float, float, float]:
    pos = el.find("position")
    pt = pos.find("point") if pos is not None else None
    if pt is None:
        raise ValueError("%s: obstacle state needs <position><point>" % op)
    x = _text_float(pt.find("x"), "x", op)
    y = _text_float(pt.find("y"), "y", op)
    vel = el.find("velocity")
    return (_exact(el.find("time"), "time", op), x, y, _exact(el.find("orientation"), "orientation", op),
            _exact(vel, "velocity", op) if vel is not None else 0.0)       # 静止障害物は velocity を持たない


def _shape(el: Optional[ET.Element], op: str) -> dict:
    if el is None:
        raise ValueError("%s: obstacle needs <shape>" % op)
    rect = el.find("rectangle")
    if rect is None:
        raise ValueError("%s: only rectangle obstacle shapes are read (got %s)" % (op, [c.tag for c in el]))
    out = {"kind": "rectangle", "length": _positive(_text_float(rect.find("length"), "length", op), "length", op),
           "width": _positive(_text_float(rect.find("width"), "width", op), "width", op),
           "orientation": 0.0, "center": (0.0, 0.0)}
    if rect.find("orientation") is not None:
        out["orientation"] = _text_float(rect.find("orientation"), "orientation", op)
    c = rect.find("center")
    if c is not None:
        out["center"] = (_text_float(c.find("x"), "center/x", op), _text_float(c.find("y"), "center/y", op))
    return out


def _goal_position(el: Optional[ET.Element], op: str) -> Tuple[Optional[List[int]], Optional[np.ndarray]]:
    if el is None:
        return None, None
    refs = [int(l.get("ref")) for l in el.findall("lanelet")]
    if refs:
        return refs, None
    rect = el.find("rectangle")
    if rect is not None:
        sh = _shape(el, op)
        return None, _rect_corners(sh["center"][0], sh["center"][1], sh["orientation"], sh["length"], sh["width"])
    poly = el.find("polygon")
    if poly is not None:
        return None, _points(poly, "polygon", op)
    circ = el.find("circle")
    if circ is not None:
        r = _positive(_text_float(circ.find("radius"), "radius", op), "radius", op)
        c = circ.find("center")
        cx, cy = (_text_float(c.find("x"), "center/x", op), _text_float(c.find("y"), "center/y", op)) if c is not None else (0.0, 0.0)
        th = np.linspace(0.0, _TWO_PI, 64, endpoint=False)
        return None, np.column_stack([cx + r * np.cos(th), cy + r * np.sin(th)])
    raise ValueError("%s: goal position must be lanelet refs or rectangle/polygon/circle" % op)


def cr_read(source) -> dict:
    """CommonRoad 2020a XML(文字列 or パス)を読む。

    返り値: ``{"kind": "commonroad_scene", "id", "dt", "version", "lanelets": {id: {"center" (n,2), "left", "right", "polygon",
    "successors", "predecessors", "adj_left", "adj_right", "speed_limit_mps" | None, "stop_line" (2,2) | None,
    "traffic_sign_ids", "traffic_light_ids", "length"}}, "obstacles": [{"id", "type", "static", "shape", "states" (T,5)
    [time_step, x, y, orientation, velocity]}], "planning_problems": [{"id", "initial": {time_step, x, y, orientation,
    velocity}, "goal": [{"time_step": (lo, hi), "position_lanelets" | None, "position_polygon" (k,2) | None,
    "velocity": (lo, hi) | None, "orientation": (lo, hi) | None}]}], "traffic_signs": {id: {"element_ids", "additional",
    "position"}}, "traffic_lights": {id: {"position", "cycle": [(color, duration)], "time_offset", "active", "direction"}}}``。

    中心線は左右境界の平均(頂点数が揃っていることを要求)。標識 274 の additional_value[0] は m/s → float。

    **Raises** ``ValueError``: 壊れた XML、ルートが commonRoad でない、commonRoadVersion ≠ 2020a、必須要素の欠落、矩形以外の障害物。"""
    op = "cr_read"
    if isinstance(source, (str, Path)) and not str(source).lstrip().startswith("<"):
        p = Path(source)
        if not p.is_file():
            raise ValueError("%s: file not found: %s" % (op, p))
        text = p.read_text(encoding="utf-8")
    elif isinstance(source, (str, bytes)):
        text = source if isinstance(source, str) else source.decode("utf-8")
    else:
        raise ValueError("%s: source must be an XML string or a path" % op)
    try:
        root = ET.fromstring(text.encode("utf-8") if isinstance(text, str) else text)
    except ET.ParseError as ex:
        raise ValueError("%s: XML parse error: %s" % (op, ex))
    if root.tag != "commonRoad":
        raise ValueError("%s: root element must be <commonRoad>, got <%s>" % (op, root.tag))
    version = root.get("commonRoadVersion")
    if version != _VERSION:
        raise ValueError("%s: commonRoadVersion must be %s, got %r" % (op, _VERSION, version))
    dt = _positive(root.get("timeStepSize"), "timeStepSize", op)
    sid = root.get("benchmarkID")
    if not sid:
        raise ValueError("%s: missing benchmarkID" % op)

    signs: Dict[int, dict] = {}
    for ts in root.findall("trafficSign"):
        ids, add = [], []
        for e in ts.findall("trafficSignElement"):
            ids.append((e.findtext("trafficSignID") or "").strip())
            add.append([(a.text or "").strip() for a in e.findall("additionalValue")])
        pos = ts.find("position/point")
        signs[int(ts.get("id"))] = {
            "element_ids": ids, "additional": add,
            "position": (_text_float(pos.find("x"), "x", op), _text_float(pos.find("y"), "y", op)) if pos is not None else None,
            "virtual": (ts.findtext("virtual") or "false").strip() == "true",
        }
    lights: Dict[int, dict] = {}
    for tl in root.findall("trafficLight"):
        pos = tl.find("position/point")
        cyc = tl.find("cycle")
        cycle = []
        if cyc is not None:
            for ce in cyc.findall("cycleElement"):
                cycle.append(((ce.findtext("color") or "").strip(), _text_float(ce.find("duration"), "duration", op)))
        lights[int(tl.get("id"))] = {
            "position": (_text_float(pos.find("x"), "x", op), _text_float(pos.find("y"), "y", op)) if pos is not None else None,
            "cycle": cycle, "time_offset": _finite(cyc.findtext("timeOffset") or 0.0, "timeOffset", op) if cyc is not None else 0.0,
            "active": (tl.findtext("active") or "true").strip() == "true", "direction": (tl.findtext("direction") or "all").strip(),
        }

    lanelets: Dict[int, dict] = {}
    for la in root.findall("lanelet"):
        lid = int(la.get("id"))
        left = _points(la.find("leftBound"), "leftBound", op)
        right = _points(la.find("rightBound"), "rightBound", op)
        if len(left) != len(right):
            raise ValueError("%s: lanelet %d has %d left and %d right vertices (must match to build the centre line)"
                             % (op, lid, len(left), len(right)))
        center = 0.5 * (left + right)
        sign_ids = [int(r.get("ref")) for r in la.findall("trafficSignRef")]
        light_ids = [int(r.get("ref")) for r in la.findall("trafficLightRef")]
        limit = None
        for sg in sign_ids:
            if sg not in signs:
                raise ValueError("%s: lanelet %d references unknown trafficSign %d" % (op, lid, sg))
            for eid, add in zip(signs[sg]["element_ids"], signs[sg]["additional"]):
                if eid == "274" and add:
                    v = _positive(add[0], "trafficSign %d additionalValue" % sg, op)
                    limit = v if limit is None else min(limit, v)
        sl = la.find("stopLine")
        stop_line = None
        if sl is not None:
            stop_line = _points(sl, "stopLine", op)[:2]
        adj_l, adj_r = la.find("adjacentLeft"), la.find("adjacentRight")
        lanelets[lid] = {
            "center": center, "left": left, "right": right, "polygon": np.vstack([left, right[::-1]]),
            "successors": [int(r.get("ref")) for r in la.findall("successor")],
            "predecessors": [int(r.get("ref")) for r in la.findall("predecessor")],
            "adj_left": int(adj_l.get("ref")) if adj_l is not None else None,
            "adj_right": int(adj_r.get("ref")) if adj_r is not None else None,
            "speed_limit_mps": limit, "stop_line": stop_line, "traffic_sign_ids": sign_ids, "traffic_light_ids": light_ids,
            "lanelet_type": [(t.text or "").strip() for t in la.findall("laneletType")],
            "length": float(_polyline_cum(center)[-1]),
        }
    for lid, la in lanelets.items():
        for s in la["successors"] + la["predecessors"]:
            if s not in lanelets:
                raise ValueError("%s: lanelet %d references unknown lanelet %d" % (op, lid, s))

    obstacles: List[dict] = []
    for tag, static in (("dynamicObstacle", False), ("staticObstacle", True)):
        for ob in root.findall(tag):
            oid = int(ob.get("id"))
            init = ob.find("initialState")
            if init is None:
                raise ValueError("%s: obstacle %d has no <initialState>" % (op, oid))
            rows = [_state_row(init, op)]
            traj = ob.find("trajectory")
            if traj is not None:
                rows.extend(_state_row(st, op) for st in traj.findall("state"))
            states = np.asarray(rows, dtype=float)
            if len(states) > 1 and np.any(np.diff(states[:, 0]) <= 0):
                raise ValueError("%s: obstacle %d time steps must increase" % (op, oid))
            obstacles.append({"id": oid, "type": (ob.findtext("type") or "").strip(), "static": static,
                              "shape": _shape(ob.find("shape"), op), "states": states})

    problems: List[dict] = []
    for pp in root.findall("planningProblem"):
        pid = int(pp.get("id"))
        init = pp.find("initialState")
        if init is None:
            raise ValueError("%s: planningProblem %d has no <initialState>" % (op, pid))
        t, x, y, psi, v = _state_row(init, op)
        goals = []
        for gs in pp.findall("goalState"):
            lan, poly = _goal_position(gs.find("position"), op)
            ts = _interval(gs.find("time"), "time", op)
            if ts is None:
                raise ValueError("%s: planningProblem %d goalState needs <time>" % (op, pid))
            goals.append({"time_step": (int(round(ts[0])), int(round(ts[1]))), "position_lanelets": lan, "position_polygon": poly,
                          "velocity": _interval(gs.find("velocity"), "velocity", op),
                          "orientation": _interval(gs.find("orientation"), "orientation", op)})
        if not goals:
            raise ValueError("%s: planningProblem %d has no <goalState>" % (op, pid))
        for g in goals:
            for lid in g["position_lanelets"] or []:
                if lid not in lanelets:
                    raise ValueError("%s: goal references unknown lanelet %d" % (op, lid))
        problems.append({"id": pid, "initial": {"time_step": int(round(t)), "x": x, "y": y, "orientation": psi, "velocity": v},
                         "goal": goals})
    if not lanelets:
        raise ValueError("%s: scenario has no lanelets" % op)
    return {"kind": "commonroad_scene", "id": sid, "dt": dt, "version": version, "author": root.get("author"),
            "lanelets": lanelets, "obstacles": obstacles, "planning_problems": problems,
            "traffic_signs": signs, "traffic_lights": lights}


# ----------------------------------------------------------------------------------------------------------------------
# 経路
def _lanelets_containing(scene: dict, pt, psi: Optional[float] = None) -> List[int]:
    """点 pt を含む lanelet の id(向き psi があれば中心線の向きと近い順)。"""
    hits = []
    for lid, la in scene["lanelets"].items():
        if _point_in_polygon(la["polygon"], pt, margin=1e-6):
            score = 0.0
            if psi is not None:
                c = la["center"]
                cum = _polyline_cum(c)
                s, _ = _project(c, cum, pt)
                q0, q1 = _point_at(c, cum, max(s - 0.5, 0.0)), _point_at(c, cum, min(s + 0.5, cum[-1]))
                score = abs(_wrap(math.atan2(q1[1] - q0[1], q1[0] - q0[0]) - psi))
            hits.append((score, lid))
    hits.sort()
    return [lid for _, lid in hits]


def cr_route(scene, lanelet_from, lanelet_to=None, *, goal=None, step: float = 0.5) -> dict:
    """successor の BFS(hop 数最小)で lanelet の列を出し、中心線を継いで ``step`` m で再標本化する。

    ``lanelet_to`` が None なら ``goal["position_lanelets"]`` を終点にする(どちらも無ければ ValueError)。
    返り値 ``{"lanelets", "polyline" (K,2), "cum" (K,), "length", "speed_limit_mps" (経路上の最小 | None),
    "lanelet_s" (各 lanelet が始まる弧長), "lanelet_len", "polygons" [多角形]}``。``length`` = 継いだ中心線の折線長
    (継ぎ目で重なる頂点は 1 つに潰す)。

    **Raises** ``ValueError``: 未知の lanelet、到達不能、終点が無い。"""
    op = "cr_route"
    scene = _check_scene(scene, op)
    L = scene["lanelets"]
    step = _positive(step, "step", op)
    if lanelet_from not in L:
        raise ValueError("%s: unknown lanelet_from %r" % (op, lanelet_from))
    if lanelet_to is None:
        if goal is None or not goal.get("position_lanelets"):
            raise ValueError("%s: lanelet_to is None and goal has no position_lanelets" % op)
        targets = set(goal["position_lanelets"])
    else:
        if lanelet_to not in L:
            raise ValueError("%s: unknown lanelet_to %r" % (op, lanelet_to))
        targets = {lanelet_to}
    prev: Dict[int, Optional[int]] = {lanelet_from: None}
    q = deque([lanelet_from])
    found = None
    while q:
        cur = q.popleft()
        if cur in targets:
            found = cur
            break
        for s in L[cur]["successors"]:
            if s not in prev:
                prev[s] = cur
                q.append(s)
    if found is None:
        raise ValueError("%s: no successor route from %r to %r" % (op, lanelet_from, sorted(targets)))
    ids = []
    cur: Optional[int] = found
    while cur is not None:
        ids.append(cur)
        cur = prev[cur]
    ids.reverse()

    pts: List[np.ndarray] = []
    lanelet_s, lanelet_len = [], []
    for lid in ids:
        c = L[lid]["center"]
        if pts and np.hypot(*(pts[-1] - c[0])) < 1e-6:
            c = c[1:]
        lanelet_s.append(float(_polyline_cum(np.vstack(pts))[-1]) if len(pts) >= 2 else 0.0)
        lanelet_len.append(L[lid]["length"])
        pts.extend(c)
    P = np.vstack(pts)
    cum_raw = _polyline_cum(P)
    total = float(cum_raw[-1])
    if total <= 0:
        raise ValueError("%s: route has zero length" % op)
    s_new = np.arange(0.0, total, step)
    if total - s_new[-1] > 1e-9:
        s_new = np.append(s_new, total)
    poly = np.column_stack([np.interp(s_new, cum_raw, P[:, 0]), np.interp(s_new, cum_raw, P[:, 1])])
    limits = [L[lid]["speed_limit_mps"] for lid in ids if L[lid]["speed_limit_mps"] is not None]
    return {"kind": "commonroad_route", "lanelets": ids, "polyline": poly, "cum": s_new, "length": total,
            "speed_limit_mps": min(limits) if limits else None, "lanelet_s": np.asarray(lanelet_s), "lanelet_len": np.asarray(lanelet_len),
            "polygons": [L[lid]["polygon"] for lid in ids]}


# ----------------------------------------------------------------------------------------------------------------------
# 運動学
def _ks_rhs(x: np.ndarray, u: np.ndarray, p: Dict[str, float]) -> np.ndarray:
    """vehicle_dynamics_ks と同じ右辺(入力の状態依存の飽和も写す)。"""
    d, v = x[2], x[3]
    sv = u[0]
    if (d <= p["delta_min"] and sv <= 0) or (d >= p["delta_max"] and sv >= 0):
        sv = 0.0
    elif sv <= p["ddelta_min"]:
        sv = p["ddelta_min"]
    elif sv >= p["ddelta_max"]:
        sv = p["ddelta_max"]
    a = u[1]
    pos_limit = p["a_max"] * p["v_switch"] / v if v > p["v_switch"] else p["a_max"]
    if (v <= p["v_min"] and a <= 0) or (v >= p["v_max"] and a >= 0):
        a = 0.0
    elif a <= -p["a_max"]:
        a = -p["a_max"]
    elif a >= pos_limit:
        a = pos_limit
    return np.array([v * math.cos(x[4]), v * math.sin(x[4]), sv, a, v / p["l_wb"] * math.tan(d)])


def ks_step(state, u, dt: float, params=None) -> np.ndarray:
    """運動学単線(KS)モデルを区分一定入力 u = (δ̇, a) で dt だけ RK4 で進める。参照点 = 後軸中心。

    state = (x_rear, y_rear, δ, v, ψ)。式: ẋ = v cos ψ、ẏ = v sin ψ、δ̇ = u₀、v̇ = u₁、ψ̇ = v / l_wb · tan δ
    (commonroad-vehicle-models ``vehicle_dynamics_ks``、入力の飽和 ``steering_constraints`` / ``acceleration_constraints`` も同じ)。

    門: δ = 0 で x = x₀ + v t(1e-9)、一定 δ で半径 l_wb / tan δ の円(1 周で始点へ 1e-6)、commonroad-io があれば
    ``vehicle_dynamics_ks`` の odeint と 1 step で 1e-6 一致。

    **Raises** ``ValueError``: state が (5,) でない・非有限、u が (2,) でない、dt ≤ 0、params が不正。"""
    op = "ks_step"
    x = _state5(state, "state", op)
    uu = np.asarray(u, dtype=float)
    if uu.shape != (2,) or not np.all(np.isfinite(uu)):
        raise ValueError("%s: u must be a finite (delta_dot, a)" % op)
    h = _positive(dt, "dt", op)
    p = _params(params, op)
    k1 = _ks_rhs(x, uu, p)
    k2 = _ks_rhs(x + 0.5 * h * k1, uu, p)
    k3 = _ks_rhs(x + 0.5 * h * k2, uu, p)
    k4 = _ks_rhs(x + h * k3, uu, p)
    return x + h / 6.0 * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def _rear_to_center(x: float, y: float, psi: float, p: Dict[str, float]) -> Tuple[float, float]:
    return x + p["b"] * math.cos(psi), y + p["b"] * math.sin(psi)


def _center_to_rear(x: float, y: float, psi: float, p: Dict[str, float]) -> Tuple[float, float]:
    return x - p["b"] * math.cos(psi), y - p["b"] * math.sin(psi)


# ----------------------------------------------------------------------------------------------------------------------
# 運転
def _idm(v: float, gap: float, dv: float, *, v0: float, T: float, a: float, b: float, s0: float) -> float:
    """IDM(Treiber 2000)。drivetraffic.idm_accel と同じ式(ここでは import せず自前に書く)。gap = inf で前が空き。"""
    s_star = s0 + max(0.0, v * T + v * dv / (2.0 * math.sqrt(a * b)))
    inter = 0.0 if math.isinf(gap) else (s_star / max(gap, 1e-6)) ** 2
    return a * (1.0 - (v / v0) ** 4 - inter)


def _curvature(P: np.ndarray, cum: np.ndarray, window: float = 6.0) -> np.ndarray:
    """0.5 m 標本の向きの差 / 弧長を window m の移動平均で平滑した |κ|(頂点の粗い折線の角を均す近似)。"""
    d = np.diff(P, axis=0)
    th = np.arctan2(d[:, 1], d[:, 0])
    dth = np.array([_wrap(b - a) for a, b in zip(th[:-1], th[1:])])
    ds = 0.5 * (np.diff(cum)[:-1] + np.diff(cum)[1:])
    kap = np.zeros(len(P))
    kap[1:-1] = dth / np.maximum(ds, 1e-9)
    n = len(P)
    if n < 3:
        return np.abs(kap)
    step = max(float(np.median(np.diff(cum))), 1e-9)
    w = max(int(round(window / step)) | 1, 1)
    pad = w // 2
    kp = np.pad(kap, pad, mode="edge")
    ker = np.ones(w) / w
    sm = np.convolve(kp, ker, mode="valid")
    return np.abs(sm[:n])


def _speed_profile(P: np.ndarray, cum: np.ndarray, v_lim: float, a_lat: float, b: float, window: float = 10.0) -> np.ndarray:
    """曲率の許容速度 √(a_lat/|κ|) を後ろ向きに v_i = min(v_curve_i, √(v_{i+1}² + 2 b Δs)) で繋いだ上限(先の曲がりへ先に減速)。"""
    kap = _curvature(P, cum, window=window)
    with np.errstate(divide="ignore"):
        v_curve = np.where(kap > 1e-9, np.sqrt(a_lat / np.maximum(kap, 1e-9)), np.inf)
    v_allow = np.minimum(v_curve, v_lim)
    for i in range(len(v_allow) - 2, -1, -1):
        ds = cum[i + 1] - cum[i]
        v_allow[i] = min(v_allow[i], math.sqrt(v_allow[i + 1] ** 2 + 2.0 * b * ds))
    return v_allow


def _obstacle_state_at(ob: dict, t: int) -> Optional[np.ndarray]:
    st = ob["states"]
    if ob["static"]:
        return st[0]
    idx = ob.get("_index")
    if idx is None:
        idx = {int(round(r[0])): i for i, r in enumerate(st)}
        ob["_index"] = idx
    i = idx.get(t)
    return None if i is None else st[i]


def _goal_state_ok(scene: dict, goal: dict, t: int, cx: float, cy: float, v: float, psi: float) -> bool:
    lo, hi = goal["time_step"]
    if not (lo <= t <= hi):
        return False
    if goal["position_lanelets"] is not None:
        if not any(_point_in_polygon(scene["lanelets"][lid]["polygon"], (cx, cy)) for lid in goal["position_lanelets"]):
            return False
    elif goal["position_polygon"] is not None:
        if not _point_in_polygon(goal["position_polygon"], (cx, cy)):
            return False
    if goal["velocity"] is not None and not (goal["velocity"][0] <= v <= goal["velocity"][1]):
        return False
    if goal["orientation"] is not None and not (goal["orientation"][0] <= psi <= goal["orientation"][1]):
        return False
    return True


def cr_drive(scene, pp_index: int = 0, *, route=None, v_cruise=None, a_max: float = 1.5, b_max: float = 3.0,
             lookahead: float = 5.0, dt=None, stop_lines=None, hold_s: float = 2.0, goal_inset: float = 0.2,
             idm_T: float = 1.2, stop_margin: float = 0.6, a_lat: float = 2.5, k_v: float = 0.6, follow_width: float = 2.0,
             follow_obstacles: bool = True, curvature_window: float = 10.0, horizon=None, params=None) -> dict:
    """自分の運転手(縦 IDM + pure pursuit)を CommonRoad の planning problem で走らせる。

    縦: IDM(a_max, b_max, idm_T, s₀ = stop_margin)で、目標 = 経路終点(ゴール lanelet の ``goal_inset`` 地点、止まった先行車と
    見なす)・``stop_lines``(経路の弧長の列、または ``"scene"`` で lanelet の stopLine を経路に射影。止まったら ``hold_s`` 秒で発進)・
    経路上の先行障害物(``follow_obstacles``、中心が経路から ``follow_width`` 以内で前にある物)。希望速度 v₀ = min(v_cruise, 経路の
    制限, 曲率の許容 √(a_lat/|κ|)、κ は ``curvature_window`` m の移動平均)。横: 見通し L_d = max(lookahead, k_v·v) の pure pursuit、
    δ̇ ∈ ±0.4。各 step は :func:`ks_step`(RK4)。``horizon`` = step 数(既定 = ゴール time_step 区間の上端 − 初期 time_step)。

    返り値 ``{"kind": "commonroad_run", "t", "time_step", "x", "y" (車両中心), "x_rear", "y_rear", "delta", "v", "psi",
    "u" (T−1, 2), "s" (中心の弧長), "s_front", "lat_err", "v_allow", "stops": [(time_step, s_front, kind, target_s)], "events",
    "route", "goal_reached", "goal_index", "params", "dt", "pp_id", "initial_time_step", "v_limit"}``。

    門: |a| ≤ max(a_max, b_max)、0 ≤ v ≤ v_limit、停止線の前端が 0〜1 m 手前で止まる、cr_feasible が feasible、ゴール到達。

    **Raises** ``ValueError``: scene / route が不正、pp_index 範囲外、速度の上限が決まらない(制限も v_cruise も無い)、
    初期位置がどの lanelet にも無い、stop_lines が経路の外。"""
    op = "cr_drive"
    scene = _check_scene(scene, op)
    p = _params(params, op)
    pps = scene["planning_problems"]
    if not isinstance(pp_index, int) or not (0 <= pp_index < len(pps)):
        raise ValueError("%s: pp_index %r out of range (%d planning problems)" % (op, pp_index, len(pps)))
    pp = pps[pp_index]
    init, goal = pp["initial"], pp["goal"][0]
    a_max = _positive(a_max, "a_max", op)
    b_max = _positive(b_max, "b_max", op)
    lookahead = _positive(lookahead, "lookahead", op)
    hold_s = _nonneg(hold_s, "hold_s", op)
    goal_inset = _finite(goal_inset, "goal_inset", op)
    if not (0.0 <= goal_inset <= 1.0):
        raise ValueError("%s: goal_inset must be in [0, 1]" % op)
    idm_T = _nonneg(idm_T, "idm_T", op)
    stop_margin = _positive(stop_margin, "stop_margin", op)
    a_lat = _positive(a_lat, "a_lat", op)
    k_v = _nonneg(k_v, "k_v", op)
    follow_width = _positive(follow_width, "follow_width", op)
    h = _positive(scene["dt"] if dt is None else dt, "dt", op)

    if route is None:
        starts = _lanelets_containing(scene, (init["x"], init["y"]), init["orientation"])
        if not starts:
            raise ValueError("%s: initial position (%.2f, %.2f) is in no lanelet" % (op, init["x"], init["y"]))
        if goal["position_lanelets"]:
            route = cr_route(scene, starts[0], goal=goal)
        else:
            # 位置の無いゴール: successor を辿れる限り継ぐ(時間だけのゴール)
            ids = [starts[0]]
            L = scene["lanelets"]
            while L[ids[-1]]["successors"] and len(ids) < 8:
                ids.append(L[ids[-1]]["successors"][0])
            route = cr_route(scene, ids[0], ids[-1])
    if not isinstance(route, dict) or route.get("kind") != "commonroad_route":
        raise ValueError("%s: route must come from cr_route" % op)
    P, cum = route["polyline"], route["cum"]
    v_lim_candidates = [c for c in (v_cruise, route["speed_limit_mps"]) if c is not None]
    if not v_lim_candidates:
        raise ValueError("%s: no speed limit on the route; pass v_cruise" % op)
    v_limit = min(_positive(c, "v_cruise/speed_limit", op) for c in v_lim_candidates)
    v_limit = min(v_limit, p["v_max"])
    curvature_window = _positive(curvature_window, "curvature_window", op)
    v_allow = _speed_profile(P, cum, v_limit, a_lat, 0.7 * b_max, window=curvature_window)

    # 目標(前端の弧長で測る)
    if goal["position_lanelets"]:
        gi = route["lanelets"].index(next(l for l in route["lanelets"] if l in goal["position_lanelets"]))
        s_goal = float(route["lanelet_s"][gi] + goal_inset * route["lanelet_len"][gi])
    else:
        s_goal = math.inf
    lines: List[float] = []
    if stop_lines == "scene":
        for lid, s_start in zip(route["lanelets"], route["lanelet_s"]):
            sl = scene["lanelets"][lid]["stop_line"]
            if sl is not None:
                s_mid, _ = _project(P, cum, 0.5 * (sl[0] + sl[1]))
                lines.append(s_mid)
    elif stop_lines is not None:
        for v in stop_lines:
            f = _finite(v, "stop_lines[]", op)
            if not (0.0 <= f <= cum[-1]):
                raise ValueError("%s: stop line at s=%g is outside the route [0, %g]" % (op, f, cum[-1]))
            lines.append(f)
    lines.sort()

    t0 = init["time_step"]
    if horizon is None:
        n = int(goal["time_step"][1]) - t0
    else:
        n = int(horizon)
    if n < 1:
        raise ValueError("%s: horizon must be >= 1 step (goal time %r, initial %d)" % (op, goal["time_step"], t0))

    xr, yr = _center_to_rear(init["x"], init["y"], init["orientation"], p)
    x = np.array([xr, yr, 0.0, init["velocity"], init["orientation"]])
    half_len = 0.5 * p["length"]
    states = [x.copy()]
    inputs: List[Tuple[float, float]] = []
    s_hist, lat_hist, v_allow_hist = [], [], []
    stops: List[Tuple[int, float, str, float]] = []
    events: List[str] = []
    line_idx = 0
    hold_until = -1.0
    stopped_kind: Optional[str] = None
    v_stop = 0.3

    for k in range(n + 1):
        t = t0 + k
        cx, cy = _rear_to_center(x[0], x[1], x[4], p)
        s_c, lat = _project(P, cum, (cx, cy))
        s_front = s_c + half_len
        v = max(x[3], 0.0)
        v0_here = float(np.interp(s_c, cum, v_allow))
        v0_here = max(v0_here, 0.5)
        s_hist.append(s_c)
        lat_hist.append(lat)
        v_allow_hist.append(v0_here)
        if k == n:
            break
        tt = k * h

        # 目標の候補(gap, Δv, kind)
        cands: List[Tuple[float, float, str, float]] = []
        if math.isfinite(s_goal):
            cands.append((s_goal - s_front, v, "goal", s_goal))
        if line_idx < len(lines) and tt >= hold_until:
            cands.append((lines[line_idx] - s_front, v, "stop_line", lines[line_idx]))
        if follow_obstacles:
            for ob in scene["obstacles"]:
                st = _obstacle_state_at(ob, t)
                if st is None:
                    continue
                so, lo = _project(P, cum, (st[1], st[2]))
                if abs(lo) > follow_width or so <= s_c:
                    continue
                gap_o = so - 0.5 * ob["shape"]["length"] - s_front
                if gap_o <= 0 or so > s_c + 80.0:
                    continue
                v_o = st[4] * math.cos(st[3] - x[4])
                cands.append((gap_o, v - v_o, "obstacle:%d" % ob["id"], so))
        # 停止中の扱い
        released = tt >= hold_until
        if stopped_kind is not None and v <= 1e-12:
            if stopped_kind == "goal" or not released:
                inputs.append((0.0, 0.0))
                states.append(x.copy())
                continue
            events.append("t=%d released after hold at %s" % (t, stopped_kind))
            stopped_kind = None
            line_idx += 1
            cands = [c for c in cands if c[2] != "stop_line"]
            if line_idx < len(lines):
                cands.append((lines[line_idx] - s_front, v, "stop_line", lines[line_idx]))

        a_cmd = _idm(v, math.inf, 0.0, v0=v0_here, T=idm_T, a=a_max, b=b_max, s0=stop_margin)
        target_kind = None
        for gap, dv, kind, s_t in cands:
            if gap <= 0.0:
                a_c, kind_c = -b_max, kind
            else:
                a_c, kind_c = _idm(v, gap, dv, v0=v0_here, T=idm_T, a=a_max, b=b_max, s0=stop_margin), kind
            if a_c < a_cmd:
                a_cmd, target_kind = a_c, kind_c
        a_cmd = min(a_max, max(-b_max, a_cmd))
        # 停止の仕上げ: IDM の停止は漸近的なので、目標の手前(gap ≤ s₀ + 0.4)で遅ければ(v ≤ v_stop)b_max 以内で v をちょうど 0 に
        if target_kind in ("goal", "stop_line") and v <= v_stop and a_cmd <= 0.0:
            gap = next(c[0] for c in cands if c[2] == target_kind)
            if gap <= stop_margin + 0.4:
                a_cmd = max(-b_max, -v / h)
                if v + a_cmd * h <= 1e-12:
                    stopped_kind = target_kind
                    hold_until = tt + h + hold_s
                    stops.append((t + 1, s_front, target_kind, next(c[3] for c in cands if c[2] == target_kind)))
                    events.append("t=%d stop at %s (front %.2f m before)" % (t + 1, target_kind, gap))
        if v + a_cmd * h < 0.0:
            a_cmd = -v / h
        # 横: pure pursuit(後軸から)
        if v <= 1e-12:
            d_dot = 0.0
        else:
            s_rear, _ = _project(P, cum, (x[0], x[1]))
            ld = max(lookahead, k_v * v)
            tgt = _point_at(P, cum, s_rear + ld)
            dx, dy = tgt[0] - x[0], tgt[1] - x[1]
            dist = max(math.hypot(dx, dy), 1e-6)
            alpha = _wrap(math.atan2(dy, dx) - x[4])
            d_des = math.atan2(2.0 * p["l_wb"] * math.sin(alpha), dist)
            d_des = min(p["delta_max"], max(p["delta_min"], d_des))
            d_dot = min(p["ddelta_max"], max(p["ddelta_min"], (d_des - x[2]) / h))
        u = (float(d_dot), float(a_cmd))
        x = ks_step(x, u, h, p)
        if abs(x[3]) < 1e-12:
            x[3] = 0.0
        inputs.append(u)
        states.append(x.copy())

    S = np.asarray(states)
    T = len(S)
    ts = np.arange(t0, t0 + T)
    cxy = np.array([_rear_to_center(r[0], r[1], r[4], p) for r in S])
    goal_idx = -1
    for k in range(T - 1, -1, -1):
        if _goal_state_ok(scene, goal, int(ts[k]), cxy[k, 0], cxy[k, 1], S[k, 3], S[k, 4]):
            goal_idx = k
            break
    return {
        "kind": "commonroad_run", "t": np.arange(T) * h, "time_step": ts, "x": cxy[:, 0], "y": cxy[:, 1],
        "x_rear": S[:, 0], "y_rear": S[:, 1], "delta": S[:, 2], "v": S[:, 3], "psi": S[:, 4],
        "u": np.asarray(inputs, dtype=float).reshape(T - 1, 2), "s": np.asarray(s_hist), "s_front": np.asarray(s_hist) + half_len,
        "lat_err": np.asarray(lat_hist), "v_allow": np.asarray(v_allow_hist), "stops": stops, "events": events, "route": route,
        "stop_lines": lines, "s_goal": s_goal, "goal_reached": goal_idx >= 0, "goal_index": goal_idx, "params": p, "dt": h,
        "pp_id": pp["id"], "initial_time_step": t0, "v_limit": v_limit,
        "driver": {"a_max": a_max, "b_max": b_max, "idm_T": idm_T, "stop_margin": stop_margin, "lookahead": lookahead, "k_v": k_v,
                   "a_lat": a_lat, "hold_s": hold_s, "goal_inset": goal_inset, "v_cruise": v_cruise},
    }


def cr_drive_sweep(scene, pp_index: int = 0, *, grid=None, margin: float = 0.15, **kwargs) -> dict:
    """ルールベースの gap acceptance: 運転手の母数の格子を穏やかな順に試し、**最初に全部の門を通った走行** を返す。

    門 = ゴール到達 ∧ :func:`cr_feasible` ∧ :func:`cr_collision` で障害物なし(``margin`` だけ膨らませた判定)∧ 道路境界なし。
    ``grid`` は ``{"a_lat": (...), "lookahead": (...), "k_v": (...), "v_cruise": (...)}`` 形式(既定 = a_lat 2.5→10、lookahead 5/8、
    k_v 0.6/1.0、v_cruise None)。他の kwargs は :func:`cr_drive` へ。

    返り値 ``{"run" (通った走行 | None), "settings" (その母数 | None), "tries": [{"settings", "goal_reached", "feasible",
    "obstacle_collision", "boundary_violation", "first_collision"}], "n_tries"}``。通る物が無ければ ``run`` は None(ValueError ではない)。

    **Raises** ``ValueError``: grid のキーが上記以外、margin < 0。"""
    op = "cr_drive_sweep"
    margin = _nonneg(margin, "margin", op)
    default = {"a_lat": (2.5, 4.0, 6.0, 8.0, 10.0), "lookahead": (5.0, 8.0), "k_v": (0.6, 1.0), "v_cruise": (None,)}
    g = dict(default)
    if grid is not None:
        if not isinstance(grid, dict) or any(k not in default for k in grid):
            raise ValueError("%s: grid keys must be a subset of %s" % (op, tuple(default)))
        g.update({k: tuple(v) for k, v in grid.items()})
    tries: List[dict] = []
    for a_lat in g["a_lat"]:
        for lookahead in g["lookahead"]:
            for k_v in g["k_v"]:
                for v_cruise in g["v_cruise"]:
                    settings = {"a_lat": a_lat, "lookahead": lookahead, "k_v": k_v, "v_cruise": v_cruise}
                    run = cr_drive(scene, pp_index, **settings, **kwargs)
                    f = cr_feasible(run)
                    c = cr_collision(scene, run, margin=margin)
                    rec = {"settings": settings, "goal_reached": run["goal_reached"], "feasible": f["feasible"],
                           "obstacle_collision": c["obstacle_collision"], "boundary_violation": c["boundary_violation"],
                           "first_collision": c["first_collision"]}
                    tries.append(rec)
                    if run["goal_reached"] and f["feasible"] and not c["obstacle_collision"] and not c["boundary_violation"]:
                        return {"run": run, "settings": settings, "tries": tries, "n_tries": len(tries)}
    return {"run": None, "settings": None, "tries": tries, "n_tries": len(tries)}


# ----------------------------------------------------------------------------------------------------------------------
# 採点器の第 2 実装
def cr_feasible(run, *, params=None, tol=(0.02, 0.02, 0.03)) -> dict:
    """運動学の実現可能性(採点器 ``solution_feasible`` と同じ考え方の第 2 実装)。

    各遷移で記録した u から :func:`ks_step` を回し、次の状態と |Δx|, |Δy| < tol[0], tol[1]、|Δψ| < tol[2] か、u が制限内か
    (δ̇ ∈ [ddelta_min, ddelta_max]、|a| ≤ a_max)、摩擦円 a² + (v ψ̇)² ≤ a_max² か(ψ̇ = v/l_wb tan δ)。

    返り値 ``{"feasible", "max_pos_err", "max_psi_err", "violations": [(k, reason)], "n_transitions"}``。

    **Raises** ``ValueError``: run が cr_drive の物でない、tol が 3 要素でない。"""
    op = "cr_feasible"
    run = _check_run(run, op)
    p = _params(run["params"] if params is None else params, op)
    tol = tuple(_positive(t, "tol[]", op) for t in tol)
    if len(tol) != 3:
        raise ValueError("%s: tol must have 3 entries (x, y, psi)" % op)
    X = np.column_stack([run["x_rear"], run["y_rear"], run["delta"], run["v"], run["psi"]])
    U = np.asarray(run["u"], dtype=float)
    h = _positive(run["dt"], "dt", op)
    viol: List[Tuple[int, str]] = []
    max_pos, max_psi = 0.0, 0.0
    for k in range(len(U)):
        u = U[k]
        if not (p["ddelta_min"] - _INPUT_TOL <= u[0] <= p["ddelta_max"] + _INPUT_TOL):
            viol.append((k, "steering rate %.4f outside [%g, %g]" % (u[0], p["ddelta_min"], p["ddelta_max"])))
        if abs(u[1]) > p["a_max"] + _INPUT_TOL:
            viol.append((k, "acceleration %.4f outside +-%g" % (u[1], p["a_max"])))
        psi_dot = X[k, 3] / p["l_wb"] * math.tan(X[k, 2])
        if u[1] ** 2 + (X[k, 3] * psi_dot) ** 2 > p["a_max"] ** 2 + _INPUT_TOL:
            viol.append((k, "friction circle a^2 + (v psi_dot)^2 = %.3f > %.3f" % (u[1] ** 2 + (X[k, 3] * psi_dot) ** 2, p["a_max"] ** 2)))
        x_sim = ks_step(X[k], u, h, p)
        dx, dy = abs(x_sim[0] - X[k + 1, 0]), abs(x_sim[1] - X[k + 1, 1])
        dpsi = abs(_wrap(x_sim[4] - X[k + 1, 4]))
        max_pos = max(max_pos, dx, dy)
        max_psi = max(max_psi, dpsi)
        if dx >= tol[0] or dy >= tol[1] or dpsi >= tol[2]:
            viol.append((k, "transition error dx=%.4f dy=%.4f dpsi=%.4f" % (dx, dy, dpsi)))
    return {"feasible": not viol, "max_pos_err": max_pos, "max_psi_err": max_psi, "violations": viol, "n_transitions": len(U)}


def cr_collision(scene, run, *, margin: float = 0.0, lanelets: str = "all") -> dict:
    """障害物との衝突(矩形同士の SAT、time_step ごと)と道路境界(車両 4 角が lanelet 多角形の和集合に入るか)。

    ``lanelets="all"``(既定)は場面の全 lanelet(採点器の boundary_collision と同じ範囲)、``"route"`` は経路の lanelet だけ。
    ``margin`` は障害物の SAT を膨らませる距離(m)。

    返り値 ``{"obstacle_collision", "first_collision": (time_step, obstacle_id) | None, "boundary_violation",
    "first_outside": time_step | None, "n_collisions", "n_outside"}``。

    **Raises** ``ValueError``: scene / run が不正、lanelets が "all"/"route" 以外、margin < 0。"""
    op = "cr_collision"
    scene = _check_scene(scene, op)
    run = _check_run(run, op)
    margin = _nonneg(margin, "margin", op)
    if lanelets not in ("all", "route"):
        raise ValueError("%s: lanelets must be 'all' or 'route', got %r" % (op, lanelets))
    p = _params(run["params"], op)
    if lanelets == "route":
        if not isinstance(run.get("route"), dict):
            raise ValueError("%s: run has no route for lanelets='route'" % op)
        polys = run["route"]["polygons"]
    else:
        polys = [la["polygon"] for la in scene["lanelets"].values()]
    first_col, first_out, n_col, n_out = None, None, 0, 0
    for k, t in enumerate(run["time_step"]):
        ego = _rect_corners(run["x"][k], run["y"][k], run["psi"][k], p["length"], p["width"])
        hit = False
        for ob in scene["obstacles"]:
            st = _obstacle_state_at(ob, int(t))
            if st is None:
                continue
            sh = ob["shape"]
            c, s = math.cos(st[3]), math.sin(st[3])
            ocx = st[1] + c * sh["center"][0] - s * sh["center"][1]
            ocy = st[2] + s * sh["center"][0] + c * sh["center"][1]
            other = _rect_corners(ocx, ocy, st[3] + sh["orientation"], sh["length"], sh["width"])
            if _sat_overlap(ego, other, margin):
                hit = True
                if first_col is None:
                    first_col = (int(t), ob["id"])
        n_col += int(hit)
        outside = any(not any(_point_in_polygon(poly, corner, margin=1e-6) for poly in polys) for corner in ego)
        if outside:
            n_out += 1
            if first_out is None:
                first_out = int(t)
    return {"obstacle_collision": first_col is not None, "first_collision": first_col, "boundary_violation": first_out is not None,
            "first_outside": first_out, "n_collisions": n_col, "n_outside": n_out}


# ----------------------------------------------------------------------------------------------------------------------
# 書く / 公式の結果を読む
def cr_solution_xml(scene, run, *, vehicle_model: str = "KS", vehicle_type: str = "BMW_320i", cost: str = "JB1",
                    benchmark_version: str = "2020a", date=None) -> str:
    """公式 solution XML(commonroad-io ``CommonRoadSolutionWriter`` と同じ形)を文字列で返す。

    ``<CommonRoadSolution benchmark_id="KS2:JB1:<scenario id>:2020a" date="YYYY-MM-DDTHH:MM:SS">`` の中に
    ``<ksTrajectory planningProblem="<pp id>">`` と ``ksState{x, y, steeringAngle, velocity, orientation, time}``。
    位置は **車両中心**(run["x"], run["y"])。``date`` を渡すと再現可能(省略で今)。

    **Raises** ``ValueError``: vehicle_model が "KS" 以外(状態が KS の物なので)、vehicle_type が未知、run が不正。"""
    op = "cr_solution_xml"
    scene = _check_scene(scene, op)
    run = _check_run(run, op)
    if vehicle_model != "KS":
        raise ValueError("%s: only vehicle_model 'KS' is written (run states are KS states)" % op)
    if vehicle_type not in VEHICLE_TYPE_IDS:
        raise ValueError("%s: vehicle_type must be one of %s" % (op, tuple(VEHICLE_TYPE_IDS)))
    if not cost or ":" in cost:
        raise ValueError("%s: cost must be a cost function id like 'JB1'" % op)
    when = datetime.now() if date is None else date
    if not isinstance(when, datetime):
        raise ValueError("%s: date must be a datetime" % op)
    bid = "%s%d:%s:%s:%s" % (vehicle_model, VEHICLE_TYPE_IDS[vehicle_type], cost, scene["id"], benchmark_version)
    lines = ['<?xml version="1.0" ?>',
             '<CommonRoadSolution benchmark_id="%s" date="%s">' % (bid, when.strftime("%Y-%m-%dT%H:%M:%S")),
             '  <ksTrajectory planningProblem="%d">' % int(run["pp_id"])]
    for k in range(len(run["time_step"])):
        lines += ["    <ksState>",
                  "      <x>%r</x>" % float(run["x"][k]), "      <y>%r</y>" % float(run["y"][k]),
                  "      <steeringAngle>%r</steeringAngle>" % float(run["delta"][k]),
                  "      <velocity>%r</velocity>" % float(run["v"][k]),
                  "      <orientation>%r</orientation>" % float(run["psi"][k]),
                  "      <time>%d</time>" % int(run["time_step"][k]),
                  "    </ksState>"]
    lines += ["  </ksTrajectory>", "</CommonRoadSolution>", ""]
    return "\n".join(lines)


def cr_checker_result(path) -> dict:
    """WSL の公式チェッカー(tools/check_solution_json.py)が書いた JSON を読む。

    必須キー :data:`CHECKER_KEYS`(``valid`` / ``goal_reached`` / ``feasible`` / ``obstacle_collision`` / ``boundary_collision``
    は bool、``scenario`` / ``solution`` / ``checker_version`` は文字列)。それ以外のキー(``details`` 等)はそのまま返す。

    **Raises** ``ValueError``: ファイルが無い、JSON でない、必須キーの欠落、型違い。"""
    op = "cr_checker_result"
    p = Path(path)
    if not p.is_file():
        raise ValueError("%s: file not found: %s" % (op, p))
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as ex:
        raise ValueError("%s: not JSON: %s" % (op, ex))
    if not isinstance(data, dict):
        raise ValueError("%s: JSON root must be an object" % op)
    for k in CHECKER_KEYS:
        if k not in data:
            raise ValueError("%s: missing key %r" % (op, k))
    for k in ("valid", "goal_reached", "feasible", "obstacle_collision", "boundary_collision"):
        if not isinstance(data[k], bool):
            raise ValueError("%s: %r must be a bool, got %r" % (op, k, data[k]))
    for k in ("scenario", "solution", "checker_version"):
        if not isinstance(data[k], str) or not data[k]:
            raise ValueError("%s: %r must be a non-empty string" % (op, k))
    return dict(data)


# ----------------------------------------------------------------------------------------------------------------------
# 合成場面
def _xml_points(P: np.ndarray, indent: str) -> str:
    return "".join("%s<point>\n%s  <x>%r</x>\n%s  <y>%r</y>\n%s</point>\n" % (indent, indent, float(x), indent, float(y), indent)
                   for x, y in P)


def cr_synthetic(kind: str = "tjunction", *, dt: float = 0.1, speed_limit: float = 13.89, v0: float = 8.0) -> str:
    """テスト・CI 用の最小 CommonRoad 2020a XML を文字列で返す。

    ``tjunction``: lanelet 100(直線 40 m, +x)→ 101(左 90° 円弧、中心線半径 12 m)→ 102(直線 40 m, +y)、対向 lanelet 200
    (100 の左隣、−x 向き)に対向車 1 台(8 m/s、矩形 4.5 × 1.8)、標識 274(speed_limit m/s)は 3 本すべてに、stopLine は 100 の
    終端(交差点の手前)、planning problem = (5, 0) から v0 でゴール lanelet 102・time_step [100, 200]・速度 [0, 15]。
    ``straight``: 101 も直線(3 本で 120 m)。``blocked``: straight の 101 の中央に静止障害物(衝突の門用)。
    車線幅 3.5 m。中心線の長さ = 40 + 6π(≒ 18.85、円弧は 16 分割の折線) + 40(tjunction)/ 120(straight)。

    **Raises** ``ValueError``: kind が :data:`SYNTHETIC_KINDS` 以外、dt / speed_limit / v0 が正でない。"""
    op = "cr_synthetic"
    if kind not in SYNTHETIC_KINDS:
        raise ValueError("%s: kind must be one of %s, got %r" % (op, SYNTHETIC_KINDS, kind))
    dt = _positive(dt, "dt", op)
    speed_limit = _positive(speed_limit, "speed_limit", op)
    v0 = _nonneg(v0, "v0", op)
    hw = 1.75
    xs0 = np.linspace(0.0, 40.0, 5)
    l100 = np.column_stack([xs0, np.full(5, hw)])
    r100 = np.column_stack([xs0, np.full(5, -hw)])
    if kind == "tjunction":
        R = 12.0
        th = np.linspace(-0.5 * math.pi, 0.0, 17)
        cx, cy = 40.0, R
        l101 = np.column_stack([cx + (R - hw) * np.cos(th), cy + (R - hw) * np.sin(th)])
        r101 = np.column_stack([cx + (R + hw) * np.cos(th), cy + (R + hw) * np.sin(th)])
        ys2 = np.linspace(R, R + 40.0, 5)
        l102 = np.column_stack([np.full(5, 40.0 + R - hw), ys2])
        r102 = np.column_stack([np.full(5, 40.0 + R + hw), ys2])
    else:
        xs1 = np.linspace(40.0, 80.0, 5)
        xs2 = np.linspace(80.0, 120.0, 5)
        l101 = np.column_stack([xs1, np.full(5, hw)])
        r101 = np.column_stack([xs1, np.full(5, -hw)])
        l102 = np.column_stack([xs2, np.full(5, hw)])
        r102 = np.column_stack([xs2, np.full(5, -hw)])
    # 対向 lanelet 200: 100 の左隣、−x 向き(left bound は進行方向の左 = y 小さい側)
    xs_opp = xs0[::-1]
    l200 = np.column_stack([xs_opp, np.full(5, hw)])
    r200 = np.column_stack([xs_opp, np.full(5, 3 * hw)])

    def lanelet(lid, L, Rb, pred, succ, adj_left=None, adj_left_dir="opposite", stop=None, sign=None):
        s = '  <lanelet id="%d">\n    <leftBound>\n%s    </leftBound>\n    <rightBound>\n%s    </rightBound>\n' % (
            lid, _xml_points(L, "      "), _xml_points(Rb, "      "))
        for pr in pred:
            s += '    <predecessor ref="%d"/>\n' % pr
        for su in succ:
            s += '    <successor ref="%d"/>\n' % su
        if adj_left is not None:
            s += '    <adjacentLeft ref="%d" drivingDir="%s"/>\n' % (adj_left, adj_left_dir)
        if stop is not None:
            s += "    <stopLine>\n%s      <lineMarking>solid</lineMarking>\n    </stopLine>\n" % _xml_points(stop, "      ")
        s += "    <laneletType>urban</laneletType>\n"
        if sign is not None:
            s += '    <trafficSignRef ref="%d"/>\n' % sign
        return s + "  </lanelet>\n"

    stop100 = np.array([[40.0, -hw], [40.0, hw]])
    body = lanelet(100, l100, r100, [], [101], adj_left=200, stop=stop100, sign=300)
    body += lanelet(101, l101, r101, [100], [102], sign=300)
    body += lanelet(102, l102, r102, [101], [], sign=300)
    body += lanelet(200, l200, r200, [], [], sign=300)
    body += ('  <trafficSign id="300">\n    <trafficSignElement>\n      <trafficSignID>274</trafficSignID>\n'
             "      <additionalValue>%r</additionalValue>\n    </trafficSignElement>\n    <position>\n      <point>\n"
             "        <x>0.0</x>\n        <y>2.0</y>\n      </point>\n    </position>\n    <virtual>false</virtual>\n  </trafficSign>\n"
             % float(speed_limit))

    def state(t, x, y, psi, v, tag="state", indent="      "):
        i = indent
        return ("%s<%s>\n%s  <position>\n%s    <point>\n%s      <x>%r</x>\n%s      <y>%r</y>\n%s    </point>\n%s  </position>\n"
                "%s  <orientation>\n%s    <exact>%r</exact>\n%s  </orientation>\n%s  <time>\n%s    <exact>%d</exact>\n%s  </time>\n"
                "%s  <velocity>\n%s    <exact>%r</exact>\n%s  </velocity>\n%s</%s>\n"
                % (i, tag, i, i, i, float(x), i, float(y), i, i, i, i, float(psi), i, i, i, int(t), i, i, i, float(v), i, i, tag))

    n_steps = 200
    v_opp = 8.0
    body += ('  <dynamicObstacle id="1">\n    <type>car</type>\n    <shape>\n      <rectangle>\n        <length>4.5</length>\n'
             "        <width>1.8</width>\n      </rectangle>\n    </shape>\n")
    body += state(0, 60.0, 2 * hw, math.pi, v_opp, tag="initialState", indent="    ")
    body += "    <trajectory>\n"
    for t in range(1, n_steps + 1):
        body += state(t, 60.0 - v_opp * t * dt, 2 * hw, math.pi, v_opp)
    body += "    </trajectory>\n  </dynamicObstacle>\n"
    if kind == "blocked":
        body += ('  <staticObstacle id="2">\n    <type>parkedVehicle</type>\n    <shape>\n      <rectangle>\n        <length>4.5</length>\n'
                 "        <width>1.8</width>\n      </rectangle>\n    </shape>\n    <initialState>\n      <position>\n        <point>\n"
                 "          <x>60.0</x>\n          <y>0.0</y>\n        </point>\n      </position>\n      <orientation>\n        <exact>0.0</exact>\n"
                 "      </orientation>\n      <time>\n        <exact>0</exact>\n      </time>\n    </initialState>\n  </staticObstacle>\n")
    body += ('  <planningProblem id="1">\n    <initialState>\n      <position>\n        <point>\n          <x>5.0</x>\n          <y>0.0</y>\n'
             "        </point>\n      </position>\n      <orientation>\n        <exact>0.0</exact>\n      </orientation>\n      <time>\n"
             "        <exact>0</exact>\n      </time>\n      <velocity>\n        <exact>%r</exact>\n      </velocity>\n      <acceleration>\n"
             "        <exact>0.0</exact>\n      </acceleration>\n      <yawRate>\n        <exact>0.0</exact>\n      </yawRate>\n      <slipAngle>\n"
             "        <exact>0.0</exact>\n      </slipAngle>\n    </initialState>\n    <goalState>\n      <position>\n        <lanelet ref=\"102\"/>\n"
             "      </position>\n      <time>\n        <intervalStart>100</intervalStart>\n        <intervalEnd>200</intervalEnd>\n      </time>\n"
             "      <velocity>\n        <intervalStart>0.0</intervalStart>\n        <intervalEnd>15.0</intervalEnd>\n      </velocity>\n"
             "    </goalState>\n  </planningProblem>\n" % float(v0))
    head = ("<?xml version='1.0' encoding='UTF-8'?>\n"
            '<commonRoad timeStepSize="%r" commonRoadVersion="2020a" author="drivecommonroad synthetic" affiliation="Fullseye" '
            'source="cr_synthetic(%s)" benchmarkID="ZAM_Synthetic%s-1_1_T-1" date="2026-10-04">\n'
            "  <location>\n    <geoNameId>-999</geoNameId>\n    <gpsLatitude>999.0</gpsLatitude>\n    <gpsLongitude>999.0</gpsLongitude>\n"
            "  </location>\n  <scenarioTags>\n    <urban/>\n  </scenarioTags>\n" % (float(dt), kind, kind.capitalize()))
    return head + body + "</commonRoad>\n"
