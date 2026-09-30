# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""drivelong の門: 停止距離の閉形式(平地・上り・下り、転がり・空気抵抗つき)、rsssafety との一致(第 2 実装)、坂の保持と
坂道発進のずり下がりの閉形式、エネルギー収支、停止線の計画、技能試験の減点(公表値)と、つまみで減点が出ること。"""
from __future__ import annotations

import math

import numpy as np
import pytest

import drivelong as L
import rsssafety as R

GRADES = [0.0, math.atan(0.08), math.atan(0.11), -math.atan(0.08), -math.atan(0.11)]


def _stop_run(v, rho, b, th, p, dt=0.01):
    def cmd(t, s, vv):
        if t < rho:
            need = p["g"] * math.sin(th) + p["c_rr"] * p["g"] * math.cos(th) + p["k"] * vv * abs(vv)
            return (need, 0.0) if need >= 0 else (0.0, -need)
        return (0.0, b) if vv > 0 else (0.0, p["a_brake_max"])
    r = L.long_simulate(0.0, v, cmd, road=th, t_end=rho + 30.0, dt=dt, params=p, t_breaks=[rho])
    stops = [e for e in r["events"] if e[0] == "stop"]
    return r, stops[0][2]


# ---- 1. 停止距離 ----------------------------------------------------------------------------------
@pytest.mark.parametrize("th", GRADES)
@pytest.mark.parametrize("crr,cda", [(0.0, 0.0), (0.012, 0.0), (0.012, 0.65)])
@pytest.mark.parametrize("v", [5.0, 30 / 3.6, 60 / 3.6])
def test_stopping_distance_closed_form_vs_integrator(th, crr, cda, v):
    p = L.long_params(c_rr=crr, cda=cda, reaction=0.75)
    _, s_stop = _stop_run(v, 0.75, 4.0, th, p)
    d = L.stopping_distance_grade(v, 0.75, 4.0, th, crr, p["k"])
    assert abs(s_stop - d) < 1e-9


@pytest.mark.parametrize("dt", [0.002, 0.01, 0.05, 0.2])
def test_stopping_distance_independent_of_step(dt):
    p = L.long_params(c_rr=0.012, cda=0.0)
    _, s = _stop_run(10.0, 0.9, 3.0, math.atan(0.11), p, dt=dt)
    assert abs(s - L.stopping_distance_grade(10.0, 0.9, 3.0, math.atan(0.11), 0.012)) < 1e-9


def test_strong_drag_is_the_log_form_not_the_quadratic():
    """空気抵抗を強く(C_d A = 20)すると ln の式と v²/(2A) の差が測れる大きさになり、積分器は ln の式に付く。"""
    # 空走の間に速さを保つ駆動(c_rr g + k v² ≈ 3.8 m/s²)が上限 3.0 に掛かると空走中に減速して式の前提が崩れる
    # (最初の版はこれで 1.37 m ずれた)→ この門では駆動の上限と μ を上げる
    p = L.long_params(c_rr=0.012, cda=20.0, a_drive_max=10.0, mu=1.2)
    _, s = _stop_run(20.0, 0.5, 2.0, 0.0, p, dt=0.005)
    d_ln = L.stopping_distance_grade(20.0, 0.5, 2.0, 0.0, 0.012, p["k"])
    d_q = L.stopping_distance_grade(20.0, 0.5, 2.0, 0.0, 0.012, 0.0)
    assert d_q - d_ln > 5.0                     # 差は数 m
    assert abs(s - d_ln) < 1e-6                  # RK4 は空気抵抗の区間で厳密でない(dt⁴)


def test_uphill_shorter_downhill_longer():
    d = [L.stopping_distance_grade(10.0, 0.75, 3.0, th) for th in (math.atan(0.1), 0.0, -math.atan(0.1))]
    assert d[0] < d[1] < d[2]


def test_downhill_that_beats_the_brake_never_stops():
    assert L.stopping_distance_grade(10.0, 0.75, 0.5, -math.atan(0.11)) == math.inf


@pytest.mark.parametrize("v", [1.0, 8.0, 25.0])
@pytest.mark.parametrize("rho", [0.0, 0.75, 1.5])
@pytest.mark.parametrize("b", [2.0, 4.0, 8.0])
def test_agrees_with_rss_on_flat(v, rho, b):
    """第 2 実装: 平地・c_rr = k = 0 では rsssafety.rss_stopping_distance(v, ρ, accel=0, brake=b)。"""
    ref = R.rss_stopping_distance(v, rho, 0.0, b)
    assert abs(L.stopping_distance_grade(v, rho, b, 0.0) - ref) < 1e-12 * max(1.0, ref)
    p = L.long_params(c_rr=0.0, cda=0.0, a_brake_max=10.0, mu=1.2)
    _, s = _stop_run(v, rho, b, 0.0, p)
    assert abs(s - ref) < 1e-9


# ---- 2. 坂の保持・坂道発進 ---------------------------------------------------------------------------
@pytest.mark.parametrize("grade", [0.065, 0.08, 0.10, 0.125])
@pytest.mark.parametrize("creep", [0.0, 0.3])
def test_hill_hold_threshold(grade, creep):
    th = math.atan(grade)
    p = L.long_params(cda=0.0, a_creep=creep)
    bmin = L.hill_hold_brake_min(th, p["c_rr"], creep)
    for b, should_hold in ((bmin + 1e-9, True), (bmin - 1e-4, False)):
        r = L.long_simulate(0.0, 0.0, lambda t, s, v, b=b: (creep, b), road=th, t_end=5.0, dt=0.01, params=p)
        moved = abs(r["s"][-1]) > 0
        assert moved != should_hold


@pytest.mark.parametrize("grade", [0.065, 0.08, 0.11, 0.125])
@pytest.mark.parametrize("tau", [0.3, 0.7, 1.2])
@pytest.mark.parametrize("creep", [0.0, 0.3])
def test_hill_start_rollback_closed_form(grade, tau, creep):
    th = math.atan(grade)
    p = L.long_params(cda=0.0, a_creep=creep)
    cmd = L.hill_start_command(1.0, tau, 2.0, 3.0, a_creep=creep, technique="gap")
    r = L.long_simulate(0.0, 0.0, cmd, road=th, t_end=8.0, dt=0.01, params=p, t_breaks=cmd.t_breaks)
    rb = -min(0.0, float(r["s"].min()))
    cf = L.hill_start_rollback(th, tau, 2.0, p["c_rr"], creep)
    assert abs(rb - cf["rollback"]) < 1e-9
    assert r["s"][-1] > 0.5                      # 最後は上っていく


def test_overlap_technique_has_no_rollback():
    th = math.atan(0.125)
    p = L.long_params(cda=0.0, a_creep=0.0)
    cmd = L.hill_start_command(1.0, 0.8, 2.0, 3.0, technique="overlap")
    r = L.long_simulate(0.0, 0.0, cmd, road=th, t_end=6.0, dt=0.01, params=p, t_breaks=cmd.t_breaks)
    assert r["s"].min() >= 0.0 and r["s"][-1] > 1.0


def test_no_rollback_when_creep_beats_the_hill():
    th = math.atan(0.02)
    assert L.hill_start_rollback(th, 1.0, 2.0, 0.012, a_creep=0.3)["rollback"] == 0.0


# ---- 3. エネルギー --------------------------------------------------------------------------------
def test_energy_bookkeeping_coasting_down_the_course_slope():
    """惰行で坂道コース(緩 8 %・頂上・急 11 %)の縦断を下る: ½v² + g z + W_rr + W_drag が一定。転がりの仕事は
    c_rr g Σ cos θ_i Δl_i(区間ごとの閉形式)と一致。"""
    road = L.road_profile([[0, 0], [18.75, 1.5], [22.75, 1.5], [36.386, 0.0], [60.0, 0.0]])
    p = L.long_params()
    l_top = road["l"][2]
    r = L.long_simulate(l_top + 0.5, 0.5, lambda t, s, v: (0.0, 0.0), road=road, t_end=40.0, dt=0.01, params=p)
    res = L.long_energy_residual(r)
    assert np.abs(res).max() < 1e-9
    assert r["W_drag"][-1] > 1e-3 and r["W_rr"][-1] > 1e-3
    # 転がりの仕事(前向きだけ動いた前提 = 下りきってから平地で止まる)
    s_end = r["s"][-1]
    assert np.all(np.diff(r["s"]) >= -1e-15)
    cuts = np.clip(road["l"], l_top + 0.5, s_end)
    w_rr = sum(p["c_rr"] * p["g"] * road["cos"][i] * (cuts[i + 1] - cuts[i]) for i in range(len(road["cos"])))
    w_rr += p["c_rr"] * p["g"] * max(0.0, s_end - road["l"][-1])
    assert abs(r["W_rr"][-1] - w_rr) < 1e-9


def test_road_profile_arc_length():
    road = L.road_profile([[0, 0], [4, 3]])
    assert road["l"][-1] == pytest.approx(5.0) and road["sin"][0] == pytest.approx(0.6)
    z, sn, cs = L.road_eval(road, 2.5)
    assert z == pytest.approx(1.5) and sn == pytest.approx(0.6) and cs == pytest.approx(0.8)
    assert L.road_eval(road, 9.0) == (3.0, 0.0, 1.0)             # 端の外は平ら


# ---- 4. 停止線の計画 ------------------------------------------------------------------------------
@pytest.mark.parametrize("th", GRADES)
@pytest.mark.parametrize("dist", [15.0, 25.0, 60.0])
def test_stop_line_plan_lands_on_target(th, dist):
    p = L.long_params()
    v = 20 / 3.6
    pl = L.stop_line_plan(v, dist, th, p)
    cmd = L.plan_command(pl, road=th, params=p)
    r = L.long_simulate(0.0, v, cmd, road=th, t_end=40.0, dt=0.02, params=p, t_breaks=pl["t_breaks"])
    stop = [e for e in r["events"] if e[0] == "stop"][0]
    assert abs((dist - stop[2]) - pl["predicted_gap"]) < 1e-9
    assert abs(pl["predicted_gap"] - 0.5) < 1e-9 and pl["stages"] == 2 and not pl["saturated"]
    assert abs(r["s"][-1] - stop[2]) < 1e-12     # 止まったら保持(クリープに勝つ)
    score = L.skill_test_score([{"kind": "stop", "gap": dist - stop[2]}, {"kind": "brake", "stages": pl["stages"]}])
    assert score["total"] == 0


def test_reaction_knob_crosses_the_line():
    """つまみ = 反応時間: 閉形式のしきい値 ρ*(上限の制動で線ちょうど)の手前は止まり、越えると線を越える → 減点。"""
    v, dist = 30 / 3.6, 20.0
    p = L.long_params(cda=0.0)
    A = p["a_brake_max"] + p["c_rr"] * p["g"]
    rho_star = (dist - v * v / (2 * A)) / v                       # 上限の制動で前端がちょうど線に着く反応時間
    for rho, crossed in ((rho_star - 0.05, False), (rho_star + 0.05, True)):
        q = L.long_params(cda=0.0, reaction=rho)
        pl = L.stop_line_plan(v, dist, 0.0, q, margin=0.5)
        cmd = L.plan_command(pl, params=q)
        r = L.long_simulate(0.0, v, cmd, t_end=30.0, dt=0.01, params=q, t_breaks=pl["t_breaks"])
        gap = dist - [e for e in r["events"] if e[0] == "stop"][0][2]
        assert (gap < 0) == crossed
        sc = L.skill_test_score([{"kind": "stop", "gap": gap}, {"kind": "brake", "stages": pl["stages"]}])
        assert (sc["total"] > 0) == crossed or pl["stages"] < 2


def test_mu_knob_caps_the_brake():
    v, dist = 30 / 3.6, 14.0
    dry = L.long_params(mu=0.8, cda=0.0)
    wet = L.long_params(mu=0.3, cda=0.0)
    assert L.stop_line_plan(v, dist, 0.0, dry)["predicted_gap"] >= 0
    pl = L.stop_line_plan(v, dist, 0.0, wet)
    assert pl["saturated"] and pl["predicted_gap"] < 0


# ---- 5. 採点(公表値) -----------------------------------------------------------------------------
def test_score_points_from_the_notice():
    sc = L.skill_test_score([{"kind": "stop", "gap": 2.5}], venue="場内")
    assert sc["deductions"][0][:2] == ("停止位置不適", 5)
    assert L.skill_test_score([{"kind": "start", "rollback": 0.35}])["deductions"][0][:2] == ("逆行小", 10)
    assert L.skill_test_score([{"kind": "start", "rollback": 0.7}])["deductions"][0][:2] == ("逆行中", 20)
    big = L.skill_test_score([{"kind": "start", "rollback": 1.2}])
    assert big["test_stopped"] and big["score"] is None
    assert L.skill_test_score([{"kind": "start", "rollback": 0.1, "delay": 4.0}], venue="路上")["deductions"][0][:2] == ("発進手間どり", 10)
    assert L.skill_test_score([{"kind": "start", "rollback": 0.1, "delay": 4.0}], venue="場内")["deductions"][0][:2] == ("発進手間どり", 5)
    assert L.skill_test_score([{"kind": "brake", "stages": 1}])["deductions"][0][:2] == ("制動操作不良", 5)
    assert L.skill_test_score([{"kind": "hold", "creep": 0.2}], venue="路上")["deductions"][0][:2] == ("制動操作不良(クリープ)", 10)
    assert L.skill_test_score([{"kind": "stop", "gap": -3.0, "signal": "red"}])["test_stopped"]
    ok = L.skill_test_score([{"kind": "stop", "gap": 0.5}, {"kind": "start", "rollback": 0.0, "delay": 1.0}])
    assert ok["total"] == 0 and ok["passed"]


# ---- 6. fail-closed ------------------------------------------------------------------------------
def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        L.long_params(mu=0.0)
    with pytest.raises(ValueError):
        L.stopping_distance_grade(-1.0, 0.75, 3.0)
    with pytest.raises(ValueError):
        L.stopping_distance_grade(10.0, 0.75, 3.0, theta=1.0)
    with pytest.raises(ValueError):
        L.long_simulate(0.0, 1.0, lambda t, s, v: (-1.0, 0.0), t_end=1.0)
    with pytest.raises(ValueError):
        L.long_simulate(0.0, 1.0, lambda t, s, v: (float("nan"), 0.0), t_end=1.0)
    with pytest.raises(ValueError):
        L.skill_test_score([{"kind": "teleport"}])
    with pytest.raises(ValueError):
        L.road_profile([[0, 0], [0, 1]])


def test_plan_caps_before_inserting_cruise():
    """回帰: 名目の段が上限(μ g)を越える路面で、名目のまま「待ち」を入れてから頭打ちにすると待った分だけ線を越えた
    (最初の版、μ* + 0.01 で 1.85 m 越え)。上限を先に掛ければ、閉形式の下限 μ* の上では線の手前に止まる。"""
    v, dist, rho = 20 / 3.6, 16.67, 0.75
    g = L.G
    lo, hi = 0.05, 1.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if L.stopping_distance_grade(v, rho, min(6.0, mid * g), 0.0, 0.012, L.long_params()["k"]) <= dist:
            hi = mid
        else:
            lo = mid
    for mu, ok in ((hi + 0.005, True), (hi - 0.005, False)):
        q = L.long_params(mu=mu)
        pl = L.stop_line_plan(v, dist, 0.0, q)
        # 滑りやすい路面では制動が 5 s 以上続き、空気抵抗の区間の RK4 の打ち切り誤差(dt⁴)が dt = 0.02 で 1.3e-7 m まで積もる
        # (実測)→ この門は dt = 0.005
        r = L.long_simulate(0.0, v, L.plan_command(pl, params=q), t_end=60.0, dt=0.005, params=q, t_breaks=pl["t_breaks"])
        gap = dist - [e for e in r["events"] if e[0] == "stop"][0][2]
        assert (gap >= 0) == ok
        assert abs(gap - pl["predicted_gap"]) < 1e-9
