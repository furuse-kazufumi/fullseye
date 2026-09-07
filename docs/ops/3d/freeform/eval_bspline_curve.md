---
op: eval_bspline_curve
dim: 3d
category: freeform
in: bspline_curve
out: points
examples: [bspline_freeform]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# eval_bspline_curve — 3D `freeform` op

- **データ種**: `bspline_curve` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.eval_bspline_curve(tck, n=200)` (実装を直接呼ぶなら `import bspline_surf; bspline_surf.eval_bspline_curve(tck, n=200)`、台帳から引くなら `ops3d.get("eval_bspline_curve")`)

## 使い方

曲線 tck をパラメータ u∈[0,1] 上 n 点で等間隔評価(splev)。

Parameters
----------
tck : tuple
    fit_bspline_curve が返した ``(t, c, k)``。
n : int
    評価点数(既定 200)。2 以上。

Returns
-------
numpy.ndarray, shape (n, D)
    曲線上の点列。D は fit 時の入力次元(3D 入力なら (n, 3))。

補足:
- u は ``linspace(0, 1, n)`` なので **パラメータ等間隔** であって弧長等間隔ではない。点の密度は元の点列の疎密に依存する。弧長で等間隔にしたければ本 op の出力を ``resample_uniform`` に通す。
- 両端点 u=0, u=1 を含む。
- Raises ``ValueError``: tck が曲線モデル ``(t, c, k)`` でない(曲面 tck / 多項式 dict を名指しで拒否)、または n < 2。
- 返り値は float64 の ``(n, D)``。決定論的。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [bspline_freeform](../../../../examples_3d/bspline_freeform.py) — `py -3.11 examples_3d/bspline_freeform.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [gaussians_to_voxel](../transform/gaussians_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md)

## 同カテゴリ(`freeform`)

[fit_bspline_surface](fit_bspline_surface.md) · [eval_bspline_surface](eval_bspline_surface.md) · [surface_residual](surface_residual.md) · [fit_bspline_curve](fit_bspline_curve.md)

---
*Provenance: bspline_surf.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
