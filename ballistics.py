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
    "thrust_ode",
    "thrust_fit",
    "drag_fit",
    "aic_from_rss",
    "ballistic_vs_thrust",
    "time_stretch_from_gravity",
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
    """スピン比 S = rω/|v| から揚力係数 C_L = 1 / (2 + 1/S)(S → 0 で 0、S → ∞ で 0.5。球の文献で広く使われる経験式)。

    空の入力(``spin_ratio`` が 0 要素)は ValueError。
    """
    if (len(spin_ratio) if isinstance(spin_ratio, (list, tuple)) else np.asarray(spin_ratio).size) == 0:   # ★2026-10-12 空入力の方針 A: 黙って値を返さず、何が空かを名指しで拒否
        raise ValueError("magnus_lift_coefficient: spin_ratio is empty — pass at least one element")
    S = np.asarray(spin_ratio, np.float64)
    return np.where(S > 0, 1.0 / (2.0 + 1.0 / np.maximum(S, 1e-300)), 0.0)


def drag_coefficient_sphere(reynolds) -> np.ndarray:
    """滑らかな球の抗力係数の経験式(Morrison 2013、Re ≲ 1e6): 24/Re + 2.6(Re/5)/(1 + (Re/5)^1.52) + 0.411(Re/263000)^−7.94/(1 + (Re/263000)^−8)
    + 0.25(Re/1e6)/(1 + Re/1e6)。卓球の球(Re ≈ 1〜5 × 10⁴)で ≈ 0.4〜0.5。

    空の入力(``reynolds`` が 0 要素)は ValueError。
    """
    if (len(reynolds) if isinstance(reynolds, (list, tuple)) else np.asarray(reynolds).size) == 0:   # ★2026-10-12 空入力の方針 A: 黙って値を返さず、何が空かを名指しで拒否
        raise ValueError("drag_coefficient_sphere: reynolds is empty — pass at least one element")
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


# ─────────────────── 推力の有無と時間の引き延ばし(映像の物理整合性、2026-10-23) ───────────────────
# 単眼の映像から尺度つきで起こした軌跡に、「重力 + 抗力」と「重力 + 抗力 + 一定の比推力」の 2 つの模型を当て、
# AIC の差で選ぶ。時刻を k 倍に引き延ばした映像では当てはめた g が g/k² に見えるので、k は閉形式で戻る。
# どれも**判定の閾値を同梱しない**(ΔAIC の床は呼び手が渡し、k は清浄な映像の分布と並べて読む: imgforensics の流儀)。

def _acc_thrust(vx, vy, vz, bp, thrust):
    ax, ay, az = _acc(vx, vy, vz, 0.0, 0.0, 0.0, bp)
    return ax + thrust[0], ay + thrust[1], az + thrust[2]


def _rk4_thrust(p, v, h, bp, thrust):
    px, py, pz = p
    vx, vy, vz = v
    a1 = _acc_thrust(vx, vy, vz, bp, thrust)
    v2 = (vx + 0.5 * h * a1[0], vy + 0.5 * h * a1[1], vz + 0.5 * h * a1[2])
    a2 = _acc_thrust(v2[0], v2[1], v2[2], bp, thrust)
    v3 = (vx + 0.5 * h * a2[0], vy + 0.5 * h * a2[1], vz + 0.5 * h * a2[2])
    a3 = _acc_thrust(v3[0], v3[1], v3[2], bp, thrust)
    v4 = (vx + h * a3[0], vy + h * a3[1], vz + h * a3[2])
    a4 = _acc_thrust(v4[0], v4[1], v4[2], bp, thrust)
    h6 = h / 6.0
    pn = (px + h6 * (vx + 2 * v2[0] + 2 * v3[0] + v4[0]), py + h6 * (vy + 2 * v2[1] + 2 * v3[1] + v4[1]),
          pz + h6 * (vz + 2 * v2[2] + 2 * v3[2] + v4[2]))
    vn = (vx + h6 * (a1[0] + 2 * a2[0] + 2 * a3[0] + a4[0]), vy + h6 * (a1[1] + 2 * a2[1] + 2 * a3[1] + a4[1]),
          vz + h6 * (a1[2] + 2 * a2[2] + 2 * a3[2] + a4[2]))
    return pn, vn


_MAX_ODE_STEPS = 5_000_001        # 純 Python の RK4 が 1 回の評価で数十秒を超えない上限。t を ms で渡す単位違いをここで止める
_MAX_FIT_STEPS = 200_001          # 当てはめは 1 回で模型を数百回評価する(反復 × ヤコビアン 10 列 × 減衰の試行)ので上限は 25 分の 1


def _finite_scalar(x, name, who):
    if isinstance(x, (str, bytes, bool)):
        raise ValueError("%s: %s must be a number, got %r" % (who, name, x))
    try:
        v = float(x)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a finite number, got %r" % (who, name, x)) from None
    if not math.isfinite(v):
        raise ValueError("%s: %s must be finite, got %r" % (who, name, x))
    return v


def _check_bp(bp, who):
    """:func:`ball_params` の表の入口検査(fail-closed)。★ 鍵の欠落・非有限・質量 0 は、黙って NaN の軌跡や KeyError /
    ZeroDivisionError になる前に ValueError で止める(2026-10-23 の敵対的レビュー: bp={} で KeyError、g=nan で NaN の軌跡、
    mass=0 で ZeroDivisionError、どれも公開面を素通りしていた)。"""
    if not isinstance(bp, dict):
        raise ValueError("%s: bp must be the dict from ball_params(), got %s" % (who, type(bp).__name__))
    missing = [k for k in ("cd", "mass", "area", "rho", "g") if k not in bp]
    if missing:
        raise ValueError("%s: bp lacks %s — build it with ball_params()" % (who, ", ".join(missing)))
    for k, positive in (("mass", True), ("area", True), ("g", True), ("rho", False)):
        v = _finite_scalar(bp[k], "bp[%r]" % k, who)
        if v < 0.0 or (positive and v == 0.0):
            raise ValueError("%s: bp[%r] must be %s, got %r" % (who, k, "> 0" if positive else "≥ 0", bp[k]))
    cd = bp["cd"]
    if isinstance(cd, str):
        if cd != "sphere":
            raise ValueError("%s: bp['cd'] must be a number or 'sphere', got %r" % (who, cd))
    elif _finite_scalar(cd, "bp['cd']", who) < 0.0:
        raise ValueError("%s: bp['cd'] must be ≥ 0, got %r" % (who, cd))


def thrust_ode(p0, v0, thrust, bp: dict, t_end: float, dt: float = 1e-3) -> dict:
    """重力 + 抗力 + **一定の比推力**(質量あたりの推力 [m/s²]、世界座標で向きも大きさも一定)の RK4。スピンは持たない(ω = 0)。
    返り値 ``{"t" (N,), "p" (N, 3), "v" (N, 3)}``(t = 0, dt, …, ≤ t_end)。``thrust`` が零ベクトルなら :func:`flight_ode`(ω = 0)と
    1e-12 で一致し、真空(rho = 0)なら閉形式 p₀ + v₀ t + ½ (a_T − g ẑ) t² と 1e-9 で一致する(門)。
    「ほぼロケット」の映像を扱う最小の模型で、推力が機体に固定されて向きを変える場合は近似になる(短い区間ほど良い)。
    ``t_end`` / ``dt`` は有限の数、``bp`` は :func:`ball_params` の表(鍵の欠落・非有限・質量 0 は ValueError)、歩数 t_end / dt は
    5×10⁶ まで(秒でなく ms で渡した t をここで止める)。

    空の入力(``thrust`` が 0 要素)は ValueError。
    """
    if (len(thrust) if isinstance(thrust, (list, tuple)) else np.asarray(thrust).size) == 0:
        raise ValueError("thrust_ode: thrust is empty — pass a 3-vector in m/s²")
    p = tuple(_v3(p0, "p0"))
    v = tuple(_v3(v0, "v0"))
    a = tuple(_v3(thrust, "thrust"))
    _check_bp(bp, "thrust_ode")
    t_end = _finite_scalar(t_end, "t_end", "thrust_ode")
    dt = _finite_scalar(dt, "dt", "thrust_ode")
    if t_end < 0 or dt <= 0:
        raise ValueError("thrust_ode: need t_end ≥ 0 and dt > 0, got t_end=%r dt=%r" % (t_end, dt))
    n = int(math.floor(t_end / dt + 1e-9)) + 1
    if n > _MAX_ODE_STEPS:
        raise ValueError("thrust_ode: t_end / dt = %d steps exceeds %d — check the units (t in seconds) or use a larger dt"
                         % (n - 1, _MAX_ODE_STEPS - 1))
    P, V = [p], [v]
    for _ in range(n - 1):
        p, v = _rk4_thrust(p, v, dt, bp, a)
        P.append(p)
        V.append(v)
    return {"t": np.arange(n, dtype=np.float64) * dt, "p": np.asarray(P), "v": np.asarray(V)}


def _fit_thrust_model(t, p, bp, fit_thrust, iters, dt, who, init=None):
    t = np.asarray(t, np.float64).reshape(-1)
    P = np.asarray(p, np.float64)
    if t.size == 0 or P.size == 0:
        raise ValueError("%s: t/p is empty — pass at least 8 samples" % who)
    if P.ndim != 2 or P.shape[1] not in (2, 3):
        raise ValueError("%s: p must be (N, 3) world points or (N, 2) planar (x, z) points" % who)
    planar = P.shape[1] == 2
    if planar:
        P = np.column_stack([P[:, 0], np.zeros(len(P)), P[:, 1]])
    if t.size != len(P) or t.size < 8 or not np.all(np.isfinite(P)) or not np.all(np.isfinite(t)) or not np.all(np.diff(t) > 0):
        raise ValueError("%s: need ≥ 8 finite samples with increasing t" % who)
    _check_bp(bp, who)
    if isinstance(iters, bool) or not isinstance(iters, (int, np.integer)) or iters < 1:
        raise ValueError("%s: iters must be an integer ≥ 1 (with 0 the parabola start would be returned as the fit), got %r" % (who, iters))
    dt = _finite_scalar(dt, "dt", who)
    if dt <= 0.0:
        raise ValueError("%s: dt must be > 0, got %r" % (who, dt))
    t0 = float(t[0])
    tau = t - t0
    # ★ dt が標本間隔を超えると模型は標本の間で区分線形になり、C_d と推力が別の値に化けるのに例外も NaN も出ない
    # (30 fps の同じ軌跡で dt = 0.5 s にすると C_d 0.33 → 3.1、2026-10-23 の敵対的レビュー)。歩数の上限は ms で渡した t を止める。
    gap = float(np.min(np.diff(tau)))
    if dt > gap:
        raise ValueError("%s: dt = %g exceeds the sample spacing %g — the model would be piecewise linear between samples" % (who, dt, gap))
    if tau[-1] / dt + 2 > _MAX_FIT_STEPS:
        raise ValueError("%s: (t[-1] - t[0]) / dt = %.3g steps per model evaluation exceeds %d — check the units (t in seconds) or use a larger dt"
                         % (who, tau[-1] / dt, _MAX_FIT_STEPS - 1))
    if float(bp["rho"]) <= 0.0:
        raise ValueError("%s: rho = 0 (vacuum) makes C_d unidentifiable — use fit_parabola or flight_fit" % who)
    par = fit_parabola(tau, P)
    cd0 = 0.4 if isinstance(bp["cd"], str) else float(bp["cd"])
    # 10 個 = p0(3) v0(3) C_d thrust(3)。C_d ≥ 0 は**射影**で保つ(反復のあとで負なら 0 に戻す)。模型の中で max(0, ·) と
    # 切るとヤコビアンが 0 になって止まり、ln C_d にすると C_d → 0 側でヤコビアンが C_d 倍に消えて粘る(2026-10-23 に両方踏んだ)。
    # 射影なら境界 0 でも前進差分のヤコビアンは消えないので、推力の段で C_d が 0 から戻れる。
    full = np.r_[par["p0"], par["v0"], cd0, 0.0, 0.0, 0.0]
    scales_full = np.r_[np.ones(6), 0.1, np.ones(3)]
    free = [0, 1, 2, 3, 4, 5, 6] + ([7, 8, 9] if fit_thrust else [])
    if planar:
        free = [i for i in free if i not in (1, 4, 8)]              # y 成分は観測が無いので動かさない(= 0)
        full[[1, 4, 8]] = 0.0
    free = np.asarray(free)
    obs = np.asarray([0, 2]) if planar else np.asarray([0, 1, 2])

    def model(xf):
        x = full.copy()
        x[free] = xf
        b = dict(bp)
        b["cd"] = max(0.0, float(x[6]))
        f = thrust_ode(x[:3], x[3:6], tuple(float(c) for c in x[7:10]), b, tau[-1] + dt, dt)
        return np.column_stack([np.interp(tau, f["t"], f["p"][:, k]) for k in obs])

    Pobs = P[:, obs]
    sc = scales_full[free]
    pos_cd = int(np.where(free == 6)[0][0])

    def jac(xf, base):
        J = np.empty((base.size, len(xf)))
        for j in range(len(xf)):
            xp = xf.copy()
            h = 1e-6 * sc[j]
            xp[j] += h
            J[:, j] = ((model(xp) - Pobs).ravel() - base) / h
        return J

    # Levenberg–Marquardt(対角減衰、尺度を揃えた座標で): 「後ろ向きの小さな推力」と抗力が縮退する方向で
    # 素の Gauss–Newton は大きな歩を出して振動し、後退探索では尺を縮めきって途中で止まった(ΔAIC が負に膨らむ)。
    # 減衰を残差が減るまで強め、減ったら弱める。残差は単調に減るので、推力 0 から出発すれば抗力だけの模型より悪くならない。
    xf = full[free].copy() if init is None else np.asarray(init, np.float64)[free].copy()
    res = (model(xf) - Pobs).ravel()
    rss = float(np.dot(res, res))
    mu = 1e-3
    it = 0
    for it in range(1, iters + 1):
        Js = jac(xf, res) * sc                        # d res / d(x / sc)
        A = Js.T @ Js
        g = Js.T @ res
        D = np.diag(np.maximum(np.diag(A), 1e-300))
        accepted = False
        for _ in range(16):
            try:
                step_s = np.linalg.solve(A + mu * D, -g)
            except np.linalg.LinAlgError:
                step_s = np.linalg.lstsq(A + mu * D, -g, rcond=None)[0]
            cand = xf + step_s * sc
            cand[pos_cd] = max(cand[pos_cd], 0.0)        # 射影: 抗力係数は負にしない
            r2 = (model(cand) - Pobs).ravel()
            rss2 = float(np.dot(r2, r2))
            if rss2 < rss:
                accepted = True
                mu = max(mu / 3.0, 1e-12)
                break
            mu *= 4.0
        if not accepted:
            break
        improved = rss - rss2
        xf, res, rss = cand, r2, rss2
        if np.linalg.norm(step_s) < 1e-10 or improved <= 1e-14 * max(rss, 1e-300):
            break
    J = jac(xf, res)
    x = full.copy()
    x[free] = xf
    out = {"p0": x[:3], "v0": x[3:6], "cd": max(0.0, float(x[6])), "thrust": x[7:10].copy(),
           "rms": float(np.sqrt(np.mean(np.sum(res.reshape(-1, len(obs)) ** 2, axis=1)))),
           "rss": rss, "n": int(res.size), "k": int(len(free)), "dims": int(len(obs)),
           "cond": float(np.linalg.cond(J)), "iters": it, "t0": t0}
    out["thrust_norm"] = float(np.linalg.norm(out["thrust"]))
    # 模型は RK4 の格子を標本時刻へ線形補間するので、残差には補間誤差(≤ a dt² / 8、a = 加速度の尺度)が残りうる。
    # その平方和の上限を添える: 残差がこの床にあるなら、それは雑音でなく離散化で、AIC の問いは立たない。
    out["rss_floor"] = float(out["n"] * ((float(bp["g"]) + out["thrust_norm"]) * dt * dt / 8.0) ** 2)
    return out


def thrust_fit(t, p, bp: dict, *, iters: int = 20, dt: float = 1e-3) -> dict:
    """軌跡 (t_i, p_i) に「重力 + 抗力 + 一定の比推力」の模型を **(p₀, v₀, C_d, a_T) の 10 パラメータ** で Levenberg–Marquardt
    (有限差分のヤコビアン、C_d ≥ 0 は射影)で当てる。``p`` は (N, 3) の世界座標か、単眼の側面視で起こした **(N, 2) の平面 (x, z)**(そのときは
    y 成分を観測も未知数も持たないので 7 パラメータ、``n`` = 2 × 点数)。``bp`` は :func:`ball_params` の表(質量・前面積・空気密度・g。
    ``radius`` は前面積を与えるためだけに使う: 車なら A = πr² が前面積になる r を渡す)。
    返り値 ``{"p0", "v0", "cd", "thrust" (3,), "thrust_norm", "rms", "rss", "rss_floor", "n", "k", "dims", "cond", "iters", "t0"}``
    (``n`` は残差の個数、``k`` は動かしたパラメータ数。:func:`aic_from_rss` の入力。``rss_floor`` = RK4 格子を標本時刻へ線形補間する
    誤差 ≤ a dt² / 8 が残差に残しうる平方和の上限)。``dt`` は標本間隔以下(超えると模型が標本の間で区分線形になる)、``iters`` ≥ 1、
    真空(rho = 0)では C_d が同定できないので、どれも ValueError。
    推力つきの真値の軌跡なら a_T は 1e-5 m/s² で戻り、推力 0 で作った軌跡なら ``thrust_norm`` は 1e-5 以下になる(門)。

    空の入力(``t`` が 0 要素)は ValueError。
    """
    # 2 段: 先に抗力だけの模型(推力 0)を解き、その解から推力を動かす。放物線から直接 10 パラメータを動かすと、
    # 「後ろ向きの推力」と抗力が縮退する谷で C_d → 0 の偽解に落ちることがある(真値の軌跡で 0.1 m/s² 外れた、2026-10-23)。
    b = _fit_thrust_model(t, p, bp, False, iters, dt, "thrust_fit")
    return _thrust_fit_two_starts(t, p, bp, iters, dt, "thrust_fit", b)


def _thrust_fit_two_starts(t, p, bp, iters, dt, who, b):
    """推力つきの当てはめを 2 つの始点から解き、残差の小さい方を採る: (1) 抗力だけの解(推力 0)から、(2) 放物線 + 表の C_d から。
    「後ろ向きの推力」と抗力が縮退する谷は壁(C_d = 0)で終わっていて、片方の始点からは壁際に止まることがある
    (真値の推力軌跡で (1) だけだと C_d = 0・|Δa_T| = 0.2 m/s²、(2) だけだと雑音のある弾道で C_d = 0 に固着、2026-10-23)。
    (1) を含むので RSS_推力 ≤ RSS_弾道 は保たれる。"""
    init = np.r_[b["p0"], b["v0"], b["cd"], 0.0, 0.0, 0.0]
    f1 = _fit_thrust_model(t, p, bp, True, iters, dt, who, init=init)
    if f1["cd"] > 1e-6:
        return f1                                     # 壁(C_d = 0)に当たっていなければ谷の底
    f2 = _fit_thrust_model(t, p, bp, True, iters, dt, who)
    return f1 if f1["rss"] <= f2["rss"] else f2


def drag_fit(t, p, bp: dict, *, iters: int = 20, dt: float = 1e-3) -> dict:
    """軌跡 (t_i, p_i) に「重力 + 抗力」の模型を **(p₀, v₀, C_d) の 7 パラメータ**(平面入力なら 5)で当てる(:func:`thrust_fit` の
    推力なし版。:func:`flight_fit` は C_d を既知として 6 パラメータ、こちらは C_d も同定する)。返り値の鍵と入口の検査
    (``dt`` ≤ 標本間隔、``iters`` ≥ 1、真空は拒否)は :func:`thrust_fit` と同じで、``thrust`` は零ベクトル。真値の軌跡なら C_d は 1e-4 で戻る(門)。

    空の入力(``t`` が 0 要素)は ValueError。
    """
    return _fit_thrust_model(t, p, bp, False, iters, dt, "drag_fit")


def aic_from_rss(rss: float, n: int, k: int) -> float:
    """最小二乗の残差平方和から赤池情報量規準 AIC = n ln(RSS/n) + 2k(ガウス雑音、分散は最尤で推定、定数項は落とす)。
    同じデータに当てた模型どうしの**差**だけに意味がある(絶対値は尺度と n に依る)。n ≤ k・RSS ≤ 0・非有限は ValueError
    (RSS = 0 は AIC = −∞ で、模型選択の問いが立たない)。"""
    if not (np.isfinite(rss) and rss > 0.0) or n <= k or k < 1:
        raise ValueError("aic_from_rss: need finite RSS > 0 and n > k ≥ 1")
    return float(n * math.log(rss / n) + 2.0 * k)


def ballistic_vs_thrust(t, p, bp: dict, *, iters: int = 20, dt: float = 1e-3) -> dict:
    """同じ軌跡に「重力 + 抗力」(:func:`drag_fit`)と「重力 + 抗力 + 一定の比推力」(:func:`thrust_fit`)を当て、
    AIC(:func:`aic_from_rss`)の差 ΔAIC = AIC_弾道 − AIC_推力 を返す。
    返り値 ``{"ballistic", "thrust"}``(2 つの当てはめ)に ``"aic_ballistic", "aic_thrust", "delta_aic", "thrust_norm"`` を添える。
    **判定は返さない**(:mod:`imgforensics` と同じ流儀): 読み方は **節約則**で、推力の模型はパラメータが 3 つ多いので雑音だけでも
    RSS を僅かに下げる —— 罰則 2Δk を超えて勝たない限り、単純な方(弾道)を採る。雑音だけの ΔAIC は **−2Δk を下限に** χ²(Δk) 近似の
    幅で散り(中央値は −2Δk + 1 ほど。C_d = 0 の壁に当たる当てはめが混じるので正確には混合分布)、推力側は弾道側の解から出発するので
    ΔAIC ≥ −2Δk が保たれる。「決定的」の慣用は 10(偽陽性 1 % を大きく下回る)だが、閾値は同梱せず呼び手が決める。
    推力側の RSS が離散化の床 ``rss_floor`` の 10 倍を下回る(雑音の無い、または格子より細かく解けた軌跡)ときは ValueError ——
    AIC が比べるのは雑音で、丸め屑ではない(雑音ゼロの真値に既定の dt で ΔAIC = +144 が出た、2026-10-23)。

    空の入力(``t`` が 0 要素)は ValueError。
    """
    b = drag_fit(t, p, bp, iters=iters, dt=dt)
    # 推力側は弾道側の解(推力 0)から出発する: 推力の模型は抗力だけの模型を含むので、残差が単調に減る当てはめなら
    # RSS_推力 ≤ RSS_弾道 が構造的に保証され、ΔAIC ≥ −2Δk になる。
    f = _thrust_fit_two_starts(t, p, bp, iters, dt, "thrust_fit", b)
    # ★ 残差が離散化の床にあるなら n·ln(RSS_b / RSS_t) は丸め屑の比を増幅するだけ(雑音ゼロの真値で +144、推力の推定値は 3e-14 m/s²)。
    if f["rss"] < 10.0 * f["rss_floor"]:
        raise ValueError("ballistic_vs_thrust: the thrust fit's RSS %.3g is within 10× the discretisation floor %.3g (noise-free or "
                         "over-resolved track) — AIC compares noise, not rounding; add the measurement noise or compare rms directly"
                         % (f["rss"], f["rss_floor"]))
    ab = aic_from_rss(b["rss"], b["n"], b["k"])
    af = aic_from_rss(f["rss"], f["n"], f["k"])
    return {"ballistic": b, "thrust": f, "aic_ballistic": ab, "aic_thrust": af, "delta_aic": float(ab - af),
            "thrust_norm": f["thrust_norm"]}


def time_stretch_from_gravity(g_fit: float, g_ref: float = G) -> dict:
    """当てはめた重力加速度から、映像の時間の引き延ばし倍率を閉形式で逆算する。時刻を k 倍に引き延ばした(スローモーションや
    フレームレートの付け替えをした)映像では、軌跡は同じ形のまま g が g/k² に見えるので、k = √(g_ref / g_fit)。
    返り値 ``{"k", "g_fit", "g_ref", "log_k"}``(``log_k`` = ln k は改変なしで 0、符号が速い/遅いを表す: :func:`imgforensics.evidence_quantile`
    に渡すなら |log_k| を「大きいほど強い」証拠として使う)。
    g_fit ≤ 0 や非有限、g_ref ≤ 0 は ValueError(重力が上を向く・無い軌跡に倍率は定義できない)。"""
    g_fit = _finite_scalar(g_fit, "g_fit", "time_stretch_from_gravity")
    g_ref = _finite_scalar(g_ref, "g_ref", "time_stretch_from_gravity")
    if g_fit <= 0.0 or g_ref <= 0.0:
        raise ValueError("time_stretch_from_gravity: need finite g_fit > 0 and g_ref > 0")
    k = math.sqrt(g_ref / g_fit)
    return {"k": float(k), "g_fit": float(g_fit), "g_ref": float(g_ref), "log_k": float(math.log(k))}
