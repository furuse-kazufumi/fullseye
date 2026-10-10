---
op: boussinesq_surface_displacement
dim: drive
category: tactorque
in: matrix × table
out: table
examples: [poc_tactile_dipole_torque]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# boussinesq_surface_displacement — DRIVE `tactorque` op

- **データ種**: `matrix × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.boussinesq_surface_displacement(p, kern: 'dict') -> 'dict'` (実装を直接呼ぶなら `import tactorque; tactorque.boussinesq_surface_displacement(p, kern: 'dict') -> 'dict'`、台帳から引くなら `opsdrive.get("boussinesq_surface_displacement")`)

## 使い方

法線圧 p (n, n) [Pa] → 表面変位 ``ux``・``uy``(核に ``Kz`` があれば ``uz``、沈む向きが正)(n, n) [m]。零詰め 2n の線形畳み込み。
**Raises** ValueError: p が (n, n) でない、kern が :func:`boussinesq_kernel` の表でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tactile_dipole_torque](../../../../examples/poc_tactile_dipole_torque.py) — `py -3.11 examples/poc_tactile_dipole_torque.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tactorque`)

[punch_pressure](punch_pressure.md) · [punch_surface_uz](punch_surface_uz.md) · [hertz_pressure_shifted](hertz_pressure_shifted.md) · [ellipse_pressure_shifted](ellipse_pressure_shifted.md) · [pressure_first_moment](pressure_first_moment.md) · [boussinesq_kernel](boussinesq_kernel.md) · [surface_divergence_closed_form](surface_divergence_closed_form.md) · [tilt_shear_field](tilt_shear_field.md)

---
*Provenance: tactorque.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
