---
op: adg_build
dim: drive
category: agv
in: table
out: table
examples: [poc_agv_fleet]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# adg_build — DRIVE `agv` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.adg_build(paths)` (実装を直接呼ぶなら `import agvfleet; agvfleet.adg_build(paths)`、台帳から引くなら `opsdrive.get("adg_build")`)

## 使い方

行動依存グラフ(Hönig, Kiesel, Tinka, Durham, Ayanian 2019)。

各車両の行動 = 「訪れるマスの列の k 番目に入る」。依存は 2 種類:
(1) 同じ車両の前の行動、(2) **同じマスを先に使う他車がそのマスを出ること**(計画の時刻順)。
返りは dict: ``cells``(各車両のマスの列)、``deps``(``(i, k)`` → それより先に終わるべき ``(j, m)`` の集合)。
計画に衝突があれば ValueError(依存の向きが決まらない)。

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
