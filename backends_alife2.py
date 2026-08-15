"""Artificial-life evolvers, second cluster (registry cluster ``alife_``).

Companion to :mod:`backends_alife`. That module collected the *continuum*
pattern-formation models (reaction-diffusion, activator-inhibitor, curvature
flows, excitable media). This one collects the four canonical **discrete
artificial-life systems** that have no continuum PDE form and that
:mod:`backends_alife` therefore does not cover:

  * a 1-D elementary cellular automaton drawn as a 2-D *spacetime diagram*
    (the image supplies the initial row, the vertical axis is time);
  * a *turmite* -- a mobile finite-state machine walking the lattice
    (Langton's ant), i.e. an agent-based rather than a field-based rule;
  * Lenia, the *continuous-state, continuous-neighbourhood* generalisation of
    Life (a smooth ring kernel plus a Gaussian growth mapping);
  * the abelian sandpile, a *dissipative integer* automaton whose relaxation is
    order-independent and self-organises to a critical state.

Provenance
----------
Every op is reimplemented from the published description of the model:

  * ``alife_wolfram1d``   -- S. Wolfram, "Statistical mechanics of cellular
    automata", Rev. Mod. Phys. 55(3), 601-644 (1983); Wolfram, *A New Kind of
    Science*, Wolfram Media (2002), ch. 3 (elementary rule numbering).
  * ``alife_langton_ant`` -- C. G. Langton, "Studying artificial life with
    cellular automata", Physica D 22(1-3), 120-149 (1986); the "ant" turmite is
    the 2-state/2-colour member (Turk & Propp's later highway analysis uses the
    same rule).
  * ``alife_lenia``       -- B. W.-C. Chan, "Lenia -- Biology of Artificial
    Life", Complex Systems 28(3), 251-286 (2019) (ring kernel K, potential
    U = K * u, growth G(U) = 2 exp(-(U-mu)^2 / 2 sigma^2) - 1, Euler step dt).
  * ``alife_sandpile``    -- P. Bak, C. Tang, K. Wiesenfeld, "Self-organized
    criticality: an explanation of 1/f noise", Phys. Rev. Lett. 59(4), 381-384
    (1987); D. Dhar, "Self-organized critical state of sandpile automaton
    models", Phys. Rev. Lett. 64(14), 1613-1616 (1990) (the abelian property
    that makes the stabilised configuration independent of toppling order).

HALCON honesty
--------------
Every op here carries ``halcon = ""`` and makes **no coverage claim**. MVTec
HALCON's operator list (``data/halcon_operators.json``, 2313 operators) contains
no ``wolfram`` / ``langton`` / ``lenia`` / ``sandpile`` / ``automat*`` /
``cellular`` / ``avalanche`` entry -- the only ``*ant*`` hits are
``determinant_matrix`` and friends, which are unrelated. These are new
capabilities, not coverage of an existing HALCON operator, so the coverage
number must not move because of them.

Operators (a, b are the two knobs, both in [0,1])
-------------------------------------------------
  alife_wolfram1d    Elementary (radius-1, 2-state) CA spacetime diagram. Row 0
                     is the thresholded top row of the image (a single central
                     seed if that row is empty); row t+1 follows from row t by
                     next = (rule >> (4*left + 2*centre + right)) & 1 on a
                     circular lattice. ``a`` picks the rule from a curated table
                     (30, 90, 110, 184, 150, 250, 54, 60, 45, 105, 0, 255),
                     ``b`` adds evenly spaced extra seed cells to row 0
                     (initial density). Output = the H x W {0,1} spacetime field.
  alife_langton_ant  Langton's ant / turmite on the 0.5-threshold of the image.
                     The ant starts at the grid centre; on a white (0) cell it
                     turns right, flips the cell to 1 and steps forward, on a
                     black (1) cell it turns left, flips the cell to 0 and steps
                     forward (toroidal). ``a`` sets the step count
                     N = 1 + int(400a), ``b`` the initial heading
                     (up / right / down / left). Returns the final {0,1} colour
                     field.
  alife_lenia        Lenia (Chan 2019), the continuous-state generalisation of
                     Life. A normalised Gaussian *ring* kernel K of radius R
                     gives the potential U = K (*) u (circular convolution);
                     the growth map G(U) = 2 exp(-(U-mu)^2/(2 sigma^2)) - 1 is
                     integrated as u <- clip(u + dt G(U), 0, 1). ``a`` sets
                     mu, sigma and dt, ``b`` the step count 1 + int(19b).
                     The output stays *continuous* -- that is the whole point of
                     Lenia versus a binary Life rule.
  alife_sandpile     Abelian (Bak-Tang-Wiesenfeld) sandpile. Grain heights
                     h = round(K * image) with K = 4 + int(12a); any cell with
                     h >= 4 topples, losing 4 grains and giving 1 to each of its
                     4 orthogonal neighbours. The boundary is **dissipative**
                     (grains that leave the grid are lost -- no wrap-around,
                     otherwise the pile could never stabilise). ``b`` sets the
                     number of parallel relaxation sweeps; for b >= 0.9 it
                     relaxes toward stability (work-bounded, so a large maximally-
                     supercritical pile is only partially relaxed). Returns
                     h / max(h) in [0, 1].

Honest limitations
------------------
* These are **generative dynamical operators, not filters.** The image is used
  only as an initial condition; on a structureless input several of them return
  a structureless output (a constant field gives no seed for the CA, an empty
  sandpile stays empty). That is the model behaving correctly, not the op
  failing.
* ``alife_wolfram1d`` consumes only the *first row* of the image -- a 1-D CA has
  no other place to put an initial condition. The rest of the input affects the
  output only through its width/height.
* ``alife_sandpile``'s "relax toward stable" mode (b >= 0.9) bounds its sweep
  count by a total-work budget (``_SANDPILE_BUDGET`` grain-updates), so the op
  runs in ~tens of ms regardless of image size. A small or varied pile reaches
  the stable critical state (max <= 3) well inside the budget; a large,
  maximally-supercritical pile (e.g. a constant bright field) is only PARTIALLY
  relaxed and its output may still hold cells with 4+ grains. Full BTW
  stabilisation is O(L^2) sweeps -- deliberately not attempted here, because a
  registry op is called thousands of times inside the evolution loop and must
  stay fast. This is a real (documented) truncation, not full stabilisation.

Determinism: no random number generator is used anywhere in this module. Every
op is a pure function of (input, a, b) and is bit-reproducible.

Contract: ``fn(v, a, b)`` maps a 2-D float64 image in [0,1] (knobs a, b in
[0,1]) to a 2-D float64 image in [0,1] of the same H x W.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

_EPS = 1e-12


# --------------------------------------------------------------------------- #
# safety wrapper (shared pattern with the other backends)                     #
# --------------------------------------------------------------------------- #
def _safe(fn, out_sort=None):
    from backend_safe import sanitize

    def w(v, a, b):
        try:
            out = fn(v, a, b)
        except Exception:  # noqa: BLE001 - fail-soft per op contract
            out = None
        return sanitize(out, v, out_sort)

    return w


# --------------------------------------------------------------------------- #
# small helpers                                                               #
# --------------------------------------------------------------------------- #
def _img(v):
    """Coerce input to a finite 2-D float64 image in [0,1] (fail-soft)."""
    x = np.asarray(v, np.float64)
    if x.ndim == 3:                       # accidental colour -> luma
        x = x.mean(axis=-1)
    elif x.ndim != 2:
        x = np.atleast_2d(x).astype(np.float64)
    x = np.nan_to_num(x, nan=0.0, posinf=1.0, neginf=0.0)
    if x.size == 0:
        return np.zeros((1, 1), np.float64)
    return np.clip(x, 0.0, 1.0)


def _knob(t):
    """Clamp a knob to [0,1] and strip non-finite values."""
    t = float(np.nan_to_num(np.float64(t), nan=0.0, posinf=1.0, neginf=0.0))
    return float(np.clip(t, 0.0, 1.0))


def _shift(x, dy, dx):
    """Toroidal (periodic) lattice shift -- the natural CA boundary."""
    return np.roll(np.roll(x, dy, axis=0), dx, axis=1)


def _shift_open(x, dy, dx):
    """Non-wrapping (zero-filled) lattice shift -- a *dissipative* boundary.

    Built on :func:`_shift` and then blanking the row/column band that the
    toroidal roll wrapped around, so material pushed off the grid is lost
    instead of reappearing on the opposite edge. This is what the abelian
    sandpile needs: with a periodic boundary the total grain count is conserved
    and a supercritical pile can never stabilise.
    """
    y = _shift(x, dy, dx)
    if dy > 0:
        y[:dy, :] = 0
    elif dy < 0:
        y[dy:, :] = 0
    if dx > 0:
        y[:, :dx] = 0
    elif dx < 0:
        y[:, dx:] = 0
    return y


# --------------------------------------------------------------------------- #
# 1. Wolfram elementary cellular automaton                                    #
# --------------------------------------------------------------------------- #
# Curated elementary rules, indexed by the ``a`` knob. The first ten are the
# classical representatives of Wolfram's four behavioural classes (30 chaotic /
# class 3, 90 the Sierpinski XOR rule, 110 Turing-complete / class 4, 184 the
# traffic rule, 150 the additive three-input XOR, 250 = "left OR right", 54 and
# 60 additive/nested, 45 chaotic, 105 complement-additive). The last two are the
# degenerate calibration rules: 0 (everything dies at once) and 255 (everything
# saturates at once).
_ELEMENTARY_RULES = (30, 90, 110, 184, 150, 250, 54, 60, 45, 105, 0, 255)


def _elementary_step(row, rule):
    """One synchronous update of a 1-D elementary CA row on a circular lattice.

    ``next[i] = (rule >> (4*row[i-1] + 2*row[i] + row[i+1])) & 1`` -- Wolfram's
    (1983) 8-bit numbering of the 256 radius-1, 2-state rules.
    """
    cur = row.astype(np.int64)
    left = np.roll(cur, 1)                  # cell i-1 (circular)
    right = np.roll(cur, -1)                # cell i+1 (circular)
    idx = 4 * left + 2 * cur + right
    return ((int(rule) >> idx) & 1).astype(bool)


def alife_wolfram1d(v, a, b):
    """Wolfram elementary 1-D cellular automaton, drawn as a spacetime diagram.

    Reimplements the elementary (radius-1, two-state) cellular automata of
    S. Wolfram, Rev. Mod. Phys. 55, 601 (1983) / *A New Kind of Science* (2002).
    The initial row is the top row of the image thresholded at 0.5; if that row
    is empty a single central seed is used instead, which is the classical
    initial condition (rule 90 from a single seed is Pascal's triangle mod 2,
    i.e. the Sierpinski gasket). The lattice is circular, one generation is
    written per output row, and row 0 is generation 0, so the output is the H x W
    {0,1} spacetime diagram.

    ``a`` picks the rule from the curated table ``_ELEMENTARY_RULES``;
    ``b`` sets the initial density by adding ``int(b * W/2)`` evenly spaced extra
    seed cells to row 0 (b = 0 leaves the thresholded row untouched).
    """
    x = _img(v)
    a = _knob(a)
    b = _knob(b)
    h, w = x.shape
    rule = _ELEMENTARY_RULES[min(int(a * len(_ELEMENTARY_RULES)),
                                 len(_ELEMENTARY_RULES) - 1)]

    row = x[0] > 0.5
    if not row.any():                        # classical single-seed condition
        row = np.zeros(w, bool)
        row[w // 2] = True
    extra = int(b * (w // 2))
    if extra > 0:                            # b -> initial density
        row = row.copy()
        row[(np.arange(extra) * w) // extra] = True

    out = np.zeros((h, w), np.float64)
    out[0] = row
    for t in range(1, h):
        row = _elementary_step(row, rule)
        out[t] = row
    return out


# --------------------------------------------------------------------------- #
# 2. Langton's ant (turmite)                                                  #
# --------------------------------------------------------------------------- #
# heading index -> (dy, dx); 0 = up, 1 = right, 2 = down, 3 = left, so that
# "turn right" is +1 (mod 4) and "turn left" is -1 (mod 4).
_ANT_DIRS = ((-1, 0), (0, 1), (1, 0), (0, -1))


def alife_langton_ant(v, a, b):
    """Langton's ant (turmite) walking the thresholded image lattice.

    Reimplements the two-colour turmite of C. G. Langton, "Studying artificial
    life with cellular automata", Physica D 22, 120-149 (1986). Cell colours are
    the 0.5-threshold of the image. A single ant starts at the grid centre and,
    at every step, applies the RL rule:

      * on a **white** (0) cell: turn 90 degrees right, flip the cell to 1,
        step forward one cell;
      * on a **black** (1) cell: turn 90 degrees left, flip the cell to 0,
        step forward one cell.

    Movement wraps toroidally. Because every visit flips the cell it stands on,
    starting from an all-white lattice a cell is black exactly when the ant has
    visited it an odd number of times.

    ``a`` sets the number of steps N = 1 + int(400a); ``b`` selects the initial
    heading (up / right / down / left) which mirrors/rotates the whole
    trajectory. Returns the final {0,1} colour field.
    """
    x = _img(v)
    a = _knob(a)
    b = _knob(b)
    grid = (x > 0.5).astype(np.int64)
    h, w = grid.shape
    steps = 1 + int(a * 400)
    head = min(int(b * 4), 3)
    r, c = h // 2, w // 2
    for _ in range(steps):
        if grid[r, c] == 0:
            head = (head + 1) % 4            # white -> turn right
            grid[r, c] = 1
        else:
            head = (head - 1) % 4            # black -> turn left
            grid[r, c] = 0
        dy, dx = _ANT_DIRS[head]
        r = (r + dy) % h
        c = (c + dx) % w
    return grid.astype(np.float64)


# --------------------------------------------------------------------------- #
# 3. Lenia (continuous cellular automaton)                                    #
# --------------------------------------------------------------------------- #
_LENIA_SHELL_MU = 0.5          # ring kernel peaks at half the radius
_LENIA_SHELL_SIGMA = 0.15      # ring thickness (Chan's default shape)


def _lenia_radius(shape):
    """Kernel radius R for an image of this shape (>=1, <=6, <= H/4 and W/4)."""
    h, w = int(shape[0]), int(shape[1])
    return int(np.clip(min(h, w) // 4, 2, 6))   # >=2: R=1 degenerates to a box, not a ring


def _lenia_kernel(radius):
    """Normalised Gaussian *ring* (annulus shell) kernel of Lenia (Chan 2019).

        K(r) ∝ exp(-(r/R - 0.5)^2 / (2 * 0.15^2))   for r <= R, else 0,
    normalised so that sum(K) == 1 (hence the potential U = K (*) u is a
    weighted average and inherits u's [0,1] range).
    """
    r = int(max(1, radius))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1].astype(np.float64)
    rr = np.sqrt(yy * yy + xx * xx) / float(r)
    k = np.where(rr <= 1.0,
                 np.exp(-((rr - _LENIA_SHELL_MU) ** 2)
                        / (2.0 * _LENIA_SHELL_SIGMA ** 2)),
                 0.0)
    s = float(k.sum())
    return k / s if s > _EPS else k


def _lenia_params(a):
    """(mu, sigma, dt) from knob ``a``.

    mu stays comfortably above sigma * sqrt(2 ln 2) over the whole range, so
    G(0) < 0 for every ``a`` and the empty state is always a stable fixed point
    (an empty Lenia world never spontaneously ignites).
    """
    a = _knob(a)
    mu = 0.08 + 0.25 * a
    sigma = 0.03 + 0.05 * a
    dt = 0.10 + 0.15 * a
    return mu, sigma, dt


def _lenia_growth(u_pot, mu, sigma):
    """Lenia's Gaussian growth mapping G(U) = 2 exp(-(U-mu)^2/(2 sigma^2)) - 1."""
    return 2.0 * np.exp(-((u_pot - mu) ** 2) / (2.0 * sigma * sigma)) - 1.0


def alife_lenia(v, a, b):
    """Lenia continuous cellular automaton (Bert Chan, Complex Systems 2019).

    Lenia generalises Conway's Life to a *continuous* state space, a continuous
    neighbourhood and a continuous time step. The field u starts as the image.
    A normalised Gaussian ring kernel K of radius R (peaking at relative radius
    0.5) gives the potential U = K (*) u as a circular convolution; the growth
    mapping G(U) = 2 exp(-(U-mu)^2 / (2 sigma^2)) - 1 is in [-1, 1] and is
    integrated explicitly as u <- clip(u + dt * G(U), 0, 1).

    ``a`` sets the growth centre mu = 0.08 + 0.25a, its width
    sigma = 0.03 + 0.05a and the time step dt = 0.10 + 0.15a; ``b`` sets the
    number of steps 1 + int(19b). The output is deliberately **not** binarised
    -- keeping intermediate values is exactly what separates Lenia from a
    discrete Life rule.
    """
    x = _img(v)
    a = _knob(a)
    b = _knob(b)
    h, w = x.shape
    if h < 3 or w < 3:                       # nothing to convolve over
        return np.clip(x, 0.0, 1.0)
    mu, sigma, dt = _lenia_params(a)
    steps = 1 + int(b * 19)
    kern = _lenia_kernel(_lenia_radius(x.shape))
    u = x
    for _ in range(steps):
        pot = ndimage.convolve(u, kern, mode="wrap")
        u = np.clip(u + dt * _lenia_growth(pot, mu, sigma), 0.0, 1.0)
    return np.clip(u, 0.0, 1.0)


# --------------------------------------------------------------------------- #
# 4. Abelian sandpile (Bak-Tang-Wiesenfeld)                                   #
# --------------------------------------------------------------------------- #
_RELAX_CAP = 4000        # hard ceiling on sweeps (small piles stabilise far below this)
# Total-work budget for the "relax toward stable" mode: the sweep count is bounded
# by BUDGET // pixels, so a small/varied pile gets enough sweeps to fully stabilise
# while a large maximally-supercritical pile is only partially relaxed — which keeps
# this registry op FAST (~tens of ms worst case) no matter the image size. Full BTW
# stabilisation is O(L^2) sweeps and would stall the evolution loop on big inputs.
_SANDPILE_BUDGET = 8_000_000


def _sandpile_relax(h, max_sweeps):
    """Relax an integer sandpile by parallel toppling sweeps (BTW 1987).

    Every cell holding at least 4 grains topples simultaneously: it loses 4
    grains and passes 1 to each of its 4 orthogonal neighbours. Grains pushed
    off the grid are **lost** (dissipative / open boundary, via
    :func:`_shift_open`) -- the standard BTW boundary condition, and the reason
    a supercritical pile can reach a stable state at all.

    Dhar (1990) proved the model is *abelian*: the stabilised configuration and
    the per-cell topple counts do not depend on the order in which unstable
    cells are toppled, so this parallel sweep and any sequential order agree.

    Returns ``(h_stable, sweeps_used)`` with ``h_stable`` a fresh int64 array.
    """
    h = np.asarray(h, np.int64).copy()
    cap = int(max(0, max_sweeps))
    used = 0
    while used < cap:
        unstable = h >= 4
        if not unstable.any():
            break
        u = unstable.astype(np.int64)
        h = (h - 4 * u
             + _shift_open(u, 1, 0) + _shift_open(u, -1, 0)
             + _shift_open(u, 0, 1) + _shift_open(u, 0, -1))
        used += 1
    return h, used


def alife_sandpile(v, a, b):
    """Abelian sandpile / self-organised criticality (Bak-Tang-Wiesenfeld 1987).

    The image is quantised to integer grain heights h = round(K * image) with
    K = 4 + int(12a), then relaxed by the BTW toppling rule: a cell with 4 or
    more grains gives one grain to each orthogonal neighbour and keeps the rest.
    The boundary is dissipative (grains leaving the grid are lost), which is what
    lets the pile settle into the self-organised critical state where every cell
    holds at most 3 grains.

    ``a`` sets the initial grain scale K (how supercritical the pile starts);
    ``b`` sets the number of parallel relaxation sweeps 1 + int(50b). For
    b >= 0.9 the pile relaxes *toward* stability with early termination, but the
    sweep count is bounded by a total-work budget (``_SANDPILE_BUDGET`` grain-
    updates) so the op stays fast on any image size: a small or varied pile
    reaches the stable critical state (every cell <= 3), while a very large
    maximally-supercritical pile is only partially relaxed (full BTW
    stabilisation is O(L^2) sweeps). Returns h / max(h) in [0, 1]; a fully
    relaxed pile (max 3) takes values in {0, 1/3, 2/3, 1} (or {0, 1/2, 1} when
    the stable maximum is 2).
    """
    x = _img(v)
    a = _knob(a)
    b = _knob(b)
    grains = 4 + int(a * 12)
    h = np.rint(x * grains).astype(np.int64)
    if b >= 0.9:                              # relax toward stability, work-bounded
        sweeps = min(_RELAX_CAP, max(64, _SANDPILE_BUDGET // max(int(h.size), 1)))
    else:
        sweeps = 1 + int(b * 50)
    h, _used = _sandpile_relax(h, sweeps)
    mx = int(h.max()) if h.size else 0
    if mx <= 0:
        return np.zeros(x.shape, np.float64)
    return np.clip(h.astype(np.float64) / float(mx), 0.0, 1.0)


# --------------------------------------------------------------------------- #
# registry                                                                    #
# --------------------------------------------------------------------------- #
def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    # halcon="" for EVERY op in this cluster. HALCON's 2313-operator list has no
    # elementary-CA, turmite, Lenia or sandpile operator (no wolfram / langton /
    # lenia / sandpile / automat* / cellular / avalanche entry exists), so none
    # of these may claim coverage of an existing operator.
    defs = [
        ("alife_wolfram1d", "artificial-life", alife_wolfram1d),
        ("alife_langton_ant", "artificial-life", alife_langton_ant),
        ("alife_lenia", "artificial-life", alife_lenia),
        ("alife_sandpile", "artificial-life", alife_sandpile),
    ]
    return [Op(n, c, "", IMAGE, IMAGE, _safe(f, IMAGE)) for (n, c, f) in defs]
