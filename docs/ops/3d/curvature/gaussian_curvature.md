---
op: gaussian_curvature
dim: 3d
category: curvature
in: points
out: signal
examples: [curvature_grasp, curvature_shape_index]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# gaussian_curvature — 3D `curvature` op

- **データ種**: `points` → `signal`
- **呼び出し**: `import curvature3d; curvature3d.gaussian_curvature(points, k=25)` (または `ops3d.get("gaussian_curvature")`)

## 使い方

ガウス曲率 K=k1·k2(法線の反転に不変)。→ (N,)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [curvature_grasp](../../../../examples_3d/curvature_grasp.py) — `py -3.11 examples_3d/curvature_grasp.py`
- [curvature_shape_index](../../../../examples_3d/curvature_shape_index.py) — `py -3.11 examples_3d/curvature_shape_index.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`curvature`)

[principal_curvatures](principal_curvatures.md) · [mean_curvature](mean_curvature.md) · [shape_index](shape_index.md) · [estimate_normals](estimate_normals.md)

---
*Provenance: curvature3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
