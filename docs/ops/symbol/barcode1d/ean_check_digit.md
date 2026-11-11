---
op: ean_check_digit
dim: symbol
category: barcode1d
in: 
out: scalar
gpu: なし
examples: [poc_symbol_package_1d]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# ean_check_digit — SYMBOL `barcode1d` op

- **データ種**: `なし` → `scalar`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.ean_check_digit(digits: 'str') -> 'int'` (実装を直接呼ぶなら `import barcode1d; barcode1d.ean_check_digit(digits: 'str') -> 'int'`、台帳から引くなら `opssymbol.get("ean_check_digit")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

EAN/UPC の検査数字(右端の桁から重み 3, 1, 3, …、和を 10 の倍数に)/ EAN/UPC check digit.

## 詳しい使い方ガイド

- [symbol_reading ファミリ ガイド](../guides/symbol_reading.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_symbol_package_1d](../../../../examples/poc_symbol_package_1d.py) — `py -3.11 examples/poc_symbol_package_1d.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`barcode1d`)

[encode_barcode1d](encode_barcode1d.md) · [barcode_scan_profiles](barcode_scan_profiles.md) · [decode_barcode_profile](decode_barcode_profile.md) · [read_barcode1d](read_barcode1d.md)

---
*Provenance: barcode1d.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
