---
op: ocr_read_line
dim: symbol
category: ocr
in: image2d × table
out: table
gpu: なし
examples: [poc_symbol_lot_ocr]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# ocr_read_line — SYMBOL `ocr` op

- **データ種**: `image2d × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.ocr_read_line(image, model, char_height_px=None, k=None) -> 'dict'` (実装を直接呼ぶなら `import ocrclassic; ocrclassic.ocr_read_line(image, model, char_height_px=None, k=None) -> 'dict'`、台帳から引くなら `opssymbol.get("ocr_read_line")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

画像の 1 行を読む: 切り出し + 識別、棄却した字は ``?``(``table``)。

Returns
-------
dict
    ``text``(棄却は ``"?"``), ``chars``(各字の ``label``, ``raw_label``, ``box``,
    ``distance``, ``margin``, ``rejected``), ``n_chars``, ``n_rejected``, ``line_box``。
    白紙は fail-soft で ``text == ""``, ``n_chars == 0``。

## 詳しい使い方ガイド

- [symbol_reading ファミリ ガイド](../guides/symbol_reading.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_symbol_lot_ocr](../../../../examples/poc_symbol_lot_ocr.py) — `py -3.11 examples/poc_symbol_lot_ocr.py`

## 型が繋がる次の op(`table` を入力に取れる)

[render_symbol](../symbol_capture/render_symbol.md) · [symbol_read_trials](../read_pod/symbol_read_trials.md) · [symbol_read_pod](../read_pod/symbol_read_pod.md) · [ocr_classify](ocr_classify.md) · [ocr_read_trials](ocr_read_trials.md)

## 同カテゴリ(`ocr`)

[ocr_font](ocr_font.md) · [ocr_render_text](ocr_render_text.md) · [ocr_segment_line](ocr_segment_line.md) · [ocr_features](ocr_features.md) · [ocr_train](ocr_train.md) · [ocr_classify](ocr_classify.md) · [ocr_score](ocr_score.md) · [ocr_read_trials](ocr_read_trials.md)

---
*Provenance: ocrclassic.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
