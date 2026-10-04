---
op: cr_solution_xml
dim: drive
category: commonroad
in: table × table
out: any
examples: [poc_driving_commonroad]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# cr_solution_xml — DRIVE `commonroad` op

- **データ種**: `table × table` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.cr_solution_xml(scene, run, *, vehicle_model: 'str' = 'KS', vehicle_type: 'str' = 'BMW_320i', cost: 'str' = 'JB1', benchmark_version: 'str' = '2020a', date=None) -> 'str'` (実装を直接呼ぶなら `import drivecommonroad; drivecommonroad.cr_solution_xml(scene, run, *, vehicle_model: 'str' = 'KS', vehicle_type: 'str' = 'BMW_320i', cost: 'str' = 'JB1', benchmark_version: 'str' = '2020a', date=None) -> 'str'`、台帳から引くなら `opsdrive.get("cr_solution_xml")`)

## 使い方

公式 solution XML(commonroad-io ``CommonRoadSolutionWriter`` と同じ形)を文字列で返す。

``<CommonRoadSolution benchmark_id="KS2:JB1:<scenario id>:2020a" date="YYYY-MM-DDTHH:MM:SS">`` の中に
``<ksTrajectory planningProblem="<pp id>">`` と ``ksState{x, y, steeringAngle, velocity, orientation, time}``。
位置は **車両中心**(run["x"], run["y"])。``date`` を渡すと再現可能(省略で今)。

**Raises** ``ValueError``: vehicle_model が "KS" 以外(状態が KS の物なので)、vehicle_type が未知、run が不正。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_commonroad](../../../../examples/poc_driving_commonroad.py) — `py -3.11 examples/poc_driving_commonroad.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`commonroad`)

[cr_synthetic](cr_synthetic.md) · [cr_read](cr_read.md) · [cr_route](cr_route.md) · [ks_step](ks_step.md) · [cr_drive](cr_drive.md) · [cr_drive_sweep](cr_drive_sweep.md) · [cr_feasible](cr_feasible.md) · [cr_collision](cr_collision.md)

---
*Provenance: drivecommonroad.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
