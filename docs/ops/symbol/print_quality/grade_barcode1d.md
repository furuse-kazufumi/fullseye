---
op: grade_barcode1d
dim: symbol
category: print_quality
in: image2d
out: table
gpu: なし
examples: [poc_symbol_package_1d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# grade_barcode1d — SYMBOL `print_quality` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.grade_barcode1d(image, symbologies=None, *, n_scans=10, aperture_x=0.5, angle_deg=None, expected_text=None)` (実装を直接呼ぶなら `import symgrade; symgrade.grade_barcode1d(image, symbologies=None, *, n_scans=10, aperture_x=0.5, angle_deg=None, expected_text=None)`、台帳から引くなら `opssymbol.get("grade_barcode1d")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

画像の 1-D シンボルの印字品質の等級(``n_scans`` 本の走査線の平均)を返す(``table``)。

Grade a 1-D symbol in a reflectance image: read it (:func:`barcode1d.read_barcode1d`)
to find the bar direction and the module width X, filter the image with a
circular measuring aperture of ``aperture_x`` · X diameter (default 0.5 X), take
``n_scans`` profiles evenly over 10 %..90 % of the bar height and grade each
(:func:`grade_barcode_profile`). ``symbol_grade`` = mean of the profile grades
(0..4), ``letter`` its letter; ``parameters`` = per-parameter lists over the scans
and ``parameter_grade_mean`` their mean grades; ``limiting`` = the parameters that
most often set a profile's grade. With ``expected_text`` a profile that decodes to
a different string is graded 0 (``misread`` counts them) — a misread is worse than
a no-read.

限界 / limits: 開口は円(画素で積分)、反射率は画像の値そのまま。走査線は画像の端まで
伸ばし、各走査線で読めたシンボルの両側の静寂域 + 1 X だけを評価に使う。

空の入力は ``ValueError``。
拒否(``ValueError``): 2-D でない、非有限、``n_scans`` < 1、``aperture_x`` が
[0, 2] の外。シンボルが見つからなければ :class:`barcode1d.Barcode1DError`。

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

[grade_barcode_profile](grade_barcode_profile.md) · [grade_datacode2d](grade_datacode2d.md)

---
*Provenance: symgrade.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
