---
op: gen_measure_rectangle2
dim: measure1d
category: caliper
in: 
out: measurehandle
examples: [poc_dimensional_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# gen_measure_rectangle2 — MEASURE1D `caliper` op

- **データ種**: `なし` → `measurehandle`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import measuring1d; measuring1d.gen_measure_rectangle2(row, col, phi, length1, length2, shape)` (または `opsmeasure1d.get("gen_measure_rectangle2")`)

## 使い方

回転測定矩形(長軸 ``phi`` 方向に 1 px 間隔でプロファイルを取る)を定義
(gen_measure_rectangle2)。サンプル数 n = round(2*length1)+1、始点は
中心から -(n-1)/2 px の位置。``length2`` は幅方向の平均化幅 [px]。

## 詳しい使い方ガイド

- [subpixel_measuring ファミリ ガイド](../guides/subpixel_measuring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dimensional_inspection](../../../../examples/poc_dimensional_inspection.py) — `py -3.11 examples/poc_dimensional_inspection.py`

## 型が繋がる次の op(`measurehandle` を入力に取れる)

[translate_measure](translate_measure.md) · [measure_pos](measure_pos.md) · [measure_pairs](measure_pairs.md) · [fuzzy_measure_pairing](fuzzy_measure_pairing.md)

## 同カテゴリ(`caliper`)

[gen_measure_arc](gen_measure_arc.md) · [translate_measure](translate_measure.md) · [measure_pos](measure_pos.md) · [measure_pairs](measure_pairs.md) · [fuzzy_measure_pairing](fuzzy_measure_pairing.md)

---
*Provenance: measuring1d.py — MEASURE1D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
