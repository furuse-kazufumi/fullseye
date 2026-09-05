---
op: edges_sub_pix
dim: 2d
category: contour
in: image
out: contour
halcon: edges_sub_pix
examples: [gallery2d_contour_measure, quickstart]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# edges_sub_pix — 2D `contour` op

- **データ種**: `image` → `contour`
- **呼び出し**: `fullseye.apply(img, "edges_sub_pix", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `edges_sub_pix`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

サブピクセル精度のエッジ点抽出。勾配とその法線方向(``gradient_
normals``)を求め、しきい値(``0.15+0.5*a``)を超える画素を連結成分化した
後、放物線当てはめで各点をサブピクセル位置へ精密化する(``subpixel_
refine_edges``、``ops`` 側の同名 op と共有する実装 ―― 2026-09-02 修正で
真の意味でサブピクセルになった。旧実装は整数画素座標をそのまま返して
いた)。HALCON の ``edges_sub_pix``（Extract sub-pixel precise edges using
Deriche, Lanser, Shen, or Canny filters.）に相当。

``a`` がエッジ強度のしきい値を振る。``b`` は未使用。

## 詳しい使い方ガイド

- [gallery2d_contour_measure ファミリ ガイド](../guides/gallery2d_contour_measure.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_contour_measure](../../../../examples/gallery2d_contour_measure.py) — `py -3.11 examples/gallery2d_contour_measure.py`
- [quickstart](../../../../examples/quickstart.py) — `py -3.11 examples/quickstart.py`

## 型が繋がる次の op(`contour` を入力に取れる)

[identity](../misc/identity.md) · [select_contours](select_contours.md) · [smooth_contours](smooth_contours.md) · [fit_line_contours](fit_line_contours.md) · [contours_to_region](contours_to_region.md) · [count_contours](../features/count_contours.md) · [total_length](../features/total_length.md) · [select_contours_xld](select_contours_xld.md)

## 同カテゴリ(`contour`)

[select_contours](select_contours.md) · [smooth_contours](smooth_contours.md) · [fit_line_contours](fit_line_contours.md) · [contours_to_region](contours_to_region.md) · [sk_find_contours](sk_find_contours.md) · [lines_gauss](lines_gauss.md) · [select_contours_xld](select_contours_xld.md) · [smooth_contours_xld](smooth_contours_xld.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
