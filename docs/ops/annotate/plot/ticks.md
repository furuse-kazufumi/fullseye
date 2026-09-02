---
op: ticks
dim: annotate
category: plot
in: image2d × axes
out: image2d
examples: [annotate_gallery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# ticks — ANNOTATE `plot` op

- **データ種**: `image2d × axes` → `image2d`
- **呼び出し**: `import annotate; annotate.ticks(img, axes, xticks=None, yticks=None, color='neutral', width=1, tick_len=5, label=True, label_fmt='{:g}', font_size=11, font_path=None, scheme='okabe_ito', text_color=None, style=None)` (または `opsannotate.get("ticks")`)

## 使い方

目盛りとその数値。**位置は閉形式**(:func:`data_to_pixel` そのもの)。

目盛りは枠の**外側**へ ``tick_len`` px 出す。ラベルは目盛りの外側に置くので、
軸の周りに余白が無ければ :func:`text_box` の境界検査が例外にする
(= 図の外に文字が消える事故が起きない)。

Raises
------
ValueError
    tick_len が負、ラベルが画像に収まらない。

## 詳しい使い方ガイド

- [figure_annotation ファミリ ガイド](../guides/figure_annotation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [annotate_gallery](../../../../examples/annotate_gallery.py) — `py -3.11 examples/annotate_gallery.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[text_box](../text/text_box.md) · [arrow](../pointer/arrow.md) · [leader_line](../pointer/leader_line.md) · [label_points](../pointer/label_points.md) · [crosshair](../pointer/crosshair.md) · [legend_box](../furniture/legend_box.md) · [color_bar](../furniture/color_bar.md) · [scale_bar](../furniture/scale_bar.md)

## 同カテゴリ(`plot`)

[axes_transform](axes_transform.md) · [data_to_pixel](data_to_pixel.md) · [nice_ticks](nice_ticks.md) · [axes_frame](axes_frame.md) · [grid_lines](grid_lines.md) · [plot_series](plot_series.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
