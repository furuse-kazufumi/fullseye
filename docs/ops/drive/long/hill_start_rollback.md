---
op: hill_start_rollback
dim: drive
category: long
in: scalar × scalar × scalar
out: table
examples: [poc_driving_longitudinal]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# hill_start_rollback — DRIVE `long` op

- **データ種**: `scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.hill_start_rollback(theta: 'float', tau: 'float', a_drive: 'float', c_rr: 'float' = 0.012, a_creep: 'float' = 0.0, g: 'float' = 9.80665) -> 'Dict[str, float]'` (実装を直接呼ぶなら `import drivelong; drivelong.hill_start_rollback(theta: 'float', tau: 'float', a_drive: 'float', c_rr: 'float' = 0.012, a_creep: 'float' = 0.0, g: 'float' = 9.80665) -> 'Dict[str, float]'`、台帳から引くなら `opsdrive.get("hill_start_rollback")`)

## 使い方

上り坂(θ > 0)で止まった車がブレーキを離し、τ 秒後に駆動 a_drive が入るときのずり下がり(空気抵抗なしの閉形式)。

τ の間の下向きの加速度 a₁ = g sin θ − c_rr g cos θ − a_creep(≤ 0 ならずり下がらない)。距離 ½ a₁ τ²、速さ a₁ τ。
駆動が入ると後ろ向きの動きを a₂ = a_drive − g sin θ + c_rr g cos θ で止める(転がり抵抗も動きに逆らう)→ (a₁ τ)²/(2 a₂)。

Returns
-------
dict : ``rollback``(合計 [m])、``during_gap``(½ a₁ τ²)、``recovery``((a₁τ)²/(2a₂))、``a1``、``a2``、``v_back``。
a₂ ≤ 0(駆動が坂に負ける)なら rollback = inf。

**Raises** ``ValueError``: τ < 0、a_drive ≤ 0、非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_longitudinal](../../../../examples/poc_driving_longitudinal.py) — `py -3.11 examples/poc_driving_longitudinal.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`long`)

[long_params](long_params.md) · [road_profile](road_profile.md) · [road_eval](road_eval.md) · [long_simulate](long_simulate.md) · [long_energy_residual](long_energy_residual.md) · [stopping_distance_grade](stopping_distance_grade.md) · [stop_line_plan](stop_line_plan.md) · [plan_command](plan_command.md)

---
*Provenance: drivelong.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
