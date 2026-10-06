---
op: conflict_zone_intervals
dim: drive
category: crossing
in: any
out: table
examples: [poc_driving_crossing]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# conflict_zone_intervals — DRIVE `crossing` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.conflict_zone_intervals(dist_to_zone, zone_length: 'float', car_length: 'float', *, v0: 'float', accel: 'float' = 0.0, v_max: 'Optional[float]' = None) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivecrossing; drivecrossing.conflict_zone_intervals(dist_to_zone, zone_length: 'float', car_length: 'float', *, v0: 'float', accel: 'float' = 0.0, v_max: 'Optional[float]' = None) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("conflict_zone_intervals")`)

## 使い方

衝突の領域(交差点の中で 2 つの進路が重なる所)を車が占める時刻 [t_in, t_out] (閉形式、配列可)。

前端が dist_to_zone 進むと入り、前端が dist_to_zone + zone_length + car_length 進むと後端が出る。初速 v0 から
``accel`` で ``v_max`` まで加速(accel = 0 なら一定の速さ)。既に領域に入っている(dist_to_zone < 0)場合は t_in = 0。

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
