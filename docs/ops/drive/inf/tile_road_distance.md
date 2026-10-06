---
op: tile_road_distance
dim: drive
category: inf
in: any × any × table
out: any
examples: [poc_driving_endless_map]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# tile_road_distance — DRIVE `inf` op

- **データ種**: `any × any × table` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.tile_road_distance(i: 'int', j: 'int', x, y, tp: 'dict') -> 'np.ndarray'` (実装を直接呼ぶなら `import driveinf; driveinf.tile_road_distance(i: 'int', j: 'int', x, y, tp: 'dict') -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("tile_road_distance")`)

## 使い方

区画 (i, j) の中の点 (x, y)(区画の中の座標)から最寄りの道の中心線までの距離。★隣の 8 区画の道も見る
(隣の道を区画の中の座標へずらして)—— 継ぎ目の近くで両側の区画が同じ距離を出すため。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_endless_map](../../../../examples/poc_driving_endless_map.py) — `py -3.11 examples/poc_driving_endless_map.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`inf`)

[tile_hash](tile_hash.md) · [tile_uniform](tile_uniform.md) · [pose_normalize](pose_normalize.md) · [tile_params](tile_params.md) · [tile_edge_crossing](tile_edge_crossing.md) · [tile_roads](tile_roads.md) · [tile_height](tile_height.md) · [tile_mesh](tile_mesh.md)

---
*Provenance: driveinf.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
