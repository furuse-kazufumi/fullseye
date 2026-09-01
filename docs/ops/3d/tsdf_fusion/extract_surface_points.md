---
op: extract_surface_points
dim: 3d
category: tsdf_fusion
in: sdf
out: points
examples: [transforms_repr, tsdf_fusion_demo]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# extract_surface_points — 3D `tsdf_fusion` op

- **データ種**: `sdf` → `points`
- **呼び出し**: `import tsdf_fusion; tsdf_fusion.extract_surface_points(tsdf: 'np.ndarray', weight: 'np.ndarray', bounds: 'Bounds', res: 'int') -> 'np.ndarray'` (または `ops3d.get("extract_surface_points")`)

## 使い方

TSDF ゼロ交差から表面点 (M,3) を抽出(marching cubes 不要、線形補間)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [transforms_repr](../../../../examples_3d/transforms_repr.py) — `py -3.11 examples_3d/transforms_repr.py`
- [tsdf_fusion_demo](../../../../examples_3d/tsdf_fusion_demo.py) — `py -3.11 examples_3d/tsdf_fusion_demo.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [gaussians_to_voxel](../transform/gaussians_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md)

## 同カテゴリ(`tsdf_fusion`)

[fuse](fuse.md) · [integrate](integrate.md)

---
*Provenance: tsdf_fusion.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
