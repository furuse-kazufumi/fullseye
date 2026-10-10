---
op: warehouse_grid
dim: drive
category: agv
in: 
out: any
examples: [poc_agv_fleet]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# warehouse_grid — DRIVE `agv` op

- **データ種**: `なし` → `any`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.warehouse_grid(n_rack_rows=3, n_rack_cols=4, rack_len=4, aisle=1, margin=2)` (実装を直接呼ぶなら `import agvfleet; agvfleet.warehouse_grid(n_rack_rows=3, n_rack_cols=4, rack_len=4, aisle=1, margin=2)`、台帳から引くなら `opsdrive.get("warehouse_grid")`)

## 使い方

棚の列と通路でできた倉庫の格子(True = 走れる)。

棚は横長の 1 行 × ``rack_len`` マスのブロックで、上下左右を幅 ``aisle`` の通路が囲む。外周に ``margin``
マスの走行帯(ステーションの前)を置く。返りは ``(grid, info)``、info に棚のマスの一覧と外周の帯。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_agv_fleet](../../../../examples/poc_agv_fleet.py) — `py -3.11 examples/poc_agv_fleet.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`agv`)

[grid_distances](grid_distances.md) · [mapf_cbs](mapf_cbs.md) · [mapf_ecbs](mapf_ecbs.md) · [mapf_joint_astar](mapf_joint_astar.md) · [mapf_prioritized](mapf_prioritized.md) · [plan_conflicts](plan_conflicts.md) · [plan_cost](plan_cost.md) · [adg_build](adg_build.md)

---
*Provenance: agvfleet.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
