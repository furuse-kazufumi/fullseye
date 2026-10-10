---
op: crossing_stop_check
dim: drive
category: crossing
in: table
out: table
examples: [poc_driving_crossing, poc_driving_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# crossing_stop_check — DRIVE `crossing` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.crossing_stop_check(trajectory, *, stop_line: 'float', crossing_start: 'float', crossing_end: 'float', car_length: 'float', look_events: 'Sequence[Tuple[float, str]]' = (), forbidden_intervals: 'Sequence[Tuple[float, float]]' = (), queue_rear: 'Optional[float]' = None, signal_controlled: 'bool' = False, near: 'float' = 2.0, v_stop: 'float' = 0.05, gap: 'float' = 1.0, beyond: 'float' = 0.5, brake_max: 'Optional[float]' = None) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivecrossing; drivecrossing.crossing_stop_check(trajectory, *, stop_line: 'float', crossing_start: 'float', crossing_end: 'float', car_length: 'float', look_events: 'Sequence[Tuple[float, str]]' = (), forbidden_intervals: 'Sequence[Tuple[float, float]]' = (), queue_rear: 'Optional[float]' = None, signal_controlled: 'bool' = False, near: 'float' = 2.0, v_stop: 'float' = 0.05, gap: 'float' = 1.0, beyond: 'float' = 0.5, brake_max: 'Optional[float]' = None) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("crossing_stop_check")`)

## 使い方

踏切の通り方を採点する(33 条 1・2 項、50 条 2 項、教則 6-1-1(1)(3)(4)(5))。

``trajectory`` = {"t", "x"[, "v"]}(x = 車の前端)。判定(違反の名前):
* ``no_stop``(33 条 1 項): 前端が踏切に入る前に、停止線の直前([stop_line − near, stop_line])で止まっていない
  (``signal_controlled`` なら免除)。
* ``no_look``(33 条 1 項・教則 6-1-1(1)(2)): **最後の停止**の間(止まってから動き出すまで)に左右の両方を見ていない。
* ``entered_while_forbidden``(33 条 2 項): 前端が踏切の手前の端を越えた時刻が ``forbidden_intervals`` の中。
  ``brake_max`` [m/s²] を渡すと、その区間の始まりの時点で brake_max の減速では踏切の手前に止まれなかった進入
  (v² / (2 brake_max) > 踏切までの距離)は違反に数えず ``unavoidable`` に記録する(黄信号で止まれない距離と同じ
  考え方。法に明文の例外は無い = **解釈・仮定**)。None なら例外なし。
* ``no_exit_room``(50 条 2 項): 入った時刻に向こう側の余地が無い(``exit_room_check``)。
* ``stopped_inside``(教則 6-1-1(5)): 車体が踏切にかかっている間に止まった。
踏切に入らなかった軌跡は ``entered`` = False(違反は停止・確認以外を数えない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_crossing](../../../../examples/poc_driving_crossing.py) — `py -3.11 examples/poc_driving_crossing.py`
- [poc_driving_town](../../../../examples/poc_driving_town.py) — `py -3.11 examples/poc_driving_town.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`crossing`)

[crossing_timing_check](crossing_timing_check.md) · [crossing_gate_state](crossing_gate_state.md) · [crossing_lamp_signal](crossing_lamp_signal.md) · [lamp_pair_phase](lamp_pair_phase.md) · [crossing_clear_time](crossing_clear_time.md) · [exit_room_check](exit_room_check.md) · [track_sight_distance](track_sight_distance.md) · [sight_triangle_distance](sight_triangle_distance.md)

---
*Provenance: drivecrossing.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
