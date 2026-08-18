"""Fullseye 3D ビューア(Open3D 連携)デモ — 知覚シーンを 3D で見せる(F6 の RViz2 相当).

evis 知覚パイプライン(点群 → 物体クラスタ → 6D pose)を Open3D geometry に変換し:
  ① Open3D 対話ウィンドウ(mouse ナビ=RViz2 相当) … --show(desktop GL 要)
  ② .ply エクスポート(外部 Open3D/CloudCompare で開ける) … 常に生成
  ③ matplotlib プレビュー PNG(内容確認・headless 可) … 常に生成

  PYTHONPATH=. py -3.11 spikes/viewer3d_demo.py          # .ply + プレビュー PNG を生成
  PYTHONPATH=. py -3.11 spikes/viewer3d_demo.py --show   # + Open3D 対話ウィンドウ
"""
from __future__ import annotations

import os
import sys
import warnings

import numpy as np

warnings.simplefilter("ignore")
sys.path.insert(0, os.path.dirname(__file__))

import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager
for _jp in ("Yu Gothic", "Meiryo", "MS Gothic"):
    if _jp in {f.name for f in font_manager.fontManager.ttflist}:
        matplotlib.rcParams["font.family"] = _jp
        break
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt  # noqa: E402
import viewer3d as v3d  # noqa: E402
import fullseye as fs  # noqa: E402

_OUT = os.path.join(os.path.dirname(__file__), "out_gallery")


def perception_scene():
    """合成の地形+物体点群を作り、fullseye 知覚 op で床除去→クラスタ→各物体の 6D pose(OBB)。"""
    rng = np.random.default_rng(1)
    xs, ys = np.meshgrid(np.linspace(-2, 2, 40), np.linspace(-2, 2, 40))
    floor = np.column_stack([xs.ravel(), ys.ravel(), 0.05 * np.sin(xs.ravel())])
    objs = []
    for cx, cy, h in [(-0.8, 0.6, 0.4), (0.9, -0.5, 0.6), (0.2, 1.1, 0.3)]:
        b = rng.normal([cx, cy, h / 2], [0.12, 0.12, h / 3], (80, 3))
        objs.append(b)
    cloud = np.vstack([floor + rng.normal(0, 0.005, floor.shape)] + objs)
    ng, gmask = fs.remove_ground(cloud, thresh=0.06)
    clusters = fs.euclidean_clusters(ng, tol=0.35, min_size=8)
    poses = []
    for idx in clusters:
        box = fs.obb(ng[idx])
        T = np.eye(4); T[:3, :3] = np.asarray(box["axes"]); T[:3, 3] = np.asarray(box["center"])
        poses.append(T)
    return cloud, gmask, [ng[i] for i in clusters], poses


def build_geometries(cloud, clusters, poses):
    """知覚結果を Open3D geometry へ(点群 + 各物体の 6D pose フレーム + 地面グリッド)。"""
    geoms = v3d.to_geometries(cloud, "point_cloud")          # 点群 + world 原点
    for T in poses:                                          # 各物体の 6D pose(RViz2 の pose 軸)
        geoms += v3d.to_geometries(T, "pose")
    grid = v3d.ground_grid()
    if grid is not None:
        geoms.append(grid)
    return geoms


def matplotlib_preview(cloud, gmask, clusters, poses, path):
    """Open3D シーンの内容を matplotlib 3D でプレビュー(headless 可)。"""
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")
    ax.scatter(cloud[gmask][:, 0], cloud[gmask][:, 1], cloud[gmask][:, 2], s=1, c="0.7", label="地面")
    cols = plt.cm.tab10(np.linspace(0, 1, max(len(clusters), 1)))
    for i, c in enumerate(clusters):
        ax.scatter(c[:, 0], c[:, 1], c[:, 2], s=8, color=cols[i])
    for T in poses:                                          # 6D pose 軸
        t = T[:3, 3]
        for k, ac in enumerate("rgb"):
            v = T[:3, k] * 0.3
            ax.plot([t[0], t[0] + v[0]], [t[1], t[1] + v[1]], [t[2], t[2] + v[2]], color=ac, lw=2)
    ax.set_title(f"evis 知覚シーン: 点群 {len(cloud)} → 物体 {len(clusters)} + 6D pose "
                 f"(Open3D で対話表示可)", fontsize=10)
    ax.set_zlim(0, 1); ax.view_init(26, -60)
    fig.savefig(path, dpi=110)
    return path


def main():
    os.makedirs(_OUT, exist_ok=True)
    print("== Fullseye 3D ビューア(Open3D 連携)デモ ==")
    print("backend:", v3d.backend_status())
    cloud, gmask, clusters, poses = perception_scene()
    print(f"知覚: 点群 {len(cloud)} → 床除去 → 物体 {len(clusters)} + 6D pose {len(poses)}")

    geoms = build_geometries(cloud, clusters, poses)
    print(f"Open3D geometry: {len(geoms)}(点群 + pose フレーム×{len(poses)} + 地面グリッド)")

    ply = os.path.join(_OUT, "viewer3d_scene.ply")
    if v3d.export_ply(geoms, ply):
        print(f"[.ply] {ply}  ← 外部 Open3D/CloudCompare で開ける")

    png = matplotlib_preview(cloud, gmask, clusters, poses, os.path.join(_OUT, "viewer3d_preview.png"))
    print(f"[preview] {png}  ← 内容確認(headless 可)")

    if "--show" in sys.argv:
        print("Open3D 対話ウィンドウを起動(mouse ナビ=RViz2 相当。閉じると戻る)…")
        ok = v3d.show_interactive(geoms, title="Fullseye 3D — evis 知覚シーン")
        print("  ->", "OK" if ok else "起動失敗(desktop GL が要る)")
    else:
        print("対話 3D を見るには: PYTHONPATH=. py -3.11 spikes/viewer3d_demo.py --show")


if __name__ == "__main__":
    main()
