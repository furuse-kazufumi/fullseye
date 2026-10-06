# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""braidpath の門(複数エージェントの経路を組紐と Dynnikov 座標でホモトピー類に分ける)。

numpy + scipy だけ。全部で数秒:
 1. 組紐の関係式が Dynnikov の作用で恒等的に成り立つ(乱数の実数・整数の座標、σᵢσᵢ₊₁σᵢ = σᵢ₊₁σᵢσᵢ₊₁、遠い対の可換、σσ⁻¹ = 1)
 2. 3 つの独立な判定(Dynnikov 座標・取っ手簡約・Artin 表現)が「等しい / 違う」の両側で一致する
 3. 参照実装(MIT)の出力と一致: Dynnikov 座標・自明かどうか・Dehornoy の順序の主の添字と符号(tests/data の 240 件)
 4. 巻き数の閉形式: k 周の公転で k、純粋な組紐で 2W = 対の交差の符号つきの数(ちょうど)
 5. 交換子: 2 つの穴のまわりを a b a⁻¹ b⁻¹ と回ると巻き数は全部 0 なのに組紐は自明でない
 6. 格子の類ごとの最短経路: 費用の閉形式 d + (輪の長さ)·m、切り込みを入れた格子の BFS(agvfleet)と一致
 7. 既存の計画器(agvfleet)の経由点つきの経路を被験者に: 類は列挙の中、費用は列挙の最短以上、安い 2 類はちょうど当たる
 8. 摂動で類が変わらない(両側: 同じ類は同じ、違う類は違う)・射影の角度に依らない・時間の細分に依らない
 9. 射影の三重点: jitter=0 は TriplePointError、自動のずらしの類 = 独立な乱数の摂動の類
10. 綴り壊しは ValueError、衝突・粗い刻みは止める、出力が空・定数・inf でない
11. 入口: __all__ が実在、docstring に Markdown のリンク記法なし、ソースに acos / asin の呼び出しなし、モジュール docstring の呼び出し例が走る
"""
from __future__ import annotations

import json
import math
import pathlib
import random

import numpy as np
import pytest

import braidpath as B

DATA = pathlib.Path(__file__).parent / "data" / "braidpath_reference.json"


def _raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    return False


def _rewrite(w, n, steps, rng):
    """関係式だけを使って同じ組紐の別の語にする(三つ組の入れ替え・遠い対の可換・σσ⁻¹ の挿入)。"""
    w = list(w)
    for _ in range(steps):
        r = rng.random()
        if r < 0.3 and len(w) >= 3:
            k = rng.randrange(len(w) - 2)
            a, b, c = w[k:k + 3]
            if a == c and abs(abs(a) - abs(b)) == 1 and (a > 0) == (b > 0):
                w[k:k + 3] = [b, a, b]
                continue
        if r < 0.6 and len(w) >= 2:
            k = rng.randrange(len(w) - 1)
            a, b = w[k:k + 2]
            if abs(abs(a) - abs(b)) >= 2:
                w[k:k + 2] = [b, a]
                continue
        k = rng.randint(0, len(w))
        i, s = rng.randint(1, n - 1), rng.choice([1, -1])
        w[k:k] = [s * i, -s * i]
    return w


# ---------------------------------------------------------------------------------------------------------------------
# 1. 関係式の恒等性
def test_braid_relations_hold_identically_on_random_coordinates():
    rng = random.Random(1)
    worst_int, worst_real, n_checks = 0, 0.0, 0
    for trial in range(600):
        n = rng.randint(3, 7)
        real = trial % 2 == 1
        co = [rng.uniform(-40, 40) if real else rng.randint(-25, 25) for _ in range(2 * (n - 1))]
        i, s = rng.randint(1, n - 2), rng.choice([1, -1])
        pairs = [([s * i, s * (i + 1), s * i], [s * (i + 1), s * i, s * (i + 1)]), ([i], [i])]
        j = rng.randint(1, n - 1)
        if abs(i - j) >= 2:
            pairs.append(([i, s * j], [s * j, i]))
        for k in (i, i + 1):
            pairs.append(([k, -k], []))
            pairs.append(([-k, k], []))
        for lhs, rhs in pairs:
            a = B.dynnikov_act(co, lhs)["key"]
            b = B.dynnikov_act(co, rhs)["key"] if rhs else tuple(co)
            err = max(abs(x - y) for x, y in zip(a, b))
            if real:
                worst_real = max(worst_real, err)
            else:
                worst_int = max(worst_int, err)
            n_checks += 1
    assert worst_int == 0                      # 整数では厳密
    assert worst_real < 1e-11                  # 実数は丸めだけ
    assert n_checks > 3000


def test_a_wrong_relation_is_not_an_identity():
    """否定の側: 関係式でない等式(σ₁σ₂ = σ₂σ₁、隣り合う対の可換)は乱数の座標でほぼ必ず破れる。"""
    rng = random.Random(2)
    broken = 0
    for _ in range(200):
        co = [rng.randint(-20, 20) for _ in range(6)]
        broken += B.dynnikov_act(co, [1, 2])["key"] != B.dynnikov_act(co, [2, 1])["key"]
    assert broken > 150


# ---------------------------------------------------------------------------------------------------------------------
# 2. 3 つの独立な判定
def test_three_independent_deciders_agree_on_both_sides():
    rng = random.Random(3)
    n_eq = n_ne = 0
    for trial in range(300):
        n = rng.randint(2, 6)
        w = [rng.choice([1, -1]) * rng.randint(1, n - 1) for _ in range(rng.randint(0, 12))]
        if trial % 2:
            v = _rewrite(w, n, 8, rng)
        else:
            v = list(w)
            v.insert(rng.randint(0, len(v)), rng.choice([1, -1]) * rng.randint(1, n - 1))
        r = B.braid_equivalent(w, v, n, method="all")     # 食い違えば RuntimeError
        if trial % 2:
            assert r["equal"]
            n_eq += 1
        else:
            assert not r["equal"]                       # 1 文字足すと置換の偶奇か長さの和が変わる
            n_ne += 1
    assert n_eq >= 140 and n_ne >= 140


def test_handle_reduction_preserves_the_braid_and_leaves_no_handle():
    rng = random.Random(4)
    for _ in range(200):
        n = rng.randint(2, 6)
        w = [rng.choice([1, -1]) * rng.randint(1, n - 1) for _ in range(rng.randint(0, 25))]
        r = B.braid_reduce(w, n).tolist()
        assert B.dynnikov_coordinates(r, n)["key"] == B.dynnikov_coordinates(w, n)["key"]
        if r:                                          # 取っ手の無い語の主の文字は符号がそろう
            m = min(abs(x) for x in r)
            assert len({x > 0 for x in r if abs(x) == m}) == 1


def test_artin_images_are_identity_exactly_for_trivial_words():
    assert B.braid_artin_images([1, 2, 1, -2, -1, -2], 3)["identity"]
    assert not B.braid_artin_images([1, 2, 1, -2, -1], 3)["identity"]
    # 手計算: σ₁ で x₁ ↦ x₁x₂x₁⁻¹、x₂ ↦ x₁。続く σ₂ は今の像を x₂x₃x₂⁻¹ と x₂ に代入する。
    assert B.braid_artin_images([1, 2], 3)["images"] == [[1, 2, -1], [1, 3, -1], [1]]


# ---------------------------------------------------------------------------------------------------------------------
# 3. 参照実装との一致
def test_matches_the_reference_implementation_outputs():
    d = json.loads(DATA.read_text())
    cases = d["cases"]
    assert len(cases) >= 200
    n_trivial = 0
    for c in cases:
        n, w = c["n"], c["word"]
        dy = B.dynnikov_coordinates(w, n)
        assert [v for p in zip(dy["a"], dy["b"]) for v in p] == c["ref_dynnikov_interleaved"]
        r = B.braid_reduce(w, n).tolist()
        assert (len(r) == 0) == (c["ref_reduced_length"] == 0)
        if r:
            m = min(abs(x) for x in r)
            sign = 1 if [x for x in r if abs(x) == m][0] > 0 else -1
            assert (m, sign) == (c["ref_main_index"], c["ref_main_sign"])   # Dehornoy の順序は不変量
        else:
            n_trivial += 1
    assert 40 < n_trivial < len(cases) - 40            # 両側が十分にある


# ---------------------------------------------------------------------------------------------------------------------
# 4. 巻き数の閉形式
def _orbit(turns, steps=200, r=1.0):
    t = np.linspace(0, 1, steps)
    th = 2 * math.pi * turns * t
    a = np.stack([r * np.cos(th), r * np.sin(th)], -1)
    return np.stack([a, np.zeros_like(a)])


@pytest.mark.parametrize("turns", [1, 2, -3])
def test_winding_of_k_turn_orbit_is_k_and_word_sum_matches(turns):
    P = _orbit(turns)
    W = B.pairwise_winding(P)
    assert abs(W[0, 1] - turns) < 1e-12
    assert int(B.braid_from_trajectories(P)["word"].sum()) == 2 * turns


def _crossings_by_pair(br):
    """語の各文字を、その時に入れ替わった紐の対に割り当てて符号を足す。"""
    order = list(br["start_order"])
    c = {}
    for x in br["word"].tolist():
        p = abs(x) - 1
        u, v = sorted((order[p], order[p + 1]))
        c[(u, v)] = c.get((u, v), 0) + (1 if x > 0 else -1)
        order[p], order[p + 1] = order[p + 1], order[p]
    return c


def test_winding_equals_half_the_signed_crossings_for_random_pure_braids():
    rng = np.random.default_rng(5)
    checked = 0
    for _ in range(25):
        K, T = 4, 400
        t = np.linspace(0, 1, T)
        base = rng.uniform(-3, 3, (K, 2))
        P = np.empty((K, T, 2))
        for k in range(K):                              # 始点に戻る閉じた動き(フーリエの和)
            P[k] = base[k]
            for h in range(1, 4):
                amp = rng.normal(0, 1.2 / h, 2)
                ph = rng.uniform(0, 2 * math.pi, 2)
                P[k, :, 0] += amp[0] * (np.sin(2 * math.pi * h * t + ph[0]) - math.sin(ph[0]))
                P[k, :, 1] += amp[1] * (np.sin(2 * math.pi * h * t + ph[1]) - math.sin(ph[1]))
        try:
            br = B.braid_from_trajectories(P)
            W = B.pairwise_winding(P)
        except ValueError:
            continue
        if br["clearance"] < 0.05:
            continue
        cr = _crossings_by_pair(br)
        for i in range(K):
            for j in range(i + 1, K):
                assert abs(2 * W[i, j] - cr.get((i, j), 0)) < 1e-9
        checked += 1
    assert checked >= 15


# ---------------------------------------------------------------------------------------------------------------------
# 5. 交換子: 巻き数は区別できない、組紐は区別する
def _commutator_loop(steps=240):
    t = np.linspace(0, 1, steps)
    seg = []
    for cx, sgn in ((-1.0, 1), (1.0, 1), (-1.0, -1), (1.0, -1)):     # a b a⁻¹ b⁻¹
        th = np.linspace(0, 2 * math.pi, steps // 4, endpoint=False) * sgn
        start = math.pi if cx > 0 else 0.0              # 原点から出て原点へ戻る円
        seg.append(np.stack([cx + np.cos(start + th), np.sin(start + th)], -1))
    path = np.vstack(seg + [np.zeros((1, 2))])
    return path[None], np.array([[-1.0, 0.0], [1.0, 0.0]]), len(t)


def test_commutator_has_zero_winding_but_a_nontrivial_braid():
    P, O, _ = _commutator_loop()
    W = B.pairwise_winding(P, O)
    assert np.max(np.abs(W[0, 1:])) < 1e-12
    still = np.zeros_like(P)
    r = B.homotopy_class_compare(P, still, O)
    assert not r["same"] and r["quotient"].size > 0


# ---------------------------------------------------------------------------------------------------------------------
# 6. 格子の類ごとの最短経路
def _pillar_grid():
    g = np.ones((9, 13), bool)
    g[3:6, 5:8] = False
    return g


def test_class_shortest_paths_follow_the_ring_closed_form_and_cut_bfs():
    import agvfleet as AF

    g = _pillar_grid()
    r = B.homotopy_shortest_paths(g, (4, 1), (4, 11), k=5)
    assert r["costs"].tolist() == [14, 14, 30, 30, 46]          # d + 16 m(3×3 の柱を囲む輪は 16 手)
    gu, gd = g.copy(), g.copy()
    gu[0:3, 6] = False                                          # 上に切り込み → 下を回るしかない
    gd[6:, 6] = False
    assert AF.grid_distances(gu, (4, 11))[4, 1] == 14 and AF.grid_distances(gd, (4, 11))[4, 1] == 14
    assert len(set(r["keys"])) == 5
    assert len(r["paths"]) == 5
    for p in r["paths"]:
        assert all(g[tuple(c)] for c in p)
        assert np.all(np.abs(np.diff(p, axis=0)).sum(1) == 1)


def test_planner_paths_fall_into_the_enumerated_classes():
    """被験者 = agvfleet の 1 台の計画(経由点つき)。類は列挙の中、費用は類の最短以上、安い 2 類はちょうど当たる。"""
    import agvfleet as AF

    g = np.ones((10, 14), bool)
    g[2:4, 4:7] = False
    g[6:8, 8:11] = False
    s, e = (5, 0), (5, 13)
    ex = B.homotopy_shortest_paths(g, s, e, k=8)
    exact = dict(zip(ex["keys"], ex["costs"]))
    O = ex["obstacles"]
    rng = random.Random(7)
    free = [tuple(int(v) for v in c) for c in np.argwhere(g)]
    hit = {}
    for _ in range(60):
        v = rng.choice(free)
        if v in (s, e):
            continue
        a = AF.mapf_cbs(g, [s], [v])["paths"][0]
        b = AF.mapf_cbs(g, [v], [e])["paths"][0]
        path = list(a) + list(b[1:])
        P = B.grid_paths_to_xy([path])
        key = B.dynnikov_coordinates(B.braid_from_trajectories(P, O)["word"], 1 + len(O))["key"]
        hit[key] = min(hit.get(key, 1e9), len(path) - 1)
    inside = [k for k, c in hit.items() if c <= ex["costs"][-1]]
    assert inside                                               # 0 件では検証にならない
    assert all(k in exact for k in inside)
    assert all(hit[k] >= exact[k] for k in inside)
    cheapest = sorted(exact.items(), key=lambda kv: kv[1])[:2]
    assert len(cheapest) == 2
    assert all(k in hit and hit[k] == c for k, c in cheapest)


# ---------------------------------------------------------------------------------------------------------------------
# 8. 摂動・角度・細分に依らない(両側)
def _three_agent_classes():
    import agvfleet as AF

    g = _pillar_grid()
    starts, goals = [(4, 1), (4, 11), (0, 6)], [(4, 11), (4, 1), (8, 6)]
    plans = [AF.mapf_cbs(g, starts, goals)]
    rng = random.Random(0)
    free = [tuple(int(v) for v in c) for c in np.argwhere(g)]
    for _ in range(40):
        vias = [rng.choice(free) for _ in starts]
        p1 = AF.mapf_prioritized(g, starts, vias, order=rng.sample(range(3), 3))
        p2 = AF.mapf_prioritized(g, vias, goals, order=rng.sample(range(3), 3)) if p1["solved"] else {"solved": False}
        if not p2["solved"]:
            continue
        T1 = max(len(p) for p in p1["paths"])
        paths = [list(a) + [a[-1]] * (T1 - len(a)) + list(b[1:]) for a, b in zip(p1["paths"], p2["paths"])]
        if not AF.plan_conflicts(paths):
            plans.append({"paths": paths})
    O = B.grid_hole_points(g)
    rep = B.braid_class_representatives(plans, O)
    reps = [B.grid_paths_to_xy(plans[c["best"]]["paths"]) for c in rep["classes"]]
    return reps, O, rep


def _perturb(P, amp, rng):
    """端を止めた滑らかな摂動(sin の窓)。"""
    T = P.shape[1]
    w = np.sin(np.linspace(0, math.pi, T))[None, :, None]
    noise = rng.normal(0, 1, (P.shape[0], 4, 2))
    t = np.linspace(0, 1, T)
    bump = sum(noise[:, h][:, None, :] * np.sin((h + 1) * math.pi * t)[None, :, None] for h in range(4)) / 4
    return P + amp * w * bump


def test_perturbation_keeps_the_class_on_both_sides():
    reps, O, rep = _three_agent_classes()
    assert rep["n_classes"] >= 5
    rng = np.random.default_rng(8)
    same = diff = 0
    for i, P in enumerate(reps[:6]):
        Q = _perturb(P, 0.12, rng)                     # 最小距離 1 マスに対して振幅 0.12(重なりは作らない)
        assert B.homotopy_class_compare(P, Q, O)["same"]
        same += 1
        for j, R in enumerate(reps[:6]):
            if j != i:
                assert not B.homotopy_class_compare(Q, R, O)["same"]
                diff += 1
    assert same == 6 and diff == 30


def _refine(P, m):
    """各刻みを m 等分した同じ動き(直線の内挿)。"""
    t0 = np.arange(P.shape[1])
    t1 = np.linspace(0, P.shape[1] - 1, (P.shape[1] - 1) * m + 1)
    return np.stack([np.stack([np.interp(t1, t0, P[k, :, d]) for d in range(2)], -1) for k in range(P.shape[0])])


def test_class_verdicts_do_not_depend_on_the_projection_angle_or_time_refinement():
    reps, O, _ = _three_agent_classes()
    reps = reps[:5]

    def verdicts(angle, refine=1):
        out = []
        for i in range(len(reps)):
            for j in range(len(reps)):
                A, Bm = reps[i], reps[j]
                if refine > 1:
                    A, Bm = _refine(A, refine), _refine(Bm, refine)
                out.append(B.homotopy_class_compare(A, Bm, O, angle=angle)["same"])
        return out

    ref = verdicts(B.DEFAULT_ANGLE)
    assert sum(ref) == len(reps)                         # 対角だけが同じ
    for ang in (0.0, 0.37, 1.1, 2.4, -0.8):
        assert verdicts(ang) == ref
    assert verdicts(B.DEFAULT_ANGLE, refine=3) == ref


# ---------------------------------------------------------------------------------------------------------------------
# 9. 射影の三重点
def test_triple_point_is_resolved_by_jitter_and_agrees_with_a_random_perturbation():
    t = np.linspace(0, 1, 2)
    a = np.stack([5 + t, -2 + 0 * t], -1)               # 障害物の点 (6, -4) をはさんで点対称に動く 2 台
    b = np.stack([7 - t, -6 + 0 * t], -1)
    P, O = np.stack([a, b]), np.array([[6.0, -4.0]])
    assert _raises(lambda: B.braid_from_trajectories(P, O, jitter=0.0), B.TriplePointError)
    r = B.braid_from_trajectories(P, O)
    assert r["jitter"] > 0 and r["word"].size == 3
    rng = np.random.default_rng(9)
    keys = set()
    for _ in range(10):
        Q = P + rng.normal(0, 1e-3, (2, 1, 2))           # 一定の乱数のずらし(ずらしより 1000 倍大きい)
        rq = B.braid_from_trajectories(Q, O + rng.normal(0, 1e-3, (1, 2)), jitter=0.0)
        keys.add(B.dynnikov_coordinates(rq["word"], 3)["key"])
    assert keys == {B.dynnikov_coordinates(r["word"], 3)["key"]}


# ---------------------------------------------------------------------------------------------------------------------
# 10. 綴り壊し・衝突・出力の中身
def test_bad_inputs_raise():
    assert _raises(lambda: B.braid_reduce([0], 3))
    assert _raises(lambda: B.braid_reduce([3], 3))
    assert _raises(lambda: B.braid_reduce([1.5], 3))
    assert _raises(lambda: B.dynnikov_coordinates([1], 1))
    assert _raises(lambda: B.dynnikov_act([1, 2, 3], [1]))
    assert _raises(lambda: B.dynnikov_act([1, float("nan")], [1]))
    assert _raises(lambda: B.braid_equivalent([1], [1], 3, method="guess"))
    assert _raises(lambda: B.braid_from_trajectories(np.zeros((1, 5, 2))))          # 紐 1 本
    assert _raises(lambda: B.braid_from_trajectories(np.full((2, 3, 2), np.nan)))
    t = np.linspace(-1, 1, 5)
    hit = np.stack([np.stack([t, 0 * t], -1), np.stack([-t, 0 * t], -1)])         # 正面衝突
    assert _raises(lambda: B.braid_from_trajectories(hit))
    assert _raises(lambda: B.pairwise_winding(_orbit(1, steps=3)))                 # 1 刻みで半回転以上
    A = _orbit(1)
    Bm = A.copy()
    Bm[0, -1] += 0.5
    assert _raises(lambda: B.homotopy_class_compare(A, Bm))
    assert _raises(lambda: B.homotopy_shortest_paths(np.ones((4, 4), bool), (0, 0), (3, 3)))   # 穴が無い
    assert _raises(lambda: B.homotopy_shortest_paths(_pillar_grid(), (4, 6), (4, 11)))       # 塞がったマス


def test_outputs_are_not_empty_constant_or_infinite():
    w = [1, 2, -1, 3, 2, 2, -3, 1]
    d = B.dynnikov_coordinates(w, 4)
    vals = np.asarray(d["a"] + d["b"], dtype=float)
    assert vals.size == 6 and np.all(np.isfinite(vals)) and np.ptp(vals) > 0
    W = B.pairwise_winding(_orbit(2))
    assert np.all(np.isfinite(W)) and np.ptp(W) > 0
    r = B.homotopy_shortest_paths(_pillar_grid(), (4, 1), (4, 11), k=3)
    assert len(r["paths"]) == 3 and np.ptp(r["costs"]) > 0 and np.all(np.isfinite(r["costs"]))
    long = [1, -2] * 60                                  # σ₁σ₂⁻¹ は擬アノソフ(伸長率 φ²): 座標は 64 bit を超えても溢れない
    big = B.dynnikov_coordinates(long, 3)
    assert big["bits"] > 63 and isinstance(big["max_abs"], int)


def test_entry_points_are_real_and_the_source_is_clean():
    import inspect
    src = inspect.getsource(B)
    assert len(B.__all__) == 12 and all(callable(getattr(B, n)) for n in B.__all__)
    assert "](" not in src.replace("]((", "")                              # docstring に Markdown のリンク記法なし
    assert "acos(" not in src and "asin(" not in src and "arccos(" not in src and "arcsin(" not in src


def test_usage_example_in_the_module_docstring_runs(capsys):
    """モジュール docstring の呼び出し例をそのまま実行する(説明のコード例は走らせる門が無いと静かに壊れる)。"""
    import textwrap
    doc = B.__doc__
    i = doc.index("呼び出し例")
    block = doc[doc.index("::", i) + 2:]
    lines = []
    for ln in block.splitlines()[1:]:
        if ln.strip() and not ln.startswith("    "):
            break
        lines.append(ln)
    code = textwrap.dedent("\n".join(lines))
    assert code.count("\n") >= 8 and "print(" in code
    exec(compile(code, "<braidpath usage>", "exec"), {})
    out = capsys.readouterr().out.strip()
    # 類ごとの最短 [12, 12, 28]・上と下は別の類(False)・語とその簡約は同じ組紐(True)・柱のまわり半周
    assert out == "[12. 12. 28.] False True [-1] [0] -0.5", out
