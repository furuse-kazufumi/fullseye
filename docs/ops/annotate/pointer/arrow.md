---
op: arrow
dim: annotate
category: pointer
in: image2d
out: image2d
examples: [annotate_gallery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# arrow — ANNOTATE `pointer` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import annotate; annotate.arrow(img, p0, p1, color='emphasis', width=2, head_len=12.0, head_width=9.0, scheme='okabe_ito', style=None)` (または `opsannotate.get("arrow")`)

## 使い方

``p0`` から ``p1`` へ矢印(軸は :func:`imagedraw.draw_line`、矢じりは塗り)。

Parameters
----------
p0, p1 : (x, y)
    起点・先端。**x=col, y=row**。
head_len, head_width : float
    矢じりの長さ・幅[px]。``0`` で線分のみ。軸より矢じりが長い短距離の
    矢印では、矢じりを軸長の 8 割まで**相似に縮める**(そうしないと
    矢じりの根元が起点の手前に来て、軸が逆向きに描かれる)。
style : dict or None
    軸線を引く :func:`imagedraw.draw_line` への素通し引数(破線など)。

Returns
-------
ndarray

Raises
------
ValueError
    端点が非有限/一致、負の太さ・矢じり寸法、両端とも画像の外。

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

[text_box](../text/text_box.md) · [leader_line](leader_line.md) · [label_points](label_points.md) · [crosshair](crosshair.md) · [legend_box](../furniture/legend_box.md) · [color_bar](../furniture/color_bar.md) · [scale_bar](../furniture/scale_bar.md) · [axes_frame](../plot/axes_frame.md)

## 同カテゴリ(`pointer`)

[leader_line](leader_line.md) · [label_points](label_points.md) · [crosshair](crosshair.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
