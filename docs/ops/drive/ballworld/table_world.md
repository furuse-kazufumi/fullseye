---
op: table_world
dim: drive
category: ballworld
in: table
out: table
examples: [poc_ball_bounce, poc_table_tennis_bounce, poc_table_tennis_spin]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# table_world — DRIVE `ballworld` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.table_world(tp: 'dict' = None, *, floor: 'bool' = True, floor_size: 'float' = 8.0) -> 'dict'` (実装を直接呼ぶなら `import ballworld; ballworld.table_world(tp: 'dict' = None, *, floor: 'bool' = True, floor_size: 'float' = 8.0) -> 'dict'`、台帳から引くなら `opsdrive.get("table_world")`)

## 使い方

台(天板 + 白線 + ネット)と床の世界。原点 = 天板の中心、x = 長手(±1.37)、y = 幅(±0.7625)、z 上。天板の上面 z = height。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ball_bounce](../../../../examples/poc_ball_bounce.py) — `py -3.11 examples/poc_ball_bounce.py`
- [poc_table_tennis_bounce](../../../../examples/poc_table_tennis_bounce.py) — `py -3.11 examples/poc_table_tennis_bounce.py`
- [poc_table_tennis_spin](../../../../examples/poc_table_tennis_spin.py) — `py -3.11 examples/poc_table_tennis_spin.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`ballworld`)

[table_params](table_params.md) · [ball_mesh](ball_mesh.md) · [add_ball](add_ball.md) · [ball_set_pose](ball_set_pose.md) · [rotation_from_omega](rotation_from_omega.md) · [camera_rig](camera_rig.md) · [ball_truth](ball_truth.md) · [icosphere](icosphere.md)

---
*Provenance: ballworld.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
