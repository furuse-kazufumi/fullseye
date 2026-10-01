# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""drivepass の門: 閉形式を独立な経路(時間の行進・Fermat の最短経路・光線追跡・見通し線の総当たり・二分法・事象の再生)
と、既存の別実装(drivetraffic・drivelong・drivedecide)と、公表値(道路構造令の視距の表)で検算する。"""
from __future__ import annotations

import math

import numpy as np
import pytest

import drivepass as DP
import drivedecide as DD
import drivelong as DLO
import drivetraffic as DT


# ───────────────────────── 独立な経路の道具 ─────────────────────────
def march_overtake(D, v0, vL, a, vmax, tlc, dt=1e-4):
    """自車と前車を小さな刻みで進め、相対の距離 D に届く時刻と、そこから tlc 後までの自車の道のり。"""
    t, xe, xl, v = 0.0, 0.0, 0.0, v0
    while True:
        v1 = min(v + a * dt, vmax)
        xe1 = xe + 0.5 * (v + v1) * dt
        xl1 = xl + vL * dt
        if xe1 - xl1 >= D:
            f = (D - (xe - xl)) / ((xe1 - xl1) - (xe - xl))
            tp = t + f * dt
            break
        t, xe, xl, v = t + dt, xe1, xl1, v1
    # 占有の終わりまで自車だけ進める
    t2, x2, v2 = 0.0, 0.0, v0
    while t2 + dt <= tp + tlc:
        v3 = min(v2 + a * dt, vmax)
        x2 += 0.5 * (v2 + v3) * dt
        v2, t2 = v3, t2 + dt
    rest = tp + tlc - t2
    v3 = min(v2 + a * rest, vmax)
    x2 += 0.5 * (v2 + v3) * rest
    return tp, x2


def ternary_min(f, lo, hi, iters=200):
    for _ in range(iters):
        m1 = lo + (hi - lo) / 3.0
        m2 = hi - (hi - lo) / 3.0
        if f(m1) < f(m2):
            hi = m2
        else:
            lo = m1
    return 0.5 * (lo + hi)


def fermat_flat(E, M, t, P):
    """平面鏡(直線 M + s t)の上で |E − S| + |S − P| を最小にする s(反射の法則を使わない経路)。"""
    def f(s):
        S = M + s * t
        return float(np.linalg.norm(E - S) + np.linalg.norm(S - P))
    return ternary_min(f, -200.0, 200.0)


def fermat_arc(E, M, n, R, P, span=1.2):
    """凸面鏡(円弧、曲率の中心 O = M − R n)の上で |E − S| + |S − P| を最小にする角 φ と点 S。"""
    t = np.array([-n[1], n[0]])
    O = M - R * n

    def pt(phi):
        return O + R * (math.cos(phi) * n + math.sin(phi) * t)

    def f(phi):
        S = pt(phi)
        return float(np.linalg.norm(E - S) + np.linalg.norm(S - P))
    phi = ternary_min(f, -span, span)
    return phi, pt(phi)


def reflect_point_on_axis_mirror(E, T, R):
    """凸面鏡(頂点 = 原点、法線 +x、曲率の中心 (−R, 0))で E と T を結ぶ反射点を、法線が二等分する条件の二分法で求める。"""
    O = np.array([-R, 0.0])

    def g(phi):
        N = np.array([math.cos(phi), math.sin(phi)])
        S = O + R * N
        uE = (E - S) / np.linalg.norm(E - S)
        uT = (T - S) / np.linalg.norm(T - S)
        s = uE + uT
        return N[0] * s[1] - N[1] * s[0], S
    lo, hi = -0.6, 0.6
    glo = g(lo)[0]
    assert glo * g(hi)[0] < 0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        gm = g(mid)[0]
        if (gm < 0) == (glo < 0):
            lo, glo = mid, gm
        else:
            hi = mid
    return g(0.5 * (lo + hi))[1]


def apparent_angle(E, S):
    """眼 E(軸の上、+x の側)から鏡の点 S を見る角(上 = 正)。"""
    return math.atan2(S[1] - E[1], E[0] - S[0])


# ───────────────────────── 1. 追越し ─────────────────────────
@pytest.mark.parametrize("v0,vL,a,vmax,tlc", [(60 / 3.6, 40 / 3.6, 1.0, 60 / 3.6, 3.0), (40 / 3.6, 40 / 3.6, 1.5, 60 / 3.6, 2.0),
                                              (30 / 3.6, 40 / 3.6, 2.0, 80 / 3.6, 0.0), (50 / 3.6, 30 / 3.6, 0.5, None, 1.0),
                                              (70 / 3.6, 50 / 3.6, 0.0, None, 2.5)])
def test_overtake_requirement_equals_march(v0, vL, a, vmax, tlc):
    r = DP.overtake_requirement(v0, vL, lead_length=4.5, ego_length=4.7, gap_back=12.0, gap_front=15.0, accel=a, v_max=vmax,
                                lane_change_time=tlc, v_oncoming=50 / 3.6, pet_min=2.0)
    D = 12.0 + 4.5 + 4.7 + 15.0
    assert r["relative_distance"] == pytest.approx(D)
    tp, s = march_overtake(D, v0, vL, a, vmax if vmax is not None else 1e9, tlc)
    assert r["t_pass"] == pytest.approx(tp, abs=2e-3)
    assert r["t_occupy"] == pytest.approx(tp + tlc, abs=2e-3)
    assert r["ego_distance"] == pytest.approx(s, abs=0.05)
    assert r["d_required"] == pytest.approx(s + 50 / 3.6 * (tp + tlc + 2.0), abs=0.1)


@pytest.mark.parametrize("ve,vb,tlc,von,pm", [(60 / 3.6, 0.0, 3.0, 50 / 3.6, 1.0), (50 / 3.6, 15 / 3.6, 2.0, 40 / 3.6, 0.0),
                                              (80 / 3.6, 60 / 3.6, 4.0, 80 / 3.6, 2.0)])
def test_overtake_requirement_constant_speed_equals_drivetraffic(ve, vb, tlc, von, pm):
    """一定の速さでは、第 8 回の passing_gap_required(別の実装)と一致する。"""
    r = DP.overtake_requirement(ve, vb, lead_length=5.0, ego_length=4.5, gap_back=8.0, gap_front=10.0,
                                lane_change_time=tlc, v_oncoming=von, pet_min=pm)
    q = DT.passing_gap_required(5.0, 10.0, 8.0, ve, von, lane_change_time=tlc, ego_length=4.5, pet_min=pm, v_obstacle=vb)
    assert r["t_occupy"] == pytest.approx(q["t_occupy"], rel=1e-12)
    assert r["d_required"] == pytest.approx(q["d_required"], rel=1e-12)
    assert r["ego_distance"] == pytest.approx(q["clear_point"], rel=1e-12)


def test_overtake_requirement_rejects_impossible():
    with pytest.raises(ValueError):
        DP.overtake_requirement(10.0, 12.0, lead_length=4.5, ego_length=4.5, gap_back=5, gap_front=5)      # 遅いまま
    with pytest.raises(ValueError):
        DP.overtake_requirement(10.0, 12.0, lead_length=4.5, ego_length=4.5, gap_back=5, gap_front=5, accel=1.0, v_max=12.0)
    with pytest.raises(ValueError):
        DP.overtake_requirement(20.0, 12.0, lead_length=4.5, ego_length=4.5, gap_back=5, gap_front=5, accel=1.0, v_max=15.0)


def _visible_by_fermat(E, M, n, w, P):
    t = np.array([-n[1], n[0]])
    s = fermat_flat(E, M, t, P)
    return abs(s) <= w and float(np.dot(P - M, n)) > 0


@pytest.mark.parametrize("cfg", [dict(lane_offset=3.5, lead_width=1.7),
                                 dict(lane_offset=3.25, lead_width=1.9, eye_xy=(0.0, -0.4), mirror_width=0.28),
                                 dict(lane_offset=3.0, lead_width=1.6, eye_xy=(0.1, -0.3), mirror_center_xy=(0.6, 0.05),
                                      mirror_width=0.22, eye_to_rear=3.2)])
def test_return_gap_equals_fermat_scan(cfg):
    """前車の輪郭の全点が Fermat の最短経路で鏡の中に映る最小の車間を二分法で求め、閉形式と比べる。"""
    r = DP.overtake_return_gap(**cfg)
    E = np.asarray(cfg.get("eye_xy", (0.0, -0.35)), float)
    M = np.asarray(cfg.get("mirror_center_xy", (0.55, 0.0)), float)
    n = r["mirror_normal"]
    w = cfg.get("mirror_width", 0.25) / 2.0
    er = cfg.get("eye_to_rear", 2.8)
    lo_, lw = cfg["lane_offset"], cfg["lead_width"]

    def outline(gap):
        xf = -er - gap
        xs = np.linspace(xf - 4.5, xf, 12)
        ys = np.linspace(lo_ - lw / 2, lo_ + lw / 2, 7)
        pts = [(x, y) for x in (xf - 4.5, xf) for y in ys] + [(x, y) for x in xs for y in (lo_ - lw / 2, lo_ + lw / 2)]
        return np.array(pts)

    def all_visible(gap):
        pts = outline(gap)
        assert len(pts) > 0
        vis = np.array([_visible_by_fermat(E, M, n, w, p) for p in pts])
        return bool(vis.all())

    lo, hi = 0.0, 200.0
    assert not all_visible(lo) and all_visible(hi)
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if all_visible(mid):
            hi = mid
        else:
            lo = mid
    assert r["gap"] == pytest.approx(hi, abs=0.02)
    assert abs(r["straight_back_s"]) <= w


def test_return_gap_feeds_overtake_requirement():
    """戻る位置まで進む手順は、余裕だけで戻るより長く対向車線にいる(必要な見通しが伸びる)。"""
    g = DP.overtake_return_gap(lane_offset=3.5, lead_width=1.7)["gap"]
    assert g > 5.0
    base = DP.overtake_requirement(60 / 3.6, 40 / 3.6, lead_length=4.5, ego_length=4.5, gap_back=15.0, gap_front=2.0,
                                   accel=1.0, v_max=60 / 3.6, lane_change_time=3.0, v_oncoming=60 / 3.6)
    mir = DP.overtake_requirement(60 / 3.6, 40 / 3.6, lead_length=4.5, ego_length=4.5, gap_back=15.0, gap_front=g,
                                  accel=1.0, v_max=60 / 3.6, lane_change_time=3.0, v_oncoming=60 / 3.6)
    assert mir["d_required"] > base["d_required"]
    assert mir["t_pass"] - base["t_pass"] == pytest.approx((g - 2.0) / (20 / 3.6), rel=1e-9)    # 上限の速さで巡航中


def zone_rule_brute(x, f, priority_road, near=30.0, vic=30.0, steep=0.10):
    """30 条の文言を 1 点ずつ当てる(閉形式の区間づくりと別の経路)。"""
    k = f["kind"]
    s = f.get("start", f.get("at"))
    e = f.get("end", f.get("at"))
    if k == "tunnel" and f.get("has_lanes"):
        return False
    if k == "intersection" and priority_road:
        return False
    if k == "downhill" and "grade" in f and abs(f["grade"]) < steep:
        return False
    if k in ("curve", "crest"):
        return s - vic <= x <= e + vic
    if k in ("intersection", "railway_crossing", "crosswalk", "bicycle_crossing"):
        return s - near <= x <= e
    return s <= x <= e


@pytest.mark.parametrize("priority_road", [False, True])
def test_no_overtaking_zones_equal_pointwise_rules(priority_road):
    feats = [{"kind": "curve", "start": 100.0, "end": 140.0}, {"kind": "crest", "at": 300.0},
             {"kind": "downhill", "start": 400.0, "end": 520.0, "grade": -0.12},
             {"kind": "downhill", "start": 600.0, "end": 650.0, "grade": -0.04},
             {"kind": "tunnel", "start": 700.0, "end": 900.0, "has_lanes": True},
             {"kind": "tunnel", "start": 950.0, "end": 1000.0},
             {"kind": "intersection", "start": 1100.0, "end": 1115.0},
             {"kind": "railway_crossing", "start": 1200.0, "end": 1210.0},
             {"kind": "crosswalk", "start": 1300.0, "end": 1304.0}, {"kind": "bicycle_crossing", "start": 1304.0, "end": 1306.0},
             {"kind": "sign", "start": 1500.0, "end": 1700.0}]
    r = DP.no_overtaking_zones(feats, priority_road=priority_road)
    M = r["merged"]
    xs = np.arange(0.0, 1800.0, 0.25)
    assert xs.size > 1000
    got = np.zeros(xs.shape, bool)
    for a, b in M:
        got |= (xs >= a) & (xs <= b)
    ref = np.array([True in [zone_rule_brute(x, f, priority_road) for f in feats] for x in xs])
    assert np.array_equal(got, ref)
    kinds = " / ".join(z[2] for z in r["zones"])
    assert ("intersection" in kinds) is (not priority_road)
    assert "downhill" in kinds and kinds.count("downhill") == 1            # 4 % の下りは「急な」でない(仮定 10 %)
    assert kinds.count("tunnel") == 1                                      # 車両通行帯のあるトンネルは除く(2 号)


def test_overtake_permitted_truth_table():
    zr = DP.no_overtaking_zones([{"kind": "crosswalk", "start": 300.0, "end": 304.0}])
    req = DP.overtake_requirement(60 / 3.6, 40 / 3.6, lead_length=4.5, ego_length=4.5, gap_back=15.0, gap_front=15.0,
                                  accel=1.0, v_max=60 / 3.6, lane_change_time=3.0, v_oncoming=60 / 3.6, pet_min=1.0)
    L = req["ego_distance"]
    cases = {
        "clear": (dict(maneuver_start=0.0, maneuver_end=L), []),
        "into_crosswalk_zone": (dict(maneuver_start=150.0, maneuver_end=150.0 + L), ["no_passing_zone"]),
        "ends_before_zone": (dict(maneuver_start=270.0 - L - 1.0, maneuver_end=269.0), []),
        "bicycle_exempt": (dict(maneuver_start=150.0, maneuver_end=150.0 + L, lead_kind="bicycle"), []),
        "double": (dict(maneuver_start=0.0, maneuver_end=L, lead_overtaking=True), ["double_overtaking"]),
        "lead_turning_right": (dict(maneuver_start=0.0, maneuver_end=L, lead_keeping_right=True), ["wrong_side"]),
        "left_of_right_turner": (dict(maneuver_start=0.0, maneuver_end=L, lead_keeping_right=True, side="left"), []),
        "oncoming_close": (dict(maneuver_start=0.0, maneuver_end=L, dist_oncoming=req["d_required"] - 1.0),
                           ["oncoming_too_close"]),
        "oncoming_far": (dict(maneuver_start=0.0, maneuver_end=L, dist_oncoming=req["d_required"] + 1.0), []),
        "being_overtaken": (dict(maneuver_start=0.0, maneuver_end=L, being_overtaken=True), ["being_overtaken"]),
    }
    assert len(cases) == 10
    for name, (kw, want) in cases.items():
        r = DP.overtake_permitted(zones_result=zr, requirement=req, **kw)
        assert [c for c, _ in r["reasons"]] == want, name
        assert r["ok"] is (want == []), name
    # 境目ちょうどの対向車(D = D*)は追越してよい: 時間の行進で戻り切ってから pet_min 秒後に対向車が着く
    tp, s = march_overtake(req["relative_distance"], 60 / 3.6, 40 / 3.6, 1.0, 60 / 3.6, 3.0)
    t_on = (req["d_required"] - s) / (60 / 3.6)
    assert t_on - (tp + 3.0) == pytest.approx(1.0, abs=2e-3)


def increase_brute(v):
    best = 0.0
    for i in range(len(v)):
        for j in range(i):
            best = max(best, v[i] - v[j])
    return best


def test_overtaken_conduct_increase_equals_pairwise():
    t = np.linspace(0.0, 10.0, 201)
    profiles = {"steady": np.full(t.shape, 12.0), "slowing": 12.0 - 0.3 * t,
                "dip_then_up": 12.0 - 2.0 * np.sin(np.pi * t / 10.0) + 0.05 * t,
                "speed_up": 12.0 + 0.4 * np.clip(t - 4.0, 0, None)}
    assert len(profiles) == 4
    for name, v in profiles.items():
        r = DP.overtaken_conduct_check({"t": t, "v": v}, t_caught=2.0, t_passed=9.0)
        sel = (t >= 2.0) & (t <= 9.0)
        ref = increase_brute(list(v[sel]))
        assert r["increase"] == pytest.approx(ref, abs=1e-9), name
        assert ("speed_increased" in " / ".join(r["violations"])) is bool(ref > 0.2), name
    up = {"t": t, "v": profiles["speed_up"]}
    assert DP.overtaken_conduct_check(up, t_caught=2.0, t_passed=9.0, kind="route_bus")["ok"]                 # 乗合は除く
    assert DP.overtaken_conduct_check(up, t_caught=2.0, t_passed=9.0, overtaker_higher_limit=False)["ok"]
    assert not DP.overtaken_conduct_check(up, t_caught=2.0, t_passed=9.0, overtaker_higher_limit=False,
                                          continuing_slower=True)["ok"]
    r = DP.overtaken_conduct_check({"t": t, "v": profiles["steady"]}, t_caught=2.0, t_passed=9.0, room=2.0, room_needed=2.5)
    assert r["must_yield_left"] is True
    assert DP.overtaken_conduct_check({"t": t, "v": profiles["steady"]}, t_caught=2.0, t_passed=9.0, lanes=True, room=2.0,
                                      room_needed=2.5)["must_yield_left"] is False


# ───────────────────────── 2. 進路変更 ─────────────────────────
def sim_min_gap(gap, vf, ve, tau, ae, b, dt=2e-4, t_end=60.0):
    """後続車(反応 tau の後に一定の減速 b)と自車(加速 ae)を行進させた車間の最小値。"""
    xf, xe, v1, v2, t = 0.0, gap, vf, ve, 0.0
    m = gap
    while t < t_end:
        a1 = 0.0 if t < tau else -b
        v1n = max(v1 + a1 * dt, 0.0)
        v2n = v2 + ae * dt
        xf += 0.5 * (v1 + v1n) * dt
        xe += 0.5 * (v2 + v2n) * dt
        v1, v2, t = v1n, v2n, t + dt
        m = min(m, xe - xf)
        if t > tau and v1 <= v2:
            break
    return m


@pytest.mark.parametrize("gap,vf,ve,tau,ae,s0", [(30.0, 25.0, 15.0, 1.0, 0.0, 2.0), (20.0, 22.0, 16.0, 0.8, 0.3, 1.0),
                                                 (12.0, 20.0, 18.0, 1.0, 0.0, 0.0), (40.0, 30.0, 20.0, 1.5, 0.5, 5.0)])
def test_follower_decel_equals_simulation(gap, vf, ve, tau, ae, s0):
    r = DP.lane_change_follower_decel(gap, vf, ve, reaction=tau, accel_ego=ae, min_gap=s0)
    b = r["decel"]
    assert 0.0 < b < math.inf
    assert sim_min_gap(gap, vf, ve, tau, ae, b) == pytest.approx(s0, abs=5e-3)
    assert sim_min_gap(gap, vf, ve, tau, ae, b * 0.97) < s0 - 1e-3
    lo, hi = 0.0, 50.0                                         # 二分法: 最小の車間がちょうど s0 になる減速度
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if sim_min_gap(gap, vf, ve, tau, ae, mid) >= s0:
            hi = mid
        else:
            lo = mid
    assert b == pytest.approx(hi, rel=2e-3)
    assert r["obstructs"] is (b > DP.SUDDEN_DECEL)


def test_follower_decel_edge_cases():
    assert DP.lane_change_follower_decel(10.0, 15.0, 20.0, reaction=1.0)["decel"] == 0.0           # 離れていく
    r = DP.lane_change_follower_decel(5.0, 25.0, 15.0, reaction=1.0)                               # 反応の間に詰まり切る
    assert r["decel"] == math.inf and r["obstructs"] is True
    assert sim_min_gap(5.0, 25.0, 15.0, 1.0, 0.0, 1e6) < 0.0
    # 自車の加速で反応の間に相対速度が 0 になる(詰まる量 2²/(2·2) = 1 m < 3 m)→ 0
    e = DP.lane_change_follower_decel(3.0, 17.0, 15.0, reaction=1.5, accel_ego=2.0)
    assert e["decel"] == 0.0
    assert sim_min_gap(3.0, 17.0, 15.0, 1.5, 2.0, 0.0) == pytest.approx(2.0, abs=1e-3)
    arr = DP.lane_change_follower_decel(np.array([30.0, 20.0, 5.0]), 25.0, 15.0, reaction=1.0)
    assert arr["decel"].shape == (3,) and arr["obstructs"].dtype == bool


def test_lane_change_permitted_truth_table():
    good_seq = [{"t": 0.0, "kind": "mirror"}, {"t": 0.5, "kind": "signal_on"}, {"t": 3.6, "kind": "start"},
                {"t": 6.0, "kind": "end"}, {"t": 6.5, "kind": "signal_off"}]
    late_seq = [{"t": 0.0, "kind": "mirror"}, {"t": 2.5, "kind": "signal_on"}, {"t": 3.6, "kind": "start"},
                {"t": 6.0, "kind": "end"}, {"t": 6.5, "kind": "signal_off"}]
    far = {"gap": 60.0, "v_follow": 22.0, "v_ego": 20.0, "reaction": 1.0}
    near = {"gap": 12.0, "v_follow": 25.0, "v_ego": 15.0, "reaction": 1.0}
    cases = {
        "ok": (dict(follower=far, signal_events=good_seq), []),
        "near_follower": (dict(follower=near), ["follower_sudden_decel"]),
        "yellow": (dict(boundary="yellow"), ["no_lane_change_marking"]),
        "yellow_article40": (dict(boundary="yellow", exception="article40"), []),
        "white": (dict(boundary="white"), []),
        "late_signal": (dict(signal_events=late_seq), ["signal_signal_timing"]),
    }
    assert len(cases) == 6
    for name, (kw, want) in cases.items():
        r = DP.lane_change_permitted(**kw)
        assert [c for c, _ in r["reasons"]] == want, name


# ───────────────────────── 3. 環状交差点 ─────────────────────────
def sim_ring_arrival(theta0, v, R, target, dt=1e-4):
    """右回りに円周を行進し、入口の向きの半直線を横切った時刻(外積の符号の変化、線形補間)。"""
    a = np.array([math.cos(target), math.sin(target)])
    th, t = theta0, 0.0
    p = np.array([math.cos(th), math.sin(th)])
    c0 = p[0] * a[1] - p[1] * a[0]
    if abs(c0) < 1e-15 and p @ a > 0:
        return 0.0
    while t < 1e4:
        th1 = th - v / R * dt
        p1 = np.array([math.cos(th1), math.sin(th1)])
        c1 = p1[0] * a[1] - p1[1] * a[0]
        if c0 * c1 <= 0 and p1 @ a > 0:
            return t + c0 / (c0 - c1) * dt
        th, t, c0 = th1, t + dt, c1
    raise AssertionError("never arrived")


def test_roundabout_arrival_equals_ring_march():
    R = 12.0
    cars = [{"theta": 1.2, "speed": 6.0}, {"theta": 0.2, "speed": 5.0}, {"theta": -0.05, "speed": 7.0},
            {"theta": 3.0, "speed": 4.0}]
    r = DP.roundabout_entry_check(0.0, R, cars, t_clear=4.0, entry_speed=2.0, side_friction=0.2)
    assert len(r["cars"]) == 4
    for c, out in zip(cars, r["cars"]):
        assert out["t_arrive"] == pytest.approx(sim_ring_arrival(c["theta"], c["speed"], R, 0.0), abs=2e-3)
        assert out["obstructs"] is (out["decel"] > DP.SUDDEN_DECEL)
    # 角 0.2 の車(弧 2.4 m、5 m/s)は入口の手前で止まるしかない(5²/(2·2.4) = 5.2 m/s² > 2)→ 譲る
    assert r["cars"][1]["decel"] == pytest.approx(5.0 ** 2 / (2 * 2.4))
    assert "must_yield" in " / ".join(c for c, _ in r["reasons"])
    assert r["ring_speed_limit"] == pytest.approx(math.sqrt(9.81 * R * 0.2))
    # 要る減速度で減速すると、ちょうど t_clear に入口に着く(止まらない場合)を行進で確かめる
    out = r["cars"][0]                                  # 角 1.2(弧 14.4 m、6 m/s): 止まらずに 4 s で着く減速 1.2 m/s²
    c = cars[0]
    arc, b = out["arc"], out["decel"]
    assert 0 < b < c["speed"] ** 2 / (2 * arc)
    x, v, t, dt = 0.0, c["speed"], 0.0, 1e-4
    while x < arc:
        v1 = v - b * dt
        x += 0.5 * (v + v1) * dt
        v, t = v1, t + dt
    assert t == pytest.approx(4.0, abs=2e-3)
    ok = DP.roundabout_entry_check(0.0, R, [{"theta": 3.0, "speed": 4.0}], t_clear=4.0, entry_speed=2.0)
    assert ok["ok"] is True
    slow = DP.roundabout_entry_check(0.0, R, [], t_clear=4.0, entry_speed=20 / 3.6)
    assert [c for c, _ in slow["reasons"]] == ["not_crawling"]


def replay_exits(progress, theta_entry, arm_angles, entry):
    """環道の上の位置ベクトルが各枝の向きを横切った回数を、サンプルごとに数える(角の剰余を使わない)。"""
    a = np.stack([np.cos(arm_angles), np.sin(arm_angles)], 1)
    count = np.zeros(len(progress), int)
    crossed = []
    p_prev = np.array([math.cos(theta_entry), math.sin(theta_entry)])
    n = 0
    for i, pr in enumerate(progress):
        th = theta_entry - pr
        p = np.array([math.cos(th), math.sin(th)])
        for j in range(len(arm_angles)):
            if j == entry and pr < math.pi:
                continue
            c0 = p_prev[0] * a[j, 1] - p_prev[1] * a[j, 0]
            c1 = p[0] * a[j, 1] - p[1] * a[j, 0]
            if c0 < 0 and c1 >= 0 and p @ a[j] > 0:          # 右回り: sin(α − θ) が負から正へ
                n += 1
                crossed.append((j, pr))
        count[i] = n
        p_prev = p
    return count, crossed


@pytest.mark.parametrize("arms,entry,exit_", [([0.0, math.pi / 2, math.pi, 3 * math.pi / 2], 0, 1),
                                              ([0.0, math.pi / 2, math.pi, 3 * math.pi / 2], 0, 3),
                                              ([0.3, 1.9, 3.0, 4.4, 5.5], 2, 3), ([0.3, 1.9, 3.0, 4.4, 5.5], 2, 2)])
def test_roundabout_signal_point_equals_replay(arms, entry, exit_):
    sp = DP.roundabout_signal_point(arms, entry, exit_)
    prog = np.linspace(0.0, sp["exit_angle"] + 0.2, 6001)
    cnt, crossed = replay_exits(prog, arms[entry], np.array(arms), entry)
    assert len(crossed) > 0
    names = [j for j, _ in crossed]
    k = names.index(exit_)                                  # 目的の出口を横切った回(その前に通った出口 = k 個)
    assert sp["exits_before"] == k
    if k == 0:
        assert sp["signal_angle"] == 0.0
    else:
        assert sp["signal_angle"] == pytest.approx(crossed[k - 1][1], abs=2e-3)
    assert sp["exit_angle"] == pytest.approx(crossed[k][1], abs=2e-3)
    # 再生の数え上げで作った「正しい合図」は合格し、遅れ・早すぎ・右の合図は落ちる
    good = (cnt >= k) & (prog <= sp["exit_angle"] + 0.05)
    assert DP.roundabout_signal_check(prog, good, arm_angles=arms, entry=entry, exit=exit_)["ok"]
    late = good & (prog >= sp["signal_angle"] + 0.3)
    assert "left_late" in " / ".join(DP.roundabout_signal_check(prog, late, arm_angles=arms, entry=entry,
                                                                  exit=exit_)["violations"])
    early = prog <= sp["exit_angle"]
    v = DP.roundabout_signal_check(prog, early, arm_angles=arms, entry=entry, exit=exit_)["violations"]
    assert ("left_early" in " / ".join(v)) is (k > 0)
    right = prog < 0.3
    assert "right_signal" in " / ".join(DP.roundabout_signal_check(prog, good, arm_angles=arms, entry=entry, exit=exit_,
                                                                   right_on=right)["violations"])


# ───────────────────────── 4. 坂 ─────────────────────────
def crest_profile(g1, g2, L):
    def z(x):
        x = np.asarray(x, float)
        xb = -L / 2.0
        mid = g1 * x - (g1 - g2) * (x - xb) ** 2 / (2.0 * L)
        return np.where(x <= xb, g1 * x, np.where(x >= L / 2.0, g2 * x, mid))
    return z


def brute_min_sight(z, h1, h2, x0s, smax):
    """各観測位置から見通し線を総当たりで調べ(二分法)、見える最も遠い物までの水平距離の最小値。"""
    best = math.inf
    for x0 in x0s:
        e = float(z(x0)) + h1

        def visible(x1):
            xs = np.linspace(x0, x1, 4001)[1:-1]
            o = float(z(x1)) + h2
            line = e + (o - e) * (xs - x0) / (x1 - x0)
            return bool(np.all(z(xs) <= line + 1e-12))
        lo, hi = x0 + 1e-6, x0 + smax
        if visible(hi):
            continue
        for _ in range(50):
            mid = 0.5 * (lo + hi)
            if visible(mid):
                lo = mid
            else:
                hi = mid
        best = min(best, lo - x0)
    return best


@pytest.mark.parametrize("g1,g2,L,h2", [(0.04, -0.04, 200.0, 0.1), (0.03, -0.03, 60.0, 0.1), (0.05, -0.02, 150.0, 1.2),
                                        (0.02, -0.03, 40.0, 1.2)])
def test_crest_sight_equals_line_of_sight_scan(g1, g2, L, h2):
    r = DP.crest_sight_distance(grade_in=g1, grade_out=g2, length=L, object_height=h2)
    z = crest_profile(g1, g2, L)
    x0s = np.arange(-L / 2 - r["sight"] - 5.0, L / 2 + 5.0, 0.5)
    assert x0s.size > 50
    got = brute_min_sight(z, 1.2, h2, x0s, 3.0 * r["sight"] + 50.0)
    assert r["sight"] == pytest.approx(got, rel=2e-3)
    assert r["within_curve"] is (r["sight"] <= L)


def test_crest_sight_reproduces_road_structure_order_table():
    """道路構造令 22 条の凸形縦断曲線の半径と 2 条 24 号の高さで、19 条の視距の表(公表値、5〜10 m 単位)が出る。"""
    rows = sorted(DP.CREST_RADIUS_TABLE)
    assert len(rows) == 3
    for v in rows:
        s = DP.crest_sight_distance(radius=DP.CREST_RADIUS_TABLE[v])["sight"]
        assert s == pytest.approx(DP.SIGHT_DISTANCE_TABLE[v], rel=0.01), v
    with pytest.raises(ValueError):
        DP.crest_sight_distance(grade_in=-0.02, grade_out=0.03, length=50.0)            # 凹形
    with pytest.raises(ValueError):
        DP.crest_sight_distance(radius=100.0, length=50.0)


@pytest.mark.parametrize("S,rho,b,th,crr", [(20.0, 0.75, 6.0, 0.0, 0.0), (60.0, 1.0, 5.0, 0.05, 0.012),
                                            (35.0, 0.75, 4.0, -0.08, 0.012), (160.0, 2.5, 3.5, 0.0, 0.0)])
def test_crest_safe_speed_inverts_drivelong(S, rho, b, th, crr):
    v = DP.crest_safe_speed(S, reaction=rho, brake=b, theta=th, c_rr=crr)["speed"]
    lo, hi = 0.0, 100.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if DLO.stopping_distance_grade(mid, rho, b, th, crr) <= S:
            lo = mid
        else:
            hi = mid
    assert v == pytest.approx(lo, rel=1e-9)
    assert DLO.stopping_distance_grade(v, rho, b, th, crr) == pytest.approx(S, rel=1e-9)


def test_crest_safe_speed_crawl_flag():
    s = DP.crest_sight_distance(radius=100.0)["sight"]                               # 20 km/h の道の頂上、視距 20 m
    r = DP.crest_safe_speed(np.array([s, 1.0]), reaction=0.75, brake=6.0)
    assert r["crawl_sufficient"].tolist() == [True, False]
    assert r["crawl_required"] is True


def test_hill_meeting_yield_truth_table():
    cases = [("down", None, None, ("ego", "stop")), ("up", None, None, ("other", "stop")),
             ("up", 20.0, None, ("ego", "refuge")), ("up", 80.0, None, ("other", "stop")),
             ("down", None, 10.0, ("other", "refuge")), ("down", 15.0, None, ("ego", "refuge"))]
    assert len(cases) == 6
    for d, er, orr, want in cases:
        r = DP.hill_meeting_yield(d, ego_refuge_distance=er, other_refuge_distance=orr)
        assert (r["yielder"], r["where"]) == want, (d, er, orr)


# ───────────────────────── 5. カーブミラー ─────────────────────────
@pytest.mark.parametrize("a,e,R,h", [(30.0, 8.0, 3.0, 1.5), (15.0, 5.0, 2.2, 1.4), (50.0, 12.0, 4.0, 1.5)])
def test_convex_mirror_image_equals_ray_tracing(a, e, R, h):
    E = np.array([e, 0.0])
    St = reflect_point_on_axis_mirror(E, np.array([a, h / 2]), R)
    Sb = reflect_point_on_axis_mirror(E, np.array([a, -h / 2]), R)
    theta = apparent_angle(E, St) - apparent_angle(E, Sb)
    r = DP.convex_mirror_image(a, R, eye_distance=e, object_size=h)
    assert r["angular_size"] == pytest.approx(theta, rel=2e-3)
    # 平面鏡のつもりで大きさから読んだ距離 = k a
    a_hat = (h / 2) / math.tan(theta / 2) - e
    assert a_hat == pytest.approx(r["flat_equivalent_distance"], rel=3e-3)
    assert r["k"] == pytest.approx(1 + 2 * e / R)
    assert r["flat_equivalent_distance"] > a


@pytest.mark.parametrize("a,v,e,R", [(30.0, 10.0, 8.0, 3.0), (20.0, 8.0, 6.0, 2.5)])
def test_convex_mirror_misjudge_equals_ray_traced_rates(a, v, e, R):
    h, dt = 1.5, 1e-3
    E = np.array([e, 0.0])

    def size(dist):
        St = reflect_point_on_axis_mirror(E, np.array([dist, h / 2]), R)
        Sb = reflect_point_on_axis_mirror(E, np.array([dist, -h / 2]), R)
        return apparent_angle(E, St) - apparent_angle(E, Sb)
    th0, th1 = size(a + v * dt), size(a - v * dt)                  # 近づいてくる(中心差分)
    thd = (th1 - th0) / (2 * dt)
    r = DP.convex_mirror_misjudge(a, v, R, eye_distance=e)
    # 1) 大きさから読んだ距離の変化(矛盾なく読む)
    ah = lambda th: (h / 2) / math.tan(th / 2) - e                 # noqa: E731
    v_cons = -(ah(th1) - ah(th0)) / (2 * dt)
    assert v_cons == pytest.approx(r["speed_size_consistent"], rel=5e-3)
    # 2) 本当の距離 a にある物(平面鏡)の大きさの変化率で割る
    dflat = (h / 2) / ((e + a) ** 2 + (h / 2) ** 2) * 2            # |d/da 2 atan(h/(2(e + a)))|
    v_anch = thd / dflat
    assert v_anch == pytest.approx(r["speed_size_anchored"], rel=5e-3)
    assert r["speed_size_anchored"] < v < r["speed_size_consistent"]
    # 3) 横切る動き: 横の位置 y の像の角の速さを本当の距離で読む
    y0, vl = 0.3, v

    def ang(y):
        return apparent_angle(E, reflect_point_on_axis_mirror(E, np.array([a, y]), R))
    om = (ang(y0 + vl * dt) - ang(y0 - vl * dt)) / (2 * dt)
    assert om * (e + a) == pytest.approx(r["speed_lateral_anchored"], rel=5e-3)
    assert r["speed_lateral_anchored"] < v
    # 見かけの到達時間 = 大きさ / 大きさの変化率
    assert th0 / thd == pytest.approx(r["tau_apparent"], rel=1e-2)
    assert a > r["slower_if_anchored_beyond"]


def _setup_tjunction():
    E = np.array([0.0, -4.0])
    M = np.array([-1.0, 5.0])
    n = DD.mirror_aim_normal(E, M, np.array([1.0, -0.2]))
    return E, M, n


def test_mirror_image_side_equals_fermat_and_convex_keeps_sign():
    E, M, n = _setup_tjunction()
    t = np.array([-n[1], n[0]])
    xs = np.linspace(-30.0, 40.0, 15)
    pts = np.array([[x, y] for x in xs for y in (1.0, 2.0, 3.5)])
    pts = pts[(pts - M) @ n > 0.5]
    V = np.tile(np.array([[-8.0, 0.0]]), (len(pts), 1))
    r = DP.mirror_image_side(E, M, n, pts, heading=(0.0, 1.0), velocities=V)
    assert len(pts) > 20
    c = M - E
    for i, P in enumerate(pts):
        S = M + fermat_flat(E, M, t, P) * t                          # 像は眼から S の向きに見える
        q = S - E
        ang = math.atan2(c[0] * q[1] - c[1] * q[0], c @ q)
        assert ang == pytest.approx(r["image_offset"][i], abs=1e-6)
        # 動き: 少し進めた点の像の角の差
        hd = 1e-2
        Sa = M + fermat_flat(E, M, t, P + V[i] * hd) * t
        Sb = M + fermat_flat(E, M, t, P - V[i] * hd) * t
        qa, qb = Sa - E, Sb - E
        da = math.atan2(c[0] * qa[1] - c[1] * qa[0], c @ qa) - math.atan2(c[0] * qb[1] - c[1] * qb[0], c @ qb)
        assert da / (2 * hd) == pytest.approx(r["image_motion"][i], rel=1e-3, abs=1e-6)
        # 凸面鏡(R = 3 m)でも鏡の中心からの左右は同じ(大きさは違う)
        if abs(r["image_offset"][i]) > 1e-3:
            _, Sc = fermat_arc(E, M, n, 3.0, P)
            qc = Sc - E
            angc = math.atan2(c[0] * qc[1] - c[1] * qc[0], c @ qc)
            assert np.sign(angc) == np.sign(r["image_offset"][i])
            assert abs(angc) < abs(r["image_offset"][i])            # 凸面は角を縮める(広く映す)
    assert np.allclose(r["virtual_eye_motion"], -r["image_motion"])  # 折り返しは向きを反転する(恒等式)
    # 前 = +y の運転者から見て x が眼より大きい点は右(−1)、小さい点は左(+1)、真正面は 0
    assert np.array_equal(r["real_side"], np.sign(E[0] - pts[:, 0]))


def brute_coverage(E, M, n, w, R, Q0, u, m=20001):
    t = np.array([-n[1], n[0]])
    if math.isinf(R):
        s = np.linspace(-w, w, m)
        P = M[None, :] + s[:, None] * t[None, :]
        N = np.repeat(n[None, :], m, 0)
    else:
        phim = math.asin(w / R)
        phi = np.linspace(-phim, phim, m)
        N = np.cos(phi)[:, None] * n[None, :] + np.sin(phi)[:, None] * t[None, :]
        P = (M - R * n)[None, :] + R * N
    d = P - E[None, :]
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    r = d - 2 * np.sum(d * N, 1, keepdims=True) * N
    lam = []
    for Pi, ri in zip(P, r):
        A = np.array([[ri[0], -u[0]], [ri[1], -u[1]]])
        if abs(np.linalg.det(A)) < 1e-14:
            continue
        s_, l_ = np.linalg.solve(A, Q0 - Pi)
        if s_ > 0:
            lam.append(l_)
    return np.array(lam)


@pytest.mark.parametrize("R,w", [(math.inf, 0.8), (3.0, 0.8), (2.0, 0.6), (5.0, 1.0)])
def test_mirror_road_coverage_equals_dense_rays(R, w):
    E, M, n = _setup_tjunction()
    Q0, u = np.array([0.0, 2.0]), np.array([1.0, 0.0])
    r = DP.mirror_road_coverage(E, M, n, w, mirror_radius=R, road_point=Q0, road_direction=u)
    lam = brute_coverage(E, M, n, w / 2, R, Q0, u)
    assert lam.size > 100
    lo, hi = r["interval"]
    assert lo == pytest.approx(lam.min(), abs=1e-6)
    if math.isinf(hi):
        assert lam.max() > 1e3                                     # 光線が道と平行に近づく = 遠くまで映る
        assert lam.size < 20001
    else:
        assert hi == pytest.approx(lam.max(), abs=1e-6)
        assert np.max(np.diff(np.sort(lam))) < 0.05                 # 間に映らない隙間が無い
    assert r["blind_near"] == pytest.approx(max(0.0, lo))


def test_mirror_coverage_edge_rays_match_convex_fov():
    """眼が軸の上なら、両端の反射光線の向きの差 = drivedecide.convex_mirror_fov の全視野角(別の実装)。"""
    M = np.array([0.0, 0.0])
    n = np.array([1.0, 0.0])
    D = 9.0
    E = M + D * n
    for R in (2.0, 3.0, 6.0):
        r = DP.mirror_road_coverage(E, M, n, 0.8, mirror_radius=R, road_point=(20.0, -30.0), road_direction=(0.0, 1.0))
        a, b = r["edge_rays"]
        ang = math.acos(float(np.clip(a @ b, -1, 1)))
        assert ang == pytest.approx(DD.convex_mirror_fov(R, 0.8, D)["fov_rad"], rel=1e-9)
