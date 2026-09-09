---
op: hx_fit_circle_contour
dim: 2d
category: halcon_ext
in: contour
out: feature
halcon: fit_circle_contour_xld
examples: [gallery2d_halcon_ext]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# hx_fit_circle_contour — 2D `halcon_ext` op

- **データ種**: `contour` → `feature`
- **呼び出し**: `fullseye.apply(img, "hx_fit_circle_contour", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `fit_circle_contour_xld`(意味・パラメータは HALCON リファレンスが参考になる)

![hx_fit_circle_contour: input → output](../../_fig/hx_fit_circle_contour.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

*つまみ a は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![hx_fit_circle_contour: stages](../../_fig/hx_fit_circle_contour.chain.jpg)

## 使い方

Kåsa 代数法で contour 点に円を当て、フィット残差(RMS)を返す(小=円に近い)。

全 contour の点をまとめ、Kåsa の代数法(``[x, y, 1]·sol = x^2 + y^2`` を最小二乗で解き、中心
``(sol0/2, sol1/2)``、半径 ``sqrt(sol2 + cx^2 + cy^2)``)で円を当て、各点の中心からの距離と半径の差の RMS を
``max(H, W)`` で割って 1 で頭打ちした ``np.float64`` で返す。円のパラメータ自体は返さない。

- ``a``, ``b`` は未使用。
- 点が 3 個未満なら 0.0(完全な円と区別できない)。半径の根号の中が負になれば半径 0 として扱う。

代数法は幾何学的な距離の最小化ではないので、円弧が短い(角度範囲が狭い)点群や外れ値では半径が偏る。
ほぼ直線上の点群では最小ノルム解の半径が非常に大きくなり、残差は小さく出る(直線が「大きな円」に見える)。
円らしさの判定には ``hx_regress_contours`` と併用して直線を除く。包含円の半径は ``hx_smallest_circle_xld``。

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
hx_fit_circle_contour 0.50 0.50
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
