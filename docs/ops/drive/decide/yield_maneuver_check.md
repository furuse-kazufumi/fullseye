---
op: yield_maneuver_check
dim: drive
category: decide
in: table
out: table
examples: [poc_driving_decisions]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# yield_maneuver_check — DRIVE `decide` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.yield_maneuver_check(trajectory, *, t_approach: 'float', t_passed: 'float', intersections=(), near_margin: 'float' = 30.0, left_tol: 'float' = 1.0, stop_speed: 'float' = 0.1, car_length: 'float' = 4.5) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivedecide; drivedecide.yield_maneuver_check(trajectory, *, t_approach: 'float', t_passed: 'float', intersections=(), near_margin: 'float' = 30.0, left_tol: 'float' = 1.0, stop_speed: 'float' = 0.1, car_length: 'float' = 4.5) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("yield_maneuver_check")`)

## 使い方

緊急自動車が近づいたときの自車の動きを道路交通法 40 条で採点する。

40 条 1 項: 交差点又はその附近 → 交差点を避け、道路の左側に寄って **一時停止**。
40 条 2 項: それ以外 → 道路の左側に寄って進路を譲る(停止までは求めない)。
(一方通行で左に寄ると妨げる場合の右寄せは扱わない。)

``trajectory``: ``{"t", "x", "y", "v"}``。x = 道に沿った前端の位置、y = 車の左側面と道路の左端の距離(≥ 0)、
v = 速さ。``intersections`` = [(x_in, x_out), ...] (交差点の範囲)。車は [x − car_length, x] を占める。
``t_approach`` = 近づきに気づくべき時刻、``t_passed`` = 緊急自動車が通り過ぎた時刻。

判定(閾値はすべて **仮定**、法は数値を定めていない):
* 「附近」= t_approach の自車の前端が [x_in − near_margin, x_out + near_margin] に入る交差点がある。
* 「左に寄る」= 期間中に y ≤ ``left_tol``。「一時停止」= 期間中に v ≤ ``stop_speed`` の刻みがある。
* 「交差点を避け」= 期間中に止まっている刻み(v ≤ stop_speed)で車体が交差点の範囲に重ならない。

返り値: ``case``(``"40-1"`` / ``"40-2"``)、``violations``(各 ``{"rule", "detail", "article"}``)、``ok``、
``min_y``、``stopped``、``stopped_in_intersection``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_decisions](../../../../examples/poc_driving_decisions.py) — `py -3.11 examples/poc_driving_decisions.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`decide`)

[mirror_reflection_matrix](mirror_reflection_matrix.md) · [mirror_virtual_camera](mirror_virtual_camera.md) · [mirror_aim_normal](mirror_aim_normal.md) · [convex_mirror_fov](convex_mirror_fov.md) · [mirror_blind_zone](mirror_blind_zone.md) · [check_sequence_score](check_sequence_score.md) · [signal_phase_plan](signal_phase_plan.md) · [signal_state](signal_state.md)

---
*Provenance: drivedecide.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
