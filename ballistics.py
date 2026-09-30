"""ballistics — 跳ねる球と摩擦とひもの力学(卓球・けん玉の PoC 系列、17 巡目): 世界の側の真値を作る op 族。

飛翔 = 重力 + 抗力(C_d は定数か Re の関数)+ マグヌス(C_L は定数かスピン比の関数)+ スピンの減衰(RK4、純 Python の float で
1 歩 ≈ 数 µs。真空なら閉形式の放物線と 1e-12 で一致)。跳ね = 剛体球 × 平面のクーロン摩擦の衝突(法線の反発係数 e —— 定数か
衝突速度の関数、摩擦係数 μ、滑ったまま/途中で転がりに移る 2 つの領域。Garwin 1969・Cross 2002)。定理の門 =
**接触点まわりの角運動量は摩擦の向きによらず保存**、運動エネルギーは増えない、μ = 0 なら接線速度と回転は不変。
落として跳ねる列は h_n = e^{2n} h₀、接触の間隔は T_{n+1} = e T_n、総時間 = √(2h₀/g)·(1 + e)/(1 − e)(閉形式)。
摩擦 = 滑りの停止距離 v₀²/(2μg)、斜面の滑り出し tan θ = μ。ひも = 伸びない片側拘束(|p − h| ≤ L、張力 ≥ 0、張った瞬間に
外向きの径方向速度が消え ½mv_r² を失う)。

**係数は仮定でなく同定する**(ユーザー 2026-09-29「ボールの動きや摩擦係数の最適化は必要」「物理を完全に再現」): :func:`fit_aero` は
軌跡から (p₀, v₀, C_d, C_L) を、:func:`fit_bounce` は跳ねの前後の速度・回転から (e, μ) を閉形式で戻す(真値の軌跡なら 1e-6 で
一致 = 門)。既定の C_d = 0.4、C_L のスピン比モデル、e = 0.9、μ = 0.25 は文献の代表値で、実測の代わりではない。

規約: 世界座標は z 上向き、g = 9.81 は下向き。速度・位置は (3,)。回転 ω は角速度ベクトル [rad/s](右手)。
球の慣性は薄殻 I = (2/3) m r²(``shell=False`` で中実 (2/5) m r²)。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "ball_params", "impact_params", "flight_vacuum", "flight_ode", "flight_simulate", "flight_state_at", "magnus_lift_coefficient",
    "drag_coefficient_sphere", "bounce", "contact_angular_momentum", "apex_sequence", "bounce_total_time",
    "restitution_from_apexes", "restitution_from_intervals", "fit_parabola", "flight_fit", "fit_aero", "fit_spin", "fit_bounce",
    "slide_stop_distance", "incline_slip_angle", "mu_from_stop_distance", "roll_slide_state", "tether_simulate",
    "pendulum_period", "cup_catch_check",
]

G = 9.81
_NU_AIR = 1.5e-5          # 空気の動粘度 [m²/s](20 ℃)


def _v3(x, name="vector"):
    a = np.asarray(x, np.float64).reshape(-1)
    if a.shape != (3,) or not np.all(np.isfinite(a)):
        raise ValueError("%s must be a finite (3,) vector" % name)
    return a


# ─────────────────────────────── 表 ───────────────────────────────

def magnus_lift_coefficient(spin_ratio) -> np.ndarray:
    """スピン比 S = rω/|v| から揚力係数 C_L = 1 / (2 + 1/S)(S → 0 で 0、S → ∞ で 0.5。球の文献で広く使われる経験式)。"""
    S = np.asarray(spin_ratio, np.float64)
    return np.where(S > 0, 1.0 / (2.0 + 1.0 / np.maximum(S, 1e-300)), 0.0)


def drag_coefficient_sphere(reynolds) -> np.ndarray:
    """滑らかな球の抗力係数の経験式(Morrison 2013、Re ≲ 1e6): 24/Re + 2.6(Re/5)/(1 + (Re/5)^1.52) + 0.411(Re/263000)^−7.94/(1 + (Re/263000)^−8)
    + 0.25(Re/1e6)/(1 + Re/1e6)。卓球の球(Re ≈ 1〜5 × 10⁴)で ≈ 0.4〜0.5。"""
    Re = np.maximum(np.asarray(reynolds, np.float64), 1e-9)
    a = Re / 5.0
    b = Re / 263000.0
    c = Re / 1e6
    return 24.0 / Re + 2.6 * a / (1.0 + a ** 1.52) + 0.411 * b ** (-7.94) / (1.0 + b ** (-8.0)) + 0.25 * c / (1.0 + c)


def ball_params(radius: float = 0.02, mass: float = 0.0027, cd=0.4, cl=None, rho: float = 1.2, g: float = G,
                shell: bool = True, spin_decay: float = 0.0) -> dict:
    """球の表。既定は卓球の球(ITTF: 直径 40 mm、2.7 g、薄殻)。

    ``cd`` = 抗力係数(数、または "sphere" で Re 依存の経験式 :func:`drag_coefficient_sphere`)、``cl`` = 揚力(マグヌス)係数
    (None なら :func:`magnus_lift_coefficient` のスピン比モデル、数なら定数)、``rho`` = 空気密度 [kg/m³]、
    ``spin_decay`` = スピンの減衰率 [1/s] (dω/dt = −spin_decay·ω。0 なら減衰なし。実測から同定する量)。"""
    if radius <= 0 or mass <= 0 or rho < 0 or g <= 0 or spin_decay < 0:
        raise ValueError("radius, mass, g must be positive; rho, spin_decay ≥ 0")
    if isinstance(cd, str):
        if cd != "sphere":
            raise ValueError("cd must be a number or 'sphere'")
    elif not np.isfinite(cd) or cd < 0:
        raise ValueError("cd must be ≥ 0")
    if cl is not None and (not np.isfinite(cl) or cl < 0):
        raise ValueError("cl must be ≥ 0 or None")
    I = (2.0 / 3.0 if shell else 2.0 / 5.0) * mass * radius ** 2
    return {"radius": float(radius), "mass": float(mass), "cd": cd if isinstance(cd, str) else float(cd),
            "cl": None if cl is None else float(cl), "rho": float(rho), "g": float(g), "shell": bool(shell), "inertia": float(I),
            "area": float(np.pi * radius ** 2), "spin_decay": float(spin_decay)}


def impact_params(e=0.9, mu: float = 0.25) -> dict:
    """衝突の表: 法線の反発係数 e ∈ [0, 1] (数、または |v_n| → e の関数: 衝突速度で下がる実測に合わせる)、クーロン摩擦係数 μ ≥ 0。"""
    if callable(e):
        pass
    elif not (0 <= e <= 1):
        raise ValueError("need 0 ≤ e ≤ 1")
    if mu < 0 or not np.isfinite(mu):
        raise ValueError("μ must be ≥ 0")
    return {"e": e if callable(e) else float(e), "mu": float(mu)}


def _e_of(ip: dict, vn: float) -> float:
    e = ip["e"]
    return float(e(abs(vn))) if callable(e) else e


# ─────────────────────────────── 飛翔(float の内側) ───────────────────────────────

def _cd_of(bp, speed):
    cd = bp["cd"]
    if isinstance(cd, str):
        return float(drag_coefficient_sphere(2.0 * bp["radius"] * speed / _NU_AIR))
    return cd


def _acc(vx, vy, vz, wx, wy, wz, bp):
    """加速度(float): 重力 + 抗力 + マグヌス。"""
    ax, ay, az = 0.0, 0.0, -bp["g"]
    sp = math.sqrt(vx * vx + vy * vy + vz * vz)
    if sp <= 0.0 or bp["rho"] <= 0.0:
        return ax, ay, az
    k = 0.5 * bp["rho"] * bp["area"] / bp["mass"]
    cd = _cd_of(bp, sp)
    ax -= k * cd * sp * vx
    ay -= k * cd * sp * vy
    az -= k * cd * sp * vz
    wn = math.sqrt(wx * wx + wy * wy + wz * wz)
    if wn > 0.0:
        cl = bp["cl"] if bp["cl"] is not None else 1.0 / (2.0 + 1.0 / (bp["radius"] * wn / sp))
        f = k * cl * sp / wn                          # k·cl·sp²·(ω̂ × v̂) = k·cl·(sp/wn)·(ω × v)
        ax += f * (wy * vz - wz * vy)
        ay += f * (wz * vx - wx * vz)
        az += f * (wx * vy - wy * vx)
    return ax, ay, az


def _accel(v, omega, bp) -> np.ndarray:
    """numpy の包み(門・古い呼び出し向け)。"""
    v = _v3(v, "v")
    w = _v3(omega, "omega")
    return np.asarray(_acc(v[0], v[1], v[2], w[0], w[1], w[2], bp))


def _rk4(p, v, w, h, bp):
    """1 歩(タプル)。スピンは dω/dt = −spin_decay·ω を解析的に。"""
    px, py, pz = p
    vx, vy, vz = v
    wx, wy, wz = w
    a1 = _acc(vx, vy, vz, wx, wy, wz, bp)
    v2 = (vx + 0.5 * h * a1[0], vy + 0.5 * h * a1[1], vz + 0.5 * h * a1[2])
    a2 = _acc(v2[0], v2[1], v2[2], wx, wy, wz, bp)
    v3 = (vx + 0.5 * h * a2[0], vy + 0.5 * h * a2[1], vz + 0.5 * h * a2[2])
    a3 = _acc(v3[0], v3[1], v3[2], wx, wy, wz, bp)
    v4 = (vx + h * a3[0], vy + h * a3[1], vz + h * a3[2])
    a4 = _acc(v4[0], v4[1], v4[2], wx, wy, wz, bp)
    h6 = h / 6.0
    pn = (px + h6 * (vx + 2 * v2[0] + 2 * v3[0] + v4[0]), py + h6 * (vy + 2 * v2[1] + 2 * v3[1] + v4[1]),
          pz + h6 * (vz + 2 * v2[2] + 2 * v3[2] + v4[2]))
    vn = (vx + h6 * (a1[0] + 2 * a2[0] + 2 * a3[0] + a4[0]), vy + h6 * (a1[1] + 2 * a2[1] + 2 * a3[1] + a4[1]),
          vz + h6 * (a1[2] + 2 * a2[2] + 2 * a3[2] + a4[2]))
    d = bp["spin_decay"]
    if d > 0.0:
        f = math.exp(-d * h)
        wn = (wx * f, wy * f, wz * f)
    else:
        wn = w
    return pn, vn, wn


def flight_vacuum(p0, v0, t, g: float = G) -> np.ndarray:
    """真空の放物線(閉形式): p(t) = p₀ + v₀ t − ½ g t² ẑ。``t`` はスカラか (N,)、返り値 (3,) か (N, 3)。"""
    p0 = _v3(p0, "p0")
    v0 = _v3(v0, "v0")
    t = np.asarray(t, np.float64)
    out = p0 + t[..., None] * v0
    out[..., 2] -= 0.5 * g * t ** 2
    return out


def flight_ode(p0, v0, omega, bp: dict, t_end: float, dt: float = 1e-3) -> dict:
    """重力 + 抗力 + マグヌス(+ スピン減衰)の RK4。返り値 ``{"t" (N,), "p" (N, 3), "v" (N, 3), "omega" (N, 3)}``
    (t = 0, dt, …, ≤ t_end)。真空(rho = 0)なら :func:`flight_vacuum` と一致(門)。"""
    p = tuple(_v3(p0, "p0"))
    v = tuple(_v3(v0, "v0"))
    w = tuple(_v3(omega, "omega"))
    if t_end < 0 or dt <= 0:
        raise ValueError("need t_end ≥ 0 and dt > 0")
    n = int(math.floor(t_end / dt + 1e-9)) + 1
    P, V, W = [p], [v], [w]
    for _ in range(n - 1):
        p, v, w = _rk4(p, v, w, dt, bp)
        P.append(p)
        V.append(v)
        W.append(w)
    return {"t": np.arange(n) * dt, "p": np.asarray(P), "v": np.asarray(V), "omega": np.asarray(W)}


def flight_state_at(p0, v0, omega, bp: dict, T: float, n_steps: int = 50) -> dict:
    """状態 (p₀, v₀, ω) を T 秒だけ運動方程式で進める(T < 0 なら **戻す**: RK4 の刻みを負にする)。``{"p", "v", "omega"}``。"""
    p = tuple(_v3(p0, "p0"))
    v = tuple(_v3(v0, "v0"))
    w = tuple(_v3(omega, "omega"))
    if n_steps < 1:
        raise ValueError("n_steps must be ≥ 1")
    h = float(T) / n_steps
    for _ in range(n_steps):
        p, v, w = _rk4(p, v, w, h, bp)
    return {"p": np.asarray(p), "v": np.asarray(v), "omega": np.asarray(w)}


# ─────────────────────────────── 跳ね ───────────────────────────────

def bounce(v, omega, normal, bp: dict, ip: dict) -> dict:
    """剛体球が平面に当たる瞬間の速度・角速度の更新(クーロン摩擦、Cross 2002 / Garwin 1969 の 2 領域)。

    接触点の滑り速度 s = v_t − r(ω × n)_t。必要な接線力積が μJ_n 以下なら滑りが止まって転がりに移る(grip)、
    超えるなら滑ったまま(slip、接線力積 = μJ_n)。法線は v_n' = −e v_n(e は定数か |v_n| の関数)。返り値
    ``{"v", "omega", "regime" ("grip"|"slip"|"none"), "J_n", "J_t", "slip_speed", "e"}``。
    ``v·n ≥ 0``(離れていく)なら何もしない(regime "none")。定理: 接触点まわりの角運動量は保存(:func:`contact_angular_momentum`)。"""
    v = _v3(v, "v")
    w = _v3(omega, "omega")
    n = _v3(normal, "normal")
    n = n / np.linalg.norm(n)
    m, r, I = bp["mass"], bp["radius"], bp["inertia"]
    vn = float(v @ n)
    if vn >= 0:
        return {"v": v.copy(), "omega": w.copy(), "regime": "none", "J_n": 0.0, "J_t": np.zeros(3), "slip_speed": 0.0, "e": None}
    e = _e_of(ip, vn)
    Jn = -(1.0 + e) * m * vn
    vt = v - vn * n
    s = vt - r * np.cross(w, n)                       # 接触点の滑り速度(接線)
    s = s - (s @ n) * n
    smag = float(np.linalg.norm(s))
    if smag <= 1e-15:
        Jt = np.zeros(3)
        regime = "grip"
    else:
        J_stop = m * smag / (1.0 + m * r * r / I)     # 滑りを止めるのに要る接線力積
        if ip["mu"] * Jn >= J_stop:
            Jt = -J_stop * s / smag
            regime = "grip"
        else:
            Jt = -ip["mu"] * Jn * s / smag
            regime = "slip"
    v2 = v + (Jn * n + Jt) / m
    w2 = w + np.cross(-r * n, Jt) / I                 # 接触点 p_c = p − r n に働く力積のトルク
    return {"v": v2, "omega": w2, "regime": regime, "J_n": float(Jn), "J_t": Jt, "slip_speed": smag, "e": e}


def contact_angular_momentum(v, omega, normal, bp: dict) -> np.ndarray:
    """接触点まわりの角運動量 L_c = I ω + m (p − p_c) × v = I ω + m r (n × v)。跳ねの前後で不変(定理)。"""
    v = _v3(v, "v")
    w = _v3(omega, "omega")
    n = _v3(normal, "normal")
    n = n / np.linalg.norm(n)
    return bp["inertia"] * w + bp["mass"] * bp["radius"] * np.cross(n, v)


def fit_spin(t, p, bp: dict, *, omega0=None, omega_max: float = 1000.0, iters: int = 20, dt: float = 1e-3) -> dict:
    """**曲がり方から回転を読む**: 軌跡 (t_i, p_i)(跳ねを含まない区間)に、抗力 + マグヌスの運動方程式を
    (p₀, v₀, ω) の 9 パラメータで Gauss–Newton で当てる(空力係数は ``bp`` の値 = 既知とする)。

    マグヌスの力は ω × v なので、**ω の v に平行な成分は力を生まず、軌跡からは決まらない**(進行方向を軸にした
    回転 = 横回転の一部)。飛ぶうちに v の向きが変わるので完全に不定ではないが弱い。返り値の ``omega_perp`` =
    初速に垂直な成分(読める部分)、``cond`` = ヤコビアンの条件数、``omega_axial_sensitivity`` = 平行成分を
    1 rad/s 動かしたときの軌跡の変化の rms [m](小さいほど読めない)。
    返り値 ``{"p0", "v0", "omega", "omega_perp", "rms", "cond", "omega_axial_sensitivity", "iters", "t0"}``。
    真値の軌跡を入れると 1e-3 rad/s で戻る(門)。模様から測った角速度(:func:`balltrack.spin_from_markers`)と
    独立な第 2 の測り方になる。

    ``omega_max`` [rad/s] = 回転の大きさの上限(各歩の後にこの球へ射影する)。★スピン比の模型 C_L = 1/(2 + 1/S) は
    回転が大きいと 0.5 で頭打ちになるので、力が足りないと見た当てはめは |ω| を際限なく大きくできる(大きさが決まらない)。
    軌跡が短く雑音が勝つと 1e5 rad/s へ走った(2026-09-30)。既定 1000 rad/s ≈ 160 回転/秒(強打の上限より上)。
    返り値の ``at_bound`` が True なら上限に張り付いた = 大きさは読めていない。"""
    t = np.asarray(t, np.float64).reshape(-1)
    P = np.asarray(p, np.float64).reshape(-1, 3)
    if not (np.isfinite(omega_max) and omega_max > 0):
        raise ValueError("omega_max must be a positive finite number")
    if t.size != len(P) or t.size < 10 or not np.all(np.isfinite(P)) or not np.all(np.diff(t) > 0):
        raise ValueError("need ≥ 10 finite samples with increasing t")
    w0 = np.zeros(3) if omega0 is None else _v3(omega0, "omega0")
    tau = t - t[0]
    ff = flight_fit(t, P, w0, bp, dt=dt)
    x = np.r_[ff["p0"], ff["v0"], w0]

    def model(x):
        f = flight_ode(x[:3], x[3:6], x[6:9], bp, tau[-1] + dt, dt)
        return np.column_stack([np.interp(tau, f["t"], f["p"][:, k]) for k in range(3)])

    scales = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 50.0, 50.0, 50.0])

    def jac(x, res):
        J = np.empty((res.size, 9))
        for j in range(9):
            h = 1e-6 * scales[j]
            xp = x.copy()
            xp[j] += h
            J[:, j] = ((model(xp) - P).ravel() - res) / h
        return J

    # ★減衰つき(Levenberg–Marquardt)。素の Gauss–Newton は軌跡が短い(曲がりが雑音に埋もれる)と ω の方向が
    #   ほぼ不定になり、1 歩で 1e7 rad/s へ飛んだ(2026-09-30、PoC ㉔ の 10〜45 コマ)。費用が下がる歩だけ受け入れる。
    res = (model(x) - P).ravel()
    cost = float(res @ res)
    lam, it = 1e-3, 0
    for it in range(1, iters + 1):
        J = jac(x, res)
        A = J.T @ J
        g = J.T @ res
        D = np.diag(np.maximum(np.diag(A), 1e-12))
        improved = False
        for _ in range(12):
            dx = np.linalg.solve(A + lam * D, -g)
            xn = x + dx
            wn = float(np.linalg.norm(xn[6:9]))
            if wn > omega_max:
                xn[6:9] *= omega_max / wn
                dx = xn - x
            rn = (model(xn) - P).ravel()
            cn = float(rn @ rn)
            if cn < cost:
                x, res, cost, lam, improved = xn, rn, cn, max(lam / 3.0, 1e-9), True
                break
            lam *= 4.0
        if not improved or np.linalg.norm(dx / scales) < 1e-10:
            break
    J = jac(x, res)
    vhat = x[3:6] / max(1e-12, float(np.linalg.norm(x[3:6])))
    w = x[6:9]
    sens = J[:, 6:9] @ vhat
    return {"p0": x[:3], "v0": x[3:6], "omega": w, "omega_perp": w - (w @ vhat) * vhat,
            "rms": float(np.sqrt(np.mean(np.sum(res.reshape(-1, 3) ** 2, axis=1)))), "cond": float(np.linalg.cond(J)),
            "omega_axial_sensitivity": float(np.sqrt(np.mean(np.sum(sens.reshape(-1, 3) ** 2, axis=1)))),
            "iters": it, "t0": float(t[0]), "at_bound": bool(np.linalg.norm(w) > omega_max * (1 - 1e-9))}


def fit_bounce(v_in, omega_in, v_out, omega_out, normal, bp: dict) -> dict:
    """跳ねの前後の (v, ω) から (e, μ) を閉形式で戻す(同定)。e = −v_n'/v_n。接線力積 J_t = m(v_t' − v_t) の大きさと
    J_n = m(v_n' − v_n) の比が μ —— 滑ったままの領域なら等号、途中で転がりに移った(grip)領域なら **下界**(μ ≥ |J_t|/J_n)。
    どちらかは、跳ねた後の接触点の滑り速度が 0 か(grip)で判る。返り値 ``{"e", "mu", "mu_is_lower_bound", "regime", "J_n", "J_t"}``。"""
    vi = _v3(v_in, "v_in")
    vo = _v3(v_out, "v_out")
    wo = _v3(omega_out, "omega_out")
    n = _v3(normal, "normal")
    n = n / np.linalg.norm(n)
    m, r = bp["mass"], bp["radius"]
    vn_i, vn_o = float(vi @ n), float(vo @ n)
    if vn_i >= 0:
        raise ValueError("v_in must approach the plane (v_in·n < 0)")
    e = -vn_o / vn_i
    Jn = m * (vn_o - vn_i)
    Jt = m * ((vo - vn_o * n) - (vi - vn_i * n))
    s_out = (vo - vn_o * n) - r * np.cross(wo, n)
    s_out = s_out - (s_out @ n) * n
    grip = float(np.linalg.norm(s_out)) < 1e-6
    mu = float(np.linalg.norm(Jt) / Jn) if Jn > 0 else float("nan")
    return {"e": float(e), "mu": mu, "mu_is_lower_bound": bool(grip), "regime": "grip" if grip else "slip", "J_n": float(Jn), "J_t": Jt}


def flight_simulate(p0, v0, omega, bp: dict, ip: dict, t_end: float, dt: float = 1e-3, table_z: float = 0.0,
                    table_xy=None, max_bounces: int = 100, v_rest: float = 1e-3) -> dict:
    """飛翔 + 卓上(z = table_z の平面、``table_xy`` = (xmin, xmax, ymin, ymax) の範囲内だけ)での跳ねを、接触時刻を 2 分法で
    区間内に求めて繋ぐ。返り値 ``{"t", "p", "v", "omega" (N, 3), "contacts": [{"t", "p", "v_in", "v_out", "omega_in",
    "omega_out", "regime"}], "rest_t"}``。球は半径 r なので中心が table_z + r に達した所が接触。跳ねは無限に続く(Zeno)ので、
    接触時の |v_n| < ``v_rest`` になったら卓上に置く(以後 z は固定、水平は摩擦無しで続く。``rest_t`` = その時刻、無ければ None)。"""
    p = tuple(_v3(p0, "p0"))
    v = tuple(_v3(v0, "v0"))
    w = tuple(_v3(omega, "omega"))
    if t_end < 0 or dt <= 0:
        raise ValueError("need t_end ≥ 0 and dt > 0")
    r = bp["radius"]
    zc = table_z + r
    nrm = np.array([0.0, 0.0, 1.0])
    if table_xy is not None:
        x0, x1, y0, y1 = (float(a) for a in table_xy)
    T, P, V, W = [0.0], [p], [v], [w]
    contacts = []
    t = 0.0
    n_b = 0
    rest_t = None
    while t < t_end - 1e-12:
        h = min(dt, t_end - t)
        p2, v2, w2 = _rk4(p, v, w, h, bp)
        if rest_t is not None:
            p2 = (p2[0], p2[1], zc)
            v2 = (v2[0], v2[1], 0.0)
        elif p2[2] < zc <= p[2] and v2[2] < 0 and n_b < max_bounces and (
                table_xy is None or (x0 <= p2[0] <= x1 and y0 <= p2[1] <= y1)):
            lo, hi = 0.0, h                                       # 2 分法で接触時刻
            for _ in range(40):
                mid = 0.5 * (lo + hi)
                pm, _, _ = _rk4(p, v, w, mid, bp)
                if pm[2] < zc:
                    hi = mid
                else:
                    lo = mid
            pc, vc, wc = _rk4(p, v, w, lo, bp)
            pc = (pc[0], pc[1], zc)
            if abs(vc[2]) < v_rest:                               # Zeno: 置く
                rest_t = t + lo
                p, v, w, t = pc, (vc[0], vc[1], 0.0), wc, t + lo
                T.append(t)
                P.append(p)
                V.append(v)
                W.append(w)
                continue
            b = bounce(np.asarray(vc), np.asarray(wc), nrm, bp, ip)
            contacts.append({"t": t + lo, "p": np.asarray(pc), "v_in": np.asarray(vc), "v_out": b["v"].copy(),
                             "omega_in": np.asarray(wc), "omega_out": b["omega"].copy(), "regime": b["regime"]})
            p, v, w, t = pc, tuple(b["v"]), tuple(b["omega"]), t + lo
            n_b += 1
            T.append(t)
            P.append(p)
            V.append(v)
            W.append(w)
            continue
        p, v, w, t = p2, v2, w2, t + h
        T.append(t)
        P.append(p)
        V.append(v)
        W.append(w)
    return {"t": np.asarray(T), "p": np.asarray(P), "v": np.asarray(V), "omega": np.asarray(W), "contacts": contacts,
            "rest_t": rest_t}


def apex_sequence(h0: float, e: float, n: int) -> np.ndarray:
    """落として跳ねる列の頂点高さ h_k = e^{2k} h₀(k = 0..n)。"""
    if h0 < 0 or not (0 <= e <= 1) or n < 0:
        raise ValueError("need h0 ≥ 0, 0 ≤ e ≤ 1, n ≥ 0")
    return h0 * e ** (2.0 * np.arange(n + 1))


def bounce_total_time(h0: float, e: float, g: float = G) -> float:
    """高さ h₀ から落として止まるまでの総時間 = √(2h₀/g)·(1 + e)/(1 − e)(等比級数の閉形式、e < 1)。"""
    if h0 < 0 or not (0 <= e < 1) or g <= 0:
        raise ValueError("need h0 ≥ 0, 0 ≤ e < 1, g > 0")
    return float(np.sqrt(2.0 * h0 / g) * (1.0 + e) / (1.0 - e))


def restitution_from_apexes(heights) -> dict:
    """頂点高さの列(≥ 2 個、正)から e を推定: log h_k は k に線形で傾き 2 log e → 最小二乗。``{"e", "h0", "residual"}``。"""
    h = np.asarray(heights, np.float64).reshape(-1)
    if h.size < 2 or np.any(h <= 0) or not np.all(np.isfinite(h)):
        raise ValueError("need ≥ 2 positive finite heights")
    k = np.arange(h.size)
    slope, icpt = np.polyfit(k, np.log(h), 1)
    res = np.log(h) - (slope * k + icpt)
    return {"e": float(np.exp(slope / 2.0)), "h0": float(np.exp(icpt)), "residual": float(np.sqrt(np.mean(res ** 2)))}


def restitution_from_intervals(contact_times) -> dict:
    """接触時刻の列(≥ 3 個、増加)から e を推定: 間隔 T_{k+1} = e T_k → log T_k の傾きが log e。``{"e", "residual"}``。"""
    t = np.asarray(contact_times, np.float64).reshape(-1)
    if t.size < 3 or not np.all(np.diff(t) > 0):
        raise ValueError("need ≥ 3 increasing contact times")
    T = np.diff(t)
    k = np.arange(T.size)
    slope, icpt = np.polyfit(k, np.log(T), 1)
    res = np.log(T) - (slope * k + icpt)
    return {"e": float(np.exp(slope)), "residual": float(np.sqrt(np.mean(res ** 2)))}


def fit_parabola(t, p) -> dict:
    """観測 (t_i, p_i) に p = p₀ + v₀ t − ½ g t² ẑ を最小二乗で当てる(線形、閉形式)。``{"p0", "v0", "g", "rms"}``。
    真空の真値なら 1e-9 で戻る(門)。"""
    t = np.asarray(t, np.float64).reshape(-1)
    P = np.asarray(p, np.float64).reshape(-1, 3)
    if t.size != len(P) or t.size < 3 or not np.all(np.isfinite(P)):
        raise ValueError("need ≥ 3 finite samples with matching t")
    A = np.column_stack([np.ones_like(t), t])
    coef_xy, *_ = np.linalg.lstsq(A, P[:, :2], rcond=None)
    Az = np.column_stack([np.ones_like(t), t, -0.5 * t * t])
    coef_z, *_ = np.linalg.lstsq(Az, P[:, 2], rcond=None)
    p0 = np.array([coef_xy[0, 0], coef_xy[0, 1], coef_z[0]])
    v0 = np.array([coef_xy[1, 0], coef_xy[1, 1], coef_z[1]])
    g = float(coef_z[2])
    pred = flight_vacuum(p0, v0, t, g)
    return {"p0": p0, "v0": v0, "g": g, "rms": float(np.sqrt(np.mean(np.sum((pred - P) ** 2, axis=1))))}


def _gauss_newton(x, model, P, iters, scales):
    res = (model(x) - P).ravel()
    it = 0
    for it in range(1, iters + 1):
        J = np.empty((res.size, len(x)))
        for j in range(len(x)):
            h = 1e-6 * scales[j]
            xp = x.copy()
            xp[j] += h
            J[:, j] = ((model(xp) - P).ravel() - res) / h
        dx = np.linalg.lstsq(J, -res, rcond=None)[0]
        x = x + dx
        res = (model(x) - P).ravel()
        if np.linalg.norm(dx / scales) < 1e-10:
            break
    return x, res, it


def flight_fit(t, p, omega, bp: dict, *, iters: int = 12, dt: float = 1e-3) -> dict:
    """観測 (t_i, p_i)(跳ねを含まない区間)に、抗力 + マグヌス(ω 既知)の運動方程式を **初期状態 (p₀, v₀) の 6 パラメータ** で
    Gauss–Newton(有限差分のヤコビアン)で当てる。放物線の当てはめは抗力・マグヌスを g と v₀ に吸うので予測が曲がる —— こちらは
    先駆者の「空力モデルつきの追跡」に当たる。返り値 ``{"p0", "v0", "rms", "iters", "t0"}``(p₀・v₀ は t = t[0] での状態)。
    真値の軌跡を入れると 1e-9 で戻る(門)。"""
    t = np.asarray(t, np.float64).reshape(-1)
    P = np.asarray(p, np.float64).reshape(-1, 3)
    if t.size != len(P) or t.size < 3 or not np.all(np.isfinite(P)) or not np.all(np.diff(t) > 0):
        raise ValueError("need ≥ 3 finite samples with increasing t")
    w = _v3(omega, "omega")
    t0 = float(t[0])
    tau = t - t0
    par = fit_parabola(tau, P)
    x = np.r_[par["p0"], par["v0"]]

    def model(x):
        f = flight_ode(x[:3], x[3:], w, bp, tau[-1] + dt, dt)
        return np.column_stack([np.interp(tau, f["t"], f["p"][:, k]) for k in range(3)])

    x, res, it = _gauss_newton(x, model, P, iters, np.ones(6))
    return {"p0": x[:3], "v0": x[3:], "rms": float(np.sqrt(np.mean(np.sum(res.reshape(-1, 3) ** 2, axis=1)))), "iters": it, "t0": t0}


def fit_aero(t, p, omega, bp: dict, *, iters: int = 15, dt: float = 1e-3) -> dict:
    """軌跡から **空力係数も** 同定する: (p₀, v₀, C_d, C_L) の 8 パラメータを Gauss–Newton(ω は既知、C_L は定数として当てる)。
    抗力は速さの 2 乗、マグヌスは ω × v なので、直線的でない軌跡(スピンあり・十分な長さ)でないと C_L は決まりにくい
    (``rms`` と一緒に ``cond`` = ヤコビアンの条件数を返すので、それで判る)。返り値 ``{"p0", "v0", "cd", "cl", "rms", "cond", "iters"}``。
    真値の軌跡(C_L 定数で作った)なら 1e-6 で戻る(門)。"""
    t = np.asarray(t, np.float64).reshape(-1)
    P = np.asarray(p, np.float64).reshape(-1, 3)
    if t.size != len(P) or t.size < 8 or not np.all(np.isfinite(P)) or not np.all(np.diff(t) > 0):
        raise ValueError("need ≥ 8 finite samples with increasing t")
    w = _v3(omega, "omega")
    tau = t - t[0]
    ff = flight_fit(t, P, w, bp, dt=dt)
    cd0 = 0.4 if isinstance(bp["cd"], str) else bp["cd"]
    cl0 = bp["cl"] if bp["cl"] is not None else 0.2
    x = np.r_[ff["p0"], ff["v0"], cd0, cl0]

    def model(x):
        b = dict(bp)
        b["cd"] = max(0.0, float(x[6]))
        b["cl"] = max(0.0, float(x[7]))
        f = flight_ode(x[:3], x[3:6], w, b, tau[-1] + dt, dt)
        return np.column_stack([np.interp(tau, f["t"], f["p"][:, k]) for k in range(3)])

    scales = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.1, 0.1])
    x, res, it = _gauss_newton(x, model, P, iters, scales)
    J = np.empty((res.size, 8))
    for j in range(8):
        h = 1e-6 * scales[j]
        xp = x.copy()
        xp[j] += h
        J[:, j] = ((model(xp) - P).ravel() - res) / h
    return {"p0": x[:3], "v0": x[3:6], "cd": float(x[6]), "cl": float(x[7]),
            "rms": float(np.sqrt(np.mean(np.sum(res.reshape(-1, 3) ** 2, axis=1)))), "cond": float(np.linalg.cond(J)), "iters": it}


# ─────────────────────────────── 摩擦 ───────────────────────────────

def slide_stop_distance(v0: float, mu: float, g: float = G) -> float:
    """水平面を初速 v₀ で滑る物の停止距離 = v₀² / (2μg)(μ > 0)。"""
    if v0 < 0 or mu <= 0 or g <= 0:
        raise ValueError("need v0 ≥ 0, μ > 0, g > 0")
    return float(v0 * v0 / (2.0 * mu * g))


def incline_slip_angle(mu: float) -> float:
    """静止摩擦係数 μ の斜面で滑り出す角度 θ = atan μ [rad]。"""
    if mu < 0:
        raise ValueError("μ must be ≥ 0")
    return float(np.arctan(mu))


def mu_from_stop_distance(v0: float, distance: float, g: float = G) -> float:
    """停止距離から μ = v₀² / (2 g d)。"""
    if v0 < 0 or distance <= 0 or g <= 0:
        raise ValueError("need v0 ≥ 0, distance > 0, g > 0")
    return float(v0 * v0 / (2.0 * g * distance))


def roll_slide_state(v_t, omega, normal, bp: dict) -> dict:
    """平面上の球が転がっているか滑っているか: 接触点の滑り速度 s = v_t − r(ω × n)。``{"slip_speed", "rolling"}``
    (|s| < 1e-9 なら転がり)。"""
    vt = _v3(v_t, "v_t")
    w = _v3(omega, "omega")
    n = _v3(normal, "normal")
    n = n / np.linalg.norm(n)
    s = vt - bp["radius"] * np.cross(w, n)
    s = s - (s @ n) * n
    sm = float(np.linalg.norm(s))
    return {"slip_speed": sm, "rolling": sm < 1e-9}


# ─────────────────────────────── ひも(けん玉) ───────────────────────────────

def pendulum_period(L: float, g: float = G) -> float:
    """微小振幅の振り子の周期 2π√(L/g)。"""
    if L <= 0 or g <= 0:
        raise ValueError("need L > 0, g > 0")
    return float(2.0 * np.pi * np.sqrt(L / g))


def tether_simulate(p0, v0, handle, L: float, t_end: float, dt: float = 1e-3, g: float = G, mass: float = 0.01) -> dict:
    """伸びないひも(長さ L)で手元 ``handle`` に繋がれた質点の運動(けん玉の玉)。

    ``handle`` は (3,) の固定点か、時刻 → (3,) の関数。各ステップで自由落下を進め、|p − h| > L になったら球面へ射影して
    外向きの相対径方向速度を消す(片側拘束: ひもは引くだけで押さない)。その瞬間に失う運動エネルギー ½ m v_r² を "snap_loss" に
    積む。張力の推定 = 射影で消した径方向の速度変化 × m / dt(≥ 0)。返り値 ``{"t", "p", "v", "tension", "taut" (bool),
    "snap_times", "snap_loss", "energy"}``。定理の門: |p − h| ≤ L + 1e-9、張力 ≥ 0、手元が固定なら力学的エネルギーは
    snap の瞬間以外で不変(RK 誤差の範囲)、小振幅の周期は 2π√(L/g)。"""
    p = _v3(p0, "p0")
    v = _v3(v0, "v0")
    if L <= 0 or t_end < 0 or dt <= 0 or mass <= 0:
        raise ValueError("need L > 0, t_end ≥ 0, dt > 0, mass > 0")
    if callable(handle):
        hf = handle
    else:
        h0 = _v3(handle, "handle")
        hf = lambda t: h0  # noqa: E731
    n = int(np.floor(t_end / dt + 1e-9)) + 1
    T = np.arange(n) * dt
    P = np.empty((n, 3))
    V = np.empty((n, 3))
    Ten = np.zeros(n)
    Taut = np.zeros(n, bool)
    E = np.empty(n)
    snaps, loss = [], 0.0
    gvec = np.array([0.0, 0.0, -g])
    for i in range(n):
        h = np.asarray(hf(T[i]), np.float64)
        if np.linalg.norm(p - h) > L + 1e-9:
            raise ValueError("string is longer than L at t = %.4f (initial state violates the constraint)" % T[i])
        P[i], V[i] = p, v
        E[i] = 0.5 * mass * float(v @ v) + mass * g * p[2]
        if i == n - 1:
            break
        p2 = p + v * dt + 0.5 * gvec * dt * dt
        v2 = v + gvec * dt
        h2 = np.asarray(hf(T[i + 1]), np.float64)
        d = p2 - h2
        dist = float(np.linalg.norm(d))
        if dist > L:
            rhat = d / dist
            hv = (h2 - h) / dt
            vr = float((v2 - hv) @ rhat)
            was_slack = float(np.linalg.norm(p - h)) < L - 1e-9
            if vr > 0:
                if was_slack:
                    snaps.append(float(T[i + 1]))
                    loss += 0.5 * mass * vr * vr
                v2 = v2 - vr * rhat
                Ten[i + 1] = mass * vr / dt
            p2 = h2 + rhat * L
            Taut[i + 1] = True
        p, v = p2, v2
    return {"t": T, "p": P, "v": V, "tension": Ten, "taut": Taut, "snap_times": np.asarray(snaps), "snap_loss": float(loss),
            "energy": E}


def cup_catch_check(p_ball, v_ball, cup_center, cup_axis, cup_radius: float, ball_radius: float, v_rel_max: float = 1.0) -> dict:
    """玉が皿(中心・軸・半径)に入る幾何の判定: 玉の中心が皿の軸から (cup_radius − ball_radius) 以内、皿の面から玉の半径の 1.5 倍以内の
    高さ(0 ≤ height ≤ 1.5 r)、速さ ≤ v_rel_max。``{"caught", "lateral", "height", "speed"}``。皿が玉より小さければ ValueError。"""
    p = _v3(p_ball, "p_ball")
    v = _v3(v_ball, "v_ball")
    c = _v3(cup_center, "cup_center")
    a = _v3(cup_axis, "cup_axis")
    a = a / np.linalg.norm(a)
    if cup_radius <= 0 or ball_radius <= 0 or v_rel_max < 0:
        raise ValueError("radii must be positive, v_rel_max ≥ 0")
    if cup_radius <= ball_radius:
        raise ValueError("cup_radius must exceed ball_radius (a ball larger than the cup can never be caught)")
    d = p - c
    height = float(d @ a)
    lateral = float(np.linalg.norm(d - height * a))
    speed = float(np.linalg.norm(v))
    caught = lateral <= max(cup_radius - ball_radius, 0.0) and 0.0 <= height <= 1.5 * ball_radius and speed <= v_rel_max
    return {"caught": bool(caught), "lateral": lateral, "height": height, "speed": speed}
