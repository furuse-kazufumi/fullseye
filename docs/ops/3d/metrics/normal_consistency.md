---
op: normal_consistency
dim: 3d
category: metrics
in: points × normals
out: measurement
examples: [metrics_eval]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# normal_consistency — 3D `metrics` op

- **データ種**: `points × normals` → `measurement`
- **呼び出し**: `import metrics3d; metrics3d.normal_consistency(points_a, normals_a, points_b, normals_b)` (または `ops3d.get("normal_consistency")`)

## 使い方

最近傍対応での法線一致度 = mean|cos(na, nb)|(向き無視)。→ [0,1]。1=完全一致。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [metrics_eval](../../../../examples_3d/metrics_eval.py) — `py -3.11 examples_3d/metrics_eval.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`metrics`)

[chamfer_distance](chamfer_distance.md) · [hausdorff_distance](hausdorff_distance.md) · [fscore](fscore.md) · [rmse_correspondence](rmse_correspondence.md) · [voxel_iou](voxel_iou.md) · [pose_error](pose_error.md)

---
*Provenance: metrics3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
