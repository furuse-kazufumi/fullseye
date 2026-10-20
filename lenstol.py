"""Manufacturing-tolerance budgets, compensated Monte Carlo, and sensitivity.

The operations in this module leave :func:`raytrace.tolerance_analysis`
unchanged.  A tolerance is an explicit row, and every Monte-Carlo row owns a
random stream derived from its stable row id and the run seed.  Thus inserting
an unrelated row cannot change existing draws.

``irregularity_fringes`` uses one fringe as half a reference wavelength of
peak-to-valley sag and a test-plate index difference of one.  The sag is the
unit-RMS pupil polynomial ``(x*x-y*y)/sqrt(1/6)`` scaled so its peak-to-valley
is the requested sag.  Refraction therefore sees the perturbed surface, not a
post-hoc score correction.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from statistics import NormalDist

import numpy as np

import lensopt as LO
import raytrace as RT

INF = float("inf")
KINDS = frozenset(("radius_pct", "radius_fringes", "thickness_mm", "index", "vd_pct",
                   "decenter_mm", "tilt_deg", "irregularity_fringes", "wedge_arcmin",
                   "group_decenter_mm", "group_tilt_deg"))
DISTRIBUTIONS = frozenset(("uniform", "normal", "truncated_normal"))
PERCENTILES = (2, 10, 50, 90, 98)


def _finite(value, name, nonneg=False, positive=False):
    return RT._finite(value, name, nonneg=nonneg, positive=positive)


def _rebuild(system, surfaces):
    return RT.lens_system(surfaces, stop=system["stop"], object_mm=system["object_mm"],
                          wavelength_um=system["wavelength_um"], index_object=system["index_object"],
                          image_mm=system["image_mm"], field=system["field"],
                          aim=system.get("aim", "paraxial"), vignetting=system.get("vignetting"),
                          **RT._system_extras(system))


def _surface_indices(system, row, number):
    n = len(system["surfaces"])
    kind = row.get("kind")
    if kind.startswith("group_"):
        raw = row.get("surfaces", row.get("group"))
        if isinstance(raw, range):
            out = list(raw)
        elif isinstance(raw, (tuple, list)) and len(raw) == 2 and all(isinstance(x, int) for x in raw):
            out = list(range(raw[0], raw[1] + 1))
        elif isinstance(raw, (tuple, list)):
            out = list(raw)
        else:
            raise ValueError("row %d %s: surfaces must be a non-empty list or inclusive pair" % (number, kind))
        if not out:
            raise ValueError("row %d %s: surfaces must not be empty" % (number, kind))
        if any(isinstance(i, bool) or not isinstance(i, (int, np.integer)) or not 0 <= int(i) < n for i in out):
            raise ValueError("row %d %s: surface range is outside 0..%d" % (number, kind, n - 1))
        out = [int(i) for i in out]
        if len(set(out)) != len(out):
            raise ValueError("row %d %s: surfaces contain duplicates" % (number, kind))
        return out
    i = row.get("surface")
    if isinstance(i, bool) or not isinstance(i, (int, np.integer)) or not 0 <= int(i) < n:
        raise ValueError("row %d %s: surface must be in 0..%d" % (number, kind, n - 1))
    return [int(i)]


def _normalise_row(system, row, number):
    if not isinstance(row, dict):
        raise ValueError("row %d must be a dict" % number)
    kind = str(row.get("kind", ""))
    if kind not in KINDS:
        raise ValueError("row %d: unknown kind %r" % (number, kind))
    idx = _surface_indices(system, row, number)
    tol = _finite(row.get("tolerance", row.get("tol")), "row %d tolerance" % number, positive=True)
    dist = str(row.get("distribution", "uniform"))
    if dist not in DISTRIBUTIONS:
        raise ValueError("row %d %s: unknown distribution %r" % (number, kind, dist))
    sigma = row.get("sigma")
    if sigma is not None:
        sigma = _finite(sigma, "row %d sigma" % number, positive=True)
    axis = str(row.get("axis", "y"))
    if axis not in ("x", "y"):
        raise ValueError("row %d %s: axis must be 'x' or 'y'" % (number, kind))
    if kind in ("radius_pct", "radius_fringes") and any(system["surfaces"][i]["R"] == INF for i in idx):
        raise ValueError("row %d %s: flat surface has no radius tolerance" % (number, kind))
    if kind in ("thickness_mm", "wedge_arcmin") and any(system["surfaces"][i]["t"] is None for i in idx):
        raise ValueError("row %d %s: surface has no following thickness" % (number, kind))
    if kind in ("index", "vd_pct") and any(system["surfaces"][i]["mirror"] or system["surfaces"][i]["n_value"] <= 1 for i in idx):
        raise ValueError("row %d %s: surface does not enter a dispersive medium" % (number, kind))
    if kind == "vd_pct":
        for i in idx:
            med = system["surfaces"][i]["n"]
            if not (isinstance(med, (tuple, list)) and len(med) == 2):
                raise ValueError("row %d vd_pct: surface %d needs an (n_d, V_d) medium" % (number, i))
    stable = row.get("id")
    if stable is None:
        target = ",".join(map(str, idx))
        stable = "%s:%s:%s" % (kind, target, axis)
    if not isinstance(stable, str) or not stable.strip():
        raise ValueError("row %d %s: id must be a non-empty string" % (number, kind))
    out = dict(row)
    out.update({"id": stable, "kind": kind, "tolerance": tol, "distribution": dist,
                "sigma": sigma, "axis": axis})
    if kind.startswith("group_"):
        out["surfaces"] = idx
        out.pop("surface", None)
    else:
        out["surface"] = idx[0]
    return out


def tolerance_table(system, defaults=None, overrides=None):
    """Build validated tolerance rows, one independent manufacturing variable per row.

    ``defaults`` maps tolerance kinds to magnitudes and expands them over every
    applicable surface. ``overrides`` is a sequence of explicit row dicts; an
    override with the same ``kind``/target/axis replaces the generated row.
    Radius power fringes use ``delta_R/R = wavelength/(2*abs(sag_edge))`` at
    the clear semi-aperture, the standard test-plate power-fringe formula.
    """
    RT._check_system(system)
    defaults = ({"radius_pct": 0.5, "thickness_mm": 0.05, "index": 0.001,
                 "decenter_mm": 0.02, "tilt_deg": 0.05} if defaults is None else defaults)
    if not isinstance(defaults, dict):
        raise ValueError("defaults must be a dict")
    unknown = set(defaults) - KINDS
    if unknown:
        raise ValueError("unknown default tolerance kinds %r" % sorted(unknown))
    raw = []
    for kind, value in defaults.items():
        if isinstance(value, dict):
            mag = value.get("tolerance", value.get("tol"))
            extra = {k: v for k, v in value.items() if k not in ("tolerance", "tol")}
        else:
            mag, extra = value, {}
        if kind.startswith("group_"):
            groups = extra.pop("groups", None)
            if not groups:
                raise ValueError("default %s needs non-empty groups" % kind)
            for group in groups:
                raw.append({"kind": kind, "surfaces": group, "tolerance": mag, **extra})
            continue
        for i, s in enumerate(system["surfaces"]):
            applicable = True
            if kind in ("radius_pct", "radius_fringes"):
                applicable = s["R"] != INF
            elif kind in ("thickness_mm", "wedge_arcmin"):
                applicable = s["t"] is not None
            elif kind == "index":
                applicable = not s["mirror"] and s["n_value"] > 1 and s.get("f") is None
            elif kind == "vd_pct":
                applicable = isinstance(s["n"], (tuple, list)) and len(s["n"]) == 2
            if applicable:
                raw.append({"kind": kind, "surface": i, "tolerance": mag, **extra})
    if overrides is not None:
        if not isinstance(overrides, (list, tuple)):
            raise ValueError("overrides must be a sequence of rows")
        for item in overrides:
            nr = _normalise_row(system, item, len(raw))
            raw = [r for j, r in enumerate(raw)
                   if _normalise_row(system, r, j)["id"] != nr["id"]]
            raw.append(nr)
    rows = [_normalise_row(system, r, i) for i, r in enumerate(raw)]
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("tolerance row ids must be unique")
    return rows


def tolerance_criteria(rms_spot=None, wavefront_rms=None, efl=None, mtf=None, distortion=None,
                       back_focus=None, fields=None, wavelengths=None, rings=6, reference="centroid",
                       psf_size=None):
    """Validate performance criteria and their optional ``min``/``max`` limits."""
    if reference not in ("centroid", "chief"):
        raise ValueError("reference must be 'centroid' or 'chief'")
    fl = [0.0] if fields is None else list(np.atleast_1d(fields))
    wl = None if wavelengths is None else list(np.atleast_1d(wavelengths))
    if not fl:
        raise ValueError("fields must not be empty")
    fl = [_finite(x, "field") for x in fl]
    if wl is not None:
        if not wl:
            raise ValueError("wavelengths must not be empty")
        wl = [_finite(x, "wavelength", positive=True) for x in wl]
    if isinstance(rings, bool) or int(rings) != rings or not 1 <= int(rings) <= 64:
        raise ValueError("rings must be an integer in 1..64")
    specs = {}
    for name, value in (("rms_spot", rms_spot), ("wavefront_rms", wavefront_rms), ("efl", efl),
                        ("mtf", mtf), ("distortion", distortion), ("back_focus", back_focus)):
        if value is None or value is False:
            continue
        d = {} if value is True else dict(value)
        unknown = set(d) - {"min", "max", "frequency_cpmm", "axis"}
        if unknown:
            raise ValueError("%s: unknown keys %r" % (name, sorted(unknown)))
        for bound in ("min", "max"):
            if bound in d:
                d[bound] = _finite(d[bound], "%s %s" % (name, bound))
        if "min" in d and "max" in d and d["min"] > d["max"]:
            raise ValueError("%s: min exceeds max" % name)
        if name == "mtf":
            d["frequency_cpmm"] = _finite(d.get("frequency_cpmm"), "mtf frequency_cpmm", nonneg=True)
            d["axis"] = d.get("axis", "mean")
            if d["axis"] not in ("mean", "tangential", "sagittal"):
                raise ValueError("mtf axis must be mean, tangential, or sagittal")
        specs[name] = d
    if not specs:
        specs["rms_spot"] = {}
    return {"criteria": specs, "fields": fl, "wavelengths": wl, "rings": int(rings),
            "reference": reference, "psf_size": psf_size}


def compensators(variables="t1", criterion="rms_spot", bounds=None, iterations=8):
    """Describe deterministic bounded re-optimisation variables in lensopt grammar."""
    variables = [variables] if isinstance(variables, str) else list(variables)
    if not variables:
        raise ValueError("compensator variables must not be empty")
    if len(set(map(str, variables))) != len(variables):
        raise ValueError("compensator variables contain duplicates")
    if criterion not in ("rms_spot", "wavefront_rms", "efl", "mtf", "distortion", "back_focus"):
        raise ValueError("unknown compensator criterion %r" % criterion)
    if isinstance(iterations, bool) or not 1 <= int(iterations) <= 50:
        raise ValueError("compensator iterations must be 1..50")
    return {"variables": variables, "criterion": criterion, "bounds": {} if bounds is None else dict(bounds),
            "iterations": int(iterations)}


def _radius_from_fringes(s, fringes, wavelength_um=0.546074):
    ap = s.get("ap")
    if ap is None or ap <= 0:
        raise ValueError("radius_fringes needs a finite clear semi-aperture")
    R = float(s["R"])
    edge = abs(R) - math.sqrt(max(0.0, R * R - ap * ap))
    if edge <= 0:
        raise ValueError("radius_fringes test-plate sag is zero")
    pct_per_fringe = wavelength_um * 1e-3 / (2.0 * edge) * 100.0
    return R * (1.0 + fringes * pct_per_fringe / 100.0)


def _apply_row(system, row, value):
    """Apply one signed row value; used by sensitivity gates as a second construction path."""
    surf = [dict(s) for s in system["surfaces"]]
    kind = row["kind"]
    idx = row.get("surfaces", [row.get("surface")])
    axis = 0 if row.get("axis", "y") == "x" else 1
    # A rotation about x steers in y, and a rotation about y steers in x.
    tilt_axis = 0 if row.get("axis", "y") == "y" else 1
    for i in idx:
        s = surf[i]
        if kind == "radius_pct":
            s["R"] *= 1.0 + value / 100.0
        elif kind == "radius_fringes":
            s["R"] = _radius_from_fringes(s, value)
        elif kind == "thickness_mm":
            s["t"] += value
            if s["t"] < 0:
                raise ValueError("%s makes surface %d thickness negative" % (row["id"], i))
        elif kind == "index":
            s["n"] = RT._index_offset(s["n"], value)
        elif kind == "vd_pct":
            nd, vd = s["n"]
            s["n"] = (nd, vd * (1.0 + value / 100.0))
        elif kind in ("decenter_mm", "group_decenter_mm"):
            q = list(s["decenter"]); q[axis] += value; s["decenter"] = tuple(q)
        elif kind in ("tilt_deg", "group_tilt_deg"):
            q = list(s["tilt"]); q[tilt_axis] += value; s["tilt"] = tuple(q)
        elif kind == "wedge_arcmin":
            q = list(s["tilt"]); q[tilt_axis] += value / 60.0; s["tilt"] = tuple(q)
        elif kind == "irregularity_fringes":
            # Full surface support lives in raytrace's anisotropic sag extension.
            q = list(s.get("zernike_sag", (0.0, 0.0)))
            q[0] += value * system["wavelength_um"] * 1e-3 / 2.0
            s["zernike_sag"] = tuple(q)
    return _rebuild(system, surf)


def _distribution_variance(distribution, tolerance, sigma):
    tol = float(tolerance)
    sig = tol / 3.0 if sigma is None else float(sigma)
    if distribution == "uniform":
        return tol * tol / 3.0
    if distribution == "normal":
        return sig * sig
    a = tol / sig
    z = math.erf(a / math.sqrt(2.0))
    return sig * sig * (1.0 - 2.0 * a * math.exp(-0.5 * a * a) / math.sqrt(2.0 * math.pi) / z)


def _row_seed(seed, row_id):
    b = hashlib.blake2b((str(int(seed)) + "\0" + row_id).encode("utf-8"), digest_size=16).digest()
    return int.from_bytes(b, "little")


def _draws(row, trials, seed):
    rng = np.random.default_rng(_row_seed(seed, row["id"]))
    tol = row["tolerance"]
    sig = tol / 3.0 if row["sigma"] is None else row["sigma"]
    if row["distribution"] == "uniform":
        return rng.uniform(-tol, tol, trials)
    if row["distribution"] == "normal":
        return rng.normal(0.0, sig, trials)
    out = np.empty(trials)
    filled = 0
    while filled < trials:
        x = rng.normal(0.0, sig, max(16, 2 * (trials - filled)))
        x = x[np.abs(x) <= tol]
        take = min(len(x), trials - filled)
        out[filled:filled + take] = x[:take]
        filled += take
    return out


def _rms_spot(system, cfg, field, wavelength):
    b = RT.ray_bundle(system, field=field, rings=cfg["rings"], wavelength_um=wavelength, pupil_fill=0.99)
    if not np.all(b["valid"]):
        raise ValueError("rms_spot: %d rays missed or underwent total internal reflection" % int((~b["valid"]).sum()))
    ref = b["chief_xy"] if cfg["reference"] == "chief" else b["image_xy"].mean(axis=0)
    d = b["image_xy"] - ref
    return float(np.sqrt(np.mean(np.sum(d * d, axis=1))))


def _check_mtf_physical(system, frequency, value, field, wavelength, size):
    import lensimage as LI
    fno = LI.through_focus_mtf(system, frequency_cpmm=[0.0], defocus_mm=[0.0],
                              field=field, wavelength_um=wavelength, size=size)["fno"]
    cutoff = 1e3 / (wavelength * fno)
    nu = frequency / cutoff
    if nu > 1.0 + 1e-12:
        raise ValueError("mtf frequency %.9g exceeds diffraction cutoff %.9g" % (frequency, cutoff))
    nu = min(1.0, max(0.0, nu))
    limit = 2.0 / math.pi * (math.acos(nu) - nu * math.sqrt(max(0.0, 1.0 - nu * nu)))
    # The finite FFT pupil raster is a Riemann approximation and can exceed
    # the continuous circular-pupil curve by a few parts in 1000.
    if value > limit + max(1e-9, 0.003 * limit):
        raise ValueError("mtf %.9g exceeds the diffraction limit %.9g" % (value, limit))


def _evaluate(system, cfg):
    import lensimage as LI
    specs = cfg["criteria"]
    fields = cfg["fields"]
    wavelengths = cfg["wavelengths"] or [system["wavelength_um"]]
    values = {k: [] for k in specs}
    para = RT.paraxial_trace(system)
    for name, spec in specs.items():
        if name == "efl":
            values[name].append(float(para["efl"])); continue
        if name == "back_focus":
            values[name].append(float(para["bfl"])); continue
        for field in fields:
            for wl in wavelengths:
                if name == "rms_spot":
                    values[name].append(_rms_spot(system, cfg, field, wl))
                elif name == "wavefront_rms":
                    q = RT.wavefront_from_opd(system, field=field, size=cfg["psf_size"] or 32,
                                              wavelength_um=wl)
                    values[name].append(float(q["rms_opd_direct"]))
                elif name == "mtf":
                    q = LI.through_focus_mtf(system, frequency_cpmm=[spec["frequency_cpmm"]],
                                             defocus_mm=[0.0], field=field, wavelength_um=wl,
                                             size=cfg["psf_size"])
                    tv, sv = float(q["tangential"][0, 0]), float(q["sagittal"][0, 0])
                    val = {"tangential": tv, "sagittal": sv, "mean": 0.5 * (tv + sv)}[spec["axis"]]
                    _check_mtf_physical(system, spec["frequency_cpmm"], val, field, wl, cfg["psf_size"])
                    values[name].append(val)
                elif name == "distortion":
                    ideal = abs(para["efl"] * math.tan(math.radians(field))) if system["object_mm"] == INF else abs(para["magnification"] * field)
                    if ideal <= 1e-15:
                        values[name].append(0.0)
                    else:
                        ch = RT.chief_ray(system, field=field, wavelength_um=wl)
                        if not ch["valid"]:
                            raise ValueError("distortion: chief ray failed")
                        values[name].append((abs(ch["image_y"]) - ideal) / ideal * 100.0)
    out = {}
    for name, a in values.items():
        if not a or not np.all(np.isfinite(a)):
            raise ValueError("%s did not produce finite values" % name)
        out[name] = float(np.mean(a))
    return out


def _compensate(system, nominal, cfg, comp):
    if comp is None:
        return system, {}
    variables = [LO._parse_variable(v, len(system["surfaces"])) for v in comp["variables"]]
    bounds = {"min_thickness": 0.0, "max_thickness": None, "min_radius": 1e-6}
    bspec = comp.get("bounds", {})
    x = np.array([LO._get(system, v) for v in variables], float)
    x_start = x.copy()
    target_name = comp["criterion"]
    if target_name not in cfg["criteria"]:
        raise ValueError("compensator criterion %r is not among the criteria" % target_name)

    def residual(sys_):
        val = _evaluate(sys_, cfg)[target_name]
        if target_name in ("rms_spot", "wavefront_rms"):
            return np.array([val])
        if target_name == "mtf":
            return np.array([1.0 - val])
        return np.array([val - nominal[target_name]])

    cur = system
    r = residual(cur)
    lam = 1e-5
    for _ in range(comp["iterations"]):
        J = np.empty((len(r), len(x)))
        for j, var in enumerate(variables):
            h = 1e-5 * max(1.0, abs(x[j]))
            xp = x.copy(); xp[j] += h
            J[:, j] = (residual(LO._rebuild(cur, xp, variables, bounds)) - r) / h
        A = J.T @ J + lam * np.eye(len(x))
        delta = np.linalg.solve(A, -J.T @ r)
        xn = x + delta
        # Optional per-variable [low, high] bounds are in physical variable units.
        for j, spec in enumerate(comp["variables"]):
            lim = bspec.get(spec, bspec.get(str(spec)))
            if lim is not None:
                xn[j] = min(float(lim[1]), max(float(lim[0]), xn[j]))
        trial = LO._rebuild(cur, xn, variables, bounds)
        rn = residual(trial)
        if float(rn @ rn) <= float(r @ r):
            cur, x, r = trial, np.array([LO._get(trial, v) for v in variables]), rn
            lam = max(1e-12, lam / 3)
        else:
            lam *= 10
    travel = {str(name): float(v - v0) for name, v, v0 in zip(comp["variables"], x, x_start)}
    return cur, travel


def _wilson(success, total, z=1.959963984540054):
    if total <= 0:
        return (0.0, 0.0)
    p = success / total
    den = 1.0 + z * z / total
    cen = (p + z * z / (2 * total)) / den
    rad = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / den
    return max(0.0, cen - rad), min(1.0, cen + rad)


def _stats(a, histogram_bins=20):
    a = np.asarray(a, float)
    if a.size == 0:
        return {"mean": INF, "std": INF, "percentiles": {str(p): INF for p in PERCENTILES},
                "worst": INF, "histogram": {"edges": [], "counts": []}}
    counts, edges = np.histogram(a, bins=min(histogram_bins, max(1, int(math.sqrt(a.size)))))
    return {"mean": float(a.mean()), "std": float(a.std()),
            "percentiles": {str(p): float(np.percentile(a, p)) for p in PERCENTILES},
            "worst": float(a.max()),
            "histogram": {"edges": edges.tolist(), "counts": counts.astype(int).tolist()}}


def _inside(values, specs):
    return all(("min" not in specs[k] or v >= specs[k]["min"]) and
               ("max" not in specs[k] or v <= specs[k]["max"]) for k, v in values.items())


def tolerance_monte_carlo(system, table, criteria, compensators=None, trials=100, seed=0,
                          histogram_bins=20, _return_draws=False):
    """Run deterministic fail-closed Monte Carlo and report yield with Wilson 95 % bounds."""
    RT._check_system(system)
    system = RT._freeze_solves(system)
    rows = [_normalise_row(system, r, i) for i, r in enumerate(table)]
    if len(rows) != len({r["id"] for r in rows}):
        raise ValueError("tolerance row ids must be unique")
    if isinstance(trials, bool) or not 1 <= int(trials) <= 1_000_000:
        raise ValueError("trials must be 1..1000000")
    trials = int(trials)
    nominal = _evaluate(system, criteria)
    drawmap = {r["id"]: _draws(r, trials, seed) for r in rows}
    samples = {k: [] for k in criteria["criteria"]}
    travels = {} if compensators is None else {str(v): [] for v in compensators["variables"]}
    passed = 0
    reasons = {}
    for j in range(trials):
        try:
            cur = system
            for row in rows:
                cur = _apply_row(cur, row, float(drawmap[row["id"]][j]))
            cur, travel = _compensate(cur, nominal, criteria, compensators)
            vals = _evaluate(cur, criteria)
            for k, v in vals.items():
                samples[k].append(v)
            for k, v in travel.items():
                travels[k].append(v)
            passed += int(_inside(vals, criteria["criteria"]))
        except (ValueError, FloatingPointError, np.linalg.LinAlgError) as exc:
            reason = str(exc) or type(exc).__name__
            reasons[reason] = reasons.get(reason, 0) + 1
    result = {"nominal": nominal, "criteria": {k: _stats(v, histogram_bins) for k, v in samples.items()},
              "yield": passed / trials, "yield_wilson95": _wilson(passed, trials),
              "passed": passed, "trials": trials, "failed_trials": trials - len(next(iter(samples.values()))),
              "failure_reasons": reasons, "seed": int(seed), "table": rows,
              "compensator_travel": {k: _stats(v, histogram_bins) for k, v in travels.items()}}
    if _return_draws:
        result["draws"] = drawmap
    return result


def tolerance_sensitivity(system, table, criteria, compensators=None, allowed_degradation=None):
    """Central differences, distribution-aware linear RSS, and inverse tolerances."""
    RT._check_system(system)
    rows = [_normalise_row(system, r, i) for i, r in enumerate(table)]
    nominal = _evaluate(system, criteria)
    out = []
    rss2 = {k: 0.0 for k in nominal}
    for row in rows:
        vals = []
        for sign in (-1.0, 1.0):
            cur = _apply_row(system, row, sign * row["tolerance"])
            cur, _travel = _compensate(cur, nominal, criteria, compensators)
            vals.append(_evaluate(cur, criteria))
        deriv = {k: (vals[1][k] - vals[0][k]) / (2.0 * row["tolerance"]) for k in nominal}
        variance = _distribution_variance(row["distribution"], row["tolerance"], row["sigma"])
        contribution = {k: abs(deriv[k]) * math.sqrt(variance) for k in nominal}
        for k in nominal:
            rss2[k] += contribution[k] ** 2
        inv = {}
        if allowed_degradation:
            for k, allowed in allowed_degradation.items():
                if k not in nominal:
                    raise ValueError("inverse_sensitivity: unknown criterion %r" % k)
                inv[k] = INF if deriv[k] == 0 else abs(_finite(allowed, "allowed degradation", nonneg=True) / deriv[k])
        out.append({"id": row["id"], "kind": row["kind"], "surface": row.get("surface"),
                    "surfaces": row.get("surfaces"), "minus": vals[0], "plus": vals[1],
                    "derivative": deriv, "std_contribution": contribution,
                    "inverse_sensitivity": inv, "inverse_is_linear_estimate": True})
    drivers = sorted(out, key=lambda q: (-max(q["std_contribution"].values()), q["id"]))
    return {"nominal": nominal, "rows": out, "rss_std": {k: math.sqrt(v) for k, v in rss2.items()},
            "drivers": drivers}


def tolerance_report(result, sensitivity=None, as_dict=False):
    """Create a compact assembly report as a dict or plain text."""
    data = {"nominal": result["nominal"], "criteria": result["criteria"], "yield": result["yield"],
            "yield_wilson95": result["yield_wilson95"], "failed_trials": result["failed_trials"],
            "top_contributors": [] if sensitivity is None else sensitivity["drivers"][:5],
            "compensator_travel": result["compensator_travel"]}
    if as_dict:
        return data
    lines = ["Tolerance report", "Nominal: " + json.dumps(data["nominal"], sort_keys=True),
             "Yield: %.3f (Wilson 95%% %.3f..%.3f); failed trials: %d" %
             (data["yield"], data["yield_wilson95"][0], data["yield_wilson95"][1], data["failed_trials"])]
    for name, stat in data["criteria"].items():
        lines.append("%s: mean %.8g, std %.8g, p2/p50/p98 %.8g / %.8g / %.8g" %
                     (name, stat["mean"], stat["std"], stat["percentiles"]["2"],
                      stat["percentiles"]["50"], stat["percentiles"]["98"]))
    if data["top_contributors"]:
        lines.append("Top contributors: " + ", ".join(q["id"] for q in data["top_contributors"]))
    if data["compensator_travel"]:
        lines.append("Compensator travel: " + json.dumps(data["compensator_travel"], sort_keys=True))
    return "\n".join(lines)


def tolerance_table_zmx(table):
    """Serialise rows as NOTE lines; public native TOL syntax was not assumed."""
    return "\n".join("NOTE TOLERANCE_ROW " + json.dumps(r, sort_keys=True, separators=(",", ":")) for r in table)


def tolerance_table_from_zmx(system, text):
    """Read tolerance NOTE lines written by :func:`tolerance_table_zmx`."""
    rows = []
    prefix = "NOTE TOLERANCE_ROW "
    for line in str(text).splitlines():
        if line.startswith(prefix):
            rows.append(json.loads(line[len(prefix):]))
    if not rows:
        raise ValueError("no TOLERANCE_ROW NOTE lines found")
    return [_normalise_row(system, r, i) for i, r in enumerate(rows)]


__all__ = ["tolerance_table", "tolerance_criteria", "compensators", "tolerance_monte_carlo",
           "tolerance_sensitivity", "tolerance_report", "tolerance_table_zmx", "tolerance_table_from_zmx"]
