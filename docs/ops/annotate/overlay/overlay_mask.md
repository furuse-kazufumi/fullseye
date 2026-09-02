---
op: overlay_mask
dim: annotate
category: overlay
in: image2d × mask
out: image2d
examples: [annotate_gallery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# overlay_mask — ANNOTATE `overlay` op

- **データ種**: `image2d × mask` → `image2d`
- **呼び出し**: `import annotate; annotate.overlay_mask(img, mask, color='wrong', alpha=0.45, outline=0, outline_color=None, scheme='okabe_ito', style=None)` (または `opsannotate.get("overlay_mask")`)

## 使い方

2 値マスクを α で重ねる。**厳密に ``a*f + (1-a)*b``**。

Parameters
----------
mask : (H,W)
    画像と同じ大きさの真偽(または [0,1] の重み)。
    **形が違えば例外** ―― (row,col) と (x,y) の取り違えはここで死ぬ。
alpha : float
    マスク側の重み。
outline : int
    0 より大きければマスクの輪郭を太さ ``outline`` で描く。

Raises
------
ValueError
    形の不一致 / alpha が [0,1] の外 / mask に非有限。

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

## 同カテゴリ(`overlay`)

[overlay_labels](overlay_labels.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
