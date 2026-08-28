---
op: bundle_adjust
dim: 3d
category: bundle_adjust
in: pose × points
out: pose
examples: [bundle_adjust]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# bundle_adjust — 3D `bundle_adjust` op

- **データ種**: `pose × points` → `pose`
- **呼び出し**: `import bundle3d; bundle3d.bundle_adjust(cameras, points, obs_cam, obs_pt, obs_uv, K, fix_first=True, max_iter=200)` (または `ops3d.get("bundle_adjust")`)

## 使い方

再投影誤差最小でカメラ姿勢と 3D 点を同時最適化。→ dict{cameras, points, rmse, cost}。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [bundle_adjust](../../../../examples_3d/bundle_adjust.py) — `py -3.11 examples_3d/bundle_adjust.py`

## 型が繋がる次の op(`pose` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [pose_error](../metrics/pose_error.md) · [reprojection_error](../pose_estimation/reprojection_error.md) · [mean_reprojection_error](mean_reprojection_error.md) · [optimize_pose_graph](../pose_graph/optimize_pose_graph.md) · [relative_pose](../pose_graph/relative_pose.md) · [mean_edge_error](../pose_graph/mean_edge_error.md) · [rotation_translation_error](../registration_metrics/rotation_translation_error.md)

## 同カテゴリ(`bundle_adjust`)

[mean_reprojection_error](mean_reprojection_error.md) · [project](project.md)

---
*Provenance: bundle3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
