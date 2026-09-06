---
op: align_metrology_model
dim: measure1d
category: apply
in: metrologymodel
out: metrologymodel
examples: [poc_dimensional_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# align_metrology_model — MEASURE1D `apply` op

- **データ種**: `metrologymodel` → `metrologymodel`
- **呼び出し**: `import metrology; metrology.align_metrology_model(model, drow=0.0, dcol=0.0) -> 'dict'` (または `opsmeasure1d.get("align_metrology_model")`)

## 使い方

計測モデルの全オブジェクトを平行移動して整列(align_metrology_model)。

## 詳しい使い方ガイド

- [subpixel_measuring ファミリ ガイド](../guides/subpixel_measuring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dimensional_inspection](../../../../examples/poc_dimensional_inspection.py) — `py -3.11 examples/poc_dimensional_inspection.py`

## 型が繋がる次の op(`metrologymodel` を入力に取れる)

[add_metrology_object_line_measure](../model/add_metrology_object_line_measure.md) · [add_metrology_object_circle_measure](../model/add_metrology_object_circle_measure.md) · [add_metrology_object_rectangle2_measure](../model/add_metrology_object_rectangle2_measure.md) · [add_metrology_object_ellipse_measure](../model/add_metrology_object_ellipse_measure.md) · [add_metrology_object_generic](../model/add_metrology_object_generic.md) · [apply_metrology_model](apply_metrology_model.md)

## 同カテゴリ(`apply`)

[apply_metrology_model](apply_metrology_model.md)

---
*Provenance: metrology.py — MEASURE1D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
