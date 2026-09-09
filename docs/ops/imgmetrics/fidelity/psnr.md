---
op: psnr
dim: imgmetrics
category: fidelity
in: image2d × image2d
out: scalar
examples: [image_quality_metrics, poc_camera_shake_deblur, poc_dehazing, poc_focus_stacking, poc_real_deblur_honesty, poc_superresolution_limits]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# psnr — IMGMETRICS `fidelity` op

- **データ種**: `image2d × image2d` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.psnr(a, b, data_range=None)` (実装を直接呼ぶなら `import imgmetrics; imgmetrics.psnr(a, b, data_range=None)`、台帳から引くなら `opsimgmetrics.get("psnr")`)

## 使い方

ピーク信号対雑音比 [dB]。

完全に一致する 2 枚では **``inf``** を返す(0 除算を黙って回避するために
小さな値を足したりしない ―― それは「非常に良い一致」を有限の数値に化かし、
平均を取ったときに嘘になる)。

``data_range`` の決め方は :func:`data_range_of` を参照。

## 詳しい使い方ガイド

- [image_difference_metrics ファミリ ガイド](../guides/image_difference_metrics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_quality_metrics](../../../../examples/image_quality_metrics.py) — `py -3.11 examples/image_quality_metrics.py`
- [poc_camera_shake_deblur](../../../../examples/poc_camera_shake_deblur.py) — `py -3.11 examples/poc_camera_shake_deblur.py`
- [poc_dehazing](../../../../examples/poc_dehazing.py) — `py -3.11 examples/poc_dehazing.py`
- [poc_focus_stacking](../../../../examples/poc_focus_stacking.py) — `py -3.11 examples/poc_focus_stacking.py`
- [poc_real_deblur_honesty](../../../../examples/poc_real_deblur_honesty.py) — `py -3.11 examples/poc_real_deblur_honesty.py`
- [poc_superresolution_limits](../../../../examples/poc_superresolution_limits.py) — `py -3.11 examples/poc_superresolution_limits.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`fidelity`)

[mse](mse.md) · [rmse](rmse.md) · [ssim](ssim.md) · [ms_ssim](ms_ssim.md) · [ssim_map](ssim_map.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
