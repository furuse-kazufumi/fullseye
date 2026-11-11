---
op: encode_barcode1d
dim: symbol
category: barcode1d
in: 
out: table
gpu: なし
examples: [poc_symbol_package_1d]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# encode_barcode1d — SYMBOL `barcode1d` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.encode_barcode1d(text, symbology='code128', *, wide_ratio=2.5, check_digit=False, gs1=False)` (実装を直接呼ぶなら `import barcode1d; barcode1d.encode_barcode1d(text, symbology='code128', *, wide_ratio=2.5, check_digit=False, gs1=False)`、台帳から引くなら `opssymbol.get("encode_barcode1d")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

文字列を 1 次元バーコードの要素幅(モジュール単位)へ符号化する(``table``)。

Encode ``text`` as a 1-D symbol. Returns a table: ``symbology``, ``text`` (the
human-readable data, e.g. EAN-13 with its check digit), ``widths`` (element widths
in modules, first element a bar, quiet zones excluded), ``quiet`` (left, right) in
modules, ``n_modules`` (symbol length without quiet zones), ``edges`` (cumulative
element boundaries starting at the left quiet-zone edge = 0), ``values`` (symbol
character values, Code 128 only) and ``wide_ratio`` (two-width symbologies).

``symbology``: ``"ean13"`` (12 or 13 digits; the 13th must be the check digit),
``"upca"`` (11 or 12 digits), ``"code128"`` (ASCII 32..126, automatic code sets
B / C; ``gs1=True`` puts FNC1 first and maps ``'\x1d'`` to FNC1 — GS1-128),
``"code39"`` (``0-9 A-Z - . space $ / + %``, start/stop ``*`` added, optional
mod-43 check with ``check_digit=True``), ``"itf"`` (an even number of digits;
``check_digit=True`` appends the GS1 mod-10 check to make the count even).
``wide_ratio`` (two-width symbologies) must lie in [2.0, 3.0].

空の入力(``text == ""``)は ``ValueError``(理由: 符号化する中身が無い)。
拒否(``ValueError``): 文字列でない、未知のシンボル体系、字種の外の文字、桁数違い、
検査数字の不一致、``wide_ratio`` が [2.0, 3.0] の外。

## 詳しい使い方ガイド

- [symbol_reading ファミリ ガイド](../guides/symbol_reading.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_symbol_package_1d](../../../../examples/poc_symbol_package_1d.py) — `py -3.11 examples/poc_symbol_package_1d.py`

## 型が繋がる次の op(`table` を入力に取れる)

[render_symbol](../symbol_capture/render_symbol.md) · [symbol_read_trials](../read_pod/symbol_read_trials.md) · [symbol_read_pod](../read_pod/symbol_read_pod.md) · [ocr_classify](../ocr/ocr_classify.md) · [ocr_read_line](../ocr/ocr_read_line.md) · [ocr_read_trials](../ocr/ocr_read_trials.md)

## 同カテゴリ(`barcode1d`)

[ean_check_digit](ean_check_digit.md) · [barcode_scan_profiles](barcode_scan_profiles.md) · [decode_barcode_profile](decode_barcode_profile.md) · [read_barcode1d](read_barcode1d.md)

---
*Provenance: barcode1d.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
