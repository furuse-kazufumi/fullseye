---
id: terrain-and-visibility
title: 地形の傾き・水の流れ・見通しを測る
title_en: Slope, flow and line of sight on a terrain
category: 測る
ops: [dem_slope, dem_aspect, dem_viewshed, dem_flow_direction]
examples: [poc_dem_terrain, dem_terrain_analysis_tour]
version: 0.1.11
inputs: [depth]
pipeline: [dem_fill_sinks, dem_slope, dem_aspect, dem_flow_direction, dem_viewshed]
alternatives: [dem_hillshade, dem_flow_accumulation, dem_geodetic_slope]
limits: 格子の刻みより細かい地形は出ない。可視領域は 1 観測点ぶん。測線の継ぎ目が地形に無い崖を作る(2.99 度 → 49.4 度、`poc_stockpile_volume`)。
calibration: `cell_size` [m] を渡す —— 傾斜は高さと格子間隔の**比**なので、単位が揃っていないと角度が全部ずれる。
---

# 地形の傾き・水の流れ・見通しを測る

## できること

高さ格子(DEM)から、傾斜・斜面方位・可視領域・流向を出します。いずれも閉形式と突き合わせられる量なので、実装の誤りを数字で捕まえられます。

## What it does

From a height grid: slope, aspect, viewshed and flow direction. Each has a closed form to check against, so an implementation error shows up as a number.

## 向くところ / 向かないところ

**向く**: 測量・防災・インフラ点検・ロボットの通行判定。

**向かない**: 格子の刻みより細かい地形。★可視領域は **1 観測点ぶん**しか出せません(複数点の和や走査計画は未実装)。★見かけの傾斜は、測線の継ぎ目で**地形に無い崖**を作ります ——`poc_stockpile_volume` で継ぎ目なし 2.99 度に対し継ぎ目あり 49.4 度。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

dem = np.zeros((41, 41))
dem[20, 30] = 10.0                                   # 平地に立つ柱
vis = fs.ledger.dem_viewshed(dem, 1.0, (20, 5), observer_height_m=2.0)
print('柱は見えるか:', vis[20, 30] == 1.0)
```

## 推奨パイプライン

`dem_fill_sinks` → `dem_slope` → `dem_aspect` → `dem_flow_direction` → `dem_viewshed`

`dem_fill_sinks` で窪地を埋め → `dem_slope` / `dem_aspect` で傾斜と方位 → `dem_flow_direction` で流向 → `dem_viewshed` で観測点からの可視領域。

## 代替

見せるなら `dem_hillshade`、集水量は `dem_flow_accumulation`、測地座標の格子なら `dem_geodetic_slope`。

## 限界

格子の刻みより細かい地形は出ない。可視領域は 1 観測点ぶん。測線の継ぎ目が地形に無い崖を作る(2.99 度 → 49.4 度、`poc_stockpile_volume`)。

## 実寸校正

`cell_size` [m] を渡す —— 傾斜は高さと格子間隔の**比**なので、単位が揃っていないと角度が全部ずれる。

## 裏づけ

- op: `dem_slope` / `dem_aspect` / `dem_viewshed` / `dem_flow_direction`
- 例: [`poc_dem_terrain`](../../examples/poc_dem_terrain.py)、[`dem_terrain_analysis_tour`](../../examples/dem_terrain_analysis_tour.py)
