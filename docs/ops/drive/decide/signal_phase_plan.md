---
op: signal_phase_plan
dim: drive
category: decide
in: 
out: table
examples: [poc_driving_decisions]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# signal_phase_plan — DRIVE `decide` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.signal_phase_plan(*, crossing_length: 'float', ped_green: 'float', walk_speed: 'float' = 1.0, ped_red_to_amber: 'float' = 2.0, amber: 'float' = 3.0, all_red: 'float' = 2.0, cross_green: 'float' = 20.0, cross_amber: 'Optional[float]' = None, cross_all_red: 'Optional[float]' = None, flash_fraction: 'float' = 1.0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivedecide; drivedecide.signal_phase_plan(*, crossing_length: 'float', ped_green: 'float', walk_speed: 'float' = 1.0, ped_red_to_amber: 'float' = 2.0, amber: 'float' = 3.0, all_red: 'float' = 2.0, cross_green: 'float' = 20.0, cross_amber: 'Optional[float]' = None, cross_all_red: 'Optional[float]' = None, flash_fraction: 'float' = 1.0) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("signal_phase_plan")`)

## 使い方

2 現示の信号の時間割(主道路 A と、それに **並行する歩行者信号**、交差道路 B)。時刻 0 = A の青の始まり。

    歩行者 A: 青 [0, g) → 青点滅 [g, g + F) → 赤 [g + F, 周期)、F = flash_fraction · crossing_length / walk_speed
    車両 A:   青 [0, t_y) → 黄 [t_y, t_y + Y) → 赤、t_y = g + F + Δ(Δ = ``ped_red_to_amber``)
    全赤 [t_y + Y, t_y + Y + AR) → 車両 B: 青 G_B → 黄 → 全赤 → 周期の終わり

返り値: ``intervals``(``{"veh_A", "ped_A", "veh_B"}`` → [(始, 終, 状態)])、``cycle``、``ped_flash_start`` = g、
``ped_flash_duration`` = F、``ped_red_onset``、``amber_onset`` = t_y、``red_onset``、``ped_red_to_amber`` = Δ。
状態は ``"green" / "flash" / "amber" / "red"``。
``flash_fraction`` = 1 は「点滅の始めに渡り始めた人が渡りきる」、0.5 は学会論文の L/(2V)(SOURCES "flash_rule")。数値の既定(黄 3 s・全赤 2 s・Δ 2 s・歩行速度)は ``SOURCES`` を見る。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_decisions](../../../../examples/poc_driving_decisions.py) — `py -3.11 examples/poc_driving_decisions.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`decide`)

[mirror_reflection_matrix](mirror_reflection_matrix.md) · [mirror_virtual_camera](mirror_virtual_camera.md) · [mirror_aim_normal](mirror_aim_normal.md) · [convex_mirror_fov](convex_mirror_fov.md) · [mirror_blind_zone](mirror_blind_zone.md) · [check_sequence_score](check_sequence_score.md) · [signal_state](signal_state.md) · [predict_amber_onset](predict_amber_onset.md)

---
*Provenance: drivedecide.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
