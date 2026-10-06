# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""2026-10-07 レビューで再現した数学 op の欠陥 5 件の回帰テスト。

真値はどれも op と別の経路から取る: 円膜の固有値は ``scipy.special.jnp_zeros`` を
全次数で総当たりした列、重心補間は ``scipy.interpolate.BarycentricInterpolator``、
IFS の次元は閉形式 ``log N / log(1/r)``、点評価と格子評価は ndarray 版との一致。
"""
import numpy as np
import pytest

import mathnumerics as N
import mathops

scipy_special = pytest.importorskip("scipy.special")
scipy_interp = pytest.importorskip("scipy.interpolate")


# --- 1. wave_mode_frequencies("circular") が m >= 3 の低い固有値を落としていた ----------------
def _circular_truth(count):
    vals = sorted(float(z) ** 2 for m in range(40) for z in scipy_special.jnp_zeros(m, count))
    return np.asarray(vals[:count])


def test_circular_frequencies_include_every_order():
    got = np.asarray(mathops.wave_mode_frequencies("circular", 5))
    assert np.allclose(got, [3.39, 9.328, 14.682, 17.65, 28.276], atol=1e-3)
    for c in (1, 5, 12, 30):
        got = np.asarray(mathops.wave_mode_frequencies("circular", c))
        truth = _circular_truth(c)
        assert got.shape == truth.shape == (c,)
        assert np.allclose(got, truth, rtol=1e-10)


def test_rectangular_frequencies_unchanged():
    lam = np.asarray(mathops.wave_mode_frequencies("rectangular", 7, 1.0)) / np.pi ** 2
    assert np.allclose(lam, [2, 5, 5, 8, 10, 10, 13])


# --- 2. ifs_similarity_dimension が縮小しない写像で上端 8.0 に張り付いていた -------------------
def test_ifs_rejects_non_contracting_maps():
    with pytest.raises(ValueError, match="contraction ratio"):
        mathops.ifs_similarity_dimension(maps=[(1.2, 0, 0, 1.2, 0, 0), (1.2, 0, 0, 1.2, 0.5, 0)])
    with pytest.raises(ValueError, match="contraction ratio"):
        mathops.ifs_similarity_dimension(maps=[(1, 0, 0, 1, 0, 0)])


def test_ifs_dimension_closed_form_and_beyond_old_bracket():
    d = mathops.ifs_similarity_dimension(maps=[(0.5, 0, 0, 0.5, 0, 0)] * 3)
    assert abs(d - np.log(3) / np.log(2)) < 1e-10
    # 解が 8 を超える場合(以前の上端 8.0)も閉形式に一致する: 2**10 枚の r=1/2 で d=10
    d = mathops.ifs_similarity_dimension(maps=[(0.5, 0, 0, 0.5, 0, 0)] * 1024)
    assert abs(d - 10.0) < 1e-9


# --- 3. wave_membrane_mode: Dirichlet の m=0 が全ゼロ / aspect != 1 で境界条件違反 -------------
def test_dirichlet_zero_index_rejected():
    for m, n in ((0, 2), (2, 0)):
        with pytest.raises(ValueError, match="Dirichlet"):
            mathops.wave_membrane_mode("rectangular", m, n, (32, 32), 1.0, free_edge=False)


def test_dirichlet_boundary_holds_for_any_aspect():
    asp = (0.6, 1.0, 1.7, 3.0)
    for a in asp:
        u = np.asarray(mathops.wave_membrane_mode("rectangular", 2, 3, (41, 61), a,
                                                  free_edge=False))
        edge = max(np.abs(u[0]).max(), np.abs(u[-1]).max(),
                   np.abs(u[:, 0]).max(), np.abs(u[:, -1]).max())
        assert edge < 1e-12, (a, edge)
        assert np.abs(u).max() == pytest.approx(1.0)
    assert len(asp) == 4


def test_free_edge_combined_mode_rejects_non_square():
    with pytest.raises(ValueError, match="aspect=1"):
        mathops.wave_membrane_mode("rectangular", 2, 3, (32, 32), 1.7)
    u = np.asarray(mathops.wave_membrane_mode("rectangular", 2, 3, (33, 33), 1.0))
    assert np.abs(u).max() == pytest.approx(1.0)


# --- 4. interp_barycentric: 重みの直接積が underflow して全点 NaN ----------------------------
def _runge(t):
    return 1.0 / (1.0 + 25.0 * t * t)


def test_barycentric_chebyshev_1200_matches_scipy():
    xk = N.chebyshev_nodes(1200, -1.0, 1.0)
    xq = np.linspace(-0.99, 0.99, 37)
    got = N.interp_barycentric(xk, _runge(xk), xq)
    ref = scipy_interp.BarycentricInterpolator(xk, _runge(xk))(xq)
    assert got.shape == ref.shape == (37,)
    assert np.all(np.isfinite(got))
    assert np.abs(got - ref).max() < 1e-10
    assert np.abs(got - _runge(xq)).max() < 1e-10


def test_barycentric_tiny_interval_matches_scipy():
    xk = np.linspace(0.0, 1e-4, 100)
    yk = np.sin(1e4 * xk)
    xq = np.linspace(1e-6, 9.9e-5, 23)
    got = N.interp_barycentric(xk, yk, xq)
    ref = scipy_interp.BarycentricInterpolator(xk, yk)(xq)
    assert got.shape == ref.shape == (23,)
    assert np.all(np.isfinite(got))                       # 以前は全点 NaN
    # 等間隔 100 点は端で丸めが 2**100 倍に増幅される(scipy も同じく端は崩れる)ので、
    # 比べるのは中央の 1/3 だけ。
    mid = (xq > 3e-5) & (xq < 7e-5)
    assert int(mid.sum()) >= 7
    assert np.abs(got - np.sin(1e4 * xq))[mid].max() < 1e-10
    assert np.abs(got - ref)[mid].max() < 1e-10
    # Chebyshev 点なら同じ小区間で全域が真値に一致する
    ck = N.chebyshev_nodes(100, 0.0, 1e-4)
    gc = N.interp_barycentric(ck, np.sin(1e4 * ck), xq)
    assert gc.shape == (23,)
    assert np.abs(gc - np.sin(1e4 * xq)).max() < 1e-12


def test_barycentric_small_case_unchanged():
    xk = np.linspace(-1, 1, 5)
    xq = np.linspace(-1, 1, 11)
    got = N.interp_barycentric(xk, xk ** 3 - xk, xq)
    assert np.abs(got - (xq ** 3 - xq)).max() < 1e-14


# --- 5. chebyshev_eval_nd: d 点 x d 次元の list が格子扱いされていた -------------------------
def _cheb_fixture():
    rng = np.random.default_rng(3)
    return N.chebyshev_coeffs_nd(rng.random((4, 5)))


def test_list_of_points_equals_ndarray_points():
    c = _cheb_fixture()
    P = np.array([[0.1, 0.2], [0.3, -0.4]])
    a = N.chebyshev_eval_nd(c, P)
    b = N.chebyshev_eval_nd(c, P.tolist())
    assert a.shape == b.shape == (2,)
    assert np.array_equal(a, b)


def test_tuple_still_means_grid():
    c = _cheb_fixture()
    gx, gy = np.array([0.1, 0.3]), np.array([0.2, -0.4, 0.5])
    G = N.chebyshev_eval_nd(c, (gx, gy))
    GX, GY = np.meshgrid(gx, gy, indexing="ij")
    pts = N.chebyshev_eval_nd(c, np.column_stack([GX.ravel(), GY.ravel()]))
    assert G.shape == (2, 3)
    assert np.allclose(G.ravel(), pts, atol=1e-14)


def test_ragged_list_fails_closed():
    c = _cheb_fixture()
    with pytest.raises(ValueError, match="tuple"):
        N.chebyshev_eval_nd(c, [np.array([0.1, 0.3]), np.array([0.2, -0.4, 0.5])])
