---
op: flight_fit
dim: drive
category: ball
in: signal × points × table
out: table
examples: [poc_ball_bounce, poc_table_tennis_bounce]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# flight_fit — DRIVE `ball` op

- **データ種**: `signal × points × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.flight_fit(t, p, omega, bp: 'dict', *, iters: 'int' = 12, dt: 'float' = 0.001) -> 'dict'` (実装を直接呼ぶなら `import ballistics; ballistics.flight_fit(t, p, omega, bp: 'dict', *, iters: 'int' = 12, dt: 'float' = 0.001) -> 'dict'`、台帳から引くなら `opsdrive.get("flight_fit")`)

## 使い方

観測 (t_i, p_i)(跳ねを含まない区間)に、抗力 + マグヌス(ω 既知)の運動方程式を **初期状態 (p₀, v₀) の 6 パラメータ** で
Gauss–Newton(有限差分のヤコビアン)で当てる。放物線の当てはめは抗力・マグヌスを g と v₀ に吸うので予測が曲がる —— こちらは
先駆者の「空力モデルつきの追跡」に当たる。返り値 ``{"p0", "v0", "rms", "iters", "t0"}``(p₀・v₀ は t = t[0] での状態)。
真値の軌跡を入れると 1e-9 で戻る(門)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ball_bounce](../../../../examples/poc_ball_bounce.py) — `py -3.11 examples/poc_ball_bounce.py`
- [poc_table_tennis_bounce](../../../../examples/poc_table_tennis_bounce.py) — `py -3.11 examples/poc_table_tennis_bounce.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`ball`)

[ball_params](ball_params.md) · [impact_params](impact_params.md) · [flight_vacuum](flight_vacuum.md) · [flight_ode](flight_ode.md) · [flight_simulate](flight_simulate.md) · [flight_state_at](flight_state_at.md) · [magnus_lift_coefficient](magnus_lift_coefficient.md) · [drag_coefficient_sphere](drag_coefficient_sphere.md)

---
*Provenance: ballistics.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
