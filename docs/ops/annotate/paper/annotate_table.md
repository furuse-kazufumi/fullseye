---
op: annotate_table
dim: annotate
category: paper
in: image2d × text
out: image2d
examples: [annotate_paper_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# annotate_table — ANNOTATE `paper` op

- **データ種**: `image2d × text` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.annotate_table(img, text, xy, anchor='lt', font_size=13, color='neutral', text_color=None, box_color=None, box_alpha=0.72, pad=6, col_gap=None, row_gap=0, align='auto', header=False, grid=False, border=0, border_color=None, font_path=None, scheme='okabe_ito', min_contrast=2.0, bold=False, italic=False, line_spacing=1.15, style=None, layout=None)` (実装を直接呼ぶなら `import annotate; annotate.annotate_table(img, text, xy, anchor='lt', font_size=13, color='neutral', text_color=None, box_color=None, box_alpha=0.72, pad=6, col_gap=None, row_gap=0, align='auto', header=False, grid=False, border=0, border_color=None, font_path=None, scheme='okabe_ito', min_contrast=2.0, bold=False, italic=False, line_spacing=1.15, style=None, layout=None)`、台帳から引くなら `opsannotate.get("annotate_table")`)

## 使い方

画像(image2d)を返す: タブ区切りの文字列を**表**として描く(半透明の板つき)。

桁幅は :func:`annotate_table_layout` が実フォントで測って決める。既定の
桁間は行高の 0.6 倍なので、``font_size`` を変えれば間隔も一緒に動く。
板は既定で半透明(``box_alpha=0.72``、0 で板なし)。

Parameters
----------
box_alpha : float
    板の不透明度 [0,1]。**0 で板を描かない**。半透明にすると下の絵が
    透けるので、文字色は「実際に下に出る色」に対して検査される。
grid : bool
    真なら桁と行の境に薄い罫を引く。既定は引かない(罫の無い表のほうが
    読みやすいことが多く、必要なときだけ足せばよい)。
header : bool
    真なら 1 行目を太字にし、下に罫を 1 本引く。
align : str or sequence
    :data:`TABLE_ALIGNS`。既定 ``"auto"`` は数の桁だけ右そろえ。
layout : dict or None
    :func:`annotate_table_layout` の返りを渡すと再計算しない。
    **渡した場合、``anchor`` などは無視される**(両方渡さないこと)。

Returns
-------
(H,W[,C]) float64
    表を描いた複製。**入力は書き換えない**。

Raises
------
ValueError
    :func:`annotate_table_layout` と同じ + 表が画像からはみ出す +
    文字が下地に対して ``min_contrast`` を割る(**黙って切らない**)。

Examples
--------
>>> import numpy as np, annotate
>>> img = np.zeros((120, 260, 3))
>>> out = annotate.annotate_table(img, "項目\t値\n面積\t12.5\n周長\t9.75",
...                               (10, 10), header=True)
>>> out.shape
(120, 260, 3)
>>> float(np.abs(out - img).max()) > 0.1
True

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

## 型が繋がる次の op(`image2d` を入力に取れる)

[text_box](../text/text_box.md) · [arrow](../pointer/arrow.md) · [leader_line](../pointer/leader_line.md) · [label_points](../pointer/label_points.md) · [crosshair](../pointer/crosshair.md) · [legend_box](../furniture/legend_box.md) · [color_bar](../furniture/color_bar.md) · [scale_bar](../furniture/scale_bar.md)

## 同カテゴリ(`paper`)

[annotate_leader_layout](annotate_leader_layout.md) · [annotate_leader](annotate_leader.md) · [annotate_markers](annotate_markers.md) · [annotate_legend](annotate_legend.md) · [annotate_dimension_layout](annotate_dimension_layout.md) · [annotate_dimension](annotate_dimension.md) · [annotate_angle_layout](annotate_angle_layout.md) · [annotate_angle](annotate_angle.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
