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


def _area_of(light):
    """The uniform-disc description of an area source (coaxial), or None."""
    a = light.get("area", None)
    if a is None:
        return None
    if not isinstance(a, dict) or a.get("kind") != "disc":
        raise ValueError("light['area'] must be {'kind': 'disc', 'radius', 'z', 'radiance'}")
    r = _finite(a.get("radius"), "area.radius", positive=True)
    z = _finite(a.get("z"), "area.z")
    L = _finite(a.get("radiance"), "area.radiance", nonneg=True)
    return {"kind": "disc", "radius": r, "z": z, "radiance": L}


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
    * ``"coaxial"`` — a disc of *n* emitters of radius *radius_mm* at
      *height_mm* pointing down: the diffuse area source a beam splitter folds
      onto the viewing axis. Put it at the camera height with a radius of at
      least twice the part size, so that every point of a flat glossy part
      sees the source in its mirror direction (a *small* source at the camera
      gives one bright spot, not a field-wide glare). The dict carries an
      ``area`` record so :func:`defect_contrast` takes the specular glare from
      the disc's uniform radiance ``L = n I0/(π r²)`` by a mirror-hit test
      instead of a point sum that cannot resolve a narrow lobe.
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
        r = R
        k = np.arange(nn)
        rr = r * np.sqrt((k + 0.5) / nn)
        ph = k * math.pi * (3.0 - math.sqrt(5.0))
        E = np.stack([rr * np.cos(ph), rr * np.sin(ph), np.full(nn, h)], 1)
        D = np.tile([0.0, 0.0, -1.0], (nn, 1))
        # the disc as a *uniform Lambertian area source* for the specular term: a
        # point sum cannot resolve a mirror-like lobe (1.3 deg wide at roughness 0.15,
        # 0.14 deg at 0.05) between emitters, so the glare is taken from the source
        # radiance L = n I0 / (pi r^2) wherever the mirror direction lands on the disc
        out["area"] = {"kind": "disc", "radius": r, "z": h, "radiance": nn * I0 / (math.pi * r * r)}
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
    mask = np.zeros(a.shape, bool)
    mask[:band, :] = True; mask[-band:, :] = True; mask[:, :band] = True; mask[:, -band:] = True
    edge = a[mask]                                                # each perimeter pixel once
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


def _mirror_hits_disc(point, normal, view_dir, area):
    """Fresnel factor × 1 if the view ray mirrored at *point* lands on the disc source, else 0."""
    r = -view_dir + 2.0 * np.dot(view_dir, normal) * normal   # reflect the (point->camera) direction
    if r[2] <= 1e-12 or area["z"] <= point[2]:
        return 0.0, 0.0
    t = (area["z"] - point[2]) / r[2]
    hit = point + t * r
    cos_i = float(np.clip(np.dot(r, normal), 0.0, 1.0))
    inside = math.hypot(hit[0], hit[1]) <= area["radius"]
    return (1.0 if inside else 0.0), cos_i


def _radiance(point, normal, view_dir, E, D, I0, m, sp, albedo=None, rough=False, area=None):
    """Radiance toward the camera from one surface point: Σ_e (ρ/π + f_s) E_e (n·l).

    *rough*: a patch of micro-facets of every slope (a chipped edge, a pit, a
    fine scratch's flank). Its specular energy — the Fresnel fraction
    ``F(θ_i)`` of each emitter's light, which the flat surface sends into one
    direction — is scattered diffusely instead, so the patch is Lambertian with
    reflectance ``F + (1 − F) ρ`` per emitter (never above 1, no lobe). That is what dark-field lighting exploits: at grazing incidence
    ``F`` is large and the flat surface returns none of it to the camera.
    """
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
    if rough:
        # energy partition: the Fresnel fraction F scatters diffusely, the rest enters
        # and comes back with the body albedo -> reflectance F + (1 - F) rho <= 1
        F = sp["f0"] + (1.0 - sp["f0"]) * (1.0 - np.clip(ndl, 0.0, 1.0)) ** 5
        return float(np.sum(((F + (1.0 - F) * rho) / np.pi) * irr * np.clip(ndl, 0.0, None)))
    fs = _ggx(ndl, np.full(len(L), ndv), ndh, vdh, sp["roughness"], sp["f0"])
    L_sum = float(np.sum((rho / np.pi + fs) * irr * np.clip(ndl, 0.0, None)))
    if area is None:
        return L_sum
    # an area source whose lobe is narrower than the emitter spacing cannot be
    # resolved by the point sum: its specular term comes from the mirror-hit test on
    # the uniform disc. A wide lobe (matte / satin) is integrated by the sum. The two
    # estimators are blended linearly over one octave of lobe-width / spacing so
    # that no infinitesimal change of roughness or geometry can jump the answer.
    lobe = (sp["roughness"] ** 2) * max(area["z"] - point[2], 1e-9)
    spacing = area["radius"] * math.sqrt(math.pi / max(len(E), 1))
    w_hit = float(np.clip(2.0 - lobe / spacing, 0.0, 1.0))      # 1 below spacing, 0 above 2x spacing
    if w_hit <= 0.0:
        return L_sum
    hit, cos_i = _mirror_hits_disc(point, normal, view_dir, area)
    F = sp["f0"] + (1.0 - sp["f0"]) * (1.0 - cos_i) ** 5
    diff = float(np.sum((rho / np.pi) * irr * np.clip(ndl, 0.0, None)))
    L_hit = diff + hit * F * area["radiance"]
    return w_hit * L_hit + (1.0 - w_hit) * L_sum


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
    the number specular glare dilutes. ``scatter`` is the contrast of a
    **rough** patch (a chipped edge, a pit floor, a fine scratch: micro-facets
    of every slope, modelled as Lambertian with reflectance ``F + (1 − F)ρ``,
    the Fresnel fraction the flat surface would have sent into its specular
    direction now scattered) against the surround — the defect class dark-field lighting is
    built for, since a smooth facet only lights up when it mirrors the source
    into the camera while a rough patch scatters some of *any* light there,
    and at grazing incidence that Fresnel fraction is large. ``regime`` is
    ``"bright_field"`` when
    the flat surface returns specular light to the camera (specular ≥ diffuse
    radiance) and ``"dark_field"`` otherwise. *surface*: a preset (``matte``,
    ``satin``, ``glossy``, ``mirror``, ``brushed_metal``) or a dict ``{albedo,
    roughness, f0}``.
    """
    E, D, I0, m = _check_light(light)
    area = _area_of(light)
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
    L_flat = _radiance(P, flat_n, view, E, D, I0, m, sp, area=area)
    L_diff = _radiance(P, flat_n, view, E, D, I0, m, {"albedo": sp["albedo"], "roughness": 1.0, "f0": 0.0}, area=area)
    L_spec = max(L_flat - L_diff, 0.0)
    rows = []
    for s in slopes:
        th = math.radians(s)
        vals, azs = [], []
        for j in range(na):
            ph = 2.0 * math.pi * j / na
            nrm = np.array([math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)])
            Ld = _radiance(P, nrm, view, E, D, I0, m, sp, area=area)
            den = Ld + L_flat
            vals.append((Ld - L_flat) / den if den > 0 else 0.0)
            azs.append(math.degrees(ph))
        vals = np.array(vals)
        k = int(np.argmax(np.abs(vals)))
        rows.append({"slope_deg": s, "mean": float(vals.mean()), "max_abs": float(abs(vals[k])),
                     "signed_at_max": float(vals[k]), "azimuth_of_max": float(azs[k])})
    L_pig = _radiance(P, flat_n, view, E, D, I0, m, sp, albedo=sp["albedo"] * ratio, area=area)
    pig = (L_flat - L_pig) / (L_flat + L_pig) if (L_flat + L_pig) > 0 else 0.0
    L_rough = _radiance(P, flat_n, view, E, D, I0, m, sp, rough=True)
    sca = (L_rough - L_flat) / (L_rough + L_flat) if (L_rough + L_flat) > 0 else 0.0
    return {"per_slope": rows, "pigment": float(pig), "scatter": float(sca),
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
    simulated Michelson contrast of the stated defect — ``topographic``: a
    smooth facet of *slope_deg* (a dent wall, a bump); ``scatter``: a rough
    patch (chipped edge, pit, fine scratch); ``pigment``: an albedo patch at
    half the surround; ``edge``: a silhouette — **multiplied by the uniformity
    of the background radiance the camera sees** across the part (min/max over
    the centre and the four edge midpoints). That second factor is what
    separates a robust choice from a fragile one: coaxial light on a glossy
    part gives a huge negative contrast exactly on axis (the glare) and almost
    none a few millimetres away, so its background uniformity is poor and it
    ranks below a dark field whose background is uniformly dark. Irradiance
    uniformity is reported too. The result lists the candidates best first
    with their numbers, the ``recommended`` family, and ``rule_of_thumb`` — the textbook
    choice (a smooth facet → coaxial bright field on a glossy finish, else the
    ring elevation that mirrors it into the camera; scatter → dark field; pigment →
    dome; edge → backlight) so a disagreement between simulation and rule is
    visible rather than hidden. Two things the numbers say that folklore does
    not: a *smooth* 10° facet does **not** light up in dark field (it mirrors
    the low light away from the camera) — the "dark field shows scratches"
    rule is about their rough flanks, the ``scatter`` class here; and for that
    class a large coaxial (bright-field) source often scores *higher* than
    dark field because the rough patch appears dark on a uniform glare with
    contrast near 1 (the wafer / glass inspection practice). The model does
    not score sensor saturation or the glare's dependence on part flatness,
    which is why the dark-field rule survives on the shop floor; the table
    shows both so the choice is made with the numbers.
    """
    if defect not in ("topographic", "scatter", "pigment", "edge"):
        raise ValueError("defect must be 'topographic', 'scatter', 'pigment' or 'edge'")
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
        # coaxial = light from the camera's own position (beam splitter): every flat point
        # mirrors it straight back, so the glare covers the field instead of one spot
        "coaxial": light_source("coaxial", radius_mm=2.0 * size, height_mm=ch, n=64),
    }
    if defect == "edge":
        cands["backlight"] = light_source("backlight", radius_mm=R, height_mm=R, n=8)
    rows = []
    probe = [(0.0, 0.0), (size / 2, 0.0), (-size / 2, 0.0), (0.0, size / 2), (0.0, -size / 2)]
    for name, lt in cands.items():
        dc = defect_contrast(lt, surface=sp, slopes_deg=[slope_deg], camera=(0.0, 0.0, ch))
        irr = irradiance_map(lt, size_mm=(size, size), shape=(32, 32),
                             facing="down" if lt["kind"] == "backlight" else "up")
        uni = illumination_uniformity(irr)
        if lt["kind"] == "backlight":
            bg_uni = uni["uniformity"]                           # the camera sees the emitter plane
        else:
            # background radiance toward the camera at the centre and the edge midpoints:
            # a specular glare that exists only on axis has a poor ratio here
            bg = [defect_contrast(lt, surface=sp, slopes_deg=[slope_deg], camera=(0.0, 0.0, ch),
                                  point=p, n_azimuth=1)["flat_radiance"] for p in probe]
            bg_uni = (min(bg) / max(bg)) if max(bg) > 0 else 1.0
        if defect == "topographic":
            contrast = dc["per_slope"][0]["max_abs"]
        elif defect == "scatter":
            contrast = abs(dc["scatter"])
        elif defect == "pigment":
            contrast = abs(dc["pigment"])
        else:                                                    # edge: silhouette wants a backlight
            contrast = 1.0 if lt["kind"] == "backlight" else dc["per_slope"][0]["max_abs"] * 0.5
        score = contrast * bg_uni
        rows.append({"candidate": name, "kind": lt["kind"], "score": float(score),
                     "contrast": float(contrast), "background_uniformity": float(bg_uni),
                     "defect_contrast": dc["per_slope"][0]["max_abs"], "pigment_contrast": abs(dc["pigment"]),
                     "scatter_contrast": abs(dc["scatter"]),
                     "regime": dc["regime"], "uniformity": uni["uniformity"],
                     "elevation_deg": lt.get("elevation_deg")})
    rows.sort(key=lambda r: (-r["score"], -r["uniformity"]))
    if defect == "edge":
        rule = "backlight"
    elif defect == "pigment":
        rule = "dome"
    elif defect == "scatter":
        rule = "ring_dark_field_20deg"
    else:
        rule = "coaxial" if sp["roughness"] < 0.3 else "ring_best_%ddeg" % int(best_el)
    return {"ranking": rows, "recommended": rows[0]["candidate"], "rule_of_thumb": rule,
            "agrees_with_rule": rows[0]["candidate"] == rule, "best_ring_elevation_deg": best_el,
            "surface": sp, "defect": defect, "slope_deg": float(slope_deg)}


# --------------------------------------------------------------------------- #
# illumination cone versus observation cone (2026-10-15)
# --------------------------------------------------------------------------- #
# A light whose *cone of directions* (half-angle and axis) is the same at every
# point of the part — the far-field / Koehler limit an illuminator with a lens
# in front of the emitter approximates — against a camera whose object-side
# cone is set by its NA. This is the illumination-NA / imaging-NA relation of
# microscopy and of schlieren optics, applied to a specular part. On a smooth
# specular facet the reflection maps the illumination cone to another cone of
# the same half-angle (a reflection is an isometry of the sphere of
# directions), so the brightness the camera records is the share of its pupil
# covered by the reflected cone: the intersection of two spherical caps, a
# closed form. Tilting the facet by θ moves the reflected cone by 2θ (on axis).
# With illumination half-angle α and observation half-angle β:
#   |2θ| + β <= α  → the full pupil is lit: the facet is as bright as the flat
#                    ground and the slope is invisible,
#   |2θ| >= α + β  → the pupil is empty: dark,
#   in between     → partial brightness that changes with θ: the slope shows.
# (when α < β the source cone fits inside the pupil and |2θ| + α <= β is the
# plateau instead). Matching α to β makes the smallest slopes visible; widening
# α (or narrowing it far below β) hides the slopes below |α − β|/2; tilting the cone axis by ψ puts the flat ground on
# the edge so that the *sign* of the slope reads as bright / dark (the
# schlieren knife edge).

MAX_SOLID_SAMPLES = 1 << 14
MAX_RENDER_WORK = 1 << 26


def _solid(light):
    """The ``solid_angle`` record of a light from :func:`solid_angle_light`."""
    if not isinstance(light, dict) or not isinstance(light.get("solid_angle"), dict):
        raise ValueError("expected the dict returned by solid_angle_light() (it carries a 'solid_angle' record)")
    sa = light["solid_angle"]
    a = _finite(sa.get("half_angle_deg"), "solid_angle.half_angle_deg", positive=True)
    t = _finite(sa.get("tilt_deg"), "solid_angle.tilt_deg", nonneg=True)
    az = _finite(sa.get("azimuth_deg"), "solid_angle.azimuth_deg")
    L = _finite(sa.get("radiance"), "solid_angle.radiance", nonneg=True)
    if a >= 90.0 or a + t > 90.0:
        raise ValueError("solid_angle: half_angle + tilt must stay within 90 deg")
    return a, t, az, L


def _cone_axis(tilt_deg, azimuth_deg):
    t, p = math.radians(tilt_deg), math.radians(azimuth_deg)
    return np.array([math.sin(t) * math.cos(p), math.sin(t) * math.sin(p), math.cos(t)])


def _view_half_angle(view_na):
    na = _finite(view_na, "view_na", positive=True)
    if na >= 1.0:
        raise ValueError("view_na must be < 1, got %r" % view_na)
    return math.degrees(math.asin(na))


def solid_angle_light(half_angle_deg=10.0, tilt_deg=0.0, azimuth_deg=0.0, radiance=1.0,
                      distance_mm=100.0, n=64):
    """A light defined by the cone of directions it delivers to every point (``table``).

    Every point of the part receives light from the same cone: axis tilted
    *tilt_deg* from the camera axis (+z) toward *azimuth_deg*, half-angle
    *half_angle_deg* (the illumination NA is ``sin`` of it), uniform *radiance*
    inside it. This is the far-field (Koehler) limit that an illuminator with
    a lens in front of the emitter approximates; a coaxial light through a
    half mirror is the case ``tilt_deg = 0``. The record ``solid_angle``
    carries the cone for :func:`solid_angle_brightness`,
    :func:`solid_angle_boundaries`, :func:`solid_angle_sweep` and
    :func:`solid_angle_render`; the dict also holds *n* emitters on a disc at
    *distance_mm* that subtends the same cone at the origin, so
    :func:`irradiance_map` and :func:`defect_contrast` accept it as well (they
    then see a near-field disc, not the far-field cone).

    Returns the light dict (``kind = "solid_angle"``) with ``solid_angle`` =
    ``{half_angle_deg, tilt_deg, azimuth_deg, radiance, axis, solid_angle_sr,
    projected_solid_angle_sr}``; ``solid_angle_sr = 2π(1 − cos α)`` and the
    projected solid angle ``π sin²α`` is the irradiance a surface facing the
    cone receives per unit radiance. Fails closed (``ValueError``) when the
    cone would reach below the part plane (``half_angle + tilt > 90``).
    """
    a = _finite(half_angle_deg, "half_angle_deg", positive=True)
    t = _finite(tilt_deg, "tilt_deg", nonneg=True)
    az = _finite(azimuth_deg, "azimuth_deg")
    L = _finite(radiance, "radiance", nonneg=True)
    dist = _finite(distance_mm, "distance_mm", positive=True)
    nn = _count(n, "n", 1, MAX_EMITTERS)
    if a >= 90.0 or a + t > 90.0:
        raise ValueError("half_angle_deg + tilt_deg must be <= 90 (the cone must stay above the part), got %g + %g" % (a, t))
    axis = _cone_axis(t, az)
    # disc of emitters perpendicular to the axis at distance dist, radius dist*tan(a)
    u = np.cross(axis, [0.0, 0.0, 1.0]) if t > 1e-9 else np.array([1.0, 0.0, 0.0])
    u = u / np.linalg.norm(u)
    w = np.cross(axis, u)
    r = dist * math.tan(math.radians(a))
    k = np.arange(nn)
    rr = r * np.sqrt((k + 0.5) / nn)
    ph = k * math.pi * (3.0 - math.sqrt(5.0))
    E = dist * axis[None, :] + rr[:, None] * (np.cos(ph)[:, None] * u[None, :] + np.sin(ph)[:, None] * w[None, :])
    D = -E / np.linalg.norm(E, axis=1, keepdims=True)
    sa = math.radians(a)
    rec = {"half_angle_deg": a, "tilt_deg": t, "azimuth_deg": az, "radiance": L,
           "axis": [float(v) for v in axis], "solid_angle_sr": 2.0 * math.pi * (1.0 - math.cos(sa)),
           "projected_solid_angle_sr": math.pi * math.sin(sa) ** 2}
    # intensity per emitter so that the disc's radiance equals L: I = L * area / n
    I0 = max(L, 1e-300) * math.pi * r * r / nn
    return {"kind": "solid_angle", "intensity": I0, "cos_exponent": 1.0, "emitters": E, "directions": D,
            "height_mm": float(E[:, 2].mean()), "radius_mm": r, "solid_angle": rec}


def _cap_overlap(a, b, d):
    """Area (sr) of the intersection of two spherical caps of angular radii a, b (rad), centres d apart."""
    if d >= a + b:
        return 0.0
    if d <= abs(a - b):
        m = min(a, b)
        return 2.0 * math.pi * (1.0 - math.cos(m))
    ca, cb, cd = math.cos(a), math.cos(b), math.cos(d)
    sa, sb, sd = math.sin(a), math.sin(b), math.sin(d)

    def ac(x):
        return math.acos(max(-1.0, min(1.0, x)))
    return (2.0 * math.pi - 2.0 * ac((cd - ca * cb) / (sa * sb))
            - 2.0 * ca * ac((cb - cd * ca) / (sd * sa))
            - 2.0 * cb * ac((ca - cd * cb) / (sd * sb)))


def _cap_overlap_vec(a, b, d):
    """:func:`_cap_overlap` over an array of centre distances *d* (rad)."""
    d = np.asarray(d, dtype=np.float64)
    out = np.zeros(d.shape)
    full = d <= abs(a - b)
    out[full] = 2.0 * math.pi * (1.0 - math.cos(min(a, b)))
    part = (~full) & (d < a + b)
    if np.any(part):
        dd = d[part]
        ca, cb, cd = math.cos(a), math.cos(b), np.cos(dd)
        sa, sb, sd = math.sin(a), math.sin(b), np.sin(dd)
        ac = lambda x: np.arccos(np.clip(x, -1.0, 1.0))  # noqa: E731
        out[part] = (2.0 * math.pi - 2.0 * ac((cd - ca * cb) / (sa * sb))
                     - 2.0 * ca * ac((cb - cd * ca) / (sd * sa))
                     - 2.0 * cb * ac((ca - cd * cb) / (sd * sb)))
    return out


def _closed_brightness_rough(alpha, beta, axis, n0, sigma_deg, cells=81):
    """The cap-intersection brightness averaged over Gaussian micro-facet tilts (σ per axis).

    The micro-facet adds a tilt δ = (δx, δy) to the facet normal (``n0 + δ``,
    renormalised). The integrand is the closed-form share — non-zero only on a
    disc of δ of radius about (α + β)/2 around the tilt δ* that mirrors the cone
    axis onto the camera axis — times the Gaussian density. A regular
    *cells* × *cells* midpoint grid over the intersection of that disc's box and
    the ±5σ box resolves both the narrow cone (σ ≫ α + β) and the narrow
    Gaussian (σ ≪ α + β); Gauss–Hermite nodes would step over a cone narrower
    than σ.
    """
    if sigma_deg <= 0.0:
        return _closed_brightness(alpha, beta, axis, n0)[0]
    sg = math.radians(sigma_deg)
    h = axis + np.array([0.0, 0.0, 1.0])
    h = h / np.linalg.norm(h)
    lam = n0[2] / h[2]
    dstar = lam * h[:2] - n0[:2]
    rho = 1.3 * math.radians(alpha + beta) / 2.0 * lam
    lo = np.maximum(dstar - rho, -5.0 * sg)
    hi = np.minimum(dstar + rho, 5.0 * sg)
    if np.any(hi <= lo):
        return 0.0
    k = int(cells)
    gx = lo[0] + (np.arange(k) + 0.5) * (hi[0] - lo[0]) / k
    gy = lo[1] + (np.arange(k) + 0.5) * (hi[1] - lo[1]) / k
    DX, DY = np.meshgrid(gx, gy)
    dA = (hi[0] - lo[0]) * (hi[1] - lo[1]) / (k * k)
    W = np.exp(-(DX * DX + DY * DY) / (2.0 * sg * sg)) / (2.0 * math.pi * sg * sg) * dA
    N = np.stack([n0[0] + DX, n0[1] + DY, np.full(DX.shape, n0[2])], -1)
    N = N / np.linalg.norm(N, axis=-1, keepdims=True)
    s2 = 2.0 * (N @ axis)[..., None] * N - axis
    d = np.arccos(np.clip(s2[..., 2], -1.0, 1.0))
    a, b = math.radians(alpha), math.radians(beta)
    share = _cap_overlap_vec(a, b, d) / (2.0 * math.pi * (1.0 - math.cos(b)))
    share = np.where(s2[..., 2] > 0.0, share, 0.0)
    return float(np.sum(W * share))


def _facet_normal(slope_deg, azimuth_deg):
    s, p = math.radians(slope_deg), math.radians(azimuth_deg)
    return np.array([math.sin(s) * math.cos(p), math.sin(s) * math.sin(p), math.cos(s)])


def _closed_brightness(alpha, beta, axis, nrm):
    """Share of the observation cap (half-angle beta about +z) covered by the mirrored illumination cap."""
    s2 = 2.0 * float(np.dot(axis, nrm)) * nrm - axis          # the cone axis mirrored by the facet
    d = math.acos(max(-1.0, min(1.0, float(s2[2]))))
    if s2[2] <= 0.0:
        return 0.0, math.degrees(d)
    a, b = math.radians(alpha), math.radians(beta)
    return _cap_overlap(a, b, d) / (2.0 * math.pi * (1.0 - math.cos(b))), math.degrees(d)


def _pupil_samples(view_na, k):
    """k points uniform over the pupil disc of radius NA in direction cosines (projected solid angle)."""
    j = np.arange(k)
    rr = view_na * np.sqrt((j + 0.5) / k)
    ph = j * math.pi * (3.0 - math.sqrt(5.0))
    px, py = rr * np.cos(ph), rr * np.sin(ph)
    return np.stack([px, py, np.sqrt(1.0 - px * px - py * py)], 1)


def _cap_samples(axis, alpha_deg, k):
    """k directions uniform in solid angle over the cap of half-angle alpha about *axis*."""
    j = np.arange(k)
    ca = math.cos(math.radians(alpha_deg))
    cz = 1.0 - (1.0 - ca) * (j + 0.5) / k
    sz = np.sqrt(np.clip(1.0 - cz * cz, 0.0, None))
    ph = j * math.pi * (3.0 - math.sqrt(5.0))
    u = np.cross(axis, [0.0, 0.0, 1.0])
    if np.linalg.norm(u) < 1e-12:
        u = np.array([1.0, 0.0, 0.0])
    u = u / np.linalg.norm(u)
    w = np.cross(axis, u)
    return (cz[:, None] * axis[None, :] + (sz * np.cos(ph))[:, None] * u[None, :]
            + (sz * np.sin(ph))[:, None] * w[None, :])


def _specular_share(N, alpha_deg, view_na, axis, k):
    """Share of the pupil that sees the mirrored cone, for normals N (..., k, 3): one micro-facet per sample.

    The quadrature runs over the *narrower* cone so that a plateau (one cone
    wholly inside the other) is resolved: over the pupil (uniform in direction
    cosines, i.e. projected solid angle) when α ≥ β — the share is the mean of
    [mirrored ray inside the source cone]; over the source cap (uniform in solid
    angle) when α < β — each source direction is mirrored into the view space
    and counted with its cosine, ``share = Ω_α/(π NA²) · mean([inside pupil]·v_z)``.
    """
    beta = math.degrees(math.asin(view_na))
    if alpha_deg >= beta:
        V = _pupil_samples(view_na, k)
        vn = np.sum(V * N, axis=-1)
        R = 2.0 * vn[..., None] * N - V
        inside = (np.sum(R * axis, axis=-1) >= math.cos(math.radians(alpha_deg))) & (vn > 0.0) & (R[..., 2] > 0.0)
        return inside.mean(axis=-1)
    S = _cap_samples(axis, alpha_deg, k)
    sn = np.sum(S * N, axis=-1)
    Vv = 2.0 * sn[..., None] * N - S
    inside = ((Vv[..., 0] ** 2 + Vv[..., 1] ** 2) <= view_na * view_na) & (Vv[..., 2] > 0.0) & (sn > 0.0)
    om = 2.0 * math.pi * (1.0 - math.cos(math.radians(alpha_deg)))
    return om / (math.pi * view_na * view_na) * np.mean(inside * Vv[..., 2], axis=-1)


def solid_angle_brightness(light, view_na=0.1, slopes_deg=(0.0, 1.0, 2.0, 5.0, 10.0), slope_azimuth_deg=0.0,
                           roughness_deg=0.0, n_samples=4096, seed=0):
    """Brightness of a smooth or rough specular facet versus its slope (``table``).

    For each facet slope θ in *slopes_deg* (tilted toward *slope_azimuth_deg*;
    a negative slope tilts the other way) the camera (object-side NA
    *view_na*, half-angle β = asin NA, on the +z axis) records the share of its
    pupil that sees the mirrored illumination cone of *light*
    (:func:`solid_angle_light`, half-angle α, axis tilt ψ):

    * ``closed_form`` — the intersection of two spherical caps (half-angles α
      and β, centres ``d`` apart; ``d = 2θ`` for an on-axis cone) divided by
      the cap of the pupil: exact for a mirror facet when the pupil is
      weighted by solid angle. With *roughness_deg* σ > 0 the same closed
      form averaged over the Gaussian micro-facet tilts on a fine midpoint
      grid around the cone (deterministic: no sampling noise);
    * ``numeric`` — *n_samples* rays over the narrower of the two cones (the
      pupil disc, uniform in direction cosines = the projected-solid-angle
      weighting of a lens, when α ≥ β; the source cap, each direction mirrored
      into the view space and weighted by its cosine, when α < β), each
      mirrored by the facet; with *roughness_deg* σ > 0 each ray meets a
      micro-facet tilted by a Gaussian slope (σ per axis, seeded by *seed*):
      the satin / blasted surface on which the boundary smears out.

    Returns ``{"rows": [{slope_deg, closed_form, numeric,
    centre_distance_deg}], ...}``. At σ = 0 the two columns differ only by the
    pupil weighting (``O(β²)``) and the quadrature. Brightness is relative to
    source radiance × Fresnel reflectance (1 = the whole pupil lit).
    """
    alpha, psi, az, _L = _solid(light)
    beta = _view_half_angle(view_na)
    na = float(view_na)
    k = _count(n_samples, "n_samples", 16, MAX_SOLID_SAMPLES)
    sig = _finite(roughness_deg, "roughness_deg", nonneg=True)
    if sig > 30.0:
        raise ValueError("roughness_deg must be <= 30 (small-slope micro-facet model)")
    saz = _finite(slope_azimuth_deg, "slope_azimuth_deg")
    seq = slopes_deg if isinstance(slopes_deg, (list, tuple, np.ndarray)) else [slopes_deg]
    slopes = [_finite(s, "slope") for s in seq]
    if not slopes or any(abs(s) >= 45.0 for s in slopes):
        raise ValueError("slopes_deg must be a non-empty list of angles with |slope| < 45")
    axis = _cone_axis(psi, az)
    J = np.random.default_rng(int(seed)).standard_normal((k, 2)) * math.radians(sig)
    rows = []
    for s in slopes:
        n0 = _facet_normal(s, saz)
        cf, d = _closed_brightness(alpha, beta, axis, n0)
        if sig > 0.0:
            cf = _closed_brightness_rough(alpha, beta, axis, n0, sig)
        N = n0[None, :] + np.stack([J[:, 0], J[:, 1], np.zeros(k)], 1)
        N = N / np.linalg.norm(N, axis=1, keepdims=True)
        num = float(_specular_share(N, alpha, na, axis, k))
        rows.append({"slope_deg": float(s), "closed_form": float(cf), "numeric": num, "centre_distance_deg": d})
    return {"rows": rows, "illum_half_angle_deg": alpha, "illum_tilt_deg": psi, "view_half_angle_deg": beta,
            "view_na": na, "roughness_deg": sig, "n_samples": k}


def solid_angle_boundaries(light, view_na=0.1):
    """Closed-form slope thresholds of a smooth specular facet (``table``).

    Illumination cone half-angle α, axis tilt ψ (from *light*); observation
    half-angle β = asin *view_na*. A facet tilted by θ in the plane of the
    cone tilt moves the mirrored cone axis to ``d = |2θ − ψ|`` from the camera
    axis. Returned:

    * ``flat_brightness`` — the flat surface (θ = 0), from the cap
      intersection: 1 when ``ψ + β ≤ α``, ``Ω_α/Ω_β`` when the whole
      (narrower) source cone sits inside the pupil, 0 when ``ψ ≥ α + β``;
    * ``invisible_below_deg`` — ``max(|α − β| − ψ, 0)/2``: every |θ| below it
      keeps one cap wholly inside the other, so the brightness does not change
      and such slopes do not show at all. It is 0 only for matched cones
      (α = β, or a tilt that puts the flat ground on the edge): there every
      slope dims from the first fraction of a degree;
    * ``dark_beyond_deg`` — ``(α + β + ψ)/2``, the slope (tilted toward the
      cone) where the pupil empties; ``dark_beyond_other_side_deg`` —
      ``(α + β − ψ)/2`` for the opposite tilt;
    * ``sensitivity_per_deg`` — dB/dθ at θ = 0 from the closed form (0 in the
      fully lit plateau, non-zero when the flat ground sits on the edge, which
      is what makes the slope sign readable);
    * ``regime`` — ``bright_field`` (the flat ground sees the whole of the
      narrower cone: ``ψ ≤ |α − β|``), ``dark_field`` (flat dark:
      ``ψ ≥ α + β``) or ``edge`` (in between: the flat ground sits on the
      boundary).
    """
    alpha, psi, az, _L = _solid(light)
    beta = _view_half_angle(view_na)
    axis = _cone_axis(psi, az)

    def b(th):
        return _closed_brightness(alpha, beta, axis, _facet_normal(th, az))[0]
    flat = b(0.0)
    h = 1e-3
    sens = (b(h) - b(-h)) / (2 * h)
    if psi <= abs(alpha - beta) + 1e-12:
        regime = "bright_field"
    elif psi >= alpha + beta - 1e-12:
        regime = "dark_field"
    else:
        regime = "edge"
    return {"illum_half_angle_deg": alpha, "illum_tilt_deg": psi, "view_half_angle_deg": beta,
            "flat_brightness": float(flat),
            "invisible_below_deg": float(max(abs(alpha - beta) - psi, 0.0) / 2.0),
            "dark_beyond_deg": float((alpha + beta + psi) / 2.0),
            "dark_beyond_other_side_deg": float((alpha + beta - psi) / 2.0),
            "sensitivity_per_deg": float(sens), "regime": regime}


def solid_angle_sweep(slope_deg=2.0, view_na=0.1, half_angles_deg=None, tilt_deg=0.0, roughness_deg=0.0,
                      n_samples=2048):
    """Contrast of a facet against flat ground versus the illumination half-angle (``pairs``).

    For each α in *half_angles_deg* (default 1°…30° in 1° steps) a cone light
    of that half-angle and tilt *tilt_deg* is evaluated with
    :func:`solid_angle_brightness` for the flat surface and a facet of
    *slope_deg* (both with micro-facet roughness *roughness_deg*; the
    numeric pupil integral when smooth, the grid average of the closed form
    over the micro-facet tilts when rough). Returns
    ``(n, 2)`` ``[α, |B_facet − B_flat| / (B_facet + B_flat)]`` (0 when both
    are dark). On a smooth surface with an on-axis cone the contrast is 0
    while ``2θ ≤ |α − β|`` (one cone stays inside the other: the slope hides,
    both for a wide cone and for a pin-hole one) and 1 once ``α + β ≤ 2θ``
    — the closed-form ends of the curve; it peaks near α = β.
    """
    if half_angles_deg is None:
        half_angles_deg = [float(v) for v in range(1, 31)]
    als = [_finite(a, "half_angle", positive=True) for a in half_angles_deg]
    if not als:
        raise ValueError("half_angles_deg must not be empty")
    out = []
    for a in als:
        lt = solid_angle_light(a, tilt_deg=tilt_deg, n=1)
        r = solid_angle_brightness(lt, view_na=view_na, slopes_deg=[0.0, slope_deg], roughness_deg=roughness_deg,
                                   n_samples=n_samples)["rows"]
        b0, b1 = r[0]["numeric"], r[1]["numeric"]
        if roughness_deg and float(roughness_deg) > 0.0:
            # the sampled micro-facets would add quadrature noise of the size of the effect; the
            # grid average of the closed form is deterministic
            b0, b1 = r[0]["closed_form"], r[1]["closed_form"]
        out.append([a, abs(b1 - b0) / (b1 + b0) if (b1 + b0) > 0 else 0.0])
    return np.array(out, dtype=np.float64)


def solid_angle_render(normals, light, view_na=0.1, roughness_deg=0.0, f0=0.9, diffuse_albedo=0.0,
                       n_samples=64, seed=0):
    """Image of a normal map under a cone light through a lens of NA *view_na* (``image2d``).

    *normals*: (H, W, 3) surface normals in camera coordinates (+z toward the
    camera; zero-length = background, rendered 0) — e.g. from a height map's
    gradient, ``metalfinish.micro_normals`` (hairline / turning marks) or
    ``metalfinish.blast_normals`` (satin). *light*: :func:`solid_angle_light`.
    Every pixel is viewed along +z with the same object-side cone (a
    telecentric camera) and lit by the same cone (the far-field light), so the
    image is a function of the local normal only:

    ``B = F · share_of_pupil_lit + ρ · sin²α · cos γ``

    The specular share uses *n_samples* rays over the narrower cone (the
    pupil, uniform in direction cosines, or the source cap; the same
    quadrature for every pixel, so there is no pixel noise),
    each mirrored by the normal tilted by a micro-facet slope drawn once per
    ray (*roughness_deg* σ, a scalar or an (H, W) map for satin patches);
    ``F`` = *f0* (Fresnel at near-normal incidence, a constant over the small
    angles involved); the diffuse body term with albedo *diffuse_albedo* uses
    the closed form of the projected solid angle of a uniform cap
    ``π sin²α cos γ`` (γ = angle between the normal and the cone axis; exact
    while the cap stays above the facet's horizon) divided by π. Values are
    relative to the source radiance (1 = mirror, full pupil, F = 1). With few
    samples a partial overlap is quantised to 1/*n_samples*.
    """
    import matappear
    N, mask = matappear._normal_map(normals, "solid_angle_render")
    alpha, psi, az, L = _solid(light)
    _view_half_angle(view_na)
    k = _count(n_samples, "n_samples", 1, 4096)
    F = _finite(f0, "f0", nonneg=True)
    rho = _finite(diffuse_albedo, "diffuse_albedo", nonneg=True)
    if F > 1.0 or rho > 1.0:
        raise ValueError("f0 and diffuse_albedo must be <= 1")
    H, W = N.shape[:2]
    if H * W == 0:
        raise ValueError("solid_angle_render: normals is empty")
    if H * W * k > MAX_RENDER_WORK:
        raise ValueError("H*W*n_samples = %d exceeds %d" % (H * W * k, MAX_RENDER_WORK))
    rg = np.asarray(roughness_deg, dtype=np.float64)
    if rg.ndim == 0:
        rg = np.full((H, W), float(rg))
    if rg.shape != (H, W) or not np.all(np.isfinite(rg)) or np.any(rg < 0) or np.any(rg > 30.0):
        raise ValueError("roughness_deg must be a scalar or an (H, W) map of finite values in [0, 30]")
    axis = _cone_axis(psi, az)
    G = np.random.default_rng(int(seed)).standard_normal((k, 2))
    flatN = N.reshape(-1, 3)
    flatR = np.radians(rg.reshape(-1))
    out = np.zeros(H * W)
    step = max(1, (1 << 20) // k)
    s2a = math.sin(math.radians(alpha)) ** 2
    for a0 in range(0, len(flatN), step):
        n0 = flatN[a0:a0 + step]
        sg = flatR[a0:a0 + step]
        Nn = n0[:, None, :] + np.concatenate([sg[:, None, None] * G[None, :, :], np.zeros((len(n0), k, 1))], 2)
        Nn = Nn / np.maximum(np.linalg.norm(Nn, axis=2, keepdims=True), 1e-12)
        share = _specular_share(Nn, alpha, float(view_na), axis, k)
        cg = np.clip(n0 @ axis, 0.0, None)
        out[a0:a0 + step] = F * share + rho * s2a * cg
    img = (out * L).reshape(H, W)
    return img * mask
