---
op: cast_shadow
dim: 3d
category: render
in: mesh × vector
out: image2d
examples: [render_beauty, render_shadow]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# cast_shadow — 3D `render` op

- **データ種**: `mesh × vector` → `image2d`
- **呼び出し**: `import render_shadow; render_shadow.cast_shadow(V, F, light, *, pose=None, intrinsics=None, width: 'int' = 256, height: 'int' = 256, directional: 'bool' = True, penumbra: 'float' = 0.0, samples: 'int' = 16, shadow_res: 'int' = 512, bias=None) -> 'np.ndarray'` (または `ops3d.get("cast_shadow")`)

## 使い方

メッシュのキャスト影 / ソフトシャドウを計算し、可視性マップ (H,W) ∈ [0,1] を返す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [render_beauty](../../../../examples_3d/render_beauty.py) — `py -3.11 examples_3d/render_beauty.py`
- [render_shadow](../../../../examples_3d/render_shadow.py) — `py -3.11 examples_3d/render_shadow.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](matcap_shade.md) · [antialias](antialias.md)

## 同カテゴリ(`render`)

[project_points](project_points.md) · [render_point_depth](render_point_depth.md) · [render_volume_projection](render_volume_projection.md) · [render_shaded](render_shaded.md) · [ambient_occlusion](ambient_occlusion.md) · [phong_shade](phong_shade.md) · [matcap_shade](matcap_shade.md) · [supersample_mesh](supersample_mesh.md)

---
*Provenance: render_shadow.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
