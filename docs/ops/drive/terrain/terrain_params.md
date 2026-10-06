---
op: terrain_params
dim: drive
category: terrain
in: 
out: table
examples: [poc_world_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# terrain_params — DRIVE `terrain` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.terrain_params(seed: 'int' = 0, hurst: 'float' = 0.8, amplitude: 'float' = 2.0, f_min: 'float' = 0.008333333333333333, f_max: 'float' = 0.16666666666666666, n_waves: 'int' = 128, flat: 'float' = 2.0, blend: 'float' = 10.0, road_amp: 'float' = 0.0, road_len=(160.0, 110.0), road_phase=(0.0, 1.0)) -> 'dict'` (実装を直接呼ぶなら `import driveterrain; driveterrain.terrain_params(seed: 'int' = 0, hurst: 'float' = 0.8, amplitude: 'float' = 2.0, f_min: 'float' = 0.008333333333333333, f_max: 'float' = 0.16666666666666666, n_waves: 'int' = 128, flat: 'float' = 2.0, blend: 'float' = 10.0, road_amp: 'float' = 0.0, road_len=(160.0, 110.0), road_phase=(0.0, 1.0)) -> 'dict'`、台帳から引くなら `opsdrive.get("terrain_params")`)

## 使い方

地形の表: fBm の起伏(道から ``flat`` m は 0、そこから ``blend`` m で smoothstep)+ 路面のうねり
``road_amp·½[sin(2πx/L₁+φ₁) + sin(2πy/L₂+φ₂)]``(道にも掛かる、勾配の上限 = road_amp·π/min(L))。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_world_terrain](../../../../examples/poc_world_terrain.py) — `py -3.11 examples/poc_world_terrain.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`terrain`)

[perlin2](perlin2.md) · [fbm_params](fbm_params.md) · [fbm_height](fbm_height.md) · [fbm_gradient](fbm_gradient.md) · [radial_periodogram](radial_periodogram.md) · [spectral_slope](spectral_slope.md) · [course_distance](course_distance.md) · [terrain_height](terrain_height.md)

---
*Provenance: driveterrain.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
