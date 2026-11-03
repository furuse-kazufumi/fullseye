# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""HALCON の角の向き(elliptic_axis / orientation_xld / elliptic_axis_xld)と、エッジ・線輪郭の点の順序(2026-11-03).

真値はすべて閉形式:

* 角: 画面上で反時計回りに θ 回した棒(行は下向き)。HALCON の Phi は列軸から「mathematically positive」
  (gen_ellipse / gen_rectangle2 の説明) = 画面上で反時計回り。棒の主軸は θ。
* エッジ: 半径 r の円板のエッジ輪郭の長さは 2πr、囲む面積は πr²。
* 線: 長さ L の直線の中心線の長さは L(画素中心で L - 1)。

修正前の値(記録): 反時計回り 20 度の棒で elliptic_axis Phi = -0.348 rad、elliptic_axis_xld Phi = -0.3505 rad、
orientation_xld = 0.389(70 度)。r = 18 の円板で edges_sub_pix -> length_xld = 2508 px。幅 2 px・長さ 40 px の
傷で lines_gauss -> length_xld = 117 px。
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import ops  # noqa: E402

pytest.importorskip("skimage")
pytest.importorskip("cv2")
from scipy import ndimage  # noqa: E402

import backends_auto as BA  # noqa: E402

N = 128


def _v(name, x, a=0.5, b=0.5):
    return ops.RT[name](x, a, b)


def _bar(theta_deg, length=80.0, width=12.0):
    """画面上で反時計回りに theta 回した矩形(行は下向き): 主軸上の点は col が増えると row が減る。"""
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
    c = N / 2.0
    t = math.radians(theta_deg)
    u = (xx - c) * math.cos(t) - (yy - c) * math.sin(t)
    v = (xx - c) * math.sin(t) + (yy - c) * math.cos(t)
    return ((np.abs(u) <= length / 2) & (np.abs(v) <= width / 2)).astype(np.float64)


def _ang_diff_deg(a, b):
    """180 度を法とした差(線の向きの差)。"""
    return abs((a - b + 90.0) % 180.0 - 90.0)


ANGLES = (-75.0, -40.0, -10.0, 0.0, 15.0, 20.0, 45.0, 70.0, 89.0)


# --------------------------------------------------------------------------- #
# 角の向き
# --------------------------------------------------------------------------- #
def test_the_bar_construction_itself_turns_counter_clockwise_on_screen():
    """門の門: 45 度の棒は右上がり(列が増える側の端が上 = 行が小さい)。"""
    m = _bar(45.0) > 0.5
    ys, xs = np.nonzero(m)
    right = xs > N / 2 + 20
    assert ys[right].mean() < N / 2 - 10


@pytest.mark.parametrize("theta", ANGLES)
def test_elliptic_axis_phi_is_counter_clockwise_on_screen(theta):
    phi = float(np.asarray(_v("elliptic_axis", _bar(theta)))[2])
    assert -math.pi / 2 < phi <= math.pi / 2 + 1e-12
    assert _ang_diff_deg(math.degrees(phi), theta) < 1.0, (theta, math.degrees(phi))


@pytest.mark.parametrize("theta", ANGLES)
def test_elliptic_axis_agrees_with_orientation_region(theta):
    reg = _bar(theta)
    phi = math.degrees(float(np.asarray(_v("elliptic_axis", reg))[2]))
    o = float(_v("orientation_region", reg)) * 180.0
    assert _ang_diff_deg(phi, o) < 1e-6, (phi, o)


@pytest.mark.parametrize("theta", ANGLES)
def test_xld_angles_are_counter_clockwise_on_screen(theta):
    con = _v("gen_contour_region_xld", _bar(theta))
    o = float(_v("orientation_xld", con)) * 180.0
    phi = math.degrees(float(np.asarray(_v("elliptic_axis_xld", con))[2]))
    assert 0.0 <= o < 180.0
    assert _ang_diff_deg(o, theta) < 1.0, (theta, o)
    assert _ang_diff_deg(phi, theta) < 1.0, (theta, phi)
    assert -90.0 < phi <= 90.0


def test_a_rising_diagonal_has_positive_phi():
    """向きを構成に頼らず確かめる: 左下から右上へ走る線(行が減る)は Phi > 0。"""
    m = np.zeros((N, N))
    for k in range(-40, 41):
        r, c = N // 2 - k, N // 2 + k
        m[r - 2:r + 3, c - 2:c + 3] = 1.0
    phi = float(np.asarray(_v("elliptic_axis", m))[2])
    assert abs(math.degrees(phi) - 45.0) < 1.0
    con = _v("gen_contour_region_xld", m)
    assert abs(float(_v("orientation_xld", con)) * 180.0 - 45.0) < 1.0
    assert abs(math.degrees(float(np.asarray(_v("elliptic_axis_xld", con))[2])) - 45.0) < 1.0


# --------------------------------------------------------------------------- #
# edges_sub_pix: 1 画素幅・曲線に沿った順
# --------------------------------------------------------------------------- #
def _disk_img(r, cy=64.3, cx=63.6):
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
    m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
    return ndimage.gaussian_filter(0.2 + 0.6 * m, 1.0)


@pytest.mark.parametrize("r", [12.0, 18.0, 30.0])
def test_edges_sub_pix_contour_of_a_disk_has_its_circumference(r):
    con = _v("edges_sub_pix", _disk_img(r), 0.3)
    assert len(con["cs"]) == 1, [len(c) for c in con["cs"]]
    c = con["cs"][0]
    steps = np.hypot(*np.diff(c, axis=0).T)
    assert steps.max() < 2.0, steps.max()                  # 点が曲線に沿って並ぶ(ラスタの往復なし)
    assert np.allclose(c[0], c[-1])                        # 閉じたエッジは閉じて返る
    L = float(_v("length_xld", con))
    assert abs(L - 2 * math.pi * r) / (2 * math.pi * r) < 0.02, (L, 2 * math.pi * r)
    area = float(np.asarray(_v("area_center_xld", con))[0])
    assert abs(area - math.pi * r * r) / (math.pi * r * r) < 0.03, (area, math.pi * r * r)
    assert float(_v("circularity_xld", con)) > 0.95


def test_edges_sub_pix_points_sit_on_the_circle():
    r, cy, cx = 20.0, 64.3, 63.6
    c = _v("edges_sub_pix", _disk_img(r, cy, cx), 0.3)["cs"][0]
    d = np.hypot(c[:, 0] - cy, c[:, 1] - cx)
    assert abs(float(np.median(d)) - r) < 0.3
    assert float(np.max(np.abs(d - r))) < 0.8


def test_edges_sub_pix_straight_edge_is_one_thin_line():
    """縦の段差 1 本 -> 1 画素幅の輪郭 1 本、点数 = 行数ほど、長さ = 行数 - 1 ほど。"""
    img = np.zeros((64, 64))
    img[:, 30:] = 1.0
    img = ndimage.gaussian_filter(img, 1.0)
    con = _v("edges_sub_pix", img, 0.3)
    assert len(con["cs"]) == 1
    c = con["cs"][0]
    assert 60 <= len(c) <= 64, len(c)
    assert abs(float(_v("length_xld", con)) - (len(c) - 1)) < 1.0
    assert np.all(np.abs(c[:, 1] - 29.5) < 0.2)


# --------------------------------------------------------------------------- #
# lines_gauss: 既定は不変、b >= 0.75 で中心線
# --------------------------------------------------------------------------- #
def _scratch(L, theta_deg=0.0, width=2.0):
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
    c = N / 2.0
    t = math.radians(theta_deg)
    u = (xx - c) * math.cos(t) - (yy - c) * math.sin(t)
    v = (xx - c) * math.sin(t) + (yy - c) * math.cos(t)
    m = (np.abs(u) <= L / 2) & (np.abs(v) <= width / 2)
    g = np.random.default_rng(3)
    return np.clip(0.6 - 0.3 * m + 0.02 * g.standard_normal((N, N)), 0, 1)


@pytest.mark.parametrize("L,theta", [(40.0, 0.0), (60.0, 0.0), (60.0, 30.0), (50.0, -60.0)])
def test_lines_gauss_centre_line_mode_measures_the_line_length(L, theta):
    con = _v("lines_gauss", _scratch(L, theta), 0.5, 1.0)
    assert len(con["cs"]) == 1, [len(c) for c in con["cs"]]
    c = con["cs"][0]
    assert np.hypot(*np.diff(c, axis=0).T).max() < 2.0
    got = float(_v("length_xld", con))
    assert abs(got - L) < 0.06 * L, (L, theta, got)
    # 中心線は線の軸の上(画像中心を通る、向き theta の直線からの距離)。端の 3 点は細線化で角へ曲がる
    # (実測 0.8〜0.9 px)ので、軸の上を言うのは内側の点だけ。
    t = math.radians(theta)
    dist = np.abs((c[:, 1] - N / 2.0) * math.sin(t) + (c[:, 0] - N / 2.0) * math.cos(t))
    assert float(np.median(dist)) < 0.1, float(np.median(dist))
    assert float(np.max(dist[3:-3])) < 0.5, float(np.max(dist[3:-3]))


def test_lines_gauss_default_mode_is_unchanged():
    """既定 b = 0.5 は帯の画素を np.where の順に並べた旧来の出力と 1 ビットも違わない。"""
    from skimage import filters as skf
    x = _scratch(40.0)
    got = _v("lines_gauss", x, 0.5, 0.5)
    r = BA._norm(skf.frangi(x, sigmas=range(1, 4)))
    lab, n = ndimage.label(r > 0.3, structure=np.ones((3, 3)))
    ref = [np.stack(np.where(lab == i), 1).astype(np.float64) for i in range(1, n + 1)]
    ref = [c for c in ref if len(c) >= 3]
    assert len(got["cs"]) == len(ref)
    for a, b in zip(got["cs"], ref):
        assert np.array_equal(a, b)


# --------------------------------------------------------------------------- #
# 鎖を繋ぐ部品
# --------------------------------------------------------------------------- #
def test_link_chains_closes_a_loop_and_splits_at_a_junction():
    ring = np.zeros((20, 20), bool)
    ring[5, 5:15] = ring[14, 5:15] = ring[5:15, 5] = ring[5:15, 14] = True
    cs = BA._link_chains(ring)
    assert len(cs) == 1 and np.array_equal(cs[0][0], cs[0][-1])
    assert len(cs[0]) == int(ring.sum()) + 1
    assert np.hypot(*np.diff(cs[0], axis=0).T).max() <= math.sqrt(2) + 1e-9

    tee = np.zeros((20, 20), bool)
    tee[5, 2:18] = True
    tee[6:15, 10] = True
    cs = BA._link_chains(tee)
    assert sum(len(c) for c in cs) == int(tee.sum())        # 画素は 1 度ずつ
    for c in cs:
        assert np.hypot(*np.diff(c, axis=0).T).max() <= math.sqrt(2) + 1e-9   # 分岐で飛ばない
