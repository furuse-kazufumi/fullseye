---
op: add_ball
dim: drive
category: ballworld
in: table × table
out: scalar
examples: [poc_ball_bounce, poc_table_tennis_spin]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# add_ball — DRIVE `ballworld` op

- **データ種**: `table × table` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.add_ball(world: 'dict', mesh: 'dict', p, R=None, *, name: 'str' = 'ball') -> 'int'` (実装を直接呼ぶなら `import ballworld; ballworld.add_ball(world: 'dict', mesh: 'dict', p, R=None, *, name: 'str' = 'ball') -> 'int'`、台帳から引くなら `opsdrive.get("add_ball")`)

## 使い方

球を姿勢 (p, R) で世界に足す。面ごとのラベル(球 23 / 模様 24)はそのまま。返り値 = objects の索引。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ball_bounce](../../../../examples/poc_ball_bounce.py) — `py -3.11 examples/poc_ball_bounce.py`
- [poc_table_tennis_spin](../../../../examples/poc_table_tennis_spin.py) — `py -3.11 examples/poc_table_tennis_spin.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[road_eval](../long/road_eval.md) · [long_simulate](../long/long_simulate.md) · [stopping_distance_grade](../long/stopping_distance_grade.md) · [stop_line_plan](../long/stop_line_plan.md) · [hill_hold_brake_min](../long/hill_hold_brake_min.md) · [hill_start_rollback](../long/hill_start_rollback.md) · [hill_start_command](../long/hill_start_command.md) · [julian_day](../env/julian_day.md)

## 同カテゴリ(`ballworld`)

[table_params](table_params.md) · [table_world](table_world.md) · [ball_mesh](ball_mesh.md) · [ball_set_pose](ball_set_pose.md) · [rotation_from_omega](rotation_from_omega.md) · [camera_rig](camera_rig.md) · [ball_truth](ball_truth.md) · [icosphere](icosphere.md)

---
*Provenance: ballworld.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
