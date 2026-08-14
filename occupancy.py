"""2-D occupancy / free-space mapping for navigation (numpy + scipy).

The planning-grid layer above :mod:`terrain`: collapse a 3-D cloud (from
:mod:`camera`/:mod:`stereo`) into a top-down occupancy grid, grow obstacles by the
robot's radius (configuration space), turn that into a clearance / distance-to-
obstacle cost field, test line-of-sight between cells, and find exploration
frontiers. These are the classic 2-D navigation primitives a path planner consumes
— the "where can I walk / drive and how do I get there" companion to terrain's
"is this cell steppable".

Frame convention: a **world/ground frame** where x, y span the ground and z is up
(same as :mod:`terrain`). Grids are indexed ``[row=y, col=x]`` with a returned
``extent = (xmin, xmax, ymin, ymax)``.

References (public literature — reimplemented, not derived from any product):
- Elfes, "Using occupancy grids for mobile robot perception and navigation",
  Computer 1989 (occupancy grids).
- Lozano-Pérez & Wesley, "An algorithm for planning collision-free paths...",
  CACM 1979 (configuration-space obstacle growing).
- Yamauchi, "A frontier-based approach for autonomous exploration", CIRA 1997.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

__all__ = ["occupancy_grid_2d", "inflate_obstacles", "clearance_map",
           "line_of_sight", "frontier_cells"]


def occupancy_grid_2d(points, cell: float = 0.05, z_range=None, bounds=None,
                      min_points: int = 1):
    """Collapse a 3-D cloud into a top-down 2-D occupancy grid.

    Points are binned by their (x, y); a cell is occupied when at least
    *min_points* fall in it. ``z_range=(zmin, zmax)`` keeps only points in a height
    slab first (e.g. the robot's body height, so the floor and high canopy don't
    count as obstacles). ``bounds=(xmin, xmax, ymin, ymax)`` fixes the extent
    (defaults to the data range). Returns ``(occ boolean grid, extent)``."""
    P = np.asarray(points, np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError("points must be (N, 3)")
    if z_range is not None:
        zlo, zhi = z_range
        P = P[(P[:, 2] >= zlo) & (P[:, 2] <= zhi)]
    x, y = P[:, 0], P[:, 1]
    if bounds is None:
        if P.shape[0] == 0:
            raise ValueError("empty cloud and no bounds given")
        xmin, xmax, ymin, ymax = x.min(), x.max(), y.min(), y.max()
    else:
        xmin, xmax, ymin, ymax = bounds
    nx = max(1, int(np.ceil((xmax - xmin) / cell)))
    ny = max(1, int(np.ceil((ymax - ymin) / cell)))
    counts = np.zeros((ny, nx), np.int64)
    if P.shape[0]:
        # DROP out-of-bounds points; clamping them onto the edge cells would pile up
        # phantom obstacles along the grid border.
        inb = (x >= xmin) & (x <= xmax) & (y >= ymin) & (y <= ymax)
        jx = np.clip(((x[inb] - xmin) / cell).astype(int), 0, nx - 1)
        iy = np.clip(((y[inb] - ymin) / cell).astype(int), 0, ny - 1)
        np.add.at(counts, (iy, jx), 1)
    return counts >= int(min_points), (xmin, xmax, ymin, ymax)


def inflate_obstacles(occ, radius_cells: float):
    """Grow occupied cells by *radius_cells* (configuration-space obstacles).

    A point robot planning on the inflated grid keeps a real robot of that radius
    clear of obstacles (Lozano-Pérez 1979). Uses a Euclidean disk, so corners are
    rounded correctly (not a square dilation). Returns a boolean grid."""
    occ = np.asarray(occ, bool)
    r = float(radius_cells)
    if r <= 0:
        return occ.copy()
    # distance from every free cell to the nearest obstacle; inflate where <= r
    dist = ndimage.distance_transform_edt(~occ)
    return dist <= r


def clearance_map(occ, cell: float = 0.05):
    """Distance from each cell to the nearest obstacle, in world units.

    The Euclidean distance transform of the free space — a smooth cost field a
    planner uses to prefer routes with margin (larger = safer). Occupied cells are
    0. Returns a float grid in the same units as *cell*."""
    occ = np.asarray(occ, bool)
    return ndimage.distance_transform_edt(~occ) * float(cell)


def line_of_sight(occ, start, end) -> bool:
    """True if the straight segment between two cells crosses no obstacle.

    Supercover Bresenham traversal of the occupancy grid between ``start`` and
    ``end`` (each ``(row, col)``) — the collision test a planner runs to add an edge
    or shortcut a path. Endpoints outside the grid, or either endpoint occupied,
    return False."""
    occ = np.asarray(occ, bool)
    H, W = occ.shape
    r0, c0 = int(start[0]), int(start[1])
    r1, c1 = int(end[0]), int(end[1])
    if not (0 <= r0 < H and 0 <= c0 < W and 0 <= r1 < H and 0 <= c1 < W):
        return False
    if occ[r0, c0] or occ[r1, c1]:
        return False
    dr = abs(r1 - r0)
    dc = abs(c1 - c0)
    sr = 1 if r1 > r0 else -1
    sc = 1 if c1 > c0 else -1
    r, c = r0, c0
    err = dr - dc
    while True:
        if occ[r, c]:
            return False
        if r == r1 and c == c1:
            return True
        e2 = 2 * err
        if e2 > -dc:
            err -= dc
            r += sr
        if e2 < dr:
            err += dr
            c += sc


def frontier_cells(free, unknown, min_cluster: int = 1):
    """Frontier cells for exploration: free cells adjacent to unknown space.

    A frontier is the boundary between what the robot has mapped as free and what it
    has not seen (Yamauchi 1997) — the places worth driving toward to grow the map.
    ``free`` and ``unknown`` are boolean grids (a cell is typically free, occupied or
    unknown). Returns ``(frontier_mask, clusters)`` where *clusters* is a list of
    (row, col) arrays (connected frontier segments >= *min_cluster*, largest first),
    each a candidate exploration target."""
    free = np.asarray(free, bool)
    unknown = np.asarray(unknown, bool)
    if free.shape != unknown.shape:
        raise ValueError("free and unknown grids must have the same shape")
    # a free cell touching unknown in its 4-neighbourhood is a frontier
    near_unknown = ndimage.binary_dilation(unknown, iterations=1) & free
    lbl, n = ndimage.label(near_unknown)
    clusters = []
    for i in range(1, n + 1):
        ys, xs = np.where(lbl == i)
        if ys.size >= int(min_cluster):
            clusters.append(np.stack([ys, xs], 1))
    clusters.sort(key=lambda a: -a.shape[0])
    return near_unknown, clusters
