---
op: ken_set_pose
dim: drive
category: kendamaworld
in: table × matrix
out: any
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# ken_set_pose — DRIVE `kendamaworld` op

- **データ種**: `table × matrix` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.ken_set_pose(world: 'dict', i: 'int', p, R) -> 'None'` (実装を直接呼ぶなら `import kendamaworld; kendamaworld.ken_set_pose(world: 'dict', i: 'int', p, R) -> 'None'`、台帳から引くなら `opsdrive.get("ken_set_pose")`)

## 使い方

けん i の姿勢を (p, R) にする(頂点だけ書き換える)。けんでない物体は ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`kendamaworld`)

[ken_mesh](ken_mesh.md) · [add_ken](add_ken.md) · [string_mesh](string_mesh.md) · [add_string](add_string.md) · [string_set](string_set.md) · [kendama_world](kendama_world.md) · [kendama_rig](kendama_rig.md) · [ken_truth](ken_truth.md)

---
*Provenance: kendamaworld.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
