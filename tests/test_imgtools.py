"""Ground-truth + contract tests for backends_imgtools.py (registry cluster it_).

Does NOT import ops.py. It drives the module's ``build()`` through a tiny ``_Op``
stub for the universal functional gate, and calls each module-level operator
directly to prove it implements the genuine algorithm its HALCON name promises.
"""
from __future__ import annotations

import numpy as np

import backends_imgtools as I


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
    assert len(OPS) == 11
    names = [o.name for o in OPS]
    assert len(set(names)) == len(names)
    for o in OPS:
        assert o.name.startswith("it_")
        assert o.in_sort == "image" and o.out_sort == "image"
        assert " " not in o.halcon                       # may be "" (it_full_domain = no-op)
    assert {o.name for o in OPS if not o.halcon} == {"it_full_domain"}


def test_halcon_names_are_the_assigned_real_operators():
    got = {o.name: o.halcon for o in OPS}
    assert got == {
        "it_add_image_border": "add_image_border",
        "it_crop_part": "crop_part",
        "it_crop_rectangle1": "crop_rectangle1",
        "it_bit_lshift": "bit_lshift",
        "it_bit_rshift": "bit_rshift",
        "it_bit_mask": "bit_mask",
        "it_convert_image_type": "convert_image_type",
        "it_change_format": "change_format",
        "it_region_to_bin": "region_to_bin",
        "it_full_domain": "",  # identity no-op on a full-domain array -> no coverage claim
        "it_crop_domain": "crop_domain",
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
                # every op preserves HxW on the (square) canonical bank
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
def test_add_image_border_is_reflect_pad_fitted_back():
    """The op is exactly reflect-pad(width w=1+round(a*6)) then bilinear-resize
    back to HxW; it is not the identity and it pulls mirrored edge content in."""
    rng = np.random.default_rng(1)
    x = np.clip(rng.random((40, 44)), 0, 1)
    a = 0.6
    w = 1 + int(round(a * 6))
    ref = I._resize(np.pad(x, w, mode="reflect"), 40, 44)
    out = I.it_add_image_border(x, a, 0.0)
    assert out.shape == x.shape
    assert np.allclose(out, np.clip(ref, 0, 1))     # genuine reflect-pad+fit
    assert not np.allclose(out, x)                   # a real border was added
    # reflection (not zero) border: a constant image survives reflect-pad+resize,
    # whereas a zero-padded border would darken the edges.
    ones = np.ones((30, 30))
    assert np.allclose(I.it_add_image_border(ones, 0.5, 0.0), 1.0)
    zero_ref = I._resize(np.pad(ones, 1 + int(round(0.5 * 6)), mode="constant"), 30, 30)
    assert zero_ref[0, 0] < 0.99                      # a zero border WOULD darken the edge


def test_crop_part_zooms_center_preserved_corners_change():
    """A radial bump: crop_part preserves the (plateau) centre and brightens the
    corners because it zooms in on the centre."""
    n = 41
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    r2 = (xx - n // 2) ** 2 + (yy - n // 2) ** 2
    img = np.exp(-r2 / 200.0)                         # 1 at centre, ~0 at corners
    out = I.it_crop_part(img, 0.5, 0.0)
    assert out.shape == img.shape
    assert abs(out[n // 2, n // 2] - img[n // 2, n // 2]) < 1e-2   # centre preserved
    assert out[0, 0] > img[0, 0] + 0.05                            # corner brightened
    assert out[-1, -1] > img[-1, -1] + 0.05
    # smaller kept-fraction => stronger zoom => even brighter corner
    strong = I.it_crop_part(img, 0.2, 0.0)
    assert strong[0, 0] > out[0, 0]


def test_crop_rectangle1_identity_at_zero_and_zoom_otherwise():
    n = 41
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    img = np.exp(-(((xx - n // 2) ** 2 + (yy - n // 2) ** 2) / 200.0))
    ident = I.it_crop_rectangle1(img, 0.0, 0.0)
    assert np.allclose(ident, img)                   # a=0 keeps the full rectangle
    zoom = I.it_crop_rectangle1(img, 0.3, 0.0)
    assert zoom[0, 0] > img[0, 0] + 0.05             # margins cropped -> zoom-in
    assert abs(zoom[n // 2, n // 2] - img[n // 2, n // 2]) < 1e-3


def test_bit_lshift_matches_masked_left_shift():
    ramp = (np.arange(256, dtype=np.float64) / 255.0).reshape(1, 256)
    for a in (0.0, 0.3, 0.6, 1.0):
        shift = int(round(a * 7))
        q = np.round(ramp * 255).astype(np.uint16)
        exp = ((np.left_shift(q, shift) & 0xFF).astype(np.float64) / 255.0)
        assert np.array_equal(I.it_bit_lshift(ramp, a, 0.0), exp)
    # a concrete value: 0x01 << 1 == 0x02
    one = np.array([[1.0 / 255.0]])
    assert np.isclose(I.it_bit_lshift(one, 1.0 / 7.0, 0.0)[0, 0], 2.0 / 255.0)


def test_bit_rshift_of_ramp_is_coarser():
    ramp = (np.arange(256, dtype=np.float64) / 255.0).reshape(1, 256)
    sharp = I.it_bit_rshift(ramp, 0.0, 0.0)          # shift 0 -> identity
    coarse = I.it_bit_rshift(ramp, 0.6, 0.0)         # shift round(4.2)=4
    assert np.array_equal(sharp, ramp)
    assert len(np.unique(coarse)) < len(np.unique(sharp))   # fewer levels
    assert coarse.max() <= sharp.max()                      # values shrink (darker)
    # exact: 255 >> 4 == 15
    q = np.round(ramp * 255).astype(np.uint16)
    assert np.array_equal(coarse, np.right_shift(q, 4).astype(np.float64) / 255.0)
    assert np.all(np.diff(coarse[0]) >= -1e-12)             # still monotone


def test_bit_mask_matches_bitwise_and():
    vals = np.array([[0, 64, 128, 200, 255]], dtype=np.float64) / 255.0
    a = 0.5
    mask = int(round(a * 255)) & 0xFF                # 128
    q = np.round(vals * 255).astype(np.uint16)
    exp = np.bitwise_and(q, mask).astype(np.float64) / 255.0
    assert np.array_equal(I.it_bit_mask(vals, a, 0.0), exp)
    # AND with 128 keeps only the top bit: 200(0xC8)&128 == 128, 64&128 == 0
    assert np.isclose(I.it_bit_mask(np.array([[200 / 255.0]]), a, 0.0)[0, 0], 128 / 255.0)
    assert np.isclose(I.it_bit_mask(np.array([[64 / 255.0]]), a, 0.0)[0, 0], 0.0)


def test_convert_image_type_reduces_unique_levels():
    ramp = (np.arange(256, dtype=np.float64) / 255.0).reshape(1, 256)
    assert len(np.unique(ramp)) == 256
    for a in (0.0, 0.02, 0.2):
        levels = max(2, min(256, int(round(2 + a * 254))))
        out = I.it_convert_image_type(ramp, a, 0.0)
        assert len(np.unique(out)) <= levels
        assert len(np.unique(out)) < 256              # genuinely reduced
        # exact quantiser reconstruction
        exp = np.round(ramp * (levels - 1)) / (levels - 1)
        assert np.allclose(out, exp)
    # more levels (higher a) => finer quantisation
    assert len(np.unique(I.it_convert_image_type(ramp, 0.5, 0.0))) > \
        len(np.unique(I.it_convert_image_type(ramp, 0.02, 0.0)))


def test_change_format_identity_on_square_crops_pads_on_nonsquare():
    sq = np.random.default_rng(2).random((20, 20))
    assert np.array_equal(I.it_change_format(sq, 0.3, 0.4), np.clip(sq, 0, 1))  # square -> identity
    rect = np.random.default_rng(3).random((20, 40))
    out = I.it_change_format(rect, 0.3, 0.4)
    assert out.shape == (40, 40)                      # square of the max dimension
    assert np.allclose(out[:20, :40], np.clip(rect, 0, 1))   # original at the origin
    assert np.all(out[20:, :] == 0.0)                 # expanded domain is zero-filled


def test_region_to_bin_produces_two_gray_levels():
    n = 30
    xx = (np.mgrid[0:n, 0:n][1] / (n - 1)).astype(float)   # left->right ramp 0..1
    a, b = 0.5, 0.85
    lo, hi = 0.5 - 0.5 * b, 0.5 + 0.5 * b
    out = I.it_region_to_bin(xx, a, b)
    assert set(np.unique(out).tolist()) == {lo, hi}   # exactly two gray levels
    assert np.all(out[xx > a] == hi)                  # foreground = high gray
    assert np.all(out[xx <= a] == lo)                 # background = low gray
    # b widens the gap between the two levels
    out2 = I.it_region_to_bin(xx, a, 0.2)
    assert (np.unique(out2).max() - np.unique(out2).min()) < (hi - lo)


def test_full_domain_is_identity():
    rng = np.random.default_rng(4)
    for shp in [(20, 20), (17, 33), (1, 1)]:
        x = np.clip(rng.random(shp), 0, 1)
        out = I.it_full_domain(x, 0.3, 0.7)
        assert out.shape == x.shape                   # full extent kept
        assert np.array_equal(out, x)                 # gray values unchanged


def test_crop_domain_zeroes_the_border_keeps_center():
    n = 40
    img = np.full((n, n), 0.8)
    out = I.it_crop_domain(img, 0.5, 0.0)             # keep central 20x20
    assert out[n // 2, n // 2] == 0.8                 # centre inside the domain
    assert out[0, 0] == 0.0 and out[-1, -1] == 0.0    # border outside -> zeroed
    assert out[0, :].sum() == 0.0 and out[:, 0].sum() == 0.0
    kept = (out > 0).sum()
    assert 0 < kept < n * n                           # a strict sub-window survives
    # larger a keeps more of the image
    wide = I.it_crop_domain(img, 0.9, 0.0)
    assert (wide > 0).sum() > kept
