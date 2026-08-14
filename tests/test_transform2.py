"""Ground-truth + contract tests for backends_transform2.py (cluster ``tf_``).

Does NOT import ops.py. It drives the module's ``build()`` through a tiny ``_Op``
stub for the universal functional gate, then calls each module-level operator
directly to prove it implements the genuine transform its name promises.
"""
from __future__ import annotations

import numpy as np

import backends_transform2 as T


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
    m = float(np.max(np.abs(x)))
    return x / m if m > 1e-8 else x


def _binm(v):
    return np.asarray(v) > 0.5


OPS = T.build(_Op, "image", "region", "feature", "contour", _norm, _binm)
KNOBS = [(0.3, 0.4), (0.6, 0.7), (0.15, 0.85)]

_N = 48


def _corr(a, b):
    return float(np.corrcoef(np.asarray(a).ravel(), np.asarray(b).ravel())[0, 1])


def _image_bank():
    yy, xx = np.mgrid[0:_N, 0:_N].astype(np.float64)
    grad = xx / (_N - 1)
    disk = ((yy - _N * 0.35) ** 2 + (xx - _N * 0.4) ** 2) < (_N * 0.18) ** 2
    rng = np.random.default_rng(20260814)
    normal = np.clip(0.35 * grad + 0.45 * disk + 0.03 * rng.standard_normal((_N, _N)), 0, 1)
    single = np.zeros((_N, _N))
    single[_N // 2, _N // 2] = 1.0
    return {
        "normal": normal,
        "const0": np.zeros((_N, _N)),
        "const1": np.ones((_N, _N)),
        "const_mid": np.full((_N, _N), 0.42),
        "single_bright": single,
        "vedge": np.where(xx < _N / 2, 0.2, 0.8),
    }


# --------------------------------------------------------------------------- #
# structural sanity                                                           #
# --------------------------------------------------------------------------- #
def test_registry_shape_and_names():
    assert len(OPS) == 7
    names = [o.name for o in OPS]
    assert len(set(names)) == len(names)
    for o in OPS:
        assert o.name.startswith("tf_")
        assert o.in_sort == "image" and o.out_sort == "image"
        # every op in this wave is a NEW capability with no uncovered HALCON analog
        assert o.halcon == ""


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
                assert out.shape == np.asarray(iv).shape, tag
                again = op.fn(np.array(iv, copy=True), a, b)
                assert np.array_equal(out, again), tag          # deterministic


def test_ops_never_raise_on_odd_input():
    odd = [
        np.zeros((1, 1)),
        np.ones((2, 3)),
        np.full((5, 5), np.nan),
        np.array([[np.inf, -np.inf], [0.0, 1.0]]),
    ]
    for op in OPS:
        for iv in odd:
            for a, b in KNOBS:
                out = op.fn(np.array(iv, copy=True), a, b)
                assert isinstance(out, np.ndarray)
                assert np.isfinite(out).all()


# --------------------------------------------------------------------------- #
# GROUND TRUTH per operator                                                   #
# --------------------------------------------------------------------------- #
def test_log_polar_of_ring_is_a_horizontal_band():
    """A centred ring is rotationally symmetric, so under the log-polar map (row =
    log-radius, col = angle) it lands on the single log-radius row(s) that match
    its radius -> a bright, angle-uniform horizontal band, dark elsewhere."""
    n = 60
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    dist = np.hypot(xx - (n - 1) / 2.0, yy - (n - 1) / 2.0)
    ring = ((dist >= 14) & (dist <= 18)).astype(float)      # centred annulus
    out = T.tf_log_polar(ring, 0.9, 0.0)
    assert out.shape == ring.shape
    row_means = out.mean(axis=1)
    peak = int(np.argmax(row_means))
    # the peak row is bright and (being one radius, all angles) nearly uniform
    assert row_means[peak] > 0.4
    assert out[peak].std() < 0.25                            # horizontal band: flat in angle
    # it is a *band*: far-away radii (inner hole / outside the ring) are dark
    assert row_means[0] < 0.2                                # smallest radius -> inside hole
    assert row_means[-1] < 0.2                               # largest radius -> outside ring
    assert row_means[peak] > 3.0 * float(np.median(row_means))


def test_log_polar_rotation_becomes_column_shift():
    """b adds an angular offset -> the whole log-polar image shifts along the
    angle (column) axis; the transform of a rotated source is a column-roll."""
    n = 60
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    dist = np.hypot(xx - (n - 1) / 2.0, yy - (n - 1) / 2.0)
    ang = np.arctan2(yy - (n - 1) / 2.0, xx - (n - 1) / 2.0)
    wedge = (((dist >= 8) & (dist <= 20)) & (np.abs(ang) < 0.4)).astype(float)
    base = T.tf_log_polar(wedge, 0.9, 0.0)
    shifted = T.tf_log_polar(wedge, 0.9, 0.25)              # +quarter turn in angle
    # find the column shift that best re-aligns the two (a pure horizontal roll)
    best = max(range(base.shape[1]),
               key=lambda s: _corr(base, np.roll(shifted, s, axis=1)))
    assert best != 0                                        # a genuine column shift
    assert _corr(base, np.roll(shifted, best, axis=1)) > 0.9


def test_radon_sinogram_symmetric_object_is_angle_independent():
    """The Radon projections of a centred (rotationally symmetric) disk are the
    same at every angle -> the sinogram rows are near-identical and their masses
    are conserved."""
    n = 60
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    disk = (np.hypot(xx - (n - 1) / 2.0, yy - (n - 1) / 2.0) <= 12).astype(float)
    sino = T.tf_radon_sinogram(disk, 0.9, 0.0)
    assert sino.shape == disk.shape
    assert _corr(sino[5], sino[30]) > 0.9                   # rows agree across angle
    sums = sino.sum(axis=1)
    assert float(sums.std()) / float(sums.mean()) < 0.12    # mass conserved (rotation)


def test_radon_sinogram_offcenter_point_traces_a_sine():
    """An off-centre point projects to a detector position that swings with the
    view angle -> the projection peak column moves as the angle advances."""
    n = 60
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    blob = np.exp(-(((xx - 45.0) ** 2 + (yy - 30.0) ** 2) / 4.0))   # off-centre dot
    sino = T.tf_radon_sinogram(blob, 1.0, 0.0)             # full 180deg span
    col0 = int(np.argmax(sino[0]))                          # ~0 deg
    col90 = int(np.argmax(sino[n // 3]))                    # ~60 deg into the span
    assert abs(col0 - col90) >= 5                           # the peak column moved


def test_steerable_filter_peaks_on_matching_gradient_orientation():
    """The oriented derivative-of-Gaussian at theta responds to gradients along
    theta. A vertical edge (horizontal, theta=0, gradient) is picked up by the
    theta=0 filter but not by the orthogonal theta=pi/2 one, and vice-versa for a
    horizontal edge."""
    n = 40
    xx = np.mgrid[0:n, 0:n][1].astype(float)
    vedge = np.where(xx < n / 2, 0.2, 0.8)                  # gradient along x (theta=0)
    dev0 = np.abs(T.tf_steerable_filter(vedge, 0.0, 0.3) - 0.5)
    dev90 = np.abs(T.tf_steerable_filter(vedge, 0.5, 0.3) - 0.5)
    assert dev0.max() > 2.0 * dev90.max()                  # aligned filter fires, orthogonal ~silent
    yy = np.mgrid[0:n, 0:n][0].astype(float)
    hedge = np.where(yy < n / 2, 0.2, 0.8)                  # gradient along y (theta=pi/2)
    hdev0 = np.abs(T.tf_steerable_filter(hedge, 0.0, 0.3) - 0.5)
    hdev90 = np.abs(T.tf_steerable_filter(hedge, 0.5, 0.3) - 0.5)
    assert hdev90.max() > 2.0 * hdev0.max()                # orientation selectivity flips


def test_phase_congruency_is_illumination_invariant_and_peaks_at_edges():
    """Phase congruency is E/A, invariant to an affine illumination change
    (gain scales E and A together; the offset is DC and log-Gabor carries no DC),
    and it peaks at the edge."""
    n = 40
    xx = np.mgrid[0:n, 0:n][1].astype(float)
    edge = np.where(xx < n / 2, 0.2, 0.8)
    pc = T.tf_phase_congruency(edge, 0.1, 0.5)
    bright = np.where(xx < n / 2, 0.3, 0.6)                 # 0.5*edge + 0.2 (affine)
    pc2 = T.tf_phase_congruency(bright, 0.1, 0.5)
    assert _corr(pc, pc2) > 0.999                          # illumination-invariant
    assert float(np.max(np.abs(pc - pc2))) < 1e-5
    # peaks at the edge column (col ~ n/2), not in the flat interiors
    assert pc[:, n // 2 - 3:n // 2 + 3].mean() > pc[:, :6].mean() + 0.05
    assert pc[:, n // 2 - 3:n // 2 + 3].mean() > pc[:, -6:].mean() + 0.05


def test_gradient_domain_reintegrate_reconstructs_then_edge_preserves():
    """a=0 keeps every gradient -> Poisson reintegration recovers the original
    (up to an affine rescale). a>0 zeros small gradients -> flat regions flatten
    while the strong edge survives."""
    rng = np.random.default_rng(7)
    smooth = np.clip(0.5 + 0.2 * np.sin(np.linspace(0, 3, 32))[:, None]
                     + 0.2 * np.cos(np.linspace(0, 4, 32))[None, :], 0, 1)
    recon = T.tf_gradient_domain_reintegrate(smooth, 0.0, 0.0)
    assert _corr(recon, smooth) > 0.99                     # faithful reconstruction

    n = 40
    xx = np.mgrid[0:n, 0:n][1].astype(float)
    step = np.where(xx < n / 2, 0.3, 0.7)
    noisy = np.clip(step + 0.03 * rng.standard_normal((n, n)), 0, 1)
    out = T.tf_gradient_domain_reintegrate(noisy, 0.35, 0.0)
    left = out[:, 3:12]
    right = out[:, -12:-3]
    # noise in the flat regions is suppressed relative to the input flat regions
    assert left.std() < noisy[:, 3:12].std()
    assert right.std() < noisy[:, -12:-3].std()
    # the edge (a big gradient, kept) still separates the two plateaus strongly
    assert right.mean() - left.mean() > 0.5


def test_census_transform_gain_invariant_and_matches_hand_value():
    """The 3x3 census signature depends only on the ordering of centre vs
    neighbours, so multiplying the image by a positive constant leaves it exactly
    unchanged; a hand-computed 3x3 confirms the bit packing."""
    rng = np.random.default_rng(11)
    img = np.clip(rng.random((30, 30)), 0, 1)
    for a in (0.0, 0.3):
        base = T.tf_census_transform(img, a, 0.4)
        gained = T.tf_census_transform(0.5 * img, a, 0.4)  # global gain
        assert np.array_equal(base, gained)                # exactly gain-invariant
    tiny = np.array([[0.1, 0.2, 0.3],
                     [0.4, 0.5, 0.6],
                     [0.7, 0.8, 0.9]])
    out = T.tf_census_transform(tiny, 0.0, 0.0)
    # centre 0.5 beats the 4 smaller neighbours (bits 0,1,2,3) -> 1+2+4+8 = 15
    assert np.isclose(out[1, 1], 15.0 / 255.0)
    assert out.std() > 0                                   # not a constant image


def test_rank_transform_gain_invariant_ramp_and_extrema():
    """The local rank is the fraction of neighbours a pixel exceeds -> ordering
    only, hence gain-invariant. On a horizontal ramp every interior pixel beats
    its 3 left neighbours out of 8 (=3/8); the lone bright pixel beats all 8."""
    ramp = np.tile(np.linspace(0, 1, 20), (20, 1))         # value increases with column
    base = T.tf_rank_transform(ramp, 0.0, 0.0)             # radius 1 -> 8 neighbours
    gained = T.tf_rank_transform(0.5 * ramp, 0.0, 0.0)
    assert np.array_equal(base, gained)                    # gain-invariant
    interior = base[5:15, 5:15]
    assert np.allclose(interior, 3.0 / 8.0)                # 3 of 8 neighbours smaller
    spike = np.zeros((21, 21))
    spike[10, 10] = 1.0
    rspike = T.tf_rank_transform(spike, 0.0, 0.0)
    assert rspike[10, 10] == 1.0                           # brightest pixel: rank 1
