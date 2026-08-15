"""Ground-truth + contract tests for backends_alife2.py (registry cluster alife_).

Does NOT import ops.py. It drives ``build()`` through a tiny ``_Op`` stub and
calls each module-level operator directly, asserting that it really implements
the artificial-life model its name promises. Every correctness anchor here is
checked against an **independent reference computation** written in this file,
not against the module's own code path:

  * ``alife_wolfram1d`` -- rule 90 from a single central seed is recomputed two
    independent ways (a shift-XOR recurrence, and Pascal's triangle mod 2 via
    ``math.comb``) and must match the op *exactly*; rule 250 is recomputed as
    "left OR right" and must fill the lattice; rule 0 must annihilate and rule
    255 must saturate after one generation.
  * ``alife_langton_ant`` -- an independent turmite simulator (complex-number
    heading rotation instead of a direction table, visit counting instead of
    in-place flipping) must reproduce the op bit-for-bit, and the hand-computed
    first four steps must build the classic 2x2 block.
  * ``alife_lenia`` -- one Lenia step is recomputed with an independent circular
    correlation (explicit roll-sum instead of ``scipy.ndimage.convolve``) plus
    the published growth mapping; the output must stay *continuous* (that is
    what separates Lenia from a binary Life rule) and the empty world must be a
    fixed point.
  * ``alife_sandpile`` -- a single 4-grain cell must topple to its four
    orthogonal neighbours; the abelian property is checked by stabilising the
    same pile with an independent *sequential* (single-cell, LIFO) toppler.

The honest caveats of this cluster are asserted too: the 1-D CA only consumes
the image's top row, and a structureless input yields a structureless output.
"""
from __future__ import annotations

from math import comb

import numpy as np

import backends_alife2 as A
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
    "alife_wolfram1d",
    "alife_langton_ant",
    "alife_lenia",
    "alife_sandpile",
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
    # HALCON's operator list has no elementary-CA / turmite / Lenia / sandpile
    # operator at all, so nothing in this cluster may claim coverage.
    assert all(op.halcon == "" for op in OPS)


def test_contract_finite_deterministic_shape_and_range():
    for op in OPS:
        for iname, iv in image_bank().items():
            for a, b in KNOBS:
                out = op.fn(np.array(iv, copy=True), a, b)
                assert isinstance(out, np.ndarray) and out.ndim == 2, (op.name, iname)
                assert out.dtype == np.float64, (op.name, iname)
                assert out.shape == iv.shape, (op.name, iname)
                assert np.isfinite(out).all(), (op.name, iname, a, b)
                assert out.min() >= -1e-9 and out.max() <= 1 + 1e-9, (op.name, iname)
                again = op.fn(np.array(iv, copy=True), a, b)
                assert np.array_equal(out, again), (op.name, iname, a, b)


def test_ops_do_not_mutate_their_input():
    for op in OPS:
        for iv in image_bank().values():
            keep = np.array(iv, copy=True)
            op.fn(iv, 0.7, 0.4)
            assert np.array_equal(iv, keep), op.name


def test_knobs_outside_the_unit_interval_are_clamped():
    img = image_bank()["normal"]
    for op in OPS:
        lo = op.fn(np.array(img, copy=True), 0.0, 0.0)
        hi = op.fn(np.array(img, copy=True), 1.0, 1.0)
        assert np.array_equal(op.fn(np.array(img, copy=True), -5.0, -5.0), lo), op.name
        assert np.array_equal(op.fn(np.array(img, copy=True), 9.0, 9.0), hi), op.name
        assert np.array_equal(op.fn(np.array(img, copy=True), np.nan, 0.0), lo), op.name


def test_wrapper_is_fail_soft():
    # A garbage input must not raise: _safe -> sanitize returns a valid value.
    for op in OPS:
        assert op.fn("not an image", 0.5, 0.5) is not None
        assert op.fn(None, 0.5, 0.5) is not None
        ragged = np.array([[np.nan, np.inf], [-np.inf, 3.0]])
        out = op.fn(ragged, 0.5, 0.5)
        assert isinstance(out, np.ndarray) and np.isfinite(out).all(), op.name


def test_module_uses_no_random_number_generator():
    # Determinism is a hard contract for this cluster: assert it at the source
    # level too, not only by re-running the ops.
    import inspect

    src = inspect.getsource(A)
    for forbidden in ("np.random", "numpy.random", "random.", "import random",
                      "default_rng", "RandomState", "np.seed"):
        assert forbidden not in src, forbidden


# --------------------------------------------------------------------------- #
# 1. Wolfram elementary cellular automaton                                    #
# --------------------------------------------------------------------------- #
def _rule_knob(rule):
    """Knob ``a`` that selects ``rule`` from the curated elementary-rule table."""
    i = A._ELEMENTARY_RULES.index(rule)
    return (i + 0.5) / len(A._ELEMENTARY_RULES)


def _spacetime_from_recurrence(seed_row, n_rows, step):
    """Independent spacetime diagram from a 1-D row recurrence ``step(row)``."""
    row = np.asarray(seed_row, bool).copy()
    out = np.zeros((n_rows, row.size), np.float64)
    out[0] = row
    for t in range(1, n_rows):
        row = step(row)
        out[t] = row
    return out


def test_wolfram_rule_table_selection_is_reachable_and_exact():
    # every curated rule must be selectable through the knob (no dead entries)
    for rule in A._ELEMENTARY_RULES:
        a = _rule_knob(rule)
        idx = min(int(a * len(A._ELEMENTARY_RULES)), len(A._ELEMENTARY_RULES) - 1)
        assert A._ELEMENTARY_RULES[idx] == rule


def test_wolfram_rule90_single_seed_matches_shift_xor_reference():
    # Rule 90 is the additive rule next = left XOR right. Recompute the whole
    # 32x32 spacetime diagram from that recurrence and demand exact equality.
    n = 32
    out = A.alife_wolfram1d(np.zeros((n, n)), _rule_knob(90), 0.0)
    seed = np.zeros(n, bool)
    seed[n // 2] = True                      # the op's empty-row fallback
    ref = _spacetime_from_recurrence(
        seed, n, lambda r: np.roll(r, 1) ^ np.roll(r, -1))
    assert np.array_equal(out, ref)
    assert set(np.unique(out)).issubset({0.0, 1.0})


def test_wolfram_rule90_single_seed_is_pascals_triangle_mod_2():
    # Sierpinski gasket ground truth, computed from binomial coefficients --
    # a completely different route than any CA update. Only the rows that have
    # not yet wrapped around the circular lattice are compared.
    n = 40
    out = A.alife_wolfram1d(np.zeros((n, n)), _rule_knob(90), 0.0)
    c = n // 2
    n_rows = 19                              # 2*19 < 40, so no wrap-around yet
    for t in range(n_rows):
        for k in range(-t, t + 1):
            if (k + t) % 2 == 0:             # rule 90 lives on one parity class
                expect = float(comb(t, (k + t) // 2) % 2)
            else:
                expect = 0.0
            assert out[t, c + k] == expect, (t, k)
        # outside the light cone nothing may be alive
        assert out[t, :c - t].sum() == 0.0
        assert out[t, c + t + 1:].sum() == 0.0


def test_wolfram_rule250_is_left_or_right_and_fills_the_lattice():
    n = 32
    img = np.zeros((n, n))
    img[0, 4:8] = 1.0                        # a contiguous block of live cells
    out = A.alife_wolfram1d(img, _rule_knob(250), 0.0)
    ref = _spacetime_from_recurrence(
        img[0] > 0.5, n, lambda r: np.roll(r, 1) | np.roll(r, -1))
    assert np.array_equal(out, ref)          # rule 250 == (left OR right)
    # the live domain grows one cell per side per generation, so after ceil(W/2)
    # generations the whole circular lattice is on and stays on
    assert out[-1].min() == 1.0
    assert out[n // 2:].min() == 1.0
    # and it is monotone: a rule-250 lattice can never lose a live cell
    live = out.sum(axis=1)
    assert np.all(np.diff(live) >= 0)


def test_wolfram_rule0_annihilates_and_rule255_saturates():
    n = 24
    img = np.zeros((n, n))
    img[0, 3:9] = 1.0
    dead = A.alife_wolfram1d(img, _rule_knob(0), 0.0)
    assert dead[0].sum() == 6.0              # row 0 is the initial condition
    assert dead[1:].max() == 0.0             # rule 0: every neighbourhood -> 0
    full = A.alife_wolfram1d(img, _rule_knob(255), 0.0)
    assert full[1:].min() == 1.0             # rule 255: every neighbourhood -> 1


def test_wolfram_initial_row_is_the_thresholded_top_row_of_the_image():
    n = 16
    img = np.zeros((n, n))
    img[0] = np.linspace(0.0, 1.0, n)        # crosses 0.5 exactly once
    out = A.alife_wolfram1d(img, _rule_knob(30), 0.0)
    assert np.array_equal(out[0], (img[0] > 0.5).astype(np.float64))


def test_wolfram_density_knob_b_seeds_extra_cells():
    n = 32
    img = np.zeros((n, n))
    dens = [A.alife_wolfram1d(img, _rule_knob(0), b)[0].sum()
            for b in (0.0, 0.25, 0.5, 1.0)]
    assert dens[0] == 1.0                    # b=0: the lone central seed
    assert dens[0] < dens[1] < dens[2] < dens[3]
    assert dens[-1] == n // 2                # b=1: every other cell seeded
    # ... and the seeding really changes the evolved diagram
    lo = A.alife_wolfram1d(img, _rule_knob(30), 0.0)
    hi = A.alife_wolfram1d(img, _rule_knob(30), 1.0)
    assert not np.array_equal(lo, hi)


def test_wolfram_rules_are_distinguishable_and_output_is_deterministic():
    img = image_bank()["normal"]
    outs = [A.alife_wolfram1d(img, _rule_knob(r), 0.3)
            for r in (30, 90, 110, 184, 150)]
    for i in range(len(outs)):
        for j in range(i + 1, len(outs)):
            assert not np.array_equal(outs[i], outs[j]), (i, j)
    assert np.array_equal(A.alife_wolfram1d(img, 0.4, 0.6),
                          A.alife_wolfram1d(img, 0.4, 0.6))


# --------------------------------------------------------------------------- #
# 2. Langton's ant                                                            #
# --------------------------------------------------------------------------- #
def _ant_knob(n_steps):
    """Knob ``a`` that yields exactly ``n_steps`` ant steps (N = 1+int(400a))."""
    return (n_steps - 0.5) / 400.0


def _ant_reference(colors, n_steps, heading=0):
    """Independent Langton's-ant simulator.

    Deliberately written a different way than the op: the heading is a complex
    unit (dy + i*dx) rotated by multiplication (turn right = *(-i), turn left =
    *(+i)) instead of an index into a direction table, and the visit count of
    every cell is recorded so the colour field can be cross-checked by parity.

    Returns ``(final_colors, visit_counts)``.
    """
    g = np.asarray(colors, np.int64).copy()
    h, w = g.shape
    visits = np.zeros((h, w), np.int64)
    r, c = h // 2, w // 2
    d = (complex(-1, 0), complex(0, 1), complex(1, 0), complex(0, -1))[heading]
    for _ in range(n_steps):
        visits[r, c] += 1
        if g[r, c] == 0:
            d *= complex(0, -1)              # white -> turn right
            g[r, c] = 1
        else:
            d *= complex(0, 1)               # black -> turn left
            g[r, c] = 0
        r = (r + int(round(d.real))) % h
        c = (c + int(round(d.imag))) % w
    return g, visits


def test_langton_first_four_steps_build_the_classic_2x2_block():
    # Hand-derived ground truth: starting on white facing up, the ant turns
    # right four times, blackening (r,c) -> (r,c+1) -> (r+1,c+1) -> (r+1,c) and
    # returning to its start cell facing up again.
    n = 16
    out = A.alife_langton_ant(np.zeros((n, n)), _ant_knob(4), 0.0)
    r0, c0 = n // 2, n // 2
    expect = np.zeros((n, n))
    expect[r0:r0 + 2, c0:c0 + 2] = 1.0
    assert np.array_equal(out, expect)
    # step 5 stands on black, turns left and clears the start cell again
    out5 = A.alife_langton_ant(np.zeros((n, n)), _ant_knob(5), 0.0)
    expect5 = expect.copy()
    expect5[r0, c0] = 0.0
    assert np.array_equal(out5, expect5)


def test_langton_matches_an_independent_simulation_bit_for_bit():
    n = 32
    blank = np.zeros((n, n))
    for n_steps in (1, 7, 40, 111, 400):
        out = A.alife_langton_ant(blank, _ant_knob(n_steps), 0.0)
        ref, _visits = _ant_reference(np.zeros((n, n), np.int64), n_steps)
        assert np.array_equal(out, ref.astype(np.float64)), n_steps


def test_langton_matches_the_independent_simulation_on_a_seeded_lattice():
    # not just the empty world: start from a real (thresholded) image so the
    # ant meets black cells and has to turn left as well.
    img = image_bank()["normal"]
    for n_steps in (3, 60, 250):
        out = A.alife_langton_ant(img, _ant_knob(n_steps), 0.0)
        ref, _v = _ant_reference((img > 0.5).astype(np.int64), n_steps)
        assert np.array_equal(out, ref.astype(np.float64)), n_steps


def test_langton_flip_parity_agrees_with_the_visit_counts():
    n = 32
    n_steps = 400
    out = A.alife_langton_ant(np.zeros((n, n)), _ant_knob(n_steps), 0.0)
    _ref, visits = _ant_reference(np.zeros((n, n), np.int64), n_steps)
    # exactly N cell visits happened, one per step
    assert int(visits.sum()) == n_steps
    # each visit flips the cell it lands on, so from an all-white lattice a cell
    # is black exactly when it was visited an odd number of times
    assert np.array_equal(out, (visits % 2 == 1).astype(np.float64))
    # and no cell outside the visited set may have changed
    assert np.array_equal(out > 0.5, (visits > 0) & (visits % 2 == 1))


def test_langton_step_count_follows_knob_a():
    n = 32
    blank = np.zeros((n, n))
    for n_steps in (1, 2, 3, 4, 137, 400):
        assert np.array_equal(
            A.alife_langton_ant(blank, _ant_knob(n_steps), 0.0),
            _ant_reference(np.zeros((n, n), np.int64), n_steps)[0].astype(np.float64))
    # the ant cannot have touched more cells than it took steps
    assert A.alife_langton_ant(blank, _ant_knob(40), 0.0).sum() <= 40


def test_langton_heading_knob_b_rotates_the_trajectory():
    n = 32
    blank = np.zeros((n, n))
    outs = [A.alife_langton_ant(blank, _ant_knob(30), b) for b in (0.0, 0.3, 0.6, 1.0)]
    for i in range(len(outs)):
        for j in range(i + 1, len(outs)):
            assert not np.array_equal(outs[i], outs[j]), (i, j)
        # a rotation of the lattice leaves the number of blackened cells alone
        assert outs[i].sum() == outs[0].sum()
    for h in range(4):
        b = (h + 0.5) / 4.0
        ref, _v = _ant_reference(np.zeros((n, n), np.int64), 30, heading=h)
        assert np.array_equal(A.alife_langton_ant(blank, _ant_knob(30), b),
                              ref.astype(np.float64)), h


def test_langton_output_is_binary_and_deterministic():
    img = image_bank()["normal"]
    out = A.alife_langton_ant(img, 0.7, 0.2)
    assert set(np.unique(out)).issubset({0.0, 1.0})
    assert np.array_equal(out, A.alife_langton_ant(img, 0.7, 0.2))


# --------------------------------------------------------------------------- #
# 3. Lenia                                                                    #
# --------------------------------------------------------------------------- #
def _circular_correlate(u, k):
    """Independent toroidal correlation (explicit roll-sum, no scipy)."""
    r = (k.shape[0] - 1) // 2
    out = np.zeros_like(u, np.float64)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            w = float(k[dy + r, dx + r])
            if w != 0.0:
                out += w * np.roll(np.roll(u, -dy, axis=0), -dx, axis=1)
    return out


def test_lenia_kernel_is_a_normalised_radial_ring():
    for radius in (1, 2, 4, 6):
        k = A._lenia_kernel(radius)
        assert k.shape == (2 * radius + 1, 2 * radius + 1)
        assert abs(float(k.sum()) - 1.0) < 1e-12
        assert (k >= 0.0).all()
        # radially symmetric under both flips and under transposition
        assert np.allclose(k, k[::-1, :]) and np.allclose(k, k[:, ::-1])
        assert np.allclose(k, k.T)
        yy, xx = np.mgrid[-radius:radius + 1, -radius:radius + 1]
        rr = np.sqrt(yy ** 2 + xx ** 2) / float(radius)
        assert (k[rr > 1.0] == 0.0).all()    # compact support of radius R
    # for a resolved ring the weight really peaks near relative radius 0.5 and
    # is far smaller at the centre and at the rim (that is what "ring" means)
    k6 = A._lenia_kernel(6)
    yy, xx = np.mgrid[-6:7, -6:7]
    rr = np.sqrt(yy ** 2 + xx ** 2) / 6.0
    peak = rr.flat[int(np.argmax(k6))]
    assert abs(peak - 0.5) < 0.2
    assert k6[6, 6] < 0.05 * k6.max()        # hollow centre
    assert k6[0, 6] < 0.05 * k6.max()        # thin rim


def test_lenia_one_step_matches_an_independent_reference():
    img = image_bank()["normal"]
    radius = A._lenia_radius(img.shape)
    kern = A._lenia_kernel(radius)
    for a in (0.0, 0.35, 1.0):
        mu, sigma, dt = A._lenia_params(a)
        pot = _circular_correlate(img, kern)                 # independent conv
        growth = 2.0 * np.exp(-((pot - mu) ** 2) / (2.0 * sigma ** 2)) - 1.0
        ref = np.clip(img + dt * growth, 0.0, 1.0)
        out = A.alife_lenia(img, a, 0.0)                     # b=0 -> exactly 1 step
        assert np.allclose(out, ref, rtol=0, atol=1e-10), a
        # the potential is a weighted average of a [0,1] field
        assert pot.min() >= -1e-12 and pot.max() <= 1 + 1e-12
        # ... and the published growth mapping is bounded by [-1, 1]
        assert growth.min() >= -1.0 - 1e-12 and growth.max() <= 1.0 + 1e-12


def test_lenia_output_is_continuous_not_binarised():
    # THE distinguishing property vs a Conway-style Life rule: Lenia keeps a
    # continuum of states instead of collapsing onto {0,1}.
    img = image_bank()["normal"]
    for a, b in ((0.0, 0.0), (0.3, 0.5), (0.6, 1.0), (1.0, 0.25)):
        out = A.alife_lenia(img, a, b)
        assert len(np.unique(out)) > 10, (a, b)
        interior = out[(out > 1e-9) & (out < 1 - 1e-9)]
        assert interior.size > out.size // 10, (a, b)


def test_lenia_empty_world_is_an_exact_fixed_point():
    # G(0) < 0 for every a, so the clip keeps an empty world empty forever.
    for a in (0.0, 0.25, 0.5, 0.75, 1.0):
        mu, sigma, _dt = A._lenia_params(a)
        assert 2.0 * np.exp(-(mu ** 2) / (2.0 * sigma ** 2)) - 1.0 < 0.0, a
        for b in (0.0, 0.5, 1.0):
            out = A.alife_lenia(np.zeros((32, 32)), a, b)
            assert out.shape == (32, 32)
            assert np.array_equal(out, np.zeros((32, 32))), (a, b)


def test_lenia_growth_is_bounded_and_the_field_stays_in_the_unit_range():
    for iname, iv in image_bank().items():
        for a, b in ((0.0, 1.0), (0.5, 1.0), (1.0, 1.0)):
            out = A.alife_lenia(iv, a, b)
            assert np.isfinite(out).all(), (iname, a, b)
            assert out.min() >= 0.0 and out.max() <= 1.0, (iname, a, b)
            # a single Euler step can never move a cell further than dt
            _mu, _sigma, dt = A._lenia_params(a)
            one = A.alife_lenia(iv, a, 0.0)
            assert np.abs(one - np.clip(iv, 0, 1)).max() <= dt + 1e-12


def test_lenia_knobs_a_and_b_each_change_the_output():
    img = image_bank()["normal"]
    assert np.abs(A.alife_lenia(img, 0.0, 0.5)
                  - A.alife_lenia(img, 1.0, 0.5)).max() > 1e-3   # mu / sigma / dt
    assert np.abs(A.alife_lenia(img, 0.5, 0.0)
                  - A.alife_lenia(img, 0.5, 1.0)).max() > 1e-3   # step count
    assert np.array_equal(A.alife_lenia(img, 0.4, 0.6),
                          A.alife_lenia(img, 0.4, 0.6))          # deterministic


# --------------------------------------------------------------------------- #
# 4. Abelian sandpile                                                         #
# --------------------------------------------------------------------------- #
def _sequential_stabilise(h):
    """Independent sequential (single-cell, LIFO) sandpile stabiliser.

    Topples one cell at a time in an order that has nothing to do with the op's
    synchronous sweeps, with an explicit bounds check as the dissipative
    boundary. Dhar (1990): the abelian property makes the two results identical.
    """
    h = np.asarray(h, np.int64).copy()
    rows, cols = h.shape
    stack = [(r, c) for r in range(rows) for c in range(cols) if h[r, c] >= 4]
    while stack:
        r, c = stack.pop()
        while h[r, c] >= 4:
            h[r, c] -= 4
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                rr, cc = r + dr, c + dc
                if 0 <= rr < rows and 0 <= cc < cols:
                    h[rr, cc] += 1
                    if h[rr, cc] >= 4:
                        stack.append((rr, cc))
    return h


def test_sandpile_single_four_grain_cell_topples_to_its_four_neighbours():
    # ground truth by hand: 4 grains on one cell -> 0 there, +1 on each of the
    # four orthogonal neighbours, nothing on the diagonals.
    img = image_bank()["single_bright"]          # centre pixel = 1.0, rest 0
    n = img.shape[0]
    r0 = c0 = n // 2
    out = A.alife_sandpile(img, 0.0, 1.0)        # a=0 -> K=4, so h[centre] == 4
    expect = np.zeros((n, n))
    expect[r0 - 1, c0] = expect[r0 + 1, c0] = 1.0
    expect[r0, c0 - 1] = expect[r0, c0 + 1] = 1.0
    assert np.array_equal(out, expect)
    assert out[r0, c0] == 0.0                    # the toppled cell is emptied
    assert out[r0 - 1, c0 - 1] == 0.0            # diagonals get nothing
    # the same at the raw integer-kernel level
    h = np.zeros((n, n), np.int64)
    h[r0, c0] = 4
    stable, sweeps = A._sandpile_relax(h, 10)
    assert sweeps == 1
    assert np.array_equal(stable, expect.astype(np.int64))
    assert int(stable.sum()) == 4                # nothing dissipated (interior)


def test_sandpile_boundary_is_dissipative_not_periodic():
    # a corner cell loses two of its four grains off the grid
    h = np.zeros((7, 7), np.int64)
    h[0, 0] = 4
    stable, _s = A._sandpile_relax(h, 10)
    assert int(stable.sum()) == 2
    assert stable[0, 1] == 1 and stable[1, 0] == 1
    assert stable[0, 0] == 0
    assert stable[-1, 0] == 0 and stable[0, -1] == 0   # no wrap-around


def test_sandpile_full_relaxation_leaves_every_cell_below_four():
    for h in (np.full((14, 14), 9, np.int64),
              ((np.mgrid[0:16, 0:16][0] * 7 + np.mgrid[0:16, 0:16][1] * 5) % 11),
              np.zeros((5, 5), np.int64)):
        h = np.asarray(h, np.int64)
        stable, _s = A._sandpile_relax(h, A._RELAX_CAP)
        assert stable.max() <= 3                       # the critical state
        assert stable.min() >= 0
        assert np.array_equal(stable, _sequential_stabilise(h))

    # end to end through the op, against the independent sequential stabiliser
    yy, xx = np.mgrid[0:12, 0:12]
    img = ((yy * 5 + xx * 3) % 13) / 12.0
    grains = 4 + int(1.0 * 12)                          # a = 1.0 -> K = 16
    ref = _sequential_stabilise(np.rint(img * grains).astype(np.int64))
    assert ref.max() <= 3
    out = A.alife_sandpile(img, 1.0, 1.0)               # b >= 0.9 -> run to stable
    assert np.array_equal(out, ref.astype(np.float64) / float(ref.max()))

    # every battery image relaxes onto a max<=3 grid, so h/max(h) can only take
    # the uniform levels j/mx with mx in {0,1,2,3}
    for iname, iv in image_bank().items():
        uniq = set(np.unique(A.alife_sandpile(iv, 1.0, 1.0)))
        assert (uniq.issubset({0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0})
                or uniq.issubset({0.0, 0.5, 1.0})), (iname, sorted(uniq))


def test_sandpile_is_abelian_order_of_toppling_does_not_matter():
    grids = [
        np.full((12, 12), 9, np.int64),
        ((np.mgrid[0:12, 0:12][0] * 7 + np.mgrid[0:12, 0:12][1] * 5) % 9).astype(np.int64),
        np.pad(np.full((4, 4), 20, np.int64), 4),
    ]
    for h in grids:
        parallel, _s = A._sandpile_relax(h, A._RELAX_CAP)
        sequential = _sequential_stabilise(h)
        assert np.array_equal(parallel, sequential)
        assert parallel.max() <= 3


def test_sandpile_relaxation_is_monotone_in_the_sweep_budget():
    h = np.full((16, 16), 12, np.int64)
    unstable = [int((A._sandpile_relax(h, s)[0] >= 4).sum()) for s in (0, 1, 4, 16, 64)]
    assert unstable[0] == 256                    # nothing relaxed yet
    assert all(unstable[i] >= unstable[i + 1] for i in range(len(unstable) - 1))
    assert unstable[-1] < unstable[0]
    # grains are conserved inside and only lost at the dissipative boundary
    totals = [int(A._sandpile_relax(h, s)[0].sum()) for s in (0, 1, 4, 16, 64)]
    assert totals[0] == 12 * 256
    assert all(totals[i] >= totals[i + 1] for i in range(len(totals) - 1))
    assert totals[-1] < totals[0]


def test_sandpile_knobs_change_the_pile_and_are_deterministic():
    img = image_bank()["normal"]
    assert np.abs(A.alife_sandpile(img, 0.0, 1.0)
                  - A.alife_sandpile(img, 1.0, 1.0)).max() > 1e-3   # grain scale K
    assert np.abs(A.alife_sandpile(img, 1.0, 0.0)
                  - A.alife_sandpile(img, 1.0, 1.0)).max() > 1e-3   # sweep budget
    assert np.array_equal(A.alife_sandpile(img, 0.6, 0.4),
                          A.alife_sandpile(img, 0.6, 0.4))
    # an empty pile has nothing to topple (honest degenerate case)
    assert A.alife_sandpile(np.zeros((16, 16)), 1.0, 1.0).max() == 0.0
