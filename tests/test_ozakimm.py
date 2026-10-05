# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ozakimm の門(順序に依らない FP64 の行列積、Ozaki-I / Ozaki-II)。

 1. 階段: 分割数を増やすと誤差が段で落ち、DGEMM の水準に届く(正確な真値 = Python の整数、φ = 0.5 / 2 / 4)
 2. 上界: |誤差| ≤ 打ち切りの上界 + (s+1) u |A||B| がすべての要素で成り立つ(破れ 0)
 3. 順序: 内側の添字を並べ替えてもビット単位で同じ(Ozaki-I / II、自動選択も)
 4. スレッド: BLAS 1 スレッドと 8 スレッドでビット単位で同じ
 5. 定数倍: 2 の冪を掛けると答えも正確に同じ倍率(arXiv 2606.29129 の fast mode の欠陥が無い)、2 の冪でない定数倍でも精度が落ちない
 6. 内部のブロック幅・切れ端を積む経路に依らない(積み方を変えても同じビット)
 7. fail-closed: NaN・形・個数・届かない tol・綴り違いは ValueError、fallback は報告される
 8. Kabsch: 点の順に依らない R・t・H、回転の復元
 9. 探針: GPU / CUDA が無くても例外を出さず表を返す
10. 入口: __all__ が実在、docstring に Markdown のリンク記法なし
"""
from __future__ import annotations

import numpy as np
import pytest
from threadpoolctl import threadpool_limits

import ozakimm as om

rng = np.random.default_rng(11)


@pytest.mark.parametrize("phi", [0.5, 2.0, 4.0])
def test_staircase_reaches_fp64(phi):
    A = om._test_matrix(24, 200, phi, rng)
    B = om._test_matrix(200, 24, phi, rng)
    R = om._exact_matmul(A, B)
    den = np.abs(A) @ np.abs(B)
    e = [np.max(np.abs(om.matmul_ozaki(A, B, s) - R) / den) for s in range(1, 14)]
    assert len(e) == 13
    bad = [(i + 1, a, b) for i, (a, b) in enumerate(zip(e, e[1:])) if b > a * 1.01 + 2.0 ** -52]
    assert not bad, bad                      # 単調(FP64 の床の丸めの揺れを除く)
    assert e[0] > 1e-3                       # 1 枚では粗い(階段の上端が本当に高い)
    assert e[-1] <= max(np.max(np.abs(A @ B - R) / den), 2.0 ** -52)
    C, info = om.matmul_ozaki(A, B, return_info=True)
    assert np.max(np.abs(C - R) / den) <= 2 * 2.0 ** -52
    assert 1 <= info["n_slices"] <= 16 and not info["fallback"]


def test_bound_holds_everywhere():
    A = om._test_matrix(20, 300, 2.0, rng)
    B = om._test_matrix(300, 20, 2.0, rng)
    R = om._exact_matmul(A, B)
    den = np.abs(A) @ np.abs(B)
    n_checked = 0
    for s in range(1, 13):
        lim = om.ozaki_error_bound(A, B, s) + (s + 1) * 2.0 ** -53 * den
        err = np.abs(om.matmul_ozaki(A, B, s) - R)
        assert np.all(err <= lim), (s, np.max(err / lim))
        n_checked += err.size
    assert n_checked == 12 * 400


@pytest.mark.parametrize("scheme,s", [("ozaki1", 10), ("ozaki2", 18), ("ozaki1", None)])
def test_order_invariance(scheme, s):
    A = om._test_matrix(5, 5000, 2.0, rng)
    B = om._test_matrix(5000, 5, 2.0, rng)
    base = om.matmul_ozaki(A, B, s, scheme)
    for seed in range(3):
        p = np.random.default_rng(seed).permutation(5000)
        assert np.array_equal(base, om.matmul_ozaki(A[:, p], B[p], s, scheme))


def test_thread_invariance():
    A = om._test_matrix(64, 2048, 1.0, rng)
    B = om._test_matrix(2048, 64, 1.0, rng)
    with threadpool_limits(1):
        c1 = om.matmul_reproducible(A, B)
    with threadpool_limits(8):
        c8 = om.matmul_reproducible(A, B)
    assert np.array_equal(c1, c8)


@pytest.mark.parametrize("k", [-20, -5, -2, 7])
def test_power_of_two_scale_is_exact(k):
    # arXiv 2606.29129: 全要素 1 の行列で c ≤ 2⁻² のとき、旧 fast mode は相対誤差 約 1(CRT の復元が壊れる)
    A = np.ones((16, 1024))
    B = np.ones((1024, 16))
    for f in (lambda a, b: om.matmul_ozaki(a, b, 16, "ozaki2"), lambda a, b: om.matmul_ozaki(a, b, 8)):
        assert np.array_equal(f(np.ldexp(A, k), B), np.ldexp(f(A, B), k))
        assert np.all(f(np.ldexp(A, k), B) == np.ldexp(1024.0, k))


@pytest.mark.parametrize("c", [2.0 ** -3, 2.0 ** -5, 2.0 ** -10, 3.7, 1e-6])
def test_scaled_random_input_keeps_accuracy(c):
    # 同じ論文の Fig 2: φ = 0.5、k = 1024 で c ≤ 2⁻³ から誤差 約 1。ここでは定数倍の前後で精度が同じ水準
    A = om._test_matrix(8, 1024, 0.5, rng)
    B = om._test_matrix(1024, 8, 0.5, rng)
    R = om._exact_matmul(c * A, B)
    den = np.abs(c * A) @ np.abs(B)
    for C in (om.matmul_ozaki(c * A, B, 18, "ozaki2"), om.matmul_reproducible(c * A, B)):
        assert np.max(np.abs(C - R) / den) < 4 * 2.0 ** -52


def test_independent_of_block_width_and_stacking(monkeypatch):
    A = om._test_matrix(3, 4000, 1.0, rng)
    B = om._test_matrix(4000, 3, 1.0, rng)
    base = om.matmul_ozaki(A, B, 9)
    monkeypatch.setattr(om, "_STACK_LIMIT", 0)          # 組ごとに掛ける経路
    assert np.array_equal(base, om.matmul_ozaki(A, B, 9))
    monkeypatch.setattr(om, "_KB", 333)                 # ブロック幅を変える
    assert np.array_equal(base, om.matmul_ozaki(A, B, 9))
    # 出力の行を分けても、枚数を固定すれば同じビット(行ごとの指数しか使わない)
    assert np.array_equal(base[:2], om.matmul_ozaki(A[:2], B, 9))


def test_fail_closed():
    A = np.ones((3, 4))
    B = np.ones((4, 2))
    bads = (lambda: om.matmul_ozaki(np.full((3, 4), np.nan), B),
            lambda: om.matmul_ozaki(A, A),
            lambda: om.matmul_ozaki(np.ones(4), B),
            lambda: om.matmul_ozaki(A, B, 0),
            lambda: om.matmul_ozaki(A, B, True),
            lambda: om.matmul_ozaki(A, B, 2.0),
            lambda: om.matmul_ozaki(A, B, 1, "ozaki2"),
            lambda: om.matmul_ozaki(A, B, 3, "ozaki3"),
            lambda: om.matmul_ozaki(A, B, None, "ozaki2"),
            lambda: om.matmul_ozaki(A, B, on_insufficient="ignore"),
            lambda: om.matmul_ozaki(A, B, tol=0.0),
            lambda: om.ozaki_error_bound(A, B, 0),
            lambda: om.matmul_reproducible(np.array([[1.0, 1e-100]]), np.array([[0.0], [1e-100]])),
            lambda: om.matmul_reproducible(np.full((2, 2), 1e300), np.full((2, 2), 1e300)),
            lambda: om.kabsch_reproducible(A, A),
            lambda: om.cross_covariance_reproducible(np.ones((5, 3)), np.ones((4, 3))))
    assert len(bads) == 16
    for bad in bads:
        with pytest.raises(ValueError):
            bad()
    # 届かないときに float64 へ戻すのは明示したときだけで、戻したことが報告される
    # (|A||B|) = 1e-200 なのに行・列の尺度は 1e-100: FP64 並みには 40 枚余りが要る
    C, info = om.matmul_ozaki(np.array([[1.0, 1e-100]]), np.array([[0.0], [1e-100]]), on_insufficient="fallback",
                              return_info=True)
    assert info["fallback"] is True and info["n_slices"] is None and C[0, 0] == 1e-200


def test_kabsch_order_invariant_and_recovers_rotation():
    P = 1000.0 + rng.normal(0, 0.5, (20000, 3))
    Rt = np.linalg.qr(rng.normal(size=(3, 3)))[0]
    if np.linalg.det(Rt) < 0:
        Rt[:, 0] *= -1
    Q = P @ Rt.T + np.array([0.1, -2.0, 3.0])
    r0 = om.kabsch_reproducible(P, Q)
    p = rng.permutation(len(P))
    r1 = om.kabsch_reproducible(P[p], Q[p])
    for key in ("R", "t", "H"):
        assert np.array_equal(r0[key], r1[key]), key
    assert np.max(np.abs(r0["R"] - Rt)) < 1e-12
    H = om.cross_covariance_reproducible(P, Q)
    assert np.array_equal(H, r0["H"])
    Hd = (P - P.mean(0)).T @ (Q - Q.mean(0))
    assert np.max(np.abs(H - Hd)) <= 1e-12 * np.max(np.abs(Hd))


def test_probe_never_raises():
    out = om.fp64_emulation_probe()
    assert set(out) >= {"available", "rows", "how", "note"}
    assert isinstance(out["available"], bool)
    rows = out["rows"]
    assert len(rows) >= 1
    for row in rows:
        assert set(row) >= {"library", "path", "loaded", "cublas_version", "emulation_api", "gpu", "reason"}
    if out["available"]:
        assert any(r["gpu"] and r["emulation_api"] for r in rows)


def test_entry_points_are_documented():
    assert len(om.__all__) == 6
    for name in om.__all__:
        fn = getattr(om, name)
        assert fn.__doc__ and len(fn.__doc__) > 80, name
        assert "](" not in fn.__doc__, name
    assert "](" not in om.__doc__
