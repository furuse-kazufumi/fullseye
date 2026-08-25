"""粘菌ソルバの回帰テスト —— 答えの分かっている迷路で最短路に収束するか。

正本の構想 = afterman/docs/SUBSTRATE_REDESIGN.md「2. 粘菌」。
モデル = Tero ら 2010(Science)、収束証明 = Bonifaci ら 2012(mu>=1)。

ここで固定する性質:
- 短い道と長い遠回りがある迷路で、**短い道を太らせ長い道を細らせる**
- 生き残った管を辿った道が BFS の最短ホップ数と一致する
- numpy 経路と torch(cpu)経路が同じ答えを出す(GPU へ載せる前提)
- 左右対称のタイでは両方が等しく残る(縮退の扱いが暴れない)
"""
import numpy as np
import pytest

import physarum_search as P


def _short_vs_long():
    """上段=直通(6 ホップ)、下段=遠回り(10 ホップ)。唯一の最短路は上段。"""
    free = np.array([
        [1, 1, 1, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 1, 1],
    ], bool)
    return free, (0, 0), (0, 6)


def _median_D_on_rows(g, res, rows):
    vals = [d for (i, j), d in zip(g.edges, res.D)
            if g.coords[i, 0] in rows and g.coords[j, 0] in rows]
    return float(np.median(vals)) if vals else float("nan")


@pytest.mark.parametrize("mu", [1.0, 1.5, 2.0])
def test_finds_the_shortest_path(mu):
    free, s_rc, t_rc = _short_vs_long()
    g = P.maze_to_graph(free)
    s, t = P.node_at(g, *s_rc), P.node_at(g, *t_rc)
    res = P.solve_physarum(g, s, t, mu=mu, dt=0.2, max_iters=5000)
    assert res.converged
    path = P.surviving_path(g, res, s, t, frac=0.5)
    assert len(path) - 1 == P.bfs_shortest_len(g, s, t) == 6
    # 道は全部上段(row 0)を通る
    assert all(g.coords[u, 0] == 0 for u in path)


def test_long_detour_is_pruned():
    """下段(遠回り)の管が上段(最短)より桁で細る = 軟らかい枝刈り。"""
    free, s_rc, t_rc = _short_vs_long()
    g = P.maze_to_graph(free)
    s, t = P.node_at(g, *s_rc), P.node_at(g, *t_rc)
    res = P.solve_physarum(g, s, t, mu=1.0, dt=0.2, max_iters=5000)
    top = _median_D_on_rows(g, res, {0})
    bot = _median_D_on_rows(g, res, {2})
    assert top > 0.9
    assert bot < 0.01
    assert top / max(bot, 1e-12) > 100


def test_numpy_and_torch_agree():
    free, s_rc, t_rc = _short_vs_long()
    g = P.maze_to_graph(free)
    s, t = P.node_at(g, *s_rc), P.node_at(g, *t_rc)
    a = P.solve_physarum(g, s, t, mu=1.0, dt=0.2, device="numpy")
    if not P._HAS_TORCH:
        pytest.skip("torch 不在")
    b = P.solve_physarum(g, s, t, mu=1.0, dt=0.2, device="cpu")
    # 同じ式なので最終 D はほぼ一致
    assert np.allclose(np.sort(a.D), np.sort(b.D), atol=1e-6)


def test_symmetric_tie_keeps_both_routes():
    """ロの字(左右対称)。両ルートが等長なので両方 D=0.5 で残る。"""
    H = W = 7
    free = np.zeros((H, W), bool)
    free[0, :] = free[-1, :] = free[:, 0] = free[:, -1] = True
    g = P.maze_to_graph(free)
    s, t = P.node_at(g, 0, 0), P.node_at(g, H - 1, W - 1)
    res = P.solve_physarum(g, s, t, mu=1.0, dt=0.2, max_iters=5000)
    assert res.converged
    # 経路上の辺は全部同じ太さ(タイ)。ばらつきが小さいことを確認。
    assert res.D.std() < 1e-3
    path = P.surviving_path(g, res, s, t, frac=0.5)
    assert len(path) - 1 == P.bfs_shortest_len(g, s, t)


def test_sparse_matches_dense_on_a_unique_shortest_path():
    """疎+CG+warm start が dense 参照実装と同じ最終 D を出す(ユニーク最短路)。

    縮退(等長最短路が多数)では CG と直接解が違うタイを選ぶので一致しない。
    ユニークなら完全一致すべき、というのがここの契約。
    """
    free, s_rc, t_rc = _short_vs_long()
    g = P.maze_to_graph(free)
    s, t = P.node_at(g, *s_rc), P.node_at(g, *t_rc)
    rd = P.solve_physarum(g, s, t, mu=1.0, dt=0.2, device="numpy_dense")
    rs = P.solve_physarum(g, s, t, mu=1.0, dt=0.2, device="numpy")
    assert rd.iters == rs.iters
    assert np.allclose(np.sort(rd.D), np.sort(rs.D), atol=1e-5)


def test_sparse_is_faster_than_dense_at_scale():
    """疎版は dense O(n^3) より速い。倍率は機械依存なので緩めに 3x を下限に。"""
    import time
    free = np.ones((21, 21), bool)
    g = P.maze_to_graph(free)
    s, t = P.node_at(g, 0, 0), P.node_at(g, 20, 20)
    t0 = time.perf_counter()
    P.solve_physarum(g, s, t, mu=2.0, dt=0.2, max_iters=1000, device="numpy_dense")
    dense = time.perf_counter() - t0
    t0 = time.perf_counter()
    P.solve_physarum(g, s, t, mu=2.0, dt=0.2, max_iters=1000, device="numpy")
    sparse = time.perf_counter() - t0
    assert sparse * 3 < dense, f"疎 {sparse*1000:.0f}ms vs dense {dense*1000:.0f}ms"


def test_batched_matfree_matches_sparse():
    """matrix-free バッチ CG(GPU 向け)が scipy 疎版と同じ最終 D を出す。"""
    if not P._HAS_TORCH:
        pytest.skip("torch 不在")
    free, s_rc, t_rc = _short_vs_long()
    g = P.maze_to_graph(free)
    s, t = P.node_at(g, *s_rc), P.node_at(g, *t_rc)
    ref = P.solve_physarum(g, s, t, mu=1.0, dt=0.2, max_iters=137, tol=0)
    Db = P.solve_physarum_batch(g, [s], [t], mu=1.0, dt=0.2, time_steps=137,
                                cg_iters=300, device="cpu")
    assert np.allclose(np.sort(ref.D), np.sort(Db[0]), atol=1e-3)


def test_batch_solves_independent_problems():
    """1 グラフの上で複数の(源,吸込)を同時に解いても、各行が独立の答えになる。"""
    if not P._HAS_TORCH:
        pytest.skip("torch 不在")
    free, _, _ = _short_vs_long()
    g = P.maze_to_graph(free)
    a = P.node_at(g, 0, 0)
    b = P.node_at(g, 0, 6)
    c = P.node_at(g, 2, 0)
    D = P.solve_physarum_batch(g, [a, a], [b, c], mu=1.0, dt=0.2,
                               time_steps=200, cg_iters=300, device="cpu")
    # 別々の吸込なので、まとめて解いても 1 個ずつ解いた結果と一致すべき
    d0 = P.solve_physarum(g, a, b, mu=1.0, dt=0.2, max_iters=200, tol=0)
    d1 = P.solve_physarum(g, a, c, mu=1.0, dt=0.2, max_iters=200, tol=0)
    assert np.allclose(np.sort(D[0]), np.sort(d0.D), atol=1e-3)
    assert np.allclose(np.sort(D[1]), np.sort(d1.D), atol=1e-3)


def test_disconnected_sink_returns_no_path():
    free = np.array([
        [1, 1, 1, 0, 1, 1, 1],   # 中央が壁で源側と吸込側が分断
    ], bool)
    g = P.maze_to_graph(free)
    s = P.node_at(g, 0, 0)
    t = P.node_at(g, 0, 6)
    assert P.bfs_shortest_len(g, s, t) == -1
    res = P.solve_physarum(g, s, t, mu=1.0, max_iters=500)
    assert P.surviving_path(g, res, s, t) == []
