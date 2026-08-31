---
op: arc_length
dim: 3d
category: curve
in: points
out: measurement
examples: [space_curve, torus_knot_curve]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# arc_length — 3D `curve` op

- **データ種**: `points` → `measurement`
- **呼び出し**: `import curve3d; curve3d.arc_length(curve)` (または `ops3d.get("arc_length")`)

## 使い方

曲線の累積弧長と全長。→ (cumulative (N,), total float)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [space_curve](../../../../examples_3d/space_curve.py) — `py -3.11 examples_3d/space_curve.py`
- [torus_knot_curve](../../../../examples_3d/torus_knot_curve.py) — `py -3.11 examples_3d/torus_knot_curve.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`curve`)

[curvature_torsion](curvature_torsion.md) · [frenet_frame](frenet_frame.md) · [resample_uniform](resample_uniform.md) · [fit_spline_curve](fit_spline_curve.md)

---
*Provenance: curve3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
