---
op: rigid_rotation_fit
dim: drive
category: tactorque
in: matrix × matrix
out: table
examples: [poc_knife_tactile_toughness, poc_tactile_dipole_torque]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# rigid_rotation_fit — DRIVE `tactorque` op

- **データ種**: `matrix × matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.rigid_rotation_fit(pts, u, window=None) -> 'dict'` (実装を直接呼ぶなら `import tactorque; tactorque.rigid_rotation_fit(pts, u, window=None) -> 'dict'`、台帳から引くなら `opsdrive.get("rigid_rotation_fit")`)

## 使い方

窓内のマーカー場に剛体変位 u ≈ t + ω ẑ×r を最小二乗で当てる: ``t`` = 平均変位、``omega`` = Σ (x′u′_y − y′u′_x)/Σ r′²
(′ は窓内平均を引いたもの)、``resid_rms`` = 残差 RMS、``n``。無滑りねじりでは円内が剛体回転(u_θ = βr)なので ω = β が真値
(平均 curl/2 は円の縁で当てはめが外に漏れて低くなる —— 実測 11 %)。``window`` = (cx, cy, R)。**Raises** ValueError: 点が 3 未満。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_knife_tactile_toughness](../../../../examples/poc_knife_tactile_toughness.py) — `py -3.11 examples/poc_knife_tactile_toughness.py`
- [poc_tactile_dipole_torque](../../../../examples/poc_tactile_dipole_torque.py) — `py -3.11 examples/poc_tactile_dipole_torque.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tactorque`)

[punch_pressure](punch_pressure.md) · [punch_surface_uz](punch_surface_uz.md) · [hertz_pressure_shifted](hertz_pressure_shifted.md) · [ellipse_pressure_shifted](ellipse_pressure_shifted.md) · [pressure_first_moment](pressure_first_moment.md) · [boussinesq_kernel](boussinesq_kernel.md) · [boussinesq_surface_displacement](boussinesq_surface_displacement.md) · [surface_divergence_closed_form](surface_divergence_closed_form.md)

---
*Provenance: tactorque.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
