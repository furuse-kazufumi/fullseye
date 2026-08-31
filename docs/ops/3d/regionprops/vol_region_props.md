---
op: vol_region_props
dim: 3d
category: regionprops
in: labels
out: table
examples: [vessel_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# vol_region_props — 3D `regionprops` op

- **データ種**: `labels` → `table`
- **呼び出し**: `import volops; volops.vol_region_props(labels, spacing=None, surface='auto')` (または `ops3d.get("vol_region_props")`)

## 使い方

Per-component quantitative descriptors from a label volume.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [vessel_metrology](../../../../examples_3d/vessel_metrology.py) — `py -3.11 examples_3d/vessel_metrology.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`regionprops`)

[label_components](label_components.md) · [region_props](region_props.md) · [largest_component](largest_component.md) · [filter_by_volume](filter_by_volume.md) · [inner_box3](inner_box3.md) · [vol_label](vol_label.md)

---
*Provenance: volops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
