# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""drivecommonroad の門: 2020a の読み(件数・dt・速度制限・stopLine、版違い・壊れた XML は ValueError)、経路(長さ = Σ 中心線長、
到達不能は ValueError)、KS モデル(直進の閉形式、一定 δ の円運動 = 1 周で始点)、運転(ゴール到達・|a| ≤ a_max・v ≤ 制限・停止線の
0〜1 m 手前で停止・cr_feasible True・2 cm 未満)、衝突(障害物なし → False、経路上の静止障害物 → True と time_step)、solution XML
(要素数 = step 数・再読込・位置 = 後軸 + b)、チェッカー JSON の読み(欠落・型違いは ValueError)、fail-closed。
第 2 実装の照合(commonroad-io があるときだけ): lanelet 数・initial が一致、vehicle_dynamics_ks の odeint と ks_step が 1e-6 一致。
実データ(環境変数 FULLSEYE_COMMONROAD_DATA があるときだけ): ZAM_Tjunction で sweep → goal・feasible・無衝突。"""
import json
import math
import os
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

import drivecommonroad as CR

_DATA = os.environ.get("FULLSEYE_COMMONROAD_DATA")
_ZAM = Path(_DATA) / "ZAM_Tjunction-1_1_T-1.xml" if _DATA else None


def _has_commonroad_io() -> bool:
    """commonroad-io が実際に import できるか(Windows では protobuf の版違いで ImportError 以外の例外が出ることがある)。"""
    try:
        from commonroad.common.file_reader import CommonRoadFileReader  # noqa: F401
        from vehiclemodels.vehicle_dynamics_ks import vehicle_dynamics_ks  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return True


@pytest.fixture(scope="module")
def scenes():
    return {k: CR.cr_read(CR.cr_synthetic(k)) for k in CR.SYNTHETIC_KINDS}


# ─────────────────────────────── 読む ───────────────────────────────
def test_read_counts_dt_speed_limit_and_stop_line(scenes):
    sc = scenes["tjunction"]
    assert sc["version"] == "2020a" and sc["dt"] == 0.1
    assert len(sc["lanelets"]) == 4 and len(sc["obstacles"]) == 1 and len(sc["planning_problems"]) == 1
    la = sc["lanelets"][100]
    assert la["speed_limit_mps"] == pytest.approx(13.89)            # 標識 274 の additional_value(m/s 文字列 → float)
    assert la["stop_line"].shape == (2, 2) and np.allclose(la["stop_line"][:, 0], 40.0)
    assert sc["lanelets"][101]["stop_line"] is None
    assert la["successors"] == [101] and sc["lanelets"][102]["predecessors"] == [101]
    assert np.allclose(la["center"], 0.5 * (la["left"] + la["right"]))
    ob = sc["obstacles"][0]
    assert ob["states"].shape == (201, 5) and ob["shape"] == {"kind": "rectangle", "length": 4.5, "width": 1.8, "orientation": 0.0, "center": (0.0, 0.0)}
    pp = sc["planning_problems"][0]
    assert pp["initial"] == {"time_step": 0, "x": 5.0, "y": 0.0, "orientation": 0.0, "velocity": 8.0}
    assert pp["goal"][0]["time_step"] == (100, 200) and pp["goal"][0]["position_lanelets"] == [102]
    assert pp["goal"][0]["velocity"] == (0.0, 15.0)
    assert len(scenes["blocked"]["obstacles"]) == 2 and scenes["blocked"]["obstacles"][1]["static"]


def test_read_rejects_other_versions_and_broken_xml():
    xml = CR.cr_synthetic("straight")
    with pytest.raises(ValueError, match="commonRoadVersion"):
        CR.cr_read(xml.replace('commonRoadVersion="2020a"', 'commonRoadVersion="2018b"'))
    with pytest.raises(ValueError, match="parse error"):
        CR.cr_read(xml[:2000])
    with pytest.raises(ValueError, match="root element"):
        CR.cr_read("<notCommonRoad commonRoadVersion='2020a'/>")
    with pytest.raises(ValueError, match="not found"):
        CR.cr_read("C:/definitely/not/here.xml")


# ─────────────────────────────── 経路 ───────────────────────────────
@pytest.mark.parametrize("kind", ["tjunction", "straight"])
def test_route_length_is_the_sum_of_the_centre_lines(scenes, kind):
    sc = scenes[kind]
    r = CR.cr_route(sc, 100, goal=sc["planning_problems"][0]["goal"][0])
    assert r["lanelets"] == [100, 101, 102]
    expect = sum(sc["lanelets"][l]["length"] for l in r["lanelets"])
    assert abs(r["length"] - expect) <= 1e-6
    assert len(r["polyline"]) == len(r["cum"]) >= 3
    assert abs(r["cum"][-1] - expect) <= 1e-9 and np.all(np.diff(r["cum"]) > 0)
    assert np.allclose(r["lanelet_s"], np.cumsum([0.0] + [sc["lanelets"][l]["length"] for l in r["lanelets"][:-1]]))
    assert r["speed_limit_mps"] == pytest.approx(13.89)
    if kind == "straight":
        assert abs(r["length"] - 120.0) <= 1e-9 and np.allclose(np.diff(r["cum"]), 0.5)


def test_route_unreachable_raises(scenes):
    sc = scenes["straight"]
    with pytest.raises(ValueError, match="no successor route"):
        CR.cr_route(sc, 102, 100)                 # 逆向き
    with pytest.raises(ValueError, match="no successor route"):
        CR.cr_route(sc, 200, 102)                 # 対向車線から
    with pytest.raises(ValueError, match="unknown lanelet"):
        CR.cr_route(sc, 999, 102)
    with pytest.raises(ValueError, match="position_lanelets"):
        CR.cr_route(sc, 100, goal={"position_lanelets": None})


# ─────────────────────────────── KS ───────────────────────────────
def test_ks_step_straight_line_is_exact():
    x = CR.ks_step((1.0, -2.0, 0.0, 7.0, 0.3), (0.0, 0.0), 0.5)
    assert abs(x[0] - (1.0 + 7.0 * 0.5 * math.cos(0.3))) <= 1e-9
    assert abs(x[1] - (-2.0 + 7.0 * 0.5 * math.sin(0.3))) <= 1e-9
    assert x[2] == 0.0 and abs(x[3] - 7.0) <= 1e-12 and abs(x[4] - 0.3) <= 1e-12
    x = CR.ks_step((0.0, 0.0, 0.0, 5.0, 0.0), (0.0, 1.5), 0.1)        # 一定加速: v = v0 + a t, x = v0 t + a t²/2(RK4 は 2 次多項式を厳密に)
    assert abs(x[3] - 5.15) <= 1e-12 and abs(x[0] - (0.5 + 0.0075)) <= 1e-12


def test_ks_step_constant_steering_is_a_circle_that_closes():
    p = CR.BMW_320I
    delta, v = 0.25, 5.0
    R = p["l_wb"] / math.tan(delta)
    T = 2.0 * math.pi * R / v
    n = 2000
    x = np.array([0.0, 0.0, delta, v, 0.0])
    xs = [x]
    for _ in range(n):
        x = CR.ks_step(x, (0.0, 0.0), T / n)
        xs.append(x)
    xs = np.asarray(xs)
    assert len(xs) == n + 1
    assert abs(xs[-1, 0]) <= 1e-6 and abs(xs[-1, 1]) <= 1e-6           # 1 周で始点へ
    assert abs(CR._wrap(xs[-1, 4])) <= 1e-6
    centre = np.array([0.0, R])                                       # 左へ回る円の中心 = (0, R)
    radii = np.hypot(xs[:, 0] - centre[0], xs[:, 1] - centre[1])
    assert np.max(np.abs(radii - R)) <= 1e-6


def test_ks_step_fail_closed():
    with pytest.raises(ValueError):
        CR.ks_step((0.0, 0.0, 0.0), (0.0, 0.0), 0.1)
    with pytest.raises(ValueError):
        CR.ks_step((0.0, 0.0, 0.0, 1.0, np.nan), (0.0, 0.0), 0.1)
    with pytest.raises(ValueError):
        CR.ks_step((0.0, 0.0, 0.0, 1.0, 0.0), (0.0,), 0.1)
    with pytest.raises(ValueError):
        CR.ks_step((0.0, 0.0, 0.0, 1.0, 0.0), (0.0, 0.0), 0.0)
    with pytest.raises(ValueError, match="params has no"):
        CR.ks_step((0.0, 0.0, 0.0, 1.0, 0.0), (0.0, 0.0), 0.1, {"l_wb": 2.5})


# ─────────────────────────────── 運転 ───────────────────────────────
@pytest.mark.parametrize("kind", ["tjunction", "straight"])
def test_drive_reaches_the_goal_within_limits_and_stops_before_the_stop_line(scenes, kind):
    sc = scenes[kind]
    run = CR.cr_drive(sc, stop_lines="scene", a_max=1.5, b_max=3.0)
    n = len(run["time_step"])
    assert n == 201 and run["u"].shape == (200, 2)                    # ゴール区間の上端 200 まで
    assert run["goal_reached"] and 100 <= run["time_step"][run["goal_index"]] <= 200
    assert np.all(np.abs(run["u"][:, 1]) <= 3.0 + 1e-9) and np.all(run["u"][:, 1] <= 1.5 + 1e-9)
    assert np.all(run["v"] >= 0.0) and np.all(run["v"] <= run["v_limit"] + 1e-9) and run["v_limit"] == pytest.approx(13.89)
    assert np.all(np.abs(run["u"][:, 0]) <= 0.4 + 1e-12) and np.all(np.abs(run["delta"]) <= 1.066)
    assert len(run["stops"]) >= 1
    t_stop, s_front, what, s_line = run["stops"][0]
    assert what == "stop_line" and s_line == pytest.approx(40.0)
    assert 0.0 <= s_line - s_front <= 1.0                             # 前端が停止線の 0〜1 m 手前
    assert run["v"][t_stop] == 0.0
    assert any("released" in e for e in run["events"])                # hold の後で発進
    assert np.max(np.abs(run["lat_err"])) <= 0.5                      # 中心線に沿う
    # 車両中心 = 後軸 + b (cos ψ, sin ψ)
    b = run["params"]["b"]
    assert np.allclose(run["x"], run["x_rear"] + b * np.cos(run["psi"])) and np.allclose(run["y"], run["y_rear"] + b * np.sin(run["psi"]))
    f = CR.cr_feasible(run)
    assert f["feasible"] and f["max_pos_err"] < 0.02 and f["violations"] == [] and f["n_transitions"] == 200
    c = CR.cr_collision(sc, run)
    assert c["obstacle_collision"] is False and c["first_collision"] is None
    assert c["boundary_violation"] is False and c["n_outside"] == 0


def test_drive_without_stop_lines_and_explicit_stop_lines(scenes):
    sc = scenes["straight"]
    free = CR.cr_drive(sc)
    assert [s[2] for s in free["stops"]] == ["goal"] and free["goal_reached"]     # 停止線なし: 止まるのはゴールだけ
    assert 0.0 <= free["stops"][0][3] - free["stops"][0][1] <= 1.0 and free["stops"][0][3] == pytest.approx(80.0 + 0.2 * 40.0)
    run = CR.cr_drive(sc, stop_lines=[30.0, 55.0])                    # 2 本目は 20 s の horizon に収まる距離に置く(IDM の停止は漸近的)
    kinds = [s[2] for s in run["stops"]]
    assert len(run["stops"]) == 2
    assert kinds == ["stop_line", "stop_line"]
    for _, s_front, _, s_line in run["stops"]:
        assert 0.0 <= s_line - s_front <= 1.0
    with pytest.raises(ValueError, match="outside the route"):
        CR.cr_drive(sc, stop_lines=[500.0])


def test_collision_is_detected_with_a_parked_obstacle_on_the_route(scenes):
    sc = scenes["blocked"]
    run = CR.cr_drive(sc, follow_obstacles=False)                     # 前方を見ない運転手 = ぶつかる
    c = CR.cr_collision(sc, run)
    assert c["obstacle_collision"] and c["first_collision"][1] == 2
    # 前端が障害物の後端(x = 60 − 2.25)に届く最初の time_step 付近
    front = run["x"] + 0.5 * run["params"]["length"]
    k_expect = int(np.argmax(front >= 60.0 - 2.25))
    assert abs(c["first_collision"][0] - run["time_step"][k_expect]) <= 1
    # IDM で先行障害物を見る運転手は手前で止まる(ゴールには届かない)
    run2 = CR.cr_drive(sc)
    c2 = CR.cr_collision(sc, run2)
    assert not c2["obstacle_collision"] and not run2["goal_reached"]
    assert run2["v"][-1] <= 1e-3                                       # 先行車の後ろは IDM の漸近停止(厳密な 0 はゴール・停止線だけ)
    assert run2["x"][-1] + 0.5 * run2["params"]["length"] < 60.0 - 2.25


def test_sweep_returns_the_first_passing_settings(scenes):
    sc = scenes["straight"]
    sw = CR.cr_drive_sweep(sc, grid={"a_lat": (2.5,), "lookahead": (5.0,), "k_v": (0.6,)})
    assert sw["n_tries"] == 1 and sw["run"] is not None and sw["settings"]["a_lat"] == 2.5
    none = CR.cr_drive_sweep(scenes["blocked"], grid={"a_lat": (2.5,), "lookahead": (5.0,), "k_v": (0.6,)})
    assert none["run"] is None and none["n_tries"] == 1 and not none["tries"][0]["goal_reached"]
    with pytest.raises(ValueError, match="grid keys"):
        CR.cr_drive_sweep(sc, grid={"bogus": (1,)})


def test_drive_fail_closed(scenes):
    sc = scenes["straight"]
    with pytest.raises(ValueError, match="pp_index"):
        CR.cr_drive(sc, 3)
    with pytest.raises(ValueError, match="scene must be"):
        CR.cr_drive({"kind": "nope"})
    with pytest.raises(ValueError, match="route must come"):
        CR.cr_drive(sc, route={"kind": "x"})
    with pytest.raises(ValueError, match="a_max"):
        CR.cr_drive(sc, a_max=0.0)
    with pytest.raises(ValueError, match="goal_inset"):
        CR.cr_drive(sc, goal_inset=1.5)
    with pytest.raises(ValueError, match="run must be"):
        CR.cr_feasible({"kind": "x"})
    with pytest.raises(ValueError, match="lanelets must be"):
        CR.cr_collision(sc, CR.cr_drive(sc), lanelets="world")


# ─────────────────────────────── 書く / 読む ───────────────────────────────
def test_solution_xml_round_trips_with_vehicle_centre_positions(scenes, tmp_path):
    sc = scenes["straight"]
    run = CR.cr_drive(sc)
    from datetime import datetime
    xml = CR.cr_solution_xml(sc, run, date=datetime(2026, 10, 4, 12, 0, 0))
    root = ET.fromstring(xml)
    assert root.tag == "CommonRoadSolution"
    assert root.get("benchmark_id") == "KS2:JB1:%s:2020a" % sc["id"] and root.get("date") == "2026-10-04T12:00:00"
    traj = root.find("ksTrajectory")
    assert traj.get("planningProblem") == "1"
    states = traj.findall("ksState")
    assert len(states) == len(run["time_step"]) == 201
    xs = np.array([float(s.findtext("x")) for s in states])
    ys = np.array([float(s.findtext("y")) for s in states])
    ts = [int(s.findtext("time")) for s in states]
    assert ts == list(range(201))
    b = run["params"]["b"]
    assert np.allclose(xs, run["x_rear"] + b * np.cos(run["psi"]), atol=1e-12)
    assert np.allclose(ys, run["y_rear"] + b * np.sin(run["psi"]), atol=1e-12)
    assert float(states[0].findtext("velocity")) == 8.0 and float(states[0].findtext("steeringAngle")) == 0.0
    for tag in ("x", "y", "steeringAngle", "velocity", "orientation", "time"):
        assert states[5].find(tag) is not None
    with pytest.raises(ValueError, match="vehicle_model"):
        CR.cr_solution_xml(sc, run, vehicle_model="PM")
    with pytest.raises(ValueError, match="vehicle_type"):
        CR.cr_solution_xml(sc, run, vehicle_type="TESLA")


def test_checker_result_reads_the_wsl_json_and_rejects_bad_ones(tmp_path):
    good = {"scenario": "ZAM_Tjunction-1_1_T-1", "solution": "s.xml", "valid": True, "goal_reached": True, "feasible": True,
            "obstacle_collision": False, "boundary_collision": False, "checker_version": "commonroad-drivability-checker 2025.4.0",
            "details": {"x": 1}}
    p = tmp_path / "r.json"
    p.write_text(json.dumps(good), encoding="utf-8")
    r = CR.cr_checker_result(p)
    assert r["valid"] is True and r["details"] == {"x": 1}
    bad = dict(good)
    del bad["feasible"]
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="missing key"):
        CR.cr_checker_result(p)
    bad = dict(good, valid="yes")
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="must be a bool"):
        CR.cr_checker_result(p)
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="not JSON"):
        CR.cr_checker_result(p)
    with pytest.raises(ValueError, match="not found"):
        CR.cr_checker_result(tmp_path / "missing.json")


def test_synthetic_fail_closed():
    with pytest.raises(ValueError, match="kind"):
        CR.cr_synthetic("roundabout")
    with pytest.raises(ValueError):
        CR.cr_synthetic("straight", dt=0.0)


# ─────────────────────────────── 第 2 実装の照合(commonroad-io があるとき) ───────────────────────────────
@pytest.mark.skipif(not _has_commonroad_io(), reason="commonroad-io / vehiclemodels not installed")
def test_second_implementation_commonroad_io_agrees(tmp_path):
    from commonroad.common.file_reader import CommonRoadFileReader
    from vehiclemodels.parameters_vehicle2 import parameters_vehicle2
    from vehiclemodels.vehicle_dynamics_ks import vehicle_dynamics_ks
    xml = CR.cr_synthetic("tjunction")
    path = tmp_path / "syn.xml"
    path.write_text(xml, encoding="utf-8")
    scenario, pps = CommonRoadFileReader(str(path)).open()
    sc = CR.cr_read(path)
    assert len(scenario.lanelet_network.lanelets) == len(sc["lanelets"]) == 4
    pp = list(pps.planning_problem_dict.values())[0]
    init = sc["planning_problems"][0]["initial"]
    assert np.allclose(pp.initial_state.position, (init["x"], init["y"]))
    assert pp.initial_state.velocity == init["velocity"] and pp.initial_state.orientation == init["orientation"]
    assert len(sc["lanelets"]) > 0
    for lid, la in sc["lanelets"].items():
        other = scenario.lanelet_network.find_lanelet_by_id(lid)
        assert np.allclose(other.center_vertices, la["center"], atol=1e-9)
        assert list(other.successor) == la["successors"]
    assert scenario.dt == sc["dt"]
    # 母数は実行して写した物と一致
    p2 = parameters_vehicle2()
    assert p2.a + p2.b == pytest.approx(CR.BMW_320I["l_wb"], abs=1e-9) and p2.b == pytest.approx(CR.BMW_320I["b"], abs=1e-12)
    assert (p2.l, p2.w, p2.steering.max, p2.steering.v_max, p2.longitudinal.a_max, p2.longitudinal.v_max, p2.longitudinal.v_switch) == \
        (CR.BMW_320I["length"], CR.BMW_320I["width"], CR.BMW_320I["delta_max"], CR.BMW_320I["ddelta_max"], CR.BMW_320I["a_max"],
         CR.BMW_320I["v_max"], CR.BMW_320I["v_switch"])
    # ks_step vs vehicle_dynamics_ks(scipy があれば odeint、無ければ自前 RK4 の細刻み)
    x0 = np.array([1.0, 2.0, 0.1, 6.0, 0.4])
    u = np.array([0.2, 1.0])
    mine = CR.ks_step(x0, u, 0.1)
    try:
        from scipy.integrate import odeint
        _, ref = odeint(lambda t, x, uu: vehicle_dynamics_ks(x, uu, p2), x0, [0.0, 0.1], args=(u,), tfirst=True, rtol=1e-10, atol=1e-12)
    except ImportError:
        ref = x0.copy()
        for _ in range(100):
            k1 = np.array(vehicle_dynamics_ks(ref, u, p2)); k2 = np.array(vehicle_dynamics_ks(ref + 0.0005 * k1, u, p2))
            k3 = np.array(vehicle_dynamics_ks(ref + 0.0005 * k2, u, p2)); k4 = np.array(vehicle_dynamics_ks(ref + 0.001 * k3, u, p2))
            ref = ref + 0.001 / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
    assert np.max(np.abs(mine - ref)) <= 1e-6


# ─────────────────────────────── 実データ(環境変数があるとき) ───────────────────────────────
@pytest.mark.skipif(_ZAM is None or not _ZAM.is_file(), reason="FULLSEYE_COMMONROAD_DATA not set or ZAM_Tjunction missing")
def test_real_zam_tjunction_sweep_passes_all_second_implementation_gates():
    sc = CR.cr_read(_ZAM)
    assert len(sc["lanelets"]) == 12 and len(sc["obstacles"]) == 5 and sc["dt"] == 0.1
    assert sc["lanelets"][50195]["speed_limit_mps"] == 14.0
    sw = CR.cr_drive_sweep(sc)
    assert sw["run"] is not None, [t for t in sw["tries"][-3:]]
    run = sw["run"]
    assert run["goal_reached"] and run["route"]["lanelets"][-1] == 50203
    assert len(run["time_step"]) == 148 and run["time_step"][0] == 0
    f = CR.cr_feasible(run)
    assert f["feasible"] and f["max_pos_err"] < 0.02
    c = CR.cr_collision(sc, run)
    assert not c["obstacle_collision"] and not c["boundary_violation"]
    xml = CR.cr_solution_xml(sc, run)
    assert ET.fromstring(xml).find("ksTrajectory").get("planningProblem") == "60000"
