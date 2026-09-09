---
op: radius_outlier_removal
dim: 3d
category: preprocess
in: points
out: points
examples: [pcl_geodesic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# radius_outlier_removal — 3D `preprocess` op

- **データ種**: `points` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.radius_outlier_removal(points, radius: 'float', min_neighbors: 'int' = 8)` (実装を直接呼ぶなら `import pcl_filter; pcl_filter.radius_outlier_removal(points, radius: 'float', min_neighbors: 'int' = 8)`、台帳から引くなら `ops3d.get("radius_outlier_removal")`)
- **台帳経由の戻り値**: `fullseye.ledger.radius_outlier_removal(...)` は**宣言 out 型 `points` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.radius_outlier_removal.raw(...)`、または `pcl_filter.radius_outlier_removal` を直接呼ぶ。

## 使い方

半径 radius 内の近傍数が min_neighbors 未満の点を除去する(孤立点除去)。

各点を中心に半径 ``radius`` の球を張り、その中に居る他点の数が ``min_neighbors``
に満たない点を「孤立した粒」として落とす。統計的手法より局所的・直接的で、
センサの実スケールが分かっているときにしきい値を決めやすい。

Parameters
----------
points : array_like, shape (N, 3)
    入力点群。
radius : float
    近傍とみなす球の半径(> 0)。
min_neighbors : int
    残すのに必要な近傍数(自分自身は数えない、既定 8)。

Returns
-------
filtered : ndarray, shape (M, 3)
    生き残った点(元の順序を保持)。
keep_mask : ndarray of bool, shape (N,)
    各入力点を残すか(True=残す)。

Notes
-----
``radius <= 0`` は ValueError。空入力は空を返す(graceful)。

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

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
