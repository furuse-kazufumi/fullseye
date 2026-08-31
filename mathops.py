# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Mathematics operators for visual metrology (numpy + scipy only).

The math that *underwrites* Fullseye's measurements. A camera calibration is a
least-squares problem, a noise cloud is a covariance matrix, a principal axis is
an eigenvector, a distortion model is a polynomial, an inverse lookup is an
interpolation — every metrology op in :mod:`measure` / :mod:`measure3d` /
:mod:`camera` quietly runs on this layer. This module surfaces it as first-class
operators, in three families:

  * **linalg** — ``mat_solve`` / ``mat_lstsq`` / ``mat_svd`` / ``mat_eigh`` /
    ``mat_pinv`` / ``mat_cond``: dense linear algebra with the numerical-health
    telltale (``mat_cond``) made explicit instead of hidden.
  * **stats**  — ``stat_describe`` / ``stat_histogram`` / ``stat_covariance`` /
    ``stat_correlation`` / ``stat_zscore``: residual and noise characterisation.
  * **interp / poly** — ``interp_linear`` / ``interp_cubic`` / ``poly_fit`` /
    ``poly_eval`` / ``poly_roots``: calibration curves and their inversion.

Deliberately **not** here (already owned elsewhere — no duplication): FFT /
complex arithmetic (:mod:`complexops`, :mod:`volfreq`, :mod:`dsp`), 1-D signal
filtering (:mod:`dsp`, :mod:`funct1d`), geometry fits (:mod:`measure`,
:mod:`measure3d`, :mod:`pcseg`), and the general-algorithm tier's numerics
(:mod:`algo`: Simpson / bisection / Newton / Gauss elimination — those are
*codegen references*; this module is the production numpy path).

HALCON correspondence (cited per function): HALCON's *Matrix* chapter
(``create_matrix`` / ``solve_matrix`` / ``svd_matrix`` /
``eigenvalues_symmetric_matrix`` / ``invert_matrix`` / ``norm_matrix``) covers
the linalg family; its *Tuple* chapter (``tuple_mean`` / ``tuple_deviation`` /
``tuple_min`` / ``tuple_max`` / ``tuple_histo_range``) covers the descriptive
stats; the *Funct1D* chapter interpolates on function pairs
(``get_y_value_funct_1d`` — see :mod:`funct1d`). HALCON has **no** public tuple
operator for covariance / correlation matrices, polynomial fitting, or root
finding — those live inside its calibration internals; here they are explicit.

Frame convention: a *matrix* is strictly 2-D, a *vector* strictly 1-D, a sample
set is ``(N, D)`` (rows = observations, columns = variables). **No silent
broadcast, promotion or truncation**: a 1-D array handed to a matrix slot (or
vice versa) raises ``ValueError`` — silent shape coercion is exactly the bug
family the 2026-08 adversarial audits kept finding.

Honest numerical disclosure (the traps, stated up front):

  * **Eigenvector / singular-vector sign is indeterminate.** ``mat_eigh`` and
    ``mat_svd`` return vectors defined only up to sign (and up to rotation
    within a degenerate eigen/singular subspace). Two runs, two LAPACK builds,
    or two platforms may flip signs. Compare subspaces (or ``|v·w|``), never raw
    vector equality.
  * **A large condition number means digits are already lost.** A linear solve
    loses roughly ``log10(cond(A))`` significant digits (Golub & Van Loan,
    *Matrix Computations*, §2.6): at ``cond > 1e12`` a float64 answer keeps at
    best ~3 digits — do not trust ``mat_solve`` there; check :func:`mat_cond`
    first, and prefer :func:`mat_lstsq` / :func:`mat_pinv` with an explicit
    ``rcond`` for rank-deficient systems.
  * **High-degree polynomial fits oscillate (Runge phenomenon)** and their
    Vandermonde matrices are notoriously ill-conditioned — the classical
    equispaced-node divergence (Runge 1901). :func:`poly_fit` therefore reports
    the Vandermonde condition number and *warns* past ``POLY_COND_WARN``;
    treat degree > ~6 on raw coordinates as a smell (centre/scale x first).
  * ``mat_eigh`` accepts **symmetric input only** and verifies it. Feeding a
    non-symmetric matrix to a symmetric eigensolver silently uses one triangle
    — the answer looks plausible and is wrong; a general matrix also has
    complex eigenvalues this API cannot represent. Fail-closed instead.

Fail-closed on untrusted input, like every Fullseye module: exact
dimensionality, NaN/Inf rejected everywhere, singular / constant / empty /
out-of-range cases raise an explicit ``ValueError`` naming the problem — never
a silent NaN, a silent clamp, or a silent zero-division.
"""
from __future__ import annotations

import warnings

import numpy as np

__all__ = [
    "mat_solve", "mat_lstsq", "mat_svd", "mat_eigh", "mat_pinv", "mat_cond",
    "stat_describe", "stat_histogram", "stat_covariance", "stat_correlation",
    "stat_zscore",
    "interp_linear", "interp_cubic", "poly_fit", "poly_eval", "poly_roots",
    "MATHOPS", "MAX_ELEMENTS", "POLY_COND_WARN",
]

#: The public math operators, by name (introspection / facade wiring).
MATHOPS = [
    "mat_solve", "mat_lstsq", "mat_svd", "mat_eigh", "mat_pinv", "mat_cond",
    "stat_describe", "stat_histogram", "stat_covariance", "stat_correlation",
    "stat_zscore",
    "interp_linear", "interp_cubic", "poly_fit", "poly_eval", "poly_roots",
]

#: Refuse an array larger than this (~67M float64 = 512 MB) — the SVD/eigen
#: routines allocate several same-size temporaries; a bigger problem should go
#: to a purpose-built solver, not this metrology support layer.
MAX_ELEMENTS = 1 << 26

#: :func:`poly_fit` emits a ``RuntimeWarning`` when the Vandermonde condition
#: number exceeds this (≈10 of 16 float64 digits already gone).
POLY_COND_WARN = 1e10


# --------------------------------------------------------------------------- #
# fail-closed input helpers                                                    #
# --------------------------------------------------------------------------- #
def _as_float64(a, name: str) -> np.ndarray:
    """Coerce to contiguous float64, rejecting inputs that would lose data.

    Two silent-truncation traps (both raise ``ValueError``): a **complex**
    input would have its imaginary part discarded (numpy emits only a
    ``ComplexWarning`` and returns a plausible-wrong real answer), and a
    **masked array with masked entries** would have the mask stripped and the
    underlying raw values used as if they were valid data."""
    if np.ma.is_masked(a):
        raise ValueError("%s is a masked array with masked (invalid) entries — "
                         "coercion would silently strip the mask and use the "
                         "raw values underneath; fill or drop them explicitly"
                         % (name,))
    if np.iscomplexobj(a):
        raise ValueError("%s is complex — coercion to float64 would silently "
                         "discard the imaginary part (a plausible-wrong real "
                         "answer); take .real/.imag/abs() explicitly, or use "
                         "the complex-capable ops in complexops" % (name,))
    return np.ascontiguousarray(a, dtype=np.float64)


def _require_finite(a: np.ndarray, name: str) -> None:
    if not np.isfinite(a).all():
        n = int((~np.isfinite(a)).sum())
        raise ValueError("%s has %d non-finite value(s) (NaN/Inf) — refusing "
                         "(they would propagate through every result)" % (name, n))


def _check_elements(a: np.ndarray, op: str) -> None:
    if a.size > MAX_ELEMENTS:
        raise ValueError("%s: %d elements (shape %r) exceeds the %d cap "
                         "(mathops.MAX_ELEMENTS)" % (op, a.size, a.shape, MAX_ELEMENTS))


def _require_matrix(a, name: str = "a") -> np.ndarray:
    """Coerce to a strictly 2-D float64 matrix or raise ``ValueError``.

    A 1-D vector is **not** silently promoted to a row/column — the caller must
    say what it means (silent shape coercion is a confirmed bug family).
    Complex input and masked entries are rejected (silent truncation)."""
    m = _as_float64(a, name)
    if m.ndim != 2:
        raise ValueError("%s must be a 2-D matrix, got a %d-D array of shape %r "
                         "— reshape explicitly, nothing is promoted silently"
                         % (name, m.ndim, tuple(np.shape(a))))
    if m.shape[0] == 0 or m.shape[1] == 0:
        raise ValueError("%s must be non-empty, got shape %r" % (name, m.shape))
    _require_finite(m, name)
    return m


def _require_vector(v, name: str = "v", min_len: int = 1) -> np.ndarray:
    """Coerce to a strictly 1-D float64 vector or raise ``ValueError``."""
    a = _as_float64(v, name)
    if a.ndim != 1:
        raise ValueError("%s must be a 1-D vector, got a %d-D array of shape %r "
                         "— flatten/reshape explicitly, nothing is coerced silently"
                         % (name, a.ndim, tuple(np.shape(v))))
    if a.size < min_len:
        raise ValueError("%s needs at least %d element(s), got %d"
                         % (name, min_len, a.size))
    _require_finite(a, name)
    return a


def _require_rhs(b, rows: int, name: str = "b") -> np.ndarray:
    """A right-hand side: 1-D ``(rows,)`` or 2-D ``(rows, k)`` — nothing else."""
    a = np.ascontiguousarray(b, dtype=np.float64)
    if a.ndim not in (1, 2):
        raise ValueError("%s must be a 1-D (n,) or 2-D (n, k) right-hand side, "
                         "got a %d-D array" % (name, a.ndim))
    if a.shape[0] != rows:
        raise ValueError("%s has %d row(s) but the matrix has %d — refusing to "
                         "broadcast" % (name, a.shape[0], rows))
    _require_finite(a, name)
    return a


def _require_samples(x, name: str = "x") -> np.ndarray:
    """An ``(N, D)`` sample matrix (rows = observations) with ``N >= 2``."""
    a = _require_matrix(x, name)
    if a.shape[0] < 2:
        raise ValueError("%s needs at least 2 observations (rows), got %d — "
                         "covariance/correlation of a single sample is undefined"
                         % (name, a.shape[0]))
    return a


def _query_points(xq, name: str = "xq"):
    """A query: a finite scalar or a 1-D array. Returns ``(array, is_scalar)``."""
    a = np.asarray(xq, dtype=np.float64)
    if a.ndim == 0:
        if not np.isfinite(a):
            raise ValueError("%s must be finite, got %r" % (name, xq))
        return a.reshape(1), True
    if a.ndim != 1:
        raise ValueError("%s must be a scalar or a 1-D array, got a %d-D array"
                         % (name, a.ndim))
    _require_finite(a, name)
    return np.ascontiguousarray(a), False


# --------------------------------------------------------------------------- #
# linalg                                                                       #
# --------------------------------------------------------------------------- #
def mat_solve(a, b):
    """Solve the square linear system ``A x = b`` (LAPACK ``gesv``, LU with
    partial pivoting).

    *a* must be square ``(n, n)``; *b* is ``(n,)`` or ``(n, k)`` (multiple
    right-hand sides). An exactly singular *A* raises ``ValueError``.

    **Do not trust the answer of an ill-conditioned system**: a solve loses
    about ``log10(cond(A))`` significant digits, so at ``cond > 1e12`` maybe 3
    of float64's ~16 digits survive — and *this function cannot tell you that*,
    because a near-singular system still "solves". Check :func:`mat_cond`
    first; for a rank-deficient or noisy system use :func:`mat_lstsq` /
    :func:`mat_pinv` with an explicit ``rcond`` instead.

    HALCON: ``solve_matrix``. Returns float64, same trailing shape as *b*.
    """
    A = _require_matrix(a, "a")
    _check_elements(A, "mat_solve")
    if A.shape[0] != A.shape[1]:
        raise ValueError("mat_solve needs a square matrix, got shape %r — for an "
                         "over-determined system use mat_lstsq" % (A.shape,))
    B = _require_rhs(b, A.shape[0])
    try:
        x = np.linalg.solve(A, B)
    except np.linalg.LinAlgError:
        raise ValueError("mat_solve: matrix is singular (exactly rank-deficient) "
                         "— no unique solution; use mat_lstsq/mat_pinv for a "
                         "minimum-norm answer") from None
    return np.ascontiguousarray(x, dtype=np.float64)


def mat_lstsq(a, b, rcond=None):
    """Least-squares solution of an over-determined system ``A x ≈ b``
    (LAPACK ``gelsd``, SVD-based).

    *a* is ``(m, n)`` with ``m >= n`` (at least as many equations as unknowns;
    an under-determined system is refused — its minimum-norm answer is a
    different question, ask :func:`mat_pinv`). *b* is ``(m,)`` or ``(m, k)``.
    *rcond* is the singular-value cutoff relative to the largest (``None`` =
    numpy's machine-precision default); singular values below it are treated
    as zero, which is what keeps a noisy rank-deficient fit stable.

    Returns a dict — the fit **and** its honesty telemetry together:

    ``x`` solution ``(n,)`` or ``(n, k)`` · ``residual_ss`` sum of squared
    residuals ``||b - A x||²`` (float, or ``(k,)`` per column — computed
    explicitly, so it is present even when the matrix is rank-deficient) ·
    ``rank`` effective rank at *rcond* · ``singular_values`` of *A*
    (descending). ``rank < n`` means the data does not determine every
    parameter — report that, don't hide it.

    HALCON: ``solve_matrix`` on a non-square system (same normal-equation
    machinery behind ``vector_to_hom_mat2d`` and friends).
    """
    A = _require_matrix(a, "a")
    _check_elements(A, "mat_lstsq")
    m, n = A.shape
    if m < n:
        raise ValueError("mat_lstsq needs m >= n (over-determined or square), got "
                         "shape %r — an under-determined system has infinitely "
                         "many solutions; use mat_pinv for the minimum-norm one"
                         % (A.shape,))
    B = _require_rhs(b, m)
    if rcond is not None:
        rc = float(rcond)
        if not np.isfinite(rc) or rc < 0.0:
            raise ValueError("rcond must be a non-negative finite float or None, "
                             "got %r" % (rcond,))
    else:
        rc = None
    x, _res, rank, sv = np.linalg.lstsq(A, B, rcond=rc)
    resid = B - A @ x
    residual_ss = (resid * resid).sum(axis=0)
    return {
        "x": np.ascontiguousarray(x, dtype=np.float64),
        "residual_ss": (float(residual_ss) if residual_ss.ndim == 0
                        else np.ascontiguousarray(residual_ss, dtype=np.float64)),
        "rank": int(rank),
        "singular_values": np.ascontiguousarray(sv, dtype=np.float64),
    }


def mat_svd(a, full_matrices=False):
    """Singular value decomposition ``A = U @ diag(s) @ Vt`` (LAPACK ``gesdd``).

    Returns ``(U, s, Vt)`` with ``s`` descending and non-negative. With the
    default ``full_matrices=False`` the *thin* SVD is returned (``U`` is
    ``(m, r)``, ``Vt`` is ``(r, n)``, ``r = min(m, n)``) — enough to
    reconstruct ``A`` exactly and what every rank/PCA use wants; pass ``True``
    for the full orthogonal bases.

    **Sign trap (honest)**: each singular-vector pair ``(u_i, v_i)`` is defined
    only up to a simultaneous sign flip, and vectors within a *degenerate*
    (equal-``s``) block only up to rotation. Assert on ``s``, on
    ``U diag(s) Vt``, or on projectors — never on raw ``U``/``Vt`` entries.

    HALCON: ``svd_matrix``.
    """
    A = _require_matrix(a, "a")
    _check_elements(A, "mat_svd")
    U, s, Vt = np.linalg.svd(A, full_matrices=bool(full_matrices))
    return (np.ascontiguousarray(U, dtype=np.float64),
            np.ascontiguousarray(s, dtype=np.float64),
            np.ascontiguousarray(Vt, dtype=np.float64))


#: Relative symmetry tolerance for :func:`mat_eigh` (``|A - A.T|`` vs ``|A|``).
_SYM_RTOL = 1e-10


def mat_eigh(a):
    """Eigen-decomposition of a **symmetric** matrix (LAPACK ``syevd``).

    Returns ``(w, V)``: eigenvalues ``w`` in **ascending** order (all real —
    guaranteed by symmetry) and orthonormal eigenvectors as the **columns** of
    ``V`` (``A @ V[:, i] == w[i] * V[:, i]``).

    **Symmetric input only, verified**: ``max|A - A.T|`` above ``1e-10`` of the
    matrix scale raises ``ValueError``. This is deliberate fail-closing of two
    traps at once — a symmetric solver fed a non-symmetric matrix silently
    reads one triangle and returns a *plausible wrong* answer, and a general
    matrix has complex eigenvalues this real-valued API cannot even represent.
    For a covariance / Hessian / Gram matrix (the metrology cases) symmetry
    holds by construction; symmetrise explicitly (``(A + A.T) / 2``) if yours
    is symmetric-up-to-noise.

    **Sign trap (honest)**: each eigenvector is defined only up to sign, and
    eigenvectors of a *repeated* eigenvalue only up to rotation in that
    subspace. Compare ``|v·w|`` or subspaces, never raw columns.

    HALCON: ``eigenvalues_symmetric_matrix``.
    """
    A = _require_matrix(a, "a")
    _check_elements(A, "mat_eigh")
    if A.shape[0] != A.shape[1]:
        raise ValueError("mat_eigh needs a square matrix, got shape %r" % (A.shape,))
    scale = float(np.abs(A).max())
    asym = float(np.abs(A - A.T).max())
    if asym > _SYM_RTOL * max(1.0, scale):
        raise ValueError("mat_eigh: matrix is not symmetric (max|A - A.T| = %g at "
                         "scale %g) — a symmetric solver would silently use one "
                         "triangle; symmetrise explicitly ((A + A.T)/2) or use a "
                         "general (complex-capable) eigensolver" % (asym, scale))
    w, V = np.linalg.eigh(A)
    return (np.ascontiguousarray(w, dtype=np.float64),
            np.ascontiguousarray(V, dtype=np.float64))


def mat_pinv(a, rcond=1e-12):
    """Moore-Penrose pseudo-inverse via SVD, with the cutoff **explicit**.

    Singular values below ``rcond * s_max`` are treated as zero — that cutoff
    *is* the regularisation, so it is a named, documented parameter here
    (default ``1e-12``) rather than a hidden library default: raising it
    discards noisy directions (stabler, more biased), lowering it keeps them
    (exact for well-conditioned *A*, explosive near rank deficiency).

    Works for any ``(m, n)``: ``pinv(A) @ b`` is the least-squares solution for
    ``m > n`` and the minimum-norm solution for ``m < n``.

    HALCON: no direct operator — HALCON reaches the same result through
    ``svd_matrix`` + reciprocal singular values.
    """
    A = _require_matrix(a, "a")
    _check_elements(A, "mat_pinv")
    rc = float(rcond)
    if not np.isfinite(rc) or rc < 0.0:
        raise ValueError("rcond must be a non-negative finite float, got %r"
                         % (rcond,))
    return np.ascontiguousarray(np.linalg.pinv(A, rcond=rc), dtype=np.float64)


def mat_cond(a):
    """Spectral (2-norm) condition number ``s_max / s_min`` — the numerical
    canary of the whole linalg family.

    ``cond == 1`` for an orthogonal/orthonormal matrix (the best possible);
    ``inf`` (returned, not raised — the question "how conditioned is it?" has
    that honest answer) for an exactly singular one. A solve against *A* loses
    roughly ``log10(cond(A))`` significant digits (Golub & Van Loan §2.6):

      * ``cond ~ 1e3``  — comfortable, ~13 digits survive.
      * ``cond ~ 1e8``  — half the digits are gone; residuals may still look
        small while parameters are off.
      * ``cond > 1e12`` — **do not trust** :func:`mat_solve` here: at best ~3
        digits remain. Rescale/centre the problem, or switch to
        :func:`mat_lstsq` / :func:`mat_pinv` with an honest ``rcond``.

    Defined for any rectangular ``(m, n)`` matrix (via its singular values).
    HALCON: no direct operator (combine ``norm_matrix`` of *A* and of its
    inverse).
    """
    A = _require_matrix(a, "a")
    _check_elements(A, "mat_cond")
    s = np.linalg.svd(A, compute_uv=False)
    smin = float(s[-1])
    if smin <= 0.0:
        return float("inf")
    return float(s[0] / smin)


# --------------------------------------------------------------------------- #
# stats                                                                        #
# --------------------------------------------------------------------------- #
def stat_describe(x):
    """Five-number-plus summary of a 1-D sample, as a plain dict.

    Returns ``{"n", "mean", "std", "min", "max", "percentiles"}`` where
    ``percentiles`` is ``{"p5", "p25", "p50", "p75", "p95"}`` (linear
    interpolation between order statistics, numpy's default). ``std`` is the
    **population** standard deviation (``ddof=0`` — well-defined down to a
    single sample; multiply by ``sqrt(n/(n-1))`` for the sample estimator,
    which is what :func:`stat_covariance` uses, documented there).

    The tails matter in metrology: ``mean``/``std`` of residuals say how good
    the fit is *on average*; ``p5``/``p95`` say how bad the *outliers* are —
    report both, a fit can pass on RMS and fail on extremes.

    HALCON: ``tuple_mean`` / ``tuple_deviation`` / ``tuple_min`` /
    ``tuple_max`` (the percentile row has no single HALCON tuple operator).
    """
    v = _require_vector(x, "x")
    p = np.percentile(v, [5.0, 25.0, 50.0, 75.0, 95.0])
    return {
        "n": int(v.size),
        "mean": float(v.mean()),
        "std": float(v.std(ddof=0)),
        "min": float(v.min()),
        "max": float(v.max()),
        "percentiles": {"p5": float(p[0]), "p25": float(p[1]), "p50": float(p[2]),
                        "p75": float(p[3]), "p95": float(p[4])},
    }


def stat_histogram(x, bins=10, range=None, density=False):
    """Histogram of a 1-D sample with the binning **explicit**.

    *bins* is a positive integer count of equal-width bins; *range* is an
    explicit ``(lo, hi)`` (finite, ``lo < hi``) or ``None`` to span the data
    (values exactly at ``hi`` land in the last bin, numpy's convention; with an
    explicit *range*, values outside it are excluded from every bin — they
    simply do not count, which is why passing *range* explicitly is the honest
    choice when comparing histograms across datasets). With ``density=False``
    (default) *counts* are occurrence **frequencies** (int64, summing to the
    number of in-range samples); with ``density=True`` they form a
    **probability density** (float64, integrating to 1 over the range).

    Returns ``(counts, edges)`` — ``edges`` has ``bins + 1`` entries;
    bin *i* is ``[edges[i], edges[i+1])``.

    HALCON: ``tuple_histo_range`` (and ``gray_histo`` for whole images).
    """
    v = _require_vector(x, "x")
    if not (isinstance(bins, (int, np.integer)) and not isinstance(bins, bool)) or bins < 1:
        raise ValueError("bins must be a positive integer, got %r" % (bins,))
    if range is not None:
        try:
            lo, hi = (float(r) for r in range)
        except (TypeError, ValueError):
            raise ValueError("range must be a (lo, hi) pair, got %r" % (range,)) from None
        if not (np.isfinite(lo) and np.isfinite(hi)) or lo >= hi:
            raise ValueError("range must be finite with lo < hi, got (%r, %r)"
                             % (lo, hi))
        rng = (lo, hi)
    else:
        rng = None
    counts, edges = np.histogram(v, bins=int(bins), range=rng, density=bool(density))
    counts = (np.ascontiguousarray(counts, dtype=np.float64) if density
              else np.ascontiguousarray(counts, dtype=np.int64))
    return counts, np.ascontiguousarray(edges, dtype=np.float64)


def stat_covariance(x):
    """Sample covariance matrix of ``(N, D)`` observations → ``(D, D)``.

    Rows are observations, columns are variables — the ``(N, D)`` orientation
    every Fullseye point/sample API uses (note ``np.cov`` defaults to the
    *transposed* convention). Uses the unbiased ``ddof=1`` estimator (divides
    by ``N - 1``), hence the ``N >= 2`` requirement. The diagonal holds the
    per-variable sample variances; the result is symmetric positive
    semi-definite by construction, so it can go straight into
    :func:`mat_eigh` for principal axes (the covariance-ellipse workflow).

    HALCON: no public tuple/matrix operator — covariance lives inside HALCON's
    calibration and matching internals only.
    """
    a = _require_samples(x, "x")
    _check_elements(a, "stat_covariance")
    mu = a.mean(axis=0)
    d = a - mu
    c = (d.T @ d) / (a.shape[0] - 1)
    return np.ascontiguousarray((c + c.T) / 2.0, dtype=np.float64)  # exactly symmetric


def stat_correlation(x):
    """Pearson correlation matrix of ``(N, D)`` observations → ``(D, D)``.

    Same orientation as :func:`stat_covariance` (rows = observations).
    Entries are clipped to ``[-1, 1]`` (floating-point can overshoot by an
    ulp), the diagonal is exactly ``1`` and the matrix exactly symmetric by
    construction.

    **A constant column raises ``ValueError``** (naming the column) instead of
    yielding NaN: correlation with a zero-variance variable is mathematically
    undefined (0/0), and a NaN that surfaces three ops downstream is the
    classic zero-division bug family this module fails closed against. Drop or
    perturb the constant column deliberately if that is what you mean.

    HALCON: no public tuple operator (see :func:`stat_covariance`).
    """
    a = _require_samples(x, "x")
    _check_elements(a, "stat_correlation")
    sd = a.std(axis=0, ddof=1)
    dead = np.flatnonzero(sd <= 0.0)
    if dead.size:
        raise ValueError("stat_correlation: column(s) %s are constant (zero "
                         "variance) — Pearson correlation is undefined (0/0); "
                         "drop or perturb them explicitly"
                         % (", ".join(str(int(i)) for i in dead),))
    c = stat_covariance(a)
    r = c / np.outer(sd, sd)
    r = np.clip((r + r.T) / 2.0, -1.0, 1.0)
    np.fill_diagonal(r, 1.0)
    return np.ascontiguousarray(r, dtype=np.float64)


def stat_zscore(x):
    """Standardise a 1-D sample: ``(x - mean) / std`` (population ``ddof=0``).

    The result has mean 0 and standard deviation 1 — the common currency for
    comparing residuals across scales and flagging outliers (``|z| > 3``).

    **A constant input raises ``ValueError``** — the decision, stated: with
    zero variance the z-score is 0/0. Returning silent zeros would claim "every
    point is perfectly average", which is *a* convention but hides upstream
    breakage (a sensor stuck at one value would sail through an outlier gate).
    Fail-closed instead; a caller who wants the all-zeros convention can catch
    this and substitute deliberately.

    HALCON: no direct tuple operator (compose ``tuple_mean`` +
    ``tuple_deviation`` + arithmetic).
    """
    v = _require_vector(x, "x", min_len=2)
    sd = float(v.std(ddof=0))
    if sd <= 0.0:
        raise ValueError("stat_zscore: input is constant (zero variance) — the "
                         "z-score is undefined (0/0); refusing to return silent "
                         "zeros (a stuck sensor would pass every outlier gate)")
    return np.ascontiguousarray((v - v.mean()) / sd, dtype=np.float64)


# --------------------------------------------------------------------------- #
# interpolation / polynomials                                                  #
# --------------------------------------------------------------------------- #
def _require_nodes(x, y, op: str, min_pts: int):
    xs = _require_vector(x, "x", min_len=min_pts)
    ys = _require_vector(y, "y", min_len=min_pts)
    if xs.size != ys.size:
        raise ValueError("%s: x and y must have the same length, got %d vs %d"
                         % (op, xs.size, ys.size))
    if not (np.diff(xs) > 0.0).all():
        raise ValueError("%s: x must be strictly increasing (sorted, no "
                         "duplicates) — sort/deduplicate explicitly; a silent "
                         "sort here would desynchronise x from y" % (op,))
    return xs, ys


def _apply_out_of_range(xq: np.ndarray, xs: np.ndarray, mode, op: str) -> np.ndarray:
    if mode not in ("raise", "clamp"):
        raise ValueError("%s: out_of_range must be 'raise' or 'clamp', got %r"
                         % (op, mode))
    lo, hi = float(xs[0]), float(xs[-1])
    outside = (xq < lo) | (xq > hi)
    if not outside.any():
        return xq
    if mode == "raise":
        raise ValueError("%s: %d query point(s) outside the data range [%g, %g] "
                         "(first offender: %g) — extrapolation is refused by "
                         "default; pass out_of_range='clamp' to hold the end "
                         "values" % (op, int(outside.sum()), lo, hi,
                                     float(xq[outside][0])))
    return np.clip(xq, lo, hi)


def interp_linear(x, y, xq, out_of_range="raise"):
    """Piecewise-linear interpolation of ``(x, y)`` samples at query *xq*.

    *x* must be strictly increasing (fail-closed: an unsorted or duplicated
    grid raises rather than being silently reordered). *xq* is a scalar or a
    1-D array; a scalar query returns a Python float, an array returns float64.

    **Out-of-range is an explicit choice**, never silent: ``'raise'`` (default)
    refuses any query outside ``[x[0], x[-1]]`` — a calibration table queried
    beyond its calibrated range is a wrong answer waiting to happen — while
    ``'clamp'`` holds the boundary values (the honest flat extension; there is
    deliberately no silent linear extrapolation mode).

    Exact on the nodes and exact for data that is genuinely piecewise linear.
    HALCON: ``get_y_value_funct_1d`` interpolates function pairs the same way
    (see :mod:`funct1d`, which works HALCON's index-grid convention; this op
    takes an arbitrary strictly-increasing x grid).
    """
    xs, ys = _require_nodes(x, y, "interp_linear", 2)
    q, scalar = _query_points(xq)
    q = _apply_out_of_range(q, xs, out_of_range, "interp_linear")
    out = np.interp(q, xs, ys)
    return float(out[0]) if scalar else np.ascontiguousarray(out, dtype=np.float64)


def interp_cubic(x, y, xq, out_of_range="raise", bc_type="not-a-knot"):
    """Cubic-spline interpolation (``scipy.interpolate.CubicSpline``).

    C²-smooth through all nodes — the step up from :func:`interp_linear` when
    the underlying curve is smooth (a lens-distortion or gamma curve). Needs at
    least 4 points. *bc_type* is the boundary condition: ``'not-a-knot'``
    (default — reproduces a global cubic polynomial *exactly*, the property the
    tests pin), ``'natural'`` (zero second derivative at the ends; slightly
    smoother-looking, but it will NOT reproduce a cubic), or ``'clamped'``.

    Same strict grid and the same explicit *out_of_range* policy as
    :func:`interp_linear` ('raise' by default, 'clamp' to hold end values) —
    spline **extrapolation diverges cubically** and is refused outright.

    Honest note: between nodes a spline can overshoot (it is a minimum-
    curvature interpolant, not shape-preserving); for monotone data whose
    interpolant must stay monotone, use a PCHIP-type method instead — not
    provided here, stated so nobody assumes otherwise.

    HALCON: no cubic tuple interpolation operator (``create_funct_1d_pairs``
    feeds linear interpolation only).
    """
    from scipy.interpolate import CubicSpline  # local: keeps import cost off the facade
    xs, ys = _require_nodes(x, y, "interp_cubic", 4)
    if bc_type not in ("not-a-knot", "natural", "clamped"):
        raise ValueError("interp_cubic: bc_type must be 'not-a-knot', 'natural' "
                         "or 'clamped', got %r" % (bc_type,))
    q, scalar = _query_points(xq)
    q = _apply_out_of_range(q, xs, out_of_range, "interp_cubic")
    out = CubicSpline(xs, ys, bc_type=bc_type)(q)
    return float(out[0]) if scalar else np.ascontiguousarray(out, dtype=np.float64)


def poly_fit(x, y, degree):
    """Least-squares polynomial fit with its conditioning **on the record**.

    Fits ``y ≈ c[0] x^d + ... + c[d]`` (coefficients highest-power-first, the
    :func:`poly_eval` / ``np.polyval`` convention) by SVD least squares on the
    Vandermonde matrix. *degree* must be an integer ``>= 0`` with at least
    ``degree + 1`` samples (fail-closed: an exactly-determined fit is allowed,
    an under-determined one is not).

    Returns a dict — the fit and its health, inseparable:

    ``coeffs`` ``(degree + 1,)`` float64 · ``degree`` · ``cond`` the Vandermonde
    condition number (:func:`mat_cond` of the design matrix) · ``rms_residual``
    root-mean-square of ``y - p(x)``.

    **The conditioning mechanism**: when ``cond > POLY_COND_WARN`` (1e10) a
    ``RuntimeWarning`` is emitted *and* the number is in the result — an
    equispaced degree-10 fit on raw pixel coordinates is already past it. High
    degree on a raw coordinate range is the classic double trap: the
    Vandermonde columns become near-collinear (digits lost, coefficients
    unstable) and the fit oscillates between nodes (Runge phenomenon, Runge
    1901). Centre and scale x to ``[-1, 1]`` first, or keep degree ≤ ~6.

    HALCON: no public polynomial-fitting tuple operator (fitting of this kind
    lives inside HALCON's calibration internals).
    """
    if not (isinstance(degree, (int, np.integer)) and not isinstance(degree, bool)) or degree < 0:
        raise ValueError("degree must be a non-negative integer, got %r" % (degree,))
    d = int(degree)
    xs, ys = _require_nodes(x, y, "poly_fit", 1)
    if xs.size < d + 1:
        raise ValueError("poly_fit: degree %d needs at least %d point(s), got %d "
                         "— an under-determined fit is refused" % (d, d + 1, xs.size))
    V = np.vander(xs, d + 1)               # columns x^d ... x^0
    sv = np.linalg.svd(V, compute_uv=False)
    cond = float("inf") if float(sv[-1]) <= 0.0 else float(sv[0] / sv[-1])
    if cond > POLY_COND_WARN:
        warnings.warn("poly_fit: Vandermonde condition number %.3g exceeds %g — "
                      "coefficients are numerically unreliable (centre/scale x, "
                      "or lower the degree)" % (cond, POLY_COND_WARN),
                      RuntimeWarning, stacklevel=2)
    coeffs, _, _, _ = np.linalg.lstsq(V, ys, rcond=None)
    resid = ys - V @ coeffs
    return {
        "coeffs": np.ascontiguousarray(coeffs, dtype=np.float64),
        "degree": d,
        "cond": cond,
        "rms_residual": float(np.sqrt(np.mean(resid * resid))),
    }


def poly_eval(coeffs, x):
    """Evaluate a polynomial (coefficients highest-power-first) at *x*.

    *coeffs* is the 1-D array :func:`poly_fit` returns in ``"coeffs"`` (or any
    hand-written one, ``[c_d, ..., c_1, c_0]``); *x* is a finite scalar or 1-D
    array. A scalar returns a Python float, an array returns float64.
    Evaluation is by Horner's scheme (``np.polyval``) — numerically the right
    way to evaluate, though it cannot repair a badly-conditioned *fit* (see
    :func:`poly_fit`'s ``cond``).

    HALCON: no polynomial tuple operator (compose ``tuple_pow`` + arithmetic).
    """
    c = _require_vector(coeffs, "coeffs")
    q, scalar = _query_points(x, "x")
    out = np.polyval(c, q)
    return float(out[0]) if scalar else np.ascontiguousarray(out, dtype=np.float64)


def poly_roots(coeffs, real_only=False, imag_tol=1e-9):
    """All roots of a polynomial (coefficients highest-power-first) — complex
    included.

    Roots are the eigenvalues of the companion matrix (``np.roots``); the
    polynomial must have degree ≥ 1 and a **non-zero leading coefficient**
    (fail-closed: a zero leading coefficient means the stated degree is a lie —
    trim it explicitly rather than have it silently dropped).

    Returns complex128, sorted by real part then imaginary part
    (deterministic). Complex answers are honest answers: ``x² + 1`` really does
    have roots ``±i``, and hiding them would misreport the polynomial. Pass
    ``real_only=True`` to keep only roots whose imaginary part is negligible
    (``|imag| <= imag_tol * max(1, |root|)``) and get them back as a sorted
    float64 array — possibly **empty**, which is the correct answer for
    ``x² + 1``.

    Numerical note: root-finding conditioning degrades with degree and with
    clustered roots (a double root moves ~``sqrt(eps)`` under coefficient
    noise — Wilkinson's classic analysis); treat high-degree roots as
    approximate. HALCON: no root-finding tuple operator.
    """
    c = _require_vector(coeffs, "coeffs", min_len=2)
    if c[0] == 0.0:
        raise ValueError("poly_roots: leading coefficient is zero — the stated "
                         "degree %d is not the true degree; trim the "
                         "coefficients explicitly" % (c.size - 1,))
    tol = float(imag_tol)
    if not np.isfinite(tol) or tol < 0.0:
        raise ValueError("imag_tol must be a non-negative finite float, got %r"
                         % (imag_tol,))
    r = np.roots(c).astype(np.complex128)
    order = np.lexsort((r.imag, r.real))
    r = r[order]
    if not real_only:
        return np.ascontiguousarray(r)
    keep = np.abs(r.imag) <= tol * np.maximum(1.0, np.abs(r))
    return np.ascontiguousarray(np.sort(r[keep].real.astype(np.float64)))
