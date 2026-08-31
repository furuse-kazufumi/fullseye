---
op: surface_form_error
dim: 3d
category: surface_fit
in: image2d
out: measurement
examples: [geometry_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# surface_form_error — 3D `surface_fit` op

- **データ種**: `image2d` → `measurement`
- **呼び出し**: `import match3d; match3d.surface_form_error(height, degree=1)` (または `ops3d.get("surface_form_error")`)

## 使い方

高さ場 grid → 理想曲面(多項式)残差=形状誤差(平面度 deg1/球面度 deg2)。→ (residual, rms, pv)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [geometry_metrology](../../../../examples_3d/geometry_metrology.py) — `py -3.11 examples_3d/geometry_metrology.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`surface_fit`)

[fit_poly_surface](fit_poly_surface.md) · [eval_poly_surface](eval_poly_surface.md) · [background_flatten](background_flatten.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
