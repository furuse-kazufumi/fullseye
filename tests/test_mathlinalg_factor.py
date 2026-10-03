# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Gates for the factorisations a student meets first (LU / QR / Cholesky / general eig, 2026-10-03).

LU and QR were reachable only through the HALCON facade names ``decompose_matrix`` /
``orthogonal_decompose_matrix`` (out of OP_INDEX and the ledger). Each gate pairs the success with the
textbook failure: LU without pivoting (growth 1e20), classical Gram–Schmidt losing orthogonality like
κ², a nudged Jordan block whose eigenvalues move by √ε.
"""
import math
import warnings

import numpy as np
import pytest

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import fullseye as fs
    import mathops as MO
    import opsmath

NEW = ["mat_lu", "mat_qr", "mat_cholesky", "mat_eig"]


def test_public_and_ledger():
    assert opsmath.missing() == []
    assert set(NEW) <= set(opsmath.list_ops("linalg"))
    for n in NEW:
        assert callable(getattr(fs, n)) and n in fs.__all__, n


def test_lu_partial_pivoting_reconstructs():
    A = np.random.default_rng(0).random((6, 6))
    r = MO.mat_lu(A)
    assert r["residual"] < 1e-14
    assert np.allclose(np.tril(r["L"]), r["L"]) and np.allclose(np.diag(r["L"]), 1)
    assert np.allclose(np.triu(r["U"]), r["U"]) and np.abs(r["L"]).max() <= 1 + 1e-15


def test_lu_without_pivoting_fails_on_a_tiny_pivot():
    """[[1e-20, 1], [1, 1]]: without pivoting the multiplier is 1e20 and L U loses A[1,1] (residual 1.0);
    partial pivoting swaps the rows and is exact (Trefethen & Bau, Lecture 20)."""
    A = np.array([[1e-20, 1.0], [1.0, 1.0]])
    bad, good = MO.mat_lu(A, pivoting="none"), MO.mat_lu(A)
    assert bad["growth"] > 1e19 and bad["residual"] > 0.5
    assert good["growth"] <= 1.0 + 1e-15 and good["residual"] < 1e-15


def _graded(kappa_exp, seed=1, n=40, m=12):
    rng = np.random.default_rng(seed)
    U, _ = np.linalg.qr(rng.standard_normal((n, m)))
    V, _ = np.linalg.qr(rng.standard_normal((m, m)))
    return U @ np.diag(np.logspace(0, -kappa_exp, m)) @ V.T


def test_qr_orthogonality_loss_scales_with_condition_number():
    """Same matrix, three algorithms: CGS loses orthogonality like κ² (gone by κ = 1e9), MGS like κ·ε,
    Householder stays at ε (Björck 1967)."""
    loss = {m: [MO.mat_qr(_graded(k), m)["orthogonality_loss"] for k in (3, 5, 7)] for m in ("cgs", "mgs", "householder")}
    # CGS: κ × 100 → loss × ~1e4 (κ²); MGS: κ × 100 → loss × ~1e2 (κ)
    assert loss["cgs"][2] / loss["cgs"][0] > 1e6
    assert 1e2 < loss["mgs"][2] / loss["mgs"][0] < 1e5
    assert max(loss["householder"]) < 1e-14
    assert MO.mat_qr(_graded(9), "cgs")["orthogonality_loss"] > 0.5
    for m in ("cgs", "mgs", "householder"):
        assert MO.mat_qr(_graded(5), m)["residual"] < 1e-14       # A = QR holds for all three — only Q decays


def test_cholesky_spd_logdet_and_rejects_indefinite():
    A = np.array([[4.0, 2.0], [2.0, 3.0]])
    c = MO.mat_cholesky(A)
    assert np.abs(c["L"] @ c["L"].T - A).max() < 1e-15
    assert abs(c["log_det"] - math.log(8.0)) < 1e-14
    with pytest.raises(ValueError, match="positive definite"):
        MO.mat_cholesky(np.array([[1.0, 2.0], [2.0, 1.0]]))
    with pytest.raises(ValueError, match="symmetric"):
        MO.mat_cholesky(np.array([[1.0, 2.0], [0.0, 1.0]]))


def test_eig_rotation_markov_and_nudged_jordan():
    th = 0.7
    R = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
    w = MO.mat_eig(R)["w"]
    assert np.allclose(w, [np.exp(1j * th), np.exp(-1j * th)], atol=1e-15)
    P = np.array([[0.9, 0.1, 0.0], [0.2, 0.7, 0.1], [0.0, 0.3, 0.7]])
    e = MO.mat_eig(P.T)
    assert abs(e["w"][0] - 1) < 1e-14 and e["residual"] < 1e-14
    pi = np.real(e["V"][:, 0] / e["V"][:, 0].sum())
    assert np.abs(pi @ P - pi).max() < 1e-14                        # stationary distribution
    # Jordan block nudged by 1e-10: eigenvalues move by √1e-10 = 1e-5, and κ(V) reports it
    J = MO.mat_eig(np.array([[1.0, 1.0], [1e-10, 1.0]]))
    assert np.allclose(np.sort(J["w"].real), [1 - 1e-5, 1 + 1e-5], atol=1e-9) and J["cond_V"] > 1e4


def test_factorisations_reject_bad_shapes():
    with pytest.raises(ValueError):
        MO.mat_lu(np.ones((2, 3)))
    with pytest.raises(ValueError):
        MO.mat_qr(np.ones((2, 3)))
    with pytest.raises(ValueError):
        MO.mat_qr(np.ones((3, 2)), "cgs")                          # rank deficient
    with pytest.raises(ValueError):
        MO.mat_lu(np.eye(2), pivoting="full")
