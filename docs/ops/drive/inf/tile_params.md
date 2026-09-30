---
op: tile_params
dim: drive
category: inf
in: 
out: table
examples: [poc_driving_endless_map]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# tile_params — DRIVE `inf` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.tile_params(tile: 'float' = 200.0, cells: 'int' = 8, relief: 'float' = 6.0, road_width: 'float' = 7.0, flat: 'float' = 18.0, blend: 'float' = 20.0, p_road: 'float' = 0.85, jitter: 'float' = 0.25, seed: 'int' = 20261001) -> 'dict'` (実装を直接呼ぶなら `import driveinf; driveinf.tile_params(tile: 'float' = 200.0, cells: 'int' = 8, relief: 'float' = 6.0, road_width: 'float' = 7.0, flat: 'float' = 18.0, blend: 'float' = 20.0, p_road: 'float' = 0.85, jitter: 'float' = 0.25, seed: 'int' = 20261001) -> 'dict'`、台帳から引くなら `opsdrive.get("tile_params")`)

## 使い方

区画の表。``tile`` = 一辺 [m]、``cells`` = 区画あたりの格子の升目数(起伏の波長 ≈ tile/cells)、``relief`` = 起伏の振幅 [m]、
``road_width`` [m]、道から ``flat`` m は平ら、そこから ``blend`` m で起伏へ戻す(★flat は地面の格子の三角形が道に掛かっても
地面が道より上に出ない幅: 道幅の半分 + 格子の対角 —— 10 m の格子で 3.5 + 14.1 ≈ 18 m。6 m では道が地面に埋もれた)、``p_road`` = 辺を道が横切る確率、
``jitter`` = 区画の中の分岐点のずらし(区画の一辺に対する割合)、``seed`` = 世界の種。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_endless_map](../../../../examples/poc_driving_endless_map.py) — `py -3.11 examples/poc_driving_endless_map.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`inf`)

[tile_hash](tile_hash.md) · [tile_uniform](tile_uniform.md) · [pose_normalize](pose_normalize.md) · [tile_edge_crossing](tile_edge_crossing.md) · [tile_roads](tile_roads.md) · [tile_road_distance](tile_road_distance.md) · [tile_height](tile_height.md) · [tile_mesh](tile_mesh.md)

---
*Provenance: driveinf.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
