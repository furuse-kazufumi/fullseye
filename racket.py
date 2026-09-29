"""racket — 卓球のラケットと対戦ラリー(17 巡目): 自由に動くラケット 2 本で打ち合い、**続いた本数**を知覚・予測・制御の指標にする。

ラケット = 平らな板(幅 × 高さ、法線 n)が速度 v_r で動く。球との衝突は :func:`ballistics.bounce` をラケットの座標系で使う
(相対速度 v − v_r で跳ねさせて戻す = 動く平面の衝突)。定理の門: ラケットが止まっていれば台の跳ねと同じ、ラケット系の接触点
まわりの角運動量は保存、運動エネルギーはラケット系で増えない。

狙い(aim)= 目標点に時間 T で届く速度: 真空なら閉形式 v = (Δxy/T, (Δz + ½gT²)/T)、抗力・マグヌス込みなら運動方程式で数回
Gauss–Newton。打ち方(plan)= 望む v_out を出すラケットの法線と速度: 摩擦 0 なら閉形式 n ∝ v_out − v_in、v_r·n = |Δv|/(1+e) + v_in·n。
摩擦とスピンがあると衝突が違うので、実際の衝突モデルで数回反復して合わせる(不能なら残差を返す)。

ラリー(rally_simulate)= 相手コートに落ちて跳ねた球をラケット面(x = ±x_r)で迎え撃ち、相手コートを狙って返す、を繰り返す。
知覚は差し替え可能(``perceive(t, p, v, ω) → (p̂, v̂, ω̂)``、既定は真値)。終わり方: 台に落ちない・ネット・ラケットに届かない・
2 度跳ね・上限。返り値の ``hits`` がラリーの本数。

戦略(ユーザーの指定、2026-09-29): 一方は **勝つための打ち方**(:func:`strategy_attacker`: 相手から遠い隅を速く、スピンを変える)、
もう一方は **前回に近いがわずかにずらした位置へ返す**(:func:`strategy_feeder`)。**巻き戻し**: 打つ前に真の物理で先読みし
(:func:`shot_is_legal`: ネットを越え、相手コートに 1 度落ち、相手の面に打てる高さで届く)、外すなら時間を戻して別の狙いで
やり直す(``retries`` 回まで。使った回数が shots[k]["rewinds"] に残る = 計画のモデルが真の物理からどれだけ外れたかの指標)。
"""
from __future__ import annotations

import numpy as np

import ballistics as B

__all__ = ["racket_params", "racket_impact", "racket_hit_check", "aim_velocity", "racket_plan", "racket_move", "rally_simulate",
           "strategy_attacker", "strategy_feeder", "shot_is_legal"]


def _v3(x, name="vector"):
    a = np.asarray(x, np.float64).reshape(-1)
    if a.shape != (3,) or not np.all(np.isfinite(a)):
        raise ValueError("%s must be a finite (3,) vector" % name)
    return a


def _unit(x, name="normal"):
    a = _v3(x, name)
    nrm = float(np.linalg.norm(a))
    if nrm < 1e-12:
        raise ValueError("%s must be non-zero" % name)
    return a / nrm


def racket_params(width: float = 0.15, height: float = 0.16, e: float = 0.8, mu: float = 0.6, v_max: float = 6.0,
                  a_max: float = 60.0) -> dict:
    """ラケットの表: 板の幅・高さ [m]、ラバーの反発係数 e と摩擦係数 μ、動きの上限(速さ v_max [m/s]、加速度 a_max [m/s²])。"""
    if min(width, height, v_max, a_max) <= 0 or not (0 <= e <= 1) or mu < 0:
        raise ValueError("width, height, v_max, a_max > 0; 0 ≤ e ≤ 1; μ ≥ 0")
    return {"width": float(width), "height": float(height), "e": float(e), "mu": float(mu), "v_max": float(v_max),
            "a_max": float(a_max)}


def racket_impact(v, omega, normal, v_racket, bp: dict, rp: dict) -> dict:
    """動くラケット(法線 n、速度 v_r)に球が当たる: ラケット系の相対速度で :func:`ballistics.bounce` → 戻す。
    返り値 = bounce と同じ + ``"v_rel_in"``。n は球の側を向く(球が n と逆向きに近づく)。"""
    v = _v3(v, "v")
    vr = _v3(v_racket, "v_racket")
    n = _unit(normal, "normal")
    rel = v - vr
    b = B.bounce(rel, omega, n, bp, B.impact_params(rp["e"], rp["mu"]))
    b["v"] = b["v"] + vr
    b["v_rel_in"] = rel
    return b


def racket_hit_check(p_ball, center, normal, rp: dict, radius: float, up=(0.0, 0.0, 1.0)) -> dict:
    """球の中心が板の面から ``radius`` 以内で、板の枠(幅 × 高さ + 半径)の中にあるか。``{"hit", "dist", "u", "v"}``
    (u = 幅方向、v = 高さ方向の板の中心からのずれ)。"""
    p = _v3(p_ball, "p_ball")
    c = _v3(center, "center")
    n = _unit(normal, "normal")
    upv = _v3(up, "up")
    ev = upv - (upv @ n) * n
    if np.linalg.norm(ev) < 1e-9:
        ev = np.array([0.0, 0.0, 1.0])
    ev = ev / np.linalg.norm(ev)
    eu = np.cross(ev, n)
    d = p - c
    dist = float(d @ n)
    u = float(d @ eu)
    vv = float(d @ ev)
    hit = abs(dist) <= radius and abs(u) <= rp["width"] / 2 + radius and abs(vv) <= rp["height"] / 2 + radius
    return {"hit": bool(hit), "dist": dist, "u": u, "v": vv}


def aim_velocity(p, target, T: float, bp: dict, omega=(0.0, 0.0, 0.0), refine: int = 6, dt: float = 1e-3) -> dict:
    """点 p から時間 T で target に届く初速。真空の閉形式 v = (Δxy/T, (Δz + ½gT²)/T) を初期値に、抗力 + マグヌス(ω)の
    運動方程式で ``refine`` 回 Gauss–Newton(有限差分)。``{"v", "residual"}``(residual = 到達点のずれ [m])。"""
    p = _v3(p, "p")
    q = _v3(target, "target")
    if T <= 0:
        raise ValueError("T must be positive")
    d = q - p
    v = np.array([d[0] / T, d[1] / T, (d[2] + 0.5 * bp["g"] * T * T) / T])
    if bp["rho"] <= 0 or refine <= 0:
        return {"v": v, "residual": 0.0}
    w = _v3(omega, "omega")

    def end(v):
        f = B.flight_ode(p, v, w, bp, T + dt, dt)
        return np.array([np.interp(T, f["t"], f["p"][:, k]) for k in range(3)])

    res = end(v) - q
    for _ in range(refine):
        J = np.empty((3, 3))
        for j in range(3):
            vp = v.copy()
            vp[j] += 1e-5
            J[:, j] = (end(vp) - q - res) / 1e-5
        v = v - np.linalg.solve(J, res)
        res = end(v) - q
        if np.linalg.norm(res) < 1e-9:
            break
    return {"v": v, "residual": float(np.linalg.norm(res))}


def racket_plan(v_in, omega_in, v_out, bp: dict, rp: dict, refine: int = 8) -> dict:
    """望む v_out を出すラケットの法線 n と速度 v_r(法線方向)。摩擦 0 の閉形式 n ∝ v_out − v_in、
    v_r·n = |Δv|/(1+e) + v_in·n を初期値に、実際の衝突(摩擦・スピン込み)で ``refine`` 回反復。
    返り値 ``{"normal", "v_racket", "v_out_actual", "omega_out", "residual"}``。Δv ≈ 0 なら ValueError。"""
    vi = _v3(v_in, "v_in")
    vo = _v3(v_out, "v_out")
    w = _v3(omega_in, "omega_in")
    want = vo - vi
    if np.linalg.norm(want) < 1e-9:
        raise ValueError("v_out equals v_in; nothing to plan")
    dv = want.copy()
    best = None
    for _ in range(max(1, refine)):
        n = dv / np.linalg.norm(dv)
        s = np.linalg.norm(dv) / (1.0 + rp["e"]) + vi @ n
        vr = s * n
        b = racket_impact(vi, w, n, vr, bp, rp)
        res = vo - b["v"]
        if best is None or np.linalg.norm(res) < best["residual"]:
            best = {"normal": n, "v_racket": vr, "v_out_actual": b["v"], "omega_out": b["omega"], "residual": float(np.linalg.norm(res))}
        if np.linalg.norm(res) < 1e-9:
            break
        dv = dv + res
    return best


def racket_move(pos, vel, target, dt: float, rp: dict) -> tuple:
    """ラケットを target へ動かす(速さ・加速度の上限つきの bang-bang: 止まれる距離を見て減速)。返り値 (pos, vel)。"""
    pos = _v3(pos, "pos")
    vel = _v3(vel, "vel")
    tgt = _v3(target, "target")
    d = tgt - pos
    dist = float(np.linalg.norm(d))
    if dist < 1e-9:
        return tgt.copy(), np.zeros(3)
    u = d / dist
    v_stop = max(0.0, np.sqrt(2.0 * rp["a_max"] * dist) - rp["a_max"] * dt)   # 止まれる最大の速さ(離散の 1 歩ぶん引く)
    v_des = min(rp["v_max"], v_stop) * u
    dv = v_des - vel
    dvn = float(np.linalg.norm(dv))
    if dvn > rp["a_max"] * dt:
        dv = dv * (rp["a_max"] * dt / dvn)
    vel2 = vel + dv
    pos2 = pos + vel2 * dt
    if float((tgt - pos2) @ u) < 0:                          # 行き過ぎたら目標に置く
        return tgt.copy(), vel2 * 0.0
    return pos2, vel2


def strategy_attacker(side: int, ctx: dict, rng) -> dict:
    """勝つための打ち方: 相手のラケットから遠い隅(左右の端、前後を交互)へ、短い滞空時間で。スピンの狙いも交互に変える。
    ``ctx`` = {"opp_pos" (3,), "shot_index", "tp"}。返り値 {"target" (x, y), "T", "spin"}。"""
    tp = ctx["tp"]
    L, Wd = tp["length"], tp["width"]
    sign = 1.0 if side == 0 else -1.0
    y_opp = ctx["opp_pos"][1]
    y = -np.sign(y_opp) * (Wd / 2 - 0.10) if abs(y_opp) > 0.02 else rng.choice([-1.0, 1.0]) * (Wd / 2 - 0.10)
    deep = ctx["shot_index"] % 2 == 0
    x = sign * ((L / 2 - 0.12) if deep else 0.30)
    T = 0.30 if deep else 0.26
    return {"target": (x, y), "T": T, "spin": "topspin" if ctx["shot_index"] % 3 else "flat"}


def strategy_feeder(side: int, ctx: dict, rng, step: float = 0.06) -> dict:
    """前回に近いがわずかにずらした位置へ返す(相手が取りやすい球): 前回の自分の狙いから ±step の一様乱数で動かし、
    コートの内側(端から 12 cm)に収める。滞空時間はゆっくり 0.42 s。"""
    tp = ctx["tp"]
    L, Wd = tp["length"], tp["width"]
    sign = 1.0 if side == 0 else -1.0
    prev = ctx.get("prev_target")
    if prev is None:
        prev = (sign * 0.75, 0.0)
    x = float(np.clip(prev[0] + rng.uniform(-step, step), *sorted((sign * 0.25, sign * (L / 2 - 0.12)))))
    y = float(np.clip(prev[1] + rng.uniform(-step, step), -Wd / 2 + 0.12, Wd / 2 - 0.12))
    return {"target": (x, y), "T": 0.42, "spin": "flat"}


def shot_is_legal(p, v, w, bp, ip, tp, x_racket: float, side: int, hit_height=(0.05, 0.45)) -> dict:
    """打球 (p, v, ω) を真の物理で先読みして、ネットを越え・相手コートに 1 度だけ落ち・相手の面 x = ∓x_r に打てる高さで
    届くかを判定する。``{"legal", "reason", "p_arrive", "t_arrive"}``。"""
    H = tp["height"]
    L, Wd = tp["length"], tp["width"]
    r = bp["radius"]
    x_opp = x_racket if side == 0 else -x_racket
    pr = B.flight_simulate(p, v, w, bp, ip, 1.5, 1e-3, table_z=H, table_xy=(-L / 2, L / 2, -Wd / 2, Wd / 2))
    P, V = pr["p"], pr["v"]
    # ネット
    cross = np.nonzero((P[1:, 0] > 0) != (P[:-1, 0] > 0))[0]
    if len(cross) == 0:
        return {"legal": False, "reason": "no_net_cross", "p_arrive": None, "t_arrive": None}
    k = cross[0]
    if P[k, 2] < H + tp["net_height"] + r:
        return {"legal": False, "reason": "net", "p_arrive": None, "t_arrive": None}
    # 相手コートの跳ね(1 度だけ、面に届く前)
    dx = P[:, 0] - x_opp
    arr = np.nonzero(np.sign(dx[1:]) != np.sign(dx[:-1]))[0]
    t_arr_idx = arr[0] if len(arr) else len(P) - 1
    bounces = [c for c in pr["contacts"] if c["t"] <= pr["t"][t_arr_idx]]
    if len(bounces) != 1:
        return {"legal": False, "reason": "bounce_%d" % len(bounces), "p_arrive": None, "t_arrive": None}
    if (bounces[0]["p"][0] > 0) != (x_opp > 0):
        return {"legal": False, "reason": "own_side", "p_arrive": None, "t_arrive": None}
    if len(arr) == 0:
        return {"legal": False, "reason": "no_arrival", "p_arrive": None, "t_arrive": None}
    pa = P[t_arr_idx]
    if not (H + hit_height[0] <= pa[2] <= H + hit_height[1]) or abs(pa[1]) > Wd / 2 + 0.3:
        return {"legal": False, "reason": "unreachable", "p_arrive": pa, "t_arrive": pr["t"][t_arr_idx]}
    return {"legal": True, "reason": "ok", "p_arrive": pa, "t_arrive": pr["t"][t_arr_idx]}


def rally_simulate(bp: dict, rp: dict, tp: dict, *, perceive=None, strategies=None, retries: int = 6, x_racket: float = 1.55,
                   hit_height=(0.05, 0.45), T_flight: float = 0.42, target_x: float = 0.75, max_hits: int = 60, dt: float = 2e-4,
                   fps: float = 100.0, seed: int = 0, y_jitter: float = 0.25, plan_spin: bool = True, table_ip=None,
                   replan_every: int = 5) -> dict:
    """2 本のラケット(x = −x_r と +x_r、板は相手を向く)で打ち合う。

    各コマ(1/fps)で受け手側の知覚 ``perceive(t, p, v, ω)`` が球の状態を返し、そこから運動方程式 + 台の跳ねで自分の面
    x = ±x_r への到達点・時刻を予測してラケットを動かす(上限つき)。球が面に届いたら、相手コートの (∓target_x, y*) に
    T_flight で落ちる速度を狙って打つ(y* は乱数、``plan_spin`` なら打球後のスピンを込みで狙いを合わせる)。
    ``strategies`` = (side 0 の戦略, side 1 の戦略)(None なら両方 :func:`strategy_feeder`)。``retries`` > 0 なら打つ前に
    :func:`shot_is_legal` で先読みし、外す狙いは巻き戻して別の狙い(戦略を引き直す)でやり直す。
    返り値 ``{"hits", "end_reason", "shots": [...], "t", "p" (N,3), "racket_pos" (N,2,3), "hit_times", "rewinds"}``。"""
    rng = np.random.default_rng(seed)
    H = tp["height"]
    L, Wd = tp["length"], tp["width"]
    ip = table_ip if table_ip is not None else B.impact_params(0.9, 0.25)
    r = bp["radius"]
    if perceive is None:
        perceive = lambda t, p, v, w: (p, v, w)  # noqa: E731
    # 状態
    p = np.array([-x_racket + 0.05, 0.0, H + 0.25])
    v = np.zeros(3)
    w = np.zeros(3)
    rk_pos = np.array([[-x_racket, 0.0, H + 0.25], [x_racket, 0.0, H + 0.25]])
    rk_vel = np.zeros((2, 3))
    rk_normal = np.array([[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]])
    rk_plan = [None, None]
    receiver = 0                     # 今から打つ側(最初はサーブ = 0 側がその場で打つ)
    bounces_since_hit = 0
    hits = 0
    shots = []
    T, P, RK = [], [], []
    t = 0.0
    frame_dt = 1.0 / fps
    next_frame = 0.0
    frame_no = 0
    end_reason = "max_time"
    hit_times = []
    # サーブ: 0 側のラケット位置で球を止めておき、最初の計画で打つ
    serve_pending = True
    t_max = max_hits * 1.2 + 1.0

    strategies = strategies or (strategy_feeder, strategy_feeder)
    prev_target = [None, None]
    rewinds_total = 0

    def plan_once(side, p_ball, v_ball, w_ball, choice):
        tgt = np.array([choice["target"][0], choice["target"][1], H + r])
        w_guess = np.zeros(3)
        pl = None
        for _ in range(3 if plan_spin else 1):
            aim = aim_velocity(p_ball, tgt, choice["T"], bp, w_guess)
            pl = racket_plan(v_ball, w_ball, aim["v"], bp, rp)
            if not plan_spin:
                break
            w_guess = pl["omega_out"]
        return pl, tgt

    def plan_shot(side, p_ball, v_ball, w_ball, true_state=None):
        """戦略で狙いを引き、(retries > 0 なら)真の物理で先読みして外すなら引き直す = 巻き戻し。"""
        nonlocal rewinds_total
        ctx = {"opp_pos": rk_pos[1 - side], "shot_index": hits, "tp": tp, "prev_target": prev_target[side]}
        best = None
        n_rw = 0
        for attempt in range(max(1, retries + 1)):
            choice = strategies[side](side, ctx, rng)
            pl, tgt = plan_once(side, p_ball, v_ball, w_ball, choice)
            if retries <= 0 or true_state is None:
                best = (pl, tgt, choice, n_rw)
                break
            pt, vt, wt = true_state
            b = racket_impact(vt, wt, pl["normal"], pl["v_racket"], bp, rp)
            leg = shot_is_legal(pt, b["v"], b["omega"], bp, ip, tp, x_racket, side, hit_height)
            if leg["legal"]:
                best = (pl, tgt, choice, n_rw)
                break
            n_rw += 1
            best = (pl, tgt, choice, n_rw)
        rewinds_total += n_rw
        prev_target[side] = (float(tgt[0]), float(tgt[1]))
        return best[0], best[1], best[2], best[3]

    while t < t_max:
        # ── 知覚と計画(コマごと)
        if t >= next_frame - 1e-12:
            next_frame += frame_dt
            frame_no += 1
            side = receiver
            if serve_pending:
                pl, tgt, choice, n_rw = plan_shot(0, p, v, w, true_state=(p, v, w))
                rk_plan[0] = (pl, tgt, p.copy(), t, choice, n_rw)
                rk_normal[0] = pl["normal"]
                rk_pos[0] = p.copy()
            elif frame_no % max(1, replan_every) == 0:                       # 計画は replan_every コマに 1 度(1 コマ 60 ms の計算を減らす)
                ph, vh, wh = perceive(t, p, v, w)
                # 面 x = ±x_r への到達を予測(台の跳ね込み)
                xr = -x_racket if side == 0 else x_racket
                pr = B.flight_simulate(ph, vh, wh, bp, ip, 1.2, 1e-3, table_z=H, table_xy=(-L / 2, L / 2, -Wd / 2, Wd / 2))
                dx = pr["p"][:, 0] - xr
                cross = np.nonzero(np.sign(dx[1:]) != np.sign(dx[:-1]))[0]
                if len(cross):
                    k = cross[0]
                    a = dx[k] / (dx[k] - dx[k + 1])
                    p_hit = pr["p"][k] + a * (pr["p"][k + 1] - pr["p"][k])
                    v_hit = pr["v"][k] + a * (pr["v"][k + 1] - pr["v"][k])
                    w_hit = pr["omega"][k]
                    # 先読み(巻き戻し)は真の到達状態で行う: 知覚が外れていれば計画そのものが外れる(それが測りたい量)
                    true_arr = None
                    if retries > 0:
                        pr_t = B.flight_simulate(p, v, w, bp, ip, 1.2, 1e-3, table_z=H, table_xy=(-L / 2, L / 2, -Wd / 2, Wd / 2))
                        dxt = pr_t["p"][:, 0] - xr
                        ct = np.nonzero(np.sign(dxt[1:]) != np.sign(dxt[:-1]))[0]
                        if len(ct):
                            kt = ct[0]
                            at = dxt[kt] / (dxt[kt] - dxt[kt + 1])
                            true_arr = (pr_t["p"][kt] + at * (pr_t["p"][kt + 1] - pr_t["p"][kt]),
                                        pr_t["v"][kt] + at * (pr_t["v"][kt + 1] - pr_t["v"][kt]), pr_t["omega"][kt])
                    pl, tgt, choice, n_rw = plan_shot(side, p_hit, v_hit, w_hit, true_state=true_arr)
                    rk_plan[side] = (pl, tgt, p_hit, t + pr["t"][k] + a * (pr["t"][k + 1] - pr["t"][k]), choice, n_rw)
                    rk_normal[side] = pl["normal"]
        # ── ラケットを動かす
        for side in (0, 1):
            if rk_plan[side] is not None and not (serve_pending and side == 0):
                rk_pos[side], rk_vel[side] = racket_move(rk_pos[side], rk_vel[side], rk_plan[side][2], dt, rp)
        T.append(t)
        P.append(p.copy())
        RK.append(rk_pos.copy())
        # ── 球を進める
        if serve_pending:
            pl, tgt, _, _, choice, n_rw = rk_plan[0]
            b = racket_impact(v, w, pl["normal"], pl["v_racket"], bp, rp)
            v, w = b["v"], b["omega"]
            hits += 1
            hit_times.append(t)
            shots.append({"t": t, "side": 0, "v_out": v.copy(), "omega_out": w.copy(), "target": tgt, "residual": pl["residual"],
                          "choice": choice, "rewinds": n_rw})
            serve_pending = False
            receiver = 1
            bounces_since_hit = 0
            t += dt
            continue
        st = B.flight_state_at(p, v, w, bp, dt, 1)
        p2, v2 = st["p"], st["v"]
        # 台の跳ね
        if p2[2] < H + r <= p[2] and v2[2] < 0 and abs(p2[0]) <= L / 2 and abs(p2[1]) <= Wd / 2:
            b = B.bounce(v2, w, [0, 0, 1], bp, ip)
            v2, w = b["v"], b["omega"]
            p2[2] = H + r
            bounces_since_hit += 1
            if bounces_since_hit >= 2:
                end_reason = "double_bounce"
                p, v = p2, v2
                break
            if (p2[0] < 0) != (receiver == 0):
                end_reason = "wrong_side_bounce"
                p, v = p2, v2
                break
        # ネット
        if (p2[0] > 0) != (p[0] > 0) and p2[2] < H + tp["net_height"] + r and abs(p2[1]) <= tp["net_length"] / 2:
            end_reason = "net"
            p, v = p2, v2
            break
        # ラケットに当たる
        side = receiver
        chk = racket_hit_check(p2, rk_pos[side], rk_normal[side], rp, r)
        approaching = (v2 @ rk_normal[side]) < 0
        if chk["hit"] and approaching and rk_plan[side] is not None:
            if bounces_since_hit == 0:
                end_reason = "volley"                       # 自分のコートで跳ねる前に打った(反則)
                p, v = p2, v2
                break
            pl, tgt, _, _, choice, n_rw = rk_plan[side]
            v_sw = pl["v_racket"]
            clipped = float(np.linalg.norm(v_sw)) > rp["v_max"]
            if clipped:                                              # 振りの速さは上限まで(位置追従とは別の「振り」だが上限は同じ)
                v_sw = v_sw * (rp["v_max"] / np.linalg.norm(v_sw))
            b = racket_impact(v2, w, rk_normal[side], v_sw, bp, rp)
            v2, w = b["v"], b["omega"]
            hits += 1
            hit_times.append(t)
            shots.append({"t": t, "side": side, "v_out": v2.copy(), "omega_out": w.copy(), "target": tgt, "residual": pl["residual"],
                          "offset": (chk["u"], chk["v"]), "choice": choice, "rewinds": n_rw, "swing_clipped": clipped})
            receiver = 1 - side
            bounces_since_hit = 0
            rk_plan[side] = None
            if hits >= max_hits:
                end_reason = "max_hits"
                p, v = p2, v2
                break
        p, v = p2, v2
        t += dt
        if p[2] < H - 0.3 or abs(p[0]) > x_racket + 0.4 or abs(p[1]) > Wd:
            end_reason = "out"
            break
    return {"hits": hits, "end_reason": end_reason, "shots": shots, "t": np.asarray(T), "p": np.asarray(P),
            "racket_pos": np.asarray(RK), "hit_times": np.asarray(hit_times), "rewinds": rewinds_total}
