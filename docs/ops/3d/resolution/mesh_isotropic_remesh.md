---
op: mesh_isotropic_remesh
dim: 3d
category: resolution
in: mesh
out: mesh
examples: [mesh_resolution_demo]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# mesh_isotropic_remesh — 3D `resolution` op

- **データ種**: `mesh` → `mesh`
- **呼び出し**: `import fullseye as fs; fs.ledger.mesh_isotropic_remesh(V, F, target_edge, iterations=5, project=True, relax=0.5)` (実装を直接呼ぶなら `import meshres; meshres.mesh_isotropic_remesh(V, F, target_edge, iterations=5, project=True, relax=0.5)`、台帳から引くなら `ops3d.get("mesh_isotropic_remesh")`)

## 使い方

Incremental isotropic remeshing to a uniform *target_edge* (``mesh``).

Botsch & Kobbelt, *A Remeshing Approach to Multiresolution Modeling*
(SGP 2004): per iteration (1) split edges longer than 4/3·L, (2) collapse
edges shorter than 4/5·L into their midpoint when the link condition
holds, no incident edge would exceed 4/3·L and no face flips, (3) flip
edges that bring the four valences closer to 6, (4) relax each vertex
toward its neighbours' centroid in the tangent plane (*relax* ∈ [0,1]),
(5) project the result back onto the **input** surface (closest point on
the original triangles, *project*=True) so the shape is not smoothed
away. Boundary vertices are pinned. The result is a triangle mesh whose
edge lengths cluster around L regardless of how the input was sampled —
the fix for "coarse and dense regions treated alike". Measured on a
pole-clustered UV sphere: edge p95/p5 from 5.6 to < 1.5, area within 2 %,
closed manifold preserved (``tests/test_meshres.py``).

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

[mesh_edge_stats](mesh_edge_stats.md) · [mesh_detail_map](mesh_detail_map.md) · [mesh_split_long_edges](mesh_split_long_edges.md) · [mesh_sample_points](mesh_sample_points.md) · [mesh_lod_chain](mesh_lod_chain.md) · [mesh_select_lod](mesh_select_lod.md) · [mesh_reduction_report](mesh_reduction_report.md) · [mesh_decimate_preserving](mesh_decimate_preserving.md)

---
*Provenance: meshres.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
