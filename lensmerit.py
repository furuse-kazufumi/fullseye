# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""lensmerit — an operand-table merit function for sequential lens design, and the optimiser that drives it.

``lensopt`` builds one fixed merit (ray offsets plus an EFL hold). A designer's merit is a *table*: one row
per requirement, each with a target, a weight and, for a bound ("edge thickness at least 1 mm"), a one-sided
form. This module is that table.

* :func:`merit_operands_list` — the catalogue of operands (name, meaning, unit, arguments).
* :func:`merit_evaluate` — evaluate a table on a prescription: value, target, weight, contribution
  ``(w (value - target))^2`` per row (zero for a satisfied bound) and the percentage of the total.
* :func:`merit_default` — the default table: ray rows over a hexapolar pupil (transverse = spot, or OPD =
  wavefront), chief-ray or centroid reference, and the EFL hold. For ``kind="spot"``, ``reference="chief"``
  its total is :func:`lensopt.merit_function`'s merit to rounding (the gate in ``tests/test_lensmerit.py``).
* :func:`merit_boundary_operands` — the manufacturing rows for a prescription: edge thickness of every glass
  element, centre-thickness and air-gap ranges.
* :func:`optimize_lens_operands` — Levenberg–Marquardt on the stacked operand residuals (variables and step
  rules of :mod:`lensopt`), with **glass as a variable**: ``"g<i>"`` moves the glass of surface *i* over a
  candidate list by an outer discrete sweep after the continuous optimisation has converged.
* :func:`merit_contributions` — "which row dominates", sorted, as percentages.

Operands (upper-case names; ``surf`` is a surface index, ``N`` the image plane; ``field`` / ``wavelength`` are
indices into the ``fields`` / ``wavelengths`` lists of the call, or ``"all"``; ``px`` / ``py`` are normalised
pupil coordinates)::

    EFFL  effective focal length                 TOTR  total track, first vertex to image
    TTHI  sum of thicknesses surf1 .. surf2      CTGT / CTLT  centre thickness  >= / <=  target
    ETGT / ETLT  edge thickness >= / <= target   MNCG / MXCG  min / max glass thickness over surf1 .. surf2
    MNCA / MXCA  min / max air thickness         REAY / REAX  real ray height at a surface
    RAID  real-ray angle of incidence            OPDX  OPD at one pupil point (waves, chief reference)
    SPHA COMA ASTI FCUR DIST  Seidel sums (waves)   AXCL / LACL  axial / lateral colour
    RSCE  RMS spot about the centroid            RSCH  RMS spot about the chief ray
    WFNO  working F-number (real marginal ray)   PMAG  paraxial magnification
    DIMX  largest |distortion| over the fields   WFRMS RMS wavefront (waves, piston removed)
    TRAN  transverse ray aberrations of a whole hexapolar pupil  (a group row: one residual per ray and axis)
    OPDW  OPD of a whole hexapolar pupil (waves)                  (a group row: one residual per ray)

Edge thickness is computed from the sag at the clear semi-diameter of both surfaces,
``t_edge = t - sag_i(h_i) + sag_{i+1}(h_{i+1})`` with the conic and even aspheric sag; the clear semi-diameter is the
surface's ``ap`` (without one, the paraxial marginal-plus-chief ray height). Everything is fail-closed: an unknown
operand, a missing or unknown argument, an index out of range, a value that is not finite, a table whose weights
are all zero — each is a ``ValueError`` naming the culprit.
"""
from __future__ import annotations

import copy
import math

import numpy as np

import lensopt as LO
import raytrace as RT

__all__ = ["merit_operands_list", "merit_evaluate", "merit_default", "merit_boundary_operands",
           "optimize_lens_operands", "merit_contributions"]

INF = float("inf")
MAX_OPERANDS = 600
SENSES = ("eq", "ge", "le")
REFERENCES = ("chief", "centroid")
LOST_RAY_CHARGE = 1.0          # a vignetted / TIR ray is charged this much (mm for TRAN, waves for OPDW), as lensopt does


# --------------------------------------------------------------------------- #
# argument checking
# --------------------------------------------------------------------------- #
def _num(x, name, positive=False, nonneg=False):
    if isinstance(x, (bool, np.bool_)) or not isinstance(x, (int, float, np.integer, np.floating)):
        raise ValueError("%s must be a finite number, got %r" % (name, x))
    v = float(x)
    if not math.isfinite(v) or (positive and v <= 0.0) or (nonneg and v < 0.0):
        raise ValueError("%s must be a finite%s number, got %r" % (name, " positive" if positive else (" non-negative" if nonneg else ""), x))
    return v


def _int(x, name, lo=None, hi=None):
    if isinstance(x, (bool, np.bool_)) or not isinstance(x, (int, np.integer)):
        raise ValueError("%s must be an integer, got %r" % (name, x))
    v = int(x)
    if (lo is not None and v < lo) or (hi is not None and v > hi):
        raise ValueError("%s must be %s..%s, got %d" % (name, lo, hi, v))
    return v


# --------------------------------------------------------------------------- #
# prescription helpers
# --------------------------------------------------------------------------- #
def _image_distance(system):
    """Last vertex to image plane, exactly as ``trace_rays`` places the image."""
    if system["image_mm"] is not None:
        return float(system["image_mm"])
    t = system["surfaces"][-1]["t"]
    if t is not None:
        return float(t)
    return float(RT.paraxial_trace(system)["image_mm"])


def _thickness(system, i):
    """Thickness after surface *i* (the last one is the distance to the image plane)."""
    n = len(system["surfaces"])
    t = system["surfaces"][i]["t"]
    if i == n - 1:
        return _image_distance(system)
    return 0.0 if t is None else float(t)


def _is_glass(s):
    return abs(float(s["n_value"]) - 1.0) > 1e-9


def _clear_semi(system, i, para=None):
    """Clear semi-diameter of surface *i*: its ``ap``, else the paraxial marginal + chief ray height there."""
    s = system["surfaces"][i]
    if s["ap"] is not None:
        return float(s["ap"])
    para = RT.paraxial_trace(system) if para is None else para
    fld = float(system["field"])
    scale = math.tan(math.radians(fld)) if system["object_mm"] == INF else fld
    return abs(para["marginal"]["y"][i]) + abs(para["chief"]["y"][i]) * abs(scale)


def _sag_at(s, h):
    c = 0.0 if s["R"] == INF else 1.0 / s["R"]
    z = float(RT._sag(np.array([h * h]), c, s["k"], s["asph"])[0])
    if not math.isfinite(z):
        raise ValueError("the semi-diameter %.6g is outside the conic of a surface (R=%r, k=%r)" % (h, s["R"], s["k"]))
    return z


def _edge_thickness(system, i):
    """Edge thickness of the element that starts at surface *i* (mm): ``t - sag_i(h_i) + sag_{i+1}(h_{i+1})``."""
    n = len(system["surfaces"])
    if not 0 <= i < n - 1:
        raise ValueError("edge thickness needs a surface 0..%d (it needs a next surface), got %r" % (n - 2, i))
    a, b = system["surfaces"][i], system["surfaces"][i + 1]
    if a["mirror"] or b["mirror"] or a.get("f") is not None or b.get("f") is not None:
        raise ValueError("edge thickness is not defined next to a mirror or an ideal lens (surface %d)" % i)
    para = RT.paraxial_trace(system)
    ha, hb = _clear_semi(system, i, para), _clear_semi(system, i + 1, para)
    return float(_thickness(system, i) - _sag_at(a, ha) + _sag_at(b, hb))


# --------------------------------------------------------------------------- #
# OPD at arbitrary pupil points
# --------------------------------------------------------------------------- #
def _opd_points(system, field, wl, px, py):
    """OPD (waves, chief-ray reference sphere) at normalised pupil points. Returns ``(opd, valid)``.

    The same construction as ``raytrace.opd_samples`` (reference sphere centred on the chief ray's image
    point, through the paraxial exit pupil; Welford's sign), but at the points asked for instead of a grid —
    ``tests/test_lensmerit.py`` checks it against ``opd_samples`` on that grid.
    """
    px = np.asarray(px, float)
    py = np.asarray(py, float)
    para = RT._para_at(system, wl)
    aim = RT._resolve_aim(system, None)
    px_a = np.append(px, 0.0)
    py_a = np.append(py, 0.0)
    if aim == "stop":
        P, D, opl0, _e, _u = RT._launch_aimed(system, px_a, py_a, field, para, 1.0, wl)
    else:
        dpx, dpy = RT._chief_offset(system, field, para, wl)
        P, D, opl0 = RT._launch(system, px_a + dpx, py_a + dpy, field, para)
    tr = RT.trace_rays(system, P, D, wavelength_um=wl)
    if not bool(tr["valid"][-1]):
        raise ValueError("the chief ray does not reach the image plane at field %r" % field)
    pts, dirs = tr["points"], tr["dirs"]
    n_img = tr["n_image"]
    chief_img = pts[-1, -1]
    dirn = 1.0 if dirs[-1, -1, 2] >= 0 else -1.0
    z_last_vertex = tr["z_image_global"] - dirn * tr["image_z"]
    z_xp = z_last_vertex + dirn * para["xp_position"]
    C = chief_img
    Rref = abs(C[2] - z_xp)
    if not math.isfinite(Rref) or Rref < 1e-9:
        raise ValueError("exit pupil coincides with the image plane; OPD reference sphere undefined")
    Pl = pts[:, -2, :]
    Dl = dirs[:, -1, :]
    last_leg = np.linalg.norm(pts[:, -1, :] - Pl, axis=1) * n_img
    opl_last = tr["opl"] - last_leg + opl0
    oc = Pl - C
    b = np.sum(oc * Dl, axis=1)
    cc = np.sum(oc * oc, axis=1) - Rref * Rref
    disc = b * b - cc
    ok = disc >= 0
    sq = np.sqrt(np.where(ok, disc, 0.0))
    s1, s2 = -b - sq, -b + sq
    z1 = Pl[:, 2] + s1 * Dl[:, 2]
    z2 = Pl[:, 2] + s2 * Dl[:, 2]
    s = np.where(np.abs(z1 - z_xp) <= np.abs(z2 - z_xp), s1, s2)
    opl_ref = opl_last + n_img * s
    valid = tr["valid"] & ok
    w = (opl_ref[-1] - opl_ref) / (wl * 1e-3)
    w = np.where(valid, w, np.nan)
    return w[:-1], valid[:-1]


# --------------------------------------------------------------------------- #
# evaluation context (one prescription, one set of fields / wavelengths, caches)
# --------------------------------------------------------------------------- #
class _Ctx:
    def __init__(self, system, fields=None, wavelengths=None, field_weights=None, wavelength_weights=None):
        RT._check_system(system)
        self.system = system
        self.fields = LO._fields(system, fields)
        if wavelengths is None:
            wls = [float(system["wavelength_um"])]
        else:
            seq = wavelengths if isinstance(wavelengths, (list, tuple, np.ndarray)) else [wavelengths]
            wls = [_num(w, "wavelength", positive=True) for w in seq]
        if not wls:
            raise ValueError("wavelengths must not be empty")
        self.wls = wls
        self.primary = wls.index(float(system["wavelength_um"])) if float(system["wavelength_um"]) in wls else 0
        self.fw = self._weights(field_weights, len(self.fields), "field_weights")
        self.ww = self._weights(wavelength_weights, len(wls), "wavelength_weights")
        self._sys, self._bundle, self._single = {}, {}, {}
        self._para = None

    @staticmethod
    def _weights(w, n, name):
        if w is None:
            return [1.0] * n
        out = [_num(v, name[:-1], nonneg=True) for v in w]
        if len(out) != n:
            raise ValueError("%s must match the list it weights (%d vs %d)" % (name, len(out), n))
        return out

    def para(self):
        if self._para is None:
            self._para = RT.paraxial_trace(self.system)
        return self._para

    def sys_at(self, wi):
        w = self.wls[wi]
        if w == float(self.system["wavelength_um"]):
            return self.system
        if wi not in self._sys:
            self._sys[wi] = RT.with_wavelength(self.system, w)
        return self._sys[wi]

    def bundle(self, fi, wi, rings, fill):
        key = (fi, wi, rings, fill)
        if key not in self._bundle:
            self._bundle[key] = RT.ray_bundle(self.system, field=self.fields[fi], rings=rings,
                                              wavelength_um=self.wls[wi], pupil_fill=fill)
        return self._bundle[key]

    def single(self, field_value, wi, px, py, aim=None):
        key = (field_value, wi, px, py, aim)
        if key not in self._single:
            sysm, wl = self.system, self.wls[wi]
            para = RT._para_at(sysm, wl)
            P, D, _o, aimed, _r = RT._launch_pupil(sysm, np.array([px]), np.array([py]), field_value, para, 1.0, wl,
                                                   RT._resolve_aim(sysm, aim))
            tr = RT.trace_rays(sysm, P, D, wavelength_um=wl)
            tr["valid"] = tr["valid"] & aimed
            self._single[key] = tr
        return self._single[key]


# --------------------------------------------------------------------------- #
# operand functions: fn(ctx, a) -> (value, residuals or None, info dict)
# --------------------------------------------------------------------------- #
def _finite_value(v, label):
    v = float(v)
    if not math.isfinite(v):
        raise ValueError("operand %s is not finite (%r)" % (label, v))
    return v


def _op_effl(ctx, a):
    return float(RT.paraxial_trace(ctx.sys_at(a["wavelength"]))["efl"]), None, {}


def _op_totr(ctx, a):
    s = ctx.system
    n = len(s["surfaces"])
    return float(sum(_thickness(s, i) for i in range(n))), None, {}


def _op_tthi(ctx, a):
    s = ctx.system
    return float(sum(_thickness(s, i) for i in range(a["surf1"], a["surf2"]))), None, {}


def _op_ct(ctx, a):
    return float(_thickness(ctx.system, a["surf"])), None, {}


def _op_et(ctx, a):
    return _edge_thickness(ctx.system, a["surf"]), None, {}


def _range_thicknesses(ctx, a, glass):
    s = ctx.system
    vals = []
    for i in range(a["surf1"], a["surf2"] + 1):
        surf = s["surfaces"][i]
        if surf["t"] is None and i == len(s["surfaces"]) - 1 and s["image_mm"] is None:
            continue
        if _is_glass(surf) == glass and not surf["mirror"]:
            vals.append(_thickness(s, i))
    if not vals:
        raise ValueError("no %s thickness between surfaces %d and %d" % ("glass" if glass else "air", a["surf1"], a["surf2"]))
    return vals


def _op_mncg(ctx, a):
    return float(min(_range_thicknesses(ctx, a, True))), None, {}


def _op_mxcg(ctx, a):
    return float(max(_range_thicknesses(ctx, a, True))), None, {}


def _op_mnca(ctx, a):
    return float(min(_range_thicknesses(ctx, a, False))), None, {}


def _op_mxca(ctx, a):
    return float(max(_range_thicknesses(ctx, a, False))), None, {}


def _ray_at_surface(ctx, a):
    tr = ctx.single(ctx.fields[a["field"]], a["wavelength"], a["px"], a["py"])
    if not bool(tr["valid"][0]):
        raise ValueError("the ray (field %d, pupil %.4g, %.4g) is lost (missed a surface, vignetted or TIR)" % (a["field"], a["px"], a["py"]))
    return tr


def _op_reay(ctx, a):
    return float(_ray_at_surface(ctx, a)["points"][0, a["surf"] + 1, 1]), None, {}


def _op_reax(ctx, a):
    return float(_ray_at_surface(ctx, a)["points"][0, a["surf"] + 1, 0]), None, {}


def _op_raid(ctx, a):
    tr = _ray_at_surface(ctx, a)
    i = a["surf"]
    s = ctx.system["surfaces"][i]
    Rm = RT._rot(*s["tilt"])
    off = np.array([s["decenter"][0], s["decenter"][1], RT._vertex_z(ctx.system, i)])
    Dl = tr["dirs"][0, i][None, :] @ Rm
    Ql = (tr["points"][0, i + 1] - off)[None, :] @ Rm
    c = 0.0 if s["R"] == INF else 1.0 / s["R"]
    nrm = RT._surface_normal(Ql, c, s["k"], s["asph"])
    cos_i = abs(float(np.sum(nrm * Dl)))
    return math.degrees(math.acos(min(1.0, cos_i))), None, {}


def _op_opdx(ctx, a):
    w, valid = _opd_points(ctx.system, ctx.fields[a["field"]], ctx.wls[a["wavelength"]], [a["px"]], [a["py"]])
    if not bool(valid[0]):
        raise ValueError("the ray (field %d, pupil %.4g, %.4g) is lost" % (a["field"], a["px"], a["py"]))
    return float(w[0]), None, {}


def _seidel(key):
    def fn(ctx, a):
        return float(RT.seidel_coefficients(ctx.system, ctx.fields[a["field"]])["waves"][key]), None, {}
    return fn


def _op_axcl(ctx, a):
    b1 = RT.paraxial_trace(RT.with_wavelength(ctx.system, a["wl1"]))["bfl"]
    b2 = RT.paraxial_trace(RT.with_wavelength(ctx.system, a["wl2"]))["bfl"]
    return float(b1 - b2), None, {}


def _op_lacl(ctx, a):
    r = RT.chromatic_shift(ctx.system, [a["wl1"], a["wl2"]], field=ctx.fields[a["field"]], rings=1)
    return float(r["lateral_color"]), None, {}


def _spot_xy(ctx, a):
    b = ctx.bundle(a["field"], a["wavelength"], a["rings"], a["pupil_fill"])
    xy = b["image_xy"][b["valid"]]
    if len(xy) == 0:
        raise ValueError("no ray reached the image plane (field %d)" % a["field"])
    return b, xy


def _op_rsce(ctx, a):
    _b, xy = _spot_xy(ctx, a)
    d = xy - xy.mean(0)
    return float(np.sqrt(np.mean(d[:, 0] ** 2 + d[:, 1] ** 2))), None, {}


def _op_rsch(ctx, a):
    b, xy = _spot_xy(ctx, a)
    if not np.isfinite(b["chief_xy"]).all():
        raise ValueError("the chief ray does not reach the image plane at field %d" % a["field"])
    d = xy - b["chief_xy"]
    return float(np.sqrt(np.mean(d[:, 0] ** 2 + d[:, 1] ** 2))), None, {}


def _op_wfno(ctx, a):
    tr = ctx.single(0.0, ctx.primary, 0.0, 1.0, aim="stop")
    if not bool(tr["valid"][0]):
        raise ValueError("the on-axis marginal ray is lost; the working F-number is undefined")
    d = tr["dirs"][0, -1]
    sin_t = math.hypot(float(d[0]), float(d[1]))
    if sin_t <= 0.0:
        raise ValueError("the on-axis marginal ray leaves parallel to the axis; the working F-number is infinite")
    return 1.0 / (2.0 * abs(float(tr["n_image"])) * sin_t), None, {}


def _op_pmag(ctx, a):
    return float(ctx.para()["magnification"]), None, {}


def _op_dimx(ctx, a):
    s, para = ctx.system, ctx.para()
    worst = 0.0
    for f in ctx.fields:
        if f == 0.0:
            continue
        ch = RT.chief_ray(s, field=f, image_mm=para["image_mm"])
        if not ch["valid"]:
            raise ValueError("the chief ray is lost at field %r" % f)
        ideal = para["efl"] * math.tan(math.radians(f)) if s["object_mm"] == INF else para["magnification"] * f
        if ideal == 0.0 or not math.isfinite(ideal):
            raise ValueError("the ideal image height is zero or not finite at field %r" % f)
        worst = max(worst, abs(100.0 * (ch["image_y"] - ideal) / ideal))
    return float(worst), None, {}


def _wf_grid(size):
    g = np.linspace(-1.0, 1.0, int(size))
    gx, gy = np.meshgrid(g, g)
    px, py = gx.ravel(), gy.ravel()
    inside = px * px + py * py <= 1.0 + 1e-12
    return px[inside], py[inside]


def _op_wfrms(ctx, a):
    px, py = _wf_grid(a["size"])
    w, valid = _opd_points(ctx.system, ctx.fields[a["field"]], ctx.wls[a["wavelength"]], px, py)
    if int(valid.sum()) < 3:
        raise ValueError("fewer than 3 valid pupil samples for the wavefront RMS")
    v = w[valid]
    return float(np.sqrt(np.mean((v - v.mean()) ** 2))), None, {"rays_lost": int((~valid).sum())}


def _op_tran(ctx, a):
    b = ctx.bundle(a["field"], a["wavelength"], a["rings"], a["pupil_fill"])
    xy, chief = b["image_xy"], b["chief_xy"]
    ok = b["valid"]
    if a["reference"] == "chief":
        if not np.isfinite(chief).all():
            raise ValueError("the chief ray does not reach the image plane at field %d" % a["field"])
        ref = chief
    else:
        if not ok.any():
            raise ValueError("no ray reached the image plane (field %d)" % a["field"])
        ref = xy[ok].mean(0)
    d = np.where(~ok[:, None], LOST_RAY_CHARGE, xy - ref)
    dv = d[ok]
    value = float(np.sqrt(np.mean(dv[:, 0] ** 2 + dv[:, 1] ** 2))) if len(dv) else INF
    return value, d.ravel(), {"rays_lost": int((~ok).sum())}


def _op_opdw(ctx, a):
    px, py = RT._pupil_grid(a["rings"])
    w, valid = _opd_points(ctx.system, ctx.fields[a["field"]], ctx.wls[a["wavelength"]],
                           px * a["pupil_fill"], py * a["pupil_fill"])
    if not valid.any():
        raise ValueError("no ray reached the image plane (field %d)" % a["field"])
    if a["reference"] == "centroid":
        w = w - float(np.mean(w[valid]))
    r = np.where(valid, w, LOST_RAY_CHARGE)
    value = float(np.sqrt(np.mean(r[valid] ** 2)))
    return value, r, {"rays_lost": int((~valid).sum())}


# --------------------------------------------------------------------------- #
# the operand catalogue
# --------------------------------------------------------------------------- #
_FIELD = ("field", 0)
_WAVE = ("wavelength", "primary")
_RAY = {"px": 0.0, "py": 1.0}
_ARGSPEC = {
    "surf": ("surf", "surface index"),
    "surf1": ("surf", "first surface index"),
    "surf2": ("surf", "last surface index"),
}

_OPERANDS: dict = {}


def _reg(name, fn, description, unit, required=(), optional=None, sense="eq", group=False):
    _OPERANDS[name] = {"fn": fn, "description": description, "unit": unit, "required": tuple(required),
                       "optional": dict(optional or {}), "sense": sense, "group": group}


_reg("EFFL", _op_effl, "Effective focal length at one wavelength.", "mm", optional={"wavelength": "primary"})
_reg("TOTR", _op_totr, "Total track: first vertex to the image plane (sum of all thicknesses).", "mm")
_reg("TTHI", _op_tthi, "Sum of the thicknesses from the vertex of surf1 to the vertex of surf2 (surf2 = N is the image plane).",
     "mm", required=("surf1", "surf2"))
_reg("CTGT", _op_ct, "Centre thickness after a surface, at least the target (one-sided).", "mm", required=("surf",), sense="ge")
_reg("CTLT", _op_ct, "Centre thickness after a surface, at most the target (one-sided).", "mm", required=("surf",), sense="le")
_reg("ETGT", _op_et, "Edge thickness at the clear semi-diameters, at least the target (one-sided).", "mm", required=("surf",), sense="ge")
_reg("ETLT", _op_et, "Edge thickness at the clear semi-diameters, at most the target (one-sided).", "mm", required=("surf",), sense="le")
_reg("MNCG", _op_mncg, "Smallest glass centre thickness over surf1..surf2, at least the target (one-sided).", "mm",
     required=("surf1", "surf2"), sense="ge")
_reg("MXCG", _op_mxcg, "Largest glass centre thickness over surf1..surf2, at most the target (one-sided).", "mm",
     required=("surf1", "surf2"), sense="le")
_reg("MNCA", _op_mnca, "Smallest air thickness over surf1..surf2, at least the target (one-sided).", "mm",
     required=("surf1", "surf2"), sense="ge")
_reg("MXCA", _op_mxca, "Largest air thickness over surf1..surf2, at most the target (one-sided).", "mm",
     required=("surf1", "surf2"), sense="le")
_reg("REAY", _op_reay, "Real ray y at a surface (surf = N is the image plane) for one field, wavelength and pupil point.", "mm",
     required=("surf",), optional=dict([_FIELD, _WAVE], **_RAY))
_reg("REAX", _op_reax, "Real ray x at a surface (surf = N is the image plane) for one field, wavelength and pupil point.", "mm",
     required=("surf",), optional=dict([_FIELD, _WAVE], **_RAY))
_reg("RAID", _op_raid, "Real-ray angle of incidence on a surface (0..N-1).", "deg",
     required=("surf",), optional=dict([_FIELD, _WAVE], **_RAY))
_reg("OPDX", _op_opdx, "Optical path difference at one pupil point relative to the chief ray (Welford sign).", "waves",
     optional=dict([_FIELD, _WAVE], **_RAY))
_reg("SPHA", _seidel("S_I"), "Seidel spherical aberration sum S_I / wavelength.", "waves", optional=dict([_FIELD]))
_reg("COMA", _seidel("S_II"), "Seidel coma sum S_II / wavelength.", "waves", optional=dict([_FIELD]))
_reg("ASTI", _seidel("S_III"), "Seidel astigmatism sum S_III / wavelength.", "waves", optional=dict([_FIELD]))
_reg("FCUR", _seidel("S_IV"), "Seidel field-curvature (Petzval) sum S_IV / wavelength.", "waves", optional=dict([_FIELD]))
_reg("DIST", _seidel("S_V"), "Seidel distortion sum S_V / wavelength.", "waves", optional=dict([_FIELD]))
_reg("AXCL", _op_axcl, "Axial colour: paraxial back focal length at wl1 minus at wl2 (default F and C lines).", "mm",
     optional={"wl1": RT.WL_F, "wl2": RT.WL_C})
_reg("LACL", _op_lacl, "Lateral colour: chief-ray image height at wl1 minus at wl2 (default F and C lines).", "mm",
     optional={"field": 0, "wl1": RT.WL_F, "wl2": RT.WL_C})
_reg("RSCE", _op_rsce, "RMS spot radius about the centroid, hexapolar pupil.", "mm",
     optional=dict([_FIELD, _WAVE], rings=4, pupil_fill=1.0))
_reg("RSCH", _op_rsch, "RMS spot radius about the chief ray, hexapolar pupil.", "mm",
     optional=dict([_FIELD, _WAVE], rings=4, pupil_fill=1.0))
_reg("WFNO", _op_wfno, "Working F-number 1/(2 n' sin(theta')) of the on-axis real marginal ray.", "")
_reg("PMAG", _op_pmag, "Paraxial (transverse) magnification; 0 for an object at infinity.", "")
_reg("DIMX", _op_dimx, "Largest absolute distortion of the chief ray over the off-axis fields, against the paraxial image height.",
     "percent")
_reg("WFRMS", _op_wfrms, "RMS wavefront error (piston removed) over a square pupil grid, no Zernike fit.", "waves",
     optional=dict([_FIELD, _WAVE], size=15))
_reg("TRAN", _op_tran, "Transverse ray aberrations of a whole hexapolar pupil: one residual per ray and axis; value = RMS radius.", "mm",
     optional=dict([_FIELD, _WAVE], rings=4, pupil_fill=0.98, reference="chief"), group=True)
_reg("OPDW", _op_opdw, "OPD of a whole hexapolar pupil: one residual per ray; value = RMS.", "waves",
     optional=dict([_FIELD, _WAVE], rings=4, pupil_fill=0.98, reference="chief"), group=True)

_IDENT_ARGS = ("surf", "surf1", "surf2", "field", "wavelength", "px", "py")


def _check_arg(op, name, v, n_surf, n_fields, n_wls, primary):
    """Validate and resolve one argument (``field`` / ``wavelength`` -> an index or ``"all"``)."""
    where = "operand %s: argument %s" % (op, name)
    if name == "surf":
        hi = n_surf if op in ("REAY", "REAX") else n_surf - 1
        if op in ("CTGT", "CTLT"):
            hi = n_surf - 1
        if op in ("ETGT", "ETLT"):
            hi = n_surf - 2
        return _int(v, where, 0, hi)
    if name == "surf1":
        return _int(v, where, 0, n_surf - 1)
    if name == "surf2":
        return _int(v, where, 0, n_surf if op == "TTHI" else n_surf - 1)
    if name == "field":
        if v == "all":
            return "all"
        if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)) or not 0 <= v < n_fields:
            raise ValueError("%s: field index %r is out of range 0..%d (or 'all')" % (where, v, n_fields - 1))
        return int(v)
    if name == "wavelength":
        if v == "primary":
            return primary
        if v == "all":
            return "all"
        if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)) or not 0 <= v < n_wls:
            raise ValueError("%s: wavelength index %r is out of range 0..%d (or 'primary' / 'all')" % (where, v, n_wls - 1))
        return int(v)
    if name in ("px", "py"):
        return _num(v, where)
    if name == "rings":
        return _int(v, where, 1, 64)
    if name == "size":
        return _int(v, where, 5, 129)
    if name == "pupil_fill":
        f = _num(v, where, positive=True)
        if f > 1.0:
            raise ValueError("%s must be <= 1" % where)
        return f
    if name in ("wl1", "wl2"):
        return _num(v, where, positive=True)
    if name == "reference":
        if v not in REFERENCES:
            raise ValueError("%s must be one of %s, got %r" % (where, ", ".join(REFERENCES), v))
        return v
    raise ValueError("%s is not handled" % where)  # pragma: no cover


def _normalise(ctx, operands):
    """Validate the table and expand ``"all"`` fields / wavelengths. Returns the concrete rows."""
    if not isinstance(operands, (list, tuple)) or len(operands) == 0:
        raise ValueError("operands must be a non-empty list of dicts {op, target, weight, ...}")
    if len(operands) > MAX_OPERANDS:
        raise ValueError("too many operands (%d > %d)" % (len(operands), MAX_OPERANDS))
    n_surf = len(ctx.system["surfaces"])
    nf, nw = len(ctx.fields), len(ctx.wls)
    rows = []
    for k, row in enumerate(operands):
        if not isinstance(row, dict) or "op" not in row:
            raise ValueError("operand %d must be a dict with an 'op' key, got %r" % (k, row))
        name = row["op"]
        if name not in _OPERANDS:
            raise ValueError("unknown operand %r; known operands: %s" % (name, ", ".join(_OPERANDS)))
        spec = _OPERANDS[name]
        allowed = set(spec["required"]) | set(spec["optional"]) | {"op", "target", "weight", "sense"}
        unknown = sorted(set(row) - allowed)
        if unknown:
            raise ValueError("operand %s: unknown argument(s) %s; it takes %s" % (name, unknown, sorted(allowed - {"op"})))
        for req in spec["required"]:
            if req not in row:
                raise ValueError("operand %s: missing required argument %r" % (name, req))
        if spec["group"]:
            tgt = _num(row.get("target", 0.0), "operand %s: target" % name)
            if tgt != 0.0:
                raise ValueError("operand %s is a group row (one residual per ray) and its target is 0, got %r" % (name, tgt))
        else:
            if "target" not in row:
                raise ValueError("operand %s: missing required argument 'target'" % name)
            tgt = _num(row["target"], "operand %s: target" % name)
        wt = _num(row.get("weight", 1.0), "operand %s: weight" % name, nonneg=True)
        sense = row.get("sense", spec["sense"])
        if sense not in SENSES:
            raise ValueError("operand %s: sense must be one of %s, got %r" % (name, ", ".join(SENSES), sense))
        if spec["group"] and sense != "eq":
            raise ValueError("operand %s is a group row; sense must be 'eq'" % name)
        args = {}
        for key in list(spec["required"]) + list(spec["optional"]):
            args[key] = _check_arg(name, key, row.get(key, spec["optional"].get(key)), n_surf, nf, nw, ctx.primary)
        if "surf1" in args and args["surf1"] > args["surf2"] and name != "TTHI":
            raise ValueError("operand %s: surf1 %d is after surf2 %d" % (name, args["surf1"], args["surf2"]))
        if name == "TTHI" and args["surf1"] >= args["surf2"]:
            raise ValueError("operand TTHI: surf1 %d must be before surf2 %d" % (args["surf1"], args["surf2"]))
        fidx = range(nf) if args.get("field") == "all" else [args.get("field")]
        widx = range(nw) if args.get("wavelength") == "all" else [args.get("wavelength")]
        for fi in fidx:
            for wi in widx:
                a = dict(args)
                factor = 1.0
                if "field" in a:
                    if a["field"] == "all":
                        factor *= math.sqrt(ctx.fw[fi])
                    a["field"] = fi
                if "wavelength" in a:
                    if a["wavelength"] == "all":
                        factor *= math.sqrt(ctx.ww[wi])
                    a["wavelength"] = wi
                ident = ",".join("%s=%s" % (q, ("%.4g" % a[q]) if isinstance(a[q], float) else a[q]) for q in _IDENT_ARGS if q in a)
                rows.append({"op": name, "label": "%s(%s)" % (name, ident) if ident else name, "target": tgt,
                             "weight": wt * factor, "sense": sense, "args": a, "source": k, "group": spec["group"]})
    if not any(r["weight"] > 0.0 for r in rows):
        raise ValueError("every operand has weight 0: the merit is empty")
    return rows


def _run(ctx, rows):
    """Evaluate concrete rows. Returns ``(table, residual vector)``."""
    table, parts = [], []
    for k, r in enumerate(rows):
        spec = _OPERANDS[r["op"]]
        value, vec, info = spec["fn"](ctx, r["args"])
        if not r["group"]:
            value = _finite_value(value, r["label"])
        elif not math.isfinite(value):
            raise ValueError("operand %s is not finite (%r)" % (r["label"], value))
        if r["group"]:
            res = r["weight"] * np.asarray(vec, float)
            margin = None
        else:
            d = value - r["target"]
            if r["sense"] == "ge":
                margin = d
                d = min(d, 0.0)
            elif r["sense"] == "le":
                margin = -d
                d = max(d, 0.0)
            else:
                margin = None
            res = np.array([r["weight"] * d])
        if not np.all(np.isfinite(res)):
            raise ValueError("operand %s produced a non-finite residual" % r["label"])
        parts.append(res)
        table.append(dict({"index": k, "op": r["op"], "label": r["label"], "value": float(value), "target": r["target"],
                           "weight": r["weight"], "sense": r["sense"], "margin": margin,
                           "contribution": float(np.dot(res, res)), "n_residuals": int(len(res)),
                           "source": r["source"], "args": dict(r["args"])}, **info))
    vec = np.concatenate(parts) if parts else np.zeros(0)
    total = float(np.dot(vec, vec))
    for row in table:
        row["percent"] = 100.0 * row["contribution"] / total if total > 0.0 else 0.0
        row["satisfied"] = row["contribution"] == 0.0
    return table, vec


def _unpack(system, operands, fields, wavelengths, field_weights, wavelength_weights):
    if system is None:
        system = RT.lens_system()
    RT._check_system(system)
    if operands is None:
        operands = merit_default(system)
    if isinstance(operands, dict) and "operands" in operands:
        d = operands
        operands = d["operands"]
        fields = d["fields"] if fields is None else fields
        wavelengths = d["wavelengths"] if wavelengths is None else wavelengths
    return system, operands, fields, wavelengths, field_weights, wavelength_weights


# --------------------------------------------------------------------------- #
# public ops
# --------------------------------------------------------------------------- #
def merit_operands_list() -> dict:
    """メリット関数の操作子(オペランド)の一覧: 名前・意味・単位・引数(``table``)。

    Returns ``{"operands": [{"name", "description", "unit", "required", "optional", "sense", "kind"}], "n_operands",
    "names"}``. ``required`` are the arguments a row must give besides ``target`` (every scalar row needs a
    ``target``); ``optional`` are the arguments with their defaults (``field`` / ``wavelength`` are indices into the
    ``fields`` / ``wavelengths`` of the call, or ``"all"``; ``wavelength="primary"`` is the system wavelength).
    ``sense`` is the default form of the row: ``"eq"`` (a two-sided target) or ``"ge"`` / ``"le"`` (a one-sided
    bound that contributes nothing while it is satisfied); any scalar row may override it with ``"sense"``.
    ``kind`` is ``"scalar"`` (one residual) or ``"group"`` (one residual per ray, target 0).

    Example::

        [o["name"] for o in merit_operands_list()["operands"] if o["sense"] != "eq"]
    """
    out = []
    for name, sp in _OPERANDS.items():
        out.append({"name": name, "description": sp["description"], "unit": sp["unit"], "required": list(sp["required"]),
                    "optional": dict(sp["optional"]), "sense": sp["sense"], "kind": "group" if sp["group"] else "scalar"})
    return {"operands": out, "n_operands": len(out), "names": [o["name"] for o in out]}


def merit_evaluate(system=None, operands=None, fields=None, wavelengths=None, field_weights=None,
                   wavelength_weights=None) -> dict:
    """オペランド表を処方に当てて、各行の値・目標・重み・寄与とその割合を返す(``table``)。

    *operands* is a list of rows ``{"op": "EFFL", "target": 50.0, "weight": 1.0, ...arguments}`` (see
    :func:`merit_operands_list`), or the dict :func:`merit_default` returns. Each row contributes
    ``(weight (value - target))^2``; a one-sided row (``ETGT`` ...) contributes 0 while the bound holds.
    A group row (``TRAN``, ``OPDW``) contributes the sum over its rays. *fields* (default: on axis, or 0 / 0.7 / 1.0
    of the system field) and *wavelengths* (default the system wavelength; the primary is the one equal to it)
    are what the rows' ``field`` / ``wavelength`` indices point into; a row with ``"all"`` is expanded to one row per
    field and wavelength, its weight times ``sqrt(field_weight)`` and ``sqrt(wavelength_weight)`` (default 1).

    Returns ``{"table", "merit", "n_operands", "n_residuals", "dominant", "fields", "wavelengths"}``. Each table row
    has ``index op label value target weight sense margin contribution percent satisfied n_residuals source args``
    (``margin`` is the slack of a one-sided row, negative when violated). Fail-closed: an unknown operand, a missing
    or unknown argument, an index out of range, a lost ray, a value that is not finite and a table of zero weights
    are all ``ValueError``.

    Example::

        t = merit_evaluate(lens, [{"op": "EFFL", "target": 50.0}, {"op": "ETGT", "surf": 0, "target": 1.0}])
        t["merit"], t["dominant"]
    """
    system, operands, fields, wavelengths, field_weights, wavelength_weights = _unpack(
        system, operands, fields, wavelengths, field_weights, wavelength_weights)
    ctx = _Ctx(system, fields, wavelengths, field_weights, wavelength_weights)
    rows = _normalise(ctx, operands)
    table, vec = _run(ctx, rows)
    total = float(np.dot(vec, vec))
    dom = max(table, key=lambda r: (r["contribution"], -r["index"]))["label"] if total > 0.0 else None
    return {"table": table, "merit": total, "n_operands": len(table), "n_residuals": int(len(vec)), "dominant": dom,
            "fields": list(ctx.fields), "wavelengths": list(ctx.wls)}


def merit_default(system=None, kind: str = "spot", fields=None, wavelengths=None, rings: int = 4,
                  reference: str = "chief", efl_target=None, efl_weight=None, field_weights=None,
                  wavelength_weights=None, pupil_fill: float = 0.98) -> dict:
    """既定のメリット関数をオペランド表として組む: 瞳全体の光線行 + EFL の保持(``table``)。

    One group row per field and wavelength: ``kind="spot"`` is ``TRAN`` (transverse ray aberrations, mm),
    ``kind="wavefront"`` is ``OPDW`` (OPD, waves); *reference* ``"chief"`` measures from the chief ray (for the
    wavefront: the OPD as it is, relative to the chief ray) and ``"centroid"`` from the centroid of the spot (for the
    wavefront: the mean OPD removed). The pupil is hexapolar with *rings* rings out to *pupil_fill*. The row weight is
    ``sqrt(field_weight x wavelength_weight)`` (default 1). The EFL hold is an ``EFFL`` row with target *efl_target*
    (default the starting EFL; ``False`` for none) and weight ``efl_weight / |target|``; the default *efl_weight* is
    ``10 sqrt(n_rays)`` for the spot and ``100 sqrt(n_rays)`` for the wavefront. For ``kind="spot"``,
    ``reference="chief"`` the total equals ``lensopt.merit_function`` on the same pupil.

    Returns ``{"operands", "fields", "wavelengths", "kind", "reference", "rings", "pupil_fill", "efl_target",
    "efl_weight", "n_rays"}``; pass it (or its ``"operands"`` with ``fields=`` and ``wavelengths=``) to the other ops.

    Example::

        m = merit_default(lens, kind="wavefront", rings=3)
        merit_evaluate(lens, m)["merit"]
    """
    if system is None:
        system = RT.lens_system()
    RT._check_system(system)
    if kind not in ("spot", "wavefront"):
        raise ValueError("kind must be 'spot' or 'wavefront', got %r" % (kind,))
    if reference not in REFERENCES:
        raise ValueError("reference must be one of %s, got %r" % (", ".join(REFERENCES), reference))
    rings = _int(rings, "rings", 1, 64)
    fill = _num(pupil_fill, "pupil_fill", positive=True)
    if fill > 1.0:
        raise ValueError("pupil_fill must be <= 1")
    ctx = _Ctx(system, fields, wavelengths, field_weights, wavelength_weights)
    n_rays = len(RT._pupil_grid(rings)[0]) * len(ctx.fields) * len(ctx.wls)
    if efl_target is None:
        efl_target = RT.paraxial_trace(system)["efl"]
        if not math.isfinite(efl_target) or efl_target == 0.0:
            efl_target = False
    if efl_target is not False:
        efl_target = _num(efl_target, "efl_target")
        if efl_target == 0.0:
            raise ValueError("efl_target must be non-zero (or False for no EFL hold)")
    if efl_weight is None:
        efl_weight = (10.0 if kind == "spot" else 100.0) * math.sqrt(n_rays)
    else:
        efl_weight = _num(efl_weight, "efl_weight", nonneg=True)
    op = "TRAN" if kind == "spot" else "OPDW"
    rows = []
    for fi in range(len(ctx.fields)):
        for wi in range(len(ctx.wls)):
            rows.append({"op": op, "field": fi, "wavelength": wi, "rings": rings, "pupil_fill": fill,
                         "reference": reference, "target": 0.0, "weight": math.sqrt(ctx.fw[fi] * ctx.ww[wi])})
    if efl_target is not False:
        rows.append({"op": "EFFL", "target": float(efl_target), "weight": float(efl_weight) / abs(efl_target)})
    return {"operands": rows, "fields": list(ctx.fields), "wavelengths": list(ctx.wls), "kind": kind,
            "reference": reference, "rings": rings, "pupil_fill": fill,
            "efl_target": None if efl_target is False else float(efl_target), "efl_weight": float(efl_weight),
            "n_rays": int(n_rays)}


def merit_boundary_operands(system=None, min_edge: float = 1.0, min_centre=None, max_centre=None,
                            min_air=None, max_air=None, weight: float = 10.0) -> dict:
    """製造上の境界を表の行にする: 各ガラスの縁厚・中心厚の範囲・空気間隔の範囲(``table``)。

    For every glass element (a surface with glass after it that has a next surface) an ``ETGT`` row with target
    *min_edge*; ``MNCG`` / ``MXCG`` rows over the glass surfaces for *min_centre* / *max_centre*; ``MNCA`` / ``MXCA`` rows
    over the surfaces between the first glass and the last surface for *min_air* / *max_air* (``None`` leaves a bound
    out). All rows are one-sided with weight *weight*. A prescription without glass is a ``ValueError``.

    Returns ``{"operands", "n_operands", "elements"}`` (``elements`` are the glass surfaces); append ``operands`` to a
    table from :func:`merit_default`.

    Example::

        ops = merit_default(lens)["operands"] + merit_boundary_operands(lens, 1.0, 2.0, 8.0, 0.5)["operands"]
    """
    if system is None:
        system = RT.lens_system()
    RT._check_system(system)
    wt = _num(weight, "weight", nonneg=True)
    n = len(system["surfaces"])
    glass = [i for i, s in enumerate(system["surfaces"]) if _is_glass(s) and not s["mirror"] and i < n - 1]
    if not glass:
        raise ValueError("the prescription has no glass element to bound")
    rows = []
    if min_edge is not None:
        e = _num(min_edge, "min_edge", nonneg=True)
        rows += [{"op": "ETGT", "surf": i, "target": e, "weight": wt} for i in glass]
    lo, hi = glass[0], glass[-1]
    for nm, val, op in (("min_centre", min_centre, "MNCG"), ("max_centre", max_centre, "MXCG")):
        if val is not None:
            rows.append({"op": op, "surf1": lo, "surf2": hi, "target": _num(val, nm, positive=True), "weight": wt})
    air = [i for i in range(lo, n - 1) if not _is_glass(system["surfaces"][i]) and system["surfaces"][i]["t"] is not None]
    for nm, val, op in (("min_air", min_air, "MNCA"), ("max_air", max_air, "MXCA")):
        if val is not None:
            if not air:
                raise ValueError("%s given but the prescription has no air gap after the first glass" % nm)
            rows.append({"op": op, "surf1": lo, "surf2": n - 2, "target": _num(val, nm, positive=True), "weight": wt})
    if not rows:
        raise ValueError("no bound requested (all of min_edge, min_centre, max_centre, min_air, max_air are None)")
    return {"operands": rows, "n_operands": len(rows), "elements": glass}


def merit_contributions(system=None, operands=None, fields=None, wavelengths=None, field_weights=None,
                        wavelength_weights=None, top=None) -> dict:
    """どの行がメリット関数を支配しているか: 寄与の大きい順のパーセント表(``table``)。

    The rows of :func:`merit_evaluate` sorted by contribution (ties by table order), each with its ``percent`` of the
    total and the running ``cumulative`` percent. *top* keeps only the largest rows (``None`` all). Returns
    ``{"contributions", "dominant", "merit", "n_operands", "violated"}``; ``violated`` lists the one-sided rows whose
    bound does not hold.

    Example::

        merit_contributions(lens, ops, top=3)["dominant"]["label"]
    """
    ev = merit_evaluate(system, operands, fields, wavelengths, field_weights, wavelength_weights)
    rows = sorted(ev["table"], key=lambda r: (-r["contribution"], r["index"]))
    cum = 0.0
    out = []
    for r in rows:
        cum += r["percent"]
        out.append({k: r[k] for k in ("index", "op", "label", "value", "target", "weight", "sense", "margin",
                                      "contribution", "percent", "satisfied")} | {"cumulative": cum})
    if top is not None:
        out = out[:_int(top, "top", 1, None)]
    violated = [r["label"] for r in ev["table"] if r["sense"] != "eq" and not r["satisfied"]]
    return {"contributions": out, "dominant": out[0] if out and ev["merit"] > 0.0 else None, "merit": ev["merit"],
            "n_operands": ev["n_operands"], "violated": violated}


# --------------------------------------------------------------------------- #
# optimiser
# --------------------------------------------------------------------------- #
def _medium_key(m):
    if isinstance(m, str):
        return ("s", m)
    if isinstance(m, dict) and "nd" in m and "vd" in m:
        return ("m", round(float(m["nd"]), 12), round(float(m["vd"]), 12))
    if isinstance(m, (tuple, list)) and len(m) == 2:
        return ("m", round(float(m[0]), 12), round(float(m[1]), 12))
    if isinstance(m, (int, float, np.integer, np.floating)) and not isinstance(m, (bool, np.bool_)):
        return ("n", float(m))
    return ("o", repr(m))


def _with_glass(system, i, medium):
    surf = [dict(s) for s in system["surfaces"]]
    surf[i]["n"] = copy.deepcopy(medium)
    return RT.lens_system(surf, stop=system["stop"], object_mm=system["object_mm"],
                          wavelength_um=system["wavelength_um"], index_object=system["index_object"],
                          image_mm=system["image_mm"], field=system["field"],
                          aim=system.get("aim", "paraxial"), vignetting=system.get("vignetting"))


def _split_variables(system, variables):
    """Continuous variable specs (as ``lensopt`` takes them) and glass variables (surface indices)."""
    n = len(system["surfaces"])
    if variables is None:
        return None, []
    if isinstance(variables, (str, dict)):
        variables = [variables]
    cont, glass = [], []
    for v in variables:
        is_g = False
        if isinstance(v, dict):
            is_g = str(v.get("param", "")).strip() == "g"
            idx = v.get("surface")
        elif isinstance(v, str):
            s = v.strip()
            is_g = len(s) > 1 and s[0] == "g" and s[1:].isdigit()
            idx = int(s[1:]) if is_g else None
        else:
            raise ValueError("variable must be a string like 'c0' / 'g2' or a dict, got %r" % type(v).__name__)
        if is_g:
            i = _int(idx, "glass variable surface", 0, n - 1)
            s = system["surfaces"][i]
            if s["mirror"] or s.get("f") is not None or not _is_glass(s):
                raise ValueError("g%d: surface %d has no glass to vary (air, mirror or ideal lens)" % (i, i))
            if i in glass:
                raise ValueError("duplicate variables (g%d)" % i)
            glass.append(i)
        else:
            cont.append(v)
    return cont, glass


def _candidates(glass_candidates, gvars):
    if not gvars:
        return {}
    if glass_candidates is None:
        raise ValueError("glass variables %s need glass_candidates (a list of media, or a dict 'g<i>' -> list)" % ["g%d" % i for i in gvars])
    out = {}
    for i in gvars:
        if isinstance(glass_candidates, dict):
            lst = glass_candidates.get("g%d" % i, glass_candidates.get(i))
            if lst is None:
                raise ValueError("glass_candidates has no list for g%d" % i)
        else:
            lst = glass_candidates
        if not isinstance(lst, (list, tuple)) or len(lst) == 0:
            raise ValueError("the candidate list for g%d must be a non-empty list of media" % i)
        for m in lst:
            try:
                RT.refractive_index(m)
            except (ValueError, TypeError, KeyError) as e:
                raise ValueError("g%d: candidate %r is not a usable medium: %s" % (i, m, e)) from None
        out[i] = list(lst)
    return out


def _lm(system, varlist, resid, bounds, iterations, lam, tolerance):
    """Levenberg–Marquardt with lensopt's variables, forward-difference Jacobian and step rules."""
    if not varlist:
        r = resid(system)
        m = float(np.dot(r, r))
        return {"system": system, "merit": m, "history": [m], "iterations": 0, "converged": True, "status": "converged",
                "rejected": 0, "lam": lam}
    x = np.array([LO._get(system, v) for v in varlist], dtype=np.float64)
    cur = LO._rebuild(system, x, varlist, bounds)            # the start obeys the bounds too
    x = np.array([LO._get(cur, v) for v in varlist], dtype=np.float64)
    r = resid(cur)
    merit = float(np.dot(r, r))
    history = [merit]
    steps = {"c": 1e-5, "t": 1e-3, "k": 1e-3, "A": None}
    ap_scale = max(1.0, float(system["surfaces"][system["stop"]]["ap"] or 1.0))
    converged, status, small, stalled, rejected, it = False, "iterations", 0, 0, 0, 0
    for it in range(1, iterations + 1):
        J = np.zeros((len(r), len(x)))
        for j, var in enumerate(varlist):
            if var[0] == "A":
                h = 1e-4 / (ap_scale ** (4 + 2 * var[2]))
            else:
                h = steps[var[0]] * max(1.0, abs(x[j]))
            xp = x.copy()
            xp[j] += h
            try:
                rp = resid(LO._rebuild(cur, xp, varlist, bounds))
            except (ValueError, FloatingPointError):
                xp = x.copy()
                xp[j] -= h
                rp = resid(LO._rebuild(cur, xp, varlist, bounds))
                h = -h
            J[:, j] = (rp - r) / h
        JtJ = J.T @ J
        Jtr = J.T @ r
        diag = np.diag(JtJ).copy()
        diag[diag <= 0] = 1e-12
        accepted = False
        for _ in range(6):
            try:
                delta = np.linalg.solve(JtJ + lam * np.diag(diag), -Jtr)
            except np.linalg.LinAlgError:
                lam *= 4.0
                rejected += 1
                continue
            try:
                sys_n = LO._rebuild(cur, x + delta, varlist, bounds)
                rn = resid(sys_n)
            except (ValueError, FloatingPointError):
                lam *= 4.0
                rejected += 1
                continue
            mn = float(np.dot(rn, rn))
            if math.isfinite(mn) and mn < merit:
                rel = (merit - mn) / max(merit, 1e-300)
                x = np.array([LO._get(sys_n, v) for v in varlist], dtype=np.float64)
                cur, r, merit = sys_n, rn, mn
                history.append(merit)
                lam = max(lam / 3.0, 1e-12)
                accepted = True
                stalled = 0
                small = small + 1 if rel < tolerance else 0
                break
            lam *= 4.0
            rejected += 1
        if not accepted:
            stalled += 1
            if lam > 1e8 or stalled >= 2:
                status = "stalled"
                break
        if small >= 2:
            converged, status = True, "converged"
            break
    return {"system": cur, "merit": merit, "history": history, "iterations": it, "converged": converged,
            "status": status, "rejected": rejected, "lam": lam}


def _var_name(v):
    kind, i, j = v
    return ("A%d_%d" % (4 + 2 * j, i)) if kind == "A" else {"c": "R%d", "t": "t%d", "k": "k%d"}[kind] % i


def optimize_lens_operands(system=None, operands=None, variables=None, iterations: int = 30, fields=None,
                           wavelengths=None, field_weights=None, wavelength_weights=None, damping: float = 1e-3,
                           tolerance: float = 1e-7, min_thickness: float = 0.5, max_thickness=None,
                           min_radius: float = 1.0, glass_candidates=None, glass_iterations: int = 12,
                           outer_iterations: int = 3) -> dict:
    """オペランド表のメリット関数を LM で最小化する。硝材も変数にできる(``table``)。

    The residual vector is the stack of the table's rows (:func:`merit_evaluate`); *variables* are those of
    :func:`lensopt.optimize_lens` (``"c<i>"`` / ``"R<i>"`` curvature, ``"t<i>"``, ``"k<i>"``, ``"A4_<i>"`` ...; default every
    finite radius) plus **glass variables** ``"g<i>"``. The continuous steps are lensopt's: forward-difference Jacobian,
    ``(JtJ + lambda diag(JtJ)) delta = -Jt r``, a step is kept only if the merit falls (lambda /3, else x4, six tries),
    stalled after two iterations without an accepted step. *min_thickness*, *max_thickness* and *min_radius* clamp the
    variables as in ``optimize_lens`` (the table's bound rows are what keep edges, centres and gaps in range).
    A glass variable moves the glass of surface *i* over *glass_candidates* (a list of media: catalogue names,
    ``(n_d, V_d)`` pairs or ``raytrace.glass`` dicts; or a dict ``"g<i>" -> list``) by an outer discrete sweep: after the
    continuous optimisation has converged each candidate is tried once (swapped in, the continuous variables re-optimised for
    *glass_iterations* iterations) and the best is kept if it lowers the merit; this repeats up to *outer_iterations* times
    with a full continuous re-optimisation between sweeps. A candidate equal to the glass already there is skipped, so a list
    holding only the current glass gives exactly the continuous result.

    Returns ``{"system", "table_before", "table_after", "merit_initial", "merit_final", "history", "iterations",
    "rejected_steps", "converged", "status", "variables", "glass", "dominant_after", "violated_after"}``;
    ``table_before`` / ``table_after`` are :func:`merit_evaluate` results, ``rejected_steps`` counts the trial steps
    refused, ``glass`` lists each glass variable with its initial / final medium and every candidate's merit.

    Example::

        r = optimize_lens_operands(lens, ops, ["c0", "c1", "t0", "g0"], glass_candidates=[(1.52, 64.2), (1.62, 36.4)],
                                   fields=m["fields"])
        r["merit_initial"], r["merit_final"], r["glass"][0]["final"]
    """
    system, operands, fields, wavelengths, field_weights, wavelength_weights = _unpack(
        system, operands, fields, wavelengths, field_weights, wavelength_weights)
    n_surf = len(system["surfaces"])
    cont, gvars = _split_variables(system, variables)
    if variables is None:
        varlist = LO._default_variables(system)
    else:
        varlist = [LO._parse_variable(v, n_surf) for v in cont]
        if not varlist and not gvars:
            raise ValueError("at least one variable is required")
    if len(varlist) > LO.MAX_VARIABLES:
        raise ValueError("too many variables (%d > %d)" % (len(varlist), LO.MAX_VARIABLES))
    if len(set(varlist)) != len(varlist):
        raise ValueError("duplicate variables")
    for kind, i, _ in varlist:
        s = system["surfaces"][i]
        if kind == "t" and s["t"] is None:
            raise ValueError("t%d is the image distance (None); give it a value or vary another surface" % i)
        if kind == "k" and s["R"] == INF:
            raise ValueError("k%d: a flat has no conic constant" % i)
    iterations = _int(iterations, "iterations", 1, LO.MAX_ITERATIONS)
    glass_iterations = _int(glass_iterations, "glass_iterations", 1, LO.MAX_ITERATIONS)
    outer_iterations = _int(outer_iterations, "outer_iterations", 1, 20)
    lam0 = _num(damping, "damping", positive=True)
    tol = _num(tolerance, "tolerance", nonneg=True)
    bounds = {"min_thickness": _num(min_thickness, "min_thickness", nonneg=True),
              "max_thickness": None if max_thickness is None else _num(max_thickness, "max_thickness", positive=True),
              "min_radius": _num(min_radius, "min_radius", positive=True)}
    if bounds["max_thickness"] is not None and bounds["max_thickness"] < bounds["min_thickness"]:
        raise ValueError("max_thickness < min_thickness")
    cands = _candidates(glass_candidates, gvars)

    # the start obeys the bounds, as in lensopt
    x_start = np.array([LO._get(system, v) for v in varlist], dtype=np.float64)
    start = LO._rebuild(system, x_start, varlist, bounds) if varlist else system
    ctx0 = _Ctx(start, fields, wavelengths, field_weights, wavelength_weights)
    rows0 = _normalise(ctx0, operands)
    fl, wls, fw, ww = ctx0.fields, ctx0.wls, ctx0.fw, ctx0.ww

    def table_of(sys_):
        ctx = _Ctx(sys_, fl, wls, fw, ww)
        return _run(ctx, rows0)

    def resid(sys_):
        return table_of(sys_)[1]

    before = merit_evaluate(start, operands, fl, wls, fw, ww)
    first = _lm(start, varlist, resid, bounds, iterations, lam0, tol)
    cur = first["system"]
    history = list(first["history"])
    total_it, rejected = first["iterations"], first["rejected"]
    status, converged, lam = first["status"], first["converged"], first["lam"]
    glass_log = [{"variable": "g%d" % i, "surface": i, "initial": copy.deepcopy(system["surfaces"][i]["n"]),
                  "final": None, "tried": [], "changed": False} for i in gvars]
    for _outer in range(outer_iterations if gvars else 0):
        changed = False
        for gl, i in zip(glass_log, gvars):
            best_m, best_sys = float(np.dot(resid(cur), resid(cur))), None
            here = _medium_key(cur["surfaces"][i]["n"])
            for cand in cands[i]:
                if _medium_key(cand) == here:
                    continue
                try:
                    trial = _with_glass(cur, i, cand)
                    res = _lm(trial, varlist, resid, bounds, glass_iterations, lam0, tol)
                except ValueError as e:
                    gl["tried"].append({"candidate": copy.deepcopy(cand), "merit": None, "error": str(e)})
                    continue
                rejected += res["rejected"]
                gl["tried"].append({"candidate": copy.deepcopy(cand), "merit": float(res["merit"]), "error": None})
                if res["merit"] < best_m * (1.0 - 1e-12):
                    best_m, best_sys = res["merit"], res["system"]
            if best_sys is not None:
                cur = best_sys
                gl["changed"] = True
                changed = True
        if not changed:
            break
        again = _lm(cur, varlist, resid, bounds, iterations, lam0, tol)
        cur = again["system"]
        history += again["history"]
        total_it += again["iterations"]
        rejected += again["rejected"]
        status, converged, lam = again["status"], again["converged"], again["lam"]
    for gl, i in zip(glass_log, gvars):
        gl["final"] = copy.deepcopy(cur["surfaces"][i]["n"])
    after = merit_evaluate(cur, operands, fl, wls, fw, ww)
    vars_out = []
    for v in varlist:
        v0, v1 = LO._get(start, v), LO._get(cur, v)
        if v[0] == "c":
            v0 = INF if v0 == 0.0 else 1.0 / v0
            v1 = INF if v1 == 0.0 else 1.0 / v1
        vars_out.append({"name": _var_name(v), "surface": v[1], "initial": float(v0), "final": float(v1)})
    return {"system": cur, "table_before": before, "table_after": after, "merit_initial": before["merit"],
            "merit_final": after["merit"], "history": [float(h) for h in history], "iterations": int(total_it),
            "rejected_steps": int(rejected), "converged": bool(converged), "status": status, "variables": vars_out,
            "glass": glass_log, "dominant_after": after["dominant"],
            "violated_after": [r["label"] for r in after["table"] if r["sense"] != "eq" and not r["satisfied"]],
            "damping_final": float(lam)}
