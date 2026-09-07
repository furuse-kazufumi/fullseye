---
op: add_metrology_object_ellipse_measure
dim: measure1d
category: model
in: metrologymodel
out: scalar
examples: [poc_dimensional_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# add_metrology_object_ellipse_measure — MEASURE1D `model` op

- **データ種**: `metrologymodel` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.add_metrology_object_ellipse_measure(model, row, col, phi, ra, rb, n: 'int' = 40) -> 'int'` (実装を直接呼ぶなら `import metrology; metrology.add_metrology_object_ellipse_measure(model, row, col, phi, ra, rb, n: 'int' = 40) -> 'int'`、台帳から引くなら `opsmeasure1d.get("add_metrology_object_ellipse_measure")`)

## 使い方

楕円計測オブジェクトを追加(add_metrology_object_ellipse_measure)。
``phi`` = ``ra`` 軸の向き(col 軸から、ラジアン)。

参照楕円(中心 ``(row, col)`` [px]、``phi`` 方向の半径 ``ra``、直交方向の半径
``rb``)を ``model["objects"]`` に積む(dict をその場で更新)。
``apply_metrology_model`` はパラメータ角 ``t`` を ``n`` 等分した点を置き
(弧長等分ではないので、扁平な楕円では長軸端が密になる)、各点で楕円の
外向き法線 ``∇F`` に沿ってエッジを測り、楕円フィットで出し直す。

- ``phi``: col 軸(x)から row 軸(画像下向き)へ測ったラジアン
  (矩形の ``phi`` と同じ規約)。
- ``ra``, ``rb``: 半径 [px]。0 を入れると法線計算で 0 除算になるので避ける
  (ここでは検証しない)。
- ``n``: サンプル数(既定 40)。
- 返り値: 追加位置の index(0 始まり)。
- ``apply`` 結果の ``params`` は ``row / col / phi / ra / rb`` で **``ra >= rb``
  (長軸が ``ra``)** に正規化され、``rms`` は代数残差ではなく中心からの
  半径方向の幾何残差 [px]。

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

[create_metrology_model](create_metrology_model.md) · [add_metrology_object_line_measure](add_metrology_object_line_measure.md) · [add_metrology_object_circle_measure](add_metrology_object_circle_measure.md) · [add_metrology_object_rectangle2_measure](add_metrology_object_rectangle2_measure.md) · [add_metrology_object_generic](add_metrology_object_generic.md)

---
*Provenance: metrology.py — MEASURE1D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
