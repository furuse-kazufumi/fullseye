# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""drivetown の門: 継ぎ目の閉形式(exit と entry の位置差 = overlap、向きの差 = 0)、中心線の総延長 = Σ centerline_length −
overlap × 継ぎ目数、標本化の間隔、停止線は走行車線の 1 本だけ(side で鏡像)、通し走行の (a)〜(e)、踏切は drivecrossing.crossing_stop_check を
実際に通す、第 2 実装(drivelong.long_simulate の RK4)と止まった位置が一致、法規パック(JP 2 回停止 / US・DE は列車なしで 1 回、
既定は JP と同じ = 回帰)、踏切の状態機械(警報中に踏切の中 0 秒、発進は警報停止の後、間に合わない警報は commit = unavoidable)、
踏切の設備(遮断かん・警報灯・列車)の状態、台帳の件数、fail-closed の ValueError。examples/poc_driving_town.py の門を単体テストにしたもの。"""
import math
from pathlib import Path

import numpy as np
import pytest

import drivecourse as DC
import drivetown as TW

_ROOT = Path(__file__).resolve().parents[1]


def _ledger_path() -> Path:
    for p in (_ROOT / "docs" / "drive" / "kyosoku_scenarios.json", Path.cwd() / "docs" / "drive" / "kyosoku_scenarios.json"):
        if p.is_file():
            return p
    raise AssertionError("kyosoku_scenarios.json が見つからない(repo の docs/drive に置く)")


def _joint_errors(layout):
    ov = layout["chain"]["overlap"]
    dp = [abs(math.hypot(ex[0] - en[0], ex[1] - en[1]) - ov) for ex, en in layout["chain"]["joints"]]
    dy = [abs(math.atan2(math.sin(ex[2] - en[2]), math.cos(ex[2] - en[2]))) for ex, en in layout["chain"]["joints"]]
    return max(dp), max(dy)


def _second_implementation(run):
    """同じ IDM 指令を drivelong.long_simulate(RK4、事象で刻みを切る)に渡し、最初の停止までの軌跡を返す。"""
    import drivelong as DL
    import drivetraffic as DT
    p = run["params"]
    line = run["stop_lines"][0]["s"]

    def cmd(t, s, v):
        gap = line - s
        if gap <= 0:
            return 0.0, p["b_max"]
        vv = max(v, 0.0)
        a = DT.idm_accel(vv, gap, vv, v0=p["v_max"], T=p["idm_T"], a=p["a_max"], b=p["b_max"], s0=p["stop_margin"])
        a = min(p["a_max"], max(-p["b_max"], a))
        return max(a, 0.0), max(-a, 0.0)

    prm = DL.long_params(c_rr=0.0, cda=0.0, a_drive_max=p["a_max"], a_brake_max=p["b_max"], reaction=0.0, a_creep=0.0)
    return DL.long_simulate(0.0, 0.0, cmd, road=None, t_end=run["stops"][0][2], dt=0.01, params=prm)


# ─────────────────────────────── 継ぐ ───────────────────────────────
def test_chain_joints_match_in_closed_form_for_the_default_town():
    L = TW.town_layout()
    assert len(L["elements"]) == 9 and L["kind"] == "layout"
    dp, dy = _joint_errors(L)
    assert dp <= 1e-9 and dy <= 1e-9
    ch = L["chain"]
    expect = ch["lengths"].sum() - ch["overlap"] * (len(L["elements"]) - 1)
    assert abs(ch["total_length"] - expect) <= 1e-9          # 直線だけの町は厳密
    assert np.allclose(ch["s_start"][1:], np.cumsum(ch["polyline_lengths"][:-1] - ch["overlap"]))


def test_chain_joints_match_for_curved_elements_and_an_arbitrary_start():
    els = [DC.course_road(10.0), DC.course_s_curve(), DC.course_road(10.0), DC.course_crank(), DC.course_loop_bend()]
    L = TW.town_chain(els, start=(5.0, -3.0, 0.7), overlap=0.05)
    dp, dy = _joint_errors(L)
    assert dp <= 1e-9 and dy <= 1e-9
    assert np.allclose(L["elements"][0]["entry"], (5.0, -3.0, 0.7))
    ch = L["chain"]
    expect = ch["lengths"].sum() - 0.05 * 4
    assert abs(ch["total_length"] - expect) / expect < 1e-3      # 弧は折線で近似されるぶんだけ短い
    assert ch["total_length"] < expect


def test_chain_with_zero_overlap_sums_the_lengths_exactly():
    L = TW.town_chain([DC.course_road(10.0), DC.course_crossing(), DC.course_road(5.0)], overlap=0.0)
    assert abs(L["chain"]["total_length"] - L["chain"]["lengths"].sum()) <= 1e-9
    assert _joint_errors(L)[0] <= 1e-9


# ─────────────────────────────── 中心線・停止線 ───────────────────────────────
@pytest.mark.parametrize("step", [0.5, 0.3])
def test_centerline_spacing_is_exact_on_straights_and_ends_at_entry_and_exit(step):
    L = TW.town_layout()
    C = TW.town_centerline(L, step=step)
    assert C.shape[1] == 4 and np.all(np.diff(C[:, 0]) > 0)
    d = np.hypot(np.diff(C[:, 1]), np.diff(C[:, 2]))
    assert np.allclose(d[:-1], step, atol=1e-9) and d[-1] <= step + 1e-9
    assert np.allclose(C[0, 1:], L["elements"][0]["entry"], atol=1e-9)
    assert np.allclose(C[-1, 1:3], L["elements"][-1]["exit"][:2], atol=1e-9)
    assert abs(C[-1, 0] - L["chain"]["total_length"]) <= 1e-9


def test_stop_lines_are_the_driving_lane_only_and_mirror_with_side():
    L = TW.town_layout()
    st = TW.town_stop_lines(L)
    assert [d["kind"] for d in st] == ["intersection", "crossing"]
    # 交差点: 入口から L − d_stop = 23.5 − (3.5 + 3 + 4 + 2) = 11 m、町では 30 − 0.05 + 11
    assert abs(st[0]["s"] - (30.0 - 0.05 + 11.0)) <= 1e-9
    # 踏切: xc − zone/2 − 0.5 = 7.3 − 1.3 − 0.5 = 5.5 m、町では 30 + 47 + 20 − 3 × 0.05 + 5.5
    assert abs(st[1]["s"] - (97.0 - 0.15 + 5.5)) <= 1e-9
    z0, z1 = st[1]["crossing_zone"]
    assert abs((z1 - z0) - 2.6) <= 1e-9 and abs(z0 - (st[1]["s"] + 0.5)) <= 1e-9
    assert st[0]["drawn"] and st[1]["drawn"]
    # 右側通行: 交差点は 4 本のうち鏡像の 1 本(交差点の中心について対称)、踏切は閉形式で同じ位置(白線は描かれていない)
    rt = TW.town_stop_lines(L, side="right")
    assert [d["kind"] for d in rt] == ["intersection", "crossing"]
    centre = 30.0 - 0.05 + 23.5
    assert abs((st[0]["s"] + rt[0]["s"]) - 2 * centre) <= 1e-9 and rt[0]["s"] > st[0]["s"]
    assert abs(rt[1]["s"] - st[1]["s"]) <= 1e-9 and not rt[1]["drawn"]


# ─────────────────────────────── 走る・採点 ───────────────────────────────
@pytest.mark.parametrize("dt", [0.05, 0.02])
def test_run_gates_a_to_d_and_the_crossing_check(dt):
    L = TW.town_layout()
    r = TW.town_run(L, dt=dt)
    ck = TW.town_checks(r, L)
    p = r["params"]
    assert ck["count_ok"] and len(r["stops"]) == 2                                  # (d)
    assert len(ck["stops"]) == 2
    for e in ck["stops"]:
        assert 0.0 <= e["before"] <= 1.0 and e["ok"], e                              # (a)
    assert np.max(np.abs(r["a"])) <= max(p["a_max"], p["b_max"]) + 1e-9             # (b)
    assert r["v"].max() <= p["v_max"] + 1e-9 and r["v"].min() >= 0.0
    assert ck["kinematics"]["integral_gap"] <= dt * p["v_max"]                      # (c)
    assert ck["kinematics"]["integral_gap"] <= 1e-8                                 # 台形則で積分しているので実際は丸めまで
    cx = ck["stops"][1]["crossing"]
    assert cx["ok"] and cx["entered"] and cx["looked"] == ["left", "right"] and cx["violations"] == []
    assert ck["ok"] and ck["train"] is None
    assert r["s"][-1] == r["total_length"] and np.all(np.diff(r["t"]) > 0)
    looks = [ev for ev in r["events"] if ev[0] == "look"]
    assert [ev[2] for ev in looks] == ["left", "right", "left", "right"]


def test_braking_distance_respects_the_closed_form_lower_bound():
    L = TW.town_layout()
    r = TW.town_run(L)
    ck = TW.town_checks(r, L)
    assert len(ck["braking"]) == 2
    assert ck["braking"]
    for b in ck["braking"]:
        assert b["distance"] >= b["v_brake"] ** 2 / (2 * r["params"]["b_max"]) and b["ok"]  # (e) 定理
        assert b["v_brake"] > 3.0                                                            # 本当に走ってから止まっている


def test_the_stop_position_matches_the_rk4_second_implementation():
    L = TW.town_layout("short")
    r = TW.town_run(L, dt=0.05)
    res = _second_implementation(r)
    s_stop = r["stops"][0][0]
    assert abs(float(res["s"][-1]) - s_stop) <= r["params"]["dt"] * r["params"]["v_max"]
    s_mine = np.interp(res["t"], r["t"], r["s"])
    assert np.max(np.abs(s_mine - res["s"])) <= r["params"]["dt"] * r["params"]["v_max"]


def test_run_without_stops_is_free_flow():
    L = TW.town_layout("short")
    r = TW.town_run(L, stop_at=())
    assert r["stops"] == [] and set(r["mode"]) == {"cruise"}
    assert TW.town_checks(r, L)["ok"]
    assert r["v"].max() > 0.99 * r["params"]["v_max"]


# ─────────────────────────────── 法規パック ───────────────────────────────
def test_rule_packs_declare_their_verification_honestly():
    jp, us, de = TW.town_rules("JP"), TW.town_rules("US"), TW.town_rules("DE")
    assert jp["verified"] is True and jp["side"] == "left" and jp["crossing_stop"] == "always" and jp["look_required"]
    assert us and de
    for r in (us, de):
        assert r["verified"] is False and r["side"] == "right" and r["crossing_stop"] == "when_active"
        assert r["sources"] and r["notes"]
    jp["sources"].append("x")
    assert TW.town_rules("JP")["sources"] != jp["sources"]          # 複製(原本を汚さない)
    with pytest.raises(ValueError):
        TW.town_rules("XX")


def test_rules_change_the_stops_and_the_default_is_jp():
    L = TW.town_layout()
    r0 = TW.town_run(L)
    r_jp = TW.town_run(L, rules=TW.town_rules("JP"))
    assert r0["stops"] == r_jp["stops"] and r0["params"]["jurisdiction"] == "JP"          # 回帰: 引数なし = JP
    assert [k for _, k, *_ in r0["stops"]] == ["intersection", "crossing"]
    assert abs(r0["stops"][0][0] - 40.41) < 0.05 and abs(r0["stops"][1][0] - 101.81) < 0.05
    for j in ("US", "DE"):
        r = TW.town_run(L, rules=TW.town_rules(j))
        ck = TW.town_checks(r, L)
        assert [k for _, k, *_ in r["stops"]] == ["intersection"] and ck["ok"] and ck["count_ok"]
        assert r["targets"] == ["static", "dynamic"] and ck["stops"][1]["skipped"]
        assert len(r["events"]) > 0
    assert any(ev[0] == "pass" and ev[3] == "crossing" for ev in r["events"])
        assert abs(r["stop_lines"][0]["s"] - 65.95) <= 1e-9                                 # 鏡像の停止線に止まる
        assert ck["stops"][1]["crossing"]["ok"]                                            # 信号制御扱いで no_stop は免除


# ─────────────────────────────── 列車 ───────────────────────────────
def test_train_state_machine_in_jp_waits_until_the_boom_is_up():
    L = TW.town_layout()
    r = TW.town_run(L, train=20.0)
    ck = TW.town_checks(r, L)
    TR = r["train"]
    assert TR["t_closed"] == 35.0 and TR["t_arrival"] == 55.0 and TR["timing_check"]["meets_minimum"]
    assert abs(TR["t_clear"] - (55.0 + (80.0 + 7.0 + 2.0) / 20.0)) <= 1e-9
    assert ck["ok"] and ck["train"]["ok"] and ck["train"]["inside_while_forbidden_s"] == 0.0 and ck["train"]["go_after_clear"]
    go = [ev for ev in r["events"] if ev[0] == "go" and ev[3] == "crossing"][0]
    assert go[1] >= TR["forbidden_interval"][1] and "wait" in set(r["mode"])
    assert len(r["events"]) > 0
    assert any(ev[0] == "wait_gate" for ev in r["events"])
    cx = ck["stops"][1]["crossing"]
    assert cx["ok"] and cx["looked"] == ["left", "right"] and not cx["unavoidable"] and cx["t_entry"] > TR["forbidden_interval"][1]
    # 列車なしの走行とは踏切の発進だけが違う(それまでは同じ)
    r0 = TW.town_run(L)
    assert r0["stops"][0] == r["stops"][0] and r0["stops"][1][:3] == r["stops"][1][:3]


def test_when_active_rules_stop_only_while_warned_and_commit_when_too_close():
    L = TW.town_layout()
    r = TW.town_run(L, rules=TW.town_rules("US"), train=20.0)
    ck = TW.town_checks(r, L)
    assert [k for _, k, *_ in r["stops"]] == ["intersection", "crossing"] and ck["ok"] and ck["train"]["ok"]
    assert len(r["events"]) > 0
    assert not any(ev[0] == "look" for ev in r["events"])
    # 警報が、b_max で止まれない距離(v²/2b = 10.7 m)まで来た時に始まる → 進む(commit)、drivecrossing は unavoidable
    r_free = TW.town_run(L, rules=TW.town_rules("US"))
    s_line = r_free["stop_lines"][1]["s"]
    t_w = float(np.interp(s_line - 4.0, r_free["s"], r_free["t"]))
    r2 = TW.town_run(L, rules=TW.town_rules("US"), train=t_w)
    ck2 = TW.town_checks(r2, L)
    assert [k for _, k, *_ in r2["stops"]] == ["intersection"]
    assert len(r2["events"]) > 0
    assert any(ev[0] == "commit" and ev[3] == "crossing" for ev in r2["events"])
    cx = ck2["stops"][1]["crossing"]
    assert cx["unavoidable"] and cx["ok"] and ck2["stops"][1]["skipped"] and ck2["count_ok"]
    assert ck2["train"]["go_after_clear"] and ck2["train"]["n_crossing_go"] == 0
    assert ck2["train"]["committed"] and ck2["train"]["inside_while_forbidden_s"] > 0 and ck2["ok"]   # 警報中に中に居たが unavoidable
    # JP は同じ警報でも常に止まる → 警報中に中に居た時間 0
    r3 = TW.town_run(L, train=t_w)
    ck3 = TW.town_checks(r3, L)
    assert ck3["ok"] and not ck3["train"]["committed"] and ck3["train"]["inside_while_forbidden_s"] == 0.0


def test_world_gear_and_crossing_state():
    import driveworld as DW
    L = TW.town_layout("short")
    W = TW.town_world(L)
    assert set(W["town"]) == {"stop_lines", "signals", "crossings", "gear", "total_length"}
    assert [k for *_, k in W["town"]["stop_lines"]] == ["crossing"] and W["town"]["signals"] == []
    (x0, y0, x1, y1, s0, s1) = W["town"]["crossings"][0]
    assert abs((x1 - x0) - 2.6) <= 1e-9 and abs(s1 - s0 - 2.6) <= 1e-9
    g = W["town"]["gear"][0]
    assert len(g["booms"]) == 2 and len(g["posts"]) == 2 and len(g["lamps"]) == 8
    names = [o.get("name") for o in W["objects"]]
    assert names.count("boom") == 2 and names.count("train") == 1 and names.count("deck") == 1 and "rail" in names
    assert g["booms"]
    assert all(W["objects"][i]["label"] == 4 for i, *_ in g["booms"]) and W["objects"][g["train"]]["label"] == 6
    r = TW.town_run(L, train=5.0)
    # 遮断中: かんは水平(0.8 m の高さ)、灯は交互に点く、列車は到達の時刻に道路の縁の手前 margin に居る
    st = TW.town_crossing_state(W, r["train"]["t_closed"] + 1.0, r["train"])
    assert st["state_name"] == "closed" and st["boom_angle"] == 0.0 and st["entry_forbidden"]
    assert sorted(np.round(st["lamps"], 6).tolist()) == [0.0, 1.0]
    assert g["booms"]
    for i, pivot, sgn in g["booms"]:
        v0, v1 = W["objects"][i]["verts"]
        z = W["V"][v0:v1, 2]
        assert abs(z.max() - 0.8) <= 0.05 and abs(z.min() - 0.8) <= 0.05
    st2 = TW.town_crossing_state(W, r["train"]["t_arrival"], r["train"])
    assert abs(st2["train_y"] - (-(3.5 + 1.0))) <= 1e-9
    st3 = TW.town_crossing_state(W, 0.0, None)
    assert st3["state_name"] == "idle" and abs(st3["boom_angle"] - 0.5 * math.pi) <= 1e-12 and st3["train_y"] == -400.0
    K = DW.camera_intrinsics(60.0, 160, 100)
    TW.town_crossing_state(W, r["train"]["t_closed"] + 1.0, r["train"])
    P, c = TW._chain_polyline(L)
    e = TW._point_at(P, c, r["stops"][0][0] - 2.05)
    cam = DW.world_camera(W, DW.camera_pose((e[0], e[1], 1.35), (e[0] + 17.0, e[1], 0.9)), K, 160, 100)
    assert np.sum(cam["label"] == 4) > 0                      # 下りた遮断かんが車載カメラに映る
    with pytest.raises(ValueError):
        TW.town_crossing_state({"V": 0}, 0.0, None)
    with pytest.raises(ValueError):
        TW.town_crossing_state(W, 0.0, {"t_warning": 0.0})


# ─────────────────────────────── 台帳 ───────────────────────────────
def test_kyosoku_summary_counts_the_whole_ledger():
    S = TW.kyosoku_summary(_ledger_path())
    assert S["total"] == 159 and sum(S["by_status"].values()) == 159
    assert S["by_status"]["reproduced"] >= 38 and S["by_status"]["not_reproducible"] <= 10
    assert sum(row[-1] for row in S["table"]) == 159
    assert len(S["table"]) > 0
    assert all(sum(row[1:-1]) == row[-1] for row in S["table"])
    default = Path(TW.__file__).resolve().parent / "docs" / "drive" / "kyosoku_scenarios.json"
    if default.is_file():
        assert TW.kyosoku_summary()["total"] == 159
    else:
        with pytest.raises(ValueError):
            TW.kyosoku_summary()


# ─────────────────────────────── fail-closed ───────────────────────────────
def test_fail_closed():
    with pytest.raises(ValueError):
        TW.town_chain([])
    with pytest.raises(ValueError):
        TW.town_chain([TW.town_layout("short")])                        # layout の入れ子
    with pytest.raises(ValueError):
        TW.town_chain([DC.course_road(10.0)], overlap=-0.1)
    with pytest.raises(ValueError):
        TW.town_chain([DC.course_road(10.0), DC.course_road(1.0)], overlap=1.5)   # 中心線より長い食い込み
    with pytest.raises(ValueError):
        TW.town_chain([DC.course_road(10.0)], start=(0.0, float("nan"), 0.0))
    with pytest.raises(ValueError):
        TW.town_layout("nowhere")
    plain = DC.course_layout([DC.course_road(10.0)], [(0.0, 0.0, 0.0)])
    with pytest.raises(ValueError):
        TW.town_centerline(plain)                                        # town_chain の物でない layout
    L = TW.town_layout("short")
    with pytest.raises(ValueError):
        TW.town_centerline(L, step=0.0)
    with pytest.raises(ValueError):
        TW.town_stop_lines(L, side="middle")
    with pytest.raises(ValueError):
        TW.town_run(L, dt=0.0)
    with pytest.raises(ValueError):
        TW.town_run(L, stop_at=("slope",))
    with pytest.raises(ValueError):
        TW.town_run(L, stop_margin=2.0)
    with pytest.raises(ValueError):
        TW.town_run(L, v_stop=1.0)                                       # b_max·dt を超える v_stop
    with pytest.raises(ValueError):
        TW.town_run(L, t_max=1.0)                                        # 終点に着かない
    with pytest.raises(ValueError):
        TW.town_run(L, rules={"side": "left"})                           # 鍵の足りない規則
    with pytest.raises(ValueError):
        TW.town_run(L, rules="JP")
    with pytest.raises(ValueError):
        TW.town_run(L, train=(1.0, 2.0, 3.0, 4.0))
    with pytest.raises(ValueError):
        TW.town_run(L, train={"v_train": 20.0})                           # t_warning が無い
    with pytest.raises(ValueError):
        TW.town_run(L, train=(10.0, -5.0))
    with pytest.raises(ValueError):
        TW.town_checks({"t": [0, 1]}, L)
    with pytest.raises(ValueError):
        TW.kyosoku_summary(Path(__file__).with_name("no_such_ledger.json"))
