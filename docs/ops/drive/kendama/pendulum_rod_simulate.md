---
op: pendulum_rod_simulate
dim: drive
category: kendama
in: 
out: table
examples: [poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# pendulum_rod_simulate — DRIVE `kendama` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.pendulum_rod_simulate(L: 'float', theta0: 'float', t_end: 'float', dt: 'float' = 0.001, g: 'float' = 9.81, omega0: 'float' = 0.0) -> 'dict'` (実装を直接呼ぶなら `import kendama; kendama.pendulum_rod_simulate(L: 'float', theta0: 'float', t_end: 'float', dt: 'float' = 0.001, g: 'float' = 9.81, omega0: 'float' = 0.0) -> 'dict'`、台帳から引くなら `opsdrive.get("pendulum_rod_simulate")`)

## 使い方

棒の振り子(拘束が両側に効く: 弛まない)θ̈ = −(g/L) sin θ を RK4 で。返り値 ``{"t", "theta", "omega", "energy"}``
(energy = ½L²ω² − gL cos θ、単位質量)。ひもでは弛む θ₀ > π/2 の周期の定理を確かめる比較用。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_kendama](../../../../examples/poc_kendama.py) — `py -3.11 examples/poc_kendama.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`kendama`)

[kendama_params](kendama_params.md) · [elliptic_k_agm](elliptic_k_agm.md) · [pendulum_period_exact](pendulum_period_exact.md) · [pendulum_launch_speed](pendulum_launch_speed.md) · [tether_tension_fixed](tether_tension_fixed.md) · [tether_slack_angle](tether_slack_angle.md) · [swing_up_plan](swing_up_plan.md) · [swing_up_apex](swing_up_apex.md)

---
*Provenance: kendama.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
