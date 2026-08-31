---
op: eval_bspline_curve
dim: 3d
category: freeform
in: surface
out: points
examples: [bspline_freeform]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# eval_bspline_curve — 3D `freeform` op

- **データ種**: `surface` → `points`
- **呼び出し**: `import bspline_surf; bspline_surf.eval_bspline_curve(tck, n=200)` (または `ops3d.get("eval_bspline_curve")`)

## 使い方

曲線 tck をパラメータ u∈[0,1] 上 n 点で等間隔評価(splev)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [bspline_freeform](../../../../examples_3d/bspline_freeform.py) — `py -3.11 examples_3d/bspline_freeform.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md) · [icp_point2plane](../refine/icp_point2plane.md)

## 同カテゴリ(`freeform`)

[fit_bspline_surface](fit_bspline_surface.md) · [eval_bspline_surface](eval_bspline_surface.md) · [surface_residual](surface_residual.md) · [fit_bspline_curve](fit_bspline_curve.md)

---
*Provenance: bspline_surf.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
