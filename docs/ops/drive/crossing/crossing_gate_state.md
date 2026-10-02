---
op: crossing_gate_state
dim: drive
category: crossing
in: signal
out: table
examples: [poc_driving_crossing]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# crossing_gate_state — DRIVE `crossing` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.crossing_gate_state(t, *, t_warning: 'float', t_lower_start: 'float', lower_duration: 'float', t_clear: 'float', raise_duration: 'float') -> 'Dict[str, np.ndarray]'` (実装を直接呼ぶなら `import drivecrossing; drivecrossing.crossing_gate_state(t, *, t_warning: 'float', t_lower_start: 'float', lower_duration: 'float', t_clear: 'float', raise_duration: 'float') -> 'Dict[str, np.ndarray]'`、台帳から引くなら `opsdrive.get("crossing_gate_state")`)

## 使い方

踏切の状態機械(警報機 + 遮断機)を時刻 t(配列)で評価する。

状態: 0 idle(警報なし・かん上)、1 warning(警報中・かん上)、2 lowering(降下中)、3 closed(遮断中)、
4 raising(列車が過ぎて警報が止まり、かんが上昇中)。警報灯は 1〜3 で点く(解釈基準 5(5)「通過後に警報を停止」)。
かんの角 [rad]: 上 π/2 → 下 0。降下・上昇は余弦の滑らかな形(**仮定**: 実機の降下曲線は資料なし)。
``entry_forbidden`` = 1〜4(33 条 2 項。上昇中も含めるのは保守側の解釈)。

返り値: ``state``(int)、``boom_angle``、``lamps_on``(bool)、``entry_forbidden``(bool)、``t_closed``(降下の終わり)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_crossing](../../../../examples/poc_driving_crossing.py) — `py -3.11 examples/poc_driving_crossing.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`crossing`)

[crossing_timing_check](crossing_timing_check.md) · [crossing_lamp_signal](crossing_lamp_signal.md) · [lamp_pair_phase](lamp_pair_phase.md) · [crossing_clear_time](crossing_clear_time.md) · [exit_room_check](exit_room_check.md) · [crossing_stop_check](crossing_stop_check.md) · [track_sight_distance](track_sight_distance.md) · [sight_triangle_distance](sight_triangle_distance.md)

---
*Provenance: drivecrossing.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
