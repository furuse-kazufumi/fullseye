# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""imagedraw のGTテスト: 座標どおりに焼け、入力を壊さないこと。"""
import numpy as np
import pytest
from scipy import ndimage

import imagedraw as D


def test_input_is_not_mutated():
    img = np.zeros((40, 40))
    D.draw_line(img, (0, 0), (39, 39), 1.0)
    assert img.max() == 0.0                       # 元は不変


def test_markers_land_at_points_one_component_each():
    img = np.zeros((100, 120))
    pts = [(30, 40), (80, 60), (55, 85)]
    out = D.draw_markers(img, pts, color=1.0, size=4, shape="cross", width=1)
    lab, n = ndimage.label(out > 0.5)
    assert n == len(pts)
    centers = ndimage.center_of_mass(out > 0.5, lab, range(1, n + 1))  # (row,col)
    got = sorted((c, r) for r, c in centers)
    for (gx, gy), (wx, wy) in zip(got, sorted(pts)):
        assert abs(gx - wx) < 3 and abs(gy - wy) < 3


def test_line_endpoints_set_offline_clear():
    L = D.draw_line(np.zeros((50, 50)), (5, 5), (40, 40), 1.0, 1)
    assert L[5, 5] > 0.5 and L[40, 40] > 0.5
    assert L[5, 45] < 0.5                          # 線外


def test_circle_outline_vs_fill():
    C = D.draw_circle(np.zeros((80, 80)), (40, 40), 20, 1.0, width=1, fill=False)
    assert C[40, 60] > 0.5 and C[40, 40] < 0.5     # 縁は塗り、中心は空
    Cf = D.draw_circle(np.zeros((80, 80)), (40, 40), 20, 1.0, fill=True)
    assert Cf[40, 40] > 0.5                         # 塗り潰しは中心も塗る


def test_polyline_closed_is_a_polygon():
    P = D.draw_polyline(np.zeros((60, 60)), [(10, 10), (50, 10), (50, 50), (10, 50)],
                        1.0, width=1, closed=True)
    # 4 辺すべてに画素がある(閉路)
    assert P[10, 30] > 0.5 and P[50, 30] > 0.5 and P[30, 10] > 0.5 and P[30, 50] > 0.5


def test_color_image_uses_channel_color():
    ci = np.zeros((60, 60, 3))
    co = D.draw_markers(ci, [(30, 30)], color=(1, 0, 0), size=5, shape="square", width=2)
    r, c = 25, 30
    assert co[r, c, 0] > 0.9 and co[r, c, 1] < 0.1 and co[r, c, 2] < 0.1


def test_draw_contour_from_xld():
    import contours_xld as X
    xld = X.gen_circle_contour_xld(40, 40, 15, n=60, shape=(80, 80))
    CC = D.draw_contour(np.zeros((80, 80)), xld, 1.0, 1)
    assert (CC > 0.5).sum() > 20                    # 輪郭が描かれている


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        D.draw_line(np.zeros((5, 5, 5, 5)), (0, 0), (1, 1))     # ndim 不正
    with pytest.raises(ValueError):
        D.draw_markers(np.zeros((20, 20)), [(1, 1)], shape="triangle")  # 未知shape
