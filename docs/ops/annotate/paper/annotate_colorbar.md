---
op: annotate_colorbar
dim: annotate
category: paper
in: image2d × image2d
out: image2d
examples: [paper_figure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# annotate_colorbar — ANNOTATE `paper` op

- **データ種**: `image2d × image2d` → `image2d`
- **呼び出し**: `import annotate; annotate.annotate_colorbar(img, field, rect, lut=None, vmin=None, vmax=None, alpha=0.6, mask=None, unit='', label_fmt='{:.3g}', orientation='vertical', font_size=12, scheme='okabe_ito', font_path=None, text_color=None, nan_transparent=False)` (または `opsannotate.get("annotate_colorbar")`)

## 使い方

画像(image2d)を返す: スカラ場を LUT で色分けして重ね、カラーバーを添える。

``t = (field - vmin)/(vmax - vmin)`` を [0,1] に**クリップ**し ``lut[round(t*(n-1))]``
で色にする(範囲外の値は端の色 —— カラーバーの端と同じなので嘘にならない)。
重ねは ``alpha`` の α 合成、``mask`` を渡せばその画素だけ。

Parameters
----------
field : (H, W)
    画像と同じ大きさのスカラ場。非有限は ``nan_transparent=True`` のときだけ
    透明として許す(既定は ValueError)。
lut : (n, 3) or None
    None なら :func:`palette.diverging_lut` の 256 段。
vmin, vmax : float or None
    None なら場の(有限値の)最小・最大。等しければ ValueError。

Raises
------
ValueError
    形の不一致、非有限(許可なし)、vmin == vmax、alpha が [0,1] の外、
    バーの矩形が画像外、LUT の形。

## 詳しい使い方ガイド

- [figure_annotation ファミリ ガイド](../guides/figure_annotation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [paper_figure](../../../../examples/paper_figure.py) — `py -3.11 examples/paper_figure.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[text_box](../text/text_box.md) · [arrow](../pointer/arrow.md) · [leader_line](../pointer/leader_line.md) · [label_points](../pointer/label_points.md) · [crosshair](../pointer/crosshair.md) · [legend_box](../furniture/legend_box.md) · [color_bar](../furniture/color_bar.md) · [scale_bar](../furniture/scale_bar.md)

## 同カテゴリ(`paper`)

[annotate_leader_layout](annotate_leader_layout.md) · [annotate_leader](annotate_leader.md) · [annotate_markers](annotate_markers.md) · [annotate_legend](annotate_legend.md) · [annotate_dimension_layout](annotate_dimension_layout.md) · [annotate_dimension](annotate_dimension.md) · [annotate_angle_layout](annotate_angle_layout.md) · [annotate_angle](annotate_angle.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
