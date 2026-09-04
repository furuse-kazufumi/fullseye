---
op: crosshair
dim: annotate
category: pointer
in: image2d
out: image2d
examples: [annotate_gallery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# crosshair — ANNOTATE `pointer` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import annotate; annotate.crosshair(img, xy, color='emphasis', width=1, gap=6, extent=None, scheme='okabe_ito', style=None)` (または `opsannotate.get("crosshair")`)

## 使い方

断面の交差線(MPR で使う)。``gap`` だけ中心を空けて視点を隠さない。

Parameters
----------
xy : (x, y)
    交点。
gap : int
    中心を空ける半径 [px] (0 で全通し)。
extent : int or None
    中心からの腕の長さ[px]。None なら画像の端まで。

Raises
------
ValueError
    交点が画像の外、負の gap/extent。

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

[text_box](../text/text_box.md) · [arrow](arrow.md) · [leader_line](leader_line.md) · [label_points](label_points.md) · [legend_box](../furniture/legend_box.md) · [color_bar](../furniture/color_bar.md) · [scale_bar](../furniture/scale_bar.md) · [axes_frame](../plot/axes_frame.md)

## 同カテゴリ(`pointer`)

[arrow](arrow.md) · [leader_line](leader_line.md) · [label_points](label_points.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
