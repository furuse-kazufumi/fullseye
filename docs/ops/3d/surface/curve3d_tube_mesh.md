---
op: curve3d_tube_mesh
dim: 3d
category: surface
in: points
out: mesh
examples: [minimal_surfaces]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# curve3d_tube_mesh — 3D `surface` op

- **データ種**: `points` → `mesh`
- **呼び出し**: `import fullseye as fs; fs.ledger.curve3d_tube_mesh(points, radius=0.1, segments=12, closed=False)` (実装を直接呼ぶなら `import render3d; render3d.curve3d_tube_mesh(points, radius=0.1, segments=12, closed=False)`、台帳から引くなら `ops3d.get("curve3d_tube_mesh")`)

## 使い方

A space curve as a tube mesh — the MATLAB ``tubeplot``, with a volume you can check.

Sweeps a circle of *radius* along the polyline using a **parallel-transport**
frame (no Frenet frame: the normal of a straight segment is undefined and the
binormal flips at an inflection, which twists the tube). Returns
``(vertices, faces)`` for the existing 3-D viewers and mesh ops.

★**Why this earns its place**: for a closed circular centre line the tube is a
torus, whose volume ``2 pi^2 R r^2`` and area ``4 pi^2 R r`` are analytic —
and the existing ``mesh_volume`` / ``mesh_area`` ops measure the result. Two
independent implementations meeting at a closed form is a real check; "it
looks like a tube" is not.

**Raises** ``ValueError``: fewer than 2 points; not (N, 3); radius not
positive; fewer than 3 segments; non-finite input; a curve with repeated
consecutive points (the direction is undefined there).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [minimal_surfaces](../../../../examples_3d/minimal_surfaces.py) — `py -3.11 examples_3d/minimal_surfaces.py`

## 型が繋がる次の op(`mesh` を入力に取れる)

[mesh_to_voxel](../transform/mesh_to_voxel.md) · [mesh_to_points](../transform/mesh_to_points.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [ambient_occlusion](../render/ambient_occlusion.md) · [cast_shadow](../render/cast_shadow.md) · [supersample_mesh](../render/supersample_mesh.md) · [render_beauty](../render/render_beauty.md)

## 同カテゴリ(`surface`)

[minimal_surface](minimal_surface.md) · [minimal_surface_bend](minimal_surface_bend.md) · [gyroid_isosurface](gyroid_isosurface.md) · [gyroid_solid_mask](gyroid_solid_mask.md)

---
*Provenance: render3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
