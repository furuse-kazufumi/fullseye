---
op: track_sight_distance
dim: drive
category: crossing
in: any
out: any
examples: [poc_driving_crossing]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# track_sight_distance — DRIVE `crossing` op

- **データ種**: `any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.track_sight_distance(v_train, clear_time, *, margin: 'float' = 0.0)` (実装を直接呼ぶなら `import drivecrossing; drivecrossing.track_sight_distance(v_train, clear_time, *, margin: 'float' = 0.0)`、台帳から引くなら `opsdrive.get("track_sight_distance")`)

## 使い方

渡り切る前に列車が着かないために、線路の上で見えていなければならない距離 = v_train · (clear_time + margin)。

見える距離がこれ以上なら、見えていない列車は渡り切る前に踏切に着かない(到達時刻 = 距離 / 速さ > 渡り切る時間)。配列可。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_crossing](../../../../examples/poc_driving_crossing.py) — `py -3.11 examples/poc_driving_crossing.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`crossing`)

[crossing_timing_check](crossing_timing_check.md) · [crossing_gate_state](crossing_gate_state.md) · [crossing_lamp_signal](crossing_lamp_signal.md) · [lamp_pair_phase](lamp_pair_phase.md) · [crossing_clear_time](crossing_clear_time.md) · [exit_room_check](exit_room_check.md) · [crossing_stop_check](crossing_stop_check.md) · [sight_triangle_distance](sight_triangle_distance.md)

---
*Provenance: drivecrossing.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
