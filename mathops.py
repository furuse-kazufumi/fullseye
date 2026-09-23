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
    "interp_linear", "interp_cubic", "interp_scattered",
    "poly_fit", "poly_eval", "poly_roots",
    "cplx_contour_circle", "cplx_poly_eval", "cplx_contour_integral",
    "cplx_winding_number", "cplx_cauchy_value", "cplx_argument_principle",
    "cplx_laurent_coeffs", "cplx_joukowski", "cplx_mobius", "cplx_cr_residual",
    "cplx_plane_grid",
    "cplx_rational_field",
    "cplx_domain_colour",
    "cplx_newton_basins",
    "cplx_escape_time",
    "mandelbrot_interior",
    "potential_flow_joukowski",
    "joukowski_circulation",
    # 定理が門になる図(2026-09-23)。★`MATHOPS`(台帳が読む一覧)と `__all__`
    # (import * の公開面)は**別物**で、両方に書かないと片方だけ通る。
    "circle_packing_apollonian", "ford_circles",
    "phyllotaxis_pattern", "neighbour_index_gaps",
    "ifs_fractal", "ifs_similarity_dimension",
    "space_filling_curve", "curve_locality",
    # 波動と力学系(2026-09-23)。定数も公開面に出す(族名の一覧は利用者が読む)。
    "wave_membrane_mode", "wave_mode_frequencies", "wave_nodal_lines",
    "wave_two_slit", "wave_fringe_period", "wave_grating_orders",
    "ode_flow_states", "ode_vector_field_grid", "dynsys_poincare_section",
    "dynsys_lyapunov_spectrum", "dynsys_bifurcation_map",
    "dynsys_correlation_dimension",
    "DYNSYS_SYSTEMS", "DYNSYS_MAPS",
    "IFS_PRESETS", "CURVE_KINDS", "GOLDEN_ANGLE_DEG",
    "MATHOPS", "MAX_ELEMENTS", "POLY_COND_WARN", "MAX_CONTOUR_POINTS",
]

#: The public math operators, by name (introspection / facade wiring).
MATHOPS = [
    "mat_solve", "mat_lstsq", "mat_svd", "mat_eigh", "mat_pinv", "mat_cond",
    "stat_describe", "stat_histogram", "stat_covariance", "stat_correlation",
    "stat_zscore",
    "interp_linear", "interp_cubic", "interp_scattered",
    "poly_fit", "poly_eval", "poly_roots",
    "cplx_contour_circle", "cplx_poly_eval", "cplx_contour_integral",
    "cplx_winding_number", "cplx_cauchy_value", "cplx_argument_principle",
    "cplx_laurent_coeffs", "cplx_joukowski", "cplx_mobius", "cplx_cr_residual",
    "cplx_plane_grid",
    "cplx_rational_field",
    "cplx_domain_colour",
    "cplx_newton_basins",
    "cplx_escape_time",
    "mandelbrot_interior",
    "potential_flow_joukowski",
    "joukowski_circulation",
    # 定理が門になる図(2026-09-23)
    "circle_packing_apollonian",
    "ford_circles",
    "phyllotaxis_pattern",
    "neighbour_index_gaps",
    "ifs_fractal",
    "ifs_similarity_dimension",
    "space_filling_curve",
    "curve_locality",
    # 波動 —— 膜の固有モード・干渉・回折(2026-09-23)
    "wave_membrane_mode",
    "wave_mode_frequencies",
    "wave_nodal_lines",
    "wave_two_slit",
    "wave_fringe_period",
    "wave_grating_orders",
    # 力学系 —— 積む・断面・指数・分岐(2026-09-23)
    "ode_flow_states",
    "ode_vector_field_grid",
    "dynsys_poincare_section",
    "dynsys_lyapunov_spectrum",
    "dynsys_bifurcation_map",
    "dynsys_correlation_dimension",
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


def interp_scattered(points, values, query, method="linear",
                     fill_value=np.nan, rescale=False, neighbors=None):
    """Values at *query* from **scattered** samples — sensor nets, boreholes, weather.

    :func:`interp_linear` and :func:`interp_cubic` need samples on a sorted 1-D
    axis. A great deal of measurement does not arrive that way: temperature
    sensors bolted wherever a rack allowed, boreholes drilled where access
    permitted, weather stations placed by history. This is the N-D scattered
    entry point (``scipy.interpolate``), and it returns **how much of the answer
    was not interpolation at all**.

    *method*:

    ``"nearest"``
        the value of the closest sample. Defined everywhere, and never
        overshoots, but it is a staircase: on a smooth field the step itself
        becomes a false feature. Measured on a smooth 3-D field sampled at 0.60,
        the nearest-neighbour reconstruction leaves a residual of 0.975 units
        where the sensor noise is only 0.15 — 6.5 times the noise, and none of
        it is noise.
    ``"linear"``
        barycentric interpolation on a Delaunay triangulation. Never exceeds the
        surrounding samples, and is **undefined outside their convex hull**.
    ``"rbf"``
        a thin-plate radial basis function through every sample. Smooth and
        defined everywhere, but it **overshoots its own nodes**: measured on the
        same field it returns peaks 1.372 times the sampled height, which is a
        37 % over-statement of a hot spot that no interpolation of the data can
        justify.

    **The point of the ``outside`` return value.** Sensors sit inside a room, a
    site, a country; the corners are always outside their hull. Ask a linear
    interpolator there and it returns ``fill_value``, or, if a caller quietly
    falls back to nearest, it returns a different method's answer under the
    first method's name. Measured on a 12 x 8.4 x 3.0 m room sampled at 1.20 m
    spacing, **71.2 %** of the evaluation grid lay outside the hull. A number
    that large has to be visible, so it is returned rather than logged.

    Parameters
    ----------
    points : (n, d) array_like
        Sample coordinates. 1-D input is accepted and treated as ``(n, 1)``.
    values : (n,) array_like
    query : (m, d) or (..., d) array_like
        Where to evaluate. The leading shape is preserved in the result.
    method : {"linear", "nearest", "rbf"}
    fill_value : float
        Returned outside the convex hull for ``"linear"``. ``"nearest"`` and
        ``"rbf"`` are defined everywhere and ignore it.
    rescale : bool
        Normalise each axis before triangulating. Needed when the axes have very
        different units (metres against millimetres); ignored by ``"rbf"``.
    neighbors : int or None
        ``"rbf"`` only: solve against the *k* nearest samples instead of all of
        them. The global solve is O(n^3); measured on 5000 query points in 3-D,
        it costs 0.55 / 1.76 / 7.53 s at 1400 / 4000 / 8000 samples, while
        ``neighbors=48`` costs 0.38 / 0.55 / 0.81 s. Below a few thousand
        samples the global solve is fine and exact — the knob earns its place
        above that. ``None`` keeps the exact global solution.

    Returns
    -------
    dict
        ``value`` (query shape), ``outside`` (bool mask, query shape, of query
        points beyond the convex hull of the samples), ``outside_fraction``,
        ``method``, ``n_points``.

    Fail-closed: fewer samples than ``d + 1`` cannot define a simplex, and
    raises ``ValueError`` rather than returning a field made of ``fill_value``.

    See also
    --------
    interp_linear : the sorted 1-D case, which is cheaper and needs no hull.
    """
    pts = np.asarray(points, np.float64)
    if pts.ndim == 1:
        pts = pts[:, None]
    if pts.ndim != 2:
        raise ValueError("points must be (n, d), got shape %r" % (pts.shape,))
    val = np.asarray(values, np.float64).ravel()
    if val.size != pts.shape[0]:
        raise ValueError("values has %d entries for %d points"
                         % (val.size, pts.shape[0]))
    if not np.isfinite(pts).all() or not np.isfinite(val).all():
        raise ValueError("interp_scattered refuses non-finite points/values")
    d = pts.shape[1]
    if pts.shape[0] < d + 1:
        raise ValueError("need at least d+1 = %d samples in %d-D, got %d"
                         % (d + 1, d, pts.shape[0]))
    q = np.asarray(query, np.float64)
    if q.ndim == 1 and d == 1:
        q = q[:, None]
    if q.shape[-1] != d:
        raise ValueError("query last axis is %d, points are %d-D"
                         % (q.shape[-1], d))
    lead = q.shape[:-1]
    qf = q.reshape(-1, d)
    _check_elements(qf, "interp_scattered query")

    if d == 1:
        # 1-D の凸包は区間そのもの。Delaunay は 2-D 以上しか受けないので
        # ここで分ける(2026-09-08: 分けるまで 1-D は「(n,1) として受ける」と
        # docstring に書きながら qhull の "Need at least 2-D data" で落ちていた)。
        outside = (qf[:, 0] < pts[:, 0].min()) | (qf[:, 0] > pts[:, 0].max())
    else:
        from scipy.spatial import Delaunay
        scale = np.ptp(pts, axis=0) + 1e-300
        tri = Delaunay(pts / scale if rescale else pts)
        outside = tri.find_simplex(qf / scale if rescale else qf) < 0

    if method == "nearest":
        if d == 1:
            o = np.argsort(pts[:, 0])
            j = np.searchsorted(pts[o, 0], qf[:, 0])
            j = np.clip(j, 1, pts.shape[0] - 1)
            left = np.abs(qf[:, 0] - pts[o, 0][j - 1]) <= np.abs(pts[o, 0][j] - qf[:, 0])
            out = val[o][np.where(left, j - 1, j)]
        else:
            from scipy.interpolate import NearestNDInterpolator
            out = NearestNDInterpolator(pts, val)(qf)
    elif method == "linear":
        if d == 1:
            # 1-D は三角形分割が要らない(Delaunay も LinearNDInterpolator も
            # 2-D 以上しか受けない)。区間の外は fill_value のまま。
            o = np.argsort(pts[:, 0])
            out = np.interp(qf[:, 0], pts[o, 0], val[o])
            out = np.where(outside, fill_value, out)
        else:
            from scipy.interpolate import LinearNDInterpolator
            out = LinearNDInterpolator(pts, val, fill_value=fill_value,
                                       rescale=rescale)(qf)
    elif method == "rbf":
        from scipy.interpolate import RBFInterpolator
        nb = None if neighbors is None else max(1, min(int(neighbors), pts.shape[0]))
        out = RBFInterpolator(pts, val, neighbors=nb,
                              kernel="thin_plate_spline")(qf)
    else:
        raise ValueError("method must be 'linear', 'nearest' or 'rbf', got %r"
                         % (method,))
    return {"value": np.asarray(out, np.float64).reshape(lead),
            "outside": outside.reshape(lead),
            "outside_fraction": float(outside.mean()) if outside.size else 0.0,
            "method": method, "n_points": int(pts.shape[0])}


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
def _reject_text(x, name: str) -> None:
    """Refuse str/bytes data — numpy *parses* it into numbers silently.

    ``np.asarray(["0", "1", "1j"], dtype=complex)`` happily returns
    ``[0, 1, 1j]``, and ``w="0"`` is accepted as the origin: a config string or
    a mis-decoded CSV column would flow through the whole complex family
    looking like data (confirmed by the 2026-09-01 adversarial probe). Text is
    not a number here; parse it yourself if that is what you mean."""
    if isinstance(x, (str, bytes)):
        raise ValueError("%s must be a real or complex number, got %s — text is "
                         "not silently parsed into numbers (numpy would accept "
                         "\"0\" as the origin); convert it explicitly"
                         % (name, type(x).__name__))
    try:
        raw = np.asanyarray(x)
    except (TypeError, ValueError):
        return                              # not array-like: the caller's coercion reports it
    if raw.dtype.kind in "USV":
        raise ValueError("%s has text/void dtype %r — numpy would silently parse "
                         "the strings into numbers; convert them explicitly"
                         % (name, raw.dtype))


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
    _reject_text(z, name)
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
    _reject_text(w, name)
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

#: :func:`cplx_winding_number` emits a ``RuntimeWarning`` once the per-step turn
#: reaches this (half of the ``pi`` hard limit). Between ``pi/2`` and ``pi`` the
#: count is still *computable* but no longer *trustworthy*: a curve that winds
#: several times can alias down to a smaller integer without any local jump to
#: detect (measured: ``f = z**5`` on a 4-point circle counts 1 instead of 5).
WIND_ALIAS_WARN = np.pi / 2.0

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
                         "error is already ~7e-10 at 1e5 points (measured)"
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
    ``a = 0``, the relative error is 1.0e-4 at ``n = 256`` and
    6.3e-6 at ``n = 1024`` — a factor 16.0 for 4x
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

    Honest limitation — **the count can alias low, and no local check can stop
    it**: this is the winding number of the polygon *through the samples*,
    which equals that of the underlying curve only if the sampling resolves it.
    A segment that turns the ray to *w* by ``>= pi`` is ambiguous (which side
    did it pass?) and raises. Below that there is no contradiction to detect:
    ``z**5`` sampled on a 4-point circle turns exactly ``pi/2`` per step and
    counts **1** instead of 5 (measured). From ``pi/2`` up, a
    ``RuntimeWarning`` says so (``WIND_ALIAS_WARN``); the only real remedy is
    the classical one — refine until the count stops changing.

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
    peak = float(np.abs(inc).max())
    if peak >= WIND_ALIAS_WARN:
        warnings.warn("cplx_winding_number: the ray to %r turns by up to %.3f rad "
                      "between consecutive samples (%.0f%% of the pi limit) — the "
                      "count can alias LOW without any detectable jump; refine the "
                      "contour until the count stops changing"
                      % (p, peak, 100.0 * peak / np.pi),
                      RuntimeWarning, stacklevel=2)
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
    256-point unit circle, the absolute error is 9.0e-6 at ``w = 0.3`` and
    8.1e-5 at ``w = 0.9`` — 9x worse for a point 7x closer to the path
    (0.7 -> 0.1 of clearance). The blow-up is real but gradual; what it does
    *not* survive is clearance below one sampling step, which is refused.

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
      * It is the winding of the *sampled* image polygon, so it **aliases low**
        on a coarse contour. A half-turn jump between samples is detected and
        raised; anything below that is indistinguishable from a genuine slower
        turn — ``f = z**5`` on a 4-point circle returns 1, not 5 (measured).
        A ``RuntimeWarning`` fires from ``pi/2`` per step onward
        (:data:`WIND_ALIAS_WARN`); the verification that actually works is to
        double ``n`` until the count repeats.

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
    ``n = 64``: ``c_-1 = 1`` and ``c_-2 = 0.5`` to 1e-16 (machine precision).

    Returns a dict: ``k`` (int64 orders, ``kmin..kmax``) · ``c`` (complex128
    coefficients) · ``center`` · ``radius``. The centre is the sample mean,
    which is exact for a uniformly sampled circle.

    **Orientation, and how it differs from the rest of the family**: the sum
    runs over the sample *set*, not the sample *order*, so this op always
    returns the coefficients of the positively oriented circle — the standard
    definition — whatever order the points arrive in. Feed a clockwise circle
    and ``c_-1`` still comes back ``+`` the residue, while
    ``cplx_contour_integral / (2*pi*i)`` on the same points returns ``-`` it
    (verified). Both are right; they answer different questions (the intrinsic
    coefficient vs the integral along *this* traversal). Do not cross-check one
    against the other without fixing the orientation first.

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
    if kmax - kmin + 1 > n:
        raise ValueError("cplx_laurent_coeffs: %d coefficients requested from %d "
                         "samples — the discrete transform cannot resolve more "
                         "orders than it has points (they alias onto each other)"
                         % (kmax - kmin + 1, n))
    ks = np.arange(kmin, kmax + 1, dtype=np.int64)
    phase = np.exp(-1j * np.outer(ks.astype(np.float64), np.angle(c - centre)))
    # The r**k normaliser must be checked *before* dividing: it overflows to inf
    # for a small radius and a large negative order, and x/inf is a silent 0 —
    # the op then returned "all coefficients vanish" for a function with genuine
    # poles, with only a numpy RuntimeWarning (which tests/conftest.py ignores)
    # as evidence. Underflow to 0 is the mirror trap (x/0 -> inf). Both are the
    # documented ValueError now (2026-09-01 adversarial probe).
    with np.errstate(over="ignore", under="ignore"):
        scale = n * np.power(r, ks.astype(np.float64))
    if not (np.isfinite(scale).all() and np.all(scale != 0.0)):
        raise ValueError("cplx_laurent_coeffs: r**k left float64 range for radius "
                         "%g and orders %d..%d (the normaliser is %r) — the "
                         "coefficients would silently come back as zeros or "
                         "infinities; rescale the circle or narrow kmin..kmax"
                         % (r, kmin, kmax,
                            scale[~np.isfinite(scale) | (scale == 0.0)][0]))
    coeffs = (phase @ f) / scale
    _finite_result(coeffs, "cplx_laurent_coeffs",
                   "the coefficient sum itself overflowed float64 — the sampled "
                   "values are too large for this radius")
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
    ``[-1,1]^2`` grid returns 1.7e-3 at ``h`` and 4.2e-4 at
    ``h/2`` — a factor 4.00, the expected second order). Read a
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
    _reject_text(f, "f")
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
    # edge_order=2 is load-bearing, not a flourish: numpy's default (1) uses a
    # *first-order* one-sided difference on the border rows/columns, which is not
    # exact even for a quadratic — the exactly-holomorphic field z**2 then scored
    # a 2.5% residual (measured, h=0.05) purely from its frame. Second-order
    # edges make the whole grid exact to degree 2, as the docstring claims.
    uy, ux = np.gradient(a.real, h.real, h.real, edge_order=2)
    vy, vx = np.gradient(a.imag, h.real, h.real, edge_order=2)
    resid = max(float(np.abs(ux - vy).max()), float(np.abs(uy + vx).max()))
    scale = max(float(np.abs(ux).max()), float(np.abs(uy).max()),
                float(np.abs(vx).max()), float(np.abs(vy).max()))
    if scale <= 0.0:
        return 0.0                      # constant field: holomorphic, residual 0
    return float(resid / scale)


# --------------------------------------------------------------------------- #
# 複素平面を「面」で見る(2026-09-22)—— tier2 は曲線の上の話しかしていない   #
#   ★既存の cplx_* は閉曲線を点列で持つ層(積分・巻き数・ローラン・等角写像)。#
#   ここで足すのは**領域**の層 —— 値の場・位相彩色・ニュートンの吸引域・      #
#   脱出時間・翼まわりのポテンシャル流。新しい語は 1 つも作らない             #
#   (cimage / rgbimage / labels2d / mask / roots / signal はすべて既存)。     #
#   真値は「使った式」ではなく、偏角の原理・Cayley の定理・主カージオイドの   #
#   閉形式内部判定・c=0 のジュリア集合(単位円板)・そして既存 op である       #
#   cplx_winding_number / cplx_cr_residual / cplx_joukowski / poly_roots。     #
# --------------------------------------------------------------------------- #
_MAX_FIELD_PIXELS = 4_194_304          # 2048 x 2048。これ以上は拒む(暗黙に重くしない)
_MIN_SIDE = 4


# --------------------------------------------------------------------------- #
# 共通 —— 面のとり方                                                           #
# --------------------------------------------------------------------------- #
def _require_field_shape(shape, op):
    try:
        h, w = (int(shape[0]), int(shape[1]))
    except Exception:
        raise ValueError("%s: shape must be a pair of ints, got %r" % (op, shape))
    if h < _MIN_SIDE or w < _MIN_SIDE:
        raise ValueError("%s: shape %dx%d is smaller than %dx%d — a field that small "
                         "cannot resolve anything" % (op, h, w, _MIN_SIDE, _MIN_SIDE))
    if h * w > _MAX_FIELD_PIXELS:
        raise ValueError("%s: shape %dx%d = %d pixels exceeds the %d cap; ask for a "
                         "smaller window rather than a bigger grid"
                         % (op, h, w, h * w, _MAX_FIELD_PIXELS))
    return h, w


def _require_field_centre(centre, op):
    try:
        c = complex(centre)
    except Exception:
        raise ValueError("%s: centre must be a complex number, got %r" % (op, centre))
    if not np.isfinite(c.real) or not np.isfinite(c.imag):
        raise ValueError("%s: centre %r is not finite" % (op, c))
    return c


def _require_field_half_width(half_width, op):
    hw = float(half_width)
    if not np.isfinite(hw) or hw <= 0.0:
        raise ValueError("%s: half_width must be finite and positive, got %r"
                         % (op, half_width))
    return hw


def cplx_plane_grid(centre=0j, half_width=2.0, shape=(256, 256)):
    """複素平面の矩形窓を格子にする(画像と同じ並び: 行 0 が上 = 虚部が大きい側)。

    返すのは ``(h, w)`` の複素配列。実部は ``[-half_width, +half_width]`` を
    ``w`` 点で等間隔、虚部は**アスペクト比を保って** ``h`` 点。窓が正方形でない
    ときに円が楕円に潰れないようにするためで、``half_width`` は常に**横**半幅。
    """
    op = "cplx_plane_grid"
    h, w = _require_field_shape(shape, op)
    c = _require_field_centre(centre, op)
    hw = _require_field_half_width(half_width, op)
    hh = hw * (h / float(w))
    re = np.linspace(c.real - hw, c.real + hw, w)
    im = np.linspace(c.imag + hh, c.imag - hh, h)          # 行 0 が上
    return re[None, :] + 1j * im[:, None]


def _require_root_vector(r, name, op, allow_empty=True):
    a = np.asarray(r)
    if a.dtype.kind in "SU":
        raise ValueError("%s: %s must be numbers, got text" % (op, name))
    a = np.atleast_1d(np.asarray(a, dtype=np.complex128).ravel())
    if a.size == 0:
        if allow_empty:
            return a
        raise ValueError("%s: %s is empty" % (op, name))
    if not np.all(np.isfinite(a)):
        raise ValueError("%s: %s contains a non-finite value" % (op, name))
    return a


# --------------------------------------------------------------------------- #
# 1. 有理関数の値の場                                                          #
# --------------------------------------------------------------------------- #
def cplx_rational_field(zeros, poles, gain=1.0, centre=0j, half_width=2.0,
                        shape=(256, 256)):
    """Sample a rational function ``R(z) = gain * prod(z - zeros) / prod(z - poles)``.

    Returns the complex image ``R(z)`` over a rectangular window of the plane —
    the *area* counterpart of this family's contour operators. The product is
    formed in log space (``exp(sum(log(z - zk)) - sum(log(z - pm)))``) so a
    degree-30 numerator does not overflow before the denominator can divide it
    back down; the branch cuts of the individual logarithms cancel in the
    exponential, so the result is the ordinary principal value of the quotient,
    not a branch of it.

    ★**Why this earns its place**: the field is not decoration. The argument
    principle says that the winding number of ``R`` along a closed contour
    equals *(zeros inside) - (poles inside)*, counted with multiplicity — so
    this family's own ``cplx_argument_principle`` / ``cplx_winding_number``
    are an independent oracle for every field this operator produces, and
    :func:`cplx_domain_colour` makes that integer **visible** as the number of
    times the hue cycles.

    Parameters
    ----------
    zeros, poles : complex array-like
        Roots of the numerator and denominator, repeated for multiplicity.
        Either may be empty (a polynomial, or ``1/q``). ``poly_roots`` produces
        exactly this ``roots`` vocabulary.
    gain : complex
        Leading coefficient.
    centre, half_width, shape :
        The window, as in :func:`cplx_plane_grid`.

    **Raises** ``ValueError``: a pole (or zero) lands *exactly* on a sample, so
    the value there is not a number — nudge ``centre`` by half a pixel or take
    an odd ``shape`` (the message says which pole and where); non-finite input;
    the window is degenerate; the result overflows to infinity anyway (the gain
    and the window disagree by more than float64 can hold).

    HALCON: no operator (HALCON has no complex-plane family).
    """
    op = "cplx_rational_field"
    z = cplx_plane_grid(centre, half_width, shape)
    zs = _require_root_vector(zeros, "zeros", op)
    ps = _require_root_vector(poles, "poles", op)
    g = complex(gain)
    if not (np.isfinite(g.real) and np.isfinite(g.imag)):
        raise ValueError("%s: gain %r is not finite" % (op, g))
    if g == 0:
        raise ValueError("%s: gain is 0 — the field would be identically zero, "
                         "which says nothing about the zeros and poles you gave"
                         % op)

    for who, arr in (("pole", ps), ("zero", zs)):
        for k, r in enumerate(arr):
            hit = np.flatnonzero(z.ravel() == r)
            if hit.size and who == "pole":
                i = int(hit[0])
                raise ValueError(
                    "%s: %s #%d (%r) lands exactly on sample (row %d, col %d), where "
                    "the field is infinite. Shift the window by half a pixel "
                    "(centre += %r) or use an odd shape."
                    % (op, who, k, r, i // z.shape[1], i % z.shape[1],
                       complex(half_width / float(z.shape[1]), 0.0)))

    acc = np.full(z.shape, np.log(g) if g != 1 else 0.0 + 0.0j, dtype=np.complex128)
    for r in zs:
        d = z - r
        with np.errstate(divide="ignore", invalid="ignore"):
            acc = acc + np.log(d)
        acc = np.where(d == 0, -np.inf + 0j, acc)          # 零点は厳密に 0 にする
    for r in ps:
        acc = acc - np.log(z - r)
    out = np.exp(acc)
    out = np.where(np.isneginf(acc.real), 0.0 + 0.0j, out)

    if not np.all(np.isfinite(out)):
        n = int((~np.isfinite(out)).sum())
        raise ValueError("%s: %d of %d samples overflowed to a non-finite value — "
                         "the window and the gain disagree by more than float64 can "
                         "hold. Shrink half_width or the gain." % (op, n, out.size))
    return out


# --------------------------------------------------------------------------- #
# 2. 位相彩色                                                                  #
# --------------------------------------------------------------------------- #
def _cplx_hsv_to_rgb(h, s, v):
    """(h, s, v) in [0,1] -> (..., 3) float RGB。numpy だけで書く(依存を足さない)。"""
    h = np.mod(np.asarray(h, dtype=np.float64), 1.0) * 6.0
    i = np.floor(h).astype(np.int64)
    f = h - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i = np.mod(i, 6)
    r = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [v, q, p, p, t, v])
    g = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [t, v, v, q, p, p])
    b = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=-1)


def cplx_domain_colour(field, gamma=1.0, bands=0.0, saturation=1.0):
    """Domain colouring: turn a complex field into an RGB image you can read.

    Hue carries ``arg(z)`` (one full turn of the colour wheel per turn of the
    argument, red at ``arg = 0``); value carries ``|z|`` through the **strictly
    increasing** map ``t/(1+t)`` with ``t = |z|**gamma``, so a zero is exactly
    black, ``|z| = 1`` is half brightness and a large modulus saturates at full
    brightness. The saturation is **not** dropped far from the origin, so the
    hue — and with it the argument — stays readable everywhere; pass
    ``saturation = 0`` for a plain grey ramp of the modulus alone. With
    ``bands = 0`` (the default) the
    brightness is monotone in ``|z|``, which means the picture is *invertible*:
    the argument comes back out of the hue and the modulus out of the value.

    ★**The picture proves a theorem.** Walk a small circle around a zero of
    order *m* and the hue cycles through the colour wheel exactly *m* times;
    around a pole of order *m*, *m* times the other way. That is the argument
    principle, read off the image with no numbers — and this family's
    ``cplx_winding_number`` counts the same integer from the field itself, so
    the drawing and the arithmetic check each other.

    Parameters
    ----------
    field : complex 2-D array (``cimage``)
        Typically from :func:`cplx_rational_field`.
    gamma : float > 0
        Compresses (``<1``) or stretches (``>1``) the modulus ramp.
    bands : float >= 0
        Classic modulus contours: ``bands`` shading cycles per decade of
        ``|z|``. **Non-zero breaks monotonicity** (that is the point — it draws
        level lines), so the inverse-mapping guarantee above holds only at 0.
    saturation : float in [0, 1]

    **Raises** ``ValueError``: not a 2-D complex array; non-finite samples
    (a pole sampled exactly — see :func:`cplx_rational_field`); ``gamma <= 0``;
    ``bands < 0``; ``saturation`` outside [0, 1].

    HALCON: no operator.
    """
    op = "cplx_domain_colour"
    a = np.asarray(field)
    if a.dtype.kind in "SU":
        raise ValueError("%s: field must be numbers, got text" % op)
    if a.ndim != 2:
        raise ValueError("%s: field must be a 2-D complex image, got ndim=%d"
                         % (op, a.ndim))
    if a.dtype.kind != "c":
        a = a.astype(np.complex128)
    if a.size == 0:
        raise ValueError("%s: field is empty" % op)
    if not np.all(np.isfinite(a)):
        n = int((~np.isfinite(a)).sum())
        raise ValueError("%s: %d of %d samples are not finite — a pole was sampled "
                         "exactly; shift the window by half a pixel"
                         % (op, n, a.size))
    g = float(gamma)
    if not np.isfinite(g) or g <= 0.0:
        raise ValueError("%s: gamma must be finite and positive, got %r" % (op, gamma))
    bd = float(bands)
    if not np.isfinite(bd) or bd < 0.0:
        raise ValueError("%s: bands must be finite and >= 0, got %r" % (op, bands))
    sat = float(saturation)
    if not (0.0 <= sat <= 1.0):
        raise ValueError("%s: saturation must lie in [0, 1], got %r" % (op, saturation))

    mod = np.abs(a)
    hue = np.mod(np.angle(a) / (2.0 * np.pi), 1.0)
    t = mod ** g
    val = t / (1.0 + t)                                     # 厳密に単調増加
    if bd > 0.0:
        with np.errstate(divide="ignore"):
            dec = np.where(mod > 0.0, np.log10(np.maximum(mod, 1e-300)), -300.0)
        saw = np.mod(dec * bd, 1.0)
        val = np.clip(val * (0.75 + 0.25 * saw), 0.0, 1.0)
    s = np.where(mod > 0.0, sat, 0.0)                       # 零点は無彩色の黒
    return np.clip(_cplx_hsv_to_rgb(hue, s, val), 0.0, 1.0)


# --------------------------------------------------------------------------- #
# 3. ニュートン法の吸引域                                                      #
# --------------------------------------------------------------------------- #
def _cplx_canonical_roots(coeffs, op):
    c = np.asarray(coeffs)
    if c.dtype.kind in "SU":
        raise ValueError("%s: coeffs must be numbers, got text" % op)
    c = np.atleast_1d(np.asarray(c, dtype=np.complex128).ravel())
    if not np.all(np.isfinite(c)):
        raise ValueError("%s: coeffs contains a non-finite value" % op)
    nz = np.flatnonzero(c != 0)
    if nz.size == 0:
        raise ValueError("%s: coeffs is identically zero — every point is a root "
                         "and there is nothing to separate" % op)
    c = c[nz[0]:]
    if c.size < 2:
        raise ValueError("%s: the polynomial is a non-zero constant — it has no "
                         "roots and Newton's method never converges" % op)
    r = np.roots(c)
    order = np.lexsort((np.round(r.imag, 12), np.round(r.real, 12)))
    return c, r[order]


def cplx_newton_basins(coeffs, centre=0j, half_width=2.0, shape=(256, 256),
                       max_iter=64, tol=1e-10):
    """Which root of a polynomial does Newton's method fall into, from each point?

    Labels the window ``1..len(roots)`` by the root reached, and ``0`` where the
    iteration has not converged within ``max_iter`` (the Julia set and its
    neighbourhood). Roots come from ``numpy.roots`` — the same routine behind
    this family's ``poly_roots`` — and are sorted by ``(Re, Im)`` so the label
    of a given root does not change between runs.

    ★**Degree 2 has a closed-form answer, so the operator can be checked
    exactly rather than plausibly.** Cayley (1879): for ``z**2 - 1`` the basins
    are the two open half-planes ``Re z > 0`` and ``Re z < 0``, and the boundary
    is the imaginary axis — no fractal. The famous fractal boundary appears at
    degree 3, which Cayley could not settle; there the honest checks are
    structural (every root's basin is non-empty; ``z**3 - 1`` is invariant under
    rotation by ``2*pi/3``, and so is its labelling, up to the cyclic
    relabelling of the roots).

    ``coeffs`` is highest-degree-first, as ``numpy.roots`` and ``poly_roots``
    take it.

    **Raises** ``ValueError``: text, non-finite or all-zero coefficients; a
    non-zero constant (no roots); ``max_iter < 1``; ``tol <= 0``; degenerate
    window. Points where the derivative vanishes are left unconverged (label
    ``0``) rather than divided by — a critical point is genuinely undecided.

    HALCON: no operator.
    """
    op = "cplx_newton_basins"
    c, roots = _cplx_canonical_roots(coeffs, op)
    z = cplx_plane_grid(centre, half_width, shape)
    mi = int(max_iter)
    if mi < 1:
        raise ValueError("%s: max_iter must be >= 1, got %r" % (op, max_iter))
    tl = float(tol)
    if not np.isfinite(tl) or tl <= 0.0:
        raise ValueError("%s: tol must be finite and positive, got %r" % (op, tol))

    d = c[:-1] * np.arange(c.size - 1, 0, -1)               # 導関数の係数
    cur = z.astype(np.complex128).copy()
    alive = np.ones(cur.shape, dtype=bool)
    for _ in range(mi):
        if not alive.any():
            break
        p = np.polyval(c, cur)
        q = np.polyval(d, cur)
        step = np.zeros_like(cur)
        ok = alive & (q != 0) & np.isfinite(q) & np.isfinite(p)
        step[ok] = p[ok] / q[ok]
        cur = np.where(ok, cur - step, cur)
        alive &= ok
        alive &= np.isfinite(cur)
        alive &= np.abs(step) > tl

    lab = np.zeros(cur.shape, dtype=np.int32)
    done = np.isfinite(cur) & ~alive
    if done.any():
        dist = np.abs(cur[done][:, None] - roots[None, :])
        near = np.argmin(dist, axis=1)
        good = dist[np.arange(near.size), near] <= max(1e-6, 1e3 * tl)
        idx = np.flatnonzero(done.ravel())
        flat = lab.ravel()
        flat[idx[good]] = (near[good] + 1).astype(np.int32)
        lab = flat.reshape(lab.shape)
    return lab


# --------------------------------------------------------------------------- #
# 4. 脱出時間                                                                  #
# --------------------------------------------------------------------------- #
ESCAPE_KINDS = ("mandelbrot", "julia")


def cplx_escape_time(kind="mandelbrot", param=0j, centre=0j, half_width=2.0,
                     shape=(256, 256), max_iter=64, escape_radius=2.0):
    """How many steps of ``z -> z**2 + c`` it takes to leave the escape disc.

    ``kind="mandelbrot"`` varies ``c`` over the window from ``z = 0``;
    ``kind="julia"`` fixes ``c = param`` and varies the starting ``z``. The
    result is a float image of iteration counts; points that never escape carry
    ``max_iter``.

    ★**This one is gated by theorems, not by a reference picture.**
      - *Escape radius*: once ``|z| > 2`` (with ``|c| <= 2``) the orbit diverges,
        so ``escape_radius = 2`` is not a tuning knob but the exact threshold.
      - *Main cardioid*: ``c`` lies in the main cardioid iff the fixed point
        ``z* = (1 - sqrt(1 - 4c)) / 2`` is attracting, i.e. ``|2 z*| < 1``.
        Every such ``c`` **provably never escapes**, so those pixels must read
        exactly ``max_iter`` — a closed-form interior test for a set usually
        drawn by iteration alone. The period-2 bulb ``|c + 1| < 1/4`` is the
        same kind of statement.
      - *Symmetry*: both families are invariant under conjugation, so the image
        must be **exactly** mirror-symmetric about the real axis (bit for bit,
        not to a tolerance) when the window is.

    **Raises** ``ValueError``: unknown ``kind``; non-finite ``param``;
    ``max_iter < 1``; ``escape_radius <= 0``; degenerate window.

    HALCON: no operator.
    """
    op = "cplx_escape_time"
    if kind not in ESCAPE_KINDS:
        raise ValueError("%s: kind must be one of %r, got %r" % (op, ESCAPE_KINDS, kind))
    grid = cplx_plane_grid(centre, half_width, shape)
    mi = int(max_iter)
    if mi < 1:
        raise ValueError("%s: max_iter must be >= 1, got %r" % (op, max_iter))
    rr = float(escape_radius)
    if not np.isfinite(rr) or rr <= 0.0:
        raise ValueError("%s: escape_radius must be finite and positive, got %r"
                         % (op, escape_radius))
    p = complex(param)
    if not (np.isfinite(p.real) and np.isfinite(p.imag)):
        raise ValueError("%s: param %r is not finite" % (op, p))

    if kind == "mandelbrot":
        c = grid
        z = np.zeros_like(grid)
    else:
        c = np.full(grid.shape, p, dtype=np.complex128)
        z = grid.astype(np.complex128).copy()

    out = np.full(grid.shape, float(mi))
    alive = np.ones(grid.shape, dtype=bool)
    r2 = rr * rr
    for n in range(mi):
        z = np.where(alive, z * z + c, z)
        gone = alive & ((z.real * z.real + z.imag * z.imag) > r2)
        out[gone] = float(n + 1)
        alive &= ~gone
        if not alive.any():
            break
    return out


def mandelbrot_interior(c):
    """Closed-form interior test for the main cardioid and the period-2 bulb.

    Returns a boolean array: ``True`` where ``c`` is **provably** in the
    Mandelbrot set, because the period-1 fixed point is attracting
    (``|1 - sqrt(1 - 4c)| < 1``) or ``c`` lies in the period-2 bulb
    (``|c + 1| < 1/4``). ``False`` means "not proven by these two tests" — the
    smaller bulbs and the filaments are not covered, so this is a **lower
    bound** on the set, which is exactly what makes it usable as a gate:
    :func:`cplx_escape_time` must return ``max_iter`` everywhere this is True,
    and no tolerance is involved.
    """
    a = np.asarray(c, dtype=np.complex128)
    card = np.abs(1.0 - np.sqrt(1.0 - 4.0 * a)) < 1.0
    bulb = np.abs(a + 1.0) < 0.25
    return card | bulb


# --------------------------------------------------------------------------- #
# 5. ジューコフスキー翼まわりのポテンシャル流                                  #
# --------------------------------------------------------------------------- #
def _joukowski_circle(op, chord_b, centre_offset):
    b = float(chord_b)
    if not np.isfinite(b) or b <= 0.0:
        raise ValueError("%s: chord_b must be finite and positive, got %r"
                         % (op, chord_b))
    mu = complex(centre_offset)
    if not (np.isfinite(mu.real) and np.isfinite(mu.imag)):
        raise ValueError("%s: centre_offset %r is not finite" % (op, mu))
    if mu.real >= b:
        raise ValueError("%s: centre_offset has Re = %g >= chord_b = %g, so the "
                         "circle does not enclose the leading-edge singularity at "
                         "-chord_b and the image is not an aerofoil"
                         % (op, mu.real, b))
    a = abs(b - mu)                       # 円が後縁 zeta = +b を通るための半径
    # ★もう一方の臨界点 -b は円の**内側**になければならない。外に出ると dz/dzeta = 0
    #   が流れの領域に現れ、そこで速度が発散する(翼でなく尖りが 2 つある図形になる)。
    if abs(-b - mu) >= a - 1e-12:
        raise ValueError("%s: the circle |zeta - %r| = %g does not strictly contain "
                         "the other critical point %g (distance %g), so dz/dzeta "
                         "vanishes in the flow region and the velocity blows up "
                         "there; keep Re(centre_offset) negative and small"
                         % (op, mu, a, -b, abs(-b - mu)))
    beta = -np.angle(b - mu)              # 有効キャンバ角(b - mu = a e^{-i beta})
    return b, mu, a, beta


def potential_flow_joukowski(alpha_deg=5.0, speed=1.0, chord_b=1.0,
                             centre_offset=-0.09 + 0.09j, centre=0j,
                             half_width=3.0, shape=(256, 256)):
    """Inviscid flow past a Joukowski aerofoil, as a complex velocity field.

    Returns the **complex velocity** ``w(z) = dW/dz = u - i*v`` sampled over a
    window of the physical plane. Inside the solid body the field is set to
    exactly ``0`` (there is no flow there), so ``field == 0`` is the body mask
    and nothing is silently ``nan``.

    The construction is the classical one: flow past a circle of radius
    ``a = |chord_b - centre_offset|`` centred at ``centre_offset``, plus the
    circulation the **Kutta condition** demands, pushed through the Joukowski
    map ``z = zeta + chord_b**2 / zeta``. The window is inverted back to the
    circle plane by choosing, of the two preimages, the one outside the circle.

    ★**What makes this checkable rather than merely plotted**:
      - The field is holomorphic outside the body, so this family's own
        ``cplx_cr_residual`` must read ~0 on it — an existing operator is the
        oracle, and it is not the formula used to build the field.
      - The **Kutta condition** is the whole point: ``dW/dzeta`` vanishes at the
        trailing edge exactly where ``dz/dzeta`` does, so the velocity there
        stays finite. Perturb the circulation by any amount and the trailing-edge
        velocity diverges — the gate has a control group.
      - ``Re(closed integral of w dz)`` around the body is the circulation, and
        it is **path independent** (Cauchy) — a big rectangle and a small one
        must agree.
      - Far from the body ``w -> speed * exp(-i*alpha)``, decaying like ``1/|z|``.
      - The zeroed region is the aerofoil, whose area the shoelace formula on
        ``cplx_joukowski`` of the circle gives independently.

    Parameters
    ----------
    alpha_deg : float
        Angle of attack in degrees.
    speed : float > 0
        Free-stream speed.
    chord_b : float > 0
        Half the flat-plate chord; the map is ``zeta + chord_b**2/zeta``.
    centre_offset : complex
        Circle centre. Negative real part thickens, positive imaginary part
        cambers. The default is a thin cambered section.
    centre, half_width, shape :
        The window in the physical plane, as in :func:`cplx_plane_grid`.

    **Raises** ``ValueError``: ``speed <= 0``; non-finite angle; a circle that
    does not enclose ``-chord_b`` (the image would fold over itself) or whose
    centre is at or beyond ``+chord_b``; degenerate window.

    HALCON: no operator.
    """
    op = "potential_flow_joukowski"
    b, mu, a, beta = _joukowski_circle(op, chord_b, centre_offset)
    u = float(speed)
    if not np.isfinite(u) or u <= 0.0:
        raise ValueError("%s: speed must be finite and positive, got %r" % (op, speed))
    ad = float(alpha_deg)
    if not np.isfinite(ad):
        raise ValueError("%s: alpha_deg %r is not finite" % (op, alpha_deg))
    alpha = np.deg2rad(ad)
    gamma = 4.0 * np.pi * a * u * np.sin(alpha + beta)      # クッタ条件

    z = cplx_plane_grid(centre, half_width, shape)
    root = np.sqrt(z * z - 4.0 * b * b)
    z1 = 0.5 * (z + root)
    z2 = 0.5 * (z - root)
    take1 = np.abs(z1 - mu) >= np.abs(z2 - mu)
    zeta = np.where(take1, z1, z2)

    outside = np.abs(zeta - mu) >= a
    d = zeta - mu
    with np.errstate(divide="ignore", invalid="ignore"):
        dwdz = (u * (np.exp(-1j * alpha) - a * a * np.exp(1j * alpha) / (d * d))
                + 1j * gamma / (2.0 * np.pi * d))
        dzdzeta = 1.0 - (b * b) / (zeta * zeta)
        w = dwdz / dzdzeta
    w = np.where(outside & np.isfinite(w), w, 0.0 + 0.0j)
    return w


def joukowski_circulation(alpha_deg=5.0, speed=1.0, chord_b=1.0,
                          centre_offset=-0.09 + 0.09j):
    """The Kutta circulation ``Gamma = 4*pi*a*U*sin(alpha + beta)`` for that section.

    Provided so a caller can state the lift without re-deriving the geometry:
    Kutta-Joukowski gives ``L = rho * U * Gamma`` per unit span, perpendicular to
    the free stream. The sign convention matches
    :func:`potential_flow_joukowski`, whose field integrates to ``-Gamma``
    counter-clockwise around the body (clockwise circulation is what lifts).
    """
    op = "joukowski_circulation"
    b, mu, a, beta = _joukowski_circle(op, chord_b, centre_offset)
    u = float(speed)
    if not np.isfinite(u) or u <= 0.0:
        raise ValueError("%s: speed must be finite and positive, got %r" % (op, speed))
    return float(4.0 * np.pi * a * u * np.sin(np.deg2rad(float(alpha_deg)) + beta))


# ------------------------------------------------------------------------- #
# 定理が門になる図(2026-09-23)
#
# ★どれも「きれいな図」だが、**採ったのはきれいだからではなく、
#   正しさを定理が言えるから**である。数学の図はきれいなので、合って
#   いるかを誰も確かめない —— だから絵の外に真値を置く:
#
#     circle_packing_apollonian  デカルトの円定理(厳密な代数等式)+ 整数充填
#     ford_circles               接するのは |ps - qr| = 1 のときに限る(整数で厳密)
#     phyllotaxis_pattern        隣の番号差がフィボナッチ数(黄金角のときだけ)
#     ifs_fractal                モランの式 sum r^d = 1 と、既存 fractal_dimension
#     space_filling_curve        4^n 点をちょうど 1 回ずつ・隣は必ず距離 1
#
#   相棒(neighbour_index_gaps / ifs_similarity_dimension / curve_locality)は
#   **主張を数にする側**で、これが無いと「それらしい絵」しか残らない。
# ------------------------------------------------------------------------- #

_THM_MAX_CIRCLES = 200_000

_THM_MAX_POINTS = 2_000_000

GOLDEN_ANGLE_DEG = 180.0 * (3.0 - np.sqrt(5.0))          # 137.50776...

IFS_PRESETS = ("sierpinski", "koch", "cantor_dust", "barnsley_fern", "dragon")

_IFS_MAP_TABLE = {
    # (a, b, c, d, e, f) = [[a b],[c d]] x + [e f]
    "sierpinski": [(.5, 0, 0, .5, 0, 0), (.5, 0, 0, .5, .5, 0), (.5, 0, 0, .5, .25, .5)],
    "koch": [(1 / 3., 0, 0, 1 / 3., 0, 0),
             (1 / 6., -np.sqrt(3) / 6, np.sqrt(3) / 6, 1 / 6., 1 / 3., 0),
             (1 / 6., np.sqrt(3) / 6, -np.sqrt(3) / 6, 1 / 6., .5, np.sqrt(3) / 6),
             (1 / 3., 0, 0, 1 / 3., 2 / 3., 0)],
    "cantor_dust": [(1 / 3., 0, 0, 1 / 3., 0, 0), (1 / 3., 0, 0, 1 / 3., 2 / 3., 0),
                    (1 / 3., 0, 0, 1 / 3., 0, 2 / 3.), (1 / 3., 0, 0, 1 / 3., 2 / 3., 2 / 3.)],
    "barnsley_fern": [(0, 0, 0, .16, 0, 0), (.85, .04, -.04, .85, 0, 1.6),
                      (.2, -.26, .23, .22, 0, 1.6), (-.15, .28, .26, .24, 0, .44)],
    "dragon": [(.5, -.5, .5, .5, 0, 0), (-.5, -.5, .5, -.5, 1, 0)],
}

_IFS_MAP_WEIGHTS = {"barnsley_fern": (0.01, 0.85, 0.07, 0.07)}

CURVE_KINDS = ("hilbert", "moore", "row_major", "boustrophedon")


def circle_packing_apollonian(curvatures=(-1.0, 2.0, 2.0, 3.0), depth=4,
                              min_curvature=0.0):
    """Apollonian gasket from a Descartes quadruple — every circle a theorem.

    Four mutually tangent circles satisfy the **Descartes circle theorem**

        (k1 + k2 + k3 + k4)**2 == 2 * (k1**2 + k2**2 + k3**2 + k4**2)

    where ``k = 1/r`` is the curvature (negative for the enclosing circle). The
    theorem is quadratic in ``k4``, so a triple of mutually tangent circles has
    **two** solutions and the second is ``k4' = 2*(k1+k2+k3) - k4``; recursing on
    that reflection fills the gasket. The centres follow the complex form
    ``k4*z4 = k1*z1 + k2*z2 + k3*z3 +- 2*sqrt(k1*k2*z1*z2 + ...)``, so no
    geometry is fitted — every circle is produced by an exact algebraic step.

    ★**Why this earns its place**: the drawing carries its own proof. Each circle
    can be checked against Descartes to machine precision, tangency is
    ``|z_i - z_j| == |r_i +- r_j|`` exactly, and **an integral quadruple stays
    integral for ever** — start from ``(-1, 2, 2, 3)`` and every curvature in the
    infinite packing is an integer (Lagarias-Mallows-Wilks). A drawing routine
    that is slightly wrong cannot keep integers integral.

    Parameters
    ----------
    curvatures : 4 floats
        A Descartes quadruple. The default ``(-1, 2, 2, 3)`` is the smallest
        integral gasket. Must satisfy the theorem to ``1e-9`` relative.
    depth : int >= 0
        Reflection levels. Level 0 is the four seed circles; each further level
        adds ``4 * 3**(level-1)``, so the total is ``2 * 3**depth + 2``.
    min_curvature : float
        Drop circles smaller than ``1/min_curvature`` (0 = keep all).

    Returns a ``table``: ``x``, ``y``, ``radius``, ``curvature``, ``depth``
    (the enclosing circle has negative curvature and positive radius).

    **Raises** ``ValueError``: not four curvatures; the quadruple does not
    satisfy Descartes; every curvature negative or zero (no packing); ``depth``
    negative or so large the packing exceeds the cap; non-finite input.

    HALCON: no operator.
    """
    op = "circle_packing_apollonian"
    k = np.asarray(curvatures, dtype=np.float64).ravel()
    if k.size != 4:
        raise ValueError("%s: need exactly 4 curvatures, got %d" % (op, k.size))
    if not np.all(np.isfinite(k)):
        raise ValueError("%s: curvatures contain a non-finite value" % op)
    lhs = float(k.sum()) ** 2
    rhs = 2.0 * float((k * k).sum())
    scale = max(abs(lhs), abs(rhs), 1.0)
    if abs(lhs - rhs) > 1e-9 * scale:
        raise ValueError("%s: the four curvatures are not a Descartes quadruple — "
                         "(sum k)^2 = %g but 2*sum(k^2) = %g (relative gap %.2e). "
                         "Four mutually tangent circles must satisfy the theorem."
                         % (op, lhs, rhs, abs(lhs - rhs) / scale))
    if np.all(k <= 0):
        raise ValueError("%s: every curvature is <= 0 — there is nothing to pack" % op)
    d = int(depth)
    if d < 0:
        raise ValueError("%s: depth must be >= 0, got %r" % (op, depth))
    total = 2 * 3 ** d + 2
    if total > _THM_MAX_CIRCLES:
        raise ValueError("%s: depth %d would make %d circles, over the %d cap"
                         % (op, d, total, _THM_MAX_CIRCLES))
    mc = float(min_curvature)
    if not np.isfinite(mc) or mc < 0.0:
        raise ValueError("%s: min_curvature must be finite and >= 0, got %r"
                         % (op, min_curvature))

    z = _apollonian_seed_centres(k, op)
    circles = [(complex(z[i]), float(k[i]), 0) for i in range(4)]
    # ★四つ組の**最後**が「直前に生まれた円」。それを落とす反射は**親をもう一度**
    #   作るので、種の四つ組だけ 4 方向、以降は 3 方向に進む。ここを間違えると
    #   depth 3 で 56 個のはずが 88 個になった(実測。一意な円は 56 のままなので、
    #   絵は正しく見えるが同じ円を何度も描き、以降の段が指数的に太る)。
    frontier = [(tuple(range(4)), True)]
    for level in range(1, d + 1):
        nxt = []
        for quad, is_seed in frontier:
            for drop in range(4 if is_seed else 3):
                keep = [quad[t] for t in range(4) if t != drop]
                ka = np.array([circles[t][1] for t in keep])
                za = np.array([circles[t][0] for t in keep])
                kd = circles[quad[drop]][1]
                zd = circles[quad[drop]][0]
                knew = 2.0 * float(ka.sum()) - kd
                if knew == 0:
                    continue                       # 直線(曲率 0)は描かない
                znew = (2.0 * complex((ka * za).sum()) - kd * zd) / knew
                circles.append((znew, knew, level))
                nxt.append((tuple(keep) + (len(circles) - 1,), False))
        frontier = nxt

    rows = [(c.real, c.imag, 1.0 / kk, kk, lv) for c, kk, lv in circles
            if kk != 0 and (mc == 0.0 or abs(kk) <= 1.0 / mc or kk < 0)]
    a = np.asarray(rows, dtype=np.float64)
    return {"x": a[:, 0], "y": a[:, 1], "radius": np.abs(a[:, 2]),
            "curvature": a[:, 3], "depth": a[:, 4].astype(np.int64)}


def _apollonian_seed_centres(k, op):
    """曲率だけから、互いに接する 4 円の中心を決める(複素デカルト)。

    外円(k<0)を原点に置き、残り 3 つを接するように配置する。
    """
    idx = np.argsort(k)                    # 外円(負)が先頭に来る
    k0, k1, k2, k3 = (float(k[i]) for i in idx)
    r0, r1, r2 = abs(1.0 / k0), 1.0 / k1, 1.0 / k2
    z0 = 0.0 + 0.0j
    z1 = complex(r0 - r1, 0.0)             # 外円に内接
    d = r1 + r2                            # 円 1 と円 2 は外接
    e = r0 - r2                            # 円 2 も外円に内接
    # z2 は |z2 - z1| = d, |z2| = e を満たす
    cosang = (e * e + abs(z1) ** 2 - d * d) / (2.0 * e * abs(z1)) if abs(z1) > 0 else 0.0
    cosang = float(np.clip(cosang, -1.0, 1.0))
    ang = np.arccos(cosang)
    z2 = e * np.exp(1j * ang)
    # 4 つめは複素デカルトの式から
    ks = np.array([k0, k1, k2], dtype=np.complex128)
    zs = np.array([z0, z1, z2], dtype=np.complex128)
    root = np.sqrt(ks[0] * ks[1] * zs[0] * zs[1] + ks[1] * ks[2] * zs[1] * zs[2]
                   + ks[2] * ks[0] * zs[2] * zs[0])
    num = (ks * zs).sum()
    cands = [(num + 2.0 * root) / k3, (num - 2.0 * root) / k3]
    z3 = min(cands, key=lambda c: abs(abs(c - z1) - (1.0 / k1 + 1.0 / k3)))
    out = np.empty(4, dtype=np.complex128)
    out[idx[0]], out[idx[1]], out[idx[2]], out[idx[3]] = z0, z1, z2, z3
    return out


def ford_circles(max_denominator=12, lo=0, hi=1):
    """Ford circles for the Farey fractions — tangency *is* an integer identity.

    For a fraction ``p/q`` in lowest terms the Ford circle sits at
    ``(p/q, 1/(2q**2))`` with radius ``1/(2q**2)``. Two such circles are
    **tangent if and only if** ``|p*s - q*r| == 1`` — the Farey-neighbour
    condition — and otherwise strictly disjoint. They never overlap.

    ★**Why this earns its place**: the picture's correctness is an identity
    between integers, not a tolerance. ``|p*s - q*r|`` is computed in exact
    integer arithmetic and compared with the *geometric* tangency
    ``|c_i - c_j| == r_i + r_j`` measured from the coordinates; the two must
    agree on every pair. The number of fractions is the Farey length
    ``1 + sum(phi(q) for q in 1..n)``, another exact integer.

    Returns a ``table``: ``x``, ``y``, ``radius``, ``p``, ``q``.

    **Raises** ``ValueError``: ``max_denominator < 1``; ``lo >= hi``; the
    interval or denominator would exceed the cap.

    HALCON: no operator.
    """
    op = "ford_circles"
    n = int(max_denominator)
    if n < 1:
        raise ValueError("%s: max_denominator must be >= 1, got %r" % (op, max_denominator))
    a, b = int(lo), int(hi)
    if a >= b:
        raise ValueError("%s: need lo < hi, got %d and %d" % (op, a, b))
    from math import gcd
    ps, qs = [], []
    for q in range(1, n + 1):
        for p in range(a * q, b * q + 1):
            if gcd(abs(p), q) == 1 or q == 1:
                if gcd(abs(p), q) != 1 and not (q == 1):
                    continue
                ps.append(p)
                qs.append(q)
        if len(ps) > _THM_MAX_CIRCLES:
            raise ValueError("%s: max_denominator %d over the %d cap"
                             % (op, n, _THM_MAX_CIRCLES))
    p = np.asarray(ps, dtype=np.int64)
    q = np.asarray(qs, dtype=np.int64)
    order = np.lexsort((q, p * 1.0 / q))
    p, q = p[order], q[order]
    r = 1.0 / (2.0 * q.astype(np.float64) ** 2)
    return {"x": p.astype(np.float64) / q, "y": r, "radius": r, "p": p, "q": q}


def phyllotaxis_pattern(n_points=400, angle_deg=None, scale=1.0, power=0.5):
    """Vogel's spiral — the angle that packs best, and the spirals it makes.

    Point ``k`` sits at ``r = scale * k**power``, ``theta = k * angle_deg``. With
    the **golden angle** ``180*(3 - sqrt 5) = 137.50776...`` degrees (the default)
    this is the arrangement of sunflower florets, pine-cone scales and the leaves
    of most plants.

    ★**Why this earns its place — two independent theorems, each with a control
    group**:

      - *The golden angle packs best.* Sweep the divergence angle and the minimum
        nearest-neighbour distance is **maximised** at 137.50776 deg; a fraction
        of a degree either side is measurably worse. Nothing in the formula says
        this — it has to be measured.
      - *The visible spirals are consecutive Fibonacci numbers.* Take each point's
        nearest neighbours and look at the **difference of their indices**: the
        differences concentrate on 1, 2, 3, 5, 8, 13, 21, 34... At a non-golden
        angle they do not.

    Returns ``pairs`` ``(n, 2)`` of ``(x, y)``.

    **Raises** ``ValueError``: ``n_points < 1`` or over the cap; non-finite angle
    or scale; ``power`` outside ``(0, 1]``.

    HALCON: no operator.
    """
    op = "phyllotaxis_pattern"
    n = int(n_points)
    if n < 1:
        raise ValueError("%s: n_points must be >= 1, got %r" % (op, n_points))
    if n > _THM_MAX_POINTS:
        raise ValueError("%s: n_points %d over the %d cap" % (op, n, _THM_MAX_POINTS))
    ang = GOLDEN_ANGLE_DEG if angle_deg is None else float(angle_deg)
    if not np.isfinite(ang):
        raise ValueError("%s: angle_deg %r is not finite" % (op, angle_deg))
    sc = float(scale)
    if not np.isfinite(sc) or sc <= 0.0:
        raise ValueError("%s: scale must be finite and positive, got %r" % (op, scale))
    pw = float(power)
    if not np.isfinite(pw) or not (0.0 < pw <= 1.0):
        raise ValueError("%s: power must lie in (0, 1], got %r — at or below 0 the "
                         "spiral does not grow and above 1 the density falls off, "
                         "which is not what phyllotaxis means" % (op, power))
    k = np.arange(n, dtype=np.float64)
    r = sc * k ** pw
    th = np.deg2rad(ang) * k
    return np.stack([r * np.cos(th), r * np.sin(th)], axis=1)


def neighbour_index_gaps(points, k=6):
    """How far apart *in index* are a point's nearest neighbours — parastichy as a number.

    In a phyllotactic pattern the visible spirals (**parastichies**) are not drawn
    by anything; they are an illusion of which florets happen to sit next to each
    other. This op replaces the illusion with a count: for every point, take its
    *k* nearest neighbours **in space** and record the difference of their
    **ordering indices**. The histogram of those differences is returned, index
    ``g`` holding how many neighbour pairs were ``g`` apart.

    ★**Why this earns its place**: with the golden angle the peaks land on
    **Fibonacci numbers** (8, 13, 21, 34, 55 ...), and with any other angle they
    do not. That is a statement about the arrangement which can be checked
    **without looking at the picture** — which is the whole point, because the
    spirals look convincing at every angle.

    Parameters
    ----------
    points : (N, 2) array
        Ordered points — **the order is the data here**, not a convenience.
    k : int >= 1
        Neighbours per point (6 is the natural choice: a well-packed planar
        arrangement is locally hexagonal).

    Returns a ``signal``: ``counts[g]`` = number of neighbour pairs whose index
    difference is ``g`` (``counts[0]`` is always 0 — a point is not its own
    neighbour).

    **Raises** ``ValueError``: not an (N, 2) array; fewer than ``k + 1`` points;
    ``k`` below 1; non-finite coordinates.

    Limits: the first points of a spiral sit near the centre where the packing
    is degenerate, so the histogram has a low-index tail that carries no
    parastichy information. Compare *peaks*, not the raw tail.

    HALCON: no operator.
    """
    op = "neighbour_index_gaps"
    p = np.asarray(points, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 2:
        raise ValueError("%s: points must be (N, 2), got %s" % (op, (p.shape,)))
    if not np.all(np.isfinite(p)):
        raise ValueError("%s: points contain a non-finite value" % op)
    kk = int(k)
    if kk < 1:
        raise ValueError("%s: k must be >= 1, got %r" % (op, k))
    if p.shape[0] < kk + 1:
        raise ValueError("%s: need at least k + 1 = %d points, got %d"
                         % (op, kk + 1, p.shape[0]))
    from scipy.spatial import cKDTree
    _, idx = cKDTree(p).query(p, k=kk + 1)
    gaps = np.abs(idx[:, 1:] - np.arange(p.shape[0])[:, None]).ravel()
    return np.bincount(gaps).astype(np.int64)


def ifs_fractal(preset="sierpinski", maps=None, n_points=60000, seed=0, burn_in=32):
    """Chaos game on an iterated function system — the dimension is a closed form.

    Picks a map at random (by ``weights``, or by area if none are given), applies
    it, and plots the orbit. After a short burn-in the orbit lands on the
    attractor and stays there, so the picture is the attractor and not a path to
    it.

    ★**Why this earns its place — two numbers that must agree and were computed
    two different ways**:

      - *Moran's equation.* For similarities with ratios ``r_i`` satisfying the
        open set condition, the similarity dimension ``d`` is the unique root of
        ``sum(r_i**d) == 1`` — a closed form read off the **maps**, before
        anything is drawn. Sierpinski gives ``log 3 / log 2 = 1.5850``, the Koch
        curve ``log 4 / log 3 = 1.2619``, Cantor dust ``log 4 / log 3`` as well.
      - *Box counting.* This repository's existing ``fractal_dimension``
        operator measures the dimension from the **drawing**. The two must agree,
        and they are not the same computation: one is algebra on the maps, the
        other is a regression on a rasterised image.

      Hutchinson's theorem gives a third, structural check: the attractor is
      **invariant**, so applying every map to the point set maps it back into
      itself.

    ``maps`` overrides ``preset``: a sequence of ``(a, b, c, d, e, f)`` meaning
    ``x -> [[a, b], [c, d]] x + [e, f]``.

    Returns ``pairs`` ``(n, 2)``.

    **Raises** ``ValueError``: unknown preset; a map that is not 6 numbers; a map
    that is not a contraction (spectral norm >= 1 — the orbit would escape);
    ``n_points`` below 1 or over the cap; negative ``burn_in``.

    HALCON: no operator.
    """
    op = "ifs_fractal"
    if maps is None:
        if preset not in IFS_PRESETS:
            raise ValueError("%s: preset must be one of %r, got %r"
                             % (op, IFS_PRESETS, preset))
        rows = _IFS_MAP_TABLE[preset]
        w = _IFS_MAP_WEIGHTS.get(preset)
    else:
        rows = [tuple(float(v) for v in m) for m in maps]
        w = None
        for i, m in enumerate(rows):
            if len(m) != 6:
                raise ValueError("%s: map #%d must be 6 numbers (a b c d e f), got %d"
                                 % (op, i, len(m)))
    M = np.asarray([[m[0], m[1], m[2], m[3]] for m in rows], dtype=np.float64)
    T = np.asarray([[m[4], m[5]] for m in rows], dtype=np.float64)
    if not np.all(np.isfinite(M)) or not np.all(np.isfinite(T)):
        raise ValueError("%s: a map contains a non-finite value" % op)
    for i in range(M.shape[0]):
        A = M[i].reshape(2, 2)
        s = float(np.linalg.svd(A, compute_uv=False)[0])
        if s >= 1.0:
            raise ValueError("%s: map #%d has spectral norm %.4f >= 1 — it is not a "
                             "contraction, so the chaos game has no attractor to "
                             "land on and the orbit escapes." % (op, i, s))
    n = int(n_points)
    if n < 1:
        raise ValueError("%s: n_points must be >= 1, got %r" % (op, n_points))
    if n > _THM_MAX_POINTS:
        raise ValueError("%s: n_points %d over the %d cap" % (op, n, _THM_MAX_POINTS))
    bi = int(burn_in)
    if bi < 0:
        raise ValueError("%s: burn_in must be >= 0, got %r" % (op, burn_in))

    if w is None:
        det = np.abs(M[:, 0] * M[:, 3] - M[:, 1] * M[:, 2])
        w = det if det.sum() > 0 else np.ones(M.shape[0])
    p = np.asarray(w, dtype=np.float64)
    p = p / p.sum()

    rng = np.random.default_rng(int(seed))
    pick = rng.choice(M.shape[0], size=n + bi, p=p)
    z = np.zeros(2, dtype=np.float64)
    out = np.empty((n, 2), dtype=np.float64)
    for t in range(n + bi):
        a = M[pick[t]]
        z = np.array([a[0] * z[0] + a[1] * z[1] + T[pick[t], 0],
                      a[2] * z[0] + a[3] * z[1] + T[pick[t], 1]])
        if t >= bi:
            out[t - bi] = z
    return out


def ifs_similarity_dimension(preset="sierpinski", maps=None, tol=1e-13):
    """Moran's equation ``sum(r_i**d) = 1`` solved for ``d`` — from the maps alone.

    The similarity dimension of a self-similar set, computed **before** anything
    is drawn. Valid when the pieces overlap only on a set of measure zero (the
    open set condition); affine maps that are not similarities (the fern) have
    no single ratio, so this raises rather than returning a number that looks
    right (measured: the fern's four maps have singular-value ratios from 0.16
    to 0.85, so no ``r_i`` exists).
    """
    op = "ifs_similarity_dimension"
    if maps is None:
        if preset not in IFS_PRESETS:
            raise ValueError("%s: preset must be one of %r, got %r"
                             % (op, IFS_PRESETS, preset))
        rows = _IFS_MAP_TABLE[preset]
    else:
        rows = [tuple(float(v) for v in m) for m in maps]
    rs = []
    for i, m in enumerate(rows):
        A = np.array([[m[0], m[1]], [m[2], m[3]]], dtype=np.float64)
        s = np.linalg.svd(A, compute_uv=False)
        if abs(s[0] - s[1]) > 1e-9 * max(s[0], 1e-30):
            raise ValueError("%s: map #%d is not a similarity — its singular values "
                             "are %.6f and %.6f, so it has no single contraction "
                             "ratio and Moran's equation does not apply. Measure the "
                             "dimension from the drawing instead (fractal_dimension)."
                             % (op, i, s[0], s[1]))
        rs.append(float(s[0]))
    r = np.asarray(rs)
    lo, hi = 0.0, 8.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if (r ** mid).sum() > 1.0:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)


def space_filling_curve(kind="hilbert", order=4):
    """Hilbert / Moore / scan orders on a ``2**order`` square — a permutation, checked.

    Returns the visiting order as ``pairs`` ``(4**order, 2)`` of integer grid
    coordinates. Two scan orders are included **as control groups**, not as
    filler: ``row_major`` jumps a whole row at the end of each line and
    ``boustrophedon`` (serpentine) does not, so "consecutive points are
    adjacent" separates them, and the locality measurement separates all four.

    ★**Why this earns its place — the defining properties are integers**:

      - The result visits ``4**order`` cells, **each exactly once**: a
        permutation, verified by sorting, not by sampling.
      - For Hilbert, Moore and boustrophedon, **consecutive points are always at
        L1 distance exactly 1**. Row-major is not (it jumps at every line end),
        which is the control.
      - Moore's curve is **closed**: the last point is adjacent to the first.
        Hilbert's is not.
      - *Locality.* For a gap of ``k`` in index, the mean Euclidean distance
        grows like ``sqrt(k)`` for Hilbert and much faster for row-major. That is
        why Hilbert order is used for spatial indexes, and it is measurable here
        rather than asserted.

    **Raises** ``ValueError``: unknown ``kind``; ``order < 1``; the grid would
    exceed the cap; ``moore`` with ``order < 2`` (it is not defined below that).

    HALCON: no operator.
    """
    op = "space_filling_curve"
    if kind not in CURVE_KINDS:
        raise ValueError("%s: kind must be one of %r, got %r" % (op, CURVE_KINDS, kind))
    o = int(order)
    if o < 1:
        raise ValueError("%s: order must be >= 1, got %r" % (op, order))
    n = 1 << o
    if n * n > _THM_MAX_POINTS:
        raise ValueError("%s: order %d would visit %d cells, over the %d cap"
                         % (op, o, n * n, _THM_MAX_POINTS))
    if kind == "moore" and o < 2:
        raise ValueError("%s: the Moore curve needs order >= 2 (it is four Hilbert "
                         "quadrants joined into a loop), got %d" % (op, o))

    if kind == "row_major":
        yy, xx = np.divmod(np.arange(n * n), n)
        return np.stack([xx, yy], axis=1).astype(np.int64)
    if kind == "boustrophedon":
        yy, xx = np.divmod(np.arange(n * n), n)
        xx = np.where(yy % 2 == 1, n - 1 - xx, xx)
        return np.stack([xx, yy], axis=1).astype(np.int64)
    if kind == "hilbert":
        return _sfc_hilbert(n)
    half = n >> 1
    # ★ムーア曲線 = ヒルベルト曲線 4 本を輪に閉じたもの。四分割の**向きと進む方向**は
    #   総当たり(8 対称 x 反転、4096 通り)で「継ぎ目 3 か所と折り返しが全部距離 1」を
    #   満たす 32 解を出し、その 1 つを固定した。手で置くと隣接条件が静かに壊れる
    #   (最初の実装は隣接 False・閉 False のまま、絵としては正しく見えていた)。
    q = _sfc_hilbert(half)
    ts = (2, 0, 0, 2)                       # 0=そのまま 1=x反転 2=y反転 4=転置 の組
    rev = (1, 0, 0, 1)
    off = ((0, 0), (0, half), (half, half), (half, 0))
    parts = []
    for qi in range(4):
        x, y = q[:, 0].copy(), q[:, 1].copy()
        t = ts[qi]
        if t & 4:
            x, y = y, x
        if t & 1:
            x = half - 1 - x
        if t & 2:
            y = half - 1 - y
        a = np.stack([x, y], axis=1)
        if rev[qi]:
            a = a[::-1]
        parts.append(a + np.asarray(off[qi]))
    return np.concatenate(parts, axis=0).astype(np.int64)


def _sfc_hilbert(n):
    d = np.arange(n * n, dtype=np.int64)
    x = np.zeros_like(d)
    y = np.zeros_like(d)
    t = d.copy()
    s = 1
    while s < n:
        rx = 1 & (t // 2)
        ry = 1 & (t ^ rx)
        flip = ry == 0
        xf = np.where(flip & (rx == 1), s - 1 - x, x)
        yf = np.where(flip & (rx == 1), s - 1 - y, y)
        x2 = np.where(flip, yf, xf)
        y2 = np.where(flip, xf, yf)
        x = x2 + s * rx
        y = y2 + s * ry
        t = t // 4
        s *= 2
    return np.stack([x, y], axis=1)


def curve_locality(points, gaps=(1, 2, 4, 8, 16, 32)):
    """Points ``k`` apart along the curve — how far apart are they on the plane?

    The reason a space-filling curve is used for storage layout, texture tiling
    or rendering order is **locality**: neighbours in the ordering should stay
    neighbours in space. This op measures that directly — for each gap ``k`` it
    returns the mean Euclidean distance between points ``i`` and ``i + k``.

    ★**Why this earns its place**: the claim "Hilbert has better locality than
    scanning row by row" is usually asserted and never measured. Here it is a
    table you can read: a Hilbert curve grows roughly as ``sqrt(k)`` (measured
    1.00 / 1.53 / 2.12 / 3.17 / 4.29 / 6.38 at k = 1 .. 32), while a boustrophedon
    scan grows nearly **linearly** (1.00 / 1.96 / 3.79 / 7.07 / 12.12 / 16.07) —
    an honest, reproducible gap rather than a slogan.

    Parameters
    ----------
    points : (N, 2) array
        The curve's points **in visiting order**.
    gaps : ints
        Index gaps to report. Gaps at or beyond ``N`` are dropped (not an error;
        a short curve simply has nothing to say about a long gap).

    Returns a ``table``: ``gap`` (int), ``mean_distance``, and ``ratio`` =
    ``mean_distance / mean_distance[gap == 1]`` so curves of different scales can
    be compared directly.

    **Raises** ``ValueError``: not an (N, 2) array; fewer than 2 points;
    non-finite coordinates; every requested gap out of range.

    HALCON: no operator.
    """
    op = "curve_locality"
    p = np.asarray(points, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 2:
        raise ValueError("%s: points must be (N, 2), got %s" % (op, (p.shape,)))
    if p.shape[0] < 2:
        raise ValueError("%s: need at least 2 points, got %d" % (op, p.shape[0]))
    if not np.all(np.isfinite(p)):
        raise ValueError("%s: points contain a non-finite value" % op)
    ks, means = [], []
    for k in gaps:
        k = int(k)
        if k < 1 or k >= p.shape[0]:
            continue
        d = np.hypot(p[k:, 0] - p[:-k, 0], p[k:, 1] - p[:-k, 1])
        ks.append(k)
        means.append(float(d.mean()))
    if not ks:
        raise ValueError("%s: every requested gap is out of range for %d points "
                         "(gaps=%r)" % (op, p.shape[0], tuple(gaps)))
    m = np.asarray(means, dtype=np.float64)
    base = m[0] if ks[0] == 1 else m.min()
    return {"gap": np.asarray(ks, dtype=np.int64), "mean_distance": m,
            "ratio": m / base if base > 0 else np.full(m.shape, np.nan)}


# ------------------------------------------------------------------------- #
# 波動 —— 膜の固有モード・干渉・回折(2026-09-23)
#
# ★クラドニ図形は「板」ではなく**膜**の解である。よく見る cos*cos - cos*cos は
#   ヘルムホルツ方程式 + ノイマン境界の膜のモードで、実際のクラドニ板は
#   **重調和方程式**に従う別物。砂が節線に集まる絵は同じでも周波数比は合わない。
#   ここでは膜と明記し、膜の真値(閉形式の固有値・ベッセル零点)だけで採点する。
#   干渉と回折の真値は既存 op(grating_wavelengths / fraunhofer_pattern)。
# ------------------------------------------------------------------------- #

_WAVE_MAX_GRID = 4_000_000

def _wave_bessel_j_zeros(order, count):
    """J_order' (微分) の零点を、区間の符号変化 + 二分法で求める。

    scipy が在れば ``jnp_zeros`` を使うが、無くても動くよう自前で持つ
    (この repo の既定は stdlib + numpy で動くこと)。
    """
    try:
        from scipy.special import jnp_zeros
        return np.asarray(jnp_zeros(int(order), int(count)), dtype=np.float64)
    except Exception:                                       # noqa: BLE001
        pass
    from numpy.polynomial import legendre  # noqa: F401  (numpy があることの保証)
    try:
        from scipy.special import jv as _jv
    except Exception:                                       # noqa: BLE001
        _jv = None
    if _jv is None:
        raise ValueError("wave_mode_frequencies: circular modes need scipy.special "
                         "(Bessel functions); the rectangular kind needs nothing")
    def dj(x):
        return 0.5 * (_jv(order - 1, x) - _jv(order + 1, x))
    xs = np.linspace(1e-6, 4.0 + 4.0 * count + 2.0 * order, 20000)
    v = dj(xs)
    out = []
    for i in range(xs.size - 1):
        if v[i] == 0.0:
            out.append(xs[i])
        elif v[i] * v[i + 1] < 0:
            lo, hi = xs[i], xs[i + 1]
            for _ in range(80):
                mid = 0.5 * (lo + hi)
                if dj(lo) * dj(mid) <= 0:
                    hi = mid
                else:
                    lo = mid
            out.append(0.5 * (lo + hi))
        if len(out) >= count:
            break
    return np.asarray(out[:count], dtype=np.float64)

def wave_membrane_mode(kind="rectangular", m=2, n=3, shape=(256, 256), aspect=1.0,
                       free_edge=True):
    """One eigenmode of a vibrating **membrane** — the shape the sand draws.

    ★**This is a membrane, not a plate.** The familiar Chladni pattern
    ``cos(m pi x) cos(n pi y) - cos(n pi x) cos(m pi y)`` solves the Helmholtz
    equation with free (Neumann) edges; a real Chladni *plate* obeys the
    **biharmonic** equation and has a different frequency ladder. The pictures
    look alike, the frequencies do not — so this op says membrane and is checked
    against membrane truth only.

    ``kind="rectangular"`` returns the (possibly combined) cosine mode over a
    rectangle of the given *aspect*; ``kind="circular"`` returns
    ``J_m(k r) cos(m theta)`` with ``k`` from the Bessel zero, zero outside the disc.

    ★**Why this earns its place**: the nodal lines of a rectangular mode are known
    **by count** — a simple ``(m, n)`` mode has ``m-1`` interior vertical and
    ``n-1`` horizontal nodal lines — and the circular mode's nodal circles are at
    the ratios of successive Bessel zeros. The drawing can therefore be graded.

    Returns a ``matrix`` (signed displacement, peak scaled to 1). Use
    :func:`wave_nodal_lines` for the zero set.

    **Raises** ``ValueError``: unknown kind; ``m``/``n`` below the valid range;
    a grid over the cap; non-positive aspect; ``free_edge=False`` combined with
    ``m == n`` for the combined mode (the difference vanishes identically).

    HALCON: no operator.
    """
    op = "wave_membrane_mode"
    if kind not in ("rectangular", "circular"):
        raise ValueError("%s: kind must be 'rectangular' or 'circular', got %r"
                         % (op, kind))
    h, w = int(shape[0]), int(shape[1])
    if h < 4 or w < 4 or h * w > _WAVE_MAX_GRID:
        raise ValueError("%s: shape %r outside 4x4 .. %d cells" % (op, shape, _WAVE_MAX_GRID))
    a = float(aspect)
    if not np.isfinite(a) or a <= 0:
        raise ValueError("%s: aspect must be finite and > 0, got %r" % (op, aspect))
    mm, nn = int(m), int(n)

    y = np.linspace(0.0, 1.0, h)[:, None]
    x = np.linspace(0.0, 1.0, w)[None, :]
    if kind == "rectangular":
        if mm < 0 or nn < 0:
            raise ValueError("%s: m and n must be >= 0 for a rectangle" % op)
        if free_edge:
            if mm == nn:
                raise ValueError("%s: the combined free-edge mode vanishes identically "
                                 "for m == n (%d); pass free_edge=False for the plain "
                                 "cosine mode" % (op, mm))
            u = (np.cos(mm * np.pi * x) * np.cos(nn * np.pi * y / a)
                 - np.cos(nn * np.pi * x) * np.cos(mm * np.pi * y / a))
        else:
            u = np.sin(mm * np.pi * x) * np.sin(nn * np.pi * y / a)
    else:
        if mm < 0 or nn < 1:
            raise ValueError("%s: circular needs m >= 0 (angular) and n >= 1 (radial)"
                             % op)
        k = float(_wave_bessel_j_zeros(mm, nn)[-1])
        cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
        yy, xx = np.mgrid[0:h, 0:w]
        r = np.hypot((yy - cy) / cy, (xx - cx) / cx)
        th = np.arctan2(yy - cy, xx - cx)
        try:
            from scipy.special import jv
        except Exception:                                   # noqa: BLE001
            raise ValueError("%s: circular modes need scipy.special (Bessel functions)"
                             % op)
        u = jv(mm, k * np.clip(r, 0, 1)) * np.cos(mm * th)
        u = np.where(r <= 1.0, u, 0.0)
    peak = float(np.max(np.abs(u)))
    return u / peak if peak > 0 else u

def wave_mode_frequencies(kind="rectangular", count=10, aspect=1.0):
    """The eigenvalue ladder of a membrane — a closed form you can check against.

    ``kind="rectangular"``: the Dirichlet eigenvalues of a rectangle are
    ``pi**2 * (m**2 + n**2 / aspect**2)`` for ``m, n >= 1`` — **not** ``m n pi``,
    which is the usual slip. ``kind="circular"``: the free-edge (Neumann) circular
    membrane's eigenvalues are the squares of the zeros of ``J'_m``.

    ★**Why this earns its place**: this ladder is what separates a membrane from a
    plate, and it is exactly computable. The square drum's ratios start
    2, 5, 5, 8, 10, 10, 13 (in units of ``pi**2``) — the repeated 5 and 10 are the
    famous degeneracies that make the square drum's modes ambiguous, and a wrong
    implementation loses them.

    Returns a ``signal``: the eigenvalues, ascending.

    **Raises** ``ValueError``: unknown kind; non-positive count or aspect; a
    circular request without scipy.
    """
    op = "wave_mode_frequencies"
    if kind not in ("rectangular", "circular"):
        raise ValueError("%s: kind must be 'rectangular' or 'circular', got %r"
                         % (op, kind))
    c = int(count)
    if c < 1:
        raise ValueError("%s: count must be >= 1, got %r" % (op, count))
    a = float(aspect)
    if not np.isfinite(a) or a <= 0:
        raise ValueError("%s: aspect must be finite and > 0, got %r" % (op, aspect))
    if kind == "rectangular":
        k = int(np.ceil(np.sqrt(c))) + 4
        mm, nn = np.meshgrid(np.arange(1, k + 1), np.arange(1, k + 1))
        lam = np.pi ** 2 * (mm ** 2 + nn ** 2 / a ** 2)
        return np.sort(lam.ravel())[:c]
    out = []
    order = 0
    while len(out) < c + 8:
        out.extend(_wave_bessel_j_zeros(order, c) ** 2)
        order += 1
        if order > c + 4:
            break
    return np.sort(np.asarray(out, dtype=np.float64))[:c]

def wave_nodal_lines(field, tol=0.0):
    """Where a signed field changes sign — the nodal set, as a mask.

    A pixel is marked when it differs in sign from its right or lower neighbour
    (or is within *tol* of zero). That is the discrete version of "the sand
    collects where the plate does not move".

    ★**Why this earns its place**: the count is predictable. A plain ``(m, n)``
    rectangular mode has ``m-1`` interior nodal lines in one direction and ``n-1``
    in the other, so the mask can be graded against integers rather than by eye.

    Returns a ``mask``.

    **Raises** ``ValueError``: not a 2-D array; non-finite values; negative *tol*.
    """
    op = "wave_nodal_lines"
    u = np.asarray(field, dtype=np.float64)
    if u.ndim != 2 or min(u.shape) < 2:
        raise ValueError("%s: field must be 2-D with at least 2x2, got %s"
                         % (op, (u.shape,)))
    if not np.all(np.isfinite(u)):
        raise ValueError("%s: field contains a non-finite value" % op)
    t = float(tol)
    if not np.isfinite(t) or t < 0:
        raise ValueError("%s: tol must be finite and >= 0, got %r" % (op, tol))
    s = np.sign(u)
    out = np.zeros(u.shape, dtype=bool)
    out[:, :-1] |= (s[:, :-1] * s[:, 1:]) < 0
    out[:-1, :] |= (s[:-1, :] * s[1:, :]) < 0
    if t > 0:
        out |= np.abs(u) <= t
    return out

def wave_two_slit(wavelength_nm=550.0, slit_sep_um=20.0, distance_mm=200.0,
                  shape=(256, 512), pixel_um=5.0, slit_width_um=2.0):
    """Two-slit interference on a screen — built from the physics, not the fringe formula.

    Each slit is treated as a line source of the given width; the screen intensity
    is ``|sum over slit of exp(i k R) / sqrt(R)|**2`` with ``R`` the true distance
    from each source point. **The textbook spacing ``lambda D / d`` is nowhere in
    this computation** — which is the point: it is then available as an
    independent prediction to check the picture against.

    ★**Why this earns its place**: :func:`wave_fringe_period` measures the period
    of the produced image, and it must land on ``lambda D / d`` (in pixels,
    ``lambda D / (d * pixel)``). Two ways to the same number, only one of which
    was used to draw.

    Returns an ``image2d`` normalised to a peak of 1.

    **Raises** ``ValueError``: non-positive wavelength, separation, distance,
    pixel or width; a grid over the cap; a geometry so coarse that fewer than
    three fringes fit on the screen (reported, not silently aliased).

    Limits: scalar, monochromatic, far-from-paraxial geometries are not modelled;
    the slits are lines, so there is no vertical structure.
    """
    op = "wave_two_slit"
    lam = float(wavelength_nm) * 1e-3                      # -> um
    d = float(slit_sep_um)
    D = float(distance_mm) * 1e3                           # -> um
    px = float(pixel_um)
    sw = float(slit_width_um)
    for nm, v in (("wavelength_nm", lam), ("slit_sep_um", d), ("distance_mm", D),
                  ("pixel_um", px), ("slit_width_um", sw)):
        if not np.isfinite(v) or v <= 0:
            raise ValueError("%s: %s must be finite and > 0" % (op, nm))
    h, w = int(shape[0]), int(shape[1])
    if h < 4 or w < 8 or h * w > _WAVE_MAX_GRID:
        raise ValueError("%s: shape %r outside 4x8 .. %d cells" % (op, shape, _WAVE_MAX_GRID))
    period_px = lam * D / (d * px)
    if period_px * 3.0 > w:
        raise ValueError("%s: the predicted fringe period is %.1f px and the screen is "
                         "%d px — fewer than 3 fringes fit (move the screen closer, "
                         "widen the separation, or use a bigger shape)"
                         % (op, period_px, w))
    if period_px < 4.0:
        raise ValueError("%s: the predicted fringe period is %.2f px — below the 4 px "
                         "needed to sample a fringe (this would alias)" % (op, period_px))
    xs = (np.arange(w) - (w - 1) / 2.0) * px
    k = 2.0 * np.pi / lam
    nsrc = max(3, int(np.ceil(sw / (lam / 4.0))))
    off = np.linspace(-sw / 2.0, sw / 2.0, nsrc)
    amp = np.zeros(w, dtype=np.complex128)
    for centre in (-d / 2.0, +d / 2.0):
        for o in off:
            R = np.hypot(xs - (centre + o), D)
            amp += np.exp(1j * k * R) / np.sqrt(R)
    line = np.abs(amp) ** 2
    line = line / line.max()
    return np.repeat(line[None, :], h, axis=0)

def wave_fringe_period(image, axis=1):
    """The period of a striped image, measured back out of it (pixels).

    Takes the mean profile along *axis*, removes the mean, and reads the dominant
    frequency from the FFT with a **parabolic interpolation** on the log spectrum,
    so the answer is not quantised to the FFT bin.

    ★**Why this earns its place**: it closes the loop on :func:`wave_two_slit` and
    on any halftone or grating image — the period predicted by the closed form and
    the period measured from the pixels are two different computations.

    Returns a ``measurement``: the period in pixels.

    **Raises** ``ValueError``: not a 2-D array; fewer than 8 samples along *axis*;
    non-finite values; a profile with no variation (a flat image has no period).
    """
    op = "wave_fringe_period"
    im = np.asarray(image, dtype=np.float64)
    if im.ndim != 2:
        raise ValueError("%s: image must be 2-D, got %s" % (op, (im.shape,)))
    if not np.all(np.isfinite(im)):
        raise ValueError("%s: image contains a non-finite value" % op)
    a = int(axis)
    if a not in (0, 1):
        raise ValueError("%s: axis must be 0 or 1, got %r" % (op, axis))
    prof = im.mean(axis=0 if a == 1 else 1)
    if prof.size < 8:
        raise ValueError("%s: need at least 8 samples along the axis, got %d"
                         % (op, prof.size))
    prof = prof - prof.mean()
    if float(np.ptp(prof)) <= 0:
        raise ValueError("%s: the profile is flat — there is no period to measure" % op)
    spec = np.abs(np.fft.rfft(prof * np.hanning(prof.size))) ** 2
    spec[0] = 0.0
    i = int(np.argmax(spec))
    if i <= 0 or i >= spec.size - 1:
        return float(prof.size) / max(i, 1)
    y0, y1, y2 = np.log(spec[i - 1:i + 2] + 1e-300)
    delta = 0.5 * (y0 - y2) / (y0 - 2.0 * y1 + y2)
    return float(prof.size) / (i + float(delta))

def wave_grating_orders(pitch_um=1.6, wavelength_nm=550.0, sin_in=0.0,
                        orders=(-2, -1, 1, 2)):
    """Where a grating sends each order: ``d (sin_out - sin_in) = m lambda`` solved for the angle.

    The companion to the existing ``grating_wavelengths`` (which solves the same
    identity for *lambda*): given the pitch and the wavelength, this returns the
    outgoing direction of each order, and marks the orders that are
    **evanescent** — ``|sin_out| > 1`` means that order does not propagate, which
    is why a CD shows fewer colours at grazing incidence.

    ★**Why this earns its place**: the two ops invert one another, so a round trip
    must return the wavelength it started from; and the angles can be compared
    against the peak positions of a *simulated* far field (the existing
    ``fraunhofer_pattern`` of a real grating aperture), which knows nothing about
    the grating equation.

    Returns a ``table``: ``order``, ``sin_out``, ``angle_deg`` (NaN when
    evanescent), ``propagates``.

    **Raises** ``ValueError``: non-positive pitch or wavelength; ``|sin_in| > 1``;
    order 0 alone with no others (it is always the specular direction — allowed,
    but a caller asking only for it probably meant something else); non-finite input.
    """
    op = "wave_grating_orders"
    d = float(pitch_um)
    lam = float(wavelength_nm) * 1e-3
    si = float(sin_in)
    if not np.isfinite(d) or d <= 0:
        raise ValueError("%s: pitch_um must be finite and > 0, got %r" % (op, pitch_um))
    if not np.isfinite(lam) or lam <= 0:
        raise ValueError("%s: wavelength_nm must be finite and > 0" % op)
    if not np.isfinite(si) or abs(si) > 1.0:
        raise ValueError("%s: sin_in must lie in [-1, 1], got %r" % (op, sin_in))
    m = np.asarray(orders, dtype=np.int64).ravel()
    if m.size == 0:
        raise ValueError("%s: orders is empty" % op)
    so = si + m * lam / d
    prop = np.abs(so) <= 1.0
    ang = np.where(prop, np.degrees(np.arcsin(np.clip(so, -1.0, 1.0))), np.nan)
    return {"order": m, "sin_out": so, "angle_deg": ang, "propagates": prop}


# ------------------------------------------------------------------------- #
# 力学系 —— 積む・断面・指数・分岐(2026-09-23)
#
# ★真値は**公表値か閉形式だけ**: 線形系は expm(At)x0 が厳密解で刻み半分に
#   すると誤差が 1/16(4 次)、Lorenz のリアプノフ指数の**和**はトレース恒等式
#   により厳密に -(sigma+1+beta)、ロジスティック写像の周期倍分岐は 3 と 1+sqrt6、
#   相関次元は円 1・カントール log2/log3。絵では何も確かめられない。
# ★関数(callable)を引数に取らない —— 型付き台帳は入力を sort で登録し、
#   連鎖ファザーがデータから引数を組むので callable は載らない。系は族名か係数配列。
# ------------------------------------------------------------------------- #

_DYN_MAX_STEPS = 4_000_000

_DYN_MAX_GRID = 4_000_000

DYNSYS_SYSTEMS = {
    # Lorenz (1963): sigma, beta, rho。発散 div f = -(sigma + 1 + beta) は**定数**。
    "lorenz": (10.0, 8.0 / 3.0, 28.0),
    # Rossler (1976): a, b, c。div f = a - c + x の**x に依る**(定数ではない)。
    "rossler": (0.2, 0.2, 5.7),
    # 調和振動子: omega。エネルギーが保存するので積分器の漂流が見える。
    "harmonic": (1.0,),
    # 線形系 x' = A x。params は A を行優先で並べたもの(n*n 個)。厳密解が expm(At)x0。
    "linear": (0.0, 1.0, -1.0, 0.0),
}

DYNSYS_MAPS = ("logistic", "sine", "tent")

def _dyn_system_dim(system, params):
    if system == "linear":
        n = int(round(np.sqrt(params.size)))
        if n * n != params.size:
            raise ValueError("ode: linear needs a square matrix, got %d numbers"
                             % params.size)
        return n
    return {"lorenz": 3, "rossler": 3, "harmonic": 2}[system]

def _dyn_derivative(system, params, x):
    """x は (..., n)。返りも同じ形。**ここだけが系の定義**(他の op は全部これを呼ぶ)。"""
    if system == "lorenz":
        s, b, r = params
        dx = s * (x[..., 1] - x[..., 0])
        dy = x[..., 0] * (r - x[..., 2]) - x[..., 1]
        dz = x[..., 0] * x[..., 1] - b * x[..., 2]
        return np.stack([dx, dy, dz], axis=-1)
    if system == "rossler":
        a, b, c = params
        dx = -x[..., 1] - x[..., 2]
        dy = x[..., 0] + a * x[..., 1]
        dz = b + x[..., 2] * (x[..., 0] - c)
        return np.stack([dx, dy, dz], axis=-1)
    if system == "harmonic":
        w = params[0]
        return np.stack([x[..., 1], -(w ** 2) * x[..., 0]], axis=-1)
    if system == "linear":
        n = _dyn_system_dim(system, params)
        A = params.reshape(n, n)
        return x @ A.T
    raise ValueError("ode: unknown system %r — one of %s"
                     % (system, tuple(DYNSYS_SYSTEMS)))

def _dyn_jacobian(system, params, x):
    """接方程式に要るヤコビ行列 (n, n)。**解析形**(差分でなく)。"""
    if system == "lorenz":
        s, b, r = params
        return np.array([[-s, s, 0.0],
                         [r - x[2], -1.0, -x[0]],
                         [x[1], x[0], -b]])
    if system == "rossler":
        a, b, c = params
        return np.array([[0.0, -1.0, -1.0],
                         [1.0, a, 0.0],
                         [x[2], 0.0, x[0] - c]])
    if system == "harmonic":
        w = params[0]
        return np.array([[0.0, 1.0], [-(w ** 2), 0.0]])
    if system == "linear":
        n = _dyn_system_dim(system, params)
        return params.reshape(n, n)
    raise ValueError("ode: unknown system %r" % (system,))

def _dyn_prepare(system, params):
    if system not in DYNSYS_SYSTEMS:
        raise ValueError("ode: unknown system %r — one of %s"
                         % (system, tuple(DYNSYS_SYSTEMS)))
    p = (np.asarray(DYNSYS_SYSTEMS[system], dtype=np.float64) if params is None
         else np.asarray(params, dtype=np.float64).ravel())
    if not np.all(np.isfinite(p)):
        raise ValueError("ode: params contain a non-finite value")
    if system != "linear" and p.size != len(DYNSYS_SYSTEMS[system]):
        raise ValueError("ode: %s takes %d parameters, got %d"
                         % (system, len(DYNSYS_SYSTEMS[system]), p.size))
    return p

def ode_flow_states(system="lorenz", params=None, x0=None, t_end=40.0, dt=0.005,
                    method="rk4"):
    """Integrate a named vector field — the trajectory, with the order you paid for.

    Explicit Runge-Kutta on one of the named systems (``lorenz``, ``rossler``,
    ``harmonic``, ``linear``). ``method="rk4"`` is the classical 4th-order step;
    ``method="euler"`` is there as a **control group** — the same picture comes out
    of both, and only the error tells them apart.

    ★**Why the field is a name, not a function**: the typed ledger registers inputs
    by sort and the chain fuzzer builds arguments from data, so a callable can
    never be reached from there. A name (or, for ``linear``, the matrix itself in
    ``params``) keeps every op in this family reachable from the ledger.

    ★**Why this earns its place**: for ``system="linear"`` the exact solution is
    ``expm(A t) x0``, so the error is known in closed form — and halving ``dt``
    divides it by **16**, which is what "4th order" means. A drawing of an
    attractor cannot be checked; this can.

    Parameters
    ----------
    system : str
        One of ``DYNSYS_SYSTEMS``.
    params : floats or None
        System parameters (defaults in ``DYNSYS_SYSTEMS``). For ``linear`` this is
        the matrix ``A`` in row-major order (``n*n`` numbers).
    x0 : floats or None
        Initial state (default: a point on the attractor / unit first coordinate).
    t_end, dt : float
        Integration window and step. ``t_end / dt`` must stay under 4,000,000.
    method : "rk4" | "euler"

    Returns a ``states`` table: ``t`` (S,) and ``x`` (S, n).

    **Raises** ``ValueError``: unknown system or method; wrong parameter count;
    non-finite input; ``dt`` not positive; a step count over the cap; a trajectory
    that left float range (the field diverged — reported, never silently clipped).

    HALCON: no operator.
    """
    op = "ode_flow_states"
    p = _dyn_prepare(system, params)
    n = _dyn_system_dim(system, p)
    if method not in ("rk4", "euler"):
        raise ValueError("%s: method must be 'rk4' or 'euler', got %r" % (op, method))
    h = float(dt)
    if not np.isfinite(h) or h <= 0:
        raise ValueError("%s: dt must be finite and > 0, got %r" % (op, dt))
    T = float(t_end)
    if not np.isfinite(T) or T <= 0:
        raise ValueError("%s: t_end must be finite and > 0, got %r" % (op, t_end))
    steps = int(round(T / h))
    if steps < 1 or steps > _DYN_MAX_STEPS:
        raise ValueError("%s: t_end/dt = %d steps, outside 1..%d"
                         % (op, steps, _DYN_MAX_STEPS))
    if x0 is None:
        x = np.zeros(n, dtype=np.float64)
        x[0] = 1.0
        if system in ("lorenz", "rossler"):
            x = np.array([1.0, 1.0, 1.0][:n], dtype=np.float64)
    else:
        x = np.asarray(x0, dtype=np.float64).ravel()
        if x.size != n:
            raise ValueError("%s: x0 must have %d components, got %d"
                             % (op, n, x.size))
    if not np.all(np.isfinite(x)):
        raise ValueError("%s: x0 contains a non-finite value" % op)

    out = np.empty((steps + 1, n), dtype=np.float64)
    out[0] = x
    for i in range(steps):
        if method == "euler":
            x = x + h * _dyn_derivative(system, p, x)
        else:
            k1 = _dyn_derivative(system, p, x)
            k2 = _dyn_derivative(system, p, x + 0.5 * h * k1)
            k3 = _dyn_derivative(system, p, x + 0.5 * h * k2)
            k4 = _dyn_derivative(system, p, x + h * k3)
            x = x + (h / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        if not np.all(np.isfinite(x)):
            raise ValueError("%s: the trajectory left float range at step %d "
                             "(the field diverged for these parameters/step)"
                             % (op, i + 1))
        out[i + 1] = x
    # ★`table` は**列名 -> 1-D 配列**。状態を (S, n) のまま 1 列に入れると型の嘘に
    #   なるので、成分ごとの列に開く(x0, x1, ... と時刻 t)。
    res = {"t": np.arange(steps + 1, dtype=np.float64) * h}
    for k in range(n):
        res["x%d" % k] = out[:, k]
    return res

def ode_vector_field_grid(system="rossler", params=None, bounds=(-10.0, 10.0, -10.0, 10.0),
                          shape=(64, 64), plane="xy", offset=0.0):
    """Sample a named field on a grid — a ``flow2d`` the existing viewers take.

    Returns ``(2, H, W)`` with components ``(dy, dx)`` — the library's
    ``flow2d`` layout — so the **existing flow family** (quiver, streamlines,
    colour wheel, ``flow_magnitude``) renders it with no new drawing code. For a
    3-D system, *plane* picks the slice (``xy`` / ``xz`` / ``yz``) and *offset*
    fixes the third coordinate.

    ★**Why this earns its place**: it is the bridge that keeps this family from
    growing its own renderer. The vectors are the same ``_dyn_derivative`` the
    integrator uses, so what you see is what gets integrated.

    ★The layout is **channel-first**, not the ``(H, W, 2)`` that reads more
    naturally here: ``flow2d`` is an existing type with an existing predicate and
    existing consumers, and a row that declares ``flow2d`` while returning the
    transpose is a type lie the fuzzer catches (it did —— 2026-09-23). Row 0 is
    the **top** (the image convention), so the vertical component is negated to
    match what the viewer draws.

    **Raises** ``ValueError``: unknown system or plane; a grid over the cap;
    non-finite bounds; a degenerate window.
    """
    op = "ode_vector_field_grid"
    p = _dyn_prepare(system, params)
    n = _dyn_system_dim(system, p)
    if plane not in ("xy", "xz", "yz"):
        raise ValueError("%s: plane must be xy / xz / yz, got %r" % (op, plane))
    b = np.asarray(bounds, dtype=np.float64).ravel()
    if b.size != 4 or not np.all(np.isfinite(b)):
        raise ValueError("%s: bounds must be 4 finite numbers (x0, x1, y0, y1)" % op)
    if b[1] <= b[0] or b[3] <= b[2]:
        raise ValueError("%s: bounds are degenerate: %s" % (op, tuple(b)))
    h, w = (int(shape[0]), int(shape[1]))
    if h < 2 or w < 2 or h * w > _DYN_MAX_GRID:
        raise ValueError("%s: shape %r outside 2x2 .. %d cells" % (op, shape, _DYN_MAX_GRID))
    gx = np.linspace(b[0], b[1], w)
    gy = np.linspace(b[3], b[2], h)                # 行 0 が上
    X, Y = np.meshgrid(gx, gy)
    pts = np.zeros(X.shape + (n,), dtype=np.float64)
    i0, i1 = {"xy": (0, 1), "xz": (0, 2), "yz": (1, 2)}[plane]
    if max(i0, i1) >= n:
        raise ValueError("%s: plane %r needs %d dimensions, the system has %d"
                         % (op, plane, max(i0, i1) + 1, n))
    pts[..., i0] = X
    pts[..., i1] = Y
    for k in range(n):
        if k not in (i0, i1):
            pts[..., k] = float(offset)
    d = _dyn_derivative(system, p, pts)
    # (2, H, W) = (dy, dx)。dy は上向きを負に(行 0 が上なので)。
    return np.stack([-d[..., i1], d[..., i0]], axis=0)

def dynsys_poincare_section(states, axis=2, value=None, direction=1):
    """Where a trajectory crosses a plane — with the crossing point interpolated.

    Takes the ``x`` block of :func:`ode_flow_states` and returns the points where
    coordinate *axis* crosses *value* in the given *direction* (+1 upward, -1
    downward, 0 either). The crossing is found by **linear interpolation between
    the two straddling samples**, not by taking the nearer sample — otherwise the
    section is quantised by the step size and a periodic orbit looks like a cloud.

    ★**Why this earns its place**: a periodic orbit must give **one** point (to
    within the interpolation error), a period-2 orbit two, and a chaotic one a
    fractal set. That is a check with a number in it, unlike "the picture looks
    like a strange attractor".

    Returns a ``pairs`` array of the remaining coordinates at each crossing.

    **Raises** ``ValueError``: states not (S, n) with S >= 2; axis out of range;
    direction not in (-1, 0, 1); non-finite input; no crossing found (reported,
    not returned as an empty array that a caller may read as "no orbit").
    """
    op = "dynsys_poincare_section"
    if isinstance(states, dict):                            # ode_flow_states の table
        cols = sorted(k for k in states if k.startswith("x") and k[1:].isdigit())
        if not cols:
            raise ValueError("%s: the table has no x0, x1, ... columns — pass the "
                             "output of ode_flow_states" % op)
        x = np.stack([np.asarray(states[c], dtype=np.float64) for c in cols], axis=1)
    else:
        x = np.asarray(states, dtype=np.float64)
    if x.ndim != 2 or x.shape[0] < 2:
        raise ValueError("%s: states must be (S, n) with S >= 2, got %s"
                         % (op, (x.shape,)))
    if not np.all(np.isfinite(x)):
        raise ValueError("%s: states contain a non-finite value" % op)
    a = int(axis)
    if not 0 <= a < x.shape[1]:
        raise ValueError("%s: axis %d outside 0..%d" % (op, a, x.shape[1] - 1))
    if direction not in (-1, 0, 1):
        raise ValueError("%s: direction must be -1, 0 or +1, got %r" % (op, direction))
    v = float(np.mean(x[:, a])) if value is None else float(value)
    s = x[:, a] - v
    lo, hi = s[:-1], s[1:]
    up = (lo < 0) & (hi >= 0)
    dn = (lo > 0) & (hi <= 0)
    hit = up if direction == 1 else (dn if direction == -1 else (up | dn))
    idx = np.flatnonzero(hit)
    if idx.size == 0:
        raise ValueError("%s: the trajectory never crosses %s = %g in direction %+d "
                         "(widen the window or move the plane)" % (op, "xyzw"[a], v, direction))
    t = lo[idx] / (lo[idx] - hi[idx])
    cross = x[idx] + (x[idx + 1] - x[idx]) * t[:, None]
    keep = [k for k in range(x.shape[1]) if k != a]
    out = cross[:, keep]
    return out[:, :2] if out.shape[1] >= 2 else np.stack([out[:, 0], np.zeros(out.shape[0])], axis=1)

def dynsys_lyapunov_spectrum(system="lorenz", params=None, x0=None, t_end=200.0,
                             dt=0.005, burn_in=20.0):
    """The Lyapunov spectrum by tangent flow + QR — and the sum you can check.

    Integrates the state together with an orthonormal frame of tangent vectors
    (the variational equation ``dY/dt = J(x) Y``), re-orthonormalising by QR at
    every step and accumulating ``log`` of the diagonal. The exponents come out
    **ordered**, largest first.

    ★★**Why this earns its place — the trace identity.** The sum of the exponents
    equals the time-average of the divergence of the field:

        sum(lambda_i) == <div f>

    For Lorenz the divergence is the **constant** ``-(sigma + 1 + beta)``, so the
    sum is known in closed form: ``-13.6667`` for the classical parameters. That
    is an exact target the attractor picture cannot provide. The published largest
    exponent (≈ 0.906 for sigma=10, beta=8/3, rho=28) is a second, independent
    check.

    Returns a ``signal``: the exponents, descending.

    **Raises** ``ValueError``: unknown system; non-finite input; ``burn_in`` not
    shorter than ``t_end``; a trajectory that left float range.

    Limits: the exponents converge like ``1/sqrt(T)`` — a short window gives a
    plausible but wrong spectrum. The trace identity converges much faster and is
    the honest gate; the individual exponents need long windows.

    HALCON: no operator.
    """
    op = "dynsys_lyapunov_spectrum"
    p = _dyn_prepare(system, params)
    n = _dyn_system_dim(system, p)
    h = float(dt)
    if not np.isfinite(h) or h <= 0:
        raise ValueError("%s: dt must be finite and > 0" % op)
    if not (0.0 <= float(burn_in) < float(t_end)):
        raise ValueError("%s: need 0 <= burn_in < t_end, got %r and %r"
                         % (op, burn_in, t_end))
    x = (np.array([1.0] * n) if x0 is None
         else np.asarray(x0, dtype=np.float64).ravel())
    if x.size != n or not np.all(np.isfinite(x)):
        raise ValueError("%s: x0 must be %d finite numbers" % (op, n))

    def step(state):
        k1 = _dyn_derivative(system, p, state)
        k2 = _dyn_derivative(system, p, state + 0.5 * h * k1)
        k3 = _dyn_derivative(system, p, state + 0.5 * h * k2)
        k4 = _dyn_derivative(system, p, state + h * k3)
        return state + (h / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

    for _ in range(int(round(float(burn_in) / h))):
        x = step(x)
        if not np.all(np.isfinite(x)):
            raise ValueError("%s: the trajectory left float range during burn-in" % op)

    Q = np.eye(n)
    total = np.zeros(n)
    steps = int(round((float(t_end) - float(burn_in)) / h))
    for _ in range(steps):
        J = _dyn_jacobian(system, p, x)
        # 接方程式も同じ 4 次で進める(状態と次数を揃える)
        y1 = J @ Q
        y2 = _dyn_jacobian(system, p, step(x) if False else x) @ (Q + 0.5 * h * y1)
        y3 = _dyn_jacobian(system, p, x) @ (Q + 0.5 * h * y2)
        y4 = _dyn_jacobian(system, p, x) @ (Q + h * y3)
        Y = Q + (h / 6.0) * (y1 + 2.0 * y2 + 2.0 * y3 + y4)
        x = step(x)
        Q, R = np.linalg.qr(Y)
        d = np.diag(R).copy()
        sgn = np.sign(d)
        sgn[sgn == 0] = 1.0
        Q = Q * sgn
        total += np.log(np.abs(d) + 1e-300)
        if not np.all(np.isfinite(x)):
            raise ValueError("%s: the trajectory left float range" % op)
    return np.sort(total / (steps * h))[::-1]

def dynsys_bifurcation_map(kind="logistic", r_lo=2.5, r_hi=4.0, n_r=800,
                           burn_in=300, keep=100, x0=0.5):
    """The orbit diagram of a 1-D map — period doubling, as points you can count.

    For each parameter value the map is iterated ``burn_in`` times (discarded) and
    the next ``keep`` states are returned. ``logistic`` is ``r x (1 - x)``,
    ``sine`` is ``r sin(pi x)``, ``tent`` is ``r min(x, 1-x) * 2``.

    ★**Why this earns its place**: the first period-doubling values are known
    exactly for the logistic map — ``r = 3`` and ``r = 1 + sqrt 6 = 3.449489...``
    — and the ratio of successive intervals tends to **Feigenbaum's constant**
    ``4.669201...``, which is universal. Counting distinct states per ``r`` turns
    the picture into integers (1, 2, 4, 8, ...) that can be checked.

    Returns a ``pairs`` array of ``(r, x)``.

    **Raises** ``ValueError``: unknown map; ``r_lo >= r_hi``; non-positive counts;
    a grid over the cap; ``x0`` outside the unit interval.

    HALCON: no operator.
    """
    op = "dynsys_bifurcation_map"
    if kind not in DYNSYS_MAPS:
        raise ValueError("%s: kind must be one of %s, got %r" % (op, DYNSYS_MAPS, kind))
    lo, hi = float(r_lo), float(r_hi)
    if not (np.isfinite(lo) and np.isfinite(hi)) or hi <= lo:
        raise ValueError("%s: need r_lo < r_hi, got %r and %r" % (op, r_lo, r_hi))
    nr, nb, nk = int(n_r), int(burn_in), int(keep)
    if min(nr, nk) < 1 or nb < 0:
        raise ValueError("%s: n_r and keep must be >= 1 and burn_in >= 0" % op)
    if nr * nk > _DYN_MAX_GRID:
        raise ValueError("%s: n_r * keep = %d over the %d cap" % (op, nr * nk, _DYN_MAX_GRID))
    x = float(x0)
    if not (0.0 < x < 1.0):
        raise ValueError("%s: x0 must lie strictly in (0, 1), got %r" % (op, x0))
    r = np.linspace(lo, hi, nr)
    s = np.full(nr, x, dtype=np.float64)

    def step(v):
        if kind == "logistic":
            return r * v * (1.0 - v)
        if kind == "sine":
            return r * np.sin(np.pi * v)
        return r * 2.0 * np.minimum(v, 1.0 - v)

    for _ in range(nb):
        s = step(s)
    out = np.empty((nr, nk, 2), dtype=np.float64)
    for j in range(nk):
        s = step(s)
        out[:, j, 0] = r
        out[:, j, 1] = s
    pts = out.reshape(-1, 2)
    return pts[np.isfinite(pts).all(axis=1)]

def dynsys_correlation_dimension(points, n_radii=24, r_lo=None, r_hi=None,
                                 max_points=4000, seed=0):
    """Grassberger-Procaccia correlation dimension — the slope of ``log C(r)``.

    ``C(r)`` is the fraction of point pairs closer than ``r``; for a self-similar
    set it grows like ``r**D``, and *D* is read off the straight part of the
    log-log plot (fitted on the middle 60 % of the radii, where the curve is free
    of the small-``r`` noise floor and the large-``r`` saturation).

    ★**Why this earns its place**: unlike box counting it needs no grid, and its
    answers are known for simple sets — a circle gives **1**, a filled square
    **2**, a Cantor set ``log2/log3 = 0.6309``. It measures a different quantity
    from the existing ``fractal_dimension`` (box counting), so the two are an
    independent pair rather than two names for one number.

    Returns a ``measurement``: the fitted dimension.

    **Raises** ``ValueError``: fewer than 32 points; not a 2-D array; non-finite
    input; a degenerate cloud (every point identical); a radius range that leaves
    no pairs.

    Limits: sub-sampled to *max_points* (pairs grow quadratically). ★The
    dominant error is **not** the sub-sampling but the **radius window**: the
    default range is the 1st-25th percentile of pair distances, and on a *bounded*
    set its upper end runs into the boundary, where ``C(r)`` saturates and flattens
    the slope. Measured on a unit square (true D = 2): 1.879 with the default
    window and 1.873 / 1.879 / 1.871 at 400 / 1,500 / 3,000 points —— more points
    do **not** help; narrowing the window to ``r_lo=0.01, r_hi=0.1`` gives 1.947
    and ``0.002 / 0.05`` gives 2.050. Pass *r_lo* / *r_hi* explicitly when the
    answer matters, and report the window with the number.
    """
    op = "dynsys_correlation_dimension"
    p = np.asarray(points, dtype=np.float64)
    if p.ndim != 2 or p.shape[0] < 32:
        raise ValueError("%s: need (N, d) with N >= 32, got %s" % (op, (p.shape,)))
    if not np.all(np.isfinite(p)):
        raise ValueError("%s: points contain a non-finite value" % op)
    m = int(max_points)
    if p.shape[0] > m:
        rng = np.random.default_rng(int(seed))
        p = p[rng.choice(p.shape[0], size=m, replace=False)]
    d = np.linalg.norm(p[:, None, :] - p[None, :, :], axis=-1)
    iu = np.triu_indices(p.shape[0], 1)
    dist = d[iu]
    pos = dist[dist > 0]
    if pos.size == 0:
        raise ValueError("%s: every point is identical — no scale to measure" % op)
    lo = float(np.percentile(pos, 1)) if r_lo is None else float(r_lo)
    # ★上限は 60 パーセンタイルにしていたが、有界な集合では大きい r で C(r) が
    #   飽和して**傾きが下がる**(充填した正方形で 1.83、真値 2.0)。飽和の
    #   手前に寄せる。下限は近傍の離散化(雑音の床)を避ける。
    hi = float(np.percentile(pos, 25)) if r_hi is None else float(r_hi)
    if not (np.isfinite(lo) and np.isfinite(hi)) or hi <= lo or lo <= 0:
        raise ValueError("%s: need 0 < r_lo < r_hi, got %g and %g" % (op, lo, hi))
    radii = np.logspace(np.log10(lo), np.log10(hi), int(n_radii))
    counts = np.array([(dist < r).sum() for r in radii], dtype=np.float64)
    ok = counts > 0
    if ok.sum() < 4:
        raise ValueError("%s: fewer than 4 usable radii — the cloud has no scale range"
                         % op)
    lr, lc = np.log(radii[ok]), np.log(counts[ok] / dist.size)
    a = int(0.2 * lr.size)
    b = max(a + 3, int(0.8 * lr.size))
    slope = float(np.polyfit(lr[a:b], lc[a:b], 1)[0])
    return slope
