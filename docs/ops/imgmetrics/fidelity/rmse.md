---
op: rmse
dim: imgmetrics
category: fidelity
in: image2d × image2d
out: scalar
examples: [grasp_pose, image_quality_metrics, physical_ai_perception]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# rmse — IMGMETRICS `fidelity` op

- **データ種**: `image2d × image2d` → `scalar`
- **呼び出し**: `import imgmetrics; imgmetrics.rmse(a, b)` (または `opsimgmetrics.get("rmse")`)

## 使い方

平均二乗誤差の平方根(画素値と同じ単位)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [grasp_pose](../../../../examples/grasp_pose.py) — `py -3.11 examples/grasp_pose.py`
- [image_quality_metrics](../../../../examples/image_quality_metrics.py) — `py -3.11 examples/image_quality_metrics.py`
- [physical_ai_perception](../../../../examples/physical_ai_perception.py) — `py -3.11 examples/physical_ai_perception.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`fidelity`)

[mse](mse.md) · [psnr](psnr.md) · [ssim](ssim.md) · [ms_ssim](ms_ssim.md) · [ssim_map](ssim_map.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
