---
op: thrust_ode
dim: drive
category: ball
in: table
out: table
examples: [poc_video_physics_consistency]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# thrust_ode — DRIVE `ball` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.thrust_ode(p0, v0, thrust, bp: 'dict', t_end: 'float', dt: 'float' = 0.001) -> 'dict'` (実装を直接呼ぶなら `import ballistics; ballistics.thrust_ode(p0, v0, thrust, bp: 'dict', t_end: 'float', dt: 'float' = 0.001) -> 'dict'`、台帳から引くなら `opsdrive.get("thrust_ode")`)

## 使い方

重力 + 抗力 + **一定の比推力**(質量あたりの推力 [m/s²]、世界座標で向きも大きさも一定)の RK4。スピンは持たない(ω = 0)。
返り値 ``{"t" (N,), "p" (N, 3), "v" (N, 3)}``(t = 0, dt, …, ≤ t_end)。``thrust`` が零ベクトルなら :func:`flight_ode`(ω = 0)と
1e-12 で一致し、真空(rho = 0)なら閉形式 p₀ + v₀ t + ½ (a_T − g ẑ) t² と 1e-9 で一致する(門)。
「ほぼロケット」の映像を扱う最小の模型で、推力が機体に固定されて向きを変える場合は近似になる(短い区間ほど良い)。

空の入力(``thrust`` が 0 要素)は ValueError。

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
