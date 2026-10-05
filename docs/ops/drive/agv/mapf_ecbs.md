---
op: mapf_ecbs
dim: drive
category: agv
in: image2d
out: table
examples: [poc_agv_fleet]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# mapf_ecbs — DRIVE `agv` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.mapf_ecbs(grid, starts, goals, w=1.2, max_nodes=50000, horizon=None)` (実装を直接呼ぶなら `import agvfleet; agvfleet.mapf_ecbs(grid, starts, goals, w=1.2, max_nodes=50000, horizon=None)`、台帳から引くなら `opsdrive.get("mapf_ecbs")`)

## 使い方

上段を焦点探索にした CBS(ECBS の上段と同じ考え方、Barer ら 2014)。総コストが **最適の w 倍以内**。

開いている節のうち最小の総コスト ``LB`` は最適値以下(最適解はどれかの節の下にある)。そこで
``コスト ≤ w · LB`` の節(焦点)の中から**衝突の少ない**ものを展開する。返す計画は
``cost ≤ w · LB ≤ w · 最適``(門)。返りは :func:`mapf_cbs` の dict に ``lower_bound`` と ``w`` を足したもの。
細い通路で最適の CBS が同じ長さの譲り合いの組を全部調べて止まるのを、衝突の少ない側へ寄せて抜ける。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_agv_fleet](../../../../examples/poc_agv_fleet.py) — `py -3.11 examples/poc_agv_fleet.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`agv`)

[warehouse_grid](warehouse_grid.md) · [grid_distances](grid_distances.md) · [mapf_cbs](mapf_cbs.md) · [mapf_joint_astar](mapf_joint_astar.md) · [mapf_prioritized](mapf_prioritized.md) · [plan_conflicts](plan_conflicts.md) · [plan_cost](plan_cost.md) · [adg_build](adg_build.md)

---
*Provenance: agvfleet.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
