"""Ground-truth tests for the terrain / traversability blocks: a synthetic scene
(flat ground + a raised box) with a known height and known obstacle edges."""
import numpy as np

import terrain


def _scene(seed=0):
    """Flat ground z=0 over [0,1]^2, plus a raised box of height 0.3 in a patch."""
    rng = np.random.default_rng(seed)
    x = rng.random(20000)
    y = rng.random(20000)
    z = np.zeros_like(x)
    box = (x > 0.4) & (x < 0.6) & (y > 0.4) & (y < 0.6)
    z[box] = 0.3
    return np.stack([x, y, z], axis=1), box


def test_elevation_map_recovers_box_and_ground():
    pts, _ = _scene()
    grid, extent = terrain.elevation_map(pts, cell=0.05, agg="max",
                                         bounds=(0, 1, 0, 1))
    assert grid.shape == (20, 20)
    # centre of the box region -> ~0.3; a ground corner -> ~0.0
    assert np.isclose(grid[10, 10], 0.3, atol=1e-6)     # (x~0.5, y~0.5) box
    assert np.isclose(grid[1, 1], 0.0, atol=1e-6)       # ground


def test_traversability_flags_box_edges_not_flat_ground():
    pts, _ = _scene()
    grid, _ = terrain.elevation_map(pts, cell=0.05, agg="max", bounds=(0, 1, 0, 1))
    ok = terrain.traversability(grid, cell=0.05, max_step=0.1, max_slope=1.0)
    # flat ground far from the box is traversable
    assert ok[1, 1] and ok[1, 18]
    # the box boundary has a 0.3 step -> not traversable somewhere on its ring
    ring = ok[7:14, 7:14]
    assert not ring.all(), "expected the box edge to be flagged non-traversable"


def test_fill_gaps_removes_nans():
    grid = np.full((6, 6), np.nan)
    grid[0, 0] = 1.0
    grid[5, 5] = 2.0
    filled = terrain.fill_gaps(grid)
    assert np.all(np.isfinite(filled))
    assert filled[0, 0] == 1.0 and filled[5, 5] == 2.0


def test_foothold_score_prefers_flat():
    pts, _ = _scene()
    grid, _ = terrain.elevation_map(pts, cell=0.05, agg="max", bounds=(0, 1, 0, 1))
    s = terrain.foothold_score(grid, cell=0.05)
    assert s.shape == grid.shape
    assert (s >= 0).all() and (s <= 1).all()
    # a flat ground cell scores higher than a box-edge cell
    assert s[1, 1] > s[7, 10]


def test_detect_obstacles_finds_the_box():
    pts, _ = _scene()
    grid, extent = terrain.elevation_map(pts, cell=0.05, agg="max", bounds=(0, 1, 0, 1))
    mask, obstacles = terrain.detect_obstacles(
        grid, cell=0.05, clearance=0.12, ground_radius=0.3, extent=extent)
    assert len(obstacles) == 1, f"expected one obstacle, got {len(obstacles)}"
    o = obstacles[0]
    assert abs(o["height"] - 0.3) < 0.05                 # ~0.3 m rise
    cx, cy = o["centroid_xy"]
    assert abs(cx - 0.5) < 0.08 and abs(cy - 0.5) < 0.08  # centred on the box
    assert mask[10, 10] and not mask[1, 1]               # box cell set, ground clear


def _ramp(seed=1, slope=0.5):
    """A tilted ground plane z = slope * x, no obstacle."""
    rng = np.random.default_rng(seed)
    x = rng.random(20000)
    y = rng.random(20000)
    return np.stack([x, y, slope * x], axis=1)


def test_detect_obstacles_ignores_a_ramp():
    # the ramp rises to 0.5 (>> clearance) yet is walkable ground, not an obstacle:
    # a naive height threshold would flag half the map; the ground-relative test must not.
    grid, extent = terrain.elevation_map(_ramp(), cell=0.05, agg="max", bounds=(0, 1, 0, 1))
    mask, obstacles = terrain.detect_obstacles(
        grid, cell=0.05, clearance=0.12, ground_radius=0.3, min_area=0.01, extent=extent)
    big = [o for o in obstacles if o["area"] > 0.02]
    assert not big, f"ramp wrongly flagged as obstacle(s): {big}"
