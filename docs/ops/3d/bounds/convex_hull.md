---
op: convex_hull
dim: 3d
category: bounds
in: points
out: mesh
examples: [hull_bounds]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# convex_hull — 3D `bounds` op

- **データ種**: `points` → `mesh`
- **呼び出し**: `import meshrepair; meshrepair.convex_hull(V)` (または `ops3d.get("convex_hull")`)

## 使い方

Convex hull of a point set -> ``(V, F)`` with outward-oriented triangles.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [hull_bounds](../../../../examples_3d/hull_bounds.py) — `py -3.11 examples_3d/hull_bounds.py`

## 型が繋がる次の op(`mesh` を入力に取れる)

[mesh_to_voxel](../transform/mesh_to_voxel.md) · [mesh_to_points](../transform/mesh_to_points.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [ambient_occlusion](../render/ambient_occlusion.md) · [cast_shadow](../render/cast_shadow.md) · [supersample_mesh](../render/supersample_mesh.md) · [render_beauty](../render/render_beauty.md)

## 同カテゴリ(`bounds`)

[aabb](aabb.md) · [obb](obb.md) · [min_enclosing_sphere](min_enclosing_sphere.md)

---
*Provenance: meshrepair.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
