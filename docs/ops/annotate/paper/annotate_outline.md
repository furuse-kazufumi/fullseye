---
op: annotate_outline
dim: annotate
category: paper
in: image2d × mask
out: image2d
examples: [paper_figure, poc_rotation_invariance_audit]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# annotate_outline — ANNOTATE `paper` op

- **データ種**: `image2d × mask` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.annotate_outline(img, mask, label=None, color='emphasis', width=1.5, alpha=1.0, dash=None, font_size=12, label_offset=(0, 0), box_alpha=0.6, text_color=None, scheme='okabe_ito', font_path=None, layout=None)` (実装を直接呼ぶなら `import annotate; annotate.annotate_outline(img, mask, label=None, color='emphasis', width=1.5, alpha=1.0, dash=None, font_size=12, label_offset=(0, 0), box_alpha=0.6, text_color=None, scheme='okabe_ito', font_path=None, layout=None)`、台帳から引くなら `opsannotate.get("annotate_outline")`)

## 使い方

画像(image2d)を返す: マスクの輪郭を(AA の)閉折れ線で描き、重心に文字を置く。

Raises
------
ValueError
    mask の形が画像と違う、真の画素が無い、alpha が [0,1] の外。

手順: ``layout`` が無ければ ``annotate_outline_layout(mask)`` で境界ループ
(画素の辺に沿う ``(x, y)`` の閉多角形、外周と穴の両方、成分ごと)と重心を
求め、各ループを距離被覆率のアンチエイリアス折れ線で載せる。``label`` が
あれば重心 + ``label_offset`` に ``text_box``(``anchor="cm"``、下敷き付き)を置く。

- ``img``: ``(H, W)`` / ``(H, W, 1|3|4)``、float64 複製・``[0, 1]``。
- ``mask``: ``(H, W)``、画像と同じ形(``[row, col]`` 添字)。bool 以外は ``> 0.5``
  で二値化、非有限は ``ValueError``。真の画素が無ければ ``ValueError``。
- ``width``: 線幅 [px]、0.5 以上。``dash=(on, off)`` [px] で破線(``on > 0``、
  ``off >= 0``)。
- ``alpha``: ``[0, 1]``。``box_alpha`` は文字の下敷きの不透明度。
- ``label_offset``: ``(dx, dy)`` [px]。重心が輪郭の外に落ちる形(三日月など)は
  ここでずらす。
- ``layout``: ``annotate_outline_layout`` の返り値を渡すと再計算せず同じ配置を
  別の絵に使い回せる(``contours`` / ``centroid`` を読む)。
- 返り値: 入力と同形の float64。

塗りで示すなら ``overlay_mask``、複数領域に番号を振るなら ``annotate_markers``。

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
- [poc_rotation_invariance_audit](../../../../examples/poc_rotation_invariance_audit.py) — `py -3.11 examples/poc_rotation_invariance_audit.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[text_box](../text/text_box.md) · [arrow](../pointer/arrow.md) · [leader_line](../pointer/leader_line.md) · [label_points](../pointer/label_points.md) · [crosshair](../pointer/crosshair.md) · [legend_box](../furniture/legend_box.md) · [color_bar](../furniture/color_bar.md) · [scale_bar](../furniture/scale_bar.md)

## 同カテゴリ(`paper`)

[annotate_leader_layout](annotate_leader_layout.md) · [annotate_leader](annotate_leader.md) · [annotate_markers](annotate_markers.md) · [annotate_legend](annotate_legend.md) · [annotate_dimension_layout](annotate_dimension_layout.md) · [annotate_dimension](annotate_dimension.md) · [annotate_angle_layout](annotate_angle_layout.md) · [annotate_angle](annotate_angle.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
