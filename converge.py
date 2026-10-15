# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""converge — iterate until it has converged, and say so only when it has.

A forward model that is "closer to reality" is often the limit of a process rather than a
closed formula: light bouncing between the walls of a groove, photons scattering in a turbid
slab, a deconvolution that is stopped somewhere. Each of these needs three things the
single-shot ops do not carry: a **driver** that runs the iteration, a **verdict** that it
converged (and how far it still is from the limit), and a **refusal** when it did not —
the last iterate of a run that diverged or oscillates must not come back looking like an
answer.

Ops
---
``iterate_fixed_point``  generic fixed-point driver x = g(x): plain iteration, Aitken's
                         delta-squared (Steffensen form) or Anderson acceleration in the
                         form of Walker & Ni 2011 eq. (3.1), solved by QR with left-most
                         columns dropped while the triangular factor is ill-conditioned.
                         Returns the residual history, iteration count, a converged flag and
                         an a-posteriori bound on the remaining error; refuses otherwise.
``conv_observed_order``  apparent (observed) order of convergence from three solutions on
                         systematically refined grids, Celik et al. 2008 eq. (3a)-(3c),
                         including a non-constant refinement ratio and oscillatory
                         convergence (s = -1).
``conv_gci``             the full procedure of Celik et al. 2008 (eqs. 1-7): extrapolated
                         value, approximate and extrapolated relative errors and the
                         fine-grid convergence index.
``mc_sequential_mean``   sequential Monte Carlo: add batches until the confidence interval
                         is narrower than a tolerance; returns the interval and the number
                         of samples used.

The Monte Carlo photon transport (``mcphoton.mc_photon_slab``) and the stopped
Richardson-Lucy deconvolution (``deconvstop.iv_richardson_lucy_until``) are siblings in the
same family (registry ``opsconverge``).

Refusal follows ``metriccontract``: a run that did not converge raises
:class:`NotConvergedError` (a ``MetricContractError``, hence a ``ValueError``) carrying the
record, or — with ``on_fail="record"`` — returns the record with ``x = None`` and the last
iterate under ``last_iterate`` (explicitly not an estimate). :func:`as_attempt` turns a
record into a ``metriccontract.Attempt`` so a sweep can rank failures last with
``value_or_worst``.

Provenance (public literature): Walker & Ni 2011, SIAM J. Numer. Anal. 49(4):1715
(Algorithm AA, eq. (3.1), Theorem 2.2 - equivalence with GMRES on linear problems, section 4 -
QR with condition-number column dropping after Yang et al.); Anderson 1965, J. ACM 12:547;
Aitken 1926, Proc. R. Soc. Edinburgh 46:289 and Steffensen 1933 (delta-squared);
Celik, Ghia, Roache, Freitas, Coleman & Raad 2008, J. Fluids Eng. 130(7):078001
(procedure for estimating discretization error, Table 1); Roache 1994, J. Fluids Eng.
116:405 (grid convergence index); Chow & Robbins 1965, Ann. Math. Statist. 36:457
(fixed-width sequential confidence intervals).
"""
from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np

from metriccontract import Attempt, MetricContractError

__all__ = ["iterate_fixed_point", "conv_observed_order", "conv_gci", "mc_sequential_mean"]

#: The fixed point of cos(x) (the "Dottie number"), used by the built-in example map.
DOTTIE = 0.7390851332151607

MAX_ITER_CAP = 1_000_000
MAX_SAMPLES_CAP = 200_000_000
#: Anderson: while cond(R) of the QR factor exceeds this, drop the oldest column (Walker & Ni 2011,
#: section 4, after Yang et al.). A design constant, not a knob: it only acts near rank deficiency.
ANDERSON_COND_MAX = 1e8
#: A residual that grows by this factor over the first one is called divergence.
DIVERGENCE_FACTOR = 1e8
#: Inner fixed-point solve for the observed order p (Celik eq. 3): absolute tolerance on p and cap.
P_TOL = 1e-13
P_MAX_ITER = 1000


class NotConvergedError(MetricContractError):
    """An iteration that did not converge. ``record`` holds the history and the reason."""

    def __init__(self, message, record=None):
        super().__init__(message)
        self.record = record


def _builtin_map(name):
    if name == "cos":
        return np.cos, 1.0
    raise ValueError("iterate_fixed_point: unknown built-in map %r (known: 'cos'); pass a callable" % (name,))


def _as_vec(x, op):
    try:
        a = np.asarray(x, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("%s: the iterate must be numeric" % op) from None
    return a


def _secant_lipschitz(xs, gs):
    """Largest secant ratio ||g(x_i) - g(x_{i-1})|| / ||x_i - x_{i-1}|| over the stored pairs."""
    best = None
    for i in range(1, len(xs)):
        dx = float(np.linalg.norm(xs[i] - xs[i - 1]))
        if dx <= 0.0:
            continue
        r = float(np.linalg.norm(gs[i] - gs[i - 1])) / dx
        best = r if best is None else max(best, r)
    return best


def _classify_failure(xs, res):
    """Why a run ended without convergence: oscillating (period 2) / stagnating / slow."""
    if len(xs) >= 4:
        d1 = float(np.linalg.norm(xs[-1] - xs[-2]))
        d2 = float(np.linalg.norm(xs[-1] - xs[-3]))
        if d1 > 0 and d2 < 1e-3 * d1:
            return "oscillating: the iterates alternate between two points (period-2 cycle, |x_k - x_(k-2)| = %.3g vs |x_k - x_(k-1)| = %.3g)" % (d2, d1)
    if len(res) >= 20:
        tail = np.asarray(res[-20:])
        if tail[-1] >= 0.5 * tail[0]:
            return "stagnating: the residual did not halve over the last 20 iterations (%.3g -> %.3g); the map is not a contraction near the iterates (oscillating or chaotic)" % (tail[0], tail[-1])
    return "not converged within max_iter (residual %.3g)" % (res[-1] if res else float("nan"))


def iterate_fixed_point(g="cos", x0=None, method="anderson", tol=1e-10, rtol=0.0, max_iter=500, m=5,
                        on_fail="raise", keep_iterates=False) -> dict:
    """Solve x = g(x) by fixed-point iteration (plain / Aitken / Anderson) and refuse if it does not converge.

    ``g`` is a callable mapping an iterate (scalar or array) to one of the same shape, or the
    name of a built-in example (``"cos"``: x = cos x, x0 = 1, fixed point 0.7390851332...).
    The residual is f_k = g(x_k) - x_k and the run has converged when
    ``||f_k|| <= tol + rtol * ||x_k||`` (2-norm). The value returned is g(x_k).

    ``method``:

    * ``"plain"``    x_{k+1} = g(x_k) — the bounce-by-bounce Neumann sum for a linear map.
    * ``"aitken"``   Aitken's delta-squared on x, g(x), g(g(x)) per step (Steffensen form),
      component-wise; a component whose second difference vanishes takes g(g(x)).
    * ``"anderson"`` Anderson acceleration (Walker & Ni 2011, Algorithm AA) with memory ``m``,
      written as their eq. (3.1): gamma = argmin ||f_k - dF_k gamma||_2 with
      dF_k = (f_{k-m_k+1} - f_{k-m_k}, ..., f_k - f_{k-1}), then
      x_{k+1} = g(x_k) - dG_k gamma (dG holds the same differences of g). The least-squares
      problem is solved by a QR factorisation; while cond(R) > ``ANDERSON_COND_MAX`` (1e8) the left-most
      (oldest) column is dropped (section 4 of Walker & Ni, after Yang et al.). On a linear
      map with no columns dropped this reproduces GMRES (their Theorem 2.2): the gates check it.

    Returned (a table dict): ``x`` (g(x_k)), ``converged``, ``n_iter``, ``n_evals`` (calls of g),
    ``residual_history`` (||f_k|| per iterate), ``lipschitz_estimate`` (largest secant ratio
    of g over the stored iterates), ``error_estimate`` = L/(1-L) * ||f_k|| — the a-posteriori
    contraction bound on |g(x_k) - x*|, ``None`` when the estimated L is not below 1 —
    ``columns_dropped`` (Anderson conditioning) and ``method``.

    **Refusal**: divergence (non-finite residual or growth by ``DIVERGENCE_FACTOR`` = 1e8),
    a period-2 oscillation, stagnation or running out of ``max_iter`` raises
    :class:`NotConvergedError` (a ``MetricContractError``) with the record attached. With
    ``on_fail="record"`` the record is returned instead, with ``x = None`` and the last
    iterate under ``last_iterate`` — never under ``x``.
    """
    op = "iterate_fixed_point"
    if isinstance(g, str):
        g, default_x0 = _builtin_map(g)
        if x0 is None:
            x0 = default_x0
    if not callable(g):
        raise ValueError("%s: g must be callable or a built-in name, got %r" % (op, type(g).__name__))
    if x0 is None:
        raise ValueError("%s: x0 is required with a user map" % op)
    if method not in ("plain", "aitken", "anderson"):
        raise ValueError("%s: method must be 'plain', 'aitken' or 'anderson', got %r" % (op, method))
    if on_fail not in ("raise", "record"):
        raise ValueError("%s: on_fail must be 'raise' or 'record', got %r" % (op, on_fail))
    tol, rtol = float(tol), float(rtol)
    if not (math.isfinite(tol) and tol >= 0 and math.isfinite(rtol) and rtol >= 0 and (tol > 0 or rtol > 0)):
        raise ValueError("%s: tol and rtol must be finite, >= 0 and not both 0" % op)
    try:
        max_iter = int(max_iter)
        m = int(m)
    except (TypeError, ValueError):
        raise ValueError("%s: max_iter and m must be integers" % op) from None
    if not 1 <= max_iter <= MAX_ITER_CAP:
        raise ValueError("%s: max_iter must be in 1..%d, got %d" % (op, MAX_ITER_CAP, max_iter))
    if m < 1:
        raise ValueError("%s: m must be >= 1, got %d" % (op, m))

    x = _as_vec(x0, op)
    scalar = x.ndim == 0
    shape = x.shape
    if not np.isfinite(x).all():
        raise ValueError("%s: x0 contains NaN or inf" % op)
    n_evals = 0

    def G(v):
        nonlocal n_evals
        n_evals += 1
        out = _as_vec(g(v.reshape(shape) if not scalar else float(v[0])), op)
        if out.shape != shape:
            raise ValueError("%s: g changed the shape of the iterate: %s -> %s" % (op, shape, out.shape))
        return out.reshape(-1)

    x = x.reshape(-1).copy()
    xs, gs, res = [], [], []
    iterates = [] if keep_iterates else None
    dF, dG = [], []
    dropped = 0
    reason = None
    converged = False
    gx = None
    res0 = None
    for k in range(max_iter + 1):
        if keep_iterates:
            iterates.append(x.reshape(shape).copy() if not scalar else float(x[0]))
        gx = G(x)
        f = gx - x
        rn = float(np.linalg.norm(f))
        if not math.isfinite(rn) or not np.isfinite(gx).all():
            reason = "diverged: g returned NaN or inf at iteration %d" % k
            break
        res.append(rn)
        xs.append(x.copy())
        gs.append(gx.copy())
        if res0 is None:
            res0 = max(rn, 1e-300)
        if rn <= tol + rtol * float(np.linalg.norm(x)):
            converged = True
            break
        if rn > DIVERGENCE_FACTOR * res0:
            reason = "diverged: the residual grew from %.3g to %.3g (factor > %.3g)" % (res0, rn, DIVERGENCE_FACTOR)
            break
        if len(xs) >= 14:
            d1 = float(np.linalg.norm(xs[-1] - xs[-2]))
            d2 = float(np.linalg.norm(xs[-1] - xs[-3]))
            d3 = float(np.linalg.norm(xs[-2] - xs[-4]))
            if d1 > 0 and d2 < 1e-9 * d1 and d3 < 1e-9 * d1:
                reason = _classify_failure(xs, res)
                break
        if k == max_iter:
            break
        if method == "plain":
            x = gx
        elif method == "aitken":
            ggx = G(gx)
            if not np.isfinite(ggx).all():
                reason = "diverged: g returned NaN or inf at iteration %d" % k
                break
            d1v = gx - x
            d2v = ggx - 2.0 * gx + x
            scale = np.abs(x) + np.abs(gx) + np.abs(ggx) + 1e-300
            ok = np.abs(d2v) > 1e-14 * scale
            nx = ggx.copy()
            nx[ok] = x[ok] - d1v[ok] ** 2 / d2v[ok]
            x = nx
        else:
            if len(xs) >= 2:
                dF.append(f - (gs[-2] - xs[-2]))
                dG.append(gx - gs[-2])
                # at most m columns, and never more columns than unknowns (a wide F_k has no unique gamma)
                while len(dF) > min(m, x.size):
                    dF.pop(0)
                    dG.pop(0)
            if not dF:
                x = gx
            else:
                while True:
                    Fm = np.column_stack(dF)
                    Q, R = np.linalg.qr(Fm)
                    sv = np.abs(np.diag(R))
                    cond = (np.linalg.cond(R) if sv.min() > 0 else math.inf)
                    if cond <= ANDERSON_COND_MAX or len(dF) == 1:
                        break
                    dF.pop(0)
                    dG.pop(0)
                    dropped += 1
                if not (math.isfinite(cond) and cond <= ANDERSON_COND_MAX):
                    dF.clear()
                    dG.clear()
                    dropped += 1
                    x = gx
                else:
                    gamma = np.linalg.solve(R, Q.T @ f)
                    x = gx - np.column_stack(dG) @ gamma
            if not np.isfinite(x).all():
                reason = "diverged: the Anderson step produced NaN or inf at iteration %d" % k
                break
    if not converged and reason is None:
        reason = _classify_failure(xs, res)

    L = _secant_lipschitz(xs[-6:], gs[-6:]) if len(xs) >= 2 else None
    est = None
    if converged and L is not None and L < 1.0:
        est = L / (1.0 - L) * res[-1]
    elif converged and len(xs) == 1:
        est = None

    def _shape(v):
        return float(v[0]) if scalar else v.reshape(shape)

    rec = {
        "op": op, "method": method,
        "converged": bool(converged),
        "x": _shape(gx) if converged else None,
        "n_iter": len(res) - 1 if res else 0,
        "n_evals": int(n_evals),
        "residual": res[-1] if res else None,
        "residual_history": [float(r) for r in res],
        "lipschitz_estimate": L,
        "error_estimate": est,
        "error_estimate_note": ("L/(1-L) * ||g(x_k) - x_k|| with L the largest secant ratio of g over the last "
                                "iterates (a-posteriori contraction bound; valid only if g is a contraction there)"),
        "columns_dropped": int(dropped),
        "reason": reason,
    }
    if keep_iterates:
        rec["iterates"] = iterates
    if not converged:
        rec["last_iterate"] = _shape(xs[-1]) if xs else None
        if on_fail == "raise":
            raise NotConvergedError("%s: %s — no value is returned as converged" % (op, reason), rec)
    return rec


def as_attempt(record, metric="fixed_point_residual"):
    """A convergence record -> ``metriccontract.Attempt`` (ok only when converged; value = final residual)."""
    if not isinstance(record, dict) or "converged" not in record:
        raise MetricContractError("as_attempt: expected a convergence record (a dict with 'converged')")
    if record["converged"]:
        return Attempt(ok=True, value=float(record["residual"]), reason=None, metric=metric)
    return Attempt(ok=False, value=None, reason=str(record.get("reason")), metric=metric)


# --------------------------------------------------------------------------- #
# Observed order and GCI (Celik et al. 2008)                                  #
# --------------------------------------------------------------------------- #
#: Celik et al. 2008, Table 1 (2-D backward-facing step; N = cell counts, r as printed = 3 digits).
#: The printed p and phi_ext are reproduced from the cell counts through eq. (2) (r21 = sqrt(N1/N2));
#: with the printed, rounded r32 = 1.333 the first column gives p = 1.537 -> "1.54" instead of 1.53.
CELIK_TABLE1 = {
    "monotonic": {"n_cells": (18000, 8000, 4500), "r": (1.5, 1.333), "phi": (6.063, 5.972, 5.863),
                  "p": 1.53, "phi_ext": 6.1685, "ea_pct": 1.5, "eext_pct": 1.7, "gci_pct": 2.2},
    "p_below_1": {"n_cells": (18000, 4500, 980), "r": (2.0, 2.143), "phi": (10.7880, 10.7250, 10.6050),
                  "p": 0.75, "phi_ext": 10.8801, "ea_pct": 0.6, "eext_pct": 0.9, "gci_pct": 1.1},
    "oscillatory": {"n_cells": (18000, 4500, 980), "r": (2.0, 2.143), "phi": (6.0042, 5.9624, 6.0909),
                    "p": 1.51, "phi_ext": 6.0269, "ea_pct": 0.7, "eext_pct": 0.4, "gci_pct": 0.5},
}


def _three(v, name, op):
    try:
        a = np.asarray(v, dtype=np.float64).reshape(-1)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be 3 numbers" % (op, name)) from None
    if a.size != 3 or not np.isfinite(a).all():
        raise ValueError("%s: %s must be 3 finite numbers, got %r" % (op, name, v))
    return a


def _ratios(h, r, n_cells, dim, op):
    given = sum(v is not None for v in (h, r, n_cells))
    if given != 1:
        raise MetricContractError("%s: give exactly one of h (h1 < h2 < h3), r (r21, r32) or n_cells "
                                  "(N1 > N2 > N3 with dim) — the refinement ratios are not guessed" % op)
    if h is not None:
        hh = _three(h, "h", op)
        if not (hh > 0).all():
            raise ValueError("%s: grid sizes must be > 0" % op)
        r21, r32 = hh[1] / hh[0], hh[2] / hh[1]
    elif n_cells is not None:
        nn = _three(n_cells, "n_cells", op)
        if dim not in (1, 2, 3):
            raise ValueError("%s: dim must be 1, 2 or 3 with n_cells (Celik eq. 1 / 2)" % op)
        hh = (1.0 / nn) ** (1.0 / dim)        # Celik eqs. (1)-(2): h = (domain / N)^(1/dim); the domain cancels in r
        r21, r32 = hh[1] / hh[0], hh[2] / hh[1]
    else:
        try:
            r21, r32 = (float(t) for t in r)
        except (TypeError, ValueError):
            raise ValueError("%s: r must be (r21, r32)" % op) from None
    if not (math.isfinite(r21) and math.isfinite(r32) and r21 > 1.0 and r32 > 1.0):
        raise MetricContractError("%s: refinement ratios must be > 1 with grid 1 the finest (h1 < h2 < h3), "
                                  "got r21=%r, r32=%r" % (op, r21, r32))
    return float(r21), float(r32)


def conv_observed_order(phi=None, h=None, r=None, n_cells=None, dim=None) -> dict:
    """Apparent order of convergence p from three systematically refined solutions (Celik et al. 2008, eq. 3).

    ``phi`` = (phi1, phi2, phi3) on grids 1 (finest) .. 3 (coarsest). The refinement is given
    by exactly one of ``h`` = (h1, h2, h3) representative cell sizes, ``r`` = (r21, r32) with
    r21 = h2/h1 and r32 = h3/h2, or ``n_cells`` = (N1, N2, N3) with ``dim`` (h from Celik eqs.
    (1)-(2)). With eps32 = phi3 - phi2 and eps21 = phi2 - phi1 (Step 3):

        p = |ln|eps32/eps21| + q(p)| / ln(r21)                       (3a)
        q(p) = ln((r21^p - s) / (r32^p - s))                          (3b)
        s = sign(eps32 / eps21)                                       (3c)

    solved by fixed-point iteration from the first term (q = 0) with :func:`iterate_fixed_point`
    (plain, as the paper prescribes; |p_k+1 - p_k| <= 1e-13, at most 1000 steps). q = 0 when r is constant. s = -1 flags **oscillatory
    convergence** (reported, not refused — Celik keeps the absolute values so the extrapolation
    goes toward h = 0).

    **Refusal**: eps21 or eps32 "very close" to zero (|eps| <= 1e-12 * max|phi|) — Celik: the
    procedure does not work there (oscillation or an exact solution; refine further) — and a
    fixed-point iteration for p that does not converge.

    Defaults: the first column of Celik et al. 2008 Table 1 (p = 1.53).
    """
    op = "conv_observed_order"
    if phi is None and h is None and r is None and n_cells is None:
        ex = CELIK_TABLE1["monotonic"]
        phi, n_cells, dim = ex["phi"], ex["n_cells"], 2
    if phi is None:
        raise MetricContractError("%s: phi (three solutions, finest first) is required" % op)
    f = _three(phi, "phi", op)
    r21, r32 = _ratios(h, r, n_cells, dim, op)
    e32 = float(f[2] - f[1])
    e21 = float(f[1] - f[0])
    floor = 1e-12 * float(np.max(np.abs(f)) + 1e-300)
    if abs(e21) <= floor or abs(e32) <= floor:
        raise MetricContractError(
            "%s: eps21 = %.3g or eps32 = %.3g is too close to zero — the procedure does not work there "
            "(oscillation, or the solution is already exact); refine further (Celik et al. 2008, Step 3)" % (op, e21, e32))
    ratio = e32 / e21
    s = 1.0 if ratio > 0 else -1.0
    lnr21 = math.log(r21)
    lnratio = math.log(abs(ratio))

    def q(p):
        a, b = r21 ** p - s, r32 ** p - s
        if a <= 0 or b <= 0:
            raise MetricContractError("%s: q(p) undefined (r^p - s <= 0 at p = %.6g)" % (op, p))
        return math.log(a / b)

    p0 = abs(lnratio) / lnr21
    if p0 <= 0:
        raise MetricContractError("%s: |eps32/eps21| = 1 gives p = 0 — no convergence is observed" % op)
    rec = iterate_fixed_point(lambda p: abs(lnratio + q(float(p))) / lnr21, x0=p0, method="plain",
                              tol=P_TOL, rtol=0.0, max_iter=P_MAX_ITER, on_fail="record")
    if not rec["converged"]:
        raise MetricContractError("%s: the fixed-point iteration for p did not converge (%s)" % (op, rec["reason"]))
    p = float(rec["x"])
    if not (math.isfinite(p) and p > 0):
        raise MetricContractError("%s: p = %r is not a positive order" % (op, p))
    notes = []
    if min(r21, r32) < 1.3:
        notes.append("a refinement ratio below 1.3 (Celik: r > 1.3 is desirable, from experience)")
    if s < 0:
        notes.append("oscillatory convergence (eps32/eps21 < 0)")
    return {"op": op, "p": p, "s": int(s), "oscillatory": bool(s < 0),
            "eps21": e21, "eps32": e32, "r21": r21, "r32": r32,
            "p_first_term": p0, "iterations": rec["n_iter"], "fixed_point_residual": rec["residual"],
            "phi": [float(v) for v in f], "notes": notes,
            "source": "Celik et al. 2008, J. Fluids Eng. 130:078001, eqs. (3a)-(3c)"}


def conv_gci(phi=None, h=None, r=None, n_cells=None, dim=None, safety_factor=1.25) -> dict:
    """Grid convergence index of the finest solution: Celik et al. 2008 procedure, eqs. (1)-(7).

    Takes the same inputs as :func:`conv_observed_order` (three solutions, finest first, and
    the refinement) and returns, with p from eq. (3):

        phi_ext21 = (r21^p phi1 - phi2) / (r21^p - 1)                  (4)   (and phi_ext32)
        e_a21     = |(phi1 - phi2) / phi1|                            (5)
        e_ext21   = |(phi_ext12 - phi1) / phi_ext12|                   (6)
        GCI_fine21 = 1.25 e_a21 / (r21^p - 1)                         (7)

    (``safety_factor`` = 1.25 as in eq. (7)). Fractions and percentages are both returned, and
    ``report`` reads "phi1 +- GCI". Note what the GCI is not: it bounds the discretization
    error of the fine solution only — "this does not account for modeling errors" (Celik).

    Refusal as in :func:`conv_observed_order`, plus phi1 = 0 or phi_ext = 0 (relative errors
    undefined). Defaults: Celik Table 1, first column (GCI 2.2 %).
    """
    op = "conv_gci"
    if phi is None and h is None and r is None and n_cells is None:
        ex = CELIK_TABLE1["monotonic"]
        phi, n_cells, dim = ex["phi"], ex["n_cells"], 2
    Fs = float(safety_factor)
    if not (math.isfinite(Fs) and Fs >= 1.0):
        raise ValueError("%s: safety_factor must be >= 1, got %r" % (op, safety_factor))
    o = conv_observed_order(phi=phi, h=h, r=r, n_cells=n_cells, dim=dim)
    p, r21, r32 = o["p"], o["r21"], o["r32"]
    f1, f2, f3 = o["phi"]
    if f1 == 0.0:
        raise MetricContractError("%s: phi1 = 0 — the relative errors of eqs. (5)-(7) are undefined" % op)
    a21 = r21 ** p
    a32 = r32 ** p
    ext21 = (a21 * f1 - f2) / (a21 - 1.0)
    ext32 = (a32 * f2 - f3) / (a32 - 1.0)
    if ext21 == 0.0:
        raise MetricContractError("%s: the extrapolated value is 0 — eq. (6) is undefined" % op)
    ea21 = abs((f1 - f2) / f1)
    eext21 = abs((ext21 - f1) / ext21)
    gci21 = Fs * ea21 / (a21 - 1.0)
    o2 = dict(o)
    o2.update({
        "op": op, "phi_ext21": ext21, "phi_ext32": ext32,
        "ea21": ea21, "eext21": eext21, "gci_fine21": gci21,
        "ea21_pct": 100.0 * ea21, "eext21_pct": 100.0 * eext21, "gci_fine21_pct": 100.0 * gci21,
        "safety_factor": Fs,
        "report": "%.6g +- %.3g %% (GCI_fine21, p = %.3g%s)" % (f1, 100.0 * gci21, p,
                                                               ", oscillatory" if o["oscillatory"] else ""),
        "source": "Celik et al. 2008, J. Fluids Eng. 130:078001, eqs. (1)-(7)",
    })
    return o2


# --------------------------------------------------------------------------- #
# Sequential Monte Carlo                                                      #
# --------------------------------------------------------------------------- #
def _builtin_sampler(name):
    if name == "pi":
        def pi_sampler(rng, n):
            u = rng.random((n, 2))
            return 4.0 * ((u * u).sum(axis=1) <= 1.0)
        return pi_sampler, math.pi
    raise ValueError("mc_sequential_mean: unknown built-in sampler %r (known: 'pi'); pass a callable" % (name,))


def _z(confidence, op):
    c = float(confidence)
    if not (0.5 <= c < 1.0):
        raise ValueError("%s: confidence must be in [0.5, 1), got %r" % (op, confidence))
    return NormalDist().inv_cdf(0.5 + c / 2.0)


class _Moments:
    """Running count / mean / M2 per column (Chan, Golub & LeVeque pairwise update)."""

    def __init__(self, k):
        self.n = 0
        self.mean = np.zeros(k)
        self.m2 = np.zeros(k)

    def add(self, X):
        X = np.asarray(X, dtype=np.float64)
        nb = X.shape[0]
        if nb == 0:
            return
        mb = X.mean(axis=0)
        m2b = ((X - mb) ** 2).sum(axis=0)
        n = self.n + nb
        d = mb - self.mean
        self.mean = self.mean + d * nb / n
        self.m2 = self.m2 + m2b + d * d * self.n * nb / n
        self.n = n

    def se(self):
        if self.n < 2:
            return np.full(self.mean.shape, math.inf)
        return np.sqrt(self.m2 / (self.n - 1) / self.n)


def _sequential_columns(draw, k, tol, rel_tol, z, batch, n_min, max_samples, op):
    """Add batches from ``draw(b) -> (n, k)`` until z * se <= tol + rel_tol * |mean| in every column."""
    mom = _Moments(k)
    hist = []
    b = 0
    converged = False
    while mom.n < max_samples:
        nb = min(batch, max_samples - mom.n)
        X = np.asarray(draw(b, nb), dtype=np.float64)
        if X.ndim == 1:
            X = X[:, None]
        if X.shape != (nb, k):
            raise ValueError("%s: the sampler returned shape %s, expected %s" % (op, X.shape, (nb, k)))
        if not np.isfinite(X).all():
            raise MetricContractError("%s: the sampler returned NaN or inf (batch %d)" % (op, b))
        mom.add(X)
        b += 1
        se = mom.se()
        hist.append((int(mom.n), mom.mean.copy(), se.copy()))
        if mom.n >= n_min and np.all(z * se <= tol + rel_tol * np.abs(mom.mean)):
            converged = True
            break
    return mom, hist, converged


def mc_sequential_mean(sampler="pi", tol=0.01, rel_tol=0.0, confidence=0.95, batch=4096,
                       max_samples=4_000_000, seed=0, on_fail="raise") -> dict:
    """Sequential Monte Carlo mean: add samples until the confidence interval is narrower than the tolerance.

    ``sampler(rng, n)`` returns n i.i.d. samples (a 1-D array) — or the built-in ``"pi"``
    (4 * [u^2 + v^2 <= 1], mean pi). Batch b is drawn from ``default_rng((seed, b))``, so the
    result is reproducible and does not depend on how many batches came before.

    Stops at the first batch boundary, from the second batch on, where the half-width
    z * s / sqrt(n) <= ``tol`` + ``rel_tol`` * |mean| (z from ``confidence``; s the running
    sample standard deviation). This is the fixed-width sequential interval of Chow & Robbins
    1965; never stopping inside the first two batches guards against an early, accidentally
    small variance (raise ``batch`` to guard more) — the actual coverage is checked by the
    gates, not assumed.

    Returns ``mean``, ``se``, ``ci`` (lower, upper), ``half_width``, ``n_samples`` (used),
    ``converged`` and ``history`` (n, mean, se per batch). **Refusal**: ``max_samples`` reached
    first raises ``NotConvergedError`` (``on_fail="record"`` returns the record with
    ``mean = None`` and the running values under ``last_mean`` / ``last_se``).
    """
    op = "mc_sequential_mean"
    truth = None
    if isinstance(sampler, str):
        sampler, truth = _builtin_sampler(sampler)
    if not callable(sampler):
        raise ValueError("%s: sampler must be callable(rng, n) or a built-in name" % op)
    if on_fail not in ("raise", "record"):
        raise ValueError("%s: on_fail must be 'raise' or 'record'" % op)
    tol, rel_tol = float(tol), float(rel_tol)
    if not (math.isfinite(tol) and tol >= 0 and math.isfinite(rel_tol) and rel_tol >= 0 and (tol > 0 or rel_tol > 0)):
        raise ValueError("%s: tol and rel_tol must be finite, >= 0 and not both 0" % op)
    z = _z(confidence, op)
    try:
        batch, max_samples, seed = int(batch), int(max_samples), int(seed)
    except (TypeError, ValueError):
        raise ValueError("%s: batch, max_samples and seed must be integers" % op) from None
    if batch < 2 or not 2 <= max_samples <= MAX_SAMPLES_CAP:
        raise ValueError("%s: need batch >= 2 and 2 <= max_samples <= %d" % (op, MAX_SAMPLES_CAP))
    n_min = 2 * batch

    def draw(b, n):
        return np.asarray(sampler(np.random.default_rng((seed, b)), n), dtype=np.float64).reshape(-1)

    mom, hist, converged = _sequential_columns(draw, 1, tol, rel_tol, z, batch, n_min, max_samples, op)
    mean = float(mom.mean[0])
    se = float(mom.se()[0])
    rec = {"op": op, "converged": bool(converged), "n_samples": int(mom.n), "confidence": float(confidence),
           "z": z,
           "history": [{"n": n, "mean": float(mu[0]), "se": float(s[0])} for n, mu, s in hist]}
    if truth is not None:
        rec["reference_value"] = truth
    if converged:
        rec.update({"mean": mean, "se": se, "half_width": z * se, "ci": (mean - z * se, mean + z * se)})
        return rec
    rec.update({"mean": None, "se": None, "ci": None, "half_width": None, "last_mean": mean, "last_se": se,
                "reason": "max_samples = %d reached with half-width %.3g > %.3g" % (max_samples, z * se,
                                                                                   tol + rel_tol * abs(mean))})
    if on_fail == "raise":
        raise NotConvergedError("%s: %s — no interval is returned as converged" % (op, rec["reason"]), rec)
    return rec
