---
op: pose_error
dim: 3d
category: metrics
in: pose × pose
out: measurement
examples: [itokawa_self_register]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# pose_error — 3D `metrics` op

- **データ種**: `pose × pose` → `measurement`
- **呼び出し**: `import metrics3d; metrics3d.pose_error(R_est, t_est, R_gt, t_gt)` (または `ops3d.get("pose_error")`)

## 使い方

姿勢誤差 = (回転角[度], 並進ノルム)。登録結果の GT 比較。→ (rot_deg, trans_err)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [itokawa_self_register](../../../../examples_3d/itokawa_self_register.py) — `py -3.11 examples_3d/itokawa_self_register.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`metrics`)

[chamfer_distance](chamfer_distance.md) · [hausdorff_distance](hausdorff_distance.md) · [fscore](fscore.md) · [rmse_correspondence](rmse_correspondence.md) · [normal_consistency](normal_consistency.md) · [voxel_iou](voxel_iou.md)

---
*Provenance: metrics3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
