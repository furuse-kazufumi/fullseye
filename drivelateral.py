# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""横の運動: 摩擦円・カーブの限界速度・2 輪等価モデル・内輪差・クロソイド・車線の中の位置保持・速度計画・TLC。

## 何を作るか

自動運転 PoC 第 10 回「横の運動」の部品を numpy だけで持つ。第 9 回までは縦(止まれるか)と判断(いつ・誰に譲るか)を
扱った。ここでは **曲がる** —— カーブの手前でどこまで減速するか、車線の中のどこを通るか、左折で後輪がどれだけ内側を
通るか —— を、**学習を使わない** 閉形式・幾何・公表値・条文の判定・古典的な数値計算の op にする。各 op は独立な経路の
検算(門)が立つものだけを置いた:

1. 摩擦と路面(``friction_circle_usage`` / ``curve_speed_limit`` / ``design_min_radius``)。
2. 2 輪等価モデル(``understeer_gradient`` / ``steady_cornering`` / ``bicycle_model_step``)。
3. 低速の幾何(``ackermann_steer_angles`` / ``offtracking_circle`` / ``rear_axle_path``)。
4. 緩和曲線(``fresnel_integrals`` / ``clothoid_points`` / ``clothoid_design``)。
5. 位置保持の古典的な制御則(``pure_pursuit_curvature`` / ``pure_pursuit_circle_offset`` / ``stanley_steer`` /
   ``stanley_straight_decay``)。
6. 速度計画と車線(``curvature_speed_plan`` / ``lateral_offset`` / ``time_to_line_crossing`` / ``turn_maneuver_check``)。

## 真値にする閉形式(門)

* 摩擦円: 縦横の加速度の合成 √(a_x² + a_y²) ≤ μg(使用率 = 合成 / μg)。
* 片勾配つきの曲線(道路構造令の解説 (2) 式): Z cos α − G sin α ≤ f (Z sin α + G cos α)、Z = G v²/(gR)、i = tan α
  → v²/(gR) ≤ (i + f)/(1 − i f)。設計の式 (3) R ≥ V²/(127(i + f)) は分母の i f を落とし 127 ≈ 3.6² × 9.81 とした形。
* 線形 2 自由度モデル(2 輪等価、軸ごとのコーナリングパワー C_f, C_r [N/rad]):
  m(v̇_y + u r) = F_f + F_r、I_z ṙ = l_f F_f − l_r F_r、α_f = δ − (v_y + l_f r)/u、α_r = −(v_y − l_r r)/u。
  定常円旋回: δ = L/R + K a_y、**K = (m/L)(l_r/C_f − l_f/C_r)** [rad/(m/s²)](アンダーステア勾配)、
  ヨーレートゲイン r/δ = (u/L)/(1 + K u²/L)、横すべり角 β = l_r/R − m l_f u²/(C_r L R)。K > 0 で特性速度 √(L/K)
  (ゲインが最大)、K < 0 で臨界速度 √(−L/K)(行列の行列式が 0 = 不安定の境)。
* アッカーマン: 後車軸の中心の旋回半径 R、輪距 t → δ_in = atan(L/(R − t/2))、δ_out = atan(L/(R + t/2))、
  cot δ_out − cot δ_in = t/L。
* 内輪差(低速・すべりなし、後車軸の中心は前車軸の中心を長さ L の棒で引く追跡曲線): 前車軸の中心が半径 R の円に
  入ってからの弧長 s で、棒と前の速度のなす角 γ は dγ/ds = 1/R − sin γ / L(Riccati 型・変数分離)。
  t = tan(γ/2) と置くと ∫ は対数になり **s → γ の閉形式**(``offtracking_circle``)。定常 sin γ* = L/R、
  後車軸の中心の半径 √(R² − L²)。後輪の内側の半径 = √(R² + L² − 2RL sin γ) − t/2(定常)。
* 追跡曲線を直線の上で: 前が直線を Δ 進むと tan(θ/2) = tan(θ₀/2) e^{−Δ/L}(θ = 棒と直線のなす角)。折線の前の軌跡に
  対して **区間ごとに厳密**(``rear_axle_path``)。円を細かい折線にすると ``offtracking_circle`` に 2 次で近づく(門)。
* クロソイド: 曲率 κ(s) = s/A²、A² = R L。座標 = A√π (C(s/(A√π)), S(s/(A√π)))(フレネル積分)。一定速度 v で走ると
  横加速度の変化率 = v³/A² = v³/(R L)(道路構造令の解説の Shortt 式 L ≥ (V/3.6)³/(P R) と同じ式)。
* pure pursuit(Coulter 1992): 前方注視点が車の座標で角 α・距離 L_d → 曲率 κ = 2 sin α / L_d。
  定常円(半径 R)の上で、曲率の指令に対し実際の曲率が κ_cmd / (1 + K v²/L) になる(アンダーステア)とき、車の円の
  半径は **ρ = √(R² + (K v²/L) L_d²)**(この版で導いた閉形式、``pure_pursuit_circle_offset``)。K = 0 なら ρ = R
  (後車軸を基準にした運動学では定常の横ずれ 0)。
* Stanley(Thrun ほか 2006, Hoffmann ほか 2007): δ = ψ_e + atan(−k e/(k_s + v))(e は経路の左を正)。直線では前車軸の
  横ずれが ė = −v k e / √((k_s + v)² + k² e²) に従い(ψ に依らない)、F(e) = √(a² + k²e²) − a ln((a + √(a² + k²e²))/(k|e|))、
  a = k_s + v が F(e(t)) = F(e₀) − v k t を満たす(``stanley_straight_decay``)。
* 速度計画(前向き・後ろ向きの 2 パス): 上限 v ≤ √(a_lat/|κ|)、各刻みで v² を s に一次(一定の加減速)とし、
  縦の加速度を摩擦円の残り √(a_tot² − (v²κ)²) で抑える。刻みの両端の |κ| の大きい方で解く 2 次方程式で、刻みの中の
  **どこでも** 摩擦円を守る(連続の保証)。
* TLC(time to line crossing, Mammar ほか 2006): 車が今の曲率のまま円を走るとして境界(直線または同心円)に届く
  時間 = 円と直線 / 円と円の交点の弧長 / v。

## 出典(書誌)と確認の状態

``SOURCES`` に 1 つずつ。一次で本文を確かめたもの = primary、教科書・論文の式 = literature(式は閉形式どうしと
数値積分の門で検算)、数値の根拠が一次で確認できないもの = **assumed(仮定)**。

## 単位と座標

m, s, m/s, m/s², rad, N, kg。2D の世界: x 東、y 北、ψ は +x から反時計回り。車の座標: x 前、y 左。
「左を正」の横ずれ(経路の進行方向の左)。左側通行(日本)。

## 限界(self_reported)

* 線形 2 自由度モデルはタイヤの飽和を持たない(摩擦円の外では現実と離れる)。摩擦円を出るかどうかは別の op
  (``friction_circle_usage``)で判定し、モデルの中では扱わない。
* 内輪差は低速・すべりなし・単車(牽引なし)の運動学。荷重移動・タイヤの横すべりで実車は少し違う。
* 道路構造令の表の値は公表値として持つが、表を式で再現するのに要る横すべり摩擦係数 f(解説の図)は本文の
  文字としては読めず **未確認**。表を式で厳密に再現する門は置かない(逆算した i + f を報告するだけ)。
"""
from __future__ import annotations

import math
from typing import Dict, Optional

import numpy as np

__all__ = [
    "SOURCES", "G", "ROAD_MIN_RADIUS", "TRANSITION_LENGTH", "MAX_SUPERELEVATION",
    "friction_circle_usage", "curve_speed_limit", "design_min_radius",
    "understeer_gradient", "steady_cornering", "bicycle_model_step",
    "ackermann_steer_angles", "offtracking_circle", "rear_axle_path",
    "fresnel_integrals", "clothoid_points", "clothoid_design",
    "pure_pursuit_curvature", "pure_pursuit_circle_offset", "stanley_steer", "stanley_straight_decay",
    "curvature_speed_plan", "lateral_offset", "time_to_line_crossing", "turn_maneuver_check",
]

G = 9.81    # 重力の加速度 [m/s²](道路構造令の解説 (1) 式の「≒ 9.81」に合わせる)

#: 道路構造令 第 15 条の表: 設計速度 [km/h] → (曲線半径の規定値 [m], 特例値 [m] または None)
ROAD_MIN_RADIUS: Dict[int, tuple] = {120: (710, 570), 100: (460, 380), 80: (280, 230), 60: (150, 120), 50: (100, 80),
                                     40: (60, 50), 30: (30, None), 20: (15, None)}
#: 道路構造令 第 18 条 3 項の表: 設計速度 [km/h] → 緩和区間の長さ [m]
TRANSITION_LENGTH: Dict[int, int] = {120: 100, 100: 85, 80: 70, 60: 50, 50: 40, 40: 35, 30: 25, 20: 20}
#: 道路構造令 第 16 条の表: 最大片勾配 [%](第1〜3種: 積雪寒冷のはなはだしい 6・その他の積雪寒冷 8・その他 10、第4種 6)
MAX_SUPERELEVATION: Dict[str, float] = {"snow_severe": 0.06, "snow": 0.08, "other": 0.10, "class4": 0.06}

SOURCES: Dict[str, Dict[str, str]] = {
    "road_min_radius_table": {
        "status": "primary", "value": "第15条の表(規定値・特例値)",
        "source": "道路構造令(昭和45年政令第320号)第15条。国土交通省 道路局 掲載の本文(平成15年7月改正版 "
                  "mlit.go.jp/road/sign/kouzourei/0.pdf 16–17 頁)を文字で確認。e-Gov は 2026-10-01 保守中"},
    "transition_length_table": {
        "status": "primary", "value": "第18条3項の表", "source": "同上 17 頁"},
    "max_superelevation_table": {
        "status": "primary", "value": "第16条の表", "source": "同上 17 頁"},
    "curve_force_balance": {
        "status": "primary", "value": "Zcosα − Gsinα ≦ f(Zsinα + Gcosα)、R ≧ V²/(127(i+f))",
        "source": "国土交通省 道路局「道路構造令の各規定の解説」4-1-1(mlit.go.jp/road/sign/pdf/kouzourei_3-4.pdf 77 頁、"
                  "出典表記: 道路構造令の解説と運用 令和3年3月 日本道路協会)。式 (2)(3) を文字で確認"},
    "design_side_friction": {
        "status": "unverified", "value": "設計上の横すべり摩擦係数 f(設計速度ごと)",
        "source": "同上の「図 設計速度と設計上の横すべり摩擦係数」は画像で、文字として読めない = 未確認。"
                  "表の値を式で厳密に再現する門は置かない"},
    "shortt_transition": {
        "status": "primary", "value": "L ≧ (V/3.6)³/(P·R)、P = 0.5〜0.75 m/s³、緩和走行時間 t = 3 秒",
        "source": "同上 4-1-4(80–81 頁)。Shortt 式。表(第18条)の長さは 3 秒の走行長"},
    "linear_bicycle_model": {
        "status": "literature", "value": "線形 2 自由度、K = (m/L)(l_r/C_f − l_f/C_r)",
        "source": "R. Rajamani, Vehicle Dynamics and Control, 2nd ed., Springer 2012, ch. 2–3; "
                  "T. D. Gillespie, Fundamentals of Vehicle Dynamics, SAE 1992, ch. 6(式の形は教科書で一般的。"
                  "この版では数値積分の定常値・固有値の門で検算した)"},
    "pure_pursuit": {
        "status": "literature", "value": "κ = 2 sin α / L_d",
        "source": "R. C. Coulter, Implementation of the Pure Pursuit Path Tracking Algorithm, CMU-RI-TR-92-01 (1992)"},
    "stanley": {
        "status": "literature", "value": "δ = ψ_e + atan(k e/(k_s + v))",
        "source": "S. Thrun et al., Stanley: The robot that won the DARPA Grand Challenge, J. Field Robotics 23(9) "
                  "661–692 (2006); G. M. Hoffmann et al., ACC 2007, 2296–2301"},
    "tlc": {
        "status": "literature", "value": "円の軌跡と境界の交点までの時間",
        "source": "S. Mammar, S. Glaser, M. Netto, Time to line crossing for lane departure avoidance, "
                  "IEEE T-ITS 7(2) 226–241 (2006)"},
    "forward_backward_speed_plan": {
        "status": "literature", "value": "曲率から上限 → 後ろ向き(減速)・前向き(加速)の 2 パス",
        "source": "例: N. R. Kapania, J. Subosits, J. C. Gerdes, J. Dyn. Sys. Meas. Control 138(9) 091005 (2016)。"
                  "刻みの中で摩擦円を守る 2 次方程式はこの版の工夫"},
    "kyosoku_turns": {
        "status": "primary_via_ledger", "value": "左折: あらかじめ左端に寄り側端に沿って徐行 / 右折: 中央に寄り"
                                                 "交差点の中心のすぐ内側を徐行",
        "source": "交通の方法に関する教則 5-7-2(docs/drive/kyosoku_scenarios.json S092/S093、道交法 34 条 1・2 項)"},
    "jokou_10kmh": {
        "status": "assumed", "value": "徐行 = 10 km/h 以下",
        "source": "仮定。法 2 条 1 項 20 号は「直ちに停止することができるような速度」で数値なし"},
    "turn_tolerances": {
        "status": "assumed", "value": "「寄る」= 車体の側面が車道の端(中央線)から 0.5 m 以内(路肩 0.5 m と合わせて道の端まで 1.0 m 以内 = 自転車 1 台の占有幅 1.0 m が残らない)、「側端に沿って」= 後輪の内側が縁石から 1.5 m 以内、"
                                      "「すぐ内側」= 中心から 3.0 m 以内、確かめる区間 = 交差点の手前 30 m",
        "source": "仮定(法・教則に数値なし。30 m は教則の合図の地点を借りた)"},
}

_EPS = 1e-12


# ---- 引数検査(fail-closed) ------------------------------------------------------------------------
def _finite(v, name: str, op: str) -> float:
    try:
        v = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a finite number, got %r" % (op, name, v))
    if not math.isfinite(v):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, v))
    return v


def _positive(v, name: str, op: str) -> float:
    v = _finite(v, name, op)
    if v <= 0.0:
        raise ValueError("%s: %s must be > 0, got %r" % (op, name, v))
    return v


def _nonneg(v, name: str, op: str) -> float:
    v = _finite(v, name, op)
    if v < 0.0:
        raise ValueError("%s: %s must be >= 0, got %r" % (op, name, v))
    return v


def _array(v, name: str, op: str) -> np.ndarray:
    try:
        a = np.asarray(v, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be numeric, got %r" % (op, name, type(v).__name__))
    if not np.all(np.isfinite(a)):
        raise ValueError("%s: %s must be finite" % (op, name))
    return a


def _path(v, name: str, op: str, min_pts: int = 2) -> np.ndarray:
    P = _array(v, name, op)
    if P.ndim != 2 or P.shape[1] != 2 or len(P) < min_pts:
        raise ValueError("%s: %s must be an (N >= %d, 2) array, got shape %r" % (op, name, min_pts, P.shape))
    seg = np.hypot(*np.diff(P, axis=0).T)
    if np.any(seg <= 0.0):
        raise ValueError("%s: %s has repeated consecutive points" % (op, name))
    return P


def _params(p, op: str) -> Dict[str, float]:
    if not isinstance(p, dict):
        raise ValueError("%s: params must be a dict with mass, l_f, l_r, c_f, c_r[, inertia]" % op)
    out = {}
    for k in ("mass", "l_f", "l_r", "c_f", "c_r"):
        if k not in p:
            raise ValueError("%s: params missing %r" % (op, k))
        out[k] = _positive(p[k], k, op)
    out["inertia"] = _positive(p["inertia"], "inertia", op) if "inertia" in p else None
    out["L"] = out["l_f"] + out["l_r"]
    return out


# ---- 1. 摩擦と路面 ------------------------------------------------------------------------------------
def friction_circle_usage(ax, ay, *, mu: float, g: float = G) -> np.ndarray:
    """摩擦円の使用率 √(a_x² + a_y²) / (μ g)(1 を超えたら摩擦円の外 = タイヤが路面から受けられる力を超える)。

    ``ax``, ``ay``: 縦・横の加速度 [m/s²](同じ形、または放送できる形)。``mu``: 路面とタイヤの摩擦係数(> 0)。
    返り値: 使用率の配列(入力と同じ形)。

    **Raises** ``ValueError``: 非有限、μ ≤ 0、g ≤ 0。"""
    op = "friction_circle_usage"
    mu = _positive(mu, "mu", op)
    g = _positive(g, "g", op)
    a = _array(ax, "ax", op)
    b = _array(ay, "ay", op)
    return np.hypot(a, b) / (mu * g)


def curve_speed_limit(radius, *, side_friction: float, superelevation: float = 0.0, g: float = G):
    """片勾配 i・横すべり摩擦係数 f の曲線(半径 R)で外へ滑らない上限速度 v = √(g R (i + f)/(1 − i f)) [m/s]。

    道路構造令の解説 (2) 式 Z cos α − G sin α ≤ f (Z sin α + G cos α)(Z = G v²/(gR)、i = tan α)を v について解いた
    厳密な形。i f ≥ 1 なら(どの速さでも外へは滑らない)``inf``。``radius`` は配列でもよい(> 0)。

    **Raises** ``ValueError``: R ≤ 0、f < 0、|i| ≥ 1、i + f ≤ 0(止まっていても内へ滑る)。"""
    op = "curve_speed_limit"
    R = _array(radius, "radius", op)
    if np.any(R <= 0.0):
        raise ValueError("%s: radius must be > 0" % op)
    f = _nonneg(side_friction, "side_friction", op)
    i = _finite(superelevation, "superelevation", op)
    g = _positive(g, "g", op)
    if abs(i) >= 1.0:
        raise ValueError("%s: |superelevation| must be < 1 (tan of the bank angle), got %r" % (op, i))
    if i + f <= 0.0:
        raise ValueError("%s: superelevation + side_friction must be > 0 (else the car slides inward at rest)" % op)
    den = 1.0 - i * f
    if den <= 0.0:
        out = np.full(R.shape, math.inf)
    else:
        out = np.sqrt(g * R * (i + f) / den)
    return float(out) if out.ndim == 0 else out


def design_min_radius(design_speed_kmh, *, side_friction: float, superelevation: float) -> np.ndarray:
    """道路構造令の解説 (3) 式の最小曲線半径 R = V² / (127 (i + f)) [m](V は km/h)。

    (2) 式から分母の i f を落とし(i f ≪ 1)、3.6² g ≈ 127 とした設計の式。厳密な上限速度は :func:`curve_speed_limit`。

    **Raises** ``ValueError``: V ≤ 0、f < 0、i + f ≤ 0。"""
    op = "design_min_radius"
    V = _array(design_speed_kmh, "design_speed_kmh", op)
    if np.any(V <= 0.0):
        raise ValueError("%s: design speed must be > 0" % op)
    f = _nonneg(side_friction, "side_friction", op)
    i = _finite(superelevation, "superelevation", op)
    if i + f <= 0.0:
        raise ValueError("%s: superelevation + side_friction must be > 0" % op)
    out = V * V / (127.0 * (i + f))
    return float(out) if out.ndim == 0 else out


# ---- 2. 2 輪等価モデル ----------------------------------------------------------------------------------
def understeer_gradient(params: dict) -> Dict[str, float]:
    """アンダーステア勾配 K = (m/L)(l_r/C_f − l_f/C_r) [rad/(m/s²)] と、特性速度 / 臨界速度。

    ``params``: ``mass`` [kg]、``l_f``・``l_r``(重心から前・後車軸)[m]、``c_f``・``c_r``(軸ごとのコーナリングパワー)[N/rad]。
    返り値: ``K``、``kind``("understeer" / "neutral" / "oversteer")、``characteristic_speed``(K > 0 で √(L/K)、
    ヨーレートゲインが最大の速さ)、``critical_speed``(K < 0 で √(−L/K)、これを超えると不安定)。無いものは ``inf``。

    **Raises** ``ValueError``: 欠けた / 正でない母数。"""
    p = _params(params, "understeer_gradient")
    m, lf, lr, cf, cr, L = p["mass"], p["l_f"], p["l_r"], p["c_f"], p["c_r"], p["L"]
    K = (m / L) * (lr / cf - lf / cr)
    scale = (m / L) * (lr / cf + lf / cr)
    if abs(K) <= 1e-12 * scale:
        return {"K": 0.0, "kind": "neutral", "characteristic_speed": math.inf, "critical_speed": math.inf}
    if K > 0:
        return {"K": K, "kind": "understeer", "characteristic_speed": math.sqrt(L / K), "critical_speed": math.inf}
    return {"K": K, "kind": "oversteer", "characteristic_speed": math.inf, "critical_speed": math.sqrt(-L / K)}


def steady_cornering(speed: float, radius: float, params: dict) -> Dict[str, float]:
    """線形 2 輪等価モデルの定常円旋回(速さ u、旋回半径 R = u/r、左旋回を正)。

    R は前向きの速さ u とヨーレート r で定義する(線形モデルの慣習)。重心の軌跡の実際の半径は合成の速さ / r =
    R √(1 + tan²β) で、β が小さい範囲で R に等しい(門で確かめた差は β² の桁)。

    返り値: ``steer`` δ = L/R + K u²/R [rad]、``yaw_rate`` r = u/R、``lateral_accel`` u²/R、
    ``sideslip`` β = l_r/R − m l_f u²/(C_r L R)、``yaw_gain`` r/δ = (u/L)/(1 + K u²/L)、``front_slip``・``rear_slip``
    (軸の横すべり角)、``K``。R < 0 で右旋回(符号がそのまま反転)。

    **Raises** ``ValueError``: u ≤ 0、R = 0 / 非有限、母数の誤り、1 + K u²/L ≤ 0(臨界速度以上)。"""
    op = "steady_cornering"
    p = _params(params, op)
    u = _positive(speed, "speed", op)
    R = _finite(radius, "radius", op)
    if R == 0.0:
        raise ValueError("%s: radius must be non-zero" % op)
    K = understeer_gradient(params)["K"]
    L = p["L"]
    den = 1.0 + K * u * u / L
    if den <= 0.0:
        raise ValueError("%s: speed %.3g m/s is at/above the critical speed (unstable)" % (op, u))
    ay = u * u / R
    fr = p["mass"] * ay * p["l_f"] / L            # 後軸の横力(重心まわりのモーメントの釣り合い)
    ff = p["mass"] * ay * p["l_r"] / L
    return {"steer": L / R + K * ay, "yaw_rate": u / R, "lateral_accel": ay,
            "sideslip": p["l_r"] / R - p["mass"] * p["l_f"] * u * u / (p["c_r"] * L * R),
            "yaw_gain": (u / L) / den, "front_slip": ff / p["c_f"], "rear_slip": fr / p["c_r"], "K": K}


def _bicycle_rhs(X, steer, u, p):
    x, y, psi, vy, r = (X[..., k] for k in range(5))
    af = steer - (vy + p["l_f"] * r) / u
    ar = -(vy - p["l_r"] * r) / u
    Ff = p["c_f"] * af
    Fr = p["c_r"] * ar
    c, s = np.cos(psi), np.sin(psi)
    return np.stack([u * c - vy * s, u * s + vy * c, r,
                     (Ff + Fr) / p["mass"] - u * r,
                     (p["l_f"] * Ff - p["l_r"] * Fr) / p["inertia"]], axis=-1)


def bicycle_model_step(state, steer, speed, params: dict, dt: float) -> np.ndarray:
    """線形 2 輪等価モデルの 1 刻み(古典的な 4 次 Runge–Kutta、刻みの間 δ と u は一定)。

    ``state``: (..., 5) = (x, y, ψ, v_y, r)(重心の位置 [m]、向き [rad]、車の座標の横速度 [m/s]、ヨーレート [rad/s])。
    ``steer``: 前輪の舵角 δ [rad](state の先頭の形に放送)。``speed``: 前向きの速さ u [m/s](> 0、放送)。
    ``params`` には ``inertia``(I_z [kg m²])も要る。返り値: 次の状態(同じ形)。

    横力は線形(飽和しない)。u → 0 で式が特異になるので u ≥ 0.5 m/s を要求する(低速は運動学で扱う)。

    **Raises** ``ValueError``: 形の誤り、非有限、u < 0.5、dt ≤ 0、I_z が無い。"""
    op = "bicycle_model_step"
    p = _params(params, op)
    if p["inertia"] is None:
        raise ValueError("%s: params must include inertia" % op)
    X = _array(state, "state", op)
    if X.shape[-1:] != (5,):
        raise ValueError("%s: state must have last dimension 5, got %r" % (op, X.shape))
    d = _array(steer, "steer", op)
    u = _array(speed, "speed", op)
    if np.any(u < 0.5):
        raise ValueError("%s: speed must be >= 0.5 m/s (the linear model is singular at u -> 0)" % op)
    dt = _positive(dt, "dt", op)
    k1 = _bicycle_rhs(X, d, u, p)
    k2 = _bicycle_rhs(X + 0.5 * dt * k1, d, u, p)
    k3 = _bicycle_rhs(X + 0.5 * dt * k2, d, u, p)
    k4 = _bicycle_rhs(X + dt * k3, d, u, p)
    return X + dt / 6.0 * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


# ---- 3. 低速の幾何 --------------------------------------------------------------------------------------
def ackermann_steer_angles(radius, wheelbase: float, track: float) -> Dict[str, np.ndarray]:
    """アッカーマンの内外輪の舵角(後車軸の中心の旋回半径 R、ホイールベース L、輪距 t)。

    δ_in = atan(L/(R − t/2))、δ_out = atan(L/(R + t/2))、2 輪等価 δ = atan(L/R)。cot δ_out − cot δ_in = t/L。
    返り値: ``inner``, ``outer``, ``bicycle`` [rad]、``front_inner_radius`` √((R − t/2)² + L²)、``front_outer_radius``、
    ``rear_inner_radius`` R − t/2、``offtracking``(定常の内輪差 = 前内輪 − 後内輪の半径)。

    **Raises** ``ValueError``: R ≤ t/2(内側の後輪が旋回の中心を越える)、L ≤ 0、t < 0。"""
    op = "ackermann_steer_angles"
    R = _array(radius, "radius", op)
    L = _positive(wheelbase, "wheelbase", op)
    t = _nonneg(track, "track", op)
    if np.any(R <= 0.5 * t):
        raise ValueError("%s: radius must be > track/2" % op)
    ri, ro = R - 0.5 * t, R + 0.5 * t
    fi = np.hypot(ri, L)
    return {"inner": np.arctan2(L, ri), "outer": np.arctan2(L, ro), "bicycle": np.arctan2(L, R),
            "front_inner_radius": fi, "front_outer_radius": np.hypot(ro, L), "rear_inner_radius": ri,
            "offtracking": fi - ri}


def offtracking_circle(front_radius: float, wheelbase: float, arc_length, *, track: float = 0.0,
                       gamma0: float = 0.0) -> Dict[str, np.ndarray]:
    """内輪差の過渡(閉形式): 前車軸の中心が半径 R の円に入ってから弧長 s 進んだときの車の姿勢と内側の車輪の半径。

    後車軸の中心は前車軸の中心を長さ L の棒で引く(すべりなし)。棒と前の速度のなす角 γ は dγ/ds = 1/R − sin γ / L。
    a = 1/R、b = 1/L、k = √(b² − a²)、t± = (b ± k)/a(t− = tan(γ*/2)、sin γ* = L/R)とすると
    Q = ((t+ − t₀)/(t− − t₀)) e^{k s}、tan(γ/2) = (Q t− − t+)/(Q − 1)。

    ``arc_length``: s ≥ 0(配列可)。``track``: 輪距 t(内側の車輪の位置に使う)。``gamma0``: 円に入るときの γ(0 = 直線から
    まっすぐ入る、0 ≤ γ₀ < γ*)。返り値(s と同じ形): ``gamma``、``rear_radius``(後車軸の中心の半径
    √(R² + L² − 2RL sin γ))、``front_inner_wheel_radius``・``rear_inner_wheel_radius``(内側の車輪の旋回中心からの距離)、
    ``offtracking``(前内輪 − 後内輪)、``steady``(s → ∞ の値の dict)。

    **Raises** ``ValueError``: R ≤ L(定常が無い)、s < 0、γ₀ が範囲外、t/2 ≥ 後輪の半径。"""
    op = "offtracking_circle"
    R = _positive(front_radius, "front_radius", op)
    L = _positive(wheelbase, "wheelbase", op)
    t = _nonneg(track, "track", op)
    s = _array(arc_length, "arc_length", op)
    if np.any(s < 0):
        raise ValueError("%s: arc_length must be >= 0" % op)
    if R <= L:
        raise ValueError("%s: front_radius must be > wheelbase (no steady state otherwise)" % op)
    g_star = math.asin(L / R)
    g0 = _nonneg(gamma0, "gamma0", op)
    if g0 >= g_star:
        raise ValueError("%s: gamma0 must be < asin(L/R) = %.6g" % (op, g_star))
    a, b = 1.0 / R, 1.0 / L
    k = math.sqrt(b * b - a * a)
    tp, tm = (b + k) / a, (b - k) / a
    t0 = math.tan(0.5 * g0)
    lnq0 = math.log((tp - t0) / (tm - t0))
    lnQ = lnq0 + k * s
    # tan(γ/2) = (Q t− − t+)/(Q − 1) = t− − (t+ − t−)/(Q − 1)、Q が大きいときの桁落ちを避ける
    with np.errstate(over="ignore"):
        tq = tm - (tp - tm) / np.expm1(lnQ)
    gamma = 2.0 * np.arctan(tq)
    rr = np.sqrt(R * R + L * L - 2.0 * R * L * np.sin(gamma))
    # 内側の車輪(左旋回の左の車輪): 旋回の中心を原点、前車軸の中心 F = (R, 0)、接線 T = (0, 1)、内向き N = (−1, 0)
    # 棒 u = cos γ T − sin γ N = (sin γ, cos γ)、後 = F − L u、車の左 n_l = (−u_y, u_x) = (−cos γ, sin γ)
    ux, uy = np.sin(gamma), np.cos(gamma)
    nlx, nly = -uy, ux
    fx, fy = R + 0.5 * t * nlx, 0.5 * t * nly
    bx, by = R - L * ux + 0.5 * t * nlx, -L * uy + 0.5 * t * nly
    fi = np.hypot(fx, fy)
    ri = np.hypot(bx, by)
    rs = math.sqrt(R * R - L * L)
    if 0.5 * t >= rs:
        raise ValueError("%s: track/2 must be < the steady rear-axle radius %.6g" % (op, rs))
    fis = math.hypot(R - 0.5 * t * math.cos(g_star), 0.5 * t * math.sin(g_star))
    steady = {"gamma": g_star, "rear_radius": rs, "rear_inner_wheel_radius": rs - 0.5 * t,
              "front_inner_wheel_radius": fis, "offtracking": fis - (rs - 0.5 * t)}
    sh = lambda v: float(v) if np.ndim(v) == 0 else v  # noqa: E731
    return {"gamma": sh(gamma), "rear_radius": sh(rr), "front_inner_wheel_radius": sh(fi),
            "rear_inner_wheel_radius": sh(ri), "offtracking": sh(fi - ri), "steady": steady}


def rear_axle_path(front_path, wheelbase: float, *, rear0=None) -> Dict[str, np.ndarray]:
    """前車軸の中心の折線の軌跡から、すべりなしで引かれる後車軸の中心の軌跡(区間ごとに厳密な追跡曲線)。

    前が直線を Δ 進む間、棒(後 → 前)と直線のなす角 θ は tan(θ/2) = tan(θ₀/2) e^{−Δ/L}(厳密)。折線の頂点ごとに
    これを繋ぐ。``rear0``: 後車軸の初めの位置(None なら最初の区間の向きに L だけ後ろ = 真っすぐ)。|前 − 後| = L を要求。
    返り値: ``rear`` (N, 2)、``heading`` (N,)(車体の向き = 棒の向き)、``gamma`` (N,)(棒と前の進む向きのなす角、
    左旋回で正)。

    **Raises** ``ValueError``: 形の誤り、重複点、L ≤ 0、|前 − 後| ≠ L、θ₀ = π(後ろ向きに押す)。"""
    op = "rear_axle_path"
    F = _path(front_path, "front_path", op)
    L = _positive(wheelbase, "wheelbase", op)
    d = np.diff(F, axis=0)
    seg = np.hypot(d[:, 0], d[:, 1])
    if rear0 is None:
        Rr = F[0] - L * d[0] / seg[0]
    else:
        Rr = _array(rear0, "rear0", op).reshape(2)
        if abs(math.hypot(*(F[0] - Rr)) - L) > 1e-6 * L:
            raise ValueError("%s: |front_path[0] - rear0| must equal wheelbase" % op)
    n = len(F)
    rear = np.empty((n, 2))
    head = np.empty(n)
    gam = np.empty(n)
    rear[0] = Rr
    bar = F[0] - Rr
    head[0] = math.atan2(bar[1], bar[0])
    for k in range(n - 1):
        dirk = math.atan2(d[k, 1], d[k, 0])
        th0 = math.atan2(math.sin(head[k] - dirk), math.cos(head[k] - dirk))
        if abs(abs(th0) - math.pi) < 1e-12:
            raise ValueError("%s: the front moves straight backwards along the bar at vertex %d" % (op, k))
        gam[k] = -th0
        th = 2.0 * math.atan(math.tan(0.5 * th0) * math.exp(-seg[k] / L))
        hk = dirk + th
        head[k + 1] = hk
        rear[k + 1] = F[k + 1] - L * np.array([math.cos(hk), math.sin(hk)])
    gam[-1] = gam[-2] if n > 1 else 0.0
    return {"rear": rear, "heading": head, "gamma": gam}


# ---- 4. 緩和曲線 ------------------------------------------------------------------------------------------
def _fresnel_series(x):
    z = 0.5 * math.pi * x * x
    C = np.zeros_like(x)
    S = np.zeros_like(x)
    tc = x.copy()                                  # n = 0 の項 x
    ts = x * z / 3.0                               # x^3 (π/2) / 3
    C += tc
    S += ts
    # C の項 a_n = (−1)^n z^{2n} x / ((2n)! (4n+1))、S の項 b_n = (−1)^n z^{2n+1} x / ((2n+1)! (4n+3))
    pc = x.copy()                                  # (−1)^n z^{2n} / (2n)! · x
    ps = x * z                                     # (−1)^n z^{2n+1} / (2n+1)! · x
    for n in range(1, 60):
        pc = -pc * z * z / ((2 * n - 1) * (2 * n))
        ps = -ps * z * z / ((2 * n) * (2 * n + 1))
        C += pc / (4 * n + 1)
        S += ps / (4 * n + 3)
    return C, S


def _fresnel_asym(x):
    w = math.pi * x * x
    f = np.zeros_like(x)
    gg = np.zeros_like(x)
    tf = np.ones_like(x)
    tg = np.ones_like(x)
    f += tf
    gg += tg
    for n in range(1, 12):
        tf = -tf * (4 * n - 3) * (4 * n - 1) / (w * w)
        tg = -tg * (4 * n - 1) * (4 * n + 1) / (w * w)
        f += tf
        gg += tg
    f /= math.pi * x
    gg /= math.pi * w * x
    ph = 0.5 * w
    C = 0.5 + f * np.sin(ph) - gg * np.cos(ph)
    S = 0.5 - f * np.cos(ph) - gg * np.sin(ph)
    return C, S


def fresnel_integrals(x):
    """フレネル積分 C(x) = ∫₀ˣ cos(π t²/2) dt、S(x) = ∫₀ˣ sin(π t²/2) dt(奇関数)。

    |x| ≤ 3.5 はべき級数、それより大きいと漸近展開(補助関数 f, g)。誤差は 1e-8 以下(門: 数値積分)。
    返り値: (C, S)(x と同じ形)。

    **Raises** ``ValueError``: 非有限。"""
    op = "fresnel_integrals"
    X = _array(x, "x", op)
    xs = np.atleast_1d(np.abs(X)).astype(np.float64)
    C = np.zeros_like(xs)
    S = np.zeros_like(xs)
    lo = xs <= 3.5
    if lo.any():
        C[lo], S[lo] = _fresnel_series(xs[lo])
    if (~lo).any():
        C[~lo], S[~lo] = _fresnel_asym(xs[~lo])
    sg = np.sign(np.atleast_1d(X))
    C, S = C * sg, S * sg
    if X.ndim == 0:
        return float(C[0]), float(S[0])
    return C.reshape(X.shape), S.reshape(X.shape)


def _std_clothoid(A, u):
    """標準のクロソイド(原点で曲率 0・向き 0、左へ曲がる)の弧長 u(負も可)での点・向き。"""
    sc = A * math.sqrt(math.pi)
    C, S = fresnel_integrals(u / sc)
    return np.stack([sc * np.asarray(C), sc * np.asarray(S)], -1), u * u / (2.0 * A * A)


def clothoid_points(length: float, s, *, kappa0: float = 0.0, kappa1: float = 0.0, start=(0.0, 0.0),
                    heading0: float = 0.0) -> Dict[str, np.ndarray]:
    """曲率が弧長に一次 κ(s) = κ₀ + (κ₁ − κ₀) s / length の曲線(クロソイドの一部。κ₀ = κ₁ なら円弧・直線)の点。

    ``s``: 0 ≤ s ≤ length の弧長(配列)。``start``・``heading0``: 始点と始点の向き。左へ曲がる曲率を正。
    クロソイドの部分は標準形(A² = 1/|dκ/ds|)をフレネル積分で写し、始点・向きに合わせて回す(数値積分を使わない)。
    返り値: ``points`` (N, 2)、``heading`` (N,)、``curvature`` (N,)、``A``(クロソイドのパラメータ、円弧・直線は inf)。

    **Raises** ``ValueError``: length ≤ 0、s が範囲外、非有限。"""
    op = "clothoid_points"
    Ls = _positive(length, "length", op)
    k0 = _finite(kappa0, "kappa0", op)
    k1 = _finite(kappa1, "kappa1", op)
    s = np.atleast_1d(_array(s, "s", op)).astype(np.float64)
    if np.any(s < -1e-12) or np.any(s > Ls * (1 + 1e-12)):
        raise ValueError("%s: s must lie in [0, length]" % op)
    p0 = _array(start, "start", op).reshape(2)
    h0 = _finite(heading0, "heading0", op)
    c = (k1 - k0) / Ls
    kap = k0 + c * s
    if abs(c) < 1e-15:
        h = h0 + k0 * s
        if abs(k0) < 1e-15:
            P = p0 + np.stack([s * math.cos(h0), s * math.sin(h0)], -1)
        else:
            P = p0 + np.stack([(np.sin(h) - math.sin(h0)) / k0, (math.cos(h0) - np.cos(h)) / k0], -1)
        return {"points": P, "heading": h, "curvature": kap, "A": math.inf}
    sgn = 1.0 if c > 0 else -1.0
    A = 1.0 / math.sqrt(abs(c))
    u0 = sgn * k0 / abs(c)                         # 標準形の上の始点の弧長(鏡に映した曲率で)
    Q, th = _std_clothoid(A, u0 + s)
    Q0, th0 = _std_clothoid(A, np.array([u0]))
    D = Q - Q0[0]
    D[:, 1] *= sgn                                 # 右へ曲がる版は y を反転
    th = sgn * (th - th0[0])
    rot = h0 - 0.0
    cr, sr = math.cos(rot), math.sin(rot)
    # 標準形の始点での向き θ(u0) を打ち消してから heading0 へ
    a0 = sgn * float(th0[0])
    ca, sa = math.cos(-a0), math.sin(-a0)
    D = np.stack([ca * D[:, 0] - sa * D[:, 1], sa * D[:, 0] + ca * D[:, 1]], -1)
    P = p0 + np.stack([cr * D[:, 0] - sr * D[:, 1], sr * D[:, 0] + cr * D[:, 1]], -1)
    return {"points": P, "heading": h0 + th, "curvature": kap, "A": A}


def clothoid_design(radius: float, length: float, speed: Optional[float] = None) -> Dict[str, float]:
    """直線 → 円(半径 R)を長さ L のクロソイドで繋ぐときの量。

    返り値: ``A`` = √(R L)、``end_angle`` τ = L/(2R)、``end_point``(終点の (x, y)、フレネル積分)、``shift``
    ΔR = y_end − R(1 − cos τ)(円が直線から離れる量。近似 L²/(24R))、``lateral_jerk``(速さ v を与えたとき
    v³/(R L) [m/s³] = Shortt 式の P)、``min_length_3s``(v を与えたとき 3 秒の走行長 3v [m])。

    **Raises** ``ValueError``: R ≤ 0、L ≤ 0、v ≤ 0。"""
    op = "clothoid_design"
    R = _positive(radius, "radius", op)
    L = _positive(length, "length", op)
    cp = clothoid_points(L, [L], kappa0=0.0, kappa1=1.0 / R)
    tau = L / (2.0 * R)
    xe, ye = cp["points"][0]
    out = {"A": math.sqrt(R * L), "end_angle": tau, "end_point": (float(xe), float(ye)),
           "shift": float(ye - R * (1.0 - math.cos(tau))), "shift_approx": L * L / (24.0 * R)}
    if speed is not None:
        v = _positive(speed, "speed", op)
        out["lateral_jerk"] = v ** 3 / (R * L)
        out["min_length_3s"] = 3.0 * v
    return out


# ---- 5. 位置保持の制御則 -----------------------------------------------------------------------------------
def _nearest_on_path(P, cum, pts, start, window):
    """点ごとに折線の最も近い点(区間への射影)。start/window で探す範囲を絞る(None なら全体)。"""
    n = len(pts)
    M = len(P)
    if start is None:
        lo = np.zeros(n, int)
        hi = np.full(n, M - 1)
    else:
        lo = np.clip(start - window, 0, M - 2)
        hi = np.clip(start + window, 1, M - 1)
    K = int(np.max(hi - lo))
    idx = lo[:, None] + np.arange(K)[None, :]
    idx = np.minimum(idx, M - 2)
    A = P[idx]
    B = P[idx + 1]
    AB = B - A
    l2 = np.sum(AB * AB, -1)
    tt = np.clip(np.sum((pts[:, None, :] - A) * AB, -1) / l2, 0.0, 1.0)
    Q = A + tt[..., None] * AB
    d2 = np.sum((pts[:, None, :] - Q) ** 2, -1)
    j = np.argmin(d2, 1)
    r = np.arange(n)
    seg = idx[r, j]
    q = Q[r, j]
    ab = AB[r, j]
    cross = ab[:, 0] * (pts[:, 1] - q[:, 1]) - ab[:, 1] * (pts[:, 0] - q[:, 0])
    dist = np.sqrt(d2[r, j])
    lateral = np.where(cross >= 0, dist, -dist)
    s = cum[seg] + tt[r, j] * np.sqrt(l2[r, j])
    return seg, s, lateral, np.arctan2(ab[:, 1], ab[:, 0])


def _poses(pose, op):
    X = _array(pose, "pose", op)
    single = X.ndim == 1
    X = np.atleast_2d(X)
    if X.shape[1] != 3:
        raise ValueError("%s: pose must be (3,) or (N, 3) = (x, y, heading)" % op)
    return X, single


def _start(start_index, n, M, op):
    if start_index is None:
        return None
    si = np.broadcast_to(np.asarray(start_index), (n,)).astype(np.int64)
    if np.any(si < 0) or np.any(si >= M):
        raise ValueError("%s: start_index out of range" % op)
    return si


def pure_pursuit_curvature(pose, path, lookahead, *, start_index=None, window: int = 40) -> Dict[str, np.ndarray]:
    """pure pursuit: 後車軸の中心(``pose`` = (x, y, ψ)、(N, 3) 可)から経路の上で距離 L_d 先の点を狙う曲率 κ = 2 sin α / L_d。

    経路は折線(M, 2)。最も近い点を探し、そこから先で初めて距離が L_d になる点を区間の上で 2 次方程式で求める
    (経路の終わりまで届かなければ終点を狙い、L_d をその距離にする)。``start_index`` と ``window`` で最も近い点を
    探す範囲を絞る(長い経路の繰り返しを速くする。None なら全体)。
    返り値: ``kappa``, ``alpha``, ``goal`` (N, 2), ``index``(最も近い区間), ``lateral``(経路からの横ずれ、左が正),
    ``lookahead``(実際の距離)。1 つの pose なら先頭の次元を落とす。

    **Raises** ``ValueError``: 形の誤り、L_d ≤ 0、start_index が範囲外。"""
    op = "pure_pursuit_curvature"
    X, single = _poses(pose, op)
    P = _path(path, "path", op)
    Ld = np.broadcast_to(_array(lookahead, "lookahead", op), (len(X),)).astype(np.float64)
    if np.any(Ld <= 0):
        raise ValueError("%s: lookahead must be > 0" % op)
    M = len(P)
    cum = np.r_[0.0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    si = _start(start_index, len(X), M, op)
    seg, s, lat, _ = _nearest_on_path(P, cum, X[:, :2], si, int(window))
    # 注視点: 最も近い区間の始点から先の頂点で、初めて距離 ≥ L_d になる頂点 k+1 を探し、区間 [k, k+1] の上で
    # |a + τ(b − a) − p| = L_d を 2 次方程式で解く(点ごとに前向きの窓 nf 頂点、全部の点を一度に)
    segl = np.hypot(*np.diff(P, axis=0).T)
    nf = int(math.ceil(1.5 * float(Ld.max()) / float(segl.min()))) + 4
    jj = seg[:, None] + 1 + np.arange(nf)[None, :]
    over = jj > M - 1
    jc = np.minimum(jj, M - 1)
    dist = np.hypot(P[jc, 0] - X[:, :1], P[jc, 1] - X[:, 1:2])
    hit = (dist >= Ld[:, None]) & ~over
    found = hit.any(1)
    first = np.argmax(hit, 1)
    kb = jc[np.arange(len(X)), first]
    ka = np.maximum(kb - 1, 0)
    A0 = P[ka]
    dd = P[kb] - A0
    f = A0 - X[:, :2]
    qa = np.sum(dd * dd, 1)
    qb = 2.0 * np.sum(f * dd, 1)
    qc = np.sum(f * f, 1) - Ld ** 2
    disc = np.maximum(qb * qb - 4.0 * qa * qc, 0.0)
    tt = np.clip((-qb + np.sqrt(disc)) / (2.0 * qa), 0.0, 1.0)
    goal = A0 + tt[:, None] * dd
    Lr = Ld.copy()
    for i in np.nonzero(~found)[0]:              # 窓で見つからない点だけ、終点まで 1 頂点ずつ調べる(正しさの保険)
        p = X[i, :2]
        dk = np.hypot(P[seg[i] + 1:, 0] - p[0], P[seg[i] + 1:, 1] - p[1])
        h = np.nonzero(dk >= Ld[i])[0]
        if len(h) == 0:                          # 経路の終わりまで届かない: 終点を狙う
            goal[i] = P[-1]
            Lr[i] = max(float(np.hypot(*(P[-1] - p))), 1e-9)
            continue
        kb1 = seg[i] + 1 + int(h[0])
        a0, d1 = P[kb1 - 1], P[kb1] - P[kb1 - 1]
        f1 = a0 - p
        qa1, qb1, qc1 = d1 @ d1, 2.0 * (f1 @ d1), f1 @ f1 - Ld[i] ** 2
        t1 = (-qb1 + math.sqrt(max(qb1 * qb1 - 4 * qa1 * qc1, 0.0))) / (2 * qa1)
        goal[i] = a0 + min(max(t1, 0.0), 1.0) * d1
    dx = goal[:, 0] - X[:, 0]
    dy = goal[:, 1] - X[:, 1]
    c, sn = np.cos(X[:, 2]), np.sin(X[:, 2])
    xl = c * dx + sn * dy
    yl = -sn * dx + c * dy
    alpha = np.arctan2(yl, xl)
    kappa = 2.0 * np.sin(alpha) / Lr
    out = {"kappa": kappa, "alpha": alpha, "goal": goal, "index": seg, "lateral": lat, "lookahead": Lr}
    if single:
        out = {k: (v[0] if np.ndim(v) else v) for k, v in out.items()}
    return out


def pure_pursuit_circle_offset(radius: float, lookahead: float, wheelbase: float, *, understeer: float = 0.0,
                               speed: float = 0.0, params: Optional[dict] = None) -> Dict[str, float]:
    """定常円(半径 R)を pure pursuit(後車軸の中心を基準)で追うときの定常の円の半径 ρ と横ずれ ρ − R(外へ正)。

    **運動学 + アンダーステア**(``params`` = None): 指令の舵角 δ = L κ_cmd に対し実際の曲率が κ_cmd / (1 + K v²/L)
    になるとすると、同心円の定常で ρ = √(R² + (K v²/L) L_d²)(この版で導いた閉形式)。K = 0 なら ρ = R(横ずれ 0)。

    **線形 2 輪等価モデル**(``params`` を与える。δ = atan(L κ_cmd)): 定常では車体の向きが後車軸の速度(円の接線)より
    後軸の横すべり角 α_r = m l_f a_y / (C_r L) だけ内を向くので、注視点の見える角が α_r 減る。定常の関係
    (δ = L/R_c + K u²/R_c、β、回転の中心)を重心の旋回半径 R_c の 1 変数の方程式にして二分法で解く(半閉形式)。
    運動学の式はこの効果を落とすので横ずれを小さく見積もる(PoC では約半分)。

    **Raises** ``ValueError``: R, L_d, L ≤ 0、注視点が円に届かない、1 + K v²/L ≤ 0、params で v ≤ 0.5。"""
    op = "pure_pursuit_circle_offset"
    R = _positive(radius, "radius", op)
    Ld = _positive(lookahead, "lookahead", op)
    L = _positive(wheelbase, "wheelbase", op)
    K = _finite(understeer, "understeer", op)
    v = _nonneg(speed, "speed", op)
    if params is not None:
        p = _params(params, op)
        if abs(p["L"] - L) > 1e-9 * L:
            raise ValueError("%s: wheelbase must equal params l_f + l_r" % op)
        if v < 0.5:
            raise ValueError("%s: speed must be >= 0.5 m/s with params" % op)
        Kp = understeer_gradient(params)["K"]
        if 1.0 + Kp * v * v / L <= 0.0:
            raise ValueError("%s: speed is above the critical speed" % op)

        def geo(Rc):
            beta = p["l_r"] / Rc - p["mass"] * p["l_f"] * v * v / (p["c_r"] * L * Rc)
            r = v / Rc
            vy = beta * v
            rho = math.hypot(-p["l_r"] + beta * Rc, Rc)
            phi = math.atan2(vy - r * p["l_r"], v)
            return rho, phi

        def resid(Rc):
            rho, phi = geo(Rc)
            sa = (rho * rho - R * R + Ld * Ld) / (2.0 * rho * Ld)
            if abs(sa) >= 1.0:
                return math.nan
            al = math.asin(sa) + phi
            return math.atan(L * 2.0 * math.sin(al) / Ld) - (L + Kp * v * v) / Rc

        grid = np.geomspace(0.5 * R, 4.0 * R, 400)
        vals = np.array([resid(g) for g in grid])
        ok = np.isfinite(vals[:-1]) & np.isfinite(vals[1:]) & (np.sign(vals[:-1]) != np.sign(vals[1:]))
        if not ok.any():
            raise ValueError("%s: no steady circle found (lookahead cannot reach the path)" % op)
        j = int(np.nonzero(ok)[0][np.argmin(np.abs(grid[:-1][ok] - R))])
        lo, hi = grid[j], grid[j + 1]
        flo = vals[j]
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            fm = resid(mid)
            if np.sign(fm) == np.sign(flo):
                lo, flo = mid, fm
            else:
                hi = mid
        Rc = 0.5 * (lo + hi)
        rho, phi = geo(Rc)
        return {"rho": rho, "offset": rho - R, "cg_radius": Rc, "rear_slip": -phi,
                "alpha": math.asin((rho * rho - R * R + Ld * Ld) / (2.0 * rho * Ld)) + phi}
    c = K * v * v / L
    if 1.0 + c <= 0.0:
        raise ValueError("%s: 1 + K v^2 / L must be > 0" % op)
    rho2 = R * R + c * Ld * Ld
    if rho2 <= 0:
        raise ValueError("%s: no steady circle (oversteer too strong)" % op)
    rho = math.sqrt(rho2)
    if Ld >= R + rho or Ld <= abs(R - rho):
        raise ValueError("%s: lookahead %.3g m cannot reach the path circle" % (op, Ld))
    return {"rho": rho, "offset": rho - R, "alpha": math.asin((rho * rho - R * R + Ld * Ld) / (2.0 * rho * Ld))}


def stanley_steer(front_pose, path, *, gain: float, speed, softening: float = 0.0, max_steer: float = math.inf,
                  start_index=None, window: int = 40) -> Dict[str, np.ndarray]:
    """Stanley の舵角 δ = ψ_e + atan2(−k e, k_s + v)(前車軸の中心の横ずれ e は経路の左が正、ψ_e = 経路の向き − ψ)。

    ``front_pose``: (3,) または (N, 3)。``max_steer`` で切る(切ると :func:`stanley_straight_decay` の閉形式から外れる)。
    返り値: ``steer``, ``lateral``, ``heading_error``, ``index``。

    **Raises** ``ValueError``: 形の誤り、k ≤ 0、v < 0、k_s < 0、max_steer ≤ 0。"""
    op = "stanley_steer"
    X, single = _poses(front_pose, op)
    P = _path(path, "path", op)
    k = _positive(gain, "gain", op)
    v = np.broadcast_to(_array(speed, "speed", op), (len(X),))
    if np.any(v < 0):
        raise ValueError("%s: speed must be >= 0" % op)
    ks = _nonneg(softening, "softening", op)
    mx = _positive(max_steer, "max_steer", op) if math.isfinite(float(max_steer)) else math.inf
    cum = np.r_[0.0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    si = _start(start_index, len(X), len(P), op)
    seg, s, lat, hp = _nearest_on_path(P, cum, X[:, :2], si, int(window))
    he = np.arctan2(np.sin(hp - X[:, 2]), np.cos(hp - X[:, 2]))
    den = ks + v
    if np.any(den <= 0):
        raise ValueError("%s: softening + speed must be > 0" % op)
    d = he + np.arctan2(-k * lat, den)
    d = np.clip(d, -mx, mx)
    out = {"steer": d, "lateral": lat, "heading_error": he, "index": seg}
    if single:
        out = {kk: (vv[0] if np.ndim(vv) else vv) for kk, vv in out.items()}
    return out


def _stanley_F(e, a, k):
    q = np.sqrt(a * a + (k * e) ** 2)
    return q - a * np.log((a + q) / (k * e))


def stanley_straight_decay(e0: float, t, *, gain: float, speed: float, softening: float = 0.0) -> np.ndarray:
    """直線の経路で Stanley(切らない)の前車軸の横ずれ e(t) の閉形式。

    ė = −v k e / √(a² + k² e²)、a = k_s + v。F(e) = √(a² + k²e²) − a ln((a + √(a² + k²e²))/(k|e|)) は
    dF/dt = −v k(一定)。F(e(t)) = F(e₀) − v k t を |e| ∈ (0, |e₀|] の二分法(F は |e| に単調増加)で解く。
    小さい e では e ≈ e₀' e^{−k t v/a}(指数)、大きい e では |e| がほぼ v t で減る(直線)。

    **Raises** ``ValueError``: k ≤ 0、v ≤ 0、k_s < 0、t < 0。"""
    op = "stanley_straight_decay"
    e0 = _finite(e0, "e0", op)
    k = _positive(gain, "gain", op)
    v = _positive(speed, "speed", op)
    ks = _nonneg(softening, "softening", op)
    T = _array(t, "t", op)
    if np.any(T < 0):
        raise ValueError("%s: t must be >= 0" % op)
    a = ks + v
    if e0 == 0.0:
        return np.zeros_like(T) if T.ndim else 0.0
    E0 = abs(e0)
    target = _stanley_F(E0, a, k) - v * k * np.atleast_1d(T)
    lo = np.zeros_like(target)
    hi = np.full_like(target, E0)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        mid_safe = np.maximum(mid, 1e-300)
        fm = _stanley_F(mid_safe, a, k)
        up = fm > target
        hi = np.where(up, mid, hi)
        lo = np.where(up, lo, mid)
    out = math.copysign(1.0, e0) * 0.5 * (lo + hi)
    return float(out[0]) if T.ndim == 0 else out.reshape(T.shape)


# ---- 6. 速度計画と車線 ----------------------------------------------------------------------------------
def _decel_step(v2_next, ds, km, amax, G_tot):
    """刻み ds で v² を一次に戻すとき、刻みの中で摩擦円(半径 G_tot)と縦の上限 amax を守る最大の v²(手前の点)。"""
    w1 = v2_next + 2.0 * ds * amax
    if G_tot is None or km * w1 <= 0.0 or (G_tot * G_tot - (w1 * km) ** 2) >= amax * amax:
        return w1
    # (w − v²)² = 4 ds² (G² − w² κ²) の大きい根
    A = 1.0 + 4.0 * ds * ds * km * km
    Bq = v2_next
    Cq = v2_next * v2_next - 4.0 * ds * ds * G_tot * G_tot
    disc = Bq * Bq - A * Cq
    if disc < 0:
        return v2_next
    w = (Bq + math.sqrt(disc)) / A
    return max(min(w, w1), v2_next)


def curvature_speed_plan(s, kappa, *, v_max, a_lat_max: float, a_accel: float, a_decel: float,
                         a_total: Optional[float] = None, v_start: Optional[float] = None,
                         v_end: Optional[float] = None) -> Dict[str, np.ndarray]:
    """曲率の列から速度の上限を作り、前向き・後ろ向きの 2 パスで加減速の上限を守る速度計画(古典的な手法)。

    ``s``: 弧長(増加、(N,))。``kappa``: 各点の曲率(符号は問わない)。``v_max``: 速度の上限(スカラーまたは (N,)、
    法定速度・徐行の区間など)。上限 v_lim = min(v_max, √(a_lat_max/|κ|))。刻みの間は v² を s に一次(一定の加減速)。
    ``a_total``(摩擦円の半径、例 μg)を与えると、縦の加減速を √(a_total² − (v²κ_m)²) でも抑える(κ_m = 刻みの両端の |κ|
    の大きい方、2 次方程式で解くので刻みの中の **どこでも** √(a_x² + a_y²) ≤ a_total)。a_lat_max ≤ a_total を要求。
    返り値: ``v``, ``v_limit``, ``ax``(刻みごとの縦の加速度、(N−1,))、``ay_max``(刻みの中の横の加速度の最大)、
    ``time``(到着時刻、v² 一次の厳密な時間)。

    **Raises** ``ValueError``: 形の誤り、s が増加でない、上限が正でない、a_lat_max > a_total、v_start/v_end が上限超え。"""
    op = "curvature_speed_plan"
    s = _array(s, "s", op)
    k = np.abs(_array(kappa, "kappa", op))
    if s.ndim != 1 or k.shape != s.shape or len(s) < 2:
        raise ValueError("%s: s and kappa must be 1-D of the same length >= 2" % op)
    ds = np.diff(s)
    if np.any(ds <= 0):
        raise ValueError("%s: s must be strictly increasing" % op)
    vm = np.broadcast_to(_array(v_max, "v_max", op), s.shape).astype(np.float64)
    if np.any(vm <= 0):
        raise ValueError("%s: v_max must be > 0" % op)
    alat = _positive(a_lat_max, "a_lat_max", op)
    aacc = _positive(a_accel, "a_accel", op)
    adec = _positive(a_decel, "a_decel", op)
    Gt = None
    if a_total is not None:
        Gt = _positive(a_total, "a_total", op)
        if alat > Gt:
            raise ValueError("%s: a_lat_max must be <= a_total" % op)
    with np.errstate(divide="ignore"):
        vlim = np.minimum(vm, np.where(k > 0, np.sqrt(alat / np.maximum(k, 1e-300)), np.inf))
    # 刻みの中の曲率の最大で上限をさらに抑える(端の点の上限だけだと刻みの中で横の上限を超えうる)
    km = np.maximum(k[:-1], k[1:])
    w = vlim ** 2
    with np.errstate(divide="ignore"):
        wseg = np.where(km > 0, alat / np.maximum(km, 1e-300), np.inf)
    w[:-1] = np.minimum(w[:-1], wseg)
    w[1:] = np.minimum(w[1:], wseg)
    if v_start is not None:
        vs = _nonneg(v_start, "v_start", op)
        if vs * vs > w[0] * (1 + 1e-9):
            raise ValueError("%s: v_start exceeds the limit at s[0]" % op)
        w[0] = vs * vs
    if v_end is not None:
        ve = _nonneg(v_end, "v_end", op)
        if ve * ve > w[-1] * (1 + 1e-9):
            raise ValueError("%s: v_end exceeds the limit at s[-1]" % op)
        w[-1] = ve * ve
    vlim_out = np.sqrt(np.minimum(vlim ** 2, w))
    for i in range(len(s) - 2, -1, -1):                     # 後ろ向き(減速)
        w[i] = min(w[i], _decel_step(w[i + 1], ds[i], km[i], adec, Gt))
    for i in range(len(s) - 1):                             # 前向き(加速)
        w[i + 1] = min(w[i + 1], _decel_step(w[i], ds[i], km[i], aacc, Gt))
    v = np.sqrt(np.maximum(w, 0.0))
    ax = np.diff(w) / (2.0 * ds)
    ay_max = np.maximum(w[:-1], w[1:]) * km
    dt = np.where(v[:-1] + v[1:] > 0, 2.0 * ds / np.maximum(v[:-1] + v[1:], 1e-300), np.inf)
    return {"v": v, "v_limit": vlim_out, "ax": ax, "ay_max": ay_max, "time": np.r_[0.0, np.cumsum(dt)]}


def lateral_offset(points, path, *, start_index=None, window: int = 40) -> Dict[str, np.ndarray]:
    """点の、折線の経路に沿った弧長 s と横ずれ n(進行方向の左が正)。最も近い区間への射影。

    ``start_index``(点ごと、または 1 つ)を与えると、その区間の前後 ``window`` 区間だけを調べる(繰り返しを速くする。
    窓の外に本当の最寄りがあると誤るので、点が少しずつ動くときに使う)。None なら全区間を調べる。
    返り値: ``s``, ``n``, ``index``(区間)、``heading``(その区間の向き)。点 (2,) なら スカラー。

    **Raises** ``ValueError``: 形の誤り、start_index が範囲外。"""
    op = "lateral_offset"
    X = _array(points, "points", op)
    single = X.ndim == 1
    X = np.atleast_2d(X)
    if X.shape[1] != 2:
        raise ValueError("%s: points must be (2,) or (N, 2)" % op)
    P = _path(path, "path", op)
    cum = np.r_[0.0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    si = _start(start_index, len(X), len(P), op)
    out_s = np.empty(len(X))
    out_n = np.empty(len(X))
    out_i = np.empty(len(X), int)
    out_h = np.empty(len(X))
    for a in range(0, len(X), 512):
        seg, s, lat, hp = _nearest_on_path(P, cum, X[a:a + 512], None if si is None else si[a:a + 512], int(window))
        out_s[a:a + 512], out_n[a:a + 512], out_i[a:a + 512], out_h[a:a + 512] = s, lat, seg, hp
    if single:
        return {"s": float(out_s[0]), "n": float(out_n[0]), "index": int(out_i[0]), "heading": float(out_h[0])}
    return {"s": out_s, "n": out_n, "index": out_i, "heading": out_h}


def time_to_line_crossing(offset: float, heading_error: float, curvature: float, speed: float, *,
                          line_offset: float, lane_curvature: float = 0.0) -> float:
    """TLC: 車(の基準点)が今の曲率のまま円(または直線)を走るとして、車線の境界に届くまでの時間 [s]。

    座標: 車線の中心線の上の点を原点、中心線の向きを +x、左を +y。車は (0, ``offset``)、中心線に対する向き
    ``heading_error``、曲率 ``curvature``(左が正)。境界は中心線から横 ``line_offset``(左が正)の線 —— 中心線が
    曲率 ``lane_curvature`` の円なら、それと同心の円。届かなければ ``inf``。

    **Raises** ``ValueError``: 非有限、v ≤ 0、車がすでに境界の外側(offset と line_offset の関係で判断)。"""
    op = "time_to_line_crossing"
    y0 = _finite(offset, "offset", op)
    psi = _finite(heading_error, "heading_error", op)
    kv = _finite(curvature, "curvature", op)
    v = _positive(speed, "speed", op)
    b = _finite(line_offset, "line_offset", op)
    kr = _finite(lane_curvature, "lane_curvature", op)
    if (b > 0 and y0 >= b) or (b < 0 and y0 <= b) or b == 0.0:
        raise ValueError("%s: the point must be strictly inside the boundary" % op)
    p = np.array([0.0, y0])
    t = np.array([math.cos(psi), math.sin(psi)])
    cands = []
    if abs(kr) < 1e-15:                        # 境界 = 直線 y = b
        if abs(kv) < 1e-15:
            if abs(t[1]) > 1e-15:
                cands.append((b - y0) / t[1])
        else:
            cphi = math.cos(psi) - kv * (b - y0)       # y(s) = y0 + (cos ψ − cos(ψ + κ s))/κ
            if abs(cphi) <= 1.0:
                base = math.acos(cphi)
                for phi in (base, -base):
                    for n in range(-3, 4):
                        ss = (phi + 2 * math.pi * n - psi) / kv
                        cands.append(ss)
    else:                                       # 境界 = 中心 (0, 1/kr)、半径 |1/kr − b| の円
        cb = np.array([0.0, 1.0 / kr])
        rb = abs(1.0 / kr - b)
        if abs(kv) < 1e-15:
            f = p - cb
            qb = 2.0 * (f @ t)
            qc = f @ f - rb * rb
            disc = qb * qb - 4.0 * qc
            if disc >= 0:
                for sg in (-1.0, 1.0):
                    cands.append((-qb + sg * math.sqrt(disc)) / 2.0)
        else:
            nrm = np.array([-t[1], t[0]])
            cv = p + nrm / kv
            rv = 1.0 / abs(kv)
            dvec = cb - cv
            dd = float(np.hypot(*dvec))
            if dd > 1e-15 and abs(rv - rb) <= dd <= rv + rb:
                aa = (rv * rv - rb * rb + dd * dd) / (2.0 * dd)
                hh = math.sqrt(max(rv * rv - aa * aa, 0.0))
                mpt = cv + aa * dvec / dd
                perp = np.array([-dvec[1], dvec[0]]) / dd
                ang0 = math.atan2(p[1] - cv[1], p[0] - cv[0])
                for sg in (-1.0, 1.0):
                    X = mpt + sg * hh * perp
                    ang = math.atan2(X[1] - cv[1], X[0] - cv[0])
                    dth = (ang - ang0) * (1.0 if kv > 0 else -1.0)
                    dth = dth % (2.0 * math.pi)
                    cands.append(dth * rv)
    pos = [c for c in cands if c > 1e-12]
    return min(pos) / v if pos else math.inf


def turn_maneuver_check(trajectory: dict, *, kind: str, x_entry: float, edge_y: float, center_y: float = 0.0,
                        corner_center=None, corner_radius: float = 0.0, intersection_center=None,
                        approach: float = 30.0, keep_tol: float = 0.5, side_tol: float = 1.5,
                        inside_tol: float = 3.0, jokou: float = 10.0 / 3.6, clearance: float = 0.0) -> Dict[str, object]:
    """左折・右折の通り方の判定(道交法 34 条 1・2 項 / 教則 5-7-2)。数値の幅はすべて仮定(``SOURCES``)。

    道は +x へ進む(左 = +y)。車道の左端 y = ``edge_y``、中央線 y = ``center_y``、交差点の手前の縁 x = ``x_entry``。
    ``trajectory``: ``t``, ``front`` (N, 2)(前車軸の中心)、``rear`` (N, 2)(後車軸の中心)、``speed`` (N,)、``width``(車幅)、
    ``track``(輪距)、``front_overhang``・``rear_overhang``(車軸から車体の端まで)。

    判定:
      * 寄る(あらかじめ): x_entry − approach ≤ 前端 < x_entry の間、左折は車体の左側と左端の距離が [0, keep_tol]
        (0 未満 = 路肩・路側帯へはみ出す)、右折は車体の右側と中央線の距離が [0, keep_tol](0 未満 = 中央線をまたぐ)。
      * 徐行: 前端が x_entry を越えてから曲がり終える(向きが ±80° を超える)までの速さ ≤ ``jokou``。
      * 左折の「側端に沿って」: 曲がる間(向き 10°〜80°)の後輪の内側と隅切りの円(中心 ``corner_center``・半径
        ``corner_radius``)の距離が [``clearance``, ``side_tol``]。clearance を下回る = 内輪差で隅の人・自転車の場所に入る。
      * 右折の「交差点の中心のすぐ内側」: 前車軸の中心の軌跡が交差点の中心 ``intersection_center`` を **右(旋回の内側)に
        見ずに** 通り(中心が軌跡の外側 = 左)、最も近いときの距離 ≤ ``inside_tol``。
    返り値: ``ok``, ``violations``(理由の文字列のリスト)、``metrics``(dict)。

    **Raises** ``ValueError``: kind が "left" / "right" 以外、必要な値の欠け、形の誤り。"""
    op = "turn_maneuver_check"
    if kind not in ("left", "right"):
        raise ValueError("%s: kind must be 'left' or 'right', got %r" % (op, kind))
    if not isinstance(trajectory, dict):
        raise ValueError("%s: trajectory must be a dict" % op)
    for key in ("t", "front", "rear", "speed", "width", "track", "front_overhang", "rear_overhang"):
        if key not in trajectory:
            raise ValueError("%s: trajectory missing %r" % (op, key))
    F = _array(trajectory["front"], "front", op)
    Rr = _array(trajectory["rear"], "rear", op)
    v = _array(trajectory["speed"], "speed", op)
    n = len(F)
    if F.shape != (n, 2) or Rr.shape != (n, 2) or v.shape != (n,) or n < 2:
        raise ValueError("%s: front/rear must be (N, 2) and speed (N,)" % op)
    W = _positive(trajectory["width"], "width", op)
    tr = _positive(trajectory["track"], "track", op)
    fo = _nonneg(trajectory["front_overhang"], "front_overhang", op)
    xe = _finite(x_entry, "x_entry", op)
    ye = _finite(edge_y, "edge_y", op)
    yc = _finite(center_y, "center_y", op)
    for nm, val in (("approach", approach), ("keep_tol", keep_tol), ("side_tol", side_tol), ("inside_tol", inside_tol),
                    ("jokou", jokou)):
        _positive(val, nm, op)
    clearance = _finite(clearance, "clearance", op)
    u = F - Rr
    Lb = np.hypot(u[:, 0], u[:, 1])
    if np.any(Lb <= 0):
        raise ValueError("%s: front and rear coincide" % op)
    u = u / Lb[:, None]
    head = np.arctan2(u[:, 1], u[:, 0])
    nl = np.stack([-u[:, 1], u[:, 0]], 1)
    nose = F + fo * u
    viol = []
    met = {}
    app = (nose[:, 0] >= xe - approach) & (nose[:, 0] < xe)
    if not app.any():
        raise ValueError("%s: the trajectory has no samples in the approach zone" % op)
    if kind == "left":
        side_y = (F + 0.5 * W * nl)[:, 1]          # 車体の左側(直進中は y が最大の側)
        side_y = np.maximum(side_y, (Rr + 0.5 * W * nl)[:, 1])
        gap = ye - side_y[app]
        met["approach_gap_min"], met["approach_gap_max"] = float(gap.min()), float(gap.max())
        if gap.min() < 0:
            viol.append("左端の外(路肩・路側帯)へはみ出した(最小 %.2f m)" % gap.min())
        if gap.max() > keep_tol:
            viol.append("あらかじめ左端に寄っていない(左端まで最大 %.2f m > %.2f m)" % (gap.max(), keep_tol))
    else:
        side_y = np.minimum((F - 0.5 * W * nl)[:, 1], (Rr - 0.5 * W * nl)[:, 1])
        gap = side_y[app] - yc
        met["approach_gap_min"], met["approach_gap_max"] = float(gap.min()), float(gap.max())
        if gap.min() < 0:
            viol.append("中央線をまたいだ(最小 %.2f m)" % gap.min())
        if gap.max() > keep_tol:
            viol.append("あらかじめ中央に寄っていない(中央線まで最大 %.2f m > %.2f m)" % (gap.max(), keep_tol))
    sgn = 1.0 if kind == "left" else -1.0
    turned = sgn * head
    inside = nose[:, 0] >= xe
    done = np.nonzero(turned >= math.radians(80.0))[0]
    i_end = int(done[0]) if len(done) else n - 1
    zone = inside.copy()
    zone[i_end + 1:] = False
    if zone.any():
        vmax = float(v[zone].max())
        met["max_speed_in_turn"] = vmax
        if vmax > jokou + 1e-9:
            viol.append("徐行していない(交差点の中で最大 %.1f km/h > %.1f km/h)" % (3.6 * vmax, 3.6 * jokou))
    else:
        viol.append("交差点に入っていない")
    if not len(done):
        viol.append("曲がり終えていない")
    mid = (turned >= math.radians(10.0)) & (turned <= math.radians(80.0))
    if kind == "left":
        if corner_center is None or corner_radius <= 0:
            raise ValueError("%s: left turn needs corner_center and corner_radius > 0" % op)
        cc = _array(corner_center, "corner_center", op).reshape(2)
        rin = Rr + 0.5 * tr * nl                    # 後輪の内側(左)
        if mid.any():
            dist = np.hypot(*(rin[mid] - cc).T) - float(corner_radius)
            met["rear_inner_gap_min"], met["rear_inner_gap_max"] = float(dist.min()), float(dist.max())
            if dist.min() < clearance:
                viol.append("内輪差で隅に入った(後輪の内側と隅切りの縁 %.2f m < %.2f m)" % (dist.min(), clearance))
            if dist.max() > side_tol:
                viol.append("側端に沿っていない(後輪の内側が縁から最大 %.2f m > %.2f m)" % (dist.max(), side_tol))
    else:
        if intersection_center is None:
            raise ValueError("%s: right turn needs intersection_center" % op)
        ic = _array(intersection_center, "intersection_center", op).reshape(2)
        d = np.hypot(*(F - ic).T)
        j = int(np.argmin(d))
        jj = min(max(j, 0), n - 2)
        tang = F[jj + 1] - F[jj]
        cr = tang[0] * (ic[1] - F[j, 1]) - tang[1] * (ic[0] - F[j, 0])
        met["center_distance"] = float(d[j])
        met["center_on_left"] = bool(cr > 0)
        if cr <= 0:
            viol.append("交差点の中心の外側を回った(中心が軌跡の右 = 大回り)")
        elif d[j] > inside_tol:
            viol.append("中心のすぐ内側でない(中心から %.2f m > %.2f m = 早回り)" % (d[j], inside_tol))
    return {"ok": not viol, "violations": viol, "metrics": met}
