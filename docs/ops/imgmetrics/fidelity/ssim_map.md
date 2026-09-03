---
op: ssim_map
dim: imgmetrics
category: fidelity
in: image2d × image2d
out: image2d
examples: [image_quality_metrics]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# ssim_map — IMGMETRICS `fidelity` op

- **データ種**: `image2d × image2d` → `image2d`
- **呼び出し**: `import imgmetrics; imgmetrics.ssim_map(a, b, data_range=None, win_size=11, sigma=1.5, K1=0.01, K2=0.03, channel_axis=None, crop_border=True)` (または `opsimgmetrics.get("ssim_map")`)

## 使い方

SSIM の**マップ**(平均を取る前)。どこが似ていないかを絵で見るため。

``channel_axis`` を指定するとチャネルごとに計算し、その平均マップを返す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_quality_metrics](../../../../examples/image_quality_metrics.py) — `py -3.11 examples/image_quality_metrics.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[mse](mse.md) · [rmse](rmse.md) · [psnr](psnr.md) · [ssim](ssim.md) · [ms_ssim](ms_ssim.md) · [image_entropy](../information/image_entropy.md) · [joint_entropy](../information/joint_entropy.md) · [mutual_information](../information/mutual_information.md)

## 同カテゴリ(`fidelity`)

[mse](mse.md) · [rmse](rmse.md) · [psnr](psnr.md) · [ssim](ssim.md) · [ms_ssim](ms_ssim.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
