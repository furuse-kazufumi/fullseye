---
op: leader_line
dim: annotate
category: pointer
in: image2d × text
out: image2d
examples: [annotate_gallery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# leader_line — ANNOTATE `pointer` op

- **データ種**: `image2d × text` → `image2d`
- **呼び出し**: `import annotate; annotate.leader_line(img, anchor_xy, target_xy, text=None, color='emphasis', width=2, cap='dot', cap_size=4, elbow=True, scheme='okabe_ito', style=None, **text_kw)` (または `opsannotate.get("leader_line")`)

## 使い方

引き出し線 —— 注記の位置(``anchor_xy``)から対象(``target_xy``)へ。

``elbow=True`` なら水平 → 斜めの 2 折れで引く(注記が本体に被りにくい)。
端点には ``cap`` の印(``'dot'``/``'arrow'``/``'cross'``/``'none'``)を置く。
``text`` を渡すと ``anchor_xy`` 側に :func:`text_box` を置く。
追加の ``**text_kw`` は :func:`text_box` へそのまま渡す。

Raises
------
ValueError
    未知の ``cap``、非有限な座標、線が画像の外。

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

[text_box](../text/text_box.md) · [arrow](arrow.md) · [label_points](label_points.md) · [crosshair](crosshair.md) · [legend_box](../furniture/legend_box.md) · [color_bar](../furniture/color_bar.md) · [scale_bar](../furniture/scale_bar.md) · [axes_frame](../plot/axes_frame.md)

## 同カテゴリ(`pointer`)

[arrow](arrow.md) · [label_points](label_points.md) · [crosshair](crosshair.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
