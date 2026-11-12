---
op: ocr_read_trials
dim: symbol
category: ocr
in: table
out: table
gpu: なし
examples: [poc_symbol_lot_ocr]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# ocr_read_trials — SYMBOL `ocr` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.ocr_read_trials(text, factor, levels, *, model, font=None, char_height_px=24.0, trials=20, render=None, capture=None, level_jitter=0.0, refine=False, seed=0)` (実装を直接呼ぶなら `import symbolpod; symbolpod.ocr_read_trials(text, factor, levels, *, model, font=None, char_height_px=24.0, trials=20, render=None, capture=None, level_jitter=0.0, refine=False, seed=0)`、台帳から引くなら `opssymbol.get("ocr_read_trials")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

印字した文字列を劣化量の各水準で ``trials`` 回撮って OCR で読み、1 行 = 1 回の表を返す(``table``)。

Legibility trials for classical OCR: render ``text`` with the built-in font
(``ocrclassic.ocr_render_text``; ``font`` defaults to the model's font), apply the
capture chain (:func:`symrender.capture_degrade`, sensor 20000 e / 10 e / 8 bit by
default) with the swept ``factor`` (:data:`OCR_FACTORS`), and read the line with
``ocrclassic.ocr_read_line``. Each trial draws a fresh sub-pixel offset of the line
and a sensor-noise seed. Outcomes per capture: ``hit`` = the whole string read
exactly, ``misread`` = at least one character read as a *different* character
(substituted or inserted, per ``ocrclassic.ocr_score``) — the dangerous case, never
folded into the read rate —, ``noread`` = otherwise (rejects ``?`` or missing
characters only). The table has the same columns as :func:`symbol_read_trials`
(plus ``rejected_chars`` / ``substituted_chars``) so :func:`symbol_read_pod` fits it.
``refine`` and ``level_jitter`` work as in :func:`symbol_read_trials`.

空の入力(``text == ""`` / ``levels`` が 3 未満)は ``ValueError``。
拒否(``ValueError``): 未知の ``factor``、``trials`` < 1、水準の重複・非有限、
字種の外の文字、``render`` / ``capture`` に掃引中の因子と同じ鍵、``level_jitter`` が
[0, 0.5] の外、OCR の模型でない ``model``。

## 詳しい使い方ガイド

- [symbol_reading ファミリ ガイド](../guides/symbol_reading.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_symbol_lot_ocr](../../../../examples/poc_symbol_lot_ocr.py) — `py -3.11 examples/poc_symbol_lot_ocr.py`

## 型が繋がる次の op(`table` を入力に取れる)

[render_symbol](../symbol_capture/render_symbol.md) · [symbol_read_trials](../read_pod/symbol_read_trials.md) · [symbol_read_pod](../read_pod/symbol_read_pod.md) · [ocr_classify](ocr_classify.md) · [ocr_read_line](ocr_read_line.md)

## 同カテゴリ(`ocr`)

[ocr_font](ocr_font.md) · [ocr_render_text](ocr_render_text.md) · [ocr_segment_line](ocr_segment_line.md) · [ocr_features](ocr_features.md) · [ocr_train](ocr_train.md) · [ocr_classify](ocr_classify.md) · [ocr_read_line](ocr_read_line.md) · [ocr_score](ocr_score.md)

---
*Provenance: symbolpod.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
