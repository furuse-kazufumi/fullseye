---
op: dlt_pose
dim: 3d
category: pose_estimation
in: points × image2d
out: pose
examples: [pnp_pose_outliers, pose_estimation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# dlt_pose — 3D `pose_estimation` op

- **データ種**: `points × image2d` → `pose`
- **呼び出し**: `import pnp3d; pnp3d.dlt_pose(points_3d, points_2d, K)` (または `ops3d.get("dlt_pose")`)

## 使い方

DLT で 3D-2D 対応からカメラ姿勢を復元(K 既知)。→ (R (3,3), t (3,))。6 点以上必要。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [pnp_pose_outliers](../../../../examples_3d/pnp_pose_outliers.py) — `py -3.11 examples_3d/pnp_pose_outliers.py`
- [pose_estimation](../../../../examples_3d/pose_estimation.py) — `py -3.11 examples_3d/pose_estimation.py`

## 型が繋がる次の op(`pose` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [pose_error](../metrics/pose_error.md) · [reprojection_error](reprojection_error.md) · [bundle_adjust](../bundle_adjust/bundle_adjust.md) · [mean_reprojection_error](../bundle_adjust/mean_reprojection_error.md) · [optimize_pose_graph](../pose_graph/optimize_pose_graph.md) · [relative_pose](../pose_graph/relative_pose.md) · [mean_edge_error](../pose_graph/mean_edge_error.md)

## 同カテゴリ(`pose_estimation`)

[pnp_ransac](pnp_ransac.md) · [reprojection_error](reprojection_error.md)

---
*Provenance: pnp3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
