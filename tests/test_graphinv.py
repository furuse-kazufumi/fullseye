# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""graphinv — 配線行列の不変量 op の厳密な恒等式と fail-closed を検査する。

真値は 3 種類: (1) 定義から出る整数の恒等式(Σ入 = Σ出 = |E|)、(2) **第 2 実装**
(3 サイクルの総当たり)、(3) 対称操作(恒等ペアで Jaccard = 1、2 回入れ替えで元に戻る)。
乱数は「対称性の破れ」を隠すので、恒等式は**構造を作った小さなグラフ**でも確かめる
(有向 3 サイクル 1 個 / 相互辺 1 組 / 星)。
"""
from __future__ import annotations

import numpy as np
import pytest

import graphinv as G


def _cycle(n=3):
    """i -> i+1 -> ... -> 0 の有向 1 周。3 サイクルはちょうど 1 個、相互辺 0。"""
    B = np.zeros((n, n), int)
    for i in range(n):
        B[i, (i + 1) % n] = 1
    return B


def _random(n=40, p=0.15, seed=1):
    rng = np.random.default_rng(seed)
    B = (rng.random((n, n)) < p).astype(int)
    np.fill_diagonal(B, 0)
    return B


def _bruteforce_cycles3(B):
    n = B.shape[0]
    return sum(1 for i in range(n) for j in range(n) if B[i, j]
               for k in range(n) if B[j, k] and B[k, i]) // 3


# ---- 次数 ----------------------------------------------------------------
def test_degree_sums_equal_the_edge_count_on_a_structured_graph():
    d = G.graph_degree_summary(_cycle(5))
    assert d["edges"] == 5 and d["in_degree"].sum() == d["out_degree"].sum() == 5
    assert d["reciprocal_pairs"] == 0 and d["self_loops"] == 0


def test_self_loops_are_counted_separately_and_excluded():
    B = _cycle(4)
    B[2, 2] = 1
    d = G.graph_degree_summary(B)
    assert d["self_loops"] == 1 and d["edges"] == 4


def test_reciprocal_pair_is_counted_once():
    B = np.zeros((3, 3), int)
    B[0, 1] = B[1, 0] = 1
    assert G.graph_degree_summary(B)["reciprocal_pairs"] == 1


# ---- 3 サイクル ----------------------------------------------------------
def test_one_directed_triangle_is_exactly_one_cycle():
    assert G.graph_cycle3(_cycle(3))["cycles3"] == 1
    # 逆向きを足すと 2 個(向きが違えば別のサイクル)
    B = _cycle(3) + _cycle(3).T
    assert G.graph_cycle3(B)["cycles3"] == 2


def test_cycle3_agrees_with_the_brute_force_second_implementation():
    """★第 2 実装。tr(B³)/3 の off-by-three を単一実装では見つけられない。"""
    for seed in (1, 2, 3):
        B = _random(seed=seed)
        assert G.graph_cycle3(B)["cycles3"] == _bruteforce_cycles3(B)


# ---- 次数保存のヌル --------------------------------------------------------
def test_null_samples_keep_every_degree_exactly():
    """★門そのもの: 入れ替えが次数列を 1 つも変えないこと(op の中でも検査している)。"""
    B = _random(n=60, p=0.1)
    r = G.graph_degree_preserving_null(B, n_samples=4, swaps_per_edge=3, seed=0)
    assert r["edges"] == int(B.sum())
    assert r["n_samples"] == 4 and r["swaps"] == 3 * int(B.sum())


def test_a_triangle_free_graph_gets_zero_observed_cycles():
    B = np.zeros((6, 6), int)
    for i in range(3):                       # 2 部グラフ(3+3)は 3 サイクルを持てない
        for j in range(3, 6):
            B[i, j] = 1
    r = G.graph_degree_preserving_null(B, n_samples=3, swaps_per_edge=2, seed=0)
    assert r["cycles3"] == 0


def test_null_is_seeded_and_reproducible():
    B = _random()
    a = G.graph_degree_preserving_null(B, n_samples=3, seed=7)
    b = G.graph_degree_preserving_null(B, n_samples=3, seed=7)
    assert a["cycles3_null_mean"] == b["cycles3_null_mean"]


# ---- 入れ替え対称性 --------------------------------------------------------
def test_identity_pairing_gives_exactly_one():
    B = _random()
    assert G.graph_swap_symmetry(B, [])["jaccard"] == 1.0


def test_a_perfectly_mirrored_graph_gives_exactly_one():
    """左右対称に作った配線は、L/R を入れ替えても 1.0。"""
    half = _random(n=10, seed=4)
    B = np.zeros((20, 20), int)
    B[:10, :10] = half
    B[10:, 10:] = half                       # 右半分は左半分の写し
    pairs = [(i, i + 10) for i in range(10)]
    assert G.graph_swap_symmetry(B, pairs)["jaccard"] == 1.0


def test_swapping_twice_recovers_the_original_matrix():
    B = _random(n=12, seed=5)
    pairs = [(0, 1), (2, 3), (4, 5)]
    perm = np.arange(12)
    for i, j in pairs:
        perm[i], perm[j] = j, i
    twice = B[np.ix_(perm, perm)][np.ix_(perm, perm)]
    assert np.array_equal(twice, B)


def test_swap_symmetry_reports_the_pair_count():
    B = _random(n=12, seed=6)
    assert G.graph_swap_symmetry(B, [(0, 1), (2, 3)])["n_pairs"] == 2


# ---- fail-closed -----------------------------------------------------------
@pytest.mark.parametrize("bad", [
    np.array([[1, -1], [0, 1]]),             # 負
    np.array([[1, 2, 3]]),                   # 非正方
    np.zeros((0, 0)),                        # 空
    np.array([[1.0, np.nan], [0, 1]]),       # 非有限
    np.array([["a", "b"], ["c", "d"]]),      # 文字列
])
def test_bad_matrices_are_refused(bad):
    with pytest.raises(ValueError):
        G.graph_degree_summary(bad)


def test_null_refuses_too_few_samples_and_edges():
    with pytest.raises(ValueError):
        G.graph_degree_preserving_null(_random(), n_samples=1)
    with pytest.raises(ValueError):
        G.graph_degree_preserving_null(np.array([[0, 1], [0, 0]]), n_samples=3)


def test_swap_symmetry_refuses_bad_pairs():
    B = _random(n=6)
    with pytest.raises(ValueError):
        G.graph_swap_symmetry(B, [(0, 0)])
    with pytest.raises(ValueError):
        G.graph_swap_symmetry(B, [(0, 1), (1, 2)])
    with pytest.raises(ValueError):
        G.graph_swap_symmetry(B, [(0, 9)])


# ---- 個体間の重なり(graph_edge_consensus) ------------------------------
def _series(K=5, n=20, core=15, uniq=6, seed=0, weighted=True):
    """核 core 本を全員に、固有 uniq 本を個体ごとに重ならず。閉形式が全部決まる構造。"""
    rng = np.random.default_rng(seed)
    cand = np.array([(i, j) for i in range(n) for j in range(n) if i != j])
    pick = rng.choice(len(cand), size=core + K * uniq, replace=False)
    mats = []
    for k in range(K):
        M = np.zeros((n, n))
        for (i, j) in cand[pick[:core]]:
            M[i, j] = 4 if weighted else 1
        for (i, j) in cand[pick[core + k * uniq: core + (k + 1) * uniq]]:
            M[i, j] = 1
        mats.append(M)
    return mats


def test_consensus_closed_form_on_core_plus_unique_series():
    K, core, uniq = 5, 15, 6
    r = G.graph_edge_consensus(_series(K, core=core, uniq=uniq), ordered=True)
    assert r["occupancy_hist"] == [0, K * uniq, 0, 0, 0, core]
    off = r["jaccard"][~np.eye(K, dtype=bool)]
    assert np.all(off == core / (core + 2 * uniq))
    assert (r["stable"], r["added"], r["lost"], r["flicker"]) == (core, uniq, uniq, (K - 2) * uniq)
    # 核の重み 4 x core x K、固有 1 x uniq x K
    assert r["synapse_share"][K] == pytest.approx(4 * core / (4 * core + uniq))


def test_consensus_counting_identities_on_random_individuals():
    rng = np.random.default_rng(5)
    mats = [(rng.random((25, 25)) < 0.2) * rng.integers(1, 6, (25, 25)) for _ in range(4)]
    r = G.graph_edge_consensus(mats, ordered=True)
    h = r["occupancy_hist"]
    assert h[0] == 0
    assert sum(c * x for c, x in enumerate(h)) == sum(r["edges_per_individual"])
    assert sum(h) == r["union"]
    assert r["stable"] + r["added"] + r["lost"] + r["flicker"] == r["union"]
    assert sum(r["synapse_share"]) == pytest.approx(1.0)
    J = r["jaccard"]
    assert np.allclose(J, J.T) and np.all(np.diag(J) == 1.0)


def test_consensus_identical_individuals_share_every_edge():
    B = _random(30, 0.2, seed=3)
    r = G.graph_edge_consensus({"a": B, "b": B, "c": B})
    assert r["occupancy_hist"][3] == r["union"] == int(B.sum())
    assert np.all(r["jaccard"] == 1.0) and r["names"] == ["a", "b", "c"]


def test_consensus_order_matters_only_for_the_developmental_split():
    mats = _series(4, core=10, uniq=5, seed=2)
    fwd = G.graph_edge_consensus(mats, ordered=True)
    rev = G.graph_edge_consensus(mats[::-1], ordered=True)
    assert fwd["occupancy_hist"] == rev["occupancy_hist"]
    assert (fwd["added"], fwd["lost"]) == (rev["lost"], rev["added"])


def test_consensus_null_keeps_degrees_and_finds_no_planted_core():
    r = G.graph_edge_consensus(_series(6, n=40, core=40, uniq=30, seed=1), n_null=4)
    assert r["occupancy_hist"][6] == 40
    assert r["shared_all_null_max"] < 40            # 核は次数だけでは再現しない
    assert r["n_null"] == 4 and len(r["occupancy_null_mean"]) == 7


def test_consensus_self_loops_are_dropped_and_input_not_mutated():
    B = _random(10, 0.3, seed=4).astype(float)
    B[0, 0] = 5.0
    before = B.copy()
    r = G.graph_edge_consensus([B, B])
    assert np.array_equal(B, before)
    assert r["edges_per_individual"][0] == int((before > 0).sum()) - 1


@pytest.mark.parametrize("bad, kw", [
    ([np.eye(3, k=1)], {}),                                     # 1 個体
    ([np.eye(3, k=1), np.eye(4, k=1)], {}),                     # 大きさ違い
    ([np.eye(3, k=1), np.zeros((3, 3))], {}),                   # 辺ゼロ
    ([np.eye(3, k=1), -np.eye(3, k=1)], {}),                    # 負
    ([np.eye(3, k=1), np.eye(3, k=1)], {"n_null": 1}),          # 広がりが測れない
    ([np.eye(3, k=1), np.eye(3, k=1)], {"swaps_per_edge": 0}),
    (np.stack([np.eye(3, k=1)] * 2), {}),                       # 3-D 配列(個体の束は list か table で)
    ("abc", {}),
])
def test_consensus_refuses(bad, kw):
    with pytest.raises(ValueError):
        G.graph_edge_consensus(bad, **kw)


def test_consensus_refuses_a_non_square_image_table():
    # 非正方の画像は形の検査で止まる。★正方の画像は重み行列と区別できない(全画素 > 0 なら
    # 全結合として数える)—— 入力が配線であることは呼び手の責任で、op は形しか確かめられない
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError):
        G.graph_edge_consensus({"a": rng.random((16, 24)), "b": rng.random((16, 24))})
