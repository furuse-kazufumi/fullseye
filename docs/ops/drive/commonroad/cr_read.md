---
op: cr_read
dim: drive
category: commonroad
in: any
out: table
examples: [poc_driving_commonroad]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# cr_read — DRIVE `commonroad` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.cr_read(source) -> 'dict'` (実装を直接呼ぶなら `import drivecommonroad; drivecommonroad.cr_read(source) -> 'dict'`、台帳から引くなら `opsdrive.get("cr_read")`)

## 使い方

CommonRoad 2020a XML(文字列 or パス)を読む。

返り値: ``{"kind": "commonroad_scene", "id", "dt", "version", "lanelets": {id: {"center" (n,2), "left", "right", "polygon",
"successors", "predecessors", "adj_left", "adj_right", "speed_limit_mps" | None, "stop_line" (2,2) | None,
"traffic_sign_ids", "traffic_light_ids", "length"}}, "obstacles": [{"id", "type", "static", "shape", "states" (T,5)
[time_step, x, y, orientation, velocity]}], "planning_problems": [{"id", "initial": {time_step, x, y, orientation,
velocity}, "goal": [{"time_step": (lo, hi), "position_lanelets" | None, "position_polygon" (k,2) | None,
"velocity": (lo, hi) | None, "orientation": (lo, hi) | None}]}], "traffic_signs": {id: {"element_ids", "additional",
"position"}}, "traffic_lights": {id: {"position", "cycle": [(color, duration)], "time_offset", "active", "direction"}}}``。

中心線は左右境界の平均(頂点数が揃っていることを要求)。標識 274 の additional_value[0] は m/s → float。

**Raises** ``ValueError``: 壊れた XML、ルートが commonRoad でない、commonRoadVersion ≠ 2020a、必須要素の欠落、矩形以外の障害物。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_commonroad](../../../../examples/poc_driving_commonroad.py) — `py -3.11 examples/poc_driving_commonroad.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`commonroad`)

[cr_synthetic](cr_synthetic.md) · [cr_route](cr_route.md) · [ks_step](ks_step.md) · [cr_drive](cr_drive.md) · [cr_drive_sweep](cr_drive_sweep.md) · [cr_feasible](cr_feasible.md) · [cr_collision](cr_collision.md) · [cr_solution_xml](cr_solution_xml.md)

---
*Provenance: drivecommonroad.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
