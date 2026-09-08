---
op: annotate_invert_path
dim: annotate
category: paper
in: image2d × pairs
out: image2d
examples: [annotate_paper_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# annotate_invert_path — ANNOTATE `paper` op

- **データ種**: `image2d × pairs` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.annotate_invert_path(img, points, width=1.5, closed=False, dash=None, mode='complement', alpha=1.0, min_contrast=1.5, on_invisible='warn')` (実装を直接呼ぶなら `import annotate; annotate.annotate_invert_path(img, points, width=1.5, closed=False, dash=None, mode='complement', alpha=1.0, min_contrast=1.5, on_invisible='warn')`、台帳から引くなら `opsannotate.get("annotate_invert_path")`)

## 使い方

折れ線(line)を**反転色**で描く。アンチエイリアスつき。

線は領域より不利で、そこがこの op を分けている理由 —— 太さ 1.5 画素の
線は端の画素の被覆率が 0.3 程度しかないため、**反転しても被覆の分しか
動かない**。中間調の地では領域よりさらに先に消える。判定は「被覆率
0.5 以上の画素」で行う(それ未満は元から半透明なので、見えなくても
それは反転のせいではない)。

Parameters
----------
points : (N,2)
    折れ線の頂点 ``(x, y)``(画素座標)。
width : float
    線の太さ(画素、0.5 以上)。
closed : bool
    真なら最後の点と最初の点を結ぶ。
dash : (on, off) or None
    破線の刻み(画素)。:func:`_dash_pieces` と同じ規則。
mode, alpha, min_contrast, on_invisible :
    :func:`annotate_invert` と同じ。

Returns
-------
(H,W[,C]) float64
    反転を乗せた複製。

Examples
--------
>>> import numpy as np, annotate
>>> img = np.zeros((16, 32))
>>> out = annotate.annotate_invert_path(img, [(2, 8), (29, 8)], width=3)
>>> float(out[8, 15])                       # 黒地の上なので白い線になる
1.0
>>> float(out[2, 15])                       # 線から離れたところは元のまま
0.0

## 詳しい使い方ガイド

- [figure_annotation ファミリ ガイド](../guides/figure_annotation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [dataset_conventions](../guides/dataset_conventions.md) — 学習データセット規約の知識 — COCO / YOLO / VOC と外観検査での落とし穴

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [annotate_paper_tour](../../../../examples/annotate_paper_tour.py) — `py -3.11 examples/annotate_paper_tour.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[text_box](../text/text_box.md) · [arrow](../pointer/arrow.md) · [leader_line](../pointer/leader_line.md) · [label_points](../pointer/label_points.md) · [crosshair](../pointer/crosshair.md) · [legend_box](../furniture/legend_box.md) · [color_bar](../furniture/color_bar.md) · [scale_bar](../furniture/scale_bar.md)

## 同カテゴリ(`paper`)

[annotate_leader_layout](annotate_leader_layout.md) · [annotate_leader](annotate_leader.md) · [annotate_markers](annotate_markers.md) · [annotate_legend](annotate_legend.md) · [annotate_dimension_layout](annotate_dimension_layout.md) · [annotate_dimension](annotate_dimension.md) · [annotate_angle_layout](annotate_angle_layout.md) · [annotate_angle](annotate_angle.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
