---
op: mesh_edge_stats
dim: 3d
category: resolution
in: mesh
out: table
examples: [mesh_resolution_demo]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# mesh_edge_stats — 3D `resolution` op

- **データ種**: `mesh` → `table`
- **呼び出し**: `import meshres; meshres.mesh_edge_stats(V, F)` (または `ops3d.get("mesh_edge_stats")`)

## 使い方

Edge-length and face-area percentiles with non-uniformity ratios (``table``).

``edge`` / ``area`` hold p5 / median / p95 / max / min / mean;
``edge_nonuniformity`` = p95/p5 of edge length and ``area_nonuniformity``
= p95/p5 of face area (1 = perfectly uniform; the Itokawa 49k model gives
2.8 / 2.7); ``n_vertices``, ``n_faces``, ``n_edges``, ``bbox_diagonal``,
``boundary_edges`` (edges with one face — 0 for a closed surface),
``non_manifold_edges`` (edges with more than two faces). Use it before
adding synthetic detail: if the ratio is far from 1, the detail you add at
a fixed wavelength will alias on the coarse part and resolve on the fine
part — remesh first (:func:`mesh_isotropic_remesh`).

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

[mesh_detail_map](mesh_detail_map.md) · [mesh_split_long_edges](mesh_split_long_edges.md) · [mesh_isotropic_remesh](mesh_isotropic_remesh.md) · [mesh_sample_points](mesh_sample_points.md) · [mesh_lod_chain](mesh_lod_chain.md) · [mesh_select_lod](mesh_select_lod.md) · [mesh_reduction_report](mesh_reduction_report.md) · [mesh_decimate_preserving](mesh_decimate_preserving.md)

---
*Provenance: meshres.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
