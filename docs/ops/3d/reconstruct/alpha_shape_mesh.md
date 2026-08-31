---
op: alpha_shape_mesh
dim: 3d
category: reconstruct
in: points
out: mesh
examples: [alpha_shape_topology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# alpha_shape_mesh — 3D `reconstruct` op

- **データ種**: `points` → `mesh`
- **呼び出し**: `import recon3d; recon3d.alpha_shape_mesh(points, alpha)` (または `ops3d.get("alpha_shape_mesh")`)

## 使い方

alpha shapes による**表面三角形メッシュ**(点群 → (vertices, faces))。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [alpha_shape_topology](../../../../examples_3d/alpha_shape_topology.py) — `py -3.11 examples_3d/alpha_shape_topology.py`

## 型が繋がる次の op(`mesh` を入力に取れる)

[mesh_to_voxel](../transform/mesh_to_voxel.md) · [mesh_to_points](../transform/mesh_to_points.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [ambient_occlusion](../render/ambient_occlusion.md) · [cast_shadow](../render/cast_shadow.md) · [supersample_mesh](../render/supersample_mesh.md) · [render_beauty](../render/render_beauty.md)

## 同カテゴリ(`reconstruct`)

[poisson_lite](poisson_lite.md) · [alpha_shape_boundary](alpha_shape_boundary.md) · [estimate_alpha](estimate_alpha.md)

---
*Provenance: recon3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
