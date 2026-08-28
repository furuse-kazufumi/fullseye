---
op: mesh_area
dim: 3d
category: mesh_process
in: mesh
out: measurement
examples: [dl_mesh_curvature, mesh_props]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# mesh_area — 3D `mesh_process` op

- **データ種**: `mesh` → `measurement`
- **呼び出し**: `import mesh_props; mesh_props.mesh_area(mesh) -> 'float'` (または `ops3d.get("mesh_area")`)

## 使い方

三角形メッシュの**表面積**(全三角形面積の総和)。→ float。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [dl_mesh_curvature](../../../../examples_3d/dl_mesh_curvature.py) — `py -3.11 examples_3d/dl_mesh_curvature.py`
- [mesh_props](../../../../examples_3d/mesh_props.py) — `py -3.11 examples_3d/mesh_props.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`mesh_process`)

[laplacian_smooth](laplacian_smooth.md) · [taubin_smooth](taubin_smooth.md) · [decimate_qem](decimate_qem.md) · [face_normals](face_normals.md) · [vertex_normals](vertex_normals.md) · [vertex_curvature](vertex_curvature.md)

---
*Provenance: mesh_props.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
