---
op: icosphere
dim: drive
category: ballworld
in: 
out: any
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# icosphere — DRIVE `ballworld` op

- **データ種**: `なし` → `any`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.icosphere(radius: 'float' = 1.0, subdiv: 'int' = 3)` (実装を直接呼ぶなら `import ballworld; ballworld.icosphere(radius: 'float' = 1.0, subdiv: 'int' = 3)`、台帳から引くなら `opsdrive.get("icosphere")`)

## 使い方

正 20 面体を ``subdiv`` 回 4 分割して球面へ射影したメッシュ (V, F)(外向き)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`ballworld`)

[table_params](table_params.md) · [table_world](table_world.md) · [ball_mesh](ball_mesh.md) · [add_ball](add_ball.md) · [ball_set_pose](ball_set_pose.md) · [rotation_from_omega](rotation_from_omega.md) · [camera_rig](camera_rig.md) · [ball_truth](ball_truth.md)

---
*Provenance: ballworld.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
