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


# ---- 2026-09-03 描画バグ回帰 ------------------------------------------------- #
def test_wholly_outside_line_lights_nothing():
    """回帰: 画面外のサンプルを縁にクランプしていたため、完全に画面外の線でも
    縁に画素が点いていた(10 画素)。"""
    z = np.zeros((20, 20))
    assert D.draw_line(z, (-10, -10), (-1, -5), 1.0).sum() == 0
    assert D.draw_polyline(z, [(25, 3), (30, 30), (40, 5)], 1.0, closed=True).sum() == 0
    assert D.draw_markers(z, [(-8, -8)], 1.0, size=3, shape="cross").sum() == 0
    assert D.draw_markers(z, [(30, 30)], 1.0, size=3, shape="square").sum() == 0
    assert D.draw_contour(z, np.array([[-5.0, -5.0], [-9.0, -2.0], [-3.0, -8.0]]), 1.0).sum() == 0


def test_corner_crossing_line_lights_only_the_inframe_segment():
    """(10,-5)→(25,10) は x = y + 15 上を走り、枠 20×20 には (15,0)…(19,4) の
    5 画素だけが入る。クランプ方式は縁に L 字を作っていた。"""
    m = D.draw_line(np.zeros((20, 20)), (10, -5), (25, 10), 1.0) > 0.5
    ys, xs = np.nonzero(m)
    assert m.sum() == 5
    assert np.array_equal(xs - ys, np.full(5, 15))             # 線上のみ
    assert m[0, :15].sum() == 0 and m[5:, 19].sum() == 0       # 縁に沿った偽の画素なし


def test_rgb_colour_on_rgba_image_keeps_alpha():
    """回帰: 色を足りないチャンネル分ゼロ埋めしていたので RGB 色で描くと alpha=0。"""
    img = np.ones((7, 7, 4))
    out = D.draw_line(img, (0, 3), (6, 3), color=(1.0, 0.0, 0.0))
    assert out[3, 3].tolist() == [1.0, 0.0, 0.0, 1.0]
    out = D.draw_circle(img, (3, 3), 2, color=(0.0, 1.0, 0.0), fill=True)
    assert out[3, 3].tolist() == [0.0, 1.0, 0.0, 1.0]
    out = D.draw_markers(img, [(3, 3)], color=(0.0, 0.0, 1.0), size=2, shape="cross")
    assert out[3, 3].tolist() == [0.0, 0.0, 1.0, 1.0]
    # スカラ色は従来どおり全チャンネル(alpha 含む)に入る
    assert D.draw_line(img, (0, 3), (6, 3), color=0.5)[3, 3].tolist() == [0.5] * 4


def test_fractional_endpoints_give_8_connected_lines():
    """回帰: サンプル数を int() で切り捨てていたので小数端点の線に穴が空いた。"""
    m = D._line_mask((5, 5), (0.4, 2), (2.3, 2))
    assert m[2].astype(int).tolist() == [1, 1, 1, 0, 0]        # 中央画素が抜けない
    m = D._line_mask((12, 32), (0.5, 0.5), (30.49, 10.2))
    lab, n = ndimage.label(m, structure=np.ones((3, 3)))
    assert n == 1                                              # 8 連結で 1 本
    assert m[0, 0] and m[10, 30]                               # 両端(丸め)が点く
    assert m.sum() == 31                                       # 支配軸 30 px + 1


def test_even_width_draws_exactly_width_pixels():
    """回帰: 偶数幅が w+1 画素(width=2 で 3 行)になっていた。奇数幅は不変。"""
    for w, rows in ((1, [10]), (2, [9, 10]), (3, [9, 10, 11]),
                    (4, [8, 9, 10, 11]), (5, [8, 9, 10, 11, 12])):
        out = D.draw_line(np.zeros((20, 30)), (2, 10), (27, 10), 1.0, width=w)
        assert np.nonzero(out.any(axis=1))[0].tolist() == rows, w
        assert out[rows, :][:, 6:24].min() > 0.5               # 帯の中は隙間なし(端のキャップは除く)
    # 縦線も同じ(−x 側に寄る)
    out = D.draw_line(np.zeros((30, 20)), (10, 2), (10, 27), 1.0, width=2)
    assert np.nonzero(out.any(axis=0))[0].tolist() == [9, 10]
