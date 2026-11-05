# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""敵対的検証 2026-11-05(担当の範囲外として残った 3 件 = leftovers)の回帰テスト。

各テストは報告の再現を「真値・不変量・独立実装」と比べる形にしてある。

* L1 ``complexops._wrap`` / ``carpath._wrap`` の値域 ``(-pi, pi]``(兄弟は ``fringe.wrapped_phase``)
* L2 ``ph_total_variation_flow`` の反復を増やすと誤差が増える
* L3 MCP ``fullseye_find_ops`` の ``limit`` が単調でない
"""
from __future__ import annotations

import math

import numpy as np
import pytest

# ---- L1: 角度を (-pi, pi] に折る関数の境界 ---------------------------------

#: pi の奇数倍。どれも +pi に折れるのが (-pi, pi] の約束。
_ODD_PI = [k * math.pi for k in (-5, -3, -1, 1, 3, 5)]


def _check_wrap_interval(values, wrapped):
    """値域 (-pi, pi] と「差が 2pi の整数倍」(同じ角度のまま)を両方見る。"""
    values = np.asarray(values, dtype=np.float64)
    wrapped = np.asarray(wrapped, dtype=np.float64)
    assert values.size == wrapped.size and values.size > 0
    assert (wrapped > -math.pi).all(), wrapped[wrapped <= -math.pi]
    assert (wrapped <= math.pi).all(), wrapped[wrapped > math.pi]
    turns = (values - wrapped) / (2.0 * math.pi)
    assert np.abs(turns - np.round(turns)).max() < 1e-9


def test_l1_complexops_wrap_maps_odd_multiples_of_pi_to_plus_pi():
    import complexops

    out = complexops._wrap(np.array(_ODD_PI))
    assert len(_ODD_PI) == 6
    # 真値: pi の奇数倍は全部 +pi(修正前は -pi / 3pi / -5pi... が -pi になっていた)
    assert np.allclose(out, math.pi, atol=1e-12), out
    _check_wrap_interval(_ODD_PI, out)


def test_l1_carpath_wrap_maps_odd_multiples_of_pi_to_plus_pi():
    import carpath

    out = [carpath._wrap(v) for v in _ODD_PI]
    assert len(out) == 6
    # 修正前は floor の式で pi そのものが -pi になっていた
    assert all(abs(v - math.pi) < 1e-12 for v in out), out
    _check_wrap_interval(_ODD_PI, out)


@pytest.mark.parametrize("mod", ["complexops", "carpath"])
def test_l1_wrap_interval_on_random_and_boundary_values(mod):
    """乱数 + 境界の近傍(nextafter)でも値域と同値性を守る。独立実装 np.angle と一致(境界以外)。"""
    import importlib

    m = importlib.import_module(mod)
    rng = np.random.default_rng(20261105)
    vals = np.concatenate([rng.uniform(-60.0, 60.0, 4000),
                           [np.nextafter(-math.pi, 0.0), np.nextafter(math.pi, 4.0),
                            -1e-300, 0.0, 1e-17]])
    if mod == "complexops":
        out = m._wrap(vals)
    else:
        out = np.array([m._wrap(float(v)) for v in vals])
    assert out.shape == vals.shape
    _check_wrap_interval(vals, out)
    # 独立実装(複素数の偏角)と、境界から離れた点で一致
    ref = np.angle(np.exp(1j * vals))
    far = np.abs(np.abs(ref) - math.pi) > 1e-6
    assert far.sum() > 3900
    assert np.abs(out[far] - ref[far]).max() < 1e-9


def test_l1_phase_unwrap_is_blind_to_the_pi_minus_pi_spelling():
    """呼び出し側の期待: 同じ位相を +pi と書いても -pi と書いても展開結果は同じ。"""
    import complexops

    y, x = np.mgrid[:16, :16]
    ramp = (x + y) * (np.pi / 4)                    # pi/4 刻み → 多くの画素がちょうど ±pi
    w = np.angle(np.exp(1j * ramp))
    edge = np.isclose(np.abs(w), np.pi)
    assert edge.sum() > 10
    plus = complexops.phase_unwrap(np.where(edge, np.pi, w))
    minus = complexops.phase_unwrap(np.where(edge, -np.pi, w))
    assert np.array_equal(plus, minus)
    assert np.ptp(plus - ramp) < 1e-9               # 真値の傾斜を定数の差だけで戻す


# ---- L2: ph_total_variation_flow は反復を増やしても誤差が育たない ----------------


def _tv_scenes():
    """区分定数の真値 3 枚(正方形 + 端の細い帯 / 縦の段差 / 大小の円板)。"""
    sq = np.full((64, 64), 0.3)
    sq[16:48, 16:48] = 0.7
    sq[:, :8] = 0.1
    step = np.where(np.arange(48)[None, :] < 24, 0.3, 0.7) * np.ones((48, 48))
    y, x = np.mgrid[:64, :64]
    disk = (0.2 + 0.5 * ((x - 32) ** 2 + (y - 32) ** 2 < 12 ** 2)
            + 0.2 * ((x - 10) ** 2 + (y - 50) ** 2 < 5 ** 2))
    return [("square", sq), ("step", step), ("disks", disk)]


def _rmse(a, b):
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))


_TV_CASES = [(name, sig, b) for name, _ in _tv_scenes() for sig in (0.05, 0.1)
             for b in (0.0, 0.5, 1.0)]


@pytest.mark.parametrize("name,sigma,b", _TV_CASES)
def test_l2_tv_flow_error_does_not_grow_with_more_steps(name, sigma, b):
    """真値 = 雑音を足す前の区分定数画像。a(反復数)を 0〜1 に振る。

    修正前(lam 0.02..0.22)は a=1 の誤差が a=0.1 の 3 倍以上になり、雑音の入力より
    悪かった(正方形・sigma 0.05・b=0 で 0.067 > 0.050)。
    """
    import backends_physics as P

    truth = dict(_tv_scenes())[name]
    noisy = np.clip(truth + np.random.default_rng(3).normal(0.0, sigma, truth.shape), 0.0, 1.0)
    e_in = _rmse(noisy, truth)
    a_grid = np.linspace(0.0, 1.0, 11)
    errs = [_rmse(P.ph_total_variation_flow(noisy, float(a), b), truth) for a in a_grid]
    assert len(errs) == 11
    # 雑音除去になっている: a>0 のどこでも入力の誤差の 3/4 未満
    assert max(errs[1:]) < 0.75 * e_in, (errs, e_in)
    # 反復を増やして悪化しない: 最後(a=1)は途中の最良の 1.25 倍以内
    assert errs[-1] <= 1.25 * min(errs), errs
    # 走り続けて育たない: どの a でも、それまでの最良からの上がり幅は入力誤差の 1/8 以下
    rise = max(errs[i] - min(errs[: i + 1]) for i in range(len(errs)))
    assert rise <= e_in / 8.0, (rise, errs)


@pytest.mark.parametrize("b", [0.0, 0.5, 1.0])
def test_l2_tv_flow_reaches_a_fixed_point_and_keeps_clean_input(b):
    """不変量: 雑音の無い区分定数画像はほぼそのまま(修正前は a=1 で RMSE 0.067)、
    かつ a=0.8 と a=1 の出力が一致する(ROF の最小点 = 不動点に着いている)。"""
    import backends_physics as P

    truth = dict(_tv_scenes())["square"]
    assert _rmse(P.ph_total_variation_flow(truth, 1.0, b), truth) < 0.025
    noisy = np.clip(truth + np.random.default_rng(5).normal(0.0, 0.1, truth.shape), 0.0, 1.0)
    late = P.ph_total_variation_flow(noisy, 1.0, b)
    earlier = P.ph_total_variation_flow(noisy, 0.8, b)
    assert float(np.abs(late - earlier).max()) < 1e-3
