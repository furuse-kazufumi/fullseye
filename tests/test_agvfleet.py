# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""agvfleet の門: CBS の最適性(結合 A* が真値)、焦点探索 ≤ w·最適、優先度付き計画の不完全性の実例、
行動依存グラフ(ADG)は遅れても衝突 0・デッドロック 0、追従の衝突の定義、時刻 0 の制約の回帰、VDA 5050 の規則、
fail-closed の ValueError。examples/poc_agv_fleet.py の門を単体テストにしたもの。"""
import itertools

import numpy as np
import pytest

import agvfleet as AF


def _small_instances(n_want=24, seed=1):
    """5×5 の乱数の格子に 2〜3 台(結合 A* で解ける問題だけ)。"""
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(8 * n_want):
        if len(out) >= n_want:
            break
        g = rng.random((5, 5)) > 0.2
        free = [tuple(map(int, x)) for x in np.argwhere(g)]
        n = int(rng.integers(2, 4))
        if len(free) < 2 * n:
            continue
        idx = rng.choice(len(free), 2 * n, replace=False)
        S, G = [free[i] for i in idx[:n]], [free[i] for i in idx[n:]]
        j = AF.mapf_joint_astar(g, S, G)
        if j["solved"]:
            out.append((g, S, G, j["cost"]))
    return out


def test_cbs_cost_equals_the_joint_astar_optimum():
    cases = _small_instances()
    assert len(cases) >= 20
    compared = 0
    for g, S, G, opt in cases:
        c = AF.mapf_cbs(g, S, G, max_nodes=20000)
        if not c["solved"]:
            continue                        # 節の上限(難しい問題)は数えない —— 件数の下限は下で
        compared += 1
        assert c["cost"] == opt, (S, G, c["cost"], opt)
        assert AF.plan_conflicts(c["paths"]) == []
        assert AF.plan_cost(c["paths"]) == c["cost"]
    assert compared >= 15, compared


def test_focal_search_cost_is_within_w_of_the_optimum():
    n = 0
    # w = 1 は最適の CBS と同じ木になり遅い(1 件で数十秒)ので、門は w > 1 だけ。節の上限で切れた問題は数えない
    for g, S, G, opt in _small_instances():
        for w in (1.3, 2.0):
            e = AF.mapf_ecbs(g, S, G, w=w, max_nodes=3000)
            if not e["solved"]:
                continue
            n += 1
            assert e["cost"] <= w * opt + 1e-9, (w, e["cost"], opt)
            assert e["lower_bound"] <= opt
            assert AF.plan_conflicts(e["paths"]) == []
    assert n >= 30, n


def test_prioritized_planning_is_incomplete_on_a_solvable_instance():
    g = np.array([[1, 1, 1, 1, 1], [1, 0, 1, 1, 1], [0, 0, 1, 1, 1], [1, 1, 1, 1, 1]], dtype=bool)
    S, G = [(3, 4), (2, 4)], [(0, 4), (3, 0)]
    orders = list(itertools.permutations(range(2)))
    assert len(orders) == 2
    for order in orders:
        r = AF.mapf_prioritized(g, S, G, order=order)
        assert not r["solved"] and r["paths"] is None and r["failed_agent"] in (0, 1)
    c = AF.mapf_cbs(g, S, G)
    j = AF.mapf_joint_astar(g, S, G)
    assert c["solved"] and j["solved"]
    assert c["cost"] == j["cost"] == 9


def _warehouse_plan(n=8, seed=5):
    grid, _ = AF.warehouse_grid(n_rack_rows=2, n_rack_cols=3, rack_len=3, aisle=2, margin=1)
    free = [tuple(map(int, x)) for x in np.argwhere(grid)]
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(free), 2 * n, replace=False)
    S, G = [free[i] for i in idx[:n]], [free[i] for i in idx[n:]]
    plan = AF.mapf_ecbs(grid, S, G, w=1.1)
    assert plan["solved"] and AF.plan_conflicts(plan["paths"]) == []
    return plan["paths"]


def test_adg_never_collides_or_deadlocks_under_delays():
    paths = _warehouse_plan()
    adg = AF.adg_build(paths)
    for seed in range(200):
        r = AF.adg_execute(adg, 0.3, seed)
        assert r["finished"] and not r["deadlock"] and r["collisions"] == 0, seed
    r0 = AF.adg_execute(adg, 0.0, 0)
    assert r0["finished"] and r0["makespan"] <= max(len(p) for p in paths) - 1


def test_naive_execution_deadlocks_with_delays_but_not_without():
    paths = _warehouse_plan()
    dead = sum(AF.naive_execute(paths, 0.3, s)["deadlock"] for s in range(200))
    assert dead > 0
    q = AF.naive_execute(paths, 0.0, 0)
    assert q["finished"] and not q["deadlock"]


def test_a_rotation_and_a_train_are_follow_conflicts():
    # 2×2 の輪を 4 台が同時に 1 マスずつ回る: vertex も edge も無いが、全台が「前の車が出た瞬間に入る」
    rot = [[(0, 0), (0, 1)], [(0, 1), (1, 1)], [(1, 1), (1, 0)], [(1, 0), (0, 0)]]
    kinds = {c[0] for c in AF.plan_conflicts(rot)}
    assert kinds == {"follow"}
    assert len(AF.plan_conflicts(rot)) == 4
    # 3 台の列が車間ゼロで同時に進む(輪でなくても追従)
    train = [[(0, 2), (0, 3)], [(0, 1), (0, 2)], [(0, 0), (0, 1)]]
    conf = AF.plan_conflicts(train)
    assert [c[0] for c in conf] == ["follow", "follow"]
    with pytest.raises(ValueError):
        AF.adg_build(rot)
    # 1 手ずらせば衝突なし
    ok = [[(0, 2), (0, 3)], [(0, 1), (0, 1), (0, 2)], [(0, 0), (0, 0), (0, 0), (0, 1)]]
    assert AF.plan_conflicts(ok) == []


def test_a_start_time_constraint_has_no_path():
    # 回帰(2026-10-03): 「時刻 0 に出発マスに居るな」は満たせない。以前は同じ経路を返し CBS が木を育て続けた
    g = np.ones((3, 3), dtype=bool)
    d = AF.grid_distances(g, (2, 2))
    assert AF._st_astar(g, (0, 0), (2, 2), d, {((0, 0), 0)}, set(), 20) is None
    p = AF._st_astar(g, (0, 0), (2, 2), d, set(), set(), 20)
    assert p[0] == (0, 0) and p[-1] == (2, 2) and len(p) == 5


def test_vda5050_orders_pass_and_a_broken_sequence_id_fails():
    paths = _warehouse_plan(n=4)
    assert len(paths) == 4
    for i, p in enumerate(paths):
        o = AF.vda5050_order(p, order_id="o%d" % i, released_nodes=max(1, len(AF._compress(p)[0]) // 2))
        assert AF.vda5050_check(o) == [], i
        ids = [n["sequenceId"] for n in o["nodes"]] + [e["sequenceId"] for e in o["edges"]]
        assert sorted(ids) == list(range(len(ids)))
    o = AF.vda5050_order(paths[0])
    assert len(o["nodes"]) >= 2
    o["nodes"][1]["sequenceId"] = 3
    errs = AF.vda5050_check(o)
    assert errs
    assert any("sequenceId" in e for e in errs)
    o2 = AF.vda5050_order(paths[0])
    del o2["orderId"]
    assert AF.vda5050_check(o2) == ["missing key orderId"]


def test_grid_and_distances():
    g, info = AF.warehouse_grid(1, 2, 2, 1, 1)
    assert g.shape == (3, 7) and g.dtype == bool and len(info["racks"]) == 4 and not g[1, 1]
    d = AF.grid_distances(g, (2, 6))
    assert d[2, 6] == 0 and d[0, 0] == 8 and np.isinf(d[1, 1])


def test_fail_closed():
    g = np.ones((3, 3), dtype=bool)
    with pytest.raises(ValueError):
        AF.warehouse_grid(n_rack_rows=0)
    with pytest.raises(ValueError):
        AF.mapf_cbs(np.ones((3, 3, 3), dtype=bool), [(0, 0)], [(1, 1)])
    with pytest.raises(ValueError):
        AF.mapf_cbs(g, [(0, 0), (0, 0)], [(1, 1), (2, 2)])
    gb = g.copy()
    gb[1, 1] = False
    with pytest.raises(ValueError):
        AF.mapf_cbs(gb, [(0, 0)], [(1, 1)])
    with pytest.raises(ValueError):
        AF.grid_distances(gb, (1, 1))
    with pytest.raises(ValueError):
        AF.mapf_prioritized(g, [(0, 0), (2, 2)], [(1, 0), (0, 2)], order=[0, 0])
    with pytest.raises(ValueError):
        AF.mapf_ecbs(g, [(0, 0)], [(1, 1)], w=0.9)
    with pytest.raises(ValueError):
        AF.vda5050_order([(0, 0), (0, 1)], released_nodes=0)
