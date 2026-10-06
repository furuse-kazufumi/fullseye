# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""2026-10-07 レビューで確かめた欠陥の回帰(conngraph / graphinv / mathgeometry)。

各テストはレビューの反例そのもの:
1. 冪零(DAG)の隣接行列のスペクトル半径を ARPACK が 0 でなく返し、reservoir_from_graph が 0 を拒否せず拡大した
2. graph_layer_propagate が入力の和 <= 0 の受け手を 1e-300 で割り、出力が 4e-301 に潰れた
3. graph_core_persistence が辺 0 本の個体の「0-core = 全員」を最内殻として数えた
4. 次数保存ヌルが「頼んだ入れ替え数」だけを報告し、通った数(密なグラフで 1 割未満)が見えなかった
5. geodesic_heat が面に使われない頂点 1 個で全頂点 NaN、始点と繋がらない成分に有限の定数を返した
"""
from __future__ import annotations

import warnings

import numpy as np
import pytest

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import conngraph as C
    import graphinv as GI
    import mathgeometry as MG


# ── 1. 冪零な隣接行列のスペクトル半径 ─────────────────────────────────────────── #
def _chain(n, perm_seed=None):
    W = np.zeros((n, n))
    for i in range(n - 1):
        W[i, i + 1] = 1.0
    if perm_seed is not None:
        p = np.random.default_rng(perm_seed).permutation(n)
        W = W[np.ix_(p, p)]
    return W


def _layered_dag(seed=1, size=150, layers=4):
    rng = np.random.default_rng(seed)
    n = size * layers
    lab = np.repeat(np.arange(layers), size)
    W = np.zeros((n, n))
    for a in range(layers - 1):
        s = np.nonzero(lab == a)[0]
        d = np.nonzero(lab == a + 1)[0]
        W[np.ix_(s, d)] = (rng.random((size, size)) < 0.05) * rng.integers(1, 10, (size, size))
    return W, lab


@pytest.mark.parametrize("n,perm", [(500, None), (500, 0), (300, 0), (100, 0)])
def test_chain_dag_spectral_radius_is_exactly_zero(n, perm):
    W = _chain(n, perm)
    assert not np.linalg.matrix_power(W, n).any()          # 冪零の確認(真値 0)
    assert C.graph_spectral_radius(W) == 0.0               # 旧: n=500 で 0.366
    with pytest.raises(ValueError, match="spectral radius 0"):
        C.reservoir_from_graph(W, 0.9)


def test_layered_dag_reservoir_is_refused_not_rescaled():
    W, _ = _layered_dag()
    assert W.shape[0] > 400 and not np.linalg.matrix_power(W, 4).any()
    assert C.graph_spectral_radius(W) == 0.0               # 旧: 3.6e-5(→ 2.5 万倍に拡大)
    with pytest.raises(ValueError, match="spectral radius 0"):
        C.reservoir_from_graph(W, 0.9)


def test_dag_plus_small_cycle_radius_is_the_cycle_not_the_jordan_edge():
    # 同じ欠陥の兄弟: 大きな冪零部分(鎖 500)+ 小さな閉路 1 個。真値は閉路の幾何平均 = 0.01
    W = np.zeros((502, 502))
    W[:500, :500] = _chain(500)
    W[500, 501] = W[501, 500] = 0.01
    W[499, 500] = 1.0                                      # 鎖 → 閉路(半径は変えない)
    assert C.graph_spectral_radius(W) == pytest.approx(0.01, rel=1e-8)


def test_nonnegative_multi_scc_radius_matches_dense():
    # ARPACK の経路(n > 400、非負、複数の強連結成分)が密の eigvals と一致すること(有効入力を壊していない)
    rng = np.random.default_rng(3)
    n = 450
    W = (rng.random((n, n)) < 0.01) * rng.random((n, n))
    W[:, :50] = 0.0                                        # 50 個の湧き出し(単独の強連結成分)
    truth = float(np.max(np.abs(np.linalg.eigvals(W))))
    assert truth > 0
    assert C.graph_spectral_radius(W) == pytest.approx(truth, rel=1e-8)
    # 自己ループ 1 個だけが半径を決める場合
    D = _chain(500)
    D[7, 7] = 0.3
    assert C.graph_spectral_radius(D) == pytest.approx(0.3, rel=1e-12)


# ── 2. 入力の和 <= 0 の受け手 ──────────────────────────────────────────────── #
def test_layer_propagate_rejects_nonpositive_input_sum():
    W = np.zeros((4, 4))
    W[0, 2], W[1, 2] = 2.0, -3.0                           # 受け手 2 の入力の和 = -1
    W[0, 3], W[1, 3] = 1.0, 1.0
    lab = np.array([0, 0, 1, 1])
    U = np.eye(2)
    with pytest.raises(ValueError, match=r"receiver node 2 .*sum -1 <= 0"):
        C.graph_layer_propagate(W, lab, U, activation="linear")
    W[1, 2] = -2.0                                         # 和がちょうど 0(非零の重みあり)も拒否
    with pytest.raises(ValueError, match="receiver node 2"):
        C.graph_layer_propagate(W, lab, U, activation="tanh")


def test_layer_propagate_valid_inputs_unchanged():
    # 入力の無い受け手(列が全部 0)は 0 のまま、和が正の符号混じりは従来どおり
    W = np.zeros((5, 5))
    W[0, 2], W[1, 2] = 3.0, -1.0                           # 和 2 > 0
    W[0, 3], W[1, 3] = 1.0, 1.0
    lab = np.array([0, 0, 1, 1, 1])                        # 受け手 4 は入力なし
    U = np.array([[1.0, 0.0], [0.0, 1.0]])
    X = C.graph_layer_propagate(W, lab, U, activation="linear")
    u = U @ np.array([[1.5, 0.5, 0.0], [-0.5, 0.5, 0.0]])
    expect = u / np.abs(u).mean()
    assert np.allclose(X[:, 2:], expect, rtol=1e-12, atol=0)
    assert np.all(X[:, 4] == 0.0)


# ── 3. 殻の無い個体 ─────────────────────────────────────────────────────── #
def _triangle5():
    A = np.zeros((5, 5))
    for i, j in [(0, 1), (1, 2), (0, 2)]:
        A[i, j] = A[j, i] = 1
    return A


def test_core_persistence_empty_individual_contributes_no_member():
    A = _triangle5()
    r = GI.graph_core_persistence([A, A, np.zeros((5, 5))], mode="undirected")
    assert list(r["kmax"]) == [2, 2, 0]
    assert list(r["appearances"]) == [2, 2, 2, 0, 0]       # 旧: [3, 3, 3, 1, 1]
    assert r["n_persistent"] == 0 and r["n_recurrent"] == 3 and r["n_transient"] == 0 and r["n_never"] == 2
    assert not r["membership"][2].any()
    assert list(r["n_inner"]) == [3, 3, 0]
    assert int(r["n_inner"].sum()) == int(r["appearances"].sum())   # 恒等式は保つ


def test_core_persistence_identical_inputs_unchanged():
    A = _triangle5()
    r = GI.graph_core_persistence([A, A, A], mode="undirected")
    assert list(r["appearances"]) == [3, 3, 3, 0, 0]
    assert r["n_persistent"] == 3 and list(r["n_inner"]) == [3, 3, 3]


# ── 4. 通った入れ替えの数 ────────────────────────────────────────────────── #
def _dense(seed=0, n=40, p=0.9):
    rng = np.random.default_rng(seed)
    B = (rng.random((n, n)) < p).astype(np.int8)
    np.fill_diagonal(B, 0)
    return B


def test_rewire_counted_matches_edges_moved():
    B = _dense()
    E = int(B.sum())
    R, acc = GI._rewire_counted(B, np.random.default_rng(0), 5 * E)
    R2 = GI._rewire(B, np.random.default_rng(0), 5 * E)
    assert np.array_equal(R, R2)                           # 同じ乱数列で同じ結果(旧 API は不変)
    assert 0 < acc < 5 * E
    assert acc / (5 * E) < 0.2                             # 密度 0.9 では頼んだ数の 1 割未満しか通らない
    moved = int(((R != B) & (B == 1)).sum())
    assert moved <= 2 * acc                                # 1 回の入れ替えが外す辺は 2 本まで


def test_null_reports_accepted_swaps():
    B = _dense()
    E = int(B.sum())
    r = GI.graph_degree_preserving_null(B, n_samples=3)
    assert r["swaps"] == 5 * E                             # 意味は「頼んだ数」のまま
    assert len(r["swaps_accepted"]) == 3
    assert all(0 < a < r["swaps"] for a in r["swaps_accepted"])
    rc = GI.graph_rich_club_curve(B, n_null=2)
    assert len(rc["swaps_accepted"]) == 2
    assert all(0 < a <= rc["swaps"] for a in rc["swaps_accepted"])


def test_sparse_graph_accepts_almost_every_swap():
    rng = np.random.default_rng(5)
    B = (rng.random((200, 200)) < 0.02).astype(np.int8)
    np.fill_diagonal(B, 0)
    r = GI.graph_degree_preserving_null(B, n_samples=2, swaps_per_edge=1)
    assert len(r["swaps_accepted"]) == 2
    assert all(a == r["swaps"] for a in r["swaps_accepted"])


# ── 5. 測地距離: 未使用の頂点と非連結成分 ─────────────────────────────────────── #
def _grid(nx, ny, x0=0.0):
    xs, ys = np.meshgrid(np.linspace(0, 1, nx) + x0, np.linspace(0, 1, ny), indexing="ij")
    V = np.c_[xs.ravel(), ys.ravel(), np.zeros(nx * ny)]
    F = []
    for i in range(nx - 1):
        for j in range(ny - 1):
            a = i * ny + j
            b = a + ny
            F += [[a, b, a + 1], [b, b + 1, a + 1]]
    F = np.array(F)
    assert len(F) == 2 * (nx - 1) * (ny - 1)
    return V, F


def test_geodesic_heat_unreferenced_vertex_is_inf_not_all_nan():
    V, F = _grid(32, 16)
    d0 = MG.geodesic_heat(V, F, 0)["distance"]
    V2 = np.vstack([V, [[5.0, 5.0, 5.0]]])
    with warnings.catch_warnings():
        warnings.simplefilter("error")                     # 旧: MatrixRankWarning(特異)→ 全部 NaN
        d = MG.geodesic_heat(V2, F, 0)["distance"]
    assert len(d) == 513
    assert not np.isnan(d).any()
    assert np.isinf(d[-1])
    assert np.array_equal(d[:512], d0)                     # 残りは未使用の頂点が無い場合と同じ
    with pytest.raises(ValueError, match="source"):
        MG.geodesic_heat(V2, F, 512)


def test_geodesic_heat_disconnected_component_is_inf():
    Va, Fa = _grid(10, 10)
    Vb, Fb = _grid(10, 10, x0=3.0)
    V = np.vstack([Va, Vb])
    F = np.vstack([Fa, Fb + 100])
    d = MG.geodesic_heat(V, F, 0)["distance"]
    alone = MG.geodesic_heat(Va, Fa, 0)["distance"]
    assert np.all(np.isinf(d[100:]))                       # 旧: 0.755 の定数
    assert np.abs(d[:100] - alone).max() < 1e-12
    # 始点が両方の成分にある: 成分ごとに始点で 0
    d2 = MG.geodesic_heat(V, F, [0, 100])["distance"]
    assert np.all(np.isfinite(d2))
    assert d2[0] == pytest.approx(0.0, abs=1e-12) and d2[100] == pytest.approx(0.0, abs=1e-12)
    assert np.abs(d2[:100] - alone).max() < 1e-9
    assert np.abs(d2[100:] - alone).max() < 1e-9           # 同じ形の格子なので同じ距離
