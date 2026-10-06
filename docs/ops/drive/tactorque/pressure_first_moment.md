---
op: pressure_first_moment
dim: drive
category: tactorque
in: matrix × matrix × matrix × scalar
out: table
examples: [poc_tactile_dipole_torque]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# pressure_first_moment — DRIVE `tactorque` op

- **データ種**: `matrix × matrix × matrix × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.pressure_first_moment(p, X, Y, pitch: 'float') -> 'dict'` (実装を直接呼ぶなら `import tactorque; tactorque.pressure_first_moment(p, X, Y, pitch: 'float') -> 'dict'`、台帳から引くなら `opsdrive.get("pressure_first_moment")`)

## 使い方

格子上の圧力 p (n, n) [Pa] の 0 次・1 次モーメント: ``P`` = Σ p h² [N]、``M1`` = Σ (x, y) p h² [N·m]、``tau`` = (−M1_y, M1_x)
(z はゲルから物体へ、物体がゲルを押す力 −ẑ p のモーメント)。**Raises** ValueError: 形が違う、pitch ≤ 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tactile_dipole_torque](../../../../examples/poc_tactile_dipole_torque.py) — `py -3.11 examples/poc_tactile_dipole_torque.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tactorque`)

[punch_pressure](punch_pressure.md) · [punch_surface_uz](punch_surface_uz.md) · [hertz_pressure_shifted](hertz_pressure_shifted.md) · [ellipse_pressure_shifted](ellipse_pressure_shifted.md) · [boussinesq_kernel](boussinesq_kernel.md) · [boussinesq_surface_displacement](boussinesq_surface_displacement.md) · [surface_divergence_closed_form](surface_divergence_closed_form.md) · [tilt_shear_field](tilt_shear_field.md)

---
*Provenance: tactorque.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
