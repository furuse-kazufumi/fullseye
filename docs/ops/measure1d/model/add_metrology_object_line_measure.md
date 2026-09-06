---
op: add_metrology_object_line_measure
dim: measure1d
category: model
in: metrologymodel
out: scalar
examples: [poc_dimensional_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# add_metrology_object_line_measure — MEASURE1D `model` op

- **データ種**: `metrologymodel` → `scalar`
- **呼び出し**: `import metrology; metrology.add_metrology_object_line_measure(model, row1, col1, row2, col2, n: 'int' = 25) -> 'int'` (または `opsmeasure1d.get("add_metrology_object_line_measure")`)

## 使い方

直線計測オブジェクトを追加(add_metrology_object_line_measure)。index を返す。

参照線分 ``(row1, col1) → (row2, col2)`` [px] を ``model["objects"]`` に積む
(dict をその場で更新)。``apply_metrology_model`` はこの線分上に ``n`` 点を
等間隔(両端を含む)に置き、各点から **線分の法線方向** に短い測定線を張って
サブピクセルのエッジを探し、得た点に直線を最小二乗で当て直す。

- ``n``: サンプル点数(既定 25)。多いほどフィットは安定するが計測時間は比例。
- 端点が一致する(長さ ``< 1e-9``)線分は積めるが、``apply`` 時にサンプル 0 個
  → フィット失敗として ``params=None``、``rms=inf`` で返る(例外にはならない)。
- 引数の型・範囲はここでは検証しない(画像外の座標も積める。``apply`` 時に
  最近傍で外挿されるだけで例外は出ない)。
- 返り値: 追加したオブジェクトの index(0 始まり)。``apply`` の結果 list の
  同じ位置に ``type="line"`` の結果(``row1/col1/row2/col2/angle_deg``)が入る。

``align_metrology_model`` で平行移動するときは両端点が一緒に動く。

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

[create_metrology_model](create_metrology_model.md) · [add_metrology_object_circle_measure](add_metrology_object_circle_measure.md) · [add_metrology_object_rectangle2_measure](add_metrology_object_rectangle2_measure.md) · [add_metrology_object_ellipse_measure](add_metrology_object_ellipse_measure.md) · [add_metrology_object_generic](add_metrology_object_generic.md)

---
*Provenance: metrology.py — MEASURE1D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
