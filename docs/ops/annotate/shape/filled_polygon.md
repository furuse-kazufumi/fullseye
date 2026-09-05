---
op: filled_polygon
dim: annotate
category: shape
in: image2d × pairs
out: image2d
examples: [annotate_gallery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# filled_polygon — ANNOTATE `shape` op

- **データ種**: `image2d × pairs` → `image2d`
- **呼び出し**: `import annotate; annotate.filled_polygon(img, points, color='neutral', alpha=1.0, scheme='okabe_ito')` (または `opsannotate.get("filled_polygon")`)

## 使い方

多角形の塗り(偶奇規則の交差判定 ―― :mod:`imagedraw` は輪郭のみ)。

Parameters
----------
points : (N,2)
    **(x,y)** の頂点列(自動的に閉じる)。3 点未満は ValueError。

Raises
------
ValueError
    点が 3 未満 / 非有限 / alpha が [0,1] の外。

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

## 同カテゴリ(`shape`)

[rounded_rect](rounded_rect.md) · [arc](arc.md) · [ellipse](ellipse.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
