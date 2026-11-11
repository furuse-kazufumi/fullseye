# -*- coding: utf-8 -*-
"""1.0 前の修正 2026-11-05(abs-floor): 単位のある量に絶対の床が混ざり、結果が座標の尺度に依存した。

外部監査 F3(``vector_to_similarity`` の分母の 1e-12)と同じ型の兄弟を、利用者が直接呼ぶ op から
拾って直した回帰テスト。門はどれも **尺度の不変量**: 入力の長さを ``k`` 倍(``k`` = 1e-6・1e6、
床が長さそのものに掛かっていたものは 1e-13 も)にした結果が、``k = 1`` の結果の ``k`` 倍(無次元量なら
そのまま)に一致すること。真値は ``k = 1`` の同じ関数(その尺度では床が効かないことを別に表明する)。

修正前は、

* ``pcseg.curvature`` / ``objmodel3d.edges_object_model_3d`` —— 近傍共分散の固有値の和(長さ²)に
  1e-12 の床。座標 1e-6 で曲率が 0 になり、エッジ点が 1 個も出なかった。
* ``feat_shot.iss_keypoints`` —— λ1(長さ²)<= 1e-12 で点を捨て、座標 1e-6 でキーポイント 0 個。
* ``backends_xldgeom.xg_eccentricity`` / ``xg_elliptic_axis`` / ``xg_height_width_ratio`` /
  ``xg_clip_contours`` / ``_max_perp`` —— 固有値(長さ²)・幅・長さに 1e-12 の床。
* ``camera.normals_from_depth`` —— 外積の長さ(長さ²)< 1e-12 を無効画素(NaN)にした。
  ``range_image.normals_from_depth`` は同じ量に + 1e-12 を足して単位にならなかった。
* ``contours_xld2.gen_parallels_xld`` / ``contours_xld.gen_contour_polygon_rounded_xld`` ——
  接線の長さに + 1e-12(座標 1e-6 で相対 1e-6 ずれる)。
* ``objmodel3d.intersect_plane_object_model_3d`` —— 平面係数の法線の長さに + 1e-12(係数の尺度で
  距離が変わる)。
* ``curve3d.resample_uniform`` / ``measure.fit_rectangle2`` —— 長さ < 1e-12 を「長さ 0」とみなした。
"""
from __future__ import annotations

import numpy as np
import pytest

SCALES = (1e-6, 1e6)


def _box_cloud(seed=0):
    """立方体の表面の点群(辺 1)。面の点は平面、辺・角の点は曲率が高い。"""
    rng = np.random.default_rng(seed)
    pts = []
    for axis in range(3):
        for side in (0.0, 1.0):
            uv = rng.uniform(0.0, 1.0, size=(150, 2))
            p = np.insert(uv, axis, side, axis=1)
            pts.append(p)
    return np.vstack(pts)


# ── 点群の曲率 ───────────────────────────────────────────────────────────── #
@pytest.mark.parametrize("k", SCALES)
def test_pcseg_curvature_scale_invariant(k):
    import pcseg
    P = _box_cloud()
    base = pcseg.curvature(P, k=12)
    assert base.shape == (len(P),) and float(base.max()) > 0.01   # 尺度 1 で曲率が出ている
    np.testing.assert_allclose(pcseg.curvature(P * k, k=12), base, rtol=1e-6, atol=1e-12)


@pytest.mark.parametrize("k", SCALES)
def test_edges_object_model_3d_scale_invariant(k):
    import objmodel3d
    P = _box_cloud()
    base = objmodel3d.edges_object_model_3d(P, k=12, thresh=0.05)
    assert len(base) >= 20                                       # 尺度 1 でエッジ点が出ている
    got = objmodel3d.edges_object_model_3d(P * k, k=12, thresh=0.05)
    assert got.shape == base.shape
    np.testing.assert_allclose(got, base * k, rtol=1e-9)


@pytest.mark.parametrize("k", SCALES)
def test_iss_keypoints_scale_invariant(k):
    import feat_shot
    rng = np.random.default_rng(3)
    # 非等方な塊(3 軸の広がりが別々)= ISS の固有値が distinct になる
    P = rng.normal(size=(600, 3)) * np.array([1.0, 0.6, 0.3])
    base = feat_shot.iss_keypoints(P, radius=0.5, max_kp=50)
    assert len(base) >= 3
    got = feat_shot.iss_keypoints(P * k, radius=0.5 * k, max_kp=50)
    assert sorted(np.asarray(got).tolist()) == sorted(np.asarray(base).tolist())


# ── XLD の形状量 ─────────────────────────────────────────────────────────── #
def _ellipse_contour(k):
    t = np.linspace(0.0, 2.0 * np.pi, 64, endpoint=False)
    c = np.column_stack([3.0 * np.sin(t), 1.0 * np.cos(t)]) * k
    return {"shape": (64, 64), "cs": [c]}


@pytest.mark.parametrize("k", SCALES)
def test_xldgeom_shape_features_scale_invariant(k):
    import backends_xldgeom as xg
    for name in ("xg_eccentricity", "xg_elliptic_axis", "xg_height_width_ratio"):
        fn = getattr(xg, name)
        base = float(fn(_ellipse_contour(1.0), 0, 0))
        assert base not in (0.0, 1.0, 1e6), name                 # 尺度 1 で意味のある値
        assert float(fn(_ellipse_contour(k), 0, 0)) == pytest.approx(base, rel=1e-9), name


@pytest.mark.parametrize("k", SCALES + (1e-13,))
def test_xg_clip_contours_scale_invariant(k):
    import backends_xldgeom as xg
    long_ = np.column_stack([np.zeros(11), np.linspace(0, 10, 11)])
    short = np.column_stack([np.ones(3), np.linspace(0, 2, 3)])
    v = {"shape": (16, 16), "cs": [long_ * k, short * k]}
    out = xg.xg_clip_contours(v, 0.5, 0)
    assert len(out["cs"]) == 1                                   # 短い方(長さ 2 < 0.5×10)を落とす
    np.testing.assert_allclose(out["cs"][0], long_ * k)


# ── 深度 → 法線 ──────────────────────────────────────────────────────────── #
def _tilted_depth():
    yy, xx = np.mgrid[0:24, 0:32].astype(np.float64)
    return 1.0 + 0.01 * xx + 0.02 * yy


@pytest.mark.parametrize("k", SCALES)
def test_camera_normals_from_depth_scale_invariant(k):
    import camera
    K = np.array([[5000.0, 0, 16], [0, 5000.0, 12], [0, 0, 1]])
    Z = _tilted_depth()
    base = camera.normals_from_depth(Z, K)
    inner = np.isfinite(base).all(axis=-1)
    assert inner.sum() >= 600                                    # 縁以外は有効
    got = camera.normals_from_depth(Z * k, K)
    assert np.array_equal(np.isfinite(got).all(axis=-1), inner)
    np.testing.assert_allclose(got[inner], base[inner], rtol=1e-9, atol=1e-12)


@pytest.mark.parametrize("k", SCALES)
def test_range_image_normals_from_depth_scale_invariant(k):
    import range_image
    Z = _tilted_depth()
    base = range_image.normals_from_depth(Z, spacing=(1.0, 1.0))
    got = range_image.normals_from_depth(Z * k, spacing=(k, k))
    assert got.dtype == base.dtype                               # 出力は float32(丸めはその桁)
    tol = 10 * float(np.finfo(got.dtype).eps)
    np.testing.assert_allclose(np.linalg.norm(got, axis=-1), 1.0, rtol=tol)
    np.testing.assert_allclose(got, base, rtol=tol, atol=tol)


# ── 輪郭の生成 ───────────────────────────────────────────────────────────── #
@pytest.mark.parametrize("k", SCALES)
def test_gen_parallels_xld_scale_equivariant(k):
    import contours_xld2
    t = np.linspace(0.0, 1.5 * np.pi, 40)
    a = np.column_stack([10.0 * np.sin(t), 10.0 * np.cos(t)])
    base = contours_xld2.gen_parallels_xld({"shape": (32, 32), "cs": [a]}, distance=2.0)
    got = contours_xld2.gen_parallels_xld({"shape": (32, 32), "cs": [a * k]}, distance=2.0 * k)
    assert len(got["cs"]) == len(base["cs"]) == 2
    for g, b in zip(got["cs"], base["cs"]):
        np.testing.assert_allclose(g, b * k, rtol=1e-12)
    # 真値: 円 r=10 の平行線は半径 8 と 12
    r = np.sort([np.hypot(*base["cs"][i][20]) for i in range(2)])
    np.testing.assert_allclose(r, [8.0, 12.0], rtol=1e-2)


@pytest.mark.parametrize("k", SCALES)
def test_gen_contour_polygon_rounded_xld_scale_equivariant(k):
    import contours_xld
    sq = np.array([[0.0, 0.0], [0.0, 10.0], [10.0, 10.0], [10.0, 0.0]])
    base = contours_xld.gen_contour_polygon_rounded_xld(sq, radius=2.0, n=5)
    got = contours_xld.gen_contour_polygon_rounded_xld(sq * k, radius=2.0 * k, n=5)
    np.testing.assert_allclose(got["cs"][0], base["cs"][0] * k, rtol=1e-12)


def test_gen_contour_polygon_rounded_xld_repeated_vertex_stays_finite():
    """重なった頂点(辺の長さ 0)は以前どおり有限(床を外しても 0/0 の NaN を出さない)。"""
    import contours_xld
    p = np.array([[0.0, 0.0], [0.0, 0.0], [0.0, 10.0], [10.0, 10.0]])
    out = contours_xld.gen_contour_polygon_rounded_xld(p, radius=2.0, n=3)
    assert out["cs"][0].shape[0] == 4 * 3 + 1
    assert np.isfinite(out["cs"][0]).all()


# ── 平面係数の尺度 ───────────────────────────────────────────────────────── #
def test_intersect_plane_object_model_3d_plane_scale_invariant():
    import objmodel3d
    z = np.linspace(-0.1, 0.1, 201)
    P = np.column_stack([np.zeros_like(z), np.zeros_like(z), z])
    base = objmodel3d.intersect_plane_object_model_3d(P, (0.0, 0.0, 1.0, 0.0), tol=0.05)
    assert len(base) == int(np.sum(np.abs(z) < 0.05))
    for s in (1e-9, 1e-6, 1e6):
        got = objmodel3d.intersect_plane_object_model_3d(P, (0.0, 0.0, s, 0.0), tol=0.05)
        assert len(got) == len(base), s


def test_plane_ops_reject_zero_normal():
    import objmodel3d
    P = np.random.default_rng(0).normal(size=(20, 3))
    for fn in (objmodel3d.intersect_plane_object_model_3d,
               objmodel3d.volume_object_model_3d_relative_to_plane):
        with pytest.raises(ValueError, match="normal"):
            fn(P, (0.0, 0.0, 0.0, 1.0))


# ── 長さ < 1e-12 を「長さ 0」とみなしていたもの ─────────────────────────── #
@pytest.mark.parametrize("k", SCALES + (1e-13,))
def test_resample_uniform_tiny_curve(k):
    import curve3d
    c = np.column_stack([np.linspace(0, 1, 5), np.zeros(5), np.zeros(5)])
    out = curve3d.resample_uniform(c * k, 3)
    np.testing.assert_allclose(out, np.array([[0, 0, 0], [0.5, 0, 0], [1, 0, 0]]) * k, rtol=1e-12)


@pytest.mark.parametrize("k", SCALES + (1e-13,))
def test_fit_rectangle2_tiny_rectangle(k):
    import measure
    rect = np.array([[0.0, 0.0], [0.0, 4.0], [2.0, 4.0], [2.0, 0.0], [1.0, 2.0]])
    base = measure.fit_rectangle2(rect)
    got = measure.fit_rectangle2(rect * k)
    assert base["l1"] == pytest.approx(2.0) and base["l2"] == pytest.approx(1.0)
    for key in ("l1", "l2"):
        assert got[key] == pytest.approx(base[key] * k, rel=1e-9)
