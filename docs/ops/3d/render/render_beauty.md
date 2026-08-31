---
op: render_beauty
dim: 3d
category: render
in: mesh
out: image2d
examples: [render_beauty]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# render_beauty — 3D `render` op

- **データ種**: `mesh` → `image2d`
- **呼び出し**: `import render_beauty; render_beauty.render_beauty(V, F, *, pose=None, intrinsics=None, size: 'int' = 512, ss: 'int' = 2, light: 'Sequence[float]' = (0.3, 0.4, 1.0), albedo: 'Sequence[float]' = (0.8, 0.8, 0.85), material: 'str' = 'plastic', matcap=None, ambient: 'float' = 0.12, ao: 'bool' = True, ground_shadow: 'bool' = True, tonemap: 'str' = 'reinhard', background: 'Sequence[float]' = (0.1, 0.11, 0.13), exposure: 'float' = 1.0, shininess: 'Optional[float]' = None, ao_samples: 'int' = 32, shadow_res: 'int' = 512, penumbra: 'float' = 2.5, shadow_samples: 'int' = 12) -> 'np.ndarray'` (または `ops3d.get("render_beauty")`)

## 使い方

メッシュを全品質層合成で「映える静止 3D」1 枚に描く → RGB ``(size, size, 3)`` float [0,1]。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [render_beauty](../../../../examples_3d/render_beauty.py) — `py -3.11 examples_3d/render_beauty.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](matcap_shade.md) · [antialias](antialias.md)

## 同カテゴリ(`render`)

[project_points](project_points.md) · [render_point_depth](render_point_depth.md) · [render_volume_projection](render_volume_projection.md) · [render_shaded](render_shaded.md) · [ambient_occlusion](ambient_occlusion.md) · [cast_shadow](cast_shadow.md) · [phong_shade](phong_shade.md) · [matcap_shade](matcap_shade.md)

---
*Provenance: render_beauty.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
