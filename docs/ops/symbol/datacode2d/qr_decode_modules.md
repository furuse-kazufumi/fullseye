---
op: qr_decode_modules
dim: symbol
category: datacode2d
in: matrix
out: table
gpu: なし
examples: [poc_symbol_part_dpm]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# qr_decode_modules — SYMBOL `datacode2d` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.qr_decode_modules(modules) -> 'dict'` (実装を直接呼ぶなら `import qrsym; qrsym.qr_decode_modules(modules) -> 'dict'`、台帳から引くなら `opssymbol.get("qr_decode_modules")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

QR のモジュール格子(静寂帯なし、1 = 暗)を復号し、ブロックごとの訂正語数を返す(``table``)。

Decode an (N,N) 0/1 module grid (1 = dark, no quiet zone). The transposed
(mirrored) grid is tried when the direct read fails.

Returns a dict with ``text``, ``version``, ``ec_level``, ``mask``, ``mode``,
``modes``, ``n_corrected``, ``block_corrected``, ``block_ec``, ``block_capacity``
(= floor((n_ec - p)/2)), ``block_p`` (誤復号保護語 / misdecode-protection codewords),
``blocks``, ``mirrored``, ``format_distance`` and ``codeword_index``. In the
mirrored case ``codeword_index`` refers to the transposed (read) grid; transpose
it to index the input grid.

Raises ``QRDecodeError`` when neither orientation decodes.

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

[qr_encode](qr_encode.md) · [qr_locate](qr_locate.md) · [qr_sample](qr_sample.md) · [qr_read](qr_read.md) · [dm_encode](dm_encode.md) · [dm_decode_modules](dm_decode_modules.md) · [dm_locate](dm_locate.md) · [dm_sample](dm_sample.md)

---
*Provenance: qrsym.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
