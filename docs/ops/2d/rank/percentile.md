---
op: percentile
dim: 2d
category: rank
in: image
out: image
halcon: rank_image
examples: [color_transport, gallery2d_smoothing_rank, image_quality_metrics, representation_roundtrip, vision_layout_from_catalog]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# percentile — 2D `rank` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "percentile", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `rank_image`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

任意パーセンタイルのランクフィルタ。HALCON の ``rank_image``（Compute a rank filter with arbitrary masks.）に相当。

``a`` が窓サイズを ``3,5,7,9``（``_k(a)``）に、``b`` が抽出するパーセンタイルを ``5〜95%``（``int(5+90b)``）に振る。``b`` が 0 に近いほど ``_min_filter``、1 に近いほど ``_max_filter``、中間で ``_median`` に近づく——3 op を 1 つに統合した一般形。

## 詳しい使い方ガイド

- [gallery2d_smoothing_rank ファミリ ガイド](../guides/gallery2d_smoothing_rank.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [color_transport](../../../../examples/color_transport.py) — `py -3.11 examples/color_transport.py`
- [gallery2d_smoothing_rank](../../../../examples/gallery2d_smoothing_rank.py) — `py -3.11 examples/gallery2d_smoothing_rank.py`
- [image_quality_metrics](../../../../examples/image_quality_metrics.py) — `py -3.11 examples/image_quality_metrics.py`
- [representation_roundtrip](../../../../examples/representation_roundtrip.py) — `py -3.11 examples/representation_roundtrip.py`
- [vision_layout_from_catalog](../../../../examples/vision_layout_from_catalog.py) — `py -3.11 examples/vision_layout_from_catalog.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](median.md) · [min_filter](min_filter.md) · [max_filter](max_filter.md)

## 同カテゴリ(`rank`)

[median](median.md) · [min_filter](min_filter.md) · [max_filter](max_filter.md) · [sk_median_disk](sk_median_disk.md) · [cv_median](cv_median.md) · [median_image](median_image.md) · [median_rect](median_rect.md) · [median_separate](median_separate.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
