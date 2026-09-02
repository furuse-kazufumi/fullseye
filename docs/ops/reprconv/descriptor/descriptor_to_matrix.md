---
op: descriptor_to_matrix
dim: reprconv
category: descriptor
in: descriptor
out: matrix
examples: [representation_conversion, representation_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# descriptor_to_matrix — REPRCONV `descriptor` op

- **データ種**: `descriptor` → `matrix`
- **呼び出し**: `import reprconv; reprconv.descriptor_to_matrix(descriptor)` (または `opsreprconv.get("descriptor_to_matrix")`)

## 使い方

記述子 → ``matrix``。``descriptor`` の出口(**可逆**)。

1-D の記述子 (n,) は **(1, n)** の 1 行行列にする。2-D の記述子束
(``sh_descriptor`` の (12, 9) のような「点 x 次元」)はそのまま通す。
こうしておくと記述子バンクに ``mat_svd`` / ``mat_pinv`` / ``mat_cond``
がそのまま掛かる —— 記述子は本質的にベクトルなので、行列語彙へ渡すのは
梱包の付け替えであって変形ではない。

:func:`matrix_to_descriptor` と往復して **bit 一致**(実測 max|Δ| = 0.0)。

Args:
    descriptor: (n,) または (m, n) の実配列。
Returns:
    (1, n) または (m, n) float64。
Raises:
    ValueError: 3-D 以上 / 非有限 / dict(``fit_zernike`` は dict を返すので
        ここで拒否される —— 詳細は本モジュール docstring)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_conversion](../../../../examples/representation_conversion.py) — `py -3.11 examples/representation_conversion.py`
- [representation_roundtrip](../../../../examples/representation_roundtrip.py) — `py -3.11 examples/representation_roundtrip.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[matrix_to_descriptor](matrix_to_descriptor.md) · [matrix_to_angle](../algebra/matrix_to_angle.md) · [matrix_to_rot_scale](../algebra/matrix_to_rot_scale.md)

## 同カテゴリ(`descriptor`)

[matrix_to_descriptor](matrix_to_descriptor.md) · [descriptor_to_table](descriptor_to_table.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
