---
op: fit_poly_surface
dim: 3d
category: surface_fit
in: image2d
out: surface
examples: [contours_to_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# fit_poly_surface — 3D `surface_fit` op

- **データ種**: `image2d` → `surface`
- **呼び出し**: `import match3d; match3d.fit_poly_surface(x, y, z, degree=2)` (または `ops3d.get("fit_poly_surface")`)

## 使い方

散布 (x,y,z) → z=f(x,y) 多項式最小二乗。返り値 model(coef/powers/degree/rms/pv)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [contours_to_terrain](../../../../examples_3d/contours_to_terrain.py) — `py -3.11 examples_3d/contours_to_terrain.py`

## 型が繋がる次の op(`surface` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [eval_poly_surface](eval_poly_surface.md) · [eval_bspline_surface](../freeform/eval_bspline_surface.md) · [surface_residual](../freeform/surface_residual.md) · [eval_bspline_curve](../freeform/eval_bspline_curve.md)

## 同カテゴリ(`surface_fit`)

[eval_poly_surface](eval_poly_surface.md) · [surface_form_error](surface_form_error.md) · [background_flatten](background_flatten.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
