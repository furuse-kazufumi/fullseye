---
op: plot_series
dim: annotate
category: plot
in: image2d × axes × signal × signal
out: image2d
examples: [annotate_gallery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# plot_series — ANNOTATE `plot` op

- **データ種**: `image2d × axes × signal × signal` → `image2d`
- **呼び出し**: `import annotate; annotate.plot_series(img, axes, x, y, kind='line', color='reference', width=2, marker_size=3, baseline=None, bar_width=0.7, clip=True, scheme='okabe_ito', style=None)` (または `opsannotate.get("plot_series")`)

## 使い方

折れ線・散布・棒を描く。**データ座標**で受ける(画素は axes が決める)。

Parameters
----------
axes : dict
    :func:`axes_transform` の返り。
x, y : 1-D
    同じ長さの系列。**空は ValueError**(空のグラフは「データが無い」のか
    「描き忘れ」なのか区別がつかない)。
kind : {'line','scatter','bar'}
baseline : float or None
    ``kind='bar'`` の基準値。None なら ``ylim`` の下端。
bar_width : float
    棒の幅(隣り合う x 間隔に対する比 ∈ (0,1])。
clip : bool
    True なら描画域の外に出る点を**例外**にする(黙って端に張り付く
    :mod:`imagedraw` のクランプは、嘘の折れ線を描いてしまう)。

Raises
------
ValueError
    長さ不一致 / 空 / 非有限 / 未知の kind / clip=True で範囲外。

## 詳しい使い方ガイド

- [figure_annotation ファミリ ガイド](../guides/figure_annotation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [dataset_conventions](../guides/dataset_conventions.md) — 学習データセット規約の知識 — COCO / YOLO / VOC と外観検査での落とし穴

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [annotate_gallery](../../../../examples/annotate_gallery.py) — `py -3.11 examples/annotate_gallery.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[text_box](../text/text_box.md) · [arrow](../pointer/arrow.md) · [leader_line](../pointer/leader_line.md) · [label_points](../pointer/label_points.md) · [crosshair](../pointer/crosshair.md) · [legend_box](../furniture/legend_box.md) · [color_bar](../furniture/color_bar.md) · [scale_bar](../furniture/scale_bar.md)

## 同カテゴリ(`plot`)

[axes_transform](axes_transform.md) · [data_to_pixel](data_to_pixel.md) · [nice_ticks](nice_ticks.md) · [axes_frame](axes_frame.md) · [grid_lines](grid_lines.md) · [ticks](ticks.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
