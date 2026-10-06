---
op: membrane_lights
dim: drive
category: tacsim
in: scalar
out: matrix
examples: [poc_tacsim_elastic_membrane, poc_tacsim_marker_shear, poc_tactile_dipole_torque]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# membrane_lights — DRIVE `tacsim` op

- **データ種**: `scalar` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.membrane_lights(elev_deg: 'float' = 55.0, azimuths_deg=(90.0, 210.0, 330.0)) -> 'np.ndarray'` (実装を直接呼ぶなら `import tacsim; tacsim.membrane_lights(elev_deg: 'float' = 55.0, azimuths_deg=(90.0, 210.0, 330.0)) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("membrane_lights")`)

## 使い方

多方向の色つき照明の単位方向ベクトル (N, 3)(行 k が色チャネル k の光源、既定は方位 90/210/330°・仰角 55° の 3 灯)。

**Raises** ``ValueError``: 仰角が (0°, 90°] の外、光源が 3 灯未満、3 灯が同一平面(rank < 3 でフォトメトリックステレオが解けない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacsim_elastic_membrane](../../../../examples/poc_tacsim_elastic_membrane.py) — `py -3.11 examples/poc_tacsim_elastic_membrane.py`
- [poc_tacsim_marker_shear](../../../../examples/poc_tacsim_marker_shear.py) — `py -3.11 examples/poc_tacsim_marker_shear.py`
- [poc_tactile_dipole_torque](../../../../examples/poc_tactile_dipole_torque.py) — `py -3.11 examples/poc_tactile_dipole_torque.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[world_camera](../world/world_camera.md) · [lidar_scan](../lidar/lidar_scan.md) · [relative_motion](../ttc/relative_motion.md) · [foe_from_motion](../ttc/foe_from_motion.md) · [flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [world_materials](../terrain/world_materials.md) · [mesh_signed_volume](../terrain/mesh_signed_volume.md)

## 同カテゴリ(`tacsim`)

[combined_modulus](combined_modulus.md) · [hertz_sphere](hertz_sphere.md) · [hertz_force](hertz_force.md) · [hertz_cylinder](hertz_cylinder.md) · [hertz_surface_uz](hertz_surface_uz.md) · [hertz_pressure](hertz_pressure.md) · [membrane_indent_sphere](membrane_indent_sphere.md) · [membrane_indent_shape](membrane_indent_shape.md)

---
*Provenance: tacsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
