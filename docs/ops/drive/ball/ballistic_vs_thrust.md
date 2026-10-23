---
op: ballistic_vs_thrust
dim: drive
category: ball
in: signal × points × table
out: table
examples: [poc_video_physics_consistency]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# ballistic_vs_thrust — DRIVE `ball` op

- **データ種**: `signal × points × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.ballistic_vs_thrust(t, p, bp: 'dict', *, iters: 'int' = 20, dt: 'float' = 0.001) -> 'dict'` (実装を直接呼ぶなら `import ballistics; ballistics.ballistic_vs_thrust(t, p, bp: 'dict', *, iters: 'int' = 20, dt: 'float' = 0.001) -> 'dict'`、台帳から引くなら `opsdrive.get("ballistic_vs_thrust")`)

## 使い方

同じ軌跡に「重力 + 抗力」(:func:`drag_fit`)と「重力 + 抗力 + 一定の比推力」(:func:`thrust_fit`)を当て、
AIC(:func:`aic_from_rss`)の差 ΔAIC = AIC_弾道 − AIC_推力 を返す。
返り値 ``{"ballistic", "thrust"}``(2 つの当てはめ)に ``"aic_ballistic", "aic_thrust", "delta_aic", "thrust_norm"`` を添える。
**判定は返さない**(:mod:`imgforensics` と同じ流儀): 読み方は **節約則**で、推力の模型はパラメータが 3 つ多いので雑音だけでも
RSS を僅かに下げる —— 罰則 2Δk を超えて勝たない限り、単純な方(弾道)を採る。雑音だけの ΔAIC は −2Δk を中心に χ²(Δk) の
幅で散り、推力側は弾道側の解から出発するので ΔAIC ≥ −2Δk が保たれる。「決定的」の慣用は 10(偽陽性 1 % を大きく下回る)だが、
閾値は同梱せず呼び手が決める。

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
