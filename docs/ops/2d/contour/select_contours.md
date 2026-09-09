---
op: select_contours
dim: 2d
category: contour
in: contour
out: contour
halcon: select_contours_xld
examples: [gallery2d_contour_measure, quickstart]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# select_contours — 2D `contour` op

- **データ種**: `contour` → `contour`
- **呼び出し**: `fullseye.apply(img, "select_contours", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `select_contours_xld`(意味・パラメータは HALCON リファレンスが参考になる)

![select_contours: input → output](../../_fig/select_contours.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![select_contours: knob a sweep](../../_fig/select_contours.a.jpg)

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![select_contours: stages](../../_fig/select_contours.chain.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![select_contours: other inputs](../../_fig/select_contours.inputs.jpg)

## 使い方

点数（長さ）でフィルタして XLD 輪郭を選別する。HALCON の ``select_contours_xld``（Select XLD contours according to several features.）に相当。

``a`` が残す最小点数のしきい値を ``3〜43``（``3 + int(40a)``）に振る。``b`` は未使用。輪郭を構成する点の数（≒長さ）がしきい値未満のものを丸ごと捨てる。HALCON 版は点数以外にも円形度・凸性などの特徴で選べるが、この実装は点数のみ。

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
select_contours 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_contour_measure](../../../../examples/gallery2d_contour_measure.py) — `py -3.11 examples/gallery2d_contour_measure.py`
- [quickstart](../../../../examples/quickstart.py) — `py -3.11 examples/quickstart.py`

## 型が繋がる次の op(`contour` を入力に取れる)

[identity](../misc/identity.md) · [smooth_contours](smooth_contours.md) · [fit_line_contours](fit_line_contours.md) · [contours_to_region](contours_to_region.md) · [count_contours](../features/count_contours.md) · [total_length](../features/total_length.md) · [select_contours_xld](select_contours_xld.md) · [smooth_contours_xld](smooth_contours_xld.md)

## 同カテゴリ(`contour`)

[smooth_contours](smooth_contours.md) · [fit_line_contours](fit_line_contours.md) · [contours_to_region](contours_to_region.md) · [sk_find_contours](sk_find_contours.md) · [edges_sub_pix](edges_sub_pix.md) · [lines_gauss](lines_gauss.md) · [select_contours_xld](select_contours_xld.md) · [smooth_contours_xld](smooth_contours_xld.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
