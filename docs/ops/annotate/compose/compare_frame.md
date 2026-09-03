---
op: compare_frame
dim: annotate
category: compose
in: image2d × image2d
out: image2d
examples: [annotate_gallery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# compare_frame — ANNOTATE `compose` op

- **データ種**: `image2d × image2d` → `image2d`
- **呼び出し**: `import annotate; annotate.compare_frame(left, right, layout='h', labels=None, divider=3, gap=0, divider_color='neutral', background=0.0, label_anchor='lt', label_margin=8, scheme='okabe_ito', **text_kw)` (または `opsannotate.get("compare_frame")`)

## 使い方

2 枚を並べ、境界に**仕切り**と**ラベル**を置く。

Parameters
----------
left, right : ndarray
    比べる 2 枚。大きさが違ってもよい(足りない側は ``background`` で埋める)。
    チャンネル数は揃っていること。
layout : {'h','v'}
    ``'h'`` = 左右、``'v'`` = 上下。
labels : (str, str) or None
    それぞれの見出し。
divider : int
    仕切りの太さ [px] (0 で無し)。
gap : int
    仕切りの両側に空ける余白[px]。

Returns
-------
ndarray
    新しい合成画像。

Raises
------
ValueError
    チャンネル数の不一致 / 未知の layout / 負の divider・gap /
    labels が 2 要素でない。

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

[zoom_inset](zoom_inset.md) · [panel_grid](panel_grid.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
