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
