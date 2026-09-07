---
op: mesh_split_long_edges
dim: 3d
category: resolution
in: mesh
out: mesh
examples: [mesh_resolution_demo]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# mesh_split_long_edges — 3D `resolution` op

- **データ種**: `mesh` → `mesh`
- **呼び出し**: `import fullseye as fs; fs.ledger.mesh_split_long_edges(V, F, max_edge, max_passes=20)` (実装を直接呼ぶなら `import meshres; meshres.mesh_split_long_edges(V, F, max_edge, max_passes=20)`、台帳から引くなら `ops3d.get("mesh_split_long_edges")`)

## 使い方

Bisect edges longer than *max_edge* until none remains — adaptive refinement (``mesh``).

Each pass splits every over-long edge at its midpoint and re-triangulates
each affected face by the number of split edges (1 → 2, 2 → 3, 3 → 4
triangles), so there are never T-junctions and faces that are already fine
are untouched: the refinement lands exactly where the mesh is coarse.
Stops after *max_passes* (``ValueError`` if edges still exceed the target
then). Vertex positions are not moved — the shape is preserved exactly.

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [mesh_resolution_demo](../../../../examples_3d/mesh_resolution_demo.py) — `py -3.11 examples_3d/mesh_resolution_demo.py`

## 型が繋がる次の op(`mesh` を入力に取れる)

[mesh_to_voxel](../transform/mesh_to_voxel.md) · [mesh_to_points](../transform/mesh_to_points.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [ambient_occlusion](../render/ambient_occlusion.md) · [cast_shadow](../render/cast_shadow.md) · [supersample_mesh](../render/supersample_mesh.md) · [render_beauty](../render/render_beauty.md)

## 同カテゴリ(`resolution`)

[mesh_edge_stats](mesh_edge_stats.md) · [mesh_detail_map](mesh_detail_map.md) · [mesh_isotropic_remesh](mesh_isotropic_remesh.md) · [mesh_sample_points](mesh_sample_points.md) · [mesh_lod_chain](mesh_lod_chain.md) · [mesh_select_lod](mesh_select_lod.md) · [mesh_reduction_report](mesh_reduction_report.md) · [mesh_decimate_preserving](mesh_decimate_preserving.md)

---
*Provenance: meshres.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
