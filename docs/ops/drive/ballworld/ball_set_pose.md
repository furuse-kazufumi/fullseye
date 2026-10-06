---
op: ball_set_pose
dim: drive
category: ballworld
in: table × matrix
out: any
examples: [poc_ball_bounce, poc_table_tennis_bounce, poc_table_tennis_spin]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# ball_set_pose — DRIVE `ballworld` op

- **データ種**: `table × matrix` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.ball_set_pose(world: 'dict', i: 'int', p, R) -> 'None'` (実装を直接呼ぶなら `import ballworld; ballworld.ball_set_pose(world: 'dict', i: 'int', p, R) -> 'None'`、台帳から引くなら `opsdrive.get("ball_set_pose")`)

## 使い方

球 i の姿勢を (p, R) にする(頂点だけ書き換える)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ball_bounce](../../../../examples/poc_ball_bounce.py) — `py -3.11 examples/poc_ball_bounce.py`
- [poc_table_tennis_bounce](../../../../examples/poc_table_tennis_bounce.py) — `py -3.11 examples/poc_table_tennis_bounce.py`
- [poc_table_tennis_spin](../../../../examples/poc_table_tennis_spin.py) — `py -3.11 examples/poc_table_tennis_spin.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`ballworld`)

[table_params](table_params.md) · [table_world](table_world.md) · [ball_mesh](ball_mesh.md) · [add_ball](add_ball.md) · [rotation_from_omega](rotation_from_omega.md) · [camera_rig](camera_rig.md) · [ball_truth](ball_truth.md) · [icosphere](icosphere.md)

---
*Provenance: ballworld.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
