---
op: contour_point_num_xld
dim: 2d
category: contour
in: contour
out: feature
halcon: contour_point_num_xld
examples: [gallery2d_contour_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# contour_point_num_xld — 2D `contour` op

- **データ種**: `contour` → `feature`
- **呼び出し**: `fullseye.apply(img, "contour_point_num_xld", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `contour_point_num_xld`(意味・パラメータは HALCON リファレンスが参考になる)

![contour_point_num_xld: input → output](../../_fig/contour_point_num_xld.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

*つまみ a は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![contour_point_num_xld: stages](../../_fig/contour_point_num_xld.chain.jpg)

## 使い方

XLD 輪郭群のうち最も点数の多い輪郭を選び、その頂点数を 500 点で正規化して [0,1] で返す（500 点以上は 1.0 に飽和）。a, b は未使用。輪郭が無ければ 0 を返す。

HALCON の ``contour_point_num_xld``（XLD 輪郭に含まれる点の実数をそのまま返す演算）とは異なり、この実装は点数そのものではなく 500 点でスケーリングした比率を返す近似（feature sort が [0,1] 想定の値を運ぶ契約のため）。

## 詳しい使い方ガイド

- [gallery2d_contour_measure ファミリ ガイド](../guides/gallery2d_contour_measure.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
threshold 0.50 0.50
sk_find_contours 0.50 0.50
contour_point_num_xld 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_contour_measure](../../../../examples/gallery2d_contour_measure.py) — `py -3.11 examples/gallery2d_contour_measure.py`

## 型が繋がる次の op(`feature` を入力に取れる)

[identity](../misc/identity.md)

## 同カテゴリ(`contour`)

[select_contours](select_contours.md) · [smooth_contours](smooth_contours.md) · [fit_line_contours](fit_line_contours.md) · [contours_to_region](contours_to_region.md) · [sk_find_contours](sk_find_contours.md) · [edges_sub_pix](edges_sub_pix.md) · [lines_gauss](lines_gauss.md) · [select_contours_xld](select_contours_xld.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
