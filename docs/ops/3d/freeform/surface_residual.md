---
op: surface_residual
dim: 3d
category: freeform
in: points × surface
out: measurement
examples: [bspline_freeform]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# surface_residual — 3D `freeform` op

- **データ種**: `points × surface` → `measurement`
- **呼び出し**: `import bspline_surf; bspline_surf.surface_residual(x, y, z, tck)` (または `ops3d.get("surface_residual")`)

## 使い方

散布データと曲面 tck の残差統計を返す(形状誤差=フィットからの逸脱)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [bspline_freeform](../../../../examples_3d/bspline_freeform.py) — `py -3.11 examples_3d/bspline_freeform.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`freeform`)

[fit_bspline_surface](fit_bspline_surface.md) · [eval_bspline_surface](eval_bspline_surface.md) · [fit_bspline_curve](fit_bspline_curve.md) · [eval_bspline_curve](eval_bspline_curve.md)

---
*Provenance: bspline_surf.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
