# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""寸法を持つ特徴は HALCON と同じ**画素値**で返すこと(2026-09-26)。

規約の選択(ユーザー判断): 「特徴は解像度に依らないよう正規化する」をやめ、
**同名は同じ数**を取る。正規化が要るなら利用者が画像サイズで割れるが、
**割った値から画素数は復元できない** —— 情報を捨てない側に倒した。

★この門は**閉形式で採点する**。30x70 の矩形なら面積は 2100、重心は画像中心、
厚みは 30、輪郭長は 196 —— どれも数えれば分かる値で、実装を実装と比べていない。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import ops  # noqa: E402

skm = pytest.importorskip("skimage.measure")
ndi = pytest.importorskip("scipy.ndimage")

_N = 200


def _rect(h, w, rot=0.0):
    reg = np.zeros((_N, _N))
    reg[_N // 2 - h // 2:_N // 2 + h // 2, _N // 2 - w // 2:_N // 2 + w // 2] = 1.0
    if rot:
        reg = (ndi.rotate(reg, rot, reshape=False, order=1) > 0.5).astype(np.float64)
    return reg


def _v(name, x):
    return np.ravel(np.asarray(ops.RT[name](x, 0.5, 0.5), np.float64))


def _contour(reg):
    return ops.RT["gen_contour_region_xld"](reg.copy(), 0.5, 0.5)


def _max_chord(reg):
    b = reg > 0.5
    st = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool)
    ys, xs = np.nonzero(b & ~ndi.binary_erosion(b, st))
    p = np.stack([ys, xs], 1).astype(float)
    return float(np.sqrt(((p[:, None, :] - p[None, :, :]) ** 2).sum(-1).max()))


# --------------------------------------------------------------------------- #
# 閉形式で採れるもの
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("h,w", [(30, 70), (16, 16), (8, 120)])
def test_area_center_is_pixels_not_a_fraction(h, w):
    """面積は画素数、重心は行・列(画像中心)。"""
    got = _v("area_center", _rect(h, w))
    assert got.shape == (3,)
    assert abs(got[0] - h * w) < 1e-9, "面積が %g(真値 %d)" % (got[0], h * w)
    assert abs(got[1] - (_N - 1) / 2.0) < 1.0 and abs(got[2] - (_N - 1) / 2.0) < 1.0


def test_contlength_is_the_perimeter_in_pixels():
    reg = _rect(30, 70)
    want = skm.regionprops((reg > 0.5).astype(int))[0].perimeter
    assert abs(_v("contlength", reg)[0] - want) < 1e-9


def test_get_region_thickness_is_pixels_and_no_longer_saturates():
    """★厚みが画像の長辺の半分を超える領域は、それまで全部 1.0 だった。"""
    assert abs(_v("get_region_thickness", _rect(30, 70))[0] - 30.0) < 1e-9
    wide = _v("get_region_thickness", _rect(150, 150))[0]
    assert wide > 100.0, "大きな領域の厚みが %g で頭打ちしている" % wide


def test_diameter_region_is_the_max_chord_in_pixels():
    """★量もスケールも違っていた(等面積円の直径を画像サイズで割っていた)。"""
    reg = _rect(30, 70)
    assert abs(_v("diameter_region", reg)[0] - _max_chord(reg)) < 1e-9


def test_the_two_diameter_ops_agree():
    """★直す前は**双子どうしで 5.6 倍**食い違っていた(0.2585 対 0.3788 / 量も別)。"""
    reg = _rect(30, 70)
    a = _v("diameter_region", reg)[0]
    b = _v("diameter_xld", _contour(reg))[0]
    assert abs(a - b) / a < 0.05, "領域版 %.3f と輪郭版 %.3f" % (a, b)


# --------------------------------------------------------------------------- #
# elliptic_axis —— 名前が約束している量を返す
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("h,w", [(30, 70), (20, 80), (16, 16)])
def test_elliptic_axis_returns_ra_rb_phi_in_pixels(h, w):
    reg = _rect(h, w)
    pr = skm.regionprops((reg > 0.5).astype(int))[0]
    got = _v("elliptic_axis", reg)
    assert got.shape == (3,), "3 成分でない: %s" % (got.shape,)
    assert abs(got[0] - pr.axis_major_length / 2.0) < 1e-9
    assert abs(got[1] - pr.axis_minor_length / 2.0) < 1e-9


def test_elliptic_axis_phi_follows_the_rotation():
    """★角は列軸から。30 度回した矩形は 30 度(符号つき)を返す。"""
    for deg in (-40, -20, 0, 25, 40):
        got = np.rad2deg(_v("elliptic_axis", _rect(20, 80, rot=deg))[2])
        diff = abs((got - (-deg) + 90) % 180 - 90)
        assert diff < 3.0, "%d 度回した矩形で Phi=%.2f 度" % (deg, got)


def test_the_two_elliptic_axis_ops_use_the_same_angle_convention():
    """★``cv2.fitEllipse`` の角は最初に返る軸(短軸)基準。忘れると 90 度ずれる。"""
    for deg in (0, 30, -20, 90):
        reg = _rect(20, 80, rot=deg) if deg != 90 else _rect(80, 20)
        a = np.rad2deg(_v("elliptic_axis", reg)[2])
        b = np.rad2deg(_v("elliptic_axis_xld", _contour(reg))[2])
        assert abs((a - b + 90) % 180 - 90) < 2.0, "region %.2f / xld %.2f" % (a, b)


def test_area_center_xld_is_pixels_too():
    reg = _rect(30, 70)
    got = _v("area_center_xld", _contour(reg))
    assert got.shape == (3,)
    assert abs(got[0] - 30 * 70) / (30 * 70) < 0.01, "面積 %g" % got[0]


# --------------------------------------------------------------------------- #
# 壊して確かめる
# --------------------------------------------------------------------------- #
def test_the_old_normalisation_is_what_the_gate_catches():
    """★正規化した値では上の門が落ちること(緩めていない)。"""
    reg = _rect(30, 70)
    normalised = (30 * 70) / float(reg.size)
    assert abs(normalised - 30 * 70) > 1.0, "正規化値と画素値が近い = 探針が弱い"
    assert abs(_v("area_center", reg)[0] - 30 * 70) < 1e-9


def test_a_bigger_image_does_not_change_a_pixel_measurement():
    """★画素値なら、同じ物体を大きな画像に置いても数は変わらない。

    正規化していた頃は**画像を広げるだけで数が変わっていた**。
    """
    small = np.zeros((120, 120))
    small[40:70, 20:90] = 1.0
    big = np.zeros((400, 400))
    big[40:70, 20:90] = 1.0
    for name in ("contlength", "get_region_thickness", "diameter_region"):
        a, b = _v(name, small)[0], _v(name, big)[0]
        assert abs(a - b) < 1e-9, "%s が画像の大きさで変わる: %g / %g" % (name, a, b)
    assert abs(_v("area_center", small)[0] - _v("area_center", big)[0]) < 1e-9
