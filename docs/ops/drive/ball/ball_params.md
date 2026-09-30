---
op: ball_params
dim: drive
category: ball
in: 
out: table
examples: [poc_ball_bounce, poc_table_tennis_spin]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# ball_params — DRIVE `ball` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.ball_params(radius: 'float' = 0.02, mass: 'float' = 0.0027, cd=0.4, cl=None, rho: 'float' = 1.2, g: 'float' = 9.81, shell: 'bool' = True, spin_decay: 'float' = 0.0) -> 'dict'` (実装を直接呼ぶなら `import ballistics; ballistics.ball_params(radius: 'float' = 0.02, mass: 'float' = 0.0027, cd=0.4, cl=None, rho: 'float' = 1.2, g: 'float' = 9.81, shell: 'bool' = True, spin_decay: 'float' = 0.0) -> 'dict'`、台帳から引くなら `opsdrive.get("ball_params")`)

## 使い方

球の表。既定は卓球の球(ITTF: 直径 40 mm、2.7 g、薄殻)。

``cd`` = 抗力係数(数、または "sphere" で Re 依存の経験式 :func:`drag_coefficient_sphere`)、``cl`` = 揚力(マグヌス)係数
(None なら :func:`magnus_lift_coefficient` のスピン比モデル、数なら定数)、``rho`` = 空気密度 [kg/m³]、
``spin_decay`` = スピンの減衰率 [1/s] (dω/dt = −spin_decay·ω。0 なら減衰なし。実測から同定する量)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ball_bounce](../../../../examples/poc_ball_bounce.py) — `py -3.11 examples/poc_ball_bounce.py`
- [poc_table_tennis_spin](../../../../examples/poc_table_tennis_spin.py) — `py -3.11 examples/poc_table_tennis_spin.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`ball`)

[impact_params](impact_params.md) · [flight_vacuum](flight_vacuum.md) · [flight_ode](flight_ode.md) · [flight_simulate](flight_simulate.md) · [flight_state_at](flight_state_at.md) · [magnus_lift_coefficient](magnus_lift_coefficient.md) · [drag_coefficient_sphere](drag_coefficient_sphere.md) · [bounce](bounce.md)

---
*Provenance: ballistics.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
