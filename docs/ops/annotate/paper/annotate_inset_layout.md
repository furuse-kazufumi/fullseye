---
op: annotate_inset_layout
dim: annotate
category: paper
in: 
out: table
examples: [paper_figure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# annotate_inset_layout — ANNOTATE `paper` op

- **データ種**: `` → `table`
- **呼び出し**: `import annotate; annotate.annotate_inset_layout(shape, src_rect, corner='rt', factor=None, margin=10, max_fraction=0.4)` (または `opsannotate.get("annotate_inset_layout")`)

## 使い方

table(dict)を返す: 拡大差し込みの置き場所と倍率を閉形式で決める。

``factor=None`` なら「幅・高さとも画像の ``max_fraction`` 以下」で最大の
整数倍率。差し込みが元枠に重なる隅は ValueError(自分の元を隠す)。

Returns
-------
dict
    ``{"src_rect","dst_rect","factor","corner"}``。

Raises
------
ValueError
    元枠が画像外、倍率 < 1 か非整数、差し込みが収まらない/元枠と重なる。

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

[annotate_leader_layout](annotate_leader_layout.md) · [annotate_leader](annotate_leader.md) · [annotate_markers](annotate_markers.md) · [annotate_legend](annotate_legend.md) · [annotate_dimension_layout](annotate_dimension_layout.md) · [annotate_dimension](annotate_dimension.md) · [annotate_angle_layout](annotate_angle_layout.md) · [annotate_angle](annotate_angle.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
