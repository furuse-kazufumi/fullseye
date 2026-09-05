---
op: sp_plateaus
dim: 2d
category: subpix
in: image
out: contour
halcon: plateaus
examples: [gallery2d_geometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# sp_plateaus — 2D `subpix` op

- **データ種**: `image` → `contour`
- **呼び出し**: `fullseye.apply(img, "sp_plateaus", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `plateaus`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

同じ（量子化した）グレー値が連結した平坦領域（プラトー）の重心をサブピクセル位置として返す（HALCON ``plateaus`` に相当）。

隣接画素同士がしきい値 ``q = 1e-6 + 0.05*a`` 以内で等しければ同じ平坦領域とみなす（Union-Find で連結成分化）。``a`` はこの許容量子化幅と最小面積（``min_area = 2 + round(6*a)``、これ未満の領域は無視）の両方を振る。``b`` は未使用。戻り値は CONTOUR で、各プラトーにつき 1 点（その領域の画素座標の平均、単位はピクセル）。入力が 200,000 画素を超える場合は安全側で空集合を返す（計算量ガード）。

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

[sp_local_max_sub_pix](sp_local_max_sub_pix.md) · [sp_local_min_sub_pix](sp_local_min_sub_pix.md) · [sp_saddle_points_sub_pix](sp_saddle_points_sub_pix.md) · [sp_critical_points_sub_pix](sp_critical_points_sub_pix.md) · [sp_lowlands_center](sp_lowlands_center.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
