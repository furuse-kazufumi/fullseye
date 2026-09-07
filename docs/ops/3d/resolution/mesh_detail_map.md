---
op: mesh_detail_map
dim: 3d
category: resolution
in: mesh
out: table
examples: [mesh_resolution_demo]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# mesh_detail_map — 3D `resolution` op

- **データ種**: `mesh` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.mesh_detail_map(V, F)` (実装を直接呼ぶなら `import meshres; meshres.mesh_detail_map(V, F)`、台帳から引くなら `ops3d.get("mesh_detail_map")`)

## 使い方

Per-vertex coarseness and detail of a mesh (``table``).

``coarseness`` (nv,) — mean incident edge length, mapped linearly from the
5th percentile (0) to the 95th (1) and clipped; ``edge_length`` (nv,) the
raw value. ``detail`` (nv,) — mean angle (radians) between the normals of
the faces around the vertex divided by the mean incident edge length: a
curvature proxy in 1/unit that is high where the *data* already carries
relief, independent of how densely it is sampled. ``relief_weight`` (nv,)
= ``coarseness × (1 − detail_norm)`` — 1 where the mesh is coarse and
smooth (add synthetic detail), 0 where it is fine or already rough — the
weight :func:`render3d.mesh_displace_fbm`-style steps should multiply
their amplitude by. Also ``stats`` for each map.

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [mesh_resolution_demo](../../../../examples_3d/mesh_resolution_demo.py) — `py -3.11 examples_3d/mesh_resolution_demo.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [mesh_select_lod](mesh_select_lod.md)

## 同カテゴリ(`resolution`)

[mesh_edge_stats](mesh_edge_stats.md) · [mesh_split_long_edges](mesh_split_long_edges.md) · [mesh_isotropic_remesh](mesh_isotropic_remesh.md) · [mesh_sample_points](mesh_sample_points.md) · [mesh_lod_chain](mesh_lod_chain.md) · [mesh_select_lod](mesh_select_lod.md) · [mesh_reduction_report](mesh_reduction_report.md) · [mesh_decimate_preserving](mesh_decimate_preserving.md)

---
*Provenance: meshres.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
