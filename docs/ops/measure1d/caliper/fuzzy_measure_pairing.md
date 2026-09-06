---
op: fuzzy_measure_pairing
dim: measure1d
category: caliper
in: image2d × measurehandle
out: table
examples: [poc_dimensional_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# fuzzy_measure_pairing — MEASURE1D `caliper` op

- **データ種**: `image2d × measurehandle` → `table`
- **呼び出し**: `import measuring1d; measuring1d.fuzzy_measure_pairing(image, measure, sigma=1.0, threshold=0.1, pair_size=None)` (または `opsmeasure1d.get("fuzzy_measure_pairing")`)

## 使い方

ファジィ基準(想定幅 pair_size)に最も合うエッジ対を選ぶ(fuzzy_measure_pairing)。

## 詳しい使い方ガイド

- [subpixel_measuring ファミリ ガイド](../guides/subpixel_measuring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dimensional_inspection](../../../../examples/poc_dimensional_inspection.py) — `py -3.11 examples/poc_dimensional_inspection.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`caliper`)

[gen_measure_rectangle2](gen_measure_rectangle2.md) · [gen_measure_arc](gen_measure_arc.md) · [translate_measure](translate_measure.md) · [measure_pos](measure_pos.md) · [measure_pairs](measure_pairs.md)

---
*Provenance: measuring1d.py — MEASURE1D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
