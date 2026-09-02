# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""raytrace — sequential lens design: real ray tracing, OPD wavefront, Seidel sums, tolerances.

``optics`` stops at the paraxial (ABCD) picture; this module traces **real rays**
through a sequential prescription of spherical / conic surfaces so that the
questions a lens designer actually asks can be answered from first principles:

* where does the image land and how large is it (``paraxial_trace``: EFL, BFL,
  principal planes, pupils, f-number, magnification);
* how big is the blur (``spot_diagram`` / ``ray_fan``: exact transverse ray
  aberration, RMS spot radius);
* what does the wavefront look like (``opd_map``: optical path difference on the
  exit-pupil reference sphere, in waves — feed it to ``match3d.fit_zernike`` and
  ``optics.wavefront_stats`` for Zernike / Strehl);
* which surface causes it (``seidel_coefficients``: third-order S_I … S_V and
  the two chromatic sums, per surface);
* what happens in manufacturing (``tolerance_analysis``: Monte-Carlo perturbation
  of radii / thickness / index / decenter / tilt, plus per-parameter sensitivity).

Conventions (every function follows these; they are the textbook ones — Welford,
*Aberrations of Optical Systems*; Smith, *Modern Optical Engineering*):

* the optical axis is **+z** and light travels toward +z. Surfaces are listed in
  the order light meets them. Surface *i* sits at vertex ``z_i``; ``t_i`` is the
  axial distance from vertex *i* to vertex *i+1*; ``n_i`` is the refractive index
  of the medium **after** surface *i* (``n[0]`` = object space, default air 1.0).
* radius ``R`` is **positive when the centre of curvature lies to the right (+z)**
  of the vertex; ``inf`` (or 0 curvature) is a flat. Conic constant ``k``:
  0 sphere, −1 paraboloid, <−1 hyperboloid, −1<k<0 prolate ellipsoid, >0 oblate.
  The surface sag is ``z = c r² / (1 + sqrt(1 − (1+k) c² r²))``.
* a mirror is a surface with ``mirror=True``: the ray is reflected and keeps
  travelling in its (now −z) direction; thicknesses after a mirror are still
  given as **positive physical distances** (the code handles the sign).
* the aperture stop is one of the surfaces (``stop``); pupils are the paraxial
  images of it. Fields are given as angles in degrees for an object at infinity
  and as object heights in millimetres for a finite object distance.
* lengths in millimetres, wavelengths in micrometres, angles in degrees at the
  API (radians inside), OPD in waves at the system wavelength.
* every input is validated fail-closed (``ValueError``); a ray that misses a
  surface, is vignetted by a semi-aperture, or suffers total internal reflection
  is reported as ``NaN`` rather than silently clipped.

Glass: a surface's medium may be a plain index, a ``(n_d, V_d)`` pair (index at
the d line and Abbe number — ``glass`` fits a two-term Cauchy model through the
d line and the F–C dispersion), a catalogue name such as ``"N-BK7"`` (a real
Sellmeier curve, see ``glass_catalog``), or a ``sellmeier(...)`` dict;
``refractive_index`` evaluates any of them at any wavelength.

Aspheres: a surface may carry even polynomial deformation coefficients
``asph=(A4, A6, A8, …)`` added to the conic sag, ``z = z_conic(r) + A4 r⁴ +
A6 r⁶ + …`` (mm⁻³, mm⁻⁵, … — the coefficients of the *sag in mm* as a function
of *r in mm*). Real rays are intersected by Newton iteration from the conic
intersection; ``seidel_coefficients`` includes the fourth-order term ``A4``.
"""
from __future__ import annotations

import math

import numpy as np

# Fraunhofer lines (micrometres)
WL_F, WL_D, WL_C = 0.48613, 0.58756, 0.65627
INF = float("inf")


# --------------------------------------------------------------------------- #
# validation helpers
# --------------------------------------------------------------------------- #
def _finite(x, name, positive=False, nonneg=False):
    try:
        v = float(x)
    except (TypeError, ValueError) as e:
        raise ValueError("%s must be a real number, got %r" % (name, x)) from e
    if not math.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (name, x))
    if positive and v <= 0:
        raise ValueError("%s must be > 0, got %r" % (name, x))
    if nonneg and v < 0:
        raise ValueError("%s must be >= 0, got %r" % (name, x))
    return v


def _radius(x, name):
    if x is None:
        return INF
    if isinstance(x, str) and x.lower() in ("inf", "flat", "plano"):
        return INF
    v = float(x)
    if math.isnan(v) or v == 0.0:
        raise ValueError("%s: a radius must be non-zero (use inf for a flat), got %r" % (name, x))
    return v


# --------------------------------------------------------------------------- #
# glass
# --------------------------------------------------------------------------- #
def glass(nd, vd):
    """A dispersive medium from its d-line index *nd* and Abbe number *vd*.

    Returns ``{"nd": nd, "vd": vd, "A": A, "B": B}`` — the two-term Cauchy model
    ``n(λ) = A + B/λ²`` (λ in µm) fitted so that ``n(λ_d) = n_d`` and
    ``n(λ_F) − n(λ_C) = (n_d − 1)/V_d``. Good to ~1e-4 over the visible for
    ordinary crowns and flints; it is a *model*, not a catalogue.
    """
    nd = _finite(nd, "nd", positive=True)
    vd = _finite(vd, "vd", positive=True)
    if nd < 1.0:
        raise ValueError("nd must be >= 1, got %r" % nd)
    dn = (nd - 1.0) / vd                                   # n_F - n_C
    B = dn / (1.0 / WL_F ** 2 - 1.0 / WL_C ** 2)
    A = nd - B / WL_D ** 2
    return {"nd": nd, "vd": vd, "A": A, "B": B}


#: Three-term Sellmeier coefficients ``(B1, B2, B3, C1, C2, C3)`` — ``n² − 1 =
#: Σ B_i λ² / (λ² − C_i)`` with λ in µm — for a small set of catalogue glasses
#: and crystals. The Schott "N-" values are the manufacturer's published fit
#: constants (Schott optical glass data sheets, 2017 catalogue); fused silica is
#: Malitson (1965), CaF2 Malitson (1963), sapphire (ordinary ray) Malitson &
#: Dodge (1972). ``tests/test_raytrace.py`` checks every entry's d-line index
#: and Abbe number against the catalogue figures, so a typo cannot survive.
#: Valid over the visible / near infrared (≈0.3–2.3 µm); ``refractive_index``
#: refuses wavelengths outside ``_SELLMEIER_RANGE``.
_SELLMEIER = {
    "N-BK7":   (1.03961212, 0.231792344, 1.01046945, 0.00600069867, 0.0200179144, 103.560653),
    "N-K5":    (1.08511833, 0.199562005, 0.930511663, 0.00661099503, 0.024110866, 111.982777),
    "N-BAK4":  (1.28834642, 0.132817724, 0.945395373, 0.00779980626, 0.0315631177, 105.965875),
    "N-SK16":  (1.34317774, 0.241144399, 0.994317969, 0.00704687339, 0.0229005, 92.7508526),
    "N-SSK5":  (1.59222659, 0.103520774, 1.05174016, 0.00920284626, 0.0423530072, 106.927374),
    "N-BAF10": (1.5851495, 0.143559385, 1.08521269, 0.00926681282, 0.0424489805, 105.613573),
    "N-LAK22": (1.14229781, 0.535138441, 1.04088385, 0.00585778594, 0.0198546147, 100.834017),
    "N-LAK9":  (1.46231905, 0.344399589, 1.15508372, 0.00724270156, 0.0243353131, 85.4686868),
    "N-LASF9": (2.00029547, 0.298926886, 1.80691843, 0.0121426017, 0.0538736236, 156.530829),
    "N-FK51A": (0.971247817, 0.216901417, 0.904651666, 0.00472301995, 0.0153575612, 168.68133),
    "N-F2":    (1.39757037, 0.159201403, 1.2686543, 0.00995906143, 0.0546931752, 119.248346),
    "N-SF2":   (1.47343127, 0.163681849, 1.36920899, 0.0109019098, 0.0585683687, 127.404933),
    "N-SF5":   (1.52481889, 0.187882145, 1.42729911, 0.011254756, 0.0588995392, 129.141675),
    "N-SF10":  (1.62153902, 0.256287842, 1.64447552, 0.0122241457, 0.0595736775, 147.468793),
    "N-SF11":  (1.73759695, 0.313747346, 1.89878101, 0.013188707, 0.0623068142, 155.23629),
    "N-SF6":   (1.77931763, 0.338149866, 2.08734474, 0.0133714182, 0.0617533621, 174.01759),
    "N-SF57":  (1.87543831, 0.37375749, 2.30001797, 0.0141749518, 0.0640509927, 177.389795),
    "SILICA":  (0.6961663, 0.4079426, 0.8974794, 0.0684043 ** 2, 0.1162414 ** 2, 9.896161 ** 2),
    "CAF2":    (0.5675888, 0.4710914, 3.8484723, 0.050263605 ** 2, 0.1003909 ** 2, 34.649040 ** 2),
    "SAPPHIRE": (1.4313493, 0.65054713, 5.3414021, 0.0726631 ** 2, 0.1193242 ** 2, 18.028251 ** 2),
}
_SELLMEIER_RANGE = (0.3, 2.3)
_GLASS_ALIASES = {"BK7": "N-BK7", "FUSED_SILICA": "SILICA", "SIO2": "SILICA", "FLUORITE": "CAF2",
                  "AL2O3": "SAPPHIRE", "SF11": "N-SF11", "SF2": "N-SF2", "F2": "N-F2", "SK16": "N-SK16"}


def _catalog_key(name):
    if not isinstance(name, str):
        raise ValueError("a glass name must be a string, got %r" % type(name).__name__)
    key = name.strip().upper().replace(" ", "")
    key = _GLASS_ALIASES.get(key, key)
    if key not in _SELLMEIER:
        raise ValueError("unknown glass %r (catalogue: %s)" % (name, ", ".join(sorted(_SELLMEIER))))
    return key


def sellmeier(B1, B2, B3, C1, C2, C3, name="custom"):
    """A dispersive medium from three-term Sellmeier constants (``table``).

    ``n²(λ) − 1 = B1 λ²/(λ² − C1) + B2 λ²/(λ² − C2) + B3 λ²/(λ² − C3)`` with λ in
    µm (the form every glass maker publishes). Returns ``{"name", "sellmeier",
    "nd", "vd", "offset"}`` — *nd* / *vd* are **evaluated** from the curve, so
    they can be checked against the data sheet. ``offset`` (0) is an additive
    index shift used by :func:`tolerance_analysis` for melt-to-melt variation.
    """
    coef = tuple(_finite(v, k, nonneg=True) for v, k in zip((B1, B2, B3, C1, C2, C3), ("B1", "B2", "B3", "C1", "C2", "C3")))
    g = {"name": str(name), "sellmeier": coef, "offset": 0.0}
    nd = refractive_index(g, WL_D)
    nf = refractive_index(g, WL_F)
    nc = refractive_index(g, WL_C)
    if not (nf > nc > 0):
        raise ValueError("Sellmeier constants give anomalous dispersion in the visible (n_F <= n_C)")
    g["nd"] = nd
    g["vd"] = (nd - 1.0) / (nf - nc)
    return g


def glass_catalog(name=None):
    """A catalogue glass by name (``table``), or the list of names when *name* is None.

    Names: Schott ``"N-BK7"``, ``"N-K5"``, ``"N-BAK4"``, ``"N-SK16"``, ``"N-SSK5"``,
    ``"N-BAF10"``, ``"N-LAK22"``, ``"N-LAK9"``, ``"N-LASF9"``, ``"N-FK51A"``,
    ``"N-F2"``, ``"N-SF2"``, ``"N-SF5"``, ``"N-SF10"``, ``"N-SF11"``, ``"N-SF6"``,
    ``"N-SF57"`` and the crystals ``"SILICA"`` (fused), ``"CAF2"``, ``"SAPPHIRE"``
    (ordinary ray); case-insensitive, a few aliases (``"BK7"``, ``"SF11"``,
    ``"fused_silica"``, ``"fluorite"``). Any surface's ``n`` may simply be the
    name — ``lens_system`` resolves it. The returned dict is the
    :func:`sellmeier` form with the evaluated ``nd`` / ``vd``.
    """
    if name is None:
        return sorted(_SELLMEIER)
    key = _catalog_key(name)
    g = sellmeier(*_SELLMEIER[key], name=key)
    return g


def refractive_index(medium, wavelength_um=WL_D):
    """Index of *medium* at *wavelength_um*.

    *medium* is a number (dispersion-free), a ``(nd, vd)`` pair, a dict from
    :func:`glass` or :func:`sellmeier`, or a catalogue name (:func:`glass_catalog`).
    Air (1.0) and vacuum are returned unchanged.
    """
    wl = _finite(wavelength_um, "wavelength_um", positive=True)
    if isinstance(medium, str):
        medium = glass_catalog(medium)
    if isinstance(medium, dict) and "sellmeier" in medium:
        if not (_SELLMEIER_RANGE[0] <= wl <= _SELLMEIER_RANGE[1]):
            raise ValueError("wavelength %.4g um is outside the Sellmeier fit range %s" % (wl, _SELLMEIER_RANGE))
        B1, B2, B3, C1, C2, C3 = medium["sellmeier"]
        l2 = wl * wl
        n2 = 1.0 + B1 * l2 / (l2 - C1) + B2 * l2 / (l2 - C2) + B3 * l2 / (l2 - C3)
        if not (n2 > 0 and math.isfinite(n2)):
            raise ValueError("Sellmeier curve is singular at %.4g um" % wl)
        return float(math.sqrt(n2) + medium.get("offset", 0.0))
    if isinstance(medium, dict) and "A" in medium:
        return float(medium["A"] + medium["B"] / wl ** 2)
    if isinstance(medium, (tuple, list)) and len(medium) == 2:
        g = glass(*medium)
        return float(g["A"] + g["B"] / wl ** 2)
    n = _finite(medium, "index", positive=True)
    if n < 1.0:
        raise ValueError("a refractive index must be >= 1, got %r" % n)
    return n


def _dispersion(medium):
    """``n_F - n_C`` of *medium* (0 for a dispersion-free index)."""
    if isinstance(medium, str) or (isinstance(medium, dict) and "sellmeier" in medium):
        return refractive_index(medium, WL_F) - refractive_index(medium, WL_C)
    if isinstance(medium, dict) and "A" in medium:
        return float(medium["B"] * (1.0 / WL_F ** 2 - 1.0 / WL_C ** 2))
    if isinstance(medium, (tuple, list)) and len(medium) == 2:
        return (float(medium[0]) - 1.0) / float(medium[1])
    return 0.0


def _index_offset(medium, delta):
    """*medium* with its index shifted by *delta* at every wavelength (tolerancing)."""
    if isinstance(medium, str):
        medium = glass_catalog(medium)
    if isinstance(medium, dict) and "sellmeier" in medium:
        q = dict(medium); q["offset"] = float(medium.get("offset", 0.0)) + delta
        return q
    if isinstance(medium, dict) and "A" in medium:
        q = dict(medium); q["A"] = medium["A"] + delta
        return q
    if isinstance(medium, (tuple, list)):
        return (float(medium[0]) + delta, float(medium[1]))
    n = float(medium) + delta
    return n if n >= 1.0 else float(medium)


# --------------------------------------------------------------------------- #
# prescription
# --------------------------------------------------------------------------- #
def lens_system(surfaces=None, stop=None, object_mm=INF, wavelength_um=WL_D,
                index_object=1.0, image_mm=None, field=None):
    """Build a validated sequential prescription (the ``table`` every other op consumes).

    *surfaces* is a list; each entry is a dict ``{"R", "t", "n", "k", "ap",
    "mirror", "decenter", "tilt", "asph"}`` or a tuple ``(R, t, n[, k[, ap]])``:

    * ``R`` radius (mm, ``inf`` for flat), ``t`` thickness to the next surface
      (mm, the last one is the distance to the image plane when *image_mm* is
      not given — use ``None`` to place the image at the paraxial focus),
      ``n`` medium after the surface (index, ``(nd, vd)`` or :func:`glass`),
      ``k`` conic (default 0), ``ap`` semi-aperture in mm (default ``None`` =
      unlimited), ``mirror`` bool, ``decenter`` ``(dx, dy)`` mm, ``tilt``
      ``(ax, ay)`` degrees about x and y, ``asph`` even aspheric coefficients
      ``(A4, A6, A8, …)`` in mm⁻³, mm⁻⁵, … (default none = pure conic).
    * *stop*: index of the aperture-stop surface (default: the first surface).
      The stop's ``ap`` is the stop radius (required unless every surface has
      one, in which case the smallest is used).
    * *object_mm*: distance from the first vertex to the object (``inf`` for a
      collimated object); *index_object*: index of object space.
    * *field*: default field for the analysis ops — degrees (infinite object)
      or object height in mm (finite object). Default 0 (on axis).

    Default (no *surfaces*): a plano-convex BK7 singlet, ``f ≈ 100 mm``,
    ``f/4``, stop at the first surface — a sensible starting point for the
    examples and for the no-argument registry call.

    Returns a plain dict (JSON-friendly) — pass it to the other functions.
    """
    if surfaces is None:
        surfaces = [{"R": 51.68, "t": 5.0, "n": (1.5168, 64.17), "ap": 12.5},
                    {"R": INF, "t": None, "n": 1.0}]
        stop = 0 if stop is None else stop
    if not isinstance(surfaces, (list, tuple)) or len(surfaces) == 0:
        raise ValueError("surfaces must be a non-empty list of dicts or tuples")
    out = []
    for i, s in enumerate(surfaces):
        if isinstance(s, (tuple, list)):
            keys = ("R", "t", "n", "k", "ap")
            s = {k: v for k, v in zip(keys, s)}
        if not isinstance(s, dict) or "R" not in s or "n" not in s:
            raise ValueError("surface %d must have at least R, t and n (got %r)" % (i, s))
        R = _radius(s.get("R"), "surface %d R" % i)
        t = s.get("t", None)
        t = None if t is None else _finite(t, "surface %d t" % i, nonneg=True)
        if t is None and i != len(surfaces) - 1:
            raise ValueError("surface %d: only the last surface may omit t" % i)
        med = s["n"]
        n_now = refractive_index(med, wavelength_um)      # validates
        k = _finite(s.get("k", 0.0), "surface %d k" % i)
        ap = s.get("ap", None)
        ap = None if ap is None else _finite(ap, "surface %d ap" % i, positive=True)
        mirror = bool(s.get("mirror", False))
        dec = tuple(float(v) for v in s.get("decenter", (0.0, 0.0)))
        tilt = tuple(float(v) for v in s.get("tilt", (0.0, 0.0)))
        if len(dec) != 2 or len(tilt) != 2 or not all(map(math.isfinite, dec + tilt)):
            raise ValueError("surface %d: decenter/tilt must be finite pairs" % i)
        asph = s.get("asph", None)
        if asph is None:
            asph = ()
        elif isinstance(asph, (int, float, bool)) or isinstance(asph, str):
            raise ValueError("surface %d: asph must be a sequence (A4, A6, ...) of coefficients" % i)
        else:
            asph = tuple(_finite(a, "surface %d asph[%d]" % (i, j)) for j, a in enumerate(asph))
            if len(asph) > 8:
                raise ValueError("surface %d: at most 8 aspheric coefficients (A4..A18)" % i)
            while asph and asph[-1] == 0.0:
                asph = asph[:-1]
        if asph and R == INF and k != 0.0:
            raise ValueError("surface %d: a flat base with a conic constant is meaningless" % i)
        if math.isfinite(R) and k > -1.0 and ap is not None and (1.0 + k) * (ap / R) ** 2 > 1.0:
            raise ValueError("surface %d: semi-aperture %.3g exceeds the conic's extent for R=%.3g" % (i, ap, R))
        out.append({"R": R, "t": t, "n": med, "k": k, "ap": ap, "mirror": mirror,
                    "decenter": dec, "tilt": tilt, "asph": asph, "n_value": n_now,
                    "dn": _dispersion(med)})
    stop = 0 if stop is None else int(stop)
    if not 0 <= stop < len(out):
        raise ValueError("stop must index a surface (0..%d), got %r" % (len(out) - 1, stop))
    if out[stop]["ap"] is None:
        aps = [s["ap"] for s in out if s["ap"] is not None]
        if not aps:
            raise ValueError("the stop surface needs a semi-aperture 'ap' (or any surface must have one)")
        out[stop]["ap"] = min(aps)
    obj = float(object_mm)
    if obj != INF and (not math.isfinite(obj) or obj <= 0):
        raise ValueError("object_mm must be > 0 or inf, got %r" % object_mm)
    n0 = refractive_index(index_object, wavelength_um)
    sysd = {"surfaces": out, "stop": stop, "object_mm": obj, "index_object": n0,
            "wavelength_um": _finite(wavelength_um, "wavelength_um", positive=True),
            "image_mm": None if image_mm is None else _finite(image_mm, "image_mm"),
            "field": 0.0 if field is None else _finite(field, "field")}
    return sysd


def _check_system(system):
    if not isinstance(system, dict) or "surfaces" not in system or "stop" not in system:
        raise ValueError("expected the dict returned by lens_system(), got %r" % type(system).__name__)
    return system


# --------------------------------------------------------------------------- #
# paraxial model (signed indices / thicknesses for mirrors)
# --------------------------------------------------------------------------- #
def _paraxial_model(system, wavelength_um=None):
    """Curvatures, signed thicknesses and signed indices for the (y, u) trace."""
    surf = system["surfaces"]
    wl = system["wavelength_um"] if wavelength_um is None else wavelength_um
    c = np.array([0.0 if s["R"] == INF else 1.0 / s["R"] for s in surf])
    n = [system["index_object"]]
    sign = 1.0
    for s in surf:
        if s["mirror"]:
            sign = -sign
            n.append(sign * abs(n[-1]))
        else:
            n.append(sign * refractive_index(s["n"], wl))
    n = np.array(n)
    t = np.array([0.0 if s["t"] is None else s["t"] for s in surf])
    t_signed = t * np.sign(n[1:])                         # after a mirror light goes -z
    return c, t_signed, n


def _trace_paraxial(c, t, n, y0, u0, start=0):
    """Trace one paraxial ray; returns arrays y (at each surface) and u' (after each)."""
    ys, us = [], []
    y, u = y0, u0
    for i in range(start, len(c)):
        ys.append(y)
        # refraction: n' u' = n u - y c (n' - n)
        u = (n[i] * u - y * c[i] * (n[i + 1] - n[i])) / n[i + 1]
        us.append(u)
        y = y + t[i] * u
    return np.array(ys), np.array(us)


def paraxial_trace(system):
    """First-order properties of the prescription: focal lengths, pupils, image.

    Returns a dict with ``efl`` (effective focal length, mm; negative for a
    diverging system), ``bfl`` (last vertex → paraxial focus), ``ffl`` (first
    vertex → front focus, negative when in front), ``pp_front`` / ``pp_rear``
    (principal planes measured from the first / last vertex), ``image_mm``
    (last vertex → paraxial image of the given object), ``magnification``
    (transverse; 0 for an object at infinity), ``ep_position`` / ``ep_radius``
    (entrance pupil from the first vertex), ``xp_position`` / ``xp_radius``
    (exit pupil from the last vertex), ``fno`` (image-space f-number,
    ``efl / (2·ep_radius)``), ``na_image``, ``lagrange`` (the Lagrange invariant
    for the system's default field), ``marginal`` / ``chief`` (the two paraxial
    rays: heights and post-surface slopes at every surface).

    Verified against the closed forms: single refracting surface
    ``n'/s' = n/s + (n' − n)/R``, the thick-lens lensmaker equation and its
    thin-lens limit, and a mirror ``f = −R/2`` (see ``tests/test_raytrace.py``).
    """
    _check_system(system)
    c, t, n = _paraxial_model(system)
    ns = len(c)
    # --- focal properties from a collimated axial ray (y=1, u=0) --- #
    y, u = _trace_paraxial(c, t, n, 1.0, 0.0)
    if abs(u[-1]) < 1e-15:
        efl = INF
        bfl = INF
    else:
        efl = -1.0 / u[-1] * (n[-1] / abs(n[-1]))          # n-signed: f = -y0/u' in image space
        efl = -y[0] / u[-1]
        bfl = -y[-1] / u[-1]
    # front focal length: reverse trace (light from the image side)
    # the system seen from the image side: surfaces reversed, curvatures negated,
    # indices reversed (light now travels -z, which the mirrored geometry maps to +z)
    c_r = -c[::-1]
    n_r = n[::-1]
    t_r = np.append(t[::-1][1:], 0.0)
    y_r, u_r = _trace_paraxial(c_r, t_r, n_r, 1.0, 0.0)
    ffl = (y_r[-1] / u_r[-1]) if abs(u_r[-1]) > 1e-15 else -INF
    pp_rear = bfl - efl if math.isfinite(efl) else INF
    pp_front = ffl + efl if math.isfinite(efl) else -INF
    # --- pupils: the stop imaged into object / image space --- #
    stop = system["stop"]
    stop_r = system["surfaces"][stop]["ap"]
    # ray from the stop centre backwards: trace forward a ray that has y=0 at the stop
    # with unit slope there, using the linearity of the paraxial trace.
    def y_at_stop(y0, u0):
        yy, _ = _trace_paraxial(c, t, n, y0, u0)
        return yy[stop]
    obj = system["object_mm"]
    if obj == INF:
        # object at infinity: chief rays are parallel; entrance pupil = plane where the
        # chief ray (y_stop = 0) crosses the axis. Trace ray with u0=slope s, y0=h:
        # y_stop = a*h + b*s -> h = -b/a * s; EP at z = -h/s = b/a before surface 0.
        a = y_at_stop(1.0, 0.0)
        b = y_at_stop(0.0, 1.0)
        if abs(a) < 1e-15:
            raise ValueError("the stop cannot be imaged into object space (degenerate system)")
        ep_pos = b / a                                   # from first vertex (negative = in front)
        ep_radius = stop_r / abs(a)
        mag = 0.0
    else:
        # finite object: axial ray from the object point with slope s: y0 = s*obj at S0
        a = y_at_stop(obj, 1.0)                          # y_stop per unit slope (ray from axial object point)
        b = y_at_stop(1.0, 0.0)
        # chief ray from object height H: y0 = H + s*obj, u0 = s -> y_stop = b*H + a*s = 0
        # entrance pupil: where does that chief ray cross the axis? y(z) = H + s*(obj+z) = 0
        if abs(a) < 1e-15:
            raise ValueError("the stop cannot be imaged into object space (degenerate system)")
        s_per_H = -b / a                                  # chief-ray slope per unit object height
        ep_pos = -obj - 1.0 / s_per_H if abs(s_per_H) > 1e-15 else -INF
        # marginal ray slope s_m = stop_r / a ; EP radius = |s_m| * (obj + ep_pos)
        s_m = stop_r / abs(a)
        ep_radius = abs(s_m * (obj + ep_pos)) if math.isfinite(ep_pos) else INF
        mag = None
    # exit pupil: trace the (paraxial) chief ray forward and find where it crosses the axis
    if obj == INF:
        h = -b / a
        yc, uc = _trace_paraxial(c, t, n, h, 1.0)
        ym, um = _trace_paraxial(c, t, n, ep_radius, 0.0)
        img = bfl
        lagrange = n[0] * (1.0 * ep_radius - 0.0 * h)      # n (ubar*y - u*ybar) at surface 0
    else:
        s0 = s_per_H                                      # chief slope per unit object height
        yc, uc = _trace_paraxial(c, t, n, 1.0 + s0 * obj, s0)   # H = 1
        s_m = stop_r / abs(a)
        ym, um = _trace_paraxial(c, t, n, s_m * obj, s_m)
        img = -ym[-1] / um[-1] if abs(um[-1]) > 1e-15 else INF
        mag = (yc[-1] + uc[-1] * img) / 1.0 if math.isfinite(img) else INF
        lagrange = n[0] * (s0 * (s_m * obj) - s_m * (1.0 + s0 * obj))
    xp_pos = -yc[-1] / uc[-1] if abs(uc[-1]) > 1e-15 else INF   # from last vertex
    xp_radius = abs(ym[-1] + um[-1] * xp_pos) if math.isfinite(xp_pos) else INF
    # after an odd number of mirrors the signed paraxial axis points against the
    # light: report distances along the direction of travel (physical) and the
    # focal length converging-positive, so a concave mirror reads f = -R/2 > 0.
    sgn = 1.0 if n[-1] > 0 else -1.0
    efl *= sgn; bfl *= sgn; img *= sgn; xp_pos *= sgn
    pp_rear = bfl - efl if math.isfinite(efl) else INF
    fno = INF if ep_radius == 0 or not math.isfinite(efl) else abs(efl) / (2.0 * ep_radius)
    na_img = abs(n[-1]) * abs(um[-1]) if obj != INF else abs(n[-1]) * abs(um[-1])
    return {"efl": float(efl), "bfl": float(bfl), "ffl": float(ffl),
            "pp_front": float(pp_front), "pp_rear": float(pp_rear),
            "image_mm": float(img), "magnification": float(mag) if mag is not None else 0.0,
            "ep_position": float(ep_pos), "ep_radius": float(ep_radius),
            "xp_position": float(xp_pos), "xp_radius": float(xp_radius),
            "fno": float(fno), "na_image": float(na_img), "lagrange": float(lagrange),
            "marginal": {"y": ym.tolist(), "u": um.tolist()},
            "chief": {"y": yc.tolist(), "u": uc.tolist()},
            "n_surfaces": ns}


def thick_lens(R1=50.0, R2=-50.0, thickness=5.0, index=1.5168):
    """Closed-form thick lens in air: EFL, back/front focal lengths, principal points.

    ``1/f = (n−1)[1/R1 − 1/R2 + (n−1)·t/(n·R1·R2)]`` (lensmaker), rear principal
    point ``pp_rear = −f(n−1)t/(n·R1)`` from the rear vertex, front
    ``pp_front = −f(n−1)t/(n·R2)`` from the front vertex, ``bfl = f + pp_rear``,
    ``ffl = −f + pp_front``. Same sign convention as :func:`lens_system`; agrees
    with :func:`paraxial_trace` to machine precision (tested).
    """
    R1 = _radius(R1, "R1"); R2 = _radius(R2, "R2")
    t = _finite(thickness, "thickness", nonneg=True)
    n = _finite(index, "index", positive=True)
    if n < 1.0:
        raise ValueError("index must be >= 1")
    c1 = 0.0 if R1 == INF else 1.0 / R1
    c2 = 0.0 if R2 == INF else 1.0 / R2
    phi = (n - 1.0) * (c1 - c2 + (n - 1.0) * t * c1 * c2 / n)
    if abs(phi) < 1e-15:
        raise ValueError("the lens has zero power (afocal)")
    f = 1.0 / phi
    pp_rear = -f * (n - 1.0) * t * c1 / n
    pp_front = -f * (n - 1.0) * t * c2 / n
    return {"efl": f, "bfl": f + pp_rear, "ffl": -f + pp_front,
            "pp_front": pp_front, "pp_rear": pp_rear, "power_dpt": 1000.0 * phi}


# --------------------------------------------------------------------------- #
# real ray tracing
# --------------------------------------------------------------------------- #
def _rot(ax_deg, ay_deg):
    ax, ay = math.radians(ax_deg), math.radians(ay_deg)
    cx, sx, cy, sy = math.cos(ax), math.sin(ax), math.cos(ay), math.sin(ay)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    return Rx @ Ry


def _intersect_conic(P, D, c, k):
    """Distance t along D from P (in the surface frame, vertex at origin) to the conic.

    Surface: ``F = c(x²+y²+(1+k)z²) − 2z = 0``. Returns NaN where the ray misses.
    """
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    L, M, N = D[:, 0], D[:, 1], D[:, 2]
    if c == 0.0:                                          # flat: z = 0
        with np.errstate(divide="ignore", invalid="ignore"):
            t = -z / N
        t = np.where(np.abs(N) < 1e-15, np.nan, t)
        return t
    kk = 1.0 + k
    A = c * (L * L + M * M + kk * N * N)
    B = 2.0 * (c * (x * L + y * M + kk * z * N) - N)
    C = c * (x * x + y * y + kk * z * z) - 2.0 * z
    disc = B * B - 4.0 * A * C
    t = np.full(len(x), np.nan)
    ok = disc >= 0
    sq = np.sqrt(np.where(ok, disc, 0.0))
    lin = np.abs(A) < 1e-14
    with np.errstate(divide="ignore", invalid="ignore"):
        t_lin = -C / B
        t1 = (-B - sq) / (2.0 * A)
        t2 = (-B + sq) / (2.0 * A)
    # the intersection nearest the vertex plane (smallest |t|) is the physical one
    pick = np.where(np.abs(t1) <= np.abs(t2), t1, t2)
    t = np.where(lin, t_lin, pick)
    t = np.where(ok, t, np.nan)
    return t


def _sag(r2, c, k, asph=()):
    """Surface sag z(r²) of the conic plus the even aspheric polynomial (NaN outside the conic)."""
    r2 = np.asarray(r2, dtype=np.float64)
    if c == 0.0:
        z = np.zeros_like(r2)
    else:
        with np.errstate(invalid="ignore"):
            root = np.sqrt(1.0 - (1.0 + k) * c * c * r2)
            z = c * r2 / (1.0 + root)
    if asph:
        p = r2 * r2                                        # r^4
        for a in asph:
            z = z + a * p
            p = p * r2
    return z


def _dsag_dr2(r2, c, k, asph=()):
    """d z / d(r²) — the sag slope expressed per unit r² (so the normal is (−2x·s, −2y·s, 1))."""
    r2 = np.asarray(r2, dtype=np.float64)
    if c == 0.0:
        s = np.zeros_like(r2)
    else:
        with np.errstate(invalid="ignore", divide="ignore"):
            root = np.sqrt(1.0 - (1.0 + k) * c * c * r2)
            s = c / (2.0 * root)                            # d/d(r²) of c r²/(1+√(1−(1+k)c²r²)) = c/(2√·)
    if asph:
        p = r2                                             # d(r^4)/d(r²) = 2 r²
        m = 2.0
        for a in asph:
            s = s + a * m * p
            p = p * r2
            m += 1.0
    return s


def _intersect_asphere(P, D, c, k, asph, t0):
    """Newton refinement of the conic intersection *t0* onto the aspheric surface."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    L, M, N = D[:, 0], D[:, 1], D[:, 2]
    t = np.where(np.isfinite(t0), t0, 0.0)
    ok = np.ones(len(t), bool)
    for _ in range(40):
        xx, yy, zz = x + t * L, y + t * M, z + t * N
        r2 = xx * xx + yy * yy
        F = zz - _sag(r2, c, k, asph)
        s = _dsag_dr2(r2, c, k, asph)
        dF = N - 2.0 * s * (xx * L + yy * M)
        with np.errstate(invalid="ignore", divide="ignore"):
            step = F / dF
        step = np.where(np.isfinite(step), step, np.nan)
        t = t - step
        if np.all(np.abs(step[np.isfinite(step)]) < 1e-12) if np.any(np.isfinite(step)) else True:
            break
    xx, yy, zz = x + t * L, y + t * M, z + t * N
    r2 = xx * xx + yy * yy
    F = zz - _sag(r2, c, k, asph)
    ok &= np.isfinite(t) & np.isfinite(F) & (np.abs(F) < 1e-8)
    return np.where(ok, t, np.nan)


def _intersect_surface(P, D, c, k, asph=()):
    t = _intersect_conic(P, D, c, k)
    if asph:
        t = _intersect_asphere(P, D, c, k, asph, t)
    return t


def _surface_normal(Q, c, k, asph=()):
    if asph:
        r2 = Q[:, 0] ** 2 + Q[:, 1] ** 2
        s = _dsag_dr2(r2, c, k, asph)
        g = np.stack([-2.0 * s * Q[:, 0], -2.0 * s * Q[:, 1], np.ones(len(Q))], 1)
        return g / np.linalg.norm(g, axis=1, keepdims=True)
    if c == 0.0:
        n = np.zeros_like(Q); n[:, 2] = -1.0
        return n
    g = np.stack([2.0 * c * Q[:, 0], 2.0 * c * Q[:, 1], 2.0 * c * (1.0 + k) * Q[:, 2] - 2.0], 1)
    return g / np.linalg.norm(g, axis=1, keepdims=True)


def trace_rays(system, origins, directions, wavelength_um=None, image_mm=None):
    """Trace a bundle of real rays through the system to the image plane.

    *origins* (N,3) in object space (mm, z measured from the first vertex, so
    ``z < 0`` is in front of the lens), *directions* (N,3) unit vectors. Returns
    a dict: ``points`` (N, n_surf+2, 3) — the ray at the start, at every surface
    and at the image plane; ``dirs`` (N, n_surf+1, 3); ``opl`` (N,) optical path
    length from the origin to the image plane (mm, index-weighted); ``valid``
    (N,) bool — False where the ray missed a surface, was vignetted or was
    totally internally reflected (those entries are NaN); ``image_z`` (mm from
    the last vertex).
    """
    _check_system(system)
    wl = system["wavelength_um"] if wavelength_um is None else _finite(wavelength_um, "wavelength_um", positive=True)
    P = np.array(origins, dtype=np.float64)
    D = np.array(directions, dtype=np.float64)
    if P.ndim != 2 or P.shape[1] != 3 or D.shape != P.shape:
        raise ValueError("origins and directions must both be (N,3), got %s %s" % (P.shape, D.shape))
    if not (np.all(np.isfinite(P)) and np.all(np.isfinite(D))):
        raise ValueError("origins/directions must be finite")
    D = D / np.linalg.norm(D, axis=1, keepdims=True)
    surf = system["surfaces"]
    N = len(P)
    n_before = float(system["index_object"])
    z_vertex = 0.0
    dirn = 1.0                                             # +1 travelling +z, -1 after a mirror
    pts = [P.copy()]
    dirs = [D.copy()]
    opl = np.zeros(N)
    valid = np.ones(N, bool)
    for i, s in enumerate(surf):
        c = 0.0 if s["R"] == INF else 1.0 / s["R"]
        k = s["k"]
        Rm = _rot(*s["tilt"])
        off = np.array([s["decenter"][0], s["decenter"][1], z_vertex])
        Pl = (P - off) @ Rm                               # into the surface frame (R^T x)
        Dl = D @ Rm
        t = _intersect_surface(Pl, Dl, c, k, s["asph"])
        # a ray must move forward along its travel direction to reach the surface
        # (allow a tiny negative tolerance for rays already on the vertex plane)
        bad = ~np.isfinite(t) | (t < -1e-9)
        t = np.where(bad, np.nan, t)
        Q = Pl + t[:, None] * Dl
        if s["ap"] is not None:
            r = np.hypot(Q[:, 0], Q[:, 1])
            bad |= r > s["ap"] * (1.0 + 1e-12)
        nrm = _surface_normal(Q, c, k, s["asph"])
        # orient the normal against the incoming ray
        flip = np.sum(nrm * Dl, axis=1) > 0
        nrm[flip] *= -1.0
        cos_i = -np.sum(nrm * Dl, axis=1)
        if s["mirror"]:
            Dn = Dl - 2.0 * np.sum(nrm * Dl, axis=1)[:, None] * nrm
            n_after = n_before
            dirn = -dirn
        else:
            n_after = refractive_index(s["n"], wl)
            eta = n_before / n_after
            sin2_t = eta * eta * (1.0 - cos_i * cos_i)
            tir = sin2_t > 1.0
            bad |= tir
            cos_t = np.sqrt(np.clip(1.0 - sin2_t, 0.0, None))
            Dn = eta * Dl + (eta * cos_i - cos_t)[:, None] * nrm
        Dn = Dn / np.linalg.norm(Dn, axis=1, keepdims=True)
        opl += n_before * np.abs(t)
        # back to the global frame
        Pg = Q @ Rm.T + off
        Dg = Dn @ Rm.T
        valid &= ~bad
        Pg[~valid] = np.nan; Dg[~valid] = np.nan
        pts.append(Pg); dirs.append(Dg)
        P, D = Pg, Dg
        n_before = n_after
        if s["t"] is not None:
            z_vertex = z_vertex + dirn * s["t"]
        # transfer to the next vertex plane happens inside the next intersection
        # (the ray is intersected from its current point), so nothing to do here.
    # image plane
    z_last = z_vertex if surf[-1]["t"] is None else z_vertex - dirn * surf[-1]["t"]
    if image_mm is None:
        image_mm = system["image_mm"]
    if image_mm is None:
        if surf[-1]["t"] is not None:
            image_mm = surf[-1]["t"]
        else:
            image_mm = paraxial_trace(system)["bfl"]
    z_img = z_last + dirn * image_mm
    with np.errstate(divide="ignore", invalid="ignore"):
        tt = (z_img - P[:, 2]) / D[:, 2]
    Q = P + tt[:, None] * D
    opl += n_before * np.abs(tt)
    valid &= np.isfinite(tt)
    Q[~valid] = np.nan
    pts.append(Q)
    return {"points": np.stack(pts, 1), "dirs": np.stack(dirs, 1), "opl": opl,
            "valid": valid, "image_z": float(image_mm), "z_image_global": float(z_img),
            "n_image": float(n_before)}


def _pupil_grid(rings=6, kind="hexapolar"):
    """Normalised pupil coordinates (px, py) in the unit disk."""
    if kind == "grid":
        m = int(rings) * 2 + 1
        g = np.linspace(-1.0, 1.0, m)
        px, py = np.meshgrid(g, g)
        px, py = px.ravel(), py.ravel()
        keep = px * px + py * py <= 1.0 + 1e-12
        return px[keep], py[keep]
    pts = [(0.0, 0.0)]
    for r in range(1, int(rings) + 1):
        rad = r / float(rings)
        for j in range(6 * r):
            a = 2.0 * math.pi * j / (6 * r)
            pts.append((rad * math.cos(a), rad * math.sin(a)))
    a = np.array(pts)
    return a[:, 0], a[:, 1]


def _launch(system, px, py, field, para, pupil_fill=1.0):
    """Object-space origins/directions for normalised pupil coords at one field."""
    obj = system["object_mm"]
    ep_z, ep_r = para["ep_position"], para["ep_radius"]
    if not math.isfinite(ep_r):
        raise ValueError("the entrance pupil is not finite; check the stop")
    X = px * ep_r * pupil_fill
    Y = py * ep_r * pupil_fill
    if obj == INF:
        th = math.radians(field)
        D = np.tile([0.0, math.sin(th), math.cos(th)], (len(px), 1))
        # ray through the entrance-pupil point (X, Y, ep_z); start 1 mm (or more) in front
        z0 = min(ep_z, 0.0) - max(10.0, abs(ep_z) + 1.0)
        s = (z0 - ep_z) / D[:, 2]
        P = np.stack([X, Y, np.full(len(px), ep_z)], 1) + s[:, None] * D
        # common wavefront: optical path measured from the plane through the origin
        # normal to D, so all rays of the collimated beam start in phase
        opl0 = system["index_object"] * np.sum(P * D, axis=1)
    else:
        P0 = np.array([0.0, field, -obj])
        target = np.stack([X, Y, np.full(len(px), ep_z)], 1)
        D = target - P0
        D = D / np.linalg.norm(D, axis=1, keepdims=True)
        P = np.tile(P0, (len(px), 1))
        opl0 = np.zeros(len(px))
    return P, D, opl0


def spot_diagram(system, field=None, rings=8, wavelength_um=None, image_mm=None):
    """Transverse ray intersections on the image plane for one field point.

    Returns ``(N,2)`` ``(x, y)`` positions in mm relative to the **chief ray**
    (so the pattern is centred; use ``ray_bundle`` for absolute positions), and
    stores the statistics on the array as attributes via :func:`spot_stats`.
    Rays that miss / vignette are dropped. Pupil: hexapolar, ``rings`` rings.
    """
    b = ray_bundle(system, field=field, rings=rings, wavelength_um=wavelength_um, image_mm=image_mm)
    xy = b["image_xy"][b["valid"]] - b["chief_xy"]
    return xy


def spot_stats(system, field=None, rings=8, wavelength_um=None, image_mm=None, pupil_fill=1.0):
    """RMS / geometric spot radius (mm) and centroid for one field point (``table``).

    *pupil_fill* < 1 samples the pupil only up to that fraction of its radius:
    with the stop on a surface, the outermost rays sit exactly on the aperture
    edge and any perturbation (tilt, decenter) vignettes half of them, which
    makes the RMS *drop* — :func:`tolerance_analysis` uses 0.99 for that reason.
    ``n_vignetted`` reports how many rays were lost either way.
    """
    b = ray_bundle(system, field=field, rings=rings, wavelength_um=wavelength_um, image_mm=image_mm, pupil_fill=pupil_fill)
    xy = b["image_xy"][b["valid"]]
    if len(xy) == 0:
        raise ValueError("no ray reached the image plane")
    cen = xy.mean(0)
    d = xy - cen
    r = np.hypot(d[:, 0], d[:, 1])
    return {"rms_radius": float(np.sqrt(np.mean(r * r))), "geo_radius": float(r.max()),
            "centroid_x": float(cen[0]), "centroid_y": float(cen[1]),
            "chief_x": float(b["chief_xy"][0]), "chief_y": float(b["chief_xy"][1]),
            "n_rays": int(len(xy)), "n_vignetted": int((~b["valid"]).sum()),
            "image_z": b["image_z"]}


def ray_bundle(system, field=None, rings=8, wavelength_um=None, image_mm=None, kind="hexapolar", pupil_fill=1.0):
    """Trace a pupil-filling bundle at one field; returns the raw trace plus
    ``image_xy`` (N,2), ``chief_xy`` (2,), ``pupil`` (N,2) normalised coordinates
    and ``opl0`` (start-of-ray optical path offsets)."""
    _check_system(system)
    field = system["field"] if field is None else _finite(field, "field")
    para = paraxial_trace(system)
    px, py = _pupil_grid(rings, kind)
    P, D, opl0 = _launch(system, px, py, field, para, pupil_fill)
    tr = trace_rays(system, P, D, wavelength_um=wavelength_um, image_mm=image_mm)
    img = tr["points"][:, -1, :2]
    # chief ray = pupil centre (index 0 of the hexapolar grid; for "grid" the nearest)
    ic = int(np.argmin(px * px + py * py))
    tr.update({"image_xy": img, "chief_xy": img[ic].copy(), "pupil": np.stack([px, py], 1),
               "opl0": opl0, "chief_index": ic, "para": para, "field": field})
    return tr


def ray_fan(system, field=None, n=21, axis="y", wavelength_um=None, image_mm=None):
    """Transverse ray aberration along one pupil diameter (``pairs``).

    Returns ``(n,2)``: column 0 the normalised pupil coordinate (−1…1) along
    *axis* (``"y"`` tangential, ``"x"`` sagittal), column 1 the image-plane
    displacement (mm) of that ray from the chief ray along the same axis.
    The classic "ray fan plot"; NaN where a ray is vignetted.
    """
    _check_system(system)
    field = system["field"] if field is None else _finite(field, "field")
    para = paraxial_trace(system)
    q = np.linspace(-1.0, 1.0, int(n))
    if axis == "y":
        px, py = np.zeros_like(q), q
    elif axis == "x":
        px, py = q, np.zeros_like(q)
    else:
        raise ValueError("axis must be 'x' or 'y'")
    px = np.append(px, 0.0); py = np.append(py, 0.0)    # chief ray last
    P, D, _ = _launch(system, px, py, field, para)
    tr = trace_rays(system, P, D, wavelength_um=wavelength_um, image_mm=image_mm)
    img = tr["points"][:, -1, :2]
    chief = img[-1]
    comp = 1 if axis == "y" else 0
    return np.stack([q, img[:-1, comp] - chief[comp]], 1)


# --------------------------------------------------------------------------- #
# wavefront / OPD
# --------------------------------------------------------------------------- #
def opd_map(system, field=None, size=64, wavelength_um=None, image_mm=None, fill=0.0):
    """Optical path difference over the exit pupil, in waves (``image2d``).

    The OPD of each ray is the chief ray's optical path from a common object-space
    wavefront to the **exit-pupil reference sphere** (centred on the chief
    ray's image point, passing through the paraxial exit pupil on axis) minus
    the ray's own, divided by the wavelength (Welford's sign: an undercorrected
    spherical singlet gives ``W = +W040·ρ⁴`` with ``W040 = S_I/8``). The map is sampled on a ``size × size`` grid over
    the unit pupil (row = +y down the array, column = +x); points outside the
    pupil or vignetted are set to *fill* (default 0 so the array is finite —
    pass ``fill=np.nan`` to see the pupil boundary). The pupil mask is available
    from :func:`opd_samples`.

    Feed the map to ``match3d.fit_zernike`` (coefficients in waves) and then to
    ``optics.wavefront_stats`` for RMS / PV / Strehl. On a stigmatic system
    (an on-axis paraboloid mirror) the map is zero to machine precision; a pure
    image-plane defocus produces the textbook ``W020·ρ²``; for a spherical
    singlet the Zernike (4,0) term reproduces the Seidel ``S_I/8`` at small
    aperture (all tested).
    """
    px, py, w, valid = opd_samples(system, field=field, size=size, wavelength_um=wavelength_um, image_mm=image_mm)
    out = np.full((size, size), float(fill))
    m = size
    ix = np.clip(np.round((px + 1.0) / 2.0 * (m - 1)).astype(int), 0, m - 1)
    iy = np.clip(np.round((py + 1.0) / 2.0 * (m - 1)).astype(int), 0, m - 1)
    out[iy[valid], ix[valid]] = w[valid]
    return out


def opd_samples(system, field=None, size=64, wavelength_um=None, image_mm=None):
    """OPD (waves) at grid pupil samples: returns ``(px, py, opd, valid)``."""
    _check_system(system)
    field = system["field"] if field is None else _finite(field, "field")
    wl = system["wavelength_um"] if wavelength_um is None else _finite(wavelength_um, "wavelength_um", positive=True)
    para = paraxial_trace(system)
    g = np.linspace(-1.0, 1.0, int(size))
    gx, gy = np.meshgrid(g, g)
    px, py = gx.ravel(), gy.ravel()
    inside = px * px + py * py <= 1.0 + 1e-12
    px_a = np.append(px, 0.0); py_a = np.append(py, 0.0)    # chief last
    P, D, opl0 = _launch(system, px_a, py_a, field, para)
    tr = trace_rays(system, P, D, wavelength_um=wl, image_mm=image_mm)
    pts, dirs = tr["points"], tr["dirs"]
    n_img = tr["n_image"]
    # reference sphere: centre = chief ray image point, through the exit pupil (on axis)
    chief_img = pts[-1, -1]
    surf = system["surfaces"]
    # exit pupil global z: last vertex + xp_position (along the final travel direction)
    dirn = 1.0 if dirs[-1, -1, 2] >= 0 else -1.0             # chief ray travel direction in image space
    z_last_vertex = tr["z_image_global"] - dirn * tr["image_z"]
    z_xp = z_last_vertex + dirn * para["xp_position"]
    C = chief_img
    Rref = abs(C[2] - z_xp)
    if not math.isfinite(Rref) or Rref < 1e-9:
        raise ValueError("exit pupil coincides with the image plane; OPD reference sphere undefined")
    # each ray in image space: its point after the last surface and its direction
    Pl = pts[:, -2, :]
    Dl = dirs[:, -1, :]
    # optical path up to the last surface (opl total minus the last leg)
    last_leg = np.linalg.norm(pts[:, -1, :] - Pl, axis=1) * n_img
    opl_last = tr["opl"] - last_leg + opl0
    # intersect with the sphere |Pl + s Dl - C|^2 = Rref^2
    oc = Pl - C
    b = np.sum(oc * Dl, axis=1)
    cc = np.sum(oc * oc, axis=1) - Rref * Rref
    disc = b * b - cc
    ok = disc >= 0
    sq = np.sqrt(np.where(ok, disc, 0.0))
    s1, s2 = -b - sq, -b + sq
    # choose the root on the exit-pupil side (closest in z to the pupil plane)
    z1 = Pl[:, 2] + s1 * Dl[:, 2]; z2 = Pl[:, 2] + s2 * Dl[:, 2]
    s = np.where(np.abs(z1 - z_xp) <= np.abs(z2 - z_xp), s1, s2)
    opl_ref = opl_last + n_img * s
    valid = tr["valid"] & ok
    # Welford sign: W = (chief path) - (ray path) on the reference sphere, so that an
    # undercorrected spherical singlet has W040 = +S_I/8 (checked in the tests)
    w = (opl_ref[-1] - opl_ref) / (wl * 1e-3)              # mm -> waves (wl in µm)
    w = np.where(valid, w, np.nan)
    return px, py, w[:-1], (valid[:-1] & inside)


def wavefront_from_opd(system, field=None, size=64, n_max=6, wavelength_um=None, image_mm=None):
    """OPD map → Zernike coefficients (waves) → RMS / PV / Strehl, in one call (``table``).

    Convenience chain: :func:`opd_map` → ``match3d.fit_zernike`` →
    ``optics.wavefront_stats``. Returns the stats dict extended with
    ``zernike`` (``{(n, m): coef}``), ``rms_opd_direct`` (RMS of the sampled OPD,
    independent of the fit) and ``pv_opd_direct``.
    """
    import match3d
    import optics
    px, py, w, valid = opd_samples(system, field=field, size=size, wavelength_um=wavelength_um, image_mm=image_mm)
    if valid.sum() < 16:
        raise ValueError("too few valid pupil samples for a wavefront fit")
    disk = np.zeros((size, size))
    m = size
    ix = np.clip(np.round((px + 1.0) / 2.0 * (m - 1)).astype(int), 0, m - 1)
    iy = np.clip(np.round((py + 1.0) / 2.0 * (m - 1)).astype(int), 0, m - 1)
    disk[iy[valid], ix[valid]] = w[valid]
    coeffs = match3d.fit_zernike(disk, n_max=n_max)
    stats = optics.wavefront_stats(coeffs)
    wv = w[valid]
    stats = dict(stats)
    stats["zernike"] = coeffs
    stats["rms_opd_direct"] = float(np.sqrt(np.mean((wv - wv.mean()) ** 2)))
    stats["pv_opd_direct"] = float(wv.max() - wv.min())
    return stats


# --------------------------------------------------------------------------- #
# Seidel sums
# --------------------------------------------------------------------------- #
def seidel_coefficients(system, field=None):
    """Third-order (Seidel) aberration sums per surface and total (``table``).

    Uses the paraxial marginal ray (through the stop edge) and chief ray (through
    the stop centre) at the system's default field (or *field*), with Welford's
    refraction-invariant form: ``A = n(yc + u)``, ``Δ(u/n)``, Lagrange invariant
    ``H = n(ūy − uȳ)``::

        S_I   = −Σ A² y Δ(u/n)            spherical
        S_II  = −Σ A Ā y Δ(u/n)           coma
        S_III = −Σ Ā² y Δ(u/n)            astigmatism
        S_IV  = −Σ H² c Δ(1/n)            Petzval (field curvature)
        S_V   = −Σ (Ā/A)[Ā² y Δ(u/n) + H² c Δ(1/n)]   distortion
        C_L   = −Σ A y Δ(δn/n),  C_T = −Σ Ā y Δ(δn/n)  axial / lateral colour

    plus the aspheric deformation contribution ``8 G (n'−n) y⁴`` with ``G = k c³/8
    + A4`` (conic and fourth-order coefficient) to ``S_I`` (and its ``ȳ/y``
    powers to S_II, S_III, S_V); higher aspheric orders are fifth order and
    above and do not enter the Seidel sums. Sums are in millimetres of wavefront times 8:
    the third-order wavefront at the pupil edge is ``W040 = S_I/8``,
    ``W131 = S_II/2``, ``W222 = S_III/2``, ``W220 = (S_III + S_IV)/4``,
    ``W311 = S_V/2`` (Welford's normalisation). ``waves`` gives the same
    numbers divided by the wavelength. Checked against the exact ray-traced OPD
    at small aperture (``tests/test_raytrace.py``).
    """
    _check_system(system)
    field = system["field"] if field is None else _finite(field, "field")
    para = paraxial_trace(system)
    c, t, n = _paraxial_model(system)
    ym = np.array(para["marginal"]["y"]); um_after = np.array(para["marginal"]["u"])
    # the chief ray stored in para is per unit field; scale to the requested field
    if system["object_mm"] == INF:
        scale = math.tan(math.radians(field))
    else:
        scale = field
    yc = np.array(para["chief"]["y"]) * scale; uc_after = np.array(para["chief"]["u"]) * scale
    # slopes BEFORE each surface
    if system["object_mm"] == INF:
        um0, uc0 = 0.0, scale                                # collimated marginal; chief at the field angle
    else:
        obj = system["object_mm"]
        um0 = ym[0] / obj                                    # marginal ray from the axial object point
        uc0 = (yc[0] - field) / obj                          # chief ray from object height `field`
    um_before = np.concatenate([[um0], um_after[:-1]])
    uc_before = np.concatenate([[uc0], uc_after[:-1]])
    surf = system["surfaces"]
    H = n[0] * (uc_before[0] * ym[0] - um_before[0] * yc[0])
    rows = []
    tot = np.zeros(7)
    for i in range(len(c)):
        A = n[i] * (ym[i] * c[i] + um_before[i])
        Ab = n[i] * (yc[i] * c[i] + uc_before[i])
        dun = um_after[i] / n[i + 1] - um_before[i] / n[i]
        d1n = 1.0 / n[i + 1] - 1.0 / n[i]
        dn_after = surf[i]["dn"] if not surf[i]["mirror"] else 0.0
        dn_before = surf[i - 1]["dn"] if i > 0 and not surf[i - 1]["mirror"] else 0.0
        ddn = dn_after / n[i + 1] - dn_before / n[i]
        SI = -A * A * ym[i] * dun
        SII = -A * Ab * ym[i] * dun
        SIII = -Ab * Ab * ym[i] * dun
        SIV = -H * H * c[i] * d1n
        if abs(A) > 1e-12:
            SV = -(Ab / A) * (Ab * Ab * ym[i] * dun + H * H * c[i] * d1n)
        else:
            SV = 0.0
        CL = -A * ym[i] * ddn
        CT = -Ab * ym[i] * ddn
        kk = surf[i]["k"]
        A4 = surf[i]["asph"][0] if surf[i]["asph"] else 0.0
        G = kk * c[i] ** 3 / 8.0 + A4
        if G != 0.0 and abs(ym[i]) > 0:
            dS = 8.0 * G * (n[i + 1] - n[i]) * ym[i] ** 4
            ratio = yc[i] / ym[i]
            SI += dS; SII += dS * ratio; SIII += dS * ratio ** 2; SV += dS * ratio ** 3
        row = np.array([SI, SII, SIII, SIV, SV, CL, CT])
        tot += row
        rows.append({"surface": i, "S_I": float(SI), "S_II": float(SII), "S_III": float(SIII),
                     "S_IV": float(SIV), "S_V": float(SV), "C_L": float(CL), "C_T": float(CT)})
    wl_mm = system["wavelength_um"] * 1e-3
    keys = ["S_I", "S_II", "S_III", "S_IV", "S_V", "C_L", "C_T"]
    total = {k: float(v) for k, v in zip(keys, tot)}
    return {"per_surface": rows, "total": total,
            "wavefront_mm": {"W040": total["S_I"] / 8, "W131": total["S_II"] / 2,
                             "W222": total["S_III"] / 2, "W220": (total["S_III"] + total["S_IV"]) / 4,
                             "W311": total["S_V"] / 2},
            "waves": {k: float(v) / wl_mm for k, v in zip(keys, tot)},
            "lagrange": float(H), "field": field,
            "petzval_radius": float(-1.0 / (total["S_IV"] / (H * H))) if H != 0 and total["S_IV"] != 0 else INF}


# --------------------------------------------------------------------------- #
# tolerances
# --------------------------------------------------------------------------- #
def _perturbed(system, rng, tol):
    surf = []
    for s in system["surfaces"]:
        q = dict(s)
        if tol.get("radius_pct", 0) and s["R"] != INF:
            q["R"] = s["R"] * (1.0 + rng.uniform(-1, 1) * tol["radius_pct"] / 100.0)
        if tol.get("thickness_mm", 0) and s["t"] is not None:
            q["t"] = max(0.0, s["t"] + rng.uniform(-1, 1) * tol["thickness_mm"])
        if tol.get("index", 0) and not s["mirror"]:
            q["n"] = _index_offset(s["n"], rng.uniform(-1, 1) * tol["index"])
        if tol.get("decenter_mm", 0):
            q["decenter"] = (s["decenter"][0] + rng.uniform(-1, 1) * tol["decenter_mm"],
                             s["decenter"][1] + rng.uniform(-1, 1) * tol["decenter_mm"])
        if tol.get("tilt_deg", 0):
            q["tilt"] = (s["tilt"][0] + rng.uniform(-1, 1) * tol["tilt_deg"],
                         s["tilt"][1] + rng.uniform(-1, 1) * tol["tilt_deg"])
        surf.append(q)
    return lens_system(surf, stop=system["stop"], object_mm=system["object_mm"],
                       wavelength_um=system["wavelength_um"], index_object=system["index_object"],
                       image_mm=system["image_mm"], field=system["field"])


def tolerance_analysis(system, tolerances=None, trials=100, seed=0, field=None, rings=6):
    """Monte-Carlo manufacturing tolerances + per-parameter sensitivities (``table``).

    *tolerances*: ``{"radius_pct": 0.5, "thickness_mm": 0.05, "index": 0.001,
    "decenter_mm": 0.02, "tilt_deg": 0.05}`` — each perturbation is drawn
    uniformly in ``±tol`` for every surface independently, *trials* times.
    Returns the distribution of ``efl`` and ``rms_spot`` (mean, std, p5, p95,
    worst), the nominal values, and ``sensitivity``: the change of EFL and RMS
    spot per **one full tolerance** of each parameter on each surface (central
    finite difference), so you can see which surface's radius or tilt drives
    the yield. Deterministic for a given *seed*. Spots are sampled to 99 % of the
    pupil radius so that edge vignetting by a tilt cannot masquerade as an
    improvement (``n_vignetted`` would otherwise jump on the nominal design).
    """
    _check_system(system)
    tol = {"radius_pct": 0.5, "thickness_mm": 0.05, "index": 0.001, "decenter_mm": 0.02, "tilt_deg": 0.05}
    if tolerances:
        for k, v in tolerances.items():
            if k not in tol:
                raise ValueError("unknown tolerance %r (choose from %s)" % (k, sorted(tol)))
            tol[k] = _finite(v, k, nonneg=True)
    trials = int(trials)
    if trials < 1:
        raise ValueError("trials must be >= 1")
    rng = np.random.default_rng(int(seed))
    field = system["field"] if field is None else _finite(field, "field")

    def metrics(sys_):
        p = paraxial_trace(sys_)
        st = spot_stats(sys_, field=field, rings=rings, pupil_fill=0.99)   # see spot_stats: edge vignetting
        return p["efl"], st["rms_radius"]

    efl0, rms0 = metrics(system)
    efls, rmss = [], []
    n_fail = 0
    for _ in range(trials):
        try:
            e, r = metrics(_perturbed(system, rng, tol))
            efls.append(e); rmss.append(r)
        except (ValueError, FloatingPointError):
            n_fail += 1
    efls = np.array(efls); rmss = np.array(rmss)

    def dist(a):
        if len(a) == 0:
            return {"mean": INF, "std": INF, "p5": INF, "p95": INF, "worst": INF}
        return {"mean": float(a.mean()), "std": float(a.std()), "p5": float(np.percentile(a, 5)),
                "p95": float(np.percentile(a, 95)), "worst": float(a.max())}
    # sensitivities: one parameter, one surface, +/- one tolerance
    sens = []
    for i, s in enumerate(system["surfaces"]):
        for key, tname in (("R", "radius_pct"), ("t", "thickness_mm"), ("n", "index"),
                           ("decenter", "decenter_mm"), ("tilt", "tilt_deg")):
            if tol[tname] == 0:
                continue
            if key == "R" and s["R"] == INF:
                continue
            if key == "t" and s["t"] is None:
                continue
            if key == "n" and s["mirror"]:
                continue
            vals = []
            for sgn in (-1.0, 1.0):
                surf = [dict(q) for q in system["surfaces"]]
                q = surf[i]
                if key == "R":
                    q["R"] = s["R"] * (1.0 + sgn * tol[tname] / 100.0)
                elif key == "t":
                    q["t"] = max(0.0, s["t"] + sgn * tol[tname])
                elif key == "n":
                    q["n"] = _index_offset(s["n"], sgn * tol[tname])
                elif key == "decenter":
                    q["decenter"] = (s["decenter"][0], s["decenter"][1] + sgn * tol[tname])
                else:
                    q["tilt"] = (s["tilt"][0] + sgn * tol[tname], s["tilt"][1])
                try:
                    sys_ = lens_system(surf, stop=system["stop"], object_mm=system["object_mm"],
                                       wavelength_um=system["wavelength_um"], index_object=system["index_object"],
                                       image_mm=system["image_mm"], field=system["field"])
                    vals.append(metrics(sys_))
                except ValueError:
                    vals.append((np.nan, np.nan))
            d_efl = (vals[1][0] - vals[0][0]) / 2.0
            d_rms = (vals[1][1] - vals[0][1]) / 2.0
            sens.append({"surface": i, "parameter": key, "tolerance": tol[tname],
                         "d_efl": float(d_efl), "d_rms_spot": float(d_rms)})
    sens.sort(key=lambda r: -abs(r["d_rms_spot"]) if math.isfinite(r["d_rms_spot"]) else 0.0)
    return {"nominal": {"efl": efl0, "rms_spot": rms0}, "efl": dist(efls), "rms_spot": dist(rmss),
            "trials": trials, "failed": n_fail, "tolerances": tol, "sensitivity": sens, "seed": int(seed)}


# --------------------------------------------------------------------------- #
# chromatic behaviour
# --------------------------------------------------------------------------- #
def with_wavelength(system, wavelength_um):
    """The same prescription evaluated at another wavelength (indices re-resolved)."""
    _check_system(system)
    return lens_system([dict(s) for s in system["surfaces"]], stop=system["stop"],
                       object_mm=system["object_mm"], wavelength_um=wavelength_um,
                       index_object=system["index_object"], image_mm=system["image_mm"],
                       field=system["field"])


def chromatic_shift(system, wavelengths=(WL_F, WL_D, WL_C), field=None, rings=6):
    """Focal shift, image-height shift and spot size versus wavelength (``table``).

    Re-evaluates the prescription at each wavelength (real dispersion for
    catalogue / Sellmeier glasses, the Cauchy fit for ``(nd, vd)`` media): per
    wavelength ``efl``, ``bfl``, the chief-ray image height at *field*, and the
    RMS spot radius **on the reference (system-wavelength) image plane** — the
    number a polychromatic sensor sees. Summaries: ``axial_color`` = BFL(first)
    − BFL(last), ``lateral_color`` = height(first) − height(last), and
    ``rms_polychromatic`` = RMS of all rays of all wavelengths pooled about
    their common centroid. Needs at least two wavelengths.
    """
    _check_system(system)
    wls = [_finite(w, "wavelength", positive=True) for w in (wavelengths if isinstance(wavelengths, (list, tuple)) else [wavelengths])]
    if len(wls) < 2:
        raise ValueError("chromatic_shift needs at least two wavelengths")
    field = system["field"] if field is None else _finite(field, "field")
    ref = paraxial_trace(system)
    img_ref = system["image_mm"] if system["image_mm"] is not None else \
        (system["surfaces"][-1]["t"] if system["surfaces"][-1]["t"] is not None else ref["bfl"])
    rows = []
    pool = []
    for wl in wls:
        sw = with_wavelength(system, wl)
        p = paraxial_trace(sw)
        b = ray_bundle(sw, field=field, rings=rings, image_mm=img_ref)
        xy = b["image_xy"][b["valid"]]
        if len(xy) == 0:
            raise ValueError("no ray reached the image plane at %.4g um" % wl)
        cen = xy.mean(0)
        d = xy - cen
        rows.append({"wavelength_um": wl, "efl": p["efl"], "bfl": p["bfl"],
                     "chief_height": float(b["chief_xy"][1]),
                     "rms_spot": float(np.sqrt(np.mean(d[:, 0] ** 2 + d[:, 1] ** 2))),
                     "n_rays": int(len(xy))})
        pool.append(xy)
    allxy = np.concatenate(pool, 0)
    cen = allxy.mean(0)
    d = allxy - cen
    return {"per_wavelength": rows,
            "axial_color": rows[0]["bfl"] - rows[-1]["bfl"],
            "lateral_color": rows[0]["chief_height"] - rows[-1]["chief_height"],
            "efl_range": max(r["efl"] for r in rows) - min(r["efl"] for r in rows),
            "rms_polychromatic": float(np.sqrt(np.mean(d[:, 0] ** 2 + d[:, 1] ** 2))),
            "reference_image_mm": float(img_ref), "field": field}


# --------------------------------------------------------------------------- #
# convenience: a few classic prescriptions
# --------------------------------------------------------------------------- #
def example_system(name="singlet"):
    """A named example: ``"singlet"`` (plano-convex BK7, f≈100), ``"doublet"``
    (a cemented achromat, BK7/SF2, f≈100), ``"paraboloid"`` (f/2 paraboloid
    mirror — stigmatic on axis), ``"sphere_mirror"`` (same radius, spherical),
    ``"asphere"`` (plano-hyperbolic N-BK7 singlet, flat toward the object, exit
    conic ``k = −n²`` — Descartes' stigmatic lens, f≈100 at f/4),
    ``"catalog_doublet"`` (the doublet with real N-BK7 / N-SF2 Sellmeier glass)."""
    if name == "singlet":
        return lens_system()
    if name == "asphere":
        n = refractive_index("N-BK7")
        return lens_system([{"R": INF, "t": 5.0, "n": "N-BK7", "ap": 12.5},
                            {"R": -(n - 1.0) * 100.0, "t": None, "n": 1.0, "k": -n * n}], stop=0)
    if name == "catalog_doublet":
        return lens_system([{"R": 61.47, "t": 6.0, "n": "N-BK7", "ap": 12.5},
                            {"R": -44.64, "t": 2.5, "n": "N-SF2"},
                            {"R": -129.94, "t": None, "n": 1.0}], stop=0)
    if name == "doublet":
        return lens_system([{"R": 61.47, "t": 6.0, "n": (1.5168, 64.17), "ap": 12.5},
                            {"R": -44.64, "t": 2.5, "n": (1.6477, 33.85)},
                            {"R": -129.94, "t": None, "n": 1.0}], stop=0)
    if name == "paraboloid":
        return lens_system([{"R": -200.0, "t": None, "n": 1.0, "k": -1.0, "ap": 25.0, "mirror": True}], stop=0)
    if name == "sphere_mirror":
        return lens_system([{"R": -200.0, "t": None, "n": 1.0, "k": 0.0, "ap": 25.0, "mirror": True}], stop=0)
    raise ValueError("unknown example %r" % name)
