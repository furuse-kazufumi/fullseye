# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""drivecrossing の門: 閉形式を独立な経路(時間の行進・状態の再生・光線の総当たり・格子・二分法)で検算する。"""
from __future__ import annotations

import math

import numpy as np
import pytest

import drivecrossing as DC
import drivedecide as DD


# ───────────────────────── 独立な経路の道具 ─────────────────────────
def march_arrival(D, v0, a, vmax, dt=1e-4):
    """一定の加速度で上限まで、を小さな刻みで進め、距離 D に着く時刻(線形補間)。閉形式と別の経路。"""
    x, v, t = 0.0, v0, 0.0
    while True:
        v1 = min(v + a * dt, vmax)
        x1 = x + 0.5 * (v + v1) * dt
        if x1 >= D:
            return t + (D - x) / (x1 - x) * dt
        x, v, t = x1, v1, t + dt


def approach_traj(stop_at, wait, *, v_app=8.0, a=1.5, decel=2.0, x0=-60.0, dt=0.02, t_end=40.0, go_after_stop=True):
    """近づいて stop_at(前端)で止まり、wait 秒待ってから一定の加速度で発進する軌跡。stop_at=None なら止まらない。"""
    t = np.arange(0.0, t_end, dt)
    x = np.empty_like(t)
    v = np.empty_like(t)
    if stop_at is None:
        x[:] = x0 + v_app * t
        v[:] = v_app
        return {"t": t, "x": x, "v": v}
    d_brake = v_app * v_app / (2 * decel)
    t_b0 = (stop_at - d_brake - x0) / v_app
    t_b1 = t_b0 + v_app / decel
    t_go = t_b1 + wait
    for i, ti in enumerate(t):
        if ti < t_b0:
            x[i], v[i] = x0 + v_app * ti, v_app
        elif ti < t_b1:
            s = ti - t_b0
            x[i], v[i] = stop_at - d_brake + v_app * s - 0.5 * decel * s * s, v_app - decel * s
        elif ti < t_go or not go_after_stop:
            x[i], v[i] = stop_at, 0.0
        else:
            s = ti - t_go
            x[i], v[i] = stop_at + 0.5 * a * s * s, a * s
    return {"t": t, "x": x, "v": v, "t_go": t_go, "t_stop": t_b1}


# ───────────────────────── 1. 時刻 ─────────────────────────
def test_timing_check_standard_and_minimum():
    r = DC.crossing_timing_check(0.0, 15.0, 35.0)
    assert r["warn_to_closed"] == 15.0 and r["closed_to_arrival"] == 20.0 and r["warn_to_arrival"] == 35.0
    assert r["meets_minimum"] is True
    assert r["deviation"]["warn_to_arrival"] == 5.0
    bad = DC.crossing_timing_check(0.0, 9.9, 30.0)          # 遮断まで 10 秒未満
    assert bad["meets_minimum"] is False
    bad2 = DC.crossing_timing_check(0.0, 10.0, 19.0)         # 到達まで 20 秒未満(遮断後 9 秒)
    assert bad2["meets_minimum"] is False
    edge = DC.crossing_timing_check(0.0, 10.0, 25.0)         # 最小ちょうど(10 / 15 / 25 ≥ 20)
    assert edge["meets_minimum"] is True
    # 列車ごと: 始動点が固定だと遅い列車ほど警報が長い(5(4) の量 = spread)
    v = np.array([130.0, 80.0, 40.0]) / 3.6
    d = 30.0 * 130.0 / 3.6
    arr = d / v
    rr = DC.crossing_timing_check(np.zeros(3), np.full(3, 15.0), arr)
    assert rr["spread"] == pytest.approx(arr.max() - arr.min())
    assert rr["meets_minimum"].shape == (3,)
    with pytest.raises(ValueError):
        DC.crossing_timing_check(0.0, 20.0, 10.0)


def replay_state(t, tw, tl, ld, tcl, rd):
    """状態を 1 刻みずつの遷移で再生する(閉形式の分類と別の経路)。"""
    st, out = 0, []
    for ti in t:
        while True:
            if st == 0 and tw <= ti < tcl + rd and ti < tl:
                st = 1
            elif st in (0, 1) and ti >= tl and ti < tl + ld:
                st = 2
            elif st in (0, 1, 2) and ti >= tl + ld and ti < tcl:
                st = 3
            elif st in (0, 1, 2, 3) and ti >= tcl and ti < tcl + rd:
                st = 4
            elif st != 0 and (ti >= tcl + rd or ti < tw):
                st = 0
            else:
                break
        out.append(st)
    return np.array(out)


@pytest.mark.parametrize("tw,tl,ld,tcl,rd", [(5.0, 8.0, 7.0, 40.0, 6.0), (0.0, 0.0, 10.0, 10.0, 5.0), (2.5, 3.0, 12.0, 50.0, 8.0)])
def test_gate_state_equals_event_replay(tw, tl, ld, tcl, rd):
    t = np.arange(-3.0, tcl + rd + 5.0, 0.01)
    g = DC.crossing_gate_state(t, t_warning=tw, t_lower_start=tl, lower_duration=ld, t_clear=tcl, raise_duration=rd)
    ref = replay_state(t, tw, tl, ld, tcl, rd)
    assert t.size > 100
    assert np.array_equal(g["state"], ref)
    # かんの角は連続(状態の境で跳ばない)・範囲 [0, π/2]
    assert np.max(np.abs(np.diff(g["boom_angle"]))) < 0.01 * math.pi / min(ld, rd) * 1.01 + 1e-12
    assert g["boom_angle"].min() >= 0 and g["boom_angle"].max() <= math.pi / 2 + 1e-12
    assert np.array_equal(g["lamps_on"], (ref >= 1) & (ref <= 3))
    assert g["t_closed"] == tl + ld


def test_gate_state_rejects_bad_order():
    with pytest.raises(ValueError):
        DC.crossing_gate_state([0.0], t_warning=5.0, t_lower_start=4.0, lower_duration=5.0, t_clear=30.0, raise_duration=5.0)
    with pytest.raises(ValueError):
        DC.crossing_gate_state([0.0], t_warning=0.0, t_lower_start=4.0, lower_duration=50.0, t_clear=30.0, raise_duration=5.0)


# ───────────────────────── 2. 警報灯 ─────────────────────────
@pytest.mark.parametrize("fpm,duty,exp", [(50.0, 0.5, 0.03), (55.0, 0.4, 0.25), (45.0, 0.6, 1.7)])
def test_lamp_exposure_closed_form_equals_fine_average(fpm, duty, exp):
    t = np.linspace(-0.5, 9.0, 37)
    got = DC.crossing_lamp_signal(t, t_on=0.0, t_off=8.0, flash_per_min=fpm, duty=duty, exposure=exp)
    sub = np.linspace(0.0, exp, 20001)[:-1] + exp / 40000.0
    ref = np.stack([DC.crossing_lamp_signal(ti + sub, t_on=0.0, t_off=8.0, flash_per_min=fpm, duty=duty).mean(0) for ti in t])
    assert np.max(np.abs(got - ref)) < 2e-4


def test_lamp_alternates_and_frequency_recovered():
    fps = 30.0
    t = np.arange(0.0, 24.0, 1.0 / fps)
    L = DC.crossing_lamp_signal(t, t_on=0.0, t_off=100.0)
    assert not np.any((L[:, 0] > 0) & (L[:, 1] > 0))            # 交互(同時に点かない)
    assert L[:, 0].sum() > 0 and L[:, 1].sum() > 0
    f = DD.flash_frequency(L[:, 0], fps)["frequency"]
    assert f == pytest.approx(50.0 / 60.0, abs=0.01)
    # 時間間隔の粗いカメラ(1 fps)では折り返して見える
    t1 = np.arange(0.0, 240.0, 1.0)
    L1 = DC.crossing_lamp_signal(t1, t_on=0.0, t_off=1e3, exposure=0.02)
    f1 = DD.flash_frequency(L1[:, 0], 1.0)["frequency"]
    assert f1 == pytest.approx(DD.aliased_frequency(50.0 / 60.0, 1.0), abs=0.01)


@pytest.mark.parametrize("phi", [0.0, 0.7, 1.6, 2.5, math.pi])
def test_lamp_pair_phase_recovers_known_shift(phi):
    fps, f = 25.0, 0.9
    t = np.arange(0.0, 20.0, 1.0 / fps)
    a = np.sin(2 * math.pi * f * t)
    b = np.sin(2 * math.pi * f * t - phi)
    r = DC.lamp_pair_phase(a, b, fps)
    assert r["phase"] == pytest.approx(phi, abs=0.05)
    assert r["frequency"] == pytest.approx(f, abs=0.02)
    assert r["alternating"] == (abs(phi - math.pi) < 0.25)


def test_lamp_pair_phase_on_square_lamps_and_constant():
    fps = 12.0
    t = np.arange(0.0, 30.0, 1.0 / fps)
    L = DC.crossing_lamp_signal(t, t_on=0.0, t_off=1e3, exposure=1.0 / fps)
    r = DC.lamp_pair_phase(L[:, 0], L[:, 1], fps)
    assert r["alternating"] and r["phase"] == pytest.approx(math.pi, abs=0.1)
    assert r["delay"] == pytest.approx(0.6, abs=0.03)                # P/2 = 0.6 s
    same = DC.lamp_pair_phase(L[:, 0], L[:, 0], fps)
    assert not same["alternating"] and same["phase"] < 1e-6
    with pytest.raises(ValueError):
        DC.lamp_pair_phase(np.ones(50), L[:50, 0], fps)


# ───────────────────────── 3. 渡り切る ─────────────────────────
@pytest.mark.parametrize("e,Lc,Lv,a,vmax,v0", [(2.0, 10.0, 4.5, 1.5, 20 / 3.6, 0.0), (1.0, 30.0, 12.0, 0.8, 15 / 3.6, 0.0),
                                                (2.0, 10.0, 4.5, 2.0, 50 / 3.6, 0.0), (0.0, 6.0, 4.5, 1.0, 10.0, 3.0),
                                                (0.0, 6.0, 4.5, 0.0, 5.0, 5.0), (0.0, 20.0, 4.5, 1.0, 5.0, 3.0)])
def test_clear_time_equals_march(e, Lc, Lv, a, vmax, v0):
    r = DC.crossing_clear_time(e, Lc, Lv, accel=a, v_max=vmax, v0=v0)
    D = e + Lc + Lv + 0.5
    assert r["distance"] == pytest.approx(D)
    assert r["time"] == pytest.approx(march_arrival(D, v0, a, vmax), abs=2e-3)
    if e > 0:
        assert r["t_on_track"] == pytest.approx(march_arrival(e, v0, a, vmax), abs=2e-3)


def test_exit_room_equals_placing_the_car():
    far, Lv, g, bm = 12.0, 4.5, 1.0, 0.5
    q = np.r_[far + np.linspace(0.0, 10.0, 41), far + Lv + g + bm + np.array([-1e-3, 0.0, 1e-3])]
    r = DC.exit_room_check(q, far, Lv, gap=g, beyond=bm)
    ref = []
    for qi in q:                                            # 前端を前の車の後ろ g まで進めて、後端が余裕の向こうか
        front = 0.0
        while front + 1e-4 <= qi - g + 1e-12:
            front += 1e-4
        ref.append(front - Lv >= far + bm - 2e-4)
    assert q.size > 40
    assert np.array_equal(r["ok"], np.array(ref))
    assert DC.exit_room_check(np.inf, far, Lv)["ok"] is True


SL, CS, CE, LV = 0.0, 2.0, 12.0, 4.5


def test_stop_check_truth_table():
    good = approach_traj(-0.5, 4.0)
    tg = good["t_go"]
    look_ok = [(good["t_stop"] + 0.5, "left"), (good["t_stop"] + 1.5, "right")]
    cases = {
        "good": (good, look_ok, (), None, False, []),
        "no_stop": (approach_traj(None, 0), look_ok, (), None, False, ["no_stop"]),
        "stop_far_back": (approach_traj(-5.0, 4.0), look_ok, (), None, False, ["no_stop"]),
        "one_side": (good, look_ok[:1], (), None, False, ["no_look"]),
        "looked_too_early": (good, [(good["t_stop"] - 3.0, "left"), (good["t_stop"] - 2.5, "right")], (), None, False,
                             ["no_look"]),
        "during_warning": (good, look_ok, [(tg - 1.0, tg + 30.0)], None, False, ["entered_while_forbidden"]),
        "no_exit_room": (good, look_ok, (), CE + 3.0, False, ["no_exit_room"]),
        "signal_exempt": (approach_traj(None, 0), [], (), None, True, []),
    }
    assert len(cases) == 8
    for name, (tr, lk, fb, q, sig, want) in cases.items():
        r = DC.crossing_stop_check(tr, stop_line=SL, crossing_start=CS, crossing_end=CE, car_length=LV, look_events=lk,
                                   forbidden_intervals=fb, queue_rear=q, signal_controlled=sig)
        assert r["violations"] == want, name
    # 発進の直後に警報が始まった: 止まれない位置(前端が踏切の 0.2 m 手前、2 m/s 超)なら brake_max で例外、止まれる位置なら違反
    t_late = tg + math.sqrt(2.0 * (CS - 0.2 - (-0.5)) / 1.5)            # 前端が CS − 0.2 に着く時刻(加速 1.5)
    t_early = tg + 0.3                                                 # まだ 7 cm しか進んでいない
    for tw, want in ((t_late, True), (t_early, False)):
        r = DC.crossing_stop_check(good, stop_line=SL, crossing_start=CS, crossing_end=CE, car_length=LV, look_events=look_ok,
                                   forbidden_intervals=[(tw, tw + 30.0)], brake_max=4.0)
        assert r["unavoidable"] is want and (r["violations"] == []) is want
    r = DC.crossing_stop_check(good, stop_line=SL, crossing_start=CS, crossing_end=CE, car_length=LV, look_events=look_ok,
                               forbidden_intervals=[(t_late, t_late + 30.0)])
    assert r["violations"] == ["entered_while_forbidden"]                # 既定(brake_max なし)は例外を作らない
    # 踏切の中で止まった(前端 5 m、車体は踏切の上)
    inside = approach_traj(5.0, 2.0)
    r = DC.crossing_stop_check(inside, stop_line=SL, crossing_start=CS, crossing_end=CE, car_length=LV)
    assert "stopped_inside" in " / ".join(r["violations"])
    # 入らなかった(停止線で待ち続ける)
    wait = approach_traj(-0.5, 100.0)
    r = DC.crossing_stop_check(wait, stop_line=SL, crossing_start=CS, crossing_end=CE, car_length=LV)
    assert r["entered"] is False and r["ok"]


# ───────────────────────── 4. 見通し ─────────────────────────
def test_track_sight_distance_equals_crossing_simulation():
    """列車がちょうど必要な距離にいれば渡り切った瞬間に着き、少し近ければ車が線路の上にいる間に着く。"""
    tc = DC.crossing_clear_time(2.0, 6.0, 4.5, accel=1.5, v_max=20 / 3.6)
    t_on, t_off = tc["t_on_track"], tc["time"]
    for vk in (40.0, 95.0, 130.0):
        v = vk / 3.6
        need = DC.track_sight_distance(v, t_off)
        for d, hit in ((need * 1.001, False), (need * 0.97, True)):
            arr = d / v
            t = np.linspace(0.0, t_off * 1.2, 20001)
            car_on = (t >= t_on) & (t < t_off)
            train_at = np.abs(d - v * t) < v * (t[1] - t[0])          # 列車の先頭が踏切の位置にいる刻み
            assert (car_on & train_at).any() == hit, (vk, d)
            assert (arr < t_off) == hit
        # 余裕 m を足した距離にいる列車は、渡り切ってからちょうど m 秒後に着く(列車の行進で確かめる)
        m = 2.0
        dm = DC.track_sight_distance(v, t_off, margin=m)
        tt = np.arange(0.0, 3 * (t_off + m), 1e-3)
        t_arr = tt[np.argmax(dm - v * tt <= 0.0)]
        assert t_arr - t_off == pytest.approx(m, abs=2e-3)


def los_blocked(E, P, xc, dc, n=4001):
    s = np.linspace(0.0, 1.0, n)
    X = E[0] + s * (P[0] - E[0])
    Y = E[1] + s * (P[1] - E[1])
    return bool(np.any((X >= xc) & (Y <= -dc)))


@pytest.mark.parametrize("xe,de,xc,dc", [(0.0, 5.0, 3.0, 2.0), (-0.4, 4.0, 2.5, 3.0), (0.5, 8.0, 6.0, 1.0)])
def test_sight_triangle_equals_ray_casting(xe, de, xc, dc):
    xv = DC.sight_triangle_distance(xe, de, xc, dc)
    xs = np.linspace(xc, xv * 3.0, 3001)
    vis = np.array([not los_blocked((xe, -de), (x, 0.0), xc, dc) for x in xs])
    assert vis.size > 1000
    far = xs[vis].max()
    assert far == pytest.approx(xv, abs=2.0 * (xs[1] - xs[0]) + 1e-3 * xv)
    assert DC.sight_triangle_distance(xe, de, xc, de + 0.1) == math.inf


# ───────────────────────── 5. 交差点の優先 ─────────────────────────
def test_priority_truth_table():
    n = {"width": 4.0}
    w = {"width": 8.0}
    pr = {"width": 6.0, "centre_line": True}
    cases = [(n, w, "cross", True), (w, n, "none", False), (n, {"width": 5.0}, "left", False), (n, pr, "cross", True),
             (pr, w, "none", False), (pr, {"width": 5.0, "priority_sign": True}, "left", False), (n, {"width": 5.9}, "left", False),
             (n, {"width": 6.0}, "cross", True)]
    assert len(cases) == 8
    for own, cross, y, slow in cases:
        r = DC.priority_rule(own, cross)
        assert (r["yield_to"], r["must_slow"]) == (y, slow), (own, cross, r)
    with pytest.raises(ValueError):
        DC.priority_rule(n, w, signalised=True)


def test_priority_is_antisymmetric():
    """A が交差道路に譲る ⇔ B は譲られる側。左方優先は両側とも 'left'。"""
    rng = np.random.default_rng(3)
    roads = [{"width": float(wd), "centre_line": bool(c), "priority_sign": bool(s)}
             for wd, c, s in zip(rng.choice([3.0, 4.0, 5.5, 6.0, 8.0, 12.0], 30), rng.random(30) < 0.3, rng.random(30) < 0.15)]
    pairs = [(a, b) for a in roads for b in roads]
    assert len(pairs) == 900
    kinds = set()
    for a, b in pairs:
        ra, rb = DC.priority_rule(a, b), DC.priority_rule(b, a)
        kinds.add(ra["yield_to"])
        assert {ra["yield_to"], rb["yield_to"]} in ({"cross", "none"}, {"left"})
        assert ra["must_slow"] == (ra["yield_to"] == "cross")
    assert kinds == {"cross", "none", "left"}


@pytest.mark.parametrize("d,zl,Lv,v0,a,vmax", [(10.0, 6.0, 4.5, 0.0, 1.5, 6.0), (-2.0, 6.0, 4.5, 3.0, 1.0, 8.0),
                                               (30.0, 7.0, 4.5, 11.0, 0.0, None), (3.0, 3.0, 4.5, 0.0, 2.0, 30.0)])
def test_conflict_intervals_equal_march(d, zl, Lv, v0, a, vmax):
    r = DC.conflict_zone_intervals(d, zl, Lv, v0=v0, accel=a, v_max=vmax)
    vm = vmax if vmax is not None else (v0 if a == 0 else 1e12)
    ti = march_arrival(d, v0, a, vm) if d > 0 else 0.0
    to = march_arrival(d + zl + Lv, v0, a, vm)
    assert r["t_in"] == pytest.approx(ti, abs=2e-3) and r["t_out"] == pytest.approx(to, abs=2e-3)


def arrival_with_decel(d, v, a, dt=1e-3, t_max=60.0):
    x, vv, t = 0.0, v, 0.0
    while t < t_max:
        v1 = max(vv - a * dt, 0.0)
        x1 = x + 0.5 * (vv + v1) * dt
        if x1 >= d:
            return t + (d - x) / (x1 - x) * dt
        if v1 == 0.0:
            return math.inf
        x, vv, t = x1, v1, t + dt
    return math.inf


@pytest.mark.parametrize("d,v,T", [(40.0, 11.0, 5.0), (25.0, 12.0, 3.0), (30.0, 10.0, 8.0), (50.0, 14.0, 2.0), (20.0, 8.0, 9.0)])
def test_obstruction_decel_equals_bisection(d, v, T):
    r = DC.obstruction_decel(d, v, T)
    lo, hi = 0.0, 50.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if arrival_with_decel(d, v, mid) >= T:
            hi = mid
        else:
            lo = mid
    ref = hi if arrival_with_decel(d, v, 0.0) < T else 0.0
    assert r["decel"] == pytest.approx(ref, abs=0.02 + 0.01 * ref)
    assert r["obstructs"] == (r["decel"] > 2.0)


def test_obstruction_decel_edges():
    assert DC.obstruction_decel(10.0, 5.0, 1.0)["decel"] == 0.0           # 減速しなくても間に合う
    assert DC.obstruction_decel(0.0, 0.0, 3.0)["decel"] == 0.0
    assert DC.obstruction_decel(-1.0, 5.0, 3.0)["decel"] == math.inf       # もう領域にいる


# ───────────────────────── 6. 横断歩道 ─────────────────────────
def lin(x0, v, t):
    return {"t": t, "x": x0 + v * t, "v": np.full_like(t, v)}


def test_overtake_check_zone_and_exemptions():
    t = np.linspace(0.0, 30.0, 3001)
    ego = lin(0.0, 14.0, t)
    cw0, cw1 = 200.0, 204.0
    # 相手 x0 + 8 t、追いつく時刻 te = x0 / 6、その位置 14 te
    for x0, want_in in ((70.0, False), (80.0, True), (87.0, True), (90.0, False)):
        o = dict(lin(x0, 8.0, t), kind="car")
        r = DC.crosswalk_overtake_check(ego, [o], crosswalk_start=cw0, crosswalk_end=cw1)
        assert len(r["events"]) == 1
        e = r["events"][0]
        assert e["x"] == pytest.approx(14.0 * x0 / 6.0, abs=1e-6)
        assert e["in_zone"] == (cw0 - 30.0 <= 14.0 * x0 / 6.0 <= cw1) == want_in
        assert r["ok"] == (not want_in)
    bike = dict(lin(80.0, 5.0, t), kind="bicycle")
    rb = DC.crosswalk_overtake_check(ego, [bike], crosswalk_start=cw0 - 60, crosswalk_end=cw1)
    assert len(rb["events"]) == 1 and rb["events"][0]["exempt"] and rb["ok"]
    parked = dict(lin(180.0, 0.0, t), kind="car")                      # 進行していない(38 条 2 項の側)
    rp = DC.crosswalk_overtake_check(ego, [parked], crosswalk_start=cw0, crosswalk_end=cw1)
    assert len(rp["events"]) == 1 and not rp["events"][0]["moving"] and rp["ok"]


def test_stopped_vehicle_check():
    cw0, cw1 = 0.0, 4.0
    stopped = [{"x": -1.0, "t0": 0.0, "t1": 100.0}]
    tr = approach_traj(-4.0, 1.5, x0=-80.0)                     # 横に並ぶ手前で一時停止してから
    r = DC.crosswalk_stopped_vehicle_check(tr, stopped, crosswalk_start=cw0, crosswalk_end=cw1)
    assert len(r["events"]) == 1 and r["ok"]
    nost = approach_traj(None, 0, x0=-80.0)
    r2 = DC.crosswalk_stopped_vehicle_check(nost, stopped, crosswalk_start=cw0, crosswalk_end=cw1)
    assert len(r2["events"]) == 1 and not r2["ok"]
    early = approach_traj(-25.0, 2.0, x0=-80.0)                 # 25 m 手前で止まっただけ
    r3 = DC.crosswalk_stopped_vehicle_check(early, stopped, crosswalk_start=cw0, crosswalk_end=cw1)
    assert not r3["ok"]
    far = [{"x": -20.0, "t0": 0.0, "t1": 100.0}]                 # 横断歩道から離れた停止車は対象外
    r4 = DC.crosswalk_stopped_vehicle_check(nost, far, crosswalk_start=cw0, crosswalk_end=cw1)
    assert r4["events"] == [] and r4["ok"]


# ───────────────────────── 7. 駐停車禁止 ─────────────────────────
FEAT = [{"kind": "intersection", "start": 50.0, "end": 62.0}, {"kind": "crosswalk", "start": 64.0, "end": 68.0},
        {"kind": "railway_crossing", "start": 150.0, "end": 160.0}, {"kind": "bus_stop", "at": 220.0},
        {"kind": "corner", "start": 300.0, "end": 300.0}, {"kind": "safety_zone", "start": 340.0, "end": 352.0}]


def test_no_stopping_zones_equal_grid():
    z = DC.no_stopping_zones(FEAT)
    M = z["merged"]
    assert len(M) > 0
    assert np.all(M[:, 1] > M[:, 0]) and np.all(M[1:, 0] > M[:-1, 1])
    xs = np.linspace(0.0, 400.0, 400001)
    ref = np.zeros(xs.shape, bool)
    for f in FEAT:                                                  # 条文の距離を直接(号ごと)
        s = f.get("start", f.get("at"))
        e = f.get("end", f.get("at"))
        d = {"intersection": 5, "crosswalk": 5, "railway_crossing": 10, "bus_stop": 10, "corner": 5, "safety_zone": 10}[f["kind"]]
        ref |= (xs >= s - d) & (xs <= e + d)
    got = np.zeros(xs.shape, bool)
    for a, b in M:
        got |= (xs >= a) & (xs <= b)
    assert np.array_equal(got, ref)
    # 交差点(45..67)と横断歩道(59..73)は併さって 1 区間
    assert any(abs(a - 45.0) < 1e-9 and abs(b - 73.0) < 1e-9 for a, b in M)
    zn = DC.no_stopping_zones(FEAT, in_service=False)
    assert len(zn["zones"]) == len(FEAT) - 1


def test_legal_stop_intervals_and_position_check_equal_grid():
    z = DC.no_stopping_zones(FEAT)
    Lv = 4.5
    S = DC.legal_stop_intervals(z["merged"], 0.0, 400.0, Lv)
    assert len(S) > 0
    rears = np.linspace(0.0, 400.0, 8001)
    assert rears.size > 1000
    for r in rears:
        inside = any(a - 1e-9 <= r <= b + 1e-9 for a, b in S)
        chk = DC.parking_position_check(r, r + Lv, z)
        assert inside == (chk["ok"] and r + Lv <= 400.0 + 1e-9), r
    c = DC.parking_position_check(150.0, 154.5, z)
    assert not c["ok"] and "railway_crossing" in " / ".join(k for k, _ in c["reasons"])
    assert c["overlap"] == pytest.approx(4.5)


# ───────────────────────── 異常入力 ─────────────────────────
@pytest.mark.parametrize("call", [
    lambda: DC.crossing_clear_time(-1.0, 10.0, 4.5, accel=1.0, v_max=5.0),
    lambda: DC.crossing_clear_time(1.0, 10.0, 4.5, accel=0.0, v_max=5.0, v0=0.0),
    lambda: DC.crossing_clear_time(1.0, 10.0, 4.5, accel=1.0, v_max=5.0, v0=6.0),
    lambda: DC.crossing_clear_time(1.0, float("nan"), 4.5, accel=1.0, v_max=5.0),
    lambda: DC.exit_room_check(-np.inf, 0.0, 4.5),
    lambda: DC.crossing_lamp_signal([0.0], t_on=1.0, t_off=0.0),
    lambda: DC.crossing_lamp_signal([0.0], t_on=0.0, t_off=1.0, duty=1.0),
    lambda: DC.lamp_pair_phase([1, 2, 3], [1, 2, 3], 10.0),
    lambda: DC.sight_triangle_distance(0.0, 5.0, -1.0, 2.0),
    lambda: DC.sight_triangle_distance(0.0, 0.0, 1.0, 2.0),
    lambda: DC.priority_rule({"width": 0.0}, {"width": 4.0}),
    lambda: DC.priority_rule({"width": 4.0}, {"width": 4.0}, wide_ratio=0.9),
    lambda: DC.conflict_zone_intervals(-20.0, 5.0, 4.5, v0=5.0),
    lambda: DC.obstruction_decel(10.0, -1.0, 2.0),
    lambda: DC.no_stopping_zones([{"kind": "shop", "start": 0, "end": 1}]),
    lambda: DC.no_stopping_zones([{"kind": "crosswalk", "start": 5, "end": 1}]),
    lambda: DC.legal_stop_intervals([[5.0, 1.0]], 0.0, 10.0, 4.5),
    lambda: DC.parking_position_check(5.0, 5.0, {"zones": []}),
    lambda: DC.crossing_stop_check({"t": [0, 1], "x": [0, 1]}, stop_line=5.0, crossing_start=1.0, crossing_end=3.0, car_length=4.5),
    lambda: DC.crossing_stop_check({"t": [1, 0], "x": [0, 1]}, stop_line=0.0, crossing_start=1.0, crossing_end=3.0, car_length=4.5),
    lambda: DC.crossing_stop_check({"t": [0, 1], "x": [0, 1]}, stop_line=0.0, crossing_start=1.0, crossing_end=3.0, car_length=4.5,
                                   look_events=[(0.5, "up")]),
    lambda: DC.track_sight_distance(-1.0, 3.0),
])
def test_bad_inputs_raise(call):
    with pytest.raises(ValueError):
        call()
