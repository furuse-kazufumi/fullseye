---
op: jitter
dim: 3d
category: augment
in: points
out: points
examples: [augment_pointcloud]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# jitter — 3D `augment` op

- **データ種**: `points` → `points`
- **呼び出し**: `import pcl_augment; pcl_augment.jitter(points, sigma: 'float', clip: 'Optional[float]' = None, seed: 'int' = 0) -> 'np.ndarray'` (または `ops3d.get("jitter")`)

## 使い方

各点に等方ガウスノイズ ``N(0, sigma)`` を付加(センサ位置ノイズの模倣)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [augment_pointcloud](../../../../examples_3d/augment_pointcloud.py) — `py -3.11 examples_3d/augment_pointcloud.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [gaussians_to_voxel](../transform/gaussians_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md)

## 同カテゴリ(`augment`)

[random_rotation](random_rotation.md) · [random_scale](random_scale.md) · [random_dropout](random_dropout.md) · [elastic_deform](elastic_deform.md) · [cutout](cutout.md)

---
*Provenance: pcl_augment.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
