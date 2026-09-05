---
op: delta_e_map
dim: imgmetrics
category: colordiff
in: rgbimage × rgbimage
out: image2d
examples: [color_transport, image_quality_metrics]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# delta_e_map — IMGMETRICS `colordiff` op

- **データ種**: `rgbimage × rgbimage` → `image2d`
- **呼び出し**: `import imgmetrics; imgmetrics.delta_e_map(rgb1, rgb2, kind='2000', white=(0.95047, 1.0, 1.08883))` (または `opsimgmetrics.get("delta_e_map")`)

## 使い方

2 枚の **sRGB 画像**の画素ごとの色差マップ。

RGB の平均二乗誤差ではなく**知覚的な色差**で見るための入口。
``kind`` は ``"2000"``(既定)または ``"76"``。

## 詳しい使い方ガイド

- [image_difference_metrics ファミリ ガイド](../guides/image_difference_metrics.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [colorimetry](../../2d/guides/colorimetry.md) — 測色と分光の知識 — 色は「分光 × 光源 × 観測者」でしか決まらない

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [color_transport](../../../../examples/color_transport.py) — `py -3.11 examples/color_transport.py`
- [image_quality_metrics](../../../../examples/image_quality_metrics.py) — `py -3.11 examples/image_quality_metrics.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[mse](../fidelity/mse.md) · [rmse](../fidelity/rmse.md) · [psnr](../fidelity/psnr.md) · [ssim](../fidelity/ssim.md) · [ms_ssim](../fidelity/ms_ssim.md) · [ssim_map](../fidelity/ssim_map.md) · [image_entropy](../information/image_entropy.md) · [joint_entropy](../information/joint_entropy.md)

## 同カテゴリ(`colordiff`)

[delta_e_2000](delta_e_2000.md) · [delta_e_76](delta_e_76.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
