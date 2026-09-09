---
op: create_metrology_model
dim: measure1d
category: model
in: 
out: metrologymodel
examples: [poc_dimensional_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# create_metrology_model — MEASURE1D `model` op

- **データ種**: `なし` → `metrologymodel`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.create_metrology_model() -> 'dict'` (実装を直接呼ぶなら `import metrology; metrology.create_metrology_model() -> 'dict'`、台帳から引くなら `opsmeasure1d.get("create_metrology_model")`)

## 使い方

空の計測モデルを作る(create_metrology_model)。

返り値は ``{"objects": []}`` の dict(``metrologymodel`` 型)。ここに
``add_metrology_object_line_measure`` / ``..._circle_measure`` /
``..._rectangle2_measure`` / ``..._ellipse_measure`` / ``..._generic`` で
参照形状を積み、``apply_metrology_model(model, image)`` で一括計測する。

- 引数は無い。画像サイズや座標系はモデルに持たず、``apply`` 時の画像で決まる。
- 各 ``add_*`` は **この dict をその場で書き換え**、追加した位置(0 始まり)を
  返す。``apply_metrology_model`` の結果 list はこの順に並ぶ。
- ``align_metrology_model`` は書き換えず、平行移動した新しいモデルを返す。

座標は (row, col) [px]、角度 ``phi`` は col 軸から row 軸(画像下向き)へ測った
ラジアン。この規約はモデル全体で共通。

## 詳しい使い方ガイド

- [subpixel_measuring ファミリ ガイド](../guides/subpixel_measuring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dimensional_inspection](../../../../examples/poc_dimensional_inspection.py) — `py -3.11 examples/poc_dimensional_inspection.py`

## 型が繋がる次の op(`metrologymodel` を入力に取れる)

[add_metrology_object_line_measure](add_metrology_object_line_measure.md) · [add_metrology_object_circle_measure](add_metrology_object_circle_measure.md) · [add_metrology_object_rectangle2_measure](add_metrology_object_rectangle2_measure.md) · [add_metrology_object_ellipse_measure](add_metrology_object_ellipse_measure.md) · [add_metrology_object_generic](add_metrology_object_generic.md) · [align_metrology_model](../apply/align_metrology_model.md) · [apply_metrology_model](../apply/apply_metrology_model.md)

## 同カテゴリ(`model`)

[add_metrology_object_line_measure](add_metrology_object_line_measure.md) · [add_metrology_object_circle_measure](add_metrology_object_circle_measure.md) · [add_metrology_object_rectangle2_measure](add_metrology_object_rectangle2_measure.md) · [add_metrology_object_ellipse_measure](add_metrology_object_ellipse_measure.md) · [add_metrology_object_generic](add_metrology_object_generic.md)

---
*Provenance: metrology.py — MEASURE1D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
