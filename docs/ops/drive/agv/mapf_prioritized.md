---
op: mapf_prioritized
dim: drive
category: agv
in: image2d
out: table
examples: [poc_agv_fleet]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# mapf_prioritized — DRIVE `agv` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.mapf_prioritized(grid, starts, goals, order=None, horizon=None)` (実装を直接呼ぶなら `import agvfleet; agvfleet.mapf_prioritized(grid, starts, goals, order=None, horizon=None)`、台帳から引くなら `opsdrive.get("mapf_prioritized")`)

## 使い方

優先度付き計画: 順に 1 台ずつ、先に決まった車両の通り道(予約表)を避けて計画する。

速いが**不完全** —— 解がある問題でも、優先順によっては(どの順でも)見つけられない(Ma ら 2019)。
返りは dict: ``paths``(失敗なら None)、``cost``、``solved``、``failed_agent``(最初に詰まった車両)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_agv_fleet](../../../../examples/poc_agv_fleet.py) — `py -3.11 examples/poc_agv_fleet.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`agv`)

[warehouse_grid](warehouse_grid.md) · [grid_distances](grid_distances.md) · [mapf_cbs](mapf_cbs.md) · [mapf_ecbs](mapf_ecbs.md) · [mapf_joint_astar](mapf_joint_astar.md) · [plan_conflicts](plan_conflicts.md) · [plan_cost](plan_cost.md) · [adg_build](adg_build.md)

---
*Provenance: agvfleet.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
