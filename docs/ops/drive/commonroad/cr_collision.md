---
op: cr_collision
dim: drive
category: commonroad
in: table × table
out: table
examples: [poc_driving_commonroad]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# cr_collision — DRIVE `commonroad` op

- **データ種**: `table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.cr_collision(scene, run, *, margin: 'float' = 0.0, lanelets: 'str' = 'all') -> 'dict'` (実装を直接呼ぶなら `import drivecommonroad; drivecommonroad.cr_collision(scene, run, *, margin: 'float' = 0.0, lanelets: 'str' = 'all') -> 'dict'`、台帳から引くなら `opsdrive.get("cr_collision")`)

## 使い方

障害物との衝突(矩形同士の SAT、time_step ごと)と道路境界(車両 4 角が lanelet 多角形の和集合に入るか)。

``lanelets="all"``(既定)は場面の全 lanelet(採点器の boundary_collision と同じ範囲)、``"route"`` は経路の lanelet だけ。
``margin`` は障害物の SAT を膨らませる距離(m)。

返り値 ``{"obstacle_collision", "first_collision": (time_step, obstacle_id) | None, "boundary_violation",
"first_outside": time_step | None, "n_collisions", "n_outside"}``。

**Raises** ``ValueError``: scene / run が不正、lanelets が "all"/"route" 以外、margin < 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_commonroad](../../../../examples/poc_driving_commonroad.py) — `py -3.11 examples/poc_driving_commonroad.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`commonroad`)

[cr_synthetic](cr_synthetic.md) · [cr_read](cr_read.md) · [cr_route](cr_route.md) · [ks_step](ks_step.md) · [cr_drive](cr_drive.md) · [cr_drive_sweep](cr_drive_sweep.md) · [cr_feasible](cr_feasible.md) · [cr_solution_xml](cr_solution_xml.md)

---
*Provenance: drivecommonroad.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
