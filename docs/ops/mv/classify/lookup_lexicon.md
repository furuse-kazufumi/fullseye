---
op: lookup_lexicon
dim: mv
category: classify
in: table
out: scalar
halcon: lookup_lexicon
gpu: なし
examples: [machine_vision_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# lookup_lexicon — MV `classify` op

- **データ種**: `table` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.lookup_lexicon(lexicon, word)` (実装を直接呼ぶなら `import mvclass; mvclass.lookup_lexicon(lexicon, word)`、台帳から引くなら `opsmv.get("lookup_lexicon")`)
- **HALCON 相当**: `lookup_lexicon`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

語が一覧にあるかを完全一致で調べ、あれば 1.0、無ければ 0.0 を返す。

空の入力(``word`` が空文字)は ValueError。

Args:
    lexicon: :func:`create_lexicon` の返り。
    word: 調べる語。

Returns:
    一覧にあれば ``1.0``、無ければ ``0.0``。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`classify`)

[train_class_gmm](train_class_gmm.md) · [classify_class_gmm](classify_class_gmm.md) · [evaluate_class_gmm](evaluate_class_gmm.md) · [train_class_knn](train_class_knn.md) · [classify_class_knn](classify_class_knn.md) · [train_class_mlp](train_class_mlp.md) · [classify_class_mlp](classify_class_mlp.md) · [train_class_svm](train_class_svm.md)

---
*Provenance: mvclass.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
