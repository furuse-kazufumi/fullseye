"""Fullseye Studio ライブギャラリー — サンプルが"動いている姿"を目で見る最小プロトタイプ.

ユーザーの理想(2026-08-18):「あなたがサンプルコードを作り、私が走らせて実際に動いて
いる姿が見れるような環境」。テキスト要約(studio_sample_catalog.py)から一歩進め、
各サンプルの**視覚出力**を描画する。Studio(HDevelop 風 IDE)の描画ペインの種。

生成物(このスクリプトを走らせると作られる):
  spikes/out_gallery/studio_gallery.png       … 静止パネル(画像処理の各段 + LiDAR 点群 + 検出)
  spikes/out_gallery/studio_lidar_sweep.gif   … LiDAR が回転走査して点が溜まる"動いている姿"

  実行:  PYTHONPATH=. py -3.11 spikes/studio_gallery.py
         (GUI 表示したいときは末尾の plt.show() を有効化。既定はファイル保存=どこでも動く)

★棲み分け(studio_sample_catalog.py と同じ): vision=fullseye が計算 / sim-source=物理が供給。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")  # GUI 不要でファイル保存(headless でも確実)。GUI 表示は "TkAgg" 等へ。
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.animation import FuncAnimation, PillowWriter  # noqa: E402

# Windows の日本語フォントを使う(既定 DejaVu Sans は CJK 無しでラベルが豆腐化する)。
from matplotlib import font_manager  # noqa: E402
_have = {f.name for f in font_manager.fontManager.ttflist}
for _jp in ("Yu Gothic", "Meiryo", "MS Gothic", "Yu Gothic UI"):
    if _jp in _have:
        matplotlib.rcParams["font.family"] = _jp
        break
matplotlib.rcParams["axes.unicode_minus"] = False  # マイナス記号の豆腐化も防ぐ

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lidar_adapter_spike as _sim  # noqa: E402
import unified_api_spike as _vis  # noqa: E402

import fullseye as fs  # noqa: E402

OUT = Path(__file__).resolve().parent / "out_gallery"
OUT.mkdir(exist_ok=True)


def _synthetic_scene(h: int = 96, w: int = 128) -> np.ndarray:
    """エッジがはっきり見える合成グレー画像(矩形 2 + 円)。sobel/threshold の効果が目で分かる。"""
    img = np.full((h, w), 0.15)
    img[20:50, 24:60] = 0.8                          # 明るい矩形
    img[55:80, 80:112] = 0.55                        # 中間の矩形
    yy, xx = np.mgrid[0:h, 0:w]
    img[(yy - 40) ** 2 + (xx - 96) ** 2 < 14 ** 2] = 0.95   # 円
    return img


def _panel_image_chain(fig) -> None:
    """vision: 画像チェーンの各段をフィルムストリップで(Image().to_gray().gaussian().sobel().threshold())。"""
    scene = _synthetic_scene()
    stages = [
        ("input", scene),
        ("gaussian(1.4)", _vis.Image(scene).gaussian(1.4).array),
        ("sobel", _vis.Image(scene).gaussian(1.4).sobel().array),
        ("threshold(0.25)", _vis.Image(scene).gaussian(1.4).sobel().threshold(0.25).array),
    ]
    for i, (title, arr) in enumerate(stages):
        ax = fig.add_subplot(2, 4, i + 1)
        ax.imshow(arr, cmap="gray", vmin=0, vmax=1)
        ax.set_title(f"vision · {title}", fontsize=8)
        ax.axis("off")


def _panel_lidar_perceive(fig) -> None:
    """sim-source→vision: LiDAR 点群を 3D 散布、床=灰/検出物体=色分け+重心マーカー。"""
    scene = _sim.sim.MuJoCo(_sim.SCENE)
    pts = scene.lidar(origin=(0.0, 0.0, 1.0))
    ng, gmask = fs.remove_ground(pts, thresh=0.03)
    clusters = fs.euclidean_clusters(ng, tol=0.25, min_size=5)
    ground = pts[gmask]

    ax = fig.add_subplot(2, 2, 3, projection="3d")
    ax.scatter(ground[:, 0], ground[:, 1], ground[:, 2], s=1, c="0.7", label="ground")
    colors = plt.cm.tab10(np.linspace(0, 1, max(len(clusters), 1)))
    for i, idx in enumerate(clusters):
        c = ng[idx]
        ax.scatter(c[:, 0], c[:, 1], c[:, 2], s=8, color=colors[i])
        cen = fs.centroid(c)
        ax.scatter(*cen, s=120, marker="*", color=colors[i], edgecolor="k")
    ax.scatter(0, 0, 1.0, s=80, marker="^", color="red")  # sensor
    ax.set_title(f"sim-source→vision · LiDAR {len(pts)}pt → 物体 {len(clusters)}", fontsize=8)
    ax.set_zlim(0, 1.2)
    ax.view_init(elev=28, azim=-60)


def _build_static() -> Path:
    fig = plt.figure(figsize=(11, 5.5))
    _panel_image_chain(fig)
    _panel_lidar_perceive(fig)
    fig.suptitle("Fullseye Studio gallery — vision(計算)/ sim-source(供給)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    path = OUT / "studio_gallery.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def _build_lidar_sweep() -> Path:
    """LiDAR が方位を回転走査し、通過した方位のヒット点が溜まっていく"動いている姿"。"""
    scene = _sim.sim.MuJoCo(_sim.SCENE)
    origin = np.array([0.0, 0.0, 1.0])
    pat = _sim.LidarPattern(h_res=144, v_res=20)
    dirs = pat.directions()
    az = np.arctan2(dirs[:, 1], dirs[:, 0])          # 各ビームの方位角

    # 全点を一度スキャンし、方位角と z を保持(アニメは方位しきい値で開示)。
    import mujoco
    gid = np.zeros(1, np.int32)
    P, A = [], []
    for vec, a in zip(dirs, az):
        d = mujoco.mj_ray(scene._m, scene._d, origin, vec, None, True, -1, gid)
        if 0.0 <= d <= pat.max_range and gid[0] >= 0:
            P.append(origin + d * vec)
            A.append(a)
    P, A = np.asarray(P), np.asarray(A)

    fig = plt.figure(figsize=(6, 5))
    ax = fig.add_subplot(111, projection="3d")
    frames = 48
    sweep = np.linspace(-np.pi, np.pi, frames)

    def draw(k):
        ax.clear()
        cur = sweep[k]
        seen = A <= cur
        if seen.any():
            pts = P[seen]
            ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], s=3, c=pts[:, 2], cmap="viridis", vmin=0, vmax=0.6)
        # 現在ビーム方向のライン(視覚的に「走査している」ことを示す)
        beam = origin + 4.0 * np.array([np.cos(cur), np.sin(cur), 0.0])
        ax.plot([origin[0], beam[0]], [origin[1], beam[1]], [origin[2], beam[2]], color="red", lw=1.5)
        ax.scatter(*origin, s=60, marker="^", color="red")
        ax.set_xlim(-3, 3); ax.set_ylim(-3, 3); ax.set_zlim(0, 1.2)
        ax.set_title(f"sim LiDAR sweep  az={np.degrees(cur):+4.0f}°  pts={int(seen.sum())}", fontsize=9)
        ax.view_init(elev=32, azim=-60)

    anim = FuncAnimation(fig, draw, frames=frames, interval=80)
    path = OUT / "studio_lidar_sweep.gif"
    anim.save(path, writer=PillowWriter(fps=12))
    plt.close(fig)
    return path


def main() -> None:
    print("Fullseye Studio gallery を描画中...")
    p1 = _build_static()
    print(f"  静止パネル: {p1}")
    p2 = _build_lidar_sweep()
    print(f"  LiDAR sweep アニメ: {p2}")
    print("[gallery OK] vision(計算)/ sim-source(供給)のサンプルが視覚化されました")


if __name__ == "__main__":
    main()
