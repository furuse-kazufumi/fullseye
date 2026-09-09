---
op: fit_spline_curve
dim: 3d
category: curve
in: points
out: points
examples: [bspline_freeform]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# fit_spline_curve — 3D `curve` op

- **データ種**: `points` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.fit_spline_curve(points, smooth=0.0, k=3, n=None)` (実装を直接呼ぶなら `import curve3d; curve3d.fit_spline_curve(points, smooth=0.0, k=3, n=None)`、台帳から引くなら `ops3d.get("fit_spline_curve")`)

## 使い方

順序付き 3D 点列を B スプラインで平滑し再サンプル。→ (M,3)。ノイズのある軌跡/エッジの平滑化。

scipy.interpolate.splprep/splev。smooth=0 は補間、>0 で平滑。n=出力点数(既定=入力数)。

``splprep([x, y, z], s=smooth, k=k)`` でパラメトリック B スプライン(パラメータ u∈[0,1]、
scipy 既定の弦長パラメータ化)を当て、``u = linspace(0, 1, n)`` で ``splev`` 評価した
(n,3) float64 を返す。u 等間隔なので出力点は弧長で厳密に等間隔ではない(弧長等間隔が
要るなら結果を ``resample_uniform`` に通す)。

- ``smooth``: scipy の平滑化条件 s。残差二乗和が s 以下になる最少ノットで当てる。
  0 なら全点を通る補間、大きいほど滑らか(単位は座標の二乗)。
- ``k``: スプライン次数(既定 3)。点数 N が k 以下だと ``ValueError``。
- ``n``: 出力点数。None で入力点数。
- 入力は index 順に並んだ (N,3) を前提とし、形状検証は点数以外に無い。

ノイズのあるエッジ点列や軌跡を平滑してから ``curvature_torsion`` / ``frenet_frame`` に
渡す前段として使う。tck を持ち回りたい場合は ``fit_bspline_curve`` / ``eval_bspline_curve``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [bspline_freeform](../../../../examples_3d/bspline_freeform.py) — `py -3.11 examples_3d/bspline_freeform.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [gaussians_to_voxel](../transform/gaussians_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md)

## 同カテゴリ(`curve`)

[curvature_torsion](curvature_torsion.md) · [frenet_frame](frenet_frame.md) · [arc_length](arc_length.md) · [resample_uniform](resample_uniform.md)

---
*Provenance: curve3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
