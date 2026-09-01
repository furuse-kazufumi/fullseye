---
op: eval_poly_surface
dim: 3d
category: surface_fit
in: poly_surface × image2d × image2d
out: image2d
examples: [contours_to_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# eval_poly_surface — 3D `surface_fit` op

- **データ種**: `poly_surface × image2d × image2d` → `image2d`
- **呼び出し**: `import match3d; match3d.eval_poly_surface(model, x, y)` (または `ops3d.get("eval_poly_surface")`)

## 使い方

model を (x,y) で評価 → z(x の shape で返す)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [contours_to_terrain](../../../../examples_3d/contours_to_terrain.py) — `py -3.11 examples_3d/contours_to_terrain.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](fit_poly_surface.md) · [surface_form_error](surface_form_error.md) · [background_flatten](background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md) · [antialias](../render/antialias.md)

## 同カテゴリ(`surface_fit`)

[fit_poly_surface](fit_poly_surface.md) · [surface_form_error](surface_form_error.md) · [background_flatten](background_flatten.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
