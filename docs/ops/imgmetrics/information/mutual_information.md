---
op: mutual_information
dim: imgmetrics
category: information
in: image2d × image2d
out: scalar
examples: [image_quality_metrics]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# mutual_information — IMGMETRICS `information` op

- **データ種**: `image2d × image2d` → `scalar`
- **呼び出し**: `import imgmetrics; imgmetrics.mutual_information(a, b, bins=64, data_range=None)` (または `opsimgmetrics.get("mutual_information")`)

## 使い方

相互情報量 I(A; B) [bit] = H(A) + H(B) - H(A, B)。

**ビン数に依存する**(増やすほど上振れする)ので ``bins`` は明示的な引数。
独立な 2 枚でも標本が有限なので厳密に 0 にはならない ―― どれくらい上振れ
するかはテストに数値で残してある。

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

## 同カテゴリ(`information`)

[image_entropy](image_entropy.md) · [joint_entropy](joint_entropy.md) · [normalized_mutual_information](normalized_mutual_information.md) · [joint_histogram](joint_histogram.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
