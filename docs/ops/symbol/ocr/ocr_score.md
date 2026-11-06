---
op: ocr_score
dim: symbol
category: ocr
in: 
out: table
gpu: なし
examples: [poc_symbol_lot_ocr]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# ocr_score — SYMBOL `ocr` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.ocr_score(read_text, true_text) -> 'dict'` (実装を直接呼ぶなら `import ocrclassic; ocrclassic.ocr_score(read_text, true_text) -> 'dict'`、台帳から引くなら `opssymbol.get("ocr_score")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

読み取り結果を真値と Levenshtein 整列で採点し、誤読と棄却を分けて数える(``table``)。

整列(置換・挿入・削除の費用 1)の後、整列した各対を数える:

* ``correct``     —— 同じ字
* ``rejected``    —— 真値の字に対して ``"?"``(**棄却**: 安全側。人が見れば済む)
* ``substituted`` —— 真値と違う字(**誤読**: 危険側。検査では見逃しになる)
* ``inserted``    —— 真値に無い字が読まれた(``"?"`` の挿入も含む)
* ``deleted``     —— 真値の字が読まれなかった

誤読と棄却は**決して 1 つの率に畳まない**。率は真値の字数で割る。
Misreads and rejects are never folded into one rate. Rates are per true character.

## 詳しい使い方ガイド

- [symbol_reading ファミリ ガイド](../guides/symbol_reading.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_symbol_lot_ocr](../../../../examples/poc_symbol_lot_ocr.py) — `py -3.11 examples/poc_symbol_lot_ocr.py`

## 型が繋がる次の op(`table` を入力に取れる)

[render_symbol](../symbol_capture/render_symbol.md) · [symbol_read_trials](../read_pod/symbol_read_trials.md) · [symbol_read_pod](../read_pod/symbol_read_pod.md) · [ocr_classify](ocr_classify.md) · [ocr_read_line](ocr_read_line.md) · [ocr_read_trials](ocr_read_trials.md)

## 同カテゴリ(`ocr`)

[ocr_font](ocr_font.md) · [ocr_render_text](ocr_render_text.md) · [ocr_segment_line](ocr_segment_line.md) · [ocr_features](ocr_features.md) · [ocr_train](ocr_train.md) · [ocr_classify](ocr_classify.md) · [ocr_read_line](ocr_read_line.md) · [ocr_read_trials](ocr_read_trials.md)

---
*Provenance: ocrclassic.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
