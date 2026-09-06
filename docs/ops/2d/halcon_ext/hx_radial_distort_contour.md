---
op: hx_radial_distort_contour
dim: 2d
category: halcon_ext
in: contour
out: contour
halcon: change_radial_distortion_contours_xld
examples: [gallery2d_halcon_ext]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# hx_radial_distort_contour — 2D `halcon_ext` op

- **データ種**: `contour` → `contour`
- **呼び出し**: `fullseye.apply(img, "hx_radial_distort_contour", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `change_radial_distortion_contours_xld`(意味・パラメータは HALCON リファレンスが参考になる)

![hx_radial_distort_contour: input → output](../../_fig/hx_radial_distort_contour.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![hx_radial_distort_contour: knob a sweep](../../_fig/hx_radial_distort_contour.a.jpg)

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![hx_radial_distort_contour: stages](../../_fig/hx_radial_distort_contour.chain.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![hx_radial_distort_contour: other inputs](../../_fig/hx_radial_distort_contour.inputs.jpg)

## 使い方

contour に放射歪み r' = r(1 + k r^2) を適用(k は (a-0.5) で樽/糸巻き)。

各 contour の点を画像中心 ``(H/2, W/2)`` からの相対座標 ``d`` にし、正規化半径 ``r = |d| / (max(H, W)/2)`` に
対して ``d' = d * (1 + k*r^2)`` と伸縮させた contour を返す(放射歪みモデルの 1 次項)。

- ``a`` → 歪み係数 ``k = (a - 0.5) * 1.5``(-0.75〜+0.75)。``k < 0`` で点が中心に寄る(樽型)、``k > 0`` で
外へ広がる(糸巻き型)、a=0.5 で無変化。
- ``b`` は未使用。

半径は画像長辺の半分で正規化しているので、画像の隅で ``r`` が 1 前後になり、``k = ±0.75`` なら隅の点は
1.75 倍/0.25 倍まで動く。逆変換は無い(``k`` の符号を反転しても厳密には戻らない)。レンズ歪みの影響を contour
計測(``hx_fit_circle_contour`` 等)で試す、あるいは合成的にデータを増やす用途。

## 詳しい使い方ガイド

- [gallery2d_halcon_ext ファミリ ガイド](../guides/gallery2d_halcon_ext.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
threshold 0.50 0.50
sk_find_contours 0.50 0.50
hx_radial_distort_contour 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_halcon_ext](../../../../examples/gallery2d_halcon_ext.py) — `py -3.11 examples/gallery2d_halcon_ext.py`

## 型が繋がる次の op(`contour` を入力に取れる)

[identity](../misc/identity.md) · [select_contours](../contour/select_contours.md) · [smooth_contours](../contour/smooth_contours.md) · [fit_line_contours](../contour/fit_line_contours.md) · [contours_to_region](../contour/contours_to_region.md) · [count_contours](../features/count_contours.md) · [total_length](../features/total_length.md) · [select_contours_xld](../contour/select_contours_xld.md)

## 同カテゴリ(`halcon_ext`)

[hx_gen_circle](hx_gen_circle.md) · [hx_gen_ellipse](hx_gen_ellipse.md) · [hx_gen_rectangle2](hx_gen_rectangle2.md) · [hx_gen_checker_region](hx_gen_checker_region.md) · [hx_gen_grid_region](hx_gen_grid_region.md) · [hx_gabor](hx_gabor.md) · [hx_fit_surface1](hx_fit_surface1.md) · [hx_fit_surface2](hx_fit_surface2.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
