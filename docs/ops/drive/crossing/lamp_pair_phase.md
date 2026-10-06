---
op: lamp_pair_phase
dim: drive
category: crossing
in: signal × signal
out: table
examples: [poc_driving_crossing]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# lamp_pair_phase — DRIVE `crossing` op

- **データ種**: `signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.lamp_pair_phase(a, b, fps: 'float', *, f_min: 'float' = 0.0, pad: 'int' = 8, tol: 'float' = 0.25) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivecrossing; drivecrossing.lamp_pair_phase(a, b, fps: 'float', *, f_min: 'float' = 0.0, pad: 'int' = 8, tol: 'float' = 0.25) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("lamp_pair_phase")`)

## 使い方

2 つの明るさの時系列(2 灯の画素)から、共通の点滅の周波数と位相差を相互スペクトルで推定する。

平均を引き Hann 窓、``pad`` 倍に 0 を詰めた rFFT。|A| + |B| の山(``f_min`` 以上、0 Hz の裾を除く)で
φ = arg(A_k B̄_k) を [0, π] に畳む。``delay`` = φ / (2π f)。``alternating`` = |φ − π| < tol(交互点滅)。
周波数は **見かけ** の値(fps/2 を超える点滅は折り返る)。どちらかが一定なら ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_crossing](../../../../examples/poc_driving_crossing.py) — `py -3.11 examples/poc_driving_crossing.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`crossing`)

[crossing_timing_check](crossing_timing_check.md) · [crossing_gate_state](crossing_gate_state.md) · [crossing_lamp_signal](crossing_lamp_signal.md) · [crossing_clear_time](crossing_clear_time.md) · [exit_room_check](exit_room_check.md) · [crossing_stop_check](crossing_stop_check.md) · [track_sight_distance](track_sight_distance.md) · [sight_triangle_distance](sight_triangle_distance.md)

---
*Provenance: drivecrossing.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
