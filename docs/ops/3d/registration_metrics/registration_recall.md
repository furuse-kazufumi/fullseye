---
op: registration_recall
dim: 3d
category: registration_metrics
in: points × points
out: measurement
examples: [reg_eval]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# registration_recall — 3D `registration_metrics` op

- **データ種**: `points × points` → `measurement`
- **呼び出し**: `import registration_eval; registration_eval.registration_recall(source, target, gt_transform, est_transform, thresh: 'float', *, corr_thresh: 'float | None' = None) -> 'float'` (または `ops3d.get("registration_recall")`)

## 使い方

3DMatch 流の per-pair 登録成否 = 1.0(成功)/ 0.0(失敗)。

GT 変換 ``gt_transform`` で source を target フレームへ写し、target 側の最近傍
(距離 < ``corr_thresh``、既定は thresh)を GT 対応(=重なり)として張る。その
対応を **推定変換** ``est_transform`` で写した RMSE が ``thresh`` を切れば成功。

``source``/``target`` は index 対応でなくてよい(対応は GT から張るため target の
並びに依存しない)。GT 重なりが 1 点も無ければ成否は未定義 → ``nan``(honest)。
データセット全体の Registration Recall はこの per-pair 指標(重なり有ペア上)の平均。
形状不正は ValueError(fail-closed)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [reg_eval](../../../../examples_3d/reg_eval.py) — `py -3.11 examples_3d/reg_eval.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`registration_metrics`)

[inlier_ratio](inlier_ratio.md) · [rmse_inliers](rmse_inliers.md) · [rotation_translation_error](rotation_translation_error.md)

---
*Provenance: registration_eval.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
