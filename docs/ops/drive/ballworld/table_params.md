---
op: table_params
dim: drive
category: ballworld
in: 
out: table
examples: [poc_ball_bounce, poc_table_tennis_bounce, poc_table_tennis_spin]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# table_params — DRIVE `ballworld` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.table_params(length: 'float' = 2.74, width: 'float' = 1.525, height: 'float' = 0.76, net_height: 'float' = 0.1525, net_length: 'float' = 1.83, line_width: 'float' = 0.02, centre_line: 'float' = 0.003) -> 'dict'` (実装を直接呼ぶなら `import ballworld; ballworld.table_params(length: 'float' = 2.74, width: 'float' = 1.525, height: 'float' = 0.76, net_height: 'float' = 0.1525, net_length: 'float' = 1.83, line_width: 'float' = 0.02, centre_line: 'float' = 0.003) -> 'dict'`、台帳から引くなら `opsdrive.get("table_params")`)

## 使い方

卓球台の表(既定 = ITTF 規格)。

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

[table_world](table_world.md) · [ball_mesh](ball_mesh.md) · [add_ball](add_ball.md) · [ball_set_pose](ball_set_pose.md) · [rotation_from_omega](rotation_from_omega.md) · [camera_rig](camera_rig.md) · [ball_truth](ball_truth.md) · [icosphere](icosphere.md)

---
*Provenance: ballworld.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
