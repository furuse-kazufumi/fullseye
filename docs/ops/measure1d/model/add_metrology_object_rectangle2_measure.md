---
op: add_metrology_object_rectangle2_measure
dim: measure1d
category: model
in: metrologymodel
out: scalar
examples: [poc_dimensional_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# add_metrology_object_rectangle2_measure — MEASURE1D `model` op

- **データ種**: `metrologymodel` → `scalar`
- **呼び出し**: `import metrology; metrology.add_metrology_object_rectangle2_measure(model, row, col, phi, l1, l2, n: 'int' = 40) -> 'int'` (または `opsmeasure1d.get("add_metrology_object_rectangle2_measure")`)

## 使い方

矩形計測オブジェクトを追加(add_metrology_object_rectangle2_measure)。
``phi`` = ``l1`` 辺の向き(col 軸から、ラジアン)、``l1``/``l2`` = 半辺長。

参照矩形(中心 ``(row, col)`` [px]、``phi`` 方向の半辺長 ``l1``、直交方向の
半辺長 ``l2``)を ``model["objects"]`` に積む(dict をその場で更新)。
``apply_metrology_model`` は 4 辺それぞれに ``max(2, n // 4)`` 点を **角を避けて**
等間隔に置き、各辺の外向き法線に沿ってエッジを測り、矩形フィットで
中心・向き・半辺長を出し直す。

- ``phi``: col 軸(x)から row 軸(画像下向き)へ測ったラジアン
  (``gen_measure_rectangle2`` と同じ規約)。
- ``l1``, ``l2``: 半辺長 [px] (全長ではない)。
- ``n``: 総サンプル数の目安(既定 40 → 各辺 10 点)。4 未満でも各辺 2 点は置く。
- 引数は検証しない。返り値は追加位置の index(0 始まり)。
- ``apply`` 結果の ``params`` は ``row / col / phi / l1 / l2`` で、再フィット後は
  **``l1 >= l2``(長辺が ``l1``)に並び替えられる** ―― 参照で ``l1 < l2`` と与えても
  結果の ``phi`` は長辺の向きになる。

## 詳しい使い方ガイド

- [subpixel_measuring ファミリ ガイド](../guides/subpixel_measuring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dimensional_inspection](../../../../examples/poc_dimensional_inspection.py) — `py -3.11 examples/poc_dimensional_inspection.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`model`)

[create_metrology_model](create_metrology_model.md) · [add_metrology_object_line_measure](add_metrology_object_line_measure.md) · [add_metrology_object_circle_measure](add_metrology_object_circle_measure.md) · [add_metrology_object_ellipse_measure](add_metrology_object_ellipse_measure.md) · [add_metrology_object_generic](add_metrology_object_generic.md)

---
*Provenance: metrology.py — MEASURE1D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
