---
op: label_points
dim: annotate
category: pointer
in: image2d × pairs
out: image2d
examples: [annotate_gallery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# label_points — ANNOTATE `pointer` op

- **データ種**: `image2d × pairs` → `image2d`
- **呼び出し**: `import annotate; annotate.label_points(img, points, labels=None, color='reference', font_size=12, pad=3, marker_size=0, scheme='okabe_ito', allow_overlap=False, **text_kw)` (または `opsannotate.get("label_points")`)

## 使い方

点群に番号や値を振る。**重なりを避けて置く**(避けられなければ例外)。

Parameters
----------
points : (N,2)
    **(x,y)** の点列。
labels : sequence or None
    各点の文字。None なら 1 始まりの番号。
marker_size : int
    0 より大きければ各点に十字マーカーも打つ。
allow_overlap : bool
    True なら重なりを許して最初の候補に置く(既定は False = 例外)。

Returns
-------
ndarray

Raises
------
ValueError
    点が空 / 非有限 / labels の数が合わない / どの候補位置でも
    既存のラベルと重なる(``allow_overlap=False`` のとき)。

## 詳しい使い方ガイド

- [figure_annotation ファミリ ガイド](../guides/figure_annotation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [annotate_gallery](../../../../examples/annotate_gallery.py) — `py -3.11 examples/annotate_gallery.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[text_box](../text/text_box.md) · [arrow](arrow.md) · [leader_line](leader_line.md) · [crosshair](crosshair.md) · [legend_box](../furniture/legend_box.md) · [color_bar](../furniture/color_bar.md) · [scale_bar](../furniture/scale_bar.md) · [axes_frame](../plot/axes_frame.md)

## 同カテゴリ(`pointer`)

[arrow](arrow.md) · [leader_line](leader_line.md) · [crosshair](crosshair.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
