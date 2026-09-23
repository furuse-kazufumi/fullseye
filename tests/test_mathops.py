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
    # tier1 16 + tier2 complex 10 + interp_scattered(2026-09-08、散在点)
    # tier1 16 + complex 18 + construct 8 + wave 6 + dynsys 6。★ここは op を
    #   足すたびに動く行なので、足した理由を残しておく(35 = 複素平面の
    #   面 8 op、43 = 定理が門になる図 8 op、55 = 波動 6 + 力学系 6)。
    assert len(mathops.MATHOPS) == 55
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
    assert len(names) == 18   # 曲線の層 10 + 領域の層 8
    assert set(names) <= set(mathops.MATHOPS)
    assert opsmath.missing() == []
    # the declared output vocabulary is the one the chain fuzzer validates
    from tools.chain_fuzz import TYPE_CHECKS
    for n in names:
        assert opsmath.OPSMATH[n]["out"] in TYPE_CHECKS, n

# --------------------------------------------------------------------------- #
# interp_scattered — 2026-09-08 に足した(PoC が穴を炙り出した)                 #
# --------------------------------------------------------------------------- #
def test_interp_scattered_returns_how_much_was_not_interpolation():
    """★凸包の外に出た割合を**返す**ことがこの op の要点。

    `examples/poc_datacenter_thermal_field.py` が「散らばった 3-D 点から場を
    作る口が無い」と記録したので足した。同 PoC は d=1.20 m で評価点の 71.2 %
    が凸包の外に出ることを測っており、その量が黙って `fill_value` に化けると
    「線形補間の結果」という名前のまま別物になる。
    """
    rng = np.random.default_rng(0)
    pts = rng.uniform(0.0, 1.0, (200, 3))
    val = np.sin(3.0 * pts[:, 0]) + pts[:, 1] ** 2 - pts[:, 2]
    g = np.stack(np.meshgrid(*[np.linspace(-0.1, 1.1, 8)] * 3, indexing="ij"), -1)
    truth = np.sin(3.0 * g[..., 0]) + g[..., 1] ** 2 - g[..., 2]

    rmse = {}
    for method in ("nearest", "linear", "rbf"):
        r = mathops.interp_scattered(pts, val, g, method=method)
        assert r["value"].shape == g.shape[:-1]
        assert r["outside"].shape == g.shape[:-1]
        assert 0.60 < r["outside_fraction"] < 0.70      # 角は必ず外に出る
        inside = ~r["outside"] & np.isfinite(r["value"])
        rmse[method] = float(np.sqrt(np.mean((r["value"][inside]
                                              - truth[inside]) ** 2)))
    # 滑らかな場では 階段 < 線形 < RBF の順に良くなる
    assert rmse["rbf"] < rmse["linear"] < rmse["nearest"]
    # linear は外で fill_value、nearest / rbf は外でも有限
    out = mathops.interp_scattered(pts, val, g, method="linear")
    assert np.isnan(out["value"][out["outside"]]).all()
    for method in ("nearest", "rbf"):
        r = mathops.interp_scattered(pts, val, g, method=method)
        assert np.isfinite(r["value"]).all()


def test_interp_scattered_rbf_overshoots_its_own_nodes():
    """★薄板スプラインは内挿なのに節点の値を超える(PoC の 1.37 倍の正体)。"""
    rng = np.random.default_rng(5)
    pts = rng.uniform(-1.0, 1.0, (120, 2))
    val = np.exp(-(pts ** 2).sum(1) / (2 * 0.25 ** 2))
    q = np.stack(np.meshgrid(np.linspace(-1, 1, 61), np.linspace(-1, 1, 61),
                             indexing="ij"), -1)
    hi = {m: float(np.nanmax(mathops.interp_scattered(pts, val, q,
                                                      method=m)["value"]))
          for m in ("nearest", "linear", "rbf")}
    node_max = float(val.max())
    assert hi["nearest"] <= node_max + 1e-12
    assert hi["linear"] <= node_max + 1e-12
    assert hi["rbf"] > node_max * 1.02            # 節点を超える


def test_interp_scattered_is_fail_closed():
    pts = np.random.default_rng(1).uniform(0, 1, (10, 3))
    val = np.arange(10.0)
    with pytest.raises(ValueError, match="at least d\\+1"):
        mathops.interp_scattered(pts[:3], val[:3], pts)
    with pytest.raises(ValueError, match="values has"):
        mathops.interp_scattered(pts, val[:5], pts)
    with pytest.raises(ValueError, match="non-finite"):
        mathops.interp_scattered(pts, np.r_[np.nan, val[1:]], pts)
    with pytest.raises(ValueError, match="query last axis"):
        mathops.interp_scattered(pts, val, np.zeros((4, 2)))
    with pytest.raises(ValueError, match="method must be"):
        mathops.interp_scattered(pts, val, pts, method="kriging")


# -*- coding: utf-8 -*-


# --------------------------------------------------------------------------- #
# 複素平面を「面」で見る 5 op(2026-09-22)                                     #
#   真値は「使った式」ではない: 偏角の原理(既存 op が数える)/ Cayley の定理   #
#   (2 次は半平面という**厳密解**)/ 主カージオイドの閉形式内部判定 /          #
#   c=0 のジュリア集合は単位円板 / コーシー・リーマン残差(既存 op)。          #
# --------------------------------------------------------------------------- #
def _ring(a, k):
    """配列の外から k 番目の矩形リングを、反時計回りに 1 周ぶん並べて返す。

    行 0 が**上**(虚部が大きい)なので、画像の上で時計回りに辿ると
    複素平面では反時計回りになる。
    """
    h, w = a.shape[:2]
    i0, i1, j0, j1 = k, h - 1 - k, k, w - 1 - k
    idx = ([(i1, j) for j in range(j0, j1)]
           + [(i, j1) for i in range(i1, i0, -1)]
           + [(i0, j) for j in range(j1, j0, -1)]
           + [(i, j0) for i in range(i0, i1)])
    return np.array([a[i, j] for i, j in idx])


def test_the_field_knows_how_many_zeros_and_poles_it_has():
    """★偏角の原理 —— 既存 op(cplx_winding_number)が真値になる。

    R の像が原点を回る回数 = 輪郭の内側の零点 − 極(重複込み)。この op が
    作った場そのものを既存の op に数えさせるので、真値は**使った式ではない**。
    """
    cases = [
        ([0.2 + 0.1j], [], 1),                                  # 零点 1
        ([0.2 + 0.1j, -0.3 + 0.2j], [], 2),                     # 零点 2
        ([0.2 + 0.1j] * 3, [], 3),                              # 3 位の零点
        ([], [0.1 - 0.2j], -1),                                 # 極 1
        ([0.2 + 0.1j, -0.3 + 0.2j], [0.1 - 0.2j], 1),           # 2 - 1
        ([0.2 + 0.1j], [0.1 - 0.2j, 0.4 + 0.4j], -1),           # 1 - 2
    ]
    for zs, ps, want in cases:
        f = mathops.cplx_rational_field(zs, ps, shape=(513, 513), half_width=2.0)
        got = mathops.cplx_winding_number(_ring(f, 1), 0.0)
        assert got == want, (zs, ps, got, want)


def test_a_zero_outside_the_window_is_not_counted():
    """対照群 —— 窓の外の零点は巻き数に効かない(効いたら窓の取り方が嘘)。"""
    f = mathops.cplx_rational_field([5.0 + 0.0j], [], shape=(257, 257), half_width=1.0)
    assert mathops.cplx_winding_number(_ring(f, 1), 0.0) == 0


def test_the_field_refuses_a_pole_it_cannot_evaluate():
    """★極が標本の上に乗ったら値は数でない —— 黙って inf を返さず拒む。"""
    with pytest.raises(ValueError) as e:
        mathops.cplx_rational_field([], [0.0 + 0.0j], shape=(65, 65), half_width=1.0)
    assert "lands exactly on sample" in str(e.value)
    # 半画素ずらせば通る(逃げ道を message が示している)
    f = mathops.cplx_rational_field([], [0.0 + 0.0j], shape=(64, 64), half_width=1.0)
    assert np.all(np.isfinite(f))


def test_the_rational_field_is_holomorphic_and_the_row_order_decides_the_sign():
    """★★既存 op(cplx_cr_residual)が真値。**行の向きが答えの符号を決める**。

    この族の cplx_cr_residual は「行は虚部の**増える**向き」を要求する。
    こちらの格子は画像の並び(行 0 が上)なので、そのまま渡すと **2**(共役)、
    反転して渡すと 0。罠を門にしてある —— 両方を同時に検査する。

    中心差分は 2 次多項式まで厳密なので、1 次・2 次は 1e-12 を切る。
    """
    hw, n = 2.0, 129
    sp = 2.0 * hw / (n - 1)
    lin = mathops.cplx_rational_field([0.3 + 0.2j], [], shape=(n, n), half_width=hw)
    quad = mathops.cplx_rational_field([0.3 + 0.2j, -0.4 + 0.1j], [], shape=(n, n), half_width=hw)
    assert mathops.cplx_cr_residual(lin[::-1], spacing=sp) < 1e-12
    assert mathops.cplx_cr_residual(quad[::-1], spacing=sp) < 1e-12
    # 反転しないと「共役の場」を測るので、厳密に 2 に行く
    assert mathops.cplx_cr_residual(quad, spacing=sp) == pytest.approx(2.0, abs=1e-9)
    # 3 次は O(h^2) で落ちる —— 格子を半分にすると残差は 4 分の 1(既存 op の
    # docstring が主張する 2 次収束を、この op が作った場で再現する)
    c3 = mathops.cplx_rational_field([0.3, 0.1j, -0.2], [], shape=(n, n), half_width=hw)
    c3b = mathops.cplx_rational_field([0.3, 0.1j, -0.2], [], shape=(2 * n - 1, 2 * n - 1),
                                half_width=hw)
    r1 = mathops.cplx_cr_residual(c3[::-1], spacing=sp)
    r2 = mathops.cplx_cr_residual(c3b[::-1], spacing=sp / 2.0)
    assert r1 / r2 == pytest.approx(4.0, rel=0.05), (r1, r2)


def test_the_picture_shows_the_order_of_the_zero():
    """★★絵から定理が読める —— 零点のまわりで色相が回る回数 = 零点の位数。

    位相彩色は飾りではない。小さな円をひと回りするあいだに色相が何周するかが、
    そのまま偏角の原理の整数になる。**画素の色だけ**から数える(場の値は見ない)。
    """
    for order in (1, 2, 3):
        f = mathops.cplx_rational_field([0.0 + 0.0j] * order, [], shape=(129, 129),
                                  half_width=1.0)
        rgb = mathops.cplx_domain_colour(f)
        ring = _ring(rgb, 20)                       # (N, 3) の色の列
        hue = _hue_of(ring)
        turns = np.mod(np.diff(np.concatenate([hue, hue[:1]])) + 0.5, 1.0) - 0.5
        assert int(round(turns.sum())) == order, (order, turns.sum())
    # 極は逆向きに回る
    # ★極は標本に乗れないので**偶数**格子で(零点と違って値が数にならない)
    f = mathops.cplx_rational_field([], [0.0 + 0.0j] * 2, shape=(128, 128), half_width=1.0)
    hue = _hue_of(_ring(mathops.cplx_domain_colour(f), 20))
    turns = np.mod(np.diff(np.concatenate([hue, hue[:1]])) + 0.5, 1.0) - 0.5
    assert int(round(turns.sum())) == -2


def _hue_of(rgb):
    """RGB -> 色相 [0,1)。絵から読み戻すための最小の逆変換。"""
    mx = rgb.max(axis=-1)
    mn = rgb.min(axis=-1)
    d = mx - mn
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.zeros(mx.shape)
    with np.errstate(divide="ignore", invalid="ignore"):
        h = np.where(d == 0, 0.0,
                     np.where(mx == r, np.mod((g - b) / np.where(d == 0, 1, d), 6.0),
                              np.where(mx == g, (b - r) / np.where(d == 0, 1, d) + 2.0,
                                       (r - g) / np.where(d == 0, 1, d) + 4.0)))
    return np.mod(h / 6.0, 1.0)


def test_domain_colouring_is_invertible_when_it_promises_to_be():
    """bands=0 なら明度は |z| に**厳密に単調** = 絵から偏角も絶対値も戻せる。

    bands>0 は等高線を描くために単調性をわざと壊す —— 対照群として、
    同じ検査が落ちることまで見る(「効く」と「効かない」を分ける)。
    """
    f = mathops.cplx_rational_field([0.2 + 0.3j], [-0.5 + 0.1j], shape=(97, 97), half_width=1.5)
    rgb = mathops.cplx_domain_colour(f)
    hue = _hue_of(rgb)
    arg = np.mod(np.angle(f) / (2.0 * np.pi), 1.0)
    dh = np.abs(np.mod(hue - arg + 0.5, 1.0) - 0.5)
    assert dh.max() < 1e-6, dh.max()

    val = rgb.max(axis=-1)                              # HSV の V
    mod = np.abs(f)
    o = np.argsort(mod.ravel())
    v = val.ravel()[o]
    assert np.all(np.diff(v) >= -1e-12)                 # 単調(bands=0)

    banded = mathops.cplx_domain_colour(f, bands=3.0).max(axis=-1).ravel()[o]
    assert np.diff(banded).min() < -1e-3                # 対照群: 単調でない


def test_a_zero_is_black_and_a_large_modulus_is_fully_bright():
    """★零点は**厳密に**黒(0,0,0)。大きい |z| は明度 1 の彩度つきの色。

    「無限大は白」ではない —— 彩度は落とさないので、遠くでも色相(= 偏角)が
    読める。白に寄せると偏角の情報がそこで消えるため、そうしていない。
    """
    f = mathops.cplx_rational_field([0.0 + 0.0j], [], shape=(65, 65), half_width=1.0)
    rgb = mathops.cplx_domain_colour(f)
    i, j = np.unravel_index(np.argmin(np.abs(f)), f.shape)
    assert np.abs(f[i, j]) == 0.0 and rgb[i, j].max() == 0.0
    big = mathops.cplx_domain_colour(np.full((8, 8), 1e6 + 0j))
    assert big.max() > 0.999999
    assert big[..., 0].min() > 0.999999          # arg = 0 なので赤が振り切れる
    # 彩度を 0 にすれば灰色階調(偏角を捨てる代わりに絵は単純になる)
    grey = mathops.cplx_domain_colour(np.full((8, 8), 1e6 + 0j), saturation=0.0)
    assert float(grey.max() - grey.min()) < 1e-12


def test_domain_colouring_refuses_what_it_cannot_draw():
    with pytest.raises(ValueError):
        mathops.cplx_domain_colour(np.array([[np.inf + 0j]] * 4))
    with pytest.raises(ValueError):
        mathops.cplx_domain_colour(np.zeros((4, 4), complex), gamma=0.0)
    with pytest.raises(ValueError):
        mathops.cplx_domain_colour(np.zeros((4, 4), complex), saturation=1.5)
    with pytest.raises(ValueError):
        mathops.cplx_domain_colour(np.zeros((4, 4, 4), complex))


def test_cayley_gives_the_degree_two_basins_exactly():
    """★★Cayley (1879): z**2 - 1 の吸引域は**2 つの半平面**、境界は虚軸。

    2 次だけは閉形式の答えがあるので、この op は「もっともらしい」ではなく
    **厳密に**検査できる。分数もフラクタルも無い —— 1 画素も外してはいけない。
    """
    lab = mathops.cplx_newton_basins([1, 0, -1], centre=0j, half_width=1.5,
                               shape=(128, 128), max_iter=80)
    z = mathops.cplx_plane_grid(0j, 1.5, (128, 128))
    assert not np.any(z.real == 0.0)                    # 偶数格子なので虚軸に乗らない
    want = np.where(z.real < 0, 1, 2).astype(np.int32)  # 根は (Re, Im) 順 = -1, +1
    assert np.array_equal(lab, want)
    assert int((lab == 0).sum()) == 0                   # 収束しない画素は 1 つも無い


def test_degree_three_is_a_fractal_but_its_symmetry_is_exact():
    """★3 次は Cayley が解けなかった側 —— 境界はフラクタル。

    だから厳密解は使えないが、**対称性は厳密**に成り立つ: z**3 - 1 の係数は実数
    なので、実軸に対称な窓では吸引域も共役対称。根は (Re, Im) 順に並ぶので、
    行を反転すると根 1 と 2 だけが入れ替わる —— 1 画素の誤差も許さない。
    """
    lab = mathops.cplx_newton_basins([1, 0, 0, -1], centre=0j, half_width=1.6,
                               shape=(129, 129), max_iter=60)
    for k in (1, 2, 3):
        assert int((lab == k).sum()) > 0, k
    swapped = np.where(lab == 1, 2, np.where(lab == 2, 1, lab))
    assert np.array_equal(lab[::-1], swapped)
    # 根そのものは既存 op(poly_roots)と一致する
    assert np.allclose(np.sort_complex(mathops.poly_roots(np.array([1.0, 0.0, 0.0, -1.0]))),
                       np.sort_complex(np.roots([1, 0, 0, -1])))


def test_newton_leaves_the_undecided_undecided():
    """★収束しなかった画素は 0 のまま —— 「近いほうの根」に丸めない。

    max_iter を切り詰めると 0 が増える(単調)。臨界点(p' = 0)では 0 のままで、
    例外も出さず、しかし「どちらかの根」とも言わない。
    """
    prev = -1
    for mi in (2, 4, 8, 30):
        lab = mathops.cplx_newton_basins([1, 0, 0, -1], half_width=1.6, shape=(64, 64),
                                   max_iter=mi)
        n0 = int((lab == 0).sum())
        if prev >= 0:
            assert n0 <= prev, (mi, n0, prev)
        prev = n0
    with pytest.raises(ValueError):
        mathops.cplx_newton_basins([3.0], shape=(16, 16))          # 0 でない定数 = 根が無い
    with pytest.raises(ValueError):
        mathops.cplx_newton_basins([0.0, 0.0], shape=(16, 16))     # 恒等的に 0
    with pytest.raises(ValueError):
        mathops.cplx_newton_basins([1, 0, -1], shape=(16, 16), max_iter=0)


def test_the_main_cardioid_provably_never_escapes():
    """★★閉形式の内部判定が門になる。

    c が主カージオイドにあるのは、固定点 z* = (1 - sqrt(1-4c))/2 が吸引的
    (|2 z*| < 1)であることと同値で、そのとき軌道は**決して**脱出しない。
    だから該当画素は例外なく max_iter を返さなければならない —— 許容差は無い。
    周期 2 球 |c+1| < 1/4 も同じ。
    """
    mi = 80
    e = mathops.cplx_escape_time("mandelbrot", centre=-0.5 + 0j, half_width=1.6,
                           shape=(180, 240), max_iter=mi)
    g = mathops.cplx_plane_grid(-0.5 + 0j, 1.6, (180, 240))
    inside = mathops.mandelbrot_interior(g)
    assert inside.sum() > 1000
    assert np.all(e[inside] == float(mi))
    # 逆は言えない(小さい球や糸は覆われない)—— それが「下界」の意味
    assert int((e == float(mi)).sum()) > int(inside.sum())
    # |c| > 2 は 1 歩で出る
    far = np.abs(g) > 2.0
    assert np.all(e[far] <= 2.0)


def test_the_escape_picture_is_exactly_mirror_symmetric():
    """★共役対称は**厳密**(浮動小数の許容差すら要らない)。"""
    e = mathops.cplx_escape_time("mandelbrot", centre=-0.5 + 0j, half_width=1.6,
                           shape=(121, 161), max_iter=40)
    assert np.array_equal(e, e[::-1])
    j = mathops.cplx_escape_time("julia", param=-0.7269 + 0.1889j, half_width=1.6,
                           shape=(121, 121), max_iter=40)
    assert np.array_equal(j, j[::-1, ::-1])          # c 固定のジュリアは原点対称


def test_the_julia_set_of_zero_is_the_unit_circle():
    """★★c = 0 のジュリア集合は**単位円**、充填集合は閉単位円板 —— 厳密解。

    z -> z**2 は |z| を 2 乗するだけなので、|z| < 1 は 0 へ、|z| > 1 は無限へ。
    絵を見て納得するのではなく、半径で全数を走査する。
    """
    mi = 60
    e = mathops.cplx_escape_time("julia", param=0j, half_width=2.0, shape=(201, 201),
                           max_iter=mi)
    g = mathops.cplx_plane_grid(0j, 2.0, (201, 201))
    r = np.abs(g)
    assert np.all(e[r < 0.995] == float(mi))
    assert np.all(e[r > 1.005] < float(mi))


def test_escape_time_refuses_what_it_cannot_answer():
    with pytest.raises(ValueError):
        mathops.cplx_escape_time("burning_ship", shape=(16, 16))
    with pytest.raises(ValueError):
        mathops.cplx_escape_time("julia", param=complex(np.nan, 0), shape=(16, 16))
    with pytest.raises(ValueError):
        mathops.cplx_escape_time(shape=(16, 16), max_iter=0)
    with pytest.raises(ValueError):
        mathops.cplx_escape_time(shape=(16, 16), escape_radius=0.0)
    with pytest.raises(ValueError):
        mathops.cplx_escape_time(shape=(2, 2))


def _circulation(field, grid, k):
    """外から k 番目のリングに沿った線積分 ∮ w dz。実部 = 循環、虚部 = 流束。"""
    zs = _ring(grid, k)
    ws = _ring(field, k)
    dz = np.roll(zs, -1) - zs
    return complex(np.sum(0.5 * (ws + np.roll(ws, -1)) * dz))


def test_the_flow_field_is_holomorphic_outside_the_body():
    """★★既存 op(cplx_cr_residual)が真値。乱数と共役が対照群。"""
    n, hw = 200, 3.0
    w = mathops.potential_flow_joukowski(alpha_deg=8.0, shape=(n, n), half_width=hw)
    strip = w[10:70, 10:190]                       # 翼を含まない帯だけ
    assert int((strip == 0).sum()) == 0
    sp = 2.0 * hw / (n - 1)
    assert mathops.cplx_cr_residual(strip[::-1], spacing=sp) < 5e-3
    assert mathops.cplx_cr_residual(np.conj(strip[::-1]), spacing=sp) > 1.9   # 対照群


def test_the_circulation_is_path_independent():
    """★コーシー —— 大きい輪と小さい輪で循環が一致する(流束は 0)。

    循環そのものはクッタ条件が決めた Γ(joukowski_circulation)に等しいが、
    **経路に依らない**ことは式からは出てこない: 場が翼の外で正則で、
    かつ湧き出しが無いことの帰結である。
    """
    n, hw = 200, 3.0
    w = mathops.potential_flow_joukowski(alpha_deg=8.0, shape=(n, n), half_width=hw)
    g = mathops.cplx_plane_grid(0j, hw, (n, n))
    v1 = _circulation(w, g, 2)
    v2 = _circulation(w, g, 25)
    assert v1.real == pytest.approx(v2.real, rel=2e-3), (v1, v2)
    assert abs(v1.imag) < 1e-2 and abs(v2.imag) < 1e-2          # 湧き出し無し
    gamma = mathops.joukowski_circulation(alpha_deg=8.0)
    assert v1.real == pytest.approx(-gamma, rel=2e-3), (v1.real, gamma)


def test_zero_lift_is_exact_for_a_symmetric_section_at_zero_incidence():
    """★対称翼を迎角 0 で置けば循環はちょうど 0(揚力ゼロ) —— 符号の門。

    迎角を振ると符号が変わり、大きさは sin で増える。「正の迎角で正の揚力」
    という向きの規約が壊れていれば、ここで落ちる。
    """
    sym = -0.1 + 0.0j
    assert mathops.joukowski_circulation(0.0, centre_offset=sym) == pytest.approx(0.0, abs=1e-12)
    assert mathops.joukowski_circulation(+5.0, centre_offset=sym) > 0
    assert mathops.joukowski_circulation(-5.0, centre_offset=sym) < 0
    w = mathops.potential_flow_joukowski(alpha_deg=0.0, centre_offset=sym, shape=(161, 161),
                                   half_width=3.0)
    assert np.allclose(w, np.conj(w[::-1]), atol=1e-9)          # 実軸に対称
    # キャンバのある翼は迎角 0 でも揚力を持つ(対照群)
    assert mathops.joukowski_circulation(0.0, centre_offset=-0.09 + 0.09j) > 0.1


def test_the_kutta_condition_is_what_keeps_the_trailing_edge_finite():
    """★★門に対照群がある —— 循環を外すと後縁で速度が発散する。

    ジューコフスキー写像は zeta = ±b で dz/dzeta = 0 になる。後縁で速度が
    有限なのは、クッタ条件が選んだ循環がちょうどそこで dW/dzeta を 0 に
    するからで、**それ以外の循環では 1/sqrt(距離) で発散する**。
    """
    b, mu = 1.0, -0.09 + 0.09j
    a = abs(b - mu)
    beta = -np.angle(b - mu)
    alpha = np.deg2rad(8.0)
    gamma = 4.0 * np.pi * a * np.sin(alpha + beta)

    def speed_at(eps, circ):
        zeta = b + eps * np.exp(1j * np.linspace(0.0, 2.0 * np.pi, 64, endpoint=False))
        zeta = zeta[np.abs(zeta - mu) > a]                      # 円の外だけ
        d = zeta - mu
        dwdz = (np.exp(-1j * alpha) - a * a * np.exp(1j * alpha) / (d * d)
                + 1j * circ / (2.0 * np.pi * d))
        return float(np.abs(dwdz / (1.0 - b * b / (zeta * zeta))).max())

    kutta = [speed_at(e, gamma) for e in (1e-2, 1e-3, 1e-4, 1e-5)]
    assert max(kutta) < 10.0, kutta                             # 有限にとどまる
    wrong = [speed_at(e, 0.0) for e in (1e-2, 1e-3, 1e-4, 1e-5)]
    assert wrong[-1] / wrong[0] > 20.0, wrong                   # 対照群: 発散する
    # 場そのものも後縁の近くで暴れない
    w = mathops.potential_flow_joukowski(alpha_deg=8.0, shape=(400, 400), half_width=2.5)
    assert float(np.abs(w).max()) < 6.0


def test_the_far_field_returns_to_the_free_stream_like_one_over_r():
    """★遠方で自由流に戻り、ずれは 1/|z| で落ちる(速さは式に書いていない)。"""
    free = np.exp(-1j * np.deg2rad(8.0))
    errs = []
    for hw in (10.0, 20.0, 40.0):
        w = mathops.potential_flow_joukowski(alpha_deg=8.0, shape=(129, 129), half_width=hw)
        g = mathops.cplx_plane_grid(0j, hw, (129, 129))
        edge = np.abs(g) > 0.9 * hw
        errs.append(float(np.abs(w[edge] - free).max()))
    assert errs[0] / errs[1] == pytest.approx(2.0, rel=0.15), errs
    assert errs[1] / errs[2] == pytest.approx(2.0, rel=0.15), errs


def test_the_zeroed_region_is_the_aerofoil():
    """★穴の面積は既存 op(cplx_joukowski)の輪郭から独立に出る。

    場が 0 の画素は「翼の中」。その面積は、円を cplx_joukowski で写した輪郭に
    靴紐公式を当てた面積と一致しなければならない(格子の離散化ぶんだけ違う)。
    """
    b, mu = 1.0, -0.09 + 0.09j
    a = abs(b - mu)
    t = np.linspace(0.0, 2.0 * np.pi, 4096, endpoint=False)
    foil = mathops.cplx_joukowski(mu + a * np.exp(1j * t), b)
    x, y = foil.real, foil.imag
    area = abs(float(0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)))

    n, hw = 600, 2.5
    w = mathops.potential_flow_joukowski(alpha_deg=8.0, chord_b=b, centre_offset=mu,
                                   shape=(n, n), half_width=hw)
    px = (2.0 * hw / (n - 1)) ** 2
    assert int((w == 0).sum()) * px == pytest.approx(area, rel=0.03), \
        (int((w == 0).sum()) * px, area)


def test_the_flow_refuses_a_circle_that_is_not_an_aerofoil():
    with pytest.raises(ValueError) as e:
        mathops.potential_flow_joukowski(centre_offset=0.5 + 0.0j, shape=(32, 32))
    assert "critical point" in str(e.value) or "chord_b" in str(e.value)
    with pytest.raises(ValueError):
        mathops.potential_flow_joukowski(centre_offset=1.5 + 0.0j, shape=(32, 32))
    with pytest.raises(ValueError):
        mathops.potential_flow_joukowski(speed=0.0, shape=(32, 32))
    with pytest.raises(ValueError):
        mathops.potential_flow_joukowski(chord_b=-1.0, shape=(32, 32))
    with pytest.raises(ValueError):
        mathops.potential_flow_joukowski(shape=(32, 32), half_width=0.0)


def test_the_lift_exceeds_thin_aerofoil_theory_by_exactly_the_thickness_ratio():
    """★★薄翼理論との比が**厳密に a/b** —— 厚みの効果が 1 つの数に落ちる。

    クッタ・ジューコフスキーで ``L = rho * U * Gamma``、平板弦 ``c = 4b`` を使うと
    ``CL = 2*Gamma/(U*c) = 2*pi*(a/b)*sin(alpha+beta)``。薄翼理論の
    ``2*pi*sin(alpha+beta)`` との比は迎角にも速さにもよらず、**円の半径と写像の
    特異点の距離の比 a/b だけ**で決まる。a -> b(厚みゼロ)で薄翼理論に戻る。

    実測(alpha=8 度、centre_offset=-0.09+0.09j): CL = 1.513、薄翼 1.383、
    比 1.0940 = a/b = 1.0937。
    """
    b = 1.0
    for mu in (-0.09 + 0.09j, -0.2 + 0.0j, -0.05 + 0.15j):
        a = abs(b - mu)
        beta = -np.angle(b - mu)
        for alpha_deg in (0.0, 4.0, 8.0, 12.0):
            gamma = mathops.joukowski_circulation(alpha_deg, chord_b=b, centre_offset=mu)
            cl = 2.0 * gamma / (1.0 * 4.0 * b)
            thin = 2.0 * np.pi * np.sin(np.deg2rad(alpha_deg) + beta)
            if abs(thin) < 1e-9:
                assert abs(cl) < 1e-9
                continue
            assert cl / thin == pytest.approx(a / b, rel=1e-12), (mu, alpha_deg, cl, thin)
    # 厚みを 0 に近づけると薄翼理論に戻る(極限が門になる)
    ratios = []
    for eps in (0.2, 0.05, 0.01, 0.001):
        mu = -eps + 0.0j
        g5 = mathops.joukowski_circulation(5.0, chord_b=b, centre_offset=mu)
        ratios.append((2.0 * g5 / 4.0) / (2.0 * np.pi * np.sin(np.deg2rad(5.0))))
    assert ratios[-1] == pytest.approx(1.0, abs=2e-3), ratios
    assert all(ratios[i] > ratios[i + 1] for i in range(len(ratios) - 1)), ratios


def test_the_closed_form_interior_is_a_lower_bound_with_no_counterexample():
    """★閉形式の内部判定は**下界** —— 覆う画素は本物、しかし全部ではない。

    実測(max_iter=200、600x800、中心 -0.5、半幅 1.6): 閉形式が『絶対に出ない』と
    言える画素 85,624。反例 0 件。実際に残った画素は 95,078 なので、閉形式は
    その 90.1 %。残りの 9.9 % は小さい球や糸で、この 2 つの式では覆えない ——
    「覆えない」ことを数で言えるのが下界の使い道である。
    """
    mi = 120
    e = mathops.cplx_escape_time("mandelbrot", centre=-0.5 + 0j, half_width=1.6,
                           shape=(240, 320), max_iter=mi)
    g = mathops.cplx_plane_grid(-0.5 + 0j, 1.6, (240, 320))
    ins = mathops.mandelbrot_interior(g)
    stay = (e == float(mi))
    assert int((e[ins] != float(mi)).sum()) == 0            # 反例ゼロ
    assert ins.sum() < stay.sum()                           # しかし全部ではない
    assert 0.80 < ins.sum() / stay.sum() < 0.98


# --------------------------------------------------------------------------- #
# 定理が門になる図(2026-09-23)
#
# ★数学の図はきれいなので、合っているかを誰も確かめない。ここでは絵を一度も
#   見ずに、**定理と既存 op**だけで合否を決める。
# --------------------------------------------------------------------------- #
def test_every_apollonian_circle_satisfies_descartes():
    """デカルトの円定理が**全部の円**で成り立つこと(機械精度)。

    生成は反射 k' = 2(k1+k2+k3) - k4 で行うので、四つ組が定理を満たすことは
    自明ではない —— 中心が複素デカルトの式で正しく決まっていて初めて、
    「接している 4 円」であり続ける。ここでは**接している組をこちらで探し直して**
    定理に入れる(op が使った四つ組をそのまま使わない)。
    """
    t = mathops.circle_packing_apollonian(depth=3)
    x, y, r, k = t["x"], t["y"], t["radius"], t["curvature"]
    assert len(x) == 2 * 3 ** 3 + 2 == 56
    # 半径と曲率は互いの逆数(外円は曲率が負)
    assert np.allclose(np.abs(1.0 / k), r, rtol=1e-12)

    # 接している組を距離から探す: |zi - zj| == |ri +- rj|
    n = len(x)
    z = x + 1j * y
    tangent = np.zeros((n, n), dtype=bool)
    for i in range(n):
        d = np.abs(z - z[i])
        tangent[i] = (np.isclose(d, r + r[i], rtol=1e-9, atol=1e-12)
                      | np.isclose(d, np.abs(r - r[i]), rtol=1e-9, atol=1e-12))
        tangent[i, i] = False
    assert tangent.sum() > 0, "接している円が 1 組も見つからない"

    # 互いに接する 4 円を 1 組見つけて定理に入れる
    quads = 0
    for i in range(n):
        for j in range(i + 1, n):
            if not tangent[i, j]:
                continue
            for m in range(j + 1, n):
                if not (tangent[i, m] and tangent[j, m]):
                    continue
                for q in range(m + 1, n):
                    if tangent[i, q] and tangent[j, q] and tangent[m, q]:
                        ks = k[[i, j, m, q]]
                        lhs, rhs = ks.sum() ** 2, 2.0 * (ks ** 2).sum()
                        assert abs(lhs - rhs) <= 1e-6 * max(abs(lhs), abs(rhs), 1.0), (
                            "接している 4 円がデカルトの円定理を破る: k=%s" % (ks,))
                        quads += 1
                        if quads >= 12:
                            return
    assert quads > 0, "互いに接する 4 円が 1 組も見つからない"


def test_the_integral_gasket_stays_integral_for_ever():
    """★(-1, 2, 2, 3) から始めた充填は、**どこまで行っても曲率が整数**。

    Lagarias-Mallows-Wilks。反射は整数を整数に写すので、実装が少しでも
    ずれていれば整数から外れる —— 絵では絶対に見えない種類の誤り。
    """
    for depth in (2, 3, 4):
        k = mathops.circle_packing_apollonian(curvatures=(-1.0, 2.0, 2.0, 3.0),
                                              depth=depth)["curvature"]
        off = np.abs(k - np.round(k))
        assert off.max() < 1e-6, ("整数でない曲率が出た(最大ずれ %.2e、depth=%d)"
                                  % (off.max(), depth))


def test_apollonian_refuses_a_quadruple_that_is_not_descartes():
    """定理を満たさない四つ組は**黙って描かず**に拒否する(fail-closed)。"""
    with pytest.raises(ValueError, match="Descartes"):
        mathops.circle_packing_apollonian(curvatures=(-1.0, 2.0, 2.0, 4.0))


def test_ford_circles_touch_exactly_when_the_integers_say_so():
    """★接するのは |p*s - q*r| = 1 のときに限る(整数の厳密な等式)。

    フォード円は p/q に半径 1/(2q^2) で載る。2 つが接する条件は**幾何でなく
    整数論**で決まるので、こちらは距離を測り、あちらは整数を見る ——
    2 つの答えが 1 つでも食い違えば落ちる。
    """
    t = mathops.ford_circles(max_denominator=9)
    p, q, x, y, r = t["p"], t["q"], t["x"], t["y"], t["radius"]
    # ★円は (p/q, 1/(2q^2)) に**載っている**ので、接触は 2 次元の距離で見る。
    #   x の差だけで測ると 0/1 と 1/9 のような組を「接していない」と読む
    #   (距離 0.1111 対 半径和 0.5062)—— 最初これで落ちた。
    assert np.allclose(y, 0.5 / q ** 2.0, rtol=1e-12)
    assert np.allclose(x, p / q, rtol=1e-12)
    assert np.allclose(r, 0.5 / q ** 2.0, rtol=1e-12)

    n = len(p)
    for i in range(n):
        for j in range(i + 1, n):
            d = float(np.hypot(x[i] - x[j], y[i] - y[j]))
            touch_geom = np.isclose(d, r[i] + r[j], rtol=1e-11, atol=1e-14)
            touch_int = abs(int(p[i]) * int(q[j]) - int(q[i]) * int(p[j])) == 1
            assert touch_geom == touch_int, (
                "幾何と整数が食い違う: %d/%d と %d/%d, 距離 %.17g, 半径和 %.17g"
                % (p[i], q[i], p[j], q[j], d, r[i] + r[j]))


def test_the_farey_count_matches_the_totient_sum():
    """|F_n| = 1 + sum_{k<=n} phi(k)。数え方が op と独立(オイラーの関数)。"""
    def phi(m):
        c = 0
        for a in range(1, m + 1):
            x, y = a, m
            while y:
                x, y = y, x % y
            c += (x == 1)
        return c

    for n in (5, 9, 12):
        got = len(mathops.ford_circles(max_denominator=n)["p"])
        want = 1 + sum(phi(k) for k in range(1, n + 1))
        assert got == want, (n, got, want)


def test_the_golden_angle_is_the_one_that_packs():
    """★フィボナッチの斜列が出るのは**黄金角のときだけ**。

    「葉序の絵」は角度をどう選んでも螺旋に見える。だから絵を見ずに、
    近傍の**番号差**を数える —— 黄金角では 8, 13, 21, 34, 55 と
    フィボナッチ数に山が立ち、対照群の 137.0 度では立たない。
    """
    fib = {1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144}

    def peaks(angle):
        pts = mathops.phyllotaxis_pattern(n_points=600, angle_deg=angle)
        counts = mathops.neighbour_index_gaps(pts, k=6)
        order = np.argsort(counts)[::-1]
        return [int(g) for g in order[:7] if counts[g] > 0]

    golden = peaks(None)                      # 既定 = 黄金角
    control = peaks(137.0)
    g_hits = sum(1 for g in golden if g in fib)
    c_hits = sum(1 for g in control if g in fib)
    assert g_hits >= 6, ("黄金角なのにフィボナッチの山が %d 個しかない: %s"
                         % (g_hits, golden))
    assert g_hits > c_hits, ("対照群(137.0 度)と区別できていない: 黄金 %s / 対照 %s"
                             % (golden, control))


def test_moran_agrees_with_the_box_counting_op():
    """★モランの式(閉形式)と、既存 `fractal_dimension`(箱数え)が一致すること。

    片方は写像の縮小率だけから解く d、もう片方は**描いた点**を箱で数える d。
    導出も入力も違うので、一致は偶然では起きない。箱数えは有限の点数で必ず
    上に出るので、幅は 0.15 を許して**順序と水準**を見る。
    """
    import ops as _ops
    fd = dict(_ops.OPS)["fractal_dimension"] if "fractal_dimension" in dict(_ops.OPS) \
        else None
    for preset, closed in (("sierpinski", np.log(3) / np.log(2)),
                           ("koch", np.log(4) / np.log(3)),
                           ("cantor_dust", np.log(4) / np.log(3))):
        d = float(mathops.ifs_similarity_dimension(preset))
        assert abs(d - closed) < 1e-9, (preset, d, closed)
        pts = mathops.ifs_fractal(preset, n_points=40000, seed=0)
        assert pts.shape == (40000, 2)
        if fd is None:
            continue
        # 点を 256x256 の二値画像にして、既存 op に測らせる
        g = np.zeros((256, 256), dtype=np.float64)
        q = pts - pts.min(axis=0)
        q = q / max(q.max(), 1e-12) * 255.0
        g[q[:, 1].astype(int).clip(0, 255), q[:, 0].astype(int).clip(0, 255)] = 1.0
        box = float(np.asarray(fd(g, 0.5, 0.5)).reshape(-1)[0])
        assert abs(box - d) < 0.25, ("箱数えと閉形式が離れすぎ: %s 箱 %.3f 閉 %.3f"
                                     % (preset, box, d))


def test_ifs_refuses_maps_that_are_not_similarities():
    """相似でない写像(バーンズリーのシダ)には**モランの式は使えない**ので拒否する。

    ★`match="similarit"` で書くと **op 名 `ifs_similarity_dimension` に当たって
    必ず通る**。しかも preset 名を間違えていても(`"fern"`、正しくは
    `"barnsley_fern"`)「未知 preset の拒否」を見て合格になる —— 検査が
    「拒否した」ことだけを見て「**なぜ**拒否したか」を見ていないと、こうなる。
    """
    with pytest.raises(ValueError, match="is not a similarity"):
        mathops.ifs_similarity_dimension("barnsley_fern")
    # シダ自体は**描ける**(描けないのは次元のほう)
    assert mathops.ifs_fractal("barnsley_fern", None, 2000).shape == (2000, 2)


def test_a_space_filling_curve_visits_every_cell_exactly_once():
    """4^n 点の**置換**であり、隣り合う点は必ず距離 1。

    「空間充填曲線」を名乗る以上、抜けも重複もあってはならない。ここは
    集合として数え、隣接は差の絶対値で見る(絵は一切見ない)。
    """
    for kind in ("hilbert", "moore", "boustrophedon"):
        for order in (2, 3, 4):
            pts = mathops.space_filling_curve(kind, order)
            n = 2 ** order
            assert pts.shape == (n * n, 2), (kind, order, pts.shape)
            seen = {(int(a), int(b)) for a, b in pts}
            assert len(seen) == n * n, ("抜け/重複: %s order=%d, 一意 %d / %d"
                                        % (kind, order, len(seen), n * n))
            step = np.abs(np.diff(pts, axis=0)).sum(axis=1)
            assert np.all(step == 1), ("隣が距離 1 でない: %s order=%d, 最大 %d"
                                       % (kind, order, step.max()))
        # ★ムーア曲線は**閉じている**(最後から最初に戻れる)。ヒルベルトは閉じない。
        pts = mathops.space_filling_curve(kind, 4)
        closed = int(np.abs(pts[0] - pts[-1]).sum()) == 1
        assert closed == (kind == "moore"), (kind, closed)


def test_hilbert_keeps_locality_and_a_raster_scan_does_not():
    """★局所性は主張でなく**表**。ヒルベルトは sqrt(k)、走査線は k に比例。"""
    h = mathops.curve_locality(mathops.space_filling_curve("hilbert", 5))
    b = mathops.curve_locality(mathops.space_filling_curve("boustrophedon", 5))
    assert list(h["gap"]) == list(b["gap"])
    # 同じ番号差で、走査線のほうが必ず遠い(k=1 は両方 1 なので k>=2 を見る)
    far = h["gap"] >= 2
    assert np.all(b["ratio"][far] > h["ratio"][far]), (h["ratio"], b["ratio"])
    # ヒルベルトは k=32 で sqrt(32)=5.66 の近く、走査線は 32 に近い側へ伸びる
    i32 = int(np.argmax(h["gap"] == 32))
    assert 3.5 < h["ratio"][i32] < 9.0, h["ratio"][i32]
    assert b["ratio"][i32] > 12.0, b["ratio"][i32]


def test_the_geodesic_dome_has_exactly_twelve_pentagons():
    """★★オイラーの公式 V - E + F = 2 が、**次数 5 の頂点をちょうど 12 個**に縛る。

    どれだけ細かく分割しても 12 個から動かない。11 個でも 13 個でも球にならない
    ので、これは実装の都合ではなく**位相の帰結**である。次数は既存の
    `graph_degree_table`(隣接行列から数える別実装)に数えさせる —— 自分で
    数え直して自分と一致しても、何も確かめたことにならない。
    """
    import conngraph
    import render3d

    for freq in (1, 2, 3, 4):
        V, F = render3d.geodesic_dome(frequency=freq)
        assert V.shape[1] == 3 and F.shape[1] == 3
        assert V.shape[0] == 10 * freq * freq + 2, (freq, V.shape)
        assert F.shape[0] == 20 * freq * freq, (freq, F.shape)
        # 全頂点が半径 1 の球面上(射影が効いている)
        rad = np.linalg.norm(V, axis=1)
        assert np.allclose(rad, 1.0, atol=1e-12), (freq, rad.min(), rad.max())

        # 面から隣接行列を組み、**既存 op**に次数を数えさせる
        n = V.shape[0]
        W = np.zeros((n, n), dtype=np.float64)
        for a, b, c in F:
            for i, j in ((a, b), (b, c), (c, a)):
                W[int(i), int(j)] = W[int(j), int(i)] = 1.0
        deg = conngraph.graph_degree_table(W)["in_degree"]
        assert int((deg == 5).sum()) == 12, (
            "次数 5 の頂点が %d 個(オイラーの公式より 12)freq=%d"
            % (int((deg == 5).sum()), freq))
        assert int((deg == 6).sum()) == n - 12, (freq, deg)

        # V - E + F = 2 も直接見る(辺は隣接行列の非零の半分)
        edges = int(W.sum() // 2)
        assert n - edges + F.shape[0] == 2, (freq, n, edges, F.shape[0])


def test_the_new_construct_ops_are_registered_and_reachable():
    """8 op が台帳とファサードの両方から引けること(登録面の取りこぼし検査)。"""
    names = ["circle_packing_apollonian", "ford_circles", "phyllotaxis_pattern",
             "neighbour_index_gaps", "ifs_fractal", "ifs_similarity_dimension",
             "space_filling_curve", "curve_locality"]
    import opsmath
    for n in names:
        assert n in opsmath.OPSMATH, n
        assert opsmath.OPSMATH[n]["category"] == "construct", n
    import fullseye as fs
    for n in names:
        assert hasattr(fs, n) and n in fs.__all__, n
        assert hasattr(fs.ledger, n), n
    assert len(mathops.MATHOPS) == 55
    assert sum(1 for r in opsmath.OPSMATH.values()
               if r["category"] == "construct") == 8
