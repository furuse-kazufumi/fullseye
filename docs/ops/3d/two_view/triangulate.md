---
op: triangulate
dim: 3d
category: two_view
in: image2d × image2d
out: points
examples: [sfm_recon]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# triangulate — 3D `two_view` op

- **データ種**: `image2d × image2d` → `points`
- **呼び出し**: `import twoview; twoview.triangulate(pts1, pts2, P1, P2)` (または `ops3d.get("triangulate")`)

## 使い方

DLT 三角測量: 2 視点の対応点 + 射影行列 → 3D 点。→ (N,3)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sfm_recon](../../../../examples_3d/sfm_recon.py) — `py -3.11 examples_3d/sfm_recon.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [gaussians_to_voxel](../transform/gaussians_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md)

## 同カテゴリ(`two_view`)

[fundamental_8point](fundamental_8point.md) · [essential_8point](essential_8point.md) · [recover_pose](recover_pose.md) · [sampson_distance](sampson_distance.md)

---
*Provenance: twoview.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
