---
op: vol_local_maxima
dim: 3d
category: feature
in: voxel
out: points
examples: [molecule_atom_count, vessel_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# vol_local_maxima — 3D `feature` op

- **データ種**: `voxel` → `points`
- **呼び出し**: `import volops; volops.vol_local_maxima(vol, min_distance, threshold=None)` (または `ops3d.get("vol_local_maxima")`)

## 使い方

3-D local-maxima (peak) detection.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [molecule_atom_count](../../../../examples_3d/molecule_atom_count.py) — `py -3.11 examples_3d/molecule_atom_count.py`
- [vessel_metrology](../../../../examples_3d/vessel_metrology.py) — `py -3.11 examples_3d/vessel_metrology.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md) · [icp_point2plane](../refine/icp_point2plane.md)

## 同カテゴリ(`feature`)

[sobel3d](sobel3d.md) · [hessian3d](hessian3d.md) · [curvature_maps](curvature_maps.md) · [edt_jfa](edt_jfa.md) · [vol_frangi](vol_frangi.md) · [vol_sato](vol_sato.md) · [vol_hessian_blobness](vol_hessian_blobness.md) · [vol_gradient_magnitude](vol_gradient_magnitude.md)

---
*Provenance: volops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
