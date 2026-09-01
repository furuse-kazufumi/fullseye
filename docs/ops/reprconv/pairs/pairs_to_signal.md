---
op: pairs_to_signal
dim: reprconv
category: pairs
in: pairs
out: signal
examples: [representation_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# pairs_to_signal — REPRCONV `pairs` op

- **データ種**: `pairs` → `signal`
- **呼び出し**: `import reprconv; reprconv.pairs_to_signal(pairs)` (または `opsreprconv.get("pairs_to_signal")`)

## 使い方

対 ``(N,2)`` → 従属変数の ``signal`` ``(N,)``。``pairs`` の 2 つ目の出口。

列 1(y)だけを取り出す。``funct_1d_to_pairs`` が (x, y) を並べた
(N,2) を返すので、その逆向きにあたる —— **x が等間隔ならば**
``signal -> pairs -> signal`` は bit 一致する。等間隔でない x を持つ対を
通すと、**x の情報が黙って落ちる**(``signal`` は添字が等間隔だという前提の型)。
だから :func:`pairs_to_table` が ``x_uniform`` を必ず一緒に出す。

Args:
    pairs: (N, 2) または 2 本の等長 1-D のタプル。
Returns:
    (N,) float64。
Raises:
    ValueError: 形状不正 / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_roundtrip](../../../../examples/representation_roundtrip.py) — `py -3.11 examples/representation_roundtrip.py`

## 型が繋がる次の op(`signal` を入力に取れる)

—

## 同カテゴリ(`pairs`)

[pairs_to_image2d](pairs_to_image2d.md) · [pairs_to_table](pairs_to_table.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
