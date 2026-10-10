---
op: tree_mesh
dim: drive
category: terrain
in: 
out: table
examples: [poc_world_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# tree_mesh — DRIVE `terrain` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.tree_mesh(height: 'float' = 6.0, trunk_radius: 'float' = 0.15, crown_radius: 'float' = 1.8, kind: 'str' = 'broadleaf', n: 'int' = 8, color=None) -> 'dict'` (実装を直接呼ぶなら `import driveterrain; driveterrain.tree_mesh(height: 'float' = 6.0, trunk_radius: 'float' = 0.15, crown_radius: 'float' = 1.8, kind: 'str' = 'broadleaf', n: 'int' = 8, color=None) -> 'dict'`、台帳から引くなら `opsdrive.get("tree_mesh")`)

## 使い方

手続き的な木: 幹 = 正 n 角柱(高さ 0.35·height)、樹冠 = 円錐(conifer)か回転楕円体(broadleaf、上下 0.65·height)。

返り値 ``{"V", "F", "color" (M,3), "label" (13), "dims", "volume"}``。``volume`` は閉形式: 幹 = ½ n r² sin(2π/n)·h_t、
円錐 = ⅓·½ n R² sin(2π/n)·h_c(多角形の底面なので厳密)、楕円体は内接なので mesh_signed_volume ≤ 4/3·π R² (h_c/2)。

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
