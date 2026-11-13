---
op: qr_encode
dim: symbol
category: datacode2d
in: 
out: table
gpu: なし
examples: [poc_symbol_part_dpm]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# qr_encode — SYMBOL `datacode2d` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.qr_encode(text, ec_level='M', version=None, mask=None, mode=None) -> 'dict'` (実装を直接呼ぶなら `import qrsym; qrsym.qr_encode(text, ec_level='M', version=None, mask=None, mode=None) -> 'dict'`、台帳から引くなら `opssymbol.get("qr_encode")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

文字列を QR Code(Model 2)のモジュール格子と符号語の対応に符号化する(``table``)。

Encode ``text`` as a QR Code (Model 2) module grid.

Parameters
----------
text : str
    符号化する文字列 / the text. Byte mode stores UTF-8 (no ECI).
ec_level : {"L", "M", "Q", "H"}
    誤り訂正レベル / error-correction level.
version : int or None
    1..40。None なら収まる最小 / 1..40, or None for the smallest that fits.
mask : int or None
    0..7。None なら 4 規則の減点が最小のもの / 0..7, or None to pick by penalty.
mode : {"numeric", "alphanumeric", "byte"} or None
    None なら文字種から自動 / None to choose from the characters.

Returns
-------
dict
    ``modules`` (N,N) uint8 (1=暗/dark), ``size``, ``version``, ``ec_level``, ``mask``,
    ``mode``, ``text``, ``blocks`` [(n_data, n_ec)…], ``n_data_codewords``,
    ``n_ec_codewords``, ``function_mask`` (N,N) bool, ``codeword_index`` (N,N) int16
    (-1 = 機能/余り / function or remainder), ``codewords`` (interleaved list).

## 詳しい使い方ガイド

- [symbol_reading ファミリ ガイド](../guides/symbol_reading.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_symbol_part_dpm](../../../../examples/poc_symbol_part_dpm.py) — `py -3.11 examples/poc_symbol_part_dpm.py`

## 型が繋がる次の op(`table` を入力に取れる)

[render_symbol](../symbol_capture/render_symbol.md) · [symbol_read_trials](../read_pod/symbol_read_trials.md) · [symbol_read_pod](../read_pod/symbol_read_pod.md) · [ocr_classify](../ocr/ocr_classify.md) · [ocr_read_line](../ocr/ocr_read_line.md) · [ocr_read_trials](../ocr/ocr_read_trials.md)

## 同カテゴリ(`datacode2d`)

[qr_decode_modules](qr_decode_modules.md) · [qr_locate](qr_locate.md) · [qr_sample](qr_sample.md) · [qr_read](qr_read.md) · [dm_encode](dm_encode.md) · [dm_decode_modules](dm_decode_modules.md) · [dm_locate](dm_locate.md) · [dm_sample](dm_sample.md)

---
*Provenance: qrsym.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
