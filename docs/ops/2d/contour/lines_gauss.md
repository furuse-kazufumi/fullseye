---
op: lines_gauss
dim: 2d
category: contour
in: image
out: contour
halcon: lines_gauss
examples: [gallery2d_contour_measure, poc_solar_el_inspection, poc_weld_bead_scan_angle]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# lines_gauss — 2D `contour` op

- **データ種**: `image` → `contour`
- **呼び出し**: `fullseye.apply(img, "lines_gauss", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `lines_gauss`(意味・パラメータは HALCON リファレンスが参考になる)

![lines_gauss: input → output](../../_fig/lines_gauss.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![lines_gauss: knob a sweep](../../_fig/lines_gauss.a.jpg)

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![lines_gauss: other inputs](../../_fig/lines_gauss.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

線状構造(リッジ)検出。``skimage.filters.frangi``(血管様のリッジ強調
フィルタ)の応答をしきい値(``0.1+0.4*a``)で二値化し、連結成分を輪郭点群
として返す。HALCON の ``lines_gauss``（Detect lines and their width.）が
本来行う「線の中心線+幅の推定」ではなく、リッジ強調画像のしきい値化に
単純化している(線幅の情報は返らない近似)。

``a`` がリッジ検出のしきい値を振る。``b`` は未使用。skimage が無い環境
ではこの分岐は呼べない。

## 詳しい使い方ガイド

- [gallery2d_contour_measure ファミリ ガイド](../guides/gallery2d_contour_measure.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
lines_gauss 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_contour_measure](../../../../examples/gallery2d_contour_measure.py) — `py -3.11 examples/gallery2d_contour_measure.py`
- [poc_solar_el_inspection](../../../../examples/poc_solar_el_inspection.py) — `py -3.11 examples/poc_solar_el_inspection.py`
- [poc_weld_bead_scan_angle](../../../../examples/poc_weld_bead_scan_angle.py) — `py -3.11 examples/poc_weld_bead_scan_angle.py`

## 型が繋がる次の op(`contour` を入力に取れる)

[identity](../misc/identity.md) · [select_contours](select_contours.md) · [smooth_contours](smooth_contours.md) · [fit_line_contours](fit_line_contours.md) · [contours_to_region](contours_to_region.md) · [count_contours](../features/count_contours.md) · [total_length](../features/total_length.md) · [select_contours_xld](select_contours_xld.md)

## 同カテゴリ(`contour`)

[select_contours](select_contours.md) · [smooth_contours](smooth_contours.md) · [fit_line_contours](fit_line_contours.md) · [contours_to_region](contours_to_region.md) · [sk_find_contours](sk_find_contours.md) · [edges_sub_pix](edges_sub_pix.md) · [select_contours_xld](select_contours_xld.md) · [smooth_contours_xld](smooth_contours_xld.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
