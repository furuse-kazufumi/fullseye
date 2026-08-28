---
op: sample_surface
dim: 3d
category: superquadric
in: primitive
out: points
examples: [mesh_lod_download, superquadric_fit]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# sample_surface — 3D `superquadric` op

- **データ種**: `primitive` → `points`
- **呼び出し**: `import superquadric; superquadric.sample_surface(a, eps, n_u: 'int' = 40, n_v: 'int' = 40, R=None, t=None) -> 'np.ndarray'` (または `ops3d.get("sample_surface")`)

## 使い方

スーパー2次曲面の表面点を (eta, omega) パラメトリックにサンプリング。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [mesh_lod_download](../../../../examples_3d/mesh_lod_download.py) — `py -3.11 examples_3d/mesh_lod_download.py`
- [superquadric_fit](../../../../examples_3d/superquadric_fit.py) — `py -3.11 examples_3d/superquadric_fit.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md) · [icp_point2plane](../refine/icp_point2plane.md)

## 同カテゴリ(`superquadric`)

[fit_superquadric](fit_superquadric.md) · [inside_outside](inside_outside.md) · [superquadric_residual](superquadric_residual.md)

---
*Provenance: superquadric.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
