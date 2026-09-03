---
op: ssim
dim: imgmetrics
category: fidelity
in: image2d × image2d
out: scalar
examples: [image_quality_metrics]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# ssim — IMGMETRICS `fidelity` op

- **データ種**: `image2d × image2d` → `scalar`
- **呼び出し**: `import imgmetrics; imgmetrics.ssim(a, b, data_range=None, win_size=11, sigma=1.5, K1=0.01, K2=0.03, channel_axis=None, crop_border=True)` (または `opsimgmetrics.get("ssim")`)

## 使い方

構造的類似度(Wang, Bovik, Sheikh & Simoncelli, IEEE TIP 13(4), 2004)。

既定は原論文の設定 ―― **11x11 のガウシアン窓 σ=1.5、K1=0.01、K2=0.03**、
重み付き**母**分散(標本分散への ``n/(n-1)`` 補正を入れない)。

``crop_border=True``(既定)は窓の半径ぶんの縁を平均から落とす。縁では
鏡像で埋めた画素が統計に混ざるため。**落とすかどうかで値が変わる**ので、
他所の数値と比べるときは必ずこの設定を揃えること(小さい絵ほど差が出る)。

Returns
-------
float
    1.0 が完全一致。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_quality_metrics](../../../../examples/image_quality_metrics.py) — `py -3.11 examples/image_quality_metrics.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`fidelity`)

[mse](mse.md) · [rmse](rmse.md) · [psnr](psnr.md) · [ms_ssim](ms_ssim.md) · [ssim_map](ssim_map.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
