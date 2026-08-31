# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Ground-truth tests for the mathematics operators (mathops.py).

Every assertion is against an *analytic* ground truth — a hand-solved 2x2/3x3
system, an exactly-known covariance, the roots of a factored polynomial — plus
the fail-closed contracts (strict dimensionality, NaN/Inf rejection, singular /
constant / out-of-range refusal). Sign-indeterminate quantities (eigenvectors,
singular vectors) are asserted through invariants (reconstruction,
orthogonality, |dot|), never raw entries — per the module's honest disclosure.
"""
import warnings

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
# silent-truncation rejection (2026-08-31 adversarial audit regressions)       #
# --------------------------------------------------------------------------- #
def test_complex_input_rejected_not_truncated():
    # Regression: numpy's float64 coercion of complex input emits only a
    # ComplexWarning and silently discards the imaginary part — mat_solve of a
    # complex matrix returned a plausible-wrong real answer. Now ValueError.
    C = np.array([[1.0 + 2.0j, 0.0], [0.0, 1.0]])
    with pytest.raises(ValueError, match="complex"):
        mathops.mat_solve(C, [1.0, 1.0])                    # matrix slot
    with pytest.raises(ValueError, match="complex"):
        mathops.mat_lstsq(np.eye(2), np.array([1.0 + 5.0j, 2.0]))  # rhs slot
    with pytest.raises(ValueError, match="complex"):
        mathops.stat_zscore(np.array([1.0 + 9.0j, 2.0, 3.0]))      # vector slot
    with pytest.raises(ValueError, match="complex"):
        mathops.interp_linear([0.0, 1.0], [0.0, 1.0],
                              np.array([0.5 + 0.5j]))              # query slot
    with pytest.raises(ValueError, match="complex"):
        mathops.poly_eval(np.array([1.0 + 3.0j, 0.0j]), 2.0)       # coeffs slot


def test_masked_values_rejected_not_stripped():
    # Same family: coercing a masked array silently strips the mask and uses
    # the raw values underneath as if they were valid measurements.
    m = np.ma.masked_array([[1.0, 0.0], [0.0, 1.0]],
                           mask=[[True, False], [False, False]])
    with pytest.raises(ValueError, match="masked"):
        mathops.mat_solve(m, [1.0, 1.0])
    with pytest.raises(ValueError, match="masked"):
        mathops.stat_describe(np.ma.masked_array([1.0, 2.0], mask=[True, False]))
    # A masked array with NO masked entries loses nothing — accepted.
    ok = np.ma.masked_array([[2.0, 0.0], [0.0, 1.0]], mask=False)
    assert np.allclose(mathops.mat_solve(ok, [2.0, 3.0]), [1.0, 3.0])


def test_histogram_density_over_empty_range_raises_not_nan():
    # Regression: an explicit range excluding every sample with density=True
    # returned a silent all-NaN density (numpy divides 0/0). Now ValueError.
    with pytest.raises(ValueError, match="no samples"):
        mathops.stat_histogram([5.0, 6.0], bins=3, range=(0.0, 1.0), density=True)
    # density=False stays: honest zero counts are a valid answer.
    counts, _ = mathops.stat_histogram([5.0, 6.0], bins=3, range=(0.0, 1.0))
    assert list(counts) == [0, 0, 0]
    # A range touching the data still yields a normalised density.
    counts, edges = mathops.stat_histogram([0.5], bins=2, range=(0.0, 1.0),
                                           density=True)
    assert abs(float((counts * np.diff(edges)).sum()) - 1.0) < 1e-12


def test_histogram_bins_capped():
    # Regression: bins was unbounded — bins=2**30 would try to allocate
    # gigabytes of edges/counts for a 2-sample vector. Now capped.
    with pytest.raises(ValueError, match="cap"):
        mathops.stat_histogram([1.0, 2.0], bins=mathops.MAX_ELEMENTS + 1)
    counts, _ = mathops.stat_histogram([1.0, 2.0], bins=4)   # sane bins still fine
    assert counts.sum() == 2


# --------------------------------------------------------------------------- #
# facade / registry wiring                                                     #
# --------------------------------------------------------------------------- #
def test_mathops_registry_names_resolve():
    assert len(mathops.MATHOPS) == 26            # tier1 16 + tier2 complex 10
    for name in mathops.MATHOPS:
        assert callable(getattr(mathops, name)), name
        assert name in mathops.__all__


def test_fullseye_facade_exports_mathops():
    import fullseye
    for name in mathops.MATHOPS:
        assert getattr(fullseye, name) is getattr(mathops, name), name
        assert name in fullseye.__all__
    assert fullseye.mathops is mathops


def test_poly_eval_overflow_is_rejected_not_silent_inf():
    """連鎖ファザー wave-7 実測: 256 個の係数を |x|<=22 で評価すると 22**255 が
    float64 を超え、無言で inf が下流に流れていた。引数の取り違え(長い信号を
    係数に渡す)が典型なので、その旨を告げて fail-closed にする。"""
    coeffs = np.sin(np.linspace(0.0, 8 * np.pi, 256))
    with pytest.raises(ValueError, match="overflow"):
        mathops.poly_eval(coeffs, np.linspace(0.0, 22.0, 16))
    # 正常系は不変: (x^2 - 1) を閉形式と一致させる
    got = mathops.poly_eval(np.array([1.0, 0.0, -1.0]), np.array([0.0, 1.0, 2.0]))
    assert np.allclose(got, [-1.0, 0.0, 3.0])
    # 高次でも |x|<=1 なら通る(次数だけを理由に拒否しない)
    assert np.isfinite(mathops.poly_eval(coeffs, np.linspace(-1.0, 1.0, 8))).all()


# --------------------------------------------------------------------------- #
# tier 2 — complex analysis: contours, Cauchy, argument principle, maps        #
#                                                                              #
# Every assertion is against a closed-form truth (2*pi*i, 2*cos(t), 1/k!, the   #
# number of roots of a factored polynomial), checked at two resolutions where   #
# the quadrature is only second order so the *rate* is pinned, not just a       #
# tolerance. Signs are asserted through orientation — where a contour op lies.  #
# --------------------------------------------------------------------------- #
TWO_PI_I = 2.0j * np.pi


def test_contour_circle_is_the_analytic_circle():
    z = mathops.cplx_contour_circle(1.0 + 2.0j, 3.0, 8)
    assert z.shape == (8,) and z.dtype == np.complex128
    assert np.allclose(np.abs(z - (1.0 + 2.0j)), 3.0, atol=1e-12)
    assert z[0] == pytest.approx(4.0 + 2.0j)              # theta = 0
    assert z[2] == pytest.approx(1.0 + 5.0j)              # theta = pi/2 (ccw)
    # the first point is NOT repeated (the closing segment is implicit)
    assert abs(z[-1] - z[0]) > 1.0
    cw = mathops.cplx_contour_circle(0.0, 1.0, 8, orientation="cw")
    assert np.allclose(cw, np.conj(mathops.cplx_contour_circle(0.0, 1.0, 8)))


def test_contour_circle_fail_closed():
    with pytest.raises(ValueError, match="MAX_CONTOUR_POINTS"):
        mathops.cplx_contour_circle(0.0, 1.0, 10 ** 9)     # no 16 GB allocation
    with pytest.raises(ValueError, match="at least 3"):
        mathops.cplx_contour_circle(0.0, 1.0, 2)
    with pytest.raises(ValueError, match="integer"):
        mathops.cplx_contour_circle(0.0, 1.0, 2.5)
    with pytest.raises(ValueError, match="positive real"):
        mathops.cplx_contour_circle(0.0, 0.0, 16)
    with pytest.raises(ValueError, match="positive real"):
        mathops.cplx_contour_circle(0.0, 1.0 + 1.0j, 16)
    with pytest.raises(ValueError, match="finite"):
        mathops.cplx_contour_circle(np.nan, 1.0, 16)
    with pytest.raises(ValueError, match="orientation"):
        mathops.cplx_contour_circle(0.0, 1.0, 16, orientation="CCW")


def test_contour_integral_cauchy_ground_truth_and_second_order():
    # closed form: the integral of dz/z around the origin is 2*pi*i (Cauchy).
    # The chordal trapezoid is second order, so 4x refinement must cut the error
    # ~16x — the rate is the honest claim; a lone tolerance would hide a wrong
    # quadrature that happens to be small.
    errs = {}
    for n in (256, 1024):
        z = mathops.cplx_contour_circle(0.0, 1.0, n)
        errs[n] = abs(mathops.cplx_contour_integral(z, 1.0 / z) - TWO_PI_I) / (2 * np.pi)
    assert errs[256] < 2e-4 and errs[1024] < 1e-5
    assert 14.0 < errs[256] / errs[1024] < 18.0            # measured 16.0
    # exact identities: the integral of z**k vanishes for every analytic integrand
    z = mathops.cplx_contour_circle(0.0, 2.0, 64)
    for k in (0, 1, 2, 5):
        assert abs(mathops.cplx_contour_integral(z, z ** k)) < 1e-9
    # pole outside the contour -> 0
    assert abs(mathops.cplx_contour_integral(z, 1.0 / (z - 10.0))) < 1e-9


def test_contour_integral_orientation_flips_the_sign():
    ccw = mathops.cplx_contour_circle(0.0, 1.0, 256)
    cw = mathops.cplx_contour_circle(0.0, 1.0, 256, orientation="cw")
    a = mathops.cplx_contour_integral(ccw, 1.0 / ccw)
    b = mathops.cplx_contour_integral(cw, 1.0 / cw)
    assert a.imag > 0 and b.imag < 0
    assert a == pytest.approx(-b, rel=1e-12)


def test_contour_integral_fail_closed():
    z = mathops.cplx_contour_circle(0.0, 1.0, 16)
    with pytest.raises(ValueError, match="at least 3"):
        mathops.cplx_contour_integral(z[:2], z[:2])
    with pytest.raises(ValueError, match="same length"):
        mathops.cplx_contour_integral(z, z[:5])
    with pytest.raises(ValueError, match="degenerate contour"):
        mathops.cplx_contour_integral(np.full(8, 1.0 + 0.0j), np.ones(8, complex))
    with pytest.raises(ValueError, match="non-finite"):
        mathops.cplx_contour_integral(z, np.full(16, np.nan))
    with pytest.raises(ValueError, match="1-D"):
        mathops.cplx_contour_integral(np.ones((4, 4), complex), np.ones(16, complex))


def test_winding_number_counts_turns_with_sign():
    z = mathops.cplx_contour_circle(0.0, 1.0, 64)
    assert mathops.cplx_winding_number(z, 0.0) == 1
    assert mathops.cplx_winding_number(z, 0.5 + 0.2j) == 1
    assert mathops.cplx_winding_number(z, 5.0) == 0                   # outside
    assert mathops.cplx_winding_number(
        mathops.cplx_contour_circle(0.0, 1.0, 64, orientation="cw"), 0.0) == -1
    # a doubly-wound circle really is 2 (not 1, not 0)
    th = np.linspace(0.0, 4.0 * np.pi, 512, endpoint=False)
    assert mathops.cplx_winding_number(np.exp(1j * th), 0.0) == 2
    # repeating the first point (a zero-length closing segment) changes nothing
    assert mathops.cplx_winding_number(np.concatenate([z, z[:1]]), 0.0) == 1


def test_winding_number_refuses_points_on_the_contour():
    z = mathops.cplx_contour_circle(0.0, 1.0, 64)
    with pytest.raises(ValueError, match="coincides with contour vertex"):
        mathops.cplx_winding_number(z, complex(z[7]))
    square = np.array([-1 + 0j, 1 + 0j, 1 + 1j, -1 + 1j])
    with pytest.raises(ValueError, match="subtends"):            # on segment #0
        mathops.cplx_winding_number(square, 0.0 + 0.0j)


def test_winding_number_warns_before_it_aliases():
    """Adversarial finding (2026-09-01): a coarse contour can alias the count
    DOWN with no local jump to detect — f = z**5 on a 4-point circle turns
    exactly pi/2 per step and counts 1 instead of 5. Undetectable in principle,
    so the op warns from pi/2 onward and the docstring says refine-until-stable."""
    z4 = mathops.cplx_contour_circle(0.0, 1.0, 4)
    with pytest.warns(RuntimeWarning, match="alias"):
        assert mathops.cplx_argument_principle(z4, z4 ** 5) == 1     # wrong, warned
    z64 = mathops.cplx_contour_circle(0.0, 1.0, 64)
    with warnings.catch_warnings():
        warnings.simplefilter("error")                               # no warning here
        assert mathops.cplx_argument_principle(z64, z64 ** 5) == 5   # true value


def test_cauchy_value_recovers_interior_values():
    z = mathops.cplx_contour_circle(0.0, 1.0, 256)
    assert mathops.cplx_cauchy_value(z, z ** 2, 0.3) == pytest.approx(0.09, abs=1e-4)
    assert mathops.cplx_cauchy_value(z, np.exp(z), 0.2 + 0.1j) == pytest.approx(
        np.exp(0.2 + 0.1j), abs=5e-4)          # measured 1.2e-4 at n = 256
    # a clockwise contour (winding -1) gives the same value: the formula divides
    # by the winding number, so orientation must NOT leak into f(w)
    cw = mathops.cplx_contour_circle(0.0, 1.0, 256, orientation="cw")
    assert mathops.cplx_cauchy_value(cw, cw ** 2, 0.3) == pytest.approx(0.09, abs=1e-4)
    # ... and neither does winding twice
    th = np.linspace(0.0, 4.0 * np.pi, 512, endpoint=False)
    z2 = np.exp(1j * th)
    assert mathops.cplx_cauchy_value(z2, z2 ** 2, 0.3) == pytest.approx(0.09, abs=1e-4)


def test_cauchy_value_accuracy_degrades_toward_the_contour():
    z = mathops.cplx_contour_circle(0.0, 1.0, 256)
    near = abs(mathops.cplx_cauchy_value(z, z ** 2, 0.9) - 0.81)
    mid = abs(mathops.cplx_cauchy_value(z, z ** 2, 0.3) - 0.09)
    assert mid < 2e-5 and near < 2e-4                    # measured 9.0e-6 / 8.1e-5
    assert near > mid                                    # the documented direction


def test_cauchy_value_fail_closed():
    z = mathops.cplx_contour_circle(0.0, 1.0, 64)
    with pytest.raises(ValueError, match="outside the contour"):
        mathops.cplx_cauchy_value(z, z ** 2, 5.0)        # winding 0: not f(w)
    with pytest.raises(ValueError, match="within one sampling step"):
        mathops.cplx_cauchy_value(z, z ** 2, 0.999)      # unresolved 1/(z-w) peak
    with pytest.raises(ValueError, match="coincides with contour vertex"):
        mathops.cplx_cauchy_value(z, z ** 2, complex(z[0]))


def test_argument_principle_counts_zeros_and_poles():
    p = np.array([1.0, 0.0, 0.0, -1.0])                  # z^3 - 1, roots on |z|=1
    big = mathops.cplx_contour_circle(0.0, 2.0, 512)
    small = mathops.cplx_contour_circle(0.0, 0.5, 512)
    one = mathops.cplx_contour_circle(1.0, 0.3, 512)     # encircles the root z=1 only
    assert mathops.cplx_argument_principle(big, mathops.cplx_poly_eval(p, big)) == 3
    assert mathops.cplx_argument_principle(small, mathops.cplx_poly_eval(p, small)) == 0
    assert mathops.cplx_argument_principle(one, mathops.cplx_poly_eval(p, one)) == 1
    # poles count negative, with multiplicity
    z = mathops.cplx_contour_circle(0.0, 1.0, 256)
    assert mathops.cplx_argument_principle(z, 1.0 / z ** 2) == -2
    # a zero and a double pole inside: Z - P = 1 - 2 = -1 (the honest difference)
    assert mathops.cplx_argument_principle(z, (z - 0.5) / (z - 0.1) ** 2) == -1
    # orientation negates the count
    cw = mathops.cplx_contour_circle(0.0, 2.0, 512, orientation="cw")
    assert mathops.cplx_argument_principle(cw, mathops.cplx_poly_eval(p, cw)) == -3


def test_argument_principle_fail_closed():
    z = mathops.cplx_contour_circle(0.0, 1.0, 64)
    with pytest.raises(ValueError, match="vanishes at sample"):
        mathops.cplx_argument_principle(z, z - z[0])     # zero sitting on the path
    with pytest.raises(ValueError, match="same length"):
        mathops.cplx_argument_principle(z, z[:8])


def test_laurent_coefficients_and_residue_ground_truth():
    # f = 1/(z - a) with |a| < 1: c_-1 = 1 (the residue), c_-k = a^(k-1), c_k>=0 = 0
    z = mathops.cplx_contour_circle(0.0, 1.0, 64)
    out = mathops.cplx_laurent_coeffs(z, 1.0 / (z - 0.5), kmin=-3, kmax=2)
    k = list(out["k"])
    assert k == [-3, -2, -1, 0, 1, 2]
    assert out["c"][k.index(-1)] == pytest.approx(1.0, abs=1e-12)      # residue
    assert out["c"][k.index(-2)] == pytest.approx(0.5, abs=1e-12)
    assert out["c"][k.index(-3)] == pytest.approx(0.25, abs=1e-12)
    assert abs(out["c"][k.index(0)]) < 1e-12
    assert out["center"] == pytest.approx(0.0, abs=1e-15)
    assert out["radius"] == pytest.approx(1.0, abs=1e-15)
    # Taylor side: exp(z) has c_k = 1/k!
    out = mathops.cplx_laurent_coeffs(z, np.exp(z), kmin=0, kmax=5)
    fact = np.array([1.0, 1.0, 2.0, 6.0, 24.0, 120.0])
    assert np.allclose(out["c"].real, 1.0 / fact, atol=1e-12)
    assert np.allclose(out["c"].imag, 0.0, atol=1e-12)
    # the residue agrees with the contour integral / (2 pi i) on the same circle
    f = 1.0 / (z - 0.5)
    integral = mathops.cplx_contour_integral(z, f) / TWO_PI_I
    res = mathops.cplx_laurent_coeffs(z, f, -1, -1)["c"][0]
    # measured 1.6e-3 at n = 64: the gap IS the trapezoid's O(n^-2) error, since
    # the Fourier form converges geometrically — they agree to ~1e-9 at n = 512
    assert abs(integral - res) < 3e-3


def test_laurent_ignores_sample_order_unlike_the_integral():
    """Documented asymmetry: the coefficient sum runs over the sample *set*, so
    it always reports the positively-oriented coefficients; the contour integral
    follows the traversal and flips sign. Cross-checking the two without fixing
    orientation is the trap this pins."""
    z = mathops.cplx_contour_circle(0.0, 1.0, 128)
    cw = mathops.cplx_contour_circle(0.0, 1.0, 128, orientation="cw")
    res_ccw = mathops.cplx_laurent_coeffs(z, 1.0 / (z - 0.5), -1, -1)["c"][0]
    res_cw = mathops.cplx_laurent_coeffs(cw, 1.0 / (cw - 0.5), -1, -1)["c"][0]
    assert res_ccw == pytest.approx(1.0, abs=1e-12)
    assert res_cw == pytest.approx(1.0, abs=1e-12)          # NOT -1
    assert (mathops.cplx_contour_integral(cw, 1.0 / (cw - 0.5)) / TWO_PI_I).real < 0


def test_laurent_fail_closed():
    z = mathops.cplx_contour_circle(0.0, 1.0, 64)
    # a genuinely non-concyclic quadrilateral (note a square would be ACCEPTED:
    # its four corners really are a uniform 4-sample of its circumcircle)
    quad = np.array([0 + 0j, 1 + 0j, 1 + 1j, 0 + 3j])
    with pytest.raises(ValueError, match="not a circle"):
        mathops.cplx_laurent_coeffs(quad, np.ones(4), -1, 1)
    rect = np.array([0 + 0j, 2 + 0j, 2 + 1j, 0 + 1j])       # concyclic but not uniform
    with pytest.raises(ValueError, match="not uniformly"):
        mathops.cplx_laurent_coeffs(rect, np.ones(4), -1, 1)
    # unevenly spaced samples OF a real circle are caught one check earlier: the
    # centre is estimated as the sample mean, which only lands on the true centre
    # for uniform sampling, so the radii stop agreeing
    with pytest.raises(ValueError, match="not a circle"):
        mathops.cplx_laurent_coeffs(np.exp(1j * np.array([0.0, 0.1, 1.0, 3.0, 4.0, 5.0])),
                                    np.ones(6), -1, 1)
    with pytest.raises(ValueError, match="cannot resolve more"):
        mathops.cplx_laurent_coeffs(z, 1.0 / z, -100, 100)
    with pytest.raises(ValueError, match="must not exceed"):
        mathops.cplx_laurent_coeffs(z, 1.0 / z, 5, -5)
    with pytest.raises(ValueError, match="integer"):
        mathops.cplx_laurent_coeffs(z, 1.0 / z, -1.5, 2)


def test_laurent_overflowing_normaliser_raises_not_silent_zeros():
    """Adversarial finding (2026-09-01): r**k overflowed to inf for a tiny
    circle and a large negative order, and ``x / inf`` handed back a silent 0 —
    "no poles here" for a function full of them, with only a numpy
    RuntimeWarning (which conftest ignores) as evidence."""
    tiny = mathops.cplx_contour_circle(0.0, 1e-30, 64)
    with pytest.raises(ValueError, match="left float64 range"):
        mathops.cplx_laurent_coeffs(tiny, np.ones(64), kmin=-40, kmax=-1)
    # a representable radius/order pair still works: f = 1/z^2 on r = 1e-3
    small = mathops.cplx_contour_circle(0.0, 1e-3, 64)
    out = mathops.cplx_laurent_coeffs(small, 1.0 / small ** 2, kmin=-3, kmax=1)
    assert out["c"][list(out["k"]).index(-2)] == pytest.approx(1.0, abs=1e-9)


def test_joukowski_maps_the_circle_to_the_plate_and_the_ellipse():
    z = mathops.cplx_contour_circle(0.0, 1.0, 128)
    w = mathops.cplx_joukowski(z, 1.0)
    # |z| = c folds onto the segment [-2c, 2c]: w = 2 cos(t), exactly
    assert np.abs(w.imag).max() < 1e-14
    assert np.allclose(w.real, 2.0 * np.cos(np.angle(z)), atol=1e-14)
    assert w.real.min() == pytest.approx(-2.0, abs=1e-14)
    assert w.real.max() == pytest.approx(2.0, abs=1e-14)
    # R > c maps to the ellipse with semi-axes R + c^2/R and R - c^2/R
    for R in (2.0, 5.0):
        we = mathops.cplx_joukowski(mathops.cplx_contour_circle(0.0, R, 128), 1.0)
        a, b = R + 1.0 / R, R - 1.0 / R
        assert np.abs(we.real ** 2 / a ** 2 + we.imag ** 2 / b ** 2 - 1.0).max() < 1e-12


def test_joukowski_fail_closed():
    with pytest.raises(ValueError, match="pole"):
        mathops.cplx_joukowski(np.array([0 + 0j, 1 + 0j]))
    with pytest.raises(ValueError, match="positive real"):
        mathops.cplx_joukowski(np.array([1 + 0j]), c=0.0)
    with pytest.raises(ValueError, match="positive real"):
        mathops.cplx_joukowski(np.array([1 + 0j]), c=1j)
    with pytest.raises(ValueError, match="1-D"):
        mathops.cplx_joukowski(np.ones((2, 2), complex))


def test_mobius_cayley_and_inversion_ground_truth():
    # Cayley transform (z - i)/(z + i): real axis -> unit circle, i -> 0
    x = np.linspace(-50.0, 50.0, 501) + 0j
    w = mathops.cplx_mobius(x, 1.0, -1j, 1.0, 1j)
    assert np.abs(np.abs(w) - 1.0).max() < 1e-12
    assert abs(mathops.cplx_mobius(np.array([1j]), 1.0, -1j, 1.0, 1j)[0]) < 1e-15
    # inversion 1/z maps the unit circle onto itself
    z = mathops.cplx_contour_circle(0.0, 1.0, 64)
    assert np.abs(np.abs(mathops.cplx_mobius(z, 0.0, 1.0, 1.0, 0.0)) - 1.0).max() < 1e-14
    # identity coefficients really are the identity
    assert np.allclose(mathops.cplx_mobius(z, 1.0, 0.0, 0.0, 1.0), z, atol=1e-15)


def test_mobius_fail_closed():
    z = mathops.cplx_contour_circle(0.0, 1.0, 16)
    with pytest.raises(ValueError, match="degenerate"):
        mathops.cplx_mobius(z, 1.0, 2.0, 2.0, 4.0)       # ad - bc = 0: constant map
    with pytest.raises(ValueError, match="pole"):
        mathops.cplx_mobius(np.array([-1 + 0j, 0 + 0j]), 1.0, 0.0, 1.0, 1.0)
    with pytest.raises(ValueError, match="scalar"):
        mathops.cplx_mobius(z, np.ones(3), 0.0, 0.0, 1.0)


def test_cr_residual_separates_holomorphic_from_conjugate():
    x = np.linspace(-1.0, 1.0, 41)
    h = float(x[1] - x[0])
    X, Y = np.meshgrid(x, x)                 # rows = increasing imaginary axis
    Z = X + 1j * Y
    assert mathops.cplx_cr_residual(Z ** 2, spacing=h) < 1e-12      # exact to degree 2
    assert mathops.cplx_cr_residual(np.conj(Z), spacing=h) == pytest.approx(2.0, abs=1e-12)
    assert mathops.cplx_cr_residual(np.full((5, 5), 3 + 4j)) == 0.0  # constant: analytic
    # an image-convention array (rows running downward) measures the conjugate
    assert mathops.cplx_cr_residual((Z ** 2)[::-1], spacing=h) == pytest.approx(
        2.0, rel=0.2)


def test_cr_residual_is_second_order_in_the_grid():
    """Central differences are exact to degree 2, so z**3 shows the floor:
    measured 1.7e-3 at h and 4.2e-4 at h/2 — the O(h^2) rate, not a tolerance."""
    res = {}
    for n in (41, 81):
        x = np.linspace(-1.0, 1.0, n)
        h = float(x[1] - x[0])
        X, Y = np.meshgrid(x, x)
        res[n] = mathops.cplx_cr_residual((X + 1j * Y) ** 3, spacing=h)
    assert res[41] < 3e-3 and res[81] < 1e-3
    assert 3.5 < res[41] / res[81] < 4.5                 # measured 4.00


def test_cr_residual_fail_closed():
    with pytest.raises(ValueError, match="2-D"):
        mathops.cplx_cr_residual(np.ones(9))
    with pytest.raises(ValueError, match="at least 3x3"):
        mathops.cplx_cr_residual(np.ones((2, 5)))
    with pytest.raises(ValueError, match="positive real"):
        mathops.cplx_cr_residual(np.ones((4, 4)), spacing=0.0)
    with pytest.raises(ValueError, match="non-finite"):
        mathops.cplx_cr_residual(np.full((4, 4), np.nan))


def test_cplx_poly_eval_is_the_complex_twin_of_poly_eval():
    c = np.array([2.0, -3.0, 1.0])                       # 2x^2 - 3x + 1
    q = np.linspace(-2.0, 2.0, 7)
    assert np.allclose(mathops.cplx_poly_eval(c, q), mathops.poly_eval(c, q), atol=1e-15)
    assert isinstance(mathops.cplx_poly_eval(c, 2.0), complex)
    # roots evaluate to zero, including the complex ones poly_eval cannot take
    r = mathops.poly_roots([1.0, 0.0, 1.0])              # x^2 + 1 -> +-i
    assert np.abs(mathops.cplx_poly_eval([1.0, 0.0, 1.0], r)).max() < 1e-15
    with pytest.raises(ValueError, match="not finite"):
        mathops.cplx_poly_eval(np.full(400, 9.0), np.array([10.0 + 0j]))


def test_complex_family_rejects_text_instead_of_parsing_it():
    """Adversarial finding (2026-09-01): numpy parses "0" / b"0" / an array of
    "1j" strings straight into numbers, so a config string or a mis-decoded CSV
    column flowed through the whole family looking like data."""
    z = mathops.cplx_contour_circle(0.0, 1.0, 16)
    with pytest.raises(ValueError, match="text is not silently parsed"):
        mathops.cplx_winding_number(z, "0")
    with pytest.raises(ValueError, match="text is not silently parsed"):
        mathops.cplx_winding_number(z, b"0")
    with pytest.raises(ValueError, match="text/void dtype"):
        mathops.cplx_contour_integral(np.array(["0", "1", "1j"]), np.ones(3))
    with pytest.raises(ValueError, match="text/void dtype"):
        mathops.cplx_cr_residual(np.array([["1", "2", "3"]] * 3))


def test_complex_family_rejects_masked_and_nonfinite():
    z = mathops.cplx_contour_circle(0.0, 1.0, 16)
    m = np.ma.masked_array(z, mask=[True] + [False] * 15)
    with pytest.raises(ValueError, match="masked"):
        mathops.cplx_contour_integral(m, np.ones(16, complex))
    with pytest.raises(ValueError, match="non-finite"):
        mathops.cplx_winding_number(np.array([1 + 0j, np.inf + 0j, 1j]))
    # a masked array with nothing masked loses nothing -> accepted
    assert mathops.cplx_winding_number(np.ma.masked_array(z, mask=False), 0.0) == 1


def test_opsmath_complex_category_is_registered():
    import opsmath
    names = opsmath.list_ops("complex")
    assert len(names) == 10
    assert set(names) <= set(mathops.MATHOPS)
    assert opsmath.missing() == []
    # the declared output vocabulary is the one the chain fuzzer validates
    from tools.chain_fuzz import TYPE_CHECKS
    for n in names:
        assert opsmath.OPSMATH[n]["out"] in TYPE_CHECKS, n
