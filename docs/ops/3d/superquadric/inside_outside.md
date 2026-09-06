---
op: inside_outside
dim: 3d
category: superquadric
in: points
out: signal
examples: [superquadric_fit]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# inside_outside — 3D `superquadric` op

- **データ種**: `points` → `signal`
- **呼び出し**: `import superquadric; superquadric.inside_outside(points, a, eps, R=None, t=None) -> 'np.ndarray'` (または `ops3d.get("inside_outside")`)

## 使い方

スーパー2次曲面の内外関数 F(表面=1, 内部<1, 外部>1)。

``F(X) = (|x/a1|^(2/eps2) + |y/a2|^(2/eps2))^(eps2/eps1) + |z/a3|^(2/eps1)``。
``R, t`` で姿勢(``X_body = R.T @ (X - t)``)。

Parameters
----------
points : array_like (N,3)
a : (a1,a2,a3) 半径(すべて正)
eps : (eps1,eps2) 形状指数(> 0)
R : (3,3) 回転(列 = body 軸の world 表現)、既定 = 単位
t : (3,) 平行移動(body 中心の world 位置)、既定 = 原点

Returns
-------
np.ndarray, shape (N,)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [superquadric_fit](../../../../examples_3d/superquadric_fit.py) — `py -3.11 examples_3d/superquadric_fit.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`superquadric`)

[fit_superquadric](fit_superquadric.md) · [sample_surface](sample_surface.md) · [superquadric_residual](superquadric_residual.md)

---
*Provenance: superquadric.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
