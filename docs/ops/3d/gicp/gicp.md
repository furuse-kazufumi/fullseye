---
op: gicp
dim: 3d
category: gicp
in: points × points
out: pose
examples: [gicp_register]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# gicp — 3D `gicp` op

- **データ種**: `points × points` → `pose`
- **呼び出し**: `import gicp; gicp.gicp(source, target, max_iter: 'int' = 30, k: 'int' = 20, epsilon: 'float' = 0.001, tol: 'float' = 1e-08, init=None) -> 'dict'` (または `ops3d.get("gicp")`)

## 使い方

Generalized-ICP(共分散重みマハラノビス ICP)で剛体変換 (R,t) を推定する。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gicp_register](../../../../examples_3d/gicp_register.py) — `py -3.11 examples_3d/gicp_register.py`

## 型が繋がる次の op(`pose` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [pose_error](../metrics/pose_error.md) · [reprojection_error](../pose_estimation/reprojection_error.md) · [bundle_adjust](../bundle_adjust/bundle_adjust.md) · [mean_reprojection_error](../bundle_adjust/mean_reprojection_error.md) · [optimize_pose_graph](../pose_graph/optimize_pose_graph.md) · [relative_pose](../pose_graph/relative_pose.md) · [mean_edge_error](../pose_graph/mean_edge_error.md)

## 同カテゴリ(`gicp`)

[estimate_covariances](estimate_covariances.md)

---
*Provenance: gicp.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
