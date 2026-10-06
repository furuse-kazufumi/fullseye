---
op: tile_roads
dim: drive
category: inf
in: table
out: table
examples: [poc_driving_endless_map]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# tile_roads — DRIVE `inf` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.tile_roads(i: 'int', j: 'int', tp: 'dict') -> 'dict'` (実装を直接呼ぶなら `import driveinf; driveinf.tile_roads(i: 'int', j: 'int', tp: 'dict') -> 'dict'`、台帳から引くなら `opsdrive.get("tile_roads")`)

## 使い方

区画の中の道: 横切る点(区画の中の座標)と分岐点、分岐点から各点への線分。返り値
``{"hub" (2,), "ends" [(side, (x, y))], "segments" (K, 2, 2)}``(横切る点が無ければ空)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_endless_map](../../../../examples/poc_driving_endless_map.py) — `py -3.11 examples/poc_driving_endless_map.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`inf`)

[tile_hash](tile_hash.md) · [tile_uniform](tile_uniform.md) · [pose_normalize](pose_normalize.md) · [tile_params](tile_params.md) · [tile_edge_crossing](tile_edge_crossing.md) · [tile_road_distance](tile_road_distance.md) · [tile_height](tile_height.md) · [tile_mesh](tile_mesh.md)

---
*Provenance: driveinf.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
