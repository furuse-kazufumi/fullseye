---
op: add_metrology_object_generic
dim: measure1d
category: model
in: metrologymodel
out: scalar
examples: [poc_dimensional_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# add_metrology_object_generic — MEASURE1D `model` op

- **データ種**: `metrologymodel` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.add_metrology_object_generic(model, otype, params, n: 'int' = 40) -> 'int'` (実装を直接呼ぶなら `import metrology; metrology.add_metrology_object_generic(model, otype, params, n: 'int' = 40) -> 'int'`、台帳から引くなら `opsmeasure1d.get("add_metrology_object_generic")`)

## 使い方

汎用計測オブジェクトを追加(add_metrology_object_generic)。

形状の種類を文字列で指定する入口。``otype`` と ``params`` の組は専用 op と
同じ並びでなければならない:

- ``"line"``: ``(row1, col1, row2, col2)``
- ``"circle"``: ``(row, col, radius)``
- ``"rect"``: ``(row, col, phi, l1, l2)``(``phi`` ラジアン、``l1``/``l2`` 半辺長)
- ``"ellipse"``: ``(row, col, phi, ra, rb)``

``params`` は ``tuple`` にして積むだけで、**ここでは ``otype`` も要素数も検証
しない**。未知の ``otype`` は ``apply_metrology_model`` が ``ValueError`` で拒否し、
要素数が違えば同じく ``apply`` 時に展開で失敗する。設定ファイルから形状を
読み込むときは、積む前に上の表で確認すること。

- ``n``: サンプル数(既定 40。矩形は 4 辺に分配)。
- 返り値: 追加位置の index(0 始まり)。
- ``align_metrology_model`` は ``params[0]``/``params[1]`` を row/col として
  動かす(``"line"`` のみ ``[2]``/``[3]`` も)。

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

[create_metrology_model](create_metrology_model.md) · [add_metrology_object_line_measure](add_metrology_object_line_measure.md) · [add_metrology_object_circle_measure](add_metrology_object_circle_measure.md) · [add_metrology_object_rectangle2_measure](add_metrology_object_rectangle2_measure.md) · [add_metrology_object_ellipse_measure](add_metrology_object_ellipse_measure.md)

---
*Provenance: metrology.py — MEASURE1D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
