# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ICP の家族の ``reproducible=True``(縮約を ozakimm の順序に依らない積にする)の門。

対象(同じ縮約 = 点の数 N の和で 3×3 の H や 6×6 の JᵀJ を作る反復の ICP、2026-10-05 に repo を grep して 5 本):
registration.icp / registration.point_to_plane_icp / match3d.icp_point2point_3d / match3d.icp_point2plane / gicp.gicp。

1. source の点の順を入れ替えても、BLAS のスレッド数を 1 / 4 に変えても、R・t・rmse がビット単位で同じ
2. 既定の経路(reproducible=False)との差は FP64 の丸めの範囲(R は 1e-12、t は座標の尺度 × 1e-12)
3. 真の姿勢を復元する(既定と同じ水準)
4. 既定の引数は reproducible=False のまま(既定の挙動を変えない)

Linux の CI(OpenBLAS)でも同じ門が走る(GPU も特別な依存も要らない)。
"""
from __future__ import annotations

import inspect

import numpy as np
import pytest
from threadpoolctl import threadpool_limits

import gicp
import match3d
import pointcloud
import registration


def _cloud(n=3000, seed=4):
    rng = np.random.default_rng(seed)
    u, v = rng.uniform(-1, 1, (2, n))
    Q = np.stack([u, v, 0.2 * np.sin(3 * u) * np.cos(2 * v)], 1) + 50.0     # 原点から遠い面
    th = 0.08
    R = np.array([[np.cos(th), -np.sin(th), 0], [np.sin(th), np.cos(th), 0], [0, 0, 1.0]])
    t = np.array([0.03, -0.02, 0.01])
    P = (Q - 50.0) @ R.T + 50.0 + t + 1e-5 * rng.normal(size=(n, 3))
    return P, Q, R


P, Q, R_TRUE = _cloud()
NQ = pointcloud.estimate_normals(Q, k=16)

RUNS = {
    "registration.icp": lambda P_, **k: (lambda r: (r[0], r[1], r[3]))(registration.icp(P_, Q, **k)),
    "registration.point_to_plane_icp": lambda P_, **k: (lambda r: (r[0], r[1], r[3]))(
        registration.point_to_plane_icp(P_, Q, NQ, **k)),
    "match3d.icp_point2point_3d": lambda P_, **k: (lambda r: (np.asarray(r[0]), np.asarray(r[1]), r[2]["rmse"]))(
        match3d.icp_point2point_3d(P_, Q, **k)),
    "match3d.icp_point2plane": lambda P_, **k: (lambda r: (r[0], r[1], r[3]))(match3d.icp_point2plane(P_, Q, NQ, **k)),
    "gicp.gicp": lambda P_, **k: (lambda r: (r["R"], r["t"], r["rmse"]))(gicp.gicp(P_, Q, **k)),
}
FUNCS = {"registration.icp": registration.icp, "registration.point_to_plane_icp": registration.point_to_plane_icp,
         "match3d.icp_point2point_3d": match3d.icp_point2point_3d, "match3d.icp_point2plane": match3d.icp_point2plane,
         "gicp.gicp": gicp.gicp}


def _same(a, b):
    return all(np.array_equal(np.asarray(x), np.asarray(y)) for x, y in zip(a, b))


def test_the_family_is_counted():
    assert len(RUNS) == 5 and set(RUNS) == set(FUNCS)


@pytest.mark.parametrize("name", sorted(RUNS))
def test_reproducible_is_bitwise_independent_of_point_order_and_threads(name):
    fn = RUNS[name]
    base = fn(P, reproducible=True)
    others = []
    for seed in (1, 2):
        p = np.random.default_rng(seed).permutation(len(P))
        others.append(fn(P[p], reproducible=True))
    others.append(fn(P[::-1], reproducible=True))
    for n in (1, 4):
        with threadpool_limits(n):
            others.append(fn(P, reproducible=True))
    assert len(others) == 5
    for r in others:
        assert _same(base, r), name


@pytest.mark.parametrize("name", sorted(RUNS))
def test_reproducible_differs_from_the_default_only_by_rounding(name):
    fn = RUNS[name]
    a = fn(P)
    b = fn(P, reproducible=True)
    assert np.max(np.abs(np.asarray(a[0]) - np.asarray(b[0]))) < 1e-12
    assert np.max(np.abs(np.asarray(a[1]) - np.asarray(b[1]))) < 50.0 * 1e-12
    assert abs(a[2] - b[2]) <= 1e-9 * max(a[2], 1e-12) + 1e-15
    assert np.max(np.abs(np.asarray(b[0]) - R_TRUE.T)) < 1e-4      # P = R_TRUE (Q - c) + ... なので P → Q は R_TRUE.T


@pytest.mark.parametrize("name", sorted(FUNCS))
def test_the_default_stays_off(name):
    assert inspect.signature(FUNCS[name]).parameters["reproducible"].default is False


def test_kabsch_reproducible_needs_three_points_and_matches_the_default():
    with pytest.raises(ValueError):
        registration.kabsch(P[:2], Q[:2], reproducible=True)
    R0, t0 = registration.kabsch(P, Q)
    R1, t1 = registration.kabsch(P, Q, reproducible=True)
    assert np.max(np.abs(R0 - R1)) < 1e-12 and np.max(np.abs(t0 - t1)) < 1e-10
    p = np.random.default_rng(9).permutation(len(P))
    R2, t2 = registration.kabsch(P[p], Q[p], reproducible=True)
    assert np.array_equal(R1, R2) and np.array_equal(t1, t2)
