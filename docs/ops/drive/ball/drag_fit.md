---
op: drag_fit
dim: drive
category: ball
in: signal × points × table
out: table
examples: [poc_video_physics_consistency]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# drag_fit — DRIVE `ball` op

- **データ種**: `signal × points × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.drag_fit(t, p, bp: 'dict', *, iters: 'int' = 20, dt: 'float' = 0.001) -> 'dict'` (実装を直接呼ぶなら `import ballistics; ballistics.drag_fit(t, p, bp: 'dict', *, iters: 'int' = 20, dt: 'float' = 0.001) -> 'dict'`、台帳から引くなら `opsdrive.get("drag_fit")`)

## 使い方

軌跡 (t_i, p_i) に「重力 + 抗力」の模型を **(p₀, v₀, C_d) の 7 パラメータ**(平面入力なら 5)で当てる(:func:`thrust_fit` の
推力なし版。:func:`flight_fit` は C_d を既知として 6 パラメータ、こちらは C_d も同定する)。返り値の鍵と入口の検査
(``dt`` ≤ 標本間隔、``iters`` ≥ 1、真空は拒否)は :func:`thrust_fit` と同じで、``thrust`` は零ベクトル。真値の軌跡なら C_d は 1e-4 で戻る(門)。

空の入力(``t`` が 0 要素)は ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_video_physics_consistency](../../../../examples/poc_video_physics_consistency.py) — `py -3.11 examples/poc_video_physics_consistency.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`ball`)

[ball_params](ball_params.md) · [impact_params](impact_params.md) · [flight_vacuum](flight_vacuum.md) · [flight_ode](flight_ode.md) · [flight_simulate](flight_simulate.md) · [flight_state_at](flight_state_at.md) · [magnus_lift_coefficient](magnus_lift_coefficient.md) · [drag_coefficient_sphere](drag_coefficient_sphere.md)

---
*Provenance: ballistics.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
