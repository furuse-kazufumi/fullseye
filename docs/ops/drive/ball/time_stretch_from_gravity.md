---
op: time_stretch_from_gravity
dim: drive
category: ball
in: 
out: table
gpu: なし
examples: [poc_video_physics_consistency]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# time_stretch_from_gravity — DRIVE `ball` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.time_stretch_from_gravity(g_fit: 'float', g_ref: 'float' = 9.81) -> 'dict'` (実装を直接呼ぶなら `import ballistics; ballistics.time_stretch_from_gravity(g_fit: 'float', g_ref: 'float' = 9.81) -> 'dict'`、台帳から引くなら `opsdrive.get("time_stretch_from_gravity")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

当てはめた重力加速度から、映像の時間の引き延ばし倍率を閉形式で逆算する。時刻を k 倍に引き延ばした(スローモーションや
フレームレートの付け替えをした)映像では、軌跡は同じ形のまま g が g/k² に見えるので、k = √(g_ref / g_fit)。
返り値 ``{"k", "g_fit", "g_ref", "log_k"}``(``log_k`` = ln k は改変なしで 0、符号が速い/遅いを表す: :func:`imgforensics.evidence_quantile`
に渡すなら |log_k| を「大きいほど強い」証拠として使う)。
g_fit ≤ 0 や非有限、g_ref ≤ 0 は ValueError(重力が上を向く・無い軌跡に倍率は定義できない)。

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
