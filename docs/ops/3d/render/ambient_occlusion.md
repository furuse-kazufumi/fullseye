---
op: ambient_occlusion
dim: 3d
category: render
in: mesh
out: image2d
examples: [render_ao]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# ambient_occlusion — 3D `render` op

- **データ種**: `mesh` → `image2d`
- **呼び出し**: `import render_ao; render_ao.ambient_occlusion(V, F, pose=None, intrinsics=None, width: 'int' = 256, height: 'int' = 256, n_dirs: 'int' = 64, max_dist: 'float | None' = None, k: 'int' = 3, background: 'float' = 1.0) -> 'np.ndarray'` (または `ops3d.get("ambient_occlusion")`)

## 使い方

メッシュを AO マップ画像 ``(H, W)`` [0,1] にレンダリングして返す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [render_ao](../../../../examples_3d/render_ao.py) — `py -3.11 examples_3d/render_ao.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](matcap_shade.md) · [antialias](antialias.md)

## 同カテゴリ(`render`)

[project_points](project_points.md) · [render_point_depth](render_point_depth.md) · [render_volume_projection](render_volume_projection.md) · [render_shaded](render_shaded.md) · [cast_shadow](cast_shadow.md) · [phong_shade](phong_shade.md) · [matcap_shade](matcap_shade.md) · [supersample_mesh](supersample_mesh.md)

---
*Provenance: render_ao.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
