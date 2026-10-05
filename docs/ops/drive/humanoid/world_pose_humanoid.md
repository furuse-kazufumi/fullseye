---
op: world_pose_humanoid
dim: drive
category: humanoid
in: table
out: any
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# world_pose_humanoid — DRIVE `humanoid` op

- **データ種**: `table` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.world_pose_humanoid(world: 'dict', i: 'int', clip: 'dict', distance: 'float', x: 'float', y: 'float', yaw: 'float') -> 'None'` (実装を直接呼ぶなら `import drivehumanoid; drivehumanoid.world_pose_humanoid(world: 'dict', i: 'int', clip: 'dict', distance: 'float', x: 'float', y: 'float', yaw: 'float') -> 'None'`、台帳から引くなら `opsdrive.get("world_pose_humanoid")`)

## 使い方

世界の物体 ``i``(:func:`driveterrain.add_mesh_object` で ``humanoid_clip_mesh`` を置いたもの)を、歩いた距離
``distance`` の姿勢にして ``(x, y, yaw)`` へ置き直す(頂点だけ書き換える。面・色・ラベル・``dims`` は不変)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`humanoid`)

[humanoid_clip_mesh](humanoid_clip_mesh.md) · [humanoid_impostors](humanoid_impostors.md) · [world_camera_impostors](world_camera_impostors.md)

---
*Provenance: drivehumanoid.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
