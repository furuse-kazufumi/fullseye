---
op: tether_simulate
dim: drive
category: ball
in: 
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# tether_simulate — DRIVE `ball` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.tether_simulate(p0, v0, handle, L: 'float', t_end: 'float', dt: 'float' = 0.001, g: 'float' = 9.81, mass: 'float' = 0.01) -> 'dict'` (実装を直接呼ぶなら `import ballistics; ballistics.tether_simulate(p0, v0, handle, L: 'float', t_end: 'float', dt: 'float' = 0.001, g: 'float' = 9.81, mass: 'float' = 0.01) -> 'dict'`、台帳から引くなら `opsdrive.get("tether_simulate")`)

## 使い方

伸びないひも(長さ L)で手元 ``handle`` に繋がれた質点の運動(けん玉の玉)。

``handle`` は (3,) の固定点か、時刻 → (3,) の関数。各ステップで自由落下を進め、|p − h| > L になったら球面へ射影して
外向きの相対径方向速度を消す(片側拘束: ひもは引くだけで押さない)。その瞬間に失う運動エネルギー ½ m v_r² を "snap_loss" に
積む。張力の推定 = 射影で消した径方向の速度変化 × m / dt(≥ 0)。返り値 ``{"t", "p", "v", "tension", "taut" (bool),
"snap_times", "snap_loss", "energy"}``。定理の門: |p − h| ≤ L + 1e-9、張力 ≥ 0、手元が固定なら力学的エネルギーは
snap の瞬間以外で不変(RK 誤差の範囲)、小振幅の周期は 2π√(L/g)。

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
