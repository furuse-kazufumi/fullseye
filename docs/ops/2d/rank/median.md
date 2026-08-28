---
op: median
dim: 2d
category: rank
in: image
out: image
halcon: median_image
examples: [consumer_onocollo, gallery2d_smoothing_rank, perception_pipeline, quickstart]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# median — 2D `rank` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "median", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `median_image`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

型契約は `image → image`。挙動の言語説明は下記のファミリ使い方ガイドと実行可能サンプルを参照(ここでは推測を書かない)。

## 詳しい使い方ガイド

- [gallery2d_smoothing_rank ファミリ ガイド](../guides/gallery2d_smoothing_rank.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [consumer_onocollo](../../../../examples/consumer_onocollo.py) — `py -3.11 examples/consumer_onocollo.py`
- [gallery2d_smoothing_rank](../../../../examples/gallery2d_smoothing_rank.py) — `py -3.11 examples/gallery2d_smoothing_rank.py`
- [perception_pipeline](../../../../examples/perception_pipeline.py) — `py -3.11 examples/perception_pipeline.py`
- [quickstart](../../../../examples/quickstart.py) — `py -3.11 examples/quickstart.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [min_filter](min_filter.md) · [max_filter](max_filter.md) · [percentile](percentile.md)

## 同カテゴリ(`rank`)

[min_filter](min_filter.md) · [max_filter](max_filter.md) · [percentile](percentile.md) · [sk_median_disk](sk_median_disk.md) · [cv_median](cv_median.md) · [median_image](median_image.md) · [median_rect](median_rect.md) · [median_separate](median_separate.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
