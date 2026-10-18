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
  ``decenter`` / ``tilt`` perturb **that surface only** — the axis never folds
  (a tilted mirror is a tolerance, not a fold: rays that end up running parallel
  to the image plane are reported invalid). Fold mirrors, coordinate breaks,
  beamsplitters and tilted plates live in ``raytrace3d``, whose traces of a
  coaxial prescription equal this module's to 1e-12.
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
#: 像面に届いたと見なす、光軸方向の方向余弦の下限(これ以下は像面とほぼ平行 = 89.94° 超)。raytrace3d と同じ値。
_MIN_DZ = 1e-3


# --------------------------------------------------------------------------- #
# validation helpers
# --------------------------------------------------------------------------- #
def _finite(x, name, positive=False, nonneg=False):
    if isinstance(x, (bool, np.bool_, str, bytes)) or x is None:
        raise ValueError("%s must be a real number, got %r" % (name, x))
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
    if isinstance(x, (bool, np.bool_, str, bytes)):
        raise ValueError("%s must be a number or 'inf', got %r" % (name, x))
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
#: constants (Schott optical glass data sheets; every entry was checked digit by
#: digit against the refractiveindex.info database mirror, specs/schott/optical,
#: on 2026-09-03); fused silica is Malitson (1965), CaF2 Malitson (1963),
#: sapphire (ordinary ray) Malitson & Dodge (1972). ``tests/test_raytrace.py`` checks every entry's d-line index
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
    "N-SF5":   (1.52481889, 0.187085527, 1.42729015, 0.011254756, 0.0588995392, 129.141675),
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


#: materials の表のうち、レンズの媒質として引ける部類(金属・半導体・膜は引かない ——
#: 可視で吸収が強く、実数の屈折率で光線を曲げると嘘になる)。
_MATERIAL_CLASSES = ("glass", "crystal", "polymer", "liquid")


def _material_names():
    """materials の透過材の名前(手元の 20 種と重なるものを除く)。"""
    import materials as _mat
    return sorted(k for k in _mat.MATERIALS
                  if _mat._record(k, "glass_catalog")["class"] in _MATERIAL_CLASSES and k not in _SELLMEIER)


def _material_key(name):
    """*name* が materials の透過材なら正規名、そうでなければ None。"""
    import materials as _mat
    try:
        rec = _mat._record(name, "glass_catalog")
    except ValueError:
        return None
    if rec["class"] not in _MATERIAL_CLASSES:
        raise ValueError("%r is a %s in the material table, not a lens medium (classes: %s)"
                         % (name, rec["class"], ", ".join(_MATERIAL_CLASSES)))
    return rec["name"]


def _catalog_key(name):
    if not isinstance(name, str):
        raise ValueError("a glass name must be a string, got %r" % type(name).__name__)
    key = "_".join(name.strip().upper().split())
    key = _GLASS_ALIASES.get(key, key)
    if key not in _SELLMEIER:
        mk = _material_key(name)
        if mk is not None and mk in _SELLMEIER:
            return mk
        if mk is not None:
            return "material:" + mk
        raise ValueError("unknown glass %r (catalogue: %s, plus the transparent materials of "
                         "materials.material_table())" % (name, ", ".join(sorted(_SELLMEIER))))
    return key


def _material_medium(key):
    """materials のレコードを、raytrace の媒質 dict にする(``{"name", "material", "nd", "vd",
    "offset", "range_um"}``)。nd / vd は表から**評価した値**で、F/d/C 線が表の範囲外なら None。"""
    import materials as _mat
    rec = _mat._record(key, "glass_catalog")
    ivs = _mat._intervals([d for d in rec["datasets"] if d["type"] in ("formula", "nk", "n")])
    g = {"name": rec["name"], "material": rec["name"], "offset": 0.0,
         "range_um": (float(min(a for a, _ in ivs)), float(max(b for _, b in ivs))),
         "nd": None, "vd": None}
    try:
        n = _mat._nk(rec, [WL_F, WL_D, WL_C], "glass_catalog")[0]
    except ValueError:
        return g
    g["nd"] = float(n[1])
    g["vd"] = float((n[1] - 1.0) / (n[0] - n[2])) if n[0] > n[2] else None
    return g


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
    if not (nf > nc >= 1.0):
        raise ValueError("Sellmeier constants give n < 1 or anomalous dispersion in the visible (n_F <= n_C)")
    g["nd"] = nd
    g["vd"] = (nd - 1.0) / (nf - nc)
    return g


def glass_catalog(name=None):
    """A catalogue glass by name (``table``), or the list of names when *name* is None.

    Names: 17 glasses from a public glass catalogue (coefficients as published;
    ``glass_catalog()`` lists their keys) and the crystals ``"SILICA"`` (fused),
    ``"CAF2"``, ``"SAPPHIRE"`` (ordinary ray); case-insensitive, a few aliases (``"BK7"``, ``"SF11"``,
    ``"fused_silica"``, ``"fluorite"``). Any surface's ``n`` may simply be the
    name — ``lens_system`` resolves it. The returned dict is the
    :func:`sellmeier` form with the evaluated ``nd`` / ``vd``.

    Every other transparent material of the shared material table
    (``materials.material_table()``: the other glasses of four makers, crystals
    such as ``"ZNSE"`` / ``"YAG"``, the plastics ``"PMMA"`` / ``"POLYCARBONATE"``
    and ``"WATER"``) resolves too, as ``{"name", "material", "nd", "vd",
    "offset", "range_um"}``: the index then comes from that table, inside the
    table's own wavelength range (outside it is a ValueError, never an
    extrapolation). The listing (*name* None) gives both, the 20 above first.
    Metals, semiconductors and films are refused — a real index would bend rays
    through an absorber.
    """
    if name is None:
        return sorted(_SELLMEIER) + _material_names()
    key = _catalog_key(name)
    if key.startswith("material:"):
        return _material_medium(key[len("material:"):])
    g = sellmeier(*_SELLMEIER[key], name=key)
    return g


def refractive_index(medium, wavelength_um=WL_D):
    """Index of *medium* at *wavelength_um*.

    *medium* is a number (dispersion-free), a ``(nd, vd)`` pair, a dict from
    :func:`glass` or :func:`sellmeier`, or a catalogue name (:func:`glass_catalog`,
    which also reaches every transparent material of ``materials``).
    Air (1.0) and vacuum are returned unchanged.

    A ``(nd, vd)`` pair (and a Cauchy dict ``{"A", "B"}`` from :func:`glass`) is
    the two-term Cauchy curve n = A + B/λ² through the d line with the
    F–C dispersion. It is only declared for **0.40–0.80 µm** and raises
    ``ValueError`` outside: against the catalogue Sellmeier curves it is off by
    +0.0057 for a borosilicate crown (n_d 1.5168, V_d 64.2) at 1.55 µm and −0.017 for
    a dense flint (n_d 1.785, V_d 25.7) at 0.365 µm (inside the range: up to 4e-4 for
    the crown and 7e-3 for the dense flint at 0.40 µm). Outside the visible, name the
    glass in the catalogue or pass a Sellmeier / material dict instead.
    """
    wl = _finite(wavelength_um, "wavelength_um", positive=True)
    cauchy_range_um = (0.40, 0.80)          # (nd, vd) / Cauchy: the visible band around F, d and C only
    if isinstance(medium, str):
        medium = glass_catalog(medium)
    if isinstance(medium, dict) and "material" in medium:
        import materials as _mat
        rec = _mat._record(medium["material"], "refractive_index")
        off = _finite(medium.get("offset", 0.0), "index offset")
        n = float(_mat._nk(rec, wl, "refractive_index")[0][0]) + off
        if not (math.isfinite(n) and n >= 1.0):
            raise ValueError("%s index %.4g at %.4g um is below 1 or non-finite" % (rec["name"], n, wl))
        return n
    if isinstance(medium, dict) and "sellmeier" in medium:
        if not (_SELLMEIER_RANGE[0] <= wl <= _SELLMEIER_RANGE[1]):
            raise ValueError("wavelength %.4g um is outside the Sellmeier fit range %s" % (wl, _SELLMEIER_RANGE))
        coef = medium["sellmeier"]
        if not isinstance(coef, (tuple, list)) or len(coef) != 6:
            raise ValueError("sellmeier must hold six coefficients (B1, B2, B3, C1, C2, C3)")
        B1, B2, B3, C1, C2, C3 = (_finite(v, "sellmeier coefficient") for v in coef)
        off = _finite(medium.get("offset", 0.0), "index offset")
        l2 = wl * wl
        if min(abs(l2 - C1), abs(l2 - C2), abs(l2 - C3)) < 1e-12:
            raise ValueError("Sellmeier curve has a pole at %.4g um" % wl)
        n2 = 1.0 + B1 * l2 / (l2 - C1) + B2 * l2 / (l2 - C2) + B3 * l2 / (l2 - C3)
        if not (n2 > 0 and math.isfinite(n2)):
            raise ValueError("Sellmeier curve is singular at %.4g um" % wl)
        n = math.sqrt(n2) + off
        if not (math.isfinite(n) and n >= 1.0):
            raise ValueError("Sellmeier index %.4g at %.4g um is below 1 or non-finite" % (n, wl))
        return float(n)
    if (isinstance(medium, dict) and "A" in medium) or (isinstance(medium, (tuple, list)) and len(medium) == 2):
        if not (cauchy_range_um[0] <= wl <= cauchy_range_um[1]):
            raise ValueError("wavelength %.4g um is outside the (nd, vd) / Cauchy range %s um; that two-term "
                             "curve drifts from the real glass outside the visible (e.g. +0.0057 for a borosilicate "
                             "crown at 1.55 um) -- name the glass or give a Sellmeier / material dict" % (wl, cauchy_range_um))
        g = medium if isinstance(medium, dict) else glass(*medium)
        return float(g["A"] + g["B"] / wl ** 2)
    n = _finite(medium, "index", positive=True)
    if n < 1.0:
        raise ValueError("a refractive index must be >= 1, got %r" % n)
    return n


def _dispersion(medium):
    """``n_F - n_C`` of *medium* (0 for a dispersion-free index)."""
    if isinstance(medium, str) or (isinstance(medium, dict) and ("sellmeier" in medium or "material" in medium)):
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
    if isinstance(medium, dict) and ("sellmeier" in medium or "material" in medium):
        q = dict(medium); q["offset"] = float(medium.get("offset", 0.0)) + delta
        return q
    if isinstance(medium, dict) and "A" in medium:
        q = dict(medium); q["A"] = medium["A"] + delta
        return q
    if isinstance(medium, (tuple, list)):
        return (float(medium[0]) + delta, float(medium[1]))
    n = float(medium) + delta
    if n < 1.0:
        raise ValueError("index %.4g + %.2g would be below 1" % (float(medium), delta))
    return n


# --------------------------------------------------------------------------- #
# prescription
# --------------------------------------------------------------------------- #
#: 面の dict が受ける鍵。後ろの 2 つ(n_value / dn)は lens_system 自身が書き足す値で、
#: ``with_wavelength`` などが出力の面をそのまま入力に戻すので受ける(読み直して上書きする)。
_SURFACE_KEYS = frozenset(("R", "t", "n", "k", "ap", "mirror", "decenter", "tilt", "asph", "n_value", "dn", "f"))


def lens_system(surfaces=None, stop=None, object_mm=INF, wavelength_um=WL_D,
                index_object=1.0, image_mm=None, field=None, aim="paraxial", vignetting=None):
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
      ``(A4, A6, A8, …)`` in mm⁻³, mm⁻⁵, … (default none = pure conic), ``f`` the
      focal length (mm, negative = diverging) of an **ideal paraxial lens**.
    * An ideal lens surface (``{"f": 50.0, "t": …}``) has zero thickness, no
      shape and no glass (``R`` is flat and ``n`` is the medium it sits in; both
      may be left out). It turns every ray by the thin-lens law exactly,
      ``tan θ' = tan θ − h/f`` per transverse axis (h = the ray height), so a
      collimated beam crosses the axis at ``f`` and a point object images at
      the Gaussian conjugate with ``m = −s'/s``. Its optical path is the
      stigmatic one (``f − √(h² + f²)`` for a collimated input, which is the
      quadratic phase ``−h²/(2f)`` at small ``h``; a first surface with a finite
      object uses that object and its Gaussian image instead), so spot, OPD and
      PSF analyses of an aberration-free lens read zero aberration. It adds no
      Seidel terms and no dispersion, takes no mirror / conic / asph, and the
      non-coaxial ``raytrace3d`` does not read it.
    * *stop*: index of the aperture-stop surface (default: the first surface).
      The stop's ``ap`` is the stop radius (required unless every surface has
      one, in which case the smallest is used).
    * *object_mm*: distance from the first vertex to the object (``inf`` for a
      collimated object); *index_object*: index of object space.
    * *field*: default field for the analysis ops — degrees (infinite object)
      or object height in mm (finite object). Default 0 (on axis).
    * *aim*: how the pupil rays are launched. ``"paraxial"`` (the default, and what every
      earlier version did) aims them at the paraxial entrance pupil, with only the chief ray
      moved onto the stop centre; in a system with pupil aberration the marginal rays then land
      outside the stop and are clipped (the stock Cooke triplet loses 48 of 217 rays on axis).
      ``"stop"`` is **real-ray aiming**: every pupil ray is iterated (Newton, tolerance 1e-11 of the
      stop radius, ``ValueError`` if it does not converge) so that it crosses the stop surface at the
      requested point, which is what lens-design software reports. See :func:`with_aiming`.
    * *vignetting*: per-field pupil vignetting factors as design software stores them, a list of
      ``{"field", "vdx", "vdy", "vcx", "vcy", "van"}`` (``field`` in the same unit as *field*;
      missing keys are 0). The normalised pupil is compressed by ``(1 - VCX, 1 - VCY)`` (along
      axes rotated by ``van`` degrees) and decentred by ``(VDX, VDY)`` before the rays are aimed:
      ``q = (VDX, VDY) + R(van) diag(1 - VCX, 1 - VCY) R(-van) p``. A field between two records is
      interpolated linearly, one outside the listed range takes the nearest record.
      :func:`set_vignetting` computes them from the apertures.

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
    med_prev = index_object
    for i, s in enumerate(surfaces):
        if isinstance(s, (tuple, list)):
            keys = ("R", "t", "n", "k", "ap")
            if len(s) > len(keys):                        # ★zip は余りを黙って捨てる
                raise ValueError("surface %d: a tuple surface is (R, t, n[, k[, ap]]) — got %d values; use a dict "
                                 "for mirror / decenter / tilt / asph" % (i, len(s)))
            s = {k: v for k, v in zip(keys, s)}
        f_ideal = s.get("f", None) if isinstance(s, dict) else None
        if f_ideal is not None:
            f_ideal = _finite(f_ideal, "surface %d f" % i)
            if f_ideal == 0.0:
                raise ValueError("surface %d: an ideal lens needs f != 0 (use a very large f for no power)" % i)
            if _radius(s.get("R", INF), "surface %d R" % i) != INF:
                raise ValueError("surface %d: an ideal lens (f) has no radius — leave R flat" % i)
            if s.get("mirror") or s.get("k", 0.0) not in (0, 0.0) or s.get("asph"):
                raise ValueError("surface %d: an ideal lens (f) takes no mirror / conic / asph" % i)
            s = dict(s)
            s["R"] = INF
            s.setdefault("n", med_prev)
        if not isinstance(s, dict) or "R" not in s or "n" not in s:
            raise ValueError("surface %d must have at least R, t and n (got %r)" % (i, s))
        unknown = sorted(set(s) - _SURFACE_KEYS)
        if unknown:                                       # ★2026-10-14: 以前は黙って捨てていた(例 "sag_map")
            raise ValueError("surface %d: unknown key(s) %s — a surface takes %s (a measured or polished "
                             "surface has to be fitted to R / k / asph first)" % (i, unknown, sorted(_SURFACE_KEYS)))
        R = _radius(s.get("R"), "surface %d R" % i)
        t = s.get("t", None)
        t = None if t is None else _finite(t, "surface %d t" % i, nonneg=True)
        if t is None and i != len(surfaces) - 1:
            raise ValueError("surface %d: only the last surface may omit t" % i)
        med = s["n"]
        n_now = refractive_index(med, wavelength_um)      # validates
        if f_ideal is not None and abs(n_now - refractive_index(med_prev, wavelength_um)) > 1e-12:
            raise ValueError("surface %d: an ideal lens sits in one medium — n after it must equal n before it" % i)
        k = _finite(s.get("k", 0.0), "surface %d k" % i)
        ap = s.get("ap", None)
        ap = None if ap is None else _finite(ap, "surface %d ap" % i, positive=True)
        mirror = s.get("mirror", False)
        if not isinstance(mirror, (bool, np.bool_)):
            raise ValueError("surface %d: mirror must be True/False, got %r" % (i, mirror))
        mirror = bool(mirror)
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
                    "dn": _dispersion(med), "f": f_ideal})
        med_prev = med
    if stop is None:
        stop = 0
    elif isinstance(stop, (bool, np.bool_)) or not isinstance(stop, (int, np.integer)):
        raise ValueError("stop must be an integer surface index, got %r" % (stop,))
    stop = int(stop)
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
            "field": 0.0 if field is None else _finite(field, "field"),
            "aim": _check_aim(aim), "vignetting": _vignetting_table(vignetting)}
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


def _paraxial_power(system):
    """Power 1/f of each ideal-lens surface (0 for the others) for :func:`_trace_paraxial`."""
    return np.array([0.0 if s.get("f") is None else 1.0 / s["f"] for s in system["surfaces"]])


def _trace_paraxial(c, t, n, y0, u0, start=0, pw=None):
    """Trace one paraxial ray; returns arrays y (at each surface) and u' (after each).

    *pw* is the per-surface power of ideal lenses (:func:`_paraxial_power`): the thin-lens
    law ``u' = u − y/f`` in the travel direction, i.e. ``n'u' = nu − y c (n'−n) − y|n|/f``.
    """
    ys, us = [], []
    y, u = y0, u0
    for i in range(start, len(c)):
        ys.append(y)
        # refraction: n' u' = n u - y c (n' - n)
        p_i = 0.0 if pw is None else pw[i]
        u = (n[i] * u - y * c[i] * (n[i + 1] - n[i]) - y * p_i * abs(n[i])) / n[i + 1]
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
    pw = _paraxial_power(system)
    ns = len(c)
    # --- focal properties from a collimated axial ray (y=1, u=0) --- #
    y, u = _trace_paraxial(c, t, n, 1.0, 0.0, pw=pw)
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
    y_r, u_r = _trace_paraxial(c_r, t_r, n_r, 1.0, 0.0, pw=pw[::-1])
    ffl = (y_r[-1] / u_r[-1]) if abs(u_r[-1]) > 1e-15 else -INF
    pp_rear = bfl - efl if math.isfinite(efl) else INF
    pp_front = ffl + efl if math.isfinite(efl) else -INF
    # --- pupils: the stop imaged into object / image space --- #
    stop = system["stop"]
    stop_r = system["surfaces"][stop]["ap"]
    # ray from the stop centre backwards: trace forward a ray that has y=0 at the stop
    # with unit slope there, using the linearity of the paraxial trace.
    def y_at_stop(y0, u0):
        yy, _ = _trace_paraxial(c, t, n, y0, u0, pw=pw)
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
        yc, uc = _trace_paraxial(c, t, n, h, 1.0, pw=pw)
        ym, um = _trace_paraxial(c, t, n, ep_radius, 0.0, pw=pw)
        img = bfl
        lagrange = n[0] * (1.0 * ep_radius - 0.0 * h)      # n (ubar*y - u*ybar) at surface 0
    else:
        s0 = s_per_H                                      # chief slope per unit object height
        yc, uc = _trace_paraxial(c, t, n, 1.0 + s0 * obj, s0, pw=pw)   # H = 1
        s_m = stop_r / abs(a)
        ym, um = _trace_paraxial(c, t, n, s_m * obj, s_m, pw=pw)
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
    # ★2026-10-18(lensfile の第 2 実装との照合で発覚): 以前は「|t| の小さい方」を選んでいた。光線が前の面から
    #   出て、球の z 範囲の中から始まる(R < 0 の面が長い空気間隔の後にある望遠型など)と、後ろ側の球面
    #   (t < 0)を拾い、全光線が「けられ」に化けていた(R = −14.5 の面の 26 mm 手前から y = 3 の光線が NaN)。
    #   物理的な交点は頂点を含む葉 —— sag の式の枝で (1+k)·c·z = 1 − √(1 − (1+k)c²r²) ≤ 1 —— の上にある。
    #   その葉の上の根だけを候補にし、両方が乗るとき(双曲面など)に |t| の小さい方を取る。
    with np.errstate(invalid="ignore"):
        on1 = kk * c * (z + t1 * N) <= 1.0 + 1e-9
        on2 = kk * c * (z + t2 * N) <= 1.0 + 1e-9
    pick = np.where(on1 & on2, np.where(np.abs(t1) <= np.abs(t2), t1, t2),
                    np.where(on1, t1, np.where(on2, t2, np.nan)))
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


def _ideal_phase(P0, D0, Q, f, n, obj_z=None):
    """Optical path (mm) an ideal lens adds at the hit point *Q* so that it is stigmatic (all local frame).

    *P0*, *D0*: the ray before the lens. A ray that starts on the object plane (``obj_z`` = its z, a
    finite object at the first surface) is a ray of a spherical wave from its own start point O, and
    the lens images O at ``I = (m Ox, m Oy, s')`` (``s' = f s/(s-f)``, ``m = -s'/s``): equal path
    ``|O−p| + φ + sgn(s')|I−p| = const``. Any other ray is a ray of a plane wave of its own direction,
    focused at ``F = f (qx, qy, 1)``: ``d·p + φ + sgn(f)|F−p| = const``. Both are zero at the vertex
    and ``−n h²/(2f)`` for small h (the quadratic phase).
    """
    sdir = np.where(D0[:, 2] >= 0.0, 1.0, -1.0)
    q = D0[:, :2] / np.abs(D0[:, 2:3])
    d = np.concatenate([q, sdir[:, None]], 1)
    d = d / np.linalg.norm(d, axis=1, keepdims=True)
    F = np.concatenate([q * f, (sdir * f)[:, None]], 1)
    sg = 1.0 if f > 0 else -1.0
    plane = n * (sg * np.linalg.norm(F, axis=1) - np.sum(d * Q, axis=1) - sg * np.linalg.norm(F - Q, axis=1))
    if obj_z is None:
        return plane
    on_obj = np.abs(P0[:, 2] - obj_z) <= 1e-9 * max(1.0, abs(obj_z))
    s_o = -obj_z
    dd = s_o - f
    if abs(dd) < 1e-12 * max(1.0, abs(f)):                # 像が無限遠: 出る波は平面波
        qo = (P0[:, :2] / s_o) * -1.0                      # q' = -O/s
        do = np.concatenate([qo, np.ones((len(P0), 1))], 1)
        do = do / np.linalg.norm(do, axis=1, keepdims=True)
        tail = np.sum(do * Q, axis=1)
    else:
        sp = f * s_o / dd
        m = -sp / s_o
        I = np.concatenate([P0[:, :2] * m, np.full((len(P0), 1), sp)], 1)
        sps = 1.0 if sp > 0 else -1.0
        tail = None
    nO = np.linalg.norm(P0, axis=1)
    sph = nO - np.linalg.norm(P0 - Q, axis=1)
    if tail is not None:
        sph = sph + tail
    else:
        sph = sph + sps * (np.linalg.norm(I, axis=1) - np.linalg.norm(I - Q, axis=1))
    return n * np.where(on_obj, sph, plane / n)


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
    dn = np.linalg.norm(D, axis=1, keepdims=True)
    if np.any(dn <= 0):
        raise ValueError("every direction must have non-zero length")
    D = D / dn
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
        ideal = s.get("f") is not None
        if ideal:                                         # 理想レンズ: 頂点面(z=0)と交わる
            with np.errstate(divide="ignore", invalid="ignore"):
                t = -Pl[:, 2] / Dl[:, 2]
        else:
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
        elif ideal:
            # 薄肉レンズの法則: 進行方向の傾き q = (Dx, Dy)/|Dz| が q' = q - h/f になる(厳密)
            n_after = n_before
            sdir = np.where(Dl[:, 2] >= 0.0, 1.0, -1.0)
            q = Dl[:, :2] / np.abs(Dl[:, 2:3])
            q2 = q - Q[:, :2] / s["f"]
            Dn = np.concatenate([q2, sdir[:, None]], 1)
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
        if ideal:
            opl += _ideal_phase(Pl, Dl, Q, s["f"], n_before,
                                -system["object_mm"] if (i == 0 and system["object_mm"] != INF) else None)
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
            # ★2026-10-14: 以前は bfl(無限遠の物体の焦点)を使い、有限物体でも像面を無限遠の焦点に置いていた
            #   (700 mm の物体で像は 51.39 mm なのに 47.71 mm、W20 −18 波の偽のぼけ)。近軸の像距離は無限遠なら bfl と同じ。
            image_mm = paraxial_trace(system)["image_mm"]
    z_img = z_last + dirn * image_mm
    with np.errstate(divide="ignore", invalid="ignore"):
        tt = (z_img - P[:, 2]) / D[:, 2]
    Q = P + tt[:, None] * D
    opl += n_before * np.abs(tt)
    # ★2026-10-15: 像面とほぼ平行・逆向きに進む光線は像面に届かない —— 無効にする。以前は傾いた鏡(tilt 45°)の後で
    #   D_z ≈ 1e-17 の光線が巨大な有限の点になり、spot_stats が rms 3.4e18 mm・n_vignetted 0 を返した
    #   (傾きは「その面だけ」の摂動で、光軸は折れない。折り返しは raytrace3d の fold_mirror で組む)。
    with np.errstate(invalid="ignore"):
        valid &= np.isfinite(tt) & (dirn * D[:, 2] > _MIN_DZ)
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


def _pupil_at_infinity(para):
    return not (math.isfinite(para["ep_radius"]) and math.isfinite(para["ep_position"]))


def _launch_stop_aimed(system, px, py, field, pupil_fill=1.0, wavelength_um=None):
    """光線を**絞りの点**へ狙って打ち出す(入射瞳が無限遠 = 物体側テレセンの系)。

    ★2026-10-15: 以前は入射瞳を狙う ``_launch`` だけで、入射瞳が無限遠の系では ``chief_ray`` /
    ``ray_bundle`` / ``spot_stats`` が ValueError で止まった(``telecentric`` は自前の狙いで回避していた)。
    狙いは ``raytrace3d`` のベクトル化した Newton 法(絞りの局所座標の (px, py)·ap に当てる)。
    狙えない光線(ケラレ・全反射)は NaN の方向で返し、追跡で無効になる。
    """
    import raytrace3d as _R3
    if any(sf.get("f") is not None for sf in system["surfaces"]):
        raise ValueError("a system with an ideal lens (f) and an object-side telecentric pupil cannot be aimed at the stop")
    sysw = system if wavelength_um is None or float(wavelength_um) == float(system["wavelength_um"]) \
        else with_wavelength(system, wavelength_um)
    s3 = _R3.noncoaxial_system(sysw)
    ap = s3["records"][s3["stop"]]["ap"]
    tg = np.stack([np.asarray(px, float), np.asarray(py, float)], 1) * ap * pupil_fill
    P, D, opl0, ok = _R3._aim(s3, tg, (0.0, float(field)))
    return P, D, opl0, ok


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


# ---- 光線の照準(ray aiming)とケラレ係数 ------------------------------------------------- #
#: 照準の許容誤差(絞りの半径に対する割合)。収束の目標は _AIM_GOAL、受け入れは _AIM_TOL。
#: trace_rays の開口の判定は ap·(1+1e-12) なので、絞りの縁を狙う光線が縁の外へ出ないよう目標は 1e-13。
_AIM_GOAL = 1e-13
_AIM_TOL = 1e-11
_AIM_MAX_ITER = 40
AIM_MODES = ("paraxial", "stop")
_VIG_KEYS = ("vdx", "vdy", "vcx", "vcy", "van")


def _check_aim(aim, name="aim"):
    if aim not in AIM_MODES:
        raise ValueError("%s must be one of %s, got %r" % (name, AIM_MODES, aim))
    return aim


def _vig_entry(v, where):
    """One vignetting record -> dict(vdx, vdy, vcx, vcy, van) of finite floats (compression < 1)."""
    if not isinstance(v, dict):
        raise ValueError("%s must be a dict with some of %s, got %r" % (where, _VIG_KEYS, type(v).__name__))
    unknown = sorted(set(v) - set(_VIG_KEYS) - {"field"})
    if unknown:
        raise ValueError("%s: unknown key(s) %s — vignetting takes %s" % (where, unknown, list(_VIG_KEYS)))
    out = {k: _finite(v.get(k, 0.0), "%s %s" % (where, k)) for k in _VIG_KEYS}
    for k in ("vcx", "vcy"):
        if not 0.0 <= out[k] < 1.0:
            raise ValueError("%s: %s is a pupil compression in [0, 1), got %r" % (where, k, out[k]))
    for k in ("vdx", "vdy"):
        if abs(out[k]) > 1.0:
            raise ValueError("%s: %s is a pupil decentre in normalised pupil units (|.| <= 1), got %r"
                             % (where, k, out[k]))
    return out


def _vignetting_table(vignetting):
    """Validate the per-field vignetting records -> a tuple of dicts sorted by ``field``."""
    if vignetting is None:
        return ()
    if isinstance(vignetting, dict) or not isinstance(vignetting, (list, tuple)):
        raise ValueError("vignetting must be a list of {field, vdx, vdy, vcx, vcy, van} dicts, got %r"
                         % (type(vignetting).__name__,))
    out = []
    for i, v in enumerate(vignetting):
        rec = _vig_entry(v, "vignetting[%d]" % i)
        rec["field"] = _finite(v.get("field", 0.0), "vignetting[%d] field" % i)
        out.append(rec)
    out.sort(key=lambda r: r["field"])
    for a, b in zip(out, out[1:]):
        if b["field"] == a["field"]:
            raise ValueError("vignetting lists field %r twice" % a["field"])
    return tuple(out)


def _vig_at(system, field, vignetting=None):
    """The vignetting factors that apply at *field*, or ``None`` when they are all zero.

    ``vignetting=None`` reads the system's table: an exact field match is used as stored, a field between
    two records is interpolated linearly (what design programs do), and a field outside the listed range
    takes the nearest record. A dict (``{"vdx": …}``) overrides the table for one call.
    """
    if vignetting is not None:
        if not isinstance(vignetting, dict):
            raise ValueError("vignetting must be None or a dict of factors, got %r" % (type(vignetting).__name__,))
        rec = _vig_entry(vignetting, "vignetting")
    else:
        tab = system.get("vignetting") or ()
        if not tab:
            return None
        if field <= tab[0]["field"]:
            rec = tab[0]
        elif field >= tab[-1]["field"]:
            rec = tab[-1]
        else:
            rec = tab[0]
            for a, b in zip(tab, tab[1:]):
                if a["field"] <= field <= b["field"]:
                    w = (field - a["field"]) / (b["field"] - a["field"])
                    rec = {k: (1.0 - w) * a[k] + w * b[k] for k in _VIG_KEYS}
                    break
    if all(rec[k] == 0.0 for k in _VIG_KEYS):
        return None
    return {k: float(rec[k]) for k in _VIG_KEYS}


def _vig_rot(van):
    a = math.radians(van)
    return math.cos(a), math.sin(a)


def _vig_forward(px, py, v):
    """Normalised pupil grid point -> point of the vignetted pupil (stop-plane units).

    The compression ``(1 - VCX, 1 - VCY)`` acts along axes rotated by ``VAN`` (degrees, counter-clockwise);
    the decentre ``(VDX, VDY)`` is added afterwards in the unrotated pupil frame:
    ``q = (VDX, VDY) + R(VAN) diag(1 - VCX, 1 - VCY) R(-VAN) p``.
    """
    c, s = _vig_rot(v["van"])
    u = c * px + s * py
    w = -s * px + c * py
    u = u * (1.0 - v["vcx"])
    w = w * (1.0 - v["vcy"])
    return v["vdx"] + c * u - s * w, v["vdy"] + s * u + c * w


def _vig_inverse(qx, qy, v):
    """Inverse of :func:`_vig_forward` (grid point whose vignetted image is q)."""
    c, s = _vig_rot(v["van"])
    x = qx - v["vdx"]
    y = qy - v["vdy"]
    u = (c * x + s * y) / (1.0 - v["vcx"])
    w = (-s * x + c * y) / (1.0 - v["vcy"])
    return c * u - s * w, s * u + c * w


def _vertex_z(system, index):
    """Global z of surface *index*'s vertex, exactly as :func:`trace_rays` places it (mirrors flip the sense)."""
    z, dirn = 0.0, 1.0
    for i, s in enumerate(system["surfaces"]):
        if i == index:
            return z
        if s["mirror"]:
            dirn = -dirn
        if s["t"] is not None:
            z += dirn * s["t"]
    raise ValueError("surface index %r out of range" % (index,))


def _stop_xy(system, tr):
    """Ray positions on the stop surface in the stop's own frame (N,2); NaN where the trace failed before it."""
    stop = system["stop"]
    s = system["surfaces"][stop]
    off = np.array([s["decenter"][0], s["decenter"][1], _vertex_z(system, stop)])
    return ((tr["points"][:, stop + 1, :] - off) @ _rot(*s["tilt"]))[:, :2]


def _no_apertures(system):
    return dict(system, surfaces=[dict(s, ap=None) for s in system["surfaces"]])


def _aim_at_stop(system, targets, field, para, guess, centre, wavelength_um=None):
    """Launch coordinates ``u`` (N,2; units of the paraxial entrance-pupil radius, see :func:`_launch`) of rays
    that cross the stop surface at *targets* (N,2; mm in the stop's frame).

    Damped Newton iteration per ray with a forward-difference 2x2 Jacobian, all rays at once. The trace used
    for aiming has every semi-aperture removed, so a ray that a later (or earlier) aperture will clip is
    still aimed -- the clipping then shows up as ``valid=False`` of the real trace, not as a failed aim.
    *guess* (N,2) is the starting point, *centre* (2,) the point rays that cannot even be traced at the start
    are pulled toward. Returns ``(u, residual)`` with ``residual`` the distance to the target in units of the
    stop radius; raises ``ValueError`` if any ray ends above ``_AIM_TOL`` (fail closed).
    """
    ap = float(system["surfaces"][system["stop"]]["ap"])
    sysn = _no_apertures(system)
    targets = np.asarray(targets, float)
    n = len(targets)

    def stop_xy(u):
        P, D, _ = _launch(system, u[:, 0], u[:, 1], field, para)
        # image_mm is given only so that trace_rays does not ask for the paraxial focus of the aperture-less copy
        return _stop_xy(system, trace_rays(sysn, P, D, wavelength_um=wavelength_um, image_mm=0.0))

    def rel_err(u, tg):
        with np.errstate(invalid="ignore"):
            return np.hypot(*(stop_xy(u) - tg).T) / ap

    u = np.array(guess, float)
    err = rel_err(u, targets)
    bad = ~np.isfinite(err)
    if bad.any():                                           # pull untraceable starts toward the centre
        g, c = u.copy(), np.asarray(centre, float)
        s = 1.0
        for _ in range(60):
            s *= 0.9
            trial = c + s * (g[bad] - c)
            u[bad] = trial
            e = rel_err(u, targets)
            ok = np.isfinite(e[bad])
            if ok.all():
                break
        err = rel_err(u, targets)
    h = 1e-6
    for _ in range(_AIM_MAX_ITER):
        act = np.where(~(err <= _AIM_GOAL))[0]
        if act.size == 0:
            break
        ua, tg = u[act], targets[act]
        m = len(act)
        big = np.concatenate([ua, ua + [h, 0.0], ua + [0.0, h]])
        r = stop_xy(big) - np.concatenate([tg, tg, tg])
        r0, rx, ry = r[:m], r[m:2 * m], r[2 * m:]
        a, b = (rx[:, 0] - r0[:, 0]) / h, (ry[:, 0] - r0[:, 0]) / h
        c_, d = (rx[:, 1] - r0[:, 1]) / h, (ry[:, 1] - r0[:, 1]) / h
        with np.errstate(divide="ignore", invalid="ignore"):
            det = a * d - b * c_
            step = np.stack([-(d * r0[:, 0] - b * r0[:, 1]) / det, -(-c_ * r0[:, 0] + a * r0[:, 1]) / det], 1)
        step[~np.all(np.isfinite(step), 1)] = 0.0
        alpha = np.ones(m)
        pend = np.ones(m, bool)
        improved = False
        for _bt in range(14):
            idx = np.where(pend)[0]
            if idx.size == 0:
                break
            un = ua[idx] + alpha[idx, None] * step[idx]
            en = rel_err(un, tg[idx])
            good = np.isfinite(en) & (en < err[act][idx])
            gi = idx[good]
            u[act[gi]] = un[good]
            err[act[gi]] = en[good]
            pend[gi] = False
            improved = improved or bool(good.any())
            alpha[idx[~good]] *= 0.5
        if not improved:
            break
    worst = float(np.nanmax(np.where(np.isfinite(err), err, np.inf))) if n else 0.0
    if not worst <= _AIM_TOL:
        nbad = int(np.sum(~(err <= _AIM_TOL)))
        raise ValueError("real-ray aiming did not converge: %d of %d rays miss their point on the stop by up to "
                         "%.3g of the stop radius at field %r (tolerance %.0e); the stop is not reachable by "
                         "that ray (use aim='paraxial', or a smaller pupil_fill / vignetting)"
                         % (nbad, n, worst, field, _AIM_TOL))
    return u, err


def _launch_aimed(system, qx, qy, field, para, pupil_fill=1.0, wavelength_um=None):
    """Rays through stop-plane points ``q * ap * pupil_fill`` (q normalised, may be vignetted).

    Returns ``(P, D, opl0, residual, u)``.
    """
    ap = float(system["surfaces"][system["stop"]]["ap"])
    q = np.stack([np.asarray(qx, float), np.asarray(qy, float)], 1)
    cu, _ = _aim_at_stop(system, np.zeros((1, 2)), field, para, np.zeros((1, 2)), np.zeros(2), wavelength_um)
    guess = q * float(pupil_fill) + cu
    u, err = _aim_at_stop(system, q * ap * float(pupil_fill), field, para, guess, cu[0], wavelength_um)
    P, D, opl0 = _launch(system, u[:, 0], u[:, 1], field, para)
    return P, D, opl0, err, u


def _resolve_aim(system, aim):
    return _check_aim(system.get("aim", "paraxial") if aim is None else aim)


def _launch_pupil(system, qx, qy, field, para, pupil_fill, wavelength_um, aim):
    """Launch rays for pupil coordinates q (already vignetted) with the chosen aiming.

    Returns ``(P, D, opl0, aimed, residual)``: *aimed* (N,) bool is False for rays that could not be aimed
    (object-side telecentric systems only); *residual* is the aiming error in stop radii (``None`` unless
    ``aim="stop"``).
    """
    qx = np.asarray(qx, float)
    qy = np.asarray(qy, float)
    if _pupil_at_infinity(para):                       # 物体側テレセン: 光線を 1 本ずつ絞りの点へ狙う
        P, D, opl0, aimed = _launch_stop_aimed(system, qx, qy, field, pupil_fill, wavelength_um)
        return P, D, opl0, aimed, None
    if aim == "stop":
        P, D, opl0, err, _u = _launch_aimed(system, qx, qy, field, para, pupil_fill, wavelength_um)
        return P, D, opl0, np.ones(len(qx), bool), err
    dpx, dpy = _chief_offset(system, field, para, wavelength_um)   # centre the bundle on the real chief ray
    P, D, opl0 = _launch(system, qx + dpx, qy + dpy, field, para, pupil_fill)
    return P, D, opl0, np.ones(len(qx), bool), None


def chief_ray(system, field=None, wavelength_um=None, image_mm=None):
    """Trace the chief ray (through the stop centre) at one field (``table``).

    Returns ``{"image_x", "image_y"}`` (mm on the image plane), ``"valid"``,
    the full ``points`` (n_surf+2, 3) / ``dirs`` polylines and ``"opl"``.
    Fields are along +y (degrees for a distant object, mm otherwise), as
    everywhere in this module; ``lensimage.distortion_map`` uses this.
    The chief ray is always the **unvignetted** one (pupil centre) and goes through the stop centre
    whatever the system's ``aim`` is.
    """
    _check_system(system)
    field = system["field"] if field is None else _finite(field, "field")
    para = _para_at(system, wavelength_um)
    if _pupil_at_infinity(para):                       # 物体側テレセン: 絞りの中心を狙う
        P, D, opl0, aimed = _launch_stop_aimed(system, [0.0], [0.0], field, wavelength_um=wavelength_um)
    elif system.get("aim", "paraxial") == "stop":      # 実光線の照準: 絞りの中心へ(収束するまで)
        P, D, opl0, _e, _u = _launch_aimed(system, [0.0], [0.0], field, para, 1.0, wavelength_um)
        aimed = np.ones(1, bool)
    else:
        dpx, dpy = _chief_offset(system, field, para, wavelength_um)
        P, D, opl0 = _launch(system, np.array([dpx]), np.array([dpy]), field, para)
        aimed = np.ones(1, bool)
    tr = trace_rays(system, P, D, wavelength_um=wavelength_um, image_mm=image_mm)
    ok = bool(tr["valid"][0]) and bool(aimed[0])
    return {"image_x": float(tr["points"][0, -1, 0]) if ok else float("nan"),
            "image_y": float(tr["points"][0, -1, 1]) if ok else float("nan"),
            "valid": ok, "points": tr["points"][0], "dirs": tr["dirs"][0],
            "opl": float(tr["opl"][0] - opl0[0]) if ok else float("nan"), "field": field}


def _para_at(system, wavelength_um=None):
    """First-order properties at *wavelength_um* (the system's own when None or equal).

    Added 2026-10-15: the traces below take a ``wavelength_um`` override and
    refract at it, but aimed their rays with the pupils of the *system*
    wavelength (and ``lensimage.psf_from_opd`` scaled the PSF with that
    wavelength's f-number), so an override differed from rebuilding the system
    at that wavelength by 2 % of the PSF peak. The image plane is not taken from
    here — the sensor stays where the system puts it.
    """
    if wavelength_um is None or float(wavelength_um) == float(system["wavelength_um"]):
        return paraxial_trace(system)
    return paraxial_trace(with_wavelength(system, wavelength_um))


def _chief_offset(system, field, para, wavelength_um=None):
    """Normalised pupil offset (dpx, dpy) that sends the real chief ray through the stop centre.

    ``_launch`` aims at the *paraxial* entrance pupil; after real refraction by
    the surfaces in front of the stop the ray generally misses the physical
    stop centre. A 2-D Newton iteration on the launch point fixes that (a few
    single-ray traces). On axis the offset is zero by symmetry.
    """
    if field == 0.0 or not math.isfinite(para["ep_radius"]):
        return 0.0, 0.0
    stop = system["stop"]
    surf = system["surfaces"]
    if stop == 0 and surf[0]["decenter"] == (0.0, 0.0) and surf[0]["tilt"] == (0.0, 0.0):
        return 0.0, 0.0                                         # the stop is the first surface: paraxial aim is exact

    def at_stop(px, py):
        P, D, _ = _launch(system, np.array([px]), np.array([py]), field, para)
        tr = trace_rays(system, P, D, wavelength_um=wavelength_um)
        return tr["points"][0, stop + 1, :2]

    px, py = 0.0, 0.0
    h = 1e-3
    for _ in range(20):
        q = at_stop(px, py)
        if not np.all(np.isfinite(q)):
            return 0.0, 0.0                                     # cannot aim (vignetted): keep the paraxial aim
        if np.hypot(q[0], q[1]) < 1e-10:
            break
        qx = at_stop(px + h, py)
        qy = at_stop(px, py + h)
        if not (np.all(np.isfinite(qx)) and np.all(np.isfinite(qy))):
            return px, py
        J = np.array([[(qx[0] - q[0]) / h, (qy[0] - q[0]) / h],
                      [(qx[1] - q[1]) / h, (qy[1] - q[1]) / h]])
        try:
            step = np.linalg.solve(J, -q)
        except np.linalg.LinAlgError:
            return px, py
        px, py = px + float(step[0]), py + float(step[1])
        if abs(px) > 5.0 or abs(py) > 5.0:
            return 0.0, 0.0
    return px, py



def spot_diagram(system, field=None, rings=8, wavelength_um=None, image_mm=None, aim=None, vignetting=None):
    """Transverse ray intersections on the image plane for one field point.

    Returns ``(N,2)`` ``(x, y)`` positions in mm relative to the **chief ray**
    (so the pattern is centred; use ``ray_bundle`` for absolute positions), and
    stores the statistics on the array as attributes via :func:`spot_stats`.
    Rays that miss / vignette are dropped. Pupil: hexapolar, ``rings`` rings.
    *aim* (``"paraxial"`` / ``"stop"``, default the system's own) and *vignetting* are those of
    :func:`ray_bundle`.
    """
    b = ray_bundle(system, field=field, rings=rings, wavelength_um=wavelength_um, image_mm=image_mm,
                   aim=aim, vignetting=vignetting)
    xy = b["image_xy"][b["valid"]] - b["chief_xy"]
    return xy


def spot_stats(system, field=None, rings=8, wavelength_um=None, image_mm=None, pupil_fill=1.0,
               aim=None, vignetting=None):
    """RMS / geometric spot radius (mm) and centroid for one field point (``table``).

    *pupil_fill* < 1 samples the pupil only up to that fraction of its radius:
    with the stop on a surface, the outermost rays sit exactly on the aperture
    edge and any perturbation (tilt, decenter) vignettes half of them, which
    makes the RMS *drop* — :func:`tolerance_analysis` uses 0.99 for that reason.
    ``n_vignetted`` reports how many rays were lost either way.
    *aim* / *vignetting*: see :func:`ray_bundle` — with ``aim="stop"`` and the field's vignetting
    factors this is the spot a lens-design program reports (no marginal rays lost to pupil aberration).
    """
    b = ray_bundle(system, field=field, rings=rings, wavelength_um=wavelength_um, image_mm=image_mm,
                   pupil_fill=pupil_fill, aim=aim, vignetting=vignetting)
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


def ray_bundle(system, field=None, rings=8, wavelength_um=None, image_mm=None, kind="hexapolar", pupil_fill=1.0,
               aim=None, vignetting=None):
    """Trace a pupil-filling bundle at one field; returns the raw trace plus
    ``image_xy`` (N,2), ``chief_xy`` (2,), ``pupil`` (N,2) normalised coordinates
    and ``opl0`` (start-of-ray optical path offsets).

    *aim*: ``"paraxial"`` launches the rays at the paraxial entrance pupil (only the chief ray is moved
    onto the stop centre — the behaviour of every earlier version and the default of a system built
    without ``aim``), ``"stop"`` is real-ray aiming (each ray is iterated until it crosses the stop at
    its own point, residual below 1e-11 of the stop radius, ``ValueError`` otherwise); ``None`` takes
    the system's ``aim``. *vignetting*: ``None`` takes the system's per-field factors
    (:func:`lens_system`), a dict ``{"vdx", "vdy", "vcx", "vcy", "van"}`` overrides them for this call
    (``{}`` = none). The grid ``pupil`` is compressed / decentred by them before aiming, so the bundle
    fills the vignetted pupil; ``chief_xy`` stays the unvignetted chief ray.

    Extra keys: ``pupil_vignetted`` (N,2) the stop-plane pupil coordinates actually aimed at,
    ``stop_xy`` (N,2) where each ray crossed the stop (stop frame, mm; NaN if it was lost before it),
    ``aim``, ``vignetting`` (the factors used, or ``None``) and ``aim_residual`` (largest aiming error in
    stop radii; ``None`` for paraxial aiming).
    """
    _check_system(system)
    field = system["field"] if field is None else _finite(field, "field")
    aim = _resolve_aim(system, aim)
    para = _para_at(system, wavelength_um)
    px, py = _pupil_grid(rings, kind)
    v = _vig_at(system, field, vignetting)
    if v is None:
        qx, qy = px, py
        la_x, la_y = qx, qy
    else:
        qx, qy = _vig_forward(px, py, v)
        la_x, la_y = np.append(qx, 0.0), np.append(qy, 0.0)        # the unvignetted chief ray goes last
    P, D, opl0, aimed, res = _launch_pupil(system, la_x, la_y, field, para, pupil_fill, wavelength_um, aim)
    tr = trace_rays(system, P, D, wavelength_um=wavelength_um, image_mm=image_mm)
    tr["valid"] &= aimed
    tr["points"][~aimed] = np.nan
    img = tr["points"][:, -1, :2]
    ic = int(np.argmin(px * px + py * py))
    if v is None:
        chief_xy = img[ic].copy()
    else:
        chief_xy = img[-1].copy()
        n = len(px)
        for k in ("points", "dirs", "opl", "valid"):
            tr[k] = tr[k][:n]
        img = img[:n]
        opl0 = opl0[:n]
        aimed = aimed[:n]
    tr.update({"image_xy": img, "chief_xy": chief_xy, "pupil": np.stack([px, py], 1),
               "opl0": opl0, "chief_index": ic, "para": para, "field": field,
               "pupil_vignetted": np.stack([qx, qy], 1), "stop_xy": _stop_xy(system, tr),
               "aim": aim, "vignetting": v,
               "aim_residual": None if res is None else float(np.max(res[:len(px)]))})
    return tr


def ray_fan(system, field=None, n=21, axis="y", wavelength_um=None, image_mm=None, aim=None, vignetting=None):
    """Transverse ray aberration along one pupil diameter (``pairs``).

    Returns ``(n,2)``: column 0 the normalised pupil coordinate (−1…1) along
    *axis* (``"y"`` tangential, ``"x"`` sagittal), column 1 the image-plane
    displacement (mm) of that ray from the chief ray along the same axis.
    The classic "ray fan plot"; NaN where a ray is vignetted.
    *aim* / *vignetting* as in :func:`ray_bundle`: the fan runs over the vignetted pupil, the chief ray
    it is measured from is the unvignetted one.
    """
    _check_system(system)
    field = system["field"] if field is None else _finite(field, "field")
    aim = _resolve_aim(system, aim)
    para = _para_at(system, wavelength_um)
    q = np.linspace(-1.0, 1.0, int(n))
    if axis == "y":
        px, py = np.zeros_like(q), q
    elif axis == "x":
        px, py = q, np.zeros_like(q)
    else:
        raise ValueError("axis must be 'x' or 'y'")
    v = _vig_at(system, field, vignetting)
    qx, qy = (px, py) if v is None else _vig_forward(px, py, v)
    qx = np.append(qx, 0.0); qy = np.append(qy, 0.0)    # chief ray last
    P, D, _o, _a, _r = _launch_pupil(system, qx, qy, field, para, 1.0, wavelength_um, aim)
    tr = trace_rays(system, P, D, wavelength_um=wavelength_um, image_mm=image_mm)
    img = tr["points"][:, -1, :2]
    chief = img[-1]
    comp = 1 if axis == "y" else 0
    return np.stack([q, img[:-1, comp] - chief[comp]], 1)


def with_aiming(system, aim="stop", vignetting=None):
    """Copy of *system* with a ray-aiming mode and/or vignetting factors set (``table``).

    ``aim="stop"`` (the default here: this is the op for switching real-ray aiming on) makes every
    spot / fan / OPD / PSF / MTF op launch each pupil ray at its own point on the stop surface
    (:func:`lens_system` explains the iteration); ``aim="paraxial"`` returns to the original launch at the
    paraxial entrance pupil. *vignetting* replaces the per-field factors when given (the list of
    :func:`lens_system`; ``[]`` clears them), otherwise they are kept.
    """
    _check_system(system)
    out = dict(system)
    out["aim"] = _check_aim(aim)
    if vignetting is not None:
        out["vignetting"] = _vignetting_table(vignetting)
    else:
        out.setdefault("vignetting", ())
    return out


def ray_aiming(system, field=None, rings=8, wavelength_um=None, aim="stop", vignetting=None):
    """How well the pupil rays reach the stop at one field: counts, residual and pupil extent (``table``).

    Traces the ``rings``-ring hexapolar pupil with the chosen *aim* (``"stop"`` by default; ``"paraxial"``
    shows what the older launch loses) and reports ``n_rays``, ``n_pass_stop`` (rays that crossed the
    stop surface inside its aperture), ``n_lost`` (rays lost anywhere: stop, other apertures, TIR),
    ``max_residual`` (largest distance between a ray's stop point and its aim point, in stop radii; ``None``
    for paraxial aiming), and the extent of the pupil on the stop in stop radii:
    ``stop_x`` / ``stop_y`` = ``(min, max)`` over the rays that passed. With vignetting factors in force
    the extent is ``(VD − (1 − VC), VD + (1 − VC))`` — compression 0.3 gives a pupil 0.7 as tall.
    """
    b = ray_bundle(system, field=field, rings=rings, wavelength_um=wavelength_um, aim=aim, vignetting=vignetting)
    ap = float(system["surfaces"][system["stop"]]["ap"])
    sxy = b["stop_xy"]
    thru = np.isfinite(sxy).all(1)
    out = {"field": b["field"], "aim": b["aim"], "n_rays": int(len(thru)), "n_pass_stop": int(thru.sum()),
           "n_lost": int((~b["valid"]).sum()), "max_residual": b["aim_residual"],
           "vignetting": b["vignetting"], "stop_radius": ap}
    if thru.any():
        out["stop_x"] = (float(sxy[thru, 0].min() / ap), float(sxy[thru, 0].max() / ap))
        out["stop_y"] = (float(sxy[thru, 1].min() / ap), float(sxy[thru, 1].max() / ap))
    else:
        out["stop_x"] = out["stop_y"] = (float("nan"), float("nan"))
    return out


def set_vignetting(system, fields=None, rings=8, wavelength_um=None):
    """Compute the vignetting factors that remove every aperture-clipped ray, as "set vignetting" does (``table``).

    For each field (a list of radial field values; default the existing records' fields, else the
    system's own ``field``) the real-ray-aimed pupil is searched along ±x and ±y for the edge of the
    clear region (bisection to 1e-13): ``VDX, VDY`` are the centres and ``VCX, VCY`` one minus the
    half-widths, ``VAN`` is 0. If a ``rings``-ring hexapolar grid plus a 72-point rim of the resulting
    ellipse still has clipped rays (the clear region is not an ellipse, e.g. two offset circles) the
    ellipse is shrunk about its centre until none is. A field with nothing clipped gets all-zero factors
    (to 1e-9 and in practice exactly). A field whose chief ray is itself clipped raises ``ValueError``.
    Returns a copy of *system* with ``aim="stop"`` (the factors are fractions of the stop pupil, so they
    belong to real-ray aiming) and the records for those fields replaced; ``vignetting_set`` records the
    fields, grid (``rings``, ``n_checked`` rays per field), and wavelength the factors were verified on.
    """
    _check_system(system)
    if fields is None:
        fields = [r["field"] for r in (system.get("vignetting") or ())] or [system["field"]]
    elif isinstance(fields, (str, bytes, dict)) or not hasattr(fields, "__iter__"):
        raise ValueError("fields must be a list of field values, got %r" % (type(fields).__name__,))
    fl = [_finite(f, "field") for f in fields]
    if not fl:
        raise ValueError("fields must not be empty")
    rings = int(rings)
    if rings < 1:
        raise ValueError("rings must be >= 1")
    wl = system["wavelength_um"] if wavelength_um is None else _finite(wavelength_um, "wavelength_um", positive=True)
    base = dict(system, aim="stop", vignetting=())
    gx, gy = _pupil_grid(rings)
    ang = np.linspace(0.0, 2.0 * math.pi, 72, endpoint=False)
    recs = {}
    for f in fl:
        para = _para_at(base, wl)

        def clear(qx, qy, f=f, para=para):
            P, D, _o, _e, _u = _launch_aimed(base, np.asarray(qx, float), np.asarray(qy, float), f, para, 1.0, wl)
            return trace_rays(base, P, D, wavelength_um=wl)["valid"]

        if not clear([0.0], [0.0])[0]:
            raise ValueError("set_vignetting: the chief ray is clipped at field %r — no pupil is left" % f)
        # edge of the clear region along +x, -x, +y, -y (bisection on the distance from the chief ray)
        dirs = np.array([[1.0, 0.0], [-1.0, 0.0], [0.0, 1.0], [0.0, -1.0]])
        lo = np.zeros(4)
        hi = np.ones(4)
        full = clear(dirs[:, 0], dirs[:, 1])
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            ok = clear(mid * dirs[:, 0], mid * dirs[:, 1])
            lo = np.where(ok, mid, lo)
            hi = np.where(ok, hi, mid)
        t = np.where(full, 1.0, lo)
        t_xp, t_xm, t_yp, t_ym = [float(v) for v in t]
        cx, cy = 0.5 * (t_xp - t_xm), 0.5 * (t_yp - t_ym)
        ax, ay = 0.5 * (t_xp + t_xm), 0.5 * (t_yp + t_ym)

        def ellipse_clear(sc):
            ex = np.concatenate([gx * ax * sc + cx, ax * sc * np.cos(ang) + cx])
            ey = np.concatenate([gy * ay * sc + cy, ay * sc * np.sin(ang) + cy])
            return bool(clear(ex, ey).all())

        sc = 1.0
        if not ellipse_clear(1.0):
            a, b = 0.0, 1.0
            for _ in range(60):
                m = 0.5 * (a + b)
                if ellipse_clear(m):
                    a = m
                else:
                    b = m
            sc = a
        ax, ay = ax * sc, ay * sc
        rec = {"field": f, "vdx": cx, "vdy": cy, "vcx": 1.0 - ax, "vcy": 1.0 - ay, "van": 0.0}
        if full.all() and sc == 1.0:
            rec.update({"vdx": 0.0, "vdy": 0.0, "vcx": 0.0, "vcy": 0.0})
        recs[f] = rec
    keep = [dict(r) for r in (system.get("vignetting") or ()) if r["field"] not in recs]
    out = dict(system)
    out["aim"] = "stop"
    out["vignetting"] = _vignetting_table(keep + list(recs.values()))
    out["vignetting_set"] = {"fields": [float(f) for f in fl], "rings": rings, "wavelength_um": float(wl),
                             "n_checked": int(len(gx) + len(ang))}
    return out


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


def opd_samples(system, field=None, size=64, wavelength_um=None, image_mm=None, aim=None, vignetting=None):
    """OPD (waves) at grid pupil samples: returns ``(px, py, opd, valid)``.

    The grid is ``linspace(-1, 1, size)`` in each pupil coordinate, so the
    outermost sample *centres* sit on the pupil edge (``rho = ±1``): the pupil
    diameter spans ``size − 1`` sample spacings. ``optics.pupil_psf`` counts
    the other way (its grid's full width of ``size`` cells is the diameter), so
    feeding it this map needs ``f_number = N·(size−1)/size`` for the same PSF
    scale (``lensimage.psf_from_opd`` does the bookkeeping for you).

    *aim* (``"paraxial"`` / ``"stop"``, default the system's) is the ray aiming of :func:`ray_bundle`.
    Vignetting (*vignetting*, default the system's per-field factors) is a **mask** here: the grid stays the
    physical pupil (so ``lensimage`` keeps its PSF scale) and only the samples inside the vignetted ellipse
    are valid — the same pupil region the spot diagram fills. The reference is the unvignetted chief ray.
    """
    _check_system(system)
    field = system["field"] if field is None else _finite(field, "field")
    wl = system["wavelength_um"] if wavelength_um is None else _finite(wavelength_um, "wavelength_um", positive=True)
    para = _para_at(system, wavelength_um)
    g = np.linspace(-1.0, 1.0, int(size))
    gx, gy = np.meshgrid(g, g)
    px, py = gx.ravel(), gy.ravel()
    inside = px * px + py * py <= 1.0 + 1e-12
    aim = _resolve_aim(system, aim)
    v = _vig_at(system, field, vignetting)
    if v is not None:
        x0, y0 = _vig_inverse(px, py, v)
        inside &= x0 * x0 + y0 * y0 <= 1.0 + 1e-12
    if aim == "stop":                                          # only aim where the pupil is (corners may not be reachable)
        px_a = np.append(np.where(inside, px, 0.0), 0.0); py_a = np.append(np.where(inside, py, 0.0), 0.0)
        P, D, opl0, _e, _u = _launch_aimed(system, px_a, py_a, field, para, 1.0, wl)
    else:
        px_a = np.append(px, 0.0); py_a = np.append(py, 0.0)    # chief last
        dpx, dpy = _chief_offset(system, field, para, wavelength_um)
        P, D, opl0 = _launch(system, px_a + dpx, py_a + dpy, field, para)
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

    Convenience chain: :func:`opd_samples` → a least-squares Zernike fit **on the
    pupil samples themselves** → ``optics.wavefront_stats``. Returns the stats dict
    extended with ``zernike`` (``{(n, m): coef}``), ``rms_opd_direct`` (RMS of the
    sampled OPD, independent of the fit) and ``pv_opd_direct``.

    Fixed 2026-10-14: the samples used to be burnt into an image and read back with
    ``match3d.fit_zernike``, whose default pupil radius was half a pixel short and
    whose outer ring read the zeros outside the pupil — a synthetic Z20 + 0.5 Z40
    came back as 0.903 / 0.427 and a rotationally symmetric singlet showed a
    spurious Z(4,4). The square grid's in-pupil samples each stand for the same
    area, so a plain least-squares fit on them is the area-weighted projection.
    """
    import match3d
    import optics
    px, py, w, valid = opd_samples(system, field=field, size=size, wavelength_um=wavelength_um, image_mm=image_mm)
    if valid.sum() < 16:
        raise ValueError("too few valid pupil samples for a wavefront fit")
    coeffs = match3d._fit_zernike_points(px[valid], py[valid], w[valid], int(n_max))
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
        if surf[i].get("f") is not None:                 # 理想レンズは収差を足さない
            row = np.zeros(7)
        tot += row
        rows.append({"surface": i, "S_I": float(row[0]), "S_II": float(row[1]), "S_III": float(row[2]),
                     "S_IV": float(row[3]), "S_V": float(row[4]), "C_L": float(row[5]), "C_T": float(row[6])})
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
        if tol.get("index", 0) and not s["mirror"] and s["n_value"] > 1.0 and s.get("f") is None:   # glass only, never an air gap
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


def tolerance_analysis(system, tolerances=None, trials=100, seed=0, field=None, rings=6, compensator="auto"):
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

    *compensator* says whether each perturbed lens is **refocused**: ``"back_focus"`` moves the image
    plane to the perturbed lens's paraxial image (an assembler adjusting the back focus), ``"none"``
    keeps the nominal image plane, ``"auto"`` (default, the behaviour before 2026-10-15) refocuses
    exactly when the last surface's ``t`` is None (the image then follows each perturbed lens) and keeps the
    plane when ``t`` / ``image_mm`` is a number. ★The two answers differ by orders of magnitude (the
    default singlet: the std of the RMS spot changes about 300×), so the result reports the compensator
    actually used under ``compensator``.
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
    if compensator not in ("auto", "back_focus", "none"):
        raise ValueError("compensator must be 'auto', 'back_focus' or 'none', got %r" % (compensator,))
    if system["image_mm"] is not None:
        img_nom = system["image_mm"]
    elif system["surfaces"][-1]["t"] is not None:
        img_nom = system["surfaces"][-1]["t"]
    else:
        img_nom = paraxial_trace(system)["image_mm"]
    if compensator == "auto":
        used = "back_focus" if (system["image_mm"] is None and system["surfaces"][-1]["t"] is None) else "none"
    else:
        used = compensator

    def metrics(sys_):
        p = paraxial_trace(sys_)
        img = p["image_mm"] if used == "back_focus" else img_nom
        st = spot_stats(sys_, field=field, rings=rings, pupil_fill=0.99, image_mm=img)   # see spot_stats: edge vignetting
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
            if key == "n" and (s["mirror"] or s["n_value"] <= 1.0):
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
            "trials": trials, "failed": n_fail, "tolerances": tol, "sensitivity": sens, "seed": int(seed),
            "compensator": used}


# --------------------------------------------------------------------------- #
# chromatic behaviour
# --------------------------------------------------------------------------- #
def with_wavelength(system, wavelength_um=WL_F):
    """The same prescription evaluated at another wavelength (indices re-resolved; default the F line)."""
    _check_system(system)
    return lens_system([dict(s) for s in system["surfaces"]], stop=system["stop"],
                       object_mm=system["object_mm"], wavelength_um=wavelength_um,
                       index_object=system["index_object"], image_mm=system["image_mm"],
                       field=system["field"], aim=system.get("aim", "paraxial"),
                       vignetting=system.get("vignetting"))


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
