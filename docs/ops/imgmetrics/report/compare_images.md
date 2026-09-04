---
op: compare_images
dim: imgmetrics
category: report
in: image2d × image2d
out: metrics
examples: [image_quality_metrics]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# compare_images — IMGMETRICS `report` op

- **データ種**: `image2d × image2d` → `metrics`
- **呼び出し**: `import imgmetrics; imgmetrics.compare_images(a, b, data_range=None, bins=64, channel_axis=None, ms=False)` (または `opsimgmetrics.get("compare_images")`)

## 使い方

一括で測り、**何をどう測ったかを一緒に返す**。

返り値の ``contract`` に ``data_range`` / ``bins`` / ``crop_border`` /
SSIM の窓を入れてあるのは、数値だけを図注に写して**条件が消える**のを
防ぐため(この repo で実際に起きた事故の型)。

Returns
-------
dict
    ``{"mse", "rmse", "psnr", "ssim", "mutual_information",
    "normalized_mutual_information", "ncd", "contract": {...}}``。
    ``ms=True`` なら ``ms_ssim`` も(成立しない大きさなら ``ValueError``)。
    カラー画像で ``channel_axis`` を渡すと ``delta_e_2000_mean`` も入る。

## 詳しい使い方ガイド

- [image_difference_metrics ファミリ ガイド](../guides/image_difference_metrics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_quality_metrics](../../../../examples/image_quality_metrics.py) — `py -3.11 examples/image_quality_metrics.py`

## 型が繋がる次の op(`metrics` を入力に取れる)

[measure_with](measure_with.md) · [metrics_table](metrics_table.md)

## 同カテゴリ(`report`)

[measure_with](measure_with.md) · [metrics_table](metrics_table.md) · [data_range_of](data_range_of.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
