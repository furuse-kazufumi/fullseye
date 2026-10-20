"""性能改善第6弾: 成立条件を明示した専用経路を旧実装と照合する。"""
from __future__ import annotations

import numpy as np
import pytest
from scipy import linalg

import mathnumerics as mn
import mathtransforms as mt
import pose_quat as pq


def _old_impulse(num, den, t):
    A, B, C, _ = mt._state_space(num, den)
    return np.array([(C @ linalg.expm(A * ti) @ B).item() for ti in t])


def _old_step(num, den, t):
    A, B, C, D = mt._state_space(num, den)
    n = len(A)
    M = np.zeros((n + 1, n + 1))
    M[:n, :n], M[:n, n:] = A, B
    return np.array([(C @ linalg.expm(M * ti)[:n, n:]).item() + D for ti in t])


@pytest.mark.parametrize("num,den", [([1], [1, 1]), ([1], [1, .1, 4]), ([1], [1, 80, 900])])
def test_uniform_transfer_responses_match_per_time_reference(num, den):
    t = np.linspace(0, 10, 10_000)
    np.testing.assert_allclose(mt.tf_impulse_response(num, den, t), _old_impulse(num, den, t), rtol=1e-10, atol=1e-12)
    np.testing.assert_allclose(mt.tf_step_response(num, den, t), _old_step(num, den, t), rtol=1e-10, atol=1e-12)


def test_nonuniform_and_ill_conditioned_transfer_responses_keep_old_path(monkeypatch):
    real = mt.linalg.expm
    calls = []
    monkeypatch.setattr(mt.linalg, "expm", lambda a: (calls.append(a.copy()), real(a))[1])
    t = np.array([0., .1, .21, .3])
    mt.tf_impulse_response([1], [1, 1], t)
    assert len(calls) == len(t)
    calls.clear()
    mt.tf_impulse_response([1], [1, 1e8], np.linspace(0, 1, 5))
    assert len(calls) == 5
    calls.clear()
    mt.tf_impulse_response([1], [1, 1], np.linspace(0, 1, 1000))
    assert len(calls) < 10


def _old_abel_image(image, dr=1., center=None, method="onion"):
    a = np.asarray(image, dtype=float)
    H, W = a.shape
    if center is None:
        prof = np.clip(a, 0, None).sum(axis=0)
        center = float(np.sum(prof * np.arange(W)) / max(prof.sum(), 1e-300))
    c = float(center); R = int(min(c, W - 1 - c))
    xs, cols = np.arange(R + 1.), np.arange(W, dtype=float)
    right = np.stack([np.interp(c + xs, cols, row) for row in a])
    left = np.stack([np.interp(c - xs, cols, row) for row in a])
    half = .5 * (left + right)
    return np.stack([mt.abel_inverse(row, dr, method=method) for row in half])


@pytest.mark.parametrize("width", [17, 18])
def test_abel_image_onion_one_matrix_and_same_rows(monkeypatch, width):
    rng = np.random.default_rng(width)
    image = rng.random((7, width))
    expected = _old_abel_image(image, center=(width - 1) / 2)
    real = mt._onion_matrix; calls = []
    monkeypatch.setattr(mt, "_onion_matrix", lambda n, dr: (calls.append((n, dr)), real(n, dr))[1])
    got = mt.abel_inverse_image(image, center=(width - 1) / 2, method="onion")["slice"]
    np.testing.assert_allclose(got, expected, rtol=1e-12, atol=1e-12)
    assert len(calls) == 1


def _old_cubature(n, dim, a=-1., b=1.):
    lo = np.broadcast_to(np.asarray(a, float), (dim,)); hi = np.broadcast_to(np.asarray(b, float), (dim,))
    x, w = np.polynomial.legendre.leggauss(n)
    axes = [.5 * (hi[d] - lo[d]) * x + .5 * (hi[d] + lo[d]) for d in range(dim)]
    wts = [.5 * (hi[d] - lo[d]) * w for d in range(dim)]
    grids = np.meshgrid(*axes, indexing="ij"); W = np.ones_like(grids[0])
    for d in range(dim):
        W *= np.meshgrid(*[wts[k] if k == d else np.ones(n) for k in range(dim)], indexing="ij")[d]
    return np.stack([g.ravel() for g in grids], axis=1), W.ravel()


@pytest.mark.parametrize("dim", range(1, 5))
@pytest.mark.parametrize("n", [2, 4, 8])
def test_cubature_matches_old_layout_and_polynomial(dim, n):
    got = mn.gauss_cubature(n, dim, np.arange(dim), np.arange(dim) + 2)
    nodes, weights = _old_cubature(n, dim, np.arange(dim), np.arange(dim) + 2)
    np.testing.assert_allclose(got["nodes"], nodes, rtol=0, atol=1e-15)
    np.testing.assert_allclose(got["weights"], weights, rtol=0, atol=1e-15)
    assert np.sum(got["weights"] * np.prod(got["nodes"], axis=1)) == pytest.approx(np.prod(2 * np.arange(dim) + 2))


@pytest.mark.parametrize("n", [2, 17, 2000])
def test_chebyshev2_analytic_barycentric_matches_general(n):
    xk = mn.chebyshev_nodes(n, -2, 3, kind=2); yk = np.sin(xk)
    x = np.linspace(-2, 3, 101)
    np.testing.assert_allclose(mn.interp_barycentric(xk, yk, x, nodes="chebyshev2"),
                               mn.interp_barycentric(xk, yk, x), rtol=1e-12, atol=1e-12)
    if n > 2:  # 2 点では任意の異なる端点が Lobatto 点になる
        bad = xk.copy(); bad[n // 2] += 2e-11
        with pytest.raises(ValueError, match="Chebyshev"):
            mn.interp_barycentric(bad, yk, x, nodes="chebyshev2")


def test_dct_diagnostics_modes_and_inverse_do_not_sort(monkeypatch):
    x = np.arange(24.).reshape(4, 6)
    default = mt.dct_transform(x)
    assert set(default) == {"coeffs", "energy", "compaction"}
    real = mt.np.sort; calls = []
    monkeypatch.setattr(mt.np, "sort", lambda a, *args, **kwargs: (calls.append(1), real(a, *args, **kwargs))[1])
    energy = mt.dct_transform(x, diagnostics="energy")
    none = mt.dct_transform(x, diagnostics="none")
    assert not calls
    inv = mt.dct_transform(default["coeffs"], inverse=True)
    assert calls == [1]  # 逆変換の従来診断経路は変えない
    assert set(energy) == {"coeffs", "energy"}
    assert isinstance(none, np.ndarray)
    np.testing.assert_array_equal(default["coeffs"], energy["coeffs"])
    np.testing.assert_allclose(inv["coeffs"], x, atol=1e-12)


def test_pose_inverse_rigid_specialisation_and_general_fallback(monkeypatch):
    rng = np.random.default_rng(6)
    real = pq.np.linalg.inv; calls = []
    monkeypatch.setattr(pq.np.linalg, "inv", lambda a: (calls.append(1), real(a))[1])
    for _ in range(40):
        p = rng.normal(size=6)
        expected = pq.hom_mat3d_to_pose_local(real(pq.pose_to_hom_mat3d_local(p)))
        got = pq.pose_invert(p)
        np.testing.assert_allclose(pq.pose_to_hom_mat3d_local(got), pq.pose_to_hom_mat3d_local(expected), atol=1e-12)
        np.testing.assert_allclose(pq.pose_to_hom_mat3d_local(pq.pose_compose(p, got)), np.eye(4), atol=1e-12)
    assert not calls
    H = np.eye(4); H[0, 0] = 2; H[0, 1] = .2
    pq.pose_invert(H)
    assert calls == [1]
