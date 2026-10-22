# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""lensrender — photograph a 3-D scene through the actual lens prescription (sensor-side ray tracing).

``lensimage.render_through_lens`` turns a flat picture into what the sensor would record by tiling
point-spread functions; it cannot show depth of field, the cat's-eye shape of a defocused highlight at the
field edge, or what a near object looks like. This module renders a **scene** instead
(Kolb, Mitchell & Hanrahan 1995, "A realistic camera model for computer graphics"): for every sensor point it
samples the exit pupil, traces each ray **backwards** through every surface of the prescription (Snell's law
with dispersion, conics and even aspheres, mirrors, the semi-diameters as stops, total internal reflection)
into object space, shades the scene there, and adds up the radiance with the geometric weight
``cos^2(theta) / d^2`` of the pupil sample. The irradiance becomes photons (energy to photons, quantum
efficiency, pixel area, exposure) and goes through the shot / dark / read noise and the quantiser of
``lensimage._sensor``.

The ops::

    lens_scene(objects, lights, ...)                       -> a validated scene (planes, spheres, meshes, lights)
    exit_pupil_samples(system, n, pattern)                 -> points and area weights on the exit pupil
    trace_sensor_rays(system, pixel_xy_mm, pupil_xy_mm)    -> sensor point -> pupil point -> object-space ray
    scene_radiance(ray_origins, ray_dirs, scene, ...)      -> Lambertian + Blinn lobe radiance, shadows
    render_scene_through_lens(system, scene, sensor, ...)  -> the photograph (irradiance, electrons, noisy image)
    bokeh_shape(system, field_xy_mm, defocus_mm)           -> the out-of-focus footprint of a point (cat's eye)
    render_ghost_overlay(system, scene, light_xy_mm, ...)  -> two-reflection ghost images of a bright point
    render_compare_prescriptions(systems, scene, sensor)   -> the same scene through several prescriptions

Conventions. The lens frame of ``raytrace``: the optical axis is z, the first vertex is at z = 0 and the scene is at
z < 0 (``z_mm = -1000`` is a plane one metre in front of the lens). Sensor points are ``(x, y)`` in the image plane in
the same axes (the image is inverted: object +y lands at sensor -y). The rendered picture is shown **upright**:
pixel ``(row, col)`` is the sensor point ``x = -(col - cx) p``, ``y = +(row - cy) p`` (pixel pitch ``p``), which is the
recorded image turned by 180 degrees. Lengths are mm, wavelengths micrometres (``_um``), spectral radiance
W m^-2 sr^-1 nm^-1.

What it does not do (stated, and shown in the PoC): it is **geometric** optics only - no diffraction, so the PSF of a
well corrected lens is smaller than the Airy disc; the exit pupil is sampled at its paraxial position and size
(pupil aberration that moves the real pupil outside it loses the light of that part); the transmission is
Fresnel-free unless ``fresnel=True`` (unpolarised Fresnel loss per refracting surface, no coating, no absorption in
the glass); point sources are splatted by forward ray tracing (they do not occlude and are not seen by shadow
rays); light is not scattered inside the lens except by the ghost overlay.
"""
from __future__ import annotations

import math

import numpy as np

import raytrace as RT

__all__ = ["lens_scene", "exit_pupil_samples", "trace_sensor_rays", "scene_radiance",
           "render_scene_through_lens", "bokeh_shape", "render_ghost_overlay", "render_compare_prescriptions"]

INF = float("inf")
#: Planck constant times the speed of light (J m); h c / lambda is the photon energy
HC = 6.62607015e-34 * 299792458.0
#: the three wavelengths of the F, d and C lines (um) - the default bands
WL_BANDS = (RT.WL_F, RT.WL_D, RT.WL_C)
#: effective wavelengths of the B, G, R channels of an RGB albedo (um)
RGB_ANCHORS_UM = (0.465, 0.54, 0.61)
PATTERNS = ("hexapolar", "halton")
#: the most ray samples one call traces
MAX_RAY_SAMPLES = 400_000_000
MAX_PUPIL = 8192
_PHI = 0.6180339887498949


# --------------------------------------------------------------------------- validation
def _real(value, name, op, lo=None, hi=None, lo_open=False, hi_open=False):
    if isinstance(value, (bool, np.bool_, str, bytes)) or value is None:
        raise ValueError("%s: %s must be a real number, got %r" % (op, name, value))
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a real number, got %r" % (op, name, value)) from None
    if not math.isfinite(v):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, value))
    if lo is not None and (v < lo or (lo_open and v == lo)):
        raise ValueError("%s: %s must be %s %g, got %g" % (op, name, ">" if lo_open else ">=", lo, v))
    if hi is not None and (v > hi or (hi_open and v == hi)):
        raise ValueError("%s: %s must be %s %g, got %g" % (op, name, "<" if hi_open else "<=", hi, v))
    return v


def _int(value, name, op, lo, hi):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        if isinstance(value, (float, np.floating)) and float(value).is_integer():
            value = int(value)
        else:
            raise ValueError("%s: %s must be an integer, got %r" % (op, name, value))
    value = int(value)
    if value < lo or value > hi:
        raise ValueError("%s: %s must be in [%d, %d], got %d" % (op, name, lo, hi, value))
    return value


def _choice(value, name, op, allowed):
    if not isinstance(value, str) or value not in allowed:
        raise ValueError("%s: %s must be one of %s, got %r" % (op, name, list(allowed), value))
    return value


def _array(value, name, op, shape_tail=None, ndim=None, min_size=1):
    """A finite float64 array; *shape_tail* is the required trailing shape (e.g. ``(3,)``)."""
    if isinstance(value, (str, bytes)) or value is None:
        raise ValueError("%s: %s must be numeric, got %r" % (op, name, value))
    try:
        a = np.asarray(value)
    except Exception:
        raise ValueError("%s: %s is not array-like" % (op, name)) from None
    if a.dtype.kind not in "iuf":
        raise ValueError("%s: %s must be numeric, got dtype %s" % (op, name, a.dtype))
    a = a.astype(np.float64)
    if ndim is not None and a.ndim != ndim:
        raise ValueError("%s: %s must be %d-D, got shape %r" % (op, name, ndim, a.shape))
    if shape_tail is not None and (a.ndim < len(shape_tail) or a.shape[a.ndim - len(shape_tail):] != tuple(shape_tail)):
        raise ValueError("%s: %s must end in shape %r, got %r" % (op, name, tuple(shape_tail), a.shape))
    if a.size < min_size:
        raise ValueError("%s: %s is empty" % (op, name))
    if not np.isfinite(a).all():
        raise ValueError("%s: %s has non-finite values" % (op, name))
    return a


def _system(system, op):
    if not isinstance(system, dict) or "surfaces" not in system or "stop" not in system:
        raise ValueError("%s: expected the table returned by raytrace.lens_system(), got %r" % (op, type(system).__name__))
    if system.get("kind") == "noncoaxial_system":
        raise ValueError("%s: a non-coaxial system is not supported (use a raytrace.lens_system prescription)" % op)
    return system


def _axisymmetric(system):
    return all(tuple(s["decenter"]) == (0.0, 0.0) and tuple(s["tilt"]) == (0.0, 0.0) for s in system["surfaces"])


def _wavelength(system, wavelength_um, op):
    if wavelength_um is None:
        return float(system["wavelength_um"])
    return _real(wavelength_um, "wavelength_um", op, lo=0.2, hi=20.0)


# --------------------------------------------------------------------------- system helpers (read-only use of raytrace)
def _with_object(system, object_mm):
    """The same prescription with another object distance (``raytrace.with_wavelength`` is the model)."""
    return RT.lens_system([dict(s) for s in system["surfaces"]], stop=system["stop"], object_mm=object_mm,
                          wavelength_um=system["wavelength_um"], index_object=system["index_object"],
                          image_mm=system["image_mm"], field=system["field"], aim=system.get("aim", "paraxial"),
                          vignetting=system.get("vignetting"))


def _nominal_image_mm(system, focus_mm):
    """Last vertex -> sensor (mm) of the unshifted sensor: the system's own plane, or the paraxial image of *focus_mm*."""
    surf = system["surfaces"]
    if focus_mm is not None:
        return float(RT.paraxial_trace(_with_object(system, focus_mm))["image_mm"])
    if system["image_mm"] is not None:
        return float(system["image_mm"])
    if surf[-1]["t"] is not None:
        return float(surf[-1]["t"])
    return float(RT.paraxial_trace(system)["image_mm"])


def _geometry(system, wl, defocus_mm=0.0, focus_mm=None, op="lensrender"):
    """Everything the backward trace needs at wavelength *wl*: vertices, indices, sensor plane, exit pupil."""
    surf = system["surfaces"]
    zv, z, dirn = [], 0.0, 1.0
    for s in surf:
        zv.append(z)
        if s["mirror"]:
            dirn = -dirn
        if s["t"] is not None:
            z = z + dirn * s["t"]
    n_obj = float(system["index_object"])
    nb, na = [], []
    n_before = n_obj
    for s in surf:
        nb.append(n_before)
        if s["mirror"] or s.get("f") is not None:
            n_after = n_before
        else:
            n_after = float(RT.refractive_index(s["n"], wl))
        na.append(n_after)
        n_before = n_after
    sysw = system if float(wl) == float(system["wavelength_um"]) else RT.with_wavelength(system, wl)
    para = RT.paraxial_trace(sysw)
    if not (math.isfinite(para["xp_position"]) and math.isfinite(para["xp_radius"])) or para["xp_radius"] <= 0.0:
        raise ValueError("%s: the exit pupil is at infinity or has no size (image-space telecentric or degenerate stop); "
                         "sensor-side pupil sampling needs a finite exit pupil" % op)
    img = _nominal_image_mm(system, focus_mm) + float(defocus_mm)
    z_last = zv[-1]
    return {"zv": zv, "nb": nb, "na": na, "dirn": dirn, "z_last": z_last, "image_mm": img,
            "z_img": z_last + dirn * img, "xp_position": float(para["xp_position"]),
            "xp_radius": float(para["xp_radius"]), "z_xp": z_last + dirn * float(para["xp_position"]),
            "wavelength_um": float(wl), "n_image": na[-1], "n_object": n_obj, "para": para}


# --------------------------------------------------------------------------- the backward trace
def _trace_back(system, geo, P, D, fresnel=False):
    """Trace rays travelling **toward the object** from points *P* (N,3) with unit directions *D* (N,3).

    The surfaces are visited from the last to the first; the medium the ray is in is the one *after* the surface in
    the forward sense, and it refracts into the one before it (indices swapped), so a forward ray reversed
    retraces itself (Snell's law is symmetric). Returns the point where the ray leaves the first surface, its
    direction (into the scene), the transmission, ``valid`` and ``tir``. Lost rays are NaN.
    """
    surf = system["surfaces"]
    P = np.array(P, dtype=np.float64)
    D = np.array(D, dtype=np.float64)
    n = len(P)
    ok = np.ones(n, bool)
    tir = np.zeros(n, bool)
    trans = np.ones(n)
    with np.errstate(all="ignore"):
        for i in range(len(surf) - 1, -1, -1):
            s = surf[i]
            c = 0.0 if s["R"] == INF else 1.0 / s["R"]
            Rm = RT._rot(*s["tilt"])
            off = np.array([s["decenter"][0], s["decenter"][1], geo["zv"][i]])
            Pl = (P - off) @ Rm
            Dl = D @ Rm
            ideal = s.get("f") is not None
            if ideal:
                t = -Pl[:, 2] / Dl[:, 2]
            else:
                t = RT._intersect_surface(Pl, Dl, c, s["k"], s["asph"])
            bad = ~np.isfinite(t) | (t < -1e-9)
            t = np.where(bad, np.nan, t)
            Q = Pl + t[:, None] * Dl
            if s["ap"] is not None:
                bad |= np.hypot(Q[:, 0], Q[:, 1]) > s["ap"] * (1.0 + 1e-12)
            nrm = RT._surface_normal(Q, c, s["k"], s["asph"])
            flip = np.sum(nrm * Dl, axis=1) > 0
            nrm[flip] *= -1.0
            cos_i = -np.sum(nrm * Dl, axis=1)
            if s["mirror"]:
                Dn = Dl - 2.0 * np.sum(nrm * Dl, axis=1)[:, None] * nrm
            elif ideal:
                sdir = np.where(Dl[:, 2] >= 0.0, 1.0, -1.0)
                q = Dl[:, :2] / np.abs(Dl[:, 2:3])
                Dn = np.concatenate([q - Q[:, :2] / s["f"], sdir[:, None]], 1)
            else:
                eta = geo["na"][i] / geo["nb"][i]
                sin2_t = eta * eta * (1.0 - cos_i * cos_i)
                t_ir = sin2_t > 1.0
                tir |= t_ir & ok & ~bad
                bad |= t_ir
                cos_t = np.sqrt(np.clip(1.0 - sin2_t, 0.0, None))
                Dn = eta * Dl + (eta * cos_i - cos_t)[:, None] * nrm
                if fresnel:
                    n1, n2 = geo["na"][i], geo["nb"][i]
                    rs = ((n1 * cos_i - n2 * cos_t) / (n1 * cos_i + n2 * cos_t)) ** 2
                    rp = ((n1 * cos_t - n2 * cos_i) / (n1 * cos_t + n2 * cos_i)) ** 2
                    trans = trans * (1.0 - 0.5 * (rs + rp))
            Dn = Dn / np.linalg.norm(Dn, axis=1, keepdims=True)
            P = Q @ Rm.T + off
            D = Dn @ Rm.T
            ok &= ~bad
            P[~ok] = np.nan
            D[~ok] = np.nan
    trans = np.where(ok, trans, 0.0)
    return P, D, trans, ok, tir


# --------------------------------------------------------------------------- exit pupil sampling
def _radical_inverse(idx, base):
    idx = np.array(idx, dtype=np.int64)
    out = np.zeros(len(idx))
    f = 1.0 / base
    while np.any(idx > 0):
        out += f * (idx % base)
        idx //= base
        f /= base
    return out


def _unit_pupil(n, pattern):
    """Points in the unit disc and weights summing to pi (the disc area), deterministically."""
    if pattern == "hexapolar":
        r = 0
        while 1 + 3 * (r + 1) * (r + 2) <= n:
            r += 1
        w = 1.0 / (r + 0.5)
        pts, wts = [(0.0, 0.0)], [math.pi * (0.5 * w) ** 2]
        for k in range(1, r + 1):
            for j in range(6 * k):
                a = 2.0 * math.pi * j / (6 * k)
                pts.append((k * w * math.cos(a), k * w * math.sin(a)))
                wts.append(2.0 * math.pi * k * w * w / (6.0 * k))
        return np.array(pts), np.array(wts), None
    got = []
    drawn = 0
    start = 1
    need = n
    while need > 0:
        m = max(2 * need, 64)
        idx = np.arange(start, start + m)
        x = 2.0 * _radical_inverse(idx, 2) - 1.0
        y = 2.0 * _radical_inverse(idx, 3) - 1.0
        sel = np.nonzero(x * x + y * y <= 1.0)[0]
        if len(sel) >= need:
            take = sel[:need]
            drawn += int(take[-1]) + 1
            got.append(np.stack([x[take], y[take]], 1))
            need = 0
        else:
            drawn += m
            got.append(np.stack([x[sel], y[sel]], 1))
            need -= len(sel)
            start += m
    uv = np.concatenate(got, 0)
    return uv, np.full(n, math.pi / n), n / float(drawn)


def exit_pupil_samples(system, n=64, pattern="hexapolar", wavelength_um=None) -> dict:
    """Sample points on the exit pupil of *system* (position and radius from the paraxial trace) -> dict.

    ``pattern="hexapolar"`` puts a centre point and rings of 6k points (the largest count not above *n*), each with the
    area of its annulus share, so the weights sum to the disc area exactly; ``pattern="halton"`` takes the Halton
    sequence (bases 2 and 3) in the enclosing square and keeps the points inside the disc (rejection), *n* of them,
    each with weight ``pi R^2 / n``. Both are deterministic. The table has ``xy_mm`` (K, 2) in the exit-pupil plane,
    ``uv`` the same in units of the radius, ``weights_mm2`` (sum = ``area_mm2`` = pi R^2), ``z_mm`` (the plane in
    the lens frame), ``radius_mm``, ``position_mm`` (last vertex to the pupil along the light), ``area_ratio``
    (sum of the weights over the enclosing square (2R)^2, pi/4) and ``square_acceptance`` (for halton the fraction of the
    square's points that fell inside the disc, which tends to pi/4; None for hexapolar). A system whose exit pupil is at
    infinity (image-space telecentric) is refused.
    """
    op = "exit_pupil_samples"
    _system(system, op)
    n = _int(n, "n", op, 1, MAX_PUPIL)
    pattern = _choice(pattern, "pattern", op, PATTERNS)
    wl = _wavelength(system, wavelength_um, op)
    geo = _geometry(system, wl, op=op)
    uv, wt, acc = _unit_pupil(n, pattern)
    R = geo["xp_radius"]
    return {"xy_mm": uv * R, "uv": uv, "weights_mm2": wt * R * R, "z_mm": float(geo["z_xp"]), "radius_mm": R,
            "position_mm": geo["xp_position"], "area_mm2": math.pi * R * R,
            "area_ratio": float(wt.sum() * R * R / (2.0 * R) ** 2), "square_acceptance": acc, "pattern": pattern,
            "n": int(len(uv)), "wavelength_um": float(wl)}


# --------------------------------------------------------------------------- sensor -> object space
def trace_sensor_rays(system, pixel_xy_mm=None, pupil_xy_mm=None, wavelength_um=None, defocus_mm=0.0, fresnel=False,
                      focus_mm=None) -> dict:
    """Trace rays from sensor points through exit-pupil points **backwards** to object space -> dict.

    *pixel_xy_mm* (M, 2) are points ``(x, y)`` in the image plane (lens-frame axes, the image is inverted); *pupil_xy_mm* (K, 2)
    are points in the exit-pupil plane (default: 16 hexapolar samples of :func:`exit_pupil_samples`). All M x K
    pairs are traced through every surface from the last to the first (Snell's law at *wavelength_um* with the
    dispersion of each medium, conics and aspheres, mirrors, the semi-diameters as apertures, total internal
    reflection); the sensor plane is the system's image plane (or the paraxial image of an object at *focus_mm*) moved by
    *defocus_mm* along the light. The table has ``origin`` / ``direction`` (M, K, 3): where the ray leaves the first surface and
    its unit direction into the scene (NaN where lost), ``transmission`` (M, K) - 1 for a ray that gets out, or with
    ``fresnel=True`` the product of the unpolarised Fresnel transmittances of the refracting surfaces (no coating, no
    absorption), 0 for a lost ray - ``vignetted`` (M, K) (any loss: a semi-diameter, a miss, TIR), ``tir``, ``geometry_mm2``
    (``cos^2(theta) / d^2`` of the pupil sample seen from the sensor point, the weight of the irradiance integral), ``z_sensor_mm``,
    ``z_pupil_mm`` and ``wavelength_um``. Reversibility is exact: a forward ray from ``raytrace.ray_bundle`` traced back from its
    image point through its exit-pupil point returns to its entrance point (tested to 1e-9 mm and 1e-12 in direction).
    """
    op = "trace_sensor_rays"
    _system(system, op)
    wl = _wavelength(system, wavelength_um, op)
    df = _real(defocus_mm, "defocus_mm", op)
    if not isinstance(fresnel, (bool, np.bool_)):
        raise ValueError("%s: fresnel must be True or False, got %r" % (op, fresnel))
    fm = None if focus_mm is None else _real(focus_mm, "focus_mm", op, lo=0.0, lo_open=True)
    geo = _geometry(system, wl, df, fm, op)
    if pixel_xy_mm is None:
        efl = geo["para"]["efl"]
        yy = 0.05 * abs(efl) if math.isfinite(efl) else 1.0
        pixel_xy_mm = [[0.0, 0.0], [0.0, yy]]
    px = _array(pixel_xy_mm, "pixel_xy_mm", op, shape_tail=(2,), ndim=2)
    if pupil_xy_mm is None:
        pupil_xy_mm = exit_pupil_samples(system, 16, "hexapolar", wl)["xy_mm"]
    pp = _array(pupil_xy_mm, "pupil_xy_mm", op, shape_tail=(2,), ndim=2)
    M, K = len(px), len(pp)
    if M * K > MAX_RAY_SAMPLES // 16:
        raise ValueError("%s: %d x %d = %d rays is over the cap %d" % (op, M, K, M * K, MAX_RAY_SAMPLES // 16))
    S = np.concatenate([px, np.full((M, 1), geo["z_img"])], 1)
    U = np.concatenate([pp, np.full((K, 1), geo["z_xp"])], 1)
    V = U[None, :, :] - S[:, None, :]
    dist = np.linalg.norm(V, axis=2)
    if np.any(dist <= 0.0):
        raise ValueError("%s: a sensor point lies in the exit-pupil plane" % op)
    D = (V / dist[..., None]).reshape(-1, 3)
    P0 = np.repeat(S, K, axis=0)
    o, d, tr, ok, tir = _trace_back(system, geo, P0, D, fresnel)
    cos_t = np.abs(V[..., 2]) / dist
    return {"origin": o.reshape(M, K, 3), "direction": d.reshape(M, K, 3), "transmission": tr.reshape(M, K),
            "vignetted": (~ok).reshape(M, K), "tir": tir.reshape(M, K), "geometry_mm2": cos_t ** 2 / dist ** 2,
            "z_sensor_mm": float(geo["z_img"]), "z_pupil_mm": float(geo["z_xp"]), "wavelength_um": float(wl),
            "fresnel": bool(fresnel)}


def _intersect_mla_surface(surface, ray_origins, ray_dirs, *, reject_boundary=True):
    """Intersect rays with a periodic spherical-cap ``kind='mla'`` surface.

    The surface vertex plane is local ``z=0``.  Newton iteration uses the sag
    and normal of the selected lenslet; the selected ``lenslet_index`` is part
    of the result.  A hit on a Voronoi boundary is rejected by default because
    two surface normals exist there.
    """
    from plenoptic import mla_sag_normal
    P = _array(ray_origins, "ray_origins", "_intersect_mla_surface", shape_tail=(3,), ndim=2)
    D = _array(ray_dirs, "ray_dirs", "_intersect_mla_surface", shape_tail=(3,), ndim=2)
    if P.shape != D.shape:
        raise ValueError("intersect_mla_surface: ray_origins and ray_dirs must have the same shape")
    norm = np.linalg.norm(D, axis=1)
    if np.any(norm <= 0):
        raise ValueError("intersect_mla_surface: ray_dirs contains a zero vector")
    D = D / norm[:, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        t = -P[:, 2] / D[:, 2]
    for _ in range(20):
        Q = P + t[:, None] * D
        h = mla_sag_normal(surface, Q[:, :2], reject_boundary=False)
        f = Q[:, 2] - h["sag_mm"]
        df = np.sum(h["normal"] * D, axis=1) / h["normal"][:, 2]
        step = np.divide(f, df, out=np.full_like(f, np.nan), where=np.abs(df) > 1e-15)
        t -= step
        if np.nanmax(np.abs(step)) < 1e-12:
            break
    Q = P + t[:, None] * D
    hit = mla_sag_normal(surface, Q[:, :2], reject_boundary=False)
    valid = np.isfinite(t) & (t >= -1e-9) & hit["valid"]
    if reject_boundary and hit["boundary_count"]:
        raise ValueError("intersect_mla_surface: %d ray(s) hit a lenslet boundary" % hit["boundary_count"])
    return {"distance_mm": np.where(valid, t, np.nan), "point_mm": np.where(valid[:, None], Q, np.nan),
            "normal": hit["normal"], "lenslet_index": hit["lenslet_index"], "valid": valid,
            "boundary": hit["boundary"], "boundary_count": hit["boundary_count"]}


# --------------------------------------------------------------------------- the scene
_OBJ_KEYS = {"plane": {"type", "point_mm", "z_mm", "normal", "up", "size_mm", "albedo", "specular", "shininess", "emission", "name"},
             "sphere": {"type", "center_mm", "radius_mm", "albedo", "specular", "shininess", "emission", "name"},
             "mesh": {"type", "vertices_mm", "faces", "albedo", "specular", "shininess", "emission", "name"}}
_LIGHT_KEYS = {"directional": {"type", "to_light", "irradiance_W_m2_nm"},
               "point": {"type", "position_mm", "intensity_W_sr_nm"}}
_SOURCE_KEYS = {"position_mm", "intensity_W_sr_nm", "name"}
_EPS_T = 1e-9


def _spectrum(v, name, op, allow_rgb=False):
    """A scalar, or ``{"nm": [...], "value": [...]}``, or (``allow_rgb``) an (R, G, B) triple -> a normal form."""
    if isinstance(v, dict):
        if set(v) != {"nm", "value"}:
            raise ValueError("%s: %s as a dict needs exactly the keys 'nm' and 'value'" % (op, name))
        nm = _array(v["nm"], name + " nm", op, ndim=1)
        val = _array(v["value"], name + " value", op, ndim=1)
        if nm.shape != val.shape or nm.size < 2 or np.any(np.diff(nm) <= 0.0) or np.any(nm <= 0.0) or np.any(val < 0.0):
            raise ValueError("%s: %s needs >= 2 increasing positive wavelengths and non-negative values" % (op, name))
        return {"nm": nm, "value": val}
    if allow_rgb and not np.isscalar(v) and np.asarray(v).shape == (3,):
        rgb = _array(v, name, op, ndim=1)
        if np.any(rgb < 0.0):
            raise ValueError("%s: %s must be non-negative" % (op, name))
        return {"rgb": rgb}
    return _real(v, name, op, lo=0.0)


def _spec_at(spec, wl_um, name="spectrum"):
    """The value of a normalised spectrum at *wl_um*; a tabulated one is not extrapolated."""
    if isinstance(spec, dict) and "nm" in spec:
        nm = 1000.0 * wl_um
        if nm < spec["nm"][0] - 1e-9 or nm > spec["nm"][-1] + 1e-9:
            raise ValueError("%s covers %.4g-%.4g nm but %.4g nm is asked (no extrapolation)" % (name, spec["nm"][0], spec["nm"][-1], nm))
        return float(np.interp(nm, spec["nm"], spec["value"]))
    if isinstance(spec, dict):
        wb = np.interp(wl_um, RGB_ANCHORS_UM, [1.0, 0.0, 0.0])
        wg = np.interp(wl_um, RGB_ANCHORS_UM, [0.0, 1.0, 0.0])
        wr = np.interp(wl_um, RGB_ANCHORS_UM, [0.0, 0.0, 1.0])
        return float(wr * spec["rgb"][0] + wg * spec["rgb"][1] + wb * spec["rgb"][2])
    return float(spec)


def _unit3(v, name, op):
    a = _array(v, name, op, ndim=1)
    if a.shape != (3,) or np.linalg.norm(a) <= 0.0:
        raise ValueError("%s: %s must be a non-zero 3-vector, got %r" % (op, name, v))
    return a / np.linalg.norm(a)


def _point3(v, name, op):
    a = _array(v, name, op, ndim=1)
    if a.shape != (3,):
        raise ValueError("%s: %s must be a 3-vector (x, y, z) in mm, got %r" % (op, name, v))
    return a


def _norm_object(ob, i, op):
    if not isinstance(ob, dict) or ob.get("type") not in _OBJ_KEYS:
        raise ValueError("%s: object %d needs a 'type' of %s" % (op, i, sorted(_OBJ_KEYS)))
    kind = ob["type"]
    extra = set(ob) - _OBJ_KEYS[kind]
    if extra:
        raise ValueError("%s: object %d (%s) has unknown key(s) %s (it takes %s)" % (op, i, kind, sorted(extra), sorted(_OBJ_KEYS[kind])))
    out = {"type": kind, "name": str(ob.get("name", "%s%d" % (kind, i)))}
    alb = ob.get("albedo", 0.5)
    tex = None
    if kind == "plane" and not np.isscalar(alb) and not isinstance(alb, dict) and np.asarray(alb).ndim >= 2:
        tex = _array(alb, "object %d albedo texture" % i, op)
        if tex.ndim not in (2, 3) or (tex.ndim == 3 and tex.shape[2] != 3) or min(tex.shape[:2]) < 2 or np.any(tex < 0.0):
            raise ValueError("%s: object %d albedo texture must be (H, W) or (H, W, 3), non-negative, at least 2 x 2" % (op, i))
        out["albedo"] = None
        out["texture"] = tex
    else:
        out["albedo"] = _spectrum(alb, "object %d albedo" % i, op, allow_rgb=True)
        out["texture"] = None
    out["specular"] = _real(ob.get("specular", 0.0), "object %d specular" % i, op, lo=0.0)
    out["shininess"] = _real(ob.get("shininess", 32.0), "object %d shininess" % i, op, lo=1.0)
    out["emission"] = _spectrum(ob.get("emission", 0.0), "object %d emission" % i, op)
    if kind == "plane":
        if "z_mm" in ob and "point_mm" in ob:
            raise ValueError("%s: object %d: give z_mm or point_mm, not both" % (op, i))
        pt = _point3(ob["point_mm"], "point_mm", op) if "point_mm" in ob else np.array([0.0, 0.0, _real(ob.get("z_mm", -1000.0), "z_mm", op)])
        nrm = _unit3(ob.get("normal", (0.0, 0.0, 1.0)), "normal", op)
        up = _unit3(ob.get("up", (0.0, 1.0, 0.0)), "up", op)
        ux = np.cross(up, nrm)
        if np.linalg.norm(ux) < 1e-9:
            raise ValueError("%s: object %d: 'up' is parallel to the normal" % (op, i))
        ux /= np.linalg.norm(ux)
        vx = np.cross(nrm, ux)
        size = ob.get("size_mm", None)
        if size is not None:
            size = _array(size, "size_mm", op, ndim=1)
            if size.shape != (2,) or np.any(size <= 0.0):
                raise ValueError("%s: object %d size_mm must be a positive (width, height)" % (op, i))
        if tex is not None and size is None:
            raise ValueError("%s: object %d has a texture and needs size_mm" % (op, i))
        out.update({"point": pt, "normal": nrm, "ux": ux, "vx": vx, "size": size})
    elif kind == "sphere":
        out["center"] = _point3(ob["center_mm"], "center_mm", op)
        out["radius"] = _real(ob["radius_mm"], "radius_mm", op, lo=0.0, lo_open=True)
    else:
        v = _array(ob["vertices_mm"], "vertices_mm", op, shape_tail=(3,), ndim=2)
        f = np.asarray(ob["faces"])
        if f.ndim != 2 or f.shape[1] != 3 or f.dtype.kind not in "iu" or f.min() < 0 or f.max() >= len(v) or len(f) < 1:
            raise ValueError("%s: object %d faces must be an (F, 3) integer array indexing the vertices" % (op, i))
        v0 = v[f[:, 0]]
        e1 = v[f[:, 1]] - v0
        e2 = v[f[:, 2]] - v0
        fn = np.cross(e1, e2)
        ln = np.linalg.norm(fn, axis=1)
        if np.any(ln <= 1e-15):
            raise ValueError("%s: object %d has a degenerate (zero-area) triangle" % (op, i))
        out.update({"v0": v0, "e1": e1, "e2": e2, "fn": fn / ln[:, None]})
    return out


def lens_scene(objects=None, lights=None, sources=None, background=0.0, ambient=None, shadows=True) -> dict:
    """Build and validate a simple 3-D scene for :func:`render_scene_through_lens` -> dict (the ``scene`` table).

    *objects* is a list of dicts. ``{"type": "plane", "z_mm": -1000, "size_mm": (w, h), "albedo": ...}`` is a plane facing the lens
    (``point_mm`` and ``normal`` / ``up`` tilt it; with ``size_mm`` it is the rectangle around the point, without it it is infinite)
    whose ``albedo`` may be a **texture** ``(H, W)`` or ``(H, W, 3)`` mapped onto the rectangle with bilinear sampling
    (row 0 at the top, ``up`` is the picture's up). ``{"type": "sphere", "center_mm": (x, y, z), "radius_mm": r}`` and
    ``{"type": "mesh", "vertices_mm": (V, 3), "faces": (F, 3)}`` (Moller-Trumbore, flat shading) take the same material keys:
    ``albedo`` (a number, an (R, G, B) triple at the effective wavelengths 0.61 / 0.54 / 0.465 um, or ``{"nm", "value"}``),
    ``specular`` (the weight ``ks`` of a normalised Blinn-Phong lobe, whose albedo is about ``ks``), ``shininess`` and ``emission``
    (spectral radiance of a self-luminous surface, W m^-2 sr^-1 nm^-1). *lights*: ``{"type": "directional", "to_light": (x, y, z),
    "irradiance_W_m2_nm": E}`` (E at normal incidence) or ``{"type": "point", "position_mm": ..., "intensity_W_sr_nm": I}``; shadow
    rays are traced when *shadows* is true. *ambient* is a spectral irradiance (default 0, or 0.05 in the demo scene) that lights every surface without shadows;
    *background* is the spectral radiance a ray that hits nothing sees. *sources* are bright **points** seen by the camera,
    ``{"position_mm": (x, y, z), "intensity_W_sr_nm": I}``: they are splatted by forward ray tracing (point sources cannot be
    found by random rays from the sensor), do not occlude and cast no shadows. With nothing given the table is a demo: a 2 mm
    checkerboard plane, a glossy sphere, one directional light and a little ambient light. Unknown keys, a degenerate
    triangle, a negative albedo or a tabulated spectrum outside its range are refused.
    """
    op = "lens_scene"
    demo = objects is None and lights is None and sources is None
    if demo:
        n = 16
        sq = 32
        yy, xx = np.mgrid[0:n * sq, 0:n * sq]
        chk = 0.08 + 0.80 * (((yy // sq) + (xx // sq)) % 2)
        objects = [{"type": "plane", "z_mm": -1000.0, "size_mm": (32.0, 32.0), "albedo": chk, "name": "checker"},
                   {"type": "sphere", "center_mm": (3.0, 2.0, -800.0), "radius_mm": 1.0, "albedo": (0.75, 0.2, 0.15),
                    "specular": 0.3, "shininess": 40.0, "name": "ball"}]
        lights = [{"type": "directional", "to_light": (0.3, 0.4, 1.0), "irradiance_W_m2_nm": 1.0}]
        if ambient is None:
            ambient = 0.05
    if not isinstance(objects, (list, tuple)):
        raise ValueError("%s: objects must be a list of dicts, got %r" % (op, type(objects).__name__))
    objs = [_norm_object(o, i, op) for i, o in enumerate(objects)]
    lts = []
    for i, li in enumerate(lights or []):
        if not isinstance(li, dict) or li.get("type") not in _LIGHT_KEYS:
            raise ValueError("%s: light %d needs a 'type' of %s" % (op, i, sorted(_LIGHT_KEYS)))
        extra = set(li) - _LIGHT_KEYS[li["type"]]
        if extra:
            raise ValueError("%s: light %d has unknown key(s) %s" % (op, i, sorted(extra)))
        if li["type"] == "directional":
            lts.append({"type": "directional", "to_light": _unit3(li["to_light"], "to_light", op),
                        "E": _spectrum(li.get("irradiance_W_m2_nm", 1.0), "irradiance_W_m2_nm", op)})
        else:
            lts.append({"type": "point", "pos": _point3(li["position_mm"], "position_mm", op),
                        "I": _spectrum(li.get("intensity_W_sr_nm", 1.0), "intensity_W_sr_nm", op)})
    srcs = []
    for i, so in enumerate(sources or []):
        if not isinstance(so, dict) or "position_mm" not in so:
            raise ValueError("%s: source %d needs 'position_mm'" % (op, i))
        extra = set(so) - _SOURCE_KEYS
        if extra:
            raise ValueError("%s: source %d has unknown key(s) %s" % (op, i, sorted(extra)))
        pos = _point3(so["position_mm"], "position_mm", op)
        if pos[2] >= 0.0:
            raise ValueError("%s: source %d must be in front of the lens (z < 0), got z = %g" % (op, i, pos[2]))
        srcs.append({"pos": pos, "I": _spectrum(so.get("intensity_W_sr_nm", 1.0), "intensity_W_sr_nm", op),
                     "name": str(so.get("name", "source%d" % i))})
    if not isinstance(shadows, (bool, np.bool_)):
        raise ValueError("%s: shadows must be True or False" % op)
    ambient = 0.0 if ambient is None else ambient
    return {"kind": "lens_scene", "objects": objs, "lights": lts, "sources": srcs,
            "background": _spectrum(background, "background", op), "ambient": _spectrum(ambient, "ambient", op),
            "shadows": bool(shadows)}


def _check_scene(scene, op):
    if scene is None:
        return lens_scene()
    if not isinstance(scene, dict) or scene.get("kind") != "lens_scene":
        raise ValueError("%s: scene must be the table returned by lens_scene(), got %r" % (op, type(scene).__name__))
    return scene


# --------------------------------------------------------------------------- intersections
def _hit_plane(ob, o, d):
    n = ob["normal"]
    with np.errstate(all="ignore"):
        den = d @ n
        t = ((ob["point"] - o) @ n) / den
    t = np.where((np.abs(den) > 1e-14) & (t > _EPS_T), t, INF)
    if ob["size"] is not None:
        fin = np.isfinite(t)
        P = o + np.where(fin, t, 0.0)[:, None] * d - ob["point"]
        u, v = P @ ob["ux"], P @ ob["vx"]
        inside = (np.abs(u) <= 0.5 * ob["size"][0]) & (np.abs(v) <= 0.5 * ob["size"][1])
        t = np.where(inside, t, INF)
    return t, None


def _hit_sphere(ob, o, d):
    oc = o - ob["center"]
    b = np.sum(oc * d, axis=1)
    c2 = np.sum(oc * oc, axis=1) - ob["radius"] ** 2
    disc = b * b - c2
    with np.errstate(invalid="ignore"):
        sq = np.sqrt(np.where(disc >= 0.0, disc, np.nan))
    t1, t2 = -b - sq, -b + sq
    t = np.where(t1 > _EPS_T, t1, np.where(t2 > _EPS_T, t2, INF))
    return np.where(np.isfinite(t), t, INF), None


def _hit_mesh(ob, o, d):
    R, F = len(o), len(ob["v0"])
    best = np.full(R, INF)
    idx = np.full(R, -1, dtype=np.int64)
    fc = max(1, min(F, 200000 // max(R, 1)))
    for f0 in range(0, F, fc):
        v0, e1, e2 = ob["v0"][f0:f0 + fc], ob["e1"][f0:f0 + fc], ob["e2"][f0:f0 + fc]
        with np.errstate(all="ignore"):
            pv = np.cross(d[:, None, :], e2[None, :, :])
            det = np.sum(e1[None] * pv, axis=2)
            inv = 1.0 / det
            tv = o[:, None, :] - v0[None]
            u = np.sum(tv * pv, axis=2) * inv
            qv = np.cross(tv, e1[None])
            v = np.sum(d[:, None, :] * qv, axis=2) * inv
            t = np.sum(e2[None] * qv, axis=2) * inv
            good = (np.abs(det) > 1e-14) & (u >= 0.0) & (v >= 0.0) & (u + v <= 1.0) & (t > _EPS_T)
        t = np.where(good, t, INF)
        j = np.argmin(t, axis=1)
        tj = t[np.arange(R), j]
        upd = tj < best
        best = np.where(upd, tj, best)
        idx = np.where(upd, f0 + j, idx)
    return best, idx


_HIT = {"plane": _hit_plane, "sphere": _hit_sphere, "mesh": _hit_mesh}


def _nearest(scene, o, d, tmax=INF):
    """Nearest hit of rays (o, d) closer than *tmax* (scalar or per ray): t, object index (-1 = none), per-object aux."""
    N = len(o)
    best = np.full(N, INF)
    oid = np.full(N, -1, dtype=np.int64)
    aux = []
    for k, ob in enumerate(scene["objects"]):
        t, a = _HIT[ob["type"]](ob, o, d)
        t = np.where(t < tmax, t, INF)
        upd = t < best
        best = np.where(upd, t, best)
        oid = np.where(upd, k, oid)
        aux.append(a)
    return best, oid, aux


def _normals(ob, P, d, aux_ids):
    if ob["type"] == "plane":
        n = np.tile(ob["normal"], (len(P), 1))
    elif ob["type"] == "sphere":
        n = (P - ob["center"]) / ob["radius"]
    else:
        n = ob["fn"][aux_ids]
    flip = np.sum(n * d, axis=1) > 0.0
    n = np.where(flip[:, None], -n, n)
    return n


def _bilinear(tex, u, v, size):
    H, W = tex.shape[:2]
    col = np.clip((u / size[0] + 0.5) * W - 0.5, 0.0, W - 1.0)
    row = np.clip((0.5 - v / size[1]) * H - 0.5, 0.0, H - 1.0)
    c0 = np.minimum(np.floor(col).astype(np.int64), W - 2)
    r0 = np.minimum(np.floor(row).astype(np.int64), H - 2)
    fc, fr = col - c0, row - r0
    if tex.ndim == 3:
        fc, fr = fc[:, None], fr[:, None]
    return ((1 - fr) * ((1 - fc) * tex[r0, c0] + fc * tex[r0, c0 + 1])
            + fr * ((1 - fc) * tex[r0 + 1, c0] + fc * tex[r0 + 1, c0 + 1]))


def _illum_rel(illuminant, wls, op):
    """Relative spectral shape of the lights at each wavelength (1 at 0.55 um); None = flat."""
    if illuminant is None:
        return np.ones(len(wls))
    a = _array(illuminant, "illuminant", op, shape_tail=(2,), ndim=2)
    if len(a) < 2 or np.any(np.diff(a[:, 0]) <= 0.0) or np.any(a[:, 1] < 0.0):
        raise ValueError("%s: illuminant must be pairs (nm, value), increasing wavelengths, non-negative values" % op)
    nm = 1000.0 * np.asarray(wls)
    need = np.concatenate([nm, [550.0]])
    if need.min() < a[0, 0] - 1e-9 or need.max() > a[-1, 0] + 1e-9:
        raise ValueError("%s: illuminant covers %.4g-%.4g nm but %.4g-%.4g nm is needed (no extrapolation)" % (op, a[0, 0], a[-1, 0], need.min(), need.max()))
    ref = np.interp(550.0, a[:, 0], a[:, 1])
    if ref <= 0.0:
        raise ValueError("%s: the illuminant is zero at 550 nm, the normalisation wavelength" % op)
    return np.interp(nm, a[:, 0], a[:, 1]) / ref


def _radiance(scene, o, d, wls, rel):
    """Spectral radiance (N, len(wls)) seen along rays (o, d): the shading of the nearest hit (rays must be finite)."""
    N, nw = len(o), len(wls)
    out = np.zeros((N, nw))
    for j, w in enumerate(wls):
        out[:, j] = _spec_at(scene["background"], w, "background")
    t, oid, aux = _nearest(scene, o, d)
    hit = oid >= 0
    for k, ob in enumerate(scene["objects"]):
        ids = np.nonzero(oid == k)[0]
        if len(ids) == 0:
            continue
        dk = d[ids]
        P = o[ids] + t[ids, None] * dk
        a_k = None if aux[k] is None else aux[k][ids]
        n = _normals(ob, P, dk, a_k)
        if ob["type"] == "plane" and ob["texture"] is not None:
            q = P - ob["point"]
            samp = _bilinear(ob["texture"], q @ ob["ux"], q @ ob["vx"], ob["size"])
        else:
            samp = None
        Po = P + n * (1e-6 * np.maximum(1.0, np.linalg.norm(P, axis=1)))[:, None]
        # light vectors and shadows are shared by all wavelengths
        lv = []
        for li in scene["lights"]:
            if li["type"] == "directional":
                Lv = np.tile(li["to_light"], (len(ids), 1))
                dist = np.full(len(ids), INF)
            else:
                vec = li["pos"] - P
                dist = np.linalg.norm(vec, axis=1)
                Lv = vec / dist[:, None]
            cosl = np.clip(np.sum(n * Lv, axis=1), 0.0, None)
            vis = np.ones(len(ids))
            if scene["shadows"] and np.any(cosl > 0.0):
                ts, _o2, _a2 = _nearest(scene, Po, Lv, tmax=dist)
                vis = np.where(np.isfinite(ts), 0.0, 1.0)
            Hv = Lv - dk
            Hv = Hv / np.maximum(np.linalg.norm(Hv, axis=1, keepdims=True), 1e-300)
            lobe = np.clip(np.sum(n * Hv, axis=1), 0.0, None) ** ob["shininess"]
            lv.append((li, cosl * vis, lobe, dist))
        for j, w in enumerate(wls):
            if samp is None:
                rho = _spec_at(ob["albedo"], w, "albedo")
            elif samp.ndim == 1:
                rho = samp
            else:
                wb = np.interp(w, RGB_ANCHORS_UM, [1.0, 0.0, 0.0])
                wg = np.interp(w, RGB_ANCHORS_UM, [0.0, 1.0, 0.0])
                wr = np.interp(w, RGB_ANCHORS_UM, [0.0, 0.0, 1.0])
                rho = wr * samp[:, 0] + wg * samp[:, 1] + wb * samp[:, 2]
            L = _spec_at(ob["emission"], w, "emission") + rho * _spec_at(scene["ambient"], w, "ambient") * rel[j] / math.pi
            for li, cv, lobe, dist in lv:
                if li["type"] == "directional":
                    E = _spec_at(li["E"], w, "irradiance") * rel[j]
                else:
                    E = _spec_at(li["I"], w, "intensity") * rel[j] / (dist * 1e-3) ** 2
                L = L + E * cv * (rho / math.pi + ob["specular"] * (ob["shininess"] + 8.0) / (8.0 * math.pi) * lobe)
            out[ids, j] = L
    return out, hit, t, oid


def scene_radiance(ray_origins=None, ray_dirs=None, scene=None, wavelengths_um=None, illuminant=None) -> dict:
    """Radiance along object-space rays hitting a :func:`lens_scene` -> dict.

    *ray_origins* / *ray_dirs* are (N, 3) points (mm) and directions (normalised here); *wavelengths_um* is a number or a list
    (default the three F, d, C lines). Every ray takes its nearest hit (plane rectangle, sphere, Moller-Trumbore triangle) and
    the radiance ``emission + rho(lambda) / pi * (E_ambient + sum_lights E cos(theta_l) * visibility)`` plus the Blinn-Phong lobe
    ``ks (s + 8) / (8 pi) (n . h)^s E cos(theta_l)`` per light (the normalised Blinn-Phong lobe: its albedo is about ``ks``); the visibility is a shadow ray to the light (zero if anything is
    in the way, if *shadows* is on). A ray that hits nothing sees the scene background. *illuminant* (pairs ``(nm, value)``) is the
    relative spectral shape that multiplies the lights and the ambient light (1 at 550 nm). A purely Lambertian surface
    never exceeds ``E rho / pi`` (tested to 1e-12). The table has ``radiance`` (N, K) in W m^-2 sr^-1 nm^-1, ``hit`` (N,),
    ``t_mm`` (N, inf for a miss), ``object_index`` (N, -1 for none) and ``wavelengths_um``. NaN rays (lost in the lens) get NaN.
    """
    op = "scene_radiance"
    scene = _check_scene(scene, op)
    if ray_origins is None or ray_dirs is None:
        ray_origins = np.zeros((5, 3))
        ray_dirs = np.array([[0.0, 0.0, -1.0], [0.002, 0.0, -1.0], [-0.002, 0.003, -1.0], [0.0, -0.004, -1.0], [0.1, 0.1, 1.0]])
    o = np.asarray(ray_origins, dtype=np.float64)
    d = np.asarray(ray_dirs, dtype=np.float64)
    if o.ndim != 2 or o.shape[1] != 3 or d.shape != o.shape or len(o) < 1:
        raise ValueError("%s: ray_origins and ray_dirs must both be (N, 3), got %r and %r" % (op, o.shape, d.shape))
    if wavelengths_um is None:
        wls = list(WL_BANDS)
    elif np.isscalar(wavelengths_um):
        wls = [_real(wavelengths_um, "wavelengths_um", op, lo=0.2, hi=20.0)]
    else:
        wls = [_real(w, "wavelengths_um", op, lo=0.2, hi=20.0) for w in wavelengths_um]
        if not wls:
            raise ValueError("%s: wavelengths_um is empty" % op)
    finite = np.all(np.isfinite(o), axis=1) & np.all(np.isfinite(d), axis=1)
    nd = np.linalg.norm(np.where(finite[:, None], d, 1.0), axis=1)
    if np.any(nd[finite] <= 0.0):
        raise ValueError("%s: a ray direction has zero length" % op)
    rel = _illum_rel(illuminant, wls, op)
    N = len(o)
    rad = np.full((N, len(wls)), np.nan)
    hit = np.zeros(N, bool)
    tt = np.full(N, INF)
    oid = np.full(N, -1, dtype=np.int64)
    f = np.nonzero(finite)[0]
    if len(f):
        r_, h_, t_, i_ = _radiance(scene, o[f], d[f] / nd[f, None], wls, rel)
        rad[f], hit[f], tt[f], oid[f] = r_, h_, t_, i_
    return {"radiance": rad, "hit": hit, "t_mm": tt, "object_index": oid, "wavelengths_um": np.array(wls)}


# --------------------------------------------------------------------------- the sensor
_SENSOR_DEFAULT = {"pixel_pitch_um": 5.0, "size": (48, 64), "qe": 0.6, "full_well": 20000.0, "read_noise_e": 2.0,
                   "dark_e": 0.0, "bits": 12, "center_mm": (0.0, 0.0)}


#: rays traced per block (memory, not a result: the sum over a pixel does not depend on it)
_BLOCK_RAYS = 200000


def _sensor_params(sensor, op):
    d = dict(_SENSOR_DEFAULT)
    if sensor is None:
        pass
    elif not isinstance(sensor, dict):
        raise ValueError("%s: sensor must be a dict with some of %s, got %r" % (op, sorted(d), type(sensor).__name__))
    else:
        extra = set(sensor) - set(d)
        if extra:
            raise ValueError("%s: unknown sensor key(s) %s (choose from %s)" % (op, sorted(extra), sorted(d)))
        d.update(sensor)
    size = d["size"]
    try:
        h, w = (int(size[0]), int(size[1]))
    except (TypeError, ValueError, IndexError):
        raise ValueError("%s: sensor size must be (rows, cols), got %r" % (op, size)) from None
    if not (1 <= h <= 4096 and 1 <= w <= 4096):
        raise ValueError("%s: sensor size must be within 1..4096 pixels, got %r" % (op, size))
    qe = d["qe"]
    if isinstance(qe, dict):
        qe = _spectrum(qe, "qe", op)
        if np.any(qe["value"] > 1.0):
            raise ValueError("%s: qe must lie in [0, 1]" % op)
    else:
        qe = _real(qe, "qe", op, lo=0.0, hi=1.0)
    cen = _array(d["center_mm"], "center_mm", op, ndim=1)
    if cen.shape != (2,):
        raise ValueError("%s: center_mm must be a pair (x, y) of the sensor centre in the image plane" % op)
    return {"center": (float(cen[0]), float(cen[1])), "pitch_um": _real(d["pixel_pitch_um"], "pixel_pitch_um", op, lo=0.1, hi=20000.0), "h": h, "w": w, "qe": qe,
            "full_well": _real(d["full_well"], "full_well", op, lo=1.0), "read_e": _real(d["read_noise_e"], "read_noise_e", op, lo=0.0),
            "dark_e": _real(d["dark_e"], "dark_e", op, lo=0.0), "bits": _int(d["bits"], "bits", op, 1, 16)}


def _wavelength_list(wavelengths, op):
    if wavelengths is None:
        return list(WL_BANDS)
    if np.isscalar(wavelengths):
        return [_real(wavelengths, "wavelengths", op, lo=0.2, hi=20.0)]
    wls = [_real(w, "wavelengths", op, lo=0.2, hi=20.0) for w in wavelengths]
    if not wls or len(set(wls)) != len(wls):
        raise ValueError("%s: wavelengths must be a non-empty list of distinct values" % op)
    return wls


def _band_widths(wls, band_nm, op):
    if band_nm is not None:
        b = np.atleast_1d(np.asarray(band_nm, dtype=np.float64))
        if b.size == 1:
            b = np.full(len(wls), float(b[0]))
        if b.shape != (len(wls),) or not np.all(np.isfinite(b)) or np.any(b <= 0.0):
            raise ValueError("%s: band_nm must be one positive width or one per wavelength" % op)
        return b
    if len(wls) == 1:
        return np.array([1.0])
    nm = 1000.0 * np.asarray(wls)
    order = np.argsort(nm)
    g = np.abs(np.gradient(nm[order]))
    out = np.empty(len(wls))
    out[order] = g
    return out


def _electrons(spec_power, wl, band_nm, exposure_s, qe):
    """Electrons from a spectral power (W per nm of band): P dlambda t (lambda / hc) QE."""
    return spec_power * band_nm * exposure_s * (wl * 1e-6 / HC) * _spec_at(qe, wl, "qe")


def _pupil_for(pattern, n, uv_given, op):
    if uv_given is not None:
        uv = _array(uv_given, "pupil_uv", op, shape_tail=(2,), ndim=2)
        if np.any(np.sum(uv * uv, axis=1) > 1.0 + 1e-12):
            raise ValueError("%s: pupil_uv must lie in the unit disc" % op)
        return uv, np.full(len(uv), math.pi / len(uv))
    uv, wt, _acc = _unit_pupil(n, pattern)
    return uv, wt


# --------------------------------------------------------------------------- point sources (forward splat)
def _ring_weights(pupil_xy, rings):
    """Area share of each ray of a hexapolar bundle (the outer ring covers half an annulus), summing to 1."""
    h = 1.0 / rings
    k = np.rint(np.hypot(pupil_xy[:, 0], pupil_xy[:, 1]) * rings).astype(int)
    w = np.empty(len(k))
    cnt = np.bincount(k, minlength=rings + 1)
    for kk in range(rings + 1):
        if kk == 0:
            area = math.pi * (0.5 * h) ** 2
        elif kk < rings:
            area = 2.0 * math.pi * kk * h * h
        else:
            area = math.pi * (1.0 - ((rings - 0.5) * h) ** 2)
        w[k == kk] = area / max(cnt[kk], 1)
    return w / w.sum()


def _solid_angle(rho, d_axial, radius):
    """Solid angle of a disc of *radius* at axial distance *d_axial*, seen from a point *rho* off its axis."""
    dist = math.hypot(rho, d_axial)
    om0 = math.pi * radius * radius * (d_axial / dist) / (dist * dist)
    a = math.atan(radius / dist)
    corr = 2.0 * (1.0 - math.cos(a)) / math.tan(a) ** 2 if a > 1e-8 else 1.0
    return om0 * corr


def _rot2(xy, ang):
    c, s = math.cos(ang), math.sin(ang)
    return np.stack([c * xy[:, 0] - s * xy[:, 1], s * xy[:, 0] + c * xy[:, 1]], 1)


def _to_pixels(xy, sp):
    """Sensor (x, y) mm -> fractional (row, col) of the upright picture."""
    cy, cx = (sp["h"] - 1) / 2.0, (sp["w"] - 1) / 2.0
    p = sp["pitch_um"] * 1e-3
    return cy + (xy[:, 1] - sp["center"][1]) / p, cx - (xy[:, 0] - sp["center"][0]) / p


def _tent(rows, cols, weights, h, w):
    """Spread weighted points over their four nearest pixels (bilinear); energy outside the picture is dropped."""
    out = np.zeros(h * w)
    r0 = np.floor(rows).astype(np.int64)
    c0 = np.floor(cols).astype(np.int64)
    fr, fc = rows - r0, cols - c0
    for dr, dc, wt in ((0, 0, (1 - fr) * (1 - fc)), (0, 1, (1 - fr) * fc), (1, 0, fr * (1 - fc)), (1, 1, fr * fc)):
        rr, cc = r0 + dr, c0 + dc
        m = (rr >= 0) & (rr < h) & (cc >= 0) & (cc < w)
        out += np.bincount(rr[m] * w + cc[m], weights=(weights * wt)[m], minlength=h * w)
    return out.reshape(h, w)


def _source_forward(system, geo, pos, wl, rings, rel_weights=True):
    """Forward bundle of a point source at *pos* (mm, z < 0): image-plane points, ray power share and solid angle."""
    if not _axisymmetric(system):
        raise ValueError("point sources need an axisymmetric system (no decenter / tilt): the field is traced along +y and rotated")
    d_obj = -float(pos[2])
    rho = math.hypot(pos[0], pos[1])
    az = math.atan2(pos[1], pos[0])
    sysd = _with_object(system, d_obj)
    b = RT.ray_bundle(sysd, field=rho, rings=rings, wavelength_um=wl, image_mm=geo["image_mm"], kind="hexapolar")
    para = b["para"]
    d_ax = d_obj + para["ep_position"]
    if d_ax <= 0.0 or not math.isfinite(para["ep_radius"]):
        raise ValueError("the source is not in front of the entrance pupil (axial distance %.4g mm)" % d_ax)
    om = _solid_angle(rho, d_ax, para["ep_radius"])
    share = _ring_weights(b["pupil"], rings)
    xy = _rot2(b["image_xy"], az - 0.5 * math.pi)
    return {"xy": xy, "valid": b["valid"], "share": share, "omega_sr": om, "chief_xy": _rot2(b["chief_xy"][None, :], az - 0.5 * math.pi)[0],
            "bundle": b, "rho": rho, "azimuth": az}


def _splat_sources(system, scene, geo, wl, sp, rings, rel):
    """Spectral power per pixel (W per nm) of every point source of the scene at one wavelength."""
    img = np.zeros((sp["h"], sp["w"]))
    for so in scene["sources"]:
        f = _source_forward(system, geo, so["pos"], wl, rings)
        v = f["valid"] & np.all(np.isfinite(f["xy"]), axis=1)
        if not np.any(v):
            continue
        P = _spec_at(so["I"], wl, "intensity") * rel * f["omega_sr"]
        rows, cols = _to_pixels(f["xy"][v], sp)
        img += _tent(rows, cols, P * f["share"][v], sp["h"], sp["w"])
    return img


# --------------------------------------------------------------------------- the photograph
def render_scene_through_lens(system, scene=None, sensor=None, pupil_samples=64, wavelengths=None, exposure_s=1e-4,
                              illuminant=None, seed=0, defocus_mm=0.0, oversample=1, pupil_pattern="halton", pupil_uv=None,
                              pupil_jitter=True, focus_mm=None, add_noise=True, output="float", band_nm=None,
                              source_rings=24) -> dict:
    """Photograph a :func:`lens_scene` through the prescription *system*: sensor-side ray tracing -> dict.

    For every pixel (and ``oversample`` x ``oversample`` points inside it) and every wavelength, the exit pupil is sampled at
    ``pupil_samples`` points (Halton or hexapolar, each pixel's pattern turned by a fixed golden-ratio angle when
    *pupil_jitter* is on, so the noiseless image does not depend on *seed*), each ray is traced backwards through the lens
    (:func:`trace_sensor_rays`), shaded in the scene (:func:`scene_radiance`) and weighted by ``cos^2(theta) / d^2`` times the
    pupil-sample area: the Monte Carlo estimate of ``E = integral L cos(theta) d(omega)`` over the exit pupil
    (Kolb, Mitchell & Hanrahan 1995), times ``(n_image / n_object)^2``. Point ``sources`` of the scene are added by forward
    ray tracing. The spectral irradiance becomes electrons per wavelength,
    ``E dlambda A_pixel t (lambda / hc) QE(lambda)``, and the sum goes through the shot noise, the dark electrons, the read
    noise and the quantiser of ``lensimage._sensor`` (*add_noise* False returns the expected values). *sensor* is a dict
    ``{"pixel_pitch_um", "size": (rows, cols), "qe", "full_well", "read_noise_e", "dark_e", "bits", "center_mm"}`` (``center_mm`` moves the window to another point of a larger sensor); *wavelengths* default to the F, d, C lines
    (each band is as wide as the spacing of the list, or *band_nm*); *illuminant* is the relative spectral shape of the scene's lights (pairs
    ``(nm, value)``); *defocus_mm* moves the sensor along the light (positive = away from the lens) and *focus_mm* puts it at the
    paraxial image of an object at that distance (default: the system's own image plane); *oversample* subdivides each pixel.
    The picture is upright (see the module doc). The table has ``image`` (``float`` in 0..1, or ``uint16`` DN with
    ``output="uint16"``), ``image_noiseless``, ``channels`` / ``channels_noiseless`` (one image per wavelength, own noise), ``electrons_mean`` and
    ``electrons_per_wavelength``, ``irradiance_W_m2_nm`` (K, H, W), ``pupil_transmission`` (H, W: the share of the pupil that is not
    vignetted), the wavelengths and the geometry. Geometric optics only: no diffraction.
    """
    op = "render_scene_through_lens"
    import lensimage as LI
    _system(system, op)
    scene = _check_scene(scene, op)
    sp = _sensor_params(sensor, op)
    npup = _int(pupil_samples, "pupil_samples", op, 1, MAX_PUPIL)
    pat = _choice(pupil_pattern, "pupil_pattern", op, PATTERNS)
    wls = _wavelength_list(wavelengths, op)
    t_exp = _real(exposure_s, "exposure_s", op, lo=0.0, lo_open=True)
    sd = _int(seed, "seed", op, 0, 2 ** 31 - 2)
    df = _real(defocus_mm, "defocus_mm", op)
    os_ = _int(oversample, "oversample", op, 1, 16)
    fm = None if focus_mm is None else _real(focus_mm, "focus_mm", op, lo=0.0, lo_open=True)
    out_kind = _choice(output, "output", op, ("float", "uint16"))
    for nm_, v in (("pupil_jitter", pupil_jitter), ("add_noise", add_noise)):
        if not isinstance(v, (bool, np.bool_)):
            raise ValueError("%s: %s must be True or False" % (op, nm_))
    rings = _int(source_rings, "source_rings", op, 2, 200)
    blk = _BLOCK_RAYS
    bw = _band_widths(wls, band_nm, op)
    rel = _illum_rel(illuminant, wls, op)
    uv, wunit = _pupil_for(pat, npup, pupil_uv, op)
    K = len(uv)
    H, W = sp["h"], sp["w"]
    nsamp = H * W * os_ * os_
    if nsamp * K * len(wls) > MAX_RAY_SAMPLES:
        raise ValueError("%s: %d ray samples is over the cap %d (reduce the size, pupil_samples or oversample)" % (op, nsamp * K * len(wls), MAX_RAY_SAMPLES))
    cy, cx = (H - 1) / 2.0, (W - 1) / 2.0
    p_mm = sp["pitch_um"] * 1e-3
    area_m2 = (sp["pitch_um"] * 1e-6) ** 2
    irr = np.zeros((len(wls), H, W))
    ptrans = np.zeros((H, W))
    B = max(1, blk // K)
    for j, wl in enumerate(wls):
        geo = _geometry(system, wl, df, fm, op)
        R = geo["xp_radius"]
        wmm = wunit * R * R
        n2 = (geo["n_image"] / geo["n_object"]) ** 2
        acc = np.zeros(nsamp)
        vacc = np.zeros(nsamp)
        for s0 in range(0, nsamp, B):
            s1 = min(nsamp, s0 + B)
            idx = np.arange(s0, s1)
            pix, sub = idx // (os_ * os_), idx % (os_ * os_)
            row, col = pix // W, pix % W
            ox, oy = (sub % os_ + 0.5) / os_ - 0.5, (sub // os_ + 0.5) / os_ - 0.5
            sx = sp["center"][0] - (col + ox - cx) * p_mm
            sy = sp["center"][1] + (row + oy - cy) * p_mm
            nb_ = len(idx)
            if pupil_jitter:
                ang = 2.0 * math.pi * np.mod(idx * _PHI, 1.0)
                ca, sa = np.cos(ang)[:, None], np.sin(ang)[:, None]
                pu = ca * uv[None, :, 0] - sa * uv[None, :, 1]
                pv = sa * uv[None, :, 0] + ca * uv[None, :, 1]
            else:
                pu = np.broadcast_to(uv[None, :, 0], (nb_, K))
                pv = np.broadcast_to(uv[None, :, 1], (nb_, K))
            Vx = pu * R - sx[:, None]
            Vy = pv * R - sy[:, None]
            Vz = np.full((nb_, K), geo["z_xp"] - geo["z_img"])
            dist = np.sqrt(Vx * Vx + Vy * Vy + Vz * Vz)
            g = (Vz / dist) ** 2 / dist ** 2
            D = np.stack([Vx / dist, Vy / dist, Vz / dist], 2).reshape(-1, 3)
            P0 = np.stack([np.repeat(sx, K), np.repeat(sy, K), np.full(nb_ * K, geo["z_img"])], 1)
            o, d, tr, ok, _tir = _trace_back(system, geo, P0, D)
            L = np.zeros(nb_ * K)
            if np.any(ok):
                L[ok] = _radiance(scene, o[ok], d[ok], [wl], rel[j:j + 1])[0][:, 0]
            contrib = (L * tr).reshape(nb_, K) * g * wmm[None, :]
            acc[s0:s1] = contrib.sum(axis=1) * n2
            vacc[s0:s1] = (ok.reshape(nb_, K) * wunit[None, :]).sum(axis=1) / wunit.sum()
        irr[j] = acc.reshape(H, W, os_ * os_).mean(axis=2)
        ptrans += vacc.reshape(H, W, os_ * os_).mean(axis=2) / len(wls)
        if scene["sources"]:
            pw = _splat_sources(system, scene, geo, wl, sp, rings, rel[j])
            irr[j] += pw / area_m2
    e_wl = np.stack([_electrons(irr[j] * area_m2, wls[j], bw[j], t_exp, sp["qe"]) for j in range(len(wls))])
    e_tot = e_wl.sum(axis=0)
    levels = (1 << sp["bits"]) - 1
    nz = {"full_well": sp["full_well"], "exposure": 1.0, "dark_e": sp["dark_e"], "read_e": sp["read_e"], "bits": sp["bits"]}

    def quant(e):
        return np.clip(np.floor((e + sp["dark_e"]) / sp["full_well"] * levels + 0.5), 0, levels) / levels

    noiseless = quant(e_tot)
    chan_noiseless = np.stack([quant(e) for e in e_wl])
    if add_noise:
        img = LI._sensor(e_tot / sp["full_well"], nz, sd)
        chans = np.stack([LI._sensor(e_wl[j] / sp["full_well"], nz, sd + 100 * (j + 1)) for j in range(len(wls))])
    else:
        img, chans = noiseless, chan_noiseless
    if out_kind == "uint16":
        img = np.rint(img * levels).astype(np.uint16)
        noiseless = np.rint(noiseless * levels).astype(np.uint16)
    return {"image": img, "image_noiseless": noiseless, "channels": chans, "channels_noiseless": chan_noiseless,
            "electrons_mean": e_tot, "electrons_per_wavelength": e_wl, "irradiance_W_m2_nm": irr,
            "pupil_transmission": ptrans, "wavelengths_um": np.array(wls), "band_nm": bw, "bits": sp["bits"],
            "full_well": sp["full_well"], "pixel_pitch_um": sp["pitch_um"], "image_mm": float(geo["image_mm"]),
            "z_sensor_mm": float(geo["z_img"]), "pupil_samples": int(K), "ray_samples": int(nsamp * K * len(wls)),
            "exposure_s": t_exp, "seed": sd, "noise": bool(add_noise)}


# --------------------------------------------------------------------------- the bokeh footprint
def _hull(points):
    from scipy.spatial import ConvexHull
    if len(points) < 3:
        raise ValueError("fewer than 3 rays got through: the point is fully vignetted")
    h = ConvexHull(points)
    return h, float(h.volume)


def bokeh_shape(system, field_xy_mm=None, defocus_mm=0.5, pupil_samples=512, object_mm=None, wavelength_um=None, grid=64) -> dict:
    """The out-of-focus footprint of a point source - the intersection of the pupil images, the cat's eye -> dict.

    The point sits at *field_xy_mm* in the object plane at *object_mm* (a height in mm; for an object at infinity a pair of angles in degrees;
    default: (0, 8) degrees for an object at infinity, a height of 5 % of the object distance otherwise), the sensor is *defocus_mm* behind the system's image plane.
    A hexapolar pupil bundle of about *pupil_samples* rays is traced forward (``raytrace.ray_bundle``, which stops a ray at every semi-diameter);
    the rays that get through land on the shifted sensor and their convex hull is the footprint. The table has ``polygon_xy_mm`` (the hull,
    counter-clockwise, relative to its centroid, on the sensor axes), ``mask`` (a ``grid x grid`` boolean image of the footprint, ``extent_mm`` wide),
    ``area_mm2``, the same for the on-axis point (``axis_area_mm2``), ``area_ratio`` (cat's eye / on-axis disc), ``vignetting_factor`` (the share of the pupil
    area that gets through relative to the axis, from the ray bundle), ``n_valid``, ``centroid_xy_mm``, ``symmetry_error_mm`` (how far the footprint is from its mirror image
    about the meridional plane, 0 in exact arithmetic) and the footprint points ``points_xy_mm``. The geometric defocus disc of a point on axis has the
    diameter ``2 |defocus| NA'`` (tested). The system must be axisymmetric (the field is traced along +y and rotated).
    """
    op = "bokeh_shape"
    _system(system, op)
    if not _axisymmetric(system):
        raise ValueError("%s: needs an axisymmetric system (no decenter / tilt)" % op)
    wl = _wavelength(system, wavelength_um, op)
    df = _real(defocus_mm, "defocus_mm", op)
    n = _int(pupil_samples, "pupil_samples", op, 7, MAX_PUPIL)
    gr = _int(grid, "grid", op, 8, 1024)
    sysd = system
    if object_mm is not None:
        sysd = _with_object(system, _real(object_mm, "object_mm", op, lo=0.0, lo_open=True))
    obj_inf = sysd["object_mm"] == INF
    if field_xy_mm is None:
        field_xy_mm = (0.0, 8.0) if obj_inf else (0.0, 0.05 * sysd["object_mm"])
    fxy = _array(field_xy_mm, "field_xy_mm", op, ndim=1)
    if fxy.shape != (2,):
        raise ValueError("%s: field_xy_mm must be a pair (x, y)" % op)
    fx, fy = float(fxy[0]), float(fxy[1])
    rho = math.hypot(fx, fy)
    az = math.atan2(fy, fx)
    rings = 1
    while 1 + 3 * (rings + 1) * (rings + 2) <= n:
        rings += 1
    img = _nominal_image_mm(system, None) + df
    b1 = RT.ray_bundle(sysd, field=rho, rings=rings, wavelength_um=wl, image_mm=img, kind="hexapolar")
    b0 = RT.ray_bundle(sysd, field=0.0, rings=rings, wavelength_um=wl, image_mm=img, kind="hexapolar")
    share = _ring_weights(b1["pupil"], rings)
    v1 = b1["valid"] & np.all(np.isfinite(b1["image_xy"]), axis=1)
    v0 = b0["valid"] & np.all(np.isfinite(b0["image_xy"]), axis=1)
    p1 = b1["image_xy"][v1]
    p0 = b0["image_xy"][v0]
    h1, a1 = _hull(p1)
    h0, a0 = _hull(p0)
    cen = p1.mean(axis=0)
    poly = p1[h1.vertices] - cen
    # symmetry about the meridional plane (the y axis before the rotation): nearest neighbour of the mirror image
    from scipy.spatial import cKDTree
    q = p1 - cen
    mir = q * np.array([-1.0, 1.0])
    sym = float(np.max(cKDTree(q).query(mir)[0]))
    ext = 2.2 * float(np.max(np.hypot(*(p0 - p0.mean(axis=0)).T)))
    gx = (np.arange(gr) + 0.5) / gr * ext - 0.5 * ext
    X, Y = np.meshgrid(gx, gx[::-1])
    pts = np.stack([X.ravel(), Y.ravel()], 1)
    eq = h1.equations
    inside = np.all((pts + cen) @ eq[:, :2].T + eq[:, 2] <= 1e-12, axis=1)
    rot = az - 0.5 * math.pi
    return {"polygon_xy_mm": _rot2(poly, rot), "mask": inside.reshape(gr, gr), "extent_mm": ext, "area_mm2": a1, "axis_area_mm2": a0,
            "area_ratio": a1 / a0, "vignetting_factor": float(share[v1].sum() / _ring_weights(b0["pupil"], rings)[v0].sum()),
            "n_valid": int(v1.sum()), "n_valid_axis": int(v0.sum()), "centroid_xy_mm": _rot2(cen[None, :], rot)[0],
            "symmetry_error_mm": sym, "points_xy_mm": _rot2(p1, rot), "defocus_mm": df, "field_xy_mm": [fx, fy], "rings": rings,
            "image_mm": float(img)}


# --------------------------------------------------------------------------- ghost images of a bright point
def _coating_spec(reflectance):
    """A reflectance (0..1) or a raytrace3d coating spec -> the ``coatings`` argument of ``ghost_analysis``."""
    if isinstance(reflectance, (bool, np.bool_)):
        raise ValueError("render_ghost_overlay: reflectance must be a number in [0, 1] or a coating spec")
    if isinstance(reflectance, (int, float, np.floating, np.integer)):
        r = float(reflectance)
        if not (math.isfinite(r) and 0.0 <= r <= 1.0):
            raise ValueError("render_ghost_overlay: reflectance must lie in [0, 1], got %r" % reflectance)
        return {"R": r}
    return reflectance


def render_ghost_overlay(system, scene=None, light_xy_mm=None, distance_mm=1000.0, intensity_W_sr_nm=1.0, reflectance=0.04,
                         sensor=None, wavelengths=None, exposure_s=1e-4, rings=10, max_ghosts=6, defocus_mm=0.0, focus_mm=None,
                         base_electrons=None, band_nm=None, illuminant=None) -> dict:
    """The two-reflection ghosts of a bright point, as electrons on the sensor -> dict.

    The point is the scene's first ``source`` or, with *light_xy_mm* ``(x, y)``, a source at *distance_mm* in front of the lens with
    spectral intensity *intensity_W_sr_nm*. ``raytrace3d.ghost_analysis`` gives, for every pair of refracting surfaces, the ghost's
    energy relative to the image (``R_i R_j`` times the transmittances along its path, *reflectance* being one value for all
    surfaces, or a ``raytrace3d`` coating spec) and the share of rays that reach the sensor; ``ghost_path`` gives the real rays of the strongest
    *max_ghosts* ghosts, which are spread over the pixels with the power ``I Omega T energy_ratio`` of the point. A reflectance of
    0 gives an overlay that is exactly zero. The table has ``overlay_electrons`` (H, W), ``electrons_with_ghosts`` (when
    *base_electrons*, e.g. a render's ``electrons_mean``, is given), ``image_electrons`` (the point's own image, for the ratio), ``ghosts`` (one
    row per ghost: surfaces ``i``, ``j``, ``energy_ratio``, ``reach_fraction``, ``power_ratio`` = their product, the footprint centroid in
    pixels ``(row, col)`` and its radius, and the offset from the main image in pixels), ``main_image_px`` and ``wavelengths_um``. The point
    must be on or off the axis of an axisymmetric system; the sensor plane follows *defocus_mm* / *focus_mm* as in the render.
    """
    op = "render_ghost_overlay"
    import raytrace3d as R3
    _system(system, op)
    scene = _check_scene(scene, op) if scene is not None else None
    sp = _sensor_params(sensor, op)
    wls = _wavelength_list(wavelengths, op)
    t_exp = _real(exposure_s, "exposure_s", op, lo=0.0, lo_open=True)
    rg = _int(rings, "rings", op, 3, 60)
    mg = _int(max_ghosts, "max_ghosts", op, 1, 64)
    df = _real(defocus_mm, "defocus_mm", op)
    fm = None if focus_mm is None else _real(focus_mm, "focus_mm", op, lo=0.0, lo_open=True)
    coat = _coating_spec(reflectance)
    bw = _band_widths(wls, band_nm, op)
    rel = _illum_rel(illuminant, wls, op)
    if light_xy_mm is not None:
        xy = _array(light_xy_mm, "light_xy_mm", op, ndim=1)
        if xy.shape != (2,):
            raise ValueError("%s: light_xy_mm must be a pair (x, y)" % op)
        dz = _real(distance_mm, "distance_mm", op, lo=0.0, lo_open=True)
        src = {"pos": np.array([xy[0], xy[1], -dz]),
               "I": _spectrum(intensity_W_sr_nm, "intensity_W_sr_nm", op)}
    elif scene is not None and scene["sources"]:
        src = scene["sources"][0]
    else:
        raise ValueError("%s: give light_xy_mm, or a scene with a source" % op)
    if not _axisymmetric(system):
        raise ValueError("%s: needs an axisymmetric system (no decenter / tilt)" % op)
    H, W = sp["h"], sp["w"]
    area_m2 = (sp["pitch_um"] * 1e-6) ** 2
    over = np.zeros((H, W))
    imgp = np.zeros((H, W))
    rows_out = []
    main_px = None
    for j, wl in enumerate(wls):
        geo = _geometry(system, wl, df, fm, op)
        f = _source_forward(system, geo, src["pos"], wl, rg)
        I_l = _spec_at(src["I"], wl, "intensity") * rel[j]
        sysw = RT.with_wavelength(_with_object(system, -float(src["pos"][2])), wl)
        s3 = R3.noncoaxial_system(sysw)
        fld = (float(src["pos"][0]), float(src["pos"][1]))
        ga = R3.ghost_analysis(s3, coatings=coat, field=fld, rings=rg)
        bd = R3._bundle(s3, fld, rings=rg, pupil_fill=0.98)
        n_ok = int(bd["valid"].sum())
        if n_ok == 0:
            continue
        frac_ok = float(bd["valid"].mean())
        p_img = I_l * f["omega_sr"] * frac_ok
        shift = geo["image_mm"] - float(s3["image_mm"])
        rows0, cols0 = _to_pixels(f["xy"][f["valid"]], sp)
        img_j = _tent(rows0, cols0, np.full(len(rows0), p_img / max(len(rows0), 1)), H, W)
        imgp += _electrons(img_j, wl, bw[j], t_exp, sp["qe"])
        if j == 0 or main_px is None:
            c0 = f["chief_xy"]
            r_, c_ = _to_pixels(c0[None, :], sp)
            main_px = (float(r_[0]), float(c_[0]))
        cand = [g for g in ga["ghosts"] if g["energy_ratio"] * g["reach_fraction"] > 0.0 and math.isfinite(g["energy_ratio"])]
        cand.sort(key=lambda g: -g["energy_ratio"] * g["reach_fraction"])
        for g in cand[:mg]:
            gp = R3.ghost_path(s3, g["i"], g["j"], field=fld, rings=rg, pupil_fill=0.98)
            v = gp["valid"]
            if not np.any(v):
                continue
            xy_g = gp["image_xy"][v]
            if shift != 0.0:
                last, prev = gp["points"][v, -1, :], gp["points"][v, -2, :]
                dirv = last - prev
                xy_g = xy_g + dirv[:, :2] / dirv[:, 2:3] * shift
            rr, cc = _to_pixels(xy_g, sp)
            pw = p_img * g["energy_ratio"] / n_ok
            lay = _tent(rr, cc, np.full(len(rr), pw), H, W)
            e_lay = _electrons(lay, wl, bw[j], t_exp, sp["qe"])
            over += e_lay
            rows_out.append({"wavelength_um": float(wl), "i": int(g["i"]), "j": int(g["j"]), "label": g["label"],
                             "energy_ratio": float(g["energy_ratio"]), "reach_fraction": float(g["reach_fraction"]),
                             "power_ratio": float(g["energy_ratio"] * g["reach_fraction"]),
                             "spread_power_ratio": float(lay.sum() / p_img) if p_img > 0 else 0.0,
                             "centroid_px": [float(rr.mean()), float(cc.mean())],
                             "radius_px": float(np.sqrt(np.mean((rr - rr.mean()) ** 2 + (cc - cc.mean()) ** 2))),
                             "offset_px": [float(rr.mean() - main_px[0]), float(cc.mean() - main_px[1])],
                             "electrons": float(e_lay.sum())})
    out = {"overlay_electrons": over, "image_electrons": imgp, "ghosts": rows_out, "main_image_px": main_px,
           "wavelengths_um": np.array(wls), "reflectance": coat, "pixel_pitch_um": sp["pitch_um"]}
    if base_electrons is not None:
        be = _array(base_electrons, "base_electrons", op, ndim=2)
        if be.shape != (H, W):
            raise ValueError("%s: base_electrons must be (%d, %d), got %r" % (op, H, W, be.shape))
        out["electrons_with_ghosts"] = be + over
    return out


# --------------------------------------------------------------------------- the same scene through several prescriptions
def _edge_metrics(img, roi, op):
    """10-90 % edge width (px) and MTF50 (cycles / px) of a slanted edge in *img* (edgesfr)."""
    import edgesfr
    esf = None
    for ovs in (4, 2, 1):                       # a heavily blurred edge gives a poor tilt estimate: bin the ESF more coarsely then
        try:
            esf = edgesfr.edge_spread(np.asarray(img, dtype=np.float64), roi, oversample=ovs)
            break
        except ValueError:
            continue
    if esf is None:
        return float("nan"), float("nan")
    x, e = np.asarray(esf["x"]), np.asarray(esf["esf"])
    lo, hi = float(np.median(e[:max(2, len(e) // 10)])), float(np.median(e[-max(2, len(e) // 10):]))
    if hi == lo:
        return float("nan"), float("nan")
    n = (e - lo) / (hi - lo)
    if lo > hi:
        n = 1.0 - (e - hi) / (lo - hi)

    def cross(level):
        k = np.nonzero((n[:-1] < level) & (n[1:] >= level))[0]
        if len(k) == 0:
            return float("nan")
        k = int(k[0])
        return float(x[k] + (level - n[k]) / (n[k + 1] - n[k]) * (x[k + 1] - x[k]))

    width = abs(cross(0.9) - cross(0.1))
    try:
        win = min(8.0, 0.45 * (x[-1] - x[0]))
        m50 = edgesfr.mtf50(edgesfr.sfr_from_edge(esf, win, correction="derivative+bin", ends=1.0 if win > 2 else 0.5 * win))
    except ValueError:
        m50 = float("nan")
    return width, float(m50)


def render_compare_prescriptions(systems=None, scene=None, sensor=None, labels=None, edge_roi=None, fields=(0.0, 0.7, 1.0), field_max=None,
                                 **render_kw) -> dict:
    """Render the same scene through two or more prescriptions and tabulate how good each picture is -> dict.

    Every system is rendered by :func:`render_scene_through_lens` with the same *scene*, *sensor* and ``render_kw`` (give ``focus_mm`` to focus each one on
    the scene). The table has one row per system: the effective focal length and f-number, the RMS spot radius (um) at the *fields*
    (fractions of the half diagonal of the sensor, or of *field_max* - an object height in mm, degrees for an object at infinity - when the picture
    covers only the middle of the lens's field; from ``raytrace.spot_stats``), the relative illumination at the corner (``lensimage``'s traced
    value), the distortion at the corner (%, ``lensimage.distortion_map``), the lateral colour at 0.7 field (um, ``raytrace.chromatic_shift``) and, when
    *edge_roi* ``(y0, y1, x0, x1)`` encloses a slanted edge of the scene in the picture, its 10-90 % rise width and MTF50 (``edgesfr``, cycles per
    pixel; the ESF is binned at 1/4 pixel, or more coarsely when the tilt of a blurred edge cannot be estimated) measured on the noiseless render.
    Fields the lens cannot reach are NaN. Also ``images`` (the renders) and ``labels``.
    Default: the doublet and the singlet prescriptions of ``raytrace.example_system``.
    """
    op = "render_compare_prescriptions"
    import lensimage as LI
    if systems is None:
        systems = [RT.example_system("doublet"), RT.example_system("singlet")]
    if not isinstance(systems, (list, tuple)) or len(systems) < 2:
        raise ValueError("%s: give a list of at least two lens_system tables" % op)
    for s in systems:
        _system(s, op)
    if labels is None:
        labels = ["system %d" % (i + 1) for i in range(len(systems))]
    if len(labels) != len(systems):
        raise ValueError("%s: labels must have one entry per system" % op)
    fr = [_real(f, "fields", op, lo=0.0, hi=1.0) for f in fields]
    fmax = None if field_max is None else _real(field_max, "field_max", op, lo=0.0, lo_open=True)
    sp = _sensor_params(sensor, op)
    scene = _check_scene(scene, op)
    r_corner = 0.5 * math.hypot(sp["h"], sp["w"]) * sp["pitch_um"] * 1e-3
    rows, images = [], []
    for lab, sysd in zip(labels, systems):
        res = render_scene_through_lens(sysd, scene, sensor, **render_kw)
        images.append(res)
        para = RT.paraxial_trace(sysd)
        obj_inf = sysd["object_mm"] == INF
        row = {"label": str(lab), "efl_mm": para["efl"], "fno": para["fno"], "fields": fr}
        spots, fvals = [], []
        for fr_ in fr:
            try:
                fv = (fr_ * fmax if fmax is not None else LI._field_for_radius(para, fr_ * r_corner, obj_inf)) if fr_ > 0 else 0.0
                spots.append(1000.0 * RT.spot_stats(sysd, field=fv, rings=6)["rms_radius"])
            except ValueError:
                fv = float("nan")
                spots.append(float("nan"))
            fvals.append(fv)
        row["field_values"] = fvals
        row["rms_spot_um"] = spots
        try:
            f_corner = fmax if fmax is not None else LI._field_for_radius(para, r_corner, obj_inf)
            row["relative_illumination_corner"] = float(LI._relative_illumination(sysd, para, [0.0, f_corner], obj_inf)[-1])
        except ValueError:
            row["relative_illumination_corner"] = float("nan")
        try:
            fl_d = None if fmax is None else np.linspace(0.0, fmax, 9).tolist()
            row["distortion_pct"] = float(LI.distortion_map(sysd, (sp["h"], sp["w"]), sp["pitch_um"], fields=fl_d)["max_distortion_pct"])
        except ValueError:
            row["distortion_pct"] = float("nan")
        try:
            f07 = 0.7 * fmax if fmax is not None else LI._field_for_radius(para, 0.7 * r_corner, obj_inf)
            row["lateral_color_um"] = 1000.0 * float(RT.chromatic_shift(sysd, field=f07)["lateral_color"])
        except ValueError:
            row["lateral_color_um"] = float("nan")
        if edge_roi is not None:
            w10, m50 = _edge_metrics(res["image_noiseless"], edge_roi, op)
        else:
            w10, m50 = float("nan"), float("nan")
        row["edge_width_10_90_px"] = w10
        row["edge_mtf50_cyc_px"] = m50
        rows.append(row)
    return {"table": rows, "images": images, "labels": [str(x) for x in labels]}
