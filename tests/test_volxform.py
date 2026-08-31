"""Ground-truth tests for the 3-D geometric transforms (volxform.py).

Every convention the module docstring *pins* is machine-verified here:

  * resize uses cell semantics — an integer upscale maps input voxel ``i``
    exactly onto the output block ``[f*i, f*(i+1))`` (order=0, bit-exact);
  * rotation direction — ``vol_rotate(v, +90, axes=a)`` equals
    ``np.rot90(v, 1, axes=a)`` bit-for-bit (order=0, square in-plane shape),
    which fixes the "from the first axis toward the second" sign convention;
  * affine is *pull* — ``matrix = 2*I`` makes the object exactly **half**
    size (asserted voxel-by-voxel at order=0), so nobody can silently flip
    the module to push semantics without a red test.

Plus the fail-closed contracts: 3-D only, finite only, exact-integer order,
output-size cap *before* allocation.
"""
import numpy as np
import pytest

import volxform
from volxform import vol_affine, vol_resize, vol_rotate


# --------------------------------------------------------------------------- #
# vol_resize                                                                   #
# --------------------------------------------------------------------------- #
def test_resize_factor2_order0_maps_voxel_to_exact_block():
    """Cell semantics: input voxel (2, 3, 4) -> the 2x2x2 output block at
    (4, 6, 8) — nothing else lights up (bit-exact at order=0)."""
    v = np.zeros((8, 8, 8))
    v[2, 3, 4] = 1.0
    out = vol_resize(v, factor=2, order=0)
    assert out.shape == (16, 16, 16) and out.dtype == np.float64
    expected = np.zeros((16, 16, 16))
    expected[4:6, 6:8, 8:10] = 1.0
    assert np.array_equal(out, expected)


def test_resize_anisotropic_factor_tuple():
    v = np.zeros((8, 10, 12))
    v[1:3, 2:4, 3:5] = 1.0
    out = vol_resize(v, factor=(1, 2, 0.5), order=0)
    assert out.shape == (8, 20, 6)


def test_resize_shape_gives_exact_shape():
    v = np.random.default_rng(0).random((8, 10, 12))
    out = vol_resize(v, shape=(13, 7, 9), order=1)
    assert out.shape == (13, 7, 9)
    assert np.isfinite(out).all()


def test_resize_spacing_recalculated_by_hand():
    """(8,8,8) at spacing (2,1,1) mm, factor (1,2,2) -> (8,16,16) and the new
    spacing must be (2, 0.5, 0.5): physical extent per axis is invariant."""
    v = np.zeros((8, 8, 8))
    v[3, 3, 3] = 1.0
    out, new_sp = vol_resize(v, factor=(1, 2, 2), order=0, spacing=(2.0, 1.0, 1.0))
    assert out.shape == (8, 16, 16)
    assert new_sp == (2.0, 0.5, 0.5)
    # physical extent invariant, axis by axis
    for d_in, s_in, d_out, s_out in zip(v.shape, (2.0, 1.0, 1.0), out.shape, new_sp):
        assert d_in * s_in == pytest.approx(d_out * s_out, abs=0.0)


def test_resize_without_spacing_returns_bare_volume():
    out = vol_resize(np.zeros((4, 4, 4)), factor=2)
    assert isinstance(out, np.ndarray)          # not a (out, spacing) tuple


def test_resize_factor_and_shape_are_mutually_exclusive():
    v = np.zeros((4, 4, 4))
    with pytest.raises(ValueError, match="exactly one"):
        vol_resize(v, factor=2, shape=(8, 8, 8))
    with pytest.raises(ValueError, match="exactly one"):
        vol_resize(v)


def test_resize_output_cap_fires_before_allocation():
    """A hostile factor on a tiny input must be refused by the *output* cap."""
    v = np.zeros((16, 16, 16))
    with pytest.raises(ValueError, match="MAX_VOXELS"):
        vol_resize(v, factor=1000, order=0)     # 16000^3 voxels — never allocated
    with pytest.raises(ValueError, match="MAX_VOXELS"):
        vol_resize(v, shape=(4096, 4096, 4096))


def test_resize_bad_factor_rejected():
    v = np.zeros((4, 4, 4))
    for bad in (0, -1, (1, 2), (1, 2, np.nan), "x"):
        with pytest.raises(ValueError):
            vol_resize(v, factor=bad)


# --------------------------------------------------------------------------- #
# vol_rotate                                                                   #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("axes,shape", [((1, 2), (4, 6, 6)),
                                        ((0, 2), (6, 5, 6)),
                                        ((0, 1), (6, 6, 5))])
def test_rotate_90_equals_rot90_pins_direction(axes, shape):
    """+90 deg == np.rot90(k=+1, axes=axes) bit-for-bit at order=0. This is the
    sign convention: positive angle rotates from axes[0] toward axes[1]."""
    v = np.arange(np.prod(shape), dtype=np.float64).reshape(shape)  # asymmetric
    out = vol_rotate(v, 90, axes=axes, order=0, reshape=False)
    assert np.array_equal(out, np.rot90(v, 1, axes=axes))
    assert not np.array_equal(out, np.rot90(v, -1, axes=axes))      # sign matters


def test_rotate_four_quarters_identity():
    v = np.arange(4 * 6 * 6, dtype=np.float64).reshape(4, 6, 6)
    out = v
    for _ in range(4):
        out = vol_rotate(out, 90, axes=(1, 2), order=0, reshape=False)
    assert np.array_equal(out, v)


def test_rotate_360_is_identity():
    v = np.random.default_rng(1).random((5, 6, 6))
    out = vol_rotate(v, 360.0, axes=(1, 2), order=1, reshape=False)
    np.testing.assert_allclose(out, v, atol=1e-9)


def test_rotate_bad_axes_rejected():
    v = np.zeros((4, 4, 4))
    for bad in ((0, 0), (2, 1), (1, 0), (0, 3), (1,), "zy"):
        with pytest.raises(ValueError):
            vol_rotate(v, 45, axes=bad)


def test_rotate_reshape_grows_and_caps():
    v = np.ones((3, 10, 4))
    out = vol_rotate(v, 90, axes=(1, 2), order=0, reshape=True)
    assert out.shape[0] == 3
    assert out.shape[1:] in ((4, 10), (5, 11))   # rotated bbox (scipy rounding)
    # a reshape on a near-cap volume must be refused before allocation
    # (input 8300^2 = 68.9 M voxels is under the cap; the 45-deg bbox grows the
    # plane by sqrt(2) per axis -> ~137.8 M voxels, over the cap)
    big = np.zeros((1, 8300, 8300))
    with pytest.raises(ValueError, match="MAX_VOXELS"):
        vol_rotate(big, 45, axes=(1, 2), reshape=True)


def test_rotate_nonfinite_params_rejected():
    v = np.zeros((4, 4, 4))
    with pytest.raises(ValueError):
        vol_rotate(v, np.nan)
    with pytest.raises(ValueError):
        vol_rotate(v, 45, cval=np.inf)


# --------------------------------------------------------------------------- #
# vol_affine                                                                   #
# --------------------------------------------------------------------------- #
def test_affine_identity_is_identity():
    v = np.random.default_rng(2).random((5, 6, 7))
    out = vol_affine(v, np.eye(3), order=1)
    np.testing.assert_allclose(out, v, atol=1e-12)
    assert out.shape == v.shape


def test_affine_translation_moves_voxel_exactly():
    """Pull: out[o] = vol[o + offset], so offset (1, 2, 3) moves the object by
    (-1, -2, -3). A voxel at (5, 6, 7) must land exactly at (4, 4, 4)."""
    v = np.zeros((10, 10, 10))
    v[5, 6, 7] = 1.0
    out = vol_affine(v, np.eye(3), offset=(1, 2, 3), order=0)
    assert out[4, 4, 4] == 1.0
    assert out.sum() == 1.0


def test_affine_4x4_equals_3x3_plus_offset():
    v = np.random.default_rng(3).random((8, 9, 10))
    A = np.array([[1.0, 0.1, 0.0],
                  [0.0, 0.9, 0.2],
                  [0.1, 0.0, 1.1]])
    t = (0.5, -1.0, 2.0)
    M = np.eye(4)
    M[:3, :3] = A
    M[:3, 3] = t
    out3 = vol_affine(v, A, offset=t, order=1)
    out4 = vol_affine(v, M, order=1)
    assert np.array_equal(out3, out4)


def test_affine_pull_convention_scale_halves_object():
    """matrix = 2*I under pull semantics: out[o] = vol[2*o], so a box filling
    input [4:12)^3 appears at exactly [2:6)^3 — HALF size. If this test turns
    red the module silently became a push resampler."""
    v = np.zeros((16, 16, 16))
    v[4:12, 4:12, 4:12] = 1.0
    out = vol_affine(v, 2.0 * np.eye(3), order=0)
    expected = np.zeros((16, 16, 16))
    expected[2:6, 2:6, 2:6] = 1.0
    assert np.array_equal(out, expected)


def test_affine_output_shape_and_cap():
    v = np.zeros((4, 4, 4))
    out = vol_affine(v, np.eye(3), output_shape=(2, 3, 5))
    assert out.shape == (2, 3, 5)
    with pytest.raises(ValueError, match="MAX_VOXELS"):
        vol_affine(v, np.eye(3), output_shape=(4096, 4096, 4096))


def test_affine_bad_matrix_rejected():
    v = np.zeros((4, 4, 4))
    with pytest.raises(ValueError, match=r"\(3, 3\) or a \(4, 4\)"):
        vol_affine(v, np.eye(2))
    with pytest.raises(ValueError, match=r"\(3, 3\) or a \(4, 4\)"):
        vol_affine(v, np.zeros((2, 3)))
    bad4 = np.eye(4)
    bad4[3, 3] = 2.0                              # bottom row not (0, 0, 0, 1)
    with pytest.raises(ValueError, match="bottom row"):
        vol_affine(v, bad4)
    M = np.eye(4)
    with pytest.raises(ValueError, match="offset"):
        vol_affine(v, M, offset=(1, 0, 0))        # double translation: ambiguous
    nanM = np.eye(3)
    nanM[0, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        vol_affine(v, nanM)


# --------------------------------------------------------------------------- #
# common fail-closed contracts                                                 #
# --------------------------------------------------------------------------- #
_CALLS = [
    ("vol_resize", lambda v: vol_resize(v, factor=2)),
    ("vol_rotate", lambda v: vol_rotate(v, 30.0)),
    ("vol_affine", lambda v: vol_affine(v, np.eye(3))),
]


@pytest.mark.parametrize("name,call", _CALLS, ids=[n for n, _ in _CALLS])
def test_nan_volume_rejected(name, call):
    v = np.zeros((4, 4, 4))
    v[1, 1, 1] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        call(v)


@pytest.mark.parametrize("name,call", _CALLS, ids=[n for n, _ in _CALLS])
def test_2d_input_rejected(name, call):
    with pytest.raises(ValueError, match="3-D"):
        call(np.zeros((8, 8)))


@pytest.mark.parametrize("fn,kwargs", [
    (vol_resize, {"factor": 2}),
    (vol_rotate, {"angle_deg": 30.0}),
    (vol_affine, {"matrix": np.eye(3)}),
])
@pytest.mark.parametrize("order", [-1, 6, 1.5, "cubic", np.nan])
def test_order_must_be_exact_integer_0_to_5(fn, kwargs, order):
    with pytest.raises(ValueError, match="order"):
        fn(np.zeros((4, 4, 4)), order=order, **kwargs)


def test_ops_registry():
    assert volxform.VOLXFORM_OPS == ["vol_resize", "vol_rotate", "vol_affine"]
    for name in volxform.VOLXFORM_OPS:
        assert callable(getattr(volxform, name))
        assert name in volxform.__all__
