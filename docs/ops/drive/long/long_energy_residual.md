---
op: long_energy_residual
dim: drive
category: long
in: table
out: any
examples: [poc_driving_longitudinal]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# long_energy_residual — DRIVE `long` op

- **データ種**: `table` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.long_energy_residual(res: 'dict', v0: 'Optional[float]' = None) -> 'np.ndarray'` (実装を直接呼ぶなら `import drivelong; drivelong.long_energy_residual(res: 'dict', v0: 'Optional[float]' = None) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("long_energy_residual")`)

## 使い方

エネルギー収支の残差(単位質量あたり [J/kg]): (½ v² + g z) − (½ v₀² + g z₀ + W_drive − W_brake − W_rr − W_drag)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_longitudinal](../../../../examples/poc_driving_longitudinal.py) — `py -3.11 examples/poc_driving_longitudinal.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`long`)

[long_params](long_params.md) · [road_profile](road_profile.md) · [road_eval](road_eval.md) · [long_simulate](long_simulate.md) · [stopping_distance_grade](stopping_distance_grade.md) · [stop_line_plan](stop_line_plan.md) · [plan_command](plan_command.md) · [hill_hold_brake_min](hill_hold_brake_min.md)

---
*Provenance: drivelong.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
