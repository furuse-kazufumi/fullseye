---
op: indices_to_labels
dim: reprconv
category: index
in: indices
out: labels
examples: [representation_conversion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# indices_to_labels — REPRCONV `index` op

- **データ種**: `indices` → `labels`
- **呼び出し**: `import reprconv; reprconv.indices_to_labels(indices)` (または `opsreprconv.get("indices_to_labels")`)

## 使い方

添字 ``(N,)`` → 選択マスク ``labels``。``indices`` の出口(**可逆**)。

``max(indices) + 1`` 長の 1-D ラベル配列を作り、選ばれた位置に 1 を置く。
``indices -> labels -> indices`` は **bit 一致**(重複と順序を除く)。
逆向き ``labels -> indices -> labels`` は**末尾の背景を落とす**
(長さが ``max_index + 1`` に切り詰まる)—— これは情報の損失であって
バグではないので、:func:`labels_to_indices` の docstring に量を書いてある。

Args:
    indices: (N,) の非負整数配列。
Returns:
    (max + 1,) の int64 ラベル配列(選択 = 1、背景 = 0)。
Raises:
    ValueError: 1-D でない / 負 / 空 / 上限超。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_conversion](../../../../examples/representation_conversion.py) — `py -3.11 examples/representation_conversion.py`

## 型が繋がる次の op(`labels` を入力に取れる)

[labels_to_indices](labels_to_indices.md)

## 同カテゴリ(`index`)

[labels_to_indices](labels_to_indices.md) · [select_points](select_points.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
