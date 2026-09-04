---
op: annotate_leader_layout
dim: annotate
category: paper
in: 
out: table
examples: [paper_figure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# annotate_leader_layout — ANNOTATE `paper` op

- **データ種**: `` → `table`
- **呼び出し**: `import annotate; annotate.annotate_leader_layout(shape, points, labels=None, font_size=12, pad=4, gap=22, side='auto', font_path=None, min_font_size=9)` (または `opsannotate.get("annotate_leader_layout")`)

## 使い方

table(dict)を返す: 引き出し線の配置(肘・文字位置・板の矩形)を閉形式で決める。

各点について候補側を固定順に試し、**板が画像に収まり・他の板と重ならず・
他の点を覆わない**最初の候補を採る。どの候補も駄目なら肘を 1.6 倍、2.4 倍に
伸ばして再試行し、それでも駄目なら **ValueError**(黙って重ねない)。

Parameters
----------
shape : (H, W)
    描く画像の大きさ。
points : (N, 2)
    指す点 **(x, y)**。
labels : sequence of str or None
    各点の文字。None なら 1 始まりの番号。
gap : float
    肘の長さ[px]。斜め腕 = gap、水平腕 = 0.6*gap。
side : {'auto','left','right'}
    ``'auto'`` は画像中心から**遠ざかる**側を先に試す(対象の上に文字を
    載せないため)。

Returns
-------
dict
    ``{"n", "gap", "items": [{"point", "elbow", "text_xy", "anchor",
    "box", "side"}]}``。``box`` は板の ``(x, y, w, h)``。

Raises
------
ValueError
    点が空・非有限、labels の数が合わない、未知の side、配置できない点。

## 詳しい使い方ガイド

- [figure_annotation ファミリ ガイド](../guides/figure_annotation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [dataset_conventions](../guides/dataset_conventions.md) — 学習データセット規約の知識 — COCO / YOLO / VOC と外観検査での落とし穴

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [paper_figure](../../../../examples/paper_figure.py) — `py -3.11 examples/paper_figure.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`paper`)

[annotate_leader](annotate_leader.md) · [annotate_markers](annotate_markers.md) · [annotate_legend](annotate_legend.md) · [annotate_dimension_layout](annotate_dimension_layout.md) · [annotate_dimension](annotate_dimension.md) · [annotate_angle_layout](annotate_angle_layout.md) · [annotate_angle](annotate_angle.md) · [annotate_scale_bar_layout](annotate_scale_bar_layout.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
