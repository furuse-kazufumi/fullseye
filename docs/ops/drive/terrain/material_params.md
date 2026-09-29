---
op: material_params
dim: drive
category: terrain
in: 
out: table
examples: [poc_world_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# material_params — DRIVE `terrain` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.material_params(seed: 'int' = 0, grain: 'float' = 0.05, puddle_level: 'float' = 0.55, puddle_freq: 'float' = 0.6, stain_level: 'float' = 0.6, stain_freq: 'float' = 0.9, wear: 'float' = 0.6, wear_freq: 'float' = 2.0, grass_var: 'float' = 0.1, sky=(0.62, 0.75, 0.92)) -> 'dict'` (実装を直接呼ぶなら `import driveterrain; driveterrain.material_params(seed: 'int' = 0, grain: 'float' = 0.05, puddle_level: 'float' = 0.55, puddle_freq: 'float' = 0.6, stain_level: 'float' = 0.6, stain_freq: 'float' = 0.9, wear: 'float' = 0.6, wear_freq: 'float' = 2.0, grass_var: 'float' = 0.1, sky=(0.62, 0.75, 0.92)) -> 'dict'`、台帳から引くなら `opsdrive.get("material_params")`)

## 使い方

材質の表。puddle = Perlin(puddle_freq) > puddle_level の所(道の内側だけ、ラベル 11、色 = 写り込み refl·空 + (1−refl)·陰影つきの路面)、
stain = 同様に暗い染み(ラベルは道のまま、真値の場 "stain" に残る)、wear = 白線の摩耗率 clip(wear·(Perlin(wear_freq)·0.5+0.5)·2, 0, 1)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_world_terrain](../../../../examples/poc_world_terrain.py) — `py -3.11 examples/poc_world_terrain.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`terrain`)

[perlin2](perlin2.md) · [fbm_params](fbm_params.md) · [fbm_height](fbm_height.md) · [fbm_gradient](fbm_gradient.md) · [radial_periodogram](radial_periodogram.md) · [spectral_slope](spectral_slope.md) · [course_distance](course_distance.md) · [terrain_params](terrain_params.md)

---
*Provenance: driveterrain.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
