# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""simcalcheck — after a sim-to-real fit: what is determined, how sure, does it hold out, and what is the model missing.

The checking half of the ``simcal`` family (design C5). Every op takes a ``calresult`` from
``simcal.simcal_fit`` and returns it with one section filled — and **withdraws point
estimates** that the check does not support (the knob moves to ``undetermined`` with the
reason; ``status`` becomes ``partial`` or ``refused``). Nothing is returned silently.

Ops
---
``simcal_identifiability``  Fisher information J^T W J (the Cramér-Rao bound of Gaussian noise
                            with known variance — the definition of
                            ``mathestimation.crlb_gaussian``, which the tests cross-check),
                            its condition number (> 1e6 is a warning), the correlation matrix,
                            the collinearity index (``sensitivity.mv_confounding``) and the
                            **profile likelihood** of every knob (Raue et al. 2009): re-fit the
                            others with the knob held, and find where chi^2 rises by
                            chi^2_1(0.95) = 3.84 on each side. Two-sided: determined (with a
                            likelihood-ratio interval). One side only: only an upper (lower)
                            limit — no point estimate. Neither: undetermined. The bracketing +
                            bisection follows ``pod.pod_hitmiss_fit``'s profile bound.
``simcal_uncertainty``      Laplace (inverse Fisher at the estimate; intervals mapped through the
                            knob scale, so a log knob gets an asymmetric interval) or parametric
                            bootstrap (Efron 1979: refit to the prediction plus noise drawn from
                            the noise model).
``simcal_validate``         the over-fitting gates of the design (§6), any one rejects: holdout
                            error not below the initial knobs; holdout / train > 1 + tau (tau =
                            bootstrap 95 % of the train error's relative spread); not better than
                            a gain-and-offset-only fit of the initial simulation; an estimate
                            outside its range, beyond 3 sd of its prior or pinned to the edge;
                            more free knobs than output directions above noise. Splits follow
                            ``robust.py``: TRAIN (fit) / OBSERVED holdout (may be looked at many
                            times) / LOCKED (scored once — a second LOCKED call is refused).
``simcal_discrepancy``      residual PCA of the noise-normalised residuals
                            (``sensitivity.mv_residual_pca``) against the Tracy-Widom 99 % point of
                            the largest singular value of white noise (Johnstone 2001) — a
                            structural residual means the model misses something and every
                            uncertainty above is optimistic (Kennedy & O'Hagan 2001; Brynjarsdóttir
                            & O'Hagan 2014: a calibrated knob may be absorbing the discrepancy).
``simcal_report``           one table: each knob's value, unit, interval and class, the gates and
                            the reasons, as rows and as text.

Provenance: Raue et al. 2009, Bioinformatics 25(15):1923 (profile likelihood, chi^2_1 threshold);
Fisher 1925 / Cramér 1946 / Rao 1945 (information bound); Efron 1979, Ann. Stat. 7(1):1;
MacKay 1992 (Laplace); Johnstone 2001, Ann. Stat. 29(2):295 (Tracy-Widom centring and scaling of
the largest eigenvalue of a white Wishart matrix); Marchenko & Pastur 1967; Kennedy & O'Hagan
2001; Brynjarsdóttir & O'Hagan 2014, Inverse Problems 30:114007.
"""
from __future__ import annotations

import copy
import math

import numpy as np

import doe as _doe
import simcal as _sc
from metriccontract import MetricContractError

__all__ = ["simcal_identifiability", "simcal_uncertainty", "simcal_validate", "simcal_discrepancy",
           "simcal_report"]

#: Tracy-Widom (beta = 1) quantiles used for the noise edge of the residual PCA. Values as tabulated
#: in the literature (90 / 95 / 99 %); checked here empirically: 1000 white n x p matrices exceed the
#: 99 % edge in 0.7-1.4 % of cases for (n, p) in {(3, 4096), (3, 1024), (64, 64), (24, 24), (4, 576)}.
TW1_QUANTILES = {0.90: 0.4501, 0.95: 0.9793, 0.99: 2.0234}
COND_WARN = 1e6


# --------------------------------------------------------------------------- #
# helpers                                                                     #
# --------------------------------------------------------------------------- #
def _check_result(res, op):
    if not isinstance(res, dict) or res.get("sort") != "calresult":
        raise ValueError("%s: expected a calresult (dict with sort='calresult' from simcal_fit), got %s"
                         % (op, type(res).__name__))
    for key in ("model", "diagnostics", "theta_hat", "undetermined", "fixed"):
        if key not in res:
            raise ValueError("%s: calresult is missing %r" % (op, key))
    _sc._check_model(res["model"], op, need_observed=True, need_noise=True)
    return res


def _problem(res, model=None, extra_fix=None):
    m = res["model"] if model is None else model
    fix = dict(res["fixed"])
    fix.update(extra_fix or {})
    P = _sc._Problem(m, fix=fix)
    end = res["diagnostics"]["endpoint_not_an_estimate"]
    u = np.array([_sc._to_u(end[k["name"]], k) for k in P.free])
    return P, u


def _withdraw(res, name, reason, rule):
    """Move a knob's point estimate out of theta_hat and record why (never silent)."""
    res["theta_hat"].pop(name, None)
    res["undetermined"].setdefault(name, reason)
    res["refusals"].append({"rule": rule, "knobs": [name], "reason": reason})


def _restatus(res):
    if not res["undetermined"]:
        res["status"] = "accepted"
    elif res["theta_hat"] or res["determined_combos"]:
        res["status"] = "partial"
    else:
        res["status"] = "refused"
    return res


def _default_result():
    return _sc.simcal_fit(_sc.simcal_model())


def _chi_red(P, u, sw=None):
    sims, th = P.mu(u)
    w = P.weights(sims, th) if sw is None else sw
    r = (P.y - P.flat(sims)) * w
    return float(r @ r) / max(1, r.size - len(P.free)), r


# --------------------------------------------------------------------------- #
# simcal_identifiability                                                      #
# --------------------------------------------------------------------------- #
def _profile_side(res, k, u_hat_j, side, chi_min, sw, sigma_u, P_full, u_full, j, crit, trace):
    """Walk one side of knob k's profile (others re-fitted); the u where chi^2 has risen by crit, or None."""
    others = [i for i in range(len(P_full.free)) if i != j]

    def prof(t):
        th_t = _sc._from_u(float(t), k)
        Pj, _ = _problem(res, extra_fix={k["name"]: th_t})
        start = u_full[others] if prof.warm is None else prof.warm
        run = _sc._lm(Pj, start, sw_fixed=sw, max_iter=60)
        prof.warm = run["u"]
        trace.append((float(th_t), float(run["chi2"] - chi_min)))
        return run["chi2"] - chi_min

    prof.warm = None
    step = max(float(sigma_u), 1e-3) if math.isfinite(sigma_u) else 0.02
    lo_t, hi_t, reached = u_hat_j, None, False
    for kk in range(16):
        t = u_hat_j + side * step * (2.0 ** kk)
        if t <= 0.0 or t >= 1.0:
            t = 0.0 if t <= 0.0 else 1.0
            reached = True
        d = prof(t)
        if d > crit:
            hi_t = t
            break
        lo_t = t
        if reached:
            return None
    if hi_t is None:
        return None
    for _ in range(30):                                               # bisection (pod_hitmiss_fit's bound search)
        mid = 0.5 * (lo_t + hi_t)
        d = prof(mid)
        if d > crit:
            hi_t = mid
        else:
            lo_t = mid
        if abs(hi_t - lo_t) < 1e-5:
            break
    return 0.5 * (lo_t + hi_t)


def simcal_identifiability(result=None, at=None, profile=True, level=0.95, threshold=None) -> dict:
    """Fisher information, Cramér-Rao bound, correlations, collinearity and profile likelihood of every fitted knob.

    Computed at the fit's end point (or at ``at`` = ``{knob: value}``, e.g. the true values of
    a synthetic study, without touching the estimates). Returned in ``identifiability``:
    ``fisher`` (natural units), ``crlb`` (sqrt of the diagonal of its inverse — the smallest
    standard deviation any unbiased estimator can have under the noise model), ``condition``
    (of the Fisher matrix on the unit-scaled knobs; > 1e6 adds a warning), ``correlation``,
    ``gamma_full`` and ``confounded_groups`` (``sensitivity.mv_confounding``), and with
    ``profile=True`` a ``profile`` per knob: the likelihood-ratio interval where chi^2 stays
    within chi^2_1(``level``) of its minimum (3.84 at 95 %), each other knob re-fitted at every
    step (Raue et al. 2009). Knobs whose profile does not rise above the threshold on both sides
    inside the range lose their point estimate: ``upper_only`` / ``lower_only`` (only one limit
    exists) or ``undetermined``. Each profile keeps its ``trace`` (knob value, chi^2 rise) of the
    evaluated points. No noise model: refused.
    """
    op = "simcal_identifiability"
    res = _default_result() if result is None else result
    _check_result(res, op)
    lv = _sc._num(level, "level", op, 0.5, 0.999)
    from scipy.stats import chi2
    crit = float(chi2.ppf(lv, 1))
    thr = float(res["fit"]["threshold"]) if threshold is None else _sc._num(threshold, "threshold", op, 1.0, lo_open=True)
    res = copy.deepcopy(res)
    P, u = _problem(res)
    if at is not None:
        vals = _sc._theta_arg(res["model"], at, op)
        u = np.array([_sc._to_u(vals[k["name"]], k) for k in P.free])
        if (u < 0).any() or (u > 1).any():
            raise ValueError("%s: 'at' lies outside the knob ranges" % op)
    sims, th = P.mu(u)
    sw = P.weights(sims, th)
    J_u = P.jac(u, sw)
    names = [k["name"] for k in P.free]
    dudt = np.array([_sc._du_dtheta(th[k["name"]], k) for k in P.free])
    J_t = J_u * dudt[None, :]
    F = J_t.T @ J_t
    F_u = J_u.T @ J_u
    ev = np.linalg.eigvalsh(F_u)
    cond = float(ev.max() / ev.min()) if ev.min() > 0 else None
    warnings = []
    if cond is None or cond > COND_WARN:
        warnings.append("Fisher information is ill-conditioned (condition %s > %g): some direction in knob space "
                        "is barely seen by the data" % ("inf" if cond is None else "%.3g" % cond, COND_WARN))
    try:
        cov = np.linalg.inv(F)
        crlb = {n: float(math.sqrt(cov[i, i])) if cov[i, i] > 0 else None for i, n in enumerate(names)}
        sd = np.sqrt(np.abs(np.diag(cov)))
        corr = cov / np.outer(sd, sd)
    except np.linalg.LinAlgError:
        crlb = {n: None for n in names}
        corr = None
    import sensitivity
    conf = None
    if len(names) >= 2:
        J_phi = J_u / np.array([1.0 / _sc._du_dphi(k) for k in P.free])[None, :]
        live = [i for i in range(len(names)) if np.linalg.norm(J_phi[:, i]) > 0]
        if len(live) >= 2:
            c = sensitivity.mv_confounding(J_phi[:, live], names=[names[i] for i in live], threshold=thr)
            conf = {"gamma_full": float(c["gamma_full"]) if math.isfinite(c["gamma_full"]) else None,
                    "confounded_pairs": [(list(s), float(g) if math.isfinite(g) else None)
                                         for s, g in c["confounded_pairs"]],
                    "confounded_groups": [{"parameters": g["parameters"], "determined": g["determined"],
                                           "undetermined": g["undetermined"]} for g in c["confounded_groups"]]}
    prof = {}
    if profile and at is None:
        chi_min = float(((P.y - P.flat(sims)) * sw) @ ((P.y - P.flat(sims)) * sw))
        su = {}
        try:
            cu = np.linalg.inv(F_u)
            su = {n: math.sqrt(cu[i, i]) if cu[i, i] > 0 else math.inf for i, n in enumerate(names)}
        except np.linalg.LinAlgError:
            su = {n: math.inf for n in names}
        for j, k in enumerate(P.free):
            trace = [(float(th[k["name"]]), 0.0)]
            if len(P.free) == 1:
                ends = [_profile_one_knob(P, k, u[j], side, chi_min, sw, su[k["name"]], crit, trace)
                        for side in (-1.0, 1.0)]
            else:
                ends = [_profile_side(res, k, float(u[j]), side, chi_min, sw, su[k["name"]], P, u, j, crit, trace)
                        for side in (-1.0, 1.0)]
            lo_u, hi_u = ends
            if lo_u is not None and hi_u is not None:
                cls = "determined"
            elif lo_u is None and hi_u is None:
                cls = "undetermined"
            elif lo_u is None:
                cls = "upper_only"
            else:
                cls = "lower_only"
            prof[k["name"]] = {"class": cls, "lower": None if lo_u is None else float(_sc._from_u(lo_u, k)),
                               "upper": None if hi_u is None else float(_sc._from_u(hi_u, k)),
                               "threshold": crit, "level": lv,
                               "trace": sorted(trace)}
            if cls != "determined" and k["name"] in res["theta_hat"]:
                what = {"upper_only": "only an upper limit (%s)" % prof[k["name"]]["upper"],
                        "lower_only": "only a lower limit (%s)" % prof[k["name"]]["lower"],
                        "undetermined": "no limit on either side"}[cls]
                _withdraw(res, k["name"], "profile: chi^2 does not rise by %.2f on both sides of %s inside its range — "
                          "%s; no point estimate" % (crit, k["name"], what), "profile")
    res["identifiability"] = {"at": "endpoint" if at is None else {n: float(th[n]) for n in names},
                              "fisher": F, "crlb": crlb, "condition": cond, "correlation": corr,
                              "knobs": names, "confounding": conf, "profile": prof or None,
                              "warnings": warnings, "level": lv}
    return _restatus(res)


def _profile_one_knob(P, k, u_hat, side, chi_min, sw, sigma_u, crit, trace):
    """Profile of a single-knob problem: chi^2 along the knob (nothing to re-fit)."""
    def d(t):
        r = (P.y - P.flat(P.mu(np.array([t]))[0])) * sw
        trace.append((float(_sc._from_u(float(t), k)), float(r @ r) - chi_min))
        return float(r @ r) - chi_min
    step = max(float(sigma_u), 1e-3) if math.isfinite(sigma_u) else 0.02
    lo_t, hi_t = u_hat, None
    for kk in range(16):
        t = min(1.0, max(0.0, u_hat + side * step * 2.0 ** kk))
        if d(t) > crit:
            hi_t = t
            break
        lo_t = t
        if t in (0.0, 1.0):
            return None
    if hi_t is None:
        return None
    for _ in range(40):
        mid = 0.5 * (lo_t + hi_t)
        if d(mid) > crit:
            hi_t = mid
        else:
            lo_t = mid
        if abs(hi_t - lo_t) < 1e-7:
            break
    return 0.5 * (lo_t + hi_t)


# --------------------------------------------------------------------------- #
# simcal_uncertainty                                                          #
# --------------------------------------------------------------------------- #
def simcal_uncertainty(result=None, method="laplace", n_boot=40, level=0.95, seed=0) -> dict:
    """Standard deviations and intervals of the determined knobs: Laplace (inverse Fisher) or parametric bootstrap.

    Only knobs that kept a point estimate are covered; knobs without one are held at the end
    point (the intervals are conditional on them — stated in ``note``). ``laplace``: covariance
    = inverse of J^T W J at the estimate on the unit-scaled knobs, intervals u ± z sd mapped back
    through each knob's scale (a log knob gets an asymmetric interval), ``std`` by the delta
    method. ``bootstrap``: ``n_boot`` refits to the fitted prediction plus Gaussian noise of the
    noise model's variance (Efron 1979), percentile intervals at ``level``. A result with no
    point estimate is refused. Under a model discrepancy both are optimistic
    (``simcal_discrepancy`` says so).
    """
    op = "simcal_uncertainty"
    res = _default_result() if result is None else result
    _check_result(res, op)
    if method not in ("laplace", "bootstrap"):
        raise ValueError("%s: method must be 'laplace' or 'bootstrap', got %r" % (op, method))
    lv = _sc._num(level, "level", op, 0.5, 0.999)
    if not res["theta_hat"]:
        raise MetricContractError("%s: the result has no point estimate (status %r) — there is nothing to put an "
                                  "uncertainty on" % (op, res.get("status")))
    res = copy.deepcopy(res)
    end = res["diagnostics"]["endpoint_not_an_estimate"]
    hold = {n: end[n] for n in end if n not in res["theta_hat"]}
    P, u = _problem(res, extra_fix=hold)
    from scipy.stats import norm
    z = float(norm.ppf(0.5 + lv / 2))
    names = [k["name"] for k in P.free]
    out = {"method": method, "level": lv, "knobs": names,
           "note": ("conditional on the knobs without an estimate held at the end point: %s" % sorted(hold)) if hold
           else "all fitted knobs determined"}
    if method == "laplace":
        sims, th = P.mu(u)
        sw = P.weights(sims, th)
        J = P.jac(u, sw)
        try:
            cu = np.linalg.inv(J.T @ J)
        except np.linalg.LinAlgError:
            raise MetricContractError("%s: the Fisher information is singular at the estimate" % op) from None
        su = np.sqrt(np.abs(np.diag(cu)))
        out["std"] = {n: float(su[i] / _sc._du_dtheta(th[n], k)) for i, (n, k) in enumerate(zip(names, P.free))}
        out["interval"] = {n: [float(_sc._from_u(max(0.0, u[i] - z * su[i]), k)),
                               float(_sc._from_u(min(1.0, u[i] + z * su[i]), k))]
                           for i, (n, k) in enumerate(zip(names, P.free))}
        out["clipped_to_range"] = [n for i, n in enumerate(names) if u[i] - z * su[i] < 0 or u[i] + z * su[i] > 1]
    else:
        nb = _doe._int_arg(n_boot, "n_boot", op, 5, 10000)
        rng = np.random.default_rng(seed)
        sims, th = P.mu(u)
        var = _sc._variances(P.model, sims, th)
        samples = []
        for b in range(nb):
            mb = copy.deepcopy(P.model)
            mb["observed"]["images"] = [s + np.sqrt(v) * rng.standard_normal(s.shape) for s, v in zip(sims, var)]
            Pb = _sc._Problem(mb, fix=P.fixed)
            run = _sc._lm(Pb, u, max_iter=60)
            tb = Pb.theta(run["u"])
            samples.append([tb[n] for n in names])
        S = np.asarray(samples)
        lo, hi = 100 * (1 - lv) / 2, 100 * (1 + lv) / 2
        out["std"] = {n: float(S[:, i].std(ddof=1)) for i, n in enumerate(names)}
        out["interval"] = {n: [float(np.percentile(S[:, i], lo)), float(np.percentile(S[:, i], hi))]
                           for i, n in enumerate(names)}
        out["n_boot"] = nb
        out["seed"] = seed
    res["uncertainty"] = out
    return res


# --------------------------------------------------------------------------- #
# simcal_validate                                                             #
# --------------------------------------------------------------------------- #
def _as_observed(res, data, split, op):
    if data is None:
        return None
    if isinstance(data, dict) and data.get("sort") == "simmodel":
        _sc._check_model(data, op, need_observed=True)
        if [k["name"] for k in data["knobs"]] != [k["name"] for k in res["model"]["knobs"]]:
            raise ValueError("%s: the %s model has different knobs from the fitted one" % (op, split))
        return data
    return _sc.simcal_observe(res["model"], data, split=split)


def _output_dims(model, P, seed):
    import sensitivity
    k = len(P.free)
    n = max(16, 4 * k)
    d = _doe.doe_lhs(n, [(kk["name"], 0.0, 1.0) for kk in P.free], seed=seed)
    U = (np.asarray(d["coded"]) + 1.0) / 2.0
    Y, _sw = _sc._whitened_runs(model, P, U)
    Yc = Y - Y.mean(axis=0)
    return int(sensitivity.mv_residual_pca(Yc, noise_sigma=1.0)["n_structural"])


def simcal_validate(result=None, holdout=None, locked=None, tau=None, dims=None, n_boot=200, alpha=1e-3,
                    seed=0) -> dict:
    """Over-fitting gates on held-out images; any one failing rejects the calibration (the estimates are withdrawn).

    ``holdout`` (and ``locked``): observed simmodels of the same knobs (``simcal_observe`` with
    ``split='holdout'`` / ``'locked'``) or image lists for the fitted model's conditions.
    Errors are reduced chi^2 (1 = the residuals are exactly the noise). Gates, each recorded in
    ``validation.gates`` with its value and limit:

    1. ``beats_initial`` — holdout error at the estimate < holdout error at the initial knobs;
    2. ``holdout_over_train`` — holdout / train <= 1 + tau, tau = the bootstrap 95 % relative
       spread of the train error over its pixels (``n_boot`` resamples) unless given;
    3. ``beats_gain_offset`` — better than the initial simulation re-scaled by a fitted gain and
       offset only (the cheapest model that could explain the images);
    4. ``estimate_plausible`` — every estimate inside its range, not within 1 % of an end, and
       within 3 sd of its prior when one is given;
    5. ``knobs_within_dims`` — free knobs <= output directions above noise (``dims``, or computed
       from a Latin hypercube over the knobs with ``sensitivity.mv_residual_pca``);
    6. ``fit_consistent_with_noise`` — the absolute gate: on the train images (nu = pixels − free
       knobs) and on the holdout images (nu = pixels), chi^2 of the noise-normalised residuals has an
       upper-tail probability P(chi^2_nu >= chi^2) of at least ``alpha`` (default 1e-3). Gates 1-5
       are relative comparisons and pass a fit that is 60 times the noise everywhere (a thin film in
       the wrong fringe order, measured); this one does not. Judged on p, not on chi^2/nu, because
       chi^2/nu concentrates on 1 for large nu (both are returned). The variance is the noise model's
       plus, for a stochastic model, its sample variance. A failure means: the fit is bad for this
       noise model — a local minimum, a model discrepancy, or a noise estimate that is too small.
       ★It does NOT detect a noise model that is too large: over-estimating the variance by 4x drives
       p to 1 and the gate passes (measured) — that direction is visible only as chi^2/nu << 1.

    ``locked`` is scored **once** (``errors.locked``) and is not used by any gate; a result that
    already carries a LOCKED score is refused (the ``robust.py`` discipline: the untouched number
    is untouched only once).
    """
    op = "simcal_validate"
    if result is None:
        result = _default_result()
        if holdout is None:
            m = result["model"]
            truth = m.get("truth") or _sc._init_values(m)
            rng = np.random.default_rng(_sc._RNG_SEED_DEMO + 10000)            # robust.py: OBSERVED = seed + 10000
            holdout = [_sc._physical_capture(y, truth["offset"], 0.5, 6.0, rng) for y in _sc._simulate(m, truth)]
    _check_result(result, op)
    if holdout is None:
        raise ValueError("%s: holdout images (or an observed simmodel) are required" % op)
    if locked is not None and result["errors"].get("locked") is not None:
        raise MetricContractError("%s: this result already has a LOCKED score (%.4g) — the LOCKED split is scored "
                                  "once; re-scoring it turns it into another holdout" % (op, result["errors"]["locked"]))
    res = copy.deepcopy(result)
    hm = _as_observed(res, holdout, "holdout", op)
    lm = _as_observed(res, locked, "locked", op)
    P, u = _problem(res)
    Ph, _ = _problem(res, model=hm)
    train, rtr = _chi_red(P, u)
    hold, rho = _chi_red(Ph, u)
    from scipy.stats import chi2 as _chi2
    a_v = _sc._num(alpha, "alpha", op, 0.0, 0.5, lo_open=True)
    chi_tr, nu_tr = float(rtr @ rtr), max(1, rtr.size - len(P.free))
    chi_ho, nu_ho = float(rho @ rho), max(1, rho.size)
    p_tr, p_ho = float(_chi2.sf(chi_tr, nu_tr)), float(_chi2.sf(chi_ho, nu_ho))
    u0 = np.array([_sc._to_u(k["init"], k) for k in P.free])
    hold0, _ = _chi_red(Ph, u0)
    # gain + offset baseline: weighted least squares of the train images on the initial simulation
    sims0, th0 = P.mu(u0)
    s0 = P.flat(sims0)
    w = P.weights(sims0, th0)
    A = np.column_stack([s0 * w, w])
    ab, *_ = np.linalg.lstsq(A, P.y * w, rcond=None)
    sh0 = Ph.flat(Ph.mu(u0)[0])
    pred_h = ab[0] * sh0 + ab[1]
    var_h = Ph.flat(_sc._variances(hm, [ab[0] * s + ab[1] for s in Ph.mu(u0)[0]], th0))
    rb = (Ph.y - pred_h) / np.sqrt(var_h)
    hold_go = float(rb @ rb) / max(1, rb.size - 2)
    if tau is None:
        nb = _doe._int_arg(n_boot, "n_boot", op, 10, 100000)
        rng = np.random.default_rng(seed)
        c = rtr ** 2
        boots = np.array([c[rng.integers(0, c.size, c.size)].mean() for _ in range(nb)])
        tau_v = float(np.percentile(boots, 95) / max(c.mean(), 1e-300) - 1.0)
    else:
        tau_v = _sc._num(tau, "tau", op, 0.0)
    if dims is None:
        dims_v = _output_dims(res["model"], P, seed)
    elif isinstance(dims, dict):
        dims_v = dims.get("output_dims")
        if dims_v is None:
            raise ValueError("%s: dims table has no output_dims" % op)
    else:
        dims_v = _doe._int_arg(dims, "dims", op, 0, 10 ** 6)
    th = P.theta(u)
    implaus = []
    for k in P.free:
        n = k["name"]
        if n not in res["theta_hat"]:
            continue
        v = th[n]
        uu = _sc._to_u(v, k)
        if not (0.0 <= uu <= 1.0):
            implaus.append("%s = %g outside %g..%g" % (n, v, k["lo"], k["hi"]))
        elif uu < _sc.EDGE_FRACTION or uu > 1 - _sc.EDGE_FRACTION:
            implaus.append("%s = %g within 1 %% of a range end" % (n, v))
        if k.get("prior") is not None and abs(v - k["prior"][0]) > 3 * k["prior"][1]:
            implaus.append("%s = %g beyond 3 sd of its prior %g +- %g" % (n, v, k["prior"][0], k["prior"][1]))
    gates = {
        "beats_initial": {"passed": bool(hold < hold0), "value": hold, "limit": hold0},
        "holdout_over_train": {"passed": bool(hold / train <= 1.0 + tau_v), "value": hold / train,
                               "limit": 1.0 + tau_v},
        "beats_gain_offset": {"passed": bool(hold < hold_go), "value": hold, "limit": hold_go},
        "estimate_plausible": {"passed": not implaus, "value": len(implaus), "limit": 0, "detail": implaus},
        "knobs_within_dims": {"passed": bool(len(P.free) <= dims_v), "value": len(P.free), "limit": dims_v},
        "fit_consistent_with_noise": {
            "passed": bool(p_tr >= a_v and p_ho >= a_v), "value": min(p_tr, p_ho), "limit": a_v,
            "train": {"chi2": chi_tr, "nu": nu_tr, "chi2_per_nu": chi_tr / nu_tr, "p": p_tr},
            "holdout": {"chi2": chi_ho, "nu": nu_ho, "chi2_per_nu": chi_ho / nu_ho, "p": p_ho},
            "detail": "" if (p_tr >= a_v and p_ho >= a_v) else (
                "the fit is poor for the noise model (chi^2/nu train %.3g, holdout %.3g; p %.3g, %.3g < alpha %g): a "
                "local minimum, a model discrepancy, or a noise estimate that is too small"
                % (chi_tr / nu_tr, chi_ho / nu_ho, p_tr, p_ho, a_v))},
    }
    failed = [g for g, v in gates.items() if not v["passed"]]
    res["errors"] = dict(res["errors"], train=train, holdout=hold, holdout_initial=hold0, holdout_gain_offset=hold_go)
    if lm is not None:
        Pl, _ = _problem(res, model=lm)
        res["errors"]["locked"] = _chi_red(Pl, u)[0]
    if failed:
        why = "; ".join("%s (%.4g vs %.4g)%s" % (g, gates[g]["value"], gates[g]["limit"],
                                                 (" — " + gates[g]["detail"]) if gates[g].get("detail") else "")
                        for g in failed)
        for n in list(res["theta_hat"]):
            _withdraw(res, n, "validation gate failed: %s" % why, "validate")
        res["determined_combos"] = []
    res["validation"] = {"gates": gates, "failed": failed, "passed": not failed, "tau": tau_v,
                         "output_dims": dims_v, "n_free": len(P.free), "split_holdout": hm["observed"]["split"],
                         "locked_scored": lm is not None, "seed": seed}
    return _restatus(res)


# --------------------------------------------------------------------------- #
# simcal_discrepancy                                                          #
# --------------------------------------------------------------------------- #
def _tw_edge(n, p, level):
    a, b = sorted((n, p))
    a = max(a, 2)
    mu = (math.sqrt(a - 1) + math.sqrt(b)) ** 2
    sg = (math.sqrt(a - 1) + math.sqrt(b)) * (1 / math.sqrt(a - 1) + 1 / math.sqrt(b)) ** (1 / 3)
    return math.sqrt(mu + TW1_QUANTILES[level] * sg)


def simcal_discrepancy(result=None, level=0.99) -> dict:
    """Is there structure in the noise-normalised residuals that the model cannot produce (model discrepancy)?

    The residual of every valid pixel is divided by the noise standard deviation (camera noise
    plus the model's own sample variance), so white residuals have unit variance. With three or
    more conditions the matrix is conditions x pixels valid in all of them; with fewer it is the
    rows x columns of the (first) residual image (a smooth spatial pattern is low-rank there).
    ``sensitivity.mv_residual_pca`` counts the components whose singular value exceeds the
    Tracy-Widom ``level`` point of white noise of that shape (Johnstone 2001; ``level`` in 0.90 /
    0.95 / 0.99 — the bare Marchenko-Pastur edge sqrt(n) + sqrt(p) is exceeded by pure noise
    10-14 % of the time, measured). Structure found: ``verdict = "structure"``, the loadings as
    maps (where the model is wrong), and a warning that every uncertainty of the result is
    optimistic — a calibrated knob may be absorbing the missing physics.
    """
    op = "simcal_discrepancy"
    res = _default_result() if result is None else result
    _check_result(res, op)
    try:
        lv = float(level)
    except (TypeError, ValueError):
        raise ValueError("%s: level must be one of %s" % (op, sorted(TW1_QUANTILES))) from None
    if lv not in TW1_QUANTILES:
        raise ValueError("%s: level must be one of %s, got %r" % (op, sorted(TW1_QUANTILES), level))
    import sensitivity
    res = copy.deepcopy(res)
    P, u = _problem(res)
    sims, th = P.mu(u)
    var = _sc._variances(P.model, sims, th)
    obs = P.model["observed"]
    maps = [np.where(m, (o - s) / np.sqrt(v), 0.0) for o, s, v, m in zip(obs["images"], sims, var, obs["mask"])]
    shapes = [mp.shape for mp in maps]
    if len(maps) >= 3 and len(set(shapes)) == 1:
        common = np.logical_and.reduce(obs["mask"])
        R = np.stack([mp[common] for mp in maps])
        mode, shape = "conditions_x_pixels", shapes[0]
    else:
        R = maps[0]
        common = obs["mask"][0]
        mode, shape = "rows_of_image", shapes[0]
    if R.shape[0] < 3 or R.shape[1] < 3:
        raise MetricContractError("%s: the residual matrix %s is too small for a PCA (needs >= 3 x 3: more "
                                  "conditions or a larger image)" % (op, R.shape))
    n, p = R.shape
    edge = _tw_edge(n, p, lv)
    pc = sensitivity.mv_residual_pca(R, noise_sigma=edge / (math.sqrt(n) + math.sqrt(p)))
    k = int(pc["n_structural"])
    loading_maps = []
    for c in range(min(k, 3)):
        if mode == "conditions_x_pixels":
            mp = np.zeros(shape)
            mp[common] = pc["loadings"][:, c]
        else:
            mp = np.outer(pc["scores"][:, c], pc["loadings"][:, c])
        loading_maps.append(mp)
    sto = P.model.get("stochastic")
    notes = []
    if sto is not None and sto.get("sample_var_maps") is None:
        notes.append("the forward model is stochastic but no sample variance was given — its sampling noise counts "
                     "as residual here and can look like structure (pass stochastic={'sample_var': 'estimate'})")
    if k:
        notes.append("structure above the noise: the model misses something; the uncertainties of this result are "
                     "optimistic (a knob may absorb the discrepancy)")
    res["discrepancy"] = {"mode": mode, "matrix_shape": [n, p], "level": lv, "edge_tracy_widom": edge,
                          "edge_marchenko_pastur": math.sqrt(n) + math.sqrt(p),
                          "singular_values": pc["singular_values"][: min(10, pc["singular_values"].size)],
                          "n_structural": k, "structural_energy_share": pc["structural_energy_share"],
                          "rms_normalised": pc["rms"], "verdict": "structure" if k else "white",
                          "loading_maps": loading_maps, "optimistic_uncertainty": bool(k), "notes": notes}
    return res


# --------------------------------------------------------------------------- #
# simcal_report                                                               #
# --------------------------------------------------------------------------- #
def _fmt(v):
    if v is None:
        return "-"
    return "%.6g" % v


def simcal_report(result=None) -> dict:
    """One table of a calibration: each knob's value, unit, interval and class, the gates, and the reasons for refusals.

    ``rows`` — one dict per knob (``knob``, ``unit``, ``scale``, ``value`` or ``None``, ``std``,
    ``interval`` from the uncertainty or the profile, ``class`` = ``estimated`` / ``fixed`` /
    ``undetermined`` with ``reason``); ``combos`` — determined combinations; ``gates`` — every
    check that was run with pass/fail; ``errors`` — train / holdout / locked reduced chi^2;
    ``text`` — the same as plain lines. Reports what is there: a check that was not run is listed
    as ``not run``, never as passed.
    """
    op = "simcal_report"
    res = _default_result() if result is None else result
    _check_result(res, op)
    model = res["model"]
    unc = res.get("uncertainty") or {}
    idf = res.get("identifiability") or {}
    prof = idf.get("profile") or {}
    rows = []
    for k in model["knobs"]:
        n = k["name"]
        row = {"knob": n, "unit": k["unit"], "scale": k["scale"], "range": [k["lo"], k["hi"]],
               "nuisance": n in (res.get("nuisance") or [])}
        if n in res["fixed"]:
            row.update({"class": "fixed", "value": res["fixed"][n]})
        elif n in res["theta_hat"]:
            row.update({"class": "estimated", "value": res["theta_hat"][n],
                        "std": (unc.get("std") or {}).get(n), "crlb": (idf.get("crlb") or {}).get(n),
                        "interval": (unc.get("interval") or {}).get(n) or (
                            [prof[n]["lower"], prof[n]["upper"]] if n in prof else None)})
        else:
            row.update({"class": "undetermined", "value": None, "reason": res["undetermined"].get(n)})
        rows.append(row)
    gates = {}
    if res.get("identifiability") is not None:
        gates["identifiability"] = {"passed": not any(r["rule"] == "profile" for r in res["refusals"]),
                                    "warnings": idf.get("warnings")}
    else:
        gates["identifiability"] = "not run"
    gates["validation"] = (res["validation"]["gates"] if res.get("validation") else "not run")
    dsc = res.get("discrepancy")
    gates["discrepancy"] = ({"passed": dsc["verdict"] == "white", "n_structural": dsc["n_structural"]}
                            if dsc else "not run")
    lines = ["%s — status: %s" % (model.get("name"), res["status"])]
    for r in rows:
        if r["class"] == "estimated":
            iv = r.get("interval")
            lines.append("  %-12s = %s %s%s%s" % (r["knob"], _fmt(r["value"]), r["unit"],
                                                  "" if r.get("std") is None else "  (sd %s)" % _fmt(r["std"]),
                                                  "" if not iv else "  [%s, %s]" % (_fmt(iv[0]), _fmt(iv[1]))))
        elif r["class"] == "fixed":
            lines.append("  %-12s = %s %s  (fixed)" % (r["knob"], _fmt(r["value"]), r["unit"]))
        else:
            lines.append("  %-12s : no estimate — %s" % (r["knob"], r.get("reason")))
    for c in res.get("determined_combos") or []:
        lines.append("  combination  %s = %s" % (c["combination"], c["value"]))
    e = res["errors"]
    lines.append("  reduced chi^2: train %s, holdout %s, locked %s" % (_fmt(e.get("train")), _fmt(e.get("holdout")),
                                                                    _fmt(e.get("locked"))))
    for g, v in gates.items():
        if v == "not run":
            lines.append("  check %-16s not run" % g)
        elif g == "validation":
            lines.append("  check %-16s %s" % (g, ", ".join("%s %s" % (n, "pass" if x["passed"] else "FAIL")
                                                            for n, x in v.items())))
        else:
            lines.append("  check %-16s %s" % (g, "pass" if v["passed"] else "FAIL"))
    if dsc and dsc["notes"]:
        lines += ["  note: " + s for s in dsc["notes"]]
    return {"status": res["status"], "rows": rows, "combos": list(res.get("determined_combos") or []),
            "gates": gates, "errors": dict(e), "text": "\n".join(lines), "data_range": list(res["data_range"])}
