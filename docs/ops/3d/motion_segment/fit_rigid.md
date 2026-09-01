---
op: fit_rigid
dim: 3d
category: motion_segment
in: points × points
out: pose
examples: [motion_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# fit_rigid — 3D `motion_segment` op

- **データ種**: `points × points` → `pose`
- **呼び出し**: `import motion_seg3d; motion_seg3d.fit_rigid(pts_from, pts_to)` (または `ops3d.get("fit_rigid")`)

## 使い方

対応点から閉形式 Kabsch で剛体変換 (R, t) を推定する(pts_from[i] -> pts_to[i])。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [motion_scene](../../../../examples_3d/motion_scene.py) — `py -3.11 examples_3d/motion_scene.py`

## 型が繋がる次の op(`pose` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [pose_error](../metrics/pose_error.md) · [bundle_adjust](../bundle_adjust/bundle_adjust.md) · [mean_reprojection_error](../bundle_adjust/mean_reprojection_error.md) · [optimize_pose_graph](../pose_graph/optimize_pose_graph.md) · [relative_pose](../pose_graph/relative_pose.md) · [mean_edge_error](../pose_graph/mean_edge_error.md) · [rotation_translation_error](../registration_metrics/rotation_translation_error.md)

## 同カテゴリ(`motion_segment`)

[segment_rigid_motions](segment_rigid_motions.md) · [estimate_flow](estimate_flow.md)

---
*Provenance: motion_seg3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
