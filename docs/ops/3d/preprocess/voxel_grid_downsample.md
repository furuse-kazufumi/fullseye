---
op: voxel_grid_downsample
dim: 3d
category: preprocess
in: points
out: points
examples: [pointcloud_downsampling]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# voxel_grid_downsample — 3D `preprocess` op

- **データ種**: `points` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.voxel_grid_downsample(points, voxel_size: 'float')` (実装を直接呼ぶなら `import pcl_filter; pcl_filter.voxel_grid_downsample(points, voxel_size: 'float')`、台帳から引くなら `ops3d.get("voxel_grid_downsample")`)

## 使い方

辺 voxel_size の格子で点群を間引き、各セルを重心 1 点に集約する(決定論的)。

空間を一辺 ``voxel_size`` の立方体セルに区切り、同じセルに落ちた点をその重心
1 点で代表させる。密度ムラを均し、下流(ICP・特徴量)の計算量を点数で抑える標準手法。
出力順はボクセル座標の辞書順で固定(同じ入力なら常に同じ出力=決定論的)。

Parameters
----------
points : array_like, shape (N, 3)
    入力点群。
voxel_size : float
    セルの一辺(> 0)。大きいほど強く間引く。

Returns
-------
ndarray, shape (M, 3)
    各占有セルの重心(M <= N)。すべて入力の軸並行 bounding box 内に収まる。

Notes
-----
``voxel_size <= 0`` は ValueError。空入力は空 (0,3) を返す(graceful)。
重心はセル内の点の平均なので、必ず入力点の凸包(ゆえに bbox)内に入る。

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [pointcloud_downsampling](../../../../examples_3d/pointcloud_downsampling.py) — `py -3.11 examples_3d/pointcloud_downsampling.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [gaussians_to_voxel](../transform/gaussians_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md)

## 同カテゴリ(`preprocess`)

[statistical_outlier_removal](statistical_outlier_removal.md) · [radius_outlier_removal](radius_outlier_removal.md) · [mls_smooth](mls_smooth.md) · [volume_downsample](volume_downsample.md)

---
*Provenance: pcl_filter.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
