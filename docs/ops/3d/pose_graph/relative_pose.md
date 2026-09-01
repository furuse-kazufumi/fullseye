---
op: relative_pose
dim: 3d
category: pose_graph
in: pose × pose
out: pose
examples: [pose_graph_slam, sfm_recon]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# relative_pose — 3D `pose_graph` op

- **データ種**: `pose × pose` → `pose`
- **呼び出し**: `import pose_graph; pose_graph.relative_pose(pose_i, pose_j)` (または `ops3d.get("relative_pose")`)

## 使い方

T_i⁻¹ ∘ T_j = i←j の相対姿勢。pose_* = [rvec|t] (6,)。→ (rvec_ij (3,), t_ij (3,))。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [pose_graph_slam](../../../../examples_3d/pose_graph_slam.py) — `py -3.11 examples_3d/pose_graph_slam.py`
- [sfm_recon](../../../../examples_3d/sfm_recon.py) — `py -3.11 examples_3d/sfm_recon.py`

## 型が繋がる次の op(`pose` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [pose_error](../metrics/pose_error.md) · [bundle_adjust](../bundle_adjust/bundle_adjust.md) · [mean_reprojection_error](../bundle_adjust/mean_reprojection_error.md) · [optimize_pose_graph](optimize_pose_graph.md) · [mean_edge_error](mean_edge_error.md) · [rotation_translation_error](../registration_metrics/rotation_translation_error.md)

## 同カテゴリ(`pose_graph`)

[optimize_pose_graph](optimize_pose_graph.md) · [mean_edge_error](mean_edge_error.md)

---
*Provenance: pose_graph.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
