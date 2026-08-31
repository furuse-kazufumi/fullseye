---
op: mean_curvature
dim: 3d
category: curvature
in: points
out: signal
examples: [curvature_shape_index]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# mean_curvature — 3D `curvature` op

- **データ種**: `points` → `signal`
- **呼び出し**: `import curvature3d; curvature3d.mean_curvature(points, k=25, normals=None)` (または `ops3d.get("mean_curvature")`)

## 使い方

平均曲率 H=(k1+k2)/2。→ (N,)。向きに依存する量。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [curvature_shape_index](../../../../examples_3d/curvature_shape_index.py) — `py -3.11 examples_3d/curvature_shape_index.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`curvature`)

[principal_curvatures](principal_curvatures.md) · [gaussian_curvature](gaussian_curvature.md) · [shape_index](shape_index.md) · [estimate_normals](estimate_normals.md)

---
*Provenance: curvature3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
