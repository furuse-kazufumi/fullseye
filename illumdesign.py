# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""illumdesign — machine-vision illumination design: lights, irradiance, defect contrast.

The lens (``raytrace`` / ``lensimage``) decides how sharply a defect is
*imaged*; the **lighting** decides whether it has any contrast to image at all.
Choosing ring / dome / coaxial / backlight and the angle is the first decision
on an inspection line and the one most often made by trial and error. This
module puts numbers on it, from first principles:

* :func:`light_source` — an emitter set (positions, pointing directions, radiant
  intensity, Lambertian order) for the standard families: ``point``, ``ring``,
  ``bar``, ``dome``, ``coaxial`` (on-axis area source), ``backlight`` (planar
  emitter behind the part), or a custom list.
* :func:`irradiance_map` — irradiance on the part plane (optionally on a height
  map), ``E = Σ I0 cosᵐθ_e · cosθ_s / d²`` per emitter — the inverse-square /
  cosine law, so a single point source over a plane reproduces ``E(r) = I0
  cos³θ / h²`` exactly.
* :func:`illumination_uniformity` — min/max ratio, coefficient of variation,
  edge fall-off of an irradiance map (the numbers a spec sheet quotes).
* :func:`defect_contrast` — Michelson contrast between a tilted facet (a
  scratch flank, a dent wall, a bump) and the flat surround as seen by the
  camera, with a Lambertian + GGX microfacet BRDF (same lobe as
  ``specularity.brdf_microfacet``), averaged and maximised over the facet's
  azimuth; also pigment (albedo) contrast, which specular glare *dilutes*.
* :func:`lighting_sweep` — contrast versus ring-light elevation; on a glossy
  surface the peak sits where the tilted facet mirrors the light into the
  camera (light zenith = 2 × facet slope) — a closed form the tests check.
* :func:`illumination_design` — evaluates the candidate families for a stated
  surface finish and defect type and ranks them by simulated contrast, with the
  rule-of-thumb it agrees or disagrees with spelled out.

Conventions: the part plane is ``z = 0`` with +z toward the camera, lengths in
millimetres, radiant intensity in arbitrary units (only ratios are reported;
irradiance therefore in units/mm²). All inputs fail closed (``ValueError``),
sizes are capped (``MAX_EMITTERS``, ``MAX_MAP_ELEMENTS``).
"""
from __future__ import annotations

import math

import numpy as np

MAX_EMITTERS = 4096
MAX_MAP_ELEMENTS = 1 << 22
MAX_HEIGHT_ELEMENTS = 1 << 22
_KINDS = ("point", "ring", "bar", "dome", "coaxial", "backlight", "custom")


# --------------------------------------------------------------------------- #
# validation
# --------------------------------------------------------------------------- #
def _finite(v, name, positive=False, nonneg=False):
    if isinstance(v, (bool, str, np.bool_)) or v is None:
        raise ValueError("%s must be a real number, got %r" % (name, v))
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real number, got %r" % (name, v))
    if not math.isfinite(x):
        raise ValueError("%s must be finite, got %r" % (name, v))
    if positive and x <= 0:
        raise ValueError("%s must be > 0, got %r" % (name, v))
    if nonneg and x < 0:
        raise ValueError("%s must be >= 0, got %r" % (name, v))
    return x


def _count(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s must be an integer, got %r" % (name, v))
    if not lo <= int(v) <= hi:
        raise ValueError("%s must be %d..%d, got %d" % (name, lo, hi, v))
    return int(v)


def _vec3(v, name, unit=False):
    a = np.asarray(v, dtype=np.float64)
    if a.shape != (3,) or not np.all(np.isfinite(a)):
        raise ValueError("%s must be a finite 3-vector, got %r" % (name, v))
    if unit:
        n = np.linalg.norm(a)
        if n <= 0:
            raise ValueError("%s has zero length" % name)
        a = a / n
    return a


def _check_light(light):
    if not isinstance(light, dict) or "emitters" not in light or "directions" not in light:
        raise ValueError("expected the dict returned by light_source(), got %r" % type(light).__name__)
    E = np.asarray(light["emitters"], dtype=np.float64)
    D = np.asarray(light["directions"], dtype=np.float64)
    if E.ndim != 2 or E.shape[1] != 3 or D.shape != E.shape or len(E) == 0:
        raise ValueError("light: emitters/directions must be (N,3) with N >= 1")
    if len(E) > MAX_EMITTERS:
        raise ValueError("light: %d emitters exceed MAX_EMITTERS=%d" % (len(E), MAX_EMITTERS))
    if not (np.all(np.isfinite(E)) and np.all(np.isfinite(D))):
        raise ValueError("light: emitters/directions must be finite")
    nrm = np.linalg.norm(D, axis=1)
    if np.any(nrm <= 0):
        raise ValueError("light: a pointing direction has zero length")
    D = D / nrm[:, None]
    I0 = _finite(light.get("intensity", 1.0), "intensity", positive=True)
    m = _finite(light.get("cos_exponent", 1.0), "cos_exponent", nonneg=True)
    return E, D, I0, m


# --------------------------------------------------------------------------- #
# light sources
# --------------------------------------------------------------------------- #
def light_source(kind="ring", radius_mm=60.0, height_mm=100.0, n=24, tilt_deg=None,
                 length_mm=100.0, intensity=1.0, cos_exponent=1.0, position=None,
                 emitters=None, directions=None):
    """An emitter set for a standard machine-vision light family (``table``).

    *kind*:

    * ``"point"`` — one emitter at *position* (default ``(0, 0, height_mm)``)
      pointing straight down.
    * ``"ring"`` — *n* emitters on a circle of *radius_mm* at *height_mm*,
      each tilted toward the axis by *tilt_deg* (default: aimed at the origin,
      so the ring's elevation angle is ``atan(height/radius)``; low
      height/radius = dark field, high = bright field).
    * ``"bar"`` — *n* emitters along a line of *length_mm* parallel to x at
      ``y = radius_mm``, ``z = height_mm``, aimed at the origin line.
    * ``"dome"`` — *n* emitters spread over a hemisphere of *radius_mm*
      (Fibonacci lattice, zenith angles 20°–85°), each pointing at the centre:
      the diffuse, shadow-free illumination of a dome light.
    * ``"coaxial"`` — a small disc of *n* emitters of radius ``radius_mm/10``
      at *height_mm* pointing down: light along the viewing axis (through a
      beam splitter in practice).
    * ``"backlight"`` — *n* × *n* emitters on a square of side ``2·radius_mm``
      at ``z = −height_mm`` pointing **up**: the part is seen in silhouette.
    * ``"custom"`` — *emitters* (N,3) and *directions* (N,3) given explicitly.

    *intensity* is the radiant intensity of one emitter on its axis (arbitrary
    units), *cos_exponent* the Lambertian order of its angular distribution
    (1 = ideal Lambertian LED; ~2–4 for a lensed LED with a narrower beam).
    """
    if kind not in _KINDS:
        raise ValueError("kind must be one of %s, got %r" % (_KINDS, kind))
    I0 = _finite(intensity, "intensity", positive=True)
    m = _finite(cos_exponent, "cos_exponent", nonneg=True)
    out = {"kind": kind, "intensity": I0, "cos_exponent": m}
    if kind == "custom":
        if emitters is None or directions is None:
            raise ValueError("custom light needs emitters and directions")
        E = np.asarray(emitters, dtype=np.float64)
        D = np.asarray(directions, dtype=np.float64)
        out.update({"emitters": E, "directions": D})
        _check_light(out)
        return out
    h = _finite(height_mm, "height_mm", positive=True)
    R = _finite(radius_mm, "radius_mm", positive=True)
    nn = _count(n, "n", 1, MAX_EMITTERS)
    if kind == "point":
        pos = np.array([0.0, 0.0, h]) if position is None else _vec3(position, "position")
        if pos[2] <= 0:
            raise ValueError("a point light must sit above the part plane (z > 0)")
        E = pos[None, :]
        D = np.array([[0.0, 0.0, -1.0]])
    elif kind == "ring":
        ang = 2.0 * np.pi * np.arange(nn) / nn
        E = np.stack([R * np.cos(ang), R * np.sin(ang), np.full(nn, h)], 1)
        if tilt_deg is None:
            D = -E / np.linalg.norm(E, axis=1, keepdims=True)         # aimed at the origin
        else:
            tl = math.radians(_finite(tilt_deg, "tilt_deg"))
            if not 0.0 <= tl <= math.pi / 2:
                raise ValueError("tilt_deg must be 0..90")
            D = np.stack([-np.cos(ang) * math.sin(tl), -np.sin(ang) * math.sin(tl), np.full(nn, -math.cos(tl))], 1)
    elif kind == "bar":
        Lh = _finite(length_mm, "length_mm", positive=True)
        xs = np.linspace(-Lh / 2, Lh / 2, nn) if nn > 1 else np.zeros(1)
        E = np.stack([xs, np.full(nn, R), np.full(nn, h)], 1)
        D = np.stack([np.zeros(nn), np.full(nn, -R), np.full(nn, -h)], 1)
        D = D / np.linalg.norm(D, axis=1, keepdims=True)
    elif kind == "dome":
        i = np.arange(nn) + 0.5
        z_lo, z_hi = math.cos(math.radians(85.0)), math.cos(math.radians(20.0))
        cz = z_hi - (z_hi - z_lo) * i / nn
        phi = i * math.pi * (3.0 - math.sqrt(5.0))
        sz = np.sqrt(1.0 - cz * cz)
        E = R * np.stack([sz * np.cos(phi), sz * np.sin(phi), cz], 1)
        D = -E / np.linalg.norm(E, axis=1, keepdims=True)
        out["radius_mm"] = R
    elif kind == "coaxial":
        r = R / 10.0
        k = np.arange(nn)
        rr = r * np.sqrt((k + 0.5) / nn)
        ph = k * math.pi * (3.0 - math.sqrt(5.0))
        E = np.stack([rr * np.cos(ph), rr * np.sin(ph), np.full(nn, h)], 1)
        D = np.tile([0.0, 0.0, -1.0], (nn, 1))
    else:                                                        # backlight
        g = np.linspace(-R, R, nn) if nn > 1 else np.zeros(1)
        gx, gy = np.meshgrid(g, g)
        E = np.stack([gx.ravel(), gy.ravel(), np.full(gx.size, -h)], 1)
        D = np.tile([0.0, 0.0, 1.0], (gx.size, 1))
        if len(E) > MAX_EMITTERS:
            raise ValueError("backlight n*n=%d exceeds MAX_EMITTERS=%d" % (len(E), MAX_EMITTERS))
    out.update({"emitters": E, "directions": D, "height_mm": h, "radius_mm": R})
    if kind == "ring":
        out["elevation_deg"] = math.degrees(math.atan2(h, R))
    return out


# --------------------------------------------------------------------------- #
# irradiance
# --------------------------------------------------------------------------- #
def _irradiance_at(points, normals, E, D, I0, m):
    """Irradiance at *points* (P,3) with unit *normals* (P,3): Σ_e I0 cos^m θ_e cos θ_s / d²."""
    out = np.zeros(len(points))
    step = max(1, int(MAX_MAP_ELEMENTS // max(1, len(E))))
    for a in range(0, len(points), step):
        P = points[a:a + step]
        Nn = normals[a:a + step]
        V = P[:, None, :] - E[None, :, :]                           # emitter -> point
        d2 = np.sum(V * V, axis=2)
        d = np.sqrt(d2)
        with np.errstate(invalid="ignore", divide="ignore"):
            U = V / d[:, :, None]
        cos_e = np.sum(U * D[None, :, :], axis=2)                    # angle off the emitter axis
        cos_s = -np.sum(U * Nn[:, None, :], axis=2)                  # angle at the surface
        cos_e = np.clip(cos_e, 0.0, None)
        cos_s = np.clip(cos_s, 0.0, None)
        with np.errstate(divide="ignore", invalid="ignore"):
            contrib = I0 * cos_e ** m * cos_s / d2
        contrib = np.where(d2 > 0, contrib, 0.0)
        out[a:a + step] = contrib.sum(1)
    return out


def irradiance_map(light, size_mm=(50.0, 50.0), shape=(128, 128), height=None, z_mm=0.0, facing="up"):
    """Irradiance on the part plane (``image2d``, units of intensity / mm²).

    The plane is centred on the axis, *size_mm* = (height, width) in mm sampled
    on *shape* = (rows, cols); +y is up (row 0 is the top). *height* (optional,
    same shape as the map, mm) tilts each pixel's normal to that of a relief
    surface — a dent or a bump then shows as the irradiance it actually
    receives. *z_mm* shifts the plane (a thick part's top face). *facing*
    ``"up"`` (+z, toward the camera) or ``"down"`` — the face a backlight
    illuminates (what the camera sees through the part's apertures).

    Closed forms: an isotropic point source (``cos_exponent=0``) at height h
    gives ``E = I0 cos³θ / h²``; a Lambertian emitter (``cos_exponent=1``)
    pointing down gives the cos⁴ law ``E = I0 cos⁴θ / h²``.
    """
    E, D, I0, m = _check_light(light)
    if not (isinstance(size_mm, (list, tuple)) and len(size_mm) == 2):
        raise ValueError("size_mm must be (height_mm, width_mm)")
    sh, sw = (_finite(size_mm[0], "size_mm[0]", positive=True), _finite(size_mm[1], "size_mm[1]", positive=True))
    if not (isinstance(shape, (list, tuple)) and len(shape) == 2):
        raise ValueError("shape must be (rows, cols)")
    H, W = _count(shape[0], "rows", 1, 1 << 14), _count(shape[1], "cols", 1, 1 << 14)
    if H * W > MAX_MAP_ELEMENTS:
        raise ValueError("map of %d elements exceeds MAX_MAP_ELEMENTS=%d" % (H * W, MAX_MAP_ELEMENTS))
    z0 = _finite(z_mm, "z_mm")
    if facing not in ("up", "down"):
        raise ValueError("facing must be 'up' or 'down'")
    ys = (0.5 - (np.arange(H) + 0.5) / H) * sh
    xs = ((np.arange(W) + 0.5) / W - 0.5) * sw
    X, Y = np.meshgrid(xs, ys)
    if height is None:
        Z = np.full((H, W), z0)
        Nn = np.tile([0.0, 0.0, 1.0], (H * W, 1))
    else:
        hz = np.asarray(height, dtype=np.float64)
        if hz.shape != (H, W) or not np.all(np.isfinite(hz)):
            raise ValueError("height must be a finite (rows, cols) array matching shape")
        Z = z0 + hz
        dy = sh / H
        dx = sw / W
        gy, gx = np.gradient(hz, dy, dx)
        gy = -gy                                                 # row index runs against +y
        Nn = np.stack([-gx.ravel(), -gy.ravel(), np.ones(H * W)], 1)
        Nn /= np.linalg.norm(Nn, axis=1, keepdims=True)
    if facing == "down":
        Nn = -Nn
    pts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    return _irradiance_at(pts, Nn, E, D, I0, m).reshape(H, W)


def illumination_uniformity(irradiance, region_fraction=0.8):
    """Uniformity figures of an irradiance map (``table``).

    ``uniformity`` = min/max over the central *region_fraction* of each axis,
    ``cv`` = std/mean there, ``edge_falloff`` = mean of the outermost 5 % band
    over the centre value, plus ``peak_offset_px`` (where the maximum sits
    relative to the centre — a mis-aimed ring shows up here).
    """
    a = np.asarray(irradiance, dtype=np.float64)
    if a.ndim != 2 or a.size == 0 or not np.all(np.isfinite(a)):
        raise ValueError("irradiance must be a finite 2-D map")
    if a.size > MAX_MAP_ELEMENTS:
        raise ValueError("map too large")
    if np.any(a < 0):
        raise ValueError("irradiance cannot be negative")
    f = _finite(region_fraction, "region_fraction", positive=True)
    if f > 1.0:
        raise ValueError("region_fraction must be <= 1")
    H, W = a.shape
    r0, r1 = int(round(H * (1 - f) / 2)), max(int(round(H * (1 + f) / 2)), int(round(H * (1 - f) / 2)) + 1)
    c0, c1 = int(round(W * (1 - f) / 2)), max(int(round(W * (1 + f) / 2)), int(round(W * (1 - f) / 2)) + 1)
    reg = a[r0:r1, c0:c1]
    mx = float(reg.max())
    if mx <= 0:
        raise ValueError("the region receives no light")
    centre = float(a[H // 2, W // 2])
    band = max(1, int(round(0.05 * min(H, W))))
    edge = np.concatenate([a[:band].ravel(), a[-band:].ravel(), a[:, :band].ravel(), a[:, -band:].ravel()])
    iy, ix = np.unravel_index(int(np.argmax(a)), a.shape)
    return {"min": float(reg.min()), "max": mx, "mean": float(reg.mean()), "std": float(reg.std()),
            "uniformity": float(reg.min() / mx), "cv": float(reg.std() / reg.mean()) if reg.mean() > 0 else float("inf"),
            "edge_falloff": float(edge.mean() / centre) if centre > 0 else float("inf"),
            "centre": centre, "peak_offset_px": (int(iy - H // 2), int(ix - W // 2)),
            "region_fraction": f}


# --------------------------------------------------------------------------- #
# reflectance seen by the camera
# --------------------------------------------------------------------------- #
def _ggx(ndl, ndv, ndh, vdh, roughness, f0):
    """GGX / Smith / Schlick specular BRDF (same lobe as specularity.brdf_microfacet)."""
    a = roughness * roughness
    a2 = a * a
    ch = np.clip(ndh, 0.0, 1.0)
    denom = (1.0 - ch * ch) + a2 * ch * ch
    Dn = a2 / (np.pi * denom * denom)
    cl = np.clip(ndl, 1e-12, 1.0)
    cv = np.clip(ndv, 1e-12, 1.0)
    g1l = 2.0 * cl / (cl + np.sqrt(a2 + (1.0 - a2) * cl * cl))
    g1v = 2.0 * cv / (cv + np.sqrt(a2 + (1.0 - a2) * cv * cv))
    F = f0 + (1.0 - f0) * (1.0 - np.clip(vdh, 0.0, 1.0)) ** 5
    f = Dn * g1l * g1v * F / (4.0 * cl * cv)
    return np.where((ndl > 0) & (ndv > 0), f, 0.0)


def _surface_params(surface):
    s = {"albedo": 0.5, "roughness": 0.3, "f0": 0.04}
    if surface is not None:
        if isinstance(surface, str):
            presets = {"matte": {"albedo": 0.6, "roughness": 0.9, "f0": 0.03},
                       "satin": {"albedo": 0.5, "roughness": 0.4, "f0": 0.04},
                       "glossy": {"albedo": 0.3, "roughness": 0.15, "f0": 0.05},
                       "mirror": {"albedo": 0.05, "roughness": 0.05, "f0": 0.9},
                       "brushed_metal": {"albedo": 0.1, "roughness": 0.35, "f0": 0.7}}
            if surface not in presets:
                raise ValueError("surface preset must be one of %s" % sorted(presets))
            s.update(presets[surface])
        elif isinstance(surface, dict):
            for k in surface:
                if k not in s:
                    raise ValueError("unknown surface key %r (albedo, roughness, f0)" % k)
            s.update(surface)
        else:
            raise ValueError("surface must be a preset name or a dict")
    alb = _finite(s["albedo"], "albedo", nonneg=True)
    rough = _finite(s["roughness"], "roughness", positive=True)
    f0 = _finite(s["f0"], "f0", nonneg=True)
    if alb > 1.0 or rough > 1.0 or f0 > 1.0:
        raise ValueError("albedo, roughness and f0 must be <= 1")
    return {"albedo": alb, "roughness": rough, "f0": f0}


def _radiance(point, normal, view_dir, E, D, I0, m, sp, albedo=None):
    """Radiance toward the camera from one surface point: Σ_e (ρ/π + f_s) E_e (n·l)."""
    V = E - point[None, :]                                       # point -> emitter
    d2 = np.sum(V * V, axis=1)
    L = V / np.sqrt(d2)[:, None]
    cos_e = np.clip(np.sum(-L * D, axis=1), 0.0, None)
    ndl = np.sum(L * normal[None, :], axis=1)
    ndv = float(np.dot(normal, view_dir))
    Hh = L + view_dir[None, :]
    Hh = Hh / np.maximum(np.linalg.norm(Hh, axis=1, keepdims=True), 1e-300)
    ndh = np.sum(Hh * normal[None, :], axis=1)
    vdh = np.sum(Hh * view_dir[None, :], axis=1)
    irr = I0 * cos_e ** m / d2                                   # irradiance per unit projected area
    rho = sp["albedo"] if albedo is None else albedo
    fs = _ggx(ndl, np.full(len(L), ndv), ndh, vdh, sp["roughness"], sp["f0"])
    return float(np.sum((rho / np.pi + fs) * irr * np.clip(ndl, 0.0, None)))


def defect_contrast(light, surface="satin", slopes_deg=(2.0, 5.0, 10.0, 20.0), camera=(0.0, 0.0, 300.0),
                    point=(0.0, 0.0), n_azimuth=12, pigment_albedo_ratio=0.5):
    """Contrast of topographic and pigment defects under a light (``table``).

    For each facet slope in *slopes_deg* the radiance toward *camera* of a
    facet tilted by that slope (azimuth swept in *n_azimuth* steps) is compared
    with the flat surface at *point*: ``contrast = (L_defect − L_flat) /
    (L_defect + L_flat)`` (Michelson, −1..1; the sign says whether the flank
    appears brighter or darker than the surround). Reported per slope as
    ``mean``, ``max_abs`` and ``azimuth_of_max``. ``pigment`` is the contrast
    of a flat patch whose albedo is *pigment_albedo_ratio* × the surround —
    the number specular glare dilutes. ``regime`` is ``"bright_field"`` when
    the flat surface returns specular light to the camera (specular ≥ diffuse
    radiance) and ``"dark_field"`` otherwise. *surface*: a preset (``matte``,
    ``satin``, ``glossy``, ``mirror``, ``brushed_metal``) or a dict ``{albedo,
    roughness, f0}``.
    """
    E, D, I0, m = _check_light(light)
    sp = _surface_params(surface)
    cam = _vec3(camera, "camera")
    if cam[2] <= 0:
        raise ValueError("the camera must be above the part plane (z > 0)")
    px, py = (_finite(point[0], "point[0]"), _finite(point[1], "point[1]")) if isinstance(point, (list, tuple)) and len(point) == 2 else (None, None)
    if px is None:
        raise ValueError("point must be (x_mm, y_mm)")
    P = np.array([px, py, 0.0])
    view = cam - P
    view = view / np.linalg.norm(view)
    na = _count(n_azimuth, "n_azimuth", 1, 360)
    ratio = _finite(pigment_albedo_ratio, "pigment_albedo_ratio", nonneg=True)
    slopes = [_finite(s, "slope", nonneg=True) for s in (slopes_deg if isinstance(slopes_deg, (list, tuple)) else [slopes_deg])]
    if not slopes or any(s >= 90.0 for s in slopes):
        raise ValueError("slopes_deg must be a non-empty list of angles < 90")
    flat_n = np.array([0.0, 0.0, 1.0])
    L_flat = _radiance(P, flat_n, view, E, D, I0, m, sp)
    L_diff = _radiance(P, flat_n, view, E, D, I0, m, {"albedo": sp["albedo"], "roughness": 1.0, "f0": 0.0})
    L_spec = max(L_flat - L_diff, 0.0)
    rows = []
    for s in slopes:
        th = math.radians(s)
        vals, azs = [], []
        for j in range(na):
            ph = 2.0 * math.pi * j / na
            nrm = np.array([math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)])
            Ld = _radiance(P, nrm, view, E, D, I0, m, sp)
            den = Ld + L_flat
            vals.append((Ld - L_flat) / den if den > 0 else 0.0)
            azs.append(math.degrees(ph))
        vals = np.array(vals)
        k = int(np.argmax(np.abs(vals)))
        rows.append({"slope_deg": s, "mean": float(vals.mean()), "max_abs": float(abs(vals[k])),
                     "signed_at_max": float(vals[k]), "azimuth_of_max": float(azs[k])})
    L_pig = _radiance(P, flat_n, view, E, D, I0, m, sp, albedo=sp["albedo"] * ratio)
    pig = (L_flat - L_pig) / (L_flat + L_pig) if (L_flat + L_pig) > 0 else 0.0
    return {"per_slope": rows, "pigment": float(pig),
            "regime": "bright_field" if L_spec >= L_diff and L_flat > 0 else "dark_field",
            "flat_radiance": L_flat, "flat_specular_fraction": float(L_spec / L_flat) if L_flat > 0 else 0.0,
            "surface": sp, "camera": [float(v) for v in cam]}


def lighting_sweep(surface="glossy", slope_deg=10.0, elevations_deg=None, radius_mm=60.0,
                   n=24, camera_height_mm=300.0, kind="ring"):
    """Defect contrast versus ring-light elevation angle (``pairs``).

    A ring (or bar) of *radius_mm* is placed at heights giving each elevation
    in *elevations_deg* (default 5°…85° in 5° steps) and :func:`defect_contrast`
    is evaluated for a facet of *slope_deg* on *surface*. Returns ``(n, 2)``
    ``[elevation, max_abs contrast]``; the maximum tells the designer where to
    put the light. On a glossy surface the peak is at elevation ``90° − 2 ×
    slope`` (the facet mirrors the light into a camera on axis) — the closed
    form ``tests/test_illumdesign.py`` pins.
    """
    if elevations_deg is None:
        elevations_deg = [float(v) for v in range(5, 90, 5)]
    els = [_finite(e, "elevation") for e in elevations_deg]
    if not els or any(not 0 < e < 90 for e in els):
        raise ValueError("elevations_deg must be angles strictly between 0 and 90")
    if kind not in ("ring", "bar"):
        raise ValueError("kind must be 'ring' or 'bar'")
    R = _finite(radius_mm, "radius_mm", positive=True)
    ch = _finite(camera_height_mm, "camera_height_mm", positive=True)
    out = []
    for e in els:
        h = R * math.tan(math.radians(e))
        lt = light_source(kind, radius_mm=R, height_mm=h, n=n)
        dc = defect_contrast(lt, surface=surface, slopes_deg=[slope_deg], camera=(0.0, 0.0, ch))
        out.append([e, dc["per_slope"][0]["max_abs"]])
    return np.array(out, dtype=np.float64)


def illumination_design(surface="glossy", defect="topographic", slope_deg=10.0, part_size_mm=50.0,
                        camera_height_mm=300.0):
    """Rank the standard light families for a surface / defect pairing (``table``).

    Candidates: low-angle ring (dark field, elevation 20°), high-angle ring
    (bright field, 70°), the elevation that :func:`lighting_sweep` finds best,
    dome, coaxial and (for ``defect="edge"``) backlight. Each is scored by the
    simulated Michelson contrast of the stated defect (``topographic``: a
    facet of *slope_deg*; ``pigment``: an albedo patch at half the surround)
    and by irradiance uniformity over the part. The result lists the
    candidates best first with their numbers, the ``recommended`` family, and
    ``rule_of_thumb`` — the textbook choice (topographic on glossy → dark
    field; pigment → dome / bright field; edge → backlight) so a disagreement
    between simulation and rule is visible rather than hidden.
    """
    if defect not in ("topographic", "pigment", "edge"):
        raise ValueError("defect must be 'topographic', 'pigment' or 'edge'")
    sp = _surface_params(surface)
    size = _finite(part_size_mm, "part_size_mm", positive=True)
    ch = _finite(camera_height_mm, "camera_height_mm", positive=True)
    R = max(size, 30.0)
    sweep = lighting_sweep(surface=sp, slope_deg=slope_deg, radius_mm=R, camera_height_mm=ch,
                           elevations_deg=[float(v) for v in range(10, 90, 10)])
    best_el = float(sweep[int(np.argmax(sweep[:, 1])), 0])
    cands = {
        "ring_dark_field_20deg": light_source("ring", radius_mm=R, height_mm=R * math.tan(math.radians(20.0))),
        "ring_bright_field_70deg": light_source("ring", radius_mm=R, height_mm=R * math.tan(math.radians(70.0))),
        "ring_best_%ddeg" % int(best_el): light_source("ring", radius_mm=R, height_mm=R * math.tan(math.radians(best_el))),
        "dome": light_source("dome", radius_mm=1.5 * R, n=96),
        "coaxial": light_source("coaxial", radius_mm=R, height_mm=ch * 0.5, n=16),
    }
    if defect == "edge":
        cands["backlight"] = light_source("backlight", radius_mm=R, height_mm=R, n=8)
    rows = []
    for name, lt in cands.items():
        dc = defect_contrast(lt, surface=sp, slopes_deg=[slope_deg], camera=(0.0, 0.0, ch))
        irr = irradiance_map(lt, size_mm=(size, size), shape=(32, 32),
                             facing="down" if lt["kind"] == "backlight" else "up")
        uni = illumination_uniformity(irr)
        if defect == "topographic":
            score = dc["per_slope"][0]["max_abs"]
        elif defect == "pigment":
            score = abs(dc["pigment"])
        else:                                                    # edge: silhouette wants a backlight
            score = 1.0 if lt["kind"] == "backlight" else dc["per_slope"][0]["max_abs"] * 0.5
        rows.append({"candidate": name, "kind": lt["kind"], "score": float(score),
                     "defect_contrast": dc["per_slope"][0]["max_abs"], "pigment_contrast": abs(dc["pigment"]),
                     "regime": dc["regime"], "uniformity": uni["uniformity"],
                     "elevation_deg": lt.get("elevation_deg")})
    rows.sort(key=lambda r: (-r["score"], -r["uniformity"]))
    if defect == "edge":
        rule = "backlight"
    elif defect == "pigment":
        rule = "dome" if sp["roughness"] < 0.5 else "ring_bright_field_70deg"
    else:
        rule = "ring_dark_field_20deg" if sp["roughness"] < 0.5 else "ring_best_%ddeg" % int(best_el)
    return {"ranking": rows, "recommended": rows[0]["candidate"], "rule_of_thumb": rule,
            "agrees_with_rule": rows[0]["candidate"] == rule, "best_ring_elevation_deg": best_el,
            "surface": sp, "defect": defect, "slope_deg": float(slope_deg)}
