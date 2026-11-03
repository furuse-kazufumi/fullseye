---
op: dm_encode
dim: symbol
category: datacode2d
in: 
out: table
gpu: なし
examples: [poc_symbol_part_dpm]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# dm_encode — SYMBOL `datacode2d` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.dm_encode(text, size=None, shape: 'str' = 'square', encodation: 'str' = 'auto') -> 'dict'` (実装を直接呼ぶなら `import dmsym; dmsym.dm_encode(text, size=None, shape: 'str' = 'square', encodation: 'str' = 'auto') -> 'dict'`、台帳から引くなら `opssymbol.get("dm_encode")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

文字列を Data Matrix ECC200 のモジュール格子と符号語の対応に符号化する(``table``)。

Encode ``text`` (str with code points <= 255, or bytes) as an ECC200 symbol.

Parameters
----------
text : str | bytes
    U+0000..U+00FF のみ(Latin-1 の 1 バイト)。ECI は扱わない。
size : None | int | (rows, cols)
    None なら ``shape`` の中で収まる最小の記号。int は正方形 N×N。
shape : {"square", "rectangle", "any"}
    ``size`` が None のときの候補。"rect" も "rectangle" と同じ。
encodation : {"auto", "ascii", "c40", "text", "base256"}
    "auto" は各記号の大きさで ascii → c40 → text → base256 の順に試し、
    最小の記号に収まる最初のもの(文書全体を 1 つの符号化で書く。区間ごとの最適化はしない)。

Returns
-------
dict
    ``modules`` (R, C) uint8 1 = 暗(L 字・クロック・領域の区切り込み)、``rows``, ``cols``,
    ``text``, ``encodation``, ``blocks`` [(n_data, n_ec)], ``n_data_codewords``,
    ``n_ec_codewords``, ``function_mask`` (R, C) bool, ``fixed_mask``(右下の固定 2x2),
    ``codeword_index`` (R, C) int16(送出順の符号語番号、機能 module と固定角は -1)、
    ``bit_index``(0 = 最上位ビット、-1 = 対象外)、``codewords``(送出順の全符号語)、
    ``data_codewords``(パッド込み)。

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

[qr_encode](qr_encode.md) · [qr_decode_modules](qr_decode_modules.md) · [qr_locate](qr_locate.md) · [qr_sample](qr_sample.md) · [qr_read](qr_read.md) · [dm_decode_modules](dm_decode_modules.md) · [dm_locate](dm_locate.md) · [dm_sample](dm_sample.md)

---
*Provenance: dmsym.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
