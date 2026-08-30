"""Ground-truth + contract tests for backends_physics.py (registry cluster ph_).

Does NOT import ops.py. It drives the module's ``build()`` through a tiny ``_Op``
stub for the universal functional gate, and calls each module-level PDE operator
directly to prove it implements the genuine algorithm its name (and, where set,
its HALCON operator) promises.
"""
from __future__ import annotations

import numpy as np

import backends_physics as P


# --------------------------------------------------------------------------- #
# stub registry + helpers (mirrors ops.Op's positional construction)          #
# --------------------------------------------------------------------------- #
class _Op:
    def __init__(self, *a):
        self.name = a[0]
        self.halcon = a[2]
        self.in_sort = a[3]
        self.out_sort = a[4]
        self.fn = a[5]


def _norm(x):
    return x / m if (m := float(np.max(np.abs(x)))) > 1e-8 else x


def _binm(v):
    return np.asarray(v) > 0.5


OPS = P.build(_Op, "image", "region", "feature", "contour", _norm, _binm)
KNOBS = [(0.3, 0.4), (0.6, 0.7), (0.15, 0.85)]

_N = 48


def _image_bank():
    yy, xx = np.mgrid[0:_N, 0:_N].astype(np.float64)
    grad = xx / (_N - 1)
    disk = ((yy - _N * 0.35) ** 2 + (xx - _N * 0.4) ** 2) < (_N * 0.18) ** 2
    rng = np.random.default_rng(20260814)
    normal = np.clip(0.35 * grad + 0.45 * disk + 0.05 * rng.standard_normal((_N, _N)), 0, 1)
    single = np.zeros((_N, _N))
    single[_N // 2, _N // 2] = 1.0
    return {
        "normal": normal,
        "const0": np.zeros((_N, _N)),
        "const1": np.ones((_N, _N)),
        "const_mid": np.full((_N, _N), 0.42),
        "tiny4": (np.arange(16, dtype=np.float64) / 15.0).reshape(4, 4),
        "single_bright": single,
    }


# --------------------------------------------------------------------------- #
# structural sanity                                                           #
# --------------------------------------------------------------------------- #
def test_registry_shape_and_unique_names():
    assert len(OPS) == 6
    names = [o.name for o in OPS]
    assert len(set(names)) == len(names)
    for o in OPS:
        assert o.name.startswith("ph_")
        assert o.in_sort == "image" and o.out_sort == "image"


def test_halcon_names_are_real_uncovered_operators_or_blank():
    """Non-empty halcon names must be the real, assigned MVTec operators; the two
    genuinely-new PDEs (Gray-Scott, ROF TV flow) carry ""."""
    # All carry "": the four PDE names (anisotropic/isotropic/coherence/mean_curvature) are
    # ALREADY covered by backends_auto, so these more-faithful implementations make no
    # (double) coverage claim; the other two are genuinely-new PDEs.
    got = {o.name: o.halcon for o in OPS}
    assert got == {
        "ph_perona_malik": "",
        "ph_coherence_enhancing_diffusion": "",
        "ph_reaction_diffusion": "",
        "ph_heat_flow": "",
        "ph_mean_curvature_motion": "",
        "ph_total_variation_flow": "",
    }
    for o in OPS:
        if o.halcon:
            assert " " not in o.halcon


def test_nonempty_halcon_names_exist_in_graph():
    """Every claimed HALCON name must be a real operator node in halcon_graph.json."""
    import json
    from pathlib import Path

    graph = json.loads(
        (Path(__file__).resolve().parents[1] / "fullseye" / "data" / "halcon_graph.json").read_text(
            encoding="utf-8"
        )
    )
    nodes = graph["nodes"]
    for o in OPS:
        if o.halcon:
            assert o.halcon in nodes, o.halcon


# --------------------------------------------------------------------------- #
# FUNCTIONAL GATE: every op, every canonical input, every knob pair           #
# --------------------------------------------------------------------------- #
def test_functional_gate():
    bank = _image_bank()
    for op in OPS:
        for iname, iv in bank.items():
            for a, b in KNOBS:
                out = op.fn(np.array(iv, copy=True), a, b)
                tag = f"{op.name}/{iname}/a={a},b={b}"
                assert isinstance(out, np.ndarray), tag
                assert out.ndim == 2, tag
                assert out.dtype == np.float64, tag
                assert np.isfinite(out).all(), tag
                assert out.min() >= -1e-9 and out.max() <= 1 + 1e-9, tag
                again = op.fn(np.array(iv, copy=True), a, b)
                assert np.array_equal(out, again), tag       # deterministic


def test_ops_never_raise_and_preserve_shape():
    bank = _image_bank()
    for op in OPS:
        for iv in bank.values():
            for a, b in KNOBS:
                out = op.fn(np.array(iv, copy=True), a, b)
                assert out.shape == np.asarray(iv).shape


# --------------------------------------------------------------------------- #
# GROUND TRUTH per operator                                                   #
# --------------------------------------------------------------------------- #
def _step_edge(h=32, w=40, split=20, lo=0.0, hi=1.0):
    im = np.full((h, w), lo)
    im[:, split:] = hi
    return im


def test_heat_flow_blurs_a_step_edge():
    """Linear heat / isotropic diffusion: the step's maximum gradient must drop
    (energy spreads), and stronger a (more time) blurs strictly more."""
    step = _step_edge()
    g0 = np.abs(np.diff(step, axis=1)).max()
    weak = P.ph_heat_flow(step, 0.2, 0.0)
    strong = P.ph_heat_flow(step, 0.8, 0.0)
    g_weak = np.abs(np.diff(weak, axis=1)).max()
    g_strong = np.abs(np.diff(strong, axis=1)).max()
    assert g_weak < g0                       # gradient max drops
    assert g_strong < g_weak                 # more time => more blur
    # total intensity is conserved by pure diffusion (no-flux boundary)
    assert abs(step.sum() - weak.sum()) < 1e-6


def test_perona_malik_preserves_strong_edge_but_smooths_noise():
    """Perona-Malik: a strong edge (|grad|>>k) survives while flat-region noise
    (|grad|<<k) is diffused away."""
    rng = np.random.default_rng(11)
    base = np.where(np.arange(48)[None, :] < 24, 0.2, 0.8) * np.ones((48, 48))
    noisy = np.clip(base + 0.05 * rng.standard_normal((48, 48)), 0, 1)
    pm = P.ph_perona_malik(noisy, 0.5, 0.15)          # k ~ 0.075, edge >> k
    # edge across the central boundary stays sharp
    edge_before = abs(noisy[:, 24].mean() - noisy[:, 23].mean())
    edge_after = abs(pm[:, 24].mean() - pm[:, 23].mean())
    assert edge_after > 0.5                            # strong edge preserved (~0.6)
    assert edge_after > 0.85 * edge_before
    # flat-region variance collapses
    flat_before = noisy[:, 2:22].var()
    flat_after = pm[:, 2:22].var()
    assert flat_after < 0.15 * flat_before
    # heat flow (isotropic) at comparable smoothing would blur the edge much more
    heat = P.ph_heat_flow(noisy, 0.5, 0.0)
    assert edge_after > 2.0 * abs(heat[:, 24].mean() - heat[:, 23].mean())


def test_coherence_enhancing_diffusion_smooths_along_not_across_structure():
    """Weickert CED: on horizontal stripes (coherent horizontal structure) it
    smooths noise ALONG the stripes while preserving the ACROSS-stripe contrast —
    unlike isotropic heat, which destroys that contrast."""
    rng = np.random.default_rng(3)
    n = 56
    stripe = 0.5 + 0.35 * np.sign(np.sin(2 * np.pi * np.arange(n) / 10.0))
    img = np.tile(stripe[:, None], (1, n))
    noisy = np.clip(img + 0.08 * rng.standard_normal((n, n)), 0, 1)
    ced = P.ph_coherence_enhancing_diffusion(noisy, 0.8, 0.5)
    heat = P.ph_heat_flow(noisy, 0.4, 0.0)

    def along_row_var(x):                       # noise along the stripe direction
        return float(np.mean(np.var(x, axis=1)))

    def cross_contrast(x):                      # peak-to-trough of the row profile
        prof = x.mean(axis=1)
        return float(prof.max() - prof.min())

    # (1) noise along the coherent direction is reduced
    assert along_row_var(ced) < 0.5 * along_row_var(noisy)
    # (2) the across-stripe contrast is preserved (anisotropic: does NOT diffuse across)
    assert cross_contrast(ced) > 0.9 * cross_contrast(noisy)
    # (3) and preserved far better than isotropic diffusion would
    assert cross_contrast(ced) > 1.5 * cross_contrast(heat)


def test_mean_curvature_motion_shrinks_a_disk():
    """Curve-shortening flow: each level curve moves inward by its curvature, so a
    bright disk's area and boundary length both shrink."""
    n = 64
    yy, xx = np.mgrid[0:n, 0:n]
    disk = (((xx - n / 2) ** 2 + (yy - n / 2) ** 2) < 12 ** 2).astype(np.float64)

    def area(x):
        return int((x > 0.5).sum())

    def perimeter(x):
        b = (x > 0.5).astype(np.int64)
        edges = np.abs(np.diff(b, axis=0, prepend=b[:1])) + np.abs(
            np.diff(b, axis=1, prepend=b[:, :1])
        )
        return int((b * (edges > 0)).sum())

    m = P.ph_mean_curvature_motion(disk, 1.0, 0.0)
    assert area(m) < area(disk)                  # region shrinks
    assert perimeter(m) < perimeter(disk)        # boundary shortens
    # the disk stays a single centered blob (does not fragment or invert)
    assert m[n // 2, n // 2] > 0.5
    # more steps => more shrink
    less = P.ph_mean_curvature_motion(disk, 0.4, 0.0)
    assert area(m) < area(less)


def test_total_variation_flow_denoises_edge_preservingly():
    """ROF TV flow: total variation and flat-region noise drop, while a step edge
    is kept far sharper than isotropic heat would at the same denoising level."""
    rng = np.random.default_rng(7)
    base = np.where(np.arange(48)[None, :] < 24, 0.3, 0.7) * np.ones((48, 48))
    noisy = np.clip(base + 0.06 * rng.standard_normal((48, 48)), 0, 1)
    tv = P.ph_total_variation_flow(noisy, 0.7, 0.3)

    def total_variation(x):
        return float(np.abs(np.diff(x, axis=1)).sum() + np.abs(np.diff(x, axis=0)).sum())

    def flat_var(x):
        return float(0.5 * (x[:, 2:22].var() + x[:, 26:46].var()))

    def edge(x):
        return abs(x[:, 24].mean() - x[:, 23].mean())

    assert total_variation(tv) < 0.5 * total_variation(noisy)   # TV energy drops
    assert flat_var(tv) < 0.3 * flat_var(noisy)                 # noise removed
    heat = P.ph_heat_flow(noisy, 0.5, 0.0)
    # both reach comparable flat smoothness, but TV keeps a much sharper edge
    assert flat_var(heat) < 0.3 * flat_var(noisy)
    assert edge(tv) > 1.5 * edge(heat)


def test_reaction_diffusion_bounded_deterministic_and_reactive():
    """Gray-Scott: output stays in [0,1], is deterministic, forms spatial pattern,
    and genuinely depends on the feed/kill (a,b) parameters (not a mere blur)."""
    seed = np.zeros((60, 60))
    seed[26:34, 26:34] = 1.0
    r1 = P.ph_reaction_diffusion(seed, 0.3, 0.4)
    r1b = P.ph_reaction_diffusion(seed, 0.3, 0.4)
    r2 = P.ph_reaction_diffusion(seed, 0.6, 0.7)
    assert r1.min() >= 0.0 and r1.max() <= 1.0                  # bounded
    assert np.array_equal(r1, r1b)                              # deterministic
    assert r1.std() > 1e-3                                      # spatial structure
    assert not np.allclose(r1, r2)                              # feed/kill matter
    # the u*v^2 reaction makes it differ from a pure diffusion (heat) of the seed
    heat = P.ph_heat_flow(seed, 0.5, 0.0)
    assert not np.allclose(r1, heat)
