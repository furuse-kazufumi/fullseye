"""粘菌ソルバの回帰テスト —— 答えの分かっている迷路で最短路に収束するか。

正本の構想 = afterman/docs/SUBSTRATE_REDESIGN.md「2. 粘菌」。
モデル = Tero ら 2010(Science)、収束証明 = Bonifaci ら 2012(mu>=1)。

ここで固定する性質:
- 短い道と長い遠回りがある迷路で、**短い道を太らせ長い道を細らせる**
- 生き残った管を辿った道が BFS の最短ホップ数と一致する
- numpy 経路と torch(cpu)経路が同じ答えを出す(GPU へ載せる前提)
- 左右対称のタイでは両方が等しく残る(縮退の扱いが暴れない)
"""
import os
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


@pytest.mark.skipif(os.environ.get("GITHUB_ACTIONS") == "true",
                    reason="wall-clock perf claim — shared CI runners invert the "
                    "ratio (measured 疎 1.8-3.2s vs dense 0.2-0.3s there); "
                    "performance is asserted on dedicated hardware only")
def test_sparse_is_faster_than_dense_at_scale():
    """疎版は dense O(n^3) より速い。倍率は機械依存なので緩めに 3x を下限に。

    ★**1 発計時は門にならない**(2026-09-22)。この門は 1 回ずつ測って 3 倍を
    要求していたため、同じ木・同じ機械で通ったり落ちたりした(実測: 疎 1175 ms
    対 密 3251 ms = 2.77 倍で失敗、直前の実行では通過)。OS のスケジューラと
    キャッシュの揺れがそのまま入るので、**各側を 3 回測って最小値を採る** ——
    最小値は計時の雑音に対していちばん頑健な推定量で、1 回目が暖機を兼ねる
    (この repo の「性能は熱定常で測る」規律)。閾値の 3 倍は緩めない。
    """
    import time
    free = np.ones((21, 21), bool)
    g = P.maze_to_graph(free)
    s, t = P.node_at(g, 0, 0), P.node_at(g, 20, 20)

    def best_of_three(device):
        best = float("inf")
        for _ in range(3):
            t0 = time.perf_counter()
            P.solve_physarum(g, s, t, mu=2.0, dt=0.2, max_iters=1000, device=device)
            best = min(best, time.perf_counter() - t0)
        return best

    dense = best_of_three("numpy_dense")
    sparse = best_of_three("numpy")
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


def _has_cuda():
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


@pytest.mark.skipif(not _has_cuda(), reason="CUDA GPU 不在")
def test_gpu_fp32_finds_shortest_path():
    """GPU + FP32 でも最短を太らせ遠回りを枝刈りする(ユニーク最短路)。"""
    free, s_rc, t_rc = _short_vs_long()
    g = P.maze_to_graph(free)
    s, t = P.node_at(g, *s_rc), P.node_at(g, *t_rc)
    D = P.solve_physarum_batch(g, [s], [t], mu=1.0, dt=0.2, time_steps=200,
                               cg_iters=200, device="cuda", dtype="float32")
    top = [d for (i, j), d in zip(g.edges, D[0])
           if g.coords[i, 0] == 0 and g.coords[j, 0] == 0]
    bot = [d for (i, j), d in zip(g.edges, D[0])
           if g.coords[i, 0] == 2 and g.coords[j, 0] == 2]
    assert np.median(top) > 0.9
    assert np.median(bot) < 0.01


@pytest.mark.skipif(not _has_cuda(), reason="CUDA GPU 不在")
def test_cuda_graph_matches_eager():
    """CUDA graph 捕獲版が eager 固定反復版と一致(非縮退グラフではビット一致)。

    捕獲は 1 タイムステップ(固定反復 CG + D 更新)を replay するだけなので、
    同じ固定反復・同じ dtype の eager と数値一致すべき。縮退(等長最短路が多数)の
    小グリッドは FP32 のタイ選択が割れるため、ここでは非縮退の大グリッドで見る。
    """
    import torch
    k, B = 40, 6
    g = P.maze_to_graph(np.ones((k, k), bool))
    cor = [(0, 0), (0, k - 1), (k - 1, 0), (k - 1, k - 1)]
    srcs = [P.node_at(g, *cor[i % 4]) for i in range(B)]
    snks = [P.node_at(g, *cor[(i + 1) % 4]) for i in range(B)]
    eager = P.solve_physarum_batch(g, srcs, snks, mu=2.0, dt=0.2, time_steps=80,
                                   cg_iters=150, device="cuda", dtype="float32",
                                   cg_tol=0, cg_check_every=10**9)
    graph = P.solve_physarum_batch(g, srcs, snks, mu=2.0, dt=0.2, time_steps=80,
                                   cg_iters=150, device="cuda", dtype="float32",
                                   use_cuda_graph=True)
    # 太管(生き残る経路)の選択が一致
    assert ((eager > 0.5) == (graph > 0.5)).mean() > 0.98


@pytest.mark.skipif(not _has_cuda(), reason="CUDA GPU 不在")
def test_cuda_graph_requires_cuda_device():
    with pytest.raises(ValueError):
        free, s_rc, t_rc = _short_vs_long()
        g = P.maze_to_graph(free)
        s, t = P.node_at(g, *s_rc), P.node_at(g, *t_rc)
        P.solve_physarum_batch(g, [s], [t], device="cpu", use_cuda_graph=True)



# ── 型付き台帳の op: graph_physarum_path / physarum_route ─────────────────── #
def _lattice(n, seed):
    """n×n 格子、辺長 U(0.5, 1.5)(最短路はほぼ確実に一意)。afterman の PH と同じ作り。"""
    rng = np.random.default_rng(seed)
    A = np.zeros((n * n, n * n))
    for r in range(n):
        for c in range(n):
            u = r * n + c
            if c + 1 < n:
                A[u, u + 1] = A[u + 1, u] = rng.uniform(0.5, 1.5)
            if r + 1 < n:
                A[u, u + n] = A[u + n, u] = rng.uniform(0.5, 1.5)
    return A


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_graph_physarum_path_matches_dijkstra_and_converges_to_the_indicator(seed):
    from scipy.sparse.csgraph import dijkstra
    A = _lattice(7, seed)
    r = P.graph_physarum_path(A, 0, 48, dt=0.3)
    d = dijkstra(A, indices=0)[48]
    assert r["converged"] and r["path"][0] == 0 and r["path"][-1] == 48
    assert r["path_length"] == pytest.approx(d, abs=1e-9)
    assert d - 1e-12 <= r["flow_length"] < d + 1e-4                  # 単位流量の長さ ≥ 最短(厳密)、収束で等号へ
    on = r["conductance"][r["path"][:-1], r["path"][1:]]
    assert on.min() > 0.99                                            # Bonifaci: 最短路の管は 1 へ
    off = r["conductance"].copy()
    off[r["path"][:-1], r["path"][1:]] = 0
    off[r["path"][1:], r["path"][:-1]] = 0
    assert off.max() < 1e-2                                           # それ以外は 0 へ
    assert np.allclose(r["flow"], -r["flow"].T)


def test_graph_physarum_path_is_symmetric_under_relabelling_and_reversal():
    A = _lattice(6, 4)
    perm = np.random.default_rng(0).permutation(36)
    inv = np.argsort(perm)
    r = P.graph_physarum_path(A, 0, 35, dt=0.3)
    q = P.graph_physarum_path(A[np.ix_(perm, perm)], inv[0], inv[35], dt=0.3)
    assert q["path_length"] == pytest.approx(r["path_length"], abs=1e-9)
    assert perm[q["path"]].tolist() == r["path"].tolist()
    back = P.graph_physarum_path(A, 35, 0, dt=0.3)                    # 向きを逆にしても同じ道
    assert back["path"][::-1].tolist() == r["path"].tolist()


def test_graph_physarum_path_refuses_bad_input():
    A = _lattice(4, 0)
    for bad in (A[:3], A + 1e-9 * np.eye(16), -A, np.where(A > 0, np.nan, 0.0), "x"):
        with pytest.raises(ValueError):
            P.graph_physarum_path(bad)
    B = A.copy()
    B[1, 0] = 0.0                                                      # 非対称
    with pytest.raises(ValueError):
        P.graph_physarum_path(B)
    with pytest.raises(ValueError):
        P.graph_physarum_path(A, 0, 0)
    with pytest.raises(ValueError):
        P.graph_physarum_path(A, 0, 99)
    C = np.zeros((4, 4)); C[0, 1] = C[1, 0] = 1.0; C[2, 3] = C[3, 2] = 1.0
    with pytest.raises(ValueError):                                    # 到達不能
        P.graph_physarum_path(C, 0, 3)
    with pytest.raises(ValueError):
        P.graph_physarum_path(A, dt=0.0)


def test_physarum_route_equals_route_through_array_and_the_end_identity():
    from skimage.graph import route_through_array
    c = np.random.default_rng(1).uniform(0.5, 1.5, (9, 9))
    r = P.physarum_route(c, snapshots=3)
    path, cost = route_through_array(c, (0, 0), (8, 8), fully_connected=False, geometric=False)
    assert r["converged"] and r["path_cost"] == pytest.approx(cost, abs=1e-9)
    assert r["path"].tolist() == [list(p) for p in path]
    assert r["route_length"] == pytest.approx(cost - 0.5 * (c[0, 0] + c[8, 8]), abs=1e-12)   # 両端の半分
    assert r["route_length"] - 1e-12 <= r["flow_length"] < r["route_length"] + 1e-4
    assert r["conductance"].shape == (9, 9) and r["conductance"][tuple(r["path"].T)].min() > 0.99
    assert len(r["snapshots"]) == 3 and np.allclose(r["snapshots"][-1], r["conductance"])
    assert r["snapshot_iters"][-1] == r["iters"]
    # 8 近傍: 斜めは √2 倍。真値は geometric=True の route_through_array
    r8 = P.physarum_route(c, connectivity=8)
    _, c8 = route_through_array(c, (0, 0), (8, 8), fully_connected=True, geometric=True)
    assert r8["route_length"] == pytest.approx(c8, abs=1e-9)          # geometric=True は両端を半分で数える


def test_physarum_route_walls_are_avoided_and_a_tie_is_refused():
    from skimage.graph import route_through_array
    c = np.random.default_rng(7).uniform(0.5, 1.5, (7, 7))
    c[3, :6] = 1000.0                                                  # 壁: 右端の 1 画素だけ通れる
    r = P.physarum_route(c, (0, 0), (6, 0))
    _, cost = route_through_array(c, (0, 0), (6, 0), fully_connected=False, geometric=False)
    assert (r["path"][:, 1] == 6).any() and r["path_cost"] == pytest.approx(cost, abs=1e-9)
    # 一様なコスト = 同じ長さの道が何本もある(タイ)。導電度は分かれたまま 1 本に収束しない → 拒否(fail-closed)
    with pytest.raises(ValueError, match="tie|converged"):
        P.physarum_route(np.ones((5, 5)), max_iters=400)
    for bad in (np.ones((7, 7)) * 0.0, np.ones(7), np.full((7, 7), np.inf), "x"):
        with pytest.raises(ValueError):
            P.physarum_route(bad)
    with pytest.raises(ValueError):
        P.physarum_route(np.ones((7, 7)), (0, 0), (0, 0))
    with pytest.raises(ValueError):
        P.physarum_route(np.ones((7, 7)), (0, 0), (9, 9))
    with pytest.raises(ValueError):
        P.physarum_route(np.ones((7, 7)), connectivity=6)
