---
op: torsion_stick_field
dim: drive
category: tactorque
in: matrix × matrix × scalar × scalar × table × scalar
out: table
examples: [poc_tactile_dipole_torque]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# torsion_stick_field — DRIVE `tactorque` op

- **データ種**: `matrix × matrix × scalar × scalar × table × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.torsion_stick_field(X, Y, a: 'float', Mz: 'float', kern: 'dict', G: 'float') -> 'dict'` (実装を直接呼ぶなら `import tactorque; tactorque.torsion_stick_field(X, Y, a: 'float', Mz: 'float', kern: 'dict', G: 'float') -> 'dict'`、台帳から引くなら `opsdrive.get("torsion_stick_field")`)

## 使い方

無滑りねじり(Reissner–Sagoci、Johnson 1985 §3.9 相当、式番号は未確認 → 畳み込みで数値検証)の表面変位場: トラクション
q_θ = 3M_z r/(4πa³√(a²−r²)) を :func:`tacslip.cerruti_kernel` の核で畳んだ ``ux``・``uy`` [m] と、閉形式 ``beta`` = 3M_z/(16Ga³)、
円内の剛体回転 ``ux_cf`` = −βy・``uy_cf`` = βx(r < a)、トラクション ``qx``・``qy``。畳み込みが円内で一様な u_θ/r = β を返すことで β の式を
独立実装で検証する(−0.5 %、一様性 0.14 %、実測)。Lubkin 1951 の部分滑り(固着半径 c)は未実装(docstring 参照)。
**Raises** ValueError: G ≤ 0、a ≤ 0、X と Y の形が違う、核の格子が合わない。

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
