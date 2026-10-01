---
op: priority_rule
dim: drive
category: crossing
in: table
out: table
examples: [poc_driving_crossing]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# priority_rule — DRIVE `crossing` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.priority_rule(own, cross, *, signalised: 'bool' = False, wide_ratio: 'float' = 1.5) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivecrossing; drivecrossing.priority_rule(own, cross, *, signalised: 'bool' = False, wide_ratio: 'float' = 1.5) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("priority_rule")`)

## 使い方

交通整理の行われていない交差点で、自分(own)が交差道路(cross)の車に譲るか(36 条 1〜3 項)。

own, cross = {"width": 幅員 [m], "priority_sign": 優先道路の標識, "centre_line": 交差点の中まで中央線・車両通行帯}。
優先道路 = 標識 or 中央線(36 条 2 項のかっこ書き)。明らかに広い = 幅の比 ≥ ``wide_ratio``(**仮定**)。

返り値: ``yield_to`` ∈ {"cross"(交差道路の車すべてに譲る、36 条 2 項)、"left"(左方から来る車に譲る、36 条 1 項)、
"none"(相手が譲る)}、``must_slow``(36 条 3 項の徐行)、``own_priority`` / ``cross_priority`` / ``cross_clearly_wider`` /
``own_clearly_wider``、``article``。交通整理あり(信号)は ValueError(信号に従う)。

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
