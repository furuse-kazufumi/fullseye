---
op: xsk_richardson_lucy
dim: 2d
category: restoration
in: image
out: image
examples: [gallery2d_smoothing_rank]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# xsk_richardson_lucy — 2D `restoration` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "xsk_richardson_lucy", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Richardson-Lucy デコンボリューション。ぼけを 3x3 の平均カーネル(box PSF)と
仮定して反復的に鮮鋭化する(skimage.restoration.richardson_lucy をそのまま呼ぶ)。

``a`` が反復回数を 2〜17 回の範囲で振る(回数が多いほど強く先鋭化するが、
ノイズ増幅やリンギングも増える)。``b`` は未使用。PSF は実際のぼけ量に関わらず
固定の 3x3 box を仮定するため、真の劣化過程と一致しない画像では改善が限定的、
または悪化することがある。

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

[xsk_inpaint](xsk_inpaint.md) · [xsk_unwrap_phase](xsk_unwrap_phase.md) · [xcv_inpaint](xcv_inpaint.md) · [xsk2_wiener](xsk2_wiener.md) · [xcv3_inpaint_ns](xcv3_inpaint_ns.md) · [iv_richardson_lucy](iv_richardson_lucy.md) · [iv_wiener_deconv_spatial](iv_wiener_deconv_spatial.md) · [iv_unsharp_deblur](iv_unsharp_deblur.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
