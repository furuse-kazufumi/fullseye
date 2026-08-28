---
op: rmse_inliers
dim: 3d
category: registration_metrics
in: points × points
out: measurement
examples: [reg_eval]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# rmse_inliers — 3D `registration_metrics` op

- **データ種**: `points × points` → `measurement`
- **呼び出し**: `import registration_eval; registration_eval.rmse_inliers(source, target, transform, thresh: 'float')` (または `ops3d.get("rmse_inliers")`)

## 使い方

inlier 対応(残差 < thresh)上の RMSE と inlier 数。→ (rmse, n_inliers)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [reg_eval](../../../../examples_3d/reg_eval.py) — `py -3.11 examples_3d/reg_eval.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`registration_metrics`)

[inlier_ratio](inlier_ratio.md) · [registration_recall](registration_recall.md) · [rotation_translation_error](rotation_translation_error.md)

---
*Provenance: registration_eval.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
