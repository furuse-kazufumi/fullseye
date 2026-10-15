# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""simcal — fit the coefficients of a physical forward model to real images, and refuse when the data cannot fix them.

A forward model (a chain of fullseye ops, e.g. blur -> vignetting -> gain/offset, or a
thin-film reflectance -> camera) has knobs with physical units. Given images taken under
known conditions and a noise model of the camera, this family estimates the knobs by
weighted least squares — and, as importantly, says **which knobs the images do not
determine** instead of returning numbers for them.

Ops (C4 of the design: model, simulation, observation, screening, fit)
----------------------------------------------------------------------
``simcal_model``     build a ``simmodel``: the chain, the knobs (name, step, argument, range,
                     unit, prior, linear/log scale), nuisance knobs, the camera noise model and
                     an optional stochastic forward model (common random numbers + sample
                     variance). Validated by running it once (fail-closed).
``simcal_simulate``  run the chain at given knob values -> one 2-D array per condition.
``simcal_observe``   attach measured images: alignment by phase correlation
                     (``filters_freq.phase_correlation_fft``, reused), ROI, exposure
                     normalisation (refused together with a gain knob: both would scale the
                     same thing and the noise model would be applied twice).
``simcal_screen``    which knobs move the picture at all (Morris or Sobol' on the principal
                     components of the noise-whitened outputs — ``sensitivity`` reused), how
                     many output directions rise above the noise, and which knobs are
                     confounded (``sensitivity.mv_confounding``, Brun et al. 2001).
``simcal_fit``       Levenberg-Marquardt with iteratively re-weighted residuals (a step that
                     leaves the knob range is rejected and the damping raised — the practice of
                     ``lensopt.optimize_lens``), Nelder-Mead, or multi-start ranked with
                     ``metriccontract.Attempt`` / ``value_or_worst``. **Refuses** (raises
                     :class:`metriccontract.MetricContractError`) when a knob is confounded,
                     has no influence, or ends within 1 % of its range end — unless the caller
                     passes ``allow_undetermined=True``, in which case those knobs get no value
                     and the determined combinations are reported instead.

The ``simmodel`` sort (a ``dict``)
---------------------------------
``sort="simmodel"`` · ``name`` · ``scene`` (the first step's input, or ``None``) · ``chain``
(list of ``{"op", "args"}``; ``op`` is a registered fullseye op name or a built-in
``stage:*``) · ``conditions`` (list of ``{step index: {arg: value}}``, one output image each)
· ``knobs`` (list of dicts: ``name, step, arg, lo, hi, unit, scale, init, prior, role,
fixed``) · ``nuisance`` · ``noise`` · ``stochastic`` · ``observed`` (``None`` until
:func:`simcal_observe`) · ``output_shapes``.

The ``calresult`` sort (a ``dict``)
----------------------------------
``sort="calresult"`` · ``status`` (``accepted`` / ``partial`` / ``refused``) · ``theta_hat``
(only the knobs the data determined, natural units) · ``units`` · ``scale`` · ``fixed`` ·
``undetermined`` (knob -> reason) · ``determined_combos`` · ``refusals`` · ``fit`` ·
``errors`` (train / holdout / locked reduced chi-square) · ``residual_maps`` · ``data_range``
· ``model`` · ``diagnostics`` (the optimiser end point, explicitly labelled as *not* an
estimate) · ``identifiability`` / ``uncertainty`` / ``validation`` / ``discrepancy``
(filled by the checking ops).

Noise model
-----------
``{"kind": "gaussian", "sigma": s}`` (DN), or the EMVA 1288 temporal noise of a linear camera
``{"kind": "emva", "K": K, "sigma_d": sigma_d, "dark": mu_dark}`` with

    sigma_y^2 = K^2 sigma_d^2 + sigma_q^2 + K (mu_y - mu_y.dark),   sigma_q^2 = 1/12 DN^2

(the denominator of the SNR of EMVA 1288 Release 4.0 Linear eq. 21 multiplied by K^2 — the
same model ``sensorchar.emva_snr_curve`` evaluates; the tests check the two agree). ``dark``
may name a knob (the offset is then the dark level). A result of
``sensorchar.emva_photon_transfer`` plus ``"dark"`` is accepted; when its ``sigma_d`` was not
estimable, the upper limit ``sigma_d_upper`` is used (wider, never narrower, noise).
Without a noise model, the fit is refused: "how far is far" is undefined.

Stochastic forward models (the port for Monte-Carlo renderers)
---------------------------------------------------------------
``stochastic={"seed": s, "sample_var": v, "n_rep": n}``: every chain step that takes a
``seed`` argument receives ``s`` (common random numbers — the Jacobian of a Monte-Carlo model
is otherwise destroyed by sampling noise), and the model's own sample variance is added to the
camera noise variance (``v`` a number, or ``"estimate"`` = per-pixel variance over ``n``
seeds at the initial knobs). Leaving it out makes the residuals look structured and the
over-fitting gates misfire.

Provenance: Levenberg 1944, Q. Appl. Math. 2:164; Marquardt 1963, J. SIAM 11(2):431 (damped
normal equations with lambda diag(J^T J)); Nelder & Mead 1965, Comput. J. 7(4):308; Kennedy &
O'Hagan 2001, J. R. Stat. Soc. B 63(3):425 (calibration with model discrepancy, the framing);
Brun, Reichert & Künsch 2001, Water Resour. Res. 37(4):1015; Morris 1991; Saltelli et al. 2010;
EMVA 1288 Release 4.0 Linear (noise model); McCullagh & Nelder 1989 (iteratively re-weighted
least squares = quasi-likelihood estimating equation, unbiased for a mean-dependent variance).
"""
from __future__ import annotations

import copy
import inspect
import math

import numpy as np

import doe as _doe
from metriccontract import MetricContractError, attempt, best_of

__all__ = ["simcal_model", "simcal_simulate", "simcal_observe", "simcal_screen", "simcal_fit"]

SIGMA_Q2 = 1.0 / 12.0           # quantisation noise variance [DN^2] (EMVA 1288; same as sensorchar.SIGMA_Q2)
CHI2_1_95 = 3.841458820694124   # chi-square, 1 degree of freedom, 95 % (scipy.stats.chi2.ppf(0.95, 1))
EDGE_FRACTION = 0.01            # a knob within 1 % of its range end is "pinned to the edge" (design note §5)
MAX_PIXELS = 4_000_000
MAX_KNOBS = 32
_RNG_SEED_DEMO = 20261015


# --------------------------------------------------------------------------- #
# built-in stages (forward pieces that are not ops of their own)             #
# --------------------------------------------------------------------------- #
def _radius(shape, cx, cy):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    cx = (w - 1) / 2.0 if cx is None else float(cx)
    cy = (h - 1) / 2.0 if cy is None else float(cy)
    return np.hypot(xx - cx, yy - cy)


def _img2(x, stage):
    a = np.asarray(x, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError("%s: needs a 2-D image, got shape %s" % (stage, a.shape))
    return a


def _st_gain_offset(x, gain=1.0, offset=0.0):
    """y = gain * x + offset (the linear camera response in DN)."""
    return float(gain) * np.asarray(x, dtype=np.float64) + float(offset)


def _st_scale(x, factor=1.0):
    """y = factor * x (an illumination level, a transmittance ...)."""
    return float(factor) * np.asarray(x, dtype=np.float64)


def _st_radial_cos4(x, f=100.0, cx=None, cy=None):
    """Natural vignetting of a thin lens: x * cos^4(atan(r / f)) = x / (1 + (r/f)^2)^2, f in pixels."""
    a = _img2(x, "stage:radial_cos4")
    f = float(f)
    if not f > 0:
        raise ValueError("stage:radial_cos4: f must be > 0, got %r" % f)
    r = _radius(a.shape, cx, cy)
    return a / (1.0 + (r / f) ** 2) ** 2


def _st_radial_poly(x, c1=0.0, c2=0.0, c3=0.0, c4=0.0, c5=0.0, c6=0.0, c7=0.0, c8=0.0,
                    cx=None, cy=None, r_norm=None):
    """x * (1 + sum_k c_k rho^k), rho = r / r_norm (default: the half diagonal) — a polynomial fall-off."""
    a = _img2(x, "stage:radial_poly")
    r = _radius(a.shape, cx, cy)
    rn = float(np.hypot(*a.shape)) / 2.0 if r_norm is None else float(r_norm)
    rho = r / rn
    v = np.ones_like(a)
    for k, c in enumerate((c1, c2, c3, c4, c5, c6, c7, c8), start=1):
        if c:
            v = v + float(c) * rho ** k
    return a * v


def _st_gaussian_blur(x, sigma=1.0):
    """Gaussian PSF of standard deviation ``sigma`` pixels (0 = no blur), edges replicated."""
    a = _img2(x, "stage:gaussian_blur")
    s = float(sigma)
    if s < 0 or not math.isfinite(s):
        raise ValueError("stage:gaussian_blur: sigma must be >= 0, got %r" % sigma)
    if s == 0:
        return a.copy()
    from scipy.ndimage import gaussian_filter
    return gaussian_filter(a, s, mode="nearest", truncate=5.0)


def _st_as_image(x, shape=None):
    """A scalar -> a constant image of ``shape``; a 1-D spectrum -> a (1, n) row; 2-D unchanged."""
    a = np.asarray(x, dtype=np.float64)
    if a.size == 1 and shape is not None:
        return np.full(tuple(int(s) for s in shape), float(a.ravel()[0]))
    if a.ndim <= 1:
        return a.reshape(1, -1)
    return a


def _st_mc_sample(x, n_samples=64, seed=0):
    """A Monte-Carlo estimate of x: x + sqrt(x / n_samples) z, z ~ N(0, 1) drawn from ``seed`` (unbiased)."""
    a = np.asarray(x, dtype=np.float64)
    n = float(n_samples)
    if not n > 0:
        raise ValueError("stage:mc_sample: n_samples must be > 0")
    z = np.random.default_rng(int(seed)).standard_normal(a.shape)
    return a + np.sqrt(np.maximum(a, 0.0) / n) * z


_STAGES = {
    "stage:gain_offset": _st_gain_offset,
    "stage:scale": _st_scale,
    "stage:radial_cos4": _st_radial_cos4,
    "stage:radial_poly": _st_radial_poly,
    "stage:gaussian_blur": _st_gaussian_blur,
    "stage:as_image": _st_as_image,
    "stage:mc_sample": _st_mc_sample,
}

_REGISTRY_CACHE: dict = {}


def _resolve(name, op):
    """A chain step's op name -> callable (built-in stage, or any op of the typed catalogue)."""
    if callable(name):
        return name
    if not isinstance(name, str) or not name:
        raise ValueError("%s: a chain step needs an op name, got %r" % (op, name))
    if name in _STAGES:
        return _STAGES[name]
    if not _REGISTRY_CACHE:
        import typed_catalog                                         # lazy: the catalogue imports this module
        for row in typed_catalog.catalog():
            _REGISTRY_CACHE.setdefault(row[0], row[4])
    fn = _REGISTRY_CACHE.get(name)
    if fn is None:
        raise ValueError("%s: unknown op %r in the chain (a registered fullseye op or one of %s)"
                         % (op, name, sorted(_STAGES)))
    return fn


def _accepts(fn, arg):
    try:
        ps = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return True
    return arg in ps or any(p.kind == p.VAR_KEYWORD for p in ps.values())


# --------------------------------------------------------------------------- #
# validation helpers                                                          #
# --------------------------------------------------------------------------- #
def _num(v, name, op, lo=-math.inf, hi=math.inf, lo_open=False):
    if isinstance(v, bool) or not isinstance(v, (int, float, np.integer, np.floating)):
        raise ValueError("%s: %s must be a number, got %r" % (op, name, v))
    v = float(v)
    if not math.isfinite(v) or v < lo or v > hi or (lo_open and v <= lo):
        raise ValueError("%s: %s must be in %s%g..%g, got %r" % (op, name, "(" if lo_open else "[", lo, hi, v))
    return v


def _check_model(model, op, need_observed=False, need_noise=False):
    if not isinstance(model, dict) or model.get("sort") != "simmodel":
        raise ValueError("%s: expected a simmodel (dict with sort='simmodel' from simcal_model), got %s"
                         % (op, type(model).__name__))
    for key in ("chain", "knobs", "conditions", "output_shapes"):
        if key not in model:
            raise ValueError("%s: simmodel is missing %r" % (op, key))
    if need_observed and not model.get("observed"):
        raise MetricContractError("%s: the simmodel has no observed images — attach them with simcal_observe first"
                                  % op)
    if need_noise and not model.get("noise"):
        raise MetricContractError("%s: the simmodel has no noise model — without the noise variance there is no "
                                  "scale on which a knob is 'determined' (pass noise= to simcal_model, e.g. from "
                                  "sensorchar.emva_photon_transfer)" % op)
    return model


def _knob_spec(knobs):
    return [{"name": k["name"], "lo": k["lo"], "hi": k["hi"], "unit": k["unit"], "scale": k["scale"]}
            for k in knobs]


def _to_u(theta, k):
    lo, hi = k["lo"], k["hi"]
    if k["scale"] == "log":
        return math.log(theta / lo) / math.log(hi / lo)
    return (theta - lo) / (hi - lo)


def _from_u(u, k):
    lo, hi = k["lo"], k["hi"]
    if k["scale"] == "log":
        return lo * (hi / lo) ** u
    return lo + u * (hi - lo)


def _du_dphi(k):
    """d u / d phi with phi = ln(theta) for a log knob, theta for a linear one."""
    if k["scale"] == "log":
        return 1.0 / math.log(k["hi"] / k["lo"])
    return 1.0 / (k["hi"] - k["lo"])


def _du_dtheta(theta, k):
    if k["scale"] == "log":
        return 1.0 / (theta * math.log(k["hi"] / k["lo"]))
    return 1.0 / (k["hi"] - k["lo"])


def _init_values(model):
    return {k["name"]: (k["fixed"] if k.get("fixed") is not None else k["init"]) for k in model["knobs"]}


# --------------------------------------------------------------------------- #
# the forward run                                                             #
# --------------------------------------------------------------------------- #
def _run_chain(model, theta, cond_index, seed=None):
    knobs_by_step: dict = {}
    for k in model["knobs"]:
        knobs_by_step.setdefault(k["step"], {})[k["arg"]] = float(theta[k["name"]])
    cond = model["conditions"][cond_index] if model["conditions"] else {}
    st = model.get("stochastic") or None
    x = None if model.get("scene") is None else np.array(model["scene"], dtype=np.float64)
    for i, step in enumerate(model["chain"]):
        fn = _resolve(step["op"], "simcal_simulate")
        kw = dict(step.get("args") or {})
        kw.update(cond.get(i, {}))
        kw.update(knobs_by_step.get(i, {}))
        if st is not None and _accepts(fn, "seed") and "seed" not in (step.get("args") or {}):
            kw["seed"] = int(st["seed"] if seed is None else seed) + 1000 * cond_index
        x = fn(**kw) if (x is None and i == 0) else fn(x, **kw)
    out = np.asarray(x, dtype=np.float64)
    if out.ndim == 0:
        out = out.reshape(1, 1)
    elif out.ndim == 1:
        out = out[None, :]
    if out.ndim != 2:
        raise ValueError("simcal_simulate: the chain must end in a 2-D array (or a scalar / 1-D signal), "
                         "got shape %s" % (out.shape,))
    return out


def _simulate(model, theta, seed=None):
    n = max(1, len(model["conditions"]))
    out = []
    for c in range(n):
        y = _run_chain(model, theta, c, seed)
        if not np.isfinite(y).all():
            raise MetricContractError("simcal_simulate: the chain returned NaN or inf at %s (condition %d)"
                                      % ({k: round(v, 6) for k, v in theta.items()}, c))
        out.append(y)
    return out


# --------------------------------------------------------------------------- #
# noise model                                                                 #
# --------------------------------------------------------------------------- #
def _norm_noise(noise, knob_names, op):
    if noise is None:
        return None
    if not isinstance(noise, dict):
        raise ValueError("%s: noise must be a dict, got %r" % (op, noise))
    kind = noise.get("kind")
    if kind is None and "K" in noise:                                 # a sensorchar.emva_photon_transfer result
        kind = "emva"
    if kind == "gaussian":
        return {"kind": "gaussian", "sigma": _num(noise.get("sigma"), "noise sigma", op, 0.0, lo_open=True)}
    if kind == "emva":
        K = _num(noise.get("K"), "noise K", op, 0.0, lo_open=True)
        sd = noise.get("sigma_d")
        source = "sigma_d"
        if sd is None and noise.get("sigma_d_upper") is not None:
            sd, source = noise["sigma_d_upper"], "sigma_d_upper (EMVA eq. 54: sigma_d not estimable, upper limit used)"
        sd = _num(sd, "noise sigma_d", op, 0.0)
        dark = noise.get("dark")
        if isinstance(dark, str):
            if dark not in knob_names:
                raise ValueError("%s: noise dark %r is not a knob name (%s)" % (op, dark, knob_names))
        else:
            dark = _num(dark, "noise dark", op)
        return {"kind": "emva", "K": K, "sigma_d": sd, "dark": dark, "sigma_d_source": source}
    raise ValueError("%s: noise kind must be 'gaussian' or 'emva' (or a sensorchar.emva_photon_transfer result "
                     "with 'dark'), got %r" % (op, kind))


def _camera_var(model, mu, theta):
    nz = model["noise"]
    if nz["kind"] == "gaussian":
        return np.full_like(mu, nz["sigma"] ** 2)
    dark = theta[nz["dark"]] if isinstance(nz["dark"], str) else nz["dark"]
    return nz["K"] ** 2 * nz["sigma_d"] ** 2 + SIGMA_Q2 + nz["K"] * np.maximum(mu - dark, 0.0)


def _variances(model, mus, theta):
    obs = model.get("observed") or {}
    scales = obs.get("var_scale") or [1.0] * len(mus)
    sv = (model.get("stochastic") or {}).get("sample_var_maps")
    out = []
    for c, mu in enumerate(mus):
        v = _camera_var(model, mu, theta) * scales[c]
        if sv is not None:
            v = v + sv[c]
        out.append(np.maximum(v, 1e-12))
    return out


# --------------------------------------------------------------------------- #
# simcal_model                                                                #
# --------------------------------------------------------------------------- #
def _chart(n=24):
    """A deterministic test chart: bars and a disc on a mid-grey ground (values 0.25..1)."""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    img = np.full((n, n), 0.55)
    img[:, : n // 3] = 0.25 + 0.75 * ((xx[:, : n // 3] // 2) % 2)
    img[np.hypot(xx - 0.68 * n, yy - 0.5 * n) < n / 5.0] = 1.0
    img[: n // 4, n // 3:] = 0.35
    return img


def _demo_spec():
    return dict(
        chain=[{"op": "stage:radial_cos4"}, {"op": "stage:gain_offset"}],
        knobs=[{"name": "f", "step": 0, "arg": "f", "lo": 10.0, "hi": 60.0, "unit": "px", "init": 30.0},
               {"name": "gain", "step": 1, "arg": "gain", "lo": 200.0, "hi": 2000.0, "unit": "DN",
                "scale": "log", "init": 600.0},
               {"name": "offset", "step": 1, "arg": "offset", "lo": 20.0, "hi": 200.0, "unit": "DN",
                "init": 100.0}],
        scene=_chart(),
        nuisance=["offset"],
        noise={"kind": "emva", "K": 0.5, "sigma_d": 6.0, "dark": "offset"},
        name="demo: chart -> cos^4 vignetting -> gain/offset")


def _physical_capture(mu, offset, K, sigma_d, rng):
    """Synthetic raw capture by the physical path (not the variance formula): Poisson electrons, read noise, rounding."""
    e = rng.poisson(np.maximum(mu - offset, 0.0) / K)
    return np.round(K * (e + sigma_d * rng.standard_normal(mu.shape)) + offset)


def simcal_model(chain=None, knobs=None, scene=None, nuisance=None, noise=None, conditions=None,
                 stochastic=None, label="model") -> dict:
    """Build a ``simmodel``: a forward chain of ops whose arguments are knobs with units, ranges and a noise model.

    ``chain`` — list of steps ``{"op": name, "args": {...}}``; ``op`` is any registered fullseye
    op (e.g. ``"thin_film_reflectance"``) or a built-in stage (``"stage:gain_offset"``,
    ``"stage:scale"``, ``"stage:radial_cos4"``, ``"stage:radial_poly"``,
    ``"stage:gaussian_blur"``, ``"stage:as_image"``, ``"stage:mc_sample"``). Step 0 receives
    ``scene`` as its first argument (or nothing when ``scene`` is ``None``), each later step
    the previous output.

    ``knobs`` — list of dicts ``{"name", "step" (index or op name), "arg", "lo", "hi", "unit",
    "scale" ("linear" | "log"), "init", "prior" ((mean, sd) or None), "role" ("gain" |
    "offset" | None), "fixed" (value or None)}``. A knob is bound to one argument of one
    step; ``init`` defaults to the middle of the range (geometric middle on a log scale).

    ``conditions`` — optional list of ``{step: {arg: value}}`` (one output image per
    condition: exposures, wavelengths, illumination angles). ``nuisance`` — names of knobs
    that are fitted but not of interest; ``label`` names the model in reports. ``noise`` / ``stochastic`` — see the module
    docstring.

    The model is run once at the initial knobs and refused (``ValueError``) when a step is
    unknown, a knob names an argument its op does not take, two knobs bind the same
    argument, a range is empty or a log range is not positive, or the output is not a finite
    2-D array. With no arguments: a demo model (chart -> cos^4 vignetting -> gain/offset, EMVA
    noise) **with synthetic observations attached**, ready for :func:`simcal_fit`.
    """
    op = "simcal_model"
    demo = chain is None and knobs is None
    if demo:
        spec = _demo_spec()
        chain, knobs, scene = spec["chain"], spec["knobs"], spec["scene"]
        nuisance, noise, label = spec["nuisance"], spec["noise"], spec["name"]
    if not isinstance(chain, (list, tuple)) or not chain:
        raise ValueError("%s: chain must be a non-empty list of steps" % op)
    steps = []
    for i, s in enumerate(chain):
        if isinstance(s, str):
            s = {"op": s}
        if not isinstance(s, dict) or "op" not in s:
            raise ValueError("%s: step %d must be {'op': name, 'args': {...}}, got %r" % (op, i, s))
        args = dict(s.get("args") or {})
        _resolve(s["op"], op)
        steps.append({"op": s["op"], "args": args})
    names_by_op = {}
    for i, s in enumerate(steps):
        names_by_op.setdefault(s["op"] if isinstance(s["op"], str) else repr(s["op"]), i)
    if not isinstance(knobs, (list, tuple)) or not knobs:
        raise ValueError("%s: knobs must be a non-empty list" % op)
    if len(knobs) > MAX_KNOBS:
        raise ValueError("%s: %d knobs (cap %d)" % (op, len(knobs), MAX_KNOBS))
    out_knobs, seen, bound = [], set(), set()
    for j, kd in enumerate(knobs):
        if not isinstance(kd, dict):
            raise ValueError("%s: knob %d must be a dict" % (op, j))
        nm = str(kd.get("name", ""))
        if not nm or nm in seen:
            raise ValueError("%s: knob %d needs a unique name, got %r" % (op, j, nm))
        seen.add(nm)
        st = kd.get("step", kd.get("op", 0))
        if isinstance(st, str):
            if st not in names_by_op:
                raise ValueError("%s: knob %r refers to op %r which is not in the chain" % (op, nm, st))
            st = names_by_op[st]
        st = _doe._int_arg(st, "knob %r step" % nm, op, 0, len(steps) - 1)
        arg = str(kd.get("arg") or nm)
        if not _accepts(_resolve(steps[st]["op"], op), arg):
            raise ValueError("%s: knob %r binds argument %r, which op %r does not take"
                             % (op, nm, arg, steps[st]["op"]))
        if (st, arg) in bound:
            raise ValueError("%s: two knobs bind the same argument %r of step %d" % (op, arg, st))
        bound.add((st, arg))
        spec = _doe._factor_spec([{"name": nm, "lo": kd.get("lo"), "hi": kd.get("hi"),
                                   "unit": kd.get("unit"), "scale": kd.get("scale")}], op)
        lo, hi, sc = float(spec["lo"][0]), float(spec["hi"][0]), spec["scale"][0]
        k = {"name": nm, "step": st, "arg": arg, "lo": lo, "hi": hi, "unit": spec["units"][0], "scale": sc}
        init = kd.get("init")
        init = (math.sqrt(lo * hi) if sc == "log" else 0.5 * (lo + hi)) if init is None else \
            _num(init, "knob %r init" % nm, op, lo, hi)
        k["init"] = init
        pr = kd.get("prior")
        if pr is not None:
            try:
                pm, ps = float(pr[0]), float(pr[1])
            except (TypeError, ValueError, IndexError):
                raise ValueError("%s: knob %r prior must be (mean, sd)" % (op, nm)) from None
            if not (math.isfinite(pm) and math.isfinite(ps) and ps > 0):
                raise ValueError("%s: knob %r prior needs a finite mean and sd > 0" % (op, nm))
            pr = (pm, ps)
        k["prior"] = pr
        role = kd.get("role")
        if role is None and arg in ("gain", "offset"):
            role = arg
        if role not in (None, "gain", "offset"):
            raise ValueError("%s: knob %r role must be 'gain', 'offset' or None, got %r" % (op, nm, role))
        k["role"] = role
        fx = kd.get("fixed")
        k["fixed"] = None if fx is None else _num(fx, "knob %r fixed" % nm, op, lo, hi)
        out_knobs.append(k)
    knames = [k["name"] for k in out_knobs]
    nuis = [str(n) for n in (nuisance or [])]
    for n in nuis:
        if n not in knames:
            raise ValueError("%s: nuisance %r is not a knob (%s)" % (op, n, knames))
    conds = []
    for c, cd in enumerate(conditions or []):
        if not isinstance(cd, dict):
            raise ValueError("%s: condition %d must be {step: {arg: value}}" % (op, c))
        nc = {}
        for key, av in cd.items():
            si = names_by_op.get(key) if isinstance(key, str) else key
            if si is None:
                raise ValueError("%s: condition %d refers to %r, not in the chain" % (op, c, key))
            si = _doe._int_arg(si, "condition step", op, 0, len(steps) - 1)
            if not isinstance(av, dict):
                raise ValueError("%s: condition %d step %r must map to {arg: value}" % (op, c, key))
            nc[si] = dict(av)
        conds.append(nc)
    sto = None
    if stochastic is not None:
        if not isinstance(stochastic, dict):
            raise ValueError("%s: stochastic must be a dict {'seed', 'sample_var', 'n_rep'}" % op)
        sto = {"seed": _doe._int_arg(stochastic.get("seed", 0), "stochastic seed", op, 0, 2 ** 31 - 1),
               "n_rep": _doe._int_arg(stochastic.get("n_rep", 16), "stochastic n_rep", op, 2, 10000),
               "sample_var": stochastic.get("sample_var")}
        sv = sto["sample_var"]
        if sv is not None and sv != "estimate":
            sto["sample_var"] = _num(sv, "stochastic sample_var", op, 0.0)
    model = {"sort": "simmodel", "name": str(label), "scene": None if scene is None else np.array(scene, float),
             "chain": steps, "conditions": conds, "knobs": out_knobs, "nuisance": nuis,
             "noise": _norm_noise(noise, knames, op), "stochastic": sto, "observed": None, "output_shapes": []}
    try:
        ys = _simulate(model, _init_values(model))
    except MetricContractError:
        raise
    except (TypeError, ValueError) as e:
        raise ValueError("%s: the chain does not run at the initial knobs: %s" % (op, e)) from None
    if sum(y.size for y in ys) > MAX_PIXELS:
        raise ValueError("%s: the model outputs %d values (cap %d)" % (op, sum(y.size for y in ys), MAX_PIXELS))
    model["output_shapes"] = [tuple(int(s) for s in y.shape) for y in ys]
    if sto is not None:
        if sto["sample_var"] == "estimate":
            reps = [_simulate(model, _init_values(model), seed=sto["seed"] + 7919 * (r + 1))
                    for r in range(sto["n_rep"])]
            sto["sample_var_maps"] = [np.var(np.stack([rp[c] for rp in reps]), axis=0, ddof=1)
                                      for c in range(len(ys))]
        elif sto["sample_var"] is not None:
            sto["sample_var_maps"] = [np.full(y.shape, float(sto["sample_var"])) for y in ys]
        else:
            sto["sample_var_maps"] = None
    if demo:
        truth = {"f": 22.0, "gain": 900.0, "offset": 64.0}
        rng = np.random.default_rng(_RNG_SEED_DEMO)
        imgs = [_physical_capture(y, truth["offset"], 0.5, 6.0, rng) for y in _simulate(model, truth)]
        model = _observe(model, imgs, None, False, None, 8, "train", "simcal_model")
        model["truth"] = truth
    return model


# --------------------------------------------------------------------------- #
# simcal_simulate                                                             #
# --------------------------------------------------------------------------- #
def _theta_arg(model, theta, op):
    vals = _init_values(model)
    if theta is None:
        return vals
    if isinstance(theta, dict) and theta.get("sort") == "calresult":
        theta = theta.get("theta_hat") or {}
    if not isinstance(theta, dict):
        raise ValueError("%s: theta must be a dict {knob: value}, got %r" % (op, type(theta).__name__))
    names = {k["name"]: k for k in model["knobs"]}
    for n, v in theta.items():
        if n not in names:
            raise ValueError("%s: %r is not a knob of the model (%s)" % (op, n, sorted(names)))
        vals[n] = _num(v, "theta[%r]" % n, op)
    return vals


def simcal_simulate(model=None, theta=None, seed=None) -> list:
    """Run a simmodel's chain at given knob values -> one 2-D array per condition (``images``).

    ``theta`` is ``{knob: value}`` in natural units (missing knobs take their initial or fixed
    value; a ``calresult`` is accepted and its ``theta_hat`` used). Values outside a knob's
    range are allowed here (a simulation is not a fit). ``seed`` overrides the common-random-
    number seed of a stochastic model (``None`` = the model's own). Refuses an unknown knob
    name or a non-finite output.
    """
    op = "simcal_simulate"
    model = simcal_model() if model is None else model
    _check_model(model, op)
    vals = _theta_arg(model, theta, op)
    if seed is not None:
        seed = _doe._int_arg(seed, "seed", op, 0, 2 ** 31 - 1)
    return _simulate(model, vals, seed)


# --------------------------------------------------------------------------- #
# simcal_observe                                                              #
# --------------------------------------------------------------------------- #
def _roi_mask(roi, shape, op):
    if roi is None:
        return np.ones(shape, dtype=bool)
    if isinstance(roi, np.ndarray) and roi.dtype == bool:
        if roi.shape != shape:
            raise ValueError("%s: ROI mask shape %s differs from the image %s" % (op, roi.shape, shape))
        return roi.copy()
    try:
        r0, r1, c0, c1 = (int(v) for v in roi)
    except (TypeError, ValueError):
        raise ValueError("%s: roi must be a boolean mask or (row0, row1, col0, col1)" % op) from None
    if not (0 <= r0 < r1 <= shape[0] and 0 <= c0 < c1 <= shape[1]):
        raise ValueError("%s: roi %r outside the image %s" % (op, roi, shape))
    m = np.zeros(shape, dtype=bool)
    m[r0:r1, c0:c1] = True
    return m


def _observe(model, images, roi, align, exposure, max_shift, split, op):
    from multivar import _images                                      # reuse the image-list validator
    shapes = model["output_shapes"]
    if isinstance(images, np.ndarray) and images.ndim == 2:
        images = [images]
    seq = []
    for i, im in enumerate(list(images) if not isinstance(images, np.ndarray) else list(images)):
        a = np.asarray(im, dtype=np.float64)
        if a.ndim == 1:
            a = a[None, :]
        seq.append(a)
    if len(seq) != len(shapes):
        raise ValueError("%s: %d images for %d conditions" % (op, len(seq), len(shapes)))
    for i, (a, s) in enumerate(zip(seq, shapes)):
        if a.shape != s:
            raise ValueError("%s: image %d has shape %s, the model outputs %s" % (op, i, a.shape, s))
        if not np.isfinite(a).all():
            raise ValueError("%s: image %d contains NaN or inf" % (op, i))
    if all(min(s) >= 3 for s in shapes):
        seq = _images(seq, op)
    if split not in ("train", "holdout", "locked"):
        raise ValueError("%s: split must be 'train', 'holdout' or 'locked', got %r" % (op, split))
    gain_knobs = [k["name"] for k in model["knobs"] if k.get("role") == "gain" and k.get("fixed") is None]
    if exposure is not None:
        ex = [float(e) for e in (exposure if hasattr(exposure, "__iter__") else [exposure] * len(seq))]
        if len(ex) != len(seq) or not all(math.isfinite(e) and e > 0 for e in ex):
            raise ValueError("%s: exposure must be one positive factor per image" % op)
        if gain_knobs:
            raise MetricContractError(
                "%s: exposure normalisation together with the gain knob(s) %s is refused — both scale the "
                "signal, so the fit cannot tell them apart and the normalised noise would be counted twice; "
                "either fix the gain or pass the raw images and put the exposure in the conditions"
                % (op, gain_knobs))
    else:
        ex = [1.0] * len(seq)
    masks, shifts = [], []
    ref = _simulate(model, _init_values(model)) if align else None
    ms = _doe._int_arg(max_shift, "max_shift", op, 0, 4096)
    out = []
    for i, a in enumerate(seq):
        m = _roi_mask(roi, a.shape, op)
        dr = dc = 0
        if align and min(a.shape) >= 8:
            from filters_freq import phase_correlation_fft             # reuse: integer-pixel registration
            pc = phase_correlation_fft(ref[i], a)
            # phase_correlation_fft returns the move that brings ref onto the image, with the sign convention
            # "image = np.roll(ref, d) -> (-d)"; the image's own displacement is therefore the negative
            dr, dc = -int(pc["row_shift"]), -int(pc["col_shift"])
            if abs(dr) > ms or abs(dc) > ms:
                raise MetricContractError("%s: image %d is shifted by (%d, %d) px, beyond max_shift=%d — refusing "
                                          "to align by that much (wrong image or wrong model?)" % (op, i, dr, dc, ms))
            a = np.roll(a, (-dr, -dc), axis=(0, 1))
            valid = np.ones(a.shape, dtype=bool)
            if dr > 0:
                valid[-dr:, :] = False
            elif dr < 0:
                valid[:-dr, :] = False
            if dc > 0:
                valid[:, -dc:] = False
            elif dc < 0:
                valid[:, :-dc] = False
            m &= valid
        if m.sum() < 1:
            raise ValueError("%s: image %d has no valid pixel after ROI/alignment" % (op, i))
        out.append(a / ex[i])
        masks.append(m)
        shifts.append((dr, dc))
    obs_all = np.concatenate([o[m] for o, m in zip(out, masks)])
    new = copy.deepcopy(model)
    new["observed"] = {"images": out, "mask": masks, "var_scale": [1.0 / e ** 2 for e in ex],
                       "exposure": ex, "shifts": shifts, "aligned": bool(align), "max_shift": ms, "split": split,
                       "roi": None if roi is None or isinstance(roi, np.ndarray) else list(roi),
                       "n_pixels": int(sum(int(m.sum()) for m in masks)),
                       "data_range": [float(obs_all.min()), float(obs_all.max())]}
    return new


def simcal_observe(model=None, images=None, roi=None, align=False, exposure=None, max_shift=8,
                   split="train") -> dict:
    """Attach measured images to a simmodel: alignment, region of interest and exposure normalisation.

    ``images`` — one 2-D array per condition (shape = what the model outputs). ``align=True``
    registers each image to the simulation at the initial knobs by phase correlation
    (``filters_freq.phase_correlation_fft``, integer pixels), shifts it back and masks the
    wrapped border; a shift larger than ``max_shift`` is refused. ``roi`` = boolean mask or
    ``(row0, row1, col0, col1)``. ``exposure`` = a factor per image to divide by (the noise
    variance is divided by its square) — **refused when the model has a free gain knob**: the
    two scale the same signal. ``split`` labels the data ``train`` / ``holdout`` / ``locked``
    (the TRAIN / OBSERVED / LOCKED discipline of ``robust.py``). Returns a new simmodel with
    ``observed`` filled (the input is not modified), including ``data_range``.
    """
    op = "simcal_observe"
    if model is None:
        model = simcal_model()
        images = model["observed"]["images"] if images is None else images
    _check_model(model, op)
    if images is None:
        raise ValueError("%s: images is required" % op)
    if isinstance(images, (list, tuple)) and len(images) == 0:
        raise ValueError("%s: images is empty" % op)
    return _observe(model, images, roi, bool(align), exposure, max_shift, split, op)


# --------------------------------------------------------------------------- #
# residuals, Jacobian, LM                                                     #
# --------------------------------------------------------------------------- #
class _Problem:
    """Residual machinery for one observed simmodel: knobs in u in [0, 1], whitened residuals."""

    def __init__(self, model, fix=None, seed=None):
        self.model = model
        self.knobs = model["knobs"]
        fix = dict(fix or {})
        self.fixed = {}
        for k in self.knobs:
            if k["name"] in fix:
                self.fixed[k["name"]] = float(fix[k["name"]])
            elif k.get("fixed") is not None:
                self.fixed[k["name"]] = float(k["fixed"])
        self.free = [k for k in self.knobs if k["name"] not in self.fixed]
        obs = model["observed"]
        self.masks = obs["mask"]
        self.y = np.concatenate([im[m] for im, m in zip(obs["images"], self.masks)])
        self.seed = seed
        self.n_eval = 0

    def theta(self, u):
        th = {k["name"]: k["init"] for k in self.knobs}
        th.update(self.fixed)
        for j, k in enumerate(self.free):
            th[k["name"]] = _from_u(float(u[j]), k)
        return th

    def mu(self, u):
        self.n_eval += 1
        th = self.theta(u)
        sims = _simulate(self.model, th, self.seed)
        return sims, th

    def flat(self, sims):
        return np.concatenate([s[m] for s, m in zip(sims, self.masks)])

    def weights(self, sims, th):
        v = _variances(self.model, sims, th)
        return 1.0 / np.sqrt(self.flat(v))

    def resid(self, u, sw):
        sims, th = self.mu(u)
        return (self.y - self.flat(sims)) * sw, sims, th

    def jac(self, u, sw, h=1e-5):
        J = np.empty((self.y.size, len(self.free)))
        for j in range(len(self.free)):
            up, um = u.copy(), u.copy()
            a, b = min(h, 1.0 - u[j]), min(h, u[j])
            if a <= 0 and b <= 0:
                J[:, j] = 0.0
                continue
            up[j] += a
            um[j] -= b
            fp = self.flat(self.mu(up)[0])
            fm = self.flat(self.mu(um)[0])
            J[:, j] = -(fp - fm) / (a + b) * sw                     # d residual / d u
        return J


def _lm(P, u0, max_iter=200, tol=1e-10, sw_fixed=None):
    """Levenberg-Marquardt with re-weighting (IRLS) in the unit box; out-of-box steps are rejected.

    ``sw_fixed`` (whitening weights) switches re-weighting off — the profile likelihood compares
    chi^2 values on one fixed scale.
    """
    u = np.clip(np.asarray(u0, dtype=np.float64), 0.0, 1.0)
    sims, th = P.mu(u)
    sw = P.weights(sims, th) if sw_fixed is None else sw_fixed
    r = (P.y - P.flat(sims)) * sw
    chi = float(r @ r)
    lam, small, status, it = 1e-3, 0, "iterations", 0
    history = [chi]
    if not P.free:
        return {"u": u, "chi2": chi, "iterations": 0, "status": "no_free_knobs", "converged": True,
                "history": history, "sw": sw, "damping": lam}
    for it in range(1, max_iter + 1):
        J = P.jac(u, sw)
        A, g = J.T @ J, J.T @ r
        d = np.diag(A).copy()
        d[d <= 0] = 1e-12
        accepted = False
        delta = np.zeros_like(u)
        # active set: a knob sitting on a range end whose descent direction points outward is held there
        act = ((u <= 1e-12) & (g > 0)) | ((u >= 1.0 - 1e-12) & (g < 0))
        free = ~act
        for _ in range(12):
            delta = np.zeros_like(u)
            try:
                Af = A[np.ix_(free, free)] + lam * np.diag(d[free])
                delta[free] = np.linalg.solve(Af, -g[free]) if free.any() else 0.0
            except np.linalg.LinAlgError:
                lam *= 4.0
                continue
            un = u + delta
            if (un < 0.0).any() or (un > 1.0).any():
                # the raw step leaves the range: it is not taken. Its projection onto the range is tried
                # instead (lensopt clamps bounded variables the same way); a forward model that refuses the
                # point (MetricContractError) rejects the step and raises the damping.
                un = np.clip(un, 0.0, 1.0)
            try:
                rn, sims_n, th_n = P.resid(un, sw)
            except MetricContractError:
                lam *= 4.0
                continue
            chin = float(rn @ rn)
            if math.isfinite(chin) and chin < chi:
                rel = (chi - chin) / max(chi, 1e-300)
                u, sims, th = un, sims_n, th_n
                lam = max(lam / 3.0, 1e-12)
                accepted = True
                small = small + 1 if (rel < tol or np.abs(delta).max() < 1e-9) else 0
                break
            lam *= 4.0
        # re-weight at the current prediction (quasi-likelihood fixed point)
        if sw_fixed is None:
            sw = P.weights(sims, th)
        r = (P.y - P.flat(sims)) * sw
        chi = float(r @ r)
        history.append(chi)
        if not accepted:
            # no decrease possible: converged if the Gauss-Newton predicted decrease is negligible
            try:
                pred = float(g @ np.linalg.lstsq(A + 1e-12 * np.diag(d), g, rcond=None)[0])
            except np.linalg.LinAlgError:
                pred = math.inf
            if pred <= 1e-8 * (1.0 + chi):
                status = "converged"
            else:
                status = "stalled"
            break
        if small >= 2:
            status = "converged"
            break
    return {"u": u, "chi2": chi, "iterations": it, "status": status, "converged": status == "converged",
            "history": history, "sw": sw, "damping": lam}


def _nelder_mead(P, u0, max_iter=400):
    """Nelder-Mead (Nelder & Mead 1965, scipy) on the unit box; a point outside the box scores the worst value."""
    from scipy.optimize import minimize
    import metriccontract as mc
    u0 = np.clip(np.asarray(u0, dtype=np.float64), 0.0, 1.0)
    sims, th = P.mu(u0)
    sw = P.weights(sims, th)
    if not P.free:
        return _lm(P, u0)

    def chi_of(u):
        if (u < 0).any() or (u > 1).any():
            raise MetricContractError("outside the knob range")
        rr = P.resid(u, sw)[0]
        return float(rr @ rr)

    def f(u):
        return mc.value_or_worst(attempt(chi_of, u, metric="simcal_chi2"))

    best = u0
    for _ in range(2):                                                # re-weight once at the first end point
        res = minimize(f, best, method="Nelder-Mead",
                       options={"maxiter": max_iter, "xatol": 1e-7, "fatol": 1e-9, "initial_simplex": None})
        best = np.clip(res.x, 0.0, 1.0)
        sims, th = P.mu(best)
        sw = P.weights(sims, th)
    r = (P.y - P.flat(sims)) * sw
    return {"u": best, "chi2": float(r @ r), "iterations": int(res.nit),
            "status": "converged" if res.success else "iterations", "converged": bool(res.success),
            "history": [float(res.fun)], "sw": sw, "damping": None}


# --------------------------------------------------------------------------- #
# diagnostics at an end point                                                 #
# --------------------------------------------------------------------------- #
def _fmt_combo(e, nrm, knobs):
    """A combination direction -> (text, natural weights).

    ``e`` is an eigenvector for unit-normalised sensitivity columns (dimensionless, so its entries
    say which knobs take part); the natural weight of knob j is ``e_j / nrm_j`` per ln(theta) for a
    log knob and per theta for a linear one. Terms with |e_j| < 5 % of the largest are dropped.
    All-log groups print as a product of powers (``n^1 * d^0.72``: the exponents are comparable),
    all-linear groups as a weighted sum, mixed groups as ``w*ln(name) + w*name``; weights are scaled
    so the term with the largest |e_j| has weight 1.
    """
    e = np.asarray(e, dtype=np.float64)
    nrm = np.where(np.asarray(nrm, dtype=np.float64) > 0, nrm, 1.0)
    lead = int(np.argmax(np.abs(e)))
    w = e / nrm
    w = w / w[lead]
    keep = [i for i in np.argsort(-np.abs(e), kind="stable") if abs(e[i]) > 0.05 * abs(e[lead])]
    logs = [i for i in keep if knobs[i]["scale"] == "log"]
    lins = [i for i in keep if knobs[i]["scale"] != "log"]
    if logs and not lins:
        text = " * ".join("%s^%.2g" % (knobs[i]["name"], w[i]) for i in logs)
    elif lins and not logs:
        text = " + ".join("%.3g*%s" % (w[i], knobs[i]["name"]) for i in lins)
    else:
        text = " + ".join(("%.3g*ln(%s)" if knobs[i]["scale"] == "log" else "%.3g*%s") % (w[i], knobs[i]["name"])
                          for i in keep)
    wn = np.zeros_like(w)
    wn[keep] = w[keep]
    return text, wn


def _combo_value(v, knobs, theta):
    """Value of a combination in natural units: product of powers over log knobs, weighted sum over linear ones."""
    out = {}
    lg = [i for i, k in enumerate(knobs) if k["scale"] == "log" and v[i] != 0]
    ln = [i for i, k in enumerate(knobs) if k["scale"] != "log" and v[i] != 0]
    if lg:
        out["product"] = float(math.exp(sum(v[i] * math.log(theta[knobs[i]["name"]]) for i in lg)))
    if ln:
        out["sum"] = float(sum(v[i] * theta[knobs[i]["name"]] for i in ln))
    return out


def _diagnose(P, u, sw, threshold):
    """Jacobian-based refusals at an end point: no influence, confounding (gamma_K), pinned to an edge."""
    import sensitivity
    J_u = P.jac(u, sw)
    knobs = P.free
    th = P.theta(u)
    scale = np.array([1.0 / _du_dphi(k) for k in knobs])               # d phi / d u
    J_phi = J_u / scale[None, :]                                        # sensitivities to ln(theta) or theta
    reasons, combos = {}, []
    names = [k["name"] for k in knobs]
    # no influence: move each knob alone to both ends of its range (the others held) and see whether chi^2 rises
    # by chi^2_1(95 %). Not the local derivative times the range: at a stationary point of the model (a blur of
    # sigma ~ 0, where the image changes with sigma^2) the derivative is 0 although the knob clearly matters.
    r0 = (P.y - P.flat(P.mu(u)[0])) * sw
    chi0 = float(r0 @ r0)
    for j, k in enumerate(knobs):
        rise = 0.0
        for end in (0.0, 1.0):
            ue = u.copy()
            ue[j] = end
            re = (P.y - P.flat(P.mu(ue)[0])) * sw
            rise = max(rise, float(re @ re) - chi0)
        if rise < CHI2_1_95:
            reasons[k["name"]] = ("no_influence: moving %s alone to either end of its range raises chi^2 by at most "
                                  "%.3g (< %.2f) — the images do not see this knob" % (k["name"], rise, CHI2_1_95))
    conf = None
    # columns with zero local sensitivity are left out (mv_confounding refuses a set with fewer than 2 live columns,
    # and a knob at a stationary point of the model, e.g. sigma = 0 of a blur, has a zero derivative there)
    live = [j for j in range(len(knobs)) if knobs[j]["name"] not in reasons and np.linalg.norm(J_phi[:, j]) > 0]
    if len(live) >= 2:
        conf = sensitivity.mv_confounding(J_phi[:, live], names=[names[j] for j in live], threshold=threshold,
                                          log_params=all(knobs[j]["scale"] == "log" for j in live))
        for grp in conf["confounded_groups"]:
            idx = [live[[names[j] for j in live].index(n)] for n in grp["parameters"]]
            sub = J_phi[:, idx]
            nrm = np.linalg.norm(sub, axis=0)
            Sn = sub / np.where(nrm > 0, nrm, 1.0)
            lam, vec = np.linalg.eigh(Sn.T @ Sn)
            gk = [knobs[i] for i in idx]
            # natural-coordinate weights: the eigenvector is for normalised columns -> divide by the column norm
            Fphi = sub.T @ sub
            for e in range(lam.size - 1, -1, -1):
                if lam[e] >= 1.0 / threshold ** 2:
                    s, wn = _fmt_combo(vec[:, e], nrm, gk)
                    var = float(wn @ np.linalg.pinv(Fphi) @ wn)
                    combos.append({"knobs": [k["name"] for k in gk], "combination": s,
                                   "weights": dict(zip([k["name"] for k in gk], wn.tolist())),
                                   "value": _combo_value(wn, gk, th), "std_linearised": math.sqrt(max(var, 0.0)),
                                   "gamma": float(grp["gamma"]) if math.isfinite(grp["gamma"]) else None})
            und = [_fmt_combo(vec[:, e], nrm, gk)[0] for e in range(lam.size) if lam[e] < 1.0 / threshold ** 2]
            for k in gk:
                reasons.setdefault(k["name"], "confounded: %s cannot be told apart from %s (gamma = %s > %g); the data fix "
                                   "only %s; not determined: %s"
                                   % (k["name"], [x["name"] for x in gk if x is not k],
                                      "inf" if not math.isfinite(grp["gamma"]) else "%.3g" % grp["gamma"], threshold,
                                      [c["combination"] for c in combos if k["name"] in c["knobs"]] or "nothing",
                                      und))
    for j, k in enumerate(knobs):
        if k["name"] in reasons:
            continue
        if u[j] < EDGE_FRACTION or u[j] > 1.0 - EDGE_FRACTION:
            reasons[k["name"]] = ("at_bound: %s ended within %g %% of its range end (%g in %g..%g) — the model or the "
                                  "range is wrong; an estimate pinned to the edge is not an estimate"
                                  % (k["name"], 100 * EDGE_FRACTION, th[k["name"]], k["lo"], k["hi"]))
    gamma_full = None if conf is None else (float(conf["gamma_full"]) if math.isfinite(conf["gamma_full"]) else None)
    return reasons, combos, J_u, gamma_full


# --------------------------------------------------------------------------- #
# simcal_screen                                                               #
# --------------------------------------------------------------------------- #
def _whitened_runs(model, P, U):
    th0 = P.theta(np.array([_to_u(k["init"], k) for k in P.free]))
    sims0, _ = P.mu(np.array([_to_u(k["init"], k) for k in P.free]))
    sw = P.weights(sims0, th0)
    Y = np.empty((U.shape[0], sw.size))
    for i in range(U.shape[0]):
        Y[i] = P.flat(P.mu(U[i])[0]) * sw
    return Y, sw


def _screen_problem(model):
    """A _Problem for screening: the observed masks if present, else every pixel and a dummy observation."""
    if model.get("observed"):
        return _Problem(model)
    m = copy.deepcopy(model)
    sims = _simulate(m, _init_values(m))
    m["observed"] = {"images": sims, "mask": [np.ones(s.shape, dtype=bool) for s in sims],
                     "var_scale": [1.0] * len(sims)}
    return _Problem(m)


def simcal_screen(model=None, method="morris", size=8, threshold=10.0, seed=0) -> dict:
    """Which knobs move the images above the camera noise, which are confounded, and how many output directions exist.

    Runs the model on a screening plan over the free knobs' ranges — Morris trajectories
    (``sensitivity.doe_morris``, ``size`` of them, (k+1) runs each) or a Saltelli plan
    (``sensitivity.doe_saltelli`` with n = the power of two >= 8 x ``size`` rows, (k+2) n runs) —
    and whitens every output by the noise standard deviation at the
    initial knobs. The whitened outputs are reduced to principal components and the indices
    are computed per component with ``sensitivity.sens_morris`` / ``sens_sobol`` (reused):
    Morris ``mu_star_whitened`` = sqrt(sum over components of mu*^2) — roughly how many noise
    standard deviations a full-range move of the knob shifts the images; Sobol' ``gsi_st`` =
    the variance-weighted total index over components (Lamboni et al. 2011).
    ``output_dims`` = number of principal directions of the centred whitened runs above the
    noise edge (``sensitivity.mv_residual_pca`` with sigma = 1): more free knobs than
    output dims means the data cannot fix them all. Local confounding at the initial knobs:
    ``sensitivity.mv_confounding`` on the whitened Jacobian (gamma_K > ``threshold``).

    ``class`` per knob: ``no_influence`` (Morris: mu*_whitened < 1.96, i.e. a full-range move is
    within noise; Sobol': gsi_st < 0.001), ``combination`` (in a confounded group: only a
    combination is determined), else ``determined``. Needs a noise model (refused without).
    """
    import sensitivity
    op = "simcal_screen"
    model = simcal_model() if model is None else model
    _check_model(model, op, need_noise=True)
    if method not in ("morris", "sobol"):
        raise ValueError("%s: method must be 'morris' or 'sobol', got %r" % (op, method))
    thr = _num(threshold, "threshold", op, 1.0, lo_open=True)
    P = _screen_problem(model)
    if not P.free:
        raise ValueError("%s: every knob is fixed — nothing to screen" % op)
    factors = [(k["name"], k["lo"], k["hi"], k["unit"], k["scale"]) for k in P.free]
    size = _doe._int_arg(size, "size", op, 2, 1000)
    if method == "morris":
        d = sensitivity.doe_morris(r=size, factors=factors, levels=4, seed=seed)
    else:
        d = sensitivity.doe_saltelli(n=2 ** int(math.ceil(math.log2(8 * size))), factors=factors, seed=seed)
    U = (np.asarray(d["coded"]) + 1.0) / 2.0
    Y, sw = _whitened_runs(model, P, U)
    Yc = Y - Y.mean(axis=0)
    Uc, S, Vt = np.linalg.svd(Yc, full_matrices=False)
    var = S ** 2
    tot = float(var.sum())
    if not tot > 0:
        raise MetricContractError("%s: no knob changes the output at all over its range" % op)
    m = int(min(10, np.searchsorted(np.cumsum(var) / tot, 0.999) + 1))
    names = [k["name"] for k in P.free]
    per_comp = []
    if method == "morris":
        for c in range(m):
            sm = sensitivity.sens_morris(d, Uc[:, c] * S[c])
            per_comp.append(np.asarray(sm["mu_star"]))
        mu_star = np.sqrt(np.sum(np.stack(per_comp) ** 2, axis=0))
        gsi = None
        cls_noinf = mu_star < math.sqrt(CHI2_1_95)
    else:
        sts = []
        for c in range(m):
            ss = sensitivity.sens_sobol(d, Uc[:, c] * S[c], n_boot=0)
            sts.append(np.asarray(ss["ST"]))
        gsi = (np.stack(sts) * var[:m, None]).sum(axis=0) / var[:m].sum()
        mu_star = None
        cls_noinf = gsi < 1e-3
    dims = sensitivity.mv_residual_pca(Yc, noise_sigma=1.0)["n_structural"] if Yc.shape[0] >= 3 else None
    u0 = np.array([_to_u(k["init"], k) for k in P.free])
    reasons, combos, J_u, gamma_full = _diagnose(P, u0, sw, thr)
    cls = []
    for j, nm in enumerate(names):
        if cls_noinf[j] or reasons.get(nm, "").startswith("no_influence"):
            cls.append("no_influence")
        elif reasons.get(nm, "").startswith("confounded"):
            cls.append("combination")
        else:
            cls.append("determined")
    return {"knobs": names, "class": dict(zip(names, cls)), "method": method,
            "mu_star_whitened": None if mu_star is None else dict(zip(names, mu_star.tolist())),
            "gsi_st": None if gsi is None else dict(zip(names, gsi.tolist())),
            "n_components": m, "output_dims": dims, "n_free": len(names),
            "more_knobs_than_dims": None if dims is None else bool(len(names) > dims),
            "gamma_full": gamma_full, "determined_combos": combos,
            "reasons": {nm: reasons[nm] for nm in names if nm in reasons},
            "n_runs": int(U.shape[0]), "size": size, "threshold": thr, "seed": seed}


# --------------------------------------------------------------------------- #
# simcal_fit                                                                  #
# --------------------------------------------------------------------------- #
def _calresult(model, P, run, reasons, combos, gamma_full, allow, method, starts, threshold):
    u = run["u"]
    th = P.theta(u)
    sims = _simulate(P.model, th, P.seed)
    var = _variances(P.model, sims, th)
    obs = model["observed"]
    maps = []
    for o, s, v, m in zip(obs["images"], sims, var, obs["mask"]):
        rm = np.where(m, (o - s) / np.sqrt(v), 0.0)
        maps.append(rm)
    n_obs = int(P.y.size)
    dof = max(1, n_obs - len(P.free))
    warn = []
    if run["chi2"] / dof > 1.0 + 4.0 * math.sqrt(2.0 / dof):
        warn.append("reduced chi^2 = %.3g is far above 1 (+4 sd of a chi^2 with %d dof): a local minimum (try "
                    "method='multistart') or a model that misses something (simcal_discrepancy)"
                    % (run["chi2"] / dof, dof))
    if run["status"] != "converged":
        warn.append("the optimiser stopped with status %r, not 'converged'" % run["status"])
    theta_hat = {k["name"]: float(th[k["name"]]) for k in P.free if k["name"] not in reasons}
    status = "accepted" if not reasons else ("partial" if theta_hat or combos else "refused")
    refusals = [{"rule": rs.split(":", 1)[0], "knobs": [nm], "reason": rs} for nm, rs in reasons.items()]
    return {
        "sort": "calresult", "status": status, "theta_hat": theta_hat,
        "units": {k["name"]: k["unit"] for k in model["knobs"]},
        "scale": {k["name"]: k["scale"] for k in model["knobs"]},
        "fixed": dict(P.fixed), "nuisance": list(model.get("nuisance") or []),
        "undetermined": dict(reasons), "determined_combos": combos, "refusals": refusals,
        "fit": {"method": method, "chi2": float(run["chi2"]), "n_obs": n_obs, "dof": dof,
                "chi2_red": float(run["chi2"]) / dof, "iterations": int(run["iterations"]),
                "status": run["status"], "converged": bool(run["converged"]), "n_evaluations": int(P.n_eval),
                "starts": starts, "gamma_full": gamma_full, "threshold": threshold,
                "allow_undetermined": bool(allow), "warnings": warn},
        "errors": {"train": float(run["chi2"]) / dof, "holdout": None, "locked": None},
        "residual_maps": maps, "data_range": list(obs["data_range"]),
        "model": model,
        "diagnostics": {"endpoint_not_an_estimate": {k["name"]: float(th[k["name"]]) for k in P.free},
                        "endpoint_u": u.tolist(), "note": (
                            "the optimiser end point, kept so the checking ops can re-run the model; for the knobs "
                            "in 'undetermined' it is NOT an estimate")},
        "identifiability": None, "uncertainty": None, "validation": None, "discrepancy": None,
    }


def _run_fit(model, method, n_starts, seed, fix, threshold, allow, op, u_start=None):
    P = _Problem(model, fix=fix)
    for n in (fix or {}):
        if n not in {k["name"] for k in model["knobs"]}:
            raise ValueError("%s: fix names an unknown knob %r" % (op, n))
    if not P.free:
        raise ValueError("%s: every knob is fixed — nothing to fit" % op)
    u0 = np.array([_to_u(k["init"], k) for k in P.free]) if u_start is None else np.asarray(u_start, float)
    # starting point(s): the initial knobs and a Latin-hypercube plan over the ranges, ranked by their own
    # reduced chi^2 — the design's "start from the best point of the plan" (an LM run from the middle of a
    # wide range can walk into a range end while a better basin exists; measured on the blur/vignetting/gain/
    # offset model: chi^2_red 371 at offset = 200 from the middle, 0.95 from the best plan point)
    n_plan = _doe._int_arg(n_starts, "n_starts", op, 2, 10000)
    plan = _doe.doe_lhs(n_plan, [(k["name"], 0.0, 1.0) for k in P.free], seed=seed)
    cand = [u0] + [np.clip((row + 1.0) / 2.0, 0.02, 0.98) for row in plan["coded"]]

    def plan_score(us):
        sims, th = P.mu(us)
        rr = (P.y - P.flat(sims)) * P.weights(sims, th)
        return float(rr @ rr)

    scored = sorted(((plan_score(c), i) for i, c in enumerate(cand)), key=lambda t: t[0])
    if method == "multistart":
        starts_u = [cand[i] for _s, i in scored[:max(2, n_plan // 4)]]
    else:
        starts_u = [cand[scored[0][1]]]
    runs = []

    def one(us):
        rr = _nelder_mead(P, us) if method == "nm" else _lm(P, us)
        runs.append(rr)
        return rr["chi2"]

    atts = [attempt(one, us, metric="simcal_chi2") for us in starts_u]
    best = best_of(atts)
    if best is None:
        raise MetricContractError("%s: every start failed: %s" % (op, "; ".join(a.reason or "" for a in atts)))
    run = min(runs, key=lambda rr: rr["chi2"])                       # = the run behind best_of(atts)
    starts = [{"start": {k["name"]: float(_from_u(float(s[j]), k)) for j, k in enumerate(P.free)},
               "chi2": None if not a.ok else float(a.value), "failed": None if a.ok else a.reason}
              for s, a in zip(starts_u, atts)]
    reasons, combos, _J, gamma_full = _diagnose(P, run["u"], run["sw"], threshold)
    starts = {"n_plan": n_plan, "runs": starts}
    return P, run, reasons, combos, gamma_full, starts


def simcal_fit(model=None, method="lm", n_starts=16, fix=None, threshold=10.0, allow_undetermined=False,
               seed=0) -> dict:
    """Fit the free knobs of an observed simmodel to its images (weighted least squares) -> ``calresult``.

    Minimises chi^2 = sum over valid pixels of (observed − simulated)^2 / variance, the
    variance coming from the noise model at the current prediction (re-weighted each
    iteration: the quasi-likelihood estimating equation, unbiased for a signal-dependent
    variance). Knobs live in u in [0, 1] (log knobs on a log axis).

    Starting point: the initial knobs and ``n_starts`` Latin-hypercube points over the ranges are
    scored by chi^2 and the best is used (the design's "start from the best point of the plan").
    ``method``: ``"lm"`` (Levenberg-Marquardt, Marquardt-scaled damping; a raw step that leaves
    the range is not taken — its projection onto the range is tried, a knob on a range end whose
    descent points outward is held there, and a point the forward model refuses rejects the step
    and raises the damping, as in ``lensopt``), ``"nm"`` (Nelder-Mead; a point outside the range
    scores the metric's worst value via ``metriccontract.value_or_worst``), ``"multistart"`` (LM
    from the best ``n_starts // 4`` plan points, at least 2, ranked with
    ``metriccontract.best_of`` — for multi-modal problems such as thin-film fringe orders).
    ``fix`` = ``{knob: value}`` pins knobs for this fit.

    **Refusal** (``metriccontract.MetricContractError``, a ``ValueError``) when, at the end
    point, a knob has no influence (a full-range move changes chi^2 by less than 3.84), is
    confounded with others (collinearity index gamma_K > ``threshold``,
    ``sensitivity.mv_confounding``), or sits within 1 % of a range end — the message names
    the knobs, the reason and the combinations the data do fix. With
    ``allow_undetermined=True`` those knobs get **no value** (``undetermined`` holds the
    reason, ``status`` = ``partial``) and ``determined_combos`` carries the combinations with
    their values (a product of powers for log knobs). No noise model / no observed images:
    refused.
    """
    op = "simcal_fit"
    model = simcal_model() if model is None else model
    _check_model(model, op, need_observed=True, need_noise=True)
    if method not in ("lm", "nm", "multistart"):
        raise ValueError("%s: method must be 'lm', 'nm' or 'multistart', got %r" % (op, method))
    thr = _num(threshold, "threshold", op, 1.0, lo_open=True)
    if fix is not None and not isinstance(fix, dict):
        raise ValueError("%s: fix must be {knob: value}" % op)
    P, run, reasons, combos, gamma_full, starts = _run_fit(model, method, n_starts, seed, fix, thr,
                                                           allow_undetermined, op)
    if reasons and not allow_undetermined:
        lines = ["%s: %s" % (n, r) for n, r in reasons.items()]
        extra = ""
        if combos:
            extra = " Determined combinations: " + "; ".join(
                "%s = %s" % (c["combination"], c["value"]) for c in combos) + "."
        raise MetricContractError(
            "%s: refusing to return point estimates — %d knob(s) are not determined by these images:\n  %s\n%s "
            "Fix them (fix={...}), change the experiment (simcal_screen shows which conditions would help), or "
            "pass allow_undetermined=True to get only the determined knobs and combinations."
            % (op, len(reasons), "\n  ".join(lines), extra))
    return _calresult(model, P, run, reasons, combos, gamma_full, allow_undetermined, method, starts, thr)
