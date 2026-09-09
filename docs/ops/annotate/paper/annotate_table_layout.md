---
op: annotate_table_layout
dim: annotate
category: paper
in: text
out: table
examples: [annotate_paper_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# annotate_table_layout — ANNOTATE `paper` op

- **データ種**: `text` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.annotate_table_layout(text, xy, anchor='lt', font_size=13, font_path=None, pad=6, col_gap=None, row_gap=0, align='auto', header=False, bold=False, italic=False, line_spacing=1.15)` (実装を直接呼ぶなら `import annotate; annotate.annotate_table_layout(text, xy, anchor='lt', font_size=13, font_path=None, pad=6, col_gap=None, row_gap=0, align='auto', header=False, bold=False, italic=False, line_spacing=1.15)`、台帳から引くなら `opsannotate.get("annotate_table_layout")`)

## 使い方

table(dict)を返す: タブ区切りの文字列を**表**として置く桁と行の位置。

行は ``\n``、桁は ``\t`` で切る。桁幅は**指定されたサイズの実フォントで
1 セルずつ測った幅の最大**で決まる —— 文字数で数えると和文と英数字で
必ずずれるので、測る以外に正しくやりようがない。

Parameters
----------
text : str
    タブ区切り。全行の桁数が同じであること(違えば **ValueError**)。
xy : (x, y)
    ``anchor`` で指す位置(**x=col, y=row**)。
anchor : str
    ``'lt','ct','rt','lm','cm','rm','lb','cb','rb'`` の 9 通り。
pad : int
    表の内側余白 [px]。
col_gap : int or None
    桁の間 [px]。**None(既定)なら行高 ×0.6 を四捨五入**するので、
    フォントサイズを変えれば間隔も一緒に動く。
row_gap : int
    行の間に足す [px] (0 なら行送りのまま)。
align : str or sequence
    :data:`TABLE_ALIGNS` のいずれか、または桁ごとの並び。``"auto"``
    (既定)は**その桁の値がすべて数に見えるときだけ右そろえ**にする。
    ``header=True`` なら見出し行は判定から外す。
header : bool
    真なら 1 行目を見出しとして**太字**にし、下に罫を 1 本引く。
bold, italic : bool or int
    合成字体(:func:`_bold_px` / :func:`_italic_tile`)。``header`` の
    太字はこれとは別で、見出し行にだけ掛かる。

Returns
-------
dict
    ``{"rect": (x,y,w,h), "ncols", "nrows", "col_w": [...], "col_x": [...],
    "row_y": [...], "row_h", "col_gap", "align": [...], "header",
    "rule_y": 見出しの罫の y(header が偽なら None),
    "cells": [{"text","row","col","xy","width","bold"}]}``。
    ``col_x`` / ``row_y`` / ``cells[i]["xy"]`` はすべて**画像座標**。

Raises
------
ValueError
    桁数が行でそろわない / 空 / 未知の ``align`` ``anchor`` /
    ``align`` の長さが桁数と違う。

Examples
--------
>>> import annotate
>>> lay = annotate.annotate_table_layout("名前\t値\nA\t1.5\nB\t22.25", (10, 10))
>>> lay["ncols"], lay["nrows"], lay["align"]
(2, 3, ['left', 'left'])
>>> lay2 = annotate.annotate_table_layout("名前\t値\nA\t1.5\nB\t22.25", (10, 10),
...                                       header=True)
>>> lay2["align"]                        # 見出しを外すと 2 桁目は数だけ
['left', 'right']

## 詳しい使い方ガイド

- [figure_annotation ファミリ ガイド](../guides/figure_annotation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [dataset_conventions](../guides/dataset_conventions.md) — 学習データセット規約の知識 — COCO / YOLO / VOC と外観検査での落とし穴

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [annotate_paper_tour](../../../../examples/annotate_paper_tour.py) — `py -3.11 examples/annotate_paper_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`paper`)

[annotate_leader_layout](annotate_leader_layout.md) · [annotate_leader](annotate_leader.md) · [annotate_markers](annotate_markers.md) · [annotate_legend](annotate_legend.md) · [annotate_dimension_layout](annotate_dimension_layout.md) · [annotate_dimension](annotate_dimension.md) · [annotate_angle_layout](annotate_angle_layout.md) · [annotate_angle](annotate_angle.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
