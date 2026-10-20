# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""lenssolve — solves, pickups, afocal systems and a curved image surface for sequential lens design.

A *solve* is a rule attached to one surface that sets its curvature or the thickness after it from the rest of the
prescription, so that the design keeps a first-order requirement while other things are changed. The rules are
declarative: they live in the surface dict (``surface["solve"]``), the resolved numbers sit next to them in ``R`` / ``t``,
and every ``raytrace`` trace re-resolves them first, so editing the stop radius or a glass lets the solved quantities
settle again. A rule is never a hidden state: write the system out (``.zmx``) and read it back and the rules come back.

Kinds (the first-order quantities are the paraxial marginal ray, the one from the axial object point through the rim
of the stop at ``+ap``, and the paraxial chief ray, the one through the stop centre at the system ``field``)::

    thickness t     marginal_ray_height  h      t such that the marginal ray is at height h at the next surface
                    chief_ray_height     h      the same for the chief ray (needs a field != 0)
                    paraxial_image              marginal height 0: the paraxial focus (what ``t=None`` on the last surface was)
    curvature c     marginal_ray_angle   angle_deg   c such that the marginal ray leaves at that paraxial angle (tan)
                    chief_ray_angle      angle_deg   the same for the chief ray
                    f_number             fno    image-space F/# 1/(2 n' |u'|) of the whole system by this curvature
                    concentric           with_surface, mode   centre of curvature shared with (or at the vertex of) an earlier surface
                    aplanatic                   c such that the marginal ray's axial object point is this surface's aplanatic point
    pickup          pickup               source, quantity, scale, offset   copy c / t / an aspheric coefficient from another surface

Surfaces are resolved in order, sweep after sweep until nothing moves (1e-12); a solve in front of the stop changes the
marginal ray's scale, so a few sweeps may be needed, and ``ValueError`` follows if they do not settle. The F/# solve is
a one-dimensional root find on the curvature (a scan for the sign changes, then bisection to machine precision, a
residual gate of 1e-9 on the F/#); the F/# has **two roots** in general (a positive and a negative surface power give the
same ``|u'|``), the one nearest the curvature the rule was set at is used and the others are reported.

Fail-closed: an unknown kind, an argument the kind does not take, a circular pickup, a solve on an ideal lens's
curvature, a thickness solve in front of the stop (it would move the stop and with it the marginal ray's normalisation),
a chief-ray solve on axis, a ray parallel to the axis, a thickness the solve would make negative (except the last one,
where the image may be virtual), a root that is not found, are all ``ValueError``.

Also here: **afocal systems** (``afocal_system``, ``lens_afocal_report``: the image space is collimated; angular
magnification and angular aberrations in arcminutes), the **curved image surface** (``lens_image_surface``,
``lens_petzval_radius``) and the ``.zmx`` round trip of the solves (``lens_zmx_solves_roundtrip``).

Ops::

    lens_apply_solves(system)               -> system with every solve resolved (pure: a copy, the rules are kept)
    lens_solve_set(system, surface, kind)   -> system with that rule set
    lens_solve_clear(system, surface)       -> system with the rule removed (the solved numbers stay)
    lens_solves_list(system)                -> the rules with their resolved values and the achieved quantities
    afocal_system(system)                   -> an afocal system (or an ideal two-lens telescope)
    lens_afocal_report(system)              -> angular magnification, exit pupil, angular spot per field
    lens_image_surface(system, R)           -> system with a curved image surface (R = "petzval" for the Petzval radius)
    lens_petzval_radius(system)             -> the Petzval radius of the image surface
    lens_zmx_solves_roundtrip(system)       -> write the solves to .zmx, read them back, write again
"""
from __future__ import annotations

import json
import math

import numpy as np

import raytrace as RT

__all__ = ["lens_apply_solves", "lens_solve_set", "lens_solve_clear", "lens_solves_list", "afocal_system",
           "lens_afocal_report", "lens_image_surface", "lens_petzval_radius", "lens_zmx_solves_roundtrip"]

INF = float("inf")
_REQ = object()

#: kind -> (target quantity, {argument: default}); ``_REQ`` marks a required argument.
SOLVE_KINDS = {
    "marginal_ray_height": ("t", {"h": 0.0}),
    "chief_ray_height": ("t", {"h": 0.0, "field": None}),
    "paraxial_image": ("t", {}),
    "marginal_ray_angle": ("c", {"angle_deg": 0.0}),
    "chief_ray_angle": ("c", {"angle_deg": 0.0, "field": None}),
    "f_number": ("c", {"fno": _REQ, "c0": None, "span": None}),
    "concentric": ("c", {"with_surface": None, "mode": "centre"}),
    "aplanatic": ("c", {}),
    "pickup": (None, {"source": _REQ, "quantity": "c", "scale": 1.0, "offset": 0.0}),
}
_QUANTITIES = ("c", "t") + tuple("A%d" % k for k in range(2, 19, 2))
_MAX_SWEEPS = 100
_SETTLE = 1e-12
_FNO_GRID = 801
_CACHE: dict = {}
_CACHE_MAX = 256


def _num(x, name):
    if isinstance(x, (bool, np.bool_)) or not isinstance(x, (int, float, np.integer, np.floating)):
        raise ValueError("%s must be a finite number, got %r" % (name, x))
    x = float(x)
    if not math.isfinite(x):
        raise ValueError("%s must be finite, got %r" % (name, x))
    return x


def _int(x, name, lo, hi):
    if isinstance(x, (bool, np.bool_)) or not isinstance(x, (int, np.integer)):
        raise ValueError("%s must be an integer, got %r" % (name, x))
    x = int(x)
    if not lo <= x <= hi:
        raise ValueError("%s must be %d..%d, got %d" % (name, lo, hi, x))
    return x


def _check_rule(rule, i, n_surf, where="surface"):
    """Validate a solve rule for surface *i* and return the normalised dict (all arguments present, ``target`` set)."""
    if not isinstance(rule, dict) or "kind" not in rule:
        raise ValueError("%s: a solve rule is a dict with a 'kind' (one of %s), got %r"
                         % (where, ", ".join(SOLVE_KINDS), rule))
    kind = rule["kind"]
    if kind not in SOLVE_KINDS:
        raise ValueError("%s: unknown solve kind %r; the kinds are %s" % (where, kind, ", ".join(SOLVE_KINDS)))
    target, spec = SOLVE_KINDS[kind]
    extra = sorted(set(rule) - set(spec) - {"kind", "target"})
    if extra:
        raise ValueError("%s: solve %r takes %s, not %s" % (where, kind, sorted(spec) or "no arguments", extra))
    out = {"kind": kind}
    for name, default in spec.items():
        v = rule.get(name, default)
        if v is _REQ:
            raise ValueError("%s: solve %r needs the argument %r" % (where, kind, name))
        out[name] = v
    if kind in ("marginal_ray_height", "chief_ray_height"):
        out["h"] = _num(out["h"], "%s: h" % where)
    if kind in ("marginal_ray_angle", "chief_ray_angle"):
        out["angle_deg"] = _num(out["angle_deg"], "%s: angle_deg" % where)
        if abs(out["angle_deg"]) >= 89.0:
            raise ValueError("%s: angle_deg must be within +-89 degrees" % where)
    if kind in ("chief_ray_height", "chief_ray_angle") and out["field"] is not None:
        out["field"] = _num(out["field"], "%s: field" % where)
    if kind == "f_number":
        out["fno"] = _num(out["fno"], "%s: fno" % where)
        if not out["fno"] > 0.0:
            raise ValueError("%s: fno must be > 0, got %r" % (where, out["fno"]))
        if out["c0"] is not None:
            out["c0"] = _num(out["c0"], "%s: c0" % where)
        if out["span"] is not None:
            out["span"] = _num(out["span"], "%s: span" % where)
            if not out["span"] > 0.0:
                raise ValueError("%s: span must be > 0" % where)
    if kind == "concentric":
        ws = out["with_surface"]
        if ws is None:
            if i < 1:
                raise ValueError("%s: 'concentric' with the previous surface needs a surface in front of it" % where)
            ws = i - 1
        ws = _int(ws, "%s: with_surface" % where, 0, n_surf - 1)
        if ws >= i:
            raise ValueError("%s: with_surface must be a surface in front of this one (< %d), got %d" % (where, i, ws))
        out["with_surface"] = ws
        if out["mode"] not in ("centre", "vertex"):
            raise ValueError("%s: mode must be 'centre' (shared centre of curvature) or 'vertex', got %r"
                             % (where, out["mode"]))
    if kind == "pickup":
        out["source"] = _int(out["source"], "%s: source" % where, 0, n_surf - 1)
        if out["source"] == i:
            raise ValueError("%s: a surface cannot pick up from itself (circular pickup)" % where)
        if out["quantity"] not in _QUANTITIES:
            raise ValueError("%s: pickup quantity must be one of %s, got %r" % (where, ", ".join(_QUANTITIES),
                                                                                out["quantity"]))
        out["scale"] = _num(out["scale"], "%s: scale" % where)
        out["offset"] = _num(out["offset"], "%s: offset" % where)
        q = out["quantity"]
        target = "c" if q == "c" else "t" if q == "t" else "A"
    out["target"] = target
    return out


# --------------------------------------------------------------------------- #
# first-order machinery on a work copy of the surfaces
# --------------------------------------------------------------------------- #
class _Ctx:
    """The paraxial model (curvature, signed thickness, signed index, ideal-lens power) of a work list of surfaces."""

    def __init__(self, system, work):
        self.system = system
        self.work = work
        tmp = {"surfaces": work, "index_object": system["index_object"], "wavelength_um": system["wavelength_um"]}
        self.c, self.t, self.n = RT._paraxial_model(tmp)
        self.pw = RT._paraxial_power(tmp)
        self.stop = system["stop"]
        self.ap = float(work[self.stop]["ap"])
        self.obj = system["object_mm"]

    def trace(self, y0, u0, c=None):
        return RT._trace_paraxial(self.c if c is None else c, self.t, self.n, y0, u0, pw=self.pw)

    def y_stop(self, y0, u0, c=None):
        ys, _ = self.trace(y0, u0, c)
        return float(ys[self.stop])

    def marginal_start(self, c=None):
        """(y0, u0) of the paraxial marginal ray: the ray from the axial object point that is at +ap on the stop."""
        if self.obj == INF:
            a = self.y_stop(1.0, 0.0, c)
            if abs(a) < 1e-15:
                raise ValueError("the stop cannot be imaged into object space (degenerate system); no marginal ray")
            return self.ap / a, 0.0
        a = self.y_stop(self.obj, 1.0, c)
        if abs(a) < 1e-15:
            raise ValueError("the stop cannot be reached from the axial object point; no marginal ray")
        s = self.ap / a
        return s * self.obj, s

    def chief_start(self, field, c=None):
        """(y0, u0) of the paraxial chief ray (y = 0 at the stop) at *field* (degrees, or object height in mm)."""
        a = self.y_stop(1.0, 0.0, c)
        b = self.y_stop(0.0, 1.0, c)
        if self.obj == INF:
            if abs(a) < 1e-15:
                raise ValueError("the stop cannot be imaged into object space (degenerate system); no chief ray")
            u0 = math.tan(math.radians(field))
            return -b * u0 / a, u0
        den = a * self.obj + b
        if abs(den) < 1e-15:
            raise ValueError("the stop cannot be reached from the object point; no chief ray")
        s = -a * field / den
        return field + s * self.obj, s


def _curv(R):
    return 0.0 if R == INF else 1.0 / R


def _radius_of(c):
    return INF if c == 0.0 else 1.0 / c


def _field_of(system, rule):
    f = system["field"] if rule.get("field") is None else rule["field"]
    if f == 0.0:
        raise ValueError("a chief-ray solve needs a field != 0 (on axis the chief ray is the axis); set the "
                         "system's field or the rule's field")
    return f


def _fno_curve(ctx, i):
    """Image-space F/# 1/(2 n' |u'|) of the marginal ray as a function of the curvature of surface *i*."""
    base = ctx.c.copy()

    def f(cj):
        base[i] = cj
        try:
            y0, u0 = ctx.marginal_start(base)
        except ValueError:
            return float("nan")
        _, us = ctx.trace(y0, u0, base)
        v = abs(ctx.n[-1] * us[-1])
        return INF if v < 1e-300 else 1.0 / (2.0 * v)
    return f


def _extent_ok(s, c):
    k = s["k"]
    return not (c != 0.0 and k > -1.0 and s["ap"] is not None and (1.0 + k) * (s["ap"] * c) ** 2 > 1.0)


def _solve_fno(ctx, i, rule, s, extra=0.0):
    f = _fno_curve(ctx, i)
    target = rule["fno"]
    c_here = ctx.c[i]
    c0 = rule["c0"] + extra if rule["c0"] is not None else c_here
    span = rule["span"] if rule["span"] is not None else max(5.0 * abs(c0), 0.1)
    grid = np.linspace(c0 - span, c0 + span, _FNO_GRID)
    vals = np.array([f(float(g)) - target for g in grid])
    roots = []
    for a, b, fa, fb in zip(grid[:-1], grid[1:], vals[:-1], vals[1:]):
        if not (math.isfinite(fa) and math.isfinite(fb)):
            continue
        if fa == 0.0:
            roots.append(float(a))
            continue
        if fa * fb > 0.0:
            continue
        lo, hi, flo = float(a), float(b), float(fa)
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            fm = f(mid) - target
            if not math.isfinite(fm):
                break
            if fm == 0.0 or hi - lo <= 1e-16 * max(1.0, abs(mid)):
                lo = hi = mid
                break
            if flo * fm < 0.0:
                hi = mid
            else:
                lo, flo = mid, fm
        mid = 0.5 * (lo + hi)
        res = f(mid) - target
        if math.isfinite(res) and abs(res) <= 1e-9 * target and _extent_ok(s, mid - extra):
            roots.append(mid)
    uniq = []
    for r in sorted(roots):
        if not uniq or abs(r - uniq[-1]) > 1e-12 * max(1.0, abs(r)):
            uniq.append(r)
    if not uniq:
        fin = vals[np.isfinite(vals)] + target
        rng = "F/# %.4g .. %.4g" % (float(fin.min()), float(fin.max())) if len(fin) else "no finite F/#"
        raise ValueError("the F/# solve on surface %d found no curvature giving F/# %.6g within c = %.6g +- %.4g "
                         "(%s over that range); widen 'span' or set another start curvature 'c0'"
                         % (i, target, c0, span, rng))
    pick = min(uniq, key=lambda r: (round(abs(r - c0), 12), abs(r)))
    return pick - extra, {"roots": [float(r - extra) for r in uniq], "n_roots": len(uniq), "chosen": float(pick - extra),
                          "branch": int(uniq.index(pick))}


def _solve_one(system, work, i, rule):
    """The value a rule sets (curvature, thickness or coefficient) from the current work surfaces, plus info."""
    s = work[i]
    kind = rule["kind"]
    ctx = _Ctx(system, work)
    extra = RT._c_extra(s)          # the paraxial curvature the surface's r^2 terms add: a solved c is the base curvature
    if rule["target"] == "c" and s.get("f") is not None:
        raise ValueError("surface %d is an ideal lens (f): it has no curvature to solve" % i)
    if kind == "pickup":
        j = rule["source"]
        q = rule["quantity"]
        if q == "c":
            return rule["scale"] * _curv(work[j]["R"]) + rule["offset"], {}
        if q == "t":
            tj = work[j]["t"]
            if tj is None:
                raise ValueError("surface %d picks up the thickness of surface %d, which has no thickness yet" % (i, j))
            return rule["scale"] * tj + rule["offset"], {}
        return rule["scale"] * _coef(work[j], q) + rule["offset"], {}
    if kind in ("marginal_ray_height", "chief_ray_height", "paraxial_image"):
        if kind == "chief_ray_height":
            y0, u0 = ctx.chief_start(_field_of(system, rule))
        else:
            y0, u0 = ctx.marginal_start()
        ys, us = ctx.trace(y0, u0)
        h = 0.0 if kind == "paraxial_image" else rule["h"]
        u = float(us[i])
        if abs(u) < 1e-12 * max(abs(float(ys[i])), 1e-12) or abs(u) < 1e-300:
            raise ValueError("surface %d: the %s ray leaves parallel to the axis (slope %.3g); no thickness reaches "
                             "height %g" % (i, "chief" if kind == "chief_ray_height" else "marginal", u, h))
        sign = 1.0 if ctx.n[i + 1] > 0 else -1.0
        t = float((h - ys[i]) / u) * sign
        if t < 0.0:
            if t > -1e-12:
                t = 0.0
            elif i != len(work) - 1:
                raise ValueError("surface %d: the %s solve would need a negative thickness (%.6g mm): the next "
                                 "surface would lie behind the light" % (i, kind, t))
        return t, {}
    if kind in ("marginal_ray_angle", "chief_ray_angle"):
        if kind == "chief_ray_angle":
            y0, u0 = ctx.chief_start(_field_of(system, rule))
        else:
            y0, u0 = ctx.marginal_start()
        ys, us = ctx.trace(y0, u0)
        y = float(ys[i])
        ub = u0 if i == 0 else float(us[i - 1])
        n1, n2 = float(ctx.n[i]), float(ctx.n[i + 1])
        if n1 == n2:
            raise ValueError("surface %d: no refraction here (same index on both sides); a curvature cannot set an angle" % i)
        if abs(y) < 1e-9 * max(ctx.ap, 1e-12):
            raise ValueError("surface %d: the %s ray is on the axis here; the angle solve is degenerate" %
                             (i, "chief" if kind == "chief_ray_angle" else "marginal"))
        up = math.tan(math.radians(rule["angle_deg"]))
        return (n1 * ub - n2 * up) / (y * (n2 - n1)) - extra, {}
    if kind == "f_number":
        return _solve_fno(ctx, i, rule, s, extra)
    if kind == "aplanatic":
        if any(w["mirror"] for w in work[:i + 1]):
            raise ValueError("surface %d: the aplanatic solve is for refracting surfaces in front of a mirror-free path" % i)
        y0, u0 = ctx.marginal_start()
        ys, us = ctx.trace(y0, u0)
        y = float(ys[i])
        ub = u0 if i == 0 else float(us[i - 1])
        n1, n2 = float(ctx.n[i]), float(ctx.n[i + 1])
        if abs(y) < 1e-9 * max(ctx.ap, 1e-12) or abs(ub) < 1e-15:
            raise ValueError("surface %d: the marginal ray is on the axis or parallel to it here; the aplanatic "
                             "solve needs a finite axial object distance" % i)
        # the aplanatic object point sits at l = R (n + n') / n from the vertex; the marginal ray meets the axis at l = -y/u
        return -(n1 + n2) * ub / (n1 * y) - extra, {}
    if kind == "concentric":
        j = rule["with_surface"]
        if any(w["mirror"] for w in work[j:i + 1]):
            raise ValueError("surface %d: a concentric solve across a mirror is not supported" % i)
        D = float(np.sum(ctx.t[j:i]))
        if rule["mode"] == "vertex":
            if D == 0.0:
                raise ValueError("surface %d: the centre of curvature cannot be at a vertex at zero distance" % i)
            return -1.0 / D - extra, {}
        if ctx.c[j] == 0.0:
            raise ValueError("surface %d: surface %d is flat; it has no centre of curvature to share" % (i, j))
        Ri = 1.0 / ctx.c[j] - D
        if Ri == 0.0:
            raise ValueError("surface %d: the concentric radius would be zero" % i)
        return 1.0 / Ri - extra, {}
    raise ValueError("unknown solve kind %r" % kind)    # pragma: no cover - _check_rule filters this


def _coef(s, q):
    k = int(q[1:])
    if k == 2:
        return float(s.get("a2", 0.0))
    a = s.get("asph", ())
    j = (k - 4) // 2
    return float(a[j]) if j < len(a) else 0.0


def _set_coef(s, q, v):
    k = int(q[1:])
    if k == 2:
        if v == 0.0:
            s.pop("a2", None)
        else:
            s["a2"] = v
        return
    j = (k - 4) // 2
    a = list(s.get("asph", ()))
    while len(a) <= j:
        a.append(0.0)
    a[j] = v
    while a and a[-1] == 0.0:
        a.pop()
    s["asph"] = tuple(a)


def _value_of(s, target, q=None):
    if target == "c":
        return _curv(s["R"])
    if target == "t":
        return 0.0 if s["t"] is None else float(s["t"])
    return _coef(s, q)


def _store(s, rule, v):
    if rule["target"] == "c":
        s["R"] = _radius_of(float(v))
    elif rule["target"] == "t":
        s["t"] = float(v)
    else:
        _set_coef(s, rule["quantity"], float(v))


def _static_checks(system, rules):
    stop = system["stop"]
    for i, r in rules.items():
        if r["target"] == "t" and i < stop:
            raise ValueError("surface %d: a thickness solve (%s) in front of the stop (surface %d) would move the stop; "
                             "put it on a surface at or behind the stop" % (i, r["kind"], stop))
        if r["target"] == "c" and system["surfaces"][i].get("f") is not None:
            raise ValueError("surface %d is an ideal lens (f): it has no curvature to solve" % i)
    # circular pickups: follow the chain of pickups of the same quantity
    for i, r in rules.items():
        if r["kind"] != "pickup":
            continue
        seen = [i]
        cur = r
        while cur is not None and cur["kind"] == "pickup":
            j = cur["source"]
            if j in seen:
                raise ValueError("circular pickup: %s" % " -> ".join("surface %d" % x for x in seen + [j]))
            seen.append(j)
            nxt = rules.get(j)
            cur = nxt if (nxt is not None and nxt["kind"] == "pickup" and nxt["quantity"] == cur["quantity"]) else None


def _resolve(system):
    """Resolve every rule; returns the work surfaces and the report rows."""
    surfs = system["surfaces"]
    work = [dict(s) for s in surfs]
    rules = {i: s["solve"] for i, s in enumerate(surfs) if s.get("solve")}
    if not rules:
        return work, []
    _static_checks(system, rules)
    info = {}
    for sweep in range(_MAX_SWEEPS):
        moved = 0.0
        for i in sorted(rules):
            rule = rules[i]
            val, inf = _solve_one(system, work, i, rule)
            old = _value_of(work[i], rule["target"], rule.get("quantity"))
            moved = max(moved, abs(val - old) / max(1.0, abs(old)))
            _store(work[i], rule, val)
            info[i] = inf
        if moved <= _SETTLE:
            break
    else:
        raise ValueError("the solves did not settle after %d sweeps (last change %.3g); a solve in front of the stop "
                         "feeds back on the marginal ray" % (_MAX_SWEEPS, moved))
    for i, w in enumerate(work):
        if w["R"] != INF and w["k"] > -1.0 and w["ap"] is not None and (1.0 + w["k"]) * (w["ap"] / w["R"]) ** 2 > 1.0:
            raise ValueError("surface %d: semi-aperture %.3g exceeds the conic's extent for the solved R=%.6g"
                             % (i, w["ap"], w["R"]))
    rows = _report(system, work, rules, info)
    return work, rows


def _report(system, work, rules, info):
    """Per rule: the resolved value and the quantity the rule asks for, measured on the final geometry."""
    ctx = _Ctx(system, work)
    rows = []
    mstart = None
    for i in sorted(rules):
        r = rules[i]
        kind = r["kind"]
        row = {"surface": i, "kind": kind, "target": r["target"], "rule": dict(r)}
        s = work[i]
        if r["target"] == "c":
            row["c"] = _curv(s["R"])
            row["R"] = s["R"]
        elif r["target"] == "t":
            row["t"] = s["t"]
        else:
            row["coefficient"] = _coef(s, r["quantity"])
        want = got = None
        if kind in ("marginal_ray_height", "chief_ray_height", "paraxial_image"):
            y0, u0 = ctx.chief_start(_field_of(system, r)) if kind == "chief_ray_height" else ctx.marginal_start()
            ys, us = ctx.trace(y0, u0)
            got = float(ys[i] + ctx.t[i] * us[i])
            want = 0.0 if kind == "paraxial_image" else r["h"]
        elif kind in ("marginal_ray_angle", "chief_ray_angle"):
            y0, u0 = ctx.chief_start(_field_of(system, r)) if kind == "chief_ray_angle" else ctx.marginal_start()
            ys, us = ctx.trace(y0, u0)
            got = float(us[i])
            want = math.tan(math.radians(r["angle_deg"]))
        elif kind == "f_number":
            got = _fno_curve(ctx, i)(float(ctx.c[i]))
            want = r["fno"]
            row.update(info.get(i, {}))
        elif kind == "aplanatic":
            y0, u0 = ctx.marginal_start()
            ys, us = ctx.trace(y0, u0)
            ub = u0 if i == 0 else float(us[i - 1])
            n1, n2 = float(ctx.n[i]), float(ctx.n[i + 1])
            got = float(-ys[i] / ub)                               # where the marginal ray meets the axis
            want = float((n1 + n2) / n1 / ctx.c[i]) if ctx.c[i] != 0.0 else INF
        elif kind == "concentric":
            j = r["with_surface"]
            D = float(np.sum(ctx.t[j:i]))
            got = 0.0 if ctx.c[i] == 0.0 else float(1.0 / ctx.c[i] + D)   # centre of this surface along the axis from vertex j
            want = 0.0 if r["mode"] == "vertex" else float(1.0 / ctx.c[j])
        elif kind == "pickup":
            q = r["quantity"]
            src = work[r["source"]]
            if q == "c":
                want, got = r["scale"] * _curv(src["R"]) + r["offset"], _curv(s["R"])
            elif q == "t":
                want, got = r["scale"] * float(src["t"]) + r["offset"], float(s["t"])
            else:
                want, got = r["scale"] * _coef(src, q) + r["offset"], _coef(s, q)
        row["wanted"] = want
        row["achieved"] = got
        row["error"] = None if (want is None or got is None) else float(got - want)
        rows.append(row)
    return rows


def _key(system):
    parts = [system["stop"], system["object_mm"], system["index_object"], system["wavelength_um"], system["field"]]
    for s in system["surfaces"]:
        rule = s.get("solve")
        tgt = rule["target"] if rule else None
        parts.append((None if tgt == "c" else s["R"], None if tgt == "t" else s["t"], repr(s["n"]), s["mirror"],
                      s.get("f"), s["ap"], s["k"], s.get("asph"), s.get("a2"),
                      json.dumps(rule, sort_keys=True) if rule else None))
    return repr(parts)


def lens_apply_solves(system=None) -> dict:
    """処方の解(solve)を全部解いた複製を返す: 規則は残り、R / t は解いた値になる(``table``)。

    Pure: the argument is not changed. The rules stay in ``surface["solve"]`` (so a write round-trips), the resolved
    numbers replace ``R`` / ``t`` / an aspheric coefficient, and the result carries ``solve_report``, one row per rule
    (see :func:`lens_solves_list`). ``lens_system`` already resolves once at construction and every ``raytrace`` trace
    resolves again first, so this op is for reading the resolved prescription and for a hand-edited dict. The
    resolved result of a system whose inputs have not changed is cached. A system without rules comes back as a copy.
    ``None`` takes a small doublet whose last thickness is a paraxial-image solve.

    Example::

        s = lens_solve_set(lens, 5, "paraxial_image")
        s["surfaces"][5]["t"]                       # the paraxial back focus
    """
    if system is None:
        system = _example_doublet()
    RT._check_system(system)
    if not any(s.get("solve") for s in system["surfaces"]):
        out = dict(system, surfaces=[dict(s) for s in system["surfaces"]])
        out.pop("solve_report", None)
        return out
    key = _key(system)
    hit = _CACHE.get(key)
    if hit is None:
        work, rows = _resolve(system)
        if len(_CACHE) >= _CACHE_MAX:
            _CACHE.clear()
        hit = _CACHE[key] = ([(w["R"], w["t"], w.get("asph", ()), w.get("a2")) for w in work], rows)
    vals, rows = hit
    surfaces = []
    for s, (R, t, asph, a2) in zip(system["surfaces"], vals):
        d = dict(s, R=R, t=t, asph=asph)
        if a2 is not None:
            d["a2"] = a2
        elif "a2" in d:
            d.pop("a2")
        surfaces.append(d)
    out = dict(system, surfaces=surfaces)
    out["solve_report"] = [dict(r) for r in rows]
    return out


def _rebuild(system, surfaces):
    return RT.lens_system(surfaces, stop=system["stop"], object_mm=system["object_mm"],
                          wavelength_um=system["wavelength_um"], index_object=system["index_object"],
                          image_mm=system["image_mm"], field=system["field"], aim=system.get("aim", "paraxial"),
                          vignetting=system.get("vignetting"), **RT._system_extras(system))


def _example_doublet():
    return RT.lens_system([{"R": 62.0, "t": 4.0, "n": (1.5168, 64.17), "ap": 10.0},
                           {"R": -45.0, "t": 2.0, "n": (1.62, 36.37)},
                           {"R": -130.0, "t": 1.0, "n": 1.0, "solve": {"kind": "paraxial_image"}}], stop=0)


def _surface_index(system, surface, name="surface"):
    n = len(system["surfaces"])
    if surface is None:
        return n - 1
    return _int(surface, name, 0, n - 1)


def lens_solve_set(system=None, surface=None, kind="paraxial_image", h=None, angle_deg=None, fno=None, source=None,
                   quantity=None, scale=None, offset=None, field=None, with_surface=None, mode=None, c0=None,
                   span=None) -> dict:
    """面に解(solve)の規則を付け、解いた処方を返す(``table``)。

    *surface* defaults to the last one. *kind* is one of ``marginal_ray_height`` (*h*, mm, default 0), ``chief_ray_height``
    (*h*, *field*), ``paraxial_image``, ``marginal_ray_angle`` / ``chief_ray_angle`` (*angle_deg*, default 0, *field*),
    ``f_number`` (*fno* required; *c0* the start curvature, default the surface's own; *span* the search half-width in
    1/mm), ``concentric`` (*with_surface*, default the previous surface; *mode* ``"centre"`` shares the centre of curvature,
    ``"vertex"`` puts it at that vertex), ``aplanatic``, ``pickup`` (*source* required, *quantity* ``"c"`` / ``"t"`` /
    ``"A2"`` ... ``"A18"`` an aspheric coefficient, *scale* 1, *offset* 0; ``scale=-1`` picks up the negative curvature). An
    argument the kind does not take is a ``ValueError``, as is an unknown kind (the message lists them). A rule replaces
    any earlier one on that surface; the rest of the prescription is untouched. The returned system is resolved (see
    :func:`lens_apply_solves`); its ``solve_report`` gives the rule's resolved value and the achieved quantity.

    Example::

        s = lens_solve_set(lens, 5, "paraxial_image")                 # image at the paraxial focus
        s = lens_solve_set(s, 4, "f_number", fno=5.6)                 # and the F/# held by surface 4's curvature
        s["solve_report"][1]["roots"]                                 # the F/# solve's roots; the nearest is used
    """
    if system is None:
        system = _example_doublet()
    RT._check_system(system)
    i = _surface_index(system, surface)
    given = {"h": h, "angle_deg": angle_deg, "fno": fno, "source": source, "quantity": quantity, "scale": scale,
             "offset": offset, "field": field, "with_surface": with_surface, "mode": mode, "c0": c0, "span": span}
    args = {k: v for k, v in given.items() if v is not None}
    if kind in SOLVE_KINDS:
        bad = sorted(set(args) - set(SOLVE_KINDS[kind][1]))
        if bad:
            raise ValueError("lens_solve_set: solve %r does not take %s (it takes %s)" %
                             (kind, bad, sorted(SOLVE_KINDS[kind][1]) or "no arguments"))
    rule = _check_rule(dict(args, kind=kind), i, len(system["surfaces"]), "lens_solve_set surface %d" % i)
    base = system if not any(s.get("solve") for s in system["surfaces"]) else lens_apply_solves(system)
    if rule["kind"] == "f_number" and rule["c0"] is None:
        rule["c0"] = _curv(base["surfaces"][i]["R"])
    surfaces = [dict(s) for s in base["surfaces"]]
    surfaces[i]["solve"] = rule
    return _rebuild(system, [{k: v for k, v in s.items()} for s in surfaces])


def lens_solve_clear(system=None, surface=None) -> dict:
    """面の解(solve)の規則を外す: 解いた値は数値として残る(``table``)。

    *surface* ``None`` clears every rule. A surface without a rule is a ``ValueError`` (nothing to clear); the numbers the
    rules had solved stay as they were, so the traced system does not change.

    Example::

        fixed = lens_solve_clear(s)           # a plain prescription with the solved numbers
    """
    if system is None:
        system = _example_doublet()
    RT._check_system(system)
    res = lens_apply_solves(system)
    n = len(res["surfaces"])
    ids = [i for i, s in enumerate(res["surfaces"]) if s.get("solve")] if surface is None else \
        [_int(surface, "surface", 0, n - 1)]
    if surface is not None and not res["surfaces"][ids[0]].get("solve"):
        raise ValueError("lens_solve_clear: surface %d has no solve to clear" % ids[0])
    if not ids:
        raise ValueError("lens_solve_clear: the system has no solve to clear")
    surfaces = [dict(s) for s in res["surfaces"]]
    for i in ids:
        surfaces[i].pop("solve", None)
    return _rebuild(system, surfaces)


def lens_solves_list(system=None) -> dict:
    """付いている解(solve)の一覧: 規則・解いた値・達成した量と誤差(``table``)。

    Returns ``{"n_solves", "kinds", "solves"}``; each row has ``surface``, ``kind``, ``target`` (``"c"`` / ``"t"`` / ``"A"``),
    ``rule`` (every argument), the resolved ``c`` and ``R`` / ``t`` / ``coefficient``, ``wanted`` and ``achieved`` (the
    quantity the rule asks for, measured on the final geometry by an independent paraxial trace) and ``error``. An
    ``f_number`` row also has ``roots`` (every curvature that gives the F/#), ``n_roots``, ``chosen`` and ``branch``.
    ``kinds`` lists the kinds this module knows.

    Example::

        for r in lens_solves_list(s)["solves"]: print(r["surface"], r["kind"], r["error"])
    """
    if system is None:
        system = _example_doublet()
    RT._check_system(system)
    res = lens_apply_solves(system)
    rows = res.get("solve_report", [])
    return {"n_solves": len(rows), "kinds": list(SOLVE_KINDS), "solves": rows}


# --------------------------------------------------------------------------- #
# afocal systems
# --------------------------------------------------------------------------- #
def afocal_system(system=None, f1: float = 100.0, f2: float = 25.0, ap: float = 10.0) -> dict:
    """像空間が平行光の系(望遠鏡・ビームエキスパンダ)を作る: 与えた系に afocal の印を付けるか、理想レンズ 2 枚の望遠鏡(``table``)。

    With *system* ``None`` it builds an ideal-lens telescope: two paraxial lenses of focal lengths *f1* and *f2* a distance
    ``f1 + f2`` apart (Keplerian for ``f2 > 0``, Galilean for ``f2 < 0``), stop on the first lens (semi-aperture *ap*); its
    angular magnification is exactly ``-f1/f2`` for every ray. With a *system* it returns a copy flagged afocal after
    checking that a collimated beam leaves collimated (``ValueError`` if it focuses: fix the spacing, for example with a
    ``marginal_ray_angle`` solve of 0 degrees on the last curvature). The flag makes ``paraxial_trace`` report
    ``angular_magnification`` (``efl`` and ``bfl`` are inf), ``ray_bundle`` / ``spot_stats`` / ``ray_fan`` read the exit
    angle in arcminutes (from the chief ray), and ``opd_samples`` reference a plane wave.

    Example::

        tele = afocal_system(f1=100.0, f2=25.0)
        paraxial_trace(tele)["angular_magnification"]       # -4
    """
    if system is None:
        f1 = _num(f1, "f1")
        f2 = _num(f2, "f2")
        ap = _num(ap, "ap")
        if f1 == 0.0 or f2 == 0.0 or not ap > 0.0:
            raise ValueError("afocal_system: f1 and f2 must be non-zero and ap > 0")
        gap = f1 + f2
        if gap < 0.0:
            raise ValueError("afocal_system: f1 + f2 = %g is negative; the second lens would lie behind the first" % gap)
        return RT.lens_system([{"f": f1, "t": gap, "ap": ap}, {"f": f2, "t": 10.0}], stop=0, afocal=True)
    RT._check_system(system)
    res = lens_apply_solves(system)
    if res["object_mm"] != INF:
        raise ValueError("afocal_system: an afocal system needs an object at infinity")
    out = _rebuild(dict(res, afocal=True), [dict(s) for s in res["surfaces"]])
    RT.paraxial_trace(out)                                      # raises if a collimated beam does not leave collimated
    return out


def lens_afocal_report(system=None, fields=None, rings: int = 6) -> dict:
    """afocal 系の角倍率・射出瞳・視野ごとの角度の収差(分角)(``table``)。

    *system* must be afocal (``None``: the ideal Keplerian f1=100, f2=25). Returns ``angular_magnification`` (image-space
    over object-space chief-ray slope, negative for an inverted image), ``beam_compression`` (entrance over exit pupil
    radius), the entrance / exit pupil position and radius, and per field (degrees, default 0, 0.7 and 1.0 of the system
    field) the chief-ray exit angle in arcminutes (``chief_arcmin``), ``rms_arcmin`` and ``geo_arcmin`` (spot about the
    chief ray, an angular spot: the blur an eye or a following lens sees), ``n_rays`` and ``n_vignetted``.
    ``wavefront_rms_waves`` is the RMS plane-wave error over the exit pupil when the field is on axis or the OPD is
    computable.

    Example::

        r = lens_afocal_report(tele)
        r["angular_magnification"], [f["rms_arcmin"] for f in r["fields"]]
    """
    if system is None:
        system = afocal_system()
    RT._check_system(system)
    if not system.get("afocal"):
        raise ValueError("lens_afocal_report: the system is not afocal (build it with afocal_system or "
                         "lens_system(afocal=True))")
    rings = _int(rings, "rings", 1, 40)
    para = RT.paraxial_trace(system)
    if fields is None:
        f = float(system["field"])
        fields = [0.0] if f == 0.0 else [0.0, 0.7 * f, f]
    elif isinstance(fields, (int, float)) and not isinstance(fields, bool):
        fields = [fields]
    rows = []
    for fld in fields:
        fld = _num(fld, "field")
        st = RT.spot_stats(system, field=fld, rings=rings)
        wf = float("nan")
        try:
            px, py, w, ok = RT.opd_samples(system, field=fld, size=17)
            if ok.sum() >= 8:
                wv = w[ok]
                wf = float(np.sqrt(np.mean((wv - wv.mean()) ** 2)))
        except ValueError:
            pass
        rows.append({"field": fld, "chief_arcmin": [st["chief_x"], st["chief_y"]], "rms_arcmin": st["rms_radius"],
                     "geo_arcmin": st["geo_radius"], "n_rays": st["n_rays"], "n_vignetted": st["n_vignetted"],
                     "wavefront_rms_waves": wf})
    M = para["angular_magnification"]
    return {"angular_magnification": M, "beam_compression": float(para["ep_radius"] / para["xp_radius"])
            if para["xp_radius"] > 0 else INF,
            "ep_position": para["ep_position"], "ep_radius": para["ep_radius"],
            "xp_position": para["xp_position"], "xp_radius": para["xp_radius"], "fields": rows, "unit": "arcmin"}


# --------------------------------------------------------------------------- #
# curved image surface
# --------------------------------------------------------------------------- #
def lens_petzval_radius(system=None) -> dict:
    """像空間のペッツバール半径: 3 次の像面湾曲を消す像面の曲率半径(``table``)。

    ``R_p = -1 / (n' P)`` with the Petzval sum ``P = sum c (n' - n) / (n n')`` over the refracting surfaces (an ideal lens adds
    nothing, as in ``seidel_coefficients``); for a thin lens of index ``N`` in air this is ``-N f``: the surface bends
    towards the lens. Positive ``R`` follows the library's convention (centre to the right), so a positive lens has a
    negative Petzval radius. Returns ``{"radius", "sum", "n_image"}`` (``radius`` is inf when the sum is zero). Systems with a
    mirror are refused.

    Example::

        lens_petzval_radius(lens)["radius"]        # about -n f for a thin lens
    """
    if system is None:
        system = _example_doublet()
    RT._check_system(system)
    system = RT._solved(system)
    if any(s["mirror"] for s in system["surfaces"]):
        raise ValueError("lens_petzval_radius: systems with a mirror are not supported")
    wl = system["wavelength_um"]
    n_prev = RT.refractive_index(system["index_object"], wl)
    P = 0.0
    for s in system["surfaces"]:
        n_now = RT.refractive_index(s["n"], wl)
        if s.get("f") is None and s["R"] != INF:
            P += (n_now - n_prev) / (s["R"] * n_prev * n_now)
        n_prev = n_now
    R = INF if abs(P) < 1e-300 else -1.0 / (n_prev * P)
    return {"radius": float(R), "sum": float(P), "n_image": float(n_prev)}


def lens_image_surface(system=None, R=INF, k: float = 0.0) -> dict:
    """像面を曲面にした処方を返す: 光線はこの面と交わり、スポット・OPD・MTF はこの面で測る(``table``)。

    *R* is the radius of the image surface (mm; ``inf`` flat; positive: centre of curvature to the right, in the
    direction the light travels) or the string ``"petzval"`` for :func:`lens_petzval_radius`; *k* its conic constant. The
    paraxial image (its position on the axis, its height) does not depend on it. A flat ``R`` with ``k != 0`` is refused.

    Example::

        flat = lens_image_surface(lens)                    # flat again
        curved = lens_image_surface(lens, R="petzval")
    """
    if system is None:
        system = _example_doublet()
    RT._check_system(system)
    res = lens_apply_solves(system)
    if isinstance(R, str):
        if R != "petzval":
            raise ValueError("lens_image_surface: R must be a radius or 'petzval', got %r" % R)
        R = lens_petzval_radius(res)["radius"]
    extras = RT._system_extras(res)
    extras.pop("image_R", None)
    extras.pop("image_k", None)
    return RT.lens_system([dict(s) for s in res["surfaces"]], stop=res["stop"], object_mm=res["object_mm"],
                          wavelength_um=res["wavelength_um"], index_object=res["index_object"],
                          image_mm=res["image_mm"], field=res["field"], aim=res.get("aim", "paraxial"),
                          vignetting=res.get("vignetting"), image_R=R, image_k=k, **extras)


# --------------------------------------------------------------------------- #
# .zmx round trip of the solves
# --------------------------------------------------------------------------- #
#: Rules the .zmx format is evidenced to carry in a form real files show (see the lensfile module help).
_NATIVE = ("pickup",)


def lens_zmx_solves_roundtrip(system=None) -> dict:
    """解(solve)を ``.zmx`` に書き、読み戻し、もう一度書く: 不動点になるかを調べる(``table``)。

    Writes *system* (``None``: a doublet with a thickness pickup, a curvature pickup with scale -1 and a paraxial-image
    solve) through ``lensfile``, reads the text back, writes again and reads again. Curvature pickups
    (``CURV c 4 source scale offset``), thickness pickups (``PZUP``) and aspheric-coefficient pickups (``PPAR``) are written in the
    form real files show; the other kinds (the marginal / chief ray solves, F/#, concentric, aplanatic) have no form in the
    files this library has seen, so they are written as ``NOTE`` lines (``FULLSEYE-SOLVE``) that other programs ignore and the
    geometry stays the solved numbers. Returns ``{"text", "text_second", "fixed_point", "max_diff", "rules_before",
    "rules_after", "native", "as_note", "dropped_solves", "afocal"}``; ``fixed_point`` means that the second write is
    text-identical to the first read-write and ``max_diff`` is the largest difference of any ``R`` / ``t`` / ``k`` / ``ap``
    between the system and the twice-read one.

    Example::

        r = lens_zmx_solves_roundtrip(s)
        assert r["fixed_point"] and r["max_diff"] < 1e-12
    """
    import lensfile as LF
    if system is None:
        system = RT.lens_system([{"R": 62.0, "t": 4.0, "n": (1.5168, 64.17), "ap": 10.0},
                                 {"R": -45.0, "t": 2.0, "n": (1.62, 36.37)},
                                 {"R": -130.0, "t": 1.0, "n": 1.0, "solve": {"kind": "pickup", "source": 1,
                                                                             "quantity": "c", "scale": 1.0,
                                                                             "offset": 0.0}},
                                 {"R": 80.0, "t": 5.0, "n": 1.0, "solve": {"kind": "pickup", "source": 0,
                                                                            "quantity": "t", "scale": 1.0,
                                                                            "offset": 1.0}},
                                 {"R": -90.0, "t": 1.0, "n": 1.0, "solve": {"kind": "paraxial_image"}}], stop=0)
    RT._check_system(system)
    res = lens_apply_solves(system)
    p0 = LF._prescription_from_system(res)
    w1 = LF.lens_file_write(p0, system=res)
    p1 = LF.lens_file_read(w1["text"])
    w2 = LF.lens_file_write(p1)
    p2 = LF.lens_file_read(w2["text"])
    w3 = LF.lens_file_write(p2)
    a, b = res, p2["system"]
    diff = 0.0
    for sa, sb in zip(a["surfaces"], b["surfaces"]):
        for key in ("R", "t", "k", "ap"):
            va, vb = sa.get(key), sb.get(key)
            if va is None or vb is None:
                if va != vb:
                    diff = INF
                continue
            if va == vb:
                continue
            diff = max(diff, abs(va - vb))
    rules_a = [s.get("solve") for s in a["surfaces"]]
    rules_b = [s.get("solve") for s in b["surfaces"]]
    native = [i for i, r in enumerate(rules_a) if r and r["kind"] in _NATIVE]
    note = [i for i, r in enumerate(rules_a) if r and r["kind"] not in _NATIVE]
    return {"text": w1["text"], "text_second": w3["text"], "fixed_point": w2["text"] == w3["text"],
            "max_diff": float(diff), "rules_before": rules_a, "rules_after": rules_b, "native": native,
            "as_note": note, "dropped_solves": w1["dropped_solves"], "afocal": bool(b.get("afocal")),
            "rules_equal": rules_a == rules_b}
