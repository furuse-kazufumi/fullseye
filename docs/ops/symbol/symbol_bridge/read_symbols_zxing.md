---
op: read_symbols_zxing
dim: symbol
category: symbol_bridge
in: image2d
out: table
gpu: なし
examples: [poc_symbol_package_1d, poc_symbol_part_dpm]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# read_symbols_zxing — SYMBOL `symbol_bridge` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.read_symbols_zxing(image, formats=None, *, try_rotate=True, try_invert=True)` (実装を直接呼ぶなら `import symzxing; symzxing.read_symbols_zxing(image, formats=None, *, try_rotate=True, try_invert=True)`、台帳から引くなら `opssymbol.get("read_symbols_zxing")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

zxing-cpp で画像の記号(1-D / 2-D)を全部読む(``table``)。

Read every symbol zxing-cpp finds in a 2-D reflectance image (values in [0, 1],
converted to 8-bit). ``formats`` is None (all) or a list of zxing format names
(``"QRCode"``, ``"DataMatrix"``, ``"EAN13"``, ``"Code128"`` …). Returns ``n``,
``texts``, ``formats``, ``positions`` (4 corners (row, col) per symbol, top-left
first as zxing reports them), ``valid`` and ``reader`` = ``"zxing-cpp <version>"``.

空の入力(辺が 0)は ``ValueError``。
拒否(``ValueError``): 2-D でない、非有限、値が [0, 1] の外、未知の形式名。
zxing-cpp が入っていなければ ``ImportError``(fail-closed、``pip install zxing-cpp``)。
何も見つからなければ ``n = 0``(読めないことは例外ではなく結果)。

## 詳しい使い方ガイド

- [symbol_reading ファミリ ガイド](../guides/symbol_reading.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_symbol_package_1d](../../../../examples/poc_symbol_package_1d.py) — `py -3.11 examples/poc_symbol_package_1d.py`
- [poc_symbol_part_dpm](../../../../examples/poc_symbol_part_dpm.py) — `py -3.11 examples/poc_symbol_part_dpm.py`

## 型が繋がる次の op(`table` を入力に取れる)

[render_symbol](../symbol_capture/render_symbol.md) · [symbol_read_trials](../read_pod/symbol_read_trials.md) · [symbol_read_pod](../read_pod/symbol_read_pod.md) · [ocr_classify](../ocr/ocr_classify.md) · [ocr_read_line](../ocr/ocr_read_line.md) · [ocr_read_trials](../ocr/ocr_read_trials.md)

## 同カテゴリ(`symbol_bridge`)

—

---
*Provenance: symzxing.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
