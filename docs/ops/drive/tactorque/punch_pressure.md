---
op: punch_pressure
dim: drive
category: tactorque
in: matrix × matrix × scalar × scalar
out: matrix
examples: [poc_tactile_dipole_torque]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# punch_pressure — DRIVE `tactorque` op

- **データ種**: `matrix × matrix × scalar × scalar` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.punch_pressure(X, Y, a: 'float', P: 'float' = 0.0, M1=(0.0, 0.0), pitch: 'float | None' = None, sub: 'int' = 4) -> 'np.ndarray'` (実装を直接呼ぶなら `import tactorque; tactorque.punch_pressure(X, Y, a: 'float', P: 'float' = 0.0, M1=(0.0, 0.0), pitch: 'float | None' = None, sub: 'int' = 4) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("punch_pressure")`)

## 使い方

平頭円形押し込み子(半径 a [m])の圧力 [Pa]: p = P/(2πa√(a²−r²)) + 3(M1_x x + M1_y y)/(2πa³√(a²−r²))(r < a、外は 0)。
第 1 項 = Johnson 1985 式 3.34、第 2 項 = ∫ (x, y) p dA = M1 を満たす反対称項(導出はモジュール docstring、門で数値確認)。
``pitch`` を渡すと画素を sub×sub の副標本で平均する(縁の 1/√ 特異点の格子誤差を減らす。4×4 で Σ p h² が P と 0.6 %、実測)。
**Raises** ValueError: a ≤ 0、P < 0、X と Y の形が違う、|M1| > Pa/3(接触が離れる: 線形の式が成り立たない、fail-closed)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tactile_dipole_torque](../../../../examples/poc_tactile_dipole_torque.py) — `py -3.11 examples/poc_tactile_dipole_torque.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[world_camera](../world/world_camera.md) · [lidar_scan](../lidar/lidar_scan.md) · [relative_motion](../ttc/relative_motion.md) · [foe_from_motion](../ttc/foe_from_motion.md) · [flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [world_materials](../terrain/world_materials.md) · [mesh_signed_volume](../terrain/mesh_signed_volume.md)

## 同カテゴリ(`tactorque`)

[punch_surface_uz](punch_surface_uz.md) · [hertz_pressure_shifted](hertz_pressure_shifted.md) · [ellipse_pressure_shifted](ellipse_pressure_shifted.md) · [pressure_first_moment](pressure_first_moment.md) · [boussinesq_kernel](boussinesq_kernel.md) · [boussinesq_surface_displacement](boussinesq_surface_displacement.md) · [surface_divergence_closed_form](surface_divergence_closed_form.md) · [tilt_shear_field](tilt_shear_field.md)

---
*Provenance: tactorque.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
