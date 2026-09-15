---
id: volume-from-3d-scan
title: 3-D スキャンから体積・土量を出す
title_en: Turn a 3-D scan into a volume
category: 測る
ops: [mesh_volume, vol_rle_volume, interp_scattered, dem_slope]
examples: [poc_stockpile_volume, poc_lidar_terrain_change]
version: 0.1.11
inputs: [voxel, mesh]
pipeline: [vol_rle_components, vol_rle_volume, mesh_volume]
alternatives: [interp_scattered, dem_slope, dem_fill_sinks, marching_cubes]
limits: 底面が測れていない場面 —— 5 cm の仮定違いで 1.269 %(72.5 t)。外周平均の底面は誤差が打ち消して見えなくなる(`poc_stockpile_volume`)。
calibration: 格子間隔 [m] と高さ [m] の単位を揃える。ボクセル数はピッチの 3 乗。底面は**実際に見えた点だけ**で決める。
---

# 3-D スキャンから体積・土量を出す

## できること

点群や高さ格子から、閉じたメッシュの符号つき体積、voxel 領域の体積、2 つの面のあいだの土量を出します。欠測は補間で埋められますが、**その補間がどこまで効いたか**を別に持ち出せます。

## What it does

Compute a signed volume from a closed mesh, a voxel count from a labelled region, or the material between two surfaces from a height grid. Gaps can be filled by interpolation, and how far that interpolation reached is reported separately.

## 向くところ / 向かないところ

**向く**: 在庫量・掘削土量・欠損体積など、面と面のあいだの量。

**向かない**: ★**底面が測れていない場面**。在庫量は「誰も測っていない面」の仮定で決まり、5 cm の仮定違いが 1.269 %(かさ 1.6 t/m^3 で 72.5 t)動きます。しかも**現場の手(外周平均)だと誤差が打ち消し合って見えなくなる** ——`poc_stockpile_volume` がその罠を測っています。誤差を「底面 x % + 遮蔽 y %」と足す報告は、この時点で嘘になります。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

xs = np.arange(60) * 1.0
gx, gy = np.meshgrid(xs, xs)
surf = np.maximum(0.0, 12.0 - 0.4 * np.hypot(gx - 30, gy - 30))   # 円錐
print('体積 =', float(surf.sum()) * 1.0 * 1.0, 'm^3')             # ΔV = Σh·A
```

## 推奨パイプライン

`vol_rle_components` → `vol_rle_volume` → `mesh_volume`

`vol_rle_components` で voxel 領域を分け → `vol_rle_volume` で体積 → 閉メッシュがあるなら `mesh_volume` で符号つき体積と突き合わせる。

## 代替

欠測は `interp_scattered`(外挿率を必ず見る)、高さ格子の傾きは `dem_slope`、窪地は `dem_fill_sinks`、等値面は `marching_cubes`。

## 限界

底面が測れていない場面 —— 5 cm の仮定違いで 1.269 %(72.5 t)。外周平均の底面は誤差が打ち消して見えなくなる(`poc_stockpile_volume`)。

## 実寸校正

格子間隔 [m] と高さ [m] の単位を揃える。ボクセル数はピッチの 3 乗。底面は**実際に見えた点だけ**で決める。

## 裏づけ

- op: `mesh_volume`(閉メッシュ)、`vol_rle_volume`(voxel 数)、`interp_scattered`(欠測の補間と**外挿率**)、`dem_slope`(面の傾き)
- 例: [`poc_stockpile_volume`](../../examples/poc_stockpile_volume.py)、[`poc_lidar_terrain_change`](../../examples/poc_lidar_terrain_change.py)
