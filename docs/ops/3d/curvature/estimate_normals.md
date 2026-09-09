---
op: estimate_normals
dim: 3d
category: curvature
in: points
out: normals
examples: [cylinder_axis_metrology, feature_register, oriented_normals]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# estimate_normals — 3D `curvature` op

- **データ種**: `points` → `normals`
- **呼び出し**: `import fullseye as fs; fs.ledger.estimate_normals(points, k=25)` (実装を直接呼ぶなら `import curvature3d; curvature3d.estimate_normals(points, k=25)`、台帳から引くなら `ops3d.get("estimate_normals")`)

## 使い方

外向き(近傍重心から離れる)に統一した点群法線。→ (N,3)。

手順(各点、Python ループ): ``cKDTree`` で自身を含む k+1 近傍(k は N-1 に切り詰め)を取り、クエリ点を原点にした近傍座標の散布行列 ``local.T @ local`` の最小固有ベクトルを法線にする(単位長)。向きは「近傍重心との内積が正なら反転」= 近傍重心から離れる側に揃える。

- 近傍が 5 点未満の点は固定値 ``(0, 0, 1)`` を返す(推定していない)。
- 向き付けは局所ヒューリスティクスで、閉じた凸形状なら外向きだが、開いた面・薄板・凹部では隣接点どうしで向きが食い違い得る(大域一貫性は保証しない)。大域的に揃えるには ``orient_normals`` に通すか、最初から ``estimate_oriented_normals`` を使う。organized 深度画像なら ``normals_from_depth`` が視点向きで速い。
- 返り値は float64 (N,3)。``k`` 既定 25。決定論的。
- 内部は ``principal_curvatures`` と同じ計算を通る(法線推定にも二次曲面フィットまで走る)ので、点数が多いと遅い。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blas_threads_and_memory](../../math/guides/blas_threads_and_memory.md) — 行列分解が遅い理由の知識 — BLAS スレッド・キャッシュ・メモリ配置

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [cylinder_axis_metrology](../../../../examples_3d/cylinder_axis_metrology.py) — `py -3.11 examples_3d/cylinder_axis_metrology.py`
- [feature_register](../../../../examples_3d/feature_register.py) — `py -3.11 examples_3d/feature_register.py`
- [oriented_normals](../../../../examples_3d/oriented_normals.py) — `py -3.11 examples_3d/oriented_normals.py`

## 型が繋がる次の op(`normals` を入力に取れる)

[icp_point2plane](../refine/icp_point2plane.md) · [compute_fpfh](../feature_register/compute_fpfh.md) · [shot_descriptor](../feature_register/shot_descriptor.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [reflect](../optics/reflect.md) · [refract](../optics/refract.md) · [normal_consistency](../metrics/normal_consistency.md) · [ransac_cylinder](../robust_fit/ransac_cylinder.md)

## 同カテゴリ(`curvature`)

[principal_curvatures](principal_curvatures.md) · [mean_curvature](mean_curvature.md) · [gaussian_curvature](gaussian_curvature.md) · [shape_index](shape_index.md)

---
*Provenance: curvature3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
