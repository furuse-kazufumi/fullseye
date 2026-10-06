---
op: world_materials
dim: drive
category: terrain
in: table × table × matrix × matrix × table
out: table
examples: [poc_world_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# world_materials — DRIVE `terrain` op

- **データ種**: `table × table × matrix × matrix × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.world_materials(world: 'dict', view: 'dict', pose, K, m: 'dict') -> 'dict'` (実装を直接呼ぶなら `import driveterrain; driveterrain.world_materials(world: 'dict', view: 'dict', pose, K, m: 'dict') -> 'dict'`、台帳から引くなら `opsdrive.get("world_materials")`)

## 使い方

描画結果 ``view``(world_camera、"shade" を含む)に路面の材質を画素ごとに掛ける。

路面(ラベル 0)と地形(10)の画素は世界座標で材質を評価し直す: アスファルトの粒(Perlin 8 周期/m)、草の色むら、
染み(暗い斑、ラベルは 0 のまま)、水溜り(空の写り込み、ラベル 11)。白線・横断歩道(9・12)は摩耗率 wear で
路面の色に混ぜる(ラベルは不変、真値 "wear" に残る)。水溜りの写り込みの強さ(0.1〜0.9、Perlin 1.5 周期/m)は真値 "refl"。
返り値 = ``{"color", "label", "puddle", "refl", "stain", "wear", "xyz"}``。

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
