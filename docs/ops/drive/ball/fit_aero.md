---
op: fit_aero
dim: drive
category: ball
in: signal × points × table
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# fit_aero — DRIVE `ball` op

- **データ種**: `signal × points × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.fit_aero(t, p, omega, bp: 'dict', *, iters: 'int' = 15, dt: 'float' = 0.001) -> 'dict'` (実装を直接呼ぶなら `import ballistics; ballistics.fit_aero(t, p, omega, bp: 'dict', *, iters: 'int' = 15, dt: 'float' = 0.001) -> 'dict'`、台帳から引くなら `opsdrive.get("fit_aero")`)

## 使い方

軌跡から **空力係数も** 同定する: (p₀, v₀, C_d, C_L) の 8 パラメータを Gauss–Newton(ω は既知、C_L は定数として当てる)。
抗力は速さの 2 乗、マグヌスは ω × v なので、直線的でない軌跡(スピンあり・十分な長さ)でないと C_L は決まりにくい
(``rms`` と一緒に ``cond`` = ヤコビアンの条件数を返すので、それで判る)。返り値 ``{"p0", "v0", "cd", "cl", "rms", "cond", "iters"}``。
真値の軌跡(C_L 定数で作った)なら 1e-6 で戻る(門)。

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
