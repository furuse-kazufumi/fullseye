---
op: mesh_decimate_preserving
dim: 3d
category: resolution
in: mesh
out: table
examples: [mesh_resolution_demo]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# mesh_decimate_preserving — 3D `resolution` op

- **データ種**: `mesh` → `table`
- **呼び出し**: `import meshres; meshres.mesh_decimate_preserving(V, F, target_faces, protect_quantile=0.8, max_error=None, samples=4000, seed=0)` (または `ops3d.get("mesh_decimate_preserving")`)

## 使い方

Decimation that keeps the detailed regions and reports what it lost (``table``).

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

[mesh_edge_stats](mesh_edge_stats.md) · [mesh_detail_map](mesh_detail_map.md) · [mesh_split_long_edges](mesh_split_long_edges.md) · [mesh_isotropic_remesh](mesh_isotropic_remesh.md) · [mesh_sample_points](mesh_sample_points.md) · [mesh_lod_chain](mesh_lod_chain.md) · [mesh_select_lod](mesh_select_lod.md) · [mesh_reduction_report](mesh_reduction_report.md)

---
*Provenance: meshres.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
