---
op: hertz_surface_uz
dim: drive
category: tacsim
in: matrix × scalar × scalar × scalar
out: matrix
examples: [poc_tacsim_elastic_membrane, poc_tactile_dipole_torque]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# hertz_surface_uz — DRIVE `tacsim` op

- **データ種**: `matrix × scalar × scalar × scalar` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.hertz_surface_uz(r, a: 'float', delta: 'float', R: 'float') -> 'np.ndarray'` (実装を直接呼ぶなら `import tacsim; tacsim.hertz_surface_uz(r, a: 'float', delta: 'float', R: 'float') -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("hertz_surface_uz")`)

## 使い方

Hertz 球接触の半空間表面の法線変位 ū_z(r)(沈む量 ≥ 0、r と同じ形の配列)。

内側 r ≤ a: δ − r²/(2R)。外側: (1/πR)[(2a² − r²) arcsin(a/r) + a r √(1 − a²/r²)] (Johnson 式 3.42a)。r = a で δ/2 に連続。
**Raises** ``ValueError``: a, δ, R ≤ 0、a² と Rδ が 1 % 以上食い違う(Hertz でない組)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacsim_elastic_membrane](../../../../examples/poc_tacsim_elastic_membrane.py) — `py -3.11 examples/poc_tacsim_elastic_membrane.py`
- [poc_tactile_dipole_torque](../../../../examples/poc_tactile_dipole_torque.py) — `py -3.11 examples/poc_tactile_dipole_torque.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[world_camera](../world/world_camera.md) · [lidar_scan](../lidar/lidar_scan.md) · [relative_motion](../ttc/relative_motion.md) · [foe_from_motion](../ttc/foe_from_motion.md) · [flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [world_materials](../terrain/world_materials.md) · [mesh_signed_volume](../terrain/mesh_signed_volume.md)

## 同カテゴリ(`tacsim`)

[combined_modulus](combined_modulus.md) · [hertz_sphere](hertz_sphere.md) · [hertz_force](hertz_force.md) · [hertz_cylinder](hertz_cylinder.md) · [hertz_pressure](hertz_pressure.md) · [membrane_indent_sphere](membrane_indent_sphere.md) · [membrane_indent_shape](membrane_indent_shape.md) · [membrane_lights](membrane_lights.md)

---
*Provenance: tacsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
