---
op: dm_sample
dim: symbol
category: datacode2d
in: image2d
out: table
gpu: なし
examples: [poc_symbol_part_dpm]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# dm_sample — SYMBOL `datacode2d` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.dm_sample(image, located=None) -> 'dict'` (実装を直接呼ぶなら `import dmsym; dmsym.dm_sample(image, located=None) -> 'dict'`、台帳から引くなら `opssymbol.get("dm_sample")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Data Matrix のモジュール中心の反射率を双一次補間で取り、大域しきい値で 2 値化する(``table``)。

Sample every module centre (bilinear) through the located homography and
threshold globally at the midpoint of the dark and light means (initial split
at the midpoint of the 5th/95th percentiles, then two mean-midpoint updates).

Returns ``reflectance`` (R, C), ``modules`` (R, C) uint8 dark = 1,
``threshold``, ``homography``, ``centers`` (R, C, 2) px (row, col).

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

[qr_encode](qr_encode.md) · [qr_decode_modules](qr_decode_modules.md) · [qr_locate](qr_locate.md) · [qr_sample](qr_sample.md) · [qr_read](qr_read.md) · [dm_encode](dm_encode.md) · [dm_decode_modules](dm_decode_modules.md) · [dm_locate](dm_locate.md)

---
*Provenance: dmsym.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
