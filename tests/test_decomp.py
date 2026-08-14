"""Ground-truth + contract tests for backends_decomp.py (registry cluster dc_).

Does NOT import ops.py. It drives the module's ``build()`` through a tiny ``_Op``
stub for the universal functional gate, and calls each module-level operator
directly to prove it implements the genuine decomposition its name promises.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

import backends_decomp as D


# --------------------------------------------------------------------------- #
# stub registry + helpers (mirror ops.Op's positional construction)           #
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


OPS = D.build(_Op, "image", "region", "feature", "contour", _norm, _binm)
KNOBS = [(0.3, 0.4), (0.6, 0.7), (0.15, 0.85)]

_N = 48


def _image_bank():
    yy, xx = np.mgrid[0:_N, 0:_N].astype(np.float64)
    grad = xx / (_N - 1)
    disk = ((yy - _N * 0.35) ** 2 + (xx - _N * 0.4) ** 2) < (_N * 0.18) ** 2
    rng = np.random.default_rng(20260814)
    normal = np.clip(0.35 * grad + 0.4 * disk + 0.03 * rng.standard_normal((_N, _N)), 0, 1)
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
# structural sanity                                                            #
# --------------------------------------------------------------------------- #
def test_registry_shape_and_unique_names():
    assert len(OPS) == 7
    names = [o.name for o in OPS]
    assert len(set(names)) == len(names)
    for o in OPS:
        assert o.name.startswith("dc_")
        assert o.in_sort == "image" and o.out_sort == "image"


def test_all_halcon_fields_are_empty_new_capability():
    # None of these reproduce a specific HALCON operator -> honest empty claim.
    assert all(o.halcon == "" for o in OPS)


# --------------------------------------------------------------------------- #
# FUNCTIONAL GATE: every op, every canonical input, every knob pair            #
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
                assert np.array_equal(out, again), tag       # deterministic


# --------------------------------------------------------------------------- #
# GROUND TRUTH per operator                                                    #
# --------------------------------------------------------------------------- #
def _structure_texture_image():
    yy, xx = np.mgrid[0:_N, 0:_N] / (_N - 1)
    ramp = 0.3 + 0.4 * xx                                    # smooth structure
    tex = 0.05 * np.sin(2 * np.pi * 6 * xx) * np.sin(2 * np.pi * 6 * yy)
    return np.clip(ramp + tex, 0, 1), ramp, tex


def test_structure_texture_and_residual_reconstruct_input():
    """structure + (texture - 0.5) == input, and the residual IS the texture."""
    img, ramp, tex = _structure_texture_image()
    struct = D.dc_structure_texture(img, 0.3, 0.0)
    texture = D.dc_texture_residual(img, 0.3, 0.0)
    # exact reconstruction (small texture -> no clipping)
    recon = struct + (texture - 0.5)
    assert np.max(np.abs(recon - img)) < 1e-9
    # the structure layer is smoother than the input (texture removed)
    struct_grad = np.abs(np.diff(struct, axis=1)).mean()
    img_grad = np.abs(np.diff(img, axis=1)).mean()
    assert struct_grad < img_grad
    # the residual layer genuinely carries the injected texture
    resid = texture - 0.5
    assert np.corrcoef(resid.ravel(), tex.ravel())[0, 1] > 0.85
    # and the structure retains almost none of the fine texture
    assert np.corrcoef((struct - ramp).ravel(), tex.ravel())[0, 1] < 0.5


def test_structure_smoothness_increases_with_a():
    img, _, _ = _structure_texture_image()
    low = D.dc_structure_texture(img, 0.1, 0.0)
    high = D.dc_structure_texture(img, 0.9, 0.0)
    tv_low = np.abs(np.diff(low, axis=1)).sum() + np.abs(np.diff(low, axis=0)).sum()
    tv_high = np.abs(np.diff(high, axis=1)).sum() + np.abs(np.diff(high, axis=0)).sum()
    assert tv_high <= tv_low + 1e-6                          # more smoothing


def _rpca_defect_image():
    n = 40
    xx = np.mgrid[0:n, 0:n][1] / (n - 1)
    bg = 0.3 + 0.5 * xx                                      # smooth low-rank background
    m = np.clip(bg.copy(), 0, 1)
    loc = (12, 28)
    m[loc] = np.clip(m[loc] + 0.6, 0, 1)                     # small bright defect
    return m, bg, loc


def test_rpca_sparse_localizes_a_bright_defect():
    m, _bg, loc = _rpca_defect_image()
    sparse = D.dc_rpca_sparse(m, 0.3, 0.0)                   # centred at 0.5
    dev = np.abs(sparse - 0.5)
    peak = np.unravel_index(int(np.argmax(dev)), dev.shape)
    assert peak == loc                                       # defect pixel is the peak
    assert sparse[loc] > 0.5 + 0.1                           # bright anomaly
    # sparse: only a handful of pixels deviate meaningfully
    assert int((dev > 0.05).sum()) <= 5
    # the background is left almost untouched (near 0.5)
    bg_dev = dev.copy()
    bg_dev[loc] = 0.0
    assert bg_dev.max() < 0.05


def test_rpca_lowrank_recovers_background_not_defect():
    m, bg, loc = _rpca_defect_image()
    low = D.dc_rpca_lowrank(m, 0.3, 0.0)
    # low-rank: few significant singular values
    sv = np.linalg.svd(low, compute_uv=False)
    assert int((sv > 1e-3 * sv[0]).sum()) <= 3
    # L matches the smooth background and does NOT absorb the bright defect
    assert np.max(np.abs(low - bg)) < 0.05
    assert abs(low[loc] - bg[loc]) < 0.1
    assert low[loc] < m[loc] - 0.2


def test_retinex_flattens_illumination_gradient():
    n = 48
    xx = np.mgrid[0:n, 0:n][1] / (n - 1)
    ramp = np.clip(0.3 + 0.6 * xx, 0, 1)                     # pure illumination gradient
    out = D.dc_retinex(ramp, 0.7, 0.4)
    assert out.var() < 0.15 * ramp.var()                    # illumination removed
    # the flattening holds across scales (a smooth ramp has no reflectance detail,
    # so every scale collapses it toward mid-gray)
    small_scale = D.dc_retinex(ramp, 0.05, 0.4)
    assert small_scale.var() < 0.15 * ramp.var()


def test_retinex_recovers_reflectance_under_multiplicative_illumination():
    """Two identical reflectance patches under different illumination map to
    similar retinex values (illumination invariance)."""
    n = 48
    img = np.full((n, n), 0.5)
    img[10:18, 6:14] = 0.75                                  # a reflectance patch (left, bright light)
    img[10:18, 34:42] = 0.75                                 # same patch (right)
    xx = np.mgrid[0:n, 0:n][1] / (n - 1)
    lit = np.clip(img * (0.4 + 0.6 * xx), 0, 1)              # multiplicative illumination ramp
    out = D.dc_retinex(lit, 0.6, 0.4)
    left = out[10:18, 6:14].mean()
    right = out[10:18, 34:42].mean()
    # raw (lit) patches differ a lot; retinex brings them closer together
    raw_diff = abs(lit[10:18, 6:14].mean() - lit[10:18, 34:42].mean())
    assert abs(left - right) < raw_diff


def test_local_contrast_norm_zero_means_locally():
    n = 48
    xx = np.mgrid[0:n, 0:n][1] / (n - 1)
    ramp = 0.2 + 0.6 * xx                                    # smooth low-frequency signal
    out = D.dc_local_contrast_norm(ramp, 0.3, 0.4)
    w = D._win(0.3)
    # reconstruct the mean-subtracted high-pass the op removes and confirm its
    # local mean is ~0 (DC removed).  For a linear ramp this is ~0 in the interior.
    mu = ndimage.uniform_filter(ramp, size=w, mode="reflect")
    hp = ramp - mu
    inner = slice(w, n - w)
    assert np.max(np.abs(hp[inner, inner])) < 1e-9
    # output is centred at 0.5 where the input is locally flat (the ramp interior)
    assert np.max(np.abs(out[inner, inner] - 0.5)) < 1e-6


def test_local_contrast_norm_is_genuine_and_equalizes_contrast():
    """Verify the exact (I-mean)/(std) computation, and that a low-contrast and a
    high-contrast textured region get comparable output contrast."""
    rng = np.random.default_rng(7)
    n = 64
    img = np.full((n, n), 0.5)
    img[8:24, 8:24] += 0.03 * rng.standard_normal((16, 16))   # low-contrast texture
    img[40:56, 40:56] += 0.20 * rng.standard_normal((16, 16))  # high-contrast texture
    img = np.clip(img, 0, 1)
    a, b = 0.3, 0.4
    out = D.dc_local_contrast_norm(img, a, b)
    # exact genuine reconstruction of the op formula
    w = D._win(a)
    mu = ndimage.uniform_filter(img, size=w, mode="reflect")
    var = ndimage.uniform_filter(img * img, size=w, mode="reflect") - mu * mu
    sd = np.sqrt(np.maximum(var, 0.0))
    floor = 0.02 + 0.18 * b
    expect = np.clip(0.5 + 0.25 * (img - mu) / (sd + floor), 0, 1)
    assert np.allclose(out, expect)
    # contrast equalization: input std ratio >> output std ratio
    lo_in = img[10:22, 10:22].std()
    hi_in = img[42:54, 42:54].std()
    lo_out = out[10:22, 10:22].std()
    hi_out = out[42:54, 42:54].std()
    assert hi_in / (lo_in + 1e-9) > 3.0                      # very different in
    assert hi_out / (lo_out + 1e-9) < hi_in / (lo_in + 1e-9)  # pulled together


def test_homomorphic_flattens_multiplicative_illumination():
    n = 48
    xx = np.mgrid[0:n, 0:n][1] / (n - 1)
    ramp = np.clip(0.3 + 0.6 * xx, 0, 1)                     # smooth illumination
    out = D.dc_homomorphic(ramp, 0.3, 0.4)

    def low_fraction(x):
        blur = ndimage.gaussian_filter(x, n * 0.15, mode="reflect")
        return blur.var() / (x.var() + 1e-12)

    # homomorphic high-emphasis suppresses low-frequency (illumination) energy
    assert low_fraction(out) < low_fraction(ramp)


def test_homomorphic_preserves_high_frequency_detail():
    n = 48
    yy, xx = np.mgrid[0:n, 0:n] / (n - 1)
    detail = 0.1 * np.sin(2 * np.pi * 8 * xx) * np.sin(2 * np.pi * 8 * yy)
    img = np.clip(0.3 + 0.5 * xx + detail, 0, 1)             # illumination + fine detail
    out = D.dc_homomorphic(img, 0.3, 0.7)
    # the fine detail survives (high correlation with the injected pattern)
    hp = out - ndimage.gaussian_filter(out, 3.0, mode="reflect")
    assert np.corrcoef(hp.ravel(), detail.ravel())[0, 1] > 0.5


def test_ops_fail_soft_on_degenerate_inputs():
    degenerate = [
        np.zeros((5, 5)),
        np.ones((5, 5)),
        np.full((5, 5), 0.42),
        np.zeros((1, 1)),
        np.array([[0.2, 0.8]]),
        np.full((3, 3), np.nan),
    ]
    for op in OPS:
        for iv in degenerate:
            out = op.fn(np.array(iv, copy=True), 0.5, 0.5)
            assert np.isfinite(out).all()
            assert out.min() >= -1e-9 and out.max() <= 1 + 1e-9
