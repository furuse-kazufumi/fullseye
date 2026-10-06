---
op: global_to_tile
dim: drive
category: inf
in: 
out: any
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# global_to_tile — DRIVE `inf` op

- **データ種**: `なし` → `any`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.global_to_tile(X: 'float', Y: 'float', tile: 'float')` (実装を直接呼ぶなら `import driveinf; driveinf.global_to_tile(X: 'float', Y: 'float', tile: 'float')`、台帳から引くなら `opsdrive.get("global_to_tile")`)

## 使い方

全体の座標 → (i, j, x, y)(比較用。遠い座標は既に浮動小数の刻みで丸まっている)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`inf`)

[tile_hash](tile_hash.md) · [tile_uniform](tile_uniform.md) · [pose_normalize](pose_normalize.md) · [tile_params](tile_params.md) · [tile_edge_crossing](tile_edge_crossing.md) · [tile_roads](tile_roads.md) · [tile_road_distance](tile_road_distance.md) · [tile_height](tile_height.md)

---
*Provenance: driveinf.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
