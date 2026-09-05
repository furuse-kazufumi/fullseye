---
op: annotate_legend
dim: annotate
category: paper
in: image2d
out: image2d
examples: [paper_figure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# annotate_legend — ANNOTATE `paper` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import annotate; annotate.annotate_legend(img, labels, xy, anchor='lt', start=1, radius=7.0, color='emphasis', text_color=None, font_size=12, pad=8, row_gap=4, box_color=None, box_alpha=0.72, border=1, border_color='neutral', scheme='okabe_ito', font_path=None, min_font_size=9, numbers=None)` (または `opsannotate.get("annotate_legend")`)

## 使い方

画像(image2d)を返す: 番号つき丸マーカー × 説明の凡例(:func:`annotate_markers` の対)。

箱の高さは閉形式 ``2*pad + n*row_h + (n-1)*row_gap``(``row_h = max(2r, 文字高)``)。

Parameters
----------
labels : sequence of str
    各行の説明。
numbers : sequence of str or None
    各行のマーカー文字。None なら ``start`` から連番。

Raises
------
ValueError
    labels が空、箱が画像からはみ出す、負の余白。

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

## 型が繋がる次の op(`image2d` を入力に取れる)

[text_box](../text/text_box.md) · [arrow](../pointer/arrow.md) · [leader_line](../pointer/leader_line.md) · [label_points](../pointer/label_points.md) · [crosshair](../pointer/crosshair.md) · [legend_box](../furniture/legend_box.md) · [color_bar](../furniture/color_bar.md) · [scale_bar](../furniture/scale_bar.md)

## 同カテゴリ(`paper`)

[annotate_leader_layout](annotate_leader_layout.md) · [annotate_leader](annotate_leader.md) · [annotate_markers](annotate_markers.md) · [annotate_dimension_layout](annotate_dimension_layout.md) · [annotate_dimension](annotate_dimension.md) · [annotate_angle_layout](annotate_angle_layout.md) · [annotate_angle](annotate_angle.md) · [annotate_scale_bar_layout](annotate_scale_bar_layout.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
