---
op: xcv_inpaint
dim: 2d
category: restoration
in: image
out: image
examples: [gallery2d_smoothing_rank]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# xcv_inpaint — 2D `restoration` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "xcv_inpaint", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

欠損領域を推定して埋める修復(inpainting)。

8bit 変換後、極端に明るい(>235)/暗い(<20)画素を「欠損」とみなして
自動マスクし、OpenCV の Telea 法(高速マーチング法ベース、
``cv2.INPAINT_TELEA``)で周囲から埋める。``xsk_inpaint``
(biharmonic 法)と同じ発想の別アルゴリズム版。

半径 3 画素の近傍を使う(固定)。``a``, ``b`` は未使用。しきい値が
固定のため、本来意味のある白飛び/黒つぶれ画素まで埋められてしまう
場合がある。

## 詳しい使い方ガイド

- [gallery2d_smoothing_rank ファミリ ガイド](../guides/gallery2d_smoothing_rank.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_smoothing_rank](../../../../examples/gallery2d_smoothing_rank.py) — `py -3.11 examples/gallery2d_smoothing_rank.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`restoration`)

[xsk_inpaint](xsk_inpaint.md) · [xsk_richardson_lucy](xsk_richardson_lucy.md) · [xsk_unwrap_phase](xsk_unwrap_phase.md) · [xsk2_wiener](xsk2_wiener.md) · [xcv3_inpaint_ns](xcv3_inpaint_ns.md) · [iv_richardson_lucy](iv_richardson_lucy.md) · [iv_wiener_deconv_spatial](iv_wiener_deconv_spatial.md) · [iv_unsharp_deblur](iv_unsharp_deblur.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
