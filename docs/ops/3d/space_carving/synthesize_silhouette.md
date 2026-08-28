---
op: synthesize_silhouette
dim: 3d
category: space_carving
in: points
out: image2d
examples: [space_carving]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# synthesize_silhouette — 3D `space_carving` op

- **データ種**: `points` → `image2d`
- **呼び出し**: `import visualhull; visualhull.synthesize_silhouette(points, K, R, t, size: 'Tuple[int, int]', *, fill: 'bool' = True, dilate: 'int' = 1) -> 'np.ndarray'` (または `ops3d.get("synthesize_silhouette")`)

## 使い方

3-D 点群を (K,R,t) カメラへ射影し占有画素 True のシルエット(H,W bool)を返す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [space_carving](../../../../examples_3d/space_carving.py) — `py -3.11 examples_3d/space_carving.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md) · [antialias](../render/antialias.md)

## 同カテゴリ(`space_carving`)

[carve](carve.md) · [visual_hull](visual_hull.md)

---
*Provenance: visualhull.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
