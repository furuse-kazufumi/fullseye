---
op: measure_pairs
dim: measure1d
category: caliper
in: image2d × measurehandle
out: table
examples: [example_scratch_width, poc_dimensional_inspection, poc_weld_radiograph_porosity]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.0  # fullseye lib version this note was generated for
---

# measure_pairs — MEASURE1D `caliper` op

- **データ種**: `image2d × measurehandle` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.measure_pairs(image, measure, sigma=1.0, threshold=0.1)` (実装を直接呼ぶなら `import measuring1d; measuring1d.measure_pairs(image, measure, sigma=1.0, threshold=0.1)`、台帳から引くなら `opsmeasure1d.get("measure_pairs")`)

## 使い方

立ち上がり/立ち下がりエッジのペア(構造の幅)を抽出(measure_pairs)。
``first``/``second`` = 各エッジの ``pos``、``width`` = 幅 [px]、
``first_point``/``second_point`` = (row, col)。

**失敗と信頼度は返さない**(対が無ければ空 list、危険域でも対を返す)。
エッジ間距離 / PSF 幅が 3.09 を切ると幅は必ず大きい側へ偏り(2.06 で +2.43 px)、
1.58 まで「対が見つかった」と答え続ける —— 実測と見張り方は
``docs/ops/measure1d/guides/subpixel_measuring.md`` の「落とし穴 2」。極性の
順序も問わない(暗い構造の幅が返ることがある。同 §4)。単位は px なので、
mm が要るときは ``table_px_to_mm`` / ``pixel_to_world`` に渡す。

## 詳しい使い方ガイド

- [subpixel_measuring ファミリ ガイド](../guides/subpixel_measuring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [example_scratch_width](../../../../examples/example_scratch_width.py) — `py -3.11 examples/example_scratch_width.py`
- [poc_dimensional_inspection](../../../../examples/poc_dimensional_inspection.py) — `py -3.11 examples/poc_dimensional_inspection.py`
- [poc_weld_radiograph_porosity](../../../../examples/poc_weld_radiograph_porosity.py) — `py -3.11 examples/poc_weld_radiograph_porosity.py`

## 型が繋がる次の op(`table` を入力に取れる)

[table_px_to_mm](../scale/table_px_to_mm.md)

## 同カテゴリ(`caliper`)

[gen_measure_rectangle2](gen_measure_rectangle2.md) · [gen_measure_arc](gen_measure_arc.md) · [translate_measure](translate_measure.md) · [measure_pos](measure_pos.md) · [fuzzy_measure_pairing](fuzzy_measure_pairing.md)

---
*Provenance: measuring1d.py — MEASURE1D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
