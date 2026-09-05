---
op: acos_image
dim: 2d
category: arithmetic
in: image
out: image
halcon: acos_image
examples: [gallery2d_gray_arith]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# acos_image — 2D `arithmetic` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "acos_image", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `acos_image`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

``arccos(x) / π`` で [0,1] を [0,1] に写す逆余弦 LUT。``asin_image`` を
反転させた形(単調減少)で、x=0 で最大(1)、x=1 で最小(0)になる。HALCON の
``acos_image``（Calculate the arccosine of an image.）の代役。

``a``, ``b`` は未使用。``asin_image`` と同様に端点近傍で傾きが急峻になる
(数値的に敏感)。単純な階調反転がしたいだけなら ``invert_image`` の方が
挙動が読みやすい。

## 詳しい使い方ガイド

- [gallery2d_gray_arith ファミリ ガイド](../guides/gallery2d_gray_arith.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_gray_arith](../../../../examples/gallery2d_gray_arith.py) — `py -3.11 examples/gallery2d_gray_arith.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`arithmetic`)

[abs_image](abs_image.md) · [sqrt_image](sqrt_image.md) · [exp_image](exp_image.md) · [log_image](log_image.md) · [sin_image](sin_image.md) · [cos_image](cos_image.md) · [asin_image](asin_image.md) · [atan_image](atan_image.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
