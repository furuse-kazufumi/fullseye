---
op: ocr_segment_line
dim: symbol
category: ocr
in: image2d
out: table
gpu: なし
examples: [poc_symbol_lot_ocr]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# ocr_segment_line — SYMBOL `ocr` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.ocr_segment_line(image, char_height_px=None, dot_font=None) -> 'dict'` (実装を直接呼ぶなら `import ocrclassic; ocrclassic.ocr_segment_line(image, char_height_px=None, dot_font=None) -> 'dict'`、台帳から引くなら `opssymbol.get("ocr_segment_line")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

1 行の文字を 1 字ずつの外接箱に切り出す(``table``)。

手順: 大津で地とインクの代表値(中央値)→ インク量の地図 → 字の画素 = インク量 >= 0.5 →
雑音点の除去 → (ドット書体なら) 列射影にドットピッチ 0.6 倍の 1-D closing で 1 字のドットを
まとめる → 列射影の切れ目で区間化 → 想定送り幅で断片を併合・接触字を分割(射影の谷)→
字の画素が 0.02 h^2 未満の区間を捨てる。等幅(固定ピッチ)印字を前提とする。
幾何だけの分割なので、ぼけで接触した字は ``ocr_read_line`` が認識で切り直す。
Otsu class medians -> ink map -> glyph pixels (ink >= 0.5) -> speck removal -> (dot font)
1-D closing of the column projection (0.6 x dot pitch) -> runs -> merge / split by expected
pitch -> drop pieces < 0.02 h^2 pixels. Assumes fixed-pitch print.

Parameters
----------
image : 2-D 灰色(float 0..1 か uint8)。暗いインク・明るい地(逆なら縁から自動反転)。
char_height_px : 字高の既知値。None なら行のインクの縦幅から推定
    (★行が ``-`` ``.`` だけだと過小推定になる —— 既知なら渡すこと)。
dot_font : True/False/None(None = 連結成分の大きさで自動判定)。

Returns
-------
dict
    ``boxes`` 左→右の ``(r0, c0, r1, c1)``(終端は含まない), ``threshold``(大津の閾値、
    雑音があれば 0.7 px 平滑後の画像に対する値。字の画素の判定には使わない参考値),
    ``line_box``, ``char_height_px``(使った値), ``pitch_px``(推定送り幅), ``dot_font``。
    白紙(インクと地の分離が雑音 4σ 未満)は **fail-soft で** ``boxes == []``,
    ``line_box is None``。

Raises
------
ValueError
    NaN/inf、2-D 以外、数値でない、4x4 未満。

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

[ocr_font](ocr_font.md) · [ocr_render_text](ocr_render_text.md) · [ocr_features](ocr_features.md) · [ocr_train](ocr_train.md) · [ocr_classify](ocr_classify.md) · [ocr_read_line](ocr_read_line.md) · [ocr_score](ocr_score.md) · [ocr_read_trials](ocr_read_trials.md)

---
*Provenance: ocrclassic.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
