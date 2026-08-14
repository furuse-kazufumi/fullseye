"""Ground-truth tests for 2-D occupancy / free-space mapping (occupancy.py).

Grids are built from known geometry (a cloud cluster at a known place, a single
obstacle cell, a wall between two points), so occupancy, inflation, clearance,
line-of-sight and frontiers are checked against exact expected values."""
import numpy as np

import occupancy


def test_occupancy_grid_marks_cluster():
    rng = np.random.default_rng(0)
    obj = rng.uniform([1.0, 1.0, 0.2], [1.2, 1.2, 0.4], (200, 3))   # a blob at (1.1,1.1)
    occ, extent = occupancy.occupancy_grid_2d(obj, cell=0.05,
                                              bounds=(0, 2, 0, 2), z_range=(0.1, 0.5))
    assert occ.shape == (40, 40)
    # the occupied cells sit around (x,y)=(1.1,1.1) -> col/row ~ 22
    ys, xs = np.where(occ)
    assert 18 <= xs.mean() <= 26 and 18 <= ys.mean() <= 26
    assert occ.sum() < 40                       # a compact blob, not the whole grid


def test_occupancy_z_slab_filters_floor():
    # floor points at z~0 and body points at z~0.3; a body-height slab keeps only body
    floor = np.column_stack([np.linspace(0, 2, 300), np.full(300, 1.0), np.zeros(300)])
    body = np.column_stack([np.full(50, 0.5), np.full(50, 0.5),
                            np.linspace(0.2, 0.4, 50)])
    P = np.vstack([floor, body])
    occ, _ = occupancy.occupancy_grid_2d(P, cell=0.1, bounds=(0, 2, 0, 2),
                                         z_range=(0.15, 0.5))
    assert occ.sum() <= 2                        # only the single body column, not the floor line


def test_inflate_obstacles_disk():
    occ = np.zeros((21, 21), bool)
    occ[10, 10] = True
    inf = occupancy.inflate_obstacles(occ, radius_cells=3.0)
    assert inf[10, 10] and inf[10, 13] and inf[7, 10]      # within radius 3
    assert not inf[10, 14] and not inf[6, 10]              # beyond radius 3
    assert inf.sum() < np.pi * 4 ** 2                       # roughly a disk of r=3


def test_clearance_map_distance():
    occ = np.zeros((10, 10), bool)
    occ[:, 0] = True                                        # a wall down column 0
    clr = occupancy.clearance_map(occ, cell=0.1)
    assert np.isclose(clr[5, 0], 0.0)                       # on the wall
    assert np.isclose(clr[5, 3], 0.3)                       # 3 cells * 0.1 m
    assert np.isclose(clr[5, 9], 0.9)


def test_line_of_sight_clear_and_blocked():
    occ = np.zeros((20, 20), bool)
    assert occupancy.line_of_sight(occ, (2, 2), (2, 17))    # empty grid -> clear
    occ[:, 10] = True                                       # a wall at column 10
    occ[2, 2] = False; occ[2, 17] = False                   # keep endpoints free
    assert not occupancy.line_of_sight(occ, (2, 2), (2, 17))   # blocked by the wall
    assert occupancy.line_of_sight(occ, (2, 2), (2, 8))     # stops before the wall
    assert not occupancy.line_of_sight(occ, (2, 2), (2, 25))  # off-grid endpoint


def test_occupancy_drops_out_of_bounds_points():
    # points outside the given bounds must be dropped, not clamped onto edge cells
    pts = np.array([[0.5, 0.5, 0.3], [5.0, 5.0, 0.3], [-3.0, 0.5, 0.3]])   # 2 outside
    occ, _ = occupancy.occupancy_grid_2d(pts, cell=0.1, bounds=(0, 1, 0, 1))
    assert occ.sum() == 1                              # only the in-bounds point
    assert not occ[:, -1].any() and not occ[:, 0].any() and not occ[-1, :].any()


def test_clearance_and_inflate_no_obstacles():
    free = np.zeros((8, 8), bool)
    clr = occupancy.clearance_map(free, cell=0.1)
    assert np.isinf(clr).all()                         # nothing to avoid -> infinite clearance
    inf = occupancy.inflate_obstacles(free, radius_cells=3.0)
    assert not inf.any()                               # no phantom C-space obstacles


def test_line_of_sight_no_corner_cutting():
    # two obstacles touching only at a diagonal must block the diagonal line between
    # the cells they flank (standard Bresenham would tunnel through).
    occ = np.zeros((7, 7), bool)
    occ[3, 4] = True
    occ[4, 3] = True
    assert not occupancy.line_of_sight(occ, (3, 3), (4, 4))   # corner is sealed
    # but a genuinely open diagonal is still visible
    assert occupancy.line_of_sight(np.zeros((7, 7), bool), (1, 1), (5, 5))


def test_frontier_between_free_and_unknown():
    free = np.zeros((10, 10), bool)
    unknown = np.zeros((10, 10), bool)
    free[:, :5] = True                                      # left half mapped free
    unknown[:, 5:] = True                                   # right half unseen
    fr, clusters = occupancy.frontier_cells(free, unknown)
    assert fr[:, 4].all()                                   # the free column touching unknown
    assert not fr[:, :4].any()                              # interior free is not a frontier
    assert len(clusters) == 1 and clusters[0].shape[0] == 10
