# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""3-D の残り指摘(2026-10-11)の回帰テスト。

- hausdorff_distance が兄弟(chamfer_distance ほか)と同じく入口で拒否する(fail-closed)
- annotate3d_axes の軸は ``pose`` が写す元の座標系(object 座標)の軸 —— 説明の「世界座標」は誤り
- annotate3d_arrow は片方だけ枠外なら描き、両端とも枠外なら拒否する(本文が「エラーにしない」と誤っていた)
- ヘルプが名指しする op 名が実在し、コード片に日本語が残っていない
- 3-D の要約(docstring の 1 行目)が文の途中で切れていない

どれも小さな合成データで決定的に走る。
"""
from __future__ import annotations

import importlib
import inspect
import re

import numpy as np
import pytest


# --------------------------------------------------------------------------- #
# A. hausdorff_distance —— 入口検査                                            #
# --------------------------------------------------------------------------- #
def test_hausdorff_rejects_empty_cloud_with_its_own_message():
    import metrics3d as M
    a = np.zeros((4, 3))
    with pytest.raises(ValueError, match="a is empty"):
        M.hausdorff_distance(np.zeros((0, 3)), a)
    with pytest.raises(ValueError, match="b is empty"):
        M.hausdorff_distance(a, np.zeros((0, 3)))


def test_hausdorff_rejects_non_3_column_input():
    import metrics3d as M
    with pytest.raises(ValueError, match=r"\(N, 3\) point cloud"):
        M.hausdorff_distance(np.zeros((5, 2)), np.zeros((5, 2)))


def test_hausdorff_value_unchanged_for_valid_input():
    import metrics3d as M
    rng = np.random.default_rng(3)
    a = rng.normal(size=(50, 3))
    assert M.hausdorff_distance(a, a) == 0.0
    # 既知オフセット: 全点を +x に 0.25 ずらすと Hausdorff <= 0.25
    b = a + np.array([0.25, 0.0, 0.0])
    h = M.hausdorff_distance(a, b)
    assert 0.0 < h <= 0.25 + 1e-12
    # 1 点だけ遠くへ: 値はその 1 点で決まる(最大値)
    c = a.copy()
    c[7] += np.array([0.0, 0.0, 10.0])
    assert M.hausdorff_distance(a, c) > 5.0


# --------------------------------------------------------------------------- #
# B. annotate3d_axes —— 軸は pose の入力側の座標系                              #
# --------------------------------------------------------------------------- #
def _cam():
    import render3d as R3
    W = R3.look_at((3.0, -4.0, 2.5), (0.0, 0.0, 0.0), up=(0.0, 0.0, 1.0))
    K = np.array([[110.0, 0.0, 80.0], [0.0, 110.0, 60.0], [0.0, 0.0, 1.0]])
    return W, K


def _rot_z(deg):
    t = np.deg2rad(deg)
    M = np.eye(4)
    M[:2, :2] = [[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]]
    return M


def _changed_near(img, base, uv, r=1):
    c, rr = int(round(uv[0])), int(round(uv[1]))
    sl = (slice(rr - r, rr + r + 1), slice(c - r, c + r + 1))
    return bool(np.abs(img[sl] - base[sl]).max() > 1e-6)


def test_axes_follow_the_object_frame_of_pose():
    import annotate3d as A3
    W, K = _cam()
    M = _rot_z(180.0)                         # 物体の姿勢(object→world)
    P = W @ M                                 # object→camera
    base = np.zeros((120, 160, 3))
    out = A3.annotate3d_axes(base, P, K, length=1.0, labels=("", "", ""))
    # 物体の +X 軸(world では -X)の中ほどの画素は塗られ、
    # world の +X 軸の中ほどの画素は塗られない
    obj_mid = A3.annotate3d_project(np.array([0.5, 0.0, 0.0]), P, K)["uv"][0]
    world_mid = A3.annotate3d_project(np.array([0.5, 0.0, 0.0]), W, K)["uv"][0]
    assert np.hypot(*(obj_mid - world_mid)) > 10.0          # 探針が区別できる配置
    assert _changed_near(out, base, obj_mid)
    assert not _changed_near(out, base, world_mid)


def test_axes_doc_names_the_object_frame():
    import annotate3d as A3
    doc = inspect.getdoc(A3.annotate3d_axes)
    assert "世界座標" not in doc
    assert "object 座標" in doc.splitlines()[0]


# --------------------------------------------------------------------------- #
# C. annotate3d_arrow —— 片方だけ枠外なら描き、両端とも枠外なら拒否             #
# --------------------------------------------------------------------------- #
def test_arrow_outside_rule_matches_the_doc():
    """片方だけ枠外なら描く・両端とも枠外なら ValueError(説明の本文が逆を書いていた)。"""
    import annotate3d as A3
    W, K = _cam()
    base = np.zeros((120, 160, 3))
    eye, right, fwd = np.array([3.0, -4.0, 2.5]), W[0, :3], -W[2, :3]
    far = eye + 5.0 * fwd + 20.0 * right       # 前方だが画像の右へ大きく外れる
    tab = A3.annotate3d_project(np.vstack([far, far + 0.5 * fwd, np.zeros(3)]), W, K,
                                shape=base.shape[:2])
    assert tab["in_front"].all()
    assert not tab["in_image"][:2].any() and tab["in_image"][2]
    out = A3.annotate3d_arrow(base, np.zeros(3), far, W, K)      # 片方だけ枠外
    assert out.shape == base.shape and np.abs(out - base).max() > 0
    with pytest.raises(ValueError, match="entirely outside"):
        A3.annotate3d_arrow(base, far, far + 0.5 * fwd, W, K)
    doc = inspect.getdoc(A3.annotate3d_arrow)
    assert "両端とも画像の外" in doc
    assert "画像の外に出た端点はエラーにしない" not in doc


def test_axes_with_origin_and_end_outside_raise():
    import annotate3d as A3
    W, K = _cam()
    eye, right, fwd = np.array([3.0, -4.0, 2.5]), W[0, :3], -W[2, :3]
    far = eye + 5.0 * fwd + 20.0 * right
    with pytest.raises(ValueError, match="entirely outside"):
        A3.annotate3d_axes(np.zeros((120, 160, 3)), W, K, origin=far, length=0.5,
                           labels=("", "", ""))
    assert "枠外の軸端はエラーにしない" not in inspect.getdoc(A3.annotate3d_axes)


def test_arrow_still_rejects_points_on_one_ray():
    import annotate3d as A3
    W, K = _cam()
    eye = np.array([3.0, -4.0, 2.5])
    with pytest.raises(ValueError, match="same pixel"):
        A3.annotate3d_arrow(np.zeros((120, 160, 3)), eye * 0.5, eye * 0.25, W, K)


# --------------------------------------------------------------------------- #
# D/E. ヘルプが名指しする名前とコード片                                          #
# --------------------------------------------------------------------------- #
def test_referenced_op_names_exist():
    import annotate3d as A3
    import metrics3d as M
    import ops3d
    names = ["estimate_point_normals", "orient_normals", "fit_sphere3", "smallest_box3"]
    assert names
    assert all(n in ops3d.OPS3D for n in names), [n for n in names if n not in ops3d.OPS3D]
    m3c2 = inspect.getdoc(M.m3c2_distance)
    assert "``estimate_point_normals``" in m3c2
    assert "`estimate_normals`" not in m3c2
    doc = inspect.getdoc(A3.annotate3d_measure)
    assert "``fit_sphere3``" in doc and "``smallest_box3``" in doc


_SPAN = re.compile(r"``[^`]+?``", re.S)
_JA = re.compile(r"[぀-ヿ㐀-鿿]")


@pytest.mark.parametrize("mod,fn", [
    ("fit_primitives_ext", "fit_cone"), ("fit_primitives_ext", "fit_torus"),
    ("fit_primitives_ext", "fit_ellipsoid"), ("feat_shot", "shot_descriptor"),
    ("match3d", "match_chamfer_3d"),
])
def test_no_japanese_inside_code_spans(mod, fn):
    doc = inspect.getdoc(getattr(importlib.import_module(mod), fn))
    spans = _SPAN.findall(doc)
    assert spans
    assert not [s for s in spans if _JA.search(s)]


def test_shot_shape_in_doc_matches_the_code():
    from scipy.spatial import cKDTree

    import feat_shot as FS
    assert "``(len(kp_idx), n_azim*n_elev*n_rad*n_cos)``" in inspect.getdoc(FS.shot_descriptor)
    rng = np.random.default_rng(0)
    p = rng.normal(size=(200, 3))
    n = FS.estimate_normals(p, k=16)
    t = cKDTree(p)
    assert FS.shot_descriptor(p, n, np.array([0, 3]), t, 1.5).shape == (2, 352)
    d = FS.shot_descriptor(p, n, np.array([0]), t, 1.5, n_azim=4, n_elev=3, n_rad=1, n_cos=5)
    assert d.shape == (1, 4 * 3 * 1 * 5)


def test_tonemap_raises_text_says_exposure():
    import render_tonemap as RT
    for f in (RT.tonemap_reinhard, RT.tonemap_aces):
        assert "exposition" not in inspect.getdoc(f)
    with pytest.raises(ValueError, match="exposure"):
        RT.tonemap_aces(np.ones((2, 2)), exposure=0.0)


def test_iss_register_shot_radii_in_doc_match_the_code():
    import feat_shot as FS
    src = inspect.getsource(FS.register_shot)
    assert "sal_r, nms_r = 0.6 * radius, 0.3 * radius" in src
    doc = inspect.getdoc(FS.iss_keypoints)
    assert "``0.6*radius``" in doc and "``0.3*radius``" in doc
    assert "λ3 は厳密には 0 に" not in doc


# --------------------------------------------------------------------------- #
# F. 3-D の要約が文の途中で切れていない                                          #
# --------------------------------------------------------------------------- #
_FIXED = ["vol_uncrop", "vol_tiled_map", "vol_rle_volume", "vol_rle_union", "vol_rle_decode",
          "vol_rle_bbox", "vol_wall_thickness", "vol_fft_lowpass", "vol_fft_highpass",
          "vol_fft_bandpass", "vol_gaussian_psf", "shot_descriptor", "fit_line3", "fit_plane3",
          "fit_circle3", "smallest_box3_axis", "fit_box3", "smallest_sphere3",
          "mesh_edge_lengths", "mesh_subdivide", "displacement_band_weights",
          "mesh_displace_spectrum", "bump_normals_fbm", "inner_box3"]


def test_3d_summaries_are_whole_sentences():
    import ops3d
    xs = [n for n in _FIXED if n in ops3d.OPS3D]
    assert xs == _FIXED
    bad = []
    for n in xs:
        first = inspect.getdoc(ops3d.OPS3D[n]["func"]).splitlines()[0].rstrip()
        if not re.search(r"[。.)）`]$", first):
            bad.append((n, first[-40:]))
    assert not bad, bad
