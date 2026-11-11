---
op: symbol_read
dim: symbol
category: read_pod
in: image2d
out: table
gpu: なし
examples: [poc_symbol_package_1d]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# symbol_read — SYMBOL `read_pod` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.symbol_read(image, reader='barcode1d', symbologies=None)` (実装を直接呼ぶなら `import symbolpod; symbolpod.symbol_read(image, reader='barcode1d', symbologies=None)`、台帳から引くなら `opssymbol.get("symbol_read")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

画像を指定の読み取り器で読み、``{"ok", "text", "error"}`` を返す(``table``)。

Read an image with one of the family's readers (``"barcode1d"`` =
:func:`barcode1d.read_barcode1d`, ``"qr"`` = ``qrsym.qr_read``, ``"datamatrix"`` =
``dmsym.dm_read``, ``"zxing"`` = :func:`symzxing.read_symbols_zxing`, optional extra,
restricted to ``symbologies`` mapped by :data:`ZXING_FORMATS`; its UPC-A answer is
normalised to 12 digits) and return ``ok`` (decoded at all), ``text`` (None if not) and
``error`` (the reader's message on a no-read). A no-read is not an exception here —
it is an outcome to be counted.

空の入力は ``ValueError``(読み取り器の検査をそのまま通す)。
拒否(``ValueError``): 未知の ``reader``、2-D でない、非有限。

## 詳しい使い方ガイド

- [symbol_reading ファミリ ガイド](../guides/symbol_reading.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_symbol_package_1d](../../../../examples/poc_symbol_package_1d.py) — `py -3.11 examples/poc_symbol_package_1d.py`

## 型が繋がる次の op(`table` を入力に取れる)

[render_symbol](../symbol_capture/render_symbol.md) · [symbol_read_trials](symbol_read_trials.md) · [symbol_read_pod](symbol_read_pod.md) · [ocr_classify](../ocr/ocr_classify.md) · [ocr_read_line](../ocr/ocr_read_line.md) · [ocr_read_trials](../ocr/ocr_read_trials.md)

## 同カテゴリ(`read_pod`)

[symbol_read_trials](symbol_read_trials.md) · [symbol_read_pod](symbol_read_pod.md)

---
*Provenance: symbolpod.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
