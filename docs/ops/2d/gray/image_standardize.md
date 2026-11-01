---
op: image_standardize
dim: 2d
category: gray
in: image
out: image
examples: [poc_threshold_transfer_after_normalization]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# image_standardize — 2D `gray` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "image_standardize", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

画像を z-score・頑健 MAD・百分位のいずれかで零中心に標準化する。

``a`` の 3 帯が ``zscore`` / ``robust`` / ``percentile``。百分位方式では ``b`` を
片側の切り落とし率 0.5〜10 % に写し、対応する上下分位点を -1 / +1 にする。
出力は clip しない float64。MAD=0 など尺度を定義できない入力は拒否する。

**空入力と尺度 0 の入力は、標準化後の単位を定義できないため拒否する。**

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_threshold_transfer_after_normalization](../../../../examples/poc_threshold_transfer_after_normalization.py) — `py -3.11 examples/poc_threshold_transfer_after_normalization.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [mean_box_wh](../smoothing/mean_box_wh.md) · [bilateral](../smoothing/bilateral.md) · [kuwahara](../smoothing/kuwahara.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md)

## 同カテゴリ(`gray`)

[gamma](gamma.md) · [quantize_uniform](quantize_uniform.md) · [quantize_lloyd_max](quantize_lloyd_max.md) · [quantization_error](quantization_error.md) · [dither_ordered](dither_ordered.md) · [dither_floyd_steinberg](dither_floyd_steinberg.md) · [companding_mu_law](companding_mu_law.md) · [banding_map](banding_map.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
