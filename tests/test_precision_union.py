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


def test_rejects_zero_d_scalar():
    with pytest.raises(ValueError):
        PrecisionUnion.from_array(np.asarray(7, np.uint8))       # 0-d has no tiles


def test_rejects_tile_axis_mismatch():
    with pytest.raises(ValueError):
        PrecisionUnion.from_array(np.zeros((4, 4, 4), np.uint8), tile=(8, 8))


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


# --- N-D: the volume case is the headline memory win ------------------------ #
def _label_volume(rng, shape=(24, 48, 48), k=6):
    return rng.integers(0, k, size=shape, dtype=np.int64)


def test_3d_integer_volume_roundtrips_losslessly():
    rng = np.random.default_rng(10)
    vol = _label_volume(rng)
    pu = PrecisionUnion.from_array(vol, tile=8, atol=0.0)
    assert pu.shape == vol.shape
    assert np.array_equal(pu.to_dense(), vol)               # lossless N-D round-trip


def test_3d_volume_saves_memory():
    # a label volume with large constant regions compresses hard in 3-D
    vol = np.zeros((32, 32, 32), np.uint8)
    vol[8:24, 8:24, 8:24] = 1                               # one interior box
    pu = PrecisionUnion.from_array(vol, tile=8)
    assert pu.ratio > 8.0, pu.ratio                         # dense uint8 vs the union


def test_3d_uniform_ops_match_dense():
    rng = np.random.default_rng(11)
    vol = (rng.random((16, 20, 24)) * 50).astype(np.float64)
    pu = PrecisionUnion.from_array(vol, tile=8, atol=0.2)
    dense = pu.to_dense()
    # threshold, mean, scale_shift all work in N-D with no bit-depth branching
    np.testing.assert_array_equal(pu.threshold(25.0), dense > 25.0)
    assert abs(pu.mean() - dense.mean()) < 1e-6 * abs(dense.mean())
    np.testing.assert_allclose(pu.scale_shift(2.0, -3.0).to_dense(),
                               2.0 * dense - 3.0, rtol=0, atol=1e-9)


def test_per_axis_tile_sizes():
    rng = np.random.default_rng(12)
    vol = rng.integers(0, 4, (10, 20, 30), dtype=np.int64)
    pu = PrecisionUnion.from_array(vol, tile=(5, 10, 10))
    assert pu._grid == (2, 2, 3)
    assert np.array_equal(pu.to_dense(), vol)


def test_1d_signal_roundtrips():
    sig = np.arange(1000, dtype=np.int64) % 7
    pu = PrecisionUnion.from_array(sig, tile=64)
    assert np.array_equal(pu.to_dense(), sig)


# --- serialization: the memory win becomes a file-size win ------------------ #
def test_save_load_roundtrip_2d(tmp_path):
    rng = np.random.default_rng(20)
    arr = rng.integers(0, 5, (40, 50), dtype=np.int64)
    pu = PrecisionUnion.from_array(arr, tile=16)
    p = tmp_path / "pu.npz"
    pu.save(p)
    back = PrecisionUnion.load(p)
    assert back.shape == pu.shape
    assert np.array_equal(back.to_dense(), arr)
    # the file is in the ballpark of the in-memory store, not the dense array
    assert p.stat().st_size < pu.dense_nbytes


def test_save_load_roundtrip_3d_float(tmp_path):
    rng = np.random.default_rng(21)
    vol = (rng.random((16, 16, 16)) * 100).astype(np.float64)
    pu = PrecisionUnion.from_array(vol, tile=8, atol=0.3)
    p = tmp_path / "vol.npz"
    pu.save(p)
    back = PrecisionUnion.load(p)
    np.testing.assert_array_equal(back.to_dense(), pu.to_dense())   # bit-identical
    assert back._tsz == pu._tsz and back._grid == pu._grid


def test_to_state_is_pure_numeric():
    pu = PrecisionUnion.from_array(np.arange(64, dtype=np.uint8).reshape(8, 8), tile=4)
    st = pu.to_state()
    for k, v in st.items():
        assert isinstance(v, np.ndarray), (k, type(v))
    assert np.array_equal(PrecisionUnion.from_state(st).to_dense(),
                          pu.to_dense())


# --- clip: per-tile deferral, exact vs np.clip ------------------------------ #
def _clip_probe():
    """Tiles of four kinds: fully inside [0,1], fully above, fully below, straddling."""
    a = np.zeros((64, 16), np.float64)
    a[0:16] = np.linspace(0.2, 0.8, 16)[:, None]      # inside  -> identity (lazy)
    a[16:32] = 1.5 + np.linspace(0, 0.3, 16)[:, None]  # above   -> constant 1
    a[32:48] = -0.7 + np.linspace(0, 0.2, 16)[:, None] # below   -> constant 0
    a[48:64] = np.linspace(-0.5, 1.5, 16)[:, None]     # straddle -> decoded+re-encoded
    return a


def test_clip_matches_dense_and_defers_by_tile():
    a = _clip_probe()
    pu = PrecisionUnion.from_array(a, tile=16, atol=1e-3)
    dense = pu.to_dense()
    c = pu.clip(0.0, 1.0)
    # straddling tiles are re-quantised at their own step/2 (see clip docstring):
    # the difference to np.clip is bounded by the encoding atol, not by eps.
    np.testing.assert_allclose(c.to_dense(), np.clip(dense, 0, 1), rtol=0, atol=1e-3)
    inside, above, below, straddle = c._tiles[0], c._tiles[1], c._tiles[2], c._tiles[3]
    assert inside.buf is pu._tiles[0].buf                # untouched: codes shared
    assert above.bits == 0 and above.offset == 1.0       # collapsed to a constant
    assert below.bits == 0 and below.offset == 0.0
    assert straddle.buf is not pu._tiles[3].buf          # the only tile that paid


def test_clip_after_negative_gain_uses_flipped_range():
    # scale_shift(-1, 1) makes scale negative; _tile_range must still bound correctly
    a = np.linspace(0.0, 1.0, 256).reshape(16, 16)
    pu = PrecisionUnion.from_array(a, tile=16, atol=1e-3)
    inv = pu.scale_shift(-1.0, 1.0)
    lo, hi = inv._tile_range(inv._tiles[0])
    assert lo <= inv.to_dense().min() + 1e-9 and hi >= inv.to_dense().max() - 1e-9
    np.testing.assert_allclose(inv.clip(0, 1).to_dense(), np.clip(1 - pu.to_dense(), 0, 1),
                               rtol=0, atol=1e-12)


# --- op-pipeline integration: lazy ops via fullseye.apply / run_pipeline ---- #
def _contract_image():
    rng = np.random.default_rng(30)
    yy, xx = np.mgrid[0:64, 0:48]
    img = 0.5 + 0.45 * np.sin(xx / 7.0) * np.cos(yy / 9.0) + 0.02 * rng.standard_normal((64, 48))
    return np.clip(img, 0, 1)                            # float64 in [0,1]: the contract


@pytest.mark.parametrize("name", sorted(__import__("precision_union").LAZY_OPS))
def test_apply_lazy_op_parity_with_dense(name):
    """apply(pu, name) must equal apply(dense, name) on the REAL op — this locks
    the (a,b) -> gain/offset mapping in LAZY_OPS to ops.py (drift fails here)."""
    import api
    pu = PrecisionUnion.from_array(_contract_image(), tile=16, atol=1e-3)
    dense = pu.to_dense()
    rng = np.random.default_rng(31)
    for _ in range(6):
        a, b = float(rng.random()), float(rng.random())  # b=1 pushes scale_clip past 1
        r = api.apply(pu, name, a, b)
        assert isinstance(r, PrecisionUnion), "lazy op must stay a union"
        # clip re-quantises straddling tiles at their own step (<= encoding atol
        # 1e-3, x gain <= 2 for scale_clip): the honest parity bound is ~2e-3
        np.testing.assert_allclose(r.to_dense(), api.apply(dense, name, a, b),
                                   rtol=0, atol=2.5e-3)


def test_apply_lazy_scale_clip_activates_clip_and_stays_partly_lazy():
    import api
    pu = PrecisionUnion.from_array(_contract_image(), tile=16, atol=1e-3)
    r = api.apply(pu, "scale_clip", 1.0, 1.0)            # 2v + 0.5: clips above 0.25
    dense = api.apply(pu.to_dense(), "scale_clip", 1.0, 1.0)
    np.testing.assert_allclose(r.to_dense(), dense, rtol=0, atol=2.5e-3)
    assert (dense == 1.0).any()                          # the clip really fired


def test_apply_non_lazy_op_materialises_once_and_matches():
    import api
    pu = PrecisionUnion.from_array(_contract_image(), tile=16, atol=1e-3)
    r = api.apply(pu, "gaussian", 0.5, 0.5)
    assert isinstance(r, np.ndarray)                      # materialised
    np.testing.assert_allclose(r, api.apply(pu.to_dense(), "gaussian", 0.5, 0.5),
                               rtol=0, atol=1e-12)


def test_apply_uint8_union_converts_lazily_and_records_the_ledger():
    """A uint8 union is brought onto the [0,1] contract LAZILY (scale_shift(1/255)):
    it stays a union, matches the dense path bit-for-bit, and leaves the same
    dtype_converted ledger record that the dense /255 conversion leaves."""
    import api
    rng = np.random.default_rng(32)
    u8 = rng.integers(0, 256, (32, 32), dtype=np.uint8)
    pu = PrecisionUnion.from_array(u8, tile=16)
    api.clear_fallbacks()
    r = api.apply(pu, "invert", 0.5, 0.5)
    assert isinstance(r, PrecisionUnion)                  # lazy, not materialised
    assert r.atol == 0.0                                  # lossless stays lossless
    np.testing.assert_allclose(r.to_dense(), api.apply(u8, "invert", 0.5, 0.5),
                               rtol=0, atol=1e-12)
    assert api.fallback_counts().get("invert", 0) >= 1
    assert any("dtype_converted" in str(e) for e in api.fallbacks())


def test_apply_uint8_union_is_refused_under_raise_like_dense():
    import api
    pu = PrecisionUnion.from_array(np.zeros((16, 16), np.uint8), tile=16)
    with pytest.raises(ValueError):
        api.apply(pu, "invert", 0.5, 0.5, on_error="raise")


def test_apply_int64_union_materialises_data_dependent_scale():
    """int64 has no documented full scale (the divisor depends on the data), so the
    union cannot convert lazily: it materialises and matches the dense path."""
    import api
    rng = np.random.default_rng(33)
    i64 = rng.integers(0, 1000, (32, 32), dtype=np.int64)
    pu = PrecisionUnion.from_array(i64, tile=16)
    r = api.apply(pu, "invert", 0.5, 0.5)
    assert isinstance(r, np.ndarray)
    np.testing.assert_allclose(r, api.apply(i64, "invert", 0.5, 0.5), rtol=0, atol=1e-12)


def test_apply_bool_union_converts_lazily():
    import api
    m = (np.arange(256).reshape(16, 16) % 3 == 0)
    pu = PrecisionUnion.from_array(m, tile=16)
    r = api.apply(pu, "invert", 0.5, 0.5)
    assert isinstance(r, PrecisionUnion)
    np.testing.assert_allclose(r.to_dense(), api.apply(m, "invert", 0.5, 0.5),
                               rtol=0, atol=1e-12)


def test_run_pipeline_uint8_label_volume_chain_stays_lazy():
    """The headline case: a uint8 label VOLUME through a point-op chain never
    materialises until the first non-lazy stage."""
    import api
    vol = np.zeros((16, 32, 32), np.uint8)
    vol[4:12, 8:24, 8:24] = 200
    pu = PrecisionUnion.from_array(vol, tile=8)
    chain = [("invert", 0.5, 0.5), ("scale_clip", 0.6, 0.4)]
    lazy = api.run_pipeline(pu, chain)
    assert isinstance(lazy, PrecisionUnion)
    np.testing.assert_allclose(lazy.to_dense(), api.run_pipeline(vol, chain),
                               rtol=0, atol=1e-12)


def test_run_pipeline_lazy_chain_then_materialise():
    import api
    pu = PrecisionUnion.from_array(_contract_image(), tile=16, atol=1e-3)
    dense = pu.to_dense()
    chain = [("invert", 0.5, 0.5), ("scale_clip", 0.8, 0.3), ("invert", 0.5, 0.5)]
    lazy = api.run_pipeline(pu, chain)
    assert isinstance(lazy, PrecisionUnion)              # all-lazy chain stays a union
    # three lazy stages, each bounded by the encoding atol x its gain (<= 1.7)
    np.testing.assert_allclose(lazy.to_dense(), api.run_pipeline(dense, chain),
                               rtol=0, atol=5e-3)
    full = chain + [("gaussian", 0.5, 0.5)]
    out = api.run_pipeline(pu, full)
    assert isinstance(out, np.ndarray)                    # first non-lazy stage materialises
    np.testing.assert_allclose(out, api.run_pipeline(dense, full), rtol=0, atol=5e-3)


# --- the atol contract travels with the union ------------------------------- #
def test_lossless_union_clips_losslessly():
    """atol=0 (integer label map): clip to integer bounds must stay bit-exact —
    the straddling tiles re-plan at atol=0 and take the exact integer path."""
    rng = np.random.default_rng(40)
    lab = rng.integers(-3, 9, (48, 32), dtype=np.int64)
    pu = PrecisionUnion.from_array(lab, tile=16)
    assert pu.atol == 0.0
    c = pu.clip(0, 5)
    assert c.atol == 0.0
    np.testing.assert_array_equal(c.to_dense(), np.clip(lab, 0, 5))


def test_scale_shift_scales_the_tolerance_and_clip_honours_it():
    a = _clip_probe()
    pu = PrecisionUnion.from_array(a, tile=16, atol=1e-3)
    g = pu.scale_shift(3.0, 0.0)
    assert g.atol == pytest.approx(3e-3)                # |gain| x atol
    c = g.clip(0.0, 1.0)
    assert c.atol == pytest.approx(3e-3)
    np.testing.assert_allclose(c.to_dense(), np.clip(3.0 * pu.to_dense(), 0, 1),
                               rtol=0, atol=3e-3 + 1e-9)


def test_save_load_persists_atol(tmp_path):
    pu = PrecisionUnion.from_array(_clip_probe(), tile=16, atol=2.5e-3)
    p = tmp_path / "t.npz"
    pu.save(p)
    assert PrecisionUnion.load(p).atol == pytest.approx(2.5e-3)


# --- exact clip guarantees: cmax range, code-space clip, raw fallback ------- #
def test_tile_range_is_exact_not_overestimated():
    # a busy uint8 tile with max 250 (unit-scale path, 8 bits) must report hi=250,
    # not offset+255 — the over-estimate turned in-range tiles into false straddles.
    a = np.full((16, 16), 3, np.uint8); a[0, :] = 250; a[1, :] = 100
    pu = PrecisionUnion.from_array(a, tile=16)
    assert pu._tile_range(pu._tiles[0]) == (3.0, 250.0)


def test_lossless_uint8_union_through_scale_clip_is_bit_exact_vs_dense():
    """The lossless contract under a straddling clip: a uint8 union pushed past 1 by
    scale_clip must still match the dense float64 path EXACTLY (raw tiles if a
    grid cannot hold the clipped values), not to within a 16-bit half-step."""
    import api
    rng = np.random.default_rng(50)
    u8 = rng.integers(0, 256, (32, 32), dtype=np.uint8)
    pu = PrecisionUnion.from_array(u8, tile=16)
    r = api.apply(pu, "scale_clip", 1.0, 1.0)             # 2v+0.5: heavy clipping
    assert isinstance(r, PrecisionUnion) and r.atol == 0.0
    # exact in real arithmetic; float64 association differs from the dense path by
    # ulps (~1e-16), six orders below a 16-bit half-step (7.6e-6) — the bug this guards
    np.testing.assert_allclose(r.to_dense(), api.apply(u8, "scale_clip", 1.0, 1.0),
                               rtol=0, atol=1e-12)


def test_on_grid_bounds_clip_in_code_space_without_raw_fallback():
    # values k/3 sit exactly on the 2-bit grid (2**2-1 = 3 steps; note k/4 would NOT:
    # 4 is not 2**b-1). Clipping to [1/3, 2/3] keeps the bounds on that grid ->
    # code-space clip: same bits, no raw tile, exact.
    a = (np.arange(256) % 4 / 3.0).reshape(16, 16)
    pu = PrecisionUnion.from_array(a, tile=16, atol=0.0)
    t0 = pu._tiles[0]
    assert t0.bits == 2
    c = pu.clip(1.0 / 3.0, 2.0 / 3.0)
    assert c._tiles[0].bits == 2                            # stayed on the 2-bit grid
    np.testing.assert_array_equal(c.to_dense(), np.clip(a, 1.0 / 3.0, 2.0 / 3.0))


def test_raw_tile_roundtrips_through_save_load(tmp_path):
    pu = PrecisionUnion.from_array(np.linspace(-0.3, 1.3, 256).reshape(16, 16), tile=16, atol=0.0)
    c = pu.clip(0.0, 1.0)                                  # off-grid bounds, atol=0 -> raw
    assert 64 in {t.bits for t in c._tiles}
    p = tmp_path / "raw.npz"
    c.save(p)
    np.testing.assert_array_equal(PrecisionUnion.load(p).to_dense(), c.to_dense())


def test_float_union_with_atol_requantises_instead_of_raw():
    pu = PrecisionUnion.from_array(np.linspace(-0.3, 1.3, 256).reshape(16, 16), tile=16, atol=1e-3)
    c = pu.clip(0.0, 1.0)
    assert 64 not in {t.bits for t in c._tiles}            # memory-cheap path
    assert np.abs(c.to_dense() - np.clip(pu.to_dense(), 0, 1)).max() <= 1e-3 + 1e-12


# --- lazy threshold: the memory win propagates through the most common op --- #
def test_threshold_lazy_matches_dense_and_costs_at_most_one_bit():
    a = _clip_probe()                                       # constant/above/below/straddle
    pu = PrecisionUnion.from_array(a, tile=16, atol=1e-3)
    dense = pu.to_dense()
    for thr in (-1.0, 0.0, 0.5, 1.0, 5.0):
        m = pu.threshold_lazy(thr)
        assert isinstance(m, PrecisionUnion) and m.atol == 0.0
        np.testing.assert_array_equal(m.to_dense(), (dense > thr).astype(np.float64))
        assert set(m.bit_histogram()) - {0, 1} == set() or all(
            m.bit_histogram()[b] == 0 for b in m.bit_histogram() if b > 1)


def test_threshold_lazy_one_sided_tiles_skip_decode():
    pu = PrecisionUnion.from_array(_clip_probe(), tile=16, atol=1e-3)
    m = pu.threshold_lazy(0.5)
    # tile 1 (all >= 1.5) and tile 2 (all <= -0.5) are decided from the header
    assert m._tiles[1].bits == 0 and m._tiles[1].offset == 1.0
    assert m._tiles[2].bits == 0 and m._tiles[2].offset == 0.0


def test_apply_threshold_stays_lazy_and_keeps_the_memory_win():
    """uint8 label VOLUME -> lazy /255 -> lazy threshold: never materialised, and
    the result is a tiny 0/1 union (<= 1 bit/voxel) that matches the dense op."""
    import api
    vol = np.zeros((32, 64, 64), np.uint8)
    vol[8:24, 16:48, 16:48] = 200
    pu = PrecisionUnion.from_array(vol, tile=8)
    r = api.apply(pu, "threshold", 0.5, 0.5)
    assert isinstance(r, PrecisionUnion)
    np.testing.assert_array_equal(r.to_dense(), api.apply(vol, "threshold", 0.5, 0.5))
    assert r.ratio > 8.0, r.ratio                           # the win propagated
    chain = [("invert", 0.5, 0.5), ("threshold", 0.7, 0.5)]
    lazy = api.run_pipeline(pu, chain)
    assert isinstance(lazy, PrecisionUnion)
    np.testing.assert_array_equal(lazy.to_dense(), api.run_pipeline(vol, chain))


# --- two-union ops closed over unions (n-ary tier) --------------------------- #
def _two_label_masks():
    """Two uint8 label volumes whose masks overlap partially: many tiles are
    constant on one or both sides (the shortcut cases), some straddle on both."""
    a = np.zeros((16, 32, 32), np.uint8); a[2:12, 4:20, 4:20] = 200
    b = np.zeros((16, 32, 32), np.uint8); b[6:16, 12:28, 12:28] = 200
    return a, b


@pytest.mark.parametrize("name", ["union2", "intersection", "difference", "symm_difference"])
def test_nary_region_ops_stay_lazy_and_match_dense(name):
    import api
    a, b = _two_label_masks()
    pa, pb = PrecisionUnion.from_array(a, tile=8), PrecisionUnion.from_array(b, tile=8)
    r = api.apply([pa, pb], name, 0.5, 0.5)
    assert isinstance(r, PrecisionUnion) and r.atol == 0.0
    np.testing.assert_array_equal(r.to_dense(), api.apply([a, b], name, 0.5, 0.5))
    assert set(k for k, v in r.bit_histogram().items() if v) <= {0, 1}   # <= 1 bit/voxel


def test_mask_binop_shares_codes_on_constant_shortcuts():
    a, b = _two_label_masks()
    pa, pb = PrecisionUnion.from_array(a, tile=8), PrecisionUnion.from_array(b, tile=8)
    qa, qb = pa.threshold_lazy(0.5), pb.threshold_lazy(0.5)
    r = qa.mask_binop(qb, "or")
    shared = sum(1 for t, tq, ta in zip(r._tiles, qb._tiles, qa._tiles)
                 if t.bits == 1 and (t.buf is tq.buf or t.buf is ta.buf))
    assert shared > 0                                     # x | 0 = x reused verbatim


@pytest.mark.parametrize("name", ["max_image", "min_image"])
def test_nary_extrema_stay_lazy_and_match_dense(name):
    import api
    rng = np.random.default_rng(60)
    yy, xx = np.mgrid[0:64, 0:64]
    a = np.clip(0.5 + 0.4 * np.sin(xx / 9.0), 0, 1)                 # smooth
    b = np.full((64, 64), 0.5); b[:32] = 0.9; b[32:, :32] = 0.1         # constant tiles
    pa = PrecisionUnion.from_array(a, tile=16, atol=1e-3)
    pb = PrecisionUnion.from_array(b, tile=16, atol=0.0)
    r = api.apply([pa, pb], name, 0.5, 0.5)
    assert isinstance(r, PrecisionUnion)
    np.testing.assert_allclose(r.to_dense(), api.apply([pa.to_dense(), pb.to_dense()], name, 0.5, 0.5),
                               rtol=0, atol=1e-3 + 1e-9)


def test_nary_with_mismatched_tiling_materialises():
    import api
    a, b = _two_label_masks()
    pa, pb = PrecisionUnion.from_array(a, tile=8), PrecisionUnion.from_array(b, tile=16)
    r = api.apply([pa, pb], "union2", 0.5, 0.5)
    assert isinstance(r, np.ndarray)
    np.testing.assert_array_equal(r, api.apply([a, b], "union2", 0.5, 0.5))


# --- header-exact features --------------------------------------------------- #
def test_min_max_from_headers_are_exact():
    rng = np.random.default_rng(61)
    a = rng.random((48, 40))
    pu = PrecisionUnion.from_array(a, tile=16, atol=1e-3)
    d = pu.to_dense()
    assert pu.min() == d.min() and pu.max() == d.max()


def test_area_frac_feature_matches_dense_and_uses_popcount():
    import api
    a, _ = _two_label_masks()
    pu = PrecisionUnion.from_array(a, tile=8)
    m = api.apply(pu, "threshold", 0.5, 0.5)              # 0/1 union (lazy)
    got = api.apply(m, "area_frac", 0.5, 0.5)
    ref = api.apply(api.apply(a, "threshold", 0.5, 0.5), "area_frac", 0.5, 0.5)
    assert isinstance(got, float) and got == pytest.approx(ref, abs=0)


@pytest.mark.parametrize("name", ["min_max_gray", "intensity"])
def test_gray_features_from_headers_match_dense(name):
    """min_max_gray (clipped max) is pure header algebra; intensity (clipped mean)
    decodes only non-constant tiles. Both must equal the dense closure exactly."""
    import api
    rng = np.random.default_rng(62)
    yy, xx = np.mgrid[0:48, 0:40]
    a = np.clip(0.5 + 0.6 * np.sin(xx / 6.0) * np.cos(yy / 5.0), -0.2, 1.2)   # clips matter
    pu = PrecisionUnion.from_array(a, tile=16, atol=1e-3)
    d = pu.to_dense()
    assert api.apply(pu, name, 0.5, 0.5) == pytest.approx(api.apply(d, name, 0.5, 0.5), abs=1e-12)
    u8 = rng.integers(0, 256, (32, 32), dtype=np.uint8)               # lazy /255 first
    pu8 = PrecisionUnion.from_array(u8, tile=16)
    assert api.apply(pu8, name, 0.5, 0.5) == pytest.approx(api.apply(u8, name, 0.5, 0.5), abs=1e-12)
