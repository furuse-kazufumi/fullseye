---
op: rotation_translation_error
dim: 3d
category: registration_metrics
in: pose × pose
out: measurement
examples: [reg_eval]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# rotation_translation_error — 3D `registration_metrics` op

- **データ種**: `pose × pose` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.rotation_translation_error(gt, est)` (実装を直接呼ぶなら `import registration_eval; registration_eval.rotation_translation_error(gt, est)`、台帳から引くなら `ops3d.get("rotation_translation_error")`)

## 使い方

2 つの 4×4 変換間の相対回転誤差(測地角[度], RRE)と相対並進誤差(RTE)。

RRE = 角度(gt_R^T · est_R) = arccos((tr−1)/2) を度で。任意軸まわりの角 θ の
回転差なら RRE=θ。RTE = ‖gt_t − est_t‖。→ (rre_deg, rte)。
非 4×4 は ValueError(fail-closed)。

- ``gt`` / ``est``: 4×4 同次変換(左上 3×3 が回転、右列が並進)。非有限を含むと ``ValueError``。
- ``rre_deg`` は [0, 180] の度(cos は [-1,1] にクリップしてから arccos)。``rte`` は並進列の差の
  ノルムで座標の単位。並進列は回転の原点に依存するので、同じ姿勢誤差でも原点が物体から遠い
  ほど RTE は大きく出る(比較は同じフレーム規約の変換どうしで行う)。
- 回転行列が直交でなくても検査しないので、``gicp`` 等の出力 (R,t) を同モジュールの
  ``make_transform`` で組んだ正しい変換を渡す。``inlier_ratio`` / ``registration_recall`` が点群上の残差で測るのに対し、
  こちらは変換パラメータそのものの差を測る。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [reg_eval](../../../../examples_3d/reg_eval.py) — `py -3.11 examples_3d/reg_eval.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`registration_metrics`)

[inlier_ratio](inlier_ratio.md) · [rmse_inliers](rmse_inliers.md) · [registration_recall](registration_recall.md)

---
*Provenance: registration_eval.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
