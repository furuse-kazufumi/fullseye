# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""車の縦の運動(慣性・坂・転がり抵抗・空気抵抗・ブレーキの保持)と、停止線の手前に止まる計画・坂道発進・技能試験の減点。

## 何を作るか

これまでの教習所(PoC ⑯ 以降)は 2.5 m おきの姿勢の列で、停止線で **瞬時に** 止まっていた(時間も速度も無い)。
ここでは道なりの距離 s(路面に沿った弧長)の 1 次元の運動方程式を持つ:

    dv/dt = a_d − g sin θ(s) − sgn(v)·(a_b + c_rr g cos θ(s)) − k v|v|,   k = ρ_air C_d A / (2 m)

(単位質量あたりの力 = 加速度 [m/s²]。a_d = 駆動、a_b = 制動の大きさ、どちらも ≥ 0。ブレーキと転がり抵抗は **動きに逆らう**
クーロン摩擦として扱う)。止まっている間(v = 0)は静止摩擦: |a_d − g sin θ| ≤ a_b + c_rr g cos θ なら v = 0 のまま、
超えたらその向きへ動き出す。制動・駆動の上限は ``min(a_max, μ g cos θ)``(μ = 路面とタイヤの摩擦係数。次の巡で雨の路面が
ここに入る)。

## 真値(門)にする閉形式

1. **停止距離** ``stopping_distance_grade``: d = v ρ + (1/(2k)) ln(1 + k v² / A)、A = a_b + g sin θ + c_rr g cos θ
   (k → 0 で v²/(2A)。上り +、下り −)。ρ の間は速さを保つ(空走 = 足をアクセルからブレーキへ移す間)。平地・c_rr = k = 0 では
   ``rsssafety.rss_stopping_distance(v, ρ, accel=0, brake=a_b)`` と一致(第 2 実装)。
2. **坂で止まっていられる最小の制動** ``hill_hold_brake_min`` = max(0, |a_creep − g sin θ| − c_rr g cos θ)。
3. **坂道発進のずり下がり** ``hill_start_rollback``: ブレーキを離してから駆動 a_d が立ち上がるまで τ の間、下向きの加速度
   a₁ = g sin θ − c_rr g cos θ − a_creep でずり下がり(½ a₁ τ²)、駆動が入ってから減速 a₂ = a_d − g sin θ + c_rr g cos θ で
   止まるまでに (a₁ τ)² / (2 a₂) —— 合計が逆行の距離(空気抵抗は無視 = k = 0 の閉形式)。
4. **エネルギーの収支**: ½ v² + g z(s) = ½ v₀² + g z₀ + W_drive − W_brake − W_rr − W_drag(各仕事は積分器が別の状態として
   積む。仕事の式は運動方程式から独立には出てこないので、恒等式が成り立つことは「重力の項 g sin θ と高さ z(s) が同じ坂を表す」
   「クーロン項の符号が正しい」ことの検査になる)。

## 積分器

RK4(固定刻み dt)。**等加速度の区間では RK4 は厳密**(解が t の 2 次式)なので、停止距離の門は 1e-9 で比べられる。
次の所では刻みを **事象の時刻に合わせて切る**(二分法で 2⁻⁶⁰ まで): 速度が 0 を横切る(クーロン項の向きが変わる)、
坂の折れ点(sin θ が不連続)、指令の切り替え時刻(``t_breaks``)、止まっている車が動き出す時刻。空気抵抗がある区間は
厳密でない(誤差は dt⁴ の桁で、門は測った値を出す)。

## 仮定(出典のあるものは出典つき。無いものは「仮定」と明記)

* 質量 1300 kg(小型乗用車の車両重量の典型、仮定)、転がり抵抗係数 c_rr = 0.012(乗用車タイヤ・舗装路の文献値 0.010〜0.015、
  Wong "Theory of Ground Vehicles"・Gillespie "Fundamentals of Vehicle Dynamics" の表の範囲。仮定)、
  C_d A = 0.65 m²(C_d ≈ 0.30 × 前面投影面積 ≈ 2.2 m²、仮定)、空気密度 1.2 kg/m³(国際標準大気の海面 1.225 を丸めた)。
* 反応時間 0.75 s(教習の教本で空走距離の説明に使われる値 —— 二次情報、要確認)。駆動の上限 3.0 m/s²、制動の上限 6.0 m/s²
  (乗用車の常用の強いブレーキ、仮定)。路面の摩擦係数 μ = 0.8(乾いた舗装の文献値 0.7〜0.8、湿潤 0.4〜0.6 —— 要確認)。
* AT のクリープの駆動 0.3 m/s²(仮定・出典なし。平地でブレーキを離すとゆっくり進む程度)。
* 重力加速度 g = 9.80665 m/s²(標準重力、CGPM 1901)。

## 技能試験の採点(``skill_test_score``)

一次情報 = 警察庁「運転免許技能試験に係る採点基準の運用の標準について」(丙運発第 12 号 令和 4 年 3 月 4 日)の減点細目:
停止位置不適 5 / 5(路上 / 場内。「停止したが、停止線の直前で停止しない場合」)、逆行小 10 / 10(「進行しようとする方向に対して
逆行した場合」)、逆行中 20 / 20(「著しく逆行した場合」)、逆行大 = 危(試験中止)、発進手間どり 10 / 5、制動操作不良 5 / 5
(「ブレーキを数回に分けて踏まない場合」)、制動操作不良(クリープ)10 / 5、信号無視 = 試験中止の項目。合格は第一種 70 点以上
(同 第 10)。**通達に距離・時間の数字は無い** —— 逆行 0.3 / 0.5 / 1 m・停止線の手前 2 m は教習所サイト等の二次情報(要確認)、
発進手間どりの 3 s と信号無視とみなす越え幅は **仮定**(出典なし)。

## 限界(self_reported)

* 1 次元(道なり)。横の運動・タイヤの滑り(ABS)・荷重移動・エンジンブレーキ・変速は持たない。
* 停止線の計画は **前向き(フィードフォワード)**: 知覚した瞬間の (s, v) から閉形式で段の時刻を決め、途中で測り直さない。
  モデルと世界が同じなのでぴったり止まる。世界との食い違い(μ の読み違い等)に対する頑健さはこの巡では測らない。
* クリープは保持(hold)の間だけ入れる(制動の段の間は入れない)。
"""
from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

__all__ = [
    "G", "long_params", "road_profile", "road_eval", "long_simulate", "long_energy_residual",
    "stopping_distance_grade", "stop_line_plan", "plan_command",
    "hill_hold_brake_min", "hill_start_rollback", "hill_start_command",
    "skill_test_thresholds", "skill_test_score",
]

G = 9.80665                                          # 標準重力 [m/s²](CGPM 1901)


# ---- 引数検査(fail-closed) ------------------------------------------------------------------------
def _finite(v, name: str, op: str) -> float:
    try:
        v = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a real number, got %r" % (op, name, v)) from None
    if not math.isfinite(v):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, v))
    return v


def _positive(v, name: str, op: str) -> float:
    v = _finite(v, name, op)
    if v <= 0:
        raise ValueError("%s: %s must be > 0, got %r" % (op, name, v))
    return v


def _nonneg(v, name: str, op: str) -> float:
    v = _finite(v, name, op)
    if v < 0:
        raise ValueError("%s: %s must be >= 0, got %r" % (op, name, v))
    return v


def _check_theta(theta, op: str) -> float:
    th = _finite(theta, "theta", op)
    if abs(th) >= math.pi / 4:
        raise ValueError("%s: |theta| must be < 45 deg (a road, not a wall), got %r rad" % (op, theta))
    return th


# ---- パラメータ -----------------------------------------------------------------------------------
def long_params(mass: float = 1300.0, c_rr: float = 0.012, cda: float = 0.65, rho_air: float = 1.2,
                a_drive_max: float = 3.0, a_brake_max: float = 6.0, reaction: float = 0.75, mu: float = 0.8,
                a_creep: float = 0.3, g: float = G) -> Dict[str, float]:
    """縦の運動のパラメータ(既定値はすべて **仮定**。出典はモジュールの docstring)。

    Parameters
    ----------
    mass : 車両質量 [kg](> 0)。空気抵抗の係数 k = ρ_air C_d A / (2 m) にだけ効く。
    c_rr : 転がり抵抗係数(≥ 0、文献値 0.010〜0.015)
    cda : C_d × 前面投影面積 [m²](≥ 0。0 で空気抵抗なし)
    rho_air : 空気密度 [kg/m³](≥ 0)
    a_drive_max, a_brake_max : 駆動・制動の上限 [m/s²](> 0)。実際の上限はさらに μ g cos θ で頭打ち。
    reaction : 反応時間(空走)[s](≥ 0)
    mu : 路面とタイヤの摩擦係数(> 0。乾燥 0.7〜0.8・湿潤 0.4〜0.6 —— 要確認)
    a_creep : AT のクリープの駆動 [m/s²](≥ 0。保持の間だけ)
    g : 重力加速度 [m/s²](> 0)

    Returns
    -------
    dict : 引数と同じキー + ``k``(空気抵抗の係数 [1/m])。

    **Raises** ``ValueError``: 非有限・範囲外。"""
    op = "long_params"
    p = {"mass": _positive(mass, "mass", op), "c_rr": _nonneg(c_rr, "c_rr", op), "cda": _nonneg(cda, "cda", op),
         "rho_air": _nonneg(rho_air, "rho_air", op), "a_drive_max": _positive(a_drive_max, "a_drive_max", op),
         "a_brake_max": _positive(a_brake_max, "a_brake_max", op), "reaction": _nonneg(reaction, "reaction", op),
         "mu": _positive(mu, "mu", op), "a_creep": _nonneg(a_creep, "a_creep", op), "g": _positive(g, "g", op)}
    if p["c_rr"] >= 1.0:
        raise ValueError("%s: c_rr must be < 1, got %r" % (op, c_rr))
    p["k"] = p["rho_air"] * p["cda"] / (2.0 * p["mass"])
    return p


def _params(p, op: str) -> Dict[str, float]:
    if p is None:
        return long_params()
    if not isinstance(p, dict):
        raise ValueError("%s: params must be a dict from long_params()" % op)
    keys = ("mass", "c_rr", "cda", "rho_air", "a_drive_max", "a_brake_max", "reaction", "mu", "a_creep", "g")
    missing = [k for k in keys if k not in p]
    if missing:
        raise ValueError("%s: params missing %s (use long_params())" % (op, missing))
    return long_params(**{k: p[k] for k in keys})


# ---- 道の縦断(坂) ---------------------------------------------------------------------------------
def road_profile(profile_xz, l0: float = 0.0) -> Dict[str, np.ndarray]:
    """水平距離と高さの折線 (x, z)(drivecourse.course_slope の ``profile`` と同じ形)を、**路面に沿った弧長 l** の縦断にする。

    返り値 = ``{"l" (n,), "x" (n,), "z" (n,), "sin" (n−1,), "cos" (n−1,)}``。l は ``l0`` から始まる折れ点の弧長。
    区間 i の勾配角 θ_i は sin = Δz/Δl、cos = Δx/Δl(両端の外は平ら: θ = 0、z は端の値)。

    **Raises** ``ValueError``: 2 点未満、非有限、x が狭義単調増加でない、勾配が 45° 以上。"""
    op = "road_profile"
    P = np.asarray(profile_xz, np.float64)
    if P.ndim != 2 or P.shape[1] != 2 or len(P) < 2:
        raise ValueError("%s: profile must be (n>=2, 2) of (x, z)" % op)
    if not np.all(np.isfinite(P)):
        raise ValueError("%s: profile must be finite" % op)
    dx, dz = np.diff(P[:, 0]), np.diff(P[:, 1])
    if np.any(dx <= 0):
        raise ValueError("%s: x must be strictly increasing" % op)
    if np.any(np.abs(dz) >= dx):
        raise ValueError("%s: grade must be < 45 deg" % op)
    dl = np.hypot(dx, dz)
    l = _finite(l0, "l0", op) + np.r_[0.0, np.cumsum(dl)]
    return {"l": l, "x": P[:, 0].copy(), "z": P[:, 1].copy(), "sin": dz / dl, "cos": dx / dl}


def road_eval(road, l: float) -> Tuple[float, float, float]:
    """道の縦断を弧長 l で引く: (z, sin θ, cos θ)。``road`` = None(平ら)/ 数値(一定の勾配角 θ [rad]、z = l sin θ)/
    :func:`road_profile` の dict。折れ点の上ではその先の区間の値(右連続)。"""
    if road is None:
        return 0.0, 0.0, 1.0
    if not isinstance(road, dict):
        th = float(road)
        return l * math.sin(th), math.sin(th), math.cos(th)
    L = road["l"]
    if l < L[0]:
        return float(road["z"][0]), 0.0, 1.0
    if l >= L[-1]:
        return float(road["z"][-1]), 0.0, 1.0
    i = int(np.searchsorted(L, l, side="right")) - 1
    return float(road["z"][i] + (l - L[i]) * road["sin"][i]), float(road["sin"][i]), float(road["cos"][i])


def _road_breaks(road) -> np.ndarray:
    if isinstance(road, dict):
        return np.asarray(road["l"], np.float64)
    return np.zeros(0)


# ---- 積分器 ---------------------------------------------------------------------------------------
def _caps(p, cs: float) -> Tuple[float, float]:
    """駆動・制動の上限(μ g cos θ で頭打ち)。"""
    fr = p["mu"] * p["g"] * cs
    return min(p["a_drive_max"], fr), min(p["a_brake_max"], fr)


def _command(command, t, s, v, p, cs, op):
    out = command(t, s, v)
    try:
        dr, br = float(out[0]), float(out[1])
    except (TypeError, ValueError, IndexError):
        raise ValueError("%s: command must return (drive, brake)" % op) from None
    if not (math.isfinite(dr) and math.isfinite(br)) or dr < 0 or br < 0:
        raise ValueError("%s: command returned invalid (drive, brake) = (%r, %r); both must be finite and >= 0" % (op, dr, br))
    cd, cb = _caps(p, cs)
    return min(dr, cd), min(br, cb), (dr > cd + 1e-12) or (br > cb + 1e-12)


def long_simulate(s0: float, v0: float, command: Callable, road=None, t_end: float = 30.0, dt: float = 0.01,
                  params: Optional[dict] = None, t_breaks: Sequence[float] = (), t0: float = 0.0) -> Dict[str, object]:
    """縦の運動方程式を RK4 で積分する(事象の時刻で刻みを切る。モジュールの docstring)。

    Parameters
    ----------
    s0, v0 : 初めの位置 [m](道なりの弧長)と速度 [m/s](負 = 後ろ向き)
    command : ``command(t, s, v) -> (drive, brake)``(どちらも ≥ 0 [m/s²]。上限は μ g cos θ と a_max で頭打ち)。
              **v = 0.0 で呼ばれるのは止まっている間だけ**(動いている刻みの中間点で速度が 0 を横切っても、指令には動きの向きの
              ±1e-300 を渡す)ので、指令は ``v == 0`` / ``v <= 0`` で「止まったら保持」を書いてよい。
              指令が時刻で不連続に変わるなら、その時刻を ``t_breaks`` に入れると刻みがそこで切れる(厳密さのため)。
    road : 道の縦断(:func:`road_eval` と同じ)
    t_end : 終わりの時刻 [s]、dt : 刻み [s]
    params : :func:`long_params` の dict(None = 既定)
    t0 : 初めの時刻 [s]

    Returns
    -------
    dict : ``t, s, v, a, drive, brake, z, W_drive, W_brake, W_rr, W_drag``(各 (n,) の配列、a = その時点の加速度)、
    ``stopped``(bool 配列)、``events``(``("stop"|"move", t, s, 向き)`` の列)、``saturated``(上限で頭打ちになった刻みがあったか)、
    ``params``。

    **Raises** ``ValueError``: 引数が不正、指令が負や非有限を返した。"""
    op = "long_simulate"
    p = _params(params, op)
    s0 = _finite(s0, "s0", op)
    v0 = _finite(v0, "v0", op)
    t0 = _finite(t0, "t0", op)
    t_end = _finite(t_end, "t_end", op)
    if t_end <= t0:
        raise ValueError("%s: t_end must be > t0" % op)
    dt = _positive(dt, "dt", op)
    if not callable(command):
        raise ValueError("%s: command must be callable" % op)
    if road is not None and not isinstance(road, dict):
        _check_theta(road, op)
    tb = np.unique(np.asarray([float(x) for x in t_breaks if t0 < float(x) < t_end], np.float64))
    lb = _road_breaks(road)
    g, crr, k = p["g"], p["c_rr"], p["k"]
    sat = [False]

    def forces(t, s, v, direction, grade=None):
        """(加速度, 駆動, 制動, 各仕事率)。direction = 動きの向き(クーロン項の符号)。grade = 刻みの間 固定の (sin, cos)
        (刻みは坂の折れ点をまたがないので、刻みの始めに「進む向きの区間」を引いておく —— 刻みの終わりがちょうど折れ点でも
        手前の区間の値を使う = 左極限)。"""
        if grade is None:
            _, sn, cs = road_eval(road, s + direction * 1e-9)
        else:
            sn, cs = grade
        # 動いている刻みの中間の評価点(RK4 の段・停止の事象の二分法)では、速度が一瞬 0 や逆向きになりうる。そこで指令が
        # 「止まった → 保持(クリープ)」に切り替わると、停止の時刻が dt に比例してずれた(実測: dt = 0.0002 で停止位置 1e-5 m)。
        # 指令には動きの向きの極小の速さを渡す —— v = 0.0 で呼ばれるのは本当に止まっている間だけ(契約)。
        v_cmd = v if direction * v > 0 else direction * 1e-300
        dr, br, st = _command(command, t, s, v_cmd, p, cs, op)
        if st:
            sat[0] = True
        a = dr - g * sn - direction * (br + crr * g * cs) - k * v * abs(v)
        av = abs(v)
        return a, dr, br, (dr * v, br * av, crr * g * cs * av, k * av * av * av)

    def deriv(t, y, direction, grade):
        a, _, _, w = forces(t, y[0], y[1], direction, grade)
        return np.array([y[1], a, w[0], w[1], w[2], w[3]])

    def rk4(t, y, h, direction):
        # 指令も区分的なので、刻みの終わりの評価は「終わりの直前」(左極限)。刻みの終わりが切り替え時刻でも、切り替え後の指令を
        # 手前の刻みに混ぜない(混ぜると停止距離が v·dt/6 ずれる —— 実測で 0.02 m、dt = 0.01・v = 12)。
        grade = road_eval(road, y[0] + direction * 1e-9)[1:]
        k1 = deriv(t, y, direction, grade)
        k2 = deriv(t + h / 2, y + h / 2 * k1, direction, grade)
        k3 = deriv(t + h / 2, y + h / 2 * k2, direction, grade)
        # 「直前」は 1 ulp 手前(nextafter)。最初の版は t + h(1 − 1e-12) で、h が小さいと h·1e-12 が t の ulp を下回って
        # 切り替え時刻そのものに丸まり、切り替え後の指令が混ざった(実測: dt = 0.005 で停止位置 3.9e-5 m)
        t_end_step = t + h
        j = int(np.searchsorted(tb, t_end_step - 1e-9)) if len(tb) else 0
        if len(tb) and j < len(tb) and abs(tb[j] - t_end_step) < 1e-9:
            t_end_step = float(tb[j])                                       # 刻みの終わり = 切り替え時刻(丸めでずれていても)
        k4 = deriv(float(np.nextafter(t_end_step, -np.inf)), y + h * k3, direction, grade)
        return y + h / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)

    def breakaway(t, s):
        """止まっている車に働く (G, R): G = 駆動 − 重力の坂成分、R = 静止摩擦の上限(制動 + 転がり)。"""
        z, sn, cs = road_eval(road, s)
        dr, br, _ = _command(command, t, s, 0.0, p, cs, op)
        return dr - g * sn, br + crr * g * cs

    y = np.array([s0, v0, 0.0, 0.0, 0.0, 0.0])
    t = t0
    stopped = v0 == 0.0
    direction = 0.0 if stopped else math.copysign(1.0, v0)
    rec = {k_: [] for k_ in ("t", "s", "v", "a", "drive", "brake", "z", "W_drive", "W_brake", "W_rr", "W_drag", "stopped")}
    events: List[Tuple[str, float, float, float]] = []

    def record():
        if stopped:
            Gv, R = breakaway(t, y[0])
            z, sn, cs = road_eval(road, y[0])
            dr, br, _ = _command(command, t, y[0], 0.0, p, cs, op)
            a = 0.0
        else:
            a, dr, br, _ = forces(t, y[0], y[1], direction)
            z = road_eval(road, y[0])[0]
        for key, val in (("t", t), ("s", y[0]), ("v", y[1]), ("a", a), ("drive", dr), ("brake", br), ("z", z),
                         ("W_drive", y[2]), ("W_brake", y[3]), ("W_rr", y[4]), ("W_drag", y[5]), ("stopped", stopped)):
            rec[key].append(val)

    record()
    guard = 0
    max_iter = int(4 * (t_end - t0) / dt) + 10 * (len(tb) + len(lb)) + 10000
    while t < t_end - 1e-12:
        guard += 1
        if guard > max_iter:
            raise RuntimeError("%s: too many steps (event chattering?)" % op)
        if len(tb):                                                       # 切り替え時刻の極く近くなら、ぴったりそこへそろえる
            j = int(np.argmin(np.abs(tb - t)))
            if abs(tb[j] - t) < 1e-9:
                t = float(tb[j])
        nb = tb[tb > t]
        h = min(dt, t_end - t, (nb[0] - t) if len(nb) else np.inf)
        if stopped:
            Gv, R = breakaway(t, y[0])
            if abs(Gv) > R:                                               # 静止摩擦を超えた → 動き出す(刻みは使わない)
                stopped = False
                direction = math.copysign(1.0, Gv)
                events.append(("move", t, float(y[0]), direction))
                continue
            G1, R1 = breakaway(t + h, y[0])
            if abs(G1) <= R1:
                t += h
                record()
                continue
            lo, hi = 0.0, h                                               # 動き出す時刻を二分法で
            for _ in range(60):
                mid = 0.5 * (lo + hi)
                Gm, Rm = breakaway(t + mid, y[0])
                if abs(Gm) > Rm:
                    hi = mid
                else:
                    lo = mid
            t += hi
            record()
            continue
        y1 = rk4(t, y, h, direction)
        # 事象: 速度の符号が変わる / 坂の折れ点を横切る → その手前まで刻みを縮める
        h_ev, kind = h, None
        if direction * y1[1] <= 0.0:
            lo, hi = 0.0, h
            for _ in range(60):
                mid = 0.5 * (lo + hi)
                if direction * rk4(t, y, mid, direction)[1] > 0.0:
                    lo = mid
                else:
                    hi = mid
            h_ev, kind = hi, "stop"
        if len(lb):
            a0, a1 = sorted((y[0], y1[0]))
            cross = lb[(lb > a0 + 1e-12) & (lb < a1 - 1e-12)]
            if len(cross):
                target = cross[0] if direction > 0 else cross[-1]
                lo, hi = 0.0, h
                for _ in range(60):
                    mid = 0.5 * (lo + hi)
                    if direction * (rk4(t, y, mid, direction)[0] - target) < 0.0:
                        lo = mid
                    else:
                        hi = mid
                if hi < h_ev:
                    h_ev, kind = hi, "break"
        if kind is None:
            y, t = y1, t + h
        else:
            y, t = rk4(t, y, h_ev, direction), t + h_ev
            if kind == "stop":
                y[1] = 0.0
                stopped = True
                events.append(("stop", t, float(y[0]), direction))
            else:
                y[0] = float(target)                                         # 折れ点の上にそろえる(二分法の残り 2⁻⁶⁰ h)
        record()
    out = {k_: np.asarray(v_) for k_, v_ in rec.items()}
    out["events"] = events
    out["saturated"] = sat[0]
    out["params"] = p
    return out


def long_energy_residual(res: dict, v0: Optional[float] = None) -> np.ndarray:
    """エネルギー収支の残差(単位質量あたり [J/kg]): (½ v² + g z) − (½ v₀² + g z₀ + W_drive − W_brake − W_rr − W_drag)。"""
    g = res["params"]["g"]
    v, z = res["v"], res["z"]
    E = 0.5 * v * v + g * z
    E0 = E[0]
    return E - (E0 + res["W_drive"] - res["W_brake"] - res["W_rr"] - res["W_drag"])


# ---- 閉形式 ---------------------------------------------------------------------------------------
def _net(A_brake: float, sn: float, cs: float, p) -> float:
    """制動 b のときの定数部分の減速度 A = b + g sin θ + c_rr g cos θ(前向きに走っているとき)。"""
    return A_brake + p["g"] * sn + p["c_rr"] * p["g"] * cs


def _decel_dist(va: float, vb: float, A: float, k: float) -> float:
    """dv/dt = −(A + k v²) で va → vb(0 ≤ vb ≤ va)の間に進む距離。"""
    if va <= vb:
        return 0.0
    if A <= 0 and vb <= 0 and k <= 0:
        return math.inf
    if k <= 0:
        return (va * va - vb * vb) / (2.0 * A)
    if A <= 0:
        if vb <= 0:
            return math.inf
        return math.log(va / vb) / k if A == 0 else math.inf
    return (math.log1p(k * va * va / A) - math.log1p(k * vb * vb / A)) / (2.0 * k)


def _decel_time(va: float, vb: float, A: float, k: float) -> float:
    """dv/dt = −(A + k v²) で va → vb にかかる時間(A > 0)。"""
    if va <= vb:
        return 0.0
    if k <= 0:
        return (va - vb) / A
    r = math.sqrt(k / A)
    return (math.atan(va * r) - math.atan(vb * r)) / math.sqrt(A * k)


def stopping_distance_grade(v: float, reaction: float, brake: float, theta: float = 0.0, c_rr: float = 0.0,
                            k: float = 0.0, g: float = G) -> float:
    """停止距離の閉形式 = 空走 v ρ + 制動距離 (1/(2k)) ln(1 + k v²/A)、A = brake + g sin θ + c_rr g cos θ(k = 0 で v²/(2A))。

    θ > 0 が上り(止まりやすい)、θ < 0 が下り。ρ の間は速さを保つ。A ≤ 0(下りで制動が坂に負ける)なら止まらない → ``inf``。
    平地・c_rr = k = 0 で ``rsssafety.rss_stopping_distance(v, ρ, 0, brake)`` と同じ式。

    **Raises** ``ValueError``: v < 0、非有限、|θ| ≥ 45°。"""
    op = "stopping_distance_grade"
    v = _nonneg(v, "v", op)
    rho = _nonneg(reaction, "reaction", op)
    b = _nonneg(brake, "brake", op)
    th = _check_theta(theta, op)
    crr = _nonneg(c_rr, "c_rr", op)
    k = _nonneg(k, "k", op)
    g = _positive(g, "g", op)
    A = b + g * math.sin(th) + crr * g * math.cos(th)
    if v == 0.0:
        return 0.0
    if A <= 0.0:
        return math.inf
    if k == 0.0:
        return v * rho + v * v / (2.0 * A)
    return v * rho + math.log1p(k * v * v / A) / (2.0 * k)


def stop_line_plan(v: float, dist_to_line: float, theta: float = 0.0, params: Optional[dict] = None, t0: float = 0.0,
                   margin: float = 0.5, A1: float = 1.5, A2: float = 2.5, split: float = 0.5) -> Dict[str, object]:
    """知覚した瞬間(時刻 t0、前端から停止線まで ``dist_to_line``、速さ v)から、停止線の ``margin`` 手前に止まる **2 段制動** の計画。

    段: 反応(ρ、速さを保つ)→ [必要なら速さを保ったまま待つ(cruise)] → 1 段目(減速度の定数部分 A1、速さが split·v まで)
    → 2 段目(A2、止まるまで)→ 保持。制動を 2 段に分けるのは通達の「ブレーキを数回に分けて踏まない場合」(制動操作不良)に合わせる。
    間に合わないときは 2 段目の減速度を閉形式で解き直し(ln の式、k > 0 でも厳密)、1 段目だけで足りない距離なら 1 段で止める
    (stages = 1)。上限(min(a_brake_max, μ g cos θ))で頭打ちなら ``saturated`` = True、予測は頭打ちの値で出す。
    坂は区間の中で一定の θ(停止の区間が坂の折れ点をまたがない)とする。

    Returns
    -------
    dict : ``phases``(``(t_start, kind, drive, brake)`` の列、kind = react / cruise / brake1 / brake2)、``t_breaks``、
    ``stages``、``predicted_gap``(止まった前端から停止線まで。負 = 越えた)、``t_stop``、``saturated``、``theta``、
    ``d_react``, ``d_cruise``, ``d_brake``。

    **Raises** ``ValueError``: v ≤ 0、非有限、split ∉ (0, 1)、A1・A2 ≤ 0。"""
    op = "stop_line_plan"
    p = _params(params, op)
    v = _positive(v, "v", op)
    D0 = _finite(dist_to_line, "dist_to_line", op)
    th = _check_theta(theta, op)
    t0 = _finite(t0, "t0", op)
    margin = _nonneg(margin, "margin", op)
    A1 = _positive(A1, "A1", op)
    A2 = _positive(A2, "A2", op)
    split = _finite(split, "split", op)
    if not 0.0 < split < 1.0:
        raise ValueError("%s: split must be in (0, 1)" % op)
    g, crr, k, rho = p["g"], p["c_rr"], p["k"], p["reaction"]
    sn, cs = math.sin(th), math.cos(th)
    _, bcap = _caps(p, cs)
    base = g * sn + crr * g * cs                                           # 制動 0 のときの減速度の定数部分
    A_cap = bcap + base
    # 上限を先に掛ける: 名目の段(A1, A2)が上限を越える路面(μ が小さい)で、名目の値のまま「待ち」を入れてから頭打ちに
    # すると、待った分だけ線を越える(最初の版はこれで μ* の上でも 1.85 m 越えた)
    saturated = A1 > A_cap or A2 > A_cap
    A1, A2 = min(A1, A_cap), min(A2, A_cap)
    d_react = v * rho
    D = D0 - margin - d_react                                              # 制動に使える距離
    v1 = split * v
    Db = _decel_dist(v, v1, A1, k) + _decel_dist(v1, 0.0, A2, k)
    stages, d_cruise = 2, 0.0
    if D >= Db:
        d_cruise = D - Db
        a1, a2 = A1, A2
    else:
        s1 = _decel_dist(v, v1, A1, k)
        if s1 < D:
            s2 = D - s1
            a1 = A1
            a2 = (k * v1 * v1 / math.expm1(2.0 * k * s2)) if k > 0 else v1 * v1 / (2.0 * s2)
        else:
            stages = 1
            a1 = None
            if D <= 0:
                a2 = math.inf
            else:
                a2 = (k * v * v / math.expm1(2.0 * k * D)) if k > 0 else v * v / (2.0 * D)
    if a1 is not None and a1 > A_cap:
        a1, saturated = A_cap, True
    if a2 > A_cap:
        a2, saturated = A_cap, True
    if A_cap <= 0 or a2 <= 0 or (a1 is not None and a1 <= 0):
        raise ValueError("%s: cannot decelerate on this grade (brake cap %.3g < downhill pull)" % (op, bcap))
    t_r = t0 + rho
    t_c = t_r + d_cruise / v
    phases = [(t0, "react", None, None)]
    if d_cruise > 0:
        phases.append((t_r, "cruise", None, None))
    if a1 is not None:
        t_1 = t_c + _decel_time(v, v1, a1, k)
        d_b = _decel_dist(v, v1, a1, k) + _decel_dist(v1, 0.0, a2, k)
        t_stop = t_1 + _decel_time(v1, 0.0, a2, k)
        phases += [(t_c, "brake1", max(0.0, -(a1 - base)), max(0.0, a1 - base)),
                   (t_1, "brake2", max(0.0, -(a2 - base)), max(0.0, a2 - base))]
    else:
        d_b = _decel_dist(v, 0.0, a2, k)
        t_stop = t_c + _decel_time(v, 0.0, a2, k)
        phases.append((t_c, "brake2", max(0.0, -(a2 - base)), max(0.0, a2 - base)))
    predicted_gap = D0 - (d_react + d_cruise + d_b)
    return {"phases": phases, "t_breaks": [ph[0] for ph in phases[1:]], "stages": stages, "predicted_gap": predicted_gap,
            "t_stop": t_stop, "saturated": saturated, "theta": th, "d_react": d_react, "d_cruise": d_cruise, "d_brake": d_b,
            "v": v, "t0": t0}


def plan_command(plan: dict, road=None, params: Optional[dict] = None, hold_brake: Optional[float] = None,
                 before: Optional[Callable] = None) -> Callable:
    """:func:`stop_line_plan` を ``command(t, s, v)`` にする。t0 より前は ``before``(None = 速さを保つ)、react / cruise は
    速さを保つ(駆動 = 坂 + 転がり + 空気抵抗の打ち消し、下りで負なら制動)、brake1 / brake2 は計画の値、止まったら保持
    (制動 ``hold_brake``(None = 上限)+ クリープの駆動)。"""
    p = _params(params, "plan_command")
    phases = plan["phases"]
    times = np.array([ph[0] for ph in phases])
    g, crr, k = p["g"], p["c_rr"], p["k"]

    def cruise(s, v):
        _, sn, cs = road_eval(road, s)
        need = g * sn + crr * g * cs * (1.0 if v >= 0 else -1.0) + k * v * abs(v)
        return (need, 0.0) if need >= 0 else (0.0, -need)

    def command(t, s, v):
        if t < plan["t0"]:
            return before(t, s, v) if before is not None else cruise(s, v)
        i = int(np.searchsorted(times, t, side="right")) - 1
        _, kind, dr, br = phases[i]
        if kind in ("react", "cruise"):
            return cruise(s, v)
        if v <= 0.0:                                                       # 止まった → 保持
            _, sn, cs = road_eval(road, s)
            hb = _caps(p, cs)[1] if hold_brake is None else hold_brake
            return p["a_creep"], hb
        return dr, br

    return command


def hill_hold_brake_min(theta: float, c_rr: float = 0.012, a_creep: float = 0.0, g: float = G) -> float:
    """坂で止まっていられる最小の制動 [m/s²] = max(0, |a_creep − g sin θ| − c_rr g cos θ)(静止摩擦のつり合い)。"""
    op = "hill_hold_brake_min"
    th = _check_theta(theta, op)
    crr = _nonneg(c_rr, "c_rr", op)
    ac = _nonneg(a_creep, "a_creep", op)
    g = _positive(g, "g", op)
    return max(0.0, abs(ac - g * math.sin(th)) - crr * g * math.cos(th))


def hill_start_rollback(theta: float, tau: float, a_drive: float, c_rr: float = 0.012, a_creep: float = 0.0,
                        g: float = G) -> Dict[str, float]:
    """上り坂(θ > 0)で止まった車がブレーキを離し、τ 秒後に駆動 a_drive が入るときのずり下がり(空気抵抗なしの閉形式)。

    τ の間の下向きの加速度 a₁ = g sin θ − c_rr g cos θ − a_creep(≤ 0 ならずり下がらない)。距離 ½ a₁ τ²、速さ a₁ τ。
    駆動が入ると後ろ向きの動きを a₂ = a_drive − g sin θ + c_rr g cos θ で止める(転がり抵抗も動きに逆らう)→ (a₁ τ)²/(2 a₂)。

    Returns
    -------
    dict : ``rollback``(合計 [m])、``during_gap``(½ a₁ τ²)、``recovery``((a₁τ)²/(2a₂))、``a1``、``a2``、``v_back``。
    a₂ ≤ 0(駆動が坂に負ける)なら rollback = inf。

    **Raises** ``ValueError``: τ < 0、a_drive ≤ 0、非有限。"""
    op = "hill_start_rollback"
    th = _check_theta(theta, op)
    tau = _nonneg(tau, "tau", op)
    ad = _positive(a_drive, "a_drive", op)
    crr = _nonneg(c_rr, "c_rr", op)
    ac = _nonneg(a_creep, "a_creep", op)
    g = _positive(g, "g", op)
    sn, cs = math.sin(th), math.cos(th)
    a1 = g * sn - crr * g * cs - ac
    a2 = ad - g * sn + crr * g * cs
    if a1 <= 0.0 or tau == 0.0:
        return {"rollback": 0.0, "during_gap": 0.0, "recovery": 0.0, "a1": a1, "a2": a2, "v_back": 0.0}
    during = 0.5 * a1 * tau * tau
    vb = a1 * tau
    rec = math.inf if a2 <= 0 else vb * vb / (2.0 * a2)
    return {"rollback": during + rec, "during_gap": during, "recovery": rec, "a1": a1, "a2": a2, "v_back": vb}


def hill_start_command(t_release: float, tau: float, a_drive: float, b_hold: float, a_creep: float = 0.0,
                       technique: str = "gap", v_cruise: Optional[float] = None) -> Callable:
    """坂道発進の指令。t_release までは保持(クリープ + 制動 b_hold)。

    * ``technique="gap"``: t_release でブレーキを離し、τ 後に駆動 a_drive(足を踏み替える間 = ずり下がる。閉形式は
      :func:`hill_start_rollback`)。
    * ``technique="overlap"``: t_release から τ の間、ブレーキを保ったままアクセルを踏み(駆動 a_drive)、τ 後にブレーキを離す
      (教習で教える「アクセルを踏んでからブレーキを離す」)。駆動 > 坂なら逆行 0。
    ``v_cruise`` を与えると、その速さに達したら駆動を止める(惰行)。"""
    op = "hill_start_command"
    tr = _finite(t_release, "t_release", op)
    tau = _nonneg(tau, "tau", op)
    ad = _positive(a_drive, "a_drive", op)
    bh = _nonneg(b_hold, "b_hold", op)
    ac = _nonneg(a_creep, "a_creep", op)
    if technique not in ("gap", "overlap"):
        raise ValueError("%s: technique must be 'gap' or 'overlap'" % op)

    def command(t, s, v):
        if t < tr:
            return ac, bh
        if v_cruise is not None and v >= v_cruise:
            return 0.0, 0.0
        if technique == "gap":
            return (ac, 0.0) if t < tr + tau else (ad, 0.0)
        return (ad, bh) if t < tr + tau else (ad, 0.0)

    command.t_breaks = (tr, tr + tau)
    return command


# ---- 技能試験の採点 --------------------------------------------------------------------------------
def skill_test_thresholds() -> Dict[str, object]:
    """採点に使う数字(通達には距離・時間の数字が無い。値ごとに出どころを付ける)。"""
    return {
        "rollback_small": 0.3, "rollback_medium": 0.5, "rollback_large": 1.0,
        "rollback_source": "二次情報(教習所サイト等、要確認): 逆行小 0.3〜0.5 m・中 0.5〜1 m・大 1 m 以上(同じ場所の累計)",
        "stop_gap_max": 2.0,
        "stop_source": "二次情報(要確認): 停止線を越えない・おおむね 2 m 以上手前は停止位置不適",
        "signal_violation_over": 2.0,
        "signal_source": "仮定(出典なし): 前端が停止線を 2 m(= 横断歩道の手前までの標準の間隔)越えたら信号無視とみなす",
        "start_delay_max": 3.0,
        "start_source": "仮定(出典なし): 発進の合図(青)から動き出すまで 3 s を超えたら発進手間どり",
        "creep_eps": 0.01,
        "pass_mark": 70,
        "points_source": "警察庁 丙運発第 12 号(令和 4 年)減点細目・第 10 合格基準(第一種 70 点以上)",
    }


_POINTS = {  # (路上, 場内)。None = 試験中止(危)
    "停止位置不適": (5, 5), "逆行小": (10, 10), "逆行中": (20, 20), "逆行大": (None, None),
    "発進手間どり": (10, 5), "制動操作不良": (5, 5), "制動操作不良(クリープ)": (10, 5), "信号無視": (None, None),
}


def skill_test_score(events, venue: str = "場内", thresholds: Optional[dict] = None) -> Dict[str, object]:
    """技能試験の減点を集計する(警察庁 丙運発第 12 号 令和 4 年の減点細目)。

    events : dict の列。
      * ``{"kind": "stop", "gap": 前端から停止線 [m](負 = 越えた), "signal": "red" など(任意)}`` →
        gap < 0 または gap > stop_gap_max で 停止位置不適。赤信号で越え幅 > signal_violation_over なら 信号無視(試験中止)。
      * ``{"kind": "brake", "stages": 段数}`` → 1 段以下で 制動操作不良(「ブレーキを数回に分けて踏まない場合」)。
      * ``{"kind": "start", "rollback": 逆行 [m](その場所の累計), "delay": 発進の合図から動き出すまで [s](任意)}`` →
        逆行小・中・大(大は試験中止)、delay > start_delay_max で 発進手間どり。
      * ``{"kind": "hold", "creep": 保持中に動いた距離 [m]}`` → creep > creep_eps で 制動操作不良(クリープ)。
    venue : "場内" か "路上"(点数が違う細目がある)。

    Returns
    -------
    dict : ``deductions``(``(細目, 点, 説明)`` の列。点 None = 試験中止)、``total``(減点の合計)、``score``(100 − 合計、
    試験中止なら None)、``test_stopped``、``passed``(第一種 70 点以上)、``thresholds``。

    **Raises** ``ValueError``: venue が不正、event の kind が不明・値が非有限。"""
    op = "skill_test_score"
    if venue not in ("場内", "路上"):
        raise ValueError("%s: venue must be '場内' or '路上'" % op)
    th = skill_test_thresholds()
    if thresholds:
        th.update(thresholds)
    col = 0 if venue == "路上" else 1
    out: List[Tuple[str, Optional[int], str]] = []

    def ded(name, detail):
        out.append((name, _POINTS[name][col], detail))

    for ev in events:
        if not isinstance(ev, dict) or "kind" not in ev:
            raise ValueError("%s: each event must be a dict with 'kind'" % op)
        kind = ev["kind"]
        if kind == "stop":
            gap = _finite(ev["gap"], "gap", op)
            if gap < 0:
                if ev.get("signal") == "red" and -gap > th["signal_violation_over"]:
                    ded("信号無視", "赤で停止線を %.2f m 越えた" % -gap)
                else:
                    ded("停止位置不適", "停止線を %.2f m 越えて停止" % -gap)
            elif gap > th["stop_gap_max"]:
                ded("停止位置不適", "停止線の %.2f m 手前で停止(直前でない)" % gap)
        elif kind == "brake":
            st = int(ev["stages"])
            if st < 2:
                ded("制動操作不良", "ブレーキを %d 段で踏んだ(数回に分けていない)" % st)
        elif kind == "start":
            rb = _nonneg(ev.get("rollback", 0.0), "rollback", op)
            if rb >= th["rollback_large"]:
                ded("逆行大", "逆行 %.2f m" % rb)
            elif rb >= th["rollback_medium"]:
                ded("逆行中", "逆行 %.2f m" % rb)
            elif rb >= th["rollback_small"]:
                ded("逆行小", "逆行 %.2f m" % rb)
            if "delay" in ev and ev["delay"] is not None:
                dl = _finite(ev["delay"], "delay", op)
                if dl > th["start_delay_max"]:
                    ded("発進手間どり", "発進まで %.2f s" % dl)
        elif kind == "hold":
            cr = _nonneg(abs(_finite(ev.get("creep", 0.0), "creep", op)), "creep", op)
            if cr > th["creep_eps"]:
                ded("制動操作不良(クリープ)", "保持中に %.3f m 動いた" % cr)
        else:
            raise ValueError("%s: unknown event kind %r" % (op, kind))
    stopped = any(pt is None for _, pt, _ in out)
    total = int(sum(pt for _, pt, _ in out if pt is not None))
    score = None if stopped else 100 - total
    return {"deductions": out, "total": total, "score": score, "test_stopped": stopped,
            "passed": (score is not None and score >= th["pass_mark"]), "thresholds": th}
