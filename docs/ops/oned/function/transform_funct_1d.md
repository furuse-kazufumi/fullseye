---
op: transform_funct_1d
dim: oned
category: function
in: signal
out: pairs
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# transform_funct_1d — ONED `function` op

- **データ種**: `signal` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.transform_funct_1d(y, mult_x=1.0, add_x=0.0, mult_y=1.0, add_y=0.0)` (実装を直接呼ぶなら `import funct1d; funct1d.transform_funct_1d(y, mult_x=1.0, add_x=0.0, mult_y=1.0, add_y=0.0)`、台帳から引くなら `ops1d.get("transform_funct_1d")`)

## 使い方

Independent affine transform of x and y (HALCON ``transform_funct_1d``).

Returns explicit pairs ``(mult_x * i + add_x, mult_y * y[i] + add_y)`` for
``i = 0..n-1``. Note ``mult_x = 0`` collapses the abscissa to a single
point (accepted; the result is then not a function of x).

:param y: 1-D function (may be empty).
:param mult_x, add_x, mult_y, add_y: finite affine coefficients.
:returns: ``(n, 2)`` float64 array of ``(x, y)`` pairs.
:raises ValueError: non-1-D / NaN / Inf input, or non-finite parameter.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`pairs` を入力に取れる)

—

## 同カテゴリ(`function`)

[create_funct_1d_array](create_funct_1d_array.md) · [create_funct_1d_pairs](create_funct_1d_pairs.md) · [smooth_funct_1d_gauss](smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](smooth_funct_1d_mean.md) · [derivate_funct_1d](derivate_funct_1d.md) · [integrate_funct_1d](integrate_funct_1d.md) · [zero_crossings_funct_1d](zero_crossings_funct_1d.md) · [local_min_max_funct_1d](local_min_max_funct_1d.md)

---
*Provenance: funct1d.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
