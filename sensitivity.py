# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""sensitivity — which knobs matter, which only matter together, and which cannot be told apart.

Global sensitivity analysis for a model that can be run but not differentiated in
closed form (a renderer, an optical simulation, a measurement chain). Two stages, as
in the literature: a cheap **screening** that sorts the knobs into negligible / linear
/ non-linear-or-interacting (Morris elementary effects), then a **variance
decomposition** for the survivors (Sobol' indices). Two further ops answer the
calibration questions: whether parameters are **confounded** — several knobs move the
output the same way, so data can only fix a combination (Brun et al. 2001) — and
whether the residuals of a fitted model still carry **structure** the model lacks.

Ops
---
``doe_morris``        r one-at-a-time trajectories on a p-level grid (Morris 1991),
                      optionally the most spread-out r of many candidates
                      (Campolongo, Cariboni & Saltelli 2007; greedy selection).
``sens_morris``       elementary effects -> mu, mu* (mean |EE|, Campolongo et al.
                      2007) and sigma per factor, in unit-cube and natural units.
``doe_saltelli``      the A, B, A_B^(i) sample matrices of Saltelli et al. 2010 from a
                      Sobol' sequence (``mathnumerics.low_discrepancy``, reused);
                      ``n`` must be a power of two.
``sens_sobol``        first-order S1 (Saltelli et al. 2010 estimator) and total ST
                      (Jansen 1999 estimator) with bootstrap confidence intervals.
``mv_confounding``    collinearity index gamma_K (Brun, Reichert & Künsch 2001) for
                      every parameter subset, the confounded pairs, the largest
                      identifiable subsets and the parameter combinations that the data
                      do determine.
``mv_residual_pca``   principal components of a residual matrix and how many of them
                      rise above noise (Marchenko-Pastur edge for a known noise level,
                      permutation parallel analysis otherwise).

Provenance (public literature): Morris 1991, Technometrics 33(2):161; Campolongo,
Cariboni & Saltelli 2007, Environ. Model. Softw. 22(10):1509; Sobol' 1993 (Math. Model.
Comput. Exp. 1:407) and 2001 (Math. Comput. Simul. 55:271); Saltelli 2002, Comput.
Phys. Commun. 145:280; Saltelli et al. 2010, Comput. Phys. Commun. 181:259; Jansen
1999, Comput. Phys. Commun. 117:35; Ishigami & Homma 1990 (test function); Brun,
Reichert & Künsch 2001, Water Resour. Res. 37(4):1015; Marchenko & Pastur 1967;
Buja & Eyuboglu 1992 (permutation parallel analysis).
"""
from __future__ import annotations

import itertools
import math

import numpy as np

import doe as _doe

__all__ = ["doe_morris", "sens_morris", "doe_saltelli", "sens_sobol", "mv_confounding", "mv_residual_pca"]

MAX_SUBSET_FACTORS = 14
MAX_ELEMENTS = 50_000_000


# --------------------------------------------------------------------------- #
# Morris                                                                      #
# --------------------------------------------------------------------------- #
def _morris_trajectory(k: int, p: int, delta: float, rng) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """One trajectory B* (Morris 1991): (k+1, k) points in [0,1], the factor changed at each step and its sign.

    B* = (J x* + (delta/2) [(2B - J) D* + J]) P*  with B the (k+1, k) strictly lower
    triangular matrix of ones, J matrices of ones, D* a random diagonal of ±1, P* a random
    permutation matrix, and x* a random base point on the grid {0, 1/(p-1), ..., 1 - delta}.
    """
    B = np.tril(np.ones((k + 1, k)), -1)
    J = np.ones((k + 1, k))
    grid_max = int(round((1.0 - delta) * (p - 1)))
    xstar = rng.integers(0, grid_max + 1, size=k) / (p - 1)
    D = np.diag(rng.choice([-1.0, 1.0], size=k))
    perm = rng.permutation(k)
    P = np.eye(k)[:, perm]
    Bstar = (J * xstar[None, :] + 0.5 * delta * ((2 * B - J) @ D + J)) @ P
    diff = np.diff(Bstar, axis=0)
    changed = np.argmax(np.abs(diff), axis=1)
    sign = np.sign(diff[np.arange(k), changed])
    return Bstar, changed, sign


def doe_morris(r=10, factors=4, levels=4, seed=0, n_candidates=0) -> dict:
    """Morris one-at-a-time screening plan: ``r`` trajectories of k+1 runs -> ``design``.

    Each trajectory starts at a random point of the ``levels``-level grid on the unit
    cube and moves one factor at a time by delta = levels / (2 (levels - 1)) (Morris
    1991; with an even ``levels`` every grid level is equally likely to be visited),
    so r (k+1) runs give r elementary effects per factor. ``n_candidates > r`` draws that
    many trajectories and keeps r of them that are spread out: the trajectory distance
    of Campolongo et al. 2007 (sum over point pairs of their Euclidean distances), chosen
    greedily — a pair of the farthest trajectories first, then repeatedly the trajectory
    that adds the most distance (an approximation of their exhaustive search, stated in
    ``meta['selection']``).

    The coded matrix is 2u - 1 of the unit-cube points; ``meta`` keeps the trajectory
    bookkeeping that :func:`sens_morris` needs (``changed`` factor and ``sign`` per step).
    """
    op = "doe_morris"
    r = _doe._int_arg(r, "r", op, 2, 100000)
    spec = _doe._factor_spec(factors, op)
    k = len(spec["names"])
    p = _doe._int_arg(levels, "levels", op, 2, 1000)
    if p % 2:
        raise ValueError("%s: levels must be even (Morris 1991: delta = p/(2(p-1)) then reaches every "
                         "grid level with equal probability), got %d" % (op, p))
    n_candidates = _doe._int_arg(n_candidates, "n_candidates", op, 0, 5000)
    if n_candidates and n_candidates < r:
        raise ValueError("%s: n_candidates (%d) must be 0 or >= r (%d)" % (op, n_candidates, r))
    if r * (k + 1) > _doe.MAX_RUNS:
        raise ValueError("%s: r*(k+1) runs exceeds the cap" % op)
    delta = p / (2.0 * (p - 1))
    rng = np.random.default_rng(seed)
    m = n_candidates if n_candidates else r
    trajs = [_morris_trajectory(k, p, delta, rng) for _ in range(m)]
    selection = "random (Morris 1991)"
    if n_candidates:
        pts = np.stack([t[0] for t in trajs])                       # (m, k+1, k)
        dist = np.zeros((m, m))
        for a in range(m):
            # d_ab = sum over point pairs (p of a, q of b) of ||p - q||  (Campolongo et al. 2007, eq. 4)
            dist[a] = np.sqrt(((pts[a][None, :, None, :] - pts[:, None, :, :]) ** 2).sum(-1)).sum(axis=(1, 2))
        dist[np.diag_indices(m)] = 0.0
        i0, j0 = np.unravel_index(int(np.argmax(dist)), dist.shape)
        chosen = [int(i0), int(j0)]
        while len(chosen) < r:
            gain = dist[:, chosen].sum(axis=1)
            gain[chosen] = -np.inf
            chosen.append(int(np.argmax(gain)))
        trajs = [trajs[i] for i in chosen]
        selection = "Campolongo et al. 2007 distance, greedy from %d candidates" % n_candidates
    u = np.concatenate([t[0] for t in trajs], axis=0)
    changed = np.stack([t[1] for t in trajs])
    sign = np.stack([t[2] for t in trajs])
    return _doe._design("morris", 2.0 * u - 1.0, spec,
                        source="Morris 1991, Technometrics 33(2):161, doi:10.1080/00401706.1991.10484804",
                        meta={"r": r, "levels": p, "delta": delta, "changed": changed, "sign": sign,
                              "selection": selection, "seed": seed})


def sens_morris(design=None, y=None, negligible=0.05) -> dict:
    """Morris elementary effects -> mu, mu*, sigma per factor (Morris 1991; mu* Campolongo et al. 2007).

    ``design`` must come from :func:`doe_morris` (its trajectory bookkeeping is used) and
    ``y`` holds the model output for its rows in order. For trajectory t and step s that
    moves factor i by ±delta: ``EE_i = (y_s - y_{s-1}) / (±delta)`` in unit-cube units, and
    also per natural unit of the factor (``ee_natural``; on a log-scale factor the step
    is in log10 units).

    ``mu`` (mean EE) can cancel when effects change sign; ``mu_star`` (mean |EE|) does
    not and is the ranking measure; ``sigma`` (standard deviation, ddof = 1) is large when
    the effect depends on where the other factors are (non-linear or interacting).
    ``class`` per factor: ``negligible`` (mu* below ``negligible`` x the largest mu*),
    ``linear/additive`` (sigma < 0.1 mu*: the effect is the same everywhere — a
    convention of this op, stated), otherwise ``non-linear or interacting``.
    """
    op = "sens_morris"
    if design is None or y is None:
        design = doe_morris(10, 3)
        c = (design["coded"] + 1) / 2
        y = 3 * c[:, 0] + c[:, 1] ** 2 + 0.0 * c[:, 2]
    if not isinstance(design, dict) or design.get("kind") != "morris":
        raise ValueError("%s: design must come from doe_morris (kind='morris')" % op)
    C = _doe._design_coded(design, op)
    meta = design["meta"]
    changed, sign, delta = np.asarray(meta["changed"]), np.asarray(meta["sign"]), float(meta["delta"])
    r, k = changed.shape
    try:
        yv = np.asarray(y, dtype=np.float64).ravel()
    except (TypeError, ValueError):
        raise ValueError("%s: y must be numeric" % op) from None
    if yv.size != r * (k + 1) or C.shape[0] != r * (k + 1):
        raise ValueError("%s: expected %d outputs (r=%d trajectories x (k+1)=%d), got %d"
                         % (op, r * (k + 1), r, k + 1, yv.size))
    if not np.isfinite(yv).all():
        raise ValueError("%s: y contains NaN or inf" % op)
    nat = _doe.doe_decode(design)
    spec = _doe._spec_from_design(design, op)
    ee = np.full((r, k), np.nan)
    ee_nat = np.full((r, k), np.nan)
    Y = yv.reshape(r, k + 1)
    N = nat.reshape(r, k + 1, k)
    for t in range(r):
        for s in range(k):
            i = int(changed[t, s])
            dy = Y[t, s + 1] - Y[t, s]
            ee[t, i] = dy / (sign[t, s] * delta)
            dx = (math.log10(N[t, s + 1, i]) - math.log10(N[t, s, i])) if spec["scale"][i] == "log" \
                else (N[t, s + 1, i] - N[t, s, i])
            ee_nat[t, i] = dy / dx
    if np.isnan(ee).any():                                          # pragma: no cover - bookkeeping guarantees it
        raise ValueError("%s: a trajectory does not move every factor once" % op)
    mu, mu_star = ee.mean(axis=0), np.abs(ee).mean(axis=0)
    sigma = ee.std(axis=0, ddof=1)
    top = float(mu_star.max()) if mu_star.size else 0.0
    cls = []
    for i in range(k):
        if mu_star[i] <= float(negligible) * top:
            cls.append("negligible")
        elif sigma[i] < 0.1 * mu_star[i]:
            cls.append("linear/additive")
        else:
            cls.append("non-linear or interacting")
    order = [design["factors"][i] for i in np.argsort(-mu_star)]
    return {"factors": list(design["factors"]), "mu": mu, "mu_star": mu_star, "sigma": sigma,
            "mu_star_natural": np.abs(ee_nat).mean(axis=0), "sigma_natural": ee_nat.std(axis=0, ddof=1),
            "elementary_effects": ee, "ee_natural": ee_nat, "class": cls, "ranking": order, "r": r,
            "delta": delta, "negligible": float(negligible)}


# --------------------------------------------------------------------------- #
# Sobol' / Saltelli                                                            #
# --------------------------------------------------------------------------- #
def _sobol_points(n: int, dim: int, seed):
    if dim <= 16:
        import mathnumerics                                         # reuse the shared low-discrepancy generator
        return mathnumerics.low_discrepancy(n, dim, "sobol", seed=seed)
    from scipy.stats import qmc                                     # same engine, beyond its 16-D table
    import warnings
    eng = qmc.Sobol(d=dim, scramble=seed is not None, seed=seed)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return eng.random(n)


def doe_saltelli(n=1024, factors=3, seed=0) -> dict:
    """Sample matrices for Sobol' indices (Saltelli et al. 2010) -> ``design`` of n (k + 2) runs.

    A Sobol' sequence of dimension 2k gives two independent n x k matrices A (first k
    columns) and B (last k). For each factor i, ``A_B^(i)`` is A with column i taken from
    B. Rows are stacked as ``[A; B; A_B^(1); ...; A_B^(k)]`` (``meta['blocks']``), which is
    the layout :func:`sens_sobol` reads.

    ``n`` must be a power of two: the balance properties of a Sobol' sequence hold for
    2^m points, and the estimators' error behaves erratically otherwise — the op refuses
    rather than silently degrading. ``seed`` scrambles the sequence (Owen scrambling via
    scipy); ``seed=None`` uses the plain sequence.
    """
    op = "doe_saltelli"
    n = _doe._int_arg(n, "n", op, 2, 2 ** 22)
    if n & (n - 1):
        raise ValueError("%s: n must be a power of two (got %d; nearest %d or %d)"
                         % (op, n, 2 ** int(math.floor(math.log2(n))), 2 ** int(math.ceil(math.log2(n)))))
    spec = _doe._factor_spec(factors, op)
    k = len(spec["names"])
    if n * (k + 2) > _doe.MAX_RUNS:
        raise ValueError("%s: n*(k+2) = %d runs exceeds the cap %d" % (op, n * (k + 2), _doe.MAX_RUNS))
    u = _sobol_points(n, 2 * k, seed)
    A, B = u[:, :k], u[:, k:]
    blocks = [A, B]
    for i in range(k):
        ab = A.copy()
        ab[:, i] = B[:, i]
        blocks.append(ab)
    unit = np.concatenate(blocks, axis=0)
    return _doe._design("saltelli", 2.0 * unit - 1.0, spec,
                        source="Saltelli et al. 2010, Comput. Phys. Commun. 181(2):259, doi:10.1016/j.cpc.2009.09.018",
                        meta={"n": n, "blocks": ["A", "B"] + ["AB_%d" % (i + 1) for i in range(k)],
                              "seed": seed, "sequence": "sobol"})


def _sobol_estimates(fA, fB, fAB):
    V = np.var(np.concatenate([fA, fB]), ddof=1)
    if not V > 0:
        return None, None, V
    s1 = np.array([np.mean(fB * (fAB[i] - fA)) for i in range(len(fAB))]) / V
    st = np.array([0.5 * np.mean((fA - fAB[i]) ** 2) for i in range(len(fAB))]) / V
    return s1, st, V


def sens_sobol(design=None, y=None, n_boot=500, level=0.95, seed=0) -> dict:
    """First-order and total Sobol' indices with bootstrap confidence intervals.

    From the outputs on a :func:`doe_saltelli` design (blocks A, B, A_B^(i)):

    * ``S1_i = (1/N) sum_j f(B)_j (f(A_B^(i))_j - f(A)_j) / V`` (Saltelli et al. 2010,
      Table 2 (b));
    * ``ST_i = (1/(2N)) sum_j (f(A)_j - f(A_B^(i))_j)^2 / V`` (Jansen 1999; Saltelli et al.
      2010, Table 2 (f));
    * ``V`` = variance of the outputs at A and B together.

    S1 is the share of output variance a factor explains alone; ST adds every interaction
    it takes part in. ST ~ 0 means the factor can be fixed anywhere in its range;
    ST - S1 large means it acts through interactions. Confidence intervals come from
    ``n_boot`` bootstrap resamples of the N rows (the same row index across A, B and
    A_B^(i)) at ``level``. The sum of S1 (``sum_s1``) is <= 1 up to estimation error; a value
    far below 1 says interactions carry the rest.
    """
    op = "sens_sobol"
    if design is None or y is None:
        design = doe_saltelli(256, [("x1", -math.pi, math.pi), ("x2", -math.pi, math.pi), ("x3", -math.pi, math.pi)])
        x = design["natural"]
        y = np.sin(x[:, 0]) + 7 * np.sin(x[:, 1]) ** 2 + 0.1 * x[:, 2] ** 4 * np.sin(x[:, 0])
    if not isinstance(design, dict) or design.get("kind") != "saltelli":
        raise ValueError("%s: design must come from doe_saltelli (kind='saltelli')" % op)
    _doe._design_coded(design, op)
    n = int(design["meta"]["n"])
    k = len(design["factors"])
    try:
        yv = np.asarray(y, dtype=np.float64).ravel()
    except (TypeError, ValueError):
        raise ValueError("%s: y must be numeric" % op) from None
    if yv.size != n * (k + 2):
        raise ValueError("%s: expected %d outputs (n=%d x (k+2)=%d), got %d" % (op, n * (k + 2), n, k + 2, yv.size))
    if not np.isfinite(yv).all():
        raise ValueError("%s: y contains NaN or inf" % op)
    n_boot = _doe._int_arg(n_boot, "n_boot", op, 0, 100000)
    if not 0 < float(level) < 1:
        raise ValueError("%s: level must be in (0, 1), got %r" % (op, level))
    fA, fB = yv[:n], yv[n:2 * n]
    fAB = [yv[(2 + i) * n:(3 + i) * n] for i in range(k)]
    s1, st, V = _sobol_estimates(fA, fB, fAB)
    if s1 is None:
        raise ValueError("%s: the output does not vary (V = %g) — no variance to decompose" % (op, V))
    ci1 = cit = None
    if n_boot:
        rng = np.random.default_rng(seed)
        b1, bt = np.empty((n_boot, k)), np.empty((n_boot, k))
        for b in range(n_boot):
            idx = rng.integers(0, n, n)
            e1, et, _v = _sobol_estimates(fA[idx], fB[idx], [f[idx] for f in fAB])
            if e1 is None:
                e1, et = np.full(k, np.nan), np.full(k, np.nan)
            b1[b], bt[b] = e1, et
        lo, hi = 100 * (1 - float(level)) / 2, 100 * (1 + float(level)) / 2
        ci1 = np.stack([np.nanpercentile(b1, lo, axis=0), np.nanpercentile(b1, hi, axis=0)], axis=1)
        cit = np.stack([np.nanpercentile(bt, lo, axis=0), np.nanpercentile(bt, hi, axis=0)], axis=1)
    return {"factors": list(design["factors"]), "S1": s1, "ST": st, "S1_ci": ci1, "ST_ci": cit,
            "variance": float(V), "sum_s1": float(s1.sum()), "interaction_share": st - s1, "n": n,
            "n_evaluations": int(yv.size), "level": float(level), "n_boot": n_boot,
            "ranking": [design["factors"][i] for i in np.argsort(-st)]}


# --------------------------------------------------------------------------- #
# confounding (Brun et al. 2001)                                              #
# --------------------------------------------------------------------------- #
def _gamma(Sn: np.ndarray) -> float:
    lam = np.linalg.eigvalsh(Sn.T @ Sn)
    lmin = float(lam.min())
    return float("inf") if lmin <= 1e-15 else 1.0 / math.sqrt(lmin)


def mv_confounding(S=None, names=None, threshold=10.0, log_params=False, max_subset=None) -> dict:
    """Collinearity index gamma_K (Brun, Reichert & Künsch 2001): which parameters the data can fix.

    ``S`` is the sensitivity matrix (observations x parameters): column j = the change of
    every output per change of parameter j (finite differences of a simulation, or a
    Jacobian), ideally already scaled to be dimensionless (Brun: s_ij = dtheta_j / sc_i *
    dy_i/dtheta_j). Each column is normalised to unit length, ``s~_j = s_j / ||s_j||``, and for
    a parameter subset K

        gamma_K = 1 / sqrt( min eigenvalue of S~_K^T S~_K ).

    gamma_K = 1 for orthogonal columns; it grows when a change in one parameter can be
    compensated by the others (Brun et al. use 10-15 as the critical range; ``threshold``
    defaults to 10). Returned: ``delta_msqr`` (importance, sqrt(mean s_ij^2) on the given
    scale), gamma of the full set and of every subset up to ``max_subset`` (all subsets
    for <= 14 parameters), the ``confounded_pairs`` (gamma > threshold), the largest
    identifiable subsets, the ``undetermined_direction`` of the full set (eigenvector of
    the smallest eigenvalue: moving the parameters along it barely changes the output),
    and per ``confounded_groups`` entry (the union of the minimal confounded subsets) the
    combinations the data ``determined`` (eigenvalue of the group's S~^T S~ >=
    1/threshold^2) and those ``undetermined``; parameters in no group are
    ``determined_individually``.
    With ``log_params=True`` (columns are sensitivities to log parameters) the
    combinations are written as products of powers — e.g. ``n^1 * d^1`` when only the
    product of refractive index and thickness reaches the data. Columns that are all zero
    are reported as ``no_influence`` and left out of gamma.
    """
    op = "mv_confounding"
    if S is None:
        rng = np.random.default_rng(0)
        g = rng.normal(size=(50, 2))
        S = np.column_stack([g[:, 0], g[:, 0] * 1.001 + 0.001 * g[:, 1], g[:, 1]])
        names = ["n", "d", "gain"]
        log_params = True
    try:
        A = np.asarray(S, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("%s: S must be numeric" % op) from None
    if A.ndim != 2 or A.shape[0] < 2 or A.shape[1] < 2:
        raise ValueError("%s: S must be (observations >= 2, parameters >= 2), got shape %s" % (op, A.shape))
    if A.size > MAX_ELEMENTS:
        raise ValueError("%s: S has %d elements (cap %d)" % (op, A.size, MAX_ELEMENTS))
    if not np.isfinite(A).all():
        raise ValueError("%s: S contains NaN or inf" % op)
    K = A.shape[1]
    names = ["p%d" % (j + 1) for j in range(K)] if names is None else [str(x) for x in names]
    if len(names) != K:
        raise ValueError("%s: %d names for %d parameters" % (op, len(names), K))
    thr = float(threshold)
    if not (math.isfinite(thr) and thr > 1):
        raise ValueError("%s: threshold must be > 1, got %r" % (op, threshold))
    norms = np.linalg.norm(A, axis=0)
    dmsqr = np.sqrt((A ** 2).mean(axis=0))
    live = [j for j in range(K) if norms[j] > 1e-300]
    dead = [names[j] for j in range(K) if j not in live]
    Sn = np.zeros_like(A)
    Sn[:, live] = A[:, live] / norms[live]
    # ★2026-10-15: 生きた列(影響ゼロでない列)が 1 本以下なら、組み合わせが 1 つも無いので交絡は定義上ない
    #   (以前は max_subset の範囲 2..2 に 1 が入って ValueError で落ちた。simcal で σ = 0 のボケの列が 0 になって踏んだ)。
    if max_subset is None:
        max_subset = len(live) if len(live) <= MAX_SUBSET_FACTORS else 3
    if len(live) >= 2:
        max_subset = _doe._int_arg(max_subset, "max_subset", op, 2, len(live))
    else:
        max_subset = 0                                              # 部分集合なし(0 本・1 本)
    subsets = []
    for size in range(2, min(max_subset, len(live)) + 1):
        for comb in itertools.combinations(live, size):
            subsets.append((tuple(names[j] for j in comb), _gamma(Sn[:, list(comb)])))
    pairs = sorted(((s, g) for s, g in subsets if len(s) == 2), key=lambda t: -t[1])
    confounded = [(s, g) for s, g in pairs if g > thr]
    ident = [s for s, g in subsets if g <= thr]
    best = max((len(s) for s in ident), default=1)
    largest = sorted(s for s in ident if len(s) == best) if ident else [(names[j],) for j in live]
    full = _gamma(Sn[:, live]) if len(live) >= 2 else 1.0
    lam, vec = np.linalg.eigh(Sn[:, live].T @ Sn[:, live]) if live else (np.zeros(0), np.zeros((0, 0)))

    def combo(v, cols):
        v = v / np.abs(v).max()
        v = v * np.sign(v[np.argmax(np.abs(v))])
        terms = [(names[cols[i]], float(v[i])) for i in np.argsort(-np.abs(v), kind="stable") if abs(v[i]) > 0.05]
        if log_params:
            return " * ".join("%s^%.2g" % (nm, e) for nm, e in terms)
        return " + ".join("%.2g*%s" % (e, nm) for nm, e in terms)

    und = None
    if lam.size and (1.0 / math.sqrt(max(lam[0], 1e-300))) > thr:
        und = {"eigenvalue": float(lam[0]), "combination": combo(vec[:, 0], live),
               "weights": dict(zip([names[j] for j in live], vec[:, 0].tolist()))}
    # confounded groups: union of the *minimal* confounded subsets (gamma > threshold while every
    # proper subset is identifiable), merged where they overlap. Inside a group the eigenvectors of
    # S~^T S~ split into combinations the data fix (eigenvalue >= 1/threshold^2) and those they do not.
    gmap = {s: g for s, g in subsets}
    minimal = [set(s) for s, g in subsets if g > thr and all(
        gmap.get(t, 0.0) <= thr for r in range(2, len(s)) for t in itertools.combinations(s, r))]
    groups = []
    for m in minimal:
        for g in [g for g in groups if g & m]:
            groups.remove(g)
            m |= g
        groups.append(m)
    group_out = []
    for g in groups:
        idx = [j for j in live if names[j] in g]
        lg, vg = np.linalg.eigh(Sn[:, idx].T @ Sn[:, idx])
        group_out.append({
            "parameters": [names[j] for j in idx],
            "gamma": _gamma(Sn[:, idx]),
            "determined": [combo(vg[:, i], idx) for i in range(lg.size - 1, -1, -1) if lg[i] >= 1.0 / thr ** 2],
            "undetermined": [combo(vg[:, i], idx) for i in range(lg.size) if lg[i] < 1.0 / thr ** 2]})
    in_groups = set().union(*groups) if groups else set()
    alone = [names[j] for j in live if names[j] not in in_groups]
    return {"names": names, "delta_msqr": dmsqr, "gamma_full": full, "gamma_subsets": subsets,
            "pairs": pairs, "confounded_pairs": confounded, "largest_identifiable": largest,
            "undetermined_direction": und, "confounded_groups": group_out,
            "determined_individually": alone,
            "no_influence": dead, "threshold": thr, "log_params": bool(log_params),
            "identifiable": bool(full <= thr and not dead)}


# --------------------------------------------------------------------------- #
# residual PCA                                                                 #
# --------------------------------------------------------------------------- #
def mv_residual_pca(R=None, noise_sigma=None, n_perm=100, seed=0) -> dict:
    """Do the residuals of a fitted model still carry structure? PCA of a residual matrix vs. noise.

    ``R`` is (observations x variables) — e.g. one row per image, one column per pixel or
    feature, holding measured minus simulated. It is **not** centred: a bias common to
    every observation is itself a structure the model lacks.

    A component counts as structural when its singular value exceeds the noise edge:

    * with ``noise_sigma`` (e.g. the temporal noise from an EMVA 1288 characterisation):
      the largest singular value of an n x p matrix of i.i.d. noise is about
      sigma (sqrt(n) + sqrt(p)) (Marchenko-Pastur edge), used as the threshold;
    * without it: permutation parallel analysis (Buja & Eyuboglu 1992) — each column is
      shuffled independently ``n_perm`` times, which keeps every column's distribution
      but destroys structure shared across columns, and component i must beat the 95th
      percentile of the shuffled i-th singular values. (It cannot see a structure that
      lives inside single columns, e.g. a constant bias column — use ``noise_sigma``
      for that.)

    Returns the singular values, the threshold(s), ``n_structural``, the share of the
    residual energy in the structural components, and their loadings (reshape a loading
    to the image shape to see *where* the model is wrong) and scores.
    """
    op = "mv_residual_pca"
    if R is None:
        rng = np.random.default_rng(0)
        R = 0.1 * rng.normal(size=(20, 64)) + np.outer(rng.normal(size=20), np.sin(np.linspace(0, 3, 64)))
    try:
        A = np.asarray(R, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("%s: R must be numeric" % op) from None
    if A.ndim != 2 or A.shape[0] < 3 or A.shape[1] < 3:
        raise ValueError("%s: R must be (observations >= 3, variables >= 3), got shape %s" % (op, A.shape))
    if A.size > MAX_ELEMENTS:
        raise ValueError("%s: R has %d elements (cap %d)" % (op, A.size, MAX_ELEMENTS))
    if not np.isfinite(A).all():
        raise ValueError("%s: R contains NaN or inf" % op)
    n, p = A.shape
    U, s, Vt = np.linalg.svd(A, full_matrices=False)
    flip = np.sign(Vt[np.arange(Vt.shape[0]), np.argmax(np.abs(Vt), axis=1)])
    flip[flip == 0] = 1.0
    U, Vt = U * flip, Vt * flip[:, None]
    if noise_sigma is not None:
        sig = float(noise_sigma)
        if not (math.isfinite(sig) and sig > 0):
            raise ValueError("%s: noise_sigma must be > 0, got %r" % (op, noise_sigma))
        thr = np.full(s.size, sig * (math.sqrt(n) + math.sqrt(p)))
        mode = "marchenko_pastur_edge"
    else:
        n_perm = _doe._int_arg(n_perm, "n_perm", op, 10, 10000)
        rng = np.random.default_rng(seed)
        sims = np.empty((n_perm, s.size))
        for b in range(n_perm):
            P = np.stack([A[rng.permutation(n), j] for j in range(p)], axis=1)
            sims[b] = np.linalg.svd(P, compute_uv=False)
        thr = np.percentile(sims, 95, axis=0)
        mode = "permutation_parallel_analysis"
    above = s > thr
    n_struct = int(np.argmin(above)) if not above.all() else int(s.size)
    energy = float((s ** 2).sum())
    share = float((s[:n_struct] ** 2).sum() / energy) if energy > 0 else 0.0
    return {"singular_values": s, "threshold": thr, "mode": mode, "n_structural": n_struct,
            "structural_energy_share": share, "loadings": Vt[:n_struct].T, "scores": U[:, :n_struct] * s[:n_struct],
            "rms": float(math.sqrt(energy / A.size)), "structure_detected": n_struct > 0,
            "noise_sigma": None if noise_sigma is None else float(noise_sigma)}
