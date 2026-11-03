"""Shared synthetic inputs for the recipe books (structured, with a closed-form truth).

Every generator takes ``variant`` (0, 1, ...) and returns ``{"value", "aux", "truth"}``. Variants must
differ in their truth (another radius, another slope, another count) — the tests run each recipe on
two variants and require the output to move with the input (a constant answer is not a measurement).
Keep inputs small (tests run every recipe twice in a few seconds each).
"""
from __future__ import annotations

import numpy as np


def rng(variant: int, salt: int = 0) -> np.random.Generator:
    return np.random.default_rng(1000 + 17 * int(variant) + int(salt))


def disk_image(variant: int, n: int = 96, noise: float = 0.02):
    """Bright disk on a dark background; truth = area (px), radius, centre (row, col)."""
    r = 18.0 + 6.0 * variant
    cy, cx = n / 2 + 3 * variant, n / 2 - 2 * variant
    yy, xx = np.mgrid[0:n, 0:n]
    img = 0.15 + 0.7 * (((yy - cy) ** 2 + (xx - cx) ** 2) <= r * r)
    img = np.clip(img + noise * rng(variant).standard_normal((n, n)), 0, 1)
    return {"value": img.astype(np.float64), "aux": {},
            "truth": {"area": float(np.pi * r * r), "radius": r, "diameter": 2 * r, "row": cy, "col": cx}}


def blobs_image(variant: int, n: int = 96, noise: float = 0.03):
    """k separated bright disks (k = 3 + variant) of radius 6..8; truth = count, total area."""
    k = 3 + int(variant)
    g = rng(variant, 1)
    yy, xx = np.mgrid[0:n, 0:n]
    img = np.full((n, n), 0.1)
    area = 0.0
    centres = [(20 + 28 * (i % 3), 20 + 28 * (i // 3)) for i in range(k)]
    for (cy, cx) in centres:
        r = 6.0 + (len(centres) % 3)
        m = ((yy - cy) ** 2 + (xx - cx) ** 2) <= r * r
        img[m] = 0.85
        area += float(m.sum())
    img = np.clip(img + noise * g.standard_normal((n, n)), 0, 1)
    return {"value": img, "aux": {}, "truth": {"count": k, "area_px": area, "centres": centres}}


def textured_image(variant: int, n: int = 64):
    """Sinusoidal texture of period 6 + 2·variant px with a little noise; truth = period."""
    p = 6.0 + 2.0 * variant
    yy, xx = np.mgrid[0:n, 0:n]
    img = 0.5 + 0.35 * np.sin(2 * np.pi * xx / p) * np.cos(2 * np.pi * yy / (p * 1.5))
    img = np.clip(img + 0.02 * rng(variant, 2).standard_normal((n, n)), 0, 1)
    return {"value": img, "aux": {}, "truth": {"period": p}}


def step_edge_image(variant: int, n: int = 64):
    """Vertical step edge at column 24 + 8·variant (dark left, bright right); truth = edge column."""
    c = 24 + 8 * int(variant)
    img = np.full((n, n), 0.2)
    img[:, c:] = 0.8
    img = np.clip(img + 0.01 * rng(variant, 3).standard_normal((n, n)), 0, 1)
    return {"value": img, "aux": {}, "truth": {"edge_col": c - 0.5}}


def tilted_plane_depth(variant: int, n: int = 48, cell: float = 1.0):
    """DEM / depth map of a plane z = s·x (s = 0.2 + 0.2·variant); truth = slope (deg), rise per cell."""
    s = 0.2 + 0.2 * variant
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    z = s * xx * cell + 10.0
    return {"value": z, "aux": {"cell_size": cell},
            "truth": {"slope_deg": float(np.degrees(np.arctan(s))), "gradient": s}}


def sphere_points(variant: int, n: int = 600):
    """Points on a sphere of radius 1 + 0.5·variant centred at (0.2·v, 0, 0.1); truth = radius, centre."""
    r = 1.0 + 0.5 * variant
    c = np.array([0.2 * variant, 0.0, 0.1])
    g = rng(variant, 4)
    u = g.standard_normal((n, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    return {"value": c + r * u, "aux": {}, "truth": {"radius": r, "center": c.tolist()}}


def plane_points(variant: int, n: int = 500):
    """Points on the plane z = 0.1·v·x + 0.5 with 1 % noise; truth = normal z-component, offset."""
    g = rng(variant, 5)
    xy = g.uniform(-1, 1, (n, 2))
    a = 0.1 * variant
    z = a * xy[:, 0] + 0.5 + 0.002 * g.standard_normal(n)
    nrm = np.array([-a, 0.0, 1.0]) / np.sqrt(a * a + 1)
    return {"value": np.column_stack([xy, z]), "aux": {}, "truth": {"normal_z": float(nrm[2]), "tilt_deg": float(np.degrees(np.arctan(a)))}}


def sine_signal(variant: int, n: int = 1024, fs: float = 1000.0):
    """Sine of 50 + 25·variant Hz sampled at fs; truth = frequency, amplitude."""
    f = 50.0 + 25.0 * variant
    t = np.arange(n) / fs
    amp = 1.0 + 0.5 * variant
    x = amp * np.sin(2 * np.pi * f * t) + 0.01 * rng(variant, 6).standard_normal(n)
    return {"value": x, "aux": {"fs": fs}, "truth": {"freq": f, "amp": amp}}


def rgb_image(variant: int, n: int = 48):
    """RGB image: left half red-ish, right half blue-ish (variant shifts the split); truth = split column."""
    c = 20 + 6 * int(variant)
    img = np.zeros((n, n, 3))
    img[:, :c] = (0.8, 0.2, 0.1)
    img[:, c:] = (0.1, 0.3, 0.8)
    img = np.clip(img + 0.01 * rng(variant, 7).standard_normal(img.shape), 0, 1)
    return {"value": img, "aux": {}, "truth": {"split_col": c}}


def volume_ball(variant: int, n: int = 24):
    """3-D volume with a bright ball of radius 5 + 2·variant; truth = voxel volume."""
    r = 5.0 + 2.0 * variant
    zz, yy, xx = np.mgrid[0:n, 0:n, 0:n]
    m = ((zz - n / 2) ** 2 + (yy - n / 2) ** 2 + (xx - n / 2) ** 2) <= r * r
    v = 0.1 + 0.8 * m + 0.01 * rng(variant, 8).standard_normal(m.shape)
    return {"value": v, "aux": {}, "truth": {"voxels": int(m.sum()), "volume": 4 / 3 * np.pi * r ** 3}}


COMMON_SAMPLES = {
    "disk_image": disk_image, "blobs_image": blobs_image, "textured_image": textured_image,
    "step_edge_image": step_edge_image, "tilted_plane_depth": tilted_plane_depth,
    "sphere_points": sphere_points, "plane_points": plane_points, "sine_signal": sine_signal,
    "rgb_image": rgb_image, "volume_ball": volume_ball,
}
