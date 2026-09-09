---
op: vol_watershed
dim: 3d
category: segment
in: voxel
out: labels
examples: [molecule_atom_count]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# vol_watershed — 3D `segment` op

- **データ種**: `voxel` → `labels`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_watershed(vol, markers, mask=None)` (実装を直接呼ぶなら `import volops; volops.vol_watershed(vol, markers, mask=None)`、台帳から引くなら `ops3d.get("vol_watershed")`)

## 使い方

Marker-controlled 3-D watershed segmentation (**optional — scikit-image**).

Floods the volume from the labelled *markers* (an int volume, ``0`` = unset),
optionally restricted to *mask*. Delegates to
``skimage.segmentation.watershed`` — treat *vol* as a landscape (e.g. a
gradient magnitude, or the negated distance transform for splitting touching
blobs). Returns an ``int32`` ``(D, H, W)`` label volume.

Raises ``ImportError`` with a clear ``pip install scikit-image`` message when
the optional dependency is absent; the rest of this module needs only
numpy + scipy.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [molecule_atom_count](../../../../examples_3d/molecule_atom_count.py) — `py -3.11 examples_3d/molecule_atom_count.py`

## 型が繋がる次の op(`labels` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [vol_region_props](../regionprops/vol_region_props.md)

## 同カテゴリ(`segment`)

[region_growing](region_growing.md) · [euclidean_cluster](euclidean_cluster.md) · [plane_segmentation](plane_segmentation.md)

---
*Provenance: volops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
