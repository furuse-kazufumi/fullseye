---
op: overlay_labels
dim: annotate
category: overlay
in: image2d × labels
out: image2d
examples: [annotate_gallery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# overlay_labels — ANNOTATE `overlay` op

- **データ種**: `image2d × labels` → `image2d`
- **呼び出し**: `import annotate; annotate.overlay_labels(img, labels, alpha=0.5, colors=None, scheme='okabe_ito', background=0)` (または `opsannotate.get("overlay_labels")`)

## 使い方

色ラベル図を α で重ねる。**同じラベル番号には常に同じ色**。

Parameters
----------
labels : (H,W) int
    ラベル番号の地図。``background``(既定 0)は透明。
colors : (k,3) or None
    番号 → 色。None なら Okabe–Ito 8 色を番号順に周回する
    (乱数を使わないので、同じラベル図なら常に同じ絵になる)。

Raises
------
ValueError
    形の不一致 / 負のラベル / alpha が [0,1] の外 / colors の形。

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

## 同カテゴリ(`overlay`)

[overlay_mask](overlay_mask.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
