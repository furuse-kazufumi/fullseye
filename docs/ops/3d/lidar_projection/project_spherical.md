---
op: project_spherical
dim: 3d
category: lidar_projection
in: points
out: image2d
examples: [lidar_projection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# project_spherical — 3D `lidar_projection` op

- **データ種**: `points` → `image2d`
- **呼び出し**: `import spherical_proj; spherical_proj.project_spherical(points, h_res: 'int' = 1024, v_res: 'int' = 64, v_fov=(-25.0, 15.0)) -> 'np.ndarray'` (または `ops3d.get("project_spherical")`)

## 使い方

回転式 LiDAR の球面レンジ画像へ投影 (v_res, h_res)。空セル=0, 近い点優先(最小 range)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lidar_projection](../../../../examples_3d/lidar_projection.py) — `py -3.11 examples_3d/lidar_projection.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md)

## 同カテゴリ(`lidar_projection`)

[unproject_spherical](unproject_spherical.md) · [project_cylindrical](project_cylindrical.md)

---
*Provenance: spherical_proj.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
