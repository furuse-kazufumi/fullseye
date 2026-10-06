---
op: displace_markers
dim: drive
category: tacslip
in: matrix × matrix × matrix × scalar
out: matrix
examples: [poc_tacsim_marker_shear, poc_tactile_dipole_torque]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# displace_markers — DRIVE `tacslip` op

- **データ種**: `matrix × matrix × matrix × scalar` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.displace_markers(pts, fx, fy, pitch: 'float') -> 'np.ndarray'` (実装を直接呼ぶなら `import tacslip; tacslip.displace_markers(pts, fx, fy, pitch: 'float') -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("displace_markers")`)

## 使い方

変位場 fx, fy (n, n) [m] でマーカー中心 (N, 2) [px] を移す(場は中心位置で双線形標本化、画素に換算して足す)。
**Raises** ValueError: pts が (N, 2) でない、fx と fy の形が違う、pitch ≤ 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacsim_marker_shear](../../../../examples/poc_tacsim_marker_shear.py) — `py -3.11 examples/poc_tacsim_marker_shear.py`
- [poc_tactile_dipole_torque](../../../../examples/poc_tactile_dipole_torque.py) — `py -3.11 examples/poc_tactile_dipole_torque.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[world_camera](../world/world_camera.md) · [lidar_scan](../lidar/lidar_scan.md) · [relative_motion](../ttc/relative_motion.md) · [foe_from_motion](../ttc/foe_from_motion.md) · [flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [world_materials](../terrain/world_materials.md) · [mesh_signed_volume](../terrain/mesh_signed_volume.md)

## 同カテゴリ(`tacslip`)

[mindlin_partial_slip](mindlin_partial_slip.md) · [mindlin_traction](mindlin_traction.md) · [hertz_surface_ur](hertz_surface_ur.md) · [hertzian_tangential_inner](hertzian_tangential_inner.md) · [cerruti_kernel](cerruti_kernel.md) · [cerruti_surface_displacement](cerruti_surface_displacement.md) · [membrane_shear_field](membrane_shear_field.md) · [membrane_markers](membrane_markers.md)

---
*Provenance: tacslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
