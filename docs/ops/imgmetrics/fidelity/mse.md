---
op: mse
dim: imgmetrics
category: fidelity
in: image2d × image2d
out: scalar
examples: [image_quality_metrics]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# mse — IMGMETRICS `fidelity` op

- **データ種**: `image2d × image2d` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.mse(a, b)` (実装を直接呼ぶなら `import imgmetrics; imgmetrics.mse(a, b)`、台帳から引くなら `opsimgmetrics.get("mse")`)

## 使い方

平均二乗誤差。``data_range`` に依らない生の量。

式: ``mean((a - b)^2)``(全要素、float64 で計算)。

- ``a``, ``b``: 同じ形なら次元は問わない(2-D グレー、``(H, W, 3)``、3-D 体積)。
  dtype も問わないが **画素値の尺度をそのまま引き継ぐ** ―― uint8 の 2 枚と、
  それを ``/255`` した float の 2 枚では値が ``255^2`` 倍違う。尺度を揃えて比べたい
  なら ``psnr``(``data_range`` で正規化)を使う。
- 返り値: Python の ``float``。0 が完全一致、上限は ``data_range^2``。
- 失敗(``MetricContractError``): 形が違う / 空 / NaN・Inf を含む(黙って伝播させない)。

平方根が要るなら ``rmse``。まとめて測るなら ``compare_images``。

## 詳しい使い方ガイド

- [image_difference_metrics ファミリ ガイド](../guides/image_difference_metrics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_quality_metrics](../../../../examples/image_quality_metrics.py) — `py -3.11 examples/image_quality_metrics.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`fidelity`)

[rmse](rmse.md) · [psnr](psnr.md) · [ssim](ssim.md) · [ms_ssim](ms_ssim.md) · [ssim_map](ssim_map.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
