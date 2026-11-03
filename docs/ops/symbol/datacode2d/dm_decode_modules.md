---
op: dm_decode_modules
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

# dm_decode_modules — SYMBOL `datacode2d` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.dm_decode_modules(modules) -> 'dict'` (実装を直接呼ぶなら `import dmsym; dmsym.dm_decode_modules(modules) -> 'dict'`、台帳から引くなら `opssymbol.get("dm_decode_modules")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Data Matrix のモジュール格子(L 字とクロック込み、0/1)を復号し、訂正語数を返す(``table``)。

Decode an (R, C) 0/1 module matrix that includes the finder L and the clock track.
The grid may be given in any of the 4 rotations, optionally mirrored; the
orientation is found from the function pattern (solid L + clock) and, when the
pattern alone is ambiguous (a square symbol and its anti-diagonal mirror share
it), from which orientation passes Reed-Solomon.

Returns
-------
dict
    ``text``, ``rows``, ``cols``, ``n_corrected``, ``block_corrected`` [int],
    ``block_ec`` [EC 語数], ``block_capacity`` [floor(n_ec/2)], ``finder_errors``
    (機能 module の不一致数), ``codeword_index``(正規化後の向き)、``rotation``
    (度、0/90/180/270)と ``mirrored``: 正規化 =
    ``np.rot90(np.fliplr(g) if mirrored else g, rotation // 90)``、``modules``(正規化後)、
    ``codewords_raw`` / ``codewords``(訂正前後、送出順)、``encodations``、
    ``fixed_errors``(右下固定 2x2 の不一致数、無ければ 0)。

Raises
------
ValueError
    2-D でない・0/1 以外・NaN。
DMDecodeError
    どの向きでも対応する大きさにならない、機能パターンが崩れすぎ、RS 訂正不能、符号化の矛盾。

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

[qr_encode](qr_encode.md) · [qr_decode_modules](qr_decode_modules.md) · [qr_locate](qr_locate.md) · [qr_sample](qr_sample.md) · [qr_read](qr_read.md) · [dm_encode](dm_encode.md) · [dm_locate](dm_locate.md) · [dm_sample](dm_sample.md)

---
*Provenance: dmsym.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
