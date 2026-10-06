---
op: boussinesq_kernel
dim: drive
category: tactorque
in: scalar × scalar × scalar × scalar
out: table
examples: [poc_tactile_dipole_torque]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# boussinesq_kernel — DRIVE `tactorque` op

- **データ種**: `scalar × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.boussinesq_kernel(n: 'int', pitch: 'float', G: 'float', nu: 'float', sub: 'int' = 4, with_uz: 'bool' = True) -> 'dict'` (実装を直接呼ぶなら `import tactorque; tactorque.boussinesq_kernel(n: 'int', pitch: 'float', G: 'float', nu: 'float', sub: 'int' = 4, with_uz: 'bool' = True) -> 'dict'`、台帳から引くなら `opsdrive.get("boussinesq_kernel")`)

## 使い方

法線圧(1 画素 = pitch² に一様 1 Pa)が作る表面変位の離散核(2n 格子、rfft2 済み): ``Kx`` = ū_x、``Ky`` = ū_y(接線、
−(1−2ν)/(4πG) · x/r² と y/r²、Johnson 1985 §3.2 の点荷重解)、``with_uz`` なら ``Kz`` = ū_z((1−ν)/(2πGr))。
画素平均(sub² の副標本)。中心画素: ∫□ x/r² dA = 0(奇関数)、∫□ 1/r dA = 4h ln(1+√2)(解析値)。
:func:`tacslip.cerruti_kernel`(接線 → 接線)と同じ作りの法線版。**Raises** ValueError: n < 8、pitch, G ≤ 0、ν が [0, 0.5] の外。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tactile_dipole_torque](../../../../examples/poc_tactile_dipole_torque.py) — `py -3.11 examples/poc_tactile_dipole_torque.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tactorque`)

[punch_pressure](punch_pressure.md) · [punch_surface_uz](punch_surface_uz.md) · [hertz_pressure_shifted](hertz_pressure_shifted.md) · [ellipse_pressure_shifted](ellipse_pressure_shifted.md) · [pressure_first_moment](pressure_first_moment.md) · [boussinesq_surface_displacement](boussinesq_surface_displacement.md) · [surface_divergence_closed_form](surface_divergence_closed_form.md) · [tilt_shear_field](tilt_shear_field.md)

---
*Provenance: tactorque.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
