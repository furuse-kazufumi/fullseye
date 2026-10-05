---
op: cup_catch_check
dim: drive
category: ball
in: 
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# cup_catch_check — DRIVE `ball` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.cup_catch_check(p_ball, v_ball, cup_center, cup_axis, cup_radius: 'float', ball_radius: 'float', v_rel_max: 'float' = 1.0) -> 'dict'` (実装を直接呼ぶなら `import ballistics; ballistics.cup_catch_check(p_ball, v_ball, cup_center, cup_axis, cup_radius: 'float', ball_radius: 'float', v_rel_max: 'float' = 1.0) -> 'dict'`、台帳から引くなら `opsdrive.get("cup_catch_check")`)

## 使い方

玉が皿(中心・軸・半径)に入る幾何の判定: 玉の中心が皿の軸から (cup_radius − ball_radius) 以内、皿の面から玉の半径の 1.5 倍以内の
高さ(0 ≤ height ≤ 1.5 r)、速さ ≤ v_rel_max。``{"caught", "lateral", "height", "speed"}``。皿が玉より小さければ ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`ball`)

[ball_params](ball_params.md) · [impact_params](impact_params.md) · [flight_vacuum](flight_vacuum.md) · [flight_ode](flight_ode.md) · [flight_simulate](flight_simulate.md) · [flight_state_at](flight_state_at.md) · [magnus_lift_coefficient](magnus_lift_coefficient.md) · [drag_coefficient_sphere](drag_coefficient_sphere.md)

---
*Provenance: ballistics.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
