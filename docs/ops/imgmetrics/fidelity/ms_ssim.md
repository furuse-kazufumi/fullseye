---
op: ms_ssim
dim: imgmetrics
category: fidelity
in: image2d × image2d
out: scalar
examples: [image_quality_metrics]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# ms_ssim — IMGMETRICS `fidelity` op

- **データ種**: `image2d × image2d` → `scalar`
- **呼び出し**: `import imgmetrics; imgmetrics.ms_ssim(a, b, data_range=None, win_size=11, sigma=1.5, K1=0.01, K2=0.03, weights=(0.0448, 0.2856, 0.3001, 0.2363, 0.1333), crop_border=True)` (または `opsimgmetrics.get("ms_ssim")`)

## 使い方

多尺度 SSIM(Wang, Simoncelli & Bovik, Asilomar Conf. 2003)。

5 段の縮小を経るので、最終段で 11 画素の窓が成立するには**各辺 176 画素**が
要る。足りないときに**段数を黙って減らさない** ―― 段数の違う MS-SSIM は
別の指標であり、比べると嘘になる。足りなければ ``ValueError``。

2 次元のグレー画像専用(色は ``channel_axis`` ではなくチャネルごとに呼ぶ)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_quality_metrics](../../../../examples/image_quality_metrics.py) — `py -3.11 examples/image_quality_metrics.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`fidelity`)

[mse](mse.md) · [rmse](rmse.md) · [psnr](psnr.md) · [ssim](ssim.md) · [ssim_map](ssim_map.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
