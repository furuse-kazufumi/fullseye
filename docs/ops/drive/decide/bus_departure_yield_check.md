---
op: bus_departure_yield_check
dim: drive
category: decide
in: table
out: table
examples: [poc_driving_decisions]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# bus_departure_yield_check — DRIVE `decide` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.bus_departure_yield_check(trajectory, *, t_signal: 'float', bus_rear_x: 'float', merge_time: 'float' = 4.0, reaction: 'float' = 1.0, sudden_decel: 'float' = 3.0, standoff: 'float' = 2.0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivedecide; drivedecide.bus_departure_yield_check(trajectory, *, t_signal: 'float', bus_rear_x: 'float', merge_time: 'float' = 4.0, reaction: 'float' = 1.0, sudden_decel: 'float' = 3.0, standoff: 'float' = 2.0) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("bus_departure_yield_check")`)

## 使い方

停留所から発進の合図をしたバスの進路変更を、後ろの自車が妨げたかを採点する(道路交通法 31 条の 2)。

``trajectory``: ``{"t", "x", "v"}``(自車の前端の位置、バスが入ってくる車線)。バスの後端は ``bus_rear_x``
(合図から ``merge_time`` 秒は止まっている / ゆっくり出る間とみなす)。

* 譲る義務: 合図の時刻 t_s の自車の (x_s, v_s) から、反応 ρ の後に一定減速でバスの後端の ``standoff`` 手前に
  止まる減速 a_req = v²/(2(D − vρ))、D = bus_rear_x − standoff − x_s(D ≤ vρ なら ∞)。
  a_req ≤ ``sudden_decel`` なら **急に速度を変えずに譲れる** → 譲る義務あり(``must_yield``)。
* 妨げた: [t_s, t_s + merge_time] のどこかで自車の前端がバスの後端を越えた(横に並んだ / 追い抜いた)。
* 違反 = 譲る義務あり かつ 妨げた。

「急に」の閾値 3.0 m/s²・反応 1.0 s・余裕 2 m・合流の時間 4 s は **仮定**(法に数値なし)。
返り値: ``a_required``、``must_yield``、``obstructed``、``violation``、``article``、``detail``。

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
