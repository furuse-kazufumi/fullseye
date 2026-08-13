"""Measurement primitives (numpy + scipy) — line intensity profiles and simple
geometry, the "measure" tools a vision IDE provides. Points are (row, col)."""
from __future__ import annotations

import numpy as np

__all__ = ["line_profile", "distance", "angle", "profile_stats"]


def line_profile(image, p0, p1, num=None):
    """Intensity along the segment p0 -> p1 (bilinear sampled). Returns a 1-D array
    (gray) or (N, 3) (color). ``num`` samples defaults to the pixel length."""
    from scipy.ndimage import map_coordinates
    img = np.asarray(image, np.float64)
    (y0, x0), (y1, x1) = p0, p1
    n = int(num) if num else int(np.hypot(y1 - y0, x1 - x0)) + 1
    ys = np.linspace(y0, y1, n)
    xs = np.linspace(x0, x1, n)
    if img.ndim == 2:
        return map_coordinates(img, [ys, xs], order=1, mode="nearest")
    return np.stack([map_coordinates(img[..., c], [ys, xs], order=1, mode="nearest")
                     for c in range(img.shape[2])], axis=-1)


def distance(p0, p1) -> float:
    """Euclidean distance between two (row, col) points."""
    return float(np.hypot(p1[0] - p0[0], p1[1] - p0[1]))


def angle(p0, p1) -> float:
    """Angle of the segment p0 -> p1 in degrees (image y downward), in (-180, 180]."""
    return float(np.degrees(np.arctan2(p1[0] - p0[0], p1[1] - p0[1])))


def profile_stats(prof) -> dict:
    """min / max / mean / and the index of the strongest edge (|gradient| peak)."""
    p = np.asarray(prof, np.float64)
    g = np.abs(np.gradient(p if p.ndim == 1 else p.mean(-1)))
    return {"n": int(len(p)), "min": float(np.min(p)), "max": float(np.max(p)),
            "mean": float(np.mean(p)), "edge_at": int(np.argmax(g))}
