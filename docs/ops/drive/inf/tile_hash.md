---
op: tile_hash
dim: drive
category: inf
in: 
out: scalar
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# tile_hash — DRIVE `inf` op

- **データ種**: `なし` → `scalar`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.tile_hash(i: 'int', j: 'int', seed: 'int', salt: 'int' = 0) -> 'int'` (実装を直接呼ぶなら `import driveinf; driveinf.tile_hash(i: 'int', j: 'int', seed: 'int', salt: 'int' = 0) -> 'int'`、台帳から引くなら `opsdrive.get("tile_hash")`)

## 使い方

区画(か格子点・辺)の番号 (i, j) と世界の種・用途の塩から 64 ビットの整数を出す(SplitMix64 を 4 回、整数だけ)。
負の番号も扱う(2 の補数で 64 ビットに折る)。同じ入力なら環境に依らず同じ値。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [road_eval](../long/road_eval.md) · [long_simulate](../long/long_simulate.md) · [stopping_distance_grade](../long/stopping_distance_grade.md) · [stop_line_plan](../long/stop_line_plan.md) · [hill_hold_brake_min](../long/hill_hold_brake_min.md) · [hill_start_rollback](../long/hill_start_rollback.md) · [hill_start_command](../long/hill_start_command.md)

## 同カテゴリ(`inf`)

[tile_uniform](tile_uniform.md) · [pose_normalize](pose_normalize.md) · [tile_params](tile_params.md) · [tile_edge_crossing](tile_edge_crossing.md) · [tile_roads](tile_roads.md) · [tile_road_distance](tile_road_distance.md) · [tile_height](tile_height.md) · [tile_mesh](tile_mesh.md)

---
*Provenance: driveinf.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
