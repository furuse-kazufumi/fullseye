---
op: crosswalk_overtake_check
dim: drive
category: crossing
in: table
out: table
examples: [poc_driving_crossing]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# crosswalk_overtake_check — DRIVE `crossing` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.crosswalk_overtake_check(ego, others, *, crosswalk_start: 'float', crosswalk_end: 'float', zone: 'float' = 30.0, v_moving: 'float' = 0.5) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivecrossing; drivecrossing.crosswalk_overtake_check(ego, others, *, crosswalk_start: 'float', crosswalk_end: 'float', zone: 'float' = 30.0, v_moving: 'float' = 0.5) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("crosswalk_overtake_check")`)

## 使い方

横断歩道等とその手前 ``zone`` m の中で、前方を進行している車の前に出たか(38 条 3 項)。

ego, others[i] = {"t", "x"[, "v"], "kind"}(x = 前端)。他の車の前端を自分の前端が後ろから越えた瞬間(線形補間)を
「前方に出た」とし、そのときの自分の前端の位置が [crosswalk_start − zone, crosswalk_end] で、相手が進行中(速さ >
``v_moving``、**仮定**)かつ特定小型原動機付自転車等(``EXEMPT_KINDS``)でなければ違反。
返り値: ``ok``、``events`` = [{"other", "t", "x", "in_zone", "exempt", "moving", "violation"}]。

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
