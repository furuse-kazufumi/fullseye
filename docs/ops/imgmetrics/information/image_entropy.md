---
op: image_entropy
dim: imgmetrics
category: information
in: image2d
out: scalar
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# image_entropy — IMGMETRICS `information` op

- **データ種**: `image2d` → `scalar`
- **呼び出し**: `import imgmetrics; imgmetrics.image_entropy(a, bins=64, data_range=None)` (または `opsimgmetrics.get("image_entropy")`)

## 使い方

1 枚のシャノンエントロピー [bit]。

``mutual_information`` と**同じビン割り**で出すので、
``mutual_information(a, a) == image_entropy(a)`` が厳密に成り立つ
(テストで固定)。既存の ``entropy_gray`` / ``entropy_image``(backends)は
別のビン割りなので値は一致しない ―― こちらは同時分布と整合する側。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`information`)

[joint_entropy](joint_entropy.md) · [mutual_information](mutual_information.md) · [normalized_mutual_information](normalized_mutual_information.md) · [joint_histogram](joint_histogram.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
