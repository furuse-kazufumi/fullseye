"""Ground-truth + contract tests for backends_inverse.py (registry cluster iv_).

Does NOT import ops.py. It drives the module's ``build()`` through a tiny ``_Op``
stub for the universal functional gate, and calls each module-level operator
directly to prove it implements the genuine inverse-problem algorithm it names:

  iv_richardson_lucy       RL deconvolution sharpens a Gaussian-blurred edge
  iv_wiener_deconv_spatial regularized Wiener inverse sharpens; b regularizes
  iv_unsharp_deblur        iterative unsharp masking sharpens monotonically in a
  iv_motion_deblur         narrows a horizontally motion-blurred bar
  iv_backproject_superres  raises high-frequency energy (sharpening-by-consistency)
  iv_gradient_inpaint      harmonic fill recovers a linear ramp; interior lap ~ 0
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

import backends_inverse as I


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


OPS = I.build(_Op, "image", "region", "feature", "contour", _norm, _binm)
KNOBS = [(0.3, 0.4), (0.6, 0.7), (0.15, 0.85)]

_N = 48


def _gmax_x(im):
    """Max absolute horizontal gradient — an edge-sharpness proxy."""
    return float(np.max(np.abs(np.gradient(im, axis=1))))


def _hf_energy(im):
    """Mean squared gradient magnitude — a high-frequency-energy proxy."""
    gy, gx = np.gradient(im)
    return float(np.mean(gx * gx + gy * gy))


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
        assert o.name.startswith("iv_")
        assert o.in_sort == "image" and o.out_sort == "image"


def test_all_halcon_claims_are_empty():
    # Every op is a new inverse-problem capability with no single uncovered
    # HALCON operator to reproduce -> no coverage claim.
    assert {o.name: o.halcon for o in OPS} == {
        "iv_richardson_lucy": "",
        "iv_wiener_deconv_spatial": "",
        "iv_unsharp_deblur": "",
        "iv_motion_deblur": "",
        "iv_backproject_superres": "",
        "iv_gradient_inpaint": "",
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
                # every op preserves HxW on the canonical bank
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
        np.array([[0.5]]),
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
def test_richardson_lucy_sharpens_blurred_edge():
    """RL deconvolution of an edge blurred by the op's OWN assumed Gaussian PSF
    increases the edge gradient back toward the true step (a genuine deblur)."""
    edge = np.where(np.mgrid[0:_N, 0:_N][1] < _N // 2, 0.2, 0.8).astype(np.float64)
    blur = ndimage.gaussian_filter(edge, I.RL_SIGMA, mode="reflect")
    rl = I.iv_richardson_lucy(blur, 0.6, 0.0)
    assert rl.shape == edge.shape
    assert np.isfinite(rl).all() and rl.min() >= 0 and rl.max() <= 1
    # sharper than the blurred input, still short of the ideal step
    assert _gmax_x(rl) > _gmax_x(blur) * 1.15
    assert _gmax_x(rl) <= _gmax_x(edge) + 1e-6
    # more iterations (larger a) sharpen at least as much
    rl_lo = I.iv_richardson_lucy(blur, 0.1, 0.0)
    assert _gmax_x(rl) >= _gmax_x(rl_lo) - 1e-9
    # a flat image is a fixed point of RL (nothing to deblur)
    flat = np.full((_N, _N), 0.5)
    assert np.allclose(I.iv_richardson_lucy(flat, 0.6, 0.0), 0.5, atol=1e-6)


def test_wiener_deconv_spatial_sharpens_and_b_regularizes():
    """The regularized Wiener inverse of an assumed Gaussian PSF sharpens a
    blurred edge, and a larger noise-ratio b yields a gentler (less sharp)
    restoration than a small b."""
    edge = np.where(np.mgrid[0:_N, 0:_N][1] < _N // 2, 0.2, 0.8).astype(np.float64)
    a = 0.6
    sigma = I._amt(a, 0.4, I.WIENER_SIGMA_MAX)
    blur = ndimage.gaussian_filter(edge, sigma, mode="reflect")
    aggressive = I.iv_wiener_deconv_spatial(blur, a, 0.03)
    gentle = I.iv_wiener_deconv_spatial(blur, a, 0.95)
    for out in (aggressive, gentle):
        assert out.shape == edge.shape
        assert np.isfinite(out).all() and out.min() >= 0 and out.max() <= 1
    # both sharpen the blurred edge
    assert _gmax_x(aggressive) > _gmax_x(blur) * 1.1
    assert _gmax_x(gentle) > _gmax_x(blur) * 1.02
    # small noise-ratio -> stronger (less regularized) deconvolution
    assert _gmax_x(aggressive) > _gmax_x(gentle)


def test_unsharp_deblur_sharpens_monotonically_in_a():
    """Iterative unsharp masking increases the edge gradient, and more iterations
    (larger a) produce a strictly sharper result."""
    edge = np.where(np.mgrid[0:_N, 0:_N][1] < _N // 2, 0.2, 0.8).astype(np.float64)
    blur = ndimage.gaussian_filter(edge, 1.0, mode="reflect")
    lo = I.iv_unsharp_deblur(blur, 0.15, 0.5)
    hi = I.iv_unsharp_deblur(blur, 0.9, 0.5)
    assert _gmax_x(lo) > _gmax_x(blur) * 1.05          # even one/few passes sharpen
    assert _gmax_x(hi) > _gmax_x(lo)                    # more passes -> sharper
    for out in (lo, hi):
        assert np.isfinite(out).all() and out.min() >= 0 and out.max() <= 1
    # a constant image is unchanged (no high-pass content to add)
    flat = np.full((_N, _N), 0.3)
    assert np.allclose(I.iv_unsharp_deblur(flat, 0.9, 0.7), 0.3, atol=1e-9)


def test_motion_deblur_narrows_horizontal_blur():
    """A vertical bar smeared HORIZONTALLY by the op's assumed motion PSF is
    narrowed back toward its original width by iv_motion_deblur (b=0 -> the
    horizontal blur direction the op assumes)."""
    bar = np.zeros((_N, _N), np.float64)
    bar[:, _N // 2 - 1:_N // 2 + 1] = 1.0              # 2-column vertical bar
    a = 0.6
    length = 3 + int(round(a * 10))
    psf = I._motion_psf(length, 0.0)                   # horizontal motion
    blurred = ndimage.convolve(bar, psf, mode="reflect")

    def width(profile):
        p = np.asarray(profile, np.float64)
        m = p.max()
        return int((p > 0.5 * m).sum()) if m > 1e-9 else 0

    deb = I.iv_motion_deblur(blurred, a, 0.0)
    row = _N // 2
    w_orig, w_blur, w_deb = width(bar[row]), width(blurred[row]), width(deb[row])
    assert w_blur > w_orig                              # blur widened the bar
    assert w_deb < w_blur                               # deblur narrowed it back
    assert w_deb <= w_orig + 1                          # close to the true width
    assert np.isfinite(deb).all() and deb.min() >= 0 and deb.max() <= 1


def test_backproject_superres_raises_high_frequency_energy():
    """Back-projection super-resolution boosts high-frequency energy relative to
    a softened input, and larger a/b do not reduce that boost (IBP converges)."""
    grid_c = np.mgrid[0:_N, 0:_N][1]
    grid_r = np.mgrid[0:_N, 0:_N][0]
    img = np.clip(0.5 + 0.25 * np.sin(grid_c * 1.3) + 0.25 * np.sin(grid_r * 1.1), 0, 1)
    soft = ndimage.gaussian_filter(img, 1.3, mode="reflect")
    sr_lo = I.iv_backproject_superres(soft, 0.2, 0.2)
    sr_hi = I.iv_backproject_superres(soft, 0.9, 1.0)
    assert _hf_energy(sr_lo) > _hf_energy(soft) * 1.1   # genuine sharpening
    assert _hf_energy(sr_hi) >= _hf_energy(sr_lo) - 1e-9
    # the knobs genuinely change the output (not a fixed constant)
    assert not np.allclose(sr_lo, sr_hi)
    for out in (sr_lo, sr_hi):
        assert out.shape == soft.shape
        assert np.isfinite(out).all() and out.min() >= 0 and out.max() <= 1


def test_gradient_inpaint_is_harmonic_and_recovers_a_ramp():
    """A horizontal linear ramp is a harmonic function (nabla^2 = 0). Corrupt a
    central window and iv_gradient_inpaint (Laplace fill) recovers the ramp there
    and leaves an interior with near-zero Laplacian."""
    ramp = np.tile(np.linspace(0.1, 0.9, _N), (_N, 1))
    corrupt = ramp.copy()
    lo, hi = int(_N * 0.35), int(_N * 0.65)
    corrupt[lo:hi, lo:hi] = 0.0                        # punch a hole
    filled = I.iv_gradient_inpaint(corrupt, 0.3, 0.0)
    assert filled.shape == ramp.shape
    assert np.isfinite(filled).all() and filled.min() >= 0 and filled.max() <= 1
    # the hole no longer holds the corrupt zeros; it recovers the linear ramp
    interior = (slice(lo + 3, hi - 3), slice(lo + 3, hi - 3))
    assert np.abs(filled[interior] - ramp[interior]).max() < 0.03
    assert np.abs(corrupt[interior]).max() < 1e-9      # was corrupted to 0
    # harmonic: interior Laplacian is ~0
    lap = (
        np.roll(filled, 1, 0) + np.roll(filled, -1, 0)
        + np.roll(filled, 1, 1) + np.roll(filled, -1, 1) - 4 * filled
    )
    assert np.abs(lap[interior]).max() < 5e-3
    # known pixels outside the window are left untouched
    assert np.allclose(filled[:lo - 1, :], ramp[:lo - 1, :], atol=1e-9)
