# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""multivar — what a set of runs says: components, latent regression, response surfaces, main effects.

The analysis half of the design-of-experiments family (the plans are in :mod:`doe`).
Inputs are tables of numbers — features measured on images, simulation outputs,
bench readings — and every op returns not only the answer but what it rests on
(how many components the data actually support, which terms the plan could not
separate, whether the model is short of the data), so that a model that only
*looks* good is visible.

Ops
---
``feat_image_vector``  images -> a feature table with column names and units; the
                       grey-level range is **given**, never guessed from the data.
``mv_pca``             principal components of a table; the number of components is
                       judged three ways — cumulative share, Horn's parallel
                       analysis, and the MDL criterion (``mathspectral.n_sources_mdl``).
``mv_pls``             partial least squares (NIPALS, Wold et al. 2001) with
                       cross-validated Q^2, the Q^2 component rule and VIP; a second
                       implementation (SIMPLS, de Jong 1993) is selectable and agrees
                       exactly for one response.
``rsm_fit``            linear / interaction / quadratic response surface on a
                       ``design``: ANOVA, lack of fit against pure error, the stationary
                       point and its canonical analysis; a model the plan cannot support
                       is refused with the aliased terms named.
``doe_main_effects``   level means per factor (Taguchi-style response table) and the
                       dispersion (log s) per level; SN ratios are reported but are not
                       the basis of the decision (Box 1988).

Provenance (public literature): Hotelling 1933 / Jolliffe 2002 (PCA); Horn 1965,
Psychometrika 30:179 (parallel analysis); Wax & Kailath 1985 (MDL); Wold, Ruhe, Wold
& Dunn 1984, SIAM J. Sci. Stat. Comput. 5(3):735 and Wold, Sjöström & Eriksson 2001,
Chemom. Intell. Lab. Syst. 58:109 (PLS, NIPALS, Q^2, VIP); de Jong 1993, Chemom.
Intell. Lab. Syst. 18:251 (SIMPLS); Box & Wilson 1951 and Box & Draper 1987
(response surfaces, canonical analysis); Taguchi 1987 and Box 1988, Technometrics
30(1):1 (SN ratios and their critique).
"""
from __future__ import annotations

import itertools
import math

import numpy as np

import doe as _doe

__all__ = ["feat_image_vector", "mv_pca", "mv_pls", "rsm_fit", "doe_main_effects"]

#: Q^2 limit for a PLS component to count as significant: Q^2_a >= 1 - 0.95^2 = 0.0975
#: (Wold, Sjöström & Eriksson 2001, section 3.6, "the component is significant if
#: Q^2 > 0.097")
Q2_LIMIT = 0.0975
MAX_ELEMENTS = 50_000_000


# --------------------------------------------------------------------------- #
# input helpers                                                               #
# --------------------------------------------------------------------------- #
def _table_matrix(X, op: str, name: str = "X", min_rows: int = 3, min_cols: int = 1):
    """(matrix, names, units) from an ndarray or a feature table ``{"matrix", "names", "units"}``."""
    names = units = None
    if isinstance(X, dict):
        if "matrix" not in X:
            raise ValueError("%s: %s table must carry a 'matrix' entry" % (op, name))
        names, units = X.get("names"), X.get("units")
        X = X["matrix"]
    try:
        A = np.asarray(X, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be numeric" % (op, name)) from None
    if A.ndim == 1:
        A = A[:, None]
    if A.ndim != 2:
        raise ValueError("%s: %s must be 2-D (samples x variables), got shape %s" % (op, name, A.shape))
    if A.shape[0] < min_rows or A.shape[1] < min_cols:
        raise ValueError("%s: %s needs >= %d rows and >= %d columns, got %s" % (op, name, min_rows, min_cols, A.shape))
    if A.size > MAX_ELEMENTS:
        raise ValueError("%s: %s has %d elements (cap %d)" % (op, name, A.size, MAX_ELEMENTS))
    if not np.isfinite(A).all():
        raise ValueError("%s: %s contains NaN or inf" % (op, name))
    p = A.shape[1]
    names = list(names) if names is not None else ["%s%d" % (name.lower(), j + 1) for j in range(p)]
    units = list(units) if units is not None else [""] * p
    if len(names) != p or len(units) != p:
        raise ValueError("%s: %s has %d columns but %d names / %d units" % (op, name, p, len(names), len(units)))
    return A, names, units


def _standardise(A: np.ndarray, names, op: str, scale: bool):
    mean = A.mean(axis=0)
    sd = A.std(axis=0, ddof=1) if scale else np.ones(A.shape[1])
    if scale:
        dead = [names[j] for j in np.flatnonzero(~(sd > 1e-12 * np.maximum(1.0, np.abs(mean))))]
        if dead:
            raise ValueError("%s: columns with no variation cannot be standardised: %s "
                             "(remove them — they carry no information)" % (op, dead))
    return (A - mean) / sd, mean, sd


# --------------------------------------------------------------------------- #
# image features                                                              #
# --------------------------------------------------------------------------- #
#: name -> (needs data_range, unit template, description). "{u}" is the image unit.
FEATURES = {
    "mean": (False, "{u}", "mean grey level"),
    "std": (False, "{u}", "standard deviation of grey level"),
    "p01": (False, "{u}", "1st percentile"),
    "p50": (False, "{u}", "median"),
    "p99": (False, "{u}", "99th percentile"),
    "rms_contrast": (False, "1", "std / mean (needs mean > 0)"),
    "michelson_contrast": (False, "1", "(p99 - p01) / (p99 + p01) (needs p99 + p01 > 0)"),
    "grad_energy": (False, "{u}^2/px^2", "mean squared central-difference gradient (sharpness)"),
    "laplacian_var": (False, "{u}^2/px^4", "variance of the 5-point Laplacian (focus measure)"),
    "saturated_fraction": (True, "1", "share of pixels at or above the top of data_range"),
    "dark_fraction": (True, "1", "share of pixels at or below the bottom of data_range"),
    "entropy_bits": (True, "bit", "Shannon entropy of a 256-bin histogram over data_range"),
}
DEFAULT_FEATURES = ("mean", "std", "p01", "p99", "rms_contrast", "michelson_contrast",
                    "grad_energy", "laplacian_var")


def _images(images, op: str):
    if isinstance(images, np.ndarray):
        if images.ndim == 2:
            seq = [images]
        elif images.ndim == 3:
            seq = list(images)
        else:
            raise ValueError("%s: images must be a list of 2-D images or a (N, H, W) stack, got shape %s"
                             % (op, images.shape))
    else:
        try:
            seq = list(images)
        except TypeError:
            raise ValueError("%s: images must be a list of 2-D images" % op) from None
    if not seq:
        raise ValueError("%s: no images" % op)
    out = []
    for i, im in enumerate(seq):
        a = np.asarray(im, dtype=np.float64)
        if a.ndim != 2 or min(a.shape) < 3:
            raise ValueError("%s: image %d must be 2-D and at least 3x3, got shape %s" % (op, i, a.shape))
        if not np.isfinite(a).all():
            raise ValueError("%s: image %d contains NaN or inf" % (op, i))
        out.append(a)
    return out


def feat_image_vector(images=None, features=DEFAULT_FEATURES, data_range=None, unit="DN", roi=None) -> dict:
    """Images -> feature table ``{"matrix" (N, F), "names", "units", ...}``, one row per image.

    The bridge from pictures to the multivariate ops: each image becomes a row of named
    numbers with units, ready for :func:`mv_pca` / :func:`mv_pls` / :func:`rsm_fit`.
    Features (see :data:`FEATURES`): ``mean, std, p01, p50, p99, rms_contrast,
    michelson_contrast, grad_energy, laplacian_var`` need no range;
    ``saturated_fraction, dark_fraction, entropy_bits`` need ``data_range=(lo, hi)`` —
    the range of the *sensor or format* (e.g. (0, 4095) for 12-bit), which the data
    cannot tell: the brightest pixel of a dim image is not the white level. It is
    therefore **required, never inferred**, and pixels outside it are refused (the
    range given is then wrong).

    ``unit`` names the grey-level unit (``"DN"`` by default) used in the unit strings.
    ``roi=(r0, r1, c0, c1)`` restricts every feature to that window (same for all images).
    """
    op = "feat_image_vector"
    if images is None:
        g = np.linspace(0.0, 1.0, 32)
        images = [np.outer(g, g) * s for s in (0.5, 1.0, 1.5)]
    imgs = _images(images, op)
    if isinstance(features, str):
        features = [features]
    feats = list(features)
    if not feats:
        raise ValueError("%s: no features requested" % op)
    unknown = [f for f in feats if f not in FEATURES]
    if unknown:
        raise ValueError("%s: unknown features %s (have %s)" % (op, unknown, sorted(FEATURES)))
    if len(set(feats)) != len(feats):
        raise ValueError("%s: features repeat: %s" % (op, feats))
    need = [f for f in feats if FEATURES[f][0]]
    lo = hi = None
    if need:
        if data_range is None:
            raise ValueError("%s: %s need data_range=(lo, hi) — the sensor/format range is not inferred "
                             "from the data" % (op, need))
        try:
            lo, hi = (float(v) for v in data_range)
        except (TypeError, ValueError):
            raise ValueError("%s: data_range must be (lo, hi)" % op) from None
        if not (math.isfinite(lo) and math.isfinite(hi) and hi > lo):
            raise ValueError("%s: data_range must be finite with hi > lo, got %r" % (op, data_range))
    if roi is not None:
        try:
            r0, r1, c0, c1 = (int(v) for v in roi)
        except (TypeError, ValueError):
            raise ValueError("%s: roi must be (r0, r1, c0, c1)" % op) from None
    rows = []
    for i, a in enumerate(imgs):
        if roi is not None:
            if not (0 <= r0 < r1 <= a.shape[0] and 0 <= c0 < c1 <= a.shape[1]) or (r1 - r0) < 3 or (c1 - c0) < 3:
                raise ValueError("%s: roi %s does not fit image %d of shape %s (min 3x3)" % (op, roi, i, a.shape))
            a = a[r0:r1, c0:c1]
        if lo is not None and (a.min() < lo - 1e-12 * max(1.0, abs(lo)) or a.max() > hi + 1e-12 * max(1.0, abs(hi))):
            raise ValueError("%s: image %d has values [%g, %g] outside data_range (%g, %g) — the range given is wrong"
                             % (op, i, a.min(), a.max(), lo, hi))
        p01, p50, p99 = np.percentile(a, [1, 50, 99])
        mu, sd = float(a.mean()), float(a.std())
        row = []
        for f in feats:
            if f == "mean":
                v = mu
            elif f == "std":
                v = sd
            elif f == "p01":
                v = p01
            elif f == "p50":
                v = p50
            elif f == "p99":
                v = p99
            elif f == "rms_contrast":
                if not mu > 0:
                    raise ValueError("%s: rms_contrast needs a positive mean, image %d has %g" % (op, i, mu))
                v = sd / mu
            elif f == "michelson_contrast":
                if not p99 + p01 > 0:
                    raise ValueError("%s: michelson_contrast needs p99 + p01 > 0 (image %d)" % (op, i))
                v = (p99 - p01) / (p99 + p01)
            elif f == "grad_energy":
                gy = 0.5 * (a[2:, 1:-1] - a[:-2, 1:-1])
                gx = 0.5 * (a[1:-1, 2:] - a[1:-1, :-2])
                v = float(np.mean(gx * gx + gy * gy))
            elif f == "laplacian_var":
                lap = a[2:, 1:-1] + a[:-2, 1:-1] + a[1:-1, 2:] + a[1:-1, :-2] - 4.0 * a[1:-1, 1:-1]
                v = float(lap.var())
            elif f == "saturated_fraction":
                v = float(np.mean(a >= hi))
            elif f == "dark_fraction":
                v = float(np.mean(a <= lo))
            else:                                               # entropy_bits
                h, _e = np.histogram(a, bins=256, range=(lo, hi))
                pr = h[h > 0] / h.sum()
                v = float(-(pr * np.log2(pr)).sum())
            row.append(float(v))
        rows.append(row)
    units = [FEATURES[f][1].replace("{u}", unit) for f in feats]
    return {"matrix": np.asarray(rows), "names": feats, "units": units,
            "data_range": None if lo is None else (lo, hi), "unit": unit, "n_images": len(imgs),
            "roi": None if roi is None else tuple(int(v) for v in roi)}


# --------------------------------------------------------------------------- #
# PCA                                                                         #
# --------------------------------------------------------------------------- #
def mv_pca(X=None, standardize=True, n_components=None, threshold=0.9, n_parallel=200,
           parallel_stat="mean", seed=0) -> dict:
    """Principal components of a table (samples x variables) and how many of them the data support.

    PCA is the SVD of the centred (by default also unit-variance) matrix
    ``Xc = U S V^T``: scores ``U S``, loadings ``V``, eigenvalues ``S^2/(n-1)`` (the
    covariance or correlation eigenvalues — the tests check this identity).

    The number of components is reported three ways, because each fails differently:

    * ``cumulative`` — the smallest count reaching ``threshold`` of the variance (a
      convention, not a test: with many noisy columns it keeps noise);
    * ``parallel`` — Horn's parallel analysis (Horn 1965): keep component i while its
      eigenvalue exceeds the ``parallel_stat`` (``"mean"`` as in Horn, or ``"p95"``) of
      the i-th eigenvalue of ``n_parallel`` normal random tables of the same shape
      treated the same way;
    * ``mdl`` — the MDL criterion of Wax & Kailath 1985 (``mathspectral.n_sources_mdl``,
      reused) on the centred data; it assumes white noise of equal variance in every
      column, which standardising breaks, so it is computed only with
      ``standardize=False`` (homogeneous columns: pixels, features in one unit) and is
      ``None`` otherwise.

    ``n_components`` fixes how many scores/loadings to return (default: the parallel
    count, at least 1). Accepts a matrix or a ``feat_image_vector`` table.
    """
    op = "mv_pca"
    if X is None:
        rng = np.random.default_rng(0)
        t = rng.normal(size=(40, 2))
        X = t @ rng.normal(size=(2, 6)) + 0.1 * rng.normal(size=(40, 6))
    A, names, units = _table_matrix(X, op)
    n, p = A.shape
    if threshold is None or not 0 < float(threshold) <= 1:
        raise ValueError("%s: threshold must be in (0, 1], got %r" % (op, threshold))
    if parallel_stat not in ("mean", "p95"):
        raise ValueError("%s: parallel_stat must be 'mean' or 'p95', got %r" % (op, parallel_stat))
    n_parallel = _doe._int_arg(n_parallel, "n_parallel", op, 0, 10000)
    Xc, mean, sd = _standardise(A, names, op, bool(standardize))
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    # sign convention: the largest |loading| of each component is positive (deterministic output)
    flip = np.sign(Vt[np.arange(Vt.shape[0]), np.argmax(np.abs(Vt), axis=1)])
    flip[flip == 0] = 1.0
    U, Vt = U * flip, Vt * flip[:, None]
    eig = S ** 2 / (n - 1)
    total = float(eig.sum())
    if not total > 0:
        raise ValueError("%s: the table has no variance" % op)
    ratio = eig / total
    cum = np.cumsum(ratio)
    k_cum = int(np.searchsorted(cum, float(threshold) - 1e-12) + 1)
    k_par = None
    ref = None
    if n_parallel:
        rng = np.random.default_rng(seed)
        sims = np.empty((n_parallel, eig.size))
        for b in range(n_parallel):
            R = rng.normal(size=(n, p))
            Rc, _m, _s = _standardise(R, ["r"] * p, op, bool(standardize))
            sims[b] = np.linalg.svd(Rc, compute_uv=False)[: eig.size] ** 2 / (n - 1)
        if not standardize:
            # raw data: compare against noise of the same total variance per column
            sims *= total / p
        ref = sims.mean(axis=0) if parallel_stat == "mean" else np.percentile(sims, 95, axis=0)
        above = eig > ref
        k_par = int(np.argmin(above)) if not above.all() else int(eig.size)
    k_mdl = None
    if p >= 2 and n > p and not standardize:
        import mathspectral                                          # reuse, do not re-implement
        k_mdl = int(mathspectral.n_sources_mdl(Xc.T)["n_sources"])
    if n_components is None:
        k = max(1, k_par if k_par is not None else k_cum)
    else:
        k = _doe._int_arg(n_components, "n_components", op, 1, eig.size)
    scores = U[:, :k] * S[:k]
    return {"scores": scores, "loadings": Vt[:k].T, "eigenvalues": eig, "explained_ratio": ratio,
            "cumulative": cum, "n_components": {"cumulative": k_cum, "parallel": k_par, "mdl": k_mdl},
            "parallel_reference": ref, "n_returned": k, "names": names, "units": units,
            "mean": mean, "scale": sd, "standardized": bool(standardize), "threshold": float(threshold),
            "parallel_stat": parallel_stat}


# --------------------------------------------------------------------------- #
# PLS                                                                         #
# --------------------------------------------------------------------------- #
def _pls_nipals(X: np.ndarray, Y: np.ndarray, A: int, tol: float = 1e-12, max_iter: int = 500):
    """NIPALS PLS2 (Wold et al. 2001, section 3.4) on centred/scaled X (n,p), Y (n,m)."""
    n, p = X.shape
    m = Y.shape[1]
    E, F = X.copy(), Y.copy()
    W, P, Q, T = (np.zeros((p, A)), np.zeros((p, A)), np.zeros((m, A)), np.zeros((n, A)))
    for a in range(A):
        u = F[:, [int(np.argmax((F ** 2).sum(axis=0)))]]
        t_old = None
        for _ in range(max_iter):
            w = E.T @ u
            nw = np.linalg.norm(w)
            if not nw > 0:
                raise ValueError("mv_pls: X has no variance left at component %d" % (a + 1))
            w /= nw
            t = E @ w
            c = F.T @ t / (t.T @ t).item()
            u = F @ c / (c.T @ c).item()
            if t_old is not None and np.linalg.norm(t - t_old) <= tol * np.linalg.norm(t):
                break
            t_old = t
            if m == 1:
                break
        pl = E.T @ t / (t.T @ t).item()
        E = E - t @ pl.T
        F = F - t @ c.T
        W[:, a], P[:, a], Q[:, a], T[:, a] = w[:, 0], pl[:, 0], c[:, 0], t[:, 0]
    B = W @ np.linalg.solve(P.T @ W, Q.T)
    return {"W": W, "P": P, "Q": Q, "T": T, "B": B}


def _pls_simpls(X: np.ndarray, Y: np.ndarray, A: int):
    """SIMPLS (de Jong 1993) on centred/scaled X, Y: the second implementation."""
    n, p = X.shape
    m = Y.shape[1]
    S = X.T @ Y
    R, T, P, Q, V = (np.zeros((p, A)), np.zeros((n, A)), np.zeros((p, A)), np.zeros((m, A)), np.zeros((p, A)))
    for a in range(A):
        if m == 1:
            r = S[:, 0].copy()
        else:
            uu, _ss, _vv = np.linalg.svd(S, full_matrices=False)
            r = uu[:, 0] * np.sign(uu[np.argmax(np.abs(uu[:, 0])), 0])
        t = X @ r
        t = t - t.mean()
        nt = np.linalg.norm(t)
        if not nt > 0:
            raise ValueError("mv_pls: X has no variance left at component %d" % (a + 1))
        t /= nt
        r /= nt
        pl = X.T @ t
        q = Y.T @ t
        v = pl.copy()
        if a > 0:
            v = v - V[:, :a] @ (V[:, :a].T @ pl)
        v /= np.linalg.norm(v)
        S = S - np.outer(v, v @ S)
        R[:, a], T[:, a], P[:, a], Q[:, a], V[:, a] = r, t, pl, q, v
    B = R @ Q.T
    return {"W": R, "P": P, "Q": Q, "T": T, "B": B}


def _vip(W: np.ndarray, T: np.ndarray, Q: np.ndarray) -> np.ndarray:
    """VIP_j = sqrt(p * sum_a SS_a (w_ja/||w_a||)^2 / sum_a SS_a), SS_a = ||q_a||^2 t_a^T t_a."""
    p = W.shape[0]
    ss = (Q ** 2).sum(axis=0) * (T ** 2).sum(axis=0)
    wn = W / np.linalg.norm(W, axis=0, keepdims=True)
    return np.sqrt(p * (wn ** 2 @ ss) / ss.sum())


def mv_pls(X=None, Y=None, n_components=None, max_components=10, cv=7, method="nipals",
           standardize=True) -> dict:
    """Partial least squares regression of Y on X with cross-validated Q^2, the Q^2 rule and VIP.

    PLS finds directions in X that both vary and predict Y — the tool for many
    correlated predictors and few runs (image features -> process settings, or the
    reverse). ``method="nipals"`` (default, Wold, Sjöström & Eriksson 2001) or
    ``"simpls"`` (de Jong 1993; identical to NIPALS for a single response — a test pins
    it). X and Y are centred and, by default, scaled to unit variance.

    Q^2 is computed by ``cv``-fold cross-validation with interleaved folds (run i in fold
    i mod cv, as in SIMCA's default of 7 groups): ``Q^2_a = 1 - PRESS_a / SS_{a-1}`` per
    component (``SS_0`` = total sum of squares of Y, ``SS_{a-1}`` the residual sum of
    squares with a-1 components), cumulative ``Q^2 = 1 - PRESS_A / SS_0``.
    ``n_components=None`` keeps adding components while ``Q^2_a >= 0.0975``
    (= 1 - 0.95^2; Wold et al. 2001) up to ``max_components``; if not even the first
    passes, one component is fitted and ``significant`` is False — the data then do not
    support a predictive model, and the coefficients should not be used.

    VIP (variable importance in projection) ranks X columns; the conventional threshold
    is VIP > 1. ``coef`` / ``intercept`` predict Y in its original units from X in its
    original units.
    """
    op = "mv_pls"
    if X is None or Y is None:
        rng = np.random.default_rng(0)
        X = rng.normal(size=(30, 5))
        Y = X @ np.array([1.0, -0.5, 0.0, 0.0, 0.2]) + 0.05 * rng.normal(size=30)
    Xa, xnames, xunits = _table_matrix(X, op, "X", min_rows=4)
    Ya, ynames, yunits = _table_matrix(Y, op, "Y", min_rows=4)
    n = Xa.shape[0]
    if Ya.shape[0] != n:
        raise ValueError("%s: X has %d rows but Y has %d" % (op, n, Ya.shape[0]))
    if method not in ("nipals", "simpls"):
        raise ValueError("%s: method must be 'nipals' or 'simpls', got %r" % (op, method))
    fit = _pls_nipals if method == "nipals" else _pls_simpls
    max_components = _doe._int_arg(max_components, "max_components", op, 1, 1000)
    amax = min(max_components, Xa.shape[1], n - 2)
    if amax < 1:
        raise ValueError("%s: too few runs (%d) for a PLS component" % (op, n))
    cv = _doe._int_arg(cv, "cv", op, 2, n)
    Xs, xm, xs = _standardise(Xa, xnames, op, bool(standardize))
    Ys, ym, ys = _standardise(Ya, ynames, op, bool(standardize))
    folds = np.arange(n) % cv
    # cross-validated PRESS for 1..amax components
    press = np.zeros(amax)
    for f in range(cv):
        tr, te = folds != f, folds == f
        if tr.sum() < 3:
            raise ValueError("%s: cv=%d leaves fewer than 3 training runs" % (op, cv))
        Xt, xmt, xst = _standardise(Xa[tr], xnames, op, bool(standardize))
        Yt, ymt, yst = _standardise(Ya[tr], ynames, op, bool(standardize))
        a_f = min(amax, Xt.shape[0] - 2, Xt.shape[1])
        model = fit(Xt, Yt, a_f)
        Xte = (Xa[te] - xmt) / xst
        for a in range(1, amax + 1):
            aa = min(a, a_f)
            Ba = model["W"][:, :aa] @ np.linalg.solve(model["P"][:, :aa].T @ model["W"][:, :aa],
                                                      model["Q"][:, :aa].T) if method == "nipals" \
                else model["W"][:, :aa] @ model["Q"][:, :aa].T
            pred = (Xte @ Ba) * yst + ymt
            press[a - 1] += float((((Ya[te] - pred) / ys) ** 2).sum())
    full = fit(Xs, Ys, amax)
    ss0 = float((Ys ** 2).sum())
    rss = [ss0]
    for a in range(1, amax + 1):
        Ba = full["W"][:, :a] @ np.linalg.solve(full["P"][:, :a].T @ full["W"][:, :a], full["Q"][:, :a].T) \
            if method == "nipals" else full["W"][:, :a] @ full["Q"][:, :a].T
        rss.append(float(((Ys - Xs @ Ba) ** 2).sum()))
    q2_comp = np.array([1.0 - press[a] / rss[a] for a in range(amax)])
    q2_cum = 1.0 - press / ss0
    if n_components is None:
        A = 0
        while A < amax and q2_comp[A] >= Q2_LIMIT:
            A += 1
        significant = A > 0
        A = max(A, 1)
    else:
        A = _doe._int_arg(n_components, "n_components", op, 1, amax)
        significant = bool(q2_comp[0] >= Q2_LIMIT)
    W, P, Q, T = full["W"][:, :A], full["P"][:, :A], full["Q"][:, :A], full["T"][:, :A]
    Bs = W @ np.linalg.solve(P.T @ W, Q.T) if method == "nipals" else W @ Q.T
    coef = Bs / xs[:, None] * ys[None, :]
    intercept = ym - xm @ coef
    if method == "simpls":
        # VIP is defined on the NIPALS weights w_a, which are orthonormal and span the same nested
        # subspaces as SIMPLS's r_1..r_a: orthonormalise R in order (QR) to get them back.
        Wq, Rr = np.linalg.qr(W)
        Wv = Wq * np.sign(np.diag(Rr))[None, :]
    else:
        Wv = W
    vip = _vip(Wv, T, Q)
    pred = Xa @ coef + intercept
    r2y = 1.0 - float((((Ya - pred) / ys) ** 2).sum()) / ss0
    r2x = 1.0 - float(((Xs - T @ P.T) ** 2).sum()) / float((Xs ** 2).sum()) if method == "nipals" else \
        1.0 - float(((Xs - T @ np.linalg.lstsq(T, Xs, rcond=None)[0]) ** 2).sum()) / float((Xs ** 2).sum())
    return {"coef": coef, "intercept": intercept, "n_components": A, "significant": significant,
            "q2_per_component": q2_comp, "q2_cumulative": q2_cum, "q2": float(q2_cum[A - 1]),
            "r2y": r2y, "r2x": r2x, "vip": vip, "x_names": xnames, "y_names": ynames,
            "x_units": xunits, "y_units": yunits, "weights": W, "x_loadings": P, "y_loadings": Q,
            "scores": T, "method": method, "cv": cv, "q2_limit": Q2_LIMIT, "standardized": bool(standardize),
            "fitted": pred}


# --------------------------------------------------------------------------- #
# response surface                                                            #
# --------------------------------------------------------------------------- #
def _terms(k: int, model: str, names):
    terms = [("1", ())]
    terms += [(names[i], (i,)) for i in range(k)]
    if model in ("interaction", "quadratic"):
        terms += [("%s*%s" % (names[i], names[j]), (i, j)) for i, j in itertools.combinations(range(k), 2)]
    if model == "quadratic":
        terms += [("%s^2" % names[i], (i, i)) for i in range(k)]
    return terms


def _model_matrix(C: np.ndarray, terms) -> np.ndarray:
    cols = []
    for _name, idx in terms:
        c = np.ones(C.shape[0])
        for i in idx:
            c = c * C[:, i]
        cols.append(c)
    return np.stack(cols, axis=1)


def _aliased_terms(M: np.ndarray, terms) -> list:
    """Which model terms the design cannot tell apart, as readable relations (empty if full rank).

    Terms are taken in model order; a term whose column lies in the span of the earlier
    independent columns is written as that combination (``x1^2 = 1`` on a two-level plan,
    ``x1*x2 = x4`` on a resolution III fraction).
    """
    basis, out = [], []
    scale = max(1.0, float(np.abs(M).max()))
    for j in range(M.shape[1]):
        col = M[:, j]
        if basis:
            B = M[:, basis]
            coef = np.linalg.lstsq(B, col, rcond=None)[0]
            if np.linalg.norm(B @ coef - col) <= 1e-9 * scale * np.sqrt(M.shape[0]):
                parts = ["%s%s" % ("" if abs(c - 1) < 1e-9 else "-" if abs(c + 1) < 1e-9 else "%.3g*" % c,
                                   terms[basis[i]][0]) for i, c in enumerate(coef) if abs(c) > 1e-9]
                out.append("%s = %s" % (terms[j][0], " + ".join(parts) if parts else "0"))
                continue
        elif np.linalg.norm(col) <= 1e-12:
            out.append("%s = 0" % terms[j][0])
            continue
        basis.append(j)
    return out


def rsm_fit(design=None, y=None, model="quadratic") -> dict:
    """Fit a response surface on a ``design`` (coded units): ANOVA, lack of fit, stationary point.

    ``model``: ``"linear"`` (b0 + sum b_i x_i), ``"interaction"`` (+ b_ij x_i x_j) or
    ``"quadratic"`` (+ b_ii x_i^2) — fitted by least squares on the **coded** matrix of
    the design (so coefficients are comparable across factors).

    **Refuses a model the plan cannot support**: if the model matrix is rank-deficient
    (a two-level plan cannot see x^2 — every x_i^2 equals the intercept; a resolution III
    fraction cannot separate a main effect from a two-factor interaction) the op raises
    ``ValueError`` naming the aliased terms, instead of returning one of infinitely many
    least-squares solutions. It also needs more runs than terms (a residual to judge with).

    Returns coefficients with standard errors and t, the ANOVA (model / residual and, when
    the plan has replicated points, lack of fit vs pure error with its F test), R^2,
    adjusted R^2, predicted R^2 (from PRESS). For the quadratic model, the stationary
    point x_s = -B^{-1} b / 2 (B symmetric with b_ii on the diagonal and b_ij/2 off it) in
    coded and natural units, the predicted response there, the eigenvalues of B
    (canonical analysis: all negative = maximum, all positive = minimum, mixed = saddle,
    any near zero = ridge) and whether x_s lies inside the explored region.
    """
    op = "rsm_fit"
    if design is None or y is None:
        design = _doe.doe_central_composite(2, center=3)
        c = design["coded"]
        y = 10 - (c[:, 0] - 0.3) ** 2 - 2 * (c[:, 1] + 0.2) ** 2 + 0.01 * np.cos(np.arange(c.shape[0]))
    C = _doe._design_coded(design, op)
    try:
        yv = np.asarray(y, dtype=np.float64).ravel()
    except (TypeError, ValueError):
        raise ValueError("%s: y must be numeric" % op) from None
    n, k = C.shape
    if yv.size != n:
        raise ValueError("%s: design has %d runs but y has %d values" % (op, n, yv.size))
    if not np.isfinite(yv).all():
        raise ValueError("%s: y contains NaN or inf" % op)
    if model not in ("linear", "interaction", "quadratic"):
        raise ValueError("%s: model must be 'linear', 'interaction' or 'quadratic', got %r" % (op, model))
    names = list(design["factors"])
    terms = _terms(k, model, names)
    M = _model_matrix(C, terms)
    pn = M.shape[1]
    rank = np.linalg.matrix_rank(M)
    if rank < pn:
        raise ValueError("%s: the design cannot support the %s model — aliased terms: %s "
                         "(use a design with more levels / higher resolution, or a smaller model)"
                         % (op, model, "; ".join(_aliased_terms(M, terms))))
    if n <= pn:
        raise ValueError("%s: %d runs for %d terms leaves no residual to judge the fit with" % (op, n, pn))
    st = _scipy_stats()
    XtX_inv = np.linalg.inv(M.T @ M)
    b = XtX_inv @ M.T @ yv
    fitted = M @ b
    resid = yv - fitted
    ss_res = float(resid @ resid)
    ss_tot = float(((yv - yv.mean()) ** 2).sum())
    df_res = n - pn
    df_mod = pn - 1
    ss_mod = ss_tot - ss_res
    mse = ss_res / df_res
    se = np.sqrt(np.maximum(np.diag(XtX_inv) * mse, 0.0))
    with np.errstate(divide="ignore", invalid="ignore"):
        tval = np.where(se > 0, b / se, np.inf)
    pval = 2 * st.t.sf(np.abs(tval), df_res)
    f_mod = (ss_mod / df_mod) / mse if df_mod > 0 and mse > 0 else float("inf")
    p_mod = float(st.f.sf(f_mod, df_mod, df_res)) if df_mod > 0 and mse > 0 else 0.0
    # pure error from replicated points
    keys = [tuple(np.round(r, 9)) for r in C]
    groups = {}
    for i, key in enumerate(keys):
        groups.setdefault(key, []).append(i)
    ss_pe = sum(float(((yv[g] - yv[g].mean()) ** 2).sum()) for g in groups.values())
    df_pe = sum(len(g) - 1 for g in groups.values())
    df_lof = len(groups) - pn
    lof = {"testable": False, "reason": ""}
    if df_pe == 0:
        lof["reason"] = "no replicated points — lack of fit cannot be separated from noise"
    elif df_lof <= 0:
        lof["reason"] = "as many distinct points as terms — the model interpolates them"
    else:
        ss_lof = ss_res - ss_pe
        if ss_pe <= 0:
            lof.update(testable=True, ss_lof=ss_lof, df_lof=df_lof, ss_pe=ss_pe, df_pe=df_pe,
                       f=float("inf") if ss_lof > 1e-12 * max(1.0, ss_tot) else 0.0,
                       p=0.0 if ss_lof > 1e-12 * max(1.0, ss_tot) else 1.0)
        else:
            f_lof = (ss_lof / df_lof) / (ss_pe / df_pe)
            lof.update(testable=True, ss_lof=ss_lof, df_lof=df_lof, ss_pe=ss_pe, df_pe=df_pe,
                       f=float(f_lof), p=float(st.f.sf(f_lof, df_lof, df_pe)))
    h = np.clip(np.sum((M @ XtX_inv) * M, axis=1), 0.0, 1.0 - 1e-12)
    press = float(((resid / (1.0 - h)) ** 2).sum())
    out = {"model": model, "terms": [t for t, _ in terms], "coef": b, "se": se, "t": tval, "p": pval,
           "anova": {"ss_model": ss_mod, "df_model": df_mod, "ss_resid": ss_res, "df_resid": df_res,
                     "ss_total": ss_tot, "f_model": float(f_mod), "p_model": p_mod},
           "lack_of_fit": lof, "r2": 1 - ss_res / ss_tot if ss_tot > 0 else 1.0,
           "r2_adj": 1 - (ss_res / df_res) / (ss_tot / (n - 1)) if ss_tot > 0 else 1.0,
           "r2_pred": 1 - press / ss_tot if ss_tot > 0 else 1.0, "press": press,
           "fitted": fitted, "residuals": resid, "factors": names}
    if model == "quadratic":
        bl = b[1:1 + k]
        B = np.zeros((k, k))
        for (name, idx), coef in zip(terms, b):
            if len(idx) == 2:
                i, j = idx
                if i == j:
                    B[i, i] = coef
                else:
                    B[i, j] = B[j, i] = coef / 2.0
        lam, vec = np.linalg.eigh(B)
        scale = max(1e-12, float(np.abs(lam).max()))
        if np.all(np.abs(lam) < 1e-9 * max(1.0, float(np.abs(bl).max()))):
            kind = "none (no curvature)"
            xs = None
        else:
            kind = ("maximum" if np.all(lam < 0) else "minimum" if np.all(lam > 0) else "saddle")
            if np.any(np.abs(lam) < 0.05 * scale):
                kind += " (ridge: an eigenvalue is near zero, the optimum is a line/plane)"
            try:
                xs = -0.5 * np.linalg.solve(B, bl)
            except np.linalg.LinAlgError:
                xs = None
        radius = float(np.abs(C).max())
        out["canonical"] = {"B": B, "eigenvalues": lam, "eigenvectors": vec, "kind": kind}
        if xs is not None:
            ys_ = float(b[0] + bl @ xs + xs @ B @ xs)
            out["stationary"] = {"coded": xs, "natural": _doe.doe_decode(design, xs)[0], "y": ys_,
                                 "inside_region": bool(np.abs(xs).max() <= radius + 1e-9),
                                 "region_radius": radius}
        else:
            out["stationary"] = None
    return out


def _scipy_stats():
    from scipy import stats as _st                            # noqa: PLC0415 — lazy, as in spc.py
    return _st


# --------------------------------------------------------------------------- #
# main effects (Taguchi response table) + SN ratios                           #
# --------------------------------------------------------------------------- #
def doe_main_effects(design=None, y=None, goal="larger") -> dict:
    """Level means per factor — the response table of a designed experiment — with dispersion and SN.

    ``y`` is (n,) or (n, r) with r repeated measurements (or noise-array conditions) per
    run. For each factor and level: the mean of y (location), the mean of log s over the
    runs at that level (dispersion, needs r >= 2), the main-effect range (max - min of the
    level means) and its share of the total sum of squares.

    SN ratios are computed per run (Taguchi): larger-the-better
    ``-10 log10(mean(1/y^2))`` (the same formula as ``spc.spc_mt_sn_ratio``, reused),
    smaller-the-better ``-10 log10(mean(y^2))``, nominal-the-best ``10 log10(ybar^2/s^2)``,
    and their level means are reported in ``sn``. **They are not the basis of the
    recommended levels**: an SN ratio mixes location and dispersion in one number, and a
    level can raise it by lowering the mean (Box 1988; Nair 1992). ``best_levels`` chooses
    from the location table by ``goal`` (``"larger"``, ``"smaller"``, or ``"nominal"`` —
    which picks the levels of smallest dispersion and leaves the mean to an adjustment
    factor), and ``sn_agrees`` says where the SN table would have chosen differently.
    """
    op = "doe_main_effects"
    if design is None or y is None:
        design = _doe.doe_orthogonal_array("L9", 4)
        c = design["coded"]
        y = np.stack([10 + 2 * c[:, 0] - c[:, 1] + 0.5 * c[:, 2] + 0.1 * s for s in (-1, 0, 1)], axis=1)
    C = _doe._design_coded(design, op)
    try:
        Y = np.asarray(y, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("%s: y must be numeric" % op) from None
    if Y.ndim == 1:
        Y = Y[:, None]
    n, k = C.shape
    if Y.ndim != 2 or Y.shape[0] != n:
        raise ValueError("%s: y must be (n,) or (n, r) with n=%d runs, got shape %s" % (op, n, Y.shape))
    if not np.isfinite(Y).all():
        raise ValueError("%s: y contains NaN or inf" % op)
    if goal not in ("larger", "smaller", "nominal"):
        raise ValueError("%s: goal must be 'larger', 'smaller' or 'nominal', got %r" % (op, goal))
    r = Y.shape[1]
    if goal == "nominal" and r < 2:
        raise ValueError("%s: goal='nominal' needs r >= 2 repeats per run (it judges dispersion)" % op)
    ybar = Y.mean(axis=1)
    s = Y.std(axis=1, ddof=1) if r >= 2 else None
    import spc                                                     # reuse the larger-the-better SN
    sn_l = np.full(n, np.nan)
    if (Y > 0).all():
        sn_l = np.array([spc.spc_mt_sn_ratio(row)["sn_ratio_db"] for row in Y])
    sn_s = -10.0 * np.log10(np.maximum((Y ** 2).mean(axis=1), 1e-300))
    sn_n = None
    if s is not None:
        with np.errstate(divide="ignore", invalid="ignore"):
            sn_n = np.where(s > 0, 10.0 * np.log10(ybar ** 2 / np.maximum(s, 1e-300) ** 2), np.inf)
    sn_run = {"larger": sn_l, "smaller": sn_s, "nominal": sn_n}[goal]
    logs = np.log(np.maximum(s, 1e-300)) if s is not None else None
    grand = float(Y.mean())
    ss_tot = float(((Y - grand) ** 2).sum())
    table, best, sn_best, sn_tab = {}, {}, {}, {}
    for j, name in enumerate(design["factors"]):
        lv = np.unique(np.round(C[:, j], 9))
        means = np.array([Y[np.isclose(C[:, j], v)].mean() for v in lv])
        counts = np.array([int(np.isclose(C[:, j], v).sum()) for v in lv])
        ss = float(sum(cnt * r * (mu - grand) ** 2 for cnt, mu in zip(counts, means)))
        disp = None if logs is None else np.array([logs[np.isclose(C[:, j], v)].mean() for v in lv])
        snm = None if sn_run is None or not np.isfinite(sn_run).all() else \
            np.array([sn_run[np.isclose(C[:, j], v)].mean() for v in lv])
        nat = _doe.doe_decode(design, np.tile(lv[:, None], (1, k)) * np.eye(k)[j] +
                              np.zeros((lv.size, k)))[:, j]
        table[name] = {"levels_coded": lv, "levels_natural": nat, "mean": means, "log_s": disp,
                       "range": float(means.max() - means.min()), "ss": ss,
                       "share": ss / ss_tot if ss_tot > 0 else 0.0, "n_runs": counts}
        sn_tab[name] = snm
        if goal == "larger":
            best[name] = float(lv[int(np.argmax(means))])
        elif goal == "smaller":
            best[name] = float(lv[int(np.argmin(means))])
        else:
            best[name] = float(lv[int(np.argmin(disp))])
        if snm is not None:
            sn_best[name] = float(lv[int(np.argmax(snm))])
    agree = {nm: (sn_best.get(nm) == best[nm]) if nm in sn_best else None for nm in best}
    return {"table": table, "best_levels": best, "goal": goal, "sn": sn_tab, "sn_best_levels": sn_best,
            "sn_agrees": agree, "sn_per_run": sn_run, "grand_mean": grand, "repeats": r,
            "decision_basis": "location (level means) and dispersion (mean log s) read separately; "
                              "SN ratios are reported for comparison only (Box 1988, Technometrics 30(1):1)"}
