---
op: decode_barcode_profile
dim: symbol
category: barcode1d
in: signal
out: table
gpu: なし
examples: [poc_symbol_package_1d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# decode_barcode_profile — SYMBOL `barcode1d` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.decode_barcode_profile(profile, symbologies=None, *, threshold=None, itf_min_length=6)` (実装を直接呼ぶなら `import barcode1d; barcode1d.decode_barcode_profile(profile, symbologies=None, *, threshold=None, itf_min_length=6)`、台帳から引くなら `opssymbol.get("decode_barcode_profile")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

1 本の走査線(反射率の 1-D 列)からシンボルを 1 つ復号する(``table``)。

Decode one symbol from a scan reflectance profile (1-D, bars dark). The global
threshold is ``(max + min) / 2`` of the profile unless given (the same threshold
the print-quality grade uses). Elements come from sub-sample threshold crossings;
every run of bar-first elements flanked by light zones at least
``5 X`` wide (X estimated from the candidate itself) is tried with each symbology,
in both scan directions. Returns ``symbology``, ``text``, ``margins`` (per
character decode margin in [0, 1]: 1 = element sums exactly on the module grid,
0 = on the decision boundary), ``reversed`` (read right-to-left), ``x_dim``
(estimated module width in samples), ``start`` / ``stop`` (sample positions of
the first bar's leading edge and the last bar's trailing edge) and
``threshold``.

限界 / limits: 1 本の走査線に 1 シンボル(最初に一致したもの)。静寂域が 5 X より
狭いと探さない。Code 128 の FNC2-4・シフト・コード A の制御文字は読まない。

★ITF は検査数字を持たず、ぼけた他のシンボルの一部が短い ITF に化ける(短読み、
short read)。``itf_min_length``(既定 6 桁)未満の ITF は返さない。実測: EAN-13 を
デフォーカスで壊すと、全体系を許した読み取りは 2 桁の ITF などを**誤読**として返した
(``tests/test_barcode1d.py``)。現場の読み取り器と同じく、``symbologies`` は使う体系
だけに絞ること。
ITF has no check digit; fragments of a blurred symbol decode as short ITF. ITF reads
shorter than ``itf_min_length`` are refused; restrict ``symbologies`` to what the
line uses.

空の入力は ``ValueError``(16 標本未満は「シンボルを含めない」)。
拒否(``ValueError``): 1-D でない、非有限、未知の体系名。どの体系とも一致しなければ
:class:`Barcode1DError`(``ValueError`` の派生)—— **誤読より読み取り不能を選ぶ**
(検査数字・開始停止・ガードの照合を全部通ったものだけ返す)。

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

[encode_barcode1d](encode_barcode1d.md) · [ean_check_digit](ean_check_digit.md) · [barcode_scan_profiles](barcode_scan_profiles.md) · [read_barcode1d](read_barcode1d.md)

---
*Provenance: barcode1d.py — SYMBOL operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
