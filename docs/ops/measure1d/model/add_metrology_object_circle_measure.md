---
op: add_metrology_object_circle_measure
dim: measure1d
category: model
in: metrologymodel
out: scalar
examples: [example_inner_diameter_mm, poc_dimensional_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.0  # fullseye lib version this note was generated for
---

# add_metrology_object_circle_measure — MEASURE1D `model` op

- **データ種**: `metrologymodel` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.add_metrology_object_circle_measure(model, row, col, radius, n: 'int' = 40) -> 'int'` (実装を直接呼ぶなら `import metrology; metrology.add_metrology_object_circle_measure(model, row, col, radius, n: 'int' = 40) -> 'int'`、台帳から引くなら `opsmeasure1d.get("add_metrology_object_circle_measure")`)

## 使い方

円計測オブジェクトを追加(add_metrology_object_circle_measure)。

参照円(中心 ``(row, col)``、半径 ``radius`` [px])を ``model["objects"]`` に積む
(dict をその場で更新)。``apply_metrology_model`` は円周を ``n`` 等分した角度に
点を置き、各点で **半径方向**(外向き法線)に測定線を張ってサブピクセルの
エッジを取り、最小二乗の円フィットで中心と半径を出し直す。

- ``radius``: 参照半径 [px]。実物とのずれは ``apply`` の ``measure_length``
  (既定 ±6 px)以内に収まっている必要がある ―― それより外のエッジは見つからない。
- ``n``: 円周のサンプル数(既定 40)。半径が大きい円ほど増やす。
- 引数はここでは検証しない(0 以下の半径も積めるが意味を持たない)。
- 返り値: 追加位置の index(0 始まり)。``apply`` 結果の ``params`` は
  ``row / col / radius``、``rms`` は円からの半径方向残差 [px]。

穴径・ピン径の検査、円形部品の中心出しに使う。

**``n`` の目安(2026-09-15 実測、ぼけ σ=1 px の合成円板)**: 偏りは n に依らない
(R=8〜128 px、n=6〜240 で ±0.005 px 以内で一定。偏り自体は縁の丸みで −0.09 →
−0.006 px と R に依る)。効くのは散らばりで、雑音 σ=0.03 のとき std·√n は
円周の標本間隔 2πR/n が **約 3 px 以上**なら一定(= 標本が独立、std ∝ 1/√n)、
それより密にしても下がらない(R=16: n=40 で 0.0174、n=240 で 0.0164 px)。
つまり ``n ≈ 2πR / 3``(R=20 で 40 = 既定、R=64 で 130、R=128 で 270)より
多くしても時間が増えるだけ(n=1000 で 22 ms)。円周の 25 % が欠けていると
n を増やしても偏りは直らない(−0.005 → −0.020 px)。欠けた側で縁が見つからない
だけなら ``rms`` はむしろ下がり(0.051 → 0.018)、欠けの境界で偽の縁を拾えば
rms が跳ねる —— **欠けは rms だけでは見えない**ので ``edge_points`` の本数も
門にする(``examples/example_inner_diameter_mm.py``)。参照半径のずれは
``measure_length``(既定 ±6 px)が上限で、+5.5 px は通り +6.5 px で
``params=None``。

## 詳しい使い方ガイド

- [subpixel_measuring ファミリ ガイド](../guides/subpixel_measuring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [example_inner_diameter_mm](../../../../examples/example_inner_diameter_mm.py) — `py -3.11 examples/example_inner_diameter_mm.py`
- [poc_dimensional_inspection](../../../../examples/poc_dimensional_inspection.py) — `py -3.11 examples/poc_dimensional_inspection.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`model`)

[create_metrology_model](create_metrology_model.md) · [add_metrology_object_line_measure](add_metrology_object_line_measure.md) · [add_metrology_object_rectangle2_measure](add_metrology_object_rectangle2_measure.md) · [add_metrology_object_ellipse_measure](add_metrology_object_ellipse_measure.md) · [add_metrology_object_generic](add_metrology_object_generic.md)

---
*Provenance: metrology.py — MEASURE1D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
