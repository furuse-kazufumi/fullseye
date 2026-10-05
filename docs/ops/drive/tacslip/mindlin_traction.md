---
op: mindlin_traction
dim: drive
category: tacslip
in: matrix × table
out: matrix
examples: [poc_tacsim_marker_shear]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# mindlin_traction — DRIVE `tacslip` op

- **データ種**: `matrix × table` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.mindlin_traction(r, mp: 'dict') -> 'np.ndarray'` (実装を直接呼ぶなら `import tacslip; tacslip.mindlin_traction(r, mp: 'dict') -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("mindlin_traction")`)

## 使い方

接線トラクション q(r) = q′ − q″ [Pa]: q′ = μp0√(1−r²/a²)(r < a)、q″ = μp0(c/a)√(1−r²/c²)(r < c)。滑り環 c ≤ r < a では q = μp(r)
(Coulomb の限界に張り付く)、固着円では q < μp。``mp`` は :func:`mindlin_partial_slip` の表。r と同じ形。**Raises** ValueError: mp に a/c/mu/p0 が無い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacsim_marker_shear](../../../../examples/poc_tacsim_marker_shear.py) — `py -3.11 examples/poc_tacsim_marker_shear.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[world_camera](../world/world_camera.md) · [lidar_scan](../lidar/lidar_scan.md) · [relative_motion](../ttc/relative_motion.md) · [foe_from_motion](../ttc/foe_from_motion.md) · [flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [world_materials](../terrain/world_materials.md) · [mesh_signed_volume](../terrain/mesh_signed_volume.md)

## 同カテゴリ(`tacslip`)

[mindlin_partial_slip](mindlin_partial_slip.md) · [hertz_surface_ur](hertz_surface_ur.md) · [hertzian_tangential_inner](hertzian_tangential_inner.md) · [cerruti_kernel](cerruti_kernel.md) · [cerruti_surface_displacement](cerruti_surface_displacement.md) · [membrane_shear_field](membrane_shear_field.md) · [membrane_markers](membrane_markers.md) · [displace_markers](displace_markers.md)

---
*Provenance: tacslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
