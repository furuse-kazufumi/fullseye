# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""hx_dist_rect2_points — contour 各点から最小面積外接矩形の辺までの平均距離。

2026-10-11 まで名前(HALCON ``dist_rectangle2_contour_points_xld``)に反して矩形を求めず、
点の重心からの平均距離を返していた。矩形の輪郭そのものでも 0 にならない(正方形で
約 0.57·辺長)ので、「矩形にどれだけ沿っているか」を測る用途では答えが逆を向いていた。
恒等式で固定する: 回した矩形の輪郭 → 0(角度を複数振る)/ 円 → (1 - (4/π)sin(π/4))·r /
内側に点を足すと増える / 退化入力は 0。
"""
import numpy as np
import pytest

import backends_halcon_ext as hx

_F = hx._dist_rectangle2_contour_points_xld


def _rect(cy, cx, w, h, th, n=50):
    t = np.linspace(0.0, 1.0, n, endpoint=False)
    pts = np.concatenate([
        np.c_[t * w - w / 2, -h / 2 + 0 * t], np.c_[w / 2 + 0 * t, t * h - h / 2],
        np.c_[w / 2 - t * w, h / 2 + 0 * t], np.c_[-w / 2 + 0 * t, h / 2 - t * h]])
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    return pts @ R.T + [cy, cx]


@pytest.mark.parametrize("th", [0.0, 0.3, 0.7, 1.2, 2.5])
def test_rotated_rectangle_outline_is_zero(th):
    v = {"shape": (100, 100), "cs": [_rect(50, 50, 40, 20, th)]}
    assert float(_F(v, 0.0, 0.0)) == pytest.approx(0.0, abs=1e-9)


def test_old_centroid_radius_would_not_be_zero():
    # 旧実装の値(重心からの平均距離)は正方形の輪郭で 0.57·辺長 —— 新実装との差を固定
    sq = _rect(50, 50, 40, 40, 0.0, 400)
    old = np.hypot(*(sq - sq.mean(0)).T).mean() / 100
    assert old > 0.2
    assert float(_F({"shape": (100, 100), "cs": [sq]}, 0.0, 0.0)) < 1e-9


@pytest.mark.parametrize("th", [0.0, 0.4, 1.1])
def test_circle_matches_closed_form(th):
    r = 30.0
    t = np.linspace(0, 2 * np.pi, 720, endpoint=False) + th
    c = np.c_[50 + r * np.sin(t), 50 + r * np.cos(t)]
    want = (1.0 - (4.0 / np.pi) * np.sin(np.pi / 4)) * r / 100
    assert float(_F({"shape": (100, 100), "cs": [c]}, 0.0, 0.0)) == pytest.approx(want, rel=2e-3)


def test_interior_points_increase_the_value():
    outline = _rect(50, 50, 40, 20, 0.5)
    inner = _rect(50, 50, 20, 10, 0.5)
    v0 = float(_F({"shape": (100, 100), "cs": [outline]}, 0.0, 0.0))
    v1 = float(_F({"shape": (100, 100), "cs": [outline, inner]}, 0.0, 0.0))
    assert v1 > v0 + 0.01


def test_a_b_unused_and_degenerate_inputs():
    v = {"shape": (100, 100), "cs": [_rect(40, 60, 30, 10, 0.2)]}
    assert float(_F(v, 0.0, 0.0)) == float(_F(v, 0.9, 0.1))
    assert float(_F({"shape": (10, 10), "cs": []}, 0.0, 0.0)) == 0.0
    assert float(_F({"shape": (10, 10), "cs": [np.array([[1.0, 1.0], [2.0, 2.0]])]}, 0, 0)) == 0.0
    line = np.array([[1.0, 1.0], [2.0, 2.0], [3.0, 3.0], [4.0, 4.0]])
    assert float(_F({"shape": (10, 10), "cs": [line]}, 0.0, 0.0)) == 0.0


def test_registered_op_uses_the_fixed_function():
    import ops
    o = next(o for o in ops.REGISTRY if o.name == "hx_dist_rect2_points")
    v = {"shape": (100, 100), "cs": [_rect(50, 50, 40, 20, 0.7)]}
    assert float(o.fn(v, 0.0, 0.0)) == pytest.approx(0.0, abs=1e-9)
