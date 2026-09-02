# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""lensopt — damped-least-squares lens optimisation on top of ``raytrace``.

``raytrace`` *evaluates* a prescription (spots, OPD, Seidel sums); this module
*changes* it. The classic designer's loop is Levenberg–Marquardt (damped least
squares, DLS — Meiron 1965, Wynne & Wormell 1963) on a residual vector made of

* the transverse ray aberrations of a pupil-filling bundle at several field
  points and wavelengths (each ray's image-plane offset from its chief ray,
  in mm — the RMS of these is the RMS spot radius);
* constraint residuals — the effective focal length held to a target with a
  heavy weight, and optional bounds handled by clamping.

Variables are surface parameters: curvature (``"c<i>"`` — radius ``"R<i>"`` is
accepted and mapped to curvature, so a surface can pass through flat), thickness
``"t<i>"``, conic ``"k<i>"`` and even aspheric coefficients ``"A4_<i>"``,
``"A6_<i>"`` …; the Jacobian is forward-differenced (the systems here are tens
of variables, not thousands), the normal equations are damped with
``λ·diag(JᵀJ)`` (Marquardt scaling) and the damping is adapted per step.

Every step re-validates the prescription through ``raytrace.lens_system`` —
a step that produces an impossible lens (aperture beyond the conic, negative
thickness) is rejected and the damping raised, so the optimiser cannot return
a prescription the tracer would refuse. The result is deterministic.

Ground truth used by the tests (``tests/test_lensopt.py``): the minimum-
spherical-aberration bending of a thin singlet (Coddington shape factor
``q = 2(n²−1)/(n+2)`` for a distant object), the plano-hyperbolic stigmatic
singlet (``k = −n²``, Descartes), and monotone merit decrease with the EFL
held to the target.
"""
from __future__ import annotations

import math

import numpy as np

import raytrace as RT

INF = float("inf")
MAX_VARIABLES = 64
MAX_ITERATIONS = 500


# --------------------------------------------------------------------------- #
# variables
# --------------------------------------------------------------------------- #
def _parse_variable(spec, n_surf):
    """``"R2"`` / ``"c2"`` / ``"t0"`` / ``"k1"`` / ``"A4_1"`` or ``{"surface": i, "param": ...}``."""
    if isinstance(spec, dict):
        kind = str(spec.get("param", "")).strip()
        idx = spec.get("surface", None)
    elif isinstance(spec, str):
        s = spec.strip()
        if "_" in s:
            kind, idx = s.split("_", 1)
        else:
            j = 0
            while j < len(s) and not s[j].isdigit():
                j += 1
            kind, idx = s[:j], s[j:]
        try:
            idx = int(idx)
        except ValueError:
            raise ValueError("cannot parse variable %r (want e.g. 'R0', 't1', 'k2', 'A4_1')" % spec)
    else:
        raise ValueError("variable must be a string like 'R0' or a dict, got %r" % type(spec).__name__)
    if idx is None or not isinstance(idx, (int, np.integer)) or isinstance(idx, bool):
        raise ValueError("variable %r needs an integer surface index" % (spec,))
    if not 0 <= idx < n_surf:
        raise ValueError("variable %r: surface index %d out of range 0..%d" % (spec, idx, n_surf - 1))
    if kind in ("R", "c"):
        return ("c", int(idx), 0)
    if kind == "t":
        return ("t", int(idx), 0)
    if kind == "k":
        return ("k", int(idx), 0)
    if kind.startswith("A") and kind[1:].isdigit():
        order = int(kind[1:])
        if order < 4 or order % 2 or order > 18:
            raise ValueError("aspheric variable %r: order must be even, 4..18" % (spec,))
        return ("A", int(idx), (order - 4) // 2)
    raise ValueError("unknown variable kind %r in %r (R/c, t, k, A4..A18)" % (kind, spec))


def _get(system, var):
    kind, i, j = var
    s = system["surfaces"][i]
    if kind == "c":
        return 0.0 if s["R"] == INF else 1.0 / s["R"]
    if kind == "t":
        return 0.0 if s["t"] is None else float(s["t"])
    if kind == "k":
        return float(s["k"])
    a = s["asph"]
    return float(a[j]) if j < len(a) else 0.0


def _rebuild(system, values, variables, bounds):
    """A new validated system with *variables* set to *values* (ValueError if impossible)."""
    surf = [dict(s) for s in system["surfaces"]]
    for v, var in zip(values, variables):
        kind, i, j = var
        s = surf[i]
        if kind == "c":
            c = float(v)
            cmax = 1.0 / bounds["min_radius"]
            c = max(-cmax, min(cmax, c))
            s["R"] = INF if abs(c) < 1e-12 else 1.0 / c
        elif kind == "t":
            t = float(v)
            t = max(bounds["min_thickness"], t)
            if bounds["max_thickness"] is not None:
                t = min(bounds["max_thickness"], t)
            s["t"] = t
        elif kind == "k":
            s["k"] = float(v)
        else:
            a = list(s["asph"])
            while len(a) <= j:
                a.append(0.0)
            a[j] = float(v)
            s["asph"] = tuple(a)
    return RT.lens_system(surf, stop=system["stop"], object_mm=system["object_mm"],
                          wavelength_um=system["wavelength_um"], index_object=system["index_object"],
                          image_mm=system["image_mm"], field=system["field"])


def _default_variables(system):
    out = []
    for i, s in enumerate(system["surfaces"]):
        if s["R"] != INF:
            out.append(("c", i, 0))
    if not out:
        raise ValueError("no finite radius to vary; pass variables= explicitly")
    return out


# --------------------------------------------------------------------------- #
# merit
# --------------------------------------------------------------------------- #
def _fields(system, fields):
    if fields is None:
        f = float(system["field"])
        if f == 0.0:
            return [0.0]
        return [0.0, 0.7 * f, f]
    if isinstance(fields, (int, float)) and not isinstance(fields, bool):
        fields = [fields]
    fl = [RT._finite(v, "field") for v in fields]
    if not fl:
        raise ValueError("fields must not be empty")
    return fl


def _residuals(system, fields, wavelengths, rings, efl_target, efl_weight, field_weights, pupil_fill):
    """Residual vector (mm): ray offsets from the chief ray at every field / wavelength + constraints."""
    res = []
    lost = 0
    for fw, field in zip(field_weights, fields):
        for wl in wavelengths:
            b = RT.ray_bundle(system, field=field, rings=rings, wavelength_um=wl, pupil_fill=pupil_fill)
            xy = b["image_xy"]
            chief = b["chief_xy"]
            if not np.isfinite(chief).all():
                raise ValueError("the chief ray does not reach the image plane at field %r" % field)
            d = xy - chief
            bad = ~b["valid"]
            lost += int(bad.sum())
            # a vignetted / TIR ray is charged a fixed large aberration so the optimiser
            # is pushed away from prescriptions that lose rays (continuous in the rest)
            d = np.where(bad[:, None], 1.0, d)
            res.append((math.sqrt(fw) * d).ravel())
    r = np.concatenate(res)
    if efl_target is not None:
        p = RT.paraxial_trace(system)
        r = np.concatenate([r, [efl_weight * (p["efl"] - efl_target) / abs(efl_target)]])
    return r, lost


def merit_function(system, fields=None, wavelengths=None, rings=4, efl_target=None,
                   efl_weight=None, field_weights=None, pupil_fill=0.98):
    """The DLS merit ``Σ residual²`` and its parts for one prescription (``table``).

    Same residual definition as :func:`optimize_lens`: transverse ray offsets
    from the chief ray (mm) over a hexapolar pupil of *rings* rings at each of
    *fields* (default: on axis, or 0 / 0.7 / 1.0 of the system field) and
    *wavelengths* (default: the system wavelength), plus ``efl_weight·(EFL −
    efl_target)/efl_target`` when a target is given. Returns ``merit``,
    ``rms_spot`` (RMS over all rays, mm), ``rms_by_field``, ``efl``,
    ``rays_lost`` and the residual count.
    """
    RT._check_system(system)
    fl = _fields(system, fields)
    wls = [system["wavelength_um"]] if wavelengths is None else \
        [RT._finite(w, "wavelength", positive=True) for w in (wavelengths if isinstance(wavelengths, (list, tuple)) else [wavelengths])]
    if not wls:
        raise ValueError("wavelengths must not be empty")
    rings = int(rings)
    if rings < 1 or rings > 64:
        raise ValueError("rings must be 1..64")
    pupil_fill = RT._finite(pupil_fill, "pupil_fill", positive=True)
    if pupil_fill > 1.0:
        raise ValueError("pupil_fill must be <= 1")
    if field_weights is None:
        fw = [1.0] * len(fl)
    else:
        fw = [RT._finite(w, "field_weight", nonneg=True) for w in field_weights]
        if len(fw) != len(fl):
            raise ValueError("field_weights must match fields (%d vs %d)" % (len(fw), len(fl)))
    if efl_target is not None:
        efl_target = RT._finite(efl_target, "efl_target")
        if efl_target == 0.0:
            raise ValueError("efl_target must be non-zero")
    n_rays = len(RT._pupil_grid(rings)[0]) * len(fl) * len(wls)
    if efl_weight is None:
        efl_weight = 10.0 * math.sqrt(n_rays)              # 1 % EFL error ~ 0.1 mm rms blur equivalent
    else:
        efl_weight = RT._finite(efl_weight, "efl_weight", nonneg=True)
    r, lost = _residuals(system, fl, wls, rings, efl_target, efl_weight, fw, pupil_fill)
    by_field = {}
    for fw_i, field in zip(fw, fl):
        st = []
        for wl in wls:
            b = RT.ray_bundle(system, field=field, rings=rings, wavelength_um=wl, pupil_fill=pupil_fill)
            d = (b["image_xy"] - b["chief_xy"])[b["valid"]]
            st.append(d)
        d = np.concatenate(st) if st else np.zeros((0, 2))
        by_field[float(field)] = float(np.sqrt(np.mean(d[:, 0] ** 2 + d[:, 1] ** 2))) if len(d) else INF
    ray_part = r[:-1] if efl_target is not None else r
    p = RT.paraxial_trace(system)
    return {"merit": float(np.dot(r, r)), "rms_spot": float(np.sqrt(np.mean(ray_part * ray_part) * 2.0)),
            "rms_by_field": by_field, "efl": p["efl"], "rays_lost": int(lost),
            "n_residuals": int(len(r)), "fields": fl, "wavelengths": wls,
            "efl_target": efl_target, "efl_weight": float(efl_weight)}


# --------------------------------------------------------------------------- #
# optimiser
# --------------------------------------------------------------------------- #
def optimize_lens(system, variables=None, fields=None, wavelengths=None, rings=4,
                  efl_target=None, efl_weight=None, field_weights=None, iterations=30,
                  damping=1e-3, tolerance=1e-7, min_thickness=0.5, max_thickness=None,
                  min_radius=1.0, pupil_fill=0.98):
    """Damped-least-squares (Levenberg–Marquardt) optimisation of a prescription (``table``).

    *variables*: surface parameters to move — strings ``"R<i>"``/``"c<i>"``
    (curvature; a radius may pass through flat), ``"t<i>"`` (thickness),
    ``"k<i>"`` (conic), ``"A4_<i>"``, ``"A6_<i>"`` … (even aspheric
    coefficients). Default: every finite radius. *efl_target*: hold the
    effective focal length (default: the starting EFL, so a design does not
    "improve" by getting longer); pass ``0`` / ``False`` to leave it free.
    Fields / wavelengths / rings / weights as in :func:`merit_function`.

    Each iteration builds the Jacobian by forward differences, solves
    ``(JᵀJ + λ diag(JᵀJ)) δ = −Jᵀr`` and accepts the step only if the merit
    falls (then λ /= 3; otherwise λ ×= 4 and retried, up to 6 times); a step
    that yields an invalid prescription counts as a failure. Stops when the
    relative merit change is below *tolerance* twice in a row, when λ blows
    past 1e8, or after *iterations*. Thickness is clamped to
    ``[min_thickness, max_thickness]`` and ``|R| >= min_radius``.

    Returns ``{"system": optimised prescription, "merit_initial",
    "merit_final", "rms_initial", "rms_final", "efl_initial", "efl_final",
    "history": [merit per accepted iteration], "iterations", "converged",
    "variables": [{"name", "surface", "initial", "final"}], "rays_lost"}``.
    """
    RT._check_system(system)
    n_surf = len(system["surfaces"])
    if variables is None:
        varlist = _default_variables(system)
    else:
        if isinstance(variables, (str, dict)):
            variables = [variables]
        varlist = [_parse_variable(v, n_surf) for v in variables]
    if not varlist:
        raise ValueError("at least one variable is required")
    if len(varlist) > MAX_VARIABLES:
        raise ValueError("too many variables (%d > %d)" % (len(varlist), MAX_VARIABLES))
    if len(set(varlist)) != len(varlist):
        raise ValueError("duplicate variables")
    for kind, i, _ in varlist:
        s = system["surfaces"][i]
        if kind == "t" and s["t"] is None:
            raise ValueError("t%d is the image distance (None); give it a value or vary another surface" % i)
        if kind == "k" and s["R"] == INF:
            raise ValueError("k%d: a flat has no conic constant" % i)
    iterations = int(iterations)
    if iterations < 1 or iterations > MAX_ITERATIONS:
        raise ValueError("iterations must be 1..%d" % MAX_ITERATIONS)
    lam = RT._finite(damping, "damping", positive=True)
    tolerance = RT._finite(tolerance, "tolerance", nonneg=True)
    bounds = {"min_thickness": RT._finite(min_thickness, "min_thickness", nonneg=True),
              "max_thickness": None if max_thickness is None else RT._finite(max_thickness, "max_thickness", positive=True),
              "min_radius": RT._finite(min_radius, "min_radius", positive=True)}
    if bounds["max_thickness"] is not None and bounds["max_thickness"] < bounds["min_thickness"]:
        raise ValueError("max_thickness < min_thickness")
    if efl_target is None:
        efl_target = RT.paraxial_trace(system)["efl"]
        if not math.isfinite(efl_target) or efl_target == 0.0:
            efl_target = None
    elif efl_target is False or efl_target == 0:
        efl_target = None
    m0 = merit_function(system, fields=fields, wavelengths=wavelengths, rings=rings, efl_target=efl_target,
                        efl_weight=efl_weight, field_weights=field_weights, pupil_fill=pupil_fill)
    fl, wls, ew, fw = m0["fields"], m0["wavelengths"], m0["efl_weight"], None
    if field_weights is None:
        fw = [1.0] * len(fl)
    else:
        fw = [float(w) for w in field_weights]

    def resid(sys_):
        return _residuals(sys_, fl, wls, int(rings), efl_target, ew, fw, pupil_fill)[0]

    x = np.array([_get(system, v) for v in varlist], dtype=np.float64)
    cur = system
    r = resid(cur)
    merit = float(np.dot(r, r))
    history = [merit]
    steps = {"c": 1e-5, "t": 1e-3, "k": 1e-3, "A": None}
    converged = False
    small_count = 0
    it = 0
    for it in range(1, iterations + 1):
        # Jacobian by forward differences
        J = np.zeros((len(r), len(x)))
        for j, var in enumerate(varlist):
            kind = var[0]
            if kind == "A":
                h = 1e-4 * max(1.0, abs(x[j])) * (0.1 ** var[2])   # higher orders: smaller coefficients
            else:
                h = steps[kind] * max(1.0, abs(x[j]))
            xp = x.copy(); xp[j] += h
            try:
                rp = resid(_rebuild(cur, xp, varlist, bounds))
            except (ValueError, FloatingPointError):
                xp = x.copy(); xp[j] -= h
                rp = resid(_rebuild(cur, xp, varlist, bounds))
                h = -h
            J[:, j] = (rp - r) / h
        JtJ = J.T @ J
        Jtr = J.T @ r
        diag = np.diag(JtJ).copy()
        diag[diag <= 0] = 1e-12
        accepted = False
        for _ in range(6):
            A = JtJ + lam * np.diag(diag)
            try:
                delta = np.linalg.solve(A, -Jtr)
            except np.linalg.LinAlgError:
                lam *= 4.0
                continue
            xn = x + delta
            try:
                sys_n = _rebuild(cur, xn, varlist, bounds)
                rn = resid(sys_n)
            except (ValueError, FloatingPointError):
                lam *= 4.0
                continue
            mn = float(np.dot(rn, rn))
            if math.isfinite(mn) and mn < merit:
                rel = (merit - mn) / max(merit, 1e-300)
                # snap the variables to what _rebuild actually applied (bounds)
                x = np.array([_get(sys_n, v) for v in varlist], dtype=np.float64)
                cur, r, merit = sys_n, rn, mn
                history.append(merit)
                lam = max(lam / 3.0, 1e-12)
                accepted = True
                small_count = small_count + 1 if rel < tolerance else 0
                break
            lam *= 4.0
        if not accepted:
            if lam > 1e8:
                converged = True
                break
            small_count += 1
        if small_count >= 2:
            converged = True
            break
    mf = merit_function(cur, fields=fl, wavelengths=wls, rings=rings, efl_target=efl_target,
                        efl_weight=ew, field_weights=fw, pupil_fill=pupil_fill)
    names = {"c": "R%d", "t": "t%d", "k": "k%d"}
    vars_out = []
    for var, x0 in zip(varlist, [_get(system, v) for v in varlist]):
        kind, i, j = var
        name = ("A%d_%d" % (4 + 2 * j, i)) if kind == "A" else names[kind] % i
        v0, v1 = x0, _get(cur, var)
        if kind == "c":
            v0 = INF if v0 == 0.0 else 1.0 / v0
            v1 = INF if v1 == 0.0 else 1.0 / v1
        vars_out.append({"name": name, "surface": i, "initial": float(v0), "final": float(v1)})
    return {"system": cur, "merit_initial": m0["merit"], "merit_final": mf["merit"],
            "rms_initial": m0["rms_spot"], "rms_final": mf["rms_spot"],
            "rms_by_field": mf["rms_by_field"], "efl_initial": m0["efl"], "efl_final": mf["efl"],
            "efl_target": efl_target, "history": [float(h) for h in history],
            "iterations": int(it), "converged": bool(converged), "variables": vars_out,
            "rays_lost": mf["rays_lost"], "damping_final": float(lam)}


def bend_singlet(focal_mm=100.0, index=1.5168, thickness_mm=3.0, semi_aperture_mm=5.0,
                 object_mm=INF, shape_factor=None):
    """A thin singlet of given focal length at a Coddington shape factor (``table``).

    ``q = (R2 + R1)/(R2 − R1)``; the thin-lens radii for focal length *f* are
    ``R1 = 2f(n−1)/(q+1)``, ``R2 = −2f(n−1)/(1−q)``. Default *shape_factor*:
    the third-order minimum-spherical bending for a distant object,
    ``q = 2(n²−1)/(n+2)`` (Coddington) — the closed form
    :func:`optimize_lens` is checked against. Returns the prescription plus
    ``shape_factor``, ``R1``, ``R2`` and the RMS spot on axis.
    """
    f = RT._finite(focal_mm, "focal_mm")
    if f == 0.0:
        raise ValueError("focal_mm must be non-zero")
    n = RT.refractive_index(index)
    t = RT._finite(thickness_mm, "thickness_mm", nonneg=True)
    ap = RT._finite(semi_aperture_mm, "semi_aperture_mm", positive=True)
    if shape_factor is None:
        q = 2.0 * (n * n - 1.0) / (n + 2.0)
    else:
        q = RT._finite(shape_factor, "shape_factor")
    R1 = INF if abs(q + 1.0) < 1e-12 else 2.0 * f * (n - 1.0) / (q + 1.0)
    R2 = INF if abs(1.0 - q) < 1e-12 else -2.0 * f * (n - 1.0) / (1.0 - q)
    sysd = RT.lens_system([{"R": R1, "t": t, "n": index, "ap": ap}, {"R": R2, "t": None, "n": 1.0}],
                          stop=0, object_mm=object_mm)
    st = RT.spot_stats(sysd)
    p = RT.paraxial_trace(sysd)
    return {"system": sysd, "shape_factor": float(q), "R1": float(R1), "R2": float(R2),
            "efl": p["efl"], "rms_spot": st["rms_radius"], "index": float(n)}
