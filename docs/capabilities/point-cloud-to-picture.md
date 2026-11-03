---
id: point-cloud-to-picture
title: 点群をそのまま色の絵にする
title_en: Draw a point cloud as a colour picture
category: 見せる
ops: [points_render, render_point_depth, project_points]
examples: [points_render_basics, poc_flybrain_pointcloud, poc_real_tless_6dof]
version: 0.2.0
inputs: [points]
pipeline: [points_render]
alternatives: [render_point_depth, points_activity_video, gs_render, render_mesh]
limits: 正射影の自動の収め方は R, t を当てた後の XY の箱で決まる(透視は K が要る)。disc の足跡は画素に量子化されるので、像の重心は半径 1〜1.5 画素で最大 0.05 画素ずれる(小数画素の位置を見るなら gaussian、1e-3 画素以内)。over は点ごとの不透明度で重ねるので、奥の密度は手前に隠れる —— 数を見るなら add。点 × 足跡の組が 4,000 万を超える描画は拒否する。
calibration: 画素校正は無い。縮尺が要るなら K の fx(画素 / 座標単位)から スケールバーを置く(annotate_scale_bar)。
---

# 点群をそのまま色の絵にする

## できること

面を張れない点群 —— 細胞の位置、LiDAR、SfM の疎な点、粒子 —— を、点のまま RGB の絵にします。点は小数画素の位置に足跡(gaussian / disc / point)を落とし、**深さの順に**アルファ合成(over)するか、**光の総量を保って**足します(add、数の密度の地図になる)。カメラは `project_points` / `render_point_depth` と同じ OpenCV の規約(+Z が前)で、正射影は K を省くと点群を画像に収めます。

## What it does

Draws a point cloud that has no surface — cell positions, LiDAR returns, sparse SfM points, particles — as an RGB image. Each point drops a sub-pixel footprint (gaussian / disc / point) that is alpha-composited in depth order (over) or added with the total light conserved (add, a density map). The camera follows the OpenCV convention of `project_points` / `render_point_depth`; an orthographic render fits the cloud to the image when K is omitted.

## 向くところ / 向かないところ

**向く**: 数万〜十数万点の分布の全体像(`poc_flybrain_pointcloud`: ハエの脳の細胞体 126,104 個を 1 枚 0.3 秒)。クラスで色を分ける図、回転の GIF、密度の地図。

**向かない**: ★面の陰影や法線が要る絵 —— 点に法線は無い。メッシュなら `render_mesh`、3DGS なら `gs_render`。★深度の値そのものが要るとき —— `render_point_depth`(1 点 1 画素の z-buffer)。★時間で変わる活動を載せる動画 —— `points_activity_video`。

## 推奨パイプライン

`points_render`

R, t でカメラを置き(正面・側面・背面は軸の入れ替えの行列)、色は (N, 3) で渡す。奥を暗くする `depth_cue` で奥行きが読みやすくなる。縮尺は `annotate_scale_bar`、凡例は `text_box` で絵の上に。

## 代替

深度だけなら `render_point_depth`、射影の座標だけなら `project_points`、活動の動画は `points_activity_video`、陰影つきのガウシアンは `gs_render`、メッシュは `render_mesh`。

## 限界

- disc の足跡は画素に量子化され、像の重心は小さな半径で最大 0.05 画素ずれる。gaussian は 1e-3 画素以内(4σ を軸ごとに切る。3σ で切ると 0.017 画素ずれた)。
- over では、奥の点は手前の不透明度ぶん隠れる。数(密度)を見るなら add —— 総和が点の色の総和と厳密に一致する。
- Z が等しい点どうしは入力の番号順で重なる(それ以外は入力の順に依らない)。

## 実寸校正

画素校正は無い。正射影なら K の fx が「画素 / 座標単位」なので、座標の単位(例: 8 nm のボクセル)を掛けてスケールバーにする。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

rng = np.random.default_rng(0)
pts = rng.normal(size=(20000, 3)) * [1.0, 0.6, 0.4]            # 楕円体の雲
cols = np.where(pts[:, :1] > 0, [1.0, 0.6, 0.2], [0.3, 0.7, 1.0])  # 左右で 2 色
img = fs.ledger.points_render(pts, colors=cols, size=(240, 320), opacity=0.4, depth_cue=0.5,
                              background=(0.05, 0.05, 0.08))
dens = fs.ledger.points_render(pts, colors=np.ones(3), size=(240, 320), composite="add",
                               background=(0.0, 0.0, 0.0))
print(img.shape, float(img.max()), "light kept:", round(float(dens.sum()), 6), "=", 3 * len(pts))
```
