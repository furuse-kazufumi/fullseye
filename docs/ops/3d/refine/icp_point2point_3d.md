---
op: icp_point2point_3d
dim: 3d
category: refine
in: points × points
out: pose
examples: [gicp_register, itokawa_self_register, itokawa_shape_match, partial_overlap_icp]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# icp_point2point_3d — 3D `refine` op

- **データ種**: `points × points` → `pose`
- **呼び出し**: `import match3d; match3d.icp_point2point_3d(src, dst, iters=50, init_R=None, init_t=None, tol=1e-06, max_corr_dist=None, trim_ratio=None, device='cpu')` (または `ops3d.get("icp_point2point_3d")`)

## 使い方

点群を point-to-point ICP(Kabsch/SVD)で精緻化する。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gicp_register](../../../../examples_3d/gicp_register.py) — `py -3.11 examples_3d/gicp_register.py`
- [itokawa_self_register](../../../../examples_3d/itokawa_self_register.py) — `py -3.11 examples_3d/itokawa_self_register.py`
- [itokawa_shape_match](../../../../examples_3d/itokawa_shape_match.py) — `py -3.11 examples_3d/itokawa_shape_match.py`
- [partial_overlap_icp](../../../../examples_3d/partial_overlap_icp.py) — `py -3.11 examples_3d/partial_overlap_icp.py`

## 型が繋がる次の op(`pose` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [pose_error](../metrics/pose_error.md) · [bundle_adjust](../bundle_adjust/bundle_adjust.md) · [mean_reprojection_error](../bundle_adjust/mean_reprojection_error.md) · [optimize_pose_graph](../pose_graph/optimize_pose_graph.md) · [relative_pose](../pose_graph/relative_pose.md) · [mean_edge_error](../pose_graph/mean_edge_error.md) · [rotation_translation_error](../registration_metrics/rotation_translation_error.md)

## 同カテゴリ(`refine`)

[refine_peak_newton](refine_peak_newton.md) · [refine_translation_lk](refine_translation_lk.md) · [refine_lm](refine_lm.md) · [refine_rotation_z](refine_rotation_z.md) · [icp_point2plane](icp_point2plane.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
