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
  * **complex** — ``cplx_contour_circle`` / ``cplx_poly_eval`` /
    ``cplx_contour_integral`` / ``cplx_winding_number`` /
    ``cplx_cauchy_value`` / ``cplx_argument_principle`` /
    ``cplx_laurent_coeffs`` / ``cplx_joukowski`` / ``cplx_mobius`` /
    ``cplx_cr_residual``: the *computable* face of complex analysis — a closed
    contour is a point list, so Cauchy's integral formula, the argument
    principle (count zeros and poles without finding them), Laurent
    coefficients / residues and the classical conformal maps all reduce to
    numpy sums over that list. Nothing here calls back into Python for ``f``:
    the caller samples ``f`` on the contour, which keeps every op a pure array
    operation and lets a *measured* field (a phase image, a transfer function)
    take the place of a formula.

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

  * **The complex family is the one exception to "complex input is refused".**
    Everywhere else a complex array in a real slot is a silent-truncation trap
    and raises; in the ``cplx_*`` ops the imaginary part *is* the data, so they
    take complex (or real, promoted) input by design. They still refuse masked
    entries, NaN/Inf, wrong rank — and, uniquely, a *result* that overflowed to
    Inf, because "the integral is inf" and "float64 ran out" are different
    statements and only the second one is what happened.

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
    "cplx_contour_circle", "cplx_poly_eval", "cplx_contour_integral",
    "cplx_winding_number", "cplx_cauchy_value", "cplx_argument_principle",
    "cplx_laurent_coeffs", "cplx_joukowski", "cplx_mobius", "cplx_cr_residual",
    "MATHOPS", "MAX_ELEMENTS", "POLY_COND_WARN", "MAX_CONTOUR_POINTS",
]

#: The public math operators, by name (introspection / facade wiring).
MATHOPS = [
    "mat_solve", "mat_lstsq", "mat_svd", "mat_eigh", "mat_pinv", "mat_cond",
    "stat_describe", "stat_histogram", "stat_covariance", "stat_correlation",
    "stat_zscore",
    "interp_linear", "interp_cubic", "poly_fit", "poly_eval", "poly_roots",
    "cplx_contour_circle", "cplx_poly_eval", "cplx_contour_integral",
    "cplx_winding_number", "cplx_cauchy_value", "cplx_argument_principle",
    "cplx_laurent_coeffs", "cplx_joukowski", "cplx_mobius", "cplx_cr_residual",
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
    a = _as_float64(b, name)
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
    if np.ma.is_masked(xq):
        raise ValueError("%s is a masked array with masked (invalid) entries — "
                         "fill or drop them explicitly" % (name,))
    if np.iscomplexobj(xq):
        raise ValueError("%s is complex — coercion to float64 would silently "
                         "discard the imaginary part" % (name,))
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
    A *range* that excludes **every** sample raises ``ValueError`` under
    ``density=True`` (the density would be 0/0 — silent NaNs refused) while
    ``density=False`` honestly returns all-zero counts. *bins* is capped at
    ``MAX_ELEMENTS`` (the edge/count arrays are allocations too).

    Returns ``(counts, edges)`` — ``edges`` has ``bins + 1`` entries;
    bin *i* is ``[edges[i], edges[i+1])``.

    HALCON: ``tuple_histo_range`` (and ``gray_histo`` for whole images).
    """
    v = _require_vector(x, "x")
    if not (isinstance(bins, (int, np.integer)) and not isinstance(bins, bool)) or bins < 1:
        raise ValueError("bins must be a positive integer, got %r" % (bins,))
    if bins > MAX_ELEMENTS:
        raise ValueError("stat_histogram: %d bins exceeds the %d cap "
                         "(mathops.MAX_ELEMENTS) — the edge/count arrays would "
                         "allocate gigabytes for no statistical gain" % (bins, MAX_ELEMENTS))
    if range is not None:
        try:
            lo, hi = (float(r) for r in range)
        except (TypeError, ValueError):
            raise ValueError("range must be a (lo, hi) pair, got %r" % (range,)) from None
        if not (np.isfinite(lo) and np.isfinite(hi)) or lo >= hi:
            raise ValueError("range must be finite with lo < hi, got (%r, %r)"
                             % (lo, hi))
        rng = (lo, hi)
        if density and not ((v >= lo) & (v <= hi)).any():
            raise ValueError("stat_histogram: no samples fall inside range "
                             "(%g, %g) — a density over zero samples is 0/0; "
                             "refusing to return silent NaNs (use "
                             "density=False for honest zero counts)" % (lo, hi))
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

    Raises ValueError when a finite input overflows float64 — a degree-*d*
    polynomial at ``|x|`` well above 1 grows like ``|x|**d``, so mixing up the
    two arguments (a long signal used as coefficients) silently produced ``inf``
    before this guard (chain fuzzer wave-7: 256 coefficients evaluated at
    ``|x|<=22`` -> ``22**255``). An unusable ``inf`` must not flow downstream.
    """
    c = _require_vector(coeffs, "coeffs")
    q, scalar = _query_points(x, "x")
    with np.errstate(over="ignore", invalid="ignore"):
        out = np.polyval(c, q)
    if not np.isfinite(out).all():
        bad = np.abs(q[~np.isfinite(out)])
        raise ValueError(
            "poly_eval overflowed float64: a degree-%d polynomial evaluated at "
            "|x| up to %.3g exceeds ~1.8e308 (|x|**degree grows that fast). "
            "Check that the arguments are not swapped — coeffs is the short "
            "coefficient vector, x the query points."
            % (len(c) - 1, float(bad.max()) if bad.size else float("nan")))
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


# --------------------------------------------------------------------------- #
# complex analysis (tier 2) — fail-closed input helpers                        #
# --------------------------------------------------------------------------- #
def _require_cvector(z, name="z", min_len=1):
    """Coerce to a strictly 1-D **complex128** vector or raise ``ValueError``.

    This family is the one place in :mod:`mathops` where a complex input is the
    *point* rather than a truncation trap, so the module-wide complex rejection
    (:func:`_as_float64`) is lifted here — and only here. Real input is
    accepted and promoted (a real sample of a complex function is legitimate);
    masked entries, non-finite values, wrong rank and over-cap sizes still
    raise, exactly as in the real families.
    """
    if np.ma.is_masked(z):
        raise ValueError("%s is a masked array with masked (invalid) entries — "
                         "coercion would silently strip the mask and use the raw "
                         "values underneath; fill or drop them explicitly" % (name,))
    try:
        a = np.ascontiguousarray(z, dtype=np.complex128)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real or complex numeric array, got %s"
                         % (name, type(z).__name__)) from None
    if a.ndim != 1:
        raise ValueError("%s must be a 1-D array of complex points, got a %d-D "
                         "array of shape %r — reshape explicitly, nothing is "
                         "promoted silently" % (name, a.ndim, tuple(np.shape(z))))
    if a.size < min_len:
        raise ValueError("%s needs at least %d point(s), got %d"
                         % (name, min_len, a.size))
    _require_finite(a, name)
    _check_elements(a, name)
    return a


def _require_cscalar(w, name="w"):
    """A single finite complex (or real) scalar → Python ``complex``."""
    if np.ma.is_masked(w):
        raise ValueError("%s is a masked array with masked (invalid) entries — "
                         "fill or drop them explicitly" % (name,))
    try:
        a = np.asarray(w, dtype=np.complex128)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real or complex scalar, got %s"
                         % (name, type(w).__name__)) from None
    if a.ndim != 0:
        raise ValueError("%s must be a single scalar, got a %d-D array of shape %r"
                         % (name, a.ndim, a.shape))
    if not np.isfinite(a):
        raise ValueError("%s must be finite, got %r" % (name, w))
    return complex(a)


def _require_contour(z, name="z"):
    """A closed contour: ``>= 3`` complex vertices, **not** all coincident.

    The closing segment ``z[-1] -> z[0]`` is implicit; repeating the first point
    at the end is tolerated (it contributes a zero-length segment)."""
    v = _require_cvector(z, name, min_len=3)
    if not np.abs(np.roll(v, -1) - v).any():
        raise ValueError("%s is a degenerate contour: all %d sample points "
                         "coincide (total length 0) — it encloses nothing and "
                         "every contour integral over it is trivially 0"
                         % (name, v.size))
    return v


def _require_contour_values(z, fz, op):
    """A contour and one sampled function value per contour point."""
    c = _require_contour(z, "z")
    f = _require_cvector(fz, "fz", min_len=3)
    if f.size != c.size:
        raise ValueError("%s: z and fz must have the same length (one sampled "
                         "value per contour point), got %d vs %d"
                         % (op, c.size, f.size))
    return c, f


def _finite_result(value, op, why):
    """Refuse to hand back a NaN/Inf produced *inside* an op (never silent)."""
    if not np.isfinite(np.asarray(value)).all():
        raise ValueError("%s: the result is not finite (NaN/Inf) — %s" % (op, why))
    return value


#: Refuse to *generate* a contour longer than this (2^22 points ≈ 64 MB of
#: complex128, and every contour op allocates a handful of same-size
#: temporaries). A quadrature needing millions of nodes wants a different
#: method (adaptive / analytic), not a bigger array — fail-closed instead of
#: turning ``n=10**9`` into a swap storm.
MAX_CONTOUR_POINTS = 1 << 22

#: :func:`cplx_winding_number` refuses a polygon segment that turns the ray to
#: the query point by ``>= pi - _HALF_TURN_TOL``: there the principal-value
#: branch cannot tell which way the segment passed the point (the point is *on*
#: the segment, or the contour is undersampled around it).
_HALF_TURN_TOL = 1e-9

#: How far the accumulated turn may sit from an exact integer number of turns
#: before :func:`cplx_winding_number` refuses (defensive: for a closed polygon
#: the sum is an integer multiple of 2*pi up to rounding, ~1e-14 at n = 1e4).
_WIND_INT_TOL = 1e-6

#: Relative tolerance for "these samples really are a uniformly-sampled circle"
#: in :func:`cplx_laurent_coeffs` (equal radii, equally spaced angles).
_CIRCLE_RTOL = 1e-8


# --------------------------------------------------------------------------- #
# complex analysis (tier 2) — contours, Cauchy, argument principle, maps       #
# --------------------------------------------------------------------------- #
def cplx_contour_circle(center=0.0, radius=1.0, n=256, orientation="ccw"):
    """Sample a circle as a closed contour — the standard integration path.

    Returns ``n`` complex points ``center + radius * exp(±i * 2*pi*k/n)``,
    ``k = 0..n-1``. The closing segment ``z[-1] -> z[0]`` is **implicit**: the
    first point is *not* repeated (every contour op in this family closes the
    polygon itself; repeating it would only add a zero-length segment).

    *orientation* is explicit because in complex analysis the sign of every
    result depends on it: ``'ccw'`` (default) is the positive/mathematical
    direction — the one for which the residue theorem, the Cauchy formula and
    the argument principle carry a ``+`` sign — and ``'cw'`` negates all three.

    Honest limitation: this is a **polygon** through samples of the circle, not
    the circle. Its enclosed area is short by a factor ``sinc``-like in
    ``2*pi/n``, and every quadrature on it converges as ``O(n^-2)``
    (:func:`cplx_contour_integral` documents the measured rate).

    **Raises** ``ValueError``: non-finite *center*/*radius*, ``radius <= 0``,
    ``n`` not an integer in ``[3, MAX_CONTOUR_POINTS]`` (a fail-closed size cap
    — ``n=10**9`` would allocate 16 GB), unknown *orientation*.

    HALCON: no complex-plane operator (``gen_circle_contour_xld`` draws the
    same geometry as an XLD contour for image space).
    """
    c = _require_cscalar(center, "center")
    r = _require_cscalar(radius, "radius")
    if r.imag != 0.0 or r.real <= 0.0:
        raise ValueError("radius must be a positive real number, got %r" % (radius,))
    if not (isinstance(n, (int, np.integer)) and not isinstance(n, bool)):
        raise ValueError("n must be an integer, got %r" % (n,))
    n = int(n)
    if n < 3:
        raise ValueError("n must be at least 3 (a closed polygon needs 3 "
                         "vertices), got %d" % (n,))
    if n > MAX_CONTOUR_POINTS:
        raise ValueError("n=%d exceeds the %d point cap "
                         "(mathops.MAX_CONTOUR_POINTS) — a contour that long "
                         "allocates gigabytes and buys nothing: the quadrature "
                         "error is already ~1e-11 at 1e5 points"
                         % (n, MAX_CONTOUR_POINTS))
    if orientation not in ("ccw", "cw"):
        raise ValueError("orientation must be 'ccw' (positive) or 'cw', got %r"
                         % (orientation,))
    sign = 1.0 if orientation == "ccw" else -1.0
    th = sign * 2.0 * np.pi * np.arange(n, dtype=np.float64) / n
    return np.ascontiguousarray(c + r.real * np.exp(1j * th), dtype=np.complex128)


def cplx_poly_eval(coeffs, z):
    """Evaluate a polynomial on the complex plane (Horner, complex-capable).

    The complex twin of :func:`poly_eval`: *coeffs* is highest-power-first
    (``[c_d, ..., c_1, c_0]``, possibly complex) and *z* is a complex scalar or
    1-D array. A scalar query returns a Python ``complex``, an array returns
    ``complex128`` — mirroring :func:`poly_eval`'s scalar/array behaviour.

    This is what makes the rest of the family usable: sample a polynomial on a
    contour from :func:`cplx_contour_circle`, then count its zeros with
    :func:`cplx_argument_principle` or reconstruct interior values with
    :func:`cplx_cauchy_value`. (:func:`poly_eval` refuses complex input by
    design — silent imaginary-part truncation — so it cannot serve here.)

    **Raises** ``ValueError``: empty/multi-dimensional *coeffs*, non-finite or
    masked input, over-cap size, and — the honest one — a result that
    overflowed to Inf/NaN (a degree-200 polynomial on ``|z| = 10`` genuinely
    exceeds float64 range; that is refused rather than returned as ``inf``).

    HALCON: no complex polynomial operator.
    """
    c = _require_cvector(coeffs, "coeffs", min_len=1)
    scalar = np.ndim(z) == 0
    q = np.atleast_1d(_require_cscalar(z, "z")) if scalar else _require_cvector(z, "z")
    out = np.polyval(c, q)
    _finite_result(out, "cplx_poly_eval",
                   "the polynomial overflowed float64 on these points (lower the "
                   "degree, or rescale z)")
    return complex(out[0]) if scalar else np.ascontiguousarray(out, dtype=np.complex128)


def cplx_contour_integral(z, fz):
    """Closed contour integral ``∮ f(z) dz`` by the chordal trapezoidal rule.

    *z* are the contour vertices (closing segment implicit, see
    :func:`cplx_contour_circle`) and *fz* the function sampled at exactly those
    points — the op never calls back into Python, so any ``f`` is allowed as
    long as you can sample it. The quadrature is
    ``sum_k (f_k + f_{k+1})/2 * (z_{k+1} - z_k)``, i.e. the trapezoidal rule
    along the *chords*; it is exact for a piecewise-linear integrand and second
    order otherwise.

    Ground truth it reproduces: ``f = 1/(z - a)`` around a circle enclosing
    ``a`` integrates to ``2*pi*i`` (Cauchy); measured on the unit circle with
    ``a = 0``, the relative error is @@ACC_INT_256@@ at ``n = 256`` and
    @@ACC_INT_1024@@ at ``n = 1024`` — a factor @@ACC_INT_RATIO@@ for 4x
    refinement, i.e. the ``O(n^-2)`` rate, *not* the spectral accuracy the
    trapezoid rule enjoys when applied in the angle parameter. That difference
    is the honest price of accepting an arbitrary point list instead of a
    parametrisation.

    Orientation follows the sample order: a clockwise contour returns the
    negative of the counter-clockwise one.

    **Raises** ``ValueError``: fewer than 3 points, ``len(z) != len(fz)``, a
    degenerate contour (all points coincide), non-finite/masked input, or a sum
    that overflowed (``|f|`` near a pole *on* the path).

    HALCON: no operator (contour integration is not part of its tuple/XLD API).
    """
    c, f = _require_contour_values(z, fz, "cplx_contour_integral")
    dz = np.roll(c, -1) - c
    total = complex(np.sum(0.5 * (f + np.roll(f, -1)) * dz))
    _finite_result(total, "cplx_contour_integral",
                   "the samples overflowed float64 (a singularity sitting on the "
                   "integration path makes the integral divergent, not large)")
    return total


def cplx_winding_number(z, w=0.0):
    """Winding number of a closed contour around a point (turning number).

    How many times the polygon ``z`` (closing segment implicit) travels
    counter-clockwise around *w*: ``+1`` for a simple positively-oriented loop
    containing it, ``-1`` clockwise, ``0`` outside, ``±k`` for a ``k``-fold
    loop. Computed as the sum of the principal-value argument increments of
    ``z_k - w`` divided by ``2*pi`` and rounded — for a *polygon* that sum is an
    exact multiple of ``2*pi``, so the result is an exact integer, not an
    estimate (the rounding merely removes ~1e-14 of accumulated float error).

    Honest limitation: this is the winding number of the **polygon through the
    samples**, which equals that of the underlying curve only if the sampling
    resolves it. The failure mode is detected rather than hidden: a segment
    that turns the ray to *w* by half a turn or more is ambiguous (which side
    did it pass?) and raises instead of silently choosing a branch.

    **Raises** ``ValueError``: *w* coincides with a vertex or lies on a segment
    (the winding number is undefined on the contour), a segment subtends
    ``>= pi`` as seen from *w* (undersampled — refine the contour), fewer than
    3 points, degenerate contour, non-finite/masked input.

    HALCON: no operator (``test_region_point`` answers the related but weaker
    inside/outside question for regions).
    """
    c = _require_contour(z, "z")
    p = _require_cscalar(w, "w")
    d = c - p
    hit = np.flatnonzero(d == 0.0)
    if hit.size:
        raise ValueError("cplx_winding_number: the query point %r coincides with "
                         "contour vertex #%d — the winding number is undefined on "
                         "the contour itself" % (p, int(hit[0])))
    ang = np.angle(d)
    inc = np.roll(ang, -1) - ang
    inc = np.mod(inc + np.pi, 2.0 * np.pi) - np.pi      # principal value in [-pi, pi)
    bad = np.flatnonzero(np.abs(inc) >= np.pi - _HALF_TURN_TOL)
    if bad.size:
        raise ValueError("cplx_winding_number: segment #%d subtends >= pi as seen "
                         "from %r — either the point lies on that segment or the "
                         "contour is undersampled there; the principal-value "
                         "branch cannot tell which side it passed. Refine the "
                         "contour (or move the point off it)."
                         % (int(bad[0]), p))
    turns = float(inc.sum()) / (2.0 * np.pi)
    k = float(np.round(turns))
    if abs(turns - k) > _WIND_INT_TOL:
        raise ValueError("cplx_winding_number: accumulated turn %g is not an "
                         "integer number of loops (off by %g) — the contour is "
                         "not closed as sampled or is pathologically "
                         "undersampled" % (turns, abs(turns - k)))
    return int(k)


def cplx_cauchy_value(z, fz, w):
    """Cauchy's integral formula: recover ``f(w)`` **inside** a contour from its
    values **on** the contour.

    ``f(w) = 1/(2*pi*i*n) ∮ f(zeta)/(zeta - w) dzeta`` where ``n`` is the
    winding number of the contour around *w* (Cauchy 1831; the division by
    ``n`` is what makes a doubly-wound contour give the same answer). Valid
    only if ``f`` is holomorphic on and inside the contour — nothing here can
    check that, and this is the honest limit of the op: fed values of a
    non-holomorphic ``f`` (or of one with a pole inside) it returns the
    integral, which is then simply *not* ``f(w)``.

    Accuracy inherits the ``O(n^-2)`` chordal quadrature of
    :func:`cplx_contour_integral` and degrades as *w* approaches the path
    (the integrand's peak sharpens): measured for ``f(z) = z**2`` on a
    256-point unit circle, the absolute error is @@ACC_CAU_MID@@ at
    ``w = 0.3`` and @@ACC_CAU_NEAR@@ at ``w = 0.9`` — three orders of
    magnitude worse for a point ten times closer to the contour.

    **Raises** ``ValueError``: *w* outside the contour (winding 0 — the
    integral is then 0 and returning it as "f(w)" would be a lie), *w* closer
    to the contour than one sampling step (the quadrature is meaningless
    there — refine the contour), plus everything
    :func:`cplx_winding_number` and :func:`cplx_contour_integral` refuse.

    HALCON: no operator.
    """
    c, f = _require_contour_values(z, fz, "cplx_cauchy_value")
    p = _require_cscalar(w, "w")
    n = cplx_winding_number(c, p)
    if n == 0:
        raise ValueError("cplx_cauchy_value: the point %r lies outside the "
                         "contour (winding number 0) — Cauchy's formula gives 0 "
                         "there, which is not f(w); the formula only recovers "
                         "values enclosed by the path" % (p,))
    dmin = float(np.abs(c - p).min())
    step = float(np.abs(np.roll(c, -1) - c).max())
    if dmin <= step:
        raise ValueError("cplx_cauchy_value: the point %r sits %g from the "
                         "contour, within one sampling step (%g) — the 1/(zeta-w) "
                         "peak is unresolved and the quadrature would return a "
                         "plausible-wrong value; refine the contour or move the "
                         "point inward" % (p, dmin, step))
    integral = cplx_contour_integral(c, f / (c - p))
    return complex(integral / (2.0j * np.pi * n))


def cplx_argument_principle(z, fz):
    """Argument principle: count zeros minus poles enclosed by a contour, from
    sampled values of ``f`` alone.

    ``Z - P = 1/(2*pi*i) ∮ f'/f dz`` equals the winding number of the **image
    curve** ``f(z)`` around the origin (Cauchy 1831 / Riemann): as the contour
    is traversed once counter-clockwise, the argument of ``f`` increases by
    ``2*pi (Z - P)``, counting multiplicities. Computing it as a winding number
    of the image needs no derivative and no root finding — only ``f`` sampled
    on the path — and returns an exact integer.

    Honest limitations, all of them real:

      * It returns the **difference** ``Z - P``, never the two separately. A
        simple zero and a simple pole inside cancel to 0.
      * The result is multiplied by the winding number of the contour itself,
        so it equals ``Z - P`` only for a **simple, positively-oriented**
        contour (a clockwise one returns ``-(Z - P)``).
      * It is the winding of the *sampled* image polygon. If the contour is too
        coarse the image can jump by half a turn between samples; that is
        detected and raised (see below), not silently miscounted.

    **Raises** ``ValueError``: ``f`` vanishes at a sample point (a zero *on*
    the path — the count is undefined there), the image curve is undersampled
    (a half-turn between consecutive samples: refine the contour), plus the
    usual shape/finiteness contracts.

    HALCON: no operator.
    """
    c, f = _require_contour_values(z, fz, "cplx_argument_principle")
    zero = np.flatnonzero(f == 0.0)
    if zero.size:
        raise ValueError("cplx_argument_principle: f vanishes at sample #%d "
                         "(z = %r) — a zero on the contour makes Z - P undefined; "
                         "move the path off it" % (int(zero[0]), complex(c[zero[0]])))
    try:
        return cplx_winding_number(f, 0.0)
    except ValueError as exc:
        raise ValueError("cplx_argument_principle: the image curve f(z) is not "
                         "resolved by these samples (%s) — refine the contour: "
                         "consecutive samples must not jump half a turn around "
                         "the origin" % (exc,)) from None


def cplx_laurent_coeffs(z, fz, kmin=-1, kmax=4):
    """Laurent (and Taylor) coefficients on a **uniformly sampled circle** —
    residues included.

    For ``f`` holomorphic on an annulus around ``c``,
    ``f(z) = sum_k c_k (z - c)^k`` with
    ``c_k = 1/(2*pi*i) ∮ f(zeta)/(zeta - c)^(k+1) dzeta``. On a circle of
    radius ``r`` sampled at ``n`` equally spaced angles this becomes a discrete
    Fourier sum, ``c_k = (1/(n r^k)) sum_j f_j exp(-i k theta_j)`` — the
    trapezoidal rule in the angle, where it converges **geometrically** rather
    than as ``O(n^-2)`` (Trefethen & Weideman 2014, "The exponentially
    convergent trapezoidal rule").

    ``c_-1`` **is the residue** at ``c`` (when ``c`` is the only singularity
    inside), ``c_k`` for ``k >= 0`` are the Taylor coefficients
    ``f^(k)(c)/k!``, and a non-zero ``c_-m`` for ``m > 1`` reveals a pole of
    order ``m``. Measured on the unit circle with ``f = 1/(z - 0.5)``,
    ``n = 64``: ``c_-1 = 1`` and ``c_-2 = 0.5`` to @@ACC_LAU@@.

    Returns a dict: ``k`` (int64 orders, ``kmin..kmax``) · ``c`` (complex128
    coefficients) · ``center`` · ``radius``. The centre is the sample mean,
    which is exact for a uniformly sampled circle.

    Honest limitation — **aliasing**: the discrete sum cannot distinguish
    ``c_k`` from ``c_{k+n}``, so a coefficient carries the alias sum
    ``sum_m c_{k+m n} r^{m n}``. That is negligible for a rapidly converging
    series (the ``0.5^64`` term above) and ruinous near the annulus boundary.
    Requesting more than ``n`` coefficients is refused for the same reason.

    **Raises** ``ValueError``: the samples are not a uniformly spaced circle
    (unequal radii or unequal angular gaps beyond ``1e-8`` relative — this op
    is *not* valid on an arbitrary contour, and silently pretending otherwise
    would return numbers that mean nothing), ``kmin > kmax``, more than ``n``
    coefficients requested, non-integer orders, and a coefficient that
    overflowed (``r^-k`` for a small radius and a large negative order).

    HALCON: no operator.
    """
    c, f = _require_contour_values(z, fz, "cplx_laurent_coeffs")
    for nm, v in (("kmin", kmin), ("kmax", kmax)):
        if not (isinstance(v, (int, np.integer)) and not isinstance(v, bool)):
            raise ValueError("%s must be an integer, got %r" % (nm, v))
    kmin, kmax = int(kmin), int(kmax)
    if kmin > kmax:
        raise ValueError("cplx_laurent_coeffs: kmin (%d) must not exceed kmax (%d)"
                         % (kmin, kmax))
    n = c.size
    if kmax - kmin + 1 > n:
        raise ValueError("cplx_laurent_coeffs: %d coefficients requested from %d "
                         "samples — the discrete transform cannot resolve more "
                         "orders than it has points (they alias onto each other)"
                         % (kmax - kmin + 1, n))
    centre = complex(np.mean(c))
    rad = np.abs(c - centre)
    r = float(rad.mean())
    if r <= 0.0:
        raise ValueError("cplx_laurent_coeffs: the samples have zero radius about "
                         "their mean — not a circle")
    spread = float(rad.max() - rad.min())
    if spread > _CIRCLE_RTOL * r:
        raise ValueError("cplx_laurent_coeffs: the samples are not a circle "
                         "(radii spread %g at mean radius %g, tolerance %g) — the "
                         "Fourier form of the coefficient integral is only valid "
                         "on a circle; use cplx_contour_integral for an arbitrary "
                         "path" % (spread, r, _CIRCLE_RTOL * r))
    th = np.sort(np.angle(c - centre))
    gaps = np.diff(np.concatenate([th, th[:1] + 2.0 * np.pi]))
    step = 2.0 * np.pi / n
    if float(np.abs(gaps - step).max()) > _CIRCLE_RTOL * step * n:
        raise ValueError("cplx_laurent_coeffs: the circle is not uniformly "
                         "sampled (angular gaps deviate by up to %g from %g) — "
                         "the discrete sum assumes equal weights"
                         % (float(np.abs(gaps - step).max()), step))
    ks = np.arange(kmin, kmax + 1, dtype=np.int64)
    phase = np.exp(-1j * np.outer(ks.astype(np.float64), np.angle(c - centre)))
    coeffs = (phase @ f) / (n * np.power(r, ks.astype(np.float64)))
    _finite_result(coeffs, "cplx_laurent_coeffs",
                   "r**-k overflowed for the requested orders (a small radius with "
                   "a large negative order); rescale or narrow kmin..kmax")
    return {"k": np.ascontiguousarray(ks),
            "c": np.ascontiguousarray(coeffs, dtype=np.complex128),
            "center": centre, "radius": r}


def cplx_joukowski(z, c=1.0):
    """Joukowski (Zhukovsky) conformal map ``w = z + c^2 / z``.

    The classical aerofoil map (Zhukovsky 1910): the circle ``|z| = c`` folds
    onto the flat plate ``[-2c, 2c]`` of the real axis (``z = c e^(i t)`` gives
    ``w = 2c cos t`` — exact, and what the tests pin); a circle of radius
    ``R > c`` centred at the origin maps to the ellipse with semi-axes
    ``R + c^2/R`` and ``R - c^2/R``; and a circle through ``z = c`` whose
    centre is offset into the second quadrant maps to a cambered aerofoil with
    a cusped trailing edge — the reason the map exists.

    Conformal (angle-preserving) everywhere except at ``z = ±c``, where the
    derivative ``1 - c^2/z^2`` vanishes and angles are **doubled** — that is
    what creates the cusp, and it is a property of the map, not a defect.

    **Raises** ``ValueError``: a sample at ``z = 0`` (the map's pole), a result
    that overflowed (a sample so close to 0 that ``c^2/z`` leaves float64
    range), a non-finite or non-positive-real *c*, plus the usual shape and
    finiteness contracts.

    HALCON: no operator (conformal maps are not part of its transform set).
    """
    v = _require_cvector(z, "z", min_len=1)
    cc = _require_cscalar(c, "c")
    if cc.imag != 0.0 or cc.real <= 0.0:
        raise ValueError("c must be a positive real number, got %r" % (c,))
    zero = np.flatnonzero(v == 0.0)
    if zero.size:
        raise ValueError("cplx_joukowski: sample #%d is z = 0, the pole of "
                         "w = z + c^2/z — the map is undefined there"
                         % (int(zero[0]),))
    w = v + (cc.real * cc.real) / v
    _finite_result(w, "cplx_joukowski",
                   "a sample sits so close to the pole at 0 that c^2/z overflows "
                   "float64 — clip the path away from the origin")
    return np.ascontiguousarray(w, dtype=np.complex128)


def cplx_mobius(z, a, b, c, d):
    """Möbius (linear fractional) map ``w = (a z + b) / (c z + d)``.

    The automorphisms of the Riemann sphere: every Möbius map is conformal and
    sends circles-and-lines to circles-and-lines. Two standard cases the tests
    pin: the Cayley transform ``(z - i)/(z + i)`` maps the real axis onto the
    unit circle (``|w| = 1``) and ``i`` to ``0``; the inversion ``1/z`` maps the
    unit circle onto itself.

    The determinant ``a d - b c`` must not vanish — that degenerate case is not
    a map but a constant (every point collapses to ``a/c``), which is refused
    rather than returned as a suspiciously uniform answer.

    **Raises** ``ValueError``: ``|a d - b c|`` below ``1e-12`` of the
    coefficient scale (degenerate/constant map), a sample **at** the pole
    ``z = -d/c`` (the image is the point at infinity, which float64 cannot
    represent), an overflowed result (a sample microscopically close to that
    pole), plus the usual shape and finiteness contracts.

    HALCON: no operator (``projective_trans_point_2d`` is the real-plane
    projective analogue).
    """
    v = _require_cvector(z, "z", min_len=1)
    aa = _require_cscalar(a, "a")
    bb = _require_cscalar(b, "b")
    cc = _require_cscalar(c, "c")
    dd = _require_cscalar(d, "d")
    scale = max(abs(aa), abs(bb), abs(cc), abs(dd))
    det = aa * dd - bb * cc
    if abs(det) <= 1e-12 * max(1.0, scale * scale):
        raise ValueError("cplx_mobius: ad - bc = %r is degenerate at coefficient "
                         "scale %g — the map is constant (every z maps to the same "
                         "point), not a Möbius transformation" % (det, scale))
    den = cc * v + dd
    zero = np.flatnonzero(den == 0.0)
    if zero.size:
        raise ValueError("cplx_mobius: sample #%d is the pole z = -d/c, whose "
                         "image is the point at infinity — not representable in "
                         "float64; drop it or shift the path"
                         % (int(zero[0]),))
    w = (aa * v + bb) / den
    _finite_result(w, "cplx_mobius",
                   "a sample sits microscopically close to the pole z = -d/c and "
                   "its image overflows float64")
    return np.ascontiguousarray(w, dtype=np.complex128)


def cplx_cr_residual(f, spacing=1.0):
    """Cauchy-Riemann residual of a sampled complex field — "is this field
    holomorphic?" as a number.

    With ``f = u + i v`` sampled on a uniform grid, holomorphy means
    ``u_x = v_y`` and ``u_y = -v_x`` (Cauchy-Riemann). This returns the
    **relative** residual ``max(|u_x - v_y|, |u_y + v_x|) / max|grad|``
    (central differences, ``numpy.gradient``): ``0`` = the samples satisfy CR to
    the discretisation limit, ``2`` = the field is the conjugate of a
    holomorphic one (``conj(z)`` gives exactly 2), values in between = partly
    analytic or noisy.

    **Grid convention (it decides the sign of the answer)**: ``f[i, j]`` is the
    field at ``z = x0 + j*spacing + i*spacing*1j`` — rows index the *increasing
    imaginary* axis, columns the real axis. Image arrays usually run rows
    *downward*; feeding one directly measures the conjugate field, whose
    residual is ``2``, not ``0``. Flip rows (``f[::-1]``) to use image data.

    Discretisation, honestly: central differences are exact for polynomials of
    degree <= 2, so ``f = z**2`` returns exactly 0; for higher order the
    residual floors at ``O(h^2 * |f'''|)`` (measured: ``f = z**3`` on a
    ``[-1,1]^2`` grid returns @@ACC_CR_H@@ at ``h`` and @@ACC_CR_H2@@ at
    ``h/2`` — a factor @@ACC_CR_RATIO@@, the expected second order). Read a
    small value as "consistent with holomorphic at this resolution", never as
    proof.

    A constant field returns ``0.0`` (it is holomorphic; the ``0/0`` of the
    normalisation is resolved by that limit, and stated here rather than left
    to numpy).

    **Raises** ``ValueError``: not a 2-D array, either dimension below 3 (no
    central difference exists), non-finite/masked input, over-cap size,
    non-finite or non-positive *spacing*.

    HALCON: no operator (``derivate_gauss`` supplies the real-valued
    derivatives one would build this from).
    """
    if np.ma.is_masked(f):
        raise ValueError("f is a masked array with masked (invalid) entries — "
                         "fill or drop them explicitly")
    try:
        a = np.ascontiguousarray(f, dtype=np.complex128)
    except (TypeError, ValueError):
        raise ValueError("f must be a real or complex numeric array, got %s"
                         % (type(f).__name__,)) from None
    if a.ndim != 2:
        raise ValueError("f must be a 2-D sampled field, got a %d-D array of "
                         "shape %r" % (a.ndim, a.shape))
    if a.shape[0] < 3 or a.shape[1] < 3:
        raise ValueError("f must be at least 3x3 for central differences, got "
                         "shape %r" % (a.shape,))
    _require_finite(a, "f")
    _check_elements(a, "cplx_cr_residual")
    h = _require_cscalar(spacing, "spacing")
    if h.imag != 0.0 or h.real <= 0.0:
        raise ValueError("spacing must be a positive real number, got %r" % (spacing,))
    uy, ux = np.gradient(a.real, h.real, h.real)
    vy, vx = np.gradient(a.imag, h.real, h.real)
    resid = max(float(np.abs(ux - vy).max()), float(np.abs(uy + vx).max()))
    scale = max(float(np.abs(ux).max()), float(np.abs(uy).max()),
                float(np.abs(vx).max()), float(np.abs(vy).max()))
    if scale <= 0.0:
        return 0.0                      # constant field: holomorphic, residual 0
    return float(resid / scale)
