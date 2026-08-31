---
op: vol_watershed
dim: 3d
category: segment
in: voxel
out: labels
examples: [molecule_atom_count, watershed3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# vol_watershed — 3D `segment` op

- **データ種**: `voxel` → `labels`
- **呼び出し**: `import volops; volops.vol_watershed(vol, markers, mask=None)` (または `ops3d.get("vol_watershed")`)

## 使い方

Marker-controlled 3-D watershed segmentation (**optional — scikit-image**).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [molecule_atom_count](../../../../examples_3d/molecule_atom_count.py) — `py -3.11 examples_3d/molecule_atom_count.py`
- [watershed3d](../../../../examples_3d/watershed3d.py) — `py -3.11 examples_3d/watershed3d.py`

## 型が繋がる次の op(`labels` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [vol_region_props](../regionprops/vol_region_props.md)

## 同カテゴリ(`segment`)

[region_growing](region_growing.md) · [euclidean_cluster](euclidean_cluster.md) · [plane_segmentation](plane_segmentation.md)

---
*Provenance: volops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
