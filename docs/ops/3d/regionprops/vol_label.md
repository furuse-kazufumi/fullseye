---
op: vol_label
dim: 3d
category: regionprops
in: voxel
out: labels
examples: [ct_bone_segmentation, molecule_atom_count, vessel_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# vol_label — 3D `regionprops` op

- **データ種**: `voxel` → `labels`
- **呼び出し**: `import volops; volops.vol_label(vol_binary, connectivity=26)` (または `ops3d.get("vol_label")`)

## 使い方

3-D connected-component labelling with a selectable neighbourhood.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_bone_segmentation](../../../../examples_3d/ct_bone_segmentation.py) — `py -3.11 examples_3d/ct_bone_segmentation.py`
- [molecule_atom_count](../../../../examples_3d/molecule_atom_count.py) — `py -3.11 examples_3d/molecule_atom_count.py`
- [vessel_metrology](../../../../examples_3d/vessel_metrology.py) — `py -3.11 examples_3d/vessel_metrology.py`

## 型が繋がる次の op(`labels` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [vol_region_props](vol_region_props.md)

## 同カテゴリ(`regionprops`)

[label_components](label_components.md) · [region_props](region_props.md) · [largest_component](largest_component.md) · [filter_by_volume](filter_by_volume.md) · [inner_box3](inner_box3.md) · [vol_region_props](vol_region_props.md)

---
*Provenance: volops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
