---
op: principal_curvatures
dim: 3d
category: curvature
in: points
out: curvature
examples: [curvature_grasp, itokawa_curvature]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# principal_curvatures — 3D `curvature` op

- **データ種**: `points` → `curvature`
- **呼び出し**: `import curvature3d; curvature3d.principal_curvatures(points, k=25, normals=None)` (または `ops3d.get("principal_curvatures")`)

## 使い方

各点の主曲率 (k1>=k2)。→ (k1 (N,), k2 (N,))。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [curvature_grasp](../../../../examples_3d/curvature_grasp.py) — `py -3.11 examples_3d/curvature_grasp.py`
- [itokawa_curvature](../../../../examples_3d/itokawa_curvature.py) — `py -3.11 examples_3d/itokawa_curvature.py`

## 型が繋がる次の op(`curvature` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`curvature`)

[mean_curvature](mean_curvature.md) · [gaussian_curvature](gaussian_curvature.md) · [shape_index](shape_index.md) · [estimate_normals](estimate_normals.md)

---
*Provenance: curvature3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
