---
op: annotate_dimension
dim: annotate
category: paper
in: image2d
out: image2d
examples: [paper_figure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# annotate_dimension — ANNOTATE `paper` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import annotate; annotate.annotate_dimension(img, p0, p1, units_per_pixel=1.0, unit='px', offset=20.0, extension=6.0, color='neutral', width=1.5, head_len=9.0, head_width=6.0, label_fmt='{:.1f}', font_size=11, box_alpha=0.6, text_color=None, scheme='okabe_ito', font_path=None, layout=None)` (または `opsannotate.get("annotate_dimension")`)

## 使い方

画像(image2d)を返す: 寸法線(両端矢じり + 補助線 + 値と単位)。

値は ``|p1-p0| * units_per_pixel``(閉形式)。幾何は
:func:`annotate_dimension_layout`。

Raises
------
ValueError
    :func:`annotate_dimension_layout` と同じ + units_per_pixel が非正、
    寸法線が画像の外、文字が収まらない。

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

[annotate_leader_layout](annotate_leader_layout.md) · [annotate_leader](annotate_leader.md) · [annotate_markers](annotate_markers.md) · [annotate_legend](annotate_legend.md) · [annotate_dimension_layout](annotate_dimension_layout.md) · [annotate_angle_layout](annotate_angle_layout.md) · [annotate_angle](annotate_angle.md) · [annotate_scale_bar_layout](annotate_scale_bar_layout.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
