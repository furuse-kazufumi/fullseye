---
op: hx_test_self_intersect
dim: 2d
category: halcon_ext
in: contour
out: feature
halcon: test_self_intersection_xld
examples: [gallery2d_halcon_ext]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# hx_test_self_intersect — 2D `halcon_ext` op

- **データ種**: `contour` → `feature`
- **呼び出し**: `fullseye.apply(img, "hx_test_self_intersect", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `test_self_intersection_xld`(意味・パラメータは HALCON リファレンスが参考になる)

![hx_test_self_intersect: input → output](../../_fig/hx_test_self_intersect.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

*つまみ a は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![hx_test_self_intersect: stages](../../_fig/hx_test_self_intersect.chain.jpg)

## 使い方

自己交差する contour の割合を返す(feature)。非隣接セグメント対を判定。

各 contour(点数 4 以上)について、隣接しない線分の全対 ``(i, i+1)`` と ``(j, j+1)``(``j >= i+2``)を
向き付き面積の符号(ccw 判定)で交差判定し、1 対でも交差する contour の本数を全 contour 数で割った割合を
``np.float64`` で返す。始点と終点が一致(距離 1e-6 未満)する閉曲線では、最初の線分と最後の線分の対は隣接扱いで
除外する。

- ``a``, ``b`` は未使用。
- contour が無ければ 0.0。点数 3 以下の contour は交差なしとして数える。

判定は真に交差する場合のみで、端点が相手の線分上に乗る接触や同一直線上の重なりは検出しない(不等号が厳密)。
計算量は contour ごとに線分数の 2 乗で、点の多い contour では遅い(``hx_split_contours`` や
``smooth_contours_xld`` で点を減らしてから)。``hx_gen_parallel_contour`` で内側にずらした輪郭の破綻検出に使える。

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
hx_test_self_intersect 0.50 0.50
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
