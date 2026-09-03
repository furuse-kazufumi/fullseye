---
op: labels_to_indices
dim: reprconv
category: index
in: labels
out: indices
examples: [representation_conversion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# labels_to_indices — REPRCONV `index` op

- **データ種**: `labels` → `indices`
- **呼び出し**: `import reprconv; reprconv.labels_to_indices(labels)` (または `opsreprconv.get("labels_to_indices")`)

## 使い方

``labels`` → 非背景の添字 ``(N,)``。:func:`indices_to_labels` の逆向き。

2-D 以上のラベル画像も受ける —— その場合の添字は
**``labels.ravel()`` への添字**(C 順)である。``np.unravel_index`` で
座標へ戻せるが、**戻すには元の shape が要る**ので、この向きは
``shape`` を捨てている(不可逆)。

Args:
    labels: 任意次元の整数/実ラベル配列。
Returns:
    (N,) int64。ラベルが 0 でない位置の平坦添字(昇順)。
Raises:
    ValueError: 空 / 非有限 / 非背景が 1 つも無い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_conversion](../../../../examples/representation_conversion.py) — `py -3.11 examples/representation_conversion.py`

## 型が繋がる次の op(`indices` を入力に取れる)

[indices_to_labels](indices_to_labels.md) · [select_points](select_points.md)

## 同カテゴリ(`index`)

[indices_to_labels](indices_to_labels.md) · [select_points](select_points.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
