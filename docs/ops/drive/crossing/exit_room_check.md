---
op: exit_room_check
dim: drive
category: crossing
in: any
out: table
examples: [poc_driving_crossing]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# exit_room_check — DRIVE `crossing` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.exit_room_check(queue_rear, far_edge: 'float', car_length: 'float', *, gap: 'float' = 1.0, beyond: 'float' = 0.5)` (実装を直接呼ぶなら `import drivecrossing; drivecrossing.exit_room_check(queue_rear, far_edge: 'float', car_length: 'float', *, gap: 'float' = 1.0, beyond: 'float' = 0.5)`、台帳から引くなら `opsdrive.get("exit_room_check")`)

## 使い方

踏切(横断歩道・交差点も同じ)の向こう側に、自分が止まれる余地があるか(50 条 2 項)。配列可。

前の車の後端 ``queue_rear`` の後ろ ``gap`` で止まると、自分の後端 = queue_rear − gap − car_length。これが
far_edge + beyond 以上なら入ってよい。返り値: ``room`` = queue_rear − far_edge、``need`` = car_length + gap + beyond、
``ok``、``rear_if_stopped``。前の車が無い場合は queue_rear = +∞。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_crossing](../../../../examples/poc_driving_crossing.py) — `py -3.11 examples/poc_driving_crossing.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`crossing`)

[crossing_timing_check](crossing_timing_check.md) · [crossing_gate_state](crossing_gate_state.md) · [crossing_lamp_signal](crossing_lamp_signal.md) · [lamp_pair_phase](lamp_pair_phase.md) · [crossing_clear_time](crossing_clear_time.md) · [crossing_stop_check](crossing_stop_check.md) · [track_sight_distance](track_sight_distance.md) · [sight_triangle_distance](sight_triangle_distance.md)

---
*Provenance: drivecrossing.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
