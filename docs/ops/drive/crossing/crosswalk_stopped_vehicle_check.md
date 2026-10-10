---
op: crosswalk_stopped_vehicle_check
dim: drive
category: crossing
in: table
out: table
examples: [poc_driving_crossing]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# crosswalk_stopped_vehicle_check — DRIVE `crossing` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.crosswalk_stopped_vehicle_check(ego, stopped, *, crosswalk_start: 'float', crosswalk_end: 'float', near: 'float' = 3.0, approach: 'float' = 10.0, v_stop: 'float' = 0.05) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivecrossing; drivecrossing.crosswalk_stopped_vehicle_check(ego, stopped, *, crosswalk_start: 'float', crosswalk_end: 'float', near: 'float' = 3.0, approach: 'float' = 10.0, v_stop: 'float' = 0.05) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("crosswalk_stopped_vehicle_check")`)

## 使い方

横断歩道等(又はその手前の直前)で止まっている車の側方を通って前に出る前に一時停止したか(38 条 2 項)。

stopped[i] = {"x": 止まっている車の前端, "t0", "t1": 止まっている時間}。前端が [crosswalk_start − near, crosswalk_end]
にある車だけが対象(near = 「直前」、**仮定** 3 m)。自分の前端がその前端を越える時刻 t_e が [t0, t1] の中なら、
t_e より前に、前端が [x − approach, x] にある間に速さ ≤ v_stop になっていなければ違反(approach は **仮定** 10 m)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_crossing](../../../../examples/poc_driving_crossing.py) — `py -3.11 examples/poc_driving_crossing.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`crossing`)

[crossing_timing_check](crossing_timing_check.md) · [crossing_gate_state](crossing_gate_state.md) · [crossing_lamp_signal](crossing_lamp_signal.md) · [lamp_pair_phase](lamp_pair_phase.md) · [crossing_clear_time](crossing_clear_time.md) · [exit_room_check](exit_room_check.md) · [crossing_stop_check](crossing_stop_check.md) · [track_sight_distance](track_sight_distance.md)

---
*Provenance: drivecrossing.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
