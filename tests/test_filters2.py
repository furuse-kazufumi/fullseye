"""Ground-truth + contract tests for backends_filters2.py (registry cluster f2_).

Does NOT import ops.py. It drives the module's ``build()`` through a tiny ``_Op``
stub for the universal functional gate, and calls each module-level operator
directly to prove it implements the genuine algorithm its HALCON name promises.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

import backends_filters2 as F


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


OPS = F.build(_Op, "image", "region", "feature", "contour", _norm, _binm)
KNOBS = [(0.3, 0.4), (0.6, 0.7), (0.15, 0.85)]

_N = 48


def _image_bank():
    yy, xx = np.mgrid[0:_N, 0:_N].astype(np.float64)
    grad = xx / (_N - 1)
    disk = ((yy - _N * 0.35) ** 2 + (xx - _N * 0.4) ** 2) < (_N * 0.18) ** 2
    rng = np.random.default_rng(20260812)
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
    assert len(OPS) == 9
    names = [o.name for o in OPS]
    assert len(set(names)) == len(names)
    for o in OPS:
        assert o.name.startswith("f2_")
        assert o.in_sort == "image" and o.out_sort == "image"
        assert o.halcon and " " not in o.halcon


def test_halcon_names_are_the_assigned_real_operators():
    got = {o.name: o.halcon for o in OPS}
    assert got == {
        "f2_shock": "shock_filter",
        "f2_gray_skeleton": "gray_skeleton",
        "f2_lut_trans": "lut_trans",
        "f2_topographic": "topographic_sketch",
        "f2_expand_domain": "expand_domain_gray",
        "f2_symmetry": "symmetry",
        "f2_gauss_pyramid": "gen_gauss_pyramid",
        "f2_gray_inside": "gray_inside",
        "f2_bit_slice": "bit_slice",
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
                # determinism
                again = op.fn(np.array(iv, copy=True), a, b)
                assert np.array_equal(out, again), tag


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
def test_shock_sharpens_blurred_step():
    """shock_filter must steepen a blurred edge (its defining behaviour)."""
    step = np.zeros((32, 40))
    step[:, 20:] = 1.0
    blur = ndimage.gaussian_filter(step, 2.5)
    sh = F.f2_shock(blur, 0.9, 0.0)
    g_blur = np.abs(np.diff(blur, axis=1)).max()
    g_shock = np.abs(np.diff(sh, axis=1)).max()
    assert g_shock > 3.0 * g_blur          # blurred edge collapses to a near-step
    # the transition band (0.2<val<0.8) is narrower after shocking
    band_blur = int(((blur > 0.2) & (blur < 0.8)).sum())
    band_shock = int(((sh > 0.2) & (sh < 0.8)).sum())
    assert band_shock < band_blur


def test_gray_skeleton_thins_thick_bar_and_keeps_gray():
    """A 9-px-thick bright bar collapses to a ~1-px ridge carrying its gray value."""
    img = np.zeros((40, 40))
    img[16:25, 5:35] = 0.8
    sk = F.f2_gray_skeleton(img, 0.3, 0.0)
    assert sk.sum() > 0                                   # a ridge exists
    per_col = (sk[:, 5:35] > 0).sum(axis=0)
    assert per_col.mean() < 2.0                           # thinned from 9 rows
    ridge_vals = sk[sk > 0]
    assert np.allclose(ridge_vals, 0.8)                   # gray value preserved
    # skeleton stays inside the original bright region
    assert (sk[img == 0] == 0).all()


def test_lut_trans_is_a_monotone_lookup_with_contrast_gain():
    ramp = np.linspace(0, 1, 256).reshape(1, 256)
    out = F.f2_lut_trans(ramp, 0.7, 0.4)[0]
    # rebuild the table the op uses and confirm it is a genuine LUT lookup
    gain, pivot = 1.0 + 12.0 * 0.7, 0.15 + 0.70 * 0.4
    t = np.linspace(0, 1, 256)
    raw = 1.0 / (1.0 + np.exp(-gain * (t - pivot)))
    lut = (raw - raw[0]) / (raw[-1] - raw[0])
    idx = np.clip(np.round(ramp[0] * 255), 0, 255).astype(int)
    assert np.allclose(out, lut[idx])
    # monotone non-decreasing and full-range
    assert np.all(np.diff(out) >= -1e-9)
    assert out.min() <= 1e-6 and out.max() >= 1 - 1e-6
    # higher a => higher mid-slope (more contrast) than a gentle curve
    soft = F.f2_lut_trans(ramp, 0.05, 0.4)[0]
    mid = slice(120, 136)
    assert np.mean(np.diff(out[mid])) > np.mean(np.diff(soft[mid]))


def test_topographic_sketch_labels_peak_pit_and_flat():
    """Haralick classification: a Gaussian bump center is a peak, a Gaussian dip
    center is a pit, flat background is flat — distinct topographic classes."""
    n = 41
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    bump = np.exp(-(((xx - 12) ** 2 + (yy - 12) ** 2) / 18.0))
    dip = -np.exp(-(((xx - 30) ** 2 + (yy - 30) ** 2) / 18.0))
    surf = np.clip(0.5 + 0.45 * bump + 0.45 * dip, 0, 1)
    code = F.f2_topographic(surf, 0.3, 0.4)
    assert code[12, 12] == 1.0            # peak code
    assert code[30, 30] == 0.14           # pit code
    assert code[2, 2] == 0.0              # flat background
    assert code[12, 12] > code[30, 30] > code[2, 2]


def test_expand_domain_grows_border_by_width():
    im = np.zeros((30, 30))
    im[12:18, 12:18] = 0.7                      # domain block
    ex = F.f2_expand_domain(im, 0.3, 0.0)       # a=0.3 -> width = 1+round(1.8)=3
    assert ex[11, 15] == 0.7                     # 1 px outside -> filled
    assert ex[9, 15] == 0.7                      # 3 px outside -> filled (within width)
    assert ex[8, 15] == 0.0                      # 4 px outside -> beyond width, still 0
    assert ex[15, 15] == 0.7                     # interior untouched
    # a=0 gives the narrowest margin; wider a reaches further out
    wide = F.f2_expand_domain(im, 1.0, 0.0)
    assert (wide > 0).sum() > (ex > 0).sum()


def test_symmetry_low_on_reflection_axis():
    """A V-shape |j - c| is left-right symmetric about column c: the response is
    ~0 on that axis and clearly larger on the asymmetric linear flanks."""
    n = 41
    col = np.abs(np.arange(n) - 20).astype(float)
    vimg = np.tile(col / col.max(), (20, 1))
    sym = F.f2_symmetry(vimg, 0.6, 0.0)
    assert sym[:, 20].mean() < 1e-6                  # symmetry axis
    assert sym[:, 5].mean() > 0.5                    # asymmetric flank
    # a constant image is perfectly symmetric everywhere
    assert np.allclose(F.f2_symmetry(np.full((10, 10), 0.5), 0.6, 0.0), 0.0)


def test_gauss_pyramid_attenuates_high_frequency_by_level():
    n = 48
    yy, xx = np.mgrid[0:n, 0:n]
    chk = (((xx // 4) + (yy // 4)) % 2).astype(float)     # period-8 checker
    l1 = F.f2_gauss_pyramid(chk, 0.0, 0.0)
    l4 = F.f2_gauss_pyramid(chk, 1.0, 0.0)
    assert l1.shape == chk.shape and l4.shape == chk.shape  # HxW preserved
    assert l1.var() < chk.var()                             # already low-passed
    assert l4.var() < l1.var()                              # deeper level = more blur
    # odd, non-power-of-two size keeps its shape too
    odd = np.random.default_rng(0).random((45, 37))
    assert F.f2_gauss_pyramid(odd, 0.6, 0.0).shape == (45, 37)


def test_gray_inside_fills_enclosed_hole_only():
    """Lowest gray value on a path to the border == grayscale hole-fill: an
    enclosed dark basin is raised to its surrounding wall; a border-connected
    dark region stays dark. Fill depth is bounded by a."""
    im = np.full((30, 30), 0.8)
    im[13:17, 13:17] = 0.1              # enclosed dark hole (interior)
    im[0:5, 0:2] = 0.1                  # dark region touching the border
    full = F.f2_gray_inside(im, 1.0, 0.0)
    assert abs(full[15, 15] - 0.8) < 1e-6      # enclosed hole filled to the wall
    assert abs(full[2, 0] - 0.1) < 1e-6        # border-connected dark stays dark
    assert np.allclose(full[im == 0.8], 0.8)   # bright background unchanged
    # shallow fill depth (a~0) cannot raise a 0.7-deep hole to the wall
    shallow = F.f2_gray_inside(im, 0.02, 0.0)
    assert shallow[15, 15] < 0.3


def test_bit_slice_extracts_exact_periodic_bit_plane():
    ramp = (np.arange(256, dtype=np.float64) / 255.0).reshape(1, 256)
    q = np.round(ramp[0] * 255).astype(int)
    # a maps to plane p = round(a*7); each plane must equal (q>>p)&1 exactly
    for a in (0.0, 1 / 7, 2 / 7, 4 / 7, 1.0):
        p = int(round(a * 7))
        bit = F.f2_bit_slice(ramp, a, 0.0)[0]
        assert np.array_equal(bit.astype(int), (q >> p) & 1)
    # plane 0 (LSB) toggles every step -> 255 transitions on a full 0..255 ramp
    lsb = F.f2_bit_slice(ramp, 0.0, 0.0)[0]
    assert int(np.abs(np.diff(lsb)).sum()) == 255
    # a higher plane is coarser: strictly fewer transitions (genuine periodicity)
    msb2 = F.f2_bit_slice(ramp, 2 / 7, 0.0)[0]
    assert int(np.abs(np.diff(msb2)).sum()) < 255
