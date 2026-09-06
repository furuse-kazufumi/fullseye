---
op: hx_test_region_points
dim: 2d
category: halcon_ext
in: region
out: feature
halcon: test_region_points
examples: [gallery2d_halcon_ext]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# hx_test_region_points — 2D `halcon_ext` op

- **データ種**: `region` → `feature`
- **呼び出し**: `fullseye.apply(img, "hx_test_region_points", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `test_region_points`(意味・パラメータは HALCON リファレンスが参考になる)

![hx_test_region_points: input → output](../../_fig/hx_test_region_points.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![hx_test_region_points: knob a sweep](../../_fig/hx_test_region_points.a.jpg)

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![hx_test_region_points: stages](../../_fig/hx_test_region_points.chain.jpg)

## 使い方

格子状の複数点のうち region に含まれる割合(test_region_points)。

``v > 0.5`` の region を ``step`` 画素おきの格子(``reg[::step, ::step]``、原点は (0,0))でサンプリングし、
格子点のうち region に入っている割合を ``np.float64``(0〜1)で返す。

- ``a`` → 格子間隔 ``step = max(2, int((0.1 + 0.3*a) * min(h, w)))``(短辺の 10%〜40%、最小 2 画素)。
- ``b`` は未使用。
- 格子点が 0 個なら 0.0。

格子が細かければ region の面積率の近似になり、粗ければ「代表点がどれだけ region に落ちるか」の粗い指標になる。
格子の原点は固定なので、region を少しずらすだけで値が飛ぶ。面積率そのものが欲しいなら region の平均値を
取る方が正確。1 点の判定は ``hx_test_region_point``。

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
hx_test_region_points 0.50 0.50
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
