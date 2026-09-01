---
op: eval_bspline_surface
dim: 3d
category: freeform
in: bspline_surface × image2d × image2d
out: image2d
examples: [bspline_freeform]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# eval_bspline_surface — 3D `freeform` op

- **データ種**: `bspline_surface × image2d × image2d` → `image2d`
- **呼び出し**: `import bspline_surf; bspline_surf.eval_bspline_surface(tck, x, y, grid=False)` (または `ops3d.get("eval_bspline_surface")`)

## 使い方

フィット済み曲面 tck を評価(bisplev)。散布点(既定)または格子の 2 モード。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [bspline_freeform](../../../../examples_3d/bspline_freeform.py) — `py -3.11 examples_3d/bspline_freeform.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md)

## 同カテゴリ(`freeform`)

[fit_bspline_surface](fit_bspline_surface.md) · [surface_residual](surface_residual.md) · [fit_bspline_curve](fit_bspline_curve.md) · [eval_bspline_curve](eval_bspline_curve.md)

---
*Provenance: bspline_surf.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
