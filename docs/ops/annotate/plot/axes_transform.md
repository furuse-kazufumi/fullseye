---
op: axes_transform
dim: annotate
category: plot
in: 
out: axes
examples: [annotate_gallery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# axes_transform — ANNOTATE `plot` op

- **データ種**: `` → `axes`
- **呼び出し**: `import annotate; annotate.axes_transform(rect, xlim, ylim, invert_y=True, xscale='linear', yscale='linear')` (または `opsannotate.get("axes_transform")`)

## 使い方

データ座標 → 画素座標の対応(**閉形式**)を作る。

``row は下向き`` という画像の事実と、``y は上向き`` というグラフの慣習の
ずれを、**この 1 か所だけ**で吸収する。図のコードはこの辞書を持ち回る。

    px = x0 + (x - xmin)/(xmax - xmin) * (w - 1)
    py = y0 + (h - 1) - (y - ymin)/(ymax - ymin) * (h - 1)     # invert_y

Parameters
----------
rect : (x, y, w, h)
    描画域(左上基準、画素)。
xlim, ylim : (lo, hi)
    データ範囲。lo == hi は**傾きが無限大**になるので ValueError。
    **lo > hi(反転軸)も許す** ―― 深度やランクを上下逆に描くため。
invert_y : bool
    True(既定)なら ``ylim[0]`` が**下端**に来る = 普通のグラフ。
    False なら画像そのままの向き(上端が ``ylim[0]``)。
xscale, yscale : {'linear','log'}
    ``'log'`` は常用対数。範囲に 0 以下が入れば ValueError
    (log 軸に 0 を渡して -inf を「端」として描く図は嘘になる)。

Returns
-------
dict
    ``{"rect", "xlim", "ylim", "invert_y", "xscale", "yscale"}``。

Raises
------
ValueError
    矩形が不正、範囲が非有限か幅ゼロ、w か h が 2 未満、
    未知の scale、log 軸で範囲に 0 以下。

## 詳しい使い方ガイド

- [figure_annotation ファミリ ガイド](../guides/figure_annotation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [annotate_gallery](../../../../examples/annotate_gallery.py) — `py -3.11 examples/annotate_gallery.py`

## 型が繋がる次の op(`axes` を入力に取れる)

[data_to_pixel](data_to_pixel.md) · [axes_frame](axes_frame.md) · [grid_lines](grid_lines.md) · [ticks](ticks.md) · [plot_series](plot_series.md)

## 同カテゴリ(`plot`)

[data_to_pixel](data_to_pixel.md) · [nice_ticks](nice_ticks.md) · [axes_frame](axes_frame.md) · [grid_lines](grid_lines.md) · [ticks](ticks.md) · [plot_series](plot_series.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
