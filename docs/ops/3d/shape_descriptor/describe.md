---
op: describe
dim: 3d
category: shape_descriptor
in: points
out: descriptor
examples: [denoise_evolution, shape_desc_pose, shape_retrieval]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# describe — 3D `shape_descriptor` op

- **データ種**: `points` → `descriptor`
- **呼び出し**: `import descriptors3d; descriptors3d.describe(points, bins: 'int' = 64, seed: 'int' = 0) -> 'np.ndarray'` (または `ops3d.get("describe")`)

## 使い方

D2 + A3 + extent を連結した大域形状記述子を返す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [denoise_evolution](../../../../examples_3d/denoise_evolution.py) — `py -3.11 examples_3d/denoise_evolution.py`
- [shape_desc_pose](../../../../examples_3d/shape_desc_pose.py) — `py -3.11 examples_3d/shape_desc_pose.py`
- [shape_retrieval](../../../../examples_3d/shape_retrieval.py) — `py -3.11 examples_3d/shape_retrieval.py`

## 型が繋がる次の op(`descriptor` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [shape_distance](shape_distance.md)

## 同カテゴリ(`shape_descriptor`)

[d2_distribution](d2_distribution.md) · [a3_distribution](a3_distribution.md) · [extent_signature](extent_signature.md) · [shape_distance](shape_distance.md)

---
*Provenance: descriptors3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
