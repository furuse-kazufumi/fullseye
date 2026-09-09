---
op: translate_measure
dim: measure1d
category: caliper
in: measurehandle
out: measurehandle
examples: [poc_dimensional_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# translate_measure — MEASURE1D `caliper` op

- **データ種**: `measurehandle` → `measurehandle`
- **呼び出し**: `import fullseye as fs; fs.ledger.translate_measure(measure, drow, dcol)` (実装を直接呼ぶなら `import measuring1d; measuring1d.translate_measure(measure, drow, dcol)`、台帳から引くなら `opsmeasure1d.get("translate_measure")`)

## 使い方

測定オブジェクトを平行移動(translate_measure)。

``rows`` / ``cols`` に ``(drow, dcol)`` [px] を足した **浅い複製** を返す(入力の
dict は変えない)。``gen_measure_rectangle2`` の ``origin`` と ``gen_measure_arc``
の ``center`` も同じだけ動かすので、両端延長(``_extended_coords``)の幾何が
ずれない。``phi`` / ``dir`` / ``angles`` / ``radius`` / ``width`` / ``spacing`` は
そのまま ―― **回転や半径変更はしない**。

- ``measure``: ``gen_measure_rectangle2`` / ``gen_measure_arc`` の dict。
  ``rows`` / ``cols`` を持つ任意の dict でも動く(他キーは素通し)。
- ``drow``, ``dcol``: 変位 [px]。小数可。
- ``shape``(画像サイズ)は再検査しないので、画像外へ出しても例外は出ず、
  ``measure_pos`` が端の値で外挿するだけになる。
- 返り値: 同じ構造の dict(``measurehandle`` 型)。

典型: 位置合わせで得たワークのずれを測定線に反映してから ``measure_pos`` /
``measure_pairs`` を掛ける。傾きが変わる場合は ``gen_measure_rectangle2`` を
新しい ``phi`` で作り直す。

## 詳しい使い方ガイド

- [subpixel_measuring ファミリ ガイド](../guides/subpixel_measuring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dimensional_inspection](../../../../examples/poc_dimensional_inspection.py) — `py -3.11 examples/poc_dimensional_inspection.py`

## 型が繋がる次の op(`measurehandle` を入力に取れる)

[measure_pos](measure_pos.md) · [measure_pairs](measure_pairs.md) · [fuzzy_measure_pairing](fuzzy_measure_pairing.md)

## 同カテゴリ(`caliper`)

[gen_measure_rectangle2](gen_measure_rectangle2.md) · [gen_measure_arc](gen_measure_arc.md) · [measure_pos](measure_pos.md) · [measure_pairs](measure_pairs.md) · [fuzzy_measure_pairing](fuzzy_measure_pairing.md)

---
*Provenance: measuring1d.py — MEASURE1D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
