---
op: joint_histogram
dim: imgmetrics
category: information
in: image2d × image2d
out: image2d
examples: [image_quality_metrics]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# joint_histogram — IMGMETRICS `information` op

- **データ種**: `image2d × image2d` → `image2d`
- **呼び出し**: `import imgmetrics; imgmetrics.joint_histogram(a, b, bins=64, data_range=None)` (または `opsimgmetrics.get("joint_histogram")`)

## 使い方

2 枚の同時ヒストグラム(正規化した同時確率)。

ビン幅は ``data_range`` から決める ―― 画像ごとに min/max で伸縮させると、
**一様に暗い絵と一様に明るい絵の相互情報量が同じになる**ので。

## 詳しい使い方ガイド

- [image_difference_metrics ファミリ ガイド](../guides/image_difference_metrics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_quality_metrics](../../../../examples/image_quality_metrics.py) — `py -3.11 examples/image_quality_metrics.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[mse](../fidelity/mse.md) · [rmse](../fidelity/rmse.md) · [psnr](../fidelity/psnr.md) · [ssim](../fidelity/ssim.md) · [ms_ssim](../fidelity/ms_ssim.md) · [ssim_map](../fidelity/ssim_map.md) · [image_entropy](image_entropy.md) · [joint_entropy](joint_entropy.md)

## 同カテゴリ(`information`)

[image_entropy](image_entropy.md) · [joint_entropy](joint_entropy.md) · [mutual_information](mutual_information.md) · [normalized_mutual_information](normalized_mutual_information.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
