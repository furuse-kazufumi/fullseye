"""PrecisionUnion — a tiled store whose bit-depth varies per tile.

The contract is: integer data round-trips **losslessly**, float data round-trips
within the requested ``atol``, the compressed store is genuinely smaller than a
dense array on low-entropy data (and the byte count is honestly accounted), and
every uniform operation (to_dense / threshold / mean / map_pointwise) agrees with
the same operation on the reconstructed dense array — with no branching on tile
bit-depth at the call site.
"""
from __future__ import annotations

import numpy as np
import pytest

from precision_union import PrecisionUnion, pack, unpack, _pack_codes, _unpack_codes


# --- sub-byte bit packing round-trips at every supported width -------------- #
@pytest.mark.parametrize("bits", [1, 2, 4, 8, 16])
def test_bitpack_roundtrip(bits):
    rng = np.random.default_rng(bits)
    n = 1000
    codes = rng.integers(0, 1 << bits, size=n).astype(np.uint16)
    buf = _pack_codes(codes, bits)
    back = _unpack_codes(buf, bits, n)
    assert np.array_equal(back, codes)
    # sub-byte widths must actually occupy sub-byte space (the whole point)
    if bits < 8:
        assert len(buf) <= (n * bits) // 8 + 1


def test_bitpack_constant_tile_is_zero_bytes():
    assert _pack_codes(np.zeros(500, np.uint16), 0) == b""


# --- lossless integer round-trip -------------------------------------------- #
@pytest.mark.parametrize("dtype", [np.uint8, np.uint16, np.int32])
def test_integer_roundtrip_is_lossless(dtype):
    rng = np.random.default_rng(0)
    a = rng.integers(0, 200, size=(130, 77)).astype(dtype)
    pu = PrecisionUnion.from_array(a, tile=32)
    assert pu.max_abs_error(a) == 0.0
    assert np.array_equal(pu.to_dense(), a)
    assert pu.to_dense().dtype == a.dtype


def test_lossless_on_few_value_label_map():
    rng = np.random.default_rng(1)
    a = np.zeros((256, 256), np.uint8)
    yy, xx = np.mgrid[0:256, 0:256]
    for _ in range(6):
        cy, cx, r, lab = rng.integers(0, 256), rng.integers(0, 256), 40, rng.integers(1, 5)
        a[(yy - cy) ** 2 + (xx - cx) ** 2 < r * r] = lab
    pu = PrecisionUnion.from_array(a, tile=32)
    assert np.array_equal(pu.to_dense(), a)          # lossless
    assert pu.ratio > 3.0, pu.ratio                  # and a real memory win


def test_far_apart_two_value_tile_uses_one_bit():
    # a tile holding only {0, 250} must land at 1 bit via the affine code, not 8;
    # this is the case the unit-scale path alone would get wrong (span 250 -> 8b).
    a = np.zeros((32, 32), np.uint8)
    a[:16] = 250
    pu = PrecisionUnion.from_array(a, tile=32)
    assert pu.bit_histogram()[1] == 1
    assert np.array_equal(pu.to_dense(), a)


def test_busy_uint8_tile_uses_eight_bits_not_sixteen():
    # a dense-range uint8 tile must not be pushed to 16 bits by a non-integer
    # affine scale — the unit-scale integer path keeps it at 8 (lossless).
    rng = np.random.default_rng(2)
    a = rng.integers(3, 251, size=(32, 32)).astype(np.uint8)
    pu = PrecisionUnion.from_array(a, tile=32)
    h = pu.bit_histogram()
    assert h[16] == 0 and h[8] == 1, h
    assert np.array_equal(pu.to_dense(), a)


# --- float round-trip within tolerance -------------------------------------- #
def test_float_roundtrip_within_atol():
    yy, xx = np.mgrid[0:200, 0:200]
    a = (5.0 + 3.0 * np.sin(xx / 40.0) + 2.0 * np.cos(yy / 30.0)).astype(np.float32)
    atol = 0.02
    pu = PrecisionUnion.from_array(a, tile=32, atol=atol)
    assert pu.max_abs_error(a) <= atol + 1e-6
    assert pu.ratio > 2.0, pu.ratio                  # beats dense float32


def test_float_atol_zero_is_near_lossless_but_honest():
    # atol==0 on float can hit the 16-bit fallback; the reported error must be the
    # TRUE achieved error, never silently claimed as zero.
    rng = np.random.default_rng(3)
    a = rng.standard_normal((64, 64)).astype(np.float64) * 1e6
    pu = PrecisionUnion.from_array(a, tile=32, atol=0.0)
    err = pu.max_abs_error(a)
    assert err == np.abs(pu.to_dense() - a).max()    # not a fabricated zero


# --- honest size accounting ------------------------------------------------- #
def test_nbytes_matches_component_sum():
    rng = np.random.default_rng(4)
    a = rng.integers(0, 16, size=(100, 100)).astype(np.uint8)
    pu = PrecisionUnion.from_array(a, tile=25)
    body = sum(len(t.buf) for t in pu._tiles)
    meta = len(pu._tiles) * (1 + 8 + 8)
    assert pu.nbytes == meta + body + 32


def test_high_entropy_photo_is_not_falsely_claimed_to_win():
    # honest negative: a busy uint8 image cannot beat 8-bit dense; the ratio must
    # come out <= ~1, never a fabricated large number.
    rng = np.random.default_rng(5)
    a = rng.integers(0, 256, size=(256, 256)).astype(np.uint8)
    pu = PrecisionUnion.from_array(a, tile=32)
    assert np.array_equal(pu.to_dense(), a)
    assert pu.ratio < 1.05, pu.ratio


# --- uniform ops agree with the dense reconstruction ------------------------ #
def _mixed():
    rng = np.random.default_rng(9)
    a = np.zeros((150, 90), np.int32)
    a[:50] = 7                                        # constant tiles
    a[50:100] = rng.integers(0, 4, (50, 90))         # low-bit tiles
    a[100:] = rng.integers(0, 250, (50, 90))         # 8-bit tiles
    return a


def test_threshold_matches_dense():
    a = _mixed()
    pu = PrecisionUnion.from_array(a, tile=32)
    d = pu.to_dense()
    for thr in (-1, 3, 6, 100, 300):
        assert np.array_equal(pu.threshold(thr), d > thr)


def test_mean_matches_dense():
    a = _mixed()
    pu = PrecisionUnion.from_array(a, tile=32)
    assert abs(pu.mean() - pu.to_dense().mean()) < 1e-6


def test_map_pointwise_integer_result_is_exact():
    a = _mixed()
    pu = PrecisionUnion.from_array(a, tile=32)
    d = pu.to_dense().astype(np.float64)
    for f in (lambda x: x * 2 + 1, lambda x: -x):          # integer-valued outputs
        got = pu.map_pointwise(f, atol=0.0).to_dense()
        assert np.abs(got.astype(np.float64) - f(d)).max() < 1e-6, f


def test_map_pointwise_float_result_is_bounded_by_atol():
    # a float-valued f cannot be lossless in a quantized union; the honest
    # contract is that the re-encoding error stays within the given atol.
    a = _mixed()
    pu = PrecisionUnion.from_array(a, tile=32)
    d = pu.to_dense().astype(np.float64)
    atol = 1e-3
    got = pu.map_pointwise(lambda x: np.sqrt(np.abs(x)), atol=atol).to_dense()
    assert np.abs(got.astype(np.float64) - np.sqrt(np.abs(d))).max() <= atol + 1e-6


def test_map_pointwise_constant_fast_path_is_correct():
    # a fully-constant array must map in the O(1)-per-tile path and still be right
    a = np.full((64, 64), 5.0, np.float64)
    pu = PrecisionUnion.from_array(a, tile=32)
    assert all(t.bits == 0 for t in pu._tiles)       # all constant -> fast path
    out = pu.map_pointwise(lambda x: x ** 2 + 1).to_dense()
    assert np.allclose(out, 26.0)


# --- edge cases ------------------------------------------------------------- #
def test_non_tile_aligned_shape():
    rng = np.random.default_rng(6)
    a = rng.integers(0, 50, size=(101, 47)).astype(np.uint8)   # not a multiple of 32
    pu = PrecisionUnion.from_array(a, tile=32)
    assert np.array_equal(pu.to_dense(), a)


def test_single_pixel_and_all_constant():
    assert np.array_equal(PrecisionUnion.from_array(np.array([[9]], np.uint8)).to_dense(),
                          np.array([[9]], np.uint8))
    a = np.full((40, 40), 3, np.uint8)
    pu = PrecisionUnion.from_array(a, tile=16)
    assert np.array_equal(pu.to_dense(), a)
    # constant tiles carry no codes, but each still costs 17 B of metadata, so a
    # tiny array wins modestly; the win grows with tile size / region size.
    assert pu.ratio > 5.0, pu.ratio
    big = np.full((512, 512), 3, np.uint8)            # large constant region
    assert PrecisionUnion.from_array(big, tile=64).ratio > 200.0


def test_pack_unpack_free_functions():
    a = np.arange(96, dtype=np.uint8).reshape(8, 12)
    assert np.array_equal(unpack(pack(a, tile=4)), a)


def test_rejects_non_2d():
    with pytest.raises(ValueError):
        PrecisionUnion.from_array(np.zeros((4, 4, 4), np.uint8))


# --- exposed through the public facade -------------------------------------- #
def test_exposed_via_api_and_facade():
    import api
    assert "PrecisionUnion" in api.__all__
    assert api.PrecisionUnion is PrecisionUnion


# --- deferred affine: scale_shift is exact and touches no codes ------------- #
def _smooth(h=70, w=90):
    yy, xx = np.mgrid[0:h, 0:w]
    return (yy * 0.3 + xx * 0.2 + 5.0 * np.sin(xx * 0.1)).astype(np.float64)


def test_scale_shift_equals_dense_affine_and_shares_code_buffers():
    pu = PrecisionUnion.from_array(_smooth(), tile=16, atol=0.25)
    base = pu.to_dense()
    a, b = -1.7, 3.5
    shifted = pu.scale_shift(a, b)
    # the packed code buffers are reused verbatim — no decode, no re-encode
    for t_src, t_dst in zip(pu._tiles, shifted._tiles):
        assert t_dst.buf is t_src.buf
        assert t_dst.bits == t_src.bits
    np.testing.assert_allclose(shifted.to_dense(), a * base + b, rtol=0, atol=1e-9)


def test_scale_shift_chain_matches_dense_chain():
    pu = PrecisionUnion.from_array(_smooth(), tile=16, atol=0.25)
    dense = pu.to_dense()
    cur_pu, cur_d = pu, dense.copy()
    for a, b in [(1.5, -2.0), (0.5, 10.0), (-3.0, 1.0), (2.0, 0.0)]:
        cur_pu = cur_pu.scale_shift(a, b)
        cur_d = a * cur_d + b
    np.testing.assert_allclose(cur_pu.to_dense(), cur_d, rtol=0, atol=1e-6)


def test_scale_shift_handles_constant_tiles():
    pu = PrecisionUnion.from_array(np.full((32, 32), 7.0), tile=16)
    out = pu.scale_shift(3.0, 1.0).to_dense()
    np.testing.assert_allclose(out, np.full((32, 32), 22.0))
