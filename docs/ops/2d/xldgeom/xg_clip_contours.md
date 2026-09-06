---
op: xg_clip_contours
dim: 2d
category: xldgeom
in: contour
out: contour
examples: [gallery2d_geometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# xg_clip_contours — 2D `xldgeom` op

- **データ種**: `contour` → `contour`
- **呼び出し**: `fullseye.apply(img, "xg_clip_contours", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

![xg_clip_contours: input → output](../../_fig/xg_clip_contours.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![xg_clip_contours: knob a sweep](../../_fig/xg_clip_contours.a.jpg)

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![xg_clip_contours: stages](../../_fig/xg_clip_contours.chain.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![xg_clip_contours: other inputs](../../_fig/xg_clip_contours.inputs.jpg)

## 使い方

Drop contours whose polyline length is below a * max-length (a in [0,1]).

各輪郭の折れ線長(隣接点間のユークリッド距離の和)を求め、最長の輪郭の長さ
``L_max`` に対して ``length >= a * L_max`` を満たす輪郭だけ残す。``a`` は
[0,1] に clip され、``a=0`` で全輪郭を残し、``a=1`` で最長の輪郭(同長なら
複数)だけ残す。``b`` は未使用。

返り値は入力と同じ ``{"shape", "cs"}`` 形式の輪郭辞書(点配列はコピー)。
輪郭が無ければ ``cs`` は空。``L_max <= 1e-12``(全輪郭が 1 点)なら全輪郭を
そのまま返す。しきい値が画像サイズでなく「最長輪郭に対する相対値」なので、
最長の輪郭が変わると選別基準も動く(点数の絶対値で選ぶなら
``select_contours_xld``)。名前から想像される矩形での切り取りではなく、
長さによる選別である(矩形で切るのは ``xg_crop_contours`` / ``hx_clip_contours``)。
閉輪郭の重複終点も長さに含むが、0 長の辺なので影響しない。

## 詳しい使い方ガイド

- [gallery2d_geometry ファミリ ガイド](../guides/gallery2d_geometry.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
threshold 0.50 0.50
sk_find_contours 0.50 0.50
xg_clip_contours 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_geometry](../../../../examples/gallery2d_geometry.py) — `py -3.11 examples/gallery2d_geometry.py`

## 型が繋がる次の op(`contour` を入力に取れる)

[identity](../misc/identity.md) · [select_contours](../contour/select_contours.md) · [smooth_contours](../contour/smooth_contours.md) · [fit_line_contours](../contour/fit_line_contours.md) · [contours_to_region](../contour/contours_to_region.md) · [count_contours](../features/count_contours.md) · [total_length](../features/total_length.md) · [select_contours_xld](../contour/select_contours_xld.md)

## 同カテゴリ(`xldgeom`)

[xg_moments](xg_moments.md) · [xg_area_center](xg_area_center.md) · [xg_eccentricity](xg_eccentricity.md) · [xg_orientation](xg_orientation.md) · [xg_elliptic_axis](xg_elliptic_axis.md) · [xg_height_width_ratio](xg_height_width_ratio.md) · [xg_regress_contours](xg_regress_contours.md) · [xg_gen_polygons](xg_gen_polygons.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
