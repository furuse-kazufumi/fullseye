---
op: xg_elliptic_axis
dim: 2d
category: xldgeom
in: contour
out: feature
halcon: elliptic_axis_points_xld
examples: [gallery2d_geometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# xg_elliptic_axis — 2D `xldgeom` op

- **データ種**: `contour` → `feature`
- **呼び出し**: `fullseye.apply(img, "xg_elliptic_axis", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `elliptic_axis_points_xld`(意味・パラメータは HALCON リファレンスが参考になる)

![xg_elliptic_axis: input → output](../../_fig/xg_elliptic_axis.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

*つまみ a は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![xg_elliptic_axis: stages](../../_fig/xg_elliptic_axis.chain.jpg)

## 使い方

Major/minor axis ratio sqrt(lambda_max/lambda_min) of the point set.

全輪郭の点(閉輪郭の重複終点は除く)の (row, col) 共分散行列の固有値から、
等価楕円の長軸/短軸比 ``sqrt(λ_max/λ_min)`` を返す。``a``, ``b`` は未使用。

返り値は ``numpy.float64`` で 1 以上。等方な点配置で 1、細長いほど大きい。
``λ_min <= 1e-12``(全点が一直線)では ``λ_max > 1e-12`` なら 1e6、そうで
なければ 1.0。それ以外でも上限 1e6 で打ち切る。点が 2 個未満なら 1.0。
非有限になった場合も 1.0 に落とす。[0,1] に正規化されていない量なので、
他の特徴量と並べる際はスケールに注意(1e6 の外れ値が出うる)。
``xg_eccentricity`` は同じ固有値を [0,1] に写した版で、こちらは比を直接
見たいときに使う。軸ではなく外接矩形の縦横比なら ``xg_height_width_ratio``
(こちらは向きに依存する)。

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
xg_elliptic_axis 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_geometry](../../../../examples/gallery2d_geometry.py) — `py -3.11 examples/gallery2d_geometry.py`

## 型が繋がる次の op(`feature` を入力に取れる)

[identity](../misc/identity.md)

## 同カテゴリ(`xldgeom`)

[xg_moments](xg_moments.md) · [xg_area_center](xg_area_center.md) · [xg_eccentricity](xg_eccentricity.md) · [xg_orientation](xg_orientation.md) · [xg_height_width_ratio](xg_height_width_ratio.md) · [xg_regress_contours](xg_regress_contours.md) · [xg_clip_contours](xg_clip_contours.md) · [xg_gen_polygons](xg_gen_polygons.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
