# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Ground-truth tests for the mathematics operators (mathops.py).

Every assertion is against an *analytic* ground truth — a hand-solved 2x2/3x3
system, an exactly-known covariance, the roots of a factored polynomial — plus
the fail-closed contracts (strict dimensionality, NaN/Inf rejection, singular /
constant / out-of-range refusal). Sign-indeterminate quantities (eigenvectors,
singular vectors) are asserted through invariants (reconstruction,
orthogonality, |dot|), never raw entries — per the module's honest disclosure.
"""
import numpy as np
import pytest

import mathops


# --------------------------------------------------------------------------- #
# mat_solve                                                                    #
# --------------------------------------------------------------------------- #
def test_solve_2x2_exact():
    # [[2, 1], [1, 3]] x = [5, 10]  ->  x = (1, 3)  (hand-solved)
    A = np.array([[2.0, 1.0], [1.0, 3.0]])
    x = mathops.mat_solve(A, np.array([5.0, 10.0]))
    assert np.allclose(x, [1.0, 3.0], atol=1e-12)


def test_solve_3x3_exact():
    # Diagonal-dominant 3x3 with a known integer solution x = (1, -2, 3).
    A = np.array([[4.0, 1.0, 0.0], [1.0, 5.0, 2.0], [0.0, 2.0, 6.0]])
    xt = np.array([1.0, -2.0, 3.0])
    x = mathops.mat_solve(A, A @ xt)
    assert np.allclose(x, xt, atol=1e-12)


def test_solve_multiple_rhs():
    A = np.array([[2.0, 0.0], [0.0, 4.0]])
    B = np.array([[2.0, 4.0], [4.0, 8.0]])
    X = mathops.mat_solve(A, B)
    assert np.allclose(X, [[1.0, 2.0], [1.0, 2.0]], atol=1e-12)


def test_solve_singular_raises():
    A = np.array([[1.0, 2.0], [2.0, 4.0]])         # rank 1
    with pytest.raises(ValueError, match="singular"):
        mathops.mat_solve(A, np.array([1.0, 2.0]))


def test_solve_rejects_non_square_and_bad_rhs():
    with pytest.raises(ValueError, match="square"):
        mathops.mat_solve(np.ones((3, 2)), np.ones(3))
    with pytest.raises(ValueError, match="row"):
        mathops.mat_solve(np.eye(2), np.ones(3))


def test_solve_rejects_nan_and_1d_matrix():
    A = np.eye(2)
    A[0, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        mathops.mat_solve(A, np.ones(2))
    with pytest.raises(ValueError, match="2-D"):
        mathops.mat_solve(np.ones(4), np.ones(2))   # no silent promotion


# --------------------------------------------------------------------------- #
# mat_lstsq                                                                    #
# --------------------------------------------------------------------------- #
def test_lstsq_recovers_known_line():
    # y = 2.5 x - 1 + small noise: coefficients recovered within the noise scale.
    rng = np.random.default_rng(7)
    x = np.linspace(0.0, 10.0, 60)
    y = 2.5 * x - 1.0 + 0.01 * rng.standard_normal(x.size)
    A = np.column_stack([x, np.ones_like(x)])
    out = mathops.mat_lstsq(A, y)
    assert abs(out["x"][0] - 2.5) < 0.01
    assert abs(out["x"][1] + 1.0) < 0.05
    assert out["rank"] == 2
    assert out["residual_ss"] < 60 * (0.05 ** 2)      # residuals at noise scale
    assert out["singular_values"].shape == (2,)


def test_lstsq_exact_system_zero_residual():
    A = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
    xt = np.array([3.0, -2.0])
    out = mathops.mat_lstsq(A, A @ xt)
    assert np.allclose(out["x"], xt, atol=1e-12)
    assert out["residual_ss"] < 1e-24


def test_lstsq_rejects_underdetermined():
    with pytest.raises(ValueError, match="m >= n"):
        mathops.mat_lstsq(np.ones((2, 3)), np.ones(2))


def test_lstsq_rejects_bad_rcond():
    with pytest.raises(ValueError, match="rcond"):
        mathops.mat_lstsq(np.eye(2), np.ones(2), rcond=-1.0)


# --------------------------------------------------------------------------- #
# mat_svd                                                                      #
# --------------------------------------------------------------------------- #
def test_svd_reconstruction_and_order():
    rng = np.random.default_rng(3)
    A = rng.standard_normal((6, 4))
    U, s, Vt = mathops.mat_svd(A)
    assert U.shape == (6, 4) and s.shape == (4,) and Vt.shape == (4, 4)
    assert np.abs(A - (U * s) @ Vt).max() < 1e-12          # |A - U diag(s) Vt|
    assert (np.diff(s) <= 1e-15).all() and (s >= 0.0).all()  # descending, >= 0
    assert np.allclose(U.T @ U, np.eye(4), atol=1e-12)     # thin-orthonormal
    assert np.allclose(Vt @ Vt.T, np.eye(4), atol=1e-12)


def test_svd_known_singular_values_of_diagonal():
    A = np.diag([3.0, 1.0, 2.0])
    _, s, _ = mathops.mat_svd(A)
    assert np.allclose(s, [3.0, 2.0, 1.0], atol=1e-14)


def test_svd_full_matrices_shapes():
    U, s, Vt = mathops.mat_svd(np.ones((5, 3)), full_matrices=True)
    assert U.shape == (5, 5) and s.shape == (3,) and Vt.shape == (3, 3)


def test_svd_rejects_inf():
    A = np.ones((2, 2))
    A[1, 1] = np.inf
    with pytest.raises(ValueError, match="non-finite"):
        mathops.mat_svd(A)


# --------------------------------------------------------------------------- #
# mat_eigh                                                                     #
# --------------------------------------------------------------------------- #
def test_eigh_known_2x2():
    # [[2, 1], [1, 2]]: eigenvalues 1 and 3 (analytic), ascending order.
    w, V = mathops.mat_eigh(np.array([[2.0, 1.0], [1.0, 2.0]]))
    assert np.allclose(w, [1.0, 3.0], atol=1e-12)
    # eigenvectors up to sign: |v . (1,±1)/sqrt(2)| == 1
    assert abs(abs(V[:, 0] @ np.array([1.0, -1.0]) / np.sqrt(2)) - 1.0) < 1e-12
    assert abs(abs(V[:, 1] @ np.array([1.0, 1.0]) / np.sqrt(2)) - 1.0) < 1e-12


def test_eigh_orthonormal_and_reconstructs():
    rng = np.random.default_rng(11)
    B = rng.standard_normal((5, 5))
    A = (B + B.T) / 2.0
    w, V = mathops.mat_eigh(A)
    assert np.allclose(V.T @ V, np.eye(5), atol=1e-12)     # orthonormal columns
    assert np.abs(A - (V * w) @ V.T).max() < 1e-11         # A = V diag(w) V^T
    assert (np.diff(w) >= -1e-15).all()                    # ascending


def test_eigh_rejects_non_symmetric():
    with pytest.raises(ValueError, match="not symmetric"):
        mathops.mat_eigh(np.array([[1.0, 2.0], [0.0, 1.0]]))


def test_eigh_rejects_non_square():
    with pytest.raises(ValueError, match="square"):
        mathops.mat_eigh(np.ones((2, 3)))


# --------------------------------------------------------------------------- #
# mat_pinv                                                                     #
# --------------------------------------------------------------------------- #
def test_pinv_inverts_full_rank_square():
    A = np.array([[2.0, 1.0], [1.0, 3.0]])
    assert np.allclose(mathops.mat_pinv(A) @ A, np.eye(2), atol=1e-12)


def test_pinv_least_squares_equals_lstsq():
    rng = np.random.default_rng(5)
    A = rng.standard_normal((8, 3))
    b = rng.standard_normal(8)
    x_pinv = mathops.mat_pinv(A) @ b
    x_ls = mathops.mat_lstsq(A, b)["x"]
    assert np.allclose(x_pinv, x_ls, atol=1e-10)


def test_pinv_rcond_regularizes_rank_deficient():
    # rank-1 matrix: with a sane rcond the tiny direction is dropped, and
    # pinv satisfies the Moore-Penrose identity A pinv(A) A = A.
    A = np.outer([1.0, 2.0], [3.0, 4.0])
    P = mathops.mat_pinv(A, rcond=1e-10)
    assert np.abs(A @ P @ A - A).max() < 1e-10
    with pytest.raises(ValueError, match="rcond"):
        mathops.mat_pinv(A, rcond=np.nan)


# --------------------------------------------------------------------------- #
# mat_cond                                                                     #
# --------------------------------------------------------------------------- #
def test_cond_orthogonal_is_one():
    th = 0.3
    Q = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    assert abs(mathops.mat_cond(Q) - 1.0) < 1e-12
    assert abs(mathops.mat_cond(np.eye(4)) - 1.0) < 1e-14


def test_cond_known_diagonal_and_singular():
    assert abs(mathops.mat_cond(np.diag([10.0, 0.1])) - 100.0) < 1e-10
    # An exact zero singular value (zero column) -> inf.
    assert mathops.mat_cond(np.array([[1.0, 0.0], [2.0, 0.0]])) == np.inf
    # A rank-1 matrix built from finite floats: the smallest singular value is
    # rounding dust (~eps), so cond is finite but past every trust threshold.
    assert mathops.mat_cond(np.array([[1.0, 2.0], [2.0, 4.0]])) > 1e15


# --------------------------------------------------------------------------- #
# stat_describe                                                                #
# --------------------------------------------------------------------------- #
def test_describe_known_values():
    d = mathops.stat_describe(np.array([1.0, 2.0, 3.0, 4.0]))
    assert d["n"] == 4 and d["mean"] == 2.5
    assert abs(d["std"] - np.sqrt(1.25)) < 1e-14           # population ddof=0
    assert d["min"] == 1.0 and d["max"] == 4.0
    assert d["percentiles"]["p50"] == 2.5
    assert d["percentiles"]["p25"] == 1.75                 # numpy linear method
    assert set(d["percentiles"]) == {"p5", "p25", "p50", "p75", "p95"}


def test_describe_fail_closed():
    with pytest.raises(ValueError, match="non-finite"):
        mathops.stat_describe([1.0, np.nan])
    with pytest.raises(ValueError, match="1-D"):
        mathops.stat_describe(np.ones((2, 2)))
    with pytest.raises(ValueError, match="at least 1"):
        mathops.stat_describe([])


# --------------------------------------------------------------------------- #
# stat_histogram                                                               #
# --------------------------------------------------------------------------- #
def test_histogram_counts_and_edges():
    counts, edges = mathops.stat_histogram([0.5, 1.5, 1.6, 2.5], bins=3,
                                           range=(0.0, 3.0))
    assert counts.dtype == np.int64
    assert list(counts) == [1, 2, 1] and counts.sum() == 4
    assert np.allclose(edges, [0.0, 1.0, 2.0, 3.0])


def test_histogram_density_integrates_to_one():
    rng = np.random.default_rng(1)
    counts, edges = mathops.stat_histogram(rng.standard_normal(500), bins=20,
                                           density=True)
    assert counts.dtype == np.float64
    assert abs(float((counts * np.diff(edges)).sum()) - 1.0) < 1e-12


def test_histogram_fail_closed():
    with pytest.raises(ValueError, match="bins"):
        mathops.stat_histogram([1.0, 2.0], bins=0)
    with pytest.raises(ValueError, match="bins"):
        mathops.stat_histogram([1.0, 2.0], bins=2.5)
    with pytest.raises(ValueError, match="lo < hi"):
        mathops.stat_histogram([1.0, 2.0], range=(3.0, 1.0))
    with pytest.raises(ValueError, match="finite"):
        mathops.stat_histogram([1.0, 2.0], range=(0.0, np.inf))


# --------------------------------------------------------------------------- #
# stat_covariance                                                              #
# --------------------------------------------------------------------------- #
def test_covariance_hand_computed_2x2():
    # Samples (N=3, D=2): x = [0, 1, 2], y = [0, 2, 4].
    # mean = (1, 2); ddof=1: var(x) = 1, var(y) = 4, cov(x, y) = 2.
    X = np.array([[0.0, 0.0], [1.0, 2.0], [2.0, 4.0]])
    C = mathops.stat_covariance(X)
    assert np.allclose(C, [[1.0, 2.0], [2.0, 4.0]], atol=1e-14)
    assert np.array_equal(C, C.T)                          # exactly symmetric
    assert np.allclose(C, np.cov(X.T), atol=1e-14)         # matches the oracle


def test_covariance_fail_closed():
    with pytest.raises(ValueError, match="at least 2 observations"):
        mathops.stat_covariance(np.ones((1, 3)))
    with pytest.raises(ValueError, match="2-D"):
        mathops.stat_covariance(np.ones(5))


# --------------------------------------------------------------------------- #
# stat_correlation                                                             #
# --------------------------------------------------------------------------- #
def test_correlation_diagonal_symmetry_and_known_signs():
    rng = np.random.default_rng(2)
    a = rng.standard_normal(300)
    X = np.column_stack([a, 2.0 * a + 0.01 * rng.standard_normal(300),
                         -a + 0.01 * rng.standard_normal(300)])
    R = mathops.stat_correlation(X)
    assert np.array_equal(np.diag(R), np.ones(3))          # diagonal exactly 1
    assert np.array_equal(R, R.T)                          # exactly symmetric
    assert (np.abs(R) <= 1.0).all()
    assert R[0, 1] > 0.99 and R[0, 2] < -0.99              # known correlations


def test_correlation_constant_column_raises():
    X = np.column_stack([np.arange(5.0), np.full(5, 7.0)])
    with pytest.raises(ValueError, match="column\\(s\\) 1"):
        mathops.stat_correlation(X)


# --------------------------------------------------------------------------- #
# stat_zscore                                                                  #
# --------------------------------------------------------------------------- #
def test_zscore_known_and_standardized():
    z = mathops.stat_zscore(np.array([1.0, 2.0, 3.0]))
    assert np.allclose(z, [-np.sqrt(1.5), 0.0, np.sqrt(1.5)], atol=1e-12)
    assert abs(z.mean()) < 1e-14 and abs(z.std(ddof=0) - 1.0) < 1e-12


def test_zscore_constant_raises():
    with pytest.raises(ValueError, match="constant"):
        mathops.stat_zscore(np.full(10, 3.0))
    with pytest.raises(ValueError, match="non-finite"):
        mathops.stat_zscore([1.0, np.inf, 2.0])


# --------------------------------------------------------------------------- #
# interp_linear                                                                #
# --------------------------------------------------------------------------- #
def test_interp_linear_exact_on_polyline():
    x = np.array([0.0, 1.0, 3.0])
    y = np.array([0.0, 2.0, -2.0])                          # known polyline
    assert mathops.interp_linear(x, y, 0.5) == 1.0          # scalar -> float
    assert np.allclose(mathops.interp_linear(x, y, [1.0, 2.0]), [2.0, 0.0])
    out = mathops.interp_linear(x, y, np.array([0.25, 2.5]))
    assert np.allclose(out, [0.5, -1.0], atol=1e-14)


def test_interp_linear_out_of_range_policy():
    x, y = np.array([0.0, 1.0]), np.array([0.0, 10.0])
    with pytest.raises(ValueError, match="outside the data range"):
        mathops.interp_linear(x, y, 2.0)                    # fail-closed default
    assert mathops.interp_linear(x, y, 2.0, out_of_range="clamp") == 10.0
    assert mathops.interp_linear(x, y, -1.0, out_of_range="clamp") == 0.0
    with pytest.raises(ValueError, match="out_of_range"):
        mathops.interp_linear(x, y, 0.5, out_of_range="extrapolate")


def test_interp_linear_rejects_unsorted_grid():
    with pytest.raises(ValueError, match="strictly increasing"):
        mathops.interp_linear([1.0, 0.0], [0.0, 1.0], 0.5)
    with pytest.raises(ValueError, match="strictly increasing"):
        mathops.interp_linear([0.0, 0.0, 1.0], [0.0, 1.0, 2.0], 0.5)


# --------------------------------------------------------------------------- #
# interp_cubic                                                                 #
# --------------------------------------------------------------------------- #
def test_interp_cubic_reproduces_cubic_polynomial():
    # not-a-knot spline through samples of x^3 - 2x reproduces it exactly.
    x = np.linspace(-2.0, 2.0, 6)
    y = x ** 3 - 2.0 * x
    xq = np.array([-1.7, -0.3, 0.9, 1.5])
    truth = xq ** 3 - 2.0 * xq
    assert np.allclose(mathops.interp_cubic(x, y, xq), truth, atol=1e-10)
    s = mathops.interp_cubic(x, y, 0.5)                      # scalar -> float
    assert isinstance(s, float) and abs(s - (0.125 - 1.0)) < 1e-10


def test_interp_cubic_out_of_range_and_min_points():
    x = np.linspace(0.0, 3.0, 4)
    y = x ** 2
    with pytest.raises(ValueError, match="outside the data range"):
        mathops.interp_cubic(x, y, 5.0)
    assert mathops.interp_cubic(x, y, 5.0, out_of_range="clamp") == pytest.approx(9.0)
    with pytest.raises(ValueError, match="at least 4"):
        mathops.interp_cubic([0.0, 1.0, 2.0], [0.0, 1.0, 4.0], 0.5)
    with pytest.raises(ValueError, match="bc_type"):
        mathops.interp_cubic(x, y, 0.5, bc_type="periodic")


# --------------------------------------------------------------------------- #
# poly_fit / poly_eval                                                         #
# --------------------------------------------------------------------------- #
def test_poly_fit_recovers_exact_quadratic():
    x = np.linspace(-1.0, 1.0, 9)
    y = 2.0 * x ** 2 - 3.0 * x + 1.0
    out = mathops.poly_fit(x, y, 2)
    assert np.allclose(out["coeffs"], [2.0, -3.0, 1.0], atol=1e-10)
    assert out["degree"] == 2
    assert out["rms_residual"] < 1e-12
    assert 1.0 <= out["cond"] < 100.0                       # well-conditioned


def test_poly_fit_condition_warning_mechanism():
    # Degree-9 fit on a raw [1000, 1010] range: Vandermonde cond explodes.
    x = np.linspace(1000.0, 1010.0, 30)
    y = x.copy()
    with pytest.warns(RuntimeWarning, match="condition number"):
        out = mathops.poly_fit(x, y, 9)
    assert out["cond"] > mathops.POLY_COND_WARN


def test_poly_fit_fail_closed():
    with pytest.raises(ValueError, match="degree"):
        mathops.poly_fit([0.0, 1.0], [0.0, 1.0], -1)
    with pytest.raises(ValueError, match="degree"):
        mathops.poly_fit([0.0, 1.0], [0.0, 1.0], 1.5)
    with pytest.raises(ValueError, match="at least 3"):
        mathops.poly_fit([0.0, 1.0], [0.0, 1.0], 2)         # under-determined
    with pytest.raises(ValueError, match="strictly increasing"):
        mathops.poly_fit([1.0, 0.0], [0.0, 1.0], 1)


def test_poly_eval_known():
    c = np.array([1.0, -2.0, 0.0, 5.0])                     # x^3 - 2x^2 + 5
    assert mathops.poly_eval(c, 0.0) == 5.0
    assert mathops.poly_eval(c, 2.0) == 5.0                 # 8 - 8 + 5
    assert np.allclose(mathops.poly_eval(c, [0.0, 1.0]), [5.0, 4.0])
    with pytest.raises(ValueError, match="non-finite"):
        mathops.poly_eval([np.nan, 1.0], 0.0)
    with pytest.raises(ValueError, match="scalar or a 1-D"):
        mathops.poly_eval(c, np.ones((2, 2)))


# --------------------------------------------------------------------------- #
# poly_roots                                                                   #
# --------------------------------------------------------------------------- #
def test_poly_roots_factored_cubic_exact():
    # (x - 1)(x - 2)(x + 3) = x^3 - 7x + 6 -> roots {-3, 1, 2}.
    r = mathops.poly_roots([1.0, 0.0, -7.0, 6.0])
    assert r.dtype == np.complex128
    assert np.allclose(sorted(r.real), [-3.0, 1.0, 2.0], atol=1e-10)
    assert np.abs(r.imag).max() < 1e-10
    rr = mathops.poly_roots([1.0, 0.0, -7.0, 6.0], real_only=True)
    assert rr.dtype == np.float64
    assert np.allclose(rr, [-3.0, 1.0, 2.0], atol=1e-10)


def test_poly_roots_complex_pair():
    # x^2 + 1 -> ±i; real_only correctly returns an EMPTY array.
    r = mathops.poly_roots([1.0, 0.0, 1.0])
    assert np.allclose(sorted(r.imag), [-1.0, 1.0], atol=1e-12)
    assert np.abs(r.real).max() < 1e-12
    assert mathops.poly_roots([1.0, 0.0, 1.0], real_only=True).size == 0


def test_poly_roots_sorted_deterministic():
    r = mathops.poly_roots([1.0, 0.0, -7.0, 6.0])
    assert (np.diff(r.real) >= -1e-12).all()                # sorted by real part


def test_poly_roots_fail_closed():
    with pytest.raises(ValueError, match="leading coefficient"):
        mathops.poly_roots([0.0, 1.0, 2.0])
    with pytest.raises(ValueError, match="at least 2"):
        mathops.poly_roots([3.0])
    with pytest.raises(ValueError, match="imag_tol"):
        mathops.poly_roots([1.0, 1.0], imag_tol=-1.0)


# --------------------------------------------------------------------------- #
# facade / registry wiring                                                     #
# --------------------------------------------------------------------------- #
def test_mathops_registry_names_resolve():
    assert len(mathops.MATHOPS) == 16
    for name in mathops.MATHOPS:
        assert callable(getattr(mathops, name)), name
        assert name in mathops.__all__


def test_fullseye_facade_exports_mathops():
    import fullseye
    for name in mathops.MATHOPS:
        assert getattr(fullseye, name) is getattr(mathops, name), name
        assert name in fullseye.__all__
    assert fullseye.mathops is mathops
