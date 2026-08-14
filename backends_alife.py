"""Artificial-life / generative field evolvers (registry cluster ``alife_``).

This cluster treats the input 2-D image not as a picture to *filter* but as the
**initial condition of a dynamical system**. Each op integrates a classical
pattern-formation model (reaction-diffusion, activator-inhibitor, cellular
automata, curvature/anisotropic PDE flows, aggregation growth, excitable media)
for a fixed number of steps and returns the resulting field, refit to [0,1] and
to the input HxW.

Provenance / HALCON honesty
---------------------------
Every op here carries ``halcon = ""`` and makes **no coverage claim**. MVTec
HALCON has no reaction-diffusion, cellular-automaton, excitable-medium or
aggregation-growth operator (verified against ``data/halcon_graph.json``: no
``gray_scott`` / ``turing`` / ``cellular`` / ``automaton`` / ``life`` /
``aggregation`` node exists), so those members are pure differentiation -- a new
capability, not coverage.

Two members overlap with prior art and are disclosed as such rather than
dressed up as new:

  * ``alife_perona_malik`` is the same PDE family as HALCON's
    ``anisotropic_diffusion`` (which imgevolve already covers elsewhere via
    ``backends_auto`` / ``backends_physics.ph_perona_malik``);
  * ``alife_curvature_flow`` is the same PDE family as HALCON's
    ``mean_curvature_flow`` (already covered via ``backends_auto`` /
    ``backends_physics.ph_mean_curvature_motion``);
  * ``alife_gray_scott`` overlaps ``backends_physics.ph_reaction_diffusion``.

They are kept here as the *evolver-parameterised* members of the family (knobs
mapped to feed/kill, step count and edge scale in the pattern-forming regime, a
toroidal lattice instead of replicated borders), and their ``halcon`` field stays
``""`` precisely so they cannot inflate the coverage number a second time.

Operators (a, b are the two knobs, both in [0,1])
-------------------------------------------------
  alife_gray_scott      Gray-Scott reaction-diffusion (U=1-seed, V=image;
                        Du=0.16, Dv=0.08). a -> feed F=0.02+0.06a AND step count
                        T=8+int(20a); b -> kill K=0.05+0.02b. Turing
                        spots/stripes/labyrinths; returns the normalised V field.
  alife_turing          Gierer-Meinhardt activator-inhibitor short evolution
                        (A_t = Da lap A + rho A^2/H - mu_a A + rho0,
                         H_t = Dh lap H + rho A^2 - mu_h H). a -> inhibitor
                        range (long-range diffusion Dh), b -> step count.
                        Local self-activation + lateral inhibition.
  alife_life_step       Life-like totalistic cellular automaton on the 0.5-
                        threshold of the input. a picks the B/S rule preset
                        (Conway B3/S23, HighLife B36/S23, Day&Night B3678/S34678,
                        Seeds B2/S), b sets the generation count 1..10.
                        Returns the live-cell field (0/1).
  alife_cyclic_ca       Cyclic cellular automaton (Fisch-Gravner-Griffeath):
                        input quantised to N=3+int(9a) states; a cell at state s
                        advances to s+1 (mod N) when at least one Moore
                        neighbour already holds s+1. b sets the step count.
                        Nucleates rotating spiral waves; returns state/(N-1).
  alife_perona_malik    Perona-Malik anisotropic (edge-preserving) diffusion,
                        g(s)=1/(1+(s/kappa)^2), kappa=0.02+0.2a,
                        iters=1+int(15b), lambda=0.2. Smooths inside regions,
                        stops at edges (distinct from a bilateral filter: the
                        conductance is recomputed from the evolving field).
  alife_curvature_flow  Mean-curvature motion / level-set smoothing,
                        u_t = |grad u| * div(grad u/|grad u|), in the stable
                        form (u_xx u_y^2 - 2 u_x u_y u_xy + u_yy u_x^2)/|grad u|^2.
                        a -> step count 1..30, b -> time step dt in [0.05,0.25].
                        Every level curve shrinks by its curvature.
  alife_dla             Deterministic diffusion-limited-aggregation proxy:
                        bright pixels seed the cluster, a diffused "walker"
                        concentration (Gaussian Green's function of the unclaimed
                        field) drives boundary attachment, and each generation
                        attaches the boundary cells whose concentration clears a
                        stickiness threshold. a -> growth generations 1..12,
                        b -> stickiness (high b = selective, dendritic growth;
                        low b = compact, Eden-like growth). Returns the 0/1
                        cluster.
  alife_reaction_bz     Belousov-Zhabotinsky-like excitable medium
                        (Greenberg-Hastings 3-state: rest -> excited ->
                        refractory -> rest). Input tertiles set the initial
                        state; a -> excitation threshold (1..4 excited Moore
                        neighbours needed to fire), b -> step count 1..21.
                        Traveling waves / spirals; returns state/2.

Honest limitation: these are **generative dynamical operators, not filters**.
They consume the input only as an initial condition and then run their own
dynamics for a fixed number of steps, so on a flat/constant input several of
them return a flat output -- nothing nucleates when there is no spatial
structure to break the symmetry. That is the correct behaviour of the model, not
a failure of the op.

All ops are fully deterministic (no random number generator is used anywhere in
this module -- the DLA member is a deterministic proxy of a stochastic process),
finite on every battery input including the degenerate ones, and fail-soft via
the shared ``sanitize`` wrapper.

Contract: ``fn(v, a, b)`` maps a 2-D float64 image in [0,1] (knobs a,b in [0,1])
to a 2-D float64 image in [0,1] of the same HxW.
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


def _norm01(x):
    """Finite-safe min-max normalisation; a constant field maps to itself."""
    x = np.nan_to_num(np.asarray(x, np.float64), nan=0.0, posinf=1.0, neginf=0.0)
    lo = float(x.min()) if x.size else 0.0
    hi = float(x.max()) if x.size else 0.0
    if hi - lo <= 1e-9:                    # degenerate range: no normalisation
        return np.clip(x, 0.0, 1.0)
    return (x - lo) / (hi - lo)


def _shift(x, dy, dx):
    """Toroidal (periodic) lattice shift -- the natural CA/RD boundary."""
    return np.roll(np.roll(x, dy, axis=0), dx, axis=1)


def _lap(x):
    """5-point discrete Laplacian on the torus."""
    return (_shift(x, 1, 0) + _shift(x, -1, 0)
            + _shift(x, 0, 1) + _shift(x, 0, -1) - 4.0 * x)


_MOORE = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))


def _moore_sum(x):
    """Sum of the 8 Moore neighbours (toroidal)."""
    acc = np.zeros_like(x, np.float64)
    for dy, dx in _MOORE:
        acc += _shift(x, dy, dx)
    return acc


def _moore_count_equal(s, tgt):
    """Count Moore neighbours whose state equals ``tgt`` (elementwise array)."""
    acc = np.zeros(s.shape, np.int64)
    for dy, dx in _MOORE:
        acc += (_shift(s, dy, dx) == tgt).astype(np.int64)
    return acc


# --------------------------------------------------------------------------- #
# operators (module-level so tests can call them directly)                    #
# --------------------------------------------------------------------------- #
def alife_gray_scott(v, a, b):
    """Gray-Scott reaction-diffusion seeded by the image.

    Two coupled species on a torus,
        u_t = Du*lap(u) - u v^2 + F (1 - u)
        v_t = Dv*lap(v) + u v^2 - (F + K) v
    with Du=0.16, Dv=0.08. The image seeds v (the autocatalyst) while u starts
    from the depleted complement, so bright input pixels are the nuclei from
    which spots / stripes / labyrinths grow. ``a`` sets the feed rate
    F = 0.02 + 0.06a *and* the number of integration steps T = 8 + int(20a);
    ``b`` sets the kill rate K = 0.05 + 0.02b. Returns the normalised v field.
    """
    x = _img(v)
    a = _knob(a)
    b = _knob(b)
    du, dv = 0.16, 0.08
    feed = 0.02 + 0.06 * a
    kill = 0.05 + 0.02 * b
    steps = 8 + int(a * 20)
    u = 1.0 - 0.5 * x                       # substrate, depleted where v is seeded
    w = 0.25 + 0.5 * x                      # autocatalyst seeded from the image
    w = np.where(x > 1e-9, w, 0.0)
    dt = 1.0
    for _ in range(steps):
        uvv = u * w * w
        u = np.clip(u + dt * (du * _lap(u) - uvv + feed * (1.0 - u)), 0.0, 1.0)
        w = np.clip(w + dt * (dv * _lap(w) + uvv - (feed + kill) * w), 0.0, 1.0)
    return np.clip(_norm01(w), 0.0, 1.0)


def alife_turing(v, a, b):
    """Gierer-Meinhardt activator-inhibitor system (Turing morphogenesis).

        A_t = Da*lap(A) + rho * A^2 / H - mu_a * A + rho0
        H_t = Dh*lap(H) + rho * A^2      - mu_h * H
    Short-range self-activation (A) plus long-range lateral inhibition (H) is the
    classical Turing mechanism for spot/stripe morphogenesis. The image seeds the
    activator; the inhibitor starts at its homogeneous level. ``a`` sets the
    inhibitor range Dh = 0.15 + 1.05a (with Da fixed at 0.02, so a controls the
    diffusion-ratio that decides the pattern wavelength); ``b`` sets the number of
    steps T = 5 + int(25b). Returns the normalised activator field.
    """
    x = _img(v)
    a = _knob(a)
    b = _knob(b)
    d_a, d_h = 0.02, 0.15 + 1.05 * a
    rho, rho0, mu_a, mu_h = 0.05, 0.01, 0.10, 0.12
    dt = 0.1
    steps = 5 + int(b * 25)
    act = 0.5 + 0.5 * x
    inh = np.full(x.shape, 1.0, np.float64)
    for _ in range(steps):
        a2 = act * act
        act_n = act + dt * (d_a * _lap(act) + rho * a2 / (inh + 1e-6) - mu_a * act + rho0)
        inh_n = inh + dt * (d_h * _lap(inh) + rho * a2 - mu_h * inh)
        act = np.clip(act_n, 0.0, 10.0)
        inh = np.clip(inh_n, 1e-3, 50.0)
    return np.clip(_norm01(act), 0.0, 1.0)


# (birth set, survival set) presets, indexed by the ``a`` knob
_LIFE_RULES = (
    ((3,), (2, 3)),                          # Conway's Life        B3/S23
    ((3, 6), (2, 3)),                        # HighLife             B36/S23
    ((3, 6, 7, 8), (3, 4, 6, 7, 8)),         # Day & Night          B3678/S34678
    ((2,), ()),                              # Seeds                B2/S
)


def alife_life_step(v, a, b):
    """Life-like totalistic cellular automaton (Conway-family B/S rules).

    The image is thresholded at 0.5 to obtain the initial live/dead lattice, then
    a totalistic outer-neighbourhood rule is applied on the torus: a dead cell is
    born when its live Moore-neighbour count lies in the birth set B, a live cell
    survives when its count lies in the survival set S. ``a`` picks the rule
    preset -- Conway B3/S23, HighLife B36/S23, Day&Night B3678/S34678, Seeds B2/S
    -- and ``b`` sets the generation count 1 + int(9b). Returns the live-cell
    field as 0.0/1.0.
    """
    x = _img(v)
    a = _knob(a)
    b = _knob(b)
    born, surv = _LIFE_RULES[min(int(a * len(_LIFE_RULES)), len(_LIFE_RULES) - 1)]
    gens = 1 + int(b * 9)
    cell = (x > 0.5).astype(np.float64)
    for _ in range(gens):
        n = np.rint(_moore_sum(cell)).astype(np.int64)
        birth = np.zeros(cell.shape, bool)
        for k in born:
            birth |= (n == k)
        survive = np.zeros(cell.shape, bool)
        for k in surv:
            survive |= (n == k)
        alive = cell > 0.5
        cell = np.where(alive, survive, birth).astype(np.float64)
    return np.clip(cell, 0.0, 1.0)


def alife_cyclic_ca(v, a, b):
    """Cyclic cellular automaton (Fisch-Gravner-Griffeath) -> spiral waves.

    The image is quantised into N = 3 + int(9a) cyclically ordered states; a cell
    in state s advances to (s+1) mod N as soon as at least one of its 8 Moore
    neighbours already holds (s+1) mod N ("eat-the-next-colour"). Repeated on the
    torus this self-organises the initial field into rotating spiral waves and
    demons. ``a`` sets the state count N, ``b`` the step count 1 + int(15b).
    Returns state/(N-1) so the full [0,1] range is used.
    """
    x = _img(v)
    a = _knob(a)
    b = _knob(b)
    n_states = 3 + int(a * 9)
    steps = 1 + int(b * 15)
    s = np.clip((x * n_states).astype(np.int64), 0, n_states - 1)
    for _ in range(steps):
        tgt = (s + 1) % n_states
        cnt = _moore_count_equal(s, tgt)
        s = np.where(cnt >= 1, tgt, s)
    return np.clip(s.astype(np.float64) / float(max(n_states - 1, 1)), 0.0, 1.0)


def alife_perona_malik(v, a, b):
    """Perona-Malik anisotropic (edge-preserving) diffusion.

    Explicit 4-neighbour update I <- I + lam * sum_dir g(|grad_dir I|) grad_dir I
    with the Perona-Malik conductance g(s) = 1/(1 + (s/kappa)^2): inside a flat
    region g -> 1 and the field diffuses like the heat equation, across a strong
    edge g -> 0 and the edge is preserved. Unlike a bilateral filter the
    conductance is recomputed from the *evolving* field at every iteration, which
    is what makes the edges sharpen rather than merely survive. ``a`` sets the
    edge scale kappa = 0.02 + 0.2a, ``b`` the iteration count 1 + int(15b);
    lambda is fixed at 0.2 (<= 0.25, the explicit-scheme stability bound).
    """
    x = _img(v)
    kappa = 0.02 + 0.2 * _knob(a)
    iters = 1 + int(_knob(b) * 15)
    lam = 0.2
    im = x
    for _ in range(iters):
        dn = _shift(im, -1, 0) - im
        ds = _shift(im, 1, 0) - im
        de = _shift(im, 0, 1) - im
        dw = _shift(im, 0, -1) - im
        cn = 1.0 / (1.0 + (dn / kappa) ** 2)
        cs = 1.0 / (1.0 + (ds / kappa) ** 2)
        ce = 1.0 / (1.0 + (de / kappa) ** 2)
        cw = 1.0 / (1.0 + (dw / kappa) ** 2)
        im = im + lam * (cn * dn + cs * ds + ce * de + cw * dw)
        im = np.clip(im, 0.0, 1.0)
    return np.clip(im, 0.0, 1.0)


def alife_curvature_flow(v, a, b):
    """Mean-curvature motion / level-set smoothing (curve-shortening flow).

    Integrates u_t = |grad u| * div(grad u / |grad u|) in the numerically stable
    algebraic form
        u_t = (u_xx u_y^2 - 2 u_x u_y u_xy + u_yy u_x^2) / (u_x^2 + u_y^2 + eps),
    i.e. every level curve of the image moves along its normal at a speed equal
    to its own curvature: small blobs and boundary wiggles vanish, straight edges
    stay put. ``a`` sets the number of steps 1 + int(29a), ``b`` the time step
    dt = 0.05 + 0.2b.
    """
    x = _img(v)
    steps = 1 + int(_knob(a) * 29)
    dt = 0.05 + 0.2 * _knob(b)
    im = x
    for _ in range(steps):
        ix = 0.5 * (_shift(im, 0, -1) - _shift(im, 0, 1))
        iy = 0.5 * (_shift(im, -1, 0) - _shift(im, 1, 0))
        ixx = _shift(im, 0, 1) - 2.0 * im + _shift(im, 0, -1)
        iyy = _shift(im, 1, 0) - 2.0 * im + _shift(im, -1, 0)
        ixy = 0.25 * (_shift(im, 1, 1) - _shift(im, 1, -1)
                      - _shift(im, -1, 1) + _shift(im, -1, -1))
        num = ixx * iy * iy - 2.0 * ix * iy * ixy + iyy * ix * ix
        den = ix * ix + iy * iy + 1e-9
        im = np.clip(im + dt * (num / den), 0.0, 1.0)
    return np.clip(im, 0.0, 1.0)


def alife_dla(v, a, b):
    """Deterministic diffusion-limited-aggregation (DLA) growth proxy.

    Witten-Sander DLA grows a cluster by releasing random walkers that stick on
    contact; the walker density obeys a Laplace equation, so this op replaces the
    random walkers by their *deterministic* mean field: the unclaimed image
    brightness is diffused with a Gaussian Green's function to give a
    concentration u, and each generation the cluster's Moore boundary attaches
    exactly those cells whose concentration clears a stickiness threshold
    (with the single strongest boundary cell always attaching, so growth never
    stalls). Bright pixels (>= 0.75 of the image maximum, or the single brightest
    pixel) are the seed. ``a`` sets the number of growth generations
    1 + int(11a), ``b`` the stickiness: high b selects only the highest-
    concentration tips (dendritic, screened growth), low b attaches nearly the
    whole boundary (compact, Eden-like growth). Returns the 0/1 cluster.
    """
    x = _img(v)
    a = _knob(a)
    b = _knob(b)
    mx = float(x.max())
    if mx <= 1e-9:                          # no bright pixel: nothing nucleates
        return np.zeros(x.shape, np.float64)
    clus = x >= 0.75 * mx
    if not clus.any():
        flat = np.zeros(x.size, bool)
        flat[int(np.argmax(x))] = True
        clus = flat.reshape(x.shape)
    if clus.all():                          # already saturated
        return np.ones(x.shape, np.float64)
    gens = 1 + int(a * 11)
    struct = np.ones((3, 3), bool)          # Moore connectivity
    sigma = 1.5
    for _ in range(gens):
        free = (~clus).astype(np.float64)
        # Mean-field walker concentration. Walkers arrive from the unclaimed
        # space (a uniform far field, weighted by the local image brightness)
        # and are absorbed by the cluster, so diffusing the free-space source
        # approximates the harmonic measure: exposed tips see a high
        # concentration, cells inside fjords are screened.
        conc = ndimage.gaussian_filter(free * (0.2 + 0.8 * x), sigma=sigma, mode="nearest")
        bnd = ndimage.binary_dilation(clus, structure=struct) & (~clus)
        if not bnd.any():
            break
        vals = conc[bnd]
        hi = float(vals.max())
        lo = float(vals.min())
        tau = lo + b * (hi - lo)            # stickiness threshold
        attach = bnd & (conc >= tau - 1e-12)
        if not attach.any():                # always attach the strongest tip
            attach = bnd & (conc >= hi - 1e-12)
        clus = clus | attach
        if clus.all():
            break
    return clus.astype(np.float64)


def alife_reaction_bz(v, a, b):
    """Belousov-Zhabotinsky-like excitable medium (Greenberg-Hastings automaton).

    A 3-state excitable lattice -- 0 = rest, 1 = excited, 2 = refractory -- with
    the Greenberg-Hastings rule: an excited cell becomes refractory, a refractory
    cell relaxes to rest, and a resting cell fires when at least ``thr`` of its 8
    Moore neighbours are excited. Because a refractory cell cannot be re-excited,
    excitation cannot back-propagate and the fronts organise into the travelling
    waves and rotating spirals of the BZ reaction. The image tertiles set the
    initial state (>2/3 excited, 1/3..2/3 refractory, else rest). ``a`` sets the
    excitation threshold thr = 1 + int(3a) neighbours, ``b`` the step count
    1 + int(20b). Returns state/2.
    """
    x = _img(v)
    a = _knob(a)
    b = _knob(b)
    thr = 1 + int(a * 3)                    # 1..4 excited neighbours to fire
    steps = 1 + int(b * 20)
    s = np.where(x > 2.0 / 3.0, 1, np.where(x > 1.0 / 3.0, 2, 0)).astype(np.int64)
    for _ in range(steps):
        exc = (s == 1).astype(np.int64)
        n_exc = np.zeros(s.shape, np.int64)
        for dy, dx in _MOORE:
            n_exc += _shift(exc, dy, dx)
        nxt = np.where(s == 1, 2,
                       np.where(s == 2, 0,
                                np.where(n_exc >= thr, 1, 0)))
        s = nxt.astype(np.int64)
    return np.clip(s.astype(np.float64) / 2.0, 0.0, 1.0)


# --------------------------------------------------------------------------- #
# registry                                                                    #
# --------------------------------------------------------------------------- #
def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    # halcon="" for EVERY op in this cluster. HALCON has no reaction-diffusion /
    # cellular-automaton / excitable-medium / aggregation operator at all, and
    # the two PDE members that DO share a family with HALCON operators
    # (anisotropic_diffusion, mean_curvature_flow) are already covered elsewhere
    # in the registry -- so nothing here claims coverage.
    defs = [
        ("alife_gray_scott", "artificial-life", alife_gray_scott),
        ("alife_turing", "artificial-life", alife_turing),
        ("alife_life_step", "artificial-life", alife_life_step),
        ("alife_cyclic_ca", "artificial-life", alife_cyclic_ca),
        ("alife_perona_malik", "artificial-life", alife_perona_malik),
        ("alife_curvature_flow", "artificial-life", alife_curvature_flow),
        ("alife_dla", "artificial-life", alife_dla),
        ("alife_reaction_bz", "artificial-life", alife_reaction_bz),
    ]
    return [Op(n, c, "", IMAGE, IMAGE, _safe(f, IMAGE)) for (n, c, f) in defs]
