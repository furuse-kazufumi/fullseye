"""Ground-truth + contract tests for backends_alife.py (registry cluster alife_).

Does NOT import ops.py. It drives ``build()`` through a tiny ``_Op`` stub and
calls each module-level operator directly, asserting that it really implements
the artificial-life / dynamical model its name promises:

  * Conway's Life reproduces the textbook glider (translation by (1,1) after 4
    generations), the blinker (period 2) and the block (still life);
  * the cyclic CA really propagates the "eat-the-next-state" front;
  * Gray-Scott spreads the autocatalyst beyond its seed support;
  * Perona-Malik denoises a flat region while keeping a step edge that a
    Gaussian of comparable smoothing power destroys;
  * mean-curvature flow shrinks a disk but leaves a straight edge exactly fixed
    (zero curvature);
  * DLA growth is monotone in the generation knob, superset-of-seed, and
    selective under high stickiness;
  * the Greenberg-Hastings medium propagates a wave at threshold 1 and cannot
    re-excite refractory cells.

The honest caveat of this cluster is asserted too: a homogeneous input has no
symmetry to break, so several evolvers correctly return a flat field.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

import backends_alife as A
from conftest import KNOBS, image_bank


# --------------------------------------------------------------------------- #
# stub registry (mirrors ops.Op's positional construction)                    #
# --------------------------------------------------------------------------- #
class _Op:
    def __init__(self, *a):
        self.name = a[0]
        self.category = a[1]
        self.halcon = a[2]
        self.in_sort = a[3]
        self.out_sort = a[4]
        self.fn = a[5]


def _norm(x):
    m = float(np.max(np.abs(x)))
    return x / m if m > 1e-8 else x


def _binm(v):
    return (np.asarray(v) > 0.5).astype(np.float64)


OPS = A.build(_Op, "image", "region", "feature", "contour", _norm, _binm)

EXPECTED = [
    "alife_gray_scott",
    "alife_turing",
    "alife_life_step",
    "alife_cyclic_ca",
    "alife_perona_malik",
    "alife_curvature_flow",
    "alife_dla",
    "alife_reaction_bz",
]


# --------------------------------------------------------------------------- #
# structural / provenance                                                     #
# --------------------------------------------------------------------------- #
def test_registry_shape_names_and_sorts():
    names = [o.name for o in OPS]
    assert names == EXPECTED
    assert len(set(names)) == len(names)
    for op in OPS:
        assert op.name.startswith("alife_")
        assert op.in_sort == "image" and op.out_sort == "image"
        assert op.category == "artificial-life"


def test_every_op_makes_no_halcon_claim():
    # HALCON has no reaction-diffusion / cellular-automaton / excitable-medium
    # operator, and the two PDE members that share a family with HALCON ops are
    # already covered elsewhere -- so nothing here may claim coverage.
    assert all(op.halcon == "" for op in OPS)


def test_contract_finite_deterministic_shape_and_range():
    for op in OPS:
        for iname, iv in image_bank().items():
            for a, b in KNOBS:
                out = op.fn(np.array(iv, copy=True), a, b)
                assert isinstance(out, np.ndarray) and out.ndim == 2, (op.name, iname)
                assert out.shape == iv.shape, (op.name, iname)
                assert np.isfinite(out).all(), (op.name, iname, a, b)
                assert out.min() >= -1e-9 and out.max() <= 1 + 1e-9, (op.name, iname)
                again = op.fn(np.array(iv, copy=True), a, b)
                assert np.array_equal(out, again), (op.name, iname, a, b)


def test_wrapper_is_fail_soft():
    # A garbage input must not raise: _safe -> sanitize returns a valid image.
    for op in OPS:
        out = op.fn("not an image", 0.5, 0.5)
        assert out is not None


# --------------------------------------------------------------------------- #
# 1. Gray-Scott reaction-diffusion                                            #
# --------------------------------------------------------------------------- #
def test_gray_scott_spreads_autocatalyst_beyond_its_seed():
    seed = np.zeros((32, 32))
    seed[14:18, 14:18] = 1.0
    out = A.alife_gray_scott(seed, 0.5, 0.5)
    # the V species diffuses out of the seeded 4x4 block
    assert (out > 0.05).sum() > (seed > 0.5).sum()
    assert out.std() > 0.01                      # a real pattern, not a flat field


def test_gray_scott_feed_kill_knobs_change_the_pattern():
    seed = np.zeros((32, 32))
    seed[14:18, 14:18] = 1.0
    lo = A.alife_gray_scott(seed, 0.1, 0.1)
    hi = A.alife_gray_scott(seed, 0.9, 0.9)
    assert np.abs(lo - hi).max() > 1e-3


def test_gray_scott_homogeneous_input_nucleates_nothing():
    # honest caveat: no spatial structure -> no symmetry breaking -> flat output
    flat = A.alife_gray_scott(np.full((24, 24), 0.42), 0.5, 0.5)
    assert flat.std() < 1e-9
    assert A.alife_gray_scott(np.zeros((24, 24)), 0.5, 0.5).max() == 0.0


# --------------------------------------------------------------------------- #
# 2. Gierer-Meinhardt activator-inhibitor                                     #
# --------------------------------------------------------------------------- #
def test_turing_evolves_with_step_count_and_stays_bounded():
    img = image_bank()["normal"]
    few = A.alife_turing(img, 0.5, 0.0)
    many = A.alife_turing(img, 0.5, 1.0)
    assert np.abs(few - many).max() > 1e-3      # the system actually integrates
    assert np.isfinite(many).all() and many.min() >= 0.0 and many.max() <= 1.0


def test_turing_inhibitor_range_knob_matters():
    img = image_bank()["normal"]
    short = A.alife_turing(img, 0.0, 1.0)
    long_ = A.alife_turing(img, 1.0, 1.0)
    assert np.abs(short - long_).max() > 1e-5


def test_turing_homogeneous_state_is_a_fixed_point():
    out = A.alife_turing(np.full((24, 24), 0.42), 0.5, 1.0)
    assert out.std() < 1e-9                      # no lateral inhibition to break it


# --------------------------------------------------------------------------- #
# 3. Life-like cellular automaton (Conway ground truth)                        #
# --------------------------------------------------------------------------- #
def test_life_output_is_strictly_binary():
    img = image_bank()["normal"]
    out = A.alife_life_step(img, 0.0, 0.5)
    assert set(np.unique(out)).issubset({0.0, 1.0})


def test_life_glider_translates_by_one_cell_after_four_generations():
    g = np.zeros((16, 16))
    g[1, 2] = g[2, 3] = g[3, 1] = g[3, 2] = g[3, 3] = 1.0
    out = A.alife_life_step(g, 0.0, 0.35)        # a=Conway B3/S23, b -> 4 gens
    assert np.array_equal(out, np.roll(np.roll(g, 1, axis=0), 1, axis=1))


def test_life_blinker_has_period_two_and_block_is_a_still_life():
    blinker = np.zeros((9, 9))
    blinker[4, 3:6] = 1.0
    vertical = np.zeros((9, 9))
    vertical[3:6, 4] = 1.0
    assert np.array_equal(A.alife_life_step(blinker, 0.0, 0.0), vertical)     # 1 gen
    assert np.array_equal(A.alife_life_step(blinker, 0.0, 0.15), blinker)     # 2 gens

    block = np.zeros((10, 10))
    block[3:5, 3:5] = 1.0
    assert np.array_equal(A.alife_life_step(block, 0.0, 1.0), block)          # 10 gens


def test_life_rule_presets_are_distinct():
    g = np.zeros((16, 16))
    g[1, 2] = g[2, 3] = g[3, 1] = g[3, 2] = g[3, 3] = 1.0
    conway = A.alife_life_step(g, 0.0, 0.0)
    seeds = A.alife_life_step(g, 0.9, 0.0)       # Seeds B2/S
    assert not np.array_equal(conway, seeds)


# --------------------------------------------------------------------------- #
# 4. Cyclic cellular automaton                                                #
# --------------------------------------------------------------------------- #
def test_cyclic_ca_front_advances_with_more_steps():
    x = np.zeros((20, 20))
    x[:, 10:] = 0.4                              # N=3 -> states 0 | 1 halfplanes
    counts = [(A.alife_cyclic_ca(x, 0.0, b) > 0.4).sum() for b in (0.0, 0.07, 0.21)]
    assert counts[0] < counts[1] < counts[2]     # the state-1 domain eats state 0


def test_cyclic_ca_constant_field_is_frozen():
    # no neighbour holds s+1, so nothing may advance (honest caveat)
    out = A.alife_cyclic_ca(np.full((10, 10), 0.42), 0.0, 1.0)
    assert out.std() == 0.0


def test_cyclic_ca_state_count_follows_knob_a():
    img = image_bank()["normal"]
    few = np.unique(A.alife_cyclic_ca(img, 0.0, 0.0))     # N=3
    many = np.unique(A.alife_cyclic_ca(img, 1.0, 0.0))    # N=12
    assert len(few) <= 3 and len(many) > len(few)


# --------------------------------------------------------------------------- #
# 5. Perona-Malik anisotropic diffusion                                       #
# --------------------------------------------------------------------------- #
def _noisy_step(n=40, sigma=0.08):
    step = np.zeros((n, n))
    step[:, n // 2:] = 1.0
    rng = np.random.default_rng(3)               # test-side fixture only
    return step, np.clip(step + sigma * rng.standard_normal((n, n)), 0, 1)


def _edge_jump(im):
    return float(im[:, 22].mean() - im[:, 17].mean())


def test_perona_malik_denoises_flat_region_but_keeps_the_edge():
    _step, noisy = _noisy_step()
    pm = A.alife_perona_malik(noisy, 0.15, 1.0)
    gauss = ndimage.gaussian_filter(noisy, 2.0, mode="nearest")
    # comparable (in fact stronger) noise suppression than the Gaussian ...
    assert pm[:, :15].std() < noisy[:, :15].std() * 0.3
    assert pm[:, :15].std() <= gauss[:, :15].std()
    # ... while the step edge survives, which the Gaussian's does not
    assert _edge_jump(pm) > 0.9
    assert _edge_jump(pm) > _edge_jump(gauss) + 0.1


def test_perona_malik_more_iterations_smooth_more():
    _step, noisy = _noisy_step()
    stds = [A.alife_perona_malik(noisy, 0.15, b)[:, :15].std() for b in (0.0, 0.3, 0.6, 1.0)]
    assert stds[0] > stds[1] > stds[2] > stds[3]


def test_perona_malik_larger_kappa_weakens_edge_preservation():
    _step, noisy = _noisy_step()
    jumps = [_edge_jump(A.alife_perona_malik(noisy, a, 1.0)) for a in (0.0, 0.5, 1.0)]
    assert jumps[0] > jumps[1] > jumps[2]        # conductance stops stopping


# --------------------------------------------------------------------------- #
# 6. Mean-curvature flow                                                      #
# --------------------------------------------------------------------------- #
def _disk(n=48, r=10.0):
    yy, xx = np.mgrid[0:n, 0:n]
    return (((yy - n // 2) ** 2 + (xx - n // 2) ** 2) < r * r).astype(np.float64)


def test_curvature_flow_shrinks_a_disk_monotonically_in_steps():
    d = _disk()
    areas = [(A.alife_curvature_flow(d, a, 1.0) > 0.5).sum() for a in (0.0, 0.3, 0.6, 1.0)]
    assert areas[0] > (d > 0.5).sum() - 1        # 1 step barely moves it
    assert areas[0] > areas[1] > areas[2] > areas[3]
    assert areas[-1] < (d > 0.5).sum()           # the level curve really shortened


def test_curvature_flow_leaves_a_straight_edge_exactly_fixed():
    half = np.zeros((48, 48))
    half[:, 24:] = 1.0                           # zero-curvature level curves
    out = A.alife_curvature_flow(half, 1.0, 1.0)
    assert np.abs(out - half).max() < 1e-12


def test_curvature_flow_constant_image_is_invariant():
    c = np.full((24, 24), 0.42)
    assert np.abs(A.alife_curvature_flow(c, 1.0, 1.0) - c).max() < 1e-12


# --------------------------------------------------------------------------- #
# 7. Diffusion-limited aggregation                                            #
# --------------------------------------------------------------------------- #
def test_dla_output_is_binary_and_contains_the_seed():
    img = image_bank()["single_bright"]
    out = A.alife_dla(img, 0.5, 0.5)
    assert set(np.unique(out)).issubset({0.0, 1.0})
    assert out[img > 0.5].min() == 1.0           # the cluster never loses its seed


def test_dla_growth_is_monotone_in_the_generation_knob():
    img = image_bank()["single_bright"]
    sizes = [A.alife_dla(img, a, 0.5).sum() for a in (0.0, 0.3, 0.6, 1.0)]
    assert sizes[0] < sizes[1] < sizes[2] < sizes[3]


def test_dla_growth_stays_inside_the_reachable_neighbourhood():
    img = image_bank()["single_bright"]
    gens = 1 + int(0.3 * 11)
    out = A.alife_dla(img, 0.3, 0.0) > 0.5
    reach = ndimage.binary_dilation(img > 0.5, structure=np.ones((3, 3), bool),
                                    iterations=gens)
    assert (out & ~reach).sum() == 0             # one Moore ring per generation


def test_dla_high_stickiness_is_selective():
    img = image_bank()["single_bright"]
    compact = A.alife_dla(img, 1.0, 0.0).sum()   # attach the whole boundary
    dendritic = A.alife_dla(img, 1.0, 1.0).sum()  # only the strongest tips
    assert dendritic < compact


def test_dla_without_a_bright_seed_grows_nothing():
    assert A.alife_dla(np.zeros((24, 24)), 1.0, 0.5).sum() == 0.0


# --------------------------------------------------------------------------- #
# 8. Greenberg-Hastings excitable medium (BZ)                                 #
# --------------------------------------------------------------------------- #
def test_bz_states_are_quantised_to_rest_excited_refractory():
    img = image_bank()["normal"]
    out = A.alife_reaction_bz(img, 0.0, 0.2)
    assert set(np.unique(out)).issubset({0.0, 0.5, 1.0})


def test_bz_wave_expands_from_a_single_spark():
    spark = np.zeros((32, 32))
    spark[16, 16] = 1.0
    fronts = [(A.alife_reaction_bz(spark, 0.0, b) > 0.1).sum() for b in (0.0, 0.05, 0.1, 0.15)]
    assert fronts[0] < fronts[1] < fronts[2] < fronts[3]


def test_bz_higher_threshold_blocks_a_lone_spark():
    spark = np.zeros((32, 32))
    spark[16, 16] = 1.0
    # one excited neighbour cannot fire a cell that needs two or more
    assert (A.alife_reaction_bz(spark, 0.34, 0.15) > 0.1).sum() == 0
    assert (A.alife_reaction_bz(spark, 0.0, 0.15) > 0.1).sum() > 0


def test_bz_refractory_period_is_respected():
    exc = np.ones((8, 8))                        # everything starts excited
    after1 = A.alife_reaction_bz(exc, 0.0, 0.0)  # 1 step  -> all refractory
    after2 = A.alife_reaction_bz(exc, 0.0, 0.06)  # 2 steps -> all rest
    assert np.all(after1 == 1.0)
    assert np.all(after2 == 0.0)                 # no self re-excitation
