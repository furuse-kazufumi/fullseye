# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""RSS(Responsibility-Sensitive Safety)の安全距離: 閉形式 + 最悪ケースの時間積分(第 2 実装)+ 公表値の門。

## 何を作るか

Shalev-Shwartz, Shammah, Shashua, "On a Formal Model of Safe and Scalable Self-driving Cars"
(arXiv:1708.06374 v6)の **安全距離** を numpy だけで持つ。同方向(Lemma 2)、対向(Lemma two_way)、
横方向(Lemma lateral)の 3 つの閉形式と、それぞれの **最悪ケースの軌道を区分ごとの厳密式で時間積分する
第 2 実装**(``rss_worst_case_gap*``)を持ち、テストで「軌道の最小間隔 = d0 − d_min」を要求する。

## 真値にする一次情報(この 2 つだけ)

* 論文 arXiv:1708.06374 v6 の Lemma 2 / Lemma two_way / Lemma lateral。
* Intel ad-rss-lib(commit 847b9c2)``ad_rss/src/structured/RssFormulas.cpp`` と ``ad_rss/src/core/Physics.cpp``、
  公表パラメータ表 ``doc/ad_rss/Appendix-ParameterDiscussion.md``、テストの期待値
  ``ad_rss/tests/structured/RssFormulaTestsCalculateSafeLateralDistance.cpp`` ほか。

## 式(ad-rss-lib の "stated braking pattern" で 3 つを 1 つに)

``rss_stopping_distance(v, ρ, a, b, v_max, direction)`` は **符号つきの位置オフセット**:

1. 応答時間 ρ の間、加速度 a(符号つき、``direction`` 側 = 相手へ向かう向き)で加速する。到達速度は
   ``v_max`` で頭打ち(``max(v_max, |v|)`` を上限。既に速ければ加速しない = ad-rss-lib
   ``calculateAcceleratedLimitedMovement``)。
2. ρ 後の速度 v_ρ が **相手へ向いている(direction·v_ρ > 0)ときだけ** 停止距離 direction·v_ρ²/(2b) を足す
   (ad-rss-lib の ``signbit(resultingSpeed) != signbit(deceleration)``)。離れる向きなら足さない
   (= その時刻で止まったと見なす。相手から離れる運動は間隔を狭めないので保守的)。

これで:

* **同方向(Lemma 2)**: ``d_min = [ S(v_r; ρ, a_accel, b_min) − v_f²/(2 b_max) ]_+ + min_distance``。
  a_accel ≥ 0, v ≥ 0 なら ``S = v_r ρ + ½ a ρ² + (v_r + a ρ)²/(2 b_min)`` で論文と一致。
* **対向(Lemma two_way)**: ``d_min = S(v_1; ρ_1, a, b_min_correct) + S(|v_2|; ρ_2, a, b_min) + max(min_distance)``。
  論文の ``(v + v_ρ)/2 · ρ`` は ``v ρ + ½ a ρ²`` と同じ。
* **横方向(Lemma lateral)**: c_1 が左。``d_min = [ S(v_1; ρ_1, +a_lat, b_lat, direction=+1)
  − S(v_2; ρ_2, −a_lat, b_lat, direction=−1) + ½(μ_1 + μ_2) ]_+``(ad-rss-lib ``calculateSafeLateralDistance``)。

## 論文と ad-rss-lib が違う所(実装は ad-rss-lib に従う。理由は公表テスト値が lib のもの)

* 横方向の ``[·]_+`` の位置: 論文は ``μ + [左 − 右]_+``(下限 μ)、lib は ``[左 − 右 + μ]_+``(下限 0)。
  左 − 右 < 0(互いに離れていく)とき論文は μ、lib は ``max(左 − 右 + μ, 0)`` で **lib の方が小さい**
  (lib の公表テスト: 左 −5 km/h・右 0 で 0.0、論文の式だと 0.1)。
* 横方向の停止距離の符号: 論文の式は ρ 後の横速度が相手へ向いている(v_{1,ρ} ≥ 0, v_{2,ρ} ≤ 0)前提で書かれていて、
  離れる向き(例: 左が −5 km/h)にそのまま当てはめると ``+v_ρ²/(2b)`` が **離れる車を近づける向きに** 足される。
  lib は離れる向きなら足さない。**前提が成り立つ範囲では両者は一致する**(テストで確かめる)。
* μ は lib では両車の ``lateral_fluctuation_margin`` の平均 ``½(μ_1 + μ_2)``(論文は 1 つの μ)。
* 同方向の ``min_distance``(lib の ``min_longitudinal_safety_distance``)は論文に無い。lib は後続車の値を
  ``[·]_+`` の外で足す(対向は両車の max)。

## 最悪ケースの時間積分(第 2 実装)

各車の運動を「加速 → (頭打ちで定速) → 減速 → 停止」の等加速度区分に分け、時刻列 t の各点で
``x = x_0 + v_0 τ + ½ a τ²`` を **区分ごとの閉形式で** 評価する(累積誤差なし)。時刻列は ``dt`` 刻みの等間隔に
**区分の境目(ρ、頭打ち時刻、各車の停止時刻)を必ず加える**。間隔 gap = 相手の位置 − 自車の位置は

* 同方向: gap' = v_f − v_r が単調非増加(b_min ≤ b_max)なので gap は凹 → 最小は t = 0 か両車停止時。
  よって ``min_gap = d0 − (d_min − min_distance)``(d_min > min_distance のとき。d_min = min_distance なら d0)。
* 対向: 両車とも相手へ進むだけなので gap は単調非増加 → ``min_gap = d0 − d_min``(min_distance = 0 で)。
* 横方向: 論文の前提(ρ 後の横速度が互いに向いている: v_{1,ρ} ≥ 0, v_{2,ρ} ≤ 0)の下では gap' = v_2 − v_1 の
  符号は + → − の高々 1 回しか変わらず、最小は t = 0 か最終停止時。よって
  ``min_gap = d0 − max(d_min − μ, 0)``(μ = ½(μ_1 + μ_2)。d_min > μ なら d0 − (d_min − μ))。
  **前提の外(片方が ρ の終わりでもまだ離れる向き)では lib の閉形式は min_gap を過大評価しうる**:
  離れる車の位置を ρ 時点で凍結するが、相手はそれより前に減速を終えて速度が並ぶことがあり、その時刻の間隔は
  凍結時点の間隔より小さい(乱数 200 組の実測は RSS_REPORT.md。d_min が安全側でない分は
  ``rss_worst_case_gap_lateral`` の ``shortfall`` に出す。論文の前提の範囲では常に 0)。

## 単位と符号

m, s, m/s, m/s²。縦の速度は ≥ 0(逆走 v_2 は絶対値を使う)。横は c_1 が左、**+ が右向き**(左の車が相手へ向かう向き)。
``rss_params`` の減速度はすべて **正の大きさ**(ad-rss-lib の内部表現は負の加速度だが、公開 API は論文の記法)。

## 限界(self_reported)

* 縦方向の ``max_speed_on_acceleration`` は同方向・対向の後続/両車に効く(lib と同じ)。横方向には無い(lib と同じ)。
* 交差点・非構造化(歩行者)・横方向の "proper response" は扱わない。安全距離の式と最悪ケース軌道だけ。
* 車体寸法は含まない(距離は「後続の前端 〜 先行の後端」、横は「左車の右側面 〜 右車の左側面」)。
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

__all__ = [
    "rss_params", "rss_stopping_distance",
    "rss_longitudinal_same", "rss_longitudinal_opposite", "rss_lateral",
    "rss_longitudinal_check", "rss_lateral_check",
    "rss_worst_case_gap", "rss_worst_case_gap_opposite", "rss_worst_case_gap_lateral",
]

_PARAM_KEYS = ("rho", "accel_max", "brake_min", "brake_max", "brake_min_correct",
               "lat_accel_max", "lat_brake_min", "lat_margin", "min_distance", "v_max_accel")


# ---- 引数検査(fail-closed) ------------------------------------------------------------------------
def _finite(v, name: str, op: str) -> float:
    try:
        v = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a finite number, got %r" % (op, name, v))
    if not math.isfinite(v):
        raise ValueError("%s: %s must be a finite number, got %r" % (op, name, v))
    return v


def _positive(v, name: str, op: str) -> float:
    v = _finite(v, name, op)
    if not v > 0:
        raise ValueError("%s: %s must be a positive finite number, got %r" % (op, name, v))
    return v


def _nonneg(v, name: str, op: str) -> float:
    v = _finite(v, name, op)
    if not v >= 0:
        raise ValueError("%s: %s must be a non-negative finite number, got %r" % (op, name, v))
    return v


def _check_params(p, op: str) -> Dict[str, Optional[float]]:
    """``rss_params`` が返した形の dict を検査して正規化した copy を返す(欠け・余りのキーは拒否)。"""
    if not isinstance(p, dict):
        raise ValueError("%s: params must be a dict from rss_params(), got %r" % (op, type(p).__name__))
    missing = [k for k in _PARAM_KEYS if k not in p]
    extra = [k for k in p if k not in _PARAM_KEYS]
    if missing or extra:
        raise ValueError("%s: params keys mismatch (missing=%r, extra=%r)" % (op, missing, extra))
    return rss_params(**p)


# ---- パラメータ -----------------------------------------------------------------------------------
def rss_params(rho: float = 1.0, accel_max: float = 3.5, brake_min: float = 4.0, brake_max: float = 8.0,
               brake_min_correct: float = 3.0, lat_accel_max: float = 0.2, lat_brake_min: float = 0.8,
               lat_margin: float = 0.1, min_distance: float = 0.0,
               v_max_accel: Optional[float] = None) -> Dict[str, Optional[float]]:
    """RSS パラメータの dict を作る(既定 = ad-rss-lib の公表表、ρ は ego の 1 s)。

    ad-rss-lib ``doc/ad_rss/Appendix-ParameterDiscussion.md`` の "conservative starting point":
    ρ_ego = 1 s(他車は ``rss_params(rho=2.0)``)、a_accel_max = 3.5、a_brake_min = 4、a_brake_max = 8、
    a_brake_min_correct = 3、a^lat_brake_min = 0.8、a^lat_accel_max = 0.2、δ^lat_min(μ)= 0.1 m。

    Parameters
    ----------
    rho : 応答時間 [s](≥ 0)
    accel_max : 応答時間中の最大加速度 [m/s²](≥ 0)
    brake_min : 応答後に最低限かける減速度の大きさ [m/s²](> 0)
    brake_max : 先行車が急ブレーキでかけうる最大減速度の大きさ [m/s²](> 0、brake_min ≤ brake_max)
    brake_min_correct : 正しい車線を走る車が対向に対してかける最低減速度の大きさ(> 0、≤ brake_min)
    lat_accel_max : 横方向の最大加速度 [m/s²](≥ 0)
    lat_brake_min : 横方向の最低減速度の大きさ [m/s²](> 0)
    lat_margin : 横方向の揺らぎ余裕 μ [m](≥ 0)
    min_distance : 縦方向に停止後も残す最小間隔 [m](≥ 0。lib の ``min_longitudinal_safety_distance``)
    v_max_accel : 応答時間中の加速で到達しうる最大速度 [m/s](None = 制限なし。lib の ``max_speed_on_acceleration``)

    Returns
    -------
    dict : キー名は引数名と同じ。値は float(v_max_accel だけ None を許す)。
    """
    op = "rss_params"
    rho = _nonneg(rho, "rho", op)
    accel_max = _nonneg(accel_max, "accel_max", op)
    brake_min = _positive(brake_min, "brake_min", op)
    brake_max = _positive(brake_max, "brake_max", op)
    brake_min_correct = _positive(brake_min_correct, "brake_min_correct", op)
    lat_accel_max = _nonneg(lat_accel_max, "lat_accel_max", op)
    lat_brake_min = _positive(lat_brake_min, "lat_brake_min", op)
    lat_margin = _nonneg(lat_margin, "lat_margin", op)
    min_distance = _nonneg(min_distance, "min_distance", op)
    if v_max_accel is not None:
        v_max_accel = _nonneg(v_max_accel, "v_max_accel", op)
    if brake_min > brake_max:
        raise ValueError("%s: brake_min (%r) must not exceed brake_max (%r)" % (op, brake_min, brake_max))
    if brake_min_correct > brake_min:
        raise ValueError("%s: brake_min_correct (%r) must not exceed brake_min (%r)"
                         % (op, brake_min_correct, brake_min))
    return {
        "rho": rho, "accel_max": accel_max, "brake_min": brake_min, "brake_max": brake_max,
        "brake_min_correct": brake_min_correct, "lat_accel_max": lat_accel_max, "lat_brake_min": lat_brake_min,
        "lat_margin": lat_margin, "min_distance": min_distance, "v_max_accel": v_max_accel,
    }


# ---- stated braking pattern(閉形式の核) ------------------------------------------------------------
def _response_phase(v: float, rho: float, accel: float, v_max: Optional[float],
                    direction: float) -> Tuple[float, float, float]:
    """応答時間 ρ の区間の運動。(v_ρ, t_acc, s_ρ) を返す。

    ad-rss-lib ``calculateAcceleratedLimitedMovement``: v_ρ = v + a ρ を ``max(v_max, direction·v)`` で
    (direction 側に)頭打ち。加速に使った時間 t_acc = (v_ρ − v)/a、残り ρ − t_acc は v_ρ で定速。
    s_ρ = v t_acc + ½ a t_acc² + v_ρ (ρ − t_acc)(lib の ``v ρ + ½ a t_acc² + (v_ρ − v)(ρ − t_acc)`` と同じ)。
    """
    v_rho = v + accel * rho
    if v_max is not None:
        cap = max(v_max, direction * v)
        if direction * v_rho > cap:
            v_rho = direction * cap
    t_acc = (v_rho - v) / accel if accel != 0.0 else 0.0
    s_rho = v * t_acc + 0.5 * accel * t_acc * t_acc + v_rho * (rho - t_acc)
    return v_rho, t_acc, s_rho


def _check_stated_args(v, rho, accel, brake, v_max, direction, op: str):
    v = _finite(v, "v", op)
    rho = _nonneg(rho, "rho", op)
    accel = _finite(accel, "accel", op)
    brake = _positive(brake, "brake", op)
    if v_max is not None:
        v_max = _nonneg(v_max, "v_max", op)
    direction = _finite(direction, "direction", op)
    if direction not in (1.0, -1.0):
        raise ValueError("%s: direction must be +1 or -1, got %r" % (op, direction))
    if direction * accel < 0:
        raise ValueError("%s: accel (%r) must point in the approach direction (direction=%r) or be 0"
                         % (op, accel, direction))
    return v, rho, accel, brake, v_max, direction


def rss_stopping_distance(v: float, rho: float, accel: float, brake: float, v_max: Optional[float] = None,
                          direction: float = 1.0) -> float:
    """ad-rss-lib の stated braking pattern による **符号つき位置オフセット**(縦・横共通の 1 つの式)。

    ρ の間 ``accel`` で加速(``v_max`` で頭打ち)し、ρ 後の速度 v_ρ が **相手へ向いている**
    (``direction · v_ρ > 0``)ときだけ停止距離 ``direction · v_ρ² / (2 brake)`` を足す。
    離れる向きなら足さない(lib ``calculateLongitudinalDistanceOffsetAfterStatedBrakingPattern`` /
    ``calculateLateralDistanceOffsetAfterStatedBrakingPattern`` の ``signbit`` 判定)。

    符号規約
    --------
    * ``direction`` = 相手へ向かう向き(+1 か −1)。縦方向は +1(進行方向 = +x)。横方向は左の車が +1、右の車が −1。
    * ``v`` は符号つき速度(direction 側が正なら相手へ向かっている)。縦方向は v ≥ 0 で呼ぶ。
    * ``accel`` は符号つきで **direction 側に向ける**(``direction · accel ≥ 0`` でないと ValueError)。
      縦方向は ``+a_accel_max``、横方向は左 ``+a_lat``、右 ``−a_lat``。
    * ``brake`` は正の大きさ。常に「相手へ向かう速度を 0 にする向き」(= ``−direction`` 側)にかかる。
    * ``v_max`` は direction 側の到達速度の上限(None = 制限なし)。既に |v| がそれ以上なら加速しない。

    縦方向(v ≥ 0, accel ≥ 0)では ``v ρ + ½ a ρ² + (v + a ρ)²/(2 b)`` になり論文 Lemma 2 の後続車の走行距離と一致する。
    """
    op = "rss_stopping_distance"
    v, rho, accel, brake, v_max, direction = _check_stated_args(v, rho, accel, brake, v_max, direction, op)
    v_rho, _, s_rho = _response_phase(v, rho, accel, v_max, direction)
    s_stop = direction * v_rho * v_rho / (2.0 * brake) if direction * v_rho > 0 else 0.0
    return float(s_rho + s_stop)


# ---- 安全距離(閉形式) -------------------------------------------------------------------------------
def rss_longitudinal_same(v_rear: float, v_front: float, p: dict, p_front: Optional[dict] = None) -> float:
    """同方向(論文 Lemma 2 / lib ``calculateSafeLongitudinalDistanceSameDirection``)の最小安全距離 [m]。

    ``d_min = [ v_r ρ + ½ a ρ² + (v_r + a ρ)²/(2 b_min) − v_f²/(2 b_max) ]_+ + min_distance``。
    後続車 c_r のパラメータが ``p``(ρ, accel_max, brake_min, v_max_accel, min_distance)、先行車 c_f の
    ``brake_max`` は ``p_front``(None なら ``p``)から取る。v_rear, v_front ≥ 0。
    """
    op = "rss_longitudinal_same"
    v_rear = _nonneg(v_rear, "v_rear", op)
    v_front = _nonneg(v_front, "v_front", op)
    p = _check_params(p, op)
    pf = p if p_front is None else _check_params(p_front, op)
    d_rear = rss_stopping_distance(v_rear, p["rho"], p["accel_max"], p["brake_min"], p["v_max_accel"], 1.0)
    d_front = v_front * v_front / (2.0 * pf["brake_max"])
    return float(max(d_rear - d_front, 0.0) + p["min_distance"])


def rss_longitudinal_opposite(v1: float, v2: float, p1: dict, p2: Optional[dict] = None) -> float:
    """対向(論文 Lemma two_way / lib ``calculateSafeLongitudinalDistanceOppositeDirection``)の最小安全距離 [m]。

    c_1 は正しい車線(v1 ≥ 0、``p1`` の ``brake_min_correct`` で減速)、c_2 は逆走(v2 は負でも大きさでも受けて
    ``abs``、``p2`` の ``brake_min`` で減速)。両車とも ρ の間 ``accel_max`` で加速。
    ``d_min = S(v1; ρ_1, a_1, b_correct,1) + S(|v2|; ρ_2, a_2, b_min,2) + max(min_distance_1, min_distance_2)``。
    """
    op = "rss_longitudinal_opposite"
    v1 = _nonneg(v1, "v1", op)
    v2 = abs(_finite(v2, "v2", op))
    p1 = _check_params(p1, op)
    p2 = p1 if p2 is None else _check_params(p2, op)
    d1 = rss_stopping_distance(v1, p1["rho"], p1["accel_max"], p1["brake_min_correct"], p1["v_max_accel"], 1.0)
    d2 = rss_stopping_distance(v2, p2["rho"], p2["accel_max"], p2["brake_min"], p2["v_max_accel"], 1.0)
    return float(d1 + d2 + max(p1["min_distance"], p2["min_distance"]))


def _lateral_parts(v1: float, v2: float, p1: dict, p2: dict) -> Tuple[float, float, float]:
    left = rss_stopping_distance(v1, p1["rho"], +p1["lat_accel_max"], p1["lat_brake_min"], None, 1.0)
    right = rss_stopping_distance(v2, p2["rho"], -p2["lat_accel_max"], p2["lat_brake_min"], None, -1.0)
    mu = 0.5 * (p1["lat_margin"] + p2["lat_margin"])
    return left, right, mu


def rss_lateral(v1: float, v2: float, p1: dict, p2: Optional[dict] = None) -> float:
    """横方向(論文 Lemma lateral / lib ``calculateSafeLateralDistance``)の最小安全距離 [m]。c_1 が左。

    横速度は **+ が右向き**(左の車が相手へ向かう向き)。``d_min = [ 左のオフセット − 右のオフセット
    + ½(μ_1 + μ_2) ]_+`` で、左 = ``S(v1; ρ_1, +a_lat,1, b_lat,1, direction=+1)``、
    右 = ``S(v2; ρ_2, −a_lat,2, b_lat,2, direction=−1)``。
    ρ 後の横速度が互いに向いている範囲(v_{1,ρ} ≥ 0, v_{2,ρ} ≤ 0、かつ 左 − 右 ≥ 0)では論文の式
    ``μ + [ (v_1 + v_{1,ρ})/2 ρ + v_{1,ρ}²/(2b) − ((v_2 + v_{2,ρ})/2 ρ − v_{2,ρ}²/(2b)) ]_+`` と一致する。
    それ以外では lib に従う(モジュール docstring「論文と ad-rss-lib が違う所」)。
    """
    op = "rss_lateral"
    v1 = _finite(v1, "v1", op)
    v2 = _finite(v2, "v2", op)
    p1 = _check_params(p1, op)
    p2 = p1 if p2 is None else _check_params(p2, op)
    left, right, mu = _lateral_parts(v1, v2, p1, p2)
    return float(max(left - right + mu, 0.0))


# ---- 判定 --------------------------------------------------------------------------------------------
def _check_result(d: float, safe: float) -> Dict[str, float]:
    # lib: isDistanceSafe = (objectDistance > safe_distance)。等しい場合は危険側に倒す。
    return {"safe_distance": float(safe), "dangerous": bool(not d > safe), "margin": float(d - safe)}


def rss_longitudinal_check(d: float, v_rear: float, v_front: float, p: dict,
                           p_front: Optional[dict] = None) -> Dict[str, float]:
    """同方向の縦間隔 d(後続の前端 〜 先行の後端、≥ 0)が安全か。

    Returns ``{"safe_distance", "dangerous" (d ≤ safe_distance), "margin" (d − safe_distance)}``。
    """
    d = _nonneg(d, "d", "rss_longitudinal_check")
    return _check_result(d, rss_longitudinal_same(v_rear, v_front, p, p_front))


def rss_lateral_check(d_lat: float, v1: float, v2: float, p1: dict, p2: Optional[dict] = None) -> Dict[str, float]:
    """横間隔 d_lat(左車の右側面 〜 右車の左側面、≥ 0)が安全か。Returns は ``rss_longitudinal_check`` と同じ形。"""
    d_lat = _nonneg(d_lat, "d_lat", "rss_lateral_check")
    return _check_result(d_lat, rss_lateral(v1, v2, p1, p2))


# ---- 最悪ケースの軌道(第 2 実装: 区分ごとの厳密式) ------------------------------------------------------
# 区分 = (t0, t1, x_at_t0, v_at_t0, a)。区分の外(t ≥ 最後の t1)は停止して位置 x_end。
Segment = Tuple[float, float, float, float, float]


def _segments(x0: float, v: float, rho: float, accel: float, brake: float, v_max: Optional[float],
              direction: float) -> Tuple[List[Segment], float, float]:
    """stated braking pattern の区分列。(segments, x_end, t_end) を返す。区分の境目が t_end までの breakpoints。"""
    v_rho, t_acc, _ = _response_phase(v, rho, accel, v_max, direction)
    segs: List[Segment] = []
    t, x, vel = 0.0, x0, v
    if t_acc > 0:                                   # 加速区分
        segs.append((0.0, t_acc, x, vel, accel))
        x += vel * t_acc + 0.5 * accel * t_acc * t_acc
        vel, t = v_rho, t_acc
    if rho > t:                                     # 頭打ち後の定速区分(t_acc = 0 なら ρ 全体)
        segs.append((t, rho, x, vel, 0.0))
        x += vel * (rho - t)
        vel, t = v_rho, rho
    if direction * v_rho > 0:                       # 相手へ向いているときだけ減速して停止
        t_stop = t + abs(v_rho) / brake
        a = -direction * brake
        segs.append((t, t_stop, x, v_rho, a))
        x += v_rho * (t_stop - t) + 0.5 * a * (t_stop - t) ** 2
        t = t_stop
    return segs, x, t


def _evaluate(segs: Sequence[Segment], x_end: float, t: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """時刻列 t での位置と速度(区分ごとの閉形式、区分の外は停止)。"""
    x = np.full(t.shape, x_end, dtype=np.float64)
    vel = np.zeros(t.shape, dtype=np.float64)
    for (t0, t1, xs, vs, a) in segs:
        m = (t >= t0) & (t < t1)
        tau = t[m] - t0
        x[m] = xs + vs * tau + 0.5 * a * tau * tau
        vel[m] = vs + a * tau
    return x, vel


def _time_grid(dt: float, t_max: float, breakpoints: Sequence[float]) -> np.ndarray:
    """dt 刻みの等間隔 + 区分の境目(t_max 以下)+ t_max。境目をまたいで積分しないための時刻列。"""
    base = np.arange(0.0, t_max, dt) if t_max > 0 else np.zeros(1)
    bps = [b for b in breakpoints if 0.0 <= b <= t_max] + [0.0, t_max]
    return np.union1d(base, np.asarray(bps, dtype=np.float64))


def _breakpoints(segs: Sequence[Segment]) -> List[float]:
    out: List[float] = []
    for (t0, t1, _, _, _) in segs:
        out.extend((t0, t1))
    return out


def _worst_case(d0: float, ego: Tuple[List[Segment], float, float], other: Tuple[List[Segment], float, float],
                dt: float, t_max: Optional[float], op: str) -> Dict[str, object]:
    segs_e, xend_e, tend_e = ego
    segs_o, xend_o, tend_o = other
    t_end = max(tend_e, tend_o)
    if t_max is None:
        t_max = t_end
    else:
        t_max = _positive(t_max, "t_max", op)
    t = _time_grid(dt, t_max, _breakpoints(segs_e) + _breakpoints(segs_o))
    x_e, v_e = _evaluate(segs_e, xend_e, t)
    x_o, v_o = _evaluate(segs_o, xend_o, t)
    gap = x_o - x_e
    i = int(np.argmin(gap))
    return {"t": t, "x_ego": x_e, "x_other": x_o, "v_ego": v_e, "v_other": v_o, "gap": gap,
            "min_gap": float(gap[i]), "t_min": float(t[i]), "collided": bool(gap[i] < 0.0),
            "t_stop_ego": float(tend_e), "t_stop_other": float(tend_o)}


def rss_worst_case_gap(d0: float, v_rear: float, v_front: float, p: dict, p_front: Optional[dict] = None,
                       dt: float = 1e-3, t_max: Optional[float] = None) -> Dict[str, object]:
    """同方向の最悪ケース(論文 Definition 4)を時間で追う。

    先行車は t = 0 から ``brake_max`` で停止まで減速。後続車は ρ の間 ``accel_max``(``v_max_accel`` で頭打ち)、
    その後 ``brake_min`` で停止まで減速。各時刻の位置は区分ごとの等加速度の厳密式で、時刻列には ρ・頭打ち時刻・
    各車の停止時刻を必ず含める(``dt`` は表示密度で、min_gap は dt に依らない)。

    Returns
    -------
    dict : ``t, x_rear, x_front, v_rear, v_front, gap`` (ndarray)、``min_gap, t_min`` (float)、
           ``collided`` (min_gap < 0)、``t_stop_rear, t_stop_front``。gap = x_front − x_rear
           (後続の前端と先行の後端の間隔、後続は x = 0、先行は x = d0 から出発)。
           ``min_gap = d0 − max(d_min − min_distance, 0)`` が成り立つ(d_min = ``rss_longitudinal_same``)。
    ``t_max`` を与えると(両車の停止より前で)打ち切る。
    """
    op = "rss_worst_case_gap"
    d0 = _nonneg(d0, "d0", op)
    v_rear = _nonneg(v_rear, "v_rear", op)
    v_front = _nonneg(v_front, "v_front", op)
    dt = _positive(dt, "dt", op)
    p = _check_params(p, op)
    pf = p if p_front is None else _check_params(p_front, op)
    rear = _segments(0.0, v_rear, p["rho"], p["accel_max"], p["brake_min"], p["v_max_accel"], 1.0)
    front = _segments(d0, v_front, 0.0, 0.0, pf["brake_max"], None, 1.0)
    r = _worst_case(d0, rear, front, dt, t_max, op)
    return {"t": r["t"], "x_rear": r["x_ego"], "x_front": r["x_other"], "v_rear": r["v_ego"],
            "v_front": r["v_other"], "gap": r["gap"], "min_gap": r["min_gap"], "t_min": r["t_min"],
            "collided": r["collided"], "t_stop_rear": r["t_stop_ego"], "t_stop_front": r["t_stop_other"]}


def rss_worst_case_gap_opposite(d0: float, v1: float, v2: float, p1: dict, p2: Optional[dict] = None,
                                dt: float = 1e-3, t_max: Optional[float] = None) -> Dict[str, object]:
    """対向の最悪ケース: 両車 ρ の間 ``accel_max`` で加速 → c_1 は ``brake_min_correct``、c_2 は ``brake_min`` で停止。

    c_1 は x = 0 から +x へ、c_2 は x = d0 から −x へ(v2 は絶対値)。gap = x_2 − x_1。
    Returns ``t, x1, x2, v1, v2, gap, min_gap, t_min, collided, t_stop_1, t_stop_2``。
    ``min_gap = d0 − (d_min − max(min_distance))`` が成り立つ(d_min = ``rss_longitudinal_opposite``)。
    """
    op = "rss_worst_case_gap_opposite"
    d0 = _nonneg(d0, "d0", op)
    v1 = _nonneg(v1, "v1", op)
    v2 = abs(_finite(v2, "v2", op))
    dt = _positive(dt, "dt", op)
    p1 = _check_params(p1, op)
    p2 = p1 if p2 is None else _check_params(p2, op)
    c1 = _segments(0.0, v1, p1["rho"], p1["accel_max"], p1["brake_min_correct"], p1["v_max_accel"], 1.0)
    c2 = _segments(d0, -v2, p2["rho"], -p2["accel_max"], p2["brake_min"], p2["v_max_accel"], -1.0)
    r = _worst_case(d0, c1, c2, dt, t_max, op)
    return {"t": r["t"], "x1": r["x_ego"], "x2": r["x_other"], "v1": r["v_ego"], "v2": r["v_other"],
            "gap": r["gap"], "min_gap": r["min_gap"], "t_min": r["t_min"], "collided": r["collided"],
            "t_stop_1": r["t_stop_ego"], "t_stop_2": r["t_stop_other"]}


def rss_worst_case_gap_lateral(d0: float, v1: float, v2: float, p1: dict, p2: Optional[dict] = None,
                               dt: float = 1e-3, t_max: Optional[float] = None) -> Dict[str, object]:
    """横方向の最悪ケース: ρ の間 互いに向かって ``lat_accel_max`` → ``lat_brake_min`` で横速度 0 まで減速。

    c_1(左)は y = 0、c_2(右)は y = d0 から。+ が右向き。ρ 後の横速度が相手から離れる向きの車は
    その時点で止まったと見なす(lib の stated pattern と同じ。離れる運動は間隔を狭めない)。
    gap = y_2 − y_1。μ は **最終間隔** の下限(論文 Definition lateral_safe_distance)なので比較は μ を除く:
    論文の前提(v_{1,ρ} ≥ 0, v_{2,ρ} ≤ 0)の下で ``min_gap = d0 − max(d_min − μ, 0)``
    (μ = ½(μ_1 + μ_2)、d_min = ``rss_lateral``)。前提の外では ``min_gap`` はこの値以下になりうる
    (モジュール docstring「最悪ケースの時間積分」)。
    Returns ``t, y1, y2, v1, v2, gap, min_gap, t_min, collided (min_gap < 0), margin (μ),
    final_gap (両車停止後の間隔 = gap[-1]、t_max で打ち切ればその時刻の間隔), margin_violated (final_gap < μ),
    min_gap_closed_form (= d0 − max(d_min − μ, 0)), shortfall (= min_gap_closed_form − min_gap ≥ 0、閉形式が
    安全側でない分), paper_assumption (両車の ρ 後の横速度が互いに向いているか), t_stop_1, t_stop_2``。
    d0 > d_min ⇔ final_gap > μ(lib の "safe" と同値)。
    """
    op = "rss_worst_case_gap_lateral"
    d0 = _nonneg(d0, "d0", op)
    v1 = _finite(v1, "v1", op)
    v2 = _finite(v2, "v2", op)
    dt = _positive(dt, "dt", op)
    p1 = _check_params(p1, op)
    p2 = p1 if p2 is None else _check_params(p2, op)
    c1 = _segments(0.0, v1, p1["rho"], +p1["lat_accel_max"], p1["lat_brake_min"], None, 1.0)
    c2 = _segments(d0, v2, p2["rho"], -p2["lat_accel_max"], p2["lat_brake_min"], None, -1.0)
    r = _worst_case(d0, c1, c2, dt, t_max, op)
    left, right, mu = _lateral_parts(v1, v2, p1, p2)
    closed = d0 - max(left - right, 0.0)              # = d0 − max(d_min − μ, 0)
    v1_rho = _response_phase(v1, p1["rho"], +p1["lat_accel_max"], None, 1.0)[0]
    v2_rho = _response_phase(v2, p2["rho"], -p2["lat_accel_max"], None, -1.0)[0]
    return {"t": r["t"], "y1": r["x_ego"], "y2": r["x_other"], "v1": r["v_ego"], "v2": r["v_other"],
            "gap": r["gap"], "min_gap": r["min_gap"], "t_min": r["t_min"], "collided": r["collided"],
            "margin": float(mu), "final_gap": float(r["gap"][-1]), "margin_violated": bool(r["gap"][-1] < mu),
            "min_gap_closed_form": float(closed), "shortfall": float(max(closed - r["min_gap"], 0.0)),
            "paper_assumption": bool(v1_rho >= 0.0 and v2_rho <= 0.0),
            "t_stop_1": r["t_stop_ego"], "t_stop_2": r["t_stop_other"]}
