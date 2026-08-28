---
op: medial_match
dim: 3d
category: medial
in: voxel × voxel
out: measurement
examples: [medial_topology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# medial_match — 3D `medial` op

- **データ種**: `voxel × voxel` → `measurement`
- **呼び出し**: `import medial; medial.medial_match(vol_a, vol_b, w_topology=0.6, w_radius=0.4, n_bins=12)` (または `ops3d.get("medial_match")`)

## 使い方

2 つの voxel 形状の medial(位相 + 半径分布)による粗照合スコア。返り値 [0,1]。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [medial_topology](../../../../examples_3d/medial_topology.py) — `py -3.11 examples_3d/medial_topology.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`medial`)

[distance_ridge](distance_ridge.md) · [skeletonize_vol](skeletonize_vol.md) · [medial_axis_points](medial_axis_points.md) · [topology_signature](topology_signature.md)

---
*Provenance: medial.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
