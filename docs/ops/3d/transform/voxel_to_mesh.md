---
op: voxel_to_mesh
dim: 3d
category: transform
in: voxel
out: mesh
examples: [mesh_smooth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# voxel_to_mesh — 3D `transform` op

- **データ種**: `voxel` → `mesh`
- **呼び出し**: `import match3d; match3d.voxel_to_mesh(vol, iso=0.5)` (または `ops3d.get("voxel_to_mesh")`)

## 使い方

voxel → mesh(marching cubes、skimage)。返り値 (verts, faces, normals)。voxel→mesh 変換。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [mesh_smooth](../../../../examples_3d/mesh_smooth.py) — `py -3.11 examples_3d/mesh_smooth.py`

## 型が繋がる次の op(`mesh` を入力に取れる)

[mesh_to_voxel](mesh_to_voxel.md) · [mesh_to_points](mesh_to_points.md) · [to_points](to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [ambient_occlusion](../render/ambient_occlusion.md) · [cast_shadow](../render/cast_shadow.md) · [supersample_mesh](../render/supersample_mesh.md) · [render_beauty](../render/render_beauty.md)

## 同カテゴリ(`transform`)

[points_to_voxel](points_to_voxel.md) · [gaussians_to_voxel](gaussians_to_voxel.md) · [mesh_to_voxel](mesh_to_voxel.md) · [mesh_to_points](mesh_to_points.md) · [depth_to_points](depth_to_points.md) · [voxel_to_mips](voxel_to_mips.md) · [tsdf_from_depth](tsdf_from_depth.md) · [signed_distance_field](signed_distance_field.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
