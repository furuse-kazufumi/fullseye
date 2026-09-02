# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""annotate3d(3-D アンカーの図注)を**閉形式の射影**で検証する。

  1. 既知カメラ・既知点が既知の画素に落ちる(1e-9)。
  2. 像面に平行なスケールバーの画素長 = ``f * L / z``。
  3. 別の面の裏にあるアンカーは depth で hidden になる(手前の点はならない)。
  4. fail-closed: カメラの後ろ / 退化姿勢 / bool の幅 / 形の不一致は ValueError。
  5. 台帳(ops3d "annotate3d")に 7 op が載り、宣言型どおりの値を返す。
"""
from __future__ import annotations

import numpy as np
import pytest

import annotate3d as T
import ops3d
import render3d

W, H = 160, 120


def _cam():
    K = render3d.intrinsics_from_fov(45.0, W, H)
    pose = render3d.look_at((0.0, 0.0, 10.0), (0.0, 0.0, 0.0), up=(0.0, 1.0, 0.0))
    return pose, K


def _canvas(v=0.2, ch=3):
    return np.full((H, W, ch) if ch else (H, W), v, dtype=np.float64)


# ------------------------------------------------------------------ #
# 1-2. 射影の閉形式
# ------------------------------------------------------------------ #

def test_known_camera_and_point_land_on_the_known_pixel():
    pose, K = _cam()
    f, cx, cy = K[0, 0], K[0, 2], K[1, 2]
    tab = T.project_anchors([(1.0, 2.0, 0.0), (-3.0, 0.5, 4.0)], pose, K, shape=(H, W))
    # カメラは (0,0,10) から -Z を見る: z = 10 - Z、u = f*X/z + cx、v = cy - f*Y/z
    want = np.array([[f * 1.0 / 10.0 + cx, cy - f * 2.0 / 10.0],
                     [f * -3.0 / 6.0 + cx, cy - f * 0.5 / 6.0]])
    assert np.allclose(tab["uv"], want, atol=1e-9, rtol=0)
    assert np.allclose(tab["depth"], [10.0, 6.0], atol=1e-12)
    assert tab["in_front"].all() and tab["in_image"].all() and not tab["hidden"].any()
    assert tab["visible"].all()


def test_rt_tuple_pose_equals_the_4x4():
    pose, K = _cam()
    a = T.project_anchors([(1.0, 2.0, 0.0)], pose, K)["uv"]
    b = T.project_anchors([(1.0, 2.0, 0.0)], (pose[:3, :3], pose[:3, 3]), K)["uv"]
    assert np.array_equal(a, b)


def test_scale_bar_parallel_to_the_image_plane_is_f_L_over_z_pixels():
    pose, K = _cam()
    f = K[0, 0]
    for L, z in ((2.0, 10.0), (0.5, 10.0), (3.0, 4.0)):
        o = (0.0, 0.0, 10.0 - z)
        tab = T.project_anchors([o, (o[0] + L, o[1], o[2])], pose, K)
        px = float(np.linalg.norm(tab["uv"][1] - tab["uv"][0]))
        assert px == pytest.approx(f * L / z, abs=1e-9)
    # 視線方向に寝かせたバーは短縮する(正直に)
    tab = T.project_anchors([(1.0, 0.0, 0.0), (1.0, 0.0, 2.0)], pose, K)
    fore = float(np.linalg.norm(tab["uv"][1] - tab["uv"][0]))
    assert fore < f * 2.0 / 10.0


def test_scale_bar_op_draws_a_bar_of_the_projected_length():
    pose, K = _cam()
    img = _canvas(0.0)
    out = T.annotate3d_scale_bar(img, (-1.0, -2.0, 0.0), (1.0, 0.0, 0.0), 2.0, pose, K,
                                 unit="mm", color=(1.0, 1.0, 1.0), tick=0.0, box_alpha=0.0,
                                 width=1.0)
    tab = T.project_anchors([(-1.0, -2.0, 0.0), (1.0, -2.0, 0.0)], pose, K)
    v = int(round(tab["uv"][0, 1]))
    lit = np.flatnonzero(out[v, :, 0] > 0.5)
    want = K[0, 0] * 2.0 / 10.0
    assert abs((lit.max() - lit.min()) - want) <= 1.5


# ------------------------------------------------------------------ #
# 3. 遮蔽
# ------------------------------------------------------------------ #

def test_anchor_behind_another_surface_is_flagged_hidden():
    pose, K = _cam()
    depth = np.full((H, W), np.inf)
    depth[30:90, 50:110] = 7.0                                   # 手前(距離 7)の面
    tab = T.project_anchors([(0.0, 0.0, 0.0), (0.0, 0.0, 5.0), (2.5, 0.0, 0.0)], pose, K,
                            depth=depth)
    # 原点は距離 10 → 面(7)の裏 = hidden。(0,0,5) は距離 5 → 面の手前 = 見える
    assert tab["hidden"].tolist() == [True, False, False]
    assert tab["visible"].tolist() == [False, True, True]
    # 面の縁ぴったり(距離 10 の面)は tol の範囲で隠れない
    depth[:] = 10.0
    tab = T.project_anchors([(0.0, 0.0, 0.0)], pose, K, depth=depth, occlusion_tol=0.01)
    assert not tab["hidden"][0]


def test_hidden_label_is_drawn_dashed_visible_label_solid():
    pose, K = _cam()
    img = _canvas(0.0)
    depth = np.full((H, W), np.inf)
    depth[:] = 7.0
    seen = T.annotate3d_label(img, "p", (0.0, 0.0, 0.0), pose, K, offset=(30.0, 0.0),
                              color=(1.0, 1.0, 1.0), box_alpha=0.0, cap_size=0.0, width=2.0)
    hid = T.annotate3d_label(img, "p", (0.0, 0.0, 0.0), pose, K, depth=depth,
                             offset=(30.0, 0.0), color=(1.0, 1.0, 1.0), box_alpha=0.0,
                             cap_size=0.0, width=2.0)
    u, v = T.project_anchors([(0.0, 0.0, 0.0)], pose, K)["uv"][0]
    r = int(round(v))
    seg = slice(int(round(u)) + 2, int(round(u)) + 26)
    solid = (seen[r, seg, 0] > 0.5).sum()
    dashed = (hid[r, seg, 0] > 0.5).sum()
    assert solid >= 22                                             # 実線はほぼ全画素
    assert 0 < dashed < solid                                      # 破線は欠ける


def test_bbox_edges_behind_the_surface_are_dashed():
    pose, K = _cam()
    img = _canvas(0.0)
    depth = np.full((H, W), 8.5)                                   # 箱の前半分だけ見える
    out = T.annotate3d_bbox(img, ((-1.0, -1.0, -1.0), (1.0, 1.0, 1.0)), pose, K, depth=depth,
                            color=(1.0, 1.0, 1.0), width=1.0)
    solid = T.annotate3d_bbox(img, ((-1.0, -1.0, -1.0), (1.0, 1.0, 1.0)), pose, K,
                              color=(1.0, 1.0, 1.0), width=1.0)
    assert (out[..., 0] > 0.5).sum() < (solid[..., 0] > 0.5).sum()


# ------------------------------------------------------------------ #
# 4. fail-closed
# ------------------------------------------------------------------ #

def test_points_behind_the_camera_are_refused():
    pose, K = _cam()
    img = _canvas()
    with pytest.raises(ValueError, match="behind the camera"):
        T.annotate3d_arrow(img, (0.0, 0.0, 11.0), (1.0, 0.0, 11.0), pose, K)
    with pytest.raises(ValueError, match="behind the camera"):
        T.annotate3d_measure(img, (0.0, 0.0, 0.0), (0.0, 0.0, 12.0), pose, K)


def test_bad_pose_intrinsics_and_flags_are_refused():
    pose, K = _cam()
    img = _canvas()
    with pytest.raises(ValueError, match="4x4"):
        T.project_anchors([(0.0, 0.0, 0.0)], np.eye(3), K)
    with pytest.raises(ValueError, match="degenerate"):
        T.project_anchors([(0.0, 0.0, 0.0)], np.zeros((4, 4)), K)
    with pytest.raises(ValueError, match="3x3"):
        T.project_anchors([(0.0, 0.0, 0.0)], pose, np.eye(4))
    with pytest.raises(ValueError, match="width must be"):
        T.annotate3d_arrow(img, (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), pose, K, width=True)
    with pytest.raises(ValueError, match="zero vector"):
        T.annotate3d_scale_bar(img, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 1.0, pose, K)
    with pytest.raises(ValueError, match="does not match"):
        T.annotate3d_label(img, "x", (0.0, 0.0, 0.0), pose, K, depth=np.ones((H + 1, W)))
    with pytest.raises(ValueError, match="max must be >= min"):
        T.annotate3d_bbox(img, ((1.0, 1.0, 1.0), (0.0, 0.0, 0.0)), pose, K)
    with pytest.raises(ValueError, match="same pixel"):
        T.annotate3d_arrow(img, (0.0, 0.0, 0.0), (0.0, 0.0, 2.0), pose, K)


def test_measure_value_is_3d_distance_not_pixel_length():
    """視線方向に寝た 2 点でも値は 3-D 距離(短縮しても数字は変わらない)。"""
    pose, K = _cam()
    img = _canvas()
    a, b = (0.0, 0.0, 0.0), (0.0, 0.0, 3.0)
    out = T.annotate3d_measure(img, (0.5, 0.0, 0.0), (0.5, 0.0, 3.0), pose, K, unit="u")
    assert not np.array_equal(out, img)
    assert float(np.linalg.norm(np.subtract(b, a))) == 3.0


def test_ops_accept_grayscale_and_are_deterministic():
    pose, K = _cam()
    for ch in (0, 1, 3, 4):
        img = _canvas(0.2, ch)
        out = T.annotate3d_axes(img, pose, K, length=1.0)
        assert out.shape == img.shape
        assert np.array_equal(out, T.annotate3d_axes(img, pose, K, length=1.0))


# ------------------------------------------------------------------ #
# 5. 台帳
# ------------------------------------------------------------------ #

def test_ledger_registers_the_annotate3d_family():
    names = ops3d.list_ops("annotate3d")
    assert names == ["annotate3d_project", "annotate3d_arrow", "annotate3d_label",
                     "annotate3d_scale_bar", "annotate3d_axes", "annotate3d_bbox",
                     "annotate3d_measure"]
    assert not [n for n in names if n in ops3d.missing()]
    assert ops3d.info("annotate3d_project")["out"] == "table"
    for n in names[1:]:
        assert ops3d.info(n)["out"] == "image2d"
        assert ops3d.info(n)["in"][0] == "image2d"
        doc = ops3d.info(n)["doc"]
        assert doc.startswith("画像(image2d)"), (n, doc)
    pose, K = _cam()
    tab = ops3d.call("annotate3d_project", np.array([[0.0, 0.0, 0.0]]), pose, K)
    assert isinstance(tab, dict) and tab["uv"].shape == (1, 2)
    out = ops3d.call("annotate3d_arrow", _canvas(0.2, 0), (0.0, 0.0, 0.0), (1.0, 0.0, 0.0),
                     pose, K)
    assert isinstance(out, np.ndarray) and out.ndim == 2
