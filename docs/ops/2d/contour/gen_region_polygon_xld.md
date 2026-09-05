---
op: gen_region_polygon_xld
dim: 2d
category: contour
in: contour
out: region
halcon: gen_region_polygon_xld
examples: [gallery2d_contour_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# gen_region_polygon_xld — 2D `contour` op

- **データ種**: `contour` → `region`
- **呼び出し**: `fullseye.apply(img, "gen_region_polygon_xld", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `gen_region_polygon_xld`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

XLD 輪郭（多角形の頂点列）を region（画素マスク）へ変換する。輪郭点を最近傍画素に打点したのち、``1+2a`` 回の二値膨張（dilation）で線を太らせて連結させる。b は未使用。

HALCON の ``gen_region_polygon_xld``（XLD 多角形の内部を塗りつぶした region を生成する演算）とは異なり、この実装は多角形の内部を塗りつぶすのではなく、輪郭線そのものを膨張させて太らせるだけの近似 —— 閉じていない輪郭や自己交差する輪郭では本来の内部塗りつぶしと結果が食い違う。

## 詳しい使い方ガイド

- [gallery2d_contour_measure ファミリ ガイド](../guides/gallery2d_contour_measure.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_contour_measure](../../../../examples/gallery2d_contour_measure.py) — `py -3.11 examples/gallery2d_contour_measure.py`

## 型が繋がる次の op(`region` を入力に取れる)

[identity](../misc/identity.md) · [reg_erode](../region/reg_erode.md) · [reg_dilate](../region/reg_dilate.md) · [reg_open](../region/reg_open.md) · [reg_close](../region/reg_close.md) · [fill_holes](../region/fill_holes.md) · [select_largest](../region/select_largest.md) · [remove_small](../region/remove_small.md)

## 同カテゴリ(`contour`)

[select_contours](select_contours.md) · [smooth_contours](smooth_contours.md) · [fit_line_contours](fit_line_contours.md) · [contours_to_region](contours_to_region.md) · [sk_find_contours](sk_find_contours.md) · [edges_sub_pix](edges_sub_pix.md) · [lines_gauss](lines_gauss.md) · [select_contours_xld](select_contours_xld.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
