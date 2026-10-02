---
op: plan_command
dim: drive
category: long
in: table
out: any
examples: [poc_driving_longitudinal, poc_driving_weather]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# plan_command — DRIVE `long` op

- **データ種**: `table` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.plan_command(plan: 'dict', road=None, params: 'Optional[dict]' = None, hold_brake: 'Optional[float]' = None, before: 'Optional[Callable]' = None) -> 'Callable'` (実装を直接呼ぶなら `import drivelong; drivelong.plan_command(plan: 'dict', road=None, params: 'Optional[dict]' = None, hold_brake: 'Optional[float]' = None, before: 'Optional[Callable]' = None) -> 'Callable'`、台帳から引くなら `opsdrive.get("plan_command")`)

## 使い方

:func:`stop_line_plan` を ``command(t, s, v)`` にする。t0 より前は ``before``(None = 速さを保つ)、react / cruise は
速さを保つ(駆動 = 坂 + 転がり + 空気抵抗の打ち消し、下りで負なら制動)、brake1 / brake2 は計画の値、止まったら保持
(制動 ``hold_brake``(None = 上限)+ クリープの駆動)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_longitudinal](../../../../examples/poc_driving_longitudinal.py) — `py -3.11 examples/poc_driving_longitudinal.py`
- [poc_driving_weather](../../../../examples/poc_driving_weather.py) — `py -3.11 examples/poc_driving_weather.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`long`)

[long_params](long_params.md) · [road_profile](road_profile.md) · [road_eval](road_eval.md) · [long_simulate](long_simulate.md) · [long_energy_residual](long_energy_residual.md) · [stopping_distance_grade](stopping_distance_grade.md) · [stop_line_plan](stop_line_plan.md) · [hill_hold_brake_min](hill_hold_brake_min.md)

---
*Provenance: drivelong.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
