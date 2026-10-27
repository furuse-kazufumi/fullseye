# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""傾けた像面(``image_tilt``)の上の座標の門。

``noncoaxial_trace`` / ``noncoaxial_spot`` の ``image_xy`` は、傾いた像面そのものの局所座標でなければならない
(傾いた受光素子の上の距離。シャインプルーフの撮像素子の計測に使う)。2026-10-24 までは傾けない面へ射影した
座標を返し、傾けた向きの長さと RMS が cos θ' 倍に縮んでいた。

真値は raytrace3d を通さない閉形式: 軸に平行な光線(無限遠の軸上の物体、屈折しない窓)は絞りの点 (x, y) のまま
進み、傾けた像面 ``z = x·tan(ty) + y·tan(tx)`` に当たる。単軸の傾き tx なら面の上の座標は (x, y/cos tx)、
ty なら (x/cos ty, y)。RMS は瞳の格子 (px, py) から ``ap·√(⟨px²⟩/cx² + ⟨py²⟩/cy²)``。2 軸の傾きでは等長性
(面の上の 2 点の 3-D 距離 = 局所座標の距離)と、収差のある系(シャインプルーフの例)の RMS = 大域の 3-D 点の
RMS を独立の経路で確かめる。乱数は引かない。
"""
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import raytrace as RT  # noqa: E402
import raytrace3d as R3  # noqa: E402

AP = 5.0


def _window(tilt):
    return R3.noncoaxial_system([{"R": math.inf, "t": 50.0, "n": 1.0, "ap": AP}], stop=0, image_tilt=tilt)


@pytest.mark.parametrize("tilt", [(30.0, 0.0), (0.0, 40.0), (-25.0, 0.0), (0.0, 0.0)])
def test_tilted_image_xy_is_on_the_tilted_plane(tilt):
    """単軸の傾き: 局所座標 = (x/cos ty, y/cos tx)、既知の 2 点の距離 = 2a/cos θ'。"""
    rings = 4
    tr = R3.noncoaxial_trace(_window(tilt), rings=rings)["fields"][0]
    px, py = RT._pupil_grid(rings)
    cy, cx = math.cos(math.radians(tilt[0])), math.cos(math.radians(tilt[1]))
    want = np.stack([AP * px / cx, AP * py / cy], 1)
    assert tr["valid"].all()
    assert np.abs(tr["image_xy"] - want).max() < 1e-9
    # 瞳の縁の上下の 2 点(py = ±1)と左右の 2 点(px = ±1)の距離
    iy = [int(np.argmin((px - 0.0) ** 2 + (py - s) ** 2)) for s in (1.0, -1.0)]
    ix = [int(np.argmin((px - s) ** 2 + (py - 0.0) ** 2)) for s in (1.0, -1.0)]
    dy = np.linalg.norm(tr["image_xy"][iy[0]] - tr["image_xy"][iy[1]])
    dx = np.linalg.norm(tr["image_xy"][ix[0]] - tr["image_xy"][ix[1]])
    assert abs(dy - 2.0 * AP / cy) < 1e-9 and abs(dx - 2.0 * AP / cx) < 1e-9


@pytest.mark.parametrize("tilt", [(30.0, 0.0), (0.0, 40.0), (-20.0, 0.0)])
def test_tilted_image_rms_matches_closed_form(tilt):
    rings = 6
    sp = R3.noncoaxial_spot(_window(tilt), rings=rings)
    px, py = RT._pupil_grid(rings)
    cy, cx = math.cos(math.radians(tilt[0])), math.cos(math.radians(tilt[1]))
    want = AP * math.sqrt(np.mean((px / cx) ** 2) + np.mean((py / cy) ** 2))
    assert abs(sp["rms_radius"] - want) < 1e-9 * want
    flat = AP * math.sqrt(np.mean(px ** 2) + np.mean(py ** 2))
    assert sp["rms_radius"] > flat * (1.0 + 1e-3)        # 射影(旧挙動)なら flat と一致して赤


@pytest.mark.parametrize("tilt", [(30.0, 20.0), (-15.0, 35.0)])
def test_compound_tilt_is_an_isometry_and_layout_reports_the_tilted_pose(tilt):
    tr = R3.noncoaxial_trace(_window(tilt), rings=4)["fields"][0]
    P = tr["points"][:, -1, :]
    xy = tr["image_xy"]
    d3 = np.linalg.norm(P[:, None, :] - P[None, :, :], axis=2)
    d2 = np.linalg.norm(xy[:, None, :] - xy[None, :, :], axis=2)
    assert np.abs(d3 - d2).max() < 1e-9
    gx, gy = math.tan(math.radians(tilt[1])), math.tan(math.radians(tilt[0]))
    n = np.array([-gx, -gy, 1.0]) / math.sqrt(1.0 + gx * gx + gy * gy)
    lay = R3.noncoaxial_layout(_window(tilt))
    assert np.abs(np.array(lay["image"]["normal"]) - n).max() < 1e-12
    Rimg = np.array(lay["image"]["rotation"])
    assert np.abs(Rimg.T @ Rimg - np.eye(3)).max() < 1e-12 and np.linalg.det(Rimg) > 0
    # 像の点は面の上(局所の z = 0)
    loc = (P - np.array(lay["image"]["origin"])) @ Rimg
    assert np.abs(loc[:, 2]).max() < 1e-9


def test_scheimpflug_spot_rms_equals_the_rms_of_the_global_points():
    """収差のある系: RMS は像面の上の大域の 3-D 点の RMS(面の上の点は同一平面なので一致する)。"""
    s = R3.noncoaxial_example("scheimpflug")
    assert s["image_tilt"][0] != 0.0
    for h in (-3.0, 0.0, 3.0):
        sp = R3.noncoaxial_spot(s, field=(0.0, h), rings=4)
        b = R3._bundle(s, (0.0, h), rings=4)
        P = b["points"][b["valid"], -1, :]
        rms3 = math.sqrt(np.mean(np.sum((P - P.mean(0)) ** 2, 1)))
        assert abs(sp["rms_radius"] - rms3) < 1e-9 * rms3
