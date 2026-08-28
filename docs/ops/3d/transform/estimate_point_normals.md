---
op: estimate_point_normals
dim: 3d
category: transform
in: points
out: normals
examples: [fpfh_correspondence]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# estimate_point_normals — 3D `transform` op

- **データ種**: `points` → `normals`
- **呼び出し**: `import match3d; match3d.estimate_point_normals(points, k=16, viewpoint=None)` (または `ops3d.get("estimate_point_normals")`)

## 使い方

点群 (N,3) → 単位法線(局所 k 近傍共分散の最小固有ベクトル=PCA)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fpfh_correspondence](../../../../examples_3d/fpfh_correspondence.py) — `py -3.11 examples_3d/fpfh_correspondence.py`

## 型が繋がる次の op(`normals` を入力に取れる)

[icp_point2plane](../refine/icp_point2plane.md) · [compute_fpfh](../feature_register/compute_fpfh.md) · [shot_descriptor](../feature_register/shot_descriptor.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [reflect](../optics/reflect.md) · [refract](../optics/refract.md) · [render_shaded](../render/render_shaded.md) · [phong_shade](../render/phong_shade.md)

## 同カテゴリ(`transform`)

[points_to_voxel](points_to_voxel.md) · [gaussians_to_voxel](gaussians_to_voxel.md) · [mesh_to_voxel](mesh_to_voxel.md) · [mesh_to_points](mesh_to_points.md) · [depth_to_points](depth_to_points.md) · [voxel_to_mips](voxel_to_mips.md) · [voxel_to_mesh](voxel_to_mesh.md) · [tsdf_from_depth](tsdf_from_depth.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
