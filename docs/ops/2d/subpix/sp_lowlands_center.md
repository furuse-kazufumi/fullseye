---
op: sp_lowlands_center
dim: 2d
category: subpix
in: image
out: contour
halcon: lowlands_center
examples: [gallery2d_geometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# sp_lowlands_center — 2D `subpix` op

- **データ種**: `image` → `contour`
- **呼び出し**: `fullseye.apply(img, "sp_lowlands_center", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `lowlands_center`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

極小の「盆地」（周囲より低い平坦領域）の重心を返す（HALCON ``lowlands_center`` に相当）。

``sp_plateaus`` と同じ量子化による平坦領域抽出を行った上で、外周の画素がすべて厳密に高い（領域極小である）ものだけを残し、さらに深さ（外周の最小値との差）が ``min_depth = 0.01 + 0.40*a`` 以上のものだけを採用する。``b`` は未使用。戻り値は CONTOUR、各盆地につき 1 点（重心座標、単位はピクセル）。入力が 200,000 画素を超える場合は安全側で空集合を返す。

## 詳しい使い方ガイド

- [gallery2d_geometry ファミリ ガイド](../guides/gallery2d_geometry.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [measurement_uncertainty](../../math/guides/measurement_uncertainty.md) — 計測の不確かさと校正の知識 — 「測れている」を主張するために

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_geometry](../../../../examples/gallery2d_geometry.py) — `py -3.11 examples/gallery2d_geometry.py`

## 型が繋がる次の op(`contour` を入力に取れる)

[identity](../misc/identity.md) · [select_contours](../contour/select_contours.md) · [smooth_contours](../contour/smooth_contours.md) · [fit_line_contours](../contour/fit_line_contours.md) · [contours_to_region](../contour/contours_to_region.md) · [count_contours](../features/count_contours.md) · [total_length](../features/total_length.md) · [select_contours_xld](../contour/select_contours_xld.md)

## 同カテゴリ(`subpix`)

[sp_local_max_sub_pix](sp_local_max_sub_pix.md) · [sp_local_min_sub_pix](sp_local_min_sub_pix.md) · [sp_saddle_points_sub_pix](sp_saddle_points_sub_pix.md) · [sp_critical_points_sub_pix](sp_critical_points_sub_pix.md) · [sp_plateaus](sp_plateaus.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
