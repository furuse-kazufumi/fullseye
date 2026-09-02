---
op: annotate_angle_layout
dim: annotate
category: paper
in: 
out: table
examples: [paper_figure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# annotate_angle_layout — ANNOTATE `paper` op

- **データ種**: `` → `table`
- **呼び出し**: `import annotate; annotate.annotate_angle_layout(a, vertex, b, radius=30.0, text_gap=12.0)` (または `opsannotate.get("annotate_angle_layout")`)

## 使い方

table(dict)を返す: 3 点 ``a, vertex, b`` のなす角(小さい方)の弧と文字位置。

角度は画面座標(x 右・y 下)で ``atan2`` から出すので、``start_deg``/``end_deg``
は :func:`arc` と同じ「x 軸から時計回り」の度。

Returns
-------
dict
    ``{"vertex","angle_deg","start_deg","end_deg","radius","text_xy",
    "bisector_deg"}``。

Raises
------
ValueError
    a か b が vertex と一致、非有限、radius が非正。

## 詳しい使い方ガイド

- [figure_annotation ファミリ ガイド](../guides/figure_annotation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [paper_figure](../../../../examples/paper_figure.py) — `py -3.11 examples/paper_figure.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`paper`)

[annotate_leader_layout](annotate_leader_layout.md) · [annotate_leader](annotate_leader.md) · [annotate_markers](annotate_markers.md) · [annotate_legend](annotate_legend.md) · [annotate_dimension_layout](annotate_dimension_layout.md) · [annotate_dimension](annotate_dimension.md) · [annotate_angle](annotate_angle.md) · [annotate_scale_bar_layout](annotate_scale_bar_layout.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
