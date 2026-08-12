"""Terrain / traversability building blocks (numpy + scipy only).

Turns a 3-D point cloud (e.g. from :mod:`stereo`) into a robot-centric 2.5-D
elevation map — the "mountain-map"/heightmap used for locomotion — and derives a
traversability mask (step + slope) for foothold selection and obstacle
avoidance.

Frame convention: input points are in a **world/ground frame** where ``x`` and
``y`` span the ground plane and ``z`` is height (up). The caller is responsible
for the camera->world transform (robot-specific extrinsics); this module owns the
binning and the terrain analysis, not the robot's pose.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

__all__ = ["elevation_map", "fill_gaps", "traversability", "foothold_score"]


def elevation_map(points, cell: float = 0.05, agg: str = "max",
                  bounds=None):
    """Bin a point cloud into a 2.5-D elevation grid.

    Parameters
    ----------
    points : (N, 3) array of (x, y, z), z = height.
    cell   : grid resolution in world units.
    agg    : 'max' (canopy / obstacle-safe, default), 'min' (ground), or 'mean'.
    bounds : optional (xmin, xmax, ymin, ymax); defaults to the data extent.

    Returns ``(grid, extent)`` where ``grid[i, j]`` is the aggregated height of
    cell (row i = y, col j = x) and empty cells are ``nan``. ``extent`` is
    ``(xmin, xmax, ymin, ymax)``.
    """
    P = np.asarray(points, np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError("points must be (N, 3)")
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    if bounds is None:
        xmin, xmax, ymin, ymax = x.min(), x.max(), y.min(), y.max()
    else:
        xmin, xmax, ymin, ymax = bounds
    nx = max(1, int(np.ceil((xmax - xmin) / cell)))
    ny = max(1, int(np.ceil((ymax - ymin) / cell)))
    jx = np.clip(((x - xmin) / cell).astype(int), 0, nx - 1)
    iy = np.clip(((y - ymin) / cell).astype(int), 0, ny - 1)
    grid = np.full((ny, nx), np.nan)
    flat = iy * nx + jx
    order = np.argsort(flat)
    fs, zs = flat[order], z[order]
    bounds_idx = np.searchsorted(fs, np.arange(nx * ny + 1))
    for c in range(nx * ny):
        lo, hi = bounds_idx[c], bounds_idx[c + 1]
        if hi > lo:
            seg = zs[lo:hi]
            grid.flat[c] = seg.max() if agg == "max" else (
                seg.min() if agg == "min" else seg.mean())
    return grid, (xmin, xmax, ymin, ymax)


def fill_gaps(grid):
    """Fill ``nan`` cells with the nearest finite height (nearest-neighbour)."""
    g = np.asarray(grid, np.float64)
    nan = ~np.isfinite(g)
    if not nan.any():
        return g.copy()
    idx = ndimage.distance_transform_edt(nan, return_distances=False,
                                         return_indices=True)
    return g[tuple(idx)]


def traversability(grid, cell: float = 0.05, max_step: float = 0.1,
                   max_slope: float = 0.6, window: int = 3):
    """Boolean mask (True = traversable) from step and slope limits.

    step  = local (max - min) height over a ``window`` neighbourhood -> a curb /
            ledge / obstacle edge.
    slope = |gradient| of the height per unit distance.
    A cell is non-traversable where either exceeds its limit. ``nan`` cells
    (unobserved) are filled first and marked non-traversable.
    """
    g = np.asarray(grid, np.float64)
    unknown = ~np.isfinite(g)
    filled = fill_gaps(g)
    lo = ndimage.minimum_filter(filled, window, mode="nearest")
    hi = ndimage.maximum_filter(filled, window, mode="nearest")
    step = hi - lo
    gy, gx = np.gradient(filled, cell)
    slope = np.hypot(gx, gy)
    ok = (step <= max_step) & (slope <= max_slope) & (~unknown)
    return ok


def foothold_score(grid, cell: float = 0.05, window: int = 3):
    """Per-cell flatness score in [0, 1] (1 = flat & level = good foothold).

    Combines local roughness (height std) and slope into a single score; useful
    to rank candidate step locations for a legged robot."""
    filled = fill_gaps(np.asarray(grid, np.float64))
    m = ndimage.uniform_filter(filled, window, mode="nearest")
    m2 = ndimage.uniform_filter(filled * filled, window, mode="nearest")
    rough = np.sqrt(np.maximum(m2 - m * m, 0.0))
    gy, gx = np.gradient(filled, cell)
    slope = np.hypot(gx, gy)
    score = np.exp(-(rough / max(cell, 1e-6))) * np.exp(-slope)
    return np.clip(score, 0.0, 1.0)
