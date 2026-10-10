---
op: adg_execute
dim: drive
category: agv
in: table
out: table
examples: [poc_agv_fleet]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# adg_execute — DRIVE `agv` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.adg_execute(adg, delay_prob=0.3, seed=0, max_steps=10000)` (実装を直接呼ぶなら `import agvfleet; agvfleet.adg_execute(adg, delay_prob=0.3, seed=0, max_steps=10000)`、台帳から引くなら `opsdrive.get("adg_execute")`)

## 使い方

ADG に従って実行する。各時刻、各車両は確率 ``delay_prob`` で止まる(滑り・人・荷役の遅れ)。

次の行動の依存がすべて済んでいる車両だけが 1 マス進む。返りは dict: ``trajectories``(実際の位置の列)、
``makespan``、``collisions``(同じマス・すれ違い)、``deadlock``(誰も進めず未了)、``finished``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_agv_fleet](../../../../examples/poc_agv_fleet.py) — `py -3.11 examples/poc_agv_fleet.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`agv`)

[warehouse_grid](warehouse_grid.md) · [grid_distances](grid_distances.md) · [mapf_cbs](mapf_cbs.md) · [mapf_ecbs](mapf_ecbs.md) · [mapf_joint_astar](mapf_joint_astar.md) · [mapf_prioritized](mapf_prioritized.md) · [plan_conflicts](plan_conflicts.md) · [plan_cost](plan_cost.md)

---
*Provenance: agvfleet.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
