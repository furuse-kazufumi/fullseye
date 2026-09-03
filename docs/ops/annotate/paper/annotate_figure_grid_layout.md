---
op: annotate_figure_grid_layout
dim: annotate
category: paper
in: 
out: table
examples: [paper_figure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# annotate_figure_grid_layout — ANNOTATE `paper` op

- **データ種**: `` → `table`
- **呼び出し**: `import annotate; annotate.annotate_figure_grid_layout(shapes, ncols=2, pad=10, caption_h=32, title_h=0, letter_style='paren')` (または `opsannotate.get("annotate_figure_grid_layout")`)

## 使い方

table(dict)を返す: 多パネル図の組版(セル・パネル・見出し帯の矩形)を閉形式で。

:func:`panel_grid` と同じ式: ``cw/ch`` は最大パネル寸、
``W = 2*pad + ncols*cw + (ncols-1)*pad``、
``H = title_h + 2*pad + nrows*(ch+caption_h) + (nrows-1)*pad``。
パネルは拡大せずセルの中央に置く。

Returns
-------
dict
    ``{"size":(H,W), "cells":[(x,y,cw,ch)], "panels":[(x,y,w,h)],
    "captions":[(x,y,cw,caption_h)], "letters":[str], "ncols", "nrows"}``。

Raises
------
ValueError
    shapes が空、ncols < 1、負の余白、26 枚を超える。

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
