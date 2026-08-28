---
op: register_shot
dim: 3d
category: feature_register
in: points × points
out: pose
examples: [feature_register]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# register_shot — 3D `feature_register` op

- **データ種**: `points × points` → `pose`
- **呼び出し**: `import feat_shot; feat_shot.register_shot(src, dst, radius=None, normal_k=16, ratio=0.9, ransac_iters=2000, inlier_thr=None, refine_icp=True, max_kp=400, device='cpu', seed=0)` (または `ops3d.get("register_shot")`)

## 使い方

SHOT 記述子による疎特徴マッチング + RANSAC 剛体姿勢推定(全パイプライン)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [feature_register](../../../../examples_3d/feature_register.py) — `py -3.11 examples_3d/feature_register.py`

## 型が繋がる次の op(`pose` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [pose_error](../metrics/pose_error.md) · [reprojection_error](../pose_estimation/reprojection_error.md) · [bundle_adjust](../bundle_adjust/bundle_adjust.md) · [mean_reprojection_error](../bundle_adjust/mean_reprojection_error.md) · [optimize_pose_graph](../pose_graph/optimize_pose_graph.md) · [relative_pose](../pose_graph/relative_pose.md) · [mean_edge_error](../pose_graph/mean_edge_error.md)

## 同カテゴリ(`feature_register`)

[harris3d_keypoints](harris3d_keypoints.md) · [iss_keypoints](iss_keypoints.md) · [compute_fpfh](compute_fpfh.md) · [shot_descriptor](shot_descriptor.md) · [register_spin](register_spin.md) · [register_fpfh](register_fpfh.md)

---
*Provenance: feat_shot.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
