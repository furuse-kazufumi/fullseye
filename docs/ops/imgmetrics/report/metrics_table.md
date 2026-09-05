---
op: metrics_table
dim: imgmetrics
category: report
in: metrics
out: table
examples: [image_quality_metrics]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# metrics_table — IMGMETRICS `report` op

- **データ種**: `metrics` → `table`
- **呼び出し**: `import imgmetrics; imgmetrics.metrics_table(report, order=None)` (または `opsimgmetrics.get("metrics_table")`)

## 使い方

報告を ``(名前, 値)`` の表にする ―― 条件の行も**必ず一緒に**並べる。

数値だけの表を作れないようにしてあるのがこの op の主旨。``contract`` の
各項目が ``条件: <名前>`` として同じ表に入る。

## 詳しい使い方ガイド

- [image_difference_metrics ファミリ ガイド](../guides/image_difference_metrics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_quality_metrics](../../../../examples/image_quality_metrics.py) — `py -3.11 examples/image_quality_metrics.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`report`)

[compare_images](compare_images.md) · [measure_with](measure_with.md) · [data_range_of](data_range_of.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
