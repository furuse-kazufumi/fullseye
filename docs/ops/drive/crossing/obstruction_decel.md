---
op: obstruction_decel
dim: drive
category: crossing
in: any
out: table
examples: [poc_driving_crossing]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# obstruction_decel — DRIVE `crossing` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.obstruction_decel(dist, speed, t_free, *, sudden: 'float' = 2.0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivecrossing; drivecrossing.obstruction_decel(dist, speed, t_free, *, sudden: 'float' = 2.0) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("obstruction_decel")`)

## 使い方

交差道路の車(領域まで dist、速さ speed)が、領域に t_free より前に入らないために要る一定の減速度(閉形式、配列可)。

T = t_free。speed·T ≤ dist なら 0(減速しなくても間に合う)。T ≤ 2 dist / speed なら 2(speed·T − dist)/T²、
それより後なら speed² / (2 dist)(領域の手前で止まる)。``obstructs`` = 減速度 > ``sudden``(**仮定** 2.0 m/s²、
2 条 22 号「速度又は方向を急に変更しなければならない」)。dist ≤ 0(もう領域にいる)で T > 0 は ∞。

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
