---
op: rmse_inliers
dim: 3d
category: registration_metrics
in: points × points
out: measurement
examples: [reg_eval]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# rmse_inliers — 3D `registration_metrics` op

- **データ種**: `points × points` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.rmse_inliers(source, target, transform, thresh: 'float')` (実装を直接呼ぶなら `import registration_eval; registration_eval.rmse_inliers(source, target, transform, thresh: 'float')`、台帳から引くなら `ops3d.get("rmse_inliers")`)
- **台帳経由の戻り値**: `fullseye.ledger.rmse_inliers(...)` は**宣言 out 型 `measurement` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.rmse_inliers.raw(...)`、または `registration_eval.rmse_inliers` を直接呼ぶ。
  - 本体の返り: `(rmse, n_inliers) → rmse`

## 使い方

inlier 対応(残差 < thresh)上の RMSE と inlier 数。→ (rmse, n_inliers)。

``source[i]↔target[i]`` の index 対応が前提(:func:`inlier_ratio` と同じ)。
inlier が 0 個なら RMSE は未定義 → ``(nan, 0)`` を返す(honest; 捏造しない)。
形状不一致・非 (N,3) は ValueError(fail-closed)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [reg_eval](../../../../examples_3d/reg_eval.py) — `py -3.11 examples_3d/reg_eval.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`registration_metrics`)

[inlier_ratio](inlier_ratio.md) · [registration_recall](registration_recall.md) · [rotation_translation_error](rotation_translation_error.md)

---
*Provenance: registration_eval.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
