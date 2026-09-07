---
op: resample_uniform
dim: 3d
category: curve
in: points
out: points
examples: [bspline_freeform]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# resample_uniform — 3D `curve` op

- **データ種**: `points` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.resample_uniform(curve, n)` (実装を直接呼ぶなら `import curve3d; curve3d.resample_uniform(curve, n)`、台帳から引くなら `ops3d.get("resample_uniform")`)

## 使い方

弧長で等間隔に n 点へ再サンプル(線形補間)。→ (n,3)。

``arc_length`` の累積弧長をパラメータとして ``np.linspace(0, total, n)`` の位置を
取り、x・y・z を独立に ``np.interp`` で線形補間する。出力は float64 の (n,3)。
始点と終点は入力の先頭・末尾に一致し、中間点は折れ線上に乗る(元の点を通るとは限らない)。

- ``n``: 出力点数。1 なら始点 1 点、0 なら空の (0,3)。入力より多くしても情報は増えず
  折れ線を細かく刻むだけ。
- 全長が 1e-12 未満(全点一致)のときは先頭点を n 回複製して返す。
- 出力列数は 3 に固定されており、入力が (N,3) 以外だと列数不足で失敗するか余剰列が
  捨てられる。形状検証は無い。
- 閉曲線は閉じない(終点→始点の区間は補間対象外)。重複点があっても ``np.interp`` は
  通るが、その区間は長さ 0 として扱われる。

``curvature_torsion`` / ``frenet_frame`` は index パラメータの差分なので、間隔が不均一な
点列はこの op で等間隔化してから渡すと数値微分が安定する。滑らかに補間したい場合は
``fit_spline_curve``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [bspline_freeform](../../../../examples_3d/bspline_freeform.py) — `py -3.11 examples_3d/bspline_freeform.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [gaussians_to_voxel](../transform/gaussians_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md)

## 同カテゴリ(`curve`)

[curvature_torsion](curvature_torsion.md) · [frenet_frame](frenet_frame.md) · [arc_length](arc_length.md) · [fit_spline_curve](fit_spline_curve.md)

---
*Provenance: curve3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
