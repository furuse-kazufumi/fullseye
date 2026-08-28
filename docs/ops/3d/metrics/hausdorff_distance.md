---
op: hausdorff_distance
dim: 3d
category: metrics
in: points × points
out: measurement
examples: [mesh_lod_download, pointcloud_downsampling, poisson_surface_recon]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# hausdorff_distance — 3D `metrics` op

- **データ種**: `points × points` → `measurement`
- **呼び出し**: `import metrics3d; metrics3d.hausdorff_distance(a, b)` (または `ops3d.get("hausdorff_distance")`)

## 使い方

対称 Hausdorff 距離 = max(max_a min_b, max_b min_a)。→ scalar。最悪ケースの乖離。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [mesh_lod_download](../../../../examples_3d/mesh_lod_download.py) — `py -3.11 examples_3d/mesh_lod_download.py`
- [pointcloud_downsampling](../../../../examples_3d/pointcloud_downsampling.py) — `py -3.11 examples_3d/pointcloud_downsampling.py`
- [poisson_surface_recon](../../../../examples_3d/poisson_surface_recon.py) — `py -3.11 examples_3d/poisson_surface_recon.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`metrics`)

[chamfer_distance](chamfer_distance.md) · [fscore](fscore.md) · [rmse_correspondence](rmse_correspondence.md) · [normal_consistency](normal_consistency.md) · [voxel_iou](voxel_iou.md) · [pose_error](pose_error.md)

---
*Provenance: metrics3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
