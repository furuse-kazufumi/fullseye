---
op: hx_test_closed_xld
dim: 2d
category: halcon_ext
in: contour
out: feature
halcon: test_closed_xld
examples: [gallery2d_halcon_ext]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# hx_test_closed_xld — 2D `halcon_ext` op

- **データ種**: `contour` → `feature`
- **呼び出し**: `fullseye.apply(img, "hx_test_closed_xld", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `test_closed_xld`(意味・パラメータは HALCON リファレンスが参考になる)

![hx_test_closed_xld: input → output](../../_fig/hx_test_closed_xld.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![hx_test_closed_xld: knob a sweep](../../_fig/hx_test_closed_xld.a.jpg)

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![hx_test_closed_xld: stages](../../_fig/hx_test_closed_xld.chain.jpg)

## 使い方

閉じている contour の割合を返す(端点間距離が閾値未満=閉、feature)。

contour dict の各 contour について、点数が 3 以上かつ始点と終点のユークリッド距離が ``tol`` 以下なら
「閉じている」と数え、閉じた contour の本数を全 contour 数で割った割合を ``np.float64`` で返す。

- ``a`` → 許容距離 ``tol = 1 + a*4``(1〜5 画素)。
- ``b`` は未使用。
- contour が無ければ 0.0。

始点=終点を重複させて閉じる ``close_contours_xld`` の出力は距離 0 なので必ず閉と判定される。
``hx_clip_end_points`` や ``hx_clip_contours`` で端を落とした後は開いた扱いになる。個々の contour がどれかは
返さない(割合のみ)。

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
hx_test_closed_xld 0.50 0.50
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
