---
op: legend_box
dim: annotate
category: furniture
in: image2d × entries
out: image2d
examples: [annotate_gallery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# legend_box — ANNOTATE `furniture` op

- **データ種**: `image2d × entries` → `image2d`
- **呼び出し**: `import annotate; annotate.legend_box(img, entries, xy, anchor='lt', swatch=14, row_gap=4, pad=8, font_size=13, box_color=None, box_alpha=0.72, markers=False, scheme='okabe_ito', font_path=None, min_font_size=9, style=None, border=1, border_color='neutral')` (または `opsannotate.get("legend_box")`)

## 使い方

色 × 説明の凡例。**箱の高さは要素数から閉形式で決まる**。

``height = 2*pad + n*row_h + (n-1)*row_gap`` (``row_h = max(swatch, 文字高))。

Parameters
----------
entries : sequence
    ``(color, text)`` の並び。``color`` は役割名でも RGB でもよい。
markers : bool
    True なら役割名に対応する :data:`palette.ROLE_MARKERS` の記号を
    説明の前に付ける(**色だけに意味を載せない**ため)。役割名でない
    要素には記号が無いので付かない。

Returns
-------
ndarray

Raises
------
ValueError
    entries が空 / 形が ``(color, text)`` でない / 箱が画像からはみ出す /
    未知の役割名。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [annotate_gallery](../../../../examples/annotate_gallery.py) — `py -3.11 examples/annotate_gallery.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[text_box](../text/text_box.md) · [arrow](../pointer/arrow.md) · [leader_line](../pointer/leader_line.md) · [label_points](../pointer/label_points.md) · [crosshair](../pointer/crosshair.md) · [color_bar](color_bar.md) · [scale_bar](scale_bar.md) · [axes_frame](../plot/axes_frame.md)

## 同カテゴリ(`furniture`)

[color_bar](color_bar.md) · [scale_bar](scale_bar.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
