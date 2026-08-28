---
op: decimate_qem
dim: 3d
category: mesh_process
in: mesh
out: mesh
examples: [mesh_decimate, mesh_lod_download]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# decimate_qem — 3D `mesh_process` op

- **データ種**: `mesh` → `mesh`
- **呼び出し**: `import meshrepair; meshrepair.decimate_qem(V, F, target_faces)` (または `ops3d.get("decimate_qem")`)

## 使い方

Quadric-error-metric edge-collapse decimation toward *target_faces*.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [mesh_decimate](../../../../examples_3d/mesh_decimate.py) — `py -3.11 examples_3d/mesh_decimate.py`
- [mesh_lod_download](../../../../examples_3d/mesh_lod_download.py) — `py -3.11 examples_3d/mesh_lod_download.py`

## 型が繋がる次の op(`mesh` を入力に取れる)

[mesh_to_voxel](../transform/mesh_to_voxel.md) · [mesh_to_points](../transform/mesh_to_points.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [ambient_occlusion](../render/ambient_occlusion.md) · [cast_shadow](../render/cast_shadow.md) · [supersample_mesh](../render/supersample_mesh.md) · [render_beauty](../render/render_beauty.md)

## 同カテゴリ(`mesh_process`)

[laplacian_smooth](laplacian_smooth.md) · [taubin_smooth](taubin_smooth.md) · [face_normals](face_normals.md) · [vertex_normals](vertex_normals.md) · [mesh_area](mesh_area.md) · [vertex_curvature](vertex_curvature.md)

---
*Provenance: meshrepair.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
