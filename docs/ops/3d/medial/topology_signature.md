---
op: topology_signature
dim: 3d
category: medial
in: voxel
out: descriptor
examples: [medial_topology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# topology_signature — 3D `medial` op

- **データ種**: `voxel` → `descriptor`
- **呼び出し**: `import medial; medial.topology_signature(skeleton)` (または `ops3d.get("topology_signature")`)

## 使い方

骨格の 26 近傍次数から位相記述子を作る。端点/分岐点/通常点/孤立点の個数を返す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [medial_topology](../../../../examples_3d/medial_topology.py) — `py -3.11 examples_3d/medial_topology.py`

## 型が繋がる次の op(`descriptor` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [shape_distance](../shape_descriptor/shape_distance.md)

## 同カテゴリ(`medial`)

[distance_ridge](distance_ridge.md) · [skeletonize_vol](skeletonize_vol.md) · [medial_axis_points](medial_axis_points.md) · [medial_match](medial_match.md)

---
*Provenance: medial.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
