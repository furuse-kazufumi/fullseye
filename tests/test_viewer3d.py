"""viewer3d(Open3D 連携 3D ビューア adapter, F6)の回帰テスト。

GL 非依存の geometry 構築・PLY エクスポート・graceful fallback を検証する
(対話ウィンドウ / オフスクリーンは desktop GL 依存のため CI では検証しない)。
"""
from __future__ import annotations

import numpy as np
import pytest

import spikes.viewer3d as v3d

o3d_missing = not v3d.available()


def test_backend_status():
    st = v3d.backend_status()
    assert "open3d" in st and "offscreen" in st and "interactive" in st


@pytest.mark.skipif(o3d_missing, reason="open3d 未導入(optional extra)")
def test_point_cloud_geometry():
    """point_cloud 出力 → PointCloud + 座標フレーム geometry。"""
    pts = np.random.default_rng(0).random((200, 3))
    geoms = v3d.to_geometries(pts, "point_cloud")
    assert len(geoms) >= 1
    import open3d as o3d
    assert any(isinstance(g, o3d.geometry.PointCloud) for g in geoms)
    pc = next(g for g in geoms if isinstance(g, o3d.geometry.PointCloud))
    assert len(pc.points) == 200 and len(pc.colors) == 200   # z で着色


@pytest.mark.skipif(o3d_missing, reason="open3d 未導入")
def test_pose_geometry():
    """pose 出力(4x4)→ 座標フレーム(RViz2 の pose 軸相当)。"""
    T = np.eye(4); T[:3, 3] = [0.5, 0.2, 0.3]
    geoms = v3d.to_geometries(T, "pose")
    assert len(geoms) >= 1
    import open3d as o3d
    assert all(isinstance(g, o3d.geometry.TriangleMesh) for g in geoms)


@pytest.mark.skipif(o3d_missing, reason="open3d 未導入")
def test_pose_from_dict():
    geoms = v3d.to_geometries({"R": np.eye(3), "t": np.array([1.0, 0, 0])}, "pose")
    assert len(geoms) >= 1


def test_non_3d_hints_empty():
    """image/region/contour は 3D 化しない(→ Studio は 2D 側で描く)。"""
    for hint in ("image", "region", "contour", "scalar", "matrix"):
        assert v3d.to_geometries(np.zeros((8, 8)), hint) == []


@pytest.mark.skipif(o3d_missing, reason="open3d 未導入")
def test_export_ply(tmp_path):
    """PLY 書き出し(GL 不要=常に可。外部ビューアで開ける)。"""
    pts = np.random.default_rng(0).random((100, 3))
    geoms = v3d.to_geometries(pts, "point_cloud")
    out = tmp_path / "cloud.ply"
    assert v3d.export_ply(geoms, out)
    assert out.exists() and out.stat().st_size > 0


@pytest.mark.skipif(o3d_missing, reason="open3d 未導入")
def test_offscreen_graceful():
    """オフスクリーンは GL(EGL)不可なら None を返す(例外を投げない=graceful)。"""
    pts = np.random.default_rng(0).random((50, 3))
    geoms = v3d.to_geometries(pts, "point_cloud")
    img = v3d.render_offscreen(geoms)
    assert img is None or (isinstance(img, np.ndarray) and img.ndim == 3)


@pytest.mark.skipif(o3d_missing, reason="open3d 未導入")
def test_ground_grid():
    ls = v3d.ground_grid()
    import open3d as o3d
    assert isinstance(ls, o3d.geometry.LineSet) and len(ls.points) > 0
