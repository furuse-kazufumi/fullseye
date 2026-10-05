---
op: predict_amber_onset
dim: drive
category: decide
in: table
out: table
examples: [poc_driving_decisions]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# predict_amber_onset — DRIVE `decide` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.predict_amber_onset(observations, *, flash_duration: 'Optional[float]' = None, crossing_length: 'Optional[float]' = None, walk_speed: 'float' = 1.0, ped_red_to_amber: 'float' = 2.0, t_now: 'Optional[float]' = None) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivedecide; drivedecide.predict_amber_onset(observations, *, flash_duration: 'Optional[float]' = None, crossing_length: 'Optional[float]' = None, walk_speed: 'float' = 1.0, ped_red_to_amber: 'float' = 2.0, t_now: 'Optional[float]' = None) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("predict_amber_onset")`)

## 使い方

並行する歩行者信号の観測(時刻順の ``(t, state)``、state ∈ green / flash / red)から車両の黄の始まりを推定する。

F = ``flash_duration``(無ければ ``crossing_length / walk_speed``)、Δ = ``ped_red_to_amber``。
観測の切り替わり(green→flash、flash→red)ごとに黄の時刻が入る区間を作り、その **積** をとる:

    green→flash(最後の green t_g、最初の flash t_f): 黄 ∈ [t_g + F + Δ, t_f + F + Δ]
    flash→red  (最後の flash t_f'、最初の red t_r):   黄 ∈ [t_f' + Δ, t_r + Δ]

返り値: ``amber_onset``(区間の中点)、``lo`` / ``hi``、``half_width``(誤差の上限)、``remaining``
= amber_onset − t_now(既定 = 最後の観測時刻)、``basis``(使った切り替わり)。切り替わりが 1 つも無ければ
ValueError(青が続いているだけでは「いつ点滅するか」は分からない)。区間が空(観測と F・Δ が矛盾)も ValueError。

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
