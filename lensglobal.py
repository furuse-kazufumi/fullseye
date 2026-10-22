# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""lensglobal — glass substitution and multi-start (global) search for sequential lens systems.

Two things a lens designer does after a local optimisation has converged:

* **swap a model glass for a real one.** A model glass is a ``(n_d, V_d)`` pair (or a dict from
  ``raytrace.glass``); a real design needs a catalogue glass. :func:`glass_nearest` ranks the catalogue
  by distance in the Abbe plane, :func:`lens_substitute_glasses` swaps every model glass of a system
  for its k-th nearest catalogue glass and reports what changed. Nothing is swapped silently: a model
  glass with no catalogue neighbour inside the stated tolerance is a ``ValueError``.
* **look for other optima.** Damped least squares finds the optimum of the basin it starts in.
  :func:`lens_global_search` runs ``lensopt.optimize_lens`` from the given prescription and from
  seeded random perturbations of the variables (multi-start, the cheap relative of a "hammer" run),
  and returns every local optimum sorted by merit, with optima that coincide flagged as duplicates.
  The merit function is *not* re-implemented: ``merit`` is the dict of keyword arguments that
  ``lensopt.optimize_lens`` / ``lensopt.merit_function`` already take.

Distances (the units are chosen so one unit of each term is a comparable step in the Abbe plane)::

    nd_vd               d = sqrt( (dn_d)^2 + (dV_d / 100)^2 )
    partial_dispersion  d = sqrt( (dn_d)^2 + (dV_d / 100)^2 + (dP_gF / 0.1)^2 )

with ``P_g,F = (n_g - n_F)/(n_F - n_C)``. The model glass of ``raytrace.glass`` is a two-term Cauchy
curve, whose implied P_g,F is the same 0.541 for every model glass, so ``partial_dispersion`` prefers
catalogue glasses that sit near that value; give a measured ``p_gf`` to :func:`glass_nearest` to ask a
different question.
"""
from __future__ import annotations

import copy
import math

import numpy as np

import lensopt as LO
import materials as MAT
import raytrace as RT

__all__ = ["glass_nearest", "lens_substitute_glasses", "lens_global_search"]

METRICS = ("nd_vd", "partial_dispersion")
VD_SCALE = 100.0           # V_d / 100 puts the Abbe number on the scale of n_d (0.2 .. 0.95 against 1.4 .. 1.9)
PGF_SCALE = 0.1            # P_g,F spans about 0.5 .. 0.65: 0.1 of it is one unit
MERIT_KEYS = ("fields", "wavelengths", "rings", "efl_target", "efl_weight", "field_weights", "pupil_fill",
              "min_thickness", "max_thickness", "min_radius", "damping", "tolerance")


def _num(x, name, positive=False):
    if isinstance(x, (bool, np.bool_)) or not isinstance(x, (int, float, np.integer, np.floating)):
        raise ValueError("%s must be a finite number, got %r" % (name, x))
    v = float(x)
    if not math.isfinite(v) or (positive and v <= 0.0):
        raise ValueError("%s must be a finite%s number, got %r" % (name, " positive" if positive else "", x))
    return v


def _default_catalog():
    """The optical glasses of ``materials`` (name, n_d, V_d, P_g,F), every one resolvable by ``raytrace``."""
    return [dict(r) for r in MAT.glass_map("glass") if r["PgF"] is not None]


def _norm_catalog(catalog, op):
    if catalog is None:
        catalog = _default_catalog()
    if not isinstance(catalog, (list, tuple)) or len(catalog) == 0:
        raise ValueError("%s: catalog must be a non-empty list of {name, nd, vd[, PgF]} dicts or None" % op)
    out, seen = [], set()
    for i, r in enumerate(catalog):
        if not isinstance(r, dict) or "name" not in r:
            raise ValueError("%s: catalog entry %d needs a name (a dict with name / nd / vd)" % (op, i))
        name = str(r["name"])
        if name in seen:
            raise ValueError("%s: catalog glass %r is listed twice" % (op, name))
        seen.add(name)
        vd = r.get("vd", r.get("Vd"))
        nd = _num(r.get("nd"), "catalog glass %s nd" % name, True)
        vd = _num(vd, "catalog glass %s vd" % name, True)
        pgf = r.get("PgF", r.get("pgf"))
        pgf = None if pgf is None else _num(pgf, "catalog glass %s PgF" % name)
        out.append({"name": name, "nd": nd, "vd": vd, "PgF": pgf, "medium": r.get("medium", name)})
    return out


def _distance(nd, vd, pgf, g, metric):
    d2 = (nd - g["nd"]) ** 2 + ((vd - g["vd"]) / VD_SCALE) ** 2
    if metric == "partial_dispersion":
        d2 += ((pgf - g["PgF"]) / PGF_SCALE) ** 2
    return math.sqrt(d2)


def _rank(nd, vd, pgf, catalog, metric, op):
    if metric not in METRICS:
        raise ValueError("%s: metric must be one of %s, got %r" % (op, ", ".join(METRICS), metric))
    if metric == "partial_dispersion":
        if pgf is None:
            raise ValueError("%s: metric 'partial_dispersion' needs p_gf (the P_g,F of the glass to match)" % op)
        cand = [g for g in catalog if g["PgF"] is not None]
        if not cand:
            raise ValueError("%s: metric 'partial_dispersion' needs catalogue glasses that carry PgF" % op)
    else:
        cand = catalog
    rows = [(_distance(nd, vd, pgf, g, metric), g["name"], g) for g in cand]
    rows.sort(key=lambda r: (r[0], r[1]))
    return rows


def glass_nearest(n_d=1.5168, v_d=64.17, catalog=None, k: int = 1, metric: str = "nd_vd", p_gf=None) -> dict:
    """(n_d, V_d) に最も近いカタログ硝材 k 個を、距離つきで返す(``table``)。

    The catalogue (default: the 46 optical glasses of ``materials.glass_map``; or a list of
    ``{"name", "nd", "vd"[, "PgF"]}`` dicts) is ranked by the distance in the Abbe plane:
    ``nd_vd`` is ``sqrt(dn_d^2 + (dV_d/100)^2)``; ``partial_dispersion`` adds ``(dP_gF/0.1)^2`` and
    needs *p_gf* (glasses without a PgF are skipped). Ties are broken by name, so the order is
    reproducible. Returns ``{"query", "metric", "neighbours"}`` where each neighbour is ``{"rank",
    "name", "nd", "vd", "PgF", "distance"}``; *k* larger than the catalogue is a ValueError.

    Example::

        glass_nearest(1.5168, 64.17, k=3)["neighbours"][0]["name"]
    """
    op = "glass_nearest"
    nd = _num(n_d, "n_d", True)
    vd = _num(v_d, "v_d", True)
    pgf = None if p_gf is None else _num(p_gf, "p_gf")
    if isinstance(k, (bool, np.bool_)) or not isinstance(k, (int, np.integer)) or k < 1:
        raise ValueError("%s: k must be an integer >= 1, got %r" % (op, k))
    cat = _norm_catalog(catalog, op)
    rows = _rank(nd, vd, pgf, cat, metric, op)
    if k > len(rows):
        raise ValueError("%s: k=%d but only %d catalogue glasses can be ranked" % (op, k, len(rows)))
    nb = [{"rank": i + 1, "name": g["name"], "nd": g["nd"], "vd": g["vd"], "PgF": g["PgF"], "distance": float(d)}
          for i, (d, _n, g) in enumerate(rows[:k])]
    return {"query": {"nd": nd, "vd": vd, "p_gf": pgf}, "metric": metric, "neighbours": nb}


def _model_nd_vd(n):
    """``(nd, vd)`` of a model glass (a pair or a ``raytrace.glass`` dict), else None (a catalogue name, a
    plain index, a Sellmeier or material dict is not a model glass)."""
    if isinstance(n, (tuple, list)) and len(n) == 2:
        return float(n[0]), float(n[1])
    if isinstance(n, dict) and "A" in n and "B" in n and "sellmeier" not in n and "material" not in n:
        return float(n["nd"]), float(n["vd"])
    return None


def _model_pgf(nd, vd):
    g = RT.glass(nd, vd)
    f = lambda wl: g["A"] + g["B"] / wl ** 2
    return (f(MAT.WL_G) - f(RT.WL_F)) / (f(RT.WL_F) - f(RT.WL_C))


def lens_substitute_glasses(system=None, catalog=None, k: int = 1, metric: str = "nd_vd",
                            tolerance: float = 0.05) -> dict:
    """系のモデル硝材 (n_d, V_d) を、k 番目に近いカタログ硝材に置き換える(``table``)。

    Every surface whose medium is a model glass (an ``(nd, vd)`` pair or a ``raytrace.glass`` dict) is
    replaced by the *k*-th nearest catalogue glass (``k=1`` the nearest; see :func:`glass_nearest` for the
    distance and the *metric*). Air, plain indices and glasses that are already named are kept. The
    result is rebuilt through ``raytrace.lens_system``; a last surface with ``t`` None is refocused on
    the new glass. Returns ``{"system", "table", "n_substituted", "n_kept", "metric", "k",
    "tolerance"}``; each table row is ``{"surface", "model_nd", "model_vd", "glass", "nd", "vd", "PgF",
    "distance", "rank", "d_nd", "d_vd"}``.

    **Fail-closed**: a model glass whose k-th neighbour is farther than *tolerance* (in the distance of
    the metric) raises ``ValueError`` naming the surface; nothing is swapped partially. The input is
    not modified. ``None`` uses a crown/flint pair as the example.

    Example::

        r = lens_substitute_glasses(sys_with_model_glasses)
        [(row["surface"], row["glass"], row["distance"]) for row in r["table"]]
    """
    op = "lens_substitute_glasses"
    if system is None:
        system = _example_doublet()
    RT._check_system(system)
    if isinstance(k, (bool, np.bool_)) or not isinstance(k, (int, np.integer)) or k < 1:
        raise ValueError("%s: k must be an integer >= 1, got %r" % (op, k))
    tol = _num(tolerance, "tolerance", True)
    cat = _norm_catalog(catalog, op)
    surf = [dict(s) for s in system["surfaces"]]
    table, kept = [], 0
    for i, s in enumerate(surf):
        mg = _model_nd_vd(s["n"])
        if mg is None:
            kept += 1
            continue
        nd, vd = mg
        rows = _rank(nd, vd, _model_pgf(nd, vd), cat, metric, op)
        if k > len(rows):
            raise ValueError("%s: surface %d: k=%d but only %d catalogue glasses can be ranked" % (op, i, k, len(rows)))
        d, _n, g = rows[k - 1]
        if d > tol:
            raise ValueError("%s: surface %d (n_d=%.4f, V_d=%.2f): the %s nearest catalogue glass %s is at distance "
                             "%.4f > tolerance %.4f" % (op, i, nd, vd, "k=%d" % k, g["name"], d, tol))
        s["n"] = copy.deepcopy(g["medium"])
        table.append({"surface": i, "model_nd": nd, "model_vd": vd, "glass": g["name"], "nd": g["nd"], "vd": g["vd"],
                      "PgF": g["PgF"], "distance": float(d), "rank": int(k), "d_nd": g["nd"] - nd, "d_vd": g["vd"] - vd})
    try:
        out = RT.lens_system(surf, stop=system["stop"], object_mm=system["object_mm"],
                             wavelength_um=system["wavelength_um"], index_object=system["index_object"],
                             image_mm=system["image_mm"], field=system["field"],
                             aim=system.get("aim", "paraxial"), vignetting=system.get("vignetting"),
                             **RT._system_extras(system))
    except ValueError as e:
        raise ValueError("%s: the substituted system cannot be built: %s" % (op, e)) from None
    for key, val in system.items():
        if key not in out:
            out[key] = copy.deepcopy(val)
    return {"system": out, "table": table, "n_substituted": len(table), "n_kept": kept, "metric": metric,
            "k": int(k), "tolerance": tol}


def _example_doublet():
    return RT.lens_system([{"R": 62.0, "t": 0.0, "n": (1.5168, 64.17), "ap": 1.0},
                           {"R": -43.0, "t": 0.0, "n": (1.6200, 36.37)},
                           {"R": -270.0, "t": None, "n": 1.0}], stop=0, object_mm=RT.INF)


def _check_merit(merit, op):
    if merit is None:
        return {}
    if not isinstance(merit, dict):
        raise ValueError("%s: merit must be None or a dict of lensopt.optimize_lens keyword arguments" % op)
    bad = sorted(set(merit) - set(MERIT_KEYS))
    if bad:
        raise ValueError("%s: merit has no key(s) %s (use %s)" % (op, bad, ", ".join(MERIT_KEYS)))
    return dict(merit)


def lens_global_search(system=None, variables=None, merit=None, n_starts: int = 8, seed: int = 0,
                       spread: float = 0.5, iterations: int = 40, duplicate_tolerance: float = 1e-3) -> dict:
    """多始点の局所最適化(lensopt.optimize_lens)で局所解を集め、merit 順に返す(``table``)。

    Start 0 is *system* as given; starts 1 .. *n_starts*-1 move every variable to ``x (1 + spread u)``
    with ``u`` uniform in [-1, 1] drawn from ``numpy.random.default_rng(seed)`` (a variable that is
    zero, such as a flat, moves by *spread* times the typical size of its kind). A perturbed start
    that is not a valid prescription is redrawn (up to 25 times, then ValueError). Every start is
    optimised by ``lensopt.optimize_lens`` with the *same* merit and the *same* EFL target (the EFL
    of *system* unless ``merit["efl_target"]`` says otherwise), so the optima are comparable.
    *merit* is a dict of ``fields wavelengths rings efl_target efl_weight field_weights pupil_fill
    min_thickness max_thickness min_radius damping tolerance``; *variables* are as in ``optimize_lens``.

    Returns ``{"optima", "best", "n_starts", "n_distinct", "basins", "seed", "spread"}``. ``optima``
    holds every start's result sorted by merit (ties by start index): ``{"start", "merit",
    "start_merit", "rms_spot", "efl", "system", "values", "status", "converged", "duplicate_of"}``
    where ``duplicate_of`` is the ``start`` of an earlier (better) optimum with the same variables
    (every variable within *duplicate_tolerance* relative, floor 1e-9) or None. ``basins`` lists the
    distinct optima with the number of starts that reached each. Deterministic for a given seed.

    Example::

        r = lens_global_search(singlet, ["c0", "c1"], {"efl_target": 100.0}, n_starts=12, seed=3)
        r["best"]["merit"], r["n_distinct"]
    """
    op = "lens_global_search"
    if system is None:
        system = RT.lens_system()
    RT._check_system(system)
    if isinstance(n_starts, (bool, np.bool_)) or not isinstance(n_starts, (int, np.integer)) or not 1 <= n_starts <= 200:
        raise ValueError("%s: n_starts must be an integer 1..200, got %r" % (op, n_starts))
    if isinstance(seed, (bool, np.bool_)) or not isinstance(seed, (int, np.integer)) or seed < 0:
        raise ValueError("%s: seed must be a non-negative integer, got %r" % (op, seed))
    spread = _num(spread, "spread", True)
    dtol = _num(duplicate_tolerance, "duplicate_tolerance", True)
    mk = _check_merit(merit, op)
    ns = len(system["surfaces"])
    if variables is None:
        varlist = LO._default_variables(system)
    else:
        if isinstance(variables, (str, dict)):
            variables = [variables]
        varlist = [LO._parse_variable(v, ns) for v in variables]
    if not varlist:
        raise ValueError("%s: at least one variable is required" % op)
    if len(set(varlist)) != len(varlist):
        raise ValueError("%s: duplicate variables" % op)
    bounds = {"min_thickness": RT._finite(mk.get("min_thickness", 0.5), "min_thickness", nonneg=True),
              "max_thickness": None if mk.get("max_thickness") is None else RT._finite(mk["max_thickness"], "max_thickness", positive=True),
              "min_radius": RT._finite(mk.get("min_radius", 1.0), "min_radius", positive=True)}
    if "efl_target" not in mk:
        e = RT.paraxial_trace(system)["efl"]
        mk["efl_target"] = e if math.isfinite(e) and e != 0.0 else None
    x0 = np.array([LO._get(system, v) for v in varlist], dtype=np.float64)
    scale = np.empty_like(x0)
    for j, v in enumerate(varlist):
        same = [abs(x0[i]) for i, w in enumerate(varlist) if w[0] == v[0] and x0[i] != 0.0]
        floor = {"c": 1e-2, "t": 1.0, "k": 1.0, "A": 1e-6}[v[0]]
        scale[j] = abs(x0[j]) if x0[j] != 0.0 else (float(np.median(same)) if same else floor)
    rng = np.random.default_rng(int(seed))
    results = []
    for s in range(int(n_starts)):
        if s == 0:
            start = system
        else:
            start = None
            for _try in range(25):
                u = rng.uniform(-1.0, 1.0, size=len(x0))
                x = x0 + spread * u * scale
                try:
                    start = LO._rebuild(system, x, varlist, bounds)
                    m = LO.merit_function(start, **{k: mk[k] for k in ("fields", "wavelengths", "rings", "efl_target",
                                                                       "efl_weight", "field_weights", "pupil_fill") if k in mk})
                    if math.isfinite(m["merit"]):
                        break
                    start = None
                except ValueError:
                    start = None
            if start is None:
                raise ValueError("%s: start %d: no valid perturbed prescription in 25 draws (reduce spread)" % (op, s))
        r = LO.optimize_lens(start, variables=[_spec(v) for v in varlist], iterations=int(iterations), **mk)
        vals = np.array([LO._get(r["system"], v) for v in varlist], dtype=np.float64)
        results.append({"start": s, "merit": r["merit_final"], "start_merit": r["merit_initial"],
                        "rms_spot": r["rms_final"], "efl": r["efl_final"], "system": r["system"],
                        "values": vals.tolist(), "status": r["status"], "converged": r["converged"],
                        "duplicate_of": None})
    results.sort(key=lambda r: (r["merit"], r["start"]))
    kept = []                                                   # distinct optima, best first
    for r in results:
        v = np.array(r["values"])
        for q in kept:
            w = np.array(q["values"])
            if np.all(np.abs(v - w) <= dtol * np.maximum(np.maximum(np.abs(v), np.abs(w)), 1e-9)):
                r["duplicate_of"] = q["start"]
                q["_count"] += 1
                break
        else:
            r["_count"] = 1
            kept.append(r)
    basins = [{"start": q["start"], "merit": q["merit"], "values": q["values"], "n_starts": q.pop("_count")}
              for q in kept]
    for r in results:
        r.pop("_count", None)
    return {"optima": results, "best": results[0], "n_starts": int(n_starts), "n_distinct": len(kept),
            "basins": basins, "seed": int(seed), "spread": spread}


def _spec(var):
    kind, i, j = var
    return {"c": "c%d", "t": "t%d", "k": "k%d"}[kind] % i if kind != "A" else "A%d_%d" % (4 + 2 * j, i)
