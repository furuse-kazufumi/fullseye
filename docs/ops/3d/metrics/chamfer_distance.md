---
op: chamfer_distance
dim: 3d
category: metrics
in: points × points
out: measurement
examples: [itokawa_pose_canonical, itokawa_shape_match, mesh_lod_download, poisson_surface_recon]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# chamfer_distance — 3D `metrics` op

- **データ種**: `points × points` → `measurement`
- **呼び出し**: `import metrics3d; metrics3d.chamfer_distance(a, b, squared=False)` (または `ops3d.get("chamfer_distance")`)

## 使い方

対称 Chamfer 距離 = 0.5*(mean_a min_b + mean_b min_a)。→ scalar。小さいほど一致。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [itokawa_pose_canonical](../../../../examples_3d/itokawa_pose_canonical.py) — `py -3.11 examples_3d/itokawa_pose_canonical.py`
- [itokawa_shape_match](../../../../examples_3d/itokawa_shape_match.py) — `py -3.11 examples_3d/itokawa_shape_match.py`
- [mesh_lod_download](../../../../examples_3d/mesh_lod_download.py) — `py -3.11 examples_3d/mesh_lod_download.py`
- [poisson_surface_recon](../../../../examples_3d/poisson_surface_recon.py) — `py -3.11 examples_3d/poisson_surface_recon.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`metrics`)

[hausdorff_distance](hausdorff_distance.md) · [fscore](fscore.md) · [rmse_correspondence](rmse_correspondence.md) · [normal_consistency](normal_consistency.md) · [voxel_iou](voxel_iou.md) · [pose_error](pose_error.md)

---
*Provenance: metrics3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
