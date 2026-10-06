---
op: ellipse_pressure_shifted
dim: drive
category: tactorque
in: matrix × matrix × scalar × scalar × scalar
out: matrix
examples: [poc_tactile_dipole_torque]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# ellipse_pressure_shifted — DRIVE `tactorque` op

- **データ種**: `matrix × matrix × scalar × scalar × scalar` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.ellipse_pressure_shifted(X, Y, a: 'float', b: 'float', P: 'float', d=(0.0, 0.0)) -> 'np.ndarray'` (実装を直接呼ぶなら `import tactorque; tactorque.ellipse_pressure_shifted(X, Y, a: 'float', b: 'float', P: 'float', d=(0.0, 0.0)) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("ellipse_pressure_shifted")`)

## 使い方

半軸 a(x)・b(y)[m] の楕円 Hertz 圧 p0 √(1 − x′²/a² − y′²/b²) [Pa]、P = 2πab p0/3(Johnson 1985 式 4.24)、中心を d にずらす。
b ≫ a で円筒(稜・くさび状)の押し込みに近い形 —— 形状不変の門の 3 つ目。**Raises** ValueError: a, b, P ≤ 0、X と Y の形が違う。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tactile_dipole_torque](../../../../examples/poc_tactile_dipole_torque.py) — `py -3.11 examples/poc_tactile_dipole_torque.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[world_camera](../world/world_camera.md) · [lidar_scan](../lidar/lidar_scan.md) · [relative_motion](../ttc/relative_motion.md) · [foe_from_motion](../ttc/foe_from_motion.md) · [flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [world_materials](../terrain/world_materials.md) · [mesh_signed_volume](../terrain/mesh_signed_volume.md)

## 同カテゴリ(`tactorque`)

[punch_pressure](punch_pressure.md) · [punch_surface_uz](punch_surface_uz.md) · [hertz_pressure_shifted](hertz_pressure_shifted.md) · [pressure_first_moment](pressure_first_moment.md) · [boussinesq_kernel](boussinesq_kernel.md) · [boussinesq_surface_displacement](boussinesq_surface_displacement.md) · [surface_divergence_closed_form](surface_divergence_closed_form.md) · [tilt_shear_field](tilt_shear_field.md)

---
*Provenance: tactorque.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
