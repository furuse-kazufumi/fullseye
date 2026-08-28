---
op: mesh_to_points
dim: 3d
category: transform
in: mesh
out: points
examples: [mesh_decimate]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# mesh_to_points — 3D `transform` op

- **データ種**: `mesh` → `points`
- **呼び出し**: `import match3d; match3d.mesh_to_points(vertices, faces, samples=20000, seed=0)` (または `ops3d.get("mesh_to_points")`)

## 使い方

mesh(頂点+面)→ 表面点群(面積重み一様サンプリング)。mesh→point cloud 変換。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [mesh_decimate](../../../../examples_3d/mesh_decimate.py) — `py -3.11 examples_3d/mesh_decimate.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](points_to_voxel.md) · [estimate_point_normals](estimate_point_normals.md) · [to_points](to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md) · [icp_point2plane](../refine/icp_point2plane.md)

## 同カテゴリ(`transform`)

[points_to_voxel](points_to_voxel.md) · [gaussians_to_voxel](gaussians_to_voxel.md) · [mesh_to_voxel](mesh_to_voxel.md) · [depth_to_points](depth_to_points.md) · [voxel_to_mips](voxel_to_mips.md) · [voxel_to_mesh](voxel_to_mesh.md) · [tsdf_from_depth](tsdf_from_depth.md) · [signed_distance_field](signed_distance_field.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
