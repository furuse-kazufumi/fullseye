---
op: vol_rle_components
dim: 3d
category: rle_region
in: voxel
out: rle_region
examples: [rle_region_efficiency]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# vol_rle_components — 3D `rle_region` op

- **データ種**: `voxel` → `rle_region`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_rle_components(vol_binary, connectivity=26)` (実装を直接呼ぶなら `import volregion; volregion.vol_rle_components(vol_binary, connectivity=26)`、台帳から引くなら `ops3d.get("vol_rle_components")`)

## 使い方

Split a binary volume into per-component ``VolRLE`` regions.

*The* use case run-length regions exist for: holding every component of a
segmentation as its own region at run-proportional cost, instead of one
dense label volume or N dense masks. Uses the key structural fact that a
run is x-connected, so a component label is constant along each run — the
volume is labelled once (dense, same 6/18/26 semantics as
``volops.vol_label``) and then each *run* is assigned by its first voxel's
label; no per-component dense mask is ever built.

Returns a list of ``VolRLE`` ordered by label id (1..n). An empty mask
returns an empty list.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [rle_region_efficiency](../../../../examples_3d/rle_region_efficiency.py) — `py -3.11 examples_3d/rle_region_efficiency.py`

## 型が繋がる次の op(`rle_region` を入力に取れる)

[vol_rle_decode](vol_rle_decode.md) · [vol_rle_volume](vol_rle_volume.md) · [vol_rle_bbox](vol_rle_bbox.md) · [vol_rle_centroid](vol_rle_centroid.md) · [vol_rle_union](vol_rle_union.md) · [vol_rle_intersect](vol_rle_intersect.md) · [vol_rle_difference](vol_rle_difference.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`rle_region`)

[vol_rle_encode](vol_rle_encode.md) · [vol_rle_decode](vol_rle_decode.md) · [vol_rle_volume](vol_rle_volume.md) · [vol_rle_bbox](vol_rle_bbox.md) · [vol_rle_centroid](vol_rle_centroid.md) · [vol_rle_union](vol_rle_union.md) · [vol_rle_intersect](vol_rle_intersect.md) · [vol_rle_difference](vol_rle_difference.md)

---
*Provenance: volregion.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
