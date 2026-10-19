# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""lensconfig — multi-configuration (zoom / switchable) sequential lens systems.

A zoom lens, a two-position switchable objective or a focus-by-spacing design is one
prescription that exists in several *configurations*: a few operands (a spacing, a
curvature, a glass, an aspheric coefficient, the field, the wavelength set ...) take
a different value in each. Design programs hold them in a multi-configuration table;
here a ``raytrace.lens_system`` simply carries the key ``"configurations"``: a list
with one entry per configuration, each a *sparse* override of the base system::

    {"name": "tele",                              # optional label
     "surfaces": {2: {"t": 18.5}, 4: {"R": -40.0}},  # surface index -> fields to replace
     "system":   {"field": 3.0}}                  # system fields to replace

Surface fields: ``R t n k ap f asph mirror`` (the keys ``lens_system`` takes; ``decenter`` /
``tilt`` as well). System fields: ``wavelength_um field stop object_mm image_mm aim``.
Nothing else is accepted and nothing is dropped silently: an unknown key, a surface index
that does not exist or a value ``lens_system`` rejects is a ``ValueError`` naming the
configuration. The base system is never modified; every ``lens_with_configuration`` call
returns a fresh, fully resolved ``lens_system`` that every other op consumes unchanged.

The ops::

    lens_configurations(system)              -> list of resolved systems (one per configuration)
    lens_with_configuration(system, k)       -> resolved system k (0-based)
    lens_configuration_table(system)         -> the operand x configuration table (rows = what varies)
    lens_configuration_metrics(system, ...)  -> one number per configuration (EFL, BFL, RMS spot, MTF, EE)

``.zmx`` files carry configurations too; ``lensfile.lens_file_read`` / ``lens_file_write``
read and write them (the file lines are documented in
``docs/capabilities/sequential-lens-design-metrics.md``).
"""
from __future__ import annotations

import copy
import math

import numpy as np

import raytrace as RT

__all__ = ["lens_configurations", "lens_with_configuration", "lens_configuration_table",
           "lens_configuration_metrics", "lens_add_configuration"]

SURFACE_FIELDS = ("R", "t", "n", "k", "ap", "f", "asph", "mirror", "decenter", "tilt")
SYSTEM_FIELDS = ("wavelength_um", "field", "stop", "object_mm", "image_mm", "aim")
_CONFIG_KEYS = frozenset(("name", "surfaces", "system"))
METRICS = ("efl", "bfl", "rms_spot", "geo_spot", "mtf", "encircled_energy")


def _is_noncoaxial(system):
    return isinstance(system, dict) and "elements" in system and "surfaces" not in system


def _check(system, op):
    if _is_noncoaxial(system):
        raise ValueError("%s: configurations are defined for the coaxial raytrace.lens_system; a non-coaxial "
                         "system (raytrace3d) has no configuration table" % op)
    RT._check_system(system)
    cfgs = system.get("configurations")
    if not isinstance(cfgs, (list, tuple)) or len(cfgs) == 0:
        raise ValueError("%s: the system has no \"configurations\" (a non-empty list of override dicts; see "
                         "lens_add_configuration)" % op)
    return cfgs


def _surface_index(key, n, where, op):
    if isinstance(key, (bool, np.bool_)):
        raise ValueError("%s: %s: surface index %r is not an integer" % (op, where, key))
    try:
        i = int(key)
    except (TypeError, ValueError):
        raise ValueError("%s: %s: surface index %r is not an integer" % (op, where, key)) from None
    if isinstance(key, float) and key != i:
        raise ValueError("%s: %s: surface index %r is not an integer" % (op, where, key))
    if not 0 <= i < n:
        raise ValueError("%s: %s: surface %d does not exist (the system has surfaces 0..%d)" % (op, where, i, n - 1))
    return i


def _validate_config(cfg, k, system, op):
    """Check one configuration entry; returns ``({surface index: {field: value}}, {system field: value})``."""
    where = "configuration %d" % k
    if not isinstance(cfg, dict):
        raise ValueError("%s: %s must be a dict, got %r" % (op, where, type(cfg).__name__))
    unknown = sorted(set(cfg) - _CONFIG_KEYS)
    if unknown:
        raise ValueError("%s: %s: unknown key(s) %s (a configuration takes name / surfaces / system)"
                         % (op, where, unknown))
    ns = len(system["surfaces"])
    surf = {}
    raw = cfg.get("surfaces", {}) or {}
    if not isinstance(raw, dict):
        raise ValueError("%s: %s: \"surfaces\" must map a surface index to a dict of fields" % (op, where))
    for key, fields in raw.items():
        i = _surface_index(key, ns, where, op)
        if not isinstance(fields, dict) or not fields:
            raise ValueError("%s: %s: surface %d needs a non-empty dict of fields" % (op, where, i))
        bad = sorted(set(fields) - set(SURFACE_FIELDS))
        if bad:
            raise ValueError("%s: %s: surface %d has no overridable field(s) %s (use %s)"
                             % (op, where, i, bad, ", ".join(SURFACE_FIELDS)))
        if i in surf:
            raise ValueError("%s: %s: surface %d is listed twice" % (op, where, i))
        surf[i] = dict(fields)
    sysf = cfg.get("system", {}) or {}
    if not isinstance(sysf, dict):
        raise ValueError("%s: %s: \"system\" must be a dict" % (op, where))
    bad = sorted(set(sysf) - set(SYSTEM_FIELDS))
    if bad:
        raise ValueError("%s: %s: no overridable system field(s) %s (use %s)" % (op, where, bad,
                                                                                ", ".join(SYSTEM_FIELDS)))
    return surf, dict(sysf)


def _resolve(system, k, op):
    cfgs = _check(system, op)
    if isinstance(k, (bool, np.bool_)) or not isinstance(k, (int, np.integer)) or not 0 <= int(k) < len(cfgs):
        raise ValueError("%s: configuration index must be 0..%d, got %r" % (op, len(cfgs) - 1, k))
    k = int(k)
    surf, sysf = _validate_config(cfgs[k], k, system, op)
    lens = [dict(s) for s in system["surfaces"]]
    for i, fields in surf.items():
        for key, val in fields.items():
            lens[i][key] = copy.deepcopy(val)
        if "f" in fields and fields["f"] is not None:
            lens[i]["R"] = RT.INF
    stop = sysf.get("stop", system["stop"])
    kw = {"object_mm": sysf.get("object_mm", system["object_mm"]),
          "wavelength_um": sysf.get("wavelength_um", system["wavelength_um"]),
          "image_mm": sysf.get("image_mm", system["image_mm"]),
          "field": sysf.get("field", system["field"]),
          "aim": sysf.get("aim", system.get("aim", "paraxial"))}
    if "stop" in sysf and 0 <= int(stop) < len(lens) and lens[int(stop)].get("ap") is None:
        aps = [s["ap"] for s in lens if s.get("ap") is not None]
        if aps:
            lens[int(stop)]["ap"] = min(aps)
    try:
        out = RT.lens_system(lens, stop=stop, index_object=system["index_object"],
                             vignetting=system.get("vignetting"), **kw)
    except ValueError as e:
        raise ValueError("%s: configuration %d cannot be built: %s" % (op, k, e)) from None
    for key, val in system.items():
        if key not in out and key != "configurations":
            out[key] = copy.deepcopy(val)
    out["configuration"] = k
    out["configuration_name"] = str(cfgs[k].get("name", "config %d" % (k + 1)))
    return out


def lens_configurations(system=None) -> list:
    """多構成の処方を、構成ごとに解決した ``lens_system`` のリストにする(``table``)。

    *system* is a ``raytrace.lens_system`` that carries ``"configurations"``: a list of sparse
    override dicts ``{"name", "surfaces": {index: {field: value}}, "system": {field: value}}``
    (surface fields ``R t n k ap f asph mirror decenter tilt``, system fields ``wavelength_um field
    stop object_mm image_mm aim``). Returns one fully resolved ``lens_system`` per configuration, in
    order (each also carries ``configuration`` = its 0-based index and ``configuration_name``);
    every raytrace / lensimage / lensopt op takes them unchanged. ``None`` uses a two-position
    example (a thin-lens pair whose separation is 10 and 30 mm).

    **Fail-closed**: a configuration that names a surface that does not exist, an unknown field,
    or a value ``lens_system`` rejects raises ``ValueError`` naming the configuration; the base
    system is not modified (each result is an independent copy).

    Example::

        base = RT.lens_system([{"f": 100.0, "t": 20.0}, {"f": 100.0, "t": None}], stop=0,
                              object_mm=float("inf"))
        base["configurations"] = [{"surfaces": {0: {"t": d}}} for d in (10.0, 20.0, 30.0)]
        [RT.paraxial_trace(s)["efl"] for s in lens_configurations(base)]
    """
    op = "lens_configurations"
    if system is None:
        system = _example_system()
    cfgs = _check(system, op)
    return [_resolve(system, k, op) for k in range(len(cfgs))]


def lens_with_configuration(system=None, k: int = 0) -> dict:
    """多構成の処方の k 番目(0 始まり)の構成を解決した ``lens_system`` を返す(``table``)。

    Same resolution as :func:`lens_configurations` for one configuration. *k* is the position in
    ``system["configurations"]`` (configuration 1 of the design program is ``k = 0``). The base
    system is untouched. ``None`` uses the two-position example.

    Example::

        tele = lens_with_configuration(zoom, 2)
        RT.spot_stats(tele)["rms_radius"]
    """
    op = "lens_with_configuration"
    if system is None:
        system = _example_system()
    return _resolve(system, k, op)


def lens_configuration_table(system=None) -> dict:
    """多構成の表(行 = 構成で変わる量、列 = 構成)を返す(``table``)。

    The operand table of a multi-configuration editor. Returns ``{"n_configurations", "names",
    "rows", "columns"}``: ``rows`` is a list of ``{"operand", "surface", "field", "values"}`` where
    ``operand`` reads like ``"surface 2 t"`` or ``"system field"`` and ``values`` holds the resolved
    value in every configuration (not only the overrides), so a row is exactly what a table cell
    shows. A row appears only if the value differs between at least two configurations or is
    overridden somewhere. ``columns`` is the same table transposed (one dict per configuration,
    operand -> value) for display. ``None`` uses the two-position example.

    Example::

        t = lens_configuration_table(zoom)
        for r in t["rows"]:
            print(r["operand"], r["values"])
    """
    op = "lens_configuration_table"
    if system is None:
        system = _example_system()
    cfgs = _check(system, op)
    res = [_resolve(system, k, op) for k in range(len(cfgs))]
    keys = []                       # (surface or None, field) in the order first overridden
    for k in range(len(cfgs)):
        surf, sysf = _validate_config(cfgs[k], k, system, op)
        for i in sorted(surf):
            for f in SURFACE_FIELDS:
                if f in surf[i] and (i, f) not in keys:
                    keys.append((i, f))
        for f in SYSTEM_FIELDS:
            if f in sysf and (None, f) not in keys:
                keys.append((None, f))
    rows = []
    for (i, f) in keys:
        vals = [copy.deepcopy(r["surfaces"][i].get(f) if i is not None else r.get(f)) for r in res]
        rows.append({"operand": ("surface %d %s" % (i, f)) if i is not None else ("system %s" % f),
                     "surface": i, "field": f, "values": vals})
    names = [r["configuration_name"] for r in res]
    columns = [{"name": names[k], "values": {row["operand"]: row["values"][k] for row in rows}}
               for k in range(len(res))]
    return {"n_configurations": len(res), "names": names, "rows": rows, "columns": columns}


def _psf_ee(system, field, radius_um):
    import lensimage as LI
    import optics as O
    psf, _ref, dx, _n = LI._psf_core(system, field, None, None, 4)
    psf = psf / psf.sum()
    curve = O.encircled_energy(psf, pixel_pitch_um=dx, samples=64, max_radius_um=radius_um)
    return float(curve[-1, 1])


def lens_configuration_metrics(system=None, metric: str = "efl", field=None, frequency_cpmm=None,
                               radius_um=None) -> dict:
    """構成ごとに 1 つの指標(EFL・後端焦点距離・RMS スポット・MTF・囲みエネルギー)を並べる(``table``)。

    Runs one existing metric on every resolved configuration; nothing is recomputed here. *metric*:
    ``"efl"`` / ``"bfl"`` (``raytrace.paraxial_trace``), ``"rms_spot"`` / ``"geo_spot"`` (radius in
    mm, ``raytrace.spot_stats`` at *field*, 8 rings), ``"mtf"`` (tangential MTF at
    *frequency_cpmm*, ``lensimage.through_focus_mtf`` at zero defocus), ``"encircled_energy"``
    (fraction of the PSF energy inside *radius_um* micrometres, ``lensimage`` PSF +
    ``optics.encircled_energy``). *field* defaults to each configuration's own field. Returns
    ``{"metric", "unit", "values", "names", "n_configurations"}`` with one number per configuration
    in order. ``None`` uses the two-position example.

    Example::

        lens_configuration_metrics(zoom, "efl")["values"]
        lens_configuration_metrics(zoom, "mtf", field=0.0, frequency_cpmm=20.0)["values"]
    """
    op = "lens_configuration_metrics"
    if metric not in METRICS:
        raise ValueError("%s: metric must be one of %s, got %r" % (op, ", ".join(METRICS), metric))
    systems = lens_configurations(system)
    vals, unit = [], "mm"
    for s in systems:
        f = s["field"] if field is None else field
        if metric in ("efl", "bfl"):
            vals.append(float(RT.paraxial_trace(s)[metric]))
        elif metric in ("rms_spot", "geo_spot"):
            st = RT.spot_stats(s, field=f)
            vals.append(float(st["rms_radius" if metric == "rms_spot" else "geo_radius"]))
        elif metric == "mtf":
            import lensimage as LI
            if frequency_cpmm is None or not (isinstance(frequency_cpmm, (int, float))
                                              and math.isfinite(frequency_cpmm) and frequency_cpmm > 0):
                raise ValueError("%s: metric 'mtf' needs frequency_cpmm > 0" % op)
            r = LI.through_focus_mtf(s, frequency_cpmm=[float(frequency_cpmm)], defocus_mm=[0.0], field=f)
            vals.append(float(np.asarray(r["tangential"])[0, 0]))
            unit = "1"
        else:
            if radius_um is None or not (isinstance(radius_um, (int, float)) and math.isfinite(radius_um)
                                         and radius_um > 0):
                raise ValueError("%s: metric 'encircled_energy' needs radius_um > 0" % op)
            vals.append(_psf_ee(s, f, float(radius_um)))
            unit = "1"
    return {"metric": metric, "unit": unit, "values": vals,
            "names": [s["configuration_name"] for s in systems], "n_configurations": len(systems)}


def lens_add_configuration(system, surfaces=None, system_fields=None, name=None) -> dict:
    """Return a copy of *system* with one more configuration appended (``table``).

    *surfaces* is ``{index: {field: value}}``, *system_fields* ``{field: value}``; both are checked
    with the same rules as the resolution (a bad entry is a ``ValueError`` and nothing is added).
    The input is not modified.

    Example::

        zoom = lens_add_configuration(zoom, {2: {"t": 12.0}}, name="mid")
    """
    op = "lens_add_configuration"
    RT._check_system(system)
    new = copy.deepcopy(system)
    cfg = {}
    if name is not None:
        cfg["name"] = str(name)
    if surfaces:
        cfg["surfaces"] = {int(i): dict(v) for i, v in surfaces.items()}
    if system_fields:
        cfg["system"] = dict(system_fields)
    new["configurations"] = list(new.get("configurations") or []) + [cfg]
    _resolve(new, len(new["configurations"]) - 1, op)           # validates (raises, nothing returned)
    return new


def _example_system():
    base = RT.lens_system([{"f": 100.0, "t": 10.0, "ap": 5.0}, {"f": 100.0, "t": None}], stop=0, object_mm=RT.INF)
    base["configurations"] = [{"name": "wide", "surfaces": {0: {"t": 10.0}}},
                              {"name": "tele", "surfaces": {0: {"t": 30.0}}}]
    return base
