---
id: geodetic-frames
title: 地球規模の座標に載せる(ECEF と測地座標)
title_en: Put measurements on the Earth (ECEF and geodetic)
category: 測る
ops: [dem_geodetic_to_ecef, dem_ecef_to_geodetic]
examples: [poc_geodetic_height_frames, dem_geodesy_tour]
version: 0.1.11
---

# 地球規模の座標に載せる(ECEF と測地座標)

## できること

緯度・経度・高さと地球中心直交座標(ECEF)を往復します。往復の誤差の床は実測で緯度 6.4e-12 度・高さ 8.5e-07 m(緯度 ±85 度・高さ -500〜9000 m の 4000 点、最大値)。

## What it does

Convert between geodetic (latitude, longitude, height) and Earth-centred Cartesian (ECEF) coordinates. The round-trip floor measures 6.4e-12 degrees in latitude and 8.5e-07 m in height (worst case over 4000 points).

## 向くところ / 向かないところ

**向く**: 測量成果・GNSS・広域の点群を 1 つの枠に載せる前処理。

**向かない**: ★**鎖はまだ途中までしかありません** —— ジオイド高、標高(正標高)、局所 ENU、測地成果(datum)の変換、epoch の移動は**どれも未実装**(2026-09-08 実測: `op_find('geoid')` / `('enu')` / `('datum')` はいずれも 0 件)。GNSS が返すのは楕円体高で、地図と設計図が使うのは標高です。この 2 つを取り違えると日本付近で **30〜40 m** 静かにずれます ——`poc_geodetic_height_frames` がその伝播を量ごとに分けて測っています。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

xyz = np.asarray(fs.ledger.dem_geodetic_to_ecef(35.68, 139.77, 40.0))
back = np.asarray(fs.ledger.dem_ecef_to_geodetic(xyz))
print(back.ravel())                       # 35.68, 139.77, 40.0 に戻る
```

## 裏づけ

- op: `dem_geodetic_to_ecef` / `dem_ecef_to_geodetic`
- 例: [`poc_geodetic_height_frames`](../../examples/poc_geodetic_height_frames.py)、[`dem_geodesy_tour`](../../examples/dem_geodesy_tour.py)
