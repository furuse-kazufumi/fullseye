---
op: grade_datacode2d
dim: symbol
category: print_quality
in: image2d
out: table
gpu: なし
examples: [poc_symbol_part_dpm]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# grade_datacode2d — SYMBOL `print_quality` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.grade_datacode2d(image, symbology='auto', *, aperture_x=0.8, expected_text=None)` (実装を直接呼ぶなら `import symgrade; symgrade.grade_datacode2d(image, symbology='auto', *, aperture_x=0.8, expected_text=None)`、台帳から引くなら `opssymbol.get("grade_datacode2d")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

画像の 2-D シンボル(QR / DataMatrix)の印字品質の等級を返す(``table``)。

Grade a QR Code or Data Matrix in a reflectance image. The symbol is read
(``qrsym.qr_read`` / ``dmsym.dm_read``), the image is filtered with a circular
measuring aperture of ``aperture_x`` · X (default 0.8 X) and sampled at every module
centre through the reader's homography, plus a one-module ring of quiet zone.

* ``symbol_contrast`` SC = Rmax − Rmin over those samples; GT = Rmin + SC / 2.
* module modulation ``2·|R − GT| / SC``; a module on the wrong side of GT (compared
  with the *ideal* module rebuilt from the decoded data) is graded 0. A codeword's
  grade is its worst module; the ``modulation`` grade is the highest level L such that
  the codewords graded below L, counted as errors, still leave unused error
  correction of grade ≥ L in every block (the error-correction rule of the 2-D
  method, as publicly described).
* ``fixed_pattern_damage``: the worst module grade over the fixed patterns (QR:
  finders, separators, timing, alignment; Data Matrix: the L finder, the clock track
  and alignment patterns) and the quiet-zone ring. ★Simplified: one dull module of a
  finder limits it (the published method grades finder segments separately).
* the grid: the reader's homography is re-fitted (normalised DLT, twice) to every
  module edge measured along all rows and columns (sub-sample GT crossings within
  0.45 module of an ideal dark/light boundary), so that the reader's own fit error is
  not graded as print non-uniformity (``grid_refined``).
* ``axial_nonuniformity`` = |X̄ − Ȳ| / ((X̄ + Ȳ)/2) of the mean module pitch along
  the two grid axes in pixels (the fitted grid: a tilt about one axis shows up here).
* ``grid_nonuniformity`` = the largest distance (modules) between a timing-pattern
  module centre located from its own edges and the fitted projective grid.
* ``unused_error_correction`` = min over blocks of ``1 − 2·e / (n_ec − p)`` with the
  decoder's corrected-codeword count ``e`` and the misdecode-protection codewords
  ``p`` (QR 1-L/M/Q, 2-L, 3-L; 0 for Data Matrix).
* ``decode``: 4 if read (and equal to ``expected_text`` when given), else 0.

``overall_grade`` = the minimum parameter grade (0..4), ``letter``, ``limiting``.
``ideal_source`` says how the ideal modules were obtained (``"reencode"``: the
decoded text re-encoded with the same version / level / mask / mode reproduced the
read; ``"codewords"`` (Data Matrix): rebuilt from the corrected codewords;
``"sampled"``: neither was possible, the thresholded samples stand in and wrong-side
modules cannot be seen — ``modulation`` is then optimistic, flagged).

限界 / limits: 反射率は画像の値のまま、開口は円。Data Matrix 144x144 の不揃いな
ブロックのブロック割り当ては近似。鏡像の QR は読み取り器の格子(転置)で採点する。

空の入力は ``ValueError``。
拒否(``ValueError``): 2-D でない、非有限、未知の ``symbology``、``aperture_x`` が
[0, 2] の外。**読めないシンボル**は例外にせず ``overall_grade = 0``、``decode = False``
(検証器が F を付けるのと同じ。読めない理由は ``error``)。

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

## 同カテゴリ(`print_quality`)

[grade_barcode_profile](grade_barcode_profile.md) · [grade_barcode1d](grade_barcode1d.md)

---
*Provenance: symgrade.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
