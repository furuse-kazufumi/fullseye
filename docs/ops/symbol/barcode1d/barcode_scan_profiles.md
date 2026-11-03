---
op: barcode_scan_profiles
dim: symbol
category: barcode1d
in: image2d
out: table
gpu: なし
examples: [poc_symbol_package_1d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# barcode_scan_profiles — SYMBOL `barcode1d` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.barcode_scan_profiles(image, angle_deg=None, n_lines=10, *, band=(0.1, 0.9), step=0.5)` (実装を直接呼ぶなら `import barcode1d; barcode1d.barcode_scan_profiles(image, angle_deg=None, n_lines=10, *, band=(0.1, 0.9), step=0.5)`、台帳から引くなら `opssymbol.get("barcode_scan_profiles")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

画像から、縞に垂直な平行走査線を ``n_lines`` 本取り出す(``table``)。

Sample ``n_lines`` parallel scan lines perpendicular to the bars. The bar-normal
direction is ``angle_deg`` (degrees from the image x axis, counter-clockwise in
display = row up) or, if None, the dominant gradient direction of the structure
tensor. Lines are spaced evenly over the ``band`` fraction of the strong-gradient
region's extent along the bars (ISO-style 10 scans over 10 %..90 % of the height),
sampled every ``step`` pixels by bilinear interpolation over the whole image width.
Returns ``profiles`` (n_lines, L), ``angle_deg``, ``coherence`` (0..1, how
line-like the texture is), ``offsets`` (px across the bars), ``step`` and
``origin`` / ``direction`` / ``normal`` (row, col) so a profile sample ``s`` of line
``k`` maps to ``origin + offsets[k] * normal + s * step * direction``.

空の入力(8 画素未満の辺)は ``ValueError``。
拒否(``ValueError``): 2-D でない、非有限、``n_lines`` < 1、``band`` が (0, 1) の
昇順でない、``step`` <= 0。勾配の無い画像は :class:`Barcode1DError`。

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

[encode_barcode1d](encode_barcode1d.md) · [ean_check_digit](ean_check_digit.md) · [decode_barcode_profile](decode_barcode_profile.md) · [read_barcode1d](read_barcode1d.md)

---
*Provenance: barcode1d.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
