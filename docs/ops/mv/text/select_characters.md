---
op: select_characters
dim: mv
category: text
in: labels2d
out: labels2d
halcon: select_characters
gpu: なし
examples: [machine_vision_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# select_characters — MV `text` op

- **データ種**: `labels2d` → `labels2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.select_characters(labels, min_height_ratio=0.5, max_height_ratio=1.5, max_width_ratio=2.0)` (実装を直接呼ぶなら `import mvtext; mvtext.select_characters(labels, min_height_ratio=0.5, max_height_ratio=1.5, max_width_ratio=2.0)`、台帳から引くなら `opsmv.get("select_characters")`)
- **HALCON 相当**: `select_characters`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

字のラベル画像から、高さと幅が中央値から外れた塊を落として左から振り直す。

高さと幅の中央値に対する比で判定する。塊が 1 つも無いと全 0 を返す(理由: 字が無い)。
空の入力(``labels`` が 0 要素)は ValueError。

Args:
    labels: :func:`segment_characters` のラベル画像。
    min_height_ratio: 高さの下限(中央値に対する比)。
    max_height_ratio: 高さの上限(中央値に対する比)。
    max_width_ratio: 幅の上限(中央値に対する比)。

Returns:
    ``labels`` と同じ形の整数ラベル画像。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`

## 型が繋がる次の op(`labels2d` を入力に取れる)

—

## 同カテゴリ(`text`)

[text_line_orientation](text_line_orientation.md) · [text_line_slant](text_line_slant.md) · [segment_characters](segment_characters.md)

---
*Provenance: mvtext.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
