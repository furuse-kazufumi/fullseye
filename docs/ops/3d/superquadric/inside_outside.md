---
op: inside_outside
dim: 3d
category: superquadric
in: points
out: measurement
examples: [superquadric_fit]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# inside_outside — 3D `superquadric` op

- **データ種**: `points` → `measurement`
- **呼び出し**: `import superquadric; superquadric.inside_outside(points, a, eps, R=None, t=None) -> 'np.ndarray'` (または `ops3d.get("inside_outside")`)

## 使い方

スーパー2次曲面の内外関数 F(表面=1, 内部<1, 外部>1)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [superquadric_fit](../../../../examples_3d/superquadric_fit.py) — `py -3.11 examples_3d/superquadric_fit.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`superquadric`)

[fit_superquadric](fit_superquadric.md) · [sample_surface](sample_surface.md) · [superquadric_residual](superquadric_residual.md)

---
*Provenance: superquadric.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
