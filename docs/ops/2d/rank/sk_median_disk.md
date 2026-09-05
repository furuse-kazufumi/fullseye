---
op: sk_median_disk
dim: 2d
category: rank
in: image
out: image
halcon: median_image
examples: [gallery2d_smoothing_rank]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# sk_median_disk — 2D `rank` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "sk_median_disk", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `median_image`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

円盤(disk)形の footprint によるメディアンフィルタ。通常の正方形カーネルと違い、円形に近い等方的な平滑化になる。

HALCON の `median_image`(Compute a median filter with various masks.)に相当。実装は ``filters.median(v, footprint=disk(1+int(a*3)))`` —— a は円盤の半径を 1〜4 に振る(半径が大きいほど強く滑らかになるが細部も消える)。b は未使用。

## 詳しい使い方ガイド

- [gallery2d_smoothing_rank ファミリ ガイド](../guides/gallery2d_smoothing_rank.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_smoothing_rank](../../../../examples/gallery2d_smoothing_rank.py) — `py -3.11 examples/gallery2d_smoothing_rank.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](median.md) · [min_filter](min_filter.md) · [max_filter](max_filter.md)

## 同カテゴリ(`rank`)

[median](median.md) · [min_filter](min_filter.md) · [max_filter](max_filter.md) · [percentile](percentile.md) · [cv_median](cv_median.md) · [median_image](median_image.md) · [median_rect](median_rect.md) · [median_separate](median_separate.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
