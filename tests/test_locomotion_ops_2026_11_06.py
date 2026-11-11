# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""歩行と足場の op の第 1 便(2026-11-06)の門。Gates for the first batch of walking ops.

どの門も、op と独立に作った真値(閉形式・別実装・総当たり)と照合する:

1. support_line_margin — 点と線分の距離の閉形式を、線分を 2 万点で刻んだ最短距離(別実装)と
   ``fullseye_shows`` の式と照合。面積のある多角形では com_support_margin と同じ値。
   com_support_margin の ``-inf``(線分)は変えていないことも固定する。
2. lipm_capture_point / capture_margin — LIPM の解析解 ``x0 cosh ωt + (v0/ω) sinh ωt`` から
   ``ξ(t) = (x0 + v0/ω) e^{ωt}``。RK4 の数値積分(別実装)で「足圧中心を ξ に置けば止まる / 支持多角形の
   中のどこに置いても止まらない」を確かめ、capture_margin の符号と突き合わせる。
3. gait_step_events — 一歩の位置が既知の合成。接地のばたつき・すり足・引きずりを一歩に数えない。
   同じコマで両足が着いたら拒否。
4. foot_slip_metrics — 滑る量が既知の合成。胴だけが進む見せかけ(足が置き直されない・足が滑る)を
   walking_ok が落とす。
5. footstep_plan — 平地では左右交互・一定の歩幅と歩隔。小さな格子では総当たりの最小と一致。
6. static_contact_force_lp — 左右対称の 2 足は等分。平地で μ が大きいとき「解がある ⇔ COM が
   支持多角形の中(com_support_margin > 0)」。多角錐は錐の内側(4 面では足りず 8 面で足りる)。
7. 台帳 — 24 op が ``fullseye.op_run`` から呼べる(以前は "not in any ledger")。
"""
import itertools
import math

import numpy as np
import pytest

import locomotion as L


# ── 1. 線分の余裕 ─────────────────────────────────────────────────────────────
def _dist_by_sampling(p, a, b, n=20001):
    t = np.linspace(0.0, 1.0, n)[:, None]
    pts = a[None, :] * (1 - t) + b[None, :] * t
    return float(np.min(np.linalg.norm(pts - p[None, :], axis=1)))


def _measure_py_formula(p, a, b):
    """fullseye_shows/common/measure.py の support_line_margin と同じ式(写し、照合の相手)。"""
    seg = b - a
    den = float(seg @ seg)
    if den < 1e-12:
        return -float(np.linalg.norm(p - a))
    pos = float(np.clip(((p - a) @ seg) / den, 0.0, 1.0))
    return -float(np.linalg.norm(p - (a + pos * seg)))


def test_line_margin_matches_closed_form_and_sampling():
    rng = np.random.default_rng(1)
    n = 0
    for _ in range(200):
        a, b = rng.uniform(-1, 1, 2), rng.uniform(-1, 1, 2)
        p = rng.uniform(-2, 2, 2)
        got = L.support_line_margin(p, np.array([[*a, 0.0], [*b, 0.0]]))
        assert got <= 0.0
        assert abs(got - _measure_py_formula(p, a, b)) < 1e-12
        assert abs(-got - _dist_by_sampling(p, a, b)) < 2e-4 * max(1.0, float(np.linalg.norm(b - a)))
        n += 1
    assert n == 200


def test_line_margin_matches_the_prototype_on_trot_diagonals():
    """試作(fullseye_shows)の式と、トロットの対角 2 足の尺度でビット単位に近く一致する(依頼 2026-11-08 の 1)。"""
    rng = np.random.default_rng(11)
    worst, n = 0.0, 0
    for _ in range(500):
        fl, hr = np.r_[rng.uniform(0.15, 0.25), rng.uniform(0.08, 0.14)], np.r_[rng.uniform(-0.25, -0.15), rng.uniform(-0.14, -0.08)]
        p = rng.uniform(-0.1, 0.1, 2)
        got = L.support_line_margin(p, np.array([[*fl, 0.0], [*hr, 0.0]]), ground=0.0)
        worst = max(worst, abs(got - _measure_py_formula(p, fl, hr)))
        n += 1
    assert n == 500 and worst < 1e-15


def test_line_margin_is_zero_on_the_segment_and_signed_with_area():
    feet = np.array([[0.0, 0.0, 0.0], [0.4, 0.0, 0.0]])
    assert L.support_line_margin([0.1, 0.0, 0.9], feet) == 0.0
    assert L.support_line_margin([0.2, 0.3], feet) == pytest.approx(-0.3, abs=1e-15)
    assert L.support_line_margin([0.7, 0.4], feet) == pytest.approx(-0.5, abs=1e-15)   # 端点までの 3-4-5
    # 面積のある多角形では com_support_margin と同じ符号つきの値(+ = 内側)
    sq = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0.0]])
    for com in ([0.5, 0.3], [0.9, 0.5], [1.5, 0.5]):
        assert L.support_line_margin(com, sq) == L.com_support_margin(com, sq)
    assert L.support_line_margin([0.5, 0.3], sq) == pytest.approx(0.3)
    # 1 足 = 点までの距離
    assert L.support_line_margin([0.3, 0.4], np.array([[0.0, 0.0, 0.0]])) == pytest.approx(-0.5)


def test_com_support_margin_still_returns_minus_inf_for_a_segment():
    """既存の値は変えていない(破壊的変更をしない)ことの固定。"""
    feet = np.array([[0.0, 0.0, 0.0], [0.4, 0.0, 0.0]])
    assert L.com_support_margin([0.2, 0.0], feet) == -math.inf
    assert L.support_line_margin([0.2, 0.0], feet) == 0.0


def test_line_margin_drops_airborne_feet_and_refuses_no_support():
    feet = np.array([[0.0, 0.0, 0.0], [0.4, 0.0, 0.0], [0.2, 0.3, 0.2]])   # 3 本目は 0.2 m 浮いている
    with_air = L.support_line_margin([0.2, 0.1], feet)
    grounded = L.support_line_margin([0.2, 0.1], feet, ground=0.0)
    assert with_air > 0.0                     # 浮いた足で多角形ができ「内側」と読む(だから ground を渡す)
    assert grounded == pytest.approx(-0.1)    # 地面の 2 本の線分まで
    with pytest.raises(ValueError):
        L.support_line_margin([0.0, 0.0], feet[2:], ground=0.0)
    with pytest.raises(ValueError):
        L.support_line_margin([np.nan, 0.0], feet)


# ── 2. LIPM の捕捉点 ──────────────────────────────────────────────────────────
def test_capture_point_matches_the_cosh_sinh_solution():
    zc, g = 0.8, 9.81
    w = math.sqrt(g / zc)
    x0, v0 = 0.05, 0.21
    t = np.linspace(0.0, 0.6, 31)
    x = x0 * np.cosh(w * t) + (v0 / w) * np.sinh(w * t)          # 支点 p = 0 の解析解
    v = x0 * w * np.sinh(w * t) + v0 * np.cosh(w * t)
    com = np.c_[x, np.zeros_like(t), np.full_like(t, zc)]
    vel = np.c_[v, np.zeros_like(t), np.zeros_like(t)]
    xi = L.lipm_capture_point(com, vel, zc, gravity=g)
    assert xi.shape == com.shape
    np.testing.assert_allclose(xi[:, 0], (x0 + v0 / w) * np.exp(w * t), rtol=1e-12)
    np.testing.assert_allclose(xi[:, 2], 0.0, atol=1e-15)        # 支点 = 地面の高さ
    # 捕捉された初期条件 x0 = -v0/ω では ξ = 0 が一定
    xi0 = L.lipm_capture_point(np.array([-v0 / w, 0.0]), np.array([v0, 0.0]), zc)
    assert np.allclose(xi0, 0.0, atol=1e-15)


def _rk4_lipm(c0, v0, p, w, T=3.0, dt=1e-3):
    """ẍ = ω² (x − p) を RK4 で(別実装)。"""
    x, v = np.array(c0, float), np.array(v0, float)
    for _ in range(int(T / dt)):
        def f(xx, vv):
            return vv, w * w * (xx - p)
        k1 = f(x, v)
        k2 = f(x + 0.5 * dt * k1[0], v + 0.5 * dt * k1[1])
        k3 = f(x + 0.5 * dt * k2[0], v + 0.5 * dt * k2[1])
        k4 = f(x + dt * k3[0], v + dt * k3[1])
        x = x + dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        v = v + dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
    return x, v


def test_capture_margin_sign_agrees_with_simulation():
    zc = 0.8
    w = math.sqrt(9.81 / zc)
    sq = np.array([[-0.1, -0.08, 0], [0.12, -0.08, 0], [0.12, 0.08, 0], [-0.1, 0.08, 0.0]])
    cops = [np.array([x, y]) for x in np.linspace(-0.1, 0.12, 7) for y in np.linspace(-0.08, 0.08, 5)]
    assert len(cops) == 35
    rng = np.random.default_rng(3)
    seen = {True: 0, False: 0}
    for _ in range(12):
        c = np.r_[rng.uniform(-0.05, 0.05, 2), zc]
        v = np.r_[rng.uniform(-0.4, 0.6, 2), 0.0]
        m = L.capture_margin(c, v, zc, sq)
        xi = L.lipm_capture_point(c, v, zc)[:2]
        if abs(m) < 0.01:
            continue
        if m > 0:
            # 足圧中心を ξ に置くと、重心は ξ の真上で止まる
            xe, ve = _rk4_lipm(c[:2], v[:2], xi, w)
            assert np.linalg.norm(ve) < 1e-3 and np.linalg.norm(xe - xi) < 1e-3
        else:
            # 支持多角形の中のどこに置いても、重心は離れていく
            for p in cops:
                xe, ve = _rk4_lipm(c[:2], v[:2], p, w, T=1.5)
                assert np.linalg.norm(xe - p) > 0.3
        seen[m > 0] += 1
    assert seen[True] >= 2 and seen[False] >= 2


def test_capture_margin_reads_a_running_com_as_unstable():
    sq = np.array([[-0.1, -0.1, 0], [0.1, -0.1, 0], [0.1, 0.1, 0], [-0.1, 0.1, 0.0]])
    com = np.array([0.0, 0.0, 0.8])
    assert L.com_support_margin(com, sq) == pytest.approx(0.1)          # 静的には「安定」
    assert L.capture_margin(com, [0.8, 0.0, 0.0], 0.8, sq) < 0.0        # 前へ走っていれば止まれない
    assert L.capture_margin(com, [0.0, 0.0, 0.0], 0.8, sq) == pytest.approx(0.1)
    with pytest.raises(ValueError):
        L.lipm_capture_point(com, [0, 0, 0], 0.0)
    with pytest.raises(ValueError):
        L.lipm_capture_point(com, [0, 0], 0.8)


# ── 3. 一歩の取り出し ─────────────────────────────────────────────────────────
def _walk(n_steps=6, dt=0.01, swing=20, stance=20, step=0.3, lift=0.08, width=0.2, chatter=False):
    """左右交互の歩き。足 f の k 番目の着地点 x = x0_f + step·(k+1)(既知)。"""
    T = 10 + n_steps * (swing + stance) // 2 + swing + stance + 10
    P = np.zeros((T, 2, 3))
    P[:, 1, 1] = width
    pos = [0.0, step / 2]
    P[:, 0, 0], P[:, 1, 0] = pos[0], pos[1]
    truth = []
    t0 = 10
    for k in range(n_steps):
        f = k % 2
        x0 = pos[f]
        for i in range(swing):
            s = (i + 1) / (swing + 1)
            P[t0 + i, f, 0] = x0 + step * s
            P[t0 + i, f, 2] = lift * math.sin(math.pi * s)
        pos[f] = x0 + step
        P[t0 + swing:, f, 0] = pos[f]
        truth.append((f, t0 + swing, pos[f], width if f == 1 else 0.0))
        t0 += (swing + stance) // 2
    if chatter:                                # 立脚中に 0.008 m のばたつき(帯 0.005〜0.02 の中)
        P[5:9, 0, 2] = [0.008, 0.003, 0.008, 0.003]
    return P, dt, truth


def test_step_events_recover_known_footholds():
    P, dt, truth = _walk(chatter=True)
    r = L.gait_step_events(P, dt, 0.005, 0.02)
    steps = r["steps"]
    assert len(steps) == len(truth) == 6
    for s, (f, td, x, y) in zip(steps, truth):
        assert s["foot"] == f and s["touchdown"] == td
        assert np.allclose(s["xy"], [x, y], atol=1e-12)
        assert s["advance"] == pytest.approx(0.3, abs=1e-12)
        assert s["clearance"] == pytest.approx(0.08, rel=0.02)
    assert r["alternating"] is True
    assert r["per_foot"] == [3, 3]
    assert r["rejected"] == []                 # ばたつきは帯の中なので一歩に数えない


def test_step_events_reject_shuffle_and_drag():
    P, dt, _ = _walk(lift=0.03)                # 上がりが 0.03 m: clearance_min 0.05 で全部すり足
    r = L.gait_step_events(P, dt, 0.005, 0.02, clearance_min=0.05)
    assert r["steps"] == [] and len(r["rejected"]) == 6
    assert {x["reason"] for x in r["rejected"]} == {"no_clearance"}
    P, dt, _ = _walk(step=0.02)                # 足を上げても前へ 2 cm しか出ない = 引きずり
    r = L.gait_step_events(P, dt, 0.005, 0.02)
    assert r["steps"] == [] and {x["reason"] for x in r["rejected"]} == {"no_advance"}


def test_step_events_refuse_a_synchronous_landing():
    P, dt, _ = _walk(n_steps=2)
    # 両足を同じコマで上げて同じコマで下ろす(両足跳び)
    P[:, 1, :] = P[:, 0, :] + np.array([0.0, 0.2, 0.0])
    with pytest.raises(ValueError, match="same frame"):
        L.gait_step_events(P, dt, 0.005, 0.02)
    with pytest.raises(ValueError):
        L.gait_step_events(np.zeros((0, 2, 3)), dt, 0.005, 0.02)
    with pytest.raises(ValueError):
        L.gait_step_events(P, dt, 0.02, 0.005)            # 帯が逆


# ── 4. 足の滑り ───────────────────────────────────────────────────────────────
def _stance_walk(slip=0.0, step=0.3, body_gain=1.0, replant=True):
    """2 足、各足 4 回の立脚(30 コマ)。立脚中に足が slip だけ前へ滑る。replant=False なら足は動かない。"""
    T = 260
    P = np.zeros((T, 2, 3))
    S = np.zeros((T, 2), bool)
    P[:, 1, 1] = 0.2
    for f in (0, 1):
        for k in range(4):
            a = 10 + f * 30 + k * 60
            b = a + 30
            x0 = (f * step / 2 + k * step) if replant else 0.0
            S[a:b, f] = True
            P[a:b, f, 0] = x0 + np.linspace(0.0, slip, b - a)
        idx = np.nonzero(S[:, f])[0]
        P[:, f, 0] = np.interp(np.arange(T), idx, P[idx, f, 0])
    body = np.c_[np.linspace(0.0, body_gain * 3 * step, T), np.full(T, 0.1), np.full(T, 0.8)]
    return P, S, body


def test_slip_is_recovered_exactly_and_progression_is_measured_by_the_feet():
    P, S, body = _stance_walk(slip=0.012)
    r = L.foot_slip_metrics(P, S, body)
    assert len(r["intervals"]) == 8
    assert all(abs(iv["slip"] - 0.012) < 1e-12 for iv in r["intervals"])
    assert r["max_slip_observed"] == pytest.approx(0.012, abs=1e-12)
    assert r["foot_advance"] == pytest.approx(0.9, abs=1e-12)          # 3 回の置き直し × 0.3 m
    assert r["body_advance"] == pytest.approx(0.9, abs=1e-12)
    assert r["advance_ratio"] == pytest.approx(1.0, abs=1e-12)
    assert r["walking_ok"] is True


def test_body_only_progress_is_failed_by_the_gate():
    # 胴だけが 0.9 m 進み、足は一度も置き直されない(足が地面に描かれているだけ)
    P, S, body = _stance_walk(replant=False)
    r = L.foot_slip_metrics(P, S, body)
    assert r["body_advance"] == pytest.approx(0.9)
    assert r["foot_advance"] == pytest.approx(0.0, abs=1e-12)
    assert r["walking_ok"] is False
    # 足を置き直さず、立脚中に滑って進む(氷の上の空回り)
    P, S, body = _stance_walk(slip=0.25, replant=False)
    r = L.foot_slip_metrics(P, S, body)
    assert r["max_slip_observed"] == pytest.approx(0.25)
    assert r["walking_ok"] is False
    with pytest.raises(ValueError):
        L.foot_slip_metrics(P, S[:-1], body)


# ── 5. 足場の列 ───────────────────────────────────────────────────────────────
def _plan_cost(steps, start, cell, smax, wmin, wmax, lam):
    """返された列から費用を数え直す(docstring の式の写し)。"""
    feet = {"L": start[0], "R": start[1]}
    wm, wh = 0.5 * (wmin + wmax), 0.5 * (wmax - wmin)
    tot = 0.0
    for s in steps:
        other = feet["R" if s["side"] == "L" else "L"]
        i, j = s["cell"]
        dx = (j - other[1]) * cell
        wy = ((i - other[0]) if s["side"] == "L" else (other[0] - i)) * cell
        dev = ((dx - smax) / smax) ** 2 + (((wy - wm) / wh) ** 2 if wh > 0 else 0.0)
        tot += 1.0 + lam * dev
        feet[s["side"]] = (i, j)
    return tot


def _brute_force(mask, cell, start, goal, smax, wmin, wmax, lam, max_steps):
    """全部の着地の列を深さ max_steps まで数え上げた最小費用(別実装)。"""
    H, W = mask.shape
    nmax = int(np.floor(smax / cell + 1e-9))
    wm, wh = 0.5 * (wmin + wmax), 0.5 * (wmax - wmin)
    best = math.inf

    def rec(L_, R_, nxt, cost, depth):
        nonlocal best
        if cost >= best:
            return
        if L_[1] >= goal and R_[1] >= goal:
            best = cost
            return
        if depth == max_steps:
            return
        for side in ([nxt] if nxt else ["L", "R"]):
            st = R_ if side == "L" else L_
            for dj in range(nmax + 1):
                j = st[1] + dj
                if j >= W:
                    break
                for i in range(H):
                    if not mask[i, j]:
                        continue
                    wy = ((i - st[0]) if side == "L" else (st[0] - i)) * cell
                    if not (wmin - 1e-9 <= wy <= wmax + 1e-9):
                        continue
                    dev = ((dj * cell - smax) / smax) ** 2 + (((wy - wm) / wh) ** 2 if wh > 0 else 0.0)
                    c = cost + 1.0 + lam * dev
                    if side == "L":
                        rec((i, j), R_, "R", c, depth + 1)
                    else:
                        rec(L_, (i, j), "L", c, depth + 1)

    rec(start[0], start[1], None, 0.0, 0)
    return best


def test_footsteps_on_flat_ground_alternate_regularly():
    m = np.ones((9, 30), bool)
    r = L.footstep_plan(m, 0.1, ((5, 0), (3, 0)), 24, 0.3, 0.15, 0.25, extent=(0.0, 3.0, 0.0, 0.9))
    steps = r["steps"]
    assert r["reached"] is True and len(steps) == r["n_steps"] >= 8
    sides = [s["side"] for s in steps]
    assert all(a != b for a, b in zip(sides, sides[1:]))
    rows = {s["side"]: set() for s in steps}
    for s in steps:
        rows[s["side"]].add(s["cell"][0])
    assert rows == {"L": {5}, "R": {3}}                          # 歩隔 0.2 m = 中央
    cols = [s["cell"][1] for s in steps]
    assert np.all(np.diff(cols) == 3)                            # 歩幅 0.3 m で一定
    i0, j0 = steps[0]["cell"]
    assert steps[0]["xy"] == pytest.approx((0.1 * (j0 + 0.5), 0.1 * (i0 + 0.5)))
    assert r["cost"] == pytest.approx(_plan_cost(steps, ((5, 0), (3, 0)), 0.1, 0.3, 0.15, 0.25, 0.1))


@pytest.mark.parametrize("seed", range(8))
def test_footsteps_match_brute_force_on_small_grids(seed):
    rng = np.random.default_rng(seed)
    m = rng.random((4, 7)) > 0.3
    m[[0, 2], 0] = True
    start = ((2, 0), (0, 0))
    args = (0.1, start, 5, 0.2, 0.1, 0.3)
    r = L.footstep_plan(m, *args, deviation_weight=0.3)
    bf = _brute_force(m, 0.1, start, 5, 0.2, 0.1, 0.3, 0.3, max_steps=10)
    if math.isinf(bf):
        assert r["reached"] is False and math.isinf(r["cost"]) and r["steps"] == []
    else:
        assert r["reached"] is True
        assert r["cost"] == pytest.approx(bf, abs=1e-9)
        assert len(r["steps"]) >= 1
        assert r["cost"] == pytest.approx(_plan_cost(r["steps"], start, 0.1, 0.2, 0.1, 0.3, 0.3), abs=1e-9)
        assert all(m[s["cell"]] for s in r["steps"])


def test_footsteps_unreachable_and_fail_closed():
    m = np.ones((5, 10), bool)
    m[:, 4:7] = False                                            # 0.3 m の溝、歩幅 0.2 m では越えられない
    r = L.footstep_plan(m, 0.1, ((3, 0), (1, 0)), 8, 0.2, 0.1, 0.3)
    assert r["reached"] is False and r["cost"] == math.inf and r["steps"] == []
    with pytest.raises(ValueError):
        L.footstep_plan(np.zeros((0, 4), bool), 0.1, ((0, 0), (0, 0)), 2, 0.2, 0.1, 0.3)
    with pytest.raises(ValueError):
        L.footstep_plan(m, 0.1, ((9, 0), (1, 0)), 8, 0.2, 0.1, 0.3)
    with pytest.raises(ValueError):
        L.footstep_plan(m, 0.1, ((3, 0), (1, 0)), 8, 0.2, 0.3, 0.1)


# ── 6. 静的な接触力 ───────────────────────────────────────────────────────────
def test_symmetric_two_feet_share_the_weight_equally():
    up = np.tile([0.0, 0.0, 1.0], (2, 1))
    for half in (0.05, 0.1, 0.17):
        P = np.array([[0.0, half, 0.0], [0.0, -half, 0.0]])
        r = L.static_contact_force_lp(P, up, [0.0, 0.0, 0.9], 50.0, 0.8)
        assert r["feasible"] is True
        np.testing.assert_allclose(r["normal"], [50 * 9.81 / 2] * 2, rtol=1e-9)
        assert np.max(r["tangential"]) < 1e-9
        assert max(r["residual"]) < 1e-8


def test_flat_ground_feasibility_equals_com_inside_support_polygon():
    rng = np.random.default_rng(7)
    up = np.tile([0.0, 0.0, 1.0], (4, 1))
    feet = np.array([[0.0, 0.0, 0.0], [0.3, 0.02, 0.0], [0.28, 0.22, 0.0], [0.03, 0.2, 0.0]])
    agree, judged = 0, 0
    for _ in range(80):
        com = np.r_[rng.uniform(-0.1, 0.4, 2), 0.85]
        m = L.com_support_margin(com, feet)
        if abs(m) < 1e-4:
            continue
        r = L.static_contact_force_lp(feet, up, com, 40.0, 2.0)
        judged += 1
        agree += (r["feasible"] is True) == (m > 0)
        if r["feasible"]:
            assert max(r["residual"]) < 1e-7
            assert np.all(r["normal"] >= -1e-9)
            # 法線力の重心 = COM の射影(モーメントの釣り合い)
            np.testing.assert_allclose((r["normal"][:, None] * feet[:, :2]).sum(0) / r["normal"].sum(),
                                       com[:2], atol=1e-8)
    assert judged >= 70 and agree == judged


def test_pyramid_is_an_inner_approximation_of_the_cone():
    mu = 0.6
    th, az = np.arctan(0.85 * mu), np.radians(45.0)               # 斜め 45 度、tan = 0.85 μ
    n = np.array([np.sin(th) * np.cos(az), np.sin(th) * np.sin(az), np.cos(th)])
    P = np.array([[0.1, -0.1, 0.0], [-0.1, 0.1, 0.0]])
    N = np.tile(n, (2, 1))
    assert L.static_contact_force_lp(P, N, [0, 0, 0.8], 30, mu, n_facets=4)["feasible"] is False   # cos 45° μ < 0.85 μ
    r8 = L.static_contact_force_lp(P, N, [0, 0, 0.8], 30, mu, n_facets=8)
    assert r8["feasible"] is True                                    # cos 22.5° μ > 0.85 μ
    # 力は錐の中(真の円錐で検査): 接線 ≤ μ · 法線
    assert np.all(r8["tangential"] <= mu * r8["normal"] + 1e-9)
    assert L.static_contact_force_lp(P, N, [0, 0, 0.8], 30, 0.0)["feasible"] is False   # 摩擦なしの斜面
    with pytest.raises(ValueError):
        L.static_contact_force_lp(np.zeros((0, 3)), np.zeros((0, 3)), [0, 0, 1], 1.0, 0.5)
    with pytest.raises(ValueError):
        L.static_contact_force_lp(P, N, [0, 0, 0.8], -1.0, mu)


# ── 7. 台帳 ───────────────────────────────────────────────────────────────────
WALK_OPS = ["elevation_map", "fill_gaps", "elevation_traversability", "foothold_score", "ground_surface",
            "ground_plane", "detect_obstacles", "fuse_elevation", "roughness_map",
            "elevation_normals", "elevation_step_edges", "foothold_candidates",
            "contact_points", "com_from_silhouette", "support_polygon", "com_support_margin",
            "gait_phase", "support_line_margin", "lipm_capture_point", "capture_margin",
            "gait_step_events", "foot_slip_metrics", "footstep_plan", "static_contact_force_lp"]


def test_the_walking_ops_are_in_the_ledger_and_callable_by_name():
    import fullseye as fs
    import opsdrive

    assert len(WALK_OPS) == 24
    cats = {n: opsdrive.OPSDRIVE[n]["category"] for n in WALK_OPS}
    assert set(cats.values()) == {"walkterrain", "locomotion"}
    assert "slope_map" not in opsdrive.OPSDRIVE            # dem_slope に寄せた
    assert "surface_normals" not in opsdrive.OPSDRIVE      # ops3d の名前と重なる
    assert "terrain_surface_normals" not in opsdrive.OPSDRIVE   # facade の正式名と重なる
    assert "traversability" not in opsdrive.OPSDRIVE and "step_edges" not in opsdrive.OPSDRIVE
    feet = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0.0]])
    out = fs.op_run("support_polygon", feet)
    res = out[0] if isinstance(out, tuple) else out
    assert res["area"] == pytest.approx(0.5)
    m = fs.op_run("support_line_margin", np.array([0.5, 0.2, 0.9]), feet[:2])
    m = m[0] if isinstance(m, tuple) else m
    assert m == pytest.approx(-0.2)


def test_step_edges_ledger_door_matches_the_raw_function():
    import terrain

    g = np.zeros((10, 12))
    g[:, 6:] = 0.1
    a = terrain.elevation_step_edges(g)
    b = terrain.step_edges(g, cell=0.05)
    c = terrain.step_edges(g, cell=0.5)                    # cell は値を変えない(だから台帳の入口から外した)
    for x, y in ((a, b), (b, c)):
        assert np.array_equal(x[0], y[0]) and np.array_equal(x[1], y[1])
    assert a[0].sum() > 0


def test_module_docstring_call_example_runs():
    """locomotion の docstring の呼び出し例をそのまま実行する(説明のコード例は走らせる門が無いと静かに壊れる)。"""
    doc = L.__doc__
    i = doc.index("呼び出し例")
    block = doc[i:].split("::", 1)[1]
    lines = []
    for ln in block.splitlines()[1:]:
        if ln.strip() and not ln.startswith("    "):
            break
        lines.append(ln[4:])
    code = "\n".join(lines)
    assert "footstep_plan" in code and "static_contact_force_lp" in code
    exec(compile(code, "<locomotion doc>", "exec"), {})


# ── 8. 試作からの依頼(2026-11-08): 幅 1 の軸で traversability / foothold_score が落ちない ──
def test_traversability_and_foothold_score_accept_a_width_one_axis():
    import terrain
    row = np.array([[0.0, 0.02, 0.04, 0.2, 0.2]])                 # (1, 5): 1 行だけの高さ図
    ok = terrain.traversability(row, cell=0.05, max_step=0.1, max_slope=0.6)
    sc = terrain.foothold_score(row, cell=0.05)
    assert ok.shape == sc.shape == (1, 5)
    assert ok.tolist() == [[True, True, False, False, True]]    # 段の上の端は平ら(窓の中も 0.2 だけ)
    assert np.all(np.isfinite(sc)) and sc[0, 0] > sc[0, 3]
    assert terrain.foothold_candidates(row.T, cell=0.05, min_score=0.0) != []
    # 2 以上の軸では値が変わらない(np.gradient と同じ)
    g = np.random.default_rng(0).normal(0, 0.02, (9, 11))
    gy, gx = np.gradient(g, 0.05)
    slope = np.hypot(gx, gy)
    assert np.array_equal(terrain.traversability(g, cell=0.05, max_step=1.0, max_slope=0.6),
                          (slope <= 0.6) & (np.ptp(g) <= 1.0))
