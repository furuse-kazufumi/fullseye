---
op: psnr
dim: imgmetrics
category: fidelity
in: image2d × image2d
out: scalar
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# psnr — IMGMETRICS `fidelity` op

- **データ種**: `image2d × image2d` → `scalar`
- **呼び出し**: `import imgmetrics; imgmetrics.psnr(a, b, data_range=None)` (または `opsimgmetrics.get("psnr")`)

## 使い方

ピーク信号対雑音比 [dB]。

完全に一致する 2 枚では **``inf``** を返す(0 除算を黙って回避するために
小さな値を足したりしない ―― それは「非常に良い一致」を有限の数値に化かし、
平均を取ったときに嘘になる)。

``data_range`` の決め方は :func:`data_range_of` を参照。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`fidelity`)

[mse](mse.md) · [rmse](rmse.md) · [ssim](ssim.md) · [ms_ssim](ms_ssim.md) · [ssim_map](ssim_map.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
