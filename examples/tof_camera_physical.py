"""Physical 3-D scene renderer used by the ToF camera exhibit.

The renderer is deliberately small and analytic: every sub-ray is intersected
with planes, axis-aligned boxes, and a thin square pole.  No raster masks are
painted after rendering.  Nine sub-rays per output pixel are combined as
complex modulation phasors, which creates mixed edge pixels naturally.
"""
from __future__ import annotations

import numpy as np

C = 299_792_458.0


def _box_hit(dx, dy, dz, bounds):
    """Return distance along a ray to an axis-aligned box, or infinity."""
    lo = np.asarray(bounds[::2], float)
    hi = np.asarray(bounds[1::2], float)
    direction = np.stack((dx, dy, dz), axis=-1)
    inv = np.divide(1.0, direction, out=np.full_like(direction, np.inf), where=direction != 0)
    t0 = lo * inv
    t1 = hi * inv
    near = np.max(np.minimum(t0, t1), axis=-1)
    far = np.min(np.maximum(t0, t1), axis=-1)
    return np.where((far >= np.maximum(near, 0.0)) & (near > 0), near, np.inf)


def render_scene(h=240, w=320, supersample=3, seed=274, noisy=True,
                 falloff=True, multipath=True, frequency_hz=20e6):
    """Render a 70 by 55 degree pinhole view and a noisy iToF observation."""
    if supersample != 3:
        raise ValueError("the physical footprint gate requires 3x3 supersampling")
    sy, sx = np.meshgrid(np.arange(h * 3), np.arange(w * 3), indexing="ij")
    fx = (w / 2) / np.tan(np.deg2rad(70 / 2))
    fy = (h / 2) / np.tan(np.deg2rad(55 / 2))
    dx = (sx + .5 - 1.5 * w) / (3 * fx)
    dy = (sy + .5 - 1.5 * h) / (3 * fy)
    dz = np.ones_like(dx)
    norm = np.sqrt(dx * dx + dy * dy + 1)
    dx, dy, dz = dx / norm, dy / norm, dz / norm

    # First-hit ray caster: back wall, left wall, floor, pallet/boxes, pole,
    # a glass pane, and a glossy plate.  y grows downwards from the camera.
    shape = dx.shape
    dist = np.full(shape, np.inf)
    rho = np.zeros(shape)
    label = np.zeros(shape, np.int16)

    def offer(t, reflectivity, code, valid=None):
        nonlocal dist, rho, label
        mask = np.isfinite(t) & (t > 0) & (t < dist)
        if valid is not None:
            mask &= valid
        dist = np.where(mask, t, dist)
        rv = reflectivity if np.ndim(reflectivity) else np.full(shape, reflectivity)
        rho = np.where(mask, rv, rho)
        label = np.where(mask, code, label)

    t = 5.2 / dz
    x, y = t * dx, t * dy
    checker = np.where(((np.floor((x + 2.6) / .35) + np.floor((y + .8) / .35)) % 2) == 0, .78, .09)
    offer(t, checker, 1, (np.abs(x) <= 4.2) & (y >= -3.0) & (y <= 3.0))
    t = -3.0 / dx
    offer(t, .48, 2, (t * dz < 5.2) & (t * dy > -3.0) & (t * dy < 3.0))
    t = 1.55 / dy
    offer(t, .38, 3, (t * dz > .5) & (t * dz < 5.2) & (np.abs(t * dx) < 3.0))

    objects = [
        ((-1.65, 1.45, 1.10, 1.55, 3.15, 3.65), .30, 4),  # pallet
        ((-1.45, -.45, .35, 1.55, 2.38, 3.15), .58, 5),
        ((-.32, .62, .60, 1.55, 2.75, 3.65), .72, 6),
        ((.75, 1.55, .82, 1.55, 3.20, 4.05), .46, 7),
        ((1.78, 1.84, -.15, 1.55, 2.10, 4.55), .62, 8),  # pole
        ((.90, 1.70, -.55, .48, 4.58, 4.64), .92, 9),   # metal plate
        ((-.65, .48, -.65, .42, 3.88, 3.91), .16, 10), # glass
    ]
    for bounds, refl, code in objects:
        offer(_box_hit(dx, dy, dz, bounds), refl, code)

    # Co-located illumination: Lambertian cosine, lens cos^4 vignetting and
    # inverse-square spreading.  A dark offset is kept separate from contrast.
    incidence = np.clip(dz, 0, 1)
    # The slightly super-linear material response represents modulation
    # contrast loss on very dark targets and reproduces the long amplitude
    # tail measured between dark and retro-bright surfaces.
    signal = 2.6e5 * rho ** 1.30
    if falloff:
        signal *= incidence ** 5 / np.maximum(dist * dist, .1)
    signal = np.clip(signal, 2, None)
    contrast = .72
    phase = 4 * np.pi * frequency_hz * dist / C
    phasor = contrast * signal * np.exp(1j * phase)

    # A second diffuse bounce becomes strongest at wall-wall/floor-wall
    # junctions.  Its longer path bends those regions away from the camera.
    xyz_x, xyz_y, xyz_z = dist * dx, dist * dy, dist * dz
    near_corner = np.exp(-((xyz_x + 3.0) / .42) ** 2) + np.exp(-((xyz_y - 1.55) / .30) ** 2)
    mpi_ratio = np.clip(.16 * near_corner, 0, .34) if multipath else np.zeros(shape)
    mpi_extra = .62 + .10 * np.sin(2.2 * xyz_z)
    phasor += contrast * signal * mpi_ratio * np.exp(1j * (phase + 4 * np.pi * frequency_hz * mpi_extra / C))

    def bin3(a):
        return a.reshape(h, 3, w, 3).mean(axis=(1, 3))

    clean_phasor = bin3(phasor)
    clean_signal = bin3(signal)
    truth = bin3(dist)
    edge_mix = 1 - np.abs(clean_phasor) / np.maximum(bin3(np.abs(phasor)), 1e-9)
    dark_level = 120.0
    background_electrons = 18000.0
    read_noise = 6.0
    rng = np.random.default_rng(seed)
    measured = clean_phasor.copy()
    if noisy:
        # Quadrature variance from shot noise, background/dark and read noise.
        sigma_q = np.sqrt(np.maximum(clean_signal + background_electrons + dark_level, 1) / 2 + read_noise ** 2)
        measured += rng.normal(0, sigma_q) + 1j * rng.normal(0, sigma_q)
    amplitude = np.abs(measured)
    wrapped = np.mod(np.angle(measured), 2 * np.pi) * C / (4 * np.pi * frequency_hz)
    return {
        "depth_truth": truth, "depth": wrapped, "amplitude": amplitude,
        "clean_depth": np.mod(np.angle(clean_phasor), 2*np.pi) * C/(4*np.pi*frequency_hz),
        "reflectivity": bin3(rho), "labels": np.rint(bin3(label)).astype(np.int16),
        "edge_mix": edge_mix, "mpi_ratio": bin3(mpi_ratio),
        "ray_x": bin3(dx / dz), "ray_y": bin3(dy / dz),
        "signal": clean_signal, "dark_level": dark_level,
        "read_noise": read_noise, "background_electrons": background_electrons,
        "frequency_hz": frequency_hz,
    }


def make_stages(h=240, w=320):
    """Return matched ablation views: ideal, falloff, mixed/noisy, full MPI."""
    ideal = render_scene(h, w, noisy=False, falloff=False, multipath=False)
    falloff = render_scene(h, w, noisy=False, falloff=True, multipath=False)
    noisy = render_scene(h, w, noisy=True, falloff=True, multipath=False)
    full = render_scene(h, w, noisy=True, falloff=True, multipath=True)
    return ideal, falloff, noisy, full
