# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""driveinf(終わらない地図)の門: 決定的な区画・継ぎ目の連続・桁の落ちない座標・持つ区画の上限。"""
from __future__ import annotations

import numpy as np
import pytest

import driveinf as DI

TP = DI.tile_params()
T = TP["tile"]


def test_tile_hash_is_deterministic_and_order_free():
    """同じ入力は同じ値(環境に依らない整数だけの計算)、負の番号も扱い、[0, 1) の一様に写る。"""
    a = DI.tile_hash(3, -4, 7, 1)
    assert a == DI.tile_hash(3, -4, 7, 1) and 0 <= a < 2 ** 64
    assert a != DI.tile_hash(-4, 3, 7, 1) and a != DI.tile_hash(3, -4, 8, 1) and a != DI.tile_hash(3, -4, 7, 2)
    u = np.array([DI.tile_uniform(i, 0, 1) for i in range(2000)])
    assert u.min() >= 0.0 and u.max() < 1.0 and abs(u.mean() - 0.5) < 0.03


def test_pose_normalize_carries_across_tiles():
    assert DI.pose_normalize(5, 2, 205.0, -3.0, 200.0) == (6, 1, 5.0, 197.0)
    assert DI.pose_normalize(0, 0, 0.0, 199.999, 200.0) == (0, 0, 0.0, 199.999)
    with pytest.raises(ValueError):
        DI.pose_normalize(0, 0, 1.0, 1.0, 0.0)


@pytest.mark.parametrize("ij", [(0, 0), (-7, 3), (123456, -654321)])
def test_edges_agree_from_both_sides(ij):
    """区画 (i, j) の E と (i+1, j) の W、N と (i, j+1) の S は同じ辺: 横切る位置がビット一致(無いなら両方 None)。"""
    i, j = ij
    assert DI.tile_edge_crossing(i, j, "E", TP) == DI.tile_edge_crossing(i + 1, j, "W", TP)
    assert DI.tile_edge_crossing(i, j, "N", TP) == DI.tile_edge_crossing(i, j + 1, "S", TP)
    with pytest.raises(ValueError):
        DI.tile_edge_crossing(i, j, "X", TP)


@pytest.mark.parametrize("ij", [(0, 0), (5000, 2), (-999999, 888888)])
def test_height_is_continuous_across_seams(ij):
    """境目で両側の区画の高さが 1e-12 m で一致(整数格子 + 区画の中の小数 —— 遠くでも桁が落ちない)。"""
    i, j = ij
    ys = np.linspace(0.0, T, 41)
    assert np.abs(DI.tile_height(i, j, np.full_like(ys, T), ys, TP) - DI.tile_height(i + 1, j, np.zeros_like(ys), ys, TP)).max() < 1e-12
    assert np.abs(DI.tile_height(i, j, ys, np.full_like(ys, T), TP) - DI.tile_height(i, j + 1, ys, np.zeros_like(ys), TP)).max() < 1e-12


def test_roads_are_flat_and_reach_the_edges():
    """道の中心線の上は高さ 0(平らにした範囲)、線分の端は区画の辺か分岐点。"""
    for i, j in ((0, 0), (3, 4), (5001, -2)):
        rd = DI.tile_roads(i, j, TP)
        assert len(rd["ends"]) >= 1                                          # 空だと下の表明が無条件に通る
        assert len(rd["segments"]) == len(rd["ends"])
        for side, (x, y) in rd["ends"]:
            assert (side in "EW" and x in (0.0, T)) or (side in "NS" and y in (0.0, T))
        for s in rd["segments"]:
            pts = s[0] + np.linspace(0, 1, 9)[:, None] * (s[1] - s[0])
            assert np.abs(DI.tile_height(i, j, pts[:, 0], pts[:, 1], TP)).max() < 1e-12
            assert DI.tile_road_distance(i, j, pts[:, 0], pts[:, 1], TP).max() < 1e-9


def test_regeneration_is_bit_identical_and_order_free():
    """同じ区画を作り直すと指紋(SHA-256)が一致し、作る順番に依らない。"""
    keys = [(a, b) for a in range(-1, 2) for b in range(-1, 2)]
    d1 = {k: DI.tile_digest(DI.tile_mesh(k[0], k[1], TP)) for k in keys}
    d2 = {k: DI.tile_digest(DI.tile_mesh(k[0], k[1], TP)) for k in reversed(keys)}
    assert d1 == d2 and len(set(d1.values())) == len(keys)


def test_tile_stream_holds_a_bounded_window():
    """車の周り (2r+1)² だけを持ち、区画をまたぐと進む側を作り反対側を捨てる。"""
    cache = {}
    r0 = DI.tile_stream(cache, 0, 0, TP, radius=1)
    assert r0["n"] == 9 and len(r0["loaded"]) == 9 and not r0["evicted"]
    r1 = DI.tile_stream(cache, 1, 0, TP, radius=1)
    assert r1["n"] == 9 and sorted(r1["loaded"]) == [(2, -1), (2, 0), (2, 1)] and sorted(r1["evicted"]) == [(-1, -1), (-1, 0), (-1, 1)]


def test_mesh_and_params_reject_bad_input():
    with pytest.raises(ValueError):
        DI.tile_params(tile=0.0)
    with pytest.raises(ValueError):
        DI.tile_params(p_road=1.5)
    with pytest.raises(ValueError):
        DI.tile_mesh(0, 0, TP, step=7.0)                               # 200 m を割り切らない
