---
op: panel_grid
dim: annotate
category: compose
in: image2d
out: image2d
examples: [annotate_gallery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# panel_grid — ANNOTATE `compose` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import annotate; annotate.panel_grid(panels, labels=None, ncols=3, pad=10, label_h=32, background=0.05, title=None, title_h=0, font_size=15, min_font_size=9, font_path=None, text_color=None, border=0, border_color='neutral', scheme='okabe_ito', style=None)` (または `opsannotate.get("panel_grid")`)

## 使い方

パネルを格子に並べ、各枠の下にラベルを敷く(montage / contact sheet)。

生成器 6 本がそれぞれ別実装を持っていた、**この repo で最も重複していた図の
部品**。ここでの流儀:

* **拡大しない** ―― 小さいパネルは中央に置いて余白で埋める。引き伸ばすと
  「無い解像度がある」ように見える。
* **ラベルは測ってから描く** ―― 入らなければ縮め、駄目なら例外
  (:func:`text_box` の境界検査に載る)。
* セルの大きさは全パネルの最大寸で、**格子は常に矩形**。

Parameters
----------
panels : sequence of ndarray
    並べる画像(``(H,W)`` / ``(H,W,C)``、大きさはばらばらでよい)。
    チャンネルの並びは揃っていること。
labels : sequence of str or None
    各パネルの見出し。``label_h`` が 0 なら描かない。
ncols : int
    列数。行数は ``ceil(n/ncols)``。
title : str or None
    全体の表題(``title_h`` が 0 なら ``font_size+14`` を自動で確保)。

Returns
-------
ndarray
    新しい合成画像(float [0,1])。大きさは
    ``W = 2*pad + ncols*cw + (ncols-1)*pad``、
    ``H = title_h + 2*pad + nrows*(ch+label_h) + (nrows-1)*pad``。

Raises
------
ValueError
    panels が空 / チャンネル不一致 / ncols < 1 / 負の余白 /
    labels の数が合わない。

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

## 同カテゴリ(`compose`)

[zoom_inset](zoom_inset.md) · [compare_frame](compare_frame.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
