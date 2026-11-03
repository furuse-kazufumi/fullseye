---
op: ocr_font
dim: symbol
category: ocr
in: 
out: table
gpu: なし
examples: [poc_symbol_lot_ocr]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# ocr_font — SYMBOL `ocr` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.ocr_font(name: 'str' = 'dot5x7') -> 'dict'` (実装を直接呼ぶなら `import ocrclassic; ocrclassic.ocr_font(name: 'str' = 'dot5x7') -> 'dict'`、台帳から引くなら `opssymbol.get("ocr_font")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

内蔵書体(5x7 ドット / 線)の字種と字形の設計を返す(``table``)。

Parameters
----------
name : ``"dot5x7"`` か ``"stroke"``。

Returns
-------
dict
    ``name``, ``charset`` (str), ``glyphs`` (char -> design: dot5x7 は (7,5) uint8 のビットマップ、
    stroke は折れ線のリスト ``[[(x, y), ...], ...]``), ``kind`` (``"dot"``/``"stroke"``),
    ``grid`` (設計格子の (行, 列) または (高さ, 幅)), ``advance`` (設計単位の送り幅:
    dot5x7 = 6 ドットピッチ、stroke = 6 格子単位)。
    返す辞書は毎回新しい複製なので、呼ぶ側が字を足して ``ocr_render_text(font=<dict>)`` に
    渡してよい(字種外の試験字を作る用途)。

Raises
------
ValueError
    未知の書体名。

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

[ocr_render_text](ocr_render_text.md) · [ocr_segment_line](ocr_segment_line.md) · [ocr_features](ocr_features.md) · [ocr_train](ocr_train.md) · [ocr_classify](ocr_classify.md) · [ocr_read_line](ocr_read_line.md) · [ocr_score](ocr_score.md) · [ocr_read_trials](ocr_read_trials.md)

---
*Provenance: ocrclassic.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
