"""Ground-truth tests for locomotion perception: terrain heightmap analysis
(terrain.py additions) and balance/gait (locomotion.py).

Terrain and gait are built from known geometry (flat/ramp/step heightmaps, feet at
known positions), so the derived slopes, normals, footholds and stability margins
are checked against the exact answer."""
import numpy as np

import terrain
import locomotion


# --- terrain heightmap analysis --------------------------------------------- #
def test_fuse_elevation_fills_and_aggregates():
    nan = np.nan
    a = np.array([[1.0, nan], [nan, 4.0]])
    b = np.array([[nan, 2.0], [3.0, nan]])
    c = np.array([[nan, nan], [nan, nan]])
    fused_max = terrain.fuse_elevation([a, b, c], agg="max")
    assert np.allclose(fused_max, [[1.0, 2.0], [3.0, 4.0]])
    # a cell unobserved in every grid stays nan
    allnan = terrain.fuse_elevation([c, c], agg="mean")
    assert np.isnan(allnan).all()


def test_slope_map_ramp_30deg():
    cell = 0.05
    cols = np.arange(20) * cell * np.tan(np.radians(30.0))
    grid = np.tile(cols, (12, 1))                       # height rises along +x
    sm = terrain.slope_map(grid, cell=cell)
    assert np.allclose(sm[2:-2, 2:-2], 30.0, atol=1e-4)
    flat = terrain.slope_map(np.zeros((8, 8)), cell=cell)
    assert np.allclose(flat, 0.0)


def test_roughness_map_flat_vs_bumpy():
    flat = terrain.roughness_map(np.ones((20, 20)), window=3)
    assert np.allclose(flat, 0.0, atol=1e-9)
    rng = np.random.default_rng(0)
    bumpy = terrain.roughness_map(rng.normal(0, 1.0, (20, 20)), window=3)
    assert np.median(bumpy) > 0.3


def test_surface_normals_flat_and_ramp():
    flat = terrain.surface_normals(np.zeros((10, 12)), cell=1.0)
    assert np.allclose(flat[2:-2, 2:-2], [0.0, 0.0, 1.0], atol=1e-9)
    j = np.arange(12)
    grid = np.tile(0.5 * j, (10, 1))                    # z = 0.5 x, cell = 1
    n = terrain.surface_normals(grid, cell=1.0)
    expect = np.array([-0.5, 0.0, 1.0]); expect /= np.linalg.norm(expect)
    assert np.allclose(n[2:-2, 2:-2], expect, atol=1e-9)


def test_step_edges_detects_curb():
    grid = np.zeros((20, 20))
    grid[:, 10:] = 0.3                                  # a 0.3 m step at column 10
    edge, signed = terrain.step_edges(grid, cell=0.05, min_rise=0.1, window=3)
    assert edge[:, 9:11].any()                          # edge marked at the boundary
    assert not edge[:, :6].any() and not edge[:, 14:].any()   # flat interiors clean
    assert np.abs(signed[edge]).max() > 0.0
    # signed_rise reports the FULL step height (~0.3), not a ~0.15 under-report
    assert 0.25 < np.abs(signed[edge]).max() < 0.35


def test_step_edges_diagonal_step_not_zeroed():
    # a step along the diagonal (grad has gx=-gy) — the old sign(gx+gy) zeroed it.
    grid = np.zeros((30, 30))
    ii, jj = np.mgrid[0:30, 0:30]
    grid[(ii + jj) > 30] = 0.4                          # raised half-plane on a diagonal
    edge, signed = terrain.step_edges(grid, cell=0.05, min_rise=0.1, window=3)
    assert edge.any()
    assert np.abs(signed[edge]).max() > 0.1             # signed rise is non-zero at the edge


def test_foothold_candidates_skip_unobserved():
    grid = np.full((40, 40), np.nan)                    # entirely unobserved...
    grid[10:30, 10:30] = 0.0                            # ...except an observed flat patch
    cands = terrain.foothold_candidates(grid, cell=0.05, min_score=0.5, min_dist=0.1)
    assert len(cands) >= 1
    for c in cands:                                     # never a candidate in a NaN cell
        r, cc = c["cell"]
        assert np.isfinite(grid[r, cc])


def test_step_edges_size1_grid_no_crash():
    grid = np.array([[0.0, 0.0, 0.3, 0.3]])             # a 1xN heightmap
    edge, signed = terrain.step_edges(grid, cell=0.05, min_rise=0.1)
    assert edge.shape == grid.shape                     # np.gradient would have raised


def test_foothold_candidates_land_on_flat_plateau():
    rng = np.random.default_rng(1)
    grid = rng.normal(0, 0.2, (60, 60))                 # rough everywhere
    grid[24:36, 24:36] = 1.0                            # a flat, level plateau
    cands = terrain.foothold_candidates(grid, cell=0.05, window=3,
                                        min_score=0.5, min_dist=0.1)
    assert len(cands) >= 1
    for c in cands:
        r, cc = c["cell"]
        assert 20 <= r <= 40 and 20 <= cc <= 40         # only the plateau is flat enough
        assert c["score"] >= 0.5


# --- balance / gait --------------------------------------------------------- #
def test_contact_points_on_ground_plane():
    ground = np.column_stack([np.linspace(-1, 1, 50), np.zeros(50), np.zeros(50)])
    up = ground + np.array([0, 0, 0.5])
    P = np.vstack([ground, up])
    plane = np.array([0.0, 0.0, 1.0, 0.0])              # z = 0
    contacts, mask = locomotion.contact_points(P, plane, tol=0.02)
    assert mask[:50].all() and not mask[50:].any()
    assert contacts.shape[0] == 50


def test_com_from_silhouette_centroid():
    m = np.zeros((40, 50), bool)
    m[10:20, 20:40] = True                              # block centre = (14.5, 29.5)
    r, c = locomotion.com_from_silhouette(m)
    assert abs(r - 14.5) < 1e-9 and abs(c - 29.5) < 1e-9


def test_support_polygon_square_area():
    feet = np.array([[0, 0], [2, 0], [2, 2], [0, 2]], float)
    poly = locomotion.support_polygon(feet)
    assert abs(poly["area"] - 4.0) < 1e-9
    assert poly["vertices"].shape[0] == 4
    assert abs(poly["perimeter"] - 8.0) < 1e-9


def test_com_support_margin_inside_and_outside():
    feet = np.array([[0, 0, 0], [2, 0, 0], [2, 2, 0], [0, 2, 0]], float)
    inside = locomotion.com_support_margin([1.0, 1.0], feet)      # dead centre
    assert abs(inside - 1.0) < 1e-9                     # 1 m from every edge
    edge = locomotion.com_support_margin([0.2, 1.0], feet)
    assert abs(edge - 0.2) < 1e-9
    outside = locomotion.com_support_margin([-0.5, 1.0], feet)
    assert outside < 0.0                                # COM outside -> tipping


def test_com_support_margin_degenerate():
    # two feet only -> no polygon area -> not statically stable
    feet = np.array([[0, 0, 0], [1, 0, 0]], float)
    assert locomotion.com_support_margin([0.5, 0.0], feet) == float("-inf")


def test_gait_phase_antiphase_and_planted():
    t = np.linspace(0, 4 * np.pi, 200)
    # two feet in anti-phase: heights lift out of stance alternately
    left = np.clip(np.sin(t), 0, None)
    right = np.clip(np.sin(t + np.pi), 0, None)
    planted = np.zeros_like(t)                          # a foot that never lifts
    H = np.stack([left, right, planted], 1)
    g = locomotion.gait_phase(H, stance_frac=0.25)
    assert g["stance"].shape == (200, 3)
    assert g["duty_factor"][2] == 1.0                   # never-moving foot always planted
    assert 0.1 < g["duty_factor"][0] < 0.6              # a swinging foot ~half stance
    # left and right rarely in stance together (anti-phase)
    both = g["stance"][:, 0] & g["stance"][:, 1]
    assert both.mean() < 0.2
