---
op: puck_velocity_estimate
dim: drive
category: puck
in: signal × matrix × table
out: table
examples: [poc_air_hockey_intercept]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# puck_velocity_estimate — DRIVE `puck` op

- **データ種**: `signal × matrix × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.puck_velocity_estimate(t, xy, table: 'dict', *, model: 'str' = 'coulomb', t_ref=None, iters: 'int' = 3) -> 'dict'` (実装を直接呼ぶなら `import puck; puck.puck_velocity_estimate(t, xy, table: 'dict', *, model: 'str' = 'coulomb', t_ref=None, iters: 'int' = 3) -> 'dict'`、台帳から引くなら `opsdrive.get("puck_velocity_estimate")`)

## 使い方

N 点の位置から速度を最小二乗で: 向き û を固定した等減速模型 p(τ) = p_ref + v_ref τ − ½ μg τ² û(τ = t − t_ref)。

û は v_ref から取るので 3 回反復(初期値 = 端点の差)。"viscous" は基底 (1 − e^{−kτ})/k で線形、"none" は直線。
雑音の見積り: 残差から σ_pos、(AᵀA)⁻¹ から v_ref の分散(``sigma_v``、等方)。返り値
``{"p_ref","v_ref","speed","u","t_ref","sigma_pos","sigma_v","sigma_p","resid_rms","n","model"}``。N < 3 は ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_air_hockey_intercept](../../../../examples/poc_air_hockey_intercept.py) — `py -3.11 examples/poc_air_hockey_intercept.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`puck`)

[puck_table](puck_table.md) · [puck_wall_bounce](puck_wall_bounce.md) · [puck_slide_predict](puck_slide_predict.md) · [puck_state_at](puck_state_at.md) · [puck_crossing_point](puck_crossing_point.md) · [puck_mirror_path](puck_mirror_path.md) · [puck_stop_distance](puck_stop_distance.md) · [puck_camera](puck_camera.md)

---
*Provenance: puck.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
