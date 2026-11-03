---
op: ocr_render_text
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

# ocr_render_text — SYMBOL `ocr` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.ocr_render_text(text, font='dot5x7', char_height_px=24, pitch=None, dot_diameter=0.8, ink_gain=0.0, contrast=0.8, background=0.9, supersample=4, stroke_width=0.12, subpixel_offset=(0.0, 0.0)) -> 'dict'` (実装を直接呼ぶなら `import ocrclassic; ocrclassic.ocr_render_text(text, font='dot5x7', char_height_px=24, pitch=None, dot_diameter=0.8, ink_gain=0.0, contrast=0.8, background=0.9, supersample=4, stroke_width=0.12, subpixel_offset=(0.0, 0.0)) -> 'dict'`、台帳から引くなら `opssymbol.get("ocr_render_text")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

文字列を内蔵書体で描き、字ごとの真値の外接箱と一緒に返す(``table``)。

Parameters
----------
text : str
    字種内の字だけ(大文字)。空文字・字種外は ValueError。
font : 書体名 (``"dot5x7"``/``"stroke"``) か ``ocr_font`` の辞書(字を足したもの可)。
char_height_px : 字高(画素)= 全高の字のインクの縦の広がり。>= 6。
pitch : 字の送り幅(画素)。None なら書体の既定(~0.88 x 字高)。
dot_diameter : ドット直径 / ドットピッチ(dot5x7 のみ)。(0, 1.5]。
ink_gain : にじみ。ドット直径・線幅に ``(1 + ink_gain)`` を掛ける。(-0.9, 2]。
contrast, background : 地の明るさ ``background``、インクの明るさ ``background - contrast``。
supersample : 1 画素あたりの超標本数(一辺)。1..16。
stroke_width : 線幅 / 字高(stroke のみ)。(0, 0.4]。
subpixel_offset : (dy, dx) 画素。字列全体を小数画素ずらす(学習の撹乱用)。

Returns
-------
dict
    ``image`` 2-D float [0, 1] (明るい地に暗いインク), ``boxes`` 字ごとの真値の外接箱
    ``(r0, c0, r1, c1)``(終端は含まない、被覆率 >= 0.5 の画素の外接箱), ``text``,
    ``line_box``(字高の行範囲 x 全幅), ``pitch_px``, ``cells``(各字の設計上の字幅の列範囲
    ``(左, 右)``、小数画素)。周囲に約 1 字高の余白。

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

[ocr_font](ocr_font.md) · [ocr_segment_line](ocr_segment_line.md) · [ocr_features](ocr_features.md) · [ocr_train](ocr_train.md) · [ocr_classify](ocr_classify.md) · [ocr_read_line](ocr_read_line.md) · [ocr_score](ocr_score.md) · [ocr_read_trials](ocr_read_trials.md)

---
*Provenance: ocrclassic.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
