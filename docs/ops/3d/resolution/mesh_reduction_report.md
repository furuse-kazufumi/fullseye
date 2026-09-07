---
op: mesh_reduction_report
dim: 3d
category: resolution
in: mesh × mesh
out: table
examples: [mesh_resolution_demo]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# mesh_reduction_report — 3D `resolution` op

- **データ種**: `mesh × mesh` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.mesh_reduction_report(V, F, V2, F2, samples=4000, seed=0, detail_quantile=0.9)` (実装を直接呼ぶなら `import meshres; meshres.mesh_reduction_report(V, F, V2, F2, samples=4000, seed=0, detail_quantile=0.9)`、台帳から引くなら `ops3d.get("mesh_reduction_report")`)

## 使い方

What a reduction (decimation, remesh, voxelisation) lost, in numbers (``table``).

Samples *samples* area-weighted points of the **original** surface, measures
their distance to the reduced surface (``rms_error``, ``max_error``, and
``p99_error``), and does the same for the subset of original points that
lie in the top ``1 − detail_quantile`` of :func:`mesh_detail_map`'s
``detail`` (``detail_rms_error`` / ``detail_max_error``): the
high-curvature places — a crater rim, a boulder, an outlier ridge — are
exactly where a discovery hides and where a quadric decimation flattens
first. Also ``face_ratio``, ``area_change`` and ``volume_change``
(signed, closed meshes). A reduction whose ``detail_max_error`` is larger
than the feature you are looking for has already lost it.

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

[mesh_edge_stats](mesh_edge_stats.md) · [mesh_detail_map](mesh_detail_map.md) · [mesh_split_long_edges](mesh_split_long_edges.md) · [mesh_isotropic_remesh](mesh_isotropic_remesh.md) · [mesh_sample_points](mesh_sample_points.md) · [mesh_lod_chain](mesh_lod_chain.md) · [mesh_select_lod](mesh_select_lod.md) · [mesh_decimate_preserving](mesh_decimate_preserving.md)

---
*Provenance: meshres.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
