---
op: no_stopping_zones
dim: drive
category: crossing
in: table
out: table
examples: [poc_driving_crossing]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# no_stopping_zones — DRIVE `crossing` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.no_stopping_zones(features: 'Iterable[dict]', *, in_service: 'bool' = True) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivecrossing; drivecrossing.no_stopping_zones(features: 'Iterable[dict]', *, in_service: 'bool' = True) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("no_stopping_zones")`)

## 使い方

道に沿った施設から、44 条 1 項の駐停車禁止の区間を作る。

features[i] = {"kind", "start", "end"}(バス停は "at" = 標示板の位置でもよい)。kind ∈ ``NO_STOP_DISTANCE``。
区間 = [start − d, end + d] (d = その号の距離)。バス停は運行時間中(``in_service``)だけ。
返り値: ``zones`` = [(a, b, kind, 号)] (元の順)、``merged`` = 重なりを併せた (k, 2) の配列(昇順・互いに素)。

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
