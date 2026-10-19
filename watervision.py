# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""watervision - how water looks in the images of an inspection camera.

``watermedia`` holds the physics of water (waves, Fresnel, Snell, attenuation, a bottle as a lens). This module turns it
into the pictures a camera records: the bright web of caustics on a pool floor, a bottle seen from the side with its
fill line and bubbles, a wet plate that looks darker and glossier than a dry one, a hull seen through murky water with a
lamp beside the lens, and the segmentation of the caustic lines so that a crack detector is not fooled by them.

The ops::

    caustic_irradiance(height_field, extent_m, depth_m, light_dir)  -> the irradiance on a flat floor below a wavy surface
    bottle_image(radius_mm, wall_mm, height_mm, fill_fraction, ...)  -> a side view of a (part-)filled bottle, backlit or frontlit
    fill_level_from_image(image, pixel_pitch_um)                    -> the fill line (mm) measured from such an image
    wet_surface_appearance(albedo, roughness, water_film_um, ...)   -> why a wet surface is darker (Lekner & Dorf 1988) and glossier
    wet_dry_inspection_pair(texture, defect_mask, roughness, ...)   -> the same textured plate dry and wet, and the defect contrast
    underwater_inspection_image(scene_albedo, distance_map_m, ...)  -> a lamp-at-the-camera hull image, the veil and the SNR
    caustic_floor_segmentation(irradiance, method)                  -> the caustic lines of a floor irradiance as a mask

Conventions: z points up, the mean water surface is z = 0 and the floor is the plane z = -depth_m; lengths of the
caustic op are in metres, those of the bottle in millimetres; angles are in degrees (``_deg``). A solver that cannot answer
is refused (``ValueError``) or flagged in the result; a wrong number is never returned silently.

Where the models stop (stated here, shown in the PoC): the bottle is ray-cast in the horizontal cross-section of every image
row, so the vertical refraction at the shoulder and the base and the tilt of the rays out of that plane are ignored; interface
reflections inside the bottle are not followed (only the first reflection of the frontlit view is); the wet film is a
non-absorbing layer much thicker than a wavelength (no interference), spread over the surface by an assumed coverage law;
the hull lamp veil uses a single-scattering profile with an assumed beam shape.
"""
from __future__ import annotations

import math

import numpy as np

import watermedia as _wm
from watermedia import _array, _choice, _int, _real, _water_index

__all__ = ["caustic_irradiance", "bottle_image", "fill_level_from_image", "wet_surface_appearance",
           "wet_dry_inspection_pair", "underwater_inspection_image", "caustic_floor_segmentation"]

#: the most rays one caustic call traces
MAX_RAYS = 1 << 22
#: the most pixels one image op builds
MAX_PIXELS = 1 << 24
#: an irradiance gain above this (a Jacobian determinant below its inverse) is a fold of the wavefront map
DEFAULT_MAX_GAIN = 20.0


# --------------------------------------------------------------------------- 1. caustics on a floor
def _fourier_pad(spec, ny2, nx2):
    """Zero-pad a 2-D spectrum (the Nyquist row and column are dropped) and return the finer real field."""
    ny, nx = spec.shape
    iy = np.fft.fftfreq(ny, 1.0 / ny).round().astype(int)
    ix = np.fft.fftfreq(nx, 1.0 / nx).round().astype(int)
    oky = np.nonzero(iy * 2 != ny)[0]
    okx = np.nonzero(ix * 2 != nx)[0]
    out = np.zeros((ny2, nx2), dtype=complex)
    out[np.ix_(iy[oky] % ny2, ix[okx] % nx2)] = spec[np.ix_(oky, okx)]
    return np.fft.ifft2(out).real * (ny2 * nx2) / (ny * nx)


def _wave_numbers(ny, nx, ly, lx):
    ky = 2.0 * math.pi * np.fft.fftfreq(ny, 1.0 / ny) / ly
    kx = 2.0 * math.pi * np.fft.fftfreq(nx, 1.0 / nx) / lx
    return ky, kx


def _periodic_derivative(a, ly, lx, axis):
    """Spectral derivative of a periodic real field along ``axis`` (0 = y, 1 = x); the Nyquist row and column are dropped."""
    ny, nx = a.shape
    ky, kx = _wave_numbers(ny, nx, ly, lx)
    spec = np.fft.fft2(a)
    spec = spec * (1j * (kx[None, :] if axis == 1 else ky[:, None]))
    if ny % 2 == 0:
        spec[ny // 2, :] = 0.0
    if nx % 2 == 0:
        spec[:, nx // 2] = 0.0
    return np.fft.ifft2(spec).real


def _light_vector(light_dir, op):
    """The unit direction the light travels: a 3-vector with a downward z, or (zenith_deg, azimuth_deg)."""
    v = _array(light_dir, "light_dir", op, ndim=1, allow_scalar=False)
    if v.size == 2:
        if not 0.0 <= v[0] < 90.0:
            raise ValueError("%s: the zenith angle of light_dir must be in [0, 90) degrees, got %g" % (op, v[0]))
        th, ph = math.radians(float(v[0])), math.radians(float(v[1]))
        return np.array([math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), -math.cos(th)])
    if v.size != 3:
        raise ValueError("%s: light_dir is a 3-vector or (zenith_deg, azimuth_deg), got %d numbers" % (op, v.size))
    nrm = float(np.linalg.norm(v))
    if nrm == 0.0 or v[2] >= 0.0 or -v[2] / nrm < 1e-6:
        raise ValueError("%s: light_dir must point down into the water (negative z component), got %r" % (op, v.tolist()))
    return v / nrm


def _extent_pair(extent_m, op):
    e = _array(extent_m, "extent_m", op, lo=0.0)
    if e.ndim == 0:
        e = np.array([float(e), float(e)])
    if e.shape != (2,) or (e <= 0).any():
        raise ValueError("%s: extent_m is a positive length or (Lx, Ly), got %r" % (op, e.tolist()))
    return float(e[0]), float(e[1])


def _splat(ix, iy, w, ny, nx, periodic):
    """Bilinear splatting (energy conserving) of weights ``w`` at fractional nodes (ix, iy); returns (grid, lost weight)."""
    i0 = np.floor(ix).astype(np.int64)
    j0 = np.floor(iy).astype(np.int64)
    fx = ix - i0
    fy = iy - j0
    lost = 0.0
    if not periodic:
        keep = (ix >= 0.0) & (ix <= nx - 1) & (iy >= 0.0) & (iy <= ny - 1)
        lost = float(w[~keep].sum())
        i0, j0, fx, fy, w = i0[keep], j0[keep], fx[keep], fy[keep], w[keep]
    grid = np.zeros(ny * nx)
    for di, dj, wt in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        ii = (i0 + di) % nx if periodic else np.minimum(i0 + di, nx - 1)
        jj = (j0 + dj) % ny if periodic else np.minimum(j0 + dj, ny - 1)
        grid += np.bincount(jj * nx + ii, weights=w * wt, minlength=ny * nx)
    return grid.reshape(ny, nx), lost


def _dilate_wrap(mask):
    out = mask.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            out |= np.roll(np.roll(mask, dy, axis=0), dx, axis=1)
    return out


def caustic_irradiance(height_field, extent_m, depth_m, light_dir, n_water=None, size=None, method="photon",
                       ray_density=4, periodic=True, max_gain=DEFAULT_MAX_GAIN) -> dict:
    """The irradiance a collimated light leaves on a flat floor below a wavy water surface -> dict.

    ``height_field`` (ny, nx) is the surface height (m) of a periodic patch of ``extent_m`` metres (a length, or (Lx, Ly)); it is
    treated as band limited (the Nyquist row and column are dropped) and sampled finer by an integer ``ray_density`` (rays per cell and axis; the default 4 is for the photon
    method, the wavefront method triangulates its landing points and is usually run with 1 or 2) with a
    Fourier interpolation that also gives the exact slopes. ``depth_m`` is the depth of the floor below the mean level
    (it must lie below every wave crest). ``light_dir`` is the direction the light travels, a 3-vector with a downward z or
    ``(zenith_deg, azimuth_deg)``. ``n_water`` defaults to the material-table index at 0.55 um. ``size`` is the
    floor grid ``(ny, nx)`` (default: that of the height field).

    ``method="photon"``: one ray per fine cell leaves the surface, is refracted by the vector form of Snell's law with the
    normal of the local slope, carries the power the beam puts on that cell, ``E0 (d.(-grad h, 1)) dx dy``, times the unpolarised
    Fresnel transmittance, lands on the floor and is binned by bilinear splatting (the weights add up exactly, so the energy is
    conserved). ``method="wavefront"``: the map surface to floor, ``(x, y) -> (x, y) + s t_xy``, has the Jacobian ``J``
    (spectral derivatives of the periodic displacement) and the irradiance at a landing point is the carried power over
    ``|det J|``; it is interpolated linearly onto the floor grid. Where ``det J`` falls below ``1 / max_gain`` or turns negative the
    map folds (a caustic: the geometric gain is unbounded and several sheets overlap), the wavefront result is ``inf`` there
    and ``fold_mask`` flags the pixels (dilated by one pixel). The unit is the irradiance of the beam, measured on the horizontal
    floor, so a flat surface gives exactly ``cos(theta_i) T(theta_i)`` everywhere (the refracted beam is narrower by
    ``cos(theta_i) / cos(theta_t)`` and meets the floor at ``cos(theta_t)``).

    The table has ``irradiance`` (ny, nx), ``fold_mask``, ``x_m`` / ``y_m`` (floor nodes), ``incident_flux`` (the power of the beam through the
    patch, summed over the rays), ``incident_flux_analytic`` (``cos(theta_i) Lx Ly``), ``transmitted_flux`` (after Fresnel),
    ``floor_flux`` (the integral of the irradiance, photon only), ``lost_flux_fraction`` (photons that left a non-periodic patch),
    ``mean_transmittance``, ``flat_irradiance`` (``cos(theta_i) T``), ``theta_i_deg``, ``theta_t_deg``, ``n_water`` and
    ``n_rays``. Non-finite heights, a floor above a crest, a light not pointing down and a patch too large for the ray cap
    are refused."""
    op = "caustic_irradiance"
    h = _array(height_field, "height_field", op, ndim=2, allow_scalar=False)
    ny, nx = h.shape
    if ny < 4 or nx < 4:
        raise ValueError("%s: height_field must be at least 4 x 4, got %r" % (op, h.shape))
    lx, ly = _extent_pair(extent_m, op)
    depth = _real(depth_m, "depth_m", op, lo=0.0, lo_open=True)
    if depth <= float(h.max()):
        raise ValueError("%s: the floor (depth %g m) must lie below the highest crest (%g m)" % (op, depth, float(h.max())))
    d = _light_vector(light_dir, op)
    n = _water_index(n_water, 0.55, op)
    method = _choice(method, "method", op, ("photon", "wavefront"))
    r = _int(ray_density, "ray_density", op, 1, 16)
    if not isinstance(periodic, (bool, np.bool_)):
        raise ValueError("%s: periodic must be a bool, got %r" % (op, periodic))
    gain = _real(max_gain, "max_gain", op, lo=1.0, lo_open=True)
    if size is None:
        fny, fnx = ny, nx
    else:
        s = _array(size, "size", op, ndim=1, allow_scalar=False)
        if s.size != 2 or (s < 4).any() or (s != np.round(s)).any():
            raise ValueError("%s: size is (ny, nx) with both >= 4 integers, got %r" % (op, s.tolist()))
        fny, fnx = int(s[0]), int(s[1])
    if (ny * r) * (nx * r) > MAX_RAYS:
        raise ValueError("%s: %d rays are over the cap of %d" % (op, (ny * r) * (nx * r), MAX_RAYS))
    if method == "wavefront" and not periodic:
        raise ValueError("%s: the wavefront method needs periodic = True (the map is differentiated spectrally)" % op)
    spec = np.fft.fft2(h)
    ky, kx = _wave_numbers(ny, nx, ly, lx)
    sx = spec * (1j * kx[None, :])
    sy = spec * (1j * ky[:, None])
    nyf, nxf = ny * r, nx * r
    hf = _fourier_pad(spec, nyf, nxf)
    hx = _fourier_pad(sx, nyf, nxf)
    hy = _fourier_pad(sy, nyf, nxf)
    dxf, dyf = lx / nxf, ly / nyf
    X0, Y0 = np.meshgrid(np.arange(nxf) * dxf, np.arange(nyf) * dyf)
    g = d[0] * hx + d[1] * hy - d[2]                       # power per horizontal cell / (E0 dx dy)
    nrm = np.sqrt(1.0 + hx * hx + hy * hy)
    cosi = np.clip(g / nrm, 0.0, 1.0)
    facing = g > 0.0
    theta_i = np.degrees(np.arccos(cosi))
    tr = _wm.fresnel_water_air(theta_i, n_water=n, polarization="unpolarized")["T"]
    nvec = np.stack([-hx, -hy, np.ones_like(hx)], axis=-1) / nrm[..., None]
    eta = 1.0 / n
    kk = 1.0 - eta * eta * (1.0 - cosi * cosi)
    tdir = eta * d[None, None, :] + (eta * cosi - np.sqrt(kk))[..., None] * nvec
    tz = tdir[..., 2]
    if (tz[facing] >= 0.0).any():
        raise ValueError("%s: a refracted ray does not point down (the light is nearly grazing the surface)" % op)
    sdist = (-depth - hf) / np.where(facing, tz, -1.0)
    dispx = sdist * tdir[..., 0]
    dispy = sdist * tdir[..., 1]
    w_inc = np.where(facing, g, 0.0) * dxf * dyf
    w_tr = w_inc * tr
    incident = float(w_inc.sum())
    transmitted = float(w_tr.sum())
    cos0 = -d[2]
    theta0 = math.degrees(math.acos(cos0))
    flat_t = float(_wm.fresnel_water_air(theta0, n_water=n, polarization="unpolarized")["T"])
    theta_t = math.degrees(math.asin(math.sin(math.radians(theta0)) / n))
    # fold diagnostics from the Jacobian of the surface -> floor map (the displacement is periodic)
    dxs = _periodic_derivative(dispx, ly, lx, 1)
    dxy = _periodic_derivative(dispx, ly, lx, 0)
    dyx = _periodic_derivative(dispy, ly, lx, 1)
    dyy = _periodic_derivative(dispy, ly, lx, 0)
    det = (1.0 + dxs) * (1.0 + dyy) - dxy * dyx
    fold_l = (det < 1.0 / gain) & facing
    dx, dy = lx / fnx, ly / fny
    Xl = X0 + dispx
    Yl = Y0 + dispy
    fold = np.zeros((fny, fnx), dtype=bool)
    if fold_l.any():
        fi = np.rint(Xl[fold_l] / dx).astype(int) % fnx
        fj = np.rint(Yl[fold_l] / dy).astype(int) % fny
        fold[fj, fi] = True
        fold = _dilate_wrap(fold)
    if method == "photon":
        grid, lost = _splat((Xl / dx).ravel(), (Yl / dy).ravel(), w_tr.ravel(), fny, fnx, periodic)
        irr = grid / (dx * dy)
        floor_flux = float(grid.sum())
        lost_frac = lost / transmitted if transmitted > 0 else 0.0
    else:
        from scipy.interpolate import LinearNDInterpolator
        e_l = np.where(facing, g * tr / np.maximum(np.abs(det), 1e-12), 0.0)
        px, py, vals = Xl.ravel(), Yl.ravel(), e_l.ravel()
        pts = [np.stack([px + ox * lx, py + oy * ly], axis=1) for oy in (-1, 0, 1) for ox in (-1, 0, 1)]
        interp = LinearNDInterpolator(np.concatenate(pts), np.tile(vals, 9))
        gx, gy = np.meshgrid(np.arange(fnx) * dx, np.arange(fny) * dy)
        irr = interp(np.stack([gx.ravel(), gy.ravel()], axis=1)).reshape(fny, fnx)
        if not np.isfinite(irr).all():
            raise ValueError("%s: the wavefront map does not cover the floor (the displacement exceeds the patch)" % op)
        irr = np.where(fold, np.inf, irr)
        floor_flux = float("nan")
        lost_frac = 0.0
    return {"irradiance": irr, "fold_mask": fold, "x_m": np.arange(fnx) * dx, "y_m": np.arange(fny) * dy,
            "incident_flux": incident, "incident_flux_analytic": cos0 * lx * ly, "transmitted_flux": transmitted,
            "floor_flux": floor_flux, "lost_flux_fraction": lost_frac, "mean_transmittance": transmitted / incident,
            "flat_irradiance": cos0 * flat_t, "theta_i_deg": theta0, "theta_t_deg": theta_t, "n_water": n,
            "n_rays": int(facing.sum()), "method": method, "ray_density": r, "periodic": bool(periodic),
            "displacement_x": dispx, "displacement_y": dispy, "jacobian_det": det}


# --------------------------------------------------------------------------- 2. a bottle seen from the side
LIGHTS = ("backlight", "frontlight")
#: the half angle (degrees) of the backlight panel: a ray leaving the bottle further from the viewing axis is not lit
PANEL_HALF_ANGLE_DEG = 8.0
#: the raised-cosine softness (degrees) of the panel edge
PANEL_EDGE_DEG = 1.0
#: the radiance of the matt wall behind a frontlit bottle (the panel of the backlight has radiance 1)
FRONT_WALL_RADIANCE = 0.8
#: the frontlight: a soft box at this azimuth from the camera axis, with this half width, over a dim dome
SOFTBOX_AZIMUTH_DEG = 35.0
SOFTBOX_HALF_DEG = 8.0
SOFTBOX_EDGE_DEG = 2.0
DOME_RADIANCE = 0.1
#: the liquid meniscus rises to the wall as (rho / r_inner) ** MENISCUS_POWER
MENISCUS_POWER = 6.0
_MAX_STEPS = 24
_STEP_EPS = 1e-6
_MAX_CHUNK = 400000


def _edge_response(ang_deg, half_deg, edge_deg):
    """1 inside ``half - edge``, 0 beyond ``half + edge``, a raised cosine between."""
    t = np.clip((ang_deg - (half_deg - edge_deg)) / (2.0 * edge_deg), 0.0, 1.0)
    return 0.5 * (1.0 + np.cos(math.pi * t))


def _env_radiance(dx, dy):
    """The radiance of the frontlight environment seen along the direction (dx, dy) leaving the bottle toward the camera side."""
    s = math.radians(SOFTBOX_AZIMUTH_DEG)
    c = np.clip(dx * (-math.cos(s)) + dy * math.sin(s), -1.0, 1.0)
    ang = np.degrees(np.arccos(c))
    return DOME_RADIANCE + (1.0 - DOME_RADIANCE) * _edge_response(ang, SOFTBOX_HALF_DEG, SOFTBOX_EDGE_DEG)


def _circle_t(px, py, dx, dy, cx, cy, r):
    """Smallest positive parameter of the ray with the circle (inf for no hit or a zero radius)."""
    ox, oy = px - cx, py - cy
    b = ox * dx + oy * dy
    c = ox * ox + oy * oy - r * r
    disc = b * b - c
    ok = (disc > 0.0) & (r > 0.0)
    sq = np.sqrt(np.where(ok, disc, 0.0))
    t1 = -b - sq
    t2 = -b + sq
    t = np.where(t1 > _STEP_EPS, t1, np.where(t2 > _STEP_EPS, t2, np.inf))
    return np.where(ok, t, np.inf)


def _trace_rows(xpix, mode, rc, bubbles, ng, nl, na, R, Ri, dc, light):
    """Ray-cast the rows of one batch: a pinhole at distance ``dc`` looks through the horizontal section of the bottle.

    ``mode`` (nr,) is 0 for an air core, 1 for a liquid core, 2 for a meniscus row (liquid between ``rc`` and the wall, air
    inside); ``bubbles`` is a list of (x, y, radius of that row's circle (nr,)). Returns (radiance (nr, nw), unresolved count)."""
    nr, nw = mode.size, xpix.size
    n = nr * nw
    ridx = np.repeat(np.arange(nr), nw)
    xs = np.tile(xpix, nr)
    nrm = np.hypot(dc, xs)
    px, py = np.full(n, -dc), np.zeros(n)
    dx, dy = dc / nrm, xs / nrm
    ncur = np.full(n, na, dtype=np.float64)
    w = np.ones(n)
    exited = np.zeros(n, dtype=bool)
    ex_dx, ex_dy = dx.copy(), dy.copy()
    r_first = np.zeros(n)
    rf_dx, rf_dy = np.zeros(n), np.zeros(n)
    active = np.arange(n)
    for step in range(_MAX_STEPS):
        if active.size == 0:
            break
        a = active
        pxa, pya, dxa, dya = px[a], py[a], dx[a], dy[a]
        rows = ridx[a]
        circles = [(0.0, 0.0, np.full(a.size, R)), (0.0, 0.0, np.full(a.size, Ri)), (0.0, 0.0, rc[rows])]
        for bx, by, brad in bubbles:
            circles.append((bx, by, brad[rows]))
        ts = np.stack([_circle_t(pxa, pya, dxa, dya, cx, cy, cr) for cx, cy, cr in circles])
        which = np.argmin(ts, axis=0)
        tmin = ts[which, np.arange(a.size)]
        gone = ~np.isfinite(tmin)
        if gone.any():
            g = a[gone]
            exited[g] = True
            ex_dx[g], ex_dy[g] = dx[g], dy[g]
        hit = ~gone
        a, rows, which, tmin = a[hit], rows[hit], which[hit], tmin[hit]
        pxa, pya, dxa, dya = pxa[hit], pya[hit], dxa[hit], dya[hit]
        if a.size == 0:
            active = a
            break
        qx, qy = pxa + tmin * dxa, pya + tmin * dya
        ccx = np.zeros(a.size)
        ccy = np.zeros(a.size)
        crad = np.empty(a.size)
        crad[:] = np.where(which == 0, R, np.where(which == 1, Ri, rc[rows]))
        for k, (bx, by, brad) in enumerate(bubbles):
            sel = which == 3 + k
            ccx[sel], ccy[sel] = bx, by
            crad[sel] = brad[rows[sel]]
        nhx, nhy = (qx - ccx) / crad, (qy - ccy) / crad
        ex_, ey_ = qx + _STEP_EPS * dxa, qy + _STEP_EPS * dya
        rho2 = ex_ * ex_ + ey_ * ey_
        n_after = np.where(rho2 > R * R, na, np.where(rho2 > Ri * Ri, ng, 0.0))
        core = n_after == 0.0
        md = mode[rows]
        n_core = np.where(md == 1, nl, np.where(md == 2, np.where(rho2 > rc[rows] ** 2, nl, na), na))
        n_after = np.where(core, n_core, n_after)
        for bx, by, brad in bubbles:
            rb = brad[rows]
            inb = ((ex_ - bx) ** 2 + (ey_ - by) ** 2 < rb * rb) & (rb > 0.0)
            n_after = np.where(inb, na, n_after)
        n1 = ncur[a]
        same = n_after == n1
        dn = dxa * nhx + dya * nhy
        nnx = np.where(dn > 0.0, -nhx, nhx)
        nny = np.where(dn > 0.0, -nhy, nhy)
        ci = np.abs(dn)
        eta = n1 / n_after
        kk = 1.0 - eta * eta * (1.0 - ci * ci)
        tir = (kk < 0.0) & ~same
        ct = np.sqrt(np.where(kk > 0.0, kk, 0.0))
        rs = (n1 * ci - n_after * ct) / (n1 * ci + n_after * ct)
        rp = (n_after * ci - n1 * ct) / (n_after * ci + n1 * ct)
        tr = 1.0 - 0.5 * (rs * rs + rp * rp)
        ndx = eta * dxa + (eta * ci - ct) * nnx
        ndy = eta * dya + (eta * ci - ct) * nny
        rdx = dxa - 2.0 * (dxa * nhx + dya * nhy) * nhx
        rdy = dya - 2.0 * (dxa * nhx + dya * nhy) * nhy
        if step == 0:
            first = (which == 0) & ~same
            fa = a[first]
            r_first[fa] = 1.0 - tr[first]
            rf_dx[fa], rf_dy[fa] = rdx[first], rdy[first]
        newdx = np.where(same, dxa, np.where(tir, rdx, ndx))
        newdy = np.where(same, dya, np.where(tir, rdy, ndy))
        w[a] = w[a] * np.where(same | tir, 1.0, tr)
        ncur[a] = np.where(same | tir, n1, n_after)
        px[a], py[a] = qx, qy
        dx[a], dy[a] = newdx, newdy
        out = rho2 > R * R
        done = a[out]
        exited[done] = True
        ex_dx[done], ex_dy[done] = dx[done], dy[done]
        active = a[~out]
    unresolved = int(active.size)
    fwd = ex_dx > 1e-12
    if light == "backlight":
        ang = np.degrees(np.abs(np.arctan2(ex_dy, ex_dx)))
        rad = w * _edge_response(ang, PANEL_HALF_ANGLE_DEG, PANEL_EDGE_DEG) * fwd
    else:
        rad = r_first * _env_radiance(rf_dx, rf_dy) + w * np.where(fwd, FRONT_WALL_RADIANCE, _env_radiance(ex_dx, ex_dy))
    rad = np.where(exited, rad, 0.0)
    return rad.reshape(nr, nw), unresolved


def _background_row(xpix, dc, light):
    if light == "backlight":
        return _edge_response(np.degrees(np.arctan2(np.abs(xpix), dc)), PANEL_HALF_ANGLE_DEG, PANEL_EDGE_DEG)
    return np.full(xpix.size, FRONT_WALL_RADIANCE)


def _bubble_list(bubbles, R_in, z0, fill, op):
    out = []
    if bubbles is None:
        return out
    if isinstance(bubbles, (str, bytes)) or not hasattr(bubbles, "__iter__"):
        raise ValueError("%s: bubbles must be a list of (x_mm, z_mm, r_mm) or (x_mm, z_mm, r_mm, y_mm)" % op)
    for b in bubbles:
        v = _array(b, "bubble", op, ndim=1, allow_scalar=False)
        if v.size not in (3, 4):
            raise ValueError("%s: a bubble is (x_mm, z_mm, r_mm) or (x_mm, z_mm, r_mm, y_mm), got %d numbers" % (op, v.size))
        x, z, r = float(v[0]), float(v[1]), float(v[2])
        y = float(v[3]) if v.size == 4 else 0.0
        if r <= 0.0:
            raise ValueError("%s: a bubble radius must be > 0, got %g" % (op, r))
        if math.hypot(x, y) + r > R_in:
            raise ValueError("%s: the bubble at (%g, %g) with radius %g sticks out of the liquid (inner radius %g mm)" % (op, x, y, r, R_in))
        if fill <= 0.0 or z - r < 0.0 or z + r > z0:
            raise ValueError("%s: the bubble at z = %g mm with radius %g mm is not below the fill line (%g mm)" % (op, z, r, z0))
        out.append((x, y, z, r))
    return out


def bottle_image(radius_mm, wall_mm, height_mm, fill_fraction, n_glass, n_liquid, meniscus_mm=0.0, bubbles=None,
                 camera_distance_mm=500.0, pixel_pitch_um=20.0, size=None, light="backlight", n_air=1.0) -> dict:
    """A side view of a cylindrical bottle, part filled with a liquid, ray-cast row by row -> dict.

    The bottle (outer radius ``radius_mm``, glass wall ``wall_mm``, height ``height_mm``, axis vertical, base at z = 0) is looked at
    by a pinhole camera ``camera_distance_mm`` from the axis. Every image row is the horizontal cross-section at its height: the
    ray of a pixel is traced through the circles of the section (outer wall, inner wall, the edge of the liquid in a
    meniscus row, bubbles) with the vector form of Snell's law and the unpolarised Fresnel transmittance at each interface.
    Total internal reflection reflects the ray (at most 24 interface events are followed; a ray still wandering then is
    counted in ``unresolved_rays`` and left dark). The liquid (``n_liquid``) fills the bottle up to ``fill_fraction * height_mm``;
    ``meniscus_mm`` lets it climb the wall by that much as ``(rho / r_inner)^6``. ``bubbles`` is a list of
    ``(x_mm, z_mm, r_mm)`` (or with a fourth ``y_mm`` along the viewing axis; default 0): air spheres in the liquid, drawn as
    their circle in each row they cross. ``pixel_pitch_um`` is the sampling pitch in the plane of the axis, so
    ``1000 / pixel_pitch_um`` pixels are 1 mm there; ``size`` is ``(rows, cols)`` (default: the rows exactly cover the height,
    the width is 1.15 times the diameter); row ``j`` is at ``z = height - (j + 0.5) pitch``.

    ``light="backlight"``: a diffuse panel of radiance 1 behind the bottle that emits only within +-8 degrees of the viewing axis
    (soft edge 1 degree): a pixel is lit when its ray leaves the bottle inside that cone, times the product of the Fresnel
    transmittances. The empty bottle bends rays little and is lit to near the edges; the filled one is a cylindrical lens, so only
    a central band (half width ``alpha / (1/f - 1/dc)`` with the paraxial focal length ``f`` of :func:`watermedia.cylinder_lens_caustic`) is lit and the
    flanks go dark; an air bubble in the liquid is a diverging lens and shows as a dark ring. ``light="frontlight"``: a matt wall of radiance 0.8 behind,
    a dim dome plus a soft box at 35 degrees, and the first Fresnel reflection of the outer wall (``R`` times the environment radiance),
    which gives the glint and the bright rim at grazing view. Interior reflections other than total internal reflection are not
    followed, the rows are independent (no vertical refraction at the shoulder or the base), and rows without bubbles or
    meniscus are computed once per kind (the empty and the full section), so rows of equal geometry are bit identical.

    The table has ``image`` (rows, cols; no pixel exceeds 1), ``x_mm``, ``z_mm``, ``pixel_pitch_mm``, ``magnification_px_per_mm``,
    ``fill_row_from_top`` (the first liquid row), ``liquid_rows`` (rows with liquid; about ``fill_fraction height / pitch``),
    ``fill_z_mm``, ``paraxial_efl_mm`` and ``band_half_width_mm_paraxial`` (the predicted half width of the lit band of the filled
    bottle, inf when the lens does not converge within the camera distance), ``central_transmittance_empty`` / ``..._filled``
    (the product of the normal-incidence Fresnel transmittances of the four interfaces on the axis), ``unresolved_rays`` and the inputs
    echoed. ``n_glass <= 1``, ``n_liquid <= 1``, ``n_air < 1`` or not below both, a fill outside [0, 1], a wall not thinner than the
    radius, a meniscus that does not fit and a bubble outside the liquid are refused."""
    op = "bottle_image"
    R = _real(radius_mm, "radius_mm", op, lo=0.0, lo_open=True)
    t = _real(wall_mm, "wall_mm", op, lo=0.0, lo_open=True)
    if t >= R:
        raise ValueError("%s: wall_mm (%g) must be thinner than radius_mm (%g)" % (op, t, R))
    H = _real(height_mm, "height_mm", op, lo=0.0, lo_open=True)
    fill = _real(fill_fraction, "fill_fraction", op, lo=0.0, hi=1.0)
    ng = _real(n_glass, "n_glass", op, lo=1.0, lo_open=True, hi=4.0)
    nl = _real(n_liquid, "n_liquid", op, lo=1.0, lo_open=True, hi=4.0)
    na = _real(n_air, "n_air", op, lo=1.0, hi=4.0)
    if na >= min(ng, nl):
        raise ValueError("%s: n_air (%g) must be below n_glass (%g) and n_liquid (%g)" % (op, na, ng, nl))
    men = _real(meniscus_mm, "meniscus_mm", op, lo=0.0)
    dc = _real(camera_distance_mm, "camera_distance_mm", op, lo=0.0, lo_open=True)
    if dc <= 2.0 * R:
        raise ValueError("%s: the camera (%g mm) must be further than one diameter from the axis" % (op, dc))
    pitch_um = _real(pixel_pitch_um, "pixel_pitch_um", op, lo=0.0, lo_open=True)
    light = _choice(light, "light", op, LIGHTS)
    p = pitch_um / 1000.0
    z0 = fill * H
    if z0 + (men if fill > 0.0 else 0.0) > H + 1e-12:
        raise ValueError("%s: the fill line (%g mm) plus the meniscus (%g mm) is above the bottle height (%g mm)" % (op, z0, men, H))
    Ri = R - t
    bubs = _bubble_list(bubbles, Ri, z0, fill, op)
    if size is None:
        nrows = max(int(round(H / p)), 1)
        ncols = max(int(math.ceil(2.3 * R / p)), 3)
    else:
        s = _array(size, "size", op, ndim=1, allow_scalar=False)
        if s.size != 2 or (s < 1).any() or (s != np.round(s)).any():
            raise ValueError("%s: size is (rows, cols) with positive integers, got %r" % (op, s.tolist()))
        nrows, ncols = int(s[0]), int(s[1])
    if nrows * ncols > MAX_PIXELS:
        raise ValueError("%s: %d x %d pixels are over the cap of %d" % (op, nrows, ncols, MAX_PIXELS))
    xpix = (np.arange(ncols) - 0.5 * (ncols - 1)) * p
    zrow = H - (np.arange(nrows) + 0.5) * p
    in_bottle = (zrow >= 0.0) & (zrow <= H)
    mode = np.zeros(nrows, dtype=int)
    rc = np.zeros(nrows)
    if fill > 0.0:
        mode[zrow < z0] = 1
        if men > 0.0:
            sel = (zrow >= z0) & (zrow < z0 + men)
            mode[sel] = 2
            rc[sel] = Ri * ((zrow[sel] - z0) / men) ** (1.0 / MENISCUS_POWER)
    brad = []
    for (bx, by, bz, br) in bubs:
        rr = np.sqrt(np.clip(br * br - (zrow - bz) ** 2, 0.0, None))
        rr = np.where(mode == 1, rr, 0.0)
        brad.append((bx, by, rr))
    bub_any = np.zeros(nrows, dtype=bool)
    for (_, _, rr) in brad:
        bub_any |= rr > 0.0
    special = in_bottle & ((mode == 2) | bub_any)
    img = np.zeros((nrows, ncols))
    unresolved = 0
    bg = _background_row(xpix, dc, light)
    img[~in_bottle] = bg[None, :]
    for m in (0, 1):
        rows = np.nonzero(in_bottle & ~special & (mode == m))[0]
        if rows.size:
            rad, un = _trace_rows(xpix, np.array([m]), np.zeros(1), [], ng, nl, na, R, Ri, dc, light)
            img[rows] = rad[0][None, :]
            unresolved += un * rows.size
    srows = np.nonzero(special)[0]
    chunk = max(1, _MAX_CHUNK // ncols)
    for i0 in range(0, srows.size, chunk):
        sel = srows[i0:i0 + chunk]
        bl = [(bx, by, rr[sel]) for (bx, by, rr) in brad]
        rad, un = _trace_rows(xpix, mode[sel], rc[sel], bl, ng, nl, na, R, Ri, dc, light)
        img[sel] = rad
        unresolved += un
    liquid = (zrow < z0) & in_bottle if fill > 0.0 else np.zeros(nrows, dtype=bool)
    first_liquid = int(np.argmax(liquid)) if liquid.any() else nrows
    # paraxial prediction of the lit band of the filled section
    if fill > 0.0:
        cyl = _wm.cylinder_lens_caustic(R, ng, n_fill=nl, thickness_wall_mm=t)
        efl = float(cyl["efl_mm"])
    else:
        efl = float("inf")
    conv = (1.0 / efl - 1.0 / dc) if math.isfinite(efl) else 0.0
    band = math.radians(PANEL_HALF_ANGLE_DEG) / conv if conv > 0.0 else float("inf")

    def fres_t(a, b):
        return 1.0 - ((a - b) / (a + b)) ** 2

    t_empty = fres_t(na, ng) * fres_t(ng, na) * fres_t(na, ng) * fres_t(ng, na)
    t_fill = fres_t(na, ng) * fres_t(ng, nl) * fres_t(nl, ng) * fres_t(ng, na)
    return {"image": img, "x_mm": xpix, "z_mm": zrow, "pixel_pitch_mm": p, "magnification_px_per_mm": 1.0 / p,
            "fill_row_from_top": first_liquid, "liquid_rows": int(liquid.sum()), "fill_z_mm": z0,
            "paraxial_efl_mm": efl, "band_half_width_mm_paraxial": band, "central_transmittance_empty": t_empty,
            "central_transmittance_filled": t_fill, "unresolved_rays": int(unresolved), "light": light,
            "radius_mm": R, "wall_mm": t, "height_mm": H, "fill_fraction": fill, "n_glass": ng, "n_liquid": nl,
            "n_air": na, "camera_distance_mm": dc, "panel_half_angle_deg": PANEL_HALF_ANGLE_DEG}


def fill_level_from_image(image, pixel_pitch_um, method="edge") -> dict:
    """The fill line measured from a side-view bottle image -> dict (level in mm above the bottom row, row, confidence).

    The row means of the image make a profile down the bottle. ``method="edge"``: the fill line is the row boundary with the
    strongest step of that profile (the largest absolute difference of neighbouring rows). ``method="brightness"``: the profile is
    split in two constant levels at the boundary that leaves the least squared error (a piecewise-constant fit), which does not
    depend on one sharp difference. Rows are counted from the top; the bottom row of the image is taken as the base of the
    bottle (as :func:`bottle_image` renders it), so ``level_mm = (rows below the boundary) * pitch``. The first
    liquid row is ``row`` and the ``step`` is the difference of the two levels (negative when the liquid is darker). ``confidence`` is
    ``|step| / (|step| + 2 sigma)`` with sigma the spread of the profile about its two levels (about 1 for a clean image, small
    when the profile is noise). An image that is constant, or whose row profile has no step above 1e-9 of its mean, is refused:
    there is no fill line to measure (an empty or a full bottle has none). Non-finite images are refused."""
    op = "fill_level_from_image"
    im = _array(image, "image", op, ndim=2, allow_scalar=False)
    if im.shape[0] < 4:
        raise ValueError("%s: the image needs at least 4 rows, got %d" % (op, im.shape[0]))
    pitch = _real(pixel_pitch_um, "pixel_pitch_um", op, lo=0.0, lo_open=True) / 1000.0
    method = _choice(method, "method", op, ("edge", "brightness"))
    if float(np.ptp(im)) == 0.0:
        raise ValueError("%s: the image is constant; there is no fill line to measure" % op)
    prof = im.mean(axis=1)
    scale = max(float(np.abs(prof).mean()), 1e-300)
    if float(np.ptp(prof)) < 1e-9 * scale:
        raise ValueError("%s: the row profile is flat; there is no horizontal fill line in this image" % op)
    nr = prof.size
    if method == "edge":
        diff = prof[1:] - prof[:-1]
        k = int(np.argmax(np.abs(diff)))
    else:
        c1 = np.concatenate([[0.0], np.cumsum(prof)])
        c2 = np.concatenate([[0.0], np.cumsum(prof * prof)])
        b = np.arange(1, nr)
        s1 = c1[b]
        s2 = c1[nr] - c1[b]
        sse = (c2[b] - s1 * s1 / b) + ((c2[nr] - c2[b]) - s2 * s2 / (nr - b))
        k = int(np.argmin(sse - 1e-18 * b))
    row = k + 1
    above, below = prof[:row], prof[row:]
    step = float(below.mean() - above.mean())
    resid = np.concatenate([above - above.mean(), below - below.mean()])
    sigma = float(resid.std())
    conf = abs(step) / (abs(step) + 2.0 * sigma) if (abs(step) + sigma) > 0.0 else 0.0
    return {"level_mm": (nr - row) * pitch, "row": row, "confidence": conf, "step": step, "method": method,
            "profile": prof, "pixel_pitch_mm": pitch}


# --------------------------------------------------------------------------- 3. a wet surface
#: the film thickness (um) over which a water film covers the roughness of the surface: coverage = 1 - exp(-film / FILM_SCALE_UM)
FILM_SCALE_UM = 2.0
#: the index of the dry dielectric surface for its own gloss
N_SURFACE = 1.5
#: the water film fills the micro-roughness: the specular lobe of a fully wet surface is this fraction as wide
FILM_LOBE_FACTOR = 0.5
#: the width (rad) of the specular lobe of the dry micro-roughness, and a floor for it
LOBE_SIGMA_RAD = 0.03


def _fresnel_unpolarised(theta_rad, n1, n2):
    """Unpolarised Fresnel reflectance from index ``n1`` to ``n2`` at the incidence angle (1 beyond the critical angle)."""
    ci = np.cos(theta_rad)
    st = n1 / n2 * np.sin(theta_rad)
    tir = st >= 1.0
    ct = np.sqrt(np.clip(1.0 - st * st, 0.0, None))
    rs = (n1 * ci - n2 * ct) / (n1 * ci + n2 * ct)
    rp = (n2 * ci - n1 * ct) / (n2 * ci + n1 * ct)
    return np.where(tir, 1.0, 0.5 * (rs * rs + rp * rp))


def _internal_reflectance_mean(n):
    """The cosine-weighted hemispherical reflectance of the water-air interface seen from inside:
    ``2 int R(theta) sin(theta) cos(theta) dtheta``; beyond the critical angle R = 1 contributes ``1 - 1/n^2`` exactly, the rest
    is a 64-point Gauss-Legendre rule below it in the variable sqrt(critical angle - theta), in which the edge is smooth."""
    thc = math.asin(1.0 / n)
    x, wt = np.polynomial.legendre.leggauss(64)
    umax = math.sqrt(thc)                           # theta = thc - u^2 removes the square-root edge of R at the critical angle
    u = 0.5 * umax * (x + 1.0)
    wq = 0.5 * umax * wt
    th = thc - u * u
    rr = _fresnel_unpolarised(th, n, 1.0)
    return float(np.sum(wq * 2.0 * u * 2.0 * rr * np.sin(th) * np.cos(th)) + (1.0 - 1.0 / (n * n)))


def _lobe(eps_rad, sigma):
    return np.exp(-0.5 * (eps_rad / sigma) ** 2) / (2.0 * math.pi * sigma * sigma)


def wet_surface_appearance(albedo, roughness, water_film_um, view_deg, light_deg, n_water=None) -> dict:
    """The darkening and the gloss of a surface under a thin water film (Lekner & Dorf 1988; Twomey et al. 1986) -> dict.

    A dry diffuse surface of albedo ``a`` returns ``a`` of the light. Under a water film the light that the surface
    scatters upward reaches the water-air interface; the part beyond the critical angle (and the Fresnel share below it) is
    reflected back down, hits the surface again and is partly absorbed again. With ``r`` the hemispherical,
    cosine-weighted internal reflectance of the interface (computed by quadrature, about 0.47 for water) and ``R_s`` the Fresnel
    reflectance of the incoming light at ``light_deg``, the geometric series of the trapped light gives, for a
    Lambertian surface, ``a_film = a (1 - R_s) (1 - r) / (1 - a r)``. This is below ``a`` for every ``a`` in (0, 1) and the
    darkening is stronger for darker surfaces (a = 0.5 loses about a third). ``water_film_um`` enters only through an
    assumed coverage ``c = 1 - exp(-film / 2 um)`` (a film thicker than a few micrometres wets all the roughness; interference
    in films thinner than a wavelength is not modelled), ``wet_albedo = (1 - c) a + c a_film``, so a film of 0 returns
    ``a`` exactly. The film also glosses: its smooth surface mirrors the light with the Fresnel reflectance of water (``n`` = 1.33; the dry
    dielectric uses 1.5) in a lobe half as wide as the dry one (Gaussian, sigma ``0.03 (1 + 4 roughness)`` rad for the dry
    surface), radiance factor ``pi F G(eps) / cos(light)`` with ``eps`` the angle between
    the mirrored light and the viewing direction (``|light_deg - view_deg|`` in the plane of incidence, the viewer opposite the light).

    ``albedo`` in [0, 1] and ``roughness`` in [0, 1] broadcast with ``water_film_um`` (>= 0); ``view_deg`` and ``light_deg`` are scalars in
    [0, 90). The table has ``wet_albedo``, ``dry_albedo``, ``ratio`` (wet / dry, 1 where the albedo is 0), ``film_albedo`` (the
    fully wet value), ``coverage``, ``internal_reflectance_mean`` (r), ``fresnel_light`` (R_s), ``specular_dry``, ``specular_wet``,
    ``specular_fraction_dry`` / ``specular_fraction_wet`` (the share of the specular radiance factor in the total), ``wet_albedo_rgb``
    (shape + (3,), with the index of water at 0.61 / 0.54 / 0.465 um), ``n_water_rgb``, ``n_water`` and ``darker`` (all wet albedos
    below the dry ones where the film is thick). Albedos or roughness outside [0, 1], a negative film and angles outside [0, 90)
    are refused."""
    op = "wet_surface_appearance"
    a = _array(albedo, "albedo", op, lo=0.0, hi=1.0)
    rough = _array(roughness, "roughness", op, lo=0.0, hi=1.0)
    film = _array(water_film_um, "water_film_um", op, lo=0.0)
    vd = _real(view_deg, "view_deg", op, lo=0.0, hi=90.0, hi_open=True)
    ld = _real(light_deg, "light_deg", op, lo=0.0, hi=90.0, hi_open=True)
    try:
        a, rough, film = np.broadcast_arrays(a, rough, film)
    except ValueError:
        raise ValueError("%s: albedo, roughness and water_film_um do not broadcast together" % op) from None
    n = _water_index(n_water, 0.55, op)
    cov = 1.0 - np.exp(-film / FILM_SCALE_UM)
    rbar = _internal_reflectance_mean(n)
    rs_light = float(_fresnel_unpolarised(math.radians(ld), 1.0, n))
    a_film = a * (1.0 - rs_light) * (1.0 - rbar) / (1.0 - a * rbar)
    wet = (1.0 - cov) * a + cov * a_film
    ratio = np.where(a > 0.0, wet / np.where(a > 0.0, a, 1.0), 1.0)
    sigma_d = LOBE_SIGMA_RAD * (1.0 + 4.0 * rough)
    sigma_w = sigma_d * FILM_LOBE_FACTOR
    eps = math.radians(abs(ld - vd))
    cosl = max(math.cos(math.radians(ld)), 1e-3)
    f_dry = float(_fresnel_unpolarised(math.radians(ld), 1.0, N_SURFACE))
    f_wet = rs_light
    spec_d = math.pi * f_dry * _lobe(eps, sigma_d) / cosl
    spec_f = math.pi * f_wet * _lobe(eps, sigma_w) / cosl
    spec_w = (1.0 - cov) * spec_d + cov * spec_f
    nrgb = np.array([_wm.fresnel_water_air(0.0, wavelength_um=w_)["n_water"] if n_water is None else n
                     for w_ in _wm.RGB_WAVELENGTHS_UM])
    rgb = []
    for nc in nrgb:
        rb = _internal_reflectance_mean(float(nc))
        rsl = float(_fresnel_unpolarised(math.radians(ld), 1.0, float(nc)))
        af = a * (1.0 - rsl) * (1.0 - rb) / (1.0 - a * rb)
        rgb.append((1.0 - cov) * a + cov * af)
    thick = film > 5.0 * FILM_SCALE_UM
    darker = bool(np.all(wet[thick & (a > 0.0)] < a[thick & (a > 0.0)])) if np.any(thick & (a > 0.0)) else True
    return {"wet_albedo": wet, "dry_albedo": a, "ratio": ratio, "film_albedo": a_film, "coverage": cov,
            "internal_reflectance_mean": rbar, "fresnel_light": rs_light, "specular_dry": spec_d, "specular_wet": spec_w,
            "specular_fraction_dry": spec_d / (spec_d + a + 1e-300), "specular_fraction_wet": spec_w / (spec_w + wet + 1e-300),
            "wet_albedo_rgb": np.stack(rgb, axis=-1), "n_water_rgb": nrgb, "n_water": n, "darker": darker,
            "film_scale_um": FILM_SCALE_UM}


def _michelson(ok, defect):
    return float((ok - defect) / (ok + defect)) if (ok + defect) > 0.0 else 0.0


def wet_dry_inspection_pair(texture, defect_mask, roughness, water_film_um, light_deg, view_deg, n_water=None,
                            seed=268, normal_sigma_px=2.0) -> dict:
    """The same textured plate rendered dry and wet, and the contrast of its defect in each -> dict.

    ``texture`` (H, W) in [0, 1] is the diffuse albedo of the plate and ``defect_mask`` (H, W, bool) marks the defect (at least
    one pixel inside and one outside). Both images use the per-pixel :func:`wet_surface_appearance` for the diffuse part. The
    specular part uses a local normal: a Gaussian-smoothed random height map (``seed``, smoothing ``normal_sigma_px``) whose
    slopes are scaled to an RMS slope per axis of ``roughness``; each pixel mirrors the light with the Fresnel reflectance of its
    local incidence angle into the Gaussian lobe of ``wet_surface_appearance`` about the viewing direction, so a glint appears
    where the local normal bisects the light and the view and moves when ``light_deg`` changes. The dry and the wet plate share the normals,
    so they differ only by the film. ``light_deg`` is in the xz plane from the plate normal, the viewer on the other side at ``view_deg``.
    The defect contrast is the Michelson contrast ``(mean_ok - mean_defect) / (mean_ok + mean_defect)`` of the region means, reported
    for the whole image and for the diffuse part alone. Because the film darkens dark pixels proportionally more (the factor
    ``(1 - r) / (1 - a r)`` grows with ``a``), a dark defect on a brighter plate gains diffuse contrast when wet; the glints (shared
    by both regions) pull the total contrast the other way, so the table has both and ``predicted_diffuse_contrast_wet`` (the
    one-step prediction from the region mean albedos).

    The table has ``dry``, ``wet``, ``diffuse_dry``, ``diffuse_wet``, ``specular_dry``, ``specular_wet`` (images), ``contrast_dry``,
    ``contrast_wet``, ``contrast_diffuse_dry``, ``contrast_diffuse_wet``, ``predicted_diffuse_contrast_wet``, ``coverage``,
    ``glint_pixels_dry`` / ``glint_pixels_wet`` (pixels whose specular term exceeds the median diffuse albedo) and ``normals``. A film of 0 gives
    identical images. Shapes that differ, a mask without both classes, textures outside [0, 1] or a negative film are refused."""
    op = "wet_dry_inspection_pair"
    tex = _array(texture, "texture", op, ndim=2, lo=0.0, hi=1.0, allow_scalar=False)
    if tex.size > MAX_PIXELS:
        raise ValueError("%s: the texture has %d pixels, over the cap of %d" % (op, tex.size, MAX_PIXELS))
    m = np.asarray(defect_mask)
    if m.dtype != bool or m.shape != tex.shape:
        raise ValueError("%s: defect_mask must be a bool array of the texture shape %r" % (op, tex.shape))
    if not m.any() or m.all():
        raise ValueError("%s: defect_mask needs at least one defect pixel and one good pixel" % op)
    rough = _real(roughness, "roughness", op, lo=0.0, hi=1.0)
    film = _real(water_film_um, "water_film_um", op, lo=0.0)
    ld = _real(light_deg, "light_deg", op, lo=0.0, hi=90.0, hi_open=True)
    vd = _real(view_deg, "view_deg", op, lo=0.0, hi=90.0, hi_open=True)
    sd = _int(seed, "seed", op, 0, 2 ** 31 - 1)
    sg = _real(normal_sigma_px, "normal_sigma_px", op, lo=0.0, lo_open=True, hi=64.0)
    from scipy.ndimage import gaussian_filter
    ap = wet_surface_appearance(tex, rough, film, vd, ld, n_water=n_water)
    rng = np.random.default_rng(sd)
    hmap = gaussian_filter(rng.standard_normal(tex.shape), sg, mode="wrap")
    sy, sx = np.gradient(hmap)
    rms = math.sqrt(float(np.mean(sx * sx + sy * sy)) / 2.0)
    scale = rough / rms if rms > 0.0 else 0.0
    sx, sy = sx * scale, sy * scale
    nn = np.sqrt(1.0 + sx * sx + sy * sy)
    nx_, ny_, nz_ = -sx / nn, -sy / nn, 1.0 / nn
    lv = np.array([math.sin(math.radians(ld)), 0.0, math.cos(math.radians(ld))])
    vv = np.array([-math.sin(math.radians(vd)), 0.0, math.cos(math.radians(vd))])
    nl = nx_ * lv[0] + ny_ * lv[1] + nz_ * lv[2]
    nv = nx_ * vv[0] + ny_ * vv[1] + nz_ * vv[2]
    rx, ry, rz = 2 * nl * nx_ - lv[0], 2 * nl * ny_ - lv[1], 2 * nl * nz_ - lv[2]
    eps = np.arccos(np.clip(rx * vv[0] + ry * vv[1] + rz * vv[2], -1.0, 1.0))
    lit = (nl > 1e-3) & (nv > 1e-3)
    theta_loc = np.arccos(np.clip(nl, 0.0, 1.0))
    n = ap["n_water"]
    f_dry = _fresnel_unpolarised(theta_loc, 1.0, N_SURFACE)
    f_wet = _fresnel_unpolarised(theta_loc, 1.0, n)
    cosl = np.maximum(nl, 1e-3)
    sd_ = LOBE_SIGMA_RAD
    spec_d = np.where(lit, math.pi * f_dry * _lobe(eps, sd_) / cosl, 0.0)
    spec_f = np.where(lit, math.pi * f_wet * _lobe(eps, sd_ * FILM_LOBE_FACTOR) / cosl, 0.0)
    cov = float(ap["coverage"].flat[0])
    spec_w = (1.0 - cov) * spec_d + cov * spec_f
    dif_d = tex
    dif_w = ap["wet_albedo"]
    dry = dif_d + spec_d
    wet = dif_w + spec_w
    c_dry = _michelson(float(dry[~m].mean()), float(dry[m].mean()))
    c_wet = _michelson(float(wet[~m].mean()), float(wet[m].mean()))
    cd_dry = _michelson(float(dif_d[~m].mean()), float(dif_d[m].mean()))
    cd_wet = _michelson(float(dif_w[~m].mean()), float(dif_w[m].mean()))
    pred = wet_surface_appearance(np.array([float(tex[~m].mean()), float(tex[m].mean())]), rough, film, vd, ld, n_water=n_water)
    c_pred = _michelson(float(pred["wet_albedo"][0]), float(pred["wet_albedo"][1]))
    med = float(np.median(tex))
    return {"dry": dry, "wet": wet, "diffuse_dry": dif_d, "diffuse_wet": dif_w, "specular_dry": spec_d, "specular_wet": spec_w,
            "contrast_dry": c_dry, "contrast_wet": c_wet, "contrast_diffuse_dry": cd_dry, "contrast_diffuse_wet": cd_wet,
            "predicted_diffuse_contrast_wet": c_pred, "coverage": cov, "glint_pixels_dry": int((spec_d > med).sum()),
            "glint_pixels_wet": int((spec_w > med).sum()), "normals": np.stack([nx_, ny_, nz_], axis=-1)}


# --------------------------------------------------------------------------- 4. a hull seen through water with a lamp
def underwater_inspection_image(scene_albedo, distance_map_m, water_type, light="camera", lamp_power=1.0,
                                camera_distance_m=None, depth_m=2.0, exposure_photons=1.0e4, fov_deg=60.0,
                                beam_exponent=6.0) -> dict:
    """A hull or pipe inspection image: a lamp at the camera lights a wall through water -> dict (image, per-pixel SNR).

    A thin layer over :func:`watermedia.underwater_image` (the Akkaynak and Treibitz form: direct signal plus backscatter veil).
    ``scene_albedo`` is (H, W) or (H, W, 3) and ``distance_map_m`` (H, W) the camera-to-surface distance (> 0). ``light="camera"``: the
    only light is a lamp at the camera of ``lamp_power`` (relative power at 1 m); the wall is lit by
    ``lamp_power exp(-c r) / r^2`` (beam attenuation ``c`` of the water at 0.61 / 0.54 / 0.465 um), reflects its albedo and the return
    path attenuates with ``Kd``. The lamp also lights the water in front of the lens: the veil of
    the water type's single-scattering backscatter grows as ``1 - exp(-Kd r)`` and is weighted by the lamp's beam pattern,
    ``cos(theta)^beam_exponent`` with ``theta`` the angle of the pixel from the axis (``fov_deg`` across the width): strongest in the
    centre, where the lamp and the camera look at the same water. A baseline between lamp and camera, ``camera_distance_m`` (default
    None: the lamp is at the camera), reduces the overlap of the lit and the seen water by ``1 / (1 + (baseline / r)^2)``.
    ``light="ambient"``: daylight at ``depth_m`` and a veil of the daylight, uniform over the image (``lamp_power`` is not used). ``light="both"``: the lamp and the daylight together (the signals and the veils add).

    ``snr = sqrt(N) direct / sqrt(direct + backscatter + 1e-12)`` is the shot-noise limited signal to noise of the direct signal against
    its own shot noise and the shot noise of the veil (``N = exposure_photons`` per unit radiance): it falls with distance because the
    direct term falls and the veil grows. ``snr_clear`` is the same expression for water that does not
    attenuate or scatter (equal to ``snr`` as the distance tends to 0). The table has ``image`` (H, W, 3), ``direct``, ``backscatter``,
    ``snr``, ``snr_clear``, ``snr_mean`` (over the three bands), ``veil_profile`` (H, W), ``transmission``, ``beam_attenuation_c``,
    ``kd``, ``water_type`` and ``light``. A zero or negative distance, an albedo outside [0, 1], an unknown water type and a bad light
    are refused."""
    op = "underwater_inspection_image"
    alb = _array(scene_albedo, "scene_albedo", op, lo=0.0, hi=1.0, allow_scalar=False)
    if alb.ndim == 2:
        alb = np.repeat(alb[:, :, None], 3, axis=2)
    if alb.ndim != 3 or alb.shape[2] != 3:
        raise ValueError("%s: scene_albedo must be (H, W) or (H, W, 3), got shape %r" % (op, alb.shape))
    h, w, _ = alb.shape
    if alb.size > MAX_PIXELS:
        raise ValueError("%s: the image has %d elements, over the cap of %d" % (op, alb.size, MAX_PIXELS))
    dist = _array(distance_map_m, "distance_map_m", op, lo=0.0)
    if dist.ndim == 0:
        dist = np.full((h, w), float(dist))
    if dist.shape != (h, w):
        raise ValueError("%s: distance_map_m must be a scalar or (%d, %d), got shape %r" % (op, h, w, dist.shape))
    if (dist <= 0.0).any():
        raise ValueError("%s: distance_map_m must be > 0 (the lamp irradiance diverges at 0)" % op)
    light = _choice(light, "light", op, ("camera", "ambient", "both"))
    lamp = _real(lamp_power, "lamp_power", op, lo=0.0, lo_open=True)
    depth = _real(depth_m, "depth_m", op, lo=0.0)
    big_n = _real(exposure_photons, "exposure_photons", op, lo=0.0, lo_open=True)
    fov = _real(fov_deg, "fov_deg", op, lo=0.0, lo_open=True, hi=170.0)
    bexp = _real(beam_exponent, "beam_exponent", op, lo=0.0)
    base = None if camera_distance_m is None else _real(camera_distance_m, "camera_distance_m", op, lo=0.0)
    att = _wm.water_attenuation(np.array(_wm.RGB_WAVELENGTHS_UM), water_type)
    c = att["c"]
    ones = np.ones(3)
    def lamp_part():
        lit = lamp * np.exp(-dist[:, :, None] * c[None, None, :]) / (dist[:, :, None] ** 2)
        o = _wm.underwater_image(alb * lit, 0.0, dist, water_type, illumination=lamp * ones, apply_ambient=False)
        u = (np.arange(w) - 0.5 * (w - 1)) / (0.5 * w)
        v = (np.arange(h) - 0.5 * (h - 1)) / (0.5 * h)
        theta = np.arctan(np.hypot(u[None, :], v[:, None]) * math.tan(math.radians(fov) / 2.0))
        prof = np.cos(theta) ** bexp
        if base is not None:
            prof = prof / (1.0 + (base / dist) ** 2)
        return o, prof

    if light == "camera":
        out, profile = lamp_part()
        direct0 = alb * lamp / (dist[:, :, None] ** 2)
        direct = out["direct"]
        back = out["backscatter"] * profile[:, :, None]
    elif light == "ambient":
        out = _wm.underwater_image(alb, depth, dist, water_type, apply_ambient=True)
        profile = np.ones((h, w))
        direct0 = alb
        direct = out["direct"]
        back = out["backscatter"]
    else:
        out_l, profile = lamp_part()
        out = _wm.underwater_image(alb, depth, dist, water_type, apply_ambient=True)
        direct0 = alb * (lamp / (dist[:, :, None] ** 2) + 1.0)
        direct = out_l["direct"] + out["direct"]
        back = out_l["backscatter"] * profile[:, :, None] + out["backscatter"]
    floor = 1e-12
    snr = math.sqrt(big_n) * direct / np.sqrt(direct + back + floor)
    snr_clear = math.sqrt(big_n) * direct0 / np.sqrt(direct0 + floor)
    return {"image": direct + back, "direct": direct, "backscatter": back, "snr": snr, "snr_clear": snr_clear,
            "snr_mean": snr.mean(axis=2), "veil_profile": profile, "transmission": out["transmission"],
            "beam_attenuation_c": c, "kd": att["kd"], "water_type": water_type, "light": light,
            "exposure_photons": big_n}


# --------------------------------------------------------------------------- 5. segmenting the caustic lines
def _otsu(values, nbins=256):
    lo, hi = float(values.min()), float(values.max())
    hist, edges = np.histogram(values, bins=nbins, range=(lo, hi))
    p = hist.astype(np.float64) / hist.sum()
    centres = 0.5 * (edges[:-1] + edges[1:])
    w0 = np.cumsum(p)
    m0 = np.cumsum(p * centres)
    mt = m0[-1]
    w1 = 1.0 - w0
    with np.errstate(divide="ignore", invalid="ignore"):
        between = (mt * w0 - m0) ** 2 / (w0 * w1)
    between = np.where(np.isfinite(between), between, -1.0)
    return float(edges[int(np.argmax(between)) + 1])


def _fundamental_period(profile):
    """The period (samples) of the lowest strong peak of the spectrum of a 1-D profile (NaN for a flat profile)."""
    p = profile - profile.mean()
    n = p.size
    if not np.any(np.abs(p) > 1e-12):
        return float("nan")
    mag = np.abs(np.fft.rfft(p))[: n // 2 + 1]
    mag[0] = 0.0
    top = mag.max()
    k = int(np.nonzero(mag >= 0.5 * top)[0][0])
    if 1 <= k < mag.size - 1:
        a, b, c = mag[k - 1], mag[k], mag[k + 1]
        den = a - 2.0 * b + c
        k_f = k + (0.5 * (a - c) / den if den != 0.0 else 0.0)
    else:
        k_f = float(k)
    return float(n / k_f)


def caustic_floor_segmentation(irradiance, method="otsu") -> dict:
    """Segment the caustic lines of a floor irradiance image -> dict (mask, threshold, line period).

    The bright web of caustics on a pool floor is what a crack detector mistakes for cracks. ``method="otsu"``: the finite
    values are normalised by their mean and split into two classes at the Otsu threshold (256 bins); the mask is the bright
    class. ``method="fold"``: ridge detection by curvature: the smaller eigenvalue of the Hessian of the Gaussian-smoothed
    irradiance (sigma 1 pixel) is the curvature across a line; where it is strongly negative (above the Otsu threshold of its negative part)
    and the irradiance is above its mean, the pixel is on a caustic ridge. ``inf`` pixels (the folds of the wavefront method of
    :func:`caustic_irradiance`) are caustic by definition and are always in the mask. The table has ``mask`` (bool), ``threshold``,
    ``fraction`` (of pixels in the mask), ``period_px_x`` / ``period_px_y`` (the fundamental period in pixels of the column and
    row profiles of the mask, from the lowest strong spectral peak refined by a parabola; NaN when the profile is flat),
    ``dominant_axis`` ("x", "y" or "none": the axis whose profile of the mask varies most) and ``n_inf``. NaN, negative values, an
    image under 8 x 8 and a constant image (no caustic to find) are refused."""
    op = "caustic_floor_segmentation"
    method = _choice(method, "method", op, ("otsu", "fold"))
    e = np.asarray(irradiance)
    if e.dtype.kind not in "iuf" or e.ndim != 2 or e.shape[0] < 8 or e.shape[1] < 8:
        raise ValueError("%s: irradiance must be a numeric 2-D array of at least 8 x 8, got dtype %s shape %r" % (op, e.dtype, e.shape))
    e = e.astype(np.float64)
    if np.isnan(e).any() or (e < 0.0).any() or np.isneginf(e).any():
        raise ValueError("%s: irradiance has NaN or negative values (only +inf is allowed, for folds)" % op)
    infm = np.isposinf(e)
    fin = e[~infm]
    if fin.size == 0 or float(np.ptp(fin)) == 0.0:
        raise ValueError("%s: the irradiance is constant; there is no caustic to segment" % op)
    mean = float(fin.mean())
    if mean <= 0.0:
        raise ValueError("%s: the irradiance has zero mean" % op)
    en = np.where(infm, fin.max(), e) / mean
    if method == "otsu":
        thr = _otsu(en[~infm])
        mask = en > thr
    else:
        from scipy.ndimage import gaussian_filter
        sm = gaussian_filter(en, 1.0, mode="reflect")
        hyy = gaussian_filter(en, 1.0, order=(2, 0), mode="reflect")
        hxx = gaussian_filter(en, 1.0, order=(0, 2), mode="reflect")
        hxy = gaussian_filter(en, 1.0, order=(1, 1), mode="reflect")
        tr = 0.5 * (hxx + hyy)
        lam_min = tr - np.sqrt(0.25 * (hxx - hyy) ** 2 + hxy * hxy)
        s = np.clip(-lam_min, 0.0, None)
        if float(s.max()) == 0.0:
            raise ValueError("%s: no ridge curvature in the image" % op)
        thr = _otsu(s)
        mask = (s > thr) & (sm > 1.0)
    mask = mask | infm
    px = _fundamental_period(mask.mean(axis=0))
    py = _fundamental_period(mask.mean(axis=1))
    vx, vy = float(mask.mean(axis=0).std()), float(mask.mean(axis=1).std())
    axis = "none" if max(vx, vy) < 1e-12 else ("x" if vx >= vy else "y")
    return {"mask": mask, "threshold": thr, "fraction": float(mask.mean()), "period_px_x": px, "period_px_y": py,
            "dominant_axis": axis, "n_inf": int(infm.sum()), "method": method}
