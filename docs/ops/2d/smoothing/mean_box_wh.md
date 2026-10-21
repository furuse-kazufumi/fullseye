---
op: mean_box_wh
dim: 2d
category: smoothing
in: image
out: image
halcon: mean_image
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# mean_box_wh — 2D `smoothing` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "mean_box_wh", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `mean_image`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

幅と高さを独立に選ぶ平均（box）フィルタ。HALCON の ``mean_image``（Smooth by averaging.）に相当。

``a`` が窓の幅、``b`` が窓の高さで、各ノブは ``1 + 2 * min(7, int(8 * clip(knob, 0, 1)))`` で
奇数 1, 3, …, 15 に写す（偶数の幅・高さを次の奇数へ切り上げるのと同じ）。境界は常に
``reflect``。幅と高さが同じなら、同じ窓・``reflect`` の ``mean_box`` とビット一致する。
例: ``_mean_box_wh(np.eye(5), 0.2, 0.4)``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](gaussian.md) · [mean_box](mean_box.md) · [bilateral](bilateral.md) · [kuwahara](kuwahara.md) · [unsharp](unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md)

## 同カテゴリ(`smoothing`)

[gaussian](gaussian.md) · [mean_box](mean_box.md) · [bilateral](bilateral.md) · [kuwahara](kuwahara.md) · [unsharp](unsharp.md) · [sk_tv](sk_tv.md) · [sk_wavelet](sk_wavelet.md) · [sk_rolling_ball](sk_rolling_ball.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
