---
op: cv_bilateral
dim: 2d
category: smoothing
in: image
out: image
halcon: bilateral_filter
examples: [gallery2d_smoothing_rank]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# cv_bilateral — 2D `smoothing` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "cv_bilateral", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `bilateral_filter`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

バイラテラルフィルタ(OpenCV 実装)。空間的な近さと輝度値の近さの両方を重みにしたガウス的平滑化で、エッジ(輝度差の大きい境界)をぼかさずに平坦部だけを滑らかにする。

HALCON の `bilateral_filter`(bilateral filtering of an image.)に相当。実装は ``cv2.bilateralFilter(v, d=5, sigmaColor=0.05+0.4*b, sigmaSpace=1.0+3.0*a)`` —— カーネル直径 d は 5 に固定、**a は空間方向の広がり sigmaSpace を 1.0〜4.0 に、b は輝度方向の許容差 sigmaColor を 0.05〜0.45 に振る**(引数の並びが sigmaColor, sigmaSpace の順なので a/b の対応がずれやすい点に注意)。

## 詳しい使い方ガイド

- [gallery2d_smoothing_rank ファミリ ガイド](../guides/gallery2d_smoothing_rank.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_smoothing_rank](../../../../examples/gallery2d_smoothing_rank.py) — `py -3.11 examples/gallery2d_smoothing_rank.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](gaussian.md) · [mean_box](mean_box.md) · [bilateral](bilateral.md) · [unsharp](unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`smoothing`)

[gaussian](gaussian.md) · [mean_box](mean_box.md) · [bilateral](bilateral.md) · [unsharp](unsharp.md) · [sk_tv](sk_tv.md) · [sk_wavelet](sk_wavelet.md) · [sk_rolling_ball](sk_rolling_ball.md) · [sk_nlm](sk_nlm.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
