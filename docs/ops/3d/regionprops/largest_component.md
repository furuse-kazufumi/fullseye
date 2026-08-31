---
op: largest_component
dim: 3d
category: regionprops
in: voxel
out: voxel
examples: [region_props_3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# largest_component — 3D `regionprops` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import regionprops3d; regionprops3d.largest_component(vol, connectivity: 'int' = 26) -> 'np.ndarray'` (または `ops3d.get("largest_component")`)

## 使い方

最大(最多ボクセル)連結成分の bool マスクを返す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [region_props_3d](../../../../examples_3d/region_props_3d.py) — `py -3.11 examples_3d/region_props_3d.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`regionprops`)

[label_components](label_components.md) · [region_props](region_props.md) · [filter_by_volume](filter_by_volume.md) · [inner_box3](inner_box3.md) · [vol_label](vol_label.md) · [vol_region_props](vol_region_props.md)

---
*Provenance: regionprops3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
