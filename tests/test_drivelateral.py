# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""drivelateral の門: 各 op の閉形式を、独立な経路(数値積分・力の釣り合い・細かい折線・行進するシミュレーション)で検算する。"""
from __future__ import annotations

import math

import numpy as np
import pytest

import drivelateral as DL

CAR = {"mass": 1500.0, "l_f": 1.2, "l_r": 1.5, "c_f": 80000.0, "c_r": 90000.0, "inertia": 2500.0}   # アンダーステア
OVER = {"mass": 1500.0, "l_f": 1.5, "l_r": 1.2, "c_f": 90000.0, "c_r": 60000.0, "inertia": 2500.0}  # オーバーステア


# ---- 共通の独立な道具 --------------------------------------------------------------------------------------
def simpson_cum(f, a, b, n=20001):
    x = np.linspace(a, b, n)
    y = f(x)
    h = x[1] - x[0]
    return x, np.r_[0.0, np.cumsum(0.5 * h * (y[1:] + y[:-1]))]          # 台形(n 大きく、誤差 h²)


def quad(f, a, b, n=200001):
    x = np.linspace(a, b, n)
    y = f(x)
    h = (b - a) / (n - 1)
    return h / 3.0 * (y[0] + y[-1] + 4 * y[1:-1:2].sum() + 2 * y[2:-1:2].sum())


def circle_poly(R, ang0, ang1, n, center=(0.0, 0.0)):
    a = np.linspace(ang0, ang1, n)
    return np.stack([center[0] + R * np.cos(a), center[1] + R * np.sin(a)], 1)


# ---- 1. 摩擦と路面 ---------------------------------------------------------------------------------------------
def test_friction_circle_usage_values_and_errors():
    u = DL.friction_circle_usage([3.0, 0.0, -6.0], [4.0, 7.848, 8.0], mu=0.8)
    assert np.allclose(u, [5.0 / (0.8 * DL.G), 7.848 / (0.8 * DL.G), 10.0 / (0.8 * DL.G)])
    with pytest.raises(ValueError):
        DL.friction_circle_usage(1.0, 1.0, mu=0.0)
    with pytest.raises(ValueError):
        DL.friction_circle_usage([np.nan], [1.0], mu=0.8)


@pytest.mark.parametrize("i,f,R", [(0.0, 0.15, 30.0), (0.06, 0.13, 150.0), (0.10, 0.10, 570.0), (-0.02, 0.12, 60.0)])
def test_curve_speed_limit_equals_force_balance_on_incline(i, f, R):
    """独立な経路: 斜面の座標で力を分解し、必要な摩擦力 / 垂直抗力 = f になる速さ(二分法)。"""
    v = DL.curve_speed_limit(R, side_friction=f, superelevation=i)
    al = math.atan(i)
    m = 1.0

    def need(vv):
        Z = m * vv * vv / R                         # 遠心力(水平)
        Gw = m * DL.G
        along = Z * math.cos(al) - Gw * math.sin(al)  # 斜面に沿って外向き
        normal = Z * math.sin(al) + Gw * math.cos(al)
        return along / normal
    lo, hi = 0.0, 200.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if need(mid) < f else (lo, mid)
    assert abs(v - lo) < 1e-9 * v
    assert abs(DL.curve_speed_limit(R, side_friction=f) - math.sqrt(f * DL.G * R)) < 1e-12


def test_curve_speed_limit_edges():
    assert DL.curve_speed_limit(50.0, side_friction=10.0, superelevation=0.2) == math.inf
    for kw in ({"side_friction": -0.1}, {"side_friction": 0.1, "superelevation": 1.0},
               {"side_friction": 0.0, "superelevation": -0.05}):
        with pytest.raises(ValueError):
            DL.curve_speed_limit(50.0, **kw)
    with pytest.raises(ValueError):
        DL.curve_speed_limit(0.0, side_friction=0.1)


def test_design_min_radius_constant_127_and_table_consistency():
    assert abs(3.6 ** 2 * DL.G / 127.0 - 1.0) < 2e-3                     # 127 ≈ 3.6² g
    R = DL.design_min_radius(60.0, side_friction=0.13, superelevation=0.06)
    assert abs(R - 3600.0 / (127.0 * 0.19)) < 1e-12
    # 設計の式は i f を落とすので、その半径での厳密な上限速度は V/3.6 を (1 − i f)^{-1/2} 倍 · √(127/(3.6² g)) だけ上回る
    v = DL.curve_speed_limit(R, side_friction=0.13, superelevation=0.06)
    assert abs(v / (60 / 3.6) - math.sqrt(3.6 ** 2 * DL.G / 127.0 / (1 - 0.06 * 0.13))) < 1e-12
    # 公表値(第 15・18 条の表)の性質: 特例値 < 規定値、速さに単調、緩和区間 ≈ 3 秒の走行長(±5 m)
    sp = sorted(DL.ROAD_MIN_RADIUS)
    assert len(sp) >= 2, sp                              # 空の並びで素通りしない
    assert all(DL.ROAD_MIN_RADIUS[a][0] < DL.ROAD_MIN_RADIUS[b][0] for a, b in zip(sp, sp[1:]))
    assert all(r[1] is None or r[1] < r[0] for r in DL.ROAD_MIN_RADIUS.values())
    for V, L in DL.TRANSITION_LENGTH.items():
        assert abs(L - 3.0 * V / 3.6) < 5.0
    with pytest.raises(ValueError):
        DL.design_min_radius(0.0, side_friction=0.1, superelevation=0.0)


# ---- 2. 2 輪等価モデル ------------------------------------------------------------------------------------------
@pytest.mark.parametrize("params,u,R", [(CAR, 15.0, 80.0), (CAR, 25.0, -150.0), (OVER, 12.0, 60.0), (CAR, 8.0, 25.0)])
def test_steady_cornering_equals_integrated_steady_state(params, u, R):
    """独立な経路: 閉形式の舵角を一定にして RK4 で 40 s 積分し、定常の r・β・軌跡の半径を測る。"""
    ss = DL.steady_cornering(u, R, params)
    X = np.zeros(5)
    for _ in range(4000):
        X = DL.bicycle_model_step(X, ss["steer"], u, params, 0.01)
    r, beta = X[4], X[3] / u
    assert abs(r - u / R) < 1e-7 * abs(u / R)
    assert abs(beta - ss["sideslip"]) < 1e-7 + 1e-6 * abs(ss["sideslip"])
    # 軌跡の半径: 最後の 2 s の重心の点を円に当てはめる(代数的な最小二乗)
    pts = []
    for _ in range(200):
        X = DL.bicycle_model_step(X, ss["steer"], u, params, 0.01)
        pts.append(X[:2].copy())
    P = np.array(pts)
    A = np.c_[2 * P, np.ones(len(P))]
    sol = np.linalg.lstsq(A, (P ** 2).sum(1), rcond=None)[0]
    rad = math.sqrt(sol[2] + sol[0] ** 2 + sol[1] ** 2)
    # 定常の R は u/r(前向きの速さで定義)。重心の軌跡の半径は合成の速さ / r = |R| √(1 + tan²β)
    assert abs(rad - abs(R) * math.hypot(1.0, beta)) < 1e-6 * abs(R)
    assert abs(ss["yaw_gain"] - ss["yaw_rate"] / ss["steer"]) < 1e-12


def _A_numeric(params, u, h=1e-6, dt=1e-4):
    """bicycle_model_step を有限差分して (v_y, r) の連続時間の行列を作る(閉形式を使わない)。"""
    A = np.zeros((2, 2))
    for j in range(2):
        e = np.zeros(5)
        e[3 + j] = h
        d = (DL.bicycle_model_step(e, 0.0, u, params, dt) - DL.bicycle_model_step(-e, 0.0, u, params, dt) - 2 * e) / (2 * h * dt)
        A[:, j] = d[3:5]
    return A


def test_understeer_gradient_speeds_match_eigen_and_gain_peak():
    ug = DL.understeer_gradient(CAR)
    assert ug["kind"] == "understeer" and ug["K"] > 0
    us = np.linspace(2.0, 80.0, 3901)
    gains = [DL.steady_cornering(u, 100.0, CAR)["yaw_gain"] for u in us]
    assert abs(us[int(np.argmax(gains))] - ug["characteristic_speed"]) < 0.03
    uo = DL.understeer_gradient(OVER)
    assert uo["kind"] == "oversteer"
    vc = uo["critical_speed"]
    lo = max(np.linalg.eigvals(_A_numeric(OVER, 0.97 * vc)).real)
    hi = max(np.linalg.eigvals(_A_numeric(OVER, 1.03 * vc)).real)
    assert lo < 0 < hi
    with pytest.raises(ValueError):
        DL.steady_cornering(1.05 * vc, 100.0, OVER)
    neutral = dict(CAR, c_r=CAR["c_f"] * CAR["l_f"] / CAR["l_r"])
    assert DL.understeer_gradient(neutral)["kind"] == "neutral"


def test_bicycle_step_errors():
    with pytest.raises(ValueError):
        DL.bicycle_model_step(np.zeros(5), 0.0, 0.1, CAR, 0.01)
    with pytest.raises(ValueError):
        DL.bicycle_model_step(np.zeros(4), 0.0, 10.0, CAR, 0.01)
    with pytest.raises(ValueError):
        DL.bicycle_model_step(np.zeros(5), 0.0, 10.0, {k: v for k, v in CAR.items() if k != "inertia"}, 0.01)
    with pytest.raises(ValueError):
        DL.steady_cornering(10.0, 0.0, CAR)


# ---- 3. 低速の幾何 ------------------------------------------------------------------------------------------
@pytest.mark.parametrize("R", [4.5, 6.0, 12.0, 40.0])
def test_ackermann_wheel_normals_meet_at_turn_centre(R):
    L, t = 2.7, 1.5
    a = DL.ackermann_steer_angles(R, L, t)
    assert abs(1 / math.tan(a["outer"]) - 1 / math.tan(a["inner"]) - t / L) < 1e-12
    # 車の座標(後車軸の中心 = 原点、前 = +x、左 = +y、旋回の中心 = (0, R))。前輪の向きに垂直な線が中心を通る
    for y, d in ((t / 2, a["inner"]), (-t / 2, a["outer"])):
        p = np.array([L, y])
        nrm = np.array([-math.sin(d), math.cos(d)])
        lam = (R - p[1]) / nrm[1]
        assert abs(p[0] + lam * nrm[0]) < 1e-9
    assert abs(a["offtracking"] - (math.hypot(R - t / 2, L) - (R - t / 2))) < 1e-12
    with pytest.raises(ValueError):
        DL.ackermann_steer_angles(0.7, L, t)


def _front_path_straight_then_circle(R, L, ang, ds):
    """直線(x < 0、y = −R)→ 原点まわりの左回りの円(半径 R)。前車軸の中心の折線。"""
    nn = int(round(6 * L / ds))
    xs = -6 * L + ds * np.arange(nn)                         # 0 を含まない(浮動小数の arange は 0 をわずかに越えうる)
    pre = np.stack([xs, np.full_like(xs, -R)], 1)
    n = int(round(R * ang / ds)) + 1
    circ = circle_poly(R, -math.pi / 2, -math.pi / 2 + ang, n)
    return np.vstack([pre, circ]), len(pre)


@pytest.mark.parametrize("R,L,t", [(6.0, 2.7, 1.5), (9.0, 2.7, 1.5), (5.0, 4.0, 1.8)])
def test_offtracking_closed_form_equals_fine_polyline_tractrix(R, L, t):
    errs = []
    for ds in (0.02, 0.01):
        F, k0 = _front_path_straight_then_circle(R, L, math.pi, ds)
        rp = DL.rear_axle_path(F, L)
        s = np.arange(len(F) - k0) * (R * math.pi / (len(F) - k0 - 1))
        cf = DL.offtracking_circle(R, L, s, track=t)
        rr = np.hypot(*rp["rear"][k0:].T)
        errs.append(np.abs(rr - cf["rear_radius"]).max())
        # 車輪の内側(左): 後車軸の中心 + (t/2)·車体の左
        h = rp["heading"][k0:]
        rin = rp["rear"][k0:] + 0.5 * t * np.stack([-np.sin(h), np.cos(h)], 1)
        assert np.abs(np.hypot(*rin.T) - cf["rear_inner_wheel_radius"]).max() < 30 * errs[-1] + 1e-6
    assert errs[1] < 1e-3 and errs[1] < errs[0] / 3.0          # 2 次で縮む
    st = cf["steady"]
    assert abs(st["rear_radius"] - math.sqrt(R * R - L * L)) < 1e-12
    big = DL.offtracking_circle(R, L, 50 * R, track=t)
    assert abs(big["offtracking"] - st["offtracking"]) < 1e-9
    a = DL.ackermann_steer_angles(math.sqrt(R * R - L * L), L, t)
    assert abs(st["offtracking"] - a["offtracking"]) < 1e-9     # 定常 = アッカーマンの式


def test_offtracking_matches_direct_ode_and_gamma0():
    """独立な経路: dγ/ds = 1/R − sin γ / L を RK4 で積分。γ₀ ≠ 0 の版も。"""
    R, L = 7.0, 2.8
    for g0 in (0.0, 0.2):
        h = 1e-3
        g = g0
        ss = np.arange(0, 20.0 + h / 2, h)
        out = [g]
        f = lambda gg: 1 / R - math.sin(gg) / L  # noqa: E731
        for _ in ss[1:]:
            k1 = f(g)
            k2 = f(g + h * k1 / 2)
            k3 = f(g + h * k2 / 2)
            k4 = f(g + h * k3)
            g += h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
            out.append(g)
        cf = DL.offtracking_circle(R, L, ss, gamma0=g0)
        assert np.abs(cf["gamma"] - np.array(out)).max() < 1e-10
    for bad in ({"front_radius": 2.0, "wheelbase": 2.7, "arc_length": 1.0},
                {"front_radius": 7.0, "wheelbase": 2.7, "arc_length": -1.0},
                {"front_radius": 7.0, "wheelbase": 2.7, "arc_length": 1.0, "gamma0": 0.5}):
        with pytest.raises(ValueError):
            DL.offtracking_circle(**bad)


def test_rear_axle_path_invariant_and_ode():
    rng = np.random.default_rng(3)
    ang = np.cumsum(rng.normal(0, 0.05, 400))
    F = np.cumsum(np.stack([np.cos(ang), np.sin(ang)], 1) * 0.1, axis=0)
    L = 2.5
    rp = DL.rear_axle_path(F, L)
    assert np.abs(np.hypot(*(F - rp["rear"]).T) - L).max() < 1e-12
    # 独立: 後の速度 = (前の速度 · 棒) 棒 を細かい刻みで RK4(各区間を 50 に分ける)
    Rr = rp["rear"][0].copy()
    for k in range(len(F) - 1):
        a, b = F[k], F[k + 1]
        for j in range(50):
            def vel(rr, tt):
                fpos = a + tt * (b - a)
                uu = (fpos - rr) / np.linalg.norm(fpos - rr)
                return ((b - a) @ uu) * uu
            h = 1 / 50
            t0 = j * h
            k1 = vel(Rr, t0)
            k2 = vel(Rr + h / 2 * k1, t0 + h / 2)
            k3 = vel(Rr + h / 2 * k2, t0 + h / 2)
            k4 = vel(Rr + h * k3, t0 + h)
            Rr = Rr + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
    assert np.linalg.norm(Rr - rp["rear"][-1]) < 1e-7
    # 直線: 後は線の上に留まる
    S = np.stack([np.linspace(0, 10, 11), np.zeros(11)], 1)
    assert np.abs(DL.rear_axle_path(S, 2.0)["rear"][:, 1]).max() == 0.0
    with pytest.raises(ValueError):
        DL.rear_axle_path(S, 2.0, rear0=(0.0, 1.0))
    with pytest.raises(ValueError):
        DL.rear_axle_path(np.array([[0.0, 0.0], [0.0, 0.0], [1.0, 0.0]]), 2.0)


# ---- 4. 緩和曲線 ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("x", [0.0, 0.1, 0.5, 1.0, 1.7, 2.9, 3.4, 3.6, 4.5, 6.0, -2.2])
def test_fresnel_equals_quadrature(x):
    C, S = DL.fresnel_integrals(x)
    if x == 0.0:
        assert C == 0.0 and S == 0.0
        return
    a, b = (0.0, x) if x > 0 else (x, 0.0)
    sg = 1 if x > 0 else -1
    Cq = sg * quad(lambda t: np.cos(np.pi * t * t / 2), a, b, 400001)
    Sq = sg * quad(lambda t: np.sin(np.pi * t * t / 2), a, b, 400001)
    tol = 1e-9 if abs(x) <= 3.5 else 1e-8
    assert abs(C - Cq) < tol and abs(S - Sq) < tol


def test_fresnel_limit_and_shape():
    C, S = DL.fresnel_integrals(np.array([[40.0, 80.0]]))
    assert C.shape == (1, 2) and np.all(np.abs(C - 0.5) < 0.01) and np.all(np.abs(S - 0.5) < 0.01)
    with pytest.raises(ValueError):
        DL.fresnel_integrals(np.inf)


@pytest.mark.parametrize("k0,k1,Ls", [(0.0, 1 / 60, 40.0), (1 / 60, 0.0, 40.0), (-1 / 30, 1 / 20, 25.0),
                                      (1 / 12, -1 / 40, 15.0), (0.05, 0.05, 30.0), (0.0, 0.0, 10.0)])
def test_clothoid_points_equal_heading_integration(k0, k1, Ls):
    """独立な経路: 向き θ(s) = h0 + κ0 s + (κ1−κ0) s²/(2 Ls) を cos・sin で数値積分。"""
    h0, p0 = 0.7, (3.0, -2.0)
    s = np.linspace(0, Ls, 11)
    cp = DL.clothoid_points(Ls, s, kappa0=k0, kappa1=k1, start=p0, heading0=h0)
    th = lambda u: h0 + k0 * u + (k1 - k0) * u * u / (2 * Ls)  # noqa: E731
    xg, X = simpson_cum(lambda u: np.cos(th(u)), 0, Ls, 400001)
    _, Y = simpson_cum(lambda u: np.sin(th(u)), 0, Ls, 400001)
    ref = np.stack([p0[0] + np.interp(s, xg, X), p0[1] + np.interp(s, xg, Y)], 1)
    assert np.abs(cp["points"] - ref).max() < 1e-8
    assert np.allclose(cp["heading"], th(s), atol=1e-12)
    assert np.allclose(cp["curvature"], k0 + (k1 - k0) * s / Ls)


def test_clothoid_design_jerk_and_shift():
    R, L, v = 60.0, 40.0, 15.0
    d = DL.clothoid_design(R, L, v)
    assert abs(d["A"] ** 2 - R * L) < 1e-9
    # 独立: クロソイドを一定速度で走るときの横加速度 v² κ(s(t)) の時間微分(数値)
    tt = np.linspace(0, L / v, 1001)
    ay = v * v * DL.clothoid_points(L, v * tt, kappa1=1 / R)["curvature"]
    assert abs(np.gradient(ay, tt).mean() - d["lateral_jerk"]) < 1e-9
    assert abs(d["shift"] / d["shift_approx"] - 1.0) < 0.05 * d["end_angle"]        # 近似の誤差は τ の高次
    # 端の点 = 曲率が 1/R の円の接続点: 端で向き τ、円の中心までの距離 R
    xe, ye = d["end_point"]
    cx, cy = xe - R * math.sin(d["end_angle"]), ye + R * math.cos(d["end_angle"])
    assert abs(cy - (R + d["shift"])) < 1e-9 and cx > 0
    with pytest.raises(ValueError):
        DL.clothoid_points(10.0, [11.0])


# ---- 5. 制御則 ------------------------------------------------------------------------------------------------------
def test_pure_pursuit_arc_passes_through_goal():
    path = circle_poly(30.0, -1.0, 1.5, 2001)
    rng = np.random.default_rng(5)
    poses = np.c_[path[300] + rng.normal(0, 0.5, (20, 2)), np.pi / 2 - 0.6 + rng.normal(0, 0.2, 20)]
    out = DL.pure_pursuit_curvature(poses, path, 8.0)
    for i in range(20):
        p, h, k, g = poses[i, :2], poses[i, 2], out["kappa"][i], out["goal"][i]
        assert abs(np.linalg.norm(g - p) - 8.0) < 1e-9
        c = p + np.array([-math.sin(h), math.cos(h)]) / k               # 指令の円の中心
        assert abs(np.linalg.norm(g - c) - 1 / abs(k)) < 1e-9
    one = DL.pure_pursuit_curvature(poses[3], path, 8.0)
    assert abs(one["kappa"] - out["kappa"][3]) < 1e-15
    win = DL.pure_pursuit_curvature(poses, path, 8.0, start_index=np.full(20, 300), window=200)
    assert np.allclose(win["kappa"], out["kappa"])


def test_pure_pursuit_goal_equals_brute_force_on_wiggly_path():
    """独立な経路: 頂点を 1 つずつ辿る素朴な探索(弧長が弦よりずっと長い蛇行で、窓の外の保険も通る)。"""
    x = np.linspace(0, 60, 3001)
    path = np.stack([x, 3.0 * np.sin(x * 1.3)], 1)
    rng = np.random.default_rng(11)
    k = rng.integers(0, 2500, 30)
    poses = np.c_[path[k] + rng.normal(0, 0.3, (30, 2)), rng.normal(0, 0.5, 30)]
    o = DL.pure_pursuit_curvature(poses, path, 6.0)
    for i in range(30):
        p = poses[i, :2]
        for j in range(o["index"][i], len(path) - 1):
            if np.hypot(*(path[j + 1] - p)) >= 6.0:
                a, d = path[j], path[j + 1] - path[j]
                f = a - p
                qa, qb, qc = d @ d, 2 * f @ d, f @ f - 36.0
                g = a + (-qb + math.sqrt(qb * qb - 4 * qa * qc)) / (2 * qa) * d
                break
        assert np.linalg.norm(o["goal"][i] - g) < 1e-9


def _pp_closed_loop(path, R, Ld, L, K, v, T, dt=0.005, y0=0.0):
    """後車軸の運動学 + アンダーステア(実際の曲率 = 指令 / (1 + K v²/L))で pure pursuit を回す。"""
    x = np.array([path[0, 0], path[0, 1] + y0, math.atan2(*(path[1] - path[0])[::-1])])
    c = 1 + K * v * v / L
    idx = 0
    for _ in range(int(T / dt)):
        o = DL.pure_pursuit_curvature(x, path, Ld, start_index=idx, window=60)
        idx = int(o["index"])
        kap = o["kappa"] / c
        ds = v * dt                                              # 刻みの間は一定の曲率 = 円弧で厳密に進める
        h1 = x[2] + kap * ds
        if abs(kap) > 1e-12:
            x = np.array([x[0] + (math.sin(h1) - math.sin(x[2])) / kap, x[1] - (math.cos(h1) - math.cos(x[2])) / kap, h1])
        else:
            x = np.array([x[0] + ds * math.cos(x[2]), x[1] + ds * math.sin(x[2]), h1])
    return x


@pytest.mark.parametrize("K,v", [(0.0, 10.0), (0.004, 15.0), (0.006, 20.0)])
def test_pure_pursuit_circle_offset_equals_closed_loop(K, v):
    R, Ld, L = 40.0, 12.0, 2.7
    path = circle_poly(R, -math.pi / 2, 4 * math.pi, 6000)
    x = _pp_closed_loop(path, R, Ld, L, K, v, T=500.0 / v)
    rho = math.hypot(x[0], x[1])
    cf = DL.pure_pursuit_circle_offset(R, Ld, L, understeer=K, speed=v)
    assert abs(rho - cf["rho"]) < 0.005
    if K > 0:
        assert cf["offset"] > 0.1                                      # 門が自明でない(外へ膨らむ量が見える)
    with pytest.raises(ValueError):
        DL.pure_pursuit_circle_offset(5.0, 12.0, 2.7)


@pytest.mark.parametrize("v,Ld", [(8.0, 8.0), (14.0, 15.0)])
def test_pure_pursuit_offset_dynamic_equals_2dof_closed_loop(v, Ld):
    """独立な経路: 線形 2 輪等価モデル(RK4)+ pure pursuit(δ = atan(L κ))を円の上で回した定常の横ずれ。
    運動学の閉形式は後軸の横すべりを落とすので小さく見積もる(門が自明でない)。"""
    R = 58.0
    L = CAR["l_f"] + CAR["l_r"]
    path = circle_poly(R, -math.pi / 2, 3 * math.pi, 9000)
    X = np.zeros((1, 5))
    X[0, :2] = path[0] + [CAR["l_r"], 0.0]
    idx = np.zeros(1, int)
    for _ in range(int(300 / v / 0.01)):
        rear = X[:, :2] - CAR["l_r"] * np.c_[np.cos(X[:, 2]), np.sin(X[:, 2])]
        o = DL.pure_pursuit_curvature(np.c_[rear, X[:, 2]], path, Ld, start_index=idx, window=30)
        idx = o["index"]
        X = DL.bicycle_model_step(X, np.arctan(L * o["kappa"]), v, CAR, 0.01)
    sim = -o["lateral"][0]
    dyn = DL.pure_pursuit_circle_offset(R, Ld, L, speed=v, params=CAR)
    kin = DL.pure_pursuit_circle_offset(R, Ld, L, speed=v, understeer=DL.understeer_gradient(CAR)["K"])
    assert abs(sim - dyn["offset"]) < 2e-3
    assert kin["offset"] < 0.7 * dyn["offset"]


def _stanley_sim(e0, k, v, T, ks=0.0, dt=1e-3):
    """前車軸の運動学(前輪の向き = ψ + δ で前車軸が進む、後は追跡曲線)。経路 = x 軸。"""
    L = 2.7
    path = np.stack([np.linspace(-50, 500, 5501), np.zeros(5501)], 1)
    f = np.array([0.0, e0])
    psi = 0.3 if e0 < 0 else -0.2
    es = [e0]
    for _ in range(int(round(T / dt))):
        o = DL.stanley_steer(np.r_[f, psi], path, gain=k, speed=v, softening=ks)
        d = o["steer"]
        f = f + dt * v * np.array([math.cos(psi + d), math.sin(psi + d)])
        psi = psi + dt * v * math.sin(d) / L
        es.append(f[1])
    return np.array(es)


@pytest.mark.parametrize("e0,k,v,ks", [(2.0, 1.0, 5.0, 0.0), (-6.0, 2.5, 10.0, 0.0), (1.0, 0.8, 8.0, 1.0)])
def test_stanley_straight_decay_equals_simulation(e0, k, v, ks):
    T = 3.0
    es = _stanley_sim(e0, k, v, T, ks)
    t = np.linspace(0, T, len(es))
    cf = DL.stanley_straight_decay(e0, t, gain=k, speed=v, softening=ks)
    assert np.abs(cf - es).max() < 2e-3 * abs(e0)
    # 小さい e では指数 e^{−v k t / a}
    e_small = DL.stanley_straight_decay(1e-4, 0.5, gain=k, speed=v, softening=ks)
    assert abs(e_small - 1e-4 * math.exp(-v * k * 0.5 / (ks + v))) < 1e-9


def test_stanley_errors():
    with pytest.raises(ValueError):
        DL.stanley_straight_decay(1.0, -1.0, gain=1.0, speed=1.0)
    with pytest.raises(ValueError):
        DL.stanley_steer([0, 0, 0], [[0, 0], [1, 0]], gain=0.0, speed=1.0)


# ---- 6. 速度計画と車線 ----------------------------------------------------------------------------------------------
def test_speed_plan_simple_curve_closed_form():
    """直線 → 半径 R の円 → 直線。減速は円の手前で v² = v_c² + 2 a (s_c − s)、加速は円の後で v² = v_c² + 2 a' (s − s_e)。"""
    R, alat, adec, aacc, vmax = 50.0, 2.0, 2.5, 1.0, 20.0
    s = np.linspace(0, 400, 4001)
    k = np.where((s > 200) & (s < 260), 1 / R, 0.0)
    pl = DL.curvature_speed_plan(s, k, v_max=vmax, a_lat_max=alat, a_accel=aacc, a_decel=adec)
    vc = math.sqrt(alat * R)
    sc = s[np.nonzero(k)[0][0] - 1]                          # 刻みの曲率の最大は前の点から効く
    ref = np.sqrt(np.minimum(vmax ** 2, vc ** 2 + 2 * adec * np.maximum(sc - s, 0)))
    pre = s < sc
    assert np.abs(pl["v"][pre] - ref[pre]).max() < 1e-9
    se = s[np.nonzero(k)[0][-1] + 1]
    ref2 = np.sqrt(np.minimum(vmax ** 2, vc ** 2 + 2 * aacc * np.maximum(s - se, 0)))
    post = s > se
    assert np.abs(pl["v"][post] - ref2[post]).max() < 1e-9
    mid = (s > 200.5) & (s < 259.5)
    assert np.abs(pl["v"][mid] - vc).max() < 1e-9
    # 時間 = ∫ ds / v(v² 一次の刻みの厳密な形)
    tt = np.sum(2 * np.diff(s) / (pl["v"][1:] + pl["v"][:-1]))
    assert abs(pl["time"][-1] - tt) < 1e-9


def test_speed_plan_friction_circle_holds_inside_every_step():
    s = np.linspace(0, 200, 801)
    k = np.interp(s, [0, 80, 110, 140, 170, 200], [0, 0, 1 / 25, 1 / 25, 0, 0])
    G = 0.8 * DL.G
    pl = DL.curvature_speed_plan(s, k, v_max=25.0, a_lat_max=0.9 * G, a_accel=3.0, a_decel=7.0, a_total=G)
    w = pl["v"] ** 2
    for j in range(len(s) - 1):                              # 刻みの中を 20 等分して確かめる
        lam = np.linspace(0, 1, 21)
        ww = w[j] + lam * (w[j + 1] - w[j])
        kk = k[j] + lam * (k[j + 1] - k[j])
        ax = (w[j + 1] - w[j]) / (2 * (s[j + 1] - s[j]))
        assert np.all(np.hypot(ax, ww * kk) <= G * (1 + 1e-9))
    # 摩擦円を守らない版(a_total なし)は同じ場所で超える = 門が自明でない
    pl2 = DL.curvature_speed_plan(s, k, v_max=25.0, a_lat_max=0.9 * G, a_accel=3.0, a_decel=7.0)
    w2 = pl2["v"] ** 2
    ax2 = np.diff(w2) / (2 * np.diff(s))
    assert np.max(np.hypot(ax2, w2[:-1] * k[:-1]) / G) > 1.05


def test_speed_plan_converges_to_fine_ode():
    """独立な経路: 減速の境界 dv/ds = −√(G² − (v²κ)²)/v を、曲線の頂点から後ろへ細かい RK4 で積分。"""
    G = 0.7 * DL.G
    Ls, R = 40.0, 30.0
    vc = math.sqrt(G * 0.95 * R)

    def kap(x):
        return np.clip(x / Ls, 0, 1) / R                         # 0..Ls のクロソイド、その後は円
    v = vc
    x = Ls
    h = -1e-3
    xs, vs = [x], [v]
    f = lambda xx, vv: -math.sqrt(max(G * G - (vv * vv * kap(xx)) ** 2, 0.0)) / vv if True else 0  # noqa: E731
    while x > 0:
        k1 = f(x, v)
        k2 = f(x + h / 2, v + h / 2 * k1)
        k3 = f(x + h / 2, v + h / 2 * k2)
        k4 = f(x + h, v + h * k3)
        v += h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        x += h
        xs.append(x)
        vs.append(v)
    ref_v0 = vs[-1]
    errs = []
    for n in (201, 801, 3201):
        s = np.linspace(0, Ls + 20, n)
        pl = DL.curvature_speed_plan(s, kap(s), v_max=40.0, a_lat_max=0.95 * G, a_accel=9.0, a_decel=9.0, a_total=G)
        errs.append(abs(pl["v"][0] - ref_v0))
    assert pl["v"][0] <= ref_v0 + 1e-9                           # 刻みの最大曲率を使うので保守的
    assert errs[-1] < 0.02 and errs[2] < errs[0]


def test_speed_plan_errors():
    with pytest.raises(ValueError):
        DL.curvature_speed_plan([0, 0], [0, 0], v_max=1, a_lat_max=1, a_accel=1, a_decel=1)
    with pytest.raises(ValueError):
        DL.curvature_speed_plan([0, 1], [0, 0], v_max=1, a_lat_max=2, a_accel=1, a_decel=1, a_total=1)
    with pytest.raises(ValueError):
        DL.curvature_speed_plan([0, 1], [0, 0], v_max=1, a_lat_max=1, a_accel=1, a_decel=1, v_start=2)


def test_lateral_offset_recovers_constructed_points():
    R = 50.0
    path = circle_poly(R, 0, math.pi, 3001)
    s_true = np.array([10.0, 40.0, 100.0, 150.0])
    n_true = np.array([1.2, -0.7, 0.0, 3.0])
    ang = s_true / R
    P = np.stack([(R - n_true) * np.cos(ang), (R - n_true) * np.sin(ang)], 1)   # 左回り: 左 = 内側
    o = DL.lateral_offset(P, path)
    assert np.abs(o["n"] - n_true).max() < 1e-3 and np.abs(o["s"] - s_true).max() < 1e-2
    ow = DL.lateral_offset(P, path, start_index=o["index"] + 7, window=20)       # 窓で探しても同じ
    assert np.allclose(ow["n"], o["n"]) and np.array_equal(ow["index"], o["index"])
    with pytest.raises(ValueError):
        DL.lateral_offset([[0.0, 0.0, 0.0]], path)


def _march_tlc(y0, psi, kv, v, b, kr, dt=1e-4, T=60.0):
    """独立な経路: 車の円を刻みで進め、境界の符号が変わる時刻(線形補間)。"""
    x, y, h = 0.0, y0, psi

    def side(xx, yy):
        if abs(kr) < 1e-15:
            return yy - b
        rb = abs(1 / kr - b)
        return (rb - math.hypot(xx, yy - 1 / kr)) * (1 if (1 / kr - b) * kr > 0 else -1) * math.copysign(1, b) * \
            math.copysign(1, kr)
    s0 = side(x, y)
    t = 0.0
    while t < T:
        x2 = x + dt * v * math.cos(h + 0.5 * dt * v * kv)
        y2 = y + dt * v * math.sin(h + 0.5 * dt * v * kv)
        s1 = side(x2, y2)
        if np.sign(s1) != np.sign(s0):
            return t + dt * s0 / (s0 - s1)
        x, y, h, t = x2, y2, h + dt * v * kv, t + dt
    return math.inf


@pytest.mark.parametrize("y0,psi,kv,v,b,kr", [(0.0, 0.05, 0.0, 15.0, 1.75, 0.0), (0.2, -0.02, -0.004, 20.0, -1.75, 0.0),
                                               (0.0, 0.0, 0.0, 15.0, -1.75, 1 / 200), (0.3, 0.0, 1 / 300, 12.0, -1.75, 1 / 120),
                                               (-0.5, 0.01, 1 / 50, 10.0, 1.75, 1 / 60)])
def test_tlc_equals_marching(y0, psi, kv, v, b, kr):
    tl = DL.time_to_line_crossing(y0, psi, kv, v, line_offset=b, lane_curvature=kr)
    ref = _march_tlc(y0, psi, kv, v, b, kr)
    assert math.isfinite(ref)
    assert abs(tl - ref) < 2e-3


def test_tlc_infinite_and_errors():
    assert DL.time_to_line_crossing(0.0, 0.0, 0.0, 10.0, line_offset=1.75) == math.inf
    assert DL.time_to_line_crossing(0.0, 0.0, 1 / 100, 10.0, line_offset=-1.75, lane_curvature=1 / 100) == math.inf
    with pytest.raises(ValueError):
        DL.time_to_line_crossing(2.0, 0.0, 0.0, 10.0, line_offset=1.75)


# ---- 条文の判定 ------------------------------------------------------------------------------------------------------
def _turn(kind, y_app, Rf, cx, v_app, v_turn, *, ds=0.05, L=2.7, after=15.0):
    """+x へ進み(y = y_app)、x = cx から半径 Rf の円で左(右)へ 90° 曲がる前車軸の中心の折線と、後車軸(rear_axle_path)。"""
    sg = 1.0 if kind == "left" else -1.0
    cy = y_app + sg * Rf
    xs = np.arange(-40.0, cx, ds)
    pre = np.stack([xs, np.full_like(xs, y_app)], 1)
    n = int(round(Rf * math.pi / 2 / ds))
    ph = np.linspace(0, math.pi / 2, n + 1)[1:]
    arc = np.stack([cx + Rf * np.sin(ph), cy - sg * Rf * np.cos(ph)], 1)
    ys = np.arange(ds, after, ds)
    post = np.stack([np.full_like(ys, arc[-1, 0]), arc[-1, 1] + sg * ys], 1)
    F = np.vstack([pre, arc, post])
    rp = DL.rear_axle_path(F, L)
    speed = np.where(F[:, 0] < cx - 25.0, v_app, v_turn)
    return {"t": np.arange(len(F)), "front": F, "rear": rp["rear"], "speed": speed, "width": 1.8, "track": 1.55,
            "front_overhang": 0.9, "rear_overhang": 0.9}


def test_turn_maneuver_check_truth_table():
    kw = dict(x_entry=24.0, edge_y=3.5, center_y=0.0, corner_center=(24.0, 9.5), corner_radius=6.0, clearance=0.5)
    good = _turn("left", 2.2, 6.5, 26.0, 8.0, 2.5)           # 車の左側が左端から 0.4 m、隅切りの 2 m 先から半径 6.5 m
    good_c = DL.turn_maneuver_check(good, kind="left", **kw)
    assert good_c["ok"], good_c
    centre = _turn("left", 1.75, 8.5, 24.0, 8.0, 2.5)        # 車線の中央(0.85 m)
    r = DL.turn_maneuver_check(centre, kind="left", **kw)
    assert r["violations"] == ["あらかじめ左端に寄っていない(左端まで最大 0.85 m > 0.50 m)"], r
    fast = _turn("left", 2.2, 6.5, 26.0, 8.0, 5.0)
    assert "徐行" in " / ".join(DL.turn_maneuver_check(fast, kind="left", **kw)["violations"])
    tight = _turn("left", 2.2, 6.5, 24.0, 8.0, 2.5)          # 前輪で隅切りに沿う = 内輪差を無視
    assert "内輪差" in " / ".join(DL.turn_maneuver_check(tight, kind="left", **kw)["violations"])
    wide = _turn("left", 2.2, 7.5, 26.0, 8.0, 2.5)
    assert "側端に沿って" in " / ".join(DL.turn_maneuver_check(wide, kind="left", **kw)["violations"])
    # 右折: 中央線に寄り(右側が中央線から 0.4 m)、交差点の中心(x = 38、y = −7)のすぐ内側を回る
    kr = dict(x_entry=24.0, edge_y=3.5, center_y=0.0, intersection_center=(38.0, -7.0))
    yr = 0.4 + 0.9
    okr = DL.turn_maneuver_check(_turn("right", yr, 7.5, 30.0, 8.0, 2.5), kind="right", **kr)
    assert okr["ok"], okr
    big = DL.turn_maneuver_check(_turn("right", yr, 7.5, 38.0, 8.0, 2.5), kind="right", **kr)
    assert "外側" in " / ".join(big["violations"]), big
    early = DL.turn_maneuver_check(_turn("right", yr, 5.0, 26.0, 8.0, 2.5), kind="right", **kr)
    assert "すぐ内側でない" in " / ".join(early["violations"]), early
    keepc = DL.turn_maneuver_check(_turn("right", 1.75, 7.5, 30.0, 8.0, 2.5), kind="right", **kr)
    assert "中央に寄っていない" in " / ".join(keepc["violations"]), keepc
    with pytest.raises(ValueError):
        DL.turn_maneuver_check(good, kind="u", **kw)
