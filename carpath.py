# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""車の最短経路(numpy + scipy のみ): Dubins・Reeds–Shepp の閉形式と、占有格子の上の Hybrid A*。

## 何を解くか

前輪で舵を切る車(曲率の上限 1/ρ、ρ = 最小回転半径)が姿勢 (x, y, θ) から姿勢 (x', y', θ') へ
移る最短の道。

* **Dubins(1957)**: 前進のみ。最短路は「円弧・直線・円弧」の 3 区間で、語は
  LSL / RSR / LSR / RSL / RLR / LRL の 6 つに限られる(定理)。各語の区間長は閉形式。
* **Reeds–Shepp(1990)**: 後退を許す。最短路は高々 5 区間で、語は 48(Sussmann–Tang 1991 で 46 に
  減る)。OMPL と同じ 44 本の式(時間反転・鏡映・逆行の対称で基本 12 本を展開)で全候補を作る。
* **Hybrid A\***(Dolgov・Thrun・Montemerlo・Diebel 2010): 占有格子の上で、連続な姿勢を離散セル
  (x, y, θ)で枝刈りしながら A* を回す。運動基本形は {左・直進・右} × {前進・後退}、ヒューリス
  ティックは障害物を無視した Reeds–Shepp 長(前進のみなら Dubins 長)—— 費用が長さ + 非負の罰則で
  あれば許容(真の費用を超えない)。節点から目標へ Reeds–Shepp の「解析的な一撃」を試し、衝突しなければ
  そこで終わる。**障害物の無い格子では、最初の一撃が通るので答えは Reeds–Shepp 長そのもの**(門)。

## 正しさの担保(fail-closed)

閉形式の各候補は **前進積分で終点を検証**し、目標に着かない候補は捨てて ``n_rejected`` に数える
(式の写し間違いは「候補が落ちる」として数に出る。テストは乱数の姿勢で ``n_rejected == 0`` を要求する)。
テストと PoC では、語ごとの区間長を未知数にした終点方程式を SLSQP で多数の初期値から解く
**第 2 実装**と比べる。ほかに RS ≤ Dubins、可逆対称 L(s, g) = L(g, s)、鏡映対称、剛体変換で不変、
ρ に比例、三角不等式、ユークリッド距離が下界、を門にする。

座標: 姿勢は ``(x, y, theta)``(theta はラジアン、x 軸から反時計回り)。左折 = θ が増える。
"""
from __future__ import annotations

import heapq
import math

import numpy as np
from scipy import ndimage

__all__ = ["car_dubins_path", "car_reeds_shepp_path", "car_hybrid_astar"]

_TWO_PI = 2.0 * math.pi
_ZERO = 1e-9


# ---- 角度・積分 -------------------------------------------------------------------------------
def _mod2pi(x: float) -> float:
    """[0, 2π) に折る。"""
    return x - _TWO_PI * math.floor(x / _TWO_PI)


def _wrap(x: float) -> float:
    """(−π, π] に折る。"""
    return x - _TWO_PI * math.floor((x + math.pi) / _TWO_PI)


def _polar(x: float, y: float) -> tuple[float, float]:
    return math.hypot(x, y), math.atan2(y, x)


def _step_segment(x, y, th, kind: str, l: float):
    """単位半径で 1 区間を進める(l は符号つき弧長、負 = 後退)。"""
    if kind == "S":
        return x + l * math.cos(th), y + l * math.sin(th), th
    if kind == "L":
        th2 = th + l
        return x + math.sin(th2) - math.sin(th), y - math.cos(th2) + math.cos(th), th2
    if kind == "R":
        th2 = th - l
        return x - math.sin(th2) + math.sin(th), y + math.cos(th2) - math.cos(th), th2
    raise ValueError("unknown segment kind %r" % kind)


def _integrate(word: str, lens, start, rho: float):
    """語と区間長(単位半径)を start から積分した終点(実寸)。"""
    x, y, th = float(start[0]) / rho, float(start[1]) / rho, float(start[2])
    for k, l in zip(word, lens):
        x, y, th = _step_segment(x, y, th, k, float(l))
    return x * rho, y * rho, th


def _sample(word: str, lens, start, rho: float, step: float) -> np.ndarray:
    """語を弧長 step(実寸)ごとに標本化した (N, 3) の姿勢列(始点と終点を含む)。"""
    x, y, th = float(start[0]) / rho, float(start[1]) / rho, float(start[2])
    pts = [(x * rho, y * rho, th)]
    for k, l in zip(word, lens):
        l = float(l)
        n = max(1, int(math.ceil(abs(l) * rho / step - 1e-9)))
        for i in range(1, n + 1):
            xi, yi, ti = _step_segment(x, y, th, k, l * i / n)
            pts.append((xi * rho, yi * rho, ti))
        x, y, th = _step_segment(x, y, th, k, l)
    return np.asarray(pts, float)


def _endpoint_error(word, lens, start, goal, rho) -> float:
    ex, ey, eth = _integrate(word, lens, start, rho)
    return max(abs(ex - goal[0]) / rho, abs(ey - goal[1]) / rho, abs(_wrap(eth - goal[2])))


def _relative(start, goal, rho: float):
    """goal を start の車体座標に(単位半径)。(x, y, phi)。"""
    dx, dy = (goal[0] - start[0]) / rho, (goal[1] - start[1]) / rho
    c, s = math.cos(start[2]), math.sin(start[2])
    return c * dx + s * dy, -s * dx + c * dy, _wrap(goal[2] - start[2])


# ---- Dubins(6 語)-------------------------------------------------------------------------------
def _dubins_candidates(x: float, y: float, phi: float):
    """車体座標 (x, y, phi)(単位半径)に対する 6 語の候補 [(word, (t, p, q))]。式は Shkel–Lumelsky 2001。"""
    d, theta = _polar(x, y)
    alpha = _mod2pi(-theta)
    beta = _mod2pi(phi - theta)
    sa, sb, ca, cb = math.sin(alpha), math.sin(beta), math.cos(alpha), math.cos(beta)
    cab = math.cos(alpha - beta)
    out = []
    # LSL
    p_sq = 2 + d * d - 2 * cab + 2 * d * (sa - sb)
    if p_sq >= 0:
        tmp = math.atan2(cb - ca, d + sa - sb)
        out.append(("LSL", (_mod2pi(-alpha + tmp), math.sqrt(p_sq), _mod2pi(beta - tmp))))
    # RSR
    p_sq = 2 + d * d - 2 * cab + 2 * d * (sb - sa)
    if p_sq >= 0:
        tmp = math.atan2(ca - cb, d - sa + sb)
        out.append(("RSR", (_mod2pi(alpha - tmp), math.sqrt(p_sq), _mod2pi(-beta + tmp))))
    # LSR
    p_sq = -2 + d * d + 2 * cab + 2 * d * (sa + sb)
    if p_sq >= 0:
        p = math.sqrt(p_sq)
        tmp = math.atan2(-ca - cb, d + sa + sb) - math.atan2(-2.0, p)
        out.append(("LSR", (_mod2pi(-alpha + tmp), p, _mod2pi(-_mod2pi(beta) + tmp))))
    # RSL
    p_sq = d * d - 2 + 2 * cab - 2 * d * (sa + sb)
    if p_sq >= 0:
        p = math.sqrt(p_sq)
        tmp = math.atan2(ca + cb, d - sa - sb) - math.atan2(2.0, p)
        out.append(("RSL", (_mod2pi(alpha - tmp), p, _mod2pi(beta - tmp))))
    # RLR
    tmp = (6 - d * d + 2 * cab + 2 * d * (sa - sb)) / 8.0
    if abs(tmp) <= 1:
        p = _mod2pi(_TWO_PI - math.acos(tmp))
        t = _mod2pi(alpha - math.atan2(ca - cb, d - sa + sb) + p / 2.0)
        out.append(("RLR", (t, p, _mod2pi(alpha - beta - t + p))))
    # LRL
    tmp = (6 - d * d + 2 * cab + 2 * d * (sb - sa)) / 8.0
    if abs(tmp) <= 1:
        p = _mod2pi(_TWO_PI - math.acos(tmp))
        t = _mod2pi(-alpha - math.atan2(ca - cb, d + sa - sb) + p / 2.0)
        out.append(("LRL", (t, p, _mod2pi(_mod2pi(beta) - alpha - t + p))))
    return out


def _dubins(start, goal, rho: float, tol: float = 1e-7):
    """検証済みの候補を短い順に。(candidates, n_rejected)。candidates = [(length_units, word, lens)]。"""
    x, y, phi = _relative(start, goal, rho)
    ok, rejected = [], 0
    for word, lens in _dubins_candidates(x, y, phi):
        if not all(np.isfinite(lens)):
            rejected += 1
            continue
        err = _endpoint_error(word, lens, (0.0, 0.0, 0.0), (x, y, phi), 1.0)
        if err > tol * (1.0 + abs(x) + abs(y)):
            rejected += 1
            continue
        ok.append((float(sum(lens)), word, tuple(float(v) for v in lens)))
    ok.sort(key=lambda c: c[0])
    return ok, rejected


# ---- Reeds–Shepp(48 語、OMPL の 44 式)-----------------------------------------------------------
# ★OMPL の mod2pi は (−π, π] に折る(Python の [0, 2π) ではない)。ここを [0, 2π) にすると t >= 0 の判定が常に真に
#   なり、CCSC 系 8 語が一度も候補に出ず(2026-09-28 に語の族を数えて発見)、負の区間長が 2π − |t| の遠回りに化ける。
_RS_TYPES = (
    "LRL", "RLR", "LRLR", "RLRL", "LRSL", "RLSR", "LSRL", "RSLR", "LRSR", "RLSL",
    "RSRL", "LSLR", "LSR", "RSL", "LSL", "RSR", "LRSLR", "RLSRL",
)


def _tau_omega(u, v, xi, eta, phi):
    delta = _wrap(u - v)
    A = math.sin(u) - math.sin(delta)
    B = math.cos(u) - math.cos(delta) - 1.0
    t1 = math.atan2(eta * A - xi * B, xi * A + eta * B)
    t2 = 2.0 * (math.cos(delta) - math.cos(v) - math.cos(u)) + 3.0
    tau = _wrap(t1 + math.pi) if t2 < 0 else _wrap(t1)
    return tau, _wrap(tau - u + v - phi)


def _LpSpLp(x, y, phi):  # 8.1
    u, t = _polar(x - math.sin(phi), y - 1.0 + math.cos(phi))
    if t >= -_ZERO:
        v = _wrap(phi - t)
        if v >= -_ZERO:
            return t, u, v
    return None


def _LpSpRp(x, y, phi):  # 8.2
    u1, t1 = _polar(x + math.sin(phi), y - 1.0 - math.cos(phi))
    u1 = u1 * u1
    if u1 >= 4.0:
        u = math.sqrt(u1 - 4.0)
        theta = math.atan2(2.0, u)
        t = _wrap(t1 + theta)
        v = _wrap(t - phi)
        if t >= -_ZERO and v >= -_ZERO:
            return t, u, v
    return None


def _LpRmL(x, y, phi):  # 8.3 / 8.4(論文の誤植を Sussmann–Tang / OMPL に合わせて直した形)
    xi, eta = x - math.sin(phi), y - 1.0 + math.cos(phi)
    u1, theta = _polar(xi, eta)
    if u1 <= 4.0:
        u = -2.0 * math.asin(0.25 * u1)
        t = _wrap(theta + 0.5 * u + math.pi)
        v = _wrap(phi - t + u)
        if t >= -_ZERO and u <= _ZERO:
            return t, u, v
    return None


def _LpRupLumRm(x, y, phi):  # 8.7
    xi, eta = x + math.sin(phi), y - 1.0 - math.cos(phi)
    rho = 0.25 * (2.0 + math.hypot(xi, eta))
    if rho <= 1.0:
        u = math.acos(rho)
        t, v = _tau_omega(u, -u, xi, eta, phi)
        if t >= -_ZERO and v <= _ZERO:
            return t, u, v
    return None


def _LpRumLumRp(x, y, phi):  # 8.8
    xi, eta = x + math.sin(phi), y - 1.0 - math.cos(phi)
    rho = (20.0 - xi * xi - eta * eta) / 16.0
    if 0.0 <= rho <= 1.0:
        u = -math.acos(rho)
        if u >= -0.5 * math.pi:
            t, v = _tau_omega(u, u, xi, eta, phi)
            if t >= -_ZERO and v >= -_ZERO:
                return t, u, v
    return None


def _LpRmSmLm(x, y, phi):  # 8.9
    xi, eta = x - math.sin(phi), y - 1.0 + math.cos(phi)
    rho, theta = _polar(xi, eta)
    if rho >= 2.0:
        r = math.sqrt(rho * rho - 4.0)
        u = 2.0 - r
        t = _wrap(theta + math.atan2(r, -2.0))
        v = _wrap(phi - 0.5 * math.pi - t)
        if t >= -_ZERO and u <= _ZERO and v <= _ZERO:
            return t, u, v
    return None


def _LpRmSmRm(x, y, phi):  # 8.10
    xi, eta = x + math.sin(phi), y - 1.0 - math.cos(phi)
    rho, theta = _polar(-eta, xi)
    if rho >= 2.0:
        t = theta
        u = 2.0 - rho
        v = _wrap(t + 0.5 * math.pi - phi)
        if t >= -_ZERO and u <= _ZERO and v <= _ZERO:
            return t, u, v
    return None


def _LpRmSLmRp(x, y, phi):  # 8.11(論文の誤植を直した形)
    xi, eta = x + math.sin(phi), y - 1.0 - math.cos(phi)
    rho, _theta = _polar(xi, eta)
    if rho >= 2.0:
        u = 4.0 - math.sqrt(rho * rho - 4.0)
        if u <= _ZERO:
            t = _wrap(math.atan2((4.0 - u) * xi - 2.0 * eta, -2.0 * xi + (u - 4.0) * eta))
            v = _wrap(t - phi)
            if t >= -_ZERO and v >= -_ZERO:
                return t, u, v
    return None


def _rs_candidates(x: float, y: float, phi: float):
    """車体座標 (x, y, phi)(単位半径)に対する 44 式の候補 [(word, lens)](lens は符号つき、負 = 後退)。"""
    out = []
    HP = 0.5 * math.pi

    def add(word, lens):
        out.append((word, tuple(lens)))

    # 4 つの対称: そのまま / 時間反転 (-x, y, -phi) → 区間長の符号を反転 / 鏡映 (x, -y, -phi) → L↔R /
    # 両方 (-x, -y, phi)。
    def four(fn, word, mirror, build):
        r = fn(x, y, phi)
        if r:
            add(word, build(*r, 1.0))
        r = fn(-x, y, -phi)
        if r:
            add(word, build(*r, -1.0))
        r = fn(x, -y, -phi)
        if r:
            add(mirror, build(*r, 1.0))
        r = fn(-x, -y, phi)
        if r:
            add(mirror, build(*r, -1.0))

    # 逆行(backwards): 終点から始点へ読む
    xb, yb = x * math.cos(phi) + y * math.sin(phi), x * math.sin(phi) - y * math.cos(phi)

    def four_back(fn, word, mirror, build):
        r = fn(xb, yb, phi)
        if r:
            add(word, build(*r, 1.0))
        r = fn(-xb, yb, -phi)
        if r:
            add(word, build(*r, -1.0))
        r = fn(xb, -yb, -phi)
        if r:
            add(mirror, build(*r, 1.0))
        r = fn(-xb, -yb, phi)
        if r:
            add(mirror, build(*r, -1.0))

    # CSC
    four(_LpSpLp, "LSL", "RSR", lambda t, u, v, s: (s * t, s * u, s * v))
    four(_LpSpRp, "LSR", "RSL", lambda t, u, v, s: (s * t, s * u, s * v))
    # CCC
    four(_LpRmL, "LRL", "RLR", lambda t, u, v, s: (s * t, s * u, s * v))
    four_back(_LpRmL, "LRL", "RLR", lambda t, u, v, s: (s * v, s * u, s * t))
    # CCCC
    four(_LpRupLumRm, "LRLR", "RLRL", lambda t, u, v, s: (s * t, s * u, -s * u, s * v))
    four(_LpRumLumRp, "LRLR", "RLRL", lambda t, u, v, s: (s * t, s * u, s * u, s * v))
    # CCSC
    four(_LpRmSmLm, "LRSL", "RLSR", lambda t, u, v, s: (s * t, -s * HP, s * u, s * v))
    four(_LpRmSmRm, "LRSR", "RLSL", lambda t, u, v, s: (s * t, -s * HP, s * u, s * v))
    four_back(_LpRmSmLm, "LSRL", "RSLR", lambda t, u, v, s: (s * v, s * u, -s * HP, s * t))
    four_back(_LpRmSmRm, "RSRL", "LSLR", lambda t, u, v, s: (s * v, s * u, -s * HP, s * t))
    # CCSCC
    four(_LpRmSLmRp, "LRSLR", "RLSRL", lambda t, u, v, s: (s * t, -s * HP, s * u, -s * HP, s * v))
    return out


def _reeds_shepp(start, goal, rho: float, tol: float = 1e-7):
    """検証済みの候補を短い順に。(candidates, n_rejected)。candidates = [(length_units, word, lens)]。"""
    x, y, phi = _relative(start, goal, rho)
    ok, rejected = [], 0
    for word, lens in _rs_candidates(x, y, phi):
        if not all(np.isfinite(lens)):
            rejected += 1
            continue
        err = _endpoint_error(word, lens, (0.0, 0.0, 0.0), (x, y, phi), 1.0)
        if err > tol * (1.0 + abs(x) + abs(y)):
            rejected += 1
            continue
        ok.append((float(sum(abs(v) for v in lens)), word, tuple(float(v) for v in lens)))
    ok.sort(key=lambda c: c[0])
    return ok, rejected


def _rs_length(start, goal, rho: float) -> float:
    ok, _ = _reeds_shepp(start, goal, rho)
    return ok[0][0] * rho if ok else math.inf


def _dubins_length(start, goal, rho: float) -> float:
    ok, _ = _dubins(start, goal, rho)
    return ok[0][0] * rho if ok else math.inf


# ---- 入力検査 -----------------------------------------------------------------------------------
def _poses(poses, op: str):
    a = np.asarray(poses, float)
    if a.shape != (2, 3):
        raise ValueError("%s: poses must have shape (2, 3) = [[x, y, theta], [x', y', theta']], got %s"
                         % (op, a.shape))
    if not np.all(np.isfinite(a)):
        raise ValueError("%s: poses must be finite" % op)
    return tuple(a[0]), tuple(a[1])


def _positive(v, name: str, op: str) -> float:
    v = float(v)
    if not (np.isfinite(v) and v > 0):
        raise ValueError("%s: %s must be a positive finite number, got %r" % (op, name, v))
    return v


def _segments(word: str, lens, rho: float):
    """[(kind, gear, length_m)]: kind ∈ {L,S,R}、gear = +1 前進 / −1 後退、長さは実寸(非負)。長さ 0 の区間は省く。"""
    out = []
    for k, l in zip(word, lens):
        if abs(l) * rho > 1e-12:
            out.append((k, 1 if l >= 0 else -1, abs(float(l)) * rho))
    return out


# ---- 公開 op: Dubins / Reeds–Shepp ---------------------------------------------------------------
def car_dubins_path(poses, radius=1.0, step=0.05):
    """Shortest forward-only path of a car between two poses (Dubins 1957) by the six closed-form words.

    ``poses`` is ``[[x, y, theta], [x', y', theta']]`` (start, goal; theta in radians, counter-clockwise
    from the x axis). The car turns with minimum radius ``radius`` and never reverses. Dubins proved the
    shortest path is one of LSL, RSR, LSR, RSL, RLR, LRL (arcs of maximal curvature and straights); each
    word's three segment lengths are closed-form (Shkel and Lumelsky 2001). Every candidate is verified
    by forward integration to the goal and discarded if it misses (fail-closed against formula slips;
    the count is returned as ``n_rejected``), and the shortest survivor is the answer.

    Returns ``word``, ``length`` (metres), ``segments`` ``[(kind, gear, length)]`` (kind L/S/R, gear +1),
    ``points`` ``(N, 3)`` poses sampled every ``step`` metres along the path (start and goal included),
    ``candidates`` ``[(word, length)]`` for all verified words in increasing length, ``n_rejected``,
    ``lower_bound`` (the Euclidean distance, never exceeded), ``radius``.

    **Raises** ``ValueError``: poses not ``(2, 3)`` finite; ``radius`` or ``step`` not positive; no word
    reaches the goal (cannot happen for finite poses; reported rather than guessed).
    """
    op = "car_dubins_path"
    start, goal = _poses(poses, op)
    rho = _positive(radius, "radius", op)
    step = _positive(step, "step", op)
    ok, rejected = _dubins(start, goal, rho)
    if not ok:
        raise ValueError("%s: no Dubins word reached the goal (n_rejected=%d)" % (op, rejected))
    length_u, word, lens = ok[0]
    return {
        "word": word,
        "length": length_u * rho,
        "segments": _segments(word, lens, rho),
        "points": _sample(word, lens, start, rho, step),
        "candidates": [(w, L * rho) for L, w, _ in ok],
        "n_rejected": int(rejected),
        "lower_bound": float(math.hypot(goal[0] - start[0], goal[1] - start[1])),
        "radius": rho,
    }


def car_reeds_shepp_path(poses, radius=1.0, step=0.05):
    """Shortest path of a car that may reverse, between two poses (Reeds and Shepp 1990), by closed form.

    ``poses`` is ``[[x, y, theta], [x', y', theta']]`` (start, goal). The car turns with minimum radius
    ``radius`` and may change gear. Reeds and Shepp proved the shortest path has at most five segments
    drawn from 48 words (Sussmann and Tang 1991: 46 suffice); the 44 formulas used here (the 12 base
    words of the paper expanded by time reversal, reflection and backwards reading, as in OMPL) generate
    every candidate. Each candidate is verified by forward integration and discarded if it misses the
    goal (counted in ``n_rejected``); the shortest survivor is the answer. Reversed segments carry
    ``gear = -1``.

    Returns ``word`` (letters L/S/R; reversed segments are lower-case), ``length`` (metres, sum of
    absolute segment lengths), ``segments`` ``[(kind, gear, length)]``, ``points`` ``(N, 3)`` poses
    sampled every ``step`` metres, ``candidates`` ``[(word, length)]`` sorted, ``n_candidates``,
    ``n_rejected``, ``lower_bound`` (Euclidean distance), ``radius``.

    **Raises** ``ValueError``: poses not ``(2, 3)`` finite; ``radius`` or ``step`` not positive; no word
    reached the goal.
    """
    op = "car_reeds_shepp_path"
    start, goal = _poses(poses, op)
    rho = _positive(radius, "radius", op)
    step = _positive(step, "step", op)
    ok, rejected = _reeds_shepp(start, goal, rho)
    if not ok:
        raise ValueError("%s: no Reeds-Shepp word reached the goal (n_rejected=%d)" % (op, rejected))
    length_u, word, lens = ok[0]
    return {
        "word": _signed_word(word, lens),
        "length": length_u * rho,
        "segments": _segments(word, lens, rho),
        "points": _sample(word, lens, start, rho, step),
        "candidates": [(_signed_word(w, l), L * rho) for L, w, l in ok],
        "n_candidates": len(ok),
        "n_rejected": int(rejected),
        "lower_bound": float(math.hypot(goal[0] - start[0], goal[1] - start[1])),
        "radius": rho,
    }


def _signed_word(word: str, lens) -> str:
    return "".join(k.lower() if l < 0 else k for k, l in zip(word, lens) if abs(l) > 1e-12)


# ---- Hybrid A* -----------------------------------------------------------------------------------
def _footprint_points(footprint, cell: float):
    """車体矩形 (length, width, rear_offset) を後軸中心の車体座標で cell/2 間隔に標本化 (M, 2)。"""
    L, W, back = (float(v) for v in footprint)
    if L <= 0 or W <= 0 or back < 0 or back > L:
        raise ValueError("car_hybrid_astar: footprint must be (length > 0, width > 0, 0 <= rear_offset <= length)")
    h = 0.5 * cell
    xs = np.arange(-back, L - back + 1e-9, h)
    ys = np.arange(-0.5 * W, 0.5 * W + 1e-9, h)
    xs = np.append(xs, L - back) if xs[-1] < L - back - 1e-9 else xs
    ys = np.append(ys, 0.5 * W) if ys[-1] < 0.5 * W - 1e-9 else ys
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    return np.column_stack([X.ravel(), Y.ravel()])


class _Collision:
    """占有格子 + 余白 + 車体で「姿勢の列が衝突するか」を答える。"""

    def __init__(self, occ: np.ndarray, cell: float, clearance: float, footprint):
        self.occ = occ
        self.cell = cell
        self.H, self.W = occ.shape
        if clearance > 0:
            free_dist = ndimage.distance_transform_edt(~occ) * cell
            self.forbidden = occ | (free_dist < clearance)
        else:
            self.forbidden = occ
        self.fp = _footprint_points(footprint, cell) if footprint is not None else None
        self.flat = np.ascontiguousarray(self.forbidden).ravel()
        self.inv = 1.0 / cell
        self.xmax, self.ymax = self.W * cell, self.H * cell

    def blocked(self, poses: np.ndarray) -> bool:
        """poses (N, 3)。格子の外は衝突とみなす(車体の一部が外に出るのも衝突)。"""
        poses = np.atleast_2d(poses)
        if self.fp is None:
            px, py = poses[:, 0], poses[:, 1]
        else:
            c = np.cos(poses[:, 2])[:, None]
            s = np.sin(poses[:, 2])[:, None]
            px = (poses[:, 0:1] + self.fp[:, 0] * c - self.fp[:, 1] * s).ravel()
            py = (poses[:, 1:2] + self.fp[:, 0] * s + self.fp[:, 1] * c).ravel()
        if px.min() < 0.0 or py.min() < 0.0 or px.max() >= self.xmax or py.max() >= self.ymax:
            return True
        ix = (px * self.inv).astype(np.intp)
        iy = (py * self.inv).astype(np.intp)
        return bool(self.flat[iy * self.W + ix].any())


def car_hybrid_astar(occupancy, poses, radius=1.0, cell=1.0, step=None, n_theta=72, allow_reverse=True,
                     footprint=None, clearance=0.0, reverse_penalty=0.0, switch_penalty=0.0,
                     steer_penalty=0.0, shot_every=None, max_expansions=200000, return_tree=False):
    """Hybrid A* (Dolgov, Thrun, Montemerlo and Diebel 2010): a car's path through an occupancy grid.

    ``occupancy`` is a 2-D grid (``> 0.5`` = obstacle); cell ``(row, col)`` covers metres
    ``x in [col*cell, (col+1)*cell)``, ``y in [row*cell, (row+1)*cell)``. ``poses`` is
    ``[[x, y, theta], [x', y', theta']]`` (start, goal) in metres/radians. The car has minimum turning
    radius ``radius``; ``footprint=(length, width, rear_offset)`` is a rectangle in rear-axle coordinates
    (``None`` = point car with ``clearance`` metres kept from obstacles). Motion primitives are
    {left, straight, right} × {forward, reverse if ``allow_reverse``} arcs of ``step`` metres (default
    ``1.01·sqrt(2)·cell``, so each primitive leaves its cell); states are pruned per discrete cell
    ``(col, row, theta bin of 2π/n_theta)``. Cost = path length + ``reverse_penalty``·(reversed length)
    + ``switch_penalty`` per gear change + ``steer_penalty`` per steering change (all default 0, so the
    cost is the geometric length). The heuristic is the obstacle-free Reeds–Shepp length (Dubins when
    reversing is disallowed), admissible because every penalty is non-negative. At the start node, and then
    every ``shot_every`` expansions (default ``None`` = adaptive: a node with cost-to-go ``h`` tries when the
    expansion count is a multiple of ``ceil(h / step)``, so nodes near the goal try every time, as in the
    paper), the shortest analytic path from the node to the goal is collision-checked, and the search ends
    when that shot is free. On an obstacle-free grid the first shot succeeds and the result equals the
    Reeds–Shepp (Dubins) length exactly; with obstacles the result is never below it (``lower_bound``).
    Cell pruning makes Hybrid A* an approximation of the optimum among all feasible paths, as in the paper.

    Returns ``points`` ``(N, 3)`` poses along the path (start, tree part, analytic shot to the goal),
    ``length`` (metres), ``cost``, ``lower_bound`` (Reeds–Shepp/Dubins length start→goal),
    ``segments`` ``[(kind, gear, length)]`` of the whole path, ``n_expanded``, ``n_generated``,
    ``closed_by_shot`` (``True`` when the analytic expansion ended the search; ``False`` when the goal cell
    itself was popped), ``shot_from`` (pose where the shot started), ``tree`` (``(K, 3)`` expanded poses,
    only when ``return_tree``).

    **Raises** ``ValueError``: grid not 2-D or empty; poses not ``(2, 3)`` finite, outside the grid or in
    collision; ``radius``/``cell``/``step`` not positive, ``n_theta < 4``, negative penalties; the goal is
    unreachable (open set exhausted) or ``max_expansions`` was hit (reported, never a partial path).
    """
    op = "car_hybrid_astar"
    occ = np.asarray(occupancy)
    if occ.ndim != 2 or occ.size == 0:
        raise ValueError("%s: occupancy must be a non-empty 2-D grid, got shape %s" % (op, occ.shape))
    if occ.dtype != bool:
        if not np.all(np.isfinite(occ)):
            raise ValueError("%s: occupancy must be finite" % op)
        occ = occ > 0.5
    start, goal = _poses(poses, op)
    rho = _positive(radius, "radius", op)
    cell = _positive(cell, "cell", op)
    step = _positive(step, "step", op) if step is not None else 1.01 * math.sqrt(2.0) * cell
    n_theta = int(n_theta)
    if n_theta < 4:
        raise ValueError("%s: n_theta must be >= 4, got %d" % (op, n_theta))
    for name, v in (("reverse_penalty", reverse_penalty), ("switch_penalty", switch_penalty),
                    ("steer_penalty", steer_penalty), ("clearance", clearance)):
        if not (np.isfinite(v) and float(v) >= 0):
            raise ValueError("%s: %s must be a non-negative finite number, got %r" % (op, name, v))
    shot_every = None if shot_every is None else max(1, int(shot_every))
    coll = _Collision(occ, cell, float(clearance), footprint)
    if coll.blocked(np.array([start])):
        raise ValueError("%s: start pose is outside the grid or in collision" % op)
    if coll.blocked(np.array([goal])):
        raise ValueError("%s: goal pose is outside the grid or in collision" % op)

    analytic = _reeds_shepp if allow_reverse else _dubins
    dtheta = _TWO_PI / n_theta

    def key(p):
        return (int(math.floor(p[0] / cell)), int(math.floor(p[1] / cell)), int(_mod2pi(p[2]) / dtheta) % n_theta)

    def heuristic(p):
        ok, _ = analytic(p, goal, rho)
        return ok[0][0] * rho if ok else math.inf

    def shot_cost(word, lens, prev_gear, prev_steer):
        """解析的な一撃の費用(同じ費用モデル)。(length, cost, gear_last, steer_last)。"""
        length = cost = 0.0
        g, st = prev_gear, prev_steer
        for k, l in zip(word, lens):
            if abs(l) < 1e-12:
                continue
            seg = abs(l) * rho
            gear = 1 if l > 0 else -1
            steer = {"L": 1, "S": 0, "R": -1}[k]
            length += seg
            cost += seg + (reverse_penalty * seg if gear < 0 else 0.0)
            if g is not None and gear != g:
                cost += switch_penalty
            if st is not None and steer != st:
                cost += steer_penalty
            g, st = gear, steer
        return length, cost

    # 運動基本形: (kind, gear)
    prims = [("L", 1), ("S", 1), ("R", 1)]
    if allow_reverse:
        prims += [("L", -1), ("S", -1), ("R", -1)]
    n_sub = max(2, int(math.ceil(step / (0.5 * cell))))
    lower_bound = heuristic(start)
    if not np.isfinite(lower_bound):
        raise ValueError("%s: no analytic path between start and goal" % op)

    # 節点: id → (pose, g, parent_id, kind, gear, seg_length)
    nodes = [(start, 0.0, -1, None, None, 0.0)]
    best_g = {key(start): 0.0}
    closed = set()
    counter = 0
    heap = [(lower_bound, counter, 0)]
    h_of = {0: lower_bound}
    n_expanded = n_generated = 0
    goal_key = key(goal)
    final = None  # (node_id, shot_word, shot_lens)

    while heap:
        f, _, nid = heapq.heappop(heap)
        pose, g, parent, kind, gear, _seg = nodes[nid]
        k0 = key(pose)
        if k0 in closed:
            continue
        closed.add(k0)
        n_expanded += 1
        if n_expanded > max_expansions:
            raise ValueError("%s: exceeded max_expansions=%d without reaching the goal" % (op, max_expansions))
        # 解析的な一撃(最短候補だけ。目標に近いほど頻繫に)
        h_node = h_of.pop(nid, 0.0)
        every = shot_every if shot_every is not None else max(1, int(math.ceil(h_node / step)))
        if n_expanded == 1 or (n_expanded - 1) % every == 0:
            ok, _ = analytic(pose, goal, rho)
            if ok:
                _L, w, l = ok[0]
                if not coll.blocked(_sample(w, l, pose, rho, 0.5 * cell)):
                    final = (nid, w, l)
                    break
        if k0 == goal_key:
            # 目標セルに来た(一撃で正確な姿勢へ寄せる)
            ok, _ = analytic(pose, goal, rho)
            for _L, w, l in ok:
                pts = _sample(w, l, pose, rho, 0.5 * cell)
                if not coll.blocked(pts):
                    final = (nid, w, l)
                    break
            if final is not None:
                break
        prev_steer = {"L": 1, "S": 0, "R": -1}[kind] if kind else None
        for k, gr in prims:
            l_units = gr * step / rho
            # 部分点で衝突検査
            sub = np.empty((n_sub, 3))
            for i in range(1, n_sub + 1):
                sub[i - 1] = _step_segment(pose[0] / rho, pose[1] / rho, pose[2], k, l_units * i / n_sub)
            sub[:, :2] *= rho
            if coll.blocked(sub):
                continue
            child = (float(sub[-1, 0]), float(sub[-1, 1]), float(_wrap(sub[-1, 2])))
            kc = key(child)
            if kc in closed:
                continue
            steer = {"L": 1, "S": 0, "R": -1}[k]
            gc = g + step + (reverse_penalty * step if gr < 0 else 0.0)
            if gear is not None and gr != gear:
                gc += switch_penalty
            if prev_steer is not None and steer != prev_steer:
                gc += steer_penalty
            if kc in best_g and best_g[kc] <= gc:
                continue
            best_g[kc] = gc
            nodes.append((child, gc, nid, k, gr, step))
            n_generated += 1
            h = heuristic(child)
            counter += 1
            h_of[len(nodes) - 1] = h
            heapq.heappush(heap, (gc + h, counter, len(nodes) - 1))

    if final is None:
        raise ValueError("%s: goal unreachable (open set exhausted after %d expansions)" % (op, n_expanded))

    nid, w, l = final
    # 木の部分を復元
    chain = []
    cur = nid
    while cur >= 0:
        chain.append(cur)
        cur = nodes[cur][2]
    chain.reverse()
    pts = [np.array([start])]
    segments = []
    g_tree = nodes[nid][1]
    for cid in chain[1:]:
        pose_c, _g, pid, k, gr, seg = nodes[cid]
        pp = nodes[pid][0]
        seg_pts = _sample(k, (gr * seg / rho,), pp, rho, 0.5 * cell)
        pts.append(seg_pts[1:])
        segments.append((k, gr, seg))
    last_gear = nodes[nid][4]
    last_steer = {"L": 1, "S": 0, "R": -1}[nodes[nid][3]] if nodes[nid][3] else None
    shot_len, shot_c = shot_cost(w, l, last_gear, last_steer)
    shot_pts = _sample(w, l, nodes[nid][0], rho, 0.5 * cell)
    pts.append(shot_pts[1:])
    segments += _segments(w, l, rho)
    points = np.vstack(pts)
    points[-1] = goal  # 一撃は目標へ厳密に着く(積分の丸めを消す)
    out = {
        "points": points,
        "length": float(sum(s[2] for s in segments)),
        "cost": float(g_tree + shot_c),
        "lower_bound": float(lower_bound),
        "segments": segments,
        "n_expanded": int(n_expanded),
        "n_generated": int(n_generated),
        "closed_by_shot": bool(key(nodes[nid][0]) != goal_key),
        "shot_from": tuple(float(v) for v in nodes[nid][0]),
    }
    if return_tree:
        out["tree"] = np.asarray([n[0] for n in nodes], float)
    return out
