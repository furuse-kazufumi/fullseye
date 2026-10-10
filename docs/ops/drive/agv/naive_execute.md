---
op: naive_execute
dim: drive
category: agv
in: table
out: table
examples: [poc_agv_fleet]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# naive_execute — DRIVE `agv` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.naive_execute(paths, delay_prob=0.3, seed=0, max_steps=10000)` (実装を直接呼ぶなら `import agvfleet; agvfleet.naive_execute(paths, delay_prob=0.3, seed=0, max_steps=10000)`、台帳から引くなら `opsdrive.get("naive_execute")`)

## 使い方

比較用の素朴な実行: 計画の**マスの列**だけを使い、次のマスが空いていれば進む(順番の約束は無い)。

遅れが入ると、計画では時間差ですれ違うはずの 2 台が向かい合って止まる。返りは :func:`adg_execute` と
同じ形に ``waits_for``(デッドロックの瞬間の「誰が誰を待つか」の辺)を足したもの。

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
