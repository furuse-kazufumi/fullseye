---
op: zoom_inset
dim: annotate
category: compose
in: image2d
out: image2d
examples: [annotate_gallery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# zoom_inset — ANNOTATE `compose` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import annotate; annotate.zoom_inset(img, src_rect, dst_xy, factor=3, color='emphasis', width=2, connect=True, scheme='okabe_ito', style=None)` (または `opsannotate.get("zoom_inset")`)

## 使い方

拡大の差し込み ―― 元図に**枠**と**引き出し線**を付ける。

拡大は ``np.repeat`` の**最近傍**(整数倍)。補間しないのは、拡大図が
「元の画素そのもの」であることを保証するため(滑らかにすると、無かった
構造が生まれたように見える)。

Parameters
----------
src_rect : (x, y, w, h)
    拡大元。
dst_xy : (x, y)
    差し込み先の**左上**。
factor : int
    整数の拡大率(>= 1)。
connect : bool
    True なら元枠と差し込み枠の対応する角を 2 本の線で結ぶ。

Raises
------
ValueError
    factor が 1 未満か非整数、元枠/差し込みが画像からはみ出す。

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

[compare_frame](compare_frame.md) · [panel_grid](panel_grid.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
