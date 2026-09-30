---
op: hill_start_command
dim: drive
category: long
in: scalar × scalar × scalar × scalar
out: any
examples: [poc_driving_longitudinal]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# hill_start_command — DRIVE `long` op

- **データ種**: `scalar × scalar × scalar × scalar` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.hill_start_command(t_release: 'float', tau: 'float', a_drive: 'float', b_hold: 'float', a_creep: 'float' = 0.0, technique: 'str' = 'gap', v_cruise: 'Optional[float]' = None) -> 'Callable'` (実装を直接呼ぶなら `import drivelong; drivelong.hill_start_command(t_release: 'float', tau: 'float', a_drive: 'float', b_hold: 'float', a_creep: 'float' = 0.0, technique: 'str' = 'gap', v_cruise: 'Optional[float]' = None) -> 'Callable'`、台帳から引くなら `opsdrive.get("hill_start_command")`)

## 使い方

坂道発進の指令。t_release までは保持(クリープ + 制動 b_hold)。

* ``technique="gap"``: t_release でブレーキを離し、τ 後に駆動 a_drive(足を踏み替える間 = ずり下がる。閉形式は
  :func:`hill_start_rollback`)。
* ``technique="overlap"``: t_release から τ の間、ブレーキを保ったままアクセルを踏み(駆動 a_drive)、τ 後にブレーキを離す
  (教習で教える「アクセルを踏んでからブレーキを離す」)。駆動 > 坂なら逆行 0。
``v_cruise`` を与えると、その速さに達したら駆動を止める(惰行)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_longitudinal](../../../../examples/poc_driving_longitudinal.py) — `py -3.11 examples/poc_driving_longitudinal.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`long`)

[long_params](long_params.md) · [road_profile](road_profile.md) · [road_eval](road_eval.md) · [long_simulate](long_simulate.md) · [long_energy_residual](long_energy_residual.md) · [stopping_distance_grade](stopping_distance_grade.md) · [stop_line_plan](stop_line_plan.md) · [plan_command](plan_command.md)

---
*Provenance: drivelong.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
