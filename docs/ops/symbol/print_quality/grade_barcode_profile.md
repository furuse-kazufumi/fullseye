---
op: grade_barcode_profile
dim: symbol
category: print_quality
in: signal
out: table
gpu: なし
examples: [poc_symbol_package_1d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# grade_barcode_profile — SYMBOL `print_quality` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.grade_barcode_profile(profile, symbologies=None, *, quiet_zone_x=None)` (実装を直接呼ぶなら `import symgrade; symgrade.grade_barcode_profile(profile, symbologies=None, *, quiet_zone_x=None)`、台帳から引くなら `opssymbol.get("grade_barcode_profile")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

1 本の走査線(反射率の 1-D 列)の印字品質のパラメータと等級を返す(``table``)。

Grade one scan reflectance profile. The profile must cover the symbol and its
quiet zones. Quantities (reflectances in [0, 1]):

* ``r_max`` / ``r_min``: highest / lowest reflectance over the profile.
* ``symbol_contrast`` SC = r_max − r_min; global threshold GT = r_min + SC / 2.
* elements = runs between GT crossings; a space's reflectance is its maximum, a
  bar's its minimum; the quiet zones are the outer spaces.
* ``edge_contrast_min`` ECmin = min over adjacent element pairs of |Rs − Rb|.
* ``modulation`` MOD = ECmin / SC.
* ``defects`` = ERNmax / SC, where an element's reflectance non-uniformity ERN is
  the deepest valley trapped between two higher samples inside a space (or the
  highest peak trapped inside a bar) — monotone edges contribute nothing.
* ``decodability`` = the smallest per-character decode margin returned by the
  reference decode (:func:`barcode1d.decode_barcode_profile` at GT): for the
  edge-to-similar-edge symbologies (EAN/UPC, Code 128) the margin of each
  similar-edge sum from its decision boundary (half a module), for the two-width
  ones (Code 39, ITF) the margin of the narrowest wide / widest narrow element from
  the mid threshold, both scaled to 1 = ideal, 0 = on the boundary.
* ``decode`` (bool), ``quiet_zone_ok`` (both light zones at least the symbology's
  quiet zone, or ``quiet_zone_x`` X, wide), ``r_min_ok`` (Rmin ≤ 0.5 Rmax),
  ``edge_contrast_ok`` (ECmin ≥ 0.15).

Grades 4..0 per parameter (``grades``), ``profile_grade`` = the minimum, and
``limiting`` = the parameters at that minimum. A profile that does not decode is
graded 0 with ``decode = False`` (the other quantities are still reported when the
profile has edges).

空の入力(16 標本未満)は ``ValueError``。
拒否(``ValueError``): 1-D でない、非有限、``quiet_zone_x`` が負。平らな走査線
(縁が無い)は SC = 0 で ``profile_grade = 0``(読めない、と数える)。

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

## 同カテゴリ(`print_quality`)

[grade_barcode1d](grade_barcode1d.md) · [grade_datacode2d](grade_datacode2d.md)

---
*Provenance: symgrade.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
