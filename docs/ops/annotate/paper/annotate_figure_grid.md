---
op: annotate_figure_grid
dim: annotate
category: paper
in: images
out: image2d
examples: [paper_figure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# annotate_figure_grid — ANNOTATE `paper` op

- **データ種**: `images` → `image2d`
- **呼び出し**: `import annotate; annotate.annotate_figure_grid(panels, captions=None, ncols=2, pad=10, caption_h=32, letters=True, letter_style='paren', title=None, font_size=14, min_font_size=9, background=1.0, border=1, border_color='neutral', text_color=None, scheme='okabe_ito', font_path=None)` (または `opsannotate.get("annotate_figure_grid")`)

## 使い方

画像(image2d)を返す: 画像 + 見出しを一枚の図に組む(余白一定・パネル文字つき)。

見出しは ``"(a) caption"``(``letters=True``)。白地(``background=1.0``)が既定
なので文字は自動で暗色になる(:func:`text_box` のコントラスト規則)。
幾何は :func:`annotate_figure_grid_layout`(``title`` があるときの ``title_h``
は :func:`measure_text` から同じ式で決まる)。

Raises
------
ValueError
    panels が空、captions の数不一致、見出しが帯に収まらない、26 枚超。

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
