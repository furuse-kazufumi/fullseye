"""性能レビュー第27便の一致ゲート。

旧実装は各テスト内の参照関数として残し、高速経路の結果と比較する。
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy import ndimage

import volxform as vx


def _old_resize(v, shape, order=1, mode="nearest", cval=0.0):
    zoom = [t / s for t, s in zip(shape, v.shape)]
    out = ndimage.zoom(v, zoom, order=order, grid_mode=True, mode=mode, cval=cval)
    return np.ascontiguousarray(out, dtype=np.float64)


def _old_rotate(v, angle, axes=(1, 2), order=1, reshape=False,
                mode="constant", cval=0.0):
    out = ndimage.rotate(v, angle, axes=axes, reshape=reshape, order=order,
                         mode=mode, cval=cval)
    return np.ascontiguousarray(out, dtype=np.float64)


def _old_affine(v, matrix, offset, shape, order=1,
                mode="constant", cval=0.0):
    out = ndimage.affine_transform(v, matrix, offset=offset, output_shape=shape,
                                   order=order, mode=mode, cval=cval)
    return np.ascontiguousarray(out, dtype=np.float64)


@pytest.mark.parametrize("order", [0, 1])
def test_368_same_shape_resize_is_bit_identical(order):
    v = np.random.default_rng(368).normal(size=(13, 11, 9))
    got = vx.vol_resize(v, shape=v.shape, order=order)
    ref = _old_resize(v, v.shape, order=order)
    assert np.array_equal(got, ref)
    assert got is not v and got.flags.c_contiguous


@pytest.mark.parametrize("angle", [-270.0, -180.0, -90.0, 0.0, 90.0, 180.0, 270.0])
@pytest.mark.parametrize("order", [0, 1])
def test_367_quarter_turn_is_bit_identical(angle, order):
    v = np.arange(7 * 9 * 9, dtype=np.float64).reshape(7, 9, 9)
    got = vx.vol_rotate(v, angle, order=order)
    ref = _old_rotate(v, angle, order=order)
    assert np.array_equal(got, ref)


def test_367_near_quarter_turn_uses_general_path(monkeypatch):
    calls = 0
    old = ndimage.rotate

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return old(*args, **kwargs)

    monkeypatch.setattr(vx.ndimage, "rotate", counted)
    vx.vol_rotate(np.ones((5, 5, 5)), 90.0000001, order=1)
    assert calls == 1


def test_364_diagonal_affine_variant_and_near_miss_dispatch(monkeypatch):
    v = np.random.default_rng(364).normal(size=(17, 15, 13))
    calls = []
    old = ndimage.affine_transform

    def counted(inp, matrix, **kwargs):
        calls.append(np.asarray(matrix).shape)
        return old(inp, matrix, **kwargs)

    monkeypatch.setattr(vx.ndimage, "affine_transform", counted)
    diag = np.diag([0.75, 1.0, 1.25])
    got = vx.vol_affine(v, diag, offset=(0.2, 0.0, -0.3), order=1)
    ref = _old_affine(v, diag, (0.2, 0.0, -0.3), v.shape)
    assert np.array_equal(got, ref)
    assert calls[-1] == (3, 3)
    fast = vx.vol_affine(v, diag, offset=(0.2, 0.0, -0.3), order=1,
                         method="fast")
    assert calls[-1] == (3,)
    assert np.max(np.abs(fast - ref)) <= 1e-12
    near = diag.copy()
    near[0, 1] = 1e-9
    vx.vol_affine(v, near, order=1, method="fast")
    assert calls[-1] == (3, 3)


def test_364_fast_variant_large_dc_tiny_variance_probe():
    rng = np.random.default_rng(1364)
    v = 1e6 + rng.normal(scale=1e-8, size=(17, 15, 13))
    A = np.diag([0.875, 1.125, 0.9375])
    exact = vx.vol_affine(v, A, offset=(0.2, -0.3, 0.4), method="exact")
    fast = vx.vol_affine(v, A, offset=(0.2, -0.3, 0.4), method="fast")
    assert np.max(np.abs(fast - exact)) <= 1e-9


@pytest.mark.parametrize("order", [0, 1])
def test_366_integer_translation_matches_reference(order):
    v = np.random.default_rng(366).normal(size=(17, 15, 13))
    off = np.array([2.0, -3.0, 1.0])
    got = vx.vol_affine(v, np.eye(3), offset=off, order=order,
                        mode="constant", cval=-7.25)
    ref = _old_affine(v, np.eye(3), off, v.shape, order=order,
                      mode="constant", cval=-7.25)
    assert np.array_equal(got, ref)


def test_366_non_integer_translation_uses_general_path(monkeypatch):
    calls = 0
    old = ndimage.affine_transform

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return old(*args, **kwargs)

    monkeypatch.setattr(vx.ndimage, "affine_transform", counted)
    vx.vol_affine(np.ones((5, 5, 5)), np.eye(3), offset=(1.000000001, 0, 0))
    assert calls == 1


def test_365_output_array_matches_allocating_path_and_refuses_overlap():
    v = np.random.default_rng(365).normal(size=(11, 9, 7))
    expected = vx.vol_affine(v, np.diag([0.9, 1.0, 1.1]), order=1)
    out = np.empty_like(expected)
    got = vx.vol_affine(v, np.diag([0.9, 1.0, 1.1]), order=1, output=out)
    assert got is out
    assert np.array_equal(got, expected)
    with pytest.raises(ValueError, match="overlap"):
        vx.vol_affine(v, np.eye(3), output=v)
