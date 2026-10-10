---
op: crossing_clear_time
dim: drive
category: crossing
in: 
out: table
examples: [poc_driving_crossing]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# crossing_clear_time — DRIVE `crossing` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.crossing_clear_time(stop_to_edge: 'float', crossing_length: 'float', car_length: 'float', *, beyond: 'float' = 0.5, accel: 'float', v_max: 'Optional[float]' = None, v0: 'float' = 0.0) -> 'Dict[str, float]'` (実装を直接呼ぶなら `import drivecrossing; drivecrossing.crossing_clear_time(stop_to_edge: 'float', crossing_length: 'float', car_length: 'float', *, beyond: 'float' = 0.5, accel: 'float', v_max: 'Optional[float]' = None, v0: 'float' = 0.0) -> 'Dict[str, float]'`、台帳から引くなら `opsdrive.get("crossing_clear_time")`)

## 使い方

停止線から発進して、車の後端が踏切の向こうの端 + ``beyond`` を越えるまでの時間(閉形式)。

距離 D = stop_to_edge + crossing_length + car_length + beyond(車の位置は前端)。一定の加速度 ``accel`` で
``v_max`` まで加速して巡航(教則 6-1-1(5)「変速しないで一気に」= 途中で止まらない)。
返り値: ``distance``、``time``、``t_on_track``(前端が線路の手前の端に着く時刻)、``v_exit``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_crossing](../../../../examples/poc_driving_crossing.py) — `py -3.11 examples/poc_driving_crossing.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`crossing`)

[crossing_timing_check](crossing_timing_check.md) · [crossing_gate_state](crossing_gate_state.md) · [crossing_lamp_signal](crossing_lamp_signal.md) · [lamp_pair_phase](lamp_pair_phase.md) · [exit_room_check](exit_room_check.md) · [crossing_stop_check](crossing_stop_check.md) · [track_sight_distance](track_sight_distance.md) · [sight_triangle_distance](sight_triangle_distance.md)

---
*Provenance: drivecrossing.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
