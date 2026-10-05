---
op: crossing_lamp_signal
dim: drive
category: crossing
in: 
out: any
examples: [poc_driving_crossing]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# crossing_lamp_signal — DRIVE `crossing` op

- **データ種**: `なし` → `any`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.crossing_lamp_signal(t, *, t_on: 'float', t_off: 'float', flash_per_min: 'float' = 50.0, duty: 'float' = 0.5, exposure: 'float' = 0.0) -> 'np.ndarray'` (実装を直接呼ぶなら `import drivecrossing; drivecrossing.crossing_lamp_signal(t, *, t_on: 'float', t_off: 'float', flash_per_min: 'float' = 50.0, duty: 'float' = 0.5, exposure: 'float' = 0.0) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("crossing_lamp_signal")`)

## 使い方

2 灯の赤色せん光灯の明るさ(0..1)を時刻 t(配列)で返す: 形 (n, 2)、列 0 = 左、列 1 = 右。

1 灯の周期 P = 60 / flash_per_min、点灯 duty·P。右の灯は P/2 遅れ(解釈基準「交互に点滅」)。点くのは
[t_on, t_off)。``exposure`` > 0 ならカメラの露光 [t, t + exposure] の平均(点灯時間の原始関数で閉形式)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_crossing](../../../../examples/poc_driving_crossing.py) — `py -3.11 examples/poc_driving_crossing.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`crossing`)

[crossing_timing_check](crossing_timing_check.md) · [crossing_gate_state](crossing_gate_state.md) · [lamp_pair_phase](lamp_pair_phase.md) · [crossing_clear_time](crossing_clear_time.md) · [exit_room_check](exit_room_check.md) · [crossing_stop_check](crossing_stop_check.md) · [track_sight_distance](track_sight_distance.md) · [sight_triangle_distance](sight_triangle_distance.md)

---
*Provenance: drivecrossing.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
