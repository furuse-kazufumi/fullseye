---
op: superquadric_residual
dim: 3d
category: superquadric
in: points
out: measurement
examples: [superquadric_fit]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# superquadric_residual — 3D `superquadric` op

- **データ種**: `points` → `measurement`
- **呼び出し**: `import superquadric; superquadric.superquadric_residual(points, a, eps, R, t) -> 'float'` (または `ops3d.get("superquadric_residual")`)

## 使い方

Gross-Boult 体積補正残差 mean( (sqrt(a1 a2 a3)(F^eps1 - 1))^2 )。

``inside_outside(points, a, eps, R, t)`` で各点の内外関数 F を求め、点ごとの残差
``r_i = sqrt(a1*a2*a3) * (F_i**eps1 - 1)`` の 2 乗平均を float で返す。表面上の点は ``F=1`` なので
残差 0、内側は負・外側は正の残差になる(2 乗するので符号は消える)。``fit_superquadric`` が
最小化しているのと同じ量で、返り dict の ``residual`` もこの値。

- ``points``: (N,3) にリシェイプできる点群(world 座標)。
- ``a``: 半径 (a1,a2,a3)。``eps``: 形状指数 (eps1,eps2)(F の計算には両方、外側の ``F**eps1`` には
  ``eps1`` だけを使う)。
- ``R``/``t``: 姿勢(``X_body = R.T @ (X - t)``)。``None`` なら単位回転 / 原点。

数値保護: F は [0, 1e12] にクリップし、``a1*a2*a3`` は 1e-12 以上に持ち上げてから sqrt を取る
(退化パラメータで inf/NaN にならないため。表面近傍の値には影響しない)。
次元: ``sqrt(a1 a2 a3)`` は長さの 3/2 乗、``F^eps1 - 1`` は無次元なので、返り値は長さの 3 乗の
次元を持ち点群のスケールに依存する。大きさの違う物体どうしの比較には向かない。真の点-表面
ユークリッド距離ではなく半径距離近似であること、外れ値に無防備なことはモジュール docstring
のとおり。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [superquadric_fit](../../../../examples_3d/superquadric_fit.py) — `py -3.11 examples_3d/superquadric_fit.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`superquadric`)

[fit_superquadric](fit_superquadric.md) · [sample_surface](sample_surface.md) · [inside_outside](inside_outside.md)

---
*Provenance: superquadric.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
