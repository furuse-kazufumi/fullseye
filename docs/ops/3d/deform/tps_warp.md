---
op: tps_warp
dim: 3d
category: deform
in: deformation × points
out: points
examples: [nonrigid_deform]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# tps_warp — 3D `deform` op

- **データ種**: `deformation × points` → `points`
- **呼び出し**: `import deform3d; deform3d.tps_warp(model, points)` (または `ops3d.get("tps_warp")`)

## 使い方

TPS モデルで点群を変形する。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [nonrigid_deform](../../../../examples_3d/nonrigid_deform.py) — `py -3.11 examples_3d/nonrigid_deform.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [gaussians_to_voxel](../transform/gaussians_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md)

## 同カテゴリ(`deform`)

[tps_fit](tps_fit.md) · [register_nonrigid](register_nonrigid.md) · [register_cpd_rigid](register_cpd_rigid.md)

---
*Provenance: deform3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
