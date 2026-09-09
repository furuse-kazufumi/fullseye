---
op: hx_fit_ellipse_contour
dim: 2d
category: halcon_ext
in: contour
out: feature
halcon: fit_ellipse_contour_xld
examples: [gallery2d_halcon_ext]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# hx_fit_ellipse_contour — 2D `halcon_ext` op

- **データ種**: `contour` → `feature`
- **呼び出し**: `fullseye.apply(img, "hx_fit_ellipse_contour", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `fit_ellipse_contour_xld`(意味・パラメータは HALCON リファレンスが参考になる)

![hx_fit_ellipse_contour: input → output](../../_fig/hx_fit_ellipse_contour.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

*つまみ a は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![hx_fit_ellipse_contour: stages](../../_fig/hx_fit_ellipse_contour.chain.jpg)

## 使い方

2 次モーメントから楕円を当て、軸比(短/長=真円で 1、細長いほど 0)を返す。

全 contour の点をまとめて座標共分散行列の固有値 ``λmin, λmax`` を取り、``sqrt(λmin/λmax)``(主軸方向の標準偏差
の比 = 慣性楕円の短軸/長軸)を ``np.float64`` で返す。

- ``a``, ``b`` は未使用。
- 点が 3 個未満、または ``λmax <= 1e-9``(全点一致)なら 0.0。負の固有値は 0 に clip する。

1 に近いほど等方(真円)、0 に近いほど細長い。楕円境界を当てはめる代数的フィットではなく点群の 2 次モーメント
なので、点の密度の偏りや欠けた弧では軸比が変わる。楕円の傾き・中心は返さない(``orientation_xld`` /
``area_center_xld``)。``cv2.fitEllipse`` 版は ``elliptic_axis_xld``。楕円からの逸脱量は ``hx_dist_ellipse_contour``。

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
hx_fit_ellipse_contour 0.50 0.50
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
