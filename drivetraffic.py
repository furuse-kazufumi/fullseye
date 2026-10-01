# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""動く交通参加者と死角: 追従する車列(IDM)・運転の癖・歩行者(social force)・横断の意図・路肩駐車の死角・
はみ出し追い越しの判断・出現事象のポアソン過程と重要度サンプリング。

## 何を作るか

自動運転 PoC 第 8 回「動く交通参加者と死角」の部品を numpy だけで持つ。これまでの巡の世界は止まっているか、
自車だけが動いていた。ここでは **他の参加者が動き**、しかも **見えない所から出てくる**:

1. 車列: Intelligent Driver Model(IDM)で先頭車の速度に追従する車列を積分する(``idm_accel`` /
   ``idm_equilibrium_gap`` / ``idm_platoon_simulate``)。運転の癖は車ごとの母数と反応遅れ(``driver_style``)。
2. 横ふらつき: Ornstein–Uhlenbeck 過程の厳密離散化(``lateral_wobble``)。
3. 歩行者: social force の 1 歩(``social_force_step``)と、意図(渡る / 待ってから渡る / 沿って歩く)を
   真値として持つ横断の軌跡(``pedestrian_crossing``)。
4. 死角: 路肩駐車車両の陰から出てくる点が **初めて見える** ときの縦距離(``occlusion_reveal_distance``)と、
   その距離で止まれる最大速度(``occlusion_safe_speed``)。
5. はみ出し: 駐車車両を避けて対向車線に出る区間を抜ける時間と、対向車がそれまでに来ない境目の距離
   (``passing_gap_required`` / ``passing_decision`` / ``passing_simulate``)。
6. 稀な出現: 位置に依存する率の非一様ポアソン過程(``poisson_events``、例 ``bus_stop_rate``)と、率を上げた試行を
   尤度比で戻す事故確率の推定(``importance_risk_estimate``)。

## 真値にする閉形式(門)

* IDM の平衡車間 s_e(v) = (s0 + v T) / sqrt(1 − (v/v0)^δ)。先頭車が一定速度なら車列の積分はそこへ収束する
  (積分は IDM の加速度だけを使い、平衡の式は使わない → 独立な経路)。停止時は s_e(0) = s0。
* OU 過程: 定常分散 σ²/(2θ)、自己相関 e^{−θτ}(厳密離散化なので dt に依らない)。
* social force: 1 人で斥力が無ければ dv/dt = (v0 e − v)/τ は線形 → v(t) = v0(1 − e^{−t/τ})、
  x(t) = v0 (t − τ(1 − e^{−t/τ}))。積分器はこの線形部分を厳密に解く指数積分(斥力は刻みの間一定と置く)。
* 死角: 箱の角 c を通る視線 e → c が自車の進路と交わる点が「見え始め」。軸平行の例では
  d = (e_x − c_x) · e_y / (e_y − c_y)(e = 出てくる点、c = 陰を作る角、自車の進路 y = 0)。
* 見えてから止まれる速度 v = b(−ρ + sqrt(ρ² + 2d/b))(= ``rsssafety.rss_stopping_distance(v, ρ, 0, b) = d``
  を v について解いたもの。桁落ちを避けて v = 2d / (ρ + sqrt(ρ² + 2d/b)) で計算する)。
* はみ出しの境目 D* = (L_occ / v_ego + T_lc)(v_ego + v_on) + v_on · PET_min、L_occ = margin_back + 駐車車両の長さ
  + margin_front。D ≥ D* なら go。
* ポアソン過程: 件数 N ~ Poisson(Λ)、Λ = ∫λ → E[N] = Var[N] = Λ。thinning は Lewis & Shedler (1979)。
* 重要度サンプリング: ポアソン過程の尤度比 dP/dP' = Π_i λ(x_i)/λ'(x_i) · exp(−(Λ − Λ'))(率が一定なら
  (λ/λ')^N exp(−(Λ − Λ')))。重みつき平均は本来の率の事故確率の不偏推定。

## 出典(書誌)と仮定

**このモジュールの数値の定数はすべて仮定**(一次情報で値を確かめたものは無い)。式の形は次の文献のものとして書くが、
**この巡で論文本文を開いて照合はしていない**(NOTES の未確認に記す):

* IDM: M. Treiber, A. Hennecke, D. Helbing, "Congested traffic states in empirical observations and microscopic
  simulations", Phys. Rev. E 62, 1805 (2000)。s* の ``max(0, ·)`` は Treiber & Kesting "Traffic Flow Dynamics"
  (2013) の形(負の s* を防ぐ)。積分は Treiber & Kanagaraj (2015) の "ballistic update"(速度は 1 次、位置は 2 次、
  速度が負になる刻みでは止まる所で止める)。
* social force: D. Helbing, P. Molnár, Phys. Rev. E 51, 4282 (1995); D. Helbing, I. Farkas, T. Vicsek,
  Nature 407, 487 (2000)。斥力は 2000 年版の A exp((r_ij − d_ij)/B) n_ij(接触力・摩擦力は持たない)。
  単位質量あたり(A は m/s²)。
* thinning: P. A. W. Lewis, G. S. Shedler, Naval Res. Logistics Quarterly 26, 403 (1979)。
* 歩行速度の既定 1.2 m/s は **仮定**(信号の歩行者時間の設計に使われる値は 1.0 m/s 前後と言われるが一次未確認)。
* ``driver_style`` の 3 種の母数・反応遅れ・ふらつき・速度むらはすべて **仮定**(IDM の典型値として文献に
  よく再掲される桁: T ≈ 1〜2 s、a ≈ 1 m/s²、b ≈ 1.5〜2 m/s²、s0 ≈ 2 m、δ = 4 に合わせた)。

## 単位と座標

m, s, m/s, m/s², rad。平面は (x, y)、向きは x 軸から反時計回り。``pedestrian_crossing`` の道路は x 方向に伸び、
車道は 0 ≤ y ≤ road_width、歩道は y < 0(手前)と y > road_width(向こう)。

## 限界(self_reported)

* IDM は 1 車線の縦だけ。車線変更・合流・信号は持たない。反応遅れは刻み dt の整数倍に丸める。
* social force は斥力が刻みの間一定の近似(1 次)。接触力・視野の異方性・速度上限は持たない。
* 死角は 2D(目の高さ・車高を持たない。背の低い子どもは車の上から見えない、という 3D の効果は扱わない)。
* はみ出しは点の車(車長は ``ego_length`` で区間に足すだけ)、対向車は一定速度、自車も一定速度。
"""
from __future__ import annotations

import math
from typing import Callable, Dict, Optional

import numpy as np

__all__ = [
    "WALK_SPEED", "DRIVER_KINDS", "PEDESTRIAN_INTENTS",
    "idm_accel", "idm_equilibrium_gap", "idm_platoon_simulate", "driver_style",
    "lateral_wobble", "ou_estimate",
    "social_force_step", "pedestrian_crossing",
    "occlusion_reveal_distance", "occlusion_visible_intervals", "occlusion_safe_speed",
    "passing_gap_required", "passing_decision", "passing_simulate",
    "bus_stop_rate", "poisson_events", "poisson_events_xt", "importance_risk_estimate",
]

WALK_SPEED = 1.2                     # 歩行速度の既定 [m/s](仮定。一次未確認)
DRIVER_KINDS = ("careful", "normal", "sloppy")
PEDESTRIAN_INTENTS = ("cross", "wait_then_cross", "walk_along", "stand_no_cross")
_IDM_KEYS = ("v0", "T", "a", "b", "s0", "delta")


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


def _array(v, name: str, op: str, allow_inf: bool = False) -> np.ndarray:
    try:
        a = np.asarray(v, dtype=float)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be numeric, got %r" % (op, name, v))
    bad = np.isnan(a) if allow_inf else ~np.isfinite(a)
    if np.any(bad):
        raise ValueError("%s: %s must be finite%s" % (op, name, "" if not allow_inf else " or +inf"))
    return a


def _xy(v, name: str, op: str) -> np.ndarray:
    a = _array(v, name, op)
    if a.shape != (2,):
        raise ValueError("%s: %s must be a 2-vector (x, y), got shape %r" % (op, name, a.shape))
    return a


# ---- 1. IDM ---------------------------------------------------------------------------------------
def idm_accel(v, gap, dv, *, v0: float, T: float, a: float, b: float, s0: float, delta: float = 4.0):
    """Intelligent Driver Model の加速度(Treiber, Hennecke, Helbing 2000)。

        a_IDM = a [ 1 − (v/v0)^δ − (s*/s)² ],   s* = s0 + max(0, v T + v Δv / (2 sqrt(a b)))

    ``dv`` = Δv = v − v_lead(近づいていれば正)、``gap`` = s = 先行車の後端までの距離(> 0、``inf`` = 前が空き)。
    ``v``, ``gap``, ``dv`` は numpy の放送で配列でも動く(スカラーを渡せば float を返す)。

    門: 平衡車間 ``idm_equilibrium_gap`` で Δv = 0 なら 0、gap = inf で a(1 − (v/v0)^δ)。

    **Raises** ``ValueError``: v < 0、gap ≤ 0、非有限、母数が正でない。"""
    op = "idm_accel"
    v0 = _positive(v0, "v0", op)
    T = _nonneg(T, "T", op)
    a = _positive(a, "a", op)
    b = _positive(b, "b", op)
    s0 = _nonneg(s0, "s0", op)
    delta = _positive(delta, "delta", op)
    va = _array(v, "v", op)
    ga = _array(gap, "gap", op, allow_inf=True)
    da = _array(dv, "dv", op)
    if np.any(va < 0):
        raise ValueError("%s: v must be >= 0" % op)
    if np.any(ga <= 0):
        raise ValueError("%s: gap must be > 0 (got min %r)" % (op, float(np.min(ga))))
    s_star = s0 + np.maximum(0.0, va * T + va * da / (2.0 * math.sqrt(a * b)))
    with np.errstate(divide="ignore", invalid="ignore"):
        inter = np.where(np.isinf(ga), 0.0, (s_star / np.where(np.isinf(ga), 1.0, ga)) ** 2)
    out = a * (1.0 - (va / v0) ** delta - inter)
    return float(out) if out.ndim == 0 else out


def idm_equilibrium_gap(v, *, v0: float, T: float, s0: float, delta: float = 4.0):
    """IDM の平衡車間 s_e(v) = (s0 + v T) / sqrt(1 − (v/v0)^δ)(0 ≤ v < v0)。

    Δv = 0 で ``idm_accel`` = 0 と置いて解いたもの(s* = s0 + vT)。v → v0 で発散する(希望速度では車間は要らない
    = 前が無限に遠い)。a, b に依らない。

    門: 先行車が一定速度のとき ``idm_platoon_simulate`` が収束した車間と rtol 1e-6 で一致。

    **Raises** ``ValueError``: v < 0 または v ≥ v0。"""
    op = "idm_equilibrium_gap"
    v0 = _positive(v0, "v0", op)
    T = _nonneg(T, "T", op)
    s0 = _nonneg(s0, "s0", op)
    delta = _positive(delta, "delta", op)
    va = _array(v, "v", op)
    if np.any(va < 0) or np.any(va >= v0):
        raise ValueError("%s: v must satisfy 0 <= v < v0 (v0=%r)" % (op, v0))
    out = (s0 + va * T) / np.sqrt(1.0 - (va / v0) ** delta)
    return float(out) if out.ndim == 0 else out


def _check_idm_params(p, op: str, i: int) -> Dict[str, float]:
    if not isinstance(p, dict):
        raise ValueError("%s: params_per_vehicle[%d] must be a dict, got %r" % (op, i, type(p).__name__))
    missing = [k for k in _IDM_KEYS if k not in p and k != "delta"]
    if missing:
        raise ValueError("%s: params_per_vehicle[%d] missing keys %r" % (op, i, missing))
    q = {
        "v0": _positive(p["v0"], "v0", op), "T": _nonneg(p["T"], "T", op), "a": _positive(p["a"], "a", op),
        "b": _positive(p["b"], "b", op), "s0": _nonneg(p["s0"], "s0", op),
        "delta": _positive(p.get("delta", 4.0), "delta", op),
        "length": _nonneg(p.get("length", 4.5), "length", op),
        "speed_noise": _nonneg(p.get("speed_noise", 0.0), "speed_noise", op),
    }
    if "reaction_delay" in p and p["reaction_delay"] is not None:
        q["reaction_delay"] = _nonneg(p["reaction_delay"], "reaction_delay", op)
    return q


def idm_platoon_simulate(lead_v_of_t, n_followers: int, *, params_per_vehicle, dt: float, t_end: float,
                         reaction_delay: float = 0.0, seed: Optional[int] = None) -> Dict[str, object]:
    """先頭車の速度プロファイルに IDM の追従車列を積分する(車 0 = 先頭、1..n = 追従車)。

    引数
    ----
    * ``lead_v_of_t``: 先頭車の速度 [m/s]。``callable(t) -> v`` か、時刻列と同じ長さの配列。
    * ``params_per_vehicle``: 追従車ごとの dict(長さ n)か、全車共通の 1 つの dict。キー ``v0, T, a, b, s0``
      (必須)、``delta``(既定 4)、``length``(前の車の車長として使う。既定 4.5 m、仮定)、``reaction_delay``
      (無ければ引数 ``reaction_delay``)、``speed_noise``(希望速度 v0 に掛ける 1 + N(0, speed_noise²) の相対むら。
      > 0 なら ``seed`` が必須 = 決定的)。先頭車の車長は ``params_per_vehicle`` の 1 台目の ``length`` を使う。
    * ``reaction_delay``: 反応遅れ [s]。刻み dt の整数倍に丸める(m = round(delay/dt))。車 i は時刻 k に
      **時刻 k − m の自分の速度・車間・相対速度** を見て加速度を決める(t < 0 は初期の定常状態が続いていたとする)。

    積分(ballistic update): v_{k+1} = max(0, v_k + a_k dt)、x_{k+1} = x_k + v_k dt + ½ a_k dt²
    (速度が負になる刻みでは止まる位置 x_k − v_k²/(2 a_k) で止める)。先頭車の位置は速度の台形積分。
    初期状態: 全車が v_lead(0) で走り、各追従車の車間はその速度の平衡車間 ``idm_equilibrium_gap``。
    車間が 0 以下になったら(追突)、その車を **接触の位置(車間 0)で止め**、以後は動かさない(速度・加速度 0。前の車や
    後ろの車は積分を続け、後ろの車には止まった車が先行車になる)。車を重ねない —— 重ねたまま積分すると位置に意味が無い。

    戻り値 dict: ``t`` (K,)、``x``, ``v``, ``a``, ``gap`` (K, n+1)(gap[:, 0] = inf)、``params``(実際に使った
    車ごとの母数。速度むら込み)、``delay_steps`` (n,)、``collision``(bool)、``collision_time``(最初の時刻 or None)、
    ``collisions``(追突の ``(時刻, 車番)`` の列。車番 i は前の車 i−1 に追突した車)、``crashed`` (n+1,) bool。
    """
    op = "idm_platoon_simulate"
    if isinstance(n_followers, bool) or not isinstance(n_followers, (int, np.integer)) or n_followers < 1:
        raise ValueError("%s: n_followers must be a positive int, got %r" % (op, n_followers))
    n = int(n_followers)
    dt = _positive(dt, "dt", op)
    t_end = _positive(t_end, "t_end", op)
    reaction_delay = _nonneg(reaction_delay, "reaction_delay", op)
    K = int(round(t_end / dt)) + 1
    t = np.arange(K) * dt

    if isinstance(params_per_vehicle, dict):
        plist = [params_per_vehicle] * n
    else:
        plist = list(params_per_vehicle)
        if len(plist) != n:
            raise ValueError("%s: params_per_vehicle has %d entries, expected n_followers=%d"
                             % (op, len(plist), n))
    ps = [_check_idm_params(p, op, i) for i, p in enumerate(plist)]
    rng = None
    if any(p["speed_noise"] > 0 for p in ps):
        if seed is None:
            raise ValueError("%s: speed_noise > 0 needs an explicit seed (determinism)" % op)
        rng = np.random.default_rng(seed)
    for p in ps:
        if p["speed_noise"] > 0:
            p["v0"] = p["v0"] * max(0.2, 1.0 + p["speed_noise"] * float(rng.standard_normal()))
        p.setdefault("reaction_delay", reaction_delay)

    if callable(lead_v_of_t):
        vl = np.array([float(lead_v_of_t(float(tk))) for tk in t])
    else:
        vl = np.asarray(lead_v_of_t, dtype=float)
        if vl.shape != (K,):
            raise ValueError("%s: lead_v_of_t array must have length %d (t_end/dt+1), got %r" % (op, K, vl.shape))
    if not np.all(np.isfinite(vl)) or np.any(vl < 0):
        raise ValueError("%s: lead speed must be finite and >= 0" % op)

    v0s = np.array([p["v0"] for p in ps])
    Ts = np.array([p["T"] for p in ps])
    As = np.array([p["a"] for p in ps])
    Bs = np.array([p["b"] for p in ps])
    S0s = np.array([p["s0"] for p in ps])
    Ds = np.array([p["delta"] for p in ps])
    lengths = np.array([ps[0]["length"]] + [p["length"] for p in ps])     # 車 j の車長(j = 0..n)
    m = np.array([int(round(p["reaction_delay"] / dt)) for p in ps])
    if np.any(vl[0] >= v0s):
        raise ValueError("%s: initial lead speed %r must be below every follower's v0" % (op, vl[0]))

    X = np.zeros((K, n + 1))
    V = np.zeros((K, n + 1))
    A = np.zeros((K, n + 1))
    GAP = np.full((K, n + 1), np.inf)
    V[0, :] = vl[0]
    for i in range(1, n + 1):
        p = ps[i - 1]
        se = idm_equilibrium_gap(vl[0], v0=p["v0"], T=p["T"], s0=p["s0"], delta=p["delta"])
        X[0, i] = X[0, i - 1] - lengths[i - 1] - se
    V[:, 0] = vl
    X[1:, 0] = np.cumsum(0.5 * (vl[1:] + vl[:-1]) * dt)
    A[:-1, 0] = np.diff(vl) / dt
    A[-1, 0] = A[-2, 0] if K > 1 else 0.0

    sq = 2.0 * np.sqrt(As * Bs)
    idx = np.arange(1, n + 1)
    collision_time = None
    crashed = np.zeros(n + 1, dtype=bool)
    collisions = []
    for k in range(K):
        GAP[k, 1:] = X[k, :-1] - X[k, 1:] - lengths[:-1]
        new = np.nonzero((GAP[k, 1:] <= 0) & ~crashed[1:])[0] + 1
        for i in new:                                     # 前から順に: 追突した車は接触の位置で止める(重ねない)
            collisions.append((float(t[k]), int(i)))
            crashed[i] = True
            X[k, i] = min(X[k, i], X[k, i - 1] - lengths[i - 1])
            V[k, i] = 0.0
            GAP[k, 1:] = X[k, :-1] - X[k, 1:] - lengths[:-1]
        if collisions and collision_time is None:
            collision_time = collisions[0][0]
        kd = np.maximum(k - m, 0)
        vo = V[kd, idx]
        so = np.maximum(GAP[kd, idx], 1e-3)
        dvo = vo - V[kd, idx - 1]
        s_star = S0s + np.maximum(0.0, vo * Ts + vo * dvo / sq)
        acc = As * (1.0 - (vo / v0s) ** Ds - (s_star / so) ** 2)
        acc = np.where(crashed[1:], 0.0, acc)
        A[k, 1:] = acc
        if k == K - 1:
            break
        vk = V[k, 1:]
        vn = vk + acc * dt
        stop = vn < 0
        xn = X[k, 1:] + vk * dt + 0.5 * acc * dt * dt
        if np.any(stop):
            xn = np.where(stop, X[k, 1:] - vk * vk / (2.0 * np.where(stop, acc, -1.0)), xn)
            vn = np.where(stop, 0.0, vn)
        V[k + 1, 1:] = vn
        X[k + 1, 1:] = xn
    return {"t": t, "x": X, "v": V, "a": A, "gap": GAP, "params": ps, "delay_steps": m,
            "collision": collision_time is not None, "collision_time": collision_time,
            "collisions": collisions, "crashed": crashed}


# ---- 4. 運転の癖 -----------------------------------------------------------------------------------
_STYLES = {
    # すべて仮定(出典なし)。市街地の希望速度 45〜55 km/h、IDM の典型値の桁に合わせた。
    "careful": {"v0": 12.5, "T": 2.0, "a": 1.0, "b": 1.5, "s0": 3.0, "delta": 4.0,
                "reaction_delay": 0.6, "wobble_theta": 0.5, "wobble_sigma": 0.05, "speed_noise": 0.02},
    "normal": {"v0": 13.9, "T": 1.5, "a": 1.4, "b": 2.0, "s0": 2.0, "delta": 4.0,
               "reaction_delay": 0.9, "wobble_theta": 0.4, "wobble_sigma": 0.10, "speed_noise": 0.05},
    "sloppy": {"v0": 15.3, "T": 1.0, "a": 2.0, "b": 3.0, "s0": 1.5, "delta": 4.0,
               "reaction_delay": 1.3, "wobble_theta": 0.25, "wobble_sigma": 0.20, "speed_noise": 0.10},
}
_STYLE_JITTER = ("v0", "T", "a", "b", "s0", "reaction_delay", "wobble_theta", "wobble_sigma")


def driver_style(kind: str, seed: Optional[int] = None) -> Dict[str, float]:
    """運転の癖 3 種("careful" / "normal" / "sloppy")の母数を返す。**値はすべて仮定**(出典なし)。

    キー: IDM の ``v0, T, a, b, s0, delta``、``reaction_delay`` [s]、横ふらつき(OU 過程)の ``wobble_theta`` [1/s]
    と ``wobble_sigma`` [m/√s] (定常の標準偏差は σ/sqrt(2θ) = 0.05 / 0.11 / 0.28 m)、``speed_noise``(希望速度の
    相対むら)、``length`` 4.5 m(仮定)、``kind``。返り値はそのまま ``idm_platoon_simulate`` の 1 台分に渡せる。

    ``seed`` を与えると、主要な値に一様 ±10% の個人差を掛ける(``default_rng(seed)`` で決定的)。None なら名目値。
    順序の性質(門): 名目値で careful の T・s0 が最大で反応遅れが最小、sloppy がその逆、ふらつきの定常 SD は
    careful < normal < sloppy。

    **Raises** ``ValueError``: 未知の kind。"""
    op = "driver_style"
    if kind not in _STYLES:
        raise ValueError("%s: kind must be one of %r, got %r" % (op, DRIVER_KINDS, kind))
    out = dict(_STYLES[kind])
    if seed is not None:
        rng = np.random.default_rng(seed)
        f = rng.uniform(0.9, 1.1, size=len(_STYLE_JITTER))
        for k, fk in zip(_STYLE_JITTER, f):
            out[k] = out[k] * float(fk)
    out["length"] = 4.5
    out["kind"] = kind
    return out


# ---- 5. 横ふらつき(OU 過程) -------------------------------------------------------------------------
def lateral_wobble(n: int, dt: float, *, theta: float, sigma: float, seed: Optional[int],
                   x0: Optional[float] = None) -> np.ndarray:
    """Ornstein–Uhlenbeck 過程 dX = −θ X dt + σ dW の厳密離散化(長さ n の列、刻み dt)。

        x_{k+1} = x_k e^{−θ dt} + σ sqrt((1 − e^{−2θ dt}) / (2θ)) ξ_k,   ξ_k ~ N(0, 1) 独立

    遷移分布が厳密なので dt に依らず定常分散 σ²/(2θ)、自己相関 corr(x_k, x_{k+j}) = e^{−θ j dt}(門は長い系列の標本で、
    許容幅は AR(1) の標本誤差から決める)。``x0`` = None なら定常分布 N(0, σ²/(2θ)) から引く(最初から定常)。
    ``seed`` は ``np.random.default_rng(seed)``(None も可だが非決定的)。

    **Raises** ``ValueError``: n < 1、dt ≤ 0、θ ≤ 0、σ < 0。"""
    op = "lateral_wobble"
    if isinstance(n, bool) or not isinstance(n, (int, np.integer)) or n < 1:
        raise ValueError("%s: n must be a positive int, got %r" % (op, n))
    dt = _positive(dt, "dt", op)
    theta = _positive(theta, "theta", op)
    sigma = _nonneg(sigma, "sigma", op)
    rng = np.random.default_rng(seed)
    phi = math.exp(-theta * dt)
    q = sigma * math.sqrt(-math.expm1(-2.0 * theta * dt) / (2.0 * theta))
    sd = sigma / math.sqrt(2.0 * theta)
    xi = rng.standard_normal(n)
    x = np.empty(n)
    x[0] = sd * xi[0] if x0 is None else _finite(x0, "x0", op)
    for k in range(1, n):
        x[k] = x[k - 1] * phi + q * xi[k]
    return x


def ou_estimate(x, dt: float) -> Dict[str, float]:
    """横ふらつき(平均 0 の OU 過程 dX = −θX dt + σ dW)の母数を、等間隔 dt の観測の列から読む。

    厳密離散化 x_{k+1} = φ x_k + ε_k(φ = e^{−θ dt}、ε ~ N(0, q²)、q² = σ²(1 − φ²)/(2θ))の条件つき最尤:

        φ̂ = Σ x_k x_{k+1} / Σ x_k²,  q̂² = mean((x_{k+1} − φ̂ x_k)²),  θ̂ = −ln φ̂ / dt,  σ̂ = q̂ sqrt(2θ̂ / (1 − φ̂²))

    (Euler の (1 − φ̂)/dt でなく ln を使うので dt が粗くても偏らない)。標準誤差は漸近式: se(φ̂) = sqrt((1 − φ²)/n)、
    se(q̂) = q/sqrt(2n)、θ̂・σ̂ はデルタ法。``sigma_increment`` = sqrt(mean(Δx²)/dt) は θ を使わない粗い推定
    (E[Δx²] = σ²(1 − φ)/θ なので θ dt → 0 で σ。相関時間の長い系列を短く見るとき、位置の標本 SD より σ を安定に読める)。

    戻り値 dict: ``theta``, ``sigma``, ``sd``(定常 SD σ/√(2θ))、``phi``, ``q``, ``n``(増分の数)、``se_theta``,
    ``se_sigma``, ``sigma_increment``。

    **Raises** ``ValueError``: 1-D でない・3 点未満・非有限、dt ≤ 0、φ̂ ∉ (0, 1)(この dt では平均へ戻る過程に見えない)。"""
    op = "ou_estimate"
    dt = _positive(dt, "dt", op)
    xa = _array(x, "x", op)
    if xa.ndim != 1 or xa.size < 3:
        raise ValueError("%s: x must be a 1-D series of at least 3 samples" % op)
    a, b = xa[:-1], xa[1:]
    den = float(np.dot(a, a))
    if den <= 0:
        raise ValueError("%s: x is identically zero" % op)
    phi = float(np.dot(a, b)) / den
    if not 0.0 < phi < 1.0:
        raise ValueError("%s: lag-1 coefficient %r is not in (0, 1) (not mean-reverting at this dt)" % (op, phi))
    n = int(a.size)
    q = math.sqrt(float(np.mean((b - phi * a) ** 2)))
    theta = -math.log(phi) / dt

    def g(ph):
        return math.sqrt(-2.0 * math.log(ph) / (dt * (1.0 - ph * ph)))
    sigma = q * g(phi)
    se_phi = math.sqrt((1.0 - phi * phi) / n)
    h = 1e-6 * min(phi, 1.0 - phi)
    dg = (g(phi + h) - g(phi - h)) / (2.0 * h)
    se_q = q / math.sqrt(2.0 * n)
    return {"theta": theta, "sigma": sigma, "sd": sigma / math.sqrt(2.0 * theta), "phi": phi, "q": q, "n": n,
            "se_theta": se_phi / (phi * dt), "se_sigma": math.hypot(g(phi) * se_q, q * dg * se_phi),
            "sigma_increment": math.sqrt(float(np.mean(np.diff(xa) ** 2)) / dt)}


# ---- 6. social force -----------------------------------------------------------------------------
def _seg_closest(P: np.ndarray, walls: np.ndarray) -> np.ndarray:
    """点 P (N,2) と線分 walls (M,2,2) の最近点 (N,M,2)。"""
    a = walls[:, 0, :][None, :, :]
    d = (walls[:, 1, :] - walls[:, 0, :])[None, :, :]
    dd = np.sum(d * d, axis=2)
    u = np.sum((P[:, None, :] - a) * d, axis=2) / np.where(dd > 0, dd, 1.0)
    u = np.clip(u, 0.0, 1.0)
    return a + u[:, :, None] * d


def social_force_step(pos, vel, goals, *, dt: float, v0, tau: float, A: float, B: float, radius,
                      walls=None):
    """social force の 1 歩(単位質量あたり。Helbing & Molnár 1995 / Helbing, Farkas, Vicsek 2000 の形)。

        dv_i/dt = (v0_i e_i − v_i)/τ + Σ_j A exp((r_ij − d_ij)/B) n_ij + Σ_W A exp((r_i − d_iW)/B) n_iW

    e_i = 目標への単位ベクトル(目標に 1e-9 m 以内なら 0)、r_ij = r_i + r_j、d_ij = |x_i − x_j|、
    n_ij = (x_i − x_j)/d_ij。壁 W は線分 ((x0, y0), (x1, y1)) の列で、d_iW と n_iW は最近点から。

    積分(指数積分): 斥力 F を刻みの間一定と置き、線形部分 (v_d − v)/τ(v_d = v0 e + τ F)を厳密に解く:
    v' = v_d + (v − v_d) e^{−dt/τ}、x' = x + v_d dt + (v − v_d) τ (1 − e^{−dt/τ})。
    1 人で斥力が無ければ v(t) = v0(1 − e^{−t/τ}) に **dt に依らず** 一致する(門)。斥力がある時は 1 次の誤差。

    引数: ``pos``, ``vel``, ``goals`` は (N, 2)。``v0`` と ``radius`` はスカラーか (N,)。``walls`` は (M, 2, 2) か None。
    戻り値: (pos', vel')。配置が鏡映・点対称なら結果も同じ対称性を保つ(式が対称なので。門で確かめる)。

    **Raises** ``ValueError``: 形の不一致、非有限、τ・B・dt ≤ 0、A < 0、半径 < 0、2 人の位置が一致。"""
    op = "social_force_step"
    P = _array(pos, "pos", op)
    Vv = _array(vel, "vel", op)
    G = _array(goals, "goals", op)
    if P.ndim != 2 or P.shape[1] != 2 or Vv.shape != P.shape or G.shape != P.shape:
        raise ValueError("%s: pos, vel, goals must all have shape (N, 2); got %r %r %r"
                         % (op, P.shape, Vv.shape, G.shape))
    N = P.shape[0]
    dt = _positive(dt, "dt", op)
    tau = _positive(tau, "tau", op)
    A = _nonneg(A, "A", op)
    B = _positive(B, "B", op)
    v0a = np.broadcast_to(_array(v0, "v0", op), (N,)).astype(float)
    ra = np.broadcast_to(_array(radius, "radius", op), (N,)).astype(float)
    if np.any(v0a < 0) or np.any(ra < 0):
        raise ValueError("%s: v0 and radius must be >= 0" % op)

    to_goal = G - P
    dist = np.linalg.norm(to_goal, axis=1)
    e = np.where(dist[:, None] > 1e-9, to_goal / np.where(dist > 1e-9, dist, 1.0)[:, None], 0.0)
    F = np.zeros_like(P)
    if N > 1:
        diff = P[:, None, :] - P[None, :, :]                      # x_i − x_j
        d = np.linalg.norm(diff, axis=2)
        off = ~np.eye(N, dtype=bool)
        if np.any(d[off] == 0):
            raise ValueError("%s: two pedestrians share the same position" % op)
        dsafe = np.where(off, d, 1.0)
        mag = np.where(off, A * np.exp((ra[:, None] + ra[None, :] - dsafe) / B), 0.0)
        F += np.sum(mag[:, :, None] * diff / dsafe[:, :, None], axis=1)
    if walls is not None:
        W = _array(walls, "walls", op)
        if W.ndim != 3 or W.shape[1:] != (2, 2):
            raise ValueError("%s: walls must have shape (M, 2, 2), got %r" % (op, W.shape))
        if W.shape[0] > 0:
            C = _seg_closest(P, W)
            diff = P[:, None, :] - C
            d = np.linalg.norm(diff, axis=2)
            if np.any(d == 0):
                raise ValueError("%s: a pedestrian stands exactly on a wall" % op)
            F += np.sum((A * np.exp((ra[:, None] - d) / B))[:, :, None] * diff / d[:, :, None], axis=1)
    vd = v0a[:, None] * e + tau * F
    E = math.exp(-dt / tau)
    one_m_E = -math.expm1(-dt / tau)
    v_new = vd + (Vv - vd) * E
    p_new = P + vd * dt + (Vv - vd) * tau * one_m_E
    return p_new, v_new


# ---- 7. 横断の意図 ---------------------------------------------------------------------------------
def pedestrian_crossing(intent: str, *, start_xy=(0.0, -3.0), road_width: float = 7.0,
                        speed: float = WALK_SPEED, wait_time: float = 3.0, curb_offset: float = 0.3,
                        along_heading: float = 0.0, dt: float = 0.1, t_end: Optional[float] = None
                        ) -> Dict[str, object]:
    """横断の意図を真値に持つ歩行者の軌跡(区分ごとの閉形式。積分しない)。

    道路は x 方向、車道 0 ≤ y ≤ road_width、歩道 y < 0 から始める(``start_xy`` の y < −curb_offset)。
    * ``cross``: (x0, y0) → 縁 (x0, −curb_offset) まで歩き、止まらずに向こうの縁 (x0, road_width + curb_offset)
      まで横断して止まる。向きは +π/2(車道の方)。
    * ``wait_then_cross``: 縁まで歩き、**縁で車道を向いて** (+π/2) ``wait_time`` 秒止まり、それから横断する。
    * ``walk_along``: 歩道を向き ``along_heading``(0 か π)で y = y0 のまま歩く(車道に入らない)。
    * ``stand_no_cross``: 縁まで歩き、**縁で車道を向いて** (+π/2) 立ち止まったまま渡らない(バス待ち・連れ待ち)。見た目は
      ``wait_then_cross`` の待ちと区別がつかない —— 規則で「止まる」と判断すれば誤検出になる真値。``t_cross_start`` は None。
    速さは ``speed``(既定 ``WALK_SPEED`` = 1.2 m/s、仮定)。

    戻り値 dict: ``t`` (K,)、``xy`` (K, 2)、``heading`` (K,)、``phase`` (K,) の文字列
    ("approach" / "wait" / "cross" / "done" / "along")、``intent``(真値)、``t_cross_start``・``t_cross_end``
    (横断しない意図では None)、``speed``。門: 横断にかかる時間 = (road_width + 2·curb_offset)/speed、待つ人は
    待ちの間の位置が一定で向きが +π/2、沿って歩く人は全時刻で y < 0、向きは位置の差分の向きと一致。

    **Raises** ``ValueError``: 未知の intent、speed ≤ 0、start が歩道上でない、along_heading が 0/π でない。"""
    op = "pedestrian_crossing"
    if intent not in PEDESTRIAN_INTENTS:
        raise ValueError("%s: intent must be one of %r, got %r" % (op, PEDESTRIAN_INTENTS, intent))
    s = _xy(start_xy, "start_xy", op)
    W = _positive(road_width, "road_width", op)
    sp = _positive(speed, "speed", op)
    wt = _nonneg(wait_time, "wait_time", op)
    co = _nonneg(curb_offset, "curb_offset", op)
    dt = _positive(dt, "dt", op)
    ah = _finite(along_heading, "along_heading", op)
    if not s[1] < -co:
        raise ValueError("%s: start_xy must be on the near sidewalk (y < -curb_offset), got %r" % (op, s[1]))
    if ah not in (0.0, math.pi):
        raise ValueError("%s: along_heading must be 0 or pi, got %r" % (op, ah))
    t_app = (-co - s[1]) / sp
    t_wait = wt if intent == "wait_then_cross" else (math.inf if intent == "stand_no_cross" else 0.0)
    t_cs = t_app + t_wait
    t_ce = t_cs + (W + 2.0 * co) / sp
    if t_end is None:
        t_end = 10.0 if intent == "walk_along" else ((t_app + 10.0) if intent == "stand_no_cross" else (t_ce + 1.0))
    t_end = _positive(t_end, "t_end", op)
    K = int(math.floor(t_end / dt + 1e-9)) + 1
    t = np.arange(K) * dt
    xy = np.empty((K, 2))
    heading = np.empty(K)
    phase = np.empty(K, dtype=object)
    if intent == "walk_along":
        xy[:, 0] = s[0] + math.cos(ah) * sp * t
        xy[:, 1] = s[1]
        heading[:] = ah
        phase[:] = "along"
        return {"t": t, "xy": xy, "heading": heading, "phase": phase, "intent": intent,
                "t_cross_start": None, "t_cross_end": None, "speed": sp}
    y_curb = -co
    y_far = W + co
    xy[:, 0] = s[0]
    heading[:] = math.pi / 2.0
    for k, tk in enumerate(t):
        if tk < t_app:
            xy[k, 1] = s[1] + sp * tk
            phase[k] = "approach"
        elif tk < t_cs:
            xy[k, 1] = y_curb
            phase[k] = "wait"
        elif tk < t_ce:
            xy[k, 1] = y_curb + sp * (tk - t_cs)
            phase[k] = "cross"
        else:
            xy[k, 1] = y_far
            phase[k] = "done"
    if intent == "stand_no_cross":
        t_cs = t_ce = None
    return {"t": t, "xy": xy, "heading": heading, "phase": phase, "intent": intent,
            "t_cross_start": t_cs, "t_cross_end": t_ce, "speed": sp}


# ---- 8. 死角 -------------------------------------------------------------------------------------
def _box(parked_box, op: str):
    b = _array(parked_box, "parked_box", op)
    if b.shape != (5,):
        raise ValueError("%s: parked_box must be (cx, cy, length, width, yaw), got shape %r" % (op, b.shape))
    cx, cy, L, Wd, yaw = (float(x) for x in b)
    if not (L > 0 and Wd > 0):
        raise ValueError("%s: parked_box length and width must be > 0" % op)
    return cx, cy, L, Wd, yaw


def _box_corners(cx, cy, L, Wd, yaw) -> np.ndarray:
    c, s = math.cos(yaw), math.sin(yaw)
    loc = np.array([[L / 2, Wd / 2], [-L / 2, Wd / 2], [-L / 2, -Wd / 2], [L / 2, -Wd / 2]])
    R = np.array([[c, -s], [s, c]])
    return loc @ R.T + np.array([cx, cy])


def _segment_blocked(p, e, cx, cy, L, Wd, yaw, eps: float) -> bool:
    """線分 p→e が箱の **内部**(各辺を eps 縮めた箱)を通るか(スラブ法)。角をかすめるだけなら通らない。"""
    c, s = math.cos(yaw), math.sin(yaw)

    def loc(q):
        dx, dy = q[0] - cx, q[1] - cy
        return c * dx + s * dy, -s * dx + c * dy
    p0 = loc(p)
    p1 = loc(e)
    t0, t1 = 0.0, 1.0
    for k, half in ((0, L / 2 - eps), (1, Wd / 2 - eps)):
        d = p1[k] - p0[k]
        if abs(d) < 1e-300:
            if not (-half < p0[k] < half):
                return False
            continue
        ta = (-half - p0[k]) / d
        tb = (half - p0[k]) / d
        if ta > tb:
            ta, tb = tb, ta
        t0 = max(t0, ta)
        t1 = min(t1, tb)
        if t0 >= t1:
            return False
    return t1 - t0 > 1e-12


def _occlusion_breaks(p0, h, e, corners) -> list:
    """見える/見えないが切り替わり得る前進量 s の候補(0、角をかすめる視線と進路の交点、進路と辺の交点)。閉形式。"""
    cands = [0.0]
    for cn in corners:
        M = np.array([[h[0], -(cn[0] - e[0])], [h[1], -(cn[1] - e[1])]])
        det = M[0, 0] * M[1, 1] - M[0, 1] * M[1, 0]
        if abs(det) < 1e-14:
            continue
        rhs = e - p0
        s_c = (rhs[0] * M[1, 1] - M[0, 1] * rhs[1]) / det
        if s_c > 0:
            cands.append(float(s_c))
    for k in range(4):                         # 進路と箱の辺の交点(目が箱を通り抜ける配置への備え)
        a, b = corners[k], corners[(k + 1) % 4]
        M = np.array([[h[0], -(b[0] - a[0])], [h[1], -(b[1] - a[1])]])
        det = M[0, 0] * M[1, 1] - M[0, 1] * M[1, 0]
        if abs(det) < 1e-14:
            continue
        rhs = a - p0
        s_c = (rhs[0] * M[1, 1] - M[0, 1] * rhs[1]) / det
        lam = (M[0, 0] * rhs[1] - rhs[0] * M[1, 0]) / det
        if s_c > 0 and -1e-12 <= lam <= 1 + 1e-12:
            cands.append(float(s_c))
    return cands


def occlusion_reveal_distance(ego_xy, ego_heading: float, parked_box, emerge_xy) -> float:
    """路肩駐車車両(向きつきの箱)の陰にある点 ``emerge_xy`` が、自車の目から **初めて見える** ときの縦距離。

    自車の目は p(s) = ego_xy + s h(h = (cos ψ, sin ψ)、s ≥ 0 = 前進量)を動く。視線 = 線分 p(s) → e が箱の内部を
    通らなければ見える。箱は凸なので「見えない s」は区間になり、その端は **視線が箱の角をかすめる** か、進路が箱の辺を
    横切る所。各角 c について直線 e + λ(c − e) と進路の交点 s_c を 2×2 の連立で解き(閉形式)、候補 {0, s_c, 進路と辺の
    交点} の小さい順に見えるかを調べ、最初に見える s* で d = h · (e − p(s*)) を返す。

    軸平行の例(進路 y = 0、+x 向き、陰を作る角 c、e は箱の向こう): d = (e_x − c_x) · e_y / (e_y − c_y)。

    ``parked_box`` = (cx, cy, length, width, yaw)(中心・全長・全幅・向き)。最初から見えていれば s* = 0 の縦距離、
    どこまで進んでも見えない(e が箱の内部)なら ``inf``。d が負(見えた時には既に e を通り過ぎている)もそのまま返す。
    角をかすめる視線は「見える」(箱を 1e-9 相対だけ縮めて判定し、浮動小数の揺れで判定が割れないようにする)。

    **Raises** ``ValueError``: 形・非有限・寸法 ≤ 0。"""
    op = "occlusion_reveal_distance"
    p0 = _xy(ego_xy, "ego_xy", op)
    psi = _finite(ego_heading, "ego_heading", op)
    e = _xy(emerge_xy, "emerge_xy", op)
    cx, cy, L, Wd, yaw = _box(parked_box, op)
    eps = 1e-9 * max(L, Wd)
    h = np.array([math.cos(psi), math.sin(psi)])
    corners = _box_corners(cx, cy, L, Wd, yaw)
    # e が箱の内部なら決して見えない
    c, s = math.cos(yaw), math.sin(yaw)
    ex, ey = c * (e[0] - cx) + s * (e[1] - cy), -s * (e[0] - cx) + c * (e[1] - cy)
    if abs(ex) < L / 2 - eps and abs(ey) < Wd / 2 - eps:
        return math.inf
    cands = _occlusion_breaks(p0, h, e, corners)
    # 見える/見えないは候補の間では変わらない → 候補そのものと、次の候補との中点(最後は十分先)を順に調べる
    cs = sorted(set(cands))
    s_far = cs[-1] + 1.0 + float(np.linalg.norm(e - p0))
    for i, s_c in enumerate(cs):
        if not _segment_blocked(p0 + s_c * h, e, cx, cy, L, Wd, yaw, eps):
            return float(h @ (e - (p0 + s_c * h)))
        s_mid = 0.5 * (s_c + (cs[i + 1] if i + 1 < len(cs) else s_far))
        if not _segment_blocked(p0 + s_mid * h, e, cx, cy, L, Wd, yaw, eps):
            return float(h @ (e - (p0 + s_c * h)))      # 開区間の左端 = 境目で見え始める
    return math.inf


def occlusion_visible_intervals(ego_xy, ego_heading: float, parked_box, emerge_xy, s_max: float) -> list:
    """自車の目が p(s) = ego_xy + s h を 0 ≤ s ≤ s_max 進む間に、点 ``emerge_xy`` が **見えている** 前進量の区間の列。

    ``occlusion_reveal_distance`` は「最初に見える所」だけを返すが、見え方は単調でない: 駐車車両の幅の帯の外(歩道の上)の点は、
    遠くからは車と縁石の隙間越しに見え、近づくと隠れ、また見える。ここでは見える/見えないが切り替わり得る候補(角をかすめる視線と
    進路の交点、進路と辺の交点 —— 閉形式)で [0, s_max] を区切り、各区間の中点で視線を判定して、見える区間を [(s0, s1), ...]
    (昇順、隣り合う見える区間は結合)で返す。区間の端の縦距離は h · (e − p(s))。点が箱の内部なら []。

    **Raises** ``ValueError``: 形・非有限・寸法 ≤ 0、s_max ≤ 0。"""
    op = "occlusion_visible_intervals"
    p0 = _xy(ego_xy, "ego_xy", op)
    psi = _finite(ego_heading, "ego_heading", op)
    e = _xy(emerge_xy, "emerge_xy", op)
    s_max = _positive(s_max, "s_max", op)
    cx, cy, L, Wd, yaw = _box(parked_box, op)
    eps = 1e-9 * max(L, Wd)
    h = np.array([math.cos(psi), math.sin(psi)])
    c, sn = math.cos(yaw), math.sin(yaw)
    ex, ey = c * (e[0] - cx) + sn * (e[1] - cy), -sn * (e[0] - cx) + c * (e[1] - cy)
    if abs(ex) < L / 2 - eps and abs(ey) < Wd / 2 - eps:
        return []
    cands = _occlusion_breaks(p0, h, e, _box_corners(cx, cy, L, Wd, yaw))
    pts = sorted({0.0, s_max} | {float(v) for v in cands if 0.0 < v < s_max})
    out = []
    for a, b in zip(pts[:-1], pts[1:]):
        if not _segment_blocked(p0 + 0.5 * (a + b) * h, e, cx, cy, L, Wd, yaw, eps):
            if out and out[-1][1] == a:
                out[-1] = (out[-1][0], b)
            else:
                out.append((a, b))
    return out


def occlusion_safe_speed(d, *, reaction: float, brake: float):
    """見えた瞬間から距離 d 以内に止まれる最大速度 v = b(−ρ + sqrt(ρ² + 2d/b))。

    v ρ + v²/(2b) = d(空走 + 制動。``rsssafety.rss_stopping_distance(v, ρ, accel=0, brake=b)`` と同じ式)を v について
    解いた正の根。桁落ちを避けて v = 2d / (ρ + sqrt(ρ² + 2d/b)) で計算する(ρ = 0 で sqrt(2 b d))。
    d は配列でもよい。d ≤ 0 なら 0(見えた時には既に間に合わない)。

    門: ``rss_stopping_distance(v, ρ, 0, b)`` == d(第 2 実装、rtol 1e-12)。

    **Raises** ``ValueError``: reaction < 0、brake ≤ 0、d が非有限(inf は許して inf を返す)。"""
    op = "occlusion_safe_speed"
    rho = _nonneg(reaction, "reaction", op)
    b = _positive(brake, "brake", op)
    da = _array(d, "d", op, allow_inf=True)
    if np.any(da == -np.inf):
        raise ValueError("%s: d must not be -inf" % op)
    dp = np.maximum(da, 0.0)
    with np.errstate(invalid="ignore"):
        v = np.where(np.isinf(dp), np.inf, 2.0 * dp / (rho + np.sqrt(rho * rho + 2.0 * np.where(np.isinf(dp), 0, dp) / b)))
    v = np.where(dp == 0, 0.0, v)
    return float(v) if v.ndim == 0 else v


# ---- 10. はみ出し追い越し -------------------------------------------------------------------------------
def passing_gap_required(parked_len: float, margin_front: float, margin_back: float, v_ego: float,
                         v_oncoming: float, *, lane_change_time: float, ego_length: float = 0.0,
                         pet_min: float = 0.0, v_obstacle: float = 0.0) -> Dict[str, float]:
    """駐車車両を避けて対向車線にはみ出す区間を抜ける時間と、対向車がそれまでに来ない境目の距離(閉形式)。

    自車は駐車車両の後端の ``margin_back`` 手前(x_in)で対向車線に出始め、前端の ``margin_front`` 先(x_out)を
    過ぎてから ``lane_change_time`` かけて自車線へ戻り切る。はみ出す長さ L_occ = margin_back + parked_len +
    margin_front + ego_length、はみ出している時間 t_occ = L_occ / v_ego + T_lc。戻り切った地点
    P = x_in + L_occ + v_ego T_lc に対向車が着くのが戻り切った時刻より ``pet_min`` 以上後(PET ≥ pet_min)である
    ための、判断時(自車が x_in)の対向車までの距離の境目:

        D* = t_occ (v_ego + v_on) + v_on · pet_min

    **走っている障害物**(自転車など、同じ向きに ``v_obstacle`` で進む): はみ出す長さは障害物に対する相対の距離なので
    t_occ = L_occ / (v_ego − v_obstacle) + T_lc、戻り切った地点 P = x_in + v_ego t_occ。D* の式は同じ形。
    v_obstacle = 0 で止まっている車の式に戻る。

    戻り値 dict: ``L_occ``, ``t_occupy``, ``d_required`` (= D*)、``clear_point``(x_in から P までの距離)。

    **Raises** ``ValueError``: 負の長さ・余裕、v_ego ≤ 0、v_oncoming < 0、lane_change_time < 0、
    v_obstacle < 0 か v_obstacle ≥ v_ego(追いつけない)。"""
    op = "passing_gap_required"
    L = _nonneg(parked_len, "parked_len", op)
    mf = _nonneg(margin_front, "margin_front", op)
    mb = _nonneg(margin_back, "margin_back", op)
    ve = _positive(v_ego, "v_ego", op)
    vo = _nonneg(v_oncoming, "v_oncoming", op)
    tlc = _nonneg(lane_change_time, "lane_change_time", op)
    el = _nonneg(ego_length, "ego_length", op)
    pm = _nonneg(pet_min, "pet_min", op)
    vb = _nonneg(v_obstacle, "v_obstacle", op)
    if not vb < ve:
        raise ValueError("%s: v_obstacle (%r) must be below v_ego (%r) to overtake" % (op, vb, ve))
    L_occ = mb + L + mf + el
    t_occ = L_occ / (ve - vb) + tlc
    return {"L_occ": L_occ, "t_occupy": t_occ, "d_required": t_occ * (ve + vo) + vo * pm,
            "clear_point": ve * t_occ}


def passing_decision(dist_oncoming: float, parked_len: float, margin_front: float, margin_back: float,
                     v_ego: float, v_oncoming: float, *, lane_change_time: float, ego_length: float = 0.0,
                     pet_min: float = 0.0, v_obstacle: float = 0.0) -> str:
    """対向車までの距離 ``dist_oncoming``(判断時、自車が x_in にいるとき)で "go" か "wait" を返す。

    D ≥ D*(``passing_gap_required`` の ``d_required``)なら "go"(境目ちょうどは PET = pet_min で go)。
    ``dist_oncoming = +inf`` は「対向車なし」= "go"(他の引数の検査はする)。−inf・NaN は ValueError。
    ``v_obstacle`` > 0 は走っている障害物(``passing_gap_required``)。
    門: D* ± ε で判断が切り替わる / ``passing_simulate`` の PET が pet_min になる境目と D* が一致。"""
    op = "passing_decision"
    req = passing_gap_required(parked_len, margin_front, margin_back, v_ego, v_oncoming,
                               lane_change_time=lane_change_time, ego_length=ego_length, pet_min=pet_min,
                               v_obstacle=v_obstacle)
    if (isinstance(dist_oncoming, (int, float, np.floating)) and not isinstance(dist_oncoming, bool)
            and float(dist_oncoming) == math.inf):
        return "go"
    D = _finite(dist_oncoming, "dist_oncoming", op)
    return "go" if D >= req["d_required"] else "wait"


def _lateral_return(tau: float, tlc: float) -> float:
    """自車線へ戻る横位置(1 = 対向車線、0 = 戻り切った)= 1 − smoothstep(τ/T_lc)。"""
    u = min(1.0, max(0.0, tau / tlc))
    return 1.0 - u * u * (3.0 - 2.0 * u)


def passing_simulate(dist_oncoming: float, parked_len: float, margin_front: float, margin_back: float,
                     v_ego: float, v_oncoming: float, *, lane_change_time: float, ego_length: float = 0.0,
                     dt: float = 0.01, v_obstacle: float = 0.0) -> Dict[str, float]:
    """"go" にした場合を時間を進めて走らせ、PET(自車が対向車線から戻り切った時刻と、対向車がその地点に着く時刻の差)を返す。

    閉形式と独立な経路: 自車の **横位置** を、x_in〜x_out の間は対向車線(y = 1)、x_out を過ぎたら
    y(τ) = 1 − smoothstep(τ / T_lc)(τ = x_out を過ぎてからの時間)で戻すとして刻み dt で進め、y が 0 になった刻みを
    探して刻み内を二分法で詰めた時刻を戻り切った時刻とする(T_lc = 0 なら x_out を過ぎた時刻)。対向車は x = D から
    −v_on で進め、戻り切った地点を通る刻みを探して線形補間する。v_on = 0 なら PET = inf。

    ``v_obstacle`` > 0: 障害物の前端の外(x_out)も v_obstacle で進む(走っている自転車の追い越し)。

    戻り値 dict: ``t_clear``、``x_clear``、``t_oncoming``(対向車が x_clear に着く時刻)、``pet``。"""
    op = "passing_simulate"
    D = _finite(dist_oncoming, "dist_oncoming", op)
    L = _nonneg(parked_len, "parked_len", op)
    mf = _nonneg(margin_front, "margin_front", op)
    mb = _nonneg(margin_back, "margin_back", op)
    ve = _positive(v_ego, "v_ego", op)
    vo = _nonneg(v_oncoming, "v_oncoming", op)
    tlc = _nonneg(lane_change_time, "lane_change_time", op)
    el = _nonneg(ego_length, "ego_length", op)
    dt = _positive(dt, "dt", op)
    vb = _nonneg(v_obstacle, "v_obstacle", op)
    if not vb < ve:
        raise ValueError("%s: v_obstacle must be below v_ego" % op)
    x_out = mb + L + mf + el                      # x_in = 0(障害物が走っていれば x_out も vb で進む)
    t = 0.0
    x = 0.0
    t_clear = x_clear = None
    t_pass_out = None
    while t_clear is None:
        t_n = t + dt
        x_n = x + ve * dt
        if t_pass_out is None and x_n >= x_out + vb * t_n:
            t_pass_out = t + (x_out + vb * t - x) / (ve - vb)
            if tlc == 0.0:
                t_clear, x_clear = t_pass_out, x + ve * (t_pass_out - t)
                break
        if t_pass_out is not None:
            y_n = _lateral_return(t_n - t_pass_out, tlc)
            if y_n <= 0.0:
                # この刻みの中で y が 0 になる時刻を二分法で(y は単調非増加)
                lo, hi = max(t, t_pass_out), t_n
                for _ in range(200):
                    mid = 0.5 * (lo + hi)
                    if _lateral_return(mid - t_pass_out, tlc) > 0.0:
                        lo = mid
                    else:
                        hi = mid
                    if hi - lo <= 1e-13 * max(1.0, hi):
                        break
                t_clear = hi
                x_clear = x + (hi - t) * ve
                break
        t, x = t_n, x_n
        if t > 1e7:
            raise ValueError("%s: simulation did not terminate" % op)
    if vo == 0.0:
        return {"t_clear": t_clear, "x_clear": x_clear, "t_oncoming": math.inf, "pet": math.inf}
    to = 0.0
    xo = D
    if xo <= x_clear:
        t_on = 0.0 - (x_clear - xo) / vo          # 既に通り過ぎている(負の時刻)
    else:
        while True:
            xo_n = xo - vo * dt
            if xo_n <= x_clear:
                t_on = to + (xo - x_clear) / (xo - xo_n) * dt
                break
            to, xo = to + dt, xo_n
    return {"t_clear": t_clear, "x_clear": x_clear, "t_oncoming": t_on, "pet": t_on - t_clear}


# ---- 11. 非一様ポアソン過程 ---------------------------------------------------------------------------
def bus_stop_rate(x, *, bus_rear: float, bus_front: float, base: float, peak: float, spread: float):
    """停車中のバスの前後で高い出現率 λ(x) = base + peak [exp(−½((x − rear)/spread)²) + exp(−½((x − front)/spread)²)]
    [件/m]。バスの陰(前端の先)と後ろから人が出てくる、という形の例(値は呼び出し側の仮定)。上限は base + 2·peak。"""
    op = "bus_stop_rate"
    xa = _array(x, "x", op)
    base = _nonneg(base, "base", op)
    peak = _nonneg(peak, "peak", op)
    spread = _positive(spread, "spread", op)
    r = _finite(bus_rear, "bus_rear", op)
    f = _finite(bus_front, "bus_front", op)
    out = base + peak * (np.exp(-0.5 * ((xa - r) / spread) ** 2) + np.exp(-0.5 * ((xa - f) / spread) ** 2))
    return float(out) if out.ndim == 0 else out


def _eval_rate(rate_fn, x: np.ndarray, op: str, name: str = "rate_fn") -> np.ndarray:
    lam = np.asarray(rate_fn(x), dtype=float)
    if lam.shape != x.shape:
        lam = np.broadcast_to(lam, x.shape).astype(float)
    if not np.all(np.isfinite(lam)) or np.any(lam < 0):
        raise ValueError("%s: %s must return finite non-negative rates" % (op, name))
    return lam


def _thinning(rate_fn, x_max: float, rate_max: float, rng, op: str) -> np.ndarray:
    n_c = rng.poisson(rate_max * x_max)
    xc = np.sort(rng.uniform(0.0, x_max, size=n_c))
    if n_c == 0:
        return xc
    lam = _eval_rate(rate_fn, xc, op)
    if np.any(lam > rate_max * (1 + 1e-12)):
        raise ValueError("%s: rate_fn exceeds rate_max (max seen %r > %r)" % (op, float(lam.max()), rate_max))
    u = rng.uniform(0.0, 1.0, size=n_c)
    return xc[u * rate_max < lam]


def _check_rate_grid(rate_fn, axes, rate_max: float, op: str) -> None:
    """格子の上で rate_fn ≤ rate_max を事前に確かめる(fail-closed)。候補点だけの検査は、狭い山を候補が外すと違反を
    見逃す(thinning は静かに少なく数える)。格子の刻みより狭い山はこれでも見逃し得る —— 刻みは呼び手が ``n_grid`` で決める。"""
    if len(axes) == 1:
        lam = _eval_rate(rate_fn, axes[0], op)
    else:
        X, T = np.meshgrid(axes[0], axes[1], indexing="ij")
        lam = np.asarray(rate_fn(X, T), dtype=float)
        if lam.shape != X.shape:
            lam = np.broadcast_to(lam, X.shape).astype(float)
        if not np.all(np.isfinite(lam)) or np.any(lam < 0):
            raise ValueError("%s: rate_fn must return finite non-negative rates" % op)
    if lam.max() > rate_max * (1 + 1e-12):
        raise ValueError("%s: rate_fn exceeds rate_max on the check grid (max %r > %r)" % (op, float(lam.max()), rate_max))


def _grid_n(n_grid, op: str) -> int:
    if isinstance(n_grid, bool) or not isinstance(n_grid, (int, np.integer)) or n_grid < 2:
        raise ValueError("%s: n_grid must be an int >= 2" % op)
    return int(n_grid)


def poisson_events(rate_fn: Callable, x_max: float, *, rate_max: float, seed, n_grid: int = 2001) -> np.ndarray:
    """[0, x_max] の非一様ポアソン過程を thinning(Lewis & Shedler 1979)で 1 本引く(昇順の位置の配列)。

    率 rate_max の一様ポアソン過程の候補を引き、各候補 x を確率 λ(x)/rate_max で残す。残った点は率 λ の非一様
    ポアソン過程 → 件数 N ~ Poisson(Λ)、Λ = ∫₀^{x_max} λ(x) dx(門: 多数の試行で平均 = 分散 = Λ、位置の分布 = λ/Λ)。
    ``rate_fn`` は numpy 配列を受けて同じ形の率を返す関数。**引く前に** ``n_grid`` 点の等間隔格子で λ ≤ rate_max を確かめ、
    引いた候補の所でも確かめる。どちらかで超えれば ValueError(fail-closed。上限を守らないと thinning は静かに少なく数える)。
    ``seed`` は int か ``np.random.Generator``。"""
    op = "poisson_events"
    if not callable(rate_fn):
        raise ValueError("%s: rate_fn must be callable" % op)
    x_max = _positive(x_max, "x_max", op)
    rate_max = _positive(rate_max, "rate_max", op)
    _check_rate_grid(rate_fn, [np.linspace(0.0, x_max, _grid_n(n_grid, op))], rate_max, op)
    rng = seed if isinstance(seed, np.random.Generator) else np.random.default_rng(seed)
    return _thinning(rate_fn, x_max, rate_max, rng, op)


def poisson_events_xt(rate_fn: Callable, x_max: float, t_max: float, *, rate_max: float, seed,
                      n_grid=(201, 201)) -> np.ndarray:
    """[0, x_max] × [0, t_max] の時空の非一様ポアソン過程(率 λ(x, t) [件/(m·s)])を thinning で 1 本引く。

    停車中のバスのように、出現率が場所と時刻の両方に依る場合(λ(x, t) = bus_stop_rate(x) · [t < 発車] + base)。
    率 rate_max の一様な候補(件数 ~ Poisson(rate_max · x_max · t_max)、位置・時刻は一様)を確率 λ/rate_max で残す。
    件数 ~ Poisson(Λ)、Λ = ∫∫λ dx dt。``rate_fn(x, t)`` は同じ形の配列 2 つを受けて率を返す関数。
    **引く前に** ``n_grid = (nx, nt)`` の格子で λ ≤ rate_max を確かめ、候補の所でも確かめる(超えれば ValueError)。

    戻り値: (N, 2) の配列 [[x, t], ...] (時刻の昇順)。"""
    op = "poisson_events_xt"
    if not callable(rate_fn):
        raise ValueError("%s: rate_fn must be callable" % op)
    x_max = _positive(x_max, "x_max", op)
    t_max = _positive(t_max, "t_max", op)
    rate_max = _positive(rate_max, "rate_max", op)
    try:
        nx, nt = n_grid
    except (TypeError, ValueError):
        raise ValueError("%s: n_grid must be a pair (nx, nt)" % op) from None
    _check_rate_grid(rate_fn, [np.linspace(0.0, x_max, _grid_n(nx, op)), np.linspace(0.0, t_max, _grid_n(nt, op))],
                     rate_max, op)
    rng = seed if isinstance(seed, np.random.Generator) else np.random.default_rng(seed)
    n_c = rng.poisson(rate_max * x_max * t_max)
    xc = rng.uniform(0.0, x_max, size=n_c)
    tc = rng.uniform(0.0, t_max, size=n_c)
    if n_c == 0:
        return np.zeros((0, 2))
    lam = np.asarray(rate_fn(xc, tc), dtype=float)
    if lam.shape != xc.shape:
        lam = np.broadcast_to(lam, xc.shape).astype(float)
    if not np.all(np.isfinite(lam)) or np.any(lam < 0):
        raise ValueError("%s: rate_fn must return finite non-negative rates" % op)
    if np.any(lam > rate_max * (1 + 1e-12)):
        raise ValueError("%s: rate_fn exceeds rate_max (max seen %r > %r)" % (op, float(lam.max()), rate_max))
    keep = rng.uniform(0.0, 1.0, size=n_c) * rate_max < lam
    out = np.column_stack([xc[keep], tc[keep]])
    return out[np.argsort(out[:, 1], kind="stable")]


# ---- 12. 重要度サンプリング -------------------------------------------------------------------------------
def importance_risk_estimate(simulate_fn: Callable, base_rate: Callable, boosted_rate: Callable, n_runs: int,
                             seed, *, x_max: float, boosted_rate_max: float, n_grid: int = 20001
                             ) -> Dict[str, float]:
    """出現率を上げた試行(率 λ')で事故を起こしやすくし、尤度比の重みで本来の率 λ の事故確率に戻す。

    1 回の試行 = ``poisson_events(boosted_rate)`` で出現位置 x_1..x_N を引き、``simulate_fn(events, rng)`` が事故なら 1
    (bool か [0, 1] の値)。重み(ポアソン過程の Radon–Nikodym 微分 dP_λ/dP_λ'):

        w = Π_i λ(x_i)/λ'(x_i) · exp(−(Λ − Λ')),   Λ = ∫λ, Λ' = ∫λ'(台形、n_grid 点)

    推定 p̂ = mean(w · Y)、標準誤差 = std(w · Y)/sqrt(n)。``boosted_rate`` を ``base_rate`` と同じにすれば w ≡ 1 で
    素朴なモンテカルロになる(門ではこれと、事故確率が閉形式で分かる simulate_fn とで比べる)。
    λ > 0 なのに λ' = 0 の所があると推定が偏る(絶対連続でない)ので格子上で検査して ValueError。

    戻り値 dict: ``estimate``, ``std_error``, ``per_run_var``(w·Y の標本分散)、``n_runs``, ``Lambda``, ``Lambda_boost``,
    ``mean_weight``(≈ 1 のはず。重みの健全性)、``ess``(有効標本数 (Σw)²/Σw²)、``hits``(Y > 0 の回数)。"""
    op = "importance_risk_estimate"
    if not (callable(simulate_fn) and callable(base_rate) and callable(boosted_rate)):
        raise ValueError("%s: simulate_fn, base_rate, boosted_rate must be callable" % op)
    if isinstance(n_runs, bool) or not isinstance(n_runs, (int, np.integer)) or n_runs < 2:
        raise ValueError("%s: n_runs must be an int >= 2, got %r" % (op, n_runs))
    x_max = _positive(x_max, "x_max", op)
    rmax = _positive(boosted_rate_max, "boosted_rate_max", op)
    if isinstance(n_grid, bool) or not isinstance(n_grid, (int, np.integer)) or n_grid < 3:
        raise ValueError("%s: n_grid must be an int >= 3" % op)
    xg = np.linspace(0.0, x_max, int(n_grid))
    lg = _eval_rate(base_rate, xg, op, "base_rate")
    lbg = _eval_rate(boosted_rate, xg, op, "boosted_rate")
    if np.any((lg > 0) & (lbg <= 0)):
        raise ValueError("%s: boosted_rate is 0 where base_rate > 0 (not absolutely continuous)" % op)
    if lbg.max() > rmax * (1 + 1e-12):
        raise ValueError("%s: boosted_rate exceeds boosted_rate_max on the grid (max %r > %r)" % (op, float(lbg.max()), rmax))
    Lam = float(np.trapezoid(lg, xg)) if hasattr(np, "trapezoid") else float(np.trapz(lg, xg))
    Lamb = float(np.trapezoid(lbg, xg)) if hasattr(np, "trapezoid") else float(np.trapz(lbg, xg))
    rng = seed if isinstance(seed, np.random.Generator) else np.random.default_rng(seed)
    wy = np.empty(int(n_runs))
    w_all = np.empty(int(n_runs))
    hits = 0
    for r in range(int(n_runs)):
        ev = _thinning(boosted_rate, x_max, rmax, rng, op)
        if ev.size:
            with np.errstate(divide="ignore"):
                lw = float(np.sum(np.log(_eval_rate(base_rate, ev, op, "base_rate"))
                                  - np.log(_eval_rate(boosted_rate, ev, op, "boosted_rate"))))
        else:
            lw = 0.0
        w = math.exp(lw - (Lam - Lamb))
        y = float(simulate_fn(ev, rng))
        if not (0.0 <= y <= 1.0):
            raise ValueError("%s: simulate_fn must return a value in [0, 1], got %r" % (op, y))
        hits += y > 0
        wy[r] = w * y
        w_all[r] = w
    var = float(np.var(wy, ddof=1))
    return {"estimate": float(np.mean(wy)), "std_error": math.sqrt(var / n_runs), "per_run_var": var,
            "n_runs": int(n_runs), "Lambda": Lam, "Lambda_boost": Lamb, "mean_weight": float(np.mean(w_all)),
            "ess": float(np.sum(w_all) ** 2 / np.sum(w_all ** 2)), "hits": int(hits)}
