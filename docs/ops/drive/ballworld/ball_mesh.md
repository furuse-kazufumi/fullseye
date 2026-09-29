---
op: ball_mesh
dim: drive
category: ballworld
in: 
out: table
examples: [poc_ball_bounce]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# ball_mesh — DRIVE `ballworld` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.ball_mesh(radius: 'float' = 0.02, subdiv: 'int' = 3, color=(1.0, 0.55, 0.05), marker_dir=(0.0, 0.0, 1.0), marker_angle: 'float' = 25.0, marker_color=(0.05, 0.05, 0.05), markers=None) -> 'dict'` (実装を直接呼ぶなら `import ballworld; ballworld.ball_mesh(radius: 'float' = 0.02, subdiv: 'int' = 3, color=(1.0, 0.55, 0.05), marker_dir=(0.0, 0.0, 1.0), marker_angle: 'float' = 25.0, marker_color=(0.05, 0.05, 0.05), markers=None) -> 'dict'`、台帳から引くなら `opsdrive.get("ball_mesh")`)

## 使い方

球のメッシュ(原点 = 中心)と模様。``markers`` = [(dir, angle_deg), …] で複数の模様(None なら marker_dir 1 つ)。
返り値 ``{"V", "F", "color" (M,3), "label" (M,) (23 or 24), "radius", "markers": [単位ベクトル …]}``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ball_bounce](../../../../examples/poc_ball_bounce.py) — `py -3.11 examples/poc_ball_bounce.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`ballworld`)

[table_params](table_params.md) · [table_world](table_world.md) · [add_ball](add_ball.md) · [ball_set_pose](ball_set_pose.md) · [rotation_from_omega](rotation_from_omega.md) · [camera_rig](camera_rig.md) · [ball_truth](ball_truth.md) · [icosphere](icosphere.md)

---
*Provenance: ballworld.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
