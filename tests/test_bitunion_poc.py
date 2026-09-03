# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Correctness gate for the precision-union PoC (poc/bitunion.py).

The PoC only earns its memory/speed claims if the uniform interface is *correct*:
lossless integer round-trip, affine ops in code-space equal to dense arithmetic,
threshold/sum equal to the dense answer. These are the properties the benchmark
then trades off against size — measured, not assumed.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "poc"))
import bitunion as bu  # noqa: E402


def _label_map(rng, h=64, w=48, k=5):
    return rng.integers(0, k, size=(h, w), dtype=np.int64)


def _smooth(rng, h=70, w=90):
    yy, xx = np.mgrid[0:h, 0:w]
    return (yy * 0.3 + xx * 0.2 + 5.0 * np.sin(xx * 0.1)).astype(np.float64)


def test_integer_roundtrip_is_lossless():
    rng = np.random.default_rng(0)
    for arr in (_label_map(rng), rng.integers(0, 256, (33, 41), dtype=np.int64)):
        pu = bu.encode(arr, tile=16, tol=0.0)
        assert np.array_equal(pu.to_dense(), arr), "integer tol=0 must be lossless"


def test_bit_histogram_reflects_local_range():
    rng = np.random.default_rng(1)
    lm = _label_map(rng, k=3)                      # <=3 labels -> range<=2 -> 2 bits
    hist = bu.encode(lm, tile=16, tol=0.0).bits_histogram()
    assert set(hist).issubset({0, 1, 2}), hist     # never needs more than 2 bits
    assert sum(hist.values()) > 0


def test_scale_shift_equals_dense_affine_without_touching_codes():
    rng = np.random.default_rng(2)
    arr = _smooth(rng)
    pu = bu.encode(arr, tile=16, tol=0.25)
    base = pu.to_dense()
    a, b = -1.7, 3.5
    shifted = pu.scale_shift(a, b)
    # codes shared verbatim: the blob object is literally the same array
    assert shifted.blob is pu.blob
    np.testing.assert_allclose(shifted.to_dense(), a * base + b, rtol=0, atol=1e-9)


def test_chained_affine_matches_dense():
    rng = np.random.default_rng(3)
    arr = _smooth(rng)
    pu = bu.encode(arr, tile=16, tol=0.25)
    dense = pu.to_dense()
    ops = [(1.5, -2.0), (0.5, 10.0), (-3.0, 1.0), (2.0, 0.0)]
    cur_pu, cur_d = pu, dense.copy()
    for a, b in ops:
        cur_pu = cur_pu.scale_shift(a, b)
        cur_d = a * cur_d + b
    np.testing.assert_allclose(cur_pu.to_dense(), cur_d, rtol=0, atol=1e-6)


def test_threshold_matches_dense():
    rng = np.random.default_rng(4)
    arr = _smooth(rng)
    pu = bu.encode(arr, tile=16, tol=0.1)
    dense = pu.to_dense()
    for t in (dense.min() - 1, np.median(dense), dense.max() + 1, dense.mean()):
        np.testing.assert_array_equal(pu.threshold(float(t)), dense > t)


def test_sum_and_mean_match_dense():
    rng = np.random.default_rng(5)
    arr = _smooth(rng)
    pu = bu.encode(arr, tile=16, tol=0.1)
    dense = pu.to_dense()
    assert abs(pu.sum() - dense.sum()) < 1e-6 * abs(dense.sum())
    assert abs(pu.mean() - dense.mean()) < 1e-9 + 1e-9 * abs(dense.mean())


def test_lossy_tolerance_is_respected():
    rng = np.random.default_rng(6)
    arr = _smooth(rng) + rng.standard_normal((70, 90)) * 0.5
    tol = 0.75
    pu = bu.encode(arr, tile=16, tol=tol)
    err = np.abs(pu.to_dense() - arr).max()
    # affine half-step bound holds per tile; global max error stays within tol
    # (allow tiny fp slack). tiles that hit the 16-bit ceiling are the only escape.
    assert err <= tol + 1e-6, err


def test_flat_tile_uses_zero_bits_and_no_blob():
    flat = np.full((32, 32), 7.0)
    pu = bu.encode(flat, tile=16, tol=0.0)
    assert pu.bits_histogram() == {0: 4}
    assert pu.blob.size == 0                # nothing packed: constants live in header
    assert np.array_equal(pu.to_dense(), flat)


def test_noise_is_honestly_reported_as_no_win():
    """High-entropy noise must NOT be claimed as a memory win: the union is allowed
    to be larger than dense uint8, and the container must report the true size."""
    rng = np.random.default_rng(7)
    noise = rng.integers(0, 256, (128, 128), dtype=np.int64)
    pu = bu.encode(noise, tile=16, tol=0.0)
    # every tile spans ~full range -> ~8 bits + header overhead => >= dense uint8
    assert pu.nbytes >= pu.dense_nbytes(np.uint8), (pu.nbytes, pu.dense_nbytes(np.uint8))
