---
op: pc_density_equalize
dim: 3d
category: resolution
in: points
out: points
examples: [mesh_resolution_demo]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# pc_density_equalize — 3D `resolution` op

- **データ種**: `points` → `points`
- **呼び出し**: `import meshres; meshres.pc_density_equalize(points, spacing, k=8, seed=0)` (または `ops3d.get("pc_density_equalize")`)

## 使い方

Fill the sparse regions, then thin the dense ones: uniform spacing (``points``).

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [mesh_resolution_demo](../../../../examples_3d/mesh_resolution_demo.py) — `py -3.11 examples_3d/mesh_resolution_demo.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [gaussians_to_voxel](../transform/gaussians_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md)

## 同カテゴリ(`resolution`)

[mesh_edge_stats](mesh_edge_stats.md) · [mesh_detail_map](mesh_detail_map.md) · [mesh_split_long_edges](mesh_split_long_edges.md) · [mesh_isotropic_remesh](mesh_isotropic_remesh.md) · [mesh_sample_points](mesh_sample_points.md) · [mesh_lod_chain](mesh_lod_chain.md) · [mesh_select_lod](mesh_select_lod.md) · [mesh_reduction_report](mesh_reduction_report.md)

---
*Provenance: meshres.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
