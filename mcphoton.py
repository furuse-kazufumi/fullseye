# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""mcphoton — Monte Carlo photon transport in a multi-layered turbid slab (MCML rules), vectorised.

The forward model of light that does not go straight: a pencil beam at normal incidence on
a stack of plane-parallel layers, each with refractive index n, absorption and scattering
coefficients mu_a, mu_s [1/length], Henyey-Greenstein anisotropy g and thickness d (the last
layer may be semi-infinite). Photon packets are traced with the rules of the MCML manual
(Wang, Jacques & Zheng 1995; manual by Wang & Jacques), all packets at once in numpy:

* launch weight W = 1 - R_sp with R_sp = ((n0 - n1)/(n0 + n1))^2      (manual eqs. 3.2a, 3.5)
* dimensionless step -ln(xi), converted per layer: s = step / mu_t      (eqs. 3.9-3.13, 3.30)
* hop, then absorb dW = W mu_a / mu_t                                   (eqs. 3.14-3.17)
* Henyey-Greenstein deflection and the direction update                 (eqs. 3.18-3.22)
* at a boundary: move to it, Fresnel reflectance from Snell's law, all-or-none reflection
  (xi <= R reflects, u_z -> -u_z); escaping weight is scored as R_d (top) or T_t (bottom);
  crossing an interface rescales u_x, u_y by n_i/n_t                    (eqs. 3.23-3.30)
* roulette below W_th: survive with probability 1/m at weight mW       (eq. 3.31)

Only the totals are scored (R_d, T_t, absorbed fraction per layer), so the lateral position
is not tracked. Each packet's contribution is kept, so the standard error and a confidence
interval come from the packets themselves, and ``tol`` turns the run into a sequential Monte
Carlo (``converge.mc_sequential_mean``'s stopping rule) that adds packets until the interval is
narrow enough.

External truth (gates): MCML manual Table 6.1 (n = 1, mu_a = 10, mu_s = 90 /cm, g = 0.75,
d = 0.02 cm: R_d = 0.09739, T_t = 0.66096, van de Hulst 1980) and Table 6.2 (semi-infinite,
n = 1.5, g = 0: 0.2600, Giovanelli 1955). Table 6.2 is reproduced by the TOTAL reflectance
R_sp + R_d (here 0.04 + 0.219 = 0.259; MCML's own run in the table, 0.25907 +- 0.0017, and Prahl
et al. 1989, 0.26079, agree with that sum) — the diffuse part alone is 0.219. The matched
semi-infinite case is checked independently against the plane albedo 1 - H(1) sqrt(1 - a) of
Chandrasekhar's H-function (solved with ``converge.iterate_fixed_point``).
"""
from __future__ import annotations

import math

import numpy as np

import converge as _cv
from metriccontract import MetricContractError

__all__ = ["mc_photon_slab"]

#: MCML manual Table 6.1 (slab, matched boundary) and Table 6.2 (semi-infinite, mismatched).
MCML_TABLE_6_1 = {"layers": [{"n": 1.0, "mua": 10.0, "mus": 90.0, "g": 0.75, "d": 0.02}],
                  "n_above": 1.0, "n_below": 1.0, "Rd": 0.09739, "Tt": 0.66096,
                  "source": "MCML manual Table 6.1 (van de Hulst 1980)"}
MCML_TABLE_6_2 = {"layers": [{"n": 1.5, "mua": 10.0, "mus": 90.0, "g": 0.0, "d": math.inf}],
                  "n_above": 1.0, "n_below": 1.0, "Rd": 0.2600,
                  "source": "MCML manual Table 6.2 (Giovanelli 1955)"}

MAX_PHOTONS_CAP = 50_000_000
COS_ZERO = 1.0 - 1e-12
COS_90 = 1e-6


def _layers(layers, op):
    if not isinstance(layers, (list, tuple)) or not layers:
        raise ValueError("%s: layers must be a non-empty list of dicts {n, mua, mus, g, d}" % op)
    out = []
    for i, L in enumerate(layers):
        if not isinstance(L, dict):
            raise ValueError("%s: layer %d must be a dict" % (op, i))
        try:
            n, mua, mus, g, d = (float(L[k]) for k in ("n", "mua", "mus", "g", "d"))
        except KeyError as e:
            raise ValueError("%s: layer %d lacks %s" % (op, i, e)) from None
        except (TypeError, ValueError):
            raise ValueError("%s: layer %d values must be numbers" % (op, i)) from None
        if not (math.isfinite(n) and n >= 1.0):
            raise ValueError("%s: layer %d: n must be >= 1" % (op, i))
        if not (math.isfinite(mua) and mua >= 0 and math.isfinite(mus) and mus >= 0 and mua + mus > 0):
            raise ValueError("%s: layer %d: mua, mus must be >= 0 with mua + mus > 0 (glass layers are not modelled)" % (op, i))
        if not (math.isfinite(g) and -1.0 < g < 1.0):
            raise ValueError("%s: layer %d: g must be in (-1, 1)" % (op, i))
        if not (d > 0):
            raise ValueError("%s: layer %d: d must be > 0" % (op, i))
        if math.isinf(d) and i != len(layers) - 1:
            raise ValueError("%s: only the last layer may be semi-infinite" % op)
        out.append((n, mua, mus, g, d))
    return out


def _fresnel(ni, nt, ca):
    """Unpolarised Fresnel reflectance (manual eq. 3.26) for incidence cosine ``ca`` (array), ni -> nt."""
    R = np.zeros_like(ca)
    same = ni == nt
    if np.all(same):
        return R
    sa = np.sqrt(np.maximum(0.0, 1.0 - ca * ca))
    st = ni / nt * sa
    tir = st >= 1.0
    normal = ca > COS_ZERO
    R[normal] = ((ni[normal] - nt[normal]) / (ni[normal] + nt[normal])) ** 2
    gen = ~(tir | normal | same)
    if gen.any():
        ct = np.sqrt(np.maximum(0.0, 1.0 - st[gen] ** 2))
        c, s_, cT, sT = ca[gen], sa[gen], ct, st[gen]
        cap = c * cT - s_ * sT          # cos(ai + at)
        cam = c * cT + s_ * sT          # cos(ai - at)
        sap = s_ * cT + c * sT          # sin(ai + at)
        sam = s_ * cT - c * sT          # sin(ai - at)
        R[gen] = 0.5 * sam * sam * (cam * cam + cap * cap) / (sap * sap * cam * cam)
    R[tir & ~same] = 1.0
    R[same] = 0.0
    return R


def _spin(ux, uy, uz, g, rng):
    """Henyey-Greenstein deflection (eq. 3.19), uniform azimuth (eq. 3.20), direction update (eqs. 3.21-3.22)."""
    xi = rng.random(ux.size)
    ct = np.empty_like(ux)
    iso = np.abs(g) < 1e-12
    ct[iso] = 2.0 * xi[iso] - 1.0
    gg = g[~iso]
    if gg.size:
        tmp = (1.0 - gg * gg) / (1.0 - gg + 2.0 * gg * xi[~iso])
        ct[~iso] = (1.0 + gg * gg - tmp * tmp) / (2.0 * gg)
    ct = np.clip(ct, -1.0, 1.0)
    st = np.sqrt(1.0 - ct * ct)
    psi = 2.0 * math.pi * rng.random(ux.size)
    cp, sp = np.cos(psi), np.sin(psi)
    nux, nuy, nuz = np.empty_like(ux), np.empty_like(uy), np.empty_like(uz)
    near = np.abs(uz) > 0.99999
    nux[near] = st[near] * cp[near]
    nuy[near] = st[near] * sp[near]
    nuz[near] = np.sign(uz[near]) * ct[near]
    f = ~near
    if f.any():
        tmp = np.sqrt(1.0 - uz[f] * uz[f])
        nux[f] = st[f] * (ux[f] * uz[f] * cp[f] - uy[f] * sp[f]) / tmp + ux[f] * ct[f]
        nuy[f] = st[f] * (uy[f] * uz[f] * cp[f] + ux[f] * sp[f]) / tmp + uy[f] * ct[f]
        nuz[f] = -st[f] * cp[f] * tmp + uz[f] * ct[f]
    return nux, nuy, nuz


def _trace(L, n_above, n_below, n, rng, w_th, m_roulette, max_steps):
    """Trace ``n`` packets; returns per-packet (Rd, Tt, absorbed per layer) contributions and R_sp."""
    nL = len(L)
    nn = np.array([l[0] for l in L])
    mua = np.array([l[1] for l in L])
    mus = np.array([l[2] for l in L])
    gL = np.array([l[3] for l in L])
    d = np.array([l[4] for l in L])
    mut = mua + mus
    z0 = np.concatenate([[0.0], np.cumsum(d)[:-1]])
    z1 = z0 + d
    n_up = np.concatenate([[n_above], nn[:-1]])         # medium above layer i
    n_dn = np.concatenate([nn[1:], [n_below]])          # medium below layer i
    rsp = ((n_above - nn[0]) / (n_above + nn[0])) ** 2  # eq. 3.2a
    rd = np.zeros(n)
    tt = np.zeros(n)
    ab = np.zeros((n, nL))
    idx = np.arange(n)
    z = np.zeros(n)
    ux = np.zeros(n)
    uy = np.zeros(n)
    uz = np.ones(n)
    W = np.full(n, 1.0 - rsp)                          # eq. 3.5
    lay = np.zeros(n, dtype=np.int64)
    sleft = np.zeros(n)                                # dimensionless step left (eq. 3.13)
    steps = 0
    while idx.size:
        steps += 1
        if steps > max_steps:
            raise MetricContractError("mc_photon_slab: %d packets still alive after %d steps" % (idx.size, max_steps))
        need = sleft <= 0.0
        if need.any():
            sleft[need] = -np.log(1.0 - rng.random(int(need.sum())))      # xi in (0, 1]
        mt = mut[lay]
        s = sleft / mt
        with np.errstate(divide="ignore", invalid="ignore"):
            db = np.where(uz < 0, (z0[lay] - z) / uz, np.where(uz > 0, (z1[lay] - z) / uz, np.inf))
        hit = s > db
        # --- no boundary: hop, absorb, scatter (eqs. 3.14-3.22) ---
        nh = ~hit
        if nh.any():
            z[nh] += s[nh] * uz[nh]
            sleft[nh] = 0.0
            dw = W[nh] * mua[lay[nh]] / mt[nh]
            np.add.at(ab, (idx[nh], lay[nh]), dw)
            W[nh] -= dw
            ux[nh], uy[nh], uz[nh] = _spin(ux[nh], uy[nh], uz[nh], gL[lay[nh]], rng)
        # --- boundary: move to it, reflect or transmit (eqs. 3.23-3.30) ---
        dead = np.zeros(idx.size, dtype=bool)
        if hit.any():
            h = np.nonzero(hit)[0]
            up = uz[h] < 0
            z[h] = np.where(up, z0[lay[h]], z1[lay[h]])
            sleft[h] -= db[h] * mt[h]
            sleft[h] = np.maximum(sleft[h], 0.0)
            ni = nn[lay[h]]
            nt = np.where(up, n_up[lay[h]], n_dn[lay[h]])
            ca = np.abs(uz[h])
            R = _fresnel(ni, nt, ca)
            refl = rng.random(h.size) <= R                                  # eq. 3.27
            hr = h[refl]
            uz[hr] = -uz[hr]                                               # eq. 3.28
            ht = h[~refl]
            if ht.size:
                upt = uz[ht] < 0
                out_top = upt & (lay[ht] == 0)
                out_bot = (~upt) & (lay[ht] == nL - 1)
                if out_top.any():
                    rd[idx[ht[out_top]]] += W[ht[out_top]]                # eq. 3.29
                    dead[ht[out_top]] = True
                if out_bot.any():
                    tt[idx[ht[out_bot]]] += W[ht[out_bot]]
                    dead[ht[out_bot]] = True
                cross = ht[~(out_top | out_bot)]
                if cross.size:
                    ni_c = nn[lay[cross]]
                    goes_up = uz[cross] < 0
                    nl = np.where(goes_up, lay[cross] - 1, lay[cross] + 1)
                    nt_c = nn[nl]
                    ratio = ni_c / nt_c
                    sa = np.sqrt(np.maximum(0.0, 1.0 - uz[cross] ** 2))
                    st = np.minimum(ratio * sa, 1.0)
                    ux[cross] *= ratio
                    uy[cross] *= ratio
                    uz[cross] = np.sign(uz[cross]) * np.sqrt(1.0 - st * st)
                    lay[cross] = nl
                    # the dimensionless step left carries over (eq. 3.30 is this conversion)
        # --- roulette (eq. 3.31) ---
        low = (~dead) & (W < w_th) & (W > 0.0) & (~hit)
        if low.any():
            li = np.nonzero(low)[0]
            surv = rng.random(li.size) <= 1.0 / m_roulette
            W[li[surv]] *= m_roulette
            W[li[~surv]] = 0.0
            dead[li[~surv]] = True
        dead |= (W <= 0.0)
        if dead.any():
            keep = ~dead
            idx, z, ux, uy, uz, W, lay, sleft = (a[keep] for a in (idx, z, ux, uy, uz, W, lay, sleft))
    return rd, tt, ab, rsp


def mc_photon_slab(layers=None, n_above=1.0, n_below=1.0, n_photons=100_000, tol=None, confidence=0.95,
                   batch=50_000, seed=1, w_threshold=1e-4, roulette_m=10) -> dict:
    """Diffuse reflectance, total transmittance and absorption of a layered turbid slab by MCML-type Monte Carlo, with confidence intervals.

    ``layers``: list of ``{"n", "mua", "mus", "g", "d"}`` from the top (coefficients in 1/length,
    thickness in the same length; ``d = inf`` for a semi-infinite last layer). ``n_above`` /
    ``n_below``: ambient refractive indices. A pencil beam enters at normal incidence.

    The tracing rules are those of the MCML manual (Wang & Jacques), eqs. 3.2a-3.31 — see the
    module docstring for which equation does what. Every packet's contribution is kept, so the
    standard error is the sample standard deviation over packets / sqrt(N) and the interval is
    mean +- z se (``confidence``). Batch b uses ``default_rng((seed, b))``.

    * ``tol=None``: trace ``n_photons`` packets.
    * ``tol=h``: sequential Monte Carlo — add batches of ``batch`` packets until the
      half-width of R_d and of T_t is <= h (the stopping rule of ``converge``, from the second
      batch on), with ``n_photons`` as the budget: refusing (``NotConvergedError``) if the
      budget is spent first.

    Returns ``Rd``, ``Tt``, ``A`` (absorbed fraction) and ``A_layers``, each with ``*_se`` and
    ``*_ci``; ``Rsp`` (specular, deterministic: eq. 3.2a); ``energy_balance`` = R_sp + R_d +
    T_t + A (1 in expectation — roulette conserves energy only on average, so its deviation is
    compared with its own standard error); ``R_total`` = R_sp + R_d (specular plus diffuse, with
    the interval of R_d shifted by the deterministic R_sp); ``n_photons``. Defaults: the MCML manual Table 6.1
    slab (van de Hulst: R_d = 0.09739, T_t = 0.66096); ``MCML_TABLE_6_2`` holds Table 6.2.
    """
    op = "mc_photon_slab"
    if layers is None:
        layers = MCML_TABLE_6_1["layers"]
    L = _layers(layers, op)
    na, nb = float(n_above), float(n_below)
    if not (math.isfinite(na) and na >= 1.0 and math.isfinite(nb) and nb >= 1.0):
        raise ValueError("%s: n_above and n_below must be >= 1" % op)
    try:
        n_photons, batch, seed, roulette_m = (int(v) for v in (n_photons, batch, seed, roulette_m))
    except (TypeError, ValueError):
        raise ValueError("%s: n_photons, batch, seed and roulette_m must be integers" % op) from None
    if not 100 <= n_photons <= MAX_PHOTONS_CAP:
        raise ValueError("%s: n_photons must be in 100..%d" % (op, MAX_PHOTONS_CAP))
    if not 100 <= batch <= MAX_PHOTONS_CAP:
        raise ValueError("%s: need 100 <= batch <= %d" % (op, MAX_PHOTONS_CAP))
    w_th = float(w_threshold)
    if not (0.0 < w_th < 1.0) or roulette_m < 2:
        raise ValueError("%s: need 0 < w_threshold < 1 and roulette_m >= 2" % op)
    z = _cv._z(confidence, op)
    nL = len(L)
    rsp_box = {}

    def draw(b, nphot):
        rng = np.random.default_rng((int(seed), int(b)))
        rd, tt, ab, rsp = _trace(L, na, nb, nphot, rng, w_th, roulette_m, max_steps=200_000)
        rsp_box["rsp"] = rsp
        return np.column_stack([rd, tt, ab.sum(axis=1), ab])

    k = 3 + nL
    if tol is None:
        mom = _cv._Moments(k)
        b = 0
        done = 0
        while done < n_photons:
            nb_ = min(batch, n_photons - done)
            mom.add(draw(b, nb_))
            done += nb_
            b += 1
        converged = True
        hist = None
    else:
        h = float(tol)
        if not (math.isfinite(h) and h > 0):
            raise ValueError("%s: tol must be > 0" % op)
        # stop on R_d and T_t (columns 0 and 1); the absorbed fraction follows from the balance
        mom2 = {"m": None}

        def draw2(b, nphot):
            X = draw(b, nphot)
            mom2.setdefault("all", _cv._Moments(k)).add(X)
            return X[:, :2]

        _m, hist, converged = _cv._sequential_columns(draw2, 2, h, 0.0, z, batch, 2 * batch, n_photons, op)
        mom = mom2["all"]
        if not converged:
            se = _m.se()
            raise _cv.NotConvergedError(
                "%s: the budget n_photons = %d was spent with half-widths R_d %.3g, T_t %.3g > tol %.3g"
                % (op, n_photons, z * se[0], z * se[1], h),
                {"op": op, "converged": False, "n_photons": int(_m.n)})
    mean, se = mom.mean, mom.se()
    rsp = float(rsp_box["rsp"])

    def ci(i):
        return (float(mean[i] - z * se[i]), float(mean[i] + z * se[i]))

    bal = rsp + mean[0] + mean[1] + mean[2]
    bal_se = float(math.sqrt(max(0.0, se[0] ** 2 + se[1] ** 2 + se[2] ** 2)))
    out = {"op": op, "converged": bool(converged), "n_photons": int(mom.n), "confidence": float(confidence), "z": z,
           "Rsp": rsp,
           "Rd": float(mean[0]), "Rd_se": float(se[0]), "Rd_ci": ci(0),
           "R_total": float(rsp + mean[0]), "R_total_ci": (rsp + ci(0)[0], rsp + ci(0)[1]),
           "Tt": float(mean[1]), "Tt_se": float(se[1]), "Tt_ci": ci(1),
           "A": float(mean[2]), "A_se": float(se[2]), "A_ci": ci(2),
           "A_layers": [float(v) for v in mean[3:]], "A_layers_se": [float(v) for v in se[3:]],
           "energy_balance": float(bal), "energy_balance_se_bound": bal_se,
           "layers": [dict(zip(("n", "mua", "mus", "g", "d"), l)) for l in L],
           "n_above": na, "n_below": nb,
           "rules": "MCML manual (Wang & Jacques) eqs. 3.2a-3.31, all-or-none Fresnel reflection, roulette m=%d below W=%g"
                    % (roulette_m, w_th)}
    if hist is not None:
        out["history"] = [{"n": n, "Rd": float(mu[0]), "Tt": float(mu[1]), "Rd_se": float(s[0]), "Tt_se": float(s[1])}
                          for n, mu, s in hist]
    return out
