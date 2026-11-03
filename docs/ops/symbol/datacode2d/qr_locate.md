---
op: qr_locate
dim: symbol
category: datacode2d
in: image2d
out: table
gpu: なし
examples: [poc_symbol_part_dpm]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# qr_locate — SYMBOL `datacode2d` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.qr_locate(image) -> 'dict'` (実装を直接呼ぶなら `import qrsym; qrsym.qr_locate(image) -> 'dict'`、台帳から引くなら `opssymbol.get("qr_locate")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

画像から QR を見つけ、モジュール空間 → 画像の射影変換を推定する(``table``)。

Locate a QR symbol (dark modules on a light background) in a 2-D float image in
[0, 1]. Returns ``homography`` (module [x=col, y=row, 1] -> image [x=col_px,
y=row_px, w]), ``size``, ``version``, ``finder_centers`` (3,2) (row, col) px in
TL/TR/BL order, ``module_px`` and ``timing_score`` (fraction of timing modules
read as expected, a sanity measure). Raises ``QRDecodeError`` if not found.

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

[qr_encode](qr_encode.md) · [qr_decode_modules](qr_decode_modules.md) · [qr_sample](qr_sample.md) · [qr_read](qr_read.md) · [dm_encode](dm_encode.md) · [dm_decode_modules](dm_decode_modules.md) · [dm_locate](dm_locate.md) · [dm_sample](dm_sample.md)

---
*Provenance: qrsym.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
