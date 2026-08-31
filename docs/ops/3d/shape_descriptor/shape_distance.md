---
op: shape_distance
dim: 3d
category: shape_descriptor
in: descriptor × descriptor
out: measurement
examples: [moment_invariants, shape_desc_pose, shape_retrieval]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# shape_distance — 3D `shape_descriptor` op

- **データ種**: `descriptor × descriptor` → `measurement`
- **呼び出し**: `import descriptors3d; descriptors3d.shape_distance(desc_a, desc_b, metric: 'str' = 'l1') -> 'float'` (または `ops3d.get("shape_distance")`)

## 使い方

2 つの記述子間の距離。小さいほど同形状。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [moment_invariants](../../../../examples_3d/moment_invariants.py) — `py -3.11 examples_3d/moment_invariants.py`
- [shape_desc_pose](../../../../examples_3d/shape_desc_pose.py) — `py -3.11 examples_3d/shape_desc_pose.py`
- [shape_retrieval](../../../../examples_3d/shape_retrieval.py) — `py -3.11 examples_3d/shape_retrieval.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`shape_descriptor`)

[d2_distribution](d2_distribution.md) · [a3_distribution](a3_distribution.md) · [extent_signature](extent_signature.md) · [describe](describe.md)

---
*Provenance: descriptors3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
