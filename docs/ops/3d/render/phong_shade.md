---
op: phong_shade
dim: 3d
category: render
in: normalmap
out: image2d
examples: [render_beauty, render_shade]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# phong_shade — 3D `render` op

- **データ種**: `normalmap` → `image2d`
- **呼び出し**: `import render_shade; render_shade.phong_shade(normals, view=(0.0, 0.0, 1.0), light=(0.0, 0.0, 1.0), ambient: 'float' = 0.1, diffuse: 'float' = 0.8, specular: 'float' = 0.5, shininess: 'float' = 32.0, clip: 'bool' = True) -> 'np.ndarray'` (または `ops3d.get("phong_shade")`)

## 使い方

Phong 反射モデルで法線マップを陰影付け(環境光 + 拡散 + **鏡面**)。→ ``(H, W)``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [render_beauty](../../../../examples_3d/render_beauty.py) — `py -3.11 examples_3d/render_beauty.py`
- [render_shade](../../../../examples_3d/render_shade.py) — `py -3.11 examples_3d/render_shade.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](matcap_shade.md)

## 同カテゴリ(`render`)

[project_points](project_points.md) · [render_point_depth](render_point_depth.md) · [render_volume_projection](render_volume_projection.md) · [render_shaded](render_shaded.md) · [ambient_occlusion](ambient_occlusion.md) · [cast_shadow](cast_shadow.md) · [matcap_shade](matcap_shade.md) · [supersample_mesh](supersample_mesh.md)

---
*Provenance: render_shade.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
