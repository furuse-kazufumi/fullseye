"""Ground-truth + contract tests for backends_tomo.py (registry cluster tm_).

Does NOT import ops.py. It drives ``build()`` through a tiny ``_Op`` stub for the
universal functional gate, and calls each module-level operator directly to prove
it implements the genuine tomographic algorithm its name promises:

  * a disk phantom forward-projected by tm_radon_forward and reconstructed by
    tm_fbp_reconstruct comes back as a disk whose correlation with the phantom
    beats plain unfiltered back-projection (the whole point of the ramp filter);
  * SART improves as its iteration count grows;
  * sinogram_denoise removes per-angle noise along the angle direction.

Everything is required to stay finite and inside [0,1].
"""
from __future__ import annotations

import numpy as np

import backends_tomo as T


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

_N = 56


def _disk(n, cx=None, cy=None, r=None):
    cy = n / 2 if cy is None else cy
    cx = n / 2 if cx is None else cx
    r = n * 0.22 if r is None else r
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    return (((yy - cy) ** 2 + (xx - cx) ** 2) < r ** 2).astype(np.float64)


def _image_bank():
    _yy, xx = np.mgrid[0:_N, 0:_N].astype(np.float64)
    grad = xx / (_N - 1)
    disk = _disk(_N)
    rng = np.random.default_rng(20260814)
    normal = np.clip(0.35 * grad + 0.45 * disk + 0.03 * rng.standard_normal((_N, _N)), 0, 1)
    single = np.zeros((_N, _N))
    single[_N // 2, _N // 2] = 1.0
    return {
        "normal": normal,
        "disk": disk,
        "const0": np.zeros((_N, _N)),
        "const1": np.ones((_N, _N)),
        "const_mid": np.full((_N, _N), 0.42),
        "single_bright": single,
    }


def _corr(a, b):
    a = np.asarray(a, np.float64).ravel()
    b = np.asarray(b, np.float64).ravel()
    a = a - a.mean()
    b = b - b.mean()
    d = np.linalg.norm(a) * np.linalg.norm(b)
    return float((a @ b) / d) if d > 1e-12 else 0.0


# --------------------------------------------------------------------------- #
# structural sanity                                                           #
# --------------------------------------------------------------------------- #
def test_registry_shape_and_names():
    assert len(OPS) == 5
    names = [o.name for o in OPS]
    assert len(set(names)) == len(names)
    for o in OPS:
        assert o.name.startswith("tm_")
        assert o.in_sort == "image" and o.out_sort == "image"
        assert o.halcon == ""                     # no HALCON analog -> no coverage claim


def test_halcon_all_empty_new_capability():
    got = {o.name: o.halcon for o in OPS}
    assert got == {
        "tm_radon_forward": "",
        "tm_fbp_reconstruct": "",
        "tm_sart_reconstruct": "",
        "tm_backproject_unfiltered": "",
        "tm_sinogram_denoise": "",
    }


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
                # determinism
                again = op.fn(np.array(iv, copy=True), a, b)
                assert np.array_equal(out, again), tag


def test_ops_never_raise_on_odd_input():
    odd = [
        np.zeros((1, 1)),
        np.ones((2, 3)),
        np.full((5, 5), np.nan),
        np.array([[np.inf, -np.inf], [0.0, 1.0]]),
        np.linspace(0, 1, 20).reshape(4, 5),   # non-square
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
def test_radon_forward_is_a_real_sinogram_not_identity():
    """Forward-projecting a disk yields a sinogram (angles x detector) that is
    NOT the input image, whose per-angle line-integral (row sum) is roughly
    constant -- the mass of a disk is the same seen from every angle."""
    n = _N
    disk = _disk(n)
    sino = T.tm_radon_forward(disk, 1.0, 1.0)          # dense, full 180 span
    assert sino.shape == disk.shape
    assert np.isfinite(sino).all()
    assert 0.0 - 1e-9 <= sino.min() and sino.max() <= 1.0 + 1e-9
    assert not np.allclose(sino, disk)                 # a genuine transform, not a copy
    # each projection sees the whole disk: the total per-angle signal is stable
    row_mass = sino.sum(axis=1)
    assert row_mass.std() / (row_mass.mean() + 1e-9) < 0.25
    # sparse (few angles) differs from dense -> a genuinely acquisition-dependent op
    sparse = T.tm_radon_forward(disk, 0.15, 1.0)
    assert not np.allclose(sparse, sino)


def test_fbp_recovers_disk_and_beats_unfiltered_backprojection():
    """The headline test: forward-project a disk, then filtered back-projection
    reconstructs a disk that correlates with the phantom far better than plain
    unfiltered back-projection does. Everything stays finite and in [0,1]."""
    n = _N
    disk = _disk(n)
    sino = T.tm_radon_forward(disk, 1.0, 1.0)          # matched angles, full span
    fbp = T.tm_fbp_reconstruct(sino, 0.5, 0.0)         # b<0.5 -> Ram-Lak
    bp = T.tm_backproject_unfiltered(sino, 0.5, 0.5)

    for r in (fbp, bp):
        assert r.shape == disk.shape
        assert np.isfinite(r).all()
        assert r.min() >= -1e-9 and r.max() <= 1.0 + 1e-9

    c_fbp = _corr(fbp, disk)
    c_bp = _corr(bp, disk)
    assert c_fbp > 0.85                                # FBP genuinely recovers the disk
    assert c_fbp > c_bp + 0.05                         # and clearly beats unfiltered BP
    # FBP reconstructs a compact bright core where the disk is, dark outside
    mask = _disk(n, r=n * 0.18) > 0.5
    outer = _disk(n, r=n * 0.30) < 0.5
    assert fbp[mask].mean() > fbp[outer].mean() + 0.2


def test_fbp_filter_selection_depends_on_b():
    """b < 0.5 selects the Ram-Lak filter, b >= 0.5 the Shepp-Logan filter; the
    two produce genuinely different reconstructions (Shepp-Logan is smoother)."""
    disk = _disk(_N)
    sino = T.tm_radon_forward(disk, 1.0, 1.0)
    ramlak = T.tm_fbp_reconstruct(sino, 0.5, 0.2)      # ramp
    shepp = T.tm_fbp_reconstruct(sino, 0.5, 0.8)       # shepp-logan
    assert not np.allclose(ramlak, shepp)              # b really switches the filter
    # both are valid disk reconstructions
    assert _corr(ramlak, disk) > 0.8
    assert _corr(shepp, disk) > 0.8


def test_backprojection_blurs_the_disk_edge_that_fbp_restores():
    """Unfiltered back-projection is a genuine low-pass: it smears the disk's
    boundary, so the image gradient AT THE TRUE EDGE is much weaker than FBP's,
    which restores that high-frequency edge via its ramp filter."""
    n = _N
    disk = _disk(n)
    sino = T.tm_radon_forward(disk, 1.0, 1.0)
    fbp = T.tm_fbp_reconstruct(sino, 0.5, 0.0)
    bp = T.tm_backproject_unfiltered(sino, 0.3, 0.6)

    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    rr = np.hypot(yy - n / 2, xx - n / 2)
    edge = (rr > n * 0.22 - 2) & (rr < n * 0.22 + 2)   # annulus at the disk boundary

    def _grad(x):
        gy, gx = np.gradient(x)
        return np.hypot(gy, gx)

    assert _grad(fbp)[edge].mean() > _grad(bp)[edge].mean() + 0.05   # FBP edge is sharper


def test_sart_improves_with_iterations_and_recovers_disk():
    """More SART sweeps (larger a) reconstruct the disk at least as well as fewer,
    and a multi-iteration SART genuinely correlates with the phantom."""
    disk = _disk(_N)
    sino = T.tm_radon_forward(disk, 1.0, 1.0)
    one = T.tm_sart_reconstruct(sino, 0.0, 0.5)        # ~1 iteration
    many = T.tm_sart_reconstruct(sino, 1.0, 0.5)       # ~5 iterations
    for r in (one, many):
        assert r.shape == disk.shape
        assert np.isfinite(r).all()
        assert r.min() >= -1e-9 and r.max() <= 1.0 + 1e-9
    assert _corr(many, disk) > 0.8                     # genuine reconstruction
    assert _corr(many, disk) >= _corr(one, disk) - 1e-6   # more sweeps do not hurt


def test_sinogram_denoise_smooths_along_angle_axis():
    """Adding per-angle noise to a clean sinogram and denoising along the angle
    direction moves the result closer to the clean sinogram; the low-a case
    barely touches it while high-a smooths strongly. Detector-axis structure is
    preserved (column means stay close)."""
    disk = _disk(_N)
    clean = T.tm_radon_forward(disk, 1.0, 1.0)
    rng = np.random.default_rng(7)
    noisy = np.clip(clean + 0.15 * rng.standard_normal(clean.shape), 0, 1)

    weak = T.tm_sinogram_denoise(noisy, 0.05, 0.0)
    strong = T.tm_sinogram_denoise(noisy, 0.9, 0.0)

    mse = lambda x: float(np.mean((x - clean) ** 2))
    assert mse(strong) < mse(noisy)                    # denoising genuinely helps
    assert mse(strong) < mse(weak)                     # more smoothing -> closer to clean
    # angle-direction smoothing keeps per-detector (column) means ~unchanged
    assert np.abs(noisy.mean(axis=0) - strong.mean(axis=0)).max() < 0.05
    # variance along the angle axis is reduced (the noise lived there)
    assert strong.var(axis=0).mean() < noisy.var(axis=0).mean()


def test_numpy_fallback_radon_and_fbp_are_genuine():
    """Exercise the NumPy fallback DIRECTLY (independent of scikit-image): its
    rotate-and-sum Radon + FFT-ramp back-projection must reconstruct the disk and
    beat its own unfiltered back-projection. Proves the fallback is a real
    algorithm, not a stub."""
    n = _N
    disk = _disk(n)
    thetas = T._thetas(n, 180.0)
    sino = T._radon_np(disk, thetas)                   # (angles, detector)
    assert sino.shape == (n, n)
    assert np.isfinite(sino).all()
    fbp = T._iradon_np(sino, thetas, "ramp")
    bp = T._iradon_np(sino, thetas, None)
    assert np.isfinite(fbp).all() and np.isfinite(bp).all()

    def nrm(x):
        x = x - x.min()
        m = x.max()
        return x / m if m > 1e-12 else x

    mask = _disk(n, r=n / 2 - 1) > 0.5
    c_fbp = _corr(nrm(fbp)[mask], disk[mask])
    c_bp = _corr(nrm(bp)[mask], disk[mask])
    assert c_fbp > 0.8
    assert c_fbp > c_bp + 0.03
