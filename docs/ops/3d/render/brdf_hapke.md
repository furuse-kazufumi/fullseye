---
op: brdf_hapke
dim: 3d
category: render
in: normalmap
out: image2d
examples: [itokawa_regolith_hero]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# brdf_hapke — 3D `render` op

- **データ種**: `normalmap` → `image2d`
- **呼び出し**: `import render_shade; render_shade.brdf_hapke(normals, light=(0.0, 0.0, 1.0), view=(0.0, 0.0, 1.0), w: 'float' = 0.42, g: 'float' = -0.35, B0: 'float' = 0.87, h: 'float' = 0.01, roughness_deg: 'float' = 26.0) -> 'np.ndarray'` (または `ops3d.get("brdf_hapke")`)

## 使い方

Hapke 反射則(対向効果 + 多重散乱 + 巨視的粗さ θ̄)で法線マップを陰影付けし I/F ``(H, W)`` を返す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [itokawa_regolith_hero](../../../../examples_3d/itokawa_regolith_hero.py) — `py -3.11 examples_3d/itokawa_regolith_hero.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](matcap_shade.md)

## 同カテゴリ(`render`)

[project_points](project_points.md) · [render_point_depth](render_point_depth.md) · [render_volume_projection](render_volume_projection.md) · [render_shaded](render_shaded.md) · [ambient_occlusion](ambient_occlusion.md) · [cast_shadow](cast_shadow.md) · [phong_shade](phong_shade.md) · [matcap_shade](matcap_shade.md)

---
*Provenance: render_shade.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
