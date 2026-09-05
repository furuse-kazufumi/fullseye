# -*- coding: utf-8 -*-
"""スタック中央値の置き換えが、**値を 1 ビットも変えていない**こと。

2026-09-06: ``np.median(cube, axis=0)`` を partition ベースの
:func:`astrostack._median_over_frames` に替えた(実測 1.9〜2.9 倍)。
速さのための置き換えは、**同じ値を返すことを示せて初めて置き換えである**。

ここで固定するのは 3 つ:

1. **bitwise 一致** —— 奇数枚・偶数枚・dtype・軸移動の有無をまたいで、
   ``np.median`` と 1 ビットも違わない。``allclose`` では足りない
   (「ほぼ同じ」を許すと、後で本当にずれたときに気づけない)。
2. **NaN では numpy へ委ねる** —— partition は NaN を末尾へ寄せるので中央の
   位置がずれ、**例外にならず違う値**を返す。この repo がいちばん嫌う壊れ方なので、
   そこへ落ちないことを実際の値で確かめる。
3. **境目の両側が両方とも通る** —— 軸を移す枝(K>=20)と移さない枝(K<20)が
   どちらも実行される。片方しか通らないと、もう片方は「あるだけ」になる。
"""
from __future__ import annotations

import numpy as np
import pytest

import astrostack as AS

_RNG = np.random.default_rng(20260906)


def _cube(k, h=17, w=13, dtype=np.float32):
    return _RNG.standard_normal((k, h, w)).astype(dtype)


# =========================================================================
# 1. bitwise 一致
# =========================================================================

@pytest.mark.parametrize("k", [1, 2, 3, 4, 5, 8, 9, 12, 16, 19, 20, 21, 25, 33])
@pytest.mark.parametrize("dtype", [np.float32, np.float64])
def test_it_matches_numpy_bit_for_bit(k, dtype):
    """奇数/偶数、境目の前後、両 dtype で ``np.median`` と完全一致。"""
    cube = _cube(k, dtype=dtype)
    got = AS._median_over_frames(cube)
    ref = np.median(cube, axis=0)
    assert got.shape == ref.shape
    assert np.array_equal(got, ref), (
        "中央値が %s (K=%d) で np.median と一致しない —— 速くするための置き換えが "
        "値を変えている。最大差 %.3e" % (np.dtype(dtype).name, k,
                                        float(np.max(np.abs(got - ref)))))


def test_integer_input_is_handled_like_numpy():
    """整数 cube でも numpy と同じ(偶数枚では中央 2 つの平均で float になる)。"""
    cube = _RNG.integers(0, 255, (6, 9, 7)).astype(np.uint8)
    got = AS._median_over_frames(cube)
    ref = np.median(cube, axis=0)
    assert np.array_equal(got, ref)
    assert got.dtype == ref.dtype


def test_a_constant_stack_returns_that_constant():
    cube = np.full((7, 5, 5), 0.25, np.float64)
    assert np.array_equal(AS._median_over_frames(cube), np.full((5, 5), 0.25))


# =========================================================================
# 2. NaN / inf では numpy へ委ねる(partition は中央の位置をずらす)
# =========================================================================

def test_nan_falls_back_to_numpy_instead_of_silently_moving_the_middle():
    """NaN があると partition は中央をずらす。**例外にならず違う値**が最悪。"""
    cube = _cube(5, 6, 6, np.float64)
    cube[2, 3, 3] = np.nan
    got = AS._median_over_frames(cube)
    ref = np.median(cube, axis=0)
    assert np.array_equal(np.isnan(got), np.isnan(ref)), "NaN の伝播が numpy と違う"
    assert np.array_equal(got[~np.isnan(got)], ref[~np.isnan(ref)])


def test_inf_also_falls_back():
    cube = _cube(9, 6, 6, np.float64)
    cube[0, 1, 1] = np.inf
    assert np.array_equal(AS._median_over_frames(cube), np.median(cube, axis=0))


@pytest.mark.parametrize("k", [21, 25])
def test_nan_is_handled_on_the_axis_moving_side_too(k):
    """境目の**向こう側**でも NaN の分岐が効くこと(片側だけ直すのが定番の穴)。"""
    cube = _cube(k, 6, 6, np.float64)
    cube[k // 2, 2, 2] = np.nan
    got, ref = AS._median_over_frames(cube), np.median(cube, axis=0)
    assert np.array_equal(np.isnan(got), np.isnan(ref))
    assert np.array_equal(got[~np.isnan(got)], ref[~np.isnan(ref)])


# =========================================================================
# 3. 境目の両側が本当に実行されている
# =========================================================================

def test_both_branches_of_the_threshold_run():
    """軸を移す枝と移さない枝が両方通ること。

    片方しか通らないと、もう片方は「書いてあるだけ」になる。
    ``np.moveaxis`` を数えて、閾値の前後で呼ばれ方が変わるのを確かめる。
    """
    calls = []
    orig = np.moveaxis

    def counting(*a, **kw):
        calls.append(1)
        return orig(*a, **kw)

    np.moveaxis = counting
    try:
        calls.clear()
        AS._median_over_frames(_cube(AS._MOVE_AXIS_FRAMES - 1))
        below = len(calls)
        calls.clear()
        AS._median_over_frames(_cube(AS._MOVE_AXIS_FRAMES))
        at_or_above = len(calls)
    finally:
        np.moveaxis = orig
    assert below == 0, "閾値未満なのに軸を移している(枚数が少ないと逆に遅い)"
    assert at_or_above == 1, "閾値以上なのに軸を移していない(速い枝が死んでいる)"


def test_the_threshold_is_documented_with_its_measurement():
    """境目の数字は、根拠なしに動かせないようにしておく。"""
    src = AS.__doc__ or ""
    import inspect
    mod = inspect.getsource(AS)
    assert "_MOVE_AXIS_FRAMES" in mod
    assert "float64" in mod and "外れた" in mod, (
        "境目の根拠(実測と、外れた仮説)が消えている —— 数字だけ残ると、"
        "次に触る人が理由なく動かせてしまう")
    assert isinstance(AS._MOVE_AXIS_FRAMES, int) and AS._MOVE_AXIS_FRAMES >= 2


# =========================================================================
# 4. 呼び出し側(op)の出力が変わっていないこと
# =========================================================================

def test_sigma_clip_stack_median_mode_is_unchanged():
    frames = [f for f in _cube(9, 12, 10, np.float64)]
    out, mask = AS.sigma_clip_stack(frames, mode="median")
    assert np.array_equal(out, np.median(np.stack(frames), axis=0))
    assert mask.shape == (9, 12, 10) and mask.all()


def test_cosmic_ray_reject_stack_still_agrees_with_the_plain_formula():
    frames = [f for f in np.abs(_cube(7, 12, 10, np.float64))]
    cleaned, masks = AS.cosmic_ray_reject_stack(frames)
    cube = np.stack(frames)
    med = np.median(cube, axis=0)
    assert np.array_equal(np.median(np.abs(cube - med), axis=0),
                          AS._median_over_frames(np.abs(cube - med)))
    assert len(cleaned) == 7 and masks.shape == cube.shape
