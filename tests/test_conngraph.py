# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""conngraph(結合グラフ解析)の門: 厳密な真値 + 台帳と公開経路。

真値はすべて閉形式(リング / スター / 完全グラフ / 2 クリーク / 手で書いた再帰)で、
乱数入力だけの検査にしない(乱数は対称性の破れを隠す —— この repo の規律)。
"""
from __future__ import annotations

import os
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import conngraph as C  # noqa: E402

_OPS = [n for n in C.__all__ if n.islower()]


# --------------------------------------------------------------------------- #
# 生成器(真値が分かっているグラフ)                                            #
# --------------------------------------------------------------------------- #
def _ring(n=8):
    W = np.zeros((n, n))
    for i in range(n):
        W[i, (i + 1) % n] = 1.0
    return W


def _star(n=7):
    W = np.zeros((n, n))
    W[0, 1:] = 1.0
    W[1:, 0] = 1.0
    return W


def _complete(n=5):
    return np.ones((n, n)) - np.eye(n)


def _two_cliques(k=4):
    W = np.zeros((2 * k, 2 * k))
    W[:k, :k] = 1.0
    W[k:, k:] = 1.0
    np.fill_diagonal(W, 0.0)
    return W


def _random_graph(n=30, p=0.15, seed=1):
    rng = np.random.default_rng(seed)
    W = (rng.random((n, n)) < p) * rng.uniform(0.5, 2.0, (n, n))
    np.fill_diagonal(W, 0.0)
    return W


# --------------------------------------------------------------------------- #
# 1. build                                                                     #
# --------------------------------------------------------------------------- #
def test_graph_from_synapses_round_trips_a_known_edge_list():
    syn = np.array([[0, 1, 3], [1, 2, 2], [0, 1, 1], [2, 0, 5]], dtype=np.float64)
    W = C.graph_from_synapses(syn)
    assert W.shape == (3, 3) and W.dtype == np.float64
    assert W[0, 1] == 4.0 and W[1, 2] == 2.0 and W[2, 0] == 5.0 and W.sum() == 11.0
    # 逆向き: 隣接行列 → 表 → 隣接行列 で同じ行列
    pre, post = np.nonzero(W)
    back = C.graph_from_synapses(np.stack([pre, post, W[pre, post]], axis=1), n=3)
    assert np.array_equal(back, W)
    assert C.graph_from_synapses(syn, n=5).shape == (5, 5)
    assert C.graph_from_synapses(syn, sign=-1.0)[0, 1] == -4.0


def test_graph_from_synapses_refuses_bad_ids():
    with pytest.raises(ValueError, match="graph_from_synapses"):
        C.graph_from_synapses(np.array([[0.5, 1, 1]]))
    with pytest.raises(ValueError, match="out of range"):
        C.graph_from_synapses(np.array([[0, 4, 1]], dtype=float), n=3)
    with pytest.raises(ValueError, match="graph_from_synapses"):
        C.graph_from_synapses(np.array([[0, 1]], dtype=float))


def test_shuffle_keeps_degrees_and_weights_but_moves_edges():
    W = _random_graph()
    H = C.graph_degree_preserving_shuffle(W, seed=3)
    d0, d1 = C.graph_degree_table(W), C.graph_degree_table(H)
    assert np.array_equal(d0["in_degree"], d1["in_degree"])
    assert np.array_equal(d0["out_degree"], d1["out_degree"])
    assert not np.array_equal(W != 0, H != 0), "辺集合が 1 本も動いていない"
    assert np.allclose(np.sort(W[W != 0]), np.sort(H[H != 0])), "重みの多重集合が変わった"
    assert not np.diag(H).any(), "自己結合が作られた"
    # 決定的
    assert np.array_equal(H, C.graph_degree_preserving_shuffle(W, seed=3))


def test_binarize_thresholds_on_magnitude():
    W = np.array([[0.0, 0.2, -0.9], [0.5, 0.0, 0.0], [0.0, 0.05, 0.0]])
    B = C.graph_binarize(W, thresh=0.1)
    assert set(np.unique(B)) <= {0.0, 1.0}
    assert B[0, 1] == 1.0 and B[0, 2] == 1.0 and B[2, 1] == 0.0


# --------------------------------------------------------------------------- #
# 2. stats(閉形式の真値)                                                     #
# --------------------------------------------------------------------------- #
def test_ring_laplacian_spectrum_is_the_cosine_formula():
    n = 8
    ev = C.graph_laplacian_spectrum(_ring(n))
    want = np.sort(2.0 - 2.0 * np.cos(2.0 * np.pi * np.arange(n) / n))
    assert ev.shape == (n,) and np.allclose(ev, want)


def test_star_betweenness_is_all_on_the_centre():
    n = 7
    bc = C.graph_betweenness(_star(n))                    # 無向(相互)スター
    assert bc[0] == pytest.approx((n - 1) * (n - 2) / 2)
    assert np.all(bc[1:] == 0.0)
    # 有向の経路 0→1→2 では順序対のまま: 中間の 1 だけが 1
    path = np.zeros((3, 3))
    path[0, 1] = path[1, 2] = 1.0
    assert C.graph_betweenness(path).tolist() == [0.0, 1.0, 0.0]


def test_complete_graph_closed_forms():
    n = 5
    K = _complete(n)
    assert C.graph_clustering_coefficient(K) == pytest.approx(1.0)
    assert C.graph_spectral_radius(K) == pytest.approx(n - 1)
    assert C.graph_rich_club(K, 1) == pytest.approx(1.0)
    assert C.graph_rich_club(K, 100) == 0.0                         # 該当 0 個 → NaN でなく 0
    deg = C.graph_degree_table(K)
    assert np.all(deg["in_degree"] == n - 1) and np.all(deg["out_strength"] == n - 1)


def test_two_cliques_components_modularity_and_layout():
    W = _two_cliques(4)
    lab = C.graph_components(W)
    assert lab.tolist() == [0, 0, 0, 0, 1, 1, 1, 1]
    assert C.graph_modularity(W, lab) > 0.4
    assert C.graph_modularity(W, lab) == pytest.approx(0.5)
    assert C.graph_modularity(W, np.zeros(8, dtype=int)) == pytest.approx(0.0)
    P = C.graph_layout_spectral(W)
    assert P.shape == (8, 3) and P.min() >= 0.0 and P.max() <= 1.0 and np.all(P[:, 2] == 0.0)
    D = np.linalg.norm(P[:, None] - P[None], axis=-1)
    within = max(D[i, j] for i, j in combinations(range(8), 2) if (i < 4) == (j < 4))
    across = min(D[i, j] for i in range(4) for j in range(4, 8))
    assert across > within, (across, within)
    assert C.graph_layout_spectral(W, dim=3).shape == (8, 3)


def test_motif_counts_each_instance_once():
    M = np.zeros((6, 6))
    M[0, 1] = M[1, 2] = M[0, 2] = 1.0            # 1 個の FFL
    M[3, 4] = M[4, 5] = M[5, 3] = 1.0            # 1 個の 3 巡回
    assert C.graph_motif_count(M, "ffl") == 1.0
    assert C.graph_motif_count(M, "cycle3") == 1.0
    assert C.graph_motif_count(M, "reciprocal") == 0.0
    R = np.array([[0.0, 1.0], [1.0, 0.0]])
    assert C.graph_motif_count(R, "reciprocal") == 1.0
    with pytest.raises(ValueError, match="graph_motif_count"):
        C.graph_motif_count(M, "square")


# --------------------------------------------------------------------------- #
# 3. reservoir                                                                 #
# --------------------------------------------------------------------------- #
def test_linear_reservoir_matches_a_hand_written_recursion():
    rng = np.random.default_rng(0)
    W = C.reservoir_from_graph(rng.random((3, 3)), rho=0.5)
    assert C.graph_spectral_radius(W) == pytest.approx(0.5)
    U = rng.random((10, 2))
    X = C.reservoir_states(W, U, in_scale=1.0, leak=1.0, nonlinearity="linear", seed=0)
    assert X.shape == (10, 3)
    W_in = np.random.default_rng(0).uniform(-1.0, 1.0, size=(3, 2))
    x = np.zeros(3)
    for t in range(10):
        x = W.T @ x + W_in @ U[t]
        assert np.allclose(x, X[t])
    assert C.reservoir_states(W, U, nonlinearity="linear", washout=4).shape == (6, 3)
    with pytest.raises(ValueError, match="reservoir_from_graph"):
        C.reservoir_from_graph(np.zeros((3, 3)))


def test_reservoir_encode_closed_forms_and_batch_shape():
    rng = np.random.default_rng(2)
    W = C.reservoir_from_graph(rng.random((4, 4)), rho=0.5)
    X = rng.random((7, 3))
    W_in = np.random.default_rng(0).uniform(-0.1, 0.1, size=(4, 3))
    one = C.reservoir_encode(W, X, steps=1, in_scale=0.1, leak=1.0, nonlinearity="linear", seed=0)
    assert one.shape == (7, 4) and np.allclose(one, X @ W_in.T)
    two = C.reservoir_encode(W, X, steps=2, in_scale=0.1, leak=1.0, nonlinearity="linear", seed=0)
    assert np.allclose(two, (X @ W_in.T) @ W + X @ W_in.T)
    # 一括版は 1 行ずつ reservoir_states を回した最終状態と同じ(tanh・leak < 1 でも)
    enc = C.reservoir_encode(W, X, steps=5, in_scale=0.1, leak=0.3, seed=0)
    for r in range(X.shape[0]):
        st = C.reservoir_states(W, np.tile(X[r], (5, 1)), in_scale=0.1, leak=0.3, seed=0)
        assert np.allclose(enc[r], st[-1])


def test_ridge_readout_recovers_an_affine_map():
    rng = np.random.default_rng(5)
    X = rng.random((50, 3))
    B = rng.random((3, 2))
    Y = X @ B + 1.0
    Wout = C.ridge_readout(X, Y, alpha=1e-8)
    assert Wout.shape == (4, 2)
    assert np.abs(C.ridge_predict(X, Wout) - Y).max() < 1e-6
    assert np.allclose(Wout[:3], B, atol=1e-6) and np.allclose(Wout[3], 1.0, atol=1e-6)
    with pytest.raises(ValueError, match="ridge_predict"):
        C.ridge_predict(X, Wout[:3])


# --------------------------------------------------------------------------- #
# 4. view                                                                      #
# --------------------------------------------------------------------------- #
def test_adjacency_image_is_a_unit_range_square():
    W = _random_graph()
    for order in C.ADJACENCY_ORDERS:
        img = C.graph_adjacency_image(W, order=order)
        assert img.shape == (30, 30) and img.min() >= 0.0 and img.max() == 1.0
        assert np.isfinite(img).all()
    assert np.array_equal(C.graph_adjacency_image(np.zeros((3, 3))), np.zeros((3, 3)))


def test_edges_as_lines_has_one_row_per_edge():
    W = _two_cliques(4)
    P = C.graph_layout_spectral(W)
    t = C.graph_edges_as_lines(W, P)
    assert t["weight"].shape == (24,) and t["x0"].shape == (24,)
    assert np.allclose(t["x0"], P[t["pre"], 0]) and np.allclose(t["z1"], P[t["post"], 2])
    assert C.graph_edges_as_lines(W, P[:, :2])["weight"].shape == (24,)


# --------------------------------------------------------------------------- #
# 5. fail-closed                                                               #
# --------------------------------------------------------------------------- #
def _first_arg_with_nan(name):
    """op の第 1 引数(グラフ / 表 / 行列)に NaN を 1 つ混ぜた入力。"""
    if name == "graph_from_synapses":
        a = np.array([[0, 1, 1.0], [1, 2, np.nan]])
    elif name in ("ridge_readout", "ridge_predict"):
        a = np.ones((5, 3))
        a[1, 1] = np.nan
    else:
        a = _complete(4)
        a[0, 1] = np.nan
    return a


@pytest.mark.parametrize("name", _OPS)
def test_every_op_refuses_nan_and_names_itself(name):
    fn = getattr(C, name)
    extra = {
        "graph_modularity": (np.zeros(4, dtype=int),),
        "graph_rich_club": (1,),
        "reservoir_states": (np.ones((3, 2)),),
        "reservoir_encode": (np.ones((3, 2)),),
        "ridge_readout": (np.ones((5, 2)),),
        "ridge_predict": (np.ones((4, 2)),),
        "graph_edges_as_lines": (np.zeros((4, 3)),),
        "graph_activity_spread": (np.zeros((4, 3)), np.array([1, 0, 0, 0])),
        "points_activity_video": (np.ones((3, 4)),),
    }.get(name, ())
    with pytest.raises(ValueError, match=name):
        fn(_first_arg_with_nan(name), *extra)


def test_non_square_and_wrong_labels_are_refused():
    with pytest.raises(ValueError, match="graph_betweenness"):
        C.graph_betweenness(np.zeros((3, 4)))
    with pytest.raises(ValueError, match="graph_modularity"):
        C.graph_modularity(_complete(4), np.zeros(3, dtype=int))
    with pytest.raises(TypeError, match="graph_components"):
        C.graph_components(np.ones((3, 3), dtype=bool))


# --------------------------------------------------------------------------- #
# 6. 台帳と公開経路                                                            #
# --------------------------------------------------------------------------- #
def test_the_ledger_lists_every_op_and_nothing_is_missing():
    import opsconngraph

    assert opsconngraph.missing() == []
    assert set(opsconngraph.OPSCONNGRAPH) == set(_OPS)
    assert len(opsconngraph.OPSCONNGRAPH) == 23
    for meta in opsconngraph.OPSCONNGRAPH.values():
        assert isinstance(meta["in"], list) and isinstance(meta["out"], str)


def test_every_op_is_reachable_from_the_public_tier():
    """``fullseye.ledger.<名前>`` から呼べること(登録面を 1 つ落とすと静かに消える)。"""
    import fullseye as fs
    import opsconngraph

    for name in opsconngraph.OPSCONNGRAPH:
        assert hasattr(fs.ledger, name), name


def test_the_typed_catalog_declares_the_family():
    import typed_catalog as tc

    rows = [r for r in tc.catalog() if r[1] == "conngraph"]
    assert {r[0] for r in rows} == set(_OPS)
    assert {r[3] for r in rows} == {"conn_graph", "table", "measurement", "signal", "labels",
                                    "matrix", "points", "image2d", "rgbvideo"}


def test_the_fuzzer_knows_the_new_types_and_can_seed_them():
    """新しい型に種と述語が無いと、その型を要る op は**永久に走らない**。"""
    sys.path.insert(0, str(ROOT / "tools"))
    import chain_fuzz as cf
    import opsconngraph

    gens = cf.make_generators()
    for sort in ("conn_graph", "synapse_table"):
        assert sort in cf.TYPE_CHECKS
        seed = gens[sort](np.random.default_rng(0))
        assert cf.TYPE_CHECKS[sort](seed), sort
    # 宣言 out 型はすべて述語を持ち、種のグラフに対する素の返りが宣言を通る
    W = gens["conn_graph"](np.random.default_rng(0))
    assert not cf.TYPE_CHECKS["conn_graph"](np.array([[0.0, np.nan], [0.0, 0.0]]))
    assert not cf.TYPE_CHECKS["synapse_table"](np.random.default_rng(0).random((5, 3)))
    for name, meta in opsconngraph.OPSCONNGRAPH.items():
        assert meta["out"] in cf.TYPE_CHECKS, name
        assert all(s in cf.TYPE_CHECKS for s in meta["in"]), name
    # 種のグラフは構造を持つ(2 成分ではなく橋でつながった 1 成分、Q > 0.4)
    assert int(C.graph_components(W).max()) == 0
    assert C.graph_modularity(W, np.arange(12) // 6) > 0.4


def test_op_run_works_through_the_default_seed_for_every_op():
    import fullseye as fs
    import opsconngraph

    two_input = {
        "graph_modularity", "reservoir_states", "reservoir_encode",
        "ridge_readout", "ridge_predict", "graph_edges_as_lines",
        "graph_activity_spread", "points_activity_video",
        "graph_activation_latency",              # matrix には既定の種が無い(明示で下に検査)
    }
    for name in opsconngraph.OPSCONNGRAPH:
        if name in two_input:
            continue
        out, notes = fs.op_run(name)                  # op_run は (result, notes)
        assert out is not None, name
        if isinstance(out, np.ndarray):
            assert np.isfinite(out).all(), name
    run = lambda *a, **k: fs.op_run(*a, **k)[0]     # noqa: E731
    W = run("graph_from_synapses")
    assert W.shape == (12, 12)
    labels = run("graph_components")
    assert run("graph_modularity", W, labels) == pytest.approx(0.0)      # 1 成分 → Q = 0
    assert run("graph_modularity", W, np.arange(12) // 6) > 0.4
    U = np.random.default_rng(0).random((8, 2))
    R = run("reservoir_from_graph")
    X = run("reservoir_states", R, U)
    assert X.shape == (8, 12)
    assert run("reservoir_encode", R, U).shape == (8, 12)
    Wout = run("ridge_readout", X, U)
    assert run("ridge_predict", X, Wout).shape == (8, 2)
    P = run("graph_layout_spectral")
    assert run("graph_edges_as_lines", W, P)["weight"].shape[0] == int((W != 0).sum())
    lat = run("graph_activation_latency", X)
    assert lat.shape == (12,) and lat.dtype.kind == "i"
    src = np.zeros(12, dtype=int); src[0] = 1
    assert set(run("graph_activity_spread", X, P, src)) == {"step", "mean_distance", "active_fraction", "source_fraction"}
    assert run("points_activity_video", P, X, size=32, aspect=1.0).shape == (8, 32, 32, 3)


def test_the_family_guide_exists_and_names_the_new_sorts():
    p = ROOT / "docs" / "ops" / "conngraph" / "guides" / "conngraph.md"
    assert p.exists()
    md = p.read_text(encoding="utf-8")
    assert "conn_graph" in md and "synapse_table" in md and "```mermaid" in md
    assert os.path.isdir(ROOT / "docs" / "ops" / "conngraph")


# --------------------------------------------------------------------------- #
# 7. activity —— 潜時・広がり・動画(2026-09-20、真値は有向の鎖)                    #
# --------------------------------------------------------------------------- #
def _chain_states(n_extra=1):
    """0 → 1 → 2 → 3 の鎖 + 孤立ノード n_extra 個。線形 reservoir に、ノード 0 だけへ t = 0 の
    パルスを W_in で入れると、活動は 1 ステップに 1 ノードずつ進む(真値 = 単位行列の帯)。"""
    n = 4 + n_extra
    W = np.zeros((n, n))
    for i in range(3):
        W[i, i + 1] = 1.0
    U = np.zeros((6, 1))
    U[0, 0] = 1.0
    w_in = np.zeros((n, 1))
    w_in[0, 0] = 1.0
    X = C.reservoir_states(W, U, leak=1.0, nonlinearity="linear", W_in=w_in)
    return W, X, n


def test_reservoir_states_takes_an_explicit_input_matrix():
    W, X, n = _chain_states()
    expect = np.zeros((6, n))
    for t in range(4):
        expect[t, t] = 1.0                       # t = 0: ノード 0、t = 1: ノード 1 …
    assert np.allclose(X, expect)
    # 既定(乱数の W_in)と、その乱数を明示的に渡したものは同じ
    U = np.random.default_rng(0).random((5, 2))
    R = C.reservoir_from_graph(_ring(6))
    a = C.reservoir_states(R, U, in_scale=0.3, seed=7)
    b = C.reservoir_states(R, U, W_in=C._input_weights(6, 2, 0.3, 7))
    assert np.allclose(a, b)
    with pytest.raises(ValueError, match="reservoir_states.*W_in"):
        C.reservoir_states(R, U, W_in=np.ones((6, 3)))


def test_activation_latency_counts_hops_and_marks_the_unreached():
    W, X, n = _chain_states(n_extra=2)
    assert np.array_equal(C.graph_activation_latency(X), [0, 1, 2, 3, -1, -1])
    assert np.array_equal(C.graph_activation_latency(np.zeros((3, 4))), [-1] * 4)
    # 尺度は 1 つ: 弱いノードは thresh 次第で「点かない」
    X2 = X.copy()
    X2[1, 1] = 0.05
    assert C.graph_activation_latency(X2, thresh=0.1)[1] == -1
    assert C.graph_activation_latency(X2, thresh=0.01)[1] == 1
    with pytest.raises(ValueError, match="graph_activation_latency.*thresh"):
        C.graph_activation_latency(X, thresh=0.0)


def test_activity_spread_measures_distance_from_the_source():
    W, X, n = _chain_states(n_extra=1)
    P = np.zeros((n, 3))
    P[:, 0] = np.arange(n) * 2.0                 # 鎖を x 軸に 2 刻みで置く
    src = np.array([1, 0, 0, 0, 0])
    t = C.graph_activity_spread(X, P, src)
    assert np.array_equal(t["step"], np.arange(6))
    assert np.allclose(t["mean_distance"], [0.0, 2.0, 4.0, 6.0, 0.0, 0.0])
    assert np.allclose(t["source_fraction"], [1.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    assert np.allclose(t["active_fraction"], [0.2, 0.2, 0.2, 0.2, 0.0, 0.0])
    with pytest.raises(ValueError, match="graph_activity_spread.*source"):
        C.graph_activity_spread(X, P, np.zeros(n, dtype=int))
    with pytest.raises(ValueError, match="graph_activity_spread.*P"):
        C.graph_activity_spread(X, P[:3], src)


def test_activity_video_shape_scale_and_placement():
    W, X, n = _chain_states(n_extra=0)
    P = np.zeros((n, 3))
    P[:, 0] = np.linspace(-1.0, 1.0, n)
    V = C.points_activity_video(P, X, size=64, aspect=1.0, substeps=2, yaw_span=0.0, pitch=0.0)
    assert V.shape == (12, 64, 64, 3) and V.dtype == np.float64
    assert 0.0 <= V.min() and V.max() <= 1.0
    # 尺度は全コマで 1 つ: 状態を 10 倍しても同じ絵
    assert np.allclose(V, C.points_activity_video(P, 10.0 * X, size=64, aspect=1.0, substeps=2, yaw_span=0.0, pitch=0.0))
    # yaw = pitch = 0 は +y を見る正射影: 画面の x は世界の x。点いたノードほど明るい
    lum = V[..., :].sum(axis=3)
    frame0 = lum[0]
    cols = frame0.max(axis=0)
    left, right = cols[:32].max(), cols[32:].max()
    assert left > right                          # t = 0 に点くのはノード 0(x = −1、画面左)
    frame6 = lum[6]                              # 時刻 3: ノード 3(x = +1、画面右)
    assert frame6[:, 32:].max() > frame6[:, :32].max()
    # 背景の点は薄い灰で敷かれ、画角に入る
    Vb = C.points_activity_video(P, X, size=64, aspect=1.0, yaw_span=0.0, pitch=0.0, background=np.array([[0.0, 0.0, 3.0]]))
    assert Vb.shape == (6, 64, 64, 3)
    # 色は (n, 3) の [0,1]
    cols_rgb = np.tile([[1.0, 0.0, 0.0]], (n, 1))
    Vc = C.points_activity_video(P, X, colors=cols_rgb, size=64, aspect=1.0, yaw_span=0.0, pitch=0.0)
    assert Vc[0, ..., 0].max() > Vc[0, ..., 1].max()
    for bad in (dict(size=4), dict(substeps=0), dict(gain=0.0), dict(aspect=0.0), dict(point_px=0),
                dict(colors=np.ones((n, 2))), dict(colors=2.0 * np.ones((n, 3)))):
        with pytest.raises(ValueError, match="points_activity_video"):
            C.points_activity_video(P, X, **bad)
    with pytest.raises(ValueError, match="points_activity_video.*cap"):
        C.points_activity_video(P, X, size=4096, aspect=1.0, substeps=200)


def test_spectral_radius_sparse_path_matches_dense():
    """n > 400 は ARPACK の経路(2026-09-20、PoC が CI の枠を超えた)。密の eigvals と同じ値を返すこと。"""
    rng = np.random.default_rng(3)
    n = 600
    W = (rng.random((n, n)) < 0.02) * rng.integers(1, 9, (n, n)).astype(np.float64)
    np.fill_diagonal(W, 0.0)
    dense = float(np.max(np.abs(np.linalg.eigvals(W))))
    assert C.graph_spectral_radius(W) == pytest.approx(dense, rel=1e-8)
    R = C.reservoir_from_graph(W, rho=0.9)
    assert float(np.max(np.abs(np.linalg.eigvals(R)))) == pytest.approx(0.9, rel=1e-8)
    # 小さいグラフは密のまま(閉形式の真値: 完全グラフ n−1)
    assert C.graph_spectral_radius(_complete(5)) == pytest.approx(4.0)
    # 符号つきの乱数行列(固有値が円状)は ARPACK が最大絶対値に届かない → 密の経路(実測で起きた誤り)
    G = rng.standard_normal((n, n)) * (rng.random((n, n)) < 0.02)
    dense_g = float(np.max(np.abs(np.linalg.eigvals(G))))
    assert C.graph_spectral_radius(G) == pytest.approx(dense_g, rel=1e-8)
    assert float(np.max(np.abs(np.linalg.eigvals(C.reservoir_from_graph(G, rho=0.9))))) == pytest.approx(0.9, rel=1e-8)
    # 非負でも 2 成分(可約)・周期的(2 部)な構造で密と一致すること
    B = np.zeros((n, n)); half = n // 2
    B[:half, :half] = W[:half, :half]; B[half:, half:] = 3.0 * W[half:, half:]
    assert C.graph_spectral_radius(B) == pytest.approx(float(np.max(np.abs(np.linalg.eigvals(B)))), rel=1e-8)
    Bp = np.zeros((n, n)); Bp[:half, half:] = W[:half, half:]; Bp[half:, :half] = W[half:, :half]
    assert C.graph_spectral_radius(Bp) == pytest.approx(float(np.max(np.abs(np.linalg.eigvals(Bp)))), rel=1e-8)
