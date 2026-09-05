---
op: lines_color
dim: 2d
category: contour
in: color
out: contour
halcon: lines_color
examples: [gallery2d_contour_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# lines_color — 2D `contour` op

- **データ種**: `color` → `contour`
- **呼び出し**: `fullseye.apply(img, "lines_color", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `lines_color`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

カラー画像の線（リッジ）を検出する。HALCON の ``lines_color``（カラーの
線とその幅を検出する）に相当するとされるが、**線幅は推定しない**——輝度
画像上のガウシアン・ラプラシアン応答をしきい値二値化して連結成分を
輪郭として返すだけで、線幅（HALCON 側が返す値）に相当する出力は持たない。

``_rgb_to_gray`` で輝度化した後、``scipy.ndimage.gaussian_laplace`` を
シグマ ``0.5 + 2.5 * a`` でかけて絶対値を最大値正規化し、
``0.2 + 0.4 * b`` でしきい値二値化して 8 連結ラベリングする。
a はリッジの太さ（LoG のスケール）、b は検出しきい値を振る。
3 画素未満の成分は捨てる。

## 詳しい使い方ガイド

- [gallery2d_contour_measure ファミリ ガイド](../guides/gallery2d_contour_measure.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_contour_measure](../../../../examples/gallery2d_contour_measure.py) — `py -3.11 examples/gallery2d_contour_measure.py`

## 型が繋がる次の op(`contour` を入力に取れる)

[identity](../misc/identity.md) · [select_contours](select_contours.md) · [smooth_contours](smooth_contours.md) · [fit_line_contours](fit_line_contours.md) · [contours_to_region](contours_to_region.md) · [count_contours](../features/count_contours.md) · [total_length](../features/total_length.md) · [select_contours_xld](select_contours_xld.md)

## 同カテゴリ(`contour`)

[select_contours](select_contours.md) · [smooth_contours](smooth_contours.md) · [fit_line_contours](fit_line_contours.md) · [contours_to_region](contours_to_region.md) · [sk_find_contours](sk_find_contours.md) · [edges_sub_pix](edges_sub_pix.md) · [lines_gauss](lines_gauss.md) · [select_contours_xld](select_contours_xld.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
