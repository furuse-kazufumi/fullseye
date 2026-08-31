---
op: estimate_normals
dim: 3d
category: curvature
in: points
out: normals
examples: [cylinder_axis_metrology, feature_register, oriented_normals]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# estimate_normals — 3D `curvature` op

- **データ種**: `points` → `normals`
- **呼び出し**: `import curvature3d; curvature3d.estimate_normals(points, k=25)` (または `ops3d.get("estimate_normals")`)

## 使い方

外向き(近傍重心から離れる)に統一した点群法線。→ (N,3)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [cylinder_axis_metrology](../../../../examples_3d/cylinder_axis_metrology.py) — `py -3.11 examples_3d/cylinder_axis_metrology.py`
- [feature_register](../../../../examples_3d/feature_register.py) — `py -3.11 examples_3d/feature_register.py`
- [oriented_normals](../../../../examples_3d/oriented_normals.py) — `py -3.11 examples_3d/oriented_normals.py`

## 型が繋がる次の op(`normals` を入力に取れる)

[icp_point2plane](../refine/icp_point2plane.md) · [compute_fpfh](../feature_register/compute_fpfh.md) · [shot_descriptor](../feature_register/shot_descriptor.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [reflect](../optics/reflect.md) · [refract](../optics/refract.md) · [normal_consistency](../metrics/normal_consistency.md) · [ransac_cylinder](../robust_fit/ransac_cylinder.md)

## 同カテゴリ(`curvature`)

[principal_curvatures](principal_curvatures.md) · [mean_curvature](mean_curvature.md) · [gaussian_curvature](gaussian_curvature.md) · [shape_index](shape_index.md)

---
*Provenance: curvature3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
