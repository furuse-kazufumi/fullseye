---
op: annotate_scale_bar_layout
dim: annotate
category: paper
in: 
out: table
examples: [paper_figure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# annotate_scale_bar_layout — ANNOTATE `paper` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import annotate; annotate.annotate_scale_bar_layout(shape, units_per_pixel, unit='µm', corner='rb', target_fraction=0.2, margin=14, thickness=5)` (または `opsannotate.get("annotate_scale_bar_layout")`)

## 使い方

table(dict)を返す: 画像幅の ``target_fraction`` 以下で**切りのよい**長さのバー。

長さは ``1/2/5 × 10^k`` のうち ``target_fraction * W * units_per_pixel`` 以下の
最大値。画素長 = ``round(length / units_per_pixel)``。

Returns
-------
dict
    ``{"length","px","rect":(x,y,w,h),"unit","corner","label"}``。

Raises
------
ValueError
    units_per_pixel / target_fraction が非正、未知の corner、
    バーが 1 画素未満か画像に収まらない。

## 詳しい使い方ガイド

- [figure_annotation ファミリ ガイド](../guides/figure_annotation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [dataset_conventions](../guides/dataset_conventions.md) — 学習データセット規約の知識 — COCO / YOLO / VOC と外観検査での落とし穴

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [paper_figure](../../../../examples/paper_figure.py) — `py -3.11 examples/paper_figure.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`paper`)

[annotate_leader_layout](annotate_leader_layout.md) · [annotate_leader](annotate_leader.md) · [annotate_markers](annotate_markers.md) · [annotate_legend](annotate_legend.md) · [annotate_dimension_layout](annotate_dimension_layout.md) · [annotate_dimension](annotate_dimension.md) · [annotate_angle_layout](annotate_angle_layout.md) · [annotate_angle](annotate_angle.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
