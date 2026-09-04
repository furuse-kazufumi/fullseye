---
op: data_to_pixel
dim: annotate
category: plot
in: axes × signal × signal
out: pairs
examples: [annotate_gallery]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# data_to_pixel — ANNOTATE `plot` op

- **データ種**: `axes × signal × signal` → `pairs`
- **呼び出し**: `import annotate; annotate.data_to_pixel(axes, x, y)` (または `opsannotate.get("data_to_pixel")`)

## 使い方

:func:`axes_transform` の対応でデータ点を画素 (x,y) に写す。

**クリップしない** ―― ``np.clip(v, lo, hi)`` は ``lo > hi``(反転軸)の
とき黙って ``hi`` を返し、全点が端に貼り付いた「もっともらしい嘘の図」に
なる(この repo の生成器で実際に一度騙されている)。範囲外を弾くのは
:func:`plot_series` の ``clip=True`` の仕事で、そこでは**例外**にする。

Returns
-------
(ndarray, ndarray)
    ``px``, ``py``(float、丸めない ―― 丸めは描画側の仕事)。

Raises
------
ValueError
    log 軸に 0 以下の値を渡したとき(-inf を「端」として描く図は嘘になる)。
    ``x`` と ``y`` の長さが違うとき(下記)。

Notes
-----
**長さの不一致を拒否するのは 2026-09-02 に足した**。連鎖ファザーがこの op を
実行できるようになった直後、長さの違う 2 本の signal を渡す経路で採掘器が
``np.stack`` の生の ValueError で落ちて発覚した。それまでは ``x`` 7 点・
``y`` 3 点でも**例外を出さず、長さの違う 2 本をそのまま返していた**。

危ないのは落ちることではなく、落ちないこと ―― 返った 2 本を ``zip`` すると
**3 点だけが、x の先頭 3 つの位置に**描かれる。点が消えたことも、x が
ずれたことも図からは分からない。兄弟の :func:`plot_series` は同じ状況を
``"x and y must have the same length"`` で拒否していたので、**同じ族の中で
規律が割れていた**(片方だけ直しても再発する型なので、文言も揃えてある)。

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

## 型が繋がる次の op(`pairs` を入力に取れる)

[label_points](../pointer/label_points.md) · [filled_polygon](../shape/filled_polygon.md)

## 同カテゴリ(`plot`)

[axes_transform](axes_transform.md) · [nice_ticks](nice_ticks.md) · [axes_frame](axes_frame.md) · [grid_lines](grid_lines.md) · [ticks](ticks.md) · [plot_series](plot_series.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
