---
op: measure_pos
dim: measure1d
category: caliper
in: image2d × measurehandle
out: table
examples: [poc_barcode_1d, poc_dimensional_inspection, poc_screw_thread_metrology, poc_solar_limb_darkening, poc_water_level, poc_weld_bead_profile, poc_weld_radiograph_porosity]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# measure_pos — MEASURE1D `caliper` op

- **データ種**: `image2d × measurehandle` → `table`
- **呼び出し**: `import measuring1d; measuring1d.measure_pos(image, measure, sigma=1.0, threshold=0.1, transition='all')` (または `opsmeasure1d.get("measure_pos")`)

## 使い方

測定線上のエッジ位置(サブピクセル)と振幅を抽出(measure_pos)。

各エッジ: ``pos``(サンプル index、矩形は始点からの px)/ ``dist``(始点からの
距離 [px])/ ``row``, ``col`` / ``amplitude``(符号つきグレー差)/ ``polarity``
("positive" = 測定方向に明るくなる)。``threshold`` は |amplitude| の下限、
``transition`` は "all" / "positive" / "negative"。

## 詳しい使い方ガイド

- [subpixel_measuring ファミリ ガイド](../guides/subpixel_measuring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_barcode_1d](../../../../examples/poc_barcode_1d.py) — `py -3.11 examples/poc_barcode_1d.py`
- [poc_dimensional_inspection](../../../../examples/poc_dimensional_inspection.py) — `py -3.11 examples/poc_dimensional_inspection.py`
- [poc_screw_thread_metrology](../../../../examples/poc_screw_thread_metrology.py) — `py -3.11 examples/poc_screw_thread_metrology.py`
- [poc_solar_limb_darkening](../../../../examples/poc_solar_limb_darkening.py) — `py -3.11 examples/poc_solar_limb_darkening.py`
- [poc_water_level](../../../../examples/poc_water_level.py) — `py -3.11 examples/poc_water_level.py`
- [poc_weld_bead_profile](../../../../examples/poc_weld_bead_profile.py) — `py -3.11 examples/poc_weld_bead_profile.py`
- [poc_weld_radiograph_porosity](../../../../examples/poc_weld_radiograph_porosity.py) — `py -3.11 examples/poc_weld_radiograph_porosity.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`caliper`)

[gen_measure_rectangle2](gen_measure_rectangle2.md) · [gen_measure_arc](gen_measure_arc.md) · [translate_measure](translate_measure.md) · [measure_pairs](measure_pairs.md) · [fuzzy_measure_pairing](fuzzy_measure_pairing.md)

---
*Provenance: measuring1d.py — MEASURE1D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
