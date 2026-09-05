---
op: hx_gen_derivative_filter
dim: 2d
category: halcon_ext
in: image
out: image
halcon: gen_derivative_filter
examples: [gallery2d_halcon_ext]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# hx_gen_derivative_filter — 2D `halcon_ext` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "hx_gen_derivative_filter", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `gen_derivative_filter`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

周波数領域の微分フィルタ。``a`` が微分の階数、``b`` が向き。

HALCON の ``gen_derivative_filter`` は Derivative(x / y / xx / yy / xy)と
次数を取るが、ここは長らく ``|f|`` を正規化して返すだけで、**入力の中身も
つまみも一切見ていなかった** —— 2026-09-02 実測で、同じ形なら
``a``/``b`` を変えても、別の絵を渡しても、返りが**バイト一致**だった
(兄弟の ``hx_gen_lowpass`` / ``hx_gen_highpass`` / ``hx_gen_bandfilter`` は
つまみで変わるので、この 1 件だけ浮いていた)。

* ``a`` : 階数 1〜2(``|f|`` か ``|f|^2``)。2 階はラプラシアンに対応する。
* ``b`` : 向き。0 で x 方向 ``|f_x|``、1 で y 方向 ``|f_y|``、間は等方 ``|f|``
  へ滑らかに混ぜる(0.5 でちょうど等方)。

返りは周波数領域の**フィルタそのもの**(HALCON の gen_* と同じ約束)なので、
入力は形を決めるためだけに使う。ただし形だけでなく**つまみでちゃんと変わる**
ようになったので、進化が階数と向きを選べる。

## 詳しい使い方ガイド

- [gallery2d_halcon_ext ファミリ ガイド](../guides/gallery2d_halcon_ext.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_halcon_ext](../../../../examples/gallery2d_halcon_ext.py) — `py -3.11 examples/gallery2d_halcon_ext.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`halcon_ext`)

[hx_gen_circle](hx_gen_circle.md) · [hx_gen_ellipse](hx_gen_ellipse.md) · [hx_gen_rectangle2](hx_gen_rectangle2.md) · [hx_gen_checker_region](hx_gen_checker_region.md) · [hx_gen_grid_region](hx_gen_grid_region.md) · [hx_gabor](hx_gabor.md) · [hx_fit_surface1](hx_fit_surface1.md) · [hx_fit_surface2](hx_fit_surface2.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
