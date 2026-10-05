---
op: legal_stop_intervals
dim: drive
category: crossing
in: any
out: any
examples: [poc_driving_crossing]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# legal_stop_intervals — DRIVE `crossing` op

- **データ種**: `any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.legal_stop_intervals(merged, road_start: 'float', road_end: 'float', car_length: 'float') -> 'np.ndarray'` (実装を直接呼ぶなら `import drivecrossing; drivecrossing.legal_stop_intervals(merged, road_start: 'float', road_end: 'float', car_length: 'float') -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("legal_stop_intervals")`)

## 使い方

駐停車禁止の区間(併せた (k, 2))を避けて、車体 [rear, rear + car_length] が丸ごと入る **後端の位置** の区間 (m, 2)。

区間の端ちょうど(距離がちょうど 5 m など)は禁止の側に含める(「以内」)ので、車体が端に触れるだけなら許す
(閉区間の補集合の閉包)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_crossing](../../../../examples/poc_driving_crossing.py) — `py -3.11 examples/poc_driving_crossing.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`crossing`)

[crossing_timing_check](crossing_timing_check.md) · [crossing_gate_state](crossing_gate_state.md) · [crossing_lamp_signal](crossing_lamp_signal.md) · [lamp_pair_phase](lamp_pair_phase.md) · [crossing_clear_time](crossing_clear_time.md) · [exit_room_check](exit_room_check.md) · [crossing_stop_check](crossing_stop_check.md) · [track_sight_distance](track_sight_distance.md)

---
*Provenance: drivecrossing.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
