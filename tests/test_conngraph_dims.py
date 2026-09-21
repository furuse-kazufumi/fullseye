# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""conngraph の「層を通す・次元を数える」4 op(2026-09-21、動きの量子化 PoC)の門: 閉形式の真値で固定する。"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import conngraph as C  # noqa: E402

SIZES = (40, 20, 10, 5)


def layered(seed=0, density=0.3):
    """層状の乱数配線(前向きのブロックだけ、層内と層をまたぐ結線は 0)。"""
    rng = np.random.default_rng(seed)
    lab = np.repeat(np.arange(len(SIZES)), SIZES)
    n = len(lab)
    W = np.zeros((n, n))
    for a in range(len(SIZES) - 1):
        src = np.nonzero(lab == a)[0]
        dst = np.nonzero(lab == a + 1)[0]
        blk = rng.random((len(src), len(dst))) * (rng.random((len(src), len(dst))) < density)
        W[np.ix_(src, dst)] = blk
    return W, lab


def test_participation_ratio_has_closed_form_values():
    rng = np.random.default_rng(0)
    X = rng.standard_normal((4000, 6))
    assert abs(C.states_participation_ratio(X) - 6.0) < 0.15                  # 独立で等分散 → n
    v = rng.standard_normal((200, 1))
    assert abs(C.states_participation_ratio(v @ rng.standard_normal((1, 9))) - 1.0) < 1e-9   # 階数 1 → 1
    assert C.states_participation_ratio(np.ones((10, 4))) == 0.0                # 定数 → 0
    # 分散 3 : 1 の 2 方向 → (3+1)² / (9+1) = 1.6
    Y = np.column_stack([np.sqrt(3.0) * rng.standard_normal(20000), rng.standard_normal(20000)])
    assert abs(C.states_participation_ratio(Y) - 1.6) < 0.05
    # N < n でも同じ(Gram 行列で計算)
    Z = rng.standard_normal((5, 50))
    assert abs(C.states_participation_ratio(Z) - C.states_participation_ratio(np.pad(Z, ((0, 0), (0, 0))))) < 1e-9
    with pytest.raises(ValueError, match="X must be"):
        C.states_participation_ratio(np.zeros((0, 3)))


def test_layer_propagate_only_moves_forward_and_kwta_fires_the_top_fraction():
    W, lab = layered()
    rng = np.random.default_rng(1)
    U = rng.random((30, SIZES[0]))
    for act in C.ACTIVATIONS:
        X = C.graph_layer_propagate(W, lab, U, activation=act, active_frac=0.2)
        assert X.shape == (30, sum(SIZES))
        assert np.array_equal(X[:, lab == 0], U)                              # 層 0 は入力そのもの
        assert np.isfinite(X).all()
    Xk = C.graph_layer_propagate(W, lab, U, activation="kwta", active_frac=0.2)
    for a in (1, 2, 3):
        frac = (Xk[:, lab == a] > 0).mean(axis=1)
        assert np.all(np.abs(frac - 0.2) <= 1.0 / SIZES[a] + 1e-9), (a, frac)  # 上位 20 % だけ発火
        assert abs(Xk[:, lab == a].mean() - 1.0) < 1e-9                          # 平均 1 に正規化
    # 線形: 受け手ごとに入力和 1 で正規化した重みつき平均 → 閉形式
    Xl = C.graph_layer_propagate(W, lab, U, activation="linear")
    B = W[lab == 0][:, lab == 1]
    ref = U @ (B / B.sum(axis=0)[None, :])
    ref = ref / np.abs(ref).mean()
    assert np.allclose(Xl[:, lab == 1], ref)
    with pytest.raises(ValueError, match="activation must be"):
        C.graph_layer_propagate(W, lab, U, activation="relu")
    with pytest.raises(ValueError, match="one column per layer-0 node"):
        C.graph_layer_propagate(W, lab, U[:, :10])
    with pytest.raises(ValueError, match="consecutive"):
        C.graph_layer_propagate(W, np.where(lab == 2, 5, lab), U)
    with pytest.raises(ValueError, match="active_frac"):
        C.graph_layer_propagate(W, lab, U, active_frac=0.0)


def test_block_shuffle_keeps_every_receiver_weight_multiset_and_block_totals():
    W, lab = layered()
    Ws = C.graph_block_shuffle(W, lab, seed=3)
    assert Ws.shape == W.shape and not np.array_equal(Ws, W)
    for a in range(4):
        for c in range(4):
            blk, blk_s = W[np.ix_(lab == a, lab == c)], Ws[np.ix_(lab == a, lab == c)]
            assert np.allclose(np.sort(blk, axis=0), np.sort(blk_s, axis=0))     # 受け手ごとの重みの多重集合
            assert abs(blk.sum() - blk_s.sum()) < 1e-9
    assert np.array_equal(C.graph_block_shuffle(W, lab, seed=3), Ws)             # 再現
    with pytest.raises(ValueError, match="labels must be one integer per node"):
        C.graph_block_shuffle(W, lab[:-1])


def test_layer_dimension_reads_the_funnel_and_rank_one_layers():
    W, lab = layered()
    rng = np.random.default_rng(2)
    U = rng.random((300, SIZES[0]))
    X = C.graph_layer_propagate(W, lab, U, activation="linear")
    t = C.states_layer_dimension(X, lab)
    assert set(t) == {"layer", "n", "participation_ratio", "ratio"}
    assert t["n"].tolist() == list(SIZES)
    assert t["participation_ratio"][0] > t["participation_ratio"][1] > t["participation_ratio"][3] > 0
    assert np.allclose(t["ratio"], t["participation_ratio"] / t["n"])
    # 全結線が同じ(すべての受け手が同じ入力)なら層 1 以降は階数 1
    W1 = np.zeros_like(W)
    for a in range(3):
        W1[np.ix_(lab == a, lab == a + 1)] = 1.0
    t1 = C.states_layer_dimension(C.graph_layer_propagate(W1, lab, U, activation="linear"), lab)
    assert np.allclose(t1["participation_ratio"][1:], 1.0)


def test_the_ledger_and_public_tier_carry_the_dimension_ops():
    import fullseye as fs
    import opsconngraph

    names = ["graph_block_shuffle", "graph_layer_propagate", "states_participation_ratio", "states_layer_dimension"]
    assert set(opsconngraph.list_ops("dimension")) == set(names)
    for nme in names:
        assert hasattr(fs.ledger, nme), nme
    W, lab = layered()
    U = np.random.default_rng(0).random((12, SIZES[0]))
    run = lambda *a, **k: fs.op_run(*a, **k)[0]     # noqa: E731
    X = run("graph_layer_propagate", W, lab, U)
    assert X.shape == (12, sum(SIZES))
    assert run("graph_block_shuffle", W, lab).shape == W.shape
    assert 0.0 < run("states_participation_ratio", X) <= sum(SIZES)
    assert run("states_layer_dimension", X, lab)["n"].tolist() == list(SIZES)
