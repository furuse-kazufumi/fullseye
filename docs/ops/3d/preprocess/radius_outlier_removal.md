---
op: radius_outlier_removal
dim: 3d
category: preprocess
in: points
out: points
examples: [pcl_geodesic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# radius_outlier_removal — 3D `preprocess` op

- **データ種**: `points` → `points`
- **呼び出し**: `import pcl_filter; pcl_filter.radius_outlier_removal(points, radius: 'float', min_neighbors: 'int' = 8)` (または `ops3d.get("radius_outlier_removal")`)

## 使い方

半径 radius 内の近傍数が min_neighbors 未満の点を除去する(孤立点除去)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [pcl_geodesic](../../../../examples_3d/pcl_geodesic.py) — `py -3.11 examples_3d/pcl_geodesic.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [gaussians_to_voxel](../transform/gaussians_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md)

## 同カテゴリ(`preprocess`)

[statistical_outlier_removal](statistical_outlier_removal.md) · [voxel_grid_downsample](voxel_grid_downsample.md) · [mls_smooth](mls_smooth.md) · [volume_downsample](volume_downsample.md)

---
*Provenance: pcl_filter.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
