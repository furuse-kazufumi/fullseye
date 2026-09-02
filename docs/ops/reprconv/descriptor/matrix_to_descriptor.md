---
op: matrix_to_descriptor
dim: reprconv
category: descriptor
in: matrix
out: descriptor
examples: [representation_conversion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# matrix_to_descriptor — REPRCONV `descriptor` op

- **データ種**: `matrix` → `descriptor`
- **呼び出し**: `import reprconv; reprconv.matrix_to_descriptor(matrix)` (または `opsreprconv.get("matrix_to_descriptor")`)

## 使い方

``matrix`` → 記述子。:func:`descriptor_to_matrix` の逆。

1 行の行列 (1, n) は (n,) へ戻す(それが元の 1-D 記述子だから)。
2 行以上はそのまま。**この非対称は意図的**で、これが無いと
``descriptor -> matrix -> descriptor`` の往復が (n,) から (1,n) へ
静かに形を変える = 型の嘘そのものになる。

★**測って残す非可逆点**: そのぶん、元から **(1, n) の 2-D だった記述子**は
往復で (n,) の 1-D になる —— (1,n) の行列は「1-D 記述子を包んだもの」と
「行が 1 本しかない記述子束」の区別を持たないので、**この 1 ケースだけは
原理的に戻せない**。値は全て保存されるので損失は「行が 1 本だった」という
メタ情報のみ。どちらを非可逆にするか選ばされる状況で、
``descriptor`` の圧倒的多数(実測 14 producers 中 12 が 1-D)を厳密側に
倒した。``tests/test_reprconv.py::test_one_row_descriptor_ambiguity_is_documented``
がこの穴を**塞がずに固定**している(隠すと、いつか黙って形が変わる)。

Args:
    matrix: (m, n) の実配列。
Returns:
    m == 1 なら (n,)、それ以外は (m, n)。
Raises:
    ValueError: 2-D でない / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_conversion](../../../../examples/representation_conversion.py) — `py -3.11 examples/representation_conversion.py`

## 型が繋がる次の op(`descriptor` を入力に取れる)

[descriptor_to_matrix](descriptor_to_matrix.md) · [descriptor_to_table](descriptor_to_table.md)

## 同カテゴリ(`descriptor`)

[descriptor_to_matrix](descriptor_to_matrix.md) · [descriptor_to_table](descriptor_to_table.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
