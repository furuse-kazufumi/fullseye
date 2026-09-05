---
op: annotate_leader
dim: annotate
category: paper
in: image2d
out: image2d
examples: [paper_figure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# annotate_leader — ANNOTATE `paper` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import annotate; annotate.annotate_leader(img, points, labels=None, color='emphasis', width=1.5, cap_size=3.0, font_size=12, pad=4, gap=22, side='auto', box_alpha=0.72, text_color=None, scheme='okabe_ito', font_path=None, min_font_size=9, layout=None)` (または `opsannotate.get("annotate_leader")`)

## 使い方

画像(image2d)を返す: 肘つき引き出し線 + 文字(複数点の衝突回避つき)。

配置は :func:`annotate_leader_layout` が決める(``layout=`` に渡せば再利用)。
線はアンチエイリアス、対象側の端には点、文字は :func:`text_box`。

Raises
------
ValueError
    :func:`annotate_leader_layout` と同じ + 太さ・cap_size が非正。

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

[annotate_leader_layout](annotate_leader_layout.md) · [annotate_markers](annotate_markers.md) · [annotate_legend](annotate_legend.md) · [annotate_dimension_layout](annotate_dimension_layout.md) · [annotate_dimension](annotate_dimension.md) · [annotate_angle_layout](annotate_angle_layout.md) · [annotate_angle](annotate_angle.md) · [annotate_scale_bar_layout](annotate_scale_bar_layout.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
