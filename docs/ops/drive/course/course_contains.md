---
op: course_contains
dim: drive
category: course
in: table × points
out: signal
examples: [poc_driving_school, poc_world_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# course_contains — DRIVE `course` op

- **データ種**: `table × points` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.course_contains(course, xy)` (実装を直接呼ぶなら `import drivecourse; drivecourse.course_contains(course, xy)`、台帳から引くなら `opsdrive.get("course_contains")`)

## 使い方

点が **走れる領域**(要素の多角形、配置なら要素の和)の内側かを偶奇規則で判定した bool 配列。

``xy`` は ``(N, 2)``(``(2,)`` なら bool スカラ)。境界上の点は未定義。要素ごとに bounds で先に篩う。

**Raises** ``ValueError``: course が dict でない・polygon が無い・xy の形が悪い・非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_school](../../../../examples/poc_driving_school.py) — `py -3.11 examples/poc_driving_school.py`
- [poc_world_terrain](../../../../examples/poc_world_terrain.py) — `py -3.11 examples/poc_world_terrain.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[flight_vacuum](../ball/flight_vacuum.md) · [magnus_lift_coefficient](../ball/magnus_lift_coefficient.md) · [drag_coefficient_sphere](../ball/drag_coefficient_sphere.md) · [restitution_from_apexes](../ball/restitution_from_apexes.md) · [restitution_from_intervals](../ball/restitution_from_intervals.md) · [fit_parabola](../ball/fit_parabola.md) · [flight_fit](../ball/flight_fit.md) · [fit_aero](../ball/fit_aero.md)

## 同カテゴリ(`course`)

[course_crank](course_crank.md) · [course_s_curve](course_s_curve.md) · [course_turnaround](course_turnaround.md) · [course_slope](course_slope.md) · [course_intersection](course_intersection.md) · [course_parallel_parking](course_parallel_parking.md) · [course_crossing](course_crossing.md) · [course_road](course_road.md)

---
*Provenance: drivecourse.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
