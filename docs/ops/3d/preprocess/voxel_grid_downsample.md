---
op: voxel_grid_downsample
dim: 3d
category: preprocess
in: points
out: points
examples: [pointcloud_downsampling]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# voxel_grid_downsample — 3D `preprocess` op

- **データ種**: `points` → `points`
- **呼び出し**: `import pcl_filter; pcl_filter.voxel_grid_downsample(points, voxel_size: 'float')` (または `ops3d.get("voxel_grid_downsample")`)

## 使い方

辺 voxel_size の格子で点群を間引き、各セルを重心 1 点に集約する(決定論的)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [pointcloud_downsampling](../../../../examples_3d/pointcloud_downsampling.py) — `py -3.11 examples_3d/pointcloud_downsampling.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md) · [icp_point2plane](../refine/icp_point2plane.md)

## 同カテゴリ(`preprocess`)

[statistical_outlier_removal](statistical_outlier_removal.md) · [radius_outlier_removal](radius_outlier_removal.md) · [mls_smooth](mls_smooth.md) · [volume_downsample](volume_downsample.md)

---
*Provenance: pcl_filter.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
