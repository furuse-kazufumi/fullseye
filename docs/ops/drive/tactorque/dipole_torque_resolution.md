---
op: dipole_torque_resolution
dim: drive
category: tactorque
in: matrix × matrix × scalar × scalar × scalar × scalar × scalar
out: table
examples: [poc_tactile_dipole_torque]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# dipole_torque_resolution — DRIVE `tactorque` op

- **データ種**: `matrix × matrix × scalar × scalar × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.dipole_torque_resolution(pts, u, sigma_px: 'float', pitch: 'float', coef: 'float', area: 'float', radius: 'float', trials: 'int' = 100, window=None, seed: 'int' = 0, form: 'str' = 'divergence') -> 'dict'` (実装を直接呼ぶなら `import tactorque; tactorque.dipole_torque_resolution(pts, u, sigma_px: 'float', pitch: 'float', coef: 'float', area: 'float', radius: 'float', trials: 'int' = 100, window=None, seed: 'int' = 0, form: 'str' = 'divergence') -> 'dict'`、台帳から引くなら `opsdrive.get("dipole_torque_resolution")`)

## 使い方

マーカー重心の雑音 σ [px] を変位に足して双極子を ``trials`` 回取り直し、トルク分解能 σ_M = σ_D/|coef| [N·m] を測る。
返り ``sigma_D`` (2,)、``sigma_M`` (2,)、``D0``(雑音なし)、``snr`` = |D0|/σ_D、``trials``。σ_M ∝ σ(実測)。
**Raises** ValueError: σ < 0、trials < 2、coef = 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tactile_dipole_torque](../../../../examples/poc_tactile_dipole_torque.py) — `py -3.11 examples/poc_tactile_dipole_torque.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tactorque`)

[punch_pressure](punch_pressure.md) · [punch_surface_uz](punch_surface_uz.md) · [hertz_pressure_shifted](hertz_pressure_shifted.md) · [ellipse_pressure_shifted](ellipse_pressure_shifted.md) · [pressure_first_moment](pressure_first_moment.md) · [boussinesq_kernel](boussinesq_kernel.md) · [boussinesq_surface_displacement](boussinesq_surface_displacement.md) · [surface_divergence_closed_form](surface_divergence_closed_form.md)

---
*Provenance: tactorque.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
