---
op: m1_measure_pos
dim: 2d
category: measure1d
in: image
out: contour
halcon: measure_pos
examples: [gallery2d_contour_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# m1_measure_pos — 2D `measure1d` op

- **データ種**: `image` → `contour`
- **呼び出し**: `fullseye.apply(img, "m1_measure_pos", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `measure_pos`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

中心を通るキャリパー線上のサブピクセルエッジ位置を抽出する（HALCON``measure_pos`` に相当: 矩形/円弧に垂直な直線エッジを検出する）。

線は画像中心を通り、``a`` で向きを ``theta = a*pi`` に振る。輝度プロファイルをガウシアンで軽く平滑化してから ``|d/ds gray|`` のピークをサブピクセル（3 点放物線補間）で検出し、``b``（0〜1）を最大振幅に対する相対しきい値として弱いエッジを捨てる。戻り値は CONTOUR（``{"shape": (H,W), "cs": [1x2 の (row, col) 点, ...]}``）、座標単位は入力画像のピクセル。主な使い道はエッジ数を ``count_contours``で数えること。

## 詳しい使い方ガイド

- [gallery2d_contour_measure ファミリ ガイド](../guides/gallery2d_contour_measure.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [measurement_uncertainty](../../math/guides/measurement_uncertainty.md) — 計測の不確かさと校正の知識 — 「測れている」を主張するために

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_contour_measure](../../../../examples/gallery2d_contour_measure.py) — `py -3.11 examples/gallery2d_contour_measure.py`

## 型が繋がる次の op(`contour` を入力に取れる)

[identity](../misc/identity.md) · [select_contours](../contour/select_contours.md) · [smooth_contours](../contour/smooth_contours.md) · [fit_line_contours](../contour/fit_line_contours.md) · [contours_to_region](../contour/contours_to_region.md) · [count_contours](../features/count_contours.md) · [total_length](../features/total_length.md) · [select_contours_xld](../contour/select_contours_xld.md)

## 同カテゴリ(`measure1d`)

[m1_measure_projection](m1_measure_projection.md) · [m1_measure_thresh](m1_measure_thresh.md) · [m1_measure_pairs](m1_measure_pairs.md) · [m1_fuzzy_measure_pos](m1_fuzzy_measure_pos.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
