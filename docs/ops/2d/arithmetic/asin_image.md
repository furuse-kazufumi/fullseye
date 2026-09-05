---
op: asin_image
dim: 2d
category: arithmetic
in: image
out: image
halcon: asin_image
examples: [gallery2d_gray_arith]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# asin_image — 2D `arithmetic` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "asin_image", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `asin_image`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

``arcsin(x) / (π/2)`` で [0,1] を [0,1] に写す逆正弦 LUT。x=0 近傍と x=1
近傍で傾きが急峻になり(定義域端で導関数が発散する)、中間階調を圧縮して
両端のコントラストを強調する効果を持つ。HALCON の ``asin_image``
（Calculate the arcsine of an image.）の代役。

``a``, ``b`` は未使用。端点付近で数値的に敏感になる点に注意(x が 1 にごく
近いとわずかな量子化誤差でも出力が大きく動く)。

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

[abs_image](abs_image.md) · [sqrt_image](sqrt_image.md) · [exp_image](exp_image.md) · [log_image](log_image.md) · [sin_image](sin_image.md) · [cos_image](cos_image.md) · [acos_image](acos_image.md) · [atan_image](atan_image.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
