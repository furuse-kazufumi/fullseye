---
op: xcv3_inpaint_ns
dim: 2d
category: restoration
in: image
out: image
examples: [gallery2d_smoothing_rank]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# xcv3_inpaint_ns — 2D `restoration` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "xcv3_inpaint_ns", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Navier-Stokes 法によるインペインティング(OpenCV ``cv2.inpaint``、``INPAINT_NS``)。周辺画素から流体力学的に情報を伝搬させて欠損領域を埋める修復アルゴリズム。

このレシピはマスクを外部から受け取らず、画像自身の中で輝度が 235 超(白飛び)または 20 未満(黒つぶれ)の画素を自動的に欠損とみなして半径 3 px でインペイントする。``a``, ``b`` は未使用。任意のマスクで穴埋めしたい用途には使えない点に注意。

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

[xsk_inpaint](xsk_inpaint.md) · [xsk_richardson_lucy](xsk_richardson_lucy.md) · [xsk_unwrap_phase](xsk_unwrap_phase.md) · [xcv_inpaint](xcv_inpaint.md) · [xsk2_wiener](xsk2_wiener.md) · [iv_richardson_lucy](iv_richardson_lucy.md) · [iv_wiener_deconv_spatial](iv_wiener_deconv_spatial.md) · [iv_unsharp_deblur](iv_unsharp_deblur.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
