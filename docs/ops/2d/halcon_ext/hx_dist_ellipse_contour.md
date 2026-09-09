---
op: hx_dist_ellipse_contour
dim: 2d
category: halcon_ext
in: contour
out: feature
halcon: dist_ellipse_contour_xld
examples: [gallery2d_halcon_ext]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# hx_dist_ellipse_contour — 2D `halcon_ext` op

- **データ種**: `contour` → `feature`
- **呼び出し**: `fullseye.apply(img, "hx_dist_ellipse_contour", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `dist_ellipse_contour_xld`(意味・パラメータは HALCON リファレンスが参考になる)

![hx_dist_ellipse_contour: input → output](../../_fig/hx_dist_ellipse_contour.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

*つまみ a は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![hx_dist_ellipse_contour: stages](../../_fig/hx_dist_ellipse_contour.chain.jpg)

## 使い方

contour 点の当てはめ楕円境界からの平均距離を返す(小=楕円に近い、feature)。

全 contour の点をまとめ、重心と座標共分散の固有分解から主軸系に移し、半軸を ``2*sqrt(λ)``(各主軸の 2σ)とする
楕円を当てて、各点の正規化半径 ``rad = sqrt((u/ax0)^2 + (v/ax1)^2)`` と 1 との差 ``|rad - 1|`` の平均を 1 で
頭打ちした ``np.float64`` で返す。

- ``a``, ``b`` は未使用。
- 点が 4 個未満なら 0.0。固有値は ``1e-9`` で下から clip。

注意: 値は画素距離ではなく楕円の正規化座標での差(無次元)。また半軸 2σ は「一様に塗られた楕円」に合う値で、
境界だけの点群では ``σ = 半軸/sqrt(2)`` になるため、完全な楕円輪郭でも 0 にならず約 0.29 の下駄が乗る(実測
0.2938)。比較用の相対指標として使い、絶対値で「楕円かどうか」を切らない。最大値版は ``hx_dist_ellipse_points``、
軸比は ``hx_fit_ellipse_contour``。

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
hx_dist_ellipse_contour 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_halcon_ext](../../../../examples/gallery2d_halcon_ext.py) — `py -3.11 examples/gallery2d_halcon_ext.py`

## 型が繋がる次の op(`feature` を入力に取れる)

[identity](../misc/identity.md)

## 同カテゴリ(`halcon_ext`)

[hx_gen_circle](hx_gen_circle.md) · [hx_gen_ellipse](hx_gen_ellipse.md) · [hx_gen_rectangle2](hx_gen_rectangle2.md) · [hx_gen_checker_region](hx_gen_checker_region.md) · [hx_gen_grid_region](hx_gen_grid_region.md) · [hx_gabor](hx_gabor.md) · [hx_fit_surface1](hx_fit_surface1.md) · [hx_fit_surface2](hx_fit_surface2.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
