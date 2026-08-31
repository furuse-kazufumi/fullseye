---
op: rigid_flow
dim: 3d
category: scene_flow3d
in: points × points
out: pose
examples: [scene_flow_rigid]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# rigid_flow — 3D `scene_flow3d` op

- **データ種**: `points × points` → `pose`
- **呼び出し**: `import scene_flow3d; scene_flow3d.rigid_flow(pts0, pts1, max_iter: 'int' = 20) -> 'dict'` (または `ops3d.get("rigid_flow")`)

## 使い方

pts0 -> pts1 を説明する単一剛体運動を最近傍対応 + Kabsch(ICP 風)で推定。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [scene_flow_rigid](../../../../examples_3d/scene_flow_rigid.py) — `py -3.11 examples_3d/scene_flow_rigid.py`

## 型が繋がる次の op(`pose` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [pose_error](../metrics/pose_error.md) · [reprojection_error](../pose_estimation/reprojection_error.md) · [bundle_adjust](../bundle_adjust/bundle_adjust.md) · [mean_reprojection_error](../bundle_adjust/mean_reprojection_error.md) · [optimize_pose_graph](../pose_graph/optimize_pose_graph.md) · [relative_pose](../pose_graph/relative_pose.md) · [mean_edge_error](../pose_graph/mean_edge_error.md)

## 同カテゴリ(`scene_flow3d`)

[nearest_neighbor_flow](nearest_neighbor_flow.md) · [smooth_flow](smooth_flow.md)

---
*Provenance: scene_flow3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
