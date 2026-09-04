---
op: color_bar
dim: annotate
category: furniture
in: image2d × lut
out: image2d
examples: [annotate_gallery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# color_bar — ANNOTATE `furniture` op

- **データ種**: `image2d × lut` → `image2d`
- **呼び出し**: `import annotate; annotate.color_bar(img, lut, rect, vmin=0.0, vmax=1.0, unit='', label_fmt='{:g}', orientation='vertical', font_size=12, font_path=None, scheme='okabe_ito', border=1, border_color='neutral', text_color=None, style=None)` (または `opsannotate.get("color_bar")`)

## 使い方

LUT の凡例(カラーバー)。最小・最大・単位のラベルつき。

Parameters
----------
lut : (n,3) or (n,)
    色対応表。float [0,1]。:func:`palette.diverging_lut` の出力をそのまま。
rect : (x, y, w, h)
    バーの矩形(左上基準)。
vmin, vmax : float
    両端の値。``vmin == vmax`` は**目盛りの意味が消える**ので ValueError。
orientation : {'vertical','horizontal'}
    ``'vertical'`` は **上が vmax**(row は下向きなので LUT を反転する)。

Returns
-------
ndarray

Raises
------
ValueError
    LUT の形/値域、矩形のはみ出し、vmin==vmax、未知の orientation。

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

[text_box](../text/text_box.md) · [arrow](../pointer/arrow.md) · [leader_line](../pointer/leader_line.md) · [label_points](../pointer/label_points.md) · [crosshair](../pointer/crosshair.md) · [legend_box](legend_box.md) · [scale_bar](scale_bar.md) · [axes_frame](../plot/axes_frame.md)

## 同カテゴリ(`furniture`)

[legend_box](legend_box.md) · [scale_bar](scale_bar.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
