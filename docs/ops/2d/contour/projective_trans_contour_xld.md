---
op: projective_trans_contour_xld
dim: 2d
category: contour
in: contour
out: contour
halcon: projective_trans_contour_xld
examples: [gallery2d_contour_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# projective_trans_contour_xld — 2D `contour` op

- **データ種**: `contour` → `contour`
- **呼び出し**: `fullseye.apply(img, "projective_trans_contour_xld", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `projective_trans_contour_xld`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

輪郭の各点に、列位置に応じた疑似的な遠近収縮(``d = 1 + 0.3*a*(col -
中心)/幅``で各点の座標を割る)を適用する。真の 3x3 ホモグラフィ行列による
射影変換ではなく、片方向だけの簡易な縮尺変化で近似している点に注意。
HALCON の ``projective_trans_contour_xld``（Apply a projective
transformation to an XLD contour.）の代役。

``a`` が収縮の強さを振る。``b`` は未使用(画像版の
``projective_trans_image`` とは異なり、この輪郭版は ``b`` を使わない)。

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
