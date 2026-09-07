---
op: inertia_tensor
dim: 3d
category: moment_invariant
in: points
out: matrix
examples: [moment_invariants]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# inertia_tensor — 3D `moment_invariant` op

- **データ種**: `points` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.inertia_tensor(points) -> 'np.ndarray'` (実装を直接呼ぶなら `import moments3d; moments3d.inertia_tensor(points) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("inertia_tensor")`)

## 使い方

点群の慣性テンソル (3,3)(中心 2 次モーメントから、等質量・総質量 1)。

I_xx = mean(y²+z²), I_yy = mean(x²+z²), I_zz = mean(x²+y²),
I_xy = -mean(xy), I_xz = -mean(xz), I_yz = -mean(yz)。
共分散 C を使うと I = tr(C)·E₃ − C(E₃ は単位行列)と等価。対称・半正定値。
重心中心化のため並進不変。

Returns
-------
np.ndarray, shape (3, 3)
    対称な慣性テンソル。

補足:
- 単位は長さ²(質量 1 の等質量点とみなすので密度は入らない)。点群を回転で回すと ``R I Rᵀ`` に写り、固有値(``principal_moments``)が回転不変量、固有ベクトルが主軸(``moment_axes``)。
- 入力は (N,3)、N >= 1(1 点なら零行列)。形状不正・非有限は ``ValueError``。
- 共分散 C とは ``I = tr(C)·E₃ - C`` の関係で、C と I の固有ベクトルは同じ、固有値は ``tr(C) - c_i``。
- 実体(体積)のモーメントではなく **サンプル点** のモーメントなので、同じ形でも点密度の偏りで値が変わる。密度を均すなら前段で ``voxel_grid_downsample``。決定論的。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [moment_invariants](../../../../examples_3d/moment_invariants.py) — `py -3.11 examples_3d/moment_invariants.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`moment_invariant`)

[moment_invariants](moment_invariants.md) · [principal_moments](principal_moments.md) · [central_moments](central_moments.md)

---
*Provenance: moments3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
