---
id: visual-hull-from-silhouettes
title: シルエットから立体を彫り出す(視体積交差)
title_en: Carve a solid out of silhouettes (visual hull)
category: 形にする
ops: [synthesize_silhouette, carve, visual_hull, carve_look_at]
examples: [space_carving, poc_livestock_body_volume]
version: 0.1.11
inputs: [points, images]
pipeline: [synthesize_silhouette, visual_hull, vol_rle_components, vol_rle_volume]
alternatives: [carve, carve_look_at, mesh_volume]
limits: 視体積交差は**必ず上界**。くぼみはカメラを増やしても残る(12 倍で 3.8 ポイント)。平行投影では偶数台の半分が無駄で 13 台が 16 台に勝つ。姿勢は OpenCV 規約(`carve_look_at`)。
calibration: K [px] と外部姿勢 [m] は校正済みのものを渡す。体積はボクセルピッチの 3 乗。シルエット 1 px の膨らみで体積 +3.21 %/px。
---

# シルエットから立体を彫り出す(視体積交差)

## できること

校正済みの複数カメラの前景マスクから、物体を必ず内包する体積を voxel として彫り出します。学習モデルも深度センサも要りません。

## What it does

From the foreground masks of several calibrated cameras, carve out a voxel volume that always contains the object. No learned model, no depth sensor.

## 向くところ / 向かないところ

**向く**: 掴む対象の当たり判定、occupancy grid の初期化、粗い体積推定。

**向かない**: ★**視体積交差は必ず上界**で、しかも**カメラを増やして消える誤差と消えない誤差があります** —— 脚の間の幽霊は 4→48 台で 5.2 倍減るのに、背中のくぼみは 12 倍にして 3.8 ポイントしか減りません(`poc_livestock_body_volume`)。★平行投影では**偶数台の半分が無駄**になり(向かい合う 2 台は同じ接線しか与えない)、**13 台が 16 台に勝ちます**。★姿勢は OpenCV 規約(+Z 前方)。`carve_look_at` を使ってください ——`fs.look_at` は OpenGL 規約の別物です。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

pts = np.random.default_rng(0).normal(0, 0.2, (2000, 3))
K = np.array([[600., 0, 320.], [0, 600., 240.], [0, 0, 1.]])
R, t = fs.ledger.carve_look_at((3.0, 0.0, 0.0), (0.0, 0.0, 0.0))
sil = fs.ledger.synthesize_silhouette(pts, K, R, t, (480, 640))
print('前景画素 =', int(np.asarray(sil).sum()))
```

## 推奨パイプライン

`synthesize_silhouette` → `visual_hull` → `vol_rle_components` → `vol_rle_volume`

`synthesize_silhouette` で校正済みカメラの前景マスク(検証用)→ `visual_hull` で彫り出し → `vol_rle_components` → `vol_rle_volume` で体積。

## 代替

1 台ずつ彫るなら `carve`、姿勢は `carve_look_at`(`fs.look_at` は OpenGL 規約の別物)。メッシュにしてからなら `mesh_volume`。

## 限界

視体積交差は**必ず上界**。くぼみはカメラを増やしても残る(12 倍で 3.8 ポイント)。平行投影では偶数台の半分が無駄で 13 台が 16 台に勝つ。姿勢は OpenCV 規約(`carve_look_at`)。

## 実寸校正

K [px] と外部姿勢 [m] は校正済みのものを渡す。体積はボクセルピッチの 3 乗。シルエット 1 px の膨らみで体積 +3.21 %/px。

## 裏づけ

- op: `synthesize_silhouette` / `carve` / `visual_hull` / `carve_look_at`
- 例: [`space_carving`](../../examples_3d/space_carving.py)、[`poc_livestock_body_volume`](../../examples/poc_livestock_body_volume.py)
